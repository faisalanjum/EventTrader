"""Focused tests for get_earnings.py fiscal-label centralization."""
from __future__ import annotations

from contextlib import contextmanager

import scripts.earnings.get_earnings as ge


class _IsoDate:
    def __init__(self, value: str):
        self.value = value

    def isoformat(self) -> str:
        return self.value


class _FakeSession:
    def __init__(self, rows: list[dict]):
        self.rows = rows
        self.tickers: list[str] = []

    def run(self, _query: str, *, ticker: str):
        self.tickers.append(ticker)
        return self.rows


@contextmanager
def _fake_neo4j_session(rows: list[dict]):
    yield _FakeSession(rows), None


def _row(accession: str, *, created: str = "2026-02-15T16:00:00-05:00") -> dict:
    return {
        "accession": accession,
        "date": _IsoDate(created),
        "period": "2026-01-31",
        "market_session": "post",
        "daily_stock": 0.01,
        "daily_adj": 0.02,
        "sector_adj": 0.03,
        "industry_adj": 0.04,
        "trailing_vol": 0.0123456,
        "vol_days": 80,
        "fye_month": 1,
        "fye_day": 31,
    }


def _data_rows(output: str) -> list[list[str]]:
    lines = output.splitlines()
    assert lines[0].startswith("accession|date|fiscal_year|fiscal_quarter|")
    return [line.split("|") for line in lines[1:]]


def test_get_earnings_uses_resolve_quarter_info_for_8k_labels(monkeypatch):
    rows = [_row("ACC-1")]
    calls = []

    def fake_resolve(ticker: str, accession: str) -> dict:
        calls.append((ticker, accession))
        return {"safety_action": "AUTO_OK", "quarter_label": "Q4_FY2025"}

    monkeypatch.setattr(ge, "neo4j_session", lambda: _fake_neo4j_session(rows))
    monkeypatch.setattr(ge, "resolve_quarter_info", fake_resolve)

    out = ge.get_earnings("abc", dedupe=False)

    assert calls == [("abc", "ACC-1")]
    data = _data_rows(out)
    assert len(data) == 1
    assert data[0][0] == "ACC-1"
    assert data[0][2:4] == ["2025", "Q4"]


def test_get_earnings_fail_closed_rows_stay_unresolved_and_not_collapsed(monkeypatch):
    rows = [
        _row("ACC-1", created="2026-02-15T16:00:00-05:00"),
        _row("ACC-2", created="2026-02-16T16:00:00-05:00"),
    ]

    monkeypatch.setattr(ge, "neo4j_session", lambda: _fake_neo4j_session(rows))
    monkeypatch.setattr(
        ge,
        "resolve_quarter_info",
        lambda _ticker, _accession: {
            "safety_action": "FAIL_CLOSED",
            "quarter_label": None,
        },
    )

    out = ge.get_earnings("ABC", dedupe=True)

    data = _data_rows(out)
    assert [r[0] for r in data] == ["ACC-1", "ACC-2"]
    assert [r[2:4] for r in data] == [["N/A", "N/A"], ["N/A", "N/A"]]


def test_get_earnings_dedupes_by_resolver_quarter_label(monkeypatch):
    rows = [
        _row("ACC-OLD", created="2026-02-15T16:00:00-05:00"),
        _row("ACC-NEW", created="2026-02-16T16:00:00-05:00"),
    ]

    monkeypatch.setattr(ge, "neo4j_session", lambda: _fake_neo4j_session(rows))
    monkeypatch.setattr(
        ge,
        "resolve_quarter_info",
        lambda _ticker, _accession: {
            "safety_action": "AUTO_OK",
            "quarter_label": "Q4_FY2025",
        },
    )

    out = ge.get_earnings("ABC", dedupe=True)

    data = _data_rows(out)
    assert len(data) == 1
    assert data[0][0] == "ACC-NEW"
    assert data[0][2:4] == ["2025", "Q4"]

