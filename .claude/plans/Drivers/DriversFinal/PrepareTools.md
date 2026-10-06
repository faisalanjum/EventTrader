# Preparation tools and scope

*2026-10-05 · Start here; linked records hold reproduction details.*

**Order:** grader/baseline → worktree merge → **HTML/XML + selective image OCR**. Dedicated PDF development is **paused**; preserve originals, fallback and research. Historical downloading is approved; live ingestion remains separate. [Overall plan](PrepareStep.md).

**Standard:** minimal generic code, libraries first, no paid APIs, exact source links. Preserve values, signs, units, dates, labels, order, footnotes and relationships. Target 100% on agreed tests; unread/uncertain content never counts as complete. Sample scores do not prove corpus accuracy.

**Shared owner priorities — Fable's grader/HTML/XML/Docling/EdgarTools work and the OCR bot (Oct 6):**

1. **Fully automatic production:** no human-review dependency. Detecting uncertainty is intermediate work; resolve it automatically where possible and report remaining gaps honestly. Independent source checks during testing remain necessary; they must not become a production requirement.
2. **Highest implementation priority — absolute minimalism and generic code:** reuse tested libraries and components; keep our code to necessary integration. No company-, document-, wording- or layout-specific exceptions, growing lists of special cases, duplicate rule engines or speculative additions. Use existing libraries for standard format syntax; do not build a checker for every possible presentation.
3. **Faithful meaning for the final AI reader:** a proven harmless presentation difference must not fail grading, trigger extra conversion/rendering/model calls, or block usable content. Preserve raw readings and source links. Reuse existing comparison rules for a small, tested set of presentation equivalences; do not build a new AI judge or word-exception list. Changes to facts, labels, units, periods, negation, qualifiers, entities or relationships still matter. Case and tense changes are not automatically harmless; an existing `other` difference is not proof of safety.
4. **Minimize unnecessary processing automatically, especially for historical backfills:** reuse cached, versioned results and existing evidence; escalate only unresolved, meaning-affecting gaps. For HTML/XML, avoid repeated parsing, conversion, full rendering and source matching. For OCR, minimize Sonnet calls, aiming substantially below the provisional 60–80% estimate. Measure complete latency, calls/tokens, memory and storage; test content that bypasses expensive steps for errors and omissions. Cost/speed improvements must preserve accuracy, context and completeness.

**Before every Fable/OCR handoff:** check the proposed action against all four priorities and current owner decisions. Give the smallest necessary next change and its validation; correct conflicting instructions and keep the two bots' source/context contracts aligned. These requirements apply to both streams, not just the current experiment.

Keep frozen tests/results unchanged. Measure literal fidelity and meaning-affecting errors separately; version any later acceptance-rule change and show its effect on saved readings before adoption.

**Current execution:** follow [Next actions](#next-actions). Earlier scores, timings and candidate flows below are research history, not current production approvals.

## HTML/XML first: tested tools and gaps

**Candidates, not a production-approved pipeline:**

| Format | Best supported approach so far | Evidence and remaining work |
|---|---|---|
| **HTML** | EdgarTools + source visibility, formatting, links/images and browser geometry; Docling remains a comparison. | Development: **171/171 cells**; structures **49/60 pass, 6 fail, 2 approximate, 3 excluded**, before final image integration. Source identity/context and integration remain. |
| **XML** | Small standard-parser wrapper; preserve hierarchy, attributes, namespaces, mixed prose and source spans. | **601/601 main XML files** pass structure/text checks; semantics and attachments unproved. Unresolved external content fails explicitly. |
| **Images** | Docling + **RapidOCR medium**; verified embedded text first, original pixels authoritative. | **85/575 images** processed. Check numbers, negation, orientation and associations; confidence cannot certify accuracy. |

**Speed:** HTML linking alone: **214→49 s/60 files**. Fuller route: **738 + 110 s**, excluding resource indexing/OCR; final latency unmeasured.

## Image OCR (Oct 5)

**Lanes (owner):** HTML (plus plain text), XML and OCR. A PDF's hidden text gives exact characters, but its tables need a layout step to keep rows and columns (Codex; see "PDF — parked" below). An HTML twin replaces a PDF only after code proves they match. Scanned or scrambled pages, and charts inside PDF pages, go through the OCR lane as pictures. PDF work stays parked. (To be checked: send text-PDF pages through the picture readers, which output tables, and check every character against the hidden text; untested idea, not Codex's.)

