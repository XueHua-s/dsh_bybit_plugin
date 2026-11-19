"""Host-owned, signed GET-only Bybit Testnet provider.

This module deliberately has no submit/cancel/account-setting method. Credentials
are resolved by an injected host boundary and are never part of profile DTOs.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from email.message import Message
from typing import Protocol
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .bybit_preflight import ProfileBinding, ProviderUnavailable, ReadOnlyTestnetProvider

TESTNET_HOST = "api-testnet.bybit.com"
TESTNET_ENDPOINT = f"https://{TESTNET_HOST}"
_RECV_WINDOW_MS = 5_000
_MAX_RESPONSE_BYTES = 1_000_000
_MAX_REPORT_PAGES = 10


@dataclass(frozen=True, repr=False)
class BybitCredential:
    """Short-lived secret material delivered only by a trusted host resolver."""

    api_key: str
    api_secret: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if (
            not isinstance(self.api_key, str)
            or not 8 <= len(self.api_key) <= 128
            or any(char.isspace() for char in self.api_key)
        ):
            raise ValueError("invalid api key")
        if not isinstance(self.api_secret, bytes) or not 16 <= len(self.api_secret) <= 256:
            raise ValueError("invalid api secret")
        if any(byte < 33 or byte > 126 for byte in self.api_secret):
            raise ValueError("invalid api secret")


class CredentialResolver(Protocol):
    """Host-owned credential lookup; implementations must not use model input."""

    def resolve(self, profile_ref: str) -> BybitCredential | None: ...


class ReadTransport(Protocol):
    """Only the fixed GET primitive needed by this provider."""

    def get(
        self,
        url: str,
        query: str,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> bytes: ...


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req: Request, fp: object, code: int, msg: str, headers: Message, newurl: str) -> None:
        raise ProviderUnavailable("redirect_denied")


class UrllibReadTransport:
    """Bounded HTTPS GET transport with exact host and redirect denial."""

    def __init__(self, max_response_bytes: int = _MAX_RESPONSE_BYTES) -> None:
        if not 1_024 <= max_response_bytes <= 10_000_000:
            raise ValueError("invalid response cap")
        self._max_response_bytes = max_response_bytes
        self._opener = build_opener(_NoRedirect)

    def get(
        self,
        url: str,
        query: str,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> bytes:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname != TESTNET_HOST or parsed.username or parsed.password:
            raise ProviderUnavailable("endpoint_denied")
        if parsed.path != "/v5/" + parsed.path.removeprefix("/v5/") or not parsed.path.startswith("/v5/"):
            raise ProviderUnavailable("path_denied")
        target = f"{url}?{query}" if query else url
        request = Request(target, method="GET", headers=dict(headers))
        try:
            with self._opener.open(request, timeout=timeout_seconds) as response:
                payload = response.read(self._max_response_bytes + 1)
        except ProviderUnavailable:
            raise
        except Exception:  # noqa: BLE001 - transport is a secret-bearing boundary; sanitize all failures
            raise ProviderUnavailable("transport_failed") from None
        if len(payload) > self._max_response_bytes:
            raise ProviderUnavailable("response_too_large")
        return payload


def _canonical_query(params: Mapping[str, str | int]) -> str:
    return urlencode(sorted((key, str(value)) for key, value in params.items()), doseq=False)


def _decimal_text(value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ProviderUnavailable("numeric_field_invalid")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ProviderUnavailable("numeric_field_invalid") from None
    if not parsed.is_finite() or parsed < 0 or parsed > Decimal("1e30"):
        raise ProviderUnavailable("numeric_field_invalid")
    return format(parsed, "f")


def _positive_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ProviderUnavailable("integer_field_invalid")
    try:
        result = int(value)
    except ValueError:
        raise ProviderUnavailable("integer_field_invalid") from None
    if result <= 0:
        raise ProviderUnavailable("integer_field_invalid")
    return result


def _timestamp_ms(value: object) -> int:
    """Normalize the API key expiry's epoch or timezone-aware ISO 8601 form."""
    if isinstance(value, int) and not isinstance(value, bool):
        return _positive_int(value)
    if isinstance(value, str) and value.isdigit():
        return _positive_int(value)
    if not isinstance(value, str):
        raise ProviderUnavailable("timestamp_field_invalid")
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise ValueError
        timestamp_ms = int(parsed.timestamp() * 1_000)
    except (ValueError, OverflowError):
        raise ProviderUnavailable("timestamp_field_invalid") from None
    if timestamp_ms <= 0:
        raise ProviderUnavailable("timestamp_field_invalid")
    return timestamp_ms


