#!/usr/bin/env python3
"""Build the probe set (inputs) across all 4 fact_types, with INDEPENDENT GT, for every company.

Pre-applies the EXACT deterministic guard() from concept_linker (faithful: guarded slugs abstain
before the LLM). Writes per-company agent input (non-guarded metrics + menu) and the GT for scoring.
"""
import json, sys, pathlib, collections
sys.path.insert(0, "plans/Drivers/WIP/concept_link_probe")          # algorithm under test (read-only)
sys.path.insert(0, ".claude/plans/Drivers/WIP/concept_link_revalidation")
from concept_linker import guard
from gt_build import CANON

CLRV = pathlib.Path("/tmp/claude-1000/-home-faisal-EventMarketDB/1fc7fcb8-680c-48d0-a64c-ac3f73b686ef/scratchpad/clrv")

CORE = ["revenue","net_sales","cost_of_revenue","gross_profit","operating_income","net_income",
        "sg_a","r_d","operating_expenses","interest_expense","income_tax_expense","d_a","eps",
        "basic_eps","operating_cash_flow","capex","cash","total_assets","total_debt",
        "stockholders_equity","inventory","diluted_share_count","basic_share_count",
        "shares_outstanding","dividend_per_share","restructuring_charges","stock_based_compensation"]
# fact_type variants: GT = base metric family (test base-strip / inheritance)
VARIANTS = {f"{b}_guidance": b for b in ["revenue","eps","capex","operating_income","net_income"]}
VARIANTS.update({f"{b}_surprise": b for b in ["revenue","eps","net_income"]})
CONCEPTLESS = {
  "ratio":  ["gross_margin","operating_margin","net_margin","ebitda_margin","ebitda","adjusted_ebitda",
             "free_cash_flow","fcf","roic","return_on_equity","revenue_growth","eps_growth","margin_change"],
  "event":  ["ceo_resignation","share_buyback_authorization","acquisition_announcement","product_recall",
             "litigation_settlement","stock_split","dividend_initiation","credit_rating_downgrade",
             "plant_closure","labor_strike","data_breach"],
  "macro":  ["oil_price","natural_gas_price","interest_rates","foreign_exchange_impact","inflation",
             "tariffs","commodity_costs"],
  "nongaap":["adjusted_eps","non_gaap_net_income","adjusted_operating_income","core_earnings"],
  "kpi":    ["market_share","foot_traffic","brand_awareness","net_promoter_score","app_downloads"],
}

def base_of(slug):
    return VARIANTS.get(slug, slug)

def gt_family_for(menu_qnames, metric):
    base = base_of(metric)
    locals_ = CANON.get(base, ([],None,None))[0]
    return [q for q in menu_qnames if (q.split(":",1)[1] if ":" in q else q) in locals_]

def main():
    (CLRV/"probe").mkdir(exist_ok=True)
    gt_out = {}
    pcounts = collections.Counter()
    nmenus = 0
    for f in (CLRV/"menus").glob("*.json"):
        t = f.stem
        rows = json.loads(f.read_text())
        if not rows: continue
        nmenus += 1
        menu = [{"qname": r["qname"], "label": r.get("label"), "usage": r.get("usage")} for r in rows]
        qset = {r["qname"] for r in rows}
        agent_metrics = []
        # core + variants → may LINK; conceptless → abstain
        probe_items = [(m,"core") for m in CORE] + [(m,"variant") for m in VARIANTS] \
                    + [(m,cat) for cat,ms in CONCEPTLESS.items() for m in ms]
        for slug, cat in probe_items:
            g = guard(slug)
            if cat in ("core","variant"):
                fam = gt_family_for(qset, slug)
                gt_type = "link" if fam else "abstain"   # abstain if company doesn't report it
                gt_out[f"{t}|{slug}"] = {"cat": cat, "gt_type": gt_type, "gt_family": fam,
                                         "guarded": g, "base": base_of(slug)}
                if g is None:
                    agent_metrics.append(slug)          # core/variant should never be guarded
            else:
                gt_out[f"{t}|{slug}"] = {"cat": cat, "gt_type": "abstain", "gt_family": [],
                                         "guarded": g, "base": slug}
                if g is None:
                    agent_metrics.append(slug)          # non-guarded conceptless (KPI) → LLM must abstain
            pcounts[cat] += 1
        (CLRV/"probe"/f"{t}.json").write_text(json.dumps(
            {"ticker": t, "menu": menu, "metrics": sorted(set(agent_metrics))}))
    (CLRV/"probe_gt.json").write_text(json.dumps(gt_out))
    print(f"probe set built for {nmenus} companies")
    print(f"GT cells: {len(gt_out)}  by category: {dict(pcounts)}")
    # how many guarded vs sent to LLM
    guarded = sum(1 for v in gt_out.values() if v["guarded"])
    print(f"guarded (abstain w/o LLM): {guarded}  ; sent to LLM: {len(gt_out)-guarded}")
    # link-GT availability (core/variant with family in menu)
    linkable = sum(1 for v in gt_out.values() if v["gt_type"]=="link")
    print(f"core/variant cells where company reports the concept (GT=link): {linkable}")

if __name__ == "__main__":
    main()
