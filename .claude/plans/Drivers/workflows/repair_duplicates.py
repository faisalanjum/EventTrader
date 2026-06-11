#!/usr/bin/env python3
"""
Duplicate repair pass (§13.2): deterministic suggestion + deterministic apply.

ZERO meaning judgment. Code suggests possible missed duplicates; AI review decides SAME or not.
Approved SAME pairs are appended to decisions.json and the existing assemble_catalog.py writer is
re-run. Validator remains the shipping gate.
"""
import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

from assemble_catalog import assemble, serialize, verify_expect
from fold_catalogs import (RECONCILE_EVIDENCE_PER_RECORD, key5, norm, require_validated,
                           side_sequence)

EMBED_MODEL = "text-embedding-3-large"


def tokens(name):
    return {t for t in norm(name).split("_") if t}


def self_records(cat):
    return [r for r in (cat.get("catalog") or [])
            if isinstance(r, dict) and norm(r.get("driver_name"))
            and norm(r.get("driver_name")) == norm(r.get("canonical_name"))]


def canonical_pick(a, b):
    """Cosmetic deterministic pick; membership is the real decision."""
    return min([a, b], key=lambda x: (len(norm(x)), norm(x)))


def already_linked(cat, a, b):
    ca, cb = norm(a), norm(b)
    by = {norm(r.get("driver_name")): r for r in cat.get("catalog") or []}
    ra, rb = by.get(ca), by.get(cb)
    if not ra or not rb:
        return False
    cluster_a = {ca} | {norm(v) for v in (ra.get("same_as_variants") or [])}
    cluster_b = {cb} | {norm(v) for v in (rb.get("same_as_variants") or [])}
    return bool(cluster_a & cluster_b)


def evidence_view(rec):
    refs = side_sequence(rec.get("evidence_refs") or [])[:RECONCILE_EVIDENCE_PER_RECORD]
    return {"driver_name": rec.get("driver_name"),
            "companies": rec.get("companies") or [],
            "same_as_variants": rec.get("same_as_variants") or [],
            "evidence_refs": refs}


def repair_text(rec):
    refs = evidence_view(rec)["evidence_refs"]
    quotes = "\n".join((r.get("quote") or "")[:500] for r in refs[:8])
    return "\n".join([
        f"driver_name: {rec.get('driver_name')}",
        f"same_as_variants: {', '.join(rec.get('same_as_variants') or [])}",
        f"companies: {', '.join(rec.get('companies') or [])}",
        quotes,
    ])


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def embedding_pairs_from_vectors(recs, vectors, top_k=5, min_score=0.72):
    """Embeddings suggest only. They never decide SAME_AS."""
    out = {}
    names = [norm(r.get("driver_name")) for r in recs]
    for i, a in enumerate(names):
        scored = []
        for j, b in enumerate(names):
            if i == j:
                continue
            scored.append((cosine(vectors[i], vectors[j]), a, b))
        for score, x, y in sorted(scored, reverse=True)[:top_k]:
            if score >= min_score:
                out[tuple(sorted((x, y)))] = f"embedding:{score:.4f}"
    return out


