# Multi-axis Driver relocation — final research handoff

Date: 2026-07-13

## Status

The isolated research is complete. Nothing from this prototype was installed in the project.
All prototype code and outputs are under `/tmp`. Other processes changed the shared project while
this work ran, so do not describe the whole project as unchanged; the accurate statement is that
this work wrote only to `/tmp`.

## Goal in plain words

Given one known Driver fact — its name or quote, source, value, unit, and period — find the same
fact in another period without a person checking it. Multi-axis means the number describes two or
more company parts at once, such as product + geography.

## Root cause

The old path flattened separate XBRL coordinates into one vague name. It lost which label was the
row and which was the column. That is why a tag such as `OtherUSRegionsMember` could be read as
`All Other` instead of `U.S. Regions`.

The earlier 73% number was not a valid two-axis score: its bucket counted words in one member name,
not distinct XBRL axes. A later audit also found equal old/target values, leaked values, and inexact
old rows in the old benchmark. Do not use 73% as the baseline.

Early ABT, ACM, ADBE, ACMR, and ADM spot checks helped expose the flattening problem, but they are
not the final proof set. ACM's VIE example and ADBE were actually one-axis cases, and one ADM
top-eight anecdote was false. The held-out benchmark below replaces those anecdotes.

## Smallest general design that survived testing

1. Bind the known old fact once.
   - Keep the full concept QName, unit, exact period, and every separate `(axis, member)` pair.
   - In the old filing, bind the exact inline-XBRL fact and recover its printed row, aligned column,
     and safe section label.
   - The table grid uses only normal HTML rules: direct rows/cells plus `colspan` and `rowspan`.
   - Ignore hidden cells, earlier numeric data rows, and full-width titles.

2. Remove the old number before searching.
   - The old value is used only to prove that the lock hit the right old cell.
   - The reader does not receive the old value, old numeric row, target value, answer key, or cell
     coordinates.

3. Use two target lanes.
   - First: for 10-Q/10-K XBRL, match full concept + every axis/member + unit + exact target period.
     This is deterministic and needs no AI.
   - Second: only when exact XBRL is unavailable or the source is text, retrieve by the old printed
     words plus the separate facets. The reader must match all facets and the exact quarter.

4. Keep the text reader strict.
   - Printed row and semantic column are one address, not a bag of words.
   - A safe section is a tie-break, not a hard filter. If an exact section plus the whole address
     matches, it beats a longer different label that merely contains the same word. If that strict
     candidate cannot prove the whole address and period, retain the normal fallback.
   - Require a quarter marker and the target year in the selected candidate.
   - Require a verbatim quote containing the emitted number. Otherwise abstain.

This needs no company map, value-size hint, human review, or fuzzy merge.

## Two real failures that prove the fix

### AMRC — missing column

- Old vague address: row `Other`; bad nearby label `Integrated-PV`; member name
  `OtherUSRegionsMember`.
- Wrong blind pick: `All Other = 9,525`.
- Exact old grid: row `Other` × column `U.S. Regions`.
- Correct target: `674` thousand.
- After adding the aligned printed column and removing the prior data-row label, the fresh blind
  reader selected `674`.

### PHM — two similar tables

- Same filing and quarter contained:
  - `Home sale revenues:` → `West` → `1,016,977` (MD&A, narrower metric)
  - `Revenues:` → `West` → `1,018,160` (financial-statement note, exact old address)
- The first full rerun chose the first table because section was treated as optional context.
- The smallest fix is the exact whole-address tie-break. A fresh blind differential read chose
  candidate 3 and `1,018,160`, with no target value hint.
- A hard “exact section only” retrieval filter was rejected: development coverage fell from 97 to
  94. The final version adds only an `exact_section` signal and does not change candidate text or
  order.

## Real benchmark

### Large source pool

