# Ported to the normal suite from context_candidate/tests/test_selection_custody.py (sha256 ec2f828d76ff2f4cbe103d0cec048e4a3868c69f5b941a4ab2458b65ff6cc33c). Only test_refused_navigation_is_listed_apart (the other four are already in test_selection_custody.py) with its helper and class setup, unchanged; mechanical change only: fixtures from
# this directory's cases.py (byte-identical fixture files, same PNG, same run() path when context is present) instead of runpy(test_context_states.py).
"""Response custody on the selection side (Root CONTEXT_RESPONSE_BOUNDARY_INVENTORY_20261021 items 2 and 5; invented public fixture): the selection's
initial parent and its measured target are served by the Source's own observed-response rule (Source.observation). A changed recorded hash fails the
selection (parent: AcquisitionError before navigation, never retried) or refuses the target there; a measured body must be exactly the recorded
response plus our comments; the healthy evidence still selects.
Run: CANDIDATE_RUNTIME=<runtime> python -I -B test_selection_custody.py"""
import unittest
from pathlib import Path
from . import cases; g = vars(cases)
sg, evidence, ANON, TARGET = g['sg'], g['evidence'], g['ANON'], g['TARGET']
from driver.prepare.get import acquisition
from driver.prepare.get.acquire import AcquisitionError
from driver.prepare.convert import overlay
P = sg.marker_prefix(ANON); vis = sg.Visible(ANON); runs, _ = sg.symbol_runs(ANON, vis)
MARKED = sg.tag_cells(ANON, vis, (), [(a, b'<!--%ss:%d-->' % (P.encode(), k)) for k, (a, _, _, ok) in enumerate(runs) if ok], P)[0]


def corrupt(ev, url): ev['observed'][url] = dict(ev['observed'][url], sha256='0' * 64); return ev
def selection(browser, ev):
    body, _ = overlay.measurement_body(ev['observed'][TARGET]['body'], ANON, MARKED, P, ev['proof'])
    return acquisition.Selection(ev['parent_url'], ev['observed'], TARGET, ANON, body, P).run(browser)


class SelectionNavigationFacts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()
    def facts_after_load(self, parent):  # the selection's own page, unmarked, settled: its received facts (acquisition.facts)
        ev = evidence(child=ANON, parent=parent); body, _ = overlay.measurement_body(ev['observed'][TARGET]['body'], ANON, MARKED, P, ev['proof'])
        sel = acquisition.Selection(ev['parent_url'], ev['observed'], TARGET, ANON, body, P); rec = {'log': [], 'errors': []}; ctx, page = sel._page(self.browser, False, rec)
        try: sel._settle(page); return acquisition.facts(rec), ev['parent_url']
        finally: ctx.close()
    def test_refused_navigation_is_listed_apart(self):  # Root CONTEXT_NAVIGATION_DECISION: a blocked navigation is unknown; refused_get and its comparison unchanged
        go = g['rep'](g['PARENT_UI'], b'</body>', b'<script>setTimeout(function () { location.href = "https://museum.invalid/portal/elsewhere.html"; }, 50);</script></body>')
        f, _ = self.facts_after_load(go); self.assertEqual(f['refused_navigation'], ['https://museum.invalid/portal/elsewhere.html'])
        self.assertNotIn('https://museum.invalid/portal/elsewhere.html', [x[0] for x in f['refused_get']])
        again = g['rep'](g['PARENT_UI'], b'</body>', b'<script>if (!sessionStorage.r) { sessionStorage.r = 1; setTimeout(function () { location.reload(); }, 50); }</script></body>')
        f, parent = self.facts_after_load(again); self.assertEqual(f['refused_navigation'], [parent])  # a refused reload of the answered parent: only the refusal list shows it
        f, _ = self.facts_after_load(g['PARENT_UI']); self.assertEqual(f['refused_navigation'], [])


if __name__ == '__main__':
    unittest.main()
