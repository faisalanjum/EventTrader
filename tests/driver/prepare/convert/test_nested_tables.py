"""A table standing in another table's cell is a table unit of its own (owner, Oct 10: preserve nested-table structure; root's design gate). Its cells are
gridded in their own source table and stand at their own bytes; it names its holder cell as a picture does (`cell`: {table, r, c}); the holder cell keeps
its native text (which holds the child's text) and names the child (`tables`). Required nested structure never disappears: a child holding only a picture
or only a caption is still a unit, and an empty holder cell still names it. Expected values come from each fixture's own markup and bytes."""
import hashlib
import unittest

from driver.prepare.convert import html_route

IN = lambda *cells: '<table><tr>' + ''.join('<td>%s</td>' % c for c in cells) + '</tr></table>'
H = lambda body: ('<!doctype html><html><head><meta charset="utf-8"></head><body>' + body + '</body></html>').encode()
PIC = '<img src="%s" width="20" height="10" alt="">'
# name: (page, [({(r, c): text}, holder (parent index, r, c) or None, caption list)], {picture src: (table index, r, c)})
CASES = {
    'flat (control)': (H('<table><tr><td>Europe</td><td>10</td></tr><tr><td>Asia</td><td>9</td></tr></table>'),
                       [({(0, 0): 'Europe', (0, 1): '10', (1, 0): 'Asia', (1, 1): '9'}, None, [])], {}),
    'one level': (H('<table><tr><td>Europe</td><td>10</td></tr><tr><td>Asia</td><td>' + IN('inner', '9') + '</td></tr></table>'),
                  [({(0, 0): 'Europe', (0, 1): '10', (1, 0): 'Asia', (1, 1): 'inner 9'}, None, []), ({(0, 0): 'inner', (0, 1): '9'}, (0, 1, 1), [])], {}),
    'two levels': (H('<table><tr><td>Europe</td><td>10</td></tr><tr><td>Asia</td><td><table><tr><td>mid</td><td>' + IN('deep', '7') + '</td></tr></table></td></tr></table>'),
                   [({(0, 0): 'Europe', (0, 1): '10', (1, 0): 'Asia', (1, 1): 'mid deep 7'}, None, []), ({(0, 0): 'mid', (0, 1): 'deep 7'}, (0, 1, 1), []),
                    ({(0, 0): 'deep', (0, 1): '7'}, (1, 0, 1), [])], {}),
    'text before and after the child': (H('<table><tr><td>Europe</td><td>10</td></tr><tr><td>Asia</td><td>before ' + IN('inner', '9') + ' after</td></tr></table>'),
                                        [({(0, 0): 'Europe', (0, 1): '10', (1, 0): 'Asia', (1, 1): 'before inner 9 after'}, None, []), ({(0, 0): 'inner', (0, 1): '9'}, (0, 1, 1), [])], {}),
    'repeated labels in the outer table and two siblings': (
        H('<table><tr><td>Total</td><td>10</td></tr><tr><td>Asia</td><td>' + IN('Total', '10') + IN('Total', '10') + '</td></tr></table>'),
        [({(0, 0): 'Total', (0, 1): '10', (1, 0): 'Asia', (1, 1): 'Total 10 Total 10'}, None, []), ({(0, 0): 'Total', (0, 1): '10'}, (0, 1, 1), []),
         ({(0, 0): 'Total', (0, 1): '10'}, (0, 1, 1), [])], {}),
    'picture in a child cell with text': (H('<table><tr><td>Europe</td><td>10</td></tr><tr><td>Asia</td><td>' + IN('inner ' + PIC % 'p.png', '9') + '</td></tr></table>'),
                                          [({(0, 0): 'Europe', (0, 1): '10', (1, 0): 'Asia', (1, 1): 'inner 9'}, None, []), ({(0, 0): 'inner', (0, 1): '9'}, (0, 1, 1), [])],
                                          {'p.png': (1, 0, 0)}),
    'child holding only a picture (empty holder)': (H('<table><tr><td>Asia</td><td>' + IN(PIC % 'q.png') + '</td></tr></table>'),
                                                    [({(0, 0): 'Asia', (0, 1): ''}, None, []), ({(0, 0): ''}, (0, 0, 1), [])], {'q.png': (1, 0, 0)}),  # v2: the child's own (blank) cell
    'child with a caption and no cell text': (H('<table><tr><td>Asia</td><td><table><caption>Cap only</caption><tr><td></td></tr></table></td></tr></table>'),
                                              [({(0, 0): 'Asia', (0, 1): 'Cap only'}, None, []), ({(0, 0): ''}, (0, 0, 1), ['Cap only'])], {}),  # v2: its blank cell
    'child with header, spans and an empty cell': (
        H('<table><tr><td>Asia</td><td><table><thead><tr><th colspan="2">Head</th></tr></thead><tbody><tr><td rowspan="2">L</td><td></td></tr><tr><td>v</td></tr></tbody></table></td></tr></table>'),
        [({(0, 0): 'Asia', (0, 1): 'Head L v'}, None, []), ({(0, 0): 'Head', (1, 0): 'L', (1, 1): '', (2, 1): 'v'}, (0, 0, 1), [])], {}),  # v2: the blank (1, 1)
    'two parents each with a child': (H('<table><tr><td>A</td><td>' + IN('a1', '1') + '</td></tr></table><table><tr><td>B</td><td>' + IN('b1', '2') + '</td></tr></table>'),
                                      [({(0, 0): 'A', (0, 1): 'a1 1'}, None, []), ({(0, 0): 'a1', (0, 1): '1'}, (0, 0, 1), []),
                                       ({(0, 0): 'B', (0, 1): 'b1 2'}, None, []), ({(0, 0): 'b1', (0, 1): '2'}, (2, 0, 1), [])], {}),
    'no mapping (a table in a div, not a cell)': (H('<table><tr><td>Europe</td><td>10</td></tr></table><div>' + IN('free', '3') + '</div>'),
                                                  [({(0, 0): 'Europe', (0, 1): '10'}, None, []), ({(0, 0): 'free', (0, 1): '3'}, None, [])], {}),
}
fold = lambda s: ' '.join((s or '').split())


