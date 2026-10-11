"""Synthetic XML-family grading controls; no converter execution."""
import copy
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True
from benchmarks.prepare.grader import grade

RAW = b'<root xmlns="urn:example"><entity><amount>10</amount></entity></root>'
START = RAW.index(b'>10<') + 1
ANCHOR = {'byte_start': START, 'byte_end_exclusive': START + 2}


def check(extension, mutate=None, raw=RAW):
    name = 'synthetic/source.' + extension
    target = dict(key_id='control/amount', file_id=name, type='cell',
                  format='cell/' + grade.source_format(name), split='development',
                  anchor=ANCHOR, table_anchor=ANCHOR, support={}, excluded=set(), alternatives={},
                  fields={'printed_value': '10', 'row_label': 'amount',
                          'header_path': ['{urn:example}root', '{urn:example}entity']})
    output = dict(file_id=name, units=[dict(id='amount', kind='field', text='10',
                  name='{urn:example}amount', path=['{urn:example}root', '{urn:example}entity'],
                  anchor=copy.deepcopy(ANCHOR), group={'at': 0, 'index': 1, 'count': 1})])
    if mutate:
        mutate(output)
    reader = grade.RouteFile(output, raw)
    scorer = grade.Grader(target, reader)
    scorer.grade_cell()
    return reader, scorer.rows


class XMLFamily(unittest.TestCase):
    def test_supported_suffixes_share_existing_xml_rules(self):
        for ext in ('xml', 'XML', 'xsd', 'XSD'):
            with self.subTest(ext=ext):
                reader, rows = check(ext)
                self.assertTrue(reader.vis.certain)
                self.assertEqual({r['check']: r['verdict'] for r in rows},
                                 {'value': 'pass', 'row_label': 'pass', 'header_path': 'pass'})

    def test_wrong_value_fails_every_supported_suffix(self):
        for ext in ('xml', 'XML', 'xsd', 'XSD'):
            with self.subTest(ext=ext):
                _, rows = check(ext, lambda d: d['units'][0].update(text='11'))
                self.assertEqual(next(r['verdict'] for r in rows if r['check'] == 'value'), 'fail')

    def test_namespace_and_parent_swaps_fail(self):
        for ext in ('xml', 'xsd'):
            for change, wanted in (({'name': '{urn:wrong}amount'}, 'row_label'),
                                   ({'path': ['{urn:example}root', '{urn:example}other']}, 'header_path')):
                with self.subTest(ext=ext, change=change):
                    _, rows = check(ext, lambda d: d['units'][0].update(change))
                    self.assertEqual(next(r['verdict'] for r in rows if r['check'] == wanted), 'fail')

    def test_missing_field_is_not_rebuilt_from_source(self):
        reader, rows = check('xsd', lambda d: d.update(units=[]))
        self.assertTrue(reader.vis.certain)
        self.assertEqual(rows, [])
        self.assertEqual(reader.units, [])

    def test_unknown_suffix_is_not_xml(self):
        for ext in ('json', 'svg', 'unknown', 'xsd.bak'):
            with self.subTest(ext=ext):
                self.assertNotEqual(grade.source_format('synthetic/source.' + ext), 'xml')
                reader = grade.RouteFile({'file_id': 'synthetic/source.' + ext, 'units': []}, RAW)
                self.assertIsNone(reader.vis)

    def test_invalid_xml_cannot_pass(self):
        _, rows = check('xsd', raw=RAW[:-7])
        self.assertTrue(rows)
        self.assertFalse(any(r['verdict'] == 'pass' for r in rows))


if __name__ == '__main__':
    unittest.main()
