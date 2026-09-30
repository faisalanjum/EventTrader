# XBRL definitions — handoff (2026-09-30)

## Purpose and result

Build a source-checked dictionary for each report: concepts, dimensions, members and company-created terms, using that report’s actual taxonomy. Numeric facts are checked only for identity.

**981/981 reports passed; failed or withheld: 0 (0%).** Covers all 795 companies with linked reports in the audit snapshot, 11 sectors and 78 version/form/size/dimension groups: 611 10-Q, 287 10-K and 83 amendments. Includes 618 previously untested reports, all 570 previously untested companies, and 301 reports from 300 separate companies reserved until the code was frozen.

Of **670,751 report-metadata entries**, 574,074 have published documentation; **96,677 (14.4%) have none in the checked XBRL sources**. Absence is not an extraction failure. Company documentation sometimes merely repeats its label.

**33 tests passed**, including 26 deliberate field corruptions. Controlled download failure withheld metadata, continued and recovered on retry. Restart skipped all 981 unchanged reports. Five-file copy and real append/revision/retry checks passed. Repeated benchmarks used **31.4% less time**, with matching data; web checks fell 58.3% and output size 19.4%. No database writes.

## Reuse

[Code and commands](../../../../scripts/xbrl_metadata_pilot/README.md). Copy only `batch.py`, `metadata_audit.py`, `verify.py`, `source_notices.json`, `requirements.txt`; three Python files, 762 lines including comments/blanks. Python 3.11, pinned dependencies, Neo4j credentials through environment or repository `.env`.

```bash
venv/bin/python scripts/xbrl_metadata_pilot/batch.py --reports INPUT.json --out OUTPUT_DIRECTORY
```

Input: JSON list of `accession`, `ticker`, `cik`, `instance_url`, selected from this graph. **Use `batch.py` as the acceptance boundary**; `run_report()` alone returns an unchecked candidate. Consume only `acceptance_status: accepted` with `verification.source_status: passed`. Failed checks withhold metadata text and return reasons.

[Results and limits](../../../../scripts/xbrl_metadata_pilot/evidence/optimized_20260930/RESULTS.md), [failure percentages](../../../../scripts/xbrl_metadata_pilot/evidence/optimized_20260930/failure_rates.json). Same folder: canonical `final_results.json`, `selected_reports.json`, `final_code/`, `final_development_0…3`, `holdout_0…3`, tests, review inventory, artifact checksums and 5,847 source files archived by hash. Earlier runs are historical evidence.

## Rules to preserve

- Identity is namespace + local name. Retain report accession and source URL/hash; never substitute today’s taxonomy for a historical report.
- Preserve documentation, other labels, annotations, references, language/role, typed domains and report structure. References are pointers, not their underlying accounting text.
- Company text blocks remain separate `company_passages`, attached only to their explicitly tagged concept/report/context; they can contain HTML. No inferred explanations.
- Keep absent, unsupported and retrieval failure distinct. Preserve supplemental discovery and capture filing relationships before adding publisher documentation.
- `verification.graph_status` is separate: 42 reports have existing graph warnings. Source acceptance does not certify database ingestion or numeric values.

## Ongoing ingestion and limits

[Integration contract](../../../../scripts/xbrl_metadata_pilot/INGESTION.md): append new reports; change a stable input `ingestion_revision` after re-ingestion to refresh that report. Unchanged inputs resume as snapshots; use a new folder for a fresh audit. One writer per output folder. The caller must supply a reliable completed-run signal/revision; no watcher is installed.

Finite tests do not guarantee every future filing. Other formats/taxonomy families, orphan nodes and full independent XBRL relationship/type semantics remain outside proven coverage. Unsupported or failed sources must abstain. No AI layer, company-specific rules or production pipeline was added. Neo4j writes require explicit approval.
