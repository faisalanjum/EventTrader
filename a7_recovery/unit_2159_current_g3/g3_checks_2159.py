# -*- coding: utf-8 -*-
"""What the corrected G3 package must satisfy, as checkable functions.

These are the caller's OWN checks and nothing else: the renderer, the batcher,
the comparator-pool owner and the source reader are unchanged and are not
re-implemented here. Every function takes already-read bytes or already-parsed
structures, so the same code runs in a focused test and in the native job.

A rendered question is placed by the EXISTING question-identity owner, and the
canonical comparison is the EXISTING owner's own `_plain` rather than a second
serializer of mine: a rendered record has been through JSON and an expected one
has not, so a Decimal that JSON writes as text must not read as a difference,
and an unsupported object must REFUSE rather than be quietly stringified.

Context and reference cards are compared against the values their own owners
return for that event, because presence is not identity.
"""
import collections
import json

import a7_g1_build as G

MARK = '\n{\n'
#: the existing canonical-text owner, aliased - never re-implemented.
canon = G._plain


def body_of(prompt_text):
    """The rendered JSON body of one batch prompt."""
    at = prompt_text.index(MARK)
    return json.loads(prompt_text[at + 1:])


def plain_report(obj):
    """A report JSON can hold: tuple KEYS become explicit rows, and anything
    it cannot represent refuses rather than being stringified."""
    if isinstance(obj, dict):
        if any(isinstance(k, tuple) for k in obj):
            return [[list(k), plain_report(v)]
                    for k, v in sorted(obj.items(), key=lambda kv: repr(kv[0]))]
        return collections.OrderedDict(
            (k, plain_report(v)) for k, v in sorted(obj.items(),
                                                    key=lambda kv: repr(kv[0])))
    if isinstance(obj, (list, tuple)):
        return [plain_report(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    raise TypeError('a report may not carry %s' % type(obj).__name__)


def expected_pool(matched_rows, asked_idx):
    """The comparator indices one question may show, in the owner's order."""
    return [i for i in sorted({row[1] for row in (matched_rows or [])})
            if i != asked_idx]


def placements(g3_population, identify):
    """{question_id: (group, produced_idx)} through the EXISTING id owner."""
    out = {}
    for group in sorted(g3_population):
        leg, source_id = group.split('|', 1)
        for idx in g3_population[group]:
            out[identify(leg, source_id, idx)] = (group, idx)
    return out


def audit(candidate, prompt_texts, g3_population, g2_population, display,
          identify, context_of, cards_of):
    """-> (rows, problems, empty_groups).

    Nothing is asserted here; the caller decides what a problem means. Every
    rendered block is visited, every question in the population must be asked
    exactly once, and each block's record, context, cards and comparison pool
    are compared with what their own owners produce for that event.
    """
    index = placements(g3_population, identify)
    seen = collections.Counter()
    rows, problems, empty = [], [], []
    for batch in candidate['batch_rows']:
        for block in body_of(prompt_texts[batch['batch_id']])['events']:
            ids = [q.get('question_id') for q in (block.get('questions') or [])]
            unknown = [q for q in ids if q not in index]
            if unknown:
                problems.append('a rendered block asks unknown questions: %r'
                                % (unknown[:2],))
                continue
            if len(ids) != 1:
                problems.append('a rendered block carries %d questions; the '
                                'preparer builds one per question' % len(ids))
                continue
            group, asked = index[ids[0]]
            leg, source_id = group.split('|', 1)
            name = '%s question %s' % (group, ids[0])

            # THE ASKED RECORD IS THIS EVENT'S OWN PRODUCED ROW
            if canon(block['questions'][0].get('produced_record')) != canon(
                    display(leg, source_id, asked)):
                problems.append('%s: the asked record is not produced row %d of '
                                'this event' % (name, asked))

            # THE COMPARISON POOL IS EXACTLY THIS EVENT'S MATCHED ROWS
            want = expected_pool(g2_population.get(group), asked)
            if not want:
                empty.append(group)
            shown = [row.get('produced_record')
                     for row in (block.get('other_records') or [])]
            expect = [display(leg, source_id, i) for i in want]
            if [canon(r) for r in shown] != [canon(r) for r in expect]:
                problems.append('%s: %s' % (name, _difference(shown, expect, want)))

            # THE CONTEXT AND CARDS ARE THE SOURCE'S OWN, not merely present
            if canon(block.get('event_context')) != canon(context_of(leg, source_id)):
                problems.append('%s: the event context is not the verified '
                                'context this source returns' % name)
            if canon(block.get('reference_cards')) != canon(cards_of(leg, source_id)):
                problems.append('%s: the reference cards are not this event\'s '
                                'own accepted source rows' % name)

            seen[ids[0]] += 1
            rows.append(collections.OrderedDict([
                ('question_id', ids[0]), ('group', group),
                ('batch_id', batch['batch_id']), ('asked_produced_idx', asked),
                ('comparator_idxs', want), ('comparators_shown', len(shown)),
                ('reference_cards', len(block.get('reference_cards') or [])),
                ('context_sha256', G._sha(canon(block.get('event_context')))),
                ('cards_sha256', G._sha(canon(block.get('reference_cards')))),
                ('record_sha256', G._sha(canon(
                    block['questions'][0].get('produced_record')))),
            ]))
    missing = sorted(q for q in index if q not in seen)
    twice = sorted(q for q, n in seen.items() if n != 1)
    if missing:
        problems.append('%d questions are never asked, first %r'
                        % (len(missing), missing[:2]))
    if twice:
        problems.append('%d questions are asked more than once, first %r'
                        % (len(twice), twice[:2]))
    return rows, problems, sorted(set(empty))


def _difference(shown, expect, want):
    """Say WHAT differs. A message that only counts argues against itself when
    the counts agree, which is exactly how the first real mismatch read."""
    if len(shown) != len(expect):
        return ('shows %d comparison records, its matched pool minus the asked '
                'row is %d %r' % (len(shown), len(expect), want))
    for n, (got, wanted) in enumerate(zip(shown, expect)):
        if canon(got) == canon(wanted):
            continue
        if not isinstance(got, dict) or not isinstance(wanted, dict):
            return 'comparison record %d is %s, expected %s' % (
                n, type(got).__name__, type(wanted).__name__)
        only_shown = sorted(set(got) - set(wanted))
        only_expect = sorted(set(wanted) - set(got))
        if only_shown or only_expect:
            return ('comparison record %d (produced row %s) carries %r and is '
                    'missing %r' % (n, want[n], only_shown, only_expect))
        keys = sorted(k for k in wanted if canon(got.get(k)) != canon(wanted.get(k)))
        return ('comparison record %d (produced row %s) differs in %r: shown %s '
                'vs expected %s' % (n, want[n], keys, canon(got.get(keys[0]))[:120],
                                    canon(wanted.get(keys[0]))[:120]))
    return 'the comparison records differ in order only: %r' % (want,)
