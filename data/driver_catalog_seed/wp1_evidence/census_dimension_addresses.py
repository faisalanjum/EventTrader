#!/usr/bin/env python3
"""EXECUTABLE census evidence (round 24, committed per reviewer directive): invalid-address
classes across 11 tickers (the wp1 cohort + CAG), every 10-K/10-Q FinancialStatementContent
blob. Result at run 2026-07-19: dimensioned facts=47,152; repeated-axis=0; padded-names=0;
mixed-format-entries=0 — enforcement of the round-24 address law costs zero real facts.

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
    with drv.session() as s:
        for tk in TICKERS:
            for row in s.run("MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker:$tk}) "
                             "WHERE r.formType IN ['10-K','10-Q'] "
                             "MATCH (r)-[:HAS_FINANCIAL_STATEMENT]->(f:FinancialStatementContent) "
                             "RETURN f.value AS xb", tk=tk):
                try:
                    data = json.loads(row['xb'])
                except Exception:
                    continue
                if not isinstance(data, dict):
                    continue
                for con, facts in data.items():
                    for fc in (facts if isinstance(facts, list) else [facts]):
                        if not isinstance(fc, dict) or not fc.get('segment'):
                            continue
                        total += 1
                        pairs = L.seg_axis_members(fc)
                        axes = [a for a, _ in pairs]
                        if len(axes) != len(set(axes)):
                            rep_ax += 1
                        if any(a != a.strip() or m != m.strip() for a, m in pairs):
                            padded += 1
                        items = fc['segment'] if isinstance(fc['segment'], list) else [fc['segment']]
                        if any(isinstance(it, dict) and 'value' in it and 'explicitMember' in it
                               for it in items):
                            mixed += 1
    drv.close()
    print(f"tickers={len(TICKERS)}  dimensioned facts={total}  repeated-axis={rep_ax}  "
          f"padded-names={padded}  mixed-format-entries={mixed}")


if __name__ == '__main__':
    main()
