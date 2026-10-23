"""The per-document generation owner, run by driver/prepare/job.py: argv PLAN PLAN_SHA256 ORDINAL NEW_ATTEMPT_DIR (an existing attempt is refused).
Before any work it checks the plan pin, every pin of the plan's runtime manifest, the browser executable's sha256 and version, and the row's
own source sha256. It then writes one attempt: START; for HTML also SOURCE and RAW_READING with the stored raw reading; ROUTE, prepared inputs and COMPLETE.
A plan row is either a sealed package (immutable_package_directory, its pinned original metadata, package_sha256) or loose local members
(`directory` plus `members` {path: {sha256, bytes}}, base and bundle null: no package seal, SEC address or response is claimed). An HTML row may
also give `requested_cik` (to bind an address in a package of several CIKs) and `observed_responses` (exact recorded responses only). A document that declares a script action enters context through the
plan's one job-level `context_campaign` (sealed rows only) or a pinned row `context`; every state is saved under states/<label>/ by the same
helpers. XML rows use xml_fields. No OCR, reader, join or repair. Moved unchanged (apart from this text) from the reviewed
context_candidate/action_budget_20261022/caller/native_one_document_v6.py."""
import hashlib
import json
import os
from pathlib import Path
import sys


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf-8') as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())


def declared_source(row, manifest, members, screen_grid, acquire):
    """The one Source of this document and its declaration: the document's member path and the verified package's identity, read at the requested
    filing's own directory where the persisted record proves the requested CIK - the package's only CIK, or the plan's `requested_cik`, which must be one
    of them - derived as acquisition and full_run derive the package address (a declared derivation, never an observed response); otherwise no address.
    Observed evidence only from the plan's exact recorded responses ({url, status, content_type, observed_at, sha256[, body (hex)]})."""
    identity, wanted = manifest['identity'], row.get('requested_cik')
    if wanted is not None and acquire._identity(identity['accession'], wanted, identity['form'])['cik'] not in identity['ciks']: raise ValueError('requested CIK is not one of the package')
    cik = acquire._identity(identity['accession'], wanted, identity['form'])['cik'] if wanted is not None else identity['ciks'][0] if len(identity['ciks']) == 1 else None
    base = None if cik is None else acquire._url(acquire._identity(identity['accession'], cik, identity['form'])).rsplit('/', 1)[0] + '/'
    observed = {o['url']: dict(o, body=bytes.fromhex(o['body'])) if 'body' in o else dict(o) for o in row.get('observed_responses', [])}
    declared = {'path': row['filename'], 'bundle': manifest['package']['sha256'], 'requested_cik': cik, 'base': base,
                'base_from': None if base is None else 'requested filing directory of the package address (declared derivation, not an observed response)',
                **({} if base else {'no_base': 'several CIKs and no requested_cik' if len(identity['ciks']) > 1 else 'no CIK'}), 'observed_urls': sorted(observed)}
    return screen_grid.Source(row['filename'], members, base=base, observed=observed, bundle=manifest['package']['sha256']), declared


def raw_reading(attempt, file_id, edgartools_html, archive, acquire):
    """The tool call html_route.prepare makes, keeping the tool's own reading once: the plain dump (as the grader command line writes it) in the
    existing archive, then its receipt, before the route is made of it. A damaged archive is storage, never a parse verdict."""
    def parse(raw, vis):
        tree, seconds, made_by = edgartools_html.parse(raw, vis)
        try:
            pin = archive.store_blob(attempt / 'raw_reading', json.dumps(tree, ensure_ascii=False).encode())
        except acquire.AcquisitionError as error:  # convert takes a ValueError for a document that cannot be parsed
            raise acquire.StorageError(f'raw reading not stored: {error}') from error
        save(attempt / 'RAW_READING.json', {'file_id': file_id, 'source_sha256': digest(raw), 'raw_reading_sha256': pin, 'version': made_by,
                                            'settings': edgartools_html.settings(vis), 'paged': vis.paged, 'tool_seconds': seconds})
        return tree, seconds, made_by
    return parse


