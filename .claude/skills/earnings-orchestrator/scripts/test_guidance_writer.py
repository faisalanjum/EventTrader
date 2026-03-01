#!/usr/bin/env python3
"""
Tests for guidance_writer.py (v3.0) — validates Cypher construction, parameter
assembly, validation gates, dry-run, feature flag, and batch logic.

v3.0 changes: No Context node, no Unit node, direct FOR_COMPANY edge,
calendar-based GuidancePeriod (gp_ namespace), canonical_unit as property.

No Neo4j connection needed — all tests use mock manager.
"""

import sys
sys.path.insert(0, "/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts")
sys.path.insert(0, "/home/faisal/EventMarketDB")

import guidance_writer
from guidance_writer import (
    _validate_item, _build_core_query, _build_params,
    _build_concept_query, _build_member_query,
    write_guidance_item, write_guidance_batch,
    create_guidance_constraints, SOURCE_LABEL_MAP,
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
        'guidance_update_id': 'gu:test_src:revenue:guidance_period_320193_duration_FY2025_Q2:gaap:total',
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
        'period_scope': 'quarter',
        'time_type': 'duration',
        'fiscal_year': 2025,
        'fiscal_quarter': 2,
        'segment': 'Total',
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
        'period_u_id': 'gp_2025-01-01_2025-06-30',
        'gp_start_date': '2025-01-01',
        'gp_end_date': '2025-06-30',
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

def test_query_period_calendar_based():
    """GuidancePeriod MERGE uses calendar dates, not fiscal properties."""
    q = _build_core_query('transcript')
    assert 'GuidancePeriod' in q
    assert 'gp.start_date = $gp_start_date' in q
    assert 'gp.end_date = $gp_end_date' in q
    assert 'p.cik' not in q
    assert 'p.fiscal_year' not in q

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

def test_query_gu_set_pattern():
    """GuidanceUpdate uses ON CREATE SET for created, SET for all other props."""
    q = _build_core_query('transcript')
    gu_section_start = q.index('MERGE (gu:GuidanceUpdate')
    after_gu = q[gu_section_start:]
    gu_to_edges = after_gu[:after_gu.index('MERGE (gu)-[:UPDATES]')]
    # ON CREATE SET only for created timestamp
    assert 'ON CREATE SET gu.created' in gu_to_edges
    # SET (not ON CREATE SET) for all content properties
    assert 'SET gu.evhash16' in gu_to_edges

def test_query_all_core_edges():
    """All 4 core edges present in query (v3.0: no IN_CONTEXT, no HAS_UNIT)."""
    q = _build_core_query('transcript')
    assert 'MERGE (gu)-[:UPDATES]->(g)' in q
    assert 'MERGE (gu)-[:FROM_SOURCE]->(source)' in q
    assert 'MERGE (gu)-[:FOR_COMPANY]->(company)' in q
    assert 'MERGE (gu)-[:HAS_PERIOD]->(gp)' in q
    # v3.0 removals
    assert 'IN_CONTEXT' not in q
    assert 'HAS_UNIT' not in q

def test_query_no_context_no_unit():
    """v3.0: No Context MERGE, no Unit MERGE in core query."""
    q = _build_core_query('transcript')
    assert 'MERGE (ctx:Context' not in q
    assert 'MERGE (u:Unit' not in q


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

def test_params_ticker():
    """Params include ticker."""
    params = _build_params(_make_item(), 'src1', 'transcript', 'AAPL')
    assert params['ticker'] == 'AAPL'

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
    del item['segment']
    del item['basis_norm']
    del item['derivation']
    params = _build_params(item, 'src1', 'transcript', 'AAPL')
    assert params['period_scope'] == 'quarter'
    assert params['time_type'] == 'duration'
    assert params['segment'] == 'Total'
    assert params['basis_norm'] == 'unknown'
    assert params['derivation'] == 'unknown'


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
        result = write_guidance_item(mgr, _make_item(), 'src1',
                                     'transcript', 'AAPL', dry_run=False)
        assert result['error'] is None
        assert result['was_created'] is True
        assert len(mgr.calls) == 2  # Core write + concept (no members)
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
            {'id': 'test', 'was_created': True},      # core write
            {'linked_qname': 'us-gaap:Revenues'},      # concept
            {'linked': 2},                              # member write
        ])
        result = write_guidance_item(mgr, item, 'src1', 'transcript',
                                     'AAPL', dry_run=False)
        assert result['member_links'] == 2
        assert len(mgr.calls) == 3  # core + concept + member
        # Third call should be the member UNWIND query
        member_query = mgr.calls[2][0]
        assert 'UNWIND' in member_query
    finally:
        guidance_writer.ENABLE_GUIDANCE_WRITES = old_val

