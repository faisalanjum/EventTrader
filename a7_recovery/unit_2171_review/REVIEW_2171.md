# The carried null-change selection: class, boundary and split, checked independently

Core 5ae9b86b, 2026-09-15 UTC. Read-only. No model call, no scoring or native
rerun, no code/prompt/key/grade edit, nothing staged. Every published file
elsewhere is untouched.

## The short answer

Your 23 are neither excessive nor incomplete. I re-derived the class from the
saved records rather than reading it off your file, judged all 22 distinct
records myself, and disagree with none of them. **The additional population is
23 carried G2 questions, it does not overlap the accepted 15, and the combined
frontier is 38 distinct questions.**

## 1. The rule, and why the corrected text is the only one the authority allows

FINAL_DESIGN line 239 states it twice. `Leave change_value=null when it could
merely be derived from a closed shape (derive at read).` And, for the stored
case, `it is stored ONLY when the source states a non-derivable delta AND its
arithmetic sign is determinable`. So a delta that the source STATES but that is
still derivable from the two stored operands belongs in neither text's
`change_value`.

The served difference is exactly one sentence. The old prompt has `A change the
source states differs from one merely derivable.` The corrected renderer adds
`Leave change_value null when it could merely be derived from a closed shape;
derive at read time.` Read as a grader:

| source states a delta? | both operands closed? | OLD | CORRECTED | task |
|---|---|---|---|---|
| no | yes | nothing stated, so null is right | explicitly null | **same** |
| yes | yes | this change IS stated, so the omission reads as wrong | derivable, so null is required | **moved** |
| either | no | no closed shape to derive from | precondition never holds | **same** |

That is your split, reached from the rule rather than from your list.

## 2. The class, re-derived

All 228 carried G2 tasks, by the saved produced record's own shapes:

| level | comparison | change stored | questions |
|---|---|---|---|
| point | **point** | **no** | **37** |
| point | none | no | 115 |
| none | none | yes | 24 |
| none | none | no | 22 |
| point | none | yes | 18 |
| floor | none | no | 6 |
| ceiling | none | no | 4 |
| ceiling | none | yes | 1 |
| range | none | no | 1 |

My 37 are exactly your 37 - same identities, every leg/gold/produced binding
matching the candidate, and every `fact` in your file byte-identical to the
saved produced record. 22 distinct records, all carried, none inside the
corrected 82.

## 3. The boundary, proved rather than counted

**Every one of the other 191 carried tasks stores no comparison operand at
all.** Line 239 derives a change at read as `level_low - comparison_low`, so
without a comparison there is no closed shape to derive from and the sentence's
precondition can never hold. This is not "the other 191 happen not to match" -
it is that the rule cannot reach them. The check asserts the property, not the
number, so a future record with a comparison operand outside the class would
fail it rather than pass quietly.

Three adjacent doors, closed with measurements:

* **0** carried records store a change while holding both closed operands - so
  there is no mirror-image missed class on the stored side.
* **0** carried guidance records store a `change_value` at all, so the
  renderer's other change sentence - percent-only guidance keeps its growth
  basis in `level_unit` - reaches no carried task.
* **0** carried records omit `driver_state`; the contract requires it. The
  renderer's third sentence therefore has no omission side, so the oversight you
  found here cannot have a twin there.
* **6** carried records set `change_unit` with a null `change_value`. All six
  are `percent_sequential` with no level and no comparison, all six are outside
  the class, and four are already in the 2170 baseline frontier as unaffected. A
  lone unit is still an assertion, but this sentence does not govern it.

## 4. The split, judged record by record

I read each of the 22 distinct records against its own source claim and asked
one question: does the source state a numeric delta OF THIS CLAIM. 12 records
yes, 10 records no; 23 questions and 14 questions. **0 disagreements with you.**

The four distinctions you asked me to hold apart all appear in the data and all
land where you put them:

* **a delta of this claim vs percentages elsewhere in a shared table** - the
  AAL table gives the Regional FTE row its own `5.9 %` beside Mainline's `3.9 %`
  (changed), while Best Buy's impairment row states `171` and a dash and the
  table's `% change` rows belong to revenue and comparable sales (unchanged).
* **an approximate or rounded delta** - AZO's `approximately 85%` against
  `approximately 86%` states two levels and no delta (unchanged), while the
  rounded percentages in the changed rows are deltas OF that row.
* **a direction without a number** - Chipotle's `a decrease from 24.8%` and
  Ulta's `decreased to 38.1% compared to 38.2%` state no delta (unchanged).
* **already lawful under both** - the four Best Buy online-mix rows state four
  LEVELS and no delta at all.

**This selection is not score shopping, and that is worth stating plainly.** Of
the 23 changed questions, **22 currently score true on every aspect** and only
one, M6d9dd25a44c4125e, carries a false aspect. Re-asking them can lower the
result at least as easily as raise it. Three of the 14 you excluded do carry
prior false aspects, so negatives were not swept in either.

## 5. Overlap with the accepted 15

**None of the 23 is among the accepted 15**, so the combined frontier is 38
distinct questions. The CLASS touches the 15 at exactly one question -
Mde7d5e39712de0c7, Best Buy's impairment - and that one is `unchanged_task` for
this sentence and already in the 15 through the empty-action scope clause. It
needs one call, not two.

## 6. Two things verified rather than accepted

* All **61** corrective G3 renderings carry the corrected sentence, so your
  instruction not to reopen the 116 G3 tasks for it is correct on the bytes.
* The original **71** G2 and **16** G3 prompts carry it **0** times, so every
  one of the 228 carried G2 tasks really was judged without it.

## 7. What this does not establish

That any of the 23 will answer differently, or better - nothing was called, and
I supply no verdict for any of them. That the 191 or the 14 are correctly
judged; unchanged means this sentence does not move their required answer. Your
native caller proof, your 290-plus-29 regression and your 28 native cases - I
read the live bytes of what I cite and ran none of your tests. And no reading
here authorizes turning M6d9dd25a44c4125e's negative into a positive.

## Files

| File | What it is |
|---|---|
| REVIEW_2171.md | this review |
| NULL_DELTA_BOUNDARY_2171.json | the shape census, all 37 identities with my own decision beside yours, the boundary and adjacent-door measurements, the prior-verdict mix and the overlap |
| check_null_delta_boundary_2171.py | the read-only check; pins your review, the selection and the 2169 loader, and refuses if the class, the reviewed records or the identities do not coincide |
