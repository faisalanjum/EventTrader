# Existing-utterance targeting: do not adopt from this test

Whole PAYX March 2026 call; identical broad definition and question as the completed passage screen. The only intended changes are target boundaries, their tags and question membership. Prepared blocks and Q&A entries come from the already-normalized native snapshot; no new splitter, finance keywords, known names or reference labels enter the request. Exact reconstruction passed for all six source snapshots (363 utterances across 186 passages).

| | Passage targets | Stored utterance targets |
| --- | ---: | ---: |
| Questions | 38 | 73 |
| Input tokens | 17,800 | 20,268 |
| Native sequences | 1 | 1 |
| Time | 200.33 s | 230.31 s |
| Positive-labelled parent passages retained at .5 | 9/12 | 8/12 |
| Positive-labelled parent passages retained at .25 | 9/12 | 9/12 |
| Negative-labelled parent passages retained at .25 | 2/23 | 1/23 |

Three reference passages remain unadjudicated. These labels are development references, not an independent gold key. A parent is retained when any child meets the cutoff; the maximum child score is not a calibrated parent probability. Neither result measures complete-record extraction.

The same low-scoring statements remained below .25: conditional margin outlook (QA003), adjusted-margin exclusion/future margin context (QA016), and prospective enterprise growth relative to peers (QA021). The unchanged-EPS exchange (QA027) also fell below .5 under utterance targeting. Source review confirms that the latter depends on question/answer context, which stayed visible; extra text boundaries alone did not resolve the judgment.

Decision: reject this replacement for now. It provided no positive-coverage gain and cost more in the one matched source. Do not run the other five merely to validate a change that has not shown the required benefit. The next structural comparison is direct sentence targeting with the full call retained, using the existing native sentence boundaries. It must replace the coarse gate, not add another recovery layer. No O1–O4 repair was reopened, no source/production change was made, and the main strategy remains unapproved.
