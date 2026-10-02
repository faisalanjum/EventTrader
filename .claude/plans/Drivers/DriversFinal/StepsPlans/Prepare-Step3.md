# Prepare · Step 3 — Freeze checks and independent answers

**Status (2026-10-02, latest):** First bulk batch finished: six blind jobs, 17 targets
per model, 78 charged turns. Claude supplied PASS and an updated guide; all remaining
packets were refreshed before launch. Bulk progress: [RUN_STATUS.md](/home/faisal/prepare_work/step3_sample_20261002/bulk_20261002/RUN_STATUS.md). [Results and guide corrections](/home/faisal/prepare_work/step3_sample_20261002/bulk_20261002/HANDOFF.md).

**Latest owner decisions supersede earlier budgets below:** ceiling **2,000 turns**;
keep all 457 targets, including XML. Bundle whole small filings by format, at most
15 targets; isolate held-out filings. The two HTML+PDF filings each stay whole and
alone. Both models remain xhigh; 10–15 targets allow 25 turns, smaller jobs 20, one
attempt. [Bundle plan](/home/faisal/prepare_work/step3_sample_20261002/bulk_20261002/bundled/PLAN.md):
74 model jobs total; remaining jobs run in bounded waves. The owner permits one
OpenAI retry for bundle-007 after diagnosis if needed; preserve and charge both attempts. Report costs before further launch; Claude's check
must begin with `PASS` in `bulk_20261002/CLAUDE_FIRST_BATCH_CHECK.md`; `FIX` waits for correction and next `PASS`. Write `bulk_20261002/RUN_STATUS.md` at start and finish. The approved typical-day sample is built afterwards. XML participates
in the chosen converter tools, with no separate custom production XML parser.

**Goal:** write and verify the answer sheet from original filings before comparing
converters. Darden's `$10.67` followed by footnote `4` must never become `$10.674`.
Tool agreement and XBRL alone cannot check all untagged evidence.

Authority: [PrepareStep.md](../PrepareStep.md), Step 3, §4–5 and T1.
Keep code minimal and generic; named failures are test fixtures, never production rules.

## Inputs

- Frozen saved sources: **11,439 verified filings**, all 12 forms. No need to wait for
  the full download. Read saved files; any live database read stays brief, read-only
  and on minisforum2. This work made no new SEC requests.
- Preserve original hashes, filenames, publication/version evidence and source
  locations. News/call originals remain outside this SEC sample.
- Verify reused code part by part, including `m3_candidate_census.py` if used.

## Work, one part at a time

| # | Part | Deliverable / approval |
|---|---|---|
| 1 | Pick sources | Separate hard cases, hash-selected controls and final-test companies; freeze IDs, hashes, reasons, planned/achieved counts and gaps. **Claude checks; owner approves.** Results below. |
| 2 | Set minimums | **Approved below.** Choose cells against these floors; unmet minimum fails the job. |
| 3 | Agree the record | One original table beside its draft answers, plus a text/structure example. Use §4 source anchors and exact printed strings, not floats. Calibrate independently; agreement alone is insufficient. **Owner approves format.** |
| 4 | Write answers | Two independent labellers, blind to each other's answers and converter output. Check renderings when needed; resolve disputes from originals, retain real ambiguity. **Qualification and Phase 6 approval before bulk AI labelling/vision.** |
| 5 | Build the checker | One builder; independent checker. Real correct cases must pass; deleted/changed digits, cells, paragraphs, images/tags, swapped headers/order, joined footnotes and broken references must fail the intended check. |
| 6 | Freeze | Lock the resolved key, manifests, code/environment and commands before scoring converters. **Owner's final OK.** |

## What must be checked

- Cells: exact text, raw coordinates/spans, row and header path, printed period,
  unit/scale, sign, segment/basis and footnotes, each with original support.
- Documents: paragraph order, section boundaries, covers, images, tags and references.
  Include nested/merged/layout tables, single-digit values, hidden contexts, encoding,
  oversized content and distant references. Later information keeps its own date.
- Calibrate with AMG, Darden, Coty, CVS and available named regressions. AES and other
  missing verified originals remain open; never claim their regressions passed.
