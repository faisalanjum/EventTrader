"""The picture runtime imports cleanly on its own: with the benchmark package and the old experiment module names blocked, every runtime module
loads from this checkout and nothing comes from benchmark or research code; the runtime uses the one shared comparison implementation
(driver/prepare/compare.py). Ported on 2026-10-06 from prepare_work runtime_extract_20261006/isolation.py and combined_check.py; the replay of
saved fixtures through the clean import moves with the shared fixtures."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = str(Path(__file__).resolve().parents[4])
PROBE = r'''
import importlib, importlib.abc, os, sys
BLOCKED = {'benchmarks', 'packets', 'rowcheck', 'routing', 'free_evidence', 'table_choice', 'geom', 'plant', 'validate_v2', 'keyrows', 'measure', 'free_support', 'sonnet_caller'}
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name.split('.')[0] in BLOCKED: raise ImportError('blocked: ' + name)
sys.meta_path.insert(0, Block()); sys.path.insert(0, sys.argv[1]); os.chdir('/')
if len(sys.argv) > 2: sys.path.insert(1, sys.argv[2]); importlib.import_module(sys.argv[3])   # a control: some other module loaded too
for m in ('compare', 'pictures', 'pictures.readers', 'pictures.worker', 'pictures.packets', 'pictures.routing', 'pictures.rowcheck', 'pictures.free_evidence',
          'pictures.table_choice', 'pictures.geometry'):
    importlib.import_module('driver.prepare.' + m)
root = os.path.realpath(sys.argv[1]) + os.sep
ours = [n for n, m in sys.modules.items() if n.startswith('driver.') and getattr(m, '__file__', None)]
assert all(os.path.realpath(sys.modules[n].__file__).startswith(root) for n in ours), [sys.modules[n].__file__ for n in ours]
libs = (root,) + tuple(os.path.realpath(x) + os.sep for x in (sys.prefix, sys.base_prefix))   # this checkout and the environment's installed libraries
bad = [n for n, m in sys.modules.items() if n.split('.')[0] in BLOCKED or ('prepare_work' in (f := os.path.realpath(getattr(m, '__file__', None) or '')) and not f.startswith(libs))]
assert not bad, bad
from driver.prepare import compare
from driver.prepare.pictures import rowcheck
assert all(getattr(rowcheck, n) is getattr(compare, n) for n in ('critical', 'norm', 'reading_units', 'spacing_only', 'wer_counts', '_TOKEN'))
print('clean', len(ours))
'''


def probe(*args):
    return subprocess.run([sys.executable, '-I', '-c', PROBE, *args], capture_output=True, text=True)


class ImportTests(unittest.TestCase):
    def test_clean_import_with_benchmark_and_research_code_blocked(self):
        p = probe(ROOT); self.assertEqual(p.returncode, 0, p.stderr[-2000:]); self.assertTrue(p.stdout.startswith('clean'))

    def test_a_checkout_inside_a_research_folder_and_a_foreign_module_there(self):  # Codex port review: only the checkout itself is allowed
        with tempfile.TemporaryDirectory() as d:
            checkout = Path(d, 'prepare_work', 'checkout'); shutil.copytree(Path(ROOT, 'driver'), checkout / 'driver', ignore=shutil.ignore_patterns('__pycache__'))
            p = probe(str(checkout)); self.assertEqual(p.returncode, 0, p.stderr[-2000:])                    # positive control
            research = Path(d, 'prepare_work', 'research'); research.mkdir(); (research / 'foreign_probe.py').write_text('X = 1\n')
            p = probe(str(checkout), str(research), 'foreign_probe'); self.assertNotEqual(p.returncode, 0)     # negative control: still refused
            self.assertIn('foreign_probe', p.stderr)


if __name__ == '__main__':
    unittest.main()