def _openai_key():
    key = os.getenv("OPENAI_API_KEY", "")
    if key:
        return key
    env = Path("/home/faisal/EventMarketDB/.env")
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("OPENAI_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def embedding_pairs(recs, top_k=5, min_score=0.72):
    key = _openai_key()
    if not key:
        raise SystemExit("REPAIR FAIL: --use-embeddings requires OPENAI_API_KEY")
    from openai import OpenAI

    texts = [repair_text(r) for r in recs]
    client = OpenAI(api_key=key)
    vectors = []
    for i in range(0, len(texts), 64):
        resp = client.embeddings.create(model=EMBED_MODEL, input=texts[i:i + 64])
        vectors.extend([d.embedding for d in resp.data])
    return embedding_pairs_from_vectors(recs, vectors, top_k=top_k, min_score=min_score)


def load_extra_pairs(path):
    if not path:
        return []
    obj = json.load(open(path))
    rows = obj.get("pairs") if isinstance(obj, dict) else obj
    out = []
    for r in rows or []:
        a, b = r.get("a"), r.get("b")
        if norm(a) and norm(b):
            out.append((a, b, r.get("reason") or "embedding_candidate"))
    return out


def _reason_score(reason):
    if str(reason).startswith("embedding:"):
        try:
            return float(str(reason).split(":", 1)[1])
        except Exception:
            return 0.0
    if str(reason).startswith("token_overlap:"):
        return 0.95
    return 0.5


def suggest(run_dir, min_token_overlap=2, limit=2000, extra_candidates=None,
            use_embeddings=False, embedding_top_k=5, embedding_min_score=0.72):
    run = Path(run_dir)
    cat = json.load(open(run / "catalog.json"))
    recs = sorted(self_records(cat), key=lambda r: norm(r.get("driver_name")))
    by = {norm(r.get("driver_name")): r for r in recs}
    pairs = {}

    # rare-token lane (13.2 graft): "cost" is everywhere but "beef" is rare — one shared RARE token
    # (document frequency <= 5 across candidate names) is as suggestive as two shared common ones.
    df = {}
    for r in recs:
        for t in tokens(r["driver_name"]):
            df[t] = df.get(t, 0) + 1

    for i, a in enumerate(recs):
        ta = tokens(a["driver_name"])
        for b in recs[i + 1:]:
            tb = tokens(b["driver_name"])
            shared = sorted(ta & tb)
            rare = [t for t in shared if df.get(t, 0) <= 5]
            if (len(shared) >= min_token_overlap or rare) and not already_linked(cat, a["driver_name"], b["driver_name"]):
                pairs[(norm(a["driver_name"]), norm(b["driver_name"]))] = \
                    f"token_overlap:{','.join(shared)}"

    for a, b, reason in load_extra_pairs(extra_candidates):
        na, nb = norm(a), norm(b)
        if na in by and nb in by and na != nb and not already_linked(cat, na, nb):
            pairs[tuple(sorted((na, nb)))] = reason

    if use_embeddings and len(recs) > 1:
        for pair, reason in embedding_pairs(recs, embedding_top_k, embedding_min_score).items():
            if pair[0] in by and pair[1] in by and not already_linked(cat, pair[0], pair[1]):
                old = pairs.get(pair)
                pairs[pair] = reason if old is None else f"{old}+{reason}"

    out = []
    ranked = sorted(pairs.items(), key=lambda kv: (-_reason_score(kv[1]), kv[0][0], kv[0][1]))
    clipped = max(0, len(ranked) - limit)   # NO silent caps (13.2 graft): always reported
    for (a, b), reason in ranked[:limit]:
        ra, rb = by[a], by[b]
        n_companies = len({norm(c) for c in (ra.get("companies") or [])}
                          | {norm(c) for c in (rb.get("companies") or [])})
        out.append({"a": ra["driver_name"], "b": rb["driver_name"],
                    "reason": reason, "n_companies": n_companies,
                    "sides": [evidence_view(ra), evidence_view(rb)]})
    blob = {"candidates": out, "count": len(out), "clipped": clipped}
    (run / "repair_candidates.json").write_text(serialize(blob))
    return blob


def apply(run_dir, review_path):
    run = Path(run_dir)
    seed = json.load(open(run / "seed.json"))
    cat = json.load(open(run / "catalog.json"))
    dec_p = run / "decisions.json"
    dec = json.load(open(dec_p))
    review = json.load(open(review_path))
    by = {norm(r.get("driver_name")): r for r in self_records(cat)}
    added, hb = [], []
    existing = {(norm(x.get("variant")), norm(x.get("canonical")))
                for x in (dec.get("approved_same_as") or [])}
    # Stage-0 #7 python backstop: a NEW link may ONLY come from the code-suggested candidate
    # set on disk — no candidates file = no new links (hard fail). Checked AFTER the
    # already_linked no-op, so idempotent crash/resume re-runs never false-stop (suggest()
    # excludes already-linked pairs from later candidate files).
    cand_p = run / "repair_candidates.json"
    cand_pairs = ({frozenset((norm(c.get("a")), norm(c.get("b"))))
                   for c in (json.load(open(cand_p)).get("candidates") or [])}
                  if cand_p.exists() else None)

    for row in review.get("reviews") or []:
        if row.get("verdict") != "SAME":
            continue
        a, b = norm(row.get("a")), norm(row.get("b"))
        if already_linked(cat, a, b):
            continue   # idempotent re-run (crash/resume): pair already in the same cluster -> no-op
        if cand_pairs is None:
            raise SystemExit(f"REPAIR FAIL: cannot add NEW link {a}|{b} — repair_candidates.json "
                             f"missing (links may only come from the code-suggested set; "
                             f"re-run suggest first)")
        if frozenset((a, b)) not in cand_pairs:
            raise SystemExit(f"REPAIR FAIL: SAME pair {a}|{b} was never suggested "
                             f"(not in repair_candidates.json) — review/candidates mismatch")
        if a not in by or b not in by:
            raise SystemExit(f"REPAIR FAIL: SAME pair references non-kept/self-canonical name: {a}|{b}")
        ca = canonical_pick(a, b)
        va = b if ca == a else a
        pair = (va, ca)
        n = len({norm(c) for c in (by[a].get("companies") or [])}
                | {norm(c) for c in (by[b].get("companies") or [])})
        if n >= 8 and row.get("high_blast_refute2_survived") is not True:
            raise SystemExit(f"REPAIR FAIL: high-blast SAME {a}|{b} lacks second-skeptic proof")
        if pair not in existing:
            dec.setdefault("approved_same_as", []).append({"variant": by[va]["driver_name"],
                                                           "canonical": by[ca]["driver_name"]})
            existing.add(pair)
            added.append({"variant": by[va]["driver_name"], "canonical": by[ca]["driver_name"]})
        if n >= 8:
            hb.append({"kind": "link", "a": by[ca]["driver_name"], "b": by[va]["driver_name"],
                       "n": n, "survives": True})

    if hb:
        have = {(norm(x.get("a")), norm(x.get("b"))) for x in dec.get("high_blast_refute2") or []}
        for row in hb:
            key = (norm(row["a"]), norm(row["b"]))
            if key not in have:
                dec.setdefault("high_blast_refute2", []).append(row)
    dec_p.write_text(serialize(dec))
    review_file = run / "same_name_review.json"
    out, approved = assemble(seed, dec, json.load(open(review_file)) if review_file.exists() else None)
    cat_blob = serialize(out)
    (run / "catalog.json").write_text(cat_blob)
    (run / "approved.json").write_text(serialize(approved))
    return {"added": len(added), "links": added,
            "catalog_sha256": hashlib.sha256(cat_blob.encode("utf-8")).hexdigest()}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Driver duplicate repair pass (§13.2)")
    sub = ap.add_subparsers(dest="mode", required=True)
    s = sub.add_parser("suggest")
    s.add_argument("run_dir")
    s.add_argument("--min-token-overlap", type=int, default=2)
    s.add_argument("--limit", type=int, default=2000)
    s.add_argument("--extra-candidates", default=None)
    s.add_argument("--use-embeddings", action="store_true")
    s.add_argument("--embedding-top-k", type=int, default=5)
    s.add_argument("--embedding-min-score", type=float, default=0.72)
    a = sub.add_parser("apply")
    a.add_argument("run_dir")
    a.add_argument("--review", required=True)
    a.add_argument("--expect", default=None,
                   help="Stage-0 #5: rv=..,h32=.. computed by the workflow JS from the review "
                        "SOURCE string; binds the agent-written repair_review.json to it")
    args = ap.parse_args(argv)
    if args.mode == "suggest":
        # Stage-0 #1: repair builds ON the catalog — refuse unless its last validation
        # passed and the catalog/approved bytes are unchanged since (sidecar binding).
        require_validated(args.run_dir)
        out = suggest(args.run_dir, args.min_token_overlap, args.limit, args.extra_candidates,
                      args.use_embeddings, args.embedding_top_k, args.embedding_min_score)
    else:
        if args.expect:
            review_raw = Path(args.review).read_text()
            verify_expect(args.expect, review_raw,
                          {"rv": len(json.loads(review_raw).get("reviews") or [])},
                          "REPAIR repair_review.json")
        out = apply(args.run_dir, args.review)
    print(json.dumps(out, sort_keys=True))


if __name__ == "__main__":
    main()
