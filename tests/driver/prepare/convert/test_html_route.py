"""The selected HTML route for one document (`driver.prepare.convert.html_route.prepare`; Codex CODEX_CLEANUP_R1_VERDICT, the composition): the stages in
order, nothing after a failed conversion, a page that cannot be measured visible on the route with its content kept, operational errors propagated.
The tool call and the browser's measurement are stand-ins; everything else is the production path. No model or external request."""
import contextlib
import copy
import hashlib
import re
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from driver.prepare.convert import anchor, edgartools_html as eh, html_route, screen_grid as sg, source_formatting as sf

RAW = b'<p><s>10</s> 20</p>'; SHA = hashlib.sha256(RAW).hexdigest()


def shown(raw):  # a stand-in render's every-run reading (SYMBOLS_JS with `every`, the screen step's agreement proof): the page shows each marked source run exactly as the scan reads it
    runs, _ = sg.symbol_runs(raw, anchor.Visible(raw)); return {'marks': {str(k): {'text': ''.join(g or '' for _, g in sg._glyphs(raw, chars)[0]), 'visibility': 'shown'} for k, (_, chars, _, ok) in enumerate(runs) if ok}, 'faces': [],
                                                             'generated': {'read': True, 'records': []}}  # and its native generated-content reading: none on these pages
TREE = {'type': 'DocumentNode', 'children': [{'type': 'ParagraphNode', 'text': '10 20'}]}
_convert = eh.convert
convert = lambda parse: (lambda raw, file_id, sha256, vis=None: _convert(raw, file_id, sha256, parse, vis))  # the production conversion with the tool call replaced
parsed = convert(lambda raw, vis: (copy.deepcopy(TREE), 0.1, 'edgartools tested'))


class Prepare(unittest.TestCase):
    def test_the_stages_run_in_order_and_the_route_names_them(self):
        calls, browser = [], object()  # the caller's own browser: the screen step must measure in it
        with patch.object(eh, 'convert', side_effect=lambda *a, **k: calls.append('convert') or parsed(*a, **k)), \
             patch.object(sf, '_step', side_effect=lambda *a, step=sf._step: calls.append('formatting') or step(*a)), \
             patch.object(sg, 'measure', side_effect=lambda marked, used, prefix=None, **reading: calls.append(('screen', used)) or ({}, {}, shown(RAW))):
            route, facts = html_route.prepare(RAW, 'a.htm', SHA, browser)
        self.assertEqual(calls, ['convert', 'formatting', ('screen', browser)]); self.assertIs(calls[2][1], browser)
        self.assertEqual((route['status'], route['error'], route['route']['name'], route['file_id'], route['sha256']), ('OK', None, 'edgartools-html+source-formatting+screen', 'a.htm', SHA))
        self.assertEqual((facts['formatting'], route['units'][0]['struck']), (1, ['10']))
        self.assertEqual(sorted(facts['screen']), ['boundaries_the_tool_dropped', 'cells_measured', 'cells_regridded', 'joined', 'parted', 'seconds', 'spaces_the_tool_added'])
        raw = b'<style>.x{text-decoration:line-through}</style><p>10 20</p>'  # a sheet rule could add a strike: the formatting step certifies nothing and says so
        claimed = lambda *a, **k: (lambda r: r['units'][0].update(struck=['10']) or r)(parsed(*a, **k))  # a converter's own claim, standing in for a tool that reports strikes
        with patch.object(eh, 'convert', side_effect=claimed), patch.object(sg, 'measure', return_value=({}, {}, shown(raw))):  # a render with no decoration answer
            route, facts = html_route.prepare(raw, 'a.htm', hashlib.sha256(raw).hexdigest(), object())
        self.assertEqual((route['status'], facts['formatting'], route['route']['name']), ('PARTIAL', None, 'edgartools-html+source-formatting+screen'))  # unknown required text is said, never certified
        self.assertEqual(route['error'], 'screen step: source formatting: 1 text run without a native decoration verdict')
        a = raw.index(b'10 20'); self.assertEqual(route['source_formatting'], {'unresolved': [[a, a + 5, 'unresolved: no decoration']]})
        self.assertEqual((route['units'][0]['text'], route['units'][0]['struck'], 'struck_at' in route['units'][0], facts['screen']['source_formatting']), ('10 20', ['10'], False, 0))  # the claim stays, no places
        def bound(marked, used, prefix=None, decorate=False, **reading):  # a browser that reached every mark and draws no decoration (the source has none)
            reached = re.findall(r'<!--%ss:(\d+)-->([^<]*)' % re.escape(prefix), marked.decode() if isinstance(marked, bytes) else marked)
            return {}, {}, {'marks': {k: {'text': t, 'visibility': 'shown'} for k, t in reached}, 'faces': [], 'generated': {'read': True, 'records': []}, **({'decor': {k: ['none', t] for k, t in reached}, 'decorations': 'none'} if decorate else {})}  # every mark reached: its text too (the agreement reading); no generated content
        with patch.object(eh, 'convert', side_effect=claimed), patch.object(sg, 'measure', side_effect=bound):
            route, facts = html_route.prepare(raw, 'a.htm', hashlib.sha256(raw).hexdigest(), object())
        self.assertEqual((route['status'], route['error'], 'source_formatting' in route, facts['screen']['source_formatting']), ('OK', None, False, 0))  # proved unstruck: no error
        self.assertEqual((route['units'][0]['text'], 'struck' in route['units'][0], 'struck_at' in route['units'][0]), ('10 20', False, False))  # the converter's claim goes

    def test_a_failed_conversion_stops_before_the_steps(self):
        def crash(raw, vis): raise ValueError('cannot parse this content')
        with patch.object(eh, 'convert', side_effect=convert(crash)), patch.object(sf, '_step') as formatting, patch.object(sg, '_step') as screen:
            route, facts = html_route.prepare(RAW, 'a.htm', SHA, object())
        self.assertEqual((route['status'], route['units'], facts), ('FAILED', [], {})); self.assertIn('cannot parse this content', route['error'])
        formatting.assert_not_called(); screen.assert_not_called()

    def test_a_page_that_cannot_be_measured_is_a_partial_route_with_its_content(self):
        with patch.object(eh, 'convert', side_effect=parsed), patch.object(sg, 'measure', side_effect=RuntimeError('one page cannot be measured')):
            route, facts = html_route.prepare(RAW, 'a.htm', SHA, SimpleNamespace(is_connected=lambda: True))
        self.assertEqual((route['status'], [u['text'] for u in route['units']], route['units'][0]['struck']), ('PARTIAL', ['10 20'], ['10']))
        self.assertIn('one page cannot be measured', route['error']); self.assertIn('one page cannot be measured', facts['screen']['error'])
        self.assertEqual(route['route']['name'], 'edgartools-html+source-formatting')  # the screen step did not finish, and the record says so

    def test_operational_errors_propagate(self):
        for error in (OSError('disk'), MemoryError('out of memory')):
            with self.subTest(type=type(error).__name__), patch.object(eh, 'convert', side_effect=parsed), patch.object(sg, 'measure', side_effect=error):
                with self.assertRaises(type(error)): html_route.prepare(RAW, 'a.htm', SHA, object())
        with self.assertRaises(ValueError): html_route.prepare(RAW, 'a.htm', hashlib.sha256(b'other').hexdigest(), object())  # bytes the hash does not name


