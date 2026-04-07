#!/usr/bin/env python3
"""
Clean 16×16 driver matrix — numpy-accelerated.
Loads all embeddings + news into memory, computes cosine similarity via matmul.
17 Neo4j queries total (1 for risks + 16 for news) instead of 256 vector searches.
"""
import os, sys, time, functools
import numpy as np
from neo4j import GraphDatabase
from dotenv import load_dotenv
load_dotenv()
print = functools.partial(print, flush=True)

driver = GraphDatabase.driver(os.getenv("NEO4J_URI","bolt://192.168.40.73:30687"),
    auth=(os.getenv("NEO4J_USERNAME","neo4j"), os.getenv("NEO4J_PASSWORD")))

NEO4J_SIM = 0.75                          # threshold in Neo4j score space
SIM = 2 * NEO4J_SIM - 1                   # convert to raw cosine for numpy (0.75 → 0.50)

CATS = ["raw_material_availability_and_cost_volatility","trade_policies_tariffs_and_sanctions",
"foreign_exchange_and_currency_exposure","artificial_intelligence_and_automation",
"data_breaches_and_cyber_attacks","competitive_pressure_and_market_share_loss",
"pandemic_and_public_health_crises","natural_disasters_and_extreme_weather",
"pricing_pressure_and_margin_compression","regulatory_compliance_and_changes",
"merger_acquisition_and_divestiture_risks","labor_relations_and_union_negotiations",
"consumer_spending_and_confidence","intellectual_property_protection_and_infringement",
"climate_change_and_environmental_impact","interest_rate_and_yield_curve_risk"]

L = ["OilMtl","Tariff","   FX ","   AI ","Cyber","Compet","Pandem","Weathr",
     "Margin","Regul ","  M&A ","Labor ","Consum","  IP  ","Climat","IntRat"]

T = ["AAPL","TSLA","AMZN","DAL","OXY","NKE","COST","UPS",
     "LLY","DIS","CAT","PBF","AAL","EQR","CRM","CMG"]

t0 = time.time()

# ============================================================
# STEP 1: Load ALL risk embeddings in ONE query
# ============================================================
print("Loading risk embeddings...", end=" ")
risk_embs = {}  # (ticker, category) -> np.array

with driver.session() as s:
    result = s.run("""
        MATCH (rc:RiskClassification)-[:CLASSIFIED_AS]->(cat:RiskCategory)
        WHERE rc.ticker IN $tickers AND cat.id IN $cats AND rc.embedding IS NOT NULL
        WITH rc.ticker AS ticker, cat.id AS category, rc.embedding AS emb, rc.filing_date AS date
        ORDER BY date DESC
        WITH ticker, category, collect(emb)[0] AS emb
        RETURN ticker, category, emb
    """, tickers=T, cats=CATS)
    for r in result:
        risk_embs[(r["ticker"], r["category"])] = np.array(r["emb"], dtype=np.float64)

# Track which are disclosed (even if no embedding)
disclosed = set()
with driver.session() as s:
    result = s.run("""
        MATCH (rc:RiskClassification)-[:CLASSIFIED_AS]->(cat:RiskCategory)
        WHERE rc.ticker IN $tickers AND cat.id IN $cats
        RETURN DISTINCT rc.ticker AS ticker, cat.id AS category
    """, tickers=T, cats=CATS)
    for r in result:
        disclosed.add((r["ticker"], r["category"]))

print(f"{len(risk_embs)} embeddings, {len(disclosed)} disclosed pairs [{time.time()-t0:.1f}s]")

# ============================================================
# STEP 2: Per company — load news embeddings + returns, numpy matmul
# ============================================================
data = {}  # (ticker, category) -> {d, n, avg, mn, mx}

