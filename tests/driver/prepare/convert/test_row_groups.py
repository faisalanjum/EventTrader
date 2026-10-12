"""Every own row of a table reaches the route (Root, extraction closeout, Oct 10): EdgarTools 5.60.0 reads only the first own <tbody> when a table has
one, so the rows of later bodies, a footer and rows standing straight in the table became one flat `uncovered` run with status OK. Expected cells -
(row, column, rows, columns, text) - come from each fixture's own markup and Chromium's table order (a footer is shown last; a second <thead> keeps its
place); every one must stand in the route with an anchor whose source bytes hold its text. Nothing is left uncovered: a caption is its table's own
caption unit (caption design v2; before it, the caption was the table's caption text with no anchor, left uncovered). Row retention only: not complete-table scoring."""
import hashlib
import re
import unittest

from driver.prepare.convert import html_route

T = lambda body: ('<!doctype html><html><head><meta charset="utf-8"></head><body><table>' + body + '</table></body></html>').encode()
CASES = {
    'two_bodies': (T('<tbody><tr><td>Europe</td><td>10</td></tr></tbody><tbody><tr><td>Asia</td><td>30</td></tr></tbody>'),
                   [(0, 0, 1, 1, 'Europe'), (0, 1, 1, 1, '10'), (1, 0, 1, 1, 'Asia'), (1, 1, 1, 1, '30')]),
    'three_bodies_picture_in_a_later_one': (
        T('<tbody><tr><td>Europe</td><td>10</td></tr></tbody><tbody><tr><td>Asia</td><td><img src="asia.png" alt="a"> 30</td></tr></tbody>'
          '<tbody><tr><td>Africa</td><td>50</td></tr></tbody>'),
        [(0, 0, 1, 1, 'Europe'), (0, 1, 1, 1, '10'), (1, 0, 1, 1, 'Asia'), (1, 1, 1, 1, '30'), (2, 0, 1, 1, 'Africa'), (2, 1, 1, 1, '50')]),
    'body_then_footer': (T('<tbody><tr><td>Europe</td><td>10</td></tr></tbody><tfoot><tr><td>Total</td><td>10</td></tr></tfoot>'),
                         [(0, 0, 1, 1, 'Europe'), (0, 1, 1, 1, '10'), (1, 0, 1, 1, 'Total'), (1, 1, 1, 1, '10')]),
    'footer_written_before_body': (T('<tfoot><tr><td>Total</td><td>10</td></tr></tfoot><tbody><tr><td>Europe</td><td>10</td></tr></tbody>'),
                                   [(0, 0, 1, 1, 'Europe'), (0, 1, 1, 1, '10'), (1, 0, 1, 1, 'Total'), (1, 1, 1, 1, '10')]),
    'direct_rows_then_body': (T('<tr><td>Direct</td><td>1</td></tr><tbody><tr><td>Grouped</td><td>2</td></tr></tbody>'),
                              [(0, 0, 1, 1, 'Direct'), (0, 1, 1, 1, '1'), (1, 0, 1, 1, 'Grouped'), (1, 1, 1, 1, '2')]),
    'occupied_following_group_labels': (
        T('<thead><tr><th rowspan="2">Region</th><th>Revenue</th></tr><tr><th>USD m</th></tr></thead>'
          '<tbody><tr><td rowspan="0">Europe <img src="flag.png" alt="flag"></td><td>10</td></tr><tr><td>20</td></tr></tbody>'
          '<tbody><tr><td rowspan="9999">Asia</td><td>30</td></tr><tr><td>40</td></tr></tbody>'
          '<tbody><tr><td rowspan="1">Africa</td><td>50</td></tr><tr><td>Other</td><td>60</td></tr></tbody>'
          '<tbody><tr><td rowspan="2">Oceania</td><td>70</td></tr><tr><td>80</td></tr></tbody>'),
        [(0, 0, 2, 1, 'Region'), (0, 1, 1, 1, 'Revenue'), (1, 1, 1, 1, 'USD m'), (2, 0, 2, 1, 'Europe'), (2, 1, 1, 1, '10'), (3, 1, 1, 1, '20'),
         (4, 0, 2, 1, 'Asia'), (4, 1, 1, 1, '30'), (5, 1, 1, 1, '40'), (6, 0, 1, 1, 'Africa'), (6, 1, 1, 1, '50'), (7, 0, 1, 1, 'Other'),
         (7, 1, 1, 1, '60'), (8, 0, 2, 1, 'Oceania'), (8, 1, 1, 1, '70'), (9, 1, 1, 1, '80')]),
    'repeated_thead': (T('<thead><tr><th>H1</th><th>H2</th></tr></thead><thead><tr><th>H3</th><th>H4</th></tr></thead><tbody><tr><td>a</td><td>1</td></tr></tbody>'),
                       [(0, 0, 1, 1, 'H1'), (0, 1, 1, 1, 'H2'), (1, 0, 1, 1, 'H3'), (1, 1, 1, 1, 'H4'), (2, 0, 1, 1, 'a'), (2, 1, 1, 1, '1')]),
    # controls: shapes the tool already read whole
    'single_body (control)': (T('<tbody><tr><td>Europe</td><td>10</td></tr><tr><td>Asia</td><td>30</td></tr></tbody>'),
                              [(0, 0, 1, 1, 'Europe'), (0, 1, 1, 1, '10'), (1, 0, 1, 1, 'Asia'), (1, 1, 1, 1, '30')]),
    'footer_without_body (control: once)': (T('<tr><td>Europe</td><td>10</td></tr><tfoot><tr><td>Total</td><td>10</td></tr></tfoot>'),
                                            [(0, 0, 1, 1, 'Europe'), (0, 1, 1, 1, '10'), (1, 0, 1, 1, 'Total'), (1, 1, 1, 1, '10')]),
    'caption_and_header (control)': (T('<caption>Results</caption><thead><tr><th>Region</th><th>Revenue</th></tr></thead>'
                                       '<tbody><tr><td>Europe</td><td>10</td></tr></tbody><tbody><tr><td>Asia</td><td>30</td></tr></tbody>'),
                                     [(0, 0, 1, 1, 'Region'), (0, 1, 1, 1, 'Revenue'), (1, 0, 1, 1, 'Europe'), (1, 1, 1, 1, '10'), (2, 0, 1, 1, 'Asia'), (2, 1, 1, 1, '30')]),
}
NESTED = T('<tbody><tr><td>Outer<table><tbody><tr><td>Inner</td></tr></tbody><tbody><tr><td>Inner2</td></tr></tbody></table></td><td>9</td></tr></tbody>'
           '<tbody><tr><td>Outer2</td><td>8</td></tr></tbody>')
