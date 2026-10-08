"""The readers (pictures/readers.py) without their engines: Chandra's settings name its actual model files, wheel (prompt and sizing), limits,
code and versions; a missing model folder stops; the free-OCR inner guard lets storage failures escape and keeps a good tool's reading when
the other fails; code identity ignores comments and docstrings; the model-tree fingerprint frames file boundaries and ignores location. Ported
on 2026-10-06 from prepare_work worker_check_20261006/worker_test.py and Codex's r16, r17 and r20 tests. Engine-dependent cases (real RapidOCR
and OnnxTR code) are in test_engines.py."""
import errno
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from driver.prepare.get.acquire import StorageError
from driver.prepare.pictures import readers

ROOT = str(Path(__file__).resolve().parents[4])
sha = lambda b: hashlib.sha256(b).hexdigest()
FAKE_MLX = {'mlx_vlm/__init__.py': "def load(m): return 'model', 'processor'\ndef generate(*a, **k): raise SystemExit('no generation in this test')\n",
            'mlx_vlm/prompt_utils.py': 'def apply_chat_template(*a, **k): return ""\n', 'mlx_vlm/utils.py': 'def load_config(m): return {}\n', 'mlx/__init__.py': '',
            'mlx_vlm-0.7.4.dist-info/METADATA': 'Metadata-Version: 2.1\nName: mlx-vlm\nVersion: 0.7.4\n', 'mlx-0.32.3.dist-info/METADATA': 'Metadata-Version: 2.1\nName: mlx\nVersion: 0.32.3\n'}


