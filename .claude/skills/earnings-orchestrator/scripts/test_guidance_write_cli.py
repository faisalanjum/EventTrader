#!/usr/bin/env python3
"""
Tests for guidance_write_cli.py — validates CLI input parsing, ID computation,
validation, dry-run output, and error handling.

No Neo4j connection needed — tests mock the write path or use dry-run mode.
"""

import json
import os
import sys
import tempfile

sys.path.insert(0, "/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts")
sys.path.insert(0, "/home/faisal/EventMarketDB")

from guidance_write_cli import _ensure_ids, _ensure_period


# ── _ensure_ids tests ────────────────────────────────────────────────────

def _make_raw_item(**overrides):
    """Build a raw extraction item (no pre-computed IDs)."""
    item = {
        'label': 'Revenue',
        'source_id': 'TEST_SRC',
        'period_u_id': 'gp_2024-10-01_2024-12-31',
        'basis_norm': 'unknown',
        'segment': 'Total',
        'low': 94.0, 'mid': None, 'high': 97.0,
        'unit_raw': 'billion',
        'qualitative': None,
        'conditions': None,
        'given_date': '2025-01-30',
        'quote': 'We expect revenue between $94B and $97B',
    }
    item.update(overrides)
    return item


def test_ensure_ids_computes_when_missing():
    item = _make_raw_item()
    result = _ensure_ids(item)
    assert 'guidance_id' in result
    assert 'guidance_update_id' in result
    assert 'evhash16' in result
    assert result['guidance_id'] == 'guidance:revenue'
    assert result['guidance_update_id'].startswith('gu:TEST_SRC:revenue:gp_')


def test_ensure_ids_skips_when_present():
    item = _make_raw_item(guidance_update_id='gu:pre_computed:id')
    result = _ensure_ids(item)
    assert result['guidance_update_id'] == 'gu:pre_computed:id'


def test_ensure_ids_computes_canonical_values():
    item = _make_raw_item(low=94.0, high=97.0, unit_raw='billion')
    result = _ensure_ids(item)
    # billion → m_usd, 94B → 94000 m
    assert result['canonical_unit'] == 'm_usd'
    assert result['canonical_low'] == 94000.0
    assert result['canonical_high'] == 97000.0
    # mid auto-computed
    assert result['canonical_mid'] == 95500.0


def test_ensure_ids_missing_label_raises():
    item = _make_raw_item(label='')
    try:
        _ensure_ids(item)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert 'label' in str(e)


def test_ensure_ids_missing_source_id_raises():
    item = _make_raw_item()
    del item['source_id']
    try:
        _ensure_ids(item)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert 'source_id' in str(e)


def test_ensure_ids_percent_unit():
    item = _make_raw_item(low=45.0, high=46.0, unit_raw='percent', label='Gross Margin')
    result = _ensure_ids(item)
    assert result['canonical_unit'] == 'percent'
    assert result['canonical_low'] == 45.0  # no scale change for percent


def test_ensure_ids_eps_usd():
    item = _make_raw_item(low=3.20, high=3.40, unit_raw='$', label='EPS')
    result = _ensure_ids(item)
    assert result['canonical_unit'] == 'usd'  # per-share override
    assert result['canonical_low'] == 3.20


def test_ensure_ids_default_segment():
    item = _make_raw_item()
    del item['segment']  # should default to 'Total'
    result = _ensure_ids(item)
    assert 'total' in result['guidance_update_id']


# ── Concept inheritance tests ────────────────────────────────────────────
# These test the batch-level concept inheritance logic in main().
# We test at the item level by importing the logic directly.

def _apply_concept_inheritance(items):
    """Replicate the concept inheritance logic from guidance_write_cli.main()."""
    concept_map = {}
    for item in items:
        if item.get('xbrl_qname') and item.get('label'):
            concept_map.setdefault(item['label'], item['xbrl_qname'])
    for item in items:
        if not item.get('xbrl_qname') and item.get('label') in concept_map:
            item['xbrl_qname'] = concept_map[item['label']]
    return items


def test_concept_inheritance_fills_null():
    """Segment item inherits xbrl_qname from sibling with same label."""
    items = [
        _make_raw_item(label='Revenue', segment='Total'),
        _make_raw_item(label='Revenue', segment='iPhone'),
    ]
    items[0]['xbrl_qname'] = 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax'
    items[1]['xbrl_qname'] = None

    _apply_concept_inheritance(items)
    assert items[1]['xbrl_qname'] == 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax'


def test_concept_inheritance_no_overwrite():
    """Item with existing xbrl_qname is NOT overwritten by sibling."""
    items = [
        _make_raw_item(label='Revenue', segment='Total'),
        _make_raw_item(label='Revenue', segment='Services'),
    ]
    items[0]['xbrl_qname'] = 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax'
    items[1]['xbrl_qname'] = 'us-gaap:SomeOtherConcept'

    _apply_concept_inheritance(items)
    assert items[1]['xbrl_qname'] == 'us-gaap:SomeOtherConcept'


