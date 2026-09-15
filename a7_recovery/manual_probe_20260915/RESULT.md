# Two direct Sonnet readings: mixed result, not an A7 pass

Completed by Codex, 2026-09-15. Both new readings correctly identified the
$171 million charge as belonging to Best Buy Health. The first was still not
a usable complete answer; the second passed the existing code checks, with
one source-interpretation uncertainty retained below. No official grade changed.

## What was actually tested

One selected, previously failed target: goodwill and intangible asset
impairments in Best Buy source 0000764478-25-000057, item #045.
Codex personally read the original instructions and complete source, selected
the case, froze the direct message, checked delivery, and reviewed both replies.
Core operated only the existing subscription connection and saved evidence.
The A7 experiment runner and automatic graders did not generate these answers.

Both fresh Sonnet child conversations received the SAME original 76,464 UTF-8
bytes: all instructions, 99 menu entries, all four ordered source parts and
the exact sole target item. No shortening, added clarification, answer key,
old result, failure hint or first reply entered either new user message.
Prompt SHA256: 566b676c1e617604554af14a76a1be93d6e5cbeff1e21dd2e6a70de0e9b0bf2b.
Both original child inputs independently equal this same prompt.

These were two separate NEW child conversations under the existing Core parent,
not two replacement top-level Core processes. Each has a distinct native
workflow and child id, null initial parent-message link, exactly one user
message, actual claude-sonnet-5, high effort in the executed call, zero tools,
attempt 1 and end_turn completion. Two model calls, zero model retries.
The second reused cached INPUT tokens; it did not receive the first answer.
The normal runtime also attaches a session reference. I inspected it: the
reference differs from the old run and is identical across the two new runs;
it contains no task text or answers. Thus the TASK prompt is byte-identical,
not every runtime metadata byte. High effort is proved from the executed
options, not a returned effort field (the child does not provide one).
The parent tool result at 08:51:02 UTC independently confirms the pre-call
output limit, unchanged agent profile and subscription billing guard.

## Actual results, checked against the source and supplied instructions

| Check | Fresh reading 1 | Fresh reading 2 |
|---|---|---|
| Completed raw reply | Yes, 104.966 seconds | Yes, 156.229 seconds |
| Correct event, four required reply fields, valid schema and exact source binding | Yes | Yes |
| $171 million, impairment event, completed, FY2026 Q3 | Correct | Correct |
| Best Buy Health business preserved | Yes | Yes |
| Distinct records returned | 2: quarter and year-to-date versions of the same charge | 1 |
| Existing code's no-write result | Both parked: missing start dates | One would be accepted |
| Abstentions / continuity proposals | 0 / 0 | 0 / 0 |
| Prior-year table dash | Interpreted as 0 | Interpreted as 0 |

The full source explicitly attributes the third-quarter/first-nine-month
impairments to Best Buy Health. The $171 million appears in both columns
because this is the same charge, not two different impairment events.
Reading 1's extra year-to-date record violates the supplied one-target task's
restriction on additional records: neither a required home/surprise sibling
nor a growth-basis split is involved. The code independently parks both rows
because they give an end date without a start date. The end date itself is
source-correct; do not misdescribe it as an invented date. The original prompt
is less explicit than later date clarifications, which were NOT supplied here.

Reading 2 keeps the one charge, its correct business, correct amount/scale,
point shape and fiscal quarter/year. It introduces no extra target or rename.
The existing public no-write route accepts it, resolving the quarter to
2025-08-03 through 2025-11-01. This proves code compatibility, not automatic
semantic approval of every assertion.

Both readings also store a prior-year comparison of zero where the table
prints a dash. The approved key deliberately leaves that comparison unset.
The original instructions require source-stated comparisons but do not
explicitly settle this table-dash convention. Key disagreement alone is not
proof of a false fact: retain this narrow interpretation uncertainty rather
than invent a rule, declare it correct, or rerun until a preferred answer appears.
The core charge and Health attribution are independently supported either way.

The provisional compound name preserves the same target meaning. No spelling
comparison against the key or new style objection is used as a failure reason.
All omitted optional fields were examined: no per-unit basis, guidance,
surprise, condition, favorability proof, measurement flavor or rename is
required for this ordinary impairment action. Missing numeric change is
appropriate; a derivable change is not newly asserted.

## What this tells us

The originally missing business attribution is NOT inevitable: both new
readings got it, and one original reading already had it. Original P2 omitted
Health; original P1 had Health but was parked for an incomplete date range.
Those old raw answers normalize to their existing scored records exactly.
Nothing in this check shows source context being lost during delivery.

Direct delivery did NOT make the whole task consistently perfect: one new
answer still duplicates the event and fails the date requirements, while the
other is mechanically usable but retains the dash interpretation question.
This single selected known case is not a representative accuracy estimate,
a replacement final exam, a stability vote, or permission to change A7's score.

## Evidence and limits

- Reading 1: workflow wf_f3b650fd-615, child a7902350b9f66265c;
  raw reply SHA256 2c6881708c882bba0e947564c60643638091f42b85191f144505944ad7209367.
- Reading 2: workflow wf_199f0418-b48, child ad4665f8f9c351717;
  raw reply SHA256 20c2931446f541c196eb8e93b34b6061e492c0f080082e61dcd1a91f5381671c.
- INDEPENDENT_EVIDENCE_CHECK.json checks exact state/script/prompt/transcript
  bindings and every native evidence copy against its original bytes.
- MECHANICAL_CHECK_1.json and MECHANICAL_CHECK_2.json reuse the existing parser,
  menu restoration, source normalizer, schema and public no-write route.
  No real database was opened or written. A dry-run row saying written means
  WOULD write if enabled, never that this diagnostic wrote to a database.
- Native workflow token counters show 45,939 each but omit final output growth;
  use the saved final assistant usage records, not that counter as full usage.
  Final usage: 45,937 input tokens each (including cached input), with 9,856
  and 14,217 output tokens respectively; thinking is already inside output.
- One initial Workflow rejected the recovery script path BEFORE any model call.
  The byte-identical script was placed in the runtime's allowed scratch path;
  the durable original and both executed state copies match. No permission
  setting, model, prompt or route was substituted.
- Codex's first optional route probe passed extra input metadata and was
  refused before I/O; the next route succeeded but its tuple-keyed index map
  needed a list representation for the diagnostic JSON report. These were
  probe/report setup errors, not Sonnet or grading-code defects. The checked
  runs use the exact public event shape and preserve those earlier audit files.

The old 382 replies, keys, official score, production code and branch HEAD
remain unchanged. No grader call or full-regression rerun was needed: no
grading behavior changed. This two-call task is finished; no further call,
correction, A8 or later work is started by this diagnostic.
