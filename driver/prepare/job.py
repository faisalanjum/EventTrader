"""The batch owner: one pinned plan, run from this checkout's own reviewed runtime (the plan's runtime_root, its manifest checked before any row). For each ordinal:
generation child (document.py) -> reconstruct main child -> reconstruct verify child, each exit observed from the child itself.
RESULT.json is one record, rewritten whole as rows change; every ordinal is listed 'unstarted' before any child runs.
Outcomes: verified_saved_output (generation 0; then ONE shared check for the initial output, for every labelled state and for the source reading: own identity, decoding,
native OK, no picture input error, readback asset status ok, every named native capture kept and restorable, reconstruct and verify 0; every activation's state is a saved folder in states/ with
the route hash it records, and every saved state is named; preservation only, never source fidelity), identity_mismatch, incomplete (with
reasons), generation_failed (composition skipped). Exit 0 only if every row is verified_saved_output, else 1.
Usage: <qualified python> -I -S -B driver/prepare/job.py PLAN PLAN_SHA256 NEW_OUT_DIR [GENERATOR [SECONDS]]. Production runs this checkout's
own document.py: omit GENERATOR, or pass that exact sibling path (needed to give SECONDS with this positional CLI). Any ALTERNATE generator
path is test-only (the operating controls' synthetic child) and is not pinned. The manifest must list every file of this runtime's driver tree (Python caches aside). Every child runs with that same interpreter; HOME and CPU affinity come from the launch (e.g. taskset or a systemd scope)."""
import hashlib, json, os, signal, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]  # this checkout: the plan's runtime_root must resolve here; reconstruct and verify run from it


def bound(seconds):  # each child's limits: time, file size, no core (CPU affinity is inherited from the launch)
    return ['timeout', '-s', 'TERM', '-k', '10', str(seconds), 'prlimit', '--fsize=1073741824', '--core=0']  # common 1 GiB limit, including native browser backing files


def save(path, record):  # the one result record, replaced whole
    tmp = path.with_name(path.name + '.tmp'); tmp.write_text(json.dumps(record, indent=1)); os.replace(tmp, path)


CURRENT = []  # the one running child, so a stop signal to the job reaches it (its `timeout` passes it on) instead of leaving it running


def _stop(signum, frame):  # no wait() here (run 2 deadlocked); the direct child is `timeout`, which passes TERM to its own process group (runs 3-4 leaked through /usr/bin/time)
    for p in CURRENT: p.send_signal(signal.SIGTERM)
    sys.exit(128 + signum)


def observed(logs, name):  # the one child's own kernel accounting (os.wait4), written when it ended
    return json.loads((logs / f'{name}.usage.json').read_bytes())


def size(d):
    return sum(p.stat().st_size for p in Path(d).rglob('*') if p.is_file())


def child(argv, logs, name, cwd, env):
    with open(logs / f'{name}.stdout', 'xb') as out, open(logs / f'{name}.stderr', 'xb') as err:
        t0 = time.monotonic(); p = subprocess.Popen(argv, stdout=out, stderr=err, stdin=subprocess.DEVNULL, cwd=cwd, env=env); CURRENT.append(p)
        try: _, status, use = os.wait4(p.pid, 0)
        finally: CURRENT.remove(p)
        p.returncode = code = os.waitstatus_to_exitcode(status)
        (logs / f'{name}.usage.json').write_text(json.dumps({'wall_seconds': round(time.monotonic() - t0, 3), 'max_rss_kb': use.ru_maxrss, 'user_seconds': use.ru_utime, 'system_seconds': use.ru_stime}))
        return code


def decoded(path, row, what):  # a child's JSON output: an explicit recorded technical failure when absent or not JSON, never a crash or a guess
    try: return json.loads(Path(path).read_bytes())
    except (OSError, ValueError) as error: row.setdefault('technical_failures', []).append(f'{what}: {type(error).__name__}: {error}'); return None


def kept_captures(folder, documents, what):  # every native capture digest a saved context record names ({'capture': {'sha256'}} at any depth): kept once under captures/, restorable
    import gzip
    named = set()
    def walk(x):
        if isinstance(x, dict):
            c = x.get('capture')
            if isinstance(c, dict) and isinstance(c.get('sha256'), str): named.add(c['sha256'])
            for v in x.values(): walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
    for d in documents: walk(d)
    bad = []
    for d in sorted(named):
        try: ok = hashlib.sha256(gzip.decompress((folder / 'captures' / (d + '.gz')).read_bytes())).hexdigest() == d
        except (OSError, ValueError, EOFError): ok = False
        if not ok: bad.append(d)
    return len(named), [f'{what}native capture not kept or not restorable: {d}' for d in bad]


