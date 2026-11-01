# Extraction snapshot — 10 October 2026

**Assessment: the extraction code has strong regression and source-preservation evidence. We have not established 99% accuracy, recall or precision across the corpus, and the final independent exam has not run.** Complete extraction first; document-tree research and downstream selection/packing are parked by the owner's latest decision.

This snapshot reconciles saved evidence, not a new extraction or model run. It distinguishes selected-target correctness, preservation of existing outputs, and independent validation. Cohorts overlap; do not add their counts into one total or treat repeated routes as independent documents.

Readback receipt, source-file hashes and recomputed sample/target counts: `/home/faisal/prepare_work/extraction_handover_20261010/EVIDENCE.json`.

## 1. What has actually been tested

| Cohort | Size and kinds | Result and limit |
|---|---|---|
| Original selected regression panel | **137 documents, 132 filings, 117 issuers**, years 2023–2026: 116 HTML, 10 XML, 11 PDF. Splits: 72 development, 41 control, 24 originally held out. | Deliberately selected for difficulty. Its HTML route covers 60 development + 35 control + 21 released HTML documents. These are now exposed development/regression evidence. |
| Selected HTML table targets, approved package 4 | Development **171/171**; control **63/65**; released **64/64**. | **298/300 = 99.3%** on these selected target checks. Two control failures remain key/scoring-contract disagreements, not silently counted as passes. This is not full-table, document, corpus or future-production accuracy. |
| Selected HTML text/picture blocks | **101 text blocks pass**: 49 development + 34 control + 18 released. **12 picture blocks do not pass** in the HTML-only route: 8 fail, 4 approximate. Three page-furniture targets are excluded by the approved key. | 101/101 applies to the text subset only. Keeping a picture does not transcribe it or prove its chart/table relationships. These old HTML-only scores are not an end-to-end OCR score. |
| Selected XML values | **30/30**: development 9, control 18, released 3, across 10 XML source documents. | Excellent on a small selected value set; not complete XML/XBRL interpretation. |
| Wider exposed HTML checks | Original local cohort: **3,353 filer HTML documents from 1,009 filing packages**. Later bounded replays include **3,355 documents**. | Source preservation, boundaries, citations, native groups and change detection—not independently authored full-document answer sheets. Old reports calling this the whole corpus were corrected. |
| Additional fresh HTML development pilot | **100 documents, 100 filings, 57 issuers**; 50 main documents + 50 exhibits. | 100 runs completed; no reported uncovered/unanchored/unbound text. Browser token sequences match on 92; eight differences were source styling, layout characters, superscript boundaries or padding, with no demonstrated material text loss in the checked scope. 307 picture entries preserved. Only eight numeric tables received bounded source checks. Not a 100% semantic-accuracy result. |
| XML/XSD preservation replay | **4,396 XML + 963 XSD documents**, from 1,002 allowlisted accessions. | 3,360,120 elements and 9,940,692 attributes retained, including 1,896,251 elements previously lacking field units; old field output preserved. Independent libxml2 checks cover bounded cases and the three corrected inventory omissions, not every financial meaning. |
| OCR saved-input panel | **506 input entries = 50 difficult known-answer pages + 336 real embedded pictures + 120 later validation pictures**. | Current code preserves saved behavior in both optional-reader modes; 576 saved packets replay unchanged. This does not mean 506 correct readings. |
| OCR preservation audit | **505 available Chandra readings + one explicitly missing input**, 4,110 block regions. | Assessed text/table/block ownership survives the default packet path; known model errors survive too. Two readings hit the token limit; the missing picture failed preprocessing. |
| PDF exploratory conversion | **9 PDFs / 427 pages** in saved native/OCR work; 35/145 context pages processed. | Useful retained experiments, not a qualified production PDF lane or an independently complete accuracy result. |

Original panel filing forms, with amendments folded into their family: **25 10-K, 27 10-Q, 64 8-K, 10 Schedule 13D, 4 Form 425, 2 Form 6-K, 1 SC 14D9 and 4 SC TO-I documents**. These include main filings, earnings releases/slides, agreements/redlines and supporting disclosures. Form counts describe the filing containing the selected document, not a guarantee that every selected file is that filing's main report.

The additional 100-document pilot is conspicuously narrower: **1 10-K, 41 Form 425, 26 Form 6-K, 24 8-K including an amendment, 6 SC 14D9, 2 SC TO-I; no 10-Q or supporting HTML.** It cannot establish generality across all forms.

## 2. What the OCR accuracy evidence says

