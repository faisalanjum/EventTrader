#!/usr/bin/env python3
"""
A2 per-chunk resume plan (CostCutting Class A2) — pure code, ZERO judgment.

For an EXISTING run dir whose fetch+chunk stages completed, decide which chunk readers
still need to run. Fail-close everywhere:
  - the dir must hold non-empty sources/ + chunks/ + chunks_manifest.json, else hard fail
    (resume of an incomplete dir is meaningless — run menu_build fresh);
  - the chunk stage is RE-PROVEN byte-exact against sources/ (§8.7c verify) — a corrupted
    chunk stage hard-fails before any reader is paid;
  - a manifest row whose chunk file is missing, or a stale menu for an unknown chunk,
    hard-fails (mixed-generation artifacts must never feed one seed);
  - a chunk is DONE only if menus/<cid>.json parses AND matches that exact chunk
    (chunk_id + ticker) AND has a well-formed candidates list — anything half-written,
    mismatched, or malformed goes back on the TODO list and is re-run (overwritten).
done_counts uses build_seed's exact counting rule (non-blank driver_name) so the
--expect cross-check stays exact across reused + freshly-run readers.

Prints ONE final JSON line:
  {"all": N, "done": N, "todo": [cid...], "done_counts": {ticker: n}, "tickers": [...], "notes": "..."}
(The §8.7c verify prints its own OK line first — consumers read the FINAL line.)
"""
import json
import sys
from pathlib import Path

from chunk_company_sources import verify_run


def norm(s):  # §12.1 shared norm()
    return (s or "").strip().lower()


REQUIRED_TOP = ("ticker", "chunk_id", "candidate_count", "candidates", "skipped_count", "notes")
CANDIDATE_FIELDS = ("driver_name", "evidence_quote", "source_type", "source_id", "date")


def menu_valid(path, cid):
    """The menu file for chunk `cid`, or None (fail-close -> re-run the reader).
    Mirrors the live MENU_SCHEMA closely enough that no absent/null/blank-evidence
    candidate can be REUSED into build_seed: top-level keys present, exact chunk_id +
    ticker match, candidate_count == len(candidates), every candidate carries all five
    string fields, and every NAMED candidate has non-blank quote/source_type/source_id
    (date may be "" — the fiscal-KPI contract). Verified against all 68 real CAKE
    menus: zero false rejections."""
    try:
        m = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(m, dict) or any(k not in m for k in REQUIRED_TOP):
        return None
    if str(m.get("chunk_id")) != cid:
        return None
    if m.get("ticker") != cid.split("__")[0]:        # EXACT match — readers copy the cid prefix
        return None
    cands = m.get("candidates")
    if (not isinstance(cands, list)
            or not isinstance(m.get("candidate_count"), int)
            or m["candidate_count"] != len(cands)):
        return None
    for x in cands:
        if not isinstance(x, dict) or any(not isinstance(x.get(k), str) for k in CANDIDATE_FIELDS):
            return None
        if norm(x["driver_name"]) and not (x["evidence_quote"].strip()
                                           and x["source_type"].strip()
                                           and x["source_id"].strip()):
            return None
    return m


