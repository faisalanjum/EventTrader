"""Exploratory: can Jev reproduce earlier-model fact_type labels? Pattern A (1 Choice) vs B (3-question fan-out)."""
import json, glob, random, re, os, sys, time, hashlib, collections, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

RUNS = "/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments/runs"
OUT = os.path.dirname(os.path.abspath(__file__))
PRICE = 0.042 / 1e6  # $/input token, docs.typesafe.ai/models
DRY = "--dry" in sys.argv

# ---- fixtures: unique (src, quote) with one consistent label across runs -------------
seen = collections.defaultdict(list)
for f in glob.glob(f"{RUNS}/kf-*/*.raw.json"):
    try: d = json.load(open(f))
    except Exception: continue
    if not isinstance(d, dict): continue
    for x in d.get("facts") or []:
        it = x.get("item") or {}
        if it.get("quote") and it.get("driver_name"):
            seen[(d.get("source_id"), it["quote"])].append((x["fact_type"], it["driver_name"], x.get("part_ref"), f))
rows = []
for (src, q), v in sorted(seen.items()):
    types = {t for t, *_ in v}
    if len(types) != 1: continue
    t, name, part, _ = v[0]
    if t not in ("metric", "action_event", "guidance"): continue
    rows.append(dict(src=src, quote=q, label=t, name=re.sub(r"_(guidance|surprise)$", "", name),
                     section=part, runs=len({f for *_, f in v}), agreed=len({f for *_, f in v}) >= 2))
random.seed(0)
by = collections.defaultdict(list)
for r in rows: by[r["label"]].append(r)
fix = []
for t, n in (("metric", 40), ("action_event", 40), ("guidance", 40)):
    pool = sorted(by[t], key=lambda r: (not r["agreed"], r["quote"]))
    ag = [r for r in pool if r["agreed"]]; rest = [r for r in pool if not r["agreed"]]
    random.shuffle(ag); random.shuffle(rest)
    fix += (ag + rest)[:n]
for i, r in enumerate(fix): r["id"] = i
json.dump(fix, open(f"{OUT}/fixtures.json", "w"), indent=1)
fhash = hashlib.sha256(open(f"{OUT}/fixtures.json", "rb").read()).hexdigest()[:16]
print("fixtures", collections.Counter(r["label"] for r in fix), "agreed", sum(r["agreed"] for r in fix), "hash", fhash)

# ---- prompts (wording from locked rule 1.5) -------------------------------------------
DEF = {
 "metric": "Any standing variable readable again over time: a number, cost, price, rate, count or ratio, or a qualitative condition such as weather, sentiment, policy in force, labor or brand.",
 "guidance": "The company's own forward outlook, target or forecast. Outlook verbs (expect, anticipate, target, plan to) make it guidance, never a metric state.",
 "surprise": "A company value, delivered (an actual) or promised (a company forecast), compared with an expectation held by another party (analyst consensus), or an actual compared with the company's own earlier forecast. Not a comparison with a prior-period actual, and not a new forecast compared with the company's own earlier forecast.",
 "action_event": "A discrete thing that happened: a decision, transaction, incident, approval or one-off charge.",
}
PERSIST = "Between two events, is there a standing level or severity you could re-read? Yes means metric; no means action_event."
QA = {"fact_type": {"type": "choice",
      "instructions": "What kind of fact does the quote state about the driver? " + PERSIST,
      "criteria": DEF}}
QB = {
 "surprise_kind": {"type": "choice",
   "instructions": DEF["surprise"] + " Which comparison, if any, does the quote make?",
   "criteria": {"none": "The quote makes none of these comparisons.",
                "actual_vs_consensus": "A delivered actual compared with analyst consensus or another party's expectation.",
                "actual_vs_guidance": "A delivered actual compared with the company's own earlier forecast.",
                "guidance_vs_consensus": "A company forecast compared with analyst consensus."}},
 "forward_looking": {"type": "noul",
   "instructions": "Is the quote the company's own forward outlook, target or forecast for a future period?",
   "criteria": {"true": DEF["guidance"], "false": "A statement about something that is or was, not a forecast."}},
 "standing_level": {"type": "noul",
   "instructions": "Ignoring any forecast or comparison wording, " + PERSIST[0].lower() + PERSIST[1:],
   "criteria": {"true": DEF["metric"], "false": DEF["action_event"]}},
}
CTX = "--ctx" in sys.argv
EV = "/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments/fixtures/events"
_norm = lambda t: re.sub(r"\s+", " ", t)
_txt = {}
def before(r, n=400):
    if r["src"] not in _txt:
        _txt[r["src"]] = _norm(" ".join(p["content"] for p in json.load(open(f"{EV}/{r['src']}.json"))["text_parts"]))
    T, q = _txt[r["src"]], _norm(r["quote"])
    i = T.find(q)
    if i < 0: i = T.find(q[:60])
    return None if i < 0 else T[max(0, i - n):i].strip()
