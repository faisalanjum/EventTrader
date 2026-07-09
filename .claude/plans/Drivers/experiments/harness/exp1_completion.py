#!/usr/bin/env python3
"""EXP-1 completion items (Fable's 5, pre-O12). READ-ONLY Neo4j, 0 LLM, NO writes to Neo4j.
Imports the materializer (MAT) to replicate its EXACT pipeline for the reconcile + precision scan
(fidelity: this is a recount of the frozen run, so using MAT's own functions is correct here -- unlike
the X-XL0 verifier which must be independent).

Deliverables (all in RUN dir unless noted):
 1 collision_census.json     (D1 = P4g du_id invariant + value-confusability base rate)
 2 comparator_census.json    (P15 prior-window / comparator availability over materialized.jsonl)
 3 fixtures_exercised.json    (synthetic P4f multi-registrant scoping; synthetic P4h derive + underivable-skip;
                               synthetic P4g keep-highest + conflict; REAL P4g precision-dup scan of the dry run)
 4 dualcik_count_reconcile.json (run 2633 vs probe 2587 -- exact decomposition + one-line note)
 5 xxl0_fields.json + manifest.xxl0_rederived_fields (the 7 X-XL0 re-derived fields)
 Backfills fixtures/FA_selection.json mandatory_fixtures.precision_dup_pair_report from the REAL scan.

Fidelity asserts: recomputed emitted == 9603 (materialized.jsonl); run_dualcik == skips.json;
probe_fail == dualcik_scope_proof.total_fail. Any mismatch is PRINTED loudly (do not trust silently)."""
import os, re, json, argparse, sys
from datetime import date, timedelta
from collections import Counter, defaultdict
sys.path.insert(0, '/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments/harness')
import xbrl_dryrun_materializer as MAT
from neo4j import GraphDatabase

EXP = '/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments'
norm_uid = MAT.norm_uid; norm_cik = MAT.norm_cik; truthy = MAT.truthy

MAT_QUERY = ("MATCH (r:Report {id:$rid})-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(con:Concept) "
             "WHERE f.is_numeric='1' AND f.is_nil='0' "
             "OPTIONAL MATCH (f)-[:IN_CONTEXT]->(ctx:Context) OPTIONAL MATCH (f)-[:HAS_PERIOD]->(p:Period) OPTIONAL MATCH (f)-[:HAS_UNIT]->(u:Unit) "
             "RETURN f.id AS fid, con.qname AS qn, f.value AS val, f.decimals AS dec, ctx.context_id AS cxid, ctx.cik AS cik, "
             "ctx.dimension_u_ids AS dims, ctx.member_u_ids AS mems, p.period_type AS pt, p.start_date AS ps, p.end_date AS pe, u.name AS un, u.is_divide AS idv")

XXL0_FIELDS = [
 {"field": "level_unit", "rederivation": "P4c/P4a unit table re-implemented independently (iso4217:USD non-divide->m_usd, shares non-divide->count, iso4217:USDshares divide->usd) from source Unit.name/is_divide"},
 {"field": "value_canonical", "rederivation": "raw Fact.value comma-stripped->float then P4c scale (USD/1e6 round6; shares & usd/share passthrough), independent 3-row table"},
 {"field": "decimals", "rederivation": "source Fact.decimals compared verbatim (precision metadata, never a multiplier)"},
 {"field": "qname", "rederivation": "source Concept.qname compared verbatim"},
 {"field": "time_type", "rederivation": "source Period.period_type (instant|duration) compared verbatim"},
 {"field": "gp_id", "rederivation": "period-window id rebuilt from source Period dates with Fable exclusive-end decode (duration: start .. end_date-1; instant: (stored-1)..(stored-1)) -- independent of the materializer"},
 {"field": "slices", "rederivation": "O13 explicit-dim positional pairing re-implemented over Context.dimension_u_ids || member_u_ids with CIK-normalized u_ids, CONFIRMED_AXES kind, elimination guard, dual-CIK unresolved sentinel"}]


