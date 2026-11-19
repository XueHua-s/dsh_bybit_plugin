"""Immutable engine-owned risk snapshots; none of these types proves caller authority."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

Environment = Literal["backtest", "internal_paper", "demo", "testnet", "mainnet"]
Side = Literal["BUY", "SELL"]


@dataclass(frozen=True)
class OrderIntent:
    """Untrusted proposal only; every order is charged as additional gross exposure."""

    request_id: str
    symbol: str
    side: Side
    quantity: Decimal
    price_limit: Decimal
    leverage: Decimal


@dataclass(frozen=True)
class Exposure:
    """One gross leg/reservation in trusted common USDT valuation, never hedge-netted.

    Server must freshly mark positions and normalize valuation before snapshotting.
    liquidation_distance is an adverse-price fraction, not a currency amount.
    """

    reference: str
    symbol: str
    notional: Decimal
    leverage: Decimal
    liquidation_distance: Decimal
    observed_at_ms: int


@dataclass(frozen=True)
class Correlation:
    first: str
    second: str
    coefficient: Decimal


@dataclass(frozen=True)
class MarketSnapshot:
    """Server estimate for this intent's side/size, including finite executable liquidity."""

    symbol: str
    estimated_for: OrderIntent
    observed_at_ms: int
    bid: Decimal
    ask: Decimal
    executable_price: Decimal
    executable_depth_notional: Decimal
    funding_rate: Decimal
    projected_liquidation_distance: Decimal
    quantity_step: Decimal
    price_tick: Decimal
    min_quantity: Decimal
    max_quantity: Decimal
    min_notional: Decimal


@dataclass(frozen=True)
class AccountSnapshot:
    """Private reconciled equity/margin; daily loss includes realized + unrealized loss."""

    account_id: str
    environment: Environment
    observed_at_ms: int
    equity: Decimal
    available_margin: Decimal
    daily_start_equity: Decimal
    daily_loss: Decimal
    peak_equity: Decimal
    identity_verified: bool
    trading_permitted: bool
    reconciled: bool


@dataclass(frozen=True)
class RiskContext:
    """One server-owned atomic generation, including complete positions and reservations.

    All notionals, executable depth, equity, margin, daily loss and prices must use
    one server-normalized valuation numeraire (initially USDT per base unit). Fresh
    mark/FX provenance is required of the snapshot producer; mixed units are invalid
    caller behavior and cannot be detected from these Decimal amounts alone.
    correlation_at_ms and portfolio_at_ms certify separately acquired snapshots.
    last_trade_at_ms must include accepted pending orders, not just fills. An empty
    positions/reservations tuple is authoritative only after successful reconciliation.
    """

    snapshot_id: str
    now_ms: int
    portfolio_at_ms: int
    correlation_at_ms: int
    last_trade_at_ms: int
    account: AccountSnapshot
    market: MarketSnapshot
    positions: tuple[Exposure, ...]
    reservations: tuple[Exposure, ...]
    correlations: tuple[Correlation, ...]
    emergency_stop: bool


@dataclass(frozen=True)
class RiskPolicy:
    """Required operator-owned ceilings; no implicit permissive defaults or secret fields."""

    account_id: str
    environment: Environment
    max_order_notional: Decimal
    max_position_notional: Decimal
    max_leverage: Decimal
    max_account_exposure: Decimal
    max_daily_loss_fraction: Decimal
    max_drawdown_fraction: Decimal
    max_concurrent_positions: int
    max_slippage_fraction: Decimal
    max_spread_fraction: Decimal
    max_liquidity_participation: Decimal
    max_abs_funding_rate: Decimal
    min_liquidation_distance: Decimal
    max_concentration_fraction: Decimal
    correlation_threshold: Decimal
    max_correlated_exposure_fraction: Decimal
    fee_buffer_fraction: Decimal
    cooldown_ms: int
    snapshot_ttl_ms: int


@dataclass(frozen=True)
class ApprovedPlan:
    """Exact scoped evidence, not a bearer execution token; revalidate before submission."""

    intent: OrderIntent
    snapshot_id: str
    expires_at_ms: int
    order_notional: Decimal
    projected_gross_exposure: Decimal


@dataclass(frozen=True)
class RiskDecision:
    """Empty reasons iff plan exists. Stable codes contain no untrusted input text."""

    reasons: tuple[str, ...]
    approved_plan: ApprovedPlan | None

    @property
    def approved(self) -> bool:
        return self.approved_plan is not None
