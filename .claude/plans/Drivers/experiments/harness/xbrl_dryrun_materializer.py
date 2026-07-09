#!/usr/bin/env python3
"""EXP-1 dry-run materializer (READ-ONLY Neo4j, 0 LLM). XBRL 5.2 steps 1-8.
Fable-pinned P4c/P4a value table (ra_0002). Writes NOTHING to Neo4j. Deterministic (sorted; no now()/rand)."""
import os, re, json, sys, argparse
from datetime import date, timedelta
from neo4j import GraphDatabase
sys.path.insert(0, '/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts')
import fiscal_math as FM

FORMS = ['10-K', '10-Q', '10-K/A', '10-Q/A']

CONFIRMED_AXES = {
 'us-gaap:StatementBusinessSegmentsAxis': 'segment', 'us-gaap:SubsegmentsAxis': 'segment', 'qdel:BusinessUnitAxis': 'segment',
 'cmcsa:BusinessUnitAxis': 'segment', 'gtes:BusinessUnitAxis': 'segment', 'cah:MedicalSegmentAxis': 'segment',
 'cah:PharmaceuticalSegmentAxis': 'segment', 'oke:RegulatedSegmentByNameAxis': 'segment', 'oke:ReportableSegmentByNameAxis': 'segment',
 'pru:DivisionAxis': 'segment', 'emn:OtherSegmentsAxis': 'segment', 'rxp:SegmentAxis': 'segment',
 'srt:ProductOrServiceAxis': 'product', 'atk:BrandAxis': 'product', 'ppl:RatesTypeAxis': 'product', 'khc:BrandsAxis': 'product',
 'pep:BrandsAxis': 'product', 'pvh:BrandsAxis': 'product', 'www:BrandAxis': 'product', 'abbv:KeyProductPortfolioAxis': 'product',
 'exas:ServiceOrProductTypeAxis': 'product', 'lpx:ProducttypeAxis': 'product', 'adsk:ContractWithCustomerResearchDevelopmentChannelAxis': 'product',
 'blmn:RestaurantConceptAxis': 'product', 'srt:StatementGeographicalAxis': 'geography', 'us-gaap:GeographicDistributionAxis': 'geography',
 'us-gaap:AirlineDestinationsAxis': 'geography', 'hig:RegionsAxis': 'geography', 'lear:RegionReportingInformationByRegionAxis': 'geography',
 'midd:RegionReportingInformationByRegionAxis': 'geography', 'pg:GeographicLocationAxis': 'geography', 'alk:InvestmentGeographicRegionAxis': 'geography',
 'srt:MajorCustomersAxis': 'customer', 'dy:CustomerTypeAxis': 'customer', 'adi:RevenueFromContractWithCustomerEndMarketAxis': 'customer',
 'fn:ContractWithCustomerMarketCategoryAxis': 'customer', 'ter:SeriesOfCustomerAxis': 'customer',
 'us-gaap:ContractWithCustomerSalesChannelAxis': 'channel', 'us-gaap:FranchisorDisclosureAxis': 'channel',
 'us-gaap:HealthCareOrganizationRevenueSourcesAxis': 'channel', 'us-gaap:ContractWithCustomerBasisOfPricingAxis': 'channel',
 'mcd:SegmentReportingInformationBySecondarySegmentAxis': 'channel', 'yum:FranchiseeOwnedStoresAxis': 'channel',
 'low:StoreTypeAxis': 'channel', 'aap:NumberOfStoresAxis': 'channel', 'dei:LegalEntityAxis': 'entity',
 'us-gaap:EquityMethodInvestmentNonconsolidatedInvesteeAxis': 'entity', 'srt:ScheduleOfEquityMethodInvestmentEquityMethodInvesteeNameAxis': 'entity',
 'us-gaap:JointlyOwnedUtilityPlantAxis': 'entity', 'us-gaap:IncomeStatementBalanceSheetAndAdditionalDisclosuresByDisposalGroupsIncludingDiscontinuedOperationsAxis': 'entity',
 'us-gaap:RealEstatePropertiesAxis': 'entity', 'srt:OwnershipAxis': 'entity', 'ppl:ByCompanyAxis': 'entity',
 'aes:DebtDefaultBySubsidiaryAxis': 'entity', 'yum:CompanyOwnedStoresAxis': 'entity', 'fe:BusinessUnitsAxis': 'entity', 'tsco:ConsolidatedStoresAxis': 'entity'}
