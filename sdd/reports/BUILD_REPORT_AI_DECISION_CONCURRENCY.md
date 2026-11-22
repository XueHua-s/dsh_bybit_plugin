# BUILD REPORT: Concurrent AI decision writes

## Scope

The local simulated AI journal now uses an optimistic compare-and-swap guard.
When a decision was evaluated against an older track, the write is rejected
and the newer track remains intact. Successful persistence still precedes the
cycle receipt; failed persistence restores the attempted replacement only when
it is still the current value.

## Verification

| Command | Exit | Result |
|---|---:|---|
| First `pnpm --dir apps/dsh-plugin run verify` | 1 | New test expected a store-write event on conflict; the guard correctly rejected before calling the store mutation. The assertion was corrected. |
| Second `pnpm --dir apps/dsh-plugin run verify` | 0 | Build, lint, source/test typecheck, unit tests, and Bundle check passed. Five existing lint warnings remain. |
| Third `pnpm --dir apps/dsh-plugin run verify` | 1 | A lint-only failure found an unused local in the newly added concurrent-failure test; no test assertion had run yet. |
| Final `pnpm --dir apps/dsh-plugin run verify` | 0 | After removing the unused local, build, lint, source/test typecheck, all unit tests (including 4 decision-writer checks), and Bundle check passed. Five existing lint warnings remain. |
| `CI=1 NX_DAEMON=false pnpm run verify` | 0 | Nx build, lint, typechecks, plugin tests, Bundle/API/SDK checks and tooling tests passed. |
| `git diff --check` | 0 | No whitespace errors in tracked changes. |
| `rg -n '[[:blank:]]+$' apps/dsh-plugin/src/lib/ai-decision-writer.ts apps/dsh-plugin/test/ai-decision-writer.ts sdd/features/DESIGN_AI_DECISION_CONCURRENCY.md sdd/reports/BUILD_REPORT_AI_DECISION_CONCURRENCY.md` | 1 | No matches; exit 1 is `rg`'s no-match result, confirming no trailing whitespace in the new/untracked files. |
| `pnpm --dir apps/dsh-plugin run verify` (sequential scenario added) | 0 | Build, lint, source/test typecheck, unit tests, and Bundle check passed. Five existing lint warnings remain; the decision-writer suite now reports 5 checks. |
| `CI=1 NX_DAEMON=false pnpm run verify` | 0 | Root Verify Gate passed; Nx build, lint, typechecks, DSH unit tests, Bundle/API/SDK checks and tooling tests succeeded. |
| `git diff --check` | 0 | No whitespace errors in tracked changes. |
| Python trailing-whitespace scan of modified test/report | 0 | No trailing whitespace found in either modified file. |

## Acceptance evidence

- Existing failure-path test verifies that a state-file error restores the
  previous track and emits no receipt.
- The concurrent-failure test verifies that if a newer state is visible when a
  write fails, conditional rollback leaves that newer state intact.
- New conflict-path test verifies that a stale track is rejected, the newer
  track is preserved, and no receipt is committed.
- The concurrent-failure test invokes the mutation callback before throwing and
  verifies that conditional rollback does not overwrite the newer track.
- Existing success-path test verifies store-write before receipt commit.
- Sequential stale-write test verifies a successful first decision keeps its
  single receipt when a second write uses the old snapshot and is rejected.

## Independent review

The independent review found no blocking defect in the current `createStore`
implementation. It confirmed compare-before-write, conditional rollback, and
store-write-before-receipt ordering. It identified the sequential
first-success/second-stale scenario as a low-priority test gap; this revision
adds that case. Custom Store implementations that clone reads or persist
partially before raising are not covered by the current concrete store contract.

## Limits

This is a guard for the internal simulated journal. It does not provide a
database transaction, exchange order idempotency, account reconciliation,
Nautilus execution, or unattended Testnet trading.
