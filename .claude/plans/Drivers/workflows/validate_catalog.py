#!/usr/bin/env python3
"""
Deterministic catalog validator — the reconcile safety net (PER-DRIVER RECORD shape).

STRUCTURE ONLY, ZERO JUDGMENT. The catalog is per-driver records:
  catalog:[ {driver_name, canonical_name, companies, evidence_refs:[{company,source_type,source_id,date,quote}], optional_links} ]
  + skips:[{driver_name,why}]  + unresolved_rewrites:[{driver_name,proposed_to,why}]
It HARD-FAILS (exit 1) on any structural break so a broken catalog can never ship silently.

Checks (no name-matching / no semantics — only fields, sets, refs):
  FORBIDDEN     no route bucket, no `kind` field
  UNIQUENESS    one record per driver_name
  COMPANIES     companies == distinct(evidence_refs.company) ; evidence_refs non-empty
  REF-FIELDS    each evidence_ref has company/source_type/source_id/quote (+ date, unless source_type==fiscal.ai-kpi)
  CANONICAL     every canonical_name resolves to a SELF-canonical catalog record (coined target, no chains)
  COMPLETE      every seed driver_name appears EXACTLY once across catalog / skips / unresolved_rewrites
  PROVENANCE    no non-seed name in catalog / skips / unresolved (roll-up & rewrite targets are coined)
  EVIDENCE      each catalog record's evidence_refs match the seed record EXACTLY (company/source_type/source_id/date/quote — no drift)
  SIDE-FIELDS   skips[] entries have driver_name+why ; unresolved_rewrites[] entries have driver_name+proposed_to+why
  SEED          the seed file itself is well-formed (no malformed entries · no duplicate driver_name)

Usage:  validate_catalog.py <seed.json> <catalog.json>
"""
import sys, json

DEF_SEED = "/home/faisal/EventMarketDB/.claude/plans/Drivers/_menu_restaurants_seed.json"
DEF_CAT  = "/home/faisal/EventMarketDB/.claude/plans/Drivers/_menu_restaurants_catalog.json"

def norm(s): return (s or "").strip().lower()
def records(obj): return [r for r in (obj.get("catalog") or []) if isinstance(r, dict)]
def name_list(items, key="driver_name"): return [norm(x.get(key)) for x in (items or []) if isinstance(x, dict) and x.get(key)]
def ev_companies(rec): return set(norm(e.get("company")) for e in (rec.get("evidence_refs") or []) if isinstance(e, dict) and e.get("company"))
def ev_full(rec):
    out = set()
    for e in (rec.get("evidence_refs") or []):
        if isinstance(e, dict):
            out.add((norm(e.get("company")), norm(e.get("source_type")), norm(e.get("source_id")), norm(e.get("date")), (e.get("quote") or "").strip()))
    return out

