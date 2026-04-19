"""Production-ready run-lifecycle ledger for the three earnings pipelines.

Design + spec: ``.claude/plans/run_ledger.md``.

Two files:
  * ``earnings-analysis/operations/run_ledger.jsonl`` — authoritative
    append-only state. Each line is one state transition for a run.
    Current state = last-row-wins collapse by ``run_id``.
  * ``earnings-analysis/operations/Run Index.md`` — human-facing static
    Markdown tables. Regenerated on every state transition so "In Flight"
    is actually real-time.

Concurrency: ``fcntl.flock(LOCK_EX) + flush + fsync`` on every append.
Safe for multiple processes on a SINGLE-HOST shared filesystem (e.g., the
K8s extraction-worker hostPath mount where 1–7 pods coexist on one node).
NOT safe for NFS / distributed filesystems with weak locking.

Readers tolerate torn/malformed JSONL lines silently (skip) so a crashed
writer never poisons the reader for later rows.

Atomic write on the index: write to ``{path}.tmp.{pid}`` + ``os.replace``.
Crash during regeneration never leaves a half-written index visible.

The module is pure stdlib — no Neo4j, no SDK, no Obsidian plugin.
"""
from __future__ import annotations

import fcntl
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
# scripts/earnings/run_ledger.py → repo root is parents[1]
REPO_ROOT = _HERE.parents[1]
OPERATIONS_DIR = REPO_ROOT / "earnings-analysis" / "operations"
LEDGER_PATH = OPERATIONS_DIR / "run_ledger.jsonl"
INDEX_PATH = OPERATIONS_DIR / "Run Index.md"

SCHEMA_VERSION = 1
VALID_COMPONENTS: frozenset[str] = frozenset({"guidance", "prediction", "learning"})
TERMINAL_STATUSES: frozenset[str] = frozenset(
    {"succeeded", "failed", "skipped", "rate_limited"}
)
ALL_STATUSES: frozenset[str] = TERMINAL_STATUSES | {"running"}


# ── Atomic append primitive ───────────────────────────────────────────────

