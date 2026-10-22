"""Parent-effect guard (Root CONTEXT_PARENT_EFFECT_GUARD_20261021; invented public fixture): our marks make the PARENT change an ancestor's class, so
the selected child's text renders struck through while the child's own unmarked DOM stays identical. Every render of every state, initial and
activated, must equal the state's unmarked reference render (whole native serialization without our comments, received inputs), so both views refuse.
An unrelated outside change made by the same trigger also refuses: the strict rule's accepted robustness limit, not a qualified positive.
The delayed case (a 100 ms timer set by the marked response) must refuse too: the settle window has to see it before the snapshot.
Run with the normal tests.driver.prepare suite."""
import json, unittest
from .cases import rep, run, controls, activations, PARENT_UI, ANON, BUTTON
INSERT = b"jQuery('#report-host').empty().append(data);"
TRIGGER = INSERT + b" if (/<!--m[0-9a-f]{8}/.test(data)) "  # the parent reacts to our marker comments in the delivered response
STRIKE = rep(rep(PARENT_UI, b'</head>', b'<style>body.struck #report-host { text-decoration: line-through; }</style></head>'), INSERT, TRIGGER + b"document.body.className = 'struck';")
OUTSIDE = rep(PARENT_UI, INSERT, TRIGGER + b"document.querySelector('nav').setAttribute('data-note', 'seen');")
DELAYED = rep(rep(PARENT_UI, b'</head>', b'<style>body.struck #report-host { text-decoration: line-through; }</style></head>'), INSERT,
             TRIGGER + b"setTimeout(function () { document.body.className = 'struck'; }, 100);")  # OCR's delayed case: one 100 ms timer after the selecting action
DECOR = "() => getComputedStyle(document.querySelector('#report-host p')).webkitTextDecorationsInEffect"  # native evidence of the rendering change


class ParentEffect(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def refused_everywhere(self, parent):
        res = run(self.browser, ANON, parent=parent); init = res['initial']
        self.assertNotEqual(init['status'], 'OK'); self.assertIn('no observation attempt equalled the state reference', init.get('error') or '')
        for s in controls(ANON):
            a = activations(res, s); self.assertTrue(a and a[0]['status'] != 'complete', json.dumps(a)[:400])
            self.assertTrue(any('no observation attempt equalled the state reference' in w and 'document_sha256' in w for w in a[0]['reasons']), json.dumps(a[0]['reasons'])[:600])
        return res

    def test_strike_via_ancestor_class_refused_initial_and_activated(self):
        self.refused_everywhere(STRIKE)
        page = self.browser.new_page()  # the fixture does what it claims: the marked response strikes the child's text, the plain one does not
        try:
            for data, want in ((b'<p>Use the east stair.</p><!--m0123abcd s:1-->', 'line-through'), (b'<p>Use the east stair.</p>', 'none')):
                page.set_content('<style>body.struck #report-host { text-decoration: line-through; }</style><div id="report-host"></div>')
                page.evaluate("(d) => { document.querySelector('#report-host').innerHTML = d; if (/<!--m[0-9a-f]{8}/.test(d)) document.body.className = 'struck'; }", data.decode())
                self.assertEqual(page.evaluate(DECOR), want)
        finally: page.close()

    def test_unrelated_outside_change_refused_by_the_strict_rule(self): self.refused_everywhere(OUTSIDE)

    def test_delayed_marker_sensitive_change_refused(self): self.refused_everywhere(DELAYED)  # caught only by the 500 ms quiet window (two quiet frames let it escape)

    def test_clean_parent_no_false_refusal(self):
        res = run(self.browser, ANON); self.assertEqual((res['initial']['status'], res['initial'].get('error')), ('PARTIAL', BUTTON))
        self.assertEqual([activations(res, s)[0]['status'] for s in controls(ANON)], ['complete', 'complete'])

if __name__ == '__main__':
    unittest.main()
