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

from assemble_catalog import assemble, h32, serialize, verify_expect

# C5 §8d GO condition #2 — production canary sizing (batched lane only): ~2% of the
# batched DIFFERENT/UNCLEAR rows, floor 5, clipped to the eligible pool. Mirrored
# EXACTLY in repair_duplicates.js (sample key = h32(norm(a)|norm(b)), idx tie-break).
CANARY_RATE = 0.02
CANARY_MIN = 5
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


def embedding_pairs_from_vectors(recs, vectors, top_k=5, min_score=0.60):
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


def embedding_pairs(recs, top_k=5, min_score=0.60):
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
            use_embeddings=False, embedding_top_k=5, embedding_min_score=0.60):
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
    eff_limit = len(ranked) if (limit is None or limit <= 0) else limit   # <=0 = NO CAP (C5 batched mode)
    clipped = max(0, len(ranked) - eff_limit)   # NO silent caps (13.2 graft): always reported
    for (a, b), reason in ranked[:eff_limit]:
        ra, rb = by[a], by[b]
        n_companies = len({norm(c) for c in (ra.get("companies") or [])}
                          | {norm(c) for c in (rb.get("companies") or [])})
        out.append({"a": ra["driver_name"], "b": rb["driver_name"],
                    "reason": reason, "n_companies": n_companies,
                    "sides": [evidence_view(ra), evidence_view(rb)]})
    # stale C5 plan artifacts from a prior (possibly crashed) batched run must never
    # survive a fresh suggest — apply's P2 would false-stop a per-pair re-run on them.
    plan_p = run / "repair_plan.json"
    if plan_p.exists():
        plan_p.unlink()
    bdir = run / "repair_batches"
    if bdir.is_dir():
        for f in bdir.glob("batch_*.json"):
            f.unlink()
    blob = {"candidates": out, "count": len(out), "clipped": clipped,
            # round-3 review fix: echo the params ACTUALLY used — the workflow asserts they
            # match what it commanded (a relay-dropped flag = smaller-but-honest set whose
            # hashes pass; this makes the mode mismatch loud).
            "limit_used": limit, "use_embeddings": bool(use_embeddings),
            # C5-study today-bug fix: the workflow relays this whole blob through one agent
            # reply; these code-computed hashes let the JS verify the relayed copy is the
            # EXACT printed truth (pair list AND full content) — an abridged/mutated relay
            # can no longer silently skip or mislead judges.
            "pairs_h32": h32("\n".join(f"{c['a']}|{c['b']}" for c in out)),
            "cands_h32": h32(json.dumps(out, sort_keys=True, separators=(",", ":"),
                                        ensure_ascii=False))}
    (run / "repair_candidates.json").write_text(serialize(blob))
    return blob


def _load_pinned_candidates(run):
    """The ONE pinned candidates file every batched artifact derives from (§C5: no
    regeneration between pages)."""
    cand_p = Path(run) / "repair_candidates.json"
    if not cand_p.exists():
        raise SystemExit("REPAIR FAIL: repair_candidates.json missing — run suggest first")
    blob = json.load(open(cand_p))
    return blob.get("candidates") or [], hashlib.sha256(cand_p.read_bytes()).hexdigest()


