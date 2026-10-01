"""Cause-link pilot (fact_types.md 'cause links with small inputs'): windows of 3 consecutive sentences around a cause-cue sentence,
with a MENU of the earlier-model facts whose quotes sit in the window. Item = (window, target fact). Prints candidates for hand labelling."""
import json, glob, re, random, collections
EV = "/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments/fixtures/events"; RUNS = "/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments/runs"
SENT = re.compile(r'(?<=[.!?;])\s+(?=["“(\$A-Z0-9•●·\-])')
CUE = re.compile(r"\b(?:due (?:primarily |mainly |largely |partly |partially |in part |principally )?to|driven (?:primarily |mainly |largely |partly |in part |principally )?by|as a result of|attributable to|result(?:ed|ing|s)? from|because(?: of)?|offset by|caused by|owing to|primarily from|mainly from)\b", re.I)
norm = lambda t: re.sub(r"\s+", " ", t).strip()
facts = {}
for f in sorted(glob.glob(f"{RUNS}/kf-*/*.raw.json")):
    try: d = json.load(open(f))
    except Exception: continue
    if not isinstance(d, dict): continue
    for x in d.get("facts") or []:
        it = x.get("item") or {}
        if it.get("quote") and it.get("driver_name"): facts.setdefault((d["source_id"], x.get("part_ref"), norm(it["quote"])), (it["driver_name"], x["fact_type"]))
by_src = collections.defaultdict(list)
for (src, part, q), (name, ft) in facts.items(): by_src[(src, part)].append((q, name, ft))
cands = []
for (src, part), fl in by_src.items():
    try: ev = json.load(open(f"{EV}/{src}.json"))
    except Exception: continue
    text = next((p["content"] for p in ev["text_parts"] if p["part"] == part), None)
    if not text: continue
    paras = [p for p in re.split(r"\n\s*\n|\n", text) if p.strip()]
    for p in paras:
        ss = [norm(s) for s in SENT.split(p) if len(s) >= 25]
        where = {}
        for q, name, ft in fl:
            for i, s in enumerate(ss):
                if q[:60] in s: where[q] = (i, name, ft); break
        for i, s in enumerate(ss):
            if not CUE.search(s): continue
            win = ss[max(0, i - 1):i + 2]; lo = max(0, i - 1)
            menu = [(q, n, ft) for q, (j, n, ft) in where.items() if lo <= j <= i + 1]
            if 2 <= len(menu) <= 5 and sum(len(x) for x in win) <= 1300 and any(where[q][0] == i for q, _, _ in menu):
                cands.append(dict(src=src, part=part, window=" ".join(win), cue_sentence=s, menu=[dict(id=f"F{k+1}", name=n, quote=q, fact_type=ft) for k, (q, n, ft) in enumerate(menu)]))
seen = set(); uniq = []
for c in cands:
    if c["window"] not in seen: seen.add(c["window"]); uniq.append(c)
print("candidate windows:", len(uniq))
random.seed(5); random.shuffle(uniq); pick = uniq[:14]
json.dump(pick, open("cause_pilot_windows.json", "w"), indent=1)
for n, c in enumerate(pick):
    print(f"\n#{n} [{c['src']} {c['part']}]\nWINDOW: {c['window']}")
    for m in c["menu"]: print(f"   {m['id']} ({m['fact_type']}) {m['name']} :: {m['quote'][:150]}")
