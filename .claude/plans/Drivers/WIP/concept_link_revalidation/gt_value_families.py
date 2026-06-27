#!/usr/bin/env python3
"""Signal A — STRICT UNIQUE value+period anchoring → metric→concept-family GT (non-LLM).

For each GuidanceUpdate (company, slug, value, period): scale the value, find the company's facts
in the matching period, and accept ONLY if EXACTLY ONE distinct concept sits within a tight
tolerance (unique = clean; ambiguous = discarded). Aggregate across companies/instances:
  - gt_anchor[(ticker,slug)] = qname    (company-specific value-anchored truth)
  - family[slug] = {qname: support}     (the metric→family map, applied to ALL companies)

Names come from independent NL extraction (guidance label_slug); concepts come from numbers only —
non-circular, non-LLM. Reuses the 31-guidance-company cache from the prior run.
"""
import json, re, pathlib, collections
from datetime import date

CLP = pathlib.Path("/tmp/claude-1000/-home-faisal-EventMarketDB/1fc7fcb8-680c-48d0-a64c-ac3f73b686ef/scratchpad/clp")
OUT = pathlib.Path("/tmp/claude-1000/-home-faisal-EventMarketDB/1fc7fcb8-680c-48d0-a64c-ac3f73b686ef/scratchpad/clrv")

TOL = 0.015          # tight: forecast that landed within 1.5% of the actual
PERIOD_TOL = 10      # days on each boundary (52/53-week calendars)
UNIT = {"m_usd": (1e6, "money"), "thousand_usd": (1e3, "money"), "k_usd": (1e3, "money"),
        "billion_usd": (1e9, "money"), "b_usd": (1e9, "money"), "usd": (1.0, "money_or_ps"),
        "count": (1.0, "count"), "shares": (1.0, "count"), "m_shares": (1e6, "count")}
PERSHARE = re.compile(r"(^|_)(eps|dps)(_|$)|per_share|per_unit")

def pval(s):
    if s is None: return None
    s = str(s).replace(",", ""); neg = s.startswith("(") and s.endswith(")"); s = s.strip("()")
    try: v = float(s)
    except ValueError: return None
    return -v if neg else v

def _d(s):
    try: return date.fromisoformat(s)
    except (ValueError, TypeError): return None

def pper(pr):
    if not pr: return None
    m = re.match(r"(duration|instant)_(\d{4}-\d{2}-\d{2})(?:_(\d{4}-\d{2}-\d{2}))?$", pr)
    if not m: return None
    a = _d(m.group(2)); b = _d(m.group(3)) if m.group(3) else a
    return (a, b) if a and b else None

def fam_unit(unit, slug):
    if unit not in UNIT: return None, None
    mult, fam = UNIT[unit]
    if fam == "money_or_ps": fam = "pershare" if PERSHARE.search(slug or "") else "money"
    return mult, fam

def ffam(u):
    u = (u or "").lower()
    if "pershare" in u: return "pershare"
    if "usd" in u: return "money"
    if u in ("shares", "number", "pure", ""): return "count"
    return "other"

def umatch(gf, ff):
    return {"money": ff == "money", "pershare": ff == "pershare",
            "count": ff in ("count", "money")}.get(gf, False)

def main():
    guidance = json.loads((CLP / "guidance.json").read_text())
    facts_raw = json.loads((CLP / "facts.json").read_text())
    facts = {}
    for t, rows in facts_raw.items():
        out = []
        for f in rows:
            out.append({"qname": f["qname"], "v": pval(f.get("value")),
                        "p": pper(f.get("period_ref")), "uf": ffam(f.get("unit_ref"))})
        facts[t] = out
    gt_anchor = {}
    fam_votes = collections.defaultdict(collections.Counter)
    n_unique = n_ambig = n_nofact = 0
    for g in guidance:
        if (g.get("segment") or "Total") != "Total": continue
        t, slug = g.get("ticker"), g.get("slug")
        if t not in facts or not slug: continue
        mult, gf = fam_unit(g.get("unit"), slug)
        if mult is None: continue
        mid = g.get("mid")
        if mid is None: continue
        target = mid * mult
        if target == 0: continue
        gp = (_d(g["pstart"]), _d(g["pend"]))
        if not (gp[0] and gp[1]): continue
        hits = set()
        for f in facts[t]:
            if f["p"] is None or f["v"] is None: continue
            if abs((gp[0]-f["p"][0]).days) > PERIOD_TOL or abs((gp[1]-f["p"][1]).days) > PERIOD_TOL: continue
            if not umatch(gf, f["uf"]): continue
            if abs(f["v"] - target) / max(abs(target), 1e-9) <= TOL:
                hits.add(f["qname"])
        if len(hits) == 1:
            q = next(iter(hits)); n_unique += 1
            gt_anchor[f"{t}|{slug}"] = q
            fam_votes[slug][q] += 1
        elif len(hits) > 1: n_ambig += 1
        else: n_nofact += 1
    # family map: keep qnames with support >= 2 (appear for >=2 instances/companies)
    family = {}
    for slug, c in fam_votes.items():
        keep = {q: n for q, n in c.items() if n >= 2}
        if keep: family[slug] = keep
    (OUT / "gt_anchor.json").write_text(json.dumps(gt_anchor))
    (OUT / "gt_family.json").write_text(json.dumps(family))
    print(f"strict-unique anchoring: unique={n_unique} ambiguous_discarded={n_ambig} no_fact={n_nofact}")
    print(f"company-specific value-anchored GT: {len(gt_anchor)} (ticker,slug) pairs")
    print(f"metric->family map: {len(family)} slugs with support>=2")
    print("=== family map sample (slug -> {qname:support}) ===")
    for slug in sorted(family)[:30]:
        fam = {q.split(':')[-1][:34]: n for q, n in sorted(family[slug].items(), key=lambda x:-x[1])}
        print(f"  {slug:34s} {fam}")

if __name__ == "__main__":
    main()
