"""Testnet AI proposal admission into the durable native ledger.

This is deliberately a venue-free boundary.  The returned claim is a durable
handoff for a future native owner; this module never creates an exchange
client, retries a submission, or treats an approved risk decision as a bearer
authorization token.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Protocol

from quant_data.commands import CommandRecord, CommandState, Environment, OrderCommand, OrderType, RiskCode, Side
from quant_data.ledger import CommandLedger
from quant_risk.evaluator import evaluate
from quant_risk.models import RiskContext, RiskPolicy

from .bybit_session import BybitSession, BybitSessionUnavailable, order_intent


class RiskContextSource(Protocol):
    """Engine-owned source of a fresh private/market context."""

    def context_for(self, command: OrderCommand) -> RiskContext: ...


@dataclass(frozen=True)
class NativeDispatchClaim:
    """Durable one-shot claim; no venue response is implied."""

    command_id: str
    native_client_order_id: str
    generation: int
    reconciliation_revision: int


@dataclass(frozen=True)
class NativeAdmissionReceipt:
    command: CommandRecord
    reasons: tuple[str, ...]
    claim: NativeDispatchClaim | None


@dataclass(frozen=True)
class NativeProposal:
    """The only AI input accepted by the Testnet admission boundary."""

    request_id: str
    symbol: str
    side: Literal["buy", "sell"]
    quantity: Decimal
    limit_price: Decimal
    reduce_only: bool = False


_RISK_CODE_BY_REASON = {
    "account_identity": RiskCode.ACCOUNT,
    "trading_permission": RiskCode.ACCOUNT,
    "reconciliation_required": RiskCode.ACCOUNT,
    "insufficient_margin": RiskCode.BALANCE,
    "instrument_precision": RiskCode.INSTRUMENT,
    "emergency_stop": RiskCode.EMERGENCY_STOP,
    "stale_snapshot": RiskCode.STALE_DATA,
    "future_snapshot": RiskCode.STALE_DATA,
}


class NativeAdmission:
    """Serialize one AI proposal through engine risk and native ledger state."""

    def __init__(self, session: BybitSession, ledger: CommandLedger) -> None:
        self._session = session
        self._ledger = ledger

    def admit(
        self,
        command: OrderCommand,
        source: RiskContextSource,
        policy: RiskPolicy,
        *,
        now_ns: int,
    ) -> NativeAdmissionReceipt:
        account = self._session.require_ready()
        if command.account_ref != account.account_ref:
            raise BybitSessionUnavailable("testnet_account_mismatch")
        context = source.context_for(command)
        if not isinstance(context, RiskContext):
            raise TypeError("risk context source returned an invalid context")
        intent = order_intent(command, context)
        if context.account.account_id != account.account_ref or context.account.environment != "testnet":
            raise BybitSessionUnavailable("risk_context_identity_mismatch")
        expected_snapshot = f"{self._session.session_id}:{account.generation}:{account.reconciliation_revision}"
        if context.snapshot_id != expected_snapshot or not context.account.reconciled:
            raise BybitSessionUnavailable("risk_context_reconciliation_mismatch")
        decision = evaluate(intent, context, policy)
        reason = decision.reasons[0] if decision.reasons else None
        code = RiskCode.APPROVED if decision.approved else _RISK_CODE_BY_REASON.get(reason or "", RiskCode.LIMIT)
        account = self._session.snapshot()
        if account.reconciliation_revision <= 0:
            raise BybitSessionUnavailable("testnet_reconciliation_missing")
        evaluated_at_ns = now_ns
        expires_at_ns = (
            decision.approved_plan.expires_at_ms * 1_000_000 if decision.approved_plan is not None else now_ns + 1
        )
        reservation_price = context.market.executable_price
        record = self._ledger.admit_native(
            command,
            self._session.session_id,
            account.generation,
            account.reconciliation_revision,
            decision.approved,
            code,
            policy_fingerprint=_fingerprint_policy(policy),
            context_fingerprint=_fingerprint_context(context),
            evaluated_at_ns=evaluated_at_ns,
            expires_at_ns=expires_at_ns,
            reservation_price=reservation_price,
        )
        if not decision.approved:
            return NativeAdmissionReceipt(record, decision.reasons, None)
        claimed, record = self._ledger.claim_native_dispatch(
            record.id,
            self._session.session_id,
            account.generation,
            account.reconciliation_revision,
            now_ns,
        )
        if not claimed or record.state is not CommandState.DISPATCHING:
            raise BybitSessionUnavailable("native_dispatch_claim_unavailable")
        return NativeAdmissionReceipt(
            record,
            (),
            NativeDispatchClaim(
                record.id,
                record.native_client_order_id,
                account.generation,
                account.reconciliation_revision,
            ),
        )

    def admit_proposal(
        self,
        proposal: NativeProposal,
        source: RiskContextSource,
        policy: RiskPolicy,
        *,
        now_ns: int,
    ) -> NativeAdmissionReceipt:
        """Build an environment/account-scoped command before invoking ``admit``."""
        if not isinstance(proposal, NativeProposal):
            raise TypeError("typed native proposal required")
        command = OrderCommand(
            Environment.TESTNET,
            self._session.account_ref,
            proposal.request_id,
            proposal.symbol,
            Side.BUY if proposal.side == "buy" else Side.SELL,
            OrderType.LIMIT,
            proposal.quantity,
            proposal.limit_price,
            proposal.reduce_only,
        )
        return self.admit(command, source, policy, now_ns=now_ns)


def _fingerprint_policy(policy: RiskPolicy) -> str:
    import hashlib
    import json
    from dataclasses import asdict

    return hashlib.sha256(json.dumps(asdict(policy), default=str, sort_keys=True).encode("utf-8")).hexdigest()


def _fingerprint_context(context: RiskContext) -> str:
    import hashlib
    import json

    return hashlib.sha256(json.dumps(context, default=str, sort_keys=True).encode("utf-8")).hexdigest()


__all__ = [
    "NativeAdmission",
    "NativeAdmissionReceipt",
    "NativeDispatchClaim",
    "NativeProposal",
    "RiskContextSource",
]