- On the 50 difficult pages, the early source-reviewed **text-level** result was Chandra **41/50 (82%)** and Sonnet 40/50. A fully correct page is a stricter measure than correct individual words, and this count does not certify every table relationship.
- On that panel, 389/525 blocks agreed between Chandra and Sonnet. Against source evidence, **388 agreed blocks were right and one shared error remained**. Agreement covered only about 44% of words; it does not measure source recall or validate the unagreed remainder.
- Of the 336 real pictures, 302 were unused before that trial and 34 already exposed. The 302 include **87 prose/scans, 56 logos, 47 mixed slides, 35 charts, 34 financial tables, 15 photos with text, 11 other, 10 diagrams and 7 KPI/infographic pictures**. Two-reader word agreement was 70.7%, only 28.9% for financial tables. Those are agreement figures, not accuracy.
- A source audit of 20 pictures in that trial found no wrong block among 90 agreed blocks and two genuine Chandra errors among 27 unresolved blocks. This small selected audit does not justify a corpus error bound.
- The later 120-picture trial exposed **18 wrong logo names** among 21 reported non-visual logo cases; the other three were case/spacing differences. Its claimed whole-image audit was corrected to **18 whole pictures + two partial**. Anything outside the recorded source checks was not inspected.
- A separate targeted check of ten pictures selected from numeric disagreements found **five wrong numeric/unit readings in two pictures**. This is an enriched error cohort, not a 20% random error rate. Known wrong fractions, multipliers written as percentages, heading/period links and chart/bar relationships remain.
- Rough historical word/digit percentages were small, selected estimates. There is **no defensible single OCR corpus precision/recall figure**. The 336/120 sets are now exposed evidence; they are no longer an untouched exam.

**Current owner policy:** Chandra + PP-OCR + OnnxTR, Sonnet optional and **off by default**. Free readings/flags are evidence, not automatic truth. The owner accepts Chandra-origin reading limitations for this extraction closeout; our code must preserve originals, readings, associations supplied by readers and honest missing/incomplete states. Future driver verification is separate and unbuilt.

## 3. What is complete in our code, within tested bounds

- Native HTML conversion, source formatting and existing Chromium measurement are composed through `driver.prepare.convert.html_route.prepare`; XML uses one strict parser and retains elements, attributes, namespaces, empty nodes and mixed-content order.
- Reviewed fixes preserve previously deleted text, inline fact spaces, struck/raised/lowered evidence, table/cell source identity, explicit links, pictures inside cells/inline spans and native paragraph membership. Browser-uncertain text that cannot be placed is retained as exact source evidence with PARTIAL status.
- Native paragraph evidence: **16,180/16,180 expected groups**, including 395 table-bearing groups, matched across 3,355 documents. This is native membership, not semantic heading authority.
- Prepared image bytes connect to the existing archive, workers, raw results, packets and every document occurrence's complete route. Reused images retain separate contexts. The composition checks used fake readers/test consumers; they do not prove real GPU execution or final-AI ingestion.
- Latest accepted code gate: **651 permanent + 402 retained grader tests**, no skips, with 506-input/576-packet replays unchanged. The two suites overlap; their counts are not 1,053 independent accuracy observations.
- Downloader's recorded historical disposition: **42,629/42,633 requests complete**, one with an unproved member and three not served. Use the repaired store and verified `read_package`, accounting for unresolved members. Download completeness is not extraction accuracy.

## 4. Biggest remaining issues, in priority order

1. **Finish bounded extraction-output review and automatic scoring coverage.** The independent key exists; its scorer still cannot fully assess required whole-table/relationship, picture, omission and other duties. Reuse current raw records, routes and comparison helpers. Separate literal extraction duties from the now-parked semantic tree; obtain an explicit scope decision for any deferred duty, never silently weaken the sealed key. Do not build a general semantic grading project.
2. **Close PDF coverage before claiming all-source extraction.** Census: 431 PDFs / 13,360 pages in 250 of 42,633 requested filings. 265 have a same-type HTML/text candidate; 166 do not. A candidate is not proven equivalent. Scans, mining reports and exhibits may contain unique information. Reuse saved native PDF/OCR work only where required; no universal substitution assumption.
3. **Qualify the actual worker and production input path.** The committed `readers.chandra` currently calls MLX; it is not a ready NVIDIA/vLLM worker. Reuse Chandra's native supported server path when the NVIDIA machine is chosen, through the existing reader boundary. NVIDIA Chandra, bounded CPU evidence readers, exact model/dependency/input settings, resource limits, cache identity, failure/restart behavior and filesystem need a real-machine check. Local Mac diagnostic settings were not adopted. The real downstream AI consumer remains unbuilt and separately deferred.
4. **Keep specific representation limits visible.** Forty potentially material private-use symbols in four exposed documents still need image interpretation; raw/source/font evidence is retained. Two fresh-pilot pages keep 310 hyperlinks without proven unit/cell ownership. Off-screen/clipped/same-colour text, physical fonts, unusual visual order and unsupported HTML/browser cases have bounded or unmeasured coverage. Some source fragments are preserved without proven visible order. These are not all newly confirmed code bugs; each needs materiality and a native-capability check before implementation.
5. **Owner-guided organization/optimization and final validation.** Preserve behavior and tests; measure gains, archive research separately and remove runtime dependencies on it. Freeze, run the independent exam once authorized, then qualify the chosen workers and repeat the same set to check backend changes. A repeat is not another generalization test.

