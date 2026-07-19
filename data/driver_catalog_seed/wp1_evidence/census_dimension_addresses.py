#!/usr/bin/env python3
"""EXECUTABLE census evidence (rounds 24/26, committed): invalid-address classes across 11
tickers (the wp1 cohort + CAG), every 10-K/10-Q FinancialStatementContent blob.
ROUND-26 CORRECTION (reviewer): the first version measured PARSED pairs — but seg_parse REJECTS
padded names, so the padded counter was structurally blind. This version inspects the FOUR RAW
storage shapes directly, independently of seg_parse, and REPORTS unreadable/non-dict data
instead of silently skipping. Re-run 2026-07-19: dimensioned facts=47,152; repeated-axis=0;
padded-names=0; mixed-format-entries=0; unreadable=0 — the zero claims now carry a proof that
can actually see the violations.

    venv/bin/python data/driver_catalog_seed/wp1_evidence/census_dimension_addresses.py
"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'scripts', 'driver_seed'))
import run_code_tier as RC, link_lib as L

TICKERS = ['A', 'AA', 'AAL', 'AAPL', 'ABT', 'ACI', 'ACN', 'ADM', 'AEE', 'AFL', 'CAG']


def main():
    RC.load_env_neo4j()
    from neo4j import GraphDatabase
    drv = GraphDatabase.driver(os.environ['NEO4J_URI'],
                               auth=(os.environ.get('NEO4J_USERNAME', 'neo4j'),
                                     os.environ['NEO4J_PASSWORD']))
    rep_ax = padded = mixed = total = 0
    unreadable_blobs = nondict_blobs = nonfact_entries = 0

    def raw_names(seg):
        """(axis, member) RAW strings from the four storage shapes — NO parser, NO stripping."""
        out = []
        for it in (seg if isinstance(seg, list) else [seg]):
            if not isinstance(it, dict):
                out.append(None)               # unreadable entry — reported, never skipped
                continue
            if 'value' in it:
                out.append((it.get('dimension'), it.get('value')))
            em = it.get('explicitMember')
            if isinstance(em, list):
                out += [(m.get('dimension'), m.get('$t')) if isinstance(m, dict) else None
                        for m in em]
            elif isinstance(em, dict):
                out.append((em.get('dimension'), em.get('$t')))
            elif isinstance(em, str):
                out.append((it.get('dimension'), em))
        return out

    with drv.session() as s:
        for tk in TICKERS:
            for row in s.run("MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker:$tk}) "
                             "WHERE r.formType IN ['10-K','10-Q'] "
                             "MATCH (r)-[:HAS_FINANCIAL_STATEMENT]->(f:FinancialStatementContent) "
                             "RETURN f.value AS xb", tk=tk):
                try:
                    data = json.loads(row['xb'])
                except Exception:
                    unreadable_blobs += 1      # round-26: REPORTED, never silently skipped
                    continue
                if not isinstance(data, dict):
                    nondict_blobs += 1
                    continue
                for con, facts in data.items():
                    for fc in (facts if isinstance(facts, list) else [facts]):
                        if not isinstance(fc, dict):
                            nonfact_entries += 1
                            continue
                        if not fc.get('segment'):
                            continue
                        total += 1
                        names = raw_names(fc['segment'])
                        if any(n is None for n in names):
                            nonfact_entries += 1
                        axes = [a for n in names if n for a in [n[0]] if isinstance(a, str)]
                        if len(axes) != len(set(axes)):
                            rep_ax += 1
                        if any(isinstance(x, str) and x != x.strip()
                               for n in names if n for x in n):
                            padded += 1
                        items = fc['segment'] if isinstance(fc['segment'], list) else [fc['segment']]
                        if any(isinstance(it, dict) and 'value' in it and 'explicitMember' in it
                               for it in items):
                            mixed += 1
    drv.close()
    print(f"tickers={len(TICKERS)}  dimensioned facts={total}  repeated-axis={rep_ax}  "
          f"padded-names={padded}  mixed-format-entries={mixed}  "
          f"unreadable-blobs={unreadable_blobs}  nondict-blobs={nondict_blobs}  "
          f"nonfact-entries={nonfact_entries}")
    assert unreadable_blobs == 0 and nondict_blobs == 0, "unreadable data must be investigated"


if __name__ == '__main__':
    main()
