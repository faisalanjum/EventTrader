"""The automatic single-version path end to end through the ACTUAL caller (root-native-automatic-trigger-closeout-20261028t211651877057z): real job.py,
document.py, native acquisition, reconstruct/verify and browser on an INVENTED filing (version_fixture) whose served copy carries ONE inserted script.
No result is fabricated and no verdict is patched: the first row is held by that unreviewed version, job.main claims it, runs the explored and the
comparison-only arms as child jobs, qualifies it, releases the file in one more ordinary attempt; the second row of the same version reuses the
record after the parent RESULT changed. Damage: the same bot also rewriting filing text on a click is held, with no release.
Run with the qualified interpreter from this checkout. Environment: BROWSER_EXECUTABLE (default: the pinned headless shell path in version_fixture)."""
import json, tempfile, unittest
from pathlib import Path
from tests.driver.prepare import version_fixture as vf

rd = lambda p: json.loads(Path(p).read_bytes())


class FirstFileQualifiesAndASecondReuses(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = Path(tempfile.mkdtemp(prefix='vq_native_')); cls.pp, cls.pin, cls.f = vf.build(cls.t, filings=2)
        cls.exit, cls.out = vf.run_job(cls.t, cls.pp, cls.pin); cls.rows = rd(cls.out / 'RESULT.json')['rows']
    def test_the_acquisition_bound_one_genuine_inserted_script(self):
        ins = self.f['record']['target']['inserted_script']
        self.assertEqual((self.f['acquisition'], ins['href'], ins['response_sha256']), ('associated', vf.SEC + vf.BOT_PATH, self.f['bot_sha256']))
    def test_the_first_file_is_released_by_its_own_qualification(self):
        r = self.rows[0]; q = r['qualification']
        self.assertEqual((self.exit, r['outcome'], r['reasons'], q['outcome'], q['reasons']), (0, 'verified_saved_output', [], 'passed', []))
        self.assertEqual(q['script_sha256'], self.f['bot_sha256']); self.assertTrue(Path(r['attempt']).is_relative_to(self.out / 'qualification_0' / 'release'))
        self.assertEqual(r['held']['outcome'], 'incomplete'); self.assertTrue((Path(r['held']['attempt']) / 'COMPLETE.json').is_file())  # the held attempt is kept whole
        rel = [x for x in rd(self.out / 'qualification_0' / 'release' / 'RESULT.json')['rows'] if x['file_id'] == r['file_id']][0]
        self.assertEqual({k: r[k] for k in ('native_status', 'native_error', 'generate_observed', 'attempt_bytes', 'reconstruct_exit', 'verify_exit')},
                         {k: rel[k] for k in ('native_status', 'native_error', 'generate_observed', 'attempt_bytes', 'reconstruct_exit', 'verify_exit')})  # every parent field is the release's own
        self.assertEqual((r['native_status'], r['held']['native_status']), ('OK', 'PARTIAL'))
        rec = rd(q['record']); self.assertEqual((rec['outcome'], rec['file_id'], rec['comparison']['all_equal']), ('passed', r['file_id'], True)); self.assertGreater(len(rec['states']), 1)
        held = rd(Path(r['held']['attempt']) / 'ROUTE.json')['facts']['optional_controls']; self.assertEqual(held['other_objections'], 0); self.assertGreater(held['inserted_version_objections'], 0)
    def test_the_second_file_reuses_the_record_after_the_parent_result_changed(self):
        r = self.rows[1]; self.assertEqual((r['outcome'], r['reasons'], r['native_status']), ('verified_saved_output', [], 'OK')); self.assertNotIn('qualification', r); self.assertNotIn('held', r)
        self.assertTrue(r['attempt'].endswith('out/attempt_1'))  # its own ordinary attempt, no child job
        self.assertEqual(rd(Path(r['attempt']) / 'ROUTE.json')['facts']['optional_controls']['qualified_versions'], [self.f['bot_sha256']])
    def test_one_claim_one_record_and_the_arms_never_qualify(self):
        self.assertEqual(sorted(p.name for p in self.f['store'].iterdir()), sorted([self.f['bot_sha256'] + '.claim', self.f['bot_sha256'] + '.json']))
        for arm in ('explored', 'without', 'release'): self.assertNotIn('qualification', rd(self.out / 'qualification_0' / arm / 'RESULT.json')['rows'][0])
        self.assertFalse((self.out / 'qualification_1').exists())


class AScriptThatChangesFilingTextIsHeld(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = Path(tempfile.mkdtemp(prefix='vq_native_evil_')); cls.pp, cls.pin, cls.f = vf.build(cls.t, bot=vf.EVIL)
        cls.exit, cls.out = vf.run_job(cls.t, cls.pp, cls.pin); cls.row = rd(cls.out / 'RESULT.json')['rows'][0]
    def test_no_qualification_and_no_release(self):
        q = self.row['qualification']; self.assertEqual((self.exit, self.row['outcome'], q['outcome']), (1, 'incomplete', 'held')); self.assertTrue(q['reasons'])
        self.assertNotIn('release', q); self.assertNotIn('held', self.row); self.assertFalse((self.out / 'qualification_0' / 'release').exists())
        self.assertEqual(rd(q['record'])['outcome'], 'held')


if __name__ == '__main__':
    unittest.main()
