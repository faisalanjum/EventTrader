"""The control sample's classes (2026-10-06): a table with no text is no unit; a table continued over a page break keeps its title; a corner of several stub
columns is the key's pieces; a row-label piece carried down a block (a stub printed once for several rows, no rowspan) still labels the row."""
import unittest

from benchmarks.prepare.grader import grade
from driver.prepare.convert import anchor
from benchmarks.prepare.grader.adapters import edgartools_html as adapter
from benchmarks.prepare.grader.tests.test_edgar_images import node

RAW = (b'<p id="t">Results of operations</p><p id="l">The following table sets forth our results:</p>'
       b'<table id="a"><tr><td>Name</td><td>Type</td><td>2024</td></tr><tr><td>Donald</td><td>Salary</td><td>600</td></tr></table>'
       b'<p>25 Table of Contents</p>'
       b'<table id="b"><tr><td>Name</td><td>Type</td><td>2024</td></tr><tr><td>Kanwardev</td><td>Salary</td><td>700</td></tr><tr><td></td><td>Bonus</td><td>80</td></tr><tr><td></td><td id="v">Total</td><td id="w">780</td></tr></table>')


def span(id_):
    i = RAW.index(b'id="' + id_.encode() + b'"'); a = RAW.rfind(b'<', 0, i); return {'byte_start': a, 'byte_end_exclusive': RAW.index(b'>', i) + 1}


def text(id_):
    s = span(id_); return {'byte_start': s['byte_end_exclusive'], 'byte_end_exclusive': RAW.index(b'<', s['byte_end_exclusive'])}


def table(id_, first_row, data, order):
    """A route table unit over the HTML table id_: cells (r, c, cs, text); anchors by text search inside the element."""
    a = span(id_); end = RAW.index(b'</table>', a['byte_start']); cells = []
    for r, row in enumerate([first_row] + data):
        for c, cs, t in row:
            if not t: continue
            at = RAW.index(t.encode(), a['byte_start'] if (r, c) != (0, 0) else a['byte_start']); cells.append({'r': r, 'c': c, 'rs': 1, 'cs': cs, 'text': t, 'anchor': {'byte_start': at, 'byte_end_exclusive': at + len(t)}})
    return {'id': 't%d' % order, 'kind': 'table', 'cells': cells, 'anchor': {'byte_start': a['byte_start'], 'byte_end_exclusive': end + 8}}


