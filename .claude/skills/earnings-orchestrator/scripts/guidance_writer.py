"""
Guidance writer module — direct Cypher write path for Guidance + GuidanceUpdate nodes.

Implements §10 Step 3 of the Guidance System Implementation Spec (v3.0).
Uses direct Cypher MERGE via execute_cypher_query() (Decision #33).
No merge_nodes() / merge_relationships() / create_relationships().

Design decisions:
  - One atomic Cypher query per GuidanceUpdate item (node + all edges)
  - ON CREATE SET for created timestamp, SET for all other properties (latest write wins)
  - MATCH for pre-existing targets (source by label, company by ticker)
  - MERGE for nodes we create (Guidance, GuidanceUpdate, calendar-based GuidancePeriod)
  - No Context node (direct FOR_COMPANY edge)
  - No Unit node (canonical_unit is a property on GuidanceUpdate)
  - Member edges batched via single UNWIND query (not N separate calls)
  - Feature flag ENABLE_GUIDANCE_WRITES must be True for actual writes
  - Dry-run mode works regardless of feature flag
"""

import logging
import os
from datetime import datetime, timezone

from guidance_ids import _is_per_share_label, slug

logger = logging.getLogger(__name__)

# Feature flag — env var takes priority, then config file, then default off
_env = os.environ.get('ENABLE_GUIDANCE_WRITES', '').lower()
if _env in ('true', '1', 'yes'):
    ENABLE_GUIDANCE_WRITES = True
elif _env in ('false', '0', 'no'):
    ENABLE_GUIDANCE_WRITES = False
else:
    try:
        from config.feature_flags import ENABLE_GUIDANCE_WRITES
    except ImportError:
        ENABLE_GUIDANCE_WRITES = False

# ── Source type → Neo4j label mapping ─────────────────────────────────────

SOURCE_LABEL_MAP = {
    '8k': 'Report',
    '10q': 'Report',
    '10k': 'Report',
    'transcript': 'Transcript',
    'news': 'News',
}

# ── Validation ────────────────────────────────────────────────────────────

REQUIRED_ITEM_FIELDS = [
    'guidance_id', 'guidance_update_id', 'evhash16',
    'label', 'quote', 'given_date',
    'canonical_unit', 'period_u_id',
]


def _validate_item(item, source_id, source_type):
    """Validate required fields before write. Returns (ok, error_message)."""
    if not source_id:
        return False, "missing source_id"
    if not source_type:
        return False, "missing source_type"
    if source_type not in SOURCE_LABEL_MAP:
        return False, f"invalid source_type '{source_type}'; expected one of {sorted(SOURCE_LABEL_MAP)}"
    for field in REQUIRED_ITEM_FIELDS:
        val = item.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            return False, f"missing required field: {field}"

    # Guard A: per-share label with m_usd is the specific corruption this fix prevents.
    # Only check == 'm_usd', NOT != 'usd'. Per-share labels can legitimately have
    # non-usd units like 'percent_yoy' (EPS growth rate) or 'unknown' (qualitative
    # EPS guidance like "we expect strong EPS growth"). Blocking those would cause
    # false rejections at scale across 10,000 reports.
    label_slug = item.get('label_slug') or slug(item.get('label', ''))
    canonical_unit = item.get('canonical_unit', '')
    if _is_per_share_label(label_slug) and canonical_unit == 'm_usd':
        return False, (
            f"per-share label '{label_slug}' has canonical_unit='m_usd'"
            f" (expected 'usd' — per-share values must not be stored as millions)"
        )

    # Guard B: xbrl_qname indicates per-share but unit is m_usd (same corruption).
    # Also uses == 'm_usd' for consistency with Guard A. Catches cases where
    # the label doesn't match the classifier patterns but the XBRL concept clearly
    # says per-share. Includes PerDilutedShare and PerBasicShare because XBRL uses
    # the pattern 'IncomeLossFromContinuingOperationsPerDilutedShare' where
    # 'PerShare' is NOT a substring (verified against real DB concepts).
    xbrl_qname = item.get('xbrl_qname') or ''
    if xbrl_qname and (
        'PerShare' in xbrl_qname
        or 'PerUnit' in xbrl_qname
        or 'PerDilutedShare' in xbrl_qname
        or 'PerBasicShare' in xbrl_qname
    ):
        if canonical_unit == 'm_usd':
            return False, (
                f"xbrl_qname '{xbrl_qname}' indicates per-share but"
                f" canonical_unit='m_usd' (expected 'usd')"
            )

    return True, None


