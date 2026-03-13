# Extraction Validation Campaign — 2026-03-13

Purpose: live validation of the generic extraction pipeline via real transcript guidance runs.

Status: completed

## Goal

Answer these questions with evidence:

1. Does the live transcript guidance pipeline run end-to-end on varied real sources?
2. Does it produce semantically correct guidance items with correct IDs, periods, basis, units, provenance, enrichment, and graph writes?
3. Do runtime artifacts, logs, and Obsidian captures agree with the graph state?
4. What defects, regressions, or confidence limits remain?

## Non-Goals

1. Proving perfection in the absolute mathematical sense.
2. Proving future extraction types will be perfect without their own prompts/scripts.
3. Proving upstream transcript ingestion never truncates or misstructures content.

## Verification Matrix

Each transcript run should be checked across all of these surfaces:

1. Trigger surface
   - Candidate exists and is selectable
   - Pre-run extraction state is known
   - Queueing mode and source identity are correct

2. Runtime surface
   - Worker accepts payload
   - Primary pass runs
   - Enrichment pass runs when expected
   - Result file status is completed
   - No retries or dead-letter unless justified

3. Prompt/protocol surface
   - 8-slot load path matches expected type/asset/pass
   - Warmup caches are created
   - Transcript content fetched through the intended Bash path
   - Output/result protocol is respected

4. Graph-write surface
   - `guidance_status` transitions correctly
   - GuidanceUpdate count matches agent report
   - Items have correct slot identity
   - Period nodes and edges are correct
   - Concept/member links are plausible
   - Idempotent rerun behavior is sane

5. Semantic extraction surface
   - No backward-looking items mistakenly extracted
   - Quantitative anchors are required where the spec requires them
   - Basis handling is correct
   - Segment decomposition is correct
   - Conditions vs standalone-item boundary is correct
   - Quote prefix/provenance is correct

6. Observability surface
   - Worker logs reflect actual execution
   - Obsidian extraction note is created and coherent
   - Repo logs and graph state do not disagree

## Confidence Model

Confidence is graded, not absolute:

1. Infra confidence: job dispatch, worker, status, logging
2. Protocol confidence: pass orchestration, temp/result files, hooks
3. Semantic confidence: extraction correctness for tested transcripts
4. Generalization confidence: likely portability of the architecture to other extraction types

Absolute perfection cannot be proven from 4-5 runs. The best we can do is:

1. Maximize variety
2. Audit all artifacts
3. Identify failure modes not covered by the sample

## Planned Transcript Variety

Target mix:

1. Rich formal guidance transcript
2. Transcript with meaningful Q&A enrichment
3. Transcript with segment-specific guidance
4. Transcript with low/no guidance
5. Transcript with a known edge shape if available
   - unusual FYE
   - fallback content structure
   - basis-switching complexity

## Candidate Ledger

Selected candidates:

1. `AVGO_2026-03-04T17.00`
   - reason: standard rich transcript, fresh source, non-December FYE, good baseline for normal primary + enrichment behavior
   - structure: prepared remarks + 14 QA exchanges

2. `FNKO_2026-03-12T16.30`
   - reason: explicit `HAS_QA_SECTION` fallback case
   - structure: prepared remarks + `QuestionAnswer` fallback, no `QAExchange`

3. `S_2026-03-12T16.30`
   - reason: prepared-remarks-absent edge case
   - structure: no prepared remarks, 14 QA exchanges

4. `HCAT_2026-03-12T17.00`
   - reason: likely low-guidance / sparse-primary case
   - structure: 488-char prepared remarks + 12 QA exchanges

5. Rerun candidate: `AVGO_2026-03-04T17.00`
   - reason: idempotency and rerun behavior after first successful write

Inventory snapshot before runs:

1. `AVGO_2026-03-04T17.00` -> `existing_items=0`, `guidance_status=NULL`
2. `FNKO_2026-03-12T16.30` -> `existing_items=0`, `guidance_status=NULL`
3. `S_2026-03-12T16.30` -> `existing_items=0`, `guidance_status=NULL`
4. `HCAT_2026-03-12T17.00` -> `existing_items=0`, `guidance_status=NULL`
5. `ADBE_2026-03-12T17.00` -> `existing_items=8`, `guidance_status=NULL` (excluded from first-pass set; existing manual write evidence already present)

