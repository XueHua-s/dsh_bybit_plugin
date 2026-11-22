# UX review: Bybit AI Quant panel

Date: 2026-11-19
Scope: DSH plugin detail, sidebar panel and configuration language
Verdict: **Readable for the implemented slice; full unattended trading UX is not ready**

## Evidence

- The installed DSH panel was opened through the signed-in Harness UI.
- The panel visibly showed `Testnet`, `Live trading off`, account-key status,
  public market data, paper ledger, backtest and AI decision cards.
- The rebuilt source and local React SSR include an explicit readiness card
  with: `Conversation-triggered only`, `Not running`, unavailable exchange
  writes, and unchecked account readiness. The card states that healthy market
  data, OAuth or API keys do not prove account, reconciliation or execution
  readiness. A redundant Mainnet-approval row was removed because writes are
  unavailable in every environment; per-order Mainnet authorization remains a
  requirement before a future Mainnet writer can be enabled.
- At the time of the initial observation, the Harness panel still rendered the
  earlier bundle without the new readiness card. The post-reload state is
  recorded separately below.
- Plugin detail and locale descriptions now say the AI workflow is
  conversation-triggered and has no unattended background loop.

## Findings

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| UX-01 | P1 | The earlier detail text could be read as a persistent “AI loop”. | Fixed by renaming it to “Conversation-triggered AI workflow” and adding an explicit runtime boundary. |
| UX-02 | P1 | A healthy ticker could imply execution readiness. | Fixed by adding the readiness card and unknown account/reconciliation state. |
| UX-03 | P2 | Mainnet OAuth had no discoverable documented command. | Fixed with `--env=live` examples and isolated credential-path documentation. |
| UX-04 | P1 | Installed active Harness profile did not automatically reload this worktree’s new bundle. | The current session now renders the updated panel; official manager install/upgrade/rollback and user-state preservation remain unverified. |
| UX-05 | P1 | Mainnet requires a user-confirmed order summary, but the plugin has no such card/approval flow. | Kept as a future release blocker; removed the redundant readiness row so it cannot look like a setup step that enables the currently unavailable writer. |

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

## Pre-reload follow-up receipt (2026-11-20)

Read-only inspection of the running DeepSeek Harness UI confirmed the active
plugin still reports version `1.4.5` and renders pre-current copy. The dashboard
labels the symbol selector `交易对`, says automation is `仅对话触发`, and omits
the current AI candidate-pool and cycle-receipt status. The separate native
paper card labels itself synthetic/no-exchange; its Start/Stop controls are
disabled. The visible panel has no enabled exchange-order or AI-loop control.

The current workspace source labels these controls as chart-only, removes the
native-paper browser controls, and reports dynamic candidates and background
simulation status. Plugin SSR/render and integration tests pass, but the active
Harness UI has not loaded those current changes. No active-profile install,
uninstall, restart, or profile-file edit was performed. Refreshing the active
Bundle remains pending through an official Plugin Manager update/reload with a
separate preservation receipt for credentials, config, journal, and audit data.

## Post-reload correction receipt (2026-11-20)

A new read-only Cua Driver inspection of the active DeepSeek Harness window now
shows the current boundary copy from the workspace: `行情查看` explicitly says
chart filters do not choose the AI symbol or parameters; the `运行边界` card
shows `仅对话触发`, a default-closed scheduler, an unavailable exchange writer,
unknown account readiness, the dynamic candidate-pool status, and the latest
cycle receipt. The native internal-paper card exposes status inspection only,
and no exchange order or unattended-loop control is enabled. The previous
statement that the active panel still rendered pre-current copy is retained as
historical evidence of the earlier snapshot and is superseded for the current
UI by this receipt.

This check used the accessibility tree and a window screenshot only. It did not
click controls, read credentials/tokens, alter the managed profile, or send an
order. It verifies presentation and boundary language, not Testnet execution,
reconciliation, restart recovery, or full unattended trading acceptance. At
the captured 1280×820 window size, a companion overlay covered part of the
readiness card's candidate-pool/status text. The overlay's ownership was not
determined; this is a visual readability issue to recheck at other window
sizes and with the companion hidden.