def keep_captures(folder, captures):  # every distinct native capture once, content-addressed under captures/ (records name the digest), restored before use
    from driver.prepare.get import archive
    for digest, png in captures.items():
        assert archive.store_blob(folder / 'captures', png) == digest, 'capture identity mismatch'
        assert archive.load_blob(folder / 'captures', digest) == png, 'capture restoration mismatch'


def source_child(attempt, row, raw, displayed, declared, html_route, edgartools_html, archive, acquire):
    """The attempt's ONE typed whole-source reading (html_route.source_reading, from the displayed initial route's own saved visibility evidence),
    saved as a whole attempt of its own under source_reading/: its SOURCE and ROUTE/COMPLETE by the same finish, with no prepared inputs. An HTML
    reading also keeps its own RAW_READING (the parent's receipt untouched) and names its pictures unprepared (PARTIAL); the strict XML reading has
    no raw reading and qualifies each source picture tag against the displayed route's own occurrence, whose input the caller checks there. The
    parent's completion pins it (finish) and the custody gate holds it to the same checks. The outcome - made, or why not - is written into the
    displayed route's facts."""
    child = attempt / 'source_reading'
    def parse(raw_, vis):
        child.mkdir(mode=0o700); save(child / 'SOURCE.json', dict(declared, reading='source (not a display state)'))
        return raw_reading(child, row['file_id'], edgartools_html, archive, acquire)(raw_, vis)
    route, why = html_route.source_reading(raw, row['file_id'], row['source_sha256'], displayed, parse=parse)
    if route is not None:
        if not child.exists(): child.mkdir(mode=0o700); save(child / 'SOURCE.json', dict(declared, reading='source (not a display state)'))  # a reading made with no HTML parse (the XML route)
        finish(child, row, route, {}, archive, save)
    displayed.setdefault('facts', {})['source_reading'] = {'made': True, 'status': route['status'], **({'error': route['error']} if route.get('error') else {})} if route is not None else {'made': False, 'why': why}


def finish(folder, row, route, prepared, archive, save_):
    """The completion step every saved route takes (version 5's tail, unchanged): prepared inputs restore, the raw reading restores, ROUTE then COMPLETE."""
    for pin, data in prepared.items():
        assert archive.store_blob(folder / 'prepared', data) == pin, 'archive identity mismatch'
        assert archive.load_blob(folder / 'prepared', pin) == data, 'archive restoration mismatch'
    receipt = folder / 'RAW_READING.json'
    kept = json.loads(receipt.read_bytes()) if receipt.exists() else None
    if kept is not None:
        assert kept['source_sha256'] == row['source_sha256'], 'raw reading source mismatch'
        archive.load_blob(folder / 'raw_reading', kept['raw_reading_sha256'])
    save_(folder / 'ROUTE.json', route)
    save_(folder / 'COMPLETE.json', {'file_id': row['file_id'], 'source_sha256': row['source_sha256'],
        'route_sha256': digest((folder / 'ROUTE.json').read_bytes()), 'native_status': route['status'],
        'prepared_input_sha256': sorted(prepared), 'reader_called': False,
        'raw_reading_sha256': kept and kept['raw_reading_sha256'], 'raw_reading_receipt_sha256': kept and digest(receipt.read_bytes()),
        **({'context_renders_sha256': digest((folder / 'CONTEXT_RENDERS.json').read_bytes())} if (folder / 'CONTEXT_RENDERS.json').exists() else {}),  # a context route's saved render evidence, bound like ROUTE
        **({'source_reading_complete_sha256': digest((folder / 'source_reading' / 'COMPLETE.json').read_bytes())} if (folder / 'source_reading' / 'COMPLETE.json').exists() else {})})  # the attempt's typed source reading, bound like ROUTE


def context_evidence(row):
    """The row's pinned evidence, every recorded body checked against its own sha256."""
    c = row['context']; body = Path(c['evidence']).read_bytes(); assert digest(body) == c['evidence_sha256'], 'context evidence pin mismatch'
    ev = json.loads(body); observed = {}
    for url, o in ev['observed'].items():
        b = bytes.fromhex(o['body']) if o.get('body') is not None else None
        assert b is None or digest(b) == o['sha256'], 'recorded body differs from its sha256: ' + url
        observed[url] = dict(o, body=b)
    return dict(ev, observed=observed)