def check_output(folder, logs, expected, seconds, renv, row, result, record, what, live):  # live: where these fields stand in the saved record
    """The one acceptance check for a saved output (the initial output, every labelled state and the typed source reading): its own completion identity, its decoding, native
    status, picture preparation and the readback's own asset status, reconstruct and verify. Returns (fields, reasons, route)."""
    st, t0 = {}, len(row.get('technical_failures', []))
    complete = decoded(folder / 'COMPLETE.json', row, what + 'COMPLETE.json'); route = decoded(folder / 'ROUTE.json', row, what + 'ROUTE.json')
    got = None if complete is None else {key: complete.get(key) for key in expected}
    if complete is None or route is None or got != expected:  # the completion must be this ordinal's own input
        readable = complete is not None and route is not None
        st.update(outcome='identity_mismatch' if readable else 'incomplete', expected_identity=expected, completion_identity=got)
        return st, (['completion identity differs from the plan row'] if readable else [f'technical failure: {t}' for t in row['technical_failures'][t0:]]), route
    st['native_status'] = complete['native_status']; st['native_error'] = route.get('error')  # native fields kept as saved
    docs = [decoded(folder / n, row, what + n) for n in ('CONTEXT_RENDERS.json', 'CONTEXT_TRIALS.json', 'CONTEXT_ACQUISITION.json') if (folder / n).exists()]  # a contextual output's records
    st['captures_named'], cap_reasons = kept_captures(folder, docs, what)
    st['picture_input_errors'] = [u.get('id') for u in route.get('units') or [] if isinstance(u, dict) and isinstance(u.get('input'), dict) and 'error' in u['input']]
    st['reconstruct_exit'] = child(bound(seconds) + [sys.executable, '-B', '-m', 'driver.prepare.reconstruct', str(folder), str(logs / 'R.json')], logs, 'reconstruct', ROOT, renv)
    st['reconstruct_observed'] = observed(logs, 'reconstruct'); live.update(st); save(result, record)  # each child's exit is saved before its output is decoded
    R = decoded(logs / 'R.json', row, what + 'R.json') if st['reconstruct_exit'] == 0 else None
    if R is not None:
        st['R_bytes'] = (logs / 'R.json').stat().st_size; fams, assets = {}, []
        for u in R['unknowns']: fams[u.get('family')] = fams.get(u.get('family'), 0) + 1
        st['reconstruction_unknown_families'] = fams  # every unknown stays in R.json; counted here, never judged
        def walk(x):
            if isinstance(x, dict):
                if 'record' in x and 'asset' in x: assets.append((x['record'].get('id'), x['asset'].get('status')))
                for v in x.values(): walk(v)
            elif isinstance(x, list):
                for v in x: walk(v)
        walk(R.get('sequence', [])); st['picture_asset_status'] = {i: s for i, s in assets}  # the collator's own asset status
        st['verify_exit'] = child(bound(seconds) + [sys.executable, '-B', '-m', 'driver.prepare.reconstruct', 'verify', str(folder), str(logs / 'R.json')], logs, 'verify', ROOT, renv)
        live.update(st); save(result, record); st['verify'] = decoded(logs / 'verify.stdout', row, what + 'verify output')
    reasons = ([] if st['native_status'] == 'OK' else [f"native status {st['native_status']}"]) + (['picture asset status not ok'] if any(v != 'ok' for v in st.get('picture_asset_status', {}).values()) else [])
    reasons += [f"picture preparation error: {i}" for i in st['picture_input_errors']]
    reasons += [] if st['reconstruct_exit'] == 0 else [f"reconstruct exit {st['reconstruct_exit']}"]
    reasons += [] if R is None or st.get('verify_exit') == 0 else [f"verify exit {st.get('verify_exit')}"]
    reasons += cap_reasons + [f'technical failure: {t}' for t in row.get('technical_failures', [])[t0:]]
    return st, reasons, route


QUALIFY_ROUTE = ('units', 'page_visibility', 'source_ids', 'source_relations', 'source_style', 'source_inline', 'source_symbols', 'source_facts', 'generated_content', 'uncovered')
QUALIFY_SCHEMA, QUALIFY_ROLES = 'script-version-qualification/2', {'normal_result', 'explored_result', 'without_result', 'normal_route', 'without_route', 'normal_acquisition', 'explored_acquisition', 'without_acquisition', 'explored_trials'}
QUALIFY_PLAN_KEYS = ('context_explore', 'qualification_diagnostic', 'qualification_withhold', 'source_commands', 'context_viewer_start')  # viewer start is separately bound to NORMAL's own observation below


