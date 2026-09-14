#!/usr/bin/env python3
"""EXP-1 census (code-only, READ-ONLY Neo4j). Throwaway harness.
Env-first creds only (NEO4J_URI/NEO4J_USERNAME/NEO4J_PASSWORD). No writes, no LLM."""
import os, json
from neo4j import GraphDatabase

FORMS = ['10-K', '10-Q', '10-K/A', '10-Q/A']
WRITE_TOKENS = (' CREATE ', ' MERGE ', ' DELETE ', ' REMOVE ', ' DROP ', ' SET ')

def read_only(q):
    up = ' ' + ' '.join(q.upper().split()) + ' '
    for t in WRITE_TOKENS:
        if t in up:
            raise SystemExit('ABORT read-only guard: %s' % t.strip())
    return q

def main():
    uri = os.environ.get('NEO4J_URI'); user = os.environ.get('NEO4J_USERNAME'); pw = os.environ.get('NEO4J_PASSWORD')
    if not (uri and pw):
        raise SystemExit('ABORT: NEO4J creds not in env (env-first required)')
    sample_n = 1000000
    years = list(range(2018, 2027))
    out = {'exp_id': 'EXP-1', 'probe': 'census', 'run_utc': os.environ.get('CENSUS_TS', ''),
           'db': {}, 'census': {}, 'schema_bindings': None, 'notes': []}
    drv = GraphDatabase.driver(uri, auth=(user or 'neo4j', pw))
    with drv.session() as s:
        def run(q, **p):
            return list(s.run(read_only(q), **p))
        out['db']['fact_count'] = run('MATCH (f:Fact) RETURN count(f) AS n')[0]['n']
        out['db']['report_count'] = run('MATCH (r:Report) RETURN count(r) AS n')[0]['n']
        print('db_counts done', flush=True)
        rows = run('MATCH (f:Fact)-[:HAS_UNIT]->(u:Unit) RETURN u.name AS unit, u.is_divide AS is_divide, count(f) AS n ORDER BY n DESC LIMIT 100')
        out['census']['unit_inventory'] = [{'unit': r['unit'], 'is_divide': r['is_divide'], 'n': r['n']} for r in rows]
        print('unit_inventory done: %d units' % len(rows), flush=True)
        out['census']['no_context_facts'] = run('MATCH (f:Fact) WHERE NOT EXISTS { (f)-[:IN_CONTEXT]->() } RETURN count(f) AS n')[0]['n']
        print('no_context done: %d' % out['census']['no_context_facts'], flush=True)
        r = run("MATCH (r:Report)-[:HAS_XBRL]->(:XBRLNode) WHERE r.formType IN $forms AND (r.periodOfReport IS NULL OR r.periodOfReport = '' OR r.periodOfReport = 'null') RETURN count(DISTINCT r) AS n, collect(DISTINCT r.id)[0..10] AS sample", forms=FORMS)[0]
        out['census']['null_period_of_report'] = {'n': r['n'], 'sample': r['sample']}
        print('null_pOR done: %d' % r['n'], flush=True)
        rows = run('MATCH (r:Report) WHERE r.formType IN $forms RETURN coalesce(r.xbrl_status, "<null>") AS status, count(*) AS n ORDER BY n DESC', forms=FORMS)
        out['census']['xbrl_status_distribution'] = [{'status': r['status'], 'n': r['n']} for r in rows]
        print('xbrl_status done', flush=True)
        rows = run("MATCH (f:Fact) WHERE f.is_numeric = '1' WITH f LIMIT $n RETURN coalesce(f.decimals, '<null>') AS decimals, count(*) AS c ORDER BY c DESC LIMIT 40", n=sample_n)
        out['census']['decimals_distribution'] = {'sample_size': sample_n, 'sample_method': 'first N numeric facts by scan order', 'dist': [{'decimals': r['decimals'], 'n': r['c']} for r in rows]}
        print('decimals done', flush=True)
        r = run("MATCH (f:Fact) WHERE f.is_numeric = '1' WITH f LIMIT $n RETURN sum(CASE WHEN f.value CONTAINS ',' THEN 1 ELSE 0 END) AS commas, count(f) AS total", n=sample_n)[0]
        out['census']['comma_values'] = {'sample_size': r['total'], 'with_comma': r['commas'], 'sample_method': 'first N numeric facts by scan order'}
        print('comma_values done: %s/%s' % (r['commas'], r['total']), flush=True)
        mr = {'by_year': [], 'total_multireg_reports': 0, 'samples': []}
        for y in years:
            rr = run("MATCH (r:Report)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(:Fact)-[:IN_CONTEXT]->(:Context)-[:FOR_COMPANY]->(c:Company) WHERE r.formType IN $forms AND r.created >= $lo AND r.created < $hi WITH r, count(DISTINCT c) AS ncomp WHERE ncomp > 1 RETURN count(r) AS nrep, collect({id: r.id, ft: r.formType, ncomp: ncomp})[0..5] AS sample",
                     forms=FORMS, lo='%d-01-01' % y, hi='%d-01-01' % (y + 1))[0]
            mr['by_year'].append({'year': y, 'multireg_reports': rr['nrep']})
            mr['total_multireg_reports'] += rr['nrep']
            if rr['sample']:
                mr['samples'].extend(rr['sample'])
            print('multireg %d done: %d' % (y, rr['nrep']), flush=True)
        out['census']['multi_registrant'] = mr
    drv.close()
    try:
        with open('exp1_xbrl/schema_bindings_probe.json') as fh:
            out['schema_bindings'] = json.load(fh)
    except Exception as e:
        out['notes'].append('schema_bindings load failed: %s' % e)
    path = 'exp1_xbrl/census.json'; tmp = path + '.tmp'
    with open(tmp, 'w') as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
    os.replace(tmp, path)
    print('WROTE ' + path, flush=True)
    summary = {'db': out['db'], 'no_context_facts': out['census']['no_context_facts'],
               'null_pOR': out['census']['null_period_of_report']['n'],
               'xbrl_status': out['census']['xbrl_status_distribution'],
               'decimals_top8': out['census']['decimals_distribution']['dist'][:8],
               'comma_values': out['census']['comma_values'],
               'multireg_total': out['census']['multi_registrant']['total_multireg_reports'],
               'multireg_by_year': out['census']['multi_registrant']['by_year'],
               'unit_inventory_top12': out['census']['unit_inventory'][:12]}
    print('=== CENSUS SUMMARY ===', flush=True)
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
    print('CENSUS_DONE', flush=True)

if __name__ == '__main__':
    main()
