# -*- coding: utf-8 -*-
"""The ONE input-selection rule for the corrected-key G1 reuse. Codex SEQ 2152.

This preparation and root's consumer import the SAME owner, so the set of
carried lanes and the set that must be called again can never drift between
them.

NOTHING HERE IS TYPED. No company, event, batch or row name appears in this
file: membership is derived from the externally pinned 2150 report and the two
candidates it pins, by comparing the complete model-facing input and the
complete row binding. A batch carries only when its prompt BYTES, its produced
indexes, its question ids and its full-row positions are all identical and its
items differ nowhere outside `_gold`; anything else is a changed batch that
must be answered again.

WHAT THIS DOES NOT DO, and must not be read as doing: it says nothing about
native replies. Whether a carried lane really has a proved valid reading is the
existing evidence owner's judgment, not this file's. This only decides which
lanes are eligible to be published and which old batch each carried batch
corresponds to.
"""
import collections
import hashlib
import io
import json
import os

#: the approved runtime input every lane of the original root carried
PROFILE_REL = 'unit_2068_input_recovery/input_profile_2068.json'
PROFILE_SHA256 = ('78b58fe7fd5ba60b9199ada86fe27d90101ceb57cd7617db158e2ea724'
                  'e2da18')
CANDIDATE_NAME = 'a7_g1_candidate.json'
A7 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _sha_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def _read_bytes(path):
    with io.open(path, 'rb') as fh:
        return fh.read()


def _pinned(path, want, what):
    raw = _read_bytes(path)
    got = _sha_bytes(raw)
    if got != want:
        raise ValueError('the %s is %s, not the pinned %s: %s'
                         % (what, got, want, path))
    return raw


def _pinned_json(path, want, what):
    return json.loads(_pinned(path, want, what).decode('utf-8'))


def _by_event(candidate, what):
    """{(leg, source_id): batch_row}, refusing anything not one-to-one."""
    event_of = {}
    for binding in candidate['question_bindings']:
        key = (binding['leg'], binding['source_id'])
        seen = event_of.setdefault(binding['batch_id'], key)
        if seen != key:
            raise ValueError('%s batch %s binds two events: %s and %s'
                             % (what, binding['batch_id'], seen, key))
    out = {}
    for row in candidate['batch_rows']:
        batch_id = row['batch_id']
        if batch_id not in event_of:
            raise ValueError('%s batch %s binds no event' % (what, batch_id))
        key = event_of[batch_id]
        if key in out:
            raise ValueError('%s event %s has two batches: %s and %s'
                             % (what, key, out[key]['batch_id'], batch_id))
        out[key] = row
    if len(out) != len(candidate['batch_rows']):
        raise ValueError('%s does not map one batch per event' % what)
    return out


def _events(rows, what):
    """{(leg, source_id): recorded event input}, refusing a repeat."""
    out = {}
    for row in rows:
        key = (row['leg'], row['source_id'])
        if key in out:
            raise ValueError('%s records event %s twice' % (what, key))
        out[key] = row
    return out


def _prompt(candidate_dir, row, what):
    """The batch's prompt BYTES, refused unless they are its own pinned ones."""
    return _pinned(os.path.join(candidate_dir, row['prompt_path']),
                   row['prompt_sha256'], '%s prompt for %s'
                   % (what, row['batch_id']))


def _without_gold(items):
    return [{k: v for k, v in item.items() if k != '_gold'} for item in items]


def derive(report_path, expected_sha256):
    """Which lanes may be reused, which must be called, and against what.

    -> a dict with the report, both candidates, the carried batch mapping, the
    changed batches, the lanes eligible for publication IN NEW ROOT ORDER, the
    batches whose gold moved under an unchanged prompt, the candidate directory
    and the approved runtime input.
    """
    report = _pinned_json(report_path, expected_sha256, '2150 report')
    current_path = report['g1_candidate']
    current_dir = os.path.dirname(current_path)
    current = _pinned_json(current_path, report['g1_candidate_sha256'],
                           'current G1 candidate')
    original_dir = report['original_g1']['candidate_dir']
    original = _pinned_json(
        os.path.join(original_dir, CANDIDATE_NAME),
        report['original_g1']['pins']['candidate_sha256'],
        'original G1 candidate')

    new_by_event = _by_event(current, 'the current candidate')
    old_by_event = _by_event(original, 'the original candidate')
    if set(new_by_event) != set(old_by_event):
        raise ValueError('the two candidates do not describe the same events')
    new_events = _events(report['current_events'], 'the report current events')
    old_events = _events(report['original_events'], 'the report original events')
    if set(new_events) != set(new_by_event) or set(old_events) != set(old_by_event):
        raise ValueError('the report and the candidates name different events')

    carry, changed, gold_moved = collections.OrderedDict(), [], []
    for key in sorted(new_by_event):
        new_row, old_row = new_by_event[key], old_by_event[key]
        new_prompt = _prompt(current_dir, new_row, 'the current candidate')
        old_prompt = _prompt(original_dir, old_row, 'the original candidate')
        # the report must describe the SAME prompt the candidate serves, or the
        # comparison below would be about a text nobody will send
        for prompt, event, what in ((new_prompt, new_events[key], 'current'),
                                    (old_prompt, old_events[key], 'original')):
            if event['prompt'].encode('utf-8') != prompt:
                raise ValueError('the %s report prompt for %s is not the '
                                 'candidate prompt' % (what, key))
        same_input = (new_prompt == old_prompt
                      and new_row['produced_idxs'] == old_row['produced_idxs']
                      and new_row['question_ids'] == old_row['question_ids']
                      and new_events[key]['full_positions']
                      == old_events[key]['full_positions'])
        if same_input and (_without_gold(new_events[key]['items'])
                           == _without_gold(old_events[key]['items'])):
            carry[new_row['batch_id']] = old_row['batch_id']
            if new_events[key]['items'] != old_events[key]['items']:
                gold_moved.append(new_row['batch_id'])
        else:
            changed.append(new_row['batch_id'])

    changed_set = set(changed)
    if len(changed_set) != len(changed) or changed_set & set(carry):
        raise ValueError('a batch is both carried and changed')
    if len(carry) + len(changed) != len(new_by_event):
        raise ValueError('the carried and changed batches do not partition '
                         'the population')
    known = {row['batch_id'] for row in current['batch_rows']}
    eligible, seen = [], set()
    for row in current['launchers']['rows']:
        if row['batch_id'] not in known:
            raise ValueError('lane %s names no batch of this candidate'
                             % row['lane_id'])
        if row['lane_id'] in seen:
            raise ValueError('lane %s appears twice' % row['lane_id'])
        seen.add(row['lane_id'])
        if row['batch_id'] in changed_set:
            eligible.append(row['lane_id'])
    covered = {lane.rsplit('/', 1)[0] for lane in eligible}
    if covered != changed_set:
        raise ValueError('the eligible lanes do not cover exactly the changed '
                         'batches: %s' % sorted(changed_set ^ covered))

    profile = _pinned_json(os.path.join(A7, PROFILE_REL), PROFILE_SHA256,
                           'approved input profile')
    return collections.OrderedDict([
        ('report', report),
        ('current_candidate', current),
        ('original_candidate', original),
        ('carry_batches', carry),
        ('changed_batches', sorted(changed_set)),
        ('eligible_lanes', eligible),
        ('gold_moved_batches', sorted(gold_moved)),
        ('candidate_dir', current_dir),
        ('expected_input', profile['expected_input_for_served_lanes'])])
