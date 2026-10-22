"""Local text proof, Boolean version (Root CONTEXT_LOCAL_PROOF_BOOLEAN_REVIEW_20261022T0956 on CONTEXT_LOCAL_PROOF_BUILD_20261022T0947), from Fable's
public reproduction (root_context_gate/local_proof_decision_20261022/fable_driver_helper). One unrelated background picture (outside the target, no
text) must not withhold a natively proved final control label or a target run a state route holds; every text-proof failure and every native state
failure still must, in BOTH local readers (observed_controls and coverage_across_states), with the aggregate route/activation status unchanged.
ChangedApi: the new fields and the renamed reason. Behaviour: what the readers compose or refuse (no new field names asserted there).
Fixtures: tests/driver/prepare/convert/context (cases; test_observed_controls FINAL_CHILD / TOGGLE_CHILD); test_source_style.src. Expected labels come
from the fixtures' authored onclick text. Runtime under test: the normal driver.prepare imports."""
import copy, hashlib, unittest
from driver.prepare.convert import context, html_route, screen_grid as sg
from driver.prepare import reconstruct
from tests.driver.prepare.convert.context import cases
from tests.driver.prepare.convert.context import test_observed_controls as T
from tests.driver.prepare.convert.test_source_style import src

BG = b'<div id="paper-texture" style="width:16px;height:16px;background-image:url(plan.png)"></div>'  # unrelated: outside the target, no text
warn = lambda child: cases.rep(child, b'<section id="native-note">', BG + b'<section id="native-note">')
RANDOM = cases.rep(T.FINAL_CHILD, b"this.textContent='Hide notes'", b"this.textContent='Hide '+Math.random()")  # native mutation: each render writes another label
PICTURE = 'screen step: generated: background image content not read'
GIF = b'data:image/gif;base64,R0lGODlhAQABAAAAACw='
PIC = b'<div style="width:9px;height:9px;background-image:url(' + GIF + b')"></div>'  # test_source_style's own unread-picture case
NEGATIVE = (('missing stylesheet', PIC + b'<link rel="stylesheet" href="missing.css"><p class="x">distant shore</p>'),
            ('generated non-text', PIC + b'<style>p::before{content:url(' + GIF + b')}</style><p>Body</p>'),
            ('first-letter strike not carried', PIC + b'<style>p::first-letter{text-decoration:line-through}</style><p>Body</p>'),
            ('first-letter paint unproved', PIC + b'<style>p::first-letter{color:transparent}</style><p>Body</p>'),
            ('generated text without owner text', PIC + src('generated_empty_owner')))
def failing_parse(raw, vis): raise RuntimeError('deliberate parse failure (control)')  # convert's own FAILED route
def late(route, s, label):  # the caller's per-state picture step, one render of it refused (native_one_document_v6 per_prepare position)
    if s.context.control is not None: s.context.records.append({'refused': 'late picture-step render refused (control)'})


