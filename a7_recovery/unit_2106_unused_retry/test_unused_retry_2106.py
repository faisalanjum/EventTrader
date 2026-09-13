"""Red/green proof for the unused-retry closure, on durable TEST copies.

Runs INSIDE the boundary: the receipt's invocation and state paths are the
scratchpad run_dir, which only resolves under the mount, so a host-only test
cannot exercise preflight at all.

Every working copy is kept under this unit, not in a deleted temp directory.
The real G2 run is READ ONLY; the caller hashes it before and after.

No recovery report is repaired to make anything pass: the closure derives the
prior reading from the saved evidence through the approved F.read, so the
positive control is the REAL saved reply.

Zero AI calls.
"""
import collections
import copy
import hashlib
import io
import json
import os
import shutil
import sys

A7 = '/home/faisal/EventMarketDB-driver-recovery/a7_recovery'
HERE = os.path.join(A7, 'unit_2106_unused_retry')
VIEW = ('/tmp/claude-1000/-home-faisal-EventMarketDB/'
        '5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/'
        '.claude/plans/Drivers/experiments/harness_g1v3')
FORMAT_DIR = os.path.join(A7, 'unit_2020_codex_check')
REAL_G2 = os.path.join(A7, 'unit_2103_g23_grading/G2')
SESSION = ('/home/faisal/.claude/projects/-home-faisal-EventMarketDB/'
           '5ae9b86b-f0f6-4449-beee-9cac7cfa7200.jsonl')
#: a NEW uniquely tagged durable root each round; earlier proof is preserved,
#: never deleted, and no test setup touches actual state.
TAG = os.environ.get('A7_TEST_TAG', 'r2108')
WORKDIR = os.path.join(HERE, 'testruns_%s' % TAG)
SEGMENT = 5
sys.path.insert(0, HERE)
sys.path.insert(0, VIEW)
sys.path.insert(0, FORMAT_DIR)
sys.path.insert(0, os.path.join(A7, 'unit_2009/owner'))
os.chdir(VIEW)
import a7_unused_retry_closure_2106 as CL                          # noqa: E402
import a7_g1_build as G                                            # noqa: E402
import a7_g23_build as B                                           # noqa: E402
import a7_g1_complete_v2 as C                                      # noqa: E402
import a7_g1_workflow_gate as W                                    # noqa: E402
import a7_meaning_format_2105 as F                                 # noqa: E402

LAUNCH = json.load(io.open(os.path.join(REAL_G2, 'LAUNCH.json')))
B.bind_grading_scorer(
    os.path.join(os.path.dirname(G.__file__), 'scorers/score_exp5_current.py'),
    LAUNCH['owners']['grading_scorer'])
LIVE_RUN = LAUNCH['run_dir']
OUT_DIR = LAUNCH['candidate_dir']


def sha_file(path):
    with io.open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


#: externally supplied expectations - never measured by the subject
EXPECT = {
    'root': sha_file(os.path.join(LIVE_RUN, 'root.json')),
    'receipt': sha_file(os.path.join(LIVE_RUN, 'receipt.seg05.json')),
    'gate': W.owner_sha256(),
    'code': sha_file(os.path.join(FORMAT_DIR, 'a7_meaning_format_2105.py')),
    'rule': sha_file(os.path.join(FORMAT_DIR, 'A7_MEANING_FORMAT_RULE_2105.md')),
}

assert not os.path.isdir(WORKDIR), (
    '%s already exists; choose a new A7_TEST_TAG rather than erasing proof'
    % WORKDIR)
os.makedirs(WORKDIR)


def fresh(name):
    """A durable TEST copy of the live G2 run directory."""
    run = os.path.join(WORKDIR, name, 'run')
    shutil.copytree(LIVE_RUN, run)
    return run


def call(run, fn=CL.inspect, **kw):
    return fn(VIEW, FORMAT_DIR, OUT_DIR, run, SEGMENT, EXPECT['root'],
              EXPECT['receipt'], EXPECT['gate'], EXPECT['code'],
              EXPECT['rule'], SESSION, **kw)


RESULTS = []


