#!/usr/bin/env python3
"""
analyze_taxonomy.py — composition of the assembled 970-row union:
  (1) subset/overlap of legacy vs modern, and (2) driver-family breakdown (company vs earnings vs macro/geo).
Run: python3 analyze_taxonomy.py   (reads bigdata_taxonomy_assembled.csv + RavenPack_categories.csv next to it)
"""
import os, csv
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
modern, legacy = [], []
for r in csv.DictReader(open(os.path.join(HERE, "bigdata_taxonomy_assembled.csv"))):
    (modern if r["kind"] == "modern" else legacy).append(
        (r["topic"], r["group"], r["type"], r["sub_type"]) if r["kind"] == "modern" else r["id_or_slug"])
plos_group = {r["category"]: (r["topic"], r["group"]) for r in csv.DictReader(open(os.path.join(HERE, "RavenPack_categories.csv")))}

FAM = {  # business-topic group -> driver family
 'earnings': 'EARNINGS/FINANCIALS', 'revenues': 'EARNINGS/FINANCIALS',
 'equity-actions': 'CAPITAL/CREDIT/PAYOUT', 'credit': 'CAPITAL/CREDIT/PAYOUT', 'credit-ratings': 'CAPITAL/CREDIT/PAYOUT',
 'bankruptcy': 'CAPITAL/CREDIT/PAYOUT', 'dividends': 'CAPITAL/CREDIT/PAYOUT', 'provisions': 'CAPITAL/CREDIT/PAYOUT',
 'acquisitions-mergers': 'M&A/OWNERSHIP', 'partnerships': 'M&A/OWNERSHIP', 'insider-trading': 'M&A/OWNERSHIP',
 'products-services': 'PRODUCTS/OPERATIONS', 'assets': 'PRODUCTS/OPERATIONS', 'business-operations': 'PRODUCTS/OPERATIONS',
 'exploration': 'PRODUCTS/OPERATIONS', 'industrial-accidents': 'PRODUCTS/OPERATIONS', 'customer-engagement': 'PRODUCTS/OPERATIONS',
 'commodity-prices': 'PRODUCTS/OPERATIONS', 'lobbying': 'PRODUCTS/OPERATIONS', 'business-activity': 'PRODUCTS/OPERATIONS', 'production': 'PRODUCTS/OPERATIONS',
 'labor-issues': 'PEOPLE/GOVERNANCE', 'regulatory': 'PEOPLE/GOVERNANCE', 'investor-relations': 'PEOPLE/GOVERNANCE', 'marketing': 'PEOPLE/GOVERNANCE',
 'analyst-ratings': 'MARKET/ANALYST', 'price-targets': 'MARKET/ANALYST', 'stock-prices': 'MARKET/ANALYST',
 'indexes': 'MARKET/ANALYST', 'technical-analysis': 'MARKET/ANALYST', 'order-imbalances': 'MARKET/ANALYST', 'stock-picks': 'MARKET/ANALYST',
 'legal': 'LEGAL/ESG/SECURITY', 'security': 'LEGAL/ESG/SECURITY', 'corporate-responsibility': 'LEGAL/ESG/SECURITY',
 'social-responsibility': 'LEGAL/ESG/SECURITY', 'reputation': 'LEGAL/ESG/SECURITY', 'sanctions': 'LEGAL/ESG/SECURITY',
 'censorship': 'LEGAL/ESG/SECURITY', 'aid': 'LEGAL/ESG/SECURITY', 'transportation': 'LEGAL/ESG/SECURITY',
 'health': 'LEGAL/ESG/SECURITY', 'crime': 'LEGAL/ESG/SECURITY', 'civil-unrest': 'LEGAL/ESG/SECURITY',
 'cyber-security': 'LEGAL/ESG/SECURITY', 'public-opinion': 'LEGAL/ESG/SECURITY',
}
def family(t, g):
    if t == 'economy': return 'MACRO/ECONOMY'
    if t == 'politics': return 'POLITICS/GEO'
    if t == 'environment': return 'ENVIRONMENT'
    if t == 'society' and g == 'war-conflict': return 'POLITICS/GEO'
    return FAM.get(g, 'OTHER:' + g)

print(f"UNION {len(modern)+len(legacy)}: modern={len(modern)} (current Bigdata) + legacy={len(legacy)} (RPA 1.0 naming)\n")
print("MODERN by TOPIC:", dict(Counter(t for t, g, ty, st in modern).most_common()))
print("\nMODERN by DRIVER FAMILY:")
for f, n in Counter(family(t, g) for t, g, ty, st in modern).most_common():
    print(f"  {f:22s} {n:4d}  ({100*n/len(modern):.0f}%)")
print("\nLEGACY (381 PLOS) by DRIVER FAMILY:")
for f, n in Counter(family(t, g) for cat, (t, g) in plos_group.items()).most_common():
    print(f"  {f:22s} {n:4d}")
mg = {g for t, g, ty, st in modern}; lg = {g for c, (t, g) in plos_group.items()}
print(f"\nOVERLAP: legacy {len(lg)} groups, {len(lg & mg)} also in modern; modern adds {len(mg - lg)} macro/geo/ESG groups legacy lacked.")
