"""The screen step's endpoint boxes in an uncertain file (Codex's held-out review): Chrome shows two units apart — another line, a visible gap — and
only that is taken as proof; touching, hidden or impossible boxes prove nothing. And the page never reaches the network."""
import unittest

from benchmarks.prepare.grader import grade
from driver.prepare.convert import anchor
from benchmarks.prepare.grader.adapters import screen_grid


class Offline(unittest.TestCase):
    def test_measure_aborts_every_request_before_the_page_is_set(self):
        calls = []
        class Page:
            def route(self, pattern, handler): calls.append(('route', pattern))
            def set_content(self, html, wait_until=None): calls.append(('set_content',))
            def evaluate(self, js): calls.append(('evaluate',)); return {'cells': [], 'boxes': {}}
            def close(self): calls.append(('close',))
        class Browser:
            def new_page(self, **kw): return Page()
        screen_grid.measure(b'<p>x</p>', Browser())
        self.assertEqual(calls[:2], [('route', '**/*'), ('set_content',)])


class EndpointBoxes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try: from playwright.sync_api import sync_playwright
        except ImportError: raise unittest.SkipTest('playwright not installed')
        cls.pw = sync_playwright().start(); cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.pw.stop()

    def check(self, html, texts, expected):
        raw = html.encode(); vis = anchor.Visible(raw); self.assertFalse(vis.certain)
        units = anchor.link(raw, [{'id': str(i), 'kind': 'text', 'text': t} for i, t in enumerate(texts)], vis=vis)['units']
        ends = screen_grid.endpoints_of(vis, units); marked, _ = screen_grid.tag_cells(raw, vis, ends); _, boxes = screen_grid.measure(marked, self.browser)
        proof = {side: {str(g[0][side]): boxes[f'{n}.{ix}'] for n, g in enumerate(ends) if f'{n}.{ix}' in boxes} for ix, side in enumerate(('start', 'end'))}
        g = grade.Grader({'fields': {}, 'support': {}, 'alternatives': {}}, grade.RouteFile({'file_id': 'fixture.htm', 'units': units, 'screen_endpoints': proof}, raw))
        result = g.adjacent(units[0]['anchor'], units[-1]['anchor'])
        if expected is None: self.assertTrue(g.unsure)
        else: self.assertIs(result, expected); self.assertFalse(g.unsure)

    def test_apart_on_screen(self):
        for html, texts in (('<style>p {display:block}</style><p>Alpha<br>Beta</p>', ['Alpha', 'Beta']), ('<style>span {display:inline}</style><p><span>Alpha</span><span style="margin-left:20px">Beta</span></p>', ['Alpha', 'Beta']),
                            ('<style>p {display:block}</style><p>Alpha</p><p>Other</p><p>Beta</p>', ['Alpha', 'Other', 'Beta']), ('<style>p {display:block;width:40px}</style><p>Alpha Beta</p>', ['Alpha', 'Beta'])):
            with self.subTest(html=html): self.check(html, texts, False)  # a break, a styled gap, separate blocks, a wrapped line

    def test_nothing_else_is_proof(self):
        for html, texts in (('<style>span {display:inline}</style><p><span>Al</span><span>pha</span></p>', ['Al', 'pha']), ('<style>br {display:none}</style><p>Al<br>pha</p>', ['Al', 'pha']),
                            ('<style>p {display:block}</style><p><span>Alpha</span><span style="position:absolute;left:800px">OTHER</span><span>Beta</span></p>', ['Alpha', 'OTHER', 'Beta']),
                            ('<style>.hidden {display:none}</style><p><span class="hidden">Alpha</span><span>Beta</span></p>', ['Alpha', 'Beta']),
                            ('<style>.hidden {visibility:hidden}</style><p><span class="hidden">Alpha</span><br><span>Beta</span></p>', ['Alpha', 'Beta']),
                            ('<style>.hidden {opacity:0}</style><p><span class="hidden"><b>Alpha</b></span><br><span>Beta</span></p>', ['Alpha', 'Beta']),
                            ('<style>p {display:block}</style><p>x&fjlig;<span>Beta</span></p>', ['xfj', 'Beta'])):
            with self.subTest(html=html): self.check(html, texts, None)  # touching, a hidden break, text standing between, hidden or transparent endpoints, an endpoint a reference makes

    def test_impossible_boxes_prove_nothing(self):
        raw = b'<style>p {display:block}</style><p>Al<br>pha</p>'
        units = anchor.link(raw, [{'id': 'a', 'kind': 'text', 'text': 'Al'}, {'id': 'b', 'kind': 'text', 'text': 'pha'}])['units']
        end, start = units[0]['anchor']['byte_end_exclusive'], units[1]['anchor']['byte_start']
        data = {'file_id': 'fixture.htm', 'units': units, 'screen_endpoints': {'end': {str(end): {'shown': True, 'x': 1, 'r': 0, 't': 1, 'b': 3}}, 'start': {str(start): {'shown': True, 'x': 0, 'r': 1, 't': 1, 'b': 3}}}}
        g = grade.Grader({'fields': {}, 'support': {}, 'alternatives': {}}, grade.RouteFile(data, raw)); g.adjacent(units[0]['anchor'], units[1]['anchor']); self.assertTrue(g.unsure)


if __name__ == '__main__':
    unittest.main()
