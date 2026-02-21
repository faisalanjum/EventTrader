#!/usr/bin/env python3
"""
Tests for guidance_writer.py — validates Cypher construction, parameter
assembly, validation gates, dry-run, feature flag, and batch logic.

No Neo4j connection needed — all tests use mock manager.
"""

import sys
sys.path.insert(0, "/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts")
sys.path.insert(0, "/home/faisal/EventMarketDB")

import guidance_writer
from guidance_writer import (
    _validate_item, _build_core_query, _build_params, _build_member_query,
    write_guidance_item, write_guidance_batch, create_guidance_constraints,
    SOURCE_LABEL_MAP,
)


# ── Mock manager ──────────────────────────────────────────────────────────

_UNSET = object()

class MockManager:
    """Minimal mock for Neo4jManager.execute_cypher_query()."""

    def __init__(self, return_value=_UNSET, side_effects=None):
        self.calls = []
        self.return_value = ({'id': 'test', 'was_created': True}
                             if return_value is _UNSET else return_value)
        self.side_effects = side_effects  # list of return values, popped per call

    def execute_cypher_query(self, query, parameters):
        self.calls.append((query, parameters))
        if self.side_effects:
            val = self.side_effects.pop(0)
            if isinstance(val, Exception):
                raise val
            return val
        return self.return_value


# ── Test item builder ─────────────────────────────────────────────────────

def _make_item(**overrides):
    """Build a complete test item dict with sensible defaults."""
    item = {
        'guidance_id': 'guidance:revenue',
        'guidance_update_id': 'gu:test_src:revenue:duration_2025-03-30_2025-06-28:gaap:total:abc123def456ab00',
        'evhash16': 'abc123def456ab00',
        'label_slug': 'revenue',
        'segment_slug': 'total',
        'canonical_unit': 'm_usd',
        'canonical_low': 94.0,
        'canonical_mid': 95.5,
        'canonical_high': 97.0,
        'label': 'Revenue',
        'aliases': ['sales', 'net revenue'],
        'given_date': '2025-01-30',
        'period_type': 'quarter',
        'fiscal_year': 2025,
        'fiscal_quarter': 2,
        'segment': 'Total',
        'unit': 'm_usd',
        'basis_norm': 'gaap',
        'basis_raw': 'as reported',
        'derivation': 'explicit',
        'qualitative': None,
        'quote': 'We expect revenue between $94B and $97B',
        'section': 'CFO Prepared Remarks',
        'source_key': 'full',
        'source_type': 'transcript',
        'conditions': None,
        'xbrl_qname': 'us-gaap:Revenues',
        'member_u_ids': [],
        'period_u_id': 'duration_2025-03-30_2025-06-28',
        'period_node_type': 'duration',
        'start_date': '2025-03-30',
        'end_date': '2025-06-28',
        'ctx_u_id': 'guidance_320193_duration_2025-03-30_2025-06-28',
        'cik': '320193',
        'unit_u_id': 'guidance_unit_m_usd',
    }
    item.update(overrides)
    return item


# ── Validation tests ──────────────────────────────────────────────────────

def test_validate_success():
    ok, err = _validate_item(_make_item(), 'src1', 'transcript')
    assert ok is True
    assert err is None

def test_validate_missing_source_id():
    ok, err = _validate_item(_make_item(), '', 'transcript')
    assert ok is False
    assert 'source_id' in err

def test_validate_missing_source_type():
    ok, err = _validate_item(_make_item(), 'src1', '')
    assert ok is False
    assert 'source_type' in err

def test_validate_invalid_source_type():
    ok, err = _validate_item(_make_item(), 'src1', 'podcast')
    assert ok is False
    assert 'podcast' in err

def test_validate_missing_quote():
    ok, err = _validate_item(_make_item(quote=''), 'src1', 'transcript')
    assert ok is False
    assert 'quote' in err

def test_validate_missing_given_date():
    ok, err = _validate_item(_make_item(given_date=''), 'src1', 'transcript')
    assert ok is False
    assert 'given_date' in err

