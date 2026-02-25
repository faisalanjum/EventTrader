#!/usr/bin/env python3
"""
CLI wrapper for guidance_writer.py — called by the guidance-extract agent via Bash.

Usage:
    python3 guidance_write_cli.py <input.json> [--dry-run|--write]

Input JSON format:
{
    "source_id": "AAPL_2023-11-03T17.00.00-04.00",
    "source_type": "transcript",
    "ticker": "AAPL",
    "items": [
        {
            "label": "Revenue",
            "given_date": "2023-11-02",
            "period_u_id": "guidance_period_320193_duration_FY2024_Q1",
            "basis_norm": "unknown",
            "segment": "Total",
            "low": 89.0, "mid": null, "high": 93.0,
            "unit_raw": "billion",
            "qualitative": "similar to last year",
            "conditions": null,
            "quote": "We expect revenue...",
            "section": "CFO Prepared Remarks",
            "source_key": "full",
            "derivation": "explicit",
            "basis_raw": null,
            "period_type": "quarter",
            "fiscal_year": 2024,
            "fiscal_quarter": 1,
            "period_node_type": "duration",
            "aliases": [],
            "xbrl_qname": "us-gaap:Revenues",
            "member_u_ids": []
        }
    ]
}

Items do NOT need pre-computed IDs — this CLI calls build_guidance_ids() internally.
Items MAY include pre-computed IDs (guidance_id, guidance_update_id, evhash16, etc.)
which will be used as-is.

Output: JSON to stdout with write results.
"""

import json
import logging
import sys

# Set up paths before imports
sys.path.insert(0, "/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts")
sys.path.insert(0, "/home/faisal/EventMarketDB")

from guidance_ids import build_guidance_ids, build_period_u_id
import guidance_writer
from guidance_writer import write_guidance_batch, write_guidance_item

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _ensure_ids(item):
    """
    Compute IDs if not already present in the item.

    If guidance_update_id is already set, skip ID computation (agent pre-computed).
    Otherwise, call build_guidance_ids() to fill in:
        guidance_id, guidance_update_id, evhash16, label_slug, segment_slug,
        canonical_unit, canonical_low, canonical_mid, canonical_high
    """
    if item.get('guidance_update_id'):
        return item

    # Require fields for ID computation
    required = ['label', 'period_u_id', 'basis_norm']
    for f in required:
        if not item.get(f):
            raise ValueError(f"Cannot compute IDs: missing '{f}' in item")

    # source_id comes from the item or must be passed
    source_id = item.get('source_id')
    if not source_id:
        raise ValueError("Cannot compute IDs: missing 'source_id' in item")

    ids = build_guidance_ids(
        label=item['label'],
        source_id=source_id,
        period_u_id=item['period_u_id'],
        basis_norm=item['basis_norm'],
        segment=item.get('segment', 'Total'),
        low=item.get('low'),
        mid=item.get('mid'),
        high=item.get('high'),
        unit_raw=item.get('unit_raw', 'unknown'),
        qualitative=item.get('qualitative'),
        conditions=item.get('conditions'),
    )
    item.update(ids)
    return item


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: guidance_write_cli.py <input.json> [--dry-run|--write]"}))
        sys.exit(1)

    input_path = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else '--dry-run'
    dry_run = mode != '--write'

    # Load input
    try:
        with open(input_path) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"error": f"Failed to read {input_path}: {e}"}))
        sys.exit(1)

    source_id = data.get('source_id')
    source_type = data.get('source_type')
    ticker = data.get('ticker')
    items = data.get('items', [])

    if not source_id or not source_type or not ticker:
        print(json.dumps({"error": "Missing required top-level fields: source_id, source_type, ticker"}))
        sys.exit(1)

    if not items:
        print(json.dumps({"error": "No items to write", "total": 0}))
        sys.exit(0)

    # Inject source_id into each item (for ID computation if needed)
    for item in items:
        if 'source_id' not in item:
            item['source_id'] = source_id

    # Compute IDs for items that don't have them
    errors = []
    valid_items = []
    for i, item in enumerate(items):
        try:
            item = _ensure_ids(item)
            valid_items.append(item)
        except ValueError as e:
            errors.append({"index": i, "label": item.get('label', '?'), "error": str(e)})

    if dry_run:
        # Dry-run: validate + build params, no connection needed
        results = []
        for item in valid_items:
            result = write_guidance_item(None, item, source_id, source_type, ticker, dry_run=True)
            results.append(result)
        output = {
            "mode": "dry_run",
            "total": len(items),
            "valid": len(valid_items),
            "id_errors": errors,
            "results": results,
        }
    else:
        # Actual write: connect to Neo4j
        try:
            from neograph.Neo4jConnection import get_manager
            manager = get_manager()
        except Exception as e:
            print(json.dumps({"error": f"Neo4j connection failed: {e}"}))
            sys.exit(1)

        try:
            summary = write_guidance_batch(
                manager, valid_items, source_id, source_type, ticker, dry_run=False
            )
            summary['id_errors'] = errors
            summary['mode'] = 'write'
            output = summary
        finally:
            try:
                manager.close()
            except Exception:
                pass

    print(json.dumps(output, default=str))


if __name__ == '__main__':
    main()
