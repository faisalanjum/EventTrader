 Review request: SEC dot-stuffing bug (full-run failure #4). Owner approved fixing it after the full run finishes. Do not touch the deployed code while the run is live.
▎
▎ Write-up and files: prepare_work/sec_filings_job/finding_zip_0001133421-25-000023/, starting with FINDING.md.
▎
▎ Bug: Northrop's 10-Q 0001133421-25-000023 failed with "Damaged zip after uudecode" on Financial_Report.xlsx. _decode_member always turns a leading .. into .. SEC stopped dot-stuffing packages around 2025:
▎ - 1,016 local packages: 2023–24 are stuffed (584; no single-dot lines), 2025–26 are not (388; no double-dot lines), and none mix both.
▎ - Northrop's last uu line genuinely starts with ... Decoded without un-doubling, the xlsx passes all 57 CRCs.
▎
▎ Fix (acquire.patch, 6 lines): decide per package from its own bytes. If any line starts with exactly one dot, the package is not stuffed, so never un-double; otherwise keep the old behaviour. No dates, no company rules.
▎
▎ Test (test_acquire.patch): a new test using the real Northrop package trimmed to 85 KB (fixture_0001133421-25-000023.txt.gz). On a scratch copy, 84/84 tests pass; the existing 2023/2025 fixtures' hashes don't move.
▎
▎ Please challenge these choices:
▎ 1. I left the decoder label sec-framing-uu-v1 unchanged. read_package compares whole manifests, so a new label would invalidate every saved version; unaffected packages decode identically.
▎ 2. No zip-retry fallback, kept minimal. The weak spot is an unstuffed package whose only leading-dot line is ... The zip CRC still fails closed for zips; a PDF or image there would be silent. recheck_dots.py lists such packages (edge) for a human look.
▎
▎ After the run ends:
▎ 1. Apply the patch + test + fixture and run the tests.
▎ 2. Deploy to the worker's /data/code and verify the hashes.
▎ 3. Run recheck_dots.py /data/versions (read-only; dry run on the 1,016 local packages found 0 affected, 0 edge).
▎ 4. Rebuild only the affected versions from the cached raw packages (no new SEC downloads).
▎ 5. Retry Northrop from its cached response.
▎ 6. Re-run the earlier zip/size scan over all versions.
▎ 7. Check whether any Step 3 sample file comes from an affected version.
▎
▎ Reply with findings; Claude will apply or adjust.