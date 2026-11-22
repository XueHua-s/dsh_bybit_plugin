"""Offline tests for the explicit Nautilus Testnet account boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import pytest
from nautilus_trader.core.nautilus_pyo3 import BybitEnvironment, BybitProductType
from quant_execution.bybit_account import (
    BybitAccountBinding,
    BybitCredentialMaterial,
    BybitCredentialResolver,
    NativeBybitConfigs,
    build_testnet_linear_configs,
    resolve_testnet_credentials,
)


def test_builds_explicit_testnet_linear_configs_without_live_io() -> None:
    binding = BybitAccountBinding("fixture-profile", "81234567", "81230000")
    material = BybitCredentialMaterial("fixture-key", "fixture-secret")

    configs = build_testnet_linear_configs(binding, material)

    assert isinstance(configs, NativeBybitConfigs)
    assert "fixture-key" not in repr(configs)
    assert "fixture-secret" not in repr(configs)
    for config in (configs.data, configs.execution):
        assert config.environment is BybitEnvironment.TESTNET
        assert config.product_types == (BybitProductType.LINEAR,)
        assert config.api_key == "fixture-key"
        assert config.api_secret == "fixture-secret"


@pytest.mark.parametrize(
    "binding",
    (
        BybitAccountBinding("test-profile", "81234567"),
        BybitAccountBinding("test-profile", "81234567", "81230000"),
    ),
)
def test_binding_does_not_widen_environment_or_category(binding: BybitAccountBinding) -> None:
    configs = build_testnet_linear_configs(binding, BybitCredentialMaterial("key", "secret"))
    assert configs.execution.environment is BybitEnvironment.TESTNET
    assert configs.execution.product_types == (BybitProductType.LINEAR,)


def test_rejects_missing_or_malformed_credentials_and_binding() -> None:
    with pytest.raises(ValueError, match="api key"):
        BybitCredentialMaterial("", "secret")
    with pytest.raises(ValueError, match="api secret"):
        BybitCredentialMaterial("key", "")
    with pytest.raises(ValueError, match="profile"):
        BybitAccountBinding("https://api.bybit.com", "81234567")
    with pytest.raises(ValueError, match="uid"):
        BybitAccountBinding("profile", "not-a-uid")
    with pytest.raises(ValueError, match="profile"):
        BybitAccountBinding(cast(str, 123), "81234567")
    with pytest.raises(ValueError, match="uid"):
        BybitAccountBinding("profile", cast(str, 123))


@dataclass
class _Resolver:
    material: BybitCredentialMaterial | None

    def resolve(self, profile_ref: str) -> BybitCredentialMaterial | None:
        assert profile_ref == "fixture-profile"
        return self.material


def test_resolution_is_opaque_and_fail_closed() -> None:
    binding = BybitAccountBinding("fixture-profile", "81234567")
    material = BybitCredentialMaterial("key", "secret")
    assert resolve_testnet_credentials(binding, _Resolver(material)) is material
    with pytest.raises(LookupError, match="unavailable"):
        resolve_testnet_credentials(binding, _Resolver(None))
    with pytest.raises(TypeError, match="binding"):
        resolve_testnet_credentials(cast(BybitAccountBinding, object()), _Resolver(material))
    with pytest.raises(TypeError, match="resolver"):
        resolve_testnet_credentials(binding, cast(BybitCredentialResolver, object()))
