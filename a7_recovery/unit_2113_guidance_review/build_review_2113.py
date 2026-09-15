"""The per-question guidance review over all 40, plus the repeatability measure.

Method, stated so the reader can weigh every cell:
  agree            - the served contract settles this aspect on the evidence in
                     this event and the existing verdict follows it
  disagree         - the served contract settles it the OTHER way; the ground
                     and the source span are named
  cannot_establish - this event's evidence does not settle it for me; recorded
                     as legitimate uncertainty rather than guessed

Only the mechanical parts are decided here in code (they restate no rule: they
compare the record with the served contract's own explicit requirements). Every
reasoned position is attached by hand, with its ground, in GROUNDS below.

    python3 -B build_review_2113.py <population.json> <out.json>
"""
import collections
import hashlib
import io
import json
import sys

ASPECTS = ('driver_state', 'driver_name_meaning', 'lane_routing', 'favorability',
           'growth_basis', 'record_matches_source', 'slice_vs_menu')

#: reasoned positions, keyed by question id, each naming its ground. Nothing is
#: keyed by company or answer text; these are the questions where I can settle
#: an aspect the mechanical checks cannot.
GROUNDS = {
    # the DRI adjusted-EPS guide claims a RAISE the event does not state
    'Mdeaf9591a2dcc241': {'driver_state': (
        'disagree', "the record states driver_state 'raised'; this event's qa "
        "part states the prior guide as $10.50 to $10.70 against the new $10.57 "
        "to $10.67, which narrows the range and leaves the midpoint unchanged. "
        "CONTRACT 'THE STATE, BY LANE' allows guidance movement ONLY where the "
        "source states it, and the source states an update, not a raise. "
        "Existing verdict credits it true.")},
    'Mff46eed2c64e8d13': {'driver_state': ('disagree', 'same record and event as '
        'Mdeaf9591a2dcc241; same ground.')},
    'Mbcadb2079632a153': {'driver_state': ('disagree', 'same record and event as '
        'Mdeaf9591a2dcc241; same ground.')},
}

#: the aspects the served contract settles mechanically for a guidance record
def mechanical(rec, row):
    item = rec.get('item') or {}
    out = {}
    # LANE: guidance is the company's own forward outlook, and GUIDANCE-ONLY
    # FIELDS requires company confirmation true on this lane
    out['lane_routing'] = ('agree' if item.get('company_confirmed') is True
                           else 'cannot_establish')
    # POPULATION: "leave it empty only for the whole company"
    out['slice_vs_menu'] = ('agree' if item.get('slice_parts') == []
                            else 'cannot_establish')
    # SURPRISE PROOF AND FAVORABILITY: the favorability flag and basis hint
    # belong only on a surprise, so off that lane the defaults are the truth
    out['favorability'] = ('agree'
                           if item.get('has_favorability_wording') is None
                           and item.get('surprise_basis_hint') is None
                           else 'cannot_establish')
    return out


def sha(path):
    with io.open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


pop = json.load(io.open(sys.argv[1], encoding='utf-8'))
rows = pop['rows']

# repeatability over records asked more than once under IDENTICAL evidence
groups = collections.defaultdict(list)
for r in rows:
    groups[json.dumps(r['produced_record'], sort_keys=True)].append(r)
repeated = [rs for rs in groups.values() if len(rs) > 1]
cells = agree_cells = hard = soft = 0
contradictions = []
for rs in repeated:
    assert len({r['event_source_id'] for r in rs}) == 1, 'not one event'
    for a in ASPECTS:
        vals = {}
        for r in rs:
            est = r['established'] or {}
            vals[r['question_id']] = str(est[a]) if a in est else 'UNRESOLVED'
        cells += 1
        distinct = set(vals.values())
        if len(distinct) == 1:
            agree_cells += 1
        elif len(distinct - {'UNRESOLVED'}) > 1:
            hard += 1
            contradictions.append(collections.OrderedDict([
                ('driver_name', (rs[0]['produced_record']['item'] or {}).get('driver_name')),
                ('event_source_id', rs[0]['event_source_id']),
                ('aspect', a), ('verdicts', vals)]))
        else:
            soft += 1

questions = []
tally = collections.Counter()
for r in rows:
    est = r['established'] or {}
    mech = mechanical(r['produced_record'], r)
    ground = GROUNDS.get(r['question_id'], {})
    per = collections.OrderedDict()
    for a in ASPECTS:
        verdict = str(est[a]) if a in est else 'UNRESOLVED'
        if a in ground:
            position, why = ground[a]
        elif a in mech:
            position, why = mech[a], 'settled by the served contract'
        else:
            position, why = 'cannot_establish', 'this event does not settle it for me'
        tally['%s|%s' % (a, position)] += 1
        per[a] = collections.OrderedDict([
            ('existing_verdict', verdict), ('review', position), ('ground', why)])
    item = r['produced_record']['item']
    questions.append(collections.OrderedDict([
        ('question_id', r['question_id']), ('batch_id', r['batch_id']),
        ('prompt_sha256', r['prompt_sha256']),
        ('event_source_id', r['event_source_id']),
        ('event_date', r['event_date']), ('part_ref', r['part_ref']),
        ('quote_verbatim_in_part', r['quote_found_verbatim_in_part']),
        ('driver_name', item.get('driver_name')),
        ('driver_state', item.get('driver_state')),
        ('company_confirmed', item.get('company_confirmed')),
        ('quote', item.get('quote')),
        ('reference_name', (r['reference_card'] or {}).get('reference_name')),
        ('aspects', per),
    ]))

out = collections.OrderedDict([
    ('scope', 'review of the TEST over every G2 question whose produced '
              'fact_type is guidance; no grade rewritten, no key touched'),
    ('population_sha256', sha(sys.argv[1])),
    ('guidance_questions', len(questions)),
    ('repeatability', collections.OrderedDict([
        ('records_asked_more_than_once', len(repeated)),
        ('askings', sum(len(rs) for rs in repeated)),
        ('record_x_aspect_cells', cells),
        ('identical_across_askings', agree_cells),
        ('decided_both_ways', hard),
        ('decided_once_unresolved_elsewhere', soft),
        ('rate', round(agree_cells / float(cells), 4)),
        ('contradictions', contradictions),
    ])),
    ('review_tally', collections.OrderedDict(sorted(tally.items()))),
    ('questions', questions),
])
with io.open(sys.argv[2], 'w', encoding='utf-8') as fh:
    fh.write(json.dumps(out, indent=1) + '\n')
print(json.dumps({k: out[k] for k in
                  ('guidance_questions', 'repeatability', 'review_tally')},
                 indent=1)[:2000])
print('WROTE', sys.argv[2], sha(sys.argv[2]))
