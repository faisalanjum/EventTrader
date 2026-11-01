#!/usr/bin/env python3
"""Value-anchored labeler — the autonomous answer key.

Idea (zero human labels): a GuidanceUpdate carries (company, label_slug, value,
period, unit). Its TRUE concept = the company's reported XBRL Fact whose
value+period match. Uniqueness margin guarantees the per-instance anchor is the
right concept; cross-instance mode voting washes out forecast-vs-actual noise.

Naturally abstains on ratios/percent/growth (no absolute Fact to match) — which
is exactly the correct abstention set.

Output: oracle = {(ticker, slug) -> qname} with confidence, + per-instance log.
"""
import json, re, pathlib, collections
from datetime import date

CLP = pathlib.Path("/tmp/claude-1000/-home-faisal-EventMarketDB/1fc7fcb8-680c-48d0-a64c-ac3f73b686ef/scratchpad/clp")

# guidance canonical_unit -> multiplier to reach full reported magnitude, and unit family.
# family: 'money' (usd-like), 'pershare', 'count', or None (not anchorable: ratios/deltas).
UNIT = {
    "m_usd": (1e6, "money"), "thousand_usd": (1e3, "money"), "k_usd": (1e3, "money"),
    "billion_usd": (1e9, "money"), "b_usd": (1e9, "money"), "usd": (1.0, "money_or_pershare"),
    "count": (1.0, "count"), "shares": (1.0, "count"), "m_shares": (1e6, "count"),
}
# Everything else (percent, percent_yoy, percent_points, basis_points, ratio, x,
# days, unknown, None) → not anchorable → labeler stays silent (correct abstention).

PERSHARE_HINT = re.compile(r"(^|_)(eps|dps)(_|$)|per_share|per_unit")

def parse_value(s):
    if s is None: return None
    s = str(s).strip().replace(",", "")
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v

def parse_period_ref(pr):
    """'duration_2024-02-04_2025-02-01' -> (start,end); 'instant_2022-01-01' -> (d,d)."""
    if not pr: return None
    m = re.match(r"(duration|instant)_(\d{4}-\d{2}-\d{2})(?:_(\d{4}-\d{2}-\d{2}))?$", pr)
    if not m: return None
    a = _d(m.group(2)); b = _d(m.group(3)) if m.group(3) else a
    return (a, b) if a and b else None

def _d(s):
    try: return date.fromisoformat(s)
    except (ValueError, TypeError): return None

def fact_unit_family(unit_ref):
    u = (unit_ref or "").lower()
    if "pershare" in u: return "pershare"
    if "usd" in u: return "money"
    if u in ("shares", "number", "pure", ""): return "count"
    return "other"

def unit_match(guidance_family, fact_family):
    if guidance_family == "money": return fact_family == "money"
    if guidance_family == "pershare": return fact_family == "pershare"
    if guidance_family == "count": return fact_family in ("count", "money")  # shares sometimes tagged usd-ish
    if guidance_family == "money_or_pershare": return fact_family in ("money", "pershare")
    return False

def guidance_unit_family(unit, slug):
    if unit not in UNIT: return None, None
    mult, fam = UNIT[unit]
    if fam == "money_or_pershare":
        fam = "pershare" if PERSHARE_HINT.search(slug or "") else "money"
    return mult, fam

def periods_align(gp, fp, tol_days=10):
    (gs, ge), (fs, fe) = gp, fp
    return abs((gs - fs).days) <= tol_days and abs((ge - fe).days) <= tol_days

