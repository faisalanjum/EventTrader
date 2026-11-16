# Procedure review — current evidence, not a finished extractor

Current Driver rules govern. The goal remains complete source-backed guidance records using the local Decider and existing code, without another writer. Keeping a passage, copying an exact phrase, or holding a difficult claim does not satisfy complete extraction.

## What the existing results justify

| Part | Keep / change | Evidence and limit |
| --- | --- | --- |
| Preparation | Preserve the full ordered source and original positions. Exclude only verified speaker-header metadata from numeric questions. | `metadata_filter/`: all 9,167 selected transcripts checked; 22.33% fewer numeric questions, every speech digit preserved. Model grouping still needs validation. |
| Guidance screening | Use the same broad definition for numeric and worded guidance, including qualifications. Keep all source text available after screening. | `passage_cohort/`: 48/57 positive-labelled passages retained at .5; 52/57 at .25, across six calls. This is a development reference, not distinct-fact recall. Neither cutoff proves a safe filter. |
| Numeric candidates | Code supplies exact digit-bearing occurrences. The model decides their roles and which occurrences form one forecast. | Literal-plus-tag questions worked better than tags alone. Shared bound definitions recovered the tested ordinary points/ranges. Dates, old values, revisions and current forecasts remain separate. Unsupported spellings and centre/tolerance forms are not solved. |
| Worded candidates | Retain the guidance sentence and its source context. Do not treat it as a completed value or assume one forecast per sentence. | Worded extraction and separation remain open (O1/O3). No word/count/ordinal repair layer. |
| Evidence and measure | Required evidence may be anywhere in the source. Select the actual measure and its association; preserve one continuous exact quote. | Full context helps, but the tested measure menus offered only retained prepared sentences or the local exchange. A model cannot choose an unavailable sentence. O2 remains open even where the correct option was present. |
| Field questions | Use source-backed evidence and verified fiscal metadata; keep raw probabilities. Copy already-owned numeric occurrences with code. | Evidence-based field tests are promising, but the final assembled six proposals are still incomplete in four cases. Separate Locate copies are unnecessary for values code already owns. Conditions and qualifiers remain open (O4). |
| Normalization | Reuse existing exact number scaling and the period resolver where inputs meet the current rules. | `native_period_controls.json`: seven controls passed. Month arithmetic is not a verified week-based calendar. Do not adopt the legacy lookup cascade without reconciling its cache/filing precedence with 3.43. |
| Final result | Account for every candidate and source; require all supported meaning before calling a record complete. | No calibrated acceptance threshold, complete-source record score or unseen full-pipeline pass exists. Experimental incomplete outcomes are not a production retry policy. |

## Necessary simplifications, not new machinery

- Remove redundant value copying after code already owns model-selected exact occurrences.
- Ask identical-bound expressions once, retaining their original occurrences. This is not identity merging: one amount can support several distinct meanings.
- Put shared definitions in the input once; use short complete questions with visible targets.
- Do not add an exclusive sentence-role menu: a sentence can state a forecast, its revision and an assumption together.
- Do not supply existing Driver names to blind discovery. Final name matching remains outside this extraction trial; identifying what the forecast measures does not.
- Do not force periods from the fixture's three fiscal years or infer a comparison, growth basis, unit, condition or target from plausibility.

## Current decision

The old measure-first, Locate-heavy strategy is not supported by the experiments. The value/role/evidence direction has better component evidence, but is not yet a coherent complete extractor. No additional copying repair is justified merely to make the same six records pass.

The completed six-call screen assessment finds lost relevant statements at both tested cutoffs. Do not fix this with company phrases or example-specific exceptions. The cheaper structural alternative was tested first: existing stored utterances, unchanged wording and whole-call context. On PAYX March it retained the same 9/12 positive-labelled passages at .25, fell from 9/12 to 8/12 at .5, and took 230.31s versus 200.33s. Do not adopt it or expand this failed comparison merely to accumulate runs. `turn_screen/` preserves all requests/results and exact reconstructions across the six sources.

The bounded direct-sentence comparison is complete for PAYX March: 673 questions, 729.94s, 60,073 input tokens and two native sequences. At .5 it retained 19/22 frozen positive sentence controls; at .25, 21/22. Eight negative controls were correctly excluded, but additional selected sentences included actual results. At .25 all 12 positive-labelled parents were retained, while the S483 integration-cost exclusion was still missed (.0629). Parent retention therefore cannot stand in for complete claim/evidence detection. All 104 selections at .25 have a source-review outcome in `sentence_screen/`; these post-result categories are not independent gold or complete records.

Sentence targeting has a measured parent-coverage/cost tradeoff, not a safe sentence-discard rule or a complete extraction result. Do not lower the cutoff to fit the missed example or add a fourth screening repair. Preserve the complete source for evidence selection. The main record requirements and four open classes remain; no new copying/measure repair chain is justified.

Still required: complete field/interpretation reference, one reproducible procedure producing actual records, all four open classes, calendar breadth, calibrated acceptance and untouched-source validation. The main strategy, rulebook, runtime and database remain unchanged.