def run_marked(raw, screen_grid, p):  # the run-mark body every selection measures with (runtime marking: the screen step's run marks; pixel-neutral)
    vis = screen_grid.Visible(raw); runs, _ = screen_grid.symbol_runs(raw, vis)
    return screen_grid.tag_cells(raw, vis, (), [(a, b'<!--%ss:%d-->' % (p.encode(), k)) for k, (a, _, _, ok) in enumerate(runs) if ok], p)[0]


def acquired_context(browser, row, raw, screen_grid, attempt, save_, require=True, max_actions=None):
    """The production path (Root CONTEXT_ACQUISITION_FAILURE_CLASS_20261021): authoritative context from the sealed package identity and member through
    the existing Campaign and the generic seam (driver.prepare.get.context_acquire); the selection's native captures kept once under captures/. Any error
    the seam raises (storage, OS, memory, an untyped acquisition error, a stopped campaign) fails the run - never an unavailable page."""
    from driver.prepare.get import acquisition, campaign, context_acquire, transport
    a = row['context']['acquire']; p = screen_grid.marker_prefix(raw); acquisition.Selection.blobs = attempt / 'captures'
    with campaign.Campaign(a['campaign'], live=bool(a.get('live')), sender=transport.http_request) as camp:
        got = context_acquire.acquire_context(camp, browser, row['immutable_package_directory'], row['filename'], run_marked(raw, screen_grid, p), p, requested_cik=row.get('requested_cik'),
                                                   **({} if max_actions is None else {'max_actions': max_actions}))  # the job-level native action limit when set; otherwise the native function's own default
    save_(attempt / 'CONTEXT_ACQUISITION.json', {'outcome': got['outcome'], 'record': got['record']})  # kept before any gate
    if got['outcome'] != 'associated' and not require: return None, {'by': 'driver.prepare.get.context_acquire', 'outcome': got['outcome']}  # automatic entry: the default output stays, incomplete
    assert got['outcome'] == 'associated', 'context acquisition: ' + got['outcome']
    return got['evidence'], {'by': 'driver.prepare.get.context_acquire', 'outcome': got['outcome']}


def select(browser, row, ev, raw, screen_grid, keep):
    """OCR's automatic parent-action selection from the runtime (driver.prepare.get.acquisition; no click list, no research-path import): the parent's
    own initial selection, else the first fully qualified native observed control (acquisition.select_parent, the same owner as context_acquire:
    a node of the recorded native parent state, never a raw-source anchor); otherwise refused. Every native result is saved before any gate."""
    from driver.prepare.get import acquisition
    from driver.prepare.convert import overlay
    c = row['context']; p = screen_grid.marker_prefix(raw); marked = run_marked(raw, screen_grid, p)
    body, rec = overlay.measurement_body(ev['observed'][ev['target_url']]['body'], raw, marked, p, ev['proof'])
    assert body is not None, 'selection: no verified measurement body: ' + json.dumps(rec)[:200]
    got, ns = acquisition.select_parent(browser, ev['parent_url'], ev['observed'], ev['target_url'], raw, body, p)  # the one selector, its default limit (as acquire_context)
    keep({'selection_result': None, 'native_selection_result': got, 'measurement': rec, 'evidence': c['evidence'], 'evidence_sha256': c['evidence_sha256']})  # no source-anchor pass any more
    chosen = [a['source_anchor'] for a in got['attempts'] if a['state'] == 'qualified']
    summary = {'by': 'NativeSelection', 'verdict': got['verdict'], 'qualified': chosen, 'baseline': got['baseline'], 'search': got.get('search'),
               'attempts': [{k: a.get(k) for k in ('source_anchor', 'state', 'neutral')} for a in got['attempts']]}
    if got['verdict'] == 'initial': return dict(acquisition.selection_record(got, ns), by='OCR acquisition: the parent\'s own initial load requests the target (no action)'), summary
    assert got['verdict'] == 'selected' and len(chosen) == 1, 'selection refused: ' + json.dumps(summary)[:300]
    return dict(acquisition.selection_record(got, ns), by='OCR acquisition.select_parent: the first fully qualified native observed control of the recorded parent state, not a raw-source anchor (programmatic untrusted click)'), summary