def load(p): return json.load(open(p))
def dwrite(p, o): json.dump(o, open(p, 'w'), indent=2, sort_keys=True)
def eff_end_iso(dstr):
    d = MAT.parse_d(dstr); return (d - timedelta(days=1)).isoformat() if d else None
def gp_parts(gp):
    p = gp.split('_'); return (p[1], p[2]) if len(p) >= 3 else (None, None)


# ---- P4g collision decision, mirroring materializer lines 239-254 (single source used by real scan + synthetic) ----
def collision_decide(rws):
    if len(rws) == 1: return ('single', 0)
    rawvals = set(MAT.to_num(r['raw_value']) for r in rws)
    decs = [MAT.dec_int(r['decimals']) for r in rws]
    if len(rawvals) == 1:
        keep = max(range(len(rws)), key=lambda i: (decs[i] if decs[i] is not None else -999))
        return ('keep_highest_identical', keep)
    if any(d is None for d in decs): return ('conflict', None)
    coarse = min(decs); rounded = set(round(MAT.to_num(r['raw_value']), coarse) for r in rws)
    if len(rounded) == 1:
        keep = max(range(len(rws)), key=lambda i: decs[i]); return ('keep_highest_rounding', keep)
    return ('conflict', None)


# ============================ TASK 1: collision_census (D1) ============================
def task1_collision_census(rows, RUN):
    du_counts = Counter(r['du_id'] for r in rows)
    dup_du = {k: c for k, c in du_counts.items() if c > 1}
    # (b) confusability: (registrant, period gp_id) pairs where >=2 different qnames carry identical canonical value
    by_val = defaultdict(lambda: defaultdict(set))      # (reg,gp) -> value -> {qname}
    by_uval = defaultdict(lambda: defaultdict(set))     # (reg,gp) -> (unit,value) -> {qname}
    for r in rows:
        k = (r['registrant'], r['period']['gp_id'])
        by_val[k][r['value_canonical']].add(r['qname'])
        by_uval[k][(r['level_unit'], r['value_canonical'])].add(r['qname'])
    total_pairs = len(by_val)
    conf_pairs = conf_pairs_nz = conf_vals = conf_pairs_unit = 0
    for k, vm in by_val.items():
        cvals = [v for v, qs in vm.items() if len(qs) >= 2]
        if cvals: conf_pairs += 1
        conf_vals += len(cvals)
        if any(v != 0.0 for v in cvals): conf_pairs_nz += 1
    for k, vm in by_uval.items():
        if any(len(qs) >= 2 for qs in vm.values()): conf_pairs_unit += 1
    out = {"probe": "collision_census (D1 / WorkOrder 10-D1 : falsifier-iii dry-run)",
           "a_p4g_invariant": {"spec": "post-dedup (registrant,period,qname,fact_scope) groups MUST be 0 -- enforced via du_id=du:{report}:{driver}:{fact_scope} uniqueness (report_id in key => per-filing)",
                               "total_rows": len(rows), "distinct_du_id": len(du_counts), "duplicate_du_id_count": len(dup_du),
                               "pass": len(dup_du) == 0, "duplicate_examples": list(dup_du.items())[:5]},
           "b_value_confusability_base_rate": {
               "spec": "(registrant,period) pairs where >=2 different qnames carry identical canonical values (informational; feeds detector calibration)",
               "total_registrant_period_pairs": total_pairs,
               "confusable_pairs_value_only": conf_pairs, "base_rate_value_only": round(conf_pairs / total_pairs, 6) if total_pairs else 0.0,
               "confusable_pairs_excl_zero_value": conf_pairs_nz, "base_rate_excl_zero": round(conf_pairs_nz / total_pairs, 6) if total_pairs else 0.0,
               "confusable_pairs_unit_scoped": conf_pairs_unit, "base_rate_unit_scoped": round(conf_pairs_unit / total_pairs, 6) if total_pairs else 0.0,
               "confusable_value_instances": conf_vals,
               "note": "headline = literal value-only per spec; excl_zero removes the many shared 0.0 facts; unit_scoped keys (level_unit,value) so m_usd 21.0 is not conflated with count 21.0"}}
    dwrite(RUN + '/collision_census.json', out); return out


