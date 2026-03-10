"""
Deterministic XBRL concept repair for reviewed guidance label slugs.

This module is intentionally conservative:
  - exact XBRL local-name matching only
  - ordered candidate lists for labels we have reviewed against live data
  - fail-closed on ambiguity
  - unknown labels pass through untouched
"""

import json
from typing import Iterable

from guidance_ids import slug


UNHANDLED_CONCEPT = object()
FORCE_NULL_CONCEPT = object()


# Reviewed, high-confidence labels only. Unknown labels must pass through
# unchanged so we do not override working agent behavior without evidence.
CONCEPT_CANDIDATES = {
    'dividend_per_share': (
        'CommonStockDividendsPerShareDeclared',
    ),
    'dividends_per_share': (
        'CommonStockDividendsPerShareDeclared',
    ),
    'eps': (
        'EarningsPerShareDiluted',
    ),
    'gross_margin': (
        'GrossProfit',
    ),
    'gross_profit': (
        'GrossProfit',
    ),
    'oine': (
        'NonoperatingIncomeExpense',
        'OtherNonoperatingIncomeExpense',
    ),
    'operating_expenses': (
        'OperatingExpenses',
    ),
    'opex': (
        'OperatingExpenses',
    ),
    'restructuring_cash_payments': (
        'PaymentsForRestructuring',
    ),
    'restructuring_charges': (
        'RestructuringCharges',
    ),
    'restructuring_costs': (
        'RestructuringCharges',
    ),
    'revenue': (
        'RevenueFromContractWithCustomerExcludingAssessedTax',
        'RevenueFromContractWithCustomerIncludingAssessedTax',
        'SalesRevenueNet',
        'Revenues',
    ),
    'tax_rate': (
        'EffectiveIncomeTaxRateContinuingOperations',
        'EffectiveIncomeTaxRate',
    ),
}


NULL_QNAME_LABELS = {
    'adjusted_ebitda',
    'ebitda',
    'fcf',
    'free_cash_flow',
    'operating_margin',
}

NULL_QNAME_SUFFIXES = (
    '_change',
    '_growth',
    '_yoy',
)


def load_concept_cache(ticker: str):
    """Load the raw warmup concept cache for a company. Missing cache is non-fatal."""
    try:
        with open(f'/tmp/concept_cache_{ticker}.json') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _local_name(qname: str) -> str:
    """Strip namespace prefix from an XBRL qname."""
    return qname.split(':', 1)[1] if ':' in qname else qname


def _as_usage(row) -> int:
    """Normalize usage values from JSON/Neo4j into sortable ints."""
    try:
        return int(row.get('usage') or 0)
    except (TypeError, ValueError):
        return 0


def resolve_xbrl_qname(label_slug: str, concept_rows: Iterable[dict]):
    """
    Resolve a reviewed label_slug to a single qname.

    Returns:
      - qname string when deterministically resolved
      - FORCE_NULL_CONCEPT for labels that should always be null
      - None for reviewed labels that remain unresolved in this company cache
      - UNHANDLED_CONCEPT for unknown labels (preserve existing agent value)
    """
    if not label_slug:
        return UNHANDLED_CONCEPT

    if label_slug in NULL_QNAME_LABELS or label_slug.endswith(NULL_QNAME_SUFFIXES):
        return FORCE_NULL_CONCEPT

    candidates = CONCEPT_CANDIDATES.get(label_slug)
    if not candidates:
        return UNHANDLED_CONCEPT

    for candidate in candidates:
        hits = [row for row in concept_rows if _local_name(row.get('qname', '')) == candidate]
        if not hits:
            continue

        hits.sort(key=lambda row: (-_as_usage(row), row.get('qname', '')))
        if len(hits) > 1 and _as_usage(hits[0]) == _as_usage(hits[1]):
            return None
        return hits[0].get('qname')

    return None


def apply_concept_resolution(items, concept_rows, logger=None):
    """
    Repair item xbrl_qname values using reviewed deterministic rules.

    Behavior is intentionally narrow:
      - fill missing qnames when we have a deterministic answer
      - clear invalid reviewed qnames when the reviewed answer is null
      - preserve existing non-null qnames that are already present in the cache
    """
    if not concept_rows:
        return items

    cache_qnames = {row.get('qname') for row in concept_rows if row.get('qname')}

    for item in items:
        label_slug = item.get('label_slug') or slug(item.get('label', ''))
        resolved = resolve_xbrl_qname(label_slug, concept_rows)
        if resolved is UNHANDLED_CONCEPT:
            continue

        current = item.get('xbrl_qname')
        if resolved is FORCE_NULL_CONCEPT:
            item['xbrl_qname'] = None
            continue

        if resolved is None:
            if not current or current not in cache_qnames:
                item['xbrl_qname'] = None
            continue

        if not current or current not in cache_qnames:
            item['xbrl_qname'] = resolved
            continue

        if current != resolved and logger:
            logger.warning(
                "Concept repair kept existing qname '%s' over deterministic '%s' for label_slug '%s'",
                current,
                resolved,
                label_slug,
            )

    return items