def compare_views(a, b):
    """One saved view against another, field by field (the producer's comparison; a may be an explored NORMAL state in its diagnostic representation).
    Content / visibility / layout fields must be equal; the text proof must be TRUE in both - for a diagnostic route its native proof before the
    diagnostic gate (route.diagnostic.text_proved_before_gate), never a missing or false value turned true."""
    tp = lambda r: (r.get('diagnostic') or {}).get('text_proved_before_gate') if r.get('diagnostic') else r.get('text_proved')
    links = lambda r: [{k: v for k, v in l.items() if k != 'activations'} for l in r.get('source_links') or []]
    screen = lambda r: {k: v for k, v in ((r.get('facts') or {}).get('screen') or {}).items() if k != 'seconds'}
    f = {k: a.get(k) == b.get(k) for k in QUALIFY_ROUTE}
    f.update(text_proved=tp(a) is True and tp(b) is True, source_links=links(a) == links(b), screen=screen(a) == screen(b),
             **{k: (a.get('facts') or {}).get(k) == (b.get('facts') or {}).get(k) for k in ('visibility', 'formatting')})
    return f


def claim_version(folder, h):
    """The one exclusive claim per exact bytes, taken BEFORE any expensive qualification run: True for the caller that created it, False when any
    caller (this job or another) already holds it. Never released or retried: one qualification attempt per version (its record or its absence)."""
    try: os.close(os.open(Path(folder) / (h + '.claim'), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)); return True
    except FileExistsError: return False


QUALIFY_FAILURES = (OSError, ValueError, KeyError, TypeError, AttributeError)  # missing, unreadable or malformed saved evidence: a technical STOP of the qualification, never a verdict


def reader(read):  # the producer's file reads: each records the file's sha256 at the moment it was read in `read` (the record's evidence)
    def rd(x): b = Path(x).read_bytes(); read[str(x)] = hashlib.sha256(b).hexdigest(); return json.loads(b)
    def sha(x): b = Path(x).read_bytes(); read[str(x)] = hashlib.sha256(b).hexdigest(); return read[str(x)]
    return rd, sha


def viewer_start(ref, expected, read):
    """Read the original unmarked parent plan from its own completed NORMAL render. Shared by the child and both producer gates; no alternate
    reference, later-attached plan, stale render or other file can supply it. Unsupported parents have no plan and retain the existing path."""
    rd, sha = reader(read); path = Path(ref['path'])
    if sha(path) != ref['sha256']: raise ValueError('viewer start: completion pin differs')
    complete = rd(path)
    if 'context_renders_sha256' not in complete: return None
    renders = path.parent / 'CONTEXT_RENDERS.json'
    if sha(renders) != complete['context_renders_sha256']: raise ValueError('viewer start: render pin differs')
    originals = [r for r in rd(renders) if 'viewer_start' in r]
    if not originals: return None
    if any(complete.get(k) != expected.get(k) for k in ('file_id', 'source_sha256')): raise ValueError('viewer start: source or file differs')
    if len(originals) != 1: raise ValueError('viewer start: not one original observation')
    r = originals[0]; attempts = r.get('attempts') or []; start = r['viewer_start']
    if not (r.get('marked') is False and r.get('state') == 'initial' and not r.get('refused') and not r.get('action') and not r.get('inner')
            and not r.get('viewer_actions') and start == r.get('viewer_before') and attempts and attempts[-1].get('outcome') == 'used: the state reference'
            and r.get('native') and r['native'] == attempts[-1].get('native')): raise ValueError('viewer start: plan is not its original accepted observation')
    if start.get('source_sha256') != expected['source_sha256']: raise ValueError('viewer start: original source differs')
    return start


