#!/usr/bin/env python3
"""Earnings Orchestrator — minimal bundle assembly and rendering.

Usage:
    python scripts/earnings/earnings_orchestrator.py CRM 0001628280-25-004383
    python scripts/earnings/earnings_orchestrator.py CRM 0001628280-25-004383 --pit 2025-02-26T17:00:00-05:00
    python scripts/earnings/earnings_orchestrator.py CRM --quarter-info-json /tmp/quarter_info.json
    python scripts/earnings/earnings_orchestrator.py CRM 0001628280-25-004383 --save
"""
from __future__ import annotations

import asyncio
import argparse
import json
import logging
import math
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

from scripts.earnings.builders import (
    build_8k_packet,
    build_guidance_history,
    build_inter_quarter_context,
    build_peer_earnings_snapshot,
    build_macro_snapshot,
    build_consensus,
    build_prior_financials,
)
from config.llm_models import LEARNER, PREDICTOR
from quarter_identity import resolve_quarter_info
from scripts.earnings.utils import neo4j_session

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


# ── Bundle assembly ──────────────────────────────────────────────────

# The 7 parallel builders — each hits Neo4j/APIs and runs in ThreadPoolExecutor.
# learning_context is the logical 8th bundle field but is NOT a parallel builder:
# it's a lightweight local file read added after builder execution (see build_prediction_bundle).
BUNDLE_ITEM_ORDER = [
    "8k_packet",
    "guidance_history",
    "inter_quarter_context",
    "peer_earnings_snapshot",
    "macro_snapshot",
    "consensus",
    "prior_financials",
]

BUILDERS = {
    "8k_packet":                 build_8k_packet,
    "guidance_history":          build_guidance_history,
    "inter_quarter_context":     build_inter_quarter_context,
    "peer_earnings_snapshot":    build_peer_earnings_snapshot,
    "macro_snapshot":            build_macro_snapshot,
    "consensus":                 build_consensus,
    "prior_financials":          build_prior_financials,
}


_TRANSIENT_MARKERS = ("defunct connection", "serviceunavailable", "connection refused",
                      "connection reset", "broken pipe", "timed out", "pool")
_COMPANY_SECTOR_QUERY = """
MATCH (c:Company {ticker: $ticker})
OPTIONAL MATCH (c)-[:BELONGS_TO]->(:Industry)-[:BELONGS_TO]->(sec:Sector)
RETURN coalesce(c.sector, sec.name) AS sector
"""


