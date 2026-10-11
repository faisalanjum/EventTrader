"""Table row order in byte frames is unproved (table-order-conservative-20261011). A table's own header group may be written after its body and a
footer group before it, yet both are drawn in their own place; frozen byte offsets therefore prove neither that a route's cross-row order is right
(they may agree with a corrupted route) nor that it is wrong (they may disagree with a faithful one). Every order-dependent table duty - in_order's
callers, both periods checks and the key-anchored header guard - is UNRESOLVED (`source_order`) there: incomplete, never PASS. Page boxes are printed
places and still decide; content, column, anchor, missing-carrier and route-structure contradictions still FAIL. Semantic truths (faithful = correct,
corrupted = wrong) come from the invented sources below, written before the code; the HTML routes are valid fixtures equal in shape to the native
routes recorded in table_order_shared_design_v1 (the header group listed first, the footer group last, for either serialization). The PDF class is
synthetic page boxes for the grader, not a PDF conversion."""
import hashlib
import unittest

from benchmarks.prepare.grader import grade

HEAD = (b'<thead><tr><th id="lead" colspan="2">Revenue by region</th></tr><tr><th id="sect" colspan="2">Operating segments</th></tr>'
        b'<tr><th id="period">Three months ended</th><th id="mark">(1)</th></tr><tr><th id="corner">Region</th><th id="y24">2024</th></tr>'
        b'<tr><th id="blank"></th><th id="unit">(in millions)</th></tr></thead>')
BODY = b'<tbody><tr><td id="north">North</td><td id="v1">10</td></tr></tbody>'
FHEAD = b'<thead><tr><th id="corner">Region</th><th id="y24">2024(1)</th></tr></thead>'
FOOT = b'<tfoot><tr><td id="note" colspan="2">(1) Excludes discontinued operations</td></tr></tfoot>'
SOURCES = {'ordinary': HEAD + BODY, 'late_thead': BODY + HEAD, 'late_tfoot': FHEAD + BODY + FOOT, 'early_tfoot': FHEAD + FOOT + BODY}
DRAWN = {'group': [('lead', 'th', 2), ('sect', 'th', 2), ('period', 'th', 1, 'mark', 'th', 1), ('corner', 'th', 1, 'y24', 'th', 1), ('blank', 'th', 1, 'unit', 'th', 1), ('north', 'td', 1, 'v1', 'td', 1)],
         'foot': [('corner', 'th', 1, 'y24', 'th', 1), ('north', 'td', 1, 'v1', 'td', 1), ('note', 'td', 2)]}  # each source's rows as drawn (thead first, tfoot last)
TEXT = {'lead': 'Revenue by region', 'sect': 'Operating segments', 'period': 'Three months ended', 'mark': '(1)', 'corner': 'Region', 'y24': '2024', 'blank': '', 'unit': '(in millions)',
        'north': 'North', 'v1': '10', 'note': '(1) Excludes discontinued operations'}
U = ('unresolved', 'source_order')


def page(name):
    return b'<!doctype html><html><body><table id="t">' + SOURCES[name] + b'</table></body></html>\n'


def at(raw, tag, name):
    s = raw.index(('<%s id="%s"' % (tag, name)).encode()); return {'byte_start': s, 'byte_end_exclusive': raw.index(('</%s>' % tag).encode(), s) + len(tag) + 3}


