"""One native source table emitted as several route parts is one source table (RouteFile.source_cell, the source's own cell bytes). Its unit line and
its qualifier/basis label are read against the value by the native rows through the shared in_order/order_holds rule: in byte frames UNRESOLVED
source_order, exactly as the unsplit table - never an external-unit FAIL judged against a part's envelope, never a PASS certified by a part's byte
envelope, its row indexes restarted or shifted. Wrong column, occurrence and content keep their exact failures. Invented sources; every truth comes
from the markup (the unit cell and the 'Segment A' label stand above the value 9 in the first table; the second table repeats both)."""
import copy
import unittest

from benchmarks.prepare.grader import grade
from benchmarks.prepare.grader.tests import test_table_order_conservative as drawn  # a module import: its TestCase is not collected twice
from benchmarks.prepare.grader.tests.test_unit_order import at, table

U, Q = '(in millions)', 'Segment A'
RAW = (b'<html><body><table><tr><td>Item</td><td>(in millions)</td></tr><tr><td>Segment A</td><td></td></tr><tr><td>Revenue</td><td>9</td></tr><tr><td>Cost</td><td>4</td></tr></table>'
       b'<p>Note</p><table><tr><td>Other</td><td>(in millions)</td></tr><tr><td>Segment A</td><td></td></tr><tr><td>Fees</td><td>7</td></tr></table></body></html>')
ROWS, OTHER = [['Item', U], [Q, ''], ['Revenue', '9'], ['Cost', '4']], [['Other', U], [Q, ''], ['Fees', '7']]
ORDER = ('unresolved', 'source_order')


def key(text, own):  # the key's own place of `text`: its occurrence `own` (0 = the first table's), among every printed one
    occ = [at(RAW, text, i) for i in range(RAW.count(text.encode()))]
    return {'pieces': [{'text': text, 'byte_ranges': [[a['byte_start'], a['byte_end_exclusive']] for a in occ], 'governing': [[occ[own]['byte_start'], occ[own]['byte_end_exclusive']]]}]}


def rows(route, own=0, value='9', unit_text=U):
    """The unit_printed and segment_or_basis rows (verdict, reason) for the value cell `value` (test_unit_order.unit's target, for both fields)."""
    tb = next(u for u in route if u['kind'] == 'table' and any(c['text'] == value for c in u['cells'])); v = [c for c in tb['cells'] if c['text'] == value][-1]
    t = {'key_id': 'syn/P', 'file_id': 'syn/p.htm', 'format': 'cell/htm', 'type': 'cell', 'split': 'development', 'anchor': v['anchor'], 'table_anchor': tb['anchor'], 'alternatives': {}, 'excluded': set(),
         'support': {'unit_printed': key(U, own), 'segment_or_basis': key(Q, own)}, 'fields': {'printed_value': value, 'display_value': value, 'unit_printed': unit_text, 'segment_or_basis': Q}}
    g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/p.htm', 'units': copy.deepcopy(route)}, RAW)); g.grade_cell()
    return {r['check']: (r['verdict'], r.get('reason')) for r in g.rows if r['check'] in ('unit_printed', 'segment_or_basis')}


def route(kind=None, cut=1, rows_from=None):
    """The first table whole, or split before source row `cut` into a head and a body part with full / tight / opening envelopes; the body's own row
    indexes kept, restarted at 0, or shifted by 5 (`rows_from`: None, 'restart', 'shift'); the second table always after."""
    whole, other = table(RAW, 't0', 0, ROWS), table(RAW, 't1', 1, OTHER)
    if kind is None: return [whole, other]
    head, body = copy.deepcopy(whole), copy.deepcopy(whole)
    head.update(id='head', cells=[c for c in whole['cells'] if c['r'] < cut]); body.update(id='body', cells=[copy.deepcopy(c) for c in whole['cells'] if c['r'] >= cut])
    for c in body['cells']: c['r'] += {'restart': -cut, 'shift': 5}.get(rows_from, 0)
    for p in (head, body):
        if kind == 'tight': p['anchor'] = {'byte_start': min(c['anchor']['byte_start'] for c in p['cells']), 'byte_end_exclusive': max(c['anchor']['byte_end_exclusive'] for c in p['cells'])}
        if kind == 'opening': p['anchor'] = {'byte_start': p['anchor']['byte_start'], 'byte_end_exclusive': RAW.index(b'>', p['anchor']['byte_start']) + 1}
    return [head, body, other]


