# Prepare Step: Step 1 · Prepare (reviewed proposal, v5)

*Claude + Codex · 2026-10-01 · v5, consolidating the independently checked reviews, including subsequent Bot 1–2 findings.*

- Evidence: code, read-only database checks, cached originals, saved scripts and official documentation. Provisional or unverified figures are labelled below; converter choice and production accuracy remain untested.
- This is a design update, not implementation or a change to the governing rules. Versions 1–4 are in `~/.claude/projects/-home-faisal-EventMarketDB/backups/runningIdeas/`.

**Reviewers:** reply to each ID with ✅ agree, ✏️ change (say how) or ❌ reject (say why). Add new ideas as `NEW-n`. IDs are stable; 🆕 marks additions since v2.

**Goal:** complete, exact, verifiable evidence for facts and stated causes, ready fast enough to predict.

**Priorities, in order:**

1. prediction first;
2. near-100% accuracy (recall and precision);
3. lowest cost, including the smallest context without losing information;
4. fast to build and to run;
5. minimal code.

**Plus:** tools and services must be ones we can keep using for the foreseeable future (P24).

**Code home:** `driver/` (new, independent of `driver_reference/`).

**Reused code (owner, 2026-10-01):** any existing code we reuse is verified part by part before we rely on it. Example: the later-10-Q cross-check in T1 is kept for now; its script is `scripts/driver_seed/relocate_probe/phase2/m3_candidate_census.py` (exact values only, matches unconfirmed, dollar amounts only).

**Flow:** original files → source-linked blocks → pieces sized for the reader.

**Next actions, one at a time:**

1. **Now — A · Get:** confirmed fixes pass 28 tests and the saved 60-filing sample (3,223 members; P3; [result and work order](StepsPlans/Prepare-A_Get.md)). Step 2 still needs independent inventory/coverage validation; readability remains separate.
2. **Then — compare converters:** define the output checks first; test complete routes against them (P14, T1).
3. **After validation — reuse:** use the same preparation process for future ingestion and a separate historical-cleanup task, while Driver development continues (P19, D14).

