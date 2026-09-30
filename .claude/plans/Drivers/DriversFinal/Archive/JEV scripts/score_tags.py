"""Score the tag recall test (JEV.md §9). Flag rules, all computed offline from the stored probabilities:
  R1(t): any of the four type tags >= t          R2(t): R1(t) and is_boilerplate < 0.5          OLD: is_fact >= 0.5 or kind != none (the set I used for the sweep estimate)
Recall on the POSITIVES (known facts) and on the background units labeled F; false-positive rate on background units labeled N; corpus flagged share =
background flagged rates weighted by each source group's estimated call count (sweep_units_stats.json). Usage: python3 score_tags.py [--misses VARIANT]"""
import json, sys, collections, math
R = json.load(open("results_tags.json")); M = json.load(open("results_tags_meta.json")); lab = json.load(open("tag_labels.json"))["labels"]
TY = ["states_metric", "states_guidance", "states_surprise", "states_action_event"]
stats = json.load(open("sweep_units_stats.json")); W = collections.defaultdict(float)
for s in stats:
    if s["group"] != "news titles": W[s["group"]] += s["est_calls"]
Wt = sum(W.values())
def p(v, i): return R[i][v]
def flag(v, i, t, rule):
    d = R[i][v]
    if v == "B0": return d["is_fact"] >= t or d["kind"] != "none"
    f = max(d[q] for q in TY) >= t
    return f and d["is_boilerplate"] < 0.5 if rule == "R2" else f
pos = [i for i, m in M.items() if m["kind"] == "pos" and m["type"] in ("metric", "guidance", "action_event", "surprise", "mixed")]
bg = [i for i, m in M.items() if m["kind"] == "bg"]
bgF = [i for i in bg if M[i]["type"] == "F"]; bgN = [i for i in bg if M[i]["type"] == "N"]; bgU = [i for i in bg if M[i]["type"] == "U"]
def wilson(k, n):
    if n == 0: return (0, 0)
    z = 1.96; ph = k / n; d = 1 + z * z / n; c = ph + z * z / (2 * n); a = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n))
    return ((c - a) / d, (c + a) / d)
def rate(v, ids, t, rule): return sum(flag(v, i, t, rule) for i in ids)
def corpus_flag(v, t, rule):
    tot = 0.0
    for g, w in W.items():
        ids = [i for i in bg if M[i]["set"] == g]
        tot += w * sum(flag(v, i, t, rule) for i in ids) / len(ids)
    return tot / Wt
def line(v, t, rule):
    a = rate(v, pos, t, rule); f = rate(v, bgF, t, rule); n = rate(v, bgN, t, rule); u = rate(v, bgU, t, rule)
    lo, hi = wilson(a, len(pos))
    return f"recall known facts {100*a/len(pos):5.1f}% [{100*lo:.1f}-{100*hi:.1f}] ({a}/{len(pos)}) | random facts {f:2d}/{len(bgF)} | non-facts flagged {n:2d}/{len(bgN)} ({100*n/len(bgN):3.0f}%) | unclear flagged {u}/{len(bgU)} | corpus flagged share {100*corpus_flag(v,t,rule):3.0f}%"
print("== 1. operating point t = 0.5")
for v in ("B0", "P", "C", "S"):
    print(f"{v:3s} {'old rule ' if v=='B0' else 'R1       '}{line(v, 0.5, 'R1')}")
    if v != "B0": print(f"{v:3s} R2       {line(v, 0.5, 'R2')}")
print("\n== 2. threshold sweep (R1 = any type tag >= t)")
for v in ("P", "C", "S"):
    for t in (0.1, 0.2, 0.3, 0.5, 0.7, 0.9):
        print(f"{v:3s} t={t:.1f}  {line(v, t, 'R1')}")
    print()
print("== 3. recall of the known facts by type at t=0.5 (any tag / the matching tag)")
own = {"metric": "states_metric", "guidance": "states_guidance", "action_event": "states_action_event", "surprise": "states_surprise"}
for v in ("P", "C", "S"):
    row = []
    for ty in ("metric", "guidance", "action_event", "surprise", "mixed"):
        ids = [i for i in pos if M[i]["type"] == ty]
        anyt = sum(flag(v, i, 0.5, "R1") for i in ids); mt = sum(R[i][v][own[ty]] >= 0.5 for i in ids) if ty in own else None
        row.append(f"{ty} {anyt}/{len(ids)}" + (f" (own tag {mt})" if mt is not None else ""))
    print(f"{v:3s} " + " | ".join(row))
print("\n== 4. the surprise tag: known surprise claims vs the look-alike controls of the surprise test (t=0.5)")
S_pos = [i for i in pos if M[i]["type"] == "surprise"]; ctrl = [i for i, m in M.items() if m["set"] == "surprise-test" and m["type"] in ("guidance", "metric", "action_event", "not_surprise")]
for v in ("P", "C", "S"):
    tp = sum(R[i][v]["states_surprise"] >= 0.5 for i in S_pos); fp = sum(R[i][v]["states_surprise"] >= 0.5 for i in ctrl)
    print(f"{v:3s} surprise claims flagged {tp}/{len(S_pos)} | controls flagged {fp}/{len(ctrl)}")
print("    old set: vs_expectation>=0.5  claims", sum(R[i]["B0"]["vs_expectation"] >= 0.5 for i in S_pos), f"/{len(S_pos)} | controls", sum(R[i]["B0"]["vs_expectation"] >= 0.5 for i in ctrl), f"/{len(ctrl)}")
print("\n== 5. random background units by source group: flagged share at t=0.5, variant S, R1 (n=15 each; labels F/N/U in brackets)")
for g in W:
    ids = [i for i in bg if M[i]["set"] == g]; c = collections.Counter(M[i]["type"] for i in ids)
    print(f"  {g:24s} labels F{c['F']} N{c['N']} U{c['U']} | flagged {sum(flag('S', i, 0.5, 'R1') for i in ids):2d}/15 (old rule {sum(flag('B0', i, 0.5, 'R1') for i in ids)}/15) | facts flagged {sum(flag('S', i, 0.5, 'R1') for i in ids if M[i]['type']=='F')}/{c['F']}")
if "--misses" in sys.argv:
    v = sys.argv[sys.argv.index("--misses") + 1]; pos_items = {p["id"]: p for p in json.load(open("items_tags_pos.json"))}
    print(f"\n######## known facts NOT flagged by {v} R1 t=0.5")
    for i in pos:
        if not flag(v, i, 0.5, "R1"):
            st = pos_items[i]["state"]; d = R[i][v]
            print(f"\n[{i}] type={M[i]['type']} | " + " ".join(f"{q[7:12]}={d[q]:.2f}" for q in TY) + f" bp={d['is_boilerplate']:.2f}\n   Q: {st['quote'][:230]!r}\n   before: …{st['text_before_quote'][-110:]!r}")
