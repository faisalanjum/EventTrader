"""Central SDK role profile for Python-owned Claude Agent SDK call sites.

Single source of truth for model identity + effort + thinking + turn budget
across predictor/learner/future roles. Validated at construction time
against MODEL_CAPABILITIES so incompatible combos (e.g. ``effort="xhigh"``
on ``claude-opus-4-6``) fail at import, not at SDK call time.

Scope limitation: this module governs PYTHON-OWNED SDK paths only.
Skill / agent frontmatter-driven flows (e.g. ``model: opus`` in SKILL.md)
are resolved by the SDK session model at invocation time and are NOT
controlled here. If strict single-source-of-truth for those flows is
needed, they must be unified separately.

Usage:
    from config.llm_models import PREDICTOR, LEARNER

    options = ClaudeAgentOptions(
        **LEARNER.as_sdk_kwargs(),
        setting_sources=["project"],
        permission_mode="bypassPermissions",
        cli_path=_sdk_cli_path(),
        stderr=_stderr_sink,
        env=_sdk_subprocess_env(),
    )
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

# NOTE: SDK 0.1.61 Literal for ``effort`` excludes "xhigh" (type-hint lag);
# runtime accepts it and routes correctly to Opus 4.7. MODEL_CAPABILITIES
# below is the authoritative per-model validation source.
Effort = Literal["low", "medium", "high", "xhigh", "max"]
ThinkingType = Literal["adaptive", "enabled", "disabled"]

# Keys reserved by the dataclass itself — blocked in ``extras`` to prevent
# silent override of validated fields.
_RESERVED_EXTRA_KEYS = frozenset({
    "model", "effort", "thinking", "max_turns", "max_thinking_tokens",
})


MODEL_CAPABILITIES: dict[str, dict[str, Any]] = {
    "claude-opus-4-7": {
        "efforts":        {"low", "medium", "high", "xhigh", "max"},
        "thinking_types": {"adaptive", "disabled"},
        "notes": "xhigh is 4.7-only as of 2026-04-17. thinking.type.enabled rejected — use adaptive.",
    },
    "claude-opus-4-6": {
        "efforts":        {"low", "medium", "high", "max"},
        "thinking_types": {"adaptive", "enabled", "disabled"},
        "notes": "Legacy-stable. Accepts both adaptive and enabled thinking.",
    },
    "claude-sonnet-4-6": {
        "efforts":        {"low", "medium", "high"},
        "thinking_types": {"adaptive", "disabled"},
    },
    "claude-haiku-4-5": {
        "efforts":        {"low", "medium"},
        "thinking_types": {"disabled"},
        "notes": "No thinking support; fastest/cheapest tier.",
    },
}


@dataclass(frozen=True)
class LLMRole:
    """Per-role SDK profile. Validated at construction time.

    Fields modelled first-class are the ones that define role identity
    today. Any other SDK kwarg can be passed via ``extras`` (escape hatch);
    if a given kwarg proves useful across roles, promote it to a first-
    class field in a follow-up diff.
    """
    model: str
    effort: Effort = "high"
    thinking_type: ThinkingType = "adaptive"
    max_turns: int = 20
    max_thinking_tokens: int | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        caps = MODEL_CAPABILITIES.get(self.model)
        if not caps:
            raise ValueError(
                f"Unknown model {self.model!r}. Add an entry to MODEL_CAPABILITIES first."
            )
        if self.effort not in caps["efforts"]:
            raise ValueError(
                f"effort={self.effort!r} not supported on {self.model}. "
                f"Allowed: {sorted(caps['efforts'])}"
            )
        if self.thinking_type not in caps["thinking_types"]:
            raise ValueError(
                f"thinking_type={self.thinking_type!r} not supported on {self.model}. "
                f"Allowed: {sorted(caps['thinking_types'])}"
            )
        if not 1 <= self.max_turns <= 200:
            raise ValueError(f"max_turns must be 1-200, got {self.max_turns}")
        if self.max_thinking_tokens is not None and self.max_thinking_tokens < 1024:
            raise ValueError(
                f"max_thinking_tokens must be >=1024, got {self.max_thinking_tokens}"
            )
        collision = _RESERVED_EXTRA_KEYS & self.extras.keys()
        if collision:
            raise ValueError(
                f"extras cannot override reserved keys: {sorted(collision)}. "
                f"Use the dataclass fields instead."
            )

    def as_sdk_kwargs(self) -> dict[str, Any]:
        """Return kwargs suitable for ``ClaudeAgentOptions(**role.as_sdk_kwargs(), ...)``."""
        kw: dict[str, Any] = {
            "model": self.model,
            "effort": self.effort,
            "thinking": {"type": self.thinking_type},
            "max_turns": self.max_turns,
        }
        if self.max_thinking_tokens is not None:
            kw["max_thinking_tokens"] = self.max_thinking_tokens
        kw.update(self.extras)
        return kw


# ── Active roles ───────────────────────────────────────────────────────
# Preserve current per-role values exactly — predictor is a single-shot
# forward call (~2-5 tool invocations), learner investigates 8-15 minutes.
PREDICTOR = LLMRole(model="claude-opus-4-7", effort="xhigh", max_turns=20)
LEARNER   = LLMRole(model="claude-opus-4-7", effort="xhigh", max_turns=50)