def qualify_arms(outs, file_id, read):
    """The producer's reading and binding of the saved arms that needs no WITHOUT comparison, shared by qualify_version and by qualify_first's decision
    before WITHOUT (root-bound-native-early-stop-and-damage-checks-20261029t095934395308z). outs: (name, job.py out dir) for normal, explored and, from
    qualify_version, without. Each arm: exactly one RESULT row for `file_id` (else ValueError), its plan at its pin, one common plan, the same COMPLETE
    source and raw reading. NORMAL: its proved inserted script (none: ValueError), held by those bytes only, its source reading's units. Explored: bound to
    the same script, no refused action, and EVERY saved route read (its initial view and each states/ entry). Missing, unreadable or malformed evidence
    raises (QUALIFY_FAILURES). -> {why, arms {name: (out, row, attempt, plan)}, ins, normal_route, normal_units, explored_route, explored_states, refused}"""
    rd, sha = reader(read); why, arms = [], {}
    for name, out in outs:
        res = rd(Path(out) / 'RESULT.json'); rows = [r for r in res.get('rows') or [] if r.get('file_id') == file_id]
        if len(rows) != 1: why.append(f'{name}: not exactly one row for the file'); continue
        plan = None
        if sha(res['plan']) != res.get('plan_sha256'): why.append(f'{name}: plan differs from its pin')
        else: plan = rd(res['plan'])
        arms[name] = (Path(out), rows[0], Path(rows[0]['attempt']), plan)
    if len(arms) != len(outs): raise ValueError('; '.join(why))
    common = lambda p: None if p is None else (json.dumps({k: v for k, v in p.items() if k not in QUALIFY_PLAN_KEYS}, sort_keys=True), json.dumps([c for c in p.get('source_commands') or [] if c.get('file_id') == file_id], sort_keys=True))
    plans = [v[3] for v in arms.values()]
    if None not in plans and any(common(p) != common(plans[0]) for p in plans): why.append('the arms ran different plans')
    src = lambda a: tuple((rd(a / 'COMPLETE.json').get(k)) for k in ('source_sha256', 'raw_reading_sha256'))
    sources = [src(v[2]) for v in arms.values()]
    if any(s != sources[0] for s in sources): why.append('the arms read different sources')
    (_, rn, an, _), (_, _, ax, _) = arms['normal'], arms['explored']
    normal_ref = {'path': str(an / 'COMPLETE.json'), 'sha256': sha(an / 'COMPLETE.json')}
    start = viewer_start(normal_ref, {'file_id': file_id, 'source_sha256': sources[0][0]}, read)
    for name, (_, _, _, plan) in arms.items():
        if name != 'normal' and plan is not None and plan.get('context_viewer_start') != (normal_ref if start is not None else None): why.append(f'{name}: viewer start is not the normal observation')
    ins = (rd(an / 'CONTEXT_ACQUISITION.json')['record'].get('target') or {}).get('inserted_script') or {}
    if not ins.get('response_sha256') or not ins.get('href'): raise ValueError('NORMAL has no proved inserted script: nothing to qualify')
    n_route = rd(an / 'ROUTE.json'); oc = (n_route.get('facts') or {}).get('optional_controls') or {}
    scripted = sum(1 for l in n_route.get('source_links') or [] if l.get('script_action'))
    if not (oc.get('other_objections') == 0 and (oc.get('inserted_version_objections') or 0) > 0 and rn.get('reasons') == ['native status PARTIAL']
            and n_route.get('error') == f'context: {scripted} declared script action(s) not attempted (report-control exploration disabled)'
            and (rn.get('source_reading') or {}).get('native_status') == 'OK'): why.append('NORMAL is held by more than its proved inserted bytes')
    ins_x = (rd(ax / 'CONTEXT_ACQUISITION.json')['record'].get('target') or {}).get('inserted_script') or {}
    if (ins_x.get('href'), ins_x.get('response_sha256')) != (ins['href'], ins['response_sha256']): why.append('the explored NORMAL run bound another inserted script')
    refused = [x.get('label') for x in rd(ax / 'CONTEXT_TRIALS.json') if x.get('refused')]
    if refused: why.append(f'explored NORMAL left {len(refused)} action(s) unobserved (refused): their states are unqualified')
    st = ax / 'states'
    return {'why': why, 'arms': arms, 'ins': ins, 'normal_route': n_route, 'normal_units': rd(an / 'source_reading/ROUTE.json').get('units'), 'explored_route': rd(ax / 'ROUTE.json'),
            'explored_states': {s.name: rd(s / 'ROUTE.json') for s in sorted(st.iterdir())} if st.is_dir() else {}, 'refused': refused}


