"""`source_style` (the widened source-run record, formerly `source_color`): for every source run, the page's own computed foreground colour, font
weight, font style, decorations in effect, text transform (the computed property, never a printed string) and the raw background stack of the element holding its text and its ancestors ([depth, colour, image,
opacity], as Chrome writes them; none observed: no key - never a paint or coverage claim), bound to its source bytes and owners as colour was; a
first-letter / first-line value that differs stays property-named uncertainty beside colour's own. Controls: Root's public style sources (checked
in, byte-exact: fixtures/source_style_controls.json) and invented ones; truths literal."""
import hashlib
import json
import unittest
from pathlib import Path

from driver.prepare.convert import html_route

CONTROLS = json.loads((Path(__file__).parent / 'fixtures' / 'source_style_controls.json').read_text(encoding='utf-8'))
K, R0, Y1 = 'rgb(0, 0, 0)', [0, 'rgb(255, 255, 0)', 'none', '1'], [1, 'rgb(255, 255, 0)', 'none', '1']


def src(k):  # a checked-in source's bytes, checked against the fixture's own sha256
    b = CONTROLS['cases'][k].encode('utf-8'); assert hashlib.sha256(b).hexdigest() == CONTROLS['sources_sha256'][k], k; return b


class SourceStyle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright  # required: a missing install fails the suite
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def read(self, raw, part='records'):  # (source text, colour, weight, font style, decorations, background) per run record, in record order
        route, _ = html_route.prepare(raw, 's.htm', hashlib.sha256(raw).hexdigest(), self.browser)
        self.assertEqual(json.loads(json.dumps(route)), route); s = route['source_style']; recs = s[part] if part in s else s['fallback'][part]
        return route, recs, [(raw[x['at']['byte_start']:x['at']['byte_end_exclusive']].decode(), x['color'], x['weight'], x['font_style'], x['decorations'], x.get('background')) for x in recs]

    def test_root_public_source(self):  # repeats, own and inherited bold, override, underline, highlight, a cell with all three; strike, raise and colour as before
        r, recs, got = self.read(src('public_review'))
        P = lambda t, w='400', d='none', b=None, c=K: (t, c, w, 'normal', d, b)
        self.assertEqual(got, [P('Left'), P('cargo', '700'), P('and'), P('cargo', '700'), P(';'), P('cargo', d='underline'), P(';'), P('cargo', b=[R0]), P(';'), P('cargo'), P('.'),
                               P('cargo', '700'), P('cargo'), P('cargo', '700', 'underline', [R0]), P('31'), P('old', d='line-through'), P('2'), P('cargo', c='rgb(255, 0, 0)')])
        self.assertEqual((r['source_style']['read'], recs[13]['owners'][0]['unit'][0], 'cell' in recs[13]['owners'][0]), (True, 't', True))  # the cell's own record
        self.assertNotIn('source_color', r)

    def test_root_background_and_italic_source(self):  # a semi-transparent or faded child never hides the yellow ancestor; opacity raw; italic
        _, _, got = self.read(src('design_review'))
        self.assertEqual(got, [('wide', K, '400', 'normal', 'none', [[0, 'color(display-p3 1 0 0 / 0.3)', 'none', '1'], Y1]), ('alpha', K, '400', 'normal', 'none', [[0, 'rgba(255, 0, 0, 0.3)', 'none', '1'], Y1]),
                               ('opacity', K, '400', 'normal', 'none', [[0, 'rgb(255, 0, 0)', 'none', '0.3'], Y1]), ('italic', K, '400', 'italic', 'none', [Y1]), ('emphasis', K, '400', 'italic', 'none', [Y1])])

    def test_invented_controls(self):
        _, recs, got = self.read(b'<style>.m{background:#ff0}.fl::first-letter{font-weight:700}</style><p><span class="m"><b>inner</b></span> <u><b>ub</b></u> <b><u>bu</u></b></p><p class="fl">Body</p>')
        self.assertEqual(got, [('inner', K, '700', 'normal', 'none', [Y1]), ('ub', K, '700', 'normal', 'underline', None), ('bu', K, '700', 'normal', 'underline', None), ('Body', K, '400', 'normal', 'none', None)])
        self.assertEqual([(x.get('style_pseudo'), x.get('pseudo')) for x in recs], [(None, None)] * 3 + [([['::first-letter', 'font-weight', '700']], None)])  # named; colour's own uncertainty untouched
        _, recs, got = self.read(b'<p>Shown <span style="visibility:hidden">gone</span></p>')
        self.assertEqual([(t, w, x.get('visibility'), x.get('owners') is None) for (t, _, w, _, _, _), x in zip(got, recs)], [('Shown', '400', None, False), ('gone', '400', 'hidden', True)])  # hidden: reading kept, no owner
        r, recs, got = self.read(b'<p style="background-image:url(missing.png)">Body</p>')  # a named picture nothing answers: raw value, the step says it is unproved
        self.assertEqual((r['status'], r['source_style']['read'], got[0][5][0][:2], got[0][5][0][3]), ('PARTIAL', False, [0, 'rgba(0, 0, 0, 0)'], '1')); self.assertRegex(got[0][5][0][2], r'^url\(".*missing\.png"\)$')

    def test_text_transform_is_the_native_computed_property(self):  # Root, display-property finding: the property as the browser computes it for each run's own element, never a printed string
        def tt(raw): _, recs, got = self.read(raw); return [(t, x.get('text_transform'), x.get('style_pseudo')) for (t, *_), x in zip(got, recs)]
        for raw, want in ((b'<p style="text-transform:uppercase">Amber kites drift</p>', [('Amber kites drift', 'uppercase', None)]),  # direct
                          (b'<div style="text-transform:uppercase"><p>Copper lanterns glow</p></div>', [('Copper lanterns glow', 'uppercase', None)]),  # inherited
                          (b'<style>.c{text-transform:capitalize}</style><p class="c">velvet river stones</p>', [('velvet river stones', 'capitalize', None)]),  # a sheet rule
                          (b'<p style="text-transform:uppercase">Quiet <span style="text-transform:none">harbor</span> bells</p>', [('Quiet', 'uppercase', None), ('harbor', 'none', None), ('bells', 'uppercase', None)]),  # a child overrides
                          (b'<style>p.f::first-line{text-transform:uppercase}</style><p class="f">opening words here</p>', [('opening words here', 'none', [['::first-line', 'text-transform', 'uppercase']])]),  # pseudo only: named uncertainty, no character reach
                          (b'<p><b>Plain meadow text</b></p>', [('Plain meadow text', 'none', None)])):  # untransformed: the browser's own 'none'
            with self.subTest(raw=raw[:48]): self.assertEqual(tt(raw), want)
        raw = b'<p style="text-transform:lowercase">Silver Pine</p><p>Silver Pine</p>'; _, recs, got = self.read(raw)  # repeated identical text: each its own source and value
        self.assertEqual([(t, x['text_transform'], x['at']['byte_start']) for (t, *_), x in zip(got, recs)], [('Silver Pine', 'lowercase', raw.index(b'Silver')), ('Silver Pine', 'none', raw.rindex(b'Silver'))])
        r, recs, got = self.read('<meta charset="utf-8"><p lang="tr" style="text-transform:uppercase">istanbul straße</p>'.encode())  # language-sensitive: the raw text and its source stay, only the property is claimed
        self.assertEqual(([u['text'] for u in r['units'] if u['kind'] == 'text'], [(t, x['text_transform']) for (t, *_), x in zip(got, recs)]), (['istanbul straße'], [('istanbul straße', 'uppercase')]))
        r, recs, _ = self.read(b'<link rel="stylesheet" href="missing.css"><p class="x">distant shore</p>')  # a sheet nothing answers: unproved, the render's reading only as fallback
        self.assertEqual((r['status'], r['source_style']['read'], 'records' in r['source_style'], [x.get('text_transform') for x in recs]), ('PARTIAL', False, False, ['none']))

    def test_root_candidate_review_sources(self):  # Root's six controls (checked in)
        Y2, I = [2, 'rgb(255, 255, 0)', 'none', '1'], 'background image content not read'
        _, _, got = self.read(src('opacity_without_background'))  # a transparent ancestor's own opacity is kept, raw
        self.assertEqual(got, [('cargo', K, '700', 'normal', 'none', [[1, 'rgba(0, 0, 0, 0)', 'none', '0.3'], Y2])])
        _, _, got = self.read(src('colour_control')); self.assertEqual(got[0][5], [[0, 'rgb(255, 0, 0)', 'none', '0.3'], Y1])
        r, _, got = self.read(src('plain_background_control'))  # a plain colour: no picture, nothing unread
        self.assertEqual((r['status'], got[0][5], r['generated_content'].get('background_images')), ('OK', [R0], None))
        r, _, got = self.read(src('available_background_image'))  # an available picture behind the text: kept raw, said unread
        self.assertEqual((r['status'], r['generated_content']['why'], [x['node'] for x in r['generated_content']['background_images']]), ('PARTIAL', [I], ['P']))
        self.assertTrue(got[0][5][0][2].startswith('url("data:image/svg+xml;base64,') and r['generated_content']['background_images'][0]['value'] == got[0][5][0][2])
        r, recs, got = self.read(src('pseudo_bold_control')); self.assertEqual((got[0][1], recs[0].get('style_pseudo'), recs[0].get('pseudo')), (K, [['::first-letter', 'font-weight', '700']], None))
        r = self.read(src('generated_empty_owner'))[0]; g = r['generated_content']  # no run, no owner text: PARTIAL; the snapshot's own ancestor stack kept raw
        self.assertEqual((r['status'], [(x['fragments'], x.get('background')) for x in g['records']]), ('PARTIAL', [(['cargo'], [Y2])]))

    def test_every_background_image_is_said_unread(self):  # an empty owner, a cell, a pseudo element, a missing picture, a gradient (no image parser): each said, raw
        PNG, I = 'data:image/gif;base64,R0lGODlhAQABAAAAACw=', 'background image content not read'
        for html, node in ((b'<div style="width:9px;height:9px;background-image:url(%s)"></div><p>Body</p>', 'DIV'), (b'<table><tr><td style="background-image:url(%s)">12</td></tr></table>', 'TD'),
                           (b'<style>p::before{content:"x ";background-image:url(%s)}</style><p>Body</p>', '::before'), (b'<p style="background-image:url(missing.png)">Body</p>%s', 'P'),
                           (b'<p style="background-image:linear-gradient(red,blue)">Body</p>%s', 'P')):
            with self.subTest(node=node, html=html[:40]):
                raw = html % PNG.encode() if b'%s' in html else html
                r = self.read(raw)[0]; g = r['generated_content']
                self.assertEqual((r['status'], I in g['why'], [x['node'] for x in g['background_images']]), ('PARTIAL', True, [node]))

    def test_runs_keep_their_native_boxes_and_one_frame(self):  # raw [x, y, width, height] CSS-pixel client rectangles as getClientRects gives them (no rounding, no sort), one frame per page; source order unchanged
        def page(raw):
            route, recs, got = self.read(raw); s = route['source_style']; fr = (s if 'frame' in s else s['fallback'])['frame']
            self.assertEqual((sorted(fr), fr['scroll']), (['device_pixel_ratio', 'scroll', 'viewport'], [0, 0])); return route, recs, {t: x.get('boxes') for (t, *_), x in zip(got, recs)}
        _, recs, b = page(src('flex_order'))  # written: Rafts before Later; displayed: Later above Rafts
        self.assertEqual([r['at']['byte_start'] for r in recs], sorted(r['at']['byte_start'] for r in recs)); self.assertLess(b['Later'][0][1], b['Rafts'][0][1])
        _, _, b = page(b'<p>First para</p><p>Second para</p>'); self.assertLess(b['First para'][0][1], b['Second para'][0][1])
        _, _, b = page('<meta charset="utf-8"><p dir="rtl">שלום עולם</p><p>after</p>'.encode()); self.assertGreater(b['שלום עולם'][0][0], 100)  # right-aligned (declared charset: undeclared non-ASCII stays unbound, as before)
        _, _, b = page(b'<p style="width:60px">one two three four five</p>'); self.assertGreater(len(b['one two three four five']), 1)  # one run, several line boxes
        _, _, b = page(b'<div style="column-count:2;width:300px"><p>Alpha</p><p>Beta</p><p>Gamma</p><p>Delta</p></div>'); self.assertTrue(b['Gamma'][0][1] < b['Beta'][0][1] and b['Gamma'][0][0] > b['Beta'][0][0])
        _, _, b = page(b'<p><span style="float:right">Right</span>Left text</p>'); self.assertGreater(b['Right'][0][0], b['Left text'][0][0])
        _, _, b = page(b'<p>Top written</p><p style="transform:translateY(-60px)">Moved up</p>'); self.assertLess(b['Moved up'][0][1], b['Top written'][0][1])
        _, recs, b = page(b'<p>Shown <span style="visibility:hidden">gone</span> end</p>')  # hidden: its raw boxes kept, never a visibility proof; no owner
        hidden = recs[[t for t in b].index('gone')]; self.assertEqual((hidden['visibility'], hidden['owners'], bool(b['gone'])), ('hidden', None, True))
        r, _, b = page(b'<style>p::before{content:"Note: "}</style><p>Body</p>')  # the snapshot's document coordinates meet the client frame at scroll (0, 0)
        g = r['generated_content']['records'][0]['bounds'][0]; self.assertAlmostEqual(g[0] + g[2], b['Body'][0][0], delta=1)
        r, recs, b = page(b'<link rel="stylesheet" href="missing.css"><p>Body</p>')  # refused: the readings stay a fallback, unproved
        self.assertEqual((r['source_style']['read'], bool(b['Body'])), (False, True))

    def test_boxes_equal_the_native_ranges_and_say_their_own_source(self):  # Root's six originals (checked in): every record's boxes are the native Range rectangles of its whole run, exactly (Root's independent readings, literal)
        NATIVE = {"preserved_edge_space": [["  Cargo  \n  ", "visible", [[8, 13, 70.453125, 15], [78.453125, 13, 0, 15], [8, 28, 15.65625, 15]]]], "entity_multiline": [["Crates & cases & cartons", "visible", [[8, 16, 57.328125, 17], [8, 34, 50.203125, 17], [8, 52, 46.203125, 17]]]], "bidi_transform": [["אבג 234 XYZ", "visible", [[1294.859375, 25.375, 32.890625, 17], [1327.75, 25.375, 4, 17], [1331.75, 25.375, 24, 17], [1355.75, 25.375, 31, 17]]]], "first_letter_float": [["Crates and bags and cases", "visible", [[8, 17, 28.015625, 46], [36.015625, 16, 57.3125, 17], [36.015625, 34, 56.4375, 17], [36.015625, 52, 33.765625, 17]]]], "repeat_occurrences": [["Cargo", "visible", [[8, 16, 38.8125, 17]]], ["Cargo", "visible", [[98, 50, 38.8125, 17]]]], "hidden_positive": [["Shown", "visible", [[8, 16, 44.453125, 17]]], ["Hidden", "hidden", [[8, 50, 47.109375, 17]]]]}
        for k, runs in NATIVE.items():
            with self.subTest(k):
                raw = src(k); route, recs, got = self.read(raw); fr = route['source_style']['frame']
                self.assertEqual((route['status'], fr), ('OK', {'viewport': [1400, 1000], 'scroll': [0, 0], 'device_pixel_ratio': 1}))
                measured = [(raw[x['boxes_at']['byte_start']:x['boxes_at']['byte_end_exclusive']] if 'boxes_at' in x else raw[x['at']['byte_start']:x['at']['byte_end_exclusive']]).decode() for x in recs]
                got = [(t, x.get('visibility', 'visible'), x['boxes']) for t, x in zip(measured, recs)]
                if k == 'first_letter_float':  # the route's own marked render splits the last line at a text-node boundary: as returned, never collapsed; its union is the native line exactly
                    *head, (x0, y0, w0, h0), (x1, y1, w1, h1) = got[0][2]; self.assertEqual((y1, h1, x1), (y0, h0, x0 + w0))  # one line: the same top and height, exactly contiguous
                    got = [(got[0][0], got[0][1], head + [[x0, y0, w0 + w1, h0]])]  # then their union must be the native line (truth unchanged; nothing normalized at runtime)
                self.assertEqual(got, [(t.replace('&', '&amp;') if k == 'entity_multiline' else t, v, b) for t, v, b in runs])
        recs = self.read(src('preserved_edge_space'))[1]  # the boxes measure "  Cargo  \n  ", the record's `at` and owner place stay "Cargo"
        self.assertEqual((recs[0]['owners'][0]['text_at'], recs[0]['at']['byte_end_exclusive'] - recs[0]['at']['byte_start'], recs[0]['boxes_at']['byte_end_exclusive'] - recs[0]['boxes_at']['byte_start']), ([[1, 6]], 5, 12))
        recs = self.read(src('hidden_positive'))[1]; self.assertEqual([x.get('owners') is None for x in recs], [False, True])  # hidden boxes never become shown content

    def test_generated_text_carries_the_same_readings(self):  # the same native properties in the generated-content capture
        raw = b'<style>p::before{content:"Note: ";font-weight:700;font-style:italic;background-color:#ff0}</style><p>Body</p>'
        route, _ = html_route.prepare(raw, 'g.htm', hashlib.sha256(raw).hexdigest(), self.browser)
        c = route['generated_content']['records'][0]['computed']
        self.assertEqual((c['font-weight'], c['font-style'], c['background-color'], c['background-image']), ('700', 'italic', 'rgb(255, 255, 0)', 'none'))


if __name__ == '__main__':
    unittest.main()
