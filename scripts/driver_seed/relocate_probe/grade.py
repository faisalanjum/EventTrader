#!/usr/bin/env python3
"""Grade a blind-relocation run (v3 — strict blind grading, NO magnitude guard).

    venv/bin/python scripts/driver_seed/relocate_probe/grade.py --set design
    venv/bin/python scripts/driver_seed/relocate_probe/grade.py --set holdout

Blind fetch = the pipeline never sees the target value, so we grade on the EXACT number the agent
picked (r.value), rounding-tolerant. Emitted = found AND verify-correct. CORRECT if the picked
number equals the true target within tolerance; else MISBIND (a real precision failure — wrong
column, wrong line, etc.). Also reports: seed-evidence validity (does the quote losslessly contain
the target — what the real seed gate would accept) and a magnitude DIAGNOSTIC (not a guard): how
many emissions a >5x-band would have flagged, so we can see whether magnitude is even needed.
"""
import os, re, json, argparse, sys, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import link_lib as L

HERE = os.path.dirname(__file__)


def scaled_forms(vstr):
    s = re.sub(r'[^0-9.]', '', (vstr or '').replace(',', ''))
    try:
        x = float(s)
    except ValueError:
        return []
    return [x * sc for sc in (1, 1e3, 1e6, 1e9, 1e12) if x > 0]


def right_number(vstr, target, tol=0.01):
    """rounding-tolerant: some scale of the picked number is within tol of the true target."""
    t = abs(float(target))
    return t > 0 and any(abs(f - t) / t <= tol for f in scaled_forms(vstr))


def mag_flag(vstr, lock_value):
    """DIAGNOSTIC only (not used to gate): would a 0.2x..5x band flag this as implausible?"""
    lv = abs(float(lock_value))
    return lv > 0 and not any(lv / 5 <= f <= lv * 5 for f in scaled_forms(vstr))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--set', default='design'); a = ap.parse_args()
    truth = {t['id']: t for t in (json.loads(l) for l in open(f'{HERE}/truth_{a.set}.jsonl'))}
    recs = {r['i']: r for r in json.load(open(f'{HERE}/relocate_out_{a.set}.json'))['records']}

    correct = misbind = abstain = ceiling = seed_ok = mag_would_flag = 0
    rows = []
    for i, t in sorted(truth.items()):
        b = json.load(open(f'{HERE}/batches_{a.set}/batch_{i}.json'))
        ctexts = [c['text'] for c in b['candidates']]
        tv, fmt, lv = t['value_target'], t['fmt'], t['value_lock']
        ceiling += any(L.value_ok(tv, fmt, c) for c in ctexts)
        r = recs.get(i)
        emitted = bool(r and r['found'] and r['correct'])
        if not emitted:
            rows.append((i, t['ticker'], t['kpi'][:30], t['period_target'], 'abstain', '')); abstain += 1
            continue
        ok = right_number(r['value'], tv)
        if ok:
            correct += 1
        else:
            misbind += 1
        seed_ok += bool(L.value_ok(tv, fmt, r['quote']))          # quote contains target losslessly
        mag_would_flag += mag_flag(r['value'], lv)
        note = '' if ok else f"picked {r['value']!r} vs true~{tv}"
        rows.append((i, t['ticker'], t['kpi'][:30], t['period_target'], 'CORRECT' if ok else 'MISBIND', note))

    print(f"{'id':>2} {'tick':<5} {'kpi':<30} {'target':<11} {'result':<8} note")
    for r in rows:
        print(f"{r[0]:>2} {r[1]:<5} {r[2]:<30} {r[3]:<11} {r[4]:<8} {r[5]}")
    emitted = correct + misbind; n = len(truth)
    print(f"\n[{a.set}]  emitted {emitted} | CORRECT {correct} | MISBIND {misbind} | abstain {abstain}  (of {n})")
    print(f"  PRECISION = {correct}/{emitted} = {100*correct/emitted:.1f}%" if emitted else "  precision n/a")
    print(f"  recall    = {correct}/{n} = {100*correct/n:.1f}%")
    print(f"  recall ceiling (target present in a candidate) = {ceiling}/{n} = {100*ceiling/n:.1f}%")
    print(f"  seed-evidence: emitted quotes that losslessly contain the target = {seed_ok}/{emitted}")
    print(f"  magnitude DIAGNOSTIC: emissions a 0.2x-5x band would flag = {mag_would_flag}")

    # per-metric-type breakdown (which categories to trust)
    by = collections.defaultdict(lambda: [0, 0, 0])          # type -> [correct, misbind, n]
    for i, t in truth.items():
        r = recs.get(i); typ = t.get('type', 'other')
        by[typ][2] += 1
        if r and r['found'] and r['correct']:
            if right_number(r['value'], t['value_target']):
                by[typ][0] += 1
            else:
                by[typ][1] += 1
    print(f"\n  {'type':<12}{'prec':>10}{'recall':>10}   (emitted, n)")
    for typ in sorted(by):
        c, m, tot = by[typ]
        e = c + m
        prec = f"{100*c/e:.0f}%" if e else "-"
        print(f"  {typ:<12}{prec:>10}{100*c/tot:>9.0f}%   ({e}, {tot})")


if __name__ == '__main__':
    main()