def qualify_version(normal, explored, without, folder, runtime_manifest_sha256, file_id):
    """The producer for qualified_version. Three saved job outputs (job.py out dirs) of ONE file: NORMAL (production settings, the saved result),
    explored (the same row, context_explore True + qualification_diagnostic: every action observed via the diagnostic continuation, states diagnostic)
    and WITHOUT (context_explore True + qualification_withhold: the proved inserted script withheld). Each arm: exactly one RESULT row for `file_id`, its
    plan unchanged since its pin, the same selected source command and common settings (QUALIFY_PLAN_KEYS aside) and the same COMPLETE source and raw
    reading. passed only if: WITHOUT verified; NORMAL held by its proved inserted bytes only (typed counts, its one deficit exactly); every arm bound the
    same address and response; no explored action refused; the same state labels; the initial views and EVERY state equal (compare_views), and the
    source readings' units. The reading and binding that needs no WITHOUT is qualify_arms, the same code qualify_first decides with before WITHOUT.
    The record keeps every compared field per state and the evidence chain; written O_EXCL, never overwritten. -> the record"""
    read = {}  # every file this decision reads, with its sha256 at the moment it was read: all of them are the record's evidence
    rd, sha = reader(read)
    b = qualify_arms((('normal', normal), ('explored', explored), ('without', without)), file_id, read); why, arms, ins = b['why'], b['arms'], b['ins']
    (_, _, an, _), (_, _, ax, _), (_, rw, aw, _) = arms['normal'], arms['explored'], arms['without']; h = ins['response_sha256']
    exc = (rd(aw / 'CONTEXT_ACQUISITION.json')['record'].get('target') or {}).get('comparison_exception') or {}
    if not (exc.get('bound') is True and exc.get('response_sha256') == h and exc.get('address_sha256') == hashlib.sha256(ins['href'].encode()).hexdigest()): why.append('the arms did not bind the same inserted address and response')
    if rw.get('outcome') != 'verified_saved_output': why.append('WITHOUT not verified')
    w_route = rd(aw / 'ROUTE.json')
    fields = dict(compare_views(b['normal_route'], w_route), source_reading_units=b['normal_units'] == rd(aw / 'source_reading/ROUTE.json').get('units'))
    why += [f'initial views differ: {k}' for k, v in fields.items() if not v]
    xs, ws = b['explored_states'], (sorted(q.name for q in (aw / 'states').iterdir()) if (aw / 'states').is_dir() else [])
    if sorted(xs) != ws: why.append(f'state sets differ: NORMAL {len(xs)}, WITHOUT {len(ws)}')
    states = {'initial': compare_views(b['explored_route'], w_route)}
    states.update({lb: compare_views(xs[lb], rd(aw / 'states' / lb / 'ROUTE.json')) for lb in ws if lb in xs})
    why += [f'state {lb} differs: {k}' for lb, f in states.items() for k, v in f.items() if not v]
    ev = [{'role': role, 'path': str(x), 'sha256': read.get(str(x)) or sha(x)} for role, x in (('normal_result', Path(normal) / 'RESULT.json'), ('explored_result', Path(explored) / 'RESULT.json'), ('without_result', Path(without) / 'RESULT.json'),
          ('normal_route', an / 'ROUTE.json'), ('without_route', aw / 'ROUTE.json'), ('normal_acquisition', an / 'CONTEXT_ACQUISITION.json'), ('explored_acquisition', ax / 'CONTEXT_ACQUISITION.json'),
          ('without_acquisition', aw / 'CONTEXT_ACQUISITION.json'), ('explored_trials', ax / 'CONTEXT_TRIALS.json'))]
    named = {e['path'] for e in ev}; ev += [{'role': 'operand', 'path': x, 'sha256': h_} for x, h_ in sorted(read.items()) if x not in named]  # plans, COMPLETEs, source readings, every state and initial route
    rec = {'schema': QUALIFY_SCHEMA, 'script_sha256': h, 'address_sha256': hashlib.sha256(ins['href'].encode()).hexdigest(), 'file_id': file_id, 'runtime_manifest_sha256': runtime_manifest_sha256,
           'arm_runtime_manifests': {k: (v[3] or {}).get('runtime_manifest') for k, v in arms.items()}, 'outcome': 'held' if why else 'passed', 'reasons': why,
           'comparison': {'all_equal': all(fields.values()) and all(all(f.values()) for f in states.values()) and not b['refused'] and sorted(xs) == ws, 'initial_view': fields},
           'states': states, 'evidence': ev, 'limits': ['one filing: residual page-dependent risk, unmeasured', 'the explored NORMAL states are diagnostic evidence, never a native success']}
    out = Path(folder) / (h + '.json'); fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)  # never overwritten: one record per exact version
    with os.fdopen(fd, 'w') as f: json.dump(rec, f, indent=1, sort_keys=True)
    return rec


QUALIFY_ARMS = (('explored', {'context_explore': True, 'qualification_diagnostic': True}), ('without', {'context_explore': True, 'qualification_withhold': True}), ('release', {}))


