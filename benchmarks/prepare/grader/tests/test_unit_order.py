"""A unit line outside the value's table keeps the source's own side of that table, with nothing the source prints elsewhere listed between them
(lead_in's C6 rule, read on either side); a line in the table's own caption is in the table (own_caption). Where the source cannot order the places,
the check stays unresolved. Invented sources; every truth comes from the markup."""
import copy
import unittest

from benchmarks.prepare.grader import grade

U = '(in millions)'
PASS = ('pass', None, None)
MOVED = ('fail', 'placement', None)


def at(raw, text, k=0):
    p = -1
    for _ in range(k + 1): p = raw.index(text.encode(), p + 1)
    return {'byte_start': p, 'byte_end_exclusive': p + len(text)}


def table(raw, tid, k, rows):
    s = -1
    for _ in range(k + 1): s = raw.index(b'<table', s + 1)
    e, cells, pos = raw.index(b'</table>', s) + 8, [], s
    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            if not text: continue
            p = raw.index(text.encode(), pos, e); pos = p + len(text)
            cells.append({'r': r, 'c': c, 'rs': 1, 'cs': 1, 'text': text, 'anchor': {'byte_start': p, 'byte_end_exclusive': p + len(text)}})
    return {'id': tid, 'kind': 'table', 'anchor': {'byte_start': s, 'byte_end_exclusive': e}, 'source_table': {'tag_start': s, 'claims': 1}, 'cells': cells}


def text(raw, uid, t, k=0):
    return {'id': uid, 'kind': 'text', 'text': t, 'anchor': at(raw, t, k)}


def governing(raw, n, own):
    return {'pieces': [{'text': U, 'byte_ranges': [[at(raw, U, i)['byte_start'], at(raw, U, i)['byte_end_exclusive']] for i in range(n)], 'governing': [[at(raw, U, own)['byte_start'], at(raw, U, own)['byte_end_exclusive']]]}]}


def unit(raw, route, support, value='9', fmt=None, file_id='syn/u.htm'):
    """The complete unit_printed row (verdict, reason, detail) for the value cell `value`."""
    tb = next(u for u in route if u['kind'] == 'table' and any(c['text'] == value for c in u['cells']))
    v = [c for c in tb['cells'] if c['text'] == value][-1]
    t = {'key_id': 'syn/U', 'file_id': file_id, 'format': 'cell/' + ('pdf' if fmt == 'pdf' else 'htm'), 'type': 'cell', 'split': 'development', 'anchor': v['anchor'], 'table_anchor': tb['anchor'],
         'alternatives': {}, 'excluded': set(), 'support': {'unit_printed': support} if support else {}, 'fields': {'printed_value': value, 'display_value': value, 'unit_printed': U}}
    g = grade.Grader(t, grade.RouteFile({'file_id': file_id, 'units': copy.deepcopy(route)}, raw, fmt)); g.grade_cell()
    return next((r['verdict'], r.get('reason'), r.get('detail')) for r in g.rows if r['check'] == 'unit_printed')


# the unit line before each table, a note between the first table and the second line, a third table after
B = b'<p>' + U.encode() + b'</p><table><tr><td>Revenue</td><td>12</td></tr></table><p>Note on costs</p><p>' + U.encode() + b'</p><table><tr><td>Costs</td><td>9</td></tr></table><table><tr><td>Other</td><td>3</td></tr></table>'
A_, B_, C_ = table(B, 'a', 0, [['Revenue', '12']]), table(B, 'b', 1, [['Costs', '9']]), table(B, 'c', 2, [['Other', '3']])
U1, NOTE, U2 = text(B, 'u1', U, 0), text(B, 'n', 'Note on costs'), text(B, 'u2', U, 1)
# the unit line after each table
AFTER = b'<table><tr><td>Revenue</td><td>12</td></tr></table><p>' + U.encode() + b'</p><table><tr><td>Costs</td><td>9</td></tr></table><p>' + U.encode() + b'</p><table><tr><td>Other</td><td>3</td></tr></table>'
FA, FB, FC = table(AFTER, 'a', 0, [['Revenue', '12']]), table(AFTER, 'b', 1, [['Costs', '9']]), table(AFTER, 'c', 2, [['Other', '3']])
W1, W2 = text(AFTER, 'w1', U, 0), text(AFTER, 'w2', U, 1)
# the unit line in the table's own <caption>
CAP = b'<p>Costs</p><table><caption>' + U.encode() + b'</caption><tr><td>Costs</td><td>9</td></tr></table>'


