from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from fetch_sec_pilot_holdings import (  # noqa: E402
    filing_may_cover_period,
    load_funds,
    parse_nport,
)


def test_parse_nport_extracts_report_date_and_long_equity_weights():
    xml = b"""<?xml version="1.0"?>
    <edgarSubmission xmlns="http://www.sec.gov/edgar/nport">
      <formData>
        <genInfo><repPdDate>2024-12-31</repPdDate></genInfo>
        <invstOrSecs>
          <invstOrSec>
            <name>Example Corp.</name><cusip>123456789</cusip>
            <pctVal>12.5</pctVal><assetCat>EC</assetCat>
            <payoffProfile>Long</payoffProfile>
          </invstOrSec>
          <invstOrSec>
            <name>Example Bond</name><cusip>987654321</cusip>
            <pctVal>2.5</pctVal><assetCat>DBT</assetCat>
            <payoffProfile>Long</payoffProfile>
          </invstOrSec>
        </invstOrSecs>
      </formData>
    </edgarSubmission>"""

    result = parse_nport(xml)

    assert result == {
        "report_date": "2024-12-31",
        "holdings": [
            {
                "name": "Example Corp.",
                "cusip": "123456789",
                "weight_percent": 12.5,
            }
        ],
    }


def test_parse_nport_keeps_available_security_identifiers():
    xml = b"""<?xml version="1.0"?>
    <edgarSubmission xmlns="http://www.sec.gov/edgar/nport">
      <formData>
        <genInfo><repPdDate>2026-03-31</repPdDate></genInfo>
        <invstOrSecs>
          <invstOrSec>
            <name>Example Corp.</name>
            <lei>EXAMPLELEI</lei>
            <title>Example Class A</title>
            <cusip>123456789</cusip>
            <identifiers>
              <isin value="US1234567890"/>
              <ticker value="EXM"/>
            </identifiers>
            <curCd>USD</curCd>
            <invCountry>US</invCountry>
            <pctVal>5</pctVal><assetCat>EC</assetCat>
            <payoffProfile>Long</payoffProfile>
          </invstOrSec>
        </invstOrSecs>
      </formData>
    </edgarSubmission>"""

    assert parse_nport(xml)["holdings"][0] == {
        "name": "Example Corp.",
        "cusip": "123456789",
        "weight_percent": 5.0,
        "title": "Example Class A",
        "lei": "EXAMPLELEI",
        "isin": "US1234567890",
        "ticker": "EXM",
        "currency": "USD",
        "investment_country": "US",
    }


def test_load_funds_reads_selected_symbols_from_sec_map(tmp_path):
    fund_map = tmp_path / "fund_map.json"
    fund_map.write_text(
        """{
          "matched": {
            "XLB": {
              "cik": "1064641",
              "series_id": "S000006414",
              "class_id": "C000017600",
              "symbol": "XLB"
            },
            "XLK": {
              "cik": "1064641",
              "series_id": "S000006415",
              "class_id": "C000017601",
              "symbol": "XLK"
            }
          }
        }""",
        encoding="utf-8",
    )

    assert load_funds(fund_map, ["xlk"]) == {
        "XLK": {
            "cik": "1064641",
            "series": "S000006415",
            "class_id": "C000017601",
            "name": "XLK",
        }
    }


def test_load_funds_preserves_multiple_historical_registrations(tmp_path):
    fund_map = tmp_path / "fund_map.json"
    fund_map.write_text(
        """{
          "matched": {
            "HACK": {
              "symbol": "HACK",
              "name": "Cybersecurity ETF",
              "registrations": [
                {
                  "cik": "1",
                  "series_id": "S-OLD",
                  "class_id": "C-OLD"
                },
                {
                  "cik": "2",
                  "series_id": "S-NEW",
                  "class_id": "C-NEW"
                }
              ]
            }
          }
        }""",
        encoding="utf-8",
    )

    assert load_funds(fund_map) == {
        "HACK": {
            "name": "Cybersecurity ETF",
            "registrations": [
                {"cik": "1", "series": "S-OLD", "class_id": "C-OLD"},
                {"cik": "2", "series": "S-NEW", "class_id": "C-NEW"},
            ],
        }
    }


def test_filing_filter_keeps_january_filing_for_december_report_period():
    assert filing_may_cover_period(
        "2023-01-27",
        "2022-12-01",
    )
    assert not filing_may_cover_period(
        "2022-11-30",
        "2022-12-01",
    )
