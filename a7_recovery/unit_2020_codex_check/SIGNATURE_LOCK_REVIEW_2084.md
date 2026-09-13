# Real A7 source-key signature and lock — Codex2084

Reviewed 2026-09-12 Eastern. Source closure and required-case reasoning remain
SOURCE_RESULTS_REVIEW_2081.md and COVERAGE_REVIEW_2072.md; this review does not
replace source truth with the signer's summary. No new model call was made.

## Exact original signature

Core2084/current archive SHA256
fe57e3e00d66450c7a48664e44262085a8a937fd48bc4a16b06e4889e92d64d8
answers Codex2083
7f380c75c4d19500a639daab2a1acf75a3cabcc5ed2b47adf420bbbadc3b85ea.
One launch: wf_cf398299-777, agent aded04e635e6e4aed,
request req_011CezWixhkmThhkPDG3zhEk,
response msg_011CezWiyEm4qTNsfYcgfojq. No retry or repeated success.

Existing SP.prove recomputes official state, complete ordered transcript/raw,
exact prompt/script, qualified role and current2068 input. Durable state and
transcript copies compare byte-for-byte to the actual official records.

| Artifact | SHA256 |
|---|---|
| Raw,560 UTF-8 bytes/558 characters | 46c0847c677657877b7a1a914404ec35be397023ba1394db039b3d79872a2ee3 |
| Official state and durable copy | dbba413f53faec8d5a35c00e5f54124566e895dda44ebecdf11d5438637b8d48 |
| Native transcript and durable copy | 99d5c7c158508ab06433ddbfbcd70509b8588eab74a4ea895d965c3ea139dbd7 |
| Standalone proof driver | 5978ef545d57897dbb8b01ec984f220891d5107205e07e32ea837a5f4e62ef2e |
| codex_signproof2084_b stdout | 7e96e017c2b8e401d0adedce0c08e7c77d0efa7e6cb62ad34a45eff6f6f9f1df |

Payload exit0, stderr empty: signed true, blocked[], parser problems[].
Observed opus/high/lean-probe, native claude-opus-5, no tools; row model
claude-opus-5[1m] is the separately declared row identity.146054 tokens,
121931 ms. Actual cumulative accounting667+1=668, not the6000 soft target.

The first proof codex_signproof2084_a failed because its caller omitted the
existing independent-key role scope, and its map lacked the new scriptPath.
The real scratchpad script still exists and hashes to the candidate's exact
87f896d24bb211524467239ed7482b40d88d439bd3aa0949102b5baefcace9fe.
Only one ro mapping was added in map_2084.tsv
da4beab254e5e97b2242df5cb85c11a0026365018a0d692169c65bc794c0e1ac.
The proof now checks SK.role_problems and exact key_transport/manifest
agreement before entering SK._key_role_binding(). No arbitrary model
constant, frozen owner, original map, candidate or native record changed.

## Actual harvest, lock and fresh-process verification

Current lock authority: archive_CODEX_2084.md
747423cd8982530aea76601801c107fa2673284b406db81e7a55d66a02fa0fcd.
Caller lock_real_key_2084.py
e6d9b9c9d18bbb2e6bf1ec16749f24bacb5f77e62fc26bd922b16aab3da58e72
uses the existing R candidate context before current N input, recovery and
complete X history. Exact unit_2005 candidate owner is preloaded and checked.
The existing harvest and compact lock owners alone persist their outputs.

The original signature is independently compared against13 prior key runs
using the existing spent-identity owner:285 run/agent identities and284
request/response identities, zero collisions in all four fields. The absent
answer identity from a prior no-answer attempt is not invented or hidden.

Both actual runs passed with payload exit0 and empty stderr:

| Run | stdout SHA256 |
|---|---|
| codex_lock2084_a | 94a8e17ce51ae607e5be55ccbbb5af31ebdb7d4f7020e14b40022f67ce16697b |
| codex_lockcold2084_a, fresh process/read-only mode | bfeb744a280dc73aa2641edd2e52a53d28121cf433bb20e2d4471e907af388ee |

The real candidate and every lock value re-derived. All33 existing mutations
refused:15 artifact identities,13 signer fields and5 aggregate blocks.
Valid controls passed before and after; the fresh process agrees.

Selected directory: unit_2081_final_key_candidate/codex_cand2082_a/candidate.

| Final artifact | SHA256 |
|---|---|
| key_identity.json, unchanged | e77684b2472f583cce116a1cadc845bcadcfd5b84a808ddbaec8139adaf13635 |
| a4_final_key_lock.json | dc9192271da3af0c3a0bb2fc2590c151073076f2893ac21136aee30424022e52 |
| a4_final_key_lock_receipt.json | a52323e2ee08be81714109d7f743036c553ebe28f15b529f21dc9ef5e4fad991 |

Counts:33 sources,191 rows,163 facts/DU-worthy facts,34 controls,
10 exclusions,44 abstentions,11 resolved kind differences,0 exact duplicates,
0 open issues,0 floor failures. Mechanical41 sequential-tag rows do not
replace the separate proof of five actual required sequential cases.

## Ruling and remaining scope

Source truth and formal key signature/lock are VERIFIED. The final real
saved-answer/grading freeze, approved preparation commit/push and actual
grading remain. Core owns only the unrun setup under2084. Reuse all382 saved
answers and all668 actual calls. No A7 score or PASS is claimed, and these
checks establish the inspected contracts, not universal reliability.
