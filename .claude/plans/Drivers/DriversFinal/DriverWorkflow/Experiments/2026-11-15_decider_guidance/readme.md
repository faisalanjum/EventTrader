# Guidance extraction experiments

**Goal:** find management's forecasts in earnings calls, preserve their exact evidence, and turn them into correct DriverUpdates without a larger model.

**Current result:** the final six-call run retained sentences for **79/79 checked claims**, but produced **0 complete, accepted records**. Finding a claim worked much better than collecting and interpreting every detail. **This is not a finished extractor.**

- [Folder map and complete code guide](code_guide.md)
- [Original one-page stopping memo](experiment/OWNER_REVIEW.md)
- [Final run totals](experiment/frozen_six/run_summary.json) · [claim-by-claim review](experiment/frozen_six/review_counts.json)

## What worked, and was it 100%?

**“100%” below means every checked example in that particular test—not every transcript, every repeated run, or a guarantee.** These are development tests, mostly six calls from two companies. The reference was already exposed during development; it is not an independent final answer key. A sentence, a claim, a field and a complete record are different counting units.

| Function | Observed result | Worked every checked time? What remains missing? |
| --- | --- | --- |
| Find sentences containing numeric **and worded** guidance | Final run retained at least one guidance-bearing sentence for **79/79 confirmed claims**, across all six calls. [Check](functional_checks.json) | **Yes for these 79 claims.** Both forms are included; this is not a separate accuracy certification for each form, nor proof that all guidance in the calls was found. |
| Find **all supporting wording**, including qualifications and confirmations | Final Paychex March answers retained **20/22 positive sentence controls (90.9%)** and excluded **8/8 negative controls**. The earlier standalone test retained **21/22**, not 22/22. [Final check](functional_checks.json) · [earlier test](experiment/sentence_screen/README.md) | **No.** Final screening missed an adjusted-margin exclusion and an EPS confirmation. Main-claim coverage does not establish complete evidence coverage. |
| Keep exact raw text and character positions | **408/408 selected sentences** match their saved transcript; **122/122 later quote/copied-field spans** passed exact-text checks. [Sentence check](functional_checks.json) · [run checks](experiment/frozen_six/integrity.json) | **Yes for exact copying.** This does not prove the selected text supports the record, contains everything needed, or matches the publisher's original. |
| Remove unrelated text | An earlier review of all **104 selected sentences** found 36 guidance-related, 49 background/past/current operations, and 19 ambiguous outlook/intention. [Review](experiment/sentence_screen/README.md) | **No.** Some past results were retained. Typical precision across companies is unknown; final-run selections have not all been relevance-labelled. |
| Screen whole prepared blocks or Q&A exchanges | At cutoff .25, **52/57 positive passages retained**, with 10/118 negative-labelled passages also retained. [Test](experiment/passage_cohort/README.md) | **No.** This earlier coarse screen missed five positive passages; splitting into speaker turns gave no coverage gain in the one matched call. |
| Avoid treating speaker timestamps as financial numbers | Read-only audit covered **441,843 utterances / 9,167 transcripts**; all spoken digits were preserved. Verified headers removed 441,846 unnecessary numeric questions; 79 unmatched headers stayed unchanged. [Audit](experiment/metadata_filter/README.md) | **Yes for the audited preservation checks.** It does not establish guidance accuracy. Five final-run snapshots lacked speaker metadata, so 304 timestamp questions remained there. |
| Decide whether a number is a forecast, an actual result, or something else | Literal text plus occurrence tag passed **25/25 role controls**: 10 positives and 15 negatives. Tag alone passed 16/25. [Test](experiment/main_path/binding_scored.json) | **Yes in that small component test.** Broader final-run role errors remain; this is not a general 100% result. |
| Choose the numbers forming a range | **25/25 endpoint checks**, including non-forecast controls. [Test](experiment/main_path/numeric_bounds_shared_scored.json) | **Yes in that component test.** Correct endpoints do not prove correct range meaning, sign or assembly; those failed elsewhere. |
| Read unit and scale from correctly supplied evidence | **12/12 unit choices**, 32.81 seconds. [Test](experiment/main_path/unit_quote_scored.json) | **Yes in this test.** The evidence was already selected and reviewed; automatic evidence collection remains unresolved. |
| Read form, broad subject/scope, period, unit/scale, sign, movement and duration/instant | **42/42 highest-probability choices** on six expressions with reviewed evidence, 112.08 seconds. Matched whole-call input: **40/42**. [Test and limits](experiment/quote_fields/README.md) | **Yes for those reviewed-evidence choices.** These are not 42 records or six complete records; confidence cutoffs, detailed business segments and independent calendar discovery were not validated. |
| Match a forecast to its supporting assumption or exclusion | **86/88 settled sentence-pair checks** correct: all 12 positives found, two false positives; 20 other pairs remained unsettled. [Test](experiment/main_path/support_sentence_scored.json) | **No.** Finding a related sentence is not yet correct, complete condition extraction. |
| Identify what the number measures and assemble its full evidence | Sentence-pointer test matched **11/15 preselected reference locations**; some alternatives may be valid. Short-copy tests also returned confidently wrong measure text. [Pointer test](experiment/main_path/measure_pointer_scored.json) · [final reviews](experiment/frozen_six/proposal_reviews.json) | **No.** For example, finding “7.6” without the organic-growth meaning and Q4 period does not make a usable record. |
| Finish records for worded forecasts | Worded claims were retained as sentences, but the frozen procedure has **no completed worded-value path**. [Procedure](experiment/OWNER_REVIEW.md) | **Not implemented completely.** This is not proof that the model can never do it. Earlier word/count/ordinal probes are experimental, not a working adopted solution. |
| Normalize numbers and resolve fiscal dates | Existing helpers handle ordinary values and supplied exact dates. Final assembly reversed one negative range; the calendar choices use a May-31 fixture for these two companies. [Number helper](experiment/proposal_numbers.py) · [calendar checks](experiment/calendar_support/) | **Not generally verified.** Calendar acquisition/cache reliability and broader number assembly remain open. Calendar metadata mismatches are review flags, not automatically errors. |
| Produce a complete, accepted record | **0 complete / 79 held / 0 missed** checked claims. Two proposals had correct reviewed content but unnecessary holds. One wrong proposal escaped automatic holds and was caught in source review. [Final review](experiment/frozen_six/review_counts.json) | **No.** Some parts work; the full procedure does not yet reliably combine them. |
| Locate literal spans after the punctuation fix—Claude's separate short-text test | **56/60 spans**, including **28/28 numeric spans**; the four misses were names. [Supplied evidence](external_review/readme.md) | **Yes for those 28 numeric spans; no overall.** This is not full-call guidance extraction or an independently repeated test here. |

