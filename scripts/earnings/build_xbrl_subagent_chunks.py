#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_UNIVERSE = Path("/tmp/db_universe_active.csv")
TEMPLATE_PATH = ROOT / ".claude/plans/xbrl_subagent_master_prompt.md"
DEFAULT_OUTDIR = ROOT / ".claude/plans/xbrl_subagent_chunks"


@dataclass
class Chunk:
    chunk_id: int
    tickers: list[str]


def load_tickers(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        tickers = sorted({(row.get("ticker") or "").strip().upper() for row in reader if (row.get("ticker") or "").strip()})
    return tickers


def split_evenly(items: list[str], n_chunks: int) -> list[Chunk]:
    base = len(items) // n_chunks
    extra = len(items) % n_chunks
    out: list[Chunk] = []
    start = 0
    for idx in range(n_chunks):
        size = base + (1 if idx < extra else 0)
        chunk_items = items[start:start + size]
        out.append(Chunk(chunk_id=idx + 1, tickers=chunk_items))
        start += size
    return out


def render_prompt(template: str, chunk: Chunk, snapshot_ts: str, outdir: Path) -> str:
    chunk_slug = f"{chunk.chunk_id:02d}"
    ticker_block = "\n".join(chunk.tickers)
    revenue_out = outdir / f"revenue_map_chunk_{chunk_slug}.jsonl"
    operating_out = outdir / f"operating_map_chunk_{chunk_slug}.jsonl"
    notes_out = outdir / f"validation_notes_chunk_{chunk_slug}.md"
    return (
        template
        .replace("__CHUNK_ID__", chunk_slug)
        .replace("__SNAPSHOT_TS__", snapshot_ts)
        .replace("__TICKER_LIST__", ticker_block)
        .replace("__REVENUE_OUT__", str(revenue_out))
        .replace("__OPERATING_OUT__", str(operating_out))
        .replace("__NOTES_OUT__", str(notes_out))
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate pre-filled XBRL sub-agent prompts from the active ticker universe.")
    parser.add_argument("--universe-csv", type=Path, default=DEFAULT_UNIVERSE)
    parser.add_argument("--template", type=Path, default=TEMPLATE_PATH)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--chunks", type=int, default=20)
    parser.add_argument("--snapshot-ts", required=True, help="Shared snapshot timestamp for all sub-agents, e.g. 2026-04-22T10:00:00-04:00")
    args = parser.parse_args()

    tickers = load_tickers(args.universe_csv)
    chunks = split_evenly(tickers, args.chunks)
    template = args.template.read_text(encoding="utf-8")

    args.outdir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "universe_csv": str(args.universe_csv),
        "ticker_count": len(tickers),
        "chunks": args.chunks,
        "snapshot_ts": args.snapshot_ts,
        "chunk_sizes": {},
    }

    for chunk in chunks:
        chunk_slug = f"{chunk.chunk_id:02d}"
        prompt_path = args.outdir / f"chunk_{chunk_slug}_prompt.md"
        tickers_path = args.outdir / f"chunk_{chunk_slug}_tickers.txt"
        prompt_path.write_text(render_prompt(template, chunk, args.snapshot_ts, args.outdir), encoding="utf-8")
        tickers_path.write_text("\n".join(chunk.tickers) + "\n", encoding="utf-8")
        manifest["chunk_sizes"][chunk_slug] = len(chunk.tickers)

    (args.outdir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
