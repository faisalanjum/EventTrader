# Original source snapshots

Six snapshots supplied the experiment's transcript text and stored structure. Each `<source_id>.json` is an unchanged copy of its original `snapshot.json`; [the archive manifest](../archive_manifest.json) records its original path, size and SHA-256. [snapshot_queries.json](snapshot_queries.json) preserves the query definitions supplied with the earlier snapshot study.

| Snapshot | Call |
| --- | --- |
| [CTAS_2025-09-24T10.00.json](CTAS_2025-09-24T10.00.json) | Cintas, September 24, 2025 |
| [CTAS_2025-12-18T10.00.json](CTAS_2025-12-18T10.00.json) | Cintas, December 18, 2025 |
| [CTAS_2026-03-25T10.00.json](CTAS_2026-03-25T10.00.json) | Cintas, March 25, 2026 |
| [PAYX_2025-09-30T09.30.json](PAYX_2025-09-30T09.30.json) | Paychex, September 30, 2025 |
| [PAYX_2025-12-19T09.30.json](PAYX_2025-12-19T09.30.json) | Paychex, December 19, 2025 |
| [PAYX_2026-03-25T09.30.json](PAYX_2026-03-25T09.30.json) | Paychex, March 25, 2026 |

The model-facing reconstruction is [experiment/sources.json](../experiment/sources.json) with six companion `.txt` files. Per-call final ledgers retain source character positions. Snapshots also contain legacy guidance records for comparison; those records and manual reference labels must not become model inputs.

These are saved graph contents, not independently checked publisher originals. Five snapshots lack speaker metadata; no data was repaired during archiving. Preserving them enables offline inspection without querying or changing the live database.
