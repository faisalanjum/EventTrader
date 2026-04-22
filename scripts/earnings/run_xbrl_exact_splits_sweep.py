#!/usr/bin/env python3
"""Run the mapped revenue XBRL exact-splits sweep over the full ticker universe.

This is a sidecar validation/promote tool, not production wiring. It:
  - loads the curated revenue map
  - runs mapped-only revenue extraction over the full non-null-qname universe
  - writes per-ticker primary/audit packets to the chosen out dir
  - writes compact summary + manifest files for later validation
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))

from xbrl_exact_splits import DEFAULT_MAPS_DIR, extract_segment_splits, load_map


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _run_one(
    ticker: str,
    out_dir: Path,
    maps_dir: Path,
    history_quarters: int,
    pit_cutoff: str | None,
) -> dict:
    t0 = time.time()
    pkt = extract_segment_splits(
        ticker=ticker,
        out_dir=out_dir,
        maps_dir=maps_dir,
        history_quarters=history_quarters,
        metric="revenue",
        pit_cutoff=pit_cutoff,
        allow_discovery_fallback=False,
        write_packets=True,
    )
    periods = pkt.get("per_period_splits", [])
    q4_derived = sum(1 for b in periods if b.get("is_derived_q4"))
    return {
        "ticker": ticker,
        "ok": True,
        "metric_qname": pkt.get("metric_qname"),
        "qname_source": pkt.get("qname_source"),
        "periods_emitted": len(periods),
        "q4_derived": q4_derived,
        "view_capability": pkt.get("view_capability", {}),
        "gaps": pkt.get("gaps", []),
        "elapsed_s": round(time.time() - t0, 3),
    }


def _write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    tmp.replace(path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run full mapped revenue XBRL exact-splits sweep.")
    ap.add_argument("--maps-dir", default=str(DEFAULT_MAPS_DIR), help="Directory containing revenue_map_783.jsonl")
    ap.add_argument("--out-dir", default=f"/tmp/xbrl_exact_splits_sweep_{_now_stamp()}",
                    help="Directory for per-ticker packets and summary artifacts")
    ap.add_argument("--history-quarters", type=int, default=8, help="Periods to request per ticker")
    ap.add_argument("--pit-cutoff", default=None, help="Optional PIT cutoff for historical sweep")
    ap.add_argument("--workers", type=int, default=4, help="Parallel workers")
    args = ap.parse_args(argv)

    maps_dir = Path(args.maps_dir)
    out_dir = Path(args.out_dir)
    packets_dir = out_dir / "packets"
    packets_dir.mkdir(parents=True, exist_ok=True)

    revenue_map = load_map(maps_dir, "revenue")
    tickers = sorted([t for t, row in revenue_map.items() if row.get("qname") is not None])

    started_at = datetime.now(timezone.utc).isoformat()
    results: list[dict] = []
    failures: list[dict] = []

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futs = {
            ex.submit(_run_one, ticker, packets_dir, maps_dir, args.history_quarters, args.pit_cutoff): ticker
            for ticker in tickers
        }
        for fut in as_completed(futs):
            ticker = futs[fut]
            try:
                results.append(fut.result())
            except Exception as e:
                failures.append({"ticker": ticker, "ok": False, "error": str(e)})

    results.sort(key=lambda r: r["ticker"])
    failures.sort(key=lambda r: r["ticker"])

    summary = {
        "schema_version": "xbrl_exact_splits_sweep.v1",
        "metric": "revenue",
        "mode": "historical" if args.pit_cutoff else "live",
        "pit_cutoff": args.pit_cutoff,
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "workers": args.workers,
        "mapped_ticker_count": len(tickers),
        "success_count": len(results),
        "failure_count": len(failures),
        "view_capability_counts": {
            "segments": sum(1 for r in results if r.get("view_capability", {}).get("segments")),
            "geography": sum(1 for r in results if r.get("view_capability", {}).get("geography")),
            "product_service": sum(1 for r in results if r.get("view_capability", {}).get("product_service")),
        },
        "q4_derived_ticker_count": sum(1 for r in results if r.get("q4_derived")),
        "manifest_path": str(out_dir / "manifest.json"),
        "failures_path": str(out_dir / "failures.json"),
        "packets_dir": str(packets_dir),
    }

    manifest = {
        "schema_version": "xbrl_exact_splits_manifest.v1",
        "summary": summary,
        "results": results,
    }

    _write_json(out_dir / "summary.json", summary)
    _write_json(out_dir / "manifest.json", manifest)
    _write_json(out_dir / "failures.json", failures)

    print(json.dumps(summary, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
