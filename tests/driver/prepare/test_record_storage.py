"""The actual producer/reconstructor and mutable job result use durable record I/O."""
import copy
import gzip
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from driver.prepare import document, job, reconstruct
from driver.prepare.convert import xml_fields
from driver.prepare.get import archive


class PublicRecords(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        raw = '<r><value>caf\u00e9</value></r>'.encode()
        self.row = dict(file_id='record.xml', source_sha256=hashlib.sha256(raw).hexdigest())
        self.route = xml_fields.convert(raw, self.row['file_id'], self.row['source_sha256'])
        self.route['seconds'] = 0

    def test_producer_and_reconstruction_roundtrip_exact_serialized_bytes(self):
        document.finish(self.root, self.row, self.route, {}, archive, document.save)
        expected = (json.dumps(self.route, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()
        self.assertFalse((self.root / 'ROUTE.json').exists())
        self.assertEqual(gzip.decompress((self.root / 'ROUTE.json.gz').read_bytes()), expected)
        self.assertEqual(json.loads((self.root / 'COMPLETE.json').read_bytes())['route_sha256'], hashlib.sha256(expected).hexdigest())
        out = self.root / 'R.json'; reconstruct.main([str(self.root), str(out)])
        self.assertFalse(out.exists())
        result = reconstruct.verify(str(self.root), str(out))
        self.assertEqual({k: result[k] for k in ('custody', 'preserved', 'annotations')}, dict(custody=[], preserved=[], annotations=[]))

    def test_job_result_flushes_file_and_directory_and_keeps_exact_serialization(self):
        events = []; sync = os.fsync
        def fsync(fd):
            events.append('directory' if stat.S_ISDIR(os.fstat(fd).st_mode) else 'file'); sync(fd)
        value = {'rows': [{'outcome': 'incomplete'}], 'unicode': '\u00e9'}
        with patch.object(os, 'fsync', fsync): job.save(self.root / 'RESULT.json', value)
        self.assertEqual(events, ['file', 'directory'])
        self.assertEqual((self.root / 'RESULT.json').read_bytes(), json.dumps(value, indent=1).encode())

    def test_failed_route_publication_never_creates_complete(self):
        with patch.object(os, 'fsync', side_effect=OSError('controlled flush failure')):
            with self.assertRaises(OSError): document.finish(self.root, self.row, self.route, {}, archive, document.save)
        self.assertFalse((self.root / 'COMPLETE.json').exists())

    def test_actual_job_checks_main_state_and_child_before_retiring_snapshots(self):
        repo = Path(__file__).resolve().parents[3]
        generator = self.root / 'copy_saved.py'
        generator.write_text("import json, shutil, sys\nfrom pathlib import Path\np=json.loads(Path(sys.argv[1]).read_bytes())\nr=p['source_commands'][int(sys.argv[3])]\nshutil.copytree(r['fixture'],sys.argv[4])\n")
        manifest = self.root / 'MANIFEST.json'
        manifest.write_text(json.dumps({'files': {str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (repo / 'driver').rglob('*') if p.is_file() and '__pycache__' not in p.parts}}))
        for partial in (False, True):
            with self.subTest(partial=partial):
                template = self.root / ('fixture_' + str(partial)); template.mkdir()
                child = template / 'source_reading'; child.mkdir()
                state = template / 'states/activated@1'; state.mkdir(parents=True)
                child_route = copy.deepcopy(self.route)
                if partial: child_route.update(status='PARTIAL', error='independent uncertainty control')
                document.finish(child, self.row, child_route, {}, archive, document.save)
                document.finish(state, self.row, self.route, {}, archive, document.save)
                parent = copy.deepcopy(self.route)
                parent['facts'] = {'source_reading': {'made': True}}
                parent['source_links'] = [{'tag': {'byte_start': 1}, 'activations': [{'state': 'activated@1', 'route_sha256': hashlib.sha256(archive.read_record(state / 'ROUTE.json')).hexdigest()}]}]
                document.finish(template, self.row, parent, {}, archive, document.save)
                temporary = b'{"temporary": true}\n'
                for folder in (template, state, child):
                    for name in ('ROUTE_BEFORE_INPUTS.json', 'ROUTE_AFTER_INPUTS.json'): (folder / name).write_bytes(temporary)
                plan = self.root / ('PLAN_' + str(partial) + '.json')
                plan.write_text(json.dumps({'runtime_root': str(repo), 'runtime_manifest': {'path': str(manifest), 'sha256': hashlib.sha256(manifest.read_bytes()).hexdigest()}, 'source_commands': [dict(self.row, fixture=str(template))]}))
                out = self.root / ('job_' + str(partial))
                done = subprocess.run([sys.executable, '-I', '-S', '-B', str(repo / 'driver/prepare/job.py'), str(plan), hashlib.sha256(plan.read_bytes()).hexdigest(), str(out), str(generator), '60'], env={'PATH': '/usr/bin:/bin', 'HOME': str(self.root)}, capture_output=True, timeout=60)
                self.assertEqual(done.returncode, 1 if partial else 0, done.stderr.decode())
                row = json.loads((out / 'RESULT.json').read_bytes())['rows'][0]
                self.assertEqual(row['outcome'], 'incomplete' if partial else 'verified_saved_output')
                readings = [(out / 'attempt_0', out / 'logs_0', row), (out / 'attempt_0/states/activated@1', out / 'logs_0/state_activated_1', row['states']['activated@1']), (out / 'attempt_0/source_reading', out / 'logs_0/source_reading', row['source_reading'])]
                for folder, logs, fields in readings:
                    self.assertEqual(fields['R_bytes'], len(gzip.decompress((logs / 'R.json.gz').read_bytes())))
                    for name in ('ROUTE_BEFORE_INPUTS.json', 'ROUTE_AFTER_INPUTS.json'): self.assertEqual((folder / name).exists(), partial)
                self.assertEqual(row['attempt_bytes'] - job.size(out / 'attempt_0'), 0 if partial else len(temporary) * 6)


if __name__ == '__main__': unittest.main()
