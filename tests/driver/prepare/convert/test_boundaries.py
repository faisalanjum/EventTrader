"""The production boundaries of the one-document calls (Codex CODEX_CLEANUP_R1_VERDICT C1-C3; his probes, ported unchanged): the caller's bytes must be
the source the hash names - checked before any parse, browser work or change to a route; storage, dependency and resource failures stop the caller,
a document the tool cannot read is a FAILED route and a page that cannot be measured is reported, the route unchanged; results never share
metadata. No model or external request."""
import copy
import errno
import hashlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from driver.prepare.convert import edgartools_html as eh, screen_grid as sg, source_formatting as sf, xml_fields as xf
from driver.prepare.get.acquire import StorageError

sha = lambda raw: hashlib.sha256(raw).hexdigest()
RAW = b'<p><i>10</i> 20</p>'
OTHER = b'<p><s>10</s> 20</p>'
TREE = {'type': 'DocumentNode', 'children': [{'type': 'ParagraphNode', 'text': '10 20'}]}

def parsed(raw, vis):
    return copy.deepcopy(TREE), 0.1, 'edgartools tested'

def route():
    return eh.convert(RAW, 'test.htm', sha(RAW), parsed)

class SourceIdentity(unittest.TestCase):
    def test_html_rejects_false_source_identity_before_calling_parser(self):
        for bad in (sha(OTHER), '', None):
            with self.subTest(hash=bad), patch.object(eh, 'parse', wraps=parsed) as parse:
                with self.assertRaises(ValueError): eh.convert(RAW, 'test.htm', bad, parse)
                parse.assert_not_called()

    def test_xml_rejects_false_source_identity_before_parsing(self):
        raw = b'<r>10</r>'
        for bad in (sha(b'<r>20</r>'), '', None):
            with self.subTest(hash=bad), patch.object(xf, 'units_of', wraps=xf.units_of) as parse:
                with self.assertRaises(ValueError): xf.convert(raw, 'test.xml', bad)
                parse.assert_not_called()

    def test_matching_source_identity_preserves_normal_results(self):
        self.assertEqual((route()['status'], route()['sha256']), ('OK', sha(RAW)))
        raw = b'<r>10</r>'
        doc = xf.convert(raw, 'test.xml', sha(raw))
        self.assertEqual((doc['status'], doc['sha256'], doc['units'][0]['text']), ('OK', sha(raw), '10'))

    def test_formatting_rejects_wrong_bytes_without_mutation(self):
        doc = route(); before = copy.deepcopy(doc)
        with self.assertRaises(ValueError): sf.step(OTHER, doc)
        self.assertEqual(doc, before)

    def test_screen_rejects_wrong_bytes_without_browser_or_mutation(self):
        doc = route(); before = copy.deepcopy(doc)
        with patch.object(sg, 'measure', return_value=({}, {})) as measure:
            with self.assertRaises(ValueError): sg.step(OTHER, doc, object())
            measure.assert_not_called()
        self.assertEqual(doc, before)

    def test_matching_source_bytes_allow_both_stages(self):
        doc = route()
        self.assertEqual(sf.step(RAW, doc), 0)
        with patch.object(sg, 'measure', return_value=({}, {})):
            facts = sg.step(RAW, doc, object())
        self.assertNotIn('error', facts)
        self.assertEqual(doc['route']['name'], 'edgartools-html+source-formatting+screen')

class Failures(unittest.TestCase):
    def test_storage_and_environment_errors_stop_html_instead_of_becoming_bad_documents(self):
        errors = [OSError(errno.EIO, 'disk'), PermissionError('denied'), FileNotFoundError('cache vanished'),
                  StorageError('invalid cache'), ImportError('missing engine'), MemoryError('out of memory')]
        for error in errors:
            def bad_parse(raw, vis): raise error
            with self.subTest(type=type(error).__name__):
                with self.assertRaises(type(error)): eh.convert(RAW, 'test.htm', sha(RAW), bad_parse)

    def test_storage_and_environment_errors_stop_screen_instead_of_becoming_page_flags(self):
        for error in [OSError(errno.EIO, 'disk'), StorageError('bad state'), ImportError('missing browser'), MemoryError('out of memory')]:
            doc = route(); before = copy.deepcopy(doc)
            with self.subTest(type=type(error).__name__), patch.object(sg, 'measure', side_effect=error):
                with self.assertRaises(type(error)): sg.step(RAW, doc, object())
            self.assertEqual(doc, before)

    def test_document_parser_error_is_still_a_failed_result(self):
        def bad_parse(raw, vis): raise ValueError('cannot parse this content')
        doc = eh.convert(RAW, 'test.htm', sha(RAW), bad_parse)
        self.assertEqual((doc['status'], doc['units']), ('FAILED', []))
        self.assertIn('cannot parse this content', doc['error'])
        broken = b'<r>'
        self.assertEqual(xf.convert(broken, 'test.xml', sha(broken))['status'], 'FAILED')

    def test_page_failure_is_reported_without_mutating_the_reading(self):
        doc = route(); before = copy.deepcopy(doc)
        with patch.object(sg, 'measure', side_effect=RuntimeError('one page cannot be measured')):
            facts = sg.step(RAW, doc, SimpleNamespace(is_connected=lambda: True))
        self.assertIn('one page cannot be measured', facts['error'])
        self.assertEqual(doc, before)

class ResultOwnership(unittest.TestCase):
    def test_xml_results_do_not_share_route_metadata_with_other_documents(self):
        original = copy.deepcopy(xf.ROUTE)
        try:
            a = b'<r>10</r>'; b = b'<r>20</r>'
            first, second = xf.convert(a, 'a.xml', sha(a)), xf.convert(b, 'b.xml', sha(b))
            first['route']['name'] = 'consumer annotation'
            first['route']['settings']['recover'] = True
            first['route']['settings']['custom'] = 'one occurrence'
            self.assertEqual(second['route'], original)
            self.assertEqual(xf.convert(b, 'c.xml', sha(b))['route'], original)
            self.assertEqual(xf.ROUTE, original)
        finally:
            xf.ROUTE.clear(); xf.ROUTE.update(original)

    def test_html_metadata_is_already_independent_between_calls(self):
        first, second = route(), route()
        before = copy.deepcopy(second)
        first['route']['name'] = 'consumer annotation'
        first['route']['settings']['custom'] = 'one occurrence'
        self.assertEqual(second, before)


if __name__ == '__main__': unittest.main()
