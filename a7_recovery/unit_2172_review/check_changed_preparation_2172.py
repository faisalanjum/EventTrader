"""Read-only checks on the frozen 38-question selection and its preparation.

Nothing is prepared, run or called here. Four things are measured:

  * the SELECTION regenerates from its own populations and equals the two
    already reviewed frontiers exactly;
  * both BASELINE candidates bind to the full population under the same
    producer, G1 and key identity the selection names;
  * the EVIDENCE the payload compares against is the right evidence - across
    every G2 question rendered both ways, the two surfaces differ only where
    the already approved display owner decodes a menu token;
  * the RULES growth leaves the transport headroom the payload will assert.

    python3 -B check_changed_preparation_2172.py <out.json>
"""
import collections
import copy
import glob
import hashlib
import io
import json
import os
import sys

A7 = '/home/faisal/EventMarketDB-driver-recovery/a7_recovery'
K = os.path.join(A7, 'unit_2020_codex_check')
CURRENT = os.path.join(K, 'codex_currentg232157_c')
CORRECTIVE = os.path.join(A7, 'unit_2161_execution')
G3_BASELINE = os.path.join(A7, 'unit_2159_current_g3/core_g3prep2159_c/G3')
JOB = os.path.join(A7, 'unit_1947/logs/attempt_codex_changedprep2171_a')
BOUNDARY = ('---------------------------------- BOUNDARY '
            '----------------------------------\n')

FRONTIERS = (
    (os.path.join(A7, 'unit_2170_review/IDENTITY_POPULATION_2170.json'),
     '05675f2b1d5f3532e5bac1e0a743b9ca2377db8558e74446e7ce3443a76155cf'),
    (os.path.join(A7, 'unit_2171_review/NULL_DELTA_BOUNDARY_2171.json'),
     '09786a4169de359fb8bae17c6fdeb4494561dd0561483e4828cdc534b83bb2bc'),
)
SELECTION = (os.path.join(K, 'CHANGED_GRADING_SELECTION_2171.json'),
             '1107680379634723be19afe255bd19864ebdf06e0b65eaeb199ee871d8998710')
PAYLOAD = (os.path.join(K, 'prepare_changed_grading_2171.py'),
           '804803834e52926d3c1fc5e40256cfeb448414317f93a1c9bf7db4a6d9595043')


def pinned(ref):
    path, expected = ref
    raw = io.open(path, 'rb').read()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('%s is not at its pin' % os.path.basename(path))
    return raw


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def plain(obj):
    return json.loads(json.dumps(obj, sort_keys=True))


def body(text):
    at = text.index('[EVENT]\n') + len('[EVENT]\n')
    return json.JSONDecoder().raw_decode(text[at:])[0]


def events_by_question(texts):
    """One event per question, with the batch-local label removed - the same
    normalisation the payload applies before comparing."""
    out = {}
    for text in texts:
        for event in body(text)['events']:
            if len(event['questions']) != 1:
                raise ValueError('a served event carries %d questions'
                                 % len(event['questions']))
            event = copy.deepcopy(event)
            qid = event['questions'][0]['question_id']
            event.pop('event')
            if qid in out:
                # A batch is launched on two grader lanes, so one question is
                # rendered twice. That is lawful only if both renderings carry
                # the SAME evidence, so require it rather than skip it.
                if plain(out[qid]) != plain(event):
                    raise ValueError('two renderings of %s differ' % qid)
                continue
            out[qid] = event
    return out


def prompt_texts(pattern):
    return [io.open(path, encoding='utf-8').read()
            for path in sorted(glob.glob(pattern))]


def bound_prompts(pattern):
    texts = []
    for path in sorted(glob.glob(pattern)):
        raw = io.open(path, encoding='utf-8').read()
        at = raw.index('const BOUND =')
        obj, _ = json.JSONDecoder().raw_decode(raw[at + len('const BOUND ='):].lstrip())
        texts.extend(obj['prompts'])
    return texts