STD_NS = {'us-gaap', 'srt', 'dei', 'ecd', 'cyd', 'country', 'stpr', 'us-gaap-supplement', 'srt-supplement'}
ELIMINATION_LOCALS = {'IntersegmentEliminationMember', 'ConsolidationEliminationsMember', 'GeographyEliminationsMember',
 'SubsegmentEliminationsMember', 'EliminationsMember', 'IntersegmentEliminationsMember'}  # partial vetted set (EXPERIMENT_ONLY completeness)
PERSHARE_HINT = re.compile(r'pershare|earningspershare|(^|[^a-z])eps([^a-z]|$)', re.I)

PROMOTION_NOTES = [
 {"file": "harness/xbrl_dryrun_materializer.py", "function": "convert_value", "rule": "P4c/P4a Fable-pinned fixed conversion table (ra_0002)",
  "disposition": "PROMOTE_CANDIDATE", "proof_file": "materialized.jsonl + X-XL0 verifier",
  "production_rewrite_needed": "this 3-row table IS the production XBRL value step; production driver_writer/xbrl_link_writer calls it (not the harness); extend per OD-10 back-port (non-USD currency axis, count-scale)"},
 {"file": "harness/xbrl_dryrun_materializer.py", "function": "resolve_slices", "rule": "O13 ratified explicit-dim positional pairing + CONFIRMED_AXES + FS-18/OD-9 label normalizer",
  "disposition": "PROMOTE_CANDIDATE", "proof_file": "materialized.jsonl slices + determinism_report.json",
  "production_rewrite_needed": "same binding; CONFIRMED_AXES must LOAD from the frozen catalog table (not hardcode); ELIMINATION_LOCALS must be the full vetted ~24 list (harness carries a partial set)"},
 {"file": "harness/xbrl_dryrun_materializer.py", "function": "build_known + classify_period", "rule": "P14 period_scope from XBRL-history windows + exact_range/WARN fallback; quarter>Q1-YTD",
  "disposition": "PROMOTE_CANDIDATE", "proof_file": "materialized.jsonl period_scope + determinism_report.json",
  "production_rewrite_needed": "promote into the FACT-18 resolver wrapper (shared classifier); harness derivation (shortest=quarter / longest=ytd|annual) is APPROXIMATE - production needs full P14c actual-fiscal-end algorithm incl SEC quarter cache + half/ttm/monthly"},
 {"file": "harness/xbrl_dryrun_materializer.py", "function": "per-report pull + entity-scope + P4g collision", "rule": "P4f entity-scope (IN_CONTEXT->cik) + P4g raw dedup/collision on raw values+decimals BEFORE conversion",
  "disposition": "PROMOTE_CANDIDATE", "proof_file": "skips.json + collision_census.json",
  "production_rewrite_needed": "production runs inside driver_writer; same logic; entity-scope via IN_CONTEXT->FOR_COMPANY (harness compares ctx.cik == filer cik derived from report id)"},
 {"file": "harness/xbrl_dryrun_materializer.py", "function": "write_reason (primary vs comparative)", "rule": "P4b strict primary (period end == periodOfReport)",
  "disposition": "PROMOTE_CANDIDATE", "proof_file": "materialized.jsonl primary flag",
  "production_rewrite_needed": "harness emits ALL facts flagged primary/comparative; production non-primary-on-change (backfill vs restatement) needs series-aware cross-event state - NOT implemented in the X-XL0 harness"},
 {"file": "harness/xbrl_dryrun_materializer.py", "function": "<module scaffolding: argparse, neo4j session, jsonl writers>", "rule": "EXP-1 X-XL0 probe harness",
  "disposition": "EXPERIMENT_ONLY", "proof_file": "the run dir",
  "production_rewrite_needed": "throwaway (12 §2.2, never imported by prod); production entrypoint is xbrl_link_writer.py (12 build step 9b) - the RULES/TABLES above promote, this scaffolding does not"}]

