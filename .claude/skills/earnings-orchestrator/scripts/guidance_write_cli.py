#!/usr/bin/env python3
"""
CLI wrapper for guidance_writer.py — called by the guidance-extract agent via Bash.

Usage:
    python3 guidance_write_cli.py <input.json> [--dry-run|--write]

Input JSON format:
{
    "source_id": "AAPL_2023-11-03T17.00",
    "source_type": "transcript",
    "ticker": "AAPL",
    "fye_month": 9,
    "items": [
        {
            "label": "Revenue",
            "given_date": "2023-11-02",
            "period_u_id": "gp_2023-10-01_2023-12-31",
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
            "period_scope": "quarter",
            "time_type": "duration",
            "fiscal_year": 2024,
            "fiscal_quarter": 1,
            "gp_start_date": "2023-10-01",
            "gp_end_date": "2023-12-31",
            "aliases": [],
            "xbrl_qname": "us-gaap:Revenues",
            "member_u_ids": []
        }
    ]
}

Items do NOT need pre-computed IDs — this CLI calls build_guidance_ids() internally.
Items MAY include pre-computed IDs (guidance_id, guidance_update_id, evhash16, etc.)
which will be used as-is.

If items lack period_u_id but have LLM extraction fields (fiscal_year, fiscal_quarter,
half, month, long_range_start_year, long_range_end_year, calendar_override, sentinel_class,
time_type), the CLI computes the period via build_guidance_period_id(). Requires fye_month
at the top level.

Output: JSON to stdout with write results.
"""

import json
import logging
import sys

# Set up paths before imports
sys.path.insert(0, "/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts")
sys.path.insert(0, "/home/faisal/EventMarketDB")

from guidance_ids import (
    build_guidance_ids,
    build_period_u_id,
    build_guidance_period_id,
    normalize_for_member_match,
    slug,
)
from concept_resolver import apply_concept_resolution, load_concept_cache, resolve_concept_family
import guidance_writer
from guidance_writer import write_guidance_batch, write_guidance_item, create_guidance_constraints

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Lazy connections for Steps A/B/C/D fiscal period resolution ──
import os
from datetime import date, timedelta

_neo4j_mgr = None
_redis_cli = None


def _get_neo4j():
    """Lazy Neo4j connection. Returns None on failure (graceful degradation)."""
    global _neo4j_mgr
    if _neo4j_mgr is None:
        try:
            from neograph.Neo4jConnection import get_manager
            _neo4j_mgr = get_manager()
        except Exception:
            pass
    return _neo4j_mgr


def _get_redis():
    """Lazy Redis connection. Returns None on failure (graceful degradation)."""
    global _redis_cli
    if _redis_cli is None:
        try:
            import redis
            _redis_cli = redis.Redis(
                host=os.environ.get('REDIS_HOST', '192.168.40.72'),
                port=int(os.environ.get('REDIS_PORT', '31379')),
                decode_responses=True)
            _redis_cli.ping()
        except Exception:
            _redis_cli = None
    return _redis_cli


def _lookup_existing_period(ticker, fiscal_year, fiscal_quarter):
    """Check Neo4j for existing GuidancePeriod for this fiscal identity.

    Deterministic: ORDER BY ref_count DESC, end_date DESC, u_id.
    Uses execute_cypher_query_all() which returns list[dict].
    """
    mgr = _get_neo4j()
    if not mgr:
        return None
    try:
        if fiscal_quarter is not None:
            result = mgr.execute_cypher_query_all("""
                MATCH (gu:GuidanceUpdate)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
                WHERE gu.fiscal_year = $fy AND gu.fiscal_quarter = $fq
                MATCH (gu)-[:HAS_PERIOD]->(gp:GuidancePeriod)
                WITH gp, count(gu) AS ref_count
                ORDER BY ref_count DESC, gp.end_date DESC, gp.u_id
                RETURN gp.u_id AS period_u_id, gp.start_date AS start_date,
                       gp.end_date AS end_date
                LIMIT 1
            """, {'ticker': ticker, 'fy': fiscal_year, 'fq': fiscal_quarter})
        else:
            result = mgr.execute_cypher_query_all("""
                MATCH (gu:GuidanceUpdate)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
                WHERE gu.fiscal_year = $fy AND gu.fiscal_quarter IS NULL
                  AND gu.period_scope = 'annual'
                MATCH (gu)-[:HAS_PERIOD]->(gp:GuidancePeriod)
                WITH gp, count(gu) AS ref_count
                ORDER BY ref_count DESC, gp.end_date DESC, gp.u_id
                RETURN gp.u_id AS period_u_id, gp.start_date AS start_date,
                       gp.end_date AS end_date
                LIMIT 1
            """, {'ticker': ticker, 'fy': fiscal_year})
        return result[0] if result else None
    except Exception:
        return None


