# Design — Read-only Bybit Testnet preflight

Date: 2026-11-19
Status: **offline profile/projection/orchestration implemented against fixtures; live provider remains unimplemented**

## Problem and boundary

The native Testnet cutover needs a server-owned, fail-closed read boundary before a
session can be considered eligible for reconciliation. This slice must not create a
Nautilus execution client, discover credentials from the environment, or expose an
order mutation path. It proves profile binding, allowlisted evidence projection and
sanitized failure semantics with injected fixtures only.

## File manifest

| File | Responsibility |
|---|---|
| `python/apps/quant-engine/src/quant_engine/bybit_profiles.py` | Resolve one opaque reference through a trusted-store protocol to explicit Testnet/Linear identity. |
| `python/packages/quant-execution/src/quant_execution/bybit_projection.py` | Parse strict identity, wallet, instrument and report evidence; reject unknown permission/data fields. |
| `python/packages/quant-execution/src/quant_execution/bybit_preflight.py` | Call four named read-only provider methods with a fixed timeout and return sanitized status. |
| `python/apps/quant-engine/tests/test_bybit_profiles.py` | Profile validation and no ambient fallback tests. |
| `python/packages/quant-execution/tests/test_bybit_projection.py` | Strict projection, permission, freshness and zero-funds fixtures. |
| `python/packages/quant-execution/tests/test_bybit_preflight.py` | Named GET-operation fixture, failure and eligibility checks. |

## Data flow and invariants

`profile_ref → trusted profile store → fixed Testnet/Linear preflight → allowlisted
provider reads → strict projections → sanitized evidence`.

The model/API supplies only an opaque profile reference. A profile contains an
expected UID and optional parent UID, but never a key, secret, token or policy. Its
endpoint is fixed to `https://api-testnet.bybit.com`. The preflight receives an
injected protocol with four named GET-only operations and no raw HTTP client; tests
assert the requested endpoint, fixed timeout and fixture operation names. The
production secure provider, signed HTTP transport, redirect denial and raw Bybit
payload normalization are **not implemented by this slice**. No result is called
`ready_to_trade`; `order_submission_allowed` is always false and success means only
`eligible_for_reconciliation`.

Identity must match the trusted profile, be a non-master account, use Unified account
mode, and include explicit read-only state, expiry, a single-IP binding and a
normalized permission set exactly equal to `read` plus `linear_trade`. Unknown,
withdrawal or transfer permissions deny. Wallet and instrument evidence must be
complete, finite, non-negative and fresh. Zero balance remains visible and cannot
authorize order admission. Reports must explicitly identify the requested symbol
and state complete order/position/execution pagination coverage; empty or partial
reports remain denied.

## Errors, security and observability

Missing profile, provider failure, malformed data and stale snapshots become
fixed `unavailable`/`denied` statuses with stable reason codes. Raw payloads,
exception messages, URLs with credentials and account identifiers beyond the opaque
profile reference are never returned. The evidence records only status, reason
codes, operation names and safe aggregate values needed by reconciliation.

## Acceptance commands

```text
uv run --project python --locked pytest python/apps/quant-engine/tests/test_bybit_profiles.py python/packages/quant-execution/tests/test_bybit_projection.py python/packages/quant-execution/tests/test_bybit_preflight.py
uv run --project python --locked ruff check python/apps/quant-engine python/packages/quant-execution
uv run --project python --locked pyright python/apps/quant-engine python/packages/quant-execution
```

This design does not claim an HTTP implementation, live credentials, private
connectivity, account funds, Nautilus reconciliation or order acceptance. The next
design must add a host-owned secure credential resolver and an HTTP transport that
enforces the endpoint, GET allowlist, timeout and no-redirect rules before any
authorized read-only live preflight. Those remain separate activation gates.
