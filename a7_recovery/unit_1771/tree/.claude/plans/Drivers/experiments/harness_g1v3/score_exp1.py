#!/usr/bin/env python3
"""EXP-1 gate (READ-ONLY files, 0 LLM). Gate = determinism_shas_equal && field_match_rate==1.0 &&
unclassified_windows==0 && pit_menu_proof.pass && len(ambiguity_register_open)==0. Writes scores.json + decision.json."""
import json, argparse, collections
VALID_SCOPES = {'quarter', 'ytd', 'half', 'annual', 'ttm', 'monthly', 'exact_range', 'null'}


def load(p, d=None):
    try:
        return json.load(open(p))
    except Exception:
        return d


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--rundir', required=True); ap.add_argument('--base', required=True); a = ap.parse_args()
    RD, BASE = a.rundir, a.base
    det = load(RD + '/determinism.json', {})
    xxl0 = load(RD + '/xxl0_report.json', {})
    pit = load(RD + '/pit_menu_proof.json', {})
    reg = load(BASE + '/exp1_xbrl/ambiguity_register.json', {})
    rows = [json.loads(l) for l in open(RD + '/materialized.jsonl')]
    scopes = collections.Counter(r['period']['period_scope'] for r in rows)
    unclassified = sum(v for k, v in scopes.items() if k not in VALID_SCOPES)
    open_amb = len(reg.get('entries_open', []))
    g_det = bool(det.get('equal'))
    g_fmr = (xxl0.get('field_match_rate') == 1.0)
    g_unc = (unclassified == 0)
    g_pit = bool(pit.get('pass'))
    g_amb = (open_amb == 0)
    gate = g_det and g_fmr and g_unc and g_pit and g_amb
    criteria = {'determinism': g_det, 'field_match_rate_eq_1': g_fmr, 'unclassified_eq_0': g_unc, 'pit_pass': g_pit, 'open_ambiguities_eq_0': g_amb}
    scores = {'exp_id': 'EXP-1', 'run_kind': 'dry-run X-XL0 + census + PIT',
              'gate': {'expr': 'determinism && field_match_rate==1.0 && unclassified_windows==0 && pit_menu_proof && open_ambiguities==0', 'pass': gate},
              'metrics': {'determinism_shas_equal': g_det, 'field_match_rate': xxl0.get('field_match_rate'), 'xxl0_checks': xxl0.get('checks'),
                          'unclassified_windows': unclassified, 'exact_range_WARN': scopes.get('exact_range', 0),
                          'pit_menu_proof_pass': g_pit, 'open_ambiguities': open_amb, 'emitted': len(rows)},
              'period_scopes': dict(scopes), 'criteria': criteria}
    json.dump(scores, open(RD + '/scores.json', 'w'), indent=2, sort_keys=True)
    decision = {'exp_id': 'EXP-1', 'outcome': 'PASS' if gate else 'BLOCKED',
                'blockers': [k for k, v in criteria.items() if not v],
                'note': 'EXP-1 dry-run gate: determinism(x2 sha) + X-XL0 field-match + period unclassified==0 + PIT-menu + no open ambiguities. Resolved pins ra_0002/ra_0004 -> O12 bundle; dual-CIK slices are skip+count by Fable ruling.',
                'fable_signoff': None}
    json.dump(decision, open(RD + '/decision.json', 'w'), indent=2, sort_keys=True)
    print('GATE', 'PASS' if gate else 'BLOCKED')
    print('CRITERIA', json.dumps(criteria, sort_keys=True))
    print('METRICS', json.dumps(scores['metrics'], sort_keys=True))
    if not gate: print('BLOCKERS', decision['blockers'])
    print('WROTE scores.json + decision.json')


if __name__ == '__main__':
    main()