def test_concept_inheritance_different_labels_no_crosstalk():
    """Concept inheritance only applies within same label, not across metrics."""
    items = [
        _make_raw_item(label='Revenue', segment='Total'),
        _make_raw_item(label='Gross Margin', segment='Total', low=45.0, high=46.0, unit_raw='percent'),
    ]
    items[0]['xbrl_qname'] = 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax'
    items[1]['xbrl_qname'] = None

    _apply_concept_inheritance(items)
    assert items[0]['xbrl_qname'] == 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax'
    assert items[1]['xbrl_qname'] is None


def test_concept_inheritance_all_null_no_change():
    """If no item has a concept, nothing changes."""
    items = [
        _make_raw_item(label='Revenue', segment='Total'),
        _make_raw_item(label='Revenue', segment='iPhone'),
    ]
    items[0]['xbrl_qname'] = None
    items[1]['xbrl_qname'] = None

    _apply_concept_inheritance(items)
    assert items[0]['xbrl_qname'] is None
    assert items[1]['xbrl_qname'] is None


# ── JSON round-trip tests ────────────────────────────────────────────────

def test_json_roundtrip_special_chars():
    """Verify shell-hostile CFO text survives JSON serialization."""
    hostile_quote = 'EPS of $3.20-$3.40, that\'s "above consensus" — Jim said: "We\'re confident"'
    item = _make_raw_item(quote=hostile_quote)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({'items': [item], 'source_id': 'S', 'source_type': 'transcript', 'ticker': 'T'}, f)
        path = f.name

    try:
        with open(path) as f:
            loaded = json.load(f)
        assert loaded['items'][0]['quote'] == hostile_quote
    finally:
        os.unlink(path)


def test_json_roundtrip_none_values():
    """Verify null values survive JSON round-trip."""
    item = _make_raw_item(qualitative=None, conditions=None, mid=None, basis_raw=None)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({'items': [item], 'source_id': 'S', 'source_type': 'transcript', 'ticker': 'T'}, f)
        path = f.name

    try:
        with open(path) as f:
            loaded = json.load(f)
        assert loaded['items'][0]['qualitative'] is None
        assert loaded['items'][0]['conditions'] is None
        assert loaded['items'][0]['mid'] is None
    finally:
        os.unlink(path)


# ── CLI invocation tests (subprocess) ────────────────────────────────────

def test_cli_dry_run():
    """Full CLI dry-run via subprocess."""
    import subprocess

    item = _make_raw_item()
    data = {
        'source_id': 'TEST_SRC',
        'source_type': 'transcript',
        'ticker': 'AAPL',
        'items': [item],
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f)
        path = f.name

    try:
        result = subprocess.run(
            [sys.executable, '-m', 'guidance_write_cli', path, '--dry-run'],
            capture_output=True, text=True,
            cwd='/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts',
            env={**os.environ, 'PYTHONPATH': '/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts:/home/faisal/EventMarketDB'},
        )
        output = json.loads(result.stdout)
        assert output['mode'] == 'dry_run'
        assert output['total'] == 1
        assert output['valid'] == 1
        assert len(output['results']) == 1
        assert output['results'][0]['dry_run'] is True
    finally:
        os.unlink(path)


def test_cli_missing_file():
    """CLI with nonexistent file returns error JSON."""
    import subprocess

    result = subprocess.run(
        [sys.executable, '-m', 'guidance_write_cli', '/tmp/nonexistent_xyz.json'],
        capture_output=True, text=True,
        cwd='/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts',
        env={**os.environ, 'PYTHONPATH': '/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts:/home/faisal/EventMarketDB'},
    )
    output = json.loads(result.stdout)
    assert 'error' in output


def test_cli_empty_items():
    """CLI with empty items list."""
    import subprocess

    data = {'source_id': 'S', 'source_type': 'transcript', 'ticker': 'T', 'items': []}

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f)
        path = f.name

    try:
        result = subprocess.run(
            [sys.executable, '-m', 'guidance_write_cli', path],
            capture_output=True, text=True,
            cwd='/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts',
            env={**os.environ, 'PYTHONPATH': '/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts:/home/faisal/EventMarketDB'},
        )
        output = json.loads(result.stdout)
        assert output['total'] == 0
    finally:
        os.unlink(path)