def main():
    seed_p = sys.argv[1] if len(sys.argv) > 1 else DEF_SEED
    cat_p  = sys.argv[2] if len(sys.argv) > 2 else DEF_CAT
    seed = json.load(open(seed_p)); cat = json.load(open(cat_p))

    seed_recs   = records(seed)
    seed_names  = set(norm(r.get("driver_name")) for r in seed_recs if r.get("driver_name"))
    seed_by_name = {norm(r.get("driver_name")): r for r in seed_recs if r.get("driver_name")}

    cat_recs       = records(cat)
    cat_names_list = [norm(r.get("driver_name")) for r in cat_recs if r.get("driver_name")]
    cat_names      = set(cat_names_list)
    skips          = name_list(cat.get("skips"))
    unres          = name_list(cat.get("unresolved_rewrites"))
    self_canon     = set(norm(r.get("driver_name")) for r in cat_recs
                         if r.get("driver_name") and norm(r.get("canonical_name")) == norm(r.get("driver_name")))

    fails = []

    # SEED-WELLFORMED — the seed is the source of truth; validate the seed file itself, not just the catalog
    seed_raw = seed.get("catalog") or []
    seed_bad = [f"index {i}" for i, r in enumerate(seed_raw) if not (isinstance(r, dict) and norm(r.get("driver_name")))]
    if seed_bad: fails.append(("SEED MALFORMED: seed entry is non-dict or missing driver_name", seed_bad))
    _seed_nl = [norm(r.get("driver_name")) for r in seed_recs if r.get("driver_name")]
    seed_dups = sorted({n for n in _seed_nl if _seed_nl.count(n) > 1})
    if seed_dups: fails.append(("SEED UNIQUENESS: duplicate driver_name in seed", seed_dups))

    # MALFORMED — every catalog entry must be a dict with a non-empty driver_name (no silent drops)
    malformed = [f"index {i}" for i, r in enumerate(cat.get("catalog") or []) if not (isinstance(r, dict) and norm(r.get("driver_name")))]
    if malformed: fails.append(("MALFORMED: catalog entry is non-dict or missing driver_name", malformed))

    # FORBIDDEN — route concept + kind never exist (regression guard)
    for k in ("route_to_other_lane", "scope_routes", "scope_route"):
        if k in cat: fails.append((f"FORBIDDEN: catalog has a '{k}' bucket", [k]))
    kinded = sorted(norm(r.get("driver_name")) for r in cat_recs if "kind" in r)
    if kinded: fails.append(("FORBIDDEN: catalog records carry a 'kind' field", kinded))

    # UNIQUENESS — one record per driver_name
    dups = sorted({n for n in cat_names_list if cat_names_list.count(n) > 1})
    if dups: fails.append(("UNIQUENESS: duplicate driver_name in catalog", dups))

    # COMPANIES == distinct(evidence_refs.company) + evidence non-empty
    bad_comp, empty_ev = [], []
    for r in cat_recs:
        nm = norm(r.get("driver_name"))
        comp = [norm(c) for c in (r.get("companies") or [])]
        if len(comp) != len(set(comp)) or set(comp) != ev_companies(r): bad_comp.append(nm)
        if not (r.get("evidence_refs") or []): empty_ev.append(nm)
    if bad_comp:  fails.append(("COMPANIES != distinct(evidence_refs.company)", sorted(bad_comp)))
    if empty_ev:  fails.append(("EMPTY evidence_refs (every kept driver must carry its evidence)", sorted(empty_ev)))

    # REF-FIELDS — each evidence_ref well-formed: company/source_type/source_id/quote required; date required unless KPI
    bad_refs = []
    for r in cat_recs:
        nm = norm(r.get("driver_name"))
        for e in (r.get("evidence_refs") or []):
            if not isinstance(e, dict): bad_refs.append(f"{nm}: non-dict ref"); continue
            miss = [k for k in ("company","source_type","source_id","quote") if not str(e.get(k) or "").strip()]
            if norm(e.get("source_type")) != "fiscal.ai-kpi" and not str(e.get("date") or "").strip(): miss.append("date")
            if miss: bad_refs.append(f"{nm}: {'+'.join(miss)}")
    if bad_refs: fails.append(("REF-FIELDS: evidence_ref missing required field(s)", sorted(set(bad_refs))))

    # CANONICAL — resolves to a self-canonical catalog record (coined target, no chains)
    bad_canon = sorted({(norm(r.get("canonical_name")) or "(empty)") for r in cat_recs
                        if norm(r.get("canonical_name")) not in self_canon})
    if bad_canon: fails.append(("CANONICAL_NAME does not resolve to a self-canonical record", bad_canon))

    # COMPLETE — every seed name EXACTLY once across catalog / skips / unresolved
    all_out = cat_names_list + skips + unres
    dropped = sorted(seed_names - set(all_out))
    multi   = sorted({n for n in all_out if all_out.count(n) > 1})
    if dropped: fails.append(("COMPLETE: seed names dropped (not in catalog/skips/unresolved)", dropped))
    if multi:   fails.append(("COMPLETE: name in >1 of catalog/skips/unresolved", multi))

    # PROVENANCE — nothing invented (targets are coined → every output name is a seed name)
    invented = sorted((cat_names | set(skips) | set(unres)) - seed_names)
    if invented: fails.append(("PROVENANCE: non-seed name in catalog/skips/unresolved", invented))

    # EVIDENCE drift — catalog record evidence must equal the seed record's (verbatim copy)
    bad_ev = []
    for r in cat_recs:
        nm = norm(r.get("driver_name")); s = seed_by_name.get(nm)
        if s and ev_full(r) != ev_full(s): bad_ev.append(nm)
    if bad_ev: fails.append(("EVIDENCE drift: catalog evidence_refs != seed (full ref: company/source_type/source_id/date/quote)", sorted(bad_ev)))

    # SIDE-FIELDS — skips[] and unresolved_rewrites[] entries must carry their required fields
    bad_skip = [str(x) for x in (cat.get("skips") or []) if not (isinstance(x, dict) and str(x.get("driver_name") or "").strip() and str(x.get("why") or "").strip())]
    bad_unr  = [str(x) for x in (cat.get("unresolved_rewrites") or []) if not (isinstance(x, dict) and str(x.get("driver_name") or "").strip() and str(x.get("proposed_to") or "").strip() and str(x.get("why") or "").strip())]
    if bad_skip: fails.append(("SIDE-FIELDS: skips[] entry missing driver_name/why", bad_skip[:50]))
    if bad_unr:  fails.append(("SIDE-FIELDS: unresolved_rewrites[] entry missing driver_name/proposed_to/why", bad_unr[:50]))

    if fails:
        print("VALIDATION FAILED")
        for tag, info in fails:
            n = len(info) if isinstance(info, (list, dict)) else 1
            print(f"  ✗ {tag}  ({n}): {json.dumps(info)[:600]}")
        sys.exit(1)

    print(f"VALIDATION PASSED  seed={len(seed_names)} | catalog={len(cat_names)} "
          f"(self-canonical={len(self_canon)}, rolled-up={len(cat_names)-len(self_canon)}) "
          f"skip={len(skips)} unresolved={len(unres)}")

if __name__ == "__main__":
    main()
