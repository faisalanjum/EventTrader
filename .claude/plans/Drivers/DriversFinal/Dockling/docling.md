# Docling for SEC filings and Driver extraction

Reviewed **2026-09-30**: Docling **2.131.0**, Core **2.99.0**, CPU; live MCP; independently checked Claude's saved results. This is a capability pilot, not a completeness or accuracy guarantee. [Detailed audit and reproducible evidence](/home/faisal/docling_capability_study_20260930/README.md).

## Recommended use in our project

1. **Use Docling to prepare evidence for our existing extractor:** ordered passages, table cells, images and source references. It does not automatically decide our fact types or causes.
2. **Preserve each original filing/exhibit and cache its parsed JSON.** Use HTML for fast text/tables; test PDF layout for visual headings and OCR for scans/slides. Fetch linked exhibits/images separately. A blanket HTML→PDF switch is not yet justified.
3. **Give the reader intact context:** neighboring blocks, table captions, headers, units and footnotes. Save each accepted fact's exact quote and source reference. Structure helps verify `caused_by`; adjacency alone does not establish a cause.
4. **Keep existing XBRL processing.** Docling's XBRL output lost dimensions and compound-unit details in our test.
5. **Validate before deployment:** form + Part + Item, TOC versus body, ordering, boundaries, table signs/units and evidence accuracy. Compare missed facts, reader tokens and runtime against today's pipeline on held-out filings.

## What it returns

`DocumentConverter.convert(source)` → `ConversionResult` containing **document, status, errors, confidence, pages and timings**. Its `DoclingDocument` contains:

| Structure | Useful content |
|---|---|
| Typed text | Paragraphs, headings/levels, lists, captions, footnotes; body/furniture separation. |
| Tables | Cell text, row/column positions, merged-cell spans, header flags; DataFrame/HTML/Markdown exports. |
| Pictures/pages | Images and optional OCR, classification or descriptions. |
| Navigation | Ordered blocks, parent/child references and IDs such as `#/texts/25`. |
| Provenance | Page, bounding box and character span **where available**; ordinary HTML lacks page boxes. |
| Exports/chunks | JSON, Markdown, HTML, DocTags, text; structural and token-budget chunkers. |