def test_write_no_members_no_extra_call():
    """Empty member_u_ids → no member queries executed (concept still runs)."""
    old_val = guidance_writer.ENABLE_GUIDANCE_WRITES
    try:
        guidance_writer.ENABLE_GUIDANCE_WRITES = True
        mgr = MockManager(return_value={'id': 'test', 'was_created': True})
        result = write_guidance_item(mgr, _make_item(member_u_ids=[]),
                                     'src1', 'transcript', 'AAPL',
                                     dry_run=False)
        assert result['member_links'] == 0
        assert len(mgr.calls) == 2  # core + concept (no member)
    finally:
        guidance_writer.ENABLE_GUIDANCE_WRITES = old_val

def test_write_members_on_existing_rerun():
    """Member links attempted even on re-run (self-healing after transient failure)."""
    old_val = guidance_writer.ENABLE_GUIDANCE_WRITES
    try:
        guidance_writer.ENABLE_GUIDANCE_WRITES = True
        item = _make_item(member_u_ids=['320193:us-gaap:ProductMember'])
        mgr = MockManager(side_effects=[
            {'id': 'test', 'was_created': False},      # existing node
            {'linked_qname': 'us-gaap:Revenues'},      # concept
            {'linked': 1},                              # member still attempted
        ])
        result = write_guidance_item(mgr, item, 'src1', 'transcript',
                                     'AAPL', dry_run=False)
        assert result['member_links'] == 1
        assert len(mgr.calls) == 3  # core + concept + member (self-healing)
    finally:
        guidance_writer.ENABLE_GUIDANCE_WRITES = old_val

def test_member_link_error_non_fatal():
    """Member link failure doesn't fail the overall write."""
    old_val = guidance_writer.ENABLE_GUIDANCE_WRITES
    try:
        guidance_writer.ENABLE_GUIDANCE_WRITES = True
        item = _make_item(member_u_ids=['bad_member'])
        mgr = MockManager(side_effects=[
            {'id': 'test', 'was_created': True},      # core succeeds
            {'linked_qname': 'us-gaap:Revenues'},      # concept succeeds
            RuntimeError("member not found"),           # member fails
        ])
        result = write_guidance_item(mgr, item, 'src1', 'transcript',
                                     'AAPL', dry_run=False)
        assert result['error'] is None  # core write succeeded
        assert result['was_created'] is True
        assert result['member_links'] == 0
    finally:
        guidance_writer.ENABLE_GUIDANCE_WRITES = old_val


# ── Concept edge tests ──────────────────────────────────────────────────

def test_concept_query_structure():
    """Concept query uses MATCH with LIMIT 1 for multi-taxonomy ambiguity."""
    q = _build_concept_query()
    assert 'MATCH (gu:GuidanceUpdate {id: $guidance_update_id})' in q
    assert 'MATCH (con:Concept {qname: $xbrl_qname})' in q
    assert 'LIMIT 1' in q
    assert 'MERGE (gu)-[:MAPS_TO_CONCEPT]->(con)' in q
    assert 'linked_qname' in q

def test_concept_query_single_query():
    """Concept query is one string (single round-trip)."""
    q = _build_concept_query()
    assert q.count('RETURN') == 1

def test_write_with_concept():
    """Concept edge created when xbrl_qname is set."""
    old_val = guidance_writer.ENABLE_GUIDANCE_WRITES
    try:
        guidance_writer.ENABLE_GUIDANCE_WRITES = True
        item = _make_item(xbrl_qname='us-gaap:Revenues', member_u_ids=[])
        mgr = MockManager(side_effects=[
            {'id': 'test', 'was_created': True},        # core write
            {'linked_qname': 'us-gaap:Revenues'},        # concept
        ])
        result = write_guidance_item(mgr, item, 'src1', 'transcript',
                                     'AAPL', dry_run=False)
        assert result['concept_links'] == 1
        assert len(mgr.calls) == 2  # core + concept
        # Second call should be concept query
        concept_query = mgr.calls[1][0]
        assert 'MAPS_TO_CONCEPT' in concept_query
    finally:
        guidance_writer.ENABLE_GUIDANCE_WRITES = old_val

