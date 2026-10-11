"""Strike-through the scanner cannot certify (not `struck_certain`, `plain_certain` true or false): the existing screen render's own decoration of each
source-bound text run decides it (`SYMBOLS_JS` decor -> `screen_grid.decorations` -> `source_formatting.rendered`), in the same single render, places from
the runs' bytes. Struck, unstruck and hidden runs are definite; literal, unbound and paint-dependent runs stay unresolved and make the route PARTIAL.
Truths are the CSS cascade/decoration rules, authored with each source. Offline Chrome; playwright is required."""
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch

from driver.prepare.convert import anchor, html_route, screen_grid as sg, source_formatting

CONTROL = (Path(__file__).with_name('fixtures') / 'native_formatting_control.html').read_bytes()  # the public invented control (Test Agent, 2026-10-11)
D = lambda style, body: b'<!doctype html><html><head>' + (b'<style>' + style + b'</style>' if style else b'') + b'</head><body>' + body + b'</body></html>'
X = b'.x{text-decoration:line-through}'


class Rendered(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.pw.stop()

    def run_route(self, raw):
        pages, real = [0], sg._offline_page
        def counted(*a, **k): pages[0] += 1; return real(*a, **k)
        with patch.object(sg, '_offline_page', counted): route, facts = html_route.prepare(raw, 'pub/x.htm', hashlib.sha256(raw).hexdigest(), self.browser)
        items = [x for u in route['units'] for x in ((u.get('cells') or []) if u.get('kind') == 'table' else [u])]
        return route, facts, pages[0], items

    def struck(self, items): return {x.get('text'): (x.get('struck'), x.get('struck_at')) for x in items if x.get('struck') or x.get('struck_at')}

    def test_the_public_failure_is_read_in_the_one_screen_render(self):
        self.assertFalse(anchor.Visible(CONTROL).struck_certain)
        route, facts, pages, items = self.run_route(CONTROL)
        self.assertEqual(pages, 2); self.assertEqual(route['status'], 'OK'); self.assertEqual(route['route']['settings']['source_formatting'], 'rendered')  # 2: the one native loader reads the original's charset in its own page first (a cost, Root 2026-10-11)
        self.assertEqual(self.struck(items), {'Retired': (['Retired'], [[0, 7]]), 'Replace after forty days sixty days.': (['forty days'], [[14, 19], [20, 24]])})
        self.assertEqual((facts['formatting'], facts['screen']['source_formatting'], route['route']['name']), (None, 2, 'edgartools-html+source-formatting+screen'))

    def test_cascade_order_specificity_importance_and_inheritance(self):
        cases = {  # source -> the texts the page draws struck (CSS cascade and decoration propagation)
            D(X, b'<table><tr><td><span class="x">Retired</span></td><td>Active</td></tr></table>'): {'Retired'},
            D(X + b'.x{text-decoration:none}', b'<p><span class="x">o1</span> a</p>'): set(),
            D(b'.x{text-decoration:none}' + X, b'<p><span class="x">o2</span> a</p>'): {'o2'},
            D(b'span.x{text-decoration:line-through}.x{text-decoration:none}', b'<p><span class="x">o3</span> a</p>'): {'o3'},
            D(b'.x{text-decoration:line-through!important}.x{text-decoration:none}', b'<p><span class="x">o4</span> a</p>'): {'o4'},
            D(X + b'.u{text-decoration:underline}', b'<p><span class="x">a1<span class="u">b1</span></span> c</p>'): {'a1', 'b1'},  # two source runs (markup between), both drawn struck
            D(X + b'.ib{display:inline-block}', b'<div class="x">o5 <span class="ib">boxed</span></div>'): {'o5'},
        }
        for raw, want in cases.items():
            with self.subTest(raw=raw):
                route, facts, pages, items = self.run_route(raw)
                self.assertEqual(pages, 2 if anchor.Visible(raw).certain else 3); self.assertEqual(route['status'], 'OK')  # an uncertain reading adds only the existing visibility render (2 loads), whose charset read the document's one Source keeps; a certain one pays the native loader's charset read (a cost, Root 2026-10-11)
                got = {anchor.squash(p) for x in items for p in x.get('struck') or []}
                self.assertEqual(got, {anchor.squash(w) for w in want})

    def test_root_trigger_class_plain_certain_but_struck_uncertain(self):
        body = b'<p>Replace after <s>forty days</s> sixty days.</p>'
        for style, want in ((b'.unused{text-decoration:none}', ['forty days']), (b's{text-decoration:none}', None)):
            raw = D(style, body); v = anchor.Visible(raw)
            self.assertTrue(v.certain and v.plain_certain and not v.struck_certain)
            route, facts, pages, items = self.run_route(raw)
            self.assertEqual((pages, route['status']), (2, 'OK')); self.assertEqual(items[0].get('struck'), want)  # 2: the native loader's charset read, then the render (a cost)

    def test_repeated_equal_words_are_placed_by_their_bytes(self):
        route, facts, pages, items = self.run_route(D(X, b'<p>Retired and <span class="x">Retired</span> now</p>'))
        self.assertEqual(self.struck(items), {'Retired and Retired now': (['Retired'], [[12, 19]])})  # the second printed Retired: characters 12-19

    def test_certain_sources_keep_the_existing_path(self):
        for raw, want in ((D(b'', b'<p>keep <s>gone</s> keep2</p>'), ['gone']), (D(b'p{color:blue}', b'<p>keep <s>gone</s></p>'), ['gone']), (D(b'', b'<p>plain</p>'), None)):
            route, facts, pages, items = self.run_route(raw)
            self.assertIs(route['route']['settings']['source_formatting'], True); self.assertEqual(items[0].get('struck'), want); self.assertNotIn('source_formatting', route)

    def test_hidden_text_is_excluded_not_partial(self):
        route, facts, pages, items = self.run_route(D(X + b'.hid{display:none}', b'<p>keep <span class="x hid">secret</span> <span class="x">gone</span></p>'))
        self.assertNotIn('source formatting', route.get('error') or ''); self.assertEqual(self.struck(items) and [p for x in items for p in x.get('struck') or []], ['gone'])

    def test_unproved_paint_unbound_and_literal_runs_stay_unresolved_and_partial(self):
        for raw, why in ((D(b'.x{text-decoration:line-through;text-decoration-color:transparent}', b'<p><span class="x">ghost</span> a</p>'), 'unresolved: paint'),
                         (D(X, b'<table class="x"><tr>moved<td>c</td></tr></table>'), 'unresolved: visibility'),  # the parser moves it: its visibility verdict is itself unresolved, said once by page visibility
                         (D(X, b'<p>a</p><textarea>typed</textarea>'), 'unresolved: literal text')):
            with self.subTest(why=why):
                route, facts, pages, items = self.run_route(raw)
                self.assertEqual(route['status'], 'PARTIAL'); self.assertIn('page visibility:' if why == 'unresolved: visibility' else 'source formatting:', route['error'])
                self.assertIn(why, [r[2] for r in route['source_formatting']['unresolved']])
                self.assertFalse(any(x.get('struck_at') for x in items if any(r[0] < a['byte_end_exclusive'] and a['byte_start'] < r[1] for r in route['source_formatting']['unresolved'] for a in anchor.spans(x.get('anchor')) if 'byte_start' in a)))

    def test_a_failed_render_gives_no_verdict_and_partial(self):
        with patch.object(sg, 'measure', side_effect=RuntimeError('boom')):
            route, facts, pages, items = self.run_route(D(X, b'<p><span class="x">gone</span></p>'))
        self.assertEqual(route['status'], 'PARTIAL'); self.assertIn('screen step:', route['error']); self.assertIsNone(facts['formatting'])  # the render failed: no verdict, nothing certified
        self.assertFalse(any(x.get('struck') for x in items))


    def test_nested_tables_holder_and_child_cells(self):  # truths from the source: <s>, a cell's own class, inline inheritance; a strike on a holder's sibling span reaches no child
        raw = D(X, b'<table><tr><td>Holder <table><tr><td>Inner plain</td><td><s>Inner gone</s></td></tr></table></td><td>Inner gone</td></tr></table>'
                   b'<table><tr><td><span class="x">Head</span> <table><tr><td>Free</td><td class="x">Own strike</td><td><s>Old <i>term</i></s> kept</td></tr></table></td></tr></table>')
        route, facts, pages, items = self.run_route(raw)
        self.assertEqual((route['status'], route['error'], pages), ('OK', None, 2))  # 2: the native loader's charset read, then the render (a cost)
        tables = {u['id']: u for u in route['units'] if u.get('kind') == 'table'}; cell = lambda t, r, c: next(x for x in tables[t]['cells'] if (x['r'], x['c']) == (r, c))
        def places(text, *words):  # each word printed once in the item's text: its place there
            self.assertTrue(all(text.count(w) == 1 for w in words), text); return [[text.index(w), text.index(w) + len(w)] for w in words]
        holder, child = cell('t0', 0, 0), cell('t1', 0, 1)
        self.assertEqual((holder['tables'], tables['t1']['cell']['table'], tables['t1']['cell']['r'], tables['t1']['cell']['c']), (['t1'], 't0', 0, 0))  # holder and child owned apart
        self.assertTrue(all(w in holder['text'] for w in ('Holder', 'Inner plain', 'Inner gone')))  # the outer cell keeps the inner text, flattened
        (i, _), = places(holder['text'], 'Inner gone'); self.assertEqual((holder['struck'], holder['struck_at']), (['Inner gone'], [[i, i + 5], [i + 6, i + 10]]))  # 'Inner' alone stands twice
        self.assertEqual((child['text'], child['struck'], child['struck_at']), ('Inner gone', ['Inner gone'], [[0, 5], [6, 10]]))
        for t, r, c in (('t1', 0, 0), ('t0', 0, 1)): self.assertFalse('struck' in cell(t, r, c) or 'struck_at' in cell(t, r, c))  # plain inner text; the same words repeated in another cell
        outer = cell('t2', 0, 0); self.assertEqual(tables['t3']['cell']['table'], 't2')
        self.assertEqual(outer['struck_at'], places(outer['text'], 'Head', 'Own', 'strike', 'Old', 'term'))  # the holder carries its own strike and its children's, never 'Free' or 'kept'
        free, own, old = (cell('t3', 0, c) for c in range(3))
        self.assertFalse('struck' in free or 'struck_at' in free)  # the holder's strike is on a sibling span: it does not reach this child
        self.assertEqual((own['text'], own['struck_at']), ('Own strike', [[0, 3], [4, 10]]))  # the cell's own decoration
        self.assertEqual((old['text'], old['struck_at'], ''.join(old['struck']).replace(' ', '')), ('Old term kept', [[0, 3], [4, 8]], 'Oldterm'))  # inherited by <i>; 'kept' is not struck


class RenderedStep(unittest.TestCase):  # source_formatting.rendered alone, on a given verdict: which converter claims may go
    def test_only_proved_unstruck_runs_drop_a_claim_and_unresolved_keeps_it(self):
        raw = b'<p>one</p><p>two</p>'; vis = anchor.Visible(raw); a1, a2 = raw.index(b'one'), raw.index(b'two')
        def route(): return {'route': {'name': 'r', 'settings': {}}, 'units': [{'kind': 'text', 'text': 'one', 'anchor': {'byte_start': a1, 'byte_end_exclusive': a1 + 3}, 'struck': ['one']},
                                                                               {'kind': 'text', 'text': 'two', 'anchor': {'byte_start': a2, 'byte_end_exclusive': a2 + 3}, 'struck': ['two']}]}
        r = route(); n, undecided = source_formatting.rendered(vis, r, [[a1, a1 + 3, 'unstruck'], [a2, a2 + 3, 'unresolved: unbound']])
        self.assertEqual((n, [u.get('struck') for u in r['units']]), (0, [None, ['two']])); self.assertEqual(undecided, [[a2, a2 + 3, 'unresolved: unbound']])
        r = route(); self.assertEqual(source_formatting.rendered(vis, r, None), (None, None)); self.assertEqual([u.get('struck') for u in r['units']], [['one'], ['two']])

    def test_a_mixed_carrier_keeps_the_converter_reading_and_claims_no_places(self):  # Root's mixed-claim control (root_formatting_mixed_claim_v1)
        raw = b'<p>one two</p>'; vis = anchor.Visible(raw); a = raw.index(b'one')
        def route(): return {'route': {'name': 'r', 'settings': {}}, 'units': [{'kind': 'text', 'text': 'one two', 'anchor': {'byte_start': a, 'byte_end_exclusive': a + 7}, 'struck': ['two'], 'struck_at': [[4, 7]]}]}
        r = route(); n, undecided = source_formatting.rendered(vis, r, [[a, a + 3, 'struck'], [a + 4, a + 7, 'unstruck']])
        self.assertEqual((n, r['units'][0]['struck'], r['units'][0]['struck_at'], undecided), (1, ['one'], [[0, 3]], []))  # every run proved: the source's reading replaces the claim
        r = route(); n, undecided = source_formatting.rendered(vis, r, [[a, a + 3, 'struck'], [a + 4, a + 7, 'unresolved: unbound']])
        self.assertEqual((n, r['units'][0]['struck'], 'struck_at' in r['units'][0], undecided), (0, ['two'], False, [[a + 4, a + 7, 'unresolved: unbound']]))  # not qualified whole: the converter's reading stays, no places

    def test_a_struck_mask_must_cover_every_search_form_character(self):
        vis = anchor.Visible(b'<p>one</p>')
        with self.assertRaises(ValueError): anchor.struck_at(vis, {'text': 'one', 'anchor': {'byte_start': 3, 'byte_end_exclusive': 6}}, b'\x01')


class DecorationVerdicts(unittest.TestCase):  # screen_grid.decorations on given render answers: every branch, never a guess
    def test_each_verdict_branch(self):
        raw = b'<p>alpha <span>beta</span> gamma</p><p>delta</p>'; vis = anchor.Visible(raw); runs, _ = sg.symbol_runs(raw, vis)
        ids = {raw[c[0][0]:c[-1][1]].decode().strip(): str(k) for k, (_, c, h, ok) in enumerate(runs) if sg._glyphs(raw, c)[1]}
        good = {'decor': {ids['alpha']: ['none', 'alpha '], ids['beta']: ['line-through', 'beta'], ids['gamma']: ['underline line-through', ' gamma'], ids['delta']: ['none', 'wrong']},
                'decorations': 'none', 'marks': {}, 'plain': ''}
        v = {raw[s:e].decode().strip(): w for s, e, w in sg.decorations(raw, vis, runs, good)}
        self.assertEqual(v, {'alpha': 'unstruck', 'beta': 'struck', 'gamma': 'struck', 'delta': 'unresolved: unbound'})  # delta's mark reached other text
        for broken in ({**good, 'decorations': ''}, {k: x for k, x in good.items() if k != 'decor'}, {**good, 'decor': []}):  # unsupported property, missing or malformed answer
            self.assertTrue(all(w == 'unresolved: no decoration' for *_, w in sg.decorations(raw, vis, runs, broken)))
        bad = {**good, 'decor': {ids['alpha']: ['', 'alpha ']}}; got = {raw[s:e].decode().strip(): w for s, e, w in sg.decorations(raw, vis, runs, bad)}
        self.assertEqual((got['alpha'], got['beta']), ('unresolved: no decoration', 'unresolved: no mark'))  # an empty effect proves nothing; an absent run is no unstruck run
        unbound = {**good, 'decor': {}, 'marks': {ids['beta']: None}}; self.assertIn([raw.index(b'beta'), raw.index(b'beta') + 4, 'unresolved: unbound'], sg.decorations(raw, vis, runs, unbound))

    def test_paint_uncertainty_turns_a_struck_run_unresolved(self):
        raw = b'<style>.x{text-decoration:line-through}.c{color:transparent}</style><p><span class="x">gone</span></p>'; vis = anchor.Visible(raw); runs, _ = sg.symbol_runs(raw, vis)
        self.assertTrue(vis.paint_uncertain)
        k = next(str(k) for k, (_, c, h, ok) in enumerate(runs) if raw[c[0][0]:c[-1][1]] == b'gone')
        self.assertEqual(sg.decorations(raw, vis, runs, {'decor': {k: ['line-through', 'gone']}, 'decorations': 'none', 'marks': {}, 'plain': ''})[0][2], 'unresolved: paint')


if __name__ == '__main__':
    unittest.main()