# ── Cypher query builders ─────────────────────────────────────────────────

def _build_core_query(source_type):
    """
    Build the single atomic Cypher MERGE query for one GuidanceUpdate.

    v3.0 architecture:
      1. Source matched by label (Report/Transcript/News) not bare {id:}
      2. Company matched by ticker; CIK derived from company node
      3. OPTIONAL MATCH before MERGE for accurate was_created detection
      4. Alias accumulation uses reduce-based dedupe
      5. GuidanceUpdate uses ON CREATE SET for created, SET for all other props (latest wins)
      6. No Context node — direct FOR_COMPANY edge
      7. No Unit node — canonical_unit is a property on GuidanceUpdate
      8. GuidancePeriod is calendar-based, company-agnostic (gp_ namespace)
    """
    source_label = SOURCE_LABEL_MAP[source_type]

    return f"""
// MATCH pre-existing targets (label-specific source, company by ticker)
MATCH (source:{source_label} {{id: $source_id}})
MATCH (company:Company {{ticker: $ticker}})

// Snapshot whether GuidanceUpdate already exists (for was_created)
OPTIONAL MATCH (existing:GuidanceUpdate {{id: $guidance_update_id}})

// MERGE nodes we own — Guidance
MERGE (g:Guidance {{id: $guidance_id}})
  ON CREATE SET g.label = $label,
                g.aliases = $aliases,
                g.created_date = $created_date
  ON MATCH SET g.aliases = reduce(
    acc = [], a IN (coalesce(g.aliases, []) + coalesce($aliases, []))
    | CASE WHEN a IS NULL OR a IN acc THEN acc ELSE acc + a END)

// GuidancePeriod (calendar-based, company-agnostic, MERGE on id for index use)
MERGE (gp:GuidancePeriod {{id: $period_u_id}})
  ON CREATE SET gp.u_id = $period_u_id,
                gp.start_date = $gp_start_date,
                gp.end_date = $gp_end_date

// GuidanceUpdate — MERGE on slot, SET all properties (latest write wins)
MERGE (gu:GuidanceUpdate {{id: $guidance_update_id}})
  ON CREATE SET gu.created = $created_ts
  SET gu.evhash16 = $evhash16,
      gu.given_date = $given_date,
      gu.period_scope = $period_scope,
      gu.time_type = $time_type,
      gu.fiscal_year = $fiscal_year,
      gu.fiscal_quarter = $fiscal_quarter,
      gu.segment = $segment,
      gu.low = $low,
      gu.mid = $mid,
      gu.high = $high,
      gu.canonical_unit = $canonical_unit,
      gu.basis_norm = $basis_norm,
      gu.basis_raw = $basis_raw,
      gu.derivation = $derivation,
      gu.qualitative = $qualitative,
      gu.quote = $quote,
      gu.section = $section,
      gu.source_key = $source_key,
      gu.source_type = $source_type,
      gu.conditions = $conditions,
      gu.xbrl_qname = $xbrl_qname,
      gu.unit_raw = $unit_raw

// Core edges (4 from GuidanceUpdate)
MERGE (gu)-[:UPDATES]->(g)
MERGE (gu)-[:FROM_SOURCE]->(source)
MERGE (gu)-[:FOR_COMPANY]->(company)
MERGE (gu)-[:HAS_PERIOD]->(gp)

RETURN gu.id AS id, existing IS NULL AS was_created
"""


def _build_concept_query():
    """
    Concept edge query (0..1). Links GuidanceUpdate to its XBRL Concept.

    LIMIT 1 handles multi-taxonomy ambiguity: multiple Concept nodes may share
    the same qname across taxonomy years. We link to one; the xbrl_qname
    property on GuidanceUpdate handles cross-taxonomy string matching.

    If the qname doesn't match any Concept node, the MATCH fails and
    no edge is created. This keeps concept failures from blocking the core write.
    """
    return """
MATCH (gu:GuidanceUpdate {id: $guidance_update_id})
MATCH (con:Concept {qname: $xbrl_qname})
WITH gu, con LIMIT 1
MERGE (gu)-[:MAPS_TO_CONCEPT]->(con)
RETURN con.qname AS linked_qname
"""


