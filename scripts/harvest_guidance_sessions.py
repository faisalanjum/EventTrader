#!/usr/bin/env python3
"""External post-hoc guidance thinking harvester.

A small standalone tool that watches / scans Claude Agent SDK session JSONLs
and invokes ``thinking_harvester.harvest()`` for completed ``/extract ...
TYPE=guidance`` sessions — all without touching the K8s extraction-worker,
trigger, or daemon.

Design rationale: 100% isolation from the guidance extraction pipeline.
The extraction-worker pod writes SDK session JSONLs to
``~/.claude/projects/-home-faisal-EventMarketDB/`` as a side-effect of
every SDK ``query()`` call. This tool simply reads those JSONLs post-hoc.

Modes (selected by CLI flag):
  --watch            long-running inotify watcher (requires ``watchdog``;
                     lazy-imported at call time so --scan/--one remain
                     dependency-free).
  --scan             one-shot reconciliation sweep over recent JSONLs
                     (``--since-hours N``). Intended for cron.
  --one SESSION_ID   manual harvest of a single session.

Reliability features:
  - Idempotent: existing ``events/{Q}/guidance/thinking_{asset}.md`` with
    same ``sdk_session_id`` in frontmatter ⇒ skip.
  - Completion gate: only harvests sessions whose JSONL tail shows a clean
    ``stop_reason=='end_turn'`` or ``type=='last-prompt'`` marker.
  - Semantic filter: only processes sessions whose first user message is
    a ``/extract ... TYPE=guidance`` slash command.
  - Silent-fail: per-session errors are logged, never propagated.
  - Reconciliation cron backs up the watcher (handles missed events /
    restart gaps).
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

# Repo layout — this script lives at scripts/harvest_guidance_sessions.py
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS_EARNINGS = _REPO_ROOT / "scripts" / "earnings"
_SKILL_SCRIPTS = _REPO_ROOT / ".claude" / "skills" / "earnings-orchestrator" / "scripts"

# sys.path setup for sibling imports (scripts/earnings/ has no __init__.py)
for _p in (_REPO_ROOT, _SCRIPTS_EARNINGS, _SKILL_SCRIPTS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

log = logging.getLogger("harvest_guidance_sessions")

# Defaults
DEFAULT_PROJECTS_ROOT = Path.home() / ".claude" / "projects" / "-home-faisal-EventMarketDB"
DEFAULT_VAULT_ROOT = _REPO_ROOT / "earnings-analysis" / "Companies"

# Valid guidance asset values (matches trigger-extract.py's ASSET_QUERIES).
_VALID_ASSETS: frozenset[str] = frozenset(
    {"8k", "10q", "10k", "transcript", "news"}
)

# Slash-command parsing (both K8s worker + interactive CLI invocations
# produce this shape per empirical verification 2026-04-17).
_COMMAND_NAME_RE = re.compile(r"<command-name>/extract</command-name>")
_COMMAND_ARGS_RE = re.compile(r"<command-args>(.+?)</command-args>", re.DOTALL)
_TYPE_RE = re.compile(r"\bTYPE=([A-Za-z_]+)")
_MODE_RE = re.compile(r"\bMODE=([A-Za-z_]+)")
_TICKER_RE = re.compile(r"^[A-Z]{1,5}$")


def parse_first_user_guidance(jsonl_path: Path) -> dict[str, str] | None:
    """Parse a session JSONL's first user message.

    Returns a dict ``{ticker, asset, source_id, mode}`` iff the session is
    a ``/extract ... TYPE=guidance`` slash command. None otherwise.

    Handles:
      - Both string-shaped and list-shaped ``message.content`` payloads.
      - Malformed JSON lines are skipped.
      - Non-user prefix entries (queue-operation, attachment) are skipped.
    """
    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("type") != "user":
                    continue
                content = (entry.get("message") or {}).get("content", "")
                text = _content_to_text(content)
                if not text:
                    return None
                return _parse_extract_guidance_text(text)
    except (FileNotFoundError, OSError):
        return None
    return None


def _content_to_text(content: Any) -> str:
    """Normalize message.content (str or list[{type:text,text:...}]) to a single string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    return ""


