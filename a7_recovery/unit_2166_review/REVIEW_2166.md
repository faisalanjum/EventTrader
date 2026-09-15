# A7 cause review — four named classes, independent, read-only

Core, 2026-09-14. Authorities used: A7_PREGRADING_WORK_ORDER.md Revision 234
section 6; exp5_scoring_spec_v3.md section 5 (af05e9c2…); the SERVED frozen
prompts; a7_grading_input_correction_2114.py (32e2f650…), which is the renderer
that produced the served G3/G2 text. CAUSE_REVIEW_PROGRESS_2165.md (ca577544…)
was read as history; no hypothesis of it was accepted without re-deriving it.
No model calls, no boundary commands, no edits outside this unit.

Section 6 gives exactly three dispositions: a served task that conflicts with
its authority is a TEST DEFECT and gets the smallest remedy; a model that
violated a sufficient task is a MODEL ERROR that stays in the score; an unclear
rule gets the Plan's rule_ambiguity exhibit and a required decision, never an
invented resolution.

## Authority chain established first

`reference_card()` builds every card from a GOLD row of the reviewed inventory,
looked up by exact row identity, and refuses unless that row carries its bound
quote (hash-checked). So a reference card IS the key carrying that claim.
The served G3 instruction block is byte-identical across all 30 batches
(b856edd4…), so a finding about it is a property of the task, not of a sample.

## Class 1 — G2 source-stated prior vs bare reported state (ORLY)

VERDICT: **real rule ambiguity remains. No code/prompt change justified.**

The served contract says: "Metric: keep apart a stated direction, differing
parts, an explicit flat, an ongoing condition with no direction, a
source-stated prior comparison, and a bare reported level", and elsewhere "A
change the source states differs from one merely derivable."

Population derived from the frozen inputs: 10 G2 records assert
driver_state="reported"; in 6 of them the key card itself carries a prior value,
so the source states a prior. Those six reached THREE different outcomes:

| question | key card values | G1a / G1b on driver_state | outcome |
|---|---|---|---|
| M70f663f593c28775 ORLY | [6447, 6265] | true / true (split on whole record) | unresolved |
| Mfdc3b99ab640f039 ORLY | [6447, 6265] | true / true (split on whole record) | unresolved |
| M02dd1d33369df31b | [1.73, 1.61] | true / false | unresolved |
| M0c5dd9bbeece43b0 | [1.73, 1.61] | false / false | unresolved |
| M31b20a4a0b7e5203 | [1.73, 1.61] | false / false | unresolved |
| M4e236380221db347 | [1.5, 2.0] | true / true (split on whole record) | unresolved |
| M4ea4d7f5cd26d81a | [-763352, -1370961] | true / true | CREDITED all-true |

The same structural situation - a bare "reported" state where the key card
carries a prior - was judged agreed-wrong twice, split three times, and
agreed-right once. The served rule names the distinction but never supplies the
criterion for when a prior COLUMN makes a claim a source-stated comparison
rather than context for a bare level, and the served prompt does not enumerate
the state vocabulary (by design: the grader judges meaning).

Honest limit: these six are not one claim - store count, EPS and a balance-sheet
deficit differ, so part of the spread may be real per-case difference. What is
established is that the shared pattern does not get a stable answer. That is
measured uncertainty plus an open rule question, NOT a proved test defect, and
under section 6 it is exactly what the rule_ambiguity exhibit exists for. I did
not invent a resolution.

## Class 2 — G3 key_miss where the key already carries the claim

VERDICT: **the model violated a sufficient task. No code/prompt change justified.**

Served definition: "key_miss: the produced record states a real claim of this
source that the reviewed set does not carry", with rule 3 "The `reference_cards`
identify reviewed claims" and rule 1 "Answer null if the evidence does not
settle it; null is a lawful answer and you must never guess." The governing spec
section 5 agrees: a genuine key miss is "a real fact the key lacks".

Measured over all 116 G3 questions: 100 agreed key_miss, 11 agreed duplicate,
3 agreed unsupported, 2 split. Of the 100 agreed key_miss:

- **90 have a reference card in their own event whose quote is BYTE-IDENTICAL to
  the asked record's own source sentence**, spread over 45 distinct sentences
  (not one repeated artifact; 10 are singletons).
