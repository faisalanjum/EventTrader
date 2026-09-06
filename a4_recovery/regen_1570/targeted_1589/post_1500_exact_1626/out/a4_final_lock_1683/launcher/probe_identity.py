# -*- coding: utf-8 -*-
"""Import/read-identity probe (Codex SEQ 1689 step4 / 1691 step3). Audits every
project module AND data file the candidate reaches at import: each must resolve
under the constructed logical tree S (or an explicitly pinned durable input),
NONE from live /home/faisal/EventMarketDB. Writes the reached inventory."""
import sys, os, io, hashlib, builtins, importlib.util
S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
LIVE = "/home/faisal/EventMarketDB/"
DURABLE = "/home/faisal/EventMarketDB-driver-recovery/"   # explicitly-pinned durable inputs (e.g. a3 serial run)
INV = os.environ["PROBE_INVENTORY"]                        # unit/manifest path to write
opened = {}
_open, _ioopen = builtins.open, io.open
def _rec(path):
    try: p = os.path.abspath(path)
    except Exception: return
    if p.startswith(S) or p.startswith(LIVE) or p.startswith(DURABLE):
        opened.setdefault(p, None)
def _w1(*a, **k):
    if a: _rec(a[0])
    return _open(*a, **k)
def _w2(*a, **k):
    if a: _rec(a[0])
    return _ioopen(*a, **k)
builtins.open, io.open = _w1, _w2
spec = importlib.util.spec_from_file_location("build_final_key_candidate", S + "/lock/build_final_key_candidate.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)                                 # candidate full import chain
builtins.open, io.open = _open, _ioopen
def sha16(p):
    try: return hashlib.sha256(_open(p, "rb").read()).hexdigest()[:16]
    except Exception: return "?"
rows, leaks = [], []
# modules
for name, mod in sorted(sys.modules.items()):
    f = getattr(mod, "__file__", None)
    if not f or "/site-packages/" in f or f.startswith(sys.prefix): continue
    if f.startswith(S) or f.startswith(LIVE) or f.startswith(DURABLE):
        rows.append(("module", name, sha16(f), f)); 
        if f.startswith(LIVE): leaks.append(("module", name, f))
# data files opened
for p in sorted(opened):
    if p.endswith(".py") and (p.startswith(S) or p.startswith(LIVE)): continue   # modules already listed
    if "/site-packages/" in p or p.startswith(sys.prefix): continue
    rows.append(("data", os.path.basename(p), sha16(p), p))
    if p.startswith(LIVE): leaks.append(("data", os.path.basename(p), p))
with _open(INV, "w") as fh:
    fh.write("kind\tname\tsha16\tpath\n")
    for k, n, h, f in rows: fh.write("%s\t%s\t%s\t%s\n" % (k, n, h, f.replace(S, "S")))
mods = [r for r in rows if r[0] == "module"]; data = [r for r in rows if r[0] == "data"]
print("REACHED_MODULES", len(mods), "REACHED_DATA", len(data), "LEAKS_FROM_LIVE_MAIN", len(leaks))
for k, n, f in leaks: print("  LEAK", k, n, f)
sys.exit(1 if leaks else 0)
