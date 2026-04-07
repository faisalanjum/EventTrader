#!/usr/bin/env python3
"""
Scan ALL companies × 16 risk factors for top return strategies.
Reads embeddings from Neo4j (no OpenAI calls). Run ingest_massive_risk_factors.py first.

Score = avg_return * sqrt(count) / (stdev + 0.5)
  → Rewards: high avg return, many news, low volatility
"""

import os, sys, json, math, functools, statistics
from neo4j import GraphDatabase
from dotenv import load_dotenv
load_dotenv()
print = functools.partial(print, flush=True)

driver = GraphDatabase.driver(os.getenv("NEO4J_URI", "bolt://192.168.40.73:30687"),
    auth=(os.getenv("NEO4J_USERNAME", "neo4j"), os.getenv("NEO4J_PASSWORD")))

SIM = 0.75
NEWS_LIMIT = 100
MIN_NEWS = 3

CATS = [
    "raw_material_availability_and_cost_volatility",
    "trade_policies_tariffs_and_sanctions",
    "foreign_exchange_and_currency_exposure",
    "artificial_intelligence_and_automation",
    "data_breaches_and_cyber_attacks",
    "competitive_pressure_and_market_share_loss",
    "pandemic_and_public_health_crises",
    "natural_disasters_and_extreme_weather",
    "pricing_pressure_and_margin_compression",
    "regulatory_compliance_and_changes",
    "merger_acquisition_and_divestiture_risks",
    "labor_relations_and_union_negotiations",
    "consumer_spending_and_confidence",
    "intellectual_property_protection_and_infringement",
    "climate_change_and_environmental_impact",
    "interest_rate_and_yield_curve_risk",
]

LABELS = {
    "raw_material_availability_and_cost_volatility": "OilMtrl",
    "trade_policies_tariffs_and_sanctions": "Tariff",
    "foreign_exchange_and_currency_exposure": "FX",
    "artificial_intelligence_and_automation": "AI",
    "data_breaches_and_cyber_attacks": "Cyber",
    "competitive_pressure_and_market_share_loss": "Compete",
    "pandemic_and_public_health_crises": "Pandemic",
    "natural_disasters_and_extreme_weather": "Weather",
    "pricing_pressure_and_margin_compression": "Margin",
    "regulatory_compliance_and_changes": "Regulat",
    "merger_acquisition_and_divestiture_risks": "M&A",
    "labor_relations_and_union_negotiations": "Labor",
    "consumer_spending_and_confidence": "Consumer",
    "intellectual_property_protection_and_infringement": "IP",
    "climate_change_and_environmental_impact": "Climate",
    "interest_rate_and_yield_curve_risk": "IntRate",
}

# ============================================================
# STEP 1: Load embeddings from Neo4j (no OpenAI calls)
# ============================================================
print("Step 1: Loading risk classifications + embeddings from Neo4j...")

with driver.session() as s:
    result = s.run("""
        MATCH (rc:RiskClassification)-[:CLASSIFIED_AS]->(cat:RiskCategory)
        WHERE cat.id IN $cats AND rc.embedding IS NOT NULL
        WITH rc.ticker AS ticker, cat.id AS category, rc.embedding AS embedding, rc.filing_date AS date
        ORDER BY date DESC
        WITH ticker, category, collect(embedding)[0] AS embedding
        RETURN ticker, category, embedding
    """, cats=CATS)
    pairs = [dict(r) for r in result]

print(f"  Found {len(pairs)} company×risk pairs with embeddings across {len(set(p['ticker'] for p in pairs))} companies")

# ============================================================
# STEP 2: Vector search for each pair
# ============================================================
print(f"\nStep 2: Searching news for {len(pairs)} pairs at {SIM} threshold...")

