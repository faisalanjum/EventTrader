"""Cause-link pilot on Jev (caused_by, menu of nearby facts). Items: windows of 3 sentences from cause_pilot_windows_all.json (earlier-model facts as the menu).
GOLD below = Claude's hand labels, frozen BEFORE any Jev call (single labeler, n=12 -> a pilot, not a measurement).
Arm A: one Choice per item: which menu fact does the text state as the cause of the effect fact, or none. Arm B: one Noul per (effect, candidate) pair.  Usage: python3 run_cause_pilot.py build|run|score"""
import json, sys, hashlib, collections
from concurrent.futures import ThreadPoolExecutor
W = json.load(open("cause_pilot_windows_all.json"))
# (window index, target fact name, gold cause names, offset names (stated as offsets, not scored as causes))
ITEMS = [
 (0, "cargo_revenue", ["cargo_ton_miles", "cargo_yield"], []),
 (1, "other_operating_revenue", ["loyalty_program_revenue"], []),
 (2, "aircraft_fuel_and_related_taxes", ["average_aircraft_fuel_price_per_gallon", "aircraft_fuel_gallons_consumed", "aircraft_fuel_price_per_gallon"], []),
 (5, "passenger_load_factor", [], []),
 (7, "salaries_wages_and_benefits", ["mainline_full_time_equivalent_employees"], []),
 (8, "interest_income", [], []),
 (11, "net_cash_provided_by_operating_activities", ["air_traffic_liability"], []),
 (16, "aircraft_fuel_expense", ["jet_fuel_market_price"], ["fuel_consumption"]),
 (17, "mro_business_expense", ["mro_business"], []),
 (18, "refinery_exchange_transaction_volume", [], []),
 (19, "refinery_revenue", [], []),
]
def items():
    out = []
    for k, (wi, tgt, gold, off) in enumerate(ITEMS):
        w = W[wi]; t = next(m for m in w["menu"] if m["name"] == tgt)
        menu = [m for m in w["menu"] if m["name"] != tgt and t["quote"][:60] not in m["quote"]]   # drop self-duplicates of the target (entries that repeat the target quote)
        out.append(dict(id=f"C{k:02d}", window=w["window"], target=t, menu=[dict(id=f"F{j+1}", **{a: b for a, b in m.items() if a in ("name", "quote")}) for j, m in enumerate(menu)],
                        gold=[m["id"] for m in [dict(id=f"F{j+1}", name=m["name"]) for j, m in enumerate(menu)] if m["name"] in gold],
                        offset=[f"F{j+1}" for j, m in enumerate(menu) if m["name"] in off]))
    return out
def q_choice(it):
    crit = {m["id"]: {"what": f"{m['name']}: \"{m['quote']}\""} for m in it["menu"]}
    crit["none"] = {"what": "The text does not state any listed fact as a cause of the effect fact.", "not_for": "A fact that is only mentioned nearby, is related, or is named in another clause without being given as the reason."}
    return {"caused_by": {"type": "choice", "instructions": {"question": "According to the text, which listed fact is stated as a cause of the effect fact?",
            "read": "`text` is a short passage. `effect_fact` is the fact to explain. Judge only what the passage itself says.",
            "order": "Choose a listed fact only when the passage says that it caused, drove or contributed to the effect fact. Otherwise choose none."}, "criteria": crit}}
def q_pair(it, m):
    return {"pair": {"type": "noul", "instructions": {"question": "Does the passage state that `cause_fact` caused, drove or contributed to `effect_fact`?", "read": "Judge only what the passage itself says."},
            "criteria": {"true": {"what": "The passage gives the cause fact as a reason for the effect fact."}, "false": {"what": "No such statement.", "not_for": "Facts that are merely mentioned together or are related."}}}}
def state(it, m=None):
    s = {"text": it["window"], "effect_fact": f"{it['target']['name']}: \"{it['target']['quote']}\""}
    if m: s["cause_fact"] = f"{m['name']}: \"{m['quote']}\""
    return s
if __name__ == "__main__":
    c = sys.argv[1]; its = items()
    if c == "build":
        json.dump(its, open("cause_pilot_items_FROZEN.json", "w"), indent=1); print("frozen", len(its), "items, sha", hashlib.sha256(open("cause_pilot_items_FROZEN.json", "rb").read()).hexdigest()[:16])
        for it in its: print(it["id"], it["target"]["name"], "| menu", [m["name"][:28] for m in it["menu"]], "| gold", it["gold"], "offset", it["offset"])
    elif c == "run":
        import prompts_v3 as P
        its = json.load(open("cause_pilot_items_FROZEN.json")); jobs = [("A", it, None) for it in its] + [("B", it, m) for it in its for m in it["menu"]]
        def one(j):
            arm, it, m = j; r = P.call(state(it, m), q_choice(it) if arm == "A" else q_pair(it, m)); return arm, it["id"], (m["id"] if m else None), r
        with ThreadPoolExecutor(8) as ex: R = list(ex.map(one, jobs))
        json.dump(R, open("results_cause_pilot.json", "w"), indent=1); print("calls", len(R), "errors", sum(1 for x in R if "error" in x[3]), "input tokens", sum(x[3].get("usage", {}).get("input_tokens", 0) for x in R), "cost $", round(sum(x[3].get("usage", {}).get("input_tokens", 0) for x in R) * 0.042 / 1e6, 4))
    else:
        its = {it["id"]: it for it in json.load(open("cause_pilot_items_FROZEN.json"))}; R = json.load(open("results_cause_pilot.json"))
        A = [x for x in R if x[0] == "A"]; ok = 0; rows = []
        for _, i, _, r in A:
            it = its[i]; a = r["answers"]["caused_by"]; ch = a["choice"]; right = (ch in it["gold"]) if it["gold"] else (ch == "none")
            ok += right; rows.append((i, it["target"]["name"][:34], "gold " + ("/".join(it["gold"]) or "none"), "Jev " + ch, f"conf {a['confidence']:.2f}", "OK" if right else ("OFFSET" if ch in it["offset"] else "WRONG")))
        pos = [i for i in its.values() if i["gold"]]; neg = [i for i in its.values() if not i["gold"]]
        print(f"ARM A (choice): {ok}/{len(A)} right  |  with a real cause: {sum(1 for r in rows if r[0] in [p['id'] for p in pos] and r[-1]=='OK')}/{len(pos)}  |  no cause (none): {sum(1 for r in rows if r[0] in [n['id'] for n in neg] and r[-1]=='OK')}/{len(neg)}")
        for r in rows: print("  ", *r)
        B = [x for x in R if x[0] == "B"]; tp = fp = fn = tn = 0; bad = []
        for _, i, fid, r in B:
            it = its[i]; p = r["answers"]["pair"]["probabilities"]["true"] if "probabilities" in r["answers"]["pair"] else r["answers"]["pair"]["noul"]; yes = p >= 0.5
            truth = fid in it["gold"]
            if fid in it["offset"]: continue
            tp += yes and truth; fp += yes and not truth; fn += (not yes) and truth; tn += (not yes) and not truth
            if yes != truth: bad.append((i, it["target"]["name"][:30], fid, "gold yes" if truth else "gold no", f"p={p:.2f}"))
        print(f"ARM B (pair yes/no): {tp+tn}/{tp+fp+fn+tn} right | real links found {tp}/{tp+fn} | false links {fp} of {fp+tn} non-links"); [print("  ", *b) for b in bad]
