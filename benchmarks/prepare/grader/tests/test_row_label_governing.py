"""A row label printed on more than one row: association comes from the key's governing place (DESIGN §3: every listed search occurrence counts for
preservation, the governing one for association), as table_title already reads it. Invented source; every truth comes from the markup."""
import unittest

from benchmarks.prepare.grader import grade

ROWS = {  # table index -> rows, as printed ('' = an empty cell)
    0: [['Item', '2026'], ['Earnings per share:', ''], ['Basic', '1.10'], ['Diluted', '1.08'], ['Weighted average shares:', ''], ['Basic', '100'], ['Diluted', '102'], ['Total shares', '202']],
    1: [['Kanwardev', 'Salary', '700'], ['', 'Bonus', '80'], ['', 'Total', '780'], ['Donald', 'Salary', '600'], ['', 'Total', '650']],
}
RAW = (b'<p>Results</p><table>' + b''.join(b'<tr>' + b''.join(b'<td>%s</td>' % c.encode() for c in row) + b'</tr>' for row in ROWS[0]) + b'</table>'
       + b'<table>' + b''.join(b'<tr>' + b''.join(b'<td>%s</td>' % c.encode() for c in row) + b'</tr>' for row in ROWS[1]) + b'</table>'
       + b'<table><tr><td rowspan="2">Diluted</td><td>Q1</td><td>5</td></tr><tr><td>Q2</td><td>6</td></tr><tr><td>Diluted</td><td>Q3</td><td>7</td></tr></table>')
SPANS = []
i = -1
while (i := RAW.find(b'<table>', i + 1)) >= 0: SPANS.append((i, RAW.index(b'</table>', i) + 8))


def place(text, table, k=0):
    """The k-th printed place of `text` inside a table's element (its bytes, from the markup)."""
    lo, hi = SPANS[table]; p = lo - 1
    for _ in range(k + 1): p = RAW.index(text.encode(), p + 1, hi)
    return {'byte_start': p, 'byte_end_exclusive': p + len(text)}


def table_unit(t):
    cells, pos = [], SPANS[t][0]
    if t < 2:
        for r, row in enumerate(ROWS[t]):
            for c, text in enumerate(row):
                if not text: continue
                p = RAW.index(text.encode(), pos, SPANS[t][1]); pos = p + len(text)
                cells.append({'r': r, 'c': c, 'rs': 1, 'cs': 1, 'text': text, 'anchor': {'byte_start': p, 'byte_end_exclusive': p + len(text)}})
    else:  # the first label spans two rows (rowspan="2")
        for r, c, rs, text in ((0, 0, 2, 'Diluted'), (0, 1, 1, 'Q1'), (0, 2, 1, '5'), (1, 1, 1, 'Q2'), (1, 2, 1, '6'), (2, 0, 1, 'Diluted'), (2, 1, 1, 'Q3'), (2, 2, 1, '7')):
            p = RAW.index(text.encode(), pos, SPANS[t][1]); pos = p + len(text)
            cells.append({'r': r, 'c': c, 'rs': rs, 'cs': 1, 'text': text, 'anchor': {'byte_start': p, 'byte_end_exclusive': p + len(text)}})
    return {'id': 't%d' % t, 'kind': 'table', 'anchor': {'byte_start': SPANS[t][0], 'byte_end_exclusive': SPANS[t][1]}, 'source_table': {'tag_start': SPANS[t][0], 'claims': 1}, 'cells': cells}


def units():
    p = RAW.index(b'Results')
    return [{'id': 'p', 'kind': 'text', 'text': 'Results', 'anchor': {'byte_start': p, 'byte_end_exclusive': p + 7}}] + [table_unit(t) for t in range(3)]


def piece(text, places, governing=None):
    out = {'text': text, 'byte_ranges': [[a['byte_start'], a['byte_end_exclusive']] for a in places]}
    if governing is not None: out['governing'] = [[a['byte_start'], a['byte_end_exclusive']] for a in governing]
    return out