def test_write_without_concept():
    """No concept query when xbrl_qname is None."""
    old_val = guidance_writer.ENABLE_GUIDANCE_WRITES
    try:
        guidance_writer.ENABLE_GUIDANCE_WRITES = True
        item = _make_item(xbrl_qname=None, member_u_ids=[])
        mgr = MockManager(return_value={'id': 'test', 'was_created': True})
        result = write_guidance_item(mgr, item, 'src1', 'transcript',
                                     'AAPL', dry_run=False)
        assert result['concept_links'] == 0
        assert len(mgr.calls) == 1  # core only, no concept

    finally:
        guidance_writer.ENABLE_GUIDANCE_WRITES = old_val

def test_sentinel_period_write():
    """Item with sentinel period (gp_MT) passes null dates through writer correctly."""
    item = _make_item(
        period_u_id='gp_MT',
        period_scope='medium_term',
        gp_start_date=None,
        gp_end_date=None,
    )
    # Verify dry-run accepts sentinel items
    result = write_guidance_item(None, item, 'src1', 'transcript', 'AAPL', dry_run=True)
    assert result['dry_run'] is True
    assert result['error'] is None
    # Verify params correctly pass null dates for sentinel
    params = _build_params(item, 'src1', 'transcript', 'AAPL')
    assert params['period_u_id'] == 'gp_MT'
    assert params['gp_start_date'] is None
    assert params['gp_end_date'] is None
    assert params['period_scope'] == 'medium_term'
    assert params['time_type'] == 'duration'

def test_concept_no_match_returns_zero():
    """Concept query returns None (no matching Concept node) → 0 links."""
    old_val = guidance_writer.ENABLE_GUIDANCE_WRITES
    try:
        guidance_writer.ENABLE_GUIDANCE_WRITES = True
        item = _make_item(xbrl_qname='us-gaap:NonExistent', member_u_ids=[])
        mgr = MockManager(side_effects=[
            {'id': 'test', 'was_created': True},  # core write
            None,                                    # concept MATCH fails
        ])
        result = write_guidance_item(mgr, item, 'src1', 'transcript',
                                     'AAPL', dry_run=False)
        assert result['concept_links'] == 0
        assert result['error'] is None
    finally:
        guidance_writer.ENABLE_GUIDANCE_WRITES = old_val

def test_concept_link_error_non_fatal():
    """Concept link failure doesn't fail the overall write."""
    old_val = guidance_writer.ENABLE_GUIDANCE_WRITES
    try:
        guidance_writer.ENABLE_GUIDANCE_WRITES = True
        item = _make_item(xbrl_qname='us-gaap:Revenues', member_u_ids=[])
        mgr = MockManager(side_effects=[
            {'id': 'test', 'was_created': True},    # core succeeds
            RuntimeError("concept not found"),        # concept fails
        ])
        result = write_guidance_item(mgr, item, 'src1', 'transcript',
                                     'AAPL', dry_run=False)
        assert result['error'] is None  # core succeeded
        assert result['was_created'] is True
        assert result['concept_links'] == 0
    finally:
        guidance_writer.ENABLE_GUIDANCE_WRITES = old_val

