#!/usr/bin/env python3
"""
Deterministic catalog validator — the reconcile safety net (PER-DRIVER RECORD shape).

STRUCTURE ONLY, ZERO JUDGMENT. Validates BOTH the seed (source of truth) AND the catalog (reconcile output),
and HARD-FAILS (exit 1) on any structural break so a broken catalog can never ship silently.

Record = {driver_name, canonical_name, companies, evidence_refs:[{company,source_type,source_id,date,quote}], optional_links}
Catalog also has skips:[{driver_name,why}] + unresolved_rewrites:[{driver_name,proposed_to,why}].

Per-record integrity (run on BOTH seed + catalog via struct_errs):
  evidence_refs non-empty · companies == distinct(evidence_refs.company) with NO duplicates ·
  each ref has company/source_type/source_id/quote (+ date unless source_type==fiscal.ai-kpi).
SEED-only: 'catalog' is a NON-EMPTY list · entries well-formed · unique driver_name · every record self-canonical.
CATALOG-only: malformed · forbidden(route/kind) · uniqueness · canonical->self-canonical (coined, no chains) ·
  completeness (every seed name once across catalog/skips/unresolved) · provenance (no invented names) ·
  evidence-drift (catalog ref == seed ref, incl. quote) · side-list fields.

No name-matching / no semantics — only fields, sets, refs.
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

def struct_errs(rec):
    """Per-record structural errors shared by seed + catalog (fields/sets only — no judgment)."""
    errs, nm = [], (norm(rec.get("driver_name")) or "(no-name)")
    refs = rec.get("evidence_refs") or []
    if not refs: errs.append(f"{nm}: empty evidence_refs")
    comp = [norm(c) for c in (rec.get("companies") or [])]
    if len(comp) != len(set(comp)): errs.append(f"{nm}: duplicate companies")
    if set(comp) != ev_companies(rec): errs.append(f"{nm}: companies != distinct(evidence_refs.company)")
    for e in refs:
        if not isinstance(e, dict): errs.append(f"{nm}: non-dict evidence_ref"); continue
        miss = [k for k in ("company", "source_type", "source_id", "quote") if not str(e.get(k) or "").strip()]
        if norm(e.get("source_type")) != "fiscal.ai-kpi" and not str(e.get("date") or "").strip(): miss.append("date")
        if miss: errs.append(f"{nm}: ref missing {'+'.join(miss)}")
    return errs

def main():
    seed_p = sys.argv[1] if len(sys.argv) > 1 else DEF_SEED
    cat_p  = sys.argv[2] if len(sys.argv) > 2 else DEF_CAT
    seed = json.load(open(seed_p)); cat = json.load(open(cat_p))

    seed_recs    = records(seed)
    seed_names   = set(norm(r.get("driver_name")) for r in seed_recs if r.get("driver_name"))
    seed_by_name = {norm(r.get("driver_name")): r for r in seed_recs if r.get("driver_name")}

    cat_recs       = records(cat)
    cat_names_list = [norm(r.get("driver_name")) for r in cat_recs if r.get("driver_name")]
    cat_names      = set(cat_names_list)
    skips          = name_list(cat.get("skips"))
    unres          = name_list(cat.get("unresolved_rewrites"))
    self_canon     = set(norm(r.get("driver_name")) for r in cat_recs
                         if r.get("driver_name") and norm(r.get("canonical_name")) == norm(r.get("driver_name")))

    fails = []

    # ---- SEED self-validation (source of truth must be clean, independent of what reconcile keeps/skips) ----
    if not isinstance(seed.get("catalog"), list):
        fails.append(("SEED MALFORMED: missing 'catalog' list", ["seed.catalog"]))
    elif not seed.get("catalog"):
        fails.append(("SEED EMPTY: catalog has no driver records (silent no-op run?)", ["seed.catalog"]))
    seed_bad = [f"index {i}" for i, r in enumerate(seed.get("catalog") or []) if not (isinstance(r, dict) and norm(r.get("driver_name")))]
    if seed_bad: fails.append(("SEED MALFORMED: entry non-dict or missing driver_name", seed_bad))
    _snl = [norm(r.get("driver_name")) for r in seed_recs if r.get("driver_name")]
    seed_dups = sorted({n for n in _snl if _snl.count(n) > 1})
    if seed_dups: fails.append(("SEED UNIQUENESS: duplicate driver_name", seed_dups))
    seed_struct = []
    for r in seed_recs:
        nm = norm(r.get("driver_name"))
        if nm and norm(r.get("canonical_name")) != nm: seed_struct.append(f"{nm}: not self-canonical (seed)")
        seed_struct += struct_errs(r)
    if seed_struct: fails.append(("SEED record integrity (companies/evidence/ref-fields/self-canonical)", sorted(set(seed_struct))))

    # ---- CATALOG checks ----
    if not isinstance(cat.get("catalog"), list):
        fails.append(("MALFORMED: catalog missing 'catalog' list", ["catalog.catalog"]))
    malformed = [f"index {i}" for i, r in enumerate(cat.get("catalog") or []) if not (isinstance(r, dict) and norm(r.get("driver_name")))]
    if malformed: fails.append(("MALFORMED: catalog entry non-dict or missing driver_name", malformed))

    for k in ("route_to_other_lane", "scope_routes", "scope_route"):
        if k in cat: fails.append((f"FORBIDDEN: catalog has a '{k}' bucket", [k]))
    kinded = sorted(norm(r.get("driver_name")) for r in cat_recs if "kind" in r)
    if kinded: fails.append(("FORBIDDEN: catalog records carry a 'kind' field", kinded))

    dups = sorted({n for n in cat_names_list if cat_names_list.count(n) > 1})
    if dups: fails.append(("UNIQUENESS: duplicate driver_name in catalog", dups))

    cat_struct = []
    for r in cat_recs: cat_struct += struct_errs(r)
    if cat_struct: fails.append(("CATALOG record integrity (companies/evidence/ref-fields)", sorted(set(cat_struct))))

    bad_canon = sorted({(norm(r.get("canonical_name")) or "(empty)") for r in cat_recs if norm(r.get("canonical_name")) not in self_canon})
    if bad_canon: fails.append(("CANONICAL_NAME does not resolve to a self-canonical record", bad_canon))

    all_out = cat_names_list + skips + unres
    dropped = sorted(seed_names - set(all_out))
    multi   = sorted({n for n in all_out if all_out.count(n) > 1})
    if dropped: fails.append(("COMPLETE: seed names dropped (not in catalog/skips/unresolved)", dropped))
    if multi:   fails.append(("COMPLETE: name in >1 of catalog/skips/unresolved", multi))

    invented = sorted((cat_names | set(skips) | set(unres)) - seed_names)
    if invented: fails.append(("PROVENANCE: non-seed name in catalog/skips/unresolved", invented))

    bad_ev = []
    for r in cat_recs:
        nm = norm(r.get("driver_name")); s = seed_by_name.get(nm)
        if s and ev_full(r) != ev_full(s): bad_ev.append(nm)
    if bad_ev: fails.append(("EVIDENCE drift: catalog evidence_refs != seed (company/source_type/source_id/date/quote)", sorted(bad_ev)))

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
