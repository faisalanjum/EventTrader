#!/usr/bin/env python3
import importlib.util
from pathlib import Path

from bs4 import BeautifulSoup


EXTRACTOR = Path('/tmp/cell_address_probe.WhbHsb/lock_row_extract.py')
spec = importlib.util.spec_from_file_location('lock_extract', EXTRACTOR)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def column(html, fact_id, pairs):
    soup = BeautifulSoup(html, 'lxml')
    fact = soup.find(id=fact_id)
    cell = fact.find_parent(['td', 'th'])
    row = cell.find_parent('tr')
    table = row.find_parent('table')
    rows = [item for item in table.find_all('tr') if item.find_parent('table') is table]
    return module.aligned_column(rows, rows.index(row), cell, pairs)


def test_rowspan_colspan():
    html = '''<table>
      <tr><td rowspan="2">Metric</td><td colspan="4">North America</td><td colspan="4">Europe</td></tr>
      <tr><td colspan="2">2024</td><td colspan="2">2023</td><td colspan="2">2024</td><td colspan="2">2023</td></tr>
      <tr><td>Grocery</td><td colspan="2"><ix:nonfraction id="target">10</ix:nonfraction></td><td colspan="2">9</td><td colspan="2">8</td><td colspan="2">7</td></tr>
    </table>'''
    pairs = [('x:GeographyAxis', 'x:NorthAmericaMember'),
             ('x:ProductAxis', 'x:GroceryMember')]
    assert column(html, 'target', pairs) == 'North America'


def test_prior_data_and_hidden_cells_are_ignored():
    html = '''<table>
      <tr><td></td><td colspan="2">U.S. Regions</td><td colspan="2">All Other</td></tr>
      <tr><td></td><td colspan="2" style="display:none">Wrong Regions</td><td colspan="2"></td></tr>
      <tr><td colspan="3">Wide prior label</td><td><ix:nonfraction>99</ix:nonfraction></td><td></td></tr>
      <tr><td>Other</td><td colspan="2"><ix:nonfraction id="target">10</ix:nonfraction></td><td colspan="2">9</td></tr>
    </table>'''
    pairs = [('x:SegmentAxis', 'x:USRegionsMember'),
             ('x:ProductAxis', 'x:OtherMember')]
    assert column(html, 'target', pairs) == 'U.S. Regions'


if __name__ == '__main__':
    test_rowspan_colspan()
    test_prior_data_and_hidden_cells_are_ignored()
    print('2 synthetic grid tests passed')
