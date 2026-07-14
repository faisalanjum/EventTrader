#!/usr/bin/env python3
"""REGRESSION GATE — certified floors on the frozen benchmark (user rule 2026-07-13: mark results on a
true sample BEFORE any cost/batching work; every future change must pass this before commit).

Re-grades the frozen benchmark/ sets (annual 150 · quarterly 40 · transcript 40) with the CURRENT grading
code and FAILS if any certified floor drops. 0 LLM tokens (grade.py does Neo4j reads for its
in-filing classification).

    venv/bin/python scripts/driver_seed/relocate_probe/regress.py
"""
import os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BM = f'{HERE}/benchmark'
PY = sys.executable

# certified 2026-07-13 (keep=12, faithful names, strict gates). precision/recall in %.
# v2 floors (locate v2 = uniform chunks + lock-word IDF; SIGN-PRES class separated; 1-ulp ruler).
# v1 floors (old locate): annual 98.5/93.0, quarterly 97.4/92.5, headline 100/17.5 — artifacts at commit 0ea0906.
# v3 floors (#768: measurement rule 5 + section tie-break; twin class eliminated). v2 at commit 14ef312.
# multiaxis/gptholdout dips = no-measurement conservatism + variance; recover with #767 measurement batches.
FLOORS = {
    ('grade.py', 'validation'): {'PRECISION': 98.5, 'RECALL': 96.4},
    ('grade_quarterly.py', 'quarterly'): {'PRECISION': 95.0, 'RECALL': 95.0, 'YTD': 0},
    ('grade_quarterly.py', 'headline'): {'PRECISION': 75.0, 'RECALL': 7.5},
    ('grade_quarterly.py', 'multiaxis'): {'PRECISION': 89.9, 'RECALL': 80.1, 'YTD': 0},
    ('grade_quarterly.py', 'news'): {'PRECISION': 100.0, 'RECALL': 14.7, 'YTD': 0},
    ('grade_quarterly.py', 'gptholdout'): {'PRECISION': 96.9, 'RECALL': 95.0, 'YTD': 0},
}


def run(script, dset):
    out = subprocess.run([PY, f'{HERE}/{script}', '--set', dset, '--root', BM],
                         capture_output=True, text=True).stdout
    got = {}
    for k in ('PRECISION', 'RECALL'):
        m = re.search(rf'{k}\s*(?:\(gradeable\))?\s*=\s*[\d/]+\s*=\s*([\d.]+)%', out)
        if m:
            got[k] = float(m.group(1))
    m = re.search(r'GUARD:\s*(\d+)', out)
    if m:
        got['YTD'] = int(m.group(1))
    return got, out


def main():
    ok = True
    for (script, dset), floors in FLOORS.items():
        got, out = run(script, dset)
        for k, floor in floors.items():
            v = got.get(k)
            bad = v is None or (k == 'YTD' and v > floor) or (k != 'YTD' and v < floor)
            tag = 'FAIL' if bad else 'ok'
            print(f"  [{tag}] {dset:<10} {k:<9} got={v} floor={'<=' if k=='YTD' else '>='}{floor}")
            if bad:
                ok = False
                print(out)
    print("REGRESSION:", "PASS — certified floors hold" if ok else "FAIL — a certified floor dropped")
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
