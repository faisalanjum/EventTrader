"""Pictures on a page the scanner cannot certify follow the browser's own verdict, read in page_visibility's one render by the native
Element.checkVisibility with its opacity and CSS-visibility options: a picture tag the page hides gives no picture (the tool's own image is left out
while its source tag is still known), one a sheet shows again is a picture at its own tag; size is not visibility (a picture of no area stays); a mark
that cannot reach its tag (the parser moved it) leaves the scanner's reading and is said. Expected from the markup, before the change (Root,
OCR_PICTURE_VISIBILITY_FIX). The sheet in `page` is what makes these pages uncertain; `CertainPage` has none (the scanner's own verdict, no browser)."""
import io, unittest

from PIL import Image

from driver.prepare.convert import anchor, html_route
from driver.prepare.pictures import inputs

SHEET = b'<style>.h{display:none}.s{display:inline !important}.v{visibility:visible}.o{opacity:0}</style>'


def page(body, sheet=SHEET): return b'<!doctype html><html><head><meta charset="utf-8">' + sheet + b'</head><body>' + body + b'</body></html>'


def png(): b = io.BytesIO(); Image.new('RGB', (40, 20), (200, 30, 30)).save(b, 'PNG'); return b.getvalue()


class InTheBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def route(self, body, sheet=SHEET):
        raw = page(body, sheet); route, facts = html_route.prepare(raw, 'f.htm', anchor.sha256(raw), self.browser)
        pics = [u for u in route['units'] if u['kind'] == 'image']
        at = lambda u: raw[u['anchor']['byte_start']:u['anchor']['byte_end_exclusive']] if isinstance(u.get('anchor'), dict) else None
        return raw, route, facts, pics, at

    def test_a_picture_the_page_hides_is_no_picture(self):
        _, r, _, pics, _ = self.route(b'<p>a</p><img class="h" src="h1.png" width="40" height="20"><div class="h"><img src="h2.png" width="40" height="20"></div><div class="o"><img src="o.png" width="40" height="20"></div><p>b</p>')
        self.assertEqual((anchor.Visible(page(b'')).certain, r['status'], pics), (False, 'OK', []))  # a sheet, a hidden ancestor, an ancestor at opacity 0

    def test_a_picture_a_sheet_shows_again_is_one_at_its_own_tag(self):
        _, r, _, pics, at = self.route(b'<p>a</p><img class="s" style="display:none" src="s.png" width="40" height="20"><div style="visibility:hidden"><img class="v" src="v.png" width="40" height="20"></div><p>b</p>')
        self.assertEqual([(u['src'], at(u)) for u in pics], [('s.png', b'<img class="s" style="display:none" src="s.png" width="40" height="20">'), ('v.png', b'<img class="v" src="v.png" width="40" height="20">')])

    def test_one_file_twice_is_two_occurrences_each_by_its_own_tag(self):
        raw, _, _, pics, at = self.route(b'<p>a</p><img class="h" src="same.png" alt="hidden" width="40" height="20"><img src="same.png" alt="shown" width="40" height="20"><p>b</p>')
        self.assertEqual([(u['alt'], at(u)) for u in pics], [('shown', b'<img src="same.png" alt="shown" width="40" height="20">')])

    def test_tables_nested_tables_captions_and_inline_svg(self):
        raw, r, _, pics, at = self.route(b'<table><caption>Brands</caption><tr><td><img class="h" src="t1.png" width="40" height="20"></td><td><img src="t2.png" width="40" height="20"></td></tr>'
                                         b'<tr><td>x</td><td><table><tr><td><svg width="40" height="20"></svg><img class="h" src="t3.png" width="40" height="20"></td></tr></table></td></tr></table>')
        t = [u['id'] for u in r['units'] if u['kind'] == 'table']
        self.assertEqual([(u.get('src'), at(u)[:4], u['cell'].get('table')) for u in pics], [('t2.png', b'<img', t[0]), (None, b'<svg', t[1])])
        self.assertEqual([u['caption'] for u in r['units'] if u['kind'] == 'table'][0], ['Brands'])

    def test_size_is_not_visibility(self):  # no area (an empty alt, a zero size) or a broken-image box: still a shown picture
        _, _, _, pics, at = self.route(b'<p>a</p><img src="z1.png" alt=""><img src="z2.png" width="0" height="0"><img src="z3.png"><p>b</p>')
        self.assertEqual([u['src'] for u in pics if at(u)], ['z1.png', 'z2.png', 'z3.png'])

    def test_a_source_comment_or_attribute_like_a_mark_binds_nothing(self):
        _, _, _, pics, _ = self.route(b'<p>a</p><!--q:0--><img class="h" src="i.png" width="40" height="20"><span title="<!--q:1-->">t</span><img src="j.png" width="40" height="20"><p>b</p>')
        self.assertEqual([u['src'] for u in pics], ['j.png'])

    def test_a_tag_the_parser_moves_keeps_the_scanners_reading_and_is_said(self):  # its mark stays in the table, the picture is fostered out of it
        raw, r, facts, pics, _ = self.route(b'<p>a</p><table><img src="f.png" width="40" height="20"><tr><td>x</td></tr></table>')
        self.assertEqual(r['status'], 'PARTIAL'); self.assertIn('picture', r['error'])
        self.assertEqual([u['src'] for u in pics], ['f.png'])

    def test_the_picture_inputs_read_the_same_verdict(self):  # inputs.prepare rebuilds the reading from the route's own stored verdict
        raw, r, _, pics, _ = self.route(b'<p>a</p><img class="s" style="display:none" src="s.png" width="40" height="20"><img class="h" src="h.png" width="40" height="20"><p>b</p>')
        got = inputs.prepare(raw, r, {'s.png': png(), 'h.png': png()}, self.browser)
        self.assertEqual([(u['src'], 'input_sha256' in u['input']) for u in pics], [('s.png', True)]); self.assertEqual(len(got), 1)


