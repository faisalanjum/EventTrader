"""Package-only contract. All network behavior is simulated in test_transport."""
import binascii
import hashlib
import gzip
import io
import json
from contextlib import redirect_stderr
import errno
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import driver.prepare.acquire as acquisition
from driver.prepare.acquire import AcquisitionError, acquire, main, parse_package
from driver.prepare.transport import DownloadError


ACCESSION = '0001004434-23-000015'
CIK = '0001004434'
FORM = '8-K'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def package(documents=None, *, nl=b'\n'):
    """Change framing newlines only; supplied payload bytes stay untouched."""
    documents = documents or [('dir/main.htm', b'<html>hello</html>\n', '8-K', '1', ' first ') ]
    header = nl.join([
        b'<SEC-DOCUMENT>' + ACCESSION.encode() + b'.txt : 20230501',
        b'<SEC-HEADER>' + ACCESSION.encode() + b'.hdr.sgml : 20230501',
        b'<ACCEPTANCE-DATETIME>20230501071224',
        b'ACCESSION NUMBER: ' + ACCESSION.encode(),
        b'CONFORMED SUBMISSION TYPE: 8-K',
        b'PUBLIC DOCUMENT COUNT: ' + str(len(documents)).encode(),
        b'FILER:', b'\tCENTRAL INDEX KEY: ' + CIK.encode(), b'</SEC-HEADER>', b'',
    ])
    for name, payload, kind, sequence, description in documents:
        fields = [b'<DOCUMENT>', b'<TYPE>' + kind.encode(), b'<SEQUENCE>' + sequence.encode(),
                  b'<FILENAME>' + name.encode()]
        if description is not None:
            fields.append(b'<DESCRIPTION>' + description.encode())
        header += nl.join(fields + [b'<TEXT>', b'']) + payload
        header += nl.join([b'</TEXT>', b'</DOCUMENT>', b''])
    return header + b'</SEC-DOCUMENT>' + nl


def uu(data, name='file.bin', nl=b'\n'):
    lines = [b'begin 644 ' + name.encode()]
    for offset in range(0, len(data), 45):
        line = binascii.b2a_uu(data[offset:offset + 45]).rstrip(b'\n').rstrip(b' ')
        lines.append(b'.' + line if line.startswith(b'.') else line)
    return nl.join(lines + [b'`', b'end', b''])


