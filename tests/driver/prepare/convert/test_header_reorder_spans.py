"""Rows keep their source order where the tool promotes a later row to its headers (Root, fallback rowspan class, Oct 12). EdgarTools 5.60.0 keeps a
table's header rows and body rows apart (TableNode.headers, .rows) and reads a body row it takes for a header - one after a short or blank row - into
`headers`; its own grid (TableMatrix.build_from_rows) and our dump both stack headers first. A cell spanning rows then covers the wrong row, and when a
declared resource is unavailable the browser's geometry is withheld (PARTIAL), so nothing regrids it. Truth is the browser's own layout of the same
source with every resource present (each cell's box), never the converter; the source rows give the same slots by the HTML table model. Invented."""
import hashlib
import unittest

from driver.prepare.convert import html_route, screen_grid

CSS = 'td, th { padding: 2px; border: 1px solid black; }'
TABLES = {  # name -> rows; a row-spanning cell crosses the row the tool moves (or, in the controls, nothing moves)
    'short_row': '<tr><th rowspan="2">Item</th><th>Q1</th><th>Q2</th></tr><tr><td>a</td><td>b</td></tr><tr><td>Period</td><td>2024</td><td>2023</td></tr>'
                 '<tr><td>Revenue</td><td>10</td><td>9</td></tr>',
    'blank_row': '<tr><th rowspan="2">Item</th><th>Q1</th><th>Q2</th></tr><tr><td> </td><td></td></tr><tr><td>Period</td><td>2024</td><td>2023</td></tr>'
                 '<tr><td>Revenue</td><td>10</td><td>9</td></tr>',
    'colspan_dash': '<tr><th rowspan="2">Line item</th><th colspan="2">Quarter</th></tr><tr><td>—</td><td>-</td></tr>'
                    '<tr><td>Fiscal</td><td>2021</td><td>2020</td></tr><tr><td>Net</td><td>7</td><td>6</td></tr>',
    'second_group': '<thead><tr><th rowspan="2">Item</th><th>Q1</th><th>Q2</th></tr><tr><th>a</th><th>b</th></tr></thead>'
                    '<tbody><tr><td rowspan="2"></td><td>c</td><td></td></tr><tr><td>2025</td><td>2024</td></tr><tr><td>Cost</td><td>4</td><td>3</td></tr></tbody>',
    'deep_span': '<tr><th>Item</th><th rowspan="3">Q1</th><th>Q2</th></tr><tr><td>x</td><td>y</td></tr><tr><td>Year</td><td>2019</td></tr>'
                 '<tr><td>Sales</td><td>5</td><td>8</td></tr>',
    'two_blank_rows': '<tr><th rowspan="3">Item</th><th>Q1</th><th>Q2</th></tr><tr><td></td><td></td></tr><tr><td> </td><td></td></tr>'
                      '<tr><td>Period</td><td>2024</td><td>2023</td></tr><tr><td>Revenue</td><td>10</td><td>9</td></tr>',
    'blank_after_short': '<tr><th rowspan="2">Item</th><th>Q1</th><th>Q2</th></tr><tr><td>a</td><td></td></tr><tr><td></td><td></td><td></td></tr>'
                         '<tr><td>Year</td><td>2022</td><td>2021</td></tr><tr><td>Revenue</td><td>10</td><td>9</td></tr>',
    'control_ordinary':'<tr><th>Item</th><th>2024</th><th>2023</th></tr><tr><td>Revenue</td><td>10</td><td>9</td></tr>',
    'control_span_in_order': '<tr><th rowspan="2">Item</th><th>Q1</th><th>Q2</th></tr><tr><th>a</th><th>b</th></tr><tr><td>Revenue</td><td>10</td><td>9</td></tr>',
}
EXPECTED = {'short_row': {'Item': (0, 0), 'Q1': (0, 1), 'Q2': (0, 2), 'a': (1, 1), 'b': (1, 2), 'Period': (2, 0), '2024': (2, 1), '2023': (2, 2),
                          'Revenue': (3, 0), '10': (3, 1), '9': (3, 2)}}  # by the HTML table model, from the source rows above
TRUTH = """() => { const cells = Array.from(document.querySelectorAll('td,th')); const at = (c, k) => Math.round(c.getBoundingClientRect()[k]);
  const L = [...new Set(cells.map(c => at(c, 'left')))].sort((a, b) => a - b), T = [...new Set(cells.map(c => at(c, 'top')))].sort((a, b) => a - b);
  return cells.filter(c => c.textContent.trim()).map(c => [c.textContent.trim(), T.indexOf(at(c, 'top')), L.indexOf(at(c, 'left'))]); }"""


def page(rows, link):
    head = '<link rel="stylesheet" href="s.css">' if link else '<style>' + CSS + '</style>'
    return ('<!doctype html><html><head><meta charset="utf-8">' + head + '</head><body><table>' + rows + '</table></body></html>').encode()


