#!/usr/bin/env python3
"""Earnings Orchestrator — minimal bundle assembly and rendering.

Usage:
    python scripts/earnings/earnings_orchestrator.py CRM 0001628280-25-004383
    python scripts/earnings/earnings_orchestrator.py CRM 0001628280-25-004383 --pit 2025-02-26T17:00:00-05:00
    python scripts/earnings/earnings_orchestrator.py CRM --quarter-info-json /tmp/quarter_info.json
    python scripts/earnings/earnings_orchestrator.py CRM 0001628280-25-004383 --save
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "scripts/earnings"))
sys.path.insert(0, str(_PROJECT_ROOT / ".claude/skills/earnings-orchestrator/scripts"))

from builder_adapters import (
    build_8k_packet,
    build_guidance_history,
    build_inter_quarter_context,
    build_peer_earnings_snapshot,
    build_macro_snapshot,
    build_consensus,
    build_prior_financials,
)
from quarter_identity import resolve_quarter_info

from dotenv import load_dotenv
load_dotenv(str(_PROJECT_ROOT / ".env"), override=True)



def load_quarter_info_json(path: str) -> dict[str, Any]:
    """Load quarter_info from a JSON file."""
    with open(path, encoding="utf-8") as f:
        quarter_info = json.load(f)
    if not isinstance(quarter_info, dict):
        raise ValueError(f"quarter_info JSON must be an object: {path}")
    return quarter_info


def validate_quarter_info(quarter_info: dict[str, Any]) -> None:
    """Validate the common quarter_info shape expected by adapters."""
    required = [
        "accession_8k",
        "filed_8k",
        "market_session",
        "period_of_report",
        "prev_8k_ts",
        "quarter_label",
    ]
    missing = [key for key in required if key not in quarter_info]
    if missing:
        raise ValueError(f"quarter_info missing keys: {', '.join(missing)}")
    if not quarter_info.get("period_of_report"):
        raise ValueError(
            f"period_of_report is None — quarter identity could not be resolved. "
            f"Gaps: {quarter_info.get('gaps', 'unknown')}"
        )
    if not quarter_info.get("quarter_label"):
        raise ValueError(
            f"quarter_label is None — fiscal identity could not be derived. "
            f"Gaps: {quarter_info.get('gaps', 'unknown')}"
        )


# ── Stub builders for items 7 & 8 ───────────────────────────────────

def _build_previous_earnings(ticker, quarter_info, pit_cutoff=None, out_path=None, **kw):
    return []  # stub — will return packet dict when builder is real


def _build_previous_earnings_lessons(ticker, quarter_info, pit_cutoff=None, out_path=None, **kw):
    return []  # stub — will return packet dict when builder is real


# ── Bundle assembly ──────────────────────────────────────────────────

BUNDLE_ITEM_ORDER = [
    "8k_packet",
    "guidance_history",
    "inter_quarter_context",
    "peer_earnings_snapshot",
    "macro_snapshot",
    "consensus",
    "previous_earnings",
    "previous_earnings_lessons",
    "prior_financials",
]

BUILDERS = {
    "8k_packet":                 build_8k_packet,
    "guidance_history":          build_guidance_history,
    "inter_quarter_context":     build_inter_quarter_context,
    "peer_earnings_snapshot":    build_peer_earnings_snapshot,
    "macro_snapshot":            build_macro_snapshot,
    "consensus":                 build_consensus,
    "previous_earnings":         _build_previous_earnings,
    "previous_earnings_lessons": _build_previous_earnings_lessons,
    "prior_financials":          build_prior_financials,
}


_TRANSIENT_MARKERS = ("defunct connection", "serviceunavailable", "connection refused",
                      "connection reset", "broken pipe", "timed out", "pool")


def _is_transient(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(m in msg for m in _TRANSIENT_MARKERS)


def _run_builder(fn, ticker, quarter_info, pit_cutoff, out_path,
                 retries: int = 2, backoff: float = 2.0):
    """Run a single builder with retry on transient (connection) errors."""
    for attempt in range(retries + 1):
        try:
            return fn(ticker, quarter_info, pit_cutoff, out_path)
        except Exception as e:
            if attempt < retries and _is_transient(e):
                wait = backoff * (attempt + 1)
                log.warning("Builder %s attempt %d failed (transient): %s — retrying in %.1fs",
                            fn.__name__, attempt + 1, e, wait)
                time.sleep(wait)
                continue
            raise


def build_prediction_bundle(ticker: str, quarter_info: dict,
                            pit_cutoff: str | None = None,
                            out_dir: str | None = None) -> dict:
    """Run all 9 builders in parallel, return merged bundle dict."""
    validate_quarter_info(quarter_info)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = Path(out_dir) if out_dir else Path("/tmp/earnings") / run_id

    def out(name: str) -> str:
        return str(base / f"{name}.json")

    results = {}
    errors = {}

    with ThreadPoolExecutor(max_workers=len(BUNDLE_ITEM_ORDER)) as pool:
        futures = {
            pool.submit(_run_builder, BUILDERS[name], ticker, quarter_info,
                        pit_cutoff, out(name)): name
            for name in BUNDLE_ITEM_ORDER
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as e:
                errors[name] = str(e)

    if "8k_packet" in errors:
        raise RuntimeError(f"HARD FAIL — 8k_packet builder failed: {errors['8k_packet']}")

    bundle = {
        "schema_version": "prediction_bundle.v1",
        "ticker": ticker,
        "quarter_info": quarter_info,
        "pit_cutoff": pit_cutoff,
        "assembled_at": datetime.now(timezone.utc).isoformat(),
        "builder_errors": errors if errors else None,
    }
    for name in BUNDLE_ITEM_ORDER:
        bundle[name] = results.get(name)
    return bundle


# ── Bundle rendering ─────────────────────────────────────────────────

SECTION_TITLES = {
    "8k_packet":                 "8-K Earnings Results (Current Quarter)",
    "guidance_history":          "Company Guidance History",
    "inter_quarter_context":     "Inter-Quarter Events (News, Filings, Analyst Actions)",
    "peer_earnings_snapshot":    "Sector Peer Earnings & Reactions",
    "macro_snapshot":            "Macro Environment",
    "consensus":                 "Analyst Consensus (EPS & Revenue Expectations)",
    "previous_earnings":         "Previous Quarter Earnings Picture",
    "previous_earnings_lessons": "Lessons From Previous Prediction",
    "prior_financials":          "Multi-Quarter Financial Trends",
}


def render_bundle_text(bundle: dict) -> str:
    """Render the 9-item bundle as sectioned text for the predictor prompt."""
    parts = []
    parts.append(f"# Prediction Bundle — {bundle['ticker']}")
    parts.append(f"Assembled: {bundle['assembled_at']}")
    if bundle.get("pit_cutoff"):
        parts.append(f"PIT cutoff: {bundle['pit_cutoff']}")
    parts.append("")

    for i, name in enumerate(BUNDLE_ITEM_ORDER, 1):
        title = SECTION_TITLES[name]
        parts.append(f"## {i}. {title}")

        if name in (bundle.get("builder_errors") or {}):
            parts.append(f"[BUILDER ERROR: {bundle['builder_errors'][name]}]")
            parts.append("")
            continue

        item = bundle.get(name)
        if item is None:
            parts.append("[NO DATA]")
            parts.append("")
            continue

        parts.append(json.dumps(item, indent=2, default=str, ensure_ascii=False))
        parts.append("")

    return "\n".join(parts)


def run_core_flow(ticker: str, quarter_info: dict,
                  pit_cutoff: str | None = None,
                  out_dir: str | None = None) -> tuple[dict, str]:
    """Build the bundle and render it as sectioned text."""
    bundle = build_prediction_bundle(
        ticker=ticker,
        quarter_info=quarter_info,
        pit_cutoff=pit_cutoff,
        out_dir=out_dir,
    )
    rendered = render_bundle_text(bundle)
    return bundle, rendered


def write_json(path: Path, payload: Any) -> None:
    """Write JSON with parent directory creation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str, ensure_ascii=False)


