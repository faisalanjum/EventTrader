"""Test's independent public fixture (test_public/conditional_target_fixture_v1; pins checked) through the candidate boundary. Fixture addresses and
selectors here are test data, as in its probe; the runtime receives only recorded responses and source positions.
Run with the normal tests.driver.prepare suite."""
import hashlib, json, unittest
from pathlib import Path
from driver.prepare.convert import context, screen_grid as sg
C = Path(__file__).with_name('fixtures'); FX = C / 'conditional_target_fixture_v1'; V2 = C / 'public_parent_reference_controls_v2'
sha = lambda b: hashlib.sha256(b).hexdigest()
assert sha((FX / 'README.md').read_bytes()) == 'd67fd13254f9ae54714c64ab5356b50565d29d09328ddaaa609c1ab5ff156262' and sha((FX / 'EXPECTATIONS_BEFORE.json').read_bytes()) == '9fd570754e6cfcb2ef5eb523482135797ab3edfad880e1f326aeaff608d70dd2'
EXP = json.loads((FX / 'EXPECTATIONS_BEFORE.json').read_bytes())
CHILD, CTRL, CSS, PARENT, JQ = ((FX / 'child.html').read_bytes(), (FX / 'controller.js').read_bytes(), (FX / 'style.css').read_bytes(), (V2 / 'parent_ui.html').read_bytes(), (V2 / 'jquery.min.js').read_bytes())
PNG = (C / 'plan.png').read_bytes(); assert sha(PNG) == EXP['required_content']['picture']['sha256']
ROOT = 'https://station.invalid'
def obs(body, ctype, status=200): return {'status': status, 'content_type': ctype, 'observed_at': 'invented test evidence', 'sha256': sha(body), 'body': body}
def evidence(parent=PARENT, ctrl=CTRL):
    o = {ROOT + '/portal/select.html': obs(parent, 'text/html'), ROOT + '/bundle/welcome.html': obs(b'<section id="welcome-panel">Choose a station page.</section>', 'text/html'),
         ROOT + '/bundle/item.html': obs(CHILD, 'text/html'), ROOT + '/vendor/jquery.min.js': obs(JQ, 'application/javascript'), ROOT + '/shared/frame.css': obs(CSS, 'text/css'),
         ROOT + '/shared/panels.js': obs(ctrl, 'application/javascript'), ROOT + '/assets/public-plan.png': obs(PNG, 'image/png')}
    return {'parent_url': ROOT + '/portal/select.html', 'target_url': ROOT + '/bundle/item.html', 'observed': o, 'selection': {'source_anchor': 1}, 'proof': {'form': 'equal', 'inserted': []}}
# the probe's own negative transformations (test data)
import lxml.html as native_html
FOREIGN = native_html.tostring(native_html.fromstring(CHILD).get_element_by_id(EXP['declared_target']), encoding='utf-8', with_tail=False)
SHADOW = PARENT.replace(b'<div id="report-host"></div>', b'<div class="foreign-store" style="display:none">' + FOREIGN + b'</div><div id="report-host"></div>'); assert SHADOW != PARENT
DAMAGED = CTRL.replace(b"copy.removeAttribute('id');", b"copy.removeAttribute('id'); copy.querySelector('td.count').firstChild.nodeValue = '999';"); assert DAMAGED != CTRL
LINKS = sg.Visible(CHILD).links
def start(text): return next(l['start'] for l in LINKS if CHILD[l['tag_end']:l['end']] == text.encode())  # test data: a control by its authored text
OUTER, NOTES, COUNTS, OVERVIEW, CLOSE, GUIDE = start('Inspect specimen'), start('Open notes'), start('Open counts'), start('Overview'), start('Close panel'), start('Field guide')
def model(seq):  # the fixture's own semantics (test data, from controller.js): each group's style form, and whether the copy is closed
    f, closed = {NOTES: 'source', COUNTS: 'source'}, False
    for c in seq[1:]:
        if c in f: f[c] = 'none' if f[c] == 'block' else 'block'
        elif c == CLOSE: closed = True
        elif c == OUTER: closed = False
    return f[NOTES], f[COUNTS], closed
def run(browser, **kw):
    return context.contextual_routes(CHILD, 'invented/station/child.html', sha(CHILD), browser, sg.Source('child.html', {'child.html': CHILD}), evidence(**kw))
def acts(res, s): return next(l for l in res['initial']['source_links'] if l['tag']['byte_start'] == s).get('activations') or []
def state_route(res, label): return next(x['route'] for x in res['states'] if x['label'] == label)