- 10 have no such card; they are only 3 distinct claims (MCD $80m restructuring,
  YUM 377m/40m special g&a, DAL 85% travel survey) and belong to the existing
  source-only exclusion review, not here.

Stated at the strength the evidence carries: a card quoting the identical
sentence proves the key reviewed THAT SENTENCE. It does not by itself prove the
key carries the specific rendering the record asserts - one sentence can yield
several key rows, and the AZO event demonstrably has two cards from one
sentence. But that distinction does not rescue the label: where a hash-bound key
card quotes the very sentence, "the reviewed set does not carry this claim" is
NOT established by the served evidence, so rule 1 required null, not key_miss.
The served task is sufficient and consistent with its authority; the model
violated it, systematically, in 90 of 100 agreed labels.

## Class 3 — DAL MRO X59b3cb047c8dd0d9 called duplicate

VERDICT: **the model violated a sufficient task. No code/prompt change justified.**

Served rule 4: "Establish first that the asked record states what the source
states, field by field; only then can it be a duplicate of one of these
records." Bucket: duplicate is "the same claim as one of this event's comparison
records".

Source and key card: "the MRO revenue in the first quarter more than doubled
over the prior year to $380 million", card values [380]. Asked record and its
comparator O1 differ in EXACTLY two fields, level_high and level_low; every
other item field and every outer field is identical:

    asked  level_low = {value 380000000, scale_multiplier 1000000, evidence "million"}, unit m_usd
    O1     level_low = {value 380,       scale_multiplier 1000000, evidence "million"}, unit m_usd

Same multiplier, same scale wording, same unit, raw values a factor of 1e6
apart - a real quantity difference, not a scale-encoding equivalence. The
asked record therefore does not state what the source states, so rule 4's
precondition for duplicate fails. Not inferred from equal numbers: the numbers
are unequal.

Whole class derived, not sampled: all 11 agreed duplicates cite the same quote
as their comparator, and every one differs in at least one field. Exactly ONE -
this record - differs by a pure magnitude error. The other ten differ in token
spelling (segment:internationalsegment vs segment:international;
segment:usmarket vs segment:u_s_market), naming (vendor_concentration vs
vendor_purchase_concentration; share_repurchases vs share_repurchase),
unit_scale_evidence wording ("millions" vs "in millions", identical values), or
specificity where the comparator defaults to null (period dates, fiscal_year,
change_value, measurement_raw_spans). Those ten need per-case source reading and
I do not rule on them here; none carries a magnitude error.

## Class 4 — AAL Mb65ece4291c4b307 qualitative fuel recapture vs the CMG rule

VERDICT: **no defect, and the grading is correct. No code/prompt change justified.**

Two G2 records quote the SAME sentence - "…i think our recapture rate would be
in the 90s" - and carry the SAME reference card, whose values are [] (the key
states no number). They differ in exactly four fields:

| field | Mb65ece4291c4b307 (both lanes ALL TRUE) | Md2061d63bedc8f75 (both lanes record_matches_source FALSE) |
|---|---|---|
| level_low | null | {value 90, scale_multiplier 1} |
| level_shape_hint | null | "floor" |
| level_unit | null | "percent" |
| value_text | "in the 90s percent" | null |

The served contract says "The qualitative text field is numberless guidance and
is not a place for quantities" and "A point, an interval, a lower bound and an
upper bound each mean what the source states." The record that kept the cautious
wording numberless was accepted; the record that turned "in the 90s" into a
stated floor of 90 percent was rejected. That is the same rule applied in both
directions.

It also matches the CMG cautious-guidance pattern: Mb65ece4291c4b307 is
fact_type guidance with driver_state "unknown" and the source's own condition
clause preserved ("if fuel is still at the level with capacity reductions"),
exactly as the CMG bare guides retain lawful unknown movement and their
qualification. No exact bound was invented in either direction, and no cautious
answer was turned into a wrong one.

## What this review did NOT establish

No proved TEST defect in any of the four classes, so no remedy is proposed and
no correction is justified on this evidence. I did not rescore, persist, reroll,
change any Boolean, bucket or key row, run a model, or touch a source, harness
or prompt. The unresolved G2 questions are reported as measured uncertainty,
never as transport failure - the collection itself is complete and every lane
valid. Whether each individual credited judgment is semantically right remains
open and is Codex's to check.