def _parse_extract_guidance_text(text: str) -> dict[str, str] | None:
    """Extract (ticker, asset, source_id, mode) from a first-user text payload.

    Expects either:
      - ``<command-name>/extract</command-name>`` + ``<command-args>...``
      - A direct ``/extract TICKER ASSET SOURCE_ID TYPE=guidance ...`` prompt
    """
    # Primary shape: <command-args>
    m_args = _COMMAND_ARGS_RE.search(text)
    if m_args and _COMMAND_NAME_RE.search(text):
        args = m_args.group(1).strip()
    else:
        # Fallback: look for a "/extract ..." prefix line
        args = None
        for ln in text.splitlines():
            if ln.startswith("/extract "):
                args = ln[len("/extract "):].strip()
                break
        if args is None:
            return None

    # Type filter — must be guidance
    m_type = _TYPE_RE.search(args)
    if not m_type or m_type.group(1) != "guidance":
        return None

    # First 3 positional tokens must be TICKER ASSET SOURCE_ID
    tokens = args.split()
    if len(tokens) < 3:
        return None
    ticker, asset, source_id = tokens[0], tokens[1], tokens[2]
    if not _TICKER_RE.match(ticker):
        return None
    if asset not in _VALID_ASSETS:
        return None
    if not source_id:
        return None

    # Mode (optional, default "write")
    m_mode = _MODE_RE.search(args)
    mode = m_mode.group(1) if m_mode else "write"

    return {
        "ticker": ticker,
        "asset": asset,
        "source_id": source_id,
        "mode": mode,
    }


# ── Completion gate ───────────────────────────────────────────────────────

def is_session_complete(jsonl_path: Path, tail_lines: int = 10) -> bool:
    """Return True iff the session JSONL looks like a cleanly-ended session.

    Empirically verified 2026-04-17 against real sessions: the tail always
    contains either a ``type=='last-prompt'`` terminal marker OR an assistant
    message whose ``message.stop_reason == 'end_turn'``. Either signal is
    sufficient — we check the last ``tail_lines`` entries.

    Returns False for:
      - File not found
      - Partial session (no terminal marker in tail)
      - Any malformed / unreadable JSONL
    """
    if not Path(jsonl_path).exists():
        return False
    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return False
    # Reverse-walk last `tail_lines` lines to find the terminal signal
    for raw in reversed(lines[-tail_lines:]):
        raw = raw.strip()
        if not raw:
            continue
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if entry.get("type") == "last-prompt":
            return True
        if entry.get("type") == "assistant":
            msg = entry.get("message") or {}
            if isinstance(msg, dict) and msg.get("stop_reason") == "end_turn":
                return True
    return False


# ── Idempotency check (path-based via frontmatter) ────────────────────────

# Parse ``sdk_session_id: <value>`` from the frontmatter block of a result.md.
# YAML scalar per our renderer may be plain (``abc-123``) or quoted (``"abc-123"``).
_FRONTMATTER_SID_RE = re.compile(
    r"^sdk_session_id:\s*\"?([^\"\n]+?)\"?\s*$",
    re.MULTILINE,
)


def is_already_harvested(
    vault_root: Path,
    ticker: str,
    quarter: str,
    source_asset: str,
    session_id: str,
) -> bool:
    """Return True iff the target ``thinking_{source_asset}.md`` already
    contains this exact ``sdk_session_id`` in its frontmatter.

    Provides idempotency for watcher + reconciliation: re-running for the same
    session is a no-op. A DIFFERENT session_id on the same target file is
    treated as "not yet harvested from this session" → harvest proceeds
    (overwrites the older harvest).
    """
    target = (
        Path(vault_root) / ticker / "events" / quarter / "guidance"
        / f"thinking_{source_asset}.md"
    )
    if not target.exists():
        return False
    try:
        content = target.read_text(encoding="utf-8")
    except OSError:
        return False
    m = _FRONTMATTER_SID_RE.search(content)
    if not m:
        return False
    return m.group(1).strip() == session_id.strip()


# ── Quarter-label derivation for guidance (asset-aware) ───────────────────

