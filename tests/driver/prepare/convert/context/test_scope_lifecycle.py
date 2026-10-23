"""Isolated-world source scope: lifetime and failure (Root FABLE_SCOPE_ROOT_REVIEW_20261022T2012; invented public fixture cases.PARENT_UI / ANON,
written before the cand_iso4 code). A closed page releases its scope; a real isolated-world failure refuses the attempt with its cause; a retried
attempt keeps only its own scope readings and the world is rebuilt for the next document."""
import unittest
from unittest import mock
from .cases import context, sg, evidence, rep, ANON, PARENT_UI, PNG

ONCE = b"<script>if (!sessionStorage.getItem('once')) { sessionStorage.setItem('once', '1'); document.querySelector('nav').innerHTML = ''; }</script></body>"  # the first load only: no menu


def render(browser, parent=PARENT_UI):  # one Context render of the initial view (selected path: the recorded selection {'source_anchor': 1}): (error, ctx)
    ev = evidence(child=ANON, parent=parent); ctx = context.Context(ev); src = context.state_source(sg.Source('child.html', {'child.html': ANON, 'plan.png': PNG}), ev, ctx); page = err = None
    try:
        page = ctx.page(browser, None, ('https://trial.invalid/', ANON), src); page.goto('trial')
    except Exception as e:
        err = repr(e)[:400]
    finally:
        if page is not None: page.close()
    return err, ctx


class ScopeLifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def test_closed_pages_release_their_scope(self):
        ev = evidence(child=ANON); ctx = context.Context(ev)
        for _ in range(2):
            page = ctx.page(self.browser, None, ('https://trial.invalid/', ANON), context.state_source(sg.Source('child.html', {'child.html': ANON}), ev, ctx)); page.close()
        self.assertEqual(len(ctx.scopes), 0)

    def test_a_real_isolated_world_failure_refuses_with_its_cause(self):
        err, ctx = render(self.browser); self.assertIsNone(err, err)  # positive: the healthy world
        with mock.patch.object(context, 'ISO_INIT', 'throw new Error("deliberate isolated-world failure")'):
            err, ctx = render(self.browser)
        self.assertIsNotNone(err); self.assertIn('source scope', err); self.assertIn('deliberate isolated-world failure', repr(ctx.records[0]))

    def test_a_retried_attempt_keeps_only_its_own_scope_readings_and_the_world_is_rebuilt(self):
        err, ctx = render(self.browser, rep(PARENT_UI, b'</body>', ONCE)); self.assertIsNone(err, err)
        r = ctx.records[0]; first = r['attempts'][0]
        self.assertTrue(first['outcome'].startswith('not used'), first)
        self.assertTrue(isinstance(first.get('pre_selection_nodes'), list) and isinstance(first['pre_selection_nodes'][0], int), first)  # its own snapshot, moved with it
        self.assertNotIn('scope_activated', first)  # never reached in that attempt: nothing inherited
        self.assertEqual(r.get('scope_activated'), [True, None]); self.assertIsInstance(r['pre_selection_nodes'][0], int)  # the later document's own world


if __name__ == '__main__':
    unittest.main()
