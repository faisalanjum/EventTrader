# Ported to the normal suite from context_candidate/tests_snapshot_20261022T0237_final/test_duplicate_marks.py (sha256 7af68c5ebe1c14032ea993f854fed8e31cb4c68afd58734cfe7c8a8980064dd7). Test bodies unchanged; mechanical change only:
# fixtures from this directory's cases.py instead of runpy (BUTTON from test_context_states.py unless cases.py defines it).
"""Duplicated run marks (Root CONTEXT_OBSERVED_CONTROL_CONTRACT_REVIEW_20261022, Range follow-up; invented public fixture): the parent inserts the selected
child twice, so every mark of ours stands twice in the page. The shared run-binding rule makes a mark the page holds twice bind nothing for every
reader (cells, gaps, symbol runs, links, pictures), so the whole initial route is not certified before any reading contributes; the activations stay
refused by control identity. Clean parent: unchanged.
Run: CANDIDATE_RUNTIME=<runtime> python -I -B test_duplicate_marks.py"""
import unittest
from pathlib import Path
from . import cases; g = dict(vars(cases)); g.setdefault('BUTTON', 'context: 1 declared event handler(s) outside the supported link path (not activated)')  # BUTTON: test_context_states.py's exact constant unless cases.py defines it
rep, run, ANON, PARENT_UI, controls, activations = g['rep'], g['run'], g['ANON'], g['PARENT_UI'], g['controls'], g['activations']
TWICE = rep(PARENT_UI, b"jQuery('#report-host').empty().append(data);", b"jQuery('#report-host').empty().append(data).append(data);")


class DuplicateMarks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def test_a_doubly_inserted_child_is_not_certified(self):
        res = run(self.browser, ANON, parent=TWICE); i = res['initial']
        self.assertEqual(i['status'], 'PARTIAL'); self.assertIn('without a browser verdict', i['error']); self.assertIn('geometry is unproved', i['error'])
        self.assertEqual([activations(res, s)[0]['status'] for s in controls(ANON)], ['refused', 'refused'])

    def test_clean_parent_unchanged(self):
        res = run(self.browser, ANON); self.assertEqual((res['initial']['status'], res['initial'].get('error')), ('PARTIAL', g['BUTTON']))

if __name__ == '__main__':
    unittest.main()
