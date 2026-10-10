"""Every own cell of a retained table is a route cell bound to its own source cell (root, Oct 10, table-source v2): its native text (possibly empty) and
`source` - the cell's own byte span, carried through the tool by the same injected-code rule as tables - with its measured place only where that source
cell was measured. No text, depth or order inference: a holder, a blank cell and a picture's cell are all found by that identity. Expected spans come
from each fixture's own markup (every <td>/<th> start, in document order), not from the adapter."""
import hashlib
import re
import unittest

from driver.prepare.convert import anchor, edgartools_html as adapter, html_route

T = lambda body: ('<!doctype html><html><head><meta charset="utf-8"></head><body>' + body + '</body></html>').encode()
CELL = re.compile(rb'<t[dh][\s>]')
WRAP = T('<table><tr><td></td><td><table><tr><td></td><td></td><td><table><tr><td>x</td></tr></table></td></tr></table></td></tr></table>')
BLANKS = T('<table><tr><td></td><td>a</td><td></td><td>b</td><td></td></tr><tr><td colspan="2"></td><td rowspan="2"></td><td>c</td><td></td></tr>'
           '<tr><td><img src="p.png" width="20" height="10" alt=""></td><td>d</td><td></td><td>e</td></tr></table>')
MIXED = T('<table><tfoot><tr><td>Total</td><th>9</th></tr></tfoot><tbody><tr><th>Head</th><td>1</td></tr></tbody></table>')
SIBLINGS = T('<table><tr><td>Total</td><td>10</td></tr><tr><td>Asia</td><td><table><tr><td>Total</td><td>10</td></tr></table>'
             '<table><tr><td>Total</td><td>10</td></tr></table></td></tr></table>')
HIDDEN = T('<table><tr><td>a</td><td style="display:none">gone</td><td>b</td></tr></table>')
PIC_ONLY_CHILD = T('<table><tr><td>Asia</td><td><table><tr><td><img src="q.png" width="20" height="10" alt=""></td></tr></table></td></tr></table>')
NO_MAPPING = T('<table><tr><td>Europe</td><td>10</td></tr></table><div><table><tr><td>free</td><td>3</td></tr></table></div>')


def cell_starts(raw):
    return [m.start() for m in CELL.finditer(raw)]


