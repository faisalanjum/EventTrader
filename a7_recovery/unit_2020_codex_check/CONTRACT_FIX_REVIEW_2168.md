# Two bounded grading-instruction corrections

Codex, 2026-09-15 UTC. Implementation and focused regression complete;
independent affected-population review and native preparation remain open.
No new AI call, key change, changed score or production edit.

## Why these changes are required

The controlling FINAL_DESIGN.md SHA-256 is
4218d73abe6b98ef2ecd325aef8b5e49985101b122e457b39784dee677f32a0b.

1. Section 5.2 gives an omitted population different meanings by lane:
   consolidated whole-company for metric/guidance/surprise; no applicable
   part for an action. The old grading contract said empty only for whole
   company without that distinction. The correction preserves the obligation
   to supply a source-stated applicable action part; it does not excuse every
   empty action population or prescribe a verdict for an existing example.
2. Section 7.1 / DU-15 chooses the source's headline comparison first, with
   prior-year winning only a tie. The old grading contract said prior-year
   wins whenever both prior-year and sequential comparisons are stated.
   The correction restores headline priority, not a preferred example answer.

The metric-state clause remains unchanged: the complete served contract
already distinguishes a source-stated prior comparison from a bare reported
level and requires signed direction. Lack of a more explicit sentence is a
clarity lead, not proof that repeating valid judgments is necessary. No
word-list, company exception or code-based meaning rule was added.

## Small implementation and preserved history

a7_grading_contract_2168.py
23c36532b0629dc4a76a5ee34a0dcf9dbd9eaca6b8c3e57134d8a6b29fcaeba4
changes the two model-facing clauses and explicitly pins the new version.
It delegates records, context, grouping, reply shape and all unchanged rules
to a7_grading_input_correction_2114.py, still byte-identical at
32e2f650f56cb77b20c89199bc8cf120181dbc7ff92bdd60014d7abc95a16a2d.
The historical owner is required to reproduce saved evidence; it is not
obsolete code to delete. No copy of its 250-line implementation was made.

Batch preparation converts rule prefixes on checked in-memory copies so the
existing frozen batch owner receives its own format. It restores the new
prefix and version on the output. No persisted packet, raw reply or old
grading verdict is relabelled. The native preparation interface remains the
existing a7_correction_candidate_2118 owner with its V and CORRECTED_RULES
inputs temporarily bound to this version, using the existing scoped-binding
mechanism. That actual candidate/consumer connection is not yet proved here.

## Actual verification

The first test setup lacked the scorer binding; that setup failure was
corrected and is not counted as reproducing a product defect. With the real
scorer bound, the historical renderer fails all six baseline assertions in
0.22s: both missing rule distinctions in G2/G3 and unchanged packet output.
After implementation, those six pass. The final test file is
test_grading_contract_2168.py
7e77a1a5d9be1b4f85c21c567ecae41be1712f4b4668fa0c866d4f7fa8e8acf8.

Its 23 cases include both single/batch paths, unchanged evidence and question
identities, unfamiliar source/menu input, eight wrong-version/digest/rules/
historical-packet controls, preserved duplicate-question refusal, changed
base-owner refusal, unsupported-kind refusal and four actual clause-removal
mutations. Each negative family has a real positive control. These verify
instructions and binding, not whether an AI follows them correctly.

Focused affected tests: **77 passed in 0.61s, exit 0**.
Full existing affected regression plus the new file:
**262 passed, 29 subtests passed in 3.03s, exit 0** (exec30285 complete).
The exact full command is preserved in CONTRACT_REGRESSION_COMMAND_2168.sh.
No successful model call was repeated.

## Checklist after this pass

| Requirement | Status / remaining proof |
|---|---|
| Generality | Verified for the two general source rules; no input-specific decisions or configurable business semantics. |
| Complete relevant workflow | Unit/shared regression passes; new native candidate/consumer connection and changed-task frontier still open. |
| Duplication / organization | Original renderer and preparer remain the sole owners of their behavior; this version owns only two corrected clauses. Historical reproduction preserved. |
| Simplicity | No new scorer, provider framework, source lookup, output schema, model retry policy or production change. |
| Verification | Test-first, positive/negative and mutation checks above. Core2169 independently reviews necessity, code and the full minimal affected task population. Fresh grading, if required, needs a frozen frontier and ceiling first. |

The native score656c18bd and traceb3a759b5 remain unchanged. Current source
review data, including FINAL_SCORE_CAUSES_2168.md, is not an alternate score
and does not replace the required qualified independent grading evidence.