def _normalize_fq_fy(fq_raw: Any, fy_raw: Any) -> str | None:
    """Normalize Neo4j fiscal_quarter/fiscal_year into 'Q{n}_FY{YYYY}'.

    Handles the storage quirks verified 2026-04-17:
      - fiscal_quarter stored as string '1'..'4' (sometimes 'Q1'..'Q4', int)
      - fiscal_year stored as string with comma thousands ('2,023')
    """
    if fq_raw is None or fy_raw is None:
        return None
    fq_str = str(fq_raw).strip().upper()
    if not fq_str.startswith("Q"):
        fq_str = f"Q{fq_str}"
    fy_str = str(fy_raw).replace(",", "").strip()
    if not (fy_str.isdigit() and len(fy_str) == 4):
        return None
    return f"{fq_str}_FY{fy_str}"


def derive_quarter_label_for_guidance(
    mgr, asset: str, source_id: str
) -> str | None:
    """Map (asset, source_id) → quarter_label ('Q4_FY2025') via Neo4j.

    Per-asset strategy (verified against real data shapes 2026-04-17):
      - ``8k``: Report.fiscal_quarter/fiscal_year are typically NULL. Derive
        via ``resolve_quarter_info(ticker, accession)`` which uses
        periodOfReport + XBRL fallback.
      - ``10q`` / ``10k``: Report.fiscal_quarter/fiscal_year are usually
        populated by the XBRL-aware ingestion path. Read directly.
      - ``transcript``: Transcript.fiscal_quarter/fiscal_year populated.
        Direct read.
      - ``news``: cross-cutting; return None (raw capture in pipeline/extractions/).

    Returns None (harvest skipped gracefully) on any failure — mgr=None,
    missing source, unrecognized asset, Neo4j exception, or malformed fields.
    """
    if mgr is None:
        log.info("Quarter derivation skipped: Neo4j manager is None")
        return None
    if asset == "news":
        return None
    try:
        if asset == "8k":
            rows = mgr.execute_cypher_query_all(
                "MATCH (r:Report {id: $sid})-[:PRIMARY_FILER]->(c:Company) "
                "RETURN c.ticker AS ticker",
                {"sid": source_id},
            )
            if not rows or not rows[0].get("ticker"):
                return None
            ticker = rows[0]["ticker"]
            from quarter_identity import resolve_quarter_info  # lazy import
            qi = resolve_quarter_info(ticker, source_id)
            return qi.get("quarter_label")

        if asset in ("10q", "10k"):
            rows = mgr.execute_cypher_query_all(
                "MATCH (r:Report {id: $sid}) "
                "RETURN r.fiscal_quarter AS fq, r.fiscal_year AS fy",
                {"sid": source_id},
            )
            if not rows:
                return None
            return _normalize_fq_fy(rows[0].get("fq"), rows[0].get("fy"))

        if asset == "transcript":
            rows = mgr.execute_cypher_query_all(
                "MATCH (t:Transcript {id: $sid}) "
                "RETURN t.fiscal_quarter AS fq, t.fiscal_year AS fy",
                {"sid": source_id},
            )
            if not rows:
                return None
            return _normalize_fq_fy(rows[0].get("fq"), rows[0].get("fy"))

        return None  # unrecognized asset
    except Exception as e:
        log.debug("Quarter derivation failed for %s/%s: %s", asset, source_id, e)
        return None


# ── Single-session orchestration ──────────────────────────────────────────

def _harvest_impl(**kwargs) -> None:
    """Shim around thinking_harvester.harvest — indirection point for tests."""
    from thinking_harvester import harvest as _harvest
    _harvest(**kwargs)


