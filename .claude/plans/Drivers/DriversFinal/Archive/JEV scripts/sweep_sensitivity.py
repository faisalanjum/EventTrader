"""Sensitivity checks for the whole-corpus sweep estimate (JEV.md §9.1 task 9). Read-only. Needs sweep_units_sample.pkl (sweep_corpus.py units).
1. Tiny units (headings, "Okay.", cell fragments under 25 characters): how many calls would skipping them save?
2. Exact-duplicate units: within the sample, and the same company's earlier filings (10-K, 10-Q, 8-K press release) = the year-over-year repeat.
3. A finer definition: every blank-line block of a financial-statement section as its own unit (upper bound), versus our row rebuild.
Usage: /home/faisal/EventMarketDB/venv/bin/python3 sweep_sensitivity.py"""
import re, json, pickle, random, collections, statistics, sys
sys.path.insert(0, ".")
from sweep_corpus import split_units, connect, PKL
random.seed(11)
out = pickle.load(open(PKL, "rb"))

print("== 1. tiny units and 2a. duplicates inside the sample, by group")
G = collections.defaultdict(lambda: dict(calls=0.0, keep25=0.0, keep40=0.0, uniq=0.0))
for st, recs in out:
    us = [u for r in recs for u in r["units"]]
    if not us: continue
    n = len(us); c = st["est_calls"]
    g = G[st["group"]]; g["calls"] += c
    g["keep25"] += c * sum(len(u) >= 25 for u in us) / n; g["keep40"] += c * sum(len(u) >= 40 for u in us) / n
    g["uniq"] += c * len(set(us)) / n
tot = sum(g["calls"] for g in G.values())
print(f"{'group':24s} {'calls M':>8s} {'skip <25 chars':>15s} {'skip <40':>9s} {'repeat text inside the sample':>30s}")
for k, g in G.items():
    print(f"{k:24s} {g['calls']/1e6:8.2f} {100*(1-g['keep25']/g['calls']):14.1f}% {100*(1-g['keep40']/g['calls']):8.1f}% {100*(1-g['uniq']/g['calls']):29.1f}%")
print(f"{'ALL':24s} {tot/1e6:8.2f} {100*(1-sum(g['keep25'] for g in G.values())/tot):14.1f}% {100*(1-sum(g['keep40'] for g in G.values())/tot):8.1f}% {100*(1-sum(g['uniq'] for g in G.values())/tot):29.1f}%")

drv = connect()
def q(cy, **p):
    with drv.session(default_access_mode="READ") as s: return s.run(cy, **p).data()
def yr(rid):
    m = re.match(r"\d+-(\d\d)-(\d+)", rid); return (int(m.group(1)) if int(m.group(1)) < 80 else int(m.group(1)) - 100, int(m.group(2))) if m else (0, 0)

print("\n== 2b. same company, earlier filings: share of units whose exact text appeared in an EARLIER filing of the same company")
def cross(form, sec_filter, label, ncik, minn, kind="sec"):
    ciks = [r["cik"] for r in q("MATCH (r:Report {formType:$f}) WITH r.cik AS cik, count(*) AS n WHERE n>=$m WITH cik ORDER BY rand() LIMIT $k RETURN cik", f=form, m=minn, k=ncik)]
    if kind == "sec":
        rows = q(f"MATCH (r:Report {{formType:$f}})-[]->(s:ExtractedSectionContent) WHERE r.cik IN $ciks AND {sec_filter} RETURN r.cik AS cik, r.id AS rid, s.content AS text", f=form, ciks=ciks)
    else:
        rows = q("MATCH (r:Report {formType:$f})-[]->(e:ExhibitContent) WHERE r.cik IN $ciks AND e.exhibit_number='EX-99.1' RETURN r.cik AS cik, r.id AS rid, e.content AS text", f=form, ciks=ciks)
    by = collections.defaultdict(list)
    for r in rows: by[r["cik"]].append(r)
    dup = tot_ = 0
    for cik, rs in by.items():
        seen = set()
        for i, r in enumerate(sorted(rs, key=lambda r: yr(r["rid"]))):
            us = split_units(r["text"] or "")
            if i > 0: dup += sum(u in seen for u in us); tot_ += len(us)
            seen.update(us)
    print(f"   {label:38s} companies {len(by):2d}  filings {len(rows):3d}  repeated units {100*dup/max(1,tot_):5.1f}% of {tot_}")
    return dup / max(1, tot_)