IMPLEMENTATION_FIXES = [
 {"id": "bug1_cik_zero_padding", "type": "implementation_bug_fix", "not_a_design_ruling": True,
  "file": "harness/xbrl_dryrun_materializer.py", "function": "norm_uid + dim/mem u_id lookup",
  "bug": "Context.dimension_u_ids/member_u_ids carry a zero-padded 10-digit cik (0000023217:...); Dimension.u_id/Member.u_id carry the unpadded cik (23217:...). Lookup missed -> every explicit dim dropped -> slice_pairing_failclosed.",
  "fix": "norm_uid() strips leading zeros on the cik segment before the u_id lookup.",
  "verified": "normalized u_id matches Dimension+Member count=1; dry3 re-run: slice_pairing_failclosed drops and slices populate."}]

FABLE_RULINGS = [
 {"id": "period_end_exclusive_decode", "ruled_by": "Fable 2026-07-09",
  "verified_precondition": "start-date check STARTS_UNSHIFTED_OK_TO_APPLY (period_start_check.json: 140/140 primary end-decode-to-por, 122/140 start-chains, 0 invalid)",
  "rule": "stored end_date is EXCLUSIVE. duration: effective_start=start_date, effective_end=end_date-1. instant: effective_instant=stored-1. P4b/gp_ids/build_known/classifier/fiscal/P4h use EFFECTIVE dates; raw dates stay in provenance; inclusive day count = raw_end-raw_start (no double adjust). A raw end_date==periodOfReport row (LUV-style) -> skip+count period_end_convention_suspect, never non-primary. instant_off_pOR_by_one RETIRED (the +1 is the convention).",
  "verifier_note": "X-XL0 verifier must INDEPENDENTLY implement this decode (not import from the materializer)."},
 {"id": "dualcik_unresolved_slice_skip", "ruled_by": "Fable 2026-07-09",
  "verified_precondition": "dualcik_scope_proof.json: AAL-only (11/12 companies pair clean); 701 would-materialize; real slice axes affected (entity=1410, product=513, geography=104)",
  "rule": "No aliasing rule ships in EXP-1. After normal normalization, if a dimension/member node still does NOT resolve -> SKIP the whole affected fact + count slice_pairing_dualcik_unresolved. Do NOT use qname-only matching; do NOT use cross-CIK/global alias matching; do NOT drop AAL.",
  "deferred_to": "O12 bundle (ingestion repair / possible future certified recovery of skipped AAL slice facts)"}]


def truthy(v): return str(v).strip().lower() in ('true', '1', 't', 'yes')
def slug(s):
    s = re.sub(r'[^a-z0-9]+', '_', (s or '').lower()).strip('_'); return re.sub(r'_+', '_', s)
def norm_cik(c): return str(c or '').lstrip('0')
def norm_uid(u):
    """Bug1 fix: strip leading zeros on the cik segment. Context u_ids use padded cik (0000023217:...),
    Dimension.u_id/Member.u_id use unpadded cik (23217:...)."""
    if not u: return u
    i = u.find(':')
    if i > 0 and u[:i].isdigit(): return str(int(u[:i])) + u[i:]
    return u
def parse_d(s):
    if not s or s == 'null': return None
    try: return date.fromisoformat(str(s)[:10])
    except Exception: return None
def to_num(v): return float(str(v).replace(',', ''))
def dec_int(d):
    ds = str(d).strip()
    if ds.upper() == 'INF': return 999
    try: return int(ds)
    except Exception: return None


def convert_value(unit_name, is_divide, raw_value):
    v = to_num(raw_value)
    if unit_name == 'iso4217:USD' and is_divide != '1': return ('m_usd', round(v / 1e6, 6))
    if unit_name == 'shares' and is_divide != '1': return ('count', v)
    if unit_name == 'iso4217:USDshares' and is_divide == '1': return ('usd', v)
    return None


