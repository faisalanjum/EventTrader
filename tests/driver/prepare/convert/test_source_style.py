"""`source_style` (the widened source-run record, formerly `source_color`): for every source run, the page's own computed foreground colour, font
weight, font style, decorations in effect and the raw background stack of the element holding its text and its ancestors ([depth, colour, image,
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

    def test_generated_text_carries_the_same_readings(self):  # the same native properties in the generated-content capture
        raw = b'<style>p::before{content:"Note: ";font-weight:700;font-style:italic;background-color:#ff0}</style><p>Body</p>'
        route, _ = html_route.prepare(raw, 'g.htm', hashlib.sha256(raw).hexdigest(), self.browser)
        c = route['generated_content']['records'][0]['computed']
        self.assertEqual((c['font-weight'], c['font-style'], c['background-color'], c['background-image']), ('700', 'italic', 'rgb(255, 255, 0)', 'none'))


if __name__ == '__main__':
    unittest.main()
