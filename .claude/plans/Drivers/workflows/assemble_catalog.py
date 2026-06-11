#!/usr/bin/env python3
"""
Deterministic catalog assembly — the §11.19 writer (HierarchicalCatalogPlan, 10th pass).

Ports reconcile.js:89-94's 5-way record precedence VERBATIM (§12.7):
  1. gate skip                                   -> skips[]                 (skip WINS)
  2. approved SAME_AS whose canonical is KEPT    -> canonical_name = canonical
  3. approved rewrite whose target is KEPT       -> canonical_name = target
  4. parked rewrite                              -> unresolved_rewrites[]
  5. otherwise                                   -> self-canonical (admit)
KEPT = seed names − skipped − parked (§12.7 flat lookup, no 3-list join).

ZERO judgment: this CLI only applies the skeptic-approved decision lists to seed.json.
Records are copied VERBATIM except canonical_name (+ the same_as_variants mirror, §3e/§11.5).
The AI never reads the full seed (§11.11): seed.json is read from DISK; the workflow agents
only transport the SMALL decisions.json (verdict lists, schema-validated).

Usage:  assemble_catalog.py <run_dir> [--review same_name_review.json]
        reads  <run_dir>/seed.json + <run_dir>/decisions.json (+ the optional review file,
               path relative to <run_dir> or absolute)
        writes <run_dir>/catalog.json + <run_dir>/approved.json
        prints the catalog sha256 + counts (the workflow compares/logs them)

decisions.json shape (written by the reconcile workflow from its Refute-filtered lists):
  { "gate_verdicts":   [{driver_name, verdict: admit|rewrite|skip, rewrite_to?, reason}],
    "approved_same_as":[{variant, canonical}],
    "approved_rewrites":[{from, to}],
    "parked_rewrites": [{driver_name, proposed_to, why}] }

--review = the LEAF flag-triggered D5 same-name review (HierarchicalCatalogPlan D5/§3c/
§11.6/§12.4; occurrence key = company). Shape:
  { "reviews":[{collision_name, verdict: SAME|DIFFERENT|UNCLEAR, new_names?, why,
                refute_survived?}],
    "split_map":[{from, to:[names], assignments:[{company, to, evidence_ref_keys?}]}] }
Applied BEFORE the 5-way precedence (it re-shapes the seed records the precedence runs over):
  SAME      -> keep the record as-is; refute_survived: true REQUIRED (fail-close — the
               cross-company union is a fusion).
  DIFFERENT -> REPLACE the record with coined split records per the assignment map
               (default: ALL refs of assignments[].company -> that entry's 'to'; optional
               evidence_ref_keys = normed 5-tuples for finer splits). Every from-ref must
               be assigned EXACTLY once (complete partition — none lost/duplicated).
  UNCLEAR   -> REMOVE the record and park it in the catalog side-list
               unresolved_same_name:[{name, occurrences:[{company, evidence_refs}], why}]
               (key present ONLY when parks exist — Phase-0 outputs stay byte-identical).
Decisions referencing a DIFFERENT-from / parked name, or a coined split target, HARD-FAIL
(the workflow resolves flags BEFORE other decisions; the gate ran before the split).
"""
import hashlib
import json
import sys
from pathlib import Path


def norm(s):  # §12.1 — shared norm(): strip + lowercase (ASCII)
    return (s or "").strip().lower()


def h32(text):
    """Stage-0 write-fidelity hash: 31-polynomial rolling hash over UTF-16 code units,
    mod 2^32 — EXACTLY reproducible in plain workflow JS as
    `let h=0; for (let i=0;i<s.length;i++) h=((Math.imul(h,31)+s.charCodeAt(i))>>>0)`.
    Binds an agent-written file to the JS-side source string. NOT cryptographic (32-bit):
    it reliably catches realistic ACCIDENTAL changes (drop/add/edit/reformat); the section
    row counts + downstream JSON parsing + the validator provide the rest of the net."""
    h = 0
    b = text.encode("utf-16-le")
    for i in range(0, len(b), 2):
        h = (h * 31 + (b[i] | (b[i + 1] << 8))) & 0xFFFFFFFF
    return h


