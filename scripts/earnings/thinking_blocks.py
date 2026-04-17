"""Shared block parser for Claude Agent SDK JSONL transcripts.

Single code path for ``.claude/hooks/obsidian_capture.py`` and
``scripts/earnings/thinking_harvester.py``. Parses an SDK transcript
JSONL into a timestamp-ordered list of ``Block`` dicts.

Block shape (every dict has these four keys)::

    {
        "kind":   "thinking" | "thinking_redacted" | "text" | "tool_use" | "tool_result",
        "ts":     "2026-04-17T12:34:56.789Z" or "",
        "content": str,                    # main textual payload (empty for redacted + tool calls)
        "meta":   {...},                   # kind-specific extras (tool name, tool_use_id, signature flag, etc.)
    }

Redacted thinking detection: a block with ``type == "thinking"`` AND
empty ``thinking`` string AND a ``signature`` key maps to
``kind == "thinking_redacted"`` with ``content == ""`` and
``meta["signature"] = True``. This is NOT a distinct Anthropic block
type — it's a regular thinking block whose content has been
cryptographically signed + stripped by the SDK (per obsidian_thinking.md
§"redacted thinking").

Malformed JSONL lines are skipped silently (never crash the caller).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# Block kinds (informational — not enforced at module boundary, but
# documented as the canonical set).
BlockKind = str  # Literal["thinking","thinking_redacted","text","tool_use","tool_result"]


def parse_session_blocks(
    jsonl_path: Path,
    *,
    preserve_file_order: bool = False,
) -> list[dict[str, Any]]:
    """Parse a Claude Agent SDK session JSONL into an ordered list of Blocks.

    Args:
        jsonl_path: Path to the session .jsonl file (primary OR subagent).
        preserve_file_order: When True, return blocks in strict JSONL file
            order (skipping the default timestamp sort). Required by
            ``.claude/hooks/obsidian_capture.py`` (via the adapter) because
            its legacy tool_use↔tool_result pairing relies on encountering
            tool_use BEFORE tool_result in file order. Harvester callers keep
            the default (timestamp-sorted) because they need deterministic
            time order, not SDK-write order.

    Returns:
        List of Block dicts. Order depends on ``preserve_file_order``:
            - False (default): ordered by timestamp (stable within ties).
            - True: ordered by JSONL line position, then by within-entry
              block position.
        Malformed lines are skipped.

    Raises:
        FileNotFoundError: If the path does not exist.
    """
    if not Path(jsonl_path).exists():
        raise FileNotFoundError(f"session JSONL not found: {jsonl_path}")

    blocks: list[dict[str, Any]] = []

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                # Malformed line — skip silently (matches obsidian_capture.py behaviour).
                continue

            entry_type = entry.get("type")
            ts = entry.get("timestamp", "") or ""

            if entry_type == "assistant":
                msg = entry.get("message", {}) or {}
                content = msg.get("content", [])
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    btype = block.get("type")

                    if btype == "thinking":
                        text = block.get("thinking", "") or ""
                        if not text and "signature" in block:
                            # Redacted — empty content + signature key
                            blocks.append({
                                "kind": "thinking_redacted",
                                "ts": ts,
                                "content": "",
                                "meta": {"signature": True},
                            })
                        else:
                            blocks.append({
                                "kind": "thinking",
                                "ts": ts,
                                "content": text,
                                "meta": {},
                            })
                    elif btype == "text":
                        blocks.append({
                            "kind": "text",
                            "ts": ts,
                            "content": block.get("text", "") or "",
                            "meta": {},
                        })
                    elif btype == "tool_use":
                        blocks.append({
                            "kind": "tool_use",
                            "ts": ts,
                            "content": "",
                            "meta": {
                                "name": block.get("name", ""),
                                "id": block.get("id", ""),
                                "input": block.get("input", {}) or {},
                            },
                        })

            elif entry_type == "user":
                msg = entry.get("message", {}) or {}
                content = msg.get("content", [])
                # User message content may be a string (first-user prompt) OR a
                # list of tool_result blocks. Only the list case concerns us
                # here — string first-user messages are consumed elsewhere
                # (e.g., skill-fork detection).
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "tool_result":
                        result_content = block.get("content", "")
                        if isinstance(result_content, list):
                            # Flatten the [{type:text,text:...}] shape into a single string
                            result_content = " ".join(
                                str(c.get("text", ""))
                                for c in result_content
                                if isinstance(c, dict)
                            )
                        blocks.append({
                            "kind": "tool_result",
                            "ts": ts,
                            "content": str(result_content),
                            "meta": {
                                "tool_use_id": block.get("tool_use_id", ""),
                            },
                        })

    if not preserve_file_order:
        # Stable timestamp sort — entries with empty ts fall at the start.
        blocks.sort(key=lambda b: b["ts"])
    return blocks
