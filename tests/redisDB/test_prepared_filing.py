"""Adapter tests (redisDB/prepared_filing.py). Pure tests: the real public AMG package, its SEC copies and index page (tests/driver/prepare/get/fixtures),
a real saved verified R1 product (fixture store group adapter.r1_verified) and saved job.py rows (fixtures/real_rows.json); the Root code-review findings
F1-F5 each have one test. The runtime under test is this checkout with its deployed runtime manifest (k8s/prepared-extraction/RUNTIME_MANIFEST.json,
or ADAPTER_RUNTIME_MANIFEST). Needs PREPARE_TEST_DATA (tests/driver/prepare/README.md).
The end-to-end event runs only with ADAPTER_E2E=1, ADAPTER_OUT=<new folder on a filesystem with >=16% free> and ADAPTER_RECORDED=<recorded SEC
responses: responses.sqlite3 + blobs> (pinned job.py: 3 browser rows)."""
import atexit, functools, gzip, hashlib, json, os, shutil, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

sys.dont_write_bytecode = True  # never write caches into the runtime tree
HERE = Path(__file__).resolve().parent
RUNTIME = HERE.parents[1]  # this checkout
RUNTIME_MANIFEST = Path(os.environ.get('ADAPTER_RUNTIME_MANIFEST', RUNTIME / 'k8s/prepared-extraction/RUNTIME_MANIFEST.json'))
sys.path.insert(0, str(RUNTIME))
from redisDB import prepared_filing as pf
from driver.prepare.get.acquire import acquire, read_package
from tests.driver.prepare.support import FixtureStore

AMG = dict(accessionNo='0001004434-23-000015', cik='1004434', formType='8-K')
FIXTURES = RUNTIME / 'tests/driver/prepare/get/fixtures'
AMG_PACKAGE = FIXTURES / '0001004434-23-000015.txt.gz'
AMG_SHA = '7f6812c06b8455d9c33611c9acca9320f1982fd7e3fc49572e3771a80cf935bb'
AMG_INDEX = 'https://www.sec.gov/Archives/edgar/data/1004434/000100443423000015/0001004434-23-000015-index.html'
RECORDED = os.environ.get('ADAPTER_RECORDED')  # end-to-end only: the recorded viewer/browser responses (public AMG)
V = pf.VERIFIED
SEC_COPIES = json.loads((FIXTURES / 'sec_copies.json').read_text())  # the runtime's own checked-in SEC copies (hash-pinned there)
REAL_RUN = subprocess.run
WORK = Path(tempfile.mkdtemp()); atexit.register(shutil.rmtree, WORK, True)


@functools.cache
def amg_version():  # the native archive version of the checked-in AMG package; the SEC copies prove its two remapped files
    pkg = WORK / 'amg.txt.gz'; shutil.copyfile(AMG_PACKAGE, pkg)  # acquire hard-links a supplied gzip: link a private copy
    return acquire(AMG['accessionNo'], AMG['cik'], AMG['formType'], WORK / 'versions', package=pkg, sha256=AMG_SHA, fetch=sec_copy)


@functools.cache
def r1_verified():  # a real saved, verified script-free R1 product: only the files settle and reconstruct verify read
    store = FixtureStore()
    for asset in store.members('adapter.r1_verified'): store.materialize(asset, WORK / 'r1' / asset.split('/', 1)[1])
    return WORK / 'r1/attempt_1'


def recorded_body(url):
    if url == AMG_INDEX: return gzip.decompress((FIXTURES / 'amg_index.html.gz').read_bytes())  # checked-in copy of SEC's index page
    if not RECORDED: return None
    db = sqlite3.connect(f'file:{RECORDED}/responses.sqlite3?mode=ro', uri=True)
    row = db.execute('SELECT receipt FROM responses WHERE url=?', (url,)).fetchone(); db.close()
    return gzip.decompress((RECORDED / 'blobs' / (json.loads(row[0])['sha256'] + '.gz')).read_bytes()) if row else None


def sec_copy(url):
    c = SEC_COPIES.get(url)
    if not c: return None
    body = gzip.decompress((FIXTURES / c['file']).read_bytes())
    assert hashlib.sha256(body).hexdigest() == c['sha256']
    return body