def parse_expect(s):
    """'k=1,h32=123' -> {'k': 1, 'h32': 123} (all values integers)."""
    out = {}
    for part in (s or "").split(","):
        if part.strip():
            k, v = part.split("=", 1)
            out[k.strip()] = int(v)
    return out


def verify_expect(expect_str, raw_text, got_counts, label):
    """Stage-0 #4/#5: compare the agent-WRITTEN file against the JS-computed expectation
    (section row counts + h32 of the exact source string; trailing newlines from the
    Write tool are tolerated — they cannot alter JSON content). Mismatch = SystemExit.
    An expectation without h32 (empty/partial string) is itself a fail — the check must
    never silently self-disable."""
    e = parse_expect(expect_str)
    if "h32" not in e:
        raise SystemExit(f"{label} EXPECT MISMATCH: expectation lacks h32 "
                         f"(empty/partial --expect is not allowed — fail-close): {expect_str!r}")
    got = dict(got_counts)
    got["h32"] = h32(raw_text.rstrip("\n"))
    bad = {k: {"expected": e[k], "got": got.get(k)} for k in e if got.get(k) != e[k]}
    if bad:
        raise SystemExit(f"{label} EXPECT MISMATCH (agent-written file differs from the "
                         f"workflow's source string — relay-write fidelity): {bad}")


def serialize(obj):  # pinned output format: indent=1 (matches fetch), trailing newline
    return json.dumps(obj, indent=1, ensure_ascii=False) + "\n"


ALL_NULL_LINKS = {"xbrl_concept": None, "xbrl_member": None, "guidance_ref": None}


def key5(ref):
    """The exact normed 5-tuple evidence identity (matches the validator's ev_full)."""
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


def decision_names(dec):
    """Every name a decision row references (all name-bearing fields, normed)."""
    names = set()
    for v in (dec.get("gate_verdicts") or []):
        names |= {norm(v.get("driver_name")), norm(v.get("rewrite_to"))}
    for l in (dec.get("approved_same_as") or []):
        names |= {norm(l.get("variant")), norm(l.get("canonical"))}
    for l in (dec.get("approved_rewrites") or []):
        names |= {norm(l.get("from")), norm(l.get("to"))}
    for p in (dec.get("parked_rewrites") or []):
        names |= {norm(p.get("driver_name")), norm(p.get("proposed_to"))}
    names.discard("")
    return names


def ref_indices(rec):
    """Deterministic per-record ref indices: refs sorted by key5 -> 'r1'..'rN'. The SAME
    sort is used by the review's evidence view, so the agent assigns INDICES (pure judgment)
    and code maps them back to refs (pure mechanics) — no 5-tuple copying by an LLM."""
    return {f"r{i}": e for i, e in
            enumerate(sorted((rec.get("evidence_refs") or []), key=key5), 1)}


