"""Core SEQ 2087: independent read-only review of the REAL G1 preparation and
the UNRUN launch. Re-measures from live bytes; calls no model and writes only
this unit's own review file.

The harness is not imported from a convenient copy: the overlay the grading map
itself serves is materialized by symlink, every row re-hashed, and the owners
imported from THAT. A validator loaded from another tree would prove nothing.
"""
import collections
import decimal
import hashlib
import io
import json
import os
import re
import sys

A7 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP = os.path.join(A7, 'unit_2020_codex_check/map_real_grading_2086.tsv')
PREP = os.path.join(A7, 'unit_2020_codex_check/codex_gprep2086_a/PREPARATION.json')
COLD = os.path.join(A7, 'unit_2020_codex_check/codex_gprepcold2086_a/PREPARATION.json')
CAND = os.path.join(A7, 'unit_2020_codex_check/codex_gprep2086_a/g1_candidate')
RUN = os.path.join(A7, 'unit_2086_real_grading/g1')
LAUNCH = os.path.join(A7, 'unit_2086_real_grading/LAUNCH.json')
BUILDER = os.path.join(A7, 'unit_2020_codex_check/freeze_grading_launch_2086.py')
PREPARER = os.path.join(A7, 'unit_2020_codex_check/prepare_real_grading_2085.py')
SIGNER_TRANSCRIPT = os.path.join(
    A7, 'unit_2083_signer_collection/evidence/signer/wf_cf398299-777.transcript.jsonl')
HARNESS_LOGICAL = ('/tmp/claude-1000/-home-faisal-EventMarketDB/'
                   '5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/'
                   '.claude/plans/Drivers/experiments/harness_g1v3')

# The prefixes Codex SEQ 2087 STATES. Only what he wrote is transcribed here; the
# full value is measured below and printed, never typed.
STATED = collections.OrderedDict([
    ('PREPARATION.json', (PREP, 'a889236369af76bd')),
    ('prepare_real_grading_2085.py', (PREPARER, '0b7fe5b90c832f53')),
    ('map_real_grading_2086.tsv', (MAP, '7cd94d5d84e00cfe')),
    ('LAUNCH.json', (LAUNCH, '3754473566bf0d8e')),
    ('freeze_grading_launch_2086.py', (BUILDER, '4e1ec36f5737208d')),
])

results = collections.OrderedDict()
problems = []


def sha_file(path):
    with io.open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def canon_sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()


def check(name, condition, detail=None):
    results[name] = bool(condition)
    if not condition:
        problems.append('%s: %s' % (name, detail))
    print('PASS' if condition else 'FAIL', name, '' if detail is None else str(detail)[:200],
          flush=True)


def prompt_body(text):
    """The trailing JSON payload. The rules preamble also contains braces, so the
    body is found by parsing, never by the first '{'."""
    for i in range(len(text)):
        if text[i] == '{':
            try:
                return json.loads(text[i:], object_pairs_hook=collections.OrderedDict,
                                  parse_float=decimal.Decimal)
            except ValueError:
                continue
    raise ValueError('no JSON body in this prompt')


# ---------------------------------------------------------------- 1. the map's own overlay
def served_harness(shadow):
    """Materialize exactly what the grading map serves at the harness path."""
    rows = []
    for line in io.open(MAP, encoding='utf-8'):
        parts = line.rstrip('\n').split('\t')
        if len(parts) >= 4:
            rows.append(parts)
    dir_rows = [r for r in rows if r[0] == HARNESS_LOGICAL]
    if len(dir_rows) != 1:
        raise ValueError('the map serves %d harness directories' % len(dir_rows))
    base = dir_rows[0][1]
    os.mkdir(shadow)
    for name in os.listdir(base):
        os.symlink(os.path.join(base, name), os.path.join(shadow, name))
    overrides = 0
    for logical, physical, want, _mode in rows:          # ORDER: later rows win
        if not logical.startswith(HARNESS_LOGICAL + '/') or os.path.isdir(physical):
            continue
        if logical.count('/') != HARNESS_LOGICAL.count('/') + 1:
            continue
        got = sha_file(physical)
        if got != want:
            raise ValueError('%s is %s, the map pins %s' % (physical, got, want))
        target = os.path.join(shadow, os.path.basename(logical))
        if os.path.islink(target):
            os.unlink(target)
        os.symlink(physical, target)
        overrides += 1
    return base, overrides