def caption_unit(raw, tb, anchor=None):
    return {'id': 'cap', 'kind': 'caption', 'text': U, 'anchor': anchor or at(raw, U), 'source_table': {'tag_start': tb['anchor']['byte_start'], 'claims': 1},
            'source': {'byte_start': raw.index(b'<caption>'), 'byte_end_exclusive': raw.index(b'</caption>') + 10}}


class UnitOrder(unittest.TestCase):
    def test_a_unit_kept_on_its_source_side_passes(self):
        self.assertEqual(unit(B, [U1, A_, NOTE, U2, B_, C_], governing(B, 2, 1)), PASS)  # before its table, another table and a note in the document
        self.assertEqual(unit(AFTER, [FA, W1, FB, W2, FC], governing(AFTER, 2, 1)), PASS)  # the source prints the unit after its table
        mid = b'<p>' + U.encode() + b'</p><p>Costs are shown net.</p><table><tr><td>Costs</td><td>9</td></tr></table>'
        self.assertEqual(unit(mid, [text(mid, 'u', U), text(mid, 'p', 'Costs are shown net.'), table(mid, 't', 0, [['Costs', '9']])], governing(mid, 1, 0)), PASS)  # ordinary source content between (C6)

    def test_a_unit_moved_across_another_table_or_to_the_other_side_fails(self):
        self.assertEqual(unit(B, [U2, U1, A_, NOTE, B_, C_], governing(B, 2, 1)), MOVED)  # listed before the earlier table
        self.assertEqual(unit(AFTER, [FA, W1, FB, FC, W2], governing(AFTER, 2, 1)), MOVED)  # an after-table unit listed past the next table
        self.assertEqual(unit(B, [U1, A_, NOTE, B_, U2, C_], governing(B, 2, 1)), MOVED)  # the source prints it before its table; the route after

    def test_an_uncertain_reading_orders_by_bytes_alike(self):
        S = b'<style>.x{display:none}</style>' + B
        a, b, c = table(S, 'a', 0, [['Revenue', '12']]), table(S, 'b', 1, [['Costs', '9']]), table(S, 'c', 2, [['Other', '3']])
        u1, n, u2 = text(S, 'u1', U, 0), text(S, 'n', 'Note on costs'), text(S, 'u2', U, 1)
        self.assertFalse(grade.RouteFile({'file_id': 'syn/u.htm', 'units': []}, S).vis.certain)
        self.assertEqual(unit(S, [u1, a, n, u2, b, c], governing(S, 2, 1)), PASS)
        self.assertEqual(unit(S, [u2, u1, a, n, b, c], governing(S, 2, 1)), MOVED)

    def test_pdf_boxes_keep_page_order(self):
        box = lambda y0, y1, page=1: {'page': page, 'region': [50, y0, 400, y1]}
        a = {'id': 'a', 'kind': 'table', 'anchor': box(100, 140), 'cells': [{'r': 0, 'c': 0, 'text': 'Revenue', 'anchor': box(100, 112)}, {'r': 0, 'c': 1, 'text': '12', 'anchor': {'page': 1, 'region': [300, 100, 400, 112]}}]}
        b = {'id': 'b', 'kind': 'table', 'anchor': box(200, 240), 'cells': [{'r': 0, 'c': 0, 'text': 'Costs', 'anchor': box(200, 212)}, {'r': 0, 'c': 1, 'text': '9', 'anchor': {'page': 1, 'region': [300, 200, 400, 212]}}]}
        u1, u2 = {'id': 'u1', 'kind': 'text', 'text': U, 'anchor': box(80, 92)}, {'id': 'u2', 'kind': 'text', 'text': U, 'anchor': box(180, 192)}
        own = {'anchors': [{'page': 1, 'region': [50, 180, 400, 192]}]}  # PDF keys carry plain box anchors: the own line
        self.assertEqual(unit(None, [u1, a, u2, b], own, fmt='pdf', file_id='syn/u.pdf'), PASS)
        self.assertEqual(unit(None, [u2, u1, a, b], own, fmt='pdf', file_id='syn/u.pdf'), MOVED)


    def test_an_in_table_unit_keeps_the_existing_row_rule(self):
        raw = b'<table><tr><td>' + U.encode() + b'</td><td>2026</td></tr><tr><td>Costs</td><td>9</td></tr></table>'
        t = table(raw, 't', 0, [[U, '2026'], ['Costs', '9']]); next(c for c in t['cells'] if c['text'] == U)['r'] = 2  # the route puts the unit cell below the value row
        self.assertEqual(unit(raw, [t], governing(raw, 1, 0)), ('unresolved', 'source_order', None))  # semantic truth unchanged (moved: wrong); automatic: only byte order says so, unproved - never a pass (table-order-conservative)

    def test_the_tables_own_caption_is_in_the_table(self):
        tb = table(CAP, 't', 0, [['Costs', '9']]); p = text(CAP, 'p', 'Costs')
        for route in ([p, caption_unit(CAP, tb), tb], [p, tb, caption_unit(CAP, tb)]):  # listed before or after its table: own_caption proves it in the table
            self.assertEqual(unit(CAP, route, governing(CAP, 1, 0)), PASS)

    def test_a_carrier_that_only_overlaps_the_table_is_not_its_caption(self):  # overlap is not containment: partial, overbroad and discontiguous carriers
        b_start, b_end = B_['anchor']['byte_start'], B_['anchor']['byte_end_exclusive']; own = at(B, U, 1)
        partial = dict(U2, anchor={'byte_start': own['byte_start'], 'byte_end_exclusive': b_start + 10})  # runs from its own place into the table
        self.assertEqual(unit(B, [U1, A_, NOTE, B_, partial, C_], governing(B, 2, 1)), MOVED)
        overbroad = dict(U2, anchor={'byte_start': own['byte_start'], 'byte_end_exclusive': b_end})  # covers its place and the whole table
        self.assertEqual(unit(B, [U1, A_, NOTE, B_, overbroad, C_], governing(B, 2, 1)), MOVED)
        tb = table(CAP, 't', 0, [['Costs', '9']]); inside = at(CAP, U); before = at(CAP, 'Costs')
        split = caption_unit(CAP, tb, anchor=[before, inside])  # claims the table's caption, but its first place stands before the table: not wholly in its caption
        self.assertEqual(unit(CAP, [p for p in [tb, split]], governing(CAP, 1, 0)), MOVED)  # listed after the table while its own first place is before it
        self.assertEqual(unit(CAP, [tb, caption_unit(CAP, tb)], governing(CAP, 1, 0)), PASS)  # positive: the genuine own caption, same order

    def test_unknown_source_order_stays_unresolved_but_proved_displacement_fails(self):
        loose = {'id': 'x', 'kind': 'text', 'text': 'Inserted', 'anchor': None}  # a unit with no source place, listed between the line and its table
        self.assertEqual(unit(B, [U1, A_, NOTE, U2, loose, B_, C_], governing(B, 2, 1))[:2], ('unresolved', 'source_order'))
        self.assertEqual(unit(B, [U2, loose, U1, A_, NOTE, B_, C_], governing(B, 2, 1)), MOVED)  # the earlier table between them is proved displaced
        boxed = {'id': 'y', 'kind': 'text', 'text': 'Inserted', 'anchor': {'page': 1, 'region': [0, 0, 10, 10]}}  # a page box in an HTML route: RouteFile.possible refuses it, so the unit has no place (admitted mixed places: test_a_place_of_several_spans_must_lie_in_one_frame)
        self.assertEqual(unit(B, [U1, A_, NOTE, U2, boxed, B_, C_], governing(B, 2, 1))[:2], ('unresolved', 'source_order'))

    def test_no_key_place_or_plain_support_keeps_todays_reading(self):  # no governing association: no own place is guessed, no new order claim
        self.assertEqual(unit(B, [U2, U1, A_, NOTE, B_, C_], None), PASS)  # no key anchor: today's text lookup
        self.assertEqual(unit(B, [dict(U2, anchor=None), U1, A_, NOTE, B_, C_], None), PASS)  # no key anchor and an unplaced carrier: no order claim either way
        self.assertEqual(unit(B, [U1, A_, NOTE, B_, C_], {'anchors': [at(B, U, 0), at(B, U, 1)]}), PASS)  # plain anchors, own line lost: today's acceptance

    def test_a_page_less_pdf_table_cannot_be_ordered(self):  # RouteFile refuses a PDF box naming no page (`possible`): the table has no place to order by
        box = lambda y0, y1: {'page': 1, 'region': [50, y0, 400, y1]}
        cells = [{'r': 0, 'c': 0, 'text': 'Costs', 'anchor': box(200, 212)}, {'r': 0, 'c': 1, 'text': '9', 'anchor': {'page': 1, 'region': [300, 200, 400, 212]}}]
        a = {'id': 'a', 'kind': 'table', 'anchor': box(100, 140), 'cells': [{'r': 0, 'c': 0, 'text': 'Revenue', 'anchor': box(100, 112)}, {'r': 0, 'c': 1, 'text': '12', 'anchor': {'page': 1, 'region': [300, 100, 400, 112]}}]}
        u1, u2 = {'id': 'u1', 'kind': 'text', 'text': U, 'anchor': box(80, 92)}, {'id': 'u2', 'kind': 'text', 'text': U, 'anchor': box(180, 192)}
        own = {'anchors': [{'page': 1, 'region': [50, 180, 400, 192]}]}
        paged = {'id': 'b', 'kind': 'table', 'anchor': box(200, 240), 'cells': cells}; page_less = dict(paged, anchor={'region': [50, 200, 400, 240]})
        self.assertEqual(unit(None, [u1, a, u2, paged], own, fmt='pdf', file_id='syn/u.pdf'), PASS)  # positive control: a valid page
        self.assertEqual(unit(None, [u2, u1, a, paged], own, fmt='pdf', file_id='syn/u.pdf'), MOVED)
        for route in ([u1, a, u2, page_less], [u2, u1, a, page_less]):  # faithful or moved: no order is claimed
            self.assertEqual(unit(None, route, own, fmt='pdf', file_id='syn/u.pdf')[:2], ('unresolved', 'source_order'))

    def test_a_place_of_several_spans_must_lie_in_one_frame(self):
        own = at(B, U, 1); half = own['byte_start'] + 7
        two = [{'byte_start': own['byte_start'], 'byte_end_exclusive': half}, {'byte_start': half, 'byte_end_exclusive': own['byte_end_exclusive']}]
        self.assertEqual(unit(B, [U1, A_, NOTE, dict(U2, anchor=two), B_, C_], governing(B, 2, 1)), PASS)  # same frame, two byte spans: positive control
        self.assertEqual(unit(B, [dict(U2, anchor=two), U1, A_, NOTE, B_, C_], governing(B, 2, 1)), MOVED)
        pic = {'file': 'chart.png', 'region': [0, 0, 40, 10]}  # an admitted picture-file box: no byte order against the page
        for spans_ in ([own, pic], [pic, own]):  # bytes and a picture box in one place, in either listing order: no one frame, never a guessed side
            for route in ([U1, A_, NOTE, dict(U2, anchor=spans_), B_, C_], [dict(U2, anchor=spans_), U1, A_, NOTE, B_, C_]):
                self.assertEqual(unit(B, route, governing(B, 2, 1))[:2], ('unresolved', 'source_order'))
        mid = b'<p>' + U.encode() + b'</p><p>Costs are shown net.</p><table><tr><td>Costs</td><td>9</td></tr></table>'
        para = text(mid, 'p', 'Costs are shown net.')
        for spans_ in ([para['anchor'], pic], [pic, para['anchor']]):  # a unit between them whose byte place is between, plus a picture place: no one frame
            self.assertEqual(unit(mid, [text(mid, 'u', U), dict(para, anchor=spans_), table(mid, 't', 0, [['Costs', '9']])], governing(mid, 1, 0))[:2], ('unresolved', 'source_order'))
        two_pictures = [pic, {'file': 'logo.png', 'region': [0, 0, 40, 10]}]  # two picture files: no page order either
        self.assertEqual(unit(B, [U1, A_, NOTE, dict(U2, anchor=[own, *two_pictures]), B_, C_], governing(B, 2, 1))[:2], ('unresolved', 'source_order'))


if __name__ == '__main__':
    unittest.main()
