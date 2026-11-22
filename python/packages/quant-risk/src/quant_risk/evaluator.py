"""Deterministic gross-risk veto; execution, snapshot acquisition and reservations live elsewhere."""

from decimal import ROUND_CEILING, Decimal, DecimalException, Inexact, Rounded, localcontext

from .models import ApprovedPlan, OrderIntent, RiskContext, RiskDecision, RiskPolicy
from .validation import context_valid, intent_valid, policy_valid

ZERO = Decimal(0)


def evaluate(intent: OrderIntent, context: RiskContext, policy: RiskPolicy) -> RiskDecision:
    """Evaluate complete engine-owned state, never trusting a model-provided risk snapshot.

    Pure approval neither reserves funds nor permits execution. The caller must serialize
    decisions, persist reservations and revalidate the generation before Nautilus submission.
    All orders consume gross exposure, including reductions; there is no bypass flag.
    """
    invalid = tuple(
        code
        for valid, code in (
            (intent_valid(intent), "invalid_intent"),
            (context_valid(context), "invalid_context"),
            (policy_valid(policy), "invalid_policy"),
        )
        if not valid
    )
    if invalid:
        return RiskDecision(invalid, None)
    try:
        # Caller decimal settings must not change arithmetic or precision of decisions.
        with localcontext() as arithmetic:
            arithmetic.prec = 100
            arithmetic.rounding = ROUND_CEILING
            arithmetic.Emax = 999
            arithmetic.Emin = -999
            for signal in arithmetic.traps:
                arithmetic.traps[signal] = True
            # Repeating ratios are expected; comparisons use multiplication below.
            arithmetic.traps[Inexact] = False
            arithmetic.traps[Rounded] = False
            return _evaluate(intent, context, policy)
    except DecimalException:
        return RiskDecision(("arithmetic_invalid",), None)


