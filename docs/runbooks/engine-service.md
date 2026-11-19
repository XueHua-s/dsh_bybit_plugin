# Read-only Testnet engine service

The independent Python process subscribes to public Bybit linear Testnet tickers. No credentials, account access, order endpoints or trading loop exist in this slice. An explicit bounded symbol set is required; no default market is silently selected.

```sh
uv sync --project python --locked
uv run --project python --locked quant-engine --symbols BTCUSDT ETHUSDT
# Equivalent Nx dispatch (serve must never be cached):
pnpm exec nx run quant-engine:serve -- --symbols BTCUSDT ETHUSDT
```

Default address: `127.0.0.1:8765`. `--host` accepts loopback IPs only, including `::1`. Remote binding and authentication are not implemented. Do not expose this local service through an unauthenticated proxy. `--port` sets the port; `--stale-after` sets the finite positive freshness threshold in seconds (default 30).

```sh
curl -i http://127.0.0.1:8765/api/v1/health
curl -i http://127.0.0.1:8765/api/v1/market/BTCUSDT
```

Health returns HTTP 200 only when the supervised consumer/adapter is running, the socket is connected and every configured symbol has fresh receive time and exchange time. Future exchange timestamps beyond 5 seconds also fail readiness. Until then HTTP 503 carries `degraded` or `unavailable`, actual process RSS/CPU time, ingress queue/counters/reconnect state, per-symbol receive freshness and exchange lag. These facts do not prove execution or account readiness. Order latency, rejection and reconciliation remain unknown/null. Supervisor restart count and terminal error survive a failed generation; no exception text from external inputs is reflected.

Market requests return HTTP 503 until a fresh connected event exists, and HTTP 404 for a symbol outside the configured set. Bybit delta frames can omit prices; `partial` identifies an incomplete update. Returned values are the latest validated update, not a reconstructed full orderbook/snapshot. An omitted price stays null rather than inventing data or mixing stale fields.

SIGINT/SIGTERM invokes uvicorn's lifespan shutdown, which closes the consumer and adapter, closes the socket and waits for tasks before stopping runtime. The supervisor restarts the whole composed worker at most three times if consumption or ingestion unexpectedly terminates. Network interruptions use adapter reconnect backoff; degraded readiness remains explicit. External process restart (systemd/launchd/container), persistence, private subscriptions, heartbeat hardening and reconciliation are future work.

## Offline contracts and tests

OpenAPI comes only from FastAPI/Pydantic. Both export commands construct an app without entering lifespan; neither opens exchange connections.

```sh
uv run --project python --locked quant-engine-openapi --output contracts/openapi/quant-engine.v1.json
uv run --project python --locked quant-engine-openapi --output contracts/openapi/quant-engine.v1.json --check
uv run --project python --locked pytest python/apps/quant-engine/tests/test_service.py
```

Tests inject an in-memory socket into the real adapter and run the actual queue consumer, supervisor and FastAPI lifespan. They send no orders or exchange requests. The broader original architecture's authenticated control API, complete market-data recovery and OpenTelemetry export are not provided by these two read-only routes.
