"""acquire.open_package: the document hot path's package reader (DEFERRED_TODO priority 1, Fable 2026-11-02). `read_package` re-derives the
whole manifest on every call, so every document child of a filing decoded every member (uuencoded PDFs included) to use two or three.
`open_package` verifies the stored version whole as before (`_read_cache`: cache layout, package bytes hash, manifest) and returns the members as a
read-only mapping keyed by the verified manifest; a member is framed at its recorded range, decoded by the same decoder, checked against its recorded
name, size and hash, and kept, only when a caller asks for it. `read_package` is unchanged: the callers that want the full re-derivation keep it."""
import gzip
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import driver.prepare.get.acquire as acquisition
from driver.prepare.get.acquire import AcquisitionError, acquire
from tests.driver.prepare.get.test_acquire import ACCESSION, CIK, FORM, digest, package, uu

PDF = bytes(range(256)) * 300  # 76,800 opaque bytes: a large binary member, uuencoded in the package, that no HTML document uses
DOCS = [('main.htm', b'<html><body><p>main 1,234</p><img src="logo.jpg"></body></html>\n', '8-K', '1', 'main'),
        ('logo.jpg', uu(b'\xff\xd8\xff' + bytes(500), 'logo.jpg'), 'GRAPHIC', '2', 'logo'),
        ('big.pdf', uu(PDF, 'big.pdf'), 'PDF', '3', 'never asked for by an HTML document'),
        ('dots.css', b'..x {}\n', 'EX-99.2', '4', None),  # a doubled leading dot: two readings, proof needed (SEC's copy decides)
        ('ex99.htm', b'<html><body><p>exhibit</p></body></html>\n', 'EX-99.1', '5', None)]
SEC_COPY = b'.x {}\n'  # SEC's published copy of dots.css: the un-doubled reading


class OpenPackage(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='open_package_')); self.addCleanup(shutil.rmtree, self.root)
        self.data = package(DOCS); gz = self.root / 'submission.txt.gz'; gz.write_bytes(gzip.compress(self.data))
        self.version = acquire(ACCESSION, CIK, FORM, self.root / 'output', package=gz, sha256=digest(self.data), minimum_free_bytes=0, fetch=lambda url: SEC_COPY)

    def decodes(self, fn):  # (how many member decodes a call made, its result)
        real = acquisition._readings; n = [0]
        def counting(text, name): n[0] += 1; return real(text, name)
        with patch.object(acquisition, '_readings', counting): out = fn()
        return n[0], out

    def tampered(self, edit):  # a fresh copy of the version directory under the same (hash) name, changed by `edit(copy)`
        copy = self.root / f'tampered_{len(list(self.root.glob("tampered_*")))}' / self.version.name; shutil.copytree(self.version, copy); edit(copy); return copy

    def test_read_package_decodes_every_member_and_the_hot_path_only_what_it_is_asked_for(self):
        full, (manifest, files) = self.decodes(lambda: acquisition.read_package(self.version)); self.assertEqual(full, len(DOCS))  # today's cost, per document child
        n, (stored, members) = self.decodes(lambda: acquisition.open_package(self.version)); self.assertEqual(n, 0)
        self.assertEqual(stored, manifest); self.assertEqual(set(members), set(files)); self.assertEqual(len(members), len(files))
        n, raw = self.decodes(lambda: members['main.htm']); self.assertEqual((n, raw), (1, files['main.htm']))
        n, again = self.decodes(lambda: members['main.htm']); self.assertEqual(n, 0); self.assertIs(again, raw)  # kept: no second decode
        n, logo = self.decodes(lambda: members.get('logo.jpg')); self.assertEqual((n, logo), (1, files['logo.jpg']))
        self.assertIn('big.pdf', members); self.assertIsNone(members.get('absent.txt'))
        with self.assertRaises(KeyError): members['absent.txt']

    def test_every_member_through_the_hot_path_is_the_full_readers_bytes_including_the_proved_one(self):
        manifest, files = acquisition.read_package(self.version); _, members = acquisition.open_package(self.version)
        self.assertIn('proof', next(m for m in manifest['members'] if m['filename'] == 'dots.css')); self.assertEqual(files['dots.css'], SEC_COPY)
        self.assertEqual(dict(members), files)
        for m in manifest['members']: self.assertEqual((len(members[m['filename']]), digest(members[m['filename']])), (m['bytes'], m['sha256']), m['filename'])

    def test_an_unresolved_member_is_absent_from_both_readers(self):
        gz = self.root / 'unresolved.gz'; gz.write_bytes(gzip.compress(self.data))
        version = acquire(ACCESSION, CIK, FORM, self.root / 'output_unresolved', package=gz, sha256=digest(self.data), minimum_free_bytes=0)  # no SEC copy: dots.css stays unresolved
        manifest, files = acquisition.read_package(version); stored, members = acquisition.open_package(version)
        self.assertIn('unresolved', next(m for m in manifest['members'] if m['filename'] == 'dots.css')['proof'])
        self.assertNotIn('dots.css', files); self.assertNotIn('dots.css', members); self.assertEqual(dict(members), files)

    def test_a_changed_manifest_entry_fails_closed_on_access(self):
        other = next(m for m in json.loads((self.version / 'manifest.json').read_bytes())['members'] if m['filename'] == 'main.htm')
        for field, value in (('sha256', '0' * 64), ('bytes', 1), ('package_range', other['package_range']), ('filename', 'renamed.htm')):
            with self.subTest(field=field):
                def edit(copy):
                    man = json.loads((copy / 'manifest.json').read_bytes()); next(m for m in man['members'] if m['filename'] == 'ex99.htm')[field] = value
                    (copy / 'manifest.json').write_bytes(json.dumps(man).encode())
                _, members = acquisition.open_package(self.tampered(edit)); name = value if field == 'filename' else 'ex99.htm'
                with self.assertRaises(AcquisitionError): members[name]
                self.assertEqual(members['main.htm'], DOCS[0][1])  # the untouched member still reads

    def test_a_changed_missing_or_corrupt_package_fails_at_open(self):
        def changed(copy): (copy / 'submission.txt.gz').write_bytes(gzip.compress(self.data.replace(b'main 1,234', b'main 1,235')))
        def missing(copy): (copy / 'submission.txt.gz').unlink()
        def corrupt(copy): (copy / 'submission.txt.gz').write_bytes((copy / 'submission.txt.gz').read_bytes()[:-12])
        for name, edit in (('changed', changed), ('missing', missing), ('corrupt', corrupt)):
            with self.subTest(case=name), self.assertRaises(AcquisitionError): acquisition.open_package(self.tampered(edit))


