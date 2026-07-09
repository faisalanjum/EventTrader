#!/usr/bin/env python3
"""EXP-1 Bug-2 confirmation (READ-ONLY, 0 LLM). Is Period.end_date universally EXCLUSIVE
(== periodOfReport + 1 day) across the 60 FA_selection filings, or only AAL/DRI?
Counts, per filing, current-period facts under BOTH readings. Writes proof to run dir. No writes, no P4b change."""
import os, json, argparse
from datetime import date, timedelta
from neo4j import GraphDatabase

FILER_5253 = {'DRI', 'AZO', 'BBY', 'ULTA', 'CAKE'}  # verified 52/53-week filers (work order WP-FA)

Q = ("MATCH (r:Report {id:$rid})-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(f:Fact)-[:HAS_PERIOD]->(p:Period) "
     "RETURN sum(CASE WHEN p.period_type='duration' AND p.end_date=$por  THEN 1 ELSE 0 END) AS dur_eq, "
     "sum(CASE WHEN p.period_type='duration' AND p.end_date=$por1 THEN 1 ELSE 0 END) AS dur_ex, "
     "sum(CASE WHEN p.period_type='instant'  AND p.start_date=$por  THEN 1 ELSE 0 END) AS ins_eq, "
     "sum(CASE WHEN p.period_type='instant'  AND p.start_date=$por1 THEN 1 ELSE 0 END) AS ins_ex")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--rundir', required=True); a = ap.parse_args()
    uri = os.environ['NEO4J_URI']; user = os.environ.get('NEO4J_USERNAME'); pw = os.environ['NEO4J_PASSWORD']
    fa = json.load(open('fixtures/FA_selection.json'))
    filings = []
    for tk, lst in sorted(fa['filings'].items()):
        for f in lst: filings.append((tk, f['report_id'], f['form'], f['periodOfReport']))
    filings.sort(key=lambda x: (x[0], x[1]))
    drv = GraphDatabase.driver(uri, auth=(user or 'neo4j', pw)); rows = []
    with drv.session() as s:
        for tk, rid, form, por in filings:
            if not por:
                rows.append({'ticker': tk, 'report_id': rid, 'form': form, 'por': None, 'convention': 'null_por'}); continue
            por1 = (date.fromisoformat(por[:10]) + timedelta(days=1)).isoformat()
            x = s.run(Q, rid=rid, por=por, por1=por1).single()
            de, dx, ie, ix = x['dur_eq'], x['dur_ex'], x['ins_eq'], x['ins_ex']
            if de == 0 and dx > 0: conv = 'exclusive'
            elif de > 0 and dx == 0: conv = 'inclusive'
            elif de == 0 and dx == 0: conv = 'neither_current'
            else: conv = 'mixed'
            rows.append({'ticker': tk, 'report_id': rid, 'form': form, 'por': por, 'is_5253': tk in FILER_5253,
                         'dur_end_eq_por': de, 'dur_end_eq_por_plus1': dx, 'inst_eq_por': ie, 'inst_eq_por_plus1': ix,
                         'convention': conv})
    drv.close()

    def agg(sel):
        r = [x for x in rows if x.get('por') and sel(x)]
        return {'filings': len(r), 'dur_eq': sum(x['dur_end_eq_por'] for x in r), 'dur_ex': sum(x['dur_end_eq_por_plus1'] for x in r),
                'ins_eq': sum(x['inst_eq_por'] for x in r), 'ins_ex': sum(x['inst_eq_por_plus1'] for x in r)}
    conv_counts = {}
    for x in rows:
        conv_counts[x['convention']] = conv_counts.get(x['convention'], 0) + 1
    dated = [x for x in rows if x.get('por')]
    all_excl = bool(dated) and all(x['convention'] == 'exclusive' for x in dated)
    proof = {'probe': 'Bug-2 period-end convention over 60 FA filings (read-only)',
             'question': 'is Period.end_date universally exclusive (== periodOfReport + 1 day)?',
             'filings_total': len(rows), 'convention_counts': conv_counts,
             'overall': agg(lambda x: True),
             'by_5253': {'52_53_week': agg(lambda x: x.get('is_5253')), 'calendar': agg(lambda x: not x.get('is_5253'))},
             'by_form': {'10-K': agg(lambda x: x['form'].startswith('10-K')), '10-Q': agg(lambda x: x['form'].startswith('10-Q'))},
             'verdict': 'UNIVERSALLY_EXCLUSIVE' if all_excl else 'NOT_UNIVERSAL_see_convention_counts',
             'recommendation': ('Route to Fable: adopt inclusive-end reading -- P4b / build_known / classifier compare (end_date - 1 day) == periodOfReport. Strict equality preserved; only the correct field. instant_off_pOR_by_one retires (the +1 is the convention).'
                                if all_excl else
                                'Route to Fable WITH the per-filing split: the +1 convention is NOT universal; a blanket end_date-1 would misread the inclusive filings.'),
             'per_filing': rows}
    json.dump(proof, open(a.rundir + '/period_convention_proof.json', 'w'), indent=2, sort_keys=True)
    print('VERDICT', proof['verdict'])
    print('CONVENTION_COUNTS', json.dumps(conv_counts, sort_keys=True))
    print('OVERALL', json.dumps(proof['overall'], sort_keys=True))
    print('BY_5253', json.dumps(proof['by_5253'], sort_keys=True))
    print('BY_FORM', json.dumps(proof['by_form'], sort_keys=True))
    print('%-5s %-24s %-5s %-11s %5s %5s %5s %5s  %-11s' % ('tk', 'report_id', 'form', 'por', 'dEQ', 'dEX', 'iEQ', 'iEX', 'conv'))
    for x in rows:
        if x.get('por'):
            print('%-5s %-24s %-5s %-11s %5d %5d %5d %5d  %-11s%s' % (x['ticker'], x['report_id'], x['form'], x['por'],
                  x['dur_end_eq_por'], x['dur_end_eq_por_plus1'], x['inst_eq_por'], x['inst_eq_por_plus1'], x['convention'],
                  ' [5253]' if x.get('is_5253') else ''))
        else:
            print('%-5s %-24s %-5s NULL_POR' % (x['ticker'], x['report_id'], x['form']))
    print('WROTE', a.rundir + '/period_convention_proof.json')


if __name__ == '__main__':
    main()