- XBRL/later filings are cross-checks, not answers. A shared parser is not an
  independent oracle. The coordinator's own answers need another person's check.
- Preserve byte/source-region anchors and resolver versions; converter-list positions
  alone are insufficient. Evidence stays unchanged; display cleanup is separate.
- Count `OK / NOT_READ / UNRESOLVED / FAILED` by source/layout, including omissions.
  Changed frozen input stops the affected job with `INPUT_MISMATCH`; never substitute.
- Keep final-test answers away from converter builders. Using a final-test case to
  fix code moves it into development; replace it before final scoring.
- T6/T7 need 20 contracts and 20 varied PDF/image sources. The shortlist has 24 each;
  these can overlap the cell key, but results stay separate. Image conversion is
  checked in Step 4; arrival in reading pieces is checked in Step 7.
- T1 uses code against the checked key; AI fact/cause extraction belongs to T4.
  This deliberately difficult sample cannot justify a database-wide accuracy bound.

## Minimums — approved by the owner (2026-10-02)

| Minimum | Why |
|---|---|
| 300 untagged cells | Existing plan requirement. |
| 60 percentages | Growth, margins and inequality signs need direct checks. |
| 40 non-percentage ratios/multiples | Conversion rates and covenants are poorly covered by later dollar tags. |
| 60 counts | Shares, locations and units; include small/single-digit values. |
| 60 distinct tables | Spread across layouts, rather than many easy cells in one table. |
| 40 distinct filings | Spread across issuers and sources; emphasize earnings releases/body disclosures. |

Categories do not double-count: percentages, non-percentage ratios/multiples and
counts are separate. Money, durations and other printed numbers fill the remaining
coverage. No per-table cap. Include the final-test set in every applicable category;
freeze its actual counts before labelling. These are coverage floors, not statistical
proof. No owner hand-labelling task is required.

## Labelling — owner approved a 2-file trial only (2026-10-02)

**Owner update after Claude's check (2026-10-02):** one fresh blind re-run at
**xhigh** for both models is approved. Same originals and 26 targets; no automatic
retry. Revised [TASK.md](/home/faisal/prepare_work/step3_sample_20261002/trial_20261002_xhigh/packet/TASK.md)
separates note markers, records range roles/partners and fixes all seven record
conventions. Each model must produce 26 correct records, checked independently
by Claude, before this calibration passes. Lower effort does not guarantee savings;
subscription-only execution and the existing budget conditions still apply.

The completed trial used **`claude-sonnet-5-5`, max** and **`gpt-6.1-sol`, max**;
its frozen records remain unchanged.
Both passed identity/availability checks without receiving source packets. Sonnet
uses Claude's Max login; OpenAI uses this session's agent runner. The installed
Codex CLI rejects that model ID under ChatGPT login, so do not use it for this trial.
Subscription only; no paid API or silent fallback.

Use identical, hashed original-backed packets: one table-heavy file and one
text/structure file. Neither labeller sees the other's answers, existing draft
answers or converter output. Claude's **separate checker session** sees labels only
after both are saved. Report elapsed time, turns, input/output tokens, unresolved
items and disagreements; do not invent usage numbers if unavailable.

Label agreed cells/structure, not every fact. The trial uses Darden's earnings
release and CVS's main 8-K: **18 cells across 6 tables, plus 8 structure targets**.
Both labellers receive the same frozen [packet](/home/faisal/prepare_work/step3_sample_20261002/trial_20261002/packet/manifest.json),
with no draft answers or checker output. Sonnet was configured for 20 turns per
attempt; OpenAI received that instruction. Sonnet needed one bounded retry; its
receipts report 21 and 23 turns. OpenAI runtime counters are unavailable. Neither
limit is a demonstrated bulk-budget control. Raw answers remain unchanged.

**Trial result:** 18/18 printed values agree; 14 cell records differ on other primary
fields, and one structure record differs on reference coverage. Differences are
not accuracy verdicts. [Trial report, time/usage and checker handoff](/home/faisal/prepare_work/step3_sample_20261002/trial_20261002/TRIAL_REPORT.md).

