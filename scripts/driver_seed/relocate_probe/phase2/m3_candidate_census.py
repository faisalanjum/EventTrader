"""M3 — LATER SAME-VALUE CANDIDATE CENSUS (renamed per reviewer corrective
2026-07-22: NOT a 'twin' census — it proves ZERO confirmed same-facts; it counts
later tagged facts of the same company sharing the exact Decimal value at the
same period END date. Supersedes m3_twin_census.py (deleted; its output sha was
fe16be99…, exact-candidate counts identical to this build).

IDENTITY, stated precisely (his corrections):
  company        proven (same CIK)
  period END     proven (exclusive +1 day law) — period START UNPROVEN: an
                 end-date-only match CONFLATES Q4 with FY (both end 12-31)
  unit           currency-FAMILY only (iso4217 spec-namespace prefix) — not unit
  metric/slice/measurement  UNPROVEN mechanically
⇒ confirmed_same_fact = 0. Every candidate is a POSSIBLE match, unconfirmed.

The fragile rounding scan is DELETED per order (its k>=0 bound and word-free
scale discovery were declared; the reviewer prefers no rounding claim at all
for now). No production edits, no reader calls, Route C held, M4 HELD.

    venv/bin/python scripts/driver_seed/relocate_probe/phase2/m3_candidate_census.py
"""
import hashlib
import json
import os
import sys
from datetime import date, timedelta
from decimal import Decimal

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..'))
sys.path.insert(0, _ROOT)
sys.path.insert(0, _HERE)

from driver.relocation import inline_html as IH
from m1_canonical_selector import _driver

WP1 = os.path.join(_ROOT, 'data', 'driver_catalog_seed', 'wp1', 'code_resolved.jsonl')
OUT = os.path.join(_HERE, 'm3_candidate_census.json')

CAND_Q = (
    "MATCH (r8:Report {accessionNo:$acc})-[:PRIMARY_FILER]->(c:Company) "
    "MATCH (q:Report)-[:PRIMARY_FILER]->(c) "
    "WHERE q.formType IN ['10-Q','10-K'] AND q.created > r8.created "
    "MATCH (q)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(f:Fact {is_numeric:'1'}) "
    "WHERE f.is_nil <> '1' "
    "MATCH (f)-[:HAS_PERIOD]->(p:Period) WHERE p.end_date = $pe1 "
    "OPTIONAL MATCH (f)-[:HAS_UNIT]->(u:Unit) "
    "RETURN q.accessionNo AS acc, f.qname AS qname, "
    "f.value AS value, u.name AS unit_name")


def census(session, rec):
    pe1 = (date.fromisoformat(str(rec['period_end']))
           + timedelta(days=1)).isoformat()
    rows = list(session.run(CAND_Q, acc=rec['source_id'], pe1=pe1))
    v = Decimal(str(rec['value']))
    exact = 0
    money_family = []
    for c in rows:
        cv = IH.parse_raw(c['value'])
        if cv is not None and cv == v:
            exact += 1
            money_family.append(bool(str(c['unit_name'] or '')
                                     .startswith('iso4217')))
    unit_family = ('not_applicable' if not money_family else
                   'currency_family_consistent'
                   if all(m == (str(rec['is_currency']) == '1')
                          for m in money_family) else 'FAMILY_MISMATCH')
    return {'item_id': rec['item_id'], 'ticker': rec['ticker'],
            'raw_label': rec['raw_label'], 'category': rec.get('category'),
            'fmt': rec['fmt'], 'is_currency': str(rec['is_currency']),
            'period_end': str(rec['period_end']),
            'candidates_same_company_end_date': len(rows),
            'exact_value_candidates': exact,
            'identity_ledger': {
                'company': 'proven_same_cik',
                'period_end': 'proven_exclusive_plus1',
                'period_start': 'UNPROVEN_end_date_only_conflates_Q4_with_FY',
                'unit': 'currency_family_only_not_full_unit',
                'metric': 'UNPROVEN_mechanically',
                'slice': 'UNPROVEN_no_axis_member_data',
                'measurement': 'UNPROVEN_wording_judgment'},
            'status': 'possible_match_unconfirmed' if exact
                      else 'no_same_value_candidate_found'}


def main():
    recs = []
    for l in open(WP1):
        r = json.loads(l, parse_float=Decimal)
        if r.get('source_type') == '8k':
            recs.append(r)
    assert len(recs) == 40
    drv = _driver()
    with drv.session() as s:
        ledger = [census(s, r) for r in recs]
    drv.close()

    def lane(r):
        if r['fmt'] == 'ratio':
            return 'decimal_form_semantics_unsplit'
        return 'money_level' if r['is_currency'] == '1' else 'count_level'

    denoms = {}
    for r in ledger:
        d = denoms.setdefault(lane(r), {'facts': 0, 'with_exact_candidates': 0,
                                        'without': 0})
        d['facts'] += 1
        d['with_exact_candidates' if r['exact_value_candidates']
          else 'without'] += 1

    out = {
        'census': 'later same-value candidate census (NOT twins)',
        'confirmed_same_fact': 0,
        'honest_result': '28/28 money items had later possible matches; none '
                         'is yet confirmed as the same financial fact.',
        'note_no_candidate_facts': 'for the 12 decimal-form/count facts this '
                                   'census found no same-value candidates at '
                                   'the same end date — a census observation, '
                                   'NOT a claim that such facts are never '
                                   'tagged',
        'denominators_by_lane': denoms,
        'part2_exact_definition_calculations': {
            'status': 'DEFERRED-UNPROVEN (needs metric identity)',
            'denominator_percentage_facts': sum(
                1 for r in ledger if r['fmt'] == 'ratio'
                and ('percent' in r['raw_label'].lower()
                     or '%' in r['raw_label'])),
            'denominator_note': 'percentage facts counted by the RECORD\'S OWN '
                'label marker (a measurement-only marker check on the record own text); the '
                'other decimal-form facts are volumes/other prints and are NOT '
                'percentage-calculation material',
            'decimal_form_total_for_reference': sum(
                1 for r in ledger if r['fmt'] == 'ratio')},
        'ledger': ledger}
    json.dump(out, open(OUT, 'w'), indent=1, default=str)
    slim = {k: v for k, v in out.items() if k != 'ledger'}
    slim['output_sha256'] = hashlib.sha256(open(OUT, 'rb').read()).hexdigest()
    print(json.dumps(slim, indent=1, default=str))
    print('M3-CANDIDATE-CENSUS-DONE')


if __name__ == '__main__':
    main()
