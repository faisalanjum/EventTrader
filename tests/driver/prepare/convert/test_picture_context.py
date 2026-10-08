"""A picture keeps where it stands in a table and what its source tag says about it (Codex, PICTURE_CONTEXT_ORDER.md; his PICTURE_BASELINE_PROBES and
OCR's 769 in-cell pictures). The route states a picture's row and column only in the coordinates of the route's own table, and only where that table is
laid out on one measured grid: the screen step gives the picture the measured row and column of its own source cell, as it gives a text cell there — an
image-only cell too (no text cell stands in it), and a picture beside text no longer keeps the tool's columns the step replaced (a hidden or zero-width
column). A route table holding cells of two grids (a table inside a table), a cell not measured, or no route table at all: the picture keeps its source
cell span and states no row or column. Every shown picture, the tool's own or added from the source, carries its tag's `alt` and `title` as written,
decoded once, first duplicate wins, empty kept apart from absent — evidence beside the picture, never its text. Expected places are read off the page
geometry by hand (the screen grid's columns are the distinct left edges of the shown cells; rows are the browser's row index), not from the candidate."""
import unittest

from driver.prepare.convert import anchor, html_route
from driver.prepare.convert import edgartools_html as adapter
from driver.prepare.convert import screen_grid as sg


def page(body): return b'<!doctype html><html><head><meta charset="utf-8"></head><body>' + body + b'</body></html>'


def pictures(route): return [u for u in route['units'] if u['kind'] == 'image']


def place(u): return (u['cell'].get('table'), u['cell'].get('r'), u['cell'].get('c'))


def spans_of(u): return {k: u['cell'][k] for k in ('r', 'c', 'rs', 'cs') if k in u['cell']}


