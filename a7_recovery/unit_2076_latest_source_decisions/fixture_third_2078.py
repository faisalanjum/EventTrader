# -*- coding: utf-8 -*-
"""The THIRD round of `decision_correction_v6`, driven to the real candidate.

ZERO AI CALLS. Every reply is an explicitly synthetic TEST fixture written into
the isolated integration_a native store, never the real one. It REUSES the
completed TEST round-two build read-only and drives F's OWN v6 owners a third
time - no new phase, renderer, merge or count is written here beyond the six
seams `a4_v6_successor` binds.

  prepare_v6 -> receipt -> native state -> record -> finalize -> F.v6_shards
  over the FIRST ROUND's completed key -> signing gate -> candidate ->
  TEST signature -> actual compact lock.

The cold consumer leg runs in its own operation, consumer_successor_2072.py.
"""
import collections, contextlib, hashlib, importlib.util, json, os, runpy, sys
from pathlib import Path
from unittest.mock import patch

UNIT = Path(__file__).resolve().parent
A7 = UNIT.parent
for rel in ('unit_2009/owner', 'unit_2001/tests', 'unit_2023_source_correction',
            'unit_2041_decision_connection', 'unit_2061_settlement_connection',
            'unit_2063_source_closeout', 'unit_2065_closeout_connection',
            'unit_1955/lock_owners', 'unit_2069_targeted_source',
            'unit_2072_two_event_closeout'):
    sys.path.insert(0, str(A7 / rel))
sys.path.insert(0, str(UNIT))
import a4_review_composite as R                                    # noqa: E402
import synthetic_reading as SYN                                    # noqa: E402
import signer_proof as SP                                          # noqa: E402
import a4_source_correction as C2023                               # noqa: E402
import a4_source_decision as D2041                                 # noqa: E402
import a4_source_settlement as S2061                               # noqa: E402
import a4_source_closeout as C2065                                 # noqa: E402
import a4_targeted_source as T2069                                 # noqa: E402
import a4_v6_successor_chain as X                                  # noqa: E402
assert Path(X.__file__).resolve() == UNIT / 'a4_v6_successor_chain.py', X.__file__
CL, SK, K, HR, F = R.CL, R.SK, R.K, R.HR, R.F
LOCK_OWNERS = A7 / 'unit_1955/lock_owners'

TAG = os.environ['A7_TAG']
BASE = (A7 / 'unit_2072_two_event_closeout'
        / os.environ.get('A7_SUCC_BUILD', 'TEST_core_sucfix2072_b'))
projects = Path('/home/faisal/.claude/projects')
assert os.path.samefile(projects, A7 / 'unit_2009/integration_a/projects'), \
    'REFUSE real native-store write'
saved = json.loads((BASE / 'TEST_RESULT.json').read_text())
out = UNIT / ('TEST_' + TAG)
out.mkdir()
review, package = saved['review'], saved['review_package']
key_run, key_package = saved['key_run'], saved['key_package']
corr, decision = saved['corrections'], saved['decision']
settlement, closeout = saved['settlement'], saved['closeout']
run1 = saved['first_run']
first_run = saved['run2']
run3 = str(out / 'v6_round3')
findings = collections.OrderedDict(saved['findings'])
decision_findings = collections.OrderedDict(saved['decision_findings'])
settlement_findings = collections.OrderedDict(saved['settlement_findings'])
closeout_findings = collections.OrderedDict(saved['closeout_findings'])
find1 = collections.OrderedDict(saved['first_findings'])
first_findings = collections.OrderedDict(saved['round2_findings'])
CHAIN = ((run1, find1),)
PREVIOUS = (findings, decision_findings, settlement_findings, closeout_findings)
event, cleared_event = saved['event'][0], saved['cleared'][0]
first_name = saved['changed'][event]
checks, notes = [], collections.OrderedDict()
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
before_bytes = {str(p): sha(p) for p in sorted(Path(first_run).rglob('*'))
                if p.is_file()}


def check(name, ok, why=''):
    print('PASS' if ok else 'FAIL', name, str(why)[:300], flush=True)
    checks.append(name)
    assert ok, '%s %s' % (name, why)


def step(n, what):
    print('--- step %s: %s' % (n, what), flush=True)


def refuses(fn, what):
    try:
        fn()
    except (ValueError, AssertionError, SystemExit, OSError, KeyError) as exc:
        return ('%s: %s' % (type(exc).__name__, exc))[:240]
    raise AssertionError('%s did not refuse' % what)


