# BUILD REPORT: Native continuous internal paper

## Metadata

| Attribute | Value |
|---|---|
| Feature | PAPER_NATIVE |
| Date | 2026-11-17 |
| Author | paper_native_runtime implementation agent |
| BRAINSTORM | sdd/features/BRAINSTORM_BYBIT_AI_QUANT.md |
| DEFINE | sdd/features/DEFINE_BYBIT_AI_QUANT.md |
| DESIGN | sdd/features/DESIGN_PAPER_NATIVE.md |
| Status | Complete — scoped native implementation and independent delta ACCEPT |

## Mode Selection

| Signal | Observation |
|---|---|
| Manifest files | 12; concrete design saved before code, amended before approved process/license changes |
| Cross-file coupling | Medium: immutable DTOs, private native owner, bounded IPC facade |
| Security surface | Native matching/lifecycle; synthetic-only, no credentials/network client |
| LLM prompt items | None |
| Independent volume | Native implementation separated from admission/store integration and independent reviewer |
| Context-rot risk | Pinned installed API verified locally rather than inferred examples |
| Runtime capabilities | Parent-assigned implementer; separate reviewer |

Recommendation: direct scoped build with independent specialist review. User decision: parent delegated approved native slice and implementer/reviewer separation. Pre-build review: parent and reviewer accepted process architecture before it ran; final scoped delta ACCEPT recorded.

## Summary

| Metric | Value |
|---|---|
| Tasks Completed | 12/12; scoped independent delta ACCEPT |
| Files Created | 11 manifest files, plus pre-build design supplement |
| Files Modified | 1 pyproject.toml |
| Files Deleted | 0 |
| Verify Gate | Green scoped native/package behavior; independent delta ACCEPT; final license artifacts exact |
| Execution Mode | Direct delegated build |

One long-lived official TradingNode runs in the main thread of a spawned child process. Its single finite native Sandbox exchange retains OMS, cash and positions across later wallclock commands. A typed facade hides native configuration, strategy, event mapping and process signals. No BacktestEngine, exchange client, credentials, fabricated fills or automatic retry is introduced. Existing offline Backtest files are unchanged.

## Task Execution

| Manifest ID | Task | Executor | Status | Evidence |
|---:|---|---|---|---|
| 1 | Frozen fixture/order/event/snapshot DTOs | paper_native_runtime | Complete | Ruff/Pyright/native assertions |
| 2 | One finite native Sandbox constructor adaptation | paper_native_runtime | Complete | Native aggregate depth depletion .006 + .004, later replenishment |
| 3 | Official node, native Strategy and evidence mapping | paper_native_runtime | Complete | Native accepted/full/partial/cancel IDs/fill/account/position checks |
| 4 | Spawned owner and bounded private IPC | paper_native_runtime | Complete | Actual child ready/exit/cleanup acknowledgment |
| 5 | Bounded lifecycle facade | paper_native_runtime | Complete | Cleanstop retains events; abrupt loss/forced deadline fail/incomplete |
| 6 | Eleven native runtime tests | paper_native_runtime | Complete | Focused11 plus existing22 =33 passed |
| 7 | This report | paper_native_runtime | Complete | Actual failures and unfinished boundaries recorded |
| 8–12 | Exact LGPL/GPL/MIT notice and artifact metadata | paper_native_runtime | Complete | Fresh wheel/sdist verified exact MIT/LGPL/GPL/NOTICE bytes plus adapted source and mixed-license metadata |

## Files Changed

See the twelve exact paths and purposes in DESIGN_PAPER_NATIVE.md File Manifest. No existing Backtest behavior files changed. Five new source modules are each below500lines. LICENSES/LGPL-3.0-only.txt is a verbatim copy of pinned upstream LICENSE; MIT.txt is verbatim root LICENSE. NOTICE gives source ref, copyright, changes and mixed-license scope. Package metadata uses MIT AND LGPL-3.0-only and license-files to include notices/text.

## Drift Detected

| Change | Evidence | Decision | Action |
|---|---|---|---|
| Thread owner → spawned process | Official TradingNode always supplies explicit loop; kernel installs mainthread-only process signals | Parent explicitly approved, reviewer concurred before native execution | Official constructors in child; no private kernel clone/global monkeypatch |
| Upstream Sandbox defaults infinite consumption | Config lacks field; exchange property readonly | Parent approved documented pinned compatibility adaptation | Exactly one exchange/client/account, native liquidity_consumption=True |
| Upstream factory name routing | TradingNodeBuilder injects portfolio only for literal SandboxLiveExecClientFactory name | Pinned compatibility documented | Private finite factory uses expected name and validates fixed config |
| LGPL adapted constructor | Upstream constructor provenance | Parent requested mixed-license artifacts | Exact license/source attribution and package metadata added before packaging |

