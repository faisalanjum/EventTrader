"""One arriving filing's metadata -> its prepared-extraction receipt, through the existing pinned owners only.

Custody: get.full_run._filing (verified package + SEC index comparison) under full_run.run's own disk reserve.
Dispatch: EdgarTools' native document type (Attachment.is_html / is_xml). Extraction: the pinned job.py, as a child.
Status comes only from job.py's RESULT.json rows and the readers' own saved records; this caller reads no content.
Every package member gets one category; nothing is dropped from the account.
The worker runs this file as an isolated child (pointer below), so the worker never imports driver/edgar itself.
"""
import hashlib, json, os, subprocess, sys
from pathlib import Path

PICTURES = {'jpeg', 'png', 'gif'}
READERS = {'html', 'xml'}
BLOCKING = {'conflict', 'unread'}
VERIFIED = 'verified_saved_output'
COMPANIONS = {'EXCEL', 'XLSX', 'XLS', 'ZIP', 'JSON'}  # owner 10-30 ~5:20 PM: Excel/ZIP/JSON companions get custody only this release (EdgarTools document type)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _kind(name):  # EdgarTools 5.60.0's own document type (attachments.py is_html/is_xml: .htm/.html, .xml/.xsd/.xbrl)
    from edgar.attachments import Attachment
    a = Attachment('', '', name, False, '', '', None)
    return 'html' if a.is_html() else 'xml' if a.is_xml() else None


def categories(manifest):
    """Before the run. html/xml by the native document type, for EVERY member (SEC-listed or not).
    A content signature that contradicts it (an .htm whose bytes are a PDF/zip/image, or html/xml bytes under another type) is an
    explicit 'conflict'. Everything else is 'pending' until the readers' records are known (settle)."""
    out = []
    for m in manifest['members']:
        n, hint = m['filename'], m.get('format_hint')
        kind = _kind(n)
        c = ('conflict' if hint == 'pdf' or hint == 'zip' or hint in PICTURES else kind) if kind else 'conflict' if hint in READERS else 'pending'
        out.append(dict(filename=n, sha256=m.get('sha256'), format_hint=hint, type=m.get('type'), category=c))
    return out


def consumed(result):
    """{(member, sha256 or None)} the VERIFIED rows' readers recorded as consumed: ROUTE dependencies with a member, and the scripts
    an eligible Renderer page's own check hashed (RENDERER_ELIGIBILITY facts.scripts, relative to the page)."""
    got = set()
    for r in result['rows']:
        if r.get('outcome') != VERIFIED: continue
        a = Path(r['attempt'])
        for d in (json.loads((a / 'ROUTE.json').read_text()).get('resources') or {}).get('dependencies', []):
            if d.get('member'): got.add((d['member'], d.get('sha256')))
        e = a / 'RENDERER_ELIGIBILITY.json'
        if e.exists() and (el := json.loads(e.read_text())).get('eligible') is True:
            here = os.path.dirname(r['file_id'])
            got |= {(os.path.normpath(os.path.join(here, s)), None) for s in el['facts']['scripts'] if s != 'inline'}
    return got


def settle(members, result):
    """After the run: a pending member a verified reader consumed is 'support'; a PDF or an unconsumed picture is 'owner_excluded'
    (no OCR / image reading); an Excel/ZIP/JSON companion by EdgarTools' native document type is 'companion_custody' (owner scope);
    any other pending member (a filed exhibit with no reader, an unconsumed script/style, ...) is 'unread' and blocks 'complete'."""
    from edgar.attachments import get_document_type
    used = consumed(result)
    for d in members:
        if d['category'] != 'pending': continue
        hit = (d['filename'], d['sha256']) in used or (d['filename'], None) in used
        d['category'] = ('owner_excluded' if d['format_hint'] == 'pdf' else 'support' if hit else
                         'owner_excluded' if d['format_hint'] in PICTURES else
                         'companion_custody' if get_document_type(filename=d['filename'], declared_document_type=d.get('type') or '') in COMPANIONS else 'unread')
    return members