def state_writer(base, label, text, run_id, prompt, script, script_path,
                 by_source, attempt=1, **over):
    real_ps = CL._prompt_scope

    @contextlib.contextmanager
    def phase_ps(bs):
        with real_ps(bs):
            with R._using(SK, prompt=lambda task: prompt,
                          render_launcher=lambda task, a=1: script):
                yield

    with R._using(CL, _prompt_scope=phase_ps):
        return SYN.write_final_state(CL, base, key_package, label, run_id,
                                     str(projects), by_source, text=text,
                                     script_path=script_path, attempt=attempt,
                                     **over)


def names(raw):
    return [(f.get('item') or {}).get('driver_name')
            for row in (K.RT.parse_reply(raw).get('rows') or [])
            for f in ((row.get('settled') or {}).get('facts') or [])]


with R.final_scope(review, package, bind_role=True) as proof:
    by_source = proof['by_source']
    bound = SK.bound(key_run, key_package)
    closed = C2065.bind(S2061.bind(D2041.bind(C2023.bind(bound, corr),
                                              decision), settlement), closeout)

    # ====== 1. this round's own finding, bound to the FIRST ROUND's reply ====
    step(1, 'the successor input: a lead on the accepted FIRST-ROUND v6 reply')
    _s, first_raws = X.first_round_accepted(closed, first_run, first_findings,
                                            PREVIOUS, CHAIN)
    first_hash = K._sha(first_raws[event])
    round3_findings = collections.OrderedDict([
        (event, [collections.OrderedDict([
            ('source_id', event), ('raw_sha256', first_hash),
            ('row', F._task_by_label(closed.evidence, event)['rows'][0]),
            ('field', 'TEST_ONLY'),
            ('decision', 'TEST_ONLY'),
            ('source_evidence',
             'TEST_ONLY successor lead on the first v6 reply')])])])
    check('the successor lead binds the FIRST ROUND, not the closeout it '
          'already superseded',
          first_hash != first_findings[event][0]['raw_sha256']
          and round3_findings[event] != first_findings.get(event))
    with C2065._render_scope(*PREVIOUS):
        closeout_raw = F.accepted_shards(closeout, closed,
                                         C2065.PHASE)[1][event]
    check('a lead bound to the superseded closeout reply is refused',
          refuses(lambda: X.successor_entries(
              closed, {event: [dict(round3_findings[event][0],
                                    raw_sha256=K._sha(closeout_raw))]},
              first_run, first_findings, PREVIOUS, CHAIN), 'a stale-raw lead'))

    def scope(b, f=None):
        return X.successor_scope(b, round3_findings if f is None else f,
                                 first_run, first_findings, PREVIOUS, CHAIN)

    # ============== 2. prepare through the EXISTING owner ===================
    step(2, 'prepare the successor round through F.prepare_v6')
    with scope(closed):
        prep = F.prepare_v6(run3, closed)
    check('F\'s own preparer publishes exactly the named population',
          prep['ok'] and [i['label'] for i in prep['invocations']] == [event],
          prep['problems'])
    receipt = K._load(os.path.join(run3, K.RECEIPT_NAME))
    check('the receipt is a real decision_correction_v6 phase from F, '
          'attempt 1 of its own round',
          receipt['phase'] == X.PHASE and receipt['attempt'] == 1
          and receipt['allowed'] == [event], receipt.get('phase'))
    check('the receipt PINS the completed first round as history, which F '
          'cannot do for itself',
          receipt['v1_evidence']['v6'] == F._run_evidence_pins(first_run))
    with scope(closed):
        prompt = F.v6_prompt(closed, event)
        script = F.render_v6_launcher(closed, event, 1)
    body = json.loads(prompt.split('[INPUT]\n', 1)[1])
    check('the body carries the FIRST ROUND\'s accepted reply, named for the '
          'round that produced it',
          body[X.PRIOR_KEY]['sha256'] == first_hash
          and body[X.PRIOR_KEY]['origin'] == X.PRIOR_ORIGIN
          and 'v5_shard' not in body)
    check('the declaration names exactly the keys the body sends',
          C2023.declared_keys(prompt) == list(body), C2023.declared_keys(prompt))
    check('the served base is the SOURCE-ONLY one, not F\'s answer-informed '
          'decision base',
          '[A7 SOURCE CORRECTION TASK]' in prompt
          and '[A4 FINAL DECISION TASK]' not in prompt)
    check('the receipt pins this event\'s own prompt, reproduced live',
          receipt['prompts'][event] == K._sha(prompt))
    notes['round2_prompt_sha256'] = K._sha(prompt)

    # ================= 3. one TEST reply, recorded and finalized ============
    step(3, 'one TEST successor answer, recorded and finalized')
    obj = K.RT.parse_reply(first_raws[event])
    hit = None
    for row in (obj.get('rows') or []):
        for fact in ((row.get('settled') or {}).get('facts') or []):
            name = ((fact.get('item') or {}).get('driver_name') or '')
            if name == first_name:
                hit = (name, 'zz_v6r3_settled_' + name)
                fact['item']['driver_name'] = hit[1]
                break
        if hit:
            break
    assert hit, 'the first round\'s own TEST fact is not in its shard'
    obj['open_issues'] = []
    text2 = SYN.dumps_exact(obj)
    spath = state_writer(run3, event, text2, 'wf_TEST_v6r3_%s' % TAG, prompt,
                         script, prep['invocations'][0]['scriptPath'],
                         by_source)
    assert not F.record_state(run3, spath)
    with scope(closed):
        fin = F.finalize(run3, closed)
    check('F\'s own finalizer proves the TEST successor reply',
          fin['ledger']['valid'] == 1 and fin['phase_complete']
          and not fin['retry'] and not fin['problems'],
          json.dumps(fin['ledger']))
    notes['round2_ledger'] = fin['ledger']
    notes['round2_driver_name'] = hit[1]

    # ========= 4. F's OWN v6 merge over the FIRST ROUND's key ===============
    step(4, 'F.v6_shards over the first round\'s key, and the existing gate')
    b2 = X.bind(closed, run3)
    with scope(b2):
        base_shards, base_raws, base_origins, base_bad = F.v5_shards(b2)
        shards, raws, origins, bad = F.v6_shards(b2)
    check('the merge BASE is the first round\'s completed key, not the '
          'closeout it replaced',
          not base_bad and first_name in names(base_raws[event])
          and base_origins[event] == X.ORIGIN, base_bad)
    check('every frozen event is present exactly once', not bad and len(shards) == 33,
          bad)
    counts = collections.Counter(origins.values())
    check('the TRUE origins are unchanged in shape: a second round of one '
          'phase re-stamps the same origin, it does not add a seventh',
          counts == collections.Counter(base_origins.values()), dict(counts))
    check('the successor content replaced the first round\'s for this event',
          hit[1] in names(raws[event]) and hit[0] not in names(raws[event]))
    check('the event nobody corrected keeps its CORRECTED content',
          saved['corrected'][cleared_event] in names(raws[cleared_event]))
    with scope(b2):
        gate = F.signing_gate(b2.events, b2)
    check('the existing gate accepts the complete successor TEST key',
          gate['ok'], gate['stops'][:2])
    notes['origins'] = dict(counts)
    notes['counts'] = {k: gate['counts'][k] for k in
                       ('rows_accounted', 'open_issues')}

    # ================= 5. every previous call, counted once =================
    # The ordinary binding is written FIRST because the candidate owner reads
    # A7_ORDINARY_BOUND at import time (measured, attempt core_v6fix2069_a).
    step(5, 'the count through the one authoritative owner')
    ordinary = out / 'ordinary_bound.json'
    R.RT.write_new(str(ordinary), json.dumps(
        dict({f: getattr(b2, f) for f in
              ('package', 'evidence', 'hr', 'events', 'hr_package')},
             corrections=corr, decision=decision,
             decision_correction=settlement, decision_correction_v5=closeout,
             decision_correction_v6=run3)))
    os.environ['A7_ORDINARY_BOUND'] = str(ordinary)
    sys.path.insert(0, str(A7 / 'unit_2005/owner'))
    import build_final_key_candidate as CAND                       # noqa: E402
    check('the candidate owner really bound this run\'s ordinary binding',
          CAND.ORDINARY == str(ordinary), CAND.ORDINARY)
    unbound = F.v6_ledger_before(b2)
    with scope(b2):
        served = F.v6_ledger_before(b2)
        full = CAND.signer_ledger_before(b2)
    # THE WHOLE CHAIN, not just the predecessor: a third round follows TWO
    # completed rounds, and F's own chain omits both of them.
    chain_calls = sum(X._finalized_scheduled(r) for r in (run1, first_run))
    first_calls = X._finalized_scheduled(first_run)
    check('F\'s chain omits BOTH completed rounds and the successor adds each '
          'exactly once', served - unbound == chain_calls,
          (unbound, served, chain_calls, first_calls))
    check('the authoritative owner then adds THIS round on top, once',
          full - served == notes['round2_ledger']['scheduled'], (served, full))
    # OUTSIDE the successor scope the authoritative owner reads F's unbound
    # chain, which stops one round short. The gap it leaves is exactly the
    # calls the first round really made.
    outside = CAND.signer_ledger_before(b2)
    check('MUTATION: without the successor\'s count seam the signer loses '
          'exactly the calls BOTH earlier rounds really made',
          full - outside == chain_calls
          and unbound + chain_calls + notes['round2_ledger']['scheduled'] == full,
          (unbound, outside, full, chain_calls, first_calls))
    notes['ledger_before_first_round'] = unbound
    notes['ledger_before_round2'] = served
    notes['signer_ledger_before'] = full

