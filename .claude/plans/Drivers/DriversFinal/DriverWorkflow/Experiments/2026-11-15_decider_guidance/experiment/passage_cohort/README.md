# Six-call passage screen

Local `pplx-decider-v1.3:8bit`, full-call context, one unchanged question per stored prepared block or Q&A exchange. All six requests completed, 186 passages, 83,524 input tokens, six native sequences, 936.90 seconds (15 min 37 s total). Finished November 15, 2026 at 7:01:47 PM EST.

Reference: 57 passages labelled positive, 118 negative, 11 unadjudicated before the run. Labels come from the source readings and targeted clarification, not an independent blind key. These are passage-presence counts, not distinct facts or complete records. A repeated claim can occur in several passages.

| Cutoff | Retained positive passages | Filtered positive passages | Retained negative-labelled passages | Unadjudicated retained / filtered |
| --- | --- | --- | --- | --- |
| 0.5 | 48/57 | 9 | 4/118 | 4 / 7 |
| 0.25 | 52/57 | 5 | 10/118 | 5 / 6 |

## Source review of the five positive-labelled passages below 0.25

| Source / passage | What is at risk | Interpretation limit |
| --- | --- | --- |
| PAYX September / QA010 | No big ARPU increase expected from the Bill partnership | A specific worded outlook, but its required record period is unresolved. |
| PAYX March / QA003 | Conditional margin expansion as revenue grows | The forecast is explicit; metric association/representation still needs review. |
| PAYX March / QA016 | Integration costs excluded from adjusted operating margin; further margin outlook | Supporting measurement evidence, not a new numeric forecast by itself. |
| PAYX March / QA021 | Enterprise growth expected at or above peers prospectively | A worded relative forecast; the preceding 10% is actual performance. |
| CTAS March / QA004 | Debt/EBITDA expected to be 1.5 at closing | A repeated forecast also retained in prepared remarks; not an independently established missing distinct fact. |

At 0.5, four additional positive-labelled passages are filtered: the Cintas December standing growth target; Paychex September PEO outlook, expense-growth continuation and confirmation of the EPS raise. The last is a repeated statement, not confirmation of the analyst's numerical revision.

Negative-labelled disagreements need interpretation review, not an automatic claim that the model is wrong. For example, PAYX September QA004 contains vague performance-building language, and CTAS March PR003 supplies acquisition-closing timing useful to the leverage fact. Keep the frozen key and report these ambiguities explicitly; do not silently relabel after seeing model scores.

## Design consequence

Neither tested cutoff is a proved safe gate for complete guidance extraction. Lowering a cutoff just to fit these misses is not a generic solution. More importantly, full-call state does not repair choice menus that omit filtered sentences: Cintas December QA011 contains the start of the ERP question but scores about 0.15; the required answer is in QA012. Keep that question available to later evidence selection even when QA011 is not itself a forecast candidate.

Next bounded comparison: target each existing stored utterance with the same question and full-call context. The source reconstruction passes across all six calls (363 utterances). Begin with the complete PAYX March call, which has three low-scoring positive passages. This changes structural granularity only; no forecast-specific wording, parser, word list or answer-key input. Per-sentence targeting is a later alternative only if justified; do not add both layers.

This result tests only screening. O1–O4 remain open; no full-record, unseen-company or production claim. All raw requests, results, scores, source hashes and uncertain labels are retained here. Main strategy and rulebook unchanged.
