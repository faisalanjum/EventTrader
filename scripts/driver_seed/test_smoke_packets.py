#!/usr/bin/env python3
"""S1.4 integration validator: assert the smoke packets obey the frozen Part D contract.

    venv/bin/python scripts/driver_seed/test_smoke_packets.py --tag smoke
"""
import os, sys, json, argparse, collections
sys.path.insert(0, os.path.dirname(__file__))
import link_lib as L

ENVELOPE = {'source_id', 'source_type', 'ticker', 'fye_month', 'event_time', 'items'}
ITEM_REQ = {'raw_label', 'value', 'fmt', 'quote', 'period_end', 'cadence', 'tier'}
DECOMP_BANNED = {'proposed_name', 'slice', 'slice_tokens', 'measurement_spans', 'measurement',
                 'per_x', 'fiscal_quarter', 'fiscal_year', 'time_type', 'series_unit', 'id', 'fact_scope'}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--tag', default='smoke'); a = ap.parse_args()
    pdir = f'data/driver_catalog_seed/{a.tag}'
    packets = [json.loads(l) for l in open(f'{pdir}/packets.jsonl')]
    assert packets, 'no packets'
    seen_sids, bad_gate = set(), 0
    for p in packets:
        assert ENVELOPE <= set(p), f"envelope missing fields: {ENVELOPE - set(p)}"
        assert p['source_type'] in ('10k', '10q', '8k'), p['source_type']
        assert p['source_id'] and ':' not in p['source_id'], p['source_id']
        assert p['source_id'] not in seen_sids, f"duplicate source event {p['source_id']}"
        seen_sids.add(p['source_id'])
        assert p['fye_month'] is not None and p['items'], p['source_id']
        for it in p['items']:
            assert ITEM_REQ <= set(it), f"item missing {ITEM_REQ - set(it)}"
            leak = DECOMP_BANNED & set(it)
            assert not leak, f"decomposition leak: {leak}"
            # re-assert the deterministic gate: the number really is in the quote
            if not L.value_ok(it['value'], it['fmt'], it['quote']):
                bad_gate += 1
            # 8-K events are text-only -> no xbrl block
            if p['source_type'] == '8k':
                assert 'xbrl' not in it, '8-K item should not carry xbrl context'
    assert bad_gate == 0, f"{bad_gate} items fail value_ok re-assert"

    # a value present in BOTH a filing and a PR must appear as TWO source events (provenance split)
    by_val = collections.defaultdict(set)
    for p in packets:
        for it in p['items']:
            by_val[(p['ticker'], it['raw_label'], str(it['value']), it['period_end'])].add(p['source_type'])
    split = [k for k, s in by_val.items() if len(s) > 1]

    tiers = collections.Counter(it['tier'] for p in packets for it in p['items'])
    print(f"[ok] {len(packets)} packets, {sum(len(p['items']) for p in packets)} items — all envelope+item fields present")
    print(f"[ok] no decomposition leak · value_ok re-holds on every item · source_ids unique & canonical")
    print(f"     tiers={dict(tiers)} · same-value-two-events pairs={len(split)}")

    # eyeball: one filing packet + one PR packet
    for stype in ('10k', '10q', '8k'):
        ex = next((p for p in packets if p['source_type'] == stype), None)
        if ex:
            it = ex['items'][0]
            print(f"\n--- {stype} {ex['source_id']} ({ex['ticker']}, fye_m={ex['fye_month']}, {len(ex['items'])} items)")
            print(f"    raw_label={it['raw_label']!r} value={it['value']} tier={it['tier']} cadence={it['cadence']}")
            print(f"    quote={it['quote'][:110]!r}")
            if 'xbrl' in it:
                print(f"    xbrl: concept={it['xbrl']['concept'].split(':')[-1]} ptype={it['xbrl']['ptype']} "
                      f"period={it['xbrl']['period_start']}..{it['xbrl']['period_end']} axes={it['xbrl']['axis_members']}")
    print("\nS1.4 SMOKE VALIDATION PASS")


if __name__ == '__main__':
    main()
