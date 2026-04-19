"""Adapter between the shared SDK JSONL parser and the legacy hook bucket shape.

Exists because .claude/hooks/obsidian_capture.py pre-renders tool_use summaries,
pairs tool_result into tool_use records, strips MCP envelopes, truncates result
text at 2000 chars, and counts redacted-thinking AS thinking — all of which are
hook-specific concerns that thinking_blocks.parse_session_blocks() intentionally
does NOT do.

Zero behaviour change for the hook (invariant). See obsidian_thinking.md §3(d).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import NamedTuple

# Self-contained sibling import — adapter may be imported from any cwd.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from thinking_blocks import parse_session_blocks  # noqa: E402


class HookBlocks(NamedTuple):
    """Legacy bucket shape consumed by .claude/hooks/obsidian_capture.py.

    - thinking:              [{text, ts}, ...]  — redacted-thinking merged in
    - text:                  [{text, ts}, ...]  — empties filtered out
    - tool:                  [{text, ts, result}, ...]  — paired + cleaned + truncated
    - total_thinking_chars:  sum of visible-thinking content lengths (redacted=0)
    """

    thinking: list[dict]
    text: list[dict]
    tool: list[dict]
    total_thinking_chars: int


def _truncate_safe_fence(text: str, limit: int) -> str:
    """Truncate ``text`` to ``limit`` chars, closing an unbalanced ``\u0060\u0060\u0060``
    code fence if the cut landed inside one.

    Mirrors scripts/earnings/thinking_harvester.py::_truncate_safe_fence; kept
    local to the adapter to avoid coupling the two modules. Without this,
    the hook's 2000-char truncation on tool_result content could leak an
    unclosed ``\u0060\u0060\u0060`` that confuses the outer ``\u0060\u0060\u0060``
    wrapping the hook renders around each tool call.
    """
    if len(text) <= limit:
        return text
    truncated = text[:limit]
    if truncated.count("```") % 2 == 1:
        truncated = truncated + "\n```"
    return truncated


def clean_tool_result(text: str) -> str:
    """Strip MCP envelope, replace <persisted-output>, mark <tool_use_error>.

    Ported verbatim from .claude/hooks/obsidian_capture.py::_clean_tool_result
    (which becomes dead code after the hook switches to this adapter).
    """
    # Strip MCP envelope: {"result":[{"type":"text","text":"ACTUAL",...}]}
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and "result" in parsed:
            inner = parsed["result"]
            if isinstance(inner, list) and inner and isinstance(inner[0], dict):
                text = inner[0].get("text", text)
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        pass
    # Handle <persisted-output> — replace with size note
    po = re.search(r"<persisted-output>\s*Output too large \(([^)]+)\)", text)
    if po:
        return f"[output too large \u2014 {po.group(1)}]"
    # Handle <tool_use_error> — mark with prefix
    if "<tool_use_error>" in text:
        err = re.search(r"<tool_use_error>(.*?)</tool_use_error>", text, re.DOTALL)
        return f"ERROR: {err.group(1).strip()}" if err else text
    return text


def parse_transcript_for_hook(jsonl_path: str | Path | None) -> HookBlocks:
    """Parse an SDK session transcript into the hook's legacy bucket shape.

    Silent-fail contract: returns empty HookBlocks on any parse/IO failure —
    never raises. Matches the hook's pre-refactor `try/except:` wrapper on
    the inline parse loop.
    """
    if not jsonl_path:
        return HookBlocks([], [], [], 0)
    try:
        # preserve_file_order=True — the hook's legacy pairing semantics rely
        # on encountering tool_use BEFORE tool_result in FILE order. Two
        # learner-fixture tool_results have file-position<ts-position relative
        # to their tool_use (by ~7-9ms clock skew), and the legacy hook
        # orphans them; timestamp-sorted order would pair them instead.
        blocks = parse_session_blocks(Path(jsonl_path), preserve_file_order=True)
    except Exception:
        return HookBlocks([], [], [], 0)

    thinking: list[dict] = []
    text_out: list[dict] = []
    tool: list[dict] = []
    total = 0
    pending: dict[str, int] = {}

    for b in blocks:
        kind = b["kind"]
        ts = b["ts"]
        if kind in ("thinking", "thinking_redacted"):
            content = b["content"]  # "" for redacted
            total += len(content)
            thinking.append({"text": content, "ts": ts})
        elif kind == "text":
            content = b["content"].strip()
            if content:
                text_out.append({"text": content, "ts": ts})
        elif kind == "tool_use":
            name = b["meta"].get("name", "unknown")
            call_id = b["meta"].get("id", "")
            inp = b["meta"].get("input", {}) or {}
            if name == "Bash":
                summary = f"{name}: {inp.get('command', '')[:500]}"
            else:
                summary = f"{name}({json.dumps(inp)[:500]})"
            tool.append({"text": summary, "ts": ts, "result": None})
            if call_id:
                pending[call_id] = len(tool) - 1
        elif kind == "tool_result":
            call_id = b["meta"].get("tool_use_id", "")
            # clean → truncate-safe-fence (closes ``` if the 2000-char cut
            # landed mid-code-block so the hook's outer ```-wrap stays sane)
            cleaned = _truncate_safe_fence(clean_tool_result(b["content"]), 2000)
            if call_id and call_id in pending:
                tool[pending[call_id]]["result"] = cleaned
            elif cleaned.strip():
                tool.append({"text": f"\u21b3 {cleaned}", "ts": ts, "result": None})

    return HookBlocks(thinking, text_out, tool, total)
