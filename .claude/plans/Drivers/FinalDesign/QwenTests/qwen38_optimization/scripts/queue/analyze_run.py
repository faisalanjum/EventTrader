#!/usr/bin/env python3
"""Summarise a choice_v2 results dir: accuracy (from score.json if present),
per-family cold/warm timings, prime calls, wall time. Usage: analyze_run.py <results_dir>"""
import json, sys, os, collections
d = sys.argv[1]
rows = [json.loads(l) for l in open(os.path.join(d, "raw_results.jsonl"))]
rr = json.load(open(os.path.join(d, "run_record.json"))) if os.path.exists(os.path.join(d, "run_record.json")) else {}
sc = json.load(open(os.path.join(d, "score.json"))) if os.path.exists(os.path.join(d, "score.json")) else {}
ok = [r for r in rows if r.get("ok")]
fails = [r for r in rows if not r.get("completed_response")]
print(f"rows={len(rows)} ok={len(ok)} transport_failures={len(fails)}")
if sc:
    keys = [k for k in sc if k in ("correct", "wrong", "abstained", "invalid", "precision", "recall", "total", "result", "label")]
    print("SCORE:", {k: sc[k] for k in keys} if keys else {k: sc[k] for k in list(sc)[:8]})
fam = collections.OrderedDict()
for r in rows:
    if not r.get("completed_response"):
        continue
    f = r["id"].rsplit("-", 1)[0]
    fam.setdefault(f, []).append(r["stats"].get("wall_s", 0))
tot = 0
print(f"{'family':8s} {'n':>2s}  walls (s)")
for f, w in fam.items():
    tot += sum(w)
    print(f"{f:8s} {len(w):2d}  " + " ".join(f"{x:6.1f}" for x in w))
pc = rr.get("prime_calls") or []
ptot = sum(p.get("wall_s", 0) for p in pc)
print(f"case walls total {tot:.0f}s ({tot/60:.1f} min); prime calls {len(pc)} total {ptot:.0f}s; "
      f"run_record wall_seconds (last attempt) {rr.get('wall_seconds')}")
if pc:
    print("prime prefill s:", [round((p.get('stats') or {}).get('prompt_eval_s', -1), 1) for p in pc])
print(f"GRAND TOTAL (cases + primes) {tot+ptot:.0f}s = {(tot+ptot)/60:.1f} min")
