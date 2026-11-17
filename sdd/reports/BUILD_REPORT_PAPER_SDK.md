# BUILD REPORT: Authenticated internal-paper SDK

## Metadata

| Attribute | Value |
|---|---|
| Feature | PAPER_SDK (scoped component, not full product acceptance) |
| Date | 2026-11-17 |
| Author | paper_sdk / SDD Build |
| BRAINSTORM | sdd/features/BRAINSTORM_BYBIT_AI_QUANT.md |
| DEFINE | sdd/features/DEFINE_BYBIT_AI_QUANT.md |
| DESIGN | sdd/features/DESIGN_PAPER_SDK.md; DESIGN_EXECUTION_CUTOVER.md |
| Status | Complete — scoped SDK only; independent ACCEPT recorded |

## Mode Selection

| Signal | Observation |
|---|---|
| Manifest files | 11 implementation/generated files plus scoped design/report |
| Cross-file coupling | High: canonical Python API → separate OpenAPI → generated TS + AJV |
| Security surface | Private capability header, verified numeric loopback, uncertainty recovery |
| LLM prompt items | None introduced |
| Independent volume | SDK delegated by root; API schema coordinated with its author |
| Context-rot risk | Controlled by schema freeze and manifest |
| Runtime capabilities | Delegated component within root-authorized parallel Build |

Recommendation: preserve delegation and coordinate schema freeze. Decision: parent assigned SDK scope; parent selected separate actual-app contract rather than unsupported superset. Pre-build review: no separate pre-build review receipt; root owns overall design acceptance.

## Summary

| Metric | Value |
|---|---|
| Tasks Completed | S1–S9 complete |
| Files Created | 6 (paper contract, two generated paper modules, paper module, test, this report), plus scoped design |
| Files Modified | 5 (exporter, generator, index, transport, validation) |
| Files Deleted | 0 |
| Verify Gate | Scoped commands green; product gate/root release unclaimed |
| Execution Mode | Root-delegated component |

## Task Execution

| Manifest | Task | Status | Evidence |
|---|---|---|---|
| S1–S3,S9 | Export actual separate optional API and generate its types/schema | Complete | Python exporter, generator + drift checks exit0 |
| S4 | Private capability transport with bounded provider/HTTP/body lifetime | Complete | Synthetic auth/deadline/cancel/close/redirection/reflection tests |
| S5,S6 | Runtime schema validation, stable recovery IDs, paper methods | Complete | 21 package tests pass; typecheck exit0 |
| S7 | Security and regression tests | Complete | Existing 9 readonly + 12 paper tests pass |
| S8 | Scoped evidence | Complete | Independent ACCEPT in sdd/reviews/REVIEW_PAPER_SDK_2026-11-17.md |

## Files Changed

| File | Action | Manifest | Verified |
|---|---|---|---|
| python/apps/quant-engine/src/quant_engine/bootstrap.py | Modify, delegated exporter | S1 | Yes |
| contracts/openapi/quant-paper.v1.json | Create from actual Python app | S2 | Yes |
| packages/ts/quant-api-client/src/generated/paper-paths.ts | Generate | S3 | Yes |
| packages/ts/quant-api-client/src/generated/paper-schema.ts | Generate | S3 | Yes |
| packages/ts/quant-api-client/src/transport.ts | Modify | S4 | Yes |
| packages/ts/quant-api-client/src/validation.ts | Modify | S5 | Yes |
| packages/ts/quant-api-client/src/index.ts | Modify | S6 | Yes |
| packages/ts/quant-api-client/src/paper.ts | Create | S6 | Yes |
| packages/ts/quant-api-client/test/paper.test.ts | Create | S7 | Yes |
| packages/ts/quant-api-client/scripts/generate.ts | Modify | S9 | Yes |
| sdd/reports/BUILD_REPORT_PAPER_SDK.md | Create, canonical reports location | S8 | Yes |

## Drift Detected

| Drift | Decision | Action |
|---|---|---|
| Existing command lookup needs command_id unavailable after lost POST response | API author added by-request lookup | Actual API + generated contract + client now resolve original request_id |
| Combined contract would advertise routes absent from readonly runtime | Parent chose separate paper schema | quant-engine schema and readonly app remain unchanged |
| Dot-only opaque IDs normalize in URL paths | Canonical Python schema changed before final generation | First character alphanumeric; SDK generated validator rejects dot-only submit/query IDs |
| Design originally described native thread | Root-coordinated actual native process boundary | PaperStatus field native_process_alive reflects actual app schema |

## Verification Results

Commands run against installed dependencies; no installation, exchange account or real network required. Each listed final command exited0 unless explicitly stated. Initial lint reported two consistent-function-scoping warnings; both fixed and lint rerun clean.

