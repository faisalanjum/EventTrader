"""Caller release controls (Root PRODUCTION_CALLER_IMPLEMENTATION_20261022). The batch owner driver/prepare/job.py must:
- run its generation, reconstruct and verify children with the interpreter, HOME and CPU affinity it was itself started with;
- run reconstruct/verify from its own reviewed runtime;
- refuse, before any row, a plan that names another runtime, a changed runtime, or a manifest that is not the exact inventory of the runtime's
  driver tree (Python __pycache__ aside; every listed file hash-checked); the default generation path is the pinned sibling document.py.

Every check reads what an executed child recorded: the probe generation child, or a stand-in reconstruct module inside a test runtime.
A path string alone proves nothing here. A missing interpreter or CPU fails a check; nothing is skipped.

Run with the qualified interpreter: python -I -B tests/driver/prepare/test_caller.py
JOB_UNDER_TEST=<job.py> tests another copy (default: this checkout's driver/prepare/job.py). The test runtimes are fresh folders under TMPDIR and are kept."""
import hashlib, json, os, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
JOB = Path(os.environ.get('JOB_UNDER_TEST') or HERE.parents[2] / 'driver/prepare/job.py')
PROBE = HERE / 'fixtures/caller_probe_generator.py'
sha = lambda b: hashlib.sha256(b).hexdigest()
STANDIN = b'''import json, os, sys
args = sys.argv[1:]
mark = {'executable': sys.executable, 'cwd': os.getcwd(), 'file': __file__}
if args[0] == 'verify': print(json.dumps({'custody': [], 'preserved': [], 'annotations': [], 'stand_in': mark})); sys.exit(0)
open(args[1], 'w').write(json.dumps({'unknowns': [], 'sequence': [], 'stand_in': mark}))
'''  # a stand-in reconstruct module: says which runtime and interpreter executed it


ENTRY_POINTS = ('driver/prepare/job.py', 'driver/prepare/document.py', 'driver/prepare/reconstruct.py')