class Base(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory(); self.addCleanup(d.cleanup); self.tmp = Path(d.name)


class ChandraSettings(Base):
    def setUp(self):
        super().setUp(); self.fake = self.tmp / 'fakelibs'
        for path, text in FAKE_MLX.items(): (self.fake / path).parent.mkdir(parents=True, exist_ok=True); (self.fake / path).write_text(text)
        self.model = self.tmp / 'model'; self.model.mkdir(); (self.model / 'config.json').write_text('{}'); (self.model / 'weights.safetensors').write_bytes(b'w1')

    def wheel(self, prompt):  # built once per test: a zip stamps its time
        p = self.tmp / f'chandra_ocr-0.2.0-{sha(prompt.encode())[:6]}.whl'
        with zipfile.ZipFile(p, 'w') as z:
            z.writestr('chandra/model/util.py', 'def scale_to_fit(im): return im\n'); z.writestr('chandra/prompts.py', f'PROMPT_MAPPING = {{"ocr_layout": {prompt!r}}}\n')
            z.writestr('chandra/settings.py', 'MIN_IMAGE_DIM: int = 1536\n')
        return str(p)

    def settings(self, model, wheel):  # chandra() in a fresh process with the fake MLX libraries first on its path
        code = ("import json, sys; sys.path.insert(0, %r); sys.path.insert(1, %r); from driver.prepare.pictures import readers as r\n"
                "print(json.dumps(r.chandra(sys.argv[1], sys.argv[2]).settings))") % (str(self.fake), ROOT)
        return json.loads(subprocess.run([sys.executable, '-c', code, str(model), wheel], capture_output=True, text=True, check=True).stdout)

    def test_settings_name_the_actual_setup(self):
        w1, w2 = self.wheel('P1'), self.wheel('P2'); s1, s2 = self.settings(self.model, w1), self.settings(self.model, w2)
        self.assertEqual(set(s1), {'reader', 'model_files', 'wheel', 'max_tokens', 'temperature', 'code', 'versions'})
        self.assertEqual((s1['max_tokens'], s1['temperature'], len(s1['code'])), (12384, 0.0, 2))
        self.assertEqual({k: v for k, v in s1['versions'].items() if k != 'pillow'}, {'mlx-vlm': '0.7.4', 'mlx': '0.32.3'})
        self.assertNotEqual(s1['wheel'], s2['wheel']); self.assertEqual(s1['model_files'], s2['model_files'])          # a changed prompt
        (self.model / 'weights.safetensors').write_bytes(b'w2'); s3 = self.settings(self.model, w1)
        self.assertNotEqual(s1['model_files'], s3['model_files']); self.assertEqual(s1['wheel'], s3['wheel'])          # changed weights

    def test_a_model_that_is_not_a_local_folder_stops(self):
        with self.assertRaises(subprocess.CalledProcessError) as e: self.settings(self.tmp / 'no-such-model', self.wheel('P1'))
        self.assertIn('FileNotFoundError', e.exception.stderr)


class FreeOcrGuard(Base):  # Codex r16 C1 / r17: storage failures escape the inner guard; a genuine inference error keeps the good peer
    def setUp(self):
        super().setUp(); self.picture = self.tmp / 'picture.png'; Image.new('RGB', (20, 10)).save(self.picture)

    def test_storage_failures_from_either_tool_escape(self):
        for name in ('_pp_boxes', '_ox_boxes'):
            for error in (StorageError('flush failed'), OSError(errno.EIO, 'I/O error'), OSError(errno.ENOSPC, 'full'), MemoryError('injected')):
                with self.subTest(tool=name, error=type(error).__name__), patch.object(readers, '_free_tools', return_value=(None, None, {})), \
                        patch.object(readers, '_pp_boxes', return_value=[]), patch.object(readers, '_ox_boxes', return_value=[]), patch.object(readers, name, side_effect=error):
                    with self.assertRaises(type(error)): readers.free_ocr(self.picture)

    def test_a_genuine_inference_error_keeps_the_good_peer(self):
        good = [{'t': 'Revenue', 'box': [0, 0, 8, 3]}]
        with patch.object(readers, '_free_tools', return_value=(None, None, {})), patch.object(readers, '_pp_boxes', side_effect=RuntimeError('inference failed')), \
                patch.object(readers, '_ox_boxes', return_value=good):
            got = readers.free_ocr(self.picture)
        self.assertEqual((got['ox'], got['pp']), (good, [])); self.assertIn('inference failed', got['pp_error'])

    def test_undecodable_bytes_are_a_picture_error_not_a_disk_error(self):
        with self.assertRaises(readers.PictureError): readers._image(b'not a picture')
        self.assertNotIsInstance(readers.PictureError('x'), OSError)
        b = io.BytesIO(); Image.new('RGB', (7, 3)).save(b, 'PNG'); self.assertEqual(readers._image(b.getvalue()).size, (7, 3))

    def test_a_memory_failure_while_decoding_stops_instead_of_blaming_the_picture(self):   # Codex/root MEMORY_BOUNDARY_BEFORE
        b = io.BytesIO(); Image.new('RGB', (7, 3)).save(b, 'PNG')
        with patch.object(Image.Image, 'load', side_effect=MemoryError('injected')):
            with self.assertRaises(MemoryError): readers._image(b.getvalue())
        with patch.object(Image.Image, 'load', side_effect=Image.DecompressionBombError('too many pixels')):   # the picture's own size: its error
            with self.assertRaises(readers.PictureError): readers._image(b.getvalue())


class SourceRenderedImages(unittest.TestCase):
    @staticmethod
    def encoded(im, fmt='PNG', **kwargs):
        stream = io.BytesIO(); im.save(stream, fmt, **kwargs); return stream.getvalue()

    def test_nonopaque_bytes_cannot_silently_discard_their_background(self):
        rgba = Image.new('RGBA', (2, 1)); rgba.putdata([(0, 0, 0, 0), (0, 0, 0, 255)])
        la = Image.new('LA', (2, 1)); la.putdata([(100, 0), (200, 255)])
        palette = Image.new('P', (2, 1)); palette.putpalette([0, 0, 0, 0, 0, 255] + [0] * 762); palette.putdata([0, 1])
        rgb = Image.new('RGB', (2, 1)); rgb.putdata([(1, 2, 3), (4, 5, 6)])
        gray = Image.new('L', (2, 1)); gray.putdata([64, 128])
        cases = {
            'RGBA': self.encoded(rgba), 'LA': self.encoded(la),
            'palette key': self.encoded(palette, transparency=0),
            'palette partial': self.encoded(palette, transparency=bytes([128, 255])),
            'RGB key': self.encoded(rgb, transparency=(1, 2, 3)),
            'gray key': self.encoded(gray, transparency=64),
            'GIF key': self.encoded(palette, fmt='GIF', transparency=0, optimize=False),
        }
        for name, data in cases.items():
            with self.subTest(name=name), self.assertRaisesRegex(readers.PictureError, 'source'):
                readers._image(data)

    def test_opaque_pixels_stay_identical_including_unused_transparency(self):
        rgb = Image.new('RGB', (2, 1)); rgb.putdata([(1, 2, 3), (4, 5, 6)])
        rgba = Image.new('RGBA', (2, 1)); rgba.putdata([(1, 2, 3, 255), (4, 5, 6, 255)])
        palette = Image.new('P', (2, 1)); palette.putpalette([0, 0, 0, 1, 2, 3, 4, 5, 6] + [0] * 759); palette.putdata([1, 2])
        cases = {
            'RGB': self.encoded(rgb), 'RGBA opaque': self.encoded(rgba),
            'unused RGB key': self.encoded(rgb, transparency=(99, 98, 97)),
            'unused palette key': self.encoded(palette, transparency=0),
            'unused GIF key': self.encoded(palette, fmt='GIF', transparency=0, optimize=False),
        }
        for name, data in cases.items():
            with self.subTest(name=name):
                got = readers._image(data)
                self.assertEqual((got.mode, got.size, list(got.getdata())), ('RGB', (2, 1), [(1, 2, 3), (4, 5, 6)]))

    def test_explicitly_prepared_pixels_keep_the_chosen_source_background(self):
        foreground = Image.new('RGBA', (2, 1)); foreground.putdata([(0, 0, 0, 0), (0, 0, 0, 255)])
        for background in ((255, 255, 255), (24, 48, 96)):
            with self.subTest(background=background):
                prepared = Image.alpha_composite(Image.new('RGBA', (2, 1), background + (255,)), foreground).convert('RGB')
                self.assertEqual(list(readers._image(self.encoded(prepared)).getdata()), [background, (0, 0, 0)])


class Fingerprints(Base):
    def test_code_identity_ignores_comments_and_docstrings_not_code(self):
        def cid(src, n):
            p = self.tmp / f'codeid_{n}.py'; p.write_text(src); spec = importlib.util.spec_from_file_location(f'codeid_{n}', p)
            m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return readers._code_id(m.g)
        c1 = cid('def g(x):  # a comment\n    """Doc."""\n    return x + 1\n', 1); c2 = cid('def g(x):\n    return x + 1  # another comment\n', 2); c3 = cid('def g(x):\n    return x + 2\n', 3)
        self.assertEqual(c1, c2); self.assertNotEqual(c1, c3)

    def test_tree_hash_frames_file_boundaries_and_ignores_location(self):  # Codex r16 C5: the reproduced collision
        a, b, c = self.tmp / 'a', self.tmp / 'b', self.tmp / 'c'
        for d, files in ((a, {'a': b'x', 'b': b'y'}), (b, {'a': b'xb\x00y'}), (c, {'a': b'x', 'b': b'y'})):
            d.mkdir()
            for k, v in files.items(): (d / k).write_bytes(v)
        self.assertNotEqual(readers._tree_sha256(a), readers._tree_sha256(b)); self.assertEqual(readers._tree_sha256(a), readers._tree_sha256(c))
        with patch('os.walk', side_effect=lambda *x, **k: (_ for _ in ()).throw(PermissionError('listing'))), self.assertRaises(PermissionError):
            readers._tree_sha256(a)

    def test_streamed_hash_and_tree_encoding_keep_their_format(self):  # Codex r20
        payload = bytes(range(256)) * 9000; (self.tmp / 'large').write_bytes(payload)
        self.assertEqual(readers._file_sha256(self.tmp / 'large'), sha(payload))
        entries = [[p.name, sha(p.read_bytes())] for p in sorted(self.tmp.iterdir()) if p.is_file()]
        self.assertEqual(readers._tree_sha256(self.tmp), sha(json.dumps(entries).encode()))
        self.assertEqual(readers._tree_sha256(self.tmp / 'large'), sha(json.dumps([['.', sha(payload)]]).encode()))


if __name__ == '__main__':
    unittest.main()