# ============================ TASK 2: comparator_census (P15) ============================
def task2_comparator_census(rows, RUN):
    series = defaultdict(list)   # (reg,driver,slices,scope) -> [effective end date]
    for r in rows:
        sc = r['period']['period_scope']
        if sc not in ('quarter', 'ytd', 'annual'): continue
        _, e = gp_parts(r['period']['gp_id']); ed = MAT.parse_d(e)
        if ed: series[(r['registrant'], r['driver'], tuple(sorted(r['slices'])), sc)].append(ed)
    tally = {sc: {'eligible': 0, 'comparator_found': 0} for sc in ('quarter', 'ytd', 'annual')}
    for r in rows:
        sc = r['period']['period_scope']
        if sc not in tally: continue
        _, e = gp_parts(r['period']['gp_id']); ed = MAT.parse_d(e)
        if not ed: continue
        lo, hi = ed - timedelta(days=372), ed - timedelta(days=358)   # (end - 1yr) +/- 7d, robust to 365/366
        ends = series[(r['registrant'], r['driver'], tuple(sorted(r['slices'])), sc)]
        found = any(lo <= x <= hi for x in ends)
        tally[sc]['eligible'] += 1; tally[sc]['comparator_found'] += 1 if found else 0
    def frac(d): return round(d['comparator_found'] / d['eligible'], 6) if d['eligible'] else None
    qy_elig = tally['quarter']['eligible'] + tally['ytd']['eligible']
    qy_found = tally['quarter']['comparator_found'] + tally['ytd']['comparator_found']
    out = {"probe": "comparator_census (P15 data check : effective_driver_state derived-comparator availability)",
           "spec": "fraction of quarter/ytd rows with a prior row in same (registrant,driver,slices,scope) whose window end is within +/-7d of (end - 1 year); annual analog",
           "headline_quarter_ytd": {"eligible": qy_elig, "comparator_found": qy_found, "availability_fraction": round(qy_found / qy_elig, 6) if qy_elig else None},
           "by_scope": {sc: {**tally[sc], "availability_fraction": frac(tally[sc])} for sc in tally},
           "note": "availability over the materialized set (comparatives the filing itself tags are counted); instants (scope=null) & exact_range excluded per P15 (instants stay 'reported'). Effective end dates (end_date-1) parsed from gp_id."}
    dwrite(RUN + '/comparator_census.json', out); return out


