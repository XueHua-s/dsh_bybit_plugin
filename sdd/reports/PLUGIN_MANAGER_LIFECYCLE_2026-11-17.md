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

## Follow-up disposable-profile upgrade attempt (2026-11-17)

Status: **BLOCKED — no safe disposable profile or standalone manager was available.** No install, upgrade, uninstall, restore, profile creation, or profile mutation was performed in this follow-up.

### Read-only availability checks

| Check | Exact command / observation | Result |
|---|---|---|
| Standalone manager executable | `command -v plugin_manager || true; command -v dsh || true` | Neither command printed a path. The shell `PATH` was also printed and contained no discovered manager command. |
| Existing profile candidates | `find "$HOME/Library" -maxdepth 5 -iname '*profile*' -path '*DeepSeek*' -print 2>/dev/null \| head -50` | No candidate paths were returned. This bounded search does not prove that no profile exists elsewhere. |
| Official Harness UI | Read-only inspection of running app `com.deepseek.dsh`, Plugins detail page | UI showed Bybit quant `@bybit-quant/dsh-plugin` v1.4.5 enabled, one component running, and source path `/Users/litlesnow/Desktop/Project/幻方量化/bybit-quant/apps/dsh-plugin`. This is the active Harness profile, not an identified disposable profile. |

Repository search: `rg -n "plugin_manager|install_bundle" scripts package.json .agents --glob '!**/node_modules/**'` returned `rg: scripts: No such file or directory (os error 2)`; there is no repository `scripts/` directory at this checkout. Separate search results found no standalone manager integration entry point. The canonical method noted in `DESIGN_BYBIT_AI_QUANT.md` is the installed official manager's `install_bundle`/upgrade/uninstall flow, but no callable API/CLI was discovered here.

### Decision and remaining acceptance

The UI manager is available, but the only profile positively identified is the user's active profile. The earlier receipt also documents sensitive user state in the active profile and no disposable-profile evidence. Therefore the authorized safety boundary prohibits testing there. No local bundle versions were installed and no upgrade/uninstall/restore receipt was fabricated. Acceptance remains pending until an isolated disposable Harness profile and an official manager flow capable of an actual version upgrade are available. At that point capture pre/post state hashes without reading or printing credential contents, then run the controlled two-version lifecycle and record every real command/action and exit/result.

## Subsequent disposable `DSH_HOME` lifecycle attempt (2026-11-17)

Status: **PARTIAL / upgrade blocked.** This run used the installed official DSH CLI and an isolated `DSH_HOME`; the active Harness profile and its managed files were not opened or changed. No Bybit credentials, Mainnet endpoints, or real orders were used.

### Read-only discovery of the official flow

- Installed binary: `/Applications/DeepSeek Harness.app/Contents/Resources/runtime/cli/bin/dsh`, `dsh --version` exited `0` and printed `0.2.2-rc.3`.
- `dsh --profile sdk --dump-config` exited `0`. The shipped SDK template rendered `tool-plugin-manager` with `disabled: false` and the `@deepseek-ai/dsh-plugin-manager` Host row. This confirms the official manager/tool is present in the installed runtime without editing a profile file.
- `dsh plugin --profile <name> --help` exited `0` and documented official profile package operations (`add`, `remove`, `why`, etc.). The installed manager README/source (read-only inspection of the app bundle) identifies the Host operations as `installBundle`, `updateBundle`, and `removeBundle`; the CLI and service share the package-operation implementation. There is no standalone `plugin_manager` executable in `PATH`.

### Disposable profile commands and receipts

The run used `DSH_HOME=/tmp/bybit-dsh-lifecycle-proof.LTKXRe` and profile `sdk` (a temporary directory created for this run). Exact commands and observed exit codes:

| Step | Exact command | Exit | Evidence |
|---|---|---:|---|
| Template/config discovery | `DSH_BIN=/Applications/DeepSeek Harness.app/Contents/Resources/runtime/cli/bin/dsh; "$DSH_BIN" --profile sdk --dump-config` | 0 | Official SDK template contains `tool-plugin-manager` enabled. |
| Install local bundle | `"$DSH_BIN" plugin --profile sdk add "/Users/litlesnow/Desktop/Project/幻方量化/bybit-quant/apps/dsh-plugin"` | 0 | pnpm v11.28.5 added `@bybit-quant/dsh-plugin` 1.4.5 as a `link:` dependency; profile bundle list appended the package. |
| Uninstall local bundle | `"$DSH_BIN" plugin --profile sdk remove '@bybit-quant/dsh-plugin'` | 0 | pnpm removed the dependency; profile bundle list returned to `@deepseek-ai/dsh-base`, `@deepseek-ai/dsh-sdk-app`. |
| Reinstall local bundle | `"$DSH_BIN" plugin --profile sdk add "/Users/litlesnow/Desktop/Project/幻方量化/bybit-quant/apps/dsh-plugin"` | 0 | pnpm re-added `@bybit-quant/dsh-plugin` 1.4.5 and the bundle list appended it again. |
| Registry/version probe for upgrade | `"$DSH_BIN" plugin --profile sdk view '@bybit-quant/dsh-plugin' versions --json` | 1 | Official pnpm returned `ERR_PNPM_FETCH_404` for `https://registry.npmjs.org/@bybit-quant%2Fdsh-plugin`; DSH recorded the diagnostic at `/tmp/bybit-dsh-lifecycle-proof.LTKXRe/profiles/sdk/.plugin-manager/logs/operation-ucRWLl/pnpm.log`. |

The disposable profile's post-install manifest contained only the safe fields `name: dsh-profile-sdk`, the local `link:/Users/litlesnow/Desktop/Project/幻方量化/bybit-quant/apps/dsh-plugin` dependency, and the ordered bundle list. No credential file was read. The temporary profile hashes after the first install were `package.json=e31514e486193db1288719ba756b6f634d73f05838c237d7679dd8975e71ad86`, `pnpm-lock.yaml=926842014ad231aa0c6fcd9dece0a8951eb3bcc2dddd93e425be414aa6273dc3`, `cordis.patch.yml=ef189a8c27db6d63930aa3046a3040482e952eafcb7487c644d508e8d461f027`, and `pnpm-workspace.yaml=ae7c5b68e2f157528e62885804e69e88583897b775e03c86fcbe52feaf498aba`. After uninstall/reinstall, the expected dependency manifest changed to `package.json=a2166e8dbdd4e0283c6ff1e08985ea980876d6fd3ec390024b927458ad2dea22`; lockfile, patch, and workspace hashes remained identical. These are disposable-profile receipts, not claims about the active Harness profile.

### Acceptance boundary

This proves the official CLI can install, remove, and reinstall the local Bundle in a disposable profile. It does **not** prove the Host service's `install_bundle` tool action or a version-to-version `updateBundle` run. Upgrade remains **blocked** because the public registry has no `@bybit-quant/dsh-plugin` package (`ERR_PNPM_FETCH_404`), and the local path is not an update-eligible registry dependency. Do not upgrade the overall acceptance verdict until an official second version (or a reachable registry source) and a disposable-profile `updateBundle` receipt are available. No managed Harness `package.json` or `cordis.patch.yml` was manually edited.

## Follow-up disposable CLI upgrade receipt

The earlier public-registry lookup was blocked because this private package is
not published there. A later isolated run served locally packed copies of
versions `1.4.5` and `1.4.6` from a loopback-only temporary registry. The
official DSH CLI completed both package operations in the disposable profile,
without reading or changing the active Harness profile:

| Step | Exact command | Exit | Observed state |
|---|---|---:|---|
| Install | `dsh plugin --profile sdk add '@bybit-quant/dsh-plugin@1.4.5' --save-exact --registry http://127.0.0.1:4873` | 0 | Profile dependency and selected bundle were `1.4.5`. |
| Upgrade | `dsh plugin --profile sdk update '@bybit-quant/dsh-plugin' --latest --registry http://127.0.0.1:4873` | 0 | Profile dependency and installed package manifest changed to `1.4.6`. |

This upgrades the disposable profile through the installed official CLI's
package-manager path. The Host service `plugin_manager.updateBundle` method
was not directly exposed as a callable tool in this session, so activation,
rollback, and state-preservation behavior for that service method remain
unverified. The prior “upgrade blocked” statement applies to the
public-registry attempt only.