def composed(route):  # body nodes composing an observed_controls record in the readback, and the observed_controls unknowns
    R = reconstruct.readback(route); out = []
    def walk(n):
        if isinstance(n, dict):
            if 'observed_controls' in (n.get('attached') or {}): out.append(n['attached']['observed_controls'])
            for v in n.values(): walk(v)
        elif isinstance(n, list):
            for v in n: walk(v)
    walk(R.get('sequence')); return out, [u for u in R['unknowns'] if isinstance(u, dict) and u.get('family') == 'observed_controls']


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.b = cls.pw.chromium.launch()
        assert b"this.textContent='Hide notes'" in T.FINAL_CHILD  # the authored final label
    @classmethod
    def tearDownClass(cls): cls.b.close(); cls.pw.stop()

    def state(self, child, texts, **kw):  # one acted state of the public fixture through the live producer and reader
        ev = cases.evidence(child=child); links = sg.Visible(child).links
        seq = (cases.controls(child)[0],) + tuple(next(l['start'] for l in links if child[l['tag_end']:l['end']] == t) for t in texts)
        ctx = context.Context(ev, control=seq, label='activated@' + '+'.join(map(str, seq)))
        s = context.state_source(sg.Source('child.html', {'child.html': child, 'plan.png': cases.PNG}), ev, ctx)
        route, facts = html_route.prepare(child, 'invented/final.html', hashlib.sha256(child).hexdigest(), self.b, s, **kw)
        pre = copy.deepcopy(route); context.observed_controls(child, route, ctx)
        return ctx, pre, route, facts

    def damaged(self, child, ctx, pre, edit_ctx=None, edit_route=None):  # one record-level damage on copies, then the same live reader
        c2 = copy.copy(ctx); c2.records = copy.deepcopy(ctx.records); r2 = copy.deepcopy(pre)
        if edit_ctx: edit_ctx(c2)
        if edit_route: edit_route(r2)
        context.observed_controls(child, r2, c2); return r2

    def run_states(self, child, prepare=None):  # the real contextual_routes, optionally with a caller step
        sha = hashlib.sha256(child).hexdigest()
        return context.contextual_routes(child, 'invented/child.html', sha, self.b, sg.Source('child.html', {'child.html': child, 'plan.png': cases.PNG}),
                                         cases.evidence(child=child), **({'prepare': prepare} if prepare else {}))

    def one(self, route):
        (o,) = route['observed_controls']; return o

    def never(self, res):
        acts = [a for l in res['initial']['source_links'] for a in l.get('activations') or [] if 'coverage_across_states' in a]
        self.assertTrue(acts); return [a['coverage_across_states']['never_affirmatively_shown_runs'] for a in acts]