def test_cli_batch_multiple_items():
    """CLI with multiple items in batch."""
    import subprocess

    items = [
        _make_raw_item(label='Revenue'),
        _make_raw_item(label='Gross Margin', low=45.0, high=46.0, unit_raw='percent'),
        _make_raw_item(label='EPS', low=3.20, high=3.40, unit_raw='$'),
    ]
    data = {'source_id': 'TEST_SRC', 'source_type': 'transcript', 'ticker': 'AAPL', 'items': items}

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f)
        path = f.name

    try:
        result = subprocess.run(
            [sys.executable, '-m', 'guidance_write_cli', path, '--dry-run'],
            capture_output=True, text=True,
            cwd='/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts',
            env={**os.environ, 'PYTHONPATH': '/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts:/home/faisal/EventMarketDB'},
        )
        output = json.loads(result.stdout)
        assert output['total'] == 3
        assert output['valid'] == 3
        assert len(output['results']) == 3
        # Each should have a unique ID
        ids = [r['id'] for r in output['results']]
        assert len(set(ids)) == 3
    finally:
        os.unlink(path)


# ── Period routing tests (build_guidance_period_id integration) ────────

def test_ensure_period_computes_from_llm_fields():
    """Item without period_u_id gets it computed from fiscal fields + fye_month."""
    item = _make_raw_item()
    del item['period_u_id']
    item['fiscal_year'] = 2025
    item['fiscal_quarter'] = 1

    _ensure_period(item, fye_month=9)  # AAPL FYE Sep

    assert item['period_u_id'] == 'gp_2024-10-01_2024-12-31'
    assert item['period_scope'] == 'quarter'
    assert item['time_type'] == 'duration'
    assert item['gp_start_date'] == '2024-10-01'
    assert item['gp_end_date'] == '2024-12-31'


def test_ensure_period_skips_when_present():
    """Item with existing period_u_id is not modified."""
    item = _make_raw_item(period_u_id='gp_2025-01-01_2025-03-31')
    _ensure_period(item, fye_month=12)
    assert item['period_u_id'] == 'gp_2025-01-01_2025-03-31'
    assert 'period_scope' not in item  # Not touched


def test_ensure_period_sentinel():
    """Sentinel class routes to sentinel u_id with null dates."""
    item = _make_raw_item()
    del item['period_u_id']
    item['sentinel_class'] = 'medium_term'

    _ensure_period(item, fye_month=12)

    assert item['period_u_id'] == 'gp_MT'
    assert item['gp_start_date'] is None
    assert item['gp_end_date'] is None
    assert item['period_scope'] == 'medium_term'


def test_ensure_period_missing_fye_raises():
    """Missing fye_month when item has no period_u_id raises ValueError."""
    item = _make_raw_item()
    del item['period_u_id']
    item['fiscal_year'] = 2025
    item['fiscal_quarter'] = 1

    try:
        _ensure_period(item, fye_month=None)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert 'fye_month' in str(e)


def test_ensure_ids_with_period_routing():
    """Full ID computation when item has no period_u_id — routing + IDs in one call."""
    item = _make_raw_item()
    del item['period_u_id']
    item['fiscal_year'] = 2025
    item['fiscal_quarter'] = 2

    result = _ensure_ids(item, fye_month=12)  # Dec FYE

    assert result['period_u_id'] == 'gp_2025-04-01_2025-06-30'
    assert result['guidance_id'] == 'guidance:revenue'
    assert 'gp_2025-04-01_2025-06-30' in result['guidance_update_id']
    assert result['period_scope'] == 'quarter'


def test_cli_dry_run_with_fye_month_and_routing():
    """Full CLI dry-run with LLM fields (no period_u_id) — period routed by CLI."""
    import subprocess

    item = {
        'label': 'Revenue',
        'source_id': 'TEST_SRC',
        'basis_norm': 'unknown',
        'segment': 'Total',
        'low': 94.0, 'mid': None, 'high': 97.0,
        'unit_raw': 'billion',
        'qualitative': None,
        'conditions': None,
        'given_date': '2025-01-30',
        'quote': 'We expect Q1 revenue between $94B and $97B',
        'fiscal_year': 2025,
        'fiscal_quarter': 1,
    }
    data = {
        'source_id': 'TEST_SRC',
        'source_type': 'transcript',
        'ticker': 'AAPL',
        'fye_month': 9,
        'items': [item],
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f)
        path = f.name

    try:
        result = subprocess.run(
            [sys.executable, '-m', 'guidance_write_cli', path, '--dry-run'],
            capture_output=True, text=True,
            cwd='/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts',
            env={**os.environ, 'PYTHONPATH': '/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts:/home/faisal/EventMarketDB'},
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        output = json.loads(result.stdout)
        assert output['mode'] == 'dry_run'
        assert output['valid'] == 1
        # The item should have been routed to gp_2024-10-01_2024-12-31 (AAPL Q1 FY2025)
        gu_id = output['results'][0]['id']
        assert 'gp_2024-10-01_2024-12-31' in gu_id
    finally:
        os.unlink(path)


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