def main():
    os.umask(0o077)
    plan_path, plan_hash, ordinal, attempt_path = sys.argv[1:]
    body = Path(plan_path).read_bytes()
    assert digest(body) == plan_hash, 'execution plan pin mismatch'
    plan = json.loads(body)
    row = plan['source_commands'][int(ordinal)]
    attempt = Path(attempt_path)
    attempt.mkdir(mode=0o700)  # an existing attempt is never overwritten
    save(attempt / 'START.json', {'ordinal': int(ordinal), 'file_id': row['file_id'], 'plan_sha256': plan_hash})
    runtime = Path(plan['runtime_root'])
    runtime_manifest = Path(plan['runtime_manifest']['path']).read_bytes()
    assert digest(runtime_manifest) == plan['runtime_manifest']['sha256'], 'runtime manifest mismatch'
    for name, pin in json.loads(runtime_manifest)['files'].items():
        assert digest((runtime / name).read_bytes()) == pin, 'runtime file mismatch'
    sys.path.insert(0, str(runtime))
    from driver.prepare.get import acquire, archive
    from driver.prepare.convert import edgartools_html, html_route, screen_grid, xml_fields
    if 'directory' in row:  # v5: loose local members, each named and pinned by the plan row; never a package
        assert 'immutable_package_directory' not in row and row.get('base') is None and row.get('bundle') is None, 'a loose row declares no package, base or bundle'
        members = {}
        for name, pin in row['members'].items():
            assert name and not Path(name).is_absolute() and '..' not in Path(name).parts, 'loose member path is not relative'
            data = (Path(row['directory']) / name).read_bytes()
            assert digest(data) == pin['sha256'] and len(data) == pin['bytes'], 'loose member pin mismatch'
            members[name] = data
    else:
        original_bytes = Path(row['package_metadata_path']).read_bytes()
        assert digest(original_bytes) == row['package_metadata_sha256'], 'original package metadata pin mismatch'
        original_manifest = json.loads(original_bytes)
        manifest, members = acquire.read_package(row['immutable_package_directory'])
        assert manifest == original_manifest, 'current package differs from original sealed metadata'
        assert manifest['package']['sha256'] == row['package_sha256'], 'package mismatch'
    raw = members[row['filename']]
    assert digest(raw) == row['source_sha256'], 'own source mismatch'
    prepared = {}
    if row['dispatch'] == 'html':
        from playwright.sync_api import sync_playwright
        from driver.prepare.pictures import inputs
        assert digest(Path(plan['browser_executable']).read_bytes()) == plan['browser_executable_sha256'], 'browser mismatch'
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=plan['browser_executable'], headless=True, timeout=30000)
            try:
                assert browser.version == plan['browser_version'], 'browser version mismatch'
                if 'directory' in row:  # v5: the loose row's own evidence only
                    source = screen_grid.Source(row['filename'], members, base=None, observed={}, bundle=None)
                    declared = {'path': row['filename'], 'members': {k: digest(v) for k, v in sorted(members.items())}, 'base': None, 'bundle': None,
                                'loose': 'plan-declared local members; no package seal, no derived or observed SEC address or response'}
                else:
                    source, declared = declared_source(row, manifest, members, screen_grid, acquire)  # one Source, through HTML and picture preparation
                save(attempt / 'SOURCE.json', declared)
                auto = (None, None)  # automatic entry (Root CONTEXT_AUTOMATIC_ENTRY_IMPLEMENT_20261022): a declared script action, no pinned context row
                from driver.prepare.convert import html_route as _route
                if 'context' not in row and _route.declarations(screen_grid.Visible(raw), browser)[0]:  # the same shared decision the route status uses; only the supported link path enters context
                    cfg = plan.get('context_campaign')  # the one job-level campaign configuration; no per-document switch
                    if cfg and 'immutable_package_directory' in row: auto = acquired_context(browser, dict(row, context={'acquire': cfg}), raw, screen_grid, attempt, save, require=False, max_actions=cfg.get('max_actions'))  # optional job-level limit only (Root CONTEXT_NATIVE_ACTION_BUDGET_20261022T0438)
                    else: save(attempt / 'CONTEXT_ACQUISITION.json', {'outcome': 'not attempted: ' + ('no job campaign configuration' if not cfg else 'a loose input has no filing package'), 'record': None})
                if 'context' in row or auto[0] is not None:  # version 6: every state through the one context boundary, each with its own custody
                    from driver.prepare.convert import context
                    if auto[0] is not None: ev, chosen = auto  # associated automatically: the same path as a pinned acquire row
                    elif 'acquire' in row['context']: ev, chosen = acquired_context(browser, row, raw, screen_grid, attempt, save)  # production: package identity + member
                    else:  # the injected public-fixture test path: a pinned evidence file, the runtime's own selection
                        ev = context_evidence(row); ev['selection'], chosen = select(browser, row, ev, raw, screen_grid, lambda x: save(attempt / 'CONTEXT_SELECTION_RESULT.json', x))
                    save(attempt / 'CONTEXT_SELECTION.json', {'selection': ev['selection'], 'summary': chosen, 'evidence': row.get('context', {}).get('evidence'), 'evidence_sha256': row.get('context', {}).get('evidence_sha256')})
                    states, prepared_by = attempt / 'states', {}; states.mkdir(mode=0o700)
                    folder = lambda label: attempt if label == 'initial' else states / label
                    def per_parse(label):
                        if label != 'initial': folder(label).mkdir(mode=0o700); save(folder(label) / 'SOURCE.json', dict(declared, state=label))
                        return raw_reading(folder(label), row['file_id'], edgartools_html, archive, acquire)
                    def per_prepare(route_, src, label):
                        if label == 'initial': source_child(attempt, row, raw, route_, declared, html_route, edgartools_html, archive, acquire)  # once, before the interaction graph
                        save(folder(label) / 'ROUTE_BEFORE_INPUTS.json', route_)
                        try: prepared_by[label] = inputs.prepare(raw, route_, members, browser, src)
                        finally:
                            late = [w for w in src.context.gate() if w not in (route_.get('error') or '')]  # renders the picture step made: same state gate
                            if late: route_['status'], route_['error'] = 'PARTIAL', '; '.join(filter(None, [route_.get('error')] + ['context: ' + w for w in late]))
                            save(folder(label) / 'ROUTE_AFTER_INPUTS.json', route_)
                            save(folder(label) / 'CONTEXT_RENDERS.json', src.context.records)  # every render of this state: its native snapshot (strict gate), requests, proofs
                            keep_captures(folder(label), src.context.captures)
                    res = context.contextual_routes(raw, row['file_id'], row['source_sha256'], browser, source, ev, parse=per_parse, prepare=per_prepare,  # the row's own Source evidence
                                                    explore=plan.get('context_explore', True))  # the one job-level choice: False = the initial view only (report controls not attempted)
                    for st in res['states']: finish(folder(st['label']), row, st['route'], prepared_by[st['label']], archive, save)  # each state finished once, after its route is whole (observed controls included)
                    route, prepared = res['initial'], prepared_by.get('initial', {})
                    for l in route['source_links']:
                        for act in l.get('activations') or []:
                            if act.get('state'): act['route_sha256'] = digest((states / act['state'] / 'ROUTE.json').read_bytes())  # a refused attempt has no state route
                    save(attempt / 'CONTEXT_TRIALS.json', res['trials']); keep_captures(attempt, res['trial_captures'])
                else:
                    route, facts = html_route.prepare(raw, row['file_id'], row['source_sha256'], browser, source,
                                                      parse=raw_reading(attempt, row['file_id'], edgartools_html, archive, acquire))
                    route['facts'] = facts
                    source_child(attempt, row, raw, route, declared, html_route, edgartools_html, archive, acquire)
                    save(attempt / 'ROUTE_BEFORE_INPUTS.json', route)
                    try:
                        prepared = inputs.prepare(raw, route, members, browser, source)
                    finally:
                        save(attempt / 'ROUTE_AFTER_INPUTS.json', route)
            finally:
                browser.close()
    elif row['dispatch'] == 'xml':
        route = xml_fields.convert(raw, row['file_id'], row['source_sha256'])
    else:
        raise ValueError('unbound original dispatch')
    finish(attempt, row, route, prepared, archive, save)  # version 5's tail, now one function every state uses


if __name__ == '__main__':
    main()