class TableOrder(unittest.TestCase):
    def route(self, raw, rows, order=None, edit=None):  # a valid route of the drawn rows, listed in `order` (default: as drawn)
        cells, text = [], dict(TEXT, y24='2024(1)') if b'tfoot' in raw else TEXT
        for r, i in enumerate(order or range(len(rows))):
            row, c = rows[i], 0
            for j in range(0, len(row), 3):
                name, tag, span = row[j:j + 3]
                cells.append({'r': r, 'c': c, 'rs': 1, 'cs': span, 'text': text[name], 'anchor': at(raw, tag, name), 'header': tag == 'th', 'name': name}); c += span
        for x in cells:
            if edit and x['name'] in edit: x.update(edit[x['name']])
        return {'file_id': 'invented/order.html', 'sha256': hashlib.sha256(raw).hexdigest(), 'status': 'OK', 'units': [{'id': 't', 'kind': 'table', 'anchor': at(raw, 'table', 't'), 'cells': cells}]}

    def duty(self, raw, route, field, value, ids=(), key_anchor=None):  # one key, the whole native path: its own row (verdict, reason) and verdict_of
        tag = lambda n: 'td' if n in ('north', 'v1', 'note') else 'th'
        key = {'key_id': 'invented/' + field, 'file_id': route['file_id'], 'split': 'public', 'type': 'cell', 'format': 'cell/html', 'fields': {'printed_value': '10', field: value},
               'alternatives': {}, 'anchor': at(raw, 'td', 'v1'), 'table_anchor': at(raw, 'table', 't'),
               'support': {field: {'anchors': [key_anchor or at(raw, tag(n), n) for n in ids]}} if ids else {}, 'excluded': set()}
        g = grade.Grader(key, grade.RouteFile(route, raw, 'html')); g.grade_cell()
        return next(((r['verdict'], r['reason']) for r in g.rows if r['check'] == field), None), grade.verdict_of(g.rows)

    def group(self, raw, route):  # the header-group duties of the value 10
        note = lambda r: r
        return {'header_path': self.duty(raw, route, 'header_path', ['2024'], ['y24']), 'corner_text': self.duty(raw, route, 'corner_text', 'Region', ['corner']),
                'unit_printed': self.duty(raw, route, 'unit_printed', '(in millions)', ['unit']), 'segment_or_basis': self.duty(raw, route, 'segment_or_basis', '(in millions)', ['unit']),
                'lead_in': self.duty(raw, route, 'lead_in', 'Revenue by region', ['lead']), 'section_path': self.duty(raw, route, 'section_path', ['Operating segments'], ['sect']),
                'periods': self.duty(raw, route, 'periods', [{'parts': [{'text': 'Three months ended', 'anchor': at(raw, 'th', 'period')}]}]),
                'row_context': self.duty(raw, route, 'row_context', [{'text': 'North', 'header': 'Region'}], ['corner'])}

    def footnote(self, raw, route):
        return self.duty(raw, route, 'footnote_markers', [{'marker_text': '(1)', 'anchor': at(raw, 'th', 'y24'), 'note_anchor': at(raw, 'td', 'note'), 'note_text': TEXT['note']}])

    def test_faithful_header_groups_are_correct_but_unproved_in_either_serialization(self):
        for name in ('ordinary', 'late_thead'):
            raw = page(name); got = self.group(raw, self.route(raw, DRAWN['group']))
            for field in ('header_path', 'corner_text', 'unit_printed', 'segment_or_basis', 'lead_in', 'section_path', 'periods'):
                with self.subTest(source=name, duty=field):
                    self.assertEqual(got[field][0], U); self.assertEqual(got[field][1], 'UNRESOLVED')  # never PASS, never blamed: bytes prove no drawn order
            with self.subTest(source=name, duty='row_context'):
                self.assertEqual(got['row_context'], (('pass', None), 'PASS'))  # same-row relation: the value's own row

    def test_a_corrupted_header_group_is_never_a_pass_in_either_serialization(self):  # the body row listed first: the header group below the value
        for name in ('ordinary', 'late_thead'):  # late_thead: the corruption agrees with the bytes (Root's counterexample)
            raw = page(name); got = self.group(raw, self.route(raw, DRAWN['group'], order=[5, 0, 1, 2, 3, 4]))
            for field, (verdict, overall) in got.items():
                with self.subTest(source=name, duty=field):
                    self.assertNotEqual(verdict[0], 'pass'); self.assertNotEqual(overall, 'PASS')
            for field in ('header_path', 'lead_in', 'section_path', 'periods', 'row_context'):  # route structure: the label is listed after the value
                with self.subTest(source=name, structure=field):
                    self.assertEqual(got[field][0][0], 'fail')

    def test_footer_note_rows_follow_the_same_rule(self):
        for name in ('late_tfoot', 'early_tfoot'):
            raw = page(name)
            with self.subTest(source=name, route='faithful'):
                self.assertEqual(self.footnote(raw, self.route(raw, DRAWN['foot'])), (U, 'UNRESOLVED'))
            with self.subTest(source=name, route='note row listed above the value'):  # early_tfoot: the corruption agrees with the bytes (the mirror case)
                (verdict, _), overall = self.footnote(raw, self.route(raw, DRAWN['foot'], order=[0, 2, 1]))
                self.assertNotEqual(verdict, 'pass'); self.assertNotEqual(overall, 'PASS')

    def test_content_column_anchor_and_missing_carrier_errors_still_fail(self):
        raw = page('ordinary'); rows = DRAWN['group']
        self.assertEqual(self.duty(raw, self.route(raw, rows, edit={'y24': {'text': '2023'}}), 'header_path', ['2024'], ['y24'])[1], 'FAIL')  # wrong text
        self.assertEqual(self.duty(raw, self.route(raw, rows, edit={'y24': {'c': 0}}), 'header_path', ['2024'], ['y24'])[0], ('fail', 'column'))  # wrong column
        self.assertEqual(self.duty(raw, self.route(raw, rows, edit={'y24': {'text': ''}}), 'header_path', ['2024'], ['y24'])[1], 'FAIL')  # missing carrier text
        self.assertEqual(self.duty(raw, self.route(raw, rows), 'header_path', ['2024'], ['y24'], key_anchor=at(raw, 'th', 'mark'))[1], 'FAIL')  # another source occurrence
        self.assertEqual(self.duty(raw, self.route(raw, rows, edit={'corner': {'text': 'Area'}}), 'corner_text', 'Region', ['corner'])[1], 'FAIL')  # corner text changed
        self.assertEqual(self.duty(raw, self.route(raw, rows, edit={'unit': {'text': '(in thousands)'}}), 'unit_printed', '(in millions)', ['unit'])[1], 'FAIL')  # unit text changed

    def test_a_label_moved_into_the_value_row_is_caught_by_the_header_duty(self):  # same-row relation: no byte order decides it
        raw = page('ordinary'); route = self.route(raw, DRAWN['group'], edit={'y24': {'r': 5, 'c': 2}})
        self.assertEqual(self.duty(raw, route, 'header_path', ['2024'], ['y24'])[1], 'FAIL')