def _lookup_sec_cache(ticker, fiscal_year, suffix):
    """Check Redis for SEC-derived exact dates. suffix is 'Q1'-'Q4' or 'FY'."""
    r = _get_redis()
    if not r:
        return None
    try:
        data = r.get(f"fiscal_quarter:{ticker}:{fiscal_year}:{suffix}")
        return json.loads(data) if data else None
    except Exception:
        return None


def _predict_from_prev_quarter(ticker, fiscal_year, fiscal_quarter):
    """Predict current quarter from previous quarter end + historical length.

    SEC inclusive convention: start = prev_end + 1d, end = start + length - 1.
    Returns None if prev-quarter data or length missing -> caller falls to Step D.
    """
    r = _get_redis()
    if not r:
        return None
    try:
        prev_q = fiscal_quarter - 1 if fiscal_quarter > 1 else 4
        prev_fy = fiscal_year if fiscal_quarter > 1 else fiscal_year - 1
        prev_data = r.get(f"fiscal_quarter:{ticker}:{prev_fy}:Q{prev_q}")
        length = r.get(f"fiscal_quarter_length:{ticker}:Q{fiscal_quarter}")
        if prev_data and length:
            prev = json.loads(prev_data)
            start = (date.fromisoformat(prev['end']) + timedelta(days=1)).isoformat()
            end = (date.fromisoformat(start) + timedelta(days=int(length) - 1)).isoformat()
            return {"start": start, "end": end}
    except Exception:
        pass
    return None


def _get_sec_corrected_fye(ticker):
    """Get SEC-adjusted FYE month from Redis cache."""
    r = _get_redis()
    if not r:
        return None
    try:
        data = r.get(f"fiscal_year_end:{ticker}")
        if data:
            return json.loads(data).get('month_adj')
    except Exception:
        pass
    return None


def _ensure_period(item, fye_month, ticker=None):
    """
    Compute period_u_id + GuidancePeriod fields if not already present.

    4-step cascade:
      A. Reuse existing period (first-write-wins dedup via Neo4j)
      B. SEC cache lookup (exact dates for filed quarters and annuals)
      C. Predict from previous quarter end + historical length (unfiled quarters)
      D. Corrected FYE math (last resort — sentinels, long-range, half, monthly, uncached)

    Steps A/B/C are additive. If all miss, Step D runs (same code as before).
    """
    if item.get('period_u_id'):
        return item

    fiscal_year = item.get('fiscal_year')
    fiscal_quarter = item.get('fiscal_quarter')

    # Guard: Steps A/B/C only handle standard quarter and annual duration items.
    is_standard_period = (
        item.get('time_type') != 'instant'
        and not item.get('half')
        and not item.get('month')
        and not item.get('sentinel_class')
        and not item.get('long_range_end_year')
    )

    # Step A: Reuse existing period (first-write-wins dedup)
    if is_standard_period and ticker and fiscal_year:
        existing = _lookup_existing_period(ticker, fiscal_year, fiscal_quarter)
        if existing:
            item['period_u_id'] = existing['period_u_id']
            item['period_scope'] = existing.get('period_scope', 'quarter' if fiscal_quarter else 'annual')
            item['time_type'] = existing.get('time_type', 'duration')
            item['gp_start_date'] = existing.get('start_date')
            item['gp_end_date'] = existing.get('end_date')
            return item

    # Step B: SEC cache lookup (quarter or annual)
    if is_standard_period and ticker and fiscal_year:
        suffix = f"Q{fiscal_quarter}" if fiscal_quarter else "FY"
        sec_dates = _lookup_sec_cache(ticker, fiscal_year, suffix)
        if sec_dates:
            item['period_u_id'] = f"gp_{sec_dates['start']}_{sec_dates['end']}"
            item['period_scope'] = 'quarter' if fiscal_quarter else 'annual'
            item['time_type'] = 'duration'
            item['gp_start_date'] = sec_dates['start']
            item['gp_end_date'] = sec_dates['end']
            return item

    # Step C: Predict from previous quarter end + historical length
    if is_standard_period and ticker and fiscal_year and fiscal_quarter:
        predicted = _predict_from_prev_quarter(ticker, fiscal_year, fiscal_quarter)
        if predicted:
            item['period_u_id'] = f"gp_{predicted['start']}_{predicted['end']}"
            item['period_scope'] = 'quarter'
            item['time_type'] = 'duration'
            item['gp_start_date'] = predicted['start']
            item['gp_end_date'] = predicted['end']
            return item

    # Step D: FYE math (last resort)
    effective_fye = fye_month
    if ticker:
        sec_fye = _get_sec_corrected_fye(ticker)
        if sec_fye is not None:
            effective_fye = sec_fye

    if effective_fye is None:
        raise ValueError("Cannot compute period: fye_month required at top level when items lack period_u_id")

    period = build_guidance_period_id(
        fye_month=effective_fye,
        fiscal_year=item.get('fiscal_year'),
        fiscal_quarter=item.get('fiscal_quarter'),
        half=item.get('half'),
        month=item.get('month'),
        long_range_start_year=item.get('long_range_start_year'),
        long_range_end_year=item.get('long_range_end_year'),
        calendar_override=item.get('calendar_override', False),
        sentinel_class=item.get('sentinel_class'),
        time_type=item.get('time_type'),
        label_slug=item.get('label_slug'),
    )
    item['period_u_id'] = period['u_id']
    item['period_scope'] = period['period_scope']
    item['time_type'] = period['time_type']
    item['gp_start_date'] = period['start_date']
    item['gp_end_date'] = period['end_date']
    return item


