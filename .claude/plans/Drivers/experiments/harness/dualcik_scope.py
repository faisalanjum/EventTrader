#!/usr/bin/env python3
"""EXP-1 PART-2 dual-CIK slice-pairing scope pass (READ-ONLY, 0 LLM). Over ALL 60 FA filings.
Question: does the dual-CIK u_id mismatch touch REAL slice axes / would-materialize facts, or only
non-slice facts that are skipped anyway? Records to run dir. Does NOT change O13/P4f.
Imports the materializer's frozen tables/helpers (this is a probe, NOT the X-XL0 verifier)."""
import os, json, argparse, sys
sys.path.insert(0, '/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments/harness')
import xbrl_dryrun_materializer as MAT
from neo4j import GraphDatabase

CONFIRMED_AXES = MAT.CONFIRMED_AXES; STD_NS = MAT.STD_NS
norm_uid = MAT.norm_uid; truthy = MAT.truthy; convert_value = MAT.convert_value


def qn_of_uid(u):
    p = (u or '').split(':'); return ':'.join(p[-2:]) if len(p) >= 2 else (u or '')


def axis_kind(qn):
    if qn in CONFIRMED_AXES: return 'slice_' + CONFIRMED_AXES[qn]
    if (qn.split(':')[0] if qn else '') in STD_NS: return 'nonslice_std'
    return 'unknown_coined'


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--rundir', required=True); a = ap.parse_args()
    uri = os.environ['NEO4J_URI']; user = os.environ.get('NEO4J_USERNAME'); pw = os.environ['NEO4J_PASSWORD']
    fa = json.load(open('fixtures/FA_selection.json')); fr = json.load(open('fixtures/fixture_resolutions.json'))['by_company']
    filings = []
    for tk, lst in sorted(fa['filings'].items()):
        for f in lst: filings.append((tk, f['report_id']))
    filings.sort(key=lambda x: (x[0], x[1]))
    drv = GraphDatabase.driver(uri, auth=(user or 'neo4j', pw))
    by_ticker = {}; fail_axis_kind = {}; real_examples = []
    entity_cik = {}; noncik = {'unique': 0, 'ambiguous': 0, 'samples': []}
    safety_left = 12
    with drv.session() as s:
        for tk, rid in filings:
            fixq = set(r['qname'] for r in fr.get(tk, []))
            rows = list(s.run("MATCH (r:Report {id:$rid})-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(con:Concept) "
                              "WHERE f.is_numeric='1' AND f.is_nil='0' OPTIONAL MATCH (f)-[:IN_CONTEXT]->(ctx:Context) OPTIONAL MATCH (f)-[:HAS_UNIT]->(u:Unit) "
                              "RETURN con.qname AS qn, ctx.dimension_u_ids AS dims, ctx.member_u_ids AS mems, u.name AS un, u.is_divide AS idv", rid=rid))
            du = set(); mu = set()
            for x in rows:
                if x['dims']: du |= set(norm_uid(d) for d in x['dims'])
                if x['mems']: mu |= set(norm_uid(m) for m in x['mems'])
            dmap = {y['u']: (y['qn'], y['exp']) for y in s.run("MATCH (d:Dimension) WHERE d.u_id IN $u RETURN d.u_id AS u, d.qname AS qn, d.is_explicit AS exp", u=list(du))} if du else {}
            mmap = {y['u']: y['qn'] for y in s.run("MATCH (m:Member) WHERE m.u_id IN $u RETURN m.u_id AS u, m.qname AS qn", u=list(mu))} if mu else {}
            bt = by_ticker.setdefault(tk, {'dim_facts': 0, 'pass': 0, 'fail': 0, 'fail_real_would_materialize': 0, 'fail_skipped_anyway': 0})
            company_sampled = False
            for x in rows:
                if x['qn'] not in fixq: continue
                dims = [norm_uid(d) for d in (x['dims'] or [])]; mems = [norm_uid(m) for m in (x['mems'] or [])]
                if not dims and not mems: continue
                bt['dim_facts'] += 1
                axis_qns = [(dmap.get(d, (None, None))[0] or qn_of_uid(d)) for d in dims]
                kinds = [axis_kind(q) for q in axis_qns]
                n_exp = sum(1 for d in dims if truthy(dmap.get(d, ('', '0'))[1]))
                if n_exp == len(mems):
                    bt['pass'] += 1; continue
                bt['fail'] += 1
                has_nonslice = any(k == 'nonslice_std' for k in kinds)
                unit_ok = convert_value(x['un'], x['idv'], '0') is not None
                would_materialize = unit_ok and not has_nonslice
                for d, k in zip(dims, kinds):
                    if d not in dmap: fail_axis_kind[k] = fail_axis_kind.get(k, 0) + 1
                if would_materialize:
                    bt['fail_real_would_materialize'] += 1
                    if len(real_examples) < 12:
                        real_examples.append({'ticker': tk, 'report_id': rid, 'qname': x['qn'], 'unit': x['un'],
                                              'axes': [[q, k] for q, k in zip(axis_qns, kinds)]})
                else:
                    bt['fail_skipped_anyway'] += 1
                if not company_sampled and safety_left > 0:
                    for m in mems:
                        if m not in mmap:
                            qn = qn_of_uid(m)
                            h = s.run("MATCH (mm:Member {qname:$qn}) RETURN collect(DISTINCT split(mm.u_id,':')[0])[0..8] AS ciks, count(DISTINCT mm.u_id) AS n_uids", qn=qn).single()
                            if h:
                                for c in (h['ciks'] or []): entity_cik.setdefault(tk, set()).add(c)
                                (noncik.__setitem__('unique', noncik['unique'] + 1) if len(h['ciks'] or []) <= 1 else noncik.__setitem__('ambiguous', noncik['ambiguous'] + 1))
                                if len(noncik['samples']) < 10:
                                    noncik['samples'].append({'ticker': tk, 'member_qname': qn, 'node_ciks': h['ciks'], 'n_uids': h['n_uids'], 'context_filer_cik': str(int(rid.split('-')[0]))})
                            company_sampled = True; safety_left -= 1
                            break
    drv.close()
    tickers_fail = sorted([tk for tk, bt in by_ticker.items() if bt['fail'] > 0])
    total_real = sum(bt['fail_real_would_materialize'] for bt in by_ticker.values())
    total_fail = sum(bt['fail'] for bt in by_ticker.values())
    slice_axis_in_fail = {k: v for k, v in fail_axis_kind.items() if k.startswith('slice_')}
    out = {'probe': 'PART-2 dual-CIK slice-pairing scope (read-only, all 60 FA filings)',
           'by_ticker': by_ticker, 'tickers_with_failures': tickers_fail, 'aal_only': set(tickers_fail) <= {'AAL'},
           'total_fail': total_fail, 'total_fail_real_would_materialize': total_real,
           'fail_unresolved_axis_kinds': fail_axis_kind, 'unresolved_SLICE_axes_in_failures': slice_axis_in_fail,
           'real_would_materialize_examples': real_examples,
           'filer_entity_cik_map_evidence': {tk: sorted(v) for tk, v in entity_cik.items()},
           'namespace_qname_uniqueness_sample': noncik,
           'touches_real_slice_axes_or_materialized_facts': (total_real > 0 or bool(slice_axis_in_fail)),
           'verdict': ('STOP_FOR_FABLE_touches_real_slices_or_materialized' if (total_real > 0 or bool(slice_axis_in_fail)) else 'COVERAGE_RISK_ONLY_no_real_slices_no_materialized_affected')}
    json.dump(out, open(a.rundir + '/dualcik_scope_proof.json', 'w'), indent=2, sort_keys=True)
    print('VERDICT', out['verdict'])
    print('AAL_ONLY', out['aal_only'], '| tickers_with_failures', tickers_fail)
    print('TOTAL_FAIL', total_fail, '| would_materialize(REAL)', total_real, '| unresolved_SLICE_axes', json.dumps(slice_axis_in_fail, sort_keys=True))
    print('FAIL_UNRESOLVED_AXIS_KINDS', json.dumps(fail_axis_kind, sort_keys=True))
    for tk in sorted(by_ticker): print('%-5s' % tk, json.dumps(by_ticker[tk], sort_keys=True))
    print('FILER_ENTITY_CIK', json.dumps({tk: sorted(v) for tk, v in entity_cik.items()}, sort_keys=True))
    print('NONCIK_UNIQUENESS', json.dumps(noncik, sort_keys=True))
    if real_examples: print('REAL_EXAMPLES', json.dumps(real_examples[:4], sort_keys=True))
    print('WROTE', a.rundir + '/dualcik_scope_proof.json')


if __name__ == '__main__':
    main()