def resolve_slices(dims, mems, dim_map, mem_map):
    """Ratified O13 + Fable dual-CIK ruling. Returns (slices|None, skipreason|None)."""
    dims = [norm_uid(d) for d in dims]; mems = [norm_uid(m) for m in mems]
    # Fable dual-CIK ruling (2026-07-09): after normalization, if any dim/member node still does NOT resolve
    # -> skip the whole fact + count. NO aliasing, NO qname-only, NO cross-CIK/global alias matching.
    if any(d not in dim_map for d in dims) or any(m not in mem_map for m in mems):
        return None, 'slice_pairing_dualcik_unresolved'
    explicit = [d for d in dims if truthy(dim_map[d][1])]
    if len(explicit) != len(mems):
        return None, 'slice_pairing_failclosed'
    slices = []
    for du, mu in zip(explicit, mems):
        axis = dim_map.get(du, ('?', '?'))[0]; mqn, mlbl = mem_map.get(mu, ('?', '?'))
        if axis in CONFIRMED_AXES:
            if CONFIRMED_AXES[axis] == 'segment' and (mqn.split(':')[-1] in ELIMINATION_LOCALS):
                return None, 'nonslice_or_elimination_axis'
            slices.append(CONFIRMED_AXES[axis] + ':' + slug(mlbl))
        elif axis.split(':')[0] in STD_NS:
            return None, 'nonslice_or_elimination_axis'
        else:
            slices.append('unknown:' + slug(axis) + '__' + slug(mlbl))
    return sorted(slices), None