def _apply_leaf_split(name, entry, rec):
    """§11.6 LEAF assignment map (key = company) -> coined split records. Every ref of the
    from-record assigned EXACTLY once (complete partition — none lost/duplicated/orphaned).
    Assignment rows per company: indexed rows ({company, to, ref_idx:["r3",...]}) and/or keyed
    rows (evidence_ref_keys 5-tuples) claim refs first; at most ONE default row ({company, to})
    per company takes the REMAINDER (deterministic — no ambiguity, no duplication possible)."""
    tos = list(entry.get("to") or [])
    if not tos:
        raise SystemExit(f"ASSEMBLE REVIEW FAIL: split for '{name}' has an empty to[] list")
    if len(set(map(norm, tos))) != len(tos):
        raise SystemExit(f"ASSEMBLE REVIEW FAIL: split for '{name}' repeats a target name")
    for t in tos:
        if not t or norm(t) != t:
            raise SystemExit(f"ASSEMBLE REVIEW FAIL: split target '{t}' is not lower_snake "
                             f"(norm(name) must equal name)")
    idx_map = ref_indices(rec)
    refs_by_company = {}
    for e in (rec.get("evidence_refs") or []):
        refs_by_company.setdefault(norm(e.get("company")), []).append(e)
    rows_by_company = {}
    for a in (entry.get("assignments") or []):
        c = norm(a.get("company"))
        if c not in refs_by_company:
            raise SystemExit(f"ASSEMBLE REVIEW FAIL: split '{name}' assignment for unknown "
                             f"company '{a.get('company')}'")
        if a.get("to") not in tos:
            raise SystemExit(f"ASSEMBLE REVIEW FAIL: split '{name}' assignment target "
                             f"'{a.get('to')}' not in to[]")
        rows_by_company.setdefault(c, []).append(a)

    assigned = {}  # key5 -> (to, ref); company is part of the key, so no cross-company clash
    for c in sorted(refs_by_company):
        rows = rows_by_company.get(c)
        if not rows:
            raise SystemExit(f"ASSEMBLE REVIEW FAIL: split '{name}': company '{c}' refs "
                             f"unassigned (none may be lost)")
        defaults = [r for r in rows if not r.get("evidence_ref_keys") and not r.get("ref_idx")]
        if len(defaults) > 1:
            raise SystemExit(f"ASSEMBLE REVIEW FAIL: split '{name}': company '{c}' has "
                             f"{len(defaults)} default rows — at most ONE remainder row allowed "
                             f"(which refs go where would be ambiguous)")
        covered = {}
        ref_by_key = {key5(e): e for e in refs_by_company[c]}
        for row in rows:
            if row in defaults:
                continue
            for ix in (row.get("ref_idx") or []):
                e = idx_map.get(str(ix).strip())
                if e is None:
                    raise SystemExit(f"ASSEMBLE REVIEW FAIL: split '{name}': unknown ref_idx "
                                     f"'{ix}' (valid: r1..r{len(idx_map)})")
                if norm(e.get("company")) != c:
                    raise SystemExit(f"ASSEMBLE REVIEW FAIL: split '{name}': ref_idx '{ix}' "
                                     f"belongs to company '{e.get('company')}', not '{c}'")
                k = key5(e)
                if k in covered:
                    raise SystemExit(f"ASSEMBLE REVIEW FAIL: split '{name}': ref '{ix}' "
                                     f"assigned twice (duplicated)")
                covered[k] = (row["to"], e)
            for arr in (row.get("evidence_ref_keys") or []):
                if not isinstance(arr, list) or len(arr) != 5:
                    raise SystemExit(f"ASSEMBLE REVIEW FAIL: split '{name}': evidence_ref_key "
                                     f"must be a 5-tuple array, got {arr!r}")
                k = (norm(arr[0]), norm(arr[1]), norm(arr[2]), norm(arr[3]),
                     (arr[4] or "").strip())
                if k not in ref_by_key:
                    raise SystemExit(f"ASSEMBLE REVIEW FAIL: split '{name}': evidence_ref_key "
                                     f"{arr!r} matches no ref of company '{c}'")
                if k in covered:
                    raise SystemExit(f"ASSEMBLE REVIEW FAIL: split '{name}': ref {arr!r} "
                                     f"assigned twice (duplicated)")
                covered[k] = (row["to"], ref_by_key[k])
        remainder = sorted(set(ref_by_key) - set(covered))
        if remainder:
            if not defaults:
                raise SystemExit(f"ASSEMBLE REVIEW FAIL: split '{name}': {len(remainder)} ref(s) "
                                 f"of company '{c}' unassigned (lost): {remainder[:3]}")
            for k in remainder:
                covered[k] = (defaults[0]["to"], ref_by_key[k])
        assigned.update(covered)

    out = []
    for t in tos:
        refs = sorted((e for to, e in assigned.values() if to == t), key=key5)
        if not refs:
            raise SystemExit(f"ASSEMBLE REVIEW FAIL: split '{name}': target '{t}' received zero "
                             f"refs (empty record cannot ship)")
        out.append({"driver_name": t, "canonical_name": t, "companies": companies_of(refs),
                    "evidence_refs": refs, "same_as_variants": [],
                    "optional_links": dict(ALL_NULL_LINKS)})
    return out