## Verification Results

### Incremental Verification

| Command / Method actually executed | Result | Evidence |
|---|---|---|
| `python/.venv/bin/pytest -q python/packages/quant-execution/tests/test_paper_runtime.py -x` initial | Exit1 | Exposed missing portfolio factory compatibility; fixed expected native factory name |
| Same native test after factory change | Exit1 | OrderInitialized emitted before cache insert; mapped native initialized event quantity0/statusINITIALIZED safely |
| Native continuous test after fixes | Exit0 | One real session accepted/full/partial/laterfill/cancel/duplicates/cleanup |
| `python/.venv/bin/pyright python/packages/quant-execution` from root without interpreter | Exit1 | Missing imports due interpreter discovery; no code success claimed |
| `python/.venv/bin/pyright --pythonpath python/.venv/bin/python python/packages/quant-execution` initial | Exit1 | Typed factory override incompatibility; replaced with base-compatible config+optional keyword portfolio narrowing |
| `/private/tmp/paper-smoke-diag.py` service fixture probe via venv Python | Exit0 after fix | BTC bid49999.9/ask50000 normalized to validated instrument precision; native start/stop balance10000 |
| Independent reviewer cleanstop probe | Initial failure (reviewer receipt) | Undrained native events were lost; fixed flush/drain/retention and regression test |
| Independent reviewer failure probe | Initial limitation (reviewer receipt) | Killed worker wrongly inherited complete stream/closed loop; fixed explicit incomplete fault and actual cleanup acknowledgment |
| Ruff incremental | Initial exits1, then0 | Import sorting/type exception style corrected; broad catches limited to documented process cleanup/failure boundaries |

### Verify Gate

| Attribute | Value |
|---|---|
| Kind | Real native integration pytest |
| Command | `python/.venv/bin/pytest -q python/packages/quant-execution/tests` |
| Exit / Result | 0 /33passed,10preexisting Pandas4Warning from offline Backtest |
| Status | Green scoped package |
| Evidence | 11new tests exercise actual installed1.231.0 TradingNode+Sandbox+SimulatedExchange;22existing regressions pass |

Manual UX Receipt: N/A.

### Complementary Checks

| Check | Command | Status | Evidence |
|---|---|---|---|
| Lint | `python/.venv/bin/ruff check python/packages/quant-execution` | Pass0 | All checks passed |
| Format | `python/.venv/bin/ruff format --check python/packages/quant-execution` | Pass0 | 13files formatted |
| Typecheck | `python/.venv/bin/pyright --pythonpath python/.venv/bin/python python/packages/quant-execution` | Pass0 | Zero errors/warnings |
| Whitespace | `git diff --check -- python/packages/quant-execution sdd/features/DESIGN_PAPER_NATIVE.md` | Pass0 | No whitespace diagnostics |
| Packaging/license inclusion | Workspace owner | Pass0 | Fresh wheel/sdist: exact license/NOTICE/source included; metadata MIT AND LGPL-3.0-only; lock unchanged; workspace owner receipt |

## Acceptance Test Verification

| ID / scoped scenario | Status | Evidence |
|---|---|---|
| AT-010 native independent lifetime | Pass native scope | Same node/process survives multiple separate wallclock commands; SDK/process E2E belongs to service integration |
| AT-014 exact persistent identities | Pass native scope | Supplied IDs equal native emitted IDs; duplicate rejected before second native dispatch |
| Native finite execution | Pass | Full .006 + partial .004 uses exactly .010initial ask; later explicit snapshot causes remaining .004native fill |
| Native event/account/position evidence | Pass | Native UUID/trade/position/account IDs, lastfillprice/qty, commission/currency; current native balance/free/netposition |
| Native market fill | Pass | Native full market fill with exact ID and real commission |
| Stop retains events | Pass | Undrained terminal fill still returned after actual clean join/loopclosed |
| Fault/overflow | Pass | Overflow protects, incomplete fault retained; stopfailed; killed/forced child cannot claim closed loop or complete event stream |
| Input validation | Pass | Invalid size/depth timestamp causes no native event/cash/position change |
| Startup failure | Pass | Invalid fixture raises, actual child reaped; failed state retained |
| AT-015 restarted recovery | Unaccepted by design | No empty Sandbox status report interpreted as flat; no reconstruction or automatic retry |

## Advisor Ledger

