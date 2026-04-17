"""Tests for config.llm_models — validates construction-time guards.

Run: pytest config/test_llm_models.py -v
"""
from __future__ import annotations

import pytest

from config.llm_models import (
    LEARNER,
    LLMRole,
    MODEL_CAPABILITIES,
    PREDICTOR,
)


# ── Active role constants preserve current values ──────────────────────
def test_predictor_preserves_current_config():
    assert PREDICTOR.model == "claude-opus-4-7"
    assert PREDICTOR.effort == "xhigh"
    assert PREDICTOR.max_turns == 20
    assert PREDICTOR.thinking_type == "adaptive"


def test_learner_preserves_current_config():
    assert LEARNER.model == "claude-opus-4-7"
    assert LEARNER.effort == "xhigh"
    assert LEARNER.max_turns == 50
    assert LEARNER.thinking_type == "adaptive"


# ── Valid constructs ───────────────────────────────────────────────────
def test_valid_opus_46_construct():
    r = LLMRole(model="claude-opus-4-6", effort="high", thinking_type="adaptive")
    assert r.as_sdk_kwargs()["model"] == "claude-opus-4-6"
    assert r.as_sdk_kwargs()["effort"] == "high"


def test_valid_haiku_construct():
    r = LLMRole(model="claude-haiku-4-5", effort="low", thinking_type="disabled")
    assert r.as_sdk_kwargs()["thinking"] == {"type": "disabled"}


def test_max_thinking_tokens_included_when_set():
    r = LLMRole(model="claude-opus-4-7", effort="high", max_thinking_tokens=8000)
    kw = r.as_sdk_kwargs()
    assert kw["max_thinking_tokens"] == 8000


def test_max_thinking_tokens_omitted_when_unset():
    r = LLMRole(model="claude-opus-4-7", effort="high")
    assert "max_thinking_tokens" not in r.as_sdk_kwargs()


# ── Validation failures ────────────────────────────────────────────────
def test_rejects_unknown_model():
    with pytest.raises(ValueError, match="Unknown model"):
        LLMRole(model="claude-ultra-9")  # type: ignore[arg-type]


def test_rejects_xhigh_on_46():
    with pytest.raises(ValueError, match="effort='xhigh'"):
        LLMRole(model="claude-opus-4-6", effort="xhigh")


def test_rejects_enabled_thinking_on_47():
    with pytest.raises(ValueError, match="thinking_type='enabled'"):
        LLMRole(
            model="claude-opus-4-7", effort="high", thinking_type="enabled",
        )


def test_rejects_thinking_on_haiku():
    with pytest.raises(ValueError, match="thinking_type='adaptive'"):
        LLMRole(
            model="claude-haiku-4-5", effort="low", thinking_type="adaptive",
        )


def test_rejects_max_turns_zero():
    with pytest.raises(ValueError, match="max_turns must be 1-200"):
        LLMRole(model="claude-opus-4-7", effort="high", max_turns=0)


def test_rejects_max_turns_too_large():
    with pytest.raises(ValueError, match="max_turns must be 1-200"):
        LLMRole(model="claude-opus-4-7", effort="high", max_turns=500)


def test_rejects_tiny_thinking_budget():
    with pytest.raises(ValueError, match="max_thinking_tokens must be >=1024"):
        LLMRole(model="claude-opus-4-7", effort="high", max_thinking_tokens=100)


# ── Extras escape hatch ────────────────────────────────────────────────
def test_extras_passthrough():
    r = LLMRole(
        model="claude-opus-4-7", effort="high",
        extras={"fallback_model": "claude-opus-4-6"},
    )
    assert r.as_sdk_kwargs()["fallback_model"] == "claude-opus-4-6"


def test_extras_cannot_override_model():
    with pytest.raises(ValueError, match="reserved keys"):
        LLMRole(
            model="claude-opus-4-7",
            extras={"model": "claude-haiku-4-5"},
        )


def test_extras_cannot_override_max_turns():
    with pytest.raises(ValueError, match="reserved keys"):
        LLMRole(
            model="claude-opus-4-7",
            max_turns=20,
            extras={"max_turns": 100},
        )


def test_extras_cannot_override_thinking():
    with pytest.raises(ValueError, match="reserved keys"):
        LLMRole(
            model="claude-opus-4-7",
            extras={"thinking": {"type": "disabled"}},
        )


# ── Sanity: MODEL_CAPABILITIES covers all active roles ─────────────────
def test_active_roles_have_registry_entries():
    for role in (PREDICTOR, LEARNER):
        assert role.model in MODEL_CAPABILITIES, (
            f"{role.model} must have an entry in MODEL_CAPABILITIES"
        )
