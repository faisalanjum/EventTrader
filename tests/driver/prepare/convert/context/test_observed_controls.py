# Ported to the normal suite from context_candidate/tests/test_observed_controls.py (sha256 8f6874dab952537e8277df792be4e952942137ca9ec2e131022c6fc988177a79). Test bodies unchanged; mechanical change only: fixtures from
# this directory's cases.py (byte-identical fixture files, same PNG, same run() path when context is present) instead of runpy(test_context_states.py).
"""observed_controls (OBSERVED_CONTROLS_CONTRACT_v2_20261022; Root CONTEXT_OBSERVED_CONTROL_CONTRACT_REVIEW_20261022): inner source-owned controls that
replace their own label (text only; their element structure stays, as the inner-action rules require) inside the revealed target of the invented
public fixture. (a) a label in the middle of a sentence owns only its slice; (b) two controls in one paragraph: each state's record owns its own,
non-overlapping slice of the same unit; (c) a label split over two block elements; (d) a control that hides itself is incomplete; the initial route has
no record and every unit keeps its saved source text.
Run: CANDIDATE_RUNTIME=<runtime> python -I -B test_observed_controls.py"""
import json, unittest
from pathlib import Path
from driver.prepare.convert import html_route
from . import cases; g = dict(vars(cases), html_route=html_route)
rep, run, controls, ANON, RICH, state, sg = g['rep'], g['run'], g['controls'], g['ANON'], g['RICH'], g['state'], g['sg']
SET = lambda text: b"this.textContent = '" + text + b"';"
INNER = (b'<aside class="museum-note" id="note-amber"><p>Use the east stair.</p>\n'
         b'<p>Before the <a href="javascript:void(0)" onclick="' + SET(b'Close notes') + b'">Open notes</a> and after.</p>\n'
         b'<p><a href="javascript:void(0)" onclick="' + SET(b'Close maps') + b'">Open maps</a> and <a href="javascript:void(0)" onclick="' + SET(b'Close counts') + b'">Open counts</a></p>\n'
         b'<div><a href="javascript:void(0)" onclick="this.children[0].textContent = \'Shut\';"><div>Show</div><div>floors</div></a></div>\n'
         b'<p><a href="javascript:void(0)" onclick="this.textContent = \'Gone\'; this.style.display = \'none\';">Hide me</a></p></aside>')
CHILD = rep(ANON, RICH, INNER)
LINKS = sg.Visible(CHILD).links
def at(text): return next(l['start'] for l in LINKS if CHILD[l['tag_end']:l['end']] == text)
def record(res, start):
    for s in res['states']:
        for o in s['route'].get('observed_controls') or []:
            if o['control'] == start: return s, o
    return None, None
def slices(route, o):
    units = {u['id']: u for u in route['units']}
    return [units[w['unit']]['text'][a:b] for w in o['owners'] for a, b in w['text_at']]


class ObservedControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch(); cls.res = run(cls.browser, CHILD)
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def test_initial_route_has_no_record(self): self.assertNotIn('observed_controls', self.res['initial'])

    def test_a_label_inside_a_sentence_owns_only_its_slice(self):
        s, o = record(self.res, at(b'Open notes')); self.assertIsNotNone(o, json.dumps([x['label'] for x in self.res['states']]))
        self.assertEqual((o['status'], o['owners_by'], o['original']['label'], o['observed']['label']), ('complete', 'action', 'Open notes', 'Close notes'), json.dumps(o)[:400])
        self.assertEqual(slices(s['route'], o), ['Open notes']); unit = next(u for u in s['route']['units'] if u['id'] == o['owners'][0]['unit'])
        self.assertIn('Before the Open notes and after.', unit['text'])  # the saved unit text keeps its source text, words around the label included

    def test_two_controls_in_one_paragraph_each_own_their_slice(self):
        (s1, o1), (s2, o2) = record(self.res, at(b'Open maps')), record(self.res, at(b'Open counts'))
        self.assertTrue(o1 and o2); self.assertNotEqual(s1['label'], s2['label'])
        self.assertEqual((slices(s1['route'], o1), slices(s2['route'], o2)), (['Open maps'], ['Open counts']))
        self.assertEqual(o1['owners'][0]['unit'], o2['owners'][0]['unit'])  # one unit, two records
        (a1, b1), (a2, b2) = o1['owners'][0]['text_at'][0], o2['owners'][0]['text_at'][0]; self.assertTrue(b1 <= a2 or b2 <= a1)  # never overlapping

    def test_a_label_split_over_two_blocks(self):
        s, o = record(self.res, at(b'<div>Show</div><div>floors</div>')); self.assertIsNotNone(o)
        self.assertEqual(o['status'], 'complete', json.dumps(o)[:400]); self.assertEqual(' '.join(slices(s['route'], o)).split(), ['Show', 'floors'])

    def test_a_control_that_hides_itself_is_incomplete(self):
        s, o = record(self.res, at(b'Hide me')); self.assertIsNotNone(o)
        self.assertEqual(o['status'], 'incomplete'); self.assertIn('control not shown in the final state', o['reasons'])

TOGGLE = (b'<aside class="museum-note" id="note-amber"><p>Use the east stair.</p>\n<p>See <a href="javascript:void(0)" onclick="this.textContent = '
          b"this.textContent === 'Open notes' ? 'Close notes' : 'Open notes';" b'">Open notes</a> here.</p></aside>')
TOGGLE_CHILD = rep(ANON, RICH, TOGGLE)


class RepeatedOccurrence(unittest.TestCase):  # Root CONTEXT_FINAL_SAVED_STATE_BOUNDARY: a repeated control binds its exact final occurrence
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()
    def record(self, seq):
        context, html_route, hashlib = g['context'], g['html_route'], g['hashlib']; ev = g['evidence'](child=TOGGLE_CHILD)
        ctx = context.Context(ev, control=seq, label='activated@' + '+'.join(map(str, seq)))
        src = context.state_source(sg.Source('child.html', {'child.html': TOGGLE_CHILD, 'plan.png': g['PNG']}), ev, ctx)
        route, _ = html_route.prepare(TOGGLE_CHILD, 'invented/toggle.html', hashlib.sha256(TOGGLE_CHILD).hexdigest(), self.browser, src)
        context.observed_controls(TOGGLE_CHILD, route, ctx); return route['observed_controls'][0]
    def test_reverse_toggle_binds_the_final_occurrence(self):
        outer = controls(TOGGLE_CHILD)[0]; c = next(l['start'] for l in sg.Visible(TOGGLE_CHILD).links if TOGGLE_CHILD[l['tag_end']:l['end']] == b'Open notes')
        once, twice = self.record((outer, c)), self.record((outer, c, c))
        self.assertEqual((once['original']['label'], once['observed']['label'], once['lineage']['action_index']), ('Open notes', 'Close notes', 1))
        self.assertEqual((twice['original']['label'], twice['observed']['label'], twice['lineage']['action_index']), ('Open notes', 'Open notes', 2))
        self.assertEqual([(o['action_index'], o['before'], o['after']) for o in twice['lineage']['occurrences']], [(1, 'Open notes', 'Close notes'), (2, 'Close notes', 'Open notes')])
        self.assertEqual((once['status'], twice['status']), ('complete', 'complete'))

FINAL = (b'<aside class="museum-note" id="note-amber"><p>Saved instructions.</p><p><a href="javascript:void(0)" onclick="this.textContent=\'Hide notes\'">Show notes</a>'
         b'<a href="javascript:void(0)" onclick="this.parentElement.firstElementChild.style.display=\'none\'">Hide first control</a>'
         b'<a href="javascript:void(0)" onclick="this.parentElement.firstElementChild.style.display=\'\'">Show first control</a></p></aside>')
