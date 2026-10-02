"""Opaque provider bytes survive storage before any parser or cleaner runs."""
import gzip
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from driver.prepare.archive import load_blob, store_blob


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'blobs'

    def test_exact_bytes_versions_and_deterministic_gzip(self):
        payloads = [b'', bytes(range(256)), b' {"body":"<table>  x </table>", "unknown":true}\r\n',
                    b' {"body":"revised", "unknown":true}\r\n', b'\xffnot JSON\x00']
        for data in payloads:
            with self.subTest(data=data[:20]):
                sha = store_blob(self.root, data)
                self.assertEqual(sha, hashlib.sha256(data).hexdigest())
                self.assertEqual(load_blob(self.root, sha), data)
                compressed = (self.root / (sha + '.gz')).read_bytes()
                self.assertEqual(gzip.decompress(compressed), data)
                other = Path(self.temp.name) / 'separate'
                self.assertEqual(store_blob(other, data), sha)
                self.assertEqual((other / (sha + '.gz')).read_bytes(), compressed)
                self.assertEqual(store_blob(self.root, data), sha)
                self.assertEqual((self.root / (sha + '.gz')).read_bytes(), compressed)
        self.assertEqual(len(list(self.root.iterdir())), len(payloads))

    def test_corrupt_or_misnamed_blob_fails_and_is_not_repaired(self):
        data = b'original'
        sha = store_blob(self.root, data)
        path = self.root / (sha + '.gz')
        valid = path.read_bytes()
        for broken in (b'not gzip', valid[:-4], gzip.compress(b'different bytes')):
            with self.subTest(broken=broken):
                path.write_bytes(broken)
                with self.assertRaises((ValueError, OSError)):
                    load_blob(self.root, sha)
                with self.assertRaises((ValueError, OSError)):
                    store_blob(self.root, data)
                self.assertEqual(path.read_bytes(), broken)
        path.write_bytes(valid)
        self.assertEqual(load_blob(self.root, sha), data)

    def test_invalid_types_hashes_and_symlink_paths_fail(self):
        for value in ('text', {'parsed': 'object'}, bytearray(b'bytes'), None):
            with self.subTest(value=value), self.assertRaises(TypeError):
                store_blob(self.root, value)
        for sha in ('../escape', 'a' * 63, 'z' * 64, None):
            with self.subTest(sha=sha), self.assertRaises(ValueError):
                load_blob(self.root, sha)
        self.assertFalse(self.root.exists())
        outside = Path(self.temp.name) / 'outside'
        outside.mkdir()
        self.root.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            store_blob(self.root / 'new', b'original')
        self.assertEqual(list(outside.iterdir()), [])
        self.root.unlink()
        sha = store_blob(self.root, b'original')
        path = self.root / (sha + '.gz')
        path.unlink()
        path.symlink_to(outside / 'missing')
        with self.assertRaises(ValueError):
            store_blob(self.root, b'original')

    def test_failed_publication_has_no_partial_blob(self):
        with patch('driver.prepare.archive.os.link', side_effect=OSError('interrupted')):
            with self.assertRaises(OSError):
                store_blob(self.root, b'original')
        self.assertEqual(list(self.root.iterdir()), [])
        sha = store_blob(self.root, b'original')
        self.assertEqual(load_blob(self.root, sha), b'original')

    def test_real_package_remains_exact_without_parsing(self):
        raw = gzip.decompress((Path(__file__).parent / 'fixtures/0001004434-23-000015.txt.gz').read_bytes())
        self.assertEqual(hashlib.sha256(raw).hexdigest(), '7f6812c06b8455d9c33611c9acca9320f1982fd7e3fc49572e3771a80cf935bb')
        self.assertEqual(load_blob(self.root, store_blob(self.root, raw)), raw)


if __name__ == '__main__':
    unittest.main()