def _ensure_ids(item, fye_month=None, ticker=None):
    """
    Compute IDs if not already present in the item.

    If guidance_update_id is already set, skip ID computation (agent pre-computed).
    Otherwise:
      1. Compute period (if needed) via 4-step cascade (A/B/C/D)
      2. Compute IDs via build_guidance_ids()
    """
    if item.get('guidance_update_id'):
        return item

    # Step 1: Ensure period_u_id exists
    _ensure_period(item, fye_month, ticker)

    # Step 2: Require fields for ID computation
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
        unit_raw=item.get('unit_raw') or item.get('canonical_unit') or 'unknown',
        qualitative=item.get('qualitative'),
        conditions=item.get('conditions'),
    )
    item.update(ids)
    return item


_ALIAS_DIR = "/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts/segment_aliases"


def _load_segment_aliases(ticker):
    """Load optional per-ticker segment alias map from repo. Returns {} if missing."""
    try:
        with open(f'{_ALIAS_DIR}/{ticker}.json') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _apply_member_map(items, member_map, source_label="map", aliases=None):
    """Apply a normalized member map to items. Clears then repopulates member_u_ids."""
    aliases = aliases or {}
    matched = 0
    for item in items:
        seg = item.get('segment', 'Total')
        if seg and seg != 'Total':
            # Clear first — CLI is sole authority, discard any agent-provided IDs
            item['member_u_ids'] = []
            norm_seg = normalize_for_member_match(seg)
            # Prefer direct match; only fall back to alias if no direct hit
            if norm_seg not in member_map:
                norm_seg = aliases.get(norm_seg, norm_seg)
            if norm_seg in member_map:
                item['member_u_ids'] = member_map[norm_seg]
                matched += 1
    if matched:
        logger.warning("Member resolution (%s): resolved %d items", source_label, matched)
    return matched


