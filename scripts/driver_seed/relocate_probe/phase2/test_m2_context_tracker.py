"""Durable pin (reviewer closing item 2, 2026-07-22): on REAL ADM data, a
repeated column-header band REPLACES the old band — the revenue rows' band is the
band printed above the revenue section, never the earlier volumes band — and the
section register changes independently (AEE both-registers pin included).

    venv/bin/python -m pytest scripts/driver_seed/relocate_probe/phase2/test_m2_context_tracker.py -q
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..')))

from driver.relocation import inline_html as IH
import m1_structure_inventory as INV
from m2_native_table_shadow_r3 import _context_track, _numeric_data_cols

CACHE = os.path.join(_HERE, '..', 'exhibit_html_cache')


def _table(filename, table_index):
    soup = IH._soup(open(os.path.join(CACHE, filename), 'rb')
                    .read().decode('utf-8', 'replace'))
    tables = [t for t in soup.find_all('table') if t.find_parent('table') is None]
    rows = INV._own_rows(tables[table_index])
    grid = IH._table_grid(rows)
    zone_end = next((i for i, p in enumerate(grid) if INV._data_like(p)), 0)
    gw = max((e for p in grid for _c, _s, e in p), default=0)
    return rows, grid, _context_track(grid, _numeric_data_cols(grid, zone_end), gw)


def _row_index(rows, prefix):
    return next(i for i, r in enumerate(rows) if IH._text(r).startswith(prefix))


def test_adm_repeated_band_replaces_old_band():
    rows, grid, ctx = _table('0000007084-25-000005__EX-99.1.htm', 16)
    vol = _row_index(rows, 'Oilseeds ')           # volumes section data row
    rev = _row_index(rows, 'Ag Services and Oilseeds $')
    vol_band, vol_sect = ctx[vol]
    rev_band, rev_sect = ctx[rev]
    vol_band_txt = ' '.join(IH._text(rows[j]) for j in vol_band)
    rev_band_txt = ' '.join(IH._text(rows[j]) for j in rev_band)
    rev_sect_txt = ' '.join(IH._text(rows[j]) for j in rev_sect)
    # the revenue rows' band is the REPEATED (later) date band — the volumes band
    # is fully replaced, never inherited
    assert rev_band and vol_band and rev_band != vol_band, (rev_band, vol_band)
    assert min(rev_band) > max(vol_band)
    assert 'metric tons' not in (rev_band_txt + rev_sect_txt).lower()
    # '(in millions)' spans the value columns → per the reviewer model it lives
    # in the BAND register; assert it reaches the row through EITHER register
    assert 'in millions' in (rev_band_txt + rev_sect_txt).lower()
    assert 'Quarter' in rev_band_txt or '2024' in rev_band_txt


def test_aee_band_survives_section_change():
    rows, grid, ctx = _table('0001002910-25-000052__EX-99.1.htm', 13)
    # the table has TWO 'Ameren Illinois Natural Gas' rows (Gas Sales vs Gas
    # Revenues — the reviewer's original distinguishing case); pin the REVENUE
    # one by its audited truth address (t13r10, truth v4)
    rev = 10
    band, sect = ctx[rev]
    band_txt = ' '.join(IH._text(rows[j]) for j in band)
    sect_txt = ' '.join(IH._text(rows[j]) for j in sect)
    # the date band set at the table top SURVIVES the section change to
    # 'Gas Revenues' — both registers present, independently
    assert band, 'date band must survive the section change'
    assert any(ch.isdigit() for ch in band_txt), band_txt
    assert 'gas revenues' in sect_txt.lower(), sect_txt
