"""Fixture-only preflight acceptance: named reads, fixed endpoint, sanitized status."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from inspect import signature

import pytest
from quant_execution.bybit_preflight import (
    PreflightEvidence,
    PreflightStatus,
    ProfileBinding,
    ProviderUnavailable,
    run_testnet_preflight,
)

NOW = 1_800_000_000_000
PROFILE = ProfileBinding("test-profile", "81234567", "81230000", "testnet", "linear", "https://api-testnet.bybit.com")


@dataclass
class FixtureProvider:
    operations: list[str] = field(default_factory=list)
    account: Mapping[str, object] | None = None
    wallet: Mapping[str, object] | None = None
    instrument: Mapping[str, object] | None = None
    reports: Mapping[str, object] | None = None
    error: Exception | None = None

    def _return(self, operation: str, value: Mapping[str, object] | None) -> Mapping[str, object]:
        self.operations.append(operation)
        if self.error is not None:
            raise self.error
        if value is None:
            raise RuntimeError("fixture missing")
        return value

    def get_api_key_evidence(self, profile: ProfileBinding, timeout_seconds: float) -> Mapping[str, object]:
        assert profile.endpoint == "https://api-testnet.bybit.com"
        assert timeout_seconds == 5.0
        return self._return("GET /v5/user/query-api", self.account)

    def get_wallet_evidence(
        self, profile: ProfileBinding, account_type: str, timeout_seconds: float
    ) -> Mapping[str, object]:
        assert account_type == "UNIFIED"
        return self._return("GET /v5/account/wallet-balance", self.wallet)

    def get_linear_instrument_evidence(
        self, profile: ProfileBinding, symbol: str, timeout_seconds: float
    ) -> Mapping[str, object]:
        assert symbol == "BTCUSDT"
        return self._return("GET /v5/market/instruments-info", self.instrument)

    def get_initial_report_coverage(
        self, profile: ProfileBinding, symbol: str, timeout_seconds: float
    ) -> Mapping[str, object]:
        assert symbol == "BTCUSDT"
        return self._return("GET /v5/order/realtime + /v5/position/list + /v5/execution/list", self.reports)


def _provider() -> FixtureProvider:
    return FixtureProvider(
        account={
            "user_id": "81234567",
            "parent_uid": "81230000",
            "is_master": False,
            "read_only": False,
            "unified": True,
            "expires_at_ms": NOW + 86_400_000,
            "ip_bindings": ["203.0.113.4"],
            "permissions": ["read", "linear_trade"],
        },
        wallet={
            "observed_at_ms": NOW,
            "account_type": "UNIFIED",
            "total_equity_usdt": "0",
            "available_margin_usdt": "0",
        },
        instrument={
            "symbol": "BTCUSDT",
            "observed_at_ms": NOW,
            "tick_size": "0.1",
            "quantity_step": "0.001",
            "minimum_quantity": "0.001",
            "minimum_notional_usdt": "5",
        },
        reports={
            "symbol": "BTCUSDT",
            "observed_at_ms": NOW,
            "orders_complete": True,
            "positions_complete": True,
            "executions_complete": True,
            "pagination_complete": True,
            "skipped_symbols": [],
        },
    )


def test_eligible_means_reconciliation_only_and_zero_funds_are_visible() -> None:
    provider = _provider()
    result = run_testnet_preflight(PROFILE, provider, "BTCUSDT", NOW)

    assert result.status is PreflightStatus.ELIGIBLE_FOR_RECONCILIATION
    assert result.funds_observed_positive is False
    assert result.order_submission_allowed is False
    assert result.total_equity_usdt == "0"
    assert all(operation.startswith("GET ") for operation in provider.operations)
    assert "ready_to_trade" not in result.__dict__


def test_identity_permission_staleness_and_report_gaps_deny() -> None:
    provider = _provider()
    assert run_testnet_preflight(
        ProfileBinding("test-profile", "999999999", "81230000", "testnet", "linear", PROFILE.endpoint),
        provider,
        "BTCUSDT",
        NOW,
    ).reason_codes == ("identity_mismatch",)

    for permission in ("withdraw", "transfer", "unknown:spottrade"):
        provider = _provider()
        provider.account = {**provider.account, "permissions": ["read", permission]} if provider.account else None
        assert (
            "permissions_unknown_or_excessive" in run_testnet_preflight(PROFILE, provider, "BTCUSDT", NOW).reason_codes
        )

    provider = _provider()
    provider.wallet = {**provider.wallet, "observed_at_ms": NOW - 30_001} if provider.wallet else None
    assert "source_stale_or_future" in run_testnet_preflight(PROFILE, provider, "BTCUSDT", NOW).reason_codes

    provider = _provider()
    provider.reports = {**provider.reports, "pagination_complete": False} if provider.reports else None
    assert "reports_incomplete" in run_testnet_preflight(PROFILE, provider, "BTCUSDT", NOW).reason_codes


def test_parent_identity_is_checked_when_a_trusted_binding_is_available() -> None:
    provider = _provider()
    selected_subaccount_only = ProfileBinding("test-profile", "81234567", None, "testnet", "linear", PROFILE.endpoint)
    assert run_testnet_preflight(selected_subaccount_only, provider, "BTCUSDT", NOW).status is (
        PreflightStatus.ELIGIBLE_FOR_RECONCILIATION
    )

    provider = _provider()
    wrong_parent = ProfileBinding("test-profile", "81234567", "99999999", "testnet", "linear", PROFILE.endpoint)
    assert run_testnet_preflight(wrong_parent, provider, "BTCUSDT", NOW).reason_codes == ("identity_mismatch",)


def test_expired_read_only_or_unbound_keys_are_denied() -> None:
    for changes, expected_reason in (
        ({"read_only": True}, "trading_permission_missing"),
        ({"ip_bindings": []}, "ip_binding_missing"),
        ({"expires_at_ms": NOW}, "key_expired"),
    ):
        provider = _provider()
        assert provider.account is not None
        provider.account = {**provider.account, **changes}
        result = run_testnet_preflight(PROFILE, provider, "BTCUSDT", NOW)
        assert result.status is PreflightStatus.DENIED
        assert expected_reason in result.reason_codes


def test_order_submission_is_not_a_caller_selectable_result() -> None:
    assert "order_submission_allowed" not in signature(PreflightEvidence).parameters


def test_provider_failure_is_sanitized_and_invalid_profile_does_not_call_provider() -> None:
    provider = _provider()
    provider.error = ProviderUnavailable("secret URL and credentials")
    result = run_testnet_preflight(PROFILE, provider, "BTCUSDT", NOW)
    assert result.status is PreflightStatus.UNAVAILABLE
    assert result.reason_codes == ("provider_read_failed",)
    assert "secret" not in repr(result)

    provider = _provider()
    invalid = ProfileBinding("bad-profile", "81234567", "81230000", "mainnet", "spot", "https://api.bybit.com")
    result = run_testnet_preflight(invalid, provider, "BTCUSDT", NOW)
    assert result.status is PreflightStatus.DENIED
    assert provider.operations == []


@pytest.mark.parametrize("symbol", ["", "BTC USDT", "BTC/USDT"])
def test_symbol_is_strict_and_never_becomes_a_provider_path(symbol: str) -> None:
    provider = _provider()
    result = run_testnet_preflight(PROFILE, provider, symbol, NOW)
    assert result.status is PreflightStatus.DENIED
    assert provider.operations == []