def test_concept_runs_on_existing_rerun():
    """Concept link attempted even on re-run (self-healing)."""
    old_val = guidance_writer.ENABLE_GUIDANCE_WRITES
    try:
        guidance_writer.ENABLE_GUIDANCE_WRITES = True
        item = _make_item(xbrl_qname='us-gaap:Revenues', member_u_ids=[])
        mgr = MockManager(side_effects=[
            {'id': 'test', 'was_created': False},      # existing node
            {'linked_qname': 'us-gaap:Revenues'},      # concept still attempted
        ])
        result = write_guidance_item(mgr, item, 'src1', 'transcript',
                                     'AAPL', dry_run=False)
        assert result['concept_links'] == 1
        assert len(mgr.calls) == 2  # core + concept (self-healing)
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
            {'id': 'gu:a', 'was_created': True},        # core write a
            {'linked_qname': 'us-gaap:Revenues'},        # concept a
            {'id': 'gu:b', 'was_created': False},        # core write b
            {'linked_qname': 'us-gaap:Revenues'},        # concept b
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
    """create_guidance_constraints runs 3 constraints + 2 indexes + 4 sentinel MERGEs = 9 calls."""
    mgr = MockManager()
    create_guidance_constraints(mgr)
    assert len(mgr.calls) == 9
    q1 = mgr.calls[0][0]
    q2 = mgr.calls[1][0]
    q3 = mgr.calls[2][0]
    assert 'guidance_id_unique' in q1
    assert 'Guidance' in q1
    assert 'guidance_update_id_unique' in q2
    assert 'GuidanceUpdate' in q2
    assert 'guidance_period_id_unique' in q3
    assert 'GuidancePeriod' in q3
    assert 'IF NOT EXISTS' in q1
    assert 'IF NOT EXISTS' in q2
    assert 'IF NOT EXISTS' in q3
    # Indexes
    idx1 = mgr.calls[3][0]
    idx2 = mgr.calls[4][0]
    assert 'INDEX' in idx1 and 'label_slug' in idx1
    assert 'INDEX' in idx2 and 'segment_slug' in idx2
    # Sentinel MERGEs
    sentinel_calls = [mgr.calls[i][0] for i in range(5, 9)]
    sentinel_ids = {'gp_ST', 'gp_MT', 'gp_LT', 'gp_UNDEF'}
    for call in sentinel_calls:
        assert 'GuidancePeriod' in call
    found_ids = {c.split("'")[1] for c in sentinel_calls}
    assert found_ids == sentinel_ids


# ── Integration-style query content tests ─────────────────────────────────

def test_query_contains_all_gu_properties():
    """GuidanceUpdate SET includes all 19 extraction fields + system fields."""
    q = _build_core_query('transcript')
    expected_props = [
        'gu.evhash16', 'gu.given_date', 'gu.period_scope', 'gu.time_type', 'gu.fiscal_year',
        'gu.fiscal_quarter', 'gu.segment', 'gu.low', 'gu.mid', 'gu.high',
        'gu.canonical_unit', 'gu.basis_norm', 'gu.basis_raw', 'gu.derivation',
        'gu.qualitative', 'gu.quote', 'gu.section', 'gu.source_key',
        'gu.source_type', 'gu.conditions', 'gu.xbrl_qname', 'gu.created',
        'gu.label', 'gu.label_slug', 'gu.segment_slug', 'gu.source_refs',
    ]
    for prop in expected_props:
        assert prop in q, f"Missing property in query: {prop}"

def test_query_gu_uses_set_not_on_match_set():
    """GuidanceUpdate section uses plain SET (not ON MATCH SET) for content properties."""
    q = _build_core_query('8k')
    parts = q.split('MERGE (gu:GuidanceUpdate')
    assert len(parts) == 2
    gu_section = parts[1]
    before_first_edge = gu_section.split('MERGE (gu)-')[0]
    # Should have ON CREATE SET for created only, then SET for everything else
    assert 'ON CREATE SET gu.created' in before_first_edge
    assert '\n  SET gu.evhash16' in before_first_edge

def test_params_complete_roundtrip():
    """All params referenced in query exist in params dict (incl. unit XBRL fields)."""
    item = _make_item()
    params = _build_params(item, 'src1', 'transcript', 'AAPL')
    q = _build_core_query('transcript')
    # Extract all $param references from query
    import re
    param_refs = set(re.findall(r'\$(\w+)', q))
    for ref in param_refs:
        assert ref in params, f"Query references ${ref} but not in params dict"
    # v3.0: no unit XBRL fields (Unit node removed)
    assert 'unit_item_type' not in params
    assert 'unit_is_divide' not in params


# ── v3.0: canonical_unit as property (no Unit node) ─────────────────

def test_params_canonical_unit_passthrough():
    """canonical_unit from item passed directly to params."""
    params = _build_params(_make_item(canonical_unit='m_usd'), 'src1',
                           'transcript', 'AAPL')
    assert params['canonical_unit'] == 'm_usd'

def test_params_no_unit_node_fields():
    """v3.0: No unit_u_id, unit_item_type, unit_is_divide in params."""
    params = _build_params(_make_item(), 'src1', 'transcript', 'AAPL')
    assert 'unit_u_id' not in params
    assert 'unit_item_type' not in params
    assert 'unit_is_divide' not in params

