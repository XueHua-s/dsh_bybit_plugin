"""Trusted offline configuration; capability material is never configuration data."""

import os
import stat
import time
from dataclasses import dataclass, field, replace
from decimal import Decimal
from pathlib import Path

from quant_execution.models import InstrumentSpec
from quant_execution.paper_models import PaperDepth, PaperFixture
from quant_risk.models import Correlation, RiskPolicy


@dataclass(frozen=True)
class Capability:
    """One process-private principal restricted to one paper session."""

    token: bytes = field(repr=False)
    session_id: str
    scopes: frozenset[str] = frozenset({"observe", "control"})

    def __post_init__(self) -> None:
        if not 32 <= len(self.token) <= 128 or any(byte < 33 or byte > 126 for byte in self.token):
            raise ValueError("invalid private capability")
        if not self.scopes or not self.scopes <= {"observe", "control"}:
            raise ValueError("invalid principal scope")


def capability_from_fd(fd: int, session_id: str) -> Capability:
    """Consume a private inherited pipe; never fall back to argv/env/config."""
    if fd < 3 or not stat.S_ISFIFO(os.fstat(fd).st_mode):
        raise ValueError("private capability pipe required")
    try:
        token = os.read(fd, 129)
    finally:
        os.close(fd)
    return Capability(token, session_id)


@dataclass(frozen=True)
class PaperConfig:
    database: Path
    session_id: str
    fixture: PaperFixture | tuple[PaperFixture, ...]
    policy: RiskPolicy
    queue_capacity: int = 32
    correlations: tuple[Correlation, ...] = ()

    def __post_init__(self) -> None:
        from quant_data.commands import identifier

        identifier(self.session_id, "session")
        if self.policy.environment != "internal_paper" or self.policy.account_id != "SIM-001":
            raise ValueError("paper policy scope required")
        if not 1 <= self.queue_capacity <= 128:
            raise ValueError("invalid queue capacity")
        fixtures = self.fixtures
        symbols = [item.instrument.symbol for item in fixtures]
        if not fixtures or len(set(symbols)) != len(symbols):
            raise ValueError("invalid_fixture_instruments")
        if len({item.starting_balance for item in fixtures}) != 1:
            raise ValueError("inconsistent_fixture_account")
        expected = {
            (first, second) for index, first in enumerate(sorted(symbols)) for second in sorted(symbols)[index + 1 :]
        }
        actual = [(item.first, item.second) for item in self.correlations]
        if any(
            item.first >= item.second
            or not item.coefficient.is_finite()
            or not Decimal(-1) <= item.coefficient <= Decimal(1)
            for item in self.correlations
        ):
            raise ValueError("invalid_fixture_correlation")
        if len(actual) != len(set(actual)) or set(actual) != expected:
            raise ValueError("fixture_correlation_pair_coverage")

    @property
    def fixtures(self) -> tuple[PaperFixture, ...]:
        return (self.fixture,) if isinstance(self.fixture, PaperFixture) else self.fixture

    def fixture_for(self, symbol: str) -> PaperFixture:
        for item in self.fixtures:
            if item.instrument.symbol == symbol:
                return item
        raise ValueError("unsupported_fixture_symbol")


def config_for_bundle(config: PaperConfig, bundle: object) -> PaperConfig:
    """Bind a service config to one validated Python registry bundle's instruments."""
    from .synthetic_fixture_registry import PaperFixtureBundle

    if type(bundle) is not PaperFixtureBundle:
        raise ValueError("invalid_fixture_bundle")
    correlations = tuple(
        Correlation(item.first_symbol, item.second_symbol, item.coefficient) for item in bundle.correlations
    )
    return replace(config, fixture=bundle.fixtures, correlations=correlations)


def synthetic_config(database: Path, session_id: str) -> PaperConfig:
    """Explicit synthetic fixture, finite size and fresh delivery timestamp; never market truth."""
    instrument = InstrumentSpec(
        "BTCUSDT", "BTC", Decimal("0.1"), Decimal("0.001"), Decimal("0.001"), Decimal(1), Decimal(5)
    )
    fixture = PaperFixture(
        instrument,
        PaperDepth(Decimal("49999.9"), Decimal(50000), Decimal("0.1"), Decimal("0.1"), time.time_ns()),
        Decimal(10000),
    )
    policy = RiskPolicy(
        "SIM-001",
        "internal_paper",
        Decimal(1000),
        Decimal(2000),
        Decimal(1),
        Decimal(2000),
        Decimal("0.05"),
        Decimal("0.1"),
        10,
        Decimal("0.001"),
        Decimal("0.001"),
        Decimal("0.2"),
        Decimal("0.001"),
        Decimal("0.1"),
        Decimal("0.2"),
        Decimal("0.8"),
        Decimal("0.2"),
        Decimal("0.001"),
        0,
        60000,
    )
    return PaperConfig(database, session_id, fixture, policy)
