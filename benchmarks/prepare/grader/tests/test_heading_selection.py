"""Heading selection by earliest completion (accepted heading-selection v4): every level takes the earliest-completing single-level printing (exact, pieces,
run-in), one printed occurrence per level, in order, before the value; an uncertain join stays open; a joined heading (E9) never completes two levels by
itself - it leaves the target unresolved for original-source review. Cases: the accepted public controls' own built sources, keys and routes
(fixtures/heading_selection/cases.json): E9 v4 role controls (14), class forms (18), uncertainty (3), native probe (4). `expected` is the automatic
answer; `truth` the original fidelity answer, kept apart: an automatic answer may only fall short of the truth as `unresolved`, never contradict it."""
import copy
import json
from pathlib import Path
import unittest

from benchmarks.prepare.grader import grade

CASES = json.loads((Path(__file__).with_name('fixtures') / 'heading_selection' / 'cases.json').read_text())


def section_path(case):
    key = copy.deepcopy(case['key']); key['excluded'] = set(key.get('excluded') or [])
    g = grade.Grader(key, grade.RouteFile(copy.deepcopy(case['route']), case['raw'].encode('utf-8'), 'html')); g.grade_cell()
    return next(r for r in g.rows if r['check'] == 'section_path')


class HeadingSelectionTests(unittest.TestCase):
    def test_every_case_gives_its_automatic_answer_and_never_contradicts_the_truth(self):
        for name, case in sorted(CASES.items()):
            with self.subTest(name):
                got = section_path(case)['verdict']
                self.assertEqual(got, case['expected'])
                self.assertIn(got, (case['truth'], 'unresolved'))

    def test_the_review_duties_are_exactly_the_joined_heading_cases(self):
        owed = sorted(n for n, c in CASES.items() if c['expected'] != c['truth'])
        self.assertEqual(owed, ['e9v4/A_neg_late', 'e9v4/A_neg_missing', 'e9v4/B_joined_faithful', 'e9v4/B_joined_late', 'e9v4/B_joined_missing'])
        for n in owed: self.assertEqual(section_path(CASES[n])['reason'], 'joined_levels', n)


if __name__ == '__main__':
    unittest.main()
