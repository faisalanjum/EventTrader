# Ongoing ingestion: integration contract

The extractor takes reports as input; the 981-report audit list is a frozen test set, not a production limit. It supports 10-K, 10-Q and their amendments. New accession numbers append normally. `test_incremental.py` and the real CLI check in `evidence/optimized_20260930/incremental_live_check.json` cover adding reports and changing the caller revision without rerunning unchanged reports. The real check changes the revision input; it does not re-ingest or modify graph data.

Use the existing ingestion completion flow to invoke extraction after graph writes have finished. `Report.xbrl_status = 'COMPLETED'` is the candidate filter; do not schedule QUEUED/PROCESSING/FAILED reports as completed work. Keep extractor failures in a retry list.

**Completion status is not proof of complete graph persistence.** The current classifier checks facts built in memory and explicitly excludes asynchronous write failures. Preserve `verification.graph_status` and its issues separately from accepted source metadata. The audit intentionally tests source extraction even for existing incomplete graph records.

For a report ingested again, add an `ingestion_revision` field to its input: a durable identifier for that completed ingestion run. Keep it stable across extractor retries and change it after re-ingestion. The existing request checksum includes every input field, so a changed revision reruns that accession automatically. An alternative is a new output directory for each ingestion run. Do not generate a new revision on every polling cycle.

The current graph has no demonstrated reliable ingestion-completion revision. `Report.updated` is an upstream report update, not an ingestion-run marker, and is absent on the checked control. Polling COMPLETED status alone cannot detect a completed → processing → completed cycle between polls. The future caller must provide the completion event/revision; no watcher or ingestion writer is installed by this extractor audit.

Read-only candidate selection for that caller:

```cypher
MATCH (r:Report)-[:HAS_XBRL]->(x:XBRLNode)
WHERE r.formType IN ['10-K','10-Q','10-K/A','10-Q/A']
  AND r.xbrl_status = 'COMPLETED'
RETURN r.accessionNo AS accession, r.cik AS cik, r.cik AS ticker,
       x.id AS instance_url, r.formType AS form
ORDER BY accession
```

The query uses CIK as the display name; the caller may supply a ticker instead. `Report.symbols` is a JSON string, not a Cypher list. This exact query returned 10,465 unique, complete input rows: see `evidence/optimized_20260930/ingestion_query_check.json`.

Evidence: `evidence/optimized_20260930/ingestion_inventory.json`. Live inventory at this audit: 10,465 COMPLETED linked reports and 3 PROCESSING. Code boundaries: `neograph/xbrl_worker_loop.py` writes the final status; `neograph/mixins/xbrl.py` does the same for the local worker; `neograph/xbrl_status_helper.py` explains the completion limit. No ingestion code or Neo4j data was changed.
