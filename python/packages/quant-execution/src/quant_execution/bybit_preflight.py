"""Fail-closed read-only Testnet evidence collection; never order readiness."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from .bybit_projection import AccountKeyEvidence, InstrumentEvidence, ProjectionError, ReportCoverage, WalletEvidence


class PreflightStatus(StrEnum):
    DENIED = "denied"
    UNAVAILABLE = "unavailable"
    ELIGIBLE_FOR_RECONCILIATION = "eligible_for_reconciliation"


class ProviderUnavailable(RuntimeError):
    """Trusted read provider reports a fixed timeout/transport failure."""


@dataclass(frozen=True)
class ProfileBinding:
    """Minimal trusted profile projection; secret and credential objects are excluded."""

    profile_ref: str
    expected_uid: str
    expected_parent_uid: str | None
    environment: str
    category: str
    endpoint: str

    def __post_init__(self) -> None:
        if not isinstance(self.profile_ref, str) or _PROFILE_REF.fullmatch(self.profile_ref) is None:
            raise ValueError("invalid profile reference")
        if not isinstance(self.expected_uid, str) or not self.expected_uid.isdigit():
            raise ValueError("invalid expected uid")
        if self.expected_parent_uid is not None and (
            not isinstance(self.expected_parent_uid, str) or not self.expected_parent_uid.isdigit()
        ):
            raise ValueError("invalid expected parent uid")


class ReadOnlyTestnetProvider(Protocol):
    """Provider exposes named GET-only reads rather than a generic request/client."""

    def get_api_key_evidence(self, profile: ProfileBinding, timeout_seconds: float) -> Mapping[str, object]: ...

    def get_wallet_evidence(
        self, profile: ProfileBinding, account_type: str, timeout_seconds: float
    ) -> Mapping[str, object]: ...

    def get_linear_instrument_evidence(
        self, profile: ProfileBinding, symbol: str, timeout_seconds: float
    ) -> Mapping[str, object]: ...

    def get_initial_report_coverage(
        self, profile: ProfileBinding, symbol: str, timeout_seconds: float
    ) -> Mapping[str, object]: ...


@dataclass(frozen=True)
class PreflightEvidence:
    status: PreflightStatus
    reason_codes: tuple[str, ...]
    profile_ref: str
    environment: str
    category: str
    total_equity_usdt: str | None = None
    available_margin_usdt: str | None = None
    funds_observed_positive: bool | None = None
    instrument: InstrumentEvidence | None = None
    order_submission_allowed: bool = field(default=False, init=False)


_ALLOWED_PERMISSIONS = frozenset({"read", "linear_trade"})
_PROFILE_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")
_MAX_AGE_MS = 30_000
_FUTURE_SKEW_MS = 5_000
_TIMEOUT_SECONDS = 5.0


def run_testnet_preflight(
    profile: ProfileBinding,
    provider: ReadOnlyTestnetProvider,
    symbol: str,
    now_ms: int,
) -> PreflightEvidence:
    """Gather only fixed Testnet reads and return redacted eligibility evidence.

    The injected provider is a trusted host boundary. This function never accepts a
    raw client, path, method, endpoint override, credential, or account policy.
    """

    if (
        profile.environment != "testnet"
        or profile.category != "linear"
        or profile.endpoint != "https://api-testnet.bybit.com"
        or not isinstance(profile.profile_ref, str)
        or _PROFILE_REF.fullmatch(profile.profile_ref) is None
        or not isinstance(profile.expected_uid, str)
        or not profile.expected_uid.isdigit()
        or not isinstance(symbol, str)
        or not symbol.isalnum()
        or not isinstance(now_ms, int)
        or isinstance(now_ms, bool)
        or now_ms <= 0
    ):
        return _result(profile, PreflightStatus.DENIED, "profile_or_request_invalid")

    try:
        account = AccountKeyEvidence.parse(provider.get_api_key_evidence(profile, _TIMEOUT_SECONDS))
        wallet = WalletEvidence.parse(provider.get_wallet_evidence(profile, "UNIFIED", _TIMEOUT_SECONDS))
        instrument = InstrumentEvidence.parse(
            provider.get_linear_instrument_evidence(profile, symbol, _TIMEOUT_SECONDS), symbol
        )
        reports = ReportCoverage.parse(provider.get_initial_report_coverage(profile, symbol, _TIMEOUT_SECONDS), symbol)
    except ProjectionError as error:
        return _result(profile, PreflightStatus.DENIED, error.code)
    except Exception:  # noqa: BLE001 -- sanitize all untrusted transport/provider failures.
        # Do not leak provider exception text, request URLs, or payloads.
        return _result(profile, PreflightStatus.UNAVAILABLE, "provider_read_failed")

    reasons: list[str] = []
    if account.user_id != profile.expected_uid or account.parent_uid != profile.expected_parent_uid:
        reasons.append("identity_mismatch")
    if account.is_master or not account.unified:
        reasons.append("account_type_unsupported")
    if account.read_only:
        reasons.append("trading_permission_missing")
    if account.permissions != _ALLOWED_PERMISSIONS:
        reasons.append("permissions_unknown_or_excessive")
    if not account.ip_bindings:
        reasons.append("ip_binding_missing")
    if account.expires_at_ms <= now_ms:
        reasons.append("key_expired")

    for observed_at in (wallet.observed_at_ms, instrument.observed_at_ms, reports.observed_at_ms):
        age = now_ms - observed_at
        if age < -_FUTURE_SKEW_MS or age > _MAX_AGE_MS:
            reasons.append("source_stale_or_future")
            break
    if (
        not all(
            (
                reports.orders_complete,
                reports.positions_complete,
                reports.executions_complete,
                reports.pagination_complete,
            )
        )
        or reports.skipped_symbols
    ):
        reasons.append("reports_incomplete")

    if reasons:
        return PreflightEvidence(
            PreflightStatus.DENIED,
            tuple(sorted(set(reasons))),
            profile.profile_ref,
            "testnet",
            "linear",
            str(wallet.total_equity_usdt),
            str(wallet.available_margin_usdt),
            wallet.total_equity_usdt > 0 and wallet.available_margin_usdt > 0,
            instrument,
        )

    return PreflightEvidence(
        PreflightStatus.ELIGIBLE_FOR_RECONCILIATION,
        (),
        profile.profile_ref,
        "testnet",
        "linear",
        str(wallet.total_equity_usdt),
        str(wallet.available_margin_usdt),
        wallet.total_equity_usdt > 0 and wallet.available_margin_usdt > 0,
        instrument,
    )


def _result(profile: ProfileBinding, status: PreflightStatus, reason: str) -> PreflightEvidence:
    profile_ref = (
        profile.profile_ref
        if isinstance(profile.profile_ref, str) and _PROFILE_REF.fullmatch(profile.profile_ref)
        else "invalid"
    )
    return PreflightEvidence(status, (reason,), profile_ref, "testnet", "linear")
