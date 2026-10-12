"""The screen step's endpoint boxes in an uncertain file (Codex's held-out review): Chrome shows two units apart — another line, a visible gap — and
only that is taken as proof; touching, hidden or impossible boxes prove nothing. And the page never reaches the network."""
import copy
import unittest

from driver.prepare.convert import screen_grid


class Offline(unittest.TestCase):
    def test_measure_aborts_every_request_before_the_page_is_set(self):
        calls = []
        class Page:
            def route(self, pattern, handler): calls.append(('route', pattern))
            def goto(self, url, wait_until=None): calls.append(('goto',))  # the native loader the measure now uses (Source/_document)
            def evaluate(self, js): calls.append(('evaluate',)); return 'UTF-8' if js == 'document.characterSet' else {'cells': [], 'boxes': {}}
            def close(self): calls.append(('close',))
        class Browser:
            def new_page(self, **kw): return Page()
        screen_grid.measure(b'<p>x</p>', Browser())
        self.assertEqual(calls[:2], [('route', '**/*'), ('goto',)]); self.assertEqual([calls[i - 1] for i, c in enumerate(calls) if c == ('goto',)], [('route', '**/*')] * 2)  # each page (the charset read's, the measure's) refuses every request before it loads

    def test_a_page_that_cannot_be_measured_keeps_the_route_content_and_says_why(self):
        class Browser:
            def new_page(self, **kw): raise RuntimeError('no page')
            def is_connected(self): return True
        route = {'sha256': screen_grid.anchor.sha256(b'<p>x</p>'), 'route': {'name': 'r'}, 'units': [{'id': 'u', 'kind': 'text', 'text': 'x'}]}; before = copy.deepcopy(route)
        facts = screen_grid.step(b'<p>x</p>', route, Browser())
        self.assertEqual(route, dict(before, source_symbols={'read': False, 'error': "RuntimeError('no page')"}, source_inline={'read': False, 'error': "RuntimeError('no page')"},
                                     source_style={'read': False, 'error': "RuntimeError('no page')"})); self.assertIn('no page', facts['error'])  # content kept; the failure added, for the colour reading too

    def test_a_disconnected_browser_stops_instead_of_marking_every_document_partial(self):
        error = RuntimeError('browser connection lost')
        class Browser:
            def new_page(self, **kw): raise error
            def is_connected(self): return False
        raw = b'<p>x</p>'
        route = {'sha256': screen_grid.anchor.sha256(raw), 'route': {'name': 'r'}, 'units': [{'id': 'u', 'kind': 'text', 'text': 'x'}]}
        before = copy.deepcopy(route)
        with self.assertRaises(RuntimeError) as caught:
            screen_grid.step(raw, route, Browser())
        self.assertIs(caught.exception, error)
        self.assertEqual(route, before)


MACHINE = lambda: (OSError(5, 'injected disk fault'), StorageError('injected store fault'), ImportError('injected missing dependency'), MemoryError('injected'))
GEOMETRY = {'cells': [], 'boxes': {'0': [1, 2, 3, 4]}}  # what the page measured before its symbols were read


def offline(symbols, connected=True, closed=None):  # a page that measures GEOMETRY and whose symbol reading (SYMBOLS_JS) raises `symbols`
    class Page:
        def route(self, pattern, handler): pass
        def goto(self, url, wait_until=None): pass  # the native loader the measure now uses (Source/_document)
        def evaluate(self, js, *args):
            if js == 'document.characterSet': return 'UTF-8'
            if js is screen_grid.SYMBOLS_JS: raise symbols
            return copy.deepcopy(GEOMETRY)
        def close(self): closed is not None and closed.append(1)
    class Browser:
        def new_page(self, **kw): return Page()
        def is_connected(self): return connected
    return Browser()


class Faults(unittest.TestCase):  # each catch tells the document's own failure from the machine's: a machine fault is never a failed or a partial document
    RAW = b'<p>x</p>'

    def route(self):
        return {'sha256': screen_grid.anchor.sha256(self.RAW), 'route': {'name': 'r'}, 'units': [{'id': 'u', 'kind': 'text', 'text': 'x'}]}

    def test_a_symbol_reading_that_fails_keeps_the_measured_geometry_and_says_why(self):  # measure's catch round SYMBOLS_JS
        closed = []; tables, boxes, sym = screen_grid.measure(self.RAW, offline(RuntimeError('symbols failed'), closed=closed), prefix='p')
        gen = sym.pop('generated')  # the fake page has no native layout snapshot: said as no reading, never an empty success
        self.assertEqual((tables, boxes, sym, closed, gen['read']), ({}, GEOMETRY['boxes'], {'error': "RuntimeError('symbols failed')"}, [1, 1], False))  # both pages closed: the charset read's and the measure's

    def test_a_machine_fault_while_reading_symbols_stops_the_measure(self):
        for error in MACHINE():
            closed = []
            with self.subTest(error=type(error).__name__), self.assertRaises(type(error)) as caught: screen_grid.measure(self.RAW, offline(error, closed=closed), prefix='p')
            self.assertIs(caught.exception, error); self.assertEqual(closed, [1, 1])  # every page is closed whatever stops it: the charset read's and the measure's

    def test_a_machine_fault_while_measuring_stops_the_step_and_marks_nothing(self):  # _step's catch: the document's own failure is said (Offline above); a machine's stops
        for error in MACHINE():
            class Browser:
                def new_page(self, error=error, **kw): raise error
                def is_connected(self): return True
            route = self.route(); before = copy.deepcopy(route)
            with self.subTest(error=type(error).__name__), self.assertRaises(type(error)) as caught: screen_grid.step(self.RAW, route, Browser())
            self.assertIs(caught.exception, error); self.assertEqual(route, before)

    def test_a_failed_symbol_reading_with_the_browser_gone_stops_instead_of_a_partial_document(self):
        route = self.route(); before = copy.deepcopy(route)
        with self.assertRaisesRegex(RuntimeError, "^browser disconnected: RuntimeError\\('target closed'\\)$"): screen_grid.step(self.RAW, route, offline(RuntimeError('target closed'), connected=False))
        self.assertEqual(route, before)
        route = self.route(); screen_grid.step(self.RAW, route, offline(RuntimeError('target closed')))  # control: the browser still there - the document's own failure, said
        self.assertEqual((route['source_symbols'], [u['text'] for u in route['units']]), ({'read': False, 'error': "RuntimeError('target closed')"}, ['x']))


from driver.prepare.get.acquire import StorageError  # noqa: E402 - beside the faults that name it

if __name__ == '__main__':
    unittest.main()
