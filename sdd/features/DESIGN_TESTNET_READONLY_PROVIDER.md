# Design — Secure read-only Bybit Testnet provider

Date: 2026-11-19
Status: **implementation slice; live account activation remains a separate gate**

## Problem and boundary

The existing preflight contract is fixture-only. This slice supplies the missing
host-owned signed GET transport while preserving the same fail-closed projection
boundary. It is a read provider, not an execution client. It cannot submit,
cancel, borrow, transfer, change account settings, follow redirects or select an
endpoint from model input.

## Manifest

| File | Responsibility |
|---|---|
| `python/packages/quant-execution/src/quant_execution/bybit_http_provider.py` | Secret resolver protocol, strict HMAC V5 signing, fixed-host no-redirect transport, named read methods and bounded pagination. |
| `python/packages/quant-execution/tests/test_bybit_http_provider.py` | Fake transport/resolver tests for signatures, GET-only paths, response normalization, pagination and secret redaction. |
| `python/packages/quant-execution/src/quant_execution/bybit_preflight.py` | Existing orchestration; unchanged authority and submission denial. |
| `sdd/reports/BUILD_REPORT_TESTNET_READONLY_PROVIDER_2026-11-19.md` | Command ledger and explicit live/provider limits. |

## Data flow

`Trusted profile → host resolver(profile_ref) → in-memory credential → signer →
fixed HTTPS GET transport → bounded response mapping → strict projection →
sanitized preflight evidence`.

The resolver returns a short-lived credential object only to the provider. The
credential is never serializable through profile DTOs, API schemas, logs or error
messages. The transport accepts only `get(path, query, timeout)` and rejects every
host except `api-testnet.bybit.com`. A custom redirect handler fails closed.

The provider exposes four named methods matching `ReadOnlyTestnetProvider`:
`get_api_key_evidence`, `get_wallet_evidence`, `get_linear_instrument_evidence`
and `get_initial_report_coverage`. The last method reads realtime orders,
positions and executions with bounded cursor pagination and returns only coverage
metadata. Unknown response fields are ignored only at the transport-to-projection
mapping boundary; required fields, permissions and pagination failures deny.

## Security invariants

- The only accepted environment is Testnet Linear and the only accepted base URL
  is `https://api-testnet.bybit.com`.
- Every request is HMAC-SHA256 V5 signed with a generated timestamp and bounded
  receive window. Query encoding is deterministic and secrets never appear in the
  signed URL or exceptions.
- Response bodies are capped, JSON objects are required, Bybit nonzero `retCode`
  is unavailable, and nonempty cursors are followed only up to a fixed page cap.
- No method accepts an HTTP verb, arbitrary path, raw URL, credential, or model
  policy. There is no POST transport method in the production adapter.
- Provider failures become the existing sanitized `provider_read_failed` result;
  no raw response or exception text crosses the preflight boundary.

## Acceptance

```text
uv run --project python --locked pytest python/packages/quant-execution/tests/test_bybit_http_provider.py python/packages/quant-execution/tests/test_bybit_preflight.py
uv run --project python --locked ruff check python/packages/quant-execution
uv run --project python --locked pyright python/packages/quant-execution
```

Tests use a fake transport and never resolve a real credential or contact Bybit.
This design does not claim a live Testnet preflight, account identity, balance,
Nautilus reconciliation or order acceptance; those require a separate authorized
operator action after all offline gates pass.
