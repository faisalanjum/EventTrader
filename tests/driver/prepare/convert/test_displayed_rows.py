"""A measured table's rows are numbered in the order the page shows them (Root, browser row order finding, Oct 12). screen_grid.JS took each cell's row
from the DOM's `tr.rowIndex`, which lists the table's first thead first and its first tfoot last, whatever CSS shows: a group drawn as the header or footer
group by `display`, a second thead or tfoot (drawn as a body group where written) stood at the wrong row with status OK. Rows are now ranked by their own
native box (`tr.getBoundingClientRect().top`; a row with no box stays after the row before it, and equal tops keep their DOM order), spans stay the
browser's table-model spans. Expected slots are hand-read from the source and its CSS. Every resource present (qualifying geometry). Invented."""
import hashlib
import unittest

from driver.prepare.convert import html_route, screen_grid
from tests.driver.prepare.convert import test_header_reorder_spans as base  # page(), CSS (module import: its TestCase is not collected twice)

HEAD, FOOT = ' style="display:table-header-group"', ' style="display:table-footer-group"'
CASES = {  # name -> (rows, every own cell of the first table in source order: (r, c[, rs]))
    'css_header_group': (f'<tbody><tr><td>v</td><td>1</td></tr></tbody><tbody{HEAD}><tr><td>H</td><td>2024</td></tr></tbody>', [(1, 0), (1, 1), (0, 0), (0, 1)]),
    'css_footer_group': (f'<tbody{FOOT}><tr><td>T</td><td>9</td></tr></tbody><tbody><tr><td>v</td><td>1</td></tr></tbody>', [(1, 0), (1, 1), (0, 0), (0, 1)]),
    'two_theads': ('<thead><tr><th>H1</th></tr></thead><tbody><tr><td>v</td></tr></tbody><thead><tr><th>H2</th></tr></thead>', [(0, 0), (1, 0), (2, 0)]),
    'two_tfoots': ('<tfoot><tr><td>F1</td></tr></tfoot><tbody><tr><td>v</td></tr></tbody><tfoot><tr><td>F2</td></tr></tfoot>', [(2, 0), (0, 0), (1, 0)]),
    'span_in_moved_group': (f'<tbody><tr><td>v</td><td>1</td></tr></tbody><tbody{HEAD}><tr><td rowspan="2">H</td><td>a</td></tr><tr><td>b</td></tr></tbody>',
                            [(2, 0, 1), (2, 1, 1), (0, 0, 2), (0, 1, 1), (1, 1, 1)]),
    'repeated_in_moved_group': (f'<tbody><tr><td>Q</td><td>Q</td></tr></tbody><tbody{HEAD}><tr><td>Q</td><td>Q</td></tr></tbody>', [(1, 0), (1, 1), (0, 0), (0, 1)]),
    'tiny_spacer_row': ('<tr><td>A</td><td>1</td></tr><tr style="height:2px;font-size:1px;line-height:1px"><td style="padding:0">s</td><td style="padding:0">t</td></tr>'
                        '<tr><td>B</td><td>2</td></tr>', [(0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1)]),
    'zero_height_row': ('<tr><td>A</td></tr><tr style="height:0;font-size:0;line-height:0"><td style="padding:0">z</td></tr><tr><td>B</td></tr>', [(0, 0), (1, 0), (2, 0)]),
    'visibility_hidden_row': ('<tr><td>A</td></tr><tr style="visibility:hidden"><td>V</td></tr><tr><td>B</td></tr>', [(0, 0), (1, 0), (2, 0)]),
    'empty_row_in_span': ('<tr><td rowspan="2">A</td><td>1</td></tr><tr></tr><tr><td>x</td><td>y</td></tr>', [(0, 0, 2), (0, 1, 1), (2, 0, 1), (2, 1, 1)]),
    'control_plain': ('<tr><th>Item</th><th>2024</th></tr><tr><td>Revenue</td><td>10</td></tr>', [(0, 0), (0, 1), (1, 0), (1, 1)]),
}
HIDDEN = '<tr><td>A</td></tr><tr style="display:none"><td>H</td></tr><tr><td>B</td></tr>'  # a row with no box keeps its place after the row before it
NESTED = (f'<tbody><tr><td>v</td><td><table><tr><td>n</td></tr></table></td></tr></tbody><tbody{HEAD}><tr><td>H</td><td>h</td></tr></tbody>')


def run(rows):
    from playwright.sync_api import sync_playwright  # required: a missing install fails the suite
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            raw = base.page(rows, True)
            return html_route.prepare(raw, 'invented/rows.htm', hashlib.sha256(raw).hexdigest(), browser, screen_grid.Source('doc.htm', {'doc.htm': raw, 's.css': base.CSS.encode()}))[0]
        finally: browser.close()


def own(route, k=0):
    tables = [u for u in route['units'] if u['kind'] == 'table']
    return sorted(tables[k]['cells'], key=lambda c: c['source']['byte_start']), tables


class DisplayedRows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.routes = {name: run(rows) for name, (rows, _) in CASES.items()}

    def test_every_cell_stands_in_its_displayed_row(self):
        for name, (_, want) in CASES.items():
            with self.subTest(table=name):
                route = self.routes[name]; cells, _ = own(route)
                self.assertEqual(route['status'], 'OK')
                self.assertEqual([(c['r'], c['c']) + ((c['rs'],) if len(w) == 3 else ()) for c, w in zip(cells, want)], want)

    def test_a_row_with_no_box_keeps_its_place(self):
        cells, _ = own(run(HIDDEN))
        self.assertEqual([(cells[0]['text'], cells[0].get('r')), (cells[2]['text'], cells[2].get('r'))], [('A', 0), ('B', 2)])  # the hidden row (its text left out) stays row 1

    def test_a_nested_table_names_its_holder_in_the_displayed_row(self):
        route = run(NESTED); cells, tables = own(route); inner = tables[1]
        self.assertEqual([(c['r'], c['c']) for c in cells], [(1, 0), (1, 1), (0, 0), (0, 1)])
        self.assertEqual({k: inner['cell'][k] for k in ('table', 'r', 'c')}, {'table': tables[0]['id'], 'r': 1, 'c': 1})


if __name__ == '__main__':
    unittest.main()
