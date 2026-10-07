"""The selected HTML route for one document (`driver.prepare.convert.html_route.prepare`; Codex CODEX_CLEANUP_R1_VERDICT, the composition): the stages in
order, nothing after a failed conversion, a page that cannot be measured visible on the route with its content kept, operational errors propagated.
The tool call and the browser's measurement are stand-ins; everything else is the production path. No model or external request."""
import copy
import hashlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from driver.prepare.convert import edgartools_html as eh, html_route, screen_grid as sg, source_formatting as sf

RAW = b'<p><s>10</s> 20</p>'; SHA = hashlib.sha256(RAW).hexdigest()
TREE = {'type': 'DocumentNode', 'children': [{'type': 'ParagraphNode', 'text': '10 20'}]}
_convert = eh.convert
convert = lambda parse: (lambda raw, file_id, sha256: _convert(raw, file_id, sha256, parse))  # the production conversion with the tool call replaced
parsed = convert(lambda raw, vis: (copy.deepcopy(TREE), 0.1, 'edgartools tested'))


class Prepare(unittest.TestCase):
    def test_the_stages_run_in_order_and_the_route_names_them(self):
        calls, browser = [], object()  # the caller's own browser: the screen step must measure in it
        with patch.object(eh, 'convert', side_effect=lambda *a: calls.append('convert') or parsed(*a)), \
             patch.object(sf, 'step', side_effect=lambda *a, step=sf.step: calls.append('formatting') or step(*a)), \
             patch.object(sg, 'measure', side_effect=lambda marked, used: calls.append(('screen', used)) or ({}, {})):
            route, facts = html_route.prepare(RAW, 'a.htm', SHA, browser)
        self.assertEqual(calls, ['convert', 'formatting', ('screen', browser)]); self.assertIs(calls[2][1], browser)
        self.assertEqual((route['status'], route['error'], route['route']['name'], route['file_id'], route['sha256']), ('OK', None, 'edgartools-html+source-formatting+screen', 'a.htm', SHA))
        self.assertEqual((facts['formatting'], route['units'][0]['struck']), (1, ['10']))
        self.assertEqual(sorted(facts['screen']), ['cells_measured', 'cells_regridded', 'joined', 'seconds', 'spaces_the_tool_added'])
        raw = b'<style>.x{text-decoration:line-through}</style><p>10 20</p>'  # a sheet rule could add a strike: the formatting step certifies nothing and says so
        with patch.object(eh, 'convert', side_effect=parsed), patch.object(sg, 'measure', return_value=({}, {})):
            route, facts = html_route.prepare(raw, 'a.htm', hashlib.sha256(raw).hexdigest(), object())
        self.assertEqual((route['status'], facts['formatting'], route['route']['name']), ('OK', None, 'edgartools-html+source-formatting+screen'))

    def test_a_failed_conversion_stops_before_the_steps(self):
        def crash(raw, vis): raise ValueError('cannot parse this content')
        with patch.object(eh, 'convert', side_effect=convert(crash)), patch.object(sf, 'step') as formatting, patch.object(sg, 'step') as screen:
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


if __name__ == '__main__': unittest.main()
