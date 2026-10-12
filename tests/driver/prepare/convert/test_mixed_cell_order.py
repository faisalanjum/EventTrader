"""A row's cells keep their source order whatever their tags (Root, mixed cell order finding, Oct 12). EdgarTools 5.60.0 `TableProcessor._process_row`
reads a row's td cells first and its th cells after them (kept from an old findall order); its own `_own_cells` lists them as the source has them. So a
row label in a th, or a th after a td, stands in another column, and when a declared resource is unavailable no browser geometry regrids it (PARTIAL).
Truth is the browser's own layout of the same source with every resource present (each cell's box), compared cell by cell in source order, never the
converter. Invented sources."""
import hashlib
import unittest

from driver.prepare.convert import html_route, screen_grid
from tests.driver.prepare.convert import test_header_reorder_spans as base  # its page(), CSS (module import: its TestCase is not collected twice)

TABLES = {
    'th_then_td': '<tr><th>A</th><td>B</td></tr><tr><td>11</td><td>29</td></tr>',
    'row_label_th': '<tr><td></td><th>2024</th><th>2023</th></tr><tr><th>Revenue</th><td>10</td><td>9</td></tr><tr><th>Cost</th><td>4</td><td>3</td></tr>',
    'th_td_th': '<tr><th>A</th><td>B</td><th>C</th></tr><tr><td>1</td><td>2</td><td>3</td></tr>',
    'repeated': '<tr><th>Q</th><td>Q</td><th>Q</th><td>Q</td></tr><tr><td>q</td><th>q</th><td>q</td><th>q</th></tr>',
    'spans': '<tr><th rowspan="2">Seg</th><td colspan="2">Both</td></tr><tr><td>3</td><td>4</td></tr><tr><th>Total</th><td>7</td><td></td></tr>',
    'control_all_td': '<tr><td>A</td><td>B</td></tr><tr><td>11</td><td>29</td></tr>',
    'control_all_th': '<tr><th>A</th><th>B</th></tr><tr><td>11</td><td>29</td></tr>',
}
SLOTS = """() => Array.from(document.querySelectorAll('body > table')).map(t => { const cells = Array.from(t.rows).flatMap(r => Array.from(r.cells));
  const at = (c, k) => Math.round(c.getBoundingClientRect()[k]);
  const L = [...new Set(cells.map(c => at(c, 'left')))].sort((a, b) => a - b), T = [...new Set(cells.map(c => at(c, 'top')))].sort((a, b) => a - b);
  return cells.map(c => [T.indexOf(at(c, 'top')), L.indexOf(at(c, 'left')), c.tagName === 'TH']); })"""
HOLDERS = ('<tr><th>H</th><td><table><tr><td>n</td></tr></table></td><td>2024 <img src="p.png" alt="p"></td></tr>'
           '<tr><th>Sales</th><td>5</td><td>8</td></tr>')


def run(rows, extra=None):
    from playwright.sync_api import sync_playwright  # required: a missing install fails the suite
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            tab = browser.new_page(); tab.set_content(base.page(rows, False).decode()); truth = tab.evaluate(SLOTS); tab.close()
            raw = base.page(rows, True); got = {}
            for case, members in (('present', {'doc.htm': raw, 's.css': base.CSS.encode(), **(extra or {})}), ('unavailable', {'doc.htm': raw, **(extra or {})})):
                got[case] = html_route.prepare(raw, 'invented/mixed.htm', hashlib.sha256(raw).hexdigest(), browser, screen_grid.Source('doc.htm', members))
        finally: browser.close()
    return truth, got


class MixedCellOrder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = {name: run(rows) for name, rows in TABLES.items()}

    def test_an_unavailable_resource_still_withholds_geometry(self):
        for name, (_, got) in self.results.items():
            with self.subTest(table=name):
                self.assertEqual((got['unavailable'][0]['status'], got['unavailable'][1]['screen']['cells_regridded'], got['present'][0]['status']), ('PARTIAL', 0, 'OK'))

    def test_every_own_cell_stands_in_its_source_slot_and_a_th_stays_a_header(self):  # cell by cell in source order: repeated texts cannot pass by equality
        for name, (truth, got) in self.results.items():
            for case, (route, _) in got.items():
                with self.subTest(table=name, resources=case):
                    tables = [u for u in route['units'] if u['kind'] == 'table' and 'cell' not in u]
                    own = [sorted(u['cells'], key=lambda c: c['source']['byte_start']) for u in tables]
                    self.assertEqual([[[c['r'], c['c']] for c in cs] for cs in own], [[[r, c] for r, c, _ in t] for t in truth])  # the source slot
                    self.assertTrue(all(c['header'] for cs, t in zip(own, truth) for c, (_, _, th) in zip(cs, t) if th))  # a th is always the tool's header; its row reading (td in a header row) stays the tool's

    def test_a_nested_table_and_a_picture_after_a_header_cell_name_their_source_slots(self):
        from tests.driver.prepare.pictures.test_inputs import MEMBERS
        truth, got = run(HOLDERS, {'p.png': MEMBERS['opaque.png']})
        for case, (route, _) in got.items():
            with self.subTest(resources=case):
                outer, inner = [u for u in route['units'] if u['kind'] == 'table']
                holder = next(c for c in outer['cells'] if c.get('tables'))
                self.assertEqual((holder['r'], holder['c'], holder['tables'], {k: inner['cell'][k] for k in ('table', 'r', 'c')}), (0, 1, [inner['id']], {'table': outer['id'], 'r': 0, 'c': 1}))
                picture = next(u for u in route['units'] if u['kind'] == 'image')
                self.assertEqual((picture['cell']['table'], picture['cell']['r'], picture['cell']['c']), (outer['id'], 0, 2))  # the 2024 cell, source slot (0, 2)


if __name__ == '__main__':
    unittest.main()
