"""Cause-link pilot 2 (hard cases) on Jev: several causes (PVH allocation), negated / hedged / merely co-mentioned causes (minimal pairs made by editing a real window; SYNTHETIC),
a cause in the next sentence, and an offset. Same two arms as pilot 1 (run_cause_pilot.py). Gold = Claude's hand labels, frozen BEFORE any Jev call.
Usage: python3 run_cause_pilot2.py build|run|score"""
import json, sys, hashlib
from concurrent.futures import ThreadPoolExecutor
import run_cause_pilot as R1
W = R1.W
def mk(i, kind, window, target, menu, gold, offset=()):
    m = [dict(id=f"F{k+1}", name=n, quote=q) for k, (n, q) in enumerate(menu)]; ids = {n: f"F{k+1}" for k, (n, q) in enumerate(menu)}
    return dict(id=f"D{i:02d}", kind=kind, window=window, target=dict(name=target[0], quote=target[1]), menu=m, gold=[ids[n] for n in gold], offset=[ids[n] for n in offset])
CARGO_T = ("cargo_revenue", "Cargo revenue increased $25 million, or 12.9%, in the first quarter of 2026 from the first quarter of 2025")
SAL_T = ("salaries_wages_and_benefits", "Salaries, wages and benefits increased $452 million, or 10.7%, in the first quarter of 2026 from the first quarter of 2025")
def cargo(window, tq, yq): return dict(window=window, target=CARGO_T, menu=[("cargo_ton_miles", tq), ("cargo_yield", yq)])
def sal(window, q): return dict(window=window, target=SAL_T, menu=[("mainline_full_time_equivalent_employees", q)])
S = []
pvh = "Earnings per share increased 14% versus last year to $2.45, exceeding our earnings guidance by 30 cents. Approximately 20 cents of that is due to the favorable shifts in timing of revenue and expenses between the first and second quarter I mentioned earlier. Approximately 5 cents is due to a lower tax rate and interest expense, and the remainder is due to modest business improvement compared to expectations."
S.append(mk(0, "real: several causes (PVH, allocation)", pvh, ("eps_beat_vs_guidance", "exceeding our earnings guidance by 30 cents"),
    [("revenue_expense_timing_shift", "Approximately 20 cents of that is due to the favorable shifts in timing of revenue and expenses between the first and second quarter"), ("lower_tax_rate_and_interest_expense", "Approximately 5 cents is due to a lower tax rate and interest expense"),
     ("business_improvement_vs_expectations", "the remainder is due to modest business improvement compared to expectations"), ("eps_growth", "Earnings per share increased 14% versus last year to $2.45")],
    ["revenue_expense_timing_shift", "lower_tax_rate_and_interest_expense", "business_improvement_vs_expectations"]))
w1 = "Cargo revenue increased $25 million, or 12.9%, in the first quarter of 2026 from the first quarter of 2025, and this was not due to a 9.0% increase in cargo ton miles or a 3.6% increase in cargo yield."
S.append(mk(1, "synthetic: negated cause (cargo)", **{**cargo(w1, "a 9.0% increase in cargo ton miles", "a 3.6% increase in cargo yield"), "gold": []}))
w2 = "Cargo revenue increased $25 million, or 12.9%, in the first quarter of 2026 from the first quarter of 2025. Management has not determined whether the increase was due to a 9.0% increase in cargo ton miles or a 3.6% increase in cargo yield."
S.append(mk(2, "synthetic: hedged cause (cargo)", **{**cargo(w2, "a 9.0% increase in cargo ton miles", "a 3.6% increase in cargo yield"), "gold": []}))
w3 = "Cargo revenue increased $25 million, or 12.9%, in the first quarter of 2026 from the first quarter of 2025. Separately, cargo ton miles increased 9.0% and cargo yield increased 3.6%."
S.append(mk(3, "synthetic: co-mention, no stated cause (cargo)", **{**cargo(w3, "cargo ton miles increased 9.0%", "cargo yield increased 3.6%"), "gold": []}))
w4 = "Salaries, wages and benefits increased $452 million, or 10.7%, in the first quarter of 2026 from the first quarter of 2025, and this was not due to a 3.9% increase in mainline full-time equivalent employees."
S.append(mk(4, "synthetic: negated cause (salaries)", **{**sal(w4, "a 3.9% increase in mainline full-time equivalent employees"), "gold": []}))
w5 = "Salaries, wages and benefits increased $452 million, or 10.7%, in the first quarter of 2026 from the first quarter of 2025. It is not yet clear whether this was due to a 3.9% increase in mainline full-time equivalent employees."
S.append(mk(5, "synthetic: hedged cause (salaries)", **{**sal(w5, "a 3.9% increase in mainline full-time equivalent employees"), "gold": []}))
w6 = "Salaries, wages and benefits increased $452 million, or 10.7%, in the first quarter of 2026 from the first quarter of 2025. Mainline full-time equivalent employees increased 3.9% subsequent to the first quarter of 2025."
S.append(mk(6, "synthetic: co-mention, no stated cause (salaries)", **{**sal(w6, "Mainline full-time equivalent employees increased 3.9% subsequent to the first quarter of 2025"), "gold": []}))
prasm = W[5]["window"]
S.append(mk(7, "real: cause in the next sentence ('This increase...'), distractor", prasm, ("prasm", "PRASM increasing 6.5% compared to the first quarter of 2025"),
    [("passenger_yield", "a 5.6% increase in passenger yield"), ("passenger_load_factor", "load factor increased 0.7pts compared to the first quarter of 2025")], ["passenger_yield"]))
