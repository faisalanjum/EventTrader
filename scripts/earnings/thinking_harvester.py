"""Thinking harvester — extracts reasoning transcripts from Claude Agent SDK sessions
into per-component ``thinking.md`` files + ``subagents/`` Data SubAgent traces
under ``earnings-analysis/Companies/{ticker}/events/{quarter}/{component}/``.

Handles three empirically-verified session patterns:

  - **EMBED-visible** (learner): rich visible thinking + Agent-spawned subagents
  - **EMBED-redacted** (guidance `/extract`): signed thinking blocks (empty
    content + ``signature`` key) + text fallback + Agent-spawned extraction subagents
  - **FORK** (predictor via `/earnings-prediction`): Skill tool_use in primary
    + 1 skill-fork JSONL which IS the thinking source (NO subagents/ dir emitted)

Linkage strategy: direct ``toolUseResult.agentId`` lookup (top-level on the
JSONL tool_result entry). Empirically 100% correct across real fixtures,
survives completion-order skew that would break positional matching.

Skill-fork detection: dual-signal.
  - Primary: subagent ``agent-<id>.meta.json`` has ``agentType == "general-purpose"``
  - Confirmation: subagent JSONL's first-user content starts with
    ``"Base directory for this skill:"``
  - WARNING logged on signal disagreement; harvest still proceeds.

Silent-fail semantics: any internal error is logged as WARNING; the caller
(orchestrator finalize_*_result) is never blocked.

Routing (per obsidian_thinking.md locked layout):
  - component call → ``events/{Q}/{thinking_type}/``
  - experiment call → ``events/{Q}/experiments/{experiment_name}/``
"""
from __future__ import annotations

import json
import logging
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# scripts/earnings is not a package — absolute sibling imports via sys.path.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
if str(_HERE.parents[1]) not in sys.path:  # repo root for config.*
    sys.path.insert(0, str(_HERE.parents[1]))

from config.pipeline_contracts import KNOWN_TYPES, validate_experiment_name
from thinking_blocks import parse_session_blocks

log = logging.getLogger(__name__)

HARVESTER_VERSION = "v1"

# Default SDK projects dir (where session JSONLs live)
_DEFAULT_PROJECTS_ROOT = Path.home() / ".claude" / "projects" / "-home-faisal-EventMarketDB"
# Default vault root — earnings-analysis/Companies/ (symlinked to Obsidian vault)
_DEFAULT_VAULT_ROOT = _HERE.parents[1] / "earnings-analysis" / "Companies"

_SKILL_FORK_FIRST_USER_PREFIX = "Base directory for this skill:"


# ── Primary public API ───────────────────────────────────────────────────

def harvest(
    *,
    thinking_type: str,
    ticker: str,
    quarter: str,
    session_id: str | None,
    experiment_name: str | None = None,
    vault_root: Path | None = None,
    projects_root: Path | None = None,
) -> None:
    """Harvest a session into vault markdown artifacts.

    Args:
        thinking_type: One of KNOWN_TYPES (``"guidance" | "prediction" | "learning"``).
        ticker: Upper-case ticker symbol (e.g., ``"BURL"``).
        quarter: Quarter label (e.g., ``"Q4_FY2025"``).
        session_id: SDK session ID (JSONL stem). If None/empty, logs WARNING and returns.
        experiment_name: Optional variant tag (e.g., ``"prediction_no_lessons"``); when
            provided, writes under ``experiments/{experiment_name}/`` and must begin
            with ``f"{thinking_type}_"`` (enforced via validate_experiment_name).
        vault_root: Where ``Companies/{ticker}/events/...`` lives. Defaults to
            the repo's ``earnings-analysis/Companies/`` symlink.
        projects_root: SDK projects dir. Defaults to
            ``~/.claude/projects/-home-faisal-EventMarketDB``.

    Side effects:
        Writes ``<component_dir>/thinking.md`` (+ ``<component_dir>/subagents/*.md``
        when Agent-spawned children exist). Idempotent — re-running overwrites
        thinking.md and clears + rewrites the subagents/ dir.

    Never raises — every internal error becomes a WARNING log line.
    """
    try:
        _harvest_inner(
            thinking_type=thinking_type,
            ticker=ticker,
            quarter=quarter,
            session_id=session_id,
            experiment_name=experiment_name,
            vault_root=vault_root or _DEFAULT_VAULT_ROOT,
            projects_root=projects_root or _DEFAULT_PROJECTS_ROOT,
        )
    except Exception as e:
        log.warning(
            "thinking_harvester: non-fatal error harvesting %s %s %s session=%s: %s",
            thinking_type, ticker, quarter, session_id, e, exc_info=True,
        )


