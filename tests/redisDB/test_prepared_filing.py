"""Adapter tests (redisDB/prepared_filing.py). Pure tests: the real public AMG package, its SEC copies and index page (tests/driver/prepare/get/fixtures),
a real saved verified R1 product (fixture store group adapter.r1_verified) and saved job.py rows (fixtures/real_rows.json); the Root code-review findings
F1-F5 each have one test. The runtime under test is this checkout with its deployed runtime manifest (k8s/prepared-extraction/RUNTIME_MANIFEST.json,
or ADAPTER_RUNTIME_MANIFEST). Needs PREPARE_TEST_DATA (tests/driver/prepare/README.md).
The end-to-end event runs only with ADAPTER_E2E=1, ADAPTER_OUT=<new folder on a filesystem with >=16% free> and ADAPTER_RECORDED=<recorded SEC
responses: responses.sqlite3 + blobs> (pinned job.py: 3 browser rows)."""
import atexit, copy, functools, gzip, hashlib, json, os, shutil, sqlite3, subprocess, sys, tempfile, unittest
from unittest.mock import patch
from types import SimpleNamespace
from pathlib import Path

sys.dont_write_bytecode = True  # never write caches into the runtime tree
HERE = Path(__file__).resolve().parent
RUNTIME = HERE.parents[1]  # this checkout
RUNTIME_MANIFEST = Path(os.environ.get('ADAPTER_RUNTIME_MANIFEST', RUNTIME / 'k8s/prepared-extraction/RUNTIME_MANIFEST.json'))
sys.path.insert(0, str(RUNTIME))
from redisDB import prepared_filing as pf
from driver.prepare.get.acquire import acquire, read_package, StorageError
from driver.prepare.get import archive
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
    return gzip.decompress((Path(RECORDED) / 'blobs' / (json.loads(row[0])['sha256'] + '.gz')).read_bytes()) if row else None


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


def pointer_reply(root, receipt, filing=AMG):
    """Only the child transport is replaced; pointer reads the producer's actual saved bytes."""
    config = root / 'pointer-config.json'
    config.write_text(json.dumps(dict(python=sys.executable)))
    child = subprocess.CompletedProcess([], 0, json.dumps(receipt), '')
    with patch.object(pf.subprocess, 'run', return_value=child):
        return pf.pointer(filing, config)