def sender(package):  # the ONLY test double: SEC's HTTP answers, served from recorded/sealed public bytes
    def send(url, headers, *timeouts):
        body = package if url.endswith('/0001004434-23-000015.txt') else sec_copy(url) or recorded_body(url)
        return (200, {'content-length': str(len(body))}, body) if body is not None else (404, {}, b'')
    return send


def e2e_config(root, runtime=RUNTIME):
    # live=True: the Campaign calls its sender; the tests always pass the stub sender, the ONLY transport (no network)
    m = RUNTIME_MANIFEST
    return dict(output_root=str(root), campaign_dir=str(root / 'campaign'), live=True, runtime_root=str(runtime),
                runtime_manifest=dict(path=str(m), sha256=hashlib.sha256(m.read_bytes()).hexdigest()),
                browser=dict(executable=os.environ.get('ADAPTER_BROWSER_EXECUTABLE', '/opt/prepared/browser/chrome-headless-shell-linux64/chrome-headless-shell'),  # the image's qualified browser
                             sha256='22d72b589f908111fa29ff4e61ead8a0601e925177f59c70e2e851c22e9b1886', version='147.0.7727.15'),
                python=sys.executable, seconds=240, context_campaign=None, max_jobs=3)


def amg_members():
    return pf.categories(read_package(amg_version())[0])


def by(members, *cats):
    return {d['filename'] for d in members if d['category'] in cats}


class Categories(unittest.TestCase):
    def test_amg_every_member_one_category_native_document_type(self):
        m = amg_members()
        self.assertEqual(len(m), 17)
        self.assertEqual(by(m, 'html'), {'amg-20230501.htm', 'amgq12023ex991.htm', 'R1.htm'})  # XHTML iXBRL .htm (hint xml) -> html reader
        self.assertEqual(by(m, 'xml'), {'amg-20230501.xsd', 'amg-20230501_def.xml', 'amg-20230501_lab.xml', 'amg-20230501_pre.xml',
                                        'amg-20230501_htm.xml', 'FilingSummary.xml'})  # package-only XML is a target too (F2)
        self.assertEqual(by(m, 'pending'), {'courtesy.pdf', 'amglogoa78a.jpg', 'image5.jpg', 'Show.js', 'report.css', 'MetaLinks.json',
                                            'Financial_Report.xlsx', '0001004434-23-000015-xbrl.zip'})

    def test_contradicting_content_is_an_explicit_conflict(self):
        man = {'members': [{'filename': 'a.htm', 'format_hint': 'pdf'}, {'filename': 'b.txt', 'format_hint': 'html'},
                           {'filename': 'c.htm', 'format_hint': 'unknown'}, {'filename': 'd.txt', 'format_hint': 'unknown'}]}
        self.assertEqual([d['category'] for d in pf.categories(man)], ['conflict', 'conflict', 'html', 'pending'])


class Settle(unittest.TestCase):
    def test_reader_records_make_support_rest_stay_accounted(self):
        m = amg_members()
        pf.settle(m, {'rows': [{'file_id': 'R1.htm', 'outcome': V, 'attempt': str(r1_verified())}]})
        self.assertEqual(by(m, 'support'), {'report.css', 'Show.js'})  # ROUTE dependency (renderer-remap) + eligible page's own scripts
        self.assertEqual(by(m, 'owner_excluded'), {'courtesy.pdf', 'amglogoa78a.jpg', 'image5.jpg'})  # no verified reader consumed these pictures here
        self.assertEqual(by(m, 'companion_custody'), {'MetaLinks.json', 'Financial_Report.xlsx', '0001004434-23-000015-xbrl.zip'})  # owner scope
        self.assertEqual(by(m, 'unread'), set())

    def test_companion_scope_is_the_native_type_not_a_package_only_exemption(self):
        m = [dict(filename=n, sha256='x', format_hint=h, type=ty, category='pending') for n, h, ty in (
            ('ex99.txt', 'unknown', 'EX-99.1'), ('data.json', 'unknown', 'JSON'), ('book.xlsx', 'zip', 'XML'), ('Show.js', 'unknown', 'XML'))]
        pf.settle(m, {'rows': []})
        self.assertEqual([d['category'] for d in m], ['unread', 'companion_custody', 'companion_custody', 'unread'])

    def test_unverified_reader_proves_nothing(self):
        m = amg_members()
        pf.settle(m, {'rows': [{'file_id': 'R1.htm', 'outcome': 'incomplete', 'attempt': str(r1_verified())}]})
        self.assertEqual(by(m, 'support'), set()); self.assertIn('report.css', by(m, 'unread'))


