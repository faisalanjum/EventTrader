"""A table's own caption is a `caption` unit (Root's caption design v2, option 1): the native caption text (EdgarTools `TableProcessor._own_section`), bound
to the source <caption> element the tool read by the adapter's own code (as tables and cells are), anchored at that element's text, standing at its source
place, naming its table by the table's own `source_table`; the table keeps no copy of it (`caption` []). Formatting, coverage and the grader then read it as any
text unit. A caption the tool did not read, or whose element identity is not proved, is never assigned to a table: it stays uncovered. Expected values come
from each fixture's own markup and bytes."""
import copy
import hashlib
import unittest

from driver.prepare.convert import html_route
from benchmarks.prepare.grader import grade

H = lambda body: ('<!doctype html><html><head><meta charset="utf-8"></head><body><p>Intro text.</p>' + body + '<p>Closing text.</p></body></html>').encode()
ROWS = '<tr><th>Item</th><th>Quantity</th></tr><tr><td>Washer</td><td>6</td></tr>'
CASES = {
    'plain': H('<table><caption>Service parts</caption>' + ROWS + '</table>'),
    'struck': H('<table><caption><s>Service parts</s></caption>' + ROWS + '</table>'),
    'after_rows': H('<table>' + ROWS + '<caption>Service parts</caption></table>'),
    'repeated': H('<table><caption>Parts list</caption><tr><td>Bolt</td><td>4</td></tr></table><p>Between.</p><table><caption>Parts list</caption><tr><td>Nut</td><td>6</td></tr></table>'),
    'empty_cells': H('<table><caption>Reserved capacity</caption><tr><td></td><td></td></tr></table>'),
    'hidden': H('<table><caption hidden>Draft caption</caption><tr><td>Lamp</td><td>1</td></tr></table>'),
    'nested': H('<table><tr><td>Outer cell<table><caption>Inner schedule</caption><tr><td>Week</td><td>9</td></tr></table></td><td>Side</td></tr></table>'),
    'two_captions': H('<table><caption>One</caption><caption>Two</caption><tr><td>Bolt</td><td>4</td></tr></table>'),
    'fostered_lookalike': H('<table>Parts list<tr><td>Bolt</td><td>4</td></tr></table><p>Between.</p><table><caption>Parts list</caption><tr><td>Nut</td><td>6</td></tr></table>'),
    'caption_outside_a_table': H('<caption>Loose words</caption><table><tr><td>Bolt</td><td>4</td></tr></table>'),
    # Root's early-review fixtures (root_caption_early_review_v1), bytes as authored there
    'root_nested_no_caption': b'<!doctype html><html><body><p>Outer.</p><table><tr><td>Holder<table><tr><td>Inner value</td></tr></table></td></tr></table></body></html>',
    'root_nested_caption': b'<!doctype html><html><body><p>Outer.</p><table><tr><td>Holder<table><caption>Inner title</caption><tr><td>Inner value</td></tr></table></td></tr></table></body></html>',
    'root_title': b'<!doctype html><html><body><h2>Service parts</h2><table><caption>Service parts</caption><tr><th>Item</th><th>Quantity</th></tr><tr><td>Washer</td><td>6</td></tr></table></body></html>',
}
at = lambda raw, text, n=0: [i for i in range(len(raw)) if raw.startswith(text.encode(), i)][n]
caps = lambda route: [u for u in route['units'] if u['kind'] == 'caption']
tabs = lambda route: [u for u in route['units'] if u['kind'] == 'table']


def key(raw, title, n=0):  # the title reviewed at the n-th printing of "Service parts" (the caption, or a heading before the table)
    span = lambda x: {'byte_start': raw.index(x), 'byte_end_exclusive': raw.index(x) + len(x)}
    cap = {'byte_start': at(raw, 'Service parts', n), 'byte_end_exclusive': at(raw, 'Service parts', n) + len('Service parts')}
    return {'alternatives': {}, 'anchor': span(b'<td>6</td>'), 'excluded': [], 'file_id': 'caption.htm', 'format': 'cell/html', 'key_id': 'pub/CAPTION', 'split': 'public', 'type': 'cell',
            'fields': {'display_value': '6', 'footnote_markers': [], 'header_path': ['Quantity'], 'periods': [], 'printed_value': '6', 'row_context': [], 'row_label': 'Washer',
                       'section_path': [], 'table_title': [title], 'value_kind': 'number'},
            'support': {'row_label': {'anchors': [span(b'<td>Washer</td>')], 'how': 'reviewed'}, 'table_title': {'anchors': [cap], 'how': 'reviewed'},
                        'header_path': {'anchors': [span(b'<th>Quantity</th>')], 'how': 'reviewed'}},
            'table_anchor': {'byte_start': raw.index(b'<table'), 'byte_end_exclusive': raw.index(b'</table>') + 8}}


