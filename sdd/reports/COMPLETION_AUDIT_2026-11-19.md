# Completion audit: DSH Bundle packaging and Mainnet OAuth

Date: 2026-11-19
Overall status: **PARTIAL**

This report is chronological: earlier increment summaries are historical
snapshots, and later follow-up sections supersede them where stated.

## Completed in this increment

- Added environment-aware Bybit OAuth for Testnet and Mainnet with PKCE,
  refresh, explicit account selection and isolated credential storage.
- Kept Mainnet order execution disabled by default.
- Added UI readiness disclosure and corrected plugin descriptions so the
  conversation-triggered workflow is not presented as unattended automation.
- Closed the direct TypeScript Bybit writer: trade requests stay local previews,
  and write intent fails before exchange access. The 98-case cutover matrix and
  packed Bundle scan passed; Python/Nautilus is not yet an exchange writer.
- Added an offline-only Testnet profile/projection/preflight contract. It uses
  fixtures, always reports `order_submission_allowed: false`, and does not yet
  include a production credential provider or signed HTTP transport.
- Isolated Mainnet environment-variable credential lookup from Testnet names;
  live configuration now defaults to `BYBIT_MAINNET_API_KEY` and
  `BYBIT_MAINNET_API_SECRET`, with a negative regression test for reuse.
- Updated English and Chinese README/detail text with Mainnet OAuth commands,
  path isolation and verification limits.
- Ran TypeScript, Python, bundle, SDK, SBOM, dependency, secret and whitespace
  checks; all recorded commands passed.

## Remaining blockers to the original goal

- No persistent background AI scheduler or restart-safe unattended strategy loop.
- No authenticated native Testnet order writer; Python/Nautilus is not yet an
  exchange execution authority. The TypeScript fallback writer is now closed.
- The signed Testnet read-only adapter now exists as a separate package slice,
  but it has no production credential resolver or DSH Host integration. The
  selected account also fails the online preflight, and complete report/
  reconciliation acceptance remains open.
- Complete portfolio/OMS, account/order reconciliation, recovery and audit
  closure are not accepted.
- Mainnet OAuth grant, token exchange, and the read-only account-list endpoint
  were exercised against the provider. The account list returned empty; no
  Mainnet sub-account was selected or created and no real order was sent.
  Testnet OAuth and signed identity/wallet reads were
  re-verified for the selected Testnet sub-account, which reported zero
  equity/USDT, so no Testnet order success is claimed.
- The repository requires independent explicit authorization for each real
  trade, and the plugin has no order-confirmation flow. Mainnet writes and
  unattended Mainnet trading therefore remain disabled.
- Official Host service `updateBundle` activation/rollback/state-preservation
  remains unverified; active Harness profile was not changed during this audit.

## Follow-up verification — 2026-11-19

The additional offline Testnet preflight slice passed 317 Python tests, full
Python Ruff/format and Pyright checks, and `NX_DAEMON=false
NX_ISOLATE_PLUGINS=false pnpm run verify` (all exit 0). `gitleaks git --redact`
and `gitleaks dir --redact --no-banner --ignore-gitleaks-allow .` also exited 0.
These runs did not make an exchange request. The production provider and online
preflight remain unimplemented; account state and execution readiness remain
unknown.

The correct product conclusion remains **PARTIAL**: OAuth support and the
TypeScript writer closure are locally implemented, while the full unattended AI
quantitative trading platform is not complete.

## OAuth and desktop recheck — 2026-11-19

| Command or check | Exit | Result |
|---|---:|---|
| `pnpm --filter @bybit-quant/dsh-plugin oauth -- --env=live accounts` | 0 | Read-only AI sub-account list returned 0 entries. No account was selected or created. |
| Chrome Testnet OAuth page | Success screen observed | Bybit reported that an access token was sent to `ai-agent`; its value unexpectedly appeared in accessibility output. It was not copied into a local file or this report. Treat it as exposed and revoke before unattended use. |
| `pnpm --filter @bybit-quant/dsh-plugin oauth -- --env=testnet exchange` | 1 | Local CLI found no OAuth callback state, so its token exchange could not be verified. |
| `pnpm --filter @bybit-quant/dsh-plugin oauth -- --env=testnet accounts` | 1 | Local CLI could not validate local Testnet token state; account-list state and count remain unverified. |
| Referenced architecture attachment | Not available | The attachment was absent from the task environment. This audit uses the repository's SDD artifacts and does not claim the external attachment was reviewed. |

No account creation, account selection, or order submission was performed during
this recheck. The browser success page does not prove that this CLI has a usable
local token or account state. Product status remains **PARTIAL**; OAuth grant
support alone does not establish trading readiness or unattended execution.

## Superseding Testnet follow-up — 2026-11-19

The OAuth and desktop recheck above was superseded by a later successful
Testnet flow: the local callback exchange and account listing succeeded, and
the explicitly selected AI subaccount was `107209442`. Its OAuth/credential
files were private (`0600`). Mainnet remains separate: the read-only account
list was empty, with no Mainnet subaccount selected or created and no Mainnet
write attempted.

A one-off signed GET diagnostic against the selected Testnet key confirmed the
subaccount UID but did not establish readiness. The account key is not a Unified
Trading Account key, has no IP allowlist, and includes transfer plus other
active scopes beyond linear trading. The Unified wallet read returned zero but
is not accepted as collateral evidence because the key reports `unified=false`.
The adapter now parses the observed expiry/IP response forms and explicitly
denies unrestricted IP markers and excessive scopes. Final preflight status was
`denied` with `account_type_unsupported`, `ip_binding_missing`, and
`permissions_unknown_or_excessive`; order submission remained false. No order
was sent. This temporary-resolver diagnostic does not mean the DSH Host runtime
has a production credential resolver or a native Testnet execution authority.

The final offline gate for this follow-up passed: `pnpm python:test` exited 0
with 337 tests and 11 warnings; Python lint and Pyright, root `pnpm run verify`,
`gitleaks dir --redact --no-banner --log-level error .`, and `git diff --check`
also exited 0. The remaining warnings are dependency/runtime deprecations in
FastAPI/Starlette and Nautilus-backed tests, not failures in the provider slice.

The DSH UI audit remains **PARTIAL**: the Host Plugin Manager service-level
upgrade/rollback and state-preservation path is not yet evidenced, and the UI
still needs to distinguish account compatibility and persistent automation
readiness from a successful OAuth connection.
