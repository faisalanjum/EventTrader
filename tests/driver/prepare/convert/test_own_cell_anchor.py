"""A table cell bound to its own source cell (`source`, to_units) is read only inside that cell (Root, own-cell anchor finding, Oct 12). The linker placed
cell text by list order and equal text, so where the route lists cells out of the source's order (a thead written after its tbody) repeated texts took
another cell's occurrence, with geometry or without. Truth is each cell's own source extent, from the markup; never the converter. Invented sources."""
import hashlib
import unittest

from driver.prepare.convert import html_route, screen_grid
from tests.driver.prepare.convert import test_header_reorder_spans as base  # page(), CSS (module import: its TestCase is not collected twice)

CASES = {
    'late_thead_repeated': '<tbody><tr><td>Q</td><td>Q</td></tr><tr><td>Q</td><td>Q</td></tr></tbody><thead><tr><th>Q</th><th>Q</th></tr></thead>',
    'early_tfoot_repeated': '<tfoot><tr><td>Q</td><td>Q</td></tr></tfoot><tbody><tr><td rowspan="2">Q</td><td>Q</td></tr><tr><td>Q</td></tr></tbody>',
    'nested_overlap': '<tr><td><table><tr><td>Q</td></tr></table></td><td>Q</td></tr><tr><td>Q</td><td>Q</td></tr>',
    'struck_and_plain': '<tbody><tr><td><s>Q</s></td><td>Q</td></tr></tbody><thead><tr><th>Q</th><th><s>Q</s></th></tr></thead>',
    'long_repeated': '<tbody><tr><td>Revenue from operations</td><td>Revenue from operations</td></tr></tbody><thead><tr><th>Revenue from operations</th><th>x</th></tr></thead>',
    'control_in_order': '<tr><th>Q</th><th>Q</th></tr><tr><td>Q</td><td>Q</td></tr>',
}


def inside(c):  # every piece of the cell's anchor lies inside its own source cell
    s, a = c['source'], c.get('anchor')
    return a is not None and all(s['byte_start'] <= x['byte_start'] < x['byte_end_exclusive'] <= s['byte_end_exclusive'] for x in (a if isinstance(a, list) else [a]))


class OwnCellAnchor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright  # required: a missing install fails the suite
        cls.routes = {}
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                for name, rows in CASES.items():
                    raw = base.page(rows, True)
                    for case, members in (('present', {'doc.htm': raw, 's.css': base.CSS.encode()}), ('unavailable', {'doc.htm': raw})):
                        cls.routes[name, case] = html_route.prepare(raw, 'invented/own.htm', hashlib.sha256(raw).hexdigest(), browser, screen_grid.Source('doc.htm', members))[0]
            finally: browser.close()

    def test_every_bound_cell_reads_its_own_occurrence(self):
        for (name, case), route in self.routes.items():
            with self.subTest(table=name, resources=case):
                cells = [c for u in route['units'] if u['kind'] == 'table' for c in u['cells'] if c['text'].strip()]
                self.assertTrue(cells and all(c.get('source') for c in cells))  # the binding exists (to_units)
                self.assertEqual([c['text'] for c in cells if not inside(c)], [])

    def test_the_resource_guard_is_kept(self):
        for (name, case), route in self.routes.items():
            with self.subTest(table=name, resources=case):
                self.assertEqual(route['status'], 'OK' if case == 'present' else 'PARTIAL')


if __name__ == '__main__':
    unittest.main()
