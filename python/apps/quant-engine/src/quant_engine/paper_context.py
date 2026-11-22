"""Conservative valuation of explicit synthetic native state for the real risk evaluator."""

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

from quant_data.admission_contracts import SessionSnapshot
from quant_execution.paper_models import PaperSnapshot
from quant_risk.models import AccountSnapshot, Exposure, MarketSnapshot, OrderIntent, RiskContext
from quant_strategies import Bar
from quant_strategies import MarketSnapshot as StrategyMarketSnapshot
from quant_strategies.families import DEFAULT_CONFIGS, STRATEGY_METADATA
from quant_strategies.metadata import LifecycleStatus, ValidationStatus

from .paper_config import PaperConfig
from .strategy_registry import StrategyRegistry
from .strategy_selector import SelectionCandidate
from .synthetic_fixture_registry import PaperFixtureBundle


def selector_inputs(
    bundle: PaperFixtureBundle, symbol: str
) -> tuple[StrategyMarketSnapshot, tuple[SelectionCandidate, ...], StrategyRegistry]:
    """Convert one immutable fixture symbol into selector-owned typed inputs."""

    if type(bundle) is not PaperFixtureBundle or type(symbol) is not str:
        raise ValueError("invalid_selector_context")
    bundle.resolve(symbol)
    bars = bundle.bars_by_symbol[symbol]
    if len(bars) < 21:
        raise ValueError("insufficient_fixture_bars")
    strategy_bars = tuple(
        Bar(
            datetime.fromtimestamp(item.timestamp_ns / 1_000_000_000, tz=UTC),
            float(item.open),
            float(item.high),
            float(item.low),
            float(item.close),
            float(item.volume),
        )
        for item in bars
    )
    evidence = bundle.evidence_by_symbol[symbol]
    candidates = tuple(item.candidate() for item in evidence)
    registry = StrategyRegistry()
    registered = 0
    metadata_by_key = {(item.strategy_id, item.version): item for item in STRATEGY_METADATA}
    for item in evidence:
        metadata = metadata_by_key.get((item.strategy_id, item.version))
        if metadata is None:
            continue
        approved = replace(
            metadata,
            validation_status=ValidationStatus.PAPER_PASSED,
            current_status=LifecycleStatus.APPROVED,
            approval_ref=item.approval_ref,
        )
        registry.register(approved, DEFAULT_CONFIGS[item.strategy_id])
        registered += 1
    if registered == 0:
        raise ValueError("no_fixture_approved_strategies")
    return StrategyMarketSnapshot(strategy_bars), candidates, registry


def risk_context(
    config: PaperConfig,
    durable: SessionSnapshot,
    native: PaperSnapshot,
    intent: OrderIntent,
    now_ms: int,
    consumed_bid: Decimal,
    consumed_ask: Decimal,
    peak_equity: Decimal,
) -> RiskContext:
    """Use durable positions/reservations, delivered fixture depth and native account truth.

    Every position is charged gross at the larger quote. Unknown native/durable position
    divergence is reconciled by the caller before this function can authorize submission.
    Finite depth is depleted cumulatively and is never refreshed by a request.
    """
    fixture = config.fixture_for(intent.symbol)
    spec = fixture.instrument
    native_by_symbol = {item.symbol: item for item in native.instruments}
    if set(native_by_symbol) != {item.instrument.symbol for item in config.fixtures}:
        raise ValueError("native_fixture_set_mismatch")
    target_market = native_by_symbol.get(intent.symbol)
    if target_market is None:
        raise ValueError("native_fixture_symbol_missing")
    market_by_symbol = {symbol: max(item.bid, item.ask) for symbol, item in native_by_symbol.items()}
    durable_equity = durable.balance + sum(
        (
            item.quantity
            * (
                (native_by_symbol[item.symbol].bid if item.quantity > 0 else native_by_symbol[item.symbol].ask)
                - item.average_entry_price
            )
            for item in durable.positions
        ),
        Decimal(0),
    )
    equity = min(durable_equity, native.equity)
    positions = tuple(
        Exposure(
            f"position:{item.symbol}",
            item.symbol,
            abs(item.quantity) * market_by_symbol[item.symbol],
            Decimal(1),
            Decimal(1),
            now_ms,
        )
        for item in durable.positions
        if item.quantity
    )
    reservations = tuple(
        Exposure(
            item.command_id,
            item.symbol,
            item.remaining_quantity * max(item.price, market_by_symbol[item.symbol]),
            Decimal(1),
            Decimal(1),
            now_ms,
        )
        for item in durable.reservations
    )
    executable = target_market.ask if intent.side == "BUY" else target_market.bid
    depth = max(
        Decimal(0),
        (target_market.ask_size - consumed_ask) if intent.side == "BUY" else (target_market.bid_size - consumed_bid),
    )
    market = MarketSnapshot(
        spec.symbol,
        intent,
        target_market.market_timestamp_ns // 1_000_000,
        target_market.bid,
        target_market.ask,
        executable,
        depth * executable,
        Decimal(0),
        Decimal(1),
        spec.size_increment,
        spec.price_increment,
        spec.min_quantity,
        spec.max_quantity,
        spec.min_notional,
    )
    account = AccountSnapshot(
        native.account_id,
        "internal_paper",
        native.snapshot_timestamp_ns // 1_000_000,
        equity,
        min(durable_equity, native.available_equity),
        fixture.starting_balance,
        max(Decimal(0), fixture.starting_balance - equity),
        max(peak_equity, equity),
        True,
        True,
        not durable.protected,
    )
    return RiskContext(
        str(durable.generation),
        now_ms,
        now_ms,
        now_ms,
        (durable.last_admitted_at_ns or 0) // 1_000_000,
        account,
        market,
        positions,
        reservations,
        config.correlations,
        durable.protected,
    )
