"""Printed places decide row order for every order-dependent table duty (table-order-conservative v2 prerequisites). Synthetic page boxes for the
grader, not a PDF conversion: one table on page 1, its rows printed top to bottom at the stated heights. Truths from the boxes, written before the
run: a label printed above its value and listed above it, a note printed below and listed below - PASS; the same label printed on the other side of
the value than the route lists it - FAIL. Same box geometry for every duty; only the duty and the moved row change."""
import unittest

from benchmarks.prepare.grader import grade

ROWS = [('lead', [('Revenue by region', 2)]), ('sect', [('Operating segments', 2)]), ('period', [('Three months ended', 1), ('', 1)]),
        ('head', [('Region', 1), ('2024', 1)]), ('unit', [('', 1), ('(in millions)', 1)]), ('value', [('North', 1), ('10', 1)]), ('note', [('(1) Excludes discontinued operations', 2)])]
RAW = b'%PDF-1.4 synthetic grader boxes'


def box(y, x, w=40):
    return {'page': 1, 'region': [x, y, x + w, y + 10]}


class PageBoxes(unittest.TestCase):
    def graded(self, field, value, moved=None, y=None):  # rows listed in ROWS order; `moved`: that row printed at height `y` instead of its own
        cells, where = [], {}
        for r, (name, row) in enumerate(ROWS):
            top = (y if name == moved else 20 * r + 10); x = 10
            for c, (text, span) in enumerate(row):
                text = '2024(1)' if field == 'footnote_markers' and text == '2024' else text  # the note's mark printed on its header (run 1 omitted it: a fixture error, marker_missing on both graders)
                a = box(top, x, 40 * span + (span - 1) * 10); cells.append({'r': r, 'c': sum(s for _, s in row[:c]), 'rs': 1, 'cs': span, 'text': text, 'anchor': a}); where[(name, c)] = a; x += 50 * span
        route = {'file_id': 'invented/page.pdf', 'status': 'OK', 'units': [{'id': 't', 'kind': 'table', 'anchor': {'page': 1, 'region': [0, 0, 300, 400]}, 'cells': cells}]}
        anchors = {'header_path': [where[('head', 1)]], 'corner_text': [where[('head', 0)]], 'unit_printed': [where[('unit', 1)]], 'segment_or_basis': [where[('unit', 1)]],
                   'lead_in': [where[('lead', 0)]], 'section_path': [where[('sect', 0)]]}.get(field)
        if field == 'periods': value = [{'parts': [{'text': 'Three months ended', 'anchor': where[('period', 0)]}]}]
        if field == 'footnote_markers': value = [{'marker_text': '(1)', 'anchor': where[('head', 1)], 'note_anchor': where[('note', 0)], 'note_text': '(1) Excludes discontinued operations'}]
        key = {'key_id': 'invented/' + field, 'file_id': route['file_id'], 'split': 'public', 'type': 'cell', 'format': 'cell/pdf', 'fields': {'printed_value': '10', field: value},
               'alternatives': {}, 'anchor': where[('value', 1)], 'table_anchor': {'page': 1, 'region': [0, 0, 300, 400]}, 'support': {field: {'anchors': anchors}} if anchors else {}, 'excluded': set()}
        g = grade.Grader(key, grade.RouteFile(route, RAW, 'pdf')); g.grade_cell()
        return next(((r['verdict'], r['reason']) for r in g.rows if r['check'] == field), None), grade.verdict_of(g.rows)

    DUTIES = {'header_path': (['2024'], 'head'), 'corner_text': ('Region', 'head'), 'unit_printed': ('(in millions)', 'unit'), 'segment_or_basis': ('(in millions)', 'unit'),
              'lead_in': ('Revenue by region', 'lead'), 'section_path': (['Operating segments'], 'sect'), 'periods': (None, 'period')}

    def test_labels_printed_above_and_listed_above_pass(self):
        for field, (value, _) in self.DUTIES.items():
            with self.subTest(duty=field):
                self.assertEqual(self.graded(field, value), (('pass', None), 'PASS'))

    def test_labels_printed_below_but_listed_above_fail(self):
        for field, (value, row) in self.DUTIES.items():
            with self.subTest(duty=field):
                (verdict, _), overall = self.graded(field, value, moved=row, y=300)
                self.assertEqual((verdict, overall), ('fail', 'FAIL'))

    def test_a_note_printed_below_passes_and_one_printed_above_but_listed_below_fails(self):
        self.assertEqual(self.graded('footnote_markers', None), (('pass', None), 'PASS'))
        (verdict, _), overall = self.graded('footnote_markers', None, moved='note', y=0)
        self.assertEqual((verdict, overall), ('fail', 'FAIL'))


if __name__ == '__main__':
    unittest.main()