def check(name, ok, detail=''):
    RESULTS.append((name, bool(ok)))
    print('  %-62s %s %s' % (name, 'PASS' if ok else 'FAIL', str(detail)[:90]))


# ---- 1. the block, and the closure ------------------------------------------
run = fresh('green')
root = G.load_root(run, EXPECT['root'])
blocked = G.lifecycle_problems(run, root, ['G2-002/G1a'], 1)
check('the pending segment 5 blocks the next publication',
      any('still pending' in p for p in blocked), blocked[:1])

ev, problems = call(run)
check('inspect accepts it from the REAL saved reply, no report supplied',
      ev is not None and not problems, problems[:1])
check('the prior reading is derived, recovered, and still originally invalid',
      ev and ev['prior_reading']['G2-001/G1a']['recovered'] is True
      and ev['prior_reading']['G2-001/G1a']['original_valid'] is False
      and ev['prior_reading']['G2-001/G1a']['prior_segment'] == 4)
check('the scanned-state count is transient, not part of the identity',
      ev and 'official_states_scanned' in ev['transient']
      and 'official_states_scanned' not in W._stable(ev))

final, problems = call(run, fn=CL.close)
check('close writes the finalization', final is not None and not problems,
      problems[:1])
check('zero credited, every lane uncalled, no verdict invented',
      final and final['ledger'] == {'scheduled': 0, 'valid': 0, 'invalid': 0,
                                    'retry': 0, 'uncalled': 1}
      and final['credited'] == 0 and final['validity'] == []
      and final['closure'] == CL.CLOSURE_KIND
      and final['state_audited'] is False)

# ---- 2. the publisher really admits the next primary -------------------------
# The refusals are checked on their OWN closed copy. Doing them after a
# successful publish_run made both pass on "segment 6 is still pending",
# which is a different refusal and would have hidden a real regression.
runR = fresh('refusals')
_f, _p = call(runR, fn=CL.close)
_i, problems = G.publish_run(OUT_DIR, runR, EXPECT['root'], ['G2-000/G1a'], 1)
check('an already-called primary is still refused',
      any('never be a primary again' in p for p in problems), problems[:1])
_i, problems = G.publish_run(OUT_DIR, runR, EXPECT['root'], ['G2-001/G1a'], 2)
check('the consumed reservation cannot be re-reserved',
      any('already reserved' in p for p in problems), problems[:1])
identity, problems = G.publish_run(OUT_DIR, run, EXPECT['root'],
                                   ['G2-002/G1a'], attempt=1)
check('G.publish_run actually publishes the next never-called primary',
      identity is not None and not problems, problems[:1])

# ---- 3. the whole-run connection, after closure ------------------------------
run2 = fresh('connection')
final2, problems = call(run2, fn=CL.close)
check('closure applied to the connection copy', final2 is not None, problems[:1])
digest, files = C.run_digest(run2)
with F.scope(EXPECT['code'], EXPECT['rule']):
    root2, doc2, lanes2, ev_problems = C.evidence(OUT_DIR, run2, EXPECT['root'],
                                                  digest, files)
    picked = lanes2.get('G2-001/G1a', {})
    check('C.evidence under F.scope selects the prior recovered attempt',
          not ev_problems and picked.get('selected') == 1, ev_problems[:1])
    ident = C.g23_identity(EXPECT['root'], run2)
    audit = (ident.get('meaning_format_recovery') or {}).get('attempts') or []
    mine = [a for a in audit if a.get('lane_id') == 'G2-001/G1a']
    check('the identity carries the recovery audit with original-invalid flags',
          mine and mine[0]['original_valid'] is False
          and mine[0]['recovered'] is True, mine[:1])
    # complete_g23 takes the SELECTED RELATIONS, not evidence's wrappers. My
    # previous run passed the wrappers, crashed, and I wrongly reported that
    # as a population property.
    per_lane = C.relations_from_run(lanes2)
    check('the recovered lane is present in the selected relations',
          'G2-001/G1a' in per_lane and 'G2-000/G1a' in per_lane,
          sorted(per_lane))
    result, cp = C.complete_g23(doc2, per_lane, ident)
    check('C.complete_g23 succeeds over the recovered population',
          result is not None, cp[:2])
    frozen = doc2['questions']
    check('the completion covers the EXACT frozen question population',
          result['questions'] == frozen, '%s of %s' % (result['questions'], frozen))
    reached = result['credited_questions'] + result['unresolved_questions']
    check('every frozen question reaches exactly one outcome',
          reached == frozen, '%s of %s' % (reached, frozen))
    check('every missing judgment is retained as unresolved, none dropped',
          result['unresolved_questions'] > 0, result['unresolved_questions'])

