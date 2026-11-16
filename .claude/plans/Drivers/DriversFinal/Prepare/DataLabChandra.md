# Chandra OCR and Datalab — decisions and evidence

*Consolidated 6 Oct 2026 from the API assessment and Chandra test log. Current execution and release gates: [PrepareTools.md](PrepareTools.md).*

**Owner decision:** full Datalab replacement is unaffordable. Keep local HTML/XML + Chandra with PP-OCR/RapidOCR and OnnxTR evidence; Sonnet remains optional, **off by default**. GPU provider/hardware/budget are undecided. Dedicated PDF development stays paused; the API trial did not change production.

**GPU comparison:** Datalab for images/PDFs alone is estimated at **$40–85/month**, so compare a rented GPU against **that**, not the much higher full-replacement bill. Measure cost per 1,000 completed images, including startup, idle time, storage and failures, with unchanged accuracy. Consider temporary backfill rental and on-demand/batched live processing; neither is selected or proved cheaper yet.

**Runpod budget check (6 Oct; GPU test deferred by owner):**

- **Planning estimate: ~$50/month; allow ~$85 for an average month, not a spending guarantee.** At the published RTX 4090 Serverless rate of **$1.10/hour**, 4,900 pictures × 20–35 s plus 644 starts × (30–120 s loading + 5 s idle) gives **$36.83–77.00 before storage/tax/retries**. The endpoint guide rounds the rate to $0.00031/s ($1.116/hour); that raises the upper calculation to $78.12. Pin the console rate before running. [Rates](https://www.runpod.io/pricing), [billing](https://docs.runpod.io/serverless/pricing).
- **Counts corroborated, timings assumed:** our saved 2025 inventory has 58,477 image occurrences (~4,873/month), but only 49,104 first-seen byte contents (~4,092/month) with persistent reuse. February has 12,120 occurrences. The supplied busy-month projection is ~$120 ($89–182 range), also unmeasured; **$85 cannot cover every month by assumption**. HTML/XML remain local; these figures exclude full-PDF OCR, existing CPU work and downstream driver AI.
- **Candidate setup, not deployed:** Serverless Flex, RTX 4090 only, one GPU/worker, **active workers 0, max workers 1 initially, idle timeout 5 s**, FlashBoot on. Queue each filing's pictures together, load the model once per worker and reuse saved image/settings results. Keep an execution timeout; retain incomplete work. Max workers limits concurrency, not monthly spend. [Settings](https://docs.runpod.io/serverless/endpoints/endpoint-configurations).
- **Remaining check:** time ~30 representative saved pictures, cold and warm, with unchanged OCR settings; measure actual billed startup/idle/storage, memory, completeness and reading quality. Current `readers.chandra()` uses Mac/MLX; Runpod needs Chandra's NVIDIA runtime. Published token-speed benchmarks do not prove seconds per picture. Owner has an account but no worker and chose to test later; no GPU or model calls were made.
- **Budget boundary:** a hard $85 ceiling would require stopping dispatch and carrying a backlog; it cannot promise that all peak-month work finishes. Runpod's default $80/hour protection is not a monthly cap. Keep trial auto-pay off and track spend; do not treat a low-balance alert as a hard stop. [Account billing](https://docs.runpod.io/accounts-billing/billing). Reproducible arithmetic and assumptions: `prepare_work/runpod_budget_check_20261006/CHECK.json`.

**Estimated API costs (USD, before tax, one pass):**

| Accurate conversion scope | Entire current backfill: observed rate / list rate | Average monthly: observed / list |
|---|---:|---:|
| All disclosure HTML + PDFs + images; standard block locations | **$28,500 / $36,800** | **$690 / $890** |
| Same, plus precise word/table-cell locations | **$46,100 / $60,200** | **$1,120 / $1,460** |
| Keep local HTML/XML; Datalab only images + PDFs, standard locations | **$1,800 / $1,820** | **$42 / $43** |
| Images + PDFs, with word/table-cell locations | **$3,540 / $3,590** | **$82 / $84** |

- **Scope:** 140,941 distinct disclosure HTML files (~3.50M estimated rendered pages), 431 PDFs (13,360 pages), 168,632 distinct images, including logos. Existing news/transcript text needs no conversion. Generated XBRL support views are not separately converted; XML remains separate and unsupported by this API.
- **Monthly basis:** 13,216 filings, Apr 2025–Mar 2026 (~1,101/month): **3,106 annual/quarterly reports (~259/month)**, 9,081 8-Ks including amendments, and 1,029 other filings/amendments. Four reports × 800 companies ÷ 12 is ~267/month; the higher total includes event filings and their attachments. Forecast assumes the same coverage and reuse of identical bytes. The stored corpus ends 28 Apr 2026; these are estimates, not current invoices.
- **Seasonality:** busiest modeled month: ~$2,010 observed / $2,610 list with standard locations; ~$3,250 / $4,250 with detailed locations. Images/PDFs alone peaked at ~$100 standard or ~$190 detailed. These are not guaranteed caps.
- **Uncertainty:** 160 stratified offline HTML counts plus six real API pagination checks. Full backfill with detailed locations: planning range **$37k–64k observed**, **$49k–84k list**. Monthly HTML estimates inherit that sampling/rendering uncertainty.
- **Billing:** receipts mostly imply 25% below list; continued discount is unconfirmed. Estimates model documented per-request cent rounding, although some receipts show fractional cents. Pay-as-you-go has no fixed subscription; optional Team is **$400/month minimum including $400 usage**, not $400 extra. That minimum would dominate an images-only plan.
- **Excluded:** taxes, storage/transfer, integration, retries, downstream driver-creation AI, structured extraction and variable-cost cross-page merging. Chart understanding adds up to ~$506 for all historical images, or ~$12/month at the observed image volume, at list rates before rounding.

**Self-hosted Chandra: lasting test findings (historical two-reader experiments):**

| Sample | Result and limit |
|---|---|
| 50 hard answer pages | Chandra 41/50 wholly right; Sonnet 40/50. After checker corrections, 389/525 blocks agreed (44% of words): 388 right, one shared error; 14/57 tables agreed and were checked right. Agreement is not proof. |
| 336 real pictures, 302 previously unseen | Readers agreed on ~71% of words, only ~29% in financial tables. Audit of 20 pictures: 90 agreed blocks right; two real Chandra errors among 27 unresolved blocks; six chart regions had incomplete usable evidence. |
| Separate 120-picture validation | Original routing sent 28 to Sonnet, with no material correction in those calls. It missed 18 wrong logo names plus three presentation differences. The later guard routed 52/120; Sonnet's alternatives helped, without automatic certification. Original audit: 18 whole pictures + two partial. |

- **Speed measured:** Chandra ~40–48 s/picture on the tested Mac GPU; each free OCR ~4 s. These are not cloud-GPU timings. Quantization, smaller inputs or a different runtime require fresh accuracy checks.
- **Meaning to preserve:** values, signs, units, periods, labels, headings, row/column/legend relationships, original image and occurrence context. Chandra can misread names/numbers and invent chart descriptions; free OCR can miss the same error. Positions alone do not prove text or relationships. Driver-stage checking remains necessary; no human production dependency.
- **Do not restart failed approaches:** whole-page exact agreement over-rejects useful content; numbers-only/free-tool voting missed errors; crop rereads cost 62% more input tokens and confirmed 0/8 pages (the original 235/235 safety claim was retracted: 221–227/235). LightOn/TeleOCR trials introduced structure or number errors. Hidden-slide-text bypass saved 1/209 calls; the bounded reread pilot demonstrated no new material correction and its flawed runner stays evidence only.
- **Current interpretation:** old mandatory Sonnet/Opus flows and “57% confirmed” wording are superseded. Retain raw readings and explicit missing/incomplete/unverified states. These samples do not prove corpus accuracy or production readiness; integration, worker reliability and release gates remain in PrepareTools.

**Hosted Datalab API trial:**

- Native financial PDF: **58/58 selected cells correct**; one label's citation box overlaps its neighbour. Scanned page recovered 8⅜%, § and key numbers; silently corrected one printed typo.
- Real HTML, dense table image and diagram processed successfully. Redline excerpt preserved deleted **1.50** and replacement **1.00**. These are bounded trials, not corpus-wide accuracy proof.
- **XML rejected (HTTP 400).** Local HTML image links are not uploaded automatically; one real scanned-HTML filing returned success with no readable body. Embedding an image worked, but fixed-width rendering clipped it; responsive sizing fixed the tested case.
- Still ours: XML reading, original-file retention, image/document association, completeness/failure handling, context-preserving chunks and delivery to the final AI. Datalab does not make this maintenance-free.

Images/PDFs-only Datalab remains a comparison, not an adopted route. API trial receipts total **~$1.91**; the API trial made no SEC requests and launched no full backfill.

Sources: [pricing](https://www.datalab.to/pricing), [billing](https://documentation.datalab.to/platform/billing). Detailed evidence stays in `prepare_work/`:
- `datalab_setup_20261006/`: `BACKFILL_REPORT.md`, `BACKFILL_COST.json`, `MONTHLY_COST.json`, scripts and API results.
- `pdf_twin_census_20261004/ocr_bench/real575_20261005/`: raw OCR, checker, adjudications, packets and `v4_replay/RESPONSE_TO_CODEX.md`.
- `documentation_consolidation_20261006_datalab_chandra/`: byte-exact pre-merge documents and hashes, including the complete former `ChandraTest.md` log. Historical review references retain their original meaning; this file replaces that log as the live summary.