class Pointer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.saved = self.root / 'RECEIPT.json'
        # Real AMG receipt from the retained November 1 live-filing proof. Only
        # its plan locator is relocated, in BOTH the saved and returned objects.
        self.receipt = json.loads((HERE / 'fixtures/real_receipt.json').read_bytes())
        self.receipt['plan']['path'] = str(self.root / 'PLAN.json')
        self.body = (json.dumps(self.receipt) + '\n').encode()
        self.saved.write_bytes(self.body)

    def call(self, receipt=None):
        return pointer_reply(self.root, self.receipt if receipt is None else receipt)

    def failed(self, receipt):
        got = self.call(receipt)
        self.assertEqual(got['status'], 'failed', got)
        self.assertFalse(pf.prepared_done(dict(prepared_extraction=got)))
        self.assertTrue(all(isinstance(reason, str) for reason in got['reasons']))

    def test_real_saved_success_read_once_and_optional_byte_pin(self):
        for explicit, pin in ((False, False), (True, False), (True, True)):
            with self.subTest(explicit=explicit, pin=pin):
                receipt = copy.deepcopy(self.receipt)
                if explicit:
                    receipt['saved_receipt'] = dict(path=str(self.saved))
                    if pin: receipt['saved_receipt']['sha256'] = hashlib.sha256(self.body).hexdigest()
                reads = []; native = Path.read_bytes
                def read(path):
                    if path == self.saved: reads.append(path)
                    return native(path)
                with patch.object(Path, 'read_bytes', read): got = self.call(receipt)
                self.assertEqual(got['status'], 'complete')
                self.assertEqual(got['receipt'], dict(path=str(self.saved), sha256=hashlib.sha256(self.body).hexdigest()))
                self.assertEqual(reads, [self.saved])
        self.saved.write_text(json.dumps(self.receipt, indent=4))
        self.assertEqual(self.call()['status'], 'complete')  # equivalent JSON, no supplied byte pin

    def test_valid_reclassification_reasons_and_failed_without_receipt(self):
        for stored, returned in (('complete', 'incomplete'), ('incomplete', 'complete')):
            self.saved.write_text(json.dumps(dict(self.receipt, status=stored)))
            receipt = dict(self.receipt, status=returned, reasons=['rechecked'] * 23, members=[])
            got = self.call(receipt)
            self.assertEqual((got['status'], got['reasons']), (returned, ['rechecked'] * 20))
        receipt = dict(self.receipt); receipt.pop('reasons')
        self.assertEqual(self.call(receipt)['reasons'], [])
        for receipt in (dict(status='failed', reasons=['no package']), dict(self.receipt, status='failed')):
            self.saved.unlink(missing_ok=True)
            got = self.call(receipt)
            self.assertEqual((got['status'], got['receipt']), ('failed', None))

    def test_malformed_child_consumed_fields_fail(self):
        for value in ([], 'bad', 7, True, {}, dict(status='complete'), dict(status='incomplete')):
            with self.subTest(value=value): self.failed(value)
        for key, values in (
                ('status', [None, [], 'done']), ('reasons', [None, {}, 'error', [7]]),
                ('plan', [None, {}, [], 'PLAN', dict(path={}), dict(path='')]),
                ('saved_receipt', [None, {}, [], 'RECEIPT', dict(path={}), dict(path='')])):
            for value in values:
                with self.subTest(key=key, value=value): self.failed(dict(self.receipt, **{key: value}))

    def test_bad_declared_pin_fails(self):
        for pin in (None, '', [], 'bad', '0' * 64):
            with self.subTest(pin=pin):
                self.failed(dict(self.receipt, saved_receipt=dict(path=str(self.saved), sha256=pin)))

    def test_receipt_read_failure_stays_inside_boundary(self):
        native = Path.read_bytes
        for kind in (FileNotFoundError, PermissionError, IsADirectoryError):
            def read(path):
                if path == self.saved: raise kind('controlled receipt read failure')
                return native(path)
            with self.subTest(kind=kind), patch.object(Path, 'read_bytes', read): self.failed(self.receipt)
        self.saved.unlink()
        self.failed(self.receipt)

    def test_receipt_content_and_each_identity_reference_must_agree(self):
        for body in (b'', b'{bad', b'[]', b'null', b'7'):
            self.saved.write_bytes(body)
            with self.subTest(body=body): self.failed(self.receipt)
        keys = ('schema', 'accession', 'cik', 'form', 'package_sha256', 'runtime_manifest_sha256',
                'version', 'manifest', 'plan', 'result')
        for key in keys:
            for missing in (False, True):
                saved = copy.deepcopy(self.receipt)
                if missing: saved.pop(key)
                else: saved[key] = 'foreign'
                self.saved.write_text(json.dumps(saved))
                with self.subTest(key=key, missing=missing): self.failed(self.receipt)
        for status in ('failed', 'unknown', None):
            self.saved.write_text(json.dumps(dict(self.receipt, status=status)))
            with self.subTest(status=status): self.failed(self.receipt)
        self.saved.write_bytes(self.body)
        for key in ('accessionNo', 'cik', 'formType'):
            got = pointer_reply(self.root, self.receipt, dict(AMG, **{key: 'foreign'}))
            self.assertEqual(got['status'], 'failed')

    def test_child_exit_bad_output_config_and_cancellation(self):
        cfg = self.root / 'config.json'; cfg.write_text(json.dumps(dict(python=sys.executable)))
        for code, body in ((1, '{}'), (0, ''), (0, 'invalid'), (0, 'null')):
            with self.subTest(code=code, body=body), patch.object(pf.subprocess, 'run', return_value=subprocess.CompletedProcess([], code, body, 'failure')):
                self.assertEqual(pf.pointer(AMG, cfg)['status'], 'failed')
        self.assertEqual(pf.pointer(AMG, self.root / 'missing')['status'], 'failed')
        for kind in (KeyboardInterrupt, SystemExit):
            with patch.object(pf.subprocess, 'run', side_effect=kind), self.assertRaises(kind): pf.pointer(AMG, cfg)