def runtime(root, job_bytes, omit=()):
    """A small runtime: the job under test, the probe as its default document.py and a stand-in reconstruct module; the manifest beside the
    folder pins every file except `omit`."""
    for rel, data in {'driver/__init__.py': b'', 'driver/prepare/__init__.py': b'', 'driver/prepare/job.py': job_bytes, 'driver/prepare/document.py': PROBE.read_bytes(),
                      'driver/prepare/reconstruct.py': STANDIN}.items():
        p = root / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)
    files = {str(p.relative_to(root)): sha(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    for rel in omit: files.pop(rel)
    man = root.parent / (root.name + '_MANIFEST.json'); man.write_text(json.dumps({'runtime_root': str(root), 'files': files}))
    return man


def row(k, complete=True):
    return {'file_id': f'probe/{k}', 'source_sha256': sha(f'probe {k}'.encode()), 'probe': {'complete': complete}}


class Caller(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp(prefix='caller_')); self.rt = self.t / 'rt'; self.man = runtime(self.rt, JOB.read_bytes())

    def go(self, launcher=None, root=None, man=None, env=None, pre=(), job=None, rows=(row(0),), manifest_sha=None, default=False, generator=None):
        """Run the job once into a new folder; returns (exit, out folder, probe record, stand-in R mark, stand-in verify mark)."""
        man = man or self.man
        body = json.dumps({'runtime_root': str(root or self.rt), 'runtime_manifest': {'path': str(man), 'sha256': manifest_sha or sha(man.read_bytes())},
                           'source_commands': list(rows)}).encode()
        plan = self.t / f'PLAN_{len(list(self.t.glob("PLAN_*")))}.json'; plan.write_bytes(body); out = self.t / ('out_' + plan.stem)
        env = dict({'PATH': '/usr/bin:/bin', 'HOME': str(self.t / 'home')}, **(env or {})) if env != 'no HOME' else {'PATH': '/usr/bin:/bin'}
        p = subprocess.run([*pre, launcher or sys.executable, '-I', '-S', '-B', str(job or self.rt / 'driver/prepare/job.py'), str(plan), sha(body), str(out), *(() if default else (str(generator or PROBE), '60'))],
                           env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        (self.t / (plan.stem + '.stderr')).write_bytes(p.stderr)
        read = lambda f: json.loads(f.read_bytes()) if f.is_file() else None
        R, V = read(out / 'logs_0/R.json'), read(out / 'logs_0/verify.stdout')
        return p.returncode, out, read(out / 'attempt_0/PROBE.json'), (R or {}).get('stand_in'), (V or {}).get('stand_in')

    # valid positive controls (old and new caller alike)
    def test_a_valid_plan_runs_its_rows(self):
        code, out, probe, _, _ = self.go(rows=(row(0), row(1, complete=False)))
        res = json.loads((out / 'RESULT.json').read_bytes())['rows']
        self.assertEqual((code, probe is not None, [r['outcome'] for r in res][1:]), (1, True, ['generation_failed']))

    def test_symlinked_paths_name_the_same_runtime(self):
        link = self.t / 'link'; link.symlink_to(self.rt, target_is_directory=True)
        code, out, probe, rmark, _ = self.go(root=link, job=link / 'driver/prepare/job.py')
        self.assertEqual((probe is not None, (out / 'attempt_0/START.json').is_file()), (True, True))

    # the job's children: launching interpreter, own runtime, HOME and CPU affinity
    def test_children_run_with_the_launching_interpreter(self):
        launchers = [sys.executable, getattr(sys, '_base_executable', sys.executable)]
        self.assertNotEqual(*launchers, 'needs two genuinely different interpreters: run under the qualified virtualenv')
        for launcher in launchers:
            with self.subTest(launcher=launcher):
                _, _, probe, rmark, vmark = self.go(launcher=launcher)
                self.assertEqual([probe and probe['executable'], rmark and rmark['executable'], vmark and vmark['executable']], [launcher] * 3)

    def test_reconstruct_and_verify_run_from_the_jobs_own_runtime(self):
        _, _, _, rmark, vmark = self.go()
        own = str(self.rt.resolve())
        self.assertEqual([rmark and rmark['cwd'], vmark and vmark['cwd'], rmark and rmark['file']], [own, own, str(self.rt.resolve() / 'driver/prepare/reconstruct.py')])

    def test_home_comes_from_the_environment(self):
        home = str(self.t / 'elsewhere')
        _, _, probe, _, _ = self.go(env={'HOME': home})
        self.assertEqual(probe and probe['home'], home)

    def test_cpu_affinity_is_inherited_from_the_launch(self):
        cpus = sorted(os.sched_getaffinity(0))[-2:]
        self.assertTrue(len(cpus) == 2 and cpus != [0, 1], 'needs two CPUs other than 0 and 1')
        _, _, probe, _, _ = self.go(pre=('taskset', '-c', ','.join(map(str, cpus))))
        self.assertEqual(probe and probe['affinity'], cpus)

    # refusals before any row: nothing is created
    def refused(self, **kw):
        code, out, probe, _, _ = self.go(**kw)
        self.assertEqual((code != 0, out.exists()), (True, False))

    def test_another_runtime_is_refused_before_any_row(self):
        other = self.t / 'other'; man2 = runtime(other, JOB.read_bytes())
        self.refused(root=other, man=man2)

    def test_a_changed_runtime_is_refused_before_any_row(self):
        with self.subTest('manifest pin'): self.refused(manifest_sha='0' * 64)
        with self.subTest('runtime file changed after the manifest'):
            f = self.rt / 'driver/prepare/reconstruct.py'; f.write_bytes(f.read_bytes() + b'\n# changed\n'); self.refused()

    def test_the_default_production_generator_runs_when_pinned(self):  # no GENERATOR argument: the pinned sibling document.py
        code, out, probe, rmark, vmark = self.go(default=True)
        res = json.loads((out / 'RESULT.json').read_bytes())
        self.assertEqual((code, res['generator'], res['rows'][0]['outcome'], probe is not None, rmark is not None, vmark is not None),
                         (0, str(self.rt.resolve() / 'driver/prepare/document.py'), 'verified_saved_output', True, True, True))

    def test_the_explicit_own_generator_with_seconds_is_production(self):  # the pinned sibling passed explicitly, as needed to set SECONDS
        own = self.rt / 'driver/prepare/document.py'
        code, out, probe, rmark, vmark = self.go(generator=own)
        res = json.loads((out / 'RESULT.json').read_bytes())
        self.assertEqual((code, res['generator'], res['rows'][0]['outcome'], probe is not None, rmark is not None, vmark is not None),
                         (0, str(own), 'verified_saved_output', True, True, True))

    def test_a_missing_production_entry_point_is_refused_before_any_row(self):  # each of the three, on the default path
        for rel in ENTRY_POINTS:
            with self.subTest(missing=rel):
                rt = self.t / ('missing_' + rel.split('/')[-1][:-3]); man = runtime(rt, JOB.read_bytes(), omit=(rel,))
                self.refused(root=rt, man=man, job=rt / 'driver/prepare/job.py', default=True)

    def test_a_changed_production_entry_point_is_refused_before_any_row(self):  # each of the three, changed after its manifest
        for rel in ENTRY_POINTS:
            with self.subTest(changed=rel):
                rt = self.t / ('changed_' + rel.split('/')[-1][:-3]); man = runtime(rt, JOB.read_bytes()); f = rt / rel; f.write_bytes(f.read_bytes() + b'\n# changed\n')
                self.refused(root=rt, man=man, job=rt / 'driver/prepare/job.py', default=True)

    def test_missing_home_is_refused_before_any_row(self):
        self.refused(env='no HOME')


INVENTORY = json.loads((HERE / 'fixtures/runtime_inventory_47.json').read_bytes())['files']  # the frozen directory inventory: the expected set, never the job's own rule
MARK = b"import os\nopen(os.path.join(os.environ['TMPDIR'], 'UNLISTED_INIT_EXECUTED'), 'a').write('imported\\n')\n"


class RuntimeInventory(unittest.TestCase):
    """The manifest must be the exact inventory of the runtime's driver tree (Python __pycache__ aside); every listed file stays hash-checked."""
    def setUp(self):
        self.t = Path(tempfile.mkdtemp(prefix='inventory_'))

    def go(self, rt, files, rows=()):
        """Default generation path (no GENERATOR); returns (exit, out folder)."""
        man = self.t / f'MANIFEST_{len(list(self.t.glob("MANIFEST_*")))}.json'; man.write_text(json.dumps({'files': files}))
        body = json.dumps({'runtime_root': str(rt), 'runtime_manifest': {'path': str(man), 'sha256': sha(man.read_bytes())}, 'source_commands': list(rows)}).encode()
        plan = man.with_name(man.name.replace('MANIFEST', 'PLAN')); plan.write_bytes(body); out = self.t / ('out_' + plan.stem)
        p = subprocess.run([sys.executable, '-I', '-S', '-B', str(rt / 'driver/prepare/job.py'), str(plan), sha(body), str(out)], env={'PATH': '/usr/bin:/bin', 'HOME': str(self.t)},
                           stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        (self.t / (plan.stem + '.stderr')).write_bytes(p.stderr)
        return p.returncode, out

    def refused(self, rt, files, **kw):
        code, out = self.go(rt, files, **kw)
        self.assertEqual((code != 0, out.exists()), (True, False))

    def real(self):
        """A copy of this checkout's runtime driver tree. Both the checkout and the copy must list exactly the frozen inventory."""
        src = JOB.parents[2]
        self.assertEqual(sorted(str(p.relative_to(src)) for p in (src / 'driver').rglob('*') if p.is_file() and '__pycache__' not in p.parts), sorted(INVENTORY))
        rt = self.t / 'rt47'
        for n in INVENTORY: d = rt / n; d.parent.mkdir(parents=True, exist_ok=True); d.write_bytes((src / n).read_bytes())
        self.assertEqual(sorted(str(p.relative_to(rt)) for p in (rt / 'driver').rglob('*') if p.is_file()), sorted(INVENTORY))
        return rt, {n: sha((rt / n).read_bytes()) for n in INVENTORY}

    def test_every_single_omission_from_the_frozen_inventory_is_refused(self):  # all 47 members, the 3 entry points included
        rt, full = self.real()
        self.assertEqual(len(full), 47)
        for n in INVENTORY:
            with self.subTest(omitted=n): self.refused(rt, {k: v for k, v in full.items() if k != n})

    def test_the_complete_inventory_is_accepted_beside_python_cache_files(self):
        rt, full = self.real()
        for d in ('driver/__pycache__', 'driver/prepare/convert/__pycache__'):
            (rt / d).mkdir(); (rt / d / 'cached.cpython-311.pyc').write_bytes(b'harmless cache')
        code, out = self.go(rt, full)
        self.assertEqual((code, (out / 'RESULT.json').is_file()), (0, True))

    def test_an_extra_file_in_the_runtime_is_refused(self):
        rt, full = self.real(); (rt / 'driver/prepare/extra.py').write_bytes(b'')
        self.refused(rt, full)

    def test_a_listed_file_that_is_absent_is_refused(self):
        rt, full = self.real()
        self.refused(rt, dict(full, **{'driver/prepare/absent.py': sha(b'')}))

    def test_an_unlisted_imported_initializer_is_refused_and_never_runs(self):  # OCR's demonstrated red (demo_unlisted_module.py)
        rt = self.t / 'rt'; runtime(rt, JOB.read_bytes()); (rt / 'driver/prepare/__init__.py').write_bytes(MARK)
        files = {str(p.relative_to(rt)): sha(p.read_bytes()) for p in rt.rglob('*') if p.is_file()}; files.pop('driver/prepare/__init__.py')
        self.refused(rt, files, rows=(row(0),))
        self.assertEqual(list(self.t.rglob('UNLISTED_INIT_EXECUTED')), [])

if __name__ == '__main__':
    unittest.main(verbosity=2)
