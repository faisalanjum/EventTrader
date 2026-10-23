"""The one native error boundary of retained-control reads (Root ROOT_CONTROL_NATIVE_ERROR_REVIEW_20261022T2109; written before the cand_ctl2 code):
a native exception or an absent/destroyed retained object refuses with its cause; a by-value undefined and a null node are results; a real Context
render whose observation throws can never be OK or text-proved. Fixture: cases.CHILD (the original public positive), its first control."""
import hashlib, unittest
from unittest import mock
from .cases import context, sg, evidence, controls, CHILD, PNG
from driver.prepare.convert import html_route

THROW = "function (p) { throw new Error('ROOT_NATIVE_OBSERVATION_FAILURE'); }"


class NativeErrorBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()
    def scoped(self):  # a real page with its Scope and one retained node
        page = self.browser.new_page(); sc = context.Scope(page); page.goto('data:text/html,<a id="x">x</a>')  # no href: its click must not navigate (v1: '#' ended the data URL; v2: href navigated on click)
        return page, sc, sc.obj('document.getElementById("x")')[0]

    def test_positive_reads_and_explicit_results(self):
        page, sc, o = self.scoped()
        try:
            self.assertEqual(sc.on(o, 'function () { return this.id; }'), ('x', None))
            self.assertEqual(sc.on(o, 'function () { this.click(); }'), (None, None))  # a by-value undefined is no error
            self.assertEqual(sc.on(o, 'function () { return null; }', by_value=False), (None, 'no object'))  # a null node: an explicit result
        finally: page.close()

    def test_a_native_exception_refuses_with_its_cause(self):
        page, sc, o = self.scoped()
        try:
            with self.assertRaises(context.Refused) as e: sc.on(o, "function () { throw new Error('NATIVE_X'); }")
            self.assertIn('NATIVE_X', str(e.exception))
        finally: page.close()

    def test_a_destroyed_or_absent_handle_refuses(self):
        page, sc, o = self.scoped()
        try:
            page.goto('data:text/html,<p>another document</p>')
            with self.assertRaises(context.Refused): sc.on(o, 'function () { return this.id; }')
            with self.assertRaises(context.Refused): sc.on(None, 'function () { return 1; }')
        finally: page.close()

    def test_a_thrown_observation_is_never_ok(self):  # Root's real Context path (html_route.prepare on the activated state)
        def route(fn):
            ctx = context.Context(evidence(child=CHILD), control=controls(CHILD)[0], label='t')
            src = context.state_source(sg.Source('child.html', {'child.html': CHILD, 'plan.png': PNG}), ctx.evidence, ctx)
            try:
                with mock.patch.object(context, 'OBSERVE', fn): r, _ = html_route.prepare(CHILD, 'invented/child.html', hashlib.sha256(CHILD).hexdigest(), self.browser, src)
            except Exception as e: return None, ctx, repr(e)
            return r, ctx, None
        r, ctx, err = route(context.OBSERVE); self.assertIsNone(err, err); self.assertEqual((r['status'], r['text_proved']), ('OK', True))  # positive
        r, ctx, err = route(THROW)
        self.assertTrue(err is not None or (r['status'] != 'OK' and r.get('text_proved') is not True), (err, r and r.get('status'), r and r.get('text_proved')))
        self.assertTrue(ctx.gate(), ctx.gate()); self.assertIn('ROOT_NATIVE_OBSERVATION_FAILURE', repr(ctx.records))


if __name__ == '__main__':
    unittest.main()