class Fixture(unittest.TestCase):
    def units(self, between=None):
        a = table('a', [(0, 1, 'Name'), (1, 1, 'Type'), (2, 1, '2024')], [[(0, 1, 'Donald'), (1, 1, 'Salary'), (2, 1, '600')]], 2)
        b = table('b', [(0, 1, 'Name'), (1, 1, 'Type'), (2, 1, '2024')], [[(0, 1, 'Kanwardev'), (1, 1, 'Salary'), (2, 1, '700')], [(0, 1, ''), (1, 1, 'Bonus'), (2, 1, '80')], [(0, 1, ''), (1, 1, 'Total'), (2, 1, '780')]], 3)
        # table b's cells after the header are found from the second table on (their texts repeat): fix their anchors
        for c in b['cells']:
            if c['r'] > 0 or True:
                at = RAW.index(c['text'].encode(), span('b')['byte_start']); c['anchor'] = {'byte_start': at, 'byte_end_exclusive': at + len(c['text'])}
        return [{'id': 'u0', 'kind': 'text', 'text': 'Results of operations', 'anchor': text('t')}, {'id': 'u1', 'kind': 'text', 'text': 'The following table sets forth our results:', 'anchor': text('l')}, a if between is None else between(a), {'id': 'u4', 'kind': 'text', 'text': '25 Table of Contents', 'anchor': {'byte_start': RAW.index(b'25 Table'), 'byte_end_exclusive': RAW.index(b'25 Table') + 20}}, b]

    def grade(self, fields, units=None, support=None):
        v = text('w'); t = {'key_id': 'syn/T1', 'file_id': 'syn/f.htm', 'format': 'cell/htm', 'type': 'cell', 'split': 'development', 'anchor': v, 'table_anchor': span('b') | {'byte_end_exclusive': len(RAW)},
                           'alternatives': {}, 'excluded': set(), 'support': support or {}, 'fields': {'printed_value': '780', 'display_value': '780', 'value_kind': 'number', 'sign': 'positive', 'header_path': ['2024'], 'footnote_markers': [], 'periods': None, **fields}}
        g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/f.htm', 'units': units if units is not None else self.units()}, RAW)); g.grade_cell()
        return {r['check']: (r['verdict'], r.get('reason')) for r in g.rows}

    def test_a_table_continued_over_a_page_break_keeps_its_title_and_an_unrelated_table_displaces_it(self):
        self.assertEqual(self.grade({'table_title': ['Results of operations'], 'row_label': 'Total'})['table_title'], ('pass', None))
        other = lambda a: dict(a, cells=[dict(c, text={'Name': 'Location', 'Type': 'Size'}.get(c['text'], c['text'])) for c in a['cells']])  # another table's header row between
        self.assertEqual(self.grade({'table_title': ['Results of operations'], 'row_label': 'Total'}, self.units(other))['table_title'], ('fail', 'placement'))
        empty = lambda a: dict(a, cells=[], anchor=None)  # a table unit with nothing in it (no adapter makes one now; a route may still carry one)
        self.assertEqual(self.grade({'table_title': ['Results of operations'], 'row_label': 'Total'}, self.units(empty))['table_title'], ('pass', None))

    def test_a_title_displaced_before_an_unrelated_table_with_the_same_header_fails(self):  # Codex R2-C3: equal header rows alone do not make a continuation; the source order must agree
        raw = b'<p>Total assets</p><table id="a"><tr><td>Name</td><td>2024</td></tr><tr><td>Cash</td><td>100</td></tr></table><p>Current debt</p><table id="b"><tr><td>Name</td><td>2024</td></tr><tr><td>Loans</td><td>20</td></tr></table>'
        def at(s, start=0):
            n = raw.index(s.encode(), start); return {'byte_start': n, 'byte_end_exclusive': n + len(s)}
        units = []
        for title, tid, label, value in (('Total assets', 'a', 'Cash', '100'), ('Current debt', 'b', 'Loans', '20')):
            units.append({'id': title, 'kind': 'text', 'text': title, 'anchor': at(title)}); start = raw.index(('id="%s"' % tid).encode())
            cells = [{'r': r, 'c': c, 'rs': 1, 'cs': 1, 'text': s, 'anchor': at(s, start), 'header': r == 0} for r, row in enumerate([['Name', '2024'], [label, value]]) for c, s in enumerate(row)]
            units.append({'id': tid, 'kind': 'table', 'cells': cells, 'anchor': {'byte_start': raw.rfind(b'<table', 0, start), 'byte_end_exclusive': raw.index(b'</table>', start) + 8}})
        t = {'key_id': 'syn/T2', 'file_id': 'syn/g.htm', 'format': 'cell/htm', 'type': 'cell', 'split': 'development', 'anchor': units[-1]['cells'][-1]['anchor'], 'table_anchor': units[-1]['anchor'], 'alternatives': {}, 'excluded': set(),
             'support': {'table_title': {'anchors': [at('Current debt')]}}, 'fields': {'printed_value': '20', 'display_value': '20', 'value_kind': 'number', 'sign': 'positive', 'header_path': ['2024'], 'row_label': 'Loans', 'table_title': ['Current debt'], 'footnote_markers': [], 'periods': None}}
        def title(order):
            g = grade.Grader(t, grade.RouteFile({'file_id': t['file_id'], 'units': [dict(u) for u in order]}, raw)); g.grade_cell(); return next((r['verdict'], r.get('reason')) for r in g.rows if r['check'] == 'table_title')
        self.assertTrue(grade.continued(units[1], units[3]))  # the two tables share a header row: the excuse alone would call them one table
        self.assertEqual(title(units), ('pass', None)); self.assertEqual(title([units[0], units[2], units[1], units[3]]), ('fail', 'placement'))  # the title listed before the other table, its source place after it
        raw2 = raw + b'<table id="c"><tr><td>Name</td><td>2024</td></tr><tr><td>Bonds</td><td>30</td></tr></table>'; start = raw2.index(b'id="c"')
        c = {'id': 'c', 'kind': 'table', 'anchor': {'byte_start': raw2.rfind(b'<table', 0, start), 'byte_end_exclusive': raw2.index(b'</table>', start) + 8},
             'cells': [{'r': r, 'c': k, 'rs': 1, 'cs': 1, 'text': s, 'anchor': {'byte_start': raw2.index(s.encode(), start), 'byte_end_exclusive': raw2.index(s.encode(), start) + len(s)}, 'header': r == 0} for r, row in enumerate([['Name', '2024'], ['Bonds', '30']]) for k, s in enumerate(row)]}
        g = grade.Grader(t, grade.RouteFile({'file_id': t['file_id'], 'units': [dict(u) for u in (units[0], units[1], units[2], c, units[3])]}, raw2)); g.grade_cell()
        self.assertEqual(next((r['verdict'], r.get('reason')) for r in g.rows if r['check'] == 'table_title'), ('fail', 'placement'))  # a same-header table listed between the title and its table, its source place after the table: no continuation

    def test_a_corner_of_two_stub_columns_is_the_keys_pieces(self):
        self.assertEqual(self.grade({'corner_text': 'Name | Type', 'row_label': 'Total'})['corner_text'], ('pass', None))
        self.assertEqual(self.grade({'corner_text': 'Name | Kind', 'row_label': 'Total'})['corner_text'][0], 'fail')

    def test_a_row_label_piece_carried_down_a_block_labels_the_row(self):
        self.assertEqual(self.grade({'row_label': 'Kanwardev | Total'})['row_label'], ('pass', None))  # the name two rows up, nothing in its column between
        blocked = self.units(); blocked[-1]['cells'].append({'r': 2, 'c': 0, 'rs': 1, 'cs': 1, 'text': 'Other', 'anchor': {'byte_start': RAW.index(b'Bonus'), 'byte_end_exclusive': RAW.index(b'Bonus') + 5}})
        self.assertEqual(self.grade({'row_label': 'Kanwardev | Total'}, blocked)['row_label'][0], 'fail')  # another name between: the block ended, the name is not this row's
        self.assertEqual(self.grade({'row_label': 'Donald | Total'})['row_label'][0], 'fail')  # a name in another table
        at = lambda t: {'byte_start': RAW.index(t, span('b')['byte_start']), 'byte_end_exclusive': RAW.index(t, span('b')['byte_start']) + len(t)}
        anchored = {'row_label': {'anchors': [at(b'Kanwardev'), at(b'Total')]}}
        self.assertEqual(self.grade({'row_label': 'Kanwardev | Total'}, support=anchored)['row_label'], ('pass', None))  # by the key's anchors: the same, carried
        self.assertEqual(self.grade({'row_label': 'Kanwardev | Total'}, blocked, support=anchored)['row_label'], ('fail', 'row'))  # by the anchors, blocked: the name is found but not this row's


