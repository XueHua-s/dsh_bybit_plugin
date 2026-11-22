# Build report: Git hooks

Date: 2026-11-17. Status: scoped implementation verified; complete repository Verify Gate and independent review remain with the integration owner.

## Mode selection and requirements

The parent assigned this isolated tooling slice within the authorized ongoing engineering work. No extra agent was spawned. AGENTS.md, project `sdd-build`, `software-design-philosophy`, and the original Brainstorm/Define/Design requirements were consulted. This slice closes recorded monorepo hook and credential-logging drift without changing trading or credential configuration. No migration, commit, push, installation or official Plugin Manager claim is made.

## Implemented manifest

Thin shell hooks now dispatch to `scripts/git-hooks.ts`. The module checks nested sensitive staged paths before diff reading, scans with gitleaks stdin/redaction, suppresses scanner diagnostics, preserves filenames as argv, blocks partial staging instead of altering the index, runs appropriate TypeScript/Python lint, and uses current workspace pnpm scripts. Pre-push scans committed history and uses tsdown wording. Old bypass hints and the skip flag are removed.

`scripts/tsconfig.json` checks the actual tooling in strict mode. Root package owner added `typecheck:tooling`, `test:tooling` and Node 22 type dependencies; root manifest/lock changes were not made by this slice. Tests use temporary Git repositories only.

## Real verification evidence

| Command | Exit | Result |
|---|---:|---|
| `node scripts/test-git-hooks.ts` | 0 | Nine isolated fixture checks pass; real gitleaks 8.30.1 rejects synthetic random token, scanner output never relayed |
| `pnpm run typecheck:tooling` (initial run) | 0 | Strict tooling compile passed |
| `pnpm run typecheck:tooling` (later rerun after concurrent manifest changes) | 130 | pnpm unexpectedly attempted dependency installation; registry DNS unavailable; interrupted rather than treating as passed |
| `node node_modules/typescript/bin/tsc -p scripts/tsconfig.json` (latest source) | 0 | Direct installed compiler verifies current tooling without dependency installation |
| `node_modules/.bin/oxlint scripts/git-hooks.ts scripts/test-git-hooks.ts` | 0 | Current tooling lint passed |
| `sh -n .githooks/pre-commit .githooks/pre-push` | 0 | Shell launchers parse |
| `git diff --check` | 0 | No whitespace errors |

## CI integration increment

The parent explicitly extended ownership to `.github/workflows/ci.yml`; the design manifest was extended before editing it. CI now runs shared root `pnpm run verify` including SDK checks/Vitest and actual tooling checks/tests, retains test typechecking and all security/SBOM/OpenAPI gates, and includes `quant-execution` in Python Nx targets. Existing optional public Testnet smoke remains unchanged. Root verify now owns SDK/tooling checks, so duplicate pre-push invocations were removed.

The main verify job uses ubuntu-24.04 x64, installs official gitleaks 8.30.1 before tooling fixtures, and downloads full Git history for a redacted secret scan. Official release checksum source was retrieved successfully (exit 0): `https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_checksums.txt`. The Linux x64 archive was independently downloaded to `/tmp` and its SHA256 matched the committed pin `551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb`; the downloaded binary was not executed locally. Local YAML parse, install-step `bash -n`, task wiring assertions and archive SHA256 assertion passed (exit 0). Hosted GitHub Actions execution remains unverified.

Fixture assertions include newlines/shell metacharacters/spaces preserved as a single filename argument, unchanged fixture index tree, rejection before any content-diff query for nested `.env.production`, refusal of partial staging, pnpm/uv lint failures, unavailable scanner failure, malicious scanner stdout/stderr suppression and correct pre-push workspace task selection. The fixtures never expose generated token values. Root owner subsequently added `type: module`; the latest Node run has no module-type warning.

## Verify Gate and unresolved work

The original full product `pnpm run verify` was not run by this slice; focused hook checks cannot replace it. Root integration must run its coordinated pipeline, review root verify coverage for reusable TS packages, handle dependency installation state and run CI/release checks. The real hooks were not invoked against the user's staged index to avoid reading an unknown sensitive staged diff; fixture hooks exercise both modes safely. Hook installation is unverified.

No user credentials were read, no user's index/worktree was stashed or rewritten, and no exchange request or order was sent. Design and report were reviewed for consistency with the actual focused checks. Final status: scoped tests PASS; full integration/release acceptance PENDING.
