import gzip
from pathlib import Path
import re
import unittest

from driver.prepare.inventory import parse_index, compare_inventory


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.url = 'https://www.sec.gov/Archives/edgar/data/1004434/000100443423000015/0001004434-23-000015-index.html'
        self.source = gzip.decompress((Path(__file__).parent / 'fixtures/amg_index.html.gz').read_bytes())

    def test_real_sec_index_and_optional_closing_tags(self):
        for source in (self.source, self.source.replace(b'</td>', b'').replace(b'</tr>', b'')):
            rows = parse_index(source, self.url)
            self.assertEqual(len(rows), 10)
            self.assertEqual(rows[0]['filename'], 'amg-20230501.htm')
            self.assertEqual(rows[0]['url'], self.url.rsplit('/', 1)[0] + '/amg-20230501.htm')
            self.assertEqual({r['filename'] for r in rows if r['type'] == 'EX-99.1'},
                             {'amgq12023ex991.htm', 'courtesy.pdf'})
            self.assertEqual(next(r['bytes'] for r in rows if r['filename'] == 'courtesy.pdf'), 209919)

    def test_missing_whole_member_and_metadata_change_are_detected(self):
        rows = parse_index(self.source, self.url)
        members = [dict(filename=r['filename'], type=r['type'], sequence=r['sequence']) for r in rows]
        self.assertFalse(compare_inventory({'members': members}, rows)['missing'])
        result = compare_inventory({'members': members[1:]}, rows)
        self.assertEqual(result['missing'], ['amg-20230501.htm'])
        members[0]['type'] = 'GRAPHIC'
        self.assertEqual(compare_inventory({'members': members}, rows)['metadata_mismatch'], ['amg-20230501.htm'])

    def test_wrong_or_empty_index_and_outside_file_fail(self):
        for source in (b'<html>Access denied</html>', self.source.replace(b'0001004434-23-000015', b'0001004434-23-000099'),
                       self.source.replace(b'/Archives/edgar/data/1004434/000100443423000015/courtesy.pdf', b'https://example.com/file.pdf')):
            with self.assertRaises(ValueError):
                parse_index(source, self.url)

    def test_joint_company_paths_keep_the_accession_and_sec_origin(self):
        url = ('https://www.sec.gov/Archives/edgar/data/65984/000006598425000132/'
               '0000065984-25-000132-index.html')
        source = gzip.decompress((Path(__file__).parent / 'fixtures/entergy_index.html.gz').read_bytes())
        rows = parse_index(source, url)
        self.assertEqual(len(rows), 33)
        self.assertEqual(rows[0]['filename'], 'etr-20250930.htm')
        self.assertEqual(rows[0]['bytes'], 6670096)
        self.assertIn('/data/7323/000006598425000132/', rows[0]['url'])
        # The company directory may vary, but never the origin or filing.
        for cik in ('1', '0000000001', '9876543210'):
            changed = source.replace(b'/data/7323/', f'/data/{cik}/'.encode())
            self.assertEqual([r['filename'] for r in parse_index(changed, url)],
                             [r['filename'] for r in rows])
        path = b'/Archives/edgar/data/1004434/000100443423000015/courtesy.pdf'
        for outside in (b'https://elsewhere.example' + path,
                        b'http://www.sec.gov' + path,
                        path.replace(b'000100443423000015', b'000100443423000016'),
                        path.replace(b'/1004434/', b'/not-a-company/'),
                        path.replace(b'courtesy.pdf', b'%2e%2e/courtesy.pdf'),
                        path + b'?different=1', path + b'#fragment'):
            with self.subTest(outside=outside), self.assertRaises(ValueError):
                parse_index(self.source.replace(path, outside), self.url)

    def test_required_rows_cannot_be_silently_skipped(self):
        row = next(match for match in re.finditer(br'<tr[^>]*>.*?</tr>', self.source, re.S)
                   if b'amg-20230501.htm' in match[0])
        changed_rows = [row[0].replace(b'href=', b'data-href='),
                        row[0].replace(b'</tr>', b'<td>extra</td></tr>')]
        for changed in changed_rows:
            source = self.source[:row.start()] + changed + self.source[row.end():]
            with self.subTest(changed=changed[:100]), self.assertRaises(ValueError):
                parse_index(source, self.url)
        # A remaining Data Files table cannot stand in for missing company rows.
        table = re.search(br'<table\b[^>]*summary="Document Format Files"[^>]*>.*?</table>',
                          self.source, re.S)
        self.assertIsNotNone(table)
        with self.assertRaises(ValueError):
            parse_index(self.source[:table.start()] + self.source[table.end():], self.url)

    def test_unrelated_tables_are_not_filing_inventory(self):
        navigation = (b'<table><tr><td>99</td><td>navigation</td>'
                      b'<td><a href="navigation.htm">navigation</a></td>'
                      b'<td>XML</td><td>1</td></tr></table>')
        expected = parse_index(self.source, self.url)
        self.assertEqual(parse_index(self.source + navigation, self.url), expected)
        self.assertEqual(parse_index(self.source + b'<!--' + navigation + b'-->', self.url), expected)
        self.assertEqual(parse_index(self.source + b'<script>' + navigation + b'</script>', self.url), expected)

    def test_declared_identity_cannot_be_replaced_by_incidental_links(self):
        # The first two occurrences are the real title and visible accession.
        changed = self.source.replace(b'0001004434-23-000015', b'0001004434-23-000099', 2)
        self.assertIn(b'0001004434-23-000015', changed)
        with self.assertRaises(ValueError):
            parse_index(changed, self.url)

    def test_header_cells_cannot_hide_a_file_row(self):
        row = next(match for match in re.finditer(br'<tr[^>]*>.*?</tr>', self.source, re.S)
                   if b'amg-20230501.htm' in match[0])
        changed = row[0].replace(b'<td', b'<th').replace(b'</td>', b'</th>')
        source = self.source[:row.start()] + changed + self.source[row.end():]
        try:
            actual = parse_index(source, self.url)
        except ValueError:
            return  # Explicit rejection is valid; silently omitting the row is not.
        self.assertEqual(actual, parse_index(self.source, self.url))