**Historical — superseded Oct 5, do not implement** (it skips logos and tiny pictures, accepts matching numbers alone, and makes Sonnet's numbers final; the strict checker work showed all three unsafe). Kept as a record:
1. Skip logos, photos, tiny pictures and repeated pictures.
2. PP-OCRv6 and OnnxTR (fast) each read the whole picture, side by side. If every number matches, accept the picture with no AI.
3. Otherwise Sonnet (low effort) reads the **whole** picture and its numbers are final; positions come from OCR.
   - Sonnet runs as a lean, tool-free `claude -p` call on the subscription, with no API key. Never use `--bare`, which signs in with the paid API key. Command: [lean_call.py](../../../../../prepare_work/pdf_twin_census_20261004/ocr_bench/sonnet_pilot_20261005/lean_call.py).
4. Safety check: Sonnet also reads ~1 in 50 accepted pictures at random.

| Option tested (Oct 4–5) | Accuracy (exact answers unless noted) | Speed per picture | Verdict |
|---|---|---|---|
| PP-OCRv6 alone (free) | 99.8% on clear pictures, 94–97% on small; hardest page 77/80 | ~3 s | Step 2; gives exact positions |
| OnnxTR fast alone (free) | Hardest page 64/80 | ~3 s | Checker in step 2 only |
| **PP-OCRv6 + OnnxTR fast agree** (free) | See note below the table | ~3–5 s | **Step 2** |
| **Sonnet low, whole picture** | 2,175/2,176 on 31 pictures (the 1 is an answer-key quirk); 600/600 randomized; hardest page 80/80; [hard set](../../../../../prepare_work/pdf_twin_census_20261004/ocr_bench/new_models_20261005/hard_set/) 11/11 pages + "$69"; effort low = medium = high = xhigh | ~5–9 s, ~5k tokens | **Step 3**; its own positions drift ~3 rows, so OCR's are used |
| Sonnet on a cut-out spot | 8 errors (cut-outs lose context) | ~4 s per spot | Rejected |
| Opus | Hardest page 80/80 | ~27 s | Not used (owner) |
| Haiku, any effort | 55–59/80; invents numbers | 26–135 s | Rejected |
| Luna low/medium (ChatGPT) | Hardest page 79/80; 28 wrong alone on 31 pictures; Luna-first still sent 39% to Sonnet | ~16–20 s | Rejected: slower than the free pair |
| Chandra OCR 2 (licence permission) | Hardest page 80/80; caught the "$69" the free pair missed. [Hard set](../../../../../prepare_work/pdf_twin_census_20261004/ocr_bench/new_models_20261005/hard_set/): **10/13 with its own enlargement** (4/12 without; our first runs skipped it). Misses: a tiny fraction (Simon "8⅜%"), text ~11 px, and a chart slide (guessed values marked "~", printed axis labels skipped) | Mac M4 Pro, full precision, own enlargement: ~100 s per small page, 2–3 min per large slide, ~11 GB. 8-bit on 8 cloud cores: ~5 min. Our CPU: 7–13 min | Third reader in the flows below |
| LightOnOCR-2-1B | Hardest page 80/80 (repeats some row labels in headings) | 1.5–4.6 min on our CPU | Accurate, but slow |
| GLM-OCR | Hardest page 78/80, 3 misread | ~1 min on our CPU | Rejected: misreads |
| PaddleOCR-VL 1.6 (Codex) | Invented a number; wrong year/value links | ~100 s per page | Rejected |
| 5-reader line vote (free) | 0 wrong of 5,343 when median line ≥20 px; 12 errors at 75 dpi | ~20 s | Fallback only |
| Qwen 27B tie-break (Mac) | Cut tiny-text errors 12→1; ~28% of lines wrong alone | ~2.3 s per line | Fallback only |
| Tesseract | Misses faint text; with PP-OCRv6, whole-picture match on only 20/128 | ~1–3 s | Rejected as checker |
| Super-resolution, EasyOCR | Worse, or no gain | — | Rejected |
| Jev | Text only (docs checked Oct 5) | — | Can't read pictures |
| Codex's comparison (8 images) | RapidOCR alone 113/123 regions; combined readers 119/123 | OpenVINO: 17.2→11.4 s, same accuracy | Its cautions apply |

**PP-OCRv6 + OnnxTR fast, agreement results:**
- **Test pictures:** they agree on 77%, with 0 wrong and 0 missing in 6,588 numbers.
- **30 new test pictures:** they agree on 60%; 1,050/1,050 right.
- **30 real pictures** (no exact answers; Sonnet as reference, checked by eye): they agree on 50%, but only 1 of 10 tiny-text pictures. That covers 501 numbers, 0 wrong, **1 missed by both** (a faint "$69" chart label).

**Real pictures:**
- 58.4% of filings have pictures, mostly logos.
- About 15% of filings have text only in pictures, mostly investor decks.
- Of pictures with numbers, 81% have a median text line ≥20 px and 19% are tiny.
- The real test oversampled tiny text; reweighted, the free pair settles about 60% of pictures.

**Cautions:**
- Agreement can share mistakes (Codex; the "⅜" read as "838"; the missed "$69").
- Finding the same digits elsewhere in a filing is not confirmation.
- The real-picture samples are small.
- Single digits and column links are not scored.

**Cost (superseded Oct 5: measured with the old lenient count):** about 40% of useful pictures need Sonnet. For history, about 200M Claude tokens instead of ~500M; the free part takes ~3–5 s per picture on our server. Under the strict checker the free tools almost never confirm a page; re-measure before use.

**Next:**
- 150 random real pictures, with no oversampling and Sonnet as reference.
- Chandra checks (below).

**Recommended flows (agreed in chat, owner Oct 5; tested on the 50 hard pages; real-picture shares pending). Rule wording superseded Oct 5: "agree" now means the checker's one decision (same text in order and the same table relationships), never numbers alone:**

```
Rule: accept a page only when two readers wrote the same whole page: same text in order and same table relationships (checker v8).

HISTORY (batch)
1. Free tool A, free tool B and Chandra read every picture.
2. Any 2 of the 3 match                    → accept
3. Else Sonnet reads it; matches any of the 3 → accept
4. Else Opus reads it (to be checked); matches any → accept
5. Else keep Sonnet's reading, tagged "unsure"

LIVE (seconds)
1. Free tool A + B read it; they match       → accept
2. Else Sonnet reads it; matches A or B      → accept
3. Else use Sonnet's reading now, tagged "provisional"
Overnight: provisional pages go through HISTORY steps 1–5 → confirmed or fixed
```

| | History (backfill) | Live (new filings) |
|---|---|---|
| Readers | Free pair + Chandra read every picture | Free pair now; Sonnet when they disagree |
| Accept | Any 2 of the 3 agree on the whole page (text and table relationships) | Free pair agree, or Sonnet equals a free tool (same rule) |
| Otherwise | Sonnet, accepted if it equals one of the 3 → (to be checked) Opus, same rule → else Sonnet's reading tagged "unsure" | Sonnet's reading used now, tagged "provisional"; overnight Chandra (+ Opus) confirms or fixes |
| Result, 50 hard pages (⚠ old lenient count, superseded: a strict check (v4, Oct 5) finds the free tools almost never write a page exactly; to be re-measured with Chandra) | 0 wrong; 13 Sonnet calls; 4 unsure | 0 wrong accepted; 10 accepted via Sonnet; 13 provisional (Sonnet right on 12) |
| Speed | Batch | ~8 s; +~9 s when Sonnet is needed |
| Cost | Chandra on a rented GPU, ~1 day, ~$25–60 (estimate) + Sonnet on leftovers | Sonnet ~5–9k tokens per call; a 30-slide deck ≈ 10–15 calls, ~100k tokens |

- **Why whole page:** number-level agreement failed (the free tools share mistakes, e.g. "$" read as "5": 5 wrong). Alone, Sonnet accepted 11 wrong numbers and Chandra 17; all-3-agree-else-Sonnet 10 wrong with 24 calls. Chandra certainty added nothing; size and chart rules are unnecessary (disagreement catches them). [Simulation](../../../../../prepare_work/pdf_twin_census_20261004/ocr_bench/new_models_20261005/hard_set/big/simulate.py).
- **Chandra facts:** its own enlargement step is required (shorter side to 1,536 px; without it 4/12, with it 10/13); enlarging further (3×, 3.4×) did not fix the dense table or the fraction and was slightly worse. It guesses chart values (marked "~"). Engine check ✅: Datalab's own code = the Mac engine (MLX).
- **Per report (superseded Oct 5, old lenient count):** logo-only filings (~53% of filings with pictures): 0 calls; 5–19 pictures: ~2–4 live calls; investor deck (20+): ~8–15 live, ~3–8 history. Logos are not skipped wholesale (Codex v8): reuse readings of byte-identical images per occurrence; skip only confirmed decoration with a recorded status.
- **Still needed:** 50 random real pictures (real-world shares); the Opus step is untested.
- **GPU rule:** rent by the hour, one batch, shut down; never 24/7 (~$30–70/day). Large models never run on our servers; GPT Cloud stopped and cleaned (owner, Oct 5).
- **Candidate to test (Oct 5, not decided):** one flow for history and live. Chandra reads every picture (history: rented GPU for one day; live: Datalab's service, ~$10/month) → checked against a second reading with the checker (whole page: text and table relationships; never numbers alone) → disputed regions re-read with their context. The AI reader gets the exact reading that was checked, with its picture link and status (verified / unresolved). Measured Oct 5: the free tools confirm only ~3% of Chandra's blocks, so they cannot be the second reader. **Crop re-reading tried and not adopted** (8 examples, 16 crop calls): more calls and tokens than whole pages (63k vs 39k input), no page completed; its selector missed 8 of 235 planted omissions (headings, a credit-rating line), so its earlier "0 missed" claim is retracted. Chandra's chart and diagram blocks can hold its own estimates and invented labels; those never count as verified text. Reader packets (Oct 5–6, no calls; after Codex's block and support reviews): the AI gets one reading block by block — *agree* (block agreement between two readers, decided by the checker) / *unresolved* (text kept, all differences stored, Sonnet's reading of the region shown as an unverified alternative) / *visual* (picture region only) — with the picture link and regions, plus FREE OCR lines (what two simple OCR tools both read at the same spot: evidence, never a decision). On the 50 answer pages, counted once: **candidate coverage 57.0% of words** (block agreement 43.8% + free-OCR-supported picks 2.4% + tables where both readers link every number to the same headings and row label 11.3%; not verified accuracy: it includes 1 known shared word error and unproved relationships), each part checked against the original separately; tables are kept whole with their headings, units and notes; 43% stays unresolved and visible. No automatic choosing rule adopted yet. LightOnOCR-2 parked. Cost figures so far are simulations, not measured production cost.
  - **Statuses are distinct:** *read by Sonnet* (one reader's text), *readers agree* (two readings equal under the checker; consistency, not proof against a shared error), *checked against the original* (a person or exact answers confirmed it). Only the last proves correctness; the AI reader is told which one applies.
- Sources: [Chandra GitHub](https://github.com/datalab-to/chandra), [GPU prices Oct 5](https://getdeploying.com/guides/cheapest-gpu-cloud), [Datalab pricing](https://www.datalab.to/pricing) ($10 per 1,000 pages accurate; free $20/month).

Evidence:
- [realistic pilot](../../../../../prepare_work/pdf_twin_census_20261004/ocr_bench/real_pilot_20261005/), [new free pictures](../../../../../prepare_work/pdf_twin_census_20261004/ocr_bench/free_tier_confirm_20261005/), [free tier](../../../../../prepare_work/pdf_twin_census_20261004/ocr_bench/free_tier_20261005/)
- [new models](../../../../../prepare_work/pdf_twin_census_20261004/ocr_bench/new_models_20261005/), [hard set](../../../../../prepare_work/pdf_twin_census_20261004/ocr_bench/new_models_20261005/hard_set/), [Luna pilot](../../../../../prepare_work/pdf_twin_census_20261004/ocr_bench/luna_pilot_20261005/), [randomized](../../../../../prepare_work/pdf_twin_census_20261004/ocr_bench/random_pilot_20261005/)
- [20 pictures](../../../../../prepare_work/pdf_twin_census_20261004/ocr_bench/sonnet_pilot_20261005/), [Claude checks](../../../../../prepare_work/pdf_twin_census_20261004/ocr_bench/claude_check_20261005/), [line vote](../../../../../prepare_work/pdf_twin_census_20261004/ocr_bench/line_vote/)
- [Codex results](../../../../../prepare_work/ocr_followup_20261004/RESULTS_20261005.md), [earlier screens](../../../../../prepare_work/tool_selection_20261004/trials/ocr/quick_compare_20261004/RESULTS.md)

**Output (owner decision D16 for pictures, Oct 5):**
- **Receipt:** one JSON file per picture, stored beside the originals. It records the reading and its picture/region, the reader(s), the comparison outcome, and any independent check against the original with its scope (text, relationships, or both), plus the tools and versions used. Unresolved and visual content stays explicit; *visual* describes content, not proof its printed text was read. *Readers agree* and *checked against the original* stay distinct (wording: Codex, Oct 5; was "status (free tools agreed / Sonnet read)").
- **Reader text:** a Markdown table placed where the picture sits, with unsure numbers marked. It lives in one new Neo4j node per picture: `Report → HAS_EXHIBIT → ExhibitContent (or section node) → HAS_IMAGE → ImageContent` (text, order, receipt link). Existing text is untouched.
- **Driver links:** Driver facts link to the `ImageContent` node and the cell; the receipt gives the exact spot.

Resume after the grader/HTML/XML gates; validate unseen originals and full latency. Unread images remain partial.

## Next actions

**Finish plan (Oct 6): one working route, existing checks, bounded automatic recovery.** No new framework, document-specific exceptions, human-review queue or speculative features. Baseline and selective merge are already recorded; retain their [handoff](../../../../../prepare_work/grader_review_codex_20261003/FABLE_MERGE_APPLIED.md), [merge checklist](../../../../../prepare_work/tool_selection_20261004/MERGE_PLAN.md#integration-sequence) and [file ledger](../../../../../prepare_work/grader_review_codex_20261003/codex_merge_review_20261005/REPORT.md).

**Fable — complete HTML/XML extraction; use the grader to verify it:**

1. Finish the open text-loss, source-position and control-sample failures at their existing parser/adapter boundary. Reuse EdgarTools/Docling capabilities, the selected route's browser geometry and a standard XML parser. Fix the failure class once; no filing-specific branches or parallel parser/checker. Use original DOM measurements rather than expand browser-emulation rules.
2. Keep one existing output model: ordered blocks/tables, parent headings, units, periods, notes and exact source/image identities. Preserve whole tables until row-level context is proved. Attach OCR results by source image identity; retain each occurrence's surrounding context. Do not build the final chunker here.
3. Keep the grader focused on lost/changed meaning and wrong associations under the approved contract. Valid presentation differences must pass; wrong values, qualifiers, periods or row/column links must fail. Change grading only for a reproduced defect, with original-backed positive and negative controls; preserve frozen results and record any contract change. Do not add grading machinery merely to raise a converter's score.
4. Measure and remove repeated work in the chosen route before adding alternatives. Reuse parsing, source positions and cached results; measure full cold/warm latency, memory and storage, including fallbacks. Test both the fast path and recovery automatically; a speed gain cannot conceal omitted content.
5. Freeze the candidate; test untouched documents and audit every in-scope corpus input for missing content and unsupported cases. Expose the tested extraction path for reuse without copying benchmark orchestration into production. Dedicated PDFs, news/transcripts and live-ingestion hookup remain separate scope.

**OCR — finish automatic resolution:**

1. Preserve the completed 336-picture comparison as the frozen baseline (logos included). On its 302 previously uninspected pictures, **60,662/85,786 non-visual output tokens agree (70.7%)**, not source accuracy or completeness. Source audit: 20 stratified pictures, 90 agreeing blocks with no error found by the OCR bot; six visual regions still contain printed content not delivered as checked text. Main next task: table/context resolution, with a small declared-math notation fix using existing components; then chart labels/associations. [Codex's bounded work order](../../../../../prepare_work/ocr_real336_review_20261006/CODEX_NEXT.md). Reuse saved readings and retain blocked/truncated results; no fresh model search or blanket logo skipping.
2. Keep Chandra's existing structured output and source positions; reuse cached readings for identical images while retaining each occurrence's context. Handle proven presentation equivalences through existing format libraries and comparison rules. A table/chart starts the existing local checks, not an automatic Sonnet call. Keep values and their full context; no second output schema or custom layout detector.
3. For remaining meaning-affecting disputes, test one bounded follow-up through an existing image reader: all disputes for one picture together, with the source image and complete paragraph/table context. Require a source-based rereading, not a vote between candidates. Reuse the existing call/packet path; do not restart the failed many-crop workflow or build a separate AI judge. This recovery step is a proposal to measure, not a proved fix. Adopt only if original-backed tests show fewer material errors without introducing new ones; no unbounded retry loop.
4. Validate the complete automatic path, including shared errors, omissions and the cases its routing would accept without rereading. No human production decision. If a material case still cannot be resolved, preserve its source and explicit failure; the accuracy objective remains open, not silently passed.

**Hybrid candidate (Oct 6; saved readings only):** Chandra primary; one small automatic routing decision uses existing completion, coverage, position and free-OCR evidence before calling Sonnet. Comparisons that already require Sonnet cannot save its call. No company names, manual picture labels, answer keys or per-layout exceptions in routing. Absence of a warning is not proof of correctness. Test the cases that bypass Sonnet as well as those escalated; report meaningful errors, omissions and calls saved. If existing checks are insufficient, report the measured limit instead of adding another rule engine or relaxing accuracy.

**Routing evidence:** a `Table` label alone misses cases: 50/302 pictures have it, but 87 contain table markup. These counts describe candidates, not mandatory calls; the earlier 60–80% estimate is not a target. Reuse the [review's failure examples](../../../../../prepare_work/ocr_real336_review_20261006/HYBRID_REVIEW.md), but follow the current priorities above: no blanket table/chart escalation and no new framework. The safe call rate remains unproved.

**Oct 6 development review, round 2:** math, table/context guards and word counter-evidence fixes pass. Reproduced v4: **177/302 pictures routed (41.4% of Sonnet calls avoided)**; eight table choices, **0/546 damaged readings selected**, six harmless-spacing controls retained. Approved for continued development, not production. **Reject blanket lone-symbol suppression:** it can hide a digit, unit, footnote or checkbox change; decorative roles must come from existing structure/rules. The “all non-visual blocks agree” count is not a wasted-call measure. [Verdict and offline probes](../../../../../prepare_work/ocr_real336_development_review_20261006/r2/CODEX_REVIEW.md). Next: chart printed content with its context, using saved readings; no new checker or layout rules.

**Filer's slide text beside pictures (Oct 6; offline replay done, not adopted):** many filers put each slide's text in the page as tiny or white text near the slide's `<img>`. By the grader's approved visibility rules this text is visible, and the HTML route already outputs it (checked on CF Industries' EX-99.1), so the final reader already gets it. As a way to skip Sonnet it does not pay: it is tied cleanly to its picture (a container holding only that picture) for 154/336 test pictures; of the 209 routed, only 37 are routed for word disagreements alone, and the existing checker finds Chandra's reading the same as that text for 1 of the 37 (planted swaps, changed numbers, dropped words, a negation, a repeated line and a stale copy all kept their call). Blockers: on scanned pages the text is itself an OCR layer with errors ("ALTowhead" for "Arrowhead"), words split at line ends, page numbers placed elsewhere. [Data and scripts](../../../../../prepare_work/pdf_twin_census_20261004/ocr_bench/real575_20261005/hidden_text_20261006/) (`BYPASS.json`, `STRUCTURE.json`). FinancialFilings (paid) does not convert SEC exhibit pictures ([test](../../FinancialFilings/picture_text_test_20261006.md)).

**Shared finish gate:** zero observed meaning-affecting errors or unexplained omissions on the locked agreed/unseen tests; every corpus input accounted for; no required human step. Retain raw evidence and harmless differences without extra calls. Test restarts/timeouts and resource limits; measure actual end-to-end time, calls/tokens and memory. Use existing content-hash/version caches and bounded workers. Package these tested paths as reusable code; chunking remains a later validation of context and size. Universal accuracy on future inputs is not implied.

## Images: prioritize, do not exclude by count

- **197,422 files / 168,632 byte hashes**, in **24,894/42,630 filings (58.4%)**, including logos. Reuse identical bytes. Excludes inline/external graphics, images inside PDFs and news/transcripts.
- The **339-filings/0.8%** screen misses ordinary-report charts. Inspection confirmed missing AEP demand labels/values; Dycom's **30 slides** and Abercrombie's **14 call-page images** have empty HTML bodies. Other copies are unverified.
- Pilot **0.23%** = estimated OCR-text mismatch in image-bearing filings, **not information loss or an upper bound**: 120 filings, **308/1,522 images unread**, signs/context ignored; heuristic “boilerplate” can include financial tables. Unique lost-fact share is unknown.

**Process:** skip confirmed decoration → reuse verified embedded text → OCR informative images → flag unresolved. Hidden copies can be stale/flattened. Prioritize **5,563 filings with 5+ images**; these are not necessarily decks, and smaller cases cannot be excluded. Unread informative images make HTML partial. [Audit](../../../../../prepare_work/tool_selection_20261004/image_scope_20261004/RESULTS.md), [pilot](../../../../../prepare_work/pdf_twin_census_20261004/README.md).

## PDF — parked, preserve for later

Saved Docling native/OCR work covers nine files/427 pages; **35/145 context pages** processed. PDF/image OCR settings differ. Assembly, context, mappings and derivative-writer validation remain; picture-only output is unread. Native conversion: **592 s/427 pages**; the 14 s preflight omits full conversion. Tested EdgeParse, OpenDataLoader, gmft, Camelot, pdfplumber/PyMuPDF and Xberg configurations failed table/text controls. [Comparison](../../../../../prepare_work/tool_selection_20261004/COMPARISON.md).

**431 PDFs in 250/42,633 requested filings (0.59%)**. Filename census covers 42,630 saved filings; three unavailable, misnamed PDFs and news/transcripts are outside scope.

| Group | Files | Pages |
|---|---:|---:|
| Same SEC document-type HTML/text candidate | 265 | 11,543 (86.4%) |
| No same-type candidate: Schedule 13D/13D-A exhibits | 157 | 1,300 |
| No same-type candidate: 10-K EX-96 mining reports | 6 | 446 |
| No same-type candidate: two 10-Q and one 8-K exhibit | 3 | 71 |
| **Total** | **431** | **13,360** |

- Candidate breakdown: **166** overlap one counterpart, **18** combined filing text, **3** partly differ, **78** have missing/garbled extraction. None proves equivalence.
- Of 166 without same-type candidates, **3 overlap elsewhere**. Earlier 151 omitted six scanned 13D exhibits; only those six of 157 are established scans.
- Matching ignores order, short values and visual relationships; a “same text” result lost `2022` and `322`. Neither “identical twins” nor “166 PDF-only files” is proved. Page share is not information/work saved.

SEC manual v78 (2026-09-14), §5.2.3.5 requires unofficial PDFs to accompany ASCII/HTML; §5.2.3.6 permits exceptions, including EX-96/10-K and EX-99/6-K. **Not proof of equivalent content.** [Manual](https://www.sec.gov/files/edgar/filermanual/efmvol2-c5.pdf#page=28), [formatting differences](https://www.sec.gov/edgar/searchedgar/aboutedgar.htm).

**Resume:** search whole filings, including ASCII/different exhibit types; verify values/signs, order, tables, footnotes and graphics before substitution. Keep both originals/identities; uncertainty remains pending. Samples cannot clear untested files. [Audit](../../../../../prepare_work/tool_selection_20261004/pdf_twin_audit_20261004/SOL_VERDICT.md).

## Code and evidence to preserve

| Purpose | Location |
|---|---|
| Production downloader / benchmark code | [driver/prepare/get](../../../../driver/prepare/get/); [benchmarks/prepare](../../../../benchmarks/prepare/) |
| Unmerged work and recovery | [handoff](../../../../../prepare_work/tool_selection_20261004/RESUME.md): `code/`, checkpoint archive/manifests, merge inventory and format resume notes |
| Frozen answers, sources and raw labels | [golden-set storage rules](../../../../benchmarks/prepare/golden/README.md); held-out answers remain reviewer-only |
| Downloader closure | [approved repair review](../../../../../prepare_work/repair_20261004/codex_final_review_20261004/CODEX_VERDICT.md); 42,629 OK, 1 unresolved Guidewire ZIP, 3 SEC 404s |

**Before deleting `prepare_work`:** merge selected code/tests; preserve checkpoints, originals, frozen keys, model/version records and regression evidence. **Links are not backups.** Keep experiment runners out of production; preserve unmerged work until explicitly accounted for.
