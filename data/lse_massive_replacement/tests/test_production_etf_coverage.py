from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from audit_production_etf_coverage import (  # noqa: E402
    build_report,
    build_requirement_rows,
    classify_catalog_symbol,
    company_coverage,
    find_name_candidates,
    load_static_allowlist,
)


def test_requirement_rows_count_unique_companies_by_benchmark_role():
    universe = [
        {
            "symbol": "AAA",
            "sector": "Technology",
            "industry": "Semiconductors",
            "sector_etf": "XLK",
            "industry_etf": "SOXX",
        },
        {
            "symbol": "BBB",
            "sector": "Technology",
            "industry": "Software",
            "sector_etf": "XLK",
            "industry_etf": "IGV",
        },
        {
            "symbol": "CCC",
            "sector": "FinancialServices",
            "industry": "BanksRegional",
            "sector_etf": "XLF",
            "industry_etf": "KIE",
        },
    ]

    rows = {row["symbol"]: row for row in build_requirement_rows(universe)}

    assert rows["XLK"]["roles"] == ["sector"]
    assert rows["XLK"]["csv_company_count"] == 2
    assert rows["XLK"]["sector_company_count"] == 2
    assert rows["XLK"]["groups"] == ["Technology"]
    assert rows["SOXX"]["industry_company_count"] == 1
    assert rows["SOXX"]["groups"] == ["Semiconductors"]


def test_only_an_exact_etf_catalog_row_counts_as_the_required_etf():
    catalog = [
        {"dataset": "etf", "symbol": "XLE", "name": "Energy ETF"},
        {"dataset": "options", "symbol": "XLE", "name": "XLE options"},
        {"dataset": "options", "symbol": "XLK", "name": "XLK options"},
        {"dataset": "stocks", "symbol": "XLF", "name": "Unrelated company"},
        {"dataset": "index", "symbol": "SOX/USD", "name": "PHLX Semiconductor"},
    ]

    xle = classify_catalog_symbol("XLE", catalog)
    xlk = classify_catalog_symbol("XLK", catalog)
    xlf = classify_catalog_symbol("XLF", catalog)

    assert xle["exact_etf_available"] is True
    assert xle["exact_datasets"] == ["etf", "options"]
    assert xlk["exact_etf_available"] is False
    assert xlk["options_underlying_available"] is True
    assert xlf["exact_etf_available"] is False
    assert xlf["non_etf_exact_matches"][0]["dataset"] == "stocks"


def test_company_coverage_requires_both_exact_benchmark_legs():
    universe = [
        {"symbol": "A", "sector_etf": "XLE", "industry_etf": "OIH"},
        {"symbol": "B", "sector_etf": "XLK", "industry_etf": "SOXX"},
        {"symbol": "C", "sector_etf": "XLF", "industry_etf": "SOXX"},
    ]

    result = company_coverage(universe, {"XLE", "XLF", "SOXX"})

    assert result == {
        "companies": 3,
        "sector_covered": 2,
        "industry_covered": 2,
        "both_covered": 1,
        "neither_covered": 0,
    }


def test_static_allowlist_is_read_without_importing_production_code(tmp_path):
    source = tmp_path / "ETF_mappings.py"
    source.write_text(
        "Sector_Industry_ETFs = {'SPY', 'XLE', 'SOXX'}\n"
        "OTHER = {'DO_NOT_INCLUDE'}\n",
        encoding="utf-8",
    )

    assert load_static_allowlist(source) == {"SPY", "XLE", "SOXX"}


def test_name_search_marks_possible_market_proxies_but_not_exact_coverage():
    requirement = {
        "symbol": "XSD",
        "groups": ["Semiconductors", "SemiconductorEquipmentAndMaterials"],
    }
    catalog = [
        {
            "dataset": "etf",
            "symbol": "SMH",
            "name": "VanEck Semiconductor ETF",
        },
        {
            "dataset": "index",
            "symbol": "SOX/USD",
            "name": "PHLX Semiconductor",
        },
        {
            "dataset": "etf",
            "symbol": "TLT",
            "name": "20+ Year Treasury Bond ETF",
        },
    ]

    candidates = find_name_candidates(requirement, catalog)

    assert [row["symbol"] for row in candidates] == ["SMH", "SOX/USD"]
    assert all(row["is_exact_replacement"] is False for row in candidates)


def test_report_uses_live_metadata_to_check_for_etf_holdings():
    universe = [
        {
            "symbol": "AAA",
            "sector": "Energy",
            "industry": "OilAndGas",
            "sector_etf": "XLE",
            "industry_etf": "OIH",
        }
    ]
    catalog = [{"dataset": "etf", "symbol": "XLE", "name": "Energy ETF"}]
    live = {
        "meta": {
            "body": {
                "reference": ["dividends", "stock_splits", "etf_holdings"]
            }
        }
    }

    report = build_report(universe, catalog, live_evidence=live)

    assert report["lse_catalog"]["reference_data_has_etf_holdings"] is True
    assert report["lse_catalog"]["reference_datasets"][-1] == "etf_holdings"