def test_validate_missing_guidance_id():
    ok, err = _validate_item(_make_item(guidance_id=''), 'src1', 'transcript')
    assert ok is False
    assert 'guidance_id' in err

def test_validate_missing_guidance_update_id():
    ok, err = _validate_item(_make_item(guidance_update_id=None), 'src1', '8k')
    assert ok is False
    assert 'guidance_update_id' in err

def test_validate_missing_label():
    ok, err = _validate_item(_make_item(label=''), 'src1', 'transcript')
    assert ok is False
    assert 'label' in err

def test_validate_none_label():
    ok, err = _validate_item(_make_item(label=None), 'src1', 'transcript')
    assert ok is False
    assert 'label' in err

def test_validate_none_source_id():
    ok, err = _validate_item(_make_item(), None, 'transcript')
    assert ok is False

def test_validate_none_source_type():
    ok, err = _validate_item(_make_item(), 'src1', None)
    assert ok is False


# ── Source label mapping tests ────────────────────────────────────────────

def test_source_label_map_completeness():
    assert SOURCE_LABEL_MAP['8k'] == 'Report'
    assert SOURCE_LABEL_MAP['10q'] == 'Report'
    assert SOURCE_LABEL_MAP['10k'] == 'Report'
    assert SOURCE_LABEL_MAP['transcript'] == 'Transcript'
    assert SOURCE_LABEL_MAP['news'] == 'News'


# ── Core query construction tests ─────────────────────────────────────────

def test_query_source_label_report():
    """Source matched by :Report label for 8k/10q/10k."""
    for st in ('8k', '10q', '10k'):
        q = _build_core_query(st)
        assert 'MATCH (source:Report {id: $source_id})' in q, f"Failed for {st}"

def test_query_source_label_transcript():
    q = _build_core_query('transcript')
    assert 'MATCH (source:Transcript {id: $source_id})' in q

def test_query_source_label_news():
    q = _build_core_query('news')
    assert 'MATCH (source:News {id: $source_id})' in q

def test_query_company_by_ticker():
    """Company matched by ticker, not CIK."""
    q = _build_core_query('transcript')
    assert 'MATCH (company:Company {ticker: $ticker})' in q
    assert '{cik: $cik}' not in q

def test_query_context_cik_from_company_node():
    """Context.cik derived from company node property, not parameter."""
    q = _build_core_query('transcript')
    assert 'ctx.cik = company.cik' in q

def test_query_optional_match_existing():
    """OPTIONAL MATCH for was_created detection before MERGE."""
    q = _build_core_query('transcript')
    assert 'OPTIONAL MATCH (existing:GuidanceUpdate {id: $guidance_update_id})' in q
    assert 'existing IS NULL AS was_created' in q

def test_query_alias_dedupe():
    """Alias accumulation uses reduce-based dedupe, not just null filter."""
    q = _build_core_query('transcript')
    assert 'reduce(' in q
    assert 'a IN acc' in q
    assert 'CASE WHEN a IS NULL OR a IN acc THEN acc ELSE acc + a END' in q

def test_query_gu_on_create_set_only():
    """GuidanceUpdate uses ON CREATE SET only (no ON MATCH SET for gu)."""
    q = _build_core_query('transcript')
    # Find the GuidanceUpdate MERGE section
    gu_section_start = q.index('MERGE (gu:GuidanceUpdate')
    # The next MERGE after GuidanceUpdate should be an edge MERGE, not ON MATCH SET
    after_gu = q[gu_section_start:]
    assert 'ON CREATE SET gu.' in after_gu
    # Ensure no ON MATCH SET for gu specifically
    # (there IS an ON MATCH SET for Guidance node 'g', which is correct)
    gu_to_edges = after_gu[:after_gu.index('MERGE (gu)-[:UPDATES]')]
    assert 'ON MATCH SET gu.' not in gu_to_edges

def test_query_all_core_edges():
    """All 5 core edges present in query."""
    q = _build_core_query('transcript')
    assert 'MERGE (gu)-[:UPDATES]->(g)' in q
    assert 'MERGE (gu)-[:FROM_SOURCE]->(source)' in q
    assert 'MERGE (gu)-[:IN_CONTEXT]->(ctx)' in q
    assert 'MERGE (gu)-[:HAS_PERIOD]->(p)' in q
    assert 'MERGE (gu)-[:HAS_UNIT]->(u)' in q

