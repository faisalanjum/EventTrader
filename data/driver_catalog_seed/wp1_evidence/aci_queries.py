#!/usr/bin/env python3
"""EXECUTABLE ACI reconciliation evidence (rounds 22-25; committed per reviewer directive —
scratchpad-only evidence is not evidence). Scope: Neo4j bolt per repo .env; ALL ACI
Report->FinancialStatementContent blobs; run 2026-07-19.
THE_PAIR = (us-gaap:StatementBusinessSegmentsAxis, aci:ReportableSegmentMember).

  A1 per-filing conflicts   : cells keyed (accession, concept, period) having BOTH a
                              THE_PAIR-only fact and a bare fact; conflict = value sets differ.
  A2 cross-filing conflicts : same, keyed (concept, period) across all filings.
  B  pair-only missing      : THE_PAIR-only cells with NO bare counterpart (per-filing).
  C  REVIEWER SPEC (round 25, CONFIRMED 43): every fact CONTAINING THE_PAIR (co-members
     included), strip THE_PAIR, seek an exact counterpart (same concept, value, period,
     remaining pairs) anywhere in the pool -> 126 targets, 83 counterparts, 43 missing
     (15 pair-only + 28 co-member).

    venv/bin/python data/driver_catalog_seed/wp1_evidence/aci_queries.py
"""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'scripts', 'driver_seed'))
import run_code_tier as RC, link_lib as L

THE_PAIR = ('us-gaap:StatementBusinessSegmentsAxis', 'aci:ReportableSegmentMember')


def main():
    RC.load_env_neo4j()
    from neo4j import GraphDatabase
    drv = GraphDatabase.driver(os.environ['NEO4J_URI'],
                               auth=(os.environ.get('NEO4J_USERNAME', 'neo4j'),
                                     os.environ['NEO4J_PASSWORD']))
    bad_blobs = []
    bad_facts = incomplete_segments = 0
    per_filing = collections.defaultdict(lambda: {'with': set(), 'without': set()})
    cross = collections.defaultdict(lambda: {'with': set(), 'without': set()})
    targets, pool = [], set()
    with drv.session() as s:
        for row in s.run("MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker:'ACI'}) "
                         "MATCH (r)-[:HAS_FINANCIAL_STATEMENT]->(f:FinancialStatementContent) "
                         "RETURN r.accessionNo AS acc, f.value AS xb"):
            try:
                data = json.loads(row['xb'])
            except Exception:
                bad_blobs.append(row['acc'])   # round-26: REPORTED, never silently skipped
                continue
            if not isinstance(data, dict):
                bad_blobs.append(row['acc'])
                continue
            for con, facts in data.items():
                for fc in (facts if isinstance(facts, list) else [facts]):
                    if not isinstance(fc, dict):
                        bad_facts += 1     # round-27: counted + asserted, never silent
                        continue
                    per = json.dumps(fc.get('period') or {}, sort_keys=True)
                    _prs, _ok = L.seg_parse(fc)
                    if not _ok:
                        incomplete_segments += 1   # round-27: counted + asserted, never silent
                        continue
                    pairs = tuple(sorted(tuple(p) for p in _prs))
                    v = str(fc.get('value'))
                    pool.add((con, v, per, pairs))
                    if pairs == (THE_PAIR,):
                        per_filing[(row['acc'], con, per)]['with'].add(v)
                        cross[(con, per)]['with'].add(v)
                    elif not pairs:
                        per_filing[(row['acc'], con, per)]['without'].add(v)
                        cross[(con, per)]['without'].add(v)
                    if THE_PAIR in pairs:
                        rest = tuple(p for p in pairs if p != THE_PAIR)
                        targets.append((con, v, per, rest))
    drv.close()
    assert pool, "EMPTY database result — the scan proves nothing"   # round-29
    for name, d in (('A1 PER-FILING', per_filing), ('A2 CROSS-FILING', cross)):
        both = {k: x for k, x in d.items() if x['with'] and x['without']}
        print(f"{name}: both-form cells={len(both)}  "
              f"conflicts={sum(1 for x in both.values() if x['with'] != x['without'])}  "
              f"identical={sum(1 for x in both.values() if x['with'] == x['without'])}")
    print(f"B  pair-only missing (per-filing): "
          f"{sum(1 for x in per_filing.values() if x['with'] and not x['without'])}")
    uniq = set(targets)
    have = {t for t in uniq if t in pool}
    missing = uniq - have
    po = sum(1 for t in missing if t[3] == ())
    print(f"C  REVIEWER SPEC: targets={len(uniq)}  counterparts={len(have)}  "
          f"MISSING={len(missing)} = pair-only {po} + co-member {len(missing) - po}")
    print(f"unreadable/non-dict blobs: {len(bad_blobs)}  non-dict facts: {bad_facts}  "
          f"incomplete-segment facts: {incomplete_segments}")
    assert not bad_blobs and bad_facts == 0 and incomplete_segments == 0, \
        "malformed data must be investigated, never silently skipped"


if __name__ == '__main__':
    main()