class NativeTableParts(unittest.TestCase):
    def test_one_source_table_in_route_parts_reads_as_the_unsplit_table(self):
        self.assertEqual(rows(route()), {'unit_printed': ORDER, 'segment_or_basis': ORDER})  # byte frames: the cross-row order is unproved
        for kind in ('full', 'tight', 'opening'):
            for cut in (1, 2):  # the qualifier row in the body part, or in the head part with the unit line
                for rows_from in (None, 'restart', 'shift'):
                    with self.subTest(kind=kind, cut=cut, rows_from=rows_from):
                        self.assertEqual(rows(route(kind, cut, rows_from)), {'unit_printed': ORDER, 'segment_or_basis': ORDER})

    def test_wrong_relations_keep_their_exact_failures(self):
        for kind in (None, 'full', 'tight'):
            with self.subTest(case='wrong column', kind=kind):
                r = route(kind, 2)
                for c in r[0]['cells']:
                    if c['text'] == U: c['c'] = 0  # the unit line's cell moved to the label column: a wrong relation, not an uncertain one
                self.assertEqual(rows(r)['unit_printed'], ('fail', 'column'))
            with self.subTest(case='wrong occurrence', kind=kind):
                r = route(kind, 2)
                for c in r[0]['cells']:
                    if c['text'] == U: c['anchor'] = at(RAW, U, 1)  # the route's unit cell holds the second table's printed line: wrong ownership
                self.assertEqual(rows(r)['unit_printed'][0], 'fail')  # a failure, never uncertainty; its exact reason (here 'missing', as before this repair) is not independently proved
            with self.subTest(case='wrong content', kind=kind):
                self.assertEqual(rows(route(kind, 2), unit_text='(in thousands)')['unit_printed'], ('fail', 'text'))

    def test_parent_and_strike_failures_come_before_uncertainty(self):
        for kind in ('full', 'tight'):
            with self.subTest(case='wrong parent', kind=kind):
                r = route(kind, 2); r[0]['anchor'] = copy.deepcopy(r[2]['anchor'])  # the head part claims the second native table: its cells' bytes are the first's
                self.assertEqual(rows(r)['unit_printed'], ('fail', 'source_table'))
            with self.subTest(case='invented strike', kind=kind):
                r = route(kind, 2)
                for c in r[0]['cells']:
                    if c['text'] == U: c['struck'] = [U]  # the route strikes the unit line; the source prints it plain
                self.assertEqual(rows(r)['unit_printed'], ('fail', 'struck'))


def parts(route, cut, start=None):
    """test_table_order_conservative's one table as two route parts, split before route row `cut`; the body's rows kept (None) or renumbered from `start`."""
    t = route['units'][0]; head, body = copy.deepcopy(t), copy.deepcopy(t)
    head.update(id='head', cells=[c for c in t['cells'] if c['r'] < cut])
    body.update(id='body', cells=[dict(c, r=c['r'] - cut + (cut if start is None else start)) for c in t['cells'] if c['r'] >= cut])
    return dict(route, units=[head, body])