def _build_member_query():
    """
    Batched member edge query using UNWIND (single round-trip for 0..N members).

    If a member_u_id doesn't match any Member node, that row is silently skipped
    (MATCH fails for that element, no edge created). This keeps member failures
    from blocking the core write.
    """
    return """
MATCH (gu:GuidanceUpdate {id: $guidance_update_id})
UNWIND $member_u_ids AS member_u_id
MATCH (m:Member {u_id: member_u_id})
MERGE (gu)-[:MAPS_TO_MEMBER]->(m)
RETURN count(*) AS linked
"""


# ── Parameter assembly ────────────────────────────────────────────────────

def _build_params(item, source_id, source_type, ticker):
    """Assemble the Cypher parameter dict from a validated item."""
    now = datetime.now(timezone.utc).isoformat()
    today = now[:10]

    return {
        # Source + company
        'source_id': source_id,
        'source_type': source_type,
        'ticker': ticker,

        # Guidance node
        'guidance_id': item['guidance_id'],
        'label': item.get('label', ''),
        'aliases': item.get('aliases') or [],
        'created_date': today,

        # GuidancePeriod (calendar-based)
        'period_u_id': item['period_u_id'],
        'gp_start_date': item.get('gp_start_date'),
        'gp_end_date': item.get('gp_end_date'),

        # GuidanceUpdate
        'guidance_update_id': item['guidance_update_id'],
        'evhash16': item['evhash16'],
        'canonical_unit': item['canonical_unit'],
        'given_date': item['given_date'],
        'period_scope': item.get('period_scope', 'quarter'),
        'time_type': item.get('time_type', 'duration'),
        'fiscal_year': item.get('fiscal_year'),
        'fiscal_quarter': item.get('fiscal_quarter'),
        'segment': item.get('segment', 'Total'),
        'low': item.get('canonical_low'),
        'mid': item.get('canonical_mid'),
        'high': item.get('canonical_high'),
        'basis_norm': item.get('basis_norm', 'unknown'),
        'basis_raw': item.get('basis_raw'),
        'derivation': item.get('derivation', 'implied'),
        'qualitative': item.get('qualitative'),
        'quote': item['quote'],
        'section': item.get('section', ''),
        'source_key': item.get('source_key', ''),
        'conditions': item.get('conditions'),
        'xbrl_qname': item.get('xbrl_qname'),
        'unit_raw': item.get('unit_raw'),
        'created_ts': now,
    }


# ── Core write functions ──────────────────────────────────────────────────

def write_guidance_item(manager, item, source_id, source_type, ticker,
                        dry_run=True):
    """
    Write a single validated/canonicalized guidance item atomically to Neo4j.

    Args:
        manager:     Neo4jManager instance (execute_cypher_query)
        item:        dict — output of build_guidance_ids() merged with
                     extraction fields and caller-resolved period
        source_id:   id of the source node (Report/Transcript/News)
        source_type: one of '8k', '10q', '10k', 'transcript', 'news'
        ticker:      company ticker symbol
        dry_run:     True → validate + log only, no DB writes (default)

    Returns:
        dict {id, was_created, error, concept_links, member_links, dry_run?}
    """
    gu_id = item.get('guidance_update_id', '?')

    # 1. Validate
    ok, err = _validate_item(item, source_id, source_type)
    if not ok:
        logger.warning("Validation failed for %s: %s", gu_id, err)
        return {'id': gu_id, 'was_created': False, 'error': err,
                'concept_links': 0, 'member_links': 0}

    # 2. Build query + params (needed for dry-run logging too)
    query = _build_core_query(source_type)
    params = _build_params(item, source_id, source_type, ticker)

    # 3. Dry-run (works regardless of feature flag)
    if dry_run:
        logger.info("[DRY-RUN] Would write GuidanceUpdate %s", gu_id)
        return {'id': gu_id, 'was_created': None, 'error': None,
                'concept_links': 0, 'member_links': 0, 'dry_run': True}

    # 4. Feature flag gate (only for actual writes)
    if not ENABLE_GUIDANCE_WRITES:
        logger.info("ENABLE_GUIDANCE_WRITES is False; skipping write for %s",
                     gu_id)
        return {'id': gu_id, 'was_created': False,
                'error': 'writes_disabled', 'concept_links': 0,
                'member_links': 0}

    # 5. Execute core write
    try:
        record = manager.execute_cypher_query(query, params)
        if record is None:
            # MATCH for source or company returned no rows
            return {'id': gu_id, 'was_created': False,
                    'error': 'source_or_company_not_found',
                    'concept_links': 0, 'member_links': 0}
        was_created = record['was_created']
    except Exception as e:
        logger.error("Write failed for %s: %s", gu_id, e)
        return {'id': gu_id, 'was_created': False, 'error': str(e),
                'concept_links': 0, 'member_links': 0}

    # 6. Concept edge (optional, 0..1)
    #    Not gated on was_created — same self-healing rationale as members.
    concept_links = 0
    xbrl_qname = item.get('xbrl_qname')
    if xbrl_qname:
        try:
            concept_result = manager.execute_cypher_query(
                _build_concept_query(),
                {'guidance_update_id': gu_id, 'xbrl_qname': xbrl_qname},
            )
            concept_links = 1 if concept_result else 0
        except Exception as e:
            logger.warning("Concept link failed for %s: %s", gu_id, e)

    # 7. Member edges (optional, batched UNWIND)
    #    Not gated on was_created — MERGE for edges is idempotent, and
    #    gating would make transient member failures permanent (no self-heal
    #    on re-run since was_created would be False).
    member_links = 0
    member_u_ids = item.get('member_u_ids') or []
    if member_u_ids:
        try:
            member_result = manager.execute_cypher_query(
                _build_member_query(),
                {'guidance_update_id': gu_id, 'member_u_ids': member_u_ids},
            )
            member_links = member_result['linked'] if member_result else 0
        except Exception as e:
            logger.warning("Member link failed for %s: %s", gu_id, e)

    return {'id': gu_id, 'was_created': was_created, 'error': None,
            'concept_links': concept_links, 'member_links': member_links}


