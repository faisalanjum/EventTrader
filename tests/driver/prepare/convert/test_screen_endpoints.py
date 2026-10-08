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
            def set_content(self, html, wait_until=None): calls.append(('set_content',))
            def evaluate(self, js): calls.append(('evaluate',)); return {'cells': [], 'boxes': {}}
            def close(self): calls.append(('close',))
        class Browser:
            def new_page(self, **kw): return Page()
        screen_grid.measure(b'<p>x</p>', Browser())
        self.assertEqual(calls[:2], [('route', '**/*'), ('set_content',)])

    def test_a_page_that_cannot_be_measured_keeps_the_route_content_and_says_why(self):
        class Browser:
            def new_page(self, **kw): raise RuntimeError('no page')
            def is_connected(self): return True
        route = {'sha256': screen_grid.anchor.sha256(b'<p>x</p>'), 'route': {'name': 'r'}, 'units': [{'id': 'u', 'kind': 'text', 'text': 'x'}]}; before = copy.deepcopy(route)
        facts = screen_grid.step(b'<p>x</p>', route, Browser())
        self.assertEqual(route, dict(before, source_symbols={'read': False, 'error': "RuntimeError('no page')"})); self.assertIn('no page', facts['error'])  # content kept; the failure added

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


if __name__ == '__main__':
    unittest.main()