**Block ID ≠ fact ID.** One block may contain several facts. Store source identity/hash, parser version/options, frozen JSON, block reference and exact quote. References can change after reconversion; quote offsets must match the chosen `text`/`orig` representation. JSON preserves the parsed model, not the original file losslessly. [Document model](https://docling-project.github.io/docling/concepts/docling_document/), [converter API](https://docling-project.github.io/docling/reference/document_converter/).

## What the tests establish

| Capability | Verified result and practical limit |
|---|---|
| **10-K / 10-Q / 8-K HTML** | Eight real sources (two of each form, two exhibits) converted with **zero section-heading labels**: their headings used styled text. A control with h1–h6 tags produced hierarchy. “HTML never supports headings” is false. |
| **PDF sections** | Antero's 16-page 8-K package produced 143 text items, 20 tables and its Item headings. Claude's saved Abbott 10-K/T. Rowe 10-Q outputs reproduce 27/13 Part-or-Item labels and 70/45 tables. Counts are not completeness scores. |
| **Heading hierarchy** | Enable `heading_hierarchy_options.enabled=True` and `generate_parsed_pages=True` for font-style inference; hierarchy is off by default. Errors remain: quarterly Items at level 6; Item 1 before Part I in both saved 10-K/10-Q reading orders. Native inference changes levels without building a full Part→Item parent tree. A level-only repair is insufficient. |
| **Rendered HTML** | `HTMLBackendOptions(render_page=True)` added page boxes, **not missing headings**. Alcoa: 50/51 text items and 7/7 tables located; one box crossed a page boundary. Requires Playwright Chromium. `infer_furniture=False` retained pre-heading cover text in the control. |
| **Tables** | FAST/ACCURATE produced the same AMD 9×4 table, with values/signs visually checked. Not proof for other tables. Repeated exported headers can represent merged cells correctly. Nearby footnotes were not automatically attached in the control. |
| **OCR / pictures** | A real AMD image-only slide yielded 19 text items and 5 pictures; picture classification worked. Its current coverage in Neo4j was not audited. |
| **Chunking** | HierarchicalChunker follows detected structure; HybridChunker adds a token budget. Antero HTML: 410 chunks at 256 tokens; all references resolved, but no heading context. Neither guarantees complete causal passages. |
| **MCP** | Live conversion, outline, text search/read and saving worked. It exposes detected structure, with no added SEC Item parser. Text search missed table-only text; text-anchor reading rejected a table anchor; thumbnail failed on the connected service. Use SDK/JSON for tables and configuration. |
| **XBRL** | Real Coinbase standalone instance converted, including some accounting links, but omitted 619 source dimension members and the `/shares` in EPS units. Arelle period strings expose exclusive end dates. The XBRL backend expects an instance plus taxonomy; inline-XBRL HTML can still use the HTML backend. |
| **Reliability / speed** | JSON round-trips, five exports and batch continuation after a failed input worked. Model-free `NativePdfPipeline` returned text/boxes but no tables/headings. Neither `SUCCESS` nor an EXCELLENT grade means financial correctness. No whole-corpus speed estimate is established. |

Printed HTML is a derivative: preserve its images/assets and original source. Claude's AMD PDF contained blank pages and a broken image placeholder. Some character spans include material removed from normalized text. [Heading options](https://docling-project.github.io/docling/usage/heading_levels/), [confidence limits](https://docling-project.github.io/docling/concepts/confidence_scores/).

## Agent features and additional options

- **Chunkless RAG (`docling-agent` 0.6.0):** an agent selects sections from an outline, reads them and answers; no embedding index required. Claude's four saved answers contain the requested values/segments, but some added interpretation is not in the cited passage. Independent helper tests found omitted table cells/nested subsections and a page-number error. Useful to evaluate for targeted lookup; not ready as an exhaustive extractor. [Audit](/home/faisal/docling_capability_study_20260930/README.md#docling-agent-and-claudes-later-additions), [upstream](https://github.com/docling-project/docling-agent).
- **Agent enrichment/editing:** summaries, entities, keywords, schema extraction, heading edits and structured run traces. Model-generated annotations must remain distinguishable from source evidence. Not validated against our Driver rules.
- **Vision conversion:** Granite-Docling is available. Our default two-page CPU probe exceeded ten minutes; a bounded table-crop probe exceeded three minutes. Claude's ~25 s/page was not reproduced. The owner-noted local GPU endpoint is reachable, but our single picture-description API test timed out at 60 seconds; queueing was not isolated. No vision speed/accuracy claim. [Results](/home/faisal/docling_capability_study_20260930/README.md).
- **Other model features:** chart→CSV/summary/code, picture descriptions, formula→LaTeX and code enrichment. Reviewed, not established on this SEC corpus. [Options](https://docling-project.github.io/docling/usage/enrichments/).
- **Other extraction/deployment:** beta `DocumentExtractor` for schema fields from PDF/images; separate `docling-graph` for schema-based graphs; batching, page/file limits, offline model caches, CPU/GPU, remote inference, Serve/Jobkit and other Office/XML/email/audio/video formats. These are available capabilities, not all runtime-tested. [Extractor](https://docling-project.github.io/docling/_generated/examples/extraction/), [Graph](https://docling-project.github.io/docling-graph/), [formats](https://docling-project.github.io/docling/usage/supported_formats/), [advanced options](https://docling-project.github.io/docling/usage/advanced_options/).

## The Docling-based SEC project

[agentic-graphrag-finance](https://github.com/caldeirav/agentic-graphrag-finance), [author's article](https://developers.redhat.com/articles/2026/07/22/how-we-built-agentic-graphrag-financial-disclosures); reviewed commit `550f21cbd79a9e145ea5772c78b7fe3ab34ce338`.

**Borrow the organization:** document → section → paragraph/table/XBRL fact, with source references and controlled navigation. Its own parser/mapper adds this around Docling. Containment, sequence and cross-filing links are not financial causes.

**Do not adopt its code unchanged.** Independent tests found Item 1/1A/7 targeting, merged repeated 10-Q Items, quarterly MD&A assigned Item 7, overlapping 8-K sections, incorrect numeric scaling and segment-fact ID collisions. Its limited upstream HTML assertions passed despite these gaps. [Reproducible audit](/home/faisal/docling_capability_study_20260930/README.md#the-docling-based-sec-project).

## Run and inspect

Use the **SDK** for controlled settings; MCP for exploration. [Small tested script](docling_probe.py) saves JSON/Markdown/HTML/outline and prints headings. `--render-html` adds browser locations; `--pages FIRST LAST` limits a PDF range; `--show-options` displays settings.

```bash
cd /home/faisal/EventMarketDB/.claude/plans/Drivers/DriversFinal/Dockling
/home/faisal/docling_capability_study_20260930/.venv/bin/python -i docling_probe.py \
  /home/faisal/docling_capability_study_20260930/inputs/ar_2025_8k.pdf \
  --no-ocr --out /home/faisal/docling_capability_study_20260930/outputs/explore
```

Then inspect `doc.model_dump()`, `list(doc.iterate_items())`, `doc.texts[0].prov` or `doc.tables[0].export_to_dataframe(doc=doc)`. The isolated environment leaves the project's older Docling installation unchanged.

**Evidence:** [full audit/scripts/results](/home/faisal/docling_capability_study_20260930/README.md), [input URLs/hashes](/home/faisal/docling_capability_study_20260930/inputs/manifest.json), [original Claude scripts](test_scripts/). No Driver-rule edits, database writes or production integration were made.

## Claude's added tests — 20 filings, SEC heading rule, vision on the Mac GPU (2026-09-30 evening)

Local only: no paid calls, nothing written to the database. **Settings:** Docling 2.131, PDF route (headless-Chrome print), FAST tables, `heading_hierarchy_options.enabled=True`, OCR off. **Inputs:** 20 cached filings from 20 companies — 5 10-K, 8 10-Q, 7 8-K EX-99.1. **Evidence:** scripts in [test_scripts/](test_scripts/) (`scale.py`, `sec_headings.py`, `indep.py`, `vlm_api.py`); results in `~/.claude/projects/-home-faisal-EventMarketDB/backups/docling_tests_20260930/scale/`.

### Results

| Check | Result |
|---|---|
| Conversions | **20/20 SUCCESS**, 0 errors. Grades: 12 EXCELLENT, 7 GOOD, 1 FAIR |
| Items found as headings — **independent** check against raw-HTML Item lines | **271 of 273 (99.3%)**. A first check built from Docling's own text showed 100%; it was circular and has been discarded |
| The 2 misses | ADM 10-K Item 15 and LAZ 10-Q Item 6. The filer laid out the heading as a **one-row table** ("Item 15. \| EXHIBITS AND …"), so Docling correctly returned a table, not a heading |
| Nesting after the SEC rule (PART = 1, Item = 2, rest ≥ 3, relative to Docling's level for that Item) | **OKE 10-Q correct:** PART I → Item 1 → notes; Item 2 → its subsections. **ADM 10-K noisy:** the repeated page banner "ARCHER-DANIELS-MIDLAND COMPANY PART I" appears as headings; its PART lines were not detected; cover-page lines appear as headings |
| Speed on this box's CPU | 10-K avg 200 pages, **158 s** (1.26 pages/s). 10-Q avg 78 pages, **62 s** (1.27 pages/s). EX-99.1 avg 20 pages, **22 s** (0.9 pages/s). Chrome print 1–12 s |

**Rule additions this points to (proposals, untested):**
- a one-row table starting "Item N." counts as a heading;
- identical headings repeated ≥ 3 times are running page banners, so treat them as furniture;
- everything before the first PART/Item is a cover block.

**I agree with Codex** that levels alone are not a full Part → Item parent tree. Levels do drive chunk heading paths, but a true tree needs re-parenting.

### Whole-corpus time, one process on this CPU

Rough: measured rates × Neo4j counts.

| Filings | Count | Time |
|---|---|---|
| 10-K | 3,130 | ~141 h |
| 10-Q | 7,342 | ~133 h |
| 8-K EX-99 | 22,309 | ~143 h |
| 8-K EX-10 contracts | 4,470 (avg 6.8× the characters) | ~190 h, very rough |
| 8-K main documents | 30,303 | not measured |

**Total ≈ 25–30 days sequential.** Untested ways to speed it up:
- running several processes in parallel;
- running Docling itself on a GPU (Apple-silicon support exists).

### Vision conversion on the Mac GPU

Docling `VlmPipeline` + `ApiVlmOptions` → ollama `http://localhost:11434/v1/chat/completions`.

| Test | Result |
|---|---|
| Model | `qwen3.8:27b-mlx`, the model **already loaded**; `reasoning_effort: none`, `timeout: 900` |
| One slide image | 18 s; 4 correct headings |
| Two AMD press-release pages | 38 s (~19 s/page); clean 9 × 4 table; key figures match the release (43% GM, $149M operating loss, $0.69 non-GAAP EPS) |

**Why earlier API calls were slow (329 s, 56 s):** the Mac was also serving **another program's model**. Asking for `qwen3.8:27b-mtp-q4_K_M` forced a model swap each time (11–21 s load) and queued behind that program. This probably explains Codex's 60-second timeout.

**Rules for using the Mac:**
- use the model that is already loaded;
- allow long timeouts;
- expect sharing.

A general 27B model is **not much faster per page** than Granite-Docling on CPU (my earlier measure: 51 s for 2 pages; Codex could not reproduce it). The gain is quality on hard pages, not speed.

### Where I differ from the text above

- **"A blanket HTML→PDF switch is not yet justified"** — I agree for text and tables. But for the **section map**, the PDF route was the only one that found SEC headings: 0 via HTML in Codex's 8 sources and my 3; 271/273 Items via PDF.
- **Suggested split:** HTML for text/tables; PDF for sections, OCR and slides. Validate on held-out filings before adopting.