def harvest_one_session(
    *,
    jsonl_path: Path,
    vault_root: Path,
    projects_root: Path,
    mgr,
) -> str:
    """Orchestrate harvest for a single session JSONL.

    Returns a status string describing the outcome:
      - ``"harvested"`` — harvest was invoked
      - ``"skipped_incomplete"`` — session JSONL doesn't show completion yet
      - ``"skipped_not_guidance"`` — first user message is not /extract guidance
      - ``"skipped_no_quarter"`` — quarter derivation returned None
      - ``"skipped_already_harvested"`` — target file already carries this sdk_session_id
      - ``"error"`` — any exception (logged, swallowed)
    """
    jsonl_path = Path(jsonl_path)
    session_id = jsonl_path.stem
    try:
        # 1. Completion gate
        if not is_session_complete(jsonl_path):
            log.info("Skip %s — session not complete", session_id)
            return "skipped_incomplete"

        # 2. Semantic filter
        meta = parse_first_user_guidance(jsonl_path)
        if meta is None:
            log.debug("Skip %s — not a /extract guidance session", session_id)
            return "skipped_not_guidance"

        ticker = meta["ticker"]
        asset = meta["asset"]
        source_id = meta["source_id"]

        # 3. Quarter derivation
        quarter = derive_quarter_label_for_guidance(mgr, asset, source_id)
        if not quarter:
            log.info(
                "Skip %s — quarter not derivable for %s/%s/%s",
                session_id, ticker, asset, source_id,
            )
            return "skipped_no_quarter"

        # 4. Idempotency
        if is_already_harvested(vault_root, ticker, quarter, asset, session_id):
            log.info(
                "Skip %s — already harvested (thinking_%s.md has this sdk_session_id)",
                session_id, asset,
            )
            return "skipped_already_harvested"

        # 5. Invoke harvester
        _harvest_impl(
            thinking_type="guidance",
            ticker=ticker,
            quarter=quarter,
            session_id=session_id,
            source_asset=asset,
            source_id=source_id,
            vault_root=vault_root,
            projects_root=projects_root,
        )
        log.info(
            "Harvested %s — %s/%s %s/%s",
            session_id, ticker, quarter, asset, source_id,
        )
        return "harvested"
    except Exception as e:
        log.warning("Harvest failed for %s: %s", session_id, e, exc_info=True)
        return "error"


# ── CLI commands ──────────────────────────────────────────────────────────

def _get_neo4j_manager_best_effort():
    """Return a Neo4jManager or None. Never raises."""
    try:
        from dotenv import load_dotenv
        load_dotenv(_REPO_ROOT / ".env", override=True)
        from neograph.Neo4jConnection import get_manager
        mgr = get_manager()
        # Smoke-test connectivity
        mgr.execute_cypher_query_all("RETURN 1 AS ok", {})
        return mgr
    except Exception as e:
        log.warning("Neo4j unavailable (mgr=None): %s", e)
        return None


def cmd_scan(args: argparse.Namespace) -> int:
    """--scan: one-shot reconciliation over recent top-level JSONLs."""
    projects_root = Path(args.projects_root)
    vault_root = Path(args.vault_root)
    since_seconds = float(args.since_hours) * 3600.0
    cutoff = time.time() - since_seconds

    if not projects_root.is_dir():
        log.error("projects_root does not exist: %s", projects_root)
        return 1

    mgr = _get_neo4j_manager_best_effort()

    # Iterate TOP-LEVEL *.jsonl only (non-recursive) — subagent JSONLs at
    # {session}/subagents/agent-*.jsonl must NOT be treated as top-level
    # sessions.
    counts = {"harvested": 0, "skipped_incomplete": 0, "skipped_not_guidance": 0,
              "skipped_no_quarter": 0, "skipped_already_harvested": 0, "error": 0}
    scanned = 0
    for path in sorted(projects_root.glob("*.jsonl")):
        if not path.is_file():
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if mtime < cutoff:
            continue
        scanned += 1
        status = harvest_one_session(
            jsonl_path=path,
            vault_root=vault_root,
            projects_root=projects_root,
            mgr=mgr,
        )
        counts[status] = counts.get(status, 0) + 1

    log.info(
        "Scan complete: %d JSONL(s) visited in last %.1fh — %s",
        scanned, args.since_hours,
        ", ".join(f"{k}={v}" for k, v in counts.items() if v),
    )
    return 0


