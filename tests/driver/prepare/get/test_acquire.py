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

import driver.prepare.get.acquire as acquisition
from driver.prepare.get.acquire import AcquisitionError, acquire, main, parse_package
from driver.prepare.get.transport import DownloadError


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
            data = package([('nested/test.xml', wire, 'XML', '1', None)], nl=nl)
            manifest, files = parse_package(data, ACCESSION, CIK, FORM, fetch=lambda url: payload)
            self.assertEqual(files['nested/test.xml'], payload)  # SEC's copy chose "remove one dot"
            self.assertIsNone(manifest['members'][0]['description'])
            literal = payload.replace(b'\n..', b'\n...')
            self.assertEqual(parse_package(data, ACCESSION, CIK, FORM, fetch=lambda url: literal)[1]['nested/test.xml'], literal)
            # 45 zero bytes have an entirely trimmed UU line; 14 uses dot length prefix.
            raw = bytes(45) + bytes(range(14))
            wire = b'<PDF>' + nl + uu(raw, nl=nl) + b'</PDF>' + nl
            sec_copy = lambda url: raw  # its last UU line starts with a doubled dot: SEC's copy decides
            _, files = parse_package(package([('file.bin', wire, 'EX-99.1', '2', None)], nl=nl), ACCESSION, CIK, FORM, fetch=sec_copy)
            self.assertEqual(files['file.bin'], raw)
            # SEC can trim the zero-length UU line to an empty line too.
            _, files = parse_package(package([('file.bin', wire.replace(b'`' + nl, nl), 'EX-99.1', '2', None)], nl=nl),
                                     ACCESSION, CIK, FORM, fetch=sec_copy)
            self.assertEqual(files['file.bin'], raw)

    def test_uu_ignores_unused_padding_bits_but_rejects_invalid_lines(self):
        _, files = self.parse(package([('file.bin', b'begin 644 file.bin\n!8?__\n`\nend\n', 'GRAPHIC', '1', None)]))
        self.assertEqual(files['file.bin'], b'a')
        valid = uu(b'abc')
        for invalid in (valid.replace(b'file.bin', b'other.bin'), valid.replace(b'end', b'stop'),
                        valid.replace(b'#86)C', b'#\xff6)C'), valid.replace(b'644', b'xyz')):
            with self.subTest(invalid=invalid), self.assertRaises(AcquisitionError):
                self.parse(package([('file.bin', invalid, 'GRAPHIC', '1', None)]))
        for unreadable in (valid.replace(b'#86)C', b'N86)C'), valid.replace(b'#86)C', b'#86)CEXTRA')):
            with self.subTest(unreadable=unreadable):  # readable only with a '- ' put back: never decoded unproven
                manifest, files = self.parse(package([('file.bin', unreadable, 'GRAPHIC', '1', None)]))
                self.assertEqual((files, manifest['members'][0]['proof']), ({}, {'unresolved': 'not checked against SEC copy'}))

    def test_uu_last_line_readable_only_with_a_dash_needs_sec_proof(self):
        # Real case: SEC dropped "- " from the last line of its XBRL zip (Guidewire 8-K; it kept it in 1,666 other such
        # lines). Put back, it reads, but SEC's own copy was made from the damaged text and lacks those 13 bytes:
        # nothing proves the restore, so the file stays unresolved, never guessed.
        fixtures, name = Path(__file__).with_name('fixtures'), '0001528396-23-000024-xbrl.zip'
        data = gzip.decompress((fixtures / '0001528396-23-000024.txt.gz').read_bytes())
        copy = gzip.decompress((fixtures / 'sec_copy_0001528396-23-000024_xbrl.zip.gz').read_bytes())
        manifest, files = parse_package(data, '0001528396-23-000024', '1528396', '8-K', fetch=lambda url: copy)
        entry = next(m for m in manifest['members'] if m['filename'] == name)
        self.assertEqual((entry['proof']['unresolved'], entry['sha256'], name in files), ('SEC copy fits no single reading', None, False))
        # Synthetic: a final 13-byte line starting with a zero byte encodes as "- ...". Kept, it is read as published.
        raw = bytes(range(45)) + b'\x00\x05' + b'tail-bytes!'
        wire = uu(raw)
        manifest, files = self.parse(package([('file.bin', wire, 'GRAPHIC', '1', None)]))
        self.assertEqual((files['file.bin'], 'proof' in manifest['members'][0]), (raw, False))
        stripped = wire.replace(b'\n- ', b'\n', 1)  # dropped: readable only with "- " put back, so SEC's copy decides
        self.assertNotEqual(stripped, wire)
        _, files = parse_package(package([('file.bin', stripped, 'GRAPHIC', '1', None)]), ACCESSION, CIK, FORM,
                                 fetch=lambda url: raw)
        self.assertEqual(files['file.bin'], raw)

    def test_zip_bytes_are_decoded_exactly_not_judged(self):
        import zipfile
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('a.txt', b'evidence ' * 50)
        good = buffer.getvalue()
        _, files = self.parse(package([('data.zip', uu(good, 'data.zip'), 'ZIP', '1', None)]))
        self.assertEqual(files['data.zip'], good)
        bad = bytearray(good)
        bad[40] ^= 0xFF  # inside the compressed data: valid uuencode, other bytes, no guess involved
        self.assertEqual(self.parse(package([('data.zip', uu(bytes(bad), 'data.zip'), 'ZIP', '1', None)]))[1]['data.zip'], bytes(bad))

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

    def test_empty_lines_between_framing_tags_are_skipped_and_nothing_else(self):
        # Landstar 0001193125-23-048874: SEC left one empty line after </SEC-HEADER>.
        documents = [('a.htm', b'<p>one</p>\n\n\n', '10-K', '1', None), ('b.txt', b'\n\ntwo\r\n', 'EX-1', '2', 'x')]
        for nl in (b'\n', b'\r\n'):
            plain = package(documents, nl=nl)
            expected_manifest, expected_files = self.parse(plain)
            for count in (1, 4):
                gap = nl * count
                spaced = {'header': plain.replace(b'</SEC-HEADER>' + nl, b'</SEC-HEADER>' + nl + gap),
                          'members': plain.replace(b'</DOCUMENT>' + nl, b'</DOCUMENT>' + nl + gap)}
                spaced['both'] = spaced['header'].replace(b'</DOCUMENT>' + nl, b'</DOCUMENT>' + nl + gap)
                for where, data in spaced.items():
                    with self.subTest(nl=nl, count=count, where=where):
                        manifest, files = self.parse(data)
                        self.assertEqual(files, expected_files)  # TEXT bytes, inner blank lines included
                        self.assertEqual([{k: v for k, v in m.items() if k != 'package_range'} for m in manifest['members']],
                                         [{k: v for k, v in m.items() if k != 'package_range'} for m in expected_manifest['members']])
                        for member in manifest['members']:
                            start, end = member['package_range']
                            self.assertTrue(data[start:end].startswith(b'<DOCUMENT>' + nl))
                            self.assertTrue(data[start:end].endswith(b'</DOCUMENT>' + nl))
            for junk in (b' ' + nl, b'\t' + nl, b'x' + nl, b'\r', nl + b' ' + nl):
                for marker in (b'</SEC-HEADER>' + nl, b'</DOCUMENT>' + nl):
                    with self.subTest(nl=nl, junk=junk, marker=marker), self.assertRaises(AcquisitionError):
                        self.parse(plain.replace(marker, marker + junk))

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
        with patch('driver.prepare.get.acquire.download', side_effect=AssertionError('network forbidden')):
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
        with patch('driver.prepare.get.acquire.parse_package', wraps=parse_package) as parse:
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
        with patch('driver.prepare.get.acquire._compress', side_effect=AssertionError('compressed twice')):
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
        from driver.prepare.get.acquire import StorageError
        with patch('driver.prepare.get.acquire.shutil.disk_usage') as usage, \
                patch('driver.prepare.get.acquire.download', side_effect=AssertionError('network forbidden')):
            usage.return_value.free = 0
            with self.assertRaises(StorageError):
                acquire(ACCESSION, CIK, FORM, self.output, live=True)
        self.source.write_bytes(gzip.compress(self.data))
        for number in (errno.ENOSPC, errno.EDQUOT, errno.EXDEV):
            with self.subTest(errno=number), \
                    patch('driver.prepare.get.acquire.os.link', side_effect=OSError(number, 'storage unavailable')):
                with self.assertRaises(StorageError):
                    self.acquire()
            self.assertFalse((self.output / ACCESSION / digest(self.data)).exists())
            self.assertEqual(gzip.decompress(self.source.read_bytes()), self.data)

    def test_same_package_reuses_version_for_each_listed_company(self):
        self.data = self.data.replace(b'\tCENTRAL INDEX KEY: ' + CIK.encode(),
            b'\tCENTRAL INDEX KEY: ' + CIK.encode() + b'\n\tCENTRAL INDEX KEY: 0000000002')
        self.source.write_bytes(self.data)
        first = self.acquire()
        with patch('driver.prepare.get.acquire.download', side_effect=AssertionError('network forbidden')):
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
        with patch('driver.prepare.get.acquire.os.rename', side_effect=OSError('interrupted')):
            with self.assertRaises(AcquisitionError):
                self.acquire(sha256=digest(changed))
        self.assertEqual(list((self.output / ACCESSION).iterdir()), [target])
        new = self.acquire(sha256=digest(changed))
        self.assertNotEqual(new, target)
        self.assertEqual((target / 'manifest.json').read_bytes(), prior)

    def test_live_uses_only_derived_package_url_and_preserves_receipt(self):
        receipt = {'retrieved_at': '2026-10-01T00:00:00+00:00', 'attempts': [{'status': 200}]}
        with patch('driver.prepare.get.acquire.download', return_value=(self.data, receipt)) as request:
            target = acquire(ACCESSION, CIK, FORM, self.output, live=True)
        request.assert_called_once_with('https://www.sec.gov/Archives/edgar/data/1004434/000100443423000015/0001004434-23-000015.txt')
        self.assertEqual(json.loads((target / 'receipt.json').read_text()), receipt)
        for data in (b'<html>Error</html>', self.data[:-25]):
            with patch('driver.prepare.get.acquire.download', return_value=(data, receipt)), self.assertRaises(AcquisitionError) as caught:
                acquire(ACCESSION, CIK, FORM, self.output, live=True)
            self.assertEqual(caught.exception.receipt, receipt)
        self.assertEqual(len(list((self.output / ACCESSION).iterdir())), 1)

    def test_a_package_read_error_other_than_missing_stops_everything(self):
        # Codex review 2026-10-03: EACCES/EMFILE on the supplied package became a per-filing error and the run went on
        real = Path.read_bytes
        for injected, error in ((OSError(errno.ENOENT, 'missing'), AcquisitionError),
                                (OSError(errno.EACCES, 'denied'), acquisition.StorageError),
                                (OSError(errno.EMFILE, 'file handles'), acquisition.StorageError),
                                (OSError(errno.EIO, 'I/O error'), acquisition.StorageError),
                                (OSError('unspecified read error'), acquisition.StorageError)):  # Codex round 3: no errno
            def failing(path, injected=injected):
                if path == self.source:
                    raise injected
                return real(path)
            with self.subTest(error=str(injected)), patch.object(Path, 'read_bytes', failing), \
                    self.assertRaises(AcquisitionError) as caught:
                self.acquire()
            self.assertIs(type(caught.exception), error)
        self.assertFalse(self.output.exists())
        # Codex review round 2: checking a path's metadata (before reading) follows the same rule; a symlink stays per-filing
        real_link = Path.is_symlink
        for target in (self.source, self.output):  # the supplied package, and the output checked before the error handler
            for code in (errno.EACCES, errno.EMFILE):
                def unreadable(path, target=target, code=code):
                    if path == target:
                        raise OSError(code, 'injected metadata failure')
                    return real_link(path)
                with self.subTest(path=target.name, errno=code), patch.object(Path, 'is_symlink', unreadable), \
                        self.assertRaises(acquisition.StorageError):
                    self.acquire()
        with patch.object(Path, 'is_symlink', lambda path: path == self.source), self.assertRaises(AcquisitionError) as caught:
            self.acquire()
        self.assertIs(type(caught.exception), AcquisitionError)

    def test_transport_errors_stay_per_filing_with_their_receipts(self):
        # Codex review round 3: only DownloadError is exempt from the storage rule, so HTTP failures never stop the run
        for reason in ('HTTP 403', 'HTTP 404', 'HTTP retries exhausted'):
            receipt = {'attempts': [{'error': reason}]}
            with self.subTest(reason=reason), patch('driver.prepare.get.acquire.download', side_effect=DownloadError(reason, receipt)), \
                    self.assertRaises(AcquisitionError) as caught:
                acquire(ACCESSION, CIK, FORM, self.output, live=True, minimum_free_bytes=0)
            self.assertEqual((type(caught.exception), caught.exception.receipt), (AcquisitionError, receipt))

    def test_live_mode_never_fetches_proof_copies_itself(self):
        # Codex review 2026-10-03: a direct fetch kept going after a 403; proofs go only through the caller's campaign
        data = package([('a.css', b'..x {}\n', 'EX-99.1', '1', None)])
        receipt = {'retrieved_at': '2026-10-01T00:00:00+00:00', 'attempts': [{'status': 200}]}
        with patch('driver.prepare.get.acquire.download', return_value=(data, receipt)) as request:
            target = acquire(ACCESSION, CIK, FORM, self.output, live=True)
        member, = json.loads((target / 'manifest.json').read_text())['members']
        self.assertEqual((request.call_count, member['proof']), (1, {'unresolved': 'not checked against SEC copy'}))

    def test_cli_failures_keep_http_receipt_without_publishing(self):
        receipt = {'url': 'https://www.sec.gov/package', 'retrieved_at': '2026-10-01T00:00:00+00:00',
                   'attempts': [{'status': 200}]}
        for response in ((b'<html>Error</html>', receipt), DownloadError('HTTP 403', receipt)):
            options = {'side_effect': response} if isinstance(response, Exception) else {'return_value': response}
            stderr = io.StringIO()
            with patch('driver.prepare.get.acquire.download', **options), redirect_stderr(stderr):
                status = main(['--accession', ACCESSION, '--cik', CIK, '--form', FORM, '--output', str(self.output), '--live'])
            self.assertEqual(status, 1)
            self.assertEqual(json.loads(stderr.getvalue().split('\n', 1)[1]), receipt)
            self.assertFalse(self.output.exists())

    def test_cli_hash_required_and_errors_have_no_traceback(self):
        cmd = [sys.executable, '-B', '-S', '-m', 'driver.prepare.get.acquire', '--accession', ACCESSION,
               '--cik', CIK, '--form', FORM, '--output', str(self.output), '--package', str(self.source)]
        failed = subprocess.run(cmd, text=True, capture_output=True)
        self.assertNotEqual(failed.returncode, 0)
        self.assertNotIn('Traceback', failed.stderr)
        ok = subprocess.run(cmd + ['--sha256', digest(self.data)], text=True, capture_output=True)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertTrue(Path(ok.stdout.strip()).is_dir())