results = []
for i, p in enumerate(pairs):
    tk = p["ticker"]
    cat = p["category"]
    emb = p["embedding"]

    with driver.session() as s:
        res = s.run("""
            CALL db.index.vector.queryNodes("news_vector_index", 500, $e)
            YIELD node, score
            WHERE score >= $th
            WITH node, score
            MATCH (node)-[r:INFLUENCES]->(c:Company {ticker: $t})
            RETURN r.daily_stock AS ds, r.daily_macro AS dm
            ORDER BY score DESC
            LIMIT $lim
        """, e=emb, th=SIM, t=tk, lim=NEWS_LIMIT)
        hits = [dict(x) for x in res]

    rets = []
    for h in hits:
        if h["ds"] is not None and h["dm"] is not None:
            rets.append(round(float(h["ds"]) - float(h["dm"]), 3))

    if len(rets) >= MIN_NEWS:
        avg = sum(rets) / len(rets)
        sd = statistics.stdev(rets) if len(rets) > 1 else 99
        mn, mx = min(rets), max(rets)
        score = avg * math.sqrt(len(rets)) / (sd + 0.5)
        results.append({
            "ticker": tk, "category": cat, "label": LABELS[cat],
            "avg": round(avg, 2), "count": len(rets), "stdev": round(sd, 2),
            "min": mn, "max": mx, "range": round(mx - mn, 2), "score": round(score, 3),
        })

    if (i + 1) % 100 == 0:
        print(f"  [{i+1}/{len(pairs)}] searched — {len(results)} valid signals so far")

print(f"\n  Total valid signals (>= {MIN_NEWS} news): {len(results)}")

# ============================================================
# STEP 3: Rank and display
# ============================================================

def show_table(title, items, n=20):
    print(f"\n{'=' * 105}")
    print(title)
    print(f"{'=' * 105}")
    print(f"  {'Rank':>4}  {'Ticker':>6} × {'Driver':<10}  {'Score':>7}  {'Avg%':>7}  {'StdDev':>7}  {'Count':>5}  {'Range':>10}")
    print(f"  {'-'*4}  {'-'*6}   {'-'*10}  {'-'*7}  {'-'*7}  {'-'*7}  {'-'*5}  {'-'*10}")
    for rank, r in enumerate(items[:n], 1):
        rng = f"[{r['min']:+.1f},{r['max']:+.1f}]"
        print(f"  {rank:>4}  {r['ticker']:>6} × {r['label']:<10}  {r['score']:>+7.2f}  {r['avg']:>+7.2f}  {r['stdev']:>7.2f}  {r['count']:>5}  {rng:>10}")

long_strats = sorted(results, key=lambda x: x["score"], reverse=True)
show_table("TOP 20 LONG STRATEGIES (buy when this driver news hits)", long_strats, 20)

short_strats = sorted(results, key=lambda x: x["score"])
show_table("TOP 20 SHORT STRATEGIES (sell when this driver news hits)", short_strats, 20)

consistent = [r for r in results if r["count"] >= 5 and abs(r["avg"]) > 0.3]
consistent.sort(key=lambda x: x["stdev"])
show_table("TOP 20 MOST CONSISTENT (low stdev, |avg| > 0.3%, min 5 news)", consistent, 20)

confident = [r for r in results if abs(r["avg"]) > 0.3]
confident.sort(key=lambda x: x["count"], reverse=True)
show_table("TOP 20 HIGHEST CONFIDENCE (most news, |avg| > 0.3%)", confident, 20)

# Summary
print(f"\n{'=' * 80}")
print("SUMMARY")
print(f"{'=' * 80}")
print(f"  Total company×risk pairs checked:  {len(pairs)}")
print(f"  Valid signals (>= {MIN_NEWS} news):       {len(results)}")
print(f"  Positive avg return:               {sum(1 for r in results if r['avg'] > 0)}")
print(f"  Negative avg return:               {sum(1 for r in results if r['avg'] < 0)}")
print(f"  Companies with any signal:         {len(set(r['ticker'] for r in results))}")
print(f"  Risk categories with any signal:   {len(set(r['category'] for r in results))}")

print(f"\n  Per-category breakdown:")
for cat in CATS:
    cat_results = [r for r in results if r["category"] == cat]
    if cat_results:
        avg_of_avgs = sum(r["avg"] for r in cat_results) / len(cat_results)
        print(f"    {LABELS[cat]:<10}  {len(cat_results):>4} signals  avg of avgs: {avg_of_avgs:>+6.2f}%")
    else:
        print(f"    {LABELS[cat]:<10}     0 signals")

# Save results
outfile = os.path.join(os.path.dirname(__file__), "massive_risk_data", "driver_strategy_results.json")
with open(outfile, "w") as f:
    json.dump({
        "threshold": SIM,
        "min_news": MIN_NEWS,
        "total_pairs": len(pairs),
        "valid_signals": len(results),
        "results": sorted(results, key=lambda x: x["score"], reverse=True),
    }, f, indent=2)
print(f"\n  Saved {len(results)} signals to {outfile}")

driver.close()
print("\nDone.")