def apply_review(recs, review):
    """LEAF flag-triggered D5 (§3c/§11.6/§12.4 — occurrence key = company): re-shape the seed
    records BEFORE the 5-way precedence. Returns (records, parks, removed_names, target_names)."""
    by = {norm(r["driver_name"]): r for r in recs}
    rev_by = {}
    for rv in (review.get("reviews") or []):
        n = norm(rv.get("collision_name"))
        if not n:
            raise SystemExit("ASSEMBLE REVIEW FAIL: review entry missing collision_name")
        if n not in by:
            raise SystemExit(f"ASSEMBLE REVIEW FAIL: collision_name '{n}' is not a seed record name")
        if n in rev_by:
            raise SystemExit(f"ASSEMBLE REVIEW FAIL: duplicate review for '{n}'")
        rev_by[n] = rv

    splits_by_from = {}
    for s in (review.get("split_map") or []):
        f = norm(s.get("from"))
        if f in splits_by_from:
            raise SystemExit(f"ASSEMBLE REVIEW FAIL: duplicate split_map entry for '{f}'")
        splits_by_from[f] = s
    different = {n for n, rv in rev_by.items() if rv.get("verdict") == "DIFFERENT"}
    unused = sorted(set(splits_by_from) - different)
    if unused:
        raise SystemExit(f"ASSEMBLE REVIEW FAIL: split_map entries without a DIFFERENT "
                         f"verdict: {unused}")

    out_recs, parks, removed, targets = [], [], set(), set()
    for r in recs:
        n = norm(r["driver_name"])
        rv = rev_by.get(n)
        if rv is None:
            out_recs.append(r)
            continue
        verdict = rv.get("verdict")
        if verdict == "SAME":
            if rv.get("refute_survived") is not True:
                raise SystemExit(f"ASSEMBLE REVIEW FAIL: SAME verdict for '{n}' lacks "
                                 f"refute_survived: true (fail-close — the union is a fusion)")
            out_recs.append(r)                                    # keep the seed record as-is
        elif verdict == "DIFFERENT":
            entry = splits_by_from.get(n)
            if entry is None:
                raise SystemExit(f"ASSEMBLE REVIEW FAIL: DIFFERENT verdict for '{n}' has no "
                                 f"split_map entry")
            out_recs.extend(_apply_leaf_split(n, entry, r))
            removed.add(n)
            targets |= {norm(t) for t in (entry.get("to") or [])}
        elif verdict == "UNCLEAR":
            occ = {}
            for e in (r.get("evidence_refs") or []):
                occ.setdefault(norm(e.get("company")), []).append(e)
            parks.append({"name": r["driver_name"], "occurrences": [
                {"company": occ[c][0].get("company"), "evidence_refs": occ[c]}
                for c in sorted(occ)], "why": rv.get("why") or ""})
            removed.add(n)
        else:
            raise SystemExit(f"ASSEMBLE REVIEW FAIL: unknown verdict '{verdict}' for '{n}' "
                             f"(fail-close)")
    return out_recs, parks, removed, targets