**Documentation follow-up:** align [rough_design.md](rough_design.md) and [Notion Prepare](https://app.notion.com/p/3eca0a3f310681ffb36de687666c09f0) with these decisions: converter choice remains open, cover facts stay, and evidence/smaller-read choices are settled. Claude handles Notion edits.

## Facts (checked 2026-10-01; numbers are sample-specific unless "all")

- **F1** The database has Items for 10-K 2,988/2,993 · 10-Q 7,297/7,301 · 8-K 29,591/29,672. They come from the paid sec-api extractor (`redisDB/ReportProcessor.py`). `SEC_API_KEY` is set, but whether it still works is untested. There is no cover-page section. Having Items ≠ complete coverage (F9).
- **F2** Originals on this machine: 1,769 main documents and 13,181 exhibits.
  - The database lists only EX-99 (23,286) and EX-10 (15,765) exhibits.
  - Main-document links: 42,023 HTML, 601 XML (13D/13D-A), 9 missing.
- **F3** Conversion only, Docling 2.131:
  - HTML: 0.16–5.51 s per file, mean 1.61 s (14 files, default settings);
  - PDF route: 13.2–284.7 s per file (20 files, FAST tables, CPU). The earlier "22/62/158 s" were averages by form type.
  - On HTML it found 0 table header rows in 178 tables, and it splits styled spans into separate items ("$10.67" · "4" · ", including:").
  - The saved AES PDF run logged 3 of 173 PDF text fragments dropped from one table. These are not necessarily three financial cells; inspect omissions against the original. Conversion still returned SUCCESS.
- **F4** Contents links reach Items in 11 of 13 10-K/10-Q files. They prove the targets exist, not that the boundaries are right.
- **F5** Tag coverage needs a corrected count. The earlier median 67% (52–81%, 13 files) is provisional: the script counts only `ix:nonFraction`, omitting tagged durations, and excludes single-digit values as presumed footnotes.
  - Withdraw the "17 partly tagged / lowest 50%" figures. Airbnb `0001559720-25-000010` tags 5.3 and 7.2 years through `ix:nonNumeric` (`ixt-sec:duryear`), which that check misses.
  - Genuinely partial tables exist: Snowflake `0001640147-25-000110` has untagged 6.3492 conversion rates beside tagged prices and share counts. The earlier 98–100% aggregated tables per filing.
  - Prose tags (26–649) and text-block tags (28–134) also occur in the sample. Text blocks include policies and tables; they are not a complete numbered-note index.
- **F6** The stored filing text is not safe evidence:
  - tables are flattened;
  - footnotes are glued onto numbers (Darden prints "$10.67" plus superscript "4", meaning "See the 'Non-GAAP Information' below"; the stored text reads "$10.674");
  - there is no cover page;
  - after HTML extraction, our code removes `<...>` from already decoded text, deleting content between financial inequality signs (`ReportProcessor.py:526,594`). Coty `0001024305-25-000015`: 100,822 normalized characters before cleanup → 23,502 stored; the production path reproduces the stored text exactly (76.7% removed);
  - replaying all 13,181 cached exhibits found 309 affected by this regex. Of these, 75 EX-99 files across 74 earnings filings lost >10% of non-whitespace text. This is a cache count, not a database-wide loss rate;
  - the same cleanup runs on 13D/6-K and other secondary filings; their losses remain unmeasured;
  - whitespace cleanup removes line breaks: none of all 38,946 stored exhibits contains one.
- **F7** Stored news is cleaned: HTML stripped, characters normalized, punctuation spacing changed and bodies capped at 3,000 words. Across all 348,670 stories, 188 have the truncation signature and 35,249 have empty bodies (10.1%; the earlier 9% was sample-specific).
  - Transcript pairing drops OPERATOR/UNKNOWN roles and executive segments within Q&A before the first accepted analyst question. Malformed segments and the graph writer's short-exchange filter are further loss paths. When pairs exist, neither full Q&A nor full-transcript fallback is stored. Lost-fact frequency is unmeasured.
  - Existing processed text has unverified completeness. A Benzinga key is configured and `pit_fetch.py` supports historical retrieval; working access and recovery of original versions remain untested. Preserve raw provider payloads before processing (P3).
- **F8** The other bot's table rules, re-run:
  - 134 of 148 tables (those with ≥20 numeric cells) had a label on every emitted value, and 95.1% of emitted values were labelled;
  - 4 tables produced no output, and nothing shows that every source value survived.
- **F9** 32 10-Ks have a short MD&A section that only points elsewhere:
  - 1 names Exhibit 13 (Carnival, whose exhibit isn't stored); 22 mention the "Annual Report"; 3 have no exhibit in the database at all.
  - The examples point to later pages of the same file or to an annual-report exhibit.
  - `_get_exhibits()` excludes EX-13. IBM `0000051143-24-000012` confirms a missing 4.7 MB EX-13 annual report; the claim that all 22 annual-report references use EX-13 is not verified. [IBM index](https://www.sec.gov/Archives/edgar/data/51143/000005114324000012/0000051143-24-000012-index.html)
  - Query: 10-K `HAS_SECTION` where the name starts 'Management', size < 3000, and the text contains 'incorporated' and 'reference'.
- **F10** EDGAR provides a document index and a complete-submission `.txt` containing packaged documents, including encoded binary attachments. T5 compares inventory coverage and decoding; technical support files need not become reader prose.
- **F11** Average absolute daily move where returns exist (all filings): earnings 8-Ks (Item 2.02 + EX-99) 7.0%, 10-Q 4.8%, 10-K 3.7%. This shows association, not that the filing caused the move.
  - 683/10,995 Item 2.02 filings have no stored exhibit. CVS `0000064803-23-000003` and Southwest `0000092380-23-000004` contain financial disclosures in the body; missing exhibits alone do not prove this for all 683.
- **F12** 🆕 204 exhibit text fields contain decoded PDF data across 129 filings: 181 EX-99 in 120 filings and 23 EX-10 in 10. AMG's stored value includes replacement characters; it is not an intact PDF to reconstruct.
  - AMG `0001004434-23-000015` has both `amgq12023ex991.htm` and `courtesy.pdf`, labelled EX-99.1. `_get_exhibits()` keys by type, so the PDF displaced the HTML; graph IDs also use exhibit type (`secReports/sec_schemas.py:192`, `neograph/mixins/report.py:774`).
  - 124 filings have only PDF links in the stored exhibit map. That does not prove their EDGAR filings lack HTML. PDF-only exhibits also exist; D14 must support both cases.
  - 41 of the PDF EX-99 records belong to 27 earnings 8-Ks. The earlier 38-PDF count was a July locator sample, not the whole database.
- **F13** 🆕 Live ingestion is off: `event-trader` is scaled to 0/0 (`report-enricher` runs 1/1). The real-time filing feed is sec-api's paid stream (`secReports/sec_websocket.py`).
  - EarningsCall: subscription lapse recorded as 2026-05-03 (`CLAUDE.md`); the local `.env` key remains disabled. Current provider entitlement was not re-tested.
  - Today, exhibits and secondary-filing text are downloaded straight from SEC (free). Items, XBRL statements and the new-filing feed come from sec-api (paid).
- **F19** 🆕 History recovery without subscriptions:
  - SEC filings: yes, free, since EDGAR keeps every original.
  - News: needs a working Benzinga key (untested).
  - Earnings calls: originals are not stored (68 of 9,608 full texts; raw copies are deleted after processing) and EarningsCall has lapsed, so they need a subscription or another source.
  - Check later, as needed (owner).
- **F14** 🆕 XML 13D forms hold substantive prose. A stored 13D contains a "non-binding proposal to acquire all of the outstanding shares… $7.22 per share in cash".
- **F15** 🆕 Tool upkeep, last 12 months (PyPI and GitHub):

  | Tool | Releases | Last release | Backing |
  |---|---|---|---|
  | Docling | 92 | 2026-10-01 | LF AI & Data Foundation |
  | edgartools | 158 | 2026-09-26 | 1 maintainer |
  | sec2md | 22 | 2026-03 | 1 maintainer |
  | doc2dict | 13 | 2026-02 | 1 maintainer |
  | sec-parser | 0 | — | README: "no longer maintained" |

  These codebases are MIT-licensed; model licences are separate. Release counts do not prove accuracy or future support. sec2md is Alpha and has an [open missing-output report](https://github.com/lucasastorian/sec2md/issues/4) against 0.1.22; not reproduced here on the selected version. doc2dict describes itself as early-stage.
- **F16** 🆕 Docling's saved JSON is 1.9–12.4× the size of the original HTML (14 files).
- **F17** 🆕 Paragraphs repeat across filing documents. [Script archived](/home/faisal/.claude/projects/-home-faisal-EventMarketDB/backups/runningIdeas/repeats_20261001.py): whitespace-normalized paragraphs ≥60 characters, counted once per file. It does not save its directory-order-dependent sample. Keep the percentage omitted until the exact sample/results are archived and verified; token/cost savings remain unmeasured.
- **F18** 🆕 Withdraw "35–60% of 8-K money figures later get a tag": the cited study measured transcripts/news, not 8-Ks. July's separate 40-fact 8-K census found later same-value candidates for 28/28 money facts, 0/10 decimal-form facts and 0/2 counts; **zero identities were proven**. This neither certifies 28 matches nor proves percentages/counts cannot be tagged. Rulebook warning corrected 2026-10-01.
- **F20** 🆕 Docling's table model works on PDF pages. The printed-PDF route (2.131, FAST tables, CPU) found header rows in 96–99% of tables with numbers: 10-K 465/484 · 10-Q 438/452 · EX-99.1 103/104. The HTML route found 0 of 178. Detected ≠ correct: the labels are ungraded. Cost: 13–285 s per file (F3).

## Proposal

- **P1** ✏️ **Complete disclosure coverage is required.** Inventory every file; prepare disclosure content and retain its supporting assets/metadata. Samples decide how and in what order, never whether.
  - Order: text by plain code first; then OCR or vision only where needed, as explicit stages.
  - Anything not yet prepared stays "not read", never "no facts" (rule 8.14).
- **P2** ✏️ Scope: all SEC filings, including XML prose and PDF exhibits (F14). News/transcripts reuse readable text where suitable, with completeness checks (F7).
- **P3** ✏️ Get:
  - plain code only, unattended, no AI;
  - **package first (owner approved, 2026-10-01):** acquire the complete-submission `.txt` and inventory every member. The index and bundle links already exist (`linkToHtml`, `linkToTxt`); compare routes in T5, not through routine double downloads;
  - identify files by accession + filename; keep sequence and exhibit type as metadata. Never collapse files sharing an exhibit label (F12);
  - use local copies or SEC with the approved User-Agent (D12). This campaign shares **5 requests/second** across workers, including file lists and retries, within SEC's overall 10/second cap (owner approved, 2026-10-01). Any HTTP 403 stops the whole campaign; a second email adds no capacity;
  - preserve each original as lossless gzip plus manifest/receipt; decode files once when needed (D15). Verify accession/form and membership among header company IDs, framing and safe decoding. Record stated/actual counts without requiring equality; framing alone cannot detect a whole omitted member. Compare **every filing** with SEC's own file list, including all 42,633 in the planned full run. Deep file validation and reference interpretation remain later checks;
  - cache packages and SEC file lists; reuse selected, hash-verified versions before downloading. Fully cached replays make zero requests; refresh is explicit. Preserve separate versions; corrupt caches stop without silent repair. Preserve original news/transcript payloads before cleaning, truncation or speaker filtering;
  - record source/version, publication and retrieval times, readiness and every gap. Later versions must not become earlier prediction evidence.
- **P4** ✏️ EX-10 contracts and images are included; samples (T6, T7) set their method and priority.
- **P5** ✏️ Formats:
  - HTML by structured parsing;
  - retain applicable styles and distinguish hidden XBRL data from visible prose; `display:none` alone is not a reason to discard source evidence. The 111-filing sample's company HTML uses inline styles only; this is not a restriction on future filings;
  - text PDFs by text, layout and table extraction;
  - OCR/image reading for needed regions, including images inside otherwise readable HTML/PDF pages;
  - XML forms: structured fields and narrative prose, including their order and references.
  - Keep the original PDF or image as evidence and link extracted content to its location.
- **P6** ✏️ Items:
  - find them in the original (Item headings, contents links), with database Items only as a free cross-check;
  - follow incorporated references available at the event time. Keep the target's actual file/path and separately link the referring Item; do not relabel its physical location (F9);
  - keep text outside Items (the cover page) as blocks;
  - mark uncertain headings, never guess.
- **P7** ✅ Subheadings come from styling or the T1 winner. Each block carries its path (Item › subheading).
  - 🆕 Idea: a small pre-step marks PART, "Item N." and bold lines as heading tags, so Docling's own outline and heading paths work. OKE 10-Q: 1 → 42 headings, and every chunk got a path. Item lines laid out as one-row tables were missed. T1 tests it.
- **P8** ✏️ Tables:
  - keep exact cells with coordinates, row labels, header paths, unit and scale lines;
  - keep footnote markers apart from numbers and link each marker to its footnote text, carrying both into the piece (Darden "4" → non-GAAP);
  - keep the raw grid when labels are uncertain.
- **P9** ✏️ Keep SEC tags and full context (period, unit, scale, sign, dimensions, transformation) on their source values, including durations. Flag fully tagged tables only after checking every relevant cell (F5).
- **P10** ✅ Keep cover facts, footnotes and captions. Drop only repeated page banners and page numbers.
- **P11** ✅ Owner-approved smaller reads: read every required block across calls sized to the full budget (instructions, context, answer space).
  - Pack small neighbouring Items; split large ones at subheadings.
  - Split oversized tables into row groups with repeated headers, and text at sentence boundaries.
  - If a single row, sentence or required context still exceeds the limit, use a reader with sufficient context or mark it unresolved. Never truncate it or count it as read.
  - Could miss connections between distant sections; validate this when creating the final design (D10).
  - 🆕 Not final (owner): piece size and shape depend on the task (e.g. JEV gets one question on a small passage). Details are decided per task later.
- **P12** ✏️ Carry referenced notes, definitions and footnotes across Items/exhibits; tags do not resolve every reference. Include them in the budget. Facts and stated causes may span blocks; test that splitting preserves their connections.
- **P13** ❌ Dropped: the stored text isn't the record (F6). It remains an optional compatibility check.
- **P14** ✏️ Minimum output, required before comparing converters (pass/fail gates):
  - evidence anchors tied to original file fingerprint + source location; never converter list positions alone;
  - versioned block/cell IDs with retained mappings, so upgrades do not invalidate saved quotes;
  - reading order, exact text/cells and full tag context;
  - footnote markers separate from numbers and linked to their text;
  - generated display text separate from exact evidence;
  - nothing lost: every visible character is in a block or the clutter log, and unread files are counted.
- **P15** ✏️ Grade each number's links: value, sign, unit, scale, period, row, column, segment, footnote. Tags and later filings are cross-checks; answers come from independently checked originals.
- **P16** ❌ Dropped (matching against the stored text). Replaced by the P14 source-location checks.
- **P17** ✏️ Output: portable, frozen ordered blocks with original file/version, fingerprint, converter version/settings and P3 timing/status. Assemble pieces at read time. Choose the compact format after T1; reader tokens, not saved JSON bytes, measure reading cost. Parser fixes create new versions without rewriting saved evidence references; changing reader budgets alone does not.
- **P18** ✏️ Run bounded-parallel on the worker node (minisforum2), not this control-plane machine. New filings go before the backfill (rule 8.16). Measure arrival-to-ready; speeds are targets.
  - No numeric speed target is agreed. Before live rollout, set an owner-approved earnings-filing publication-to-ready target using T5 timing/burst results, including discovery delay.
  - 🆕 Option (owner): run Docling on the Mac's GPU. Only its layout model uses the GPU; Docling forces its table model onto the CPU on Apple GPUs, and the Mac is shared with local Qwen. First time 3 filings on minisforum2 vs the Mac (Step 7).
- **P19** ✅ Owner-approved: build and validate one preparation function for future ingestion first.
  - Then reuse it for a separate historical-cleanup task, runnable by other bots while Driver development continues (D14).
  - Cover every observed failure class (T2) with explicit, deterministic repair rules and checks. Reruns must not duplicate or degrade data. Repair only verified cases; log unresolved cases without guessing.
  - Backfill, live rollout and consumer migration stay separate. Preparing files or restarting ingestion does not switch consumers automatically.
  - The existing predictor will be revamped; migrating it is not a prerequisite for Driver development. During that work, explicitly migrate and test the 8-K packet and warmup paths sharing `_fetch_8k_core()` in `scripts/earnings/builders/eight_k_packet.py`.
- **P20** ✅ Owner-approved: originals (fingerprinted) + frozen blocks are the evidence record.
  - A fact is a `DriverUpdate`. Keep its `FROM_SOURCE → Report` link and quote; add a location-reference property identifying the original file/version and exact passage or supporting table cells. Store each original once.
  - Original PDFs/images may support facts when extraction is checked against them. Generated labels or a rendering of HTML do not replace original evidence.
  - Rules updated 2026-10-01: 1.17 (original files as evidence) and the 3.3 field table (`source_location`, 25 fields).
- **P21** ✏️ Keep every repeated occurrence. Reading identical paragraphs once is a later optimization (F17; savings unmeasured).
- **P22** ✅ Re-join inline fragments into one paragraph, keeping footnote markers as separate tokens (F3).
- **P23** ✏️ Build order: coverage and evidence first → earnings 8-Ks (body + exhibits, including press releases) → 10-Q → 10-K → the rest (F11). Include referenced Items and images; EX-99.1 alone misses body-only disclosures. A7's first pilot was Darden's press release (F6).
- **P24** 🆕 Upkeep: prefer maintained, self-run open-source tools with suitable licences, predictable cost and a replacement path; neither MIT nor a free backup is mandatory. Keep portable output behind a small interface. Retain tested code and model weights/configuration with versions, checksums and licences; test upgrades. Maintaining a fork is a last resort. Future support is not guaranteed.
- **P25** 🆕 Multiple versions: preserve each file's identity and original. Prefer the source HTML when a PDF is verified to duplicate it. Code does the check, not AI: every number and word of the PDF must appear in the HTML in order. The exhibit label alone proves no equivalence. Extract unique PDF content too. Re-fetch intact originals for corrupted records; validate extraction before marking readable (F12).
- **P26** 🆕 Services:
  - keep sec-api's real-time feed and XBRL calls for now;
  - replace only its section extractor if independent comparison shows better results under our priorities, all required checks pass and consumers migrate; otherwise retain it (D11);
  - fixing the predictor's input also means replacing our flattening exhibit code (F6);
  - savings are unproven;
  - evaluate SEC's own feeds as a fallback only after measuring coverage, reliability and arrival delay. Its submissions API's typical sub-second server processing is not our end-to-end discovery time under polling/rate limits. [SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)

## Tests

- **T1** ✏️ Screen maintained existing tools first: prioritize Docling and edgartools; include sec2md/doc2dict as experimental contenders. sec-parser is excluded (F15). Build custom conversion only for demonstrated gaps.
  - 🆕 Owner: no custom table code unless every out-of-the-box route fails. HTML routes come first (Docling, edgartools); the printed-PDF route (F20) is the fallback. Small non-table adapters stay allowed: the P7 heading pre-step, and linking evidence back to the original HTML cells (P20).
  - Screen each complete route (converter + source/tag preservation) against P14, then score passing routes. Raw Docling HTML alone is insufficient; do not pre-exclude a route that can meet the contract with small additions. Choose the smallest sufficient combination; one tool need not win every format.
  - Emphasize press releases, but stratify by form, format and layout and report each separately. No arbitrary requirement that half the sample be press releases.
  - Rank by preserved text/cells, structure and P15 links, scored by code against the checked answer key, including omissions; then reader tokens, total time/cost and upkeep (P24). Saved size and code length are secondary. AI fact/cause extraction is tested only in T4; T1 makes no AI-reader calls.
  - Answer key: independently checked originals, with at least 300 untagged cells spread over many tables, explicitly including percentages, ratios and counts; lock it before any run. Tags and later 10-Q tags are cross-checks only (F18).
  - Final round on fresh filings; agreement between helpers alone isn't proof.
  - For D11, compare against the existing sec-api section extractor: boundaries, coverage and correctness first, then time/cost. Resolve any coverage or correctness regressions before switching.
- **T2** ✏️ Scale check across every observed form/format category and varied years/layouts. Include repeated exhibit labels, HTML/PDF twins, PDF-only exhibits, XML prose, positioned HTML, mixed text/images, damaged inputs and oversized rows/sentences/references. Regression cases: Coty's inequality-sign deletion, body-only earnings disclosures and AES's dropped PDF text fragments. Count accepted, unresolved and failed inputs separately; converter SUCCESS is insufficient.
- **T3** ✏️ Completeness of news and transcripts:
  - news: 3,000-word cuts, empty bodies and a check of historical retrieval access; compare recovered originals for tables and other cleaning losses, keeping later edits separate;
  - transcripts: compare all original segments with stored output across speaker filtering, Q&A boundaries/pairing, malformed segments and fallback paths—not only OPERATOR removal.
- **T4** ✏️ Reader comparison with one fixed reader: stored text vs prepared blocks.
  - Count correct facts, stated causes, misses, errors, tokens and time; also report tokens spent on fully tagged tables, to reconsider rule A1 if large.
  - During final design, test references and stated causes spanning distant sections (P11).
  - 20 development files, then held-out ones; needs Phase 6 approval.
  - This measures extraction benefit; improvement in predictions requires a separate test.
- **T5** ✏️ Get route on 50 filings: the complete submission `.txt` vs index + files. Measure end-to-end retrieval plus preparation, including slow cases.
  - Check SEC rate-limit impact: requests per filing, throttling/retries and arrival-to-ready delays during filing bursts and concurrent historical cleanup. Verify new filings retain priority under the shared limit (P3, P18).
- **T6** ✏️ EX-10 sample: about 20 contracts. Sets method and priority, not inclusion.
- **T7** 🆕 Pilot image handling on about 20 varied sources: scanned decks, native PDFs and images/charts inside readable documents. Grade correct and missed facts against the originals, plus processing time; verify recovered content reaches reader pieces.
- **Stats:** 0 errors in 300 bounds the rate under 1% (95%) only for that cell population with independent sampling. Spread the sample across tables.

## Decisions (owner)

| ID | Question | Recommendation | Why |
|---|---|---|---|
| D1 | Run T1? | ✅ In scope: converter/content checks; AI-reader tests stay in T4 | Docling misses table labels (F3) |
| D2 | EX-10 contracts? | ✅ Approved: included; T6 sets method and priority | Coverage is required (P1) |
| D3 | Images? | ✅ Approved: included; T7 sets method; built after text | Coverage is required |
| D4 | The record? | ✅ Approved: originals + frozen blocks (P20) | Keep the Report link and quote; add the exact evidence location |
| D5 | Ingestion? | Reuse the validated preparation function; deploy separately (F13) | Permanent preparation fix first (P19) |
| D6 | Is table evidence the set of exact cells with coordinates? | ✅ Approved, through the DriverUpdate location reference (P20) | Identifies where the fact is supported within its filing |
| D7 | Skip the reader for fully tagged tables? | ✅ Approved: keep AI reading these tables for now; test before skipping (T4) | Tags do not capture all context and explanations; Part A1 keeps the full source text as the baseline |
| D8 | 13D/13D-A XML forms? | ✅ Approved: included (fields, narrative prose and exhibits) | Acquisition offers (F14) |
| D9 | Can text read from a PDF or picture be evidence? | ✅ Approved for originals, with checked extraction and exact source references | Rule 1.17 updated 2026-10-01; the existing Report link stays |
| D10 | Rule 8.10 ("whole event")? | ✅ Approved: smaller reads, covering the whole event | Validate distant-section connections during final design; rule 8.10 updated 2026-10-01 |
| D11 | sec-api? | ✅ Conditional: replace only the section extractor when independent tests demonstrate better results under our priorities and all required checks pass; keep the live feed | No unresolved coverage/correctness failures; migrate consumers first (T1, P26). Superiority is not yet established |
| D12 | SEC User-Agent contact? | ✅ Settled: `EventMarketDB faianjum@gmail.com` | Owner supplied; shared request limit stays unchanged (P3) |
| D13 | Adopt the upkeep rule (P24)? | ✅ Settled: adopt P24 | The owner's requirement |
| D14 | Repair PDF data and deleted release text (F6/F12)? | ✅ Approved: separate cleanup after preparation is validated, while Driver development continues | Reuse tested rules (P19); the existing predictor's revamp does not set the priority |
| D15 | 🆕 Where and how to store originals and their records? | Approved SEC representation: lossless compressed package plus manifest/receipt; unpack on demand. Production location and any shared index (e.g. SQLite) remain open after T5 | Avoid permanent duplicate bytes; current implementation has one writer per output directory |
| D16 | 🆕 Open (owner 2026-10-02): after the swap, does the new prepared text **replace** the old flattened section/exhibit text under each existing Report node, or sit **beside** it? | Decide at Step 5 with D15; applies to live ingestion and historical cleanup alike (Step 9). Report nodes and their links stay either way; the old text stays restorable | Avoids an unplanned overwrite of existing Neo4j content (Step 9 repair rule 3) |

## Sources and review trail

Current qualified findings above supersede earlier reviews. Detailed review logs remain in the v2–v5 backups.

- **Licences (checked 2026-10-01):** candidate codebases are MIT-licensed; check model licences separately. EdgarTools can run locally against SEC with a declared identity, without a paid hosted-service account. P24 governs selection.
- Docling: https://github.com/docling-project/docling · pipeline options https://docling-project.github.io/docling/reference/pipeline_options/ · chunking https://docling-project.github.io/docling/_generated/examples/advanced_chunking_and_serialization/ · enrich pictures https://docling-project.github.io/docling/_generated/examples/enrich_doclingdocument/ · 2.132 https://github.com/docling-project/docling/releases/tag/v2.132.0
- edgartools: https://github.com/dgunning/edgartools · https://edgartools.readthedocs.io/
- doc2dict: https://github.com/john-friedman/doc2dict
- sec2md: https://sec2md.readthedocs.io/ (PyPI: https://pypi.org/project/sec2md/) · reported missing output: https://github.com/lucasastorian/sec2md/issues/4
- sec-parser (not to be used; unmaintained): https://github.com/alphanome-ai/sec-parser
- SEC fair access (≤10 requests/s across all machines; declare a User-Agent): https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
- SEC request limits and IP throttling: https://www.sec.gov/about/privacy-information#internet-security-policy
- Example indexes:
  - Darden: https://www.sec.gov/Archives/edgar/data/940944/000094094426000005/0000940944-26-000005-index.html
  - AMG (HTML + courtesy PDF): https://www.sec.gov/Archives/edgar/data/1004434/000100443423000015/0001004434-23-000015-index.html
- XBRL validation limits: https://www.xbrl.org/the-standard/what/key-concepts-in-xbrl/validation/
- Sampling bounds (NIST): https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm
- Local:
  - [Dockling/docling.md](Dockling/docling.md) and `Dockling/test_scripts/`;
  - cache in `scripts/driver_seed/relocate_probe/{inline,exhibit}_html_cache/`;
  - [Earlier review decisions](/home/faisal/.claude/projects/-home-faisal-EventMarketDB/backups/runningIdeas/runningIdeas.v3.before_codex_review_20261001.md);
  - subsequent review evidence: [REDESIGN_SCRATCHPAD.md §9g](Archive/REDESIGN_SCRATCHPAD.md#9g-roughmd-3-reviews-of-v2-checked-against-runningideasmd-v3-other-session-1254-2026-10-01-read-only), qualified by this review;
  - [Bot 2 verification and count queries](/home/faisal/.claude/projects/-home-faisal-EventMarketDB/backups/runningIdeas/bot2_verification_20261001/VERIFY.md), with `cleanup_scan.json` beside it;
  - July candidate census: `../WIP/UniversalLocator_ReviewRecord_2026-07-18.md:3945` (not proven fact matches);
  - [rough_design.md](rough_design.md).

---

## Parallel-agent execution plan

*2026-10-01 · consolidated, independently reviewed, then condensed without changing scope.*

**Goal:** complete, correct, source-linked evidence, ready quickly enough to explain moves, learn and predict.

**Scope:** originals → conversion → structured blocks → reading pieces → checks → ingestion reuse and historical cleanup. Later Driver reading/naming/judging and a runtime manager AI remain outside this plan.

**Execution:** plan all steps now; run only the owner-approved step or batch. Review each step by default. Within an approved batch, the coordinator checks prerequisites and handles routine work; the owner reviews before scope expands.

This section grants no new approval for agents, downloads, conversions, paid tests, repairs, deployments or other implementation.

### 1. Authority and settled decisions

Follow the owner's latest instructions, repository instructions and the [proposal](#proposal) and [approved decisions](#decisions-owner) above. Work orders cannot override them. Older `rough_design.md` and Notion Prepare contain superseded assumptions.

**Priorities:** prediction usefulness → recall/precision → total cost and smallest sufficient context → fast build/run → minimal code. Missing evidence cannot buy a cheaper score.

| Area | Required behavior |
|---|---|
| Evidence | Preserve originals and frozen blocks; references identify original file/version and exact passages/cells. Verify PDF/image extraction against originals, including images inside readable documents. Printed HTML is not original evidence. |
| Coverage | All disclosure files, contracts, XML prose, cover facts, footnotes and captions. Inventory technical support files without turning them into reader prose. |
| Reading | Smaller reads cover the whole event; test distant-section connections. Keep reading tagged tables initially: tags do not replace context. |
| Acquisition | Unattended plain code, no AI; preserve raw payloads before processing. SEC identity: `EventMarketDB faianjum@gmail.com`. Limits are shared; another email adds no capacity. |
| Services | Keep sec-api's live feed and XBRL calls. Replace section extraction only after independent superiority checks and consumer migration. |
| AI billing | Subscription only; JEV is the sole possible paid API exception (§6). |
| Order | Validate permanent preparation first; then repair history alongside Driver development. The separate predictor revamp does not set this priority. |
| News/call history | Provider-access checks and recovery are deferred until needed (F19); gaps remain explicit. |
| Tools/tests | Maintained tools, portable output, verified reuse; no MIT-only, free-only or mandatory-fork rule. T1 uses code and checked originals; AI fact/cause extraction belongs to T4. |

**Unsettled:** D15's production location and shared index remain open after T5; D16 (replace old Neo4j text in place, or keep beside) is decided at Step 5. Compressed originals plus manifest/receipt are approved; the experimental directory does not choose the production location.

Before dependent implementation, reconcile approved evidence changes with rule 1.17, smaller reads with 8.10, and the DriverUpdate location-reference contract. Do not reopen those owner decisions. Other unresolved rules stay open; this plan neither activates sources nor changes Fiscal/Core ownership. Applicable Phase 6 conditions include AI labelling, not just reader tests.

### 2. Team and review control

Staff independent approved jobs within actual account/machine limits; **no fixed four-agent cap**.

| Role | Responsibility |
|---|---|
| Coordinator | Version instructions/interfaces, assign ownership, integrate and report. |
| Builders | Separate components or source partitions; first filing needs one builder. |
| Independent checkers | Establish expected answers from originals, inspect delivered code and replay it. |

Claude/OpenAI may fill any role. Different providers do not guarantee independence. Nobody accepts their own unchecked work; a coordinator who builds needs another checker. Replay accepted code rather than duplicate every implementation; use a second small implementation only for a critical independent check.

Agents build/debug general rules. Bounded code performs bulk downloading/conversion. Add workers for ready independent jobs; reduce concurrency when contention or coordination slows delivery.

At each agreed checkpoint, show:

1. One real example of the completed behavior.
2. Passed/failed/unresolved counts and evidence.
3. Measured cost/time; after the first small run, remaining duration ranges with assumptions, separating review waits.
4. Proposed next scope and assignments.

Tests permit only already-released dependent work. Routine fixes stay with the coordinator; scope/quality/cost tradeoffs stay with the owner.

### 3. Complete sequence

```text
0 Freeze work order
  ├─ 1 Get one filing → 2 Extend acquisition
  └─ 3 Prepare checks/key (may overlap 1–2)
        ↓ acquisition and checks accepted
      4 Compare converters → 5 Save blocks → 6 Assemble pieces
        → 7 Replay, scale and timing
              ├─ 8 Approved AI-reader comparison
              └─ 9 Ingestion reuse and historical cleanup
```

Steps 1–3 overlap only within an approved batch: Step 3 uses verified cached originals, frozen hashes and agreed records; the full key must be accepted before Step 4. Steps 8–9 may overlap after Step 7 if released together. Historical repair need not wait for the entire Driver pipeline.

All steps use the common records (§4), sampling rules (§5), execution rules (§6), regressions (§7) and handoff (§8). Each **Review** below is the default owner checkpoint; approved batches use §2.

#### Step 0 — Freeze the first work order

**Assignments:** coordinator prepares the contract/package; workers independently check reusable acquisition code and cached fixtures/failures; checker reviews the contract. No converter/reader work starts here.

- Hash current plans/rules/instructions. Freeze the code commit **plus included working/untracked files**: this planning file is currently untracked, so HEAD alone omits it.
- Freeze requested source identities/URLs; retrieved byte hashes freeze downstream inputs.
- Assign files/components; define records (§4), first inputs, tools, access/billing, host and resource limits. Exclude secrets.
- Verify a route from the current SSH host (`minisforum`) to worker `minisforum2`: SSH or Kubernetes execution, input transfer and output retrieval, with hashes checked. Record working commands; unavailable access blocks dependent heavy jobs, not unrelated approved work.
- Fill §8, marking missing interfaces/commands as deliverables rather than runnable instructions.
- Deliver a fingerprinted work order, named fixtures, ownership and status table. Keep instructions here until dispatch needs separate files.

**Pass:** another bot knows its exact scope, inputs, output, checks and stop. Coordinator resolves interfaces before dispatch; genuine owner choices get one concise recommendation.

**Review:** release the first implementation scope; Steps 0–1 may be grouped by the owner.

#### Step 1 — A · Get one complete filing

**Entry:** accepted acquisition contract and fixed identity. Proposed first fixture: **AMG `0001004434-23-000015`**, whose HTML and PDF share EX-99.1. It is a regression, not coverage proof.

**Assignments:** one builder implements inventory/retrieval/storage/cache; checker independently verifies inventory/bytes and good/damaged fixtures. Coordinator handles shared choices, potentially also building. Spare agents may start Step 3 only within released scope.

1. Acquire the complete-submission package through one download owner, unattended in plain code; no routine index or individual-file requests.
2. Check expected accession/form, company membership and header time/framing. Record stated and actual counts; unequal counts are valid. Preserve every member through the compressed original, with exact filenames, hashes and package byte ranges; decode once on demand.
3. Unpack safely and publish atomically; verify supplied cache hashes and retain separate source versions. Corrupt caches stop explicitly, without an automatic repair framework.
4. Emit one compact manifest and a separate retrieval receipt. Format hints may remain unknown; deep validity, supporting references and readability are preparation duties.
5. Keep bounded respectful HTTP behavior and deterministic replay. No reference crawler, schema framework, AI, database writes or ingestion changes.

**Pass:** independent package/member identity agreement, intact bytes, no filename/label overwrite and identical offline output; wrong identity, truncated packages and returned error pages are detected. Acquisition success does not certify file readability or resolved external references. The [package-first work order](StepsPlans/Prepare-A_Get.md) supersedes the earlier Step 1 contract.

**Review:** filing inventory plus one source record. Checker accepts Step 1 before expansion, including within a batch.

#### Step 2 — Extend acquisition

**Checked 2026-10-02 UTC:** [implementation and evidence](StepsPlans/Prepare-Step2.md).
50 filings across 12 forms passed inventory checks; compressed-only replay made zero requests.
Scale follow-up: all 502 filings/23,958 files match the independent extractor;
all five reviewed fixes pass. The planned full run checks every SEC file list.
External reference resolution and unavailable news/call originals remain explicit limits.

**Entry:** accepted Step 1 and frozen expansion manifest.

**Assignments:** SEC worker runs T5's **50-filing** retrieval comparison; news/transcript worker checks local ingestion boundaries and available copies (T3); checker audits coverage/cache/retries/versions; coordinator owns shared downloads/records.

- Cover earnings 8-K bodies/exhibits, 10-Q/K, amendments, XML prose, contracts, EX-13, native PDFs and embedded/supporting images.
- Reuse selected, verified packages and SEC file lists before downloading; cached replays make zero requests. Share **5 SEC requests/second** across the whole campaign, including retries; **any 403 stops the whole run**.
- Compare every package with SEC's own file list to detect missing company documents. Account separately for generated viewer/support files. Compare routes on the **same originals**: requests, bytes, gaps, failures and retrieval time. Full preparation timing is Step 7.
- Follow explicit relevant references only; preserve target file/date and referring location. Record ambiguity/unavailability; avoid unbounded crawling and later evidence.
- Preserve raw news/call payloads before cleaning, truncation, segmentation or speaker filtering. Audit every transcript loss path; compare available originals.
- Separate originals from processed-only copies. Historical access/recovery stays deferred (F19). When needed, use an approved access/budget job and verify publication versions; later edits cannot repair earlier prediction evidence. Deferral neither blocks unrelated SEC work nor proves recovery impossible.

**Pass/deliver:** manifests, outcome ledger, route comparison and source-specific gaps; every expected file/payload and observed acquisition category accounted for. Successful averages/populated fields cannot conceal missing evidence.

**Review:** acquisition behavior and converter-test scope; unavailable news/call originals remain open items.

#### Step 3 — Freeze checks and independent answers

**Work order:** [Prepare-Step3.md](StepsPlans/Prepare-Step3.md).

**Entry:** agreed records and verified originals. May start from fingerprinted cached files during Steps 1–2 if released together; extend as remaining originals are verified. Freeze the full key before converter scoring. AI-labelling approvals still apply.

**Assignments:** one builder creates preservation checks/commands; independent labellers/checker work blind to each other's answers and candidate outputs; coordinator resolves differences from originals and gets its own contributions independently checked.

1. Lock source manifests/locations. Establish expected text, cells and structure from originals, inspecting renderings when markup is insufficient.
2. Calibrate on known examples; agreement is a prerequisite, not certification.
3. Freeze **≥300 untagged cells** across tables/source types. Before selection, specify numeric minimums for percentages, ratios, counts and distinct tables/filings, with coverage/risk rationale. Missing/unmet minima fail the job. No unsupported “40%” quota or five-cell-per-table cap.
4. Record exact value, row/header support, printed period, unit/scale, footnote references and location; retain genuine ambiguity. Include paragraph order, section boundaries, cover text, images and references: cells alone cannot prove document coverage.
5. Separate development from fresh held-out cases; fixes consume a held-out case into development.
6. Challenge the checker with real positives and mutations: deleted/changed digits, paragraphs/cells, swapped headers/order, joined footnotes, dropped images/tags and broken source references.
7. XBRL/later filings are cross-checks, not answer keys. Verify `m3_candidate_census.py` part by part before reuse; equal values do not prove identity.
8. Apply qualification/authorization to extra model-backed labelling/vision; bot agreement is insufficient.

**Pass:** good cases pass, planted faults fail the intended checks, disputes have source-based resolutions. A shared parser is not an independent oracle. Sampling limits are in §5.

**Review:** original-to-answer example and demonstrated checks; no mandatory “owner labels 30 cells” task.

#### Step 4 — B · Compare conversion routes

**Entry:** accepted checks, frozen development inputs and independent answers.

**Assignments:** separate Docling and EdgarTools builders; checker scores/inspects omissions; coordinator selects the smallest sufficient combination. Screen sec2md/doc2dict only for a named gap or credible simplification; exclude unmaintained sec-parser.

- Pin verified tool/dependency/environment/model versions and settings (§6). Test **converter + source/tag preservation**; retain raw output to distinguish converter from adapter errors.
- Preserve text, cell grids/spans, visible order, covers, footnotes, full tag context and content outside Items. Start with HTML where suitable; printed PDF is a measured fallback. Include P7's heading-tag pre-step as an unproven adapter candidate; check source mappings and missed headings inside one-row tables.
- Include **20 contracts (T6)** and **20 varied sources (T7)**: native PDFs, scans/slides, mixed text/images and charts. These tests determine method/priority, not inclusion. Check image content/locations in conversion here; Step 7 checks blocks and reading pieces.
- HTML/PDF equivalence requires text/numbers **and** row/column, period/unit, footnote, image/caption relationships. Matching word order is insufficient. Preserve both; process both when unresolved and grade unique content against its own original. P25's text-order check is preliminary; apply the relationship checks in P8/P15 before skipping duplicate reads.
- Write custom code only for demonstrated gaps; report upkeep/complexity without an arbitrary 300-line cap. Disambiguate repeated source matches structurally; greedy text matching cannot establish exact locations.
- **T1 makes no AI-reader calls:** code scores against the checked key. Fact/cause extraction testing is Step 8.

**Pass/select:** required preservation first, then reader tokens, total cost/time and upkeep. Count omissions/wrong associations, not just emitted labels. Confirm on fresh held-out sources; known coverage/correctness regressions block the affected route. Format-specific winners are allowed; unsupported content needs a tested fallback before complete-coverage claims.

**Review:** same real table/passage through each route, quality separate from cost/time; select routes without switching live services.

#### Step 5 — C · Save structured blocks

**Entry:** accepted routes and preservation requirements. Choose the compact block format here; the test contract does not prescribe a bulky production schema. D15 still governs production storage. Settle D16 here (replace the old Neo4j section/exhibit text in place, or keep the new text beside it).

**Assignments:** builders separately integrate one preparation function/versioned storage and structure/references; checker tests source reconstruction, repetition, versions and failures; coordinator owns shared records and merges.

1. Build in `driver/prepare/`, independent of `driver_reference/`; verify reused code.
2. Derive Items/subheadings from originals; database Items/contents links are cross-checks. Preserve unmatched text and uncertain headings.
3. Save ordered paragraphs/tables/headings/image content with exact locations. Keep generated labels separate; retain raw grids/spans with printed headers/unit lines when semantic labels are uncertain.
4. Preserve full inline-tag context in prose/tables. Hidden tags remain metadata, not visible quotes inferred by matching values.
5. Link supported footnotes/references; short superscripts may be exponents/units. Keep every repeated occurrence/location/context.
6. Reuse output only for matching source bytes and preparation settings/version. Parser fixes create versions; old originals, references and resolver mappings remain usable.
7. Publish atomically; partial work never appears complete. Emit every file/asset outcome; conversion SUCCESS is insufficient.

**Pass:** independent reconstruction of exact evidence, repeats and table support; deterministic replay; upgrades/resumes preserve old references and incomplete status.

**Review:** original → blocks → exact location, including a table and unresolved case.

#### Step 6 — D · Assemble reading pieces

**Entry:** accepted blocks and explicit tokenizer/budget profile. Provisional profiles are allowed for development; final benefit uses the actual reader profile.

**Assignments:** separate assembly and reference/boundary workers; checker verifies coverage/order/repeated context/oversize cases; coordinator integrates one algorithm.

- Count the full request with a pinned tokenizer: instructions, metadata, text, context and answer space. Characters ÷ four is insufficient.
- Traverse in source order. Test each Item plus required context against a fresh piece; keep fitting Items intact and pack consecutive ones greedily. Split oversized Items at subheadings then blocks; tables into row groups with headers/unit lines; text at declared sentence boundaries. Pack resulting consecutive blocks greedily within budget.
- Budget referenced notes/definitions/footnotes and needed neighbours before finalizing. Resolve competing references in fixed source order; track visited targets to stop cycles without silently dropping required context.
- Assign each source occurrence one primary read; repeated context retains the same ID.
- Oversized indivisible rows/sentences/required context use an already-approved larger profile or remain unresolved—never truncated or counted as read. Vague “above” references remain unresolved when the outline cannot resolve them.
- Budget changes rebuild pieces from saved blocks, without reconversion.

**Pass:** code verifies primary coverage, order, token fit and reference accounting. Step 8 tests distant facts/causes; fit alone does not prove semantic recall.

**Review:** whole Item, split table and cross-section reference with measured tokens.

#### Step 7 — E · Replay, scale and timing

**Entry:** one integrated, frozen code/settings snapshot.

**Assignments:** checker independently replays/audits; builders run T2 scale/failure/resume/concurrency partitions and T5 instrumentation/timing; coordinator reconciles all categories.

- Derive tests from live entry points, failure branches and source categories; cover every observed category (§7 is a minimum). Use original-based answers plus boundary/adversarial/mutation cases.
- Trace required content, including images, conversion → blocks → pieces; verify locations and table/footnote relationships at each boundary.
- Replay in clean worktrees with changed file order/worker counts; compare canonical content, reporting model/OCR variation separately.
- Test interruption, exhausted retries, corrupt caches, duplicate tasks, changed sources and partial writes.
- Measure retrieval + preparation: cold/warm cache, requests, throttling/retries, memory and normal/slow/burst behavior. Quality tests may overlap; performance comparisons require comparable controlled load.
- Separate publication → discovery → acquisition → prepared. Historical replay cannot establish live discovery delay. Check live priority during backfill and the shared limit, including redirects/retries.
- Report distributions and sample counts. Before deployment, propose an owner-approved numeric earnings-readiness target from preparation/discovery/burst measurements; no invented deadline.

**Pass:** required checks on one version; zero known wrong-content/association accepts under the approved gate. Report omissions/unresolved counts and denominators. Unread required evidence blocks full readiness; remaining failures get a bounded fix or hold.

**Review:** demonstrated uses and next scope. Finite tests cannot prove all future filings correct.

#### Step 8 — Approved AI-reader comparison (T4)

**Entry:** accepted preparation, qualified independent answers and an approved model/prompt/settings/strata/token/cost package under applicable Phase 6 rules.

**Assignments:** runner and measurement builders; independent checker guards unseen truth. Competing arms start only after package approval.

- Define the task: locating known facts differs from discovering facts; Fiscal locator results cannot certify general Driver extraction.
- Use one fixed reader to compare stored text with prepared blocks: **20 development files, then fresh held-out files**.
- Score correct facts/causes, misses, wrong associations, tokens, calls, latency and cost by source/layout. Include distant-section/exhibit links, references, images and oversize cases; do not score only proposed relationships.
- Keep tagged tables in the baseline and measure their token cost separately; skipping needs its own coverage test.
- Hide realized returns; enforce publication/version cutoffs. Preserve originals separately from any reader view with leakage controls.
- The tested reader neither creates nor grades truth. Cross-provider agreement/typed output is not proof. Keep semantic judgement separate from deterministic copying/calculation; TypeSafe/JEV needs role-specific qualification.
- Failed held-out cases become regressions; certify again on fresh material.

**Pass:** task gates, rule 8.17 and stricter applicable Fiscal requirements. Report whole-fact errors, missed relationships and total coverage, not accuracy on a tiny accepted subset. Preparation, extraction and prediction improvements are separate claims; T4 does not prove trading performance.

**Review:** accept the input/reader arrangement or identify the measured issue to iterate.

#### Step 9 — Reuse and repair

**Entry:** Step 7 accepted for the format/failure class; applicable Step 8/source-activation approvals remain separate.

After owner review, independent tracks may run together:

| Track | Work |
|---|---|
| Drivers | Continue agreed later steps through the versioned interface; no redesign here. |
| Future ingestion | Call the same function before cleaning raw inputs; prepare tested rollout/rollback and readiness evidence. |
| Historical cleanup | Frozen affected-record manifest and read-only proposal; defer news/call recovery until needed. |
| Predictor revamp | Migrate/test consumers separately; preparing data or restarting ingestion does not migrate them. |

**Repair sequence**
1. Specify each failure class, detector, recovery method, expected result and checks.
2. Partition whole events deterministically; one writer owner per event/run. Resume without duplication/degradation.
3. Preserve source versions and restorable before-state; recover intact bytes, never PDFs reconstructed from damaged database strings.
4. Produce dry-run changes: identity, old version/hash, new references/content, reason and checks.
5. Independent checker verifies originals; recheck stored version before writing and leave conflicts unresolved.
6. Obtain approval for the concrete write batch; cleanup priority alone grants no database writes.
7. Run bounded code with live-first priority; read back, verify and retain before/after counts, conflicts and recovery records.
8. Log unknown/unverified cases; no improvised case-specific rules or later evidence.

**Integration:** test 8-K packet and warmup consumers sharing `_fetch_8k_core()`; switch section extraction only after independent superiority, required checks and consumer migration. Keep the live feed; savings are unproved. Any future SEC-feed fallback needs separate coverage/reliability/arrival-delay testing under the shared limit. Record rollback and consumer version.

**Review:** concrete database-write, deployment and service/consumer decisions; never re-request authorization already granted.

### 4. Shared records and reproducibility

Freeze these meanings before dependent jobs; they define required information, not a bulky converter format. Package-first Get stores shared identity/publication evidence once and member identities/ranges in its compact manifest; reference, decoding and readiness records are added by the stage that establishes them.

| Record | Required fields |
|---|---|
| Event | Stable ID/provider/accession; publication time and evidence; version/availability. |
| Original | Event, filename/path or provider ID, URL, sequence/type/description, byte hash/size, format/decoding outcome, retrieval provenance/inventory source. |
| Reference | Referring location; actual target ID/location/version/availability; resolution status. |
| Block | Prepared-version ID, original reference, order/kind, exact evidence/anchors, accepted structural path, unresolved annotations. |
| Table/cell | Raw coordinates/spans, exact printed text, anchor, supporting row/header/unit/footnote references. |
| Tag | Original identity/context, transform, sign, scale, unit, period, dimensions, location, visible/hidden status. |
| Outcome | Event/file/component, stage, status, reason, affected locations and required unread counts. |
| Run | Package/code/environment/input/output hashes, commands, timings/resources/costs, errors, limits, checker verdict. |

Keep stage separate from proposed status: `OK / NOT_READ / UNRESOLVED / FAILED`. Acquisition OK proves acquisition only. Full preparation requires all required evidence; optional labels may remain uncertain if complete original text/grids survive. These statuses do not replace rule 8.14's five Driver outcomes.

Unknown metadata stays explicit. Publication/version/availability dates remain evidence; runtime timestamps/durations belong in the run log.

**Identity and exactness**

- File ID = accession + original filename/path; version = byte hash. Exhibit labels are not IDs. Shared blobs may retain separate source/occurrence records.
- Preserve immutable bytes. Pin/test decoding against source declarations/format rules, retaining byte mappings. Successful Windows-1252 fallback alone proves nothing.
- HTML/XML anchors use mapped source-node/text ranges or bytes with a versioned resolver. PDF/image anchors include original, page/region and extraction version; a box locates evidence, not OCR correctness.
- Map decoded entities/rendered text back to originals. Normalize display only; preserve evidence dashes, quotes, non-breaking spaces and financial characters.
- Check inline styles, stylesheets, hidden tags and alternative image text. Blanket removal of `display:none`/hidden tags is insufficient.
- Preserve occurrences: one primary representation/read per occurrence, not global deduplication of repeated numbers.
- Never use converter-list positions alone as anchors. Retain old originals/prepared versions/resolver mappings across upgrades; bare DOM paths need not survive parser changes.
- Store financial values as exact strings plus source metadata; indices/counts may be integers. Pin geometry/numeric serialization, avoiding floating-point changes to printed values.

| Comparison | Required agreement |
|---|---|
| Same deterministic code/bytes/settings, including another bot/worktree/order | Identical canonical content/references; runtime/performance may differ. |
| Different converters | Required evidence/associations; raw format and block segmentation may differ. |
| Independent implementations | Declared fields and original evidence; code need not match. |
| Fresh OCR/model runs | Retain versions/settings/outputs; measure variation. Cached replay proves no model determinism. |
| Independent labels | Compare fields/locations; resolve from originals. Agreement alone is insufficient. |

Canonical tests: UTF-8 JSONL, sorted object keys, compact separators, no NaN/Infinity, one trailing newline. Preserve ordered arrays; sort only declared unordered collections. Manifests, not completion order, control processing order. IDs exclude agent names, absolute output paths, runtime timestamps and random execution order.

Matching hashes prove equality, not correctness. Diagnose mismatches for input/code/serialization/environment/model faults before changing the specification.

### 5. Sampling and outcome rules

The coordinator freezes each job's exact manifests:

- Version the population inventory; stratify by actual form, format, year/layout and failure class.
- Within strata, sort by documented hash of fixed salt + source ID. Retain IDs/hashes, quotas/rationale and planned/achieved type/table/filing counts. A seed over an unsorted directory is insufficient.
- Name mandatory regressions separately from population samples. Cover every relevant category; news/transcript results cannot establish press-release performance.
- Required samples: **50 retrieval filings; ≥300 untagged cells; 20 contracts; 20 varied PDF/image sources; T4's 20 development files plus fresh held-out files.** The familiar 20 are not final validation.
- Changed/corrupt frozen input stops the affected job with `INPUT_MISMATCH`; never silently substitute/drop it.
- Original-based answers precede candidate scoring; code grades the frozen key. Later equal-value matches are not truth.
- Report accepted/not-read/unresolved/failed counts and denominators by source/layout, including unattempted content.

Zero errors in 300 cells supports only a bound for that sampled population under its sampling assumptions—not whole-document recall, model accuracy, every cell type's error rate or universal perfection.

### 6. Execution rules

**Scope and coordination**

- Read the frozen job, applicable sources/instructions and accepted prerequisites; verify hashes. Avoid rereading whole chat histories.
- Edit assigned files only; coordinator owns shared interfaces, locks and integration. Source documents and bot opinions are data, not overriding instructions.
- Resolve routine issues locally. Stop affected work on ambiguity changing evidence/scope/acceptance; send the coordinator the issue, source, smallest proposed fix and affected jobs. Continue unrelated approved work.
- Never guess defaults. Contract changes require a new version and affected-job rerun list.
- Independent review inspects evidence and executes the delivered version. Stop at the agreed handoff; a free slot never releases downstream work.

**Files and environments**

- Separate builder Git worktrees from the frozen base + approved overlay. Return reviewed patches/new-file lists; never reset/discard others' edits.
- Proposed code/tests: `driver/prepare/`, `tests/driver/prepare/`.
- Proposed experimental root: `/home/faisal/prepare_work/<campaign>/<job>/<run>/`; shared originals read-only, separate job outputs. Outside the repo, so no new `.gitignore` entry; not D15's production choice. No paths are created by this plan.
- Keep accepted instructions/manifests/results durable; temporary scratch is allowed, sole copies in `/tmp` are not.
- Leave the shared root environment unchanged. Pin compatible isolated environments. Prepare has no `uv.lock` yet: create/test project and lock before using `uv sync --frozen`.
- Use Step 0's verified route to copy code/input snapshots to **minisforum2**, check hashes and run heavy tests there. Do not substitute the control-plane host. The owner withdrew the local GPU idea; P18's optional Mac/GPU route is outside this scope.
- Pin performance hardware, threads/workers and cache state; fix locale/timezone/relevant seeds without claiming model/library determinism.

**Downloads and spending**

- One acquisition queue owns all campaign SEC calls, including library calls. Converters use its immutable cache. SEC's overall cap is **10 requests/second** across machines/clients; **this campaign uses 5/second**, including file lists and retries. Existing clients share the overall cap; never a per-agent quota.
- Freeze connect/read timeouts, retryable faults, attempts, delays and `Retry-After` handling. Respect throttling; bounded network retries only, not repeated semantic attempts until success.
- Verify cache identity/hash. Partial/failed/changed sources get recorded attempts/versions.
- Use approved access, verify active authentication/account limits; provider names/flags do not prove billing. Checks are offline by default; live tests name authorization/access and cannot hide paid calls.
- **Owner's AI billing rule: subscription only.** JEV is the sole possible paid API exception; its existing test/budget approvals still apply. This does not change data-service access or authorize a run.
- Codex uses **ChatGPT subscription login**, not API-key billing. [Official OpenAI authentication](https://learn.chatgpt.com/docs/auth)
- Claude uses **subscription authentication**. Checked 2026-10-01: the June 15 separate-credit change was paused; plan-authenticated SDK/`claude -p` still use subscription limits. The older local separate-pool claim is outdated. [Official billing notice](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan)
- Verify effective authentication: API keys can override Claude subscription credentials. Keep approved transport and no-extra-spending controls. [Official Claude authentication](https://code.claude.com/docs/en/authentication)
- If subscription access or quota is unavailable, stop affected AI calls and report/wait; never fall back to paid APIs, extra credits or overage. JEV's exception does not extend to other AI.
- No unlimited-capacity assumption, credential changes or “lighter” Phase 6 approval. Prepare the concrete run/cost first.
- Database writes, production ingestion, deployment, provider replacement and push need their applicable authorization. Honor grants without repeatedly asking.

No new cross-provider messaging service: distribute small work orders and collect named artifacts. Without shared storage, transfer the hashed package and verify receipt.

### 7. Required regressions

Expand this minimum from live code branches and observed source categories. Every negative test needs a real positive control; fix the owning rule for the class, never one company.

| Area | Cases |
|---|---|
| Acquisition | Repeated EX-99.1; missing EX-13; referenced assets; index/package differences; HTTP/error pages; retries; corrupt/truncated cache; XML without expected declaration. |
| Real filings | AMG HTML/PDF identity; IBM/Carnival incorporated reports; CVS/Southwest body-only disclosures; Coty inequality deletion; Darden footnotes—each checked against its own original. |
| Formats | Native/scanned PDFs; charts/images inside text; styled fragments; covers; hidden tags; uncertain encoding; explicit unsupported outcomes. |
| Tables | Empty/layout/nested/merged tables/cells; multi-row headers; repeated labels; signs, percentages, counts, dates, units/scales, segment/basis headings, footnotes. |
| Tags | Airbnb durations; single-digit values; partial tables; Snowflake untagged conversion rates; hidden/visible contexts/transforms. |
| Conversion loss | AES dropped PDF fragments; values/image OCR omitted by chunking despite conversion SUCCESS. |
| News/calls | Truncated/empty/edited news; missing originals; every speaker filter; answers before first analyst pair; malformed/short exchanges; fallback storage. |
| Pieces | Long Items; indivisible oversized rows/sentences/context; reference cycles/vague pointers; across-exhibit causes; missing/later targets; repeated context; token limits. |
| Concurrency/versioning | Duplicate downloads/tasks; changed order/worker count; interrupted publication; cache upgrades; stale repair preconditions; live/backfill contention. |

### 8. Copyable work order and handoff

Fill every applicable field before dispatch; mark others N/A rather than leaving assumptions implicit. Bootstrap jobs name the missing commands/interfaces they create; dependent jobs wait for tested versions.

```text
JOB: ID / stage / role / purpose
Authority: relevant P/T/D IDs and rules
Approved scope and stopping checkpoint
Accepted prerequisites + hashes

INPUTS:
Code commit + working-file overlay
Instruction/contract version + hash
Named sources + hashes
Sample type/table/filing minima + rationale
Expected-answer/checker version; evidence/hidden-key restrictions

RUN:
Working directory; permitted edit paths
Tool/dependency/environment/model/weight/configuration versions
Host/resources; verified worker execution/transfer commands where required
AI subscription authentication; JEV approval/budget if used
Duration range + basis, or unmeasured until pilot
Network/timeouts/retries, or offline
Ordered instructions; exact setup/run/check commands
Missing interfaces/commands this job creates

OUTPUT:
Paths/records/order/comparison rules
Failures/reason codes; evidence and acceptance checks
Independent reviewer; owner-visible example

HANDOFF:
Actual code/input/output/environment hashes
Commands + exit results
Accepted/not-read/unresolved/failed counts + denominators
Regression + fresh-input results
Time/tokens/cost, or unmeasured
Assignment deviations/dependencies/limits
Patch + new files; next step
```

**Builder prompt**

> Follow the frozen job and common rules. Build the smallest correct component, verify reuse, preserve evidence. Write a failing test before a behavior fix; run focused and required regressions. Do not substitute inputs, widen scope, alter shared contracts or start unreleased work. Escalate cross-component issues with evidence; deliver the handoff and stop.

**Checker prompt**

> Independently establish answers from originals, inspect delivered code and replay commands in a separate worktree. Check omissions, associations, failures and repeatability. Neither model agreement nor matching hashes proves correctness. Report source-backed discrepancies; accept only the agreed checks on one frozen version.

### 9. Review decisions retained

Repeated instructions are consolidated above; these distinctions prevent earlier rejected shortcuts returning.

| Earlier suggestion | Retained decision |
|---|---|
| Start everything together; write later stages after Wave 1 | Full plan now; only approved, dependency-ready work runs (§2–3). |
| Duplicate all components; fixed four/eight-agent staffing | Independent replay and targeted second implementations; staff actual independent jobs (§2). |
| Equal hashes prove correctness; mismatches prove unclear instructions | Equality only; diagnose other causes (§4). |
| Freeze production format before comparison | Freeze required information first; choose block format at Step 5 and production storage under D15. |
| Trust prefix detection, decoding, universal tag pre-pass or exact-text adapters | Verify format, full tag context, hidden facts, repeated matches and source associations (§3–4). |
| Clean evidence; classify short superscripts as footnotes; deduplicate all numbers | Normalize display only; preserve exponents/units and every occurrence (§4/Step 5). |
| HTML twin is a free PDF answer key | Verify structural/content equivalence; preserve unique evidence (Step 4). |
| Arbitrary quotas/code caps/owner-labelling workload | Justified coverage minima; no 40% rule, five-cell cap, 300-line cap or compulsory 30 owner labels. |
| Headless billing always separate; labelling gets lighter approval | Current official billing and unchanged project access/qualification controls (§6). |
| Reopen D12/D13; urgent history repair for old predictor; news irrecoverable | Carry approvals forward; preparation first, history alongside Drivers, news/call recovery deferred (§1). |
| Ban temporary files/retries; other lanes never block earnings | Durable accepted artifacts, bounded network retries; unrelated work proceeds, required missing earnings evidence still blocks full readiness. |

### 10. Coverage and evidence trail

| Source IDs | Location |
|---|---|
| P1–P5, P25; T3/T5 | Steps 1–2/4; §4: acquisition, formats, coverage, originals/equivalence. |
| P6–P10, P14–P15, P20, P22 | Steps 3–5; §4/7: structure, exact evidence, tags/tables/footnotes. |
| P11–P12, P17, P21 | Steps 5–6: versions, pieces/context, repeated occurrences. |
| P18; T2/T5 | Step 7; §6: worker host, limits, replay, timing. |
| P19, P23, P26; D11/D14 | Steps 1–2/9: earnings-first preparation, repair, conditional service replacement. |
| P24; T1 | Steps 0/4; §6: maintained routes, portable output, dependencies/costs. |
| T4/T6/T7 | Steps 4/7/8: contracts/images, complete path, separate reader test. |
| P13/P16 | Dropped: old flattened text is not evidence authority. |
| D1–D14; F19/D15 | §1 and relevant steps: existing approvals retained, history recovery deferred, storage proposed. |

**Reviewed:** both drafts/follow-ups; `runningIdeas.md`; repository instructions and `driver/`; environment/locks; rules/Phase 6; local billing note and official authentication/billing pages; [TypeSafe model description](https://docs.typesafe.ai/concepts/system-one). Typed judgement is not guaranteed truth; no new JEV role is activated.

**Review baseline before consolidation:** HEAD `722a931669f29f91beda2d640750eda197e986f7`; `runningIdeas.md` SHA-256 `92a63a1b3e02a181a09b6da27f212d7d179e5967d4dff3827f8d36569f5753ca`; moved plan SHA-256 `8842fd18769f3c96f77739d1762d403d8de2a72b52882dfd38fb7e6e26384768`. Freeze this complete updated file and included working/untracked code before dispatch; these baseline hashes are not its current hash.

**Unproven until tested:** winning converter, corpus completeness/correctness, model determinism, live speed, subscription capacity and production repair.

**First checkpoint:** Step 0, then the single-filing A · Get result, unless the owner releases a combined scope.