**Xhigh re-run:** both corrected the three footnote labels and three range records,
and captured the previously missed references. Sonnet took 7m00s / 20 reported turns;
OpenAI finished within a 9m07s observation window, with runtime usage unavailable.
Sonnet left units unknown in five cells; period/reference choices also differ.
**26/26 correctness is not yet certified.** [Re-run report and Claude handoff](/home/faisal/prepare_work/step3_sample_20261002/trial_20261002_xhigh/TRIAL_REPORT.md).

The trial sets packet limits and realistic cost. The typical-day run is already
approved conditionally below; the larger stress-key run still needs approval.
For the 137-source key alone, two first passes mean 274 jobs; the earlier 300–400
turn allowance is unmeasured, not an approved budget.

## Results: source selection approved by the owner after 3 swaps (2026-10-02)

**Owner decisions:** (1) approve the sample once the 3 unsupported "text fragmented across styled spans"
cases are replaced with genuinely fragmented files (Claude re-checks those 3);
(2) add a separate typical-day sample from the saved 1,016 rehearsal filings,
using proportional form quotas and the same fixed hash; propose size/cost first.

**Replacements completed:** both Deckers cases → AMH's policy exhibit and CVS's
merger exhibit; Silgan → Euronet's 10-K. Ordinary prose contains `do + c + um + e + nt`,
`S + tockhold + e + r`, and `ter + minals`, respectively. The other **134 files and
all 41 controls are unchanged**. [Exact files, hashes and byte locations](/home/faisal/prepare_work/step3_sample_20261002/replacement_evidence.json).

**137 source files from 132 filings / 117 primary issuers:** 72 development stress
files, 24 final-test stress files and 41 controls (one per available form/year).
All 12 forms, 2023–2026 and all 11 named sectors are covered; two files have unknown
sector. Formats: 116 HTML, 11 PDF and 10 XML.

| Filing type | Distinct filings |
|---|---:|
| 10-K | 19 |
| 10-K/A | 4 |
| 10-Q | 23 |
| 10-Q/A | 4 |
| 425 | 4 |
| 6-K | 2 |
| 8-K | 57 |
| 8-K/A | 4 |
| SC 14D9 | 1 |
| SC TO-I | 4 |
| SCHEDULE 13D | 3 |
| SCHEDULE 13D/A | 7 |

**Final-test companies (20):** AEP, ALKS, AUPH, BA, BXP, CBOE, CI, CLSK, DLR, EEFT, F, G, GSHD, MTDR, MYGN, NXST, PI, PRI, SPG, YELP.
Primary issuers and exact file hashes do not overlap the other sets; corporate-family
separation is not established. Structural qualification has seen these sources;
converter builders must not tune on them. This is not a claim that no past bot has
seen their content.

[Every hard case, one-line reasons and company names](/home/faisal/prepare_work/step3_sample_20261002/SAMPLE_REVIEW.md) ·
[All files as CSV](/home/faisal/prepare_work/step3_sample_20261002/case_catalog.csv) ·
[Frozen selection/inputs](/home/faisal/prepare_work/step3_sample_20261002/REVIEW_SNAPSHOT.json).

Hard cases are deliberately ranked by source difficulty; controls use the documented
fixed hash within form/year. Seven form/year combinations have no saved sources at
the cutoff. Some named regression originals remain unavailable in this snapshot;
they are listed in the review. Contract/image sets are qualified source candidates,
not completed T6/T7 accuracy tests.

**Draft table example:** [original table beside answer record](/home/faisal/prepare_work/step3_sample_20261002/worked_example.html).
Olive Garden's **Q3 2026 segment profit is printed `$320.0`, with `($ in millions)`**.
The record points separately to the value, row, metric header, year and unit line.
It is an illustration awaiting independent checking, not an approved key.

**Text/structure example:** CVS's main 8-K contains guidance and its explanation;
Darden's raised footnote is separate from the preceding number. Their original byte
locations are in [source checks](/home/faisal/prepare_work/step3_sample_20261002/known_source_checks.json).

