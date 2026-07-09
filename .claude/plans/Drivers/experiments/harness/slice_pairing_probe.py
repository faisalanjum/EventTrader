#!/usr/bin/env python3
"""EXP-1 slice-pairing residual verification (READ-ONLY, 0 LLM). Verifies WHY facts fail-closed.
Hypothesis: aligned contexts contain a TYPED dim (is_explicit='0') that carries a member entry, so the
current explicit-filter drops the dim but NOT its member -> len(explicit) != len(mems) -> fail-closed.
Does NOT modify O13 / resolve_slices."""
import os, json, argparse
from neo4j import GraphDatabase


def norm_uid(u):
    if not u: return u
    i = u.find(':')
    if i > 0 and u[:i].isdigit(): return str(int(u[:i])) + u[i:]
    return u


def truthy(v): return str(v).strip().lower() in ('true', '1', 't', 'yes')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--rundir', required=True); a = ap.parse_args()
    uri = os.environ['NEO4J_URI']; user = os.environ.get('NEO4J_USERNAME'); pw = os.environ['NEO4J_PASSWORD']
    fa = json.load(open('fixtures/FA_selection.json')); fr = json.load(open('fixtures/fixture_resolutions.json'))['by_company']
    filings = []
    for tk, lst in sorted(fa['filings'].items()):
        for f in lst: filings.append((tk, f['report_id']))
    filings.sort(key=lambda x: x[1]); filings = filings[:3]  # same dry3 slice
    drv = GraphDatabase.driver(uri, auth=(user or 'neo4j', pw))
    cats = {'nondimensional_pass': 0, 'clean_dim_pass': 0, 'FAIL_typed_with_member': 0,
            'FAIL_dims_gt_mems': 0, 'FAIL_mems_gt_dims': 0, 'FAIL_other': 0}
    examples = []
    with drv.session() as s:
        for tk, rid in filings:
            fixq = set(r['qname'] for r in fr.get(tk, []))
            rows = list(s.run("MATCH (r:Report {id:$rid})-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(con:Concept) "
                              "WHERE f.is_numeric='1' AND f.is_nil='0' OPTIONAL MATCH (f)-[:IN_CONTEXT]->(ctx:Context) "
                              "RETURN con.qname AS qn, ctx.dimension_u_ids AS dims, ctx.member_u_ids AS mems", rid=rid))
            du = set(); mu = set()
            for x in rows:
                if x['dims']: du |= set(norm_uid(d) for d in x['dims'])
                if x['mems']: mu |= set(norm_uid(m) for m in x['mems'])
            dmap = {y['u']: (y['qn'], y['exp']) for y in s.run("MATCH (d:Dimension) WHERE d.u_id IN $u RETURN d.u_id AS u, d.qname AS qn, d.is_explicit AS exp", u=list(du))} if du else {}
            mmap = {y['u']: y['qn'] for y in s.run("MATCH (m:Member) WHERE m.u_id IN $u RETURN m.u_id AS u, m.qname AS qn", u=list(mu))} if mu else {}
            for x in rows:
                if x['qn'] not in fixq: continue
                dims = [norm_uid(d) for d in (x['dims'] or [])]; mems = [norm_uid(m) for m in (x['mems'] or [])]
                if not dims and not mems:
                    cats['nondimensional_pass'] += 1; continue
                n_exp = sum(1 for d in dims if truthy(dmap.get(d, ('', '0'))[1]))
                n_typed = len(dims) - n_exp; nd = len(dims); nm = len(mems)
                if n_exp == nm:
                    cats['clean_dim_pass'] += 1
                elif nd == nm and n_typed > 0:
                    cats['FAIL_typed_with_member'] += 1
                    if len(examples) < 5:
                        examples.append({'qname': x['qn'], 'positional_pairs': [
                            {'dim': dmap.get(d, ('?', '?'))[0], 'is_explicit': dmap.get(d, ('', '?'))[1], 'member': mmap.get(m, '?')}
                            for d, m in zip(dims, mems)]})
                elif nd > nm:
                    cats['FAIL_dims_gt_mems'] += 1
                elif nm > nd:
                    cats['FAIL_mems_gt_dims'] += 1
                else:
                    cats['FAIL_other'] += 1
    drv.close()
    fails = cats['FAIL_typed_with_member'] + cats['FAIL_dims_gt_mems'] + cats['FAIL_mems_gt_dims'] + cats['FAIL_other']
    out = {'probe': 'slice_pairing residual verification (read-only, dry3 3 reports)', 'categories': cats, 'total_fail_closed': fails,
           'hypothesis': 'FAIL_typed_with_member = aligned length + a typed dim (is_explicit=0) carrying a member -> current code drops the dim not its member',
           'hypothesis_confirmed_pct_of_fails': round(100.0 * cats['FAIL_typed_with_member'] / fails, 1) if fails else 0,
           'mechanical_fix': 'positional pairing dimension_u_ids[i]<->member_u_ids[i]; skip (drop BOTH dim and member) when is_explicit=0; misaligned length -> fail-closed. == the ratified O13 rule as literally written.',
           'examples_typed_with_member': examples}
    json.dump(out, open(a.rundir + '/slice_pairing_probe.json', 'w'), indent=2, sort_keys=True)
    print('CATEGORIES', json.dumps(cats, sort_keys=True))
    print('TOTAL_FAIL_CLOSED', fails, '| typed_with_member % of fails', out['hypothesis_confirmed_pct_of_fails'])
    print('EXAMPLES', json.dumps(examples, sort_keys=True))
    print('WROTE', a.rundir + '/slice_pairing_probe.json')


if __name__ == '__main__':
    main()