# ======================= 6. candidate, signer, lock =========================
step(6, 'the candidate over the successor key, with the successor evidence')
candidate = out / 'candidate'
with R.candidate_scope(review, package, key_run, key_package) as C:
    with X.successor_scope(b2, round3_findings, first_run, first_findings,
                           PREVIOUS, CHAIN):
        hashes, full_counts, cand_counts, signer_manifest = C.build(str(candidate))
        check('the candidate builder and its full verifier accept',
              not C.verify(str(candidate)))
    identity = json.loads((candidate / 'key_identity.json').read_text())
    want = ('v6_correction_receipt', 'v6_correction_finalization')
    check('the candidate binds THIS round\'s receipt and finalization',
          all(n in identity['bindings'] for n in want)
          and run3 in identity['runs'], list(identity['bindings']))
    check('every bound artifact is the exact byte on disk',
          all(identity['bindings'][n]['sha256']
              == sha(identity['bindings'][n]['path']) for n in want))
    pinned = K._load(identity['bindings']['v6_correction_receipt']['path'])
    check('and through that receipt the FIRST ROUND is pinned too, so a later '
          'edit to it diverges',
          pinned['v1_evidence']['v6'] == F._run_evidence_pins(first_run))
    check('no earlier phase was displaced',
          all(n in identity['bindings'] for n in
              ('correction_receipt', 'decision_receipt', 'settlement_receipt',
               'closeout_receipt')), list(identity['bindings']))
    prov = json.loads((candidate / 'provenance.json').read_text())
    check('the candidate carries each event\'s TRUE origin and exact raw hash',
          prov['origins'] == dict(origins)
          and all(prov['provenance']['events'][s]['raw_sha256'] == K._sha(raws[s])
                  for s in origins))
    check('the signer budget counts both v6 rounds',
          signer_manifest['budget']['before'] == notes['signer_ledger_before'],
          signer_manifest['budget'])
    notes['signer_budget_before'] = signer_manifest['budget']['before']

