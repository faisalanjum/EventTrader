# Preparation tools and scope

*2026-10-04 · Start here; linked records hold reproduction details.*

**Order:** grader/baseline → worktree merge → **HTML/XML + selective image OCR**. Dedicated PDF development is **paused**; preserve originals, fallback and research. Historical downloading is approved; live ingestion remains separate. [Overall plan](PrepareStep.md).

**Standard:** minimal generic code, libraries first, no paid APIs, exact source links. Preserve values, signs, units, dates, labels, order, footnotes and relationships. Target 100% on agreed tests; unread/uncertain content never counts as complete. Sample scores do not prove corpus accuracy.

## HTML/XML first: tested tools and gaps

**Candidates, not a production-approved pipeline:**

| Format | Best supported approach so far | Evidence and remaining work |
|---|---|---|
| **HTML** | EdgarTools + source visibility, formatting, links/images and browser geometry; Docling remains a comparison. | Development: **171/171 cells**; structures **49/60 pass, 6 fail, 2 approximate, 3 excluded**, before final image integration. Source identity/context and integration remain. |
| **XML** | Small standard-parser wrapper; preserve hierarchy, attributes, namespaces, mixed prose and source spans. | **601/601 main XML files** pass structure/text checks; semantics and attachments unproved. Unresolved external content fails explicitly. |
| **Images** | Docling + **RapidOCR medium**; verified embedded text first, original pixels authoritative. | **85/575 images** processed. Check numbers, negation, orientation and associations; confidence cannot certify accuracy. |

**Speed:** HTML linking alone: **214→49 s/60 files**. Fuller route: **738 + 110 s**, excluding resource indexing/OCR; final latency unmeasured.

**Keep medium RapidOCR:** smaller detection merged headers; OnnxTR FAST-base/PARSeq was slower and misread numbers/identifiers; PaddleOCR-VL failed whole pages despite crop success; Tesseract omitted content. Configuration-specific findings, not blanket library rejections. [OCR comparison](../../../../../prepare_work/tool_selection_20261004/trials/ocr/quick_compare_20261004/RESULTS.md).

## Next actions

1. **Baseline:** finish grader review → activate approved package 3 → official comparison 35. Pointer still package 2; recheck live state.
2. **Merge:** reconcile **38 saved worktree files** against current main on identical sources/key/settings. Verify changed results, retain both sets of useful tests, merge small qualified changes. Never overwrite newer main behavior or copy the experimental key pointer. [Checklist](../../../../../prepare_work/tool_selection_20261004/MERGE_PLAN.md#integration-sequence).
3. **Complete:** re-link 60 HTML outputs; resolve 1,759 repeated-table fingerprints with unproved occurrence identity; finish headings/references, XML attachments and images. Test unseen documents and corpus coverage; incomplete news/transcripts remain gaps.
4. **Measure:** full cold/warm, fresh/cached and slow-case latency, memory, restarts, reader tokens and resource cost. Pin dependencies/models; one heavy process within the worker's 8-GiB cap. Save ordered source-linked blocks; chunking still requires coverage/context/size validation.

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
