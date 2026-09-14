"""Versioned grading-input correction; no calls, scores or evidence rewrites.

The frozen packet owner still supplies question identities, source cards and
verified inputs. This explicit successor changes only the model-facing view.
Historical packets keep their original renderer. A caller must freeze this
version and its affected population before using it for new grading evidence.
"""
import collections
import copy

import a1_reader as A
import a7_g1_build as G
import a7_g23_build as OLD
from driver.core.driver_ids import IdLawError


def _replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('the frozen grading instruction changed')
    return text.replace(old, new, 1)


def record_view(fact):
    """Decode valid menu tokens with their existing owner; preserve all else."""
    shown = copy.deepcopy(G._display(fact))
    parts = shown['item'].get('slice_parts', [])
    for i, token in enumerate(parts):
        try:
            display, _back = A.readable_menu([token])
        except IdLawError:
            # Off-menu source spans are allowed. Do not normalize, infer a
            # population, or turn malformed evidence into a valid menu pick.
            continue
        parts[i] = display[0]
    return shown


def _output(rules, text):
    before, tail = rules.split('[OUTPUT]\n', 1)
    _old, boundary = tail.split(G.BOUNDARY, 1)
    return before + '[OUTPUT]\n' + text + '\n\n' + G.BOUNDARY + boundary


def meaning_contract():
    rules = _replace_once(
        OLD.meaning_contract(),
        'bare reported level. Guidance: movement only where the source states it; a\n'
        '   bare guide is unknown.',
        'bare reported level. Direction follows the signed numerical axis, not\n'
        '   whether the outcome improves. Guidance: source-stated introduction, revision, reaffirmation or withdrawal\n'
        '   describes the guide itself. Compare revisions\n'
        "   against the company's own prior guide, not projected business growth\n"
        '   against an actual. Store movement only when the source states it; a\n'
        '   bare guide is unknown.')
    rules = _replace_once(
        rules, '   derivable. A point, an interval, a lower bound and an upper bound each mean',
        '   derivable. Leave change_value null when it could merely be derived\n'
        '   from a closed shape; derive at read time. A point, an interval, a lower bound and an upper bound each mean')
    return _replace_once(
        rules, '   accompanies a change value. Several stated bases are not one assertion.',
        '   accompanies a change value. Percent-only guidance stores its growth\n'
        "   basis in level_unit; only the guide's own revision size belongs in\n"
        '   change_value. Several stated bases are not one assertion.')


def meaning_rules():
    rules = _replace_once(OLD.meaning_rules(), OLD.meaning_contract(),
                          meaning_contract())
    return _output(rules,
        'Return ONLY a JSON array with one object per supplied question id.\n'
        'Each object has exactly question_id (the supplied string) and verdicts\n'
        '(an object containing every named aspect exactly once). Each aspect\n'
        'value is an unquoted JSON true, false, or null, never a string.\n'
        'No prose, extra fields or missing fields. Plain JSON or one fenced JSON block.')


def extras_rules():
    rules = _replace_once(
        OLD.extras_rules(),
        'different source claims and never applies. Within the block, source support\n'
        '   is established by the `reference_cards` AND by the quote each produced\n'
        '   record carries, which is the original bound source text.',
        'different source claims and never applies. Read the full verified source\n'
        '   in `event_context`, including relevant surrounding text and footnotes.\n'
        '   The `reference_cards` identify reviewed claims; produced records are\n'
        '   assertions to check against that source, not independent truth.')
    rules = _replace_once(
        rules,
        '4. `other_records` are the OTHER produced records of the SAME event. They are\n'
        '   candidate assertions, not established truth, and they are there so you can\n'
        '   judge whether the asked record repeats one of them. The asked record is\n'
        '   never its own repeat. The produced records of the OTHER questions in this\n'
        '   event are comparison records in exactly the same way: compare the asked\n'
        '   record with those as well, never with its own occurrence. A claim that is',
        '4. `other_records` are the produced records of the SAME event that this run\n'
        '   paired with a reviewed claim, and an empty list means this event has\n'
        '   none. They are candidate assertions, not established truth, and they are\n'
        '   the only records the asked record can be a duplicate OF. The asked record\n'
        '   is never its own repeat, and the produced records of the OTHER questions\n'
        '   in this event are NOT comparison records. Establish first that the asked\n'
        '   record states what the source states, field by field; only then can it be\n'
        '   a duplicate of one of these records, or a claim the reviewed set omits. A\n'
        '   repeated unsupported assertion is still unsupported. A claim that is')
    rules = _replace_once(
        rules,
        '   - duplicate: the produced record states a claim the run already states '
        'elsewhere, so it is the same claim emitted twice',
        '   - duplicate: the produced record states the same claim as one of this '
        'event\'s comparison records, so it is that claim emitted twice')
    rules = _replace_once(rules, '[OUTPUT]\n', meaning_contract() + '\n[OUTPUT]\n')
    return _output(rules,
        'Return ONLY a JSON array with one object per supplied question id.\n'
        'Each object has exactly question_id (the supplied string) and bucket\n'
        '(one of the named bucket strings, or the unquoted JSON null).\n'
        'No prose, extra fields or missing fields. Plain JSON or one fenced JSON block.')