def write_guidance_batch(manager, items, source_id, source_type, ticker,
                         dry_run=True):
    """
    Write a batch of guidance items. Calls write_guidance_item() per item.

    Returns:
        dict {created, skipped, errors, concept_links, member_links, total, results}
    """
    summary = {
        'created': 0, 'skipped': 0, 'errors': 0,
        'concept_links': 0, 'member_links': 0,
        'total': len(items), 'results': [],
    }

    for item in items:
        result = write_guidance_item(
            manager, item, source_id, source_type, ticker, dry_run=dry_run,
        )
        summary['results'].append(result)

        if result.get('error'):
            summary['errors'] += 1
        elif result.get('was_created'):
            summary['created'] += 1
            summary['concept_links'] += result.get('concept_links', 0)
            summary['member_links'] += result.get('member_links', 0)
        else:
            summary['skipped'] += 1

    return summary


def create_guidance_constraints(manager):
    """
    Create uniqueness constraints for Guidance, GuidanceUpdate, and
    GuidancePeriod nodes. Pre-create 4 sentinel GuidancePeriod nodes.
    All operations are idempotent.
    """
    constraints = [
        ("CREATE CONSTRAINT guidance_id_unique IF NOT EXISTS "
         "FOR (g:Guidance) REQUIRE g.id IS UNIQUE"),
        ("CREATE CONSTRAINT guidance_update_id_unique IF NOT EXISTS "
         "FOR (gu:GuidanceUpdate) REQUIRE gu.id IS UNIQUE"),
        ("CREATE CONSTRAINT guidance_period_id_unique IF NOT EXISTS "
         "FOR (gp:GuidancePeriod) REQUIRE gp.id IS UNIQUE"),
    ]
    sentinels = [
        ("MERGE (gp:GuidancePeriod {id: 'gp_ST'}) "
         "SET gp.u_id = 'gp_ST', gp.start_date = null, gp.end_date = null"),
        ("MERGE (gp:GuidancePeriod {id: 'gp_MT'}) "
         "SET gp.u_id = 'gp_MT', gp.start_date = null, gp.end_date = null"),
        ("MERGE (gp:GuidancePeriod {id: 'gp_LT'}) "
         "SET gp.u_id = 'gp_LT', gp.start_date = null, gp.end_date = null"),
        ("MERGE (gp:GuidancePeriod {id: 'gp_UNDEF'}) "
         "SET gp.u_id = 'gp_UNDEF', gp.start_date = null, gp.end_date = null"),
    ]
    for cypher in constraints + sentinels:
        manager.execute_cypher_query(cypher, {})
    logger.info("Guidance constraints + GuidancePeriod sentinels ensured")