class Status(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, self.dir)

    def members(self, extra=()):
        return [dict(filename='a.htm', sha256='1', format_hint='html', category='html'), dict(filename='b.xml', sha256='2', format_hint='xml', category='xml'), *extra]

    def result(self, rows, pin='P'):
        (self.dir / 'RESULT.json').write_text(json.dumps({'plan_sha256': pin, 'rows': [real(k, f, o) for k, (f, o) in enumerate(rows)]}))
        return self.dir / 'RESULT.json'

    def test_complete_needs_every_target_verified_and_nothing_unread_or_conflicting(self):
        r = self.result([('a.htm', V), ('b.xml', V)])
        self.assertEqual(pf.status(r, 'P', self.members())[0], 'complete')
        for c in ('unread', 'conflict'):
            self.assertEqual(pf.status(r, 'P', self.members([dict(filename='x', sha256='3', format_hint='unknown', category=c)]))[0], 'incomplete')
        self.assertEqual(pf.status(r, 'P', self.members([dict(filename='g.json', sha256='3', format_hint='unknown', category='pending')]))[0], 'incomplete')

    def test_clean_partial_row_is_incomplete(self):
        self.assertEqual(pf.status(self.result([('a.htm', V), ('b.xml', 'incomplete')]), 'P', self.members())[0], 'incomplete')

    def test_unfinished_or_technical_row_is_failed_not_incomplete(self):  # job.clean_row / arm_row's finished-attempt contract
        for o in ('startup_crash', None, 'technical', 'identity_mismatch'):
            st, why = pf.status(self.result([('a.htm', V), ('b.xml', o)]), 'P', self.members())
            self.assertEqual(st, 'failed', (o, why)); self.assertTrue(any(w.startswith('b.xml: ') for w in why), why)

    def test_missing_corrupt_foreign_absent_duplicate_extra_rows_fail(self):
        m = self.members
        self.assertEqual(pf.status(self.dir / 'RESULT.json', 'P', m())[0], 'failed')  # missing
        (self.dir / 'RESULT.json').write_text('{not json'); self.assertEqual(pf.status(self.dir / 'RESULT.json', 'P', m())[0], 'failed')
        self.assertEqual(pf.status(self.result([('a.htm', V), ('b.xml', V)], pin='OTHER'), 'P', m())[0], 'failed')
        self.assertEqual(pf.status(self.result([('a.htm', V)]), 'P', m())[0], 'failed')  # absent
        self.assertEqual(pf.status(self.result([('a.htm', V), ('a.htm', V), ('b.xml', V)]), 'P', m())[0], 'failed')  # duplicate
        self.assertEqual(pf.status(self.result([('a.htm', V), ('b.xml', V), ('c.htm', V)]), 'P', m())[0], 'failed')  # extra


REAL_ROWS = json.loads((HERE / 'fixtures/real_rows.json').read_text())  # saved job.py rows: the actual startup crash, a verified and a clean PARTIAL row


def real(k, f, o):  # a saved row under a test file_id: verified / clean PARTIAL / the startup crash; None = unfinished; others = native failure shapes
    if o is None: return {'ordinal': k, 'file_id': f, 'status': 'generating'}
    key = {V: 'verified', 'incomplete': 'clean_partial', 'technical': 'clean_partial', 'identity_mismatch': 'verified'}.get(o, o)
    r = dict(REAL_ROWS[key], ordinal=k, file_id=f)
    if key == 'verified': r['attempt'] = str(r1_verified())  # the saved row's own product, from the fixture store
    if o == 'technical': r['technical_failures'] = ['qualification not comparable: x']
    if o == 'identity_mismatch': r['outcome'] = 'identity_mismatch'
    return r


class Blocked(Exception): pass


