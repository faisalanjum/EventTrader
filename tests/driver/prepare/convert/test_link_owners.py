"""Source links on a page the scanner cannot read for certain (Root's bounded nonempty-link release): the page's own visibility render proves a link's
owners only where the scanner's extent is whole, the browser's <a> for that very tag binds, every marked run and picture of the extent stands in it and none
outside does, each has a verdict, no literal run hides in it, no <a href> was made by the parser, and the link holds extracted text or a picture of its own -
then owners as a certain page gives them, `owners_by: page` (the extracted units, cells and pictures it holds: never a claim that nothing else shows).
Everything else keeps owners None. Controls: Fable's link_ownership_design_v1 truths, Root's false-empty pseudo control."""
import hashlib
import unittest

from driver.prepare.convert import html_route

U = b'<style>.zz{display:none}</style>'  # one generic uncertainty: a sheet rule the scanner does not evaluate


class PageProvedLinks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright  # required: a missing install fails the suite
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def links(self, body, uncertain=True):  # [(href, owners as (kind, text or src) of each owner, owners_by)]
        raw = (U if uncertain else b'') + body; route, _ = html_route.prepare(raw, 'l.htm', hashlib.sha256(raw).hexdigest(), self.browser)
        what = {u['id']: (u['kind'], u.get('text') if u['kind'] != 'image' else u.get('src')) for u in route['units']}
        what.update({(u['id'], c['anchor']['byte_start']): ('cell', c.get('text')) for u in route['units'] for c in u.get('cells') or [] if isinstance(c.get('anchor'), dict)})
        return [(l['href'], None if l['owners'] is None else [what[(o['unit'], o['cell'])] if 'cell' in o else what[o['unit']] for o in l['owners']], l.get('owners_by')) for l in route['source_links']]

    def test_a_link_in_text_and_one_in_a_cell_name_their_own_unit_and_cell(self):
        self.assertEqual(self.links(b'<p>See <a href="#t1">Alpha <b>bold</b></a> after</p><p id="t1">Target</p>'), [('#t1', [('text', 'See Alpha  bold after')], 'page')])
        self.assertEqual(self.links(b'<table><tr><td><a href="#c">Cell link</a></td><td>2</td></tr></table>'), [('#c', [('cell', 'Cell link')], 'page')])

    def test_a_picture_only_link_names_its_picture_and_a_picture_outside_is_never_its_own(self):
        self.assertEqual(self.links(b'<p>Logo <a href="#p"><img src="p.png" width="8" height="8"></a></p>'), [('#p', [('image', 'p.png')], 'page')])
        self.assertEqual(self.links(b'<p><a href="#pt">Logo <img src="a.png" width="8" height="8"></a> <img src="b.png" width="8" height="8"></p>'), [('#pt', [('text', 'Logo'), ('image', 'a.png')], 'page')])

    def test_duplicate_href_and_text_bind_by_their_own_tags(self):
        self.assertEqual(self.links(b'<p><a href="#d">Same</a> and <a href="#d">Same</a></p>'), [('#d', [('text', 'Same and Same')], 'page')] * 2)

    def test_the_inner_of_nested_links_is_proved_and_the_outer_is_not(self):  # the parser ends the outer at the inner <a>; " after" is in neither
        self.assertEqual(self.links(b'<p><a href="#o">out <a href="#i">in</a> after</a></p>'), [('#o', None, None), ('#i', [('text', 'out in after')], 'page')])

    def test_a_link_the_parser_reopens_fosters_or_leaves_open_stays_unproved(self):
        for body in (b'<p><b><a href="#r">one</b> two</a></p>', b'<table><tr><a href="#f">fost</a><td>c</td></tr></table>', b'<p><a href="#u">open text</p><p>next</p>'):
            with self.subTest(body=body): self.assertEqual([(h, o, b) for h, o, b in self.links(body)], [(self.links(body)[0][0], None, None)])

    def test_inside_and_outside_run_mutations_stay_unproved(self):  # text the parser moves out of its run's mark (fostered), a run reopened outside its source extent
        self.assertEqual(self.links(b'<a href="#in"><table><tr>stray<td>x</td></tr></table></a>'), [('#in', None, None)])
        self.assertEqual(self.links(b'<p><b><a href="#r">one</b> two</a></p>'), [('#r', None, None)])

    def test_a_moved_or_unbound_picture_stays_unproved(self):  # a picture the parser fosters out of a row: its mark binds nothing in the link
        self.assertEqual(self.links(b'<a href="#mp">Logo <table><tr><img src="m.png" width="8" height="8"><td>x</td></tr></table></a>'), [('#mp', None, None)])

    def test_ordinary_text_plus_literal_content_stays_unproved(self):  # a literal run (never marked: a comment there would be text) is no proved owner
        self.assertEqual(self.links(b'<p><a href="#lt">Plain <textarea>literal</textarea></a></p>'), [('#lt', None, None)])

    def test_no_text_or_picture_of_its_own_is_never_certified_empty(self):  # Root's false-empty controls: zero own area is not an empty link
        for body in (b'<p>x<a href="#e"></a>y</p>', b'<p><a href="#h" class="zz">hidden</a> shown</p>',
                     b'<p>x<a href="#bg" style="display:inline-block;width:20px;height:10px;background:#c81e1e"></a>y</p>',
                     b'<style>.ps::before{content:"VISIBLE";position:absolute}</style><p>x<a href="#ps" class="ps"></a>y</p>'):
            with self.subTest(body=body): self.assertEqual([o for _, o, _ in self.links(body)], [None]); self.assertEqual([b for _, _, b in self.links(body)], [None])

    def test_a_certain_page_is_unchanged(self):  # the scanner's own proof, as before: no page evidence named
        self.assertEqual(self.links(b'<p>See <a href="#t1">Alpha</a> after</p><p id="t1">Target</p>', uncertain=False), [('#t1', [('text', 'See Alpha after')], None)])


if __name__ == '__main__':
    unittest.main()
