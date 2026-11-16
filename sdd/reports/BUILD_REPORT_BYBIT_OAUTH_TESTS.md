# BUILD REPORT: Bybit OAuth CLI Mock Tests

## Metadata

| Attribute | Value |
|---|---|
| Feature | BYBIT_OAUTH_TESTS |
| Date | 2026-11-17 |
| Scope | Local-only OAuth CLI regression coverage |
| Status | Complete for the scoped test increment |
| Design references | `sdd/features/DEFINE_BYBIT_AI_QUANT.md`, `sdd/features/DESIGN_BYBIT_AI_QUANT.md` |

## Summary

Added three fake-backed OAuth tests covering PKCE S256 challenge construction, state mismatch rejection, Testnet token exchange configuration without a client secret, and preservation of the existing token file when refresh fails. Test data uses temporary directories and synthetic token strings. The callback test binds only to `127.0.0.1`; the overridden `fetch` rejects any unexpected outbound request. No Bybit endpoint was contacted, no OAuth flow was run, and no production secret or token was read or changed.

The test module is 100 lines, below the 500-line cap. Its design-philosophy diagnostic is **10/10**: it has one clear purpose, uses the existing OAuth boundary directly, keeps test data in temporary storage, replaces the outbound transport at the test boundary, and documents why loopback is used.

## Files Changed

| File | Action | Purpose |
|---|---|---|
| `apps/dsh-plugin/test/oauth.ts` | Create | Fake-backed OAuth regressions; no production secret/token access |
| `apps/dsh-plugin/package.json` | Modify | Add OAuth test to package unit-test command |
| `apps/dsh-plugin/project.json` | Modify | Add OAuth test to the Nx unit-test target |
| `sdd/reports/VERIFY_GATE_2026-11-17.md` | Modify | Record current OAuth test and full gate evidence |
| `sdd/reports/BUILD_REPORT_BYBIT_OAUTH_TESTS.md` | Create | This scoped evidence report |

No production OAuth source was changed.

## Verification Results

| Command | Exit | Result |
|---|---:|---|
| `pnpm --filter @bybit-quant/dsh-plugin build` | 0 | OAuth module built into local `dist`; no runtime OAuth invocation |
| `pnpm --filter @bybit-quant/dsh-plugin exec node test/oauth.ts` | 0 | 3 scenarios passed; no external fetch performed |
| `pnpm --filter @bybit-quant/dsh-plugin typecheck:tests` | 0 | Strict test typecheck passed |
| `pnpm --filter @bybit-quant/dsh-plugin exec oxlint test/oauth.ts` | 0 | No lint findings |
| `pnpm run verify` | 0 | Build, lint, production typecheck, unit tests and bundle check passed; unit target includes the OAuth tests |
| `git diff --check` | 0 | No whitespace errors |
| `wc -l apps/dsh-plugin/test/oauth.ts` | 0 | 100 lines |

An initial focused run returned exit 1 because the fixture had an already-expired refresh token and therefore never reached the fake refresh response. The fixture was corrected to represent an expired access token with a still-valid refresh token; the final focused run and full Verify Gate then passed.

## Acceptance Evidence

| Scenario | Result | Evidence |
|---|---|---|
| PKCE challenge is SHA-256/base64url of the stored verifier and advertises S256 | Pass | Derived challenge equals the authorization URL parameter |
| Mismatched state is rejected | Pass | Local callback returns 403, persists only an error marker, and exchange rejects |
| Token exchange remains Testnet-only and omits any client secret | Pass | Fake fetch captures the fixed Testnet URL and exact three form fields: client_id, code, code_verifier |
| Failed refresh does not overwrite the existing token | Pass | Fake error response rejects and token file bytes remain identical |

## Limits and Final Status

The local callback listener is exercised over loopback to test the real callback handler. All outbound transport is fake; the test does not validate Bybit's remote OAuth service, authorization grant, or real credentials. The repository contains unrelated pre-existing worktree changes; this increment did not stage or commit files.

**Final status: COMPLETE for the scoped OAuth test increment.**
