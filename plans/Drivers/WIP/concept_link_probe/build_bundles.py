#!/usr/bin/env python3
"""Build per-company bundles for the LLM-pick matcher + the conceptless NEGATIVE set.

bundles.json = { ticker: {menu:[{qname,label,usage}], pos_slugs:[...], neg_slugs:[...]} }
  pos_slugs = the company's real guidance slugs (segment=Total)   → should mostly LINK
  neg_slugs = conceptless drivers                                 → MUST abstain (NONE)

Inference is value-withheld: the matcher sees only slugs + menu, never the number.
"""
import json, pathlib, collections
from matchers import build_menus

CLP = pathlib.Path("/tmp/claude-1000/-home-faisal-EventMarketDB/1fc7fcb8-680c-48d0-a64c-ac3f73b686ef/scratchpad/clp")

# Conceptless drivers — genuinely have NO exact us-gaap line concept. Matcher MUST abstain.
NEGATIVE = {
    "action_event": [
        "ceo_resignation", "acquisition_announcement", "share_buyback_authorization",
        "dividend_initiation", "stock_split", "credit_rating_downgrade",
        "litigation_settlement", "product_recall", "data_breach", "plant_closure",
        "labor_strike", "fda_approval", "contract_award", "debt_refinancing",
    ],
    "macro_exogenous": [
        "oil_price", "natural_gas_price", "interest_rates", "foreign_exchange_impact",
        "commodity_costs", "inflation", "tariffs", "weather_impact", "freight_costs",
    ],
    "derived_ratio": [
        "ebitda", "adjusted_ebitda", "free_cash_flow", "fcf", "operating_margin",
        "gross_margin", "net_margin", "ebitda_margin", "return_on_equity",
    ],
    "growth_change": [
        "revenue_growth", "eps_growth", "same_store_sales_growth", "revenue_yoy",
        "margin_change", "operating_income_growth",
    ],
}

def main():
    menus = build_menus()
    guidance = json.loads((CLP / "guidance.json").read_text())
    pos = collections.defaultdict(set)
    for g in guidance:
        if (g.get("segment") or "Total") == "Total" and g.get("ticker") in menus and g.get("slug"):
            pos[g["ticker"]].add(g["slug"])
    neg_all = sorted({s for v in NEGATIVE.values() for s in v})
    bundles = {}
    for t, menu in menus.items():
        bundles[t] = {
            "ticker": t,
            "menu": sorted(menu, key=lambda c: -c["usage"]),
            "pos_slugs": sorted(pos.get(t, [])),
            "neg_slugs": neg_all,
        }
    (CLP / "bundles.json").write_text(json.dumps(bundles))
    (CLP / "negative_set.json").write_text(json.dumps(NEGATIVE, indent=2))
    npos = sum(len(b["pos_slugs"]) for b in bundles.values())
    print(f"bundles: {len(bundles)} companies")
    print(f"  pos_slugs total: {npos} (avg {npos/len(bundles):.1f}/co)")
    print(f"  neg_slugs: {len(neg_all)} conceptless drivers x {len(bundles)} companies = {len(neg_all)*len(bundles)} abstention tests")
    print(f"  menu sizes: min {min(len(b['menu']) for b in bundles.values())} "
          f"max {max(len(b['menu']) for b in bundles.values())}")

if __name__ == "__main__":
    main()
