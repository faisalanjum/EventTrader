# Ten source questions, checked independently

Core 5ae9b86b, 2026-09-15 UTC. Read-only. No model call, no rerun, no
code/prompt/key/grade edit, no label overwritten, nothing staged. I re-measured
your addendum `882d8715…`, the native score `656c18bd…` and the selection
`11076803…` before using any of them.

**Headline: your three dispositions hold, and none of the seven newly collected
G3 extras establishes a fact absent from the key — zero of seven.** One
disposition needs a qualification, not a correction.

## 0. Your correction to my progress helper is right

`collection_progress_2173.py` added `(kind, segment)` pairs in `launched_runs()`
and counted receipt files in `scheduled`, then reported both under `lanes_*`
names. With multi-lane segments that is 20 where the answer is 24. It also
accumulated `problems` and `retry` across finalizations with no removal once a
retry succeeded, so a lane whose attempt 2 was valid still showed retry-eligible
with its attempt-1 problem. Both are my bugs. The standing-outcome fields were
keyed on `(lane, attempt)` and were right, so the numbers I reported to you -
24 required, 24 usable, 0 invalid, 0 exhausted, 0 waiting, 38 of 38 covered, 20
preserved runs, 26 calls - are unaffected. I have not touched or rerun your
fixed helper.

## 1. The three source dispositions

### M8624b63494238990 — AGREE, and I can make it stronger

I compared the approved gold fact and the produced fact **recursively, field by
field**. The complete difference is three fields a produced record never carries
at all: `ambiguity_note`, `du_worthy`, `gold_extra`. `fact_type`, the entire
`item`, `part_ref`, `occurrence_in_part` and `per_x` are equal.

So the produced record asserts exactly what the approved key asserts. A
`record_matches_source: false` on it cannot be a reader defect without
simultaneously condemning the key. **Grading-model limitation. The measured flag
stands as measured; I overwrite nothing.**

### Ma31af1665347b9ec — AGREE on the cause, with one qualification

The cause is confirmed against live law, quoted: **FINAL_DESIGN line 90,
NAME-10** — *"a reporting company's own measured segment, product, geography,
customer group, sales channel, or owned entity goes to the slice, not the
name."* `digital` is the company's own measured sales channel. The key puts it
in `channel:digital` with the name `system_sales_mix`; the produced record puts
it in the name (`digital_mix`) and leaves the population EMPTY. That is a real
producer defect on name and population, and it is a metric, so the empty-action
scope correction does not touch it.