class TableSource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright  # required: a missing install fails the suite
        cls.routes = {}
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                for name in ('WRAP', 'BLANKS', 'MIXED', 'SIBLINGS', 'HIDDEN', 'PIC_ONLY_CHILD', 'NO_MAPPING'):
                    raw = globals()[name]; cls.routes[name] = html_route.prepare(raw, name + '.htm', hashlib.sha256(raw).hexdigest(), browser)[0]
            finally: browser.close()

    def tables(self, name):
        return [u for u in self.routes[name]['units'] if u['kind'] == 'table']

    def test_every_own_cell_is_present_once_bound_to_its_own_source_cell(self):  # source-complete accounting: every <td>/<th> of every retained table
        for name in ('WRAP', 'BLANKS', 'MIXED', 'SIBLINGS', 'PIC_ONLY_CHILD', 'NO_MAPPING', 'HIDDEN'):
            with self.subTest(name):
                got = sorted(c['source']['byte_start'] for u in self.tables(name) for c in u['cells'] if c.get('source'))
                self.assertEqual(got, cell_starts(globals()[name]))

    def test_holders_in_an_all_blank_wrapper_chain_stand_in_their_own_columns(self):
        t0, t1, t2 = self.tables('WRAP')
        self.assertEqual([(t1['cell']['table'], t1['cell']['r'], t1['cell']['c']), (t2['cell']['table'], t2['cell']['r'], t2['cell']['c'])], [(t0['id'], 0, 1), (t1['id'], 0, 2)])
        self.assertEqual(sorted((c['r'], c['c'], c['text'].strip(), c.get('tables', [])) for c in t0['cells']), [(0, 0, '', []), (0, 1, 'x', [t1['id']])])
        self.assertEqual(sorted((c['r'], c['c'], c['text'].strip()) for c in t2['cells']), [(0, 0, 'x')])

    def test_blank_cells_and_blank_spans_keep_their_places(self):
        [t] = self.tables('BLANKS'); starts = cell_starts(BLANKS)
        by_start = {c['source']['byte_start']: (c['r'], c['c'], c['rs'], c['cs'], c['text'].strip()) for c in t['cells']}
        self.assertEqual([by_start[s] for s in starts],
                         [(0, 0, 1, 1, ''), (0, 1, 1, 1, 'a'), (0, 2, 1, 1, ''), (0, 3, 1, 1, 'b'), (0, 4, 1, 1, ''),
                          (1, 0, 1, 2, ''), (1, 2, 2, 1, ''), (1, 3, 1, 1, 'c'), (1, 4, 1, 1, ''),
                          (2, 0, 1, 1, ''), (2, 1, 1, 1, 'd'), (2, 3, 1, 1, ''), (2, 4, 1, 1, 'e')])
        p = next(u for u in self.routes['BLANKS']['units'] if u['kind'] == 'image')
        self.assertEqual((p['cell']['table'], p['cell']['r'], p['cell']['c'], p['cell']['byte_start']), (t['id'], 2, 0, starts[9]))

    def test_mixed_th_td_and_a_footer_written_first_keep_their_own_cells(self):
        [t] = self.tables('MIXED'); s = cell_starts(MIXED)
        self.assertEqual(sorted((c['source']['byte_start'], c['r'], c['c'], c['text']) for c in t['cells']),
                         sorted([(s[0], 1, 0, 'Total'), (s[1], 1, 1, '9'), (s[2], 0, 0, 'Head'), (s[3], 0, 1, '1')]))
        self.assertTrue(all(c['header'] for c in t['cells'] if c['source']['byte_start'] in (s[1], s[2])))  # its <th> cells (native header heuristics may add rows)

    def test_identical_sibling_values_stand_in_their_own_tables(self):
        units = self.tables('SIBLINGS'); s = cell_starts(SIBLINGS)
        self.assertEqual([[c['source']['byte_start'] for c in u['cells']] for u in units], [[s[0], s[1], s[2], s[3]], [s[4], s[5]], [s[6], s[7]]])
        self.assertEqual([(u['cell']['table'], u['cell']['r'], u['cell']['c']) for u in units[1:]], [(units[0]['id'], 1, 1)] * 2)

    def test_a_picture_only_child_keeps_its_empty_cell(self):
        t0, t1 = self.tables('PIC_ONLY_CHILD'); s = cell_starts(PIC_ONLY_CHILD)
        self.assertEqual([(c['source']['byte_start'], c['text'].strip()) for c in t1['cells']], [(s[2], '')])
        p = next(u for u in self.routes['PIC_ONLY_CHILD']['units'] if u['kind'] == 'image')
        self.assertEqual((p['cell']['table'], p['cell']['r'], p['cell']['c']), (t1['id'], 0, 0))

    def test_a_hidden_cell_has_its_source_but_no_measured_place(self):
        [t] = self.tables('HIDDEN'); s = cell_starts(HIDDEN)
        hidden = next(c for c in t['cells'] if c['source']['byte_start'] == s[1])
        self.assertEqual((hidden['text'].strip(), hidden.get('grid')), ('', None))

    def test_missing_altered_or_duplicated_codes_give_no_source_and_no_place(self):  # the adapter alone, on a tree the tool could have made
        raw = T('<table><tr><td>a</td><td>b</td><td>c</td></tr></table>'); vis = anchor.Visible(raw); known = adapter.codes(raw, vis)
        table = next(k for k, (s, n) in known.items() if n is None); cells = sorted((s, k) for k, (s, n) in known.items() if isinstance(n, tuple))
        row = [{'text': 'a', 'colspan': 1, 'rowspan': 1, 'is_header': False, 'code': cells[0][1]},             # valid control
               {'text': 'b', 'colspan': 1, 'rowspan': 1, 'is_header': False, 'code': cells[1][1] + 'x'},       # altered
               {'text': 'c', 'colspan': 1, 'rowspan': 1, 'is_header': False}]                                  # missing
        dup = [dict(row[0]), {'text': 'a2', 'colspan': 1, 'rowspan': 1, 'is_header': False, 'code': cells[0][1]}]  # one code twice
        for rows, want in (([row], [cells[0][0], None, None]), ([dup], [None, None])):
            units = adapter.route_for({'type': 'DocumentNode', 'children': [{'type': 'TableNode', 'caption': None, 'code': table, 'rows': rows}]}, raw, 'f.htm', 'sha', 0, 'v', vis=vis)['units']
            [t] = [u for u in units if u['kind'] == 'table']
            with self.subTest(rows=len(rows[0])): self.assertEqual([(c.get('source') or {}).get('byte_start') for c in t['cells']], want)

    def test_codes_lost_in_a_fresh_parse_keep_every_cell_with_no_source_and_no_place(self):  # root's probe: not an old dump
        from unittest import mock
        from playwright.sync_api import sync_playwright
        raw = T('<table><tr><td>A</td><td></td><td>B</td></tr></table>'); real = adapter.named; got = {}
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                for variant in ('valid', 'all cell codes lost'):
                    lose = (lambda *a, **k: re.sub(r' data-prepare-cell="[^"]*"', '', real(*a, **k))) if variant != 'valid' else real
                    with mock.patch.object(adapter, 'named', lose): got[variant] = html_route.prepare(raw, 'codes.htm', hashlib.sha256(raw).hexdigest(), browser)[0]
            finally: browser.close()
        cells = lambda v: [(c['text'], (c['source'] or {}).get('byte_start') if 'source' in c else 'absent', c.get('grid')) for u in got[v]['units'] if u['kind'] == 'table' for c in u['cells']]
        self.assertEqual(cells('valid'), [(t, s, 'screen') for t, s in zip(('A', '', 'B'), cell_starts(raw))])  # positive control
        self.assertEqual(cells('all cell codes lost'), [('A', None, None), ('', None, None), ('B', None, None)])  # kept, unbound, unplaced

    def test_a_table_outside_any_cell_names_no_holder(self):
        self.assertEqual([u.get('cell') for u in self.tables('NO_MAPPING')], [None, None])