class InTheBrowser(unittest.TestCase):
    """The selected route itself (EdgarTools, the formatting step, the screen step in Chrome)."""

    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright  # required: a missing install fails the suite
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def route(self, body):
        raw = page(body); route, facts = html_route.prepare(raw, 'f.htm', anchor.sha256(raw), self.browser)
        self.assertEqual((route['status'], 'error' in facts['screen']), ('OK', False))
        table = [u['id'] for u in route['units'] if u['kind'] == 'table']
        return raw, route, table

    def test_an_image_only_cell_gets_the_measured_row_and_column(self):  # failed before: no row or column
        _, r, t = self.route(b'<table><tr><th>2024</th><th>2025</th></tr><tr><td><img src="same.png" alt="old chart"></td><td><img src="same.png" alt="new chart"></td></tr></table>')
        self.assertEqual([(place(u), u['alt']) for u in pictures(r)], [((t[0], 1, 0), 'old chart'), ((t[0], 1, 1), 'new chart')])  # one picture file twice: two occurrences under two years
        _, r, t = self.route(b'<table><tr><th rowspan="2">Region</th><th colspan="2">Revenue</th></tr><tr><th>2024</th><th>2025</th></tr><tr><td>Europe</td><td><img src="same.png"></td><td><img src="same.png"></td></tr></table>')
        self.assertEqual([place(u) for u in pictures(r)], [(t[0], 2, 1), (t[0], 2, 2)])  # under 2024 and 2025 (left edges 62 and 98, as the headers)
        _, r, t = self.route(b'<table><tr><th>Region</th><th>Chart</th></tr><tr><td>Europe</td><td rowspan="2"><img src="same.png"></td></tr><tr><td>All segments</td></tr></table>')
        self.assertEqual([place(u) for u in pictures(r)], [(t[0], 1, 1)])  # a cell over two rows stands in its first
        self.assertEqual([spans_of(u) for u in pictures(r)], [{'r': 1, 'c': 1, 'rs': 2, 'cs': 1}])  # and says it covers two (the browser's reading of its rowspan)
        _, r, t = self.route(b'<table><tr><th>Actual</th><th>Forecast</th></tr><tr><td colspan="2"><img src="same.png"></td></tr></table>')
        self.assertEqual([spans_of(u) for u in pictures(r)], [{'r': 1, 'c': 0, 'rs': 1, 'cs': 2}])  # a cell over two columns: at its first, covering both (measured)

    def test_a_picture_beside_text_takes_the_measured_columns_as_its_text_does(self):  # failed before: the tool's columns 1 and 2
        for first in (b'<td style="display:none">Hidden</td>', b'<td style="padding:0;width:0"></td>'):
            _, r, t = self.route(b'<table style="border-collapse:collapse"><tr>' + first + b'<td>2024<img src="same.png"></td><td>2025<img src="same.png"></td></tr></table>')
            text = {c['text']: (t[0], c['r'], c['c']) for u in r['units'] if u['kind'] == 'table' for c in u['cells']}
            self.assertEqual([place(u) for u in pictures(r)], [text['2024'], text['2025']])
            self.assertEqual([place(u) for u in pictures(r)], [(t[0], 0, 0), (t[0], 0, 1)])

    def test_a_route_table_of_two_grids_states_no_row_or_column(self):
        raw, r, t = self.route(b'<table><tr><th>Outer</th></tr><tr><td><table><tr><th>Inner 2025</th></tr><tr><td><img src="same.png"></td></tr></table></td></tr></table>')
        [p] = pictures(r)
        self.assertEqual((place(p), spans_of(p)), ((t[0], None, None), {}))  # the route's one table holds cells of both grids: no row or column is one of them
        self.assertTrue(raw[p['cell']['byte_start']:p['cell']['byte_end_exclusive']].startswith(b'<td><img src="same.png">'))  # its own (inner) source cell

    def test_pictures_of_a_table_with_no_route_table_name_no_table(self):
        raw, r, t = self.route(b'<table><tr><td><img src="a.png"></td><td><img src="b.png"></td></tr></table>')
        self.assertEqual((t, [place(u) for u in pictures(r)]), ([], [(None, None, None)] * 2))  # never a parent the route does not have
        self.assertEqual([raw[u['cell']['byte_start']:u['cell']['byte_end_exclusive']][:20] for u in pictures(r)], [b'<td><img src="a.png"', b'<td><img src="b.png"'])

    def test_the_source_descriptions_as_written_for_the_tools_pictures_and_the_added_ones(self):  # failed before: no alt or title anywhere
        _, r, _ = self.route(b'<h2>Revenue</h2><img src="same.png" alt="Profit &amp;amp; loss" title=""><p>USD millions.</p>')
        [p] = pictures(r)
        self.assertEqual((p.get('from'), p['alt'], p['title'], p['text']), (None, 'Profit &amp; loss', '', ''))  # the tool's own picture; decoded once; an empty title is a title
        _, r, t = self.route(b'<table><tr><th>2025</th></tr><tr><td>Revenue <img src="same.png" ALT="Revenue &amp; costs" alt="wrong" TITLE="Source description"></td></tr></table>')
        [p] = pictures(r)
        self.assertEqual((p['from'], p['alt'], p['title'], p['text'], place(p)), ('source', 'Revenue & costs', 'Source description', '', (t[0], 1, 0)))  # the first of two
        _, r, t = self.route(b'<table><tr><th>2024</th><th>2025</th></tr><tr><td><img style="display:none" src="same.png" alt="hidden"><img src="same.png" alt="shown"></td><td>25</td></tr></table>')
        self.assertEqual([(u['alt'], place(u)) for u in pictures(r)], [('shown', (t[0], 1, 0))])  # a hidden copy has no unit and lends nothing
        _, r, _ = self.route(b'<p>Chart</p><img src="a.png"><table><tr><td>1</td><td><img src="b.png"></td></tr></table>')
        self.assertTrue(all('alt' not in u and 'title' not in u for u in pictures(r)))  # none written: none stated


    def test_a_cells_rows_end_where_its_row_group_ends(self):  # failed on the first draft: rowspan="0" gave rs 0 and "9999" gave 9999 (Codex, CANDIDATE_ROWSPAN_PROBE)
        for written, rows in ((b'0', 2), (b'9999', 2), (b'2', 2), (b'1', 1)):  # "0" runs to the end of its group, a larger one stops there (the table model, as Chrome lays it out)
            _, r, t = self.route(b'<table><thead><tr><th>Region</th><th>Chart</th></tr></thead><tbody><tr><td>A</td><td rowspan="' + written + b'"><img src="s.png"></td></tr>'
                                 b'<tr><td>B</td></tr></tbody><tbody><tr><td>C</td><td>Separate</td></tr></tbody></table>')
            self.assertEqual([spans_of(u) for u in pictures(r)], [{'r': 1, 'c': 1, 'rs': rows, 'cs': 1}])
            self.assertEqual([(c['text'], c['r'], c['c'], c['rs']) for u in r['units'] if u['kind'] == 'table' for c in u['cells'] if c['text'] in 'AB'], [('A', 1, 0, 1), ('B', 2, 0, 1)])  # text cells keep the tool's rows

    def test_only_table_cells_are_measured(self):  # failed before: a source element carrying the step's own mark was measured as that cell (Codex, MEASURE_ALIAS_BASELINE)
        body = b'<table><tr><th>2024</th><th>2025</th></tr><tr><td>Chart<img src="same.png"></td><td>Other</td></tr></table>'
        def seen(suffix):
            raw = page(body + suffix); route, facts = html_route.prepare(raw, 'f.htm', anchor.sha256(raw), self.browser)
            return [(c['text'], c['r'], c['c'], c['cs']) for u in route['units'] if u['kind'] == 'table' for c in u['cells']], [spans_of(u) for u in pictures(route)], facts['screen']['cells_measured']
        plain = seen(b'')
        self.assertEqual(plain, ([('2024', 0, 0, 1), ('2025', 0, 1, 1), ('Chart', 1, 0, 1), ('Other', 1, 1, 1)], [{'r': 1, 'c': 0, 'rs': 1, 'cs': 1}], 4))
        for suffix in (b'<div data-g="2">Other text</div>', b'<span data-g="2">Other text</span>', b'<p data-g="0">y</p>'):
            self.assertEqual(seen(suffix)[0], plain[0]); self.assertEqual(seen(suffix)[1:], plain[1:])  # a mark the source writes on another element measures nothing
        raw = page(body.replace(b'<td>Other', b'<td data-g="0">Other')); route, facts = html_route.prepare(raw, 'f.htm', anchor.sha256(raw), self.browser)  # on a cell itself: the step's own mark stands first, the browser keeps the first
        self.assertEqual(([(c['text'], c['r'], c['c'], c['cs']) for u in route['units'] if u['kind'] == 'table' for c in u['cells']], facts['screen']['cells_measured']), (plain[0], 4))