def _flag(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return value == 1
    raise ProviderUnavailable("boolean_field_invalid")


class BybitReadOnlyProvider(ReadOnlyTestnetProvider):
    """Named Bybit Testnet reads mapped into the preflight projection schema."""

    def __init__(
        self,
        resolver: CredentialResolver,
        transport: ReadTransport,
        clock_ms: Callable[[], int] | None = None,
        timeout_seconds: float = 5.0,
    ) -> None:
        if not 0.1 <= timeout_seconds <= 10:
            raise ValueError("invalid timeout")
        self._resolver = resolver
        self._transport = transport
        self._clock_ms = clock_ms or (lambda: time.time_ns() // 1_000_000)
        self._timeout_seconds = timeout_seconds

    def get_api_key_evidence(self, profile: ProfileBinding, timeout_seconds: float) -> Mapping[str, object]:
        result = self._read(profile, "/v5/user/query-api", {})
        return {
            "user_id": self._digits(result.get("userID")),
            "parent_uid": self._optional_digits(result.get("parentUID", result.get("parentUid"))),
            "is_master": _flag(result.get("isMaster", result.get("is_master", False))),
            "read_only": _flag(result.get("readOnly")),
            "unified": _flag(result.get("unified")),
            "expires_at_ms": _timestamp_ms(result.get("expiredAt")),
            "ip_bindings": self._ips(result.get("ips")),
            "permissions": self._permissions(result.get("permissions")),
        }

    def get_wallet_evidence(
        self, profile: ProfileBinding, account_type: str, timeout_seconds: float
    ) -> Mapping[str, object]:
        if account_type != "UNIFIED":
            raise ProviderUnavailable("account_type_denied")
        result = self._read(profile, "/v5/account/wallet-balance", {"accountType": account_type})
        rows = result.get("list")
        if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], Mapping):
            raise ProviderUnavailable("wallet_result_invalid")
        account = rows[0]
        return {
            "observed_at_ms": self._now(),
            "account_type": account_type,
            "total_equity_usdt": _decimal_text(account.get("totalEquity")),
            "available_margin_usdt": _decimal_text(account.get("totalAvailableBalance")),
        }

    def get_linear_instrument_evidence(
        self, profile: ProfileBinding, symbol: str, timeout_seconds: float
    ) -> Mapping[str, object]:
        if not symbol.isalnum():
            raise ProviderUnavailable("symbol_invalid")
        result = self._read(profile, "/v5/market/instruments-info", {"category": "linear", "symbol": symbol})
        rows = result.get("list")
        if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], Mapping):
            raise ProviderUnavailable("instrument_result_invalid")
        row = rows[0]
        price_filter = row.get("priceFilter")
        lot_filter = row.get("lotSizeFilter")
        if not isinstance(price_filter, Mapping) or not isinstance(lot_filter, Mapping):
            raise ProviderUnavailable("instrument_rules_missing")
        return {
            "symbol": row.get("symbol"),
            "observed_at_ms": self._now(),
            "tick_size": _decimal_text(price_filter.get("tickSize")),
            "quantity_step": _decimal_text(lot_filter.get("qtyStep")),
            "minimum_quantity": _decimal_text(lot_filter.get("minOrderQty")),
            "minimum_notional_usdt": _decimal_text(lot_filter.get("minNotionalValue", "0")),
        }

    def get_initial_report_coverage(
        self, profile: ProfileBinding, symbol: str, timeout_seconds: float
    ) -> Mapping[str, object]:
        self._count_pages(profile, "/v5/order/realtime", {"category": "linear", "symbol": symbol})
        self._count_pages(profile, "/v5/position/list", {"category": "linear", "symbol": symbol})
        self._count_pages(profile, "/v5/execution/list", {"category": "linear", "symbol": symbol})
        return {
            "symbol": symbol,
            "observed_at_ms": self._now(),
            "orders_complete": True,
            "positions_complete": True,
            "executions_complete": True,
            "pagination_complete": True,
            "skipped_symbols": [],
        }

    def _read(self, profile: ProfileBinding, path: str, params: Mapping[str, str]) -> Mapping[str, object]:
        if profile.environment != "testnet" or profile.category != "linear" or profile.endpoint != TESTNET_ENDPOINT:
            raise ProviderUnavailable("profile_denied")
        if path not in {
            "/v5/user/query-api",
            "/v5/account/wallet-balance",
            "/v5/market/instruments-info",
            "/v5/order/realtime",
            "/v5/position/list",
            "/v5/execution/list",
        }:
            raise ProviderUnavailable("path_denied")
        credential = self._resolver.resolve(profile.profile_ref)
        if credential is None:
            raise ProviderUnavailable("credential_unavailable")
        query = _canonical_query(params)
        timestamp = str(self._now())
        recv_window = str(_RECV_WINDOW_MS)
        payload = timestamp + credential.api_key + recv_window + query
        signature = hmac.new(credential.api_secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        headers = {
            "X-BAPI-API-KEY": credential.api_key,
            "X-BAPI-SIGN": signature,
            "X-BAPI-SIGN-TYPE": "2",
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-RECV-WINDOW": recv_window,
        }
        body = self._transport.get(profile.endpoint + path, query, headers, self._timeout_seconds)
        try:
            document = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ProviderUnavailable("response_invalid") from None
        if not isinstance(document, Mapping) or document.get("retCode") != 0:
            raise ProviderUnavailable("exchange_read_rejected")
        result = document.get("result")
        if not isinstance(result, Mapping):
            raise ProviderUnavailable("response_result_invalid")
        return result

    def _count_pages(self, profile: ProfileBinding, path: str, params: Mapping[str, str]) -> int:
        cursor: str | None = None
        count = 0
        for _ in range(_MAX_REPORT_PAGES):
            request_params = dict(params)
            if cursor:
                request_params["cursor"] = cursor
            result = self._read(profile, path, request_params)
            rows = result.get("list")
            if not isinstance(rows, list):
                raise ProviderUnavailable("report_result_invalid")
            count += len(rows)
            next_cursor = result.get("nextPageCursor")
            if next_cursor in (None, ""):
                return count
            if not isinstance(next_cursor, str) or next_cursor == cursor:
                raise ProviderUnavailable("pagination_invalid")
            cursor = next_cursor
        raise ProviderUnavailable("pagination_limit")

    def _now(self) -> int:
        value = self._clock_ms()
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ProviderUnavailable("clock_invalid")
        return value

    @staticmethod
    def _digits(value: object) -> str:
        if not isinstance(value, (str, int)) or isinstance(value, bool) or not str(value).isdigit():
            raise ProviderUnavailable("identity_field_invalid")
        return str(value)

    @staticmethod
    def _optional_digits(value: object) -> str | None:
        if value in (None, ""):
            return None
        return BybitReadOnlyProvider._digits(value)

    @staticmethod
    def _ips(value: object) -> list[str]:
        if value in (None, ""):
            return []
        candidates = value.split(",") if isinstance(value, str) else value
        if not isinstance(candidates, list) or len(candidates) > 32:
            raise ProviderUnavailable("ip_field_invalid")
        if any(not isinstance(item, str) or len(item) > 64 for item in candidates):
            raise ProviderUnavailable("ip_field_invalid")
        bindings = [item.strip() for item in candidates if item.strip()]
        if "*" in bindings:
            if bindings == ["*"]:
                return []
            raise ProviderUnavailable("ip_field_invalid")
        return bindings

    @staticmethod
    def _permissions(value: object) -> list[str]:
        if not isinstance(value, Mapping):
            return ["read"]
        normalized = {"read"}
        for raw_key, raw_value in value.items():
            if not isinstance(raw_key, str):
                raise ProviderUnavailable("permission_field_invalid")
            key = raw_key.lower()
            values = raw_value if isinstance(raw_value, list) else [raw_value]
            active = [item for item in values if item not in (None, "", [], {}) and item is not False and item != 0]
            if not active:
                continue
            labels = [raw_key.lower()]
            labels.extend(item.lower() for item in active if isinstance(item, str))
            joined = " ".join(labels)
            if "withdraw" in joined:
                normalized.add("withdraw")
            elif "transfer" in joined:
                normalized.add("transfer")
            elif key in {"contracttrade", "derivativetrade", "lineartrade"}:
                if all(isinstance(item, str) and item.lower() in {"order", "position"} for item in active):
                    normalized.add("linear_trade")
                else:
                    normalized.add("unknown:" + raw_key[:48])
            elif key in {"wallet", "read"} and all(
                isinstance(item, str) and item.lower() in {"accountbalance", "accountinfo", "read"} for item in active
            ):
                continue
            else:
                normalized.add("unknown:" + raw_key[:48])
        return sorted(normalized)