def _append_row(path: Path, row: dict[str, Any]) -> None:
    """Append ``row`` as one JSON line. Concurrency-safe on single-host FS.

    Uses ``fcntl.flock(LOCK_EX)`` plus ``flush`` + ``fsync`` so multiple
    writers on the same host (extraction-worker pods, orchestrator process,
    etc.) serialize cleanly. Not safe across NFS / distributed FS.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, ensure_ascii=False, sort_keys=False) + "\n"
    with open(path, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _read_all_rows(path: Path) -> list[dict[str, Any]]:
    """Read every parseable row from the ledger; skip torn/malformed lines.

    Returns empty list if the file doesn't exist — a fresh vault starts with
    no ledger.
    """
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    # Torn write from a crashed process — silently skip.
                    continue
    except OSError:
        return []
    return rows


# ── Public API ────────────────────────────────────────────────────────────

def open_run(
    component: str,
    *,
    ticker: str,
    quarter_label: str | None = None,
    accession_8k: str | None = None,
    source_id: str | None = None,
    source_asset: str | None = None,
    experiment_name: str | None = None,
    artifact_dir: str | None = None,
    ledger_path: Path | None = None,
    index_path: Path | None = None,
) -> str:
    """Mark a new run as ``running``. Append one row. Refresh the index note.

    Returns a fresh ``run_id`` (uuid4 string) to pass back to :func:`close_run`.

    Contract: this must fire at the OUTERMOST execution boundary of a
    pipeline attempt — BEFORE the SDK call, not inside a finalizer. See
    ``.claude/plans/run_ledger.md`` §7 for the exact wrap pattern per
    pipeline.
    """
    if component not in VALID_COMPONENTS:
        raise ValueError(f"component must be one of {VALID_COMPONENTS}, got {component!r}")

    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    row = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "component": component,
        "status": "running",
        "ticker": ticker.upper() if ticker else None,
        "quarter_label": quarter_label,
        "accession_8k": accession_8k,
        "source_id": source_id,
        "source_asset": source_asset,
        "experiment_name": experiment_name,
        "sdk_session_id": None,
        "started_at": now,
        "finished_at": None,
        "elapsed_seconds": None,
        "artifact_dir": artifact_dir,
        "result_path": None,
        "thinking_path": None,
        "error": None,
        "summary": {},
    }

    _append_row(ledger_path or LEDGER_PATH, row)
    try:
        refresh_index(ledger_path=ledger_path, index_path=index_path)
    except Exception:  # noqa: BLE001 — index refresh must never block the caller
        pass
    return run_id


def close_run(
    run_id: str,
    status: str,
    *,
    sdk_session_id: str | None = None,
    result_path: str | None = None,
    thinking_path: str | None = None,
    error: str | None = None,
    summary: dict[str, Any] | None = None,
    ledger_path: Path | None = None,
    index_path: Path | None = None,
) -> None:
    """Mark a run as terminal. Append one row. Refresh the index note.

    ``status`` must be one of the terminal statuses
    (``succeeded`` | ``failed`` | ``skipped`` | ``rate_limited``).

    The row reuses ``run_id`` so the reader collapses multiple rows
    (``running`` at start, terminal at end) to the last-row-wins state.
    Retries of the same work are separate ``run_id`` values — each attempt
    is its own row.

    Index refresh errors are swallowed so a rendering failure never blocks
    a pipeline shutdown.
    """
    if status not in TERMINAL_STATUSES:
        raise ValueError(
            f"close_run status must be terminal "
            f"({sorted(TERMINAL_STATUSES)}); got {status!r}"
        )

    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat().replace("+00:00", "Z")

    # Try to preserve started_at / compute elapsed by looking up the original
    # running row — but don't fail if it's missing (the ledger may have been
    # rotated, pruned, or this is a close of a run we never opened).
    started_at = None
    path = ledger_path or LEDGER_PATH
    rows = _read_all_rows(path)
    for r in rows:
        if r.get("run_id") == run_id and r.get("status") == "running":
            started_at = r.get("started_at")
            break

    elapsed = None
    if started_at:
        try:
            started_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            elapsed = round((now_dt - started_dt).total_seconds(), 2)
        except (ValueError, TypeError):
            pass

    # Copy the identifying fields from the opening row so each row is
    # self-describing. This means a reader can render any row without
    # having to also scan the opening row.
    open_row: dict[str, Any] = {}
    for r in rows:
        if r.get("run_id") == run_id and r.get("status") == "running":
            open_row = r
            break

    close = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "component": open_row.get("component"),
        "status": status,
        "ticker": open_row.get("ticker"),
        "quarter_label": open_row.get("quarter_label"),
        "accession_8k": open_row.get("accession_8k"),
        "source_id": open_row.get("source_id"),
        "source_asset": open_row.get("source_asset"),
        "experiment_name": open_row.get("experiment_name"),
        "sdk_session_id": sdk_session_id,
        "started_at": started_at,
        "finished_at": now,
        "elapsed_seconds": elapsed,
        "artifact_dir": open_row.get("artifact_dir"),
        "result_path": result_path,
        "thinking_path": thinking_path,
        "error": (error[:500] if error else None),
        "summary": summary or {},
    }

    _append_row(path, close)
    try:
        refresh_index(ledger_path=path, index_path=index_path)
    except Exception:  # noqa: BLE001
        pass


def current_state(
    *,
    component: str | None = None,
    status: str | None = None,
    limit: int | None = None,
    ledger_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Return each run's current state (last-row-wins collapse by ``run_id``).

    Applies optional filters. Sort is reverse-chronological by
    ``started_at``. Pass ``limit`` to cap the result list size.
    """
    rows = _read_all_rows(ledger_path or LEDGER_PATH)
    latest: dict[str, dict[str, Any]] = {}
    for r in rows:
        run_id = r.get("run_id")
        if run_id is not None:
            latest[run_id] = r

    out = list(latest.values())
    if component is not None:
        out = [r for r in out if r.get("component") == component]
    if status is not None:
        out = [r for r in out if r.get("status") == status]
    # Reverse-chrono by started_at; missing values sort last
    out.sort(key=lambda r: (r.get("started_at") or ""), reverse=True)
    if limit is not None:
        out = out[:limit]
    return out


# ── Index rendering (Python-generated static Markdown tables) ─────────────

_STATUS_EMOJI = {
    "running": "🔄",
    "succeeded": "✅",
    "failed": "❌",
    "skipped": "⏭",
    "rate_limited": "⏸",
}


def _fmt(v: Any) -> str:
    """Markdown-safe cell rendering."""
    if v is None or v == "":
        return "—"
    if isinstance(v, bool):
        return "True" if v else "False"
    if isinstance(v, list) and len(v) == 2:
        # Expected move range: [3.0, 6.5] → "3.0–6.5%"
        return f"{v[0]}–{v[1]}%"
    s = str(v)
    # Escape pipe characters — they'd break the Markdown table
    return s.replace("|", "\\|")


def _fmt_status(status: str) -> str:
    emoji = _STATUS_EMOJI.get(status, "?")
    return f"{emoji} {status}"


def _fmt_date(iso_ts: str | None) -> str:
    if not iso_ts:
        return "—"
    return iso_ts[:10]  # YYYY-MM-DD


def _short_id(run_id: str | None) -> str:
    if not run_id:
        return "—"
    return run_id[:8]


def _render_in_flight_section(running: list[dict[str, Any]]) -> str:
    header = "## In Flight (status = running)\n\n"
    if not running:
        return header + "_No runs in flight._\n\n"
    lines = [
        "| run_id | component | ticker | quarter | started_at |",
        "|---|---|---|---|---|",
    ]
    for r in running:
        lines.append(
            "| "
            + " | ".join([
                _short_id(r.get("run_id")),
                _fmt(r.get("component")),
                _fmt(r.get("ticker")),
                _fmt(r.get("quarter_label")),
                _fmt(r.get("started_at")),
            ])
            + " |"
        )
    return header + "\n".join(lines) + "\n\n"


