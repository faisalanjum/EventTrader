"""A cell's rows end where the HTML table model ends them (Root, extraction closeout, Oct 10): rowspan="0" runs to the end of its row group and a
larger span stops there (thead/tbody/tfoot). The browser already measures that span for every cell (screen_grid.JS `rs`); a text cell must state it as
a picture in the same cell does, so a label never claims the rows of the next row group. Expected values come from the fixture's own row groups
(thead rows 0-1, tbody rows 2-4). One body group only: EdgarTools 5.60.0 reads the first <tbody> alone (its later groups are a separate finding)."""
import hashlib
import unittest

from driver.prepare.convert import html_route

PAGE = ('<!doctype html><html><head><meta charset="utf-8"></head><body><table>'
        '<thead><tr><th rowspan="9999">Region</th><th colspan="2">Revenue</th></tr><tr><th>2025</th><th>2024</th></tr></thead>'
        '<tbody><tr><td rowspan="0">Europe <img src="flag.png" alt="flag"></td><td rowspan="2">10</td><td>11</td></tr>'
        '<tr><td>12</td></tr><tr><td rowspan="1">13</td><td>14</td></tr></tbody>'
        '</table></body></html>').encode()
EXPECTED = {'Region': (0, 0, 2), 'Revenue': (0, 1, 1), '2025': (1, 1, 1), '2024': (1, 2, 1), 'Europe': (2, 0, 3), '10': (2, 1, 2), '11': (2, 2, 1),
            '12': (3, 2, 1), '13': (4, 1, 1), '14': (4, 2, 1)}  # text -> (row, column, rows)
GROUPS = [range(0, 2), range(2, 5)]


from tests.driver.prepare.convert.test_picture_visibility import honest_negative, paired

class RowGroupSpans(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright  # required: a missing install fails the suite
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try: cls.negative, cls.route, cls.facts = paired(PAGE, 'rowspan.htm', browser, ('flag.png',))
            finally: browser.close()
        cls.cells = {c['text'].strip(): c for u in cls.route['units'] if u['kind'] == 'table' for c in u['cells']}

    def test_without_its_picture_the_original_input_is_an_honest_negative(self): honest_negative(self, self.negative, self.route)

    def test_the_route_is_whole(self):
        self.assertEqual(self.route['status'], 'OK')
        self.assertEqual(set(self.cells), set(EXPECTED))
        self.assertEqual(self.route['uncovered'], [])

    def test_every_cell_states_the_rows_the_table_model_gives_it(self):  # zero, oversized (a header) and ordinary spans, and the controls
        self.assertEqual({k: (c['r'], c['c'], c['rs']) for k, c in self.cells.items()}, EXPECTED)

    def test_no_span_leaves_its_row_group(self):  # the relation, not the number: the header label must not cover the body's rows
        for name, c in self.cells.items():
            group = next(g for g in GROUPS if c['r'] in g)
            self.assertLessEqual(c['r'] + c['rs'] - 1, group[-1], name)

    def test_a_picture_and_the_text_of_one_cell_state_the_same_rows(self):
        flag = next(u for u in self.route['units'] if u['kind'] == 'image' and u.get('src') == 'flag.png')
        europe = self.cells['Europe']
        self.assertEqual((flag['cell']['r'], flag['cell']['c'], flag['cell']['rs']), (europe['r'], europe['c'], europe['rs']))


if __name__ == '__main__':
    unittest.main()
