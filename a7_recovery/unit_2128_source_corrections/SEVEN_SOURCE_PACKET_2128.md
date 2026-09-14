# SEVEN_SOURCE_PACKET_2128

The seven-source correction packet, assembled and proved through the existing
owners. Codex SEQ 2128, work order Revision 171. Armed and **unrun**: no model
call, no signer, no key mutation, no grading, no publication.

## The serial constraint

`unit_1947/logs/attempt_codex_predecessor2128_final/exit` read **0** before any
native check ran, and the caller refuses to start otherwise. No verifier of
mine overlapped root's.

## What was built

| file | role |
|---|---|
| `a7_round_binding_2128.py` | the ONE current-round binding, shared by preparation and collection |
| `prepare_seven_2128.py` | assembles the packet through `F.prepare_v6` and proves it |

The binding owns pointers only. `F.prepare_v6`, `record_state`, `finalize`, the
native proof, the budget and the retry law stay exactly where they are; nothing
is copied or re-stated, and no phase or framework is opened.

Run `core_pkt2128_d`, raw exit 0, packet report
`SEVEN_SOURCE_PACKET_2128.json` `032d7265675c3f85ddf3d23add3c31af041249662d3221bad5ff189135b7c362`.

## The binding

Every pointer is derived. The predecessor is the completed 2123 round, receipt
`472a4b7f…`, finalization `c8e2bd22…`; its own findings come from the pinned
`SOURCE_KEY_RECHECK_BINDINGS_2120.json`; the prior chain is the three earlier
v6 rounds; and the signature sits at the **predecessor's own round boundary**,
not immediately before this one. The seven-event population is read from the
two measured review files rather than typed, and returned in frozen event
order — positions 4, 7, 9, 14, 17, 20, 25 of the frozen inventory.

## What is proved

| acceptance item | result |
|---|---|
| seven events, ALL original task rows | 7 events, **47 tasks**, every event serving all of its rows |
| 33-source carry | 33 carried |
| the other 26 raws and origins unchanged | **true**, both |
| no output-informed body field | every body is exactly the payload owner's view + the prior source key + a finding whose only fields are `source_id`, `raw_sha256`, `row` |
| exactly the approved prefix delta | **true** for all 7; the clarification appears exactly **once** each |
| 4 historical rounds / 12 recorded prompt hashes | 6 + 2 + 2 + 2 = **12**, all byte-exact with the install held |
| real prepare/receipt/launcher agreement | the receipt's own prompt hashes equal the rendered prompts; 7 invocations written |
| ledger before 670, counts by the existing owner | before **670**, 7 corrections + 1 signer, after_planned **678**, worst case 686 of 6000, retry law `invalid_response` at most one per call |
| source-key model/route/identity pins unchanged | the receipt transport block is **identical** to the predecessor's |
| collection/resume uses the SAME binding | labels identical, prompt hashes identical, `receipt_problems` **empty** |

Largest rendered launcher **254,870 bytes**, under the 524,288 transport limit.
Prompts range 113,714–240,694 bytes.

Three of the seven serve `v6_shard` and four serve `prior_key_shard`, following
each event's own current origin — the two corrected in the completed 2123 round
and one corrected earlier now carry the v6 origin, and the renderer names the
round that really produced each reply.

An unrun packet must not read as an answered round, and it does not: the merged
key refuses with *"7 named events have no accepted v6 correction"*.

## Negative controls, each after a real intact positive control

Every refusal runs after a fresh cold operation in which the intact binding
counts 670, so no accepted-result cache can hide a missing or misplaced
signature.

| case | refused with |
|---|---|
| omitted signature | the merged key cannot read the predecessor's two events |
| misplaced signature (wrong round boundary) | the completed signature does not verify — `receipt.v1_evidence is not the expected value` |
| signature outside this history | *a signature names a round outside this history* |
| stale current raw | *a finding does not bind the exact source/raw/row* |
| changed history | the completed signature does not verify, same nested cause |

## Two things reported rather than fixed

**1. The served wording is part of the BINDING, not of preparation.** I found
this by failing: a collection or resume caller that entered only the successor
scope recomputed the prompts **without** the clarification, and
`F.receipt_problems` then refused the packet's own published receipt. The
published receipt records the hashes of the prefix actually served, so the
install must be held wherever the receipt is read. The shared binding now owns
it and both callers take the scope from there, which is why resume comes back
with zero problems. No owner logic changed.

**2. Two of the five refusals surface through the lock owner's re-derivation
path.** `misplaced_signature` and `changed_history` refuse as *"the candidate
no longer re-derives"*, with the real cause nested inside the message
(`the signing gate is not clean: receipt.v1_evidence is not the expected
value`). The refusal is genuine and the cause is visible, but the top-level
wording names the re-derivation rather than the boundary. I did not change any
owner to improve the message; naming it here is the report.

## Scope

Files written, all in `unit_2128_source_corrections`: the shared binding, the
preparation caller, this report, and the packet with its receipt, seven
launchers and the proof JSON under `core_pkt2128_d`. Root's candidate
`a4_v6_successor_chain.review_2126.py` was loaded read-only and not edited;
`unit_2020_codex_check`, the accepted 2121 owner, the frozen histories, the
completed 2123 calls and every earlier report are untouched.
