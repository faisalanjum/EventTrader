# Whole-source sentence comparison — 2026-11-15

Local `pplx-decider-v1.3:8bit`, PAYX March 2026 source, 673 sentence questions with the whole call visible. The model received no reference labels or expected values. Native pysbd spans preserve exact source positions. The request also changed tags and instruction layout, so this is not a single-variable test of chunk size.

Completed at **7:26:40 PM EST** in **12m10s**, with 60,073 input tokens and two native sequences. The previous same-call passage screen took 3m20s and 17,800 tokens.

| Measure | Cutoff .5 | Cutoff .25 |
| --- | ---: | ---: |
| Frozen positive sentence controls retained | 19/22 | 21/22 |
| Frozen negative sentence controls excluded | 8/8 | 8/8 |
| Sentences selected from all 673 | 43 | 104 |
| Positive-labelled parent passages retained | 9/12 | 12/12 |

The controls are source-derived development checks, not independent or complete gold. They include confirmations, qualifications and repetitions, not 22 distinct records.

The remaining .25 miss is S483: integration-related costs are excluded from adjusted margins. Its score is .0629. Other outlook sentences retain the same parent passage, which is why 12/12 parent retention still does not mean complete evidence detection. At .5 the conditional margin outlook S199 and EPS confirmation S652 are also filtered.

All 104 selected sentences were reviewed. Root's post-result categories: 36 guidance-related, 49 context/past/current operations rather than a current forecast, 19 ambiguous outlook/intention. Context can be useful evidence; these counts are not a precision score. Some selections clearly describe past results (S044, S358, S644), despite all eight negative controls passing. Analyst wording also appears and still requires management confirmation. Native segmentation includes fragments, so a sentence is not automatically a complete fact or quote.

Keep the measured coverage/cost tradeoff and the limitation. Do not fit a lower cutoff, add another repair layer, or describe the selected sentences as complete guidance records. No production code, main strategy, rulebook or database was changed.

Files: frozen `*_request.json` and `*_reference.json`; raw `*_result.json`; verified `*_scores.json`; all-selection `*_source_review.json`. Runners are `../sentence_screen_check.py` and `../score_sentence_screen.py`.
