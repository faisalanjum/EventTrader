#!/usr/bin/env python3
"""
Deterministic seed grouping + write (E1/E2 + §11.14; HierarchicalCatalogPlan 11th-pass code-write).

Replaces menu_build.js's in-JS Converge grouping so seed.json is written BY CODE (E2)
and the grouping logic is pytest-able (structure -> code; the AI never transports the seed):
  - reads  <run_dir>/menus/*.json  (one file per blind bot; aggregated by the `ticker` FIELD,
    so per-chunk files like TICK__chunk_003.json work unchanged in Phase 0.5)
  - groups candidates by norm()'d driver_name; the record's final driver_name IS the
    lowercased form (E1 + §11.14)
  - unions evidence_refs, dedup by the exact 5-tuple; companies = sorted distinct
  - first non-null xbrl (ticker-sorted, candidate order) -> optional_links.xbrl_concept
  - writes <run_dir>/seed.json (sorted by driver_name) + prints a one-line JSON summary
    {seed_sha256, total_distinct_drivers, total_candidates, per_ticker, file}
  - --expect '{"TICK": n, ...}' cross-checks per-ticker raw candidate counts against the
    workflow's schema-validated structured outputs; mismatch = exit 1 (fail-loud)

Usage: build_seed.py <run_dir> --industry NAME --slug SLUG --run-id RUN_ID [--expect JSON]
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path


def norm(s):  # §12.1 shared norm(): strip + lowercase (ASCII)
    return (s or "").strip().lower()


def serialize(obj):
    return json.dumps(obj, indent=1, ensure_ascii=False) + "\n"


def build_seed(run_dir, industry, slug, run_id):
    run_dir = Path(run_dir)
    files = sorted((run_dir / "menus").glob("*.json"))
    if not files:
        raise SystemExit(f"BUILD_SEED FAIL: no menu files in {run_dir / 'menus'}")
    # Stage-0 #2: chunk coverage against BOTH code-written ground truths (never an agent
    # relay): the chunks/ dir (covers KPI-only chunks, which have zero manifest rows) UNION
    # chunks_manifest.json rows (covers a chunk file deleted after chunking). Every chunk
    # must have been read into a menu, and no stale menus may contaminate the seed.
    chunks_dir = run_dir / "chunks"
    manifest_p = run_dir / "chunks_manifest.json"
    if chunks_dir.exists() or manifest_p.exists():
        want = {p.stem for p in chunks_dir.glob("*.json")} if chunks_dir.exists() else set()
        if manifest_p.exists():
            want |= {str(r.get("chunk_id")) for r in
                     (json.loads(manifest_p.read_text()).get("rows") or []) if r.get("chunk_id")}
        got = {p.stem for p in files}
        if want != got:
            raise SystemExit(f"BUILD_SEED FAIL: menus/ != chunks (dir ∪ manifest) — every chunk "
                             f"needs exactly one menu; missing={sorted(want - got)}, "
                             f"stale_extra={sorted(got - want)}")
    menus = [json.loads(f.read_text()) for f in files]
    menus.sort(key=lambda m: (str(m.get("ticker") or ""),))

    by = {}           # norm name -> record
    seen = {}         # norm name -> set of 5-tuples
    per_ticker = {}   # raw candidate counts (incl. blanks? no — blanks aren't candidates we count)
    total_candidates = 0
    for m in menus:
        tk = str(m.get("ticker") or "").strip()
        for c in (m.get("candidates") or []):
            k = norm(c.get("driver_name"))
            if not k:
                continue
            per_ticker[tk] = per_ticker.get(tk, 0) + 1
            total_candidates += 1
            r = by.get(k)
            if r is None:
                r = by[k] = {"driver_name": k, "canonical_name": k, "companies": set(),
                             "evidence_refs": [],
                             "optional_links": {"xbrl_concept": None, "xbrl_member": None,
                                                "guidance_ref": None}}
                seen[k] = set()
            r["companies"].add(tk)
            ref = {"company": tk, "source_type": c.get("source_type"),
                   "source_id": c.get("source_id"), "date": c.get("date"),
                   "quote": c.get("evidence_quote")}
            key5 = (norm(ref["company"]), norm(ref["source_type"]), norm(ref["source_id"]),
                    norm(ref["date"]), (ref["quote"] or "").strip())
            if key5 not in seen[k]:
                seen[k].add(key5)
                r["evidence_refs"].append(ref)
            xb = (c.get("xbrl_or_null") or "").strip()
            if xb and xb.lower() != "null" and not r["optional_links"]["xbrl_concept"]:
                r["optional_links"]["xbrl_concept"] = xb

    catalog = []
    for k in sorted(by):
        r = by[k]
        catalog.append({"driver_name": r["driver_name"], "canonical_name": r["canonical_name"],
                        "companies": sorted(r["companies"]), "evidence_refs": r["evidence_refs"],
                        "optional_links": r["optional_links"]})
    shared = [{"driver_name": r["driver_name"], "companies": r["companies"]}
              for r in catalog if len(r["companies"]) >= 2]
    return {"industry": industry, "slug": slug, "run_id": run_id, "catalog": catalog,
            "analysis": {"shared_drivers": shared, "total_distinct_drivers": len(catalog),
                         "total_candidates": total_candidates}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--industry", required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--expect", help="JSON {ticker: raw_candidate_count} cross-check")
    a = ap.parse_args()

    seed = build_seed(a.run_dir, a.industry, a.slug, a.run_id)

    per_ticker = {}
    for r in seed["catalog"]:
        for e in r["evidence_refs"]:
            pass  # per-ticker counts come from raw candidates, recomputed below
    # recompute raw per-ticker counts the same way build_seed did
    files = sorted((Path(a.run_dir) / "menus").glob("*.json"))
    for f in files:
        m = json.loads(f.read_text())
        tk = str(m.get("ticker") or "").strip()
        n = sum(1 for c in (m.get("candidates") or []) if norm(c.get("driver_name")))
        per_ticker[tk] = per_ticker.get(tk, 0) + n

    if a.expect:
        expect = {str(k): int(v) for k, v in json.loads(a.expect).items()}
        if expect != per_ticker:
            print(f"BUILD_SEED EXPECT MISMATCH: expected {expect} got {per_ticker}", file=sys.stderr)
            sys.exit(1)

    blob = serialize(seed)
    out = Path(a.run_dir) / "seed.json"
    out.write_text(blob)
    sha = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    print(json.dumps({"seed_sha256": sha, "total_distinct_drivers": seed["analysis"]["total_distinct_drivers"],
                      "total_candidates": seed["analysis"]["total_candidates"],
                      "per_ticker": per_ticker, "file": str(out)}))


if __name__ == "__main__":
    main()
