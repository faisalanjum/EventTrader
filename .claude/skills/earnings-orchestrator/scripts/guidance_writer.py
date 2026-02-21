"""
Guidance writer module — direct Cypher write path for Guidance + GuidanceUpdate nodes.

Implements §10 Step 3 of the Guidance System Implementation Spec (v2.2).
Uses direct Cypher MERGE via execute_cypher_query() (Decision #33).
No merge_nodes() / merge_relationships() / create_relationships().

Design decisions:
  - One atomic Cypher query per GuidanceUpdate item (node + all edges)
  - ON CREATE SET only for GuidanceUpdate (idempotent no-op on re-run)
  - MATCH for pre-existing targets (source by label, company by ticker)
  - MERGE for nodes we create (Guidance, GuidanceUpdate, synthetic Context, Period, Unit)
  - Member edges batched via single UNWIND query (not N separate calls)
  - Feature flag ENABLE_GUIDANCE_WRITES must be True for actual writes
  - Dry-run mode works regardless of feature flag
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Feature flag — safe import with fallback
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
    'canonical_unit', 'period_u_id', 'ctx_u_id', 'unit_u_id',
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
    return True, None


# ── Cypher query builders ─────────────────────────────────────────────────

def _build_core_query(source_type):
    """
    Build the single atomic Cypher MERGE query for one GuidanceUpdate.

    Fixes vs original plan:
      1. Source matched by label (Report/Transcript/News) not bare {id:}
      2. Company matched by ticker; CIK derived from company node
      3. OPTIONAL MATCH before MERGE for accurate was_created detection
      4. Alias accumulation uses reduce-based dedupe (spec §10 line 818)
      5. GuidanceUpdate uses ON CREATE SET only (idempotent)
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

// Period
MERGE (p:Period {{u_id: $period_u_id}})
  ON CREATE SET p.id = $period_u_id,
                p.period_type = $period_node_type,
                p.start_date = $start_date,
                p.end_date = $end_date

// Context (synthetic, XBRL-compatible)
MERGE (ctx:Context {{u_id: $ctx_u_id}})
  ON CREATE SET ctx.id = $ctx_u_id,
                ctx.context_id = $ctx_u_id,
                ctx.cik = company.cik,
                ctx.period_u_id = $period_u_id,
                ctx.member_u_ids = [],
                ctx.dimension_u_ids = []
MERGE (ctx)-[:HAS_PERIOD]->(p)
MERGE (ctx)-[:FOR_COMPANY]->(company)

// Unit (canonical guidance unit)
MERGE (u:Unit {{u_id: $unit_u_id}})
  ON CREATE SET u.id = $unit_u_id,
                u.canonical_unit = $canonical_unit

// GuidanceUpdate — ON CREATE SET only (idempotent no-op on re-run)
MERGE (gu:GuidanceUpdate {{id: $guidance_update_id}})
  ON CREATE SET gu.evhash16 = $evhash16,
                gu.given_date = $given_date,
                gu.period_type = $period_type,
                gu.fiscal_year = $fiscal_year,
                gu.fiscal_quarter = $fiscal_quarter,
                gu.segment = $segment,
                gu.low = $low,
                gu.mid = $mid,
                gu.high = $high,
                gu.unit = $canonical_unit,
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
                gu.created = $created_ts

// Core edges
MERGE (gu)-[:UPDATES]->(g)
MERGE (gu)-[:FROM_SOURCE]->(source)
MERGE (gu)-[:IN_CONTEXT]->(ctx)
MERGE (gu)-[:HAS_PERIOD]->(p)
MERGE (gu)-[:HAS_UNIT]->(u)