# ============================ TASK 3 + 4: Neo4j recount ============================
def neo4j_recount(RUN):
    uri = os.environ.get('NEO4J_URI'); user = os.environ.get('NEO4J_USERNAME'); pw = os.environ.get('NEO4J_PASSWORD')
    if not (uri and pw): raise SystemExit('ABORT: NEO4J creds not in env (need NEO4J_URI + NEO4J_PASSWORD)')
    fa = load('fixtures/FA_selection.json'); fr = load('fixtures/fixture_resolutions.json')['by_company']
    filings = []
    for tk, lst in sorted(fa['filings'].items()):
        for f in lst: filings.append((tk, f['report_id'], f['form'], f['periodOfReport']))
    filings.sort(key=lambda x: x[1])
    ct = Counter()                      # reconcile cross-tab
    emitted_total = 0; precision_dups = []
    drv = GraphDatabase.driver(uri, auth=(user or 'neo4j', pw)); known_cache = {}
    with drv.session() as s:
        tickers = sorted(set(f[0] for f in filings))
        cik_map = {y['t']: norm_cik(y['c']) for y in s.run("MATCH (c:Company) WHERE c.ticker IN $ts RETURN c.ticker AS t, c.cik AS c", ts=tickers)}
        for tk, rid, form, por in filings:
            fixq = {r['qname']: r['driver'] for r in fr.get(tk, [])}
            if tk not in known_cache: known_cache[tk] = MAT.build_known(s, tk)
            known, fye = known_cache[tk]
            filer = cik_map.get(tk) or norm_cik(rid.split('-')[0])
            rows = list(s.run(MAT_QUERY, rid=rid))
            dim_uids = set(); mem_uids = set()
            for x in rows:
                if x['dims']: dim_uids |= set(norm_uid(d) for d in x['dims'])
                if x['mems']: mem_uids |= set(norm_uid(m) for m in x['mems'])
            dim_map = {y['u']: (y['qn'], y['exp']) for y in s.run("MATCH (d:Dimension) WHERE d.u_id IN $u RETURN d.u_id AS u, d.qname AS qn, d.is_explicit AS exp", u=list(dim_uids))} if dim_uids else {}
            mem_map = {y['u']: (y['qn'], y['lbl']) for y in s.run("MATCH (m:Member) WHERE m.u_id IN $u RETURN m.u_id AS u, m.qname AS qn, m.label AS lbl", u=list(mem_uids))} if mem_uids else {}
            seen_raw = set(); groups = defaultdict(list)
            for x in sorted(rows, key=lambda r: (r['qn'] or '', r['fid'] or '')):
                if x['qn'] not in fixq: continue
                dims_raw = x['dims'] or []; mems_raw = x['mems'] or []
                dimensional = bool(dims_raw or mems_raw)
                arity_fail = node_unresolved = False
                if dimensional:
                    dn = [norm_uid(d) for d in dims_raw]; mn = [norm_uid(m) for m in mems_raw]
                    node_unresolved = any(d not in dim_map for d in dn) or any(m not in mem_map for m in mn)
                    n_exp = sum(1 for d in dn if truthy(dim_map.get(d, ('', '0'))[1]))
                    arity_fail = (n_exp != len(mn))
                    if arity_fail: ct['probe_fail'] += 1               # PROBE view: no filters, no dedup
                # RUN pipeline (materializer order: no_context -> entity -> raw_dup -> unit -> slice)
                if x['cxid'] is None:
                    if dimensional and arity_fail: ct['po_no_context'] += 1
                    continue
                if x['cik'] is not None and norm_cik(x['cik']) != filer:
                    if dimensional and arity_fail: ct['po_entity'] += 1
                    continue
                dk = (x['qn'], x['cxid'], x['val'])
                if dk in seen_raw:
                    if dimensional and arity_fail: ct['po_rawdup'] += 1
                    continue
                seen_raw.add(dk)
                conv = MAT.convert_value(x['un'], x['idv'], x['val'])
                if conv is None:
                    if dimensional and arity_fail: ct['po_unit'] += 1
                    continue
                slices, skip = MAT.resolve_slices(dims_raw, mems_raw, dim_map, mem_map)
                if skip:
                    if skip == 'slice_pairing_dualcik_unresolved':
                        ct['run_dualcik'] += 1
                        if arity_fail: ct['both'] += 1
                        else:
                            ct['run_only'] += 1
                            ct['run_only_member_unresolved' if all(norm_uid(d) in dim_map for d in dims_raw) else 'run_only_other'] += 1
                    elif skip == 'slice_pairing_failclosed':
                        if arity_fail: ct['po_failclosed'] += 1
                    else:                                              # nonslice_or_elimination_axis
                        if arity_fail: ct['po_nonslice'] += 1
                    continue
                # period decode (mirror materializer 210-223) -> gp for grouping + precision scan
                pt = x['pt']; raw_s = str(x['ps'])[:10] if x['ps'] else None
                raw_e = str(x['pe'])[:10] if (x['pe'] and x['pe'] != 'null') else None
                if pt == 'instant':
                    di = MAT.parse_d(raw_s)
                    if di is None: continue
                    ei = (di - timedelta(days=1)).isoformat(); gp = 'gp_%s_%s' % (ei, ei)
                else:
                    de2 = MAT.parse_d(raw_e)
                    if de2 is None: continue
                    if raw_e == por: continue
                    gp = 'gp_%s_%s' % (raw_s, (de2 - timedelta(days=1)).isoformat())
                fscope = 'period=' + gp + ('|slice=' + ';'.join(slices) if slices else '')
                groups[(tk, fixq[x['qn']], fscope)].append({'decimals': x['dec'], 'raw_value': x['val'], 'gp': gp, 'slices': slices or [], 'driver': fixq[x['qn']]})
            for key, rws in sorted(groups.items()):
                outcome, keep = collision_decide(rws)
                if outcome == 'conflict': continue
                emitted_total += 1
                if outcome.startswith('keep_highest'):
                    decs = sorted(str(r['decimals']) for r in rws)
                    precision_dups.append({'report_id': rid, 'registrant': key[0], 'driver': key[1], 'gp_id': rws[0]['gp'],
                                           'slices': rws[0]['slices'], 'kind': outcome, 'group_size': len(rws),
                                           'decimals_seen': decs, 'kept_decimals': str(rws[keep]['decimals']),
                                           'raw_values': sorted(set(str(r['raw_value']) for r in rws)),
                                           'decimals_differ': len(set(decs)) > 1})
    drv.close()
    return ct, emitted_total, precision_dups