def clean_row(r):  # job.main's own outcome contract: generated, no recorded technical failure, every reconstruct/verify (initial, each state, source reading) exited 0
    parts = [r] + [s for s in (r.get('states') or {}).values() if isinstance(s, dict)] + ([r['source_reading']] if isinstance(r.get('source_reading'), dict) else [])
    return r.get('generate_exit') == 0 and not r.get('technical_failures') and all(x.get('reconstruct_exit') == 0 and x.get('verify_exit') == 0 for x in parts)


def arm_row(out_dir, file_id, code, name):  # one child job's actual return: exit 0 or 1 only, exactly one finished own row agreeing with it, clean; else why it stops
    if code not in (0, 1): return None, f'held: {name} child job returned {code}'
    try: rows = [r for r in json.loads((out_dir / 'RESULT.json').read_bytes())['rows'] if r.get('file_id') == file_id]
    except (OSError, ValueError, KeyError, TypeError, AttributeError): return None, f'held: {name} child job wrote no readable RESULT'
    if len(rows) != 1: return None, f'held: {name} child job has {len(rows)} own rows'
    r = rows[0]
    if r.get('status') != 'done' or r.get('outcome') not in ('verified_saved_output', 'incomplete') or (code == 0) != (r.get('outcome') == 'verified_saved_output') or not clean_row(r):
        return None, f"held: {name} child row is not a clean finished attempt ({r.get('status')}, {r.get('outcome')}, exit {code})"
    return r, None


def technical(row, what):  # a failed qualification child or unreadable comparison is THIS row's technical failure, in the same fields check_output uses
    row.setdefault('technical_failures', []).append(what); row['reasons'] = row.get('reasons', []) + [f'technical failure: {what}']  # so clean_row and every row reader see it


def qualify_first(plan, plan_path, pin, out, record, result, row, k, generator, seconds, home):
    """Owner single-version policy (root-native-automatic-trigger-closeout-20261028t211651877057z): the FIRST file held ONLY by its own proved inserted
    script version (typed counts, no record for those bytes) qualifies that exact version once, inside this job. One exclusive claim
    (context.claim_version) before any arm; then one-row child jobs of THIS runtime through the native job CLI (-I -S -B, child accounting, the same
    per-child seconds, the enclosing process/STOP boundary): the explored NORMAL (diagnostic continuation); then the producer's own NORMAL/explored
    reading and binding (qualify_arms) and compare_views' text operand on every explored route: damaged evidence is a technical STOP, any reason a held
    version, and either stops here; else the comparison-only WITHOUT, then
    context.qualify_version over a frozen copy of this row's held result; only if it passed, exactly one ordinary attempt of the same file, whose
    actual row becomes this row's outcome (the held attempt kept). Never from a diagnostic or withhold plan, never twice for the same bytes, no retry."""
    store = plan.get('script_qualifications')
    if not store or plan.get('qualification_diagnostic') or plan.get('qualification_withhold'): return
    if row.get('outcome') != 'incomplete' or row.get('reasons') != ['native status PARTIAL'] or not clean_row(row): return  # an independent failure is never spent on arms
    a = Path(row['attempt'])
    try:
        oc = (json.loads((a / 'ROUTE.json').read_bytes()).get('facts') or {}).get('optional_controls') or {}
        ins = ((json.loads((a / 'CONTEXT_ACQUISITION.json').read_bytes()).get('record') or {}).get('target') or {}).get('inserted_script') or {}
    except (OSError, ValueError): return
    h = ins.get('response_sha256')
    if not (h and oc.get('other_objections') == 0 and (oc.get('inserted_version_objections') or 0) > 0) or (Path(store) / (h + '.json')).exists(): return
    done = row['qualification'] = {'script_sha256': h}
    if not claim_version(store, h): done['outcome'] = 'held: this version is claimed by another qualification'; save(result, record); return
    q = out / f'qualification_{k}'; (q / 'normal').mkdir(parents=True)
    save(q / 'normal' / 'RESULT.json', {'plan': str(plan_path), 'plan_sha256': pin, 'rows': [dict(row)]})  # the held NORMAL result, frozen as the record's evidence
    one, env, arms = dict(plan, source_commands=[plan['source_commands'][k]]), {'PATH': '/usr/bin:/bin', 'HOME': home}, {}
    def uncomparable(e): done.update(outcome='held: qualification not comparable', why=repr(e)[:300]); technical(row, 'qualification not comparable: ' + repr(e)[:300])
    try:
        ref = {'path': str(a / 'COMPLETE.json'), 'sha256': hashlib.sha256((a / 'COMPLETE.json').read_bytes()).hexdigest()}
        if viewer_start(ref, plan['source_commands'][k], {}) is not None: one['context_viewer_start'] = ref
    except QUALIFY_FAILURES as e: uncomparable(e); save(result, record); return
    for name, extra in QUALIFY_ARMS:
        if name == 'release' and done.get('outcome') != 'passed': break
        body = json.dumps(dict(one, **extra)).encode(); pp = q / f'{name}_PLAN.json'; pp.write_bytes(body); logs = q / f'{name}_logs'; logs.mkdir()
        done[name] = {'exit': child([sys.executable, '-I', '-S', '-B', str(HERE / 'job.py'), str(pp), hashlib.sha256(body).hexdigest(), str(q / name), generator, str(seconds)], logs, 'job', ROOT, env),
                      'observed': observed(logs, 'job'), 'result': str(q / name / 'RESULT.json')}
        save(result, record)
        arms[name], why = arm_row(q / name, row['file_id'], done[name]['exit'], name)
        if why: done['release_outcome' if name == 'release' else 'outcome'] = why; technical(row, f'qualification {name}: {why}'); break  # its dependent path stops, truthfully
        if name == 'explored':  # before any WITHOUT is spent: all own evidence read and bound first, so a false route never hides a damaged sibling
            try:
                b = qualify_arms((('normal', q / 'normal'), ('explored', q / 'explored')), row['file_id'], {})
                held = b['why'] + [f'{lb}: explored text proof not TRUE, so compare_views text_proved fails' for lb, r in [('initial', b['explored_route'])] + list(b['explored_states'].items()) if not compare_views(r, r)['text_proved']]
            except QUALIFY_FAILURES as e: uncomparable(e); break
            if held: done.update(outcome="held before WITHOUT: the NORMAL/explored evidence already fails the producer's own checks (no WITHOUT can pass it); WITHOUT and release not run", reasons=held); break
        if name == 'without':
            try:
                rec = qualify_version(q / 'normal', q / 'explored', q / 'without', store, plan['runtime_manifest']['sha256'], row['file_id'])
                done.update(outcome=rec['outcome'], reasons=rec['reasons'], record=str(Path(store) / (h + '.json')), record_sha256=hashlib.sha256((Path(store) / (h + '.json')).read_bytes()).hexdigest())
            except QUALIFY_FAILURES as e: uncomparable(e)
    if arms.get('release') is not None:  # the parent row becomes the released row whole (its own status, error, evidence, measurements, size, states, source); the held row kept whole
        held = {key: v for key, v in row.items() if key not in ('ordinal', 'file_id', 'qualification')}
        for key in held: del row[key]
        row.update({key: v for key, v in arms['release'].items() if key not in ('ordinal', 'file_id')}, held=held, released_by=str(q / 'release' / 'RESULT.json'))
    save(result, record)


