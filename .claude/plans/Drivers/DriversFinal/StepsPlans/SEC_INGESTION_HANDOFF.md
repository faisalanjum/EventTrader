# SEC ingestion → prepared extraction: handoff

Verified 2026-11-01, 9:46–10:00 AM EST, read-only: `main` 0bd4a5a51, live cluster, Redis, Neo4j, code. Live state beats this note; re-check with §8 before acting.

**Owner goal:** feed whole-filing extraction and OCR into the existing SEC ingestion. **Next task:** decide how prepared content enters Neo4j (§6).

## 1. Live state

| Part | State |
|---|---|
| Ingestion | **Stopped.** `processing/event-trader` (SEC intake + graph writer) = 0 replicas. Newest Report `created` 2026-04-28. Data-provider subscriptions off (owner; not checked). |
| Enricher | `report-enricher`: 1 pod (KEDA 1–5), image `e72cf15d…`. Old code: plain `blpop`, no prepared call, no prepared config or mount. |
| Prepared extraction | **Built, not active.** Pin `faisalanjum/report-enricher@sha256:7d057ab66ac7e6ab3b97a31cd2c828b4123df2704a5d395a0e6c17164a089010` (`prepared-ocr-docs-20261101`), manifest `4a74c64e…`. ConfigMap `prepared-adapter-config` absent; `prepared-adapter-canary-config` (Oct 31 AMG canary) unused. Go-live: owner only. |
| OCR server | None. RunPod test resources deleted. No automatic GPU. |
| XBRL | `xbrl-worker-heavy` 3, `xbrl-worker-medium` 2 (KEDA 2–4), `edge-writer` 1. Running worker, processor, edge-writer, status and routing files = checkout. |
| Unrelated | `extraction-worker` (0; KEDA 0–7): LLM extraction from `extract:pipeline`. |
| Endpoints | Redis `infrastructure/redis`, db 0 (NodePort 31379). Neo4j `neo4j/neo4j-bolt` (NodePort 30687); credentials `.env` `NEO4J_*`. |

## 2. Flow

```text
SEC WebSocket (live) / REST (history) → Redis raw → filter + metadata → enrich queue
→ report-enricher → Redis processed → returns → withoutreturns / withreturns
→ Neo4j Report + content nodes → XBRL queues (10-K/10-Q) → facts
```

| Step | Code | Behavior and Redis keys |
|---|---|---|
| Intake | [DataManagerCentral](../../../../../config/DataManagerCentral.py), [sec_schemas](../../../../../secReports/sec_schemas.py) | REST requests only the 12 forms; WebSocket takes every form (validator commented out). 10-K/Q families need the XML URL; others XML or `.txt`. Exhibits: `EX-10.*`/`EX-99.*` only, one per type. `set_filing` → `reports:{live\|hist}:raw:<acc>.<filedAt in UTC, ':'→'.'>`, queue `reports:queues:raw`, `tracking:meta:reports:<ID>`. |
| Filter | [ReportProcessor](../../../../../redisDB/ReportProcessor.py), [BaseProcessor](../../../../../redisDB/BaseProcessor.py) | 12 forms + tracked symbol; company identity; market session, benchmarks, return schedule. → `reports:queues:enrich`; raw deleted. |
| Enrich | [report_enricher](../../../../../redisDB/report_enricher.py) | SEC API sections (8-K: listed items only), flattened text for other forms, selected exhibits, ≤4 statement JSONs (CIK must match). → `reports:{live\|hist}:processed:<ID>` (2-day TTL), list `reports:queues:processed`, channel `reports:live:processed`. `enriched=true` is unconditional. |
| Returns | [ReturnsProcessor](../../../../../eventReturns/ReturnsProcessor.py) | Adds hourly/session/daily stock and benchmark returns. → `reports:withoutreturns:<ID>` until complete, then `reports:withreturns:<ID>` (no TTL); schedule `reports:pending_returns`. |
| Graph | [pubsub](../../../../../neograph/mixins/pubsub.py), [report](../../../../../neograph/mixins/report.py), [reconcile](../../../../../neograph/mixins/reconcile.py) | Listener on both return channels; startup/batch scan; hourly reconcile. Does not wait for returns. |

12 forms ([feature_flags](../../../../../config/feature_flags.py)), live Reports: 8-K 29,672 · 10-Q 7,301 · 10-K 2,993 · 425 1,206 · 8-K/A 631 · SCHEDULE 13D/A 531 · 10-K/A 137 · SCHEDULE 13D 70 · 10-Q/A 41 · 6-K 31 · SC TO-I 13 · SC 14D9 7.

## 3. Neo4j (live)

**Report:** 42,633; `id` = accessionNo (no Redis suffix); `created` 2023-01-03 → 2026-04-28. JSON copies on the node: `extracted_sections` 40,766, `exhibit_contents` 25,299, `financial_statements` 10,032; no filing text. `updated` and `prepared_extraction`: none.