### Why 79/79 and 20/22 are both true

The 79 count asks whether a checked claim was retained somewhere. The 22 controls ask about particular statements, including supporting exclusions and repeated confirmations. A claim can survive while one of its necessary qualifications is missed. The archived final answers were compared with the same 30 control texts; all text identities matched. This additional check used saved answers, with **no new model calls**.

### How much extra text is kept?

The final run kept **408 of 3,338 sentences (12.2%)**. That is the fraction retained, **not accuracy**. In the separate 104-sentence review, 34.6% were guidance-related, 47.1% background/past/current operations and 18.3% ambiguous. Background can help interpret a forecast, so these categories do not give a clean “junk percentage” or a typical rate across transcripts.

The saved output includes the full transcript, selected raw sentences, exact start/end positions, model scores and numeric-role decisions. It has already undergone selection/classification; it is **not yet a set of completed guidance records**.

## Final unchanged run

Local model: `pplx-decider-v1.3:8bit`. November 15, 2026, **7:51:59–10:48:51 PM EST**; total **2h 56m 52s**, roughly 24–39 minutes per call.

| Call | Checked claims | Complete | Held | Missed |
| --- | ---: | ---: | ---: | ---: |
| Cintas, September 24, 2025 | 12 | 0 | 12 | 0 |
| Cintas, December 18, 2025 | 14 | 0 | 14 | 0 |
| Cintas, March 25, 2026 | 14 | 0 | 14 | 0 |
| Paychex, September 30, 2025 | 14 | 0 | 14 | 0 |
| Paychex, December 19, 2025 | 12 | 0 | 12 | 0 |
| Paychex, March 25, 2026 | 13 | 0 | 13 | 0 |
| **Total** | **79** | **0** | **79** | **0** |

**Complete:** correct fields and evidence, with no unresolved hold. **Held:** retained but unfinished, uncertain or blocked. **Missed:** a confirmed reference claim was not retained. The 23 other reference entries are listed separately and excluded from this denominator. The run produced 45 numeric proposals, including four duplicates; these are not 45 complete facts.

The most useful demonstrated parts to reuse and test further are exact sentence preservation, verified speaker-header filtering, explicit number-role questions, endpoint choices, and field questions on correct evidence. They have **not** been proved to work perfectly together. The [stopping memo](experiment/OWNER_REVIEW.md) separates owner choices from model failures and unfinished code.

## Archive status

Everything is inside this one dated folder: **644 copied files**, including tested code, prompts, raw results, logs, reviews, six source snapshots and supporting project code/rules. The original experiment/review/snapshot set contains 634 files; 10 additional project snapshots preserve dependencies and the rulebook. Two dependency snapshots match the final run's recorded hashes; the others are labelled archive-time copies. Only 66 generated cache files were omitted. Originals were retained. [Manifest](archive_manifest.json) · [archive verification](archive_verification.json).

**Final-round preservation check:** all 132 files in `experiment/frozen_six/` are present, including all **40 requests and 40 responses / 5,183 questions**. All **18 recorded fingerprints** match: five code files, six inputs, six references and the configuration. All **135 saved Python files** are documented in the code guide. The known missing fixtures belong to Claude's separate earlier test, not this final run.

New documentation and saved-result checks sit outside the unchanged experiment. Earlier reports retain their original wording and intermediate results; use this page and the final-run files for the latest result. Scripts retain historical absolute paths and may call the model or overwrite old outputs: **this is an evidence archive, not a portable production runner**. See the [code guide and reuse limits](code_guide.md). No experiments were resumed to create this archive.
