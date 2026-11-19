# Build Evidence: Quant Contracts Package

## Scope

Implemented the first real `packages/ts/*` workspace project, `@bybit-quant/quant-contracts`, and moved the existing normalized market category, candle, ticker, and instrument contracts behind it. The DSH plugin keeps its current import paths through type re-exports. No transport, account, order, Python, README, CI, bundle metadata, or external lifecycle behavior was changed.

## Design

The package owns only normalized domain DTOs already present in the app. It does not own Bybit wire parsing, credentials, or order/account API shapes. This makes it reusable without leaking transport or DSH concerns and avoids creating a speculative empty package. See the package-scope decision and 9/10 software-design diagnostic in `sdd/features/DESIGN_BYBIT_AI_QUANT.md`.

## Changed Files

| File | Change |
|---|---|
| `packages/ts/quant-contracts/package.json` | Added workspace package entry and ESM/type exports. |
| `packages/ts/quant-contracts/project.json` | Added independent Nx build and typecheck targets. |
| `packages/ts/quant-contracts/tsconfig.json` | Added strict source and contract-test typecheck. |
| `packages/ts/quant-contracts/tsconfig.build.json` | Added ESM and declaration output configuration. |
| `packages/ts/quant-contracts/src/index.ts` | Added normalized market DTOs. |
| `packages/ts/quant-contracts/test/contracts.test.ts` | Added positive contract examples and expected compile errors for invalid category/value types. |
| `apps/dsh-plugin/package.json` | Added local workspace dependency. |
| `apps/dsh-plugin/project.json` | Build shared package before app typecheck. |
| `apps/dsh-plugin/src/lib/bybit-types.ts` | Re-export shared DTOs and retain plugin-specific types. |
| `nx.json` | Build dependency projects before app builds. |
| `pnpm-lock.yaml` | Refreshed workspace lockfile for the new dependency. |
| `sbom.cdx.json` | Attempted scripted refresh; it remains unchanged because the repository's SBOM script cannot relaunch the pinned pnpm binary. |
| `sdd/features/DESIGN_BYBIT_AI_QUANT.md` | Recorded package boundary rationale and design score. |

## Verification Evidence

Commands ran in this workspace on 2026-11-17:

| Command | Exit | Result |
|---|---:|---|
| `pnpm install --lockfile-only` | 0 | Lockfile recognized all 3 workspace projects and passed supply-chain lock policy. |
| `pnpm nx show projects` | 0 | Discovered `@bybit-quant/quant-contracts`, `@bybit-quant/dsh-plugin`, `quant-data`, `quant-engine`. |
| `pnpm nx graph --file=/tmp/bybit-quant-graph.json` | 0 | Graph contains static edge `@bybit-quant/dsh-plugin` → `@bybit-quant/quant-contracts`. |
| `pnpm nx run @bybit-quant/quant-contracts:typecheck` | 0 | Package source and contract compile checks passed. |
| `pnpm exec tsc -p packages/ts/quant-contracts/tsconfig.json --noEmit` | 0 | Expected-negative DTO assertions passed; type errors were correctly rejected. |
| `pnpm --filter @bybit-quant/quant-contracts build` | 0 | ESM and declarations emitted. |
| `pnpm nx run @bybit-quant/dsh-plugin:typecheck --skip-nx-cache --output-style=static` | 0 | Contract package built first; plugin strict typecheck passed. |
| `pnpm build` | 0 | Both contract package and plugin build targets passed. |
| `pnpm typecheck` | 0 | Contract package and plugin typechecks passed. |
| `pnpm test:unit` | 1 (first run 0, rerun 1) | Initial run passed. After rebuilding the app output, rerun failed in existing `apps/dsh-plugin/test/client.ts` with `SyntaxError: Identifier 'plugin' has already been declared`; signal and AI suites completed before failure. |
| `pnpm typecheck:tests` | 1 | Existing app test typecheck reports many errors across tests (implicit anys, nullability and test fixture drift), including `client.ts`/`render.ts` declarations; scoped contract package typecheck is green. |
| `pnpm bundle:check` | 0 | Existing bundle static checks passed. |
| `pnpm verify` | 1 | Stopped at existing plugin lint target; no full Verify Gate pass. |
| `pnpm run sbom` | 1 | Existing script failed because its nested `pnpm list` could not launch pinned pnpm 12.6.0 (`ENOEXEC`, missing/invalid `.../.tools/pnpm/12.6.0/bin`). |

## Limits

This is a scoped package/build increment, not completion of the broader DEFINE. The plugin unit suite is not green on the rebuilt output, the app test typecheck is red, and the aggregate `pnpm verify` is red at lint. Official DSH Plugin Manager lifecycle, Python consumption, SBOM regeneration, security scans, and manual UI checks were not part of this scoped package verification.
