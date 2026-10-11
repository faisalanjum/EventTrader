"""Association reads the key's governing place (DESIGN §3: every listed search occurrence counts for preservation, the governing one for association) in
the six association consumers - row_context, header_path, corner_text, lead_in, section_path, unit_printed - as table_title and row_label already do.
Each case prints the same text in more than one place; every truth comes from the invented markup."""
import copy
import unittest

from benchmarks.prepare.grader import grade


def at(raw, text, k=0):
    p = -1
    for _ in range(k + 1): p = raw.index(text.encode(), p + 1)
    return {'byte_start': p, 'byte_end_exclusive': p + len(text)}


def table(raw, tid, k, rows):
    """A route table over the k-th <table> of raw: every non-empty cell anchored at its own bytes, in order."""
    s = -1
    for _ in range(k + 1): s = raw.index(b'<table>', s + 1)
    e, cells, pos = raw.index(b'</table>', s) + 8, [], s
    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            if not text: continue
            p = raw.index(text.encode(), pos, e); pos = p + len(text)
            cells.append({'r': r, 'c': c, 'rs': 1, 'cs': 1, 'text': text, 'anchor': {'byte_start': p, 'byte_end_exclusive': p + len(text)}})
    return {'id': tid, 'kind': 'table', 'anchor': {'byte_start': s, 'byte_end_exclusive': e}, 'source_table': {'tag_start': s, 'claims': 1}, 'cells': cells}


def unit(raw, uid, text, k=0, kind='text'):
    return {'id': uid, 'kind': kind, 'text': text, 'anchor': at(raw, text, k)}


def search(raw, text, n, own=None):
    """A search piece listing every printed place of `text`; `own` = the governing one (None: no governing information)."""
    p = {'text': text, 'byte_ranges': [[at(raw, text, k)['byte_start'], at(raw, text, k)['byte_end_exclusive']] for k in range(n)]}
    if own is not None: p['governing'] = [[at(raw, text, own)['byte_start'], at(raw, text, own)['byte_end_exclusive']]]
    return p


def outcome(raw, route, value, field, fval, support, alternatives=None):
    """The complete row of `field` for the value cell printing `value` in the last table: (verdict, reason, detail)."""
    tb = [u for u in route if u['kind'] == 'table'][-1]; v = [c for c in tb['cells'] if c['text'] == value][-1]
    t = {'key_id': 'syn/A', 'file_id': 'syn/a.htm', 'format': 'cell/htm', 'type': 'cell', 'split': 'development', 'anchor': v['anchor'], 'table_anchor': tb['anchor'],
         'alternatives': alternatives or {}, 'excluded': set(), 'support': support, 'fields': {'printed_value': value, 'display_value': value, field: fval}}
    g = grade.Grader(t, grade.RouteFile({'file_id': 'syn/a.htm', 'units': copy.deepcopy(route)}, raw)); g.grade_cell()
    return next((r['verdict'], r.get('reason'), r.get('detail')) for r in g.rows if r['check'] == field)


def without(route, tid, r, c):
    out = copy.deepcopy(route); tb = next(u for u in out if u['id'] == tid); tb['cells'] = [x for x in tb['cells'] if (x['r'], x['c']) != (r, c)]
    return out


PASS = ('pass', None, None)

# stacked blocks: the same heading over each block
STACK = b'<table><tr><td>Name</td><td>Type</td><td>2026</td></tr><tr><td>Ann</td><td>Salary</td><td>10</td></tr><tr><td>Name</td><td>Type</td><td>2026</td></tr><tr><td>Bo</td><td>Salary</td><td>9</td></tr></table>'
STACK_T = table(STACK, 't', 0, [['Name', 'Type', '2026'], ['Ann', 'Salary', '10'], ['Name', 'Type', '2026'], ['Bo', 'Salary', '9']])
CORNER = b'<table><tr><td>(in millions)</td><td>2026</td></tr><tr><td>Revenue</td><td>10</td></tr><tr><td>(in millions)</td><td>2025</td></tr><tr><td>Revenue</td><td>9</td></tr></table>'
CORNER_T = table(CORNER, 't', 0, [['(in millions)', '2026'], ['Revenue', '10'], ['(in millions)', '2025'], ['Revenue', '9']])
LEAD = 'The following table presents results:'
LEADS = (b'<p>' + LEAD.encode() + b'</p><table><tr><td>Crop</td><td>12</td></tr></table><p>' + LEAD.encode() + b'</p><table><tr><td>Tools</td><td>9</td></tr></table>')
LEADS_R = [unit(LEADS, 'l1', LEAD, 0), table(LEADS, 'a', 0, [['Crop', '12']]), unit(LEADS, 'l2', LEAD, 1), table(LEADS, 'b', 1, [['Tools', '9']])]
H = 'Item 2. Results'
SECT = b'<p>Contents</p><p>' + H.encode() + b'</p><p>Body</p><h2>' + H.encode() + b'</h2><table><tr><td>Revenue</td><td>9</td></tr></table>'
SECT_R = [unit(SECT, 'c', 'Contents'), unit(SECT, 'toc', H, 0), unit(SECT, 'b', 'Body'), unit(SECT, 'h', H, 1, 'heading'), table(SECT, 't', 0, [['Revenue', '9']])]
LEVELS = b'<table><tr><td></td><td>Three Months</td></tr><tr><td>Name</td><td>2026</td></tr><tr><td>Ann</td><td>10</td></tr><tr><td></td><td>Three Months</td></tr><tr><td>Name</td><td>2026</td></tr><tr><td>Bo</td><td>9</td></tr></table>'
LEVELS_T = table(LEVELS, 't', 0, [['', 'Three Months'], ['Name', '2026'], ['Ann', '10'], ['', 'Three Months'], ['Name', '2026'], ['Bo', '9']])
U = '(in millions)'
UNITS = b'<p>' + U.encode() + b'</p><table><tr><td>Revenue</td><td>12</td></tr></table><p>' + U.encode() + b'</p><table><tr><td>Costs</td><td>9</td></tr></table>'
UNITS_R = [unit(UNITS, 'u1', U, 0), table(UNITS, 'a', 0, [['Revenue', '12']]), unit(UNITS, 'u2', U, 1), table(UNITS, 'b', 1, [['Costs', '9']])]