def custody_only(out):  # prepare_filing up to the job launch (blocked): custody, categories, plan
    def no_job(*a, **k): raise Blocked()
    pf.subprocess.run = no_job
    try: return pf.prepare_filing(dict(AMG), e2e_config(out), sender=sender(gzip.decompress(AMG_PACKAGE.read_bytes())))
    except Blocked: return 'custody passed'
    finally: pf.subprocess.run = REAL_RUN


class ReviewFindings(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: (REAL_RUN(['chmod', '-R', 'u+w', str(self.dir)]), shutil.rmtree(self.dir)))

    def test_f1_native_disk_reserve(self):  # full_run.run's 16%, on whatever filesystem the output is
        du = shutil.disk_usage(self.dir); got = custody_only(self.dir / 'out')
        if du.free / du.total < 0.16:
            self.assertEqual(got['status'], 'failed'); self.assertIn('StorageError', got['reasons'][0])
        else:
            self.assertEqual(got, 'custody passed')

    def runtime_copy_and_run(self):
        rt = self.dir / 'runtime'; shutil.copytree(RUNTIME / 'driver', rt / 'driver', ignore=shutil.ignore_patterns('__pycache__')); REAL_RUN(['chmod', '-R', 'u+w', str(rt)], check=True)
        run = self.dir / 'run'; shutil.copytree(r1_verified(), run / 'attempt_0', symlinks=True); shutil.copytree(r1_verified().with_name('logs_1'), run / 'logs_0', symlinks=True)
        REAL_RUN(['chmod', '-R', 'u+w', str(run)], check=True)
        (run / 'RESULT.json').write_text(json.dumps({'plan_sha256': 'P', 'rows': [
            dict(ordinal=0, file_id='R1.htm', outcome=V, attempt=str(run / 'attempt_0'), source_reading={})]}))
        (run / 'PLAN.json').write_text('{}')
        sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest(); cfg = e2e_config(self.dir / 'out')
        receipt = dict(status='complete', version=str(amg_version()), runtime_manifest_sha256=cfg['runtime_manifest']['sha256'],
                       plan=dict(path=str(run / 'PLAN.json'), sha256=sha(run / 'PLAN.json')), result=dict(path=str(run / 'RESULT.json'), sha256=sha(run / 'RESULT.json')),
                       manifest=dict(path=str(amg_version() / 'manifest.json'), sha256=sha(amg_version() / 'manifest.json')))
        return rt, run, receipt, cfg

    def test_f3_cached_receipt_needs_pinned_runtime_and_every_reading(self):
        rt, run, receipt, cfg = self.runtime_copy_and_run()
        self.assertEqual(pf.reverify(dict(receipt), cfg)['status'], 'complete')  # control: real runtime, intact readings
        changed = dict(cfg, runtime_root=str(rt)); (rt / 'driver/prepare/compare.py').write_text((rt / 'driver/prepare/compare.py').read_text() + '\n# changed\n')
        r = pf.reverify(dict(receipt), changed); self.assertEqual(r['status'], 'failed'); self.assertIn('runtime file changed: driver/prepare/compare.py', r['reasons'])
        (run / 'logs_0/source_reading/R.json').write_text('{}')
        r = pf.reverify(dict(receipt), cfg); self.assertEqual(r['status'], 'failed')
        self.assertTrue(any('source_reading no longer verifies' in x for x in r['reasons']), r['reasons'])

    def test_f4_enriched_flag_alone_never_skips_a_missing_or_failed_product(self):
        self.assertFalse(pf.prepared_done({'enriched': True}))
        self.assertFalse(pf.prepared_done({'enriched': True, 'prepared_extraction': {'status': 'failed'}}))
        self.assertTrue(pf.prepared_done({'enriched': True, 'prepared_extraction': {'status': 'incomplete'}}))

    def test_f5_worker_with_its_own_driver_tree(self):  # a worker-like process that imported another driver package (this checkout's) first
        pinned = self.dir / 'pinned'; shutil.copytree(RUNTIME / 'driver', pinned / 'driver', ignore=shutil.ignore_patterns('__pycache__'))
        code = f"""
import sys, json; sys.dont_write_bytecode = True
sys.path.insert(0, {str(RUNTIME)!r}); import driver
sys.path.insert(0, {str(HERE)!r}); import test_prepared_filing as t; pf = t.pf
from pathlib import Path
try: pf.prepare_filing(dict(t.AMG), t.e2e_config(Path({str(self.dir / 'inproc')!r}), runtime=Path({str(pinned)!r}))); print('PROCEEDED')
except ImportError as e: print('REFUSED', e)
cfg = t.e2e_config(Path({str(self.dir / 'child')!r}), runtime=Path({str(pinned)!r})); cfg['live'] = False  # empty offline campaign: the child stops at custody, no job
(Path({str(self.dir)!r}) / 'cfg.json').write_text(json.dumps(cfg))
print(json.dumps(pf.pointer(dict(t.AMG), {str(self.dir / 'cfg.json')!r})))
"""
        p = REAL_RUN([sys.executable, '-B', '-c', code], capture_output=True, text=True,
                     env={'PATH': '/usr/bin:/bin', 'HOME': os.environ['HOME'], 'PYTHONDONTWRITEBYTECODE': '1'})
        lines = p.stdout.strip().splitlines()
        self.assertTrue(lines and lines[0].startswith('REFUSED driver modules not from the pinned runtime'), p.stdout + p.stderr[-500:])
        child = json.loads(lines[-1])  # the isolated pinned child used its own owners: an honest custody failure, not an import refusal
        self.assertEqual(child['status'], 'failed'); self.assertIn('OfflineCacheMiss', child['reasons'][0])

    def test_pointer_error_is_a_failed_pointer_not_a_worker_crash(self):
        p = pf.pointer(dict(AMG), '/nonexistent/adapter-config.json')
        self.assertEqual(p['status'], 'failed'); self.assertIn('FileNotFoundError', p['reasons'][0])