## Run Ledger

To be filled per transcript:

1. Source ID
2. Reason selected
3. Pre-run state
4. Runtime observations
5. Graph observations
6. Semantic observations
7. Obsidian/log observations
8. Verdict

### 1. `AVGO_2026-03-04T17.00`

1. Source ID
   - `AVGO_2026-03-04T17.00`

2. Reason selected
   - baseline rich transcript with prepared remarks plus 14 QA exchanges
   - non-December FYE
   - expected primary + enrichment behavior

3. Pre-run state
   - `guidance_status=NULL`
   - existing `GuidanceUpdate` count for source: `0`
   - prepared remarks present and substantial

4. Runtime observations
   - queued via `trigger-extract.py` in `mode=write`
   - worker dequeued expected payload and invoked `/extract AVGO transcript AVGO_2026-03-04T17.00 TYPE=guidance MODE=write`
   - warmup produced `312` concepts, `196` members, `425` member-map keys
   - transcript fetch succeeded through warmup Bash path; temp file size `46,572` bytes
   - primary pass dry-run validated `11/11` items; write created `11`, updated `0`, errors `0`
   - primary write emitted member-resolution warning: `resolved 2 items` from precomputed map
   - enrichment pass first dry-run validated only `3/4`; `AI Revenue` failed with `100000.0 with 'billion' looks pre-scaled`
   - enrichment agent inspected its own JSON, corrected `AI Revenue` from pre-scaled `100000` to raw `100` with `unit_raw="billion"`, reran dry-run, then wrote successfully
   - enrichment write created `1`, updated `3`, errors `0`
   - final worker result: `status=completed`, `guidance_status=completed`, wall time about `364s`

5. Graph observations
   - final graph state: `guidance_status='completed'`
   - final `GuidanceUpdate` count from this source: `12`
   - two `MAPS_TO_MEMBER` edges present for Broadcom members corresponding to `Infrastructure Software` and `Semiconductor Solutions`
   - `GuidancePeriod` nodes in live graph carry `id/u_id/start_date/end_date`; no extra label field observed
   - created baseline items matched expected Q2/FY27 guidance set, including one enrichment-created long-term item: `AI Networking Revenue Share` for `gp_LT`
   - important defect candidate: persisted node `gu:AVGO_2026-03-04T17.00:diluted_share_count:gp_2026-05-31_2026-05-31:non_gaap:total` has `canonical_unit='m_usd'` with `low=mid=high=4940.0`, despite quote clearly saying `4.94 billion shares`

6. Semantic observations
   - transcript text directly supports extracted Q2 values:
     - consolidated revenue `~$22B`
     - semiconductor revenue `$14.8B`
     - AI semiconductor revenue `$10.7B`
     - infrastructure software revenue `$7.2B`
     - adjusted EBITDA `68%`
     - gross margin `77%`
     - non-GAAP tax rate `16.5%`
     - diluted share count `4.94 billion shares`
   - Q&A enrichment behavior looked semantically appropriate:
     - `33% to 40%` AI networking share became long-term structural range
     - AI revenue FY2027 item was enriched with chip-only scope plus `~10 gigawatts`, `~$20B per gigawatt`, `6 customers`
     - gross-margin item received Q&A conditions rather than duplicate new slot
   - semantic defect candidate remains the diluted-share unit handling:
     - pod-local source JSON captured `unit_raw="billion"` instead of a shares-bearing unit
     - persisted graph value ended up looking like money, not count

7. Obsidian/log observations
   - worker logs and graph state agree on completion and counts
   - pod-local extraction note exists at `/home/faisal/Obsidian/EventTrader/Earnings/earnings-analysis/pipeline/extractions/2026-03-13_extraction_AVGO_2026-03-04T17.00.md`
   - host Obsidian vault did **not** receive the AVGO note
   - deployment root cause appears to be in `k8s/processing/extraction-worker.yaml`: pod mounts `/home/faisal` as `emptyDir` and does not mount the host Obsidian vault path, so capture artifacts are written only inside the pod filesystem
   - pod-local note reported `Diluted Share Count` as `count`, which disagrees with the persisted graph row; observability and graph are therefore not fully consistent

