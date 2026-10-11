"""A text value's own footnote marks printed into its text (public invented controls, OCR text-marker design v2, Root ROOT_MARKER_CANCELLATION_GATE):
a value that prints no number takes the label equivalence (`without_marks`) over its full displayed reading, then its strikes on the same carriers; a value
that prints a number keeps the E11 rule (a mark glued to it never passes); the footnote check judges the mark's own carriers, the note and the link, and
the strikes over every carrier at the mark's anchor. Truths are the markup below and the public key contract (E11, E12); routes are hand-made, marks
reported apart in `markers` as the converter's fixtures do."""
import copy
import unittest

from benchmarks.prepare.grader import grade

RAW = (b'<table><tr><td></td><td>2024</td><td>2023</td></tr>'
       b'<tr><td>Title</td><td>Director<sup>(3)</sup></td><td>Director</td></tr>'
       b'<tr><td>Chair</td><td>Chair<sup>(3)</sup><sup>(4)</sup></td><td>Member</td></tr>'
       b'<tr><td>Status</td><td><s>Retired</s><sup>(4)</sup></td><td>Active</td></tr>'
       b'<tr><td>Role</td><td>Director<sup>(3)</sup></td><td>(acting)</td></tr>'
       b'<tr><td>Fees</td><td>70<sup>2</sup></td><td>70</td></tr>'
       b'<tr><td>Series</td><td>Series 2<sup>(1)</sup></td><td>none</td></tr>'
       b'<tr><td>Bonus<sup>(5)</sup></td><td>80</td><td>90</td></tr></table>'
       b'<p><sup>(1)</sup> Class one.</p><p><sup>2</sup> Includes retainer.</p><p><sup>(3)</sup> Lead director.</p><p><sup>(4)</sup> Since May.</p><p><sup>(5)</sup> Paid in May.</p>')
NOTES = {'(1)': 'Class one.', '2': 'Includes retainer.', '(3)': 'Lead director.', '(4)': 'Since May.', '(5)': 'Paid in May.'}
GRID = [[None, ('2024', []), ('2023', [])], [('Title', []), ('Director', ['(3)']), ('Director', [])], [('Chair', []), ('Chair', ['(3)', '(4)']), ('Member', [])],
        [('Status', []), ('Retired', ['(4)']), ('Active', [])], [('Role', []), ('Director', ['(3)']), ('(acting)', [])], [('Fees', []), ('70', ['2']), ('70', [])],
        [('Series', []), ('Series 2', ['(1)']), ('none', [])], [('Bonus', ['(5)']), ('80', []), ('90', [])]]
T0, T1 = RAW.index(b'<table>'), RAW.index(b'</table>') + 8


