#!/usr/bin/env python3
"""
Deterministic catalog validator — the G2/reconcile safety net.

STRUCTURE ONLY, ZERO JUDGMENT: it never reads what a driver MEANS. It only checks the
LLM writer's output for self-contradiction / dropped names / dangling refs / forbidden buckets,
and HARD-FAILS (exit 1) on any violation so a broken catalog can never ship silently.

Catalog buckets are EXACTLY: final_drivers · skips · rewrites · same_as.
There is NO route/scope bucket and NO `kind` field — their presence is a hard fail (regression guard).

No name matching · no banned-word · no format regex · no semantic call. Only JSON fields, sets, refs.

Usage:  validate_catalog.py <seed.json> <catalog.json>
"""
import sys, json

DEF_SEED = "/home/faisal/EventMarketDB/.claude/plans/Drivers/_menu_restaurants_seed.json"
DEF_CAT  = "/home/faisal/EventMarketDB/.claude/plans/Drivers/_menu_restaurants_catalog.json"

def norm(s): return (s or "").strip().lower()

def field(items, *keys):
    out = []
    for it in items or []:
        if isinstance(it, str): out.append(norm(it))
        elif isinstance(it, dict):
            for k in keys:
                if it.get(k): out.append(norm(it[k])); break
    return out

def main():
    seed_p = sys.argv[1] if len(sys.argv) > 1 else DEF_SEED
    cat_p  = sys.argv[2] if len(sys.argv) > 2 else DEF_CAT
    seed = json.load(open(seed_p)); cat = json.load(open(cat_p))

    # ---- seed distinct names ----
    seed_names = set()
    for m in seed.get("menus", []):
        for c in m.get("candidates", []):
            n = c.get("driver_name") if isinstance(c, dict) else c
            if n: seed_names.add(norm(n))

    # ---- catalog buckets (exactly four) ----
    fd_items = cat.get("final_drivers") or []
    final  = set(field(fd_items, "driver_name"))
    skips  = set(field(cat.get("skips"), "driver_name"))
    rew    = [r for r in (cat.get("rewrites") or []) if isinstance(r, dict)]
    rew_from = set(norm(r.get("from")) for r in rew if r.get("from"))
    rew_to   = set(norm(r.get("to"))   for r in rew if r.get("to"))
    sa     = [s for s in (cat.get("same_as") or []) if isinstance(s, dict)]
    sa_var = set(norm(s.get("variant"))   for s in sa if s.get("variant"))
    sa_can = set(norm(s.get("canonical")) for s in sa if s.get("canonical"))

    fails = []

    # 0. FORBIDDEN — the route concept and `kind` field no longer exist; their reappearance is a regression
    for k in ("route_to_other_lane", "scope_routes", "scope_route"):
        if k in cat: fails.append((f"FORBIDDEN: catalog has a '{k}' bucket (route concept removed)", [k]))
    kinded = sorted(norm(x.get("driver_name")) for x in fd_items if isinstance(x, dict) and "kind" in x)
    if kinded: fails.append(("FORBIDDEN: final_drivers carry a 'kind' field (dropped)", kinded))

    # 1. DISJOINT — a name may have only ONE outcome
    outcome = {"final": final, "skips": skips, "rewrite.from": rew_from, "same_as.variant": sa_var}
    overlap = {n: [b for b, s in outcome.items() if n in s] for n in set().union(*outcome.values())}
    overlap = {n: w for n, w in overlap.items() if len(w) > 1}
    if overlap: fails.append(("DISJOINT (name in >1 bucket)", overlap))

    # 2. COMPLETE — every seed name accounted for; no invented outcome-source names
    accounted = final | skips | rew_from | sa_var
    dropped  = sorted(seed_names - accounted)
    invented = sorted((skips | rew_from | sa_var) - seed_names)   # final may hold coined rewrite-targets; the source buckets must be seed names
    if dropped:  fails.append(("COMPLETE: seed names dropped", dropped))
    if invented: fails.append(("COMPLETE: non-seed names in outcome buckets", invented))

    # 3. REFERENCES — rewrite.to & same_as.canonical must resolve to a final driver
    bad_to  = sorted(rew_to - final)
    bad_can = sorted(sa_can - final)
    if bad_to:  fails.append(("REFERENCES: rewrite.to not in final_drivers", bad_to))
    if bad_can: fails.append(("REFERENCES: same_as.canonical not in final_drivers", bad_can))

    # 4. ACCOUNTING — key-independent: every seed name lands in exactly one bucket (declared counts NOT trusted)
    admitted_seed = final & seed_names
    bucket_sum = len(admitted_seed) + len(rew_from) + len(skips) + len(sa_var)
    if bucket_sum != len(seed_names):
        fails.append(("ACCOUNTING: admitted+rewrite.from+skip+same_as.variant != seed distinct",
                      {"seed": len(seed_names), "admitted": len(admitted_seed), "rewrite.from": len(rew_from),
                       "skip": len(skips), "same_as.variant": len(sa_var), "sum": bucket_sum}))

    # 5. PROVENANCE — every final driver must be a seed name or a rewrite target (no invented finals)
    extra_final = sorted(final - (seed_names | rew_to))
    if extra_final:
        fails.append(("PROVENANCE: final driver not from seed and not a rewrite.to", extra_final))

    if fails:
        print("VALIDATION FAILED")
        for tag, info in fails:
            n = len(info) if isinstance(info, (list, dict)) else 1
            print(f"  ✗ {tag}  ({n}): {json.dumps(info)[:600]}")
        sys.exit(1)

    print(f"VALIDATION PASSED  seed={len(seed_names)} | final={len(final)} skip={len(skips)} "
          f"rewrite={len(rew_from)} same_as={len(sa_var)}")

if __name__ == "__main__":
    main()