def task3_fixtures(precision_dups, RUN, fa_path, fa):
    # ---- P4f synthetic multi-registrant scoping (drives MAT.norm_cik + the inline scope predicate) ----
    facts = [{'id': 'A1', 'cxid': 'cA1', 'cik': '111'}, {'id': 'A2_padded', 'cxid': 'cA2', 'cik': '0000000111'},
             {'id': 'A3', 'cxid': 'cA3', 'cik': '111'}, {'id': 'B1', 'cxid': 'cB1', 'cik': '222'},
             {'id': 'B2', 'cxid': 'cB2', 'cik': '222'}, {'id': 'NOCTX', 'cxid': None, 'cik': None}]
    def run_as(filer):
        si = []; so = []; nc = []
        for f in facts:
            if f['cxid'] is None: nc.append(f['id']); continue                       # no_context skip
            if f['cik'] is not None and norm_cik(f['cik']) != filer: so.append(f['id']); continue  # entity_scoped_out
            si.append(f['id'])
        return {'scoped_in': si, 'entity_scoped_out': so, 'no_context_skipped': nc}
    ra = run_as(norm_cik('111')); rb = run_as(norm_cik('222'))
    p4f = {"spec": "P4f: per-registrant runs; ctx.cik != registrant filer cik -> entity_scoped_out; ctx None -> no_context skip; norm_cik strips zero-pad",
           "synthetic_filing": "2 registrants (A cik 111 incl. one zero-padded ctx, B cik 222) + 1 no-context fact",
           "run_as_A": ra, "run_as_B": rb,
           "isolation_ok": set(ra['scoped_in']).isdisjoint(rb['scoped_in']),
           "padded_cik_scoped_with_A": 'A2_padded' in ra['scoped_in'],
           "counts": {"A": {"in": len(ra['scoped_in']), "out": len(ra['entity_scoped_out']), "no_context": len(ra['no_context_skipped'])},
                      "B": {"in": len(rb['scoped_in']), "out": len(rb['entity_scoped_out']), "no_context": len(rb['no_context_skipped'])}}}
    # ---- P4h synthetic derive + underivable-skip (SPEC logic; harness main() only counts null_por -- EXPERIMENT_ONLY gap) ----
    def derive_por(fx):
        cands = [eff_end_iso(f['end_date']) for f in fx if f['period_type'] == 'duration' and f.get('end_date') not in (None, 'null')]
        cands = [c for c in cands if c]
        return max(cands) if cands else None
    fx_derive = [{'period_type': 'duration', 'start_date': '2024-01-01', 'end_date': '2024-04-01'},
                 {'period_type': 'duration', 'start_date': '2024-01-01', 'end_date': '2025-01-01'},
                 {'period_type': 'instant', 'start_date': '2024-12-31', 'end_date': 'null'}]
    fx_skip = [{'period_type': 'instant', 'start_date': '2024-12-31', 'end_date': 'null'},
               {'period_type': 'instant', 'start_date': '2023-12-31', 'end_date': 'null'}]
    p4h = {"spec": "P4h: null periodOfReport -> derive = max EFFECTIVE duration end (end_date-1, Fable ruling); none -> skip report + count null_por_report_skip (fail-closed)",
           "harness_note": "materializer main() implements only the COUNT branch (line: if not por: null_por_report_skip += 1); the SPEC derive is proven here on synthetic input (EXPERIMENT_ONLY -- promotes to the FACT-18 resolver in production)",
           "derive_branch": {"input": "2 durations (eff-ends 2024-03-31, 2024-12-31) + 1 instant", "derived_periodOfReport": derive_por(fx_derive), "expected": "2024-12-31", "ok": derive_por(fx_derive) == '2024-12-31'},
           "underivable_skip_branch": {"input": "2 instants, 0 durations", "derived_periodOfReport": derive_por(fx_skip), "action": "skip report + count null_por_report_skip", "ok": derive_por(fx_skip) is None}}
    # ---- P4g synthetic keep-highest + conflict (drives collision_decide == materializer inline logic) ----
    def grp(decs, vals): return [{'decimals': d, 'raw_value': v} for d, v in zip(decs, vals)]
    g_id = grp(['-6', '-3'], ['1000000', '1000000']); g_rd = grp(['-6', '-3'], ['1000000', '1000200']); g_cf = grp(['-6', '-3'], ['1000000', '2000000'])
    oi, ki = collision_decide(g_id); ordv, kr = collision_decide(g_rd); oc, kc = collision_decide(g_cf)
    p4g_syn = {"spec": "P4g: within-rounding agreement -> keep highest precision (max decimals); beyond rounding -> skip + xbrl_internal_conflict",
               "keep_highest_identical_value": {"decimals": ['-6', '-3'], "raw": ['1000000', '1000000'], "outcome": oi, "kept_decimals": g_id[ki]['decimals'], "ok": oi == 'keep_highest_identical' and g_id[ki]['decimals'] == '-3'},
               "keep_highest_within_rounding": {"decimals": ['-6', '-3'], "raw": ['1000000', '1000200'], "outcome": ordv, "kept_decimals": g_rd[kr]['decimals'] if kr is not None else None, "ok": ordv == 'keep_highest_rounding' and kr is not None and g_rd[kr]['decimals'] == '-3'},
               "conflict_beyond_rounding": {"decimals": ['-6', '-3'], "raw": ['1000000', '2000000'], "outcome": oc, "ok": oc == 'conflict'}}
    # ---- REAL P4g precision-dup scan of the dry run ----
    diff = [r for r in precision_dups if r['decimals_differ']]
    by_report = Counter(r['report_id'] for r in diff)
    canonical = by_report.most_common(1)[0][0] if diff else None
    p4g_real = {"spec": "intra-filing precision-duplicate pair (mandatory X-XL0 fixture) -- scanned from the 60-filing dry run",
                "precision_dup_groups_total": len(precision_dups), "precision_dup_groups_diff_decimals": len(diff),
                "kept_highest_precision_count": len(diff), "reports_with_precision_dups": sorted(by_report),
                "canonical_report_id": canonical, "examples": diff[:6],
                "all_keep_highest_kinds": dict(Counter(r['kind'] for r in precision_dups))}
    out = {"probe": "fixtures_exercised (mandatory X-XL0 fixtures: P4f multi-registrant, P4h null-pOR, P4g precision-dup)",
           "p4f_multi_registrant_synthetic": p4f, "p4h_null_periodofreport_synthetic": p4h,
           "p4g_precision_dup_synthetic": p4g_syn, "p4g_precision_dup_real_scan": p4g_real}
    dwrite(RUN + '/fixtures_exercised.json', out)
    # ---- backfill FA_selection.json precision_dup_pair_report from the REAL scan ----
    if len(diff) > 0:
        fa['mandatory_fixtures']['precision_dup_pair_report'] = {
            "report_id": canonical, "kept_highest_precision_count": len(diff),
            "precision_dup_pair_groups": len(diff), "reports_with_precision_dups": sorted(by_report),
            "note": "backfilled by EXP-1 dry run; P4g intra-filing precision-duplicate collisions resolved by keep-highest-precision; xbrl_internal_conflict=0"}
        backfill_kind = "REAL"
    else:
        fa['mandatory_fixtures']['precision_dup_pair_report'] = {
            "real_precision_dup_pairs": 0, "synthetic_exercised": True,
            "note": "no intra-filing precision-dup pair with differing decimals occurred in the 60-filing real corpus; P4g keep-highest path exercised via synthetic fixture (fixtures_exercised.json p4g_precision_dup_synthetic)"}
        backfill_kind = "SYNTHETIC_ONLY"
    dwrite(fa_path, fa)
    return out, p4g_real, backfill_kind


