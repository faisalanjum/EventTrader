from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from map_openfigi_holdings import (  # noqa: E402
    choose_lse_symbol,
    split_cached_jobs,
)


def test_choose_lse_symbol_prefers_exact_us_symbol():
    figi_rows = [
        {"ticker": "RIO", "exchCode": "US", "name": "RIO TINTO PLC-SPON ADR"},
        {"ticker": "RIO", "exchCode": "LN", "name": "RIO TINTO PLC"},
    ]
    catalog = [
        {"dataset": "stocks", "symbol": "RIO", "name": "Rio Tinto plc"},
        {"dataset": "stocks", "symbol": "RIO.L", "name": "Rio Tinto plc"},
        {"dataset": "stocks", "symbol": "RIO.AX", "name": "Rio Tinto Limited"},
    ]

    result = choose_lse_symbol(figi_rows, catalog, "Rio Tinto PLC")

    assert result["symbol"] == "RIO"
    assert result["selection"] == "exact OpenFIGI ticker in LSE catalog"


def test_choose_lse_symbol_maps_unique_local_ticker_with_suffix():
    figi_rows = [
        {"ticker": "BAYN", "exchCode": "GR", "name": "BAYER AG"}
    ]
    catalog = [
        {"dataset": "stocks", "symbol": "BAYN.DE", "name": "Bayer AG"}
    ]

    result = choose_lse_symbol(figi_rows, catalog, "Bayer AG")

    assert result["symbol"] == "BAYN.DE"
    assert result["selection"] == "unique suffixed LSE symbol for FIGI ticker"


def test_choose_lse_symbol_rejects_ambiguous_suffix_matches():
    figi_rows = [
        {"ticker": "ABC", "exchCode": "US", "name": "Example"}
    ]
    catalog = [
        {"dataset": "stocks", "symbol": "ABC.L", "name": "Example"},
        {"dataset": "stocks", "symbol": "ABC.AX", "name": "Example"},
    ]

    assert choose_lse_symbol(figi_rows, catalog, "Example") is None


def test_choose_lse_symbol_strips_openfigi_currency_suffix_with_name_check():
    figi_rows = [
        {
            "ticker": "LBTYAUSD",
            "exchCode": "X9",
            "name": "LIBERTY GLOBAL PLC-A",
        }
    ]
    catalog = [
        {
            "dataset": "stocks",
            "symbol": "LBTYA",
            "name": "Liberty Global plc",
        }
    ]

    result = choose_lse_symbol(figi_rows, catalog, "Liberty Global PLC")

    assert result["symbol"] == "LBTYA"
    assert result["selection"] == (
        "currency-suffixed OpenFIGI ticker plus matching LSE company name"
    )


def test_choose_lse_symbol_does_not_strip_currency_into_name_collision():
    figi_rows = [
        {"ticker": "FUSD", "exchCode": "X9", "name": "FORVIA SE"}
    ]
    catalog = [
        {
            "dataset": "stocks",
            "symbol": "F",
            "name": "Ford Motor Company",
        }
    ]

    assert choose_lse_symbol(figi_rows, catalog, "Forvia SE") is None


def test_split_cached_jobs_fetches_only_unseen_holding_keys():
    jobs = [
        {"holding": {"key": "A"}, "job": {"idValue": "1"}},
        {"holding": {"key": "B"}, "job": {"idValue": "2"}},
    ]
    cached = [
        {
            "holding": {"key": "A"},
            "job": {"idValue": "1"},
            "response": {"data": []},
        },
        {
            "holding": {"key": "OLD"},
            "job": {"idValue": "0"},
            "response": {"data": []},
        },
    ]

    reused, pending = split_cached_jobs(jobs, cached)

    assert [item["holding"]["key"] for item in reused] == ["A"]
    assert [item["holding"]["key"] for item in pending] == ["B"]