class Qualifications(unittest.TestCase):  # Root 6:13 PM: a configured context campaign must not silently drop job.py's automatic script qualification
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir='/dev/shm'))  # tmpfs: the native 16% reserve holds there (the root fs is below it)
        self.addCleanup(shutil.rmtree, self.dir)

    def plan(self, **extra):
        cfg = dict(e2e_config(self.dir / 'out'), **extra)
        def no_job(*a, **k): raise Blocked()
        pf.subprocess.run = no_job
        try: got = pf.prepare_filing(dict(AMG), cfg, sender=sender(gzip.decompress(AMG_PACKAGE.read_bytes())))
        except Blocked: got = None
        finally: pf.subprocess.run = REAL_RUN
        plans = list(self.dir.glob('out/runs/*/*/*/PLAN.json'))
        return got, (json.loads(plans[0].read_text()) if plans else None)

    def test_configured_qualification_store_reaches_the_plan(self):  # job.qualify_first / document.py read plan['script_qualifications']
        campaign = {'campaign': str(self.dir / 'ctx'), 'live': False, 'max_actions': 200}
        got, plan = self.plan(context_campaign=campaign, script_qualifications=str(self.dir / 'qualifications'))
        self.assertIsNone(plan); self.assertIn('not an existing folder', got['reasons'][0])  # job.claim_version never creates the store
        (self.dir / 'qualifications').mkdir()
        got, plan = self.plan(context_campaign=campaign, script_qualifications=str(self.dir / 'qualifications'))
        self.assertIsNotNone(plan, got)
        self.assertEqual((plan.get('context_campaign'), plan.get('script_qualifications')), (campaign, str(self.dir / 'qualifications')))

    def test_campaign_without_a_qualification_store_is_refused_not_silently_disabled(self):
        got, plan = self.plan(context_campaign={'campaign': str(self.dir / 'ctx'), 'live': False, 'max_actions': 200})
        self.assertIsNone(plan); self.assertEqual(got['status'], 'failed'); self.assertIn('script_qualifications', got['reasons'][0])


