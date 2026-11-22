# DESIGN: Validated strategy selection boundary

Date: 2026-11-20. Status: implementation slice; no execution authority.

## Problem and boundary

The repository now contains deterministic strategy-family evaluators, but no
runtime component decides which validated family is appropriate for a market
window. This slice adds a small engine-owned selector and regime detector. It
produces an auditable suggestion for research/portfolio code; it never creates
an order, reads account state, chooses a Bybit symbol, or grants execution
permission. The DSH AI remains responsible for selecting eligible instruments
and deciding whether to act. The selector only compares registered strategy
records for the instrument the caller already supplied.

## Decisions

1. **Validation gate:** only a registry record in `approved` lifecycle with
   `paper_passed` validation and a non-empty approval reference is eligible.
   Metadata is provenance, not an execution token.
2. **Regime:** use a bounded close-return trend score and normalized range
   volatility. The detector returns `trend_up`, `trend_down`, `range`,
   `volatile`, or `unknown`; insufficient/invalid evidence returns `unknown`.
3. **Score:** combine caller-owned out-of-sample score, confidence and an
   explicit cost penalty. Each candidate must carry a non-empty evaluation
   reference, a timestamp no more than 30 days old, and at least 30
   out-of-sample observations. The selector returns the reference and
   timestamp with its result. These caller-supplied references are audit
   metadata only; this slice cannot verify them against a research artifact.
   Regime support is a deterministic eligibility filter. Ties are broken by
   strategy id and version.
4. **Hysteresis/cooldown:** retain the previous selection during its cooldown;
   after cooldown, replace it only when the new score exceeds it by the
   configured margin. A missing or stale previous strategy cannot block a
   fresh choice.
5. **Fail closed:** no eligible candidate, non-ready signal, malformed score,
   missing/future/stale evaluation timestamp, too few OOS observations, or
   insufficient bars yields an abstention result.

## File Manifest

| Path | Action | Purpose |
|---|---|---|
| `python/apps/quant-engine/src/quant_engine/strategy_selector.py` | Create | Pure regime detection, validation gate, scoring, cooldown and hysteresis |
| `python/apps/quant-engine/tests/test_strategy_selector.py` | Create | Deterministic regime, eligibility, scoring and transition coverage |
| `sdd/reports/BUILD_REPORT_STRATEGY_SELECTION.md` | Create | Command receipts, limits and requirement traceability |

## Verification

```text
uv run --project python --locked pytest python/apps/quant-engine/tests/test_strategy_selector.py -q
uv run --project python --locked ruff check python/apps/quant-engine/src/quant_engine/strategy_selector.py python/apps/quant-engine/tests/test_strategy_selector.py
uv run --project python --locked pyright python/apps/quant-engine/src/quant_engine/strategy_selector.py
```

This slice does not prove strategy profitability, OOS validity, dynamic AI
symbol selection, portfolio construction, persistence, or Nautilus execution.
It also does not independently validate the referenced OOS artifact or meet
AT-019's broader stability, common-data, and portfolio-transition requirements.
