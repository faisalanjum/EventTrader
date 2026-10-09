"""The bytes each picture occurrence is read from (pictures/inputs.py; Codex/Root, Oct 9): an opaque member is its own bytes; a picture with
transparency is the page's own pixels round its box at its natural resolution - its background, a background of its own, a gradient, its display
size as drawn - and anything that cannot be read so is an error with no input, never the bytes with their transparency dropped. Every occurrence is
its own source tag. Offline Chrome; playwright is required (a missing install fails, never skips)."""
import hashlib
import io
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

from driver.prepare.convert import anchor, edgartools_html
from driver.prepare.pictures import inputs


def picture(fill, size=(300, 80), back=(0, 0, 0, 0)):  # letters on a transparent (or given) ground, as PNG bytes
    im = Image.new('RGBA', size, back); ImageDraw.Draw(im).text((10, 30), 'TOTAL = (1,234.50)', fill=fill); out = io.BytesIO(); im.save(out, 'PNG')
    return out.getvalue()


WHITE, BLACK = picture((255, 255, 255, 255)), picture((0, 0, 0, 255))
OPAQUE, CLEAR, TILE = picture((0, 0, 0, 255), back=(250, 250, 250, 255)), picture((0, 0, 0, 0)), picture((0, 0, 0, 0), (8, 8), (16, 32, 64, 255))
MEMBERS = {'white.png': WHITE, 'black.png': BLACK, 'opaque.png': OPAQUE, 'clear.png': CLEAR, 'tile.png': TILE, 'broken.png': b'not a picture'}
sha = lambda b: hashlib.sha256(b).hexdigest()


def route(html):  # the route's own picture units: one per shown picture tag, added from the source (edgartools_html.with_every_picture), a cell's too
    return {'sha256': sha(html), 'units': edgartools_html.with_every_picture([], anchor.Visible(html))}


def page(body):
    return b'<!DOCTYPE html><html><body style="margin:0">' + body + b'</body></html>'


def pixels(data):
    return Image.open(io.BytesIO(data)).convert('RGB')


def composite(data, colour):
    im = Image.open(io.BytesIO(data)).convert('RGBA'); return Image.alpha_composite(Image.new('RGBA', im.size, colour + (255,)), im).convert('RGB')


def largest(a, b):
    return max(abs(x - y) for p, q in zip(a.getdata(), b.getdata()) for x, y in zip(p, q))


