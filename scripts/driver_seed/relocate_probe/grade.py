#!/usr/bin/env python3
"""Grade a blind-relocation run — HONEST RULER (Phase 0).

    venv/bin/python scripts/driver_seed/relocate_probe/grade.py --set validation

Replaces the old sign-blind, 1%-tolerant grader. ONE matcher (stated_match): the model's printed
number must equal the true value at ITS OWN stated precision, over the scale ladder, sign-aware — so
rounded prose ("24.6" for 24.644B) still counts, but a wrong-column pick on a slow metric no longer
gets free credit. Three outcomes, not two:
  CORRECT        — printed value matches truth at stated precision
  TRUE-MISBIND   — emitted a wrong value AND truth was actually IN the filing (a real pipeline error)
  UNGRADEABLE-REF— fiscal.ai's value is NOT in the target filing (adjusted/restated) -> we can't grade
Precision/recall are computed over GRADEABLE pairs only; UNGRADEABLE-REF is reported separately.
Also prints the verify quadrant (did the verify step help or hurt?). Neo4j read-only; 0 LLM tokens.
"""
import os, re, json, argparse, sys, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import link_lib as L
import run_code_tier as RC

HERE = os.path.dirname(__file__)
SCALE_WORD = {'thousand': 1e3, 'thousands': 1e3, 'million': 1e6, 'millions': 1e6,
              'billion': 1e9, 'billions': 1e9, 'trillion': 1e12, 'trillions': 1e12}


def _parse(vstr):
    s = (vstr or '').lower().strip()
    if not re.search(r'\d', s):
        return None
    neg = ('(' in s and ')' in s) or s.lstrip().startswith('-')
    mult = next((m for w, m in SCALE_WORD.items() if w in s), None)
    core = re.sub(r'[^0-9.]', '', s)
    if not re.search(r'\d', core) or core.count('.') > 1:
        return None
    dec = len(core.split('.')[1]) if '.' in core else 0
    return neg, float(core), dec, mult


def stated_match(vstr, truth):
    """printed value == truth at the printed number's own precision, sign-aware, over the scale ladder."""
    p = _parse(vstr)
    if p is None:
        return False
    neg, val, dec, mult = p
    if neg != (float(truth) < 0):
        return False
    at = abs(float(truth))
    for sc in ([mult] if mult else (1, 1e3, 1e6, 1e9, 1e12)):
        st = at / sc
        if st >= 0.5 and round(st, dec) == round(val, dec):
            return True
    return False


def _check():
    assert stated_match("6,115", 6115000000) and stated_match("$ 6,115", 6115000000)
    assert stated_match("24.6", 24643957000)               # rounded-consistent -> CORRECT
    assert stated_match("$768.9 million", 768900000)
    assert stated_match("( 196.7 )", -196700000)           # negative, paren
    assert not stated_match("1,017.0", 989400000)          # genuine mismatch
    assert not stated_match("644", -734000000)             # sign mismatch (pos vs neg)
    assert not stated_match("508,713", 508700000)          # exact filing != rounded reference


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--set', default='validation'); a = ap.parse_args()
    _check()
    truth = {t['id']: t for t in (json.loads(l) for l in open(f'{HERE}/truth_{a.set}.jsonl'))}
    recs = {r['i']: r for r in json.load(open(f'{HERE}/relocate_out_{a.set}.json'))['records']}

    RC.load_env_neo4j()
    from neo4j import GraphDatabase
    drv = GraphDatabase.driver(os.environ['NEO4J_URI'],
                               auth=(os.environ.get('NEO4J_USERNAME', 'neo4j'), os.environ['NEO4J_PASSWORD']))
    corpus_cache = {}

    def in_filing(tk, form, period, value, fmt):
        key = (tk, form, period)
        if key not in corpus_cache:
            with drv.session() as s:
                xb, tx, _ = RC.fetch_corpus(s, tk, form, period)
                tx = tx + RC.fetch_press_release(s, tk, period)
            corpus_cache[key] = [L._tidy(x) for x in tx] + xb           # text + raw XBRL JSON
        return any(L.value_ok(value, fmt, blob) for blob in corpus_cache[key])

    C = collections.Counter()               # outcome counts
    quad = collections.Counter()            # verify quadrant (accept/reject x right/wrong), gradeable
    by = collections.defaultdict(lambda: collections.Counter())   # per-type
    rows = []
    for i, t in sorted(truth.items()):
        b = json.load(open(f'{HERE}/batches_{a.set}/batch_{i}.json'))
        tv, fmt = t['value_target'], t['fmt']
        r = recs.get(i)
        found = bool(r and r['found'] and r.get('value'))
        emitted = bool(found and r['correct'])
        right = found and stated_match(r['value'], tv)               # is the BIND value right?
        gradeable = right or in_filing(t['ticker'], b['form'], t['period_target'], tv, fmt)

        if not gradeable:
            outcome = 'UNGRADEABLE-REF'
        elif emitted and right:
            outcome = 'CORRECT'
        elif emitted:
            outcome = 'TRUE-MISBIND'
        else:
            outcome = 'abstain'
        C[outcome] += 1
        by[t.get('type', 'other')][outcome] += 1
        if gradeable and found:                                      # verify quadrant over gradeable binds
            quad[('accept' if r['correct'] else 'reject', 'right' if right else 'wrong')] += 1
        if outcome in ('TRUE-MISBIND', 'UNGRADEABLE-REF'):
            rows.append((i, t['ticker'], t['kpi'][:30], outcome, f"picked {r['value']!r} vs {tv}"))

    grad = C['CORRECT'] + C['TRUE-MISBIND'] + C['abstain']           # gradeable pairs
    emit = C['CORRECT'] + C['TRUE-MISBIND']
    print(f"[{a.set}]  n={len(truth)}  gradeable={grad}  UNGRADEABLE-REF={C['UNGRADEABLE-REF']}")
    print(f"  CORRECT {C['CORRECT']} | TRUE-MISBIND {C['TRUE-MISBIND']} | abstain {C['abstain']}")
    print(f"  PRECISION (gradeable) = {C['CORRECT']}/{emit} = {100*C['CORRECT']/emit:.1f}%" if emit else "  precision n/a")
    print(f"  RECALL    (gradeable) = {C['CORRECT']}/{grad} = {100*C['CORRECT']/grad:.1f}%" if grad else "")
    print(f"\n  VERIFY QUADRANT (gradeable binds):")
    print(f"    accept & right {quad[('accept','right')]:>3}   accept & wrong {quad[('accept','wrong')]:>3}  (precision leaks verify let through)")
    print(f"    reject & right {quad[('reject','right')]:>3}   reject & wrong {quad[('reject','wrong')]:>3}  (right=recall verify KILLED, wrong=real catches)")
    print(f"\n  {'type':<12}{'prec':>7}{'recall':>8}   C/MB/abst/ungr")
    for typ in sorted(by):
        c = by[typ]; e = c['CORRECT'] + c['TRUE-MISBIND']; g = e + c['abstain']
        pr = f"{100*c['CORRECT']/e:.0f}%" if e else "-"
        rc = f"{100*c['CORRECT']/g:.0f}%" if g else "-"
        print(f"  {typ:<12}{pr:>7}{rc:>8}   {c['CORRECT']}/{c['TRUE-MISBIND']}/{c['abstain']}/{c['UNGRADEABLE-REF']}")
    print(f"\n  TRUE-MISBIND + UNGRADEABLE-REF detail:")
    for r in rows:
        print(f"    [{r[0]}] {r[1]:<5} {r[2]:<30} {r[3]:<16} {r[4]}")
    drv.close()


if __name__ == '__main__':
    main()
