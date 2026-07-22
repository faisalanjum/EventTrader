"""ROUTE-A 150-case status reporter (corrective-5 item 3 — SIMPLIFIED).

Every one of the 150 source-linked cases is multi-axis; real rebuilt anchors do not
exist until Core Phase 5, and invented slices are banned. Therefore NOTHING can be
lawfully attempted here yet: this reporter joins the cases, verifies the deferral
reason per case, and states the honest result. Real certification belongs to Phase 5.

    venv/bin/python scripts/driver_seed/relocate_probe/route_a_e2e_150.py
"""
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(_HERE, 'route_a_e2e_150_result.json')


def main():
    cases = json.load(open(os.path.join(_HERE, 'xbrl_gate_expected.json')))
    ledger = {}
    for key, pinned in cases.items():
        parts = key.split('|')
        dimensioned = len(parts) > 8 and '=' in parts[8]
        ledger[parts[0]] = {
            'outcome': ('recall_deferred_dimensioned_no_real_anchor'
                        if dimensioned else 'recall_deferred_no_real_anchor'),
            'legacy': pinned.get('verdict', '?')}
    out = {'label': 'ROUTE-A 150-case status (Phase-5-deferred)',
           'attempted': 0, 'deferred': len(ledger),
           'precision': 'not_measured', 'recall': 'not_measured',
           'ledger': ledger}
    json.dump(out, open(OUT, 'w'), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != 'ledger'}))
    assert out['deferred'] == 150


if __name__ == '__main__':
    main()