@contextlib.contextmanager
def readings():  # every scanner reading made inside the block, in order (Visible's own constructor, called unchanged)
    made, real = [], anchor.Visible.__init__
    def init(self, raw, xml=False, page=None): real(self, raw, xml, page); made.append(self)
    with patch.object(anchor.Visible, '__init__', init): yield made


def timeless(route, facts):  # a copy without the two elapsed times, route['seconds'] and facts['screen']['seconds']; no other field is dropped, whatever its name
    route, facts = copy.deepcopy(route), copy.deepcopy(facts); route.pop('seconds', None); (facts.get('screen') or {}).pop('seconds', None)
    return route, facts
CERTAIN = b'<p><s>10</s> 20 and ten more words to read here</p><table><tr><td>Total</td><td>5</td></tr></table>'
UNCERTAIN = b'<style>.x{display:none}</style><p>ONE <span style="display:none">HID</span> <s>TWO</s> <span class="x">GONE</span> THREE</p>'


def standalone(raw, fid, browser):  # the composition's stages one by one through their public, self-checking entries: the route before the reuse
    vis, _ = html_route.visibility(raw, anchor.Visible(raw), browser); route = eh.convert(raw, fid, hashlib.sha256(raw).hexdigest(), vis=vis)
    return route, {'formatting': sf.step(raw, route), 'screen': sg.step(raw, route, browser)}