class Inputs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.pw.stop()

    def run_page(self, body, members=MEMBERS):
        raw = page(body); r = route(raw); got = inputs.prepare(raw, r, members, self.browser)
        for u in r['units']:  # every input the page gives is opaque, and is the bytes its unit names
            i = u['input']
            if i.get('how') == 'page': self.assertTrue(inputs.opaque(got[i['input_sha256']])); self.assertEqual(sha(got[i['input_sha256']]), i['input_sha256'])
        return r['units'], got

    def test_white_letters_on_a_dark_block_are_read_on_that_block(self):  # a fixed white background would lose them
        (u,), got = self.run_page(b'<div style="background:#102040;padding:10px"><img src="white.png" width="300" height="80" style="display:block"></div>')
        i = u['input']; im = pixels(got[i['input_sha256']])
        self.assertEqual((i['how'], i['member_sha256'], i['scale'], im.size), ('page', sha(WHITE), 1, (300, 80)))
        self.assertLessEqual(largest(im, composite(WHITE, (16, 32, 64))), 1); self.assertGreater(largest(im, pixels(WHITE)), 200)  # not what convert('RGB') gives

    def test_a_gradient_a_background_of_its_own_and_a_background_picture_are_kept_as_drawn(self):
        (g, own, tiled), got = self.run_page(b'<div style="background:linear-gradient(90deg,#ffffff,#44aa88)"><img src="black.png" width="300" height="80" style="display:block"></div>'
                                             b'<img src="black.png" width="300" height="80" style="display:block;background:#ffff00">'
                                             b'<div style="background-image:url(tile.png)"><img src="white.png" width="300" height="80" style="display:block"></div>')
        gi, oi, ti = (pixels(got[x['input']['input_sha256']]) for x in (g, own, tiled))
        self.assertNotEqual(gi.getpixel((1, 1)), gi.getpixel((298, 1))); self.assertEqual(oi.getpixel((2, 2)), (255, 255, 0)); self.assertLessEqual(largest(ti, composite(WHITE, (16, 32, 64))), 1)

    def test_a_tiny_display_is_captured_at_the_pictures_own_resolution(self):  # both directions at least natural: the larger ratio
        (u,), got = self.run_page(b'<div style="height:20px"></div><img src="black.png" width="30" height="2" style="display:block">')
        i = u['input']; self.assertEqual(i['scale'], 40); self.assertEqual(i['size'], [1200, 80]); self.assertEqual(pixels(got[i['input_sha256']]).size, (1200, 80))

    def test_a_fractional_box_is_captured_whole_round_it(self):  # Chrome snaps a fractional clip: the whole CSS pixels round the box are asked for
        (u,), got = self.run_page(b'<p>x</p><img src="black.png" style="width:77px;height:20.5px">')
        i = u['input']; self.assertEqual(i['how'], 'page'); self.assertTrue(all(isinstance(v, int) for v in i['clip']))
        self.assertEqual(pixels(got[i['input_sha256']]).size, tuple(i['size'])); self.assertGreaterEqual(i['size'][0], 300); self.assertGreaterEqual(i['size'][1], 80)

    def test_a_picture_far_down_a_long_page_is_captured_as_drawn(self):  # in view first (hal-20260331: Chrome left such a picture unpainted)
        (u,), got = self.run_page(b'<div style="position:relative;overflow:hidden;height:1056px;margin-top:17000px"><div style="position:absolute;top:77px;left:50px">'
                                  b'<img src="black.png" width="300" height="80" style="display:block"></div></div><div style="height:12000px"></div>')
        im = pixels(got[u['input']['input_sha256']]); self.assertEqual(u['input']['box'][1], 17077); self.assertEqual(im.size, (300, 80))
        self.assertLessEqual(largest(im, composite(BLACK, (255, 255, 255))), 1)

    def test_a_picture_in_a_table_cell_is_read_like_any_other(self):  # a unit the route adds from the source tag ('from': 'source', its cell)
        (u,), got = self.run_page(b'<table><tr><td style="background:#102040"><img src="white.png" width="300" height="80" style="display:block"></td></tr></table>')
        self.assertEqual((u['from'], 'link_flag' in u, 'cell' in u), ('source', False, True)); self.assertEqual(u['input']['how'], 'page'); self.assertLessEqual(largest(pixels(got[u['input']['input_sha256']]), composite(WHITE, (16, 32, 64))), 1)

    def test_same_bytes_share_an_input_only_where_the_page_draws_them_alike(self):
        (a, b, c), _ = self.run_page(b'<div><img src="white.png" width="300" height="80"></div><div><img src="white.png" width="300" height="80"></div>'
                                     b'<div style="background:#102040"><img src="white.png" width="300" height="80"></div>')
        self.assertEqual({a['input']['member_sha256'], b['input']['member_sha256'], c['input']['member_sha256']}, {sha(WHITE)})
        self.assertEqual(a['input']['input_sha256'], b['input']['input_sha256']); self.assertNotEqual(a['input']['input_sha256'], c['input']['input_sha256'])

    def test_the_same_page_gives_the_same_bytes_again(self):  # a rerun keeps its readings
        body = b'<div style="background:#102040;padding:10px"><img src="white.png" width="150" height="40"></div>'
        (u1,), _ = self.run_page(body); (u2,), _ = self.run_page(body); self.assertEqual(u1['input'], u2['input'])

    def test_an_opaque_member_is_its_own_bytes(self):
        (u,), got = self.run_page(b'<div style="background:#102040"><img src="opaque.png" width="150" height="40"></div>')
        self.assertEqual(u['input'], {'member_sha256': sha(OPAQUE), 'input_sha256': sha(OPAQUE), 'how': 'member'}); self.assertIs(got[sha(OPAQUE)], OPAQUE)

    def test_a_fully_transparent_picture_is_what_the_page_shows_there(self):  # not the hidden colours under its transparency
        (u,), got = self.run_page(b'<img src="clear.png" width="300" height="80" style="display:block">')
        self.assertEqual(pixels(got[u['input']['input_sha256']]).getcolors(), [(300 * 80, (255, 255, 255))])

    def test_a_unit_that_is_not_its_source_tag_is_an_error_for_either_kind(self):  # never another member's bytes
        raw = page(b'<img src="opaque.png" width="30" height="8"><img src="black.png" width="30" height="8">'); r = route(raw); o, b = r['units']
        o['src'], b['src'] = 'black.png', 'opaque.png'; got = inputs.prepare(raw, r, MEMBERS, self.browser)
        r2 = route(raw); r2['units'][0]['anchor']['byte_start'] += 1; r2['units'][1]['anchor']['byte_end_exclusive'] -= 1; got2 = inputs.prepare(raw, r2, MEMBERS, self.browser)
        for u in r['units'] + r2['units']: self.assertEqual(u['input'], {'error': 'not a shown picture tag of the source with its src'})
        r3 = route(raw); r3['units'][0].pop('anchor'); r3['units'][1]['anchor'] = [r3['units'][1]['anchor']]; got3 = inputs.prepare(raw, r3, MEMBERS, self.browser)  # placed nowhere
        for u in r3['units']: self.assertEqual(u['input'], {'error': 'the route places this picture at no source tag'})
        self.assertEqual((got, got2, got3), ({}, {}, {}))

    def test_what_cannot_be_read_so_is_an_error_with_no_input(self):
        (missing,), got = self.run_page(b'<img src="missing.png" width="10" height="10">'); self.assertEqual(missing['input'], {'error': 'not a member of the package'})
        (moved,), got2 = self.run_page(b'<table><img src="black.png" width="30" height="8"><tr><td>x</td></tr></table>')  # the parser moves it out of the table
        self.assertEqual(moved['input'], {'member_sha256': sha(BLACK), 'error': 'unbound: its mark is not right before its picture tag'}); self.assertEqual((got, got2), ({}, {}))

    def test_what_the_page_cannot_read_leaves_its_captures_unproved_not_its_opaque_members(self):  # a missing background would leave white letters on white
        for missing in (b'<head><link rel="stylesheet" href="http://elsewhere.example/s.css"></head>', b'<div style="background-image:url(gone.png)">'):
            raw = b'<html>' + missing + b'<body><img src="white.png" width="30" height="8"><img src="opaque.png" width="30" height="8"></body></html>'
            r = route(raw); got = inputs.prepare(raw, r, MEMBERS, self.browser); white, op = r['units']
            self.assertIn('what the page names cannot be read offline, so how it draws is unproved', white['input']['error']); self.assertNotIn('input_sha256', white['input'])
            self.assertEqual(op['input']['how'], 'member'); self.assertEqual(set(got), {sha(OPAQUE)})

    def test_a_member_pillow_cannot_read_stays_its_own_bytes(self):  # the readers report it, as now
        (u,), got = self.run_page(b'<img src="broken.png" width="10" height="10">'); self.assertEqual(u['input']['how'], 'member')

    def test_a_missing_dependency_or_memory_propagates(self):
        raw = page(b'<img src="white.png" width="30" height="8">')
        for failure in (ImportError('no decoder'), MemoryError()):
            with patch.object(inputs.Image, 'open', side_effect=failure), self.assertRaises(type(failure)): inputs.prepare(raw, route(raw), MEMBERS, self.browser)

    def test_bytes_that_are_not_the_routes_source_stop_before_any_page(self):
        raw = page(b'<img src="white.png" width="30" height="8">'); r = route(raw)
        with self.assertRaises(ValueError): inputs.prepare(raw + b' ', r, MEMBERS, self.browser)
        self.assertNotIn('input', r['units'][0])


if __name__ == '__main__':
    unittest.main()