def anchor_one(g, facts, value_tol=0.06, margin=4.0):
    """Return (qname, detail) if g uniquely anchors to one concept, else (None, reason)."""
    mult, fam = guidance_unit_family(g.get("unit"), g.get("slug"))
    if mult is None:
        return None, "unit_not_anchorable"
    mid = g.get("mid")
    if mid is None:
        mid = g.get("low") if g.get("high") is None else (
            ((g["low"] or 0) + (g["high"] or 0)) / 2 if g.get("low") is not None else None)
    if mid is None:
        return None, "no_value"
    target = mid * mult
    if target == 0:
        return None, "zero_target"
    gp = (_d(g["pstart"]), _d(g["pend"]))
    if not (gp[0] and gp[1]):
        return None, "no_period"
    # candidate facts: period aligned + unit family compatible
    cands = []
    for f in facts:
        fp = f["_period"]
        if fp is None or not periods_align(gp, fp): continue
        if not unit_match(fam, f["_ufam"]): continue
        fv = f["_val"]
        if fv is None: continue
        rel = abs(fv - target) / max(abs(target), 1e-9)
        cands.append((rel, f["qname"], fv))
    if not cands:
        return None, "no_fact_in_period"
    cands.sort()
    best_rel, best_q, best_v = cands[0]
    if best_rel > value_tol:
        return None, f"best_rel_{best_rel:.3f}>tol"
    # distinct qnames within tolerance band
    within = {q for rel, q, _ in cands if rel <= value_tol}
    if len(within) > 1:
        # ambiguous only if the runner-up qname is also close (no clean margin)
        second = next((rel for rel, q, _ in cands if q != best_q), None)
        if second is not None and second < margin * max(best_rel, 1e-4):
            return None, f"ambiguous:{sorted(within)[:3]}"
    return best_q, {"rel": round(best_rel, 4), "target": target, "fact_val": best_v}

def load():
    guidance = json.loads((CLP / "guidance.json").read_text())
    facts_raw = json.loads((CLP / "facts.json").read_text())
    facts = {}
    for t, rows in facts_raw.items():
        out = []
        for f in rows:
            f = dict(f)
            f["_val"] = parse_value(f.get("value"))
            f["_period"] = parse_period_ref(f.get("period_ref"))
            f["_ufam"] = fact_unit_family(f.get("unit_ref"))
            out.append(f)
        facts[t] = out
    return guidance, facts

def run(value_tol=0.06, margin=4.0, total_only=True):
    guidance, facts = load()
    per_instance = []
    reasons = collections.Counter()
    for g in guidance:
        if total_only and (g.get("segment") or "Total") != "Total":
            reasons["segment_skip"] += 1; continue
        t = g.get("ticker")
        if t not in facts:
            reasons["no_company_facts"] += 1; continue
        q, detail = anchor_one(g, facts[t], value_tol, margin)
        if q:
            per_instance.append({"ticker": t, "slug": g["slug"], "qname": q,
                                 "existing": g.get("existing_qname"), "detail": detail})
            reasons["ANCHORED"] += 1
        else:
            reasons[detail.split(":")[0]] += 1
    # aggregate per (ticker, slug) -> mode
    by_key = collections.defaultdict(list)
    for r in per_instance:
        by_key[(r["ticker"], r["slug"])].append(r["qname"])
    oracle = {}
    for (t, slug), qs in by_key.items():
        c = collections.Counter(qs)
        mode_q, mode_n = c.most_common(1)[0]
        share = mode_n / len(qs)
        conf = "high" if (len(qs) >= 2 and share >= 0.8) else ("single" if len(qs) == 1 else "low")
        oracle[f"{t}|{slug}"] = {"qname": mode_q, "n": len(qs), "share": round(share, 2),
                                 "conf": conf, "distinct": len(c)}
    return per_instance, oracle, reasons

if __name__ == "__main__":
    per_instance, oracle, reasons = run()
    (CLP / "oracle.json").write_text(json.dumps(oracle, indent=0))
    (CLP / "per_instance.json").write_text(json.dumps(per_instance))
    print("=== anchoring outcomes (per guidance instance) ===")
    for k, v in reasons.most_common():
        print(f"  {k}: {v}")
    n_total = sum(reasons.values())
    print(f"  -> anchored {reasons['ANCHORED']}/{n_total} = {reasons['ANCHORED']/n_total:.1%}")
    print(f"=== oracle: {len(oracle)} (ticker,slug) pairs ===")
    conf_c = collections.Counter(v["conf"] for v in oracle.values())
    print("  by confidence:", dict(conf_c))
    multi = {k: v for k, v in oracle.items() if v["distinct"] > 1}
    print(f"  pairs with >1 distinct anchored qname: {len(multi)}")
    # quick spot-check sample
    print("=== spot-check (high-conf sample) ===")
    shown = 0
    for k, v in sorted(oracle.items()):
        if v["conf"] == "high":
            print(f"  {k} -> {v['qname']}  (n={v['n']} share={v['share']})")
            shown += 1
            if shown >= 25: break
