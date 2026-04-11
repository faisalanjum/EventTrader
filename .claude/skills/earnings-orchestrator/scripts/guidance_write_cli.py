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
    VALID_UNIT_KIND_HINTS,
    VALID_MONEY_MODE_HINTS,
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


def _classify_payload_origin(data, items):
    """Classify payload origin per spec §7.2. Returns 'extract_v2'|'readback'|'legacy_extract'."""
    origin = data.get('payload_origin')
    if origin in ('extract_v2', 'readback', 'legacy_extract'):
        return origin
    # Fallback inference (backward compat only)
    for item in items:
        if item.get('resolution_version') == 'v2':
            return 'readback'
    return 'legacy_extract'


def _validate_item_hints(item, payload_origin):
    """Pre-ID validation of V2 hint fields per spec §7.2. Raises ValueError on failure."""
    ukh = item.get('unit_kind_hint')
    mmh = item.get('money_mode_hint')

    if ukh and ukh not in VALID_UNIT_KIND_HINTS:
        raise ValueError(f"invalid unit_kind_hint: '{ukh}'")
    if mmh and mmh not in VALID_MONEY_MODE_HINTS:
        raise ValueError(f"invalid money_mode_hint: '{mmh}'")
    if mmh and (not ukh or ukh != 'money'):
        raise ValueError(f"money_mode_hint='{mmh}' present but unit_kind_hint='{ukh or '(absent)'}' is not money")

    if payload_origin == 'extract_v2':
        if not ukh:
            raise ValueError("extract_v2 payload requires unit_kind_hint")
        if ukh == 'money' and not mmh:
            raise ValueError("extract_v2 money item requires money_mode_hint")
        has_numeric = any(item.get(k) is not None for k in ('low', 'mid', 'high'))
        ur = item.get('unit_raw')
        if has_numeric and (not ur or not ur.strip() or ur.strip().lower() == 'unknown'):
            raise ValueError("extract_v2 numeric item requires non-empty unit_raw (not 'unknown')")


def _should_skip_pre_v2_readback(item, payload_origin, resolution_mode):
    """Skip gate for pre-V2 readback items in v2 mode per spec §7.5 control point."""
    if resolution_mode != 'v2' or payload_origin != 'readback':
        return False
    has_hints = bool(item.get('unit_kind_hint'))
    ur = item.get('unit_raw', '')
    has_surface = bool(ur and ur.strip() and ur.strip().lower() != 'unknown')
    has_v2_fallback = item.get('resolution_version') == 'v2'
    return not has_hints and not has_surface and not has_v2_fallback


