"""Generated content and native lists (Root's bounded release): the page's own layout of generated content (one DOMSnapshot of the screen step's page)
is kept as `generated_content` - fragments, computed readings, owner visibility - and placed in a unit's text only where its owner's whole source content
is proved (offset from anchor._reading); anything required but unplaced, a generated picture, or no reading leaves the route PARTIAL. List items keep
the parser's own list membership (`lists`). Controls: Root's public review sources (checked in, byte-exact: fixtures/generated_content_controls.json), Fable's own controls."""
import hashlib
import json
import unittest
from pathlib import Path
from unittest import mock

from driver.prepare.convert import edgartools_html, html_route, screen_grid

CONTROLS = json.loads((Path(__file__).parent / 'fixtures' / 'generated_content_controls.json').read_text(encoding='utf-8'))  # Root's public review sources, byte-exact


def src(k, part='cases'):  # a checked-in source's bytes, checked against the fixture's own sha256
    b = CONTROLS[part][k].encode('utf-8')
    assert hashlib.sha256(b).hexdigest() == CONTROLS[('formatting_' if part != 'cases' else '') + 'sources_sha256'][k], k
    return b


def rebuild(route):  # the test consumer: each unit's (or cell's) text with its placed generated records at their offsets
    gen, out = (route.get('generated_content') or {}).get('records', []), []
    for u in route['units']:
        for cell, x in [(None, u)] if u.get('kind') != 'table' else [(c['anchor']['byte_start'], c) for c in u.get('cells') or [] if isinstance(c.get('anchor'), dict)]:
            t = x.get('text') or ''
            for r in sorted(reversed([r for r in gen if r.get('bound') and r['at']['unit'] == u['id'] and r['at'].get('cell') == cell]), key=lambda r: -r['at']['offset']): t = t[:r['at']['offset']] + ''.join(r['fragments']) + t[r['at']['offset']:]  # one offset: in record order
            out.append(t)
    return out