def test_query_context_edges():
    """Context has HAS_PERIOD and FOR_COMPANY edges."""
    q = _build_core_query('transcript')
    assert 'MERGE (ctx)-[:HAS_PERIOD]->(p)' in q
    assert 'MERGE (ctx)-[:FOR_COMPANY]->(company)' in q


# ── Member query tests ────────────────────────────────────────────────────

def test_member_query_unwind():
    """Member edges use UNWIND batch, not per-member queries."""
    q = _build_member_query()
    assert 'UNWIND $member_u_ids AS member_u_id' in q
    assert 'MATCH (m:Member {u_id: member_u_id})' in q
    assert 'MERGE (gu)-[:MAPS_TO_MEMBER]->(m)' in q
    assert 'count(*) AS linked' in q

def test_member_query_single_query():
    """Member query is one string (single round-trip), not N queries."""
    q = _build_member_query()
    # Should be a single query — only one RETURN
    assert q.count('RETURN') == 1


# ── Parameter assembly tests ─────────────────────────────────────────────

def test_params_maps_canonical_values():
    """canonical_low/mid/high map to low/mid/high params."""
    item = _make_item(canonical_low=94.0, canonical_mid=95.5, canonical_high=97.0)
    params = _build_params(item, 'src1', 'transcript', 'AAPL')
    assert params['low'] == 94.0
    assert params['mid'] == 95.5
    assert params['high'] == 97.0

def test_params_ticker_not_cik():
    """Params use ticker, not cik."""
    params = _build_params(_make_item(), 'src1', 'transcript', 'AAPL')
    assert params['ticker'] == 'AAPL'
    assert 'cik' not in params

def test_params_source_fields():
    params = _build_params(_make_item(), 'my_source_123', '8k', 'MSFT')
    assert params['source_id'] == 'my_source_123'
    assert params['source_type'] == '8k'

def test_params_none_values_preserved():
    """None values (qualitative, conditions, etc.) passed as None."""
    item = _make_item(qualitative=None, conditions=None, fiscal_quarter=None)
    params = _build_params(item, 'src1', 'transcript', 'AAPL')
    assert params['qualitative'] is None
    assert params['conditions'] is None
    assert params['fiscal_quarter'] is None

def test_params_has_timestamp():
    params = _build_params(_make_item(), 'src1', 'transcript', 'AAPL')
    assert 'created_ts' in params
    assert len(params['created_ts']) > 10  # ISO timestamp
    assert 'created_date' in params
    assert len(params['created_date']) == 10  # YYYY-MM-DD

def test_params_defaults():
    """Missing optional fields get sensible defaults."""
    item = _make_item()
    del item['period_node_type']
    del item['segment']
    del item['basis_norm']
    del item['derivation']
    params = _build_params(item, 'src1', 'transcript', 'AAPL')
    assert params['period_node_type'] == 'duration'
    assert params['segment'] == 'Total'
    assert params['basis_norm'] == 'unknown'
    assert params['derivation'] == 'explicit'


# ── Dry-run tests ─────────────────────────────────────────────────────────

def test_dry_run_no_execute():
    """Dry-run returns without calling execute_cypher_query."""
    mgr = MockManager()
    result = write_guidance_item(mgr, _make_item(), 'src1', 'transcript',
                                 'AAPL', dry_run=True)
    assert result['dry_run'] is True
    assert result['error'] is None
    assert result['was_created'] is None
    assert len(mgr.calls) == 0  # No DB calls

def test_dry_run_works_with_flag_disabled():
    """Dry-run works even when ENABLE_GUIDANCE_WRITES is False."""
    old_val = guidance_writer.ENABLE_GUIDANCE_WRITES
    try:
        guidance_writer.ENABLE_GUIDANCE_WRITES = False
        mgr = MockManager()
        result = write_guidance_item(mgr, _make_item(), 'src1', 'transcript',
                                     'AAPL', dry_run=True)
        assert result['dry_run'] is True
        assert result['error'] is None
        assert len(mgr.calls) == 0
    finally:
        guidance_writer.ENABLE_GUIDANCE_WRITES = old_val

