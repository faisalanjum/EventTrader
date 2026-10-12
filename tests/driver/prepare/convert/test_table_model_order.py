"""Every own row, empty ones too, stands where the HTML table model draws it, and a span ends with its row group (Root, consolidated native table
design, Oct 12). EdgarTools 5.60.0 drops a row with no cells, keeps no row group, reads a tfoot written before its tbody in source order, and reads
rowspan="0" as one row and a span larger than its group as crossing into the next. Without qualifying geometry (a declared resource unavailable) nothing
regrids it. Expected slots are hand-read by the HTML table model (header group drawn first, bodies as written, footer group last; empty rows count;
rowspan 0 runs to its group's end, a larger span stops there), checked against the browser's own layout of the same source: its columns always, its rows
wherever no empty row hides one (an empty row has no box). Invented sources; never the converter."""
import hashlib
import unittest

from driver.prepare.convert import html_route, screen_grid
from tests.driver.prepare.convert import test_header_reorder_spans as base  # page(), CSS (module import: its TestCase is not collected twice)

CASES = {  # name -> (rows, expected (r, c) of every own cell of each table in source order)
    'early_tfoot': ('<thead><tr><th>Item</th><th>2024</th></tr></thead><tfoot><tr><td>Total</td><td>19</td></tr></tfoot><tbody><tr><td>Revenue</td><td>10</td></tr>'
                    '<tr><td>Cost</td><td>9</td></tr></tbody>', [[(0, 0), (0, 1), (3, 0), (3, 1), (1, 0), (1, 1), (2, 0), (2, 1)]]),
    'empty_row_in_span': ('<tr><td rowspan="2">A</td><td>1</td></tr><tr></tr><tr><td>x</td><td>y</td></tr>', [[(0, 0), (0, 1), (2, 0), (2, 1)]]),
    'trailing_empty_row': ('<tr><td>A</td><td>B</td></tr><tr><td>C</td><td>D</td></tr><tr></tr>', [[(0, 0), (0, 1), (1, 0), (1, 1)]]),
    'zero_span': ('<tbody><tr><td rowspan="0">A</td><td>1</td></tr><tr><td>2</td></tr><tr><td>3</td></tr></tbody><tbody><tr><td>x</td><td>y</td></tr></tbody>',
                  [[(0, 0), (0, 1), (1, 1), (2, 1), (3, 0), (3, 1)]]),
    'oversized_span': ('<tbody><tr><td rowspan="9">A</td><td>1</td></tr><tr><td>2</td></tr></tbody><tbody><tr><td>x</td><td>y</td></tr></tbody>',
                       [[(0, 0), (0, 1), (1, 1), (2, 0), (2, 1)]]),
    'late_thead': ('<tbody><tr><td>v</td><td>1</td></tr></tbody><thead><tr><th>H</th><th>2024</th></tr></thead>', [[(1, 0), (1, 1), (0, 0), (0, 1)]]),
    'footer_span_mixed': ('<tfoot><tr><th>Total</th><td>19</td></tr></tfoot><tbody><tr><th rowspan="2">Item</th><th>Q1</th></tr><tr><td>a</td></tr>'
                          '<tr><td>Period</td><td>2024</td></tr></tbody>', [[(3, 0), (3, 1), (0, 0), (0, 1), (1, 1), (2, 0), (2, 1)]]),
    'repeated_in_groups': ('<tfoot><tr><td>Q</td><td>Q</td></tr></tfoot><tbody><tr><td rowspan="2">Q</td><td>Q</td></tr><tr><td>Q</td></tr></tbody>',
                           [[(2, 0), (2, 1), (0, 0), (0, 1), (1, 1)]]),
    'control_ordinary': ('<tr><th>Item</th><th>2024</th></tr><tr><td>Revenue</td><td>10</td></tr>', [[(0, 0), (0, 1), (1, 0), (1, 1)]]),
    'control_bounded_span': ('<tbody><tr><td rowspan="2">A</td><td>1</td></tr><tr><td>2</td></tr></tbody><tbody><tr><td>x</td><td>y</td></tr></tbody>',
                             [[(0, 0), (0, 1), (1, 1), (2, 0), (2, 1)]]),
}
HOLDERS = ('<tfoot><tr><td>F</td><td>9</td></tr></tfoot><tbody><tr><td><table><tr><td>n</td></tr></table></td><td>2024 <img src="p.png" alt="p"></td></tr></tbody>')
OWN = """() => Array.from(document.querySelectorAll('body > table')).map(t => { const cells = Array.from(t.querySelectorAll('td,th')).filter(c => c.closest('table') === t);
  const at = (c, k) => Math.round(c.getBoundingClientRect()[k]); const L = [...new Set(cells.map(c => at(c, 'left')))].sort((a, b) => a - b), T = [...new Set(cells.map(c => at(c, 'top')))].sort((a, b) => a - b);
  return cells.map(c => [T.indexOf(at(c, 'top')), L.indexOf(at(c, 'left'))]); })"""


