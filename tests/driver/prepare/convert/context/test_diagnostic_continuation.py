"""Context.continuation: the QUALIFICATION-ONLY diagnostic continuation at the NORMAL refusal owners (root-single-version-qualification-20261028t193735747002z).
The existing invented fixture whose source control POSTs before it reveals (test_family_outcome OUTER_POST) is refused natively; only evidence naming the
exact POST address as the bound inserted script lets the state be observed, and then it stays incomplete with every rejected reason kept."""
import hashlib, json, unittest
from driver.prepare.convert import context, screen_grid as sg
from . import cases
from .test_family_outcome import CHILD, OUTER_POST, OUTER_MISSING, MORE, at

POST = 'https://museum.invalid/portal/log'
# OUTER_POST's fetch has no rejection handler, so its blocked POST is ALSO a script error (never continued). A sender that handles its own failed
# request, as the recorded SEC script did (10-22: its only refusal reasons were the POST and outside mutations), gives exactly the bound-effect reasons:
BOT = 'https://museum.invalid/bot'  # a window-level click listener in the parent's script, as SEC's: a POST to its own address and a transient frame
BOT_JS = MORE + b"\nwindow.addEventListener('click', function () { fetch('https://museum.invalid/bot', {method: 'POST', body: 'x'}).catch(function () {}); var f = document.createElement('iframe'); document.body.appendChild(f); f.remove(); }, true);\n"
EVIL_JS = BOT_JS + b"window.addEventListener('click', function () { var p = document.querySelector('p'); if (p) p.textContent = p.textContent + ' (changed)'; }, true);\n"  # also rewrites filing text outside the copy
POST_CAUGHT = cases.rep(CHILD, b"MuseumCards.reveal(this, 'note-indigo')", b"fetch('https://museum.invalid/portal/log', {method: 'POST', body: 'x'}).catch(function () {}); MuseumCards.reveal(this, 'note-indigo')")


def run(browser, child, bound=None, **kw):  # cases.run, with the qualification caller's one extra evidence key when `bound` is given
    ev = cases.evidence(child=child, **kw)
    if bound: ev['diagnostic_continuation'] = {'bound_href': bound}
    return context.contextual_routes(child, 'invented/child.html', hashlib.sha256(child).hexdigest(), browser, sg.Source('child.html', {'child.html': child, 'plan.png': cases.PNG}), ev)


class DiagnosticContinuation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
        cls.plain, cls.diag, cls.other = (run(cls.browser, POST_CAUGHT, b, panels=MORE) for b in (None, POST, 'https://museum.invalid/other'))
        cls.err, cls.uncaught = run(cls.browser, OUTER_MISSING, POST, panels=MORE), run(cls.browser, OUTER_POST, POST, panels=MORE)
        cls.normal, cls.evil, cls.without = run(cls.browser, CHILD, BOT, panels=BOT_JS), run(cls.browser, CHILD, BOT, panels=EVIL_JS), run(cls.browser, CHILD, panels=MORE)
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()
    def acts(self, res, child=POST_CAUGHT): return cases.activations(res, at(child, b'Cabinet label'))

    def test_production_settings_still_refuse_the_post(self):  # unchanged: no evidence key, no continuation
        a = self.acts(self.plain); self.assertEqual(a[0]['status'], 'refused', json.dumps(a)[:300]); self.assertIn('non-GET request', json.dumps(a[0]['reasons']))
    def test_the_bound_post_is_observed_on_but_stays_incomplete(self):
        a = self.acts(self.diag); self.assertTrue(a and a[0]['state'], json.dumps(a)[:400]); self.assertEqual(a[0]['status'], 'incomplete')
        self.assertTrue(any('diagnostic continuation (qualification only, never a native success)' in r for r in a[0]['reasons']), a[0]['reasons'])
        s = cases.state(self.diag, a[0]['state']); c = [r['diagnostic_continuation'] for r in s['records'] if r.get('diagnostic_continuation')]
        self.assertTrue(c); self.assertEqual(c[0]['rejected'], ['non-GET request']); self.assertTrue(any(q[1] == 'POST' and q[2] == POST for q in c[0]['requests']))
    def test_the_document_is_never_a_native_success(self):
        self.assertEqual(self.diag['initial']['status'], 'PARTIAL')
    def test_a_post_to_another_address_is_still_refused(self):
        a = self.acts(self.other); self.assertEqual(a[0]['status'], 'refused'); self.assertIn('non-GET request', json.dumps(a[0]['reasons']))
    def test_a_script_error_is_never_continued(self):
        a = self.acts(self.err, OUTER_MISSING); self.assertEqual(a[0]['status'], 'refused', json.dumps(a)[:300]); self.assertIn('script error', json.dumps(a[0]['reasons']))
    def test_a_bound_post_that_also_raises_a_script_error_is_never_continued(self):
        a = self.acts(self.uncaught, OUTER_POST); self.assertEqual(a[0]['status'], 'refused'); self.assertIn('script error', json.dumps(a[0]['reasons']))


    # the producer's comparison on REAL contextual_routes output in its actual diagnostic representation
    def views(self, res): return dict({'initial': res['initial']}, **{s['label']: s['route'] for s in res['states']})
    def test_the_native_positive_pairs_every_state(self):  # the bot listener's effects were continued; every state equals WITHOUT's
        n, w = self.views(self.normal), self.views(self.without); self.assertEqual(sorted(n), sorted(w)); self.assertGreater(len(w), 1)
        self.assertTrue(any(r.get('diagnostic') for r in n.values()), 'no state carried the diagnostic representation')
        diffs = {lb: [k for k, v in context.compare_views(n[lb], w[lb]).items() if not v] for lb in w}
        self.assertEqual({lb: d for lb, d in diffs.items() if lb != 'initial'}, {lb: [] for lb in w if lb != 'initial'})  # every state pairs, its kept native proof included
        # this invented page's initial view is itself unproved in BOTH arms (a declared handler outside the supported link path, unrelated to the
        # script), so a qualification of it is held, as it must be: no missing or false proof is turned true
        self.assertEqual(diffs['initial'], ['text_proved']); self.assertIs(n['initial'].get('text_proved'), False); self.assertIs(w['initial'].get('text_proved'), False)
        self.assertEqual(self.normal['initial']['status'], 'PARTIAL')  # never a native success on its own
    def test_a_listener_that_also_changes_filing_text_is_caught_by_the_pair(self):  # the continuation lets it be observed; the comparison holds it
        n, w = self.views(self.evil), self.views(self.without)
        diffs = {lb: [k for k, v in context.compare_views(n[lb], w[lb]).items() if not v] for lb in w if lb in n}
        self.assertTrue(sorted(n) != sorted(w) or any(diffs.values()), diffs)


if __name__ == '__main__':
    unittest.main()
