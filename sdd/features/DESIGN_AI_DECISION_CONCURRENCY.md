# DESIGN: Concurrent AI decision writes

## Outcome and scope

Prevent a delayed AI decision, evaluated against an old simulated track, from
overwriting a newer decision committed by another tool call. This is an
optimistic concurrency guard for the local simulated journal only. It adds no
exchange, account, risk, or order capability.

## Contract

- A decision writer must compare the current stored AI track with the exact
  track snapshot used for its evaluation inside the synchronous store mutation.
- If the track changed, the writer rejects with the stable error
  `ai_track_changed_during_decision`; it must preserve the newer track and must
  not commit the cycle receipt.
- If persistence fails after replacing the track in memory, the writer restores
  the prior track only when the store still contains the attempted replacement.
- A successful write persists first and commits its cycle receipt second.

## Design rationale

Decision evaluation performs network reads before its final local write, so two
calls can observe the same initial state. A single-threaded JavaScript runtime
does not remove this race: asynchronous work can interleave between snapshot
and commit. An in-mutation deep comparison provides a small compare-and-swap
boundary without holding a lock across network I/O. The losing proposal is
rejected and can be reconsidered with fresh state; the writer never merges
positions or accounting from stale decisions.

The store mutation is synchronous, so the compare and replacement execute in
one JavaScript turn. `isDeepStrictEqual` compares the JSON-shaped decision-track
snapshot without relying on object identity, which can change across cloning.

## File manifest

| Path | Action | Purpose |
|---|---|---|
| `apps/dsh-plugin/src/lib/ai-decision-writer.ts` | Modify | Reject stale simulated-track writes and conditionally restore failed writes |
| `apps/dsh-plugin/test/ai-decision-writer.ts` | Modify | Cover conflict preservation, failed persistence, and successful receipt order |
| `sdd/reports/BUILD_REPORT_AI_DECISION_CONCURRENCY.md` | Create | Record actual verification and acceptance evidence |

## Acceptance checks

1. Given two decisions based on the same track, after the first commits the
   second must fail without replacing the first decision or committing a receipt.
2. If the local persistence operation fails after applying the replacement,
   the prior track must be restored and no receipt may be committed.
3. On success, the store write must precede receipt commit.

## Limits

This does not serialize user-visible prompts or automatically retry a stale
proposal. It rejects stale work so a later Agent turn can recompute from current
state. It does not establish predictive quality or exchange execution.
