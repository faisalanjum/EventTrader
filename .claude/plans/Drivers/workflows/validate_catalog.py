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

PHASE-0 additions (HierarchicalCatalogPlan D1/§3a/§3e, 10th pass):
  optional 3rd arg approved.json -> D1 FUSION-APPROVAL (every canonical_name != driver_name pair
  must be in approved.same_as or approved.rewrites) + SAME_AS_VARIANTS mirror check (each record's
  same_as_variants == the names actually folded onto it in this catalog). Omitting approved.json
  SKIPS those two checks with a WARN (legacy mode). Stale _menu_restaurants_* defaults REMOVED.

PHASE-1 additions (HierarchicalCatalogPlan D8/§11.2/§11.3/§11.9 — fold mode):
  - §11.3 relaxations (both leaf + fold): COMPLETE/PROVENANCE accounting includes the
    unresolved_same_name[] catalog side-list ({name, occurrences, why} — fields validated);
    with --review, D5 split-map TARGET names are legitimate non-seed names, i.e.
    (catalog ∪ skips ∪ unresolved_rewrites ∪ unresolved_same_name) − (seed ∪ split_targets) = ∅,
    and COMPLETE counts the split-map FROM names (§11.2 — a leaf split's source name lives
    only in the split map, not as a record).
    The parent seed carries scope_name/scope_level instead of industry — industry never required.
  - D8 (with --fold <child catalogs>; zero judgment): NAMES (every child driver_name accounted
    EXACTLY ONCE across parent self-canonical records ∪ same_as_variants ∪ skips ∪
    unresolved_rewrites ∪ unresolved_same_name (catalog + --sidecars parks) ∪ split-map from
    names) · EVIDENCE (parent record evidence == exact 5-tuple union of its child cluster) ·
    PARTITION (a DIFFERENT split's records partition the from-name's child evidence union —
    disjoint + complete) · VARIANTS (no invented variant names — every variant exists in some
    child, or is an approved split target). Parks must carry non-empty occurrence evidence.

No name-matching / no semantics — only fields, sets, refs.
Usage:  validate_catalog.py <seed.json> <catalog.json> [approved.json]
            [--fold <child_catalog.json> ...] [--review same_name_review.json]
            [--sidecars fold_sidecars.json]
