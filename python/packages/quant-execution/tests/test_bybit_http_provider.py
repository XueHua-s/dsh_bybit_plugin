"""Offline contract tests for the signed GET-only Bybit Testnet provider."""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from email.message import Message
from urllib.error import HTTPError
from urllib.request import Request

import pytest
from quant_execution.bybit_http_provider import (
    TESTNET_ENDPOINT,
    BybitCredential,
    BybitReadOnlyProvider,
    UrllibReadTransport,
    _NoRedirect,
)
from quant_execution.bybit_preflight import PreflightStatus, ProfileBinding, ProviderUnavailable, run_testnet_preflight

NOW = 1_800_000_000_000
API_KEY = "fixture-api-key"
API_SECRET = b"fixture-api-secret-is-never-real"
PROFILE = ProfileBinding("fixture-profile", "81234567", "81230000", "testnet", "linear", TESTNET_ENDPOINT)


@dataclass
class FixtureResolver:
    credential: BybitCredential | None = field(default_factory=lambda: BybitCredential(API_KEY, API_SECRET))
    references: list[str] = field(default_factory=list)

    def resolve(self, profile_ref: str) -> BybitCredential | None:
        self.references.append(profile_ref)
        return self.credential


@dataclass(frozen=True)
class RequestRecord:
    url: str
    query: str
    headers: Mapping[str, str]
    timeout: float


@dataclass
class FixtureTransport:
    responder: Callable[[str, str], Mapping[str, object]]
    calls: list[RequestRecord] = field(default_factory=list)

    def get(self, url: str, query: str, headers: Mapping[str, str], timeout_seconds: float) -> bytes:
        self.calls.append(RequestRecord(url, query, dict(headers), timeout_seconds))
        path = url.removeprefix(TESTNET_ENDPOINT)
        return json.dumps({"retCode": 0, "result": self.responder(path, query)}).encode()


def _provider(
    responder: Callable[[str, str], Mapping[str, object]] | None = None,
) -> tuple[BybitReadOnlyProvider, FixtureResolver, FixtureTransport]:
    def default_response(_path: str, _query: str) -> Mapping[str, object]:
        return {"list": [{"totalEquity": "0", "totalAvailableBalance": "0"}]}

    resolver = FixtureResolver()
    transport = FixtureTransport(responder or default_response)
    provider = BybitReadOnlyProvider(resolver, transport, clock_ms=lambda: NOW)
    return provider, resolver, transport


def test_signed_request_uses_exact_testnet_host_and_stable_v5_signature() -> None:
    provider, resolver, transport = _provider()
    provider.get_wallet_evidence(PROFILE, "UNIFIED", 5.0)

    call = transport.calls[0]
    expected = hmac.new(
        API_SECRET,
        f"{NOW}{API_KEY}5000accountType=UNIFIED".encode(),
        hashlib.sha256,
    ).hexdigest()
    assert call.url == f"{TESTNET_ENDPOINT}/v5/account/wallet-balance"
    assert call.query == "accountType=UNIFIED"
    assert call.headers["X-BAPI-API-KEY"] == API_KEY
    assert call.headers["X-BAPI-SIGN"] == expected
    assert call.headers["X-BAPI-TIMESTAMP"] == str(NOW)
    assert call.headers["X-BAPI-RECV-WINDOW"] == "5000"
    assert call.timeout == 5.0
    assert resolver.references == [PROFILE.profile_ref]
    assert not hasattr(transport, "post")


