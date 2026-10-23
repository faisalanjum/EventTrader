"""Initial-only contextual reading (Root FABLE_CORE_INITIAL_IMPLEMENT_20261023T1125). With report-control exploration disabled, the ONE context
boundary (`context.contextual_routes`) gives the selected initial view only: no source-control trial and no activated state; every declared scripted
action stays unresolved, so the document stays PARTIAL; non-link handlers, missing resources and native failures keep their own reasons; an
independently proved initial view keeps its own text proof; the default (full exploration) is unchanged; invalid option values are refused.
Expected values come from the fixture facts (cases: two visible javascript controls, one non-link handler, the evidence's resources)."""
import hashlib, unittest
from unittest import mock
from .cases import context, sg, evidence, controls, CHILD, PNG, BUTTON, ROOT, PANELS, rep

NOT_ATTEMPTED = 'not attempted: report-control exploration disabled'
HIDDEN_SCRIPTED = rep(CHILD, b'<a href="#native-note">see access</a>', b'<a href="javascript:void(0)" onclick="MuseumCards.reveal(this, \'note-indigo\')">see access</a>')
PLAIN = b'<!doctype html><html><head><title>Plain</title></head><body><p>Opening hours are posted here.</p></body></html>'
NO_HANDLER = rep(CHILD, b' onclick="document.body.classList.toggle(\'muted\')"', b'')  # the fixture without its non-link handler: its initial view can be proved
# Root FABLE_INITIAL_LINK_BOUNDARY_20261023T1210: plain source links (no inline declaration anywhere) whose action the PARENT owns (a delegated listener)
PLAIN_LINKS = rep(rep(NO_HANDLER, b'href="javascript:void(0)" onclick="MuseumCards.reveal(this, \'note-amber\')"', b'href="#note-amber"'),
                  b'href="javascript:void(0)" onclick="MuseumCards.reveal(this, \'note-indigo\')"', b'href="#note-indigo"')
PARENT_OWNED = PANELS + b"\ndocument.addEventListener('click', e => { const a = e.target.closest('#map-card a'); if (a) { e.preventDefault(); MuseumCards.reveal(a, 'note-amber'); } });\n"


def run(browser, child=CHILD, drop=(), panels=PANELS, **kw):  # the fixtures' own call (cases.run) with the option passed through to the one owner
    sha = hashlib.sha256(child).hexdigest()
    return context.contextual_routes(child, 'invented/child.html', sha, browser, sg.Source('child.html', {'child.html': child, 'plan.png': PNG}), evidence(child=child, drop=drop, panels=panels), **kw)


def attempted(res): return {t['controls'][0] for t in res['trials'] if not t.get('skipped')}


