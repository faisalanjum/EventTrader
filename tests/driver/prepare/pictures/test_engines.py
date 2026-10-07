"""The free OCR readers with their real engine code (RapidOCR 3.9.2, OnnxTR 0.9.0): PP-OCR's settings are RapidOCR's own full configuration plus
the weight SHA-256s its loader pins, checked against the actual files after initialisation (its downloader does not check a fresh download);
OnnxTR's settings hold the full SHA-256 of each model file its engines loaded and the providers registered for each session. Downloads,
inference sessions and model loading are replaced: no model runs. Requires the approved preparation environment (rapidocr, onnxtr,
onnxruntime installed). Ported on 2026-10-06 from Codex's r17 weight_fix_tests.py and r20 identity_tests.py (run against the installed
libraries, not a copied source) and prepare_work worker_check_20261006/worker_test.py (the PP-OCR configuration case)."""
import errno
import hashlib
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from onnxtr.models import engine as E
from onnxtr.utils import data as D
from rapidocr import RapidOCR
from rapidocr.inference_engine.base import InferSession
from rapidocr.utils.download_file import DownloadFile
from rapidocr.utils.typings import ModelType, OCRVersion

from driver.prepare.pictures import readers, worker

sha = lambda b: hashlib.sha256(b).hexdigest()


