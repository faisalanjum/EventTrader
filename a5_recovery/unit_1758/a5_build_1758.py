# -*- coding: utf-8 -*-
"""The recorded A5 deterministic build, run inside the boundary (Codex 1758 step 3).

This is the SEQ 1514 build program: build the corrected kit twice into fresh
directories, require them byte-identical, freeze the candidate, and report the
manifest identity and the counts the approved candidate must carry. It calls no
model and writes only into the three logical output directories the map binds.
"""
import hashlib
import io
import json
import os
import sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
sys.path.insert(0, H)
sys.path.insert(0, "/home/faisal/EventMarketDB")
import build_a5_exp5_kit as A5                                # noqa: E402

WANT_MANIFEST = "6780a746a7deb41dc1ed6a249c1139b5f6d9af6fc86875f0b197a225ae9b972a"
WANT_INVENTORY = "1440d75131c0c7418a66821778a88d5c1ff8fd9bdf7f4cca4d561b596c1b3066"
WANT_BACKMAP = "b502407ca9dd497287fa46f3799ca6d713bb8838163581d3436e865039a6a18f"
CHECKS = []


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def tree(d):
    o = {}
    for root, _ds, fs in os.walk(d):
        for f in fs:
            o[os.path.relpath(os.path.join(root, f), d)] = sha(os.path.join(root, f))
    return o


def check(name, got, want):
    ok = got == want
    CHECKS.append((name, ok))
    print("%s %-52s %s%s" % ("ok  " if ok else "BAD ", name, str(got)[:60],
                             "" if ok else "   != %s" % str(want)[:60]), flush=True)


print("inventory_problems:", A5.inventory_problems(), flush=True)
print("resolved inventory:", sha(A5.corrected_inventory())[:16], flush=True)
check("A5 serves the corrected inventory", sha(A5.corrected_inventory()), WANT_INVENTORY)

a, b, cand = S + "/a5_build_a_1758", S + "/a5_build_b_1758", S + "/a5_candidate_1758"
for d in (a, b, cand):
    if os.listdir(d):
        raise SystemExit("REFUSED: %s is not empty; a build is never run over a result" % d)

pa, ha, _doc = A5.build(a)
pb, hb, _ = A5.build(b)
pc, hc, _ = A5.build(cand)
check("the double build is byte-identical", tree(a) == tree(b) == tree(cand), True)
check("the three manifest hashes agree", (ha == hb == hc), True)
check("the candidate manifest", hc, WANT_MANIFEST)

man = json.load(io.open(pc, encoding="utf-8"))
check("events", man["n_events"], 36)
check("packets", man["n_packets"], 196)
check("planned producer calls", man["planned_producer_calls"], 392)
check("launcher templates", len(man["launcher_sha256"]), 36)
check("packet prompts", len(man["prompt_sha256"]), 196)
check("menu back-map", man["menu_backmap_sha256"], WANT_BACKMAP)
check("bound inventory", man["inventory_sha256"], WANT_INVENTORY)

out = {"manifest_path": pc, "manifest_sha256": hc, "files": len(tree(cand)),
       "n_events": man["n_events"], "n_packets": man["n_packets"],
       "planned_producer_calls": man["planned_producer_calls"],
       "launchers": len(man["launcher_sha256"]), "prompts": len(man["prompt_sha256"]),
       "menu_backmap_sha256": man["menu_backmap_sha256"],
       "inventory_sha256": man["inventory_sha256"],
       "contract_suffix": man.get("contract_suffix"),
       "reply_shape": man.get("reply_shape"),
       "a2_runtime_freeze": man.get("a2_runtime_freeze"),
       "scorer_sha256": man["bound_inputs"].get("scorer_sha256"),
       "matcher_sha256": man["bound_inputs"].get("matcher_sha256"),
       "event_source_sha256": man["bound_inputs"].get("event_source_sha256")}
io.open(cand + "/A5_BUILD_RESULT.json", "w", encoding="utf-8").write(json.dumps(out, indent=1))
print(json.dumps(out, indent=1), flush=True)

bad = [n for n, ok in CHECKS if not ok]
print("checks %d  failed %d  %s" % (len(CHECKS), len(bad), bad), flush=True)
print("A5_BUILD_1758_DONE" if not bad else "A5_BUILD_1758_MISMATCH", flush=True)
sys.exit(1 if bad else 0)