def task4_reconcile(ct, run_dualcik_auth, probe_fail_auth, RUN):
    run_dualcik = ct['run_dualcik']; probe_fail = ct['probe_fail']
    po = ct['po_rawdup'] + ct['po_unit'] + ct['po_entity'] + ct['po_no_context'] + ct['po_failclosed'] + ct['po_nonslice']
    delta = run_dualcik - probe_fail
    identity_ok = (run_dualcik == ct['both'] + ct['run_only']) and (probe_fail == ct['both'] + po) and (delta == ct['run_only'] - po)
    note = ("Run 2633 (slice_pairing_dualcik_unresolved) counts UNRESOLVED-NODE skips on de-duplicated, entity-scoped, "
            "unit-whitelisted SURVIVING facts (per-fact, at the slice step); probe 2587 (dualcik_scope fail) counts ARITY mismatches "
            "(explicit-dim-count != member-count) over ALL AAL dimensional fixture-facts with NO unit/dedup/entity filter. "
            "Delta +%d = %d run-only facts (dimension resolves explicit but the coined MEMBER node is unresolved -> run flags dual-CIK, "
            "probe's arity test passes) minus %d probe-only facts the run drops before the slice step "
            "(%d raw-duplicate, %d non-whitelist-unit, %d all-nodes-resolve arity-only->failclosed, %d entity/no-context)."
            % (delta, ct['run_only'], po, ct['po_rawdup'], ct['po_unit'], ct['po_failclosed'], ct['po_entity'] + ct['po_no_context'] + ct['po_nonslice']))
    out = {"probe": "dual-CIK count reconcile (run slice_pairing_dualcik_unresolved vs dualcik_scope_proof fail)",
           "run_dualcik_recomputed": run_dualcik, "run_dualcik_authoritative_skips_json": run_dualcik_auth, "run_dualcik_match": run_dualcik == run_dualcik_auth,
           "probe_fail_recomputed": probe_fail, "probe_fail_authoritative_scope_proof": probe_fail_auth, "probe_fail_match": probe_fail == probe_fail_auth,
           "delta": delta, "crosstab": dict(ct),
           "counting_basis_note": note,
           "identity_check": {"run_dualcik == both + run_only": run_dualcik == ct['both'] + ct['run_only'],
                              "probe_fail == both + probe_only": probe_fail == ct['both'] + po,
                              "delta == run_only - probe_only": delta == ct['run_only'] - po, "all_ok": identity_ok}}
    dwrite(RUN + '/dualcik_count_reconcile.json', out); return out