| Command | Result / Evidence |
|---|---|
| `python/.venv/bin/python -c 'from quant_engine.bootstrap import export_openapi; export_openapi()' --paper --output contracts/openapi/quant-paper.v1.json` | exit0; actual app offline export, no lifespan |
| `pnpm --filter @bybit-quant/quant-api-client generate` | exit0; generates both contracts separately |
| `pnpm --filter @bybit-quant/quant-api-client test` | exit0; build + 21/21 tests in 2 files |
| `pnpm --filter @bybit-quant/quant-api-client typecheck` | exit0; strict TypeScript |
| `pnpm --filter @bybit-quant/quant-api-client generate:check` | exit0; no generated drift |
| `pnpm exec oxlint packages/ts/quant-api-client/src packages/ts/quant-api-client/scripts packages/ts/quant-api-client/test` | exit0; clean |
| `python/.venv/bin/python -c 'from quant_engine.bootstrap import export_openapi; export_openapi()' --paper --check --output contracts/openapi/quant-paper.v1.json` | exit0; actual paper schema matches artifact |
| `python/.venv/bin/python -c 'from quant_engine.bootstrap import export_openapi; export_openapi()' --check --output contracts/openapi/quant-engine.v1.json` | exit0; readonly schema unchanged |
| `python/.venv/bin/ruff check python/apps/quant-engine/src/quant_engine/bootstrap.py` | exit0 |
| `python/.venv/bin/ruff format --check python/apps/quant-engine/src/quant_engine/bootstrap.py` | exit0 |
| `git diff --check -- packages/ts/quant-api-client python/apps/quant-engine/src/quant_engine/bootstrap.py` | exit0 |

### Verify Gate

Kind: component test/typecheck/schema drift. Scope: generated SDK only. Root must execute DEFINE's full product gate and release checks; this report does not substitute focused commands for those gates. Manual UX: N/A for this slice.

## Acceptance Test Verification

| Requirement | Scope evidence | Limit |
|---|---|---|
| AT-013 / §16 schema authority | Actual Python app exported; generated types and AJV schema; path names compile against generated paths | No DSH mutation tools wired |
| AT-014 / AT-029 stable identity | No mutation retries; uncertain result directs query original request_id; caller mutation during provider wait cannot replace original recovery ID | Real native dispatch acceptance belongs to engine/native integration |
| Authentication and safe boundary | Synthetic capability header only; strict extra-field rejection, safe 401/403/409/422/503, 202 command success | Host provider implementation intentionally not installed/wired |
| Bounded client lifecycle | Provider, fetch, streaming body deadline; cancellation/close; no redirects; numeric loopback only | Injected tests; reviewer separately probes real local mock HTTP |

## Advisor Ledger

Independent reviewer: paper_sdk_review, root assigned. Final scoped ACCEPT: sdd/reviews/REVIEW_PAPER_SDK_2026-11-17.md (21 tests, seven actual loopback HTTP probes, delayed-provider mutation and invalid-origin probes; isolated generated-artifact and Python schema drift both rejected).

| Finding | Decision | Evidence |
|---|---|---|
| Printable quote/backslash capability escapes defeat reserialization comparison | APPLIED | Scan decoded strings + keys; synthetic reflection test passes |
| Dot-only request IDs normalize in actual HTTP URL | APPLIED via canonical API author | First-alnum schema regenerated; submit/request regression rejects both '.' and '..' |
| Mutable caller DTO can change recovery ID during pending capability provider | APPLIED | Capture primitive IDs before await; test verifies original serialized body and recovery ID |

## Issues Encountered

No dependency or infrastructure blocker. Review findings were fixed with focused regressions. No capability, credential or account material loaded; fixtures are synthetic. All handwritten files remain below500 lines; no `any` added.

## Deviations from Design

No unapproved implementation scope. Exporter ownership delegated by API author; separate paper contract selected explicitly by parent. Report uses canonical sdd/reports location as directed by parent.

## Blockers

No SDK blocker; independent scoped ACCEPT recorded. Root product verification remains separate. No release, installation, lockfile change, commit, push, DSH mutation wiring or real order performed by this component.

## Final Status

Overall: COMPLETE for scoped SDK; independent review found no remaining P1/P2. Product readiness, native process behavior and account authorization are not certified here.

- [x] All scoped manifest tasks completed
- [x] Incremental verification recorded
- [x] Scoped test/typecheck/schema checks green
- [x] Complementary checks pass
- [x] Scoped acceptance scenarios verified
- [x] No runtime LLM prompts introduced
- [x] Drift decisions recorded
- [x] Advisor findings applied and independently accepted
- [x] No SDK blocker or TODO/FIXME substitution

## Next Step

Execute o **SDD Handoff by RDD**.
