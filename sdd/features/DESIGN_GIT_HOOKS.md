# Design: monorepo Git hooks

Date: 2026-11-17. Scope: local developer gates supporting DEFINE_BYBIT_AI_QUANT AT-001, AT-002 and credential protection (AT-008/009). This is not proof of the complete product or a release approval.

## Drift recorded

The previous hooks restricted lint to root `src/`, printed matched secret-bearing lines, referenced removed `credentials.mjs`, used npm/npx, labelled the build tsup, and offered bypass instructions. The monorepo requires apps/packages/Python/tooling checks and prohibits credential logging. The old pre-push opt-out silently skipped all checks.

## Boundary and decisions

Two executable shell entrypoints only dispatch to one strict TypeScript policy module. The module owns NUL-separated Git filename parsing, sensitive filename denial, redacted scanner invocation, filename-safe child argv, and workspace task names. Child failures do not serialize errors or scanner output. Sensitive filenames are rejected before reading diff contents, including nested `.env*`, private-key extensions and credential data filenames; source tooling `credentials.ts` remains editable.

Pre-commit scans the staged diff with `gitleaks stdin --redact --ignore-gitleaks-allow`; absent/failing scanner blocks. TypeScript lint covers `apps/`, `packages/ts/`, `scripts/`; Python Ruff lint and format checks cover staged `python/**/*.py`. Linters read the worktree, so staged source paths with unstaged changes are rejected without stashing, changing the index or rewriting files. Workspace and tooling strict typechecks follow.

Pre-push scans committed history with redacted gitleaks, then calls existing pnpm tasks: `verify` (tsdown build, SDK checks/tests and tooling checks/tests), `typecheck:tests`, `python:lint`, `python:typecheck`, `python:test`. Shared gates are not repeated after verify. No live-network exchange tests or order calls are added. No bypass flag is provided. Root owns verify composition and dependency installation; missing tooling blocks rather than silently passing.

## Manifest

| Path | Purpose |
|---|---|
| `.githooks/pre-commit`, `.githooks/pre-push` | Thin shell launchers |
| `scripts/git-hooks.ts` | Policy and safe process orchestration |
| `scripts/tsconfig.json` | Strict root tooling compile gate |
| `scripts/test-git-hooks.ts` | Isolated temporary Git repositories and safe synthetic fixtures |
| `sdd/reports/BUILD_REPORT_GIT_HOOKS.md` | Real command results and limits |
| `.github/workflows/ci.yml` | Shared root verify pipeline, all Python projects, pinned/checksummed real gitleaks installation and scan |

Root package scripts/dependency wiring is coordinated with its separate owner; this slice does not edit the manifest, lockfile, Git hook installation configuration or managed DSH profile.

### CI integration increment

CI installs official gitleaks 8.30.1 Linux x64 using a SHA256 pinned from the official release checksum file, then runs a redacted full-history secret scan and root `pnpm run verify`. The real scanner is mandatory for tooling fixtures. Python Nx gates explicitly include `quant-execution`; OpenAPI drift, formatting, dependency audit and TS/Python SBOM gates remain. Fetching full Git history makes the secret scan meaningful. Existing optional public Testnet smoke remains separate and cannot send orders.

## Verification and complexity

Nine fixture scenarios cover rejection before reading sensitive contents, newline/shell metacharacter/space argv preservation and unchanged index, pnpm and uv lint failures, partially staged rejection and unchanged index, hostile scanner output suppression, absent scanner failure, real gitleaks synthetic detection, and the pre-push pipeline task list. Fixtures never read a user credential, commit, push, or send an order. All fixture repositories are removed in `finally`.

Software-design-philosophy diagnostic: 10/10 (8/8 rows). Shell callers know only a mode; the policy module hides command construction, filename framing, scanner suppression and workspace selection; tests own their temporary environment. No failed diagnostic row is currently identified. Independent integration review remains required; this internal diagnostic is not external acceptance.

## Limits

Gitleaks is a heuristic detector, not proof that arbitrary secrets cannot exist. Local hooks can be bypassed externally and do not replace CI/release gates. Whole-history pre-push scanning can block on old findings requiring explicit remediation. This change does not prove hook installation or execute a real commit/push. pnpm can attempt dependency installation when its installation state is stale; the integration owner must record any unavailable dependency gate honestly.
