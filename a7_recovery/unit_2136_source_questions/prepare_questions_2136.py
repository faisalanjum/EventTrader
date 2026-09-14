# -*- coding: utf-8 -*-
"""Assemble the source-question packet. Codex SEQ 2136. NO CALL IS MADE.

`F.prepare_v6` is the unchanged owner; this only supplies the shared binding's
scope and records what it produced. Nothing here launches, schedules or
authorizes an invocation.
"""
import collections
import os


def prepare(E, X, B, B2128, V3, out_dir):
    """Render and publish the packet. -> the report. Zero calls."""
    F, K, G = E.F, E.K, E.G
    bb = B.binding(E, X, B2128, V3)
    _shards, raws, origins, bad = B.current_key(E, X, bb)
    if bad:
        raise ValueError('the current key does not read cleanly: %s' % bad[:2])
    findings = B.round_findings(E, bb, raws)
    bound = X.bind(bb.bound, out_dir)
    with B.scope(E, X, bb, bound, findings, V3):
        prepared = F.prepare_v6(out_dir, bound)
        if not prepared['ok']:
            raise ValueError('preparation refused: %s' % prepared['problems'][:2])
        receipt = K._load(os.path.join(out_dir, K.RECEIPT_NAME))
        budget = F.v6_budget(bound)
        scripts = F.v6_scripts(bound)
        capacity = F.capacity_problems(scripts)
    return collections.OrderedDict([
        ('scope', 'source-question packet, prepared and UNRUN; no call, no '
                  'key edit, no signer, no grading'),
        ('run_dir', out_dir),
        ('owner_sha256', G._sha_file(X.__file__)),
        ('binding_sha256', G._sha_file(B.__file__)),
        ('renderer_sha256', G._sha_file(str(E.A7 / B.RENDERER))),
        ('pointers', B.pointers(E, bb)),
        ('input_declarations', [collections.OrderedDict(
            [('source_id', sid), ('prompt_sha256', receipt['prompts'][sid])])
            for sid in receipt['allowed']]),
        ('events', list(receipt['allowed'])),
        ('rows_served', collections.OrderedDict(
            (sid, len(F._task_by_label(bb.bound.evidence, sid)['rows']))
            for sid in receipt['allowed'])),
        ('findings_served', collections.OrderedDict(
            (sid, len(rows)) for sid, rows in findings.items())),
        ('receipt_sha256', G._sha_file(os.path.join(out_dir, K.RECEIPT_NAME))),
        ('receipt_states', list(receipt['states'])),
        ('largest_script_bytes', prepared['largest_script_bytes']),
        ('transport_limit', K.TRANSPORT_LIMIT),
        ('capacity_problems', capacity),
        ('accounting', collections.OrderedDict([
            ('before_this_round', budget['before']),
            ('planned_corrections', budget['planned_corrections']),
            ('planned_signer', budget['planned_signer']),
            ('after_planned', budget['after_planned']),
            ('max_attempts_per_call', budget['max_attempts_per_call']),
            ('worst_case_after', budget['worst_case_after']),
            ('global_ceiling', budget['global_ceiling']),
            ('retryable_outcomes', list(F.RETRYABLE))])),
        ('model_calls_started_here', 0)])