| Report → child | Child `id` / text field | Nodes / linked / unlinked |
|---|---|---:|
| `HAS_SECTION` → `ExtractedSectionContent` | `<acc>_<section_name>` / `content` | 198,706 / 198,641 / 65 |
| `HAS_EXHIBIT` → `ExhibitContent` | `<acc>_EX-<key>`, e.g. `<acc>_EX-EX-99.1` / `content` | 38,946 / 38,946 / 0 |
| `HAS_FILING_TEXT` → `FilingTextContent` | `<acc>_text` / `content` | 2,689 / 2,689 / 0 |
| `HAS_FINANCIAL_STATEMENT` → `FinancialStatementContent` | `<acc>_<statement_type>` / `value` (JSON) | 38,950 / 38,942 / 8 |

Children carry `filing_id`, `form_type`, `filed_at` and, when known, `filer_cik`. Unique `id` constraints (Report, 4 content labels, XBRLNode) and full-text indexes (4 content labels) are online. Readers: [eight_k_packet](../../../../../scripts/earnings/builders/eight_k_packet.py), [prior_financials](../../../../../scripts/earnings/builders/prior_financials.py).

Other links: `PRIMARY_FILER` 42,243 and `REFERENCED_IN` 519 → Company (stock, sector, industry, macro returns); `INFLUENCES` → Industry 42,639, Sector 42,618, MarketIndex 42,610 (benchmark returns); `IN_CATEGORY` → AdminReport 42,618; `GuidanceUpdate -FROM_SOURCE→` Report 3,587 (532 Reports). Reports lacking a link: Company 15, Sector 15, Industry 15, AdminReport 15, MarketIndex 23. Only AdminReport must pre-exist ([Neo4jInitializer](../../../../../neograph/Neo4jInitializer.py)); the others are MERGEd.

**XBRL** ([routing](../../../../../neograph/mixins/xbrl.py), [worker](../../../../../neograph/xbrl_worker_loop.py), Arelle [processor](../../../../../XBRL/xbrl_processor.py)). Eligible: `is_xml`, CIK, status not COMPLETED/PROCESSING/SKIPPED/REFERENCE_ONLY/FAILED. 10-K, 10-K/A → `reports:queues:xbrl:heavy`; 10-Q, 10-Q/A → `reports:queues:xbrl:medium`; others SKIPPED. Edges go through `edge_writer:queue` (`EDGE_QUEUE` set on running workers; [edge writer](../../../../../neograph/edge_writer_loop.py)).

```text
Report -HAS_XBRL-> XBRLNode (id = instance URL) <-REPORTS- Fact
Fact -> Concept · Unit · Period · Context · Member · Dimension;  Fact -CALCULATION_EDGE-> Fact
Context -> Period · Company;  Abstract -PRESENTATION_EDGE-> Fact/Abstract;  Domain -HAS_MEMBER-> Member
```

Live: 10,468 XBRLNode; 13,775,616 Fact. `xbrl_status`: SKIPPED 31,787 · COMPLETED 10,465 · REFERENCE_ONLY 375 · PROCESSING 3 · FAILED 3.

## 4. Defects and limits (verified in code)

1. **Dedup regression.** `d84dad2` (Mar 31) made `set_filing` skip accessions in `reports:confirmed_in_neo4j`. `397268b29` (Oct 31, extraction commit) silently restored the old processed-list check, the blocking bug in [report-ingestion-gaps](../../../Infra_Bugs/report-ingestion-gaps.md), which still says "deployed". Only the producer (event-trader: `sec_websocket`, `sec_restAPI`) calls `set_filing`. Fix restored in checkout 2026-11-01 (owner-approved; test `tests/redisDB/test_set_filing_dedup.py`); live only after the event-trader image is rebuilt.
2. `reports:confirmed_in_neo4j` is written on success and read by the restored `set_filing` check. Root rechecked all 42,633 entries against the graph's Report IDs at 10:51 AM EST: no differences and no expiry.
3. Graph write and Redis stamp (`inserted_into_neo4j_at`) are separate. Batch and reconcile skip stamped Reports and delete their later return copies: **only the live listener applies late returns.** Only `withreturns` keys are deleted after a write.
4. Silent failures: content writers log and return empty; [Neo4jManager](../../../../../neograph/Neo4jManager.py) `merge_relationships` swallows per row; a MATCH on a missing node writes nothing; Reports without symbols succeed with no Company links; reconcile's confirmed-set write uses `except: pass`.
5. `updated` is never set, so rewrites keep the original description, form, period and section, statement, exhibit-content and text JSON; `exhibits`, `entities`, `items`, `symbols` are overwritten.
6. XBRL "completed" means facts in memory, not persisted edges. XBRL and edge workers pop jobs before processing.
7. **Never read through app code:** default `EventTraderRedis()` deletes `reports:*:raw:*` and writes `admin:tradable_universe:*`; `DataManagerCentral` startup writes Neo4j. Use `redis-cli` and the Neo4j driver in `READ_ACCESS`.
8. [ROLLOUT.txt](../../../../../k8s/prepared-extraction/ROLLOUT.txt) now matches the 1 November qualified image `7d057ab6…`, manifest `4a74c64e…`, and deployment patch. This documentation correction does not activate anything.