def plan_batches(run_dir, k=10, page_size=600):
    """C5 batched lane (pure code, ZERO judgment): deterministically compose review batches
    from the pinned candidates file. Order = h32-shuffle of the similarity-ranked list (the
    ranked adjacency is the anchoring hazard); pages of `page_size` (owner: 600 is a PAGE
    size, never a cap — every pair is planned); within a page, first-fit batches of <=k with
    HARD record-name disjointness (a colliding pair opens a fresh batch — same-record overflow
    is per-pair by construction, never co-batched). Writes repair_batches/batch_NNNN.json
    (each judge Reads its own code-written file — no giant relay) + repair_plan.json bound
    to the candidates bytes by sha256."""
    run = Path(run_dir)
    cands, cands_sha = _load_pinned_candidates(run)
    if not cands:
        raise SystemExit("REPAIR FAIL: plan requested but the pinned candidates file has 0 pairs")
    order = sorted(range(len(cands)),
                   key=lambda i: (h32(f"{cands[i]['a']}|{cands[i]['b']}"), i))
    pages = [order[s:s + page_size] for s in range(0, len(order), page_size)]
    batches, page_of = [], {}
    for pg_no, page in enumerate(pages):
        open_batches = []
        for i in page:
            page_of[str(i)] = pg_no
            nm = {norm(cands[i]["a"]), norm(cands[i]["b"])}
            for names, idxs in open_batches:
                if len(idxs) < k and not (names & nm):
                    idxs.append(i)
                    names |= nm
                    break
            else:
                open_batches.append((set(nm), [i]))
        batches += [{"page": pg_no, "idx": idxs} for _, idxs in open_batches]
    bdir = run / "repair_batches"
    bdir.mkdir(exist_ok=True)
    for old in bdir.glob("batch_*.json"):
        old.unlink()                      # stale files from a prior plan must never survive
    for bid, b in enumerate(batches):
        b["id"] = bid
        (bdir / f"batch_{bid:04d}.json").write_text(serialize(
            {"batch_id": bid, "page": b["page"],
             "pairs": [{**cands[i], "idx": i} for i in b["idx"]]}))
    plan = {"k": k, "page_size": page_size, "n_candidates": len(cands),
            "cands_sha256": cands_sha, "pages": len(pages), "page_of": page_of,
            "batches": [{"id": b["id"], "page": b["page"], "idx": b["idx"]} for b in batches]}
    (run / "repair_plan.json").write_text(serialize(plan))
    return {"ok": True, "n_candidates": len(cands), "pages": len(pages),
            "batches": len(batches),
            "batch_counts": [len(b["idx"]) for b in batches],
            "cands_sha256": cands_sha}


def show_candidates(run_dir, idx_list):
    """Code-printed candidate views for the confirm lane: the workflow verifies page_h32
    over the relayed copy (same canonical-JSON h32 as cands_h32), then inlines each
    candidate byte-identically into TODAY's per-pair prompt."""
    run = Path(run_dir)
    cands, _ = _load_pinned_candidates(run)
    bad = [i for i in idx_list if not (0 <= i < len(cands))]
    if bad:
        raise SystemExit(f"REPAIR FAIL: show idx out of range: {bad[:5]} (n={len(cands)})")
    sel = [{**cands[i], "idx": i} for i in idx_list]
    return {"candidates": sel,
            "page_h32": h32(json.dumps(sel, sort_keys=True, separators=(",", ":"),
                                       ensure_ascii=False))}