class Readings(unittest.TestCase):
    """One preparation reads its source once as written and, where the scanner cannot certify it, once as the browser shows it: formatting reads the
    first, the screen step the reading the route was made with, and the route is the standalone path's (Root, ROOT_IMPLEMENTATION_ORDER). The real
    tool and offline Chrome (playwright is required: a missing install fails, never skips)."""
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def prepare(self, raw, fid='r.htm'):
        with readings() as made, patch.object(sf, '_step', wraps=sf._step) as formatting, patch.object(sg, '_step', wraps=sg._step) as screen:
            route, facts = html_route.prepare(raw, fid, hashlib.sha256(raw).hexdigest(), self.browser)
        return route, facts, made, formatting, screen

    def test_a_certain_page_is_read_once_and_each_step_reads_that_reading(self):  # failed before: three readings, one per stage
        route, facts, made, formatting, screen = self.prepare(CERTAIN)
        self.assertEqual([v.paged for v in made], [False]); self.assertIs(formatting.call_args.args[0], made[0]); self.assertIs(screen.call_args.args[3], made[0])
        self.assertEqual(timeless(route, facts), timeless(*standalone(CERTAIN, 'r.htm', self.browser)))

    def test_an_uncertain_page_is_read_as_written_for_formatting_and_as_the_browser_shows_it_for_the_screen(self):  # failed before: four readings
        route, facts, made, formatting, screen = self.prepare(UNCERTAIN)
        self.assertEqual([v.paged for v in made], [False, True]); self.assertIs(formatting.call_args.args[0], made[0]); self.assertIs(screen.call_args.args[3], made[1])
        self.assertIs(made[1].page, route['page_visibility'])
        mine, alone = timeless(route, facts), timeless(*standalone(UNCERTAIN, 'r.htm', self.browser)); mine[1].pop('visibility')
        self.assertEqual(mine, alone)

    def test_a_failed_verdict_keeps_the_original_reading_and_the_route_is_partial(self):
        with patch.object(sg, 'page_visibility', side_effect=RuntimeError('no visibility')): route, facts, made, formatting, screen = self.prepare(UNCERTAIN)
        self.assertEqual((route['status'], [v.paged for v in made]), ('PARTIAL', [False])); self.assertNotIn('page_visibility', route)
        self.assertIs(formatting.call_args.args[0], made[0]); self.assertIs(screen.call_args.args[3], made[0])

    def test_two_documents_with_one_file_id_keep_their_own_readings(self):  # nothing crosses calls: each route is its own bytes'
        first, second = self.prepare(UNCERTAIN, 'same.htm'), self.prepare(CERTAIN, 'same.htm')
        for (route, facts, made, *_), raw in ((first, UNCERTAIN), (second, CERTAIN)):
            with self.subTest(raw=raw[:20]):
                alone = timeless(*standalone(raw, 'same.htm', self.browser)); mine = timeless(route, facts); mine[1].pop('visibility', None)
                self.assertEqual(mine, alone); self.assertTrue(all(v.raw_len == len(raw) for v in made))

    def test_a_route_that_names_other_bytes_is_refused_before_either_step(self):
        other = lambda raw, fid, sha, vis=None: _convert(CERTAIN + b' ', fid, hashlib.sha256(CERTAIN + b' ').hexdigest())  # a conversion of other bytes
        with patch.object(eh, 'convert', side_effect=other), patch.object(sf, '_step') as formatting, patch.object(sg, '_step') as screen, self.assertRaises(ValueError):
            html_route.prepare(CERTAIN, 'r.htm', hashlib.sha256(CERTAIN).hexdigest(), self.browser)
        formatting.assert_not_called(); screen.assert_not_called()

    def test_each_private_stage_refuses_the_other_reading_before_it_changes_anything(self):
        original, qualified = anchor.Visible(UNCERTAIN), anchor.Visible(UNCERTAIN, page={'hidden': [], 'shown': [], 'unproven': 0, 'unbound': []})
        route = eh.convert(UNCERTAIN, 'r.htm', hashlib.sha256(UNCERTAIN).hexdigest(), vis=qualified); before = copy.deepcopy(route)
        with self.assertRaises(ValueError): sf._step(qualified, route)  # formatting reads the source as written, never the browser's reading
        with self.assertRaises(ValueError): sg._step(UNCERTAIN, route, object(), original)  # the screen reads the route's own reading; no browser work first
        self.assertEqual(route, before)



