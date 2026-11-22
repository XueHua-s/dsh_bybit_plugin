from decimal import Decimal
from typing import cast

import pytest
from quant_engine.strategy_selector import Regime
from quant_engine.synthetic_fixture_registry import (
    PaperFixtureBundle,
    SyntheticBar,
    SyntheticCorrelation,
    SyntheticFixtureRegistry,
    SyntheticSelectionEvidence,
)
from quant_execution.models import InstrumentSpec
from quant_execution.paper_models import PaperDepth, PaperFixture


def _fixture(symbol: str, bid: str, ask: str, stamp: int) -> PaperFixture:
    return PaperFixture(
        InstrumentSpec(
            symbol, f"{symbol[:3]}", Decimal("0.1"), Decimal("0.01"), Decimal("0.01"), Decimal(100), Decimal(1)
        ),
        PaperDepth(Decimal(bid), Decimal(ask), Decimal(2), Decimal(3), stamp),
        Decimal(10000),
    )


def _bars(fixture: PaperFixture) -> tuple[SyntheticBar, ...]:
    bid, ask = fixture.initial_depth.bid, fixture.initial_depth.ask
    return tuple(SyntheticBar(stamp, bid, ask, bid, bid, Decimal(1)) for stamp in range(80, 101))


def _bundle(fixture_id: str, *fixtures: PaperFixture) -> PaperFixtureBundle:
    bars = {item.instrument.symbol: _bars(item) for item in fixtures}
    evidence = {item.instrument.symbol: (_evidence(),) for item in fixtures}
    symbols = sorted({item.instrument.symbol for item in fixtures})
    correlations = tuple(
        SyntheticCorrelation(first, second, Decimal(1))
        for index, first in enumerate(symbols)
        for second in symbols[index + 1 :]
    )
    return PaperFixtureBundle(fixture_id, tuple(fixtures), bars, evidence, correlations)


def _evidence() -> SyntheticSelectionEvidence:
    return SyntheticSelectionEvidence(
        "sma_cross",
        "0.1.0",
        "fixture-approval:sma-cross",
        1.0,
        0.8,
        2.0,
        "fixture-evidence:sma-cross",
        80,
        100_000,
        64,
        (Regime.TREND_UP, Regime.TREND_DOWN, Regime.RANGE, Regime.VOLATILE),
        True,
    )


def test_bundle_a_and_b_replace_candidate_pool_and_symbol_resolution() -> None:
    first = _bundle("bundle-a", _fixture("ALPHA-PERP", "10", "10.1", 100), _fixture("BETA.PERP", "20", "20.1", 100))
    second = _bundle("bundle-b", _fixture("GAMMA_1", "30", "30.1", 100))
    registry = SyntheticFixtureRegistry((first, second))

    a = registry.snapshot("bundle-a", now_ns=101, ttl_ns=1000)
    b = registry.snapshot("bundle-b", now_ns=101, ttl_ns=1000)
    a_candidates = cast(list[dict[str, object]], a["candidates"])
    b_candidates = cast(list[dict[str, object]], b["candidates"])
    assert [item["symbol"] for item in a_candidates] == ["ALPHA-PERP", "BETA.PERP"]
    assert [item["symbol"] for item in b_candidates] == ["GAMMA_1"]
    assert a["bundle_digest"] != b["bundle_digest"]
    evidence = cast(list[dict[str, object]], a_candidates[0]["selector_evidence"])
    assert evidence[0]["provenance"] == "synthetic_fixture_only"
    assert registry.resolve("bundle-a", str(a["bundle_digest"])).resolve("BETA.PERP").instrument.symbol == "BETA.PERP"
    assert registry.resolve("bundle-b", str(b["bundle_digest"])).resolve("GAMMA_1").instrument.symbol == "GAMMA_1"
    with pytest.raises(ValueError, match="unsupported_fixture_symbol"):
        registry.resolve("bundle-a").resolve("GAMMA_1")


def test_bundle_digest_is_order_independent_but_binds_price_and_depth() -> None:
    left = _fixture("ALPHA", "10", "10.1", 100)
    right = _fixture("BETA", "20", "20.1", 100)
    first = _bundle("bundle-a", left, right)
    reordered = _bundle("bundle-a", right, left)
    changed = _bundle("bundle-a", left, _fixture("BETA", "20", "20.2", 100))

    assert first.digest == reordered.digest
    assert first.digest != changed.digest


def test_bundle_digest_binds_complete_canonical_pairwise_correlations() -> None:
    left = _fixture("ALPHA", "10", "10.1", 100)
    right = _fixture("BETA", "20", "20.1", 100)
    base = _bundle("bundle-a", left, right)
    changed = PaperFixtureBundle(
        "bundle-a",
        base.fixtures,
        base.bars_by_symbol,
        base.evidence_by_symbol,
        (SyntheticCorrelation("ALPHA", "BETA", Decimal("0.5")),),
    )
    snapshot = base.snapshot(now_ns=101, ttl_ns=1000)
    assert base.digest != changed.digest
    assert snapshot["correlations"] == [{"first_symbol": "ALPHA", "second_symbol": "BETA", "coefficient": "1"}]


