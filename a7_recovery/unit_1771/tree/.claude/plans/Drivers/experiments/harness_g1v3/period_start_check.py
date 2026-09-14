#!/usr/bin/env python3
"""EXP-1 PART-1 start-date check (READ-ONLY, 0 LLM). Fable-required BEFORE applying the exclusive-end decode.
Confirms start_date is UNSHIFTED (inclusive first day) over the 60 FA filings.
Model under test: [start_incl, end_excl) -> effective_end = end_date-1 == periodOfReport; start_date == a prior
period's exclusive end_date (boundary chaining). A start-shift breaks chaining. If suspect -> STOP."""
import os, json, argparse
from datetime import date, timedelta
from neo4j import GraphDatabase


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--rundir', required=True); a = ap.parse_args()
    uri = os.environ['NEO4J_URI']; user = os.environ.get('NEO4J_USERNAME'); pw = os.environ['NEO4J_PASSWORD']
    fa = json.load(open('fixtures/FA_selection.json'))
    tickers = sorted(fa['filings'].keys())
    fil = {tk: [(f['report_id'], f['form'], f['periodOfReport']) for f in lst] for tk, lst in fa['filings'].items()}
    drv = GraphDatabase.driver(uri, auth=(user or 'neo4j', pw))
    per_company = {}
    with drv.session() as s:
        for tk in tickers:
            rows = list(s.run("MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker:$t}) WHERE r.formType IN ['10-K','10-Q','10-K/A','10-Q/A'] AND r.xbrl_status='COMPLETED' "
                              "MATCH (r)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(:Fact)-[:HAS_PERIOD]->(p:Period) WHERE p.period_type='duration' "
                              "RETURN DISTINCT p.start_date AS s, p.end_date AS e", t=tk))
            starts = set(); ends = set(); windows = set()
            for x in rows:
                if x['s'] and x['e'] and x['s'] != 'null' and x['e'] != 'null':
                    starts.add(x['s']); ends.add(x['e']); windows.add((x['s'], x['e']))
            n_invalid = sum(1 for (s0, e0) in windows if s0 >= e0)
            starts_in_ends = sum(1 for s0 in starts if s0 in ends)
            prim_total = 0; prim_end_ok = 0; prim_start_chains = 0
            for rid, form, por in fil.get(tk, []):
                if not por:
                    continue
                por1 = (date.fromisoformat(por[:10]) + timedelta(days=1)).isoformat()
                pr = list(s.run("MATCH (r:Report {id:$rid})-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(:Fact)-[:HAS_PERIOD]->(p:Period) "
                                "WHERE p.period_type='duration' AND p.end_date=$por1 RETURN DISTINCT p.start_date AS s, p.end_date AS e", rid=rid, por1=por1))
                for x in pr:
                    prim_total += 1
                    eff_end = (date.fromisoformat(x['e'][:10]) - timedelta(days=1)).isoformat()
                    if eff_end == por: prim_end_ok += 1
                    if x['s'] in ends: prim_start_chains += 1
            per_company[tk] = {'n_windows': len(windows), 'n_starts': len(starts),
                               'starts_that_are_also_ends': starts_in_ends,
                               'boundary_chain_pct': round(100.0 * starts_in_ends / len(starts), 1) if starts else 0,
                               'invalid_start_ge_end': n_invalid,
                               'primary_windows': prim_total, 'primary_end_decodes_to_por': prim_end_ok,
                               'primary_start_chains_to_prior_end': prim_start_chains}
    drv.close()
    tp = sum(c['primary_windows'] for c in per_company.values())
    tpe = sum(c['primary_end_decodes_to_por'] for c in per_company.values())
    tpc = sum(c['primary_start_chains_to_prior_end'] for c in per_company.values())
    tinv = sum(c['invalid_start_ge_end'] for c in per_company.values())
    ok = (tp > 0 and tpe == tp and tinv == 0 and tpc >= 0.85 * tp)
    out = {'probe': 'PART-1 start-date check (read-only): are starts unshifted (inclusive) under exclusive-end?',
           'per_company': per_company,
           'totals': {'primary_windows': tp, 'primary_end_decodes_to_por': tpe, 'primary_start_chains_to_prior_end': tpc, 'invalid_start_ge_end': tinv},
           'verdict': 'STARTS_UNSHIFTED_OK_TO_APPLY' if ok else 'STARTS_SUSPECT_STOP',
           'interpretation': 'primary_end_decodes_to_por==primary_windows => end_date-1==periodOfReport (exclusive end confirmed). primary_start_chains high => start_date is a prior period exclusive end (UNSHIFTED). invalid_start_ge_end must be 0.'}
    json.dump(out, open(a.rundir + '/period_start_check.json', 'w'), indent=2, sort_keys=True)
    print('VERDICT', out['verdict'])
    print('TOTALS', json.dumps(out['totals'], sort_keys=True))
    for tk in tickers:
        print('%-5s' % tk, json.dumps(per_company[tk], sort_keys=True))
    print('WROTE', a.rundir + '/period_start_check.json')


if __name__ == '__main__':
    main()