def test_named_mappings_validate_identity_wallet_instrument_and_report_pages() -> None:
    def respond(path: str, query: str) -> Mapping[str, object]:
        if path == "/v5/user/query-api":
            return {
                "userID": "81234567",
                "parentUID": "81230000",
                "isMaster": False,
                "readOnly": False,
                "unified": True,
                "expiredAt": NOW + 86_400_000,
                "ips": "203.0.113.8",
                "permissions": {"ContractTrade": ["Order"], "Wallet": ["AccountTransfer"]},
            }
        if path == "/v5/account/wallet-balance":
            return {"list": [{"totalEquity": "12.50", "totalAvailableBalance": "9.25"}]}
        if path == "/v5/market/instruments-info":
            return {
                "list": [
                    {
                        "symbol": "BTCUSDT",
                        "priceFilter": {"tickSize": "0.1"},
                        "lotSizeFilter": {"qtyStep": "0.001", "minOrderQty": "0.001", "minNotionalValue": "5"},
                    }
                ]
            }
        cursor_page = "cursor=page%2F2" in query
        if path == "/v5/order/realtime":
            return {
                "list": [{"orderId": "one"}] if cursor_page else [{"orderId": "two"}],
                **({} if cursor_page else {"nextPageCursor": "page/2"}),
            }
        if path == "/v5/position/list":
            return {"list": [{"positionIdx": 0}]}
        if path == "/v5/execution/list":
            return {"list": [{"execId": "exec"}]}
        raise AssertionError(f"unexpected named path: {path}")

    provider, _resolver, transport = _provider(respond)
    key = provider.get_api_key_evidence(PROFILE, 5.0)
    wallet = provider.get_wallet_evidence(PROFILE, "UNIFIED", 5.0)
    instrument = provider.get_linear_instrument_evidence(PROFILE, "BTCUSDT", 5.0)
    reports = provider.get_initial_report_coverage(PROFILE, "BTCUSDT", 5.0)

    assert key == {
        "user_id": "81234567",
        "parent_uid": "81230000",
        "is_master": False,
        "read_only": False,
        "unified": True,
        "expires_at_ms": NOW + 86_400_000,
        "ip_bindings": ["203.0.113.8"],
        "permissions": ["linear_trade", "read"],
    }
    assert wallet == {
        "observed_at_ms": NOW,
        "account_type": "UNIFIED",
        "total_equity_usdt": "12.50",
        "available_margin_usdt": "9.25",
    }
    assert instrument == {
        "symbol": "BTCUSDT",
        "observed_at_ms": NOW,
        "tick_size": "0.1",
        "quantity_step": "0.001",
        "minimum_quantity": "0.001",
        "minimum_notional_usdt": "5",
    }
    assert reports["pagination_complete"] is True
    assert len(transport.calls) == 7
    assert all(call.url.startswith(TESTNET_ENDPOINT + "/v5/") for call in transport.calls)


def test_read_provider_preflight_remains_non_trading_with_zero_balance() -> None:
    def respond(path: str, _query: str) -> Mapping[str, object]:
        if path == "/v5/user/query-api":
            return {
                "userID": "81234567",
                "parentUID": "81230000",
                "isMaster": False,
                "readOnly": False,
                "unified": True,
                "expiredAt": NOW + 86_400_000,
                "ips": "203.0.113.8",
                "permissions": {"ContractTrade": ["Order"]},
            }
        if path == "/v5/account/wallet-balance":
            return {"list": [{"totalEquity": "0", "totalAvailableBalance": "0"}]}
        if path == "/v5/market/instruments-info":
            return {
                "list": [
                    {
                        "symbol": "BTCUSDT",
                        "priceFilter": {"tickSize": "0.1"},
                        "lotSizeFilter": {"qtyStep": "0.001", "minOrderQty": "0.001", "minNotionalValue": "5"},
                    }
                ]
            }
        if path in {"/v5/order/realtime", "/v5/position/list", "/v5/execution/list"}:
            return {"list": []}
        raise AssertionError(f"unexpected path: {path}")

    provider, _resolver, transport = _provider(respond)
    evidence = run_testnet_preflight(PROFILE, provider, "BTCUSDT", NOW)

    assert evidence.status is PreflightStatus.ELIGIBLE_FOR_RECONCILIATION
    assert evidence.funds_observed_positive is False
    assert evidence.order_submission_allowed is False
    assert len(transport.calls) == 6


@pytest.mark.parametrize(
    "profile",
    [
        ProfileBinding("fixture-profile", "81234567", None, "live", "linear", TESTNET_ENDPOINT),
        ProfileBinding("fixture-profile", "81234567", None, "testnet", "spot", TESTNET_ENDPOINT),
        ProfileBinding("fixture-profile", "81234567", None, "testnet", "linear", "https://api.bybit.com"),
    ],
)
def test_provider_rejects_non_testnet_binding_before_credential_resolution(profile: ProfileBinding) -> None:
    provider, resolver, transport = _provider()

    with pytest.raises(ProviderUnavailable, match="profile_denied"):
        provider.get_api_key_evidence(profile, 5.0)

    assert resolver.references == []
    assert transport.calls == []


