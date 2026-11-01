# XBRL metadata extractor

Extracts exact published metadata for a report's own taxonomy version and company extension. Uses Arelle, independent XML checks and read-only Neo4j queries. No AI, inferred definitions or database writes.

## Run or copy

The reusable core is **`batch.py`, `metadata_audit.py`, `verify.py`, `source_notices.json`, `requirements.txt`**. Copy these together; selection scripts and audit evidence are separate. Tested with Python 3.11. Install the pinned requirements in a virtual environment. Supply `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` through environment variables or this repository's `.env`.

From the repository root:

```bash
venv/bin/python scripts/xbrl_metadata_pilot/batch.py --reports /path/to/reports.json --out /path/to/new_run
```

`--reports` takes a JSON list. Each report needs `accession`, `ticker`, `cik` and `instance_url`. Accessions must be unique. Supply your own input list; the former local lists are privately archived with the historical audit. Inputs are trusted SEC XML-instance URLs selected from this project's graph. The Neo4j queries use this repository's Report/XBRLNode/Fact/metadata relationships.

Fast graph lookups use existing unique ID indexes: Report.id is its accession; XBRLNode.id is its instance URL. This mapping was checked across all 10,468 reports. No new indexes or database writes are required.

Use **`batch.py` as the acceptance boundary**. `run_report()` returns an unchecked candidate for internal use. Each accepted output has `acceptance_status: accepted`, `extraction_status: complete` and `verification.source_status: passed`. Incomplete sources, incorrect text or verification failures produce an abstention/error **without metadata text**. One report failure does not stop the remaining reports. CLI exit code is 1 if any report is not accepted.

## Output and restart

- `elements`: namespace/name identity, category, exact documentation and other labels, schema annotations, references, typed domains and graph matches. Preserve role, language, URL and source hash. `custom` identifies a company-owned declaration; labels for standard concepts can also come from company files, so use each resource's source URL. `documentation_status: absent` means the complete checked sources contain no documentation label; it is a valid result.
- `company_passages`: full tagged text blocks, potentially HTML, associated only with their own concept/report/context. These are published passages, not generated explanations for other concepts.
- `relationships`, `roles`, `source_manifest`: report structure and provenance. Fact identity checks are separate from numeric-value validation.
- `verification.graph_status`: existing graph gaps or ambiguous fact links may require review even when source metadata passes. Do not treat accepted source text as proof that every database link is sound.

Results and checksum receipts are written atomically per accession. Restart skips only accepted results with matching input, code/dependencies and output checksum; failures retry. Resume preserves a snapshot: **use a new output folder to audit changed graph/source data**. Arelle uses its normal local cache and freshness checks. One controller is reused per process; every report model is closed. Use one writer per output folder and do not share the controller between threads. The large audit uses four separate processes/output folders.

For ongoing ingestion, see [the integration contract](INGESTION.md). Append new reports; include a stable `ingestion_revision` per completed ingestion run to refresh reprocessed accessions. This is supported by the existing input checksum. A live completion caller/watch process is separate from the extractor.

## Evidence and limits

See [the concise handoff](../../.claude/plans/Drivers/DriversFinal/XBRL_Definitions.md). The September 30, 2026 audit recorded 981 reports / 795 companies passing source checks; failed/withheld extraction was 0%, while 14.4% of report-metadata entries had no published documentation. The final 301-report company-separated sample, 33 tests, all-report restart and five-file copy checks passed then. Repeated comparisons measured 31.4% less elapsed time with preserved data. These are historical results, not a new qualification of the current checkout.

On November 1, 2026, the owner retired full historical replay and the old 33-test audit. Its untracked tests and bulk fixtures were removed after private preservation of the useful source, final results, strategy, queries, outcomes, hashes and one complete failure/recovery example. The private archive is `/home/faisal/prepare_cleanup_review_20261031/clean_worktree_20261101/CODEX_MAIN_A3_PRIVATE_KEEPERS.tar.gz`; `CODEX_MAIN_A3_PRIVATE_KEEPERS_INDEX.json` beside it lists original paths and verified hashes. Current tracked tests and their five real HTML inputs remain in place elsewhere in the repository.

The selected example includes all 59 pinned raw source members. To inspect it without the old Arelle cache, extract the archived files outside the source tree, load a copy of its result, map each `source_manifest[].path` to the saved `source_files/<sha256>` member, and call `verify.verify()`; leave original exports/receipts unchanged. The reduced keeper does not reproduce the complete 981-report audit or all 33 historical tests. No replacement test pass is claimed by this cleanup.

The XML verifier checks published text, identity, associations and completeness where independently established. Arelle owns full XBRL effective-relationship semantics; raw/effective documentation differences cause abstention. Unpublished descriptions, arbitrary prose, other input formats/taxonomy families, orphan graph nodes and production scheduling/storage are outside the proven scope. A finite sample cannot guarantee 100% future correctness.