- 8,941,902 raw XBRL graph rows scanned.
- 120,130 eligible fact observations.
- 8,634 eligible series.
- 16,926 adjacent unequal pairs before balancing.
- 1,523 balanced two/three-facet pairs across 316 companies.
- 1,452 two-facet and 71 three-facet pairs.
- Company-held-out split: 1,227 development and 296 holdout pairs.

The locked FinalDesign axis catalog was used only to exclude known accounting/elimination axes when
building the benchmark. It is benchmark/design data, not a per-company relocation map.

### Deterministic XBRL lane

- 1,399 fully confirmed USD pairs across 301 companies kept the identical full concept + facets +
  unit between periods.
- Every target identity was unique, every old/target value differed, and all 1,399 target facts
  resolved by that identity: 1,399/1,399.
- This proves the stable-identity lane. It does not test renamed tags because this subset is selected
  for identity stability.

### Exact old printed address

- Development: 120 safe addresses from 136 attempts, across 120 companies.
- Holdout: 120 safe addresses from 128 attempts, across 58 companies.
- Total: 240 safe exact locks from 264 attempts; 24 ambiguous/hidden/mismatched cases safely rejected.
- The safe model payload has a printed column in 239/240. One date heading was conservatively
  removed because its day number collided with a short rounded old-value form.
- Two synthetic tests cover mixed `rowspan`/`colspan`, hidden headers, and a wide prior data row.

### Retrieval

- Development: the answer existed in 97 sources and stayed in candidates for 97/97.
- Held-out: the answer existed in 99 sources and stayed in candidates for 99/99.
- The one absent case was TSLA regulatory credits × automotive; exact XBRL still resolves it.
- The final section signal changed no candidate text, order, or truth case.

### Blind text fallback

Frozen set: 100 real cases, 58 companies not used in development, periods from 2023-03-31 through
2026-03-31, 98 two-facet and 2 three-facet cases.

- Full blind rerun after the column fix: 95 emitted, 94 correct, 5 abstained. AMRC was fixed; PHM was
  the only wrong pick.
- Differential blind check of the only choices affected by the whole-address tie-break fixed PHM
  and confirmed the BBIO same-value alternative. A separate audit confirmed the remaining choices
  were unchanged.
- Final: **95 correct / 95 emitted = 100% precision**.
- Recall: **95/100 = 95% overall**; **95/99 = 95.96% where the source candidate contains the answer**.
- Five abstentions remain: one source-absent TSLA case and four cases where the printed source did
  not safely prove the target year/cell. A fresh blind recovery pass kept all five abstentions.

This final score combines one full frozen-100 rerun with a fresh differential blind check for the
small set affected by the last generic tie-break. It is not a second full 100-case rerun.

The held-out set is realistic but narrow: 88/100 are revenue-like concepts, all are filing facts,
and identities are stable by construction. A finite test cannot prove universal 100% accuracy.

## Existing behavior and other sources

The new path was not installed, so it cannot directly regress the project. The saved regression
floors were also rerun read-only:

- Annual: 132 correct, 2 wrong, 8 abstain among 142 gradeable; 98.5% precision, 93.0% recall.
- Quarterly: 37 correct, 1 wrong, 2 abstain; 97.4% precision, 92.5% recall; zero YTD picks.
- Clean saved one-axis audit: 15/15.
- Clean saved zero-axis total audit: 10/11 with one safe abstain.
- Headline transcript: 7/7 emitted answers correct; recall is low because transcripts often do not
  state the exact number.

Real source transfers already present in the saved audit include filing → transcript for AA, AAPL,
and ADBE, and filing → release for AA plus two AEIS cases. These show that the visible-address reader
is source-neutral. They are small spot tests, not multi-axis certification across all source types.

## Generalization and the user's proposed input

The proposed input is almost enough:

`Driver name/quote + known source + known value + unit + known period`

The period and unit are necessary to avoid binding the same words to the wrong column. From that one
known fact, the system can build the exact address once and reuse it over company history:

`concept + separate facets + printed row/column/section + unit`