class Behaviour(Base):
    def test_label_composed_despite_unrelated_picture(self):
        for name, child in (('healthy', T.FINAL_CHILD), ('unrelated picture', warn(T.FINAL_CHILD))):
            with self.subTest(name):
                _, _, route, _ = self.state(child, [b'Show notes']); o = self.one(route)
                self.assertEqual((o['status'], o['reasons'], o['observed']['label'], o['observed']['shown']), ('complete', [], 'Hide notes', True))
                lr = next(l for l in route['source_links'] if l['tag']['byte_start'] == o['control'])
                self.assertEqual((lr.get('extent'), lr.get('owners_by')), (o['extent'], 'action'))
                self.assertEqual([len(x) for x in [composed(route)[0]]] + [len(composed(route)[1])], [1, 0])
                if name != 'healthy': self.assertEqual((route['status'], route['error']), ('PARTIAL', PICTURE))  # aggregate unchanged

    def test_target_runs_shown_despite_unrelated_picture(self):
        for name, child in (('healthy', T.TOGGLE_CHILD), ('unrelated picture', warn(T.TOGGLE_CHILD))):
            with self.subTest(name):
                res = self.run_states(child); n = self.never(res); self.assertEqual(n, [[] for _ in n])
                if name != 'healthy':  # aggregate: every state route, activation and the initial view keep the picture error
                    self.assertEqual({s['route']['error'] for s in res['states']}, {PICTURE})
                    self.assertEqual(res['initial']['status'], 'PARTIAL'); self.assertIn(PICTURE, res['initial']['error'])
                    self.assertTrue(all(PICTURE in a['reasons'] and a['status'] == 'incomplete' for l in res['initial']['source_links'] for a in l.get('activations') or [] if a.get('state')))

    def test_native_state_failures_block(self):
        def disagree(c):
            m = next(i for i, r in enumerate(c.records) if r.get('marked') and r.get('native')); k = next(iter(c.records[m]['native']))
            c.records[m]['native'] = dict(c.records[m]['native'], **{k: 'damaged'})
        def refuse(c): c.records[0]['refused'] = 'damaged: refused render'
        def lost(c): c.records[0].pop('native', None)
        for name, child in (('healthy', T.FINAL_CHILD), ('unrelated picture', warn(T.FINAL_CHILD))):
            ctx, pre, _, _ = self.state(child, [b'Show notes'])
            for dname, edit in (('native disagreement', disagree), ('refused render', refuse), ('render without native record', lost)):
                with self.subTest(name + ': ' + dname):
                    r2 = self.damaged(child, ctx, pre, edit_ctx=edit); o = self.one(r2)
                    self.assertEqual(o['status'], 'incomplete'); self.assertTrue(any(w.startswith('render ') or w.startswith('neutrality') for w in o['reasons']))
                    self.assertEqual(composed(r2)[0], [])
        for name, child in (('native mutation', RANDOM), ('native mutation + picture', warn(RANDOM))):  # live: renders read different labels
            with self.subTest(name):
                _, _, route, _ = self.state(child, [b'Show notes']); self.assertEqual(self.one(route)['status'], 'incomplete'); self.assertEqual(composed(route)[0], [])

    def test_label_damage_blocks_with_picture(self):
        W = warn(T.FINAL_CHILD)
        _, _, route, _ = self.state(W, [b'Show notes', b'Hide first control'])  # hidden control: the healthy state's own reasons
        self.assertEqual((self.one(route)['status'], self.one(route)['reasons']), ('incomplete', ['control not shown in the final state', 'the label is not owned whole: not every character held']))
        ctx, pre, _, _ = self.state(W, [b'Show notes'])
        def drop_final(c):
            for r in c.records: r.pop('final_controls', None)
        o = self.one(self.damaged(W, ctx, pre, edit_ctx=drop_final)); self.assertEqual((o['status'], o['reasons']), ('incomplete', ['control not shown in the final state', 'no final native reading of the control']))
        def change_final(c):
            for r in c.records:
                if isinstance(r.get('final_controls'), list) and r['final_controls']: r['final_controls'][0] = dict(r['final_controls'][0], label='Hide notes (changed)')
        got, unknown = composed(self.damaged(W, ctx, pre, edit_ctx=change_final))  # existing reconstruction binding refuses it
        self.assertEqual((got, [u['why'] for u in unknown]), ([], ['observed label is not the last recorded change']))
        def drop_owner(r): r['units'] = [u for u in r['units'] if 'Show notes' not in (u.get('text') or '')]
        o = self.one(self.damaged(W, ctx, pre, edit_route=drop_owner)); self.assertEqual(o['status'], 'incomplete'); self.assertTrue(o['reasons'][0].startswith('the label is not owned whole'))

    def test_failed_conversion_blocks(self):
        for name, child in (('healthy', T.FINAL_CHILD), ('unrelated picture', warn(T.FINAL_CHILD))):
            with self.subTest(name):
                _, _, route, facts = self.state(child, [b'Show notes'], parse=failing_parse)
                self.assertEqual((route['status'], facts), ('FAILED', {})); o = self.one(route)
                self.assertEqual(o['status'], 'incomplete'); self.assertEqual(composed(route)[0], [])

    def test_missing_proof_blocks_without_status_fallback(self):
        for name, child in (('healthy', T.FINAL_CHILD), ('unrelated picture', warn(T.FINAL_CHILD))):
            ctx, pre, _, _ = self.state(child, [b'Show notes'])
            for dname, edit in (('proof removed', lambda r: r.pop('text_proved', None)), ('proof removed, status OK', lambda r: (r.pop('text_proved', None), r.update(status='OK', error=None)))):
                with self.subTest(name + ': ' + dname):
                    r2 = self.damaged(child, ctx, pre, edit_route=edit); self.assertEqual(self.one(r2)['status'], 'incomplete'); self.assertEqual(composed(r2)[0], [])

    def test_late_gate_blocks_both_readers(self):  # a picture-step render refused after prepare: labels and target runs are not proved
        for name, child in (('healthy', T.FINAL_CHILD), ('unrelated picture', warn(T.FINAL_CHILD))):
            with self.subTest(name):
                plain, hooked = self.run_states(child), self.run_states(child, prepare=late)
                self.assertEqual([(s['route']['status'], s['route']['error']) for s in hooked['states']], [(s['route']['status'], s['route']['error']) for s in plain['states']])  # status/error untouched here
                self.assertTrue(all(o['status'] == 'incomplete' for s in hooked['states'] for o in s['route'].get('observed_controls') or []))
                self.assertTrue(any(s['route'].get('observed_controls') for s in hooked['states']))
                self.assertTrue(all(n for n in self.never(hooked)))  # every target's runs: none affirmatively shown
                self.assertEqual([n for n in self.never(plain)], [[] for _ in self.never(plain)])


