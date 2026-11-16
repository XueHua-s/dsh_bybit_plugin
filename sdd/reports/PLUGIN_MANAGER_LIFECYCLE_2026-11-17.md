# DSH Plugin Manager Lifecycle Evidence

Date: 2026-11-17
Scope: official Harness UI lifecycle for the local Bybit Bundle. No managed profile files were edited manually.

## Install and enable

| Action | Method | Observed result |
|---|---|---|
| Install local Bundle | Harness → Plugins → Add plugin → Install third-party plugin → local directory `/Users/litlesnow/Desktop/Project/幻方量化/bybit-quant/apps/dsh-plugin` | UI reported installed `@bybit-quant/dsh-plugin`, version `1.4.5`. |
| Enable | Harness Plugin Manager `立即启用` | Plugin row showed enabled and one running component. |
| Detail resource | Harness plugin detail view after install | English `docs/DETAIL.md` rendered; prior “invalid detail file” diagnostic was absent. |

## Uninstall and reinstall

| Action | Method | Observed result |
|---|---|---|
| Uninstall | Harness Plugin Manager `卸载 Bybit 量化` and confirm | Managed `@bybit-quant/dsh-plugin` component disappeared from the active plugin list. |
| Reinstall | Repeated the official local-directory install flow above | `@bybit-quant/dsh-plugin` v1.4.5 appeared as installed but disabled. |
| Re-enable | Harness Plugin Manager `立即启用` | Component returned to running state. |

Immediately before and after the lifecycle flow, user state files had unchanged sizes and modification times: `state.json` 15,417 bytes (2026-11-16 20:42:08), `oauth-token.json` 423 bytes (2026-11-17 01:42:21), `oauth-callback.json` 155 bytes (2026-11-17 01:40:59), `credentials.json` 163 bytes (2026-11-17 01:56:06), and `oauth-init.json` 178 bytes (2026-11-17 01:38:33). File contents were not read or printed.

## Limits and remaining acceptance work

- The Harness official UI manager was used; no standalone `plugin_manager` executable was available in `PATH`.
- This was the user's active Harness profile, not a disposable profile. State-file size and timestamps were unchanged, but there was no pre-operation content hash receipt, so byte-for-byte state preservation is not claimed.
- The installed version remained `1.4.5`; this proves install/uninstall/reinstall behavior but does **not** prove an upgrade path. Do not claim upgrade acceptance.
- A separate legacy `@local/bybit-quant` entry remained in the plugin list and displayed “this package does not declare a bundle and cannot be managed as a plugin.” It was not modified.
- Harness-managed profile `package.json` and `cordis.patch.yml` were never edited directly.
