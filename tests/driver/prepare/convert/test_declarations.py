# Ported to the normal suite from context_candidate/tests/test_script_action.py (sha256 cf3c0f7aa7b8ebf924c817abeb7094c64efb5372377b61fb2742ee7e99404fc3), frozen in tests_snapshot_20261022T0237_final. Test bodies unchanged;
# mechanical change only: the checkout's own driver package is imported directly instead of through CANDIDATE_RUNTIME.
"""Source declarations use the existing attribute scan and the pinned browser's
native URL protocol and event properties. Custom on-prefixed attributes remain
negative controls. Unqualified source actions make the document incomplete;
ordinary links and documents keep their existing status.
Run with the normal suite (the checkout's own driver package)."""
import hashlib, unittest

from driver.prepare.convert import html_route, screen_grid as sg
from driver.prepare.convert.anchor import Visible


class Fact(unittest.TestCase):  # the one native decision (pinned browser, Root CONTEXT_NATIVE_DECLARATION_URL_REVIEW_20261022): the anchor's own protocol for the exact decoded href, its own event properties
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()
    def fact(self, tag): return html_route.declarations(Visible(b'<p>' + tag + b'go</a></p>'), self.browser)[0].get(3)  # the link at byte 3

    def test_owned_script_link(self): self.assertEqual(self.fact(b'<a href="javascript:void(0)" onclick="f()">'), {'javascript_href': True, 'event_attributes': ['onclick']})
    def test_declared_handler_with_an_ordinary_href(self): self.assertEqual(self.fact(b'<a href="#note" onmouseover="f()">'), {'javascript_href': False, 'event_attributes': ['onmouseover']})
    def test_ordinary_links_carry_nothing(self):
        for t in (b'<a href="#note">', b'<a href="https://reference.invalid/a#b">', b'<a href="other.htm">', b'<a href="mailto:x@reference.invalid">'):
            with self.subTest(tag=t): self.assertIsNone(self.fact(t))
    def test_url_permutations(self):
        for t in (b'<a href="JavaScript:void(0)">', b'<a href=" javascript:void(0)">', b'<a href="java&#x09;script:void(0)">', b'<a href="&#106;avascript:void(0)">',
                  b'<a href="javascript&colon;void(0)">', b'<a href="JAVASCRIPT:x">', b'<a href="jav&#10;ascript:x">'):
            with self.subTest(tag=t): self.assertEqual(self.fact(t), {'javascript_href': True, 'event_attributes': []})
        self.assertIsNone(self.fact(b'<a href="javascript :x">'))  # a space inside the scheme: the browser gives no javascript protocol
    def test_malformed_urls_no_longer_raise(self):  # the regression Root reproduced on auto2 (evidence/url_declaration_failing_control_run1): urlsplit raised Invalid IPv6 URL
        for t in (b'<a href="https://[">', b'<a href="javascript://[">'):
            with self.subTest(tag=t): self.assertIsNone(self.fact(t))  # the browser's own protocol is ':' for both: no script URL, and nothing raises
    def test_custom_attribute_beginning_on_is_not_an_event(self):
        for t in (b'<a href="#n" onward="1">', b'<a href="#n" ontology="x">', b'<a href="#n" on="1">'):
            with self.subTest(tag=t): self.assertIsNone(self.fact(t))
    def test_attribute_case(self): self.assertEqual(self.fact(b'<a HREF="#n" OnClick="f()">'), {'javascript_href': False, 'event_attributes': ['onclick']})


class DefaultStatus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()
    def route(self, raw): return html_route.prepare(raw, 'invented/x.html', hashlib.sha256(raw).hexdigest(), self.browser, sg.Source('x.html', {'x.html': raw}))[0]

    def test_declared_actions_make_the_default_route_partial(self):
        r = self.route(b'<html><body><p><a href="javascript:void(0)" onclick="show()">Open notes</a></p><div style="display:none"><p>Hidden notes.</p></div></body></html>')
        self.assertEqual(r['status'], 'PARTIAL'); self.assertIn('context: 1 declared script action(s) not qualified (no context entered)', r['error'])
        self.assertEqual([l.get('script_action') for l in r['source_links']], [{'javascript_href': True, 'event_attributes': ['onclick']}])

    def test_ordinary_document_unchanged(self):
        r = self.route(b'<html><body><p><a href="#n">Notes</a></p><p id="n">Notes here.</p><div style="display:none"><p>Hidden.</p></div></body></html>')
        self.assertEqual(r['status'], 'OK', r.get('error')); self.assertNotIn('script_action', r['source_links'][0])


