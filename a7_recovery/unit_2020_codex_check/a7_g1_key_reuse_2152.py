"""Reuse native G1 readings only when their complete task is unchanged.

Both runs keep their original evidence. The sole input-selection owner says
which tasks match; the existing native reader proves the answers, and the
existing partial policy, reconciler and scorer still decide every outcome.
The public entry accepts approved handles, never a supplied state or verdict.
"""
import copy
from pathlib import Path
import sys

import a4_review_composite as R
import a7_g1_build as G
import a7_g23_build as B
import a7_g1_complete_v2 as C
import a7_partial_grading_2095 as P
import a7_current_key_context_2148 as CURRENT
import a7_signed_key_input_2149 as INPUT

CODE_PIN = 'g1_key_reuse_owner_sha256'
SELECTION_PIN = 'g1_key_reuse_selection_sha256'
REPORT_PIN = 'g1_key_reuse_inputs_sha256'
SELECTION_DIR = Path(__file__).resolve().parents[1] / 'unit_2152_g1_reuse'


def _merge(original, current, problems, selection, claimed):
    """PRIVATE: combine only states already proved by the two native readers."""
    if original is None or current is None:
        raise ValueError('no proved native evidence state for G1 reuse')
    old_root, old_doc, old_lanes = original
    root, doc, lanes = current
    if (old_doc != selection['original_candidate']
            or doc != selection['current_candidate']
            or G.task_kind(doc) != 'G1' or G.task_kind(old_doc) != 'G1'):
        raise ValueError('native evidence names another reuse candidate')
    for field in ('lane', 'owners', 'max_attempts', 'max_output_tokens', 'rules_block_sha256'):
        if root[field] != old_root[field]:
            raise ValueError('G1 reuse changed ' + field)
    if doc['launchers']['lanes'] != old_doc['launchers']['lanes']:
        raise ValueError('G1 reuse changed blind lane identities')
    for frozen, candidate, records in ((root, doc, lanes), (old_root, old_doc, old_lanes)):
        ids = [r['lane_id'] for r in frozen['rows']]
        if (len(ids) != len(set(ids)) or set(ids) != set(records)
                or ids != [r['lane_id'] for r in candidate['launchers']['rows']]):
            raise ValueError('native evidence does not cover the complete candidate')
    missing = [r['lane_id'] + ' has no selected valid attempt'
               for r in root['rows'] if lanes[r['lane_id']]['selected'] is None]
    if problems != missing:
        raise ValueError('G1 reuse native evidence refused: %s' % problems)

    carry = selection['carry_batches']
    if len(set(carry.values())) != len(carry):
        raise ValueError('one original batch cannot supply two current batches')
    carry_lanes = {r['lane_id'] for r in root['rows'] if r['batch_id'] in carry}
    eligible = selection['eligible_lanes']
    if (len(eligible) != len(set(eligible)) or carry_lanes & set(eligible)
            or carry_lanes | set(eligible) != set(lanes)
            or {r['batch_id'] for r in root['rows'] if r['lane_id'] in carry_lanes} != set(carry)):
        raise ValueError('reuse and changed lanes do not partition the full candidate')
    if any(lane in carry_lanes for _attempt, lane in claimed):
        raise ValueError('a carried G1 task is already reserved in the new run')
    old_rows = {r['lane_id']: r for r in old_root['rows']}
    combined = copy.deepcopy(lanes)
    for row in root['rows']:
        lane, batch = row['lane_id'], row['batch_id']
        if lane not in carry_lanes:
            continue
        rec = lanes[lane]
        if rec['attempts'] or rec['selected'] is not None or rec['relation'] is not None:
            raise ValueError('a carried G1 task has new evidence that cannot be hidden')
        old_lane = carry[batch] + '/' + lane.rsplit('/', 1)[1]
        if old_lane not in old_rows:
            raise ValueError('the carried G1 lane has no original evidence')
        for field in ('prompt_sha256', 'expected_input'):
            if row[field] != old_rows[old_lane][field]:
                raise ValueError('the carried G1 task changed ' + field)
        combined[lane] = dict(copy.deepcopy(old_lanes[old_lane]), batch_id=batch)
    # No safety message is removed by pattern. The earlier comparison proved
    # the ONLY native diagnostics were missing selections. Re-derive that list
    # from the combined state; P.lifecycle retains its exact exhaustion check.
    missing = [r['lane_id'] + ' has no selected valid attempt'
               for r in root['rows'] if combined[r['lane_id']]['selected'] is None]
    return (root, doc, combined), missing