RETURN gu.id AS id, existing IS NULL AS was_created
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

        # Period
        'period_u_id': item['period_u_id'],
        'period_node_type': item.get('period_node_type', 'duration'),
        'start_date': item.get('start_date'),
        'end_date': item.get('end_date'),

        # Context
        'ctx_u_id': item['ctx_u_id'],

        # Unit
        'unit_u_id': item['unit_u_id'],
        'canonical_unit': item['canonical_unit'],

        # GuidanceUpdate
        'guidance_update_id': item['guidance_update_id'],
        'evhash16': item['evhash16'],
        'given_date': item['given_date'],
        'period_type': item.get('period_type', 'quarter'),
        'fiscal_year': item.get('fiscal_year'),
        'fiscal_quarter': item.get('fiscal_quarter'),
        'segment': item.get('segment', 'Total'),
        'low': item.get('canonical_low'),
        'mid': item.get('canonical_mid'),
        'high': item.get('canonical_high'),
        'basis_norm': item.get('basis_norm', 'unknown'),
        'basis_raw': item.get('basis_raw'),
        'derivation': item.get('derivation', 'explicit'),
        'qualitative': item.get('qualitative'),
        'quote': item['quote'],
        'section': item.get('section', ''),
        'source_key': item.get('source_key', ''),
        'conditions': item.get('conditions'),
        'xbrl_qname': item.get('xbrl_qname'),
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
                     extraction fields and caller-resolved period/context/unit
        source_id:   id of the source node (Report/Transcript/News)
        source_type: one of '8k', '10q', '10k', 'transcript', 'news'
        ticker:      company ticker symbol
        dry_run:     True → validate + log only, no DB writes (default)

    Returns:
        dict {id, was_created, error, member_links, dry_run?}
    """
    gu_id = item.get('guidance_update_id', '?')

    # 1. Validate
    ok, err = _validate_item(item, source_id, source_type)
    if not ok:
        logger.warning("Validation failed for %s: %s", gu_id, err)
        return {'id': gu_id, 'was_created': False, 'error': err,
                'member_links': 0}

    # 2. Build query + params (needed for dry-run logging too)
    query = _build_core_query(source_type)
    params = _build_params(item, source_id, source_type, ticker)

    # 3. Dry-run (works regardless of feature flag)
    if dry_run:
        logger.info("[DRY-RUN] Would write GuidanceUpdate %s", gu_id)
        return {'id': gu_id, 'was_created': None, 'error': None,
                'member_links': 0, 'dry_run': True}

    # 4. Feature flag gate (only for actual writes)
    if not ENABLE_GUIDANCE_WRITES:
        logger.info("ENABLE_GUIDANCE_WRITES is False; skipping write for %s",
                     gu_id)
        return {'id': gu_id, 'was_created': False,
                'error': 'writes_disabled', 'member_links': 0}

    # 5. Execute core write
    try:
        record = manager.execute_cypher_query(query, params)
        if record is None:
            # MATCH for source or company returned no rows
            return {'id': gu_id, 'was_created': False,
                    'error': 'source_or_company_not_found', 'member_links': 0}
        was_created = record['was_created']
    except Exception as e:
        logger.error("Write failed for %s: %s", gu_id, e)
        return {'id': gu_id, 'was_created': False, 'error': str(e),
                'member_links': 0}

    # 6. Member edges (optional, batched UNWIND)
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
            'member_links': member_links}


def write_guidance_batch(manager, items, source_id, source_type, ticker,
                         dry_run=True):
    """
    Write a batch of guidance items. Calls write_guidance_item() per item.

    Returns:
        dict {created, skipped, errors, member_links, total, results}
    """
    summary = {
        'created': 0, 'skipped': 0, 'errors': 0,
        'member_links': 0, 'total': len(items), 'results': [],
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
            summary['member_links'] += result.get('member_links', 0)
        else:
            summary['skipped'] += 1

    return summary


def create_guidance_constraints(manager):
    """
    Create uniqueness constraints for Guidance and GuidanceUpdate nodes.
    Idempotent — uses IF NOT EXISTS. Context and Period constraints already
    exist from XBRL pipeline.
    """
    constraints = [
        ("CREATE CONSTRAINT guidance_id_unique IF NOT EXISTS "
         "FOR (g:Guidance) REQUIRE g.id IS UNIQUE"),
        ("CREATE CONSTRAINT guidance_update_id_unique IF NOT EXISTS "
         "FOR (gu:GuidanceUpdate) REQUIRE gu.id IS UNIQUE"),
    ]
    for cypher in constraints:
        manager.execute_cypher_query(cypher, {})
    logger.info("Guidance constraints ensured")