8. Verdict
   - end-to-end extraction succeeded
   - primary/enrichment orchestration worked
   - semantic coverage for major AVGO guidance was strong
   - not perfect: at least one likely persisted data defect and one definite observability deployment defect were found

### 2. `FNKO_2026-03-12T16.30`

1. Source ID
   - `FNKO_2026-03-12T16.30`

2. Reason selected
   - explicit transcript fallback case with `HAS_QA_SECTION` and no `QAExchange` rows
   - clean fresh source for first-pass write validation

3. Pre-run state
   - `guidance_status=NULL`
   - existing `GuidanceUpdate` count for source: `0`
   - prepared remarks chars: about `16,881`
   - `qa_count=0`
   - `qa_section_count=1`

4. Runtime observations
   - queued via `trigger-extract.py` in `mode=write`
   - worker invoked `/extract FNKO transcript FNKO_2026-03-12T16.30 TYPE=guidance MODE=write`
   - primary pass wrote `/tmp/gu_FNKO_FNKO_2026-03-12T16.30.json`
   - primary write result: `created=5`, `updated=0`, `errors=0`, `concept_links=3`
   - enrichment explicitly tested `QAExchange`, got none, then fell back to `QuestionAnswer`
   - enrichment payload updated only `2` existing items (`Revenue Total`, `Gross Margin Total`)
   - enrichment dry-run: `valid=2/2`, `id_errors=[]`
   - enrichment write result: `created=0`, `updated=2`, `errors=0`, `concept_links=1`
   - final worker result: `status=completed`, `guidance_status=completed`, wall time about `289s`

5. Graph observations
   - final graph state: `guidance_status='completed'`
   - final `GuidanceUpdate` count from this source: `5`
   - final items:
     - `Revenue` total FY2026: `0%` to `3%` YoY
     - `Adjusted EBITDA` total FY2026: `$70M` to `$80M`
     - `Gross Margin` total FY2026: `41%` to `43%`
     - `Revenue` Funko Core FY2026: qualitative `high single digits year over year`
     - `Revenue` Loungefly FY2026: qualitative `down double digits`
   - enrichment updated in place rather than creating extra slots
   - final `source_refs` on updated items correctly unioned prepared-remarks and Q&A references

6. Semantic observations
   - primary extraction matched the prepared-remarks source well:
     - annual sales guidance `flat to up 3%`
     - adjusted EBITDA `70M-80M`
     - gross margin `41%-43%`
     - segment-level directional guidance for Funko Core and Loungefly
   - enrichment behavior was conservative and good:
     - no quarter-specific slots were invented from vague cadence language
     - annual `Revenue Total` item was enriched with quarterly phasing conditions (`Q2 up a little`, steady Q3/Q4)
     - annual `Gross Margin Total` item was enriched with tariff / pricing / licensing context from Q&A
   - this is a positive generalization signal for transcripts that only have `QuestionAnswer` fallback data

7. Obsidian/log observations
   - pod-local extraction note exists at `/home/faisal/Obsidian/EventTrader/Earnings/earnings-analysis/pipeline/extractions/2026-03-13_extraction_FNKO_2026-03-12T16.30.md`
   - host Obsidian vault again did **not** receive the note
   - this is the same deployment-level persistence defect observed on AVGO, not an FNKO-specific extraction issue
   - worker logs, pod-local note, and graph state were consistent on counts: primary `5`, enrichment `2 updated`, `0 new`

8. Verdict
   - strong success case for the transcript fallback architecture
   - no material semantic extraction defect found in this run
   - deployment-level observability defect remains open

### 3. `S_2026-03-12T16.30`

1. Source ID
   - `S_2026-03-12T16.30`

2. Reason selected
   - no prepared remarks at all
   - guidance, if any, must come from `QAExchange` content only
   - strongest over-extraction stress test in the transcript set

3. Pre-run state
   - `guidance_status=NULL`
   - existing `GuidanceUpdate` count for source: `0`
   - `pr_chars=0`
   - `qa_count=14`
   - `qa_section_count=0`

