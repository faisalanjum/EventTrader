#!/usr/bin/env python3
"""S1.1 self-check: FETCH provenance + XBRL context + abstain routing. No Neo4j (synthetic sources).

    venv/bin/python scripts/driver_seed/test_run_code_tier.py
"""
import os, sys, json
import pytest
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
    located proof ABSTAINS (value_absent, retryable), NEVER a terminal magnitude skip.
    WP1 update: a stated '0' in generic text does NOT resolve (label-adjacency guards precision) but
    now legitimately becomes a READER CANDIDATE (residual) — the gray zone belongs to the reader lane
    (owner F2). Truly unstated values still abstain cleanly."""
    filing = {'source_id': 'F', 'source_type': '10k', 'event_time': 't', 'xbrls': [],
              'texts': ['revenue grew strongly; nothing here was 0 and no store count is stated']}
    _, res, ab = RC.process_cp([mk_item('Total Fee Related Earnings', 0),   # a 0 IS in the text ->
                                mk_item('Other Revenue', -1000),            #   residual, not resolved
                                mk_item('Big Revenue', 7777)], filing, [])  # unstated -> abstain
    assert not any(a.get('reason') == 'plug' for a in ab), ab               # the magnitude skip is gone
    assert all(a['reason'] == 'value_absent' for a in ab), ab               # unstated -> honest abstain
    assert {a['raw_label'] for a in ab} == {'Other Revenue', 'Big Revenue'}, ab
    assert len(res) == 1 and res[0]['kpi'] == 'Total Fee Related Earnings', res
    assert res[0]['candidates'], res                # the stated '0' rides to the reader, unresolved
    for a in ab:
        assert a['sources_searched'] == ['10k'], a   # completeness signal still carried
    print("[ok] no magnitude plug skip; unproven values abstain; stated-0 -> reader candidate")


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


def test_8k_gate_target_identity():
    """Round-13 fix (reviewer-confirmed, live-reproduced): the join compares the resolver's label
    against the TARGET filing's OWN declared XBRL identity — never period_to_fiscal math.
    fiscal_math.py itself documents ACI/AAP as unfixable edge cases; live ACI 2025-02-22 ACCEPTED
    the future Q4_FY2025 8-K (0001646972-26-000028, 23 leaked candidates) and REJECTED the true
    Q4_FY2024 one (-25-000040). Both sides of the new equality live in the company's own
    XBRL-convention space, so year-numbering conventions can never disagree."""
    lbl = {'safety_action': 'AUTO_OK', 'quarter_label': 'Q4_FY2024'}
    assert RC._8k_gate(lbl, (2024, 4)) == 'accept'
    assert RC._8k_gate({'safety_action': 'AUTO_OK', 'quarter_label': 'Q4_FY2025'},
                       (2024, 4)) == 'other_period'      # the ACI future-8-K case
    assert RC._8k_gate({'safety_action': 'AUTO_OK', 'quarter_label': 'Q3_FY2024'},
                       (2024, 4)) == 'other_period'
    assert RC._8k_gate(lbl, None) == 'uncertain'         # target identity unproven -> fail closed
    assert RC._8k_gate({'safety_action': 'FAIL_CLOSED', 'quarter_label': 'Q4_FY2024'},
                       (2024, 4)) == 'uncertain'
    assert RC._8k_gate({'safety_action': 'AUTO_OK', 'quarter_label': None}, (2024, 4)) == 'uncertain'
    assert RC._8k_gate({}, (2024, 4)) == 'uncertain'
    assert RC._8k_gate(None, (2024, 4)) == 'uncertain'
    print("[ok] 8-K gate: target-XBRL-identity join, convention-safe, fail-closed")


def test_uncertain_only_when_period_relevant():
    """Round-13: an unlabelable 8-K FILED BEFORE the period ended cannot be its announcer (the
    results do not exist yet) — pure impossibility, no windows. One unresolved HISTORICAL 8-K must
    no longer mark every later period incomplete."""
    assert not RC._uncertain_relevant('2023-01-10T21:05:00Z', '2025-02-22')
    assert RC._uncertain_relevant('2025-07-15T20:10:00Z', '2025-02-22')
    assert RC._uncertain_relevant('2025-02-22T09:00:00Z', '2025-02-22')   # same-day: conservative
    print("[ok] uncertainty is period-relevant (created >= period_end only)")


def test_worklist_dedupe_collapses_identical_rows():
    """Round-13: fiscal.ai repeats byte-identical rows (BX 'Total Distributable Earnings' under two
    segment groupings — 18 groups / 31 extra occurrences in the full sheet). Identical rows are ONE
    fact: collapse at load; duplicates share one whole-row id by construction."""
    r1 = {'ticker': 'BX', 'kpi': 'Total Distributable Earnings', 'value': 1, 'period': '2024-12-31'}
    r2 = {'ticker': 'BX', 'kpi': 'Other', 'value': 2, 'period': '2024-12-31'}
    out, dropped = RC.dedupe_rows([r1, dict(r1), r2])
    assert out == [r1, r2] and dropped == 1, (out, dropped)
    assert RC._iid(out[0]) == RC._iid(dict(r1))
    print("[ok] identical raw rows collapse at load; one id per distinct fact")


def test_invalid_vendor_value_parks_not_skips():
    """Round-13: a malformed vendor number must surface as a VISIBLE park (channel data defect),
    never crash and never fall into value_absent/terminal skip."""
    filing = {'source_id': 'F1', 'source_type': '10k', 'xbrls': [], 'texts': ['x'], 'event_time': 't'}
    it = mk_item('Some Revenue Metric', 'N/A')
    res, rem, ab = RC.process_cp([it], filing, [])
    assert not res and not rem and len(ab) == 1, (res, rem, ab)
    assert ab[0]['status'] == 'park' and ab[0]['reason'] == 'invalid_value', ab[0]
    print("[ok] malformed vendor value -> visible PARK, never a crash or terminal skip")


def test_8k_selection_live_aci_aapl():
    """LIVE round-13 regression (reviewer directive): ACI 2025-02-22 must accept the true
    Q4_FY2024 8-K and reject the future -26-000028; AAPL's 52/53-week acceptance must survive.
    Skips ONLY on genuine graph unavailability (probe policy) — assertion failures always FAIL."""
    try:
        RC.load_env_neo4j()
        from neo4j import GraphDatabase
        from neo4j.exceptions import ServiceUnavailable
        drv = GraphDatabase.driver(os.environ['NEO4J_URI'],
                                   auth=(os.environ.get('NEO4J_USERNAME', 'neo4j'),
                                         os.environ['NEO4J_PASSWORD']))
        with drv.session() as s:
            tfq = RC.target_fiscal_identity(s, '0001646972-25-000052')   # ACI 10-K 2025-02-22
    except (KeyError, OSError, Exception) as e:
        if type(e).__name__ in ('ServiceUnavailable', 'KeyError', 'OSError', 'ConnectionError',
                                'AuthError', 'ConfigurationError'):
            pytest.skip(f"graph unavailable: {e}")
        raise
    assert tfq == (2024, 4), tfq                          # dei: FY2024 (ACI's own year-of-start)
    with drv.session() as s:
        events, uncertain, audit = RC.fetch_earnings_8ks(s, 'ACI', '2025-02-22', tfq)
        got = {e['source_id'] for e in events}
        assert '0001646972-25-000040' in got, got         # the TRUE announcer, recovered
        assert '0001646972-26-000028' not in got, got     # the FUTURE 8-K stays out
        by = {a['acc']: a for a in audit}
        assert by['0001646972-26-000028']['verdict'] == 'other_period', by['0001646972-26-000028']
        old = by['0001646972-23-000010']                  # unlabelable 8-K from 2023
        assert old['verdict'] == 'uncertain' and not old['relevant'], old
        assert uncertain == sum(1 for a in audit
                                if a['verdict'] in ('uncertain', 'resolver_error') and a['relevant'])
        tfq_aapl = RC.target_fiscal_identity(s, '0000320193-24-000123')   # AAPL 10-K 2024-09-28
        assert tfq_aapl == (2024, 4), tfq_aapl
        ev2, _, _ = RC.fetch_earnings_8ks(s, 'AAPL', '2024-09-28', tfq_aapl)
        got2 = [e['source_id'] for e in ev2]
        assert got2 == ['0000320193-24-000120'], got2   # the reviewer-pinned exact selection
    drv.close()
    print("[ok] LIVE: ACI true 8-K accepted + future rejected; AAPL 52/53-week preserved")


def test_corpus_missing_rows_carry_item_id():
    """Round-12: EVERY raw row yields an id-carrying outcome — including corpus_missing."""
    it = mk_item('Some Metric', 42)
    row = RC._corpus_missing_row(it)
    assert row['item_id'] == RC._iid(it) and row['reason'] == 'corpus_missing'
    assert row['status'] == 'park'
    print("[ok] corpus_missing rows carry item_id")


def test_sources_incomplete_propagates():
    """A fail-closed (uncertain) 8-K means the expected source set is INCOMPLETE: value-absent
    rows carry sources_incomplete=True so a terminal SKIP stays illegal downstream."""
    filing = {'source_id': 'F', 'source_type': '10k', 'event_time': 't', 'xbrls': [],
              'texts': ['nothing relevant here']}
    _, _, ab1 = RC.process_cp([mk_item('Unfound Metric', 4242)], filing, [], sources_incomplete=True)
    assert ab1 and all(a['sources_incomplete'] is True for a in ab1), ab1
    _, _, ab2 = RC.process_cp([mk_item('Unfound Metric', 4242)], filing, [], sources_incomplete=False)
    assert ab2 and all(a['sources_incomplete'] is False for a in ab2), ab2
    print("[ok] sources_incomplete propagates to value-absent abstains")


def test_item_id_unique_per_distinct_raw_row():
    """Reviewer catch, CONFIRMED on the wp1 cohort (26 collision groups): fiscal.ai repeats a KPI
    label across category variants (geo1 vs geo2) with different values — an id over
    (ticker,kpi,period,form) alone conflates distinct raw rows. The id must hash the WHOLE row."""
    a = mk_item('Other Revenue by Geography', 23000)
    b = mk_item('Other Revenue by Geography', 45029043000)
    a['category'] = 'Revenue by Geography geo1'
    b['category'] = 'Revenue by Geography geo2'
    assert RC._iid(a) != RC._iid(b), "distinct raw rows shared one item_id"
    assert RC._iid(a) == RC._iid(dict(a)), "id must be deterministic"
    print("[ok] item_id unique per distinct raw row")


def test_item_id_traceability():
    """WP1: ONE deterministic item_id rides through resolved, residual, and abstain."""
    filing = {'source_id': 'F', 'source_type': '10k', 'event_time': 't', 'xbrls': [],
              'texts': ['Total revenue $ 5,432 for the year. mystery metric maybe 777 unclear']}
    it_res = mk_item('revenue', 5432)
    it_abs = mk_item('Unstated Thing', 90210)
    resolved, residual, abstain = RC.process_cp([it_res, it_abs], filing, [])
    assert resolved and resolved[0]['item_id'] == RC._iid(it_res), resolved
    assert abstain and abstain[0]['item_id'] == RC._iid(it_abs), abstain
    assert RC._iid(it_res) != RC._iid(it_abs)
    for r in residual:
        assert r['item_id'], r
    print("[ok] item_id carried through all three paths")


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