"""
import hashlib, sys, json
from collections import Counter
from pathlib import Path

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

def parse_args(argv):
    """Manual parse (no argparse — keeps the exact Usage/exit-2 contract): positionals
    seed/catalog/[approved] + --fold <child...> + --review X + --sidecars X."""
    pos, fold, review_p, sidecars_p, i = [], [], None, None, 0
    while i < len(argv):
        a = argv[i]
        if a == "--fold":
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                fold.append(argv[i]); i += 1
        elif a == "--review":
            review_p = argv[i + 1]; i += 2
        elif a == "--sidecars":
            sidecars_p = argv[i + 1]; i += 2
        else:
            pos.append(a); i += 1
    return pos, fold, review_p, sidecars_p

def park_errs(entries, where):
    """unresolved_same_name[] field check: {name, occurrences:[{..., evidence_refs}], why};
    every occurrence must carry NON-EMPTY evidence_refs (D8 park rule)."""
    bad = []
    for x in (entries or []):
        if not (isinstance(x, dict) and str(x.get("name") or "").strip()
                and str(x.get("why") or "").strip()
                and isinstance(x.get("occurrences"), list) and x.get("occurrences")):
            bad.append(f"{where}: malformed entry {str(x)[:80]}")
            continue
        for o in x["occurrences"]:
            if not (isinstance(o, dict) and o.get("evidence_refs")):
                bad.append(f"{where}: '{norm(x.get('name'))}' occurrence missing/empty evidence_refs")
    return bad

def main():
    pos, fold_ps, review_p, sidecars_p = parse_args(sys.argv[1:])
    if len(pos) < 2 or len(pos) > 3:
        print("Usage: validate_catalog.py <seed.json> <catalog.json> [approved.json] "
              "[--fold <child_catalog.json> ...] [--review same_name_review.json] "
              "[--sidecars fold_sidecars.json]", file=sys.stderr)
        sys.exit(2)
    seed_p, cat_p = pos[0], pos[1]
    appr_p = pos[2] if len(pos) > 2 else None
    seed = json.load(open(seed_p)); cat = json.load(open(cat_p))
    review = json.load(open(review_p)) if review_p else None
    sidecars = json.load(open(sidecars_p)) if sidecars_p else None
    split_from, split_targets = [], set()
    for s in ((review or {}).get("split_map") or []):
        if norm(s.get("from")): split_from.append(norm(s.get("from")))
        for t in (s.get("to") or []):
            if norm(t): split_targets.add(norm(t))

    seed_recs    = records(seed)
    seed_names   = set(norm(r.get("driver_name")) for r in seed_recs if r.get("driver_name"))
    seed_by_name = {norm(r.get("driver_name")): r for r in seed_recs if r.get("driver_name")}

    cat_recs       = records(cat)
    cat_names_list = [norm(r.get("driver_name")) for r in cat_recs if r.get("driver_name")]
    cat_names      = set(cat_names_list)
    skips          = name_list(cat.get("skips"))
    unres          = name_list(cat.get("unresolved_rewrites"))
    unres_same     = name_list(cat.get("unresolved_same_name"), key="name")  # §11.3(b) side-list
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

    # §11.2 leaf accounting: a D5 split's 'from' name is accounted via the split map (--review)
    all_out = cat_names_list + skips + unres + unres_same + split_from
    dropped = sorted(seed_names - set(all_out))
    multi   = sorted({n for n in all_out if all_out.count(n) > 1})
    if dropped: fails.append(("COMPLETE: seed names dropped (not in catalog/skips/unresolved/unresolved_same_name/split-from)", dropped))
    if multi:   fails.append(("COMPLETE: name in >1 of catalog/skips/unresolved/unresolved_same_name/split-from", multi))

    # §11.3(a): D5 split-map TARGET names are legitimate non-seed names (read from --review)
    invented = sorted((cat_names | set(skips) | set(unres) | set(unres_same))
                      - (seed_names | split_targets))
    if invented: fails.append(("PROVENANCE: non-seed name in catalog/skips/unresolved (and not a D5 split target)", invented))

    bad_ev = []
    for r in cat_recs:
        nm = norm(r.get("driver_name")); s = seed_by_name.get(nm)
        if s and ev_full(r) != ev_full(s): bad_ev.append(nm)
    if bad_ev: fails.append(("EVIDENCE drift: catalog evidence_refs != seed (company/source_type/source_id/date/quote)", sorted(bad_ev)))

    # ---- D1 FUSION-APPROVAL + SAME_AS_VARIANTS mirror (approved.json given) ----
    if appr_p is None:
        print("WARN: no approved.json passed — D1 fusion-approval + same_as_variants checks SKIPPED", file=sys.stderr)
    else:
        appr = json.load(open(appr_p))
        ok_links = set()
        for l in (appr.get("same_as") or []):
            ok_links.add((norm(l.get("variant")), norm(l.get("canonical"))))
        for l in (appr.get("rewrites") or []):
            ok_links.add((norm(l.get("from")), norm(l.get("to"))))
        # D1 accepts the TRANSITIVE closure of approved links: STAR-flattening (assembler /
        # fold §11.7.6) turns approved chains a->b->c into a direct a->c pointer — every hop
        # was individually Refute-approved, so reachability over approved edges = approval.
        adj = {}
        for a, b in ok_links:
            adj.setdefault(a, set()).add(b)
        def _reachable(src, dst):
            seen, stack = set(), [src]
            while stack:
                cur = stack.pop()
                if cur == dst:
                    return True
                if cur in seen:
                    continue
                seen.add(cur)
                stack.extend(adj.get(cur, ()))
            return False
        bad_fusion = sorted({norm(r.get("driver_name")) for r in cat_recs
                             if norm(r.get("canonical_name")) != norm(r.get("driver_name"))
                             and not _reachable(norm(r.get("driver_name")), norm(r.get("canonical_name")))})
        if bad_fusion:
            fails.append(("D1 FUSION-APPROVAL: canonical_name not REACHABLE via the Refute-approved link set", bad_fusion))
        # mirror: same_as_variants[C] == (the SEED record's CARRIED variants — §11.5 fold-parent
        #         seeds may already hold child variants) ∪ (names actually folded onto C HERE)
        folded = {}
        for r in cat_recs:
            cn, dn = norm(r.get("canonical_name")), norm(r.get("driver_name"))
            if cn and dn and cn != dn:
                folded.setdefault(cn, set()).add(dn)
        bad_var = []
        for r in cat_recs:
            nm = norm(r.get("driver_name"))
            got = set(norm(v) for v in (r.get("same_as_variants") or []))
            seed_carried = set(norm(v) for v in ((seed_by_name.get(nm) or {}).get("same_as_variants") or []))
            if got != (seed_carried | folded.get(nm, set())):
                bad_var.append(nm)
        if bad_var:
            fails.append(("SAME_AS_VARIANTS: mirror != names actually folded onto the record", sorted(bad_var)))

        # ---- 12th pass rev2 HIGH-BLAST backstop (pure code; the workflow's trigger relay is only an
        # optimization): recompute every approved fusion's company count FROM THE SEED; any fusion
        # spanning >= 8 companies MUST carry a SURVIVING second-skeptic verdict in
        # approved.high_blast_refute2 — else the catalog cannot ship.
        HIGH_BLAST = 8
        def _coset(n):
            return set(((seed_by_name.get(n) or {}).get("companies")) or [])
        hb_ok = {frozenset((norm(e.get("a")), norm(e.get("b"))))
                 for e in (appr.get("high_blast_refute2") or []) if e.get("survives") is True}
        bad_hb = sorted(f"{a} -> {b} (n={len(_coset(a) | _coset(b))})" for a, b in ok_links
                        if len(_coset(a) | _coset(b)) >= HIGH_BLAST
                        and frozenset((a, b)) not in hb_ok)
        if bad_hb:
            fails.append(("HIGH-BLAST fusion (>=8 companies) lacks a surviving second-skeptic verdict "
                          "in approved.high_blast_refute2", bad_hb))

    # 12th pass rev2 (owner): a KEPT high-blast same-name union (D5 verdict SAME on a record whose
    # seed companies >= 8) must carry high_blast_refute2_survived=true in the review file.
    if review is not None:
        bad_d5hb = sorted(
            f"{norm(v.get('collision_name'))} (n={len(((seed_by_name.get(norm(v.get('collision_name'))) or {}).get('companies')) or [])})"
            for v in (review.get("reviews") or [])
            if v.get("verdict") == "SAME"
            and len(((seed_by_name.get(norm(v.get("collision_name"))) or {}).get("companies")) or []) >= 8
            and v.get("high_blast_refute2_survived") is not True)
        if bad_d5hb:
            fails.append(("HIGH-BLAST D5 SAME union (>=8 companies) lacks high_blast_refute2_survived in the review file", bad_d5hb))

    bad_skip = [str(x) for x in (cat.get("skips") or []) if not (isinstance(x, dict) and str(x.get("driver_name") or "").strip() and str(x.get("why") or "").strip())]
    bad_unr  = [str(x) for x in (cat.get("unresolved_rewrites") or []) if not (isinstance(x, dict) and str(x.get("driver_name") or "").strip() and str(x.get("proposed_to") or "").strip() and str(x.get("why") or "").strip())]
    if bad_skip: fails.append(("SIDE-FIELDS: skips[] entry missing driver_name/why", bad_skip[:50]))
    if bad_unr:  fails.append(("SIDE-FIELDS: unresolved_rewrites[] entry missing driver_name/proposed_to/why", bad_unr[:50]))
    bad_park = park_errs(cat.get("unresolved_same_name"), "catalog") \
             + park_errs((sidecars or {}).get("unresolved_same_name"), "sidecars")
    if bad_park: fails.append(("SIDE-FIELDS: unresolved_same_name[] entry missing name/occurrences/why or empty occurrence evidence_refs", bad_park[:50]))

    # ---- D8 fold mode (--fold child catalogs): names/evidence/partition/variants — zero judgment ----
    if fold_ps:
        union_ev, all_child_names = {}, set()   # rep name -> 5-tuple union ACROSS children
        child_variant_names = set()             # variants the children THEMSELVES carry (deeper levels)
        rep_children = Counter()                # rep name -> how many children carry it (Stage-0 #6)
        for ci, fp in enumerate(fold_ps):
            ch = json.load(open(fp))
            crecs = [r for r in (ch.get("catalog") or []) if isinstance(r, dict) and norm(r.get("driver_name"))]
            cby = {norm(r.get("driver_name")): r for r in crecs}
            all_child_names |= set(cby)
            child_variant_names |= {norm(v) for r in crecs
                                    for v in (r.get("same_as_variants") or []) if norm(v)}
            child_reps = set()
            for n in sorted(cby):               # independent canonical-fixpoint resolution
                cur, chain = n, []
                while True:
                    if cur in chain or cur not in cby:
                        fails.append((f"D8 CHILD: canonical chain cycle/dangling in child {fp}",
                                      chain + [cur])); cur = None; break
                    chain.append(cur)
                    nxt = norm(cby[cur].get("canonical_name"))
                    if nxt == cur: break
                    cur = nxt
                if cur is not None:
                    union_ev.setdefault(cur, set()).update(ev_full(cby[n]))
                    child_reps.add(cur)
            rep_children.update(child_reps)

        # Stage-0 #6 (12th-pass gap): the workflow's GLOBAL-fold high-blast trigger
        # ((scope_level global) AND (n_children >= 2)) read an AGENT-relayed collision_meta;
        # recompute n_children here FROM THE CHILD CATALOGS so a deflated relay cannot
        # silently skip the second skeptic on a kept global SAME union.
        if norm(str(seed.get("scope_level") or "")) == "global" and review is not None:
            bad_g = sorted(
                f"{norm(v.get('collision_name'))} (children={rep_children[norm(v.get('collision_name'))]})"
                for v in (review.get("reviews") or [])
                if v.get("verdict") == "SAME"
                and rep_children[norm(v.get("collision_name"))] >= 2
                and v.get("high_blast_refute2_survived") is not True)
            if bad_g:
                fails.append(("HIGH-BLAST GLOBAL-fold SAME union (>=2 children, recomputed from "
                              "child catalogs) lacks high_blast_refute2_survived in the review file",
                              bad_g))

        # (a) NAMES: every child driver_name accounted EXACTLY ONCE (§11.2)
        park_names = unres_same + name_list((sidecars or {}).get("unresolved_same_name"), key="name")
        acct = Counter([n for n in cat_names_list if n in self_canon]
                       + [norm(v) for r in cat_recs for v in (r.get("same_as_variants") or []) if norm(v)]
                       + skips + unres + park_names + split_from)
        bad_n = sorted(f"{n} (x{acct[n]})" for n in all_child_names if acct[n] != 1)
        if bad_n: fails.append(("D8 NAMES: child driver_name not accounted EXACTLY ONCE across "
                                "records/variants/skips/unresolved/parks/split-from", bad_n))

        # (b) EVIDENCE: parent record evidence == exact 5-tuple union of its child cluster
        bad_e = []
        for r in cat_recs:
            n = norm(r.get("driver_name"))
            if not n or n in split_targets: continue          # splits checked by PARTITION
            exp = union_ev.get(n)
            if exp is None: bad_e.append(f"{n}: no child evidence source (not a child rep name)")
            elif ev_full(r) != exp: bad_e.append(f"{n}: evidence != union of children")
        if bad_e: fails.append(("D8 EVIDENCE: parent evidence_refs != exact 5-tuple union of children", sorted(bad_e)))

        # (b/§11.2) PARTITION: a DIFFERENT split partitions the from-name's child union
        bad_p = []
        cat_by = {norm(r.get("driver_name")): r for r in cat_recs if r.get("driver_name")}
        for s in ((review or {}).get("split_map") or []):
            f, tos = norm(s.get("from")), [norm(t) for t in (s.get("to") or []) if norm(t)]
            from_union = union_ev.get(f)
            if from_union is None:
                bad_p.append(f"{f}: from-name has no child evidence"); continue
            missing = [t for t in tos if t not in cat_by]
            if missing:
                bad_p.append(f"{f}: split target(s) missing from catalog: {missing}"); continue
            sets = [ev_full(cat_by[t]) for t in tos]
            u = set().union(*sets) if sets else set()
            if sum(len(x) for x in sets) != len(u): bad_p.append(f"{f}: split evidence sets overlap (ref duplicated)")
            if u != from_union: bad_p.append(f"{f}: union of split evidence != from-name child union (ref lost/invented)")
        if bad_p: fails.append(("D8 PARTITION: split records do not partition the from-name's evidence", bad_p))

        # (d) VARIANTS: no invented variant names. Legit = child RECORD names + the variants
        # the children themselves carry (3+ level folds: a leaf-collapsed name exists only
        # inside a child's same_as_variants, never as a child record) + split targets.
        legit = all_child_names | child_variant_names | split_targets
        bad_v = sorted({f"{norm(r.get('driver_name'))}: {norm(v)}" for r in cat_recs
                        for v in (r.get("same_as_variants") or [])
                        if norm(v) and norm(v) not in legit})
        if bad_v: fails.append(("D8 VARIANTS: variant name not found in any child (invented)", bad_v))

    if fails:
        print("VALIDATION FAILED")
        for tag, info in fails:
            n = len(info) if isinstance(info, (list, dict)) else 1
            print(f"  ✗ {tag}  ({n}): {json.dumps(info)[:600]}")
    else:
        fold_note = f" | D8 fold: children={len(fold_ps)}" if fold_ps else ""
        print(f"VALIDATION PASSED  seed={len(seed_names)} | catalog={len(cat_names)} "
              f"(self-canonical={len(self_canon)}, rolled-up={len(cat_names)-len(self_canon)}) "
              f"skip={len(skips)} unresolved={len(unres)} unresolved_same_name={len(unres_same)}{fold_note}")

    # Stage-0 #1: code-written, content-bound verdict sidecar. The agent relaying this
    # validator's output is NEVER re-checked by code — this file is. Consumers (fold part-a,
    # repair-suggest CLI, the honesty gate) hard-fail unless it exists, exit==0, AND the
    # catalog/approved bytes are UNCHANGED since this validation (sha binding also catches
    # "validator never actually ran" and "catalog rewritten after validation").
    sidecar = {"exit": 1 if fails else 0,
               "fold": bool(fold_ps),   # final-gate fix: a fold parent's LAST validation must be D8 (--fold) mode
               "catalog_sha256": hashlib.sha256(Path(cat_p).read_bytes()).hexdigest()}
    if appr_p is not None:
        sidecar["approved_sha256"] = hashlib.sha256(Path(appr_p).read_bytes()).hexdigest()
    (Path(cat_p).parent / "validation_exit.json").write_text(json.dumps(sidecar) + "\n")
    if fails:
        sys.exit(1)

if __name__ == "__main__":
    main()