FINAL_CHILD = rep(ANON, RICH, FINAL)


class FinalObservation(unittest.TestCase):  # Root CONTEXT_FINAL_NATIVE_OBSERVATION_CONTRACT_20261022: published label/visibility = the final state; actions stay raw history
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()
    def record(self, *texts):
        context, html_route, hashlib = g['context'], g['html_route'], g['hashlib']; ev = g['evidence'](child=FINAL_CHILD); links = sg.Visible(FINAL_CHILD).links
        seq = (controls(FINAL_CHILD)[0],) + tuple(next(l['start'] for l in links if FINAL_CHILD[l['tag_end']:l['end']] == t) for t in texts)
        ctx = context.Context(ev, control=seq, label='activated@' + '+'.join(map(str, seq)))
        src = context.state_source(sg.Source('child.html', {'child.html': FINAL_CHILD, 'plan.png': g['PNG']}), ev, ctx)
        route, _ = html_route.prepare(FINAL_CHILD, 'invented/final.html', hashlib.sha256(FINAL_CHILD).hexdigest(), self.browser, src)
        context.observed_controls(FINAL_CHILD, route, ctx); o = route['observed_controls'][0]; self.ctx, self.route = ctx, route
        fin = ctx.records[o['lineage']['render']]['final_controls'][0]  # the render's own final reading of the first acted control
        self.assertEqual((o['observed']['label'], o['observed']['shown']), (fin['label'], fin['shown']))  # published = that final reading, never a historical one
        self.assertEqual([(x['action_index'], x['before'], x['after'], x['shown']) for x in o['lineage']['occurrences']], [(1, 'Show notes', 'Hide notes', True)])  # raw history unchanged
        lr = next(l for l in route['source_links'] if l['tag']['byte_start'] == o['control']); self.assertEqual(o['extent']['byte_start'], o['control'])  # the link record's own extent
        if o['status'] == 'complete': self.assertEqual((lr['extent'], lr['owners'], lr.get('owners_by')), (o['extent'], o['owners'], 'action'))  # one owner result, stated as action evidence
        else: self.assertEqual((lr['extent'], lr['owners'], lr.get('owners_by')), (None, None, None))  # a hidden or unowned label: the link record stays unproved
        return o
    def test_unchanged_positive(self):
        o = self.record(b'Show notes'); self.assertEqual((o['observed']['label'], o['observed']['shown'], o['status']), ('Hide notes', True, 'complete'))
    def test_a_later_action_hides_the_changed_control(self):
        o = self.record(b'Show notes', b'Hide first control'); self.assertEqual((o['observed']['label'], o['observed']['shown'], o['status']), ('Hide notes', False, 'incomplete'))
        self.assertIn('control not shown in the final state', o['reasons'])
    def test_a_later_action_shows_it_again(self):
        o = self.record(b'Show notes', b'Hide first control', b'Show first control'); self.assertEqual((o['observed']['label'], o['observed']['shown'], o['status']), ('Hide notes', True, 'complete'))
    def test_corrupt_final_reading_is_never_shown(self):  # a missing or mismatched final reading: incomplete, never a historical value in its place
        o = self.record(b'Show notes'); context = g['context']
        for bad in (None, [], [{'label': 'Hide notes', 'shown': True}] * 2):
            with self.subTest(final=bad):
                r = self.ctx.records[o['lineage']['render']]; keep = r.get('final_controls'); r['final_controls'] = bad; route = dict(self.route); route.pop('observed_controls', None)
                try: context.observed_controls(FINAL_CHILD, route, self.ctx)
                finally: r['final_controls'] = keep
                x = route['observed_controls'][0]; self.assertEqual((x['status'], x['observed']['label'], x['observed']['shown']), ('incomplete', None, False))
                self.assertIn('no final native reading of the control', x['reasons'])

if __name__ == '__main__':
    unittest.main()
