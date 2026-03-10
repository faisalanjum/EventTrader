#!/usr/bin/env python3
"""Tests for concept_resolver.py."""

import sys

sys.path.insert(0, "/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts")
sys.path.insert(0, "/home/faisal/EventMarketDB")

from concept_resolver import (
    FORCE_NULL_CONCEPT,
    UNHANDLED_CONCEPT,
    apply_concept_resolution,
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


def test_apply_preserves_existing_valid_qname():
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
    assert items[0]['xbrl_qname'] == 'us-gaap:Revenues'


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