Your §6.1 citation is exact — **line 207: "No number → no unit resolution."** I
checked the whole key for facts that contradict it: three numberless key facts do
carry a `level_unit`, and all three are growth facts, which **OD-11, line 208**
explicitly permits (*"A numberless GROWTH fact may take its unit from source
framing"*). No contradiction.

**The qualification.** The gold here is not numberless. It carries
`level_high = 60`, `level_shape_hint = ceiling`, `unit_scale_evidence = "%"`,
`level_unit = percent` — "nearly 60%" encoded as a ceiling at 60. The produced
record stores no number, no unit and no `value_text`. And `value_text` is
**guidance-only** (line 244), so a *metric* has no lawful field left to carry a
vague quantity once it declines the numeric slots. So the produced record's
choice is not simply "cautious representation": measured against the key it
carries the stated quantity nowhere. Whether that is lawful caution or lost
precision is **exactly the open question you raise for Md2061d63bedc8f75, seen
from the other side** — there the producer stored a bound and the key stayed
qualitative; here the key stored a bound and the producer stayed silent. Your
addendum treats them as unrelated. I would keep your cause as written and drop
the sentence that settles the numeric slots as lawful caution.

### Md2061d63bedc8f75 — AGREE it is unresolved

FINAL_DESIGN fixes both halves and joins neither. Line 244 makes `value_text`
guidance-only and numberless-only and says it *rejects stored numeric values*;
line 238 makes `floor = low only` a self-describing shape. So for a guidance
fact both encodings are individually lawful, and no live clause says which one a
**vague** band requires. That is a rule gap, not a producer defect and not a
grader defect.

Your proposed §7.1 clarification is the right remedy. **Recommend it cover both
directions**, because Ma31af1665347b9ec is the mirror case and a one-sided
sentence would leave that one open.

## 2. The seven newly collected G3 extras

Checked against the full approved key for each source — fact type, state, level
numbers, unit, shape, baseline, population and period — not shared text.

**Six of the seven correspond to an approved key fact that states the same
claim.** For each, exactly one key fact matches on type, state and both level
numbers, and **that fact's own reference card was served in the very prompt that
answered `key_miss`**:

| question | key fact | its served card name | label |
|---|---|---|---|
| X99d7bc16850a9dde | g6 `aircraft_purchase_option` | "option to purchase up to an additional 30 of the same aircraft" | key_miss |
| Xe10aa94910fc4e7a | g6 (same) | same | key_miss |
| X6eea70137b9a2e63 | g6 `net_debt` | "Adjusted net debt" | key_miss |
| X73357410ba2d97a2 | g6 (same) | same | key_miss |
| X24756096af610d6d | g2 `restaurant_closure_impairment` | "Impairment due to restaurant closures3" | key_miss |
| Xa0f9de09f3c55112 | g0 `asset_impairment` | "Goodwill and intangible asset impairments" | key_miss |

The last is the sharpest: the produced record's own driver name is
`goodwill_and_intangible_asset_impairment` and the card in front of the grader
is named *Goodwill and intangible asset impairments*, same 171, same type, same
state. `key_miss` means *"a real claim of this source that the reviewed set does
not carry"*. The reviewed set carries it, and its card was on the page.

**So these are "an existing key fact represented differently", not key
omissions.** They differ from their key fact mainly in the driver NAME - and for
Xa0f9de09f3c55112 also in population (empty where the key carries Best Buy
Health) and in an added prior-year comparison against the table's dash, which is
the disposition you already hold open.

**One matching failure is being counted twice.** All four distinct gold facts
above appear in my own 185-row recall-miss trace, each with the same two
reasons: `agreed_selection_not_credited` and `multi_candidate_selection`. The
readers AGREED the gold fact matched a produced row; the UNION edge law refused
credit because the produced row had degree greater than one — the same gate you
reproduced for ULTA. That single event then records as a recall miss on the gold
side and, because the produced row stays unmatched, reappears as a `key_miss` on
the extra side. It is one cause, not two problems, and it is not a key omission.

**Two of the seven are also internal duplicate pairs.** The aircraft pair differs
in exactly one field, `driver_name`; the net_debt pair in exactly one field,
`period_start_date`. Neither twin was served to the other: a G3 question's
`other_records` is the MATCHED comparator pool, and two unmatched extras never
see each other, so the `duplicate` bucket cannot fire on extra-versus-extra
duplication by construction. Stated as an observation about the frontier, not a
request for a change.

**The seventh — X56415b76439cd6be — is the disagreement, and I read it as
`unsupported`.** The source says *"Recent corporate survey results indicate 85
percent of respondents expect their corporate travel spend will increase or stay
the same in the June quarter."* The produced record stores 85 percent as the
**level of `travel_spend`** with `driver_state: reported`. 85 percent is the
share of survey RESPONDENTS, not a level of travel spend — the same shape as the
Habit 79-percent error already in your causes table. It is also an outside
survey's expectation about a future quarter, not the company's own measured
metric. No approved key fact states the same claim, and none should. Lane A's
`unsupported` is the source-supported reading; lane B's `key_miss` is not. **The
disagreement stands as measured and I supply no replacement grade.**

## 3. What follows, and what does not

Proven defect: one — the name/population error in Ma31af1665347b9ec, against
NAME-10. Rule ambiguity: one — Md2061d63bedc8f75, and its mirror inside
Ma31af1665347b9ec. Grading-model limitation: M8624b63494238990, plus the six
`key_miss` labels that a served card refutes. Producer defect on an extra: one —
X56415b76439cd6be.

**No new missing-key fact is established by any of the ten**, which agrees with
your position. All six agreed `key_miss` labels and the one disagreement stand
unchanged as raw measured outcomes. Nothing here is a replacement grade, a new
scorer category, a key correction or a reason for another call.

## Files

| File | What it is |
|---|---|
| REVIEW_2174.md | this review |
| EVIDENCE_2174.json | all ten questions with exact identities, the recursive field differences, the same-claim key facts, whether their card was served, and the recall-miss reasons |
| build_evidence_2174.py | the read-only derivation; it pins the score, selection and your addendum and refuses if the regenerated G3 ids are not the selection |
