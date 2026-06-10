#!/usr/bin/env python3
"""
Deterministic fold combine (HierarchicalCatalogPlan §11.7) + the §12.8 evidence draw
+ the §11.11 SEED_MAX guard. ZERO AI, ZERO merge judgment — union, count, set-compare,
HARD-FAIL only. The same-name review (AI, §11.6) runs BETWEEN part-a and part-b in the
workflow; this CLI trusts (and structurally checks) its artifact.

part-a  <parent_run_dir> --scope-name X --scope-level sector|global --children <dir> ...
    Per child: resolve every SAME_AS cluster to its self-canonical rep (canonical_name
    followed to a fixpoint; cycle/dangling = SystemExit), union variant evidence onto the
    rep (dedup by the exact 5-tuple), recompute companies, carry variant names (+ the
    variants' own same_as_variants) into the rep's same_as_variants; DROP the child's
    skips/unresolved_rewrites/unresolved_same_name but COUNT them (§11.16). Then group
    reps ACROSS children by norm()'d name: unique -> passthrough; identical in >=2
    children -> the SAME-NAME REVIEW queue (never pre-merged, D5).
    Writes fold_queue.json {queue} + fold_passthrough.json {records} +
    fold_manifest.json {scope_name, scope_level, children:[counts]}.
    The one-line summary also carries collision_names (sorted queue names) + collision_meta
    {name: {n_companies (distinct across ALL occurrences), n_children (occurrence count)}}.
    §11.11 GUARD fires BEFORE writing: records > SEED_MAX_RECORDS (400) or serialized
    chars > SEED_MAX_CHARS (300,000) -> guard line + exit 1.

draw    <parent_run_dir> [--cap N]
    §12.8 evidence views for each queued collision: sides = occurrences (side_key =
    child_run_id), canonical 5-tuple ref order, sides ascending by total ref count
    (smallest side FIRST), within a side a company round-robin (least-represented
    companies first) with source-type + date spread (empty date sorts FIRST); cap is
    PER SIDE (RECONCILE_EVIDENCE_PER_RECORD = 20); view2 = the next up-to-cap refs,
    disjoint, shorter when exhausted, never padded. Writes fold_queue_views.json.

part-b  <parent_run_dir> --review same_name_review.json
    Apply the review (fail-close): every queue item needs EXACTLY one review.
    SAME (must carry refute_survived: true) -> one unioned record; DIFFERENT -> split
    records per the §11.6 assignment map (every from-ref assigned EXACTLY once — none
    lost/duplicated); UNCLEAR -> terminal park in fold_sidecars.json. optional_links
    merge per key: identical non-null -> keep; conflict -> null + a conflicts row
    (never silently pick; children visited in sorted child_run_id order). All records
    self-canonical (STAR); catalog sorted by driver_name, evidence by the 5-tuple.
    Writes seed.json (scope_name/scope_level shape, §11.8) + fold_sidecars.json.
    The same SEED_MAX guard runs on the final seed before writing.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

SEED_MAX_RECORDS = 400                 # §11.11 [OWNER]
SEED_MAX_CHARS = 300_000               # §11.11 [OWNER] — full serialized records, not the AI view
RECONCILE_EVIDENCE_PER_RECORD = 20     # §11.17 [OWNER] — per-SIDE prompt-view cap
ALL_NULL_LINKS = {"xbrl_concept": None, "xbrl_member": None, "guidance_ref": None}


def norm(s):  # §12.1 shared norm(): strip + lowercase (ASCII)
    return (s or "").strip().lower()


def serialize(obj):
    return json.dumps(obj, indent=1, ensure_ascii=False) + "\n"


def key5(ref):
    """The exact 5-tuple evidence identity (dedup + canonical sort key)."""
    return (norm(ref.get("company")), norm(ref.get("source_type")), norm(ref.get("source_id")),
            norm(ref.get("date")), (ref.get("quote") or "").strip())


def companies_of(refs):
    """sorted distinct evidence companies (dedup by norm, keep the first raw string)."""
    seen, out = set(), []
    for e in refs:
        c = e.get("company")
        if norm(c) not in seen:
            seen.add(norm(c))
            out.append(c)
    return sorted(out)


def guard_seed_max(records, max_records=None, max_chars=None):
    """§11.11 deterministic over-size HARD-FAIL — runs BEFORE any write / AI call."""
    max_records = SEED_MAX_RECORDS if max_records is None else max_records
    max_chars = SEED_MAX_CHARS if max_chars is None else max_chars
    chars = len(json.dumps(records, ensure_ascii=False, separators=(",", ":")))
    if len(records) > max_records or chars > max_chars:
        raise SystemExit(f"SEED_MAX GUARD: records={len(records)}>{max_records} "
                         f"or chars={chars}>{max_chars} — sub-split required")


def merge_optional_links(link_dicts):
    """Per key: exactly one distinct non-null value -> keep; >=2 -> None (+ conflict row);
    none -> None. Input order (sorted member/child order) pins the values order."""
    keys = []
    for d in link_dicts:
        for k in (d or {}):
            if k not in keys:
                keys.append(k)
    merged, conflicts = {}, []
    for k in keys:
        vals = []
        for d in link_dicts:
            v = (d or {}).get(k)
            if v is not None and v != "" and v not in vals:
                vals.append(v)
        merged[k] = vals[0] if len(vals) == 1 else None
        if len(vals) > 1:
            conflicts.append((k, vals))
    return merged, conflicts


# ---------------------------------------------------------------- part A (§11.7 Part A)

def collapse_child(cat, child_id="?"):
    """Resolve each cluster to its self-canonical rep; union evidence; carry variants;
    DROP side-lists but count them. Returns (reps sorted by name, counts)."""
    recs = [r for r in (cat.get("catalog") or []) if isinstance(r, dict) and norm(r.get("driver_name"))]
    by = {}
    for r in recs:
        n = norm(r["driver_name"])
        if n in by:
            raise SystemExit(f"FOLD FAIL [{child_id}]: duplicate driver_name '{n}' in child catalog")
        by[n] = r

    def rep_of(n):
        chain, cur = [], n
        while True:
            if cur in chain:
                raise SystemExit(f"FOLD FAIL [{child_id}]: canonical_name cycle "
                                 f"{' -> '.join(chain + [cur])}")
            chain.append(cur)
            nxt = norm(by[cur].get("canonical_name"))
            if not nxt or nxt not in by:
                raise SystemExit(f"FOLD FAIL [{child_id}]: canonical_name '{nxt or '(empty)'}' "
                                 f"dangles (chain {' -> '.join(chain)})")
            if nxt == cur:
                return cur
            cur = nxt

    clusters = {}
    for n in sorted(by):
        clusters.setdefault(rep_of(n), []).append(n)

    reps = []
    for rep_n in sorted(clusters):
        members = [rep_n] + [m for m in clusters[rep_n] if m != rep_n]  # rep first, then sorted
        seen, refs, variants = set(), [], set()
        for m in members:
            r = by[m]
            if m != rep_n:
                variants.add(norm(r["driver_name"]))
            for v in (r.get("same_as_variants") or []):
                if norm(v):
                    variants.add(norm(v))
            for e in (r.get("evidence_refs") or []):
                k = key5(e)
                if k not in seen:
                    seen.add(k)
                    refs.append(e)
        variants.discard(rep_n)
        refs.sort(key=key5)
        links, _ = merge_optional_links([by[m].get("optional_links") for m in members])
        reps.append({"driver_name": by[rep_n]["driver_name"],
                     "canonical_name": by[rep_n]["driver_name"],
                     "companies": companies_of(refs),
                     "evidence_refs": refs,
                     "same_as_variants": sorted(variants),
                     "optional_links": links})
    counts = {"kept_count": len(reps),
              "skips_count": len(cat.get("skips") or []),
              "unresolved_rewrites_count": len(cat.get("unresolved_rewrites") or []),
              "unresolved_same_name_count": len(cat.get("unresolved_same_name") or [])}
    return reps, counts


def part_a(parent_run_dir, scope_name, scope_level, children, max_records=None, max_chars=None):
    parent = Path(parent_run_dir)
    parent.mkdir(parents=True, exist_ok=True)   # fresh parent run dir (orchestrator passes a new path)
    dirs = sorted((Path(c) for c in children), key=lambda p: p.name)
    if len({d.name for d in dirs}) != len(dirs):
        raise SystemExit("FOLD FAIL: duplicate child_run_id basenames among --children")

    by_name, manifest = {}, []
    for d in dirs:
        cat = json.load(open(d / "catalog.json"))
        reps, counts = collapse_child(cat, child_id=d.name)
        manifest.append({"child_run_id": d.name,
                         "scope_name": cat.get("industry") or cat.get("scope_name"),
                         **counts})
        for r in reps:
            by_name.setdefault(norm(r["driver_name"]), []).append((d.name, r))

    passthrough, queue = [], []
    for n in sorted(by_name):
        occ = by_name[n]
        if len(occ) == 1:
            passthrough.append(occ[0][1])
        else:
            queue.append({"name": n, "occurrences": [
                {"child_run_id": cid, "record": r} for cid, r in occ]})

    all_records = passthrough + [o["record"] for q in queue for o in q["occurrences"]]
    guard_seed_max(all_records, max_records, max_chars)   # §11.11 — BEFORE any write

    (parent / "fold_queue.json").write_text(serialize({"queue": queue}))
    (parent / "fold_passthrough.json").write_text(serialize({"records": passthrough}))
    (parent / "fold_manifest.json").write_text(serialize(
        {"scope_name": scope_name, "scope_level": scope_level, "children": manifest}))
    collision_names = sorted(q["name"] for q in queue)
    meta = {q["name"]: {"n_companies": len({norm(c) for o in q["occurrences"]
                                            for c in (o["record"].get("companies") or [])}),
                        "n_children": len(q["occurrences"])} for q in queue}
    return {"passthrough": len(passthrough), "collisions": len(queue), "children": len(dirs),
            "collision_names": collision_names,
            "collision_meta": {n: meta[n] for n in collision_names}}


# ---------------------------------------------------------------- draw (§12.8)

def _company_priority(refs):
    """§12.8.4 within-company order: one ref per distinct source_type first (types sorted,
    each type's earliest date, empty date FIRST), then earliest remaining, then latest
    remaining, then the rest in canonical 5-tuple order."""
    remaining = sorted(refs, key=key5)
    picked = []
    for t in sorted({norm(r.get("source_type")) for r in remaining}):
        best = min((r for r in remaining if norm(r.get("source_type")) == t),
                   key=lambda r: (norm(r.get("date")), key5(r)))
        picked.append(best)
        remaining.remove(best)
    if remaining:
        best = min(remaining, key=lambda r: (norm(r.get("date")), key5(r)))
        picked.append(best)
        remaining.remove(best)
    if remaining:
        maxd = max(norm(r.get("date")) for r in remaining)
        best = next(r for r in remaining if norm(r.get("date")) == maxd)  # tie -> canonical order
        picked.append(best)
        remaining.remove(best)
    return picked + remaining


def side_sequence(refs):
    """§12.8 full per-side sequence: company round-robin, companies ascending per-company
    ref count (tie -> lexicographic company)."""
    groups = {}
    for r in sorted(refs, key=key5):
        groups.setdefault(norm(r.get("company")), []).append(r)
    order = sorted(groups, key=lambda c: (len(groups[c]), c))
    pri = {c: _company_priority(groups[c]) for c in order}
    seq, i = [], 0
    while any(i < len(pri[c]) for c in order):
        for c in order:
            if i < len(pri[c]):
                seq.append(pri[c][i])
        i += 1
    return seq


def draw_views(queue_obj, cap=None):
    cap = RECONCILE_EVIDENCE_PER_RECORD if cap is None else cap
    items = []
    for item in (queue_obj.get("queue") or []):
        sides = []
        for o in (item.get("occurrences") or []):
            seq = side_sequence((o.get("record") or {}).get("evidence_refs") or [])
            sides.append((str(o.get("child_run_id")), seq))
        sides.sort(key=lambda s: (len(s[1]), s[0]))           # smallest side FIRST
        items.append({"name": item.get("name"), "sides": [
            {"side_key": k, "view1": seq[:cap], "view2": seq[cap:2 * cap],
             "total_refs": len(seq)} for k, seq in sides]})
    return {"items": items}


def draw(parent_run_dir, cap=None):
    parent = Path(parent_run_dir)
    queue_obj = json.load(open(parent / "fold_queue.json"))
    views = draw_views(queue_obj, cap)
    (parent / "fold_queue_views.json").write_text(serialize(views))
    return {"items": len(views["items"])}


# ---------------------------------------------------------------- part B (§11.7 Part B)

def _apply_split(name, entry, occs):
    """§11.6 assignment map -> split records. Every from-ref assigned EXACTLY once."""
    tos = list(entry.get("to") or [])
    if not tos:
        raise SystemExit(f"FOLD PART-B FAIL: split for '{name}' has an empty to[] list")
    if len(set(map(norm, tos))) != len(tos):
        raise SystemExit(f"FOLD PART-B FAIL: split for '{name}' repeats a target name")
    for t in tos:
        if not t or norm(t) != t:
            raise SystemExit(f"FOLD PART-B FAIL: split target '{t}' is not lower_snake "
                             f"(norm(name) must equal name)")
    occ_by = {str(o.get("child_run_id")): o for o in occs}
    rows_by_child = {}
    for a in (entry.get("assignments") or []):
        cid = str(a.get("child_run_id"))
        if cid not in occ_by:
            raise SystemExit(f"FOLD PART-B FAIL: split '{name}' assignment for unknown child '{cid}'")
        if a.get("to") not in tos:
            raise SystemExit(f"FOLD PART-B FAIL: split '{name}' assignment target "
                             f"'{a.get('to')}' not in to[]")
        rows_by_child.setdefault(cid, []).append(a)

    assigned = {}  # key5 -> [to, ref]
    for cid in sorted(occ_by):
        refs = (occ_by[cid].get("record") or {}).get("evidence_refs") or []
        rows = rows_by_child.get(cid)
        if not rows:
            raise SystemExit(f"FOLD PART-B FAIL: split '{name}': child '{cid}' refs "
                             f"unassigned (none may be lost)")
        defaults = [r for r in rows if not r.get("evidence_ref_keys")]
        covered = {}
        if defaults:
            if len(rows) > 1:
                raise SystemExit(f"FOLD PART-B FAIL: split '{name}': child '{cid}' default "
                                 f"assignment mixed with other rows (refs would be duplicated)")
            for e in refs:
                covered[key5(e)] = (defaults[0]["to"], e)
        else:
            ref_by_key = {key5(e): e for e in refs}
            for row in rows:
                for arr in row["evidence_ref_keys"]:
                    if not isinstance(arr, list) or len(arr) != 5:
                        raise SystemExit(f"FOLD PART-B FAIL: split '{name}': evidence_ref_key "
                                         f"must be a 5-tuple array, got {arr!r}")
                    k = (norm(arr[0]), norm(arr[1]), norm(arr[2]), norm(arr[3]),
                         (arr[4] or "").strip())
                    if k not in ref_by_key:
                        raise SystemExit(f"FOLD PART-B FAIL: split '{name}': evidence_ref_key "
                                         f"{arr!r} matches no ref of child '{cid}'")
                    if k in covered:
                        raise SystemExit(f"FOLD PART-B FAIL: split '{name}': ref {arr!r} "
                                         f"assigned twice within child '{cid}' (duplicated)")
                    covered[k] = (row["to"], ref_by_key[k])
            missing = sorted(set(ref_by_key) - set(covered))
            if missing:
                raise SystemExit(f"FOLD PART-B FAIL: split '{name}': {len(missing)} ref(s) of "
                                 f"child '{cid}' unassigned (lost): {missing[:3]}")
        for k, (to, e) in covered.items():
            if k in assigned and assigned[k][0] != to:
                raise SystemExit(f"FOLD PART-B FAIL: split '{name}': identical ref assigned to "
                                 f"two targets ('{assigned[k][0]}' and '{to}') — duplicated")
            assigned.setdefault(k, (to, e))

    out = []
    for t in tos:
        refs = sorted((e for k, (to, e) in assigned.items() if to == t), key=key5)
        if not refs:
            raise SystemExit(f"FOLD PART-B FAIL: split '{name}': target '{t}' received zero "
                             f"refs (empty record cannot ship)")
        out.append({"driver_name": t, "canonical_name": t, "companies": companies_of(refs),
                    "evidence_refs": refs, "same_as_variants": [],
                    "optional_links": dict(ALL_NULL_LINKS)})
    return out


def part_b(parent_run_dir, review, max_records=None, max_chars=None):
    parent = Path(parent_run_dir)
    passthrough = json.load(open(parent / "fold_passthrough.json"))["records"]
    queue = json.load(open(parent / "fold_queue.json"))["queue"]
    manifest = json.load(open(parent / "fold_manifest.json"))

    rev_by = {}
    for rv in (review.get("reviews") or []):
        n = norm(rv.get("collision_name"))
        if not n:
            raise SystemExit("FOLD PART-B FAIL: review entry missing collision_name")
        if n in rev_by:
            raise SystemExit(f"FOLD PART-B FAIL: duplicate review for '{n}'")
        rev_by[n] = rv
    qnames = {norm(q["name"]) for q in queue}
    missing = sorted(qnames - set(rev_by))
    extra = sorted(set(rev_by) - qnames)
    if missing:
        raise SystemExit(f"FOLD PART-B FAIL: queue items without a review (fail-close): {missing}")
    if extra:
        raise SystemExit(f"FOLD PART-B FAIL: reviews for non-queued names: {extra}")

    splits_by_from = {}
    for s in (review.get("split_map") or []):
        f = norm(s.get("from"))
        if f in splits_by_from:
            raise SystemExit(f"FOLD PART-B FAIL: duplicate split_map entry for '{f}'")
        splits_by_from[f] = s
    different = {n for n, rv in rev_by.items() if rv.get("verdict") == "DIFFERENT"}
    unused = sorted(set(splits_by_from) - different)
    if unused:
        raise SystemExit(f"FOLD PART-B FAIL: split_map entries without a DIFFERENT verdict: {unused}")

    records = [dict(r) for r in passthrough]
    parks, conflicts = [], []
    for q in sorted(queue, key=lambda q: norm(q["name"])):
        n, rv = norm(q["name"]), rev_by[norm(q["name"])]
        occs = sorted(q["occurrences"], key=lambda o: str(o.get("child_run_id")))
        verdict = rv.get("verdict")
        if verdict == "SAME":
            if rv.get("refute_survived") is not True:
                raise SystemExit(f"FOLD PART-B FAIL: SAME verdict for '{n}' lacks "
                                 f"refute_survived: true (fail-close — the union is a fusion)")
            seen, refs, variants = set(), [], set()
            for o in occs:
                r = o["record"]
                for v in (r.get("same_as_variants") or []):
                    if norm(v):
                        variants.add(norm(v))
                for e in (r.get("evidence_refs") or []):
                    k = key5(e)
                    if k not in seen:
                        seen.add(k)
                        refs.append(e)
            variants.discard(n)
            refs.sort(key=key5)
            links, confs = merge_optional_links([o["record"].get("optional_links") for o in occs])
            for k, vals in confs:
                conflicts.append({"driver_name": n, "key": k, "values": vals})
            records.append({"driver_name": n, "canonical_name": n,
                            "companies": companies_of(refs), "evidence_refs": refs,
                            "same_as_variants": sorted(variants), "optional_links": links})
        elif verdict == "DIFFERENT":
            entry = splits_by_from.get(n)
            if entry is None:
                raise SystemExit(f"FOLD PART-B FAIL: DIFFERENT verdict for '{n}' has no "
                                 f"split_map entry")
            records.extend(_apply_split(n, entry, occs))
        elif verdict == "UNCLEAR":
            parks.append({"name": n, "occurrences": [
                {"child_run_id": str(o.get("child_run_id")),
                 "evidence_refs": o["record"].get("evidence_refs") or []} for o in occs],
                "why": rv.get("why") or ""})
        else:
            raise SystemExit(f"FOLD PART-B FAIL: unknown verdict '{verdict}' for '{n}' (fail-close)")

    names = [norm(r["driver_name"]) for r in records]
    dups = sorted({x for x in names if names.count(x) > 1})
    if dups:
        raise SystemExit(f"FOLD PART-B FAIL: duplicate driver_name in the assembled seed: {dups}")
    records.sort(key=lambda r: norm(r["driver_name"]))
    for r in records:
        r["evidence_refs"] = sorted(r["evidence_refs"], key=key5)

    guard_seed_max(records, max_records, max_chars)       # §11.11 — same guard, final seed

    seed = {"scope_name": manifest.get("scope_name"), "scope_level": manifest.get("scope_level"),
            "run_id": parent.name, "catalog": records,
            "analysis": {"total_distinct_drivers": len(records),
                         "from_children": len(manifest.get("children") or [])}}
    blob = serialize(seed)
    (parent / "seed.json").write_text(blob)
    (parent / "fold_sidecars.json").write_text(serialize(
        {"unresolved_same_name": parks, "optional_links_conflicts": conflicts}))
    return {"records": len(records), "parks": len(parks), "conflicts": len(conflicts),
            "seed_sha256": hashlib.sha256(blob.encode("utf-8")).hexdigest()}


# ---------------------------------------------------------------- CLI (thin)

def main(argv=None):
    ap = argparse.ArgumentParser(description="Deterministic fold combine (§11.7) + §12.8 draw")
    sub = ap.add_subparsers(dest="mode", required=True)
    a = sub.add_parser("part-a")
    a.add_argument("parent_run_dir")
    a.add_argument("--scope-name", required=True)
    a.add_argument("--scope-level", required=True, choices=["sector", "global"])
    a.add_argument("--children", nargs="+", required=True)
    a.add_argument("--max-records", type=int, default=None)
    a.add_argument("--max-chars", type=int, default=None)
    d = sub.add_parser("draw")
    d.add_argument("parent_run_dir")
    d.add_argument("--cap", type=int, default=None)
    b = sub.add_parser("part-b")
    b.add_argument("parent_run_dir")
    b.add_argument("--review", required=True)
    b.add_argument("--max-records", type=int, default=None)
    b.add_argument("--max-chars", type=int, default=None)
    args = ap.parse_args(argv)

    if args.mode == "part-a":
        summary = part_a(args.parent_run_dir, args.scope_name, args.scope_level,
                         args.children, args.max_records, args.max_chars)
    elif args.mode == "draw":
        summary = draw(args.parent_run_dir, args.cap)
    else:
        review = json.load(open(args.review))
        summary = part_b(args.parent_run_dir, review, args.max_records, args.max_chars)
    if getattr(args, "max_records", None) is not None:
        summary["max_records"] = args.max_records
    if getattr(args, "max_chars", None) is not None:
        summary["max_chars"] = args.max_chars
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
