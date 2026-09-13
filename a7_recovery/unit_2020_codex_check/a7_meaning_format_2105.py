"""Owner-approved G2 format recovery; not yet enabled in collection/scoring.

Original raw replies and original validity remain authoritative history.
The original parser is the sole schema/identity validator.
"""
import json
import copy
from contextlib import contextmanager
from pathlib import Path

import a4_review_composite as R
import a7_g1_build as G
import a7_g23_build as B
import a7_g1_complete_v2 as C
import raw_transport as RT

RULE_FILE = Path(__file__).with_name('A7_MEANING_FORMAT_RULE_2105.md')


@contextmanager
def scope(expected_code_sha256, expected_rule_sha256):
    """An explicitly pinned reporting view AFTER original collection checks.

    Original owner files/functions are restored on exit. Original attempt
    validity is retained; only the selected usable relation changes. The
    existing completion carries the complete recovery audit in its identity,
    so the unchanged consumer must reproduce it byte-for-byte before scoring.
    """
    def verify():
        if G._sha_file(__file__) != expected_code_sha256:
            raise ValueError('unapproved meaning-format code')
        if G._sha_file(str(RULE_FILE)) != expected_rule_sha256:
            raise ValueError('unapproved meaning-format rule')
    verify()
    original_evidence, original_identity = C.evidence, C.g23_identity

    def evidence(out_dir, run_dir, *pins):
        state = original_evidence(out_dir, run_dir, *pins)
        root, doc, lanes, problems = state
        if problems or root is None or G.task_kind(doc) != 'G2':
            return state
        attempts, _audit = _read_run(root, doc, run_dir)
        recovered = copy.deepcopy(lanes)
        for lane, readings in attempts.items():
            chosen = C.select_attempt(readings)
            recovered[lane]['selected'] = None if chosen is None else chosen[0]
            recovered[lane]['relation'] = None if chosen is None else chosen[1]
        return root, doc, recovered, problems

    def identity(root_sha, run_dir):
        value = original_identity(root_sha, run_dir)
        root = G.load_root(run_dir, root_sha)
        doc, _ = G.load_frozen(root['candidate_dir'], root['candidate_sha256'])
        if G.task_kind(doc) == 'G2':
            _attempts, audit = _read_run(root, doc, run_dir)
            value['meaning_format_recovery'] = {
                'code_sha256': expected_code_sha256,
                'rule_sha256': expected_rule_sha256, 'attempts': audit}
        return value

    try:
        with R._using(C, evidence=evidence, g23_identity=identity):
            yield
    finally:
        verify()


def _read_run(root, doc, run_dir):
    """Interpret saved whole replies only; native admission is never replaced."""
    rows = {row['lane_id']: row for row in root['rows']}
    binding, _parser = G.binding_and_parser('G2')
    attempts, audit = {}, []
    for segment in G.segments(run_dir):
        if G.segment_state(run_dir, segment) != 'finalized':
            raise ValueError('meaning-format recovery requires finalized segments')
        final = G._read(G.finalization_path(run_dir, segment))
        called = [(lane, valid) for lane, valid in final['validity']
                  if lane not in final['uncalled']]
        if not called:
            continue  # A named zero-call closure has no answer to recover.
        whole, problems = G.whole_answers(run_dir, segment)
        if problems:
            raise ValueError('meaning-format whole reply refused: %s' % problems)
        validity = dict(final['validity'])
        if set(whole or {}) - set(validity):
            raise ValueError('meaning-format reply was not finalized')
        for lane, original_valid in called:
            if lane not in rows:
                raise ValueError('meaning-format lane is absent from its root')
            attempt = final['attempt']
            seen = attempts.setdefault(lane, {})
            if attempt in seen:
                raise ValueError('meaning-format attempt was finalized twice')
            raw = (whole or {}).get(lane)
            answer, bad, record = read(raw, binding(doc, rows[lane]['batch_id']))
            if record['original_valid'] != original_valid:
                raise ValueError('meaning-format original validity drifted')
            seen[attempt] = answer, bad
            audit.append(dict(record, lane_id=lane, attempt=attempt, segment=segment))
    return attempts, audit


def read(text, packet):
    """Recover only exact JSON-literal strings; re-use the entire strict door.

    Return the original failure with an explicit recovery audit. No native
    file is written, no identity/field is filled, and no meaning is inferred.
    """
    answer, problems = B.read_meaning_reply(text, packet)
    audit = {'raw_sha256': G._sha(text) if isinstance(text, str) else None,
             'original_valid': not problems, 'original_problems': list(problems),
             'recovered': False, 'conversions': []}
    if not problems:
        return answer, problems, audit
    try:
        rows = RT.parse_reply(text)
    except Exception:
        return None, problems, audit
    if not isinstance(rows, list):
        return None, problems, audit
    literals = {json.dumps(value): value for value in (True, False, None)}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('verdicts'), dict):
            continue
        for field in B.meaning_fields():
            value = row['verdicts'].get(field)
            if type(value) is str and value in literals:
                decoded = literals[value]
                row['verdicts'][field] = decoded
                audit['conversions'].append({'question_id': row.get('question_id'),
                                             'field': field, 'from': value, 'to': decoded})
    if not audit['conversions']:
        return None, problems, audit
    answer, remaining = B.read_meaning_reply(G._plain(rows), packet)
    if remaining:
        audit['remaining_problems'] = remaining
        return None, problems, audit
    audit['recovered'] = True
    return answer, [], audit