class GoverningAssociation(unittest.TestCase):
    def test_row_context_header_at_its_governing_place(self):
        ctx = [{'text': 'Salary', 'header': 'Type'}]; gov = {'row_context': {'pieces': [search(STACK, 'Type', 2, 1)]}}
        self.assertEqual(outcome(STACK, [STACK_T], '9', 'row_context', ctx, gov), PASS)
        self.assertEqual(outcome(STACK, [without([STACK_T], 't', 2, 1)[0]], '9', 'row_context', ctx, gov), ('fail', 'header', 'Type'))  # own block's header lost; the other block's is that block's
        moved = copy.deepcopy(STACK_T); next(c for c in moved['cells'] if (c['r'], c['c']) == (2, 1))['c'] = 0  # own header printed over another column
        self.assertEqual(outcome(STACK, [moved], '9', 'row_context', ctx, gov)[0], 'fail')

    def test_header_path_at_its_governing_place(self):
        gov = {'header_path': {'pieces': [search(STACK, '2026', 2, 1)]}}
        self.assertEqual(outcome(STACK, [STACK_T], '9', 'header_path', ['2026'], gov), PASS)
        self.assertEqual(outcome(STACK, [without([STACK_T], 't', 2, 2)[0]], '9', 'header_path', ['2026'], gov), ('fail', 'missing', None))
        moved = copy.deepcopy(STACK_T); next(c for c in moved['cells'] if (c['r'], c['c']) == (2, 2))['c'] = 1  # own heading over another column
        self.assertEqual(outcome(STACK, [moved], '9', 'header_path', ['2026'], gov), ('fail', 'column', None))
        two = {'header_path': {'pieces': [search(LEVELS, 'Three Months', 2, 1), search(LEVELS, '2026', 2, 1)]}}  # two pieces, each at its own block's governing place
        self.assertEqual(outcome(LEVELS, [LEVELS_T], '9', 'header_path', ['Three Months', '2026'], two), PASS)
        self.assertNotEqual(outcome(LEVELS, [without([LEVELS_T], 't', 3, 1)[0]], '9', 'header_path', ['Three Months', '2026'], two)[0], 'pass')  # one governing piece lost

    def test_corner_text_at_its_governing_place(self):
        gov = {'corner_text': {'pieces': [search(CORNER, U, 2, 1)]}}
        self.assertEqual(outcome(CORNER, [CORNER_T], '9', 'corner_text', U, gov), PASS)
        self.assertEqual(outcome(CORNER, [without([CORNER_T], 't', 2, 0)[0]], '9', 'corner_text', U, gov), ('fail', 'missing', None))

    def test_lead_in_at_its_governing_place(self):
        gov = {'lead_in': {'pieces': [search(LEADS, LEAD, 2, 1)]}}
        self.assertEqual(outcome(LEADS, LEADS_R, '9', 'lead_in', LEAD, gov), PASS)
        self.assertEqual(outcome(LEADS, [u for u in LEADS_R if u['id'] != 'l2'], '9', 'lead_in', LEAD, gov), ('fail', 'missing', None))  # the earlier table's identical sentence is that table's
        after = [u for u in LEADS_R if u['id'] != 'l2'] + [LEADS_R[2]]  # the own lead-in listed after its table
        self.assertEqual(outcome(LEADS, after, '9', 'lead_in', LEAD, gov)[0], 'fail')

    def test_section_path_at_its_governing_place(self):
        gov = {'section_path': {'pieces': [search(SECT, H, 2, 1)]}}
        self.assertEqual(outcome(SECT, SECT_R, '9', 'section_path', [H], gov), PASS)
        self.assertNotEqual(outcome(SECT, [u for u in SECT_R if u['id'] != 'h'], '9', 'section_path', [H], gov)[0], 'pass')  # the body heading lost; a contents entry contains nothing

    def test_unit_printed_at_its_governing_place(self):
        gov = {'unit_printed': {'pieces': [search(UNITS, U, 2, 1)]}}
        self.assertEqual(outcome(UNITS, UNITS_R, '9', 'unit_printed', U, gov), PASS)
        self.assertEqual(outcome(UNITS, [u for u in UNITS_R if u['id'] != 'u2'], '9', 'unit_printed', U, gov), ('fail', 'missing', None))
        alts = {'unit_printed': [U, '(in thousands)']}; per_alt = {'unit_printed#0': {'pieces': [search(UNITS, U, 2, 1)]}}  # an accepted alternative carries its own governing support
        self.assertEqual(outcome(UNITS, UNITS_R, '9', 'unit_printed', U, per_alt, alts), PASS)
        self.assertEqual(outcome(UNITS, [u for u in UNITS_R if u['id'] != 'u2'], '9', 'unit_printed', U, per_alt, alts)[0], 'fail')

    def test_the_listing_order_does_not_decide(self):  # permutation of the listed places; the governing one decides
        for order in ((0, 1), (1, 0)):
            p = search(UNITS, U, 2, 1); p['byte_ranges'] = [p['byte_ranges'][i] for i in order]
            self.assertEqual(outcome(UNITS, UNITS_R, '9', 'unit_printed', U, {'unit_printed': {'pieces': [p]}}), PASS)
            self.assertEqual(outcome(UNITS, [u for u in UNITS_R if u['id'] != 'u2'], '9', 'unit_printed', U, {'unit_printed': {'pieces': [p]}}), ('fail', 'missing', None))

    def test_an_own_lead_in_the_route_moves_before_another_table(self):  # route mutation: the own place kept, listed before the earlier table (lead_in's existing source-order rule)
        moved = [LEADS_R[2], LEADS_R[0], LEADS_R[1], LEADS_R[3]]
        self.assertEqual(outcome(LEADS, moved, '9', 'lead_in', LEAD, {'lead_in': {'pieces': [search(LEADS, LEAD, 2, 1)]}}), ('fail', 'placement', None))

    def test_absent_governing_and_plain_anchors_keep_todays_reading(self):  # no place is guessed: these keep the false acceptance as a named limitation
        self.assertEqual(outcome(UNITS, [u for u in UNITS_R if u['id'] != 'u2'], '9', 'unit_printed', U, {'unit_printed': {'pieces': [search(UNITS, U, 2)]}}), PASS)
        self.assertEqual(outcome(UNITS, [u for u in UNITS_R if u['id'] != 'u2'], '9', 'unit_printed', U, {'unit_printed': {'anchors': [at(UNITS, U, 0), at(UNITS, U, 1)]}}), PASS)
        self.assertEqual(outcome(LEADS, [u for u in LEADS_R if u['id'] != 'l2'], '9', 'lead_in', LEAD, {'lead_in': {'anchors': [at(LEADS, LEAD, 0), at(LEADS, LEAD, 1)]}}), PASS)
        self.assertEqual(outcome(STACK, [without([STACK_T], 't', 2, 2)[0]], '9', 'header_path', ['2026'], {'header_path': {'anchors': [at(STACK, '2026', 0), at(STACK, '2026', 1)]}}), PASS)

    def test_another_copys_own_duties_stay_with_their_owners(self):
        gov = {'unit_printed': {'pieces': [search(UNITS, U, 2, 1)]}}
        misread = copy.deepcopy(UNITS_R); misread[0]['text'] = '(in billions)'  # the earlier table's copy misread: this table's unit line is kept
        self.assertEqual(outcome(UNITS, misread, '9', 'unit_printed', U, gov), PASS)
        self.assertEqual(grade.gates_for_file(grade.RouteFile({'file_id': 'syn/a.htm', 'units': misread}, UNITS), 'OK')['dishonest'], 1)  # reported, never silent
        self.assertEqual(grade.gates_for_file(grade.RouteFile({'file_id': 'syn/a.htm', 'units': copy.deepcopy(UNITS_R)}, UNITS), 'OK')['dishonest'], 0)
        struck = copy.deepcopy(CORNER_T); next(c for c in struck['cells'] if (c['r'], c['c']) == (2, 0))['struck'] = [U]  # a strike the source does not print, on the own corner
        self.assertEqual(outcome(CORNER, [struck], '9', 'corner_text', U, {'corner_text': {'pieces': [search(CORNER, U, 2, 1)]}}), ('fail', 'struck', None))


if __name__ == '__main__':
    unittest.main()
