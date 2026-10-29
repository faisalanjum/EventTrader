"""The compare-only trial/extraction identity guard's changed branches (root-trial-identity-guard-branch-closeout-20261029t115051695081z; invented public
fixtures, real browser, test_canonical's ALT parent switch). A state whose extraction is not the trial observation that named it is held by its own gate,
is never enrolled as an equal-state or replacement target, and is never expanded (no traversal from an unproved state); each Context keeps its own first
unmarked reference. Gate component checks run without a browser. Run with the normal tests.driver.prepare suite."""
import hashlib, json, os, sys, unittest
from .cases import context, sg, evidence, controls, activations, ANON, PNG
from .test_canonical import ALT
from .test_inner import CHILD_INNER, inner_links
from .test_trial_identity import IDENTITY, held_by_trial

CEILINGS = {'max_states': 6, 'max_transitions': 12}  # small test ceilings: an invalid expansion shows as a reached ceiling, quickly


class Pages:  # the test's browser: trial pages whose label matches `which` show state B (the real ALT switch), every other page state A
    def __init__(self, browser, which): self.b, self.which = browser, which
    def new_page(self, **kw):
        f, label = sys._getframe(1), None
        while f is not None and label is None: label, f = (f.f_locals.get('label') if f.f_code.co_name == 'trial' else None), f.f_back
        page = self.b.new_page(**kw); page.add_init_script('window.__seq = %s;' % json.dumps(['B' if label is not None and self.which(label) else 'A'])); return page
    def __getattr__(self, name): return getattr(self.b, name)


def routes(browser, child):
    sha = hashlib.sha256(child).hexdigest()
    return context.contextual_routes(child, 'invented/child.html', sha, browser, sg.Source('child.html', {'child.html': child, 'plan.png': PNG}), evidence(child=child, parent=ALT), **CEILINGS)


def acts(res): return [a for l in res['initial']['source_links'] for a in l.get('activations') or []]
def held(res): return {a['state'] for a in acts(res) if held_by_trial(a['reasons'])}
def graph(res): return next(a['state_graph'] for a in acts(res) if a.get('state_graph'))
def graphs(res): return [a['state_graph'] for a in acts(res) if a.get('state_graph')]
def first_unmarked(res, label): return next(r['native'] for s in res['states'] if s['label'] == label for r in s['records'] if not r.get('marked') and r.get('native'))
def trial_native(res, label): return next(t['record'].get('native') for t in res['trials'] if t['label'] == label)
def counts(res): gs = graphs(res); return {'states': len(res['states']), 'trials': len(res['trials']), 'transitions': sum(g['transitions'] for g in gs), 'graph_states': sum(len(g['states']) for g in gs),
                                           'frontier': sum(len(g['frontier']) for g in gs), 'edges': sorted(e['kind'] for g in gs for e in g['edges']), 'held': sorted(held(res))}


