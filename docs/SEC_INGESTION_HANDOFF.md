# SEC ingestion and extraction handoff

This is the separate ingestion review's dated snapshot. Current image pins and
activation instructions are in the [operating guide](../k8s/prepared-extraction/README.md);
the 31 October OCR image cited below is historical. Cleanup preserved this note
without rerunning its live database inspection.

Owner goal: understand existing ingestion before integrating whole-filing extraction and RunPod OCR. Continue this one document after compaction/session changes. Subscriptions are off **per owner**; this review changed documentation only.

Verified **November 1, 2026, 9:25–9:34 AM EST** (`America/Toronto`): source/container inspection and read-only Redis/Neo4j checks. No fresh ingestion, model calls, deployment changes or graph writes. Snapshot counts do not certify source coverage or accuracy.

## Current flow

```text
SEC API live feed / historical search
  -> Redis raw -> report filtering and metadata -> enrichment worker
  -> Redis processed -> price-return calculation -> Redis withoutreturns / withreturns
  -> Neo4j Report and content nodes
       -> separate jobs for tagged financial facts
```

| Step | Actual behavior and source |
|---|---|
| Intake | [ReportsManager](../config/DataManagerCentral.py): SEC live WebSocket/historical REST. [Schema](../secReports/sec_schemas.py): XML URL required for 10-K/Q families; otherwise XML or submission-text URL. Exhibit map keeps only `EX-10.*`/`EX-99.*`, keyed by type, not all attachments. |
| Raw | [set_filing](../redisDB/redisClasses.py): writes `reports:{live|hist}:raw:<accession>.<filedAt with colons replaced by dots>`, queues its key in `reports:queues:raw`, stamps `tracking:meta:reports:<ID>`. Live/history share one database. |
| Filter | [ReportProcessor](../redisDB/ReportProcessor.py): allowed form + tracked symbol; standardizes company identity. [Metadata](../redisDB/BaseProcessor.py): market session, benchmarks, return schedules. Heavy payload goes to `reports:queues:enrich`; Redis raw record may then be deleted. |
| Enrich | [Worker](../redisDB/report_enricher.py): SEC API sections for 8-K/K/Q families, flattened other text/selected exhibits, up to four SEC API statement JSON objects. Saves `reports:{live|hist}:processed:<ID>` for two days; records key in `reports:queues:processed`; publishes key on `reports:live:processed`. `enriched=true` does not prove complete reading. |
| Price returns | [ReturnsProcessor](../eventReturns/ReturnsProcessor.py): preserves payload, adds hourly/session/daily stock/benchmark changes. Saves `reports:withoutreturns:<ID>` while pending, otherwise `reports:withreturns:<ID>`; publishes ID on matching channel. Future calculations use `reports:pending_returns`. **Graph loading need not wait for all returns.** |
| Graph | [Listener](../neograph/mixins/pubsub.py) consumes both return channels. [Report writer](../neograph/mixins/report.py) also serves startup/batch scans. [Reconciliation](../neograph/mixins/reconcile.py) checks missing/newer records hourly. |

The [12 allowed forms](../config/feature_flags.py), with live Report counts: 8-K 29,672; 8-K/A 631; 10-K 2,993; 10-K/A 137; 10-Q 7,301; 10-Q/A 41; 425 1,206; SCHEDULE 13D 70; SCHEDULE 13D/A 531; 6-K 31; SC TO-I 13; SC 14D9 7. Intake is restricted to this list.

## What Neo4j stores

All **42,633** Reports use `id = accessionNo`, without Redis's timestamp suffix. [ReportNode](../neograph/EventTraderNodes.py) stores filing metadata and JSON copies of sections/exhibits/statements; its serializer excludes filing text. The [content writers](../neograph/mixins/report.py) separately create:

| Report relationship -> node | Child ID / payload | Live nodes / links from Report / unlinked nodes |
|---|---|---:|
| `HAS_SECTION` -> `ExtractedSectionContent` | `<accession>_<section_name>` / `content` text | 198,706 / 198,641 / 65 |
| `HAS_EXHIBIT` -> `ExhibitContent` | `<accession>_EX-<exhibit-map key>` / `content` text | 38,946 / 38,946 / 0 |
| `HAS_FILING_TEXT` -> `FilingTextContent` | `<accession>_text` / `content` text | 2,689 / 2,689 / 0 |
| `HAS_FINANCIAL_STATEMENT` -> `FinancialStatementContent` | `<accession>_<statement_type>` / whole statement JSON in `value` | 38,950 / 38,942 / 8 |

Children retain filing/form IDs and available company/time fields. ID and child full-text indexes are online. Existing [8-K readers](../scripts/earnings/builders/eight_k_packet.py) and [financial readers](../scripts/earnings/builders/prior_financials.py) follow these links.

Report links outward to Company via `PRIMARY_FILER`/`REFERENCED_IN`, carrying price returns; to Sector/Industry/MarketIndex via `INFLUENCES`; to AdminReport via `IN_CATEGORY`. Targets come from the [initializer](../neograph/Neo4jInitializer.py); invalid company/sector/industry data can prevent links. Shared infrastructure also serves [news](../neograph/mixins/news.py) and [transcripts](../neograph/mixins/transcript.py).

Tagged financial data (XBRL) is **separate from statement JSON and OCR**. [Queue routing](../neograph/mixins/xbrl.py): eligible 10-K/10-K/A -> `reports:queues:xbrl:heavy`; 10-Q/10-Q/A -> `reports:queues:xbrl:medium`; other forms skipped. [Workers](../neograph/xbrl_worker_loop.py) use [Arelle, the financial-file reader](../XBRL/xbrl_processor.py):

```text
Report -HAS_XBRL-> XBRLNode <-REPORTS- Fact
Fact -> Concept / Unit / Period / Context; Context -> Company / dimensions / members
```

XBRLNode ID is the source URL. Some links use `edge_writer:queue` and the [edge writer](../neograph/edge_writer_loop.py). Live: 10,468 XBRLNode; 13,775,616 Fact. Report statuses: COMPLETED 10,465; SKIPPED 31,787; REFERENCE_ONLY 375; PROCESSING 3; FAILED 3.

## Existing failure and update limits

- Graph writes and Redis completion stamps are separate transactions. Success stamps `inserted_into_neo4j_at`; checkout code adds `reports:confirmed_in_neo4j`; successful final return records are deleted. Batch/reconciliation can skip stamped records. Full comparison: confirmation set = graph IDs, **42,633 each, zero differences**, not proof of complete content.
- Both checkout and running enrichment's bundled `set_filing` still deduplicate against the processed list, contrary to the older [gap plan](../.claude/plans/Infra_Bugs/report-ingestion-gaps.md).
- [Content](../neograph/mixins/report.py) and [database helpers](../neograph/Neo4jManager.py) can swallow failures. Success is not proof of all children/links; measured missing links are in the table, causes unestablished.
- All Reports lack `updated`; the writer's date-versus-null comparisons keep existing Report JSON. Child nodes are updated separately.
- [XBRL completion](../neograph/xbrl_status_helper.py) checks in-memory facts, not edge persistence. XBRL/edge workers pop jobs before processing.
- Read with native clients: [EventTraderRedis construction](../redisDB/redisClasses.py) clears raw keys by default; application startup can write Neo4j.

## New extraction and RunPod recap

[prepare_filing](../redisDB/prepared_filing.py) takes `accessionNo`, `cik`, `formType` and qualified configuration: verified full package -> [HTML/XML extraction](../driver/prepare/README.md) -> optional [image/PDF-page OCR](../driver/prepare/pictures/saved.py). Chandra runs on authenticated RunPod; two local readers also contribute. Companion files remain preserved; unread/incomplete items stay explicit. Saved successful readings are reused; technical retries are bounded; OCR has `fidelity: unverified`.

