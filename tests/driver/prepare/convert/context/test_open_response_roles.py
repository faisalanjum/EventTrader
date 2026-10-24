"""Whole injected-context controls for the one completion rule (transport.closes) in every page role: the parent's shared stylesheet (a
subresource), the parent document and the target document (Root FABLE_RESPONSE_WHOLE_CONTEXT_CONTROLS_20261024T1344). Public invented fixture
(cases.py: the parent page loads ROOT/shared/frame.css). Expected values come from the fixture's own recorded statuses and bytes and from
transport's RETRY / unsupported-3xx policy, never from the candidate's outputs. Raw recorded evidence is never changed by a render."""
import copy, hashlib, unittest
from .cases import context, sg, evidence, obs, ANON, CSS, ROOT, PARENT, TARGET
from driver.prepare.get import transport

sha = lambda b: hashlib.sha256(b).hexdigest()
URL = ROOT + '/shared/frame.css'
OPEN = (503, 429, 301)  # transport.RETRY members and an unsupported 3xx


class OpenResponseRoles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
        assert all(not transport.closes({'status': s}) for s in OPEN) and transport.closes({'status': 200}) and transport.closes({'status': 404})  # the policy the expectations rest on

    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def initial(self, ev):  # the whole injected-context path of the caller (document.py: context_evidence -> contextual_routes), initial view only
        kept = copy.deepcopy(ev)
        res = context.contextual_routes(ANON, 'invented/item.html', sha(ANON), self.browser, sg.Source('item.html', {'item.html': ANON}, base=ROOT + '/bundle/'), ev, explore=False)
        self.assertEqual(ev, kept)  # the recorded evidence itself is never changed
        return res['initial']

    def dep(self, route, url):
        return [d for d in (route.get('resources') or {}).get('dependencies') or [] if d.get('url') == url]

    def test_closed_required_stylesheet_positive(self):
        ev = evidence(child=ANON); self.assertEqual((ev['observed'][URL]['status'], ev['observed'][URL]['sha256']), (200, sha(CSS)))  # fixture fact
        route = self.initial(ev)
        self.assertNotIn('cannot be read offline', route.get('error') or '', route.get('error')); self.assertIn('page_visibility', route)  # the closed state proves visibility
        self.assertEqual([(d['status'], d.get('sha256')) for d in self.dep(route, URL)], [(200, sha(CSS))])

    def test_open_required_stylesheet_cannot_qualify(self):
        for s in OPEN:
            with self.subTest(status=s):
                ev = evidence(child=ANON); ev['observed'][URL] = obs(CSS, 'text/css', s)  # the same bytes, an open recorded status
                route = self.initial(ev)
                self.assertEqual(route['status'], 'PARTIAL'); self.assertIn('cannot be read offline', route.get('error') or '')
                self.assertEqual([d['status'] for d in self.dep(route, URL)], ['refused'])
                self.assertIn('observed %d' % s, self.dep(route, URL)[0].get('why') or '')

    def test_open_parent_cannot_qualify(self):
        for s in OPEN:
            with self.subTest(status=s):
                ev = evidence(child=ANON); ev['observed'][PARENT] = dict(ev['observed'][PARENT], status=s)  # recorded parent bytes kept, open status
                route = self.initial(ev)
                self.assertEqual(route['status'], 'PARTIAL', route.get('error')); self.assertNotIn('page_visibility', route)  # no visibility proof from an open parent
                self.assertIn('parent response refused by the source rule', route.get('error') or '')  # context.Context's existing parent refusal

    def test_open_target_cannot_qualify(self):
        for s in OPEN:
            with self.subTest(status=s):
                ev = evidence(child=ANON); ev['observed'][TARGET] = dict(ev['observed'][TARGET], status=s)
                route = self.initial(ev)
                self.assertEqual(route['status'], 'PARTIAL', route.get('error')); self.assertNotIn('page_visibility', route)
                self.assertIn('target response', route.get('error') or '')  # context.Context's existing target refusal (a 200 is required)


if __name__ == '__main__':
    unittest.main()