class NativeEvents(unittest.TestCase):  # OCR challenge 2026-10-22: event-handler attributes the library does not list; the pinned browser decides
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def test_the_parser_keeps_them_as_raw_declaration_only(self):
        l = Visible(b'<p><a href="#n" onpointerup="f()" onboarding="1">go</a></p>').links[0]
        self.assertEqual((l.get('script_action'), l.get('on_attributes')), (None, ['onboarding', 'onpointerup']))
    def test_native_event_properties_are_declared_and_custom_names_are_not(self):
        for name in (b'onpointerup', b'oncontextmenu', b'onauxclick'):
            with self.subTest(attribute=name):
                self.assertEqual(list(html_route.declarations(Visible(b'<p><a href="#n" ' + name + b'="f()">go</a></p>'), self.browser)[0].values()), [{'javascript_href': False, 'event_attributes': [name.decode()]}])
        self.assertEqual(html_route.declarations(Visible(b'<p><a href="#n" onboarding="1" onward="2">go</a></p>'), self.browser), ({}, []))
    def test_default_route_status_uses_the_native_fact(self):
        raw = b'<html><body><p><a href="#n" onauxclick="f()">Notes</a></p><p id="n">Notes here.</p></body></html>'
        r = html_route.prepare(raw, 'invented/x.html', hashlib.sha256(raw).hexdigest(), self.browser, sg.Source('x.html', {'x.html': raw}))[0]
        self.assertEqual(r['status'], 'PARTIAL'); self.assertIn('context: 1 declared script action(s) not qualified', r['error'])
        self.assertEqual(r['source_links'][0]['script_action'], {'javascript_href': False, 'event_attributes': ['onauxclick']})


class OutsideLinkPath(unittest.TestCase):  # Root CONTEXT_DECLARED_ACTION_BOUNDARY_20261022: declared handlers outside the supported link path keep the document incomplete
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()
    def outside(self, body): return html_route.declarations(Visible(b'<html><body>' + body + b'</body></html>'), self.browser)
    def route(self, body):
        raw = b'<html><body>' + body + b'</body></html>'
        return html_route.prepare(raw, 'invented/x.html', hashlib.sha256(raw).hexdigest(), self.browser, sg.Source('x.html', {'x.html': raw}))

    def test_declared_handlers_on_other_elements_and_an_href_less_anchor(self):
        for body, tag, ev in ((b'<p><a onclick="f()">Open</a></p>', 'a', ['onclick']), (b'<p><span onclick="f()">Open</span></p>', 'span', ['onclick']),
                              (b'<p><button onclick="f()">Open</button></p>', 'button', ['onclick']), (b'<div onpointerup="f()"><p>Panel</p></div>', 'div', ['onpointerup'])):
            with self.subTest(tag=tag):
                links, outside = self.outside(body); self.assertEqual(links, {}); self.assertEqual([(d['tag'], d['event_attributes']) for d in outside], [(tag, ev)])
                route, facts = self.route(body); self.assertEqual(route['status'], 'PARTIAL'); self.assertIn('context: 1 declared event handler(s) outside the supported link path (not activated)', route['error'])
                self.assertEqual([(d['tag'], d['event_attributes']) for d in facts['declared_outside_link_path']], [(tag, ev)])  # raw evidence: occurrence and attributes
    def test_custom_on_attributes_are_negative(self):
        self.assertEqual(self.outside(b'<p><span onward="1" ontology="x">Text</span></p>'), ({}, []))
        route, facts = self.route(b'<p><span onward="1">Text</span></p>'); self.assertEqual(route['status'], 'OK', route.get('error')); self.assertNotIn('declared_outside_link_path', facts)
    def test_a_supported_link_stays_on_the_link_path(self):
        links, outside = self.outside(b'<p><a href="#n" onclick="f()">Open</a></p><p id="n">x</p>'); self.assertEqual((len(links), outside), (1, []))

if __name__ == '__main__':
    unittest.main()