class ChangedApi(Base):
    def test_producer_fields(self):
        def prep(raw): return html_route.prepare(raw, 's.htm', hashlib.sha256(raw).hexdigest(), self.b)
        r, f = prep(PIC + b'<p>Body</p>')  # the unread picture alone: every stage proves its text
        self.assertEqual((r['status'], r['error'], r['generated_content']['text_proved'], f['screen']['text_proved'], r['text_proved']), ('PARTIAL', PICTURE, True, True, True))
        r, f = prep(b'<p>Body</p>')
        self.assertEqual((r['status'], r['generated_content']['text_proved'], f['screen']['text_proved'], r['text_proved']), ('OK', True, True, True))
        for name, raw in NEGATIVE:
            with self.subTest(name):
                r, f = prep(raw); self.assertEqual((r['status'], r['text_proved']), ('PARTIAL', False))
                self.assertIs(f['screen']['text_proved'], False)
                if name != 'missing stylesheet': self.assertIs(r['generated_content']['text_proved'], False)  # the generated stage refuses it
        r, f = html_route.prepare(PIC, 's.htm', hashlib.sha256(PIC).hexdigest(), self.b, parse=failing_parse)
        self.assertEqual((r['status'], 'text_proved' in r, f), ('FAILED', False, {}))  # a failed conversion carries no proof

    def test_state_fields_and_reason(self):
        _, _, route, _ = self.state(warn(T.FINAL_CHILD), [b'Show notes']); self.assertIs(route['text_proved'], True)
        _, _, route, _ = self.state(warn(RANDOM), [b'Show notes']); self.assertIs(route['text_proved'], False)  # the context list fails it
        self.assertIn('state route text not proved', self.one(route)['reasons'])
        ctx, pre, _, _ = self.state(warn(T.FINAL_CHILD), [b'Show notes'])
        r2 = self.damaged(warn(T.FINAL_CHILD), ctx, pre, edit_route=lambda r: r.pop('text_proved'))
        self.assertEqual(self.one(r2)['reasons'], ['state route text not proved'])
        hooked = self.run_states(warn(T.FINAL_CHILD), prepare=late)  # revoked after the caller step
        self.assertEqual({s['route'].get('text_proved') for s in hooked['states']}, {False})
        plain = self.run_states(warn(T.FINAL_CHILD)); self.assertEqual({s['route'].get('text_proved') for s in plain['states']}, {True})

    def test_shared_helper(self):
        ok = context.Context(cases.evidence(child=T.FINAL_CHILD))  # no renders: its gate says why
        self.assertTrue(context.text_proof({'status': 'OK', 'text_proved': True}, ok))  # the gate alone blocks
        for rt in ({'status': 'OK'}, {'status': 'OK', 'text_proved': None}, {'status': 'PARTIAL', 'text_proved': 1}, {'status': 'FAILED', 'error': 'x'}):
            with self.subTest(rt): self.assertIn('state route text not proved', context.text_proof(rt, ok))


if __name__ == '__main__':
    unittest.main(verbosity=2)
