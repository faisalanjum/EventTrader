"""Offline checks of the Step 2 experiment's claims and failure ledger."""
from contextlib import redirect_stdout
import gzip
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from driver.prepare.acquire import parse_package, StorageError
from driver.prepare.campaign import Campaign
from scripts.driver.prepare import acquisition_check as audit


FIXTURES = Path(__file__).with_name('fixtures')
ACCESSION = '0001004434-23-000015'
BASE = 'https://www.sec.gov/Archives/edgar/data/1004434/000100443423000015/'
INDEX = BASE + ACCESSION + '-index.html'
INDEX_FILES = ('amg-20230501.htm', 'amgq12023ex991.htm', 'amglogoa78a.jpg',
               'image5.jpg', 'courtesy.pdf', 'amg-20230501.xsd',
               'amg-20230501_def.xml', 'amg-20230501_lab.xml',
               'amg-20230501_pre.xml', 'amg-20230501_htm.xml')


def selected(accession):
    expected = json.loads((FIXTURES / (accession + '.expected.json')).read_text())
    request = expected['request']
    return dict(acc=accession, cik=request['cik'], form=request['form'],
                sha256=expected['package']['sha256'])


class AcquisitionCheckTests(unittest.TestCase):
    def setUp(self):
        self.package = gzip.decompress((FIXTURES / (ACCESSION + '.txt.gz')).read_bytes())
        self.manifest, self.files = parse_package(self.package, ACCESSION, '1004434', '8-K')
        self.responses = {INDEX: gzip.decompress((FIXTURES / 'amg_index.html.gz').read_bytes())}
        self.responses.update({BASE + name: self.files[name] for name in INDEX_FILES})
        self.clock = [0.0]
        self.calls = []

    def campaign(self, directory, *, live=False):
        def sender(url, *args):
            self.calls.append(url)
            return 200, {}, self.responses[url]
        def sleep(delay):
            self.clock[0] += delay
        return Campaign(directory, live=live, sender=sender,
                        now=lambda: self.clock[0], sleep=sleep)

    def test_real_xml_declared_html_retains_its_exhibit_link(self):
        name = 'amg-20230501.htm'
        self.assertTrue(self.files[name].startswith(b'<?xml '))
        observed = [r for r in audit.references(self.files, self.manifest, BASE)
                    if r['source'] == name]
        self.assertEqual(len(observed), 1)
        link = observed[0]
        self.assertEqual(link['target'], 'amgq12023ex991.htm')
        self.assertEqual(link['target_url'], BASE + 'amgq12023ex991.htm')
        self.assertEqual(link['target_file'], 'amgq12023ex991.htm')
        self.assertEqual(link['status'], 'inside_package')
        self.assertEqual(link['source_sha256'],
                         '4c13d94bfa9666130403bd80c12fef9d4852788fd243497b10c4631ee53866f4')
        self.assertEqual(link['target_time'], self.manifest['acceptance'])
        text = self.files[name].decode('utf-8')
        start = text.index('<a ')
        self.assertEqual(link['line_column'],
                         [text[:start].count('\n') + 1, start - text.rfind('\n', 0, start) - 1])

    def test_explicit_html_attributes_ignore_comments_and_script_text(self):
        parser = audit.Links()
        parser.feed('''<html><body>
            <!-- <a href="not-a-reference"> -->
            <a title="quoted > character" href="exhibit.htm?a=1&amp;b=2">Exhibit</a>
            <link href="style.css"><img src="image.jpg">
            <script src="app.js">var text = '<a href="also-not-a-reference">';</script>
            <iframe src="frame.htm"></iframe><object data="exhibit.pdf"></object>
            <source src="clip.mp4"><video poster="poster.jpg"></video>
            </body></html>''')
        self.assertEqual([(r['tag'], r['target']) for r in parser.links],
                         [('a', 'exhibit.htm?a=1&b=2'), ('link', 'style.css'),
                          ('img', 'image.jpg'), ('script', 'app.js'), ('iframe', 'frame.htm'),
                          ('object', 'exhibit.pdf'), ('source', 'clip.mp4'), ('video', 'poster.jpg')])

    def test_missing_and_corrupt_packages_are_recorded_and_later_filing_is_audited(self):
        missing, corrupt = '0000950170-25-021181', '0000906107-25-000005'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources, output = root / 'sources', root / 'output'
            sources.mkdir()
            (sources / (ACCESSION + '.txt')).write_bytes(self.package)
            (sources / (corrupt + '.txt')).write_bytes(b'corrupt cached package')
            inputs = root / 'inputs.json'
            inputs.write_text(json.dumps({'filings': [selected(a) for a in (missing, corrupt, ACCESSION)]}))
            with self.campaign(output / 'http', live=True) as campaign:
                for url in self.responses:
                    campaign.fetch(url)
            before = (output / 'http/responses.sqlite3').read_bytes()
            self.calls.clear()
            with patch.object(audit, 'Campaign', side_effect=self.campaign), \
                    patch('http.client.HTTPSConnection.connect', side_effect=AssertionError('network forbidden')), \
                    redirect_stdout(io.StringIO()):
                summary = audit.run(inputs, sources, output)
            outcomes = json.loads((output / 'outcomes.json').read_text())
            self.assertEqual([(r['accession'], r['status']) for r in outcomes],
                             [(missing, 'failed'), (corrupt, 'failed'), (ACCESSION, 'acquired')])
            self.assertTrue(all(r.get('error') for r in outcomes[:2]))
            self.assertEqual(len(outcomes[2]['direct_files']), 10)
            self.assertEqual((summary['requested'], summary['processed']), (3, 3))
            self.assertEqual(summary['sent_http_attempts'], 0)
            self.assertEqual(self.calls, [])
            self.assertEqual((output / 'http/responses.sqlite3').read_bytes(), before)

    def test_this_run_attempts_are_separate_from_cached_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources, output = root / 'sources', root / 'output'
            sources.mkdir()
            (sources / (ACCESSION + '.txt')).write_bytes(self.package)
            inputs = root / 'inputs.json'
            inputs.write_text(json.dumps({'filings': [selected(ACCESSION)]}))
            def factory(directory, *, live=False):
                campaign = self.campaign(directory, live=live)
                successful_sender = campaign.sender
                def retry_once(url, *args):
                    if not self.calls:
                        self.calls.append(url)
                        return 429, {}, b''
                    return successful_sender(url, *args)
                campaign.sender = retry_once
                return campaign
            with patch.object(audit, 'Campaign', side_effect=factory), \
                    patch('http.client.HTTPSConnection.connect', side_effect=AssertionError('network forbidden')), \
                    redirect_stdout(io.StringIO()):
                first = audit.run(inputs, sources, output, live=True)
                self.assertEqual(len(self.calls), 12)  # One index retry plus eleven responses.
                self.assertEqual(first['sent_http_attempts'], 12)
                self.assertEqual(first['recorded_http_attempts'], 12)
                before = (output / 'http/responses.sqlite3').read_bytes()
                # Only the durable compressed original is needed on replay.
                (sources / (ACCESSION + '.txt')).unlink()
                self.calls.clear()
                second = audit.run(inputs, sources, output)
            self.assertEqual(second['sent_http_attempts'], 0)
            self.assertEqual(second['recorded_http_attempts'], 12)
            self.assertEqual(second['selected_http_responses'], 11)
            self.assertEqual(second['statuses'], {'acquired': 1})
            self.assertEqual(self.calls, [])
            self.assertEqual((output / 'http/responses.sqlite3').read_bytes(), before)

    def test_403_names_remaining_filings_as_unattempted(self):
        later = '0000906107-25-000005'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / (ACCESSION + '.txt')).write_bytes(self.package)
            inputs = root / 'inputs.json'
            inputs.write_text(json.dumps({'filings': [selected(ACCESSION), selected(later)]}))
            calls = []
            def blocked(url, *args):
                calls.append(url)
                return 403, {}, b''
            def factory(path, *, live=False):
                return Campaign(path, live=live, sender=blocked, now=lambda: 0, sleep=lambda n: None)
            with patch.object(audit, 'Campaign', side_effect=factory), redirect_stdout(io.StringIO()):
                summary = audit.run(inputs, root, root / 'output', live=True)
            self.assertEqual(calls, [INDEX])
            self.assertEqual(summary['statuses'], {'failed': 1})
            self.assertEqual(summary['unattempted'], [later])

    def test_storage_failure_stops_the_batch_and_names_unattempted_filings(self):
        later = '0000906107-25-000005'
        for boundary in ('acquire', 'check_space'):
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / (ACCESSION + '.txt')).write_bytes(self.package)
                inputs = root / 'inputs.json'
                inputs.write_text(json.dumps({'filings': [selected(ACCESSION), selected(later)]}))
                with patch.object(audit, 'Campaign', side_effect=self.campaign), \
                        patch.object(audit, boundary, side_effect=StorageError('disk unavailable')), \
                        redirect_stdout(io.StringIO()):
                    summary = audit.run(inputs, root, root / 'output', live=True)
                self.assertEqual(summary['statuses'], {'failed': 1})
                self.assertEqual(summary['unattempted'], [later])
                self.assertEqual(summary['sent_http_attempts'], 0)

    def test_cached_identity_mismatch_is_a_filing_failure_before_requests(self):
        changes = ({'cik': '2'}, {'form': '10-K'},
                   {'acc': '0001004434-23-000016'}, {'sha256': '0' * 64})
        for change in changes:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                output, inputs = root / 'output', root / 'inputs.json'
                source = root / (ACCESSION + '.txt')
                source.write_bytes(self.package)
                valid = selected(ACCESSION)
                inputs.write_text(json.dumps({'filings': [valid]}))
                with patch.object(audit, 'Campaign', side_effect=self.campaign), redirect_stdout(io.StringIO()):
                    self.assertEqual(audit.run(inputs, root, output, live=True)['statuses'], {'acquired': 1})
                source.unlink()
                changed = dict(valid, **change)
                original = output / 'packages' / valid['acc'] / valid['sha256']
                candidate = output / 'packages' / changed['acc'] / changed['sha256']
                if candidate != original:
                    shutil.copytree(original, candidate)
                inputs.write_text(json.dumps({'filings': [changed]}))
                self.calls.clear()
                with patch.object(audit, 'Campaign', side_effect=self.campaign), \
                        patch.object(audit, 'acquire', side_effect=AssertionError('existing cache was reacquired')), \
                        redirect_stdout(io.StringIO()):
                    summary = audit.run(inputs, root / 'absent', output, live=True)
                self.assertEqual(summary['statuses'], {'failed': 1})
                self.assertEqual(summary['sent_http_attempts'], 0)
                self.assertEqual(self.calls, [])
                self.assertEqual(json.loads((output / 'references.json').read_text()), [])
                outcome = json.loads((output / 'outcomes.json').read_text())[0]
                self.assertTrue(outcome.get('error'))
                self.assertEqual(outcome['direct_files'], [])

    def test_existing_corrupt_package_is_not_repaired_from_raw_source(self):
        for name, damaged in (('submission.txt.gz', b'broken gzip'), ('manifest.json', b'{}')):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                output, inputs = root / 'output', root / 'inputs.json'
                (root / (ACCESSION + '.txt')).write_bytes(self.package)
                row = selected(ACCESSION)
                inputs.write_text(json.dumps({'filings': [row]}))
                with patch.object(audit, 'Campaign', side_effect=self.campaign), redirect_stdout(io.StringIO()):
                    self.assertEqual(audit.run(inputs, root, output, live=True)['statuses'], {'acquired': 1})
                version = output / 'packages' / ACCESSION / row['sha256']
                (version / name).write_bytes(damaged)
                before = {p.name: p.read_bytes() for p in version.iterdir()}
                self.calls.clear()
                with patch.object(audit, 'Campaign', side_effect=self.campaign), \
                        patch.object(audit, 'acquire', side_effect=AssertionError('corrupt cache was repaired')), \
                        redirect_stdout(io.StringIO()):
                    summary = audit.run(inputs, root, output, live=True)
                self.assertEqual(summary['statuses'], {'failed': 1})
                self.assertEqual(summary['sent_http_attempts'], 0)
                self.assertEqual(self.calls, [])
                self.assertEqual({p.name: p.read_bytes() for p in version.iterdir()}, before)
