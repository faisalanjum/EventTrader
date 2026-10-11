"""A side check of an order-open reading stays open: never PASS, never dropped (table-order-conservative v4b). The footer sources and valid
fixture routes are test_table_order_conservative's; truth: the note is linked (correct) but its row order is byte order only, unproved."""
import unittest

from benchmarks.prepare.grader import grade
from benchmarks.prepare.grader.tests import test_table_order_conservative as base  # the module, not its TestCase: its tests are not collected twice (run 1 imported the class)


class SideRows(unittest.TestCase):
    def test_a_note_link_of_an_order_open_reading_is_kept_open(self):
        build = base.TableOrder('test_footer_note_rows_follow_the_same_rule')  # its route builder only
        for name in ('late_tfoot', 'early_tfoot'):  # bytes agree / bytes disagree with the drawn order
            with self.subTest(source=name):
                raw = base.page(name); route = build.route(raw, base.DRAWN['foot'])
                key = {'key_id': 'invented/note', 'file_id': route['file_id'], 'split': 'public', 'type': 'cell', 'format': 'cell/html',
                       'fields': {'printed_value': '10', 'footnote_markers': [{'marker_text': '(1)', 'anchor': base.at(raw, 'th', 'y24'), 'note_anchor': base.at(raw, 'td', 'note'), 'note_text': base.TEXT['note']}]},
                       'alternatives': {}, 'anchor': base.at(raw, 'td', 'v1'), 'table_anchor': base.at(raw, 'table', 't'), 'support': {}, 'excluded': set()}
                g = grade.Grader(key, grade.RouteFile(route, raw, 'html')); g.grade_cell(); rows = {r['check']: (r['verdict'], r['reason']) for r in g.rows}
                self.assertEqual(rows['footnote_markers'], ('unresolved', 'source_order'))
                self.assertEqual(rows.get('note_linked'), ('unresolved', 'source_order'))  # kept, and open like its reading


class Alternatives(unittest.TestCase):  # accepted alternatives in either order: an order-open one never turns into PASS, and a wrong one never into the verdict
    def test_an_open_alternative_beside_a_wrong_one_is_open_in_either_order(self):
        build = base.TableOrder('test_footer_note_rows_follow_the_same_rule'); raw = base.page('ordinary'); route = build.route(raw, base.DRAWN['group'])
        for alts in ([['2023'], ['2024']], [['2024'], ['2023']]):  # 2023: printed nowhere (wrong); 2024: correct, its row order byte-only
            with self.subTest(alternatives=alts):
                key = {'key_id': 'invented/alt', 'file_id': route['file_id'], 'split': 'public', 'type': 'cell', 'format': 'cell/html', 'fields': {'printed_value': '10', 'header_path': alts[0]},
                       'alternatives': {'header_path': alts}, 'anchor': base.at(raw, 'td', 'v1'), 'table_anchor': base.at(raw, 'table', 't'),
                       'support': {'header_path': {'anchors': [base.at(raw, 'th', 'y24')]}}, 'excluded': set()}
                g = grade.Grader(key, grade.RouteFile(route, raw, 'html')); g.grade_cell()
                self.assertEqual(next((r['verdict'], r['reason']) for r in g.rows if r['check'] == 'header_path'), ('unresolved', 'source_order'))
                self.assertEqual(grade.verdict_of(g.rows), 'UNRESOLVED')

    def test_a_proved_contradiction_beside_an_unrelated_open_order_still_fails(self):
        build = base.TableOrder('test_footer_note_rows_follow_the_same_rule'); raw = base.page('ordinary')
        route = build.route(raw, base.DRAWN['group'], edit={'y24': {'c': 0}})  # 2024 listed over the other column; the corner row is order-open too
        key = {'key_id': 'invented/col', 'file_id': route['file_id'], 'split': 'public', 'type': 'cell', 'format': 'cell/html', 'fields': {'printed_value': '10', 'header_path': ['2024'], 'corner_text': 'Region'},
               'alternatives': {}, 'anchor': base.at(raw, 'td', 'v1'), 'table_anchor': base.at(raw, 'table', 't'),
               'support': {'header_path': {'anchors': [base.at(raw, 'th', 'y24')]}, 'corner_text': {'anchors': [base.at(raw, 'th', 'corner')]}}, 'excluded': set()}
        g = grade.Grader(key, grade.RouteFile(route, raw, 'html')); g.grade_cell(); rows = {r['check']: (r['verdict'], r['reason']) for r in g.rows}
        self.assertEqual(rows['header_path'], ('fail', 'column')); self.assertEqual(grade.verdict_of(g.rows), 'FAIL')


if __name__ == '__main__':
    unittest.main()
