# Ported to the normal suite from context_candidate/tests_snapshot_20261022T0237_final/test_family_outcome.py (sha256 d78c0d29253e772be97b6d812df176d92ee9d35093cf69b39b2418e01875abd4). Test bodies unchanged; mechanical change only:
# fixtures from this directory's cases.py instead of runpy (BUTTON from test_context_states.py unless cases.py defines it).
"""A failed source-owned action must not silently imply complete content (Root CONTEXT_MINIMAL_COMPLETENESS_DECISION_20261022; OCR's counterexample:
a control that needs a function from the parent's own script). Invented public fixture, real mechanism: the parent's panels.js either defines the
function (positive) or does not (the action raises a native TypeError, a script error). Positive: the inner control reveals its hidden paragraph in an
inner state, so the family shows every target run; the document stays OK although the outer state alone has a hidden child (an explicitly observed
hidden state, not a document error). Inner failure: the same child without the function; the paragraph is never shown in any state, so the saved
document status must say incomplete. Outer failure: a top-level control whose own function is missing; its target state is unknown, so the same.
The document status is html_route's existing route status (PARTIAL + reasons), which the caller saves as COMPLETE native_status.
Run: CANDIDATE_RUNTIME=<runtime> python -I -B test_family_outcome.py"""
import json, unittest
from pathlib import Path
from . import cases; g = dict(vars(cases)); g.setdefault('BUTTON', 'context: 1 declared event handler(s) outside the supported link path (not activated)')  # BUTTON: test_context_states.py's exact constant unless cases.py defines it
rep, run, activations, ANON, RICH, PANELS, sg = (g[k] for k in ('rep', 'run', 'activations', 'ANON', 'RICH', 'PANELS', 'sg'))
MORE = PANELS + b"\nwindow.MuseumCards.more = function (trigger) { trigger.nextElementSibling.style.display = 'block'; };\n"
INNER = (b'<aside class="museum-note" id="note-amber"><p>Use the east stair.</p>\n<a href="javascript:void(0)" onclick="MuseumCards.more(this)">More hours</a>'
         b'<div style="display:none"><p>Late opening on Fridays.</p></div></aside>')
CHILD = rep(ANON, RICH, INNER)
OUTER_MISSING = rep(CHILD, b"MuseumCards.reveal(this, 'note-indigo')", b"MuseumCards.missing(this, 'note-indigo')")
def at(child, text): return next(l['start'] for l in sg.Visible(child).links if child[l['tag_end']:l['end']] == text)