class PageBoxOrder(unittest.TestCase):  # synthetic page boxes for the grader, no PDF conversion: printed places decide
    RAW = b'%PDF-1.4 synthetic grader boxes'

    def graded(self, field, value, label_y, value_y, label_row):
        box = lambda y, x: {'page': 1, 'region': [x, y, x + 40, y + 10]}
        rows = {label_row: [('Region', box(label_y, 10)), ('2024', box(label_y, 60))], 1 - label_row: [('North', box(value_y, 10)), ('10', box(value_y, 60))]}
        cells = [{'r': r, 'c': c, 'rs': 1, 'cs': 1, 'text': t, 'anchor': a} for r, row in rows.items() for c, (t, a) in enumerate(row)]
        route = {'file_id': 'invented/page.pdf', 'status': 'OK', 'units': [{'id': 't', 'kind': 'table', 'anchor': {'page': 1, 'region': [0, 0, 200, 300]}, 'cells': cells}]}
        anchor = box(label_y, 60 if field == 'header_path' else 10)
        key = {'key_id': 'invented/' + field, 'file_id': route['file_id'], 'split': 'public', 'type': 'cell', 'format': 'cell/pdf', 'fields': {'printed_value': '10', field: value},
               'alternatives': {}, 'anchor': box(value_y, 60), 'table_anchor': {'page': 1, 'region': [0, 0, 200, 300]}, 'support': {field: {'anchors': [anchor]}}, 'excluded': set()}
        g = grade.Grader(key, grade.RouteFile(route, self.RAW, 'pdf')); g.grade_cell()
        return next(((r['verdict'], r['reason']) for r in g.rows if r['check'] == field), None), grade.verdict_of(g.rows)

    def test_printed_above_and_listed_above_passes(self):
        self.assertEqual(self.graded('header_path', ['2024'], 50, 100, 0), (('pass', None), 'PASS'))
        self.assertEqual(self.graded('corner_text', 'Region', 50, 100, 0), (('pass', None), 'PASS'))

    def test_printed_below_and_listed_above_fails(self):
        self.assertEqual(self.graded('header_path', ['2024'], 200, 100, 0)[1], 'FAIL')
        self.assertEqual(self.graded('corner_text', 'Region', 200, 100, 0)[1], 'FAIL')


if __name__ == '__main__':
    unittest.main()