def assemble(seed, dec, review=None):
    recs = [r for r in (seed.get("catalog") or []) if isinstance(r, dict) and norm(r.get("driver_name"))]
    by = {norm(r["driver_name"]): r for r in recs}
    if len(by) != len(recs):
        raise SystemExit("ASSEMBLE FAIL: duplicate driver_name in seed")

    parks = []
    if review is not None:                       # leaf flag-triggered D5 — BEFORE the precedence
        seed_names = set(by)
        recs, parks, removed, targets = apply_review(recs, review)
        by = {norm(r["driver_name"]): r for r in recs}
        if len(by) != len(recs):
            raise SystemExit("ASSEMBLE REVIEW FAIL: split target collides with another seed name")
        referenced = decision_names(dec)
        bad = sorted(referenced & removed)
        if bad:
            raise SystemExit(f"ASSEMBLE REVIEW FAIL: decision references a name the review "
                             f"split/parked (flags must be resolved BEFORE other decisions): {bad}")
        coined = sorted(referenced & (targets - seed_names))
        if coined:
            raise SystemExit(f"ASSEMBLE REVIEW FAIL: decision references a coined split target "
                             f"(the gate ran before the split): {coined}")

    gate = {norm(v.get("driver_name")): v for v in (dec.get("gate_verdicts") or [])}
    same_as = list(dec.get("approved_same_as") or [])
    rewrites = list(dec.get("approved_rewrites") or [])
    parked = list(dec.get("parked_rewrites") or [])

    # Invariant (the workflow JS guarantees it; fail loud if broken): every gate
    # 'rewrite' verdict must appear in approved_rewrites OR parked_rewrites.
    rw_names = {norm(l.get("from")) for l in rewrites} | {norm(p.get("driver_name")) for p in parked}
    for n, v in gate.items():
        if v.get("verdict") == "rewrite" and n not in rw_names:
            raise SystemExit(f"ASSEMBLE FAIL: gate rewrite for '{n}' missing from approved/parked lists")

    skipped = {n for n, v in gate.items() if v.get("verdict") == "skip"}
    parked_by = {norm(p.get("driver_name")): p for p in parked if norm(p.get("driver_name")) not in skipped}
    kept = {n for n in by if n not in skipped and n not in parked_by}
    sa_map = {norm(l.get("variant")): norm(l.get("canonical")) for l in same_as}
    rw_map = {norm(l.get("from")): norm(l.get("to")) for l in rewrites}

    catalog, skips, unresolved = [], [], []
    counts = {"keep": 0, "same_as": 0, "rewrite": 0, "skip": 0, "unresolved": 0}
    variants = {}  # canonical (norm) -> [seed-exact variant names folded at THIS level]
    # Carried variants (fold-parent seeds): a parent seed record may already hold child
    # same_as_variants (§11.5) — they must be PRESERVED, not rebuilt away (D8 NAMES).
    carried = {norm(r["driver_name"]): list(r.get("same_as_variants") or []) for r in recs}

    def _next_hop(cur):
        """One approved fold step (rule-2 SAME_AS before rule-3 rewrite; KEPT targets only)."""
        t = sa_map.get(cur)
        if t and t != cur and t in kept:
            return t, "same_as"
        t = rw_map.get(cur)
        if t and t != cur and t in kept:
            return t, "rewrite"
        return None, None

    def _star(start):
        """Transitive closure of the Refute-APPROVED links to the self-canonical root — the
        leaf STAR contract (mirrors the fold's §11.7.6 chain-flattening; pure bookkeeping,
        every hop was individually approved). Cycle -> deterministic root: shortest
        seed-exact name, then lexicographic (R6-flavored tie-break)."""
        seen, cur = [start], start
        while True:
            nxt, _ = _next_hop(cur)
            if nxt is None:
                return cur
            if nxt in seen:
                cyc = seen[seen.index(nxt):]
                return min(cyc, key=lambda x: (len(by[x]["driver_name"]), x))
            seen.append(nxt)
            cur = nxt

    for r in sorted(recs, key=lambda r: norm(r["driver_name"])):
        n = norm(r["driver_name"])
        if n in skipped:                                              # 1. skip WINS
            counts["skip"] += 1
            skips.append({"driver_name": r["driver_name"],
                          "why": (gate.get(n) or {}).get("reason") or "gate skip"})
            continue
        canon = _star(n)                                              # 2+3. approved folds, STAR-flattened
        if canon != n:
            _, hop_kind = _next_hop(n)
            counts[hop_kind] += 1
            variants.setdefault(canon, []).append(r["driver_name"])
        elif n in parked_by:                                          # 4. parked rewrite
            p = parked_by[n]
            counts["unresolved"] += 1
            unresolved.append({"driver_name": r["driver_name"],
                               "proposed_to": p.get("proposed_to") or "",
                               "why": p.get("why") or "unverified by skeptic"})
            continue
        else:                                                          # 5. admit self-canonical
            counts["keep"] += 1
        catalog.append({
            "driver_name": r["driver_name"],
            "canonical_name": by[canon]["driver_name"],   # seed-exact string, case-safe
            "companies": r.get("companies"),
            "evidence_refs": r.get("evidence_refs"),
            "same_as_variants": [],                       # mirror filled below
            "optional_links": r.get("optional_links"),
        })

    for cr in catalog:
        nm = norm(cr["driver_name"])
        cr["same_as_variants"] = sorted(set(carried.get(nm, [])) | set(variants.get(nm, [])))

    out = {"industry": seed.get("industry"), "catalog": catalog, "skips": skips,
           "unresolved_rewrites": unresolved}
    if parks:                # ONLY when --review produced parks — Phase-0 stays byte-identical
        out["unresolved_same_name"] = parks
    out["counts"] = counts
    approved = {"same_as": [{"variant": l.get("variant"), "canonical": l.get("canonical")} for l in same_as],
                "rewrites": [{"from": l.get("from"), "to": l.get("to")} for l in rewrites],
                # 12th pass rev2: the high-blast second-skeptic PROOF rides decisions.json and is
                # code-copied here so the validator can enforce it from disk (pure code, no relay).
                "high_blast_refute2": list((dec or {}).get("high_blast_refute2") or [])}
    return out, approved


