"""Source-owned content, relationships, placement and refusals in an observed parent."""
import hashlib
import json
import unittest
from .cases import (ANON, CHILD, CLONE, CSS, INDIGO, PANELS, PARENT_UI, PNG, RICH, ROOT,
                    activations, context, controls, evidence, rep, run, sg, state, units_in)

class ContextStates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def check_positive(self, child):
        res = run(self.browser, child); a0, a1 = (activations(res, s) for s in controls(child))
        self.assertEqual([len(a0), len(a1)], [1, 1], 'each source control carries one labelled conditional activation')
        for a, tid in ((a0[0], 'note-amber'), (a1[0], 'note-indigo')):
            self.assertEqual((a['status'], a['target']['declared_id']), ('complete', tid))
            st = state(res, a['state']); self.assertEqual(st['route']['status'], 'OK')
            got = units_in(st['route'], a['target']['source_extent']); self.assertEqual(sorted({p['unit'] for p in a['participants']}), sorted(u['id'] for u in got))  # cells are referenced per cell (review item 4)
            self.assertEqual(a['placement']['previous_sibling_is_control'], True)
        amber = units_in(state(res, a0[0]['state'])['route'], a0[0]['target']['source_extent'])
        self.assertEqual([u['kind'] for u in amber], ['text', 'text', 'list_item', 'list_item', 'table', 'image'])
        self.assertEqual(amber[5]['input'].get('how') if 'input' in amber[5] else 'not prepared', 'not prepared')  # pictures are prepared by the caller (inputs.prepare), per state
        inner = [l for l in state(res, a0[0]['state'])['route']['source_links'] if l['href'] == '#native-note' and a0[0]['target']['source_extent']['byte_start'] <= l['tag']['byte_start'] < a0[0]['target']['source_extent']['byte_end_exclusive']]
        self.assertEqual(len(inner), 1); self.assertTrue(inner[0]['owners'], "the target's own link is owned in the revealed state")
        self.assertTrue(all(l['owners'] for l in res['initial']['source_links'] if not l.get('hidden')), 'shown source links are owned in the parent context')
        return res

    def test_missing_connection_two_targets(self): self.check_positive(CHILD)
    def test_anonymous_controls(self): self.check_positive(ANON)
    def test_reordered_targets(self): self.check_positive(rep(rep(rep(ANON, RICH, b'\x00'), INDIGO, RICH), b'\x00', INDIGO))

    def test_inherited_meaningful_formatting(self):
        css = CSS + b'\n#map-card .museum-note p { font-style: italic; }\n'
        res = run(self.browser, ANON, css=css); a = activations(res, controls(ANON)[0])[0]; route = state(res, a['state'])['route']
        ext = a['target']['source_extent']; recs = [r for r in route['source_style']['records'] if ext['byte_start'] <= r['at']['byte_start'] < ext['byte_end_exclusive']]
        italic = [r for r in recs if r['font_style'] == 'italic']
        self.assertTrue(italic and all(r['owners'] for r in italic), 'formatting inherited at the copy placement is measured and owned')

    def test_initial_selection_without_an_action(self):  # the parent's own initial load requests the target (OCR's native 'initial' outcome): no click
        init = rep(PARENT_UI, b"window.onload = function() { chooseSheet('welcome'); };", b"window.onload = function() { chooseSheet('board'); };")
        sha = hashlib.sha256(ANON).hexdigest(); ev = evidence(child=ANON, parent=init); ev['selection'] = {'initial': True}
        res = context.contextual_routes(ANON, 'invented/child.html', sha, self.browser, sg.Source('child.html', {'child.html': ANON, 'plan.png': PNG}), ev)
        a = activations(res, controls(ANON)[0]); self.assertTrue(a and a[0]['status'] == 'complete', json.dumps(a)[:400])

    def test_comment_sensitive_action_is_refused(self):
        branch = rep(PANELS, b'const target = document.getElementById(targetId);',
                     b"const target = document.getElementById(trigger.firstChild && trigger.firstChild.nodeType === 8 ? (targetId === 'note-amber' ? 'note-indigo' : 'note-amber') : targetId);")
        res = run(self.browser, ANON, panels=branch); a = activations(res, controls(ANON)[0])
        self.assertTrue(a and a[0]['status'] != 'complete', 'marks change the action: the state must not be complete')
        self.assertIn('neutrality', json.dumps(a[0]))

    def test_repeated_target(self):
        shared = rep(ANON, b"MuseumCards.reveal(this, 'note-indigo')", b"MuseumCards.reveal(this, 'note-amber')")
        res = run(self.browser, shared); a0, a1 = (activations(res, s)[0] for s in controls(shared))
        self.assertEqual((a0['status'], a1['status'], a0['target'], a1['target']), ('complete', 'complete', a1['target'], a0['target']))
        self.assertNotEqual(a0['state'], a1['state'], 'one reading per placement (no deduplication subsystem)')

    def refused(self, child=ANON, **kw):
        res = run(self.browser, child, **kw); a = activations(res, controls(child)[0])
        self.assertTrue(a and a[0]['status'] != 'complete', json.dumps(a)[:400]); return a[0]
    def test_copied_damage(self): self.refused(panels=rep(PANELS, CLONE, CLONE + b" { const ps = copy.querySelectorAll('p'); if (ps.length > 1) copy.insertBefore(ps[1], ps[0]); }"))
    def test_origin_damage(self): self.refused(panels=rep(PANELS, CLONE, b"target.querySelector('p').lastChild.textContent = 'A different instruction.'; " + CLONE))
    def test_other_effects_are_held(self): self.refused(panels=rep(PANELS, CLONE, CLONE + b" document.querySelector('#museum-board h1').appendChild(document.createTextNode(' Extra instruction.'));"))
    def test_ambiguous_double_insertion(self): self.refused(parent=rep(PARENT_UI, b"jQuery('#report-host').empty().append(data);", b"jQuery('#report-host').empty().append(data).append(data);"))
    def test_failed_resource_is_not_success(self):
        res = run(self.browser, ANON, drop=(ROOT + '/shared/panels.js',)); a = activations(res, controls(ANON)[0])
        self.assertTrue(not a or a[0]['status'] != 'complete'); self.assertIn(ROOT + '/shared/panels.js', json.dumps(res['initial'].get('resources')))

if __name__ == '__main__':
    unittest.main()
