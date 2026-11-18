"""Opaque Testnet profile binding rejects untrusted or cross-environment input."""

import pytest
from quant_engine.bybit_profiles import (
    TESTNET_ENDPOINT,
    FixtureTrustedProfileStore,
    TrustedBybitProfile,
    resolve_testnet_profile,
)


def test_resolves_only_known_opaque_profile_to_fixed_testnet_linear() -> None:
    expected = TrustedBybitProfile("test-profile", "81234567", "81230000")
    store = FixtureTrustedProfileStore((expected,))

    assert resolve_testnet_profile("test-profile", store) == expected
    assert expected.environment == "testnet"
    assert expected.category == "linear"
    assert expected.endpoint == TESTNET_ENDPOINT
    assert resolve_testnet_profile("unknown", store) is None


def test_rejects_secret_like_or_malformed_profile_reference() -> None:
    store = FixtureTrustedProfileStore((TrustedBybitProfile("safe-ref", "81234567"),))

    for value in ("", "safe ref", "sk_test_secret", "https://example.test", "a" * 65):
        assert resolve_testnet_profile(value, store) is None


def test_profile_constructor_rejects_environment_endpoint_or_identity_drift() -> None:
    with pytest.raises(ValueError):
        TrustedBybitProfile("test-ref", "81234567", environment="mainnet")
    with pytest.raises(ValueError):
        TrustedBybitProfile("test-ref", "81234567", category="spot")
    with pytest.raises(ValueError):
        TrustedBybitProfile("test-ref", "81234567", endpoint="https://api.bybit.com")
    with pytest.raises(ValueError):
        TrustedBybitProfile("test-ref", "not-a-uid")