class HeaderReorderSpans(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright  # required: a missing install fails the suite
        cls.truth, cls.routes = {}, {}
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                for name, rows in TABLES.items():
                    tab = browser.new_page(); tab.set_content(page(rows, False).decode()); cls.truth[name] = {t: (r, c) for t, r, c in tab.evaluate(TRUTH)}; tab.close()
                    raw = page(rows, True)
                    for case, members in (('present', {'doc.htm': raw, 's.css': CSS.encode()}), ('unavailable', {'doc.htm': raw})):
                        cls.routes[name, case] = html_route.prepare(raw, 'invented/' + name + '.htm', hashlib.sha256(raw).hexdigest(), browser, screen_grid.Source('doc.htm', members))
            finally: browser.close()

    def cells(self, name, case):
        route, _ = self.routes[name, case]
        return {c['text'].strip(): c for u in route['units'] if u['kind'] == 'table' for c in u['cells'] if c['text'].strip()}

    def test_the_browser_control_is_the_table_model(self):  # the independent truth agrees with the hand-read slots
        self.assertEqual(self.truth['short_row'], EXPECTED['short_row'])

    def test_an_unavailable_resource_still_withholds_geometry(self):  # the guard this class must keep
        for name in TABLES:
            with self.subTest(table=name):
                self.assertEqual(self.routes[name, 'unavailable'][0]['status'], 'PARTIAL')
                self.assertEqual(self.routes[name, 'unavailable'][1]['screen']['cells_regridded'], 0)
                self.assertEqual(self.routes[name, 'present'][0]['status'], 'OK')

    def test_every_cell_stands_in_its_source_row_and_column(self):  # with geometry and in the fallback without it
        for name in TABLES:
            for case in ('present', 'unavailable'):
                with self.subTest(table=name, resources=case):
                    self.assertEqual({t: (c['r'], c['c']) for t, c in self.cells(name, case).items()}, self.truth[name])

    def test_a_nested_table_and_a_picture_name_their_holder_cell_in_its_source_row(self):  # holders across the moved rows, with and without geometry
        rows = ('<tr><th rowspan="2">Item</th><th>Q1</th><th>Q2</th></tr><tr><td><table><tr><td>n</td></tr></table></td><td>b</td></tr>'
                '<tr><td>Period</td><td>2024 <img src="p.png" alt="p"></td><td>2023</td></tr><tr><td>Sales</td><td>5</td><td>8</td></tr>')
        from playwright.sync_api import sync_playwright
        from tests.driver.prepare.pictures.test_inputs import MEMBERS
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                raw = page(rows, True); got = {}
                for case, members in (('present', {'doc.htm': raw, 's.css': CSS.encode(), 'p.png': MEMBERS['opaque.png']}), ('unavailable', {'doc.htm': raw, 'p.png': MEMBERS['opaque.png']})):
                    got[case] = html_route.prepare(raw, 'invented/holders.htm', hashlib.sha256(raw).hexdigest(), browser, screen_grid.Source('doc.htm', members))[0]
            finally: browser.close()
        for case, route in got.items():
            with self.subTest(resources=case):
                outer, inner = [u for u in route['units'] if u['kind'] == 'table']
                holder = next(c for c in outer['cells'] if c.get('tables'))
                self.assertEqual((holder['r'], holder['c'], holder['tables']), (1, 1, [inner['id']]))  # source slot (1, 1): the outer table's second row, second column
                self.assertEqual({k: inner['cell'][k] for k in ('table', 'r', 'c')}, {'table': outer['id'], 'r': 1, 'c': 1})
                picture = next(u for u in route['units'] if u['kind'] == 'image')
                self.assertEqual((picture['cell']['table'], picture['cell']['r'], picture['cell']['c']), (outer['id'], 2, 1))  # the 2024 cell, source slot (2, 1)

    def test_repeated_labels_keep_each_occurrence_in_its_source_slot(self):  # several span lengths; equal texts in distinct cells: compared cell by cell in source order
        rows = ('<tr><th rowspan="3">Seg</th><th>Q</th><th>Q</th></tr><tr><td>a</td><td>a</td></tr><tr><td>b</td><td>b</td></tr><tr><td>Period</td><td>2024</td><td>2024</td></tr>'
                '<tr><td>x</td><td>1</td><td>1</td></tr></table><table><tr><th rowspan="2">Seg</th><th>Q</th><th>Q</th></tr><tr><td>a</td><td>a</td></tr>'
                '<tr><td>Period</td><td>2024</td><td>2023</td></tr><tr><td>x</td><td>1</td><td>1</td></tr>')
        slots = """() => Array.from(document.querySelectorAll('table')).map(t => { const cells = Array.from(t.querySelectorAll('td,th')); const at = (c, k) => Math.round(c.getBoundingClientRect()[k]);
          const L = [...new Set(cells.map(c => at(c, 'left')))].sort((a, b) => a - b), T = [...new Set(cells.map(c => at(c, 'top')))].sort((a, b) => a - b);
          return cells.map(c => [T.indexOf(at(c, 'top')), L.indexOf(at(c, 'left'))]); })"""
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                tab = browser.new_page(); tab.set_content(page(rows, False).decode()); truth = tab.evaluate(slots); tab.close()
                raw = page(rows, True); got = {}
                for case, members in (('present', {'doc.htm': raw, 's.css': CSS.encode()}), ('unavailable', {'doc.htm': raw})):
                    got[case] = html_route.prepare(raw, 'invented/repeated.htm', hashlib.sha256(raw).hexdigest(), browser, screen_grid.Source('doc.htm', members))[0]
            finally: browser.close()
        for case, route in got.items():
            with self.subTest(resources=case):
                tables = [u for u in route['units'] if u['kind'] == 'table']
                self.assertEqual([[[c['r'], c['c']] for c in sorted(u['cells'], key=lambda c: c['source']['byte_start'])] for u in tables], truth)  # each own cell, in source order

    def test_the_tool_header_reading_spans_and_text_are_kept(self):  # the fix orders rows; it decides nothing about headers, spans or text
        for name in TABLES:
            with self.subTest(table=name):
                a, b = self.cells(name, 'present'), self.cells(name, 'unavailable')
                self.assertEqual({t: (c['header'], c['rs'], c['cs'], c['text']) for t, c in a.items()}, {t: (c['header'], c['rs'], c['cs'], c['text']) for t, c in b.items()})


if __name__ == '__main__':
    unittest.main()
