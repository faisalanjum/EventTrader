"""A replay of the recorded parent consumes the same recorded responses as acquisition, and every received identity names what was sent
(Root FABLE_PARENT_RESPONSE_IDENTITY_FIX_20261023T1610). Public invented fixture: test_native_selection's scripted-menu parent, whose startup loads
the shared stylesheet. The document's Source also holds a package member at that SAME address. Expected values come from the fixture's own recorded
parent state (acquisition's NativeSelection.state_facts: no package members, unchanged code) and the fixture bytes, never from the changed code.
Two address layouts (member name 'frame.css' under the shared folder, 'shared/frame.css' under the root) show the rule is not tied to a name."""
import copy, hashlib, unittest
from .cases import context, sg, evidence, obs, ANON, CSS, ROOT, TARGET, PNG, rep
from driver.prepare.pictures import inputs
from .test_native_selection import SCRIPTED, select, declared

S = lambda xs: {tuple(x) for x in xs}
sha = lambda b: hashlib.sha256(b).hexdigest()
URL = ROOT + '/shared/frame.css'
LAYOUTS = ((ROOT + '/shared/', 'frame.css'), (ROOT + '/', 'shared/frame.css'))  # (base, member name at URL): the same address, two member layouts
OTHER = CSS + b'\n/* a package member with other bytes at the same address */\n'


def recorded(browser, ev):  # acquisition's own recorded parent state for this evidence (the fixture's expectation source)
    r, s, _ = select(browser, ev); assert r['verdict'] == 'selected', r.get('verdict')
    return declared(r, s), S(s.state_facts['delivered']), S(s.state_facts['refused_get'])


def replay(browser, ev, sel, base, name, member):  # one Context render of the initial view: (error, render record, the Source's own records)
    ev = copy.deepcopy(ev); ev['selection'] = sel; ctx = context.Context(ev)
    src = context.state_source(sg.Source('item.html', {'item.html': ANON, name: member}, base=base), ev, ctx); src.at(TARGET, ANON); page = err = None  # bound as the route binds it (root = base)
    try:
        page = ctx.page(browser, None, ('https://trial.invalid/', ANON), src); page.goto('trial')
    except Exception as e:
        err = repr(e)[:300]
    finally:
        if page is not None: page.close()
    return err, ctx.records[0], dict(src.records)