def tables(route):
    return [u for u in route['units'] if u['kind'] == 'table']


class NestedTables(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright  # required: a missing install fails the suite
        cls.routes = {}
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                for name, (raw, _, _) in CASES.items(): cls.routes[name] = html_route.prepare(raw, 'nested.htm', hashlib.sha256(raw).hexdigest(), browser)[0]
            finally: browser.close()

    def test_every_source_table_is_a_unit_in_source_order_gridded_in_itself(self):
        for name, (raw, want, _) in CASES.items():
            with self.subTest(name):
                route = self.routes[name]; caps = [u for u in route['units'] if u['kind'] == 'caption']
                self.assertEqual(route['status'], 'OK')
                own = lambda t: [c['text'] for c in caps if c.get('source_table') == t.get('source_table') and raw[c['anchor']['byte_start']:c['anchor']['byte_end_exclusive']].decode() == c['text']]
                self.assertEqual([({(c['r'], c['c']): fold(c['text']) for c in u['cells']}, own(u)) for u in tables(route)],
                                 [(cells, caption) for cells, _, caption in want])  # a table's caption is its own caption unit, at its own source bytes (caption design v2)
                self.assertEqual(([u.get('caption', []) for u in tables(route)], len(caps)), ([[] for _ in want], sum(len(caption) for _, _, caption in want)))  # no bare copy; each caption once

    def test_a_child_names_its_holder_and_the_holder_names_the_child(self):
        for name, (_, want, _) in CASES.items():
            units = tables(self.routes[name])
            if len(units) != len(want): continue  # counted above
            for k, (_, holder, _) in enumerate(want):
                with self.subTest(name, table=k):
                    cell = units[k].get('cell')
                    self.assertEqual(None if cell is None else (cell.get('table'), cell.get('r'), cell.get('c')), None if holder is None else (units[holder[0]]['id'],) + holder[1:])
                    if holder:
                        h = [c for c in units[holder[0]]['cells'] if (c['r'], c['c']) == holder[1:]]
                        self.assertEqual(len(h), 1); self.assertIn(units[k]['id'], h[0].get('tables', []))

    def test_every_child_cell_stands_at_its_own_bytes(self):  # the n-th child table's text, searched for in that table's own bytes only
        for name, (raw, want, _) in CASES.items():
            units = tables(self.routes[name])
            if len(units) != len(want): continue
            starts = [i for i in range(len(raw)) if raw.startswith(b'<table', i)]
            for k, u in enumerate(units):
                for c in u['cells']:
                    if (c['r'], c['c']) in want[k][0] and want[k][1] is not None and c['text'].strip() and 'tables' not in c:
                        with self.subTest(name, table=k, cell=c['text']):
                            at = raw.index(b'>' + c['text'].strip().encode(), starts[k]) + 1  # a cell's text where the cell's content starts: "1" is not the 1 of "a1"
                            self.assertEqual(c['anchor']['byte_start'], at)

    def test_a_picture_names_the_cell_of_its_own_table(self):
        for name, (_, _, pics) in CASES.items():
            units = tables(self.routes[name])
            for src, (k, r, c) in pics.items():
                with self.subTest(name, src=src):
                    p = next(u for u in self.routes[name]['units'] if u['kind'] == 'image' and u.get('src') == src)
                    self.assertEqual((p['cell'].get('table'), p['cell'].get('r'), p['cell'].get('c')), (units[k]['id'] if k < len(units) else None, r, c))


if __name__ == '__main__':
    unittest.main()