def main(out):
    selection = json.loads(pinned(SELECTION))
    pinned(PAYLOAD)
    frontier = set()
    for ref in FRONTIERS:
        doc = json.loads(pinned(ref))
        frontier |= ({q for q, v in doc['questions'].items()
                      if v['verdict'] != 'unaffected'}
                     if 'core_additional_question_ids' not in doc
                     else set(doc['core_additional_question_ids']))

    # 1. the selection regenerates from its own populations
    regenerated = set()
    for kind, groups in selection['populations'].items():
        for group, rows in groups.items():
            leg, source_id = group.split('|', 1)
            for row in rows:
                regenerated.add(
                    'M' + sha('G2|%s|%s|%d|%d' % (leg, source_id, row[0], row[1]))[:16]
                    if kind == 'G2' else
                    'X' + sha('G3|%s|%s|%d' % (leg, source_id, row))[:16])
    listed = set(selection['question_ids']['G2']) | set(selection['question_ids']['G3'])

    # 2. both baselines bind to the full population and the same identities
    full = json.load(io.open(os.path.join(CURRENT, 'a7_g23_candidate.json')))
    baselines = {}
    for kind in ('G2', 'G3'):
        ref = selection['baseline_candidates'][kind]
        doc = json.loads(pinned((ref['path'], ref['sha256'])))
        baselines[kind] = collections.OrderedDict([
            ('population_is_the_full_population',
             plain(doc['population']) == plain(
                 full['g2_pairs'] if kind == 'G2' else full['g3_idxs'])),
            ('identities_match_the_full_candidate', all(
                plain(doc.get(field)) == plain(full.get(field))
                for field in ('producer_identity', 'g1_identity', 'key_identity'))),
            ('input_correction_sha256', doc.get('input_correction_sha256')),
            ('matched_population_is_the_full_g2',
             plain(doc.get('matched_population')) == plain(full['g2_pairs'])
             if kind == 'G3' else None)])

    # 3. the evidence surfaces, compared question by question
    original = events_by_question(prompt_texts(
        os.path.join(CURRENT, 'G2/prompts/*.txt')))
    corrective = events_by_question(bound_prompts(
        os.path.join(CORRECTIVE, 'G2/run/grade_batch.*.js')))
    g3_baseline = events_by_question(prompt_texts(
        os.path.join(G3_BASELINE, 'prompts/*.txt')))
    both = sorted(set(original) & set(corrective))
    identical, decoded_only, other = [], [], []
    for qid in both:
        left, right = original[qid], corrective[qid]
        if plain(left) == plain(right):
            identical.append(qid)
            continue
        stripped = copy.deepcopy(left), copy.deepcopy(right)
        for side in stripped:
            side['questions'][0]['produced_record']['item'].pop('slice_parts', None)
        (decoded_only if plain(stripped[0]) == plain(stripped[1])
         else other).append(qid)
    graded_correctively = sorted(set(selection['question_ids']['G2']) & set(corrective))

    # 4. rules growth and the headroom the payload will assert
    frozen_rules = len(prompt_texts(
        os.path.join(CURRENT, 'G2/prompts/G2-000.prompt.txt'))[0].split(BOUNDARY)[0])
    corrective_rules = len(bound_prompts(
        os.path.join(CORRECTIVE, 'G2/run/grade_batch.seg01.js'))[0].split(BOUNDARY)[0])
    contract_delta = 142
    largest = max(row['prompt_bytes'] for row in full['batching']['rows'])

    # 5. the native job, read and not interpreted
    owner = dict(line.split('\t', 1) for line in
                 io.open(os.path.join(JOB, 'owner.tsv'), encoding='utf-8').read().splitlines()
                 if '\t' in line)
    exit_path = os.path.join(JOB, 'exit')
    job = collections.OrderedDict([
        ('state_in_owner_tsv', owner.get('state')),
        ('exit_file_present', os.path.exists(exit_path)),
        ('raw_exit', io.open(exit_path).read().strip()
         if os.path.exists(exit_path) else None),
        ('stdout_bytes', os.path.getsize(os.path.join(JOB, 'stdout.txt'))),
        ('stderr_bytes', os.path.getsize(os.path.join(JOB, 'stderr.txt'))),
        ('payload_pid_alive', os.path.exists('/proc/%s' % owner.get('payload_pid', '0'))),
        ('report_present', os.path.exists(os.path.join(
            K, 'codex_changedprep2171_a/CHANGED_GRADING_PREPARATION_2171.json')))])

    # 6. the produced candidates, if the native job finished successfully.
    produced = None
    if job['raw_exit'] == '0' and job['report_present']:
        produced = collections.OrderedDict()
        clauses = {
            'scope': '   empty only for the whole company on metric, guidance '
                     'and surprise',
            'headline': "   streak do not create one. Keep the source's "
                        'headline comparison;',
            'null_change': 'Leave change_value null when it could merely be derived'}
        for kind in ('G2', 'G3'):
            root = os.path.join(K, 'codex_changedprep2171_a', kind)
            candidate = json.load(io.open(os.path.join(root, 'a7_g1_candidate.json')))
            baseline_ref = selection['baseline_candidates'][kind]
            baseline = json.load(io.open(baseline_ref['path']))
            expected = events_by_question([
                io.open(os.path.join(os.path.dirname(baseline_ref['path']),
                                     row['prompt_path']), encoding='utf-8').read()
                for row in baseline['batch_rows']])
            rendered, served, sizes, hashes_ok = {}, collections.Counter(), [], True
            for row in candidate['batch_rows']:
                text = io.open(os.path.join(root, row['prompt_path']),
                               encoding='utf-8').read()
                hashes_ok = hashes_ok and sha(text) == row['prompt_sha256']
                sizes.append(row['prompt_bytes'])
                for name, needle in clauses.items():
                    served[name] += text.count(needle)
                for event in body(text)['events']:
                    event = copy.deepcopy(event)
                    qid = event['questions'][0]['question_id']
                    event.pop('event')
                    rendered[qid] = event
            same = sum(1 for qid, event in rendered.items()
                       if plain(event) == plain(expected[qid]))
            lanes = (candidate['launchers']['rows']
                     if isinstance(candidate['launchers'], dict)
                     else candidate['launchers'])
            produced[kind] = collections.OrderedDict([
                ('population_equals_the_selection_subset',
                 plain(candidate['population']) == plain(selection['populations'][kind])),
                ('every_prompt_hash_verifies', hashes_ok),
                ('rendered_question_ids_equal_the_selection',
                 sorted(rendered) == selection['question_ids'][kind]),
                ('questions', len(rendered)),
                ('evidence_identical_to_the_baseline', same),
                ('corrected_clauses_served', dict(served)),
                ('input_correction_sha256', candidate.get('input_correction_sha256')),
                ('batches', len(candidate['batch_rows'])),
                ('launcher_rows', len(lanes)),
                ('made_calls', candidate.get('made_calls')),
                ('largest_prompt_bytes', max(sizes))])

    json.dump(collections.OrderedDict([
        ('schema', 'a7-changed-preparation-check/2172'),
        ('selection', collections.OrderedDict([
            ('g2_questions', len(selection['question_ids']['G2'])),
            ('g3_questions', len(selection['question_ids']['G3'])),
            ('expected_questions', selection['expected_questions']),
            ('expected_matches_the_lists',
             selection['expected_questions']['G2'] == len(selection['question_ids']['G2'])
             and selection['expected_questions']['G3'] == len(selection['question_ids']['G3'])),
            ('populations_regenerate_the_listed_ids', regenerated == listed),
            ('listed_equals_my_two_frontiers', listed == frontier),
            ('input_correction_sha256', selection['input_correction_sha256'])])),
        ('baselines', baselines),
        ('g2_evidence_surfaces', collections.OrderedDict([
            ('questions_rendered_both_ways', len(both)),
            ('byte_identical', len(identical)),
            ('differ_only_in_slice_parts', len(decoded_only)),
            ('differ_elsewhere', len(other)),
            ('differ_elsewhere_identities', other),
            ('selected_g2_also_graded_correctively', graded_correctively),
            ('selected_and_corrective_are_byte_identical',
             all(q in identical for q in graded_correctively))])),
        ('one_question_per_event', collections.OrderedDict([
            ('original_g2_events', len(original)),
            ('corrective_g2_events', len(corrective)),
            ('g3_baseline_events', len(g3_baseline))])),
        ('transport', collections.OrderedDict([
            ('frozen_g2_rules_bytes', frozen_rules),
            ('corrective_g2_rules_bytes', corrective_rules),
            ('contract_adds_bytes', contract_delta),
            ('rules_growth_vs_frozen', corrective_rules + contract_delta - frozen_rules),
            ('largest_existing_prompt_bytes', largest),
            ('largest_prompt_under_contract_rules',
             largest + corrective_rules + contract_delta - frozen_rules),
            ('script_byte_limit', 524288)])),
        ('native_job', job),
        ('produced_candidates', produced),
    ]), io.open(out, 'w', encoding='utf-8'), indent=1)
    print('selection', len(listed), 'regenerates', regenerated == listed,
          '| equals my frontiers', listed == frontier)
    print('G2 surfaces: identical', len(identical), 'slice-only', len(decoded_only),
          'other', len(other))
    print('job state', job['state_in_owner_tsv'], '| exit file',
          job['exit_file_present'], '| report', job['report_present'])
    if produced:
        for kind, row in produced.items():
            print(kind, 'questions', row['questions'], 'evidence identical',
                  row['evidence_identical_to_the_baseline'], 'clauses',
                  row['corrected_clauses_served'], 'lanes', row['launcher_rows'])


if __name__ == '__main__':
    main(sys.argv[1])
