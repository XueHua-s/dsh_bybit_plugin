# Build report: Bybit Mainnet OAuth support

Date: 2026-11-19
Scope: environment-aware Bybit AI-agent OAuth client and readiness disclosure
Status: **Scoped complete; real Mainnet OAuth and read-only account-list request verified; no account was returned**

## Implemented behavior

- `BybitOAuth` supports `testnet` and `live` environments while retaining the
  `BybitTestnetOAuth` compatibility facade.
- Testnet uses `testnet.bybit.com` and `api2-testnet.bybit.com`; Mainnet uses
  `www.bybit.com` and `api2.bybit.com`.
- PKCE, state checking, token exchange, refresh, account listing and explicit
  AI sub-account selection are shared across environments.
- Mainnet OAuth state is isolated under `$DSH_HOME/bybit-quant/live/`; Testnet
  state remains under `$DSH_HOME/bybit-quant/`.
- Mainnet Host credential resolution is environment-scoped: it defaults to
  `BYBIT_MAINNET_API_KEY`/`BYBIT_MAINNET_API_SECRET` and rejects reusing the
  common Testnet variable names. Testnet retains the legacy names.
- Credential resolution fails closed on a partial environment pair, malformed or
  cross-environment credentials file, or partial Harness Credential Store pair;
  it never combines key halves from different sources.
- `env: live` defaults to isolated Mainnet credentials **and plugin state** at
  `$DSH_HOME/bybit-quant/live/credentials.json` and
  `$DSH_HOME/bybit-quant/live/state.json`, while `allowLiveTrading` remains
  `false` unless independently configured. Explicit path overrides remain
  available for advanced configuration.
- CLI usage is `oauth -- --env=live start|exchange|accounts|select ...`.
- The configured Mainnet host, OAuth paths, scope, PKCE and account-selection
  flow match the provider's current [AI-agent connection guide](https://www.bybit.com/en/learn/ai-subaccount/agent-connect),
  which was fetched successfully during this verification and contains both
  production and Testnet API endpoints.

## Verification

| Command | Exit | Result |
|---|---:|---|
| `pnpm --filter @bybit-quant/dsh-plugin build` | 0 | Mainnet/Testnet OAuth and UI bundle compiled |
| `pnpm --filter @bybit-quant/dsh-plugin exec node test/oauth.ts` | 0 | 7 local fake-backed scenarios passed; no external fetch |
| `pnpm --filter @bybit-quant/dsh-plugin exec node test/render.ts` | 0 | Real React SSR panel checks passed |
| `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm run verify` | 0 | Root TypeScript, bundle, SDK and tooling gate passed after the final Mainnet approval disclosure |
| `pnpm typecheck:tests` | 0 | Strict test-source typecheck passed |
| `node <read-only BybitClient probe>` | 0 | Existing Testnet selected-account credential matched sub-account `107209442`; signed identity and wallet reads succeeded; no non-zero equity or USDT was available, so no order was attempted |
| `node <provider guide fetch>` | 0 | Bybit guide returned HTTP 200 and contained `api2.bybit.com`, `api2-testnet.bybit.com`, and `ai-account` |
| `pnpm --filter @bybit-quant/dsh-plugin oauth -- --env=live start` | Long-running callback process | Official Mainnet AI-agent OAuth completed; callback state/verifier matched; no token values printed |
| `pnpm --filter @bybit-quant/dsh-plugin oauth -- --env=live exchange` | 0 | Real Mainnet authorization code exchanged; token stored mode `0600` in isolated `live/` directory |
| `pnpm --filter @bybit-quant/dsh-plugin oauth -- --env=live accounts` | 0 | Real read-only Mainnet account endpoint succeeded and returned an empty list; no account selected or created |
| OAuth credential preservation regression | 0 | Six mock-backed scenarios pass, including malformed and cross-environment files remaining unchanged |
| `pnpm python:lint` | 0 | Ruff check and format check passed |
| `pnpm python:typecheck` | 0 | Pyright reported 0 errors |
| `pnpm python:test` | 0 | 289 passed, 11 upstream warnings |
| `pnpm run security:deps` | 0 | Dependency scans reported no known vulnerabilities; editable packages skipped by pip-audit |
| `pnpm run sbom` | 0 | TypeScript SBOM generated with 200 components |
| `gitleaks dir --redact --no-banner --log-level error .` | 0 | No secrets found |
| `git diff --check` | 0 | No whitespace errors |

## Limits

OAuth tests use temporary files and fake transport. Seven mock-backed scenarios
completed with exit code 0. A first test invocation was started concurrently
with `build`, read the old `dist`, and failed on the new state-path assertion;
the required build → OAuth/SSR tests → typecheck sequence then completed with
exit code 0. A real Mainnet OAuth grant and token exchange
succeeded, and the real read-only account-list endpoint returned an empty list.
No Mainnet AI sub-account was selected or created, and no Mainnet order was sent.
After successful exchange, the callback-code and PKCE-init files were removed;
the live OAuth token remains local with mode `0600`.
The existing Testnet grant and selected account were re-verified with a signed
identity and wallet read; the account had zero equity/USDT, so no Testnet order
was attempted. OAuth support does not imply Mainnet trading readiness. The independent review still finds a direct
TypeScript REST order path, no persistent AI scheduler, no Mainnet per-order
confirmation-card flow, and no complete account/order reconciliation cutover
to the Python/Nautilus engine.
