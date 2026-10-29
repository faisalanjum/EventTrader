"""Trial-bound first observation (root-trial-bound-first-observation-validation-20261029t130424212507z; invented public fixture, real browser, test_canonical's
ALT switch and Scheduled browser). A trial-named extraction establishes its reference only from its OWN unmarked observation that equals the trial record
that named the state, within the existing attempts: nothing is prefilled, a marked render never borrows the trial, the fixed reference is never switched
afterwards, and an unnamed Context is unchanged. The expected state of every navigation is the fixture schedule's. Run with the normal suite."""
import json, sys, unittest
from .cases import context, sg, evidence, run, controls, activations, state, ANON
from .test_canonical import ALT, MARKED, Scheduled

NOT_TRIAL = 'differs from the trial observation that named the state'


def outcomes(rec): return [a['outcome'].split(' (')[0] for a in rec.get('attempts', [])]


class Ordered:  # trial pages show `trial`; the first other page after each trial shows `first` (one entry per navigation of that page); every other page `later`
    def __init__(self, browser, trial, first, later): self.b, self.trial, self.first, self.later, self.armed = browser, trial, first, later, False
    def new_page(self, **kw):
        f, in_trial = sys._getframe(1), False
        while f is not None and not in_trial: in_trial, f = f.f_code.co_name == 'trial', f.f_back
        if in_trial: seq, self.armed = [self.trial], True
        elif self.armed: seq, self.armed = self.first, False
        else: seq = self.later
        page = self.b.new_page(**kw); page.add_init_script('window.__seq = %s;' % json.dumps(seq)); return page
    def __getattr__(self, name): return getattr(self.b, name)


class ContextLevel(unittest.TestCase):  # one Context, its renders in order (test_canonical's readings), named by a real earlier unmarked observation of state B
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch(); cls.B = cls.reading(None, [['B']], [ANON])[0].reference
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()
    @classmethod
    def reading(cls, named_by, plan, bodies):
        ev = evidence(child=ANON, parent=ALT); ctx = context.Context(ev); ctx.named_by = named_by; src = context.state_source(sg.Source('child.html', {'child.html': ANON}), ev, ctx)
        br, errs = Scheduled(cls.browser, plan), []
        for body in bodies:
            page = ctx.page(br, None, ('https://trial.invalid/', body), src)
            try: page.goto('reading'); errs.append(None)
            except Exception as e: errs.append(repr(e)[:300])
            finally: page.close()
        return ctx, errs

    def test_mismatch_then_match_establishes_the_named_state(self):
        ctx, errs = self.reading(self.B, [['A', 'B'], ['B']], [ANON, MARKED])
        self.assertEqual((errs, ctx.gate()), ([None, None], [])); self.assertEqual(ctx.reference, self.B)
        self.assertEqual(outcomes(ctx.records[0]), ['not used: ' + NOT_TRIAL, 'used: the state reference']); self.assertEqual(outcomes(ctx.records[1]), ['used'])
    def test_never_matching_establishes_no_reference(self):
        ctx, errs = self.reading(self.B, [['A']], [ANON]); self.assertIsNone(ctx.reference); self.assertIsNotNone(errs[0])
        self.assertEqual(outcomes(ctx.records[0]), ['not used: ' + NOT_TRIAL] * 3); self.assertTrue(ctx.gate())
    def test_a_marked_first_render_cannot_borrow_the_trial(self):
        ctx, errs = self.reading(self.B, [['B']], [MARKED]); self.assertIsNone(ctx.reference)
        self.assertEqual(outcomes(ctx.records[0]), ['not used: no state reference']); self.assertTrue(ctx.gate())
    def test_the_established_reference_is_never_switched(self):
        ctx, errs = self.reading(self.B, [['A', 'B'], ['A']], [ANON, MARKED]); self.assertEqual(ctx.reference, self.B); self.assertTrue(ctx.gate())
        self.assertEqual(outcomes(ctx.records[1]), ['not used: differs from the state reference'] * 3)
    def test_an_unnamed_context_is_unchanged(self):
        ctx, errs = self.reading(None, [['A'], ['A']], [ANON, MARKED]); self.assertEqual((errs, ctx.gate()), ([None, None], []))
        self.assertEqual(outcomes(ctx.records[0]), ['used: the state reference'])


class GraphLevel(unittest.TestCase):  # the actual contextual_routes boundary
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); b = cls.pw.chromium.launch(); cls.browser = b
        cls.switch = run(Ordered(b, 'B', ['A', 'B'], ['B']), ANON, parent=ALT); cls.never = run(Ordered(b, 'B', ['A'], ['A']), ANON, parent=ALT)
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def test_a_state_reached_on_its_second_attempt_is_complete_and_enrolled(self):
        outer = controls(ANON)[0]; a = activations(self.switch, outer)[0]; self.assertEqual((a['status'], a['reasons']), ('complete', []), json.dumps(a['reasons'])[:400])
        r0 = state(self.switch, a['state'])['records'][0]; self.assertEqual(outcomes(r0), ['not used: ' + NOT_TRIAL, 'used: the state reference'])
        self.assertEqual(r0['native'], next(t['record']['native'] for t in self.switch['trials'] if t['label'] == f'trial@{outer}'))
        self.assertEqual({(e['kind'], e['to']) for e in a['state_graph']['edges'] if e['control'] == outer}, {('equal state', a['state'])})  # the replacement reaches the proved state
    def test_a_never_matching_state_is_held_unenrolled_and_unexpanded(self):
        a = activations(self.never, controls(ANON)[0])[0]; self.assertEqual(a['status'], 'incomplete'); self.assertTrue(any(NOT_TRIAL in r for r in a['reasons']), a['reasons'])
        s = state(self.never, a['state']); self.assertFalse(any(r.get('native') for r in s['records']))  # no reference established
        self.assertIsNot(s['route'].get('text_proved'), True); self.assertEqual((a['state_graph']['edges'], a['state_graph']['unexpanded']), ([], [a['state']]))


if __name__ == '__main__':
    unittest.main()
