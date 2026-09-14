# -*- coding: utf-8 -*-
"""The ONE shared binding for the source-rule closeout round. Codex SEQ 2143.

Preparation and collection take their scope from HERE, so the served wording
and every pointer come from one place and the two callers cannot drift. It is
deliberately thin: the 2136 binding owns the key, the findings seam, the round
scope and the pointer record, and every one of those is CALLED here, not
copied. This file owns exactly two things - which round is the predecessor, and
which one question this round serves.

WHAT IS NEW, and it is only data:

  * the predecessor is the COMPLETED eight-question round, declaring the
    wording it was actually served under, so the current key is derived from
    the real eight and never from pre-eight history; and
  * one question, for the one source that root's pinned review still records
    as carrying an open issue.

THE QUESTION IS READ, NEVER TYPED. Its text is the reader's own recorded open
issue, taken verbatim from root's pinned review; its fields are the frozen
finding's own fields, unchanged; its raw binding is root's recorded current raw
for that source, which is an INDEPENDENT value - the existing seam then refuses
unless the live key agrees with it. Nothing here adds an expected count, value,
state, answer or grade, because none exists in this file to add.

THE ONE THING THIS FILE DECLARES RATHER THAN DERIVES is the question ROW. The
open issue is recorded at EVENT level with no row pointer, so no derivation
from the evidence exists; the work order names it. It is therefore declared
with its provenance and then CHECKED two ways - it must be one of that source's
frozen question rows, and one of its live located rows - and the source it
belongs to is derived independently and must agree with the declaration.
"""
import collections
import os
import sys
from pathlib import Path

A7 = Path(__file__).resolve().parents[1]
for _rel in ("unit_2127_source_context", "unit_2128_source_corrections",
             "unit_2136_source_questions"):
    sys.path.insert(0, str(A7 / _rel))
import a7_source_context_2127 as V3                                # noqa: E402
import a7_round_binding_2128 as B2128                              # noqa: E402
import a7_round_binding_2136 as _B2136                             # noqa: E402

#: the completed round this one follows, and the wording it was SERVED under
PREDECESSOR = 'unit_2136_source_questions/packet_2136'
RENDERER = 'unit_2143_source_authority/a7_source_authority_2143.py'
RENDERER_SHA256 = ('ff48b6e5d44304bb8246365ee49207e379fda22e86ecb32fb6bb25c26'
                   'b4c5a0f')
#: root's independent review of the completed eight. It is the round's evidence
#: for WHICH source is still open, for that source's recorded open issue, and
#: for the current raw every question must bind.
REVIEW = 'unit_2020_codex_check/codex_eight2141_b/EIGHT_SOURCE_REVIEW_2141.json'
REVIEW_SHA256 = ('91f0f1b3454a938834242b05a4f23c9d9addf90491598e21269651fd7a1'
                 'd4bf1')

#: the work order's own scope. Declared, never derived - see the module note.
DECLARED = collections.OrderedDict([
    ('work_order', 'Codex SEQ 2143'),
    ('source_id', '0001104659-26-017090'),
    ('question_row', '0001104659-26-017090#115')])


def binding(E, X, B2136, V):
    """Every pointer this round is bound to. Nothing semantic is typed.

    `V` is the version this round SERVES; the predecessor keeps the version it
    was served under, and every older round keeps its own historical wording.
    """
    served = os.path.abspath(V.__file__)
    if served != str(E.A7 / RENDERER):
        raise ValueError('the served version is %s, not the pinned renderer %s'
                         % (served, RENDERER))
    if E.G._sha_file(served) != RENDERER_SHA256:
        raise ValueError('the served renderer is not the pinned one')
    b = B2136.binding(E, X, B2128, V3)
    # B2136's OWN key is the one BEFORE the eight; it is exactly what the
    # completed round was served, which is what its findings must bind.
    _shards, pre_raws, _origins, bad = B2136.current_key(E, X, b)
    if bad:
        raise ValueError('the pre-eight key does not read cleanly: %s' % bad[:2])
    done = str(E.A7 / PREDECESSOR)
    review = B2136.pinned(E, REVIEW, REVIEW_SHA256)
    sid = DECLARED['source_id']
    row = DECLARED['question_row']

    issues = review['open_issues_by_source']
    derived = [s for s, v in issues.items() if v]
    if derived != [sid]:
        raise ValueError('the sources still carrying an open issue are %s, '
                         'not the declared %s' % (derived, [sid]))
    if len(issues[sid]) != 1:
        raise ValueError('the affected source records %d open issues, not one'
                         % len(issues[sid]))
    frozen = collections.OrderedDict((q['row'], q) for q in b.questions[sid])
    if row not in frozen:
        raise ValueError('the declared question row is not one of that '
                         "source's frozen question rows: %s" % list(frozen))
    located = E.F._task_by_label(b.bound.evidence, sid)['rows']
    if row not in located:
        raise ValueError('the declared question row is not a located row of '
                         'its event: %s' % row)

    prefixes = dict(b.prefixes)
    prefixes[done] = V3.served_prefix
    return b._replace(
        predecessor=done,
        predecessor_findings=B2136.round_findings(E, b, pre_raws),
        prior=tuple(b.prior) + ((b.predecessor, b.predecessor_findings),),
        prefixes=prefixes,
        affected=[sid],
        questions={sid: [collections.OrderedDict([
            ('source_id', sid),
            ('raw_sha256', review['all_current_raw_sha256'][sid]),
            ('row', row),
            ('fields', list(frozen[row]['fields'])),
            ('review_question', issues[sid][0]['what'])])]})


def pointers(E, bb):
    """What this binding resolved, plus THIS round's own declared scope.

    The shared pointer owner reports the FROZEN evidence file's own totals for
    the eight-event round; they are that file's declarations, not this round's,
    so this round's counts are recorded separately and measured.
    """
    out = _B2136.pointers(E, bb)
    out['round_declared_scope'] = collections.OrderedDict(DECLARED)
    out['round_question_rows'] = sum(len(v) for v in bb.questions.values())
    out['round_event_rows'] = collections.OrderedDict(
        (sid, len(E.F._task_by_label(bb.bound.evidence, sid)['rows']))
        for sid in bb.affected)
    return out


#: the key, the findings seam and the round scope are the 2136 owner's, used
#: unchanged. They are named here only so the existing preparation and
#: collection callers can bind THIS round without knowing which file owns what.
current_key = _B2136.current_key
round_findings = _B2136.round_findings
scope = _B2136.scope
pinned = _B2136.pinned
