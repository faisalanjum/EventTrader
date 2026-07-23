"""PHASE-4 dry-run LAW PINS (RED-first per FinalPlan §12).

Five laws the chronological replay engine must obey BEFORE it runs on real data:
  1. the strict public-time clock REFUSES an out-of-order stream (the §12 order attack);
  2. a retry transition is only legal when the awaited source arrives STRICTLY LATER
     than the park origin (PIT §7 — the future never rescues the past);
  3. the leakage sweep CATCHES a ledger row citing a source published after the row's
     own event time (no future evidence, mechanically proven);
  4. the residual chunk law: 0 chars -> 0 chunks, else ceil(chars / 100_000) with the
     REAL batch cap (batch_groups.py:14-15 via m4_reader_residual, verified there);
  5. a manifest row is SOURCE-LOCAL: it carries exactly its own source_id + sha256 of
     its own bytes, nothing else.

    venv/bin/python -m pytest scripts/driver_seed/relocate_probe/phase4/test_p4_dry_run.py -q
"""
import hashlib
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import p4_dry_run as P4


def _ev(t, sid, kind='8k', ticker='AA'):
    return {'t': t, 'kind': kind, 'ticker': ticker, 'source_id': sid}


def test_pit_order_attack_refused():
    good = [_ev('2023-01-01T10:00:00-05:00', 'a'), _ev('2023-02-01T10:00:00-05:00', 'b')]
    P4.check_order(good)                        # in-order stream passes
    attack = list(reversed(good))               # the §12 order attack
    with pytest.raises(P4.PITOrderError):
        P4.check_order(attack)


def test_pit_equal_timestamps_allowed():
    same = [_ev('2023-01-01T10:00:00-05:00', 'a'), _ev('2023-01-01T10:00:00-05:00', 'b')]
    P4.check_order(same)                        # simultaneous publication is not a regression


def test_retry_transition_requires_strictly_later_arrival():
    park = {'item_id': 'x', 'ticker': 'AA', 'form': '10-K', 'period_end': '2025-12-31'}
    origin_t = '2026-01-15T16:00:00-05:00'
    early = _ev('2026-01-15T16:00:00-05:00', 'p1', kind='periodic')
    early.update({'form': '10-K', 'period': '2025-12-31'})
    with pytest.raises(P4.PITOrderError):
        P4.retry_transition(park, early, origin_t)      # not strictly later -> refused
    late = _ev('2026-02-20T09:00:00-05:00', 'p2', kind='periodic')
    late.update({'form': '10-K', 'period': '2025-12-31'})
    tr = P4.retry_transition(park, late, origin_t)
    assert tr and tr['item_id'] == 'x' and tr['arrived_at'] == late['t']
    other = dict(late, ticker='ABT')
    assert P4.retry_transition(park, other, origin_t) is None   # wrong company -> no transition


def test_leakage_sweep_catches_future_reference():
    times = {'s1': '2023-01-01T10:00:00-05:00', 's2': '2024-01-01T10:00:00-05:00'}
    clean = [{'t': times['s1'], 'source_id': 's1', 'evidence_source_ids': ['s1']},
             {'t': times['s2'], 'source_id': 's2', 'evidence_source_ids': ['s2']}]
    assert P4.leakage_sweep(clean, times) == []
    dirty = [{'t': times['s1'], 'source_id': 's1', 'evidence_source_ids': ['s1', 's2']}]
    viol = P4.leakage_sweep(dirty, times)
    assert len(viol) == 1 and viol[0]['cited'] == 's2'


def test_residual_chunk_law():
    assert P4.chunk_law(0) == 0
    assert P4.chunk_law(1) == 1
    assert P4.chunk_law(100_000) == 1
    assert P4.chunk_law(100_001) == 2


def test_manifest_row_is_source_local(tmp_path):
    p = tmp_path / 'ex.htm'
    body = b'<html><body><p>Revenue was $1,234 million.</p></body></html>'
    p.write_bytes(body)
    row = P4.manifest_8k_file('ACC-1', str(p))
    assert row['source_id'] == 'ACC-1'
    assert row['sha256'] == hashlib.sha256(body).hexdigest()
    assert row['evidence_source_ids'] == ['ACC-1']
    assert row['prose_struct_numeric_blocks'] == 1


# ---- corrective round (reviewer Phase-4 audit): REAL-DATA pins, RED-first ----

_REPORT = os.path.join(_HERE, 'p4_dry_run_report.json')


def _report():
    import json
    return json.load(open(_REPORT))


def test_asof_excludes_future_8k_real_data():
    """PIT cutoff on the EXISTING selector: replaying AA's Feb-2026 10-K arrival must
    not see the April-2026 8-K; without as_of the April 8-K IS enumerated (the gap)."""
    sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..')))
    import run_code_tier as RC
    from m1_canonical_selector import _driver
    drv = _driver()
    APRIL, FEB_10K = '0001193125-26-159018', '0001193125-26-077167'
    AS_OF = '2026-02-26T16:52:29-05:00'
    with drv.session() as s:
        _e, _u, audit = RC.fetch_earnings_8ks(s, 'AA', FEB_10K, as_of=AS_OF)
        accs = {a['acc'] for a in audit if a.get('verdict') != 'excluded_after_as_of'}
        assert APRIL not in accs
        assert all(a['created'] <= AS_OF for a in audit
                   if a.get('verdict') != 'excluded_after_as_of')
        _e2, _u2, audit2 = RC.fetch_earnings_8ks(s, 'AA', FEB_10K)
        assert APRIL in {a['acc'] for a in audit2}      # without as_of the gap is real
    drv.close()