class SourceMembers(unittest.TestCase):
    """screen_grid.Source keeps its snapshot contract for every caller-owned mapping; only the verified package mapping is kept as given."""
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='source_members_')); self.addCleanup(shutil.rmtree, self.root)
        data = package(DOCS); gz = self.root / 'submission.txt.gz'; gz.write_bytes(gzip.compress(data))
        self.version = acquire(ACCESSION, CIK, FORM, self.root / 'output', package=gz, sha256=digest(data), minimum_free_bytes=0, fetch=lambda url: SEC_COPY)

    def test_every_caller_owned_mapping_is_copied_and_a_later_mutation_is_invisible(self):
        import types
        from collections.abc import Mapping
        from driver.prepare.convert import screen_grid as sg
        class ReadOnly(Mapping):  # a read-only view over a dict the caller still owns
            def __init__(self, d): self.d = d
            def __getitem__(self, k): return self.d[k]
            def __iter__(self): return iter(self.d)
            def __len__(self): return len(self.d)
        class CallerMembers(ReadOnly, acquisition.Members):
            pass  # a caller can override the package mapping's methods and own its data
        for kind in ('dict', 'mappingproxy', 'read-only mapping', 'package subclass'):
            with self.subTest(kind=kind):
                backing = {'main.htm': DOCS[0][1]}; given = {'dict': backing, 'mappingproxy': types.MappingProxyType(backing), 'read-only mapping': ReadOnly(backing), 'package subclass': CallerMembers(backing)}[kind]
                src = sg.Source('main.htm', given); backing['main.htm'] = b'changed'; backing['new.htm'] = b'new'
                self.assertEqual(src.members['main.htm'], DOCS[0][1]); self.assertNotIn('new.htm', src.members)
        for factory in (dict, types.MappingProxyType, ReadOnly, CallerMembers):
            with self.subTest(factory=factory.__name__), self.assertRaises(ValueError):
                sg.Source('x', factory({'x': 'not bytes'}))  # whole-value checks stay for every caller-owned mapping

    def test_the_package_mapping_is_kept_as_given_and_decodes_only_on_access(self):
        from driver.prepare.convert import screen_grid as sg
        real = acquisition._readings; n = [0]
        def counting(text, name): n[0] += 1; return real(text, name)
        with patch.object(acquisition, '_readings', counting):
            manifest, members = acquisition.open_package(self.version); src = sg.Source('main.htm', members)
            self.assertEqual(n[0], 0)  # construction (key check only) decodes nothing
            self.assertEqual(src.members['main.htm'], DOCS[0][1]); self.assertEqual(n[0], 1); self.assertNotIn('absent.htm', src.members)
            manifest['members'][0]['sha256'] = '0' * 64; manifest['members'][-1]['sha256'] = '0' * 64  # a caller's later change to the manifest it was handed
            self.assertEqual(src.members['ex99.htm'], DOCS[-1][1])  # the mapping's evidence was copied out at construction


if __name__ == '__main__':
    unittest.main()
