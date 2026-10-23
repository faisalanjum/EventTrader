"""Control identity (Root FABLE_CONTROL_IDENTITY_REPAIR_20261022T2020; Smart's class C fixture, SMART_PROOF_STATE_VERIFY_RESULT.md): the member's
own script swaps a page-writable control pointer. Expected outcomes come from the fixture's authored source: 'Gallery map' (first control) reveals
note-amber, 'Cabinet label' reveals note-indigo; inside the amber note 'Open notes' sets its own label to 'Close notes' and 'Open maps' sets 'Close
maps'. A control is never credited with another control's definition or label change; the genuine relation is still found."""
import unittest
from .cases import run, rep, controls, activations, CHILD as V1
from . import test_observed_controls as T

def swap(js): return b'<script>(function () { setInterval(function () { ' + js + b' }, 0); })();</script></head>'
SWAP_OUTER = swap(b'if (window.__ctl && window.__ctl.id === "map-link") { window.__ctl = document.getElementById("label-link"); }')  # Smart's class C script, verbatim logic
SWAP_REPEAT = swap(b'if (window.__outerCtl && window.__outerCtl.id === "map-link") { window.__outerCtl = document.getElementById("label-link"); }')
SWAP_INNER = swap(b'var c = window.__ctl; if (c && c.textContent === "Open notes" && window.__copy) { var m = Array.prototype.find.call(window.__copy.querySelectorAll("a"), function (a) { return a.textContent === "Open maps"; }); if (m) window.__ctl = m; }')


class ControlIdentity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()
    def targets(self, res, start): return [(a.get('status'), (a.get('target') or {}).get('declared_id')) for a in activations(res, start)]

    def test_positive_first_label_reveals_its_own_definition(self):
        res = run(self.browser, child=V1); self.assertIn(('complete', 'note-amber'), self.targets(res, controls(V1)[0]))

    def test_a_swapped_control_pointer_never_credits_another_definition(self):
        child = rep(V1, b'</head>', SWAP_OUTER); res = run(self.browser, child=child); got = self.targets(res, controls(child)[0])
        self.assertFalse(any(t == 'note-indigo' for _, t in got), got)
        self.assertIn(('complete', 'note-amber'), got)  # the pointer is never read: the genuine relation stands

    def test_a_swapped_outer_pointer_never_credits_another_definition_on_repeat(self):
        child = rep(V1, b'</head>', SWAP_REPEAT); res = run(self.browser, child=child); got = self.targets(res, controls(child)[0])
        self.assertFalse(any(t == 'note-indigo' for _, t in got), got); self.assertIn(('complete', 'note-amber'), got)

    def test_a_swapped_inner_pointer_never_credits_another_label_change(self):
        for child, must in ((T.CHILD, True), (rep(T.CHILD, b'</head>', SWAP_INNER), False)):
            res = run(self.browser, child=child); notes = next(l['start'] for l in T.sg.Visible(child).links if child[l['tag_end']:l['end']] == b'Open notes')
            labels = [(a.get('control_label') or {}).get('after') for a in activations(res, notes)]
            self.assertNotIn('Close maps', labels, labels)
            if must: self.assertIn('Close notes', labels, labels)  # positive: its own label change is found
            else: self.assertTrue(all(x in (None, 'Close notes') for x in labels), labels)


if __name__ == '__main__':
    unittest.main()