class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def test_positive_states_and_complete_content_across_states(self):
        res = run(self.browser); outer = acts(res, OUTER); self.assertTrue(outer and outer[0]['state'], json.dumps(outer)[:500])
        o = outer[0]; self.assertEqual(o['target']['declared_id'], EXP['declared_target']); self.assertEqual(o['coverage_across_states']['never_affirmatively_shown_runs'], [], json.dumps(o['coverage_across_states'])[:400])
        notes, counts = acts(res, NOTES), acts(res, COUNTS)
        only = 'target descendants not shown or not proven in this state (listed in coverage)'  # the other independent group stays hidden in each single-toggle state
        for a in (notes[0], counts[0]): self.assertTrue(a['state'] and state_route(res, a['state'])['status'] == 'OK' and a['reasons'] == [only], json.dumps(a['reasons'])[:400])
        self.assertEqual(acts(res, OVERVIEW), [], 'an already-visible no-op gets no state')
        x0, x1 = o['target']['source_extent']['byte_start'], o['target']['source_extent']['byte_end_exclusive']
        texts = ' '.join(u.get('text') or ' '.join(c.get('text') or '' for c in u.get('cells') or []) for x in res['states'] for u in x['route']['units'] if u.get('anchor') and x0 <= (u['anchor'].get('byte_start') or -1) < x1)
        rc = EXP['required_content']
        for want in [rc['title'], rc['summary'], rc['notes'], rc['reference']['text'], rc['table']['caption']] + rc['ordered_list'] + rc['table']['headers'] + [v for row in rc['table']['rows'] for v in row]:
            self.assertIn(want, texts)
        close = acts(res, CLOSE); self.assertTrue(close and close[0].get('copy_shown_after') is False, json.dumps(close)[:400])
        g_ = o['state_graph']; self.assertEqual(g_['frontier'], []); seq = lambda lb: tuple(int(x) for x in lb.split('@')[1].split('+'))
        reopen = [e for e in g_['edges'] if e['control'] == OUTER and e['kind'] == 'equal state']  # Root: equal identity is an edge, never another extracted copy
        self.assertTrue(reopen and all(e['lineage']['same_instance'] for e in reopen), 'the same outer control reopens the same copy (node lineage, not a matching hash)')
        states = {lb: model(seq(lb)) for lb in g_['states']}; self.assertEqual(len(set(states.values())), len(states), states)  # one state per distinct configuration
        self.assertEqual(len(states), 18)  # 3 style forms per group (source / opened / closed again: the browser rewrites the attribute) x open or closed copy
        for e in g_['edges']:
            want = model(seq(e['from']) + (e['control'],))
            if e['kind'] in ('equal state', 'new state'): self.assertEqual(states[e['to']], want, e)
            elif e['kind'] == 'no-op': self.assertEqual(states[e['from']], want, e)
            else: self.assertEqual((e['kind'], e['control']), ('refused', GUIDE), e)  # only the ordinary external link: navigation, no conditional state
        shown = {(f[0] == 'block', f[1] == 'block', not f[2]) for f in states.values()}  # Test's prewritten configurations (acceptance example)
        for x in EXP['states'][1:]: self.assertIn((x['groups'][1], x['groups'][2], x['outer_shown']), shown, x['name'])
        for a in acts(res, NOTES) + acts(res, COUNTS):  # the acted control's own label follows its group
            c = a['state'].split('+')[-1]; f = states[a['state']][0 if int(c) == NOTES else 1]; word = 'notes' if int(c) == NOTES else 'counts'
            self.assertEqual(a['control_label']['after'], ('Close ' if f == 'block' else 'Open ') + word, a['state'])
        self.assertTrue(any(e['control'] == OVERVIEW and e['kind'] == 'no-op' for e in g_['edges']))  # visible_noop_00
        print('STATES', len(res['states']), 'TRIALS', len(res['trials']), 'EDGES', len(g_['edges']))

    def test_scope_negative_parent_owned_equal_target(self):
        a = acts(run(self.browser, parent=SHADOW), OUTER); self.assertTrue(a and a[0]['status'] != 'complete' and 'selected child' in json.dumps(a[0]), json.dumps(a)[:500])

    def test_content_negative_damaged_copy(self):
        a = acts(run(self.browser, ctrl=DAMAGED), OUTER); self.assertTrue(a and a[0]['status'] != 'complete', json.dumps(a)[:500])

    def test_close_and_same_node_reopen_preserves_groups(self):
        ev = evidence(); ctx = context.Context(ev, control=(OUTER, NOTES, COUNTS, CLOSE, OUTER), label='sequence')
        pg = ctx.page(self.browser, None, ('http://seq.invalid/', CHILD), context.state_source(sg.Source('child.html', {'child.html': CHILD}), ev, ctx))
        try:
            pg.goto('seq'); groups = pg.evaluate("() => Array.from(window.__copy.querySelectorAll('.sheet-body > div')).map(d => getComputedStyle(d).display !== 'none')")
            shown = pg.evaluate('() => window.__copy.checkVisibility()')
        finally: pg.close()
        r = ctx.records[0]; self.assertFalse(r.get('refused'), r.get('refused')); last = r['inner'][-1]
        self.assertEqual((last['probe']['new_roots'], last['copy_shown_after'], shown, groups), (0, True, True, [True, True, True]))
        self.assertEqual([i['label_after'] for i in r['inner'][:2]], ['Close notes', 'Close counts'])

class Identity(unittest.TestCase):  # Root's STATE_IDENTITY_RED: a state's identity owns its whole ordered action sequence
    def test_identity_keeps_the_ordered_sequence(self):
        ev = evidence(); a, b = (context.Context(ev, control=(OUTER, x)).identity() for x in (NOTES, COUNTS))
        self.assertNotEqual(a, b); self.assertEqual(a['controls'], [OUTER, NOTES])

if __name__ == '__main__':
    unittest.main()
