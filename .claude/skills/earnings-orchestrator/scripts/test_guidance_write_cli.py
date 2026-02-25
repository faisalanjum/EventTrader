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

from guidance_write_cli import _ensure_ids


# ── _ensure_ids tests ────────────────────────────────────────────────────

def _make_raw_item(**overrides):
    """Build a raw extraction item (no pre-computed IDs)."""
    item = {
        'label': 'Revenue',
        'source_id': 'TEST_SRC',
        'period_u_id': 'guidance_period_320193_duration_FY2025_Q1',
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
    assert result['guidance_update_id'].startswith('gu:TEST_SRC:revenue:')


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
