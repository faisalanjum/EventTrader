# Real G2/G3 launch preparation — no AI call yet

Codex, 2026-09-13. This records preparation, not authorization to call or an
A7 score. The affected regression must close and verified preparation must
be committed/pushed before Core receives a model-call task.

## What is reused

The unchanged 382 producer replies, signed 163-fact key, and 194 completed
G1 calls. The partial-report rule keeps the exhausted five-question gap at
zero credit and cannot convert missing judgments to PASS. Native TEST
consumer proof: `codex_partialscore2099_c/SCORING_CONNECTION.json`,
SHA256 `30ae7917ec623986bd9d411e5fb907097d256cbdb4a74d3ac63bdfc5192e05cf`.
These TEST G2/G3 replies are never real model evidence.

The existing `run_grading_2086.py` works unchanged for G2 and G3 through the
existing G/W lifecycle and automatic task parser registration. No new runner
or scoring framework is needed. Its historical `g1_args_segNN.json` filename
does not change the task: the frozen root and rows own the actual kind.
The new preparation payload only freezes these already reviewed candidates.

## Frozen roots and actual first publications

All paths start at `../unit_2100_g23_grading/`.

| Item | G2 | G3 |
|---|---|---|
| Required primary calls | 140 | 32 |
| Questions | 306 | 117 |
| LAUNCH.json SHA256 | `7e47f8017c011d1fc4eeb093aa632d621a353d0c96f5973eb9948e83156ab764` | `c1cb93906e25aa6cf557345578aabe8c0522aeb1f3fc1271bedc529f840930bd` |
| run/root.json SHA256 | `1ee010cf06a9a726c5e12c4893031dbdad075f4f39a09c0f92298bbafa8a6a18` | `56eeda65fd0863823531410aeb05b2a54486eda9c44663222e6af86941e44c6e` |
| Segment 1 receipt SHA256 | `569802e2d971c0cb11d2a5fa0d35feb556f29feb228ebe53031d09d5591e5e80` | `47140a643fec49a549542b64f295e9b9bec486f5f82365993f62aa46cf114e2a` |
| Segment 1 script SHA256 | `6b5af0d57a429526363c2874401ab0504bdd0461b3c768c4ad3707235b6a4a75` | `9b82c822bf6ae1f7cda52d32f5399146f2d98540b5d53020ec159db2a56b2ff8` |
| Segment 1 bytes / lanes | 432989 / 1 | 449768 / 3 |

Scripts are the actual files under `G2/run` and `G3/run` in recovery. Do not
make a separate executed copy in `/tmp`. Call only the exact path and args
the original preflight returns. Segment 1 is ALREADY published: do not call
`prepare` again before collecting/preserving/ingesting that exact segment.

Every root row carries the original verified runtime input declaration;
every candidate/prompt/owner identity is checked by the unchanged owners.
All 172 single-lane rendered scripts were measured separately, including
escaping and row ordinals: G2 maximum516367, G3 maximum207821, limit524288.
The whole 423-question/evidence comparison is unchanged by regrouping.

## Actual checks

Logs are under `../unit_1947/logs/attempt_<tag>/`; the `exit` file, not the
outer shell completion, is the payload result.

- `codex_g23freeze2100_a`: exit0, stderr0. Two fresh roots, no publication
  at the time LAUNCH.json was written, no call. The following preparation
  commands then published each first segment through the existing operator.
- `codex_g2prepare2100_a`, `codex_g3prepare2100_a`: exit0, stderr0.
- `codex_g2preflight2100_a`, `codex_g3preflight2100_a`: exit0, stderr0.
- `codex_g2wrongreceipt2100_a`, `codex_g3wrongreceipt2100_a`: expected exit1,
  each refuses the zeroed external receipt hash at the original preflight
  check. Actual receipts/scripts are unchanged. These are negative controls,
  not unresolved grading failures.

Independent host reads also matched every invocation arg against its saved
args file and measured script/receipt/root hashes, not just printed output.
Exact first lanes: G2-000/G1a; G3-000/G1a, G3-000/G1b, G3-001/G1a.

## Accounting and limits

862 completed prior calls; 172 required never-collected grading calls.
1034 after all primaries; at most1206 if every one uses its existing single
invalid-only retry. No success may repeat. The original 6000 ceiling is
retained; it is not a target. Neither root has any AI call yet.

The original publisher, native auditor, finalizer and completion owner still
decide identity/validity. Preserve each actual native state, journal and
worker transcript byte-for-byte into a new recovery directory before
ingestion. The existing publication receipt plus the exact Codex call task
already bind the request; do not add another launch-record framework.
Fully evidenced invalids remain counted; refuse missing evidence, identity
drift, unfinished calls or safety conflicts. No third attempt, main edit,
production/DB action, hidden-answer access or A8 permission is implied.
