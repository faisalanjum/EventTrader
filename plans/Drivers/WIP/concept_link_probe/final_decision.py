#!/usr/bin/env python3
"""Apply the FINAL algorithm's decision = G1 family-guard + G2 nongaap-guard +
LLM-pick + adversarial-refute, then score precision/recall/abstention on the census.

Precision is reported on EMITTED (survivor) links: independently-confirmed (VA-agree or
det-agree) are proven; the rest (LLM+adversary only) are the audit set for a final panel.
"""
import json, re, pathlib, collections
from build_bundles import NEGATIVE

CLP = pathlib.Path("/tmp/claude-1000/-home-faisal-EventMarketDB/1fc7fcb8-680c-48d0-a64c-ac3f73b686ef/scratchpad/clp")
NEG = {s for v in NEGATIVE.values() for s in v}

# G1: derived/ratio/event/macro families with no exact GAAP line concept (goal-mandated abstain,
# = schema fact_type routing). NOTE: effective/tax_rate are NOT here (EffectiveIncomeTaxRate is real).
G1 = re.compile(r"(_margin$|^.*margin$|_growth|_yoy|_change$|_ratio|^roic$|^roe$|^roa$|^roce$|"
                r"^ebitda|_ebitda|^fcf$|free_cash_flow|_per_square_foot|_penetration|_mix$|"
                r"_turns$|^inventory_turns$|comparable_sales_growth|same_store_sales_growth)")
# G2: non-GAAP / adjusted figures — their value is not the GAAP concept's fact. Base metric
# carries the concept via BASE_METRIC.
G2 = re.compile(r"^(adjusted_|non_gaap_|underlying_|core_|organic_)")

def guarded(slug):
    if slug in NEG:            # events/macro/explicit-conceptless (= fact_type action_event/exogenous)
        return "G1_family" if not G2.match(slug) else "G2_nongaap"
    if G2.match(slug):
        return "G2_nongaap"
    if G1.search(slug):
        return "G1_family"
    return None

def main():
    rows = json.loads((CLP / "consolidated.json").read_text())
    bundles = json.loads((CLP / "bundles.json").read_text())
    # decision per emitted link
    survivors, dropped = [], collections.Counter()
    for r in rows:
        g = guarded(r["slug"])
        if g:
            dropped[g] += 1; continue
        if r["adv"] is False:
            dropped["adversary_refuted"] += 1; continue
        survivors.append(r)

    pos_surv = [r for r in survivors if not r["is_neg"]]
    neg_surv = [r for r in survivors if r["is_neg"]]
    confirmed = [r for r in pos_surv if r["va_agree"] or r["det_agree"]]
    audit = [r for r in pos_surv if not (r["va_agree"] or r["det_agree"])]

    print("=== FINAL DECISION (G1+G2 guard + LLM-pick + adversary-refute) ===")
    print(f"emitted links:  {len(survivors)}  (positive {len(pos_surv)}, negative {len(neg_surv)})")
    print(f"dropped:        {dict(dropped)}")
    print()
    print(f"NEGATIVE leaks after guards: {len(neg_surv)}  (target 0)")
    for r in neg_surv:
        print(f"   LEAK {r['t']}|{r['slug']} -> {r['q'].split(':')[-1]}")
    print()
    print(f"positive emitted:           {len(pos_surv)}")
    print(f"  independently confirmed:  {len(confirmed)}  (VA-agree or det-agree)")
    print(f"  audit set (LLM+adv only): {len(audit)}")
    # write the audit set for a final verification panel
    (CLP / "audit_set.json").write_text(json.dumps(
        [{"t": r["t"], "slug": r["slug"], "q": r["q"]} for r in audit]))
    # recall: universe = positive (ticker,slug) pairs that genuinely have a concept.
    # Best autonomous proxy: pairs where ANY of {emitted-confirmed, VA-strong, det} found a concept,
    # restricted to non-guarded slugs.
    pos_pairs = [(t, s) for t, b in bundles.items() for s in b["pos_slugs"] if not guarded(s)]
    emitted_pairs = {(r["t"], r["slug"]) for r in pos_surv}
    print()
    print(f"non-guarded positive pairs: {len(pos_pairs)}")
    print(f"  emitted a link:           {len(emitted_pairs)} = {len(emitted_pairs)/len(pos_pairs):.1%}")
    print(f"  curated baseline links:   195 (24.1% of all 809)")
    print()
    print("--- audit set by slug (final panel will verify these) ---")
    for slug, n in collections.Counter(r["slug"] for r in audit).most_common(40):
        ex = next(r for r in audit if r["slug"] == slug)
        print(f"  {n:2d}x {slug:38s} e.g. {ex['t']}->{ex['q'].split(':')[-1][:32]}")

if __name__ == "__main__":
    main()