SPAN = b'<table><tr><td>2024</td><td>2025</td></tr><tr><td><img src="a.png"></td><td>9 <img src="b.png"></td></tr></table>'  # source cells g 0..3


def measured_route(stale=(1, 5)):
    """A route table over SPAN's cells as the tool gave it (columns not yet measured), with an image-only picture (g 2) and one beside "9" (g 3) holding the
    tool's row and column; and the screen step's measurement of the four cells."""
    _, spans = sg.tag_cells(SPAN)
    at = lambda g: {'byte_start': spans[g][0], 'byte_end_exclusive': spans[g][1]}
    cells = [{'r': r, 'c': c, 'rs': 1, 'cs': 1, 'text': text, 'anchor': at(g)} for g, r, c, text in ((0, 0, 3, '2024'), (1, 0, 5, '2025'), (3, 1, 5, '9'))]
    units = [{'id': 't0', 'kind': 'table', 'cells': cells},
             {'id': 'pa', 'kind': 'image', 'text': '', 'cell': dict(at(2), table='t0')},
             {'id': 'pb', 'kind': 'image', 'text': '', 'cell': dict(at(3), table='t0', r=stale[0], c=stale[1])}]
    return units, spans, {0: [{'g': g, 'row': g // 2, 'x': 100 * (g % 2), 'w': 80} for g in range(4)]}


class TheScreenStep(unittest.TestCase):
    def test_pictures_take_their_own_cells_measured_places(self):
        units, spans, measured = measured_route(); sg.apply(units, spans, measured)
        self.assertEqual([spans_of(u) for u in units[1:]], [{'r': 1, 'c': 0, 'rs': 1, 'cs': 1}, {'r': 1, 'c': 1, 'rs': 1, 'cs': 1}])

    def test_a_table_with_a_cell_not_measured_states_no_picture_row_or_column(self):
        units, spans, measured = measured_route(); units[0]['cells'][0]['anchor'] = None; sg.apply(units, spans, measured)
        self.assertEqual([(place(u), spans_of(u)) for u in units[1:]], [(('t0', None, None), {})] * 2)  # the tool's row and column beside "9" are not this table's one grid: not kept

    def test_a_table_measured_in_two_tables_states_no_picture_row_or_column(self):
        units, spans, measured = measured_route(); measured[1] = [measured[0].pop()]; sg.apply(units, spans, measured)
        self.assertEqual([place(u) for u in units[1:]], [('t0', None, None)] * 2)

    def test_a_picture_whose_own_cell_is_not_measured_states_none(self):
        units, spans, measured = measured_route(); measured[0][2]['w'] = 0; sg.apply(units, spans, measured)
        self.assertEqual([place(u) for u in units[1:]], [('t0', None, None), ('t0', 1, 1)])

    def test_a_picture_with_no_route_table_is_left_alone(self):
        units, spans, measured = measured_route(); del units[1]['cell']['table']; before = dict(units[1]['cell']); sg.apply(units, spans, measured)
        self.assertEqual(units[1]['cell'], before)

    def test_the_tables_and_the_steps_facts_are_as_before(self):
        units, spans, measured = measured_route(); n = sg.apply(units, spans, measured)
        self.assertEqual((n, [(c['r'], c['c']) for c in units[0]['cells']]), (3, [(0, 0), (0, 1), (1, 1)]))  # the count is of table cells only

SAME = b'<table><tr><td>Revenue</td><td>10 <img src="n.png" alt="Native"></td><td>12 <img src="s.png" alt="A &amp;amp; B" title=""></td></tr></table>'


class OneTreatment(unittest.TestCase):
    def test_a_tool_picture_in_a_cell_gets_what_an_added_one_gets(self):  # failed before: the tool's own picture had no cell and no description
        vis = anchor.Visible(SAME); known = adapter.codes(SAME, vis); code = {name: c for c, (s, name) in known.items()}
        table = next(c for c, (s, name) in known.items() if name is None)
        tree = {'type': 'DocumentNode', 'children': [{'type': 'TableNode', 'caption': None, 'code': table, 'rows': [[{'text': t, 'colspan': 1, 'rowspan': 1, 'is_header': False} for t in ('Revenue', '10', '12')]]},
                                                     {'type': 'ImageNode', 'src': code['n.png']}]}
        units = adapter.route_for(tree, SAME, 'f.htm', 'sha', 0, 'v', vis=vis)['units']
        native, added = [u for u in units if u.get('src') == 'n.png'], [u for u in units if u.get('src') == 's.png']
        self.assertEqual(([u.get('from') for u in native], [u.get('from') for u in added]), ([None], ['source']))
        t = next(u['id'] for u in units if u['kind'] == 'table')
        self.assertEqual([(place(u), u['alt'], u.get('title')) for u in native + added], [((t, 0, 1), 'Native', None), ((t, 0, 2), 'A &amp; B', '')])
        self.assertEqual([SAME[u['cell']['byte_start']:u['cell']['byte_end_exclusive']][:8] for u in native + added], [b'<td>10 <', b'<td>12 <'])


    def test_a_source_table_read_as_two_route_tables_names_no_table(self):  # failed before: the first route table was named (Codex)
        raw = b'<table><tr><td>Revenue</td><td><img src="a.png"></td></tr><tr><td>Costs</td><td>5 <img src="b.png"></td></tr></table>'
        vis = anchor.Visible(raw); known = adapter.codes(raw, vis); table = next(c for c, (s, name) in known.items() if name is None)
        row = lambda *texts: [{'text': t, 'colspan': 1, 'rowspan': 1, 'is_header': False} for t in texts]
        tree = {'type': 'DocumentNode', 'children': [{'type': 'TableNode', 'caption': None, 'code': table, 'rows': [row('Revenue', '')]}, {'type': 'TableNode', 'caption': None, 'code': table, 'rows': [row('Costs', '5')]}]}
        units = adapter.route_for(tree, raw, 'f.htm', 'sha', 0, 'v', vis=vis)['units']
        self.assertEqual([u['kind'] for u in units].count('table'), 2)  # both are the one source table's (its cells stand in each)
        self.assertEqual([(u['src'], place(u)) for u in pictures({'units': units})], [('a.png', (None, None, None)), ('b.png', (None, None, None))])  # no one table: none named, no row or column

if __name__ == '__main__':
    unittest.main()
