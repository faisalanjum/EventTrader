#!/usr/bin/env python3
"""Grade the quarterly oracle run — precision + the Q-vs-YTD guard diagnostic + per-type (incl. multi-axis).
Truth = XBRL oracle. A pick that matches the YTD (183/273d) value is a wrong-period misbind the guard exists
to prevent. 0 Neo4j / 0 LLM (grades the saved bind output against the oracle values)."""
import os, re, sys, json, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import link_lib as L

HERE = os.path.dirname(__file__)


def main():
    truth = {t['id']: t for t in (json.loads(l) for l in open(f'{HERE}/truth_quarterly.jsonl'))}
    recs = {r['i']: r for r in json.load(open(f'{HERE}/relocate_out_quarterly.json'))['records']}
    C = collections.Counter()
    by = collections.defaultdict(lambda: collections.Counter())     # type -> {correct, emitted, total}
    rows = []
    for i, t in sorted(truth.items()):
        typ = t['type']; by[typ]['total'] += 1
        r = recs.get(i)
        if not (r and r['found'] and r.get('value')):
            C['abstain'] += 1; continue
        # (b) Step-0 emit gates (production config): quote must be verbatim in a candidate AND the picked
        # value must be a real number — a hallucinated quote or a "—" pick is abstained, not emitted.
        cands = [L._tidy(c['text']) for c in json.load(open(f'{HERE}/batches_quarterly/batch_{i}.json'))['candidates']]
        vcore = re.sub(r'[^0-9.,]', '', r['value'] or '')
        val_in_cand = bool(re.search(r'\d', vcore)) and any(vcore in c for c in cands)
        if L._parse_stated(r['value']) is None or not val_in_cand:   # "—" or hallucinated number -> abstain
            C['gate-abstain'] += 1; continue
        v = r['value']; by[typ]['emitted'] += 1
        if L.stated_match(v, t['value_target']):
            C['CORRECT'] += 1; by[typ]['correct'] += 1
        elif t.get('ytd_distractor') and L.stated_match(v, t['ytd_distractor']):
            C['YTD-MISBIND'] += 1; rows.append((i, t['ticker'], t['kpi'][:34], 'YTD', v, t['value_target']))
        else:
            C['MISBIND'] += 1; rows.append((i, t['ticker'], t['kpi'][:34], 'other', v, t['value_target']))
    emit = C['CORRECT'] + C['YTD-MISBIND'] + C['MISBIND']; n = len(truth)
    print(f"QUARTERLY (oracle truth) — {n} pairs, bind-only:")
    print(f"  emitted {emit} | CORRECT {C['CORRECT']} | YTD-MISBIND {C['YTD-MISBIND']} | other-MISBIND {C['MISBIND']} | abstain {C['abstain']}")
    print(f"  PRECISION = {C['CORRECT']}/{emit} = {100*C['CORRECT']/max(emit,1):.1f}%")
    print(f"  RECALL    = {C['CORRECT']}/{n} = {100*C['CORRECT']/n:.1f}%")
    print(f"  Q-vs-YTD GUARD: {C['YTD-MISBIND']} picks were the year-to-date value (the guard must prevent these)")
    print(f"  per type:")
    for typ in sorted(by):
        c = by[typ]; e = c['emitted']
        print(f"    {typ:<12} precision {c['correct']}/{e} = {100*c['correct']/max(e,1):.0f}%   recall {c['correct']}/{c['total']}")
    if rows:
        print("  misbinds:")
        for row in rows:
            print("   ", row)


if __name__ == '__main__':
    main()
