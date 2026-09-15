"""The bounded collection's own progress, against BOTH denominators.

24 required lanes and 38 required questions are different things, so they are
counted separately and never mixed. Every number is derived from the operator's
own frozen roots, its finalization files and the preserved-run ledger - nothing
is typed and no outcome is judged here.

    python3 -B collection_progress_2173.py
"""
import collections
import glob
import io
import json
import os

UNIT = os.path.dirname(os.path.abspath(__file__))
PREP = os.path.join(os.path.dirname(UNIT), 'unit_2020_codex_check',
                    'codex_changedprep2171_a')
KINDS = sorted(k for k in os.listdir(UNIT)
               if os.path.isfile(os.path.join(UNIT, k, 'run', 'root.json')))


def read(path):
    return json.load(io.open(path, encoding='utf-8'))


def launched_runs():
    """(kind, segment) pairs a preserved run exists for."""
    path = os.path.join(UNIT, 'COLLECTION_LEDGER_2173.jsonl')
    out = set()
    if os.path.isfile(path):
        for line in io.open(path, encoding='utf-8'):
            line = line.strip()
            if not line.startswith('{'):
                continue
            row = json.loads(line)
            if 'run_id' in row:
                out.add((row['kind'], row['segment']))
    return out


report, total = collections.OrderedDict(), collections.Counter()
runs = launched_runs()
for kind in KINDS:
    run = os.path.join(UNIT, kind, 'run')
    root = read(os.path.join(run, 'root.json'))
    candidate = read(os.path.join(PREP, kind, 'a7_g1_candidate.json'))
    lanes_required = len(root['rows'])
    scheduled = {int(os.path.basename(p).split('.seg')[1].split('.')[0])
                 for p in glob.glob(os.path.join(run, 'receipt.seg*.json'))}
    scheduled_lanes = {arg['lane_id'] for segment in scheduled
                       for arg in read(os.path.join(
                           run, 'invocation.seg%02d.json' % segment))['args']}
    launched_lanes = {arg['lane_id'] for k, segment in runs if k == kind
                      for arg in read(os.path.join(
                          run, 'invocation.seg%02d.json' % segment))['args']}
    # (lane, attempt) -> validity, exactly as the operator finalized it. A
    # retry lawfully re-finalizes a lane, so attempt is part of the key.
    outcomes, problems = {}, {}
    for path in sorted(glob.glob(os.path.join(run, 'finalization.seg*.json'))):
        done = read(path)
        for lane, ok in done['validity']:
            outcomes[(lane, done['attempt'])] = ok
        problems.update(done.get('problems') or {})
    standing = {}
    for (lane, attempt), ok in sorted(outcomes.items()):
        if lane not in standing or attempt >= standing[lane][0]:
            standing[lane] = (attempt, ok)
    usable = sorted(l for l, (_a, ok) in standing.items() if ok)
    invalid = sorted(l for l, (_a, ok) in standing.items() if not ok)
    exhausted = sorted(l for l in invalid
                       if standing[l][0] >= root['max_attempts'])
    retry = [l for l in invalid if standing[l][0] < root['max_attempts']]
    problems = {l: problems[l] for l in invalid if l in problems}
    finalized = sorted(standing)
    waiting = sorted(row['lane_id'] for row in root['rows']
                     if row['lane_id'] not in standing)
    # A batch's questions are covered when EVERY lane of that batch stands
    # valid; the lanes of one batch read the same prompt.
    by_batch = collections.defaultdict(list)
    for row in root['rows']:
        by_batch[row['lane_id'].split('/')[0]].append(row['lane_id'])
    sizes = {row['batch_id']: row['items'] for row in candidate['batch_rows']}
    covered = sum(sizes[b] for b, lanes in by_batch.items()
                  if all(l in usable for l in lanes))
    report[kind] = collections.OrderedDict([
        ('lanes_required', lanes_required),
        ('lanes_scheduled', len(scheduled_lanes)),
        ('lanes_launched', len(launched_lanes)),
        ('lanes_finalized', len(finalized)),
        ('lanes_usable', len(usable)),
        ('lanes_invalid', len(invalid)),
        ('lanes_exhausted', len(exhausted)),
        ('lanes_waiting', len(waiting)),
        ('questions_required', candidate['questions']),
        ('questions_covered_by_usable_lanes', covered),
        ('max_attempts', root['max_attempts']),
        ('retry_eligible_lanes', sorted(retry)),
        ('invalid_lanes', invalid),
        ('exhausted_lanes', exhausted),
        ('waiting_lanes', waiting),
        ('problems', problems),
    ])
    for field in ('lanes_required', 'lanes_scheduled', 'lanes_launched',
                  'lanes_finalized', 'lanes_usable', 'lanes_invalid',
                  'lanes_exhausted', 'lanes_waiting', 'questions_required',
                  'questions_covered_by_usable_lanes'):
        total[field] += report[kind][field]

doc = collections.OrderedDict([
    ('scope', 'bounded collection progress; lanes and questions are DISTINCT '
              'denominators and no outcome is judged here'),
    ('per_kind', report),
    ('total', collections.OrderedDict(sorted(total.items()))),
])
text = json.dumps(doc, indent=1) + '\n'
io.open(os.path.join(UNIT, 'COLLECTION_PROGRESS_2173.json'), 'w',
        encoding='utf-8').write(text)
print(json.dumps(doc['total'], sort_keys=True))
