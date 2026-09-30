# XBRL definitions — session handoff (2026-09-30)

## Goal and verified status

Automatically collect published definitions/descriptions for concepts, dimensions, members and other report metadata, preserving each report’s actual taxonomy version. Numeric facts link to metadata; they do not need definitions.

**Ten-report pilot passed:** Apple, Mercury, Gladstone, Merus and Mosaic; two reports each, with different actual taxonomy versions. **Read-only; no Neo4j or production changes.**

| Result | Count |
|---|---:|
| Report-metadata entries checked | 6,792 (4,824 distinct namespace/name identities) |
| Published documentation found / absent | 5,753 / 1,039 |
| Company documentation found / company entries | 1,345 / 1,362 |
| Explicitly tagged company passages | 508 |
| Stored fact/concept identities checked / mismatches | 13,207 / 0 |

All **13 tests passed**: source text, references, schemas, missing documentation, original three-report regression, version controls, failure handling and restart. Eleven typed dimensions were included. Extraction took **139 seconds using the existing download cache**; tests took 98 seconds. Restart skipped all ten unchanged reports. These timings do not establish whole-database performance.

**Mosaic’s 17 missing company definitions are confirmed in source XML** (11 in 2022, six in 2025); their labels remain available. Of all 1,039 documentation gaps, 471 have references. No universal guarantee of complete descriptions.

## What the fields mean

- **Taxonomy text:** preserve exact documentation, other labels/guidance, role and language. Documentation can be short; it is not automatically a rich explanation.
- **References:** published pointers, not the referenced accounting text.
- **Company passages:** complete text blocks attached only to their explicit concept, report and context. They can contain HTML/tables. No inferred links to other concepts/members and no AI-generated definitions.
- **Correction:** XBRL supports long descriptions, guidance, examples and custom labels; two text fields were an oversimplification ([official guidance](https://www.xbrl.org/guidance/label-roles/)). A definition linkbase mainly supplies relationships. Gladstone’s standard `LineOfCredit` documentation is 217 words.

## Reuse — do not repeat discovery

Repository paths:

- [Code and instructions](../../../../scripts/xbrl_metadata_pilot/README.md): `batch.py`, reusable reader, frozen `reports.json`, tests.
- [Final results](../../../../scripts/xbrl_metadata_pilot/evidence/latest/RESULTS.md): company breakdown; adjacent JSON holds every extracted item, source, timing and status.
- `scripts/xbrl_metadata_pilot/evidence/source_files/`: **199 exact source files**, named by content hash; each result’s `source_manifest` maps URLs/cache paths to hashes.
- `evidence/latest/reviewed_snapshot.json`: code hashes, function/exception inventory and named untested cases. `artifact_hashes.json` verifies saved evidence.
- `evidence/prior/`: preserved earlier scripts, comparisons, results and source checks. README explains restoring old temporary baselines for tests. Evidence is stored as regular project files, not only under `/tmp`.

Run from the repository root:

```bash
venv/bin/python scripts/xbrl_metadata_pilot/batch.py --out scripts/xbrl_metadata_pilot/evidence/latest
```

Complete results resume only when input, code/dependency versions and checksums match. Failed/partial reports retry; use a new output directory for a fresh audit. Reader uses repository `.env` and Arelle’s cache. No credentials are stored in evidence.

**Next bot:** reuse this reader and batch runner. Replace the frozen input list with a Neo4j report query; add bounded automatic retries/download pacing and per-report acceptance checks. Current `complete` means extraction completed, **not** that graph/source checks passed. Before database integration, preserve taxonomy-version identity and report-specific company text, and make repeated writes safe. Inventory actual database formats before adding support; validate wider coverage before claiming readiness. No AI or per-company scripts are needed for this scope.

## Rules and remaining limits

- Identity = **namespace + local name**; derive versions from schemas/imports, not report dates. Retain accession, source URL/hash, role and language. Keep latest-version comparisons separate.
- Apply company additions per filing. Load supplemental documentation with `isSupplemental=True, isDiscovered=True`; capture filing relationships **before** adding supplements.
- Separate present, absent, unsupported and failed retrieval. Do not substitute a short label for missing documentation; a failed download is not proof of absence.
- Pilot covers SEC XML instances using US-GAAP/SRT/SEC taxonomies. IFRS, direct inline-XBRL auditing, generic labels on other object types, inferred company explanations, network recovery and full-database throughput remain unproven.
- Earlier inventory: 10,468 reports, 618,754 concepts, 13,775,616 facts; structural checks only. Original 2026 comparisons changed 20 Apple, 68 Mercury and 20 Gladstone documentation entries.
- Existing unrelated finding: six Gladstone facts retain rounded source copies; unfixed. Historical extraction-software version remains unknown. **Neo4j writes require explicit user approval.**