4. Runtime observations
   - queued via `trigger-extract.py` in `mode=write`
   - worker invoked `/extract S transcript S_2026-03-12T16.30 TYPE=guidance MODE=write`
   - relative to AVGO/FNKO, this run spent longer in pre-write reasoning after transcript load
   - primary pass wrote exactly `1` item; write result `created=1`, `updated=0`, `errors=0`
   - enrichment then wrote `/tmp/gu_S_S_2026-03-12T16.30_enrichment.json`
   - enrichment dry-run validated `3/3`
   - enrichment write result: `created=2`, `updated=1`, `errors=0`
   - final worker result: `status=completed`, `guidance_status=completed`, wall time about `368s`

5. Graph observations
   - final graph state: `guidance_status='completed'`
   - final `GuidanceUpdate` count from this source: `3`
   - final items:
     - `Net New ARR` FY2027 qualitative improvement over roughly `$200M`
     - `Gross Margin` long-term qualitative stability at the high end of long-term targets
     - `Operating Margin` FY2027 qualitative `double digit`
   - important provenance defect: final `Net New ARR` row carried a composite `"[PR] ... [Q&A] ..."` quote and `CFO Prepared Remarks + Q&A ...` section even though this transcript has no prepared remarks at all

6. Semantic observations
   - positive signal:
     - primary pass was restrained and wrote only one item instead of broad speculative output
     - `Gross Margin gp_LT` looks defensible from the explicit management statement that gross margins are stable, best-in-industry, at the high end of long-term targets, and not expected to change
     - `Net New ARR` is arguable but at least partially grounded because management replied `you're not wrong` to the analyst's rough `$200M` framing and described slight improvement plus stronger seasonality
   - negative signal:
     - `Operating Margin FY2027 = double digit` appears weakly grounded
     - the phrase `double digit for the year` appears in the analyst question, but the stored management quote only discusses drivers of leverage and improved profitability
     - this looks like a likely analyst-framing leak rather than clean extraction of an explicitly confirmed management target

7. Obsidian/log observations
   - host Obsidian vault again did **not** receive the extraction note
   - worker logs summarized the run as primary `1 extracted / 1 written` and enrichment `1 enriched / 2 new secondary`
   - same pod-local-vault persistence defect remains present

8. Verdict
   - mixed result
   - strong precision signal from the primary pass
   - enrichment likely introduced at least one semantic overreach and definitely corrupted provenance labeling for a Q&A-only source
   - this run lowers confidence in current enrichment quality filters for ambiguous Q&A-only transcripts

### 4. `HCAT_2026-03-12T17.00`

1. Source ID
   - `HCAT_2026-03-12T17.00`

2. Reason selected
   - low-guidance / sparse transcript candidate
   - useful test of whether the pipeline can abstain when management explicitly defers guidance

3. Pre-run state
   - `guidance_status=NULL`
   - existing `GuidanceUpdate` count for source: `0`
   - prepared remarks present but weak for guidance signals
   - `qa_count=12`
   - host-side source review found pressure commentary and an explicit promise to provide guidance on the next earnings call, not current guidance

4. Runtime observations
   - queued via `trigger-extract.py` in `mode=write`
   - worker invoked `/extract HCAT transcript HCAT_2026-03-12T17.00 TYPE=guidance MODE=write`
   - primary pass completed with `items_extracted=0`, `items_written=0`, `errors=0`
   - primary pass note explicitly recorded `NO_GUIDANCE`
   - enrichment then emitted `PHASE_DEPENDENCY_FAILED` because there were no primary items to enrich
   - outer worker still finalized cleanly with `status=completed`, `guidance_status=completed`, wall time about `187s`

5. Graph observations
   - final graph state: `guidance_status='completed'`
   - final `GuidanceUpdate` count from this source: `0`
   - no stray guidance nodes were written from vague pressure language or future-intent statements

6. Semantic observations
   - this looks correct from the source text
   - management explicitly deferred 2026 guidance to a future earnings call
   - transcript did contain business pressure discussion (`$12.5M` notified churn, `$35M` at-risk ARR, pressure across 2026/2027), but not the kind of forward-looking targets/ranges that should become guidance slots under the current contract
   - therefore `0` extracted items is a positive precision outcome, not a miss

