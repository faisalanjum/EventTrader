"""Durable pin (2026-07-18, added when match_8k_to_periodic was extracted): the presentation
tool get_earnings_with_10q() keeps its FROZEN behavior — daily-stock scope filter, the exact
[-24h, +MAX_LAG_HOURS] lag boundaries, per-fiscal-key deduplication (nearest |lag| wins), and the
exact pipe output shape. Any future drift in the shared matcher or the wrapper fails HERE, not in
production. Pure: the session is faked; no graph.

    venv/bin/python -m pytest scripts/earnings/test_get_quarterly_filings.py -q
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..', '.claude', 'skills', 'earnings-orchestrator', 'scripts'))
import get_quarterly_filings as G


class _FakeSession:
    def __init__(self, rows):
        self._rows = rows

    def run(self, query, **kw):
        return list(self._rows)


def _fake_neo4j_session(rows):
    from contextlib import contextmanager

    @contextmanager
    def cm():
        yield _FakeSession(rows), None
    return cm


ROW = dict(accession_8k='8K-1', filed_8k='2024-04-25T16:05:00', market_session_8k='post',
           daily_stock_8k=1.0, accession_10q='10Q-1', filed_10q='2024-05-05T09:00:00',
           market_session_10q='pre', form_type='10-Q', period_10q='2024-03-31',
           xbrl_period_focus='Q1', xbrl_year_focus='2024')

HEADER = ('accession_8k|filed_8k|market_session_8k|accession_10q|filed_10q|'
          'market_session_10q|form_type|fiscal_year|fiscal_quarter|lag')


def test_daily_stock_filter_and_output_shape(monkeypatch):
    rows = [ROW, dict(ROW, accession_8k='8K-NO-DS', daily_stock_8k=None)]
    monkeypatch.setattr(G, 'neo4j_session', _fake_neo4j_session(rows))
    monkeypatch.setattr(G, 'get_derived_fye', lambda s, t: 12)
    out = G.get_earnings_with_10q('TST', dedupe=False)
    lines = out.strip().split('\n')
    assert lines[0] == HEADER                                   # output shape FROZEN
    body = lines[1:]
    assert len(body) == 1 and body[0].startswith('8K-1|'), body  # ds-null row EXCLUDED (frozen)
    assert body[0].split('|')[3] == '10Q-1'
    # the harvest-facing matcher DOES see the ds-null 8-K (the one intentional scope difference)
    ms = G.match_8k_to_periodic(_FakeSession(rows), 'TST', require_daily_stock=False)
    assert [m['accession_8k'] for m in ms] == ['8K-1', '8K-NO-DS']
    print("[ok] tool scope + output shape frozen; harvest superset intentional")


def test_lag_boundaries_frozen(monkeypatch):
    just_in = dict(ROW, accession_8k='IN', filed_10q='2024-07-24T16:05:00')      # +90d exactly
    just_out = dict(ROW, accession_8k='OUT', filed_10q='2024-07-24T16:05:01')    # +90d + 1s
    neg_in = dict(ROW, accession_8k='NEG', filed_10q='2024-04-24T16:05:00')      # -24h exactly
    neg_out = dict(ROW, accession_8k='NEGOUT', filed_10q='2024-04-24T16:04:59')  # -24h - 1s
    monkeypatch.setattr(G, 'neo4j_session',
                        _fake_neo4j_session([just_in, just_out, neg_in, neg_out]))
    monkeypatch.setattr(G, 'get_derived_fye', lambda s, t: 12)
    out = G.get_earnings_with_10q('TST', dedupe=False)
    got = {l.split('|')[0]: l.split('|')[3] for l in out.strip().split('\n')[1:]}
    assert got['IN'] == '10Q-1' and got['NEG'] == '10Q-1', got   # inclusive boundaries FROZEN
    assert got['OUT'] == 'N/A' and got['NEGOUT'] == 'N/A', got
    print("[ok] lag window boundaries frozen: [-24h, +MAX_LAG_HOURS] inclusive")


def test_dedupe_keeps_nearest_lag(monkeypatch):
    near = ROW                                                              # ~9.7d lag
    far = dict(ROW, accession_8k='8K-2', filed_8k='2024-04-20T16:05:00')    # ~14.7d, same key
    monkeypatch.setattr(G, 'neo4j_session', _fake_neo4j_session([far, near]))
    monkeypatch.setattr(G, 'get_derived_fye', lambda s, t: 12)
    out = G.get_earnings_with_10q('TST', dedupe=True)
    body = out.strip().split('\n')[1:]
    assert len(body) == 1 and body[0].startswith('8K-1|'), body  # nearest |lag| wins (frozen)
    print("[ok] per-fiscal-key dedupe keeps the nearest-lag 8-K")
