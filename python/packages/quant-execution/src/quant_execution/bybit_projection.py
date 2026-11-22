"""Strict, secret-free projections for a trusted Bybit Testnet read provider."""

from __future__ import annotations

import ipaddress
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


class ProjectionError(ValueError):
    """A payload failed a fixed schema rule; message contains no source data."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _mapping(value: object, required: frozenset[str], optional: frozenset[str] = frozenset()) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise ProjectionError("schema_invalid")
    keys = frozenset(value)
    if not required <= keys or not keys <= required | optional:
        raise ProjectionError("schema_invalid")
    return value


def _text(value: object, code: str = "schema_invalid") -> str:
    if not isinstance(value, str) or not value or len(value) > 128:
        raise ProjectionError(code)
    return value


def _boolean(value: object) -> bool:
    if not isinstance(value, bool):
        raise ProjectionError("schema_invalid")
    return value


def _integer(value: object, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ProjectionError("schema_invalid")
    return value


def _decimal(value: object, *, minimum: Decimal = Decimal(0)) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ProjectionError("schema_invalid")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ProjectionError("schema_invalid") from None
    if not parsed.is_finite() or parsed < minimum or parsed > Decimal("1e30"):
        raise ProjectionError("schema_invalid")
    return parsed


@dataclass(frozen=True)
class AccountKeyEvidence:
    user_id: str
    parent_uid: str | None
    is_master: bool
    read_only: bool
    unified: bool
    expires_at_ms: int
    ip_bindings: tuple[str, ...]
    permissions: frozenset[str]

    @classmethod
    def parse(cls, raw: object) -> AccountKeyEvidence:
        row = _mapping(
            raw,
            frozenset({"user_id", "is_master", "read_only", "unified", "expires_at_ms", "ip_bindings", "permissions"}),
            frozenset({"parent_uid"}),
        )
        parent = row.get("parent_uid")
        if parent is not None and (not isinstance(parent, str) or not parent.isdigit()):
            raise ProjectionError("schema_invalid")
        bindings = row["ip_bindings"]
        permissions = row["permissions"]
        if not isinstance(bindings, (tuple, list)) or not all(
            isinstance(item, str) and len(item) <= 64 for item in bindings
        ):
            raise ProjectionError("schema_invalid")
        try:
            parsed_bindings = tuple(ipaddress.ip_address(item) for item in bindings)
        except ValueError:
            raise ProjectionError("schema_invalid") from None
        if any(item.is_unspecified or item.is_multicast for item in parsed_bindings):
            raise ProjectionError("schema_invalid")
        if not isinstance(permissions, (tuple, list, set, frozenset)) or not all(
            isinstance(item, str) for item in permissions
        ):
            raise ProjectionError("schema_invalid")
        normalized_permissions = frozenset(permissions)
        if len(normalized_permissions) != len(permissions):
            raise ProjectionError("schema_invalid")
        return cls(
            _text(row["user_id"]),
            parent,
            _boolean(row["is_master"]),
            _boolean(row["read_only"]),
            _boolean(row["unified"]),
            _integer(row["expires_at_ms"], minimum=1),
            tuple(bindings),
            normalized_permissions,
        )


@dataclass(frozen=True)
class WalletEvidence:
    observed_at_ms: int
    account_type: str
    total_equity_usdt: Decimal
    available_margin_usdt: Decimal

    @classmethod
    def parse(cls, raw: object) -> WalletEvidence:
        row = _mapping(raw, frozenset({"observed_at_ms", "account_type", "total_equity_usdt", "available_margin_usdt"}))
        account_type = _text(row["account_type"])
        if account_type != "UNIFIED":
            raise ProjectionError("account_type_unsupported")
        return cls(
            _integer(row["observed_at_ms"], minimum=1),
            account_type,
            _decimal(row["total_equity_usdt"]),
            _decimal(row["available_margin_usdt"]),
        )


@dataclass(frozen=True)
class InstrumentEvidence:
    symbol: str
    observed_at_ms: int
    tick_size: Decimal
    quantity_step: Decimal
    minimum_quantity: Decimal
    minimum_notional_usdt: Decimal

    @classmethod
    def parse(cls, raw: object, expected_symbol: str) -> InstrumentEvidence:
        row = _mapping(
            raw,
            frozenset(
                {"symbol", "observed_at_ms", "tick_size", "quantity_step", "minimum_quantity", "minimum_notional_usdt"}
            ),
        )
        symbol = _text(row["symbol"])
        if symbol != expected_symbol:
            raise ProjectionError("instrument_mismatch")
        return cls(
            symbol,
            _integer(row["observed_at_ms"], minimum=1),
            _decimal(row["tick_size"], minimum=Decimal("1e-18")),
            _decimal(row["quantity_step"], minimum=Decimal("1e-18")),
            _decimal(row["minimum_quantity"], minimum=Decimal("1e-18")),
            _decimal(row["minimum_notional_usdt"]),
        )


@dataclass(frozen=True)
class ReportCoverage:
    symbol: str
    observed_at_ms: int
    orders_complete: bool
    positions_complete: bool
    executions_complete: bool
    pagination_complete: bool
    skipped_symbols: tuple[str, ...]

    @classmethod
    def parse(cls, raw: object, expected_symbol: str) -> ReportCoverage:
        row = _mapping(
            raw,
            frozenset(
                {
                    "symbol",
                    "observed_at_ms",
                    "orders_complete",
                    "positions_complete",
                    "executions_complete",
                    "pagination_complete",
                    "skipped_symbols",
                }
            ),
        )
        skipped = row["skipped_symbols"]
        if not isinstance(skipped, (tuple, list)) or not all(isinstance(item, str) for item in skipped):
            raise ProjectionError("schema_invalid")
        symbol = _text(row["symbol"])
        if symbol != expected_symbol:
            raise ProjectionError("instrument_mismatch")
        return cls(
            symbol,
            _integer(row["observed_at_ms"], minimum=1),
            _boolean(row["orders_complete"]),
            _boolean(row["positions_complete"]),
            _boolean(row["executions_complete"]),
            _boolean(row["pagination_complete"]),
            tuple(skipped),
        )