def cmd_one(args: argparse.Namespace) -> int:
    """--one SESSION_ID: manually harvest a specific session by id."""
    projects_root = Path(args.projects_root)
    vault_root = Path(args.vault_root)
    session_id = args.session_id

    jsonl_path = projects_root / f"{session_id}.jsonl"
    if not jsonl_path.exists():
        print(
            f"ERROR: session JSONL not found: {jsonl_path}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    mgr = _get_neo4j_manager_best_effort()
    status = harvest_one_session(
        jsonl_path=jsonl_path,
        vault_root=vault_root,
        projects_root=projects_root,
        mgr=mgr,
    )
    log.info("harvest_one_session status: %s", status)
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    """--watch: long-running event-driven watcher (requires ``watchdog``).

    Lazy-imports watchdog so --scan and --one remain dependency-free.
    Exits with code 2 + clear message if watchdog is missing.
    """
    try:
        from watchdog.observers import Observer  # noqa: F401
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        print(
            "ERROR: --watch mode requires the 'watchdog' Python package.\n"
            "Install: /home/faisal/EventMarketDB/venv/bin/pip install watchdog\n"
            "Alternative: use --scan on a periodic cron schedule instead.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    projects_root = Path(args.projects_root)
    vault_root = Path(args.vault_root)
    debounce = float(args.debounce_seconds)
    if not projects_root.is_dir():
        log.error("projects_root does not exist: %s", projects_root)
        return 1

    mgr = _get_neo4j_manager_best_effort()

    # Track pending JSONLs (debounce on last-modified time)
    pending: dict[Path, float] = {}

    class _Handler(FileSystemEventHandler):  # type: ignore[misc]
        def _on_event(self, event_path: str) -> None:
            p = Path(event_path)
            # Only top-level *.jsonl in projects_root
            if p.parent != projects_root:
                return
            if p.suffix != ".jsonl":
                return
            pending[p] = time.time()

        def on_created(self, event):
            if not event.is_directory:
                self._on_event(event.src_path)

        def on_modified(self, event):
            if not event.is_directory:
                self._on_event(event.src_path)

    # Scan existing on startup so we don't miss sessions completed before boot
    log.info("Watcher starting — initial reconciliation scan of last 2h")
    cmd_scan(argparse.Namespace(
        since_hours=2.0,
        projects_root=projects_root,
        vault_root=vault_root,
    ))

    from watchdog.observers import Observer
    observer = Observer()
    observer.schedule(_Handler(), str(projects_root), recursive=False)
    observer.start()
    log.info("Watching %s (debounce=%.1fs)", projects_root, debounce)
    try:
        while True:
            time.sleep(max(1.0, debounce / 2.0))
            now = time.time()
            ready = [p for p, t in pending.items() if (now - t) >= debounce]
            for p in ready:
                pending.pop(p, None)
                status = harvest_one_session(
                    jsonl_path=p, vault_root=vault_root,
                    projects_root=projects_root, mgr=mgr,
                )
                log.info("  event → %s: %s", p.name, status)
    except KeyboardInterrupt:
        log.info("Watcher stopping (SIGINT)")
    finally:
        observer.stop()
        observer.join()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0] if __doc__ else None,
    )
    parser.add_argument(
        "--projects-root",
        default=str(DEFAULT_PROJECTS_ROOT),
        help=f"SDK projects directory (default: {DEFAULT_PROJECTS_ROOT})",
    )
    parser.add_argument(
        "--vault-root",
        default=str(DEFAULT_VAULT_ROOT),
        help=f"Vault Companies/ root (default: {DEFAULT_VAULT_ROOT})",
    )

    subs = parser.add_subparsers(dest="mode", required=True)

    s_scan = subs.add_parser("scan", help="One-shot reconciliation over recent JSONLs")
    s_scan.add_argument("--since-hours", type=float, default=2.0,
                        help="Scan JSONLs modified in last N hours (default: 2)")

    s_one = subs.add_parser("one", help="Manually harvest one session")
    s_one.add_argument("session_id")

    s_watch = subs.add_parser("watch", help="Event-driven watcher (requires watchdog)")
    s_watch.add_argument("--debounce-seconds", type=float, default=15.0,
                         help="Wait N seconds of no writes before harvesting (default: 15)")

    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if args.mode == "scan":
        return cmd_scan(args)
    if args.mode == "one":
        return cmd_one(args)
    if args.mode == "watch":
        return cmd_watch(args)
    parser.error(f"unknown mode: {args.mode!r}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
