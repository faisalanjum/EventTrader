# COLLECT_ENTRY_2129

The thin collection / resume entry for the seven-source packet, and its focused
proof. Codex SEQ 2129. No model call, no signer, no lock, no key mutation, no
grading, no publication.

## The serial rule

`unit_1947/logs/attempt_codex_pkt2129_verify/exit` read **0** and
`state finished exit 0` before any native check of mine ran; the test refuses to
start otherwise. The shared binding `81374968…` and the preparer `f71efd95…`
were **not touched** while root's rerun was in flight, and are unchanged now.

## The callable

```
collect_seven_2128.collect(E, X, B, V2, V3,
                           report_path, expected_sha256, states)
```

Entry file `collect_seven_2128.py`
`44d5faa38dbeb75a6d0fb61cf7aacf68c7004dc8fa07cdaed59b6aa131f0cad9`.
It is also runnable directly as a boundary payload through
`unit_1947/ledger/run_real_1947.sh` with the real map and environment, which is
how every other payload in this lane runs.

**The required inputs are three, and only three:**

| input | meaning |
|---|---|
| `A7_COLLECT_REPORT` | the frozen packet report to collect against |
| `A7_COLLECT_REPORT_SHA256` | that report's expected sha256 |
| `A7_COLLECT_STATES` | JSON list of official workflow state paths |

## What it does, and what it refuses to do

It consumes the report by its expected hash, checks the three identities the
report pins — the round owner, the shared binding and the wording renderer —
against the live files **before** relying on anything, then enters the SAME
shared binding the preparation used. There is no second set of source pointers
and no second prefix installation: the scope comes from
`a7_round_binding_2128.scope`, so preparation and collection cannot drift.

Identity is checked through the receipt's own owner: `F.receipt_problems` must
be empty and the receipt's prompt block must still be the report's. Both
survive a resume, which a raw receipt hash does not once a state is appended.

Saving, proof and accounting are `F.record_state` and `F.finalize`, unchanged
and uncopied. Every recorded state, every problem and every outcome is reported
exactly as those owners return it, including incomplete and invalid ones. There
is no verdict, no retry rule, no key edit and no fallback to an earlier answer
in this file.

## The focused proof

Run `core_col2129_a`, raw exit 0, proof
`COLLECT_PROOF_2129.json` `2392ef861d92241ad670460437fb634199757da2141dc160497dbeb810953e92`.

The test invokes the **real** entry — it asserts the callable and its pin tuple
exist before anything else — against an isolated, clearly named **zero-call
probe packet** prepared through `F.prepare_v6` under the same shared binding.
No model response is faked anywhere.

| check | result |
|---|---|
| seven uncalled events accounted | all seven **missing**, reason *no official state* |
| ledger | scheduled 7, valid **0**, invalid 0, transport_no_answer 0, unproved 0, missing 7 |
| phase complete / retry / child | false / none / none |
| paid raw files | none |
| ledger before this round | 670 |
| resume is idempotent | outcomes identical, finalization byte-identical, receipt states still empty |
| the REAL packet | **unchanged**, 8 files, 0 states, no finalization |

Interface refusals, each after a valid control that re-collects the probe
cleanly:

| case | refused with |
|---|---|
| wrong report hash | *the packet report is 16eb47c0…, not the expected 0000…* |
| drifted binding identity | *renderer_sha256 drifted: …a7_source_context_2127.py …* |

The history, pointer and eleven-artifact mutation proofs were not repeated, and
neither completed source call was re-run: the two-result and eight-identity
regression stays where it is, in `codex_sources2126_reg`.

## The genuine remaining gap

**The valid-outcome path of this packet's collection is unexercised**, and it
cannot honestly be exercised yet. There is no real model response for these
seven events, and faking one is exactly what this proof must not do. What is
proved is the missing / incomplete path, the identity and resume behaviour, and
the two interface refusals. The first real collection will be the first time
`finalize` returns a `valid` outcome under this binding — the owner is the same
one that already produced two valid outcomes for the completed 2123 round, so
the untested part is the binding's use of it, not the owner.

## Scope

Files added, both in `unit_2128_source_corrections`: `collect_seven_2128.py`
and `test_collect_seven_2128.py`, plus this report and the proof, probe packet
and probe report under `core_col2129_a`. The shared binding, the preparer, the
frozen seven-source packet, root's candidate, `unit_2020_codex_check` and every
earlier file are byte-identical.