plain_root, plain_doc, plain_lanes, _pp = C.evidence(
    OUT_DIR, run2, EXPECT['root'], digest, files)
check('positive control: without recovery only the one originally-valid lane '
      'is selected',
      sorted(C.relations_from_run(plain_lanes)) == ['G2-000/G1a'],
      sorted(C.relations_from_run(plain_lanes)))

# ---- 4. positive-controlled corruptions --------------------------------------
run3 = fresh('bogus_prior')
prior = os.path.join(run3, 'whole', 'segment_004.whole.json')
check('positive control: the prior whole reply exists', os.path.isfile(prior))
doc = json.load(io.open(prior))
lane_entry = doc['lanes']['G2-001/G1a']
before = lane_entry['text']
# the reply text is a JSON STRING, so its quotes are escaped inside the file;
# an earlier version of this test substituted on the unescaped form, changed
# nothing, and passed for the wrong reason. Edit the decoded text instead and
# leave the recorded sha alone, so the owner's own hash check must fire.
lane_entry['text'] = before.replace('"true"', '"maybe"')
check('positive control: the prior reply text really changed',
      lane_entry['text'] != before)
io.open(prior, 'w').write(json.dumps(doc))
_e, problems = call(run3)
check('a tampered prior whole reply is refused by the owner hash check',
      _e is None and problems, problems[:1])

# CODEX SEQ 2108 COUNTEREXAMPLE, exactly: alter one judgment AND recompute the
# record's own hash and length, so the bound-answer check is satisfied and only
# the native official-state audit can refuse. The earlier closure accepted this.
runX = fresh('rehashed_prior')
priorX = os.path.join(runX, 'whole', 'segment_004.whole.json')
docX = json.load(io.open(priorX))
entry = docX['lanes']['G2-001/G1a']
altered = entry['text'].replace('"true"', '"false"', 1)
check('positive control: one judgment really was altered',
      altered != entry['text'])
entry['text'] = altered
entry['sha256'] = G._sha(altered)
entry['chars'] = len(altered)
io.open(priorX, 'w').write(json.dumps(docX))
selfok, selfproblems = G.whole_answers(runX, 4)
check('positive control: the rehashed record now SATISFIES the bound-answer '
      'check, so only the native audit can catch it',
      not selfproblems and selfok['G2-001/G1a'] == altered, selfproblems[:1])
_e, problems = call(runX)
check('a rehashed altered prior record is refused by the NATIVE audit',
      _e is None and any('native' in p for p in problems), problems[:1])

# and the native-audit failure control, through the owner itself
runY = fresh('native_audit_fails')
original_audit = G.audit_official_state
G.audit_official_state = lambda *a, **k: (['injected native audit failure'], {})
try:
    _e, problems = call(runY)
finally:
    G.audit_official_state = original_audit
check('a native audit failure refuses the closure',
      _e is None and any('injected native audit failure' in p
                         for p in problems), problems[:1])

run4 = fresh('missing_prior')
os.remove(os.path.join(run4, 'whole', 'segment_004.whole.json'))
_e, problems = call(run4)
check('a missing prior whole reply is refused', _e is None and problems,
      problems[:1])

run5 = fresh('valid_prior')
f4 = os.path.join(run5, 'finalization.seg04.json')
d4 = json.load(io.open(f4))
d4['validity'] = [['G2-001/G1a', True]]
io.open(f4, 'w').write(json.dumps(d4))
_e, problems = call(run5)
check('a prior reading recorded VALID is refused (nothing to recover)',
      _e is None and problems, problems[:1])

