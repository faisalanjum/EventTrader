"""Trial-to-extraction state identity (root-native-trial-reference-handoff-20261029t112025714288z; invented public fixture, real browser). contextual_routes
names a state by its trial's unmarked native record ('a state is its canonical native fingerprint'), then extracts it in a new Context whose gate is
anchored to that Context's own first unmarked observation. An extraction whose reference is NOT the observation that named its state is not proved to be
that state: it stays incomplete with its reason. The page's own state comes from test_canonical's ALT parent (a real class switch per navigation);
this browser only decides which pages show state B. Run with the normal tests.driver.prepare suite."""
import json, sys, unittest
from .cases import run, controls, activations, state, ANON
from .test_canonical import ALT

IDENTITY = "state identity: this extraction's reference differs from the trial observation that named the state"
NOT_TRIAL = 'differs from the trial observation that named the state'  # the gate's defense or (root-trial-bound-first-observation) the first observation's own refusal
def held_by_trial(reasons): return any(NOT_TRIAL in r for r in reasons)


class TrialPages:  # the test's browser: pages opened inside contextual_routes' trial() show `trial`, every other page state A (the real ALT switch)
    def __init__(self, browser, trial): self.b, self.trial = browser, trial
    def new_page(self, **kw):
        f, in_trial = sys._getframe(1), False
        while f is not None and not in_trial: in_trial, f = f.f_code.co_name == 'trial', f.f_back
        page = self.b.new_page(**kw); page.add_init_script('window.__seq = %s;' % json.dumps([self.trial if in_trial else 'A'])); return page
    def __getattr__(self, name): return getattr(self.b, name)


class TrialIdentity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
        cls.same = run(TrialPages(cls.browser, 'A'), ANON, parent=ALT); cls.other = run(TrialPages(cls.browser, 'B'), ANON, parent=ALT)
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def first(self, res): return activations(res, controls(ANON)[0])[0]
    def trial_native(self, res, label): return next(t['record'].get('native') for t in res['trials'] if t['label'] == label)

    def test_control_the_trial_and_the_extraction_observe_the_same_state(self):
        a = self.first(self.same); self.assertEqual((a['status'], a['reasons']), ('complete', []), json.dumps(a['reasons'])[:400])
        s = state(self.same, a['state']); ref = next(r['native'] for r in s['records'] if not r.get('marked') and r.get('native'))
        self.assertEqual(ref, self.trial_native(self.same, 'trial@%d' % controls(ANON)[0]))  # the same native record: document, capture, inputs
    def test_an_extraction_of_another_observation_is_not_that_state(self):
        a = self.first(self.other); s = state(self.other, a['state']); trial = self.trial_native(self.other, 'trial@%d' % controls(ANON)[0])
        seen = [x['native'] for r in s['records'] if not r.get('marked') for x in r.get('attempts', []) if x.get('native')]  # every unmarked observation the extraction made
        self.assertTrue(seen); self.assertTrue(all(n['document_sha256'] != trial['document_sha256'] for n in seen))  # the fixture did diverge
        self.assertFalse(any(r.get('native') for r in s['records']))  # no reference established from another observation
        self.assertEqual(a['status'], 'incomplete'); self.assertTrue(held_by_trial(a['reasons']), a['reasons'])
        self.assertIsNot(s['route'].get('text_proved'), True)  # the state's own route keeps no text proof
    def test_a_mismatched_state_is_never_an_equal_state_target(self):  # never enrolled: no later trial resolves to it
        for res, want in ((self.same, False), (self.other, True)):
            acts = [a for l in res['initial']['source_links'] for a in l.get('activations') or []]; held = {a['state'] for a in acts if held_by_trial(a['reasons'])}
            self.assertEqual(bool(held), want); edges = [e for a in acts for e in (a.get('state_graph') or {}).get('edges', [])]
            self.assertEqual([e for e in edges if e['kind'] == 'equal state' and e['to'] in held], [])
    def test_the_initial_view_is_unchanged(self):  # no trial names the initial view: its own reference only
        for res in (self.same, self.other): self.assertNotIn(IDENTITY, json.dumps(res['initial'].get('error') or ''))


if __name__ == '__main__':
    unittest.main()