class Helpers(unittest.TestCase):
    def test_continued_and_carried(self):
        a = {'cells': [{'r': 0, 'c': 0, 'text': 'Name'}, {'r': 0, 'c': 1, 'text': 'x'}, {'r': 1, 'c': 0, 'text': 'A'}]}; b = {'cells': [{'r': 0, 'c': 0, 'text': 'Name'}, {'r': 0, 'c': 1, 'text': 'x'}, {'r': 1, 'c': 0, 'text': 'B'}]}
        self.assertTrue(grade.continued(a, b)); self.assertFalse(grade.continued(a, {'cells': [{'r': 0, 'c': 0, 'text': 'Name'}]})); self.assertFalse(grade.continued({'cells': []}, b)); self.assertFalse(grade.continued(a, {'cells': []}))
        stub = {'r': 1, 'c': 0, 'cs': 1, 'text': 'A'}; t = {'cells': [stub, {'r': 2, 'c': 1, 'text': 'x'}, {'r': 3, 'c': 1, 'text': 'y'}]}
        self.assertTrue(grade.carried(stub, 3, t)); self.assertFalse(grade.carried(stub, 1, t)); self.assertFalse(grade.carried(stub, 3, {'cells': t['cells'] + [{'r': 2, 'c': 0, 'text': 'B'}]}))
        self.assertFalse(grade.carried(stub, 3, {'cells': t['cells'] + [{'r': 3, 'c': 0, 'text': 'B'}]}))  # a stub in the row itself ends the block
        self.assertTrue(grade.carried(stub, 3, {})); self.assertFalse(grade.continued({'cells': []}, {'cells': []})); self.assertFalse(grade.continued({}, b))  # no cells: nothing continues, nothing blocks

    def test_a_table_with_no_text_is_no_unit(self):
        tree = {'type': 'DocumentNode', 'children': [{'type': 'TableNode', 'caption': None, 'rows': [[{'text': ' ', 'colspan': 1, 'rowspan': 1, 'is_header': False}]]}, {'type': 'ParagraphNode', 'text': 'after'}]}
        self.assertEqual([u['kind'] for u in adapter.to_units(tree)], ['text'])
        tree['children'][0]['rows'][0][0]['text'] = 'x'; self.assertEqual([u['kind'] for u in adapter.to_units(tree)], ['table', 'text'])
        tree['children'][0]['rows'][0][0]['text'] = ' '; tree['children'][0]['caption'] = 'Outstanding debt at December 31'  # no text in any cell, a caption: the caption is read, and anchored (Codex R2-C4)
        units = adapter.to_units(tree); self.assertEqual([(u['kind'], u['text']) for u in units][0], ('caption', 'Outstanding debt at December 31'))
        raw = b'<table><caption>Outstanding debt at December 31</caption><tr><td></td></tr></table><p>after</p>'
        self.assertEqual(raw[anchor.link(raw, units)['units'][0]['anchor']['byte_start']:][:31], b'Outstanding debt at December 31')


if __name__ == '__main__':
    unittest.main()
