"""M1 structure-inventory durable tests (audit round 2 order, RED-first).

Three REAL cached exhibits pin the header-credit law:
  1. AAP balance sheet — banner-only credit must NEVER be complete (the reviewer's
     $1,657|$1,869 case), while the SAME file's cash-flow table with genuinely
     aligned date headers stays complete.
  2. AMD — 'Q1 2023'-style period header rows land in the header zone and the data
     cells under them stay complete (the first-fix regression pin).
  3. American Airlines guidance — a FULL-GRID heading ('FY 2026E' spanning every
     column) must never prove a SPECIFIC column, even when the numeric cell starts
     at grid column 0 (the certified left-anchor guard alone missed this: its
     `start==0 and target_start>0` test never fires for a leftmost target).

    venv/bin/python -m pytest scripts/driver_seed/relocate_probe/phase2/test_m1_structure_inventory.py -q
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..')))

from m1_transcript_census import NUM
from driver.relocation import inline_html as IH
import m1_structure_inventory as INV

CACHE = os.path.join(_HERE, '..', 'exhibit_html_cache')


def _verdicts(filename, row_predicate, token_predicate=None):
    """Every classifier verdict for numeric-bearing cells on rows matching the
    predicate — found through the REAL shipped classifier, no test-only parsing."""
    html = open(os.path.join(CACHE, filename), 'rb').read().decode('utf-8', 'replace')
    soup = IH._soup(html)
    ctx = {'tables': {}, 'cells': {}}
    out = []
    for s in soup.find_all(string=True):
        if not NUM.findall(s):
            continue
        el = s.parent
        cell = el if el.name in ('td', 'th') else el.find_parent(['td', 'th'])
        if cell is None or cell.find_parent('table') is None:
            continue
        row_text = IH._text(cell.find_parent('tr'))
        if not row_predicate(row_text):
            continue
        if token_predicate and not token_predicate(str(s)):
            continue
        out.append((row_text[:60], str(s).strip()[:16],
                    INV._classify_cell(cell, ctx)))
    return out


def test_aap_banner_only_is_never_complete():
    # Balance sheet: only full-grid banners above ('Condensed Consolidated Balance
    # Sheets', '(In millions) (unaudited)') — must NOT be complete.
    got = _verdicts('0001158449-25-000268__EX-99.1.htm',
                    lambda r: r.startswith('Cash and cash equivalents $'),
                    lambda t: '1,657' in t or '1,869' in t)
    assert got, 'AAP balance-sheet row not found'
    assert all(v != 'complete_strict' for _r, _t, v in got), got


def test_aap_real_headers_stay_complete():
    # Cash-flow table in the SAME file: 'Twenty-Eight Weeks Ended' + dated column
    # headers are genuinely grid-aligned — completeness must be preserved.
    got = _verdicts('0001158449-25-000268__EX-99.1.htm',
                    lambda r: r.startswith('Cash and cash equivalents , end of period'),
                    lambda t: '1,657' in t)
    assert got, 'AAP cash-flow row not found'
    assert all(v == 'complete_strict' for _r, _t, v in got), got


def test_amd_period_headers_preserved():
    data = _verdicts('0000002488-23-000074__EX-99.1.htm',
                     lambda r: r.startswith('Revenue ($M)'))
    assert data and all(v == 'complete_strict' for _r, _t, v in data), data
    hdr = _verdicts('0000002488-23-000074__EX-99.1.htm',
                    lambda r: r.startswith('Q1 2023 Q1 2022'))
    assert hdr and all(v == 'header_zone' for _r, _t, v in hdr), hdr


def test_full_grid_banner_never_proves_leftmost_column():
    # AA guidance: numeric-bearing leftmost cell ('Free cash flow 4') whose ONLY
    # credit is the full-grid 'FY 2026E' banner — must NOT be complete.
    got = _verdicts('0000006201-26-000008__EX-99.1.htm',
                    lambda r: r.startswith('Free cash flow 4'))
    assert got, 'AA guidance row not found'
    assert all(v != 'complete_strict' for _r, _t, v in got), got