def status(result_path, plan_sha, members):
    """(status, reasons). failed: RESULT missing/corrupt/foreign, its rows are not exactly the planned targets, or a row is not a clean
    finished attempt (job.arm_row's own rule: done, verified or incomplete, job.clean_row), e.g. generation_failed (a browser startup crash).
    incomplete: every row finished cleanly, but a target is not verified (e.g. native PARTIAL), or a conflict/unread member."""
    from driver.prepare.job import clean_row
    targets = sorted(d['filename'] for d in members if d['category'] in READERS)
    try:
        res = json.loads(Path(result_path).read_bytes())
        ids = sorted(r['file_id'] for r in res['rows'])
        assert res['plan_sha256'] == plan_sha and ids == targets, 'RESULT rows are not exactly the planned targets'
    except (OSError, ValueError, KeyError, TypeError, AssertionError) as e:
        return 'failed', [f'RESULT.json: {type(e).__name__}: {e}']
    broken = [f'{r["file_id"]}: {r.get("outcome") or r.get("status")} (not a clean finished attempt)' for r in res['rows']
              if r.get('status') != 'done' or r.get('outcome') not in (VERIFIED, 'incomplete') or not clean_row(r)]
    if broken: return 'failed', broken
    settle(members, res)
    reasons = [f'{r["file_id"]}: {r.get("outcome") or "not finished"}' for r in res['rows'] if r.get('outcome') != VERIFIED]
    reasons += [f'{d["filename"]}: {d["category"]} ({d["format_hint"]})' for d in members if d['category'] in BLOCKING]
    return ('incomplete' if reasons else 'complete'), reasons


def _runtime_reasons(config):  # job.main's own inline pin check (job.py:332-335), repeated by this caller: no reusable function exists
    root = Path(config['runtime_root']); body = Path(config['runtime_manifest']['path']).read_bytes()
    if hashlib.sha256(body).hexdigest() != config['runtime_manifest']['sha256']: return ['runtime manifest file differs from its pin']
    pins = json.loads(body)['files']
    tree = {str(p.relative_to(root)) for p in (root / 'driver').rglob('*') if p.is_file() and '__pycache__' not in p.relative_to(root).parts}
    return ([f'runtime inventory differs: {sorted(set(pins) ^ tree)[:5]}'] if set(pins) != tree else []) + \
           [f'runtime file changed: {n}' for n, h in pins.items() if n in tree and _sha(root / n) != h]


