# -*- coding: utf-8 -*-
"""Derive durable collection progress from the operator's own finalization files.

Reads nothing but <kind>/run/finalization.seg*.json, which the existing ingest
owner writes. Sums no rule and decides nothing: it counts lanes and reprints the
operator's own ledger fields, so Codex can review progress without a mailbox
message. Writing this file is the only side effect.
"""
import glob
import json
import os
import sys

sys.dont_write_bytecode = True
UNIT = os.path.dirname(os.path.abspath(__file__))
KINDS = sorted(d for d in os.listdir(UNIT)
               if os.path.isfile(os.path.join(UNIT, d, 'run', 'root.json')))
PRIMARY = {k: len(json.load(open(os.path.join(UNIT, k, 'run',
                                              'root.json')))['rows'])
           for k in KINDS}

out = {'primary_target': PRIMARY, 'roots': {}, 'problems': {}, 'retry_lanes': {}}
grand = {'segments': 0, 'lanes': 0, 'valid': 0, 'invalid': 0, 'retry': 0,
         'uncalled': 0, 'scheduled': 0}
for kind in KINDS:
    tot = {k: 0 for k in grand}
    lanes, roots, cands = [], set(), set()
    seen, standing = [], {}
    for path in sorted(glob.glob(os.path.join(UNIT, kind, 'run',
                                              'finalization.seg*.json'))):
        doc = json.load(open(path))
        tot['segments'] += 1
        for field in ('valid', 'invalid', 'retry', 'uncalled', 'scheduled'):
            tot[field] += doc['ledger'][field]
        for lane, ok in doc['validity']:
            # A retry finalizes the same lane again at a higher attempt. Keep
            # the highest attempt as the lane's standing outcome; a repeat of
            # the SAME attempt would be a real duplicate and is asserted below.
            seen.append((lane, doc['attempt']))
            prev = standing.get(lane)
            if prev is None or doc['attempt'] >= prev[0]:
                standing[lane] = (doc['attempt'], ok, doc['problems'])
            lanes.append(lane)
        for lane in doc['retry']:
            out['retry_lanes'].setdefault(kind, []).append(lane)
        roots.add(doc['root_sha256'])
        cands.add(doc['candidate_sha256'])
    # Pair every finalized segment with the preserved raw evidence of its call.
    # The state file is the transport's own record, so this compares the
    # operator's accounting against what was actually returned, not against a
    # second copy of the accounting.
    evid = {}
    for rec_path in sorted(glob.glob(os.path.join(UNIT, kind, 'evidence',
                                                  '*', '*.json'))):
        run_id = os.path.basename(os.path.dirname(rec_path))
        if os.path.basename(rec_path) != run_id + '.json':
            continue
        rec = json.load(open(rec_path))
        rows = rec['result']['results']
        evid[run_id] = {
            'lanes': [r['lane_id'] for r in rows],
            'attempts': sorted({r['attempt'] for r in rows}),
            'candidates': sorted({r['candidate_sha256'] for r in rows}),
            'runtime_models': sorted({r['runtime_model_id'] for r in rows}),
            'errors': [r['lane_id'] for r in rows if r['error']],
            'empty_text': [r['lane_id'] for r in rows if not (r['text'] or '').strip()],
        }
    called = [lane for e in evid.values() for lane in e['lanes']]
    out.setdefault('evidence', {})[kind] = {
        'runs': len(evid),
        'lanes_called': len(called),
        'lanes_called_twice': sorted(l for l in set(called)
                                     if called.count(l) > 1),
        'called_but_not_finalized': sorted(set(called) - set(lanes)),
        'finalized_but_no_evidence': sorted(set(lanes) - set(called)),
        'errors': sorted(l for e in evid.values() for l in e['errors']),
        'empty_text': sorted(l for e in evid.values() for l in e['empty_text']),
        'candidates': sorted({c for e in evid.values() for c in e['candidates']}),
        'runtime_models': sorted({m for e in evid.values()
                                  for m in e['runtime_models']}),
        'attempts': sorted({a for e in evid.values() for a in e['attempts']}),
        # The operator's ledger 'retry' field counts lanes marked ELIGIBLE for a
        # retry, not calls spent. A spent retry is an actual second attempt in the
        # raw evidence, so it is counted from the returned rows instead.
        'retry_calls_spent': sum(1 for e in evid.values()
                                 for a in e['attempts'] if a > 1),
    }
    for lane, (att, ok, probs) in standing.items():
        if not ok:
            out['problems'].setdefault(kind, {})[lane] = probs
    tot['lanes'] = len(standing)
    tot['final_valid'] = sum(1 for _a, ok, _p in standing.values() if ok)
    tot['final_invalid'] = sum(1 for _a, ok, _p in standing.values() if not ok)
    assert len(set(seen)) == len(seen), (
        'the same lane was finalized twice at the same attempt in %s' % kind)
    assert len(roots) <= 1 and len(cands) <= 1, 'identity drift in %s' % kind
    out['roots'][kind] = dict(tot, root_sha256=sorted(roots), lanes_done=len(standing),
                              remaining=PRIMARY[kind] - len(standing),
                              candidate_sha256=sorted(cands))
    for k in grand:
        grand[k] += tot[k]
out['total'] = dict(grand, remaining=sum(PRIMARY.values()) - grand['lanes'])
text = json.dumps(out, indent=1, sort_keys=True) + '\n'
open(os.path.join(UNIT, 'PROGRESS_2161.json'), 'w').write(text)
print(text, end='')
