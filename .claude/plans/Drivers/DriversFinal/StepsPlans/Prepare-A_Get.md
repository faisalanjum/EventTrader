# Prepare · A Get

**Goal:** preserve an SEC submission and every packaged file, unchanged and traceable.
**Status:** done (2026-10-04): 42,633 filings → 42,629 complete, 1 with one file SEC cannot prove (Guidewire), 3 not served by SEC; Codex approved. Live download of new filings: not built.

```text
SEC package → verify identity/framing → inventory files → save compressed original
                                                        ↓ later
                                             verify and decode once
```

## Contract

- Standard-library code; no AI, database writes, conversion or ingestion changes.
- Input: accession, expected company ID and form; either a local raw/gzip package
  plus its original SHA-256, or an explicit fresh download. No company-specific logic.
- Match accession/form exactly and require the company among the header's validated
  IDs. Record stated and actual document counts; SEC often reports different counts.
- Decode SEC envelopes, doubled leading dots and UU encoding; preserve other bytes,
  LF/CRLF content, exact names and all occurrences. Reject unsafe/conflicting paths,
  ambiguous metadata and broken framing, including two members accidentally merged.
- Save only `submission.txt.gz`, `manifest.json`, `receipt.json` under
  `<accession>/<original-sha256>/`. Gzip is lossless (level 6, fixed timestamp).
- Manifest v2 records canonical company IDs, source time/timezone, original hash/size,
  metadata, exact header/member ranges and decoded-file hashes. Actual URL/retrieval
  time stay in the receipt. Unknown offline retrieval time remains null.
- Publish atomically; verify existing versions, never silently repair them. Offline
  reuse makes no requests; `read_package()` verifies and returns all decoded files
  in one pass. Older experimental cache layouts remain separate.
- Keep bounded HTTP retries/timeouts, 403 stop and explicit redirect rejection.
  Caller coordinates the shared SEC budget. See [usage](../../../../../driver/prepare/get/README.md).

No routine index/download duplication, reference crawler, schema framework or
permanently unpacked second copy. Safe paths and timeout protections remain.
One writer per output directory; live HTTP requires Linux/main thread. Package and
decoded bytes are held in memory; large-file resource limits need Step 2 validation.

## Verification

- **28 offline tests**, zero skips, on Python 3.10/3.11; real AMG, EQR and multi-company
  13D fixtures. Tests cover positive controls, damaged framing, identity, encoding,
  paths, compressed storage/readback, corruption, deterministic reuse and HTTP.
- **60 saved filings / 11 form types / 3,223 members:** every decoded member matches
  the independent extractor's size/hash. This sample is stratified, not proportional;
  it is not a population error estimate or proof of complete SEC coverage.
- Of these, **36** have unequal stated/actual counts. Original code rejected 48/60
  through count or multi-company restrictions; the corrected code accepts all 60.
- Measured package bytes: **516,737,723 → 103,208,566** with gzip. Whole-database
  storage estimates from the review remain projections, not measured requirements.
- Fresh follow-up: **47/47 filings, 12 types, 1,793 members** match independent
  decoded bytes.
- **Closed as an acquisition blocker for this sample:** missing `include/report.css` occurs only in
  generated SEC views across 111 filings; 491 company HTML documents have no outside
  stylesheets, and all 1,057 HTML image references resolve inside their packages.
  Convert must retain inline styles and handle hidden XBRL separately from visible prose.
- AMG's browser check confirms the missing sheet affects only its cover-page appearance:
  all 82 visible cells retain their text and associations; the main 8-K and earnings
  tables are unaffected.
- The earlier live AMG check used one successful request (**0.334 s**, one observation).
  This revision used saved inputs and simulated HTTP; it made no new SEC requests.

**Remaining limit:** well-formed framing alone cannot reveal a whole missing member.
Step 2 now compares independent SEC inventories; neither count equality nor hashes
replace that check. Deep file validity, readability and external references also
remain later work. Acquisition success does not mean all evidence is ready to read.

## Evidence

- [Permanent tests and fixtures](../../../../../tests/driver/README.md). Runtime stays
  in `driver/prepare/get/`; tests mirror it.
- The working folders behind these results were deleted on 2026-10-04, after the full download was approved; the numbers here are the record.