casm = W[3]["window"]
S.append(mk(8, "real: offset (not scored)", casm, ("total_operating_cost_per_available_seat_mile", "Our 2026 first quarter total operating cost per available seat mile (CASM) was 19.38 cents, an increase of 5.6% from 18.34 cents in the first quarter of 2025"),
    [("mainline_operating_special_items", "offset in part by a decrease in mainline operating special items, net")], [], ["mainline_operating_special_items"]))
if __name__ == "__main__":
    c = sys.argv[1]
    if c == "build":
        json.dump(S, open("cause_pilot2_items_FROZEN.json", "w"), indent=1); print("frozen", len(S), "items, sha", hashlib.sha256(open("cause_pilot2_items_FROZEN.json", "rb").read()).hexdigest()[:16])
        for it in S: print(it["id"], it["kind"], "| menu", [m["name"][:26] for m in it["menu"]], "| gold", it["gold"], "offset", it["offset"])
    elif c == "run":
        import prompts_v3 as P
        its = json.load(open("cause_pilot2_items_FROZEN.json")); jobs = [("A", it, None) for it in its] + [("B", it, m) for it in its for m in it["menu"]]
        def one(j):
            arm, it, m = j; r = P.call(R1.state(it, m), R1.q_choice(it) if arm == "A" else R1.q_pair(it, m)); return arm, it["id"], (m["id"] if m else None), r
        with ThreadPoolExecutor(8) as ex: RR = list(ex.map(one, jobs))
        json.dump(RR, open("results_cause_pilot2.json", "w"), indent=1); print("calls", len(RR), "errors", sum(1 for x in RR if "error" in x[3]), "cost $", round(sum(x[3].get("usage", {}).get("input_tokens", 0) for x in RR) * 0.042 / 1e6, 4))
    else:
        its = {it["id"]: it for it in json.load(open("cause_pilot2_items_FROZEN.json"))}; RR = json.load(open("results_cause_pilot2.json"))
        print("ARM A (one Choice)")
        for arm, i, _, r in RR:
            if arm != "A": continue
            it = its[i]; a = r["answers"]["caused_by"]; ch = a["choice"]; g = it["gold"]
            v = "offset (not scored)" if it["offset"] else ("OK" if (ch in g if g else ch == "none") else "WRONG")
            print(f"  {i} {it['kind'][:48]:48s} gold {'/'.join(g) or 'none':10s} Jev {ch:5s} conf {a['confidence']:.2f}  {v}   probs {{{', '.join(f'{k}:{x:.2f}' for k, x in a['probabilities'].items())}}}")
        print("ARM B (yes/no per pair)")
        for arm, i, fid, r in RR:
            if arm != "B": continue
            it = its[i]; a = r["answers"]["pair"]; p = a["probabilities"]["true"] if "probabilities" in a else a["noul"]; truth = fid in it["gold"]
            v = "offset (not scored)" if fid in it["offset"] else ("OK" if (p >= 0.5) == truth else "WRONG")
            print(f"  {i} {fid} {next(m['name'] for m in it['menu'] if m['id']==fid)[:38]:38s} gold {'yes' if truth else 'no ':3s} P(yes)={p:.2f}  {v}")