def test_params_no_ctx_fields():
    """v3.0: No ctx_u_id in params (Context removed)."""
    params = _build_params(_make_item(), 'src1', 'transcript', 'AAPL')
    assert 'ctx_u_id' not in params

def test_params_has_gp_date_fields():
    """GuidancePeriod: gp_start_date and gp_end_date ARE in params."""
    params = _build_params(_make_item(), 'src1', 'transcript', 'AAPL')
    assert 'gp_start_date' in params
    assert 'gp_end_date' in params
    assert params['gp_start_date'] == '2025-01-01'
    assert params['gp_end_date'] == '2025-06-30'


# ── Denormalized slug tests (Issues #53/#55) ─────────────────────────────

def test_params_label_and_segment_slugs():
    """label_slug and segment_slug are denormalized into params for GuidanceUpdate."""
    item = _make_item()
    params = _build_params(item, 'src1', 'transcript', 'AAPL')
    assert params['label_slug'] == 'revenue'
    assert params['segment_slug'] == 'total'

def test_params_slug_fallback_when_missing():
    """Slugs computed from raw fields when pre-computed slugs are absent."""
    item = _make_item()
    del item['label_slug']
    del item['segment_slug']
    params = _build_params(item, 'src1', 'transcript', 'AAPL')
    assert params['label_slug'] == 'revenue'   # computed from label='Revenue'
    assert params['segment_slug'] == 'total'    # computed from segment='Total'

def test_params_slug_segment_variant():
    """segment_slug correctly slugifies non-trivial segment names."""
    item = _make_item(segment='Wearables, Home and Accessories',
                      segment_slug='wearables_home_and_accessories')
    params = _build_params(item, 'src1', 'transcript', 'AAPL')
    assert params['segment_slug'] == 'wearables_home_and_accessories'


# ── source_refs sub-provenance (Issue #36) ───────────────────────────────

def test_params_source_refs_passthrough():
    """source_refs array is passed through to params."""
    refs = ['AAPL_2023-11-03_qa__3', 'AAPL_2023-11-03_qa__7']
    params = _build_params(_make_item(source_refs=refs), 'src1', 'transcript', 'AAPL')
    assert params['source_refs'] == refs

def test_params_source_refs_default_empty():
    """source_refs defaults to empty list when not provided."""
    item = _make_item()
    # source_refs not in _make_item defaults
    params = _build_params(item, 'src1', 'transcript', 'AAPL')
    assert params['source_refs'] == []

def test_params_source_refs_none_becomes_empty():
    """source_refs=None normalizes to empty list."""
    params = _build_params(_make_item(source_refs=None), 'src1', 'transcript', 'AAPL')
    assert params['source_refs'] == []


# ── Per-share validation guards (Issue #28) ──────────────────────────────

def test_validate_per_share_label_with_m_usd():
    """Guard A: per-share label + canonical_unit='m_usd' must be rejected."""
    item = _make_item(
        label='Adjusted EPS',
        label_slug='adjusted_eps',
        canonical_unit='m_usd',
        guidance_id='guidance:adjusted_eps',
        guidance_update_id='gu:src:adjusted_eps:gp_2025-01-01_2025-03-31:non_gaap:total',
    )
    ok, err = _validate_item(item, 'src1', 'transcript')
    assert ok is False
    assert 'per-share' in err
    assert 'adjusted_eps' in err


def test_validate_per_share_label_with_correct_unit():
    """Per-share label + canonical_unit='usd' must pass."""
    item = _make_item(
        label='Adjusted EPS',
        label_slug='adjusted_eps',
        canonical_unit='usd',
        canonical_low=1.46,
        canonical_mid=1.48,
        canonical_high=1.50,
        guidance_id='guidance:adjusted_eps',
        guidance_update_id='gu:src:adjusted_eps:gp_2025-01-01_2025-03-31:non_gaap:total',
    )
    ok, err = _validate_item(item, 'src1', 'transcript')
    assert ok is True
    assert err is None


