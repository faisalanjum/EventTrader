# Verified A7 grading repair checkpoint — 2026-09-13

This checkpoint preserves the completed grading-input, question-replacement
and duplicate-accounting repairs. It is NOT an approved new answer key, a
fresh grading run, a corrected final score, A7 PASS or production software.
All 382 original answers and the published baseline remain unchanged.

## Completed checklist

| Requirement | Evidence and limit |
|---|---|
| General rules, not example fixes | One shared field contract, reversible menu display and the existing matched-pair inventory. Empty and sparse valid populations work; missing/tampered evidence refuses. No company-specific semantic branch. |
| Complete affected workflow | All 306 meaning questions and 117 extra-fact questions render from real bound inputs; all 400 complete script variants fit the existing limit. The actual consumer verifies original and correction evidence and removes old credit when a replacement remains unresolved. |
| One owner per behavior | Existing matcher, parser, completion, source-card and scoring owners retained. One explicit matched view; one correction-subset boundary; no replacement scorer or signature validator. |
| Simplicity | The last renderer change removes one unnecessary empty-dict rejection. No extra response field, matching scheme, input truncation, model reroll or production component was added. |
| Verification | Current focused suite: 85 passed in 1.96 seconds, exit 0. Native rules/consumer/mutation suite: 2 + 26 + 10 passed, raw and combined exit 0. Historical affected regression: 559 + 139 passed, 2 explicitly historical skips; all 19 module exits 0. |

Current code identities: renderer 32e2f650, revision dd708431, preparation
50f9298c, duplicate counter 375cc483. Full hashes are in the publication
manifest. Native stdout is 218111deb363e28b1377352a9b526496d2141094985634643aef32c0d21d920b.
Real input proof is 4e3adcd02dcb8b037ba70fbd5e7efa80efce0a2540e451087b8cd352ce0dc9da;
independent byte/pool comparison is 0262dbc8c29db3afc6a5a215f2bcdb18fbe1c00a23961a2703c2fa370b1c3696.
The counter-only real replay f9345f36 changes only the two audited counters;
the original scores, semantic judgments and both failing decisions survive.

The 85-test command was:

```sh
env PYTHONDONTWRITEBYTECODE=1 /home/faisal/EventMarketDB/venv/bin/python3 -m pytest -q -p no:cacheprovider a7_recovery/unit_2020_codex_check/test_grading_input_correction_2114.py a7_recovery/unit_2020_codex_check/test_grading_revision_2115.py a7_recovery/unit_2020_codex_check/test_grading_contract_gaps_2118.py a7_recovery/unit_2020_codex_check/test_duplicate_accounting_2116.py
```

Other exact commands and input bindings are retained in
INPUT_CHECK_AND_RUN_COMMANDS_2122.txt. That comparison also needs its retained
prior input-fit output, codex_inputfit2119_a. Historical snapshots are evidence,
not alternate active implementations. The original historical suite is not
misrepresented as testing these new behaviors.

## Key handoff: evidence gathered, not declared complete

The new no-call proof `codex_keyreuse2123_a` reconstructs all 413 identity
questions in all 96 event/arm prompts, byte-compares every prompt and binding
with its frozen original, and revalidates both full saved meaning/extra
completions through their existing consumer. All 33 key-source hashes are
retained. Report cce187e23262708ba05e419368d49054304a2fdadfe796e2111909aad94e6847;
raw exit 0. The two source-review leads account for six existing event/arm
groups and 31 identity questions, NOT a newly approved call population.

Read owners: G.live_key/gold_by_event/questions/event_packet,
B._lifecycle/_resolutions_from/_verdict_maps_from/reference_card,
R.populations and the prepared-run/reference-inventory bindings. Existing
saved roots must remain tied to their original context. A different key
hash does not by itself justify new AI calls; an unchanged integer index
does not by itself justify transferring a saved judgment either.

Do not implement a speculative key-reuse framework before the two blind
source reviews establish an actual change. Once a new independently signed
key exists, compare its full affected event inputs and mechanical populations
against this baseline and reuse only judgments whose bindings still hold.
New or changed questions use the existing collection and consumer owners.
No source/key conclusion, changed-key proof or corrective call is approved by
this diagnostic.

Still open: Core's two-source post-signature preparation and independent
source decisions; any required new-key/old-grading handoff; the bounded
corrective grading; final score/cause report; and the END-only offline
local-model setup check. No A8 or later step is authorized.