def main():
    args, review_p, expect_p, expect_rv, i = [], None, None, None, 1
    while i < len(sys.argv):
        if sys.argv[i] == "--review" and i + 1 < len(sys.argv):
            review_p = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--expect" and i + 1 < len(sys.argv):
            expect_p = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--expect-review" and i + 1 < len(sys.argv):
            expect_rv = sys.argv[i + 1]
            i += 2
        else:
            args.append(sys.argv[i])
            i += 1
    if len(args) != 1:
        print("Usage: assemble_catalog.py <run_dir> [--review same_name_review.json] "
              "[--expect gv=..,sa=..,rw=..,pk=..,hb=..,h32=..] [--expect-review rv=..,sm=..,h32=..]",
              file=sys.stderr)
        sys.exit(2)
    run = Path(args[0])
    seed = json.load(open(run / "seed.json"))
    dec_raw = (run / "decisions.json").read_text()
    dec = json.loads(dec_raw)
    review, review_raw = None, None
    if review_p is not None:                     # path relative to run_dir, or absolute
        rp = Path(review_p)
        review_raw = (rp if rp.is_absolute() else run / rp).read_text()
        review = json.loads(review_raw)

    # Stage-0 #4/#5: relay-write fidelity — the agent re-typed these files from the workflow's
    # JS strings; the counts + h32 expectations are computed in JS from the SOURCE strings.
    if expect_p is not None:
        verify_expect(expect_p, dec_raw,
                      {"gv": len(dec.get("gate_verdicts") or []),
                       "sa": len(dec.get("approved_same_as") or []),
                       "rw": len(dec.get("approved_rewrites") or []),
                       "pk": len(dec.get("parked_rewrites") or []),
                       "hb": len(dec.get("high_blast_refute2") or [])},
                      "ASSEMBLE decisions.json")
    if expect_rv is not None:
        if review_raw is None:
            raise SystemExit("ASSEMBLE FAIL: --expect-review given without --review")
        verify_expect(expect_rv, review_raw,
                      {"rv": len(review.get("reviews") or []),
                       "sm": len(review.get("split_map") or [])},
                      "ASSEMBLE same_name_review.json")

    # Stage-0 #3: gate coverage — every seed driver_name must carry a gate verdict, or be
    # RESHAPED by the same-name review (DIFFERENT split / UNCLEAR park, whose gate verdicts
    # the workflow deliberately filters out). A SAME-kept review name is NOT excused: in the
    # real flow it keeps its gate verdict, so a missing one means a dropped gate batch —
    # the verified slice-subset hole. CLI-level: the production entry point is this CLI.
    seed_names = {norm(r.get("driver_name")) for r in (seed.get("catalog") or [])
                  if isinstance(r, dict) and norm(r.get("driver_name"))}
    gate_names = {norm(v.get("driver_name")) for v in (dec.get("gate_verdicts") or [])}
    review_names = {norm(rv.get("collision_name"))
                    for rv in ((review or {}).get("reviews") or [])
                    if rv.get("verdict") != "SAME"}
    unreviewed = sorted(seed_names - gate_names - review_names)
    if unreviewed:
        raise SystemExit(f"ASSEMBLE FAIL: {len(unreviewed)} seed record(s) have NO gate verdict "
                         f"and no same-name review — un-reviewed names cannot ship "
                         f"(dropped review batch?): {unreviewed[:10]}")

    out, approved = assemble(seed, dec, review)
    cat_blob = serialize(out)
    (run / "catalog.json").write_text(cat_blob)
    (run / "approved.json").write_text(serialize(approved))
    sha = hashlib.sha256(cat_blob.encode("utf-8")).hexdigest()
    c = out["counts"]
    extra = (f" unresolved_same_name={len(out.get('unresolved_same_name') or [])}"
             if review is not None else "")
    print(f"ASSEMBLED catalog.json sha256={sha} | keep={c['keep']} same_as={c['same_as']} "
          f"rewrite={c['rewrite']} skip={c['skip']} unresolved={c['unresolved']}{extra} "
          f"| approved.json written")


if __name__ == "__main__":
    main()
