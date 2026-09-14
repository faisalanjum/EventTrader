# -*- coding: utf-8 -*-
"""The ONE current-round binding, shared by preparation and collection.

Codex SEQ 2128 allows a small shared binding exactly where preparation and its
later collection/resume caller would otherwise duplicate it. That is all this
is: the pointers the new round is bound to, every one of them DERIVED - the
completed predecessor and its own findings, the prior chain, the signature at
its own round boundary, the affected population, and the served findings.

It owns no lifecycle. `F.prepare_v6`, `record_state`, `finalize`, the native
proof, the budget and the retry law stay exactly where they are; nothing here
copies or re-states any of them. It calls no model and decides no meaning.
"""
import collections
import contextlib
import os

#: the completed post-signature round this one follows
PREDECESSOR = ('unit_2123_post_signature_key/core_recheck2123_h/'
               'recheck_packet')
#: the frozen original bindings the predecessor's own findings come from
BINDINGS = 'unit_2020_codex_check/SOURCE_KEY_RECHECK_BINDINGS_2120.json'
BINDINGS_SHA256 = ('a97d16ba0895f6170e3f4ac5358152d7e4c987057b9c2bdf09c153513'
                   'b964bb0')
#: the two measured review files the affected population is READ from. The
#: population is a review conclusion and it selects which events are asked
#: again; it never reaches a worker's input.
DISPOSITIONS = ('unit_2123_post_signature_key/core_full2126_c/'
                'SOURCE_STATE_DISPOSITIONS_2126.json')
DISPOSITIONS_SHA256 = ('b0f1c6ad0e1133f5cecb201a56c7fc23ec9ade73debda211817e5'
                       '7c9a7d98a91')
ADDENDUM = 'unit_2127_source_context/SOURCE_DISPOSITION_ADDENDUM_2127.json'
ADDENDUM_SHA256 = ('85d65d653045c6dd4e73c3b62fa9ac970b286a1eea595961b4e4ed830'
                   '2e0be62')

Binding = collections.namedtuple(
    'Binding',
    'bound predecessor predecessor_findings prior signatures affected order')


def _pinned(E, rel, want):
    path = str(E.A7 / rel)
    got = E.G._sha_file(path)
    if got != want:
        raise ValueError('%s is %s, not the pinned %s' % (rel, got, want))
    return E.G._read(path)


def affected_sources(E, order):
    """The seven events, READ from the two measured review files.

    Derived, never typed: the union of the rows both files rule a correction,
    returned in the frozen event order.
    """
    dis = _pinned(E, DISPOSITIONS, DISPOSITIONS_SHA256)
    add = _pinned(E, ADDENDUM, ADDENDUM_SHA256)
    rows = {r['row'] for r in dis['rows']
            if r['disposition'] == 'needs_independent_source_correction'}
    rows.add(add['row'])
    if add['disposition_after'] != 'needs_independent_source_correction':
        raise ValueError('the addendum does not rule a correction')
    sources = {r.split('#')[0] for r in rows}
    return [s for s in order if s in sources]


def binding(E, X):
    """Every pointer the new round is bound to. Nothing here is typed."""
    F = E.F
    bound = E.G._approved_bound()
    order = [t['source_id'] for t in F.event_tasks(bound.evidence)]
    request = _pinned(E, BINDINGS, BINDINGS_SHA256)
    predecessor_findings = collections.OrderedDict()
    for event in sorted(request['source_events'],
                        key=lambda e: order.index(e['source_id'])):
        sid = event['source_id']
        predecessor_findings[sid] = [collections.OrderedDict([
            ('source_id', sid),
            ('raw_sha256', event['prior_source_raw_sha256']), ('row', row)])
            for row in event['original_task_ids']]
    run = str(E.A7 / PREDECESSOR)
    return Binding(
        bound=bound, predecessor=run,
        predecessor_findings=predecessor_findings,
        prior=tuple(E.chain) + ((E.saved['third_round'],
                                 E.saved['third_by_event']),),
        #: the signature sits at the boundary of the round it preceded, not
        #: immediately before the next one.
        signatures={run: E.result['notes']['candidate']},
        affected=affected_sources(E, order), order=order)


def round_findings(E, b, raws):
    """The served findings: EVERY original task row of each affected event.

    source_id, raw_sha256 and row, and nothing else - no verdict, no grade and
    no review note can reach the served body through this.
    """
    F, K = E.F, E.K
    out = collections.OrderedDict()
    for sid in b.affected:
        out[sid] = [collections.OrderedDict([
            ('source_id', sid), ('raw_sha256', K._sha(raws[sid])),
            ('row', row)])
            for row in F._task_by_label(b.bound.evidence, sid)['rows']]
    return out


@contextlib.contextmanager
def scope(E, X, b, next_bound, findings, V2, V3):
    """The scope this round runs in - preparation and collection ALIKE.

    The served wording is part of the binding, not of the preparation step.
    MEASURED (Core SEQ 2128): the published receipt records the prompt hashes
    of the prefix actually served, so a collection or resume caller that
    entered only the successor scope would recompute prompts WITHOUT the
    clarification and `F.receipt_problems` would refuse its own packet. Both
    callers therefore take the scope from here and cannot drift apart.
    """
    with X.successor_scope(next_bound, findings, b.predecessor,
                           b.predecessor_findings, E.source_inputs, b.prior,
                           signatures=b.signatures):
        with install_prefix(E, V2, V3, E.F):
            yield


def current_key(E, X, b):
    """The 33-source key the new round starts from, through the existing owner."""
    return X.first_round_key(b.bound, b.predecessor, b.predecessor_findings,
                             E.source_inputs, b.prior, signatures=b.signatures)


def install_prefix(E, V2, V3, F):
    """The approved wording, around the CURRENT `F.v6_prefix` call only.

    The already-installed seam is captured BEFORE the swap; reading the live
    attribute inside the replacement calls it again and recurses forever
    (measured, Core SEQ 2128). Holding the swap for one call is what keeps
    every historical round rendering its own recorded prompt.
    """
    installed = F.v6_prefix

    def context_prefix(package, keys):
        with E.R._using(V2, served_prefix=V3.served_prefix):
            return installed(package, keys)

    return E.R._using(F, v6_prefix=context_prefix)


def pointers(E, b):
    """What this binding actually resolved, for the record."""
    return collections.OrderedDict([
        ('predecessor_run', b.predecessor),
        ('predecessor_receipt_sha256',
         E.G._sha_file(os.path.join(b.predecessor, E.K.RECEIPT_NAME))),
        ('predecessor_finalization_sha256',
         E.G._sha_file(os.path.join(b.predecessor, E.K.FINALIZATION_NAME))),
        ('predecessor_events', list(b.predecessor_findings)),
        ('prior_rounds', [r for r, _f in b.prior]),
        ('signatures', collections.OrderedDict(sorted(b.signatures.items()))),
        ('affected_sources', list(b.affected)),
        ('frozen_event_order_positions',
         [b.order.index(s) for s in b.affected])])
