"""Named records keep their exact bytes, exclusive publication and durable names."""
import gzip
import os
from pathlib import Path
import resource
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from driver.prepare.get import archive


class Records(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        self.root = Path(t.name)

    def test_only_route_and_readback_are_compressed_and_exact(self):
        data = b'{"literal":"caf\xc3\xa9", "unknown": null}\r\n'
        for name in ('ROUTE.json', 'R.json', 'COMPLETE.json', 'RESULT.json', 'ROUTE_BEFORE_INPUTS.json'):
            with self.subTest(name=name):
                path = self.root / name
                archive.write_record(path, data)
                stored = path.with_name(name + '.gz') if name in ('ROUTE.json', 'R.json') else path
                self.assertEqual(archive.record_path(path), stored)
                self.assertEqual(archive.read_record(path), data)
                self.assertEqual(gzip.decompress(stored.read_bytes()) if stored != path else stored.read_bytes(), data)
                if stored != path: self.assertFalse(path.exists())

    def test_legacy_plain_is_read_but_never_overwritten_or_duplicated(self):
        for name in ('ROUTE.json', 'R.json'):
            path = self.root / name; path.write_bytes(b'legacy bytes')
            self.assertEqual(archive.read_record(path), b'legacy bytes')
            with self.assertRaises(FileExistsError): archive.write_record(path, b'legacy bytes')
            self.assertFalse(path.with_name(name + '.gz').exists())

    def test_missing_corrupt_truncated_and_dual_names_never_fall_back(self):
        path = self.root / 'ROUTE.json'; stored = path.with_name(path.name + '.gz')
        with self.assertRaises(FileNotFoundError): archive.read_record(path)
        for data in (b'bad', gzip.compress(b'positive')[:-4]):
            stored.write_bytes(data)
            with self.assertRaises(ValueError): archive.read_record(path)
        stored.write_bytes(gzip.compress(b'positive'))
        self.assertEqual(archive.read_record(path), b'positive')
        path.write_bytes(b'stale')
        with self.assertRaises(ValueError): archive.read_record(path)
        with self.assertRaises(ValueError): archive.write_record(path, b'new')
        self.assertEqual(path.read_bytes(), b'stale')

    def test_immutable_repeat_refuses_even_identical_bytes(self):
        path = self.root / 'R.json'; archive.write_record(path, b'exact')
        before = archive.record_path(path).read_bytes()
        with self.assertRaises(FileExistsError): archive.write_record(path, b'exact')
        self.assertEqual(archive.record_path(path).read_bytes(), before)

    def test_mutable_metadata_replace_is_atomic_and_flush_failure_preserves_old(self):
        path = self.root / 'RESULT.json'; archive.write_record(path, b'old', replace=True)
        with patch.object(archive.os, 'fsync', side_effect=OSError('file flush')):
            with self.assertRaises(OSError): archive.write_record(path, b'new', replace=True)
        self.assertEqual(path.read_bytes(), b'old')
        with patch.object(archive.os, 'replace', side_effect=OSError('replace')):
            with self.assertRaises(OSError): archive.write_record(path, b'new', replace=True)
        self.assertEqual(path.read_bytes(), b'old')
        archive.write_record(path, b'new', replace=True)
        self.assertEqual(path.read_bytes(), b'new')
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['RESULT.json'])

    def test_decoded_content_honors_inherited_file_limit_before_compression(self):
        path = self.root / 'R.json'
        with patch.object(resource, 'getrlimit', return_value=(100, 100)), patch.object(archive, '_compress', wraps=archive._compress) as compress:
            with self.assertRaises(OSError): archive.write_record(path, b'x' * 101)
            compress.assert_not_called()
            archive.write_record(path, b'x' * 100)
        self.assertEqual(archive.read_record(path), b'x' * 100)

    def test_file_flush_precedes_publication_and_directory_flush_follows(self):
        events = []; sync, link = os.fsync, os.link
        def fsync(fd):
            events.append('directory' if stat.S_ISDIR(os.fstat(fd).st_mode) else 'file'); sync(fd)
        def publish(a, b): events.append('publish'); link(a, b)
        with patch.object(archive.os, 'fsync', fsync), patch.object(archive.os, 'link', publish):
            archive.write_record(self.root / 'R.json', b'positive')
        self.assertEqual(events, ['file', 'publish', 'directory'])

    def test_publication_and_directory_flush_failures_are_never_success(self):
        path = self.root / 'R.json'
        with patch.object(archive.os, 'link', side_effect=OSError('publication')):
            with self.assertRaises(OSError): archive.write_record(path, b'positive')
        self.assertEqual(list(self.root.iterdir()), [])
        with patch.object(archive, '_sync_dir', side_effect=OSError('directory flush')):
            with self.assertRaises(OSError): archive.write_record(path, b'positive')
        self.assertEqual(archive.read_record(path), b'positive')

    def test_exclusive_directory_creation_flushes_parent_and_refuses_reuse(self):
        path = self.root / 'new'
        with patch.object(archive, '_sync_dir', wraps=archive._sync_dir) as sync:
            archive.make_dir(path)
        sync.assert_called_once_with(path.parent)
        with self.assertRaises(FileExistsError): archive.make_dir(path)

    def test_explicit_physical_names_mutable_compressed_and_nonbytes_refuse(self):
        for name in ('ROUTE.json.gz', 'R.json.gz'):
            with self.subTest(name=name), self.assertRaises(ValueError): archive.read_record(self.root / name)
        with self.assertRaises(ValueError): archive.write_record(self.root / 'R.json', b'bytes', replace=True)
        with self.assertRaises(TypeError): archive.write_record(self.root / 'R.json', 'text')
        archive.write_record(self.root / 'claim', b'', mode=0o444)
        self.assertEqual(stat.S_IMODE((self.root / 'claim').stat().st_mode), 0o444)

    def test_named_publication_requires_its_owners_existing_parent(self):
        from driver.prepare import job
        for name in ('ROUTE.json', 'R.json', 'RESULT.json'):
            path = self.root / name / name
            with self.subTest(name=name), self.assertRaises(FileNotFoundError): archive.write_record(path, b'bytes')
            self.assertFalse(path.parent.exists())
        store = self.root / 'qualification_store'
        with self.assertRaises(FileNotFoundError): job.claim_version(store, 'a' * 64)
        self.assertFalse(store.exists())
        store.mkdir()
        self.assertTrue(job.claim_version(store, 'a' * 64))
        self.assertFalse(job.claim_version(store, 'a' * 64))

    def test_actual_native_file_limit_counts_decoded_bytes(self):
        repo = Path(__file__).resolve().parents[4]
        code = '''import errno, resource, sys
sys.path.insert(0, sys.argv[1])
from driver.prepare.get import archive
resource.setrlimit(resource.RLIMIT_FSIZE, (1024, 1024))
try: archive.write_record(sys.argv[2], b'x' * int(sys.argv[3]))
except OSError as error:
    if error.errno == errno.EFBIG: sys.exit(7)
    raise
'''
        for size, expected in ((1024, 0), (1025, 7)):
            target = self.root / str(size); target.mkdir(); path = target / 'R.json'
            done = subprocess.run([sys.executable, '-I', '-S', '-B', '-c', code, str(repo), str(path), str(size)], capture_output=True, timeout=10)
            self.assertEqual(done.returncode, expected, done.stderr.decode())
            if expected == 0: self.assertEqual(archive.read_record(path), b'x' * size)
            else: self.assertFalse(path.with_name('R.json.gz').exists())


if __name__ == '__main__': unittest.main()