def state(r):
    s = {"quote": r["quote"], "section": r["section"], "driver_name": r["name"]}
    if CTX: s["text_just_before_quote"] = r["ctx"]
    return s
if CTX:
    for r in fix: r["ctx"] = before(r)
    print("context found for", sum(r["ctx"] is not None for r in fix), "of", len(fix))
    for r in fix:
        if r["ctx"] is None: r["ctx"] = ""
if DRY:
    print(json.dumps({"state": state(fix[0]), "A": QA, "B": QB}, indent=1)); sys.exit()

# ---- calls ---------------------------------------------------------------------------
env = dict(l.strip().split("=", 1) for l in open("/home/faisal/EventMarketDB/.env") if l.startswith("TYPESAFE_API_KEY="))
KEY = env["TYPESAFE_API_KEY"].strip("'\"")
def call(r, qs):
    body = json.dumps({"state": state(r), "model": "jev-1.13.0", "questions": qs}).encode()
    for k in range(6):
        try:
            req = urllib.request.Request("https://api.typesafe.ai/v1/systemone", body,
                                         {"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
            return json.load(urllib.request.urlopen(req, timeout=60))
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(2 ** k); continue
            return {"error": f"HTTP {e.code} {e.read()[:200]}"}
        except Exception as e:
            time.sleep(1 + k)
    return {"error": "failed"}
def decide_b(a):
    if a["surprise_kind"]["choice"] != "none": return "surprise"
    if a["forward_looking"]["noul"] >= 0.5: return "guidance"   # 0.5 = placeholder, not tuned (rule 8.6)
    return "metric" if a["standing_level"]["noul"] >= 0.5 else "action_event"
with ThreadPoolExecutor(8) as ex:
    RA = list(ex.map(lambda r: call(r, QA), fix))
    RB = list(ex.map(lambda r: call(r, QB), fix))
res = []; tok = {"A": 0, "B": 0}; errs = 0
for r, a, b in zip(fix, RA, RB):
    if "error" in a or "error" in b: errs += 1; continue
    tok["A"] += a["usage"]["input_tokens"]; tok["B"] += b["usage"]["input_tokens"]
    res.append(dict(id=r["id"], label=r["label"], agreed=r["agreed"], quote=r["quote"], name=r["name"],
                    A=a["answers"]["fact_type"]["choice"], A_conf=a["answers"]["fact_type"]["confidence"],
                    A_p=a["answers"]["fact_type"]["probabilities"],
                    B=decide_b(b["answers"]), B_raw={k: (v.get("noul", v.get("choice"))) for k, v in b["answers"].items()}))
json.dump(res, open(f"{OUT}/results{'_ctx' if CTX else ''}.json", "w"), indent=1)
print("errors", errs, "scored", len(res), "input tokens", tok, "cost $%.4f" % ((tok["A"] + tok["B"]) * PRICE))
for p in "AB":
    print(f"\nPattern {p}")
    for t in ("metric", "action_event", "guidance"):
        s = [x for x in res if x["label"] == t]; ok = sum(x[p] == t for x in s)
        ag = [x for x in s if x["agreed"]]; oka = sum(x[p] == t for x in ag)
        print(f"  {t:13s} {ok}/{len(s)}   (two-run-agreed only: {oka}/{len(ag)})   picked instead:",
              dict(collections.Counter(x[p] for x in s if x[p] != t)))
    print("  overall", sum(x[p] == x["label"] for x in res), "/", len(res))
print("\nA and B disagree with each other on", sum(x["A"] != x["B"] for x in res))
