# -*- coding: utf-8 -*-
"""The ONE shared binding for the source-question round. Codex SEQ 2136.

Preparation and collection take their scope from HERE, so the served wording
and every pointer come from one place and the two callers cannot drift.

WHAT IS NEW, and it is only data: the eight affected events and their thirteen
review questions are READ from the frozen source-only findings, and each
question is passed through the EXISTING finding seam unchanged. A question is
evidence and a question; this file turns none of them into a mandated answer.

WHAT IS REUSED: B2128 supplies its ORIGINAL pointers and the findings the
completed seven-source round was actually served. The current key is NOT
B2128.current_key - that one predates the seven - it is the verified 2134
owner read over the completed round with an explicit prefix map.
"""
import collections
import contextlib
import os

#: the completed round this one follows, and the wording it was SERVED under
PREDECESSOR = ('unit_2128_source_corrections/core_pkt2128_d/'
               'seven_source_packet')
RENDERER = 'unit_2127_source_context/a7_source_context_2127.py'
RENDERER_SHA256 = ('002001473da073b21dfa6e5db7aed620d0da7da96d787a5127b292e70'
                   '14d7c33')
#: the frozen source-only review data; the population is READ, never typed
FINDINGS = 'unit_2020_codex_check/SOURCE_ONLY_FINDINGS_2133.json'
FINDINGS_SHA256 = ('650bb5ae9067e18ae7d2295c3e7cb11792f5f9977c5677d2ab01186c6'
                   'e558bc5')
EVIDENCE = 'unit_2020_codex_check/SOURCE_ONLY_REVIEW_EVIDENCE_2133.json'
EVIDENCE_SHA256 = ('ce49deb956758915e8337a61bc9fd2fe004d3afe60b4b8be1b24e24dd'
                   'b316424')
DISPOSITIONS = 'unit_2020_codex_check/DEFAULT_STATE_DISPOSITIONS_2133.json'
DISPOSITIONS_SHA256 = ('64c9a62065f95b917e1f05e60649fef6fd2e6e73e6a345932fcce'
                       '023f9488da1')

Binding = collections.namedtuple(
    'Binding',
    'bound predecessor predecessor_findings prior signatures prefixes '
    'affected order questions evidence dispositions')


def pinned(E, rel, want):
    """A frozen input, refused unless its bytes are the pinned ones."""
    path = str(E.A7 / rel)
    got = E.G._sha_file(path)
    if got != want:
        raise ValueError('%s is %s, not the pinned %s' % (rel, got, want))
    return E.G._read(path)


def binding(E, X, B2128, V3):
    """Every pointer this round is bound to. Nothing here is typed.

    `X` must be the VERIFIED 2134 round-input owner: the completed round was
    served under the clarified wording, so only an owner that can restore a
    round's own input can read it as history.
    """
    if E.G._sha_file(str(E.A7 / RENDERER)) != RENDERER_SHA256:
        raise ValueError('the served renderer is not the pinned one')
    b = B2128.binding(E, X)
    # B2128's OWN key is the one BEFORE the seven; it is exactly what the
    # completed round was served, which is what its findings must bind.
    _shards, pre_raws, _origins, bad = B2128.current_key(E, X, b)
    if bad:
        raise ValueError('the pre-seven key does not read cleanly: %s' % bad[:2])
    done = str(E.A7 / PREDECESSOR)
    questions = pinned(E, FINDINGS, FINDINGS_SHA256)
    order = list(b.order)
    affected = [s for s in order if s in questions]
    missing = [s for s in questions if s not in order]
    if missing:
        raise ValueError('a question names an event outside the frozen '
                         'order: %s' % missing[:2])
    return Binding(
        bound=b.bound, predecessor=done,
        predecessor_findings=B2128.round_findings(E, b, pre_raws),
        prior=tuple(b.prior) + ((b.predecessor, b.predecessor_findings),),
        signatures=b.signatures,
        #: the completed round carries the clarification it was served under;
        #: every OLDER round is left with its own historical wording
        prefixes={done: V3.served_prefix},
        affected=affected, order=order, questions=questions,
        evidence=pinned(E, EVIDENCE, EVIDENCE_SHA256),
        dispositions=pinned(E, DISPOSITIONS, DISPOSITIONS_SHA256))


def current_key(E, X, bb):
    """The 33-source key INCLUDING the completed seven, through the owner."""
    return X.first_round_key(bb.bound, bb.predecessor, bb.predecessor_findings,
                             E.source_inputs, bb.prior,
                             signatures=bb.signatures, prefixes=bb.prefixes)


def round_findings(E, bb, raws):
    """The served findings: the frozen questions, bound to the CURRENT raw.

    The question objects are passed through UNCHANGED - source_id, raw_sha256,
    row, the fields under review, the question itself and its source evidence.
    Nothing is added, and no expected answer, score or grade exists here to add.
    """
    K, F = E.K, E.F
    out = collections.OrderedDict()
    for sid in bb.affected:
        allowed = F._task_by_label(bb.bound.evidence, sid)['rows']
        rows = []
        for q in bb.questions[sid]:
            if q['row'] not in allowed:
                raise ValueError('a question names a row outside its event: '
                                 '%s' % q['row'])
            if q['raw_sha256'] != K._sha(raws[sid]):
                raise ValueError('a question does not bind the current raw '
                                 'for %s: %s' % (sid, q['raw_sha256']))
            rows.append(collections.OrderedDict(q))
        out[sid] = rows
    return out


@contextlib.contextmanager
def scope(E, X, bb, next_bound, findings, V3):
    """The scope this round runs in - preparation and collection ALIKE.

    The served wording belongs to the binding, not to either caller. The
    completed predecessor keeps the wording it was served under, and THIS
    round serves the same unchanged V3 task; every older round is untouched.
    """
    prefixes = dict(bb.prefixes)
    prefixes[next_bound.decision_correction_v6] = V3.served_prefix
    with X.successor_scope(next_bound, findings, bb.predecessor,
                           bb.predecessor_findings, E.source_inputs, bb.prior,
                           signatures=bb.signatures, prefixes=prefixes):
        yield


def pointers(E, bb):
    """What this binding actually resolved, for the record."""
    K = E.K
    return collections.OrderedDict([
        ('predecessor_run', bb.predecessor),
        ('predecessor_receipt_sha256',
         E.G._sha_file(os.path.join(bb.predecessor, K.RECEIPT_NAME))),
        ('predecessor_finalization_sha256',
         E.G._sha_file(os.path.join(bb.predecessor, K.FINALIZATION_NAME))),
        ('prior_rounds', [r for r, _f in bb.prior]),
        ('signatures', collections.OrderedDict(sorted(bb.signatures.items()))),
        ('prefix_rounds', sorted(bb.prefixes)),
        ('affected_sources', list(bb.affected)),
        ('frozen_event_order_positions',
         [bb.order.index(s) for s in bb.affected]),
        ('question_rows', sum(len(v) for v in bb.questions.values())),
        ('declared_question_count', bb.evidence['question_count']),
        ('declared_full_event_rows', bb.evidence['full_event_row_count'])])