Reviewer paper_runtime_review independently found pre-cache initialized callback, signed Decimal quantity, clean-stop event loss, misleading loop_closed and worker-lost completeness. All were applied with regression tests. Final scoped receipt: sdd/reviews/REVIEW_PAPER_NATIVE_2026-11-17.md, delta ACCEPT for source hashes listed there. Parent requested process-safe official node and license artifacts; applied.

## Issues Encountered

Native live context forbids logging bypass; use ERROR logs. Native QuoteTick requires consistent representational precisions; validate then instrument.make_price/make_qty, never round invalid increments. No upstream trading examples executed.

## Deviations from Design

Parent-approved process/compatibility/license changes are recorded above and in design before corresponding implementation. No hidden scope change.

## Derivatives and owner-death delta

Parent required a native-authoritative derivative valuation rather than spot notional cash. Snapshot now includes fresh native realized_pnl (NET commissions), unrealized_pnl (long bid / short ask), equity=wallet+unrealized, raw native balance_free and explicit conservative available_equity=min(balance_free,balance_free+unrealized). This includes adverse marks without crediting positive unrealized for available capacity. Tests prove opening cash changes fees only, long mark/close, aggregate net realized after close, adverse short mark and available equity.

Daemon cleanup alone does not cover service SIGKILL. A separate child watchdog thread watches multiprocessing's parent sentinel outside the native loop; it cancels the main native task and self-exits70 if cleanup stalls2seconds. Two real subprocess tests kill the service owner after dispatch, with native loop responsive and deliberately blocked60seconds; both verify actual native PID disappears. No other process is signaled. First attempt to inspect process state using ps was denied by macOS sandbox (PermissionError); test uses permitted kill(pid,0) and requires ProcessLookupError. One crash run displayed resource_tracker's expected cleanup warning for9semaphores after killed owner; latest two-case run passed without warning. This is owner-loss teardown, not session reconstruction.

Latest scoped result:11native tests /33total execution tests pass14.22s; latest Ruff/format/Pyright all exit0. Independent reviewer also reran33tests and long/short valuation plus responsive/blocked-loop ownerdeath probes, all0; final delta ACCEPT. Workspace agent reports fresh license artifacts0 and unchanged lock0; no install performed by native implementer.

## Final GPL base terms correction

Parent requested exact GPLv3 terms incorporated by LGPLv3. Manifest row12 was added before copying. Default restricted `curl --fail --location --max-time20 https://www.gnu.org/licenses/gpl-3.0.txt --output /private/tmp/bybit-gpl-3.0.txt` failedDNS(exit6); the approved network retry completedexit0,35149bytes. Exact copied package text SHA-256: `3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986`. NOTICE records authoritative URL/retrieval date/hash and preserves original MIT scope. Existing license-files wildcard includes GPL text. No runtime source changed after final independent delta acceptance. Final rebuild `uv build --offline --project python/packages/quant-execution --out-dir /private/tmp/bybit-native-license-final` first failed2 under default sandbox (uv cache temporary write denied); approved offline retry succeeded0. Python stdlib zip/tar byte comparison exited0: MIT/LGPL/GPL/NOTICE equal source in both artifacts; wheel metadata License-Expression is MIT AND LGPL-3.0-only; adapted paper_sandbox.py source matches. NOTICE SHA-256 `7c71b27ec096da3473bbf62ea642936417c0c52c14a35a901805afdec8299d69`. No application dependency, lock or runtime changes for this correction.

## Blockers

None within scoped native manifest. Independent final delta ACCEPT recorded; final wheel/sdist license/notice byte equality passed. Root aggregate verification/security/SBOM/publication belongs to parent; this report does not claim it.

## Final Status

### Overall: COMPLETE (scoped native foundation)

All scoped code/test manifest tasks implemented; scoped native verification green and independent final delta ACCEPT recorded. Final exact license/notice wheel/sdist artifact gate passed. Full reliable durable replay, crash reconstruction and nonflat session recovery remain unimplemented and explicitly unaccepted. The bounded event overflow policy is protect+immutable incomplete fault, not durable replay. Demo/Testnet/Mainnet connectivity and trading are not implemented or tested here. No application dependency change, lock edit, migration, commit or push by native agent.


- [x] All12 scoped manifest tasks completed
- [x] Actual incremental failures/fixes recorded
- [x] Native/package Verify Gate green (33tests)
- [x] Ruff/format/Pyright applicable checks passed
- [x] Scoped acceptance scenarios verified; full recovery/product gaps explicit
- [x] No LLM prompt work in this slice
- [x] Parent-approved design drift recorded before changes
- [x] Independent findings applied; final delta ACCEPT
- [x] Exact final license artifacts verified in wheel and sdist
- [x] No unresolved scoped blocker or unfinished code placeholder

## Next Step

Execute o **SDD Handoff by RDD**.
