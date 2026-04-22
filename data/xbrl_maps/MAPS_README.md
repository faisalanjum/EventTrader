# XBRL Exact-QName Maps

Precision-first revenue and operating-income qname maps for the 783-ticker active universe.

## Files

| File | Rows | Description |
|---|---|---|
| `revenue_map_783.jsonl` | 783 | Post-coordinator-review; 744 resolved, 39 null |
| `operating_map_783.jsonl` | 783 | Post-coordinator-review; 203 resolved, 580 null |
| `revenue_map_783_precoord.jsonl` | 783 | Baseline before coordinator review (757 resolved) |
| `operating_map_783_precoord.jsonl` | 783 | Baseline before coordinator review (234 resolved) |

## Snapshot

- Universe snapshot: `2026-04-22T00:21:51-04:00`
- Wave 2 run completed: 2026-04-22 ~05:45 EST
- Coordinator review applied: 2026-04-22 ~06:27 EST
- 13 revenue and 31 operating non-primary qnames nulled during review

## Row schema (both files)

```json
{
  "ticker": "LSTR",
  "qname": "us-gaap:Revenues",
  "source_form_types": ["10-K", "10-Q"],
  "last_validated_filing": "0001193125-26-064756",
  "last_validated_period": "2025-12-27",
  "works_for_segments": true,
  "works_for_geography": false,
  "works_for_product_service": false,
  "validation_period_types": ["annual", "quarterly"],
  "basis_type": "memberless_total",
  "notes": ["exact business-segment view"]
}
```

Null rows carry `"qname": null` with `"notes": ["no exact … disclosed"]` or coordinator-review rationale.

## Regeneration

To rebuild from chunk outputs:

```bash
cat .claude/plans/xbrl_subagent_chunks/revenue_map_chunk_*.jsonl  > revenue_map_783.jsonl
cat .claude/plans/xbrl_subagent_chunks/operating_map_chunk_*.jsonl > operating_map_783.jsonl
```

Then apply the coordinator null-patches (list of 13 + 31 tickers embedded in the Wave 2 autonomous run logs).

## Usage

Read-only map files consumed by `scripts/earnings/xbrl_exact_splits.py` (D1 sidecar extractor).

Do not modify by hand — modifications should regenerate via a new Wave N run with updated precision rules.