**Checks:** Claude's [original review](/home/faisal/prepare_work/step3_sample_20261002/CLAUDE_CHECK.md)
reproduced 41/41 controls, verified 137/137 source files and supported 66/69 inspected
case reasons; it identified the three replaced cases. Revision 2 again verifies all
137 hashes, unchanged controls, repeatable selection and no company overlap,
including co-filers. **Claude's replacement recheck (~08:50): passed.** AMH, CVS and Euronet split words confirmed in the originals (own unpacker, fingerprints, exports match); controls 41/41 and final-test separation re-verified; the 50 typical-day picks recomputed identically. One typical-day filing (0001085146-25-006037) names final-test company Impinj: treat it as final-test only. [Details](/home/faisal/prepare_work/step3_sample_20261002/CLAUDE_CHECK.md).


**Claude's trial check (2026-10-02 ~10:15):** values, positions, labels' cells and headers are 18/18 correct for both; structure text, kinds and headings 8/8 for both. Two mistakes are shared by both labellers: footnote markers glued into 3 row labels, and range ends ($10.57 to $10.67) not recorded in 3 cells. Sonnet missed 2 of 3 references in S05. Seven conventions need settling in TASK.md before bulk work. [Details](/home/faisal/prepare_work/step3_sample_20261002/trial_20261002/CLAUDE_TRIAL_CHECK.md).


**Claude's xhigh re-run check (2026-10-02 ~11:05):** both models now get every value, position, label, footnote and range right, and 8/8 structure records. Not yet 26/26 under v2: OpenAI 15/18 cells, Sonnet 9/18. The gaps are mainly rule wording (currency in financial statements, comparison base, unit evidence choice, href). Proposed v3 fixes and one more short re-run. [Details](/home/faisal/prepare_work/step3_sample_20261002/trial_20261002_xhigh/CLAUDE_TRIAL_CHECK.md).


**Rules review (owner 2026-10-02: think every rule through, no doubt, then one quick re-run):** round 1 by Claude, grounded in the 137 sampled originals: [RULES_REVIEW_R1_CLAUDE.md](/home/faisal/prepare_work/step3_sample_20261002/RULES_REVIEW_R1_CLAUDE.md). Covers non-HTML sources, target selection, values, footnotes, headers, units, periods, ranges, basis, hidden content, structure and process, plus 3 owner questions. Codex reviews next (round 2), then TASK.md v3 and the re-run.
Claude's full draft of the labellers' guide (step-by-step, tested on real cells from the sample): [TASK_V3_DRAFT_CLAUDE.md](/home/faisal/prepare_work/step3_sample_20261002/TASK_V3_DRAFT_CLAUDE.md).

## Typical-day sample — approved, conditional on the trial

**Owner decisions (2026-10-02 ~08:55):** the 50-filing sample is approved, with a labelling budget of up to about **561 AI turns** (Codex's estimate). It is labelled with the same method once the 2-file trial has validated that method. Filing **0001085146-25-006037** (13D/A naming final-test company Impinj) stays in the sample but is **final-test only**: its answers are never shown to converter builders.

**Approved 50 filings:** 35 × 8-K, 9 × 10-Q, 3 × 10-K, and one each of 8-K/A,
425 and SCHEDULE 13D/A. Allocate by rehearsal form shares with largest-remainder
rounding; select within each form by the existing hash. No difficulty filter.

All 1,016 rehearsal package hashes match the saved snapshot. Its 8-K share is
69.59% versus 69.60% in the full list. It contains no SC 14D9 or SC TO-I; the
stress panel covers those. This is a coarse historical-mix check, not proof of
future daily accuracy. Report results separately; 41 balanced controls also remain
separate.

The 50 filings contain **187 main/exhibit files**: 374 first-pass jobs for two
labellers. The trial shows that jobs can take many turns, so the earlier
**412–561-turn estimate is unsupported**. The approved 561-turn ceiling remains;
establish observable usage and a plan that fits it before starting.
Five files overlap the existing sample: reuse suitable labels, withhold them from
converter tuning, and never count them as independent extra evidence.
[Reproducible proposal and exact IDs](/home/faisal/prepare_work/step3_sample_20261002/typical_day_proposal.json).
The run must fit the approved limit; stop and report if measured usage would
exceed it. Never substitute paid API access or a different model.

**Next:** Claude independently checks all 26 frozen xhigh records per model against
v2 TASK and originals, including agreements and remaining unit/period/reference
choices. No further model run, converter comparison or bulk labelling has started.
