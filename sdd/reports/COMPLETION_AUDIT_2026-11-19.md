# Completion audit: DSH Bundle packaging and Mainnet OAuth

Date: 2026-11-19
Overall status: **PARTIAL**

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
- The secure production provider, signed Testnet read-only transport, actual
  online preflight, and complete report/reconciliation proof remain unimplemented.
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
| `pnpm --filter @bybit-quant/dsh-plugin oauth -- --env=testnet accounts` | 1 | Current Testnet OAuth/account-list state was not verified. No account details or credential values are included here. |
| Chrome OAuth page inspection | Not run | The Chrome window showed an existing Testnet OAuth tab, but its page state was not read. macOS Accessibility and Screen Recording permissions for the desktop driver are disabled; login/consent state remains unverified. |
| Referenced architecture attachment | Not available | The attachment was absent from the task environment. This audit uses the repository's SDD artifacts and does not claim the external attachment was reviewed. |

No account creation, account selection, or order submission was performed during
this recheck. Product status remains **PARTIAL**; OAuth grant support alone does
not establish a usable account, trading readiness, or unattended execution.