def matched_inventory(matched_pairs, asked_population):
    """The canonical G2 population, made EXPLICIT for every asked group.

    `a7_g23_run.populations` writes g2[group] only `if rows`, so the frozen
    full inventory is sparse: a leg/source that matched nothing is simply
    absent. The G3 population names exactly which groups are legitimately
    asked about, so the two together say - mechanically, per group and with no
    per-event branch - which absences are lawful. Every asked group appears
    here, with its matched pairs or with an explicit empty list; a group that
    is NOT asked about stays absent, so a wrong, truncated or tampered
    inventory still refuses downstream instead of turning into an empty pool.
    """
    if not isinstance(matched_pairs, dict):
        raise ValueError('the matched-pair inventory is required')
    if not isinstance(asked_population, dict) or not asked_population:
        raise ValueError('the asked population is required to make the '
                         'matched-pair inventory explicit')
    view = collections.OrderedDict()
    for group in sorted(asked_population):
        rows = matched_pairs.get(group, [])
        if not isinstance(rows, list):
            raise ValueError('the matched-pair inventory for %r is not a list'
                             % (group,))
        view[group] = [list(row) for row in rows]
    return view


def eligible_comparators(matched_pairs, leg, source_id, produced_facts):
    """The event's MATCHED produced rows - the only lawful comparison records.

    exp5_scoring_spec_v3.md section 5 defines an extra `duplicate` as a
    duplicate OF A MATCHED FACT, so the pool is the produced side of this
    leg/source's matched pairs. Excluding the asked rows is NOT done here: the
    packet owner already builds `other_records` without them, and two owners
    for one rule are two rules waiting to disagree. Membership is mechanical
    and comes from the same G2 inventory the consumer already requires; it is
    never a caller's claim. An EMPTY pool is an explicit answer. An absent
    inventory, a wrong event, an index this event does not have, or a repeated
    index refuses instead of quietly becoming the whole event.
    """
    if not isinstance(matched_pairs, dict):
        raise ValueError('the matched-pair inventory is required for G3')
    key = '%s|%s' % (leg, source_id)
    rows = matched_pairs.get(key)
    if rows is None:
        raise ValueError('the matched-pair inventory names no %r' % (key,))
    if not isinstance(rows, list):
        raise ValueError('the matched-pair inventory for %r is not a list' % (key,))
    seen, pool = set(), []
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) != 2:
            raise ValueError('a matched pair is one gold and one produced index')
        produced = row[1]
        if (not isinstance(produced, int) or isinstance(produced, bool)
                or not 0 <= produced < len(produced_facts)):
            raise ValueError('a matched pair names produced row %r, which this '
                             'event does not have' % (produced,))
        if produced in seen:
            raise ValueError('the matched-pair inventory repeats produced row %d'
                             % produced)
        seen.add(produced)
        pool.append(produced)
    return sorted(pool)


def _render(packet, kind, body):
    result = dict(packet)
    result['prompt'] = (meaning_rules() if kind == 'G2' else extras_rules()) + G._pretty(body) + '\n'
    result['prompt_sha256'] = G._sha(result['prompt'])
    result['input_correction_sha256'] = G._sha_file(__file__)
    return result


def meaning_packet(leg, source_id, pairs, gold_facts, produced_facts,
                   run=None, inputs=None):
    if not inputs:
        raise ValueError('verified source inputs are required for grading')
    packet = OLD.meaning_packet(leg, source_id, pairs, gold_facts,
                                produced_facts, run, inputs=inputs)
    for row in packet['questions']:
        row['produced_record'] = record_view(row['produced_record'])
    return _render(packet, 'G2', {
        'event_context': OLD._required_context(packet, 0),
        'questions': packet['questions']})


def extras_packet(leg, source_id, produced_idxs, produced_facts,
                  source_facts, run=None, inputs=None, matched_pairs=None):
    if not inputs:
        raise ValueError('verified source inputs are required for grading')
    context = dict(OLD.verified_event_context(inputs, source_id, run))
    if context.pop('_source_id', None) != source_id:
        raise ValueError('the verified context names a different source')
    packet = OLD.extras_packet(leg, source_id, produced_idxs, produced_facts,
                               source_facts, run)
    # ONLY THE MATCHED COMPARISON RECORDS. The owner's own rows and displays
    # are kept; this drops the ones a duplicate cannot lawfully be OF, and
    # relabels what remains with the owner's own positional pattern so no
    # index identity reaches the prompt.
    pool = set(eligible_comparators(matched_pairs, leg, source_id,
                                    produced_facts))
    keep = [(row, idx) for row, idx in zip(packet['other_records'],
                                           packet['other_produced_idxs'])
            if idx in pool]
    packet['other_records'] = [collections.OrderedDict([
        ('other', 'O%d' % (n + 1)),
        ('produced_record', row['produced_record'])])
        for n, (row, _idx) in enumerate(keep)]
    packet['other_produced_idxs'] = [idx for _row, idx in keep]
    packet['matched_comparators'] = list(packet['other_produced_idxs'])
    packet['event_context'] = context
    for row in packet['questions'] + packet['other_records']:
        row['produced_record'] = record_view(row['produced_record'])
    return _render(packet, 'G3', {k: packet[k] for k in (
        'event_context', 'questions', 'other_records', 'reference_cards')})


def batch_packet(kind, packets):
    # Keep the original kind/id validation. Source context is required for
    # both kinds; every event retains its own context, never another event's.
    expected = G._sha_file(__file__)
    if any(packet.get('input_correction_sha256') != expected for packet in packets):
        raise ValueError('a packet uses a different or missing correction version')
    result = OLD.batch_packet(kind, packets)
    events = []
    for n, packet in enumerate(packets):
        event = {'event': 'E%d' % (n + 1),
                 'event_context': OLD._required_context(packet, n),
                 'questions': packet['questions']}
        if kind == 'G3':
            event.update({k: packet[k] for k in ('other_records', 'reference_cards')})
        events.append(event)
    return _render(result, kind, {'events': events})