TWINS = T('<table><tr><td>A</td><td></td></tr></table><table><tr><td>A</td><td></td></tr></table>')   # identical text, blank cells (root's loss control)
ENTITY = T('<table><tr><td>A&amp;B</td></tr></table>')                                                 # the tool's text differs from the source bytes


class TableProvenance(unittest.TestCase):  # root OCR_TABLE_PROVENANCE: the table's own source occurrence (its <table start tag) survives linking
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.routes = {}
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                for name in ('TWINS', 'ENTITY', 'SIBLINGS'):
                    raw = globals()[name]; cls.routes[name] = (raw, html_route.prepare(raw, name + '.htm', hashlib.sha256(raw).hexdigest(), browser)[0])
            finally: browser.close()

    def test_each_table_names_its_own_source_start_tag(self):  # expected: every <table start in the original bytes, in document order
        for name in ('TWINS', 'ENTITY', 'SIBLINGS'):
            with self.subTest(name):
                raw, route = self.routes[name]
                tabs = [u for u in route['units'] if u['kind'] == 'table']
                self.assertEqual([u['source_table'] for u in tabs], [{'tag_start': m.start(), 'claims': 1} for m in re.finditer(rb'<table', raw)])

    def test_unknown_split_and_legacy_identities_stay_distinct(self):  # the linker alone, on units an adapter could give
        raw = TWINS; start = raw.index(b'<table')
        unit = lambda i, **kw: {'id': f't{i}', 'kind': 'table', 'cells': [{'r': 0, 'c': 0, 'rs': 1, 'cs': 1, 'text': 'A'}], 'caption': [], **kw}
        units = [unit(0, tag=None), unit(1, tag=start), unit(2, tag=start), unit(3)]
        anchor.link(raw, units)
        self.assertEqual([u.get('source_table', 'absent') for u in units],
                         [None, {'tag_start': start, 'claims': 2}, {'tag_start': start, 'claims': 2}, 'absent'])   # unknown; one tag claimed twice; a legacy unit
        self.assertNotIn('tag', units[1])


if __name__ == '__main__':
    unittest.main()