class InitialOnly(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
        cls.full = run(cls.browser)  # the default: full exploration, as before
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def test_existing_ceilings_do_not_stop_the_outer_trials(self):  # the demonstrated gap: zero ceilings still try every visible control
        res = run(self.browser, max_states=0, max_transitions=0)
        self.assertTrue(set(controls(CHILD)) <= attempted(res), attempted(res))

    def test_initial_only_attempts_no_report_control(self):
        res = run(self.browser, explore=False)
        self.assertEqual(res['states'], []); self.assertEqual(attempted(res), set()); self.assertEqual(res['trial_captures'], {})
        skipped = {t['controls'][0]: t['skipped'] for t in res['trials']}
        for c in controls(CHILD): self.assertEqual(skipped.get(c), NOT_ATTEMPTED)
        ini = res['initial']; self.assertEqual(ini['status'], 'PARTIAL')
        self.assertIn('context: %d declared script action(s) not attempted (report-control exploration disabled)' % len(controls(CHILD)), ini['error'])
        self.assertIn(BUTTON, ini['error'])  # the non-link handler keeps its own reason
        self.assertFalse(any(a for l in ini['source_links'] for a in l.get('activations') or []))  # no activation recorded

    def test_the_initial_view_and_its_proof_are_the_default_ones(self):  # deferral does not erase the initial view's own narrower proof
        res = run(self.browser, explore=False); a, b = res['initial'], self.full['initial']
        self.assertEqual(a['text_proved'], b['text_proved']); self.assertEqual(a['units'], b['units'])
        self.assertEqual(a.get('page_visibility'), b.get('page_visibility'))

    def test_a_proved_initial_view_keeps_its_proof(self):  # Root correction 4: the narrower proof stays; the aggregate stays PARTIAL
        a, b = run(self.browser, child=NO_HANDLER, explore=False)['initial'], run(self.browser, child=NO_HANDLER)['initial']
        self.assertIs(b['text_proved'], True, b.get('error'))  # control: the default proves this initial view
        self.assertIs(a['text_proved'], True, a.get('error')); self.assertEqual(a['status'], 'PARTIAL')
        self.assertEqual(a['error'], 'context: %d declared script action(s) not attempted (report-control exploration disabled)' % len(controls(NO_HANDLER)))

    def test_a_hidden_scripted_link_counts_and_is_never_attempted(self):
        res = run(self.browser, child=HIDDEN_SCRIPTED, explore=False)
        js = [l['start'] for l in sg.Visible(HIDDEN_SCRIPTED).links if l['href'].startswith('javascript:')]
        self.assertEqual(len(js), len(controls(CHILD)) + 1)  # fixture fact: one more scripted link, inside the hidden note
        self.assertIn('context: %d declared script action(s) not attempted' % len(js), res['initial']['error'])
        self.assertEqual(attempted(res), set()); self.assertEqual(res['states'], [])

    def test_a_page_without_declared_actions_is_unchanged(self):  # ordinary/no-action positive control
        a, b = run(self.browser, child=PLAIN, explore=False)['initial'], run(self.browser, child=PLAIN)['initial']
        self.assertNotIn('not attempted', a.get('error') or ''); self.assertEqual((a['status'], a.get('error'), a['text_proved']), (b['status'], b.get('error'), b['text_proved']))
        self.assertEqual((b['status'], b['text_proved']), ('OK', True), b.get('error'))  # a real positive control: the default proves this no-link, no-action view

    def test_a_parent_owned_action_on_a_plain_link_stays_unresolved(self):  # Root FABLE_INITIAL_LINK_BOUNDARY_20261023T1210
        from driver.prepare.convert import html_route
        links = sg.Visible(PLAIN_LINKS).links; amber = next(l['start'] for l in links if l['href'] == '#note-amber')
        self.assertEqual(html_route.declarations(sg.Visible(PLAIN_LINKS), self.browser), ({}, []))  # fixture fact: no declared action at all (the native decision)
        full = run(self.browser, child=PLAIN_LINKS, panels=PARENT_OWNED)  # the full native boundary trials every visible link
        t = next(t for t in full['trials'] if t.get('label') == 'trial@%d' % amber)
        self.assertGreater(t['probe']['new_roots'], 0, t['probe'])  # native fact: the parent's own listener acted on the plain link
        res = run(self.browser, child=PLAIN_LINKS, panels=PARENT_OWNED, explore=False); ini = res['initial']
        self.assertEqual(attempted(res), set()); self.assertEqual(res['states'], [])
        self.assertNotEqual(ini['status'], 'OK', ini.get('error'))  # never complete while a skipped visible link's action is unknown
        self.assertIn('context: %d visible source link(s) not attempted' % sum(1 for l in links if not l['hidden']), ini.get('error') or '')

    def test_a_missing_resource_keeps_its_own_failure(self):
        a, b = run(self.browser, explore=False, drop=(ROOT + '/portal/plan.png',))['initial'], run(self.browser, drop=(ROOT + '/portal/plan.png',))['initial']
        self.assertNotEqual(a['status'], 'OK')
        for part in (b.get('error') or '').split('; '):  # every reason the default gives for the initial view, except the explored states' own deficits
            if part and not part.startswith('context: trial@') and not part.startswith('context: activated@'): self.assertIn(part, a['error'])

    def test_a_native_failure_is_never_hidden(self):
        with mock.patch.object(sg, 'native_state', side_effect=sg.CaptureError('injected native capture failure')):
            try: res = run(self.browser, explore=False)
            except Exception as e: return self.assertIn('injected native capture failure', repr(e))
        self.assertNotEqual(res['initial']['status'], 'OK'); self.assertIn('injected native capture failure', repr(res['initial']))

    def test_invalid_option_values_are_refused(self):
        for v in ('false', 0, 1, None, 'no', []):
            with self.assertRaises(TypeError): run(self.browser, explore=v)

    def test_explicit_full_exploration_equals_the_default(self):
        res = run(self.browser, explore=True)
        key = lambda r: ([s['label'] for s in r['states']], [t['label'] for t in r['trials']], r['initial']['status'], r['initial'].get('error'))
        self.assertEqual(key(res), key(self.full))


if __name__ == '__main__':
    unittest.main()