class Generated(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright  # required: a missing install fails the suite
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def route(self, raw):
        route, _ = html_route.prepare(raw, 'g.htm', hashlib.sha256(raw).hexdigest(), self.browser)
        self.assertEqual(json.loads(json.dumps(route)), route)  # the contract survives JSON
        return route

    def check(self, raw, status, text, why=()):
        r = self.route(raw); g = r['generated_content']
        self.assertEqual((g['status'], g['why'], rebuild(r)), (status, list(why), text)); return r

    def test_root_controls(self):
        self.check(src('inline_quote'), 'complete', ['The “quoted” text'])  # placed inside the unit by the existing source-to-text reading
        r = self.check(src('list_stray_text'), 'complete', ['Outside', '• Inside'])
        self.assertEqual([(u['text'], u.get('lists')) for u in r['units']], [('Outside', None), ('Inside', [{'list': 0, 'ordered': False, 'item': 0}])])  # a stray text is no item
        r = self.check(src('transparent_shadow'), 'complete', ['Read this Body'])  # alpha 0 is no proof of absence: required, paint uncertain
        self.assertEqual([(x['required'], x.get('paint')) for x in r['generated_content']['records']], [(True, 'uncertain')])
        self.check(src('unmarked_text_owner'), 'PARTIAL', ['Original', 'Body'], ['generated text not bound: native text under the owner follows no source run'])
        self.check(src('ordinary'), 'complete', ['Body'])
        self.check(src('empty_quote'), 'PARTIAL', [], ['generated text not bound: the owner has no proved source text'])
        self.check(src('inline_list_item'), 'complete', ['1. Body'])
        r = self.check(src('opacity_ancestor'), 'complete', [])  # the owner is hidden by the existing rule: raw reading only
        self.assertEqual([(x['fragments'], x['required']) for x in r['generated_content']['records']], [(['Ghost'], False)])
        self.check(src('summary'), 'complete', ['▾ Choice', 'Body'])
        self.check(src('empty_generated'), 'PARTIAL', ['Body'], ['generated text not bound: the owner has no proved source text'])

    def test_owners_counters_repeats_and_hidden(self):
        self.check(b'<style>p::before{content:attr(data-label)}</style><p data-label="Marker 17 ">Body 29</p>', 'complete', ['Marker 17 Body 29'])
        self.check(b'<style>body{counter-reset:n} p.c::before{counter-increment:n;content:"Item " counter(n) ". "}</style><p class="c">A</p><p class="c">B</p>', 'complete', ['Item 1. A', 'Item 2. B'])
        self.check(b'<style>.r::before{content:"Rep "}</style><p class="r">one</p><p class="r">two</p>', 'complete', ['Rep one', 'Rep two'])  # the same string, each its own owner
        self.check(b'<style>p::before{content:"X ";display:none}</style><p>Body</p>', 'complete', ['Body'])

    def test_generated_text_keeps_strike_and_raise(self):  # Root's formatting sources (checked in, verbatim): own and ancestor strike, raised, ordinary
        S = {k: src(k, 'formatting_sources') for k in CONTROLS['formatting_sources']}
        got = {k: [x.get('formatting') for x in self.check(v, 'complete', [{'raised': '29'}.get(k, 'Loss 9')])['generated_content']['records']] for k, v in S.items()}
        self.assertEqual(got, {'own_strike': [{'struck': True}], 'ancestor_strike': [{'struck': True}], 'raised': [{'vertical_align': 'super'}], 'ordinary': [None]})

    def test_lists_keep_native_membership(self):
        r = self.check(b'<ol start="3"><li>Third</li><li value="7">Seventh</li></ol>', 'complete', ['3. Third', '7. Seventh'])  # the printed marker from layout; no ordinal arithmetic
        self.assertEqual([u.get('lists') for u in r['units']], [[{'list': 0, 'ordered': True, 'item': 0}], [{'list': 0, 'ordered': True, 'item': 1}]])
        r = self.check(b'<ol><li>Outer<ul><li>Inner</li></ul></li><li>Next</li></ol>', 'complete', ['1. Outer', '◦ Inner', '2. Next'])
        self.assertEqual(r['units'][1]['lists'], [{'list': 0, 'ordered': True, 'item': 0}, {'list': 1, 'ordered': False, 'item': 0}])  # nested: the outer item kept
        r = self.check(b'<ul><li><p>Para one</p><p>Para two</p></li><li>Two</li></ul>', 'complete', ['• Para one', 'Para two', '• Two'])
        self.check(b'<ul><li> Leading</li><li>Plain </li></ul><style>p::after{content:" end"}</style><p>Tail </p>', 'complete', [' • Leading', '• Plain ', 'Tail end '])  # a collapsed edge space no unit holds (6 real list documents: 38 markers); the parser's own spaces stay, the marker before the first shown character
        self.assertEqual([u['lists'][0]['item'] for u in r['units']], [0, 0, 1])  # a split item's units share it

    def test_unproved_owners_and_pictures_stay_partial(self):
        self.check(b'<style>p.x::before{content:"Fig "}</style><p class="x"><img src="a.png" width="8" height="8"></p>', 'PARTIAL', [''], ['generated text not bound: the owner has no proved source text'])
        self.check(b'<table><tr><li>Fostered</li><td>c</td></tr></table>', 'PARTIAL', ['c'], ['generated text not bound: the owner text is not held by one unit at its edge'])
        self.check(b'<style>div::before{content:"Before "}</style><div><textarea>Original</textarea></div>', 'PARTIAL', ['Original'], ['generated text not bound: native text under the owner follows no source run'])
        N = ['generated non-text content not extracted']  # by the native tokens of the computed content, never by box geometry
        r = self.check(b'<style>p::before{content:"Fig " url(x.png)}</style><p>Body</p>', 'PARTIAL', ['Fig Body'], N)  # text beside it does not hide the picture
        self.assertRegex(' | '.join(r['generated_content']['records'][0]['non_text']), r'^url\("[^"]*/x\.png"\)$')  # raw, as computed (resolved against the page's base)
        self.check(b'<style>p::before{content:url(x.png)}</style><p>Body</p>', 'PARTIAL', ['Body'], N)
        self.check(b'<style>p::before{content:linear-gradient(red,blue)}</style><p>Body</p>', 'PARTIAL', ['Body'], N)  # an image without a URL
        self.check(b'<style>li{list-style-image:url(x.png)}</style><ul><li>Item</li></ul>', 'PARTIAL', ['\u2022 Item'], N)  # a marker image (its unloaded fallback glyph laid out)
        self.check(b'<style>li::marker{content:url(x.png)}</style><ul><li>Item</li></ul>', 'PARTIAL', ['Item'], N)
        self.check(b'<style>p::before{content:"Fig " / "Alt"}</style><p>Body</p>', 'complete', ['Fig Body'])  # the alternative text is never shown

    def test_a_refused_capture_is_partial_with_its_reason(self):
        with mock.patch.object(screen_grid, 'GENERATED_STYLES', ['display', 'no-such-property-']):
            r = self.route(b'<p>Body</p>')
        g = r['generated_content']; self.assertEqual((g['read'], g['status'], g['why'], r['status']), (False, 'PARTIAL', ['generated content: no native reading'], 'PARTIAL'))
        self.assertIn('captureSnapshot', g['error'])


    # Root's review of v1 (its sources, checked in verbatim) and its class controls
    def test_root_review_sources(self):
        r = self.check(src('first_letter'), 'complete', ['Alpha body'])  # formats the original's first letter: no insertion
        self.assertEqual([(x['pseudo'], x['role'], x['bound'], x['required']) for x in r['generated_content']['records']], [('first-letter', 'formats', False, False)])
        self.check(src('plain_before'), 'complete', ['Added Alpha body'])
        r = self.check(src('hidden_owner_visible_before'), 'PARTIAL', [], ['generated text not bound: the owner text is not held by one unit at its edge'])  # painted (its own visibility); the hidden original is in no unit
        self.assertEqual([(x['visible'], x['required']) for x in r['generated_content']['records']], [(True, True)])
        r = self.check(src('opacity_parent'), 'complete', [])  # nothing painted
        self.assertEqual([(x['visible'], x['required']) for x in r['generated_content']['records']], [(False, False)])
        self.check(src('nested_quotes'), 'complete', ['The “A  ‘B’  C” text.'])  # the parser's own unit text (its double spaces, as on main), quotes at their native places

    def test_pseudo_classes(self):
        self.check(b'<style>li::first-letter, p::first-letter{color:red} p::after{content:" end"}</style><ol><li>Item</li></ol><p>Body</p>', 'complete', ['1. Item', 'Body end'])
        self.check(b'<style>p::before{content:"Added "} p::first-letter{color:red}</style><p>Alpha body</p>', 'PARTIAL', ['Alpha body'], ['generated text not bound: ::first-letter may format part of it'])  # its first letter: which text it took is not proved
        self.check(b'<style>p::first-letter{text-decoration:line-through}</style><p>Alpha body</p>', 'PARTIAL', ['Alpha body'], ['source text formatting by ::first-letter not carried'])

    def test_first_letter_over_generated_text(self):  # Root's whole/partial/ordinary first-letter sources (checked in), and the other consumptions
        P = ['generated text not bound: ::first-letter may format part of it']
        r = self.check(src('whole_generated_first_letter'), 'PARTIAL', ['Body'], P)  # it takes ALL of "Z": no fragment of the before's own
        self.assertEqual([(x['pseudo'], x['fragments'], x['required'], x['bound']) for x in r['generated_content']['records']], [('first-letter', ['Z'], False, False), ('before', [], True, False)])  # raw, kept
        self.check(src('partial_generated_first_letter'), 'PARTIAL', ['Body'], P)
        self.check(src('ordinary_source_first_letter'), 'complete', ['Body'])
        self.check(b'<style>p::before{content:""} p::first-letter{color:red}</style><p>Body</p>', 'complete', ['Body'])  # names no text: the first letter is the source's
        for c in (b'"("', b'open-quote', b'" "'):  # punctuation and a quote are taken; a space is not, but which part each holds is not proved: PARTIAL
            self.check(b'<style>p::before{content:%s} p::first-letter{color:red}</style><p>Body</p>' % c, 'PARTIAL', ['Body'], P)

    def test_a_formatting_pseudo_over_carried_source_text(self):  # Root's v3-review sources (checked in), and the disclosed interactions
        F = '<style>p::first-letter{%s}</style><p>Body</p>'
        H, U, P = ['source text in the units is hidden by ::first-letter'], ['source text in the units: its visibility under ::first-letter is not proved'], ['source text in the units: its paint under ::first-letter is not proved']
        r = self.check(src('hidden_format_letter'), 'PARTIAL', ['Body'], H)  # the page shows "ody": the original stays whole, the status says so
        self.assertEqual([(x['visible'], x['fragments']) for x in r['generated_content']['records']], [(False, ['B'])])
        self.check(src('transparent_format_letter'), 'PARTIAL', ['Body'], P)  # paint uncertain, never turned into hidden
        r = self.check(src('ordinary_format_letter'), 'complete', ['Body'])
        self.assertEqual([x['computed']['color'] for x in r['generated_content']['records']], ['rgb(255, 0, 0)'])  # its colour reading kept
        self.check((F % 'color:transparent;text-shadow:0 0 0 red').encode(), 'PARTIAL', ['Body'], P)  # a visible shadow: still not a proved paint
        self.check(b'<style>.h{visibility:hidden} .o{opacity:0} p::first-letter{color:red}</style><p class="h">Body</p><p class="o">Gone</p><p>Shown</p>', 'complete', ['Shown'])  # their text is in no unit
        self.check((F % 'color:red').replace('<p>', '<p style="text-decoration:line-through">').encode(), 'PARTIAL', ['Body'], ['source text formatting by ::first-letter not carried'])  # already struck: still flagged (units hold struck phrases, no places)
        real = screen_grid._generated
        def unknown(page, prefix):
            g = real(page, prefix)
            for x in g['records']: x['visible'], x['visible_error'] = None, 'resolveNode failed (test)'
            return g
        with mock.patch.object(screen_grid, '_generated', unknown):
            self.check((F % 'color:red').encode(), 'PARTIAL', ['Body'], U)  # unknown native visibility: never a verdict

    def test_a_failed_native_visibility_call(self):  # Root's resource control (invented): at either call, a process failure propagates; an ordinary one leaves it PARTIAL
        from playwright.sync_api import CDPSession
        from driver.prepare.get.acquire import StorageError
        raw, real = b'<style>p::before{content:"Count "}</style><p>17</p>', CDPSession.send
        r = self.check(raw, 'complete', ['Count 17'])  # the real native reading
        self.assertEqual([x['visible'] for x in r['generated_content']['records']], [True])
        def failing(method, cls):
            def send(session, m, params=None):
                if m == method: raise cls('injected')
                return real(session, m, params)
            return send
        for method in ('DOM.resolveNode', 'Runtime.callFunctionOn'):
            for cls in (OSError, StorageError, ImportError, MemoryError):  # never a content verdict
                with self.subTest(method=method, error=cls.__name__), mock.patch.object(CDPSession, 'send', failing(method, cls)), self.assertRaises(cls): self.route(raw)
            with self.subTest(method=method, error='RuntimeError'), mock.patch.object(CDPSession, 'send', failing(method, RuntimeError)):
                r = self.check(raw, 'PARTIAL', ['Count 17'], ['generated text: its visibility is not proved'])  # its raw reading and error kept
                self.assertEqual([(x['visible'], x['visible_error']) for x in r['generated_content']['records']], [(None, "RuntimeError('injected')")])

    def test_an_unknown_native_pseudo_type_stays_raw_and_partial(self):  # this Chromium's snapshot shows no other type: a real ::before reading, its type renamed
        real = screen_grid._generated
        def renamed(page, prefix):
            g = real(page, prefix)
            for x in g['records']: x['pseudo'] = 'scroll-marker'
            return g
        with mock.patch.object(screen_grid, '_generated', renamed):
            r = self.check(b'<style>p::before{content:"Go "}</style><p>Body</p>', 'PARTIAL', ['Body'], ['native pseudo element ::scroll-marker not handled'])  # never read as a before, never dropped
        self.assertEqual([(x['pseudo'], x['role'], x['bound'], x['fragments']) for x in r['generated_content']['records']], [('scroll-marker', None, False, ['Go '])])

    def test_visibility_at_the_pseudo(self):
        self.check(b'<style>p.h{visibility:hidden} p.h::before{content:"H "}</style><p class="h">Body</p><p>Shown</p>', 'complete', ['Shown'])  # inherited hidden
        r = self.check(b'<style>p::before{content:"T ";color:transparent}</style><p>Body</p>', 'complete', ['T Body'])  # alpha 0: paint uncertain, still required
        self.assertEqual([(x['required'], x.get('paint')) for x in r['generated_content']['records']], [(True, 'uncertain')])
        self.check(b'<style>p::before{content:"Ghost ";opacity:0}</style><p>Body</p>', 'complete', ['Body'])  # its own opacity 0

    def test_insertion_order_cells_and_reversed_lists(self):
        self.check(b'<p><q><q>B</q></q> end</p>', 'complete', ['“‘B’” end'])  # one offset each side: outer open first, inner close first
        self.check(b'<style>li::before{content:"Pre "}</style><ol><li>Item</li></ol>', 'complete', ['1. Pre Item'])  # marker, then before
        self.check(b'<style>td::before{content:"$"}</style><table><tr><td>12</td><td>Name</td></tr></table>', 'complete', ['$12', '$Name'])  # in each cell's own text
        self.check(b'<ol reversed><li>a</li><li>b</li></ol><ol reversed start="5"><li>c</li><li value="9">d</li></ol>', 'complete', ['2. a', '1. b', '5. c', '9. d'])  # the printed markers, no ordinal arithmetic


class Identity(unittest.TestCase):
    def test_a_parse_saved_under_the_old_settings_is_refused(self):  # the output changed (list membership): a saved parse under the old settings is never reused
        import tempfile
        from benchmarks.prepare.grader.adapters import cache
        old = {k: v for k, v in edgartools_html.SETTINGS.items() if k != 'lists'}
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / 'p.json'; out.write_text('{}'); meta = Path(d) / 'p.meta.json'
            cache.save(meta, [out], sha256='s', version='v', settings=old, status='OK', tool_seconds=0)
            with self.assertRaisesRegex(RuntimeError, 'other settings'): cache.reuse(meta, 's', edgartools_html.SETTINGS)
            cache.save(meta, [out], sha256='s', version='v', settings=edgartools_html.SETTINGS, status='OK', tool_seconds=0)
            self.assertEqual(cache.reuse(meta, 's', edgartools_html.SETTINGS)['status'], 'OK')


if __name__ == '__main__':
    unittest.main()