class Kept(unittest.TestCase):
    """A caller may take the tool's own reading (`parse`'s plain dump) on its way into the route (Root, FABLE_HTML_RAW_RETENTION_IMPLEMENTATION): the
    real tool and offline Chrome, the caller's `parse` the production one with a recorder around it; without it nothing changes."""
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()

    def keeper(self):
        kept = []
        def keep(raw, vis):
            got = eh.parse(raw, vis); kept.append((raw, vis, copy.deepcopy(got))); return got
        return kept, keep

    def test_the_caller_gets_the_tools_own_reading_and_the_route_is_the_default_one(self):  # failed before: prepare took no parse
        for raw in (CERTAIN, UNCERTAIN):
            with self.subTest(raw=raw[:20]):
                kept, keep = self.keeper(); sha = hashlib.sha256(raw).hexdigest()
                route, facts = html_route.prepare(raw, 'r.htm', sha, self.browser, parse=keep)
                self.assertEqual(len(kept), 1); got, vis, (tree, seconds, made_by) = kept[0]
                self.assertIs(got, raw); self.assertEqual((made_by, route['route']['version'], route['route']['settings']['parse_html']), (eh.version(), eh.version(), 'defaults'))
                self.assertEqual(tree, eh.parse(raw, vis)[0])  # the reading of these bytes as the route read them
                if vis.paged: self.assertIs(vis.page, route['page_visibility'])
                self.assertEqual(timeless(route, facts), timeless(*html_route.prepare(raw, 'r.htm', sha, self.browser)))  # every field but the two elapsed times

    def test_the_reading_is_handed_over_before_a_later_stage_fails(self):
        kept, keep = self.keeper()
        with patch.object(eh, 'route_for', side_effect=ValueError('adaptation stops')), self.assertRaises(ValueError):
            html_route.prepare(CERTAIN, 'r.htm', hashlib.sha256(CERTAIN).hexdigest(), self.browser, parse=keep)
        self.assertEqual(len(kept), 1)

    def test_bytes_the_hash_does_not_name_are_never_read(self):
        kept, keep = self.keeper()
        with self.assertRaises(ValueError): html_route.prepare(CERTAIN, 'r.htm', hashlib.sha256(b'other').hexdigest(), self.browser, parse=keep)
        self.assertEqual(kept, [])

    def test_a_storage_failure_propagates_and_a_content_failure_is_a_failed_route(self):
        for error in (OSError('disk full'), MemoryError('out of memory')):
            def fail(raw, vis, error=error): raise error
            with self.subTest(type=type(error).__name__), self.assertRaises(type(error)):
                html_route.prepare(CERTAIN, 'r.htm', hashlib.sha256(CERTAIN).hexdigest(), self.browser, parse=fail)
        def unreadable(raw, vis): raise ValueError('cannot parse this content')
        route, facts = html_route.prepare(CERTAIN, 'r.htm', hashlib.sha256(CERTAIN).hexdigest(), self.browser, parse=unreadable)
        self.assertEqual((route['status'], route['units'], facts), ('FAILED', [], {})); self.assertIn('cannot parse this content', route['error'])

    def test_two_documents_with_one_file_id_keep_their_own_readings(self):
        kept, keep = self.keeper()
        for raw in (UNCERTAIN, CERTAIN): html_route.prepare(raw, 'same.htm', hashlib.sha256(raw).hexdigest(), self.browser, parse=keep)
        self.assertEqual([k[0] for k in kept], [UNCERTAIN, CERTAIN]); self.assertEqual([v.raw_len for _, v, _ in kept], [len(UNCERTAIN), len(CERTAIN)])


class Compared(unittest.TestCase):
    def test_only_the_two_elapsed_times_are_set_aside(self):  # Root's comparison probe (ROOT_COMPARE_PROBE): a source value named "seconds" is content
        route, facts = {'seconds': 1.0, 'units': [{'id': 'u0', 'attributes': {'seconds': '5'}}]}, {'screen': {'seconds': 0.4, 'joined': 0}, 'formatting': None}
        later = copy.deepcopy((route, facts)); later[0]['seconds'] = 9.9; later[1]['screen']['seconds'] = 3.1
        changed = copy.deepcopy((route, facts)); changed[0]['units'][0]['attributes']['seconds'] = '9'
        self.assertEqual(timeless(*later), timeless(route, facts)); self.assertNotEqual(timeless(*changed), timeless(route, facts))


class StepTime(unittest.TestCase):
    """The screen step's own time (Root, ROOT_TIMING_REVIEW): called alone it counts the reading it makes; given the reading the preparation already
    made, only its own work. A clock only a reading advances (two seconds each); nothing else takes time; no browser."""
    def timed(self, given):
        raw = b'<p>Value 10</p>'; route = {'sha256': hashlib.sha256(raw).hexdigest(), 'units': [], 'route': {'name': 'probe'}}; clock, real = [0.0], anchor.Visible.__init__
        def init(self, *a, **k): real(self, *a, **k); clock[0] += 2.0
        with patch.object(sg.time, 'time', side_effect=lambda: clock[0]), patch.object(anchor.Visible, '__init__', init), patch.object(sg, 'measure', return_value=({}, {}, {'marks': {}, 'faces': []})):
            vis = anchor.Visible(raw) if given else None; start = clock[0]
            facts = sg._step(raw, route, object(), vis) if given else sg.step(raw, route, object())
        return facts['seconds'], clock[0] - start

    def test_the_public_screen_step_counts_the_reading_it_makes(self):  # failed on the first draft: 0 reported for a 2-second scan
        self.assertEqual(self.timed(given=False), (2.0, 2.0))

    def test_a_reading_made_before_the_step_is_not_counted_as_its_time(self):
        self.assertEqual(self.timed(given=True), (0, 0.0))


if __name__ == '__main__': unittest.main()
