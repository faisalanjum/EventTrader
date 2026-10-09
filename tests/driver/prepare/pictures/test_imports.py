"""The picture runtime imports cleanly on its own: with the benchmark package and the old experiment module names blocked, every runtime module
loads from this checkout and nothing comes from benchmark or research code; the runtime uses the one shared comparison implementation
(driver/prepare/compare.py). Ported on 2026-10-06 from prepare_work runtime_extract_20261006/isolation.py and combined_check.py; the four saved
cases (agree, resolved, unrouted, visual) run in a clean process through the pinned fixtures (2026-10-07)."""
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
          'pictures.table_choice', 'pictures.geometry', 'pictures.join'):
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


SAVED_CASES = r'''
import importlib.abc, os, subprocess, sys, tempfile
BLOCKED = {'benchmarks', 'packets', 'rowcheck', 'routing', 'free_evidence', 'table_choice', 'geom', 'plant', 'validate_v2', 'keyrows', 'measure', 'free_support', 'sonnet_caller', 'inventory'}
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name.split('.')[0] in BLOCKED: raise ImportError('blocked: ' + name)
sys.meta_path.insert(0, Block()); sys.path.insert(0, sys.argv[1]); os.chdir('/')
def boom(*a, **k): raise AssertionError('a subprocess or a second reader was started')
subprocess.run = subprocess.Popen = boom
from driver.prepare import pictures
from tests.driver.prepare.pictures.saved import Saved, body
NAMES = {'agree': '004_0000877212-23-000025_zbra-20221231_g1.jpg', 'resolved': '056_0000899051-24-000082_allcorp93024investorsupp012.jpg',
         'unrouted': '001_0000950103-25-013977_image_001.jpg', 'visual': '000_0001170010-24-000084_carmaxlogoblue2019a.jpg'}
with tempfile.TemporaryDirectory() as d:
    s = Saved(d)
    off = lambda r: s.line(r['expected']['off']['asset'], r['expected']['off']['line'])
    for k, n in NAMES.items():                                            # default mode first: nothing optional may load
        r = s.by_name[n]; name, pic, html, tok, free, second = s.inputs(r)
        asked, flags, text, rec = pictures.read_picture(name, pic, html, tok, free, s.limit, second=boom)
        b = off(r); assert not asked and flags == b['flags'] and body(*s.relocated(r, text, rec)) == (b['text'], b['record']), k
    assert 'driver.prepare.pictures.table_choice' not in sys.modules and 'driver.prepare.pictures.geometry' not in sys.modules
    for k, n in NAMES.items():
        r = s.by_name[n]; name, pic, html, tok, free, second = s.inputs(r); e = r['expected']['on']
        asked, flags, text, rec = pictures.read_picture(name, pic, html, tok, free, s.limit, enable_sonnet=True, second=lambda _, sec=second: sec)
        want = (off(r)['text'], off(r)['record']) if not e['asked'] else (s.text(e['assets'][0])[:-1], s.json(e['assets'][1]))
        assert (asked, flags) == (e['asked'], e['why']) and body(*s.relocated(r, text, rec)) == want, k
        kinds = {b['status'] for b in rec['blocks']} | {'resolved' for b in rec['blocks'] if b['table_choice']} | ({'unrouted'} if not asked else set())
        assert k in kinds, (k, kinds)
root = os.path.realpath(sys.argv[1]) + os.sep
ours = [n for n, m in sys.modules.items() if n.startswith(('driver.', 'tests.')) and getattr(m, '__file__', None)]
assert all(os.path.realpath(sys.modules[n].__file__).startswith(root) for n in ours), ours
print('isolated', len(NAMES))
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

    def test_the_four_saved_cases_run_with_research_code_blocked(self):  # agree, resolved, unrouted, visual: both modes, pinned fixtures only
        p = subprocess.run([sys.executable, '-I', '-c', SAVED_CASES, ROOT], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr[-3000:]); self.assertEqual(p.stdout.strip(), 'isolated 4')


if __name__ == '__main__':
    unittest.main()
