# DESIGN: Quant Risk

> Independent deterministic offline veto foundation for original brief §13; no exchange authority.

## Metadata

| Attribute | Value |
|---|---|
| Feature | QUANT_RISK |
| Date | 2026-11-17 |
| Author | risk_foundation implementation agent |
| BRAINSTORM | `sdd/features/BRAINSTORM_BYBIT_AI_QUANT.md` |
| DEFINE | `sdd/features/DEFINE_BYBIT_AI_QUANT.md` |
| UX REVIEW | N/A |
| LLM Prompts | false for this isolated deterministic slice; parent feature remains true |
| Status | Ready for Build; independent acceptance pending |

## Architecture Overview

```text
untrusted order proposal -> evaluate(intent, server_context, operator_policy)
                                     ^
               server-owned atomic snapshots + reservations + clock
                                     |
                           validated deterministic veto
                                     |
                      Decision(reasons, approved_plan | None)
                                     |
                 future transactional audit/reservation/Nautilus gate
```

## Components

| Component | Purpose | Technology / Pattern | Inputs | Outputs | Dependencies |
|---|---|---|---|---|---|
| models | Immutable explicit trusted snapshot contract | Python typed frozen dataclasses, Decimal | engine-normalized values | domain records | standard library |
| validation | Own all runtime invariants, including typed-record misuse | pure explicit validation | complete request/context/policy | validity | models |
| evaluator | Own gross portfolio arithmetic and stable veto ordering | pure Decimal arithmetic | validated records | immutable Decision | models, validation |

## Key Decisions

### Decision 1: Trusted data cannot come from model tools

Status: proposed for independent review. Date: 2026-11-17. Source: original §13, DEFINE AT-012/021/022.
Context: Python types do not authenticate caller-supplied snapshots. Choice: no JSON parser/tool route; snapshots and policy are exclusively engine/operator-owned. Intent contains only request ID, instrument, side, quantity, price ceiling and leverage. Market snapshot owns projected liquidation distance and side-specific executable depth/price, bound to the exact immutable `estimated_for` intent; each exposure carries its own observed timestamp. All amounts are normalized by the trusted producer into common USDT valuation with fresh mark/FX provenance; this pure package cannot detect mixed units from Decimal values alone. Rationale: no LLM field can claim account approval, risk limits, freshness or reconciliation. Rejected: a model-controlled risk context, or an allow flag accepted by execution. Consequence: this package alone cannot enforce origin, prevent concurrent double approval or make veto unbypassable; a serialized execution integration with atomic reservations, durable audit and revalidation is mandatory and unfinished.

### Decision 2: Conservative gross accounting without hedge netting

Status: proposed for independent review. Date: 2026-11-17. Source: §13.
Choice: each position and pending-order reservation consumes absolute notional; opposite legs never cancel. Proposed quantity is conservatively treated as additional exposure, including SELL. Per-symbol aggregate counts for position/concentration; total gross for exposure/leverage; each leg/reservation plus proposed order counts toward concurrency. There is no reduce-only bypass. Rationale: under-approving reductions is preferable to treating an unauthenticated reduction as safe. Rejected: signed net exposures and special bypass flags. Consequence: reductions require a future dedicated verified transition contract; this slice does not plan closures.

### Decision 3: Fully specified limits and finite bounded arithmetic

Status: proposed for independent review. Date: 2026-11-17. Source: §13 and existing Decimal execution models.
Choice: all limits required, no permissive defaults. Inputs must be actual finite Decimal values (bounded precision/exponents), exact int timestamps, enums and immutable tuples; no float coercion. Arithmetic uses a private Decimal context and traps numeric errors into a stable arithmetic rejection. Equality at maxima is allowed; daily loss/drawdown reaching their ceiling freezes new exposure; freshness age equal to TTL is allowed. Correlations must fully cover every distinct held/reserved/proposed symbol pair; absolute correlation clusters charge full gross member exposure including negative relationships, with no diversification credit. Rationale: deterministic fail-closed behavior. Consequence: caller supplies correlation estimates and provenance, funding/liquidation estimates, and reconciliation; estimator correctness remains outside package.