- [Production configuration](../k8s/prepared-extraction/adapter-config.yaml): `/data/sec_prepared/output` = `/home/faisal/data/sec_prepared/output` on **minisforum2**. Originals: `package/versions/<accession>/<source hash>/`; extraction: `runs/<accession>/<source hash>/<plan hash>/`; OCR: that run's `ocr/`. `RECEIPT.json` records extraction; `ocr/receipts/` records combined results. Redis holds the location/status.
- [Earlier outputs](/home/faisal/prepare_cleanup_review_20261031/live_filing/filing) exist. [Qualification](../k8s/prepared-extraction/OCR_QUALIFICATION.txt) records test RunPod deletion. Future execution needs a ready authenticated server; no automatic GPU allocation. Follow the [existing run instructions](../k8s/prepared-extraction/README.md).
- **Not active:** main `processing/event-trader` replicas = 0; enricher = 1, without prepared config/mount; `prepared-adapter-config` absent. Running enricher digest: `e72cf15d4cc39a23beb91a20af019aae9322232995b432067bb26fae34e8f50c`; prepared OCR image: `7d1be4640e4806a526c62b5d5a92808940a7e49fb5367d049502c91ee40ddd70`.
- Running enricher uses the older queue pop, no prepared call; its bundled writer differs from checkout. Stopped event-trader image contents were not verified. The sampled medium XBRL worker's worker/classifier/processor/edge-writer files match checkout exactly.

**Missing integration:** the optional [enrichment hook](../redisDB/report_enricher.py) adds Redis `prepared_extraction`, but the graph writer ignores it/files; zero Reports have that property. The next task must settle content mapping. [D16](../.claude/plans/Drivers/DriversFinal/PrepareStep.md) records replace-versus-beside text as open and an earlier ImageContent decision; nothing was changed here. Follow [project rules](../AGENTS.md): native-library reuse, TDD for changes, explicit approval for graph writes.

## Read-only verification for the next session

Source baseline: HEAD `4eda437eaf0292c1a2b180a306828786300b86f1`, with existing working-tree changes. Live evidence wins over historical plans.

Real examples, nonempty content and matching `filing_id` checked: AMG 8-K `0001004434-23-000015` (3 sections/1 exhibit); Apple 10-K `0000320193-25-000079` (21 sections/4 statements/1,042 facts); Apple 10-Q `0000320193-26-000006` (11/4/617).

Use `neo4j.GraphDatabase`, `READ_ACCESS`, `execute_read`, existing private credentials:

```cypher
MATCH (r:Report) RETURN r.formType, count(*) ORDER BY count(*) DESC;
MATCH (r:Report) RETURN count(r), count(r.updated), count(r.prepared_extraction);
MATCH (:Report)-[e]->(n) RETURN type(e), labels(n), count(*) ORDER BY type(e);
MATCH (r:Report) RETURN r.id; // Compare the whole result with Redis SMEMBERS below.
MATCH (n:ExtractedSectionContent)
WHERE NOT EXISTS { MATCH (:Report)-[:HAS_SECTION]->(n) } RETURN count(n);
// Repeat the last query for each content label and its relationship from the table.
MATCH (r:Report {id: $accession}) OPTIONAL MATCH (r)-[e]->(n)
RETURN type(e), labels(n), count(n);
```

Redis snapshot: raw/enrichment/XBRL/edge queues empty; processed list 82; withoutreturns 70; withreturns/processed payloads 0; pending-return schedule entries 178 (different units). Recheck via native `LLEN`/`ZCARD`/`SCAN` and `SMEMBERS reports:confirmed_in_neo4j`. Deployment: `kubectl -n processing get deploy`, enricher environment/mounts/image ID, adapter config map. Provider subscription status was not independently checked.