7. Obsidian/log observations
   - host Obsidian vault again did **not** receive the extraction note
   - worker logs clearly stated the final reason: `NO_GUIDANCE`
   - enrichment status wording is operationally awkward: `PHASE_DEPENDENCY_FAILED` in this case is not a true failure condition

8. Verdict
   - strong precision success
   - pipeline correctly abstained from writing guidance
   - one workflow/observability cleanup remains: no-guidance runs should not surface an enrichment `failed` phase label when the overall outcome is valid

## Known Limits To Watch

1. Large transcript reads can still hit output ceilings even after warmup.
2. The worker validates result-file shape, not identity equality.
3. Manual semantic verification remains sampling-based unless every quote is re-checked.
4. Transcript quality issues upstream can mimic extraction defects.

## Suggested Fixes So Far

1. ~~Scaled count / share-unit canonicalization~~ — **FIXED** (2026-03-13)
   - Problem: `guidance_ids.py` maps plain `billion` to `m_usd`, so count-like metrics such as `Diluted Share Count` mis-canonicalize when the agent emits `unit_raw='billion'`.
   - Evidence: AVGO `Diluted Share Count` persisted as `canonical_unit='m_usd'` even though the quote says `4.94 billion shares`.
   - Resolution: closed as fixed.

2. Enrichment reuse of canonicalized values
   - Problem: enrichment reused an already scaled `AI Revenue` value (`100000`) together with `unit_raw='billion'`, which triggered a deterministic validation error before self-correction.
   - Evidence: AVGO enrichment first dry-run returned `valid: 3/4` and rejected `AI Revenue` as pre-scaled.
   - Suggested fix: when enrichment reads existing graph items, keep canonical values with canonical units consistently, or convert back to raw source-scale values before writing a new payload. Do not mix canonical numeric scale with raw source unit strings.

3. ~~Obsidian capture persistence from worker pods~~ — **FIXED** (2026-03-13)
   - Problem: extraction notes are written inside the worker pod’s `/home/faisal/Obsidian/...` path, but that vault is not mounted from the host.
   - Evidence: AVGO note exists in the pod-local vault but not in the host Obsidian vault.
   - Fix applied: added `obsidian-vault` hostPath volume mount in `k8s/processing/extraction-worker.yaml`. Deployed and verified read+write from pod.

4. ~~Observability summary should be generated from post-write truth~~ — **FIXED** (2026-03-13)
   - Problem: the pod-local AVGO note reported `Diluted Share Count` as `count`, while the graph row shows `m_usd`.
   - Evidence: note/graph mismatch after the same run.
   - Fix applied: CLI (`guidance_write_cli.py`) writes post-canonical sidecar file `/tmp/gu_written_{source_id}.json`. Hook (`obsidian_capture.py`) reads sidecar and renders "Written Items (Post-Canonical)" table in the note.

5. Q&A-only provenance must never be rewritten as prepared-remarks provenance
   - Problem: when enrichment updated the `S` transcript’s `Net New ARR` item, the final graph quote/section became `"[PR] ... [Q&A] ..."` and `CFO Prepared Remarks + Q&A ...` even though the transcript has no prepared remarks at all.
   - Evidence: `S_2026-03-12T16.30` has `pr_chars=0`, but the final item still carried prepared-remarks framing.
   - Suggested fix: build composite quote/section fields strictly from actual `source_refs` that exist for the source. If the item is Q&A-only, the final provenance should remain Q&A-only.

6. Analyst-framed targets need an explicit management-confirmation gate
   - Problem: enrichment for `S` created `Operating Margin FY2027 = "double digit"` even though the stored management quote does not say `double digit`; that phrase appears in the analyst question framing.
   - Evidence: the persisted quote only says operating margin is improving and profitability is accelerating.
   - Suggested fix: forbid extracting a numeric or qualitative target from analyst wording unless management explicitly repeats or unmistakably confirms that target in its own answer. Treat unconfirmed analyst framing as context, not guidance.