def _is_transient(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(m in msg for m in _TRANSIENT_MARKERS)


# Anti-poisoning cache (amendment 2026-04-17): we use a manual dict that caches
# ONLY successful lookups. Failed lookups (Neo4j down, ticker absent, empty
# string) are re-queried on every call so a single transient Neo4j hiccup does
# NOT poison the cache for the lifetime of the process.
_SECTOR_CACHE: dict[str, str] = {}


def _lookup_company_sector(ticker: str) -> str | None:
    """Best-effort sector lookup for learning-context filtering and source_sector
    stamping. Only successful results are cached; None results are re-queried
    on every call to prevent transient-Neo4j-failure cache poisoning.
    """
    symbol = str(ticker or "").upper().strip()
    if not symbol:
        return None
    if symbol in _SECTOR_CACHE:
        return _SECTOR_CACHE[symbol]

    try:
        with neo4j_session() as (session, err):
            if err or session is None:
                log.warning("Sector lookup unavailable for %s: %s", symbol, err)
                return None  # intentionally NOT cached
            row = session.run(_COMPANY_SECTOR_QUERY, ticker=symbol).single()
    except Exception as e:
        log.warning("Sector lookup failed for %s: %s", symbol, e)
        return None  # intentionally NOT cached

    if not row:
        log.warning("Sector lookup returned no row for %s (ticker may be out-of-universe)", symbol)
        return None

    sector = row.data().get("sector")
    if sector is None:
        log.warning("source_sector is None for %s (ticker may be out-of-universe)", symbol)
        return None
    sector_text = str(sector).strip()
    if not sector_text:
        return None
    _SECTOR_CACHE[symbol] = sector_text  # success only
    return sector_text


def _normalize_sector(sector: str | None) -> str | None:
    if sector is None:
        return None
    normalized = " ".join(str(sector).split()).casefold()
    return normalized or None


def _run_builder(fn, ticker, quarter_info, pit_cutoff, out_path,
                 builder_kwargs: dict | None = None,
                 retries: int = 2, backoff: float = 2.0):
    """Run a single builder with retry on transient (connection) errors.

    `builder_kwargs` is a dict of additional kwargs threaded through the
    adapter (every adapter declares **kwargs; unrecognized keys are dropped).
    """
    builder_kwargs = builder_kwargs or {}
    for attempt in range(retries + 1):
        try:
            return fn(ticker, quarter_info, pit_cutoff, out_path, **builder_kwargs)
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
                            out_dir: str | None = None,
                            related_filings_dir: str | None = None) -> dict:
    """Run all 7 standardized builders in parallel, return merged bundle dict.

    `related_filings_dir`: when provided, `inter_quarter_context` writes
    per-accession sidecar markdown files for selected related 8-Ks. Pass None
    for dry inspection (no on-disk side effects).
    """
    validate_quarter_info(quarter_info)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = Path(out_dir) if out_dir else Path("/tmp/earnings") / run_id

    def out(name: str) -> str:
        return str(base / f"{name}.json")

    # Per-builder kwargs (each adapter declares **kwargs, so unknown keys drop).
    per_builder_kwargs: dict[str, dict] = {}
    if related_filings_dir:
        per_builder_kwargs["inter_quarter_context"] = {
            "related_filings_dir": str(related_filings_dir)
        }

    results = {}
    errors = {}

    with ThreadPoolExecutor(max_workers=len(BUNDLE_ITEM_ORDER)) as pool:
        futures = {
            pool.submit(_run_builder, BUILDERS[name], ticker, quarter_info,
                        pit_cutoff, out(name),
                        per_builder_kwargs.get(name)): name
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

    # learning_context is the logical 8th bundle field. It remains outside
    # BUNDLE_ITEM_ORDER because the main work is local lesson-file loading;
    # sector-aware filtering may do a cached company-metadata lookup when needed.
    # T1.5b: pit_cutoff flows in from the bundle caller so historical reruns
    # filter out lessons stamped after the predictor's cutoff. Live mode
    # (pit_cutoff=None) bypasses the filter entirely.
    try:
        sector = (results.get("8k_packet") or {}).get("sector") or _lookup_company_sector(ticker)
        bundle["learning_context"] = build_learning_context(
            ticker, sector=sector, pit_cutoff=pit_cutoff,
            current_quarter_label=quarter_info.get("quarter_label"),
        )
    except AssertionError:
        # Pipeline invariant violation — re-raise so it surfaces visibly. NEVER
        # swallow into the broad-except fallback below; the invariant exists
        # specifically to halt production on inconsistent learner_paths state.
        raise
    except Exception as e:
        log.warning("learning_context builder failed (non-fatal): %s", e)
        bundle["learning_context"] = {
            "ticker_lessons": [], "global_lessons": [],
            "ticker_ref": None, "global_ref": None,
            "_allowed_learner_paths": [],   # schema consistency on fallback
        }

    # U67: attach the event-scoped source-ID catalog used by the predictor
    # for evidence_ledger[i].source_id citations and by the validator for
    # exact set-membership grounding.
    bundle["evidence_source_catalog"] = build_evidence_source_catalog(bundle)

    return bundle


# ── Bundle rendering ─────────────────────────────────────────────────

SECTION_TITLES = {
    "8k_packet":                 "8-K Earnings Results (Current Quarter)",
    "guidance_history":          "Company Guidance History",
    "inter_quarter_context":     "Inter-Quarter Events (News, Filings, Analyst Actions)",
    "peer_earnings_snapshot":    "Sector Peer Earnings & Reactions",
    "macro_snapshot":            "Macro Environment",
    "consensus":                 "Analyst Consensus (EPS & Revenue Expectations)",
    "prior_financials":          "Multi-Quarter Financial Trends",
}


# ════════════════════════════════════════════════════════════════════════════════
# RENDERER EXTRACTION SHIM BLOCK (seeded commit 8/20, populated commits 8-18)
# All bundle-renderer code is being moved to scripts/earnings/renderer/.
# Imports below preserve `from earnings_orchestrator import X` for legacy callers.
# DO NOT REMOVE without auditing every importer in the repo.
# Submodule-direct imports (NOT via renderer/__init__.py) — works regardless of
# __init__.py being populated.
# ════════════════════════════════════════════════════════════════════════════════
from scripts.earnings.renderer._formatters import (  # noqa: F401
    _md_table, _fmt_num, _fmt_money, _fmt_pct,
    _fmt_financial_cell,  # canonical home (financials.py keeps a re-export for back-compat)
)
from scripts.earnings.renderer.header import _render_header  # noqa: F401
from scripts.earnings.renderer.guidance import (  # noqa: F401
    _fmt_guidance_value, _compute_change, _fmt_metric_label,
    _guidance_target_key, _guidance_target_label, _is_segmented_label,
    _render_forward_guidance,
)
from scripts.earnings.renderer.financials import (  # noqa: F401
    _FINANCIAL_SECTIONS,
    _fmt_split_pct,
    _render_revenue_splits, _render_prior_financials,
)
from scripts.earnings.renderer.consensus import _render_consensus_history  # noqa: F401
from scripts.earnings.renderer.results import (  # noqa: F401
    _render_results_and_expectations, _render_reference,
)
from scripts.earnings.renderer.inter_quarter import (  # noqa: F401
    _iq_cell, _iq_val, _iq_bool, _iq_join,
    _iq_header, _iq_days_table, _iq_adj_returns,
    _iq_news_table, _iq_filings_table,
    _iq_dividends_table, _iq_splits_table,
    _render_inter_quarter,
)
from scripts.earnings.renderer.peers import _render_peer_earnings  # noqa: F401
from scripts.earnings.renderer.macro import _render_macro  # noqa: F401
from scripts.earnings.renderer.lessons import _render_learning_context  # noqa: F401
from scripts.earnings.renderer.bundle import render_bundle_text  # noqa: F401
# Sibling utility (not in renderer package — shared between renderer + validator)
from scripts.earnings._text_utils import _normalize_lesson_text  # noqa: F401


# Dead constant from pre-renderer-extract baseline (line 990). Verified zero
# external usages but kept here per migration plan §2.2 — deletion deferred
# to a follow-up PR.
_IQ_ANALYST_CHANNELS = frozenset({
    "Analyst Ratings", "Upgrades", "Downgrades", "Reiteration",
    "Initiation", "Price Target",
})


def run_core_flow(ticker: str, quarter_info: dict,
                  pit_cutoff: str | None = None,
                  out_dir: str | None = None,
                  related_filings_dir: str | None = None) -> tuple[dict, str]:
    """Build the bundle and render it as sectioned text.

    `related_filings_dir`: optional. When set, `inter_quarter_context` writes
    per-accession sidecar markdown files. Pass None for dry inspection
    (no on-disk side effects).
    """
    bundle = build_prediction_bundle(
        ticker=ticker,
        quarter_info=quarter_info,
        pit_cutoff=pit_cutoff,
        out_dir=out_dir,
        related_filings_dir=related_filings_dir,
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


def get_prediction_dir(ticker: str, quarter_info: dict, save_dir: str | None = None) -> Path:
    """Return the prediction artifact directory for this event."""
    if save_dir:
        return Path(save_dir)
    quarter_dir = quarter_info.get("quarter_label") or quarter_info["accession_8k"]
    return Path("earnings-analysis/Companies") / ticker.upper() / "events" / quarter_dir / "prediction"


def get_quarter_dir(ticker: str, quarter_info: dict, save_dir: str | None = None) -> Path:
    """Return the top-level quarter directory (parent of prediction/, learning/, experiments/).

    Added 2026-04-17 per obsidian_thinking.md: context_bundle.{json,txt} are
    PROMOTED from events/{Q}/prediction/ up to events/{Q}/ (quarter root) so
    they are shared by predictor + learner + future readers.

    U65 (2026-04-30): when ``save_dir`` is supplied, the quarter root IS
    ``save_dir`` itself. Pre-U65 returned ``Path(save_dir).parent``, which
    aliased to the shared parent (e.g. ``/tmp``) for any caller passing
    ``--save-dir /tmp/smoke_<TICKER>`` and caused parallel runs to race
    on ``/tmp/context_bundle.json``.
    """
    if save_dir:
        return Path(save_dir)
    quarter_dir = quarter_info.get("quarter_label") or quarter_info["accession_8k"]
    return Path("earnings-analysis/Companies") / ticker.upper() / "events" / quarter_dir


def get_prediction_paths(ticker: str, quarter_info: dict,
                         save_dir: str | None = None) -> dict[str, Path]:
    """Return canonical paths for predictor bundle + result artifacts.

    As of obsidian_thinking.md (2026-04-17), ``context_bundle.{json,txt}``
    live at the QUARTER ROOT (``events/{Q}/``), not under ``prediction/``.
    ``result.json`` stays under ``prediction/``.
    """
    base_dir = get_prediction_dir(ticker, quarter_info, save_dir)
    q_dir = get_quarter_dir(ticker, quarter_info, save_dir)
    return {
        "base_dir": base_dir,
        "bundle_path": q_dir / "context_bundle.json",
        "rendered_path": q_dir / "context_bundle_rendered.txt",
        "result_path": base_dir / "result.json",
        "section_audit_path": base_dir / "section_audit.json",
    }


# ── U67: evidence_source_catalog (event-scoped per-fact citation IDs) ──

def build_evidence_source_catalog(bundle: dict[str, Any]) -> list[str]:
    """Generate the bundle's event-scoped source-ID catalog (U67 / Tier M+/C).

    Each ID has the shape:

        SRC:<TICKER>:<QUARTER_LABEL>:<ACCESSION_8K>#<location>

    The event prefix (ticker + quarter + accession) makes the IDs unique to
    *this* in-memory bundle. A wrong-bundle contamination (U65 race class)
    cannot produce a matching ID because the predictor would copy the OTHER
    bundle's prefix. The location suffix names the specific fact — sections,
    exhibits, consensus rows, peers, news refs, lessons, etc.

    Returned list preserves render order with first-seen dedupe. Validator
    uses set-membership.
    """
    qi = bundle.get("quarter_info") or {}
    ticker = (qi.get("ticker") or bundle.get("ticker") or "?").upper()
    quarter = qi.get("quarter_label") or "?"
    accession = qi.get("accession_8k") or "?"
    prefix = f"SRC:{ticker}:{quarter}:{accession}"

    catalog: list[str] = [
        f"{prefix}#header",
        f"{prefix}#quarter_info",
    ]

    # Section-level catch-alls (so predictor can cite "the §1.3 consensus" overall).
    section_keys = {
        "consensus":              "S1.consensus",
        "8k_packet":              "S2.8k_packet",
        "guidance_history":       "S3.guidance",
        "prior_financials":       "S5.prior_financials",
        "inter_quarter_context":  "S6.inter_quarter",
        "peer_earnings_snapshot": "S7.peers",
        "macro_snapshot":         "S8.macro",
        "learning_context":       "S10.lessons",
    }
    for k, loc in section_keys.items():
        if bundle.get(k):
            catalog.append(f"{prefix}#{loc}")

    # 8-K exhibits + named sections
    pkt = bundle.get("8k_packet") or {}
    for ex in pkt.get("exhibits_99") or []:
        ex_num = ex.get("exhibit_number")
        if ex_num:
            catalog.append(f"{prefix}#S2.exhibit.{str(ex_num).replace(' ', '_')}")
    for ex in pkt.get("exhibits_other") or []:
        ex_num = ex.get("exhibit_number")
        if ex_num:
            catalog.append(f"{prefix}#S2.exhibit.{str(ex_num).replace(' ', '_')}")
    for sec in pkt.get("sections") or []:
        nm = sec.get("section_name")
        if nm:
            catalog.append(f"{prefix}#S2.section.{nm}")

    # Consensus quarterly rows + forward estimates
    cs = bundle.get("consensus") or {}
    for i, _ in enumerate(cs.get("quarterly_rows") or []):
        catalog.append(f"{prefix}#S1.consensus.row[{i}]")
    for i, _ in enumerate(cs.get("forward_estimates") or []):
        catalog.append(f"{prefix}#S1.consensus.forward[{i}]")

    # Guidance history entries (real schema: guidance_history.series[i])
    gh = bundle.get("guidance_history") or {}
    for i, entry in enumerate(gh.get("series") or []):
        metric_id = entry.get("metric_id")
        if metric_id:
            catalog.append(f"{prefix}#S3.guidance[{i}]:{metric_id}")
        else:
            catalog.append(f"{prefix}#S3.guidance[{i}]")

    # Prior financials per-quarter
    pf = bundle.get("prior_financials") or {}
    for q in pf.get("quarters") or []:
        period = q.get("period_of_report") or q.get("period")
        if period:
            catalog.append(f"{prefix}#S5.financials.{period}")

    # Inter-quarter events (real schema: inter_quarter_context.days[].events[]).
    # The RENDERED bundle (inter_quarter.py:147,182) labels news as N1..Nk and
    # filings as F1..Fk in chronological render order. The catalog therefore
    # emits BOTH the rendered alias (#S6.news.N{i} / #S6.filing.F{i}) so the
    # predictor can copy what it sees, AND the raw event_ref (which carries
    # `news:` / `report:` prefix) for traceability.
    iq = bundle.get("inter_quarter_context") or {}
    news_idx = 0
    filing_idx = 0
    for day in iq.get("days") or []:
        for ev in day.get("events") or []:
            ev_type = ev.get("type")
            if ev_type == "news":
                news_idx += 1
                catalog.append(f"{prefix}#S6.news.N{news_idx}")
            elif ev_type == "filing":
                filing_idx += 1
                catalog.append(f"{prefix}#S6.filing.F{filing_idx}")
            ref = ev.get("event_ref")
            if ref:
                catalog.append(f"{prefix}#S6.event.{ref}")
            else:
                # Fallback for events missing event_ref but carrying id/accession.
                ev_id = ev.get("id") or ev.get("accession")
                if ev_id:
                    catalog.append(f"{prefix}#S6.event.{ev_id}")

    # Peers
    pe = bundle.get("peer_earnings_snapshot") or {}
    for peer in pe.get("peers") or []:
        pt = peer.get("ticker")
        if pt:
            catalog.append(f"{prefix}#S7.peer.{str(pt).upper()}")

    # Macro catalysts (real schema: macro_snapshot.catalysts).
    # Bucket shapes (verified against AVGO Q4 fixture):
    #   today / yesterday → {date, headlines: [headline_dict, ...]}
    #   earlier           → [[date_str, headline_dict], [date_str, headline_dict], ...]
    # Renderer (renderer/macro.py:126) iterates each pair to expose the bz_id;
    # the catalog must mirror that to keep U67 set-membership exhaustive.
    ms = bundle.get("macro_snapshot") or {}
    mc = ms.get("catalysts") or {}
    def _headline_list(bucket_val):
        if isinstance(bucket_val, list):
            out: list[dict] = []
            for item in bucket_val:
                if isinstance(item, dict):
                    out.append(item)
                elif isinstance(item, list) and len(item) >= 2 and isinstance(item[1], dict):
                    out.append(item[1])    # [date_str, headline_dict] pair
            return out
        if isinstance(bucket_val, dict):
            return bucket_val.get("headlines") or []
        return []
    for bucket in ("today", "yesterday", "earlier"):
        for i, cat in enumerate(_headline_list(mc.get(bucket))):
            if not isinstance(cat, dict):
                continue
            bz = cat.get("bz_id")
            if bz:
                catalog.append(f"{prefix}#S8.macro.bz:{bz}")
            else:
                catalog.append(f"{prefix}#S8.macro.{bucket}[{i}]")

    # Lesson markers (U45+U66): flat L1..Ln matching renderer's
    # ## Lessons To Label section. Both walks share iter_labeled_lessons
    # in _text_utils so numbering can never drift.
    from scripts.earnings._text_utils import iter_labeled_lessons
    lc = bundle.get("learning_context") or {}
    for n, _scope, _entry, _body in iter_labeled_lessons(lc):
        catalog.append(f"{prefix}#S10.lesson.L{n}")

    # Preserve render order (not sorted). Dedupe first-seen-wins so
    # repeats from cross-walks don't duplicate but the catalog still
    # mirrors the order in which the predictor encounters anchors.
    seen: set[str] = set()
    out: list[str] = []
    for sid in catalog:
        if sid not in seen:
            seen.add(sid)
            out.append(sid)
    return out


def validate_prediction_result(payload: dict[str, Any],
                               expected_ticker: str,
                               expected_quarter: str,
                               *,
                               expected_lesson_texts: list[str] | None = None,
                               expected_source_ids: list[str] | set[str] | None = None) -> None:
    """Validator for prediction_result.v1 including T1 labeled-lesson-consumption contract.

    T1 (added 2026-04-19 per .claude/plans/learner.md Appendix B):
      - `lesson_labels[]` is required (no backward-compat — corpus wiped).
      - Each entry validated for shape/enum/sentinel discipline.
      - If `expected_lesson_texts` is provided (kwarg), positional equality is
        enforced against the renderer-emitted list (same source of truth).
      - Every `key_drivers[i].cites_lesson_indices[j]` must point to a
        `confirmed` label.
      - `analysis` must not verbatim-quote a non-confirmed lesson ≥30 chars.

    `expected_lesson_texts=None` skips only the positional check — shape/
    enum/citation/analysis-floor still fire. Used for offline audit reads
    without the bundle in scope.
    """
    required = [
        "schema_version",
        "ticker",
        "quarter_label",
        "direction",
        "confidence_score",
        "confidence_bucket",
        "expected_move_range_pct",
        "magnitude_bucket",
        "key_drivers",
        "data_gaps",
        "evidence_ledger",
        "analysis",
        "lesson_labels",           # T1
        "predicted_at",
        "model_version",
        "prompt_version",
    ]
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"prediction/result.json missing keys: {', '.join(missing)}")

    if payload["schema_version"] != "prediction_result.v1":
        raise ValueError(f"unexpected schema_version: {payload['schema_version']}")

    if str(payload["ticker"]).upper() != expected_ticker.upper():
        raise ValueError(
            f"ticker mismatch in prediction/result.json: {payload['ticker']} != {expected_ticker}"
        )

    if payload["quarter_label"] != expected_quarter:
        raise ValueError(
            "quarter_label mismatch in prediction/result.json: "
            f"{payload['quarter_label']} != {expected_quarter}"
        )

    if payload["direction"] not in {"long", "short", "no_call"}:
        raise ValueError(f"invalid direction: {payload['direction']}")

    if payload["confidence_bucket"] not in {"high", "moderate", "low", "no_call"}:
        raise ValueError(f"invalid confidence_bucket: {payload['confidence_bucket']}")

    if payload["magnitude_bucket"] not in {"large", "medium", "small", "none"}:
        raise ValueError(f"invalid magnitude_bucket: {payload['magnitude_bucket']}")

    score = payload["confidence_score"]
    if not isinstance(score, int) or not 0 <= score <= 100:
        raise ValueError(f"invalid confidence_score: {score}")

    move_range = payload["expected_move_range_pct"]
    if (
        not isinstance(move_range, list)
        or len(move_range) != 2
        or not all(isinstance(x, (int, float)) for x in move_range)
    ):
        raise ValueError("expected_move_range_pct must be a 2-number array")

    for key in ("key_drivers", "data_gaps", "evidence_ledger"):
        if not isinstance(payload[key], list):
            raise ValueError(f"{key} must be a list")

    if not isinstance(payload["analysis"], str) or not payload["analysis"].strip():
        raise ValueError("analysis must be a non-empty string")

    # ══════════════════════════════════════════════════════════════════
    # T1 — lesson_labels validation (template-overfit mitigation)
    # Spec: .claude/plans/learner.md Appendix B §6.3 / §8.4
    # ══════════════════════════════════════════════════════════════════
    _LABEL_ENUM = {"confirmed", "contradicted", "irrelevant"}

    labels = payload.get("lesson_labels")
    if labels is None:
        raise ValueError("lesson_labels must be a list, got null")
    if not isinstance(labels, list):
        raise ValueError(f"lesson_labels must be a list, got {type(labels).__name__}")

    # ─ Shape + enum + non-empty + sentinel discipline ─
    for i, entry in enumerate(labels):
        if not isinstance(entry, dict):
            raise ValueError(f"lesson_labels[{i}] must be an object")
        for req in ("lesson_text", "label", "bundle_evidence"):
            if req not in entry:
                raise ValueError(f"lesson_labels[{i}] missing required field: {req}")
        lbl = entry["label"]
        if lbl not in _LABEL_ENUM:
            raise ValueError(
                f"lesson_labels[{i}].label must be one of {sorted(_LABEL_ENUM)}, got {lbl!r}"
            )
        for sf in ("lesson_text", "bundle_evidence"):
            if not isinstance(entry[sf], str):
                raise ValueError(f"lesson_labels[{i}].{sf} must be a string")
        if not entry["lesson_text"].strip():
            raise ValueError(f"lesson_labels[{i}].lesson_text must be non-empty")
        evidence = entry["bundle_evidence"].strip()
        if not evidence:
            raise ValueError(f"lesson_labels[{i}].bundle_evidence must be non-empty")
        # Sentinel discipline: 'no relevant evidence' reserved for irrelevant
        if lbl in ("confirmed", "contradicted") and evidence.lower() == "no relevant evidence":
            raise ValueError(
                f"lesson_labels[{i}]: {lbl!r} requires specific bundle_evidence; "
                f"'no relevant evidence' sentinel is reserved for 'irrelevant'"
            )

    # ─ Positional equality against renderer-emitted expected list ─
    if expected_lesson_texts is not None:
        if len(labels) != len(expected_lesson_texts):
            raise ValueError(
                f"lesson_labels has {len(labels)} entries; "
                f"expected {len(expected_lesson_texts)} (from bundle.learning_context render order)"
            )
        for i, (got, want) in enumerate(zip(labels, expected_lesson_texts)):
            if _normalize_lesson_text(got["lesson_text"]) != _normalize_lesson_text(want):
                raise ValueError(
                    f"lesson_labels[{i}].lesson_text does not match expected "
                    f"(normalized comparison failed at position {i})"
                )

    # ─ cites_lesson_indices: confirmed-only on every key_drivers[i] ─
    for i, kd in enumerate(payload["key_drivers"]):
        if "cites_lesson_indices" not in kd:
            raise ValueError(
                f"key_drivers[{i}].cites_lesson_indices is required (may be empty list)"
            )
        cites = kd["cites_lesson_indices"]
        if not isinstance(cites, list):
            raise ValueError(
                f"key_drivers[{i}].cites_lesson_indices must be a list"
            )
        for j, idx in enumerate(cites):
            # Reject bool-as-int (Python quirk: isinstance(True, int) is True)
            if not isinstance(idx, int) or isinstance(idx, bool):
                raise ValueError(
                    f"key_drivers[{i}].cites_lesson_indices[{j}] must be int, "
                    f"got {type(idx).__name__}"
                )
            if not (0 <= idx < len(labels)):
                raise ValueError(
                    f"key_drivers[{i}].cites_lesson_indices[{j}] = {idx} out of range "
                    f"(len(lesson_labels)={len(labels)})"
                )
            if labels[idx]["label"] != "confirmed":
                raise ValueError(
                    f"key_drivers[{i}].cites_lesson_indices[{j}] = {idx} cites lesson "
                    f"with label={labels[idx]['label']!r}; only 'confirmed' labels may be cited"
                )

    # ─ Analysis-field substring floor: reject verbatim quote of non-confirmed lesson ─
    # Length guard at 30 chars: below, substring match risks innocent collision
    # on common short phrases. Real learner lessons are 80-150 chars.
    # See plan §3 invariant 6 + §8.4.
    _ANALYSIS_MIN_LEN = 30
    analysis_norm = _normalize_lesson_text(payload["analysis"])
    for i, entry in enumerate(labels):
        if entry["label"] == "confirmed":
            continue
        lt_norm = _normalize_lesson_text(entry["lesson_text"])
        if len(lt_norm) < _ANALYSIS_MIN_LEN:
            continue  # too short — paraphrase-evasion already acknowledged (§2.2)
        if lt_norm in analysis_norm:
            raise ValueError(
                f"analysis contains verbatim lesson_labels[{i}].lesson_text "
                f"(label={entry['label']!r}); paraphrase or omit — may not quote"
            )

    # ══════════════════════════════════════════════════════════════════
    # U67 — evidence_ledger.source_id grounding (Tier M+/C)
    # Each entry's source_id MUST be present in the bundle's
    # evidence_source_catalog, generated from the in-memory bundle.
    # This deterministically catches U65-class bundle-swap contamination:
    # a wrong bundle's source_ids carry a different event prefix and
    # therefore can never appear in the expected catalog.
    # Only enforced when caller passes expected_source_ids (production
    # path); offline/legacy callers default to None and skip the check.
    # ══════════════════════════════════════════════════════════════════
    if expected_source_ids is not None:
        anchor_set = set(expected_source_ids)
        ledger = payload["evidence_ledger"]
        if not ledger:
            raise ValueError(
                "evidence_ledger must be non-empty in production validation "
                "(zero entries bypasses U67 source_id grounding)"
            )
        # Fail closed: one missing/foreign source_id makes the whole prediction
        # untrusted because partial bundle contamination is still contamination.
        for i, entry in enumerate(ledger):
            if not isinstance(entry, dict):
                raise ValueError(f"evidence_ledger[{i}] must be an object")
            sid = entry.get("source_id")
            if not sid or not isinstance(sid, str):
                raise ValueError(
                    f"evidence_ledger[{i}].source_id is required (non-empty string); "
                    f"copy verbatim from the bundle's Evidence Source IDs catalog"
                )
            if sid not in anchor_set:
                raise ValueError(
                    f"evidence_ledger[{i}].source_id={sid!r} is not in the bundle's "
                    f"evidence_source_catalog — possible bundle contamination or "
                    f"fabricated citation"
                )


# ── Attribution / Learner Helpers ────────────────────────────────────


COMPANIES_DIR = Path("earnings-analysis/Companies")
LEARNINGS_DIR = Path("earnings-analysis/learnings")


def get_learning_dir(ticker: str, quarter_info: dict,
                     save_dir: str | None = None) -> Path:
    """Return the learning artifact directory for this event.

    Renamed from ``get_attribution_dir`` per obsidian_thinking.md
    (2026-04-17). The folder name changed from ``attribution/`` to
    ``learning/``; the schema name ``attribution_result.v2`` is preserved
    (schema versions are not renamed per plan).
    """
    if save_dir:
        return Path(save_dir)
    quarter_dir = quarter_info.get("quarter_label") or quarter_info["accession_8k"]
    return COMPANIES_DIR / ticker.upper() / "events" / quarter_dir / "learning"


def get_learning_paths(ticker: str, quarter_info: dict,
                       save_dir: str | None = None) -> dict[str, Path]:
    """Return canonical paths for learner result + lesson artifacts.

    As of obsidian_thinking.md (2026-04-17):
      - ``base_dir`` is ``events/{Q}/learning/`` (renamed from attribution/)
      - ``context_bundle_path`` is at the QUARTER ROOT (promoted from
        prediction/)
    """
    learn_dir = get_learning_dir(ticker, quarter_info, save_dir)
    q_dir = learn_dir.parent
    pred_dir = q_dir / "prediction"
    return {
        "base_dir": learn_dir,
        "result_path": learn_dir / "result.json",
        "prediction_result_path": pred_dir / "result.json",
        "context_bundle_path": q_dir / "context_bundle.json",
    }


def get_learnings_paths(ticker: str) -> dict[str, Path]:
    """Return canonical paths for ticker + global lesson files."""
    return {
        "ticker_lessons_path": LEARNINGS_DIR / "ticker" / f"{ticker.upper()}.json",
        "global_lessons_path": LEARNINGS_DIR / "global.json",
    }


# ── Attribution Result Validator (canonical standalone module) ─

from validate_learning import validate_attribution_result  # noqa: F401 — stdlib-only, hook-safe


# ── PIT Cutoff Derivation (three-tier rule per learner.md §3) ──


def derive_learner_pit(events: list[dict], current_index: int,
                       live_state_path: Path | None = None
                       ) -> tuple[str | None, str]:
    """Derive the PIT cutoff for the learner at position current_index.

    Three-tier rule:
      1. Q(n+1) exists in events → use Q(n+1)'s filed_8k
      2. No Q(n+1), but a live cycle exists → use live quarter's filed_8k
      3. No Q(n+1) and no live cycle → use current invocation time

    Rationale: the learner cutoff deliberately trails the predictor's
    bundle cutoff (``Q_n.filed_8k``) by roughly one quarter. In production
    a lesson cannot be written until the next cycle's data arrives, so
    ``Q_{n+1}.filed_8k`` is the tightest honest bound on when the lesson
    could have been produced. Stamping that value into each lesson's
    ``source_pit_cutoff`` keeps the T1.5b visibility predicate honest:
    ``lesson visible iff source_pit_cutoff <= predictor.pit_cutoff``.
    See :func:`run_learner_for_quarter` "PIT boundary" section and
    ``.claude/plans/learner.md`` §T1.5 for the full rationale.

    Sole caller: :func:`run_learner_for_quarter` (pit_mode=="historical"
    branch). This function is NEVER fed ``args.pit`` from the CLI.

    Returns (pit_cutoff, pit_boundary_source).
    For live mode (caller decides), returns (None, "").
    ⚠️ HUMAN REVIEW GATE — verify correctness across all tickers.
    """
    # Tier 1: next quarter in the events list
    if current_index + 1 < len(events):
        next_event = events[current_index + 1]
        next_filed = next_event.get("filed_8k")
        if next_filed:
            return next_filed, "next_quarter"

    # Tier 2: live cycle exists (live_state.json has a filed_8k for a quarter
    # that's not yet in the events list)
    if live_state_path and live_state_path.exists():
        try:
            ls = json.loads(live_state_path.read_text(encoding="utf-8"))
            live_filed = ls.get("filed_8k")
            if live_filed:
                return live_filed, "live_cycle"
        except (json.JSONDecodeError, OSError):
            pass

    # Tier 3: fallback to current invocation time
    return datetime.now(timezone.utc).isoformat(), "invocation_time"


# ── actual_return Normalization (Neo4j PUBLISHED_AS → normalized packet) ─


_RETURN_FIELD_MAP = {
    "daily_stock": "daily_stock_pct",
    "hourly_stock": "hourly_stock_pct",
    "session_stock": "session_stock_pct",
    "daily_macro": "daily_macro_pct",
    "daily_sector": "daily_sector_pct",
    "daily_industry": "daily_industry_pct",
}


def normalize_actual_return(neo4j_record: dict) -> dict:
    """Normalize Neo4j PUBLISHED_AS relationship fields to the learner contract.

    Input: dict with raw Neo4j field names (daily_stock, hourly_stock, etc.)
    Output: dict with normalized names (daily_stock_pct, hourly_stock_pct, etc.)
    """
    result: dict[str, Any] = {}
    for neo4j_name, normalized_name in _RETURN_FIELD_MAP.items():
        val = neo4j_record.get(neo4j_name)
        result[normalized_name] = float(val) if val is not None else None
    result["market_session"] = neo4j_record.get("market_session") or neo4j_record.get("market_session_8k")
    return result


def fetch_actual_return(ticker: str, accession: str) -> dict | None:
    """Fetch actual return data from Neo4j for a given 8-K accession.

    Queries the PRIMARY_FILER relationship on the 8-K report.
    Returns normalized actual_return dict, or None if not found or daily_stock missing.
    """
    try:
        from neo4j import GraphDatabase
    except ImportError:
        log.error("neo4j driver not available — cannot fetch actual_return")
        return None

    uri = os.environ.get("NEO4J_URI", "bolt://10.102.222.120:7687")
    user = os.environ.get("NEO4J_USERNAME", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "")

    query_str = """
    MATCH (r:Report {accessionNo: $accession})-[p:PRIMARY_FILER]->(c:Company {ticker: $ticker})
    RETURN p.daily_stock AS daily_stock,
           p.hourly_stock AS hourly_stock,
           p.session_stock AS session_stock,
           p.daily_macro AS daily_macro,
           p.daily_sector AS daily_sector,
           p.daily_industry AS daily_industry,
           r.market_session AS market_session
    LIMIT 1
    """
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            result = session.run(query_str, accession=accession, ticker=ticker.upper())
            record = result.single()
        driver.close()
    except Exception as e:
        log.error("Neo4j query failed for actual_return: %s", e)
        return None

    if not record:
        log.warning("No PUBLISHED_AS relationship found for %s / %s", ticker, accession)
        return None

    raw = dict(record)
    if raw.get("daily_stock") is None:
        log.warning("daily_stock is NULL for %s / %s — hard gate not met", ticker, accession)
        return None

    return normalize_actual_return(raw)


# ── Learner Orchestration (post-prediction sequential flow) ─────────


class LearnerOutcome:
    """Centralized taxonomy of every exit condition from ``run_learner_for_quarter``.

    Each of the function's 12 return sites maps to exactly one of these string
    constants. Callers that need to distinguish *skipped* (environmental, not
    a failure) from *failed* (pipeline defect) use the ``SKIPPED``/``FAILED``
    sets below instead of parsing the constants individually.

    Adding a new outcome: define a constant here, add it to the matching set,
    and ensure ``ALL`` contains it. The test in ``test_learner_outcomes.py``
    asserts ``len(ALL) == 12`` and that the sets are pairwise disjoint so a
    future addition that forgets to categorize is caught automatically.
    """

    SUCCEEDED                 = "succeeded"
    RECOVERED                 = "recovered"
    SKIPPED_NO_PREDICTION     = "skipped_no_prediction"
    SKIPPED_NO_DAILY_STOCK    = "skipped_no_daily_stock"
    FAILED_NO_RESULT          = "failed_no_result"
    FAILED_INVALID_JSON       = "failed_invalid_json"
    FAILED_NO_RESULT_RETRY    = "failed_no_result_retry"
    FAILED_INVALID_JSON_RETRY = "failed_invalid_json_retry"
    FAILED_VALIDATION         = "failed_validation"
    FAILED_RECOVERY_APPEND    = "failed_recovery_append"
    FAILED_TICKER_APPEND      = "failed_ticker_append"
    FAILED_GLOBAL_APPEND      = "failed_global_append"
    # LearnerLoopRevamp.md commit 2 — success-path audit aggregator (D18)
    # surfaces a distinct outcome from the appends. Aggregator IO failures
    # (library file missing/corrupt) are operational bugs, not validation.
    FAILED_AGGREGATOR         = "failed_aggregator"

    SUCCESS = frozenset({SUCCEEDED, RECOVERED})
    SKIPPED = frozenset({SKIPPED_NO_PREDICTION, SKIPPED_NO_DAILY_STOCK})
    FAILED  = frozenset({
        FAILED_NO_RESULT, FAILED_INVALID_JSON,
        FAILED_NO_RESULT_RETRY, FAILED_INVALID_JSON_RETRY,
        FAILED_VALIDATION, FAILED_RECOVERY_APPEND,
        FAILED_TICKER_APPEND, FAILED_GLOBAL_APPEND,
        FAILED_AGGREGATOR,
    })
    ALL = SUCCESS | SKIPPED | FAILED  # 13 members


class LearnerSkipped(RuntimeError):
    """Raised by auxiliary scripts when ``run_learner_for_quarter`` returned
    a :class:`LearnerOutcome` in ``SKIPPED`` (environmental — event not ready
    to learn from, not a pipeline defect).

    Kept distinct from :class:`LearnerFailed` so outer drivers can log the
    two categories differently (skip = WARN, fail = ERROR) and downstream
    callers can take different recovery actions.
    """
    def __init__(self, outcome: str, context: str = ""):
        self.outcome = outcome
        suffix = f" ({context})" if context else ""
        super().__init__(f"Learner skipped: {outcome}{suffix}")


class LearnerFailed(RuntimeError):
    """Raised by auxiliary scripts when ``run_learner_for_quarter`` returned
    a :class:`LearnerOutcome` in ``FAILED`` (pipeline-level defect)."""
    def __init__(self, outcome: str, context: str = ""):
        self.outcome = outcome
        suffix = f" ({context})" if context else ""
        super().__init__(f"Learner failed: {outcome}{suffix}")


def run_learner_for_quarter(
    ticker: str,
    quarter_info: dict,
    events: list[dict],
    current_index: int,
    pit_mode: str = "historical",
    live_state_path: Path | None = None,
) -> tuple[dict | None, str]:
    """Run the full learner pipeline for one quarter.

    Returns a 2-tuple ``(attribution, outcome)`` where ``outcome`` is a
    :class:`LearnerOutcome` string constant. The payload is a dict on
    ``SUCCEEDED`` / ``RECOVERED``, else ``None``.

    This contract lets callers distinguish three terminal dispositions:
      * **success** — ``outcome in LearnerOutcome.SUCCESS`` (``payload`` is the attribution dict)
      * **skip** — environmental, not a defect (``outcome in LearnerOutcome.SKIPPED``)
      * **fail** — pipeline-level error (``outcome in LearnerOutcome.FAILED``)

    PIT boundary (asymmetric vs. the predictor — important):
        This function takes **no ``pit_cutoff`` argument**. When
        ``pit_mode == "historical"`` (the caller default, and what ``main()``
        always passes at the ``--learn`` site) the learner cutoff is
        re-derived internally via :func:`derive_learner_pit` using the
        ``events`` list + ``live_state_path``. When ``pit_mode`` is anything
        else the cutoff is ``None`` (live).

        The learner PIT is deliberately **DIFFERENT** from the predictor's
        bundle PIT for the same quarter Q_n:

        * Predictor bundle PIT = ``Q_n.filed_8k`` (the event horizon — must
          be blind to anything after the release). Produced by
          :func:`_resolve_pit_mode` and written into ``bundle["pit_cutoff"]``.
        * Learner PIT          = ``Q_{n+1}.filed_8k`` via tier 1 of
          :func:`derive_learner_pit`, with tier-2 (live cycle) / tier-3
          (invocation time) fallbacks when no next quarter exists.

        Rationale: in production a lesson cannot be written until the next
        cycle's data arrives. Stamping ``source_pit_cutoff = Q_{n+1}.filed_8k``
        on each lesson makes the T1.5b visibility predicate honest —
        ``lesson visible at predictor.pit_cutoff iff
        lesson.source_pit_cutoff <= predictor.pit_cutoff`` — so a lesson
        cannot be consumed by any predictor that fires before the moment
        the lesson could plausibly have been produced.

        Consequence for callers: ``--pit X`` on the CLI sets the predictor's
        bundle PIT but has **no effect** on the learner; and ``--live``
        likewise does not propagate (``main()`` hardcodes
        ``pit_mode="historical"`` at this call site by design). See
        ``.claude/plans/learner.md`` §T1.5 for the full rationale.

    Steps:
      1. Hard gate 1 — ``prediction/result.json`` must exist
      2. Derived-write recovery if ``learning/result.json`` already exists
      3. Hard gate 2 — ``daily_stock`` actual_return must be fetchable from Neo4j
      4. Derive PIT cutoff
      5. Invoke learner via SDK (up to 2 attempts: original + informed retry on validation errors)
      6. Validate learning/result.json
      7. Stamp authoritative model_version + sdk_session_id
      8. Append ticker + global lessons
    """
    ticker = ticker.upper()
    attr_paths = get_learning_paths(ticker, quarter_info)
    learn_paths = get_learnings_paths(ticker)
    accession = quarter_info.get("accession_8k", "")

    # ── Hard gate 1: prediction must exist ──
    if not attr_paths["prediction_result_path"].exists():
        log.warning("Learner skip %s %s: prediction/result.json does not exist",
                     ticker, quarter_info.get("quarter_label"))
        return None, LearnerOutcome.SKIPPED_NO_PREDICTION

    # ── If attribution already exists, run derived-write recovery FIRST ──
    # Runs before fetch_actual_return() so recovery works even if Neo4j is down.
    # A prior run may have written result.json but crashed before ticker/global appends.
    # Completion requires all 3 artifacts (plan §10 completion semantics).
    if attr_paths["result_path"].exists():
        log.info("Learner %s %s: learning/result.json exists, running derived-write recovery",
                  ticker, quarter_info.get("quarter_label"))
        try:
            existing = json.loads(attr_paths["result_path"].read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            log.error("Existing result.json unreadable for %s %s: %s — deleting and re-running",
                       ticker, quarter_info.get("quarter_label"), e)
            attr_paths["result_path"].unlink(missing_ok=True)
            existing = None
        if existing is not None:
            errors = validate_attribution_result(existing, ticker, quarter_info.get("quarter_label", ""))
            if errors:
                log.error("Existing result.json invalid for %s %s: %s — deleting and re-running",
                           ticker, quarter_info.get("quarter_label"), "; ".join(errors[:3]))
                attr_paths["result_path"].unlink(missing_ok=True)
            else:
                # Valid result exists — ensure derived writes + audit aggregation
                # are complete. D18: aggregator runs in BOTH success AND recovery
                # paths so a recovered run leaves audit_history up-to-date for
                # the next quarter's bundle. D19: cross-file validation against
                # the prediction file is required before aggregation.
                try:
                    append_ticker_lesson(ticker, existing)
                    append_global_lessons(existing)
                    pred_path = attr_paths["prediction_result_path"]
                    bundle_path = attr_paths["context_bundle_path"]
                    if not pred_path.is_file() or not bundle_path.is_file():
                        log.error(
                            "recovery aggregator: missing sibling file(s) for %s %s "
                            "(pred=%s bundle=%s)",
                            ticker, quarter_info.get("quarter_label"),
                            pred_path.is_file(), bundle_path.is_file(),
                        )
                        return None, LearnerOutcome.FAILED_RECOVERY_APPEND
                    prediction_payload = json.loads(pred_path.read_text(encoding="utf-8"))
                    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
                    cross_errors = _validate_audit_against_prediction(
                        existing, prediction_payload, bundle,
                    )
                    if cross_errors:
                        log.error(
                            "recovery aggregator: cross-file validation failed for %s %s: %s",
                            ticker, quarter_info.get("quarter_label"),
                            "; ".join(cross_errors[:3]),
                        )
                        return None, LearnerOutcome.FAILED_RECOVERY_APPEND
                    aggregate_lesson_audits(
                        learning_payload=existing,
                        prediction_payload=prediction_payload,
                        bundle=bundle,
                        auditor_ticker=ticker,
                        auditor_quarter_label=quarter_info.get("quarter_label", ""),
                        audit_pit_cutoff=existing.get("pit_cutoff"),
                    )
                    log.info("Derived-write recovery complete for %s %s", ticker, quarter_info.get("quarter_label"))
                except Exception as e:
                    log.error("Derived-write recovery failed for %s %s: %s", ticker, quarter_info.get("quarter_label"), e)
                    return None, LearnerOutcome.FAILED_RECOVERY_APPEND
                return existing, LearnerOutcome.RECOVERED

    # ── Hard gate 2: actual returns (daily_stock must exist) ──
    actual_return = fetch_actual_return(ticker, accession)
    if actual_return is None:
        log.warning("Learner skip %s %s: daily_stock not available (hard gate)",
                     ticker, quarter_info.get("quarter_label"))
        return None, LearnerOutcome.SKIPPED_NO_DAILY_STOCK

    # ── PIT cutoff derivation ──
    if pit_mode == "historical":
        pit_cutoff, pit_boundary_source = derive_learner_pit(
            events, current_index, live_state_path
        )
    else:
        pit_cutoff, pit_boundary_source = None, "invocation_time"

    # ── Invoke learner via SDK ──
    log.info("Running learner for %s %s (PIT=%s, source=%s)",
             ticker, quarter_info.get("quarter_label"), pit_cutoff, pit_boundary_source)

    result_path = attr_paths["result_path"]
    result_path.parent.mkdir(parents=True, exist_ok=True)

    _sdk_result, learner_session_id = run_learner_via_sdk(
        ticker=ticker,
        quarter_info=quarter_info,
        actual_return=actual_return,
        pit_mode=pit_mode,
        pit_cutoff=pit_cutoff,
        pit_boundary_source=pit_boundary_source,
        result_path=result_path,
        prediction_result_path=attr_paths["prediction_result_path"],
        context_bundle_path=attr_paths["context_bundle_path"],
        prior_lessons_path=learn_paths["ticker_lessons_path"],
    )

    # ── Post-return validation ──
    if not result_path.exists():
        log.error("Learner failed %s %s: learning/result.json not written",
                   ticker, quarter_info.get("quarter_label"))
        return None, LearnerOutcome.FAILED_NO_RESULT

    try:
        payload = json.loads(result_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        log.error("Learner failed %s %s: result.json not valid JSON: %s",
                   ticker, quarter_info.get("quarter_label"), e)
        return None, LearnerOutcome.FAILED_INVALID_JSON

    # ── Schema + cross-file validation (D19) ──
    # Combined gate: schema first (cheap, payload-internal), then cross-file
    # against prediction.lesson_labels + bundle.learning_context. Cross-file
    # errors are merged into the same H2 retry payload as schema errors,
    # prefixed with "[cross-file]" so the LLM can distinguish them (E32).
    # ``prediction_payload`` and ``bundle`` are loaded once here and reused
    # by the aggregator after appends.
    errors, prediction_payload, bundle = _full_validate_for_orchestrator(
        payload, ticker, quarter_info.get("quarter_label", ""),
        attr_paths["prediction_result_path"], attr_paths["context_bundle_path"],
    )
    if errors:
        log.error("Learner failed %s %s: validation errors: %s",
                   ticker, quarter_info.get("quarter_label"), "; ".join(errors[:3]))
        # Retry once: delete bad file, re-invoke WITH validation errors fed
        # back into the prompt (H2 informed retry, amendment 2026-04-17 per
        # .claude/plans/learner.md Appendix A §6.6). E32: cross-file errors
        # join the same prior_validation_errors list so the LLM sees them
        # alongside schema errors with the [cross-file] prefix.
        result_path.unlink(missing_ok=True)
        log.info(
            "Retrying learner for %s %s (1 retry, feeding %d validation errors back)",
            ticker, quarter_info.get("quarter_label"), len(errors),
        )
        _sdk_retry_result, learner_session_id = run_learner_via_sdk(
            ticker=ticker,
            quarter_info=quarter_info,
            actual_return=actual_return,
            pit_mode=pit_mode,
            pit_cutoff=pit_cutoff,
            pit_boundary_source=pit_boundary_source,
            result_path=result_path,
            prediction_result_path=attr_paths["prediction_result_path"],
            context_bundle_path=attr_paths["context_bundle_path"],
            prior_lessons_path=learn_paths["ticker_lessons_path"],
            prior_validation_errors=errors,
        )
        if not result_path.exists():
            log.error("Learner retry failed %s %s: no result.json after retry",
                       ticker, quarter_info.get("quarter_label"))
            return None, LearnerOutcome.FAILED_NO_RESULT_RETRY
        try:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log.error("Learner retry failed %s %s: result.json still invalid JSON",
                       ticker, quarter_info.get("quarter_label"))
            return None, LearnerOutcome.FAILED_INVALID_JSON_RETRY
        errors, prediction_payload, bundle = _full_validate_for_orchestrator(
            payload, ticker, quarter_info.get("quarter_label", ""),
            attr_paths["prediction_result_path"], attr_paths["context_bundle_path"],
        )
        if errors:
            log.error("Learner retry failed %s %s: still invalid after retry: %s",
                       ticker, quarter_info.get("quarter_label"), "; ".join(errors[:3]))
            return None, LearnerOutcome.FAILED_VALIDATION

    # Stamp authoritative model_version + sdk_session_id; side-effect render + harvest.
    payload = finalize_learning_result(
        result_path=result_path,
        model=LEARNER.model,
        sdk_session_id=learner_session_id,
        ticker=ticker,
        quarter_label=quarter_info.get("quarter_label"),
    )

    # ── Derived writes: ticker.json + global.json ──
    try:
        append_ticker_lesson(ticker, payload)
        log.info("Appended ticker lesson for %s %s", ticker, quarter_info.get("quarter_label"))
    except Exception as e:
        log.error("Ticker lesson append failed for %s %s: %s",
                   ticker, quarter_info.get("quarter_label"), e)
        return None, LearnerOutcome.FAILED_TICKER_APPEND

    try:
        append_global_lessons(payload)
        log.info("Appended global lessons for %s %s", ticker, quarter_info.get("quarter_label"))
    except Exception as e:
        log.error("Global lesson append failed for %s %s: %s",
                   ticker, quarter_info.get("quarter_label"), e)
        return None, LearnerOutcome.FAILED_GLOBAL_APPEND

    # ── D18 audit aggregator (success path) ──
    # Apply the learner's lesson_audit[] to library audit_history. The
    # aggregator handles per-audit failures internally (log + skip per
    # user clarification #1); a broader IO failure (library file
    # missing/corrupt) propagates and maps to FAILED_AGGREGATOR.
    try:
        aggregate_lesson_audits(
            learning_payload=payload,
            prediction_payload=prediction_payload,
            bundle=bundle,
            auditor_ticker=ticker,
            auditor_quarter_label=quarter_info.get("quarter_label", ""),
            audit_pit_cutoff=pit_cutoff,
        )
    except Exception as e:
        log.error("Audit aggregator failed for %s %s: %s",
                   ticker, quarter_info.get("quarter_label"), e)
        return None, LearnerOutcome.FAILED_AGGREGATOR

    log.info("Learner complete for %s %s", ticker, quarter_info.get("quarter_label"))
    return payload, LearnerOutcome.SUCCEEDED


# ── Lesson File Operations (Python owns all derived writes) ─────────

import fcntl
import tempfile


def _atomic_write_json(path: Path, data: Any) -> None:
    """Write JSON atomically: temp file + os.replace. Creates parents."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(
        dir=path.parent, suffix=".tmp", mode="w", encoding="utf-8", delete=False
    )
    try:
        json.dump(data, tmp, indent=2, default=str, ensure_ascii=False)
        tmp.close()
        os.replace(tmp.name, path)
    except BaseException:
        tmp.close()
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
        raise


def _stamp_ticker_lesson_row(ticker: str, lesson_dict: dict) -> dict:
    """Stamp identity + content + state for a v3 predictor_lesson dict to be
    persisted inside a ticker.json quarter row. Plan §6.3 (storage v2).

    Returns the row in canonical key order. Idempotent: same content →
    same lesson_id (computed from normalized body + scope + routing_key).
    """
    lesson_text = lesson_dict.get("lesson") or ""
    routing_key = ticker.upper()
    lesson_id = compute_lesson_id(lesson_text, "ticker", routing_key)
    return {
        "lesson_id":     lesson_id,
        "lesson":        lesson_text,
        "mechanism":     lesson_dict.get("mechanism"),
        "applies_when":  lesson_dict.get("applies_when"),
        "invalid_if":    lesson_dict.get("invalid_if"),
        "evidence_refs": lesson_dict.get("evidence_refs") or [],
        "scope":         "ticker",
        "routing_key":   routing_key,
        "audit_history": [],
        "parent_id":     None,
    }


def append_ticker_lesson(ticker: str, attribution_result: dict) -> Path:
    """Extract feedback from attribution result and append to ticker lessons file.

    LearnerLoopRevamp.md round-6 fresh-start (2026-05-04): storage bumped
    to ``ticker_lessons.v2``; predictor_lessons inside the quarter row are
    stamped structured dicts (lesson_id + content + audit_history + parent_id)
    per plan §5.2 / §6.3. Outer quarter row provenance (quarter_label,
    attributed_at, source_filed_8k, source_pit_cutoff, etc.) unchanged.

    D22 collision check fires per stamped lesson — silent same-id-different-
    content corruption raises ``DuplicateLessonIdError``.

    Atomic write. No locking needed (single-ticker sequential processing).
    Returns the path written.
    """
    paths = get_learnings_paths(ticker)
    path = paths["ticker_lessons_path"]

    # Read existing or create skeleton (v2 storage post-cutover)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {
            "schema_version": "ticker_lessons.v2",
            "ticker": ticker.upper(),
            "updated_at": None,
            "lessons": [],
        }

    # Stamp v3 lesson dicts → v3 storage rows. v2 string fallback removed
    # at write-time (round-6 fresh-start cutover wipes v1/v2 storage; the
    # validator already rejects non-dict v3 predictor_lessons).
    fb = attribution_result.get("feedback", {})
    pc = fb.get("prediction_comparison", {})
    raw_predictor_lessons = fb.get("predictor_lessons", []) or []
    stamped_predictor_lessons: list[dict] = []
    for pl in raw_predictor_lessons:
        if not isinstance(pl, dict):
            continue  # validator should have rejected; defensive skip
        row = _stamp_ticker_lesson_row(ticker, pl)
        # D22: loud halt on collision (same id, different content).
        assert_no_id_collision(path, "ticker", row["lesson_id"], row)
        stamped_predictor_lessons.append(row)

    entry = {
        "quarter_label": attribution_result.get("quarter_label"),
        "attributed_at": attribution_result.get("attributed_at"),
        # T1.5b: stamp source event's PIT metadata for read-side filtering.
        "source_filed_8k": attribution_result.get("filed_8k"),
        "source_pit_cutoff": attribution_result.get("pit_cutoff"),
        "direction_correct": pc.get("direction_correct"),
        "actual_daily_pct": (attribution_result.get("actual_return") or {}).get("daily_stock_pct"),
        "predicted_direction": pc.get("predicted_direction"),
        "predicted_confidence_score": pc.get("predicted_confidence_score"),
        "primary_driver_summary": (attribution_result.get("primary_driver") or {}).get("summary"),
        "primary_driver_category": (attribution_result.get("primary_driver") or {}).get("category"),
        "what_worked": fb.get("what_worked", []),
        "what_failed": fb.get("what_failed", []),
        "predictor_lessons": stamped_predictor_lessons,
        "data_lessons": fb.get("data_lessons", []),
        "why": fb.get("why"),
    }

    # Idempotent upsert-by-quarter_label (amendment 2026-04-17): remove any
    # prior entry for this quarter before appending, so derived-write recovery
    # or a re-run replaces rather than duplicates.
    target_ql = entry["quarter_label"]
    data["lessons"] = [l for l in data["lessons"] if l.get("quarter_label") != target_ql]
    data["lessons"].append(entry)
    # Bump schema_version on existing files written under v1 (round-6 cutover).
    data["schema_version"] = "ticker_lessons.v2"
    data["updated_at"] = attribution_result.get("attributed_at")
    _atomic_write_json(path, data)
    return path


def append_global_lessons(attribution_result: dict) -> Path | None:
    """Upsert global_observations into learnings/global.json for this quarter.

    Amendment 2026-04-17 (per .claude/plans/learner.md Appendix A §6.2):

      - **Always returns the path** on success (was: returned None when
        observations were empty). Docstring change is intentional — the
        function now runs the flock-protected upsert UNCONDITIONALLY so that a
        re-run producing zero global_observations still purges stale prior
        entries for (source_ticker, quarter_label).
      - **Upsert-by-source-key** (source_ticker, quarter_label): prior entries
        for the same key are removed before the new ones are appended.
        Idempotent under derived-write recovery or any re-run.
      - Enrichment dict passes through structured routing fields
        (related_tickers, target_sector) and stamps source_sector via
        _lookup_company_sector. `scope_key` is NOT passed through (removed
        from schema; validator rejects it on writes).

    Uses fcntl.flock for concurrent-ticker safety. Return type annotation
    stays Path | None — the function can still return None if an exception
    propagates after the lock releases, even though the contract on success
    is "always returns path".
    """
    observations = attribution_result.get("global_observations", [])
    # Normalize src_ticker to UPPER for consistent upsert-key integrity.
    # Mixed-case tickers (e.g., "AAPL" from one call, "aapl" from another) would
    # otherwise produce distinct upsert keys and leave duplicate entries.
    src_ticker = (attribution_result.get("ticker") or "").upper().strip()
    src_quarter = attribution_result.get("quarter_label")

    # Enrich each observation with structured routing + audit fields.
    # NOTE: scope_key is DROPPED here — never passed through to global.json.
    # Routing fields (related_tickers, target_sector) are passed through by
    # key-presence only, so stored entries don't get null-padded on their
    # non-owning scopes. The upstream validator + PreToolUse hook guarantee
    # each routing field appears only on its owning scope before this writer
    # runs; we simply mirror that contract into storage.
    # T1.5b: stamp source event's PIT metadata from attribution_result top-level
    # fields. These are storage metadata used by build_learning_context's
    # read-side filter; they are NOT new learner-output contract fields.
    src_filed_8k = attribution_result.get("filed_8k")
    src_pit_cutoff = attribution_result.get("pit_cutoff")

    # Stamp identity + content + state for each observation (v3 storage v2).
    # Plan §6.3 — global entries carry FLAT provenance + structured content.
    # The lesson_id is computed from (normalized body + scope + routing_key)
    # and is stable across re-runs (idempotent).
    enriched: list[dict] = []
    for obs in observations:
        scope = obs.get("scope")
        # routing_key derives from the OBSERVATION's structured routing
        # field, not the source ticker. cross_ticker → sorted-uppercase
        # tuple of related_tickers; sector → canonical target_sector;
        # macro → None. _routing_key_from_source matches this contract.
        try:
            routing_key = _routing_key_from_source(scope or "", obs)
        except ValueError:
            # Validator should have rejected unknown scopes / missing routing
            # fields before we get here. Defensive: skip rather than raise so
            # one bad observation doesn't reject all of them.
            log.error("append_global_lessons: unroutable observation scope=%r", scope)
            continue
        lesson_text = obs.get("lesson") or ""
        lesson_id = compute_lesson_id(lesson_text, scope or "", routing_key)
        entry = {
            "lesson_id":         lesson_id,
            "lesson":            lesson_text,
            "mechanism":         obs.get("mechanism"),
            "applies_when":      obs.get("applies_when"),
            "invalid_if":        obs.get("invalid_if"),
            "evidence_refs":     obs.get("evidence_refs") or [],
            "scope":             scope,
            "routing_key":       list(routing_key) if isinstance(routing_key, tuple) else routing_key,
            # Flat provenance (matches existing read-side at orchestrator:1733+)
            "source_ticker":     src_ticker,
            "source_sector":     _lookup_company_sector(src_ticker),  # audit-only
            "quarter_label":     src_quarter,
            "attributed_at":     attribution_result.get("attributed_at"),
            "source_filed_8k":   src_filed_8k,
            "source_pit_cutoff": src_pit_cutoff,
            # State
            "audit_history":     [],
            "parent_id":         None,
        }
        # Scope-conditional routing field at top level (kept for read-side
        # compatibility with existing scope-routing logic).
        if "related_tickers" in obs:
            entry["related_tickers"] = obs["related_tickers"]
        if "target_sector" in obs:
            entry["target_sector"] = obs["target_sector"]
        enriched.append(entry)

    path = LEARNINGS_DIR / "global.json"
    path.parent.mkdir(parents=True, exist_ok=True)

    # D22 collision check (read-only scan, outside the flock — D22 raises
    # before we acquire the lock if a collision exists).
    for entry in enriched:
        assert_no_id_collision(path, entry["scope"] or "", entry["lesson_id"], entry)

    # Locked read-modify-write for concurrency safety.
    # Upsert step — always runs, even when enriched == [] (purges stale entries).
    lock_path = path.with_suffix(".lock")
    with open(lock_path, "w") as lock_fd:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        try:
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
            else:
                data = {
                    "schema_version": "global_lessons.v2",
                    "updated_at": None,
                    "entries": [],
                }
            # Remove any prior entries for this (source_ticker, quarter_label)
            # before extending — deterministic upsert-by-source-key. Carries
            # over from v1 storage; lesson_id is a finer key but the per-event
            # purge keeps the same on-disk semantics during cutover.
            key = (src_ticker, src_quarter)
            data["entries"] = [
                e for e in data["entries"]
                if (e.get("source_ticker"), e.get("quarter_label")) != key
            ]
            data["entries"].extend(enriched)
            # Bump schema_version on files originally written under v1 storage.
            data["schema_version"] = "global_lessons.v2"
            data["updated_at"] = attribution_result.get("attributed_at")
            _atomic_write_json(path, data)
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)

    return path


# ── Learning Context Builder (read-time filtering for predictor) ─────


def _assert_learner_paths_invariant(
    lc: dict,
    *,
    ticker: str | None = None,
    current_quarter_label: str | None = None,
) -> None:
    """Three-clause invariant on lc (per learner_result_paths plan):

      (A) Cross-surface set equality:
          set(lc["_allowed_learner_paths"]) == {every learner_result_path
          attached to any lesson in ticker_lessons or global_lessons}.
      (B) No duplicates in the allowlist list:
          len(allowlist) == len(set(allowlist)).
      (C) When ticker AND current_quarter_label are both provided
          (production call path): the would-be self-path
            "earnings-analysis/Companies/{TICKER}/events/{Q}/learning/result.md"
          is NOT present in _allowed_learner_paths.

    Together A and C prove no self-path can leak: A guarantees both surfaces
    hold the same set; C guarantees that set excludes the current quarter.

    Separately callable so tests verify each clause independently. Uses
    explicit `raise AssertionError` so `python -O` cannot strip the check.
    The decorator calls this AFTER allowlist assembly, with full context.
    """
    allowed = lc.get("_allowed_learner_paths") or []
    allowed_set = set(allowed)
    decorated: set[str] = set()
    for L in lc.get("ticker_lessons", []) or []:
        if "learner_result_path" in L:
            decorated.add(L["learner_result_path"])
    for L in lc.get("global_lessons", []) or []:
        if "learner_result_path" in L:
            decorated.add(L["learner_result_path"])

    # (A) cross-surface set equality
    if allowed_set != decorated:
        raise AssertionError(
            "learner_paths invariant (A) violated: allowlist set != decorated set "
            f"(allowlist={sorted(allowed_set)}, decorated={sorted(decorated)})"
        )

    # (B) no duplicates in list form
    if len(allowed) != len(allowed_set):
        raise AssertionError(
            f"learner_paths invariant (B) violated: duplicate paths in allowlist "
            f"(list={allowed})"
        )

    # (C) no self-path leak when context is known
    if ticker is not None and current_quarter_label is not None:
        self_path = (
            f"earnings-analysis/Companies/{ticker.upper()}/events/"
            f"{current_quarter_label}/learning/result.md"
        )
        if self_path in allowed_set:
            raise AssertionError(
                f"learner_paths invariant (C) violated: self-path leaked into "
                f"_allowed_learner_paths (self_path={self_path!r})"
            )


# ════════════════════════════════════════════════════════════════════════
# v3 Audit Aggregator + Lesson Identity + Status + PIT (LearnerLoopRevamp)
# ════════════════════════════════════════════════════════════════════════
#
# Pure-function helpers used by build_learning_context (render-time view) and
# aggregate_lesson_audits (post-event mutation). No file I/O in this section
# except `assert_no_id_collision`, which is a read-only scan with a defensive
# raise. State-mutating helpers live AFTER build_learning_context (so they
# can use _passes_pit / iter_labeled_lessons via local imports).
#
# Plan refs: §7.1 (lesson identity, D10 + D22), §7.3 (status, D6 + D17),
# §7.5 (PIT + same-quarter guard).


class DuplicateLessonIdError(Exception):
    """Raised when D22 collision check finds the same lesson_id with
    differing content. Loud halt — investigate before retry."""


# Tunable status thresholds — see plan §14. Adjustable post-launch.
LESSON_AUDIT_WINDOW = 5
LESSON_RETIRE_MISLED_THRESHOLD = 3
LESSON_WATCH_MISLED_THRESHOLD = 2
LESSON_WATCH_MISSED_THRESHOLD = 2


def _routing_key_from_source(scope: str, source_entry: dict,
                              *, ticker_hint: str | None = None):
    """Derive routing_key from a global.json entry OR a ticker.json
    quarter-row context. Plan §7.1.

    routing_key shape per scope:
      - ticker:       "AVGO" (caller MUST pass ticker_hint — quarter rows
                      don't carry per-row source_ticker; the ticker.json
                      filename IS the routing key)
      - sector:       canonical sector string ("Technology")
      - macro:        None
      - cross_ticker: tuple of sorted UPPERCASE tickers
    """
    if scope == "ticker":
        if not ticker_hint:
            raise ValueError("ticker_hint required for scope='ticker'")
        return ticker_hint.upper()
    if scope == "sector":
        return source_entry.get("target_sector")
    if scope == "macro":
        return None
    if scope == "cross_ticker":
        rt = source_entry.get("related_tickers") or []
        return tuple(sorted(str(t).upper() for t in rt))
    raise ValueError(f"unknown scope: {scope}")


def compute_lesson_id(lesson_text: str, scope: str, routing_key) -> str:
    """Stable lesson id derived from normalized content + scope + routing.

    Properties (plan §7.1):
      - Same body + scope + routing → same id (idempotent under re-runs)
      - Refinement (different text) → different id (chain via parent_id)
      - Cross-scope same-text → different id (scope is in the hash)
      - 10-char hex → ~16^10 ≈ 1.1×10^12 keyspace; collision probability
        ~10^-4 at 10^4 lessons (D22 catches via assert_no_id_collision).
    """
    import hashlib
    normalized_text = " ".join((lesson_text or "").strip().split()).lower()
    if isinstance(routing_key, (list, tuple)):
        routing_repr = ",".join(sorted(str(t).upper() for t in routing_key))
    elif routing_key is None:
        routing_repr = ""
    else:
        routing_repr = str(routing_key)
    payload = f"{normalized_text}|{scope}|{routing_repr}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()[:10]
    return f"lsn_{digest}"


def _content_matches(existing: dict, new_content: dict) -> bool:
    """True iff (lesson body, mechanism, applies_when, invalid_if, scope,
    routing_key) all match after normalization. Used by assert_no_id_collision
    to allow idempotent re-emission while flagging genuine collisions
    (different content under same id). evidence_refs is provenance, not
    content — intentionally excluded."""
    if _normalize_lesson_text(existing.get("lesson", "")) != \
       _normalize_lesson_text(new_content.get("lesson", "")):
        return False
    for field in ("mechanism", "applies_when", "invalid_if"):
        if (existing.get(field) or "") != (new_content.get(field) or ""):
            return False
    if existing.get("scope") != new_content.get("scope"):
        return False
    # Normalize routing_key: list/tuple → sorted tuple of uppercase strings.
    def _norm_rk(rk):
        if isinstance(rk, (list, tuple)):
            return tuple(sorted(str(t).upper() for t in rk))
        return rk
    return _norm_rk(existing.get("routing_key")) == _norm_rk(new_content.get("routing_key"))


def assert_no_id_collision(library_path: Path, scope: str, lesson_id: str,
                            new_content: dict) -> None:
    """D22: scan target library for lesson_id; raise on content mismatch.

    For each existing lesson with matching ``lesson_id``:
      - identical content (per ``_content_matches``) → no-op (legitimate
        idempotent re-emission, e.g., aggregator re-run on the same audit)
      - different content → raise ``DuplicateLessonIdError``

    Cheap defensive check (linear scan over O(N) lessons). Loud failure
    beats silent collision. No-op when library file does not yet exist.
    """
    if not library_path.exists():
        return
    try:
        data = json.loads(library_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return  # malformed — D22 not applicable until file is fixed
    candidates: list[dict] = []
    if scope == "ticker":
        for q_row in data.get("lessons", []) or []:
            for pl in q_row.get("predictor_lessons", []) or []:
                if isinstance(pl, dict) and pl.get("lesson_id") == lesson_id:
                    candidates.append(pl)
    else:
        for entry in data.get("entries", []) or []:
            if isinstance(entry, dict) and entry.get("lesson_id") == lesson_id:
                candidates.append(entry)
    for existing in candidates:
        if not _content_matches(existing, new_content):
            raise DuplicateLessonIdError(
                f"lesson_id {lesson_id!r} collision in {library_path}: "
                f"existing content differs from new_content. "
                f"Existing.lesson={existing.get('lesson')!r}; "
                f"new.lesson={new_content.get('lesson')!r}"
            )


def compute_status(lesson: dict) -> str:
    """Pure function over lesson dict. Caller must pre-filter audit_history
    by ``audit_pit_cutoff <= predictor.pit_cutoff`` before calling (B1).

    Determinism — status depends only on:
      (a) presence of action="retire" in PIT-visible audits, OR
      (b) action="refine" presence (treated as retire for the parent), OR
      (c) recent_window misled count >= retire threshold, OR
      (d) recent_window misled or missed count >= watch threshold

    No side effects. No file I/O. Plan §7.3.
    """
    from collections import Counter
    audits = lesson.get("audit_history", []) or []

    # Explicit retire/refine actions are terminal once visible in PIT
    if any(a.get("action") in ("retire", "refine") for a in audits):
        return "retired"

    recent = audits[-LESSON_AUDIT_WINDOW:]
    counts = Counter(a.get("review") for a in recent)

    if counts["misled"] >= LESSON_RETIRE_MISLED_THRESHOLD:
        return "retired"

    if counts["misled"] >= LESSON_WATCH_MISLED_THRESHOLD or \
       counts["missed"] >= LESSON_WATCH_MISSED_THRESHOLD:
        return "watch"

    return "active"


def _passes_audit_pit(audit_entry: dict, pit_cutoff: str | None) -> bool:
    """Per-audit PIT filter — mirror of build_learning_context._passes_pit
    but over ``audit_pit_cutoff`` instead of ``source_pit_cutoff``. Plan
    §7.5.2 (B1).

    Live mode (pit_cutoff is None) → always True.
    Historical mode → audit_pit_cutoff must exist AND be tz-aware AND
    chronologically <= pit_cutoff. Defensive exclude on parse error /
    naive-datetime / missing field.
    """
    if pit_cutoff is None:
        return True
    apc_raw = audit_entry.get("audit_pit_cutoff")
    if apc_raw is None:
        return False
    try:
        apc_dt = datetime.fromisoformat(str(apc_raw).replace("Z", "+00:00"))
        cut_dt = datetime.fromisoformat(str(pit_cutoff).replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        return False
    if apc_dt.tzinfo is None or cut_dt.tzinfo is None:
        return False
    return apc_dt <= cut_dt


def _apply_render_view(lesson: dict, pit_cutoff: str | None) -> dict | None:
    """Build a transient render-view of a v3 lesson dict with PIT-filtered
    audit_history, computed status, and audit-review counts. Plan §7.5.2.

    Returns ``None`` when the computed status is ``retired`` so the caller
    can drop the lesson before caps + render. Otherwise returns a shallow
    copy of the lesson with three transient fields:

      - ``audit_history`` (PIT-filtered subset)
      - ``_render_status``       ("active" | "watch")
      - ``_render_audit_counts`` (Counter dict of review → count)

    String-bodied lessons (legacy v1 storage) pass through unchanged with
    ``_render_status = "active"`` — they have no audit_history to filter.
    The aggregator never writes audits to v1 strings (lesson_id is
    derivable only from v3 dicts).
    """
    if not isinstance(lesson, dict):
        return lesson  # v1 string fallback — unchanged
    from collections import Counter
    pit_audits = [
        a for a in (lesson.get("audit_history") or [])
        if _passes_audit_pit(a, pit_cutoff)
    ]
    view = {**lesson, "audit_history": pit_audits}
    status = compute_status(view)
    if status == "retired":
        return None
    view["_render_status"] = status
    view["_render_audit_counts"] = dict(Counter(a.get("review") for a in pit_audits))
    return view


def _decorate_with_learner_paths(
    lc: dict, *, ticker: str,
    current_quarter_label: str | None,
    companies_dir: Path,
) -> None:
    """Attach `learner_result_path` per-lesson + assemble `_allowed_learner_paths`.

    Mutates `lc` in-place. Two-phase:

      Phase 1 — attach paths only.
      PIT guard: skip emission whenever
        (source_ticker, quarter_label) == (ticker, current_quarter_label).
      Missing file: stat via `is_file()` (stricter than `exists()`); omit the
      key entirely on miss.

      Phase 2 — collect _allowed_learner_paths in render order.
      Walk ticker_lessons (recency-desc, already sorted by build_learning_context),
      then global_lessons in render order (sector → macro → cross_ticker).
      First-seen dedupe.

      Phase 3 — invariant check via _assert_learner_paths_invariant with full
      context so all three clauses (A, B, C) fire.
    """
    # ── Phase 1: attach paths only ─────────────────────────────────────
    def _maybe_attach(entry: dict, src_ticker: str) -> None:
        # Idempotency belt-and-suspenders: clear any stale value before
        # re-deciding. Defensive only — current flow calls the helper exactly
        # once per bundle build, but a future re-run on an in-memory `lc`
        # whose underlying file disappeared between calls would otherwise
        # leak the stale path past the existence check.
        entry.pop("learner_result_path", None)
        ql = entry.get("quarter_label")
        if not ql or not src_ticker:
            return
        if current_quarter_label is not None \
           and src_ticker.upper() == ticker.upper() \
           and ql == current_quarter_label:
            return  # PIT guard — skip current-quarter self
        rel = (Path("earnings-analysis/Companies") / src_ticker.upper()
               / "events" / ql / "learning" / "result.md")
        abs_path = companies_dir / src_ticker.upper() / "events" / ql / "learning" / "result.md"
        if not abs_path.is_file():
            return  # omit key
        entry["learner_result_path"] = str(rel)

    for lesson in lc.get("ticker_lessons", []):
        _maybe_attach(lesson, ticker)  # ticker_lessons: implicit source=current ticker
    for entry in lc.get("global_lessons", []):
        _maybe_attach(entry, entry.get("source_ticker") or "")

    # ── Phase 2: collect allowlist in render order, deduplicate ────────
    allowed: list[str] = []
    seen: set[str] = set()
    for lesson in lc.get("ticker_lessons", []):
        p = lesson.get("learner_result_path")
        if p and p not in seen:
            seen.add(p)
            allowed.append(p)
    for entry in lc.get("global_lessons", []):
        p = entry.get("learner_result_path")
        if p and p not in seen:
            seen.add(p)
            allowed.append(p)
    lc["_allowed_learner_paths"] = allowed

    # ── Phase 3: invariant check (full three-clause check, with context) ─
    _assert_learner_paths_invariant(
        lc, ticker=ticker, current_quarter_label=current_quarter_label,
    )


def build_learning_context(ticker: str, sector: str | None = None,
                           base_dir: Path | None = None,
                           pit_cutoff: str | None = None,
                           *,
                           current_quarter_label: str | None = None,
                           companies_dir: Path | None = None) -> dict:
    """Build learning context for predictor consumption.

    Amendment 2026-04-17 (per .claude/plans/learner.md Appendix A §4.3 / §6.3):
      - Structured-field routing: cross_ticker by ``related_tickers`` list
        membership; sector by ``target_sector`` enum (normalized compare); macro
        always included. No regex. No per-entry Neo4j calls.
      - ``sector_lookup`` parameter DROPPED (was codex-era threading).
      - Six named exclusion counters; observability log ALWAYS fires (even when
        global.json is absent).
      - ``except JSONDecodeError / OSError`` now log ``log.error`` (was silent).

    Amendment 2026-04-17 T1.5b (per .claude/plans/learner.md §🔥):
      - New ``pit_cutoff`` parameter. When not None, filter lessons whose
        ``source_pit_cutoff`` is strictly after ``pit_cutoff`` across ALL four
        scopes (ticker, sector, macro, cross_ticker). Legacy entries without
        ``source_pit_cutoff`` are treated as post-cutoff in historical mode
        (excluded) and passed through in live mode.
      - When pit_cutoff is None (production real-time path), NO filter is
        applied — preserves pre-T1.5b behavior exactly.
      - Two new observability counters: ``ticker_post_cutoff``,
        ``global_post_cutoff``.
    """
    # Normalize ticker case at function entry. Stored related_tickers are
    # validator-enforced UPPERCASE, and the ticker-lessons filename is UPPERCASE.
    # Without this normalization, a caller passing "aapl" would silently drop
    # every ["AAPL"] cross_ticker lesson and miss its own ticker.json.
    ticker = (ticker or "").upper().strip()
    learnings_dir = base_dir or LEARNINGS_DIR
    ticker_path = learnings_dir / "ticker" / f"{ticker}.json"
    global_path = learnings_dir / "global.json"

    result: dict[str, Any] = {
        "ticker_lessons": [],
        "global_lessons": [],
        "ticker_ref": str(ticker_path) if ticker_path.exists() else None,
        "global_ref": str(global_path) if global_path.exists() else None,
    }

    # T1.5b PIT filter helper. Returns True iff the entry passes the cutoff.
    # Live mode (pit_cutoff is None) → always True (no filter).
    # Historical mode → entry must have source_pit_cutoff AND it must be
    # chronologically <= pit_cutoff.
    #
    # IMPORTANT: naive string comparison is UNSAFE across different UTC
    # offsets (e.g., "...-04:00" vs "...+00:00") — lexical order diverges
    # from chronological order when timestamps are close in real time but
    # differ in offset. Reported by external review 2026-04-17 with this
    # repro: src=2024-06-12T16:19:05-04:00 (20:19:05 UTC) and
    # pit=2024-06-12T20:18:00+00:00 (20:18:00 UTC) — src is chronologically
    # 65s LATER but lexically appears earlier ('16' < '20'). Must parse to
    # tz-aware datetime before comparing. This mirrors the existing PIT
    # pattern in peer_earnings_snapshot._parse_dt_for_pit().
    def _passes_pit(entry: dict) -> bool:
        if pit_cutoff is None:
            return True
        src_pit_raw = entry.get("source_pit_cutoff")
        if src_pit_raw is None:
            return False  # legacy: no bound → cannot be trusted in historical mode
        try:
            # "Z" suffix → "+00:00" for portability across Python versions.
            src_dt = datetime.fromisoformat(str(src_pit_raw).replace("Z", "+00:00"))
            cut_dt = datetime.fromisoformat(str(pit_cutoff).replace("Z", "+00:00"))
        except (ValueError, AttributeError, TypeError):
            return False  # malformed → defensive exclude in historical mode
        # Both must be tz-aware — comparing naive + aware raises TypeError
        # and would hide the bug silently.
        if src_dt.tzinfo is None or cut_dt.tzinfo is None:
            return False
        return src_dt <= cut_dt

    ticker_post_cutoff = 0
    global_post_cutoff = 0
    # Combined counter — incremented from both ticker_lessons and
    # global_lessons paths. Plan §7.5.1 (D13).
    same_quarter_self_leak = 0

    # ── Ticker lessons: most recent 8 ──
    if ticker_path.exists():
        try:
            data = json.loads(ticker_path.read_text(encoding="utf-8"))
            lessons = data.get("lessons", [])
            # Sort by attributed_at descending, dedupe by quarter_label (keep most recent),
            # then take most recent 8. Dedup handles re-bootstrap/retry reruns.
            lessons.sort(key=lambda x: x.get("attributed_at", ""), reverse=True)
            seen_quarters: set[str] = set()
            deduped: list[dict] = []
            for lesson in lessons:
                ql = lesson.get("quarter_label", "")
                if ql not in seen_quarters:
                    seen_quarters.add(ql)
                    deduped.append(lesson)
            # T1.5b: lesson PIT filter (source_pit_cutoff <= predictor.pit_cutoff)
            filtered: list[dict] = []
            for lesson in deduped:
                if _passes_pit(lesson):
                    filtered.append(lesson)
                else:
                    ticker_post_cutoff += 1
            # D13: same-quarter self-leak guard — exclude THIS quarter's
            # ticker rows from THIS quarter's bundle, both historical and
            # live. Compares (ticker, quarter_label) — not timestamps —
            # so a re-run in live mode doesn't see its own prior emission.
            if current_quarter_label:
                guarded: list[dict] = []
                for lesson in filtered:
                    if lesson.get("quarter_label") == current_quarter_label:
                        same_quarter_self_leak += 1
                        continue
                    guarded.append(lesson)
                filtered = guarded
            # B1 + user clarification #2: per-lesson audit_history PIT
            # filter + compute_status + drop retired BEFORE the row cap.
            # _apply_render_view returns None for retired entries; surviving
            # views carry transient _render_status / _render_audit_counts.
            for q_row in filtered:
                pls = q_row.get("predictor_lessons") or []
                surviving: list = []
                for pl in pls:
                    view = _apply_render_view(pl, pit_cutoff)
                    if view is not None:
                        surviving.append(view)
                q_row["predictor_lessons"] = surviving
            result["ticker_lessons"] = filtered[:8]
        except json.JSONDecodeError as e:
            log.error("ticker.json malformed — no ticker lessons loaded for %s: %s", ticker, e)
        except OSError as e:
            log.error("ticker.json read failed — no ticker lessons loaded for %s: %s", ticker, e)

    # ── Global lessons: structured-field routing, per-scope caps ──
    # Counters initialized to zero BEFORE the file-exists check so the
    # observability log at the end always fires with a full, consistent shape
    # — even if global.json is absent (first-ever run / post-wipe state).
    sector_entries: list[dict] = []
    macro_entries: list[dict] = []
    cross_entries: list[dict] = []
    excluded = {
        "sector_mismatch": 0,
        "current_sector_unknown": 0,
        "cross_ticker_not_listed": 0,
        "cross_ticker_missing_related": 0,
        "unknown_scope": 0,
        "legacy_schema": 0,
    }
    normalized_current_sector = _normalize_sector(sector)

    if global_path.exists():
        try:
            data = json.loads(global_path.read_text(encoding="utf-8"))
            entries = data.get("entries", [])

            for e in entries:
                # T1.5b: PIT filter fires BEFORE scope routing for all scopes,
                # so global_post_cutoff is disjoint from scope-specific counters.
                if not _passes_pit(e):
                    global_post_cutoff += 1
                    continue

                # D13: same-quarter self-leak — exclude THIS quarter's own
                # global emissions from THIS quarter's bundle.
                if current_quarter_label and ticker:
                    if (e.get("source_ticker") == ticker
                            and e.get("quarter_label") == current_quarter_label):
                        same_quarter_self_leak += 1
                        continue

                # B1 + user clarification #2: PIT-filter audit_history,
                # compute_status, drop retired BEFORE scope routing/caps.
                # Retired lessons must never consume cap slots (otherwise
                # dead lessons quietly crowd out good live lessons).
                view = _apply_render_view(e, pit_cutoff)
                if view is None:
                    continue
                e = view  # rebind so scope routing reads the rendered view

                scope = e.get("scope")

                if scope == "sector":
                    ts = e.get("target_sector")
                    if ts is None:
                        # Legacy/old-schema entry (pre-fix) — transparently excluded
                        excluded["legacy_schema"] += 1
                        continue
                    if not normalized_current_sector:
                        # CURRENT ticker's sector unknown — cannot route sector-scope.
                        # (Distinct from legacy_schema, which is about the ENTRY.)
                        excluded["current_sector_unknown"] += 1
                        continue
                    if _normalize_sector(ts) == normalized_current_sector:
                        sector_entries.append(e)
                    else:
                        excluded["sector_mismatch"] += 1

                elif scope == "macro":
                    macro_entries.append(e)

                elif scope == "cross_ticker":
                    rt = e.get("related_tickers")
                    if not rt:
                        # Legacy/old-schema entry OR learner error past validator
                        excluded["cross_ticker_missing_related"] += 1
                        continue
                    if ticker in rt:
                        cross_entries.append(e)
                    else:
                        excluded["cross_ticker_not_listed"] += 1

                else:
                    excluded["unknown_scope"] += 1

            # Sort each bucket by recency, apply per-scope caps
            for bucket in (sector_entries, macro_entries, cross_entries):
                bucket.sort(key=lambda x: x.get("attributed_at", ""), reverse=True)

            # Dedupe within each scope: exact text match after normalization
            def _dedupe(entries: list[dict]) -> list[dict]:
                seen: set[str] = set()
                out = []
                for e in entries:
                    k = (e.get("lesson") or "").strip().lower()
                    if k and k not in seen:
                        seen.add(k)
                        out.append(e)
                return out

            sector_entries = _dedupe(sector_entries)[:4]
            macro_entries = _dedupe(macro_entries)[:4]
            cross_entries = _dedupe(cross_entries)[:2]

            result["global_lessons"] = sector_entries + macro_entries + cross_entries
        except json.JSONDecodeError as e:
            log.error("global.json malformed — no global lessons loaded for %s: %s", ticker, e)
        except OSError as e:
            log.error("global.json read failed — no global lessons loaded for %s: %s", ticker, e)

    # Decorate each surviving lesson with `learner_result_path` (when the prior
    # learner's result.md exists on disk) and assemble `_allowed_learner_paths`
    # — the canonical PIT-safe set the predictor is permitted to Read.
    # Two-phase + invariant; raises AssertionError on inconsistent state.
    _decorate_with_learner_paths(
        result, ticker=ticker,
        current_quarter_label=current_quarter_label,
        companies_dir=(companies_dir or COMPANIES_DIR),
    )

    # Observability log — fires ALWAYS, even if global_path didn't exist.
    # Names must match §4.5 contract exactly. Six exclusion counters so any
    # future silent-drop regression appears immediately as an anomalous count.
    # T1.5b adds two more: ticker_post_cutoff, global_post_cutoff.
    log.info(
        "learning_context %s(sector=%s, pit=%s, current_q=%s): "
        "included[sector=%d macro=%d cross=%d] "
        "excluded[sector_mismatch=%d current_sector_unknown=%d "
        "cross_ticker_not_listed=%d cross_ticker_missing_related=%d "
        "unknown_scope=%d legacy_schema=%d "
        "ticker_post_cutoff=%d global_post_cutoff=%d "
        "same_quarter_self_leak=%d]",
        ticker, sector, pit_cutoff, current_quarter_label,
        len(sector_entries), len(macro_entries), len(cross_entries),
        excluded["sector_mismatch"],
        excluded["current_sector_unknown"],
        excluded["cross_ticker_not_listed"],
        excluded["cross_ticker_missing_related"],
        excluded["unknown_scope"],
        excluded["legacy_schema"],
        ticker_post_cutoff,
        global_post_cutoff,
        same_quarter_self_leak,
    )

    return result


# ════════════════════════════════════════════════════════════════════════
# v3 Audit Aggregator — state mutation (post-event)
# ════════════════════════════════════════════════════════════════════════
#
# Plan refs: §7.2 (aggregator), §7.2.1 (helper contracts), §7.6 (cross-file
# validation D19), §7.5 (PIT). The aggregator is the only state-mutating
# component for audit_history; runs in BOTH success and recovery paths
# (D18). Helpers raise loudly; the aggregator catches per-audit failures
# and skips rather than failing the whole batch.


def _stamp_quarter_row_skeleton(ticker: str, learning_payload: dict) -> dict:
    """Build a fresh ticker.json quarter-row skeleton from learning_payload.
    Used by ``_append_lesson_row_to_ticker_quarter`` when the auditor's row
    does not yet exist (§7.2.1 implementation rule — empty-`predictor_lessons`
    + ticker-scope refine). Mirrors the outer-field stamping in
    ``append_ticker_lesson`` exactly.
    """
    fb = learning_payload.get("feedback", {}) or {}
    pc = (fb.get("prediction_comparison") or {}) if isinstance(fb, dict) else {}
    return {
        "quarter_label":              learning_payload.get("quarter_label"),
        "attributed_at":              learning_payload.get("attributed_at"),
        "source_filed_8k":            learning_payload.get("filed_8k"),
        "source_pit_cutoff":          learning_payload.get("pit_cutoff"),
        "direction_correct":          pc.get("direction_correct") if isinstance(pc, dict) else None,
        "actual_daily_pct":           (learning_payload.get("actual_return") or {}).get("daily_stock_pct"),
        "predicted_direction":        pc.get("predicted_direction") if isinstance(pc, dict) else None,
        "predicted_confidence_score": pc.get("predicted_confidence_score") if isinstance(pc, dict) else None,
        "primary_driver_summary":     (learning_payload.get("primary_driver") or {}).get("summary"),
        "primary_driver_category":    (learning_payload.get("primary_driver") or {}).get("category"),
        "what_worked":                fb.get("what_worked", []) if isinstance(fb, dict) else [],
        "what_failed":                fb.get("what_failed", []) if isinstance(fb, dict) else [],
        "predictor_lessons":          [],
        "data_lessons":               fb.get("data_lessons", []) if isinstance(fb, dict) else [],
        "why":                        fb.get("why") if isinstance(fb, dict) else None,
    }


def _upsert_audit_in_history(audit_history: list, audit_entry: dict) -> list:
    """Replace existing entry with matching (auditor_ticker, auditor_quarter_label),
    else append. Returns the modified history list (mutated in place).

    Plan §7.2.1 — the upsert key for re-runs (e.g., recovery path or H2
    retry that re-emits audits) is (auditor_ticker, auditor_quarter_label).
    Same auditor re-emitting on the same quarter REPLACES rather than
    duplicates."""
    key = (audit_entry.get("auditor_ticker"),
           audit_entry.get("auditor_quarter_label"))
    new_history = [
        a for a in (audit_history or [])
        if (a.get("auditor_ticker"), a.get("auditor_quarter_label")) != key
    ]
    new_history.append(audit_entry)
    return new_history


def _apply_audit_ticker(ticker_path: Path, source_quarter_label: str,
                         lesson_id: str, audit_entry: dict) -> None:
    """Append/upsert an audit entry on the matched lesson's audit_history
    inside the SOURCE quarter row (= the row the lesson was created in).

    Lookup tuple: (source_quarter_label, lesson_id) — D22 guarantees
    lesson_id is unique within a quarter row, so this is exact-match.

    Raises if ticker.json missing/corrupt OR source quarter row missing
    OR lesson_id not found in that row's predictor_lessons. Aggregator
    converts these to log-and-skip per audit (plan §7.2 + user clarification
    #1: helpers raise loudly; aggregator handles per-audit failure).
    """
    if not ticker_path.exists():
        raise FileNotFoundError(f"_apply_audit_ticker: {ticker_path} missing")
    data = json.loads(ticker_path.read_text(encoding="utf-8"))
    target_row = None
    for row in data.get("lessons", []) or []:
        if row.get("quarter_label") == source_quarter_label:
            target_row = row
            break
    if target_row is None:
        raise LookupError(
            f"_apply_audit_ticker: source quarter row {source_quarter_label!r} "
            f"not found in {ticker_path}"
        )
    target_lesson = None
    for pl in target_row.get("predictor_lessons", []) or []:
        if isinstance(pl, dict) and pl.get("lesson_id") == lesson_id:
            target_lesson = pl
            break
    if target_lesson is None:
        raise LookupError(
            f"_apply_audit_ticker: lesson_id {lesson_id!r} not found in "
            f"quarter row {source_quarter_label!r}"
        )
    target_lesson["audit_history"] = _upsert_audit_in_history(
        target_lesson.get("audit_history") or [], audit_entry,
    )
    _atomic_write_json(ticker_path, data)


def _apply_audit_global(global_path: Path, lesson_id: str,
                         audit_entry: dict) -> None:
    """Append/upsert an audit entry on the matched global lesson's
    audit_history. Single flock acquisition. Used for non-refine global
    audits; refine path goes through ``_apply_audit_and_append_global_atomic``
    so audit-append + new-entry-insert happen under one lock (E31).
    """
    if not global_path.exists():
        raise FileNotFoundError(f"_apply_audit_global: {global_path} missing")
    lock_path = global_path.with_suffix(".lock")
    with open(lock_path, "w") as lock_fd:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        try:
            data = json.loads(global_path.read_text(encoding="utf-8"))
            target = None
            for entry in data.get("entries", []) or []:
                if isinstance(entry, dict) and entry.get("lesson_id") == lesson_id:
                    target = entry
                    break
            if target is None:
                raise LookupError(
                    f"_apply_audit_global: lesson_id {lesson_id!r} not found "
                    f"in {global_path}"
                )
            target["audit_history"] = _upsert_audit_in_history(
                target.get("audit_history") or [], audit_entry,
            )
            _atomic_write_json(global_path, data)
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)


def _apply_audit_and_append_global_atomic(global_path: Path,
                                           parent_lesson_id: str,
                                           audit_entry: dict,
                                           new_entry: dict) -> None:
    """Atomic global+refine path (E31): append audit_entry to parent's
    audit_history AND insert new_entry into entries[], all under a single
    flock acquisition. Without this atomicity, a reader between the two
    writes would see audit-without-replacement.
    """
    if not global_path.exists():
        raise FileNotFoundError(
            f"_apply_audit_and_append_global_atomic: {global_path} missing"
        )
    lock_path = global_path.with_suffix(".lock")
    with open(lock_path, "w") as lock_fd:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        try:
            data = json.loads(global_path.read_text(encoding="utf-8"))
            target = None
            for entry in data.get("entries", []) or []:
                if isinstance(entry, dict) and entry.get("lesson_id") == parent_lesson_id:
                    target = entry
                    break
            if target is None:
                raise LookupError(
                    f"_apply_audit_and_append_global_atomic: parent_lesson_id "
                    f"{parent_lesson_id!r} not found in {global_path}"
                )
            # 1) append audit on parent
            target["audit_history"] = _upsert_audit_in_history(
                target.get("audit_history") or [], audit_entry,
            )
            # 2) append new replacement entry (lesson_id collision pre-checked
            #    upstream by D22 in _register_replacement)
            data.setdefault("entries", []).append(new_entry)
            _atomic_write_json(global_path, data)
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)


def _append_lesson_row_to_ticker_quarter(ticker_path: Path,
                                          quarter_label: str,
                                          new_row: dict,
                                          *,
                                          quarter_skeleton: dict | None = None
                                          ) -> None:
    """Append a v3 lesson dict to a ticker.json quarter row's
    ``predictor_lessons``. If the quarter row does not exist and
    ``quarter_skeleton`` is provided, the row is created from the skeleton
    first (plan §7.2.1 implementation rule — empty-`predictor_lessons` +
    ticker-scope refine).

    Raises ``FileNotFoundError`` if ticker.json is missing,
    ``json.JSONDecodeError`` if malformed, ``LookupError`` if the target
    quarter row doesn't exist AND no skeleton was provided.
    """
    if not ticker_path.exists():
        raise FileNotFoundError(
            f"_append_lesson_row_to_ticker_quarter: {ticker_path} missing"
        )
    data = json.loads(ticker_path.read_text(encoding="utf-8"))
    target_row = None
    for row in data.get("lessons", []) or []:
        if row.get("quarter_label") == quarter_label:
            target_row = row
            break
    if target_row is None:
        if quarter_skeleton is None:
            raise LookupError(
                f"_append_lesson_row_to_ticker_quarter: quarter row "
                f"{quarter_label!r} not found and no quarter_skeleton provided"
            )
        # §7.2.1 implementation rule — stamp a fresh quarter row from
        # learning_payload outer fields.
        target_row = quarter_skeleton
        data.setdefault("lessons", []).append(target_row)
    target_row.setdefault("predictor_lessons", []).append(new_row)
    _atomic_write_json(ticker_path, data)


def _register_replacement(
    learnings_dir: Path,
    *,
    parent_lesson_id: str,
    parent_scope: str,
    parent_source_entry: dict,
    replacement: dict,
    auditor_ticker: str,
    auditor_quarter_label: str,
    audit_pit_cutoff: str | None,
    learning_payload: dict,
    audit_entry: dict | None,
) -> str:
    """Register a refined replacement lesson + (for global scope) atomically
    append the parent's refine-audit entry. Plan §7.2.

    Constraints:
      - Refinement INHERITS scope + routing from the parent. To change
        scope, the learner must retire the parent and emit a separate
        new lesson at the new scope normally.
      - Ticker-scope: routing_key = auditor_ticker (file-system construction;
        ticker-scope lessons live in learnings/ticker/{auditor_ticker}.json).
      - Atomicity (E31): for global scope, audit-append + new-entry-insert
        share one flock via ``_apply_audit_and_append_global_atomic``. The
        aggregator MUST pass ``audit_entry`` for global scope. For ticker
        scope, audit_entry is None (audit already applied upstream by
        ``_apply_audit_ticker``).
    """
    if parent_scope == "ticker":
        routing_key = auditor_ticker.upper()
    else:
        routing_key = _routing_key_from_source(parent_scope, parent_source_entry)

    new_id = compute_lesson_id(replacement.get("lesson") or "",
                                parent_scope, routing_key)

    if parent_scope == "ticker":
        new_row = {
            "lesson_id":     new_id,
            "lesson":        replacement.get("lesson") or "",
            "mechanism":     replacement.get("mechanism"),
            "applies_when":  replacement.get("applies_when"),
            "invalid_if":    replacement.get("invalid_if"),
            "evidence_refs": replacement.get("evidence_refs") or [],
            "scope":         "ticker",
            "routing_key":   routing_key,
            "audit_history": [],
            "parent_id":     parent_lesson_id,
        }
        target_path = learnings_dir / "ticker" / f"{routing_key}.json"
        assert_no_id_collision(target_path, parent_scope, new_id, new_row)
        assert audit_entry is None, (
            "_register_replacement: ticker-scope must have audit applied "
            "upstream (audit_entry must be None)"
        )
        _append_lesson_row_to_ticker_quarter(
            target_path, auditor_quarter_label, new_row,
            quarter_skeleton=_stamp_quarter_row_skeleton(auditor_ticker, learning_payload),
        )
    else:
        new_row = {
            "lesson_id":     new_id,
            "lesson":        replacement.get("lesson") or "",
            "mechanism":     replacement.get("mechanism"),
            "applies_when":  replacement.get("applies_when"),
            "invalid_if":    replacement.get("invalid_if"),
            "evidence_refs": replacement.get("evidence_refs") or [],
            "scope":         parent_scope,
            "routing_key":   list(routing_key) if isinstance(routing_key, tuple) else routing_key,
            "source_ticker":      auditor_ticker.upper(),
            "source_sector":      _lookup_company_sector(auditor_ticker),
            "quarter_label":      auditor_quarter_label,
            "attributed_at":      learning_payload.get("attributed_at"),
            "source_filed_8k":    learning_payload.get("filed_8k"),
            "source_pit_cutoff":  audit_pit_cutoff,
            "audit_history":      [],
            "parent_id":          parent_lesson_id,
        }
        # Carry scope-conditional routing field at top level (existing
        # build_learning_context routing logic reads it from there).
        if parent_scope == "sector" and "target_sector" in (parent_source_entry or {}):
            new_row["target_sector"] = parent_source_entry["target_sector"]
        if parent_scope == "cross_ticker" and "related_tickers" in (parent_source_entry or {}):
            new_row["related_tickers"] = parent_source_entry["related_tickers"]
        target_path = learnings_dir / "global.json"
        assert_no_id_collision(target_path, parent_scope, new_id, new_row)
        assert audit_entry is not None, (
            "_register_replacement: global-scope requires audit_entry "
            "(E31 atomicity — audit + insert under one flock)"
        )
        _apply_audit_and_append_global_atomic(
            target_path, parent_lesson_id, audit_entry, new_row,
        )

    return new_id


def aggregate_lesson_audits(
    *,
    learning_payload: dict,
    prediction_payload: dict,
    bundle: dict,
    auditor_ticker: str,
    auditor_quarter_label: str,
    audit_pit_cutoff: str | None,
    learnings_dir: Path | None = None,
) -> None:
    """Apply the learner's lesson_audit[] to library audit_history. Plan §7.2.

    Steps per audit entry:
      1. Resolve (scope, source_entry, body) via iter_labeled_lessons over
         the bundle's learning_context (canonical render order).
      2. Compute lesson_id from (body, scope, routing_key).
      3. Build the audit_entry payload with provenance + verdict fields.
      4. Same-hash-refinement guard (user clarification #4): if action ==
         "refine" and replacement hashes to parent's lesson_id, downgrade
         to action="keep" + log warning. Prevents accidental retire of
         parent via cosmetic-edit refinements.
      5. Apply the audit (ticker via _apply_audit_ticker; global via
         _apply_audit_global OR _apply_audit_and_append_global_atomic for
         refine).
      6. Handle action="refine" via _register_replacement.

    Per-audit failure handling (user clarification #1):
      - Out-of-range lesson_index → log warning, skip (D19 cross-file check
        should have rejected this upstream; defensive only).
      - lesson_text drift from bundle body → log warning, prefer index match.
      - missing replacement_lesson on action="refine" → log error, skip refine.
      - lesson_id not found in library → log error (helpers raise; aggregator
        catches per-audit and skips that audit).
      - Library file missing/corrupt → exception propagates (broader IO
        failure is the orchestrator's responsibility to map to FAILED_*).

    Idempotency: re-running with the same (auditor_ticker,
    auditor_quarter_label) UPSERTS each audit entry by that key (replaces,
    no duplicates). Refinement re-runs hit the D22 idempotency check —
    same replacement → same lesson_id → no-op.
    """
    audits = learning_payload.get("lesson_audit") or []
    if not audits:
        return  # first-prediction or no labels — nothing to apply

    learnings_dir = learnings_dir or LEARNINGS_DIR
    learning_ctx = bundle.get("learning_context") or {}

    # Local import — iter_labeled_lessons is defined in _text_utils; avoid
    # forward reference at module-import time.
    from scripts.earnings._text_utils import iter_labeled_lessons

    indexed = list(iter_labeled_lessons(learning_ctx))
    labels = prediction_payload.get("lesson_labels") or []

    cited: set[int] = set()
    for kd in (prediction_payload.get("key_drivers") or []):
        for idx in (kd.get("cites_lesson_indices") or []):
            if isinstance(idx, int):
                cited.add(idx)

    for audit in audits:
        if not isinstance(audit, dict):
            log.warning("aggregator: non-dict audit entry; skipping")
            continue
        idx = audit.get("lesson_index")
        if not isinstance(idx, int) or not (0 <= idx < len(indexed)) \
           or not (0 <= idx < len(labels)):
            log.warning(
                "aggregator: lesson_index=%r out of range "
                "(indexed=%d, labels=%d); skipping",
                idx, len(indexed), len(labels),
            )
            continue
        n, scope, source_entry, body = indexed[idx]

        # D15 defense-in-depth: lesson_text drift between learner-emitted
        # text and bundle body. Continue with index match (D19 should have
        # already rejected at orchestrator level).
        audit_text_norm = _normalize_lesson_text(audit.get("lesson_text") or "")
        body_norm = _normalize_lesson_text(body or "")
        if audit_text_norm != body_norm:
            log.warning(
                "aggregator: lesson_text drift at index=%d; using index match",
                idx,
            )

        # Compute routing_key for the parent lesson.
        try:
            if scope == "ticker":
                routing_key = _routing_key_from_source(
                    scope, source_entry, ticker_hint=auditor_ticker,
                )
            else:
                routing_key = _routing_key_from_source(scope, source_entry)
        except ValueError as e:
            log.error("aggregator: cannot derive routing_key: %s; skipping audit %d", e, idx)
            continue
        lesson_id = compute_lesson_id(body, scope, routing_key)

        # Build the audit entry payload.
        audit_entry = {
            "auditor_ticker":           auditor_ticker.upper(),
            "auditor_quarter_label":    auditor_quarter_label,
            "audited_at":               learning_payload.get("attributed_at"),
            "audit_pit_cutoff":         audit_pit_cutoff,
            "predictor_label_at_audit": (labels[idx] or {}).get("label"),
            "was_cited":                (idx in cited),
            "review":                   audit.get("review"),
            "action":                   audit.get("action"),
            "comment":                  audit.get("comment"),
            "evidence_refs":            audit.get("evidence_refs") or [],
        }

        # User clarification #4 — same-hash refinement → keep, no retire.
        action = audit.get("action")
        replacement = audit.get("replacement_lesson")
        is_refine = (action == "refine"
                     and isinstance(replacement, dict))
        if is_refine:
            replacement_id = compute_lesson_id(
                replacement.get("lesson") or "", scope, routing_key,
            )
            if replacement_id == lesson_id:
                log.warning(
                    "aggregator: refinement at index=%d hashes to parent "
                    "lesson_id %s — downgrading action to 'keep' (no-op refine)",
                    idx, lesson_id,
                )
                audit_entry["action"] = "keep"
                is_refine = False
        elif action == "refine":
            # action=refine without a valid replacement_lesson — D19 should
            # reject this upstream. Defensive: log + treat as keep.
            log.error(
                "aggregator: action='refine' at index=%d missing valid "
                "replacement_lesson; treating as 'keep'", idx,
            )
            audit_entry["action"] = "keep"

        # Apply the audit (per-audit try/except so one failure doesn't
        # cancel the rest of the batch — user clarification #1).
        try:
            if scope == "ticker":
                ticker_path = learnings_dir / "ticker" / f"{auditor_ticker.upper()}.json"
                source_quarter_label = source_entry.get("quarter_label")
                if not source_quarter_label:
                    log.error(
                        "aggregator: ticker-scope source row missing "
                        "quarter_label at index=%d; skipping", idx,
                    )
                    continue
                _apply_audit_ticker(
                    ticker_path, source_quarter_label, lesson_id, audit_entry,
                )
                if is_refine:
                    _register_replacement(
                        learnings_dir,
                        parent_lesson_id=lesson_id,
                        parent_scope=scope,
                        parent_source_entry=source_entry,
                        replacement=replacement,
                        auditor_ticker=auditor_ticker,
                        auditor_quarter_label=auditor_quarter_label,
                        audit_pit_cutoff=audit_pit_cutoff,
                        learning_payload=learning_payload,
                        audit_entry=None,  # already applied above
                    )
            else:
                global_path = learnings_dir / "global.json"
                if is_refine:
                    _register_replacement(
                        learnings_dir,
                        parent_lesson_id=lesson_id,
                        parent_scope=scope,
                        parent_source_entry=source_entry,
                        replacement=replacement,
                        auditor_ticker=auditor_ticker,
                        auditor_quarter_label=auditor_quarter_label,
                        audit_pit_cutoff=audit_pit_cutoff,
                        learning_payload=learning_payload,
                        audit_entry=audit_entry,  # E31 atomicity
                    )
                else:
                    _apply_audit_global(global_path, lesson_id, audit_entry)
        except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
            # Library file IO failure — not a per-audit problem; let it
            # propagate so the orchestrator marks the run FAILED_*.
            raise
        except (LookupError, ValueError, AssertionError, DuplicateLessonIdError) as e:
            # Per-audit failure — log + skip (user clarification #1).
            log.error(
                "aggregator: audit %d (lesson_id=%s) failed: %s — skipping",
                idx, lesson_id, e,
            )
            continue


# ── Cross-file validation (D19) ─────────────────────────────────────────


def _validate_audit_against_prediction(
    learning_payload: dict,
    prediction_payload: dict,
    bundle: dict,
) -> list[str]:
    """D19 cross-file gate. The hook validator is path-blind (stdlib-only,
    no prediction-file access) and treats lesson_audit as structurally
    optional. The orchestrator-level gate enforces full coverage:

      * len(lesson_audit) == len(prediction.lesson_labels)
      * len(bundle.learning_context lessons) == len(lesson_labels)
        (defensive — T1 already asserts this; D19 stays self-contained)
      * each audit's lesson_index == its position
      * predictor_label matches prediction.lesson_labels[i].label
      * was_cited matches whether i appears in any cites_lesson_indices
      * lesson_text matches bundle body at lesson_index (whitespace-norm)

    Returns a list of error strings; empty = pass. Failures feed the H2
    informed-retry loop via prior_validation_errors with [cross-file] prefix
    (E32). Plan §7.6.
    """
    errors: list[str] = []
    audits = learning_payload.get("lesson_audit", []) or []
    labels = prediction_payload.get("lesson_labels", []) or []

    if not isinstance(audits, list):
        errors.append("[cross-file] lesson_audit must be a list")
        return errors
    if len(audits) != len(labels):
        errors.append(
            f"[cross-file] lesson_audit count {len(audits)} != "
            f"lesson_labels count {len(labels)}"
        )
        return errors

    from scripts.earnings._text_utils import iter_labeled_lessons
    indexed = list(iter_labeled_lessons(bundle.get("learning_context") or {}))

    if len(indexed) != len(labels):
        errors.append(
            f"[cross-file] bundle.learning_context lesson count {len(indexed)} "
            f"!= lesson_labels count {len(labels)}"
        )
        return errors

    cited: set[int] = set()
    for kd in (prediction_payload.get("key_drivers") or []):
        for idx in (kd.get("cites_lesson_indices") or []):
            if isinstance(idx, int):
                cited.add(idx)

    for i, audit in enumerate(audits):
        if not isinstance(audit, dict):
            errors.append(f"[cross-file] lesson_audit[{i}] must be an object")
            continue
        if audit.get("lesson_index") != i:
            errors.append(
                f"[cross-file] lesson_audit[{i}].lesson_index = "
                f"{audit.get('lesson_index')!r} (expected {i})"
            )
        expected_label = (labels[i] or {}).get("label") if isinstance(labels[i], dict) else None
        if audit.get("predictor_label") != expected_label:
            errors.append(
                f"[cross-file] lesson_audit[{i}].predictor_label "
                f"{audit.get('predictor_label')!r} != prediction label "
                f"{expected_label!r}"
            )
        expected_cited = (i in cited)
        if audit.get("was_cited") != expected_cited:
            errors.append(
                f"[cross-file] lesson_audit[{i}].was_cited = "
                f"{audit.get('was_cited')!r} (expected {expected_cited})"
            )
        if i < len(indexed):
            _, _, _, body = indexed[i]
            if _normalize_lesson_text(audit.get("lesson_text") or "") \
               != _normalize_lesson_text(body or ""):
                errors.append(
                    f"[cross-file] lesson_audit[{i}].lesson_text drift "
                    f"from bundle body"
                )

    return errors


def _full_validate_for_orchestrator(
    payload: dict,
    ticker: str,
    quarter_label: str,
    prediction_result_path: Path,
    context_bundle_path: Path,
) -> tuple[list[str], dict | None, dict | None]:
    """Schema + cross-file validation as a single gate. Plan §7.6 (D19) +
    §8.2. Returns ``(errors, prediction_payload, bundle)``:

      * ``errors`` is a flat list — schema errors first, cross-file
        errors second (prefixed with ``[cross-file]``). Empty on success.
      * ``prediction_payload`` and ``bundle`` are loaded ONLY when schema
        passes (cross-file is irrelevant on a malformed payload). They
        are reused by the aggregator after the appends; loading once here
        avoids re-reading the files.

    Module-level (not a closure inside ``run_learner_for_quarter``) so the
    test_learner_outcomes.py AST walk does not pick up the helper's
    internal returns as if they were outcome-tagged learner returns.
    """
    schema_errs = validate_attribution_result(payload, ticker, quarter_label)
    if schema_errs:
        return schema_errs, None, None
    try:
        pp = json.loads(prediction_result_path.read_text(encoding="utf-8"))
        bb = json.loads(context_bundle_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return [f"[cross-file] failed to load sibling files: {e}"], None, None
    cross_errs = _validate_audit_against_prediction(payload, pp, bb)
    return cross_errs, pp, bb


# ── Learner SDK Invocation ───────────────────────────────────────────

_LEARNER_SKILL_PATH = Path(".claude/skills/earnings-learner/SKILL.md")


def _load_learner_skill_content() -> str:
    """Load SKILL.md content, stripping YAML frontmatter."""
    raw = _LEARNER_SKILL_PATH.read_text(encoding="utf-8")
    # Strip frontmatter (--- ... ---)
    if raw.startswith("---"):
        end = raw.find("---", 3)
        if end != -1:
            raw = raw[end + 3:].lstrip("\n")
    return raw


def _build_learner_prompt(
    skill_content: str,
    ticker: str,
    quarter_info: dict,
    actual_return: dict,
    pit_mode: str,
    pit_cutoff: str | None,
    pit_boundary_source: str,
    result_path: Path,
    prediction_result_path: Path,
    context_bundle_path: Path,
    prior_lessons_path: Path,
    prior_validation_errors: list[str] | None = None,
) -> str:
    """Assemble the full learner prompt: SKILL.md instructions + runtime INPUTS.

    ``prior_validation_errors`` (amendment 2026-04-17, H2 informed retry per
    .claude/plans/learner.md Appendix A §6.6): when non-empty, appended as a
    dedicated "YOUR PRIOR OUTPUT WAS REJECTED" block so the 1-retry path is
    informed rather than blind. Default None for first-attempt calls.
    """
    actual_return_json = json.dumps(actual_return, indent=2, default=str)
    inputs_section = f"""--- INPUTS ---
TICKER: {ticker}
QUARTER: {quarter_info.get('quarter_label', 'UNKNOWN')}
FILED_8K: {quarter_info.get('filed_8k', 'UNKNOWN')}
ACCESSION: {quarter_info.get('accession_8k', 'UNKNOWN')}
PIT_MODE: {pit_mode}
PIT_CUTOFF: {pit_cutoff or 'null'}
PIT_BOUNDARY_SOURCE: {pit_boundary_source}
RESULT_PATH: {result_path}
PREDICTION_RESULT: {prediction_result_path}
CONTEXT_BUNDLE: {context_bundle_path}
ACTUAL_RETURN: {actual_return_json}
PRIOR_LESSONS: {prior_lessons_path}
"""
    if prior_validation_errors:
        numbered = "\n".join(
            f"  {i + 1}. {e}" for i, e in enumerate(prior_validation_errors)
        )
        retry_block = (
            "\n--- YOUR PRIOR OUTPUT WAS REJECTED ---\n"
            "The previous attempt failed schema validation with these errors:\n"
            f"{numbered}\n\n"
            "Fix these EXACT errors and re-emit learning/result.json. "
            "Do not change other fields; only correct the listed shape issues.\n"
        )
        return f"{skill_content}\n\n{inputs_section}{retry_block}"
    return f"{skill_content}\n\n{inputs_section}"


async def _run_learner_via_sdk(
    ticker: str,
    quarter_info: dict,
    actual_return: dict,
    pit_mode: str,
    pit_cutoff: str | None,
    pit_boundary_source: str,
    result_path: Path,
    prediction_result_path: Path,
    context_bundle_path: Path,
    prior_lessons_path: Path,
    prior_validation_errors: list[str] | None = None,
) -> tuple[str | None, str | None]:
    """Invoke the learner via SDK embed (main session, full tool access).

    Loads SKILL.md content as prompt text — NOT via /earnings-learner fork.
    This gives the session Agent tool access for all 14 Data SubAgents.

    ``prior_validation_errors`` threads through to ``_build_learner_prompt`` so
    the retry path in ``run_learner_for_quarter`` can feed the previous
    attempt's validation errors back into the prompt (H2, informed retry).

    Returns:
        Tuple of ``(final_result, session_id)``. ``session_id`` is captured
        using the hybrid approach (per obsidian_thinking.md locked decision §6):
        primary path is ``getattr(msg, "session_id", None)`` which works
        against SDK v0.1.61 where every message class exposes it; fallback to
        the older ``SystemMessage(subtype="init").data.get("session_id")``
        shape for SDK-version resilience.
    """
    from claude_agent_sdk import query, ClaudeAgentOptions
    cli_path, creds_path = _assert_claude_code_oauth_ready()
    log.info("Learner SDK auth mode: Claude Code OAuth via %s (creds %s)", cli_path, creds_path)

    skill_content = _load_learner_skill_content()
    prompt = _build_learner_prompt(
        skill_content=skill_content,
        ticker=ticker,
        quarter_info=quarter_info,
        actual_return=actual_return,
        pit_mode=pit_mode,
        pit_cutoff=pit_cutoff,
        pit_boundary_source=pit_boundary_source,
        result_path=result_path,
        prediction_result_path=prediction_result_path,
        context_bundle_path=context_bundle_path,
        prior_lessons_path=prior_lessons_path,
        prior_validation_errors=prior_validation_errors,
    )

    # Drain stderr via callback — without this, a chatty subprocess stderr
    # pipe fills and the child dies with "Command failed with exit code 1".
    def _stderr_sink(line: str) -> None:
        log.info("learner stderr: %s", line.rstrip())

    final_result: str | None = None
    session_id: str | None = None
    async for msg in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            **LEARNER.as_sdk_kwargs(),
            setting_sources=["project"],
            permission_mode="bypassPermissions",
            stderr=_stderr_sink,
            cli_path=cli_path,
            env=_sdk_subprocess_env(),
        ),
    ):
        # Hybrid session_id capture — primary path (SDK v0.1.61+) + fallback.
        if session_id is None:
            session_id = getattr(msg, "session_id", None) or getattr(msg, "sessionId", None)
        if session_id is None and getattr(msg, "subtype", "") == "init":
            data = getattr(msg, "data", {}) or {}
            session_id = data.get("session_id") or data.get("sessionId")
        if hasattr(msg, "result"):
            final_result = str(msg.result)
    return final_result, session_id


def run_learner_via_sdk(
    ticker: str,
    quarter_info: dict,
    actual_return: dict,
    pit_mode: str,
    pit_cutoff: str | None,
    pit_boundary_source: str,
    result_path: Path,
    prediction_result_path: Path,
    context_bundle_path: Path,
    prior_lessons_path: Path,
    prior_validation_errors: list[str] | None = None,
) -> tuple[str | None, str | None]:
    """Sync wrapper for the learner SDK call.

    ``prior_validation_errors`` threads through to ``_run_learner_via_sdk`` for
    the H2 informed-retry path. Default None for first-attempt calls.

    Returns ``(final_result, session_id)`` tuple — see ``_run_learner_via_sdk``.
    """
    try:
        return asyncio.run(_run_learner_via_sdk(
            ticker=ticker,
            quarter_info=quarter_info,
            actual_return=actual_return,
            pit_mode=pit_mode,
            pit_cutoff=pit_cutoff,
            pit_boundary_source=pit_boundary_source,
            result_path=result_path,
            prediction_result_path=prediction_result_path,
            context_bundle_path=context_bundle_path,
            prior_lessons_path=prior_lessons_path,
            prior_validation_errors=prior_validation_errors,
        ))
    except ImportError as e:
        raise RuntimeError(
            "claude_agent_sdk is not available; cannot run learner"
        ) from e


# ── Predictor Canonicalization Layer (Option A) ─────────────────────
# SKILL.md is UNCHANGED. LLM writes the 7 analytic fields. Python adds
# 8 metadata/derived fields after SDK write, before validation.
# Thresholds from .claude/plans/predictor-revamp.md §389-390 (canonical).

import hashlib
import shutil

# Backward-compat alias for existing callers — authoritative source is
# config.llm_models.PREDICTOR.model
PREDICTOR_MODEL_ID = PREDICTOR.model
_PREDICTOR_SKILL_PATH = Path(".claude/skills/earnings-prediction/SKILL.md")
_CLAUDE_CREDS_PATH = Path.home() / ".claude" / ".credentials.json"
_SYSTEM_CLAUDE_CANDIDATES = [
    Path.home() / ".local" / "bin" / "claude",
    Path(shutil.which("claude")) if shutil.which("claude") else None,
]

# System CLI path — use the user's installed Claude Code CLI with local OAuth
# credentials, not the SDK's bundled fallback.
_SYSTEM_CLAUDE_CLI = next(
    (str(path) for path in _SYSTEM_CLAUDE_CANDIDATES if path and path.exists()),
    None,
)


def _sdk_cli_path() -> str | None:
    """Return the claude CLI path for SDK invocation (system CLI if available)."""
    return _SYSTEM_CLAUDE_CLI


def _sdk_subprocess_env() -> dict[str, str]:
    """Strip Anthropic API-key auth from the Claude Code subprocess environment.

    The earnings predictor/learner must run through local Claude Code OAuth
    credentials, not direct Anthropic API-key auth.
    """
    return {
        "ANTHROPIC_API_KEY": "",
        "ANTHROPIC_AUTH_TOKEN": "",
    }


def _strip_anthropic_api_auth_env() -> list[str]:
    """Remove direct Anthropic API auth from the current process environment."""
    stripped: list[str] = []
    for env_key in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        if os.environ.pop(env_key, None):
            stripped.append(env_key)
    return stripped


def _assert_claude_code_oauth_ready() -> tuple[str, str]:
    """Fail closed unless Claude Code OAuth credentials are available.

    Returns:
        tuple[str, str]: (cli_path, credentials_path)
    """
    stripped = _strip_anthropic_api_auth_env()
    if stripped:
        log.warning(
            "Stripped direct Anthropic API auth from orchestrator process before "
            "Claude Code SDK invocation: %s",
            ", ".join(stripped),
        )

    cli_path = _sdk_cli_path()
    if not cli_path:
        raise RuntimeError(
            "Claude Code CLI not found. Expected ~/.local/bin/claude or a "
            "'claude' binary on PATH for OAuth-backed execution."
        )

    if not _CLAUDE_CREDS_PATH.exists():
        raise RuntimeError(
            f"Claude Code OAuth credentials not found: {_CLAUDE_CREDS_PATH}"
        )

    try:
        creds = json.loads(_CLAUDE_CREDS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise RuntimeError(
            f"Could not read Claude Code credentials at {_CLAUDE_CREDS_PATH}"
        ) from e

    oauth = creds.get("claudeAiOauth") or {}
    if not oauth.get("accessToken"):
        raise RuntimeError(
            "Claude Code OAuth credentials are missing claudeAiOauth.accessToken; "
            "predictor/learner will not run in API-key mode."
        )

    return cli_path, str(_CLAUDE_CREDS_PATH)


def _derive_confidence_bucket(direction: str, score: int | float) -> str:
    """Per predictor-revamp.md: 70-100=high, 40-69=moderate, 0-39=low, no_call=no_call."""
    if direction == "no_call":
        return "no_call"
    if score >= 70:
        return "high"
    if score >= 40:
        return "moderate"
    return "low"


def _derive_magnitude_bucket(direction: str, move_range: list) -> str:
    """Per predictor-revamp.md: <2%=small, 2-4%=medium, >=4%=large, no_call=none.
    Midpoint of expected_move_range_pct used as the magnitude."""
    if direction == "no_call":
        return "none"
    try:
        midpoint = (float(move_range[0]) + float(move_range[1])) / 2.0
    except (TypeError, ValueError, IndexError):
        return "none"
    if midpoint >= 4.0:
        return "large"
    if midpoint >= 2.0:
        return "medium"
    return "small"


def _hash_prompt_version(skill_path: Path = _PREDICTOR_SKILL_PATH) -> str:
    """Deterministic prompt_version: short sha256 hash of SKILL.md content.
    Auto-invalidates when SKILL.md changes. Fallback to 'v1' if unreadable."""
    try:
        content = skill_path.read_bytes()
        return "v1-" + hashlib.sha256(content).hexdigest()[:12]
    except OSError:
        return "v1"


def finalize_learning_result(
    *,
    result_path: Path,
    model: str,
    sdk_session_id: str | None = None,
    ticker: str | None = None,
    quarter_label: str | None = None,
    experiment_name: str | None = None,
) -> dict:
    """Stamp authoritative metadata onto learning/result.json + side-effects.

    Mirrors the predictor's finalize_prediction_result() in principle but
    intentionally narrow: ONLY overwrites ``model_version`` + adds
    ``sdk_session_id`` flat top-level field. Does NOT rewrite any other
    learner-authored field. The learner's prompt controls everything else;
    Python is only the source of truth for which model actually ran + the
    SDK session id for thinking harvest linkage.

    Side-effects (best-effort, try/except so neither blocks the JSON write):
      - Generates ``result.md`` sidecar via result_md_renderer
      - Calls thinking_harvester.harvest() to produce ``thinking.md`` +
        ``subagents/`` under ``events/{Q}/learning/``

    Added 2026-04-17 per obsidian_thinking.md (renamed from
    ``finalize_attribution_result``; the old alias was retired 2026-04-19
    in the T5 cleanup).
    """
    if not result_path.exists():
        raise RuntimeError(f"Learner did not write {result_path}")
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    payload["model_version"] = model
    # sdk_session_id: never overwrite an existing non-null value with None
    # (protects resume paths where the caller doesn't re-capture a session id).
    # Rule: stamp when caller provides a real value OR when the key is missing;
    # otherwise preserve whatever is already there.
    existing_sid = payload.get("sdk_session_id")
    if sdk_session_id is not None:
        payload["sdk_session_id"] = sdk_session_id
    elif "sdk_session_id" not in payload:
        payload["sdk_session_id"] = None
    # else: payload already has a value (None or real); keep it unchanged.
    effective_sid = payload.get("sdk_session_id")
    result_path.write_text(
        json.dumps(payload, indent=2, default=str), encoding="utf-8"
    )

    _render_and_harvest_best_effort(
        component="learning",
        result_path=result_path,
        ticker=ticker or payload.get("ticker"),
        quarter_label=quarter_label or payload.get("quarter_label"),
        sdk_session_id=effective_sid,
        experiment_name=experiment_name,
    )
    return payload


def finalize_prediction_result(
    result_path: Path,
    ticker: str,
    quarter_info: dict,
    model: str = PREDICTOR_MODEL_ID,
    sdk_session_id: str | None = None,
    experiment_name: str | None = None,
) -> None:
    """Enrich LLM-written prediction with deterministic metadata.

    LLM writes 7 analytic fields per SKILL.md; Python adds 8 fields here
    plus ``sdk_session_id`` (flat top-level; nullable).
    Runs AFTER SDK write, BEFORE validator. Does not change /earnings-prediction.

    Side-effects (best-effort, try/except so neither blocks the JSON write):
      - Generates ``result.md`` sidecar via result_md_renderer
      - Calls thinking_harvester.harvest() to produce ``thinking.md`` under
        ``events/{Q}/prediction/`` (or under ``experiments/{experiment_name}/``
        when ``experiment_name`` is provided — used by A/B baseline callsites).
    """
    if not result_path.exists():
        raise RuntimeError(f"Predictor did not write {result_path}")

    payload = json.loads(result_path.read_text(encoding="utf-8"))

    # Required LLM-written fields (must be present — predictor's job)
    for required in ("direction", "confidence_score", "expected_move_range_pct"):
        if required not in payload:
            raise ValueError(
                f"LLM output missing required analytic field '{required}' — predictor SKILL.md contract violation"
            )

    # Python-owned metadata
    payload["schema_version"] = "prediction_result.v1"
    payload["ticker"] = ticker.upper()
    payload["quarter_label"] = quarter_info["quarter_label"]
    payload["predicted_at"] = datetime.now(timezone.utc).isoformat()
    payload["model_version"] = model
    payload["prompt_version"] = _hash_prompt_version()
    # sdk_session_id: never overwrite an existing non-null value with None.
    # Protects resume paths (e.g., run_ab_baseline.py) where caller passes
    # None because the SDK wasn't re-invoked.
    if sdk_session_id is not None:
        payload["sdk_session_id"] = sdk_session_id
    elif "sdk_session_id" not in payload:
        payload["sdk_session_id"] = None
    # else: existing value (None or real) preserved.
    effective_sid = payload.get("sdk_session_id")

    # Deterministic derivations from LLM output
    payload["confidence_bucket"] = _derive_confidence_bucket(
        payload["direction"], payload["confidence_score"]
    )
    payload["magnitude_bucket"] = _derive_magnitude_bucket(
        payload["direction"], payload["expected_move_range_pct"]
    )

    # Atomic write back (temp file + os.replace)
    _atomic_write_json(result_path, payload)

    _render_and_harvest_best_effort(
        component="prediction" if experiment_name is None else "prediction_no_lessons",
        result_path=result_path,
        ticker=ticker,
        quarter_label=quarter_info["quarter_label"],
        sdk_session_id=effective_sid,
        experiment_name=experiment_name,
    )


def _render_and_harvest_best_effort(
    *,
    component: str,
    result_path: Path,
    ticker: str | None,
    quarter_label: str | None,
    sdk_session_id: str | None,
    experiment_name: str | None,
) -> None:
    """Run result_md render + thinking_harvester in try/except.

    Neither failure blocks the result.json write (per locked decision:
    "Silent-fail semantics on harvest").
    """
    # result.md sidecar
    try:
        from result_md_renderer import render as _render
        md_path = result_path.with_name("result.md")
        _render(component, result_path, md_path)
    except Exception as e:
        log.warning("result.md render failed for %s: %s", result_path, e)

    # thinking.md harvest — requires ticker + quarter + session_id
    if not (ticker and quarter_label):
        log.info("Skipping thinking harvest (missing ticker/quarter): %s", result_path)
        return
    try:
        from thinking_harvester import harvest as _harvest
        # Map renderer component name to harvester thinking_type
        if component == "prediction_no_lessons":
            harv_type = "prediction"
            harv_exp = experiment_name or "prediction_no_lessons"
        elif component in ("prediction", "learning", "guidance"):
            harv_type = component
            harv_exp = experiment_name
        else:
            log.info("Unknown component for harvest: %s", component)
            return
        _harvest(
            thinking_type=harv_type,
            ticker=ticker,
            quarter=quarter_label,
            session_id=sdk_session_id,
            experiment_name=harv_exp,
        )
    except Exception as e:
        log.warning(
            "thinking_harvester failed for %s %s (session=%s): %s",
            ticker, quarter_label, sdk_session_id, e,
        )


def _build_predictor_prompt(bundle_path: Path,
                            rendered_path: Path,
                            section_audit_path: Path,
                            result_path: Path) -> str:
    """Pure helper — assemble the predictor SDK prompt. Extracted for unit-testing
    prompt content without mocking the SDK."""
    return (
        "Run /earnings-prediction with these exact paths:\n"
        f"BUNDLE_PATH={bundle_path}\n"
        f"RENDERED_BUNDLE_PATH={rendered_path}\n"
        f"SECTION_AUDIT_PATH={section_audit_path}\n"
        f"RESULT_PATH={result_path}\n"
        "Read the bundle, write SECTION_AUDIT_PATH as facts-only JSON, then write RESULT_PATH as JSON, and stop."
    )


async def _run_predictor_via_sdk(bundle_path: Path,
                                 rendered_path: Path,
                                 section_audit_path: Path,
                                 result_path: Path) -> tuple[str | None, str | None]:
    """Invoke the predictor skill once via Claude Agent SDK.

    Returns ``(final_result, session_id)`` — session_id is captured via the
    hybrid approach (per obsidian_thinking.md locked decision §6).
    """
    from claude_agent_sdk import query, ClaudeAgentOptions
    cli_path, creds_path = _assert_claude_code_oauth_ready()
    log.info("Predictor SDK auth mode: Claude Code OAuth via %s (creds %s)", cli_path, creds_path)

    prompt = _build_predictor_prompt(bundle_path, rendered_path, section_audit_path, result_path)

    # Drain stderr via callback — without this, a chatty subprocess stderr
    # pipe fills and the child dies with "Command failed with exit code 1".
    def _stderr_sink(line: str) -> None:
        log.debug("predictor stderr: %s", line.rstrip())

    final_result: str | None = None
    session_id: str | None = None
    async for msg in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            **PREDICTOR.as_sdk_kwargs(),
            setting_sources=["project"],
            permission_mode="bypassPermissions",
            stderr=_stderr_sink,
            cli_path=cli_path,
            env=_sdk_subprocess_env(),
        ),
    ):
        # Hybrid session_id capture — primary path (SDK v0.1.61+) + fallback.
        if session_id is None:
            session_id = getattr(msg, "session_id", None) or getattr(msg, "sessionId", None)
        if session_id is None and getattr(msg, "subtype", "") == "init":
            data = getattr(msg, "data", {}) or {}
            session_id = data.get("session_id") or data.get("sessionId")
        if hasattr(msg, "result"):
            final_result = str(msg.result)
    return final_result, session_id


def run_predictor_via_sdk(bundle_path: Path,
                          rendered_path: Path,
                          section_audit_path: Path,
                          result_path: Path) -> tuple[str | None, str | None]:
    """Sync wrapper for the one-turn predictor SDK call.

    Returns ``(final_result, session_id)`` tuple.
    """
    try:
        result = asyncio.run(_run_predictor_via_sdk(
            bundle_path, rendered_path, section_audit_path, result_path
        ))
    except ImportError as e:
        raise RuntimeError(
            "claude_agent_sdk is not available; cannot run --predict"
        ) from e

    # Central existence check — every caller that invokes the SDK is protected here.
    # Result first (canonical output → more informative error if both missing), then audit.
    if not result_path.exists():
        raise RuntimeError(f"Predictor finished without writing {result_path}")
    if not section_audit_path.exists():
        raise RuntimeError(f"Predictor finished without writing {section_audit_path}")

    return result


# ── CLI ──────────────────────────────────────────────────────────────

def _resolve_pit_mode(args, quarter_info):
    """Resolve ``(pit_cutoff, mode_label)`` from CLI args + quarter_info.

    Implements T1.5a per ``.claude/plans/learner.md`` §🔥. Rules:

    - ``--live`` and ``--pit`` are mutually exclusive → ``ValueError``.
    - ``--live`` → ``(None, "live")`` regardless of other flags.
    - ``--pit X`` → ``(X, "historical")`` regardless of other flags.
    - No ``--pit`` / ``--live`` with ``--predict`` or ``--learn``
      → ``(quarter_info["filed_8k"], "historical")``.  This is the default
      that closes the T1.5a bug: manual CLI runs against historical
      accessions no longer silently fall into live mode.
    - No ``--pit`` / ``--live`` / ``--predict`` / ``--learn``
      → ``(None, "live")``.  Preserves bundle-inspection mode (``--save``
      alone) where the caller explicitly didn't ask for a prediction.

    Raises ``ValueError`` if the default branch would fire but
    ``quarter_info`` is missing ``filed_8k`` — the caller must then pass
    ``--pit`` or ``--live`` explicitly.

    Scope: the cutoff returned here is the **predictor's bundle PIT** only.
    It flows into :func:`run_core_flow` → :func:`build_prediction_bundle`
    (``bundle["pit_cutoff"]``) and is consumed by the predictor via the
    bundle JSON file. It does **NOT** reach the learner.
    :func:`run_learner_for_quarter` has no ``pit_cutoff`` parameter and
    re-derives a later cutoff via :func:`derive_learner_pit`
    (typically ``Q_{n+1}.filed_8k``). That asymmetry is intentional —
    see :func:`run_learner_for_quarter` "PIT boundary" section.
    """
    if args.live and args.pit:
        raise ValueError(
            "--live and --pit are mutually exclusive. Pass exactly one."
        )
    if args.live:
        return None, "live"
    if args.pit:
        return args.pit, "historical"
    if args.predict or args.learn:
        filed_8k = (quarter_info or {}).get("filed_8k")
        if not filed_8k:
            raise ValueError(
                "Cannot default pit_cutoff to filed_8k: quarter_info is "
                "missing filed_8k. Pass --pit explicitly or --live."
            )
        return filed_8k, "historical"
    return None, "live"


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Earnings prediction bundle assembly")
    parser.add_argument("ticker", help="Company ticker")
    parser.add_argument("accession", nargs="?", help="8-K accession number")
    parser.add_argument("--quarter-info-json", default=None,
                        help="Path to a quarter_info JSON file (alternative to accession)")
    parser.add_argument("--pit", default=None, help="PIT cutoff (ISO8601) for historical mode")
    parser.add_argument("--live", action="store_true",
                        help="Force live mode (pit_cutoff=None). Mutually exclusive with --pit. "
                             "Required to preserve old accidental-live behavior on historical accessions.")
    parser.add_argument("--save", action="store_true", help="Write bundle artifacts to disk")
    parser.add_argument("--predict", action="store_true",
                        help="Save bundle artifacts and run one predictor SDK call")
    parser.add_argument("--learn", action="store_true",
                        help="Run learner/attribution after prediction for this quarter")
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

    # T1.5a: resolve PIT mode (default=filed_8k for --predict/--learn; --live opt-in;
    # --pit CLI wins). Historical calibration is now PIT-safe by construction.
    try:
        pit_cutoff, pit_mode = _resolve_pit_mode(args, quarter_info)
    except ValueError as e:
        parser.error(str(e))
    log.info("PIT mode resolved: mode=%s cutoff=%s (cli_pit=%s cli_live=%s)",
             pit_mode, pit_cutoff, args.pit, args.live)
    print(f"  pit_mode:    {pit_mode}")
    print(f"  pit_cutoff:  {pit_cutoff}")
    print()

    # U7: compute related_filings_dir up front when we'll persist the bundle.
    # Dry inspections (no --save / --predict) pass None — no on-disk side effects.
    related_filings_dir: str | None = None
    if args.save or args.predict:
        _early_paths = get_prediction_paths(args.ticker, quarter_info, args.save_dir)
        related_filings_dir = str(_early_paths["bundle_path"].parent / "related_filings")

    print(f"Building prediction bundle ({len(BUILDERS)} builders in parallel) ...", flush=True)
    t0 = datetime.now()
    bundle, rendered = run_core_flow(
        ticker=args.ticker,
        quarter_info=quarter_info,
        pit_cutoff=pit_cutoff,
        out_dir=args.save_dir,
        related_filings_dir=related_filings_dir,
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

    paths = get_prediction_paths(args.ticker, quarter_info, args.save_dir)
    if args.save or args.predict:
        write_json(paths["bundle_path"], bundle)
        write_text(paths["rendered_path"], rendered)
        print(f"Saved: {paths['bundle_path']}")
        print(f"Saved: {paths['rendered_path']}")

    # Run ledger — hoisted so both predict and learn blocks can use it.
    # Wrap covers: predict = SDK + finalize + validate (close on "succeeded"
    # only after validate passes); learn = the whole run_learner_for_quarter()
    # so derived-write recovery, retries, and lesson appends are all inside.
    # See .claude/plans/run_ledger.md §7.
    from run_ledger import open_run as _open_run, close_run as _close_run

    if args.predict:
        if paths["result_path"].exists():
            paths["result_path"].unlink()
        if paths["section_audit_path"].exists():
            paths["section_audit_path"].unlink()

        _pred_run_id = _open_run(
            "prediction",
            ticker=args.ticker,
            quarter_label=quarter_info.get("quarter_label"),
            accession_8k=quarter_info.get("accession_8k"),
            artifact_dir=str(paths["result_path"].parent),
        )
        prediction_validated = False
        try:
            print("Running predictor via SDK ...", flush=True)
            t1 = datetime.now()
            _pred_result, predictor_session_id = run_predictor_via_sdk(
                paths["bundle_path"],
                paths["rendered_path"],
                paths["section_audit_path"],
                paths["result_path"],
            )
            pred_elapsed = (datetime.now() - t1).total_seconds()
            # Existence checks now live inside run_predictor_via_sdk (central).

            # Canonicalize: LLM wrote 7 analytic fields; Python adds 8 metadata/derived + sdk_session_id.
            # Side-effects (best-effort): result.md sidecar + thinking.md harvest.
            finalize_prediction_result(
                result_path=paths["result_path"],
                ticker=args.ticker,
                quarter_info=quarter_info,
                model=PREDICTOR_MODEL_ID,
                sdk_session_id=predictor_session_id,
            )

            with open(paths["result_path"], encoding="utf-8") as f:
                prediction = json.load(f)

            # T1: extract renderer-emitted expected list for positional validation
            _, _expected_lessons = _render_learning_context(
                (bundle or {}).get("learning_context") or {}
            )
            # U67: strict subscript — never silently disable the source_id
            # check by .get() returning None when the catalog is missing.
            validate_prediction_result(
                prediction,
                expected_ticker=args.ticker,
                expected_quarter=quarter_info["quarter_label"],
                expected_lesson_texts=_expected_lessons,
                expected_source_ids=bundle["evidence_source_catalog"],
            )
            prediction_validated = True   # U67: gate quarantine on validation success

            print(f"Prediction written in {pred_elapsed:.1f}s: {paths['result_path']}")
            print(
                f"  direction: {prediction['direction']} | "
                f"confidence: {prediction['confidence_score']} ({prediction['confidence_bucket']}) | "
                f"magnitude: {prediction['magnitude_bucket']}"
            )
            _close_run(
                _pred_run_id, "succeeded",
                sdk_session_id=predictor_session_id,
                result_path=str(paths["result_path"]),
                thinking_path=str(paths["result_path"].parent / "thinking.md"),
                summary={
                    "direction": prediction.get("direction"),
                    "confidence_score": prediction.get("confidence_score"),
                    "confidence_bucket": prediction.get("confidence_bucket"),
                    "magnitude_bucket": prediction.get("magnitude_bucket"),
                    "expected_move_range_pct": prediction.get("expected_move_range_pct"),
                },
            )
        except Exception as _e:
            # U67 quarantine: rejected predictions must not be consumable by a
            # later learner-only run on the same quarter. finalize_prediction_result
            # writes result.json BEFORE validate_prediction_result raises, so on
            # validation failure the file is on disk with rejected content. Move it
            # aside so the learner's existence-only check on prediction_result_path
            # cannot silently consume it. Gate on prediction_validated so a post-
            # validation failure (e.g. run_ledger close failure) does NOT quarantine
            # a valid result.json. Rename failures fall back to unlink (best-effort).
            if not prediction_validated:
                try:
                    if paths["result_path"].exists():
                        rejected = paths["result_path"].with_suffix(".json.rejected")
                        try:
                            if rejected.exists():
                                rejected.unlink()
                            paths["result_path"].rename(rejected)
                        except OSError:
                            paths["result_path"].unlink(missing_ok=True)
                except Exception:
                    pass    # never let quarantine-cleanup mask the original failure
            _close_run(_pred_run_id, "failed", error=str(_e)[:500])
            raise

    if args.learn:
        # Load event.json for PIT derivation (needs chronological quarter list).
        # Auto-regenerate via Neo4j when the manifest is missing, invalid, or
        # does not contain the target quarter — semantic trigger, not age-based.
        # The shared helper lives with the Neo4j query it uses; make sure
        # scripts/earnings/earnings-orchestrator/scripts/ is on sys.path.
        event_json_path = COMPANIES_DIR / args.ticker.upper() / "events" / "event.json"
        target_ql = quarter_info["quarter_label"]
        target_acc = quarter_info["accession_8k"]

        # __file__ = scripts/earnings/earnings_orchestrator.py → repo root is parents[2]
        _eoo_scripts = str(Path(__file__).resolve().parents[2]
                           / ".claude" / "skills" / "earnings-orchestrator" / "scripts")
        if _eoo_scripts not in sys.path:
            sys.path.insert(0, _eoo_scripts)
        from event_json_manifest import ensure_event_json_for_target  # noqa: E402

        event_data, current_index = ensure_event_json_for_target(
            event_json_path, args.ticker, target_ql, target_acc,
        )
        events = event_data["events"]

        live_state_path = COMPANIES_DIR / args.ticker.upper() / "events" / "live_state.json"

        print(f"\nRunning learner for {args.ticker} {target_ql} ...", flush=True)
        t2 = datetime.now()
        _learn_dir = COMPANIES_DIR / args.ticker.upper() / "events" / target_ql / "learning"
        _learn_run_id = _open_run(
            "learning",
            ticker=args.ticker,
            quarter_label=target_ql,
            accession_8k=target_acc,
            artifact_dir=str(_learn_dir),
        )
        # Note: no pit_cutoff passed — run_learner_for_quarter re-derives its
        # own (Q_{n+1}.filed_8k via derive_learner_pit). pit_mode hardcoded
        # "historical" so --live on a historical accession still produces a
        # lesson stamped with a principled source_pit_cutoff rather than now().
        # See run_learner_for_quarter "PIT boundary" section for why this
        # differs from the predictor's bundle PIT.
        try:
            attribution, _outcome = run_learner_for_quarter(
                ticker=args.ticker,
                quarter_info=quarter_info,
                events=events,
                current_index=current_index,
                pit_mode="historical",
                live_state_path=live_state_path,
            )
            learn_elapsed = (datetime.now() - t2).total_seconds()

            if _outcome in LearnerOutcome.SUCCESS:
                # SUCCEEDED or RECOVERED — both produce a valid attribution dict.
                assert attribution is not None  # by LearnerOutcome contract
                print(f"Learner complete ({_outcome}) in {learn_elapsed:.1f}s")
                pd = attribution.get("primary_driver", {}) or {}
                fb = attribution.get("feedback", {}) or {}
                pc = fb.get("prediction_comparison", {}) or {}
                ar = attribution.get("actual_return", {}) or {}
                print(f"  primary_driver: {pd.get('category', '?')} — {pd.get('summary', '?')[:80]}")
                print(f"  direction_correct: {pc.get('direction_correct')}")
                print(f"  predictor_lessons: {len(fb.get('predictor_lessons', []))}")
                _close_run(
                    _learn_run_id, "succeeded",
                    sdk_session_id=attribution.get("sdk_session_id"),
                    result_path=str(_learn_dir / "result.json"),
                    thinking_path=str(_learn_dir / "thinking.md"),
                    summary={
                        "direction_correct":       pc.get("direction_correct"),
                        "magnitude_error_pct":     pc.get("magnitude_error_pct"),
                        "primary_driver_category": pd.get("category"),
                        "actual_daily_stock_pct":  ar.get("daily_stock_pct"),
                    },
                )
            elif _outcome in LearnerOutcome.SKIPPED:
                # Environmental — no prediction yet, or daily_stock unavailable.
                # NOT a failure; the event genuinely isn't ready to learn from.
                print(f"Learner skipped ({_outcome}) for {args.ticker} {target_ql} after {learn_elapsed:.1f}s")
                _close_run(_learn_run_id, "skipped", error=_outcome)
            else:
                # Pipeline-level failure: SDK didn't write, validator rejected,
                # lesson-append raised, etc. Outcome string IS the diagnostic.
                assert _outcome in LearnerOutcome.FAILED, f"unclassified outcome: {_outcome!r}"
                print(f"Learner failed ({_outcome}) for {args.ticker} {target_ql} after {learn_elapsed:.1f}s")
                _close_run(_learn_run_id, "failed", error=_outcome)
        except Exception as _e:
            _close_run(_learn_run_id, "failed", error=str(_e)[:500])
            raise


def _run_v2_regression_tests():
    """V2 regression tests for _fmt_guidance_value with corrected canonical_unit values.
    Verifies renderer behavior once V2 resolver produces correct units.
    Run with full env: python3 scripts/earnings/earnings_orchestrator.py --test"""

    passed = failed = 0
    def check(name, actual, expected_substr):
        nonlocal passed, failed
        if expected_substr in actual:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL {name}: expected '{expected_substr}' in {actual!r}")

    # Corrected usd: face-value dollar formatting (was m_usd → billions in V1)
    check("fmt_eps_usd", _fmt_guidance_value({'low': 3.2, 'high': 3.4}, 'usd'), '$3.20-$3.40')
    check("fmt_dps_usd", _fmt_guidance_value({'low': 0.32, 'high': 0.32}, 'usd'), '$0.32')

    # Corrected count: absolute quantity (was m_usd → $300M in V1)
    r_count = _fmt_guidance_value({'low': 300e6, 'high': 300e6}, 'count')
    check("fmt_count_300m", r_count, '300')

    # m_usd unchanged: aggregate money still formatted in B/M
    check("fmt_rev_musd", _fmt_guidance_value({'low': 94000, 'high': 98000}, 'm_usd'), 'B')

    # Ratios
    check("fmt_pct", _fmt_guidance_value({'low': 42, 'high': 42}, 'percent'), '42%')
    check("fmt_pct_yoy", _fmt_guidance_value({'low': 5, 'high': 7}, 'percent_yoy'), 'YoY')
    check("fmt_bps", _fmt_guidance_value({'low': 50, 'high': 50}, 'basis_points'), 'bps')
    check("fmt_x", _fmt_guidance_value({'low': 2.5, 'high': 2.5}, 'x'), '2.5x')

    # Qualitative-only
    check("fmt_qual", _fmt_guidance_value({'qualitative': 'strong growth expected'}, 'unknown'), 'strong growth')

    print(f"\n{passed} passed, {failed} failed out of {passed + failed}")
    return failed == 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        sys.exit(0 if _run_v2_regression_tests() else 1)
    main()
