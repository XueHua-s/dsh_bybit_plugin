# DSH paper design — static evidence

Date:2026-11-17. Owner:paper_dsh_design. Design-only; no source/runtime/configuration/credential/Git mutation. New artifacts: this report and `sdd/features/DESIGN_DSH_PAPER.md`.

## Inspected inputs

Read `AGENTS.md`; project-local `sdd-design` (including canonical template/protocol/LLM guidance) and `software-design-philosophy`; full project Brainstorm/Define, current handoff, all six `DESIGN_PAPER_*` documents, `DESIGN_DSH_ENGINE` and execution-cutover design. Inspected Host composition/tools/bridge/Client, generated SDK public paper API/transport, Python paper CLI/config/API/models, runbook, Nx/package manifests and CI. Existing code acceptance belongs to its cited receipts, not to this design inspection.

## Actual commands and outcomes

| Actual inspection command | Exit | Finding |
|---|---:|---|
| `rg -n "bybit-quant\|DSH\|paper\|execution cutover" /Users/litlesnow/.codex/memories/MEMORY.md` using ordinary regex alternation in the actual call |0 | Only unrelated Godot paper matches; no relevant memory used |
| `cat AGENTS.md` and the two project skill files; subsequent template/reference reads |0 | Project boundaries and canonical design structure |
| `rg --files sdd/features apps/dsh-plugin packages/ts` |0 | Actual current file manifest candidates |
| `cat sdd/features/BRAINSTORM_BYBIT_AI_QUANT.md`; `cat sdd/features/DEFINE_BYBIT_AI_QUANT.md` |0 | Full requirements retained; product LLM Prompts=true |
| `cat` current handoff, paper/DSH designs and selected execution-cutover sections |0 | Scoped native/service/SDK receipts; future exchange cutover remains open |
| `cat` Host runtime/panel/engine/config, Tools, Client, SDK index/paper/transport |0 | Existing readonly DSH and private SDK seam; no Host paper provider |
| `cat` paper_bootstrap/paper_config/paper_api/paper_api_models and runbook |0 | Existing FIFO-only capability bootstrap; strict internal_paper schema |
| `cat .github/workflows/ci.yml`; `cat` plugin/root package and Nx manifests |0 | Locked Python sync precedes root verification; no process E2E target yet |
| `ls '/Applications/DeepSeek Harness.app/Contents/Resources'` |0 | Packaged app.asar and unpacked/runtime resources |
| Read-only Node ASAR header traversal/content reads described below |0 | Actual installed source contracts/hashes below |
| `rg -n 'def run\(|def serve\(|async def startup|sockets:|create_server|bind_socket' python/.venv/lib/python3.12/site-packages/uvicorn/{server.py,config.py,main.py}` |0 | Server supplied-socket interface exists |
| `sed -n '70,100p' python/.venv/lib/python3.12/site-packages/uvicorn/server.py`; `sed -n '145,158p' .../server.py` |0 | `run(sockets=...)` forwards to serve and loop.create_server(sock=...) |
| `wc -l sdd/features/DESIGN_DSH_PAPER.md`; heading/manifest `rg` inspection |0 | Canonical sections and32 manifest rows inspected |
| `python3` heredoc static document validator |0 | Required section order, IDs1–32, backward-only dependency DAG, no placeholders, exact footer and both files' trailing whitespace; printed `design_sections_manifest_dag_footer_whitespace_ok` and `design_files=2 manifest_files=32` |

Exploratory failures were not gates: an early `sdd/reports/UPSTREAM*` shell glob matched nothing and its batch exited1; a speculative docs/reference path was absent, and broad ASAR inventory output was truncated before a narrower successful query. No dependency/test/install/network/exchange/database command was run to remedy those read-only search misses.

## Installed DSH source receipts

Container: `/Applications/DeepSeek Harness.app/Contents/Resources/app.asar`. Read packed source bytes directly; did not execute app code or read any user profile/credential document. `dsh/package.json` reports `@deepseek-ai/dsh-desktop-runtime` version`0.2.2-rc.3`; credentials-local/client-connection/host-webserver/web-fetch-http packages report the same version.

Paths below are inside the ASAR under `dsh/node_modules/@deepseek-ai/`:

| Source | Relevant lines | Actual fact | SHA256 of source bytes |
|---|---|---|---|
| `dsh-client-connection/src/rpc.ts` |147–175 | GET/HEAD/POST; buffered/streaming; exact routes owner-only after trust/auth; register returns async disposer |`74ba5632fea441a4c76de677ddeb840de51a775b42514c0908a3ef207339d94b` |
| `dsh-client-connection/src/rpc-host.ts` |208–250 | Exact route checks `peer.principal.kind !== 'owner'` and returns403 before route.fetch; effect removes route |`55cd4aaf34103aba890146a8168ec88ba45c0373e55367a74d4f547ed579bcf7` |
| `dsh-client-connection/src/index.ts` |146–160 | `connection.admit(req)` precedes shared Fetch bridge |`33a14e80298e0a0bc7bafef515d853d13584cd2433844b3dc2a89d4980d315e1` |
| `dsh-client-connection/src/api-request-trust.ts` |1–12 | Host/Origin fence defends browser rebinding/cross-site paths; fence alone is not identity |`879a4f497ad41355771303a5956851da04661be24b08435fe7bf13d42e1e3b9b` |
| `dsh-client-connection/src/browser-auth.ts` |356–379 | Cookie authentication and distinct API-operator validation |`f1ebdb9fa8706414852420393d9f34b2d604a128928a2f5852d4832ce38b45f7` |
| `dsh-credentials/src/index.ts` |201–256 | set/unset and readRecord/describeRecord/listRecords/modifyRecord/deleteRecord exist |`b089b7a57eb7a4731379e2696c3c43b99030fc7f54271b769fbe5f63496fde01` |
| `dsh-credentials-local/src/index.ts` |638–645,670–681,692–723 | resolve has env/dotenv fallbacks; records have no ambient layer; atomic grant writes use0600 |`834d5a326d00b878390a95a5b9f2a40ed2dd43e9358b00d63f026b6ab103f254` |

Exact read-only ASAR extraction pattern used in the successful source/hash commands (example target; replace only the public package source path):

```sh
node - <<'JS'
const fs = require('node:fs');
const crypto = require('node:crypto');
const file = fs.openSync('/Applications/DeepSeek Harness.app/Contents/Resources/app.asar', 'r');
const prefix = Buffer.alloc(16);
fs.readSync(file, prefix, 0, 16, 0);
const headerSize = prefix.readUInt32LE(4);
const header = Buffer.alloc(prefix.readUInt32LE(12));
fs.readSync(file, header, 0, header.length, 16);
let entry = JSON.parse(header.toString());
const path = 'dsh/node_modules/@deepseek-ai/dsh-client-connection/src/rpc.ts';
for (const segment of path.split('/')) entry = entry.files[segment];
const source = Buffer.alloc(Number(entry.size));
fs.readSync(file, source, 0, source.length, 8 + headerSize + Number(entry.offset));
fs.closeSync(file);
console.log(path, crypto.createHash('sha256').update(source).digest('hex'));
console.log(source.toString().split('\n').slice(146, 176).join('\n'));
JS
```

No fresh installed DSH auth/UI request, service start, command, socket bind, native runtime, scan, test, migration, install, commit or push was performed. This document establishes API evidence and a Build contract only. Parent-reported current hosted shutdown failure must be repaired/independently verified before new process acceptance. The full objective remains IN PROGRESS/PARTIAL.

## Independent pre-build review revisions

Read the full formal receipt `sdd/reviews/REVIEW_DSH_PAPER_DESIGN_2026-11-17.md` and the skill's `references/advisor-review.md`, exit0. Initial verdict HOLD required R1 mutation503 ambiguity and R2 complete-stream framing; R3 clarified lifecycle controls. Design Advisor Ledger marks all three APPLIED; final reviewer recheck is pending, not presumed accepted.

Actual additional read-only command batch, exit0: `sed -n '205,255p' python/apps/quant-engine/src/quant_engine/paper_admission.py`; `sed -n '60,78p' .../paper_api.py`; `sed -n '32,55p' packages/ts/quant-api-client/src/paper.ts`; `rg -n '503|uncertain|timeout|unavailable' packages/ts/quant-api-client/test/paper.test.ts`. This directly verified the real source chain: admission persists decision, claims dispatch, calls native submit, then drain/ledger lookup may fail and raise PaperUnavailable; API maps it to503; existing SDK uncertain() omits unavailable. The new design assigns the fix/tests to existing SDK owner rather than duplicating policy in DSH. No fault was executed in this design task.

Also inspected `sed -n '80,155p' .../paper_admission.py`, exit0: `_start` permits idle only, while idle `_status` is not execution-ready. The revised UI table explicitly permits first Start at idle/ready:false and Stop for running/protected native-alive states; stopped/protected cannot Start.

The revised local protocol specifies request half-close and complete EOF on both directions, under the unchanged500ms/1024-byte budgets, plus split/delayed-trailing/no-EOF tests. Manifest adds existing SDK `src/paper.ts` and `test/paper.test.ts` as stable IDs33–34, with explicit owner/dependencies. Stable numbering permits forward references; the revised document validation checks the actual graph for cycles rather than requiring numerical order.

Revised `python3` static validator exit0 checked canonical section order, exact34 manifest IDs, referenced-ID existence and actual dependency graph acyclicity, R1/R2/R3 contract anchors, no placeholders, footer and whitespace. Output: `revised_design_sections_manifest34_dag_R1_R2_R3_footer_whitespace_ok`; revised design SHA256 `9522a18cd5f21acae640bb781c622dacc0b1ff21876d904e3635769facfba923`. No implementation tests were run.