def assemble_review(run_dir, pieces, expect):
    """Chunked relay-write FINAL enforcement (incident 2026-06-11: a single-shot agent
    Write of a full-size review truncated at the clerk's output-token limit; the hand
    re-transcription drifted 1 byte and the --expect gate refused). The workflow has
    clerks write the review JSON in row-boundary pieces (each post-write h32-asserted);
    THIS pure-code step is the gate that counts: exact piece set, byte concat, full
    h32+rv vs the workflow-computed --expect, write repair_review.json only on match."""
    run = Path(run_dir)
    if not isinstance(pieces, int) or pieces < 1:
        raise SystemExit(f"REPAIR FAIL: assemble-review needs --pieces >= 1 (got {pieces!r})")
    cdir = run / "review_chunks"
    have = sorted(p.name for p in cdir.glob("piece_*.txt")) if cdir.exists() else []
    want = [f"piece_{i:04d}.txt" for i in range(pieces)]
    if have != want:
        raise SystemExit(f"REPAIR FAIL: review piece set mismatch — have {have} want {want} "
                         f"(missing/stale pieces; a prior run's survivors must never splice in)")
    full = "".join((cdir / w).read_text(encoding="utf-8") for w in want)
    try:
        rows = json.loads(full).get("reviews")
    except json.JSONDecodeError as e:
        raise SystemExit(f"REPAIR FAIL: assembled review is not valid JSON ({e}) — a piece "
                         f"was written wrong (relay-write fidelity)")
    rv = len(rows) if isinstance(rows, list) else -1
    verify_expect(expect, full, {"rv": rv}, "REPAIR assemble-review")
    (run / "repair_review.json").write_text(full, encoding="utf-8")
    for w in want:
        (cdir / w).unlink()
    cdir.rmdir()
    return {"ok": True, "rv": rv, "h32": h32(full)}


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
            # post_split: repair runs on the FINAL catalog (after leaf D5 splits), so its
            # links may legitimately reference split-coined records; assemble's coined-target
            # anachronism guard exempts ONLY rows carrying this tag.
            dec.setdefault("approved_same_as", []).append({"variant": by[va]["driver_name"],
                                                           "canonical": by[ca]["driver_name"],
                                                           "post_split": True})
            existing.add(pair)
            added.append({"variant": by[va]["driver_name"], "canonical": by[ca]["driver_name"]})
        if n >= 8:
            hb.append({"kind": "link", "a": by[ca]["driver_name"], "b": by[va]["driver_name"],
                       "n": n, "survives": True})

    # C5 P2 (batched lane only — repair_plan.json present): the review rows must match the
    # code-written plan EXACTLY: every planned idx exactly once, names echo the pinned
    # candidate at that idx (catches transposition the norm-echo alone lets through), the
    # plan must still bind to the CURRENT candidates bytes (stale plan = mixed generations),
    # and every SAME row must carry confirmed:true (the per-pair blind confirm ran — a
    # batched SAME may NEVER reach apply unconfirmed).
    plan_p = run / "repair_plan.json"
    if plan_p.exists():
        plan = json.load(open(plan_p))
        cur_sha = (hashlib.sha256((run / "repair_candidates.json").read_bytes()).hexdigest()
                   if (run / "repair_candidates.json").exists() else None)
        if plan.get("cands_sha256") != cur_sha:
            raise SystemExit("REPAIR FAIL: repair_plan.json is stale — candidates changed "
                             "since planning (no regeneration between pages); re-run plan")
        cands_list = json.load(open(run / "repair_candidates.json")).get("candidates") or []
        planned = [i for b in (plan.get("batches") or []) for i in b.get("idx") or []]
        rows = review.get("reviews") or []
        got_idx = [r.get("idx") for r in rows]
        if sorted(got_idx, key=str) != sorted(planned, key=str) or len(set(got_idx)) != len(got_idx):
            raise SystemExit("REPAIR FAIL: review rows must cover every planned pair "
                             "exactly once (missing/duplicate idx) — fail-close")
        for r in rows:
            c = cands_list[r["idx"]]
            if norm(r.get("a")) != norm(c.get("a")) or norm(r.get("b")) != norm(c.get("b")):
                raise SystemExit(f"REPAIR FAIL: row idx={r['idx']} names "
                                 f"{r.get('a')}|{r.get('b')} does not match plan candidate "
                                 f"{c.get('a')}|{c.get('b')} — transposed verdict; fail-close")
            if r.get("verdict") == "SAME" and r.get("confirmed") is not True:
                raise SystemExit(f"REPAIR FAIL: batched SAME idx={r['idx']} lacks the blind "
                                 f"per-pair confirm (confirmed:true) — a batch proposer SAME "
                                 f"may never apply unconfirmed")

        # C5 §8d GO condition #2 — the production canary. Apply RE-derives the deterministic
        # sample itself (h32 of the normalized pinned pair, idx tie-break; ~CANARY_RATE of
        # the DIFFERENT/UNCLEAR rows that never got an isolated look, min CANARY_MIN), so a
        # relay can never silently skip it. A sampled row without a solo canary_verdict =
        # canary skipped; any canary_verdict SAME = the batched lane is missing merges.
        # The canary NEVER creates links (alarm only) — abort before any write, loud.
        eligible = [r for r in rows if r.get("verdict") in ("DIFFERENT", "UNCLEAR")
                    and r.get("confirmed") is not True]
        if eligible:
            n = min(len(eligible), max(CANARY_MIN, math.ceil(CANARY_RATE * len(eligible))))
            sampled = sorted(eligible,
                             key=lambda r: (h32(f"{norm(cands_list[r['idx']]['a'])}|"
                                                f"{norm(cands_list[r['idx']]['b'])}"),
                                            r["idx"]))[:n]
            no_solo = [r["idx"] for r in sampled
                       if r.get("canary_verdict") not in ("SAME", "DIFFERENT", "UNCLEAR")]
            if no_solo:
                raise SystemExit(f"REPAIR FAIL: canary solo verdict missing/invalid for idx "
                                 f"{no_solo} — the {n}-row production canary may never be "
                                 f"skipped (fail-close)")
            hits = [r["idx"] for r in sampled if r.get("canary_verdict") == "SAME"]
            if hits:
                raise SystemExit(f"REPAIR FAIL: CANARY HIT — solo re-judgment says SAME for "
                                 f"batched-DIFFERENT/UNCLEAR idx {hits}; the batched lane is "
                                 f"missing merges — investigate / re-run per-pair before any "
                                 f"batched apply")

    # C5-study today-bug fix: EVERY suggested pair must carry a review verdict (any verdict).
    # Without this, an abridged relay or lost verdicts leave pairs silently unjudged —
    # under-merge that no existing check could see. Directional on purpose: review rows for
    # pairs absent from a REGENERATED candidates file stay legal (idempotent resume after
    # suggest re-ran post-link). Placed after the loop so nothing has been written yet.
    if cand_pairs is not None:
        review_pairs = {frozenset((norm(r.get("a")), norm(r.get("b"))))
                        for r in (review.get("reviews") or [])}
        unjudged = sorted("|".join(sorted(pr)) for pr in (cand_pairs - review_pairs))
        if unjudged:
            raise SystemExit(f"REPAIR FAIL: {len(unjudged)} suggested pair(s) have NO review "
                             f"verdict (first 5: {unjudged[:5]}) — pairs silently unjudged "
                             f"(abridged relay / lost verdicts?); re-run the review")

    if hb:
        have = {(norm(x.get("a")), norm(x.get("b"))) for x in dec.get("high_blast_refute2") or []}
        for row in hb:
            key = (norm(row["a"]), norm(row["b"]))
            if key not in have:
                dec.setdefault("high_blast_refute2", []).append(row)
    # assemble FIRST (it validates the updated decisions), persist ONLY on success —
    # found live 2026-06-11: writing decisions.json before assemble left 24 stale rows
    # behind when assemble raised, poisoning every re-run (mutate-before-validate).
    # Fold-parent fix (2026-06-12): on a FOLD parent, same_name_review.json is the FOLD-SHAPED
    # review that fold part-b already consumed to BUILD this seed (DIFFERENT names replaced by
    # split targets, UNCLEAR names parked to fold_sidecars.json; D4 — fold verdicts are final,
    # never re-applied). Feeding it to the leaf apply_review hard-failed ("collision_name ...
    # is not a seed record name") on any DIFFERENT/UNCLEAR row. Leaf runs keep today's
    # behavior byte-for-byte: their leaf-D5 review applies at every re-assembly. The file
    # itself MUST stay on disk — the D8 fold gates still read it for split accounting.
    review_file = run / "same_name_review.json"
    use_review = review_file.exists() and not (run / "fold_manifest.json").exists()
    out, approved = assemble(seed, dec, json.load(open(review_file)) if use_review else None)
    dec_p.write_text(serialize(dec))
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
    s.add_argument("--limit", type=int, default=0,
                   help="0 = no cap (default): rank ALL pairs (13.2 C5 batched mode)")
    s.add_argument("--extra-candidates", default=None)
    s.add_argument("--use-embeddings", dest="use_embeddings", action="store_true", default=True,
                   help="embeddings suggester ON by default (13.2, min_score 0.60); --no-embeddings to disable")
    s.add_argument("--no-embeddings", dest="use_embeddings", action="store_false",
                   help="disable the embeddings suggester (offline / no OPENAI_API_KEY)")
    s.add_argument("--embedding-top-k", type=int, default=5)
    s.add_argument("--embedding-min-score", type=float, default=0.60)
    s.add_argument("--print-summary", action="store_true",
                   help="C5 slim relay: print counts/hashes/params only (full blob still "
                        "written to repair_candidates.json on disk)")
    pl = sub.add_parser("plan")
    pl.add_argument("run_dir")
    pl.add_argument("--k", type=int, default=10, help="C5: pairs per batch")
    pl.add_argument("--page-size", type=int, default=600,
                    help="C5: review PAGE size (never a cap — all pairs are planned)")
    sm = sub.add_parser("summary")
    sm.add_argument("run_dir")
    sh = sub.add_parser("show")
    sh.add_argument("run_dir")
    sh.add_argument("--idx", required=True, help="comma-separated candidate indices")
    a = sub.add_parser("apply")
    a.add_argument("run_dir")
    a.add_argument("--review", required=True)
    a.add_argument("--expect", default=None,
                   help="Stage-0 #5: rv=..,h32=.. computed by the workflow JS from the review "
                        "SOURCE string; binds the agent-written repair_review.json to it")
    ar = sub.add_parser("assemble-review")
    ar.add_argument("run_dir")
    ar.add_argument("--pieces", type=int, required=True,
                    help="exact number of review_chunks/piece_NNNN.txt files to glue")
    ar.add_argument("--expect", required=True,
                    help="rv=..,h32=.. computed by the workflow JS from the review SOURCE "
                         "string; the assembled bytes must hit it or nothing is written")
    args = ap.parse_args(argv)
    if args.mode == "assemble-review":
        print(json.dumps(assemble_review(args.run_dir, args.pieces, args.expect),
                         sort_keys=True))
        return
    if args.mode == "summary":
        # decision-④ frozen fixture: slim view of the EXISTING pinned candidates file —
        # never regenerates (the whole point is byte-frozen candidates across arms).
        blob = json.load(open(Path(args.run_dir) / "repair_candidates.json"))
        print(json.dumps({k: v for k, v in blob.items() if k != "candidates"}, sort_keys=True))
        return
    if args.mode == "plan":
        print(json.dumps(plan_batches(args.run_dir, args.k, args.page_size), sort_keys=True))
        return
    if args.mode == "show":
        idxs = [int(x) for x in args.idx.split(",") if x.strip() != ""]
        print(json.dumps(show_candidates(args.run_dir, idxs), sort_keys=True))
        return
    if args.mode == "suggest":
        # Stage-0 #1: repair builds ON the catalog — refuse unless its last validation
        # passed and the catalog/approved bytes are unchanged since (sidecar binding).
        require_validated(args.run_dir)
        out = suggest(args.run_dir, args.min_token_overlap, args.limit, args.extra_candidates,
                      args.use_embeddings, args.embedding_top_k, args.embedding_min_score)
        if args.print_summary:
            out = {k: v for k, v in out.items() if k != "candidates"}
    else:
        if args.expect is not None:
            review_raw = Path(args.review).read_text()
            verify_expect(args.expect, review_raw,
                          {"rv": len(json.loads(review_raw).get("reviews") or [])},
                          "REPAIR repair_review.json")
        out = apply(args.run_dir, args.review)
    print(json.dumps(out, sort_keys=True))


if __name__ == "__main__":
    main()