class Base(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory(); self.addCleanup(d.cleanup); self.root = Path(d.name)


class RapidOcrWeights(Base):  # Codex r17: the post-load hash guard on RapidOCR's own configuration and hash utility
    def setUp(self):
        super().setUp()
        self.payloads = {'det': b'expected detector weights', 'rec': b'expected recognizer weights'}
        params = {'Det.ocr_version': OCRVersion.PPOCRV6, 'Det.model_type': ModelType.MEDIUM, 'Rec.ocr_version': OCRVersion.PPOCRV6, 'Rec.model_type': ModelType.MEDIUM}
        self.cfg = RapidOCR._load_config(RapidOCR.__new__(RapidOCR), None, params); self.cfg.Global.model_root_dir = self.root; self.infos = {}
        for t in ('Det', 'Rec'):
            self.infos[str(self.cfg[t].task_type)] = {'model_dir': f'https://invalid.test/{t}.onnx', 'SHA256': sha(self.payloads[t.lower()])}
            (self.root / f'{t}.onnx').write_bytes(self.payloads[t.lower()])
        lookup = patch.object(InferSession, 'get_model_url', side_effect=lambda fi: self.infos[str(fi.task_type)]); lookup.start(); self.addCleanup(lookup.stop)

    def test_matching_actual_bytes_get_the_recorded_hashes(self):
        self.assertEqual(readers._pp_weights(self.cfg), {t: sha(self.payloads[t.lower()]) for t in ('Det', 'Rec')})

    def test_each_mismatch_stops(self):
        for t in ('Det', 'Rec'):
            with self.subTest(model=t):
                p = self.root / f'{t}.onnx'; p.write_bytes(b'different weights')
                with self.assertRaisesRegex(ValueError, 'expected SHA-256'): readers._pp_weights(self.cfg)
                p.write_bytes(self.payloads[t.lower()])

    def test_missing_and_unreadable_weights_stop(self):
        p = self.root / 'Det.onnx'; p.unlink()
        with self.assertRaises(FileNotFoundError): readers._pp_weights(self.cfg)
        p.write_bytes(self.payloads['det'])
        with patch('builtins.open', side_effect=OSError('disk unavailable')), self.assertRaises(OSError): readers._pp_weights(self.cfg)

    def test_same_bytes_new_directory_same_identity(self):
        before = readers._pp_weights(self.cfg); d = self.root / 'moved'; d.mkdir()
        for t in ('Det', 'Rec'): (self.root / f'{t}.onnx').replace(d / f'{t}.onnx')
        self.cfg.Global.model_root_dir = d; self.assertEqual(readers._pp_weights(self.cfg), before)

    def test_a_fresh_wrong_download_is_caught_after_initialisation(self):
        ox = types.ModuleType('onnxtr.models'); ox.EngineConfig = lambda **kw: types.SimpleNamespace(providers=['CPUExecutionProvider'], **kw); ox.ocr_predictor = lambda **kw: object()
        def init(tool, params=None):
            tool.cfg = self.cfg; (self.root / 'Rec.onnx').write_bytes(b'fresh wrong model')    # written during initialisation: checked after it
        readers._free_tools.cache_clear(); self.addCleanup(readers._free_tools.cache_clear)
        with patch.dict(sys.modules, {'onnxtr.models': ox}), patch.object(RapidOCR, '__init__', init), self.assertRaisesRegex(ValueError, 'expected SHA-256'):
            readers.free_readers()


class FreeSettings(Base):  # the settings free_readers() records, from RapidOCR's own configuration and the predictor's loaded files
    def test_settings_name_the_actual_configuration_weights_files_and_providers(self):
        files = {'det': self.root / 'rep_fast_base-1b89ebf9.onnx', 'reco': self.root / 'parseq-00b40714.onnx'}
        for k, p in files.items(): p.write_bytes(k.encode() + b' weights')
        model = lambda p: types.SimpleNamespace(model_path=str(p), runtime=types.SimpleNamespace(get_providers=lambda: ['CPUExecutionProvider']))
        predictor = types.SimpleNamespace(det_predictor=types.SimpleNamespace(model=model(files['det'])), reco_predictor=types.SimpleNamespace(model=model(files['reco'])))
        readers._free_tools.cache_clear(); self.addCleanup(readers._free_tools.cache_clear)
        with patch.object(RapidOCR, '__init__', lambda tool, params=None: setattr(tool, 'cfg', tool._load_config(None, params))), \
                patch.object(DownloadFile, 'check_file_sha256', return_value=True), patch('onnxtr.models.ocr_predictor', return_value=predictor):   # models never loaded
            pp, ox = readers.free_readers()
        c = pp.settings['config']
        self.assertEqual((c['Global']['use_cls'], c['Det']['ocr_version'], c['EngineConfig']['onnxruntime']['use_cuda']), (False, 'PPOCRV6', False))
        self.assertNotIn('model_root_dir', c['Global'])                                                       # a machine location is not identity
        self.assertEqual(pp.settings['weights'], {'Det': '92078b7355007ccfffcd4c8cd441a3afd4538904d06881b29a155e1e679907c2', 'Rec': 'eef444829dbbe18d7fea59a3f6eb75647518d2b3a9568d27c92e42940204894b'})
        self.assertEqual((pp.settings['versions']['rapidocr'], len(pp.settings['code'])), ('3.9.2', 2))
        self.assertEqual(ox.settings['args'], readers.OX); self.assertEqual(ox.settings['versions']['onnxtr'], '0.9.0')
        self.assertEqual(ox.settings['models'], {k: {'sha256': sha(p.read_bytes()), 'providers': ['CPUExecutionProvider']} for k, p in files.items()})
        self.assertNotEqual(pp.settings, ox.settings)


class OnnxtrIdentity(Base):  # Codex r20: the installed OnnxTR Engine and loader, downloads and sessions replaced
    def setUp(self):
        super().setUp(); self.content = {'det': b'detector bytes', 'reco': b'recognizer bytes'}; self.loaded = []
        for role, content in self.content.items(): (self.root / (role + '.onnx')).write_bytes(content)

    def predictor(self, root=None, providers=('CPUExecutionProvider',)):
        root = root or self.root
        def session(path, providers, sess_options):
            self.loaded.append((str(path), Path(path).read_bytes()))
            return types.SimpleNamespace(get_providers=lambda: list(providers), get_inputs=lambda: [types.SimpleNamespace(shape=[1, 3, 32, 32], name='input')],
                                         get_outputs=lambda: [types.SimpleNamespace(name='output')])
        cfg = E.EngineConfig(providers=list(providers))
        with patch.object(E, 'InferenceSession', side_effect=session):
            det, reco = E.Engine(str(root / 'det.onnx'), cfg), E.Engine(str(root / 'reco.onnx'), cfg)
        return types.SimpleNamespace(det_predictor=types.SimpleNamespace(model=det), reco_predictor=types.SimpleNamespace(model=reco))

    def test_engine_paths_match_session_inputs_and_full_hashes_are_recorded(self):
        self.assertEqual(readers._ox_models(self.predictor()), {k: {'sha256': sha(v), 'providers': ['CPUExecutionProvider']} for k, v in self.content.items()})
        self.assertEqual(self.loaded, [(str(self.root / (k + '.onnx')), v) for k, v in self.content.items()])

    def test_each_selected_model_change_changes_its_identity_only(self):
        before = readers._ox_models(self.predictor())
        for role in self.content:
            with self.subTest(role=role):
                path = self.root / (role + '.onnx'); path.write_bytes(b'changed selected model'); after = readers._ox_models(self.predictor())
                other = 'reco' if role == 'det' else 'det'
                self.assertNotEqual(before[role], after[role]); self.assertEqual(before[other], after[other]); path.write_bytes(self.content[role])

    def test_location_and_unselected_files_do_not_change_identity(self):
        before = readers._ox_models(self.predictor()); moved = self.root / 'moved'; moved.mkdir()
        for role, content in self.content.items(): (moved / (role + '.onnx')).write_bytes(content)
        (moved / 'unused.onnx').write_bytes(b'not loaded'); self.assertEqual(before, readers._ox_models(self.predictor(moved)))
        (moved / 'unused.onnx').write_bytes(b'changed, still unused'); self.assertEqual(before, readers._ox_models(self.predictor(moved)))

    def test_registered_session_providers_change_identity(self):
        cpu = readers._ox_models(self.predictor())
        for providers in (('CUDAExecutionProvider', 'CPUExecutionProvider'), ('CoreMLExecutionProvider', 'CPUExecutionProvider')):
            with self.subTest(providers=providers):
                got = readers._ox_models(self.predictor(providers=providers))
                for role in self.content:
                    self.assertEqual(got[role]['sha256'], cpu[role]['sha256']); self.assertEqual(got[role]['providers'], list(providers)); self.assertNotEqual(got[role], cpu[role])

    def test_missing_or_unreadable_model_stops_before_reading_or_publication(self):
        for role in self.content:
            for kind in ('missing', 'io_error'):
                with self.subTest(role=role, kind=kind):
                    predictor = self.predictor(); target = self.root / (role + '.onnx')
                    if kind == 'missing': target.unlink()
                    real_open, called = open, []
                    def checked_open(path, *a, **k):
                        if kind == 'io_error' and Path(path) == target: raise OSError(errno.EIO, 'model read failure')
                        return real_open(path, *a, **k)
                    factory = lambda: types.SimpleNamespace(settings=readers._ox_models(predictor), read=lambda data: called.append(data), status=lambda value: 'complete')
                    output = self.root / (role + kind)
                    with patch('builtins.open', side_effect=checked_open), self.assertRaises(OSError): worker.run(output, [('image', b'image')], factory)
                    self.assertEqual((called, list(output.glob('*.json'))), ([], [])); target.write_bytes(self.content[role])

    def test_record_reuse_changes_when_model_or_provider_changes(self):
        calls, state = [], {'providers': ('CPUExecutionProvider',)}
        def factory():
            def read(data): calls.append(data); return ['text', {'generation_tokens': 1}]
            return types.SimpleNamespace(settings=readers._ox_models(self.predictor(providers=state['providers'])), read=read, status=readers._chandra_status)
        folder = self.root / 'results'
        worker.run(folder, [('a', b'image')], factory); worker.run(folder, [('b', b'image')], factory); self.assertEqual(len(calls), 1)
        (self.root / 'reco.onnx').write_bytes(b'new recognizer'); worker.run(folder, [('a', b'image')], factory); self.assertEqual(len(calls), 2)
        state['providers'] = ('CoreMLExecutionProvider', 'CPUExecutionProvider'); worker.run(folder, [('a', b'image')], factory)
        self.assertEqual((len(calls), len(list(folder.glob('*.json')))), (3, 3))

    def test_loader_checks_fresh_cached_and_damaged_files(self):  # only the 8-hex SHA-256 prefix in the file name
        good, downloads = b'published model bytes', []; url = 'https://invalid.test/model-' + sha(good)[:8] + '.onnx'
        def download(url, path, chunk_size=1024): downloads.append(url); Path(path).write_bytes(good)
        with patch.object(D, '_urlretrieve', side_effect=download):
            path = D.download_from_url(url, cache_dir=str(self.root / 'cache')); self.assertEqual(path.read_bytes(), good)
            D.download_from_url(url, cache_dir=str(self.root / 'cache')); self.assertEqual(len(downloads), 1)
            path.write_bytes(b'bad cached data'); D.download_from_url(url, cache_dir=str(self.root / 'cache'))
            self.assertEqual((len(downloads), path.read_bytes()), (2, good))
        path.unlink()
        with patch.object(D, '_urlretrieve', side_effect=lambda url, p, chunk_size=1024: Path(p).write_bytes(b'bad download')), self.assertRaisesRegex(ValueError, 'corrupted download'):
            D.download_from_url(url, cache_dir=str(self.root / 'cache'))
        self.assertFalse(path.exists())

    def test_default_provider_selection(self):
        for available, device, expected in ((['CPUExecutionProvider'], 'CPU', ['CPUExecutionProvider']),
                                            (['CUDAExecutionProvider', 'CPUExecutionProvider'], 'GPU', ['CUDAExecutionProvider', 'CPUExecutionProvider']),
                                            (['CoreMLExecutionProvider', 'CPUExecutionProvider'], 'CPU', ['CoreMLExecutionProvider', 'CPUExecutionProvider'])):
            with self.subTest(device=device, available=available), patch.object(E, 'get_available_providers', return_value=available), patch.object(E, 'get_device', return_value=device):
                self.assertEqual([name for name, _ in E.EngineConfig().providers], expected)


if __name__ == '__main__':
    unittest.main()