def _render_predictions_section(rows: list[dict[str, Any]]) -> str:
    header = "## Recent Predictions (last 50)\n\n"
    if not rows:
        return header + "_No predictions yet._\n\n"
    lines = [
        "| date | ticker | quarter | direction | conf | magnitude | expected | status | run_id |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        s = r.get("summary", {}) or {}
        lines.append(
            "| "
            + " | ".join([
                _fmt_date(r.get("started_at")),
                _fmt(r.get("ticker")),
                _fmt(r.get("quarter_label")),
                _fmt(s.get("direction")),
                _fmt(s.get("confidence_score")),
                _fmt(s.get("magnitude_bucket")),
                _fmt(s.get("expected_move_range_pct")),
                _fmt_status(r.get("status", "?")),
                _short_id(r.get("run_id")),
            ])
            + " |"
        )
    return header + "\n".join(lines) + "\n\n"


def _render_learners_section(rows: list[dict[str, Any]]) -> str:
    header = "## Recent Learners (last 50)\n\n"
    if not rows:
        return header + "_No learner runs yet._\n\n"
    lines = [
        "| date | ticker | quarter | direction_correct | actual_return | magnitude_error | primary_driver | status | run_id |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        s = r.get("summary", {}) or {}
        ar = s.get("actual_daily_stock_pct")
        actual_return = f"{ar:+.2f}%" if isinstance(ar, (int, float)) else _fmt(ar)
        mep = s.get("magnitude_error_pct")
        mag_err = f"{mep:.2f}pp" if isinstance(mep, (int, float)) else _fmt(mep)
        lines.append(
            "| "
            + " | ".join([
                _fmt_date(r.get("started_at")),
                _fmt(r.get("ticker")),
                _fmt(r.get("quarter_label")),
                _fmt(s.get("direction_correct")),
                actual_return,
                mag_err,
                _fmt(s.get("primary_driver_category")),
                _fmt_status(r.get("status", "?")),
                _short_id(r.get("run_id")),
            ])
            + " |"
        )
    return header + "\n".join(lines) + "\n\n"


def _render_extractions_section(rows: list[dict[str, Any]]) -> str:
    header = "## Recent Extractions (last 50)\n\n"
    if not rows:
        return header + "_No guidance extractions yet._\n\n"
    lines = [
        "| date | ticker | asset | source_id | items_extracted | items_written | enrichment | status | run_id |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        s = r.get("summary", {}) or {}
        lines.append(
            "| "
            + " | ".join([
                _fmt_date(r.get("started_at")),
                _fmt(r.get("ticker")),
                _fmt(r.get("source_asset")),
                _fmt(r.get("source_id")),
                _fmt(s.get("items_extracted")),
                _fmt(s.get("items_written")),
                _fmt(s.get("enrichment_status")),
                _fmt_status(r.get("status", "?")),
                _short_id(r.get("run_id")),
            ])
            + " |"
        )
    return header + "\n".join(lines) + "\n\n"


def refresh_index(
    *,
    ledger_path: Path | None = None,
    index_path: Path | None = None,
) -> None:
    """Regenerate the human-facing Run Index.md from the current ledger state.

    Atomic write (tmp + ``os.replace``). Crash during regeneration never
    leaves a half-written index.

    Called automatically by :func:`open_run` and :func:`close_run` so the
    "In Flight" section is always real-time.
    """
    src = ledger_path or LEDGER_PATH
    dst = index_path or INDEX_PATH
    state = current_state(ledger_path=src)

    # Partition state — "In Flight" is a disjoint view from the per-component
    # "Recent *" tables. A running row belongs ONLY in the In Flight section;
    # it must not double-appear in the per-component list, or the user sees
    # the same run_id in two places and the row-counts lie.
    running = [r for r in state if r.get("status") == "running"]
    predictions = [
        r for r in state
        if r.get("component") == "prediction" and r.get("status") != "running"
    ][:50]
    learners = [
        r for r in state
        if r.get("component") == "learning" and r.get("status") != "running"
    ][:50]
    extractions = [
        r for r in state
        if r.get("component") == "guidance" and r.get("status") != "running"
    ][:50]

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    parts = [
        "# Run Index\n",
        f"_Last regenerated: {now}_\n",
        "_Schema: run_ledger.v1. Ledger: "
        "`earnings-analysis/operations/run_ledger.jsonl`._\n\n",
        _render_in_flight_section(running),
        _render_predictions_section(predictions),
        _render_learners_section(learners),
        _render_extractions_section(extractions),
    ]
    content = "".join(parts)

    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, dst)


# ── CLI (optional convenience: `python -m run_ledger refresh`) ────────────

def _cli() -> int:
    import argparse
    p = argparse.ArgumentParser(description="Run ledger utility")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("refresh", help="Regenerate Run Index.md from the ledger")
    s = sub.add_parser("status", help="Print current state as JSON")
    s.add_argument("--component", default=None)
    s.add_argument("--status", default=None)
    s.add_argument("--limit", type=int, default=None)
    args = p.parse_args()

    if args.cmd == "refresh":
        refresh_index()
        print(f"Regenerated {INDEX_PATH}")
        return 0
    if args.cmd == "status":
        out = current_state(
            component=args.component, status=args.status, limit=args.limit,
        )
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(_cli())