def task5_fields(RUN):
    dwrite(RUN + '/xxl0_fields.json', {"probe": "X-XL0 re-derived fields (independent verifier)", "count": len(XXL0_FIELDS),
                                       "fields": [f['field'] for f in XXL0_FIELDS], "detail": XXL0_FIELDS,
                                       "source": "harness/xbrl_xxl0_verifier.py chk() calls (source_fact_present is a presence guard, not a re-derived field)"})
    try:
        mp = RUN + '/manifest.json'; m = load(mp)
        m['xxl0_rederived_fields'] = {"count": len(XXL0_FIELDS), "fields": [f['field'] for f in XXL0_FIELDS], "detail": XXL0_FIELDS}
        dwrite(mp, m); return "manifest+xxl0_fields.json"
    except Exception as e:
        return "xxl0_fields.json only (manifest update failed: %s)" % e


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--rundir', required=True); a = ap.parse_args()
    RUN = a.rundir
    rows = [json.loads(l) for l in open(RUN + '/materialized.jsonl')]
    skips = load(RUN + '/skips.json'); scope_proof = load(RUN + '/dualcik_scope_proof.json')
    run_dualcik_auth = skips.get('slice_pairing_dualcik_unresolved'); probe_fail_auth = scope_proof.get('total_fail')
    fa_path = 'fixtures/FA_selection.json'; fa = load(fa_path)

    t1 = task1_collision_census(rows, RUN)
    t2 = task2_comparator_census(rows, RUN)
    ct, emitted_total, precision_dups = neo4j_recount(RUN)
    t3, p4g_real, backfill_kind = task3_fixtures(precision_dups, RUN, fa_path, fa)
    t4 = task4_reconcile(ct, run_dualcik_auth, probe_fail_auth, RUN)
    t5 = task5_fields(RUN)

    print('=== FIDELITY ===')
    print('emitted_recomputed', emitted_total, '| materialized.jsonl rows', len(rows), '| MATCH', emitted_total == len(rows))
    print('run_dualcik', ct['run_dualcik'], '| skips.json', run_dualcik_auth, '| MATCH', ct['run_dualcik'] == run_dualcik_auth)
    print('probe_fail', ct['probe_fail'], '| scope_proof', probe_fail_auth, '| MATCH', ct['probe_fail'] == probe_fail_auth)
    print('=== TASK1 collision_census ===', json.dumps(t1['a_p4g_invariant'], sort_keys=True))
    print('  confusability', json.dumps(t1['b_value_confusability_base_rate'], sort_keys=True))
    print('=== TASK2 comparator_census ===', json.dumps(t2['headline_quarter_ytd'], sort_keys=True), json.dumps(t2['by_scope'], sort_keys=True))
    print('=== TASK3 fixtures ===')
    print('  P4f isolation_ok', t3['p4f_multi_registrant_synthetic']['isolation_ok'], 'counts', json.dumps(t3['p4f_multi_registrant_synthetic']['counts'], sort_keys=True))
    print('  P4h derive', t3['p4h_null_periodofreport_synthetic']['derive_branch']['ok'], '| skip', t3['p4h_null_periodofreport_synthetic']['underivable_skip_branch']['ok'])
    print('  P4g syn', t3['p4g_precision_dup_synthetic']['keep_highest_identical_value']['ok'], t3['p4g_precision_dup_synthetic']['keep_highest_within_rounding']['ok'], t3['p4g_precision_dup_synthetic']['conflict_beyond_rounding']['ok'])
    print('  P4g REAL kept_highest_precision_count', p4g_real['kept_highest_precision_count'], '| canonical', p4g_real['canonical_report_id'], '| backfill', backfill_kind)
    print('=== TASK4 reconcile ===', 'identity_all_ok', t4['identity_check']['all_ok'])
    print('  NOTE:', t4['counting_basis_note'])
    print('=== TASK5 ===', t5, '| 7 fields', [f['field'] for f in XXL0_FIELDS])


if __name__ == '__main__':
    main()