cross("10-K", "s.section_name='RiskFactors'", "10-K Risk Factors", 12, 6)
cross("10-K", "s.section_name='Business'", "10-K Business", 12, 6)
cross("10-K", "s.section_name STARTS WITH 'Management'", "10-K MD&A", 12, 6)
cross("10-K", "s.section_name='FinancialStatementsandSupplementaryData'", "10-K financial statements + notes", 12, 6)
cross("10-Q", "s.section_name='RiskFactors'", "10-Q Risk Factors", 12, 10)
cross("10-Q", "s.section_name STARTS WITH 'ManagementDiscussion'", "10-Q MD&A", 12, 10)
cross("10-Q", "s.section_name='FinancialStatements'", "10-Q financial statements + notes", 12, 10)
cross("8-K", None, "8-K press release (EX-99.1)", 12, 12, kind="ex")

print("\n== 3. finer definition: every blank-line block of a financial-statement section as its own unit (upper bound)")
for form, name in (("10-Q", "FinancialStatements"), ("10-K", "FinancialStatementsandSupplementaryData")):
    rows = q("MATCH (s:ExtractedSectionContent) WHERE s.form_type=$f AND s.section_name=$n WITH s, rand() AS r ORDER BY r LIMIT 40 RETURN s.content AS text", f=form, n=name)
    blocks = sum(len([b for b in re.split(r"\n\s*\n", r["text"]) if b.strip()]) for r in rows)
    units = sum(len(split_units(r["text"])) for r in rows)
    print(f"   {form} {name[:30]:30s} blocks {blocks:6d}  our units {units:6d}  -> {blocks/units:.2f} blocks per unit")

print("\n== 4. repeats that count for caching: the WHOLE input (context before + unit + context after) identical to an earlier filing of the same company")
from sweep_corpus import make_state
def cross_ctx(form, sec_filter, label, ncik, minn, kind="sec"):
    ciks = [r["cik"] for r in q("MATCH (r:Report {formType:$f}) WITH r.cik AS cik, count(*) AS n WHERE n>=$m WITH cik ORDER BY rand() LIMIT $k RETURN cik", f=form, m=minn, k=ncik)]
    if kind == "sec":
        rows = q(f"MATCH (r:Report {{formType:$f}})-[]->(s:ExtractedSectionContent) WHERE r.cik IN $ciks AND {sec_filter} RETURN r.cik AS cik, r.id AS rid, s.content AS text", f=form, ciks=ciks)
    else:
        rows = q("MATCH (r:Report {formType:$f})-[]->(e:ExhibitContent) WHERE r.cik IN $ciks AND e.exhibit_number='EX-99.1' RETURN r.cik AS cik, r.id AS rid, e.content AS text", f=form, ciks=ciks)
    by = collections.defaultdict(list)
    for r in rows: by[r["cik"]].append(r)
    d_unit = d_ctx = n = 0
    for cik, rs in by.items():
        seen_u, seen_c = set(), set()
        for k, r in enumerate(sorted(rs, key=lambda r: yr(r["rid"]))):
            us = split_units(r["text"] or ""); keys = []
            for i in range(len(us)):
                st = make_state(us, i, "x"); keys.append((st["text_before_quote"], st["quote"], st["text_after_quote"]))
            if k > 0:
                n += len(us); d_unit += sum(u in seen_u for u in us); d_ctx += sum(kk in seen_c for kk in keys)
            seen_u.update(us); seen_c.update(keys)
    print(f"   {label:38s} companies {len(by):2d} filings {len(rows):3d} | unit text repeated {100*d_unit/max(1,n):5.1f}% | whole input repeated {100*d_ctx/max(1,n):5.1f}%  (of {n})")
cross_ctx("10-K", "s.section_name='RiskFactors'", "10-K Risk Factors", 12, 3)
cross_ctx("10-K", "s.section_name='Business'", "10-K Business", 12, 3)
cross_ctx("10-K", "s.section_name STARTS WITH 'Management'", "10-K MD&A", 12, 3)
cross_ctx("10-K", "s.section_name='FinancialStatementsandSupplementaryData'", "10-K financial statements + notes", 12, 3)
cross_ctx("10-Q", "s.section_name STARTS WITH 'ManagementDiscussion'", "10-Q MD&A", 12, 10)
cross_ctx("10-Q", "s.section_name='FinancialStatements'", "10-Q financial statements + notes", 12, 10)
cross_ctx("8-K", None, "8-K press release (EX-99.1)", 12, 12, kind="ex")
