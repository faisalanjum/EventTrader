from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from compare_corporate_actions import (
    dividend_core,
    dividend_production_id,
    dividend_production_id_summary,
    matched_field_counts,
    multiset_summary,
    split_core,
)


def test_dividend_core_maps_lse_names_without_float_noise():
    graph = {
        "ticker": "AAPL",
        "declaration_date": "2025-01-30",
        "cash_amount": 0.25,
    }
    lse = {
        "symbol": "AAPL",
        "declaration_date": "2025-01-30",
        "dividend_amount": 0.2500,
    }

    assert dividend_core(graph, "graph") == dividend_core(lse, "lse")


def test_dividend_optional_codes_normalize_to_production_labels():
    graph = {
        "ticker": "AAPL",
        "declaration_date": "2025-01-30",
        "cash_amount": 0.25,
        "currency": "USD",
        "dividend_type": "Regular",
        "ex_dividend_date": "2025-02-10",
        "frequency": "Quarterly",
        "pay_date": "2025-02-13",
        "record_date": "2025-02-10",
    }
    lse = {
        "symbol": "AAPL",
        "declaration_date": "2025-01-30",
        "dividend_amount": 0.25,
        "currency": "usd",
        "dividend_type": "CD",
        "effective_date": "2025-02-10",
        "frequency": "4",
        "payment_date": "2025-02-13",
        "record_date": "2025-02-10",
    }

    result = matched_field_counts([graph], [lse])

    assert result["paired_core_rows"] == 1
    assert set(result["field_exact_after_normalization"].values()) == {1}


def test_dividend_production_id_normalizes_type_code():
    graph = {
        "ticker": "AAPL",
        "declaration_date": "2025-01-30",
        "dividend_type": "Regular",
    }
    lse = {
        "symbol": "AAPL",
        "declaration_date": "2025-01-30",
        "dividend_type": "CD",
    }

    assert dividend_production_id(
        graph, "graph"
    ) == dividend_production_id(lse, "lse")


def test_dividend_id_summary_detects_conflicting_duplicate_payloads():
    graph = [
        {
            "ticker": "AAPL",
            "declaration_date": "2025-01-30",
            "dividend_type": "Regular",
            "cash_amount": 0.25,
            "currency": "USD",
            "ex_dividend_date": "2025-02-10",
            "frequency": "Quarterly",
            "pay_date": "2025-02-13",
            "record_date": "2025-02-10",
        }
    ]
    lse = [
        {
            "symbol": "AAPL",
            "declaration_date": "2025-01-30",
            "dividend_type": "CD",
            "dividend_amount": 0.25,
            "currency": "USD",
            "effective_date": "2025-02-10",
            "frequency": "4",
            "payment_date": "2025-02-13",
            "record_date": "2025-02-10",
        },
        {
            "symbol": "AAPL",
            "declaration_date": "2025-01-30",
            "dividend_type": "Regular",
            "dividend_amount": 0.30,
            "currency": "USD",
            "effective_date": "2025-02-10",
            "frequency": "Quarterly",
            "payment_date": "2025-02-13",
            "record_date": "2025-02-10",
        },
    ]

    result = dividend_production_id_summary(graph, lse)

    assert result["overlap_ids"] == 1
    assert result["ids_with_any_exact_full_payload"] == 1
    assert result["lse_duplicate_rows_beyond_one_per_id"] == 1
    assert result["lse_conflicting_duplicate_ids"] == 1


def test_split_multiset_comparison_preserves_duplicate_counts():
    graph = [
        {
            "ticker": "NVDA",
            "execution_date": "2024-06-10",
            "split_from": 1,
            "split_to": 10,
        },
        {
            "ticker": "NVDA",
            "execution_date": "2024-06-10",
            "split_from": 1,
            "split_to": 10,
        },
    ]
    lse = [
        {
            "symbol": "NVDA",
            "effective_date": "2024-06-10",
            "split_from": 1,
            "split_to": 10,
        }
    ]

    result = multiset_summary(graph, lse, split_core)

    assert result["matched_rows"] == 1
    assert result["graph_missing_rows"] == 1


def test_split_core_treats_comma_formatted_graph_number_as_numeric():
    graph = {
        "ticker": "GE",
        "execution_date": "2024-04-02",
        "split_from": "1,000",
        "split_to": "1,253",
    }
    lse = {
        "symbol": "GE",
        "effective_date": "2024-04-02",
        "split_from": 1000,
        "split_to": 1253,
    }

    assert split_core(graph, "graph") == split_core(lse, "lse")
