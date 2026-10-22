# Ported to the normal suite from context_candidate/tests_snapshot_20261022T0237_final/test_replacement.py (sha256 cb323b952133838770fca584aa216b8d8b5bbbd6360f6ea9e3d4cdb4bd671b49). Test bodies unchanged; mechanical change only:
# fixtures from this directory's cases.py and test_inner.py instead of runpy (BUTTON from test_context_states.py unless cases.py defines it).
"""Exact already-qualified state for a clean repeat replacement (Root CONTEXT_EXACT_STATE_REPLACEMENT_DECISION_20261022). Invented public fixture: the
parent's MuseumCards.reveal removes its previous copy and appends a fresh native clone. Positive: the outer control again on its shown copy (also after an
inner action) is accepted as a replacement only when every native fact holds (one new root of the same origin in the same place, the old copy and only it
removed, children equal to the origin and to the inert source parse, only already-received GET inputs, settled, error-free), and in the state loop it is
an edge to the already-qualified first state with new-instance lineage (same_instance False), the document OK. Negatives (the parent's own script
changed for the second reveal only): changed text, another source target, unrelated removed content, a new input, a script error: each refused with the
failing fact. Same-instance reopen (FieldStation, same node) stays covered by test_conditional_fixture.
Run: CANDIDATE_RUNTIME=<runtime> python -I -B test_replacement.py"""
import json, unittest
from pathlib import Path
from . import cases; g = dict(vars(cases)); g.setdefault('BUTTON', 'context: 1 declared event handler(s) outside the supported link path (not activated)')  # BUTTON: test_context_states.py's exact constant unless cases.py defines it
from . import test_inner; i = vars(test_inner)
context, sg, rep, ANON, PANELS, PNG, controls, activations = (g[k] for k in ('context', 'sg', 'rep', 'ANON', 'PANELS', 'PNG', 'controls', 'activations'))
CHILD_INNER, inner_links = i['CHILD_INNER'], i['inner_links']
ONCE = b"copy.removeAttribute('id');"
def second(js): return rep(PANELS, ONCE, ONCE + b' if (this.last) { ' + js + b' }')  # the parent's script changed for the second reveal only
CHANGED, OTHER = second(b"copy.querySelector('p').textContent = 'Changed text.';"), rep(PANELS, b"const target = document.getElementById(targetId);", b"const target = document.getElementById(this.last ? 'note-indigo' : targetId);")
UNRELATED, NEWINPUT = second(b"document.querySelector('h1').remove();"), second(b"copy.appendChild(Object.assign(document.createElement('img'), {src: 'other.png'}));")
ERROR = rep(PANELS, b'this.last = copy;', b'if (this.last) { this.last = copy; throw new Error(\'second reveal failed\'); } this.last = copy;')


def render(browser, child, seq, panels=PANELS):  # one Context render of the sequence; (record, refusal)
    ev = g['evidence'](child=child, panels=panels); ctx = context.Context(ev, control=seq, label='replacement'); err = None
    page = ctx.page(browser, None, ('https://trial.invalid/', child), context.state_source(sg.Source('child.html', {'child.html': child, 'plan.png': PNG}), ev, ctx))
    try: page.goto('trial')
    except context.Refused as e: err = str(e)
    finally: page.close()
    return ctx.records[0], err


class Replacement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch(); cls.outer = controls(ANON)[0]
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def test_clean_repeat_is_a_qualified_replacement(self):
        r, err = render(self.browser, ANON, (self.outer, self.outer)); self.assertIsNone(err, err); last = r['inner'][-1]
        self.assertTrue(last['replacement'] and all(last['replacement'].values()), last.get('replacement')); self.assertEqual((last['probe']['new_roots'], last['copy_shown_after']), (1, True))

    def test_after_an_inner_action(self):
        outer, toggle = controls(CHILD_INNER)[0], inner_links(CHILD_INNER)[0]
        r, err = render(self.browser, CHILD_INNER, (outer, toggle, outer)); self.assertIsNone(err, err); self.assertTrue(all(r['inner'][-1]['replacement'].values()))

    def test_negatives_are_refused_with_the_failing_fact(self):
        for name, panels, fact in (('changed text', CHANGED, 'children_equal'), ('another source target', OTHER, 'same_origin'), ('unrelated removed content', UNRELATED, 'old_copy_removed_only'),
                                   ('a new input', NEWINPUT, 'inputs_already_received'), ('a script error', ERROR, 'script error')):
            with self.subTest(case=name):
                r, err = render(self.browser, ANON, (self.outer, self.outer), panels); self.assertIsNotNone(err, name); self.assertIn(fact, err)

    def test_state_loop_edge_to_the_qualified_first_state(self):
        res = g['run'](self.browser, ANON); self.assertEqual((res['initial']['status'], res['initial'].get('error')), ('PARTIAL', g['BUTTON']))
        graph = next(a['state_graph'] for a in activations(res, self.outer) if a.get('state_graph'))
        e = [x for x in graph['edges'] if x['control'] == self.outer]; self.assertTrue(e, json.dumps(graph)[:400])
        self.assertEqual({(x['kind'], x['to'], x['lineage']['same_instance'], bool(x['lineage']['replacements'])) for x in e}, {('equal state', f'activated@{self.outer}', False, True)})
        self.assertNotIn('not_attempted', graph); self.assertEqual(graph['frontier'], [])

if __name__ == '__main__':
    unittest.main()