step(7, 'the TEST native signature and the actual compact lock')
with R.candidate_scope(review, package, key_run, key_package) as C:
    sig = candidate / 'signer'
    run_id = 'wf_TEST_v6r3_%s_signature' % TAG
    session = projects / '-home-faisal-EventMarketDB' / K.PARENT_SESSION
    sprompt = (sig / 'signer_prompt.txt').read_text()
    script_path = sig / 'final_sign.attempt1.js'
    sscript2 = script_path.read_text()
    (sig / 'scripts').mkdir(exist_ok=True)
    R.RT.write_new(str(sig / 'scripts/TEST_native_script.js'), sscript2)
    initial = K._load(os.path.join(CL.INITIAL_RUN, K.RECEIPT_NAME))
    template = Path(initial['states'][0]).name
    listdir = os.listdir

    def key_template(path):
        return [template] if Path(path) == session / 'workflows' else listdir(path)

    with patch.object(CL.F, 'signer_script', return_value=sscript2), \
            patch.object(CL.F, '_signer_context', return_value=(sprompt, sscript2)), \
            patch.object(SYN.os, 'listdir', side_effect=key_template):
        SYN.write_signature_state(
            CL, str(sig), b2, SP.LABEL, run_id, str(projects),
            row={'model': K.ROW_MODEL_ID, 'agentType': K.AGENT_TYPE},
            result={'model': K.MODEL, 'effort': K.EFFORT,
                    'agentType': K.AGENT_TYPE},
            state={'scriptPath': str(script_path)})
    proof_sig, sbad = SP.prove(str(sig), signer_manifest, 1, run_id,
                               str(session), {})
    check('the actual native proof accepts the explicit TEST signature',
          not sbad and proof_sig['outcome'] == 'signed'
          and 'establishes no source truth' in proof_sig['_text'], sbad[:2])
    env = {'A7_CANDIDATE_DIR': str(candidate), 'A7_ORDINARY_BOUND': str(ordinary),
           'A7_SIGNER_SESSION': str(session),
           'A7_AUTHORITY': '/home/faisal/.core827-orchestrator/archive_CODEX_2078.md'}
    with patch.dict(os.environ, env), patch.object(
            sys, 'argv', [str(LOCK_OWNERS / 'harvest_final_sign.py'), run_id, '1']):
        try:
            runpy.run_path(str(LOCK_OWNERS / 'harvest_final_sign.py'),
                           run_name='__main__')
        except SystemExit as exc:
            assert exc.code == 0, exc.code
        lspec = importlib.util.spec_from_file_location(
            'v6r3_lock', LOCK_OWNERS / 'build_final_key_lock.py')
        L = importlib.util.module_from_spec(lspec)
        lspec.loader.exec_module(L)
        with X.successor_scope(b2, round3_findings, first_run, first_findings,
                               PREVIOUS, CHAIN):
            try:
                L.main()
            except SystemExit as exc:
                assert exc.code == 0, exc.code
        lock = json.loads(Path(L.LOCK).read_text())
        receipt_l = json.loads(Path(L.RECEIPT).read_text())
        check('the actual compact lock verifies and every bound value refuses '
              'when mutated',
              not L.verify(lock)
              and receipt_l['every_bound_value_refuses_when_mutated']
              and not receipt_l['verify_problems_on_the_live_bytes'])
        check('the lock counts one TEST signer on top of BOTH v6 rounds',
              lock['call_accounting']['ledger_after']
              == notes['signer_budget_before'] + 1,
              json.dumps(lock['call_accounting']))
        notes['lock'] = {'path': L.LOCK,
                         'ledger_after': lock['call_accounting']['ledger_after']}

