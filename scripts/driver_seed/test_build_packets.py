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
    """A stray decomposition field must NOT reach the item; unit HINTS must; concept/member -> xbrl only."""
    r = rec('ACC-1', '10k', 'AAA', 'revenue', 5000, proposed_name='revenue', slice='product:iphone',
            measurement_spans=['adjusted'], fiscal_quarter='Q4', concept='us-gaap:Revenues', member='IPhone',
            xbrl={'concept': 'us-gaap:Revenues', 'axis_members': [['a', 'm']], 'period_start': 's',
                  'period_end': 'e', 'ptype': 'duration'})
    packets, _, _ = BP.build([r], [], {'AAA': 12})
    item = packets[0]['items'][0]
    for banned in ('proposed_name', 'slice', 'measurement_spans', 'fiscal_quarter', 'series_unit', 'id',
                   'concept', 'member'):                    # concept/member live in xbrl only, not top-level
        assert banned not in item, f"leaked into item: {banned}"
    assert item['xbrl']['concept'] == 'us-gaap:Revenues', 'raw xbrl concept must survive inside the block'
    for h in ('level_unit_raw', 'level_unit_kind_hint', 'level_money_mode_hint', 'level_shape_hint'):
        assert h in item, f"missing unit hint {h}"
    assert item['level_unit_kind_hint'] == 'money' and item['level_shape_hint'] == 'point', item
    print("[ok] no decomposition leak · unit hints present · concept/member only inside xbrl")


def test_money_mode_hint_is_null_off_the_money_lane():
    """UNIT-04: 'money kind requires money_mode (aggregate|price_like|unknown), NULL OTHERWISE.'
    Emitting 'aggregate' on a percent/count asserts a money property about a non-money number."""
    assert BP.unit_hints('%', 0)['level_money_mode_hint'] is None
    assert BP.unit_hints(None, 0)['level_money_mode_hint'] is None
    assert BP.unit_hints('number', 1)['level_money_mode_hint'] == 'aggregate'   # money keeps it


def test_ratio_fmt_is_never_guessed_as_a_count():
    """fiscal.ai has a FOURTH fmt the map never knew: 'ratio' (2,567 of 73,267 worklist rows, e.g.
    'Bauxite Production (mdmt)' = 38.3). It fell to the else-branch and was silently hinted 'count'.
    A hint must never be a guess — emit 'unknown' and let the shared resolver decide."""
    h = BP.unit_hints('ratio', 0)
    assert h['level_unit_kind_hint'] == 'unknown', h
    assert h['level_unit_raw'] == 'unknown', h
    assert BP.unit_hints('number', 0)['level_unit_kind_hint'] == 'count'        # a real count still counts


def test_currency_marked_ratio_is_not_guessed_as_money():
    """#6: 543 worklist rows are fmt='ratio' + is_currency=1. A ratio is ambiguous ($-per-X / dimensionless),
    so it must NOT be hinted aggregate money — the shared resolver decides from the concept/quote."""
    h = BP.unit_hints('ratio', 1)
    assert h['level_unit_kind_hint'] == 'unknown', h
    assert h['level_money_mode_hint'] is None, h


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
