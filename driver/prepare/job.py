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


def main(plan_path, pin, out_dir, generator=str(HERE / 'document.py'), seconds=900):  # common per-child time and file-size bounds
    body = Path(plan_path).read_bytes(); assert hashlib.sha256(body).hexdigest() == pin, 'plan pin mismatch'
    plan = json.loads(body)
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
    return 0 if all(r.get('outcome') == 'verified_saved_output' for r in rows) else 1


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, _stop); signal.signal(signal.SIGINT, _stop)
    a = sys.argv[1:]; sys.exit(main(*a[:4], *([int(a[4])] if len(a) > 4 else [])))