def _harvest_inner(
    *,
    thinking_type: str,
    ticker: str,
    quarter: str,
    session_id: str | None,
    experiment_name: str | None,
    vault_root: Path,
    projects_root: Path,
) -> None:
    # Validate inputs
    if thinking_type not in KNOWN_TYPES:
        raise ValueError(
            f"unknown thinking_type {thinking_type!r}; must be one of {sorted(KNOWN_TYPES)}"
        )
    if experiment_name is not None:
        validate_experiment_name(thinking_type, experiment_name)
    if not session_id:
        log.warning(
            "thinking_harvester: missing session_id for %s %s %s — skipping harvest",
            thinking_type, ticker, quarter,
        )
        return

    # Locate primary session JSONL
    primary_jsonl = projects_root / f"{session_id}.jsonl"
    if not primary_jsonl.exists():
        log.warning(
            "thinking_harvester: primary session JSONL not found: %s — skipping",
            primary_jsonl,
        )
        return

    primary_blocks = parse_session_blocks(primary_jsonl)

    # Detect pattern by scanning tool_use blocks in primary
    has_skill = any(
        b["kind"] == "tool_use" and b["meta"].get("name") == "Skill"
        for b in primary_blocks
    )
    has_agent = any(
        b["kind"] == "tool_use" and b["meta"].get("name") == "Agent"
        for b in primary_blocks
    )
    has_redacted = any(b["kind"] == "thinking_redacted" for b in primary_blocks)

    if has_skill:
        session_pattern = "FORK"
    elif has_redacted:
        session_pattern = "EMBED-redacted"
    else:
        session_pattern = "EMBED-visible"

    # Build link map: tool_use_id → agentId (via tool_result entries in primary)
    linkage = _build_agent_linkage(primary_jsonl)

    # Destination directory
    component_dir = _destination_dir(
        vault_root, ticker, quarter, thinking_type, experiment_name,
    )

    # Gather subagent info
    agent_tool_uses = [
        b for b in primary_blocks
        if b["kind"] == "tool_use" and b["meta"].get("name") == "Agent"
    ]
    skill_tool_uses = [
        b for b in primary_blocks
        if b["kind"] == "tool_use" and b["meta"].get("name") == "Skill"
    ]

    # For FORK pattern, find the skill-fork JSONL (content source for thinking.md)
    skill_fork_jsonl: Path | None = None
    skill_fork_blocks: list[dict[str, Any]] = []
    if session_pattern == "FORK":
        for sb in skill_tool_uses:
            tu_id = sb["meta"].get("id", "")
            agent_id = linkage.get(tu_id)
            if not agent_id:
                continue
            candidate = projects_root / session_id / "subagents" / f"agent-{agent_id}.jsonl"
            if candidate.exists():
                # Detect via dual-signal
                if _is_skill_fork(candidate, context_label=f"{ticker} {quarter} {thinking_type}"):
                    skill_fork_jsonl = candidate
                    try:
                        skill_fork_blocks = parse_session_blocks(candidate)
                    except Exception as e:
                        log.warning(
                            "thinking_harvester: failed to parse skill-fork %s: %s",
                            candidate, e,
                        )
                    break

    # Assemble subagent outputs — Agent-spawned only (NOT skill-forks)
    subagent_outputs: list[tuple[str, str]] = []  # (filename, content)
    orphan_warnings: list[str] = []
    for au in agent_tool_uses:
        tu_id = au["meta"].get("id", "")
        agent_id = linkage.get(tu_id)
        subagent_type = au["meta"].get("input", {}).get("subagent_type", "unknown")
        if not agent_id:
            # Orphan — no matching tool_result
            orphan_warnings.append(
                f"Agent spawn with subagent_type={subagent_type} (tu_id={tu_id}) "
                f"had no tool_result — possible crash / rate-limit fast-fail; skipped."
            )
            continue
        sub_jsonl = projects_root / session_id / "subagents" / f"agent-{agent_id}.jsonl"
        sub_meta = projects_root / session_id / "subagents" / f"agent-{agent_id}.meta.json"
        # Prefer meta.json agentType when available (most localized)
        if sub_meta.exists():
            try:
                meta_data = json.loads(sub_meta.read_text())
                meta_type = meta_data.get("agentType")
                if meta_type and meta_type != "general-purpose":
                    subagent_type = meta_type
            except Exception:
                pass
        short_id = agent_id[:8]
        filename = f"{subagent_type}_{short_id}.md"
        subagent_outputs.append((filename, _render_subagent_trace(
            sub_jsonl=sub_jsonl,
            subagent_type=subagent_type,
            agent_id=agent_id,
            primary_subagent_type=au["meta"].get("input", {}).get("subagent_type", "unknown"),
        )))

    # ── Write outputs ─────────────────────────────────────────────────────
    component_dir.mkdir(parents=True, exist_ok=True)

    # Clear stale subagents/ before rewriting (idempotency)
    subagents_dir = component_dir / "subagents"
    if subagents_dir.exists():
        shutil.rmtree(subagents_dir)

    # Only materialize subagents/ for Agent-spawned children (NOT skill-fork)
    if subagent_outputs:
        subagents_dir.mkdir(parents=True)
        for filename, content in subagent_outputs:
            (subagents_dir / filename).write_text(content, encoding="utf-8")

    # Render thinking.md
    thinking_md = _render_thinking_md(
        thinking_type=thinking_type,
        ticker=ticker,
        quarter=quarter,
        session_id=session_id,
        session_pattern=session_pattern,
        experiment_name=experiment_name,
        primary_blocks=primary_blocks,
        skill_fork_blocks=skill_fork_blocks,
        orphan_warnings=orphan_warnings,
        subagents_count=len(subagent_outputs),
    )
    (component_dir / "thinking.md").write_text(thinking_md, encoding="utf-8")