def reverify(receipt, config):
    """A saved receipt counts only after the native checks run again: the pinned runtime files, the package (read_package), exact
    plan/result/manifest hashes, and reconstruct verify for every reading job.py checked (attempt, each state, source_reading)."""
    from driver.prepare.get.acquire import read_package
    why = _runtime_reasons(config)
    if receipt.get('runtime_manifest_sha256') != config['runtime_manifest']['sha256']: why.append('receipt was made by another runtime')
    try: read_package(receipt['version'])
    except Exception as e: why.append(f'package: {type(e).__name__}: {e}')
    for key in ('plan', 'result', 'manifest'):
        p = receipt.get(key) or {}
        if not p.get('path') or not Path(p['path']).exists() or _sha(p['path']) != p.get('sha256'): why.append(f'{key}: missing or changed')
    if not why:
        for r in json.loads(Path(receipt['result']['path']).read_text())['rows']:
            if r.get('outcome') != VERIFIED: continue
            a = Path(r['attempt']); logs = a.with_name('logs_' + a.name.split('_', 1)[1])  # the row's actual attempt path (a released arm included)
            pairs = [(a, logs / 'R.json')] + [(a / 'states' / s, logs / ('state_' + s.replace('@', '_')) / 'R.json') for s in r.get('states') or {}]
            pairs += [(a / 'source_reading', logs / 'source_reading' / 'R.json')] if 'source_reading' in r else []
            for folder, rj in pairs:
                code = subprocess.run([config['python'], '-B', '-m', 'driver.prepare.reconstruct', 'verify', str(folder), str(rj)],
                                      cwd=config['runtime_root'], env={'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1'},
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
                if code: why.append(f'{r["file_id"]}: {folder.relative_to(a.parent)} no longer verifies (exit {code})')
    return dict(receipt, status='failed', reasons=['saved output no longer verifies'] + why) if why else receipt


def _save(path, value):
    pending = path.with_name(path.name + '.pending'); pending.write_text(json.dumps(value, indent=1, sort_keys=True) + '\n'); os.replace(pending, path)


def prepare_filing(filing, config, sender=None):
    """filing: the worker's metadata (accessionNo, cik, formType). config: explicit, no defaults (ADAPTER_DESIGN.txt)."""
    import inspect, shutil
    sys.dont_write_bytecode = True  # the pinned runtime is read-only
    root = Path(config['runtime_root']).resolve()
    if str(root) not in sys.path: sys.path.insert(0, str(root))
    from driver.prepare.get.campaign import Campaign
    from driver.prepare.get import full_run
    from driver.prepare.get.acquire import read_package, _identity
    foreign = sorted({m.__file__ for k, m in list(sys.modules.items()) if k.split('.')[0] == 'driver' and getattr(m, '__file__', None)
                      and not Path(m.__file__).resolve().is_relative_to(root)})
    if foreign: raise ImportError(f'driver modules not from the pinned runtime: {foreign[:3]}')  # e.g. a worker that imported its own tree
    acc, cik, form = filing['accessionNo'], str(filing['cik']), filing['formType']
    out = Path(config['output_root']).absolute(); out.mkdir(parents=True, exist_ok=True)
    pct = inspect.signature(full_run.run).parameters['min_free_percent'].default  # the native acquisition reserve policy
    reserve = int(shutil.disk_usage(out).total * pct / 100)  # full_run.run's own formula
    base = dict(schema='prepared-filing-receipt/2', accession=acc, cik=cik, form=form)
    if config.get('context_campaign') and not config.get('script_qualifications'):  # job.qualify_first and document.py read plan['script_qualifications']
        return dict(base, status='failed', reasons=['config: context_campaign without script_qualifications would silently disable job.py automatic script qualification'])
    if config.get('script_qualifications') and not Path(config['script_qualifications']).is_dir():  # job.claim_version opens files inside it; it never creates it
        return dict(base, status='failed', reasons=['config: script_qualifications is not an existing folder'])
    try:
        with Campaign(config['campaign_dir'], live=config['live'], minimum_free_bytes=reserve, **({'sender': sender} if sender else {})) as campaign:
            got = full_run._filing(campaign, out / 'package', reserve, acc, cik, form)
    except Exception as e:  # no custody: nothing to extract
        return dict(base, status='failed', reasons=[f'package: {type(e).__name__}: {e}'])
    version = out / 'package/versions' / acc / got['sha256']
    manifest, _ = read_package(version)
    members = categories(manifest)
    mpath = version / 'manifest.json'
    base.update(package=got, package_sha256=got['sha256'], version=str(version), manifest=dict(path=str(mpath), sha256=_sha(mpath)),
                runtime_manifest_sha256=config['runtime_manifest']['sha256'])
    if got['status'] != 'OK':  # native custody result kept as is (UNRESOLVED / INVENTORY_GAP), with the member account
        return dict(base, status='failed', reasons=[f'package: {got["status"]}'], members=members)
    several = len(manifest['identity']['ciks']) > 1
    plan = dict(runtime_root=config['runtime_root'], runtime_manifest=config['runtime_manifest'],
                browser_executable=config['browser']['executable'], browser_executable_sha256=config['browser']['sha256'],
                browser_version=config['browser']['version'], context_explore=False,
                **({'context_campaign': config['context_campaign']} if config.get('context_campaign') else {}),
                **({'script_qualifications': config['script_qualifications']} if config.get('script_qualifications') else {}),  # the native store (a folder), passed through
                source_commands=[dict(file_id=d['filename'], dispatch=d['category'], filename=d['filename'], source_sha256=d['sha256'],
                                      immutable_package_directory=str(version), package_metadata_path=str(mpath),
                                      package_metadata_sha256=base['manifest']['sha256'], package_sha256=got['sha256'],
                                      **({'requested_cik': _identity(acc, cik, form)['cik']} if several else {}))
                                 for d in members if d['category'] in READERS])
    body = (json.dumps(plan, indent=1, sort_keys=True) + '\n').encode(); pin = hashlib.sha256(body).hexdigest()
    run = out / 'runs' / acc / got['sha256'] / pin
    receipt = None
    if (run / 'RECEIPT.json').exists():  # a repeat event: a saved product counts only after re-verify, then the status is re-derived under THIS code's policy
        receipt = json.loads((run / 'RECEIPT.json').read_text())
        if receipt['status'] != 'failed':
            saved = reverify(receipt, config)
            if saved['status'] == 'failed': return saved  # damaged/changed saved output: an explicit failure, never credited, never run over
            st, reasons = status(saved['result']['path'], pin, members)
            receipt = dict(saved, status=st, reasons=reasons, members=members)
    run.mkdir(parents=True, exist_ok=True)
    if not (run / 'PLAN.json').exists(): (run / 'PLAN.json').write_bytes(body)
    while receipt is None or receipt['status'] == 'failed':  # no product yet, or a technical failure: a new job, every earlier job folder and receipt kept
        n = len(list(run.glob('job_*.stdout')))  # every launched job, an interrupted one included
        if n >= config['max_jobs']:
            return receipt or dict(base, status='failed', reasons=[f'{n} jobs launched, none finished (max_jobs {config["max_jobs"]})'], members=members)
        receipt = _job(config, root, run, pin, run / f'job_{n}', base, members)
    return receipt


def _job(config, root, run, pin, jobdir, base, members):  # one pinned job.py child in a new folder (job.py refuses an existing one)
    prep = root / 'driver/prepare'
    with open(run / f'{jobdir.name}.stdout', 'xb') as so, open(run / f'{jobdir.name}.stderr', 'xb') as se:
        code = subprocess.run([config['python'], '-I', '-S', '-B', str(prep / 'job.py'), str(run / 'PLAN.json'), pin, str(jobdir),
                               str(prep / 'document.py'), str(config['seconds'])], env={'PATH': '/usr/bin:/bin', 'HOME': os.environ['HOME']},
                              cwd=str(run), stdout=so, stderr=se).returncode
    result = jobdir / 'RESULT.json'
    st, reasons = status(result, pin, members)
    if code not in (0, 1) and st != 'failed': st, reasons = 'failed', [f'job.py exit {code}'] + reasons
    receipt = dict(base, status=st, reasons=reasons, plan=dict(path=str(run / 'PLAN.json'), sha256=pin),
                   result=dict(path=str(result), sha256=_sha(result) if result.exists() else None), job_exit=code, members=members)
    _save(run / f'{jobdir.name}.receipt.json', receipt); _save(run / 'RECEIPT.json', receipt)  # this job's own receipt stays; RECEIPT.json = the latest
    return receipt


def prepared_done(record):
    """The worker's skip rule for an already-enriched record: only a complete/incomplete prepared product counts as done.
    Missing or failed -> the item is processed again (existing worker path), never skipped on 'enriched' alone."""
    return (record.get('prepared_extraction') or {}).get('status') in ('complete', 'incomplete')


def pointer(filing, config_path):
    """What the existing worker adds to its processed record: a locator to the durable receipt, never the product itself.
    The adapter runs as an isolated child of the configured pinned interpreter. Any error becomes an honest 'failed' pointer."""
    try:
        config = json.loads(Path(config_path).read_text())
        p = subprocess.run([config['python'], '-I', '-B', str(Path(__file__).resolve()), str(config_path)], input=json.dumps(filing),
                           capture_output=True, text=True, env={'PATH': '/usr/bin:/bin', 'HOME': os.environ['HOME']})
        r = json.loads(p.stdout.strip().splitlines()[-1]) if p.returncode == 0 else None
        if r is None: return dict(status='failed', reasons=[f'adapter exit {p.returncode}: {p.stderr.strip()[-300:]}'])
    except Exception as e:
        return dict(status='failed', reasons=[f'adapter: {type(e).__name__}: {e}'])
    saved = Path(r['plan']['path']).with_name('RECEIPT.json') if r.get('plan') else None
    return dict(status=r['status'], reasons=r.get('reasons', [])[:20], package_sha256=r.get('package_sha256'),
                runtime_manifest_sha256=r.get('runtime_manifest_sha256'),
                receipt=dict(path=str(saved), sha256=_sha(saved)) if saved and saved.exists() else None)


if __name__ == '__main__':  # the isolated child: filing JSON on stdin, config path as argv[1], the receipt as the last stdout line
    print(json.dumps(prepare_filing(json.loads(sys.stdin.read()), json.loads(Path(sys.argv[1]).read_text()))))
