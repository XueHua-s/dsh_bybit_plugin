import pytest
from quant_portfolio import PositionExposure, TargetProposal


@pytest.mark.parametrize("symbol", ["ALPHA-PERP", "BETA.PERP", "GAMMA_1", "BTCUSDT"])
def test_safe_exchange_style_symbols_are_accepted(symbol: str) -> None:
    assert PositionExposure(symbol, 0.1).symbol == symbol


@pytest.mark.parametrize(
    "symbol",
    ["alpha", "A--B", "-ALPHA", "ALPHA_", "A/B", "A\\B", "A B", "A\nB", "A" * 41],
)
def test_unsafe_or_malformed_symbols_are_rejected(symbol: str) -> None:
    with pytest.raises(ValueError, match="invalid_position_symbol"):
        PositionExposure(symbol, 0.1)


def test_proposal_uses_same_symbol_grammar() -> None:
    with pytest.raises(ValueError, match="invalid_target_reference"):
        TargetProposal("A/B", "strategy", "1.0.0", 0.1, 0.9, "fixture://evidence", 100)