def plan(run_dir):
    run = Path(run_dir)
    chunks_dir, manifest_p, sources_dir = run / "chunks", run / "chunks_manifest.json", run / "sources"
    if not (chunks_dir.is_dir() and any(chunks_dir.glob("*.json"))
            and manifest_p.exists()
            and sources_dir.is_dir() and any(sources_dir.glob("*.json"))):
        raise SystemExit(f"RESUME FAIL: {run} is not a completed fetch+chunk run dir "
                         f"(need non-empty sources/ + chunks/ + chunks_manifest.json) — "
                         f"run menu_build fresh instead")
    dir_ids = {p.stem for p in chunks_dir.glob("*.json")}
    try:
        man_ids = {str(r.get("chunk_id")) for r in
                   (json.loads(manifest_p.read_text()).get("rows") or []) if r.get("chunk_id")}
    except (OSError, ValueError):
        raise SystemExit("RESUME FAIL: chunks_manifest.json unreadable/corrupt — chunk stage "
                         "corrupted; re-run fresh")
    missing_files = sorted(man_ids - dir_ids)
    if missing_files:
        raise SystemExit(f"RESUME FAIL: chunks_manifest.json references chunk files missing on "
                         f"disk {missing_files[:5]} — chunk stage corrupted; re-run fresh")

    src_stems = {p.stem for p in sources_dir.glob("*.json")}
    # Stage-0 #8 mirror (final-gate fix): if the run dir carries the code-written scope file,
    # the sources on disk must still match it exactly (a source deleted/added after fetch
    # would silently change the company set the seed claims to cover).
    scope_p = run / "scope_resolved.json"
    if scope_p.exists():
        try:
            scope_t = {str(t).strip().upper() for t in
                       (json.loads(scope_p.read_text()).get("tickers") or [])}
        except (OSError, ValueError):
            raise SystemExit("RESUME FAIL: scope_resolved.json unreadable/corrupt — re-run fresh")
        if scope_t != {s.upper() for s in src_stems}:
            raise SystemExit(f"RESUME FAIL: sources/ tickers != scope_resolved.json "
                             f"(missing={sorted(scope_t - {s.upper() for s in src_stems})}, "
                             f"extra={sorted({s.upper() for s in src_stems} - scope_t)}) — re-run fresh")

    # Per-chunk consistency sweep (final-gate fix — covers ALL chunks, not just row-less):
    # every chunk's ticker must have a source file (orphan = deleted/foreign source);
    # every *_chunk_001's fiscal_kpis must equal the source list VERBATIM (the chunker
    # copies it; any difference = stale generation); no other chunk may carry KPIs;
    # a row-less chunk is legitimate ONLY as the KPI-only chunk_001 shape.
    all_ids = sorted(dir_ids | man_ids)
    src_kpis = {}
    for cid in all_ids:
        tk = cid.split("__")[0]
        if tk not in src_stems:
            raise SystemExit(f"RESUME FAIL: chunk {cid} references ticker '{tk}' with no source "
                             f"file — deleted/foreign source; mixed generations; re-run fresh")
        try:
            ch = json.loads((chunks_dir / f"{cid}.json").read_text())
        except (OSError, ValueError):
            raise SystemExit(f"RESUME FAIL: unreadable chunk file {cid} — chunk stage corrupted; "
                             f"re-run fresh")
        # the chunker always writes chunk_id == filename stem and ticker == its prefix; a
        # mismatch is corruption/mixed-generation (the reader cats this JSON directly)
        if not isinstance(ch, dict) or ch.get("chunk_id") != cid or ch.get("ticker") != tk:
            raise SystemExit(f"RESUME FAIL: chunk file {cid} internal chunk_id/ticker mismatch "
                             f"(chunk_id={ch.get('chunk_id') if isinstance(ch, dict) else None!r}, "
                             f"ticker={ch.get('ticker') if isinstance(ch, dict) else None!r}) — "
                             f"corrupted/mixed-generation; re-run fresh")
        kp = ch.get("fiscal_kpis")
        if cid.endswith("__chunk_001"):
            if tk not in src_kpis:
                try:
                    src_kpis[tk] = (json.loads((sources_dir / f"{tk}.json").read_text())
                                    .get("fiscal_kpis") or [])
                except (OSError, ValueError):
                    raise SystemExit(f"RESUME FAIL: unreadable source file for '{tk}' — re-run fresh")
            if (kp or []) != src_kpis[tk]:
                raise SystemExit(f"RESUME FAIL: {cid} fiscal_kpis differ from source — stale "
                                 f"generation; re-run fresh")
        elif kp:
            raise SystemExit(f"RESUME FAIL: {cid} carries fiscal_kpis but only chunk_001 may "
                             f"carry fiscal_kpis — stale generation; re-run fresh")
        if cid not in man_ids:
            legit = (isinstance(ch, dict)
                     and ch.get("chunk_id") == cid and ch.get("ticker") == tk
                     and cid.endswith("__chunk_001")
                     and ch.get("events") == []
                     and isinstance(kp, list) and kp)
            if not legit:
                raise SystemExit(f"RESUME FAIL: chunk file {cid} has no chunks_manifest.json rows "
                                 f"and is not a legitimate KPI-only chunk — stale/mixed-generation "
                                 f"text must never reach a reader; re-run fresh")
    verify_run(run)   # §8.7c byte-exact conservation re-proven from disk (exits 1 on any break)

    menus_dir = run / "menus"
    stale = sorted({p.stem for p in menus_dir.glob("*.json")} - set(all_ids)) if menus_dir.is_dir() else []
    if stale:
        raise SystemExit(f"RESUME FAIL: stale menu file(s) for unknown chunks {stale[:5]} — "
                         f"mixed-generation artifacts; clean menus/ or re-run fresh")

    todo, done_counts, done = [], {}, 0
    for cid in all_ids:
        mp = menus_dir / f"{cid}.json"
        m = menu_valid(mp, cid)
        if m is None:
            if mp.exists():
                mp.unlink()   # invalid file is worthless and would block the reader's fresh Write
            todo.append(cid)
        else:
            done += 1
            tk = str(m.get("ticker") or "").strip()
            n = sum(1 for x in m["candidates"] if norm(x.get("driver_name")))
            done_counts[tk] = done_counts.get(tk, 0) + n
    return {"all": len(all_ids), "done": done, "todo": todo, "done_counts": done_counts,
            "tickers": sorted(p.stem for p in sources_dir.glob("*.json")),
            "notes": f"{done} valid menu(s) reused; {len(todo)} chunk(s) to run"}


def main():
    if len(sys.argv) != 2:
        print("Usage: resume_menus.py <run_dir>", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(plan(sys.argv[1]), sort_keys=True))


if __name__ == "__main__":
    main()