XML preservation does not resolve external taxonomy dependencies or validate financial semantics. Whole-corpus attachment dispatch and future live ingestion are not proved by the sampled converter replays. Images absent from a sampling frame, SVG/CSS images and unavailable sources must not disappear from coverage accounting. No human-review step is allowed in production; source inspections here were development/evaluation work, often by AI reviewers, not a proposed operating workflow.

## 5. Independent validation still to run

**KEY_READY / SCORER_NOT_READY / EXAM_NOT_RUN.** Public handoff: `/home/faisal/prepare_work/validation_next_20261007/public/KEY_READY.md`.

- 300 probability-sampled documents + 30 reserved challenges; 300 picture slots, 292 available pictures / 283 unique images, eight unavailable retained.
- 221 complete selected tables / 7,563 nonempty cells, 166 prose regions, 68 XML subtrees and whole-source inventories; whole-picture reviews include context/relationships. This does not assess every word outside selected document regions.
- 622 available cases independently read and reconciled; 71 retain bounded source uncertainty. These are source ambiguities, not observed extraction errors.
- All 81,483 restored backup hashes passed in Test Agent's receipt. No outputs informed the answers.
- Main HTML, exhibits, supporting HTML/XML, challenge exposure and repeated-image clusters need separate reporting. Ten challenges have known/possible exposure and cannot count as proven unseen.
- Accepted public scorer v15 closes a specific table-span false-success defect; it does **not** establish complete scoring readiness. Historical binding counts must not be presented as a current accuracy score.

The earlier 24-document blind exam remains **50/64 HTML cells (78.1%)** historically. Repairs plus reviewed answer-key corrections later yielded 64/64 on those released documents. Both figures must remain; the later result is not new blind evidence.

## Evidence index

- Exact old-panel counts/forms: `/home/faisal/prepare_work/step3_sample_20261002/selection_summary.json` and `selection.json`.
- Selected-target results: `/home/faisal/prepare_work/package4_switch_20261007/graded/`; integration explanation: `/home/faisal/prepare_work/grader_review_codex_20261003/FABLE_CONVERT_EXTRACT.md`.
- Wider-cohort scope correction: `/home/faisal/prepare_work/grader_review_codex_20261003/FABLE_JOINED_NUMBERS.md`; later source gates supersede its old defect list.
- Fresh pilot: `/home/faisal/prepare_work/fresh_prepare_development_20261009/ROOT_FULL100_GATE.md`, `ROOT_LINK_ASSESSMENT_GATE.md`, `pilot_v1/INVENTORY.json`.
- XML: `/home/faisal/prepare_work/post_font_scope_20261008/XML_GATE.md`.
- Native paragraphs: `/home/faisal/prepare_work/native_paragraph_20261009/ROOT_FINAL_GATE.md`.
- OCR accuracy history: `/home/faisal/prepare_work/pdf_twin_census_20261004/ocr_bench/real575_20261005/v4_replay/RESPONSE_TO_CODEX.md`, especially corrected r9/r10 and block-review sections; targeted numbers: `../runtime_extract_20261006/CHECK10_RESULT.json` relative to `v4_replay`.
- OCR preservation: `/home/faisal/prepare_work/ocr_completeness_20261008/raw_preservation/CODEX_GATE.md`.
- Current connection and code proof: `/home/faisal/prepare_work/picture_chain_preflight_20261009/ROOT_FINAL_GATE.md`; `/home/faisal/prepare_work/packet_close_20261009/ROOT_GATE.md`.
- Scorer: `/home/faisal/prepare_work/scorer_finish_20261009/root_table_v2_review/ROOT_FINAL_GATE.md`; public `SCORER_CLOSURE_INVENTORY_20261009.md` and `SCORER_FINISH_DECISIONS_20261009.md` (their table-span proposal is superseded by v15 acceptance).
- PDF census and limitations: [PrepareTools.md, PDF section](PrepareTools.md#pdf--parked-preserve-for-later).

Use [PrepareExtractionHandover.md](PrepareExtractionHandover.md) for the new session's work order and agent communication.