def test_dry_run_still_validates():
    """Dry-run still rejects bad input."""
    mgr = MockManager()
    result = write_guidance_item(mgr, _make_item(quote=''), 'src1',
                                 'transcript', 'AAPL', dry_run=True)
    assert result['error'] is not None
    assert 'quote' in result['error']


# ── Feature flag tests ────────────────────────────────────────────────────

def test_feature_flag_disabled_blocks_write():
    """Feature flag off + dry_run=False → writes_disabled error."""
    old_val = guidance_writer.ENABLE_GUIDANCE_WRITES
    try:
        guidance_writer.ENABLE_GUIDANCE_WRITES = False
        mgr = MockManager()
        result = write_guidance_item(mgr, _make_item(), 'src1', 'transcript',
                                     'AAPL', dry_run=False)
        assert result['error'] == 'writes_disabled'
        assert len(mgr.calls) == 0
    finally:
        guidance_writer.ENABLE_GUIDANCE_WRITES = old_val

def test_feature_flag_enabled_allows_write():
    """Feature flag on + dry_run=False → write proceeds."""
    old_val = guidance_writer.ENABLE_GUIDANCE_WRITES
    try:
        guidance_writer.ENABLE_GUIDANCE_WRITES = True
        mgr = MockManager(return_value={'id': 'test', 'was_created': True})
        result = write_guidance_item(mgr, _make_item(), 'src1', 'transcript',
                                     'AAPL', dry_run=False)
        assert result['error'] is None
        assert result['was_created'] is True
        assert len(mgr.calls) == 1  # Core write only (no members)
    finally:
        guidance_writer.ENABLE_GUIDANCE_WRITES = old_val


# ── Write execution tests ────────────────────────────────────────────────

def test_write_success_created():
    """Successful write of new GuidanceUpdate."""
    old_val = guidance_writer.ENABLE_GUIDANCE_WRITES
    try:
        guidance_writer.ENABLE_GUIDANCE_WRITES = True
        mgr = MockManager(return_value={'id': 'test', 'was_created': True})
        result = write_guidance_item(mgr, _make_item(), 'src1', 'transcript',
                                     'AAPL', dry_run=False)
        assert result['was_created'] is True
        assert result['error'] is None
    finally:
        guidance_writer.ENABLE_GUIDANCE_WRITES = old_val

def test_write_existing_skipped():
    """Re-run on existing GuidanceUpdate → was_created=False (no-op)."""
    old_val = guidance_writer.ENABLE_GUIDANCE_WRITES
    try:
        guidance_writer.ENABLE_GUIDANCE_WRITES = True
        mgr = MockManager(return_value={'id': 'test', 'was_created': False})
        result = write_guidance_item(mgr, _make_item(), 'src1', 'transcript',
                                     'AAPL', dry_run=False)
        assert result['was_created'] is False
        assert result['error'] is None
    finally:
        guidance_writer.ENABLE_GUIDANCE_WRITES = old_val

def test_write_source_not_found():
    """MATCH for source returns no rows → source_or_company_not_found."""
    old_val = guidance_writer.ENABLE_GUIDANCE_WRITES
    try:
        guidance_writer.ENABLE_GUIDANCE_WRITES = True
        mgr = MockManager(return_value=None)
        result = write_guidance_item(mgr, _make_item(), 'src1', 'transcript',
                                     'AAPL', dry_run=False)
        assert result['error'] == 'source_or_company_not_found'
    finally:
        guidance_writer.ENABLE_GUIDANCE_WRITES = old_val

def test_write_error_handling():
    """DB error → caught and returned in error field."""
    old_val = guidance_writer.ENABLE_GUIDANCE_WRITES
    try:
        guidance_writer.ENABLE_GUIDANCE_WRITES = True
        mgr = MockManager(side_effects=[RuntimeError("connection lost")])
        result = write_guidance_item(mgr, _make_item(), 'src1', 'transcript',
                                     'AAPL', dry_run=False)
        assert 'connection lost' in result['error']
        assert result['was_created'] is False
    finally:
        guidance_writer.ENABLE_GUIDANCE_WRITES = old_val