Software-design diagnostic: internal scoped score 10/10 (8 of 8 diagnostic rows), not independent acceptance or an integrated-system score. Each module has one sentence purpose; a three-argument facade hides validation/arithmetic; the caller sees immutable domain data rather than implementation internals; interface comments explain promises and trust limits; independent review discusses design; each internal module hides validation or gross-risk calculation knowledge; package documentation makes boundaries discoverable; pre-code design and revisions record strategic effort. No diagnostic row currently failed in this slice. Wider execution integration and snapshot authenticity remain unfinished regardless of this local diagnostic.

## File Manifest

| # | File | Action | Purpose | Agent / Owner | Dependencies |
|---:|---|---|---|---|---|
| 1 | `python/packages/quant-risk/pyproject.toml` | Create | genuine uv package | risk_foundation | none |
| 2 | `python/packages/quant-risk/project.json` | Create | Nx lint/typecheck/test/build targets | risk_foundation | 1 |
| 3 | `python/packages/quant-risk/src/quant_risk/models.py` | Create | immutable boundary and decision types | risk_foundation | none |
| 4 | `python/packages/quant-risk/src/quant_risk/validation.py` | Create | strict bounded data invariants | risk_foundation | 3 |
| 5 | `python/packages/quant-risk/src/quant_risk/evaluator.py` | Create | independent deterministic risk veto | risk_foundation | 3,4 |
| 6 | `python/packages/quant-risk/src/quant_risk/__init__.py` | Create | explicit public interface | risk_foundation | 3,5 |
| 7 | `python/packages/quant-risk/tests/test_risk.py` | Create | risk boundaries/adversarial scenarios | risk_foundation | 6 |
| 8 | `sdd/reports/BUILD_REPORT_QUANT_RISK.md` | Create | commands, exit evidence and unfinished gates | risk_foundation | 1-7 |

Total Files: 8. Agent Assignment Rationale: one implementation owner for tightly coupled safety logic; independent reviewer assigned by parent. Agent Discovery: parent explicit delegation. Root uv dependency/source, lock, CI/SBOM and Nx full graph integration are parent-owned, outside this manifest; required edits reported to parent.

## Code Patterns

```python
def evaluate(intent: OrderIntent, context: RiskContext, policy: RiskPolicy) -> RiskDecision:
    """Pure veto over engine-owned atomic snapshots; approval is not exchange authorization."""
```

Approved plan is the exact immutable intent plus snapshot ID and expiry; it is not an execution token. Rejection exposes stable codes only, never input text or secrets.

## Data Flow

1. Engine normalizes account/market/portfolio/correlation snapshots and pending reservations under one generation ID.
2. Evaluator validates every field before arithmetic; missing/wrong-type/nonfinite data denies.
3. Identity, Testnet/Demo/backtest/internal_paper environment isolation, reconciliation, clock freshness and emergency freeze gate all orders.
4. Evaluator applies all §13 controls to conservative projected gross portfolio.
5. Result contains all deterministic applicable codes in stable order or an exact approved plan with generation and expiry.
6. Future caller must atomically persist decision/reservation, notify rejection and revalidate immediately before sole Nautilus submission. Agent retries never change snapshots/policy; these integration requirements are not implemented here.

## Integration Points

| External System | Integration Type | Authentication | Direction | Failure / Retry |
|---|---|---|---|---|
| None | pure in-process only | N/A | N/A | no retry/network |

Current quant-execution models are offline fixtures, not authoritative exchange metadata; package does not import Nautilus or execution. Future integration must validate instrument precision/minimum notional, idempotency, account/environment and current snapshot generation again.

## Testing Strategy

