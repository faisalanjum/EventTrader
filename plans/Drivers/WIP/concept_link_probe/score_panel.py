#!/usr/bin/env python3
"""Score the 3-lens panel: a link is PROVEN if >=2 of 3 lenses say real.
Works on partial data (only scores links whose company has all 3 lens files)."""
import json, pathlib, collections

CLP = pathlib.Path("/tmp/claude-1000/-home-faisal-EventMarketDB/1fc7fcb8-680c-48d0-a64c-ac3f73b686ef/scratchpad/clp")
LENSES = ["value", "filer", "name"]

def main():
    audit = json.loads((CLP / "audit_set.json").read_text())
    by_co = collections.defaultdict(list)
    for r in audit:
        by_co[r["t"]].append(r)
    proven, refuted, incomplete = [], [], 0
    complete_cos = []
    for t in sorted(by_co):
        verds = {}
        ok = True
        for L in LENSES:
            f = CLP / "panel_out" / f"{t}_{L}.json"
            if not f.exists():
                ok = False; break
            verds[L] = {(r["slug"], r["qname"]): r.get("real") for r in json.loads(f.read_text())}
        if not ok:
            incomplete += len(by_co[t]); continue
        complete_cos.append(t)
        for r in by_co[t]:
            key = (r["slug"], r["q"])
            votes = [verds[L].get(key) for L in LENSES]
            nreal = sum(v is True for v in votes)
            (proven if nreal >= 2 else refuted).append((t, r["slug"], r["q"], votes))
    n = len(proven) + len(refuted)
    print(f"=== 3-lens panel (companies complete: {len(complete_cos)}/29) ===")
    print(f"scored links: {n}  (incomplete-company links pending: {incomplete})")
    if n:
        print(f"  PROVEN (>=2/3 real): {len(proven)} = {len(proven)/n:.1%}")
        print(f"  refuted (<2/3):      {len(refuted)}")
    print("--- refuted-by-panel (would be dropped → abstain; audit) ---")
    for t, s, q, votes in refuted:
        print(f"  {t}|{s} -> {q.split(':')[-1][:34]}  votes(value,filer,name)={votes}")
    print("--- sample PROVEN ---")
    for t, s, q, votes in proven[:15]:
        print(f"  {t}|{s} -> {q.split(':')[-1][:34]}  {votes}")

if __name__ == "__main__":
    main()
