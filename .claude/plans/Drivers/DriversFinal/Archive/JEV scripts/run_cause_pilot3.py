"""Cause-link pilot 3 on Jev: causes that sit several sentences from the effect or are spread over several sentences (real passages from the sampled filings/transcripts,
claude_review_20260930/text_sample.json). Menus = hand-picked exact phrases from the passage (earlier-model facts do not exist for these texts). Each item is run with
a SHORT window (effect sentence + next 2) and the FULL passage, to test the 'expand once' design of fact_types.md. Gold = Claude's hand labels, frozen BEFORE any Jev call.
'ignore' = offsets / indirect causes: shown, not scored. Usage: python3 run_cause_pilot3.py build|run|score"""
import json, re, sys, hashlib
from concurrent.futures import ThreadPoolExecutor
import run_cause_pilot as R1
TS = "/home/faisal/driver_typology_audit_20260930/claude_review_20260930/text_sample.json"
SENT = re.compile(r'(?<=[.!?;])\s+(?=["“(\$A-Z0-9•●·\-])')
def sentences(kind, di, start, n):
    D = json.load(open(TS))[kind]["docs"][di]; t = D["t"] if isinstance(D["t"], str) else json.dumps(D["t"])
    paras = [p for p in re.split(r"\n\s*\n|\n", t) if p.strip()] if kind == "mdna" else [t]
    for p in paras:
        ss = [re.sub(r"\s+", " ", s).strip() for s in SENT.split(p) if len(s) >= 25]
        for i, s in enumerate(ss):
            if s.startswith(start): return ss[i:i + n]
    raise SystemExit(f"passage not found: {kind} {di} {start}")