def label(table, value, row_label, support, route=None):
    """The row_label verdict of `value` (its cell in `table`) under `support`."""
    route = units() if route is None else route
    tb = route[1 + table]; v = next(c for c in tb['cells'] if c['text'] == value)
    t = {'key_id': 'syn/RL', 'file_id': 'syn/rl.htm', 'format': 'cell/htm', 'type': 'cell', 'split': 'development', 'anchor': v['anchor'], 'table_anchor': tb['anchor'],
         'alternatives': {}, 'excluded': set(), 'support': {'row_label': support}, 'fields': {'printed_value': value, 'display_value': value, 'row_label': row_label}}
    g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/rl.htm', 'units': route}, RAW)); g.grade_cell()
    return next((r['verdict'], r.get('reason')) for r in g.rows if r['check'] == 'row_label')


def cell_at(route, table, a):
    return next(c for c in route[1 + table]['cells'] if c['anchor'] == a)


EVERY_DILUTED = [place('Diluted', 0, 0), place('Diluted', 0, 1), place('Diluted', 2, 0), place('Diluted', 2, 1)]  # every printed place of the text, both tables


class RepeatedRowLabel(unittest.TestCase):
    def test_a_faithful_repeated_label_passes_at_its_governing_place(self):
        for value, own in (('1.08', place('Diluted', 0, 0)), ('102', place('Diluted', 0, 1))):  # the same text on two rows of one table, and in another table
            self.assertEqual(label(0, value, 'Diluted', {'pieces': [piece('Diluted', EVERY_DILUTED, [own])]}), ('pass', None))
        self.assertEqual(label(0, '100', 'Basic', {'pieces': [piece('Basic', [place('Basic', 0, 0), place('Basic', 0, 1)], [place('Basic', 0, 1)])]}), ('pass', None))

    def test_the_listing_order_does_not_decide(self):  # permutation: the listed places in another order, the governing place first or last
        own = place('Diluted', 0, 0)
        for listed in (EVERY_DILUTED, EVERY_DILUTED[::-1], EVERY_DILUTED[1:] + EVERY_DILUTED[:1]):
            self.assertEqual(label(0, '1.08', 'Diluted', {'pieces': [piece('Diluted', listed, [own])]}), ('pass', None))

    def test_a_unique_label_reads_as_before(self):
        own = place('Total shares', 0)
        for support in ({'pieces': [piece('Total shares', [own], [own])]}, {'pieces': [piece('Total shares', [own])]}, {'anchors': [own]}):
            self.assertEqual(label(0, '202', 'Total shares', support), ('pass', None))

    def test_the_own_governing_label_lost_changed_or_moved_fails(self):
        own = place('Diluted', 0, 0); support = {'pieces': [piece('Diluted', EVERY_DILUTED, [own])]}
        lost = units(); lost[1]['cells'].remove(cell_at(lost, 0, own))
        self.assertEqual(label(0, '1.08', 'Diluted', support, lost), ('fail', 'missing'))  # the other row's equal label is no carrier
        changed = units(); cell_at(changed, 0, own)['text'] = 'Dilutive'
        self.assertEqual(label(0, '1.08', 'Diluted', support, changed)[0], 'fail')
        moved = units(); cell_at(moved, 0, own)['r'] = 2  # the route prints the value's own label on the row above
        self.assertEqual(label(0, '1.08', 'Diluted', support, moved), ('fail', 'row'))

    def test_a_governing_place_on_another_row_or_table_is_not_this_rows_label(self):  # mutation: the association really comes from the governing place
        self.assertEqual(label(0, '1.08', 'Diluted', {'pieces': [piece('Diluted', EVERY_DILUTED, [place('Diluted', 0, 1)])]}), ('fail', 'row'))
        self.assertEqual(label(0, '1.08', 'Diluted', {'pieces': [piece('Diluted', EVERY_DILUTED, [place('Diluted', 2, 0)])]}), ('fail', 'missing'))  # another table's place: no carrier in this table

    def test_every_governing_piece_of_a_carried_label_must_hold(self):
        totals = [place('Total', 1, 0), place('Total', 1, 1)]; kan = place('Kanwardev', 1)
        both = lambda gov_total: {'pieces': [piece('Kanwardev', [kan], [kan]), piece('Total', totals, [gov_total])]}
        self.assertEqual(label(1, '780', 'Kanwardev | Total', both(totals[0])), ('pass', None))  # the name carried down its block, the block's own total
        self.assertEqual(label(1, '650', 'Donald | Total', {'pieces': [piece('Donald', [place('Donald', 1)], [place('Donald', 1)]), piece('Total', totals, [totals[1]])]}), ('pass', None))
        self.assertEqual(label(1, '780', 'Kanwardev | Total', both(totals[1])), ('fail', 'row'))  # the other block's total
        no_name = units(); no_name[2]['cells'].remove(cell_at(no_name, 1, kan))
        self.assertNotEqual(label(1, '780', 'Kanwardev | Total', both(totals[0]), no_name)[0], 'pass')  # one governing piece lost
        blocked = units(); blocked[2]['cells'].append({'r': 1, 'c': 0, 'rs': 1, 'cs': 1, 'text': 'Other', 'anchor': place('Bonus', 1)})
        self.assertEqual(label(1, '780', 'Kanwardev | Total', both(totals[0]), blocked), ('fail', 'row'))  # a stub between ends the block (existing carried rule)

    def test_a_label_spanning_rows_labels_each_of_them(self):
        own, other = place('Diluted', 2, 0), place('Diluted', 2, 1)
        self.assertEqual(label(2, '6', 'Diluted', {'pieces': [piece('Diluted', [own, other], [own])]}), ('pass', None))  # rowspan="2" covers the value's row
        self.assertEqual(label(2, '7', 'Diluted', {'pieces': [piece('Diluted', [own, other], [other])]}), ('pass', None))
        self.assertEqual(label(2, '7', 'Diluted', {'pieces': [piece('Diluted', [own, other], [own])]}), ('fail', 'row'))  # the spanning label stops at its own rows

    def test_mixed_and_absent_governing_information(self):
        totals = [place('Total', 1, 0), place('Total', 1, 1)]; kan = place('Kanwardev', 1)
        self.assertEqual(label(1, '780', 'Kanwardev | Total', {'pieces': [piece('Kanwardev', [kan]), piece('Total', totals, [totals[0]])]}), ('pass', None))  # one piece without governing: its listed place
        # retained limitation: with no governing place, no nearest or own place is guessed; every listed place is read, as today
        self.assertEqual(label(1, '780', 'Kanwardev | Total', {'pieces': [piece('Kanwardev', [kan]), piece('Total', totals)]}), ('fail', 'text'))

    def test_plain_anchors_listing_both_places_keep_todays_reading(self):  # retained limitation (title decision 2): plain anchors carry no governing place
        self.assertEqual(label(0, '1.08', 'Diluted', {'anchors': [place('Diluted', 0, 0), place('Diluted', 0, 1)]}), ('fail', 'text'))
        self.assertEqual(label(0, '1.08', 'Diluted', {'anchors': [place('Diluted', 0, 0)]}), ('pass', None))

    def test_formatting_and_honesty_stay_with_their_owners(self):
        own, other = place('Diluted', 0, 0), place('Diluted', 0, 1); support = {'pieces': [piece('Diluted', [own, other], [own])]}
        invented = units(); cell_at(invented, 0, own)['struck'] = ['Diluted']
        self.assertEqual(label(0, '1.08', 'Diluted', support, invented), ('fail', 'struck'))  # a strike the source does not print, on the own label
        misread = units(); cell_at(misread, 0, other)['text'] = 'Dilutd'  # the other row's copy misread: this value's label is kept
        self.assertEqual(label(0, '1.08', 'Diluted', support, misread), ('pass', None))
        self.assertEqual(grade.gates_for_file(grade.RouteFile({'file_id': 'syn/rl.htm', 'units': misread}, RAW), 'OK')['dishonest'], 1)  # reported by the honesty gate, never silent
        self.assertEqual(grade.gates_for_file(grade.RouteFile({'file_id': 'syn/rl.htm', 'units': units()}, RAW), 'OK')['dishonest'], 0)


if __name__ == '__main__':
    unittest.main()
