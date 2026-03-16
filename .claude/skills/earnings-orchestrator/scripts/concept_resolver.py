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
    'capex': (
        'PaymentsToAcquirePropertyPlantAndEquipment',
        'CapitalExpenditure',
    ),
    'capital_expenditures': (
        'PaymentsToAcquirePropertyPlantAndEquipment',
        'CapitalExpenditure',
    ),
    'capital_spending': (
        'PaymentsToAcquirePropertyPlantAndEquipment',
        'CapitalExpenditure',
    ),
    'cash_from_operations': (
        'NetCashProvidedByOperatingActivities',
    ),
    'cogs': (
        'CostOfGoodsAndServicesSold',
        'CostOfRevenue',
        'CostOfGoodsSold',
    ),
    'cost_of_goods_sold': (
        'CostOfGoodsAndServicesSold',
        'CostOfRevenue',
        'CostOfGoodsSold',
    ),
    'cost_of_revenue': (
        'CostOfGoodsAndServicesSold',
        'CostOfRevenue',
        'CostOfGoodsSold',
    ),
    'd_a': (
        'DepreciationDepletionAndAmortization',
        'DepreciationAndAmortization',
        'Depreciation',
    ),
    'depreciation_and_amortization': (
        'DepreciationDepletionAndAmortization',
        'DepreciationAndAmortization',
        'Depreciation',
    ),
    'basic_eps': (
        'EarningsPerShareBasic',
    ),
    'basic_shares': (
        'CommonStockSharesOutstanding',
    ),
    'cash': (
        'CashAndCashEquivalentsAtCarryingValue',
    ),
    'cash_and_equivalents': (
        'CashAndCashEquivalentsAtCarryingValue',
    ),
    'diluted_shares': (
        'WeightedAverageNumberOfDilutedSharesOutstanding',
    ),
    'dividend_per_share': (
        'CommonStockDividendsPerShareDeclared',
        'CommonStockDividendsPerShareCashPaid',
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
    'income_tax': (
        'IncomeTaxExpenseBenefit',
    ),
    'interest_expense': (
        'InterestExpense',
        'InterestExpenseDebt',
    ),
    'interest_income': (
        'InvestmentIncomeInterest',
    ),
    'long_term_debt': (
        'LongTermDebt',
        'LongTermDebtNoncurrent',
    ),
    'net_income': (
        'NetIncomeLoss',
        'ProfitLoss',
    ),
    'oine': (
        'NonoperatingIncomeExpense',
        'OtherNonoperatingIncomeExpense',
    ),
    'operating_cash_flow': (
        'NetCashProvidedByOperatingActivities',
    ),
    'pp_e': (
        'PropertyPlantAndEquipmentNet',
    ),
    'ppe': (
        'PropertyPlantAndEquipmentNet',
    ),
    'operating_expenses': (
        'OperatingExpenses',
    ),
    'operating_income': (
        'OperatingIncomeLoss',
    ),
    'opex': (
        'OperatingExpenses',
    ),
    'r_d': (
        'ResearchAndDevelopmentExpense',
    ),
    'rd': (
        'ResearchAndDevelopmentExpense',
    ),
    'research_and_development': (
        'ResearchAndDevelopmentExpense',
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
    'sbc': (
        'ShareBasedCompensation',
        'AllocatedShareBasedCompensationExpense',
    ),
    'share_repurchase': (
        'PaymentsForRepurchaseOfCommonStock',
    ),
    'share_repurchases': (
        'PaymentsForRepurchaseOfCommonStock',
    ),
    'selling_general_and_administrative': (
        'SellingGeneralAndAdministrativeExpense',
    ),
    'sg_a': (
        'SellingGeneralAndAdministrativeExpense',
    ),
    'sga': (
        'SellingGeneralAndAdministrativeExpense',
    ),
    'share_count': (
        'WeightedAverageNumberOfDilutedSharesOutstanding',
    ),
    'shares_outstanding': (
        'WeightedAverageNumberOfDilutedSharesOutstanding',
    ),
    'stock_based_compensation': (
        'ShareBasedCompensation',
        'AllocatedShareBasedCompensationExpense',
    ),
    'tax_expense': (
        'IncomeTaxExpenseBenefit',
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
      - overwrite agent qnames with the deterministic value (consistency > agent choice)
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

        if current != resolved:
            if current and current in cache_qnames and logger:
                logger.warning(
                    "Concept repair overwrote agent qname '%s' with deterministic '%s' for label_slug '%s'",
                    current,
                    resolved,
                    label_slug,
                )
            item['xbrl_qname'] = resolved

    return items


# ── Concept Family Resolution ─────────────────────────────────────────────
# Maps derived/composite metrics to their canonical XBRL concept family anchor.
# concept_family_qname is a GuidanceUpdate property: the single best XBRL concept
# this metric relates to, even when no exact xbrl_qname exists.

CONCEPT_FAMILY = {
    # Revenue
    'revenue': 'us-gaap:Revenues',
    # Profitability
    'gross_margin': 'us-gaap:GrossProfit',
    'gross_profit': 'us-gaap:GrossProfit',
    'operating_margin': 'us-gaap:OperatingIncomeLoss',
    'operating_income': 'us-gaap:OperatingIncomeLoss',
    'ebitda': 'us-gaap:OperatingIncomeLoss',
    'adjusted_ebitda': 'us-gaap:OperatingIncomeLoss',
    'net_income': 'us-gaap:NetIncomeLoss',
    # EPS
    'eps': 'us-gaap:EarningsPerShareDiluted',
    'basic_eps': 'us-gaap:EarningsPerShareDiluted',
    # Cash flow
    'fcf': 'us-gaap:NetCashProvidedByOperatingActivities',
    'free_cash_flow': 'us-gaap:NetCashProvidedByOperatingActivities',
    'operating_cash_flow': 'us-gaap:NetCashProvidedByOperatingActivities',
    'cash_from_operations': 'us-gaap:NetCashProvidedByOperatingActivities',
    # Expenses
    'opex': 'us-gaap:OperatingExpenses',
    'operating_expenses': 'us-gaap:OperatingExpenses',
    # Tax
    'tax_rate': 'us-gaap:EffectiveIncomeTaxRateContinuingOperations',
    'tax_expense': 'us-gaap:IncomeTaxExpenseBenefit',
    # Other
    'restructuring_cash_payments': 'us-gaap:PaymentsForRestructuring',
}

FAMILY_PREFIXES = ('adjusted_', 'non_gaap_', 'gaap_', 'basic_', 'diluted_')
FAMILY_SUFFIXES = ('_growth', '_change', '_yoy')


def resolve_concept_family(label_slug, xbrl_qname=None):
    """
    Resolve a label_slug to its canonical XBRL concept family anchor.

    Resolution order:
      1. Direct lookup in CONCEPT_FAMILY
      2. Strip suffix (_growth, _change, _yoy), then prefix (adjusted_, non_gaap_, etc.)
      3. Try lookup on stripped base
      4. Fallback to exact xbrl_qname (metric is its own family)
      5. Else null
    """
    if not label_slug:
        return xbrl_qname

    # 1. Direct lookup
    if label_slug in CONCEPT_FAMILY:
        return CONCEPT_FAMILY[label_slug]

    # 2. Strip suffix, then prefix
    base = label_slug
    for suffix in FAMILY_SUFFIXES:
        if base.endswith(suffix):
            base = base[:-len(suffix)]
            break
    for prefix in FAMILY_PREFIXES:
        if base.startswith(prefix):
            base = base[len(prefix):]
            break

    # 3. Try lookup on stripped base
    if base != label_slug and base in CONCEPT_FAMILY:
        return CONCEPT_FAMILY[base]

    # 4. Fallback to exact xbrl_qname
    return xbrl_qname