def _ensure_ids(item, fye_month=None, ticker=None, resolution_mode='v1'):
    """
    Always recompute deterministic fields from current payload.

    V2 changes (spec §7.2):
      - No early-return on pre-computed IDs (CLI is sole authority)
      - Preserve period_u_id when already present
      - Fix unit_raw fallback (no canonical_unit proxy)
      - Pass V2 params to build_guidance_ids
    """
    # Step 1: Ensure period_u_id exists (preserved if already set)
    _ensure_period(item, fye_month, ticker)

    # Step 2: Require fields for ID computation
    required = ['label', 'period_u_id', 'basis_norm']
    for f in required:
        if not item.get(f):
            raise ValueError(f"Cannot compute IDs: missing '{f}' in item")

    source_id = item.get('source_id')
    if not source_id:
        raise ValueError("Cannot compute IDs: missing 'source_id' in item")

    # Step 3: Compute IDs (always recompute, overwrite stale pre-computed fields)
    ids = build_guidance_ids(
        label=item['label'],
        source_id=source_id,
        period_u_id=item['period_u_id'],
        basis_norm=item['basis_norm'],
        segment=item.get('segment', 'Total'),
        low=item.get('low'),
        mid=item.get('mid'),
        high=item.get('high'),
        unit_raw=item.get('unit_raw') or 'unknown',
        qualitative=item.get('qualitative'),
        conditions=item.get('conditions'),
        # V2 params
        unit_kind_hint=item.get('unit_kind_hint'),
        money_mode_hint=item.get('money_mode_hint'),
        quote=item.get('quote'),
        xbrl_qname=item.get('xbrl_qname'),
        existing_guidance_id=item.get('guidance_id'),
        existing_resolved_kind=item.get('resolved_kind'),
        existing_resolved_money_mode=item.get('resolved_money_mode'),
        existing_resolved_ratio_subtype=item.get('resolved_ratio_subtype'),
        existing_resolution_version=item.get('resolution_version'),
        resolution_mode=resolution_mode,
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

    # V2: read resolution mode from env (default v1 for Phase 0 safety)
    resolution_mode = os.environ.get('GUIDANCE_UNIT_RESOLUTION_MODE', 'v1')
    if resolution_mode not in ('v1', 'v2', 'shadow'):
        resolution_mode = 'v1'

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

    # V2: classify payload origin (spec §7.2)
    payload_origin = _classify_payload_origin(data, items)

    # ── Phase A: inject source_id, label_slug, period, hint validation ──
    # (concept repair needs label_slug; V2 ID computation needs repaired xbrl_qname)
    errors = []
    period_items = []
    for i, item in enumerate(items):
        try:
            # 1. Inject source_id
            if 'source_id' not in item:
                item['source_id'] = source_id

            # 2. Compute label_slug early
            if item.get('label'):
                item['label_slug'] = slug(item['label'])

            # 3. Ensure period (preserved if already set)
            _ensure_period(item, fye_month, ticker)

            # 4. Validate hints (pre-ID validation per spec §7.2)
            _validate_item_hints(item, payload_origin)

            period_items.append(item)
        except ValueError as e:
            errors.append({"index": i, "label": item.get('label', '?'), "error": str(e)})

    # ── Concept repair (batch — runs on label_slug, does NOT need IDs) ──
    concept_rows = load_concept_cache(ticker)
    apply_concept_resolution(period_items, concept_rows, logger=logger)

    # Concept inheritance: same metric = same concept regardless of segment
    concept_map = {}
    for item in period_items:
        label_key = item.get('label_slug') or slug(item.get('label', ''))
        if item.get('xbrl_qname') and label_key:
            concept_map.setdefault(label_key, item['xbrl_qname'])
    for item in period_items:
        label_key = item.get('label_slug') or slug(item.get('label', ''))
        if not item.get('xbrl_qname') and label_key in concept_map:
            item['xbrl_qname'] = concept_map[label_key]

    # ── Phase B: skip gate + compute IDs (xbrl_qname now repaired) ──
    valid_items = []
    for i, item in enumerate(period_items):
        try:
            # Skip gate: pre-V2 readback items in v2 mode (spec §7.5)
            if _should_skip_pre_v2_readback(item, payload_origin, resolution_mode):
                errors.append({
                    "index": i, "label": item.get('label', '?'),
                    "error": "pre_v2_readback_skip",
                })
                continue

            # Compute IDs + canonical fields (V2-aware)
            _ensure_ids(item, fye_month=fye_month, ticker=ticker,
                        resolution_mode=resolution_mode)
            valid_items.append(item)
        except ValueError as e:
            errors.append({"index": i, "label": item.get('label', '?'), "error": str(e)})

    # Concept family resolution (runs after IDs so xbrl_qname is finalized)
    for item in valid_items:
        label_slug_val = item.get('label_slug') or slug(item.get('label', ''))
        item['concept_family_qname'] = resolve_concept_family(
            label_slug_val, item.get('xbrl_qname')
        )

    # Member resolution: precomputed CIK-based member map
    try:
        with open(f'/tmp/member_map_{ticker}.json') as f:
            member_map = json.load(f)
    except (OSError, json.JSONDecodeError):
        member_map = None

    segment_aliases = _load_segment_aliases(ticker)
    if member_map is not None:
        _apply_member_map(valid_items, member_map, "precomputed map", aliases=segment_aliases)

    # ── Write ──
    if dry_run:
        results = []
        for item in valid_items:
            result = write_guidance_item(
                None, item, source_id, source_type, ticker,
                dry_run=True, resolution_mode=resolution_mode)
            results.append(result)
        output = {
            "mode": "dry_run",
            "resolution_mode": resolution_mode,
            "payload_origin": payload_origin,
            "total": len(items),
            "valid": len(valid_items),
            "id_errors": errors,
            "results": results,
        }
    else:
        try:
            from neograph.Neo4jConnection import get_manager
            manager = get_manager()
        except Exception as e:
            print(json.dumps({"error": f"Neo4j connection failed: {e}"}))
            sys.exit(1)

        if member_map is None:
            live_map = _build_live_member_map(manager, ticker)
            if live_map is not None:
                _apply_member_map(valid_items, live_map, "live CIK fallback", aliases=segment_aliases)

        try:
            create_guidance_constraints(manager)
            summary = write_guidance_batch(
                manager, valid_items, source_id, source_type, ticker,
                dry_run=False, resolution_mode=resolution_mode)
            summary['id_errors'] = errors
            summary['mode'] = 'write'
            summary['resolution_mode'] = resolution_mode
            summary['payload_origin'] = payload_origin
            output = summary
        finally:
            try:
                manager.close()
            except Exception:
                pass

    # ── Observability sidecar (extended for V2) ──
    results_list = output.get('results', [])
    written_summary = []
    for i, item in enumerate(valid_items):
        result = results_list[i] if i < len(results_list) else {}
        entry = {
            'label': item.get('label', ''),
            'segment': item.get('segment', 'Total'),
            'canonical_unit': item.get('canonical_unit', ''),
            'low': item.get('canonical_low'),
            'mid': item.get('canonical_mid'),
            'high': item.get('canonical_high'),
            'was_created': result.get('was_created'),
            'error': result.get('error'),
        }
        # V2 additive fields
        if resolution_mode in ('v2', 'shadow'):
            entry['unit_kind_hint'] = item.get('unit_kind_hint')
            entry['money_mode_hint'] = item.get('money_mode_hint')
            entry['resolved_kind'] = item.get('resolved_kind')
            entry['resolved_money_mode'] = item.get('resolved_money_mode')
            entry['resolved_ratio_subtype'] = item.get('resolved_ratio_subtype')
            entry['resolution_version'] = item.get('resolution_version')
        if resolution_mode == 'shadow' and item.get('shadow_v2'):
            entry['shadow_v2'] = item['shadow_v2']
        written_summary.append(entry)
    try:
        with open(f'/tmp/gu_written_{source_id}.json', 'w') as f:
            json.dump(written_summary, f, default=str)
    except OSError:
        pass  # Non-fatal — observability degradation only

    print(json.dumps(output, default=str))


if __name__ == '__main__':
    main()
