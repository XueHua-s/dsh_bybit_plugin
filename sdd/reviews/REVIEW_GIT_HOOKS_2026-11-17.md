# Independent review: Git hooks

Date: 2026-11-17. Reviewer scope: `.githooks/pre-commit`, `.githooks/pre-push`, `scripts/git-hooks.ts`, `scripts/test-git-hooks.ts`, `scripts/tsconfig.json`, design and root script integration. Review-only ownership: this report; no source edits, user index changes, real commit/push, credentials or trading requests.

## Verdict

Scoped independent review ACCEPT. Hook safety and final monorepo gate wiring satisfy this review scope; all identified findings are closed. Actual aggregate command outcomes remain the integration owner's responsibility. This is not a release approval or proof of hook installation.

## Findings communicated to owners

1. Root `verify`, `typecheck`, `lint`, and `test:unit` initially targeted only `@bybit-quant/dsh-plugin`. Latest `verify` now includes `sdk:test`, `sdk:check` and tooling gates, closing the missing SDK runtime tests. However root `typecheck` still targets only the plugin and its explicit `dependsOn: ["^build"]` does not prove independent dependency typechecks. SDK build excludes `scripts/` and `test/`; contracts build excludes tests. SDK scripts/test and contracts test type errors can escape pre-push; SDK full lint is also absent. Broaden root typecheck/lint composition to explicit TS project targets. Status: CLOSED after final manifest re-inspection: root typecheck explicitly runs all three TS projects; root lint runs plugin and SDK Nx lint targets plus `oxlint scripts packages/ts/quant-contracts`. SDK full tsconfig includes src/scripts/test; contracts full tsconfig includes source/tests. Root verify invokes this composition and the SDK test target.
2. Design says nested `.env*`; initial sensitive-path expression rejects `.env` and `.env.*`, but not `.envrc` or `.env-production`. Align the predicate with the stated conservative rule or explicitly narrow the design. Status: CLOSED; latest predicate uses `/^\.env/i`.
3. Root package initially lacks `type: module`; Node 22.20.0 executes the ESM TypeScript successfully through syntax detection but prints `MODULE_TYPELESS_PACKAGE_JSON`. Add explicit module declaration for a clean ESM tooling boundary. Status: CLOSED; root now declares `type: module`, and the rerun has no warning.

## Verified evidence

| Actual command or isolated experiment | Exit | Result |
|---|---:|---|
| `node scripts/test-git-hooks.ts` | 0 | Latest rerun: nine isolated fixture scenarios pass, including pnpm/uv failure and newline/metacharacter filenames; temporary repositories cleaned up |
| `node node_modules/typescript/bin/tsc -p scripts/tsconfig.json` | 0 | Strict inherited settings, unchecked index access, exact optional properties, Node 22 typings; fixture assertions also compile |
| `sh -n .githooks/pre-commit .githooks/pre-push` | 0 | Both shell launchers parse; filesystem executable bits present |
| `node_modules/.bin/oxlint scripts/git-hooks.ts scripts/test-git-hooks.ts` | 0 | Focused tooling lint passes |
| Independent Python temporary-copy harness running Node fixture with newline, shell substitution/semicolon, and option-like filenames | 0 | All seven scenarios still pass, argv preserved as individual values |
| Independent Python temporary-copy harness adding failing pnpm lint and pre-push verify (child exits 23) | 0 | Both hooks return 1, checks fail closed; eight scenario groups pass |

Independent harnesses copied only the two hook TS sources to a newly created temporary directory, changed the copy of fixture inputs, ran Node with stdout/stderr captured, printed only pass summaries and integer status, and removed the directory in `finally`. No actual repository staging was performed.

## Safety and architecture assessment

NUL-delimited filename parsing and `execFileSync` arrays avoid shell interpolation. `--` separates filenames from options. Sensitive names are checked from Git's filename-only query before obtaining the content diff. Scanner failures and missing executable errors become constant messages; scanner stdout/stderr are always captured and discarded, including the deliberately hostile scanner fixture. Real gitleaks rejects a random synthetic fixture without revealing its value. Assertion diagnostics contain booleans/statuses/argv, never synthetic secret values.

Staged TS sources across `apps/`, `packages/ts/`, and `scripts/`, and Python sources under `python/`, receive appropriate lint checks. TS/Python paths with unstaged edits are refused before lint, and fixture tree hashes prove the index remains unchanged. Python pre-push lint/typecheck/test scripts cover both `python/packages` and `python/apps`. No skip flag remains, and absence/failure of required tools blocks. Final root composition closes the independent TS package coverage finding above; actual task execution results are reported separately by the integration owner.

Module boundaries are simple: shell callers specify only a mode; one short policy module hides filename framing, sensitive-path policy, scanner handling and task dispatch. Strict TS tooling and fixtures are below the 500-line limit; no `any` escape was introduced. Software-design-philosophy score: 10/10 (8/8 diagnostic rows pass after corrections). Initial implementation-change-isolation concern was the implicit incomplete root composition; explicit root TS project selection and complete lint paths now close it. Policy, scanner and filename handling remain centralized, and callers retain the simple mode interface. No failed diagnostic row remains in this scope.

## Remaining limits

No full root pipeline, network exchange test, dependency installation, Git hook installation, SBOM/security scan or release gate was performed by this reviewer. Gitleaks is heuristic; these tests demonstrate the redaction/failure boundary, not universal secret detection. Full integration remains the parent agent's responsibility.

## Coordinated CI static review

At the hook author's request, reviewed `.github/workflows/ci.yml` without editing it. The added scanner downloads a pinned gitleaks 8.30.1 release over HTTPS with fail-on-error curl, verifies a hardcoded 64-hex SHA256 before extraction, quotes temporary paths and installs via `GITHUB_PATH`. Checkout obtains full history; scanner failure blocks, redaction and ignore-inline-allow flags are present. The official checksum's network provenance was not independently fetched by this reviewer. CI invokes root verify, TS test typecheck, Python Nx lint/typecheck/test including quant-execution, schema drift, formatting and existing dependency/SBOM commands. Final root independent TS typecheck/lint wiring closes the previous gap; root verify invokes it. No workflow run or successful CI result is claimed. Existing nonblocking public Testnet smoke is explicitly separate and does not authorize live orders.

Latest source reruns: `node scripts/test-git-hooks.ts` exit 0 (9 checks); `node node_modules/typescript/bin/tsc -p scripts/tsconfig.json` exit 0; `git diff --check -- .githooks scripts .github/workflows/ci.yml sdd/reviews/REVIEW_GIT_HOOKS_2026-11-17.md` exit 0.

## Final re-review

Re-read final root package scripts and both relevant Nx project definitions after the integration changes. Root `typecheck` now explicitly selects all three TS project targets. Root `lint` includes plugin, SDK (src/scripts/test), root scripts and contracts. `verify` composes those with SDK generation drift/tests and tooling tests; CI and pre-push call that composition. Hook safety rerun still reports 9 checks, exit 0; direct tooling strict typecheck exit 0. No further source changes requested. Final scoped verdict: ACCEPT. Full aggregate gates, security/SBOM and runtime/release conclusions remain outside this review's independently executed evidence.