# (id, label, kind, doc, start phrase, n sentences, effect sentence idx, target (name, phrase), facts [(name, phrase)], gold names, ignore names)
P = [
 ("E0", "pension swing: 2 causes in later sentences + distractor", "prepared", 539, "2022 earnings also included $157 million of excess capacity costs", 5, 1,
  ("other_expense_swing", "Other expense was $14 million compared to other income of $147 million in 2021"),
  [("excess_capacity_costs", "2022 earnings also included $157 million of excess capacity costs, a decrease of $60 million over 2021"), ("pension_curtailment_gain_2021", "2021 included a curtailment gain of $61 million resulting from the closure of the defined benefit plans acquired as part of the Bombardier acquisition"),
   ("pension_plan_termination_charge_2022", "in 2022, we terminated the frozen U.S. pension value plan A, which resulted in non-cash charges of $108 million")], ["pension_curtailment_gain_2021", "pension_plan_termination_charge_2022"], []),
 ("E1", "operating cash flow: 3 causes in later sentences + future-tax distractor", "ex99_8k", 621, "Cash flow from operating activities was $27.4 billion", 4, 0,
  ("operating_cash_flow", "Cash flow from operating activities was $27.4 billion, up from $15.3 billion a year ago and up from $16.6 billion a quarter ago"),
  [("higher_revenue", "higher revenue"), ("cash_collection_timing", "timing of cash collections"), ("lower_cash_taxes", "lower cash taxes"), ("expected_q2_cash_tax_increase", "We expect a substantial increase in cash taxes in the second quarter")],
  ["higher_revenue", "cash_collection_timing", "lower_cash_taxes"], []),
 ("E2", "interest expense: cause 3 sentences later, offset in between", "mdna", 29, "Interest expense increased by $2.0 million", 4, 0,
  ("interest_expense_increase", "Interest expense increased by $2.0 million during the three months ended November 30, 2022"),
  [("capitalized_interest", "Capitalized interest was $4.6 million during the three months ended November 30, 2022, compared to $1.5 million during the corresponding period"), ("third_micro_mill_construction", "construction of the Company's third micro mill in Mesa, Arizona"),
   ("long_term_debt_interest_expense_increase", "an increase in long-term debt interest expense of $3.9 million during the three months ended November 30, 2022")], ["long_term_debt_interest_expense_increase"], ["capitalized_interest", "third_micro_mill_construction"]),
 ("E3", "chain: capitalized interest <- micro mill (next sentence), debt interest as distractor", "mdna", 29, "Interest expense increased by $2.0 million", 4, 1,
  ("capitalized_interest", "Capitalized interest was $4.6 million during the three months ended November 30, 2022, compared to $1.5 million during the corresponding period"),
  [("third_micro_mill_construction", "construction of the Company's third micro mill in Mesa, Arizona"), ("long_term_debt_interest_expense_increase", "an increase in long-term debt interest expense of $3.9 million during the three months ended November 30, 2022")], ["third_micro_mill_construction"], []),
 ("E4", "revenue: one cause shared with other effects, AAV resolution is NOT a cause of revenue", "ex99_8k", 83, "Third Quarter Summary Results Revenues for the quarter increased $81 million", 3, 0,
  ("revenue_increase", "Revenues for the quarter increased $81 million or 4% compared to the same period in the prior year"),
  [("volume_ramp_up", "ramp up in volume on existing and new contracts"), ("aav_contract_termination_resolution", "the resolution of the Assault Amphibious Vehicle"), ("contract_completions", "contract completions")], ["volume_ramp_up"], ["contract_completions"]),
 ("E5", "operating margin: 2 causes (one is not in the revenue sentence)", "ex99_8k", 83, "Third Quarter Summary Results Revenues for the quarter increased $81 million", 3, 1,
  ("operating_margin_increase", "Operating income as a percentage of revenues increased from the comparable prior year period"),
  [("volume_ramp_up", "ramp up in volume on existing and new contracts"), ("aav_contract_termination_resolution", "the resolution of the Assault Amphibious Vehicle"), ("contract_completions", "contract completions")], ["volume_ramp_up", "aav_contract_termination_resolution"], ["contract_completions"]),
 ("E6", "EBITDA margin decline: 4 causes in the sentence after + share distractor", "prepared", 315, "Aftermarket revenue finished at 37%", 4, 2,
  ("adjusted_ebitda_margin", "an adjusted EBITDA margin of 27%"),
  [("aftermarket_revenue_share", "Aftermarket revenue finished at 37% of total revenue"), ("organic_volume_declines", "the flow-through on organic volume declines"), ("acquired_businesses_dilution", "the dilutive impact from recently acquired businesses"),
   ("tariff_pricing_dilution", "the dilutive impact of tariff pricing matching tariff costs one-for-one"), ("growth_investments", "continued targeted investments to drive organic growth")],
  ["organic_volume_declines", "acquired_businesses_dilution", "tariff_pricing_dilution", "growth_investments"], []),
 ("E7", "operating margin: 3 causes + 2 offsets in the next sentence", "mdna", 771, "Excluding amortization of acquisition-related intangibles, the adjusted operating margin", 3, 0,
  ("adjusted_operating_margin", "the adjusted operating margin increased to 24.4% in the first quarter of 2022 compared to 15.7% in the prior year period"),
  [("favorable_price_realization", "favorable price realization"), ("increased_volumes", "increased volumes"), ("lower_material_costs", "lower material costs"), ("non_material_cost_inflation", "increases in non-material cost inflation"), ("capacity_innovation_investments", "investments in capacity, innovation and productivity")],
  ["favorable_price_realization", "increased_volumes", "lower_material_costs"], ["non_material_cost_inflation", "capacity_innovation_investments"]),
 ("E8", "volume decline: causes in the next two sentences, one indirect, one offset", "mdna", 269, "Freight revenues from bulk shipments decreased", 4, 0,
  ("bulk_freight_volume_decline", "a 5% decline in volume"),
  [("reduced_coal_use_in_power_generation", "reduced use of coal in electricity generation"), ("low_natural_gas_prices", "low natural gas prices"), ("mild_winter_weather", "mild winter weather"), ("fertilizer_shipments_increase", "increased fertilizer shipments in the second quarter of 2024")],
  ["reduced_coal_use_in_power_generation", "mild_winter_weather"], ["low_natural_gas_prices", "fertilizer_shipments_increase"]),
]
def make():
    out = []
    for (iid, label, kind, di, start, n, eff, tgt, facts, gold, ign) in P:
        ss = sentences(kind, di, start, n)
        for wname, lo, hi in (("full", 0, len(ss)), ("short", eff, min(len(ss), eff + 3))):
            if wname == "short" and (lo, hi) == (0, len(ss)): continue
            win = " ".join(ss[lo:hi]); assert tgt[1] in win, (iid, wname, "target not in window")
            menu = [(nm, ph) for nm, ph in facts if ph in win]
            for nm, ph in facts: assert ph in " ".join(ss), (iid, nm, "phrase not in passage")
            ids = {nm: f"F{k+1}" for k, (nm, ph) in enumerate(menu)}
            out.append(dict(id=f"{iid}-{wname}", label=label, window=win, n_sentences=hi - lo, target=dict(name=tgt[0], quote=tgt[1]), menu=[dict(id=ids[nm], name=nm, quote=ph) for nm, ph in menu],
                            gold=[ids[g] for g in gold if g in ids], offset=[ids[g] for g in ign if g in ids]))
    return out