TAGS = re.compile(rb'<[^>]*>')


from tests.driver.prepare.convert.test_picture_visibility import honest_negative, paired

class EveryOwnRow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright  # required: a missing install fails the suite
        cls.routes, cls.negatives = {}, {}
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                for name, raw in [(k, v[0]) for k, v in CASES.items()] + [('nested', NESTED)]:
                    cls.negatives[name], cls.routes[name], _ = paired(raw, name + '.htm', browser, ('flag.png', 'asia.png'))
            finally: browser.close()

    def cells(self, name):
        return [c for u in self.routes[name]['units'] if u['kind'] == 'table' for c in u['cells']]

    def test_without_their_pictures_the_original_inputs_are_honest_negatives(self):
        for name in self.routes:
            with self.subTest(name): honest_negative(self, self.negatives[name], self.routes[name])

    def test_every_case_is_ok_and_only_the_known_caption_range_stays_uncovered(self):
        for name in self.routes:
            raw = CASES[name][0] if name in CASES else NESTED
            at = raw.find(b'<caption>Results') + len(b'<caption>')  # the known caption range: before caption design v2 it stayed uncovered (the table's caption text had no anchor)
            caption = [{'byte_start': at, 'byte_end_exclusive': at + len('Results'), 'text': 'Results'}] if b'<caption>' in raw else []
            with self.subTest(name):
                route = self.routes[name]; self.assertEqual((route['status'], route['uncovered']), ('OK', []))  # its own caption unit covers it now
                if caption:  # and only that unit: without it, exactly the known caption range is uncovered again
                    from benchmarks.prepare.grader import grade
                    gone = dict(route, units=[u for u in route['units'] if u['kind'] != 'caption']); g = grade.gates_for_file(grade.RouteFile(gone, raw, 'html'), gone['status'])
                    self.assertEqual([(x['byte_start'], x['byte_end_exclusive'], x['text']) for x in g['uncovered']], [(c['byte_start'], c['byte_end_exclusive'], c['text']) for c in caption])

    def test_the_complete_occupied_inventory_and_coordinates(self):
        for name, (raw, expected) in CASES.items():
            with self.subTest(name):
                got = sorted((c['r'], c['c'], c['rs'], c.get('cs', 1), c['text'].strip()) for c in self.cells(name))
                self.assertEqual(got, sorted(expected))

    def test_every_cell_stands_at_its_own_source_text(self):
        for name, (raw, _) in CASES.items():
            for c in self.cells(name):
                a = c['anchor']
                with self.subTest(name, cell=c['text']): self.assertIn(c['text'].strip().encode(), b' '.join(TAGS.sub(b' ', raw[a['byte_start']:a['byte_end_exclusive']]).split()))

    def test_a_picture_in_a_later_group_keeps_its_cell(self):
        for name, src, rc in (('three_bodies_picture_in_a_later_one', 'asia.png', (1, 1)), ('occupied_following_group_labels', 'flag.png', (2, 0))):
            with self.subTest(name):
                pic = next(u for u in self.routes[name]['units'] if u['kind'] == 'image' and u.get('src') == src)
                self.assertEqual((pic['cell']['r'], pic['cell']['c']), rc)

    def test_a_caption_and_header_flags_are_kept(self):
        r, raw = self.routes['caption_and_header (control)'], CASES['caption_and_header (control)'][0]; t = next(u for u in r['units'] if u['kind'] == 'table')
        self.assertEqual((t['caption'], [(u['text'], raw[u['anchor']['byte_start']:u['anchor']['byte_end_exclusive']], u['source_table'] == t['source_table']) for u in r['units'] if u['kind'] == 'caption']),
                         ([], [('Results', b'Results', True)]))  # the table's own caption unit, once, at its own source bytes; no bare copy (caption design v2)
        self.assertEqual({c['text']: c['header'] for c in t['cells'] if c['text'] in ('Region', 'Revenue')}, {'Region': True, 'Revenue': True})

    def test_a_later_outer_row_is_kept_and_nested_rows_never_become_outer_rows(self):  # inner-table cells and both holder links are checked in test_nested_tables
        outer = next(u for u in self.routes['nested']['units'] if u['kind'] == 'table')
        rows = {(c['r'], c['c']): c['text'].strip() for c in outer['cells']}
        self.assertEqual((rows.get((1, 0)), rows.get((1, 1))), ('Outer2', '8'))
        self.assertNotIn('Inner2', rows.values())


if __name__ == '__main__':
    unittest.main()