class InOrderCallers(unittest.TestCase):
    """Every in_order caller on test_table_order_conservative's own sources and contract, the table emitted as two route parts: it reads as the unsplit
    table. The route's own claim across parts is their order; the same row is the same native source row; bytes prove no drawn order."""
    CALLERS, T, OPEN, DRAWN, page = ('corner_text', 'lead_in', 'section_path', 'segment_or_basis', 'unit_printed'), drawn.TableOrder(), drawn.U, drawn.DRAWN, staticmethod(drawn.page)

    def test_faithful_parts_are_unproved_like_the_unsplit_table(self):
        for name in ('ordinary', 'late_thead'):
            raw = self.page(name)
            for start in (None, 0, 3):  # body rows kept, restarted, or from the corner's own route row 3 (OCR's restarted-corner case)
                got = self.T.group(raw, parts(self.T.route(raw, self.DRAWN['group']), 5, start))
                for f in self.CALLERS:
                    with self.subTest(source=name, start=start, duty=f):
                        self.assertEqual(got[f], (self.OPEN, 'UNRESOLVED'))

    def test_the_value_part_listed_first_keeps_the_unsplit_verdicts(self):  # the route lists the header group's part after the value's: below it
        want = {'corner_text': self.OPEN, 'unit_printed': self.OPEN, 'segment_or_basis': self.OPEN, 'lead_in': ('fail', 'missing'), 'section_path': ('fail', 'missing')}
        for name in ('ordinary', 'late_thead'):
            raw = self.page(name)
            for start in (None, 0):
                got = self.T.group(raw, parts(self.T.route(raw, self.DRAWN['group'], order=[5, 0, 1, 2, 3, 4]), 1, start))
                for f in self.CALLERS:
                    with self.subTest(source=name, start=start, duty=f):
                        self.assertEqual(got[f][0], want[f])

    def test_footer_note_rows_in_another_part(self):
        for name in ('late_tfoot', 'early_tfoot'):
            raw = self.page(name)
            for start in (None, 0):
                with self.subTest(source=name, start=start, route='note part after the value part'):
                    self.assertEqual(self.T.footnote(raw, parts(self.T.route(raw, self.DRAWN['foot']), 2, start)), (self.OPEN, 'UNRESOLVED'))
                with self.subTest(source=name, start=start, route='note part listed above the value part'):
                    (verdict, _), overall = self.T.footnote(raw, parts(self.T.route(raw, self.DRAWN['foot'], order=[0, 2, 1]), 2, start))
                    self.assertNotEqual(verdict, 'pass'); self.assertNotEqual(overall, 'PASS')

    def note_linked(self, raw, route, note):  # the footnotes caller's side row itself (verdict_of leaves structure rows out)
        t = {'key_id': 'invented/note_linked', 'file_id': route['file_id'], 'split': 'public', 'type': 'cell', 'format': 'cell/html', 'alternatives': {}, 'excluded': set(), 'support': {},
             'fields': {'printed_value': '10', 'footnote_markers': [{'marker_text': '(1)', 'anchor': drawn.at(raw, 'th', 'y24'), 'note_anchor': drawn.at(raw, 'td', note), 'note_text': drawn.TEXT['note']}]},
             'anchor': drawn.at(raw, 'td', 'v1'), 'table_anchor': drawn.at(raw, 'table', 't')}
        g = grade.Grader(t, grade.RouteFile(copy.deepcopy(route), raw, 'html')); g.grade_cell()
        return next((r['verdict'], r.get('reason')) for r in g.rows if r['check'] == 'note_linked')

    def test_a_note_row_in_another_part_stays_linked_to_its_own_table(self):  # the same native table membership; a note in another native table is not
        for name in ('late_tfoot', 'early_tfoot'):
            raw = self.page(name); base = self.T.route(raw, self.DRAWN['foot'])
            self.assertEqual(self.note_linked(raw, base, 'note'), self.OPEN)  # the unsplit table's own note row: linked, its order unproved
            for start in (None, 0):
                with self.subTest(source=name, start=start):
                    self.assertEqual(self.note_linked(raw, parts(base, 2, start), 'note'), self.OPEN)
            two = raw.replace(b'</body>', b'<table id="t2"><tr><td id="other">(1) Excludes discontinued operations</td></tr></table></body>')
            other = {'id': 't2', 'kind': 'table', 'anchor': drawn.at(two, 'table', 't2'), 'cells': [{'r': 0, 'c': 0, 'rs': 1, 'cs': 1, 'text': drawn.TEXT['note'], 'anchor': drawn.at(two, 'td', 'other')}]}
            for start in ('unsplit', None, 0):  # the key's note printed in a second native table, no explicit link: not linked, split or not
                with self.subTest(source=name, wrong_link=start):
                    r = self.T.route(two, self.DRAWN['foot']); r = r if start == 'unsplit' else parts(r, 2, start); r['units'] = r['units'] + [other]
                    self.assertEqual(self.note_linked(two, r, 'other'), ('fail', None))


if __name__ == '__main__':
    unittest.main()
