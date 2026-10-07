"""Large regression fixtures are pinned evidence, never refreshed by a test run."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests.driver.prepare.support import FixtureStore


class FixtureStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.root = self.folder / 'data'
        (self.root / 'blobs').mkdir(parents=True)
        self.raw = b'Original bytes: 8 3/8%\r\n'
        self.sha = hashlib.sha256(self.raw).hexdigest()
        self.blob = self.root / 'blobs' / (self.sha + '.gz')
        # Independent stdlib writer; do not use the archive under test as oracle.
        self.blob.write_bytes(gzip.compress(self.raw, mtime=0))
        self.manifest = self.folder / 'manifest.json'
        self.spec = {'schema': 'prepare-test-fixtures/1', 'assets': {
            'reading': {'sha256': self.sha, 'bytes': len(self.raw), 'role': 'input',
                        'provenance': {'source': 'independent literal fixture'}}},
            'groups': {'pair': ['reading']}}
        self.save()

    def save(self):
        self.manifest.write_text(json.dumps(self.spec))

    def store(self):
        return FixtureStore(self.manifest, self.root)

    def test_exact_bytes_and_explicit_group_ignore_unlisted_files(self):
        (self.root / 'blobs' / 'unlisted.gz').write_bytes(b'unrelated')
        store = self.store()
        self.assertEqual(store.read('reading'), self.raw)
        members = store.members('pair')
        self.assertEqual(members, ['reading'])
        members.clear()
        self.assertEqual(store.members('pair'), ['reading'])

    def test_distinct_occurrences_can_share_one_blob(self):
        self.spec['assets']['second'] = dict(self.spec['assets']['reading'])
        self.spec['assets']['second']['role'] = 'expected'
        self.spec['groups']['pair'].append('second')
        self.save()
        self.assertEqual([self.store().read(k) for k in self.store().members('pair')],
                         [self.raw, self.raw])

    def test_environment_root_is_required_unless_explicit(self):
        with patch.dict(os.environ, {'PREPARE_TEST_DATA': str(self.root)}):
            self.assertEqual(FixtureStore(self.manifest).read('reading'), self.raw)
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(AssertionError, 'PREPARE_TEST_DATA'):
                FixtureStore(self.manifest)
        self.assertEqual(self.store().read('reading'), self.raw)

    def test_missing_fixture_reports_asset_and_expected_hash(self):
        self.blob.unlink()
        with self.assertRaisesRegex(AssertionError, 'reading.*' + self.sha):
            self.store().read('reading')

    def test_bad_compression_hash_or_length_never_passes(self):
        for data in (b'not gzip', gzip.compress(b'wrong bytes', mtime=0)):
            with self.subTest(data=data):
                self.blob.write_bytes(data)
                with self.assertRaisesRegex(AssertionError, 'reading.*' + self.sha):
                    self.store().read('reading')
        self.blob.write_bytes(gzip.compress(self.raw, mtime=0))
        self.spec['assets']['reading']['bytes'] += 1
        self.save()
        with self.assertRaisesRegex(AssertionError, 'reading.*length'):
            self.store().read('reading')

    def test_loaded_fixture_is_reverified_after_disk_damage(self):
        store = self.store()
        self.assertEqual(store.read('reading'), self.raw)
        self.blob.write_bytes(gzip.compress(b'changed', mtime=0))
        with self.assertRaises(AssertionError):
            store.read('reading')

    def test_unknown_ids_and_groups_fail(self):
        store = self.store()
        for call in (lambda: store.read('unknown'), lambda: store.members('unknown')):
            with self.assertRaisesRegex(AssertionError, 'unknown'):
                call()

    def test_missing_malformed_and_duplicate_manifest_fields_fail(self):
        original = json.dumps(self.spec)
        for field, value in [('sha256', '../outside'), ('sha256', int('1' * 64)), ('bytes', True), ('bytes', -1),
                             ('role', 'approved'), ('provenance', {})]:
            with self.subTest(field=field, value=value):
                self.spec = json.loads(original)
                self.spec['assets']['reading'][field] = value
                self.save()
                with self.assertRaises(AssertionError):
                    self.store()
        self.manifest.write_text('{"schema":"a","schema":"prepare-test-fixtures/1"}')
        with self.assertRaisesRegex(AssertionError, 'duplicate'):
            self.store()
        self.manifest.unlink()
        with self.assertRaisesRegex(AssertionError, 'manifest'):
            self.store()

    def test_invalid_group_members_are_not_silently_dropped(self):
        for members in (['reading', 'reading'], ['unknown'], 'reading', [None]):
            with self.subTest(members=members):
                self.spec['groups']['pair'] = members
                self.save()
                with self.assertRaises(AssertionError):
                    self.store()

    def test_materialize_is_exact_and_never_overwrites(self):
        target = self.folder / 'output' / 'reading.html'
        self.assertEqual(self.store().materialize('reading', target), target)
        self.assertEqual(target.read_bytes(), self.raw)
        with self.assertRaises(FileExistsError):
            self.store().materialize('reading', target)
        self.assertEqual(target.read_bytes(), self.raw)

    def test_materialize_cannot_write_inside_the_fixture_store(self):
        target = self.root / 'new-file'
        with self.assertRaisesRegex(AssertionError, 'read.only'):
            self.store().materialize('reading', target)
        self.assertFalse(target.exists())

    def test_fixture_symlinks_are_not_followed(self):
        other = self.folder / 'other.gz'
        self.blob.rename(other)
        self.blob.symlink_to(other)
        with self.assertRaises(AssertionError):
            self.store().read('reading')


if __name__ == '__main__':
    unittest.main()
