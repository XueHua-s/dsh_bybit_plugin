"""Explicit, credential-handle-only Nautilus configuration for Bybit Testnet.

This module validates the boundary and constructs immutable Nautilus config
objects. It does not create a live client, resolve ambient environment
variables, persist credentials, or submit an order.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol

from nautilus_trader.adapters.bybit.config import (
    BybitDataClientConfig,
    BybitExecClientConfig,
)
from nautilus_trader.core.nautilus_pyo3 import BybitEnvironment, BybitProductType

_PROFILE_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")


def _is_valid_uid(value: object) -> bool:
    return isinstance(value, str) and value.isdigit() and 1 <= len(value) <= 32


@dataclass(frozen=True)
class BybitCredentialMaterial:
    """Short-lived secret material supplied by an already-authorized host."""

    api_key: str = field(repr=False)
    api_secret: str = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.api_key, str) or not self.api_key:
            raise ValueError("api key handle is missing")
        if not isinstance(self.api_secret, str) or not self.api_secret:
            raise ValueError("api secret handle is missing")


class BybitCredentialResolver(Protocol):
    """Host-owned lookup; implementations must not read model or env input."""

    def resolve(self, profile_ref: str) -> BybitCredentialMaterial | None: ...


@dataclass(frozen=True)
class BybitAccountBinding:
    """Non-secret identity facts required before constructing a native config."""

    profile_ref: str
    expected_uid: str
    expected_parent_uid: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.profile_ref, str) or _PROFILE_REF.fullmatch(self.profile_ref) is None:
            raise ValueError("invalid profile reference")
        if not _is_valid_uid(self.expected_uid):
            raise ValueError("invalid expected uid")
        if self.expected_parent_uid is not None and not _is_valid_uid(self.expected_parent_uid):
            raise ValueError("invalid expected parent uid")


@dataclass(frozen=True, repr=False)
class NativeBybitConfigs:
    """Credential-bearing configs with a redacted wrapper representation.

    Nautilus config objects include API secrets in their own repr. Callers must
    pass them directly to a trusted factory and must never log or serialize
    either underlying config.
    """

    data: BybitDataClientConfig
    execution: BybitExecClientConfig

    def __repr__(self) -> str:
        return "NativeBybitConfigs(data=<redacted>, execution=<redacted>)"


def build_testnet_linear_configs(
    binding: BybitAccountBinding,
    credentials: BybitCredentialMaterial,
) -> NativeBybitConfigs:
    """Build explicit Testnet Linear configs from trusted, in-memory material.

    The returned configs are inert until a separately owned Nautilus runtime
    creates clients. Mainnet, Spot and implicit environment credentials cannot
    enter this function.
    """

    if not isinstance(binding, BybitAccountBinding) or not isinstance(credentials, BybitCredentialMaterial):
        raise TypeError("trusted account binding and credential material are required")
    common = {
        "api_key": credentials.api_key,
        "api_secret": credentials.api_secret,
        "environment": BybitEnvironment.TESTNET,
        "product_types": (BybitProductType.LINEAR,),
    }
    return NativeBybitConfigs(
        data=BybitDataClientConfig(**common),
        execution=BybitExecClientConfig(**common),
    )


def resolve_testnet_credentials(
    binding: BybitAccountBinding,
    resolver: BybitCredentialResolver,
) -> BybitCredentialMaterial:
    """Resolve one opaque profile through the host-owned credential boundary."""

    if not isinstance(binding, BybitAccountBinding):
        raise TypeError("trusted account binding is required")
    resolve = getattr(resolver, "resolve", None)
    if not callable(resolve):
        raise TypeError("host credential resolver is invalid")
    material = resolve(binding.profile_ref)
    if material is None:
        raise LookupError("credential profile unavailable")
    if not isinstance(material, BybitCredentialMaterial):
        raise TypeError("credential resolver returned an invalid material type")
    return material
