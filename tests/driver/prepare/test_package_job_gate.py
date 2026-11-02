"""The public job validates each full package once before any document runs."""
import copy
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from driver.prepare import job
from driver.prepare.get import acquire as acquisition

RUNTIME = Path(job.__file__).resolve().parents[2]
FIXTURES = RUNTIME / 'tests/driver/prepare/get/fixtures'
SHA = '7f6812c06b8455d9c33611c9acca9320f1982fd7e3fc49572e3771a80cf935bb'
TARGETS = ('FilingSummary.xml', 'amg-20230501_def.xml')


class PackageJobGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='package_job_gate_')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        copies = json.loads((FIXTURES / 'sec_copies.json').read_text())
        def fetch(url):
            record = copies.get(url)
            if record is None: return None
            body = gzip.decompress((FIXTURES / record['file']).read_bytes())
            assert hashlib.sha256(body).hexdigest() == record['sha256']
            return body
        package = cls.root / 'submission.gz'
        shutil.copyfile(FIXTURES / '0001004434-23-000015.txt.gz', package)
        cls.version = acquisition.acquire('0001004434-23-000015', '1004434', '8-K', cls.root / 'versions',
                                          package=package, sha256=SHA, minimum_free_bytes=0, fetch=fetch)
        cls.manifest, _ = acquisition.read_package(cls.version)
        files = {str(p.relative_to(RUNTIME)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in (RUNTIME / 'driver').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        cls.runtime_manifest = cls.root / 'RUNTIME.json'
        cls.runtime_manifest.write_text(json.dumps(dict(files=files)))

    def setUp(self):
        self.work = Path(tempfile.mkdtemp(dir=self.root))
        self.version_copy = self.work / self.version.name
        shutil.copytree(self.version, self.version_copy)
        self.metadata = self.version_copy / 'manifest.json'
        self.metadata.chmod(0o600)
        self.serial = 0
        home = self.work / 'home'; home.mkdir()
        env = patch.dict(os.environ, HOME=str(home)); env.start(); self.addCleanup(env.stop)

    def run_job(self, manifest):
        self.serial += 1
        self.metadata.write_text(json.dumps(manifest))  # checksum is deliberately recomputed AFTER a bad edit
        rows = [dict(file_id=m['filename'], filename=m['filename'], dispatch='xml', source_sha256=m['sha256'],
                     immutable_package_directory=str(self.version_copy), package_metadata_path=str(self.metadata),
                     package_metadata_sha256=hashlib.sha256(self.metadata.read_bytes()).hexdigest(), package_sha256=SHA)
                for m in self.manifest['members'] if m['filename'] in TARGETS]
        self.assertEqual(len(rows), 2)
        plan = dict(runtime_root=str(RUNTIME), runtime_manifest=dict(path=str(self.runtime_manifest),
                    sha256=hashlib.sha256(self.runtime_manifest.read_bytes()).hexdigest()), context_explore=False, source_commands=rows)
        body = json.dumps(plan).encode(); path = self.work / f'PLAN_{self.serial}.json'; path.write_bytes(body)
        out = self.work / f'job_{self.serial}'
        code = job.main(path, hashlib.sha256(body).hexdigest(), out, seconds=40)
        return code, json.loads((out / 'RESULT.json').read_text())

    def test_two_real_documents_validate_their_one_package_once(self):
        with patch.object(acquisition, 'read_package', wraps=acquisition.read_package) as checked:
            code, result = self.run_job(self.manifest)
        self.assertEqual(code, 0)
        self.assertEqual(checked.call_count, 1)
        self.assertEqual({r['file_id'] for r in result['rows']}, set(TARGETS))
        self.assertTrue(all(r['outcome'] == 'verified_saved_output' for r in result['rows']))

    def test_every_unused_member_and_header_field_is_checked_before_generation(self):
        changes = []
        for index, member in enumerate(self.manifest['members']):
            if member['filename'] in TARGETS: continue
            for field in member:
                changed = copy.deepcopy(self.manifest); del changed['members'][index][field]
                changes.append((f"unused {member['filename']} missing {field}", changed))
                if field in ('sha256', 'bytes', 'type'):
                    changed = copy.deepcopy(self.manifest)
                    changed['members'][index][field] = member[field] + 1 if type(member[field]) is int else str(member[field]) + '_changed'
                    changes.append((f"unused {member['filename']} changed {field}", changed))
        for section, value in self.manifest.items():
            if section == 'members': continue
            for field in value if isinstance(value, dict) else (None,):
                changed = copy.deepcopy(self.manifest)
                if field is None: del changed[section]
                else: del changed[section][field]
                changes.append((f'header {section}/{field}', changed))
        changed = copy.deepcopy(self.manifest); changed['identity']['form'] = '10-K'
        changes.append(('header changed form', changed))
        for label, changed in changes:
            with self.subTest(case=label), patch.object(job, 'child', side_effect=AssertionError('generation before full package validation')) as child:
                with self.assertRaises(acquisition.AcquisitionError): self.run_job(changed)
                child.assert_not_called()


if __name__ == '__main__': unittest.main()