class PackageTests(unittest.TestCase):
    def parse(self, data):
        return parse_package(data, ACCESSION, CIK, FORM)

    def test_exact_metadata_body_and_ranges_lf_and_crlf(self):
        payload = b' \n<html>\xc3\xa9</html>\r\n\n  '
        for nl in (b'\n', b'\r\n'):
            with self.subTest(nl=nl):
                data = package([('dir/main.htm', payload, '8-K', '9', ' first ')], nl=nl)
                manifest, files = self.parse(data)
                self.assertEqual(files, {'dir/main.htm': payload})
                self.assertEqual(manifest['acceptance'], {'printed': '20230501071224', 'timezone': 'America/New_York'})
                self.assertEqual(manifest['identity'], {'accession': ACCESSION, 'ciks': [CIK], 'form': FORM})
                member = manifest['members'][0]
                self.assertEqual((member['filename'], member['type'], member['sequence'], member['description']),
                                 ('dir/main.htm', '8-K', '9', ' first '))
                self.assertEqual(member['sha256'], digest(payload))
                self.assertEqual(member['bytes'], len(payload))
                start, end = member['package_range']
                self.assertEqual(data[start:end], data[data.index(b'<DOCUMENT>'):data.index(b'</DOCUMENT>') + 11 + len(nl)])
                start, end = manifest['header_range']
                self.assertTrue(data[start:end].startswith(b'<SEC-HEADER>'))
                self.assertTrue(data[start:end].endswith(b'</SEC-HEADER>'))

    def test_company_membership_is_order_independent_and_wrong_identity_fails(self):
        original = package()
        line = b'\tCENTRAL INDEX KEY: ' + CIK.encode()
        other = '0000000002'
        baseline = None
        for ciks in ((CIK, other), (other, CIK), (other, CIK, CIK)):
            changed = original.replace(line, b'\n'.join(
                b'\tCENTRAL INDEX KEY: ' + value.encode() for value in ciks))
            for requested in (CIK, other, '2'):
                manifest, files = parse_package(changed, ACCESSION, requested, FORM)
                self.assertEqual(manifest['identity']['ciks'], sorted({CIK, other}))
                self.assertEqual(files['dir/main.htm'], b'<html>hello</html>\n')
                if requested == CIK:
                    baseline = manifest
                else:
                    self.assertEqual(manifest, baseline)
            for bad_acc, bad_cik, bad_form in ((ACCESSION, '3', FORM),
                    ('0001004434-23-000016', CIK, FORM), (ACCESSION, CIK, '10-K')):
                with self.subTest(ciks=ciks, requested=(bad_acc, bad_cik, bad_form)):
                    with self.assertRaises(AcquisitionError):
                        parse_package(changed, bad_acc, bad_cik, bad_form)

    def test_stated_count_is_information_not_completeness(self):
        original = package()
        for stated in (0, 1, 2, 100):
            data = original.replace(b'PUBLIC DOCUMENT COUNT: 1',
                                    b'PUBLIC DOCUMENT COUNT: ' + str(stated).encode())
            manifest, _ = self.parse(data)
            self.assertEqual(manifest['document_count'], {'stated': stated, 'actual': 1})
        start, end = original.index(b'<DOCUMENT>'), original.index(b'</SEC-DOCUMENT>')
        with self.assertRaises(AcquisitionError):
            self.parse(original[:start] + original[end:])

    def test_incomplete_member_cannot_swallow_the_next_member(self):
        for nl in (b'\n', b'\r\n'):
            original = package([('first.txt', b'Literal <TEXT> in prose.\n', '8-K', '1', None),
                                ('second.txt', b'second\n', 'EX-99.1', '2', None)], nl=nl)
            self.assertEqual(list(self.parse(original)[1]), ['first.txt', 'second.txt'])
            endings = (b'<DOCUMENT>', b'<TEXT>', b'</TEXT>', b'</DOCUMENT>',
                       b'</TEXT>' + nl + b'</DOCUMENT>')
            for marker in endings:
                damaged = original.replace(marker + nl, b'', 1)
                with self.subTest(nl=nl, marker=marker), self.assertRaises(AcquisitionError):
                    self.parse(damaged)

    def test_every_declared_cik_must_be_valid(self):
        original = package()
        self.assertEqual(self.parse(original)[0]['identity']['ciks'], [CIK])
        for extra in (b'0000000000', b'12345678901', b'not-a-cik', b''):
            damaged = original.replace(b'</SEC-HEADER>',
                b'\tCENTRAL INDEX KEY: ' + extra + b'\n</SEC-HEADER>')
            with self.subTest(extra=extra), self.assertRaises(AcquisitionError):
                self.parse(damaged)

    def test_wrapper_dots_and_uu_do_not_trim_payload(self):
        for nl in (b'\n', b'\r\n'):
            payload = b' \n..selector\nlast \r\n'
            wire = b'<XML>' + nl + payload.replace(b'\n..', b'\n...') + b'</XML>' + nl
            manifest, files = self.parse(package([('nested/test.xml', wire, 'XML', '1', None)], nl=nl))
            self.assertEqual(files['nested/test.xml'], payload)
            self.assertIsNone(manifest['members'][0]['description'])
            # 45 zero bytes have an entirely trimmed UU line; 14 uses dot length prefix.
            raw = bytes(45) + bytes(range(14))
            wire = b'<PDF>' + nl + uu(raw, nl=nl) + b'</PDF>' + nl
            _, files = self.parse(package([('file.bin', wire, 'EX-99.1', '2', None)], nl=nl))
            self.assertEqual(files['file.bin'], raw)
            # SEC can trim the zero-length UU line to an empty line too.
            _, files = self.parse(package([('file.bin', wire.replace(b'`' + nl, nl), 'EX-99.1', '2', None)], nl=nl))
            self.assertEqual(files['file.bin'], raw)

    def test_uu_ignores_unused_padding_bits_but_rejects_invalid_lines(self):
        _, files = self.parse(package([('file.bin', b'begin 644 file.bin\n!8?__\n`\nend\n', 'GRAPHIC', '1', None)]))
        self.assertEqual(files['file.bin'], b'a')
        valid = uu(b'abc')
        for invalid in (valid.replace(b'file.bin', b'other.bin'), valid.replace(b'end', b'stop'),
                        valid.replace(b'#86)C', b'#\xff6)C'), valid.replace(b'#86)C', b'N86)C'),
                        valid.replace(b'644', b'xyz'), valid.replace(b'#86)C', b'#86)CEXTRA')):
            with self.subTest(invalid=invalid), self.assertRaises(AcquisitionError):
                self.parse(package([('file.bin', invalid, 'GRAPHIC', '1', None)]))

    def test_subdirectories_and_identical_occurrences_survive(self):
        docs = [('a/file.txt', b'first\n', 'EX-99.1', '2', None),
                ('b/file.txt', b'second\n', 'EX-99.1', '7', None),
                ('a/file.txt', b'first\n', 'EX-99.1', '8', 'again')]
        manifest, files = self.parse(package(docs))
        self.assertEqual(files, {'a/file.txt': b'first\n', 'b/file.txt': b'second\n'})
        self.assertEqual([m['sequence'] for m in manifest['members']], ['2', '7', '8'])
        for names in (('same', 'same'), ('dir', 'dir/file'), ('dir/file', 'dir')):
            with self.subTest(names=names), self.assertRaisesRegex(AcquisitionError, 'conflict'):
                self.parse(package([(names[0], b'a', '8-K', '1', None), (names[1], b'b', '8-K', '2', None)]))

    def test_unsafe_paths_fail_without_flattening(self):
        self.assertIn('safe/name', self.parse(package([('safe/name', b'ok', '8-K', '1', None)]))[1])
        for name in ('/absolute', '../escape', 'a/../escape', 'a//b', './a', 'a/./b', 'C:/a',
                     'a\\b', 'a\x00b', 'a\x1fb', '', 'trailing/'):
            with self.subTest(name=name), self.assertRaises(AcquisitionError):
                self.parse(package([(name, b'ok', '8-K', '1', None)]))

    def test_bad_identity_count_time_encoding_and_framing_are_explicit(self):
        original = package()
        self.assertEqual(len(self.parse(original)[0]['members']), 1)
        mutations = [original.replace(ACCESSION.encode(), b'0001004434-23-000016'),
                     original.replace(b'CENTRAL INDEX KEY: ' + CIK.encode(), b'CENTRAL INDEX KEY: 9999999999'),
                     original.replace(b'CONFORMED SUBMISSION TYPE: 8-K', b'CONFORMED SUBMISSION TYPE: 8-K/A'),
                     original.replace(b'20230501071224', b'20230230071224'),
                     original.replace(b'20230501071224', b'not-a-date'),
                     original.replace(b'CONFORMED SUBMISSION TYPE: 8-K', b'CONFORMED SUBMISSION TYPE: \xff-K'),
                     original.replace(b'<DESCRIPTION> first ', b'<DESCRIPTION>\xff'),
                     original.replace(b'<FILENAME>dir/main.htm', b'<FILENAME>\xff'),
                     original.replace(b'</TEXT>', b''), original.replace(b'</DOCUMENT>', b''),
                     original[:-25], original + b'garbage', b'<html>Service unavailable</html>',
                     original.replace(b'</SEC-HEADER>', b'</SEC-HEADER>UNACCOUNTED'),
                     original.replace(b'<SEQUENCE>1', b'<SEQUENCE>1\n<SEQUENCE>2'),
                     original.replace(b'<TYPE>8-K\n', b''),
                     original.replace(b'PUBLIC DOCUMENT COUNT: 1', b'PUBLIC DOCUMENT COUNT: 1\nPUBLIC DOCUMENT COUNT: 1')]
        for mutated in mutations:
            with self.subTest(mutated=mutated[:120]), self.assertRaises(AcquisitionError):
                self.parse(mutated)

    def test_unknown_is_not_text_and_known_magic_is_only_a_hint(self):
        samples = [(b'\x00\xffopaque', 'unknown'), (b'ordinary prose', 'unknown'),
                   (b'%PDF-incomplete', 'pdf'), (b'PK\x03\x04opaque', 'zip'),
                   (b'\xff\xd8\xffopaque', 'jpeg'), (b'\x89PNG\r\n\x1a\n', 'png'),
                   (b'GIF89a', 'gif'), (b'<?xml version="1.0"?><bad', 'xml'),
                   (b'<html><h1>Service unavailable</h1></html>', 'html')]
        for body, expected in samples:
            with self.subTest(expected=expected):
                manifest, files = self.parse(package([('m.bin', body, 'XML', '1', None)]))
                self.assertEqual(manifest['members'][0]['format_hint'], expected)
                self.assertEqual(files['m.bin'], body)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = package()
        self.source = self.root / 'input.txt'
        self.source.write_bytes(self.data)
        self.output = self.root / 'output'

    def acquire(self, **kwargs):
        options = dict(package=self.source, sha256=digest(self.data))
        options.update(kwargs)
        return acquire(ACCESSION, CIK, FORM, self.output, **options)

    def test_publish_replay_and_verified_reuse_make_zero_requests(self):
        with patch('driver.prepare.acquire.download', side_effect=AssertionError('network forbidden')):
            target = self.acquire()
            self.assertEqual(target, self.output / ACCESSION / digest(self.data))
            self.assertEqual(gzip.decompress((target / 'submission.txt.gz').read_bytes()), self.data)
            self.assertEqual({p.name for p in target.iterdir()}, {'submission.txt.gz', 'manifest.json', 'receipt.json'})
            receipt = json.loads((target / 'receipt.json').read_text())
            self.assertIsNone(receipt['retrieved_at'])
            before = {str(p.relative_to(target)): p.read_bytes() for p in target.rglob('*') if p.is_file()}
            self.assertEqual(self.acquire(package=target / 'submission.txt.gz'), target)
            after = {str(p.relative_to(target)): p.read_bytes() for p in target.rglob('*') if p.is_file()}
            self.assertEqual(before, after)
            other = acquire(ACCESSION, '1004434', FORM, self.root / 'replay', package=self.source, sha256=digest(self.data))
            for name in ('manifest.json', 'submission.txt.gz', 'receipt.json'):
                self.assertEqual((target / name).read_bytes(), (other / name).read_bytes())

    def test_read_package_decodes_once_and_checks_saved_evidence(self):
        target = self.acquire()
        with patch('driver.prepare.acquire.parse_package', wraps=parse_package) as parse:
            manifest, files = acquisition.read_package(target)
            self.assertEqual(files, {'dir/main.htm': b'<html>hello</html>\n'})
            self.assertEqual(manifest['package']['sha256'], digest(self.data))
            parse.assert_called_once()
        saved = (target / 'manifest.json').read_bytes()
        for mutate in (
                lambda m: m['members'][0].update(sha256='0' * 64),
                lambda m: m['members'][0].update(package_range=[0, 1]),
                lambda m: m.update(members=[]),
                lambda m: m['identity'].update(form='10-K'),
                lambda m: m['identity'].update(form=1),
                lambda m: m['identity'].update(form=True),
                lambda m: m['identity'].update(ciks=[1]),
                lambda m: m['identity'].update(accession=[]),
                lambda m: m.update(identity=[]),
                lambda m: m['package'].update(sha256='0' * 64)):
            manifest = json.loads(saved)
            mutate(manifest)
            (target / 'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises(AcquisitionError):
                acquisition.read_package(target)
        (target / 'manifest.json').write_bytes(saved)
        self.assertEqual(acquisition.read_package(target)[1], files)

    def test_immutable_compressed_input_is_shared_without_recompression(self):
        self.source.write_bytes(gzip.compress(self.data, compresslevel=1, mtime=123))
        original = self.source.read_bytes()
        with patch('driver.prepare.acquire._compress', side_effect=AssertionError('compressed twice')):
            target = self.acquire()
        saved = target / 'submission.txt.gz'
        self.assertTrue(saved.samefile(self.source), 'the two paths must use one physical copy')
        self.assertEqual(saved.read_bytes(), original)
        self.assertEqual(acquisition.read_package(target)[1]['dir/main.htm'], b'<html>hello</html>\n')
        self.source.unlink()
        self.assertEqual(gzip.decompress(saved.read_bytes()), self.data)

    def test_compressed_source_symlinks_fail_without_publication(self):
        source = self.root / 'original.gz'
        source.write_bytes(gzip.compress(self.data))
        self.source.unlink()
        self.source.symlink_to(source)
        with self.assertRaises(AcquisitionError):
            self.acquire()
        self.assertFalse(self.output.exists())

    def test_storage_shortage_stops_before_download_and_during_publication(self):
        from driver.prepare.acquire import StorageError
        with patch('driver.prepare.acquire.shutil.disk_usage') as usage, \
                patch('driver.prepare.acquire.download', side_effect=AssertionError('network forbidden')):
            usage.return_value.free = 0
            with self.assertRaises(StorageError):
                acquire(ACCESSION, CIK, FORM, self.output, live=True)
        self.source.write_bytes(gzip.compress(self.data))
        for number in (errno.ENOSPC, errno.EDQUOT, errno.EXDEV):
            with self.subTest(errno=number), \
                    patch('driver.prepare.acquire.os.link', side_effect=OSError(number, 'storage unavailable')):
                with self.assertRaises(StorageError):
                    self.acquire()
            self.assertFalse((self.output / ACCESSION / digest(self.data)).exists())
            self.assertEqual(gzip.decompress(self.source.read_bytes()), self.data)

    def test_same_package_reuses_version_for_each_listed_company(self):
        self.data = self.data.replace(b'\tCENTRAL INDEX KEY: ' + CIK.encode(),
            b'\tCENTRAL INDEX KEY: ' + CIK.encode() + b'\n\tCENTRAL INDEX KEY: 0000000002')
        self.source.write_bytes(self.data)
        first = self.acquire()
        with patch('driver.prepare.acquire.download', side_effect=AssertionError('network forbidden')):
            second = acquire(ACCESSION, '2', FORM, self.output,
                             package=first / 'submission.txt.gz', sha256=digest(self.data))
        self.assertEqual(first, second)

    def test_corrupt_gzip_input_fails_without_output(self):
        good = gzip.compress(self.data)
        for damaged in (good[:-8], good[:10] + b'\xff' * 10 + good[-8:]):
            self.source.write_bytes(damaged)
            with self.assertRaises(AcquisitionError):
                self.acquire()
            self.assertFalse(self.output.exists())
        self.source.write_bytes(good)
        self.assertTrue(self.acquire().is_dir())

    def test_bad_hash_and_request_fail_before_output_or_network(self):
        for arguments in ({'sha256': None}, {'sha256': '0' * 64}, {'sha256': 'bad'}, {'live': True}):
            with self.subTest(arguments=arguments), self.assertRaises(AcquisitionError):
                self.acquire(**arguments)
        for accession, cik, form in (('../bad', CIK, FORM), (ACCESSION, 'x', FORM),
                                     (ACCESSION, CIK, ''), (ACCESSION, CIK, '8-K\n'),
                                     (None, CIK, FORM), (ACCESSION, 123, FORM),
                                     (ACCESSION, CIK, 1)):
            with self.subTest(identity=(accession, cik, form)), self.assertRaises(AcquisitionError):
                acquire(accession, cik, form, self.output, package=self.source, sha256=digest(self.data))
        self.assertFalse(self.output.exists())

    def test_cache_corruption_and_unexpected_paths_stop_without_repair(self):
        target = self.acquire()
        for relative, content in [('submission.txt.gz', b'bad'), ('manifest.json', b'{}'),
                                  ('manifest.json', b'not json'), ('receipt.json', b'[]'),
                                  ('unlisted', b'extra')]:
            with self.subTest(relative=relative):
                path = target / relative
                saved = path.read_bytes() if path.exists() else None
                path.write_bytes(content)
                with self.assertRaisesRegex(AcquisitionError, 'cache'):
                    self.acquire()
                with self.assertRaises(AcquisitionError):
                    acquisition.read_package(target)
                self.assertEqual(path.read_bytes(), content)
                if saved is None:
                    path.unlink()
                else:
                    path.write_bytes(saved)
        self.assertEqual(self.acquire(), target)

    def test_cache_symlinks_and_output_symlink_parents_fail(self):
        target = self.acquire()
        member = target / 'submission.txt.gz'
        member.unlink()
        member.symlink_to(self.source)
        with self.assertRaises(AcquisitionError):
            self.acquire()
        outside = self.root / 'outside'
        outside.mkdir()
        (self.root / 'link').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(AcquisitionError):
            acquire(ACCESSION, CIK, FORM, self.root / 'link/new', package=self.source, sha256=digest(self.data))
        self.assertEqual(list(outside.iterdir()), [])

    def test_new_version_does_not_replace_old_and_interruption_is_not_published(self):
        target = self.acquire()
        prior = (target / 'manifest.json').read_bytes()
        changed = self.data.replace(b'hello', b'world')
        self.source.write_bytes(changed)
        with patch('driver.prepare.acquire.os.rename', side_effect=OSError('interrupted')):
            with self.assertRaises(AcquisitionError):
                self.acquire(sha256=digest(changed))
        self.assertEqual(list((self.output / ACCESSION).iterdir()), [target])
        new = self.acquire(sha256=digest(changed))
        self.assertNotEqual(new, target)
        self.assertEqual((target / 'manifest.json').read_bytes(), prior)

    def test_live_uses_only_derived_package_url_and_preserves_receipt(self):
        receipt = {'retrieved_at': '2026-10-01T00:00:00+00:00', 'attempts': [{'status': 200}]}
        with patch('driver.prepare.acquire.download', return_value=(self.data, receipt)) as request:
            target = acquire(ACCESSION, CIK, FORM, self.output, live=True)
        request.assert_called_once_with('https://www.sec.gov/Archives/edgar/data/1004434/000100443423000015/0001004434-23-000015.txt')
        self.assertEqual(json.loads((target / 'receipt.json').read_text()), receipt)
        for data in (b'<html>Error</html>', self.data[:-25]):
            with patch('driver.prepare.acquire.download', return_value=(data, receipt)), self.assertRaises(AcquisitionError) as caught:
                acquire(ACCESSION, CIK, FORM, self.output, live=True)
            self.assertEqual(caught.exception.receipt, receipt)
        self.assertEqual(len(list((self.output / ACCESSION).iterdir())), 1)

    def test_cli_failures_keep_http_receipt_without_publishing(self):
        receipt = {'url': 'https://www.sec.gov/package', 'retrieved_at': '2026-10-01T00:00:00+00:00',
                   'attempts': [{'status': 200}]}
        for response in ((b'<html>Error</html>', receipt), DownloadError('HTTP 403', receipt)):
            options = {'side_effect': response} if isinstance(response, Exception) else {'return_value': response}
            stderr = io.StringIO()
            with patch('driver.prepare.acquire.download', **options), redirect_stderr(stderr):
                status = main(['--accession', ACCESSION, '--cik', CIK, '--form', FORM, '--output', str(self.output), '--live'])
            self.assertEqual(status, 1)
            self.assertEqual(json.loads(stderr.getvalue().split('\n', 1)[1]), receipt)
            self.assertFalse(self.output.exists())

    def test_cli_hash_required_and_errors_have_no_traceback(self):
        cmd = [sys.executable, '-B', '-S', '-m', 'driver.prepare.acquire', '--accession', ACCESSION,
               '--cik', CIK, '--form', FORM, '--output', str(self.output), '--package', str(self.source)]
        failed = subprocess.run(cmd, text=True, capture_output=True)
        self.assertNotEqual(failed.returncode, 0)
        self.assertNotIn('Traceback', failed.stderr)
        ok = subprocess.run(cmd + ['--sha256', digest(self.data)], text=True, capture_output=True)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertTrue(Path(ok.stdout.strip()).is_dir())


class RealPackageTests(unittest.TestCase):
    def test_originals_and_exact_ranges(self):
        for accession in (ACCESSION, '0000950170-25-021181', '0000906107-25-000005'):
            fixture = Path(__file__).with_name('fixtures') / (accession + '.expected.json')
            with self.subTest(fixture=fixture.name):
                expected = json.loads(fixture.read_bytes())
                raw = gzip.decompress(fixture.with_name(
                    fixture.name.replace('.expected.json', '.txt.gz')).read_bytes())
                self.assertEqual((len(raw), digest(raw)),
                                 (expected['package']['bytes'], expected['package']['sha256']))
                manifest, files = parse_package(raw, **expected['request'])
                for key in ('identity', 'acceptance', 'document_count', 'header_range'):
                    self.assertEqual(manifest[key], expected[key])
                actual = [{key: member[key] for key in expected['members'][0]}
                          for member in manifest['members']]
                self.assertEqual(actual, expected['members'])
                self.assertEqual(len(files), len({m['filename'] for m in expected['members']}))
                for member in expected['members']:
                    data = files[member['filename']]
                    self.assertEqual((len(data), digest(data)), (member['bytes'], member['sha256']))
                with tempfile.TemporaryDirectory() as output:
                    source = Path(output) / 'input.txt'
                    source.write_bytes(raw)
                    target = acquire(**expected['request'], output=Path(output) / 'saved',
                                     package=source, sha256=expected['package']['sha256'])
                    recovered_manifest, recovered_files = acquisition.read_package(target)
                    self.assertEqual(recovered_manifest, manifest)
                    self.assertEqual(recovered_files, files)


if __name__ == '__main__':
    unittest.main()