def title(route, raw, value, n=0):
    g = grade.Grader(key(raw, value, n), grade.RouteFile(route, raw, 'html')); g.grade_cell()
    row = next(r for r in g.rows if r['check'] == 'table_title'); return row['verdict'], row['reason']


def gates(route, raw):
    g = grade.gates_for_file(grade.RouteFile(route, raw, 'html'), route['status']); return [x['text'] for x in g['uncovered'] or []], g['dishonest']


class CaptionUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.routes = {}
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                for name, raw in CASES.items(): cls.routes[name] = html_route.prepare(raw, 'caption.htm', hashlib.sha256(raw).hexdigest(), browser)[0]
            finally: browser.close()

    def test_an_own_caption_is_one_caption_unit_at_its_own_text_naming_its_table(self):
        for name in ('plain', 'struck', 'after_rows'):
            with self.subTest(name):
                raw, route = CASES[name], self.routes[name]; (c,), (t,) = caps(route), tabs(route); i = at(raw, 'Service parts')
                self.assertEqual((route['status'], c['text'], c['anchor'], c['source_table'], t['caption']),
                                 ('OK', 'Service parts', {'byte_start': i, 'byte_end_exclusive': i + 13}, t['source_table'], []))
                self.assertEqual(gates(route, raw), ([], 0))  # nothing lost, nothing claimed falsely

    def test_the_caption_stands_at_its_source_place(self):
        order = lambda name: [u['kind'] for u in self.routes[name]['units'] if u['kind'] in ('caption', 'table')]
        self.assertEqual((order('plain'), order('after_rows')), (['caption', 'table'], ['table', 'caption']))

    def test_a_struck_caption_is_struck_through_the_existing_text_path(self):
        self.assertEqual([(c.get('struck'), c.get('struck_at')) for c in caps(self.routes['struck'])], [(['Service parts'], [[0, 7], [8, 13]])])
        self.assertEqual([c.get('struck') for c in caps(self.routes['plain'])], [None])

    def test_repeated_equal_captions_each_name_their_own_table(self):
        raw, route = CASES['repeated'], self.routes['repeated']
        self.assertEqual([(c['anchor']['byte_start'], c['source_table']['tag_start']) for c in caps(route)],
                         [(at(raw, 'Parts list', 0), at(raw, '<table', 0)), (at(raw, 'Parts list', 1), at(raw, '<table', 1))])
        self.assertEqual([t['caption'] for t in tabs(route)], [[], []])

    def test_a_table_of_empty_cells_and_a_nested_table_keep_their_own_caption(self):
        raw = CASES['empty_cells']; (c,) = caps(self.routes['empty_cells'])
        self.assertEqual((c['text'], c['anchor']['byte_start'], c['source_table']['tag_start']), ('Reserved capacity', at(raw, 'Reserved capacity'), at(raw, '<table')))
        raw, route = CASES['nested'], self.routes['nested']; (c,) = caps(route); outer, inner = tabs(route)
        self.assertEqual((c['text'], c['source_table'], inner['caption'], outer['caption']), ('Inner schedule', inner['source_table'], [], []))
        self.assertIn('Inner schedule', outer['cells'][0]['text'])  # the accepted flattening of the holder cell stays

    def test_a_hidden_caption_is_no_unit_and_a_caption_the_tool_did_not_read_stays_uncovered(self):
        self.assertEqual((caps(self.routes['hidden']), gates(self.routes['hidden'], CASES['hidden'])), ([], ([], 0)))
        route = self.routes['two_captions']
        self.assertEqual(([c['text'] for c in caps(route)], gates(route, CASES['two_captions'])), (['One'], (['Two'], 0)))  # the tool reads the first own caption only

    def test_text_that_only_reads_like_a_caption_is_never_one(self):
        raw, route = CASES['fostered_lookalike'], self.routes['fostered_lookalike']  # the first table's stray text is no caption; only the second table has one
        self.assertEqual([(c['text'], c['source_table']['tag_start'], c['anchor']['byte_start']) for c in caps(route)], [('Parts list', at(raw, '<table', 1), at(raw, 'Parts list', 1))])
        route = self.routes['caption_outside_a_table']  # a caption tag outside any table is no table's caption (the parser drops the tag)
        self.assertEqual([(c.get('source_table'), c.get('source')) for c in caps(route)], [])
        self.assertEqual([t['caption'] for t in tabs(route)], [[]])

    def test_a_parse_saved_without_caption_codes_is_neither_reused_nor_read_as_bound(self):  # the tool's input gains a code on each caption: the setting names it
        from driver.prepare.convert import anchor, edgartools_html as eh
        self.assertEqual(eh.SETTINGS['table_captions'], "each table's own caption a caption unit, bound to its source caption")
        raw = CASES['plain']; vis = anchor.Visible(raw); known = eh.codes(raw, vis)
        old = {'type': 'DocumentNode', 'children': [{'type': 'TableNode', 'caption': 'Service parts', 'code': next(k for k, v in known.items() if v[1] is None),
                                                     'rows': [[{'text': 'Washer', 'colspan': 1, 'rowspan': 1, 'is_header': False}]]}]}  # an older dump: no `caption_code`
        units = eh.to_units(old, known)
        self.assertEqual(([u['kind'] for u in units], units[0]['caption']), (['table'], ['Service parts']))  # kept as before, unbound: never a caption unit by its text

    def test_a_holder_cell_names_its_actual_child_table_with_or_without_a_caption(self):  # Root's early review, defect 1
        for name in ('root_nested_no_caption', 'root_nested_caption', 'nested'):
            with self.subTest(name):
                route = self.routes[name]; ids = {u['id']: u for u in route['units']}
                refs = [(t['id'], k) for t in tabs(route) for c in t['cells'] for k in c.get('tables', [])]
                self.assertTrue(refs)
                for parent, child in refs: self.assertEqual((ids.get(child, {}).get('kind'), ids[child]['cell']['table']), ('table', parent))

    def test_a_title_reviewed_at_a_heading_needs_that_heading_not_an_equal_caption(self):  # Root's early review, defect 2: the field's own occurrence
        raw, route = CASES['root_title'], self.routes['root_title']
        self.assertEqual(title(route, raw, 'Service parts', 0)[0], 'pass')  # reviewed at the <h2>: the heading is there
        gone = copy.deepcopy(route); gone['units'] = [u for u in gone['units'] if not (u['kind'] == 'heading' and u.get('text') == 'Service parts')]
        self.assertNotEqual(title(gone, raw, 'Service parts', 0)[0], 'pass')  # the heading removed; the equal own caption elsewhere does not stand for it
        self.assertEqual(title(gone, raw, 'Service parts', 1)[0], 'pass')  # reviewed at the caption itself: the caption is the title

    def test_a_caption_carrier_that_names_another_table_carries_no_field(self):  # Root, caption field ownership: the shared placement check, every field
        raw, route = CASES['plain'], self.routes['plain']
        wrong = copy.deepcopy(route); caps(wrong)[0]['source_table'] = {'tag_start': 0, 'claims': 1}  # names a byte that starts no table (the v2 CLI wrong-owner edit)
        self.assertEqual((title(route, raw, 'Service parts'), title(wrong, raw, 'Service parts')), (('pass', None), ('fail', 'source_table')))
        def path(r):  # the same caption carrying another field: a section heading reviewed at the caption's own text
            k = key(raw, 'Service parts'); k['fields'].update(table_title=[], section_path=['Service parts']); k['support']['section_path'] = k['support'].pop('table_title')
            g = grade.Grader(k, grade.RouteFile(r, raw, 'html')); g.grade_cell(); row = next(x for x in g.rows if x['check'] == 'section_path'); return row['verdict'], row['reason']
        self.assertEqual((path(route), path(wrong)), (('pass', None), ('fail', 'source_table')))

    def test_the_grader_reads_the_title_from_the_tables_own_caption_unit(self):
        for name, value, want in (('plain', 'Service parts', 'pass'), ('after_rows', 'Service parts', 'pass'), ('struck', '~~Service parts~~', 'pass'), ('plain', '~~Service parts~~', 'fail')):
            with self.subTest(name + ' ' + value): self.assertEqual(title(self.routes[name], CASES[name], value)[0], want)

    def test_a_lost_strike_removed_caption_wrong_owner_or_wrong_source_never_passes(self):
        raw, base = CASES['struck'], self.routes['struck']
        lost = copy.deepcopy(base); [c.pop('struck', None) or c.pop('struck_at', None) for c in caps(lost)]
        for c in caps(lost): c.pop('struck_at', None)
        self.assertEqual(title(lost, raw, '~~Service parts~~'), ('fail', 'struck'))
        raw, plain = CASES['plain'], self.routes['plain']
        bare = copy.deepcopy(plain); bare['units'] = [u for u in bare['units'] if u['kind'] != 'caption']; tabs(bare)[0]['caption'] = ['Service parts']  # a caption string with no place
        self.assertNotEqual(title(bare, raw, 'Service parts')[0], 'pass'); self.assertEqual(gates(bare, raw), (['Service parts'], 0))
        twin = self.routes['repeated']; wrong = copy.deepcopy(twin); a, b = caps(wrong); b['source_table'] = dict(a['source_table'])  # names the other table
        self.assertEqual(gates(wrong, CASES['repeated'])[1], 1)
        moved = copy.deepcopy(plain); c = caps(moved)[0]; cell = next(x for x in tabs(moved)[0]['cells'] if x['text'] == 'Washer'); c['anchor'] = dict(cell['anchor'])
        self.assertNotEqual(title(moved, raw, 'Service parts')[0], 'pass'); self.assertEqual(gates(moved, raw)[1], 1)


if __name__ == '__main__':
    unittest.main()