# ── Member edge tests ────────────────────────────────────────────────────

def test_write_with_members():
    """Members linked when item has member_u_ids and was_created=True."""
    old_val = guidance_writer.ENABLE_GUIDANCE_WRITES
    try:
        guidance_writer.ENABLE_GUIDANCE_WRITES = True
        item = _make_item(member_u_ids=['320193:us-gaap:ProductMember',
                                        '320193:us-gaap:ServiceMember'])
        mgr = MockManager(side_effects=[
            {'id': 'test', 'was_created': True},  # core write
            {'linked': 2},                          # member write
        ])
        result = write_guidance_item(mgr, item, 'src1', 'transcript',
                                     'AAPL', dry_run=False)
        assert result['member_links'] == 2
        assert len(mgr.calls) == 2  # core + member
        # Second call should be the member UNWIND query
        member_query = mgr.calls[1][0]
        assert 'UNWIND' in member_query
    finally:
        guidance_writer.ENABLE_GUIDANCE_WRITES = old_val

def test_write_no_members_no_extra_call():
    """Empty member_u_ids → no member query executed."""
    old_val = guidance_writer.ENABLE_GUIDANCE_WRITES
    try:
        guidance_writer.ENABLE_GUIDANCE_WRITES = True
        mgr = MockManager(return_value={'id': 'test', 'was_created': True})
        result = write_guidance_item(mgr, _make_item(member_u_ids=[]),
                                     'src1', 'transcript', 'AAPL',
                                     dry_run=False)
        assert result['member_links'] == 0
        assert len(mgr.calls) == 1  # core only
    finally:
        guidance_writer.ENABLE_GUIDANCE_WRITES = old_val

def test_write_members_on_existing_rerun():
    """Member links attempted even on re-run (self-healing after transient failure)."""
    old_val = guidance_writer.ENABLE_GUIDANCE_WRITES
    try:
        guidance_writer.ENABLE_GUIDANCE_WRITES = True
        item = _make_item(member_u_ids=['320193:us-gaap:ProductMember'])
        mgr = MockManager(side_effects=[
            {'id': 'test', 'was_created': False},  # existing node
            {'linked': 1},                           # member still attempted
        ])
        result = write_guidance_item(mgr, item, 'src1', 'transcript',
                                     'AAPL', dry_run=False)
        assert result['member_links'] == 1
        assert len(mgr.calls) == 2  # core + member (self-healing)
    finally:
        guidance_writer.ENABLE_GUIDANCE_WRITES = old_val

def test_member_link_error_non_fatal():
    """Member link failure doesn't fail the overall write."""
    old_val = guidance_writer.ENABLE_GUIDANCE_WRITES
    try:
        guidance_writer.ENABLE_GUIDANCE_WRITES = True
        item = _make_item(member_u_ids=['bad_member'])
        mgr = MockManager(side_effects=[
            {'id': 'test', 'was_created': True},   # core succeeds
            RuntimeError("member not found"),       # member fails
        ])
        result = write_guidance_item(mgr, item, 'src1', 'transcript',
                                     'AAPL', dry_run=False)
        assert result['error'] is None  # core write succeeded
        assert result['was_created'] is True
        assert result['member_links'] == 0
    finally:
        guidance_writer.ENABLE_GUIDANCE_WRITES = old_val


# ── Batch tests ───────────────────────────────────────────────────────────

def test_batch_summary_counts():
    """Batch correctly tallies created/skipped/errors."""
    old_val = guidance_writer.ENABLE_GUIDANCE_WRITES
    try:
        guidance_writer.ENABLE_GUIDANCE_WRITES = True
        items = [
            _make_item(guidance_update_id='gu:a'),
            _make_item(guidance_update_id='gu:b'),
            _make_item(guidance_update_id='gu:c', quote=''),  # will fail validation
        ]
        mgr = MockManager(side_effects=[
            {'id': 'gu:a', 'was_created': True},
            {'id': 'gu:b', 'was_created': False},
        ])
        summary = write_guidance_batch(mgr, items, 'src1', 'transcript',
                                       'AAPL', dry_run=False)
        assert summary['total'] == 3
        assert summary['created'] == 1
        assert summary['skipped'] == 1
        assert summary['errors'] == 1
    finally:
        guidance_writer.ENABLE_GUIDANCE_WRITES = old_val

