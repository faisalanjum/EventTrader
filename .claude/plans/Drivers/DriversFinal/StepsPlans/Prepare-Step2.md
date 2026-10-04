# Prepare · Step 2 — Extend acquisition

**Status: Step 2 accepted by the owner (2026-10-02).** Acquisition and validation
passed. Historical download continues separately; two SEC 404 filings remain
tracked for investigation. Ready for Step 3.

**Goal:** preserve complete originals, prove which files were acquired, and reuse
saved copies cheaply. Standing requirements remain minimal, generic code and
comprehensive checks ([project instructions](/home/faisal/EventMarketDB/AGENTS.md)).

## Scale review

- **502 filings, 12 forms, 23,958 files:** byte-exact against the independent
  extractor; all **5,905 SEC-listed physical files** present, plus 65 identified
  viewing pages. All 11 joint-company false rejections are fixed. Claude's earlier
  5,769 count omitted the 136 physical files in those 11 filings.
- All 502 saved versions share their compressed input: **one physical copy**.
  This complete replay made **zero SEC requests**.
- Receipts use built-in SQLite transactions, one insert per response. **85,266
  durable inserts took 344 seconds** on the worker; this measures logging only.
  No whole-log rewrites or custom crash-repair protocol. The comparison script
  writes its final outcomes once.
- **69 tests pass** on Python 3.10/3.11: crash/restart boundaries, disk/quota stops,
  shared storage, index boundaries, cache integrity, retries and timestamps after pacing.
- Approved default: **5 requests/second shared**, retries included. Every filing
  in the planned 42,633-filing run requires its SEC file-list check. Unrelated tests
  are untouched. The overnight runner and 1,000-filing rehearsal remain separate.

## Initial 50-filing comparison

- **50 filings, 12 form types, 2,223 packaged files.** Every SEC-listed physical
  file is present: **534 physical files + 7 separately identified viewing pages**.
  No missing-file or metadata gaps. A separate parser checked all 50 original indexes.
- **All 50 fresh package downloads match the frozen originals byte for byte.**
  The sample covers amendments, XML disclosures, contracts, EX-13, PDFs and images.
- **Additional body-only earnings case:** CVS `0000064803-23-000003` passes;
  13 packaged files, six index-listed files, no EX-99 release. The disclosure is
  in the 8-K itself. It is separate from the frozen 50-file sample.
- **Replay: zero requests**, with network connections blocked and temporary raw
  inputs unavailable. Compressed originals produce identical inventories, source
  metadata and reference observations. This run took **18.4 seconds**; process
  peak memory was approximately **369 MiB**.
- **56 tests pass on Python 3.10 and 3.11**, plus independent source readback.
  Checks include whole missing files, malformed indexes, cache corruption and
  identity mismatches, generated views, retries, shared pacing and global 403 stop.

| Measured route, same 50 filings | Requests | Response bytes | Recorded seconds |
|---|---:|---:|---:|
| Complete packages | 50 | 305,895,410 | 50.5 |
| Indexes + listed files/views | 591 | 182,422,793 | 564.8 |

Times include configured pacing and fetch/cache work, excluding conversion and
separate package parsing. These are observations, not speed guarantees. All 649
requests across the comparison and supplement returned 200; stop/retry behavior
was tested through controlled failures. Routine acquisition uses packages plus SEC indexes.

## What changed

- `archive.py`: one shared, lossless raw-byte store for SEC responses and future
  news/transcript intake; content-addressed gzip, verified reuse, no silent repair.
- `campaign.py`: one download owner, five-request/second pacing including retries,
  persistent stop on 403, transactional receipts and a disk reserve; offline by default.
- `inventory.py`: compare original indexes with package members; preserve repeated
  exhibit labels and distinguish a supported viewing-page relationship from a
  physical source. No company-specific rules or new parsing framework.
- One bounded experiment script in `scripts/driver/prepare/`; tests mirror the
  runtime under `tests/driver/prepare/get/`. The package parser remains unchanged;
  saving now reuses compressed inputs and stops on storage failures.

## Explicit limits and next step

The 1,487 missing local HTML references are all the previously examined SEC-viewer
`include/report.css`; all audited company image links resolve. The **745 external
links remain inventoried, not resolved**. CSS/PDF/XML reference interpretation and
readability still need later preparation checks. Of the physical website copies,
195 differ from package bytes; both are preserved, with no inferred equivalence.

News/transcript auditing confirmed that today's “raw” Redis data is already
transformed. The archive must run **before JSON/schema/SDK transformations**.
All 187 available Redis copies were preserved as **processed-only** evidence.
Original-history recovery remains deferred; ingestion wiring is a later step.

**Next:** Step 3 — freeze preservation checks and independent answers before
comparing converters.

## Evidence and use

- [News/transcript audit](/home/faisal/prepare_work/news_transcript_audit_20261002/README.md) (kept: it holds
  the only saved copies of the audited news/transcript records).
- [Runtime/API notes](/home/faisal/EventMarketDB/driver/prepare/get/README.md)
  · [tests](/home/faisal/EventMarketDB/tests/driver/README.md).

The working folders behind these results were deleted on 2026-10-04, after the full download was approved; the numbers here are the record. The full Driver test command is
`python3 -B -S -m unittest discover -s tests/driver -t . -v`.
