# G1 segment2 — independently checked collection, not an A7 score

2026-09-13 Eastern. Core2092/current archive SHA256
75f58c482e5013e8e631461f2456508ee19660aaa00d175af9bc56b71d909640.
Main2dc0ad39f30dba4756078573f5e80038465939cc; recovery at review
64fb0143a4b29f24a25a14f45a550dfce7a9470e. All paths below are relative to
the recovery worktree's a7_recovery directory unless absolute.

## Result and independent checks

The second batch returned50 whole answers, of which49 satisfy the frozen
response contract and1 does not. Combined with segment1:102 completed model
calls,101 valid readings,90 primary lanes never launched,1 eligible retry.
The original192-primary denominator is unchanged. Total completed calls
before G1 were668, so the current total is770, not769; invalid replies count.
The older zero-worker dispatch refusal remains a separate recorded refusal.

1. Rehashed every one of102 preserved native files against its original;
   exact matches. Strictly parsed162 JSON lines across all50 worker
   transcripts; each raw text bound to the native request/response and to
   the matching journal start/result/official result. Every worker used
   claude-sonnet-5, with no tool calls.50 distinct agents,requests,responses;
   no identity collision against the earlier52 workers. Identical raw text
   across independent readers is allowed and is not an identity collision.
2. Reused the existing read-only replay driver through the real boundary:
   codex_g1review2092_a payload exit0,stderr empty. The existing native
   auditor replayed52+50 whole answers with no problems. C.evidence selected
   exactly101 valid readings and withheld only G1-050/G1a among collected
   rows. No grading owner, candidate, input, raw result or finalization changed.
3. The whole-run pin before retry preparation was
   e8d3e334c1af52bc57302377bfd9c25433eea04e49beb205e55292ba33a3e465,
   221files. It was measured independently and unchanged by the proof.
   Recipe: hash each file, form `sha256  ./relative/path\n`, sort whole
   lines bytewise, concatenate, hash. A later prepared segment adds files;
   do not mistake the historical221-file proof for a pin of that newer run.
4. Read the actual invalid whole text and its frozen prompt. The prompt
   requires one JSON array. The reply was five newline-separated objects.
   The refusal is correct. Do not wrap or repair it, substitute the twin,
   relax the parser, or infer an accepted answer from otherwise plausible
   individual objects. Only its one allowed fresh attempt2 is authorized.

REVIEW: unit_2020_codex_check/codex_g1review2092_a/REVIEW.json,
SHA25633f9530ac0a353e6073d0a06602bee2739da4f6bbcd5653a858e1c6905c884f8.
Raw proof logs: unit_1947/logs/attempt_codex_g1review2092_a.
stdout252bytes,bda2ad6f391063a92eabfaaef706b316c270c8bb36849c3e7b973ea00d8363b0;
stderr0bytes;exit0. This is collection/native/schema and paired-identity
evidence, not final A7 semantic adjudication, field accuracy or a pass.

## Exact segment2 evidence

Workflow wf_afd003ba-837,task wb0a81a33,launch tool
toolu_01LEUg4tMwgLDV4RSCCL4U81. Native start1789272353938ms,duration372626ms;
50workers,947738tokens,0tools. Actual published script path and50 arguments
were independently matched to the frozen invocation before accepting this
evidence. Parent-state defaultModel is not the worker model; the original
worker transcripts provide the model identity above.

Under unit_2088_real_grading:

| Artifact | SHA256 |
|---|---|
| NATIVE_INVENTORY_SEG02.json | 61f39f1a2bd452ca2264c7203fe48094e72bbead69fe22fa5dda20ad283e21af |
| OUTCOME_SEG02.json | 4a7f6a632a73aaa9555a911b4925dfd8149a5c7e36fb0bc353fc077114feeac0 |
| LAUNCH_RECORD_SEG02.json | 2d82847942256bf803edb6f1f1e6638a33d6415bae73a10c65e7ed3adb3f88fe |
| g1/finalization.seg02.json | 2f60306b195429b3de7d738ed0fc1e2e97e67fa0c53091ca2fa6bc52959293e4 |
| g1/accounting.seg02.json | 1b0719e502752077342dff95ecb2f1b721eda311e910b21a6317db965f8e6ff3 |
| g1/state.seg02.json | 4b18b37123ae81561261eee1cd78a64dadf5844277f556658224b6cadab2fbe8 |
| native/seg02/wf_afd003ba-837/wf_afd003ba-837.state.json | 22e37f89b11a6870042a93f7fc92323fe12f20573d35f754411f16d19080081e |
| native/seg02/wf_afd003ba-837/wf_afd003ba-837.journal.jsonl | 56bd8d18739b409d8859e7fbf5936035f0e82a9e9a2c2f465dba35a0b16cfbcc |

Rejected lane G1-050/G1a,agent a20675a6523537c8f,request
req_011CeznXoH2A58WKA3Vdmfbv,response msg_011CeznXodMd1BsNAPxAFQwD;
raw294bytes,826e27d50299ccd4cb5dceccd35874e0615b91bbbc1cc19141d04d6c5f4f0b28.
Core ingestion log: unit_1947/logs/attempt_core_g1ing02_2091_a,
payload exit0,stderr0; segment_clean false, one named invalid/retry.
An exit0 from the ingestion command does not turn that segment clean.

## Smallest next task and scope corrections

Codex2092,9079e1896a99d0e1821c45d05d84af18e6e21ae356f54cb1e5ac453f2d754d23,
authorizes only one bounded G1 collection, maximum91 further calls:
already-prepared G1-050/G1a attempt2, then only if clean the90 unused
primary rows102–191 through the unchanged byte-bounded publisher. Stop on
any refusal, invalid/missing reply, drift or failed finalization. No further
retry, G2/G3, source/key/signature call or successful-call repetition.

Retry preparation codex_g1retry2092_a passed through the existing operator;
do not prepare again. Segment3 receipt
2b89e744483c2cd8e86175555eadb477e1adeb80fe0f0674bafa4acb32a106db;
invocatione0aa82646d243cb596e0aeb0442fcae846a311c204fd59b0f15f4882fa5cf8fe;
script26fa59e889e4f192a8545bc3b4e776fa8fa819778ebd46d7844df71dd0c6b368,
22069bytes; args0b0774b59fdfe1f0ac3879d20fdf6503d72a01a82399e8177e9a2db34c0456d0.
The retry retains prompt1848b01aa03967034b17f49389baf37f9bb0450054ff6753dfd4885fb571729a
and binds the exact segment2 finalization as its parent. No AI call was made
by this preparation.

Core's proposed pair-aligned chunking is unnecessary: C.evidence gathers
all segments before C.lane_relations pairs by frozen event identities.
No split-policy or grading-owner change is approved. Two supporting record
helpers need only current receipt/authority labels and removal of their
duplicated valid-only cumulative counter before reuse; their current saved
segment2 data remains accurate. This checkpoint does not certify later
helper edits or anything still running.

The hook did not authorize extra work. Core's claim of no foreground wait
over15seconds is false: native transcript toolu_01C3YCtfycHBRUGPidH3MHQy at
04:08:25Z requests60seconds; toolu_015vNjKBTXQM6mozFvPnVsrz at04:09:31Z
requests100seconds, after a completion waiter was already armed. Codex2092
requires existing completion notifications, no redundant foreground polls,
no hook/settings changes, one monitor and one final report. No direct
process intervention or extra mailbox task was necessary.