for ci, tk in enumerate(T):
    t1 = time.time()

    # Get this company's risk categories
    tk_cats = [cat for cat in CATS if (tk, cat) in risk_embs]
    if not tk_cats:
        # Mark all as not-disclosed or no-embedding
        for cat in CATS:
            data[(tk,cat)] = {"d": (tk,cat) in disclosed, "n":0, "avg":None, "mn":None, "mx":None}
        print(f"  [{ci+1}/{len(T)}] {tk}: no embeddings, skipped [{time.time()-t0:.1f}s]")
        continue

    # Load ALL news for this company with embeddings + returns
    with driver.session() as s:
        result = s.run("""
            MATCH (n:News)-[r:INFLUENCES]->(c:Company {ticker: $tk})
            WHERE n.embedding IS NOT NULL
            RETURN n.embedding AS emb, r.daily_stock AS ds, r.daily_macro AS dm
        """, tk=tk)
        news_raw = [dict(r) for r in result]

    if not news_raw:
        for cat in CATS:
            data[(tk,cat)] = {"d": (tk,cat) in disclosed, "n":0, "avg":None, "mn":None, "mx":None}
        print(f"  [{ci+1}/{len(T)}] {tk}: no news, skipped [{time.time()-t0:.1f}s]")
        continue

    # Build numpy arrays
    news_emb_matrix = np.array([n["emb"] for n in news_raw], dtype=np.float64)  # (N, 3072)
    news_returns = []
    for n in news_raw:
        if n["ds"] is not None and n["dm"] is not None:
            news_returns.append(round(float(n["ds"]) - float(n["dm"]), 3))
        else:
            news_returns.append(None)

    # Build risk embedding matrix for this company's categories
    risk_cat_list = tk_cats
    risk_emb_matrix = np.array([risk_embs[(tk, cat)] for cat in risk_cat_list], dtype=np.float64)  # (K, 3072)

    # Normalize for cosine similarity
    risk_norm = risk_emb_matrix / np.linalg.norm(risk_emb_matrix, axis=1, keepdims=True)
    news_norm = news_emb_matrix / np.linalg.norm(news_emb_matrix, axis=1, keepdims=True)

    # Cosine similarity: (K risks × N news)
    sim_matrix = risk_norm @ news_norm.T  # single matmul — the fast part

    # Aggregate per risk category
    for k, cat in enumerate(risk_cat_list):
        mask = sim_matrix[k] >= SIM
        matched_indices = np.where(mask)[0]

        rets = [news_returns[j] for j in matched_indices if news_returns[j] is not None]

        if rets:
            data[(tk,cat)] = {"d":True, "n":len(rets), "avg":round(sum(rets)/len(rets),1),
                              "mn":min(rets), "mx":max(rets)}
        else:
            data[(tk,cat)] = {"d":True, "n":0, "avg":None, "mn":None, "mx":None}

    # Fill non-disclosed categories
    for cat in CATS:
        if (tk, cat) not in data:
            data[(tk,cat)] = {"d": (tk,cat) in disclosed, "n":0, "avg":None, "mn":None, "mx":None}

    n_news = len(news_raw)
    n_match = sum(1 for cat in CATS if data[(tk,cat)]["n"] > 0)
    print(f"  [{ci+1}/{len(T)}] {tk}: {n_news} news × {len(tk_cats)} risks → {n_match} with matches [{time.time()-t0:.1f}s]")

total_time = time.time() - t0
print(f"\nTotal compute time: {total_time:.1f}s\n")

# ============================================================
# DISPLAY MATRICES
# ============================================================
W = 7

def sep():
    print("      +" + (("-" * W + "+") * 16))

def header():
    print("      |", end="")
    for l in L:
        print(f"{l:^{W}}|", end="")
    print()
    sep()

print("MATRIX 1: AVG MARKET-ADJUSTED RETURN (%)")
print("— = not disclosed   · = disclosed, no news match")
print()
header()
for tk in T:
    print(f"  {tk:>4}|", end="")
    for cat in CATS:
        c = data[(tk,cat)]
        if not c["d"]:
            val = "  —  "
        elif c["n"] == 0:
            val = "  ·  "
        else:
            val = f"{c['avg']:>+5.1f}"
        print(f"{val:^{W}}|", end="")
    print()
sep()

print()
print("MATRIX 2: NEWS COUNT")
print("— = not disclosed   · = 0 news")
print()
header()
for tk in T:
    print(f"  {tk:>4}|", end="")
    for cat in CATS:
        c = data[(tk,cat)]
        if not c["d"]:
            val = "  —  "
        elif c["n"] == 0:
            val = "  ·  "
        else:
            val = f"{c['n']:>4} "
        print(f"{val:^{W}}|", end="")
    print()
sep()

W3 = 10
def sep3():
    print("      +" + (("-" * W3 + "+") * 16))

def header3():
    print("      |", end="")
    for l in L:
        print(f"{l:^{W3}}|", end="")
    print()
    sep3()

print()
print("MATRIX 3: RETURN RANGE [min, max]%")
print("— = not disclosed   · = <3 news (unreliable)")
print()
header3()
for tk in T:
    print(f"  {tk:>4}|", end="")
    for cat in CATS:
        c = data[(tk,cat)]
        if not c["d"]:
            val = "    —     "
        elif c["n"] < 3:
            val = "    ·     "
        else:
            val = f"{c['mn']:>+4.0f},{c['mx']:>+4.0f}"
        print(f"{val:^{W3}}|", end="")
    print()
sep3()

driver.close()
print(f"\nDone in {time.time()-t0:.1f}s total.")