def write_text(path: Path, content: str) -> None:
    """Write text with parent directory creation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ── CLI ──────────────────────────────────────────────────────────────

def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Earnings prediction bundle assembly")
    parser.add_argument("ticker", help="Company ticker")
    parser.add_argument("accession", nargs="?", help="8-K accession number")
    parser.add_argument("--quarter-info-json", default=None,
                        help="Path to a quarter_info JSON file (alternative to accession)")
    parser.add_argument("--pit", default=None, help="PIT cutoff (ISO8601) for historical mode")
    parser.add_argument("--save", action="store_true", help="Write context_bundle.json to disk")
    parser.add_argument("--save-dir", default=None,
                        help="Optional output directory for saved bundle artifacts")
    args = parser.parse_args()

    if bool(args.accession) == bool(args.quarter_info_json):
        parser.error("Provide exactly one of ACCESSION or --quarter-info-json")

    if args.quarter_info_json:
        print(f"Loading quarter info for {args.ticker} from {args.quarter_info_json} ...", flush=True)
        quarter_info = load_quarter_info_json(args.quarter_info_json)
    else:
        print(f"Resolving quarter identity for {args.ticker} / {args.accession} ...", flush=True)
        quarter_info = resolve_quarter_info(args.ticker, args.accession)

    validate_quarter_info(quarter_info)
    print(f"  filed_8k:    {quarter_info['filed_8k']}")
    print(f"  period:      {quarter_info['period_of_report']}")
    print(f"  session:     {quarter_info['market_session']}")
    print(f"  prev_8k_ts:  {quarter_info['prev_8k_ts']}")
    print(f"  quarter:     {quarter_info['quarter_label']}")
    print(f"  source:      {quarter_info.get('quarter_identity_source', 'n/a')}")
    if quarter_info.get("gaps"):
        for g in quarter_info["gaps"]:
            print(f"  GAP: {g['type']}: {g['reason']}")
    print()

    print(f"Building prediction bundle ({len(BUILDERS)} builders in parallel) ...", flush=True)
    t0 = datetime.now()
    bundle, rendered = run_core_flow(
        ticker=args.ticker,
        quarter_info=quarter_info,
        pit_cutoff=args.pit,
        out_dir=args.save_dir,
    )
    elapsed = (datetime.now() - t0).total_seconds()

    ok = [k for k in BUNDLE_ITEM_ORDER if k not in (bundle.get("builder_errors") or {})]
    fail = list((bundle.get("builder_errors") or {}).keys())
    print(f"  Done in {elapsed:.1f}s — {len(ok)} ok, {len(fail)} failed")
    if fail:
        for name in fail:
            print(f"  FAIL: {name}: {bundle['builder_errors'][name]}")
    print()

    print(f"Rendered bundle: {len(rendered)} chars, {rendered.count(chr(10))} lines")

    if args.save:
        quarter_dir = quarter_info.get("quarter_label") or quarter_info["accession_8k"]
        base_dir = Path(args.save_dir) if args.save_dir else (
            Path("earnings-analysis/Companies") / args.ticker.upper() / "events" / quarter_dir / "prediction"
        )
        bundle_path = base_dir / "context_bundle.json"
        rendered_path = base_dir / "context_bundle_rendered.txt"
        write_json(bundle_path, bundle)
        write_text(rendered_path, rendered)
        print(f"Saved: {bundle_path}")
        print(f"Saved: {rendered_path}")


if __name__ == "__main__":
    main()
