#!/usr/bin/env python3
"""Builder Adapters — Uniform interface for all 7 prediction bundle builders.

Every function follows the same contract:

    build_X(ticker, quarter_info, pit_cutoff=None, out_path=None, **kwargs) -> dict

    pit_cutoff:
        None  → live mode, unrestricted
        str   → historical mode, PIT-gated (ISO8601 timestamp)

    Returns: packet dict with at minimum:
        schema_version, ticker, pit_cutoff, effective_cutoff_ts, source_mode, assembled_at

The orchestrator calls ONLY these functions. The adapters translate arguments
to legacy builder signatures, normalize return shapes, and enrich output packets.

Underlying builders are NOT modified — adapters import and wrap them.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Path setup ──────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "scripts/earnings"))
sys.path.insert(0, str(_PROJECT_ROOT / ".claude/skills/earnings-orchestrator/scripts"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _derive_mode(pit_cutoff: str | None) -> str:
    return "historical" if pit_cutoff else "live"


def _enrich_packet(packet: dict, pit_cutoff: str | None,
                   effective_cutoff_ts: str | None) -> dict:
    """Add standardized metadata fields to any builder packet."""
    packet["pit_cutoff"] = pit_cutoff
    packet["source_mode"] = _derive_mode(pit_cutoff)
    packet["effective_cutoff_ts"] = effective_cutoff_ts
    return packet


def _write_enriched(packet: dict, out_path: str) -> None:
    """Write the enriched packet to disk (atomic temp+rename)."""
    _ensure_dir(out_path)
    tmp = out_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(packet, f, indent=2, default=str, ensure_ascii=False)
    os.replace(tmp, out_path)


def _ensure_dir(path: str) -> None:
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)


class _SuppressStdout:
    """Context manager to suppress builder stdout noise (prints, rendered text).

    Redirects stdout to /dev/null during legacy builder calls.
    Stderr is left open for genuine errors.

    Thread-safety note: sys.stdout is global, so swapping it from concurrent
    threads in ThreadPoolExecutor can race. For the orchestrator's parallel
    execution, each builder runs in its own thread — the race window is small
    (only during enter/exit) and the worst case is a few lines of builder noise
    leaking through, not data corruption. For true isolation, the orchestrator
    should use subprocess-level redirection or capture at a lower level.
    """
    def __enter__(self):
        self._orig = sys.stdout
        self._devnull = open(os.devnull, 'w')
        sys.stdout = self._devnull
        return self

    def __exit__(self, *args):
        sys.stdout = self._orig
        self._devnull.close()


# ═══════════════════════════════════════════════════════════════════════
# Builder #1: 8k_packet
# ═══════════════════════════════════════════════════════════════════════

def build_8k_packet(ticker: str, quarter_info: dict,
                    pit_cutoff: str | None = None,
                    out_path: str | None = None,
                    **kwargs) -> dict:
    """Adapter for build_8k_packet. Accession-anchored — pit_cutoff is metadata only.

    effective_cutoff_ts: always null (no temporal query).
    """
    from warmup_cache import build_8k_packet as _legacy

    accession = quarter_info["accession_8k"]
    out = out_path or f"/tmp/earnings_8k_packet_{accession}.json"
    _ensure_dir(out)

    # Legacy builder calls sys.exit(1) on missing report — catch it
    try:
        with _SuppressStdout():
            _legacy(accession, ticker, out_path=out)
    except SystemExit as e:
        raise ValueError(
            f"8-K not found for accession={accession} ticker={ticker} "
            f"(legacy builder called sys.exit({e.code}))"
        ) from None

    # Legacy returns None — read packet from disk
    with open(out, encoding="utf-8") as f:
        packet = json.load(f)

    _enrich_packet(packet, pit_cutoff, effective_cutoff_ts=None)
    _write_enriched(packet, out)
    return packet


# ═══════════════════════════════════════════════════════════════════════
# Builder #2: guidance_history
# ═══════════════════════════════════════════════════════════════════════

def build_guidance_history(ticker: str, quarter_info: dict,
                           pit_cutoff: str | None = None,
                           out_path: str | None = None,
                           **kwargs) -> dict:
    """Adapter for build_guidance_history.

    effective_cutoff_ts: null for live, pit_cutoff for historical.
    """
    from warmup_cache import build_guidance_history as _legacy

    out = out_path or f"/tmp/earnings_guidance_{ticker}.json"
    _ensure_dir(out)

    # Translate: pit_cutoff → legacy 'pit' param
    with _SuppressStdout():
        _legacy(ticker, pit=pit_cutoff, out_path=out)

    # Legacy returns None — read packet from disk
    with open(out, encoding="utf-8") as f:
        packet = json.load(f)

    effective = pit_cutoff if pit_cutoff else None
    _enrich_packet(packet, pit_cutoff, effective_cutoff_ts=effective)
    _write_enriched(packet, out)
    return packet


# ═══════════════════════════════════════════════════════════════════════
# Builder #3: inter_quarter_context
# ═══════════════════════════════════════════════════════════════════════

def build_inter_quarter_context(ticker: str, quarter_info: dict,
                                 pit_cutoff: str | None = None,
                                 out_path: str | None = None,
                                 **kwargs) -> dict:
    """Adapter for build_inter_quarter_context.

    effective_cutoff_ts: filed_8k for live, pit_cutoff for historical.
    """
    from warmup_cache import build_inter_quarter_context as _legacy

    prev_8k_ts = quarter_info.get("prev_8k_ts")
    if not prev_8k_ts:
        raise ValueError("quarter_info must include prev_8k_ts for inter_quarter_context")

    filed_8k = quarter_info["filed_8k"]
    # Historical: use pit_cutoff as context boundary
    # Live: use filed_8k as the natural window boundary
    context_cutoff = pit_cutoff or filed_8k
    cutoff_reason = "pit_cutoff" if pit_cutoff else "filed_8k"

    out = out_path or f"/tmp/earnings_inter_quarter_{ticker}.json"
    _ensure_dir(out)

    # Legacy returns (out_path, rendered) tuple — we discard rendered
    with _SuppressStdout():
        _legacy(ticker, prev_8k_ts, context_cutoff,
                out_path=out, context_cutoff_reason=cutoff_reason)

    # Read packet from disk
    with open(out, encoding="utf-8") as f:
        packet = json.load(f)

    effective = pit_cutoff if pit_cutoff else filed_8k
    _enrich_packet(packet, pit_cutoff, effective_cutoff_ts=effective)
    _write_enriched(packet, out)
    return packet


# ═══════════════════════════════════════════════════════════════════════
# Builder #4: peer_earnings_snapshot
# ═══════════════════════════════════════════════════════════════════════

def build_peer_earnings_snapshot(ticker: str, quarter_info: dict,
                                  pit_cutoff: str | None = None,
                                  out_path: str | None = None,
                                  **kwargs) -> dict:
    """Adapter for build_peer_earnings_snapshot.

    effective_cutoff_ts: derived now() for live, pit_cutoff for historical.
    Builder requires non-None cutoff — adapter derives now() for live.
    """
    from peer_earnings_snapshot import build_peer_earnings_snapshot as _legacy

    # Builder crashes on None — derive runtime anchor for live
    effective = pit_cutoff or _now_iso()

    out = out_path or f"/tmp/peer_earnings_snapshot_{ticker}.json"
    _ensure_dir(out)

    # Pass through builder-specific kwargs (top_n, window_start)
    with _SuppressStdout():
        packet = _legacy(ticker, effective, out_path=out, **kwargs)

    # Output packet shows original pit_cutoff (None for live), not the derived anchor
    _enrich_packet(packet, pit_cutoff, effective_cutoff_ts=effective)
    _write_enriched(packet, out)
    return packet


# ═══════════════════════════════════════════════════════════════════════
# Builder #5: macro_snapshot
# ═══════════════════════════════════════════════════════════════════════

def build_macro_snapshot(ticker: str, quarter_info: dict,
                          pit_cutoff: str | None = None,
                          out_path: str | None = None,
                          **kwargs) -> dict:
    """Adapter for build_macro_snapshot.

    effective_cutoff_ts: derived now() for live, pit_cutoff for historical.
    Default source policy: yahoo for live, polygon for historical (overridable via kwargs).
    """
    from macro_snapshot import build_macro_snapshot as _legacy

    # Builder crashes on None — derive runtime anchor for live
    effective = pit_cutoff or _now_iso()

    # Default source policy (overridable)
    source = kwargs.pop("source", "polygon" if pit_cutoff else "yahoo")
    # Historical: use the filing's market_session. Live: let builder auto-infer from now()
    market_session = quarter_info.get("market_session") if pit_cutoff else None

    out = out_path or f"/tmp/macro_snapshot_{ticker}.json"
    _ensure_dir(out)

    with _SuppressStdout():
        packet = _legacy(ticker, effective, market_session, out_path=out, source=source, **kwargs)

    _enrich_packet(packet, pit_cutoff, effective_cutoff_ts=effective)
    _write_enriched(packet, out)
    return packet


# ═══════════════════════════════════════════════════════════════════════
# Builder #6: consensus
# ═══════════════════════════════════════════════════════════════════════

def build_consensus(ticker: str, quarter_info: dict,
                    pit_cutoff: str | None = None,
                    out_path: str | None = None,
                    **kwargs) -> dict:
    """Adapter for build_consensus. Near-passthrough.

    effective_cutoff_ts: null for live, pit_cutoff for historical.
    """
    from build_consensus import build_consensus as _legacy

    # Legacy uses as_of_ts, not pit_cutoff
    qi_for_legacy = {
        "period_of_report": quarter_info.get("period_of_report", ""),
        "filed_8k": quarter_info.get("filed_8k", ""),
        "market_session": quarter_info.get("market_session", ""),
    }

    out = out_path or f"/tmp/consensus_{ticker}.json"

    with _SuppressStdout():
        packet = _legacy(ticker, qi_for_legacy, as_of_ts=pit_cutoff, out_path=out)

    # Normalize: remove legacy as_of_ts, replace with pit_cutoff
    packet.pop("as_of_ts", None)
    effective = pit_cutoff if pit_cutoff else None
    _enrich_packet(packet, pit_cutoff, effective_cutoff_ts=effective)
    _write_enriched(packet, out)
    return packet


# ═══════════════════════════════════════════════════════════════════════
# Builder #7: prior_financials
# ═══════════════════════════════════════════════════════════════════════

def build_prior_financials(ticker: str, quarter_info: dict,
                            pit_cutoff: str | None = None,
                            out_path: str | None = None,
                            **kwargs) -> dict:
    """Adapter for build_prior_financials. Near-passthrough.

    effective_cutoff_ts: null for live, pit_cutoff for historical.
    """
    from build_prior_financials import build_prior_financials as _legacy

    qi_for_legacy = {
        "period_of_report": quarter_info.get("period_of_report", ""),
        "filed_8k": quarter_info.get("filed_8k", ""),
        "market_session": quarter_info.get("market_session", ""),
        "quarter_label": quarter_info.get("quarter_label", ""),
    }

    out = out_path or f"/tmp/prior_financials_{ticker}.json"

    # Pass through builder-specific kwargs (allow_yahoo)
    with _SuppressStdout():
        packet = _legacy(ticker, qi_for_legacy, as_of_ts=pit_cutoff, out_path=out, **kwargs)

    # Normalize: remove legacy as_of_ts, replace with pit_cutoff
    packet.pop("as_of_ts", None)
    effective = pit_cutoff if pit_cutoff else None
    _enrich_packet(packet, pit_cutoff, effective_cutoff_ts=effective)
    _write_enriched(packet, out)
    return packet
