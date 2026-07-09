#!/usr/bin/env python3
"""EXP-1 X-XL0 INDEPENDENT verifier (READ-ONLY, 0 LLM). Re-reads each materialized row's SOURCE Fact and
re-derives value/scale, unit, decimals, concept, time_type, gp_id (period dates) and members->slice with its
OWN fresh implementation of the P4c/P4a table + Fable exclusive-end decode + O13 dual-CIK pairing (NOT imported
from the materializer). Frozen axis DATA is shared (it is the catalog spec); the LOGIC is independent.
Bar: field_match_rate == 1.0. Writes xxl0_report.json."""
import re, os, json, argparse
from datetime import date, timedelta
from neo4j import GraphDatabase

_SLICE = {
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
_STD = {'us-gaap', 'srt', 'dei', 'ecd', 'cyd', 'country', 'stpr', 'us-gaap-supplement', 'srt-supplement'}
_ELIM = {'IntersegmentEliminationMember', 'ConsolidationEliminationsMember', 'GeographyEliminationsMember',
         'SubsegmentEliminationsMember', 'EliminationsMember', 'IntersegmentEliminationsMember'}


def v_true(x): return str(x).strip().lower() in ('1', 'true', 't', 'yes')
def v_norm(u):
    if not u: return u
    k = u.find(':')
    return (str(int(u[:k])) + u[k:]) if (k > 0 and u[:k].isdigit()) else u
def v_slug(s): return re.sub('_+', '_', re.sub('[^a-z0-9]+', '_', (s or '').lower())).strip('_')
def v_value(unit, isdiv, raw):
    x = float(str(raw).replace(',', ''))
    if unit == 'iso4217:USD' and isdiv != '1': return ('m_usd', round(x / 1000000.0, 6))
    if unit == 'shares' and isdiv != '1': return ('count', x)
    if unit == 'iso4217:USDshares' and isdiv == '1': return ('usd', x)
    return (None, None)
def v_effdate(s): return (date.fromisoformat(str(s)[:10]) - timedelta(days=1)).isoformat()
def v_slices(dims, mems, dmap, mmap):
    dd = [v_norm(d) for d in (dims or [])]; mm = [v_norm(m) for m in (mems or [])]
    if any(d not in dmap for d in dd) or any(m not in mmap for m in mm): return '<dualcik_unresolved>'
    exp = [d for d in dd if v_true(dmap[d][1])]
    if len(exp) != len(mm): return '<pairing_failclosed>'
    out = []
    for du, mu in zip(exp, mm):
        ax = dmap[du][0]; mq, ml = mmap[mu]
        if ax in _SLICE:
            if _SLICE[ax] == 'segment' and mq.split(':')[-1] in _ELIM: return '<nonslice_or_elim>'
            out.append(_SLICE[ax] + ':' + v_slug(ml))
        elif (ax.split(':')[0] if ax else '') in _STD:
            return '<nonslice_or_elim>'
        else:
            out.append('unknown:' + v_slug(ax) + '__' + v_slug(ml))
    return sorted(out)
def eqv(a, b):
    if isinstance(a, float) or isinstance(b, float):
        try: return abs(float(a) - float(b)) < 1e-6
        except Exception: return a == b
    return a == b


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--rundir', required=True); a = ap.parse_args()
    uri = os.environ['NEO4J_URI']; user = os.environ.get('NEO4J_USERNAME'); pw = os.environ['NEO4J_PASSWORD']
    rows = [json.loads(l) for l in open(a.rundir + '/materialized.jsonl')]
    by_rep = {}
    for r in rows: by_rep.setdefault(r['report_id'], []).append(r)
    drv = GraphDatabase.driver(uri, auth=(user or 'neo4j', pw))
    checks = 0; mism = 0; field_mism = {}; examples = []
    with drv.session() as s:
        for rid, rrows in sorted(by_rep.items()):
            facts = {y['fid']: y for y in s.run(
                "MATCH (r:Report {id:$rid})-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_CONCEPT]->(con:Concept) "
                "WHERE f.is_numeric='1' AND f.is_nil='0' OPTIONAL MATCH (f)-[:IN_CONTEXT]->(ctx:Context) "
                "OPTIONAL MATCH (f)-[:HAS_PERIOD]->(p:Period) OPTIONAL MATCH (f)-[:HAS_UNIT]->(u:Unit) "
                "RETURN f.id AS fid, con.qname AS qn, f.value AS val, f.decimals AS dec, ctx.dimension_u_ids AS dims, "
                "ctx.member_u_ids AS mems, p.period_type AS pt, p.start_date AS ps, p.end_date AS pe, u.name AS un, u.is_divide AS idv", rid=rid)}
            du = set(); mu = set()
            for r in rrows:
                f = facts.get(r['xbrl_fact_id'])
                if f:
                    if f['dims']: du |= set(v_norm(d) for d in f['dims'])
                    if f['mems']: mu |= set(v_norm(m) for m in f['mems'])
            dmap = {y['u']: (y['qn'], y['exp']) for y in s.run("MATCH (d:Dimension) WHERE d.u_id IN $u RETURN d.u_id AS u, d.qname AS qn, d.is_explicit AS exp", u=list(du))} if du else {}
            mmap = {y['u']: (y['qn'], y['lbl']) for y in s.run("MATCH (m:Member) WHERE m.u_id IN $u RETURN m.u_id AS u, m.qname AS qn, m.label AS lbl", u=list(mu))} if mu else {}
            for r in rrows:
                f = facts.get(r['xbrl_fact_id'])

                def chk(field, expected, actual):
                    nonlocal checks, mism
                    checks += 1
                    if not eqv(expected, actual):
                        mism += 1; field_mism[field] = field_mism.get(field, 0) + 1
                        if len(examples) < 12: examples.append({'du_id': r['du_id'], 'field': field, 'materializer': actual, 'verifier': expected})
                if f is None:
                    chk('source_fact_present', True, False); continue
                cu, cv = v_value(f['un'], f['idv'], f['val'])
                chk('level_unit', cu, r['level_unit'])
                chk('value_canonical', cv, r['value_canonical'])
                chk('decimals', f['dec'], r['decimals'])
                chk('qname', f['qn'], r['qname'])
                chk('time_type', f['pt'], r['period']['time_type'])
                if f['pt'] == 'instant':
                    ei = v_effdate(f['ps']); gp = 'gp_%s_%s' % (ei, ei)
                else:
                    gp = 'gp_%s_%s' % (str(f['ps'])[:10], v_effdate(f['pe']))
                chk('gp_id', gp, r['period']['gp_id'])
                sl = v_slices(f['dims'], f['mems'], dmap, mmap)
                chk('slices', sl, r['slices'])
    drv.close()
    rate = 1.0 - (mism / checks) if checks else 0.0
    out = {'probe': 'X-XL0 independent verifier', 'rows': len(rows), 'checks': checks, 'mismatches': mism,
           'field_match_rate': round(rate, 8), 'field_mismatches': field_mism, 'examples': examples, 'pass': mism == 0}
    json.dump(out, open(a.rundir + '/xxl0_report.json', 'w'), indent=2, sort_keys=True)
    print('FIELD_MATCH_RATE', out['field_match_rate'], '| CHECKS', checks, '| MISMATCHES', mism)
    print('FIELD_MISMATCHES', json.dumps(field_mism, sort_keys=True))
    if examples: print('EXAMPLES', json.dumps(examples[:6], sort_keys=True))
    print('XXL0_PASS', out['pass'])


if __name__ == '__main__':
    main()
