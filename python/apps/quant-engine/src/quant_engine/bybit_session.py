"""Engine-owned Testnet account session and reconciliation gate.

The session owns only opaque account identity and redacted reconciliation
projections.  It never resolves credentials or performs exchange IO; a future
host adapter may feed validated evidence into this boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Final

from quant_data.commands import Environment, LedgerConflict, OrderCommand
from quant_data.reconciliation_store import (
    AccountSessionRecord,
    ReconciliationEvidence,
    ReconciliationRecord,
    ReconciliationStore,
)
from quant_execution.bybit_preflight import (
    PreflightEvidence,
    PreflightStatus,
    ProfileBinding,
    ReadOnlyTestnetProvider,
    run_testnet_preflight,
)
from quant_risk.models import OrderIntent, RiskContext
from sqlalchemy.orm import Session, sessionmaker

from .bybit_profiles import TrustedBybitProfile

_NATIVE_ENV: Final[Environment] = Environment.TESTNET


class BybitSessionUnavailable(RuntimeError):
    """A fixed, safe session boundary failure."""


@dataclass(frozen=True)
class BybitSessionStatus:
    """Credential-free projection suitable for a health endpoint."""

    session_id: str
    account_ref: str
    generation: int
    reconciliation_revision: int
    protected: bool
    status: str
    ready: bool
    reason: str | None


class BybitSession:
    """One Testnet Linear account generation owned by the engine process."""

    def __init__(
        self,
        sessions: sessionmaker[Session],
        *,
        session_id: str,
        account_ref: str,
        profile: TrustedBybitProfile,
        config_fingerprint: str,
    ) -> None:
        if profile.environment != "testnet" or profile.category != "linear":
            raise ValueError("Testnet Linear profile required")
        self._sessions = sessions
        self.session_id = session_id
        self.account_ref = account_ref
        self.profile = profile
        self._store = ReconciliationStore(sessions)
        self._account: AccountSessionRecord | None = None
        self._preflight: PreflightEvidence | None = None
        self._config_fingerprint = config_fingerprint

    def open(self) -> BybitSessionStatus:
        """Open or verify the durable account binding; starts protected."""
        self._account = self._store.open_session(
            self.session_id,
            self.account_ref,
            self._config_fingerprint,
            expected_uid=self.profile.expected_uid,
            category="linear",
        )
        return self.status()

    def begin_generation(self) -> BybitSessionStatus:
        account = self._require_account()
        self._account = self._store.begin_generation(self.session_id, account.generation)
        return self.status()

    def preflight(self, provider: ReadOnlyTestnetProvider, symbol: str, now_ms: int) -> PreflightEvidence:
        """Run fixed GET-only evidence checks; never returns order authority."""
        binding = ProfileBinding(
            self.profile.profile_ref,
            self.profile.expected_uid,
            self.profile.expected_parent_uid,
            self.profile.environment,
            self.profile.category,
            self.profile.endpoint,
        )
        self._preflight = run_testnet_preflight(binding, provider, symbol, now_ms)
        return self._preflight

    def record_reconciliation(self, evidence: ReconciliationEvidence) -> ReconciliationRecord:
        account = self._require_account()
        if evidence.session_id != self.session_id or evidence.generation != account.generation:
            raise LedgerConflict("reconciliation account generation mismatch")
        record = self._store.record(evidence)
        self._account = self._store.account_session(self.session_id)
        return record

    def activate(self, revision: int, activated_at_ns: int) -> BybitSessionStatus:
        account = self._require_account()
        self._account = self._store.activate(self.session_id, account.generation, revision, activated_at_ns)
        return self.status()

    def snapshot(self) -> AccountSessionRecord:
        self._account = self._store.account_session(self.session_id)
        return self._account

    def latest_reconciliation(self) -> ReconciliationRecord:
        return self._store.latest(self.session_id)

    def status(self) -> BybitSessionStatus:
        account = self._require_account()
        preflight_ready = (
            self._preflight is not None and self._preflight.status is PreflightStatus.ELIGIBLE_FOR_RECONCILIATION
        )
        return BybitSessionStatus(
            self.session_id,
            self.account_ref,
            account.generation,
            account.reconciliation_revision,
            account.protected,
            account.status,
            not account.protected and account.status == "running" and preflight_ready,
            account.protection_reason,
        )

    def require_ready(self) -> AccountSessionRecord:
        account = self._require_account()
        if account.protected or account.status != "running":
            raise BybitSessionUnavailable("testnet_session_not_ready")
        if self._preflight is None:
            raise BybitSessionUnavailable("testnet_preflight_missing")
        if self._preflight.status is not PreflightStatus.ELIGIBLE_FOR_RECONCILIATION:
            raise BybitSessionUnavailable("testnet_preflight_denied")
        return account

    def _require_account(self) -> AccountSessionRecord:
        if self._account is None:
            raise BybitSessionUnavailable("testnet_session_not_open")
        return self._account


def order_intent(command: OrderCommand, context: RiskContext) -> OrderIntent:
    """Convert a server-owned command to the evaluator's typed intent."""
    if command.environment is not _NATIVE_ENV:
        raise ValueError("native admission requires Testnet")
    if command.order_type.value != "limit" or command.limit_price is None:
        raise ValueError("native admission currently requires limit orders")
    return OrderIntent(
        command.request_id,
        command.symbol,
        "BUY" if command.side.value == "buy" else "SELL",
        command.quantity,
        command.limit_price,
        Decimal(1),
    )


__all__ = ["BybitSession", "BybitSessionStatus", "BybitSessionUnavailable", "order_intent"]
