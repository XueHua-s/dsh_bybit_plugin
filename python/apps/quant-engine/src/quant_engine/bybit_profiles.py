"""Trusted, secret-free profile binding for the native Bybit Testnet boundary."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

TESTNET_ENDPOINT = "https://api-testnet.bybit.com"
_PROFILE_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")


@dataclass(frozen=True)
class TrustedBybitProfile:
    """Host-owned identity binding; credentials never cross this boundary."""

    profile_ref: str
    expected_uid: str
    expected_parent_uid: str | None = None
    environment: str = "testnet"
    category: str = "linear"
    endpoint: str = TESTNET_ENDPOINT

    def __post_init__(self) -> None:
        if not isinstance(self.profile_ref, str) or _PROFILE_REF.fullmatch(self.profile_ref) is None:
            raise ValueError("invalid profile reference")
        if (
            not isinstance(self.expected_uid, str)
            or not self.expected_uid.isdigit()
            or not 1 <= len(self.expected_uid) <= 32
        ):
            raise ValueError("invalid expected uid")
        if self.expected_parent_uid is not None and (
            not isinstance(self.expected_parent_uid, str)
            or not self.expected_parent_uid.isdigit()
            or not 1 <= len(self.expected_parent_uid) <= 32
        ):
            raise ValueError("invalid expected subaccount uid")
        if self.environment != "testnet" or self.category != "linear" or self.endpoint != TESTNET_ENDPOINT:
            raise ValueError("profile must be explicit Testnet Linear")


class TrustedProfileStore(Protocol):
    """Secure host/provider lookup; implementations must not use ambient env fallback."""

    def resolve(self, profile_ref: str) -> TrustedBybitProfile | None: ...


class FixtureTrustedProfileStore:
    """Small in-memory fixture store; production secret/profile persistence is not implied."""

    def __init__(self, profiles: tuple[TrustedBybitProfile, ...]) -> None:
        self._profiles = {profile.profile_ref: profile for profile in profiles}

    def resolve(self, profile_ref: str) -> TrustedBybitProfile | None:
        if _PROFILE_REF.fullmatch(profile_ref) is None:
            return None
        return self._profiles.get(profile_ref)


def resolve_testnet_profile(profile_ref: str, store: TrustedProfileStore) -> TrustedBybitProfile | None:
    """Resolve only an opaque reference; malformed/missing profiles are unavailable."""

    if not isinstance(profile_ref, str) or _PROFILE_REF.fullmatch(profile_ref) is None:
        return None
    profile = store.resolve(profile_ref)
    if profile is None:
        return None
    if profile.environment != "testnet" or profile.category != "linear" or profile.endpoint != TESTNET_ENDPOINT:
        return None
    return profile