def test_batch_empty():
    summary = write_guidance_batch(MockManager(), [], 'src1', 'transcript',
                                   'AAPL', dry_run=True)
    assert summary['total'] == 0
    assert summary['created'] == 0

def test_batch_dry_run():
    """All items in dry-run → skipped count (not created, not errors)."""
    items = [_make_item(), _make_item(guidance_update_id='gu:x')]
    mgr = MockManager()
    summary = write_guidance_batch(mgr, items, 'src1', 'transcript',
                                   'AAPL', dry_run=True)
    assert summary['total'] == 2
    assert summary['skipped'] == 2  # dry-run returns was_created=None → skipped
    assert summary['errors'] == 0
    assert len(mgr.calls) == 0


# ── Constraint creation tests ────────────────────────────────────────────

def test_create_constraints():
    """create_guidance_constraints runs 2 constraint queries."""
    mgr = MockManager()
    create_guidance_constraints(mgr)
    assert len(mgr.calls) == 2
    q1 = mgr.calls[0][0]
    q2 = mgr.calls[1][0]
    assert 'guidance_id_unique' in q1
    assert 'Guidance' in q1
    assert 'guidance_update_id_unique' in q2
    assert 'GuidanceUpdate' in q2
    assert 'IF NOT EXISTS' in q1
    assert 'IF NOT EXISTS' in q2


# ── Integration-style query content tests ─────────────────────────────────

def test_query_contains_all_gu_properties():
    """GuidanceUpdate ON CREATE SET includes all 19 extraction fields + system fields."""
    q = _build_core_query('transcript')
    expected_props = [
        'gu.evhash16', 'gu.given_date', 'gu.period_type', 'gu.fiscal_year',
        'gu.fiscal_quarter', 'gu.segment', 'gu.low', 'gu.mid', 'gu.high',
        'gu.unit', 'gu.basis_norm', 'gu.basis_raw', 'gu.derivation',
        'gu.qualitative', 'gu.quote', 'gu.section', 'gu.source_key',
        'gu.source_type', 'gu.conditions', 'gu.xbrl_qname', 'gu.created',
    ]
    for prop in expected_props:
        assert prop in q, f"Missing property in query: {prop}"

def test_query_no_on_match_set_for_gu():
    """GuidanceUpdate section has ON CREATE SET but not ON MATCH SET."""
    q = _build_core_query('8k')
    # Split at GuidanceUpdate MERGE to isolate its section
    parts = q.split('MERGE (gu:GuidanceUpdate')
    assert len(parts) == 2
    gu_section = parts[1]
    # ON MATCH SET should NOT appear before the next MERGE
    before_first_edge = gu_section.split('MERGE (gu)-')[0]
    assert 'ON MATCH SET' not in before_first_edge

def test_params_complete_roundtrip():
    """All params referenced in query exist in params dict."""
    item = _make_item()
    params = _build_params(item, 'src1', 'transcript', 'AAPL')
    q = _build_core_query('transcript')
    # Extract all $param references from query
    import re
    param_refs = set(re.findall(r'\$(\w+)', q))
    for ref in param_refs:
        assert ref in params, f"Query references ${ref} but not in params dict"


# ── Run all tests ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [(name, obj) for name, obj in sorted(globals().items())
             if name.startswith('test_') and callable(obj)]
    passed = failed = 0
    for name, fn in tests:
        try:
            fn()
            passed += 1
            print(f"  PASS  {name}")
        except Exception as e:
            failed += 1
            print(f"  FAIL  {name}: {e}")
    print(f"\n{passed} passed, {failed} failed out of {passed + failed}")
    sys.exit(1 if failed else 0)