class RecordedTransport(unittest.TestCase):
    def test_recorded_response_folder_accepts_the_environment_string_and_a_path(self):
        body = b'independent recorded SEC transport control'
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root / 'blobs').mkdir(); pin = hashlib.sha256(body).hexdigest()
            (root / 'blobs' / (pin + '.gz')).write_bytes(gzip.compress(body))
            with sqlite3.connect(root / 'responses.sqlite3') as db:
                db.execute('CREATE TABLE responses (url TEXT, receipt TEXT)')
                db.execute('INSERT INTO responses VALUES (?, ?)', ('https://recorded.invalid/found', json.dumps(dict(sha256=pin))))
            for folder in (str(root), root):
                with self.subTest(folder=type(folder).__name__), patch(__name__ + '.RECORDED', folder):
                    self.assertEqual(recorded_body('https://recorded.invalid/found'), body)
                    self.assertIsNone(recorded_body('https://recorded.invalid/absent'))
            with patch(__name__ + '.RECORDED', None): self.assertIsNone(recorded_body('https://recorded.invalid/found'))


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


class ReceiptDurability(unittest.TestCase):
    def test_file_flush_failure_does_not_publish_or_replace_a_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / 'RECEIPT.json'
            pf._save(target, dict(status='original'))
            with patch.object(pf.os, 'fsync', side_effect=OSError('controlled file flush failure')):
                with self.assertRaises(OSError): pf._save(target, dict(status='changed'))
            self.assertEqual(json.loads(target.read_bytes()), dict(status='original'))
            pf._save(target, dict(status='changed'))
            self.assertEqual(json.loads(target.read_bytes()), dict(status='changed'))

    def test_directory_flush_failure_is_never_success(self):
        from driver.prepare.get.acquire import StorageError
        import stat
        sync = os.fsync
        def fail_directory(fd):
            if stat.S_ISDIR(os.fstat(fd).st_mode): raise OSError('controlled directory flush failure')
            sync(fd)
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / 'RECEIPT.json'
            with patch.object(pf.os, 'fsync', side_effect=fail_directory):
                with self.assertRaises(StorageError): pf._save(target, dict(status='complete'))
            pf._save(target, dict(status='complete'))
            self.assertEqual(json.loads(target.read_bytes()), dict(status='complete'))

    def test_new_receipt_directories_are_synced_before_publication(self):
        from driver.prepare.get.acquire import StorageError
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / 'ocr' / 'receipts' / 'RECEIPT.json'
            with patch.object(pf.os, 'fsync', side_effect=OSError('controlled parent flush failure')):
                with self.assertRaises(StorageError): pf._save(target, dict(status='complete'))
            self.assertFalse(target.exists())
            pf._save(target, dict(status='complete'))
            self.assertEqual(json.loads(target.read_bytes()), dict(status='complete'))


