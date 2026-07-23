"""WP3 COMPLIANT PROOF (2026-07-23) — the smallest current-contract packet.

AUDIT WRAPPER ONLY: every extraction step below is the EXISTING certified machinery
(route_a_source.build_source -> locator.locate on the already-pinned real CE tagged
source -> build_packets.build envelope -> THE shared writer). This file adds zero
extraction logic: it wires, sorts chronologically, demonstrates the prose-abstain
law, and persists. Zero AI tokens; Neo4j READS only.

    venv/bin/python scripts/driver_seed/wp3_compliant_packet.py
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, '..', '..', 'driver', 'relocation'))

import build_packets as BP
import route_a_source as SRC
import locator as LOC

# FIXED source-verified fixture values (accepted Phase-4 ledger forms; NO runtime
# derivation, NO classifier). Unknown accession/form -> fail closed, no packet.
CADENCE_FIXTURE = {
    # STABLE VALUE-BLIND key: (source_id, period_start, period_end) -> series.
    # Cadence is a period-shape property — never keyed by extracted value.
    ('0001306830-24-000155', '2023-01-01', '2023-06-30'): 'Quarterly',
    ('0001306830-24-000155', '2023-04-01', '2023-06-30'): 'Quarterly',
    ('0001306830-24-000155', '2024-01-01', '2024-06-30'): 'Quarterly',
    ('0001306830-24-000155', '2024-04-01', '2024-06-30'): 'Quarterly',
    ('0001646972-23-000045', '2020-03-01', '2021-02-27'): 'Annual',
    ('0001646972-23-000045', '2021-02-28', '2022-02-26'): 'Annual',
    ('0001646972-23-000045', '2022-02-27', '2023-02-25'): 'Annual',
    ('0001646972-23-000056', '2022-02-27', '2022-06-18'): 'Quarterly',
    ('0001646972-23-000056', '2023-02-26', '2023-06-17'): 'Quarterly',
    ('0001646972-24-000165', '2023-02-26', '2023-06-17'): 'Quarterly',
    ('0001646972-24-000165', '2024-02-25', '2024-06-15'): 'Quarterly',
}
ACC = '0001306830-24-000155'                 # the already-pinned real CE 10-Q
ANCHOR = {                                   # the certified suite's pinned anchor
    'source_id': 'SYN-PRIOR', 'company': 'C1', 'driver': 'revenue',
    'slice': 'segment:acetyl_chain', 'measurement': '', 'series_unit': 'm_usd',
    'time_type': 'duration', 'fact_type': 'metric', 'wording': ('North America',),
    'concept_clue': 'RevenueFromContractWithCustomerExcludingAssessedTax',
}
OUT = os.path.join(_HERE, '..', '..', 'data', 'driver_catalog_seed',
                   'wp3_ce_compliant')


def ce_packets():
    s = SRC.build_source(ACC)
    r = LOC.locate(ANCHOR, s)
    assert r['items'], 'pinned CE items not located'
    drv = SRC._driver()
    with drv.session() as ses:
        created = ses.run("MATCH (x:XBRLNode {accessionNo:$a})<-[:HAS_XBRL]-(rep:Report) "
                          "RETURN rep.created AS c", a=ACC).single()['c']
    drv.close()
    recs = [dict(i, source_id=s['source_id'], source_type=s['source_type'],
                 ticker='CE', fmt='number', is_currency=True, tier='T1-xbrl',
                 period_end=i['xbrl']['period_end'], cadence=CADENCE_FIXTURE[(ACC, i['xbrl']['period_start'], i['xbrl']['period_end'])],
                 event_time=str(created)) for i in r['items']]
    packets, _s, _p = BP.build(recs, [], {'CE': 12})
    return packets                                   # ALL returned items, no filter


ACI_ANCHOR = {                                       # ONE fixed value-blind fixture
    'source_id': 'test_fixture', 'company': 'TEST_FIXTURE', 'driver': 'revenue',
    'slice': '', 'measurement': '', 'series_unit': 'm_usd',
    'time_type': 'duration', 'fact_type': 'metric',
    'wording': ('Net sales and other revenue',),
    'concept_clue': 'RevenueFromContractWithCustomerExcludingAssessedTax',
}
P4LED = os.path.join(_HERE, 'relocate_probe', 'phase4', 'p4_event_ledger.jsonl')


def aci_stream():
    import datetime as _dt0
    evs = sorted((json.loads(l) for l in open(P4LED)),
                 key=lambda e: _dt0.datetime.fromisoformat(e['t']))
    packs, ledger = [], []
    for ev in (e for e in evs if e['ticker'] == 'ACI'):
        if ev['kind'] != 'periodic':                 # untagged sources: abstain law
            ledger.append({'event': ev['source_id'], 'kind': ev['kind'],
                           't': ev['t'], 'result': 'no_proven_match',
                           'p4_source_sha': ev['sha256'],
                           'law': 'untagged source; prose abstains (Route E)'})
            continue
        s = SRC.build_source(ev['source_id'])    # adapter now owns the form law
        r = LOC.locate(ACI_ANCHOR, s)
        if r['items']:
            recs = [dict(i, source_id=s['source_id'], source_type=s['source_type'],
                         ticker='ACI', fmt='number', is_currency=True,
                         tier='T1-xbrl',   # tier = FISCAL PROVENANCE only, never Core identity
                         period_end=i['xbrl']['period_end'],
                         cadence=CADENCE_FIXTURE[(ev['source_id'], i['xbrl']['period_start'], i['xbrl']['period_end'])],
                         event_time=ev['t']) for i in r['items']]
            p, _s2, _p2 = BP.build(recs, [], {'ACI': 2})
            packs += p
        else:
            ledger.append({'event': ev['source_id'], 'kind': 'periodic',
                           't': ev['t'], 'result': r['status'],
                           'p4_source_sha': ev['sha256']})
    import datetime as _dt
    packs.sort(key=lambda p: _dt.datetime.fromisoformat(p['event_time']))
    return packs, ledger


def main():
    ce = ce_packets()
    os.makedirs(OUT, exist_ok=True)
    BP.write_jsonl(ce, os.path.join(OUT, 'packets.jsonl'))
    packs, ledger = aci_stream()
    out2 = os.path.join(_HERE, '..', '..', 'data', 'driver_catalog_seed',
                        'wp3_aci_stream')
    os.makedirs(out2, exist_ok=True)
    BP.write_jsonl(packs, os.path.join(out2, 'packets.jsonl'))
    BP.write_jsonl(ledger, os.path.join(out2, 'no_match_ledger.jsonl'))
    print(json.dumps({'ce_items': sum(len(p['items']) for p in ce),
                      'aci_packets': len(packs),
                      'aci_items': sum(len(p['items']) for p in packs),
                      'aci_no_match_events': len(ledger),
                      'total_events': len(packs) + len(ledger)}, indent=1))


if __name__ == '__main__':
    main()
