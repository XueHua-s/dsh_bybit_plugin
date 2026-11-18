# Sandbox image digest pin — 2026-11-19

## Scope

This slice closes the mutable-container-image gap identified by the acceptance audits. Generated research code continues to run without exchange credentials, network access, writable root, or elevated capabilities; the image reference is now immutable.

## Change

`apps/dsh-plugin/src/lib/sandbox.ts` uses:

`node:22.20.0-alpine@sha256:dbcedd8aeab47fbc0f4dd4bffa55b7c3c729a707875968d467aaaea42d6225af`

The digest was read from the local Docker image metadata immediately before the change. The sandbox test asserts the image reference format (`repository:version@sha256:<64 hex digits>`), so a future tag-only edit fails the unit test.

## Verification receipts

| Command | Exit | Evidence |
|---|---:|---|
| `docker image inspect node:22.20.0-alpine --format '{{json .RepoDigests}}'` | 0 | Returned `node@sha256:dbcedd8aeab47fbc0f4dd4bffa55b7c3c729a707875968d467aaaea42d6225af`; no credentials or payloads read. |
| `node --experimental-strip-types apps/dsh-plugin/test/sandbox-output.ts` | 0 | Stream capture retains the fixed output budget under flooding. |
| `node --experimental-strip-types apps/dsh-plugin/test/sandbox.ts` | 0 | Container smoke confirmed no host-file visibility, network access, or writable root; the pinned digest assertion passed. |
| `NX_DAEMON=false NX_ISOLATE_PLUGINS=false pnpm run verify && pnpm typecheck:tests && pnpm python:lint && pnpm python:typecheck && pnpm python:test` | 0 | Nx/TypeScript/Bundle/SDK checks passed; strict test typecheck passed; Ruff and Pyright passed; 289 Python tests passed with 11 upstream warnings. |

## Boundary

The digest is an upstream image identity receipt, not a complete supply-chain attestation. CI now pulls this exact immutable image and reruns the Docker smoke before completing verification. Monitoring remains process-local, and full unattended execution, exchange reconciliation, and Plugin Manager upgrade preservation remain open acceptance items.
