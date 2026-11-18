# Completion audit: DSH Bundle packaging and Mainnet OAuth

Date: 2026-11-19
Overall status: **PARTIAL**

## Completed in this increment

- Added environment-aware Bybit OAuth for Testnet and Mainnet with PKCE,
  refresh, explicit account selection and isolated credential storage.
- Kept Mainnet order execution disabled by default.
- Added UI readiness disclosure and corrected plugin descriptions so the
  conversation-triggered workflow is not presented as unattended automation.
- Isolated Mainnet environment-variable credential lookup from Testnet names;
  live configuration now defaults to `BYBIT_MAINNET_API_KEY` and
  `BYBIT_MAINNET_API_SECRET`, with a negative regression test for reuse.
- Updated English and Chinese README/detail text with Mainnet OAuth commands,
  path isolation and verification limits.
- Ran TypeScript, Python, bundle, SDK, SBOM, dependency, secret and whitespace
  checks; all recorded commands passed.

## Remaining blockers to the original goal

- No persistent background AI scheduler or restart-safe unattended strategy loop.
- TypeScript Host trade tools still provide a direct Bybit REST order path;
  Python/Nautilus is not yet the sole exchange execution authority.
- Complete portfolio/OMS, account/order reconciliation, recovery and audit
  closure are not accepted.
- Mainnet OAuth grant, token exchange, and the read-only account-list endpoint
  were exercised against the provider. The account list returned empty; no
  Mainnet sub-account was selected or created and no real order was sent.
  Testnet OAuth and signed identity/wallet reads were
  re-verified for sub-account `107209442`, which reported zero equity/USDT, so
  no Testnet order success is claimed.
- Bybit's current AI-agent guidance requires explicit user confirmation for
  each Mainnet trade; this plugin has no confirmation-card flow. Mainnet writes
  and unattended Mainnet trading therefore remain blocked by both product UX
  and the repository's authorization rule.
- Official Host service `updateBundle` activation/rollback/state-preservation
  remains unverified; active Harness profile was not changed during this audit.

The correct product conclusion is therefore **PARTIAL**: Mainnet OAuth client
support is implemented and locally verified, while the full unattended AI
quantitative trading platform is not complete.