## 5. Prepared extraction (built, inactive)

- **Entry:** [prepare_filing](../../../../../redisDB/prepared_filing.py)`(filing, config)`: `accessionNo`, `cik`, `formType`; explicit config, no defaults (docstring cites untracked `ADAPTER_DESIGN.txt`).
- **Steps:** verified full package → HTML/XML extraction ([driver/prepare](../../../../../driver/prepare/README.md)) → OCR only if `config.ocr` is set and extraction did not fail.
- **OCR:** Chandra on a self-hosted vLLM endpoint (`VLLM_API_KEY`; RunPod was the tested host) plus local PP-OCR (RapidOCR) and OnnxTR ([readers](../../../../../driver/prepare/pictures/readers.py)). Readings reused; retries bounded; `fidelity: unverified`.
- **Storage:** node minisforum2, host `/home/faisal/data/sec_prepared` → pod `/data/sec_prepared` ([worker.patch](../../../../../k8s/prepared-extraction/worker.patch.yaml)); `output_root` `/data/sec_prepared/output` ([adapter-config](../../../../../k8s/prepared-extraction/adapter-config.yaml)): `package/versions/<acc>/<package sha>/`, `runs/<acc>/<package sha>/<plan sha>/RECEIPT.json`, `…/ocr/receipts/`.
- **Hook:** with `PREPARED_EXTRACTION_CONFIG`, the enricher uses claim/ack queues (`reports:queues:enrich:processing`, `reports:queues:enrich:dead`) and adds `prepared_extraction` {status, ≤20 reasons, package and manifest sha, receipt path and sha, fidelity, ocr} inside the 2-day processed record. **The graph writer ignores it;** receipts on disk are the only lasting record.
- **Earlier outputs:** `/home/faisal/prepare_cleanup_review_20261031/live_filing/filing` (outside the repo, 16 MB).
- **Go-live (owner):** [README](../../../../../k8s/prepared-extraction/README.md) → `ROLLOUT.txt` (§4.8), `REDIS_AOF.txt`, `ROLLBACK.txt`; first confirm the OCR server, endpoint and Secret.

## 6. Next decision

How prepared content enters Neo4j: [PrepareStep D16](../PrepareStep.md), settled at Step 5. Open (owner, 2026-10-02): new text **replaces** or sits **beside** existing section/exhibit text. Decided (owner, 2026-10-05): one `ImageContent` node per picture, beside the text. Rules ([AGENTS.md](../../../../../AGENTS.md)): reuse native library features; TDD for behavior changes; Neo4j writes need the owner's explicit approval.

## 7. Spot-checked filings

AMG 8-K `0001004434-23-000015`: 3 sections, 1 exhibit · Apple 10-K `0000320193-25-000079`: 21 sections, 4 statements, 1,042 facts · Apple 10-Q `0000320193-26-000006`: 11 / 4 / 617. All content non-empty; `filing_id` = Report `id`.

## 8. Re-verify (read-only)

```bash
kubectl -n processing get deploy,cm
kubectl -n processing get pods -o custom-columns=NAME:.metadata.name,IMAGE:.status.containerStatuses[0].imageID
R='kubectl -n infrastructure exec deploy/redis -- redis-cli'
for q in raw enrich processed xbrl:heavy xbrl:medium; do $R LLEN reports:queues:$q; done; $R LLEN edge_writer:queue
$R ZCARD reports:pending_returns; $R SCARD reports:confirmed_in_neo4j
$R --scan --pattern 'reports:withoutreturns:*' | wc -l
```

Snapshot: queues 0 except `reports:queues:processed` 82; withoutreturns 70; withreturns 0; processed payloads 0; pending 178; confirmed 42,633.

Neo4j: `neo4j.GraphDatabase`, `READ_ACCESS`, `execute_read`:

```cypher
MATCH (r:Report) RETURN r.formType, count(*) ORDER BY count(*) DESC;
MATCH (:Report)-[e]->(n) RETURN type(e), labels(n), count(*);
MATCH (n:ExtractedSectionContent) WHERE NOT EXISTS { (:Report)-[:HAS_SECTION]->(n) } RETURN count(n);
MATCH (r:Report) RETURN r.id;  // compare with SMEMBERS reports:confirmed_in_neo4j
```