class FamilyOutcome(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
        cls.pos, cls.inner, cls.outer = run(cls.browser, CHILD, panels=MORE), run(cls.browser, CHILD), run(cls.browser, OUTER_MISSING, panels=MORE)
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()
    def family(self, res): return next(a for a in activations(res, at(CHILD, b'Gallery map')) if a.get('coverage_across_states'))

    def test_positive_every_run_shown_and_document_ok(self):
        f = self.family(self.pos); self.assertEqual(f['coverage_across_states']['never_affirmatively_shown_runs'], [], json.dumps(f['coverage_across_states'])[:400])
        self.assertEqual(f['status'], 'incomplete')  # the outer state alone: its hidden child, explicitly observed hidden there
        self.assertEqual([a['status'] for a in activations(self.pos, at(CHILD, b'More hours'))][:1], ['complete'])
        self.assertEqual((self.pos['initial']['status'], self.pos['initial'].get('error')), ('PARTIAL', g['BUTTON']))  # only the fixture's own button: every family run shown

    def test_inner_failure_never_shown_makes_the_document_incomplete(self):
        a = activations(self.inner, at(CHILD, b'More hours')); self.assertTrue(a and {x['status'] for x in a} == {'refused'}, json.dumps(a)[:400])
        self.assertIn('script error', json.dumps(a[0]['reasons']))
        self.assertTrue(self.family(self.inner)['coverage_across_states']['never_affirmatively_shown_runs'])
        i = self.inner['initial']; self.assertEqual(i['status'], 'PARTIAL', 'a failed inner action left target content never shown, yet the document says OK')
        self.assertIn('never affirmatively shown', i['error'])

    def test_outer_failure_unknown_state_makes_the_document_incomplete(self):
        c = at(OUTER_MISSING, b'Cabinet label'); a = activations(self.outer, c); self.assertTrue(a and a[0]['status'] == 'refused', json.dumps(a)[:400])
        self.assertIn('script error', json.dumps(a[0]['reasons']))
        i = self.outer['initial']; self.assertEqual(i['status'], 'PARTIAL', 'a failed outer action has an unknown state, yet the document says OK')
        self.assertIn(str(c), i['error'])

OUTER_POST = rep(CHILD, b"MuseumCards.reveal(this, 'note-indigo')", b"fetch('https://museum.invalid/portal/log', {method: 'POST', body: 'x'}); MuseumCards.reveal(this, 'note-indigo')")
def routes(browser, child, panels, **ceilings):  # cases.run with the configured ceilings passed through to the one owner (contextual_routes)
    sha = g['hashlib'].sha256(child).hexdigest(); members = {'child.html': child, 'plan.png': g['PNG']}
    return g['context'].contextual_routes(child, 'invented/child.html', sha, browser, sg.Source('child.html', members), g['evidence'](child=child, panels=panels), **ceilings)


class FamilyBoundaries(unittest.TestCase):  # Root CONTEXT_FINAL_OUTCOME_CLOSE_20261022: the ceilings and a non-GET source action, on the same real positive fixture
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
        cls.pos = routes(cls.browser, CHILD, MORE)  # default ceilings (32 states, 128 transitions)
        cls.states1, cls.trans1 = routes(cls.browser, CHILD, MORE, max_states=1), routes(cls.browser, CHILD, MORE, max_transitions=1)
        cls.post = run(cls.browser, OUTER_POST, panels=MORE)
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()
    def family(self, res): return next(a for a in activations(res, at(CHILD, b'Gallery map')) if a.get('coverage_across_states'))

    def test_positive_default_ceilings_leave_no_frontier_and_no_new_deficit(self):
        f = self.family(self.pos); self.assertEqual(f['state_graph']['frontier'], []); self.assertEqual(f['state_graph']['ceilings'], {'states': 32, 'transitions': 128})
        self.assertEqual((self.pos['initial']['status'], self.pos['initial'].get('error')), ('PARTIAL', g['BUTTON']))  # only the fixture's own button

    def ceiling(self, res, key, value):
        f = self.family(res); sg_ = f['state_graph']; self.assertEqual(sg_['ceilings'][key], value); self.assertTrue(sg_['frontier'], json.dumps(sg_)[:400])
        self.assertEqual(f['status'], 'incomplete'); self.assertTrue(any('left unexplored at the ceiling' in r for r in f['reasons']), json.dumps(f['reasons'])[:400])
        i = res['initial']; self.assertEqual(i['status'], 'PARTIAL'); self.assertIn(g['BUTTON'], i['error'])
        self.assertIn('%d transition(s) left unexplored at the state ceiling' % len(sg_['frontier']), i['error'])  # the document's own extra reason, beyond the button
        return sg_
    def test_state_ceiling_saves_the_frontier_and_makes_the_document_incomplete(self):
        sg_ = self.ceiling(self.states1, 'states', 1); self.assertEqual(len(sg_['states']), 1)
    def test_transition_ceiling_saves_the_frontier_and_makes_the_document_incomplete(self):
        sg_ = self.ceiling(self.trans1, 'transitions', 1); self.assertEqual(sg_['transitions'], 1)

    def test_a_source_action_making_a_non_get_request_is_unknown(self):
        c = at(OUTER_POST, b'Cabinet label'); a = activations(self.post, c); self.assertTrue(a and a[0]['status'] == 'refused', json.dumps(a)[:400])
        self.assertIn('non-GET request', json.dumps(a[0]['reasons']))
        i = self.post['initial']; self.assertEqual(i['status'], 'PARTIAL'); self.assertIn(g['BUTTON'], i['error'])
        self.assertIn('trial@%d: source-owned action refused, its state unknown' % c, i['error'])  # the extra reason, beyond the button


if __name__ == '__main__':
    unittest.main()