@unittest.skipUnless(os.environ.get('ADAPTER_E2E') == '1', 'native end-to-end event: ADAPTER_E2E=1, ADAPTER_OUT=<new folder, fs >=16% free>, ADAPTER_RECORDED, CPU allocation')
class AmgEvent(unittest.TestCase):
    def test_1_event_receipt_repeat_and_damage(self):
        root = Path(os.environ['ADAPTER_OUT']) / 'event'; package = gzip.decompress(AMG_PACKAGE.read_bytes())
        go = lambda: pf.prepare_filing(dict(AMG), e2e_config(root), sender=sender(package))
        receipt = go()
        self.assertNotEqual(receipt['status'], 'failed', receipt.get('reasons'))
        (root.parent / 'EVENT_RECEIPT_FIRST.json').write_text(json.dumps(receipt, indent=1, sort_keys=True))  # evidence before the damage controls
        result = json.loads(Path(receipt['result']['path']).read_text())
        self.assertEqual(receipt['package_sha256'], AMG_SHA)
        self.assertEqual(hashlib.sha256(Path(receipt['result']['path']).read_bytes()).hexdigest(), receipt['result']['sha256'])
        self.assertEqual(sorted(r['file_id'] for r in result['rows']), sorted(by(receipt['members'], 'html', 'xml')))  # 9 targets, whole filing
        self.assertEqual(len(receipt['members']), 17)
        self.assertEqual(by(receipt['members'], 'companion_custody'), {'MetaLinks.json', 'Financial_Report.xlsx', '0001004434-23-000015-xbrl.zip'})
        self.assertEqual(receipt['status'] == 'complete', all(r['outcome'] == V for r in result['rows']) and not by(receipt['members'], 'unread', 'conflict'))
        self.assertEqual(go(), receipt)  # repeat event: native re-verification passes, same receipt, no new job folder
        self.assertEqual(len(list(root.glob('runs/*/*/*/job_*/'))), 1)
        cfg, job = e2e_config(root), Path(receipt['result']['path']).parent

        def clone(name):  # a whole copy of the job folder whose RESULT names the clone's own attempts: the positive product stays intact
            dst = root.parent / 'damage_clones' / name / job.name; shutil.copytree(job, dst, symlinks=True)
            res = json.loads((dst / 'RESULT.json').read_text())
            for r in res['rows']: r['attempt'] = str(dst / Path(r['attempt']).name)
            (dst / 'RESULT.json').write_text(json.dumps(res, indent=1))
            return dict(receipt, result=dict(path=str(dst / 'RESULT.json'), sha256=hashlib.sha256((dst / 'RESULT.json').read_bytes()).hexdigest())), dst

        c, d = clone('control_undamaged'); self.assertEqual(pf.reverify(c, cfg)['status'], receipt['status'])  # control: a clone verifies like the original
        first = next(r for r in result['rows'] if r['outcome'] == V)
        c, d = clone('readback_damaged'); (d / ('logs_' + Path(first['attempt']).name.split('_', 1)[1]) / 'R.json').write_text('{}')
        damaged = pf.reverify(c, cfg)
        self.assertEqual(damaged['status'], 'failed'); self.assertTrue(any('no longer verifies' in x for x in damaged['reasons']), damaged['reasons'])
        c, d = clone('result_missing'); (d / 'RESULT.json').unlink()
        self.assertEqual(pf.reverify(c, cfg)['status'], 'failed')
        self.assertEqual(go(), receipt)  # the positive product is still intact after the damage clones

    def test_2_interrupted_run_folder_kept_new_job_folder_used(self):  # a SECOND whole-filing job run: needs its own allocation
        root = Path(os.environ['ADAPTER_OUT']) / 'interrupted'; package = gzip.decompress(AMG_PACKAGE.read_bytes())
        first = pf.prepare_filing(dict(AMG), e2e_config(root), sender=sender(package))
        run = Path(first['plan']['path']).parent
        (run / 'RECEIPT.json').rename(run / 'RECEIPT.interrupted-test.json')  # as if the caller died after job.py, before its receipt
        second = pf.prepare_filing(dict(AMG), e2e_config(root), sender=sender(package))
        self.assertTrue((run / 'job_0' / 'RESULT.json').exists()); self.assertTrue((run / 'job_1' / 'RESULT.json').exists())
        self.assertEqual(second['result']['path'], str(run / 'job_1' / 'RESULT.json'))

    def test_3_missing_package_fails_without_a_job(self):
        root = Path(os.environ['ADAPTER_OUT']) / 'missing'
        receipt = pf.prepare_filing(dict(AMG), e2e_config(root), sender=lambda url, *a: (404, {}, b''))
        self.assertEqual(receipt['status'], 'failed'); self.assertFalse((root / 'runs').exists())