def main():
    shadow = os.path.join(os.environ['A7_REVIEW_SHADOW'], 'served_harness')
    base, overrides = served_harness(shadow)
    expected = sum(1 for r in io.open(MAP, encoding='utf-8')
                   for c in [r.rstrip('\n').split('\t')]
                   if len(c) >= 4 and c[0].startswith(HARNESS_LOGICAL + '/')
                   and c[0].count('/') == HARNESS_LOGICAL.count('/') + 1
                   and not os.path.isdir(c[1]))
    check('the overlay re-hashes EVERY harness file row the map pins',
          overrides == expected and expected > 0,
          '%s + %d of %d overrides' % (base, overrides, expected))
    sys.path.insert(0, shadow)
    import a7_g1_build as G
    import a7_g23_build as B
    import a7_g1_workflow_gate as W
    homes = {mod.__name__: os.path.realpath(os.path.dirname(mod.__file__))
             for mod in (G, B, W)}
    check('every owner this review loaded came from the served overlay, not another tree',
          set(homes.values()) == {os.path.realpath(shadow)} and len(homes) == 3, homes)

    inventory_source, key_rows = None, []
    for line in io.open(MAP, encoding='utf-8'):
        cols = line.rstrip('\n').split('\t')
        if len(cols) < 4:
            continue
        if cols[0] == '/tmp/a7_reference_inventory.json':
            inventory_source = cols[1]
        elif cols[0].startswith('/tmp/a7_approved_key/'):
            key_rows.append((cols[0], cols[1], cols[2]))

    launch = json.load(io.open(LAUNCH))
    prep = json.load(io.open(PREP))
    cold = json.load(io.open(COLD))
    doc = json.load(io.open(os.path.join(CAND, 'a7_g1_candidate.json')))

    # ------------------------------------------------------------ 2. the stated pins
    stated = collections.OrderedDict(
        (name, sha_file(path)) for name, (path, _pfx) in STATED.items())
    check('every artifact Codex SEQ 2087 states re-hashes to the prefix he wrote',
          all(stated[name].startswith(pfx) for name, (_p, pfx) in STATED.items()),
          [name for name, (_p, pfx) in STATED.items() if not stated[name].startswith(pfx)]
          or list(stated.values()))
    check('LAUNCH.json names the preparation, cold proof, profile and candidate it pins',
          all(sha_file(launch[k]) == launch[k + '_sha256']
              for k in ('preparation', 'cold_proof', 'input_profile'))
          and sha_file(os.path.join(launch['candidate_dir'], 'a7_g1_candidate.json'))
          == launch['candidate_sha256'])

    # ------------------------------------------------------------ 3. runtime owners
    scorer = os.path.join(os.path.dirname(G.__file__), 'scorers', 'score_exp5_current.py')
    measured = collections.OrderedDict([
        ('a7_g1_build', sha_file(G.__file__)),
        ('a7_g23_build', sha_file(B.__file__)),
        ('a7_g1_complete_v2', sha_file(os.path.join(shadow, 'a7_g1_complete_v2.py'))),
        ('raw_transport', sha_file(os.path.join(shadow, 'raw_transport.py'))),
        ('audit_worker_access', sha_file(os.path.join(shadow, 'audit_worker_access.py'))),
        ('grade_batch_owner', sha_file(os.path.join(shadow, G.BATCH_OWNER))),
        ('lean_probe_agent', sha_file(G.LIVE_AGENT_DEF)),
        ('score_exp5', sha_file(os.path.join(shadow, 'scorers', 'score_exp5.py'))),
        ('grading_scorer', sha_file(scorer))])
    check('all nine pinned runtime owners re-hash to the frozen root',
          dict(measured) == dict(launch['owners']) and len(measured) == 9,
          sorted(k for k in set(measured) | set(launch['owners'])
                 if measured.get(k) != launch['owners'].get(k)) or 'all nine match')
    check('the workflow size gate re-hashes',
          W.owner_sha256() == launch['workflow_gate_sha256'])

    # ------------------------------------------------------------ 4. population arithmetic
    pop, bud = prep['population'], prep['budget']
    leg = pop['legs']
    key = prep['key_identity']
    check('every leg accounts the same accepted gold rows',
          all(leg[k]['auto'] + leg[k]['unmatched_gold'] == key['accepted_rows'] for k in leg),
          {k: leg[k]['auto'] + leg[k]['unmatched_gold'] for k in leg})
    check('questions are exactly the unmatched gold of the three legs',
          sum(leg[k]['unmatched_gold'] for k in leg) == pop['questions'], pop['questions'])
    check('two blind reviewers per batch, and reviewers are not legs',
          pop['reviewer_calls'] == pop['batches'] * len(G.GRADER_LANES)
          and len(G.GRADER_LANES) == 2 and len(leg) == 3,
          '%d batches x %d reviewers = %d' % (pop['batches'], len(G.GRADER_LANES),
                                              pop['reviewer_calls']))
    check('the budget spends the completed 668 once and stays under the ceiling',
          bud['spent_before'] == 668
          and bud['after_initial'] == bud['spent_before'] + pop['reviewer_calls']
          and bud['max_grader_calls'] == pop['reviewer_calls'] * bud['max_attempts_per_row']
          and bud['after_max'] == bud['spent_before'] + bud['max_grader_calls']
          and bud['after_max'] < bud['ceiling'] and bud['under_ceiling'] is True,
          '%d -> %d worst, ceiling %d' % (bud['spent_before'], bud['after_max'], bud['ceiling']))
    check('grading-run events and KEY source events are two different counts, both stated',
          pop['events'] == 36 and key['events'] == 33 and pop['answers'] == 382
          and key['accepted_rows'] == 163,
          'run %d/%d, key %d/%d' % (pop['events'], pop['answers'], key['events'],
                                    key['accepted_rows']))

    # ------------------------------------------------------------ 5. the cold re-derivation
    check('the cold proof re-derives the SAME candidate and prompt bytes in a fresh process',
          cold['g1_candidate_sha256'] == prep['g1_candidate_sha256']
          and set(prep['checks']) < set(cold['checks'])
          and any('re-derive byte-identically' in c for c in cold['checks']),
          sorted(set(cold['checks']) - set(prep['checks'])))

    # ------------------------------------------------------------ 6. the rendered prompts
    rows = doc['batch_rows']
    bad_card, qids = [], set()
    forbidden = collections.Counter()
    for row in rows:
        raw = io.open(os.path.join(CAND, row['prompt_path']), 'rb').read()
        if hashlib.sha256(raw).hexdigest() != row['prompt_sha256'] or len(raw) != row['prompt_bytes']:
            bad_card.append((row['batch_id'], 'prompt bytes moved'))
            continue
        body = prompt_body(raw.decode('utf-8'))
        for question in body['questions']:
            qids.add(question.get('question_id'))
            if list(question) != ['question_id', 'reference_card']:
                bad_card.append((question.get('question_id'), list(question)))
                continue
            found = B.card_problems(question['reference_card'])   # THE OWNER decides
            if found:
                bad_card.append((question['question_id'], found))
        blob = json.dumps(body['questions'])
        for name in ('final_outcome', 'du_worthy', 'hard_classes', 'record_kind_note',
                     'driver_state', 'verdict', 'gold'):
            if name in blob:
                forbidden[name] += 1
    check('all %d frozen prompt files still carry their recorded bytes' % len(rows),
          not any(p == 'prompt bytes moved' for _b, p in bad_card), len(rows))
    check('every rendered reference card passes the OWNER whitelist validator',
          not bad_card and len(qids) == pop['questions'], bad_card[:3] or len(qids))
    check('no adjudicated conclusion name appears anywhere in the asked questions',
          not forbidden, dict(forbidden) or 'none')
    check('the asked question ids are exactly the frozen bindings',
          qids == {q['question_id'] for q in doc['question_bindings']}
          and len(doc['question_bindings']) == pop['questions'])
    check('the candidate is armed for nothing', doc['armed_calls'] == 0)

    ctl = prep['controls']
    control_ids = ([ctl['positive_control']['question_id']]
                   + list(ctl['near_miss_control']['question_ids']))
    check('the retained controls are real asked questions, not placeholders',
          set(control_ids) <= qids and len(control_ids) == 3
          and ctl['same_locator_pairs'] == ctl['same_locator_pairs_differing_in_a_scored_field']
          and ctl['scored_fields'] == 33 and ctl['scored_fields_owner'],
          '%d same-locator pairs, all differing in a scored field; owner %s'
          % (ctl['same_locator_pairs'], ctl['scored_fields_owner']))
    check('every saved answer is answered, and they are the population being graded',
          prep['trace_statuses'] == {'answered': pop['answers']}, prep['trace_statuses'])
    check('the reference inventory the run reads is the live pinned bytes',
          sha_file(inventory_source) == prep['reference_inventory_sha256']
          and cold['reference_inventory_sha256'] == prep['reference_inventory_sha256'],
          prep['reference_inventory_sha256'])
    check('the cold process re-derived the same saved-answer evaluation',
          cold['evaluation_sha256'] == prep['evaluation_sha256'],
          prep['evaluation_sha256'])
    check('the approved-key mount serves the REAL locked key, not a substituted one',
          all(sha_file(physical) == want and 'codex_cand2082_a' in physical
              for _l, physical, want in key_rows) and len(key_rows) == 3,
          [os.path.basename(p_) for _l, p_, _w in key_rows])

    # ------------------------------------------------------------ 7. the unrun launch
    root_sha = launch['root_sha256']
    root = G.load_root(RUN, root_sha)
    lanes = [r['lane_id'] for r in root['rows']]
    check('the root carries every primary lane and nothing has been called',
          len(lanes) == launch['total_primary_lanes'] == pop['reviewer_calls']
          and G.lane_states(RUN) == {}
          and json.load(io.open(os.path.join(RUN, 'state.seg01.json')))['states'] == [],
          '%d lanes, 0 called' % len(lanes))
    selected = lanes[:launch['first_segment_lanes']]
    fits, _p = W._script_bytes(CAND, root, selected, W.PRIMARY_ATTEMPT)
    over, _p = W._script_bytes(CAND, root, lanes[:len(selected) + 1], W.PRIMARY_ATTEMPT)
    check('the published segment is the MAXIMAL admissible prefix, re-rendered',
          fits == launch['first_script_bytes'] <= W.SCRIPT_BYTE_LIMIT
          and over > W.SCRIPT_BYTE_LIMIT
          and sha_file(os.path.join(RUN, 'grade_batch.seg01.js')) == launch['first_script_sha256'],
          '%d lanes = %d bytes; %d lanes = %d > %d'
          % (len(selected), fits, len(selected) + 1, over, W.SCRIPT_BYTE_LIMIT))
    check('the receipt and invocation are the bytes on disk',
          sha_file(os.path.join(RUN, 'receipt.seg01.json')) == launch['first_receipt_sha256']
          and sha_file(os.path.join(RUN, 'invocation.seg01.json')) == launch['invocation_sha256'])

    script = io.open(os.path.join(RUN, 'grade_batch.seg01.js'), encoding='utf-8').read()
    bound = json.loads(re.search(r'const BOUND = (\{.*?\})\nconst PINNED_MODEL',
                                 script, re.S).group(1))
    arg_keys = json.loads(re.search(r'const ARG_KEYS = (\[.*?\])', script,
                                    re.S).group(1).replace('\n', ' '))
    args = json.load(io.open(os.path.join(RUN, 'invocation.seg01.json')))['args']
    by_batch = {r['batch_id']: os.path.join(CAND, r['prompt_path']) for r in rows}
    check('the script carries the frozen prompt BYTES, not a reference to them',
          all(io.open(by_batch[b], encoding='utf-8').read() == text
              for b, text in zip(bound['batch_ids'], bound['prompts']))
          and bound['prompt_sha256'] == [r['prompt_sha256'] for r in args]
          and bound['invocation_sha256'] == launch['invocation_sha256'],
          '%d embedded prompts' % len(bound['prompts']))
    check('the invocation rows carry exactly the argument shape the script demands',
          all(sorted(r) == sorted(arg_keys) for r in args)
          and [r['batch_id'] for r in args] == bound['batch_ids']
          and all(r['attempt'] == 1 for r in args))
    check('every lane is pinned to the reviewed transport',
          all(r['model'] == launch['lane']['model']
              and r['runtime_model_id'] == launch['lane']['runtime_model_id']
              and r['effort'] == launch['lane']['effort']
              and r['agentType'] == launch['lane']['agentType']
              and r['disallowedTools'] == launch['lane']['disallowedTools']
              and r['max_output_tokens'] == launch['lane']['max_output_tokens'] for r in args),
          launch['lane'])
    check('the script opens no file and needs no path, so a copy runs identically',
          not re.search(r'\brequire\(|^import |\bfs\.|process\.env|/home/faisal|/tmp/',
                        script, re.M))

    # ------------------------------------------------------------ 8. the declared attachment
    records = [json.loads(l) for l in io.open(SIGNER_TRANSCRIPT, encoding='utf-8') if l.strip()]
    declared = json.load(io.open(launch['input_profile']))['expected_input_for_served_lanes']
    extra = [i for i, r in enumerate(records) if not isinstance(r.get('message'), dict)]
    record = records[declared['record_index']]
    check('the declared per-lane input IS the attachment proved in the signer transcript',
          extra == [declared['record_index']]
          and record.get('type') == declared['record_type']
          and canon_sha(record[declared['payload_field']]) == declared['payload_sha256']
          and record[declared['payload_field']].get('type') == 'remote_session_change',
          declared['payload_sha256'])
    check('every root row declares that one input', 
          all(r['expected_input'] == declared for r in root['rows']))

    review = collections.OrderedDict([
        ('kind', 'Core SEQ 2087 independent review; read-only, no model call'),
        ('model_calls', 0),
        ('passed', sum(1 for v in results.values() if v is True)),
        ('problems', problems),
        ('checks', [k for k, v in results.items() if v is True]),
        ('measured', collections.OrderedDict([
            ('preparation', sha_file(PREP)), ('preparer', sha_file(PREPARER)),
            ('map', sha_file(MAP)), ('launch', sha_file(LAUNCH)),
            ('builder', sha_file(BUILDER)), ('root', sha_file(os.path.join(RUN, 'root.json'))),
            ('script', sha_file(os.path.join(RUN, 'grade_batch.seg01.js'))),
            ('script_bytes', launch['first_script_bytes']),
            ('candidate', launch['candidate_sha256'])])),
        ('stated_prefixes_measured_in_full', stated),
        ('transport_requirement', 
         'Workflow refuses a scriptPath it cannot already read: the frozen script under '
         'EventMarketDB-driver-recovery/ is not launchable in place. The proved precedent is '
         'the real signer (wf_cf398299-777), whose official state records '
         'scratchpad/signer_2083/final_sign.attempt1.js - a byte-identical copy of the packet '
         'script. G1 needs the same: copy grade_batch.seg01.js into the session scratchpad, '
         're-hash the copy against the receipt pin BEFORE launching, launch from the copy, and '
         'hand the recorder that same path. No frozen identity changes; only the vehicle.'),
        ('not_claimed',
         'G2 and G3 populations are absent from the preparation and the launch, which is '
         'correct: they are not knowable before the G1 identity results exist. The budget '
         'block sizes G1 only (192 initial, 384 worst); it is not a whole-grading ceiling.'),
    ])
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'REVIEW_2087.json')
    with io.open(out, 'x', encoding='utf-8') as fh:
        fh.write(json.dumps(review, indent=1) + '\n')
    print('\nwrote', out)
    print('passed', review['passed'], 'problems', len(problems))
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