def test_validate_per_share_label_with_percent_unit():
    """Per-share label + canonical_unit='percent' must pass (growth rate guidance)."""
    item = _make_item(
        label='AFFO Per Share',
        label_slug='affo_per_share',
        canonical_unit='percent',
        canonical_low=5.0,
        canonical_high=7.0,
        guidance_id='guidance:affo_per_share',
        guidance_update_id='gu:src:affo_per_share:gp_2025-01-01_2025-03-31:unknown:total',
    )
    ok, err = _validate_item(item, 'src1', 'transcript')
    assert ok is True
    assert err is None


def test_validate_per_share_label_with_unknown_unit():
    """Per-share label + canonical_unit='unknown' must pass (qualitative guidance)."""
    item = _make_item(
        label='EPS',
        label_slug='eps',
        canonical_unit='unknown',
        canonical_low=None,
        canonical_mid=None,
        canonical_high=None,
        qualitative='continued strong growth',
        guidance_id='guidance:eps',
        guidance_update_id='gu:src:eps:gp_2025-01-01_2025-03-31:gaap:total',
    )
    ok, err = _validate_item(item, 'src1', 'transcript')
    assert ok is True
    assert err is None


def test_validate_xbrl_per_share_with_m_usd():
    """Guard B: xbrl_qname with PerShare + canonical_unit='m_usd' must be rejected."""
    item = _make_item(
        label='Diluted Earnings',
        label_slug='diluted_earnings',
        canonical_unit='m_usd',
        xbrl_qname='us-gaap:EarningsPerShareDiluted',
        guidance_id='guidance:diluted_earnings',
        guidance_update_id='gu:src:diluted_earnings:gp_2025-01-01_2025-03-31:gaap:total',
    )
    ok, err = _validate_item(item, 'src1', 'transcript')
    assert ok is False
    assert 'xbrl_qname' in err


def test_validate_xbrl_per_diluted_share_with_m_usd():
    """Guard B: xbrl_qname with PerDilutedShare pattern + m_usd must be rejected."""
    item = _make_item(
        label='Continuing Operations Income',
        label_slug='continuing_operations_income',
        canonical_unit='m_usd',
        xbrl_qname='us-gaap:IncomeLossFromContinuingOperationsPerDilutedShare',
        guidance_id='guidance:continuing_operations_income',
        guidance_update_id='gu:src:continuing_operations_income:gp_2025-01-01_2025-03-31:gaap:total',
    )
    ok, err = _validate_item(item, 'src1', 'transcript')
    assert ok is False
    assert 'xbrl_qname' in err


def test_validate_xbrl_per_unit_with_m_usd():
    """Guard B: xbrl_qname with PerUnit + canonical_unit='m_usd' must be rejected."""
    item = _make_item(
        label='LP Distributions',
        label_slug='lp_distributions',
        canonical_unit='m_usd',
        xbrl_qname='us-gaap:DistributionMadeToLimitedPartnerDistributionsPaidPerUnit',
        guidance_id='guidance:lp_distributions',
        guidance_update_id='gu:src:lp_distributions:gp_2025-01-01_2025-03-31:gaap:total',
    )
    ok, err = _validate_item(item, 'src1', 'transcript')
    assert ok is False
    assert 'xbrl_qname' in err


def test_validate_xbrl_per_share_with_correct_unit():
    """xbrl_qname with PerShare + canonical_unit='usd' must pass."""
    item = _make_item(
        label='EPS',
        label_slug='eps',
        canonical_unit='usd',
        canonical_low=1.46,
        canonical_mid=1.48,
        canonical_high=1.50,
        xbrl_qname='us-gaap:EarningsPerShareDiluted',
        guidance_id='guidance:eps',
        guidance_update_id='gu:src:eps:gp_2025-01-01_2025-03-31:gaap:total',
    )
    ok, err = _validate_item(item, 'src1', 'transcript')
    assert ok is True
    assert err is None


def test_validate_aggregate_label_unchanged():
    """Non-per-share labels with m_usd must still pass (no false positive)."""
    item = _make_item()  # default is revenue + m_usd
    ok, err = _validate_item(item, 'src1', 'transcript')
    assert ok is True
    assert err is None


def test_validate_xbrl_aggregate_unchanged():
    """xbrl_qname without PerShare/PerUnit + m_usd must pass."""
    item = _make_item(xbrl_qname='us-gaap:Revenues')
    ok, err = _validate_item(item, 'src1', 'transcript')
    assert ok is True
    assert err is None


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