7. No-guidance runs should use a non-error enrichment terminal state
   - Problem: `HCAT` was a valid `NO_GUIDANCE` run, but the enrichment pass emitted `PHASE_DEPENDENCY_FAILED` because there were no primary items.
   - Evidence: outer job completed successfully with `0` items and explicit `NO_GUIDANCE`, yet the enrichment phase still logged a failure-style status.
   - Suggested fix: introduce a terminal state such as `skipped_no_primary` or `no_guidance`, and teach downstream dashboards/notes to treat it as a valid completion path rather than a failure.

## Current Observations

1. Obsidian vault exists at `/home/faisal/Obsidian/EventTrader/Earnings/earnings-analysis`.
2. Extraction-specific notes are stored under `pipeline/extractions/`.
3. Repo logs include `logs/extraction-worker.log.*`.
4. Existing Obsidian extraction notes show the capture path is live and usable.
5. AVGO baseline write-mode run completed successfully with `12` final items (`11` primary creates + enrichment touching `4` items and creating `1` new secondary item).
6. Enrichment dry-run caught a real pre-scaled-value error (`AI Revenue` at `100000` with `unit_raw='billion'`), and the agent self-corrected before write.
7. The persisted AVGO `Diluted Share Count` node appears mis-canonicalized as `m_usd` even though the quote is clearly `4.94 billion shares`.
8. The extraction-worker pod writes Obsidian capture files into a pod-local vault path that is not persisted back to the host vault.
9. FNKO confirmed the `HAS_QA_SECTION` fallback path works end-to-end: no `QAExchange` rows, but enrichment still loaded the fallback blob, updated the correct existing annual slots, and avoided inventing extra quarter items.
10. `S` confirmed that Q&A-only transcripts can be processed, but it also exposed two important problems: provenance fields can be corrupted during enrichment when no prepared remarks exist, and analyst-framed targets can leak into extracted guidance without clear management confirmation.
11. HCAT produced the right semantic result: `0` items and an explicit `NO_GUIDANCE` reason. The remaining issue is workflow semantics, because enrichment currently reports a failure-style phase when primary correctly finds nothing to enrich.
12. Forced rerun/idempotency on AVGO completed cleanly: primary reported `12 extracted / 0 written`, enrichment reported `0 enriched / 0 new`, and the final graph still contained the exact same `12` guidance rows with unchanged `evhash16` values and unchanged `source_ref_count` values.

## Idempotency Closeout

### 5. Forced rerun: `AVGO_2026-03-04T17.00`

1. Purpose
   - verify rerun behavior on a transcript that had already completed a successful write-mode extraction
   - confirm no duplicate slots, no provenance growth, and no evidence-hash drift

2. Pre-rerun baseline
   - `guidance_status='completed'`
   - final row count: `12`
   - baseline row snapshot:
     - `gu:AVGO_2026-03-04T17.00:adjusted_ebitda_margin:gp_2026-03-01_2026-05-31:non_gaap:total` -> `evhash16=3c8a205e0b9a6eb9`, `source_ref_count=1`
     - `gu:AVGO_2026-03-04T17.00:ai_networking_revenue_share:gp_2026-03-01_2026-05-31:unknown:total` -> `evhash16=8b6402d1df194004`, `source_ref_count=2`
     - `gu:AVGO_2026-03-04T17.00:ai_networking_revenue_share:gp_LT:unknown:total` -> `evhash16=ba72900eb82339fa`, `source_ref_count=1`
     - `gu:AVGO_2026-03-04T17.00:ai_revenue:gp_2026-12-01_2027-11-30:unknown:total` -> `evhash16=177622438a33495c`, `source_ref_count=3`
     - `gu:AVGO_2026-03-04T17.00:ai_semiconductor_revenue:gp_2026-03-01_2026-05-31:unknown:total` -> `evhash16=4d19346f28520cb4`, `source_ref_count=1`
     - `gu:AVGO_2026-03-04T17.00:diluted_share_count:gp_2026-05-31_2026-05-31:non_gaap:total` -> `evhash16=67077de44e900399`, `source_ref_count=1`
     - `gu:AVGO_2026-03-04T17.00:gross_margin:gp_2026-03-01_2026-05-31:unknown:total` -> `evhash16=f04aa7594e945eb7`, `source_ref_count=2`
     - `gu:AVGO_2026-03-04T17.00:revenue:gp_2026-03-01_2026-05-31:unknown:infrastructure_software` -> `evhash16=a1b9073d9cdd49f5`, `source_ref_count=1`
     - `gu:AVGO_2026-03-04T17.00:revenue:gp_2026-03-01_2026-05-31:unknown:non_ai_semiconductor` -> `evhash16=beac910f8364c2e7`, `source_ref_count=1`
     - `gu:AVGO_2026-03-04T17.00:revenue:gp_2026-03-01_2026-05-31:unknown:semiconductor_solutions` -> `evhash16=96b65525cfdd135a`, `source_ref_count=1`
     - `gu:AVGO_2026-03-04T17.00:revenue:gp_2026-03-01_2026-05-31:unknown:total` -> `evhash16=d18fda41fc3a78f5`, `source_ref_count=1`
     - `gu:AVGO_2026-03-04T17.00:tax_rate:gp_2026-03-01_2026-05-31:non_gaap:total` -> `evhash16=3ff7ff692f99c758`, `source_ref_count=1`