# ── Helpers ───────────────────────────────────────────────────────────────

def _destination_dir(
    vault_root: Path, ticker: str, quarter: str,
    thinking_type: str, experiment_name: str | None,
) -> Path:
    base = vault_root / ticker / "events" / quarter
    if experiment_name is not None:
        return base / "experiments" / experiment_name
    return base / thinking_type


def _build_agent_linkage(primary_jsonl: Path) -> dict[str, str]:
    """Map tool_use_id → agentId by scanning primary JSONL for tool_result entries
    that carry a top-level ``toolUseResult.agentId``.

    Returns:
        Dict mapping each ``tool_use_id`` to its ``agentId`` (17-char hex string).
        If an Agent/Skill tool_use has no matching tool_result, it will be absent
        from this map (caller treats as orphan).
    """
    linkage: dict[str, str] = {}
    with open(primary_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            tur = entry.get("toolUseResult")
            if not isinstance(tur, dict):
                continue
            agent_id = tur.get("agentId")
            if not agent_id:
                continue
            # Find the tool_use_id — look in entry.message.content for a tool_result block
            msg = entry.get("message", {}) or {}
            content = msg.get("content", []) or []
            if not isinstance(content, list):
                continue
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    tu_id = block.get("tool_use_id")
                    if tu_id:
                        linkage[tu_id] = agent_id
    return linkage


def _is_skill_fork(sub_jsonl: Path, *, context_label: str) -> bool:
    """Dual-signal skill-fork detection.

    Signal A (primary, cheap): sibling ``<stem>.meta.json`` has
    ``agentType == "general-purpose"``.
    Signal B (confirmation): subagent JSONL's first ``user`` message content
    starts with ``"Base directory for this skill:"``.

    Returns:
        True if BOTH signals agree OR only signal A is available (meta exists
        but first-user is ambiguous). Returns False if neither signal fires.
        Logs a WARNING when the two signals DISAGREE (both present but opposite).
    """
    meta_path = sub_jsonl.with_suffix(".meta.json")
    signal_a: bool | None = None  # None = meta.json missing
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
            signal_a = (meta.get("agentType") == "general-purpose")
        except Exception as e:
            log.warning(
                "thinking_harvester: failed to read meta.json %s: %s",
                meta_path, e,
            )
            signal_a = None
    else:
        log.warning(
            "thinking_harvester: missing meta.json for %s — falling back to first-user scan (context: %s)",
            sub_jsonl.name, context_label,
        )

    # Signal B: first-user prefix scan
    signal_b = _first_user_matches_skill_prefix(sub_jsonl)

    if signal_a is None:
        return signal_b  # rely solely on fallback
    if signal_a and not signal_b:
        log.warning(
            "thinking_harvester: skill-fork signal MISMATCH for %s — "
            "meta.json=general-purpose but first-user does not start with %r "
            "(context: %s). Treating as skill-fork (meta.json wins); investigate SDK drift.",
            sub_jsonl.name, _SKILL_FORK_FIRST_USER_PREFIX, context_label,
        )
        return True
    if signal_b and not signal_a:
        log.warning(
            "thinking_harvester: skill-fork signal MISMATCH for %s — "
            "first-user matches but meta.json agentType != general-purpose "
            "(context: %s). Treating as skill-fork (first-user wins).",
            sub_jsonl.name, context_label,
        )
        return True
    return signal_a and signal_b


def _first_user_matches_skill_prefix(sub_jsonl: Path) -> bool:
    try:
        with open(sub_jsonl, "r", encoding="utf-8") as f:
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
                content = entry.get("message", {}).get("content", "")
                if isinstance(content, str):
                    return content.startswith(_SKILL_FORK_FIRST_USER_PREFIX)
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            return str(item.get("text", "")).startswith(_SKILL_FORK_FIRST_USER_PREFIX)
                        if isinstance(item, str):
                            return item.startswith(_SKILL_FORK_FIRST_USER_PREFIX)
                return False  # first user message encountered, no match
    except Exception:
        return False
    return False


# ── thinking.md composition ───────────────────────────────────────────────

_READONLY_MARKER = """<!--
⚠ AUTOGENERATED FROM SDK session transcripts — DO NOT EDIT MANUALLY
Any manual edits will be overwritten on the next harvest or finalize_*_result() run.
To change content, adjust the source session or the harvester at
scripts/earnings/thinking_harvester.py.
-->"""


def _yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "" or any(c in text for c in ":#&*!|>%@`\n") or text.strip() != text:
        return json.dumps(text, ensure_ascii=False)
    return text


_TOOL_EMOJI = {
    "Bash": "🔨",
    "Read": "📖",
    "Write": "✏️",
    "Edit": "✏️",
    "Glob": "🔎",
    "Grep": "🔎",
    "Agent": "🤖",
    "Skill": "🔩",
}


def _tool_use_annotation(block: dict[str, Any]) -> str:
    name = block["meta"].get("name", "unknown")
    inp = block["meta"].get("input", {}) or {}
    emoji = _TOOL_EMOJI.get(name, "🔧")
    if name == "Bash":
        desc = inp.get("description") or (inp.get("command", "") or "")[:60]
        return f"{emoji} Bash({desc})"
    if name in ("Read", "Write", "Edit"):
        fp = inp.get("file_path", "") or ""
        base = Path(fp).name if fp else "?"
        return f"{emoji} {name}({base})"
    if name in ("Glob", "Grep"):
        pattern = inp.get("pattern", "") or ""
        return f"{emoji} {name}({pattern})"
    if name == "Agent":
        sub = inp.get("subagent_type", "?")
        return f"{emoji} Agent({sub})"
    if name == "Skill":
        skill = inp.get("skill", "?")
        return f"{emoji} Skill({skill})"
    if name.startswith("mcp__neo4j-cypher__"):
        return "🗃  Cypher(read)" if "read" in name else "🗃  Cypher(write)"
    return f"🔧 {name}"


def _render_thinking_md(
    *,
    thinking_type: str,
    ticker: str,
    quarter: str,
    session_id: str,
    session_pattern: str,
    experiment_name: str | None,
    primary_blocks: list[dict[str, Any]],
    skill_fork_blocks: list[dict[str, Any]],
    orphan_warnings: list[str],
    subagents_count: int,
) -> str:
    # Metrics — combine primary + skill_fork where applicable
    if session_pattern == "FORK" and skill_fork_blocks:
        # Primary's meta-thinking + skill-fork's text/thinking
        content_blocks = primary_blocks + skill_fork_blocks
    else:
        content_blocks = primary_blocks

    thinking_total = sum(
        len(b["content"]) for b in content_blocks if b["kind"] == "thinking"
    )
    thinking_block_count = sum(1 for b in content_blocks if b["kind"] == "thinking")
    redacted_block_count = sum(1 for b in primary_blocks if b["kind"] == "thinking_redacted")
    generated_at = datetime.now(timezone.utc).isoformat()

    # Frontmatter
    fm = ["---"]
    fm.append("autogenerated: true")
    fm.append(f"source: SDK session transcript")
    fm.append(f"generator: scripts/earnings/thinking_harvester.py")
    fm.append(f"component: {_yaml_scalar(thinking_type)}")
    if experiment_name is not None:
        fm.append(f"experiment_name: {_yaml_scalar(experiment_name)}")
    fm.append(f"ticker: {_yaml_scalar(ticker)}")
    fm.append(f"quarter: {_yaml_scalar(quarter)}")
    fm.append(f"sdk_session_id: {_yaml_scalar(session_id)}")
    fm.append(f"session_pattern: {session_pattern}")
    fm.append(f"thinking_blocks: {thinking_block_count}")
    fm.append(f"thinking_chars: {thinking_total}")
    fm.append(f"redacted_thinking_blocks: {redacted_block_count}")
    fm.append(f"subagents_count: {subagents_count}")
    fm.append(f"generated_at: {_yaml_scalar(generated_at)}")
    fm.append(f"harvester_version: {HARVESTER_VERSION}")
    fm.append("---")

    # Body
    body = []
    body.append("")
    body.append(_READONLY_MARKER)
    body.append("")
    label_context = f"{ticker} {quarter}"
    if experiment_name:
        body.append(f"# Thinking — {thinking_type} / {experiment_name} — {label_context}")
    else:
        body.append(f"# Thinking — {thinking_type} — {label_context}")
    body.append("")
    body.append(f"Session pattern: **{session_pattern}**. "
                f"Primary thinking: {thinking_block_count} blocks, "
                f"{thinking_total:,} chars. "
                f"Redacted: {redacted_block_count}. "
                f"Data subagents: {subagents_count}.")
    body.append("")

    if orphan_warnings:
        body.append("## ⚠ Orphan Agent spawns (no tool_result)")
        body.append("")
        for w in orphan_warnings:
            body.append(f"- {w}")
        body.append("")

    # Primary reasoning content (thinking + text), merged in timestamp order
    body.append("## Primary session reasoning")
    body.append("")
    _append_reasoning_blocks(body, primary_blocks)
    body.append("")

    if session_pattern == "FORK" and skill_fork_blocks:
        body.append("## Skill-fork reasoning (predictor sub-session)")
        body.append("")
        _append_reasoning_blocks(body, skill_fork_blocks)
        body.append("")

    if redacted_block_count:
        body.append(f"_Note: {redacted_block_count} thinking block(s) were **content redacted (signed)** "
                    f"— Claude cryptographically-signed reasoning, recoverable server-side only._")
        body.append("")

    return "\n".join(fm + body) + "\n"


def _append_reasoning_blocks(lines: list[str], blocks: list[dict[str, Any]]) -> None:
    for b in blocks:
        kind = b["kind"]
        if kind == "thinking":
            text = b["content"].strip()
            if not text:
                continue
            lines.append(f"### 💭 Thinking ({len(b['content']):,} chars)")
            lines.append("")
            lines.append(text)
            lines.append("")
        elif kind == "text":
            text = b["content"].strip()
            if not text:
                continue
            lines.append(f"### 📝 Text ({len(b['content']):,} chars)")
            lines.append("")
            lines.append(text)
            lines.append("")
        elif kind == "tool_use":
            lines.append(f"- {_tool_use_annotation(b)}")
        elif kind == "thinking_redacted":
            lines.append("- 🔒 _(thinking block — content redacted (signed))_")


def _render_subagent_trace(
    *,
    sub_jsonl: Path,
    subagent_type: str,
    agent_id: str,
    primary_subagent_type: str,
) -> str:
    """Render one Agent-spawned subagent's execution trace to markdown.

    Data SubAgents typically produce 0 thinking blocks — the trace is
    prompt + tool_use + tool_result + any text output.
    """
    if not sub_jsonl.exists():
        return (
            f"---\n"
            f"component: subagent_trace\n"
            f"subagent_type: {_yaml_scalar(subagent_type)}\n"
            f"agent_id: {_yaml_scalar(agent_id)}\n"
            f"missing_jsonl: true\n"
            f"---\n\n"
            f"⚠ Subagent JSONL not found at `{sub_jsonl}`.\n"
        )
    try:
        blocks = parse_session_blocks(sub_jsonl)
    except Exception as e:
        return (
            f"---\n"
            f"component: subagent_trace\n"
            f"subagent_type: {_yaml_scalar(subagent_type)}\n"
            f"agent_id: {_yaml_scalar(agent_id)}\n"
            f"parse_error: {_yaml_scalar(str(e))}\n"
            f"---\n\n"
            f"⚠ Failed to parse subagent JSONL: {e}\n"
        )

    # Metrics
    text_chars = sum(len(b["content"]) for b in blocks if b["kind"] == "text")
    tool_use_count = sum(1 for b in blocks if b["kind"] == "tool_use")

    lines = ["---"]
    lines.append("autogenerated: true")
    lines.append(f"source: SDK subagent transcript")
    lines.append(f"generator: scripts/earnings/thinking_harvester.py")
    lines.append("component: subagent_trace")
    lines.append(f"subagent_type: {_yaml_scalar(subagent_type)}")
    lines.append(f"primary_input_subagent_type: {_yaml_scalar(primary_subagent_type)}")
    lines.append(f"agent_id: {_yaml_scalar(agent_id)}")
    lines.append(f"agent_id_short: {_yaml_scalar(agent_id[:8])}")
    lines.append(f"text_chars: {text_chars}")
    lines.append(f"tool_use_count: {tool_use_count}")
    lines.append(f"harvester_version: {HARVESTER_VERSION}")
    lines.append("---")
    lines.append("")
    lines.append(_READONLY_MARKER)
    lines.append("")
    lines.append(f"# Subagent trace — {subagent_type} ({agent_id[:8]})")
    lines.append("")

    # First-user prompt (if string)
    first_user_content = ""
    for b in blocks:
        # parse_session_blocks ignores string-form user messages; read first line manually.
        pass
    try:
        with open(sub_jsonl, "r", encoding="utf-8") as f:
            for raw in f:
                entry = json.loads(raw)
                if entry.get("type") == "user":
                    c = entry.get("message", {}).get("content", "")
                    if isinstance(c, str):
                        first_user_content = c
                    elif isinstance(c, list):
                        for item in c:
                            if isinstance(item, dict) and item.get("type") == "text":
                                first_user_content = str(item.get("text", ""))
                                break
                    break
    except Exception:
        pass
    if first_user_content:
        lines.append("## Prompt")
        lines.append("")
        lines.append(first_user_content[:4000])
        if len(first_user_content) > 4000:
            lines.append(f"\n*[truncated — {len(first_user_content)-4000:,} more chars]*")
        lines.append("")

    # Ordered transcript
    lines.append("## Transcript")
    lines.append("")
    for b in blocks:
        kind = b["kind"]
        if kind == "text":
            text = b["content"].strip()
            if text:
                lines.append(f"### 📝 Text ({len(b['content']):,} chars)")
                lines.append("")
                lines.append(text[:4000])
                lines.append("")
        elif kind == "tool_use":
            lines.append(f"- {_tool_use_annotation(b)}")
        elif kind == "tool_result":
            preview = b["content"][:300]
            lines.append(f"  ↳ _result:_ {preview}" + (" …" if len(b["content"]) > 300 else ""))
        elif kind == "thinking":
            text = b["content"].strip()
            if text:
                lines.append(f"### 💭 Thinking ({len(b['content']):,} chars)")
                lines.append("")
                lines.append(text[:4000])
                lines.append("")

    return "\n".join(lines) + "\n"


# ── CLI ──────────────────────────────────────────────────────────────────

def _cli(argv: list[str]) -> int:
    import argparse
    p = argparse.ArgumentParser(description="Harvest SDK session into vault thinking.md + subagents/")
    p.add_argument("thinking_type", choices=sorted(KNOWN_TYPES))
    p.add_argument("ticker")
    p.add_argument("quarter")
    p.add_argument("session_id")
    p.add_argument("--experiment-name", default=None)
    p.add_argument("--vault-root", default=None)
    p.add_argument("--projects-root", default=None)
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    harvest(
        thinking_type=args.thinking_type,
        ticker=args.ticker,
        quarter=args.quarter,
        session_id=args.session_id,
        experiment_name=args.experiment_name,
        vault_root=Path(args.vault_root) if args.vault_root else None,
        projects_root=Path(args.projects_root) if args.projects_root else None,
    )
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