def spans():
    out, i = [], 0
    while (i := RAW.find(b'<td>', i)) >= 0: j = RAW.index(b'</td>', i); out.append({'byte_start': i + 4, 'byte_end_exclusive': j}); i = j
    return {(n // 3, n % 3): s for n, s in enumerate(out)}


SPAN = spans()


def at(r, c, s):  # `s` inside cell (r, c)
    a = SPAN[(r, c)]['byte_start'] + RAW[SPAN[(r, c)]['byte_start']:SPAN[(r, c)]['byte_end_exclusive']].index(s.encode()); return {'byte_start': a, 'byte_end_exclusive': a + len(s.encode())}


def note_at(mark):
    s = RAW.index(NOTES[mark].encode(), T1); return {'byte_start': RAW.rindex(b'<p>', 0, s) + 3, 'byte_end_exclusive': RAW.index(b'</p>', s)}


def route():
    cells = [{'r': r, 'c': c, 'rs': 1, 'cs': 1, 'text': x[0], 'markers': list(x[1]), 'anchor': SPAN[(r, c)], 'header': r == 0} for r, row in enumerate(GRID) for c, x in enumerate(row) if x]
    next(x for x in cells if (x['r'], x['c']) == (3, 1))['struck'] = ['Retired']  # the source cancels "Retired" (<s>), not its mark
    notes = [{'id': 'n' + m, 'kind': 'text', 'text': m + ' ' + t, 'marker': m, 'anchor': note_at(m)} for m, t in NOTES.items()]
    return {'file_id': 'pub/marks.htm', 'units': [{'id': 't0', 'kind': 'table', 'cells': cells, 'anchor': {'byte_start': T0, 'byte_end_exclusive': T1}}] + notes}


def target(r, printed, display, marks, label, mark_cell=1, display_cells=None):
    fields = {'printed_value': printed, 'display_value': display, 'value_kind': 'text', 'sign': 'positive', 'row_label': label, 'header_path': ['2024'], 'table_title': None, 'periods': None,
              'footnote_markers': [{'marker_text': m, 'anchor': at(r, mark_cell, '<sup>%s</sup>' % m) | {'byte_start': at(r, mark_cell, '<sup>%s</sup>' % m)['byte_start'] + 5, 'byte_end_exclusive': at(r, mark_cell, '<sup>%s</sup>' % m)['byte_start'] + 5 + len(m)},
                                    'note_anchor': note_at(m), 'note_text': m + ' ' + NOTES[m]} for m in marks]}
    support = {'row_label': {'anchors': [at(r, 0, label)]}, 'header_path': {'anchors': [SPAN[(0, 1)]]}, **({'display_value': {'anchors': [SPAN[x] for x in display_cells]}} if display_cells else {})}
    return {'key_id': 'pub/r%d' % r, 'file_id': 'pub/marks.htm', 'format': 'cell/htm', 'type': 'cell', 'split': 'development', 'anchor': at(r, 1, printed), 'table_anchor': {'byte_start': T0, 'byte_end_exclusive': T1},
            'alternatives': {}, 'excluded': set(), 'support': support, 'fields': fields}


T = {'L': target(1, 'Director', 'Director', ['(3)'], 'Title'), 'G': target(2, 'Chair', 'Chair', ['(3)', '(4)'], 'Chair'), 'S': target(3, 'Retired', '~~Retired~~', ['(4)'], 'Status'),
     'E': target(4, 'Director', 'Director (acting)', ['(3)'], 'Role', display_cells=[(4, 1), (4, 2)]), 'N': target(5, '70', '70', ['2'], 'Fees'), 'M': target(6, 'Series 2', 'Series 2', ['(1)'], 'Series'),
     'B': target(7, '80', '80', ['(5)'], 'Bonus', mark_cell=0)}
ROW = {'L': 1, 'G': 2, 'S': 3, 'E': 4, 'N': 5, 'M': 6, 'B': 7}


def grade_of(name, *edits, raw=RAW):
    rt = route(); cells = {(x['r'], x['c']): x for x in rt['units'][0]['cells']}
    for e in edits: e(rt, cells)
    g = grade.Grader(copy.deepcopy(T[name]), grade.RouteFile(rt, raw)); g.grade_cell()
    return {r['check']: (r['verdict'], r['reason']) for r in g.rows}


def glued(name, text, struck=None):  # the value cell prints its own marks into its text
    return lambda rt, cells: cells[(ROW[name], 1)].update(text=text, markers=[], **({} if struck is None else {'struck': struck}))


class TextValueMarks(unittest.TestCase):
    def test_own_marks_glued_to_a_text_value_are_the_label_equivalence(self):
        for name, texts in (('L', ('Director(3)', '(3)Director')), ('G', ('Chair(3)(4)', '(3)(4)Chair'))):
            self.assertEqual([grade_of(name)[k] for k in ('value', 'footnote_markers')], [('pass', None)] * 2)  # faithful: the marks reported apart
            for text in texts:
                with self.subTest(text=text):
                    got = grade_of(name, glued(name, text)); self.assertEqual((got['value'][0], got['footnote_markers']), ('pass', ('pass', None)))

    def test_a_text_value_printed_with_other_text_fails(self):
        for text in ('Dir ector(3)', 'Directors(3)', 'Director(3) Emeritus', 'Director(4)'):
            with self.subTest(text=text): self.assertEqual(grade_of('L', glued('L', text))['value'], ('fail', 'text'))
        self.assertEqual(grade_of('L', glued('L', 'Director(4)'))['footnote_markers'], ('fail', 'marker_missing'))  # (3) is not printed; (4) is no mark of this value

    def test_the_full_displayed_reading_is_required(self):
        self.assertEqual(grade_of('E', glued('E', 'Director(3)'))['value'][0], 'pass')  # "(acting)" kept in its own cell
        self.assertEqual(grade_of('E', glued('E', 'Director(3)'), lambda rt, cells: rt['units'][0]['cells'].remove(cells[(4, 2)]))['value'], ('fail', 'text'))  # the qualifier lost

    def test_the_mark_is_judged_at_its_own_cell_and_note(self):
        lost = grade_of('L', glued('L', 'Director'))
        self.assertEqual((lost['value'], lost['footnote_markers']), (('pass', None), ('fail', 'marker_missing')))
        self.assertEqual(grade_of('L', glued('L', 'Director'), lambda rt, cells: cells[(1, 2)].update(text='Director(3)'))['footnote_markers'], ('fail', 'marker_missing'))  # on the repeated cell, not its own
        self.assertEqual(grade_of('L', glued('L', 'Director(3)'), lambda rt, cells: next(u for u in rt['units'] if u.get('id') == 'n(3)').update(marker='(4)'))['footnote_markers'], ('fail', 'wrong_note_link'))
        self.assertEqual(grade_of('L', glued('L', 'Director(3)'), lambda rt, cells: rt['units'].remove(next(u for u in rt['units'] if u.get('id') == 'n(3)')))['footnote_markers'], ('fail', 'missing_note'))
        self.assertEqual(grade_of('G', glued('G', 'Chair(3)'))['footnote_markers'], ('fail', 'marker_missing'))  # one of two own marks lost

    def test_numbers_and_mixed_values_keep_the_strict_rule(self):
        self.assertEqual([grade_of('N')[k] for k in ('value', 'footnote_markers')], [('pass', None)] * 2)
        for text, value in (('702', ('fail', 'marker_glued')), ('70(2)', ('fail', 'text')), ('70 (2)', ('fail', 'text'))):  # E11: a mark glued to a number never passes
            with self.subTest(text=text):
                got = grade_of('N', glued('N', text)); self.assertEqual((got['value'], got['footnote_markers']), (value, ('fail', 'marker_glued')))
        self.assertEqual(grade_of('N', glued('N', '70'))['footnote_markers'], ('fail', 'marker_glued'))  # the mark lost
        self.assertEqual(grade_of('N', glued('N', '70'), lambda rt, cells: cells[(5, 2)].update(markers=['2']))['footnote_markers'], ('fail', 'marker_glued'))  # on the other 70
        self.assertEqual([grade_of('M')[k] for k in ('value', 'footnote_markers')], [('pass', None)] * 2)
        got = grade_of('M', glued('M', 'Series 2(1)')); self.assertEqual((got['value'], got['footnote_markers']), (('fail', 'marker_glued'), ('fail', 'marker_glued')))  # a value that prints a number stays strict

    def test_cancellation_of_the_value_and_of_its_attached_mark(self):
        self.assertEqual([grade_of('S')[k] for k in ('value', 'footnote_markers')], [('pass', None)] * 2)  # faithful: "Retired" struck, the mark apart
        kept = grade_of('S', glued('S', 'Retired(4)', ['Retired'])); self.assertEqual((kept['value'][0], kept['footnote_markers']), ('pass', ('pass', None)))
        self.assertEqual(grade_of('S', glued('S', 'Retired(4)', []))['value'], ('fail', 'struck'))  # the cancellation lost
        self.assertEqual(grade_of('L', glued('L', 'Director(3)', ['Director']))['value'], ('fail', 'struck'))  # a cancellation invented
        over = grade_of('S', glued('S', 'Retired(4)', ['Retired(4)']))  # the route strikes the mark too; the source does not
        self.assertEqual(over['value'][0], 'pass')  # the value's own duty: its cancellation is kept
        self.assertNotEqual(over['footnote_markers'][0], 'pass')  # the mark's duty: never a pass for a cancellation the source does not print

    def test_a_mark_on_a_label_keeps_the_label_allowance_and_its_cancellation_duty(self):
        self.assertEqual([grade_of('B')[k] for k in ('row_label', 'footnote_markers')], [('pass', None)] * 2)
        got = grade_of('B', lambda rt, cells: cells[(7, 0)].update(text='Bonus(5)', markers=[])); self.assertEqual((got['row_label'], got['footnote_markers']), (('pass', None), ('pass', None)))
        over = grade_of('B', lambda rt, cells: cells[(7, 0)].update(text='Bonus(5)', markers=[], struck=['Bonus(5)']))  # a cancellation the source does not print, over the label and its mark
        self.assertEqual((over['row_label'][0], over['footnote_markers'][0] != 'pass'), ('fail', True))

    def test_without_the_source_nothing_is_proved_wrong(self):
        got = grade_of('S', glued('S', 'Retired(4)', ['Retired']), raw=None)  # no source bytes: the existing strike check compares the route's own claim with the key, it locates nothing in a source
        self.assertNotEqual(got['value'][0], 'fail'); self.assertNotEqual(got['footnote_markers'][0], 'fail')


def one_row(label_html, value_html, label_struck=None, value_struck=None, key_mark='(4)', unlinked=None, only_unlinked=False, narrow=False, value_markers=None):
    """One row 'label | value' plus the note of (4) (public class controls, public_marker_class_check_v1): the target is the value; (4) is linked to its
    note; `unlinked` is the key's own mark (1) on the label, an entry with no note anchor."""
    raw = ('<table><tr><td>Name</td><td>Status</td></tr><tr><td>%s</td><td>%s</td></tr></table><p><sup>(4)</sup> The note.</p>' % (label_html, value_html)).encode()
    def sp(b, n=0):
        i = -1
        for _ in range(n + 1): i = raw.index(b, i + 1)
        return {'byte_start': i, 'byte_end_exclusive': i + len(b)}
    td = lambda html: {'byte_start': raw.index(('<td>' + html + '</td>').encode()) + 4, 'byte_end_exclusive': raw.index(('<td>' + html + '</td>').encode()) + 4 + len(html.encode())}
    plain = lambda html: html.replace('<sup>', '').replace('</sup>', '').replace('<s>', '').replace('</s>', '')
    note = {'byte_start': raw.index(b'<p>') + 3, 'byte_end_exclusive': raw.index(b'</p>')}
    marks = [{'marker_text': key_mark, 'anchor': sp(b'(4)'), 'note_anchor': note, 'note_text': '(4) The note.'}]
    if unlinked: marks = ([] if only_unlinked else marks) + [{'marker_text': unlinked, 'anchor': sp(b'(1)')}]
    t = {'byte_start': 0, 'byte_end_exclusive': raw.index(b'</table>') + 8}
    fields = {'printed_value': 'Retired', 'display_value': '~~Retired~~', 'value_kind': 'text', 'sign': 'positive', 'row_label': plain(label_html), 'header_path': ['Status'], 'table_title': None, 'periods': None, 'footnote_markers': marks}
    support = {'row_label': {'anchors': [td(label_html)]}, 'header_path': {'anchors': [sp(b'Status')]}, **({'footnote_markers': {'anchors': [sp(b'(4)')]}} if narrow else {})}
    key = {'key_id': 'pub/one', 'file_id': 'pub/one.htm', 'format': 'cell/htm', 'type': 'cell', 'split': 'development', 'anchor': sp(b'Retired'), 'table_anchor': t, 'alternatives': {}, 'excluded': set(), 'support': support, 'fields': fields}
    cell = lambda r, c, text, a, struck=None: dict({'r': r, 'c': c, 'rs': 1, 'cs': 1, 'text': text, 'anchor': a}, **({'struck': struck} if struck else {}))
    cells = [cell(0, 0, 'Name', sp(b'Name')), cell(0, 1, 'Status', sp(b'Status')), cell(1, 0, plain(label_html), td(label_html), label_struck), dict(cell(1, 1, 'Retired' if value_markers else plain(value_html), td(value_html), value_struck), **({'markers': value_markers} if value_markers else {}))]  # value_markers: the mark reported apart
    rt = {'file_id': 'pub/one.htm', 'units': [{'id': 't0', 'kind': 'table', 'cells': cells, 'anchor': t}, {'id': 'n', 'kind': 'text', 'text': '(4) The note.', 'marker': '(4)', 'anchor': note}]}
    g = grade.Grader(key, grade.RouteFile(rt, raw)); g.grade_cell()
    return {r['check']: (r['verdict'], r['reason']) for r in g.rows}


class EveryMarkOwnsItsCarriers(unittest.TestCase):  # each of the target's marks, linked to a note or not, is judged on its own carriers' strikes
    def test_an_unlinked_mark_beside_a_linked_one(self):
        cancelled = '<s>Retired</s><sup>(4)</sup>'
        self.assertEqual(one_row('Jane Roe<sup>(1)</sup>', cancelled, value_struck=['Retired'], unlinked='(1)')['footnote_markers'], ('pass', None))  # U1: the source strikes no mark
        self.assertNotEqual(one_row('Jane Roe<sup>(1)</sup>', cancelled, ['(1)'], ['Retired'], unlinked='(1)')['footnote_markers'][0], 'pass')  # U2: a strike the source does not print
        self.assertNotEqual(one_row('Jane Roe<sup><s>(1)</s></sup>', cancelled, None, ['Retired'], unlinked='~~(1)~~')['footnote_markers'][0], 'pass')  # U3: the cancelled mark's strike lost
        self.assertEqual(one_row('Jane Roe<sup><s>(1)</s></sup>', cancelled, ['(1)'], ['Retired'], unlinked='~~(1)~~')['footnote_markers'], ('pass', None))  # U4: kept
        self.assertNotEqual(one_row('Jane Roe<sup>(1)</sup>', cancelled, ['(1)'], ['Retired'], unlinked='(1)', only_unlinked=True)['footnote_markers'][0], 'pass')  # U0: the only mark, unlinked

    def test_a_cancelled_mark_authored_with_its_own_anchor(self):
        src = '<s>Retired</s><sup><s>(4)</s></sup>'  # the key authors the cancelled mark '~~(4)~~' and supports it with the mark's own bytes
        self.assertEqual(one_row('Jane Roe', src, value_struck=['Retired(4)'], key_mark='~~(4)~~', narrow=True)['footnote_markers'], ('pass', None))  # K3
        self.assertNotEqual(one_row('Jane Roe', src, value_struck=['Retired'], key_mark='~~(4)~~', narrow=True)['footnote_markers'][0], 'pass')  # its strike lost


class StrikesWithoutAPlace(unittest.TestCase):  # a route strike that has no place in its item's text certifies nothing; definite failures stay failures
    def test_a_strike_on_a_mark_reported_apart(self):
        src = '<s>Retired</s><sup>(4)</sup>'
        s1 = one_row('Jane Roe', src, value_struck=['Retired'], value_markers=['(4)'])  # S1: the source strikes "Retired" only
        self.assertEqual((s1['value'], s1['footnote_markers']), (('pass', None), ('pass', None)))
        s2 = one_row('Jane Roe', src, value_struck=['Retired', '(4)'], value_markers=['(4)'])  # S2: a strike on the separated mark the source does not print
        self.assertNotEqual(s2['footnote_markers'][0], 'pass'); self.assertNotEqual(s2['value'][0], 'pass')

    def test_an_unplaceable_phrase_and_a_number(self):
        self.assertNotEqual(one_row('Jane Roe', '<s>Retired</s><sup>(4)</sup>', value_struck=['Retired', 'Gone'], value_markers=['(4)'])['value'][0], 'pass')  # "Gone" is printed nowhere
        self.assertNotEqual(grade_of('N', lambda rt, cells: cells[(5, 1)].update(struck=['2']))['value'][0], 'pass')  # a strike on the number's mark, kept apart; the faithful N passes (above)

    def test_known_failures_stay_failures_beside_an_unplaceable_strike(self):
        self.assertEqual(grade_of('S', lambda rt, cells: cells[(3, 1)].update(struck=['Gone']))['value'], ('fail', 'struck'))  # the cancellation lost
        self.assertEqual(grade_of('L', lambda rt, cells: cells[(1, 1)].update(struck=['Director', 'Gone']))['value'], ('fail', 'struck'))  # a cancellation invented

    def test_exact_places_still_certify(self):
        got = grade_of('S', lambda rt, cells: cells[(3, 1)].update(struck_at=[[0, 7]]))  # the source's own place of "Retired"
        self.assertEqual((got['value'], got['footnote_markers']), (('pass', None), ('pass', None)))

    def test_a_cancelled_mark_reported_apart_is_still_that_mark(self):
        src = '<s>Retired</s><sup><s>(4)</s></sup>'  # the key authors '~~(4)~~'; the route reports the mark apart as '(4)'
        kept = one_row('Jane Roe', src, value_struck=['Retired', '(4)'], key_mark='~~(4)~~', narrow=True, value_markers=['(4)'])
        self.assertNotEqual(kept['footnote_markers'], ('fail', 'marker_missing'))  # the same mark; whether its strike is kept is not certified here (a scorer limit)
        self.assertNotEqual(one_row('Jane Roe', src, value_struck=['Retired'], key_mark='~~(4)~~', narrow=True, value_markers=['(4)'])['footnote_markers'][0], 'pass')  # its strike lost


if __name__ == '__main__':
    unittest.main()