def run(rows, extra=None):
    from playwright.sync_api import sync_playwright  # required: a missing install fails the suite
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            tab = browser.new_page(); tab.set_content(base.page(rows, False).decode()); shown = tab.evaluate(OWN); tab.close()
            raw = base.page(rows, True); got = {}
            for case, members in (('present', {'doc.htm': raw, 's.css': base.CSS.encode(), **(extra or {})}), ('unavailable', {'doc.htm': raw, **(extra or {})})):
                got[case] = html_route.prepare(raw, 'invented/model.htm', hashlib.sha256(raw).hexdigest(), browser, screen_grid.Source('doc.htm', members))
        finally: browser.close()
    return shown, got


def slots(route):  # every own cell of each top table, in source order
    return [[(c['r'], c['c']) for c in sorted(u['cells'], key=lambda c: c['source']['byte_start'])] for u in route['units'] if u['kind'] == 'table' and 'cell' not in u]


class TableModelOrder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = {name: run(rows) for name, (rows, _) in CASES.items()}

    def test_the_hand_read_slots_are_the_browser_layout(self):  # the independent check of every expectation: columns always, rows where no empty row hides one
        for name, (rows, want) in CASES.items():
            with self.subTest(table=name):
                shown = self.results[name][0]
                self.assertEqual([[c for _, c in t] for t in shown], [[c for _, c in t] for t in want])
                if '<tr></tr>' not in rows: self.assertEqual([[tuple(x) for x in t] for t in shown], want)

    def test_an_unavailable_resource_still_withholds_geometry(self):
        for name, (_, got) in self.results.items():
            with self.subTest(table=name):
                self.assertEqual((got['unavailable'][0]['status'], got['unavailable'][1]['screen']['cells_regridded'], got['present'][0]['status']), ('PARTIAL', 0, 'OK'))

    def test_every_own_cell_stands_in_its_table_model_slot(self):
        for name, (_, want) in CASES.items():
            for case, (route, _) in self.results[name][1].items():
                with self.subTest(table=name, resources=case):
                    self.assertEqual(slots(route), want)

    def test_every_cell_text_anchor_stays_inside_its_own_source_cell(self):  # the linker reads text in list order: repeated texts must keep their own occurrence
        for name in CASES:
            for case, (route, _) in self.results[name][1].items():
                with self.subTest(table=name, resources=case):
                    cells = [c for u in route['units'] if u['kind'] == 'table' for c in u['cells'] if c['text'].strip()]
                    self.assertTrue(all(c['source']['byte_start'] <= c['anchor']['byte_start'] < c['anchor']['byte_end_exclusive'] <= c['source']['byte_end_exclusive'] for c in cells))

    def test_a_nested_table_and_a_picture_keep_their_holder_slots_below_an_early_footer(self):
        from tests.driver.prepare.pictures.test_inputs import MEMBERS
        _, got = run(HOLDERS, {'p.png': MEMBERS['opaque.png']})
        for case, (route, _) in got.items():
            with self.subTest(resources=case):
                outer, inner = [u for u in route['units'] if u['kind'] == 'table']
                self.assertEqual(slots(route), [[(1, 0), (1, 1), (0, 0), (0, 1)]])  # tfoot F 9 drawn last; the holder row first
                self.assertEqual({k: inner['cell'][k] for k in ('table', 'r', 'c')}, {'table': outer['id'], 'r': 0, 'c': 0})
                picture = next(u for u in route['units'] if u['kind'] == 'image')
                self.assertEqual((picture['cell']['table'], picture['cell']['r'], picture['cell']['c']), (outer['id'], 0, 1))


if __name__ == '__main__':
    unittest.main()
