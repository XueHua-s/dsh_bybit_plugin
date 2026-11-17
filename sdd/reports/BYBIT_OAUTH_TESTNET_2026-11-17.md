# Bybit Testnet OAuth Verification

Date: 2026-11-18

## Provider contract

The Bybit AI-agent connection guide documents the Testnet OAuth base URL
`https://api2-testnet.bybit.com`, the `ai-agent` client, the `ai-account`
scope, PKCE with `S256`, a loopback callback for local agents, and explicit
AI sub-account selection after authorization.

Source: <https://www.bybit.com/en/learn/ai-subaccount/agent-connect>

The repository implementation keeps the OAuth token and selected Testnet
account credentials under `$DSH_HOME/bybit-quant/` with mode `0700` for the
directory and `0600` for private files. It does not print token or secret
values, does not place them in `cordis.patch.yml`, and rejects a token whose
environment is not `testnet`.

## Local verification

| Check | Command or observation | Result |
|---|---|---|
| PKCE URL construction | `pnpm --filter @bybit-quant/dsh-plugin oauth -- start` | Local callback bound to `127.0.0.1:9876`; URL contained `client_id=ai-agent`, `scope=ai-account`, `code_challenge_method=S256`, random `state`, and a Testnet origin. |
| Callback and exchange regression | `pnpm --filter @bybit-quant/dsh-plugin test:unit` | Exit 0; OAuth mock checks passed without external fetch. |
| Browser provider page | Chrome opened `testnet.bybit.com/oauth` | The authorization page showed AI Subaccount Trading allowed and Withdrawals not allowed. |
| First consent attempt | Browser reached the success page, but the local callback process had ended after the handoff | No callback file was present, so no token exchange was attempted. |
| Fresh consent and callback | Chrome completed the Testnet authorization page while the second local callback was running | Callback file was received and `pnpm --filter @bybit-quant/dsh-plugin oauth -- exchange` exited 0 without printing token material. |
| Account listing | `pnpm --filter @bybit-quant/dsh-plugin oauth -- accounts` | Exit 0; two AI sub-accounts were returned and presented for explicit selection. |
| Account selection | `pnpm --filter @bybit-quant/dsh-plugin oauth -- select 107209442` | Exit 0; selected credentials were stored in a local `0600` file without printing secrets. |
| Read-only Testnet identity and balance probe | Built `BybitClient` with the local Testnet credential file, `apiKeyInfo`, and wallet balance reads | Exit 0; Testnet signed requests succeeded. Unified account returned zero non-zero coins and no USDT. No order or transfer request was sent. |

## Current boundary

The Testnet OAuth flow is verified through callback, exchange, account listing,
explicit account selection, and read-only signed requests. The selected AI
sub-account currently reports no non-zero wallet coins, so no order test was
attempted. The implementation never auto-selects or creates an account.

No Testnet order, transfer, withdrawal, Mainnet request, or credential value
was sent to the repository, logs, reports, or remote Git history.

## Disposable Bundle upgrade receipt

After the OAuth checks, a separate disposable `DSH_HOME` was used with the
installed official DSH CLI at
`/Applications/DeepSeek Harness.app/Contents/Resources/runtime/cli/bin/dsh`.
A loopback-only temporary registry served two locally packed copies of the
Bundle, versions `1.4.5` and `1.4.6`. The active Harness profile was not read
or changed.

| Step | Exact operation | Result |
|---|---|---|
| Install | `dsh plugin --profile sdk add '@bybit-quant/dsh-plugin@1.4.5' --save-exact --registry http://127.0.0.1:4873` | Exit 0; profile dependency became `1.4.5` and the DSH bundle list included the plugin. |
| Upgrade | `dsh plugin --profile sdk update '@bybit-quant/dsh-plugin' --latest --registry http://127.0.0.1:4873` | Exit 0; profile dependency changed from `1.4.5` to `1.4.6`, and the installed package manifest reported `1.4.6`. |

This is a disposable official CLI install and upgrade receipt. The separate
Host service `plugin_manager.updateBundle` action was not directly callable
from this session, so the report does not claim that service-level activation
or rollback behavior was exercised. The earlier official CLI install,
uninstall, and reinstall receipt remains in
`sdd/reports/PLUGIN_MANAGER_LIFECYCLE_2026-11-17.md`.
