"""The ordinary-navigation exemption as a class (Root CONTEXT_FINAL_OUTCOME_CLOSE_20261022, 03:26/03:27): a refused source-owned action is exempt from
the document's unknown-state deficit only as an ordinary navigation. Native offline controls on the same real family fixture (its outer control's own
handler replaced; every request answered or aborted by the context route, so nothing reaches a network): a POST form navigation, a child-frame
document GET, a top-level GET navigation that also raises a script error, and an XHR POST must each leave the specific deficit; the ordinary top-level
GET navigation stays exempt (no deficit). The fixture's unrelated BUTTON reason is always present, so each check reads the specific trial deficit."""
import json, unittest
from .test_family_outcome import CHILD, MORE, at, g, run
OUTER = b"MuseumCards.reveal(this, 'note-indigo')"
NEXT = "'https://museum.invalid/portal/next.html'"
VARIANTS = {
    'post_form_navigation': "var f = document.createElement('form'); f.method = 'post'; f.action = " + NEXT + "; document.body.appendChild(f); f.submit();",
    'child_frame_document_get': "var i = document.createElement('iframe'); i.src = 'https://museum.invalid/portal/frame.html'; document.body.appendChild(i);",
    'get_navigation_with_script_error': "location.href = " + NEXT + "; MuseumCards.missing(this);",
    'xhr_post': "var x = new XMLHttpRequest(); x.open('POST', 'https://museum.invalid/portal/log'); x.send('x'); MuseumCards.reveal(this, 'note-indigo')",
    'ordinary_get_navigation': "location.href = " + NEXT + ";",
    'new_window_get': "window.open(" + NEXT + ");",  # Root 03:40: a real new window; its request's native frame is not available yet
    'mixed_top_and_child_frame': "var i = document.createElement('iframe'); i.src = 'https://museum.invalid/portal/frame.html'; document.body.appendChild(i); location.href = " + NEXT + ";",  # one qualifying GET must not hide a child-frame load
}
def child(v): return g['rep'](CHILD, OUTER, VARIANTS[v].encode())
def deficit(c): return 'trial@%d: source-owned action refused, its state unknown' % c


class NavigationBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
        cls.res = {v: run(cls.browser, child(v), panels=MORE) for v in VARIANTS}
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()
    def seen(self, v):  # the trial's own refusal and the action-phase requests it saw (method, resource type): for the reader of a failure
        c = at(child(v), b'Cabinet label'); res = self.res[v]
        t = next((t for t in res['trials'] if t.get('label') == 'trial@%d' % c), {}); reqs = [q[1:] for q in (t.get('record') or {}).get('requests') or [] if q[0] == 'action']
        return c, res['initial'], json.dumps({'refused': t.get('refused'), 'action_requests': reqs, 'error': res['initial'].get('error')})[:900]
    def raw(self, v):  # the trial's raw action-phase requests (method, url, resource type) and page errors, as recorded
        c = at(child(v), b'Cabinet label'); t = next(t for t in self.res[v]['trials'] if t.get('label') == 'trial@%d' % c); r = t.get('record') or {}
        return [tuple(q[1:4]) for q in r.get('requests') or [] if q[0] == 'action'], [e for e in r.get('errors') or [] if e[0] == 'action']
    def valid(self, v):  # fixture validity (Root 03:37): each variant actually exercised its claimed method/resource type; no verdict here
        reqs, errs = self.raw(v); info = json.dumps({'action_requests': reqs, 'action_errors': errs})[:900]; nxt = NEXT.strip("'")
        if v == 'post_form_navigation': self.assertIn(('POST', nxt, 'document'), reqs, info)
        if v == 'child_frame_document_get': self.assertIn(('GET', 'https://museum.invalid/portal/frame.html', 'document'), reqs, info)  # only the inserted iframe loads this URL
        if v == 'get_navigation_with_script_error': self.assertIn(('GET', nxt, 'document'), reqs, info); self.assertTrue(errs, info)
        if v == 'xhr_post': self.assertIn(('POST', 'https://museum.invalid/portal/log', 'xhr'), reqs, info)
        if v == 'new_window_get': self.assertIn(('GET', nxt, 'document'), reqs, info)
        if v == 'mixed_top_and_child_frame': self.assertIn(('GET', nxt, 'document'), reqs, info); self.assertIn(('GET', 'https://museum.invalid/portal/frame.html', 'document'), reqs, info)
        if v == 'ordinary_get_navigation': self.assertIn(('GET', nxt, 'document'), reqs, info); self.assertEqual(errs, [], info); self.assertTrue(all(m == 'GET' for m, _, _ in reqs), info)
    def unknown(self, v):
        self.valid(v); c, i, info = self.seen(v); self.assertEqual(i['status'], 'PARTIAL'); self.assertIn(deficit(c), i.get('error') or '', info)

    def test_post_form_navigation_is_not_ordinary_navigation(self): self.unknown('post_form_navigation')
    def test_child_frame_document_get_is_not_ordinary_navigation(self): self.unknown('child_frame_document_get')
    def test_navigation_with_a_script_error_is_not_ordinary_navigation(self): self.unknown('get_navigation_with_script_error')
    def test_xhr_post_is_unknown(self): self.unknown('xhr_post')
    def test_new_window_navigation_is_not_ordinary_navigation(self): self.unknown('new_window_get')  # Root CONTEXT_NATIVE_FRAME_PROOF_20261022
    def test_mixed_top_and_child_frame_is_not_ordinary_navigation(self): self.unknown('mixed_top_and_child_frame')
    def test_ordinary_top_level_get_navigation_stays_exempt(self):
        self.valid('ordinary_get_navigation'); c, i, info = self.seen('ordinary_get_navigation'); self.assertNotIn(deficit(c), i.get('error') or '', info)
        self.assertEqual((i['status'], i.get('error')), ('PARTIAL', g['BUTTON']), info)  # only the fixture's own button


if __name__ == '__main__':
    unittest.main()
