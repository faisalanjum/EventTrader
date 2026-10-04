# SEC dot-stuffing: verify bytes before repair

**Status — 2026-10-03:** the original `acquire.patch` is rejected. The revised scanner still needs the three fixes below; completed comparisons must be reviewed before repairing saved files. This replaces the earlier instructions in this file.

**Goal:** recover exact member-file bytes while preserving the compressed SEC package, provenance and existing evidence. Reuse the current downloader and cache; no AI, company-specific rules or new framework.

## What is established

`driver/prepare/get/acquire.py::_decode_member` always changes line-leading `..` to `.`. That restores stuffed lines but deletes a genuine dot from unstuffed lines, including encoded binary files. Northrop's `0001133421-25-000023/Financial_Report.xlsx` exposed the problem.

Neither year, another line's dots, file size, signature nor ZIP member checksums prove which interpretation is original. The rejected patch corrupts a valid PDF without changing its size or signature. Two different ZIPs can also pass every member checksum. The earlier year-filtered scan and “zero edge cases” result are not proof of safety.

## Required sequence

1. **Scan originals.** Read every cached submission across all years, including failed acquisitions. Validate package/member framing and metadata. Count unavailable, malformed and unprocessed packages explicitly.
2. **Compare interpretations per member.** From unchanged `<TEXT>` bytes, decode both keeping dots and removing one leading dot from each `..` line. If both succeed with identical bytes, no dot-resolution request is needed. Preserve decoding failures; do not select a candidate by guesswork.
3. **Obtain independent evidence.** For differing candidates, fetch SEC's separate member copy through the existing cache-first campaign: **5 requests/second shared across the campaign, retries included; stop on any 403**. Validate any served wrapper's filename/type/sequence before removing it. Compare the entire resulting body byte-for-byte. Any additional transformation must be individually verified and recorded; no arbitrary script removal, text normalization or dot-line-only comparison. Unavailable, ambiguous or unexplained results stay unresolved. ZIP checks remain diagnostics; unsupported/encrypted checks mean unchecked.
4. **Review the complete report.** Record package/member identity, both candidate hashes, saved hash, reference URL/hash, transformations, decision/reason and decoder code fingerprint. Reconcile the input inventory with every outcome. Approve repairs only for independently resolved members; report unfinished work rather than claiming completion. Earlier request/time estimates remain estimates.
5. **Repair without overwriting evidence.** First support and test old and corrected versions: current `read_package` regenerates and compares the whole manifest, and the save path uses only the raw-package hash. Merely changing the decoder label or replacing a manifest is insufficient. Preserve raw packages, old manifests and receipts; record the new decoder version and replayable per-member decisions. Check affected Step 3 source packets before publishing corrections; never silently change frozen bytes or offsets. Re-read corrected versions, compare exact member hashes, and confirm unchanged members remain identical. Retry Northrop only after its interpretation is resolved.

The same verification rule must cover future ingestion. Parsing should replay recorded decisions; missing evidence stays unresolved. Do not reuse the unchanged decoder label to bypass cache checks. Deploy only with acquisition jobs stopped; verify deployed code hashes and cache-only replay.

## Three scanner fixes still required

In `prepare_work/sec_filings_job/claude_dot_scan/claude_dot_scan.py`:

| Area | Tested failure | Smallest correction |
|---|---|---|
| `judge()` | An unreviewed script URL with the expected tag shape is removed and accepted. | Keep script-removal-only matches unresolved until that insertion is verified; record its exact range/hash. |
| `frame()` | Duplicate `<FILENAME>` fields are accepted by choosing the first; production rejects them. | Enforce the existing strict framing/metadata rules; report malformed packages. |
| `compare()` | A 403 on the final member writes `STOP.json` but leaves the summary's stop reason empty. | Record the failed member and stop reason immediately. Transport already prevents further requests. |

These are evidence-collection fixes, not permission to repair files. Keep the independent blank-line fix separate.

## Verification before deployment

- Keep real positive controls for stuffed and unstuffed members; compare whole bytes with independently served copies.
- Retain regressions for the valid-PDF counterexample, two CRC-valid ZIP interpretations, malformed wrappers/metadata, unverified script changes, unavailable references and a final-request 403.
- Test cache replay, unchanged old versions, corrected versions, and explicit unresolved outcomes; run focused and full prepare tests. Full-population comparison results are still required—green unit tests alone cannot certify saved files.

Evidence: [original patch rejection](/home/faisal/prepare_work/sec_filings_job/finding_zip_0001133421-25-000023/CODEX_REVIEW.md), [fresh PDF reproduction](/tmp/dot_stuffing_doc_check_20261003/CODEX_PROBES.json), [whole-file/ZIP checks](/home/faisal/prepare_work/downloader_fixes_20261003/codex_evidence_20261003T015521Z/dot_checks.json), [scanner recheck](/home/faisal/prepare_work/downloader_fixes_20261003/prepare_five_fixes_recheck_copy.md), [reproducible scanner cases](/tmp/prepare_five_fixes_recheck_20261003/check.py). The older finding and patch files are historical evidence, not current instructions.
