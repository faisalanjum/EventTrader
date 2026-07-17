"""#1 CLEAN-CHECKOUT GUARD: lock_cell.exact_cell MUST return `row_cells` (the verbatim printed row WITH its
numbers). locate.py's exact-cell rung (commit ea2ba29) builds the quote from it — without row_cells the rung
silently abstains, so on a clean checkout the whole exact-cell accuracy lever vanishes with no test failure.
This pins the contract. Deterministic — stubs the extractor, so NO EDGAR fetch and NO cached HTML needed.

    venv/bin/python -m pytest scripts/driver_seed/test_exact_cell.py -q
"""
import os, sys, types
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'relocate_probe'))
sys.path.insert(0, os.path.join(HERE, 'relocate_probe', 'benchmark', 'multiaxis_pool', 'final'))
import lock_cell

_ROW = ['Membership fees', '4,828', '', '4,580', '', '4,224']


def test_exact_cell_surfaces_row_cells(monkeypatch):
    fake = types.ModuleType('lock_row_extract')
    fake.extract = lambda *a, **k: {
        'source_words': {'row': 'Membership fees', 'column': 'September 1, 2024', 'section': 'REVENUE'},
        'evidence': {'row_cells': list(_ROW)}}
    monkeypatch.setitem(sys.modules, 'lock_row_extract', fake)
    # a qualified concept makes _resolve_concept return early (no HTML read); html_path is never opened.
    sw = lock_cell.exact_cell('unused.htm', 'us-gaap:RevenueFromContract', '2024-01-01', '2024-12-31', [])
    assert sw is not None, 'exact_cell returned None on a clean stub'
    assert sw.get('row_cells') == _ROW, f'row_cells missing/wrong -> the exact-cell quote would be empty: {sw}'
