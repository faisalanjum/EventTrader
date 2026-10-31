"""Actual saved-output/qualification children on the existing invented fixture.

Only viewer data slots and menu markup differ: the selected report is explicit,
and two real accordion categories exist. All executable viewer assets are exact.
The deterministic varied-start graph test is separate; no timing claim here.
"""
import hashlib, json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from . import version_fixture as vf
from driver.prepare import job

read = lambda p: json.loads(Path(p).read_bytes())
BASE_VIEWER = vf.viewer
# A separate invented bot: POST on every full native click, with no frame creation
# during report selection (that independent lifetime-context deficit is not eligible).
BOT = vf.BOT.replace(b"    var f = document.createElement('iframe'); f.style.display = 'none'; document.body.appendChild(f); f.remove(); ", b'')
EVIL = BOT.replace(b"}, true);", b"var c = document.querySelector('#reportDiv td.text'); if (c) c.textContent = c.textContent + ' (changed)'; }, true);")


def viewer():
    v = BASE_VIEWER()
    v = v.replace(b'var reports = new Array(2);', b'var reports = new Array(3);')
    v = v.replace(b"reports[2] = 'all';", b"reports[3] = 'all';")
    line = b'reports[1] = "' + vf.FOLDER.encode() + b'R1.htm";'
    assert v.count(line) == 1
    v = v.replace(line, b"reports[1] = 'all';\n    reports[2] = \"" + vf.FOLDER.encode() + b'R1.htm";')
    v = v.replace(b'class="all_reports" href="javascript:loadReport(2);"', b'class="all_reports" href="javascript:loadReport(3);"')
    old = b'    <li class="accordion" id="r1" ><a class="xbrlviewer" onClick="javascript:highlight(this);" href="javascript:loadReport(1);">Cover page</a></li>\n'
    new = (b'<li class="accordion"><a href="#">Introduction</a><ul><li id="r1"><a class="xbrlviewer" onClick="javascript:highlight(this);" href="javascript:loadReport(1);">Introduction</a></li></ul></li>'
           b'<li class="accordion"><a href="#">Reports</a><ul><li id="r2"><a class="xbrlviewer" onClick="javascript:highlight(this);" href="javascript:loadReport(2);">Invented Information</a></li></ul></li>')
    assert v.count(old) == 1
    return v.replace(old, new)


def run(name, bot, filings=1):
    root = Path(os.environ.get('ASTRA_TEST_ROOT', tempfile.gettempdir())); root.mkdir(exist_ok=True)
    t = Path(tempfile.mkdtemp(prefix=name, dir=root))
    with patch.object(vf, 'viewer', viewer): pp, pin, facts = vf.build(t, bot=bot, filings=filings)
    code, out = vf.run_job(t, pp, pin)
    return t, code, out, facts, read(out / 'RESULT.json')['rows']


class NativeViewerStart(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.t, cls.code, cls.out, cls.facts, cls.rows = run('positive_', BOT, 2)
    def test_own_normal_observation_is_used_by_every_arm_and_saved_output_passes(self):
        row = self.rows[0]; self.assertEqual((self.code, row['outcome']), (0, 'verified_saved_output'), json.dumps(self.rows))
        q = row['qualification']; self.assertEqual((q['outcome'], q['reasons']), ('passed', []))
        normal = Path(row['held']['attempt']); complete = normal / 'COMPLETE.json'; ref = {'path': str(complete), 'sha256': hashlib.sha256(complete.read_bytes()).hexdigest()}
        renders = read(normal / 'CONTEXT_RENDERS.json'); originals = [r for r in renders if 'viewer_start' in r]
        self.assertEqual(len(originals), 1); plan = originals[0]['viewer_start']; self.assertEqual(plan['source_sha256'], vf.sha(vf.member()))
        self.assertEqual(len(plan['controls']), 2)
        for arm in ('explored', 'without', 'release'):
            self.assertEqual(read(self.out / 'qualification_0' / (arm + '_PLAN.json'))['context_viewer_start'], ref)
            a = Path(read(self.out / 'qualification_0' / arm / 'RESULT.json')['rows'][0]['attempt'])
            self.assertEqual(read(a / 'COMPLETE.json')['source_sha256'], vf.sha(vf.member()))
        rec = read(q['record']); self.assertGreater(len(rec['states']), 1); self.assertTrue(rec['comparison']['all_equal'])
        self.assertTrue(all(all(fields.values()) for fields in rec['states'].values()))
        source = read(Path(row['attempt']) / 'source_reading/ROUTE.json')
        self.assertIn('42', json.dumps(source['units'])); self.assertIn('The number of invented widgets.', json.dumps(source['units']))
    def test_same_version_reuses_approval_but_second_file_has_its_own_start(self):
        row = self.rows[1]; self.assertEqual(row['outcome'], 'verified_saved_output'); self.assertNotIn('qualification', row)
        self.assertTrue(row['attempt'].endswith('out/attempt_1'))
        renders = read(Path(row['attempt']) / 'CONTEXT_RENDERS.json')
        self.assertEqual(len([r for r in renders if 'viewer_start' in r]), 1)
        self.assertEqual(sorted(p.name for p in self.facts['store'].iterdir()), sorted([self.facts['bot_sha256'] + '.claim', self.facts['bot_sha256'] + '.json']))


class NativeViewerDamage(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.t, cls.code, cls.out, cls.facts, cls.rows = run('damage_', EVIL)
    def test_real_source_damage_is_held_before_without_and_release(self):
        row = self.rows[0]; self.assertEqual((self.code, row['outcome']), (1, 'incomplete'), json.dumps(row))
        q = row['qualification']; self.assertTrue(q['outcome'].startswith('held before WITHOUT'), json.dumps(q))
        self.assertNotIn('without', q); self.assertNotIn('release', q); self.assertNotIn('record', q)
        self.assertTrue(job.clean_row(row)); self.assertEqual(sorted(p.name for p in self.facts['store'].iterdir()), [self.facts['bot_sha256'] + '.claim'])


if __name__ == '__main__': unittest.main()
