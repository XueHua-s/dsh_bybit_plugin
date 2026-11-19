# DESIGN: independent read-only engine service

Date: 2026-11-17. Supplement to the complete BYBIT_AI_QUANT Brainstorm, Define and Design and architecture brief sections 3, 5, 11, 16, 20. Parent task explicitly delegates this implementation; no new mode/permission prompt is required. This slice has no runtime LLM prompts.

## Scope and drift

The existing supervisor/adapter are an in-process foundation, not an independently runnable API. Implement a real FastAPI lifecycle and CLI with required explicit symbols, fixed public linear Testnet transport, read-only endpoints and loopback-only binding. Future account/orders/research/strategy endpoints, heartbeat/orderbook/reconciliation, OTel export and process-manager recovery remain unimplemented. Python services are expressly required by the architecture; the repository TypeScript rule applies to plugin/tooling source, not this Python engine.

## Decisions and boundaries

- MarketWorker hides the adapter plus queue consumer and stores at most one latest ticker per configured symbol. Its health reports failure when the consumer stops; supervisor applies its finite restart budget to the whole composed worker.
- EngineService composes worker generation with EngineSupervisor(factory=...). HTTP never owns or starts a separate trading loop. Lifespan alone starts/stops it.
- Pydantic response models are the only API schema source. Offline OpenAPI export constructs an app without entering lifespan or connecting a socket. SDK generation follows in a separate slice.
- Monitoring samples actual process RSS/CPU (psutil), ingress queue/reconnect facts and per-symbol receive freshness. Readiness requires running supervisor, connected healthy worker and fresh data for every configured symbol. Missing/stale data or restart/failure returns 503. Order latency/rejections/reconciliation stay explicitly unknown/null.
- Default 127.0.0.1; reject every non-loopback bind, since authentication is not implemented. No keys, private exchange APIs, order routes or mainnet switch exist.
- Software-design score target 10/10: the eight diagnostic rows are addressed by small documented interfaces, coherent modules hiding wire/lifecycle/config/measurement decisions, dependency injection and this explicit rationale; independent review must validate the score.

## File manifest

| Path | Action | Acceptance |
|---|---|---|
| python/apps/quant-engine/src/quant_engine/service.py | create | composed worker drains queue, bounded latest state, consumer failure observable, complete cleanup |
| python/apps/quant-engine/src/quant_engine/api.py | create | Pydantic /api/v1/health and /market/{symbol}; unavailable 503; lifecycle owner |
| python/apps/quant-engine/src/quant_engine/monitoring.py | create | real process metrics; health freshness; unknown execution facts |
| python/apps/quant-engine/src/quant_engine/bootstrap.py | create | validated required symbols and loopback CLI; uvicorn and offline schema export |
| python/apps/quant-engine/tests/test_service.py | create | real adapter + injected socket + consumer + lifespan; readiness, failure/restart/shutdown |
| python/apps/quant-engine/pyproject.toml | modify | FastAPI/Pydantic/uvicorn/psutil and scripts |
| python/pyproject.toml, python/uv.lock | modify | httpx dev dependency; one uv workspace |
| python/apps/quant-engine/project.json | modify | uncached serve, deterministic OpenAPI export/check and full-project Python typing (source plus tests) |
| .github/workflows/ci.yml | modify | blocking verify job executes offline OpenAPI consistency check |
| contracts/openapi/quant-engine.v1.json | create | deterministic schema exported offline |
| docs/runbooks/engine-service.md | create | reproducible run/check commands, limitations |
| sdd/reports/BUILD_REPORT_ENGINE_SERVICE.md | create | actual commands, exits and outstanding work |

## Acceptance / verification

1. Mock socket sends a real Bybit ticker into adapter, consumer drains it and HTTP returns it through FastAPI lifespan; no exchange network calls.
2. Missing symbol is 404, not-yet-seen or stale configured ticker is 503; healthy fresh feed yields ready health. CPU/RSS are measured and execution metrics unknown.
3. Consumer failure makes whole worker failed; finite supervisor restart budget eventually produces failed/unready state; shutdown closes socket/tasks and runtime.
4. Offline export and check match the checked-in schema; invalid remote bind and absent symbols are rejected.
5. `uv run --project python --locked ruff check python/apps/quant-engine`, Ruff format check, Pyright and pytest pass; parent executes full `pnpm run verify` and independent review.

## CI integration supplement

Parent authorized this necessary release integration: the blocking verify job runs the existing offline OpenAPI check. Nx engine typecheck covers source and tests, matching the full verification boundary; source-only typing previously missed test errors. Schema generation/check is provided; generated SDK remains a separate unimplemented gate.