class Branches(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); b = cls.pw.chromium.launch(); cls.browser = b
        inner = lambda lb: '+' in lb  # only trials of inner sequences show B: the root state is proved, its inner states are not
        cls.r = {'inner AA': routes(Pages(b, lambda lb: False), CHILD_INNER), 'inner AB': routes(Pages(b, inner), CHILD_INNER),
                 'outer AA': routes(Pages(b, lambda lb: False), ANON), 'outer BB': routes(Pages(b, lambda lb: True), ANON)}
        cls.outer, cls.toggle = controls(CHILD_INNER)[0], inner_links(CHILD_INNER)[0]
        if os.environ.get('FABLE_TRACE'): open(os.environ['FABLE_TRACE'], 'x').write(json.dumps({k: counts(v) for k, v in cls.r.items()}, indent=1, sort_keys=True))
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def test_inner_mismatch_is_held_with_its_own_reference(self):
        label = f'activated@{self.outer}+{self.toggle}'
        a = next(x for x in activations(self.r['inner AA'], self.toggle) if x['state'] == label)
        self.assertEqual((a['status'], a['reasons']), ('complete', []), json.dumps(a['reasons'])[:400])  # matching positive
        self.assertEqual(first_unmarked(self.r['inner AA'], label), trial_native(self.r['inner AA'], f'trial@{self.outer}+{self.toggle}'))
        res = self.r['inner AB']; a = next(x for x in activations(res, self.toggle) if x['state'] == label); s = next(x for x in res['states'] if x['label'] == label)
        self.assertEqual(a['status'], 'incomplete'); self.assertTrue(held_by_trial(a['reasons']), a['reasons']); self.assertIsNot(s['route'].get('text_proved'), True)
        seen = [x['native'] for r in s['records'] if not r.get('marked') for x in r.get('attempts', []) if x.get('native')]; trial = trial_native(res, f'trial@{self.outer}+{self.toggle}')
        self.assertTrue(seen); self.assertTrue(all(n != trial for n in seen)); self.assertFalse(any(r.get('native') for r in s['records']))  # no reference from another observation
        self.assertTrue(all(n['capture']['height'] == first_unmarked(self.r['inner AA'], label)['capture']['height'] for n in seen))  # the A state, as the A/A extraction saw it
        self.assertNotIn(f'activated@{self.outer}', held(res))  # the proved root stays unaffected
    def test_no_equal_state_edge_reaches_a_held_state(self):
        for k in ('inner AB', 'outer BB'):
            with self.subTest(run=k):
                res = self.r[k]; self.assertTrue(held(res)); self.assertEqual([e for g in graphs(res) for e in g['edges'] if e['kind'] == 'equal state' and e['to'] in held(res)], [])
        self.assertEqual(held(self.r['inner AA']) | held(self.r['outer AA']), set())
    def test_no_traversal_from_an_unproved_state(self):
        for k in ('inner AB', 'outer BB'):
            with self.subTest(run=k):
                res = self.r[k]; seqs = {s['label']: s['control'] for s in res['states']}; bad = [seqs[h] if isinstance(seqs[h], list) else [seqs[h]] for h in held(res)]
                tried = [t['controls'] for t in res['trials'] if t.get('label')]
                self.assertEqual([t for t in tried for p in bad if len(t) > len(p) and t[:len(p)] == p], []); self.assertEqual([f for g in graphs(res) for f in g['frontier']], [])
                self.assertEqual(sorted(u for g in graphs(res) for u in g.get('unexpanded') or []), sorted(held(res)))
    def test_replacement_reaches_only_a_proved_state(self):
        outer = controls(ANON)[0]; e = [x for x in graph(self.r['outer AA'])['edges'] if x['control'] == outer]
        self.assertEqual({(x['kind'], x['to']) for x in e}, {('equal state', f'activated@{outer}')})  # the qualified replacement edge, A/A
        self.assertEqual([e for g in graphs(self.r['outer BB']) for e in g['edges']], []); self.assertIn(f'activated@{outer}', held(self.r['outer BB']))  # held and not expanded: no replacement trial


class GateComponents(unittest.TestCase):  # Context.gate's identity check alone (no browser): one native record against the trial record that named it
    N = {'document_sha256': 'd' * 64, 'capture': {'sha256': 'c' * 64, 'height': 10}, 'received': [['GET', 'https://p.invalid/x']], 'refused_get': []}
    def gate(self, named_by, records=None):
        ctx = context.Context(evidence(child=ANON)); ctx.records = records if records is not None else [{'marked': False, 'native': self.N}, {'marked': True, 'native': self.N}]
        ctx.named_by = named_by; return ctx.gate()
    def test_each_component_difference_is_held_and_equal_is_not(self):
        self.assertNotIn(IDENTITY, self.gate(dict(self.N)))  # the matching control
        for k, v in (('document_sha256', 'e' * 64), ('capture', {'sha256': 'f' * 64, 'height': 10}), ('received', []), ('refused_get', [['GET', 'https://p.invalid/y']])):
            with self.subTest(component=k): self.assertIn(IDENTITY, self.gate(dict(self.N, **{k: v})))
    def test_absent_trial_record_is_held_and_no_naming_trial_is_not_checked(self):
        self.assertIn(IDENTITY, self.gate({})); self.assertNotIn(IDENTITY, self.gate(None))
    def test_no_reference_keeps_its_own_reason_only(self):
        why = self.gate(dict(self.N), records=[{'marked': True, 'native': self.N}]); self.assertIn('neutrality: no unmarked reference render of this state', why); self.assertNotIn(IDENTITY, why)


if __name__ == '__main__':
    unittest.main()