def test_provider_rejects_missing_credential_without_request() -> None:
    provider, resolver, transport = _provider()
    resolver.credential = None

    with pytest.raises(ProviderUnavailable, match="credential_unavailable"):
        provider.get_api_key_evidence(PROFILE, 5.0)

    assert resolver.references == [PROFILE.profile_ref]
    assert transport.calls == []


def test_credential_repr_does_not_disclose_fixture_material() -> None:
    rendered = repr(BybitCredential(API_KEY, API_SECRET))
    assert API_KEY not in rendered
    assert API_SECRET.decode() not in rendered


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (b"not-json", "response_invalid"),
        (b'{"retCode":10001,"retMsg":"secret response"}', "exchange_read_rejected"),
        (b'{"retCode":0,"result":[]}', "response_result_invalid"),
    ],
)
def test_provider_maps_exchange_and_decode_failures_to_fixed_codes(body: bytes, expected: str) -> None:
    class BadBodyTransport:
        def get(self, url: str, query: str, headers: Mapping[str, str], timeout_seconds: float) -> bytes:
            assert url.startswith(TESTNET_ENDPOINT)
            assert query == ""
            assert headers["X-BAPI-API-KEY"] == API_KEY
            assert timeout_seconds == 5.0
            return body

    provider = BybitReadOnlyProvider(FixtureResolver(), BadBodyTransport(), clock_ms=lambda: NOW)

    with pytest.raises(ProviderUnavailable) as error:
        provider.get_api_key_evidence(PROFILE, 5.0)

    assert str(error.value) == expected
    assert "secret response" not in str(error.value)


def test_mapping_failure_closes_instead_of_coercing_unknown_exchange_fields() -> None:
    provider, _resolver, _transport = _provider(
        lambda _path, _query: {
            "list": [
                {
                    "symbol": "BTCUSDT",
                    "priceFilter": {"tickSize": "NaN"},
                    "lotSizeFilter": {"qtyStep": "0.001", "minOrderQty": "0.001"},
                }
            ]
        }
    )

    with pytest.raises(ProviderUnavailable, match="numeric_field_invalid"):
        provider.get_linear_instrument_evidence(PROFILE, "BTCUSDT", 5.0)


def test_transport_rejects_wrong_host_path_and_redirect_without_network() -> None:
    transport = UrllibReadTransport()
    headers: Mapping[str, str] = {}
    with pytest.raises(ProviderUnavailable, match="endpoint_denied"):
        transport.get("https://api.bybit.com/v5/user/query-api", "", headers, 1.0)
    with pytest.raises(ProviderUnavailable, match="path_denied"):
        transport.get(TESTNET_ENDPOINT + "/private/key", "", headers, 1.0)

    handler = _NoRedirect()
    with pytest.raises(ProviderUnavailable, match="redirect_denied"):
        handler.redirect_request(
            Request(TESTNET_ENDPOINT), object(), 302, "found", Message(), "https://attacker.invalid/"
        )


def test_transport_enforces_response_size_and_sanitizes_transport_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    class ResponseContext(AbstractContextManager[object]):
        def __enter__(self) -> object:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, count: int) -> bytes:
            return b"x" * count

    class OversizedOpener:
        def open(self, request: Request, timeout: float) -> ResponseContext:
            assert request.get_method() == "GET"
            assert timeout == 1.0
            return ResponseContext()

    transport = UrllibReadTransport(max_response_bytes=1_024)
    monkeypatch.setattr(transport, "_opener", OversizedOpener())
    with pytest.raises(ProviderUnavailable, match="response_too_large"):
        transport.get(TESTNET_ENDPOINT + "/v5/user/query-api", "", {}, 1.0)

    class FailingOpener:
        def open(self, request: Request, timeout: float) -> object:
            assert request.get_method() == "GET"
            assert timeout == 1.0
            raise HTTPError(TESTNET_ENDPOINT, 302, "redirect with secret", Message(), None)

    monkeypatch.setattr(transport, "_opener", FailingOpener())
    with pytest.raises(ProviderUnavailable, match="transport_failed") as error:
        transport.get(TESTNET_ENDPOINT + "/v5/user/query-api", "", {}, 1.0)
    assert "secret" not in str(error.value)