def _build_live_member_map(manager, ticker):
    """Build member map via live CIK query (write-mode fallback when precomputed map missing)."""
    try:
        cik_rec = manager.execute_cypher_query(
            "MATCH (c:Company {ticker: $ticker}) RETURN c.cik AS cik LIMIT 1",
            {'ticker': ticker},
        )
        if not cik_rec:
            return None
        cik = str(cik_rec['cik'])
        cik_stripped = cik.lstrip('0') or '0'
        member_rows = manager.execute_cypher_query_all(
            "MATCH (m:Member) "
            "WHERE m.u_id STARTS WITH $cp OR m.u_id STARTS WITH $cpp "
            "RETURN m.label AS label, m.qname AS qname, "
            "       head(collect(m.u_id)) AS u_id",
            {'cp': cik_stripped + ':', 'cpp': cik + ':'},
        )
        member_map = {}
        for row in member_rows:
            if row['label']:
                norm = normalize_for_member_match(row['label'])
                if norm:
                    member_map.setdefault(norm, []).append(row['u_id'])
        return member_map
    except Exception as e:
        logger.warning("Live member map build failed (non-fatal): %s", e)
        return None


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
    fye_month = data.get('fye_month')  # Required when items lack period_u_id
    items = data.get('items', [])

    if not source_id or not source_type or not ticker:
        error_data = {"error": "Missing required top-level fields: source_id, source_type, ticker"}
        if 'company' in data or 'source' in data:
            error_data["hint"] = "Detected nested 'company'/'source' objects — use flat top-level fields instead. See enrichment-pass.md JSON example."
        print(json.dumps(error_data))
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
            item = _ensure_ids(item, fye_month=fye_month, ticker=ticker)
            valid_items.append(item)
        except ValueError as e:
            errors.append({"index": i, "label": item.get('label', '?'), "error": str(e)})

    # Deterministic concept repair fills reviewed null/invalid cases first.
    concept_rows = load_concept_cache(ticker)
    apply_concept_resolution(valid_items, concept_rows, logger=logger)

    # Concept inheritance: if Revenue(Total) has xbrl_qname but Revenue(iPhone) doesn't,
    # copy it over. Same metric = same concept regardless of segment.
    concept_map = {}
    for item in valid_items:
        label_key = item.get('label_slug') or slug(item.get('label', ''))
        if item.get('xbrl_qname') and label_key:
            concept_map.setdefault(label_key, item['xbrl_qname'])
    for item in valid_items:
        label_key = item.get('label_slug') or slug(item.get('label', ''))
        if not item.get('xbrl_qname') and label_key in concept_map:
            item['xbrl_qname'] = concept_map[label_key]

    # Concept family resolution: assign concept_family_qname to each item.
    # Runs after concept resolution + inheritance so xbrl_qname is finalized.
    for item in valid_items:
        label_slug = item.get('label_slug') or slug(item.get('label', ''))
        item['concept_family_qname'] = resolve_concept_family(
            label_slug, item.get('xbrl_qname')
        )

    # Member resolution: precomputed CIK-based member map (works in both dry-run and write).
    # Primary source — always overwrites agent-provided member_u_ids.
    # In write mode, if the map file is missing, falls back to live CIK query (self-healing).
    try:
        with open(f'/tmp/member_map_{ticker}.json') as f:
            member_map = json.load(f)
    except (OSError, json.JSONDecodeError):
        member_map = None

    # Optional per-ticker aliases for semantic renames (e.g. "creativecloud" → "digitalmedia")
    segment_aliases = _load_segment_aliases(ticker)

    if member_map is not None:
        _apply_member_map(valid_items, member_map, "precomputed map", aliases=segment_aliases)

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

        # Write-mode fallback: if precomputed member_map was missing, build it live.
        # This ensures write mode is self-healing even if warmup was skipped or /tmp cleaned.
        if member_map is None:
            live_map = _build_live_member_map(manager, ticker)
            if live_map is not None:
                _apply_member_map(valid_items, live_map, "live CIK fallback", aliases=segment_aliases)

        try:
            create_guidance_constraints(manager)
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

    # Write post-canonicalization sidecar for observability hooks (Obsidian capture).
    # Contains per-item post-_ensure_ids values so the hook can show what was actually
    # written, not the agent's pre-write interpretation.
    results_list = output.get('results', [])
    written_summary = []
    for i, item in enumerate(valid_items):
        result = results_list[i] if i < len(results_list) else {}
        written_summary.append({
            'label': item.get('label', ''),
            'segment': item.get('segment', 'Total'),
            'canonical_unit': item.get('canonical_unit', ''),
            'low': item.get('canonical_low'),
            'mid': item.get('canonical_mid'),
            'high': item.get('canonical_high'),
            'was_created': result.get('was_created'),
            'error': result.get('error'),
        })
    try:
        with open(f'/tmp/gu_written_{source_id}.json', 'w') as f:
            json.dump(written_summary, f, default=str)
    except OSError:
        pass  # Non-fatal — observability degradation only

    print(json.dumps(output, default=str))


if __name__ == '__main__':
    main()