class ParentResponseIdentity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
        cls.ev = evidence(child=ANON, parent=SCRIPTED); cls.sel, cls.delivered, cls.refused = recorded(cls.browser, cls.ev)
        assert (URL, 200, sha(CSS)) in cls.delivered, sorted(cls.delivered)  # fixture fact: the recorded parent startup received the stylesheet
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def inputs(self, rec): return S(rec['selection_inputs']['received']), S(rec['selection_inputs']['refused_get'])

    def test_different_member_bytes_at_a_recorded_address_are_never_sent(self):  # the demonstrated class (R3 R1.htm): red before the fix
        for base, name in LAYOUTS:
            err, rec, recs = replay(self.browser, self.ev, self.sel, base, name, OTHER)
            self.assertIsNone(rec.get('refused'), (name, rec.get('refused'), err))
            self.assertEqual(self.inputs(rec), (self.delivered, self.refused), name)  # the same inputs as the recorded parent state
            self.assertEqual((recs[URL].get('url'), recs[URL].get('status'), recs[URL].get('sha256')), (URL, 200, sha(CSS)), (name, recs[URL]))  # what was SENT: the recorded response
            self.assertNotIn('member', recs[URL], name)

    def test_same_member_bytes_positive(self):
        for base, name in LAYOUTS:
            err, rec, recs = replay(self.browser, self.ev, self.sel, base, name, CSS)
            self.assertIsNone(rec.get('refused'), (name, rec.get('refused'), err)); self.assertEqual(self.inputs(rec), (self.delivered, self.refused), name)
            self.assertEqual(recs[URL]['sha256'], sha(CSS), name)

    def test_a_conflicting_recorded_status_is_served_as_recorded(self):  # recorded 404 at the address, a 200 member there: the replay consumes the 404
        ev = evidence(child=ANON, parent=SCRIPTED); ev['observed'][URL] = obs(b'not found', 'text/plain', 404); sel, delivered, refused = recorded(self.browser, ev)
        self.assertIn((URL, 404, sha(b'not found')), delivered)  # fixture fact (acquisition)
        err, rec, recs = replay(self.browser, ev, sel, *LAYOUTS[0], OTHER)
        self.assertIsNone(rec.get('refused'), (rec.get('refused'), err)); self.assertEqual(self.inputs(rec), (delivered, refused))
        self.assertEqual((recs[URL].get('status'), recs[URL].get('sha256')), (404, sha(b'not found'))); self.assertNotIn('member', recs[URL])

    def test_invalid_recorded_bytes_are_refused_never_replaced_by_a_member(self):
        ev = evidence(child=ANON, parent=SCRIPTED); ev['observed'][URL] = dict(ev['observed'][URL], sha256=sha(b'another body')); sel, delivered, refused = recorded(self.browser, ev)
        self.assertIn((URL, 'stylesheet'), refused)  # fixture fact: acquisition refused the stylesheet whose bytes are not its recorded sha256
        err, rec, recs = replay(self.browser, ev, sel, *LAYOUTS[0], OTHER)
        self.assertIsNone(rec.get('refused'), (rec.get('refused'), err)); self.assertEqual(self.inputs(rec), (delivered, refused))
        self.assertEqual((recs[URL].get('status'), recs[URL].get('why')), ('refused', 'observed bytes are not the recorded sha256')); self.assertNotIn('member', recs[URL])

    def test_an_unrecorded_address_keeps_the_member_rule_and_its_identity(self):  # no recorded response in the replay's evidence: the member is sent and named; the inputs differ from the recorded state, so refused
        ev = evidence(child=ANON, parent=SCRIPTED, drop=(URL,))  # (acquisition itself does not select with this dependency unobserved: 'incomplete: unobserved dependency')
        err, rec, recs = replay(self.browser, ev, self.sel, *LAYOUTS[0], OTHER)
        self.assertEqual((recs[URL].get('member'), recs[URL].get('sha256')), ('frame.css', sha(OTHER)))
        self.assertIn((URL, 200, sha(OTHER)), self.inputs(rec)[0])  # the received identity names the member actually sent
        self.assertIn('received different inputs than the recorded parent state', str(rec.get('refused')))  # never a relaxed equality

    def test_a_picture_at_a_recorded_address_is_the_recorded_image_for_render_and_picture_step(self):  # Root FABLE_PARENT_ASSET_BOUNDARY_20261023T1620
        img = ROOT + '/portal/plan.png'; other = PNG + b'\x00' * 8  # same resolved image URL; the package member has other bytes
        child = rep(ANON, b'<p><a id="plain-link"', b'<p><img src="plan.png" alt="plan"></p><p><a id="plain-link"'); members = {'item.html': child, 'plan.png': other}
        ev = evidence(child=child); self.assertEqual(ev['observed'][img]['body'], PNG)  # fixture fact: the recorded parent response at the image URL
        got = {}
        def prep(route, src, label): got[label] = inputs.prepare(child, route, members, self.browser, src)
        res = context.contextual_routes(child, 'invented/item.html', sha(child), self.browser, sg.Source('item.html', members, base=ROOT + '/portal/'), ev, prepare=prep, explore=False)
        route = res['initial']; units = [u for u in route['units'] if u.get('kind') == 'image']; self.assertEqual(len(units), 1, route.get('error')); u = units[0]
        deps = route['resources']['dependencies']
        self.assertIn({'url': img, 'status': 200, 'sha256': sha(PNG)}, [{k: d.get(k) for k in ('url', 'status', 'sha256')} for d in deps])  # the dependency identity: the recorded response
        self.assertFalse([d for d in deps if d.get('member') == 'plan.png'], deps)  # never the member
        self.assertEqual(sha(got['initial'][u['input']['input_sha256']]) if u['input'].get('how') == 'member' else u['input'].get('member_sha256'), sha(PNG), u['input'])  # the prepared image bytes
        self.assertEqual(u['input'].get('member_sha256'), sha(PNG), u['input'])  # the legacy field names the direct image bytes actually used

    def test_the_ordinary_non_context_source_still_answers_its_package_member(self):  # screen_grid.Source's own rule is unchanged
        s = sg.Source('item.html', {'item.html': ANON, 'frame.css': OTHER}, base=ROOT + '/shared/', observed={URL: obs(CSS, 'text/css')}); s.at(ROOT + '/shared/item.html', ANON)
        self.assertEqual(s.answer(URL, 'stylesheet')[2], OTHER); self.assertEqual(s.records[URL]['member'], 'frame.css')
        self.assertIsNone(s.answer(URL, 'document', navigation=True)); self.assertEqual(s.records[URL]['member'], 'frame.css')  # a navigation is refused (first record kept)


if __name__ == '__main__':
    unittest.main()