class ProofTests(unittest.TestCase):
    """A file SEC's escaping makes ambiguous is kept only when SEC's own copy proves exactly one reading."""
    fixtures = Path(__file__).with_name('fixtures')

    def test_one_inserted_run(self):
        cases = {(b'abc', b'abc'): [], (b'abcdef', b'abcXYdef'): [3, 5], (b'abc', b'XYabc'): [0, 2], (b'abc', b'abcXY'): [3, 5],
                 (b'</body>', b'<s></body>'): [1, 4], (b'abc', b'aXbYc'): None, (b'abc', b'ab'): None, (b'abc', b'abd'): None}
        for (expected, copy), want in cases.items():
            run = acquisition._one_run(expected, copy)
            self.assertEqual(run, want, (expected, copy))
            if run:  # removing exactly that run gives back the expected bytes
                self.assertEqual(copy[:run[0]] + copy[run[1]:], expected)

    def test_real_2025_page_keeps_its_dot_despite_the_script_sec_adds(self):
        block = gzip.decompress((self.fixtures / 'block_0001193125-25-020426_d905299dex993.htm.gz').read_bytes())
        copy = gzip.decompress((self.fixtures / 'sec_copy_0001193125-25-020426_d905299dex993.htm.gz').read_bytes())
        start, end = block.index(b'<TEXT>\n') + len(b'<TEXT>\n'), block.rindex(b'</TEXT>\n')
        readings, needs_proof = acquisition._readings(block[start:end], 'd905299dex993.htm')
        data, how = acquisition._prove(copy, readings, block[:start], block[end:])
        self.assertEqual((needs_proof, data, how['form']), (True, block[start:end], 'block'))  # the literal text: keep
        first, last = how['inserted']
        self.assertEqual((last - first, copy[:first] + copy[last:]), (123, block))

    def test_two_checksum_valid_zips_only_sec_copy_decides(self):
        import zipfile
        readings, needs_proof = acquisition._readings((self.fixtures / 'two_valid_zips_original.uu').read_bytes(), 'fixture.zip')
        self.assertTrue(needs_proof and all(zipfile.ZipFile(io.BytesIO(data)).testzip() is None for _, data in readings))
        for name in ('two_valid_zips_original.zip', 'two_valid_zips_other.zip'):
            copy = (self.fixtures / name).read_bytes()
            self.assertEqual(acquisition._prove(copy, readings, b'', b'')[0], copy)

    def test_a_wrong_dash_guess_is_left_unresolved(self):
        original = (self.fixtures / 'dash_control.pdf').read_bytes()  # a valid 463-byte PDF (Codex)
        lines = uu(original, 'proof.pdf').splitlines(keepends=True)
        damaged = b''.join(lines[:-3] + [lines[-3][1:]] + lines[-2:])  # one length byte lost: the '- ' rule fires
        readings, needs_proof = acquisition._readings(damaged, 'proof.pdf')
        self.assertTrue(needs_proof and all(data != original and len(data) == len(original) for _, data in readings))
        self.assertIsNone(acquisition._prove(original, readings, b'', b''))

    def test_same_size_same_signature_readings_need_sec_copy(self):
        prefix = b'%PDF-1.4\n%evidence\n'
        data = prefix + b' ' * (-len(prefix) % 45) + b'8000000\n%%EOF\n'  # last UU line: 14 bytes from '8' -> starts '..'
        literal = (b'begin 644 x.pdf\n' + b''.join(binascii.b2a_uu(data[i:i + 45]).rstrip(b' \n') + b'\n'
                                                  for i in range(0, len(data), 45)) + b'`\nend\n')
        self.assertTrue(b'\n..' in literal and b'\n.' not in literal.replace(b'\n..', b''))
        readings, needs_proof = acquisition._readings(literal, 'x.pdf')
        self.assertTrue(needs_proof and len(readings) == 2)
        self.assertTrue(all(len(read) == len(data) and read.startswith(b'%PDF-') for _, read in readings))
        for wire in (literal, uu(data, 'x.pdf')):  # an unstuffed and a stuffed package of the same PDF
            self.assertEqual(acquisition._prove(data, acquisition._readings(wire, 'x.pdf')[0], b'', b'')[0], data)

    def test_a_run_counts_only_inside_an_exact_envelope_even_at_the_text_end(self):
        before, text, after = b'<DOCUMENT>\n<TEXT>\n', b'<p>x</p>\n..a\n', b'</TEXT>\n</DOCUMENT>\n'
        readings = [(text, text), (b'<p>x</p>\n.a\n', b'<p>x</p>\n.a\n')]
        end = len(before) + len(text)  # a run starting like the envelope after it ('<') is still inside the TEXT
        self.assertEqual(acquisition._prove(before + text + b'<s/>' + after, readings, before, after),
                         (text, dict(form='block', inserted=[end, end + 4])))
        for copy in (b'X' + before[1:] + text + b'<s/>' + after, before + text + b'<s/>' + after[:-1] + b'X'):
            self.assertIsNone(acquisition._prove(copy, readings, before, after))  # envelope changed: no proof

    def test_a_page_served_as_bytes_may_hold_one_run_but_must_be_mostly_the_file(self):
        # Real case: SEC served a 2024 10-K page (0001178913-24-000717 zk2431010.htm) unwrapped, with a 123-byte script
        # before </body>; only the reading with one dot removed fits (evidence/probe_zk2431010.log).
        page = b'<html><body>\n..note\n<p>text</p>\n</body></html>\n'
        readings = [(b'<XBRL>\n' + page + b'</XBRL>\n', page), (b'<XBRL>\n' + page.replace(b'\n..', b'\n.') + b'</XBRL>\n', page.replace(b'\n..', b'\n.'))]
        script = b'<script src="/x"></script>'
        served = readings[1][1].replace(b'</body>', script + b'</body>')
        data, how = acquisition._prove(served, readings, b'<DOCUMENT>\n<TEXT>\n', b'</TEXT>\n</DOCUMENT>\n')
        first, last = how['inserted']
        self.assertEqual((data, how['form'], last - first, served[:first] + served[last:]), (readings[1][1], 'bytes', len(script), data))
        tiny = [(b'..\n', b'..\n'), (b'.\n', b'.\n')]  # a copy that is mostly something else proves nothing
        for unrelated in (b'some other page ending in a dot.\n', b'.' + b'x' * 40 + b'\n'):
            self.assertIsNone(acquisition._prove(unrelated, tiny, b'', b''))

    def test_two_members_with_one_name_keep_their_own_proofs(self):
        data = package([('a.css', b'..x\n', 'EX-99.1', '1', None), ('a.css', b'..y\n', 'EX-99.2', '2', None)])
        manifest, files = parse_package(data, ACCESSION, CIK, FORM, fetch=lambda url: b'.x\n')
        self.assertEqual(([m['proof'].get('unresolved') for m in manifest['members']], files),
                         ([None, 'SEC copy fits no single reading'], {'a.css': b'.x\n'}))
        with tempfile.TemporaryDirectory() as out:
            source = Path(out) / 'in.txt'
            source.write_bytes(data)
            target = acquire(ACCESSION, CIK, FORM, Path(out) / 'v', package=source, sha256=digest(data), fetch=lambda url: b'.x\n')
            self.assertEqual(acquisition.read_package(target), (manifest, files))

    def test_a_copy_repeating_the_damaged_text_cannot_prove_a_dash_restore(self):
        # Codex review 2026-10-03: served as its package block, a file whose '- ' was dropped repeats the damaged line;
        # that proves nothing. Only SEC's bytes of the restored file could.
        raw = bytes(range(45)) + b'\x00\x05' + b'tail-bytes!'
        stripped = uu(raw).replace(b'\n- ', b'\n', 1)
        for wire in (stripped, b'<PDF>\n' + stripped + b'</PDF>\n'):
            data = package([('file.bin', wire, 'GRAPHIC', '1', None)])
            block = data[data.index(b'<DOCUMENT>'):data.index(b'</DOCUMENT>\n') + len(b'</DOCUMENT>\n')]
            manifest, files = parse_package(data, ACCESSION, CIK, FORM, fetch=lambda url: block)
            self.assertEqual((files, manifest['members'][0]['proof'].get('unresolved')), ({}, 'SEC copy fits no single reading'))
            self.assertEqual(parse_package(data, ACCESSION, CIK, FORM, fetch=lambda url: raw)[1], {'file.bin': raw})

    def test_a_copy_fitting_both_readings_proves_nothing(self):
        readings = [(b'..a\n', b'..a\n'), (b'.a\n', b'.a\n')]
        self.assertEqual(acquisition._prove(b'..a\n', readings, b'', b'')[0], b'..a\n')  # an exact fit wins
        self.assertIsNone(acquisition._prove(b'...a\n', readings, b'', b''))  # each fits only with a run

    def test_proofs_are_recorded_replayed_offline_and_checked(self):
        data = package([('a.css', b'..x {}\n', 'EX-99.1', '1', None), ('b.txt', b'plain\n', 'EX-99.2', '2', None)])
        copy = lambda url: b'.x {}\n'
        manifest, files = parse_package(data, ACCESSION, CIK, FORM, fetch=copy)
        entry = manifest['members'][0]
        self.assertEqual((manifest['decoder'], files['a.css'], entry['proof']['form'], entry['proof']['url']),
                         ('sec-framing-uu-v2', b'.x {}\n', 'bytes',
                          'https://www.sec.gov/Archives/edgar/data/1004434/000100443423000015/a.css'))
        self.assertNotIn('proof', manifest['members'][1])
        with tempfile.TemporaryDirectory() as out:
            source = Path(out) / 'in.txt'
            source.write_bytes(data)
            target = acquire(ACCESSION, CIK, FORM, Path(out) / 'versions', package=source, sha256=digest(data), fetch=copy)
            with patch.object(acquisition, '_prove', side_effect=AssertionError('replay must not re-prove')):
                self.assertEqual(acquisition.read_package(target), (manifest, files))
            stored = json.loads((target / 'manifest.json').read_text())
            stored['members'][0]['sha256'] = '0' * 64
            (target / 'manifest.json').write_text(json.dumps(stored))
            with self.assertRaisesRegex(AcquisitionError, 'matches no reading'):
                acquisition.read_package(target)

    def test_unproven_files_are_listed_never_guessed(self):
        data = package([('a.css', b'..x {}\n', 'EX-99.1', '1', None)])
        for fetch, why in ((None, 'not checked against SEC copy'), (lambda url: None, 'SEC copy unavailable'),
                           (lambda url: b'other\n', 'SEC copy fits no single reading')):
            with self.subTest(why=why):
                manifest, files = parse_package(data, ACCESSION, CIK, FORM, fetch=fetch)
                member = manifest['members'][0]
                self.assertEqual((files, member['sha256'], member['bytes'], member['proof']['unresolved']), ({}, None, None, why))

    def test_an_unresolved_version_is_replaced_and_a_usable_one_only_by_repair(self):
        data = package([('a.css', b'..x {}\n', 'EX-99.1', '1', None)])
        with tempfile.TemporaryDirectory() as out:
            source, versions = Path(out) / 'in.txt', Path(out) / 'versions'
            source.write_bytes(data)
            first = acquire(ACCESSION, CIK, FORM, versions, package=source, sha256=digest(data))  # no copy: unresolved
            saved = lambda: {path.name: path.read_bytes() for path in first.iterdir()}
            old = saved()
            proven = dict(package=source, sha256=digest(data), fetch=lambda url: b'.x {}\n')
            self.assertEqual(acquire(ACCESSION, CIK, FORM, versions, **proven), first)  # never usable: replaced
            kept, = (Path(out) / 'versions_superseded' / ACCESSION).iterdir()
            self.assertEqual(({path.name: path.read_bytes() for path in kept.iterdir()}, kept.name.split('.')[0]), (old, first.name))
            self.assertEqual(acquisition.read_package(first)[1], {'a.css': b'.x {}\n'})
            usable, other = saved(), dict(proven, fetch=lambda url: b'..x {}\n')  # a copy proving the other reading
            with self.assertRaisesRegex(AcquisitionError, 'Immutable cache differs'):
                acquire(ACCESSION, CIK, FORM, versions, **other)
            self.assertEqual(saved(), usable)
            self.assertEqual(acquire(ACCESSION, CIK, FORM, versions, **other, repair=True), first)
            self.assertEqual(len(list((Path(out) / 'versions_superseded' / ACCESSION).iterdir())), 2)
            self.assertEqual(acquisition.read_package(first)[1], {'a.css': b'..x {}\n'})


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
                copies = json.loads(fixture.with_name('sec_copies.json').read_text())
                fetch = lambda url: gzip.decompress((fixture.with_name(copies[url]['file'])).read_bytes())
                manifest, files = parse_package(raw, **expected['request'], fetch=fetch)
                proven = {m['filename']: m['proof']['form'] for m in manifest['members'] if 'proof' in m}
                self.assertEqual((proven, manifest['decoder']), ({'report.css': 'block', 'Financial_Report.xlsx': 'bytes'}, 'sec-framing-uu-v2')
                                 if accession == ACCESSION else ({}, 'sec-framing-uu-v1'))
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
                    target = acquire(**expected['request'], output=Path(output) / 'saved', fetch=fetch,
                                     package=source, sha256=expected['package']['sha256'])
                    recovered_manifest, recovered_files = acquisition.read_package(target)
                    self.assertEqual(recovered_manifest, manifest)
                    self.assertEqual(recovered_files, files)


if __name__ == '__main__':
    unittest.main()
