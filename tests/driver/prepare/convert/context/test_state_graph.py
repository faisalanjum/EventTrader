# Ported to the normal suite from context_candidate/tests/test_state_graph.py (sha256 a8fc48e043be638ec8e54fda6442c396088e88e474becd2a00efdb77592a0b8a). Test bodies unchanged; mechanical change only: fixtures from
# this directory's cases.py (byte-identical fixture files, same PNG, same run() path when context is present) instead of runpy(test_context_states.py).
"""The state loop's failed attempts (Root CONTEXT_RANGE_AND_STATE_IMPLEMENTATION_20261021: count no-ops and failed attempts, never silently complete;
OCR parent-acceptance review 2026-10-22 item (ii): a source-owned control whose action raises a page error is unknown or incomplete, never "no state").
Invented public fixture: inside the revealed target one control calls a function the page never defines (ReferenceError, no change), one changes its
own label and then calls it (a change plus an error), one only changes its label. The two erroring controls are refused with the page error as their
reason (the action rules' own 'script error'), from every state, and never become an equal or a new state; the clean control still builds its state;
a state render whose action raised a page error is refused and its gate says so.
Run: CANDIDATE_RUNTIME=<runtime> python -I -B test_state_graph.py"""
import json, unittest
from pathlib import Path
from . import cases; g = vars(cases)
rep, run, activations, ANON, RICH, sg, context = (g[k] for k in ('rep', 'run', 'activations', 'ANON', 'RICH', 'sg', 'context'))
INNER = (b'<aside class="museum-note" id="note-amber"><p>Use the east stair.</p>\n'
         b'<p><a href="javascript:void(0)" onclick="missingShow(this)">Open plan</a> and '
         b'<a href="javascript:void(0)" onclick="this.textContent = \'Shut maps\'; missingShow(this);">Open maps</a> and '
         b'<a href="javascript:void(0)" onclick="this.textContent = \'Close notes\';">Open notes</a></p></aside>')
CHILD = rep(ANON, RICH, INNER); LINKS = sg.Visible(CHILD).links
def at(text): return next(l['start'] for l in LINKS if CHILD[l['tag_end']:l['end']] == text)
PLAN, MAPS, NOTES = at(b'Open plan'), at(b'Open maps'), at(b'Open notes')


class PageErrors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch(); cls.res = run(cls.browser, CHILD)
        cls.outer = next(a for s in cls.res['states'] if isinstance(s['control'], int) for a in activations(cls.res, s['control']) if a.get('state_graph'))
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def test_an_erroring_control_is_refused_with_its_page_error(self):
        for c in (PLAN, MAPS):
            with self.subTest(control=c):
                a = activations(self.res, c); self.assertTrue(a, 'an attempted action keeps its record')
                self.assertEqual({x['status'] for x in a}, {'refused'}, json.dumps(a)[:500]); self.assertIn('script error', json.dumps(a[0]['reasons']))
                self.assertEqual([s['label'] for s in self.res['states'] if isinstance(s['control'], list) and s['control'][-1] == c], [])  # never a built state
                edges = [e for e in self.outer['state_graph']['edges'] if e['control'] == c]; self.assertTrue(edges)
                self.assertEqual({e['kind'] for e in edges}, {'refused'}, json.dumps(edges)[:500])  # never an equal or a new state

    def test_the_clean_control_builds_its_state_and_failures_are_counted(self):
        sg_ = self.outer['state_graph']; self.assertIn('new state', {e['kind'] for e in sg_['edges'] if e['control'] == NOTES})
        self.assertEqual(sg_['refused'], len([e for e in sg_['edges'] if e['kind'] == 'refused'])); self.assertGreaterEqual(sg_['refused'], 2)
        self.assertEqual(sg_['frontier'], [])

    def test_a_render_whose_action_raised_a_page_error_is_refused(self):
        ev = g['evidence'](child=CHILD); outer = int(self.outer['state'].split('@')[1]); ctx = context.Context(ev, control=(outer, MAPS), label='gate')
        page = ctx.page(self.browser, None, ('https://trial.invalid/', CHILD), context.state_source(sg.Source('child.html', {'child.html': CHILD}), ev, ctx))
        try: page.goto('trial')
        except context.Refused: pass  # the render itself refuses; its gate must name the cause
        finally: page.close()
        self.assertIn('script error', json.dumps(ctx.gate()))

if __name__ == '__main__':
    unittest.main()
