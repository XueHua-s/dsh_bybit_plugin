# Synthetic internal-paper service

This optional service runs a real Nautilus TradingNode/Sandbox in a spawned
process, with server-owned synthetic BTCUSDT finite depth and a linear-perpetual
margin account. It connects to no exchange and uses no exchange credentials.
Only LIMIT proposals are supported. Existing DSH paper/trading tools are not
wired to it. The normal `quant-engine` application remains two read-only routes.

Native/service/SDK scoped ACCEPTs and the actual built-SDK→CLI process receipt
are in `sdd/reviews/REVIEW_PAPER_{NATIVE,ADMISSION,SDK}_2026-11-17.md` and
`sdd/reports/PAPER_SDK_PROCESS_E2E_2026-11-17.md`. The E2E proves native fills,
later orders in the same process, durable identities, SDK-close independence,
cleanup and protected restart. It does not establish full product acceptance.

## Prerequisites and database boundary

Run from the repository root with the locked uv environment:

```sh
uv sync --project python --locked
uv run --project python --locked quant-engine-paper --help
```

The CLI requires `--database`, `--session` and `--capability-fd`; optional
`--host` defaults to numeric loopback `127.0.0.1`, `--port` to8766. Non-loopback
hosts are rejected. The database must already be migrated; startup never applies
migrations. Use a new explicitly temporary database for this fixture. For an
existing durable database, identify its environment, stop all consumers, and use
the protected backup/candidate upgrade flow; never substitute a production path
into this example. Packaged Alembic resources include revision0004.

## Capability descriptor protocol

A trusted launcher creates one ephemeral synthetic capability in memory, writes
its **raw bytes without a newline** to a private pipe, closes the write end, and
passes the read FD using `subprocess.Popen(pass_fds=...)`. The FD must be≥3 and
must be a FIFO. The loader consumes/closes it;32–128 printable non-space ASCII
bytes are accepted. The capability is scoped to that configured session and
supports observation/control. No capability fallback exists in argv, environment
or configuration files. `--capability-fd` contains only the numeric FD.

The client supplies `Authorization: Bearer <capability>` from its trusted memory
provider, never from a model argument. Never print/copy the actual value. The
SDK process E2E passed it to the Node client through private stdin and checked
captured outputs against the in-memory value before printing allowlisted results.

This bounded launcher recipe uses the verified CLI/FD protocol, a disposable DB,
no exchange credentials, and no order submission. It starts and stops the native
fixture once. An independent reviewer extracted this exact Python block, parsed it and ran
the no-submit start/stop recipe with the locked environment: exit0 and only
`synthetic_native_start_stop_ok` output. The E2E report retains that receipt;
external PID/listener cleanup observations come from its separate process probe.

```sh
uv run --project python --locked python - <<'PY'
import os
import secrets
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
from quant_data.migrations import upgrade_sqlite

with tempfile.TemporaryDirectory(prefix="quant-paper-runbook-") as directory:
    database = Path(directory) / "synthetic-paper.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA user_version=0")
    upgrade_sqlite(database)  # protected backup and candidate upgrade, temporary target only
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    capability = secrets.token_urlsafe(48).encode("ascii")
    read_fd, write_fd = os.pipe()
    os.write(write_fd, capability)
    os.close(write_fd)
    process = subprocess.Popen(
        [sys.executable, "-m", "quant_engine.paper_bootstrap",
         "--database", str(database), "--session", "runbook-paper",
         "--capability-fd", str(read_fd), "--host", "127.0.0.1", "--port", str(port)],
        pass_fds=(read_fd,), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    os.close(read_fd)
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=8,
                          follow_redirects=False,
                          headers={"Authorization": "Bearer " + capability.decode("ascii")}) as client:
            deadline = time.monotonic() + 12
            while True:
                try:
                    response = client.get("/api/v1/trading/status")
                    if response.status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                if process.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError("paper_startup_unavailable") from None
                time.sleep(0.05)
            session = {"environment": "internal_paper", "session_id": "runbook-paper"}
            started = client.post("/api/v1/trading/start", json=session)
            if started.status_code != 200 or not started.json().get("ready"):
                raise RuntimeError("paper_native_not_ready") from None
            stopped = client.post("/api/v1/trading/stop", json=session)
            if stopped.status_code != 200 or stopped.json().get("native_process_alive"):
                raise RuntimeError("paper_stop_not_confirmed") from None
            print("synthetic_native_start_stop_ok")
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
        try:
            process.wait(timeout=12)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)
            raise RuntimeError("paper_shutdown_failed") from None
PY
```

Forced kill is a failure outcome. An exit code of-15 alone does not prove clean
shutdown; require native PID disappearance and listener closure as in the E2E.
A client close does not stop the service/native process. Native parent-death
watchdog containment was separately probed, including a blocked native loop;
SIGKILL is not graceful shutdown or durable recovery.

## Authenticated routes and uncertain results

| Method/path | Purpose |
|---|---|
| `GET /api/v1/trading/status` | Session readiness/protection and native process state |
| `POST /api/v1/trading/start` | Start the explicitly configured synthetic session |
| `POST /api/v1/trading/stop` | Freeze admission and stop native owner; does not flatten positions |
| `POST /api/v1/trading/commands` | One synthetic LIMIT proposal with stable request identity |
| `GET /api/v1/trading/commands/{command_id}` | Durable scoped command state |
| `GET /api/v1/trading/commands/by-request/{request_id}` | Resolve a lost submit response using its original identity |

The generated SDK uses the separate `contracts/openapi/quant-paper.v1.json`.
No mutation is automatically retried. After ambiguous timeout/cancellation,
query the original request/status before further action; do not generate a new
request ID and resubmit. Same request/payload retains identity; changed payload
conflicts. Caller cannot provide balances, risk policy, truth snapshots or
leverage. Origin-bearing control requests are rejected.

Finite fixture depth and its timestamp expire; startup does not promise an
indefinitely fresh market. Wallet tracks collateral plus realized PnL minus
fees, not opening notional. Risk uses native marked equity and conservative
available equity; inconsistencies protect admission. Public status deliberately
does not expose wallet/equity as wire fields.

Existing/unclean/nonflat sessions restart protected, preserving durable facts
without replay/resubmission or a silently reset balance. A new isolated session
is a separate simulation, not recovery. Reconciliation, reliable event replay,
DSH control integration, native Testnet execution and removal of TS exchange
write bypasses remain mandatory future work. Mainnet is not tested or enabled.

## Scoped reproducible checks

```sh
uv run --project python --locked pytest python/apps/quant-engine/tests/test_paper_process.py -q
uv run --project python --locked quant-engine-openapi --paper --output contracts/openapi/quant-paper.v1.json --check
pnpm sdk:check
```

Loopback tests need permitted local socket binding. Record denied/missing or
failed checks as such; full root/Python/security/SBOM/release gates are tracked
in `sdd/reports/VERIFY_GATE_2026-11-17.md`.