3. Trigger behavior
   - rerun attempt without `--force` was correctly refused with `Already processed: AVGO_2026-03-04T17.00`
   - rerun with `--force` queued successfully

4. Runtime observations
   - worker dequeued the forced payload at `2026-03-13 10:03:27`
   - primary pass completed with `items_extracted=12`, `items_written=0`, `errors=0`
   - primary summary explicitly said all `12` items were already present
   - enrichment pass completed with `items_enriched=0`, `new_secondary_items=0`, `errors=0`
   - final worker result:
     - `guidance_status=completed`
     - total duration about `259s`
     - explanation: primary already contained all Q&A-derived items; enrichment found nothing additional

5. Post-rerun graph observations
   - final row count remained `12`
   - final row snapshot exactly matched the baseline snapshot above
   - no duplicate IDs were created
   - no `evhash16` changed
   - no `source_ref_count` grew

6. Verdict
   - idempotency is strong for this tested transcript path
   - rerunning a completed transcript did not mutate graph identity, evidence hashes, or provenance cardinality
   - this is one of the strongest parts of the current pipeline

## Overall Assessment

1. End-to-end pipeline quality
   - infrastructure/orchestration quality: strong
   - deterministic writer/idempotency quality: strong
   - transcript semantic quality: good but not perfect
   - observability/persistence quality: mixed

2. What worked very well
   - all four fresh transcripts completed end-to-end in live `mode=write`
   - the pipeline handled four distinct transcript shapes:
     - rich prepared-remarks guidance (`AVGO`)
     - `HAS_QA_SECTION` fallback (`FNKO`)
     - Q&A-only transcript (`S`)
     - valid no-guidance abstention (`HCAT`)
   - the worker/skill/pass orchestration was stable across all cases
   - deterministic validation caught at least one real agent mistake before write (`AVGO` pre-scaled `AI Revenue`) and forced self-correction
   - forced rerun/idempotency behavior on AVGO was excellent

3. What is not perfect
   - at least one real persisted data defect exists today (`AVGO` diluted share count unit canonicalization)
   - at least one real semantic over-extraction risk exists today (`S` analyst-framing leak into `Operating Margin FY2027`)
   - at least one real provenance corruption defect exists today (`S` Q&A-only source rewritten as if prepared remarks existed)
   - observability is incomplete because pod-local Obsidian notes are not persisted to the host vault
   - no-guidance workflow semantics need cleanup so successful abstention is not partially labeled as a failure

4. Final judgment
   - this is not a perfect extraction pipeline
   - it is a strong pipeline with good architecture, strong runtime discipline, and impressive idempotency, but it still has correctness defects that matter
   - the current guidance transcript pipeline is already very good, but it is not yet good enough to claim `zero issues` or `absolute guarantee`

5. Score
   - current tested score for transcript-guidance extraction: `84/100`
   - rationale:
     - `+` strong architecture, stable live execution, strong abstention on HCAT, strong fallback behavior on FNKO, strong rerun/idempotency on AVGO
     - `-` one concrete persisted unit bug, one concrete provenance bug, one likely semantic overreach bug, and one concrete observability deployment gap