class CertainPage(InTheBrowser):  # no sheet: the scanner certifies the page itself; no browser verdict is asked, and its certified verdict is the one used
    def test_a_picture_a_certified_reading_proves_hidden_is_no_picture(self):  # changed (Root review addendum): v1 kept c.png unplaced, so inputs gave it an error
        for hide in ('display:none', 'visibility:hidden', 'opacity:0'):
            for first in ('hidden', 'shown'):
                parts = [b'<div style="%s"><img src="x.png" width="40" height="20"></div>' % hide.encode(), b'<img src="x.png" width="40" height="20">']
                if first == 'shown': parts.reverse()
                with self.subTest(hide=hide, first=first):
                    raw, r, facts, pics, at = self.route(b'<p>a</p>' + parts[0] + b'<p>m</p>' + parts[1] + b'<p>b</p>', sheet=b'')
                    self.assertEqual((anchor.Visible(raw).certain, 'visibility' in facts, [at(u) for u in pics]), (True, False, [b'<img src="x.png" width="40" height="20">']))
                    self.assertEqual(pics[0]['anchor']['byte_start'], raw.index(b'<img src="x.png" width="40" height="20">', raw.index(b'<p>m</p>') if first == 'hidden' else 0))  # the shown tag itself

    def test_a_shown_picture_and_a_child_that_restores_visibility_stay(self):
        raw, r, facts, pics, at = self.route(b'<p>a</p><img src="d.png" width="40" height="20"><div style="visibility:hidden"><img src="r.png" style="visibility:visible" width="40" height="20"></div><p>b</p>', sheet=b'')
        self.assertEqual((anchor.Visible(raw).certain, [(u['src'], bool(at(u))) for u in pics]), (True, [('d.png', True), ('r.png', True)]))

    def test_the_picture_inputs_get_no_error_for_a_hidden_copy(self):
        raw, r, facts, pics, at = self.route(b'<p>a</p><img src="c.png" style="display:none" width="40" height="20"><img src="d.png" width="40" height="20"><p>b</p>', sheet=b'')
        got = inputs.prepare(raw, r, {'c.png': png(), 'd.png': png()}, self.browser)
        self.assertEqual(([(u['src'], sorted(u['input'])) for u in pics], len(got)), ([('d.png', sorted(next(u for u in pics)['input']))], 1)); self.assertIn('input_sha256', pics[0]['input'])

    test_a_picture_the_page_hides_is_no_picture = test_a_picture_a_sheet_shows_again_is_one_at_its_own_tag = None
    test_one_file_twice_is_two_occurrences_each_by_its_own_tag = test_tables_nested_tables_captions_and_inline_svg = test_size_is_not_visibility = None
    test_a_source_comment_or_attribute_like_a_mark_binds_nothing = test_a_tag_the_parser_moves_keeps_the_scanners_reading_and_is_said = test_the_picture_inputs_read_the_same_verdict = None
