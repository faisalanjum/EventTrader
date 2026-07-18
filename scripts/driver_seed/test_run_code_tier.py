#!/usr/bin/env python3
"""S1.1 self-check: FETCH provenance + XBRL context + abstain routing. No Neo4j (synthetic sources).

    venv/bin/python scripts/driver_seed/test_run_code_tier.py
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
import run_code_tier as RC, link_lib as L


def mk_item(kpi, val, fmt='number'):
    return {'ticker': 'TST', 'kpi': kpi, 'value': val, 'fmt': fmt, 'is_currency': 1,
            'period': '2024-12-31', 'form': '10-K', 'section': 'Annual', 'category': 'x'}


def test_provenance():
    """A value found only in the filing -> filing accession; only in the PR -> the 8-K accession."""
    filing = {'source_id': 'FILING-ACC', 'source_type': '10k', 'event_time': 't1', 'xbrls': [],
              'texts': ['Total revenue $ 5,432 for the year ended December 31, 2024.']}
    pr = {'source_id': '8K-ACC', 'source_type': '8k', 'event_time': 't0', 'xbrls': [],
          'texts': ['Fourth quarter revenue was $ 9,876 million, up 10%.']}
    resolved, _, _ = RC.process_cp([mk_item('revenue', 5432), mk_item('revenue', 9876)], filing, [pr])
    by = {(r['value'], r['source_type'], r['source_id']) for r in resolved}
    assert (5432, '10k', 'FILING-ACC') in by, by
    assert (9876, '8k', '8K-ACC') in by, by
    for r in resolved:                           # never cross-stamp
        assert r['source_id'] == ('FILING-ACC' if r['source_type'] == '10k' else '8K-ACC'), r
        assert r['cadence'] == 'Annual' and r['raw_label'] == 'revenue'
    print("[ok] provenance:", by)


def test_value_in_both_makes_two_events():
    filing = {'source_id': 'F', 'source_type': '10q', 'event_time': 't1', 'xbrls': [],
              'texts': ['Net revenue $ 4,321 in the quarter.']}
    pr = {'source_id': '8K', 'source_type': '8k', 'event_time': 't0', 'xbrls': [],
          'texts': ['revenue of $ 4,321 for the quarter.']}
    resolved, _, _ = RC.process_cp([mk_item('revenue', 4321)], filing, [pr])
    srcs = sorted(r['source_type'] for r in resolved)
    assert srcs == ['10q', '8k'], srcs        # same value, two source events -> two records
    print("[ok] value in both -> two events:", srcs)


def test_derived_skip():
    filing = {'source_id': 'F', 'source_type': '10k', 'event_time': 't', 'xbrls': [], 'texts': ['x']}
    _, _, ab = RC.process_cp([mk_item('Total Revenue % Chg.', 12.0),
                              mk_item('Segment Revenue Common Size', 40.0)], filing, [])
    assert ab and all(a['status'] == 'skip' and a['reason'] == 'derived_metric' for a in ab), ab
    print("[ok] derived -> terminal SKIP")


def test_no_magnitude_plug_skip__abstain_without_proof():
    """#4: the magnitude 'plug' skip (<=1000) is GONE — it dropped legit small facts (78 'Total X = 0'
    rows, 'International Stores = 86', 'ACPU = 670'). No value is pre-skipped by size; a value with no
    located proof ABSTAINS (value_absent, retryable), NEVER a terminal magnitude skip. A zero in generic
    text is insufficient -> abstains. An unstated small value (fiscal.ai filler) -> abstains."""
    filing = {'source_id': 'F', 'source_type': '10k', 'event_time': 't', 'xbrls': [],
              'texts': ['revenue grew strongly; nothing here was 0 and no store count is stated']}
    _, res, ab = RC.process_cp([mk_item('Total Fee Related Earnings', 0),   # a real 0, not in text
                                mk_item('Other Revenue', -1000),            # fiscal.ai filler, unstated
                                mk_item('Big Revenue', 7777)], filing, [])
    assert not any(a.get('reason') == 'plug' for a in ab), ab               # the magnitude skip is gone
    assert all(a['reason'] == 'value_absent' for a in ab), ab               # all abstain for lack of proof
    assert not res, res                                                     # none produced LLM candidates
    for a in ab:
        assert a['sources_searched'] == ['10k'], a   # completeness signal still carried
    print("[ok] no magnitude plug skip; unproven values abstain")


def test_small_value_reaches_the_locator_not_magnitude_vetoed():
    """#4: a small value is no longer VETOED by size before the locator runs. Whether it then resolves
    depends on locatable printed proof (exact_cell on real HTML, measured at the regenerate) — but it must
    never be a terminal magnitude 'plug' skip. Here, with no proof, it ABSTAINS (value_absent, retryable)."""
    filing = {'source_id': 'F', 'source_type': '10k', 'event_time': 't', 'xbrls': [],
              'texts': ['International stores were up nicely this year']}
    _, _, ab = RC.process_cp([mk_item('International Stores', 86)], filing, [])
    assert not any(a.get('reason') == 'plug' for a in ab), ab           # never a magnitude skip
    assert any(a['reason'] == 'value_absent' for a in ab), ab           # abstains (retryable), not terminal
    print("[ok] small value reaches the locator; abstains without proof, never a magnitude skip")


def test_second_source_residual_survives_when_first_resolves(monkeypatch):
    """#2: a source whose value only the LLM could extract must NOT be dropped just because ANOTHER source
    already resolved deterministically. Design (15 D.2): the same value on two sources = two records, and the
    8-K/PR carries EARLIER availability. Old code did `if emitted: continue` -> the PR's candidates vanished.
    Routing is the defect, so drive resolve_one directly."""
    filing = {'source_id': 'F', 'source_type': '10q', 'event_time': 't1', 'xbrls': [], 'texts': ['x']}
    pr = {'source_id': '8K', 'source_type': '8k', 'event_time': 't0', 'xbrls': [], 'texts': ['y']}

    def fake_resolve(it, src, allow_t1):
        if src['source_id'] == 'F':
            return ({'source_id': 'F', 'source_type': '10q', 'value': it['value']}, [])   # filing resolves
        return (None, ['fourth quarter revenue was strong'])                              # PR: snips-only
    monkeypatch.setattr(RC, 'resolve_one', fake_resolve)

    resolved, residual, abstain = RC.process_cp([mk_item('revenue', 4321)], filing, [pr])
    assert len(resolved) == 1 and resolved[0]['source_id'] == 'F', resolved
    # the PR's candidates survive (tagged with their source), even though the filing resolved
    assert any(c['src'] == '8K' for r in residual for c in r['candidates']), f"PR residual dropped: {residual}"
    assert not abstain, abstain
    # and the residual record carries EXACTLY the fields the LLM batcher reads (prep_llm_batches), so the
    # residual -> LLM path can't KeyError
    for k in ('ticker', 'kpi', 'value', 'fmt', 'is_currency', 'period', 'form', 'filing_id', 'candidates'):
        assert k in residual[0], f"residual missing batcher field {k}: {residual[0]}"


def test_xbrl_context():
    fc = {'value': '201183', 'period': {'startDate': '2023-10-01', 'endDate': '2024-09-28'},
          'segment': {'dimension': 'us-gaap:ProductOrServiceAxis', 'value': 'aapl:IPhoneMember'}}
    assert L.seg_axis_members(fc) == [('us-gaap:ProductOrServiceAxis', 'aapl:IPhoneMember')]
    xb = json.dumps({'RevenueFromContractWithCustomerExcludingAssessedTax': [fc]})
    r = L.tier1([xb], 'iphone revenue', 201183, '2024-09-28')
    assert r is not None, 'tier1 should match the synthetic iPhone fact'
    assert r['ptype'] == 'duration' and r['period_start'] == '2023-10-01' and r['period_end'] == '2024-09-28', r
    assert r['axis_members'] == [('us-gaap:ProductOrServiceAxis', 'aapl:IPhoneMember')], r
    print("[ok] xbrl context:", r['axis_members'], r['ptype'], r['period_start'], '->', r['period_end'])


if __name__ == '__main__':
    test_provenance()
    test_value_in_both_makes_two_events()
    test_derived_skip()
    test_no_magnitude_plug_skip__abstain_without_proof()
    test_small_value_reaches_the_locator_not_magnitude_vetoed()
    test_xbrl_context()
    print("\nALL S1.1 CHECKS PASS")