def test_timing_inversions_recorded_real_data():
    """The report must record REAL publication order: 5 paired periodics published
    before their 8-K (3 genuine same-day inversions + 2 stale live-only pairings)."""
    pt = _report()['pair_timing']
    inv = [p for p in pt if p['inverted']]
    assert len(inv) == 5
    assert sum(1 for p in inv if p['stale_live_pairing']) == 2
    assert {p['ticker'] for p in inv} == {'AA', 'ABT', 'ADM', 'AFL'}


def test_complete_8k_source_counts_real_data():
    """The 8-K workload must cover ALL parts of the source event (Design law):
    exhibits + stored sections + filing text — graph truth for the 84 events."""
    res = _report()['actual_reader_residual']
    assert res['8k_sections']['parts'] == 201
    assert res['8k_filing_text']['parts'] == 12
    assert res['8k_exhibits']['files'] == 158


def test_transcript_gap_pinned():
    gaps = _report()['transcript_gaps']
    assert any(g['source_id'] == 'AAL_2024-01-25T08.30'
               and g['prepared_blocks'] == 0 and g['qa_blocks'] == 55 for g in gaps)


def test_retry_final_outcomes_real():
    """The two parked items must have REAL retry outcomes (not mere eligibility),
    produced by the actual code tier under the as_of cutoff."""
    fin = {t['item_id']: t for t in _report()['retry']['final_dispositions']}
    tr = {t['item_id']: t for t in _report()['retry']['transitions']}
    ARRIVALS = {'16daa97aa02e': '0001193125-26-077167',    # AA FY2025 10-K
                '5f652af46cf7': '0001628280-26-010185'}    # ABT FY2025 10-K
    for iid, acc in ARRIVALS.items():
        assert fin[iid]['disposition'] == 'value_absent_complete'
        assert fin[iid]['real_retry'] is True
        assert tr[iid]['arrival_source'] == acc
        assert tr[iid]['filing_searched'] == acc


def test_hash_manifest_deterministic():
    """Transcript/8-K manifest hashes are derived from sha-sorted exact-source part
    hashes — order-independent and recomputable from the ledger itself."""
    import json, hashlib
    led = [json.loads(l) for l in
           open(os.path.join(_HERE, 'p4_event_ledger.jsonl'))]
    tr = next(r for r in led if r['kind'] == 'transcript' and r.get('part_shas'))
    assert tr['part_shas'] == sorted(tr['part_shas'])
    assert tr['sha256'] == hashlib.sha256(
        '\n'.join(tr['part_shas']).encode()).hexdigest()
    ek = next(r for r in led if r['kind'] == '8k')
    manifest = sorted([e['sha256'] for e in ek['exhibits']]
                      + [p['sha256'] for p in ek['parts']])
    assert ek['sha256'] == hashlib.sha256(
        '\n'.join(manifest).encode()).hexdigest()


def test_candidate_forms_exclude_padded_percent():
    """The 3-ACI-case fix (RED-pinned): padded percentage companions ('21.0' for 21,
    '0.50'/'0.500' for 0.5) serve STRICT verification only — the CAPPED reader-
    candidate scan must not be expanded by them (they pulled an unrelated tax table
    ahead of the true 'Digital Sales increased 21%' passage). Items: a2d445ea7168,
    ef477ec33ea3, ff1b97121b05 (ACI, values 21 and 2)."""
    sys.path.insert(0, os.path.abspath(
        os.path.join(_HERE, '..', '..', '..', '..', 'driver', 'relocation')))
    import locator as L
    assert L._tableforms(21, '%', padded=False) == {'21'}
    assert L._tableforms(2, '%', padded=False) == {'2'}
    frac = L._tableforms(0.5, '%', padded=False)
    assert '0.5' in frac and '.5' in frac
    assert '0.50' not in frac and '0.500' not in frac
    full = L._tableforms(21, '%')
    assert '21.0' in full                  # strict verification keeps the padded family


def test_passage_search_padded_percent_end_to_end():
    """His round-4 order: prove it at the ACTUAL passage-search level, not just the
    form helper. (1) the true 'Digital sales increased 21 %' passage is retained as
    a candidate; (2) the unrelated tax-table 21.0 % text contributes NO candidate;
    (3) STRICT verification still accepts a labeled padded 21.0 % print."""
    sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..')))
    import link_lib as LL
    tax = ("The effective income tax rate was 21.0 % for fiscal 2024 compared "
           "with 22.5 % in the prior year.")
    good = "Digital sales increased 21 % during fiscal 2024."
    strict, snips, _ctx = LL.scan_text([tax, good], 'Digital Sales', 21, '%',
                                       with_context=True)
    assert any('Digital sales increased 21' in s for s in snips)   # retained
    assert all('tax rate' not in s for s in snips)                 # excluded
    padded = "Digital sales increased 21.0 % during fiscal 2024."
    strict2, _snips2, _c2 = LL.scan_text([padded], 'Digital Sales', 21, '%',
                                         with_context=True)
    assert strict2 and '21.0' in strict2                # strict keeps the padded family
