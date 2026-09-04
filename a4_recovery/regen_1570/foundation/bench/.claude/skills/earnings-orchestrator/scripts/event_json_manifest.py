"""Shared helpers for the per-ticker earnings events manifest at
``earnings-analysis/Companies/{TICKER}/events/event.json``.

Two entry points converge on one set of helpers so the manifest shape is
single-sourced:

  * ``earnings_orchestrator.py`` (learner branch) calls
    :func:`ensure_event_json_for_target` which auto-regenerates the
    manifest when it is missing, invalid, or does not contain the target
    quarter. Regen triggers are **semantic** (target-quarter match),
    never age/mtime-based — a fresh file can still miss the target; an
    old file can still be correct.

  * The ``.claude/hooks/build_orchestrator_event_json.py`` PostToolUse
    hook parses the stdout of a manual ``get_quarterly_filings.py``
    invocation and writes the same manifest via the same builder.

Both paths share parsing (``parse_pipe_table`` / ``parse_column_table``),
manifest building (``build_manifest``), and atomic write
(``atomic_write_json``).  :func:`refresh_event_json` additionally
handles the Neo4j-query → build → write chain without depending on
Claude Code's hook runner.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

try:
    from zoneinfo import ZoneInfo  # py>=3.9
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore[assignment]

_HERE = Path(__file__).resolve().parent
# .claude/skills/earnings-orchestrator/scripts → repo root is parents[3]
REPO_ROOT = _HERE.parents[3]
COMPANIES_DIR = REPO_ROOT / "earnings-analysis" / "Companies"


# ── Parsing primitives (copied verbatim from the old hook) ────────────────

@dataclass(frozen=True)
class ParsedTable:
    headers: list[str]
    rows: list[list[str]]


def _na_to_none(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    v = v.strip()
    if not v or v.upper() == "N/A":
        return None
    return v


def parse_pipe_table(stdout: str) -> Optional[ParsedTable]:
    """Parse pipe-delimited output from ``get_earnings_with_10q``.

    Returns ``None`` when no ``accession_8k|...`` header line is found.
    """
    lines = [ln.strip() for ln in (stdout or "").splitlines() if ln.strip()]
    if not lines:
        return None

    header_idx: Optional[int] = None
    for i, ln in enumerate(lines):
        if ln.startswith("accession_8k|"):
            header_idx = i
            break
    if header_idx is None:
        return None

    header = [h.strip() for h in lines[header_idx].split("|")]
    if not header or header[0] != "accession_8k":
        return None

    rows: list[list[str]] = []
    for ln in lines[header_idx + 1:]:
        cols = [c.strip() for c in ln.split("|")]
        if len(cols) != len(header):
            continue
        rows.append(cols)
    return ParsedTable(headers=header, rows=rows)


def parse_column_table(stdout: str) -> Optional[ParsedTable]:
    """Fallback parser for whitespace-column-aligned output."""
    lines = [ln.strip() for ln in (stdout or "").splitlines() if ln.strip()]
    if not lines:
        return None

    header_idx: Optional[int] = None
    header: list[str] = []
    for i, ln in enumerate(lines):
        cols = ln.split()
        if cols and cols[0] == "accession_8k":
            header_idx = i
            header = cols
            break
    if header_idx is None:
        return None

    rows: list[list[str]] = []
    for ln in lines[header_idx + 1:]:
        cols = ln.split()
        if len(cols) != len(header):
            continue
        rows.append(cols)
    return ParsedTable(headers=header, rows=rows)


# ── Manifest builder ──────────────────────────────────────────────────────

def build_manifest(ticker: str, table: ParsedTable) -> dict[str, Any]:
    """Build the event.json payload from a parsed table. Shape is frozen:

      {schema_version: 1, ticker, built_at, events: [{...}]}
    """
    idx = {name: i for i, name in enumerate(table.headers)}

    events: list[dict[str, Any]] = []
    for cols in table.rows:
        get = lambda k: _na_to_none(cols[idx[k]]) if k in idx else None

        accession_8k = get("accession_8k")
        fiscal_year = get("fiscal_year")
        fiscal_quarter = get("fiscal_quarter")

        if fiscal_year and fiscal_quarter:
            quarter_label = f"{fiscal_quarter}_FY{fiscal_year}"
        else:
            quarter_label = f"8K_{accession_8k}" if accession_8k else "8K_UNKNOWN"

        events.append({
            "event_id": quarter_label,
            "quarter_label": quarter_label,
            "accession_8k": accession_8k,
            "filed_8k": get("filed_8k"),
            "market_session_8k": get("market_session_8k"),
            "accession_10q": get("accession_10q"),
            "filed_10q": get("filed_10q"),
            "market_session_10q": get("market_session_10q"),
            "form_type": get("form_type"),
            "fiscal_year": int(fiscal_year) if fiscal_year and fiscal_year.isdigit() else fiscal_year,
            "fiscal_quarter": fiscal_quarter,
            "lag": get("lag"),
        })

    return {
        "schema_version": 1,
        "ticker": ticker,
        # Eastern Time for quick eyeballing alongside filings/market session
        "built_at": (
            datetime.now(ZoneInfo("America/New_York")).isoformat()
            if ZoneInfo is not None
            else datetime.now(timezone.utc).isoformat()
        ),
        "events": events,
    }


# ── Atomic write ──────────────────────────────────────────────────────────

def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write ``payload`` to ``path`` via tmp + ``os.replace``.

    Atomic on POSIX — readers never see a half-written file. Concurrent
    callers with the same payload for the same path see last-writer-wins
    but never corruption.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(
        json.dumps(payload, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)


# ── Neo4j-driven refresh (for orchestrator auto-regen) ───────────────────

def refresh_event_json(
    ticker: str,
    *,
    out_dir: Optional[Path] = None,
    fetch_stdout: Optional[Callable[[str], str]] = None,
) -> dict[str, Any]:
    """Query Neo4j, build the manifest, write ``events/event.json``.

    This is the path the orchestrator uses when it detects the manifest is
    missing, invalid, or missing the target quarter. Unlike the hook path,
    it does NOT depend on Claude Code's hook runner — it directly calls
    the same Neo4j query function used by the manual ``get_quarterly_filings``
    CLI.

    Args:
        ticker: Uppercased on entry.
        out_dir: Override the Companies/ root (testing).
        fetch_stdout: Optional override returning the
            ``get_earnings_with_10q`` string output (testing — bypasses Neo4j).

    Returns:
        The manifest dict (also written atomically to disk).

    Raises:
        RuntimeError: Neo4j error string from the query or unparseable output.
    """
    ticker = ticker.upper()

    if fetch_stdout is None:
        # Lazy import to avoid bringing Neo4j deps in at module-import time.
        if str(_HERE) not in sys.path:
            sys.path.insert(0, str(_HERE))
        from get_quarterly_filings import get_earnings_with_10q  # noqa: E402
        fetch_stdout = lambda t: get_earnings_with_10q(t, dedupe=True)

    stdout = fetch_stdout(ticker)
    if isinstance(stdout, str) and stdout.startswith("ERROR|"):
        raise RuntimeError(f"get_earnings_with_10q failed for {ticker}: {stdout[:500]}")

    table = parse_pipe_table(stdout) or parse_column_table(stdout)
    if table is None:
        raise RuntimeError(
            f"Could not parse get_earnings_with_10q output for {ticker} "
            f"(stdout prefix: {str(stdout)[:200]!r})"
        )

    manifest = build_manifest(ticker, table)
    companies_dir = out_dir if out_dir is not None else COMPANIES_DIR
    out_path = companies_dir / ticker / "events" / "event.json"
    atomic_write_json(out_path, manifest)
    return manifest


# ── Orchestrator-facing decision helper ──────────────────────────────────

def ensure_event_json_for_target(
    path: Path,
    ticker: str,
    target_quarter_label: str,
    target_accession_8k: str,
    *,
    refresh_fn: Optional[Callable[[str], dict[str, Any]]] = None,
) -> tuple[dict[str, Any], int]:
    """Load ``event.json`` from ``path`` and return ``(manifest, target_index)``.

    Regeneration is triggered semantically (NOT age-based) when the file is:
      * **missing**: FileNotFoundError / OSError on read
      * **invalid**: JSONDecodeError on parse
      * **target-absent**: parseable but no event matches
        ``quarter_label == target_quarter_label`` OR
        ``accession_8k == target_accession_8k``

    After regen, re-reads and re-validates. If the target is still absent,
    raises — typically indicates Neo4j has not ingested the 8-K yet (its
    ``pf.daily_stock`` relationship property is still NULL).

    The ``refresh_fn`` parameter is injected for testing; defaults to
    :func:`refresh_event_json`.
    """
    def _read_manifest() -> Optional[dict[str, Any]]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return None

    def _find_index(events: list[dict[str, Any]]) -> Optional[int]:
        for i, e in enumerate(events):
            if (e.get("quarter_label") == target_quarter_label
                    or e.get("accession_8k") == target_accession_8k):
                return i
        return None

    data = _read_manifest()
    idx = _find_index(data.get("events", [])) if data else None

    if data is None or idx is None:
        # Semantic regen — not age-based.
        reason = "missing/invalid" if data is None else "target-absent"
        import logging
        logging.getLogger(__name__).info(
            "event.json %s for %s %s — regenerating via Neo4j",
            reason, ticker, target_quarter_label,
        )
        (refresh_fn or refresh_event_json)(ticker)
        data = _read_manifest()
        if data is None:
            raise RuntimeError(f"event.json regen failed — could not read {path}")
        idx = _find_index(data.get("events", []))
        if idx is None:
            raise RuntimeError(
                f"Quarter {target_quarter_label} ({target_accession_8k}) "
                f"still not found after regen — Neo4j may not have this 8-K yet "
                f"(needs pf.daily_stock relationship populated)"
            )

    return data, idx