class OcrExtension(unittest.TestCase):
    def setUp(self):
        space = patch.object(shutil, 'disk_usage', return_value=SimpleNamespace(total=10_000_000_000, used=4_000_000_000, free=6_000_000_000))
        space.start(); self.addCleanup(space.stop)  # independent ample-space control for these small temporary reader fixtures
        from tests.driver.prepare.pictures.test_saved import SavedPictures
        from tests.driver.prepare.pictures.test_join import fakes
        self.fixture = SavedPictures(); self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        self.receipt = self.fixture.filing()
        from tests.driver.prepare.get.test_acquire import ACCESSION, CIK, FORM
        self.receipt.update(schema='prepared-filing-receipt/2', accession=ACCESSION, cik=str(CIK), form=FORM)
        self.receipt['members'] = pf.categories(read_package(self.receipt['version'])[0])
        pf.settle(self.receipt['members'], json.loads(Path(self.receipt['result']['path']).read_bytes()))
        self.makers = fakes(self.fixture.calls, html='<div data-bbox="0 0 1000 1000" data-label="Text"><p>FAKE</p></div>')
        self.config = dict(runtime_root=str(RUNTIME), python=sys.executable,
                           ocr=dict(endpoint='http://unused.invalid/v1', identity=dict(model='control'), seconds=60))

    def test_low_space_stops_before_ocr_config_or_writing_child(self):
        low = SimpleNamespace(total=10_000_000_000, used=9_999_000_000, free=1_000_000)
        with patch.object(shutil, 'disk_usage', return_value=low), patch.object(pf.subprocess, 'run', side_effect=self.child) as child:
            with self.assertRaises(StorageError): pf.with_ocr(self.receipt, self.config)
            child.assert_not_called()
        self.assertEqual(self.fixture.calls, [])
        self.assertFalse(list(self.fixture.root.glob('OCR_CONFIG_*.json')))
        self.assertFalse((self.fixture.root / 'ocr').exists())

    def test_space_failure_between_ocr_attempts_is_not_a_model_error_or_retry(self):
        calls = []
        def child(*args, **kwargs): calls.append(1); raise RuntimeError('controlled first child failure')
        def space(_):
            free = 1_000_000 if calls else 5_000_000_000
            return SimpleNamespace(total=10_000_000_000, used=10_000_000_000-free, free=free)
        with patch.object(shutil, 'disk_usage', side_effect=space), patch.object(pf.subprocess, 'run', side_effect=child):
            with self.assertRaises(StorageError): pf.with_ocr(self.receipt, self.config)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.fixture.calls, [])

    def test_identical_ocr_aggregate_reuse_requires_parent_flush(self):
        sync = os.fsync
        def fail_receipts(fd):
            path = Path(os.readlink(f'/proc/self/fd/{fd}'))
            if path.is_dir() and path.name == 'receipts': raise OSError('controlled aggregate parent flush failure')
            sync(fd)
        with patch.object(pf.subprocess, 'run', side_effect=self.child):
            for _ in range(2):
                with patch.object(os, 'fsync', side_effect=fail_receipts):
                    with self.assertRaises(StorageError): pf.with_ocr(self.receipt, self.config)
            result = pf.with_ocr(self.receipt, self.config)
        self.assertEqual(result['status'], 'complete')
        self.assertTrue(Path(result['saved_receipt']['path']).is_file())

    def child(self, argv, **kwargs):
        from driver.prepare.pictures import saved
        self.assertIn('driver.prepare.pictures.saved', argv)
        receipt = json.loads(kwargs['input'])
        reference = saved.run(receipt, json.loads(Path(argv[-2]).read_text()), argv[-1], self.makers)
        return SimpleNamespace(returncode=0, stdout=json.dumps(reference)+'\n', stderr='')

    def test_enabled_ocr_is_source_bound_unverified_and_reuses_reader_results(self):
        original = json.dumps(self.receipt, sort_keys=True)
        with patch.object(pf.subprocess, 'run', side_effect=self.child):
            result = pf.with_ocr(self.receipt, self.config)
            again = pf.with_ocr(self.receipt, self.config)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual((result['fidelity'], result['ocr']['fidelity']), ('unverified', 'unverified'))
        self.assertEqual(len(self.fixture.calls), 3)
        self.assertEqual(result, again)
        self.assertEqual(json.dumps(self.receipt, sort_keys=True), original)
        filing = dict(accessionNo=result['accession'], cik=result['cik'], formType=result['form'])
        got = pointer_reply(self.fixture.root, result, filing)
        self.assertEqual((got['status'], got['receipt'], got['fidelity']), ('complete', result['saved_receipt'], 'unverified'))
        self.assertEqual(got['ocr'], result['ocr'])
        for key, value in (('ocr', {}), ('extraction_status', 'incomplete'), ('extraction_status', None), ('status', 'incomplete')):
            with self.subTest(key=key):
                self.assertEqual(pointer_reply(self.fixture.root, dict(result, **{key: value}), filing)['status'], 'failed')
        missing = dict(result); missing.pop('extraction_status')
        self.assertEqual(pointer_reply(self.fixture.root, missing, filing)['status'], 'failed')
        self.assertTrue(Path(result['saved_receipt']['path']).is_file())

    def test_unconsumed_picture_is_explicitly_unread_with_ocr_enabled(self):
        self.receipt['members'].append(dict(filename='unbound.png', sha256='1'*64, format_hint='png', category='owner_excluded'))
        with patch.object(pf.subprocess, 'run', side_effect=self.child): result = pf.with_ocr(self.receipt, self.config)
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(result['members'][-1]['category'], 'unread')
        self.assertTrue(any('unbound.png' in reason for reason in result['reasons']))
        filing = dict(accessionNo=result['accession'], cik=result['cik'], formType=result['form'])
        got = pointer_reply(self.fixture.root, result, filing)
        self.assertEqual((got['status'], got['fidelity'], got['receipt']), ('incomplete', 'unverified', result['saved_receipt']))

    def test_transient_ocr_failure_retries_only_failed_reader_without_html_rerun(self):
        reader = self.makers['chandra'](); normal = reader.read; attempts = []
        def read(data):
            attempts.append(1)
            if len(attempts) == 1: raise RuntimeError('controlled transient OCR outage')
            return normal(data)
        reader.read = read; self.makers['chandra'] = lambda: reader
        with patch.object(pf.subprocess, 'run', side_effect=self.child) as child, patch.object(pf, '_job', side_effect=AssertionError('HTML rerun')):
            result = pf.with_ocr(self.receipt, self.config)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual((child.call_count, len(attempts)), (2, 2))
        self.assertEqual([role for role, _ in self.fixture.calls], ['pp', 'ox', 'chandra'])
        old = [json.loads(p.read_bytes()) for p in (self.fixture.root / 'ocr/receipts').glob('*.json')]
        self.assertEqual(sorted(r['status'] for r in old), ['complete', 'failed'])

    def test_persistent_ocr_failure_stops_after_exactly_three_attempts(self):
        reader = self.makers['chandra'](); attempts = []
        def read(_): attempts.append(1); raise RuntimeError('controlled persistent OCR outage')
        reader.read = read; self.makers['chandra'] = lambda: reader
        with patch.object(pf.subprocess, 'run', side_effect=self.child) as child, patch.object(pf, '_job', side_effect=AssertionError('HTML rerun')):
            result = pf.with_ocr(self.receipt, self.config)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual((child.call_count, len(attempts)), (3, 3))
        self.assertEqual([role for role, _ in self.fixture.calls], ['pp', 'ox'])

    def test_budget_counts_unique_html_inputs_and_native_pdf_pages_without_rendering(self):
        from tests.driver.prepare.pictures.test_saved import SavedPictures
        from tests.driver.prepare.pictures.test_pdf import made
        from tests.driver.prepare.get.test_acquire import uu
        from driver.prepare.pictures import pdf
        self.assertEqual(pf._ocr_seconds(self.receipt, dict(seconds=60, timeout=10)), 70)  # two occurrences, one input
        fixture = SavedPictures(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        raw = made((100, 100), (200, 100), (300, 100))
        receipt = fixture.filing([('three-pages.pdf', uu(raw, 'three-pages.pdf'), 'EX-99', '3', None)])
        with patch.object(pdf, 'pages', side_effect=AssertionError('budget rerendered PDF')):
            self.assertEqual(pf._ocr_seconds(receipt, dict(seconds=60, timeout=10)), 100)  # one input + three native pages
        for bad in (dict(seconds=0), dict(seconds='60'), dict(timeout=0), dict(timeout=float('inf'))):
            with self.subTest(bad=bad), self.assertRaises(ValueError): pf._ocr_seconds(receipt, bad)

    def test_missing_child_result_is_failed_and_no_ocr_config_keeps_original_path(self):
        self.assertIs(pf.with_ocr(self.receipt, {}), self.receipt)
        with patch.object(pf.subprocess, 'run', return_value=SimpleNamespace(returncode=124, stdout='', stderr='bounded stop')):
            result = pf.with_ocr(self.receipt, self.config)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['fidelity'], 'unverified')

    def test_config_flush_failure_never_starts_child_or_credits_an_ocr_result(self):
        sync = os.fsync
        def fail_config(fd):
            if Path(os.readlink(f'/proc/self/fd/{fd}')).name.startswith('OCR_CONFIG_'):
                raise OSError('controlled OCR configuration flush failure')
            sync(fd)
        with patch.object(pf.subprocess, 'run') as child, patch.object(pf.os, 'fsync', side_effect=fail_config):
            with self.assertRaises(OSError): pf.with_ocr(self.receipt, self.config)
            child.assert_not_called()
        self.assertFalse(list(self.fixture.root.glob('ocr/receipts/*.json')))
        with patch.object(pf.subprocess, 'run', side_effect=self.child): result = pf.with_ocr(self.receipt, self.config)
        self.assertEqual(result['status'], 'complete')

    def test_real_saved_wrong_ratio_suffix_is_preserved_and_never_certified(self):
        from tests.driver.prepare.pictures.test_saved import SavedPictures
        from tests.driver.prepare.pictures.saved import Saved
        from driver.prepare.pictures import readers, saved
        fixture = SavedPictures(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        source = Saved(fixture.root)
        row = next(r for r in source.records if r['name'] == '157_0001558370-25-005434_dlr-20250424xex99d2g026.jpg')
        _, picture, raw, tokens, free, _ = source.inputs(row)
        fixture.image = Path(picture).read_bytes()
        self.fixture = fixture
        self.receipt = fixture.filing()
        self.receipt['members'] = pf.categories(read_package(self.receipt['version'])[0])
        pf.settle(self.receipt['members'], json.loads(Path(self.receipt['result']['path']).read_bytes()))
        self.makers = dict(chandra=lambda: SimpleNamespace(
            settings=dict(reader='saved-original-157', max_tokens=readers.MAX_TOKENS),
            status=readers._chandra_status, read=lambda _: [raw, dict(generation_tokens=tokens)]))
        for role in ('pp', 'ox'):
            self.makers[role] = lambda role=role: SimpleNamespace(
                settings=dict(reader='saved-original-157-' + role), status=readers._free_status,
                read=lambda _: dict(w=free['w'], h=free['h'], boxes=free[role]))
        # Independently reviewed original image says 5.1x; the frozen OCR wrote 5.1%. Preserve the error, never silently repair it.
        self.assertIn('5.1%', raw)
        with patch.object(pf.subprocess, 'run', side_effect=self.child): result = pf.with_ocr(self.receipt, self.config)
        report = saved.verify(result['ocr'], self.receipt)
        self.assertEqual((result['fidelity'], report['fidelity']), ('unverified', 'unverified'))
        for picture in report['documents'][0]['pictures']:
            self.assertEqual(saved._restore(picture['records']['chandra'])['result'][0], raw)
            self.assertIn('5.1%', picture['packet'])
            self.assertIn('unverified', picture['packet'])

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
        self.assertEqual(pointer_reply(root, receipt)['status'], receipt['status'])
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
        c, d = clone('readback_damaged')
        logical = d / ('logs_' + Path(first['attempt']).name.split('_', 1)[1]) / 'R.json'; stored = archive.record_path(logical)
        self.assertEqual(stored.name, 'R.json.gz'); stored.write_bytes(gzip.compress(b'{}', mtime=0))
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

    def test_plan_flush_failure_never_launches_a_job_or_saves_a_success(self):
        sync = os.fsync
        def fail_plan(fd):
            if Path(os.readlink(f'/proc/self/fd/{fd}')).name == 'PLAN.json.pending':
                raise OSError('controlled extraction plan flush failure')
            sync(fd)
        with patch.object(pf.os, 'fsync', side_effect=fail_plan):
            with self.assertRaises(OSError): self.event(['verified'])
        self.assertFalse(list(self.dir.glob('runs/*/*/*/job_*')))
        self.assertFalse(list(self.dir.glob('runs/*/*/*/RECEIPT.json')))
        receipt, launched = self.event(['verified'])
        self.assertEqual((receipt['status'], launched), ('complete', ['job_0']))

    def test_retry_sentinel_flush_failure_never_launches_or_acknowledges_a_job(self):
        sync = os.fsync
        def fail_sentinel(fd):
            if Path(os.readlink(f'/proc/self/fd/{fd}')).name == 'job_0.stdout':
                raise OSError('controlled retry sentinel flush failure')
            sync(fd)
        with patch.object(os, 'fsync', side_effect=fail_sentinel):
            with self.assertRaises(OSError): self.event(['verified'])
        run = self.run_dir()
        self.assertFalse((run / 'job_0').exists())
        self.assertFalse((run / 'RECEIPT.json').exists())
        receipt, launched = self.event(['verified'])
        self.assertEqual((receipt['status'], launched), ('complete', ['job_1']))

    def test_published_receipt_reuse_requires_successful_parent_flush(self):
        sync = os.fsync
        def fail_receipt_parent(fd):
            path = Path(os.readlink(f'/proc/self/fd/{fd}'))
            if path.is_dir() and (path / 'RECEIPT.json').is_file(): raise OSError('controlled receipt parent flush failure')
            sync(fd)
        with patch.object(os, 'fsync', side_effect=fail_receipt_parent):
            with self.assertRaises(StorageError): self.event(['verified'])
        self.assertEqual(json.loads((self.run_dir() / 'RECEIPT.json').read_bytes())['status'], 'complete')
        with patch.object(os, 'fsync', side_effect=fail_receipt_parent):
            with self.assertRaises(StorageError): self.event([])
        receipt, launched = self.event([])
        self.assertEqual((receipt['status'], launched), ('complete', []))

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
        saved = self.run_dir() / 'RECEIPT.json'; original = saved.read_bytes()
        for old, current in (('incomplete', 'complete'), ('complete', 'incomplete')):
            saved.write_text(json.dumps(dict(r, status=old, reasons=['old policy'], members=[])))
            before = saved.read_bytes()
            # Real repeat/reverify branch; the status seam represents a changed
            # current policy. It must not require rewriting the old receipt.
            with patch.object(pf, 'status', return_value=(current, ['current policy'])):
                fresh, launched = self.event([])
            self.assertEqual((fresh['status'], launched, saved.read_bytes()), (current, [], before))
            self.assertNotEqual(fresh['members'], [])
            got = pointer_reply(self.dir, fresh)
            self.assertEqual((got['status'], got['reasons']), (current, ['current policy']))
        saved.write_bytes(original)
        res = self.run_dir() / 'job_0/RESULT.json'; res.write_text(res.read_text().replace('"incomplete"', '"verified_saved_output"') + ' ')
        r, launched = self.event([]); self.assertEqual((r['status'], launched), ('failed', [])); self.assertIn('result: missing or changed', r['reasons'])

    def test_interrupted_job_counts_and_the_restart_uses_a_new_job_folder(self):
        with self.assertRaises(KeyboardInterrupt): self.event(['interrupt'])
        self.assertFalse((self.run_dir() / 'RECEIPT.json').exists())
        r, launched = self.event(['verified']); self.assertEqual((r['status'], launched), ('complete', ['job_1']))
        self.assertTrue((self.run_dir() / 'job_0/RESULT.json').exists())


class CachedReserve(unittest.TestCase):
    """Real cached SEC package/responses must not bypass the native work reserve."""
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='cached_reserve_', dir='/dev/shm'))
        self.addCleanup(lambda: (REAL_RUN(['chmod', '-R', 'u+w', str(self.root)]), shutil.rmtree(self.root)))
        self.send = sender(gzip.decompress(AMG_PACKAGE.read_bytes()))
        self.calls = []

    def invoke(self, root, free):
        class ReachedJob(Exception): pass
        def send(*args, **kwargs): self.calls.append(args[0]); return self.send(*args, **kwargs)
        with patch.object(shutil, 'disk_usage', return_value=SimpleNamespace(total=10_000_000_000, used=10_000_000_000-free, free=free)), patch.object(pf, '_job', side_effect=ReachedJob) as child:
            try: result = pf.prepare_filing(dict(AMG), e2e_config(root), sender=send)
            except ReachedJob: result = 'job reached'
            finally: self.job_called = child.called
        return result

    def test_cached_package_requires_reserve_before_new_job(self):
        root = self.root / 'warm'
        self.assertEqual(self.invoke(root, 5_000_000_000), 'job reached')
        self.assertTrue(self.calls)
        self.calls.clear()
        self.assertEqual(self.invoke(root, 1_600_000_000), 'job reached')  # the native check accepts the exact reserve boundary
        with self.assertRaises(StorageError): self.invoke(root, 1_000_000)
        self.assertFalse(self.job_called)
        self.assertEqual(self.calls, [])
        self.assertFalse(list(root.glob('runs/*/*/*/job_*.stdout')))

    def test_cold_low_space_stops_and_ample_space_is_the_positive_control(self):
        root = self.root / 'cold'
        self.assertEqual(self.invoke(root, 1_000_000)['status'], 'failed')
        self.assertFalse(self.job_called)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.invoke(root, 5_000_000_000), 'job reached')

    def test_low_space_keeps_read_only_verified_receipt_reuse_available(self):
        root = self.root / 'saved'; config = e2e_config(root)
        for free, script in ((5_000_000_000, ['verified']), (1_000_000, [])):
            child = FakeJob(script)
            with patch.object(shutil, 'disk_usage', return_value=SimpleNamespace(total=10_000_000_000, used=10_000_000_000-free, free=free)), patch.object(pf.subprocess, 'run', child):
                receipt = pf.prepare_filing(dict(AMG), config, sender=self.send)
            self.assertEqual(receipt['status'], 'complete', receipt.get('reasons'))
            self.assertEqual(child.launched, ['job_0'] if script else [])

    def test_space_is_checked_again_before_a_new_job_retry(self):
        child = FakeJob(['startup_crash', 'verified'])
        def space(_):
            free = 1_000_000 if child.launched else 5_000_000_000
            return SimpleNamespace(total=10_000_000_000, used=10_000_000_000-free, free=free)
        with patch.object(shutil, 'disk_usage', side_effect=space), patch.object(pf.subprocess, 'run', child):
            with self.assertRaises(StorageError): pf.prepare_filing(dict(AMG), e2e_config(self.root / 'retry'), sender=self.send)
        self.assertEqual(child.launched, ['job_0'])
        self.assertFalse(list(self.root.glob('retry/runs/*/*/*/job_1.stdout')))


if __name__ == '__main__':
    unittest.main()
