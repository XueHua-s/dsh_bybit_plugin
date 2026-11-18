# UX review: Bybit AI Quant panel

Date: 2026-11-19
Scope: DSH plugin detail, sidebar panel and configuration language
Verdict: **Readable for the implemented slice; full unattended trading UX is not ready**

## Evidence

- The installed DSH panel was opened through the signed-in Harness UI.
- The panel visibly showed `Testnet`, `Live trading off`, account-key status,
  public market data, paper ledger, backtest and AI decision cards.
- The rebuilt source and local React SSR include an explicit readiness card
  with: `Conversation-triggered only`, `Not running`, `Direct TS REST path
  (quant executor not connected)`, and unknown account readiness. The card also
  states that healthy market data does not prove account, reconciliation or
  execution readiness, and that the Mainnet per-order approval-card flow is not
  implemented.
- The currently installed Harness panel still runs the earlier bundle: it
  shows Testnet, live trading off, API-key status, the engine card, the native
  paper card and the AI decision card, but not the new readiness card. The
  active profile was left unchanged.
- Plugin detail and locale descriptions now say the AI workflow is
  conversation-triggered and has no unattended background loop.

## Findings

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| UX-01 | P1 | The earlier detail text could be read as a persistent “AI loop”. | Fixed by renaming it to “Conversation-triggered AI workflow” and adding an explicit runtime boundary. |
| UX-02 | P1 | A healthy ticker could imply execution readiness. | Fixed by adding the readiness card and unknown account/reconciliation state. |
| UX-03 | P2 | Mainnet OAuth had no discoverable documented command. | Fixed with `--env=live` examples and isolated credential-path documentation. |
| UX-04 | P1 | Installed active Harness profile did not automatically reload this worktree’s new bundle. | Remains operationally pending; official manager lifecycle is documented separately and active profile was not mutated. |
| UX-05 | P1 | Mainnet requires a user-confirmed order summary, but the plugin has no such card/approval flow. | Explicitly disclosed in the readiness card; remains a release blocker for Mainnet writes and any claim of unattended Mainnet trading. |

## Acceptance boundary

The interface is honest about the current capability and safer for unattended
use because it exposes the absence of an unattended loop. It does **not** claim
that DSH can autonomously wake an AI, run a strategy continuously, reconcile
orders after restart, or make the Python/Nautilus executor the sole exchange
authority. Those product requirements remain open.

The Mainnet configuration now exposes environment-scoped credential names
(`BYBIT_MAINNET_API_KEY`/`BYBIT_MAINNET_API_SECRET`) instead of inheriting the
Testnet names. The Host rejects an explicit Mainnet configuration that reuses
the common Testnet variable names.