class Schedule13DIndexTests(unittest.TestCase):
    def setUp(self):
        self.url = ('https://www.sec.gov/Archives/edgar/data/1468174/000119312526167598/'
                    '0001193125-26-167598-index.html')
        self.source = gzip.decompress((Path(__file__).parent / 'fixtures/schedule13d_index.html.gz').read_bytes())
        self.view = next(match for match in re.finditer(br'<tr[^>]*>.*?</tr>', self.source, re.S)
                         if b'xslSCHEDULE_13D_X02/primary_doc.xml' in match[0])
        self.raw = next(match for match in re.finditer(br'<tr[^>]*>.*?</tr>', self.source, re.S)
                        if b'/000119312526167598/primary_doc.xml' in match[0])
        self.physical = [('primary_doc.xml', '1', 'SCHEDULE 13D/A', 31820),
                         ('ck0000000000-ex99_1.pdf', '2', 'EX-99.1', 59606),
                         ('ck0000000000-ex99_2.pdf', '3', 'EX-99.2', 93870),
                         ('ck0000000000-ex99_3.pdf', '4', 'EX-99.3', 136001)]

    def test_real_index_keeps_four_files_and_one_paired_rendering(self):
        swapped = (self.source[:self.view.start()] + self.raw[0]
                   + self.source[self.view.end():self.raw.start()] + self.view[0]
                   + self.source[self.raw.end():])
        expected = self.physical + [('xslSCHEDULE_13D_X02/primary_doc.xml', '1', 'SCHEDULE 13D/A', None)]
        for source in (self.source, swapped):
            with self.subTest(view_first=source == self.source):
                rows = parse_index(source, self.url)
                self.assertEqual(sorted((r['filename'], r['sequence'], r['type'], r['bytes']) for r in rows),
                                 sorted(expected))
                view = next(r for r in rows if r['filename'].startswith('xslSCHEDULE_13D_X02/'))
                self.assertEqual(view['url'], self.url.rsplit('/', 1)[0] + '/' + view['filename'])
                self.assertEqual(view['rendered_from'], 'primary_doc.xml')
                self.assertTrue(all(r.get('rendered_from') is None for r in rows if r is not view))
                members = [dict(filename=name, sequence=seq, type=kind) for name, seq, kind, _ in self.physical]
                result = compare_inventory({'members': members}, rows)
                self.assertEqual(result['missing'], [])
                self.assertEqual(result['metadata_mismatch'], [])
                self.assertEqual(result['package_only'], [])
                self.assertEqual(compare_inventory({'members': members[1:]}, rows)['missing'], ['primary_doc.xml'])

    def test_blank_size_requires_one_exact_physical_mate(self):
        damaged = {
            'missing raw row': self.source[:self.raw.start()] + self.source[self.raw.end():],
            'different type': self.source[:self.view.start()] + self.view[0].replace(b'SCHEDULE 13D/A', b'8-K')
                              + self.source[self.view.end():],
            'different sequence': self.source[:self.view.start()] + self.view[0].replace(b'>1</td>', b'>9</td>', 1)
                                  + self.source[self.view.end():],
            'different basename': self.source[:self.view.start()] + self.view[0].replace(b'primary_doc.xml', b'other_doc.xml')
                                  + self.source[self.view.end():],
            'raw size missing': self.source.replace(b'>31820</td>', b'>&nbsp;</td>'),
            'unrelated file size missing': self.source.replace(b'>59606</td>', b'>&nbsp;</td>'),
            'duplicate raw mate': self.source[:self.raw.end()] + self.raw[0] + self.source[self.raw.end():],
            'raw mate is not at filing root': self.source.replace(
                b'/000119312526167598/primary_doc.xml', b'/000119312526167598/raw/primary_doc.xml').replace(
                b'xslSCHEDULE_13D_X02/primary_doc.xml', b'xslSCHEDULE_13D_X02/raw/primary_doc.xml'),
        }
        for reason, source in damaged.items():
            with self.subTest(reason=reason), self.assertRaises(ValueError):
                parse_index(source, self.url)
