# G1 exhausted retry — preserved failure, not a clean result

2026-09-13 Eastern. Core2093/archive
324939e7081a03bf1d7761089f59d1ca9f85d8a58cf16e70de89e279a379959c;
Codex2093 cc59a9052f559faac9aabb007bce97d74fbf670d1cd1b6c1b94c6edfbac39525.
Recovery parent at this review30bafd205af0f83cb58469add364ce9983a353aa,
verified normally pushed. Main remains2dc0ad39f30dba4756078573f5e80038465939cc.

## Evidence and result

The sole G1-050/G1a attempt2 ran as wf_e1e631c0-080,taskwo17p2zk8,
5190ms,20175tokens,0tools. Independently verified all4 native preserved
copies against their originals and strictly parsed the worker transcript.
New agent a64b830ed60536184,request req_011CezoUQtfHAhPfe4SM7Jvi,
response msg_011CezoUREkWwN6AgzPhydRX are distinct from every prior102
worker/request/response identity. The original journal start/result, official
returned row and worker whole text agree. Actual published row is attempt2,
ordinal100, unchanged prompt1848b01aa03967034b17f49389baf37f9bb0450054ff6753dfd4885fb571729a.

The294-byte reply is exactly the earlier malformed newline-separated objects,
SHA256826e27d50299ccd4cb5dceccd35874e0615b91bbbc1cc19141d04d6c5f4f0b28.
It is NOT one array as required. Preserve both invalid attempts. No third
attempt, repaired raw text, twin substitution or relaxed parser is permitted.
Two identical observations do not prove the model is generally deterministic.

Existing native/completion owners replayed all three segments independently:
codex_g1review2093_a payload exit0,stderr empty,103 whole answers,zero
evidence problems,101 valid selected readings. REVIEW.json
63f10cc93b6b8dc5d8b19039511addfae382da25f119b3287c1f2c53fe1a7501,
under unit_2020_codex_check/codex_g1review2093_a. Whole-run pin before
segment4 preparation23025199c312d55e97b82bdd951ed2d302303ae2e17aec6a866d5030601d15b5,
231files. The proof left the run unchanged. Raw logs are under
unit_1947/logs/attempt_codex_g1review2093_a.

Actual finalizer result:0valid,1invalid,0retry,0uncalled in segment3;
finalizationbdf6e8fd718bd01f39253561f470d0fc977a9a986a8cad320ab3e1ad44760bfa.
Accountingd6fef83b5252421efec8484fd7ce7cab2ec79b67d778888ad87ec12808690678;
statef77e5578a919b4611f8552958ad4ffdcd50ce15038fd5f42e632caa5d86685b6.
Native inventoryba533d813a22903a2da8a2810c32c0378994dd1c3cb72a6b8b09505756f8ef9f;
outcome8b8969f9d91c582416afc7b089d59788b31bc075cd52c6ae31fbc78632b0d146;
precall recordbbc648792c314627fdfc0e70af5d8d24ef6177619ba6631f4a52b6e10874e27f.
All are under unit_2088_real_grading and remain immutable.

## Accounting and next task

G1 has103 completed calls:101valid and2invalid attempts on one lane.
102 of192 primary lanes have been attempted;90 remain unlaunched.
Global completed count668+103=771; the earlier zero-worker refusal is
separate. The invalid grader rate is not the producer invalid-response rate.

The frozen five question bindings for G1-050 are P2/source
0001104659-25-118458. C.complete/G.terminal_categories retain the missing
reader; B._safety_from sends that incomplete finding only to its own leg.
WorkOrder1.5 retains exhausted invalids, while Step1 requires the remaining
scheduled cases and separate arms to be measured. Codex2093 therefore
authorizes only90 uncalled primaries,maximum90calls,under unchanged owners.
This does not fill the gap, waive a bar, promise A7 PASS or advance LaneA.
Stop on a NEW invalid/refusal/drift; no further retry under that message.

## Necessary helper changes and scope

The supporting precall record now derives current authority and attempt from
actual artifacts, and reads accepted lanes from finalization rather than
mistaking every previous invocation for a forbidden successful-call repeat.
The actual segment3 record correctly reports2092,attempt2,101 prior valid
readings and zero repeated-valid lanes. Preservation now emits only actual
per-run counts; the duplicated valid-only cumulative counter was removed.
Both code files were fully read and the real outputs/native binding checked.
The nine text-inspection controls are not claimed as execution coverage.
The existing preflight/finalizer remain the only admission/validity owners.
No grader, prompt, key, answer, parser or scoring policy changed.

Core acknowledged the two excessive foreground waits and dropped its
unnecessary pair-alignment proposal. No hook/settings edit, duplicate watcher
or additional work was needed. This checkpoint includes only reviewed
segment3 evidence and supporting record changes, not the ongoing segment4+.
