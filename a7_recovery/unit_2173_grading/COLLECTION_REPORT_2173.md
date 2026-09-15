# The bounded 38-question collection

Core 5ae9b86b, 2026-09-15 UTC. The approved changed-task collection ran to the
end. No prompt, question, key, score or existing answer was changed; the two
completion CANDIDATES are written and deliberately NOT persisted.

## What was called

| | lanes required | usable | invalid standing | exhausted | waiting |
|---|---|---|---|---|---|
| G2 | 18 | 18 | 0 | 0 | 0 |
| G3 | 6 | 6 | 0 | 0 | 0 |
| **total** | **24** | **24** | **0** | **0** | **0** |

**26 model calls: 24 primary and 2 invalid-only retries**, inside the
authorized 24 + 24. No lane was reserved or called twice, no valid answer was
repeated and no semantic disagreement was rerolled.

Questions are the other denominator: **38 required, 38 covered** by lanes whose
every reading stands valid.

Two readings came back unusable on their first attempt and each was replaced by
the one existing invalid-only retry:

| lane | attempt 1 problem | retry |
|---|---|---|
| G2-000/G1a | the reply did not parse: the reply opens a fence it never closes at the end of the reply | attempt 2 valid |
| G3-002/G1b | the reply is not a JSON array | attempt 2 valid |

Both were format failures, not refusals: the model answered, the operator's own
parser rejected the shape. They were recorded and carried, they halted no other
lane, and the retry was the existing path at attempt 2.

## One refusal, which was the lawful end of a root

`prepare` for G3 after its last primary segment returned raw exit 1 with
`REFUSED next_admissible: ['every primary lane of this root has been called']`.
That is the publisher saying the root has no uncalled primary left, not a
failure. The driver refuses to advance on any nonzero raw exit, so it stopped
there and I went to the invalid-only retry path by hand rather than letting
anything pass. It is the only nonzero raw exit in the whole collection.

## The layout, frozen before any call

Roots, receipts, scripts, arguments and manifests were frozen and preflighted
first, with zero model calls, and the frozen root row ids equal the candidate
launcher rows exactly - 18 and 6, in order, none unknown, missing or repeated.
The lane profile and owner pins came through the existing preflight from the
proved 2161 root, not from this session: lean-probe, sonnet resolving to
claude-sonnet-5, effort high, output limit 128000, `Read` disallowed,
max_attempts 2.

The runtime path and the durable path are ONE directory through the map, so the
receipt, the invocation and the executed script name the same bytes and nothing
is copied between binding and call. The map is map2161 with only its two
execution bindings repointed at the new unit; every other line is byte-identical
and the old map and roots are untouched.

## Evidence

Every returned run was preserved before anything read it - the official state,
the journal, the exact returned payload and every child transcript - and each
copy was byte-compared against its original, with zero mismatches. 20 preserved
runs, 20 finalizations, 40 ledger lines.

## The completion candidates

Produced by the existing native chain (`C.evidence` -> `C.relations_from_run`
-> `C.g23_identity` -> `C.complete_g23`) with `persist_g23` deliberately NOT
called.

| | questions | credited | unresolved | evidence problems | completion problems |
|---|---|---|---|---|---|
| G2 | 31 | 25 | 6 | 0 | 0 |
| G3 | 7 | 6 | 1 | 0 | 0 |

All 24 lanes were read and all 24 produced a selected relation. Each root's
completion names the same root hash the freeze produced and the durable root
still carries.

The 7 unresolved questions are blind-lane disagreements, which is the
lifecycle's own outcome and not a defect:
`M43e87509e5cc819b`, `M24065e66c77fea00`, `Mece90a618a058690`,
`M4ca257814a3d2655`, `M357a5ef0bb7e36e6`, `Mf1aca8c5849b0770` and
`X56415b76439cd6be`. Six are "the readings disagree" and one also carries
"a reading could not establish it". I supply no verdict for any of them.

## What this does not establish

Any score, any final verdict, and any claim that a corrected answer is better
than the one it may replace. Nothing is persisted into the immutable
candidates. The ordered consumer check, the verification of these returned
bytes and the final scoring are not mine.