def _evaluate(intent: OrderIntent, context: RiskContext, policy: RiskPolicy) -> RiskDecision:
    reasons: list[str] = []

    def reject(condition: bool, code: str) -> None:
        if condition:
            reasons.append(code)

    account, market = context.account, context.market
    exposures = context.positions + context.reservations
    reject(context.emergency_stop, "emergency_stop")
    reject(policy.environment == "mainnet" or account.environment == "mainnet", "mainnet_disabled")
    reject(account.environment != policy.environment, "environment_mismatch")
    reject(account.account_id != policy.account_id or not account.identity_verified, "account_identity")
    reject(not account.trading_permitted, "trading_permission")
    reject(not account.reconciled, "reconciliation_required")
    reject(market.symbol != intent.symbol or market.estimated_for != intent, "market_estimate_mismatch")
    times = (account.observed_at_ms, market.observed_at_ms, context.portfolio_at_ms, context.correlation_at_ms) + tuple(
        item.observed_at_ms for item in exposures
    )
    reject(
        any(timestamp > context.now_ms for timestamp in times) or context.last_trade_at_ms > context.now_ms,
        "future_snapshot",
    )
    reject(any(context.now_ms - timestamp > policy.snapshot_ttl_ms for timestamp in times), "stale_snapshot")
    reject(context.now_ms - context.last_trade_at_ms < policy.cooldown_ms, "trading_cooldown")

    # Executable depth/price must be a trusted estimate for this precise proposal.
    reject(
        market.executable_price < market.ask if intent.side == "BUY" else market.executable_price > market.bid,
        "inconsistent_execution_estimate",
    )
    reject(
        market.executable_price > intent.price_limit
        if intent.side == "BUY"
        else market.executable_price < intent.price_limit,
        "price_limit",
    )
    reject(
        intent.quantity < market.min_quantity
        or intent.quantity > market.max_quantity
        or intent.quantity % market.quantity_step != 0
        or intent.price_limit % market.price_tick != 0,
        "instrument_precision",
    )
    # A BUY may execute anywhere up to its ceiling; a SELL receives no margin credit
    # for its lower floor. Charge the greater of executable value and intent limit.
    notional = intent.quantity * max(market.executable_price, intent.price_limit)
    reject(intent.quantity * min(market.executable_price, intent.price_limit) < market.min_notional, "minimum_notional")
    reject(notional > policy.max_order_notional, "max_order_size")
    symbol_totals: dict[str, Decimal] = {}
    for exposure in exposures:
        symbol_totals[exposure.symbol] = symbol_totals.get(exposure.symbol, ZERO) + exposure.notional
    symbol_totals[intent.symbol] = symbol_totals.get(intent.symbol, ZERO) + notional
    gross = sum(symbol_totals.values(), ZERO)
    reject(any(value > policy.max_position_notional for value in symbol_totals.values()), "max_position_size")
    reject(
        intent.leverage > policy.max_leverage
        or any(item.leverage > policy.max_leverage for item in exposures)
        or gross > policy.max_leverage * account.equity,
        "max_leverage",
    )
    reject(gross > policy.max_account_exposure, "max_account_exposure")
    # Charge pending reservations again if exchange available margin already excludes
    # them; conservative double charging is preferable to an implicit funding credit.
    required_margin = notional / intent.leverage + notional * policy.fee_buffer_fraction
    required_margin += sum(
        (item.notional / item.leverage + item.notional * policy.fee_buffer_fraction for item in context.reservations),
        ZERO,
    )
    reject(required_margin > account.available_margin, "insufficient_margin")
    loss = max(account.daily_loss, account.daily_start_equity - account.equity)
    reject(loss >= policy.max_daily_loss_fraction * account.daily_start_equity, "max_daily_loss")
    reject(account.peak_equity - account.equity >= policy.max_drawdown_fraction * account.peak_equity, "max_drawdown")
    reject(len(exposures) + 1 > policy.max_concurrent_positions, "max_concurrent_positions")
    midpoint = (market.ask + market.bid) / 2
    reject(market.ask - market.bid > policy.max_spread_fraction * midpoint, "spread_limit")
    reference = market.ask if intent.side == "BUY" else market.bid
    adverse = (
        max(market.executable_price, intent.price_limit) - reference
        if intent.side == "BUY"
        else reference - min(market.executable_price, intent.price_limit)
    )
    reject(adverse > policy.max_slippage_fraction * reference, "max_slippage")
    reject(notional > market.executable_depth_notional * policy.max_liquidity_participation, "liquidity_limit")
    reject(abs(market.funding_rate) > policy.max_abs_funding_rate, "funding_risk")
    reject(
        market.projected_liquidation_distance < policy.min_liquidation_distance
        or any(item.liquidation_distance < policy.min_liquidation_distance for item in exposures),
        "liquidation_distance",
    )
    reject(
        any(value > policy.max_concentration_fraction * account.equity for value in symbol_totals.values()),
        "concentration_risk",
    )
    pairs = {tuple(sorted((pair.first, pair.second))): abs(pair.coefficient) for pair in context.correlations}
    symbols = sorted(symbol_totals)
    missing = any(
        (first, second) not in pairs for index, first in enumerate(symbols) for second in symbols[index + 1 :]
    )
    reject(missing, "correlation_missing")
    if not missing:
        # Connected components are deliberately conservative: chained correlations
        # aggregate the whole cluster rather than granting unsupported diversification.
        remaining = set(symbols)
        largest_cluster = ZERO
        while remaining:
            frontier = [min(remaining)]
            cluster: set[str] = set()
            while frontier:
                symbol = frontier.pop()
                if symbol in cluster:
                    continue
                cluster.add(symbol)
                frontier.extend(
                    other
                    for other in remaining - cluster
                    if other != symbol
                    and pairs.get(tuple(sorted((symbol, other))), ZERO) >= policy.correlation_threshold
                )
            remaining -= cluster
            largest_cluster = max(largest_cluster, sum((symbol_totals[symbol] for symbol in cluster), ZERO))
        reject(largest_cluster > policy.max_correlated_exposure_fraction * account.equity, "correlation_risk")
    if reasons:
        return RiskDecision(tuple(reasons), None)
    return RiskDecision(
        (), ApprovedPlan(intent, context.snapshot_id, min(times) + policy.snapshot_ttl_ms, notional, gross)
    )