# ---- sidecar variants, through a CONTROLLED owner read ----------------------
# The receipt names the real sidecar path, so the variants are supplied by
# narrowly intercepting the owner's own read for THAT path only; every other
# read passes straight through. Each variant must refuse, and the untouched
# empty sidecar is the positive control.
SIDE_PATH = G.load_receipt(fresh('sidecar_probe'), SEGMENT)['state_path']
REAL_SIDE = G._read(SIDE_PATH)
check('positive control: the real sidecar is the empty owner shape',
      REAL_SIDE == {'run_id': 'run', 'states': []}, REAL_SIDE)

VARIANTS = collections.OrderedDict([
    ('states null', {'run_id': REAL_SIDE['run_id'], 'states': None}),
    ('states false', {'run_id': REAL_SIDE['run_id'], 'states': False}),
    ('states missing', {'run_id': REAL_SIDE['run_id']}),
    ('wrong run_id', {'run_id': 'some_other_run', 'states': []}),
    ('active', {'run_id': REAL_SIDE['run_id'], 'states': ['/tmp/s.json']}),
    ('extra key', {'run_id': REAL_SIDE['run_id'], 'states': [], 'x': 1}),
])
for label, variant in VARIANTS.items():
    runv = fresh('sidecar_%s' % label.replace(' ', '_'))
    original_read = G._read

    def scoped_read(path, _v=variant, _o=original_read):
        return copy.deepcopy(_v) if path == SIDE_PATH else _o(path)

    G._read = scoped_read
    try:
        _e, problems = call(runv)
    finally:
        G._read = original_read
    check('a %s sidecar is refused' % label,
          _e is None and any('sidecar' in p for p in problems), problems[:1])

# ---- parent-use and official-state refusals, via the owners -----------------
runU = fresh('parent_use')
original_parents = W._parent_records
W._parent_records = lambda *a, **k: ([('rec', 'line', {'id': 'x'})], [], [])
try:
    _e, problems = call(runU)
finally:
    W._parent_records = original_parents
check('a Workflow use naming this script is refused',
      _e is None and any('Workflow uses naming' in p for p in problems),
      problems[:1])

runS = fresh('official_state')
original_states = W._states_naming
W._states_naming = lambda sp: (['/tmp/wf_x.json'], 1, [])
try:
    _e, problems = call(runS)
finally:
    W._states_naming = original_states
check('an official state naming this script is refused',
      _e is None and any('official workflow states name' in p
                         for p in problems), problems[:1])

run8 = fresh('wrong_code_pin')
_e, problems = CL.inspect(VIEW, FORMAT_DIR, OUT_DIR, run8, SEGMENT,
                          EXPECT['root'], EXPECT['receipt'], EXPECT['gate'],
                          'a' * 64, EXPECT['rule'], SESSION)
check('a wrong externally supplied FORMAT CODE pin is refused',
      _e is None and any('scope refused' in p for p in problems), problems[:1])

run9 = fresh('output_present')
os.makedirs(os.path.join(run9, G.ERROR_DIRNAME), exist_ok=True)
io.open(os.path.join(run9, G.ERROR_DIRNAME,
                     G._seg(SEGMENT) + '.x.json'), 'w').write('{}')
_e, problems = call(run9)
check('existing output for this segment is refused',
      _e is None and any('errors' in p for p in problems), problems[:1])

run10 = fresh('refusal_artifact')
io.open(W.refusal_path(run10, SEGMENT), 'w').write('{}')
_e, problems = call(run10)
check('a segment carrying refusal-closure evidence is refused',
      _e is None and any('refusal evidence' in p for p in problems),
      problems[:1])

# ---- 5. interrupted closure --------------------------------------------------
run11 = fresh('resume')
ev11, p11 = call(run11)
check('positive control: clean before staging', ev11 is not None, p11[:1])
G._write_new(CL.evidence_path(G, run11, SEGMENT), G._pretty(ev11) + '\n')
f11, p11b = call(run11, fn=CL.close)
check('an interrupted closure resumes from its exact staged evidence',
      f11 is not None and not p11b, p11b[:1])