def build_known(session, ticker):
    rows = list(session.run(
        "MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker:$t}) WHERE r.formType IN $forms AND r.xbrl_status='COMPLETED' AND r.periodOfReport IS NOT NULL "
        "MATCH (r)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_PERIOD]->(p:Period) WHERE p.period_type='duration' "
        "RETURN DISTINCT r.formType AS form, r.periodOfReport AS por, p.start_date AS s, p.end_date AS e", t=ticker, forms=FORMS))
    by = {}
    for x in rows:
        ds, de = parse_d(x['s']), parse_d(x['e'])
        if not (ds and de): continue
        ef_end = (de - timedelta(days=1)).isoformat()   # Fable: effective inclusive end
        if ef_end != x['por']: continue                 # PRIMARY windows only (effective end == periodOfReport)
        by.setdefault(x['por'], []).append(((de - timedelta(days=1) - ds).days, str(x['s'])[:10], ef_end, x['form']))
    known = {}; fye = None
    for por, wins in sorted(by.items()):
        wins.sort()
        short = wins[0]; lng = wins[-1]
        for days, s, e, form in wins:
            if form.startswith('10-K'): fye = parse_d(e).month
        if short[0] == lng[0]:
            known.setdefault((short[1], short[2]), 'annual' if short[3].startswith('10-K') else 'quarter')
        else:
            known[(short[1], short[2])] = 'quarter'
            known[(lng[1], lng[2])] = 'annual' if lng[3].startswith('10-K') else 'ytd'
    return known, fye


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--rundir', required=True); ap.add_argument('--dry3', action='store_true'); a = ap.parse_args()
    uri = os.environ.get('NEO4J_URI'); user = os.environ.get('NEO4J_USERNAME'); pw = os.environ.get('NEO4J_PASSWORD')
    if not (uri and pw): raise SystemExit('ABORT: NEO4J creds not in env')
    fa = json.load(open('fixtures/FA_selection.json')); fr = json.load(open('fixtures/fixture_resolutions.json'))['by_company']
    filings = []
    for tk, lst in sorted(fa['filings'].items()):
        for f in lst: filings.append((tk, f['report_id'], f['form'], f['periodOfReport']))
    filings.sort(key=lambda x: x[1])
    if a.dry3: filings = filings[:3]
    ctr = {k: 0 for k in ['no_context', 'entity_scoped_out', 'unit_nonwhitelist', 'usd_bare_pershare_suspect', 'nonslice_or_elimination_axis',
                          'xbrl_internal_conflict', 'slice_pairing_failclosed', 'slice_pairing_dualcik_unresolved', 'null_por_report_skip', 'raw_duplicate', 'latent_excluded',
                          'period_end_convention_suspect', 'report_primary_window_missing', 'fixture_fact_seen', 'emitted', 'proc_error']}
    drv = GraphDatabase.driver(uri, auth=(user or 'neo4j', pw)); out = []; known_cache = {}
    with drv.session() as s:
        for tk, rid, form, por in filings:
            fixq = {r['qname']: r['driver'] for r in fr.get(tk, [])}
            if tk not in known_cache: known_cache[tk] = build_known(s, tk)
            known, fye = known_cache[tk]
            if not por: ctr['null_por_report_skip'] += 1
            filer = norm_cik(rid.split('-')[0])
            rows = list(s.run(
                "MATCH (r:Report {id:$rid})-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(con:Concept) WHERE f.is_numeric='1' AND f.is_nil='0' "
                "OPTIONAL MATCH (f)-[:IN_CONTEXT]->(ctx:Context) OPTIONAL MATCH (f)-[:HAS_PERIOD]->(p:Period) OPTIONAL MATCH (f)-[:HAS_UNIT]->(u:Unit) "
                "RETURN f.id AS fid, con.qname AS qn, f.value AS val, f.decimals AS dec, ctx.context_id AS cxid, ctx.cik AS cik, "
                "ctx.dimension_u_ids AS dims, ctx.member_u_ids AS mems, p.period_type AS pt, p.start_date AS ps, p.end_date AS pe, u.name AS un, u.is_divide AS idv", rid=rid))
            dim_uids = set(); mem_uids = set()
            for x in rows:
                if x['dims']: dim_uids |= set(norm_uid(d) for d in x['dims'])
                if x['mems']: mem_uids |= set(norm_uid(m) for m in x['mems'])
            dim_map = {y['u']: (y['qn'], y['exp']) for y in s.run("MATCH (d:Dimension) WHERE d.u_id IN $u RETURN d.u_id AS u, d.qname AS qn, d.is_explicit AS exp", u=list(dim_uids))} if dim_uids else {}
            mem_map = {y['u']: (y['qn'], y['lbl']) for y in s.run("MATCH (m:Member) WHERE m.u_id IN $u RETURN m.u_id AS u, m.qname AS qn, m.label AS lbl", u=list(mem_uids))} if mem_uids else {}
            seen_raw = set(); groups = {}; report_has_primary = False
            for x in sorted(rows, key=lambda r: (r['qn'] or '', r['fid'] or '')):
                if x['qn'] not in fixq: continue
                ctr['fixture_fact_seen'] += 1
                try:
                    if x['cxid'] is None: ctr['no_context'] += 1; continue
                    if x['cik'] is not None and norm_cik(x['cik']) != filer: ctr['entity_scoped_out'] += 1; continue
                    dk = (x['qn'], x['cxid'], x['val'])
                    if dk in seen_raw: ctr['raw_duplicate'] += 1; continue
                    seen_raw.add(dk)
                    if PERSHARE_HINT.search(x['qn'] or '') and x['un'] == 'iso4217:USD' and x['idv'] != '1': ctr['usd_bare_pershare_suspect'] += 1
                    conv = convert_value(x['un'], x['idv'], x['val'])
                    if conv is None: ctr['unit_nonwhitelist'] += 1; continue
                    slices, skip = resolve_slices(x['dims'] or [], x['mems'] or [], dim_map, mem_map)
                    if skip: ctr[skip] += 1; continue
                    pt = x['pt']; raw_s = str(x['ps'])[:10] if x['ps'] else None
                    raw_e = str(x['pe'])[:10] if (x['pe'] and x['pe'] != 'null') else None
                    if pt == 'instant':                                    # Fable: effective instant = stored - 1
                        di = parse_d(raw_s)
                        if di is None: ctr['proc_error'] += 1; continue
                        ei = (di - timedelta(days=1)).isoformat(); gp = 'gp_%s_%s' % (ei, ei); scope = 'null'; pend = ei
                    else:
                        de2 = parse_d(raw_e)
                        if de2 is None: ctr['proc_error'] += 1; continue
                        if raw_e == por:                                   # Fable: raw end == pOR (LUV-style) -> skip+count, never non-primary
                            ctr['period_end_convention_suspect'] += 1; continue
                        ef_end = (de2 - timedelta(days=1)).isoformat()     # Fable: effective end = end_date - 1; start unshifted
                        gp = 'gp_%s_%s' % (raw_s, ef_end); scope = known.get((raw_s, ef_end), 'exact_range'); pend = ef_end
                    fscope = 'period=' + gp + ('|slice=' + ';'.join(slices) if slices else '')
                    du_id = 'du:%s:%s:%s' % (rid, fixq[x['qn']], fscope)
                    primary = (pend == por)
                    if primary: report_has_primary = True
                    fy, fq = (None, None)
                    if pt != 'instant' and fye and parse_d(pend):
                        d2 = parse_d(pend); fy, fq = FM.period_to_fiscal(d2.year, d2.month, d2.day, fye, '10-K' if form.startswith('10-K') else '10-Q')
                    row = {'du_id': du_id, 'report_id': rid, 'registrant': tk, 'driver': fixq[x['qn']], 'qname': x['qn'], 'xbrl_fact_id': x['fid'],
                           'level_unit': conv[0], 'value_canonical': conv[1], 'decimals': x['dec'],
                           'period': {'gp_id': gp, 'period_scope': scope, 'time_type': pt, 'fiscal_year': fy, 'fiscal_quarter': fq,
                                      'raw_start_date': x['ps'], 'raw_end_date': x['pe']},
                           'slices': slices or [], 'primary': primary, 'write_reason': 'primary' if primary else 'comparative', 'raw_value': x['val']}
                    groups.setdefault((tk, fixq[x['qn']], fscope), []).append(row)
                except Exception:
                    ctr['proc_error'] += 1
            for key, rws in sorted(groups.items()):
                if len(rws) == 1:
                    out.append(rws[0]); ctr['emitted'] += 1; continue
                rawvals = set(to_num(r['raw_value']) for r in rws)
                if len(rawvals) == 1:
                    out.append(max(rws, key=lambda r: (dec_int(r['decimals']) if dec_int(r['decimals']) is not None else -999))); ctr['emitted'] += 1
                else:
                    decs = [dec_int(r['decimals']) for r in rws]
                    if any(d is None for d in decs):
                        ctr['xbrl_internal_conflict'] += 1; continue
                    coarse = min(decs)
                    rounded = set(round(to_num(r['raw_value']), coarse) for r in rws)
                    if len(rounded) == 1:
                        out.append(max(rws, key=lambda r: dec_int(r['decimals']))); ctr['emitted'] += 1
                    else:
                        ctr['xbrl_internal_conflict'] += 1
            if not report_has_primary:
                ctr['report_primary_window_missing'] += 1
    drv.close()
    for r in out: r.pop('raw_value', None)
    out.sort(key=lambda r: r['du_id'])
    suf = '.dry3' if a.dry3 else ''
    with open(a.rundir + '/materialized%s.jsonl' % suf, 'w') as fh:
        for r in out: fh.write(json.dumps(r, sort_keys=True) + '\n')
    json.dump(ctr, open(a.rundir + '/skips%s.json' % suf, 'w'), indent=2, sort_keys=True)
    try:
        mf = a.rundir + '/manifest.json'; m = json.load(open(mf))
        m['promotion_notes'] = PROMOTION_NOTES; m['implementation_fixes'] = IMPLEMENTATION_FIXES; m['fable_rulings'] = FABLE_RULINGS
        json.dump(m, open(mf, 'w'), indent=2, sort_keys=True)
    except Exception as e:
        print('manifest promo update failed', e)
    scopes = {}
    for r in out: scopes[r['period']['period_scope']] = scopes.get(r['period']['period_scope'], 0) + 1
    print('REPORTS', len(filings), 'EMITTED', len(out))
    print('COUNTERS', json.dumps(ctr, sort_keys=True))
    print('PERIOD_SCOPES', json.dumps(scopes, sort_keys=True))
    print('SAMPLE', json.dumps(out[:2], sort_keys=True) if out else '[]')


if __name__ == '__main__':
    main()
