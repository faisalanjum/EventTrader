#!/usr/bin/env python3
"""S1.2 + S1.3 self-check: packet grouping + envelope + no-decomposition-leak + PARK/SKIP routing.

    venv/bin/python scripts/driver_seed/test_build_packets.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import build_packets as BP


def rec(sid, stype, tk, label, val, **extra):
    r = {'source_id': sid, 'source_type': stype, 'ticker': tk, 'event_time': 't', 'raw_label': label,
         'value': val, 'fmt': 'number', 'is_currency': 1, 'period_end': '2024-12-31', 'cadence': 'Annual',
         'quote': f'{label} $ {val}', 'period_evidence': '', 'tier': 'T2-label', 'quote_source': 'section'}
    r.update(extra); return r


def test_grouping_and_envelope():
    recs = [rec('ACC-1', '10q', 'AAA', 'revenue', 5000),
            rec('ACC-1', '10q', 'AAA', 'operating income', 900),   # same event -> same packet
            rec('ACC-2', '8k', 'AAA', 'revenue', 5000)]            # different event -> own packet
    packets, _, _ = BP.build(recs, [], {'AAA': 9})
    assert len(packets) == 2, packets
    p1 = [p for p in packets if p['source_id'] == 'ACC-1'][0]
    assert len(p1['items']) == 2 and p1['fye_month'] == 9 and p1['ticker'] == 'AAA', p1
    assert {p['source_type'] for p in packets} == {'10q', '8k'}
    print("[ok] one packet per source event; envelope correct")


def test_no_decomposition_leak():
    """A stray decomposition field on a record must NOT reach the packet item."""
    r = rec('ACC-1', '10k', 'AAA', 'revenue', 5000, proposed_name='revenue', slice='product:iphone',
            measurement_spans=['adjusted'], fiscal_quarter='Q4')
    packets, _, _ = BP.build([r], [], {'AAA': 12})
    item = packets[0]['items'][0]
    for banned in ('proposed_name', 'slice', 'measurement_spans', 'fiscal_quarter', 'series_unit', 'id'):
        assert banned not in item, f"decomposition field leaked: {banned}"
    assert item['raw_label'] == 'revenue' and item['tier'] == 'T2-label'
    print("[ok] no decomposition field leaks into the packet")


def test_canonicalize():
    packets, _, _ = BP.build([rec('AC:C:1', '10k', 'AAA', 'revenue', 5000)], [], {'AAA': 12})
    assert packets[0]['source_id'] == 'AC_C_1', packets[0]['source_id']
    print("[ok] source_id canonicalized ':' -> '_'")


def test_park_skip_routing():
    ab = [
        {'ticker': 'AAA', 'kpi': 'Rev % Chg.', 'status': 'skip', 'reason': 'derived_metric', 'form': '10-K'},
        {'ticker': 'AAA', 'kpi': 'Small', 'status': 'skip', 'reason': 'plug', 'form': '10-K'},
        {'ticker': 'AAA', 'kpi': 'Late', 'status': 'park', 'reason': 'corpus_missing', 'form': '10-K'},
        # value absent but the WHOLE expected set (10-K + 8-K) was searched -> terminal skip
        {'ticker': 'AAA', 'raw_label': 'Rev', 'status': 'value_absent', 'reason': 'value_absent',
         'form': '10-K', 'sources_searched': ['10k', '8k']},
        # value absent but 8-K was NOT searched -> corpus incomplete -> PARK, not skip
        {'ticker': 'AAA', 'raw_label': 'Rev', 'status': 'value_absent', 'reason': 'value_absent',
         'form': '10-K', 'sources_searched': ['10k']},
    ]
    _, skip, park = BP.build([], ab, {})
    sr = sorted(x['reason'] for x in skip); pr = sorted(x['reason'] for x in park)
    assert sr == ['derived_metric', 'plug', 'value_absent_complete'], sr
    assert pr == ['corpus_incomplete', 'corpus_missing'], pr
    print("[ok] PARK/SKIP routing:", 'skip=', sr, 'park=', pr)


if __name__ == '__main__':
    test_grouping_and_envelope()
    test_no_decomposition_leak()
    test_canonicalize()
    test_park_skip_routing()
    print("\nALL S1.2 + S1.3 CHECKS PASS")
