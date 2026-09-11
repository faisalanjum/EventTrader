"""Review scheduling over every live slot, without model calls or writes.

Expected identities come from the preserved receipt, not the new scheduler.
Production contexts select a subsequence of that canonical receipt order.
"""
import collections
import json
import os
from pathlib import Path
import sys

UNIT = Path(__file__).resolve().parent
sys.path.insert(0, str(UNIT / 'owner'))
import a4_review_composite as R

H = R.HR
ctx = R._ctx()
full = dict(ctx)
full.pop('slots')
allowed = R.K._load(os.path.join(R.OLD_RUN, R.K.RECEIPT_NAME))['allowed']
slots = [(s.rsplit('/b', 1)[0], int(s.rsplit('/b', 1)[1])) for s in allowed]
counts = collections.Counter()


def check(name, ok):
    assert ok, name
    counts[name] += 1


def schedule(selected, labels, manifest=True):
    local = dict(full, slots=selected)
    check('canonical identity and order', H._canonical_of(local) == labels)
    check('lookup has the exact same identities', list(H._by_label_of(local)) == labels)
    if manifest:
        doc = H._manifest(local)
        check('manifest and budget use the exact selected denominator',
              doc['call_order'] == labels
              and doc['counts']['primary_calls'] == len(labels)
              and doc['budget']['primaries'] == len(labels)
              and doc['budget']['after_primaries'] == ctx['before'] + len(labels)
              and doc['budget']['worst_case_after'] == ctx['before'] + 2 * len(labels))
    for attempt, scheduled, spent in ((1, len(labels), len(labels)),
                                      (2, 1, len(labels) + 1)):
        budget = H._budget_after(local, attempt, scheduled)
        check('primary and one invalid-only retry count each call once',
              budget['this_attempt'] == scheduled
              and budget['frozen_primaries'] == len(labels)
              and budget['spent_so_far'] == spent
              and budget['ledger_after'] == ctx['before'] + spent)


check('historical default is unchanged', H._canonical_of(full) == allowed)
schedule(slots, allowed)
for index in range(len(slots)):
    schedule([slots[index]], [allowed[index]])
    schedule(slots[:index] + slots[index + 1:],
             allowed[:index] + allowed[index + 1:], manifest=False)
for task in full['tasks']:
    indexes = [i for i, pair in enumerate(slots) if pair[0] == task['task_id']]
    schedule([slots[i] for i in indexes], [allowed[i] for i in indexes])

invalid = [[], [('a task outside this frozen population', slots[0][1])],
           [(slots[0][0], max(b for _, b in slots) + 1)],
           [('malformed',)], [(slots[0][0], slots[0][1], 'extra')]]
invalid += [[pair, pair] for pair in slots]
for selected in invalid:
    check('negative has its real positive control', H._canonical_of(full) == allowed)
    try:
        H._canonical_of(dict(full, slots=selected))
    except (ValueError, TypeError):
        counts['foreign malformed empty or duplicate slots refused'] += 1
    else:
        raise AssertionError('an invalid schedule was accepted: %r' % (selected,))

# Renaming task identifiers must not introduce a vocabulary-dependent rule.
renamed = dict(full, tasks=[dict(t, task_id='unfamiliar_%d' % n)
                           for n, t in enumerate(full['tasks'])])
expected = ['unfamiliar_%d/b%d' % (n, b)
            for n in range(len(renamed['tasks'])) for b in (1, 2)]
check('unfamiliar task identities retain the same required behavior',
      H._canonical_of(renamed) == expected)

# The selected-slot owner and the ledger connection must both be load-bearing.
original_slots, original_budget = H._slots_of, H._budget_after
mutants = {
    'ignore selected slots': dict(_slots_of=lambda local: original_slots(full)),
    'charge the full population for a subset': dict(
        _budget_after=lambda local, attempt, scheduled:
        original_budget(full, attempt, scheduled)),
}
for name, changes in mutants.items():
    schedule([slots[0]], [allowed[0]], manifest=False)
    with R._using(H, **changes):
        try:
            schedule([slots[0]], [allowed[0]], manifest=False)
        except AssertionError:
            counts['meaningful scheduling or accounting mutation killed'] += 1
        else:
            raise AssertionError('surviving mutation: ' + name)
    schedule([slots[0]], [allowed[0]], manifest=False)

print(json.dumps({'model_calls': 0, 'live_slots': len(slots),
                  'live_tasks': len(full['tasks']), 'checks': dict(counts),
                  'passed_assertions': sum(counts.values())}, indent=1))