def main(plan_path, pin, out_dir, generator=str(HERE / 'document.py'), seconds=900):  # common per-child time and file-size bounds
    body = Path(plan_path).read_bytes(); assert hashlib.sha256(body).hexdigest() == pin, 'plan pin mismatch'
    plan = json.loads(body)
    assert isinstance(plan.get('context_explore', True), bool), 'context_explore must be true or false'  # refused before any row, never a silent other path
    assert Path(plan['runtime_root']).resolve() == ROOT, 'the plan runtime is not this job\'s own checkout'  # one reviewed runtime for job, generation and reconstruct
    manifest = Path(plan['runtime_manifest']['path']).read_bytes(); assert hashlib.sha256(manifest).hexdigest() == plan['runtime_manifest']['sha256'], 'runtime manifest mismatch'
    pins = json.loads(manifest)['files']; tree = {str(p.relative_to(ROOT)) for p in (ROOT / 'driver').rglob('*') if p.is_file() and '__pycache__' not in p.relative_to(ROOT).parts}
    assert set(pins) == tree, 'the manifest is not the exact runtime inventory: ' + ', '.join(sorted(set(pins) ^ tree))[:500]  # every runtime file listed, nothing else (Python caches aside)
    for name, file_pin in pins.items(): assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == file_pin, 'runtime file mismatch: ' + name
    home = os.environ['HOME']  # the caller's own environment; no default
    out = Path(out_dir); out.mkdir(mode=0o700)  # a fresh job folder; an existing one is refused
    rows = [{'ordinal': k, 'file_id': r.get('file_id'), 'status': 'unstarted'} for k, r in enumerate(plan['source_commands'])]
    record = {'plan': str(plan_path), 'plan_sha256': pin, 'generator': generator, 'reconstruct': str(ROOT / 'driver/prepare/reconstruct.py'), 'rows': rows}
    result = out / 'RESULT.json'; save(result, record)
    for row in rows:
        k = row['ordinal']; attempt, logs = out / f'attempt_{k}', out / f'logs_{k}'
        logs.mkdir(); (logs / 'tmp').mkdir(); (logs / 'cache').mkdir()
        row.update(status='generating', attempt=str(attempt)); save(result, record)
        env = {'PATH': '/usr/bin:/bin', 'HOME': home, 'TMPDIR': str(logs / 'tmp'), 'XDG_CACHE_HOME': str(logs / 'cache')}
        row['generate_exit'] = child(bound(seconds) + [sys.executable, '-I', '-B', generator, str(plan_path), pin, str(k), str(attempt)], logs, 'generate', logs / 'tmp', env)
        row['attempt_exists'] = attempt.exists(); row['complete_exists'] = (attempt / 'COMPLETE.json').exists(); row['generate_observed'] = observed(logs, 'generate')
        row['attempt_bytes'] = size(attempt) if attempt.exists() else None
        if row['generate_exit'] != 0 or not row['complete_exists']:
            row.update(status='done', outcome='generation_failed', reasons=[f"generation exit {row['generate_exit']}"] + ([] if row['complete_exists'] else ['no COMPLETE.json']))
            save(result, record); continue
        expected = {'file_id': plan['source_commands'][k].get('file_id'), 'source_sha256': plan['source_commands'][k].get('source_sha256')}
        renv = {'PATH': '/usr/bin:/bin', 'TMPDIR': str(logs / 'tmp')}
        row['status'] = 'composing'; save(result, record)
        first, reasons, route = check_output(attempt, logs, expected, seconds, renv, row, result, record, '', row)
        row.update(first)
        if first.get('outcome'):  # the initial output is not this ordinal's own (or unreadable): evidence stays, dependent work stops, as before
            row.update(status='done', reasons=reasons); save(result, record); continue
        row['states'], states = {}, attempt / 'states'
        saved = sorted(sf.name for sf in states.iterdir()) if states.is_dir() else []
        named = [(l['tag']['byte_start'], a) for l in route.get('source_links') or [] if isinstance(l, dict) for a in l.get('activations') or [] if isinstance(a, dict) and a.get('state')]
        for start_, a in named:  # every activation's state is a saved folder directly inside states/ (so it gets the per-state check), with the ROUTE.json its activation records
            sf = states / a['state'] if a['state'] in saved else None
            if sf is None or not (sf / 'ROUTE.json').is_file(): reasons.append(f"activation at {start_} names a state with no saved route: {a['state']}")
            elif hashlib.sha256((sf / 'ROUTE.json').read_bytes()).hexdigest() != a.get('route_sha256'): reasons.append(f"activation at {start_}: state {a['state']} route differs from its recorded sha256")
        reasons += [f'saved state not referenced by any activation: {name}' for name in saved if name not in {a['state'] for _, a in named}]
        for name in saved:  # each labelled state: the same complete check as the initial output
            sl = logs / ('state_' + name.replace('@', '_')); sl.mkdir()
            st, st_reasons, _ = check_output(states / name, sl, expected, seconds, renv, row, result, record, f'state {name} ', row['states'].setdefault(name, {}))
            row['states'][name] = dict(st, reasons=st_reasons); reasons += [f'state {name}: {r}' for r in st_reasons]; save(result, record)
        sdir, said = attempt / 'source_reading', (route.get('facts') or {}).get('source_reading')  # the attempt's one typed source reading (document.source_child): a required owned reading
        if sdir.exists() or (said or {}).get('made'):  # the same complete check as the initial output and every state; its own logs; its reasons keep the document incomplete
            sl = logs / 'source_reading'; sl.mkdir()
            st, st_reasons, _ = check_output(sdir, sl, expected, seconds, renv, row, result, record, 'source reading ', row.setdefault('source_reading', {}))
            row['source_reading'] = dict(st, reasons=st_reasons); reasons += [f'source reading: {r}' for r in st_reasons]; save(result, record)
        row.update(status='done', outcome='incomplete' if reasons else 'verified_saved_output', reasons=reasons); save(result, record)
        if row['outcome'] == 'incomplete': qualify_first(plan, plan_path, pin, out, record, result, row, k, generator, seconds, home)  # the one automatic version qualification
    return 0 if all(r.get('outcome') == 'verified_saved_output' for r in rows) else 1


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, _stop); signal.signal(signal.SIGINT, _stop)
    a = sys.argv[1:]; sys.exit(main(*a[:4], *([int(a[4])] if len(a) > 4 else [])))
