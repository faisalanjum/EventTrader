#!/usr/bin/env python3
"""Tests for concept_resolver.py."""

import sys

sys.path.insert(0, "/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts")
sys.path.insert(0, "/home/faisal/EventMarketDB")

from concept_resolver import (
    FORCE_NULL_CONCEPT,
    UNHANDLED_CONCEPT,
    apply_concept_resolution,
    resolve_concept_family,
    resolve_xbrl_qname,
)


def _rows(*items):
    """Helper to build concept-cache rows."""
    return [{'qname': qname, 'usage': usage} for qname, usage in items]


def test_revenue_prefers_reviewed_primary_concept():
    rows = _rows(
        ('us-gaap:ContractWithCustomerLiabilityRevenueRecognized', 13),
        ('us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax', 13),
    )
    assert (
        resolve_xbrl_qname('revenue', rows)
        == 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax'
    )


def test_tax_rate_ignores_reconciliation_noise():
    rows = _rows(
        ('us-gaap:EffectiveIncomeTaxRateReconciliationFdiiAmount', 3),
        ('us-gaap:EffectiveIncomeTaxRateReconciliationShareBasedCompensationExcessTaxBenefitAmount', 3),
        ('us-gaap:EffectiveIncomeTaxRateContinuingOperations', 2),
    )
    assert (
        resolve_xbrl_qname('tax_rate', rows)
        == 'us-gaap:EffectiveIncomeTaxRateContinuingOperations'
    )


def test_oine_falls_back_to_other_nonoperating():
    rows = _rows(
        ('us-gaap:OtherNonoperatingIncomeExpense', 5),
    )
    assert resolve_xbrl_qname('oine', rows) == 'us-gaap:OtherNonoperatingIncomeExpense'


def test_growth_suffix_is_null_by_policy():
    rows = _rows(
        ('us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax', 10),
    )
    assert resolve_xbrl_qname('revenue_growth', rows) is FORCE_NULL_CONCEPT


def test_unknown_label_passes_through():
    rows = _rows(
        ('us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax', 10),
    )
    assert resolve_xbrl_qname('average_revenue_per_user', rows) is UNHANDLED_CONCEPT


def test_ambiguity_fails_closed():
    rows = _rows(
        ('foo:GrossProfit', 7),
        ('bar:GrossProfit', 7),
    )
    assert resolve_xbrl_qname('gross_margin', rows) is None


def test_apply_fills_missing_qname():
    items = [{'label': 'Tax Rate', 'label_slug': 'tax_rate', 'xbrl_qname': None}]
    rows = _rows(
        ('us-gaap:EffectiveIncomeTaxRateContinuingOperations', 2),
    )
    apply_concept_resolution(items, rows)
    assert items[0]['xbrl_qname'] == 'us-gaap:EffectiveIncomeTaxRateContinuingOperations'


def test_apply_overwrites_with_deterministic_qname():
    """Deterministic resolver always wins over agent-provided qname, even if agent's is cache-valid."""
    items = [{
        'label': 'Revenue',
        'label_slug': 'revenue',
        'xbrl_qname': 'us-gaap:Revenues',
    }]
    rows = _rows(
        ('us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax', 10),
        ('us-gaap:Revenues', 8),
    )
    apply_concept_resolution(items, rows)
    assert items[0]['xbrl_qname'] == 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax'


def test_apply_replaces_invalid_existing_qname():
    items = [{
        'label': 'Gross Margin',
        'label_slug': 'gross_margin',
        'xbrl_qname': 'us-gaap:DefinitelyNotInCache',
    }]
    rows = _rows(
        ('us-gaap:GrossProfit', 10),
    )
    apply_concept_resolution(items, rows)
    assert items[0]['xbrl_qname'] == 'us-gaap:GrossProfit'


def test_apply_clears_qname_for_null_policy_label():
    items = [{
        'label': 'Revenue Growth',
        'label_slug': 'revenue_growth',
        'xbrl_qname': 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax',
    }]
    rows = _rows(
        ('us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax', 10),
    )
    apply_concept_resolution(items, rows)
    assert items[0]['xbrl_qname'] is None


# ── concept_family tests ──────────────────────────────────────────────────

def test_family_direct_lookup():
    """Direct table hit: revenue → us-gaap:Revenues."""
    assert resolve_concept_family('revenue') == 'us-gaap:Revenues'


def test_family_ebitda_maps_to_operating_income():
    """EBITDA is an operating profitability proxy, not net income."""
    assert resolve_concept_family('ebitda') == 'us-gaap:OperatingIncomeLoss'
    assert resolve_concept_family('adjusted_ebitda') == 'us-gaap:OperatingIncomeLoss'


def test_family_fcf_maps_to_operating_cash_flow():
    """FCF = Operating Cash Flow - CapEx, so family is OCF."""
    assert resolve_concept_family('fcf') == 'us-gaap:NetCashProvidedByOperatingActivities'
    assert resolve_concept_family('free_cash_flow') == 'us-gaap:NetCashProvidedByOperatingActivities'


def test_family_suffix_strip():
    """revenue_growth strips _growth, resolves to revenue family."""
    assert resolve_concept_family('revenue_growth') == 'us-gaap:Revenues'
    assert resolve_concept_family('eps_yoy') == 'us-gaap:EarningsPerShareDiluted'
    assert resolve_concept_family('operating_cash_flow_change') == 'us-gaap:NetCashProvidedByOperatingActivities'


def test_family_prefix_strip():
    """non_gaap_eps strips non_gaap_, resolves to eps family."""
    assert resolve_concept_family('non_gaap_eps') == 'us-gaap:EarningsPerShareDiluted'
    assert resolve_concept_family('diluted_eps') == 'us-gaap:EarningsPerShareDiluted'
    assert resolve_concept_family('gaap_revenue') == 'us-gaap:Revenues'


def test_family_prefix_and_suffix_strip():
    """adjusted_ebitda_growth strips _growth then adjusted_, resolves via ebitda → direct hit."""
    # After suffix strip: adjusted_ebitda → direct lookup hit (in CONCEPT_FAMILY)
    # Actually: base starts as adjusted_ebitda_growth, strip _growth → adjusted_ebitda
    # adjusted_ebitda is in CONCEPT_FAMILY directly? No wait — let me think:
    # base = 'adjusted_ebitda_growth' → strip _growth → 'adjusted_ebitda'
    # strip prefix adjusted_ → 'ebitda'
    # base != label_slug → lookup 'ebitda' → hit
    assert resolve_concept_family('adjusted_ebitda_growth') == 'us-gaap:OperatingIncomeLoss'
    assert resolve_concept_family('non_gaap_operating_margin_growth') == 'us-gaap:OperatingIncomeLoss'


def test_family_fallback_to_xbrl_qname():
    """Unknown label with xbrl_qname falls back to that qname as its own family."""
    assert (
        resolve_concept_family('dividend_per_share', 'us-gaap:CommonStockDividendsPerShareDeclared')
        == 'us-gaap:CommonStockDividendsPerShareDeclared'
    )


def test_family_unknown_no_qname_is_null():
    """Unknown label without xbrl_qname → None."""
    assert resolve_concept_family('crpo_growth') is None
    assert resolve_concept_family('subscription_support_revenue_growth') is None


def test_family_empty_label_returns_qname():
    """Empty/None label returns xbrl_qname fallback."""
    assert resolve_concept_family('', 'us-gaap:Revenues') == 'us-gaap:Revenues'
    assert resolve_concept_family(None, 'us-gaap:Revenues') == 'us-gaap:Revenues'
    assert resolve_concept_family(None) is None


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