if __name__ == "__main__":
    c = sys.argv[1]
    if c == "build":
        S = make(); json.dump(S, open("cause_pilot3_items_FROZEN.json", "w"), indent=1); print("frozen", len(S), "items, sha", hashlib.sha256(open("cause_pilot3_items_FROZEN.json", "rb").read()).hexdigest()[:16])
        for it in S: print(f"{it['id']:9s} {it['n_sentences']} sent | menu {len(it['menu'])} | gold {it['gold']} ignore {it['offset']} | {it['label'][:60]}")
    elif c == "run":
        import prompts_v3 as P3
        its = json.load(open("cause_pilot3_items_FROZEN.json")); jobs = [("A", it, None) for it in its] + [("B", it, m) for it in its for m in it["menu"]]
        def one(j):
            arm, it, m = j; r = P3.call(R1.state(it, m), R1.q_choice(it) if arm == "A" else R1.q_pair(it, m)); return arm, it["id"], (m["id"] if m else None), r
        with ThreadPoolExecutor(8) as ex: RR = list(ex.map(one, jobs))
        json.dump(RR, open("results_cause_pilot3.json", "w"), indent=1); print("calls", len(RR), "errors", sum(1 for x in RR if "error" in x[3]), "cost $", round(sum(x[3].get("usage", {}).get("input_tokens", 0) for x in RR) * 0.042 / 1e6, 4))
    else:
        its = {it["id"]: it for it in json.load(open("cause_pilot3_items_FROZEN.json"))}; RR = json.load(open("results_cause_pilot3.json"))
        okA = nA = 0; print("ARM A (one Choice)")
        for arm, i, _, r in RR:
            if arm != "A": continue
            it = its[i]; a = r["answers"]["caused_by"]; ch = a["choice"]; g = it["gold"]
            ok = (ch in g) if g else (ch == "none"); ign = ch in it["offset"]; okA += ok; nA += 1
            print(f"  {i:9s} gold {'/'.join(g) or 'none':11s} Jev {ch:5s} {'OK' if ok else ('IGNORED-TYPE' if ign else 'WRONG'):12s} probs {{{', '.join(f'{k}:{x:.2f}' for k, x in sorted(a['probabilities'].items()))}}}")
        print(f"  Choice: {okA}/{nA} (any valid cause counts)")
        print("ARM B (yes/no per pair): P(yes)")
        tp = fn = fp = tn = 0; wrong = []
        for arm, i, fid, r in RR:
            if arm != "B": continue
            it = its[i]; a = r["answers"]["pair"]; p = a["probabilities"]["true"] if "probabilities" in a else a["noul"]; truth = fid in it["gold"]; nm = next(m["name"] for m in it["menu"] if m["id"] == fid)
            tag = "ignore" if fid in it["offset"] else ("OK" if (p >= 0.5) == truth else "WRONG")
            if tag != "ignore": tp += truth and p >= .5; fn += truth and p < .5; fp += (not truth) and p >= .5; tn += (not truth) and p < .5
            print(f"  {i:9s} {nm[:40]:40s} gold {'yes' if truth else 'no ':3s} P={p:.2f} {tag}")
        print(f"  Pairs scored: real links found {tp}/{tp+fn}, false links {fp}/{fp+tn} non-links")
