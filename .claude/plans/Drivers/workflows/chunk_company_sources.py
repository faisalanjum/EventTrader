#!/usr/bin/env python3
"""
Derived chunk layer for the Driver seed build (HierarchicalCatalogPlan §8 / §12.2 / §12.5, D7).

Never drop text; bound every blind bot's reading load by SPLITTING, never clipping.
- builds, per event, `event_text` = the event's sub-units joined in the locked §12.2 order
- layered fallback ladder: (a) whole small events pack together · (b) natural units ·
  (c) paragraph (\\n\\s*\\n) · (d) sentence ((?<=[.!?])\\s+) · (e) char range — (e) always succeeds
- parts are contiguous SLICES of event_text (separators land in exactly one part, in order)
  -> ordered concat(parts) == event_text BY CONSTRUCTION; --verify re-proves it from disk (§8.7c)
- writes <run_dir>/chunks/<TICKER>__chunk_NNN.json  (= one blind bot's full input, §12.5)
  + <run_dir>/chunks_manifest.json (one row per part: split_level, char range, sha256)
- KPIs ride in chunk_001 only; deterministic (sorted inputs, no wall-clock in outputs)

Usage:  chunk_company_sources.py <run_dir> [--budget N] [--verify]
        reads <run_dir>/sources/<TICKER>.json (the UNCAPPED structured fetch output)
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

CHUNK_BUDGET_CHARS = 40_000   # §11.1 [OWNER] per-bot budget
PARA_RE = re.compile(r"\n\s*\n")
SENT_RE = re.compile(r"(?<=[.!?])\s+")
LEVELS = {"whole": 0, "natural": 1, "paragraph": 2, "sentence": 3, "char": 4}


def build_event_text(ev):
    """§12.2: join sub-units in the legacy build_*_content order, uncapped, '\\n\\n' between blocks."""
    return "\n\n".join(b for b, _ in event_blocks(ev))


def event_blocks(ev):
    """Returns [(block_text, intra_block_cuts)] where cuts are char offsets WITHIN the block
    at natural sub-boundaries (transcript Q&A exchange starts)."""
    blocks = []
    if ev.get("source_type") == "transcript":
        if ev.get("prepared"):
            blocks.append(("PREPARED REMARKS:\n" + ev["prepared"], []))
        qa = [q for q in (ev.get("qa_exchanges") or []) if q]
        if qa:
            text = "Q&A:\n" + "\n---\n".join(qa)
            cuts, pos = [], len("Q&A:\n")
            for q in qa[:-1]:
                pos += len(q) + len("\n---\n")
                cuts.append(pos)        # cut at the start of the NEXT exchange (separator stays left)
            blocks.append((text, cuts))
    else:
        blocks.append((f"FORM: {ev.get('source_type') or ''}", []))
        blocks.append((f"ITEMS: {ev.get('items') or ''}", []))
        if ev.get("description"):
            blocks.append((f"DESC: {ev['description']}", []))
        if ev.get("is_earnings") and ev.get("ex991"):
            blocks.append(("PRESS RELEASE (EX-99.1):\n" + ev["ex991"], []))
        for s in (ev.get("sections") or []):
            if s and s.get("content"):
                blocks.append((f"[{s.get('name')}]\n{s['content']}", []))
    return blocks


def natural_cuts(ev):
    """Global char offsets into event_text where a natural boundary exists (block starts +
    intra-block sub-boundaries). Separators ('\\n\\n') attach to the PRECEDING part."""
    cuts, pos = [], 0
    blocks = event_blocks(ev)
    for i, (text, intra) in enumerate(blocks):
        if i > 0:
            cuts.append(pos)            # cut at the start of this block
        cuts.extend(pos + c for c in intra)
        pos += len(text) + (2 if i < len(blocks) - 1 else 0)  # "\n\n" rides with the left part
    return cuts


def _refine(text, start, end, budget, regex):
    """Cut offsets inside [start,end) at regex match-ends; only offsets strictly inside."""
    return [start + m.end() for m in regex.finditer(text[start:end]) if 0 < m.end() < (end - start)]


def split_event(text, cuts, budget):
    """-> [(start, end, split_level)] contiguous parts, each <= budget, covering text exactly."""
    if len(text) <= budget:
        return [(0, len(text), "whole")]
    # atoms between consecutive natural cuts, refined down the ladder where needed
    bounds = sorted({0, len(text), *[c for c in cuts if 0 < c < len(text)]})
    atoms = []  # (start, end, level)
    for s, e in zip(bounds, bounds[1:]):
        if e - s <= budget:
            atoms.append((s, e, "natural"))
            continue
        pcuts = _refine(text, s, e, budget, PARA_RE)
        pb = sorted({s, e, *pcuts})
        for ps, pe in zip(pb, pb[1:]):
            if pe - ps <= budget:
                atoms.append((ps, pe, "paragraph"))
                continue
            scuts = _refine(text, ps, pe, budget, SENT_RE)
            sb = sorted({ps, pe, *scuts})
            for ss, se in zip(sb, sb[1:]):
                if se - ss <= budget:
                    atoms.append((ss, se, "sentence"))
                else:
                    for cs in range(ss, se, budget):       # (e) char range — always succeeds
                        atoms.append((cs, min(cs + budget, se), "char"))
    atoms.sort()
    # greedy merge consecutive atoms (fewest parts); part level = finest level at its edges
    parts, cur_s, cur_e, cur_lv = [], atoms[0][0], atoms[0][1], atoms[0][2]
    for s, e, lv in atoms[1:]:
        if (e - cur_s) <= budget:
            cur_e = e
            cur_lv = lv if LEVELS[lv] > LEVELS[cur_lv] else cur_lv
        else:
            parts.append((cur_s, cur_e, cur_lv))
            cur_s, cur_e, cur_lv = s, e, lv
    parts.append((cur_s, cur_e, cur_lv))
    return parts


def chunk_run(run_dir, budget=CHUNK_BUDGET_CHARS):
    run_dir = Path(run_dir)
    # Stage-0 #8: when the fetch wrote a code-to-code scope_resolved.json, the fetched
    # sources MUST cover exactly those tickers (a relay-dropped ticker = a whole company
    # silently absent from the seed). Absent file = legacy/positional-ticker run, no check.
    scope_p = run_dir / "scope_resolved.json"
    if scope_p.exists():
        want = {str(t).strip().upper() for t in (json.loads(scope_p.read_text()).get("tickers") or [])}
        got = {p.stem.upper() for p in (run_dir / "sources").glob("*.json")}
        if want != got:
            raise SystemExit(f"CHUNK FAIL: sources/ tickers != scope_resolved.json tickers "
                             f"(missing={sorted(want - got)}, extra={sorted(got - want)})")
    out_dir = run_dir / "chunks"
    out_dir.mkdir(exist_ok=True)
    for old in out_dir.glob("*.json"):
        old.unlink()
    rows, chunk_ids, per_ticker = [], [], {}
    for src in sorted((run_dir / "sources").glob("*.json")):
        data = json.loads(src.read_text())
        tk = data.get("ticker") or src.stem
        entries = []   # flat (source_id, source_type, date, part_index, part_count, content, level, s, e)
        for ev in (data.get("events") or []):
            text = build_event_text(ev)
            if not text:
                continue
            parts = split_event(text, natural_cuts(ev), budget)
            assert "".join(text[s:e] for s, e, _ in parts) == text  # conservation by construction
            for i, (s, e, lv) in enumerate(parts, 1):
                entries.append({"source_id": ev.get("source_id"), "source_type": ev.get("source_type"),
                                "date": ev.get("date"), "part_index": i, "part_count": len(parts),
                                "content": text[s:e], "_lv": lv if len(parts) > 1 else "whole",
                                "_s": s, "_e": e})
        # pack entries greedily, in order
        chunks, cur, cur_len = [], [], 0
        for en in entries:
            if cur and cur_len + len(en["content"]) > budget:
                chunks.append(cur)
                cur, cur_len = [], 0
            cur.append(en)
            cur_len += len(en["content"])
        if cur or data.get("fiscal_kpis"):
            chunks.append(cur)
        for n, ch in enumerate(chunks, 1):
            cid = f"{tk}__chunk_{n:03d}"
            payload = {"ticker": tk, "chunk_id": cid,
                       "events": [{k: e[k] for k in ("source_id", "source_type", "date",
                                                     "part_index", "part_count", "content")}
                                  for e in ch]}
            if n == 1:
                payload["fiscal_kpis"] = data.get("fiscal_kpis") or []
            (out_dir / f"{cid}.json").write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n")
            chunk_ids.append(cid)
            for e in ch:
                rows.append({"ticker": tk, "chunk_id": cid, "source_id": e["source_id"],
                             "part_index": e["part_index"], "part_count": e["part_count"],
                             "split_level": e["_lv"], "char_start": e["_s"], "char_end": e["_e"],
                             "sha256": hashlib.sha256(e["content"].encode("utf-8")).hexdigest()})
        per_ticker[tk] = len(chunks)
    (run_dir / "chunks_manifest.json").write_text(
        json.dumps({"budget": budget, "rows": rows}, indent=1, ensure_ascii=False) + "\n")
    return {"chunk_ids": chunk_ids, "per_ticker": per_ticker, "budget": budget, "rows": len(rows)}


def verify_run(run_dir):
    """§8.7c byte-exact conservation + part completeness, re-proven from disk."""
    run_dir = Path(run_dir)
    got = {}   # (ticker, source_id) -> {part_index: content}
    for f in sorted((run_dir / "chunks").glob("*.json")):
        ch = json.loads(f.read_text())
        for e in ch["events"]:
            got.setdefault((ch["ticker"], e["source_id"]), {})[e["part_index"]] = (e["content"], e["part_count"])
    fails = []
    for src in sorted((run_dir / "sources").glob("*.json")):
        data = json.loads(src.read_text())
        tk = data.get("ticker") or src.stem
        for ev in (data.get("events") or []):
            text = build_event_text(ev)
            if not text:
                continue
            parts = got.get((tk, ev.get("source_id")))
            if not parts:
                fails.append(f"{tk}/{ev.get('source_id')}: NO parts on disk")
                continue
            pc = next(iter(parts.values()))[1]
            if sorted(parts) != list(range(1, pc + 1)):
                fails.append(f"{tk}/{ev.get('source_id')}: parts {sorted(parts)} != 1..{pc}")
                continue
            joined = "".join(parts[i][0] for i in range(1, pc + 1))
            if hashlib.sha256(joined.encode("utf-8")).hexdigest() != hashlib.sha256(text.encode("utf-8")).hexdigest():
                fails.append(f"{tk}/{ev.get('source_id')}: byte-exact conservation BROKEN")
    if fails:
        print("VERIFY FAILED")
        for f in fails[:50]:
            print("  ✗ " + f)
        sys.exit(1)
    print(f"VERIFY OK ({len(got)} events byte-exact)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--budget", type=int, default=CHUNK_BUDGET_CHARS)
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    if a.verify:
        verify_run(a.run_dir)
        return
    summary = chunk_run(a.run_dir, budget=a.budget)
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