| Test Type | Scope / Requirement | Files | Tools | Pass Signal |
|---|---|---|---|---|
| Unit | all fifteen §13 controls, exact thresholds, gross hedge/reservation treatment | `tests/test_risk.py` | existing pytest | exit 0 |
| Adversarial | NaN, infinity, string/float Decimal impostors, future/stale state, missing pair and wrong account/mainnet | same | pytest | rejects without approval or input leak |
| Static | types and coherent <=500 line modules | package | existing pyright/ruff | exit 0 |
| Full Verify Gate | parent DEFINE `pnpm run verify` plus independent review | parent-owned | pnpm | incomplete until parent receipt |

Four Hypothesis properties use explicit seed `20261117` and `database=None`; no local example database alters reproducibility. The locked Hypothesis version fixes generator semantics.

## Error Handling

| Error Type | Detection | Handling Strategy | Retry? | Observability |
|---|---|---|---|---|
| malformed input/policy/context | strict validator | fixed invalid_* rejection | No | stable reasons |
| numeric failure | DecimalException in isolated arithmetic only | arithmetic_invalid rejection | No | reason |
| stale/uncertain account | timestamps/reconciliation | reject | only after new trusted state | reason |
| emergency | explicit frozen flag | reject all orders | No | emergency_stop reason |

## Configuration

All required RiskPolicy fields are operator-owned caps: order/position/account gross notionals, leverage, equity-loss/drawdown fractions, concurrency, spread/slippage/funding fractions, depth participation, liquidation distance, concentration and correlated equity fractions, correlation cutoff, cooldown, TTL. No credentials or secret fields. No default limits.

## Security Considerations

- No network, filesystem, execution, secrets, LLM provider, permissive fallback or reduce-only bypass.
- Server-owned context authenticity cannot be established by dataclasses; do not expose it as tool arguments.
- Mainnet always rejected in this increment; other environments must match policy and account context exactly.
- Existing and pending exposure must be complete; missing private-stream/reconciliation data must set reconciled false.
- Emergency stop here only freezes new approval. Actual cancel/reconcile/freeze-scheduler/durable events and authorized liquidation are mandatory unfinished integration; never blind-close during network failure.

## Observability

| Aspect | Implementation | Signal / Why |
|---|---|---|
| Logging | none in pure package | caller persists stable reason codes |
| Metrics | none | caller counts rejections by reason |
| Tracing | approved snapshot ID | links future audited decision to server generation |

## Requirements Traceability

| Requirement / AT | Design Element | Test / Gate |
|---|---|---|
| §13 all controls / AT-021 | evaluator | parameterized independent limit tests |
| AT-012 | context freshness/reconciliation | stale/missing/invalid cases |
| AT-016 | strict environment match | mainnet/mismatch cases |
| AT-022 partial | emergency veto | emergency case; cancellations unimplemented |
| AT-014/015/029 | future sole-authority transaction | explicitly incomplete |

## Risks and Mitigations

| Risk | Impact | Mitigation | Residual Risk |
|---|---|---|---|
| untrusted/missing snapshot | unsafe approval | caller ownership + reject invalid/reconciled false | live adapter/authenticity not implemented |
| concurrent approvals | oversubscription | pending reservations contract | transactional caller unfinished |
| conservative reduction handling | reductions denied | dedicated future verified transition path | cannot close positions here |
| false funding/liquidation/correlation estimate | unsafe economics | required bounded complete server estimate | estimator/provenance integration unfinished |

## Advisor Ledger

Independent reviewer `/root/risk_independent_review` reviewed implementation in progress. Findings applied: exact Decimal dataclass field matching; exact enum strings/blank identifiers; full executable price-limit slippage envelope; per-leg timestamps/earliest expiry; exact intent-bound liquidation estimate; common trusted valuation units. Final independent receipt: `sdd/reviews/REVIEW_QUANT_RISK_2026-11-17.md` ACCEPT for the bounded pure package, no outstanding P1/P2. Minimum-notional lower-floor correction was also applied and tested. Implementation agent does not self-ACCEPT.

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-11-17 | risk_foundation | Pre-code scoped design from original §13 |

## Next Step

Execute o **SDD Build by RDD**.
