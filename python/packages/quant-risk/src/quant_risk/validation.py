"""Strict runtime shape and numerical bounds before any risk arithmetic occurs."""

from dataclasses import fields
from decimal import Decimal

from .models import AccountSnapshot, Correlation, Exposure, MarketSnapshot, OrderIntent, RiskContext, RiskPolicy

ENVIRONMENTS = ("backtest", "internal_paper", "demo", "testnet", "mainnet")


def number(value: object, *, positive: bool = False, signed: bool = False) -> bool:
    if type(value) is not Decimal or not value.is_finite():
        return False
    parts = value.as_tuple()
    if len(parts.digits) > 28 or not isinstance(parts.exponent, int) or not -18 <= parts.exponent <= 18:
        return False
    if value.copy_abs() > Decimal("1e18"):
        return False
    return value > 0 if positive else signed or value >= 0


def integer(value: object, *, positive: bool = False) -> bool:
    return type(value) is int and (0 < value <= 10**16 if positive else 0 <= value <= 10**16)


def text(value: object) -> bool:
    return (
        type(value) is str and 0 < len(value) <= 128 and bool(value.strip()) and value.isascii() and value.isprintable()
    )


def intent_valid(intent: OrderIntent) -> bool:
    return (
        type(intent) is OrderIntent
        and text(intent.request_id)
        and text(intent.symbol)
        and type(intent.side) is str
        and intent.side in ("BUY", "SELL")
        and number(intent.quantity, positive=True)
        and number(intent.price_limit, positive=True)
        and number(intent.leverage, positive=True)
    )


def policy_valid(policy: RiskPolicy) -> bool:
    if (
        type(policy) is not RiskPolicy
        or not text(policy.account_id)
        or type(policy.environment) is not str
        or policy.environment not in ENVIRONMENTS
    ):
        return False
    decimals = [getattr(policy, field.name) for field in fields(policy) if field.type is Decimal]
    if not all(number(value, positive=True) for value in decimals):
        return False
    fractions = (
        policy.max_daily_loss_fraction,
        policy.max_drawdown_fraction,
        policy.max_slippage_fraction,
        policy.max_spread_fraction,
        policy.max_liquidity_participation,
        policy.max_abs_funding_rate,
        policy.min_liquidation_distance,
        policy.correlation_threshold,
        policy.fee_buffer_fraction,
    )
    return (
        all(value <= 1 for value in fractions)
        and integer(policy.max_concurrent_positions, positive=True)
        and policy.max_concurrent_positions <= 10_000
        and integer(policy.cooldown_ms)
        and integer(policy.snapshot_ttl_ms, positive=True)
    )


def exposure_valid(exposure: Exposure) -> bool:
    return (
        type(exposure) is Exposure
        and text(exposure.reference)
        and text(exposure.symbol)
        and number(exposure.notional, positive=True)
        and number(exposure.leverage, positive=True)
        and number(exposure.liquidation_distance, positive=True)
        and exposure.liquidation_distance <= 1
        and integer(exposure.observed_at_ms)
    )


def account_valid(account: AccountSnapshot) -> bool:
    return (
        type(account) is AccountSnapshot
        and text(account.account_id)
        and type(account.environment) is str
        and account.environment in ENVIRONMENTS
        and integer(account.observed_at_ms)
        and all(
            type(value) is bool
            for value in (
                account.identity_verified,
                account.trading_permitted,
                account.reconciled,
            )
        )
        and number(account.equity, positive=True)
        and number(account.available_margin)
        and account.available_margin <= account.equity
        and number(account.daily_start_equity, positive=True)
        and number(account.daily_loss)
        and number(account.peak_equity, positive=True)
        and account.peak_equity >= account.equity
    )


def market_valid(market: MarketSnapshot) -> bool:
    if (
        type(market) is not MarketSnapshot
        or not text(market.symbol)
        or not integer(market.observed_at_ms)
        or not intent_valid(market.estimated_for)
    ):
        return False
    decimals = [
        getattr(market, field.name)
        for field in fields(market)
        if field.type is Decimal and field.name != "funding_rate"
    ]
    return (
        all(number(value, positive=True) for value in decimals)
        and number(market.funding_rate, signed=True)
        and market.bid <= market.ask
        and market.min_quantity <= market.max_quantity
        and market.projected_liquidation_distance <= 1
    )


def context_valid(context: RiskContext) -> bool:
    if type(context) is not RiskContext:
        return False
    if not (
        text(context.snapshot_id)
        and all(
            integer(value)
            for value in (
                context.now_ms,
                context.portfolio_at_ms,
                context.correlation_at_ms,
                context.last_trade_at_ms,
            )
        )
        and type(context.emergency_stop) is bool
        and account_valid(context.account)
        and market_valid(context.market)
        and type(context.positions) is tuple
        and type(context.reservations) is tuple
        and type(context.correlations) is tuple
        and len(context.positions) + len(context.reservations) <= 10_000
        and len(context.correlations) <= 50_000
    ):
        return False
    exposures = context.positions + context.reservations
    if not all(exposure_valid(item) for item in exposures):
        return False
    if len({item.reference for item in exposures}) != len(exposures):
        return False
    pairs: set[tuple[str, str]] = set()
    for pair in context.correlations:
        if not (
            type(pair) is Correlation
            and text(pair.first)
            and text(pair.second)
            and pair.first != pair.second
            and number(pair.coefficient, signed=True)
            and pair.coefficient.copy_abs() <= 1
        ):
            return False
        key = (pair.first, pair.second) if pair.first < pair.second else (pair.second, pair.first)
        if key in pairs:
            return False
        pairs.add(key)
    return True
