"""Score results_wf.json against the frozen keys (JEV.md §6.8). Usage: python3 score_wf.py"""
import json, collections, statistics
SCRATCH = "/tmp/claude-1000/-home-faisal-EventMarketDB/7e6a5492-bcab-436c-8470-48a87eb77533/scratchpad"
H = {h["id"]: h["state"] for h in json.load(open(f"{SCRATCH}/tag_holdout.json"))}
K = json.load(open("wf_keys.json"))["keys"]; R = json.load(open("results_wf.json"))
TYPES = ["metric", "guidance", "surprise", "action_event"]; TK = {"M": "metric", "G": "guidance", "S": "surprise", "A": "action_event"}
STATES = ["increased", "decreased", "unchanged", "persists", "reported"]
pct = lambda a, b: f"{a}/{b} ({100*a/b:.0f}%)" if b else "0/0"
T = collections.defaultdict(dict); S = collections.defaultdict(dict); C = {}
for o in R:
    if o["task"] == "type": T[o["id"]][o["run"]] = o
    elif o["task"] == "state": S[o["id"]][o["run"]] = o
    else: C[(o["id"], o["claimed"])] = o
print("== STEP 3: type check (V6) on", len(T), "keyed facts ==")
for r in (0, 1):
    hit = [i for i in T if T[i][r]["choice"] == TK[K[i]["type"]]]
    # planted: every wrong type for every fact; caught when V6's own answer differs from the wrong claim
    pl = [(i, w) for i in T for w in TYPES if w != TK[K[i]["type"]]]; caught = sum(T[i][r]["choice"] != w for i, w in pl)
    print(f"run {r}: true claim accepted {pct(len(hit), len(T))} | planted wrong type caught {pct(caught, len(pl))}")
same = sum(T[i][0]["choice"] == T[i][1]["choice"] for i in T); print("both runs give the same answer", pct(same, len(T)))
by = collections.defaultdict(lambda: [0, 0])
for i in T:
    by[K[i]["type"]][1] += 1; by[K[i]["type"]][0] += T[i][0]["choice"] == TK[K[i]["type"]]
print("by key type (run 0):", {TK[t]: pct(*by[t]) for t in by})
hc = [T[i][0]["conf"] for i in T if T[i][0]["choice"] == TK[K[i]["type"]]]; mc = [T[i][0]["conf"] for i in T if T[i][0]["choice"] != TK[K[i]["type"]]]
print(f"confidence: hits mean {statistics.mean(hc):.2f} (min {min(hc):.2f}) | misses mean {statistics.mean(mc):.2f} (n={len(mc)})" if mc else "no misses")
print("misses (either run):")
for i in T:
    a, b = T[i][0]["choice"], T[i][1]["choice"]; k = TK[K[i]["type"]]
    if a != k or b != k: print(f"  #{K[i]['n']} key={k} run0={a}({T[i][0]['conf']:.2f}) run1={b}({T[i][1]['conf']:.2f}) name={K[i]['name']!r} | {H[i]['quote'][:130]!r}")
print("\n== STEP 6: state check on", len(S), "metric facts with a clear state ==")
for r in (0, 1):
    hit = [i for i in S if S[i][r]["choice"] == K[i]["state"]]
    pl = [(i, w) for i in S for w in STATES if w != K[i]["state"]]; caught = sum(S[i][r]["choice"] != w for i, w in pl)
    print(f"re-classify run {r}: true state accepted {pct(len(hit), len(S))} | planted wrong state caught {pct(caught, len(pl))}")
tp = [i for i in S if C[(i, K[i]["state"])]["choice"] == "supports"]
pl = [(i, w) for i in S for w in STATES if w != K[i]["state"]]; caught = sum(C[(i, w)]["choice"] != "supports" for i, w in pl)
print(f"claim checker: true state accepted {pct(len(tp), len(S))} | planted wrong state caught {pct(caught, len(pl))}")
print("state misses (re-classify run 0 or run 1):")
for i in S:
    a, b = S[i][0]["choice"], S[i][1]["choice"]
    if a != K[i]["state"] or b != K[i]["state"]: print(f"  #{K[i]['n']} key={K[i]['state']} run0={a} run1={b} name={K[i]['name']!r} | {H[i]['quote'][:120]!r}")
print("claim-checker true claims rejected:", [(K[i]["n"], K[i]["state"], C[(i, K[i]['state'])]["choice"]) for i in S if C[(i, K[i]["state"])]["choice"] != "supports"])
print("claim-checker planted claims passed (missed):", [(K[i]["n"], K[i]["state"], "claimed", w) for i, w in pl if C[(i, w)]["choice"] == "supports"])
tk = collections.defaultdict(list)
for o in R: tk[o["task"]].append(o["tokens"])
print("\ntokens/call:", {t: round(statistics.mean(v)) for t, v in tk.items()}, "| cost per call $:", {t: round(statistics.mean(v) * 0.042 / 1e6, 6) for t, v in tk.items()})