For XBRL filings, use deterministic identity. For releases, transcripts, and news, reuse the visible
address and strict evidence gates. If a source does not contain the number, no system can honestly
return it from that source; it should try another allowed source or abstain.

This is aligned with FinalDesign: the Driver stays a value-free class; period, slice, measurement,
unit, quote, and source belong to each DriverUpdate/fact. Multi-valued slices must keep every part.

## What not to port

- No per-company axis map. The old `abbv:KeyProductPortfolioAxis → product` style map is acceptable
  only as benchmark metadata and must stay out of the relocation engine.
- No naive `explicitMember` list loop in the existing Tier-1 path. The project state records that it
  lost 50/1,761 certified matches. Add the new multi-axis identity path without changing the working
  zero/one-axis ambiguity behavior until its companion resolver is tested.
- Do not use the `corrected_benchmark_v2/certified_reader` result as reader proof. Its batches expose
  old value/row fields. Its structural audits are useful; its reader claim is not blind.
- Do not claim the old numeral is absent from all target candidates. It can recur naturally. The
  correct claim is that non-candidate metadata contains no labeled old/target value or numeric row.
- Do not repeat the ADM top-eight/113 anecdote.

## Suggested production landing order

1. Preserve all current zero/one-axis behavior.
2. Add a separate full-facet address object and exact-XBRL-first resolver.
3. Add the small HTML grid extractor for exact old row/column/section.
4. Expose `exact_section` only as a reader tie-break; never filter candidates solely by it.
5. Keep quote, value, unit, period, and ambiguity gates deterministic.
6. Rerun all current floors, then the frozen multi-axis set.
7. Before broad rollout, add two new held-out sets: tag/member drift across years and multi-axis
   filing → release/transcript/news. These are the main untested claims.

## Main artifacts

- Pool builder: `/tmp/relocate_multi_axis.mrogHs/prototype/build_clean_pool.py`
- Pool summary: `/tmp/relocate_multi_axis.mrogHs/runs/clean_multi_axis/pool_summary.json`
- Exact address builder: `/tmp/relocate_multi_axis.mrogHs/prototype/build_exact_addresses.py`
- HTML cell extractor: `/tmp/cell_address_probe.WhbHsb/lock_row_extract.py`
- Grid tests: `/tmp/relocate_multi_axis.mrogHs/prototype/test_column_grid.py`
- Candidate builder: `/tmp/relocate_multi_axis.mrogHs/prototype/build_clean_candidates.py`
- Final grader: `/tmp/relocate_multi_axis.mrogHs/prototype/grade_clean_blind.py`
- Final score: `/tmp/relocate_multi_axis.mrogHs/runs/clean_multi_axis/blind_reader_final_grade.json`
- Independent regression/source audit: `/tmp/relocate_multi_axis.mrogHs/audits/nonregression_source_audit.md`

Final SHA-256 snapshots:

- cell extractor: `38690c7b5025660d7490c43eea099ff69f359a39b1a2b7bf8149235deea4996f`
- pool builder: `bf859d6536531c0ec3a11fa0ee3d97c46453dfdb2303b4a5d2b8de4555ef7115`
- exact-address builder: `b05421071f89166064bae69f909f0beec3d95d756f6bf0ac23895a8273b5dce7`
- candidate builder: `13e40313bbde63da04f54428aec330b07b4615a8a38c2989cf154f84817a1cf9`
- final grader: `9e379a3a3de239b3df207abd074128402f4cf4859bba70cc511e51d26ed5a74c`
- frozen truth: `e6372c9e38da4249a6c1cc5bf9381d16534b9eef9b7d5b73001df0d12f72ac97`
- final score: `d42719cb7910491e0cf58530ba8e1ee8ad834c1ce8955a88360f23d503c25ade`

Recompute these immediately before copying code. The project is a shared dirty workspace and its
current files must not be assumed to match the snapshots used here.