def test_bundle_rejects_missing_reversed_and_out_of_range_correlations() -> None:
    left = _fixture("ALPHA", "10", "10.1", 100)
    right = _fixture("BETA", "20", "20.1", 100)
    base = _bundle("bundle-a", left, right)
    with pytest.raises(ValueError, match="fixture_correlation_pair_coverage"):
        PaperFixtureBundle("bundle-a", base.fixtures, base.bars_by_symbol, base.evidence_by_symbol)
    with pytest.raises(ValueError, match="invalid_fixture_correlation_pair"):
        SyntheticCorrelation("BETA", "ALPHA", Decimal(1))
    with pytest.raises(ValueError, match="invalid_fixture_correlation_range"):
        SyntheticCorrelation("ALPHA", "BETA", Decimal("1.01"))


def test_registry_fails_closed_for_bad_identity_and_stale_bundle() -> None:
    bundle = _bundle("bundle-a", _fixture("ALPHA", "10", "10.1", 100))
    registry = SyntheticFixtureRegistry((bundle,))

    with pytest.raises(ValueError, match="fixture_identity_mismatch"):
        registry.resolve("missing")
    with pytest.raises(ValueError, match="stale_fixture_bundle"):
        registry.snapshot("bundle-a", now_ns=1100, ttl_ns=1000)
    with pytest.raises(ValueError, match="stale_fixture_bars"):
        registry.snapshot("bundle-a", now_ns=1200, ttl_ns=1000)
    with pytest.raises(ValueError, match="invalid_fixture_snapshot_clock"):
        registry.snapshot("bundle-a", now_ns=99, ttl_ns=1000)


def test_one_native_session_requires_exactly_one_registered_bundle() -> None:
    first = _bundle("bundle-a", _fixture("ALPHA", "10", "10.1", 100))
    second = _bundle("bundle-b", _fixture("BETA", "20", "20.1", 100))

    assert SyntheticFixtureRegistry((first,)).only_bundle is first
    multi_bundle_registry = SyntheticFixtureRegistry((first, second))
    with pytest.raises(ValueError, match="paper_session_requires_single_fixture_bundle"):
        _ = multi_bundle_registry.only_bundle


def test_bundle_rejects_duplicate_symbol_and_inconsistent_balance() -> None:
    first = _fixture("ALPHA", "10", "10.1", 100)
    duplicate = _fixture("ALPHA", "20", "20.1", 100)
    with pytest.raises(ValueError, match="duplicate_fixture_symbol"):
        _bundle("bundle-a", first, duplicate)
    with pytest.raises(ValueError, match="inconsistent_fixture_account"):
        _bundle(
            "bundle-b",
            first,
            PaperFixture(_fixture("GAMMA", "30", "30.1", 100).instrument, duplicate.initial_depth, Decimal(9000)),
        )


def test_bars_are_bound_to_digest_and_reject_missing_or_invalid_history() -> None:
    fixture = _fixture("ALPHA", "10", "10.1", 100)
    base = _bundle("bundle-a", fixture)
    changed_bars = dict(base.bars_by_symbol)
    changed_bars["ALPHA"] = (
        *changed_bars["ALPHA"][:-1],
        SyntheticBar(100, Decimal(10), Decimal("10.2"), Decimal(10), Decimal("10.1"), Decimal(1)),
    )
    changed = PaperFixtureBundle("bundle-a", (fixture,), changed_bars, base.evidence_by_symbol)
    assert changed.digest != base.digest
    snapshot = base.snapshot(now_ns=101, ttl_ns=1000)
    candidate = cast(list[dict[str, object]], snapshot["candidates"])[0]
    assert len(cast(list[object], candidate["bars"])) == 21
    with pytest.raises(ValueError, match="fixture_bars_symbol_mismatch"):
        PaperFixtureBundle("bundle-a", (fixture,), {}, base.evidence_by_symbol)
    with pytest.raises(ValueError, match="fixture_evidence_symbol_mismatch"):
        PaperFixtureBundle("bundle-a", (fixture,), base.bars_by_symbol, {})
    with pytest.raises(ValueError, match="unordered_fixture_bars"):
        PaperFixtureBundle(
            "bundle-a",
            (fixture,),
            {
                "ALPHA": (
                    SyntheticBar(90, Decimal(10), Decimal(10), Decimal(10), Decimal(10), Decimal(1)),
                    SyntheticBar(80, Decimal(10), Decimal(10), Decimal(10), Decimal(10), Decimal(1)),
                )
            },
            base.evidence_by_symbol,
        )
    with pytest.raises(ValueError, match="invalid_fixture_bar_ohlc"):
        SyntheticBar(100, Decimal(10), Decimal(9), Decimal(10), Decimal(10), Decimal(1))
