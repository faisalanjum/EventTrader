#!/usr/bin/env -S uv run --script

# /// script
# dependencies = []
# ///

"""
Claude Code hook: build/refresh a per-ticker earnings events manifest after discovery.

Trigger: PostToolUse on Bash. We only act when the Bash command includes
`get_quarterly_filings.py`.

Input: hook JSON on stdin (tool_input.command, tool_response.stdout).
Output: always prints `{}` and exits 0 (never blocks the agent).
"""

from __future__ import annotations

import json
import os
import shlex
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    from zoneinfo import ZoneInfo  # py>=3.9
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore[assignment]


REPO_ROOT = Path("/home/faisal/EventMarketDB")
COMPANIES_DIR = REPO_ROOT / "earnings-analysis" / "Companies"
TARGET_SCRIPT_BASENAME = "get_quarterly_filings.py"


def _json_ok() -> None:
    # Claude expects JSON output from hooks.
    sys.stdout.write("{}")


def _na_to_none(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    v = v.strip()
    if not v or v.upper() == "N/A":
        return None
    return v


def _extract_ticker_from_command(command: str) -> Optional[str]:
    try:
        parts = shlex.split(command)
    except Exception:
        parts = command.split()

    for i, p in enumerate(parts):
        if p.endswith(TARGET_SCRIPT_BASENAME):
            if i + 1 < len(parts):
                t = parts[i + 1]
                if t.startswith("-"):
                    return None
                return t.strip().upper()
    return None


@dataclass(frozen=True)
class ParsedTable:
    headers: list[str]
    rows: list[list[str]]

def _parse_pipe_table(stdout: str) -> Optional[ParsedTable]:
    lines = [ln.rstrip("\n") for ln in (stdout or "").splitlines()]
    lines = [ln.strip() for ln in lines if ln.strip()]
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
    for ln in lines[header_idx + 1 :]:
        cols = [c.strip() for c in ln.split("|")]
        if len(cols) != len(header):
            continue
        rows.append(cols)
    return ParsedTable(headers=header, rows=rows)


def _parse_column_table(stdout: str) -> Optional[ParsedTable]:
    lines = [ln.rstrip("\n") for ln in (stdout or "").splitlines()]
    lines = [ln.strip() for ln in lines if ln.strip()]
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
    for ln in lines[header_idx + 1 :]:
        cols = ln.split()
        if len(cols) != len(header):
            # Fail-soft: ignore malformed lines.
            continue
        rows.append(cols)
    return ParsedTable(headers=header, rows=rows)


def _build_manifest(ticker: str, table: ParsedTable) -> dict[str, Any]:
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

        events.append(
            {
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
            }
        )

    return {
        "schema_version": 1,
        "ticker": ticker,
        # Store in Eastern Time for quick eyeballing alongside filings/market session.
        # (EST in winter, EDT in summer).
        "built_at": (
            datetime.now(ZoneInfo("America/New_York")).isoformat()
            if ZoneInfo is not None
            else datetime.now(timezone.utc).isoformat()
        ),
        "events": events,
    }


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def main() -> None:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            _json_ok()
            return

        hook = json.loads(raw)
        command = (hook.get("tool_input") or {}).get("command") or ""
        if TARGET_SCRIPT_BASENAME not in command:
            _json_ok()
            return

        ticker = _extract_ticker_from_command(command)
        if not ticker:
            _json_ok()
            return

        stdout = (hook.get("tool_response") or {}).get("stdout") or ""
        table = _parse_pipe_table(stdout) or _parse_column_table(stdout)
        if not table:
            _json_ok()
            return

        manifest = _build_manifest(ticker, table)
        out_path = COMPANIES_DIR / ticker / "events" / "event.json"
        _atomic_write_json(out_path, manifest)
        _json_ok()
    except Exception:
        # Never block/interrupt the agent. Best-effort only.
        _json_ok()


if __name__ == "__main__":
    main()
