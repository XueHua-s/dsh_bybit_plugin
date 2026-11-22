"""Internal server-owned paper facts; these are never wire authorization DTOs."""

import re
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from quant_data.commands import CommandState, RiskCode, Side, decimal_text, identifier


class AccountingModel(StrEnum):
    """Explicit server-configured economics; never infer this from side or symbol."""

    SPOT = "spot"
    LINEAR_PERPETUAL = "linear_perpetual"


RISK_REASONS = frozenset(
    (
        "account_identity",
        "arithmetic_invalid",
        "concentration_risk",
        "correlation_missing",
        "correlation_risk",
        "emergency_stop",
        "environment_mismatch",
        "funding_risk",
        "future_snapshot",
        "inconsistent_execution_estimate",
        "instrument_precision",
        "insufficient_margin",
        "invalid_context",
        "invalid_intent",
        "invalid_policy",
        "liquidation_distance",
        "liquidity_limit",
        "mainnet_disabled",
        "market_estimate_mismatch",
        "max_account_exposure",
        "max_concurrent_positions",
        "max_daily_loss",
        "max_drawdown",
        "max_leverage",
        "max_order_size",
        "max_position_size",
        "max_slippage",
        "minimum_notional",
        "price_limit",
        "reconciliation_required",
        "spread_limit",
        "stale_snapshot",
        "trading_cooldown",
        "trading_permission",
    )
)


def digest(value: str) -> str:
    if not isinstance(value, str) or re.fullmatch("[0-9a-f]{64}", value) is None:
        raise ValueError("expected sha256 fingerprint")
    return value


def timestamp(value: int) -> None:
    if type(value) is not int or not 0 <= value <= 2**63 - 1:
        raise ValueError("expected nonnegative nanosecond timestamp")


@dataclass(frozen=True)
class AdmissionDecision:
    allowed: bool
    code: RiskCode
    policy_fingerprint: str
    context_fingerprint: str
    evaluated_at_ns: int
    expires_at_ns: int
    reservation_price: Decimal
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.allowed) is not bool or not isinstance(self.code, RiskCode):
            raise TypeError("typed risk decision required")
        if self.allowed != (self.code == RiskCode.APPROVED):
            raise ValueError("contradictory risk decision")
        if type(self.reasons) is not tuple or any(code not in RISK_REASONS for code in self.reasons):
            raise ValueError("unknown risk reason code")
        if self.allowed and self.reasons:
            raise ValueError("approved decision cannot have veto reasons")
        digest(self.policy_fingerprint)
        digest(self.context_fingerprint)
        timestamp(self.evaluated_at_ns)
        timestamp(self.expires_at_ns)
        if self.expires_at_ns <= self.evaluated_at_ns:
            raise ValueError("decision expiry must follow evaluation")
        decimal_text(self.reservation_price)
        if self.reservation_price <= 0:
            raise ValueError("reservation price must be positive")


@dataclass(frozen=True)
class NativeObservation:
    command_id: str
    event_id: str
    state: CommandState
    cumulative_filled: Decimal
    cumulative_notional: Decimal
    cumulative_fee: Decimal
    occurred_at_ns: int

    def __post_init__(self) -> None:
        identifier(self.command_id, "command_id")
        identifier(self.event_id, "event_id")
        if self.event_id.startswith("internal:") or not isinstance(self.state, CommandState):
            raise ValueError("invalid native observation")
        for value in (self.cumulative_filled, self.cumulative_notional, self.cumulative_fee):
            decimal_text(value)
        timestamp(self.occurred_at_ns)


@dataclass(frozen=True)
class PositionSnapshot:
    symbol: str
    quantity: Decimal
    average_entry_price: Decimal = Decimal(0)


@dataclass(frozen=True)
class ReservationSnapshot:
    command_id: str
    symbol: str
    side: Side
    remaining_quantity: Decimal
    price: Decimal


@dataclass(frozen=True)
class SessionSnapshot:
    session_id: str
    account_ref: str
    owner_id: str
    generation: int
    protected: bool
    protection_reason: str | None
    balance: Decimal
    positions: tuple[PositionSnapshot, ...]
    reservations: tuple[ReservationSnapshot, ...]
    last_admitted_at_ns: int | None
    accounting_model: AccountingModel = AccountingModel.SPOT
    realized_pnl: Decimal = Decimal(0)
    cumulative_fee: Decimal = Decimal(0)