def evaluate(E, report_path, g1, action):
    """One original-context proof, one current-key context, approved G1 only."""
    g1 = copy.deepcopy(g1)
    pins = g1.get('pins') or {}
    selection_path = SELECTION_DIR / 'g1_reuse_inputs_2152.py'
    for name, path in ((CODE_PIN, __file__), (SELECTION_PIN, selection_path),
                       (REPORT_PIN, report_path)):
        if pins.get(name) != G._sha_file(str(path)):
            raise ValueError('unapproved G1 reuse input: ' + name)
    sys.path.insert(0, str(SELECTION_DIR))
    import g1_reuse_inputs_2152 as SELECT
    selection = SELECT.derive(str(report_path), pins[REPORT_PIN])
    report = selection['report']
    if (g1['candidate_dir'] != selection['candidate_dir']
            or pins.get('candidate_sha256') != report['g1_candidate_sha256']):
        raise ValueError('G1 reuse handle names another current candidate')

    def checked(original_producer, inputs):
        if (original_producer != report['original_producer']
                or E.g1 != report['original_g1']):
            raise ValueError('the original producer or G1 handle changed')
        original = B._lifecycle(report['original_g1'])
        for name, module in (('context_sha256', CURRENT), ('input_owner_sha256', INPUT)):
            if G._sha_file(module.__file__) != report[name]:
                raise ValueError('the approved current-key input owner changed')
        if G._sha_file(report['signed_key_report']) != report['signed_key_report_sha256']:
            raise ValueError('the approved signed-key report changed')
        signed = E.K._load(report['signed_key_report'])
        import build_a5_exp5_kit as A5
        import a7_reference_inventory as RI
        with CURRENT.current_key(E, signed['preparation'], signed['preparation_sha256']) as (_C, bound, _prepared), \
                INPUT.approved_inputs(E, A5, report['signed_key_report'],
                                      report['signed_key_report_sha256']):
            if G._approved_bound() != bound:
                raise ValueError('the grading consumer is not bound to the approved key')
            producer = E.PR.reuse(report['evaluation'], report['evaluation_sha256'])
            if producer != report['producer']:
                raise ValueError('the current saved-answer evaluation changed')
            if (G._sha_file(report['reference_inventory']) != report['reference_inventory_sha256']
                    or G.live_key()[1] != report['key_identity']):
                raise ValueError('the current reference inventory or key changed')
            native = B.refuse

            def reused(candidate_dir, run_dir, expected):
                if (candidate_dir, run_dir) != (g1['candidate_dir'], g1['run_dir']):
                    return native(candidate_dir, run_dir, expected)
                if expected != pins:
                    raise ValueError('the current G1 reuse pins changed')
                state, problems = native(candidate_dir, run_dir, expected)
                return _merge(original, state, problems, selection, G._claimed(run_dir))

            with R._using(RI, INVENTORY_PATH=report['reference_inventory']), \
                    R._using(B, refuse=reused), P.scope(pins[P.POLICY_PIN]):
                result = action(producer, inputs, g1)
        for handle in (report['original_g1'], g1):
            expected = handle['pins']
            if C.run_digest(handle['run_dir']) != (expected['run_tree_sha256'], expected['run_file_count']):
                raise ValueError('G1 native evidence changed during evaluation')
        if G._sha_file(str(report_path)) != pins[REPORT_PIN]:
            raise ValueError('G1 reuse input report changed during evaluation')
        return result

    return E.with_prepared_inputs(checked)