class FakeJob:  # stands in for the pinned job.py child ONLY: writes job.py's RESULT shape (saved real rows) for the plan's targets
    def __init__(self, script): self.script, self.launched = list(script), []
    def __call__(self, argv, **k):
        if not str(argv[4]).endswith('job.py'): return REAL_RUN(argv, **k)  # reconstruct verify etc. stay real
        plan, pin, jobdir = Path(argv[5]), argv[6], Path(argv[7]); self.launched.append(jobdir.name); kind = self.script.pop(0)
        jobdir.mkdir(mode=0o700)
        ids = [c['file_id'] for c in json.loads(plan.read_text())['source_commands']]
        rows = [real(n, f, None if kind == 'interrupt' else V if kind == 'verified' or n else kind) for n, f in enumerate(ids)]  # one row of each job carries the kind
        (jobdir / 'RESULT.json').write_text(json.dumps({'plan_sha256': pin, 'rows': rows}))
        if kind == 'interrupt': raise KeyboardInterrupt('worker pod stopped mid-job')
        return subprocess.CompletedProcess(argv, 0 if kind == 'verified' else 1)


class Recovery(unittest.TestCase):  # Root 8:28 PM: bounded automatic recovery inside the existing caller, no new queue
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir='/dev/shm'))  # tmpfs: the native 16% reserve holds there (the root fs is below it)
        self.addCleanup(lambda: (REAL_RUN(['chmod', '-R', 'u+w', str(self.dir)]), shutil.rmtree(self.dir)))

    def event(self, script):
        job = FakeJob(script); pf.subprocess.run = job
        try: return pf.prepare_filing(dict(AMG), e2e_config(self.dir), sender=sender(gzip.decompress(AMG_PACKAGE.read_bytes()))), job.launched
        finally: pf.subprocess.run = REAL_RUN

    def run_dir(self): return next((self.dir / 'runs').glob('*/*/*'))

    def test_startup_crash_is_recovered_automatically_and_the_failed_job_is_kept(self):
        r, launched = self.event(['startup_crash', 'verified'])
        self.assertEqual((r['status'], launched), ('complete', ['job_0', 'job_1']), r['reasons'])
        old = json.loads((self.run_dir() / 'job_0.receipt.json').read_text())
        self.assertEqual(old['status'], 'failed'); self.assertTrue(any('generation_failed' in w for w in old['reasons']), old['reasons'])
        self.assertTrue((self.run_dir() / 'job_0/RESULT.json').exists())

    def test_persistent_failure_stops_at_the_cap_and_stays_failed(self):
        r, launched = self.event(['startup_crash'] * 5)
        self.assertEqual((r['status'], launched), ('failed', ['job_0', 'job_1', 'job_2']))
        r, launched = self.event([]); self.assertEqual((r['status'], launched), ('failed', []))  # repeat event at the cap: no extra job

    def test_clean_partial_and_verified_are_final_no_retry_no_repeat_job(self):
        r, launched = self.event(['incomplete']); self.assertEqual((r['status'], launched), ('incomplete', ['job_0']))
        r, launched = self.event([]); self.assertEqual((r['status'], launched), ('incomplete', []))

    def test_cached_complete_repeat_no_job_and_corrupt_saved_output_never_credited(self):
        r, launched = self.event(['verified']); self.assertEqual((r['status'], launched), ('complete', ['job_0']))
        r, launched = self.event([]); self.assertEqual((r['status'], launched), ('complete', []))
        res = self.run_dir() / 'job_0/RESULT.json'; res.write_text(res.read_text().replace('"incomplete"', '"verified_saved_output"') + ' ')
        r, launched = self.event([]); self.assertEqual((r['status'], launched), ('failed', [])); self.assertIn('result: missing or changed', r['reasons'])

    def test_interrupted_job_counts_and_the_restart_uses_a_new_job_folder(self):
        with self.assertRaises(KeyboardInterrupt): self.event(['interrupt'])
        self.assertFalse((self.run_dir() / 'RECEIPT.json').exists())
        r, launched = self.event(['verified']); self.assertEqual((r['status'], launched), ('complete', ['job_1']))
        self.assertTrue((self.run_dir() / 'job_0/RESULT.json').exists())


if __name__ == '__main__':
    unittest.main()