run12 = fresh('resume_tampered')
ev12, _ = call(run12)
bad = json.loads(json.dumps(ev12))
bad['reason'] = 'something else'
G._write_new(CL.evidence_path(G, run12, SEGMENT), G._pretty(bad) + '\n')
f12, p12 = call(run12, fn=CL.close)
check('staged evidence that differs is refused, never overwritten',
      f12 is None and any('not the evidence this run derives' in p
                          for p in p12), p12[:1])

run13 = fresh('accounting_orphan')
G._write_new(G.accounting_path(run13, SEGMENT), '{}\n')
f13, p13 = call(run13, fn=CL.close)
check('accounting without staged evidence is refused',
      f13 is None and any('accounting but no closure evidence' in p
                          for p in p13), p13[:1])

# ---- 6. late activity BETWEEN the two inspections ----------------------------
run14 = fresh('late_between')
original_account = G.account_segment
injected = {'done': False}


def account_then_inject(run_dir, n, root_doc):
    """Runs BETWEEN close's first and last inspection - the exact window."""
    out = original_account(run_dir, n, root_doc)
    if not injected['done']:
        injected['done'] = True
        os.makedirs(os.path.join(run_dir, G.ERROR_DIRNAME), exist_ok=True)
        io.open(os.path.join(run_dir, G.ERROR_DIRNAME,
                             G._seg(n) + '.late.json'), 'w').write('{}')
    return out


G.account_segment = account_then_inject
try:
    f14, p14 = call(run14, fn=CL.close)
finally:
    G.account_segment = original_account
check('positive control: the injection actually fired', injected['done'])
check('activity appearing BETWEEN the inspections is refused',
      f14 is None and any('errors' in p for p in p14), p14[:1])
check('and no finalization was written for it',
      not os.path.isfile(G.finalization_path(run14, SEGMENT)))

# ---- 7. unrelated new activity BETWEEN inspections must not block resume ----
run15 = fresh('unrelated_between')
ev15, p15 = call(run15)
check('positive control: clean before staging the unrelated case',
      ev15 is not None, p15[:1])
G._write_new(CL.evidence_path(G, run15, SEGMENT), G._pretty(ev15) + '\n')
original_states = W._states_naming
bumped = {'n': 0}


def scanning_more(script_path, _o=original_states):
    """Reports one MORE unrelated state on every later call - the same shape a
    genuinely new, unrelated workflow produces between the two inspections."""
    matches, scanned, problems = _o(script_path)
    bumped['n'] += 1
    return matches, scanned + bumped['n'], problems


W._states_naming = scanning_more
try:
    f15, p15b = call(run15, fn=CL.close)
finally:
    W._states_naming = original_states
check('positive control: the scanner count really changed between inspections',
      bumped['n'] >= 2, bumped['n'])
check('a staged closure still resumes when only the scanned count changed',
      f15 is not None and not p15b, p15b[:1])

# ---- 8. interrupted accounting -----------------------------------------------
run16 = fresh('resume_accounting')
ev16, _ = call(run16)
G._write_new(CL.evidence_path(G, run16, SEGMENT), G._pretty(ev16) + '\n')
receipt16 = G.load_receipt(run16, SEGMENT)
G._write_new(G.accounting_path(run16, SEGMENT),
             G._pretty(W._zero_capture_accounting(run16, SEGMENT, receipt16))
             + '\n')
f16, p16 = call(run16, fn=CL.close)
check('a closure interrupted after canonical accounting resumes',
      f16 is not None and not p16, p16[:1])

run17 = fresh('resume_bad_accounting')
ev17, _ = call(run17)
G._write_new(CL.evidence_path(G, run17, SEGMENT), G._pretty(ev17) + '\n')
G._write_new(G.accounting_path(run17, SEGMENT), G._pretty({'schema': 'x'}) + '\n')
f17, p17 = call(run17, fn=CL.close)
check('staged accounting that is not the canonical zero-capture one refuses',
      f17 is None and any('canonical zero-capture' in p for p in p17), p17[:1])

print()
passed = sum(1 for _n, ok in RESULTS if ok)
print('%d/%d checks passed' % (passed, len(RESULTS)))
sys.exit(0 if passed == len(RESULTS) else 1)