step(8, 'the first round is untouched by its successor')
check('every byte of the first v6 round this phase read is unchanged',
      {str(p): sha(p) for p in sorted(Path(first_run).rglob('*'))
       if p.is_file()} == before_bytes)
with R.final_scope(review, package, bind_role=True):
    fb = X.first_bound(closed, first_run)
    with X.first_round_scope(closed, first_run, first_findings, PREVIOUS, CHAIN):
        stale = F._receipt_still_the_proved_one(first_run, fb)
        redone = {s: K._sha(F.v6_prompt(fb, s)) for s in F.v6_labels(fb)}
first_receipt = K._load(os.path.join(first_run, K.RECEIPT_NAME))
check('and its frozen prompts and receipt still re-derive byte-identically '
      'under its OWN inputs',
      not stale and {s: first_receipt['prompts'][s] for s in redone} == redone,
      (stale, list(redone)))

R.RT.write_new(str(out / 'TEST_RESULT.json'), json.dumps({
    'kind': 'TEST ONLY: isolated fixtures; no model call, no real approval and '
            'no grading. The signature and lock are explicitly TEST.',
    'model_calls': 0, 'passed': len(checks), 'checks': checks, 'notes': notes,
    'base': str(BASE), 'review': review, 'review_package': package,
    'key_run': key_run, 'key_package': key_package, 'corrections': corr,
    'decision': decision, 'settlement': settlement, 'closeout': closeout,
    'first_run': first_run, 'run3': run3, 'candidate': str(candidate),
    'ordinary': str(ordinary), 'event': [event], 'cleared': [cleared_event],
    'findings': findings, 'decision_findings': decision_findings,
    'settlement_findings': settlement_findings,
    'closeout_findings': closeout_findings, 'first_findings': first_findings,
    'round3_findings': round3_findings,
    'changed': {event: hit[1]}, 'first_name': {event: hit[0]},
    'corrected': saved['corrected'], 'control': saved['control']},
    indent=1, default=str))
print('COMPLETE', len(checks), 'checks; zero AI calls;', out)
