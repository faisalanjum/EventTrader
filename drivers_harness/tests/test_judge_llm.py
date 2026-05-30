"""Deterministic unit tests for judge_llm.py — NO network (fake transport).

Runs in the DEFAULT suite (NOT marked llm). Drives every INTEGRATION_CONTRACT
path with an injected fake transport: prompt loading, post-validation rules,
fail-safe defer, hard-case escalation, and the cache key + hit. The real OpenAI
call path is exercised separately by tests/test_synonym_judge_live.py (opt-in).
"""
from __future__ import annotations

import judge_llm

PACKET = {
    "kind": "synonym", "from_token": "uptake",
    "candidates": [
        {"to_token": "demand", "observation_count": 2, "sample_evidence": ["uptake rose"]},
        {"to_token": "consumption", "observation_count": 2,
         "sample_evidence": ["uptake of capacity rose"]},
    ],
}


def _fake_const(verdict, *, exc=None, calls=None):
    """A fake transport that returns a constant verdict (or raises / returns None)."""
    def transport(system, user, schema, schema_name, model):
        if calls is not None:
            calls.append(model)
        if exc is not None:
            raise exc
        return dict(verdict) if isinstance(verdict, dict) else verdict
    return transport


def _fake_by_model(mapping, *, calls=None):
    """A fake transport that dispatches the verdict by model name (for escalation)."""
    def transport(system, user, schema, schema_name, model):
        if calls is not None:
            calls.append(model)
        v = mapping.get(model)
        if isinstance(v, Exception):
            raise v
        return dict(v) if isinstance(v, dict) else v
    return transport


def _judge(transport, **kw):
    kw.setdefault("cache", {})          # in-memory: unit tests never touch disk
    return judge_llm.make_synonym_judge_fn(transport=transport, **kw)


# ── prompt loading ───────────────────────────────────────────────────────────
def test_prompt_loads_system_schema_and_content_hash() -> None:
    system, schema, version, chash = judge_llm.load_prompt("synonym_judge.v1")
    assert "SYNONYM JUDGE" in system and len(system) > 200
    assert version == "synonym_judge.v1"
    assert isinstance(chash, str) and len(chash) >= 16     # content hash present
    assert schema["properties"]["decision"]["enum"] == ["promote", "no_global_rule", "defer"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"decision", "to_token", "reason"}


# ── happy paths (pass-through of valid verdicts) ─────────────────────────────
def test_valid_promote_passthrough() -> None:
    j = _judge(_fake_const({"decision": "promote", "to_token": "demand", "reason": "ok"}))
    assert j(PACKET) == {"decision": "promote", "to_token": "demand", "reason": "ok"}


def test_valid_no_global_rule_passthrough() -> None:
    j = _judge(_fake_const({"decision": "no_global_rule", "to_token": None, "reason": "ctx"}))
    assert j(PACKET) == {"decision": "no_global_rule", "to_token": None, "reason": "ctx"}


# ── post-validation (the rules the schema can't express) ─────────────────────
def test_promote_to_token_not_a_candidate_defers() -> None:
    j = _judge(_fake_const({"decision": "promote", "to_token": "revenue", "reason": "x"}))
    assert j(PACKET)["decision"] == "defer"            # never guess a non-candidate token


def test_promote_null_to_token_defers() -> None:
    j = _judge(_fake_const({"decision": "promote", "to_token": None, "reason": "x"}))
    assert j(PACKET)["decision"] == "defer"


def test_non_promote_with_to_token_is_coerced_null() -> None:
    j = _judge(_fake_const({"decision": "no_global_rule", "to_token": "demand", "reason": "x"}))
    v = j(PACKET)
    assert v["decision"] == "no_global_rule" and v["to_token"] is None   # to_token non-null IFF promote


def test_invalid_decision_defers() -> None:
    j = _judge(_fake_const({"decision": "merge", "to_token": None, "reason": "x"}))
    assert j(PACKET)["decision"] == "defer"


# ── fail-safe (never guess) ──────────────────────────────────────────────────
def test_none_output_defers() -> None:
    j = _judge(_fake_const(None))
    assert j(PACKET)["decision"] == "defer"


def test_transport_exception_defers() -> None:
    j = _judge(_fake_const(None, exc=RuntimeError("api down")))
    assert j(PACKET)["decision"] == "defer"


def test_non_dict_output_defers() -> None:
    j = _judge(_fake_const("not a dict"))
    assert j(PACKET)["decision"] == "defer"


# ── hard-case escalation (default defers -> stronger model) ──────────────────
def test_escalation_on_defer_uses_stronger_model() -> None:
    calls: list[str] = []
    t = _fake_by_model({
        judge_llm.DEFAULT_MODEL: {"decision": "defer", "to_token": None, "reason": "unsure"},
        judge_llm.ESCALATION_MODEL: {"decision": "promote", "to_token": "demand", "reason": "sure"},
    }, calls=calls)
    v = judge_llm.make_synonym_judge_fn(transport=t, cache={})(PACKET)
    assert calls == [judge_llm.DEFAULT_MODEL, judge_llm.ESCALATION_MODEL]   # escalated once
    assert v == {"decision": "promote", "to_token": "demand", "reason": "sure"}


# (removed test_no_escalation_when_default_decides: under the new policy a
# `promote` ESCALATES to confirm. The only no-escalation case is now
# `no_global_rule` -> see test_no_global_rule_is_not_escalated, plus the
# promote-confirmation tests below.)
def test_escalation_both_defer_stays_defer() -> None:
    calls: list[str] = []
    t = _fake_by_model({
        judge_llm.DEFAULT_MODEL: {"decision": "defer", "to_token": None, "reason": "a"},
        judge_llm.ESCALATION_MODEL: {"decision": "defer", "to_token": None, "reason": "b"},
    }, calls=calls)
    v = judge_llm.make_synonym_judge_fn(transport=t, cache={})(PACKET)
    assert calls == [judge_llm.DEFAULT_MODEL, judge_llm.ESCALATION_MODEL]
    assert v["decision"] == "defer"


# ── cache (decide once, replay by code) ──────────────────────────────────────
def test_cache_hit_avoids_second_call() -> None:
    calls: list[str] = []
    j = _judge(_fake_const({"decision": "promote", "to_token": "demand", "reason": "x"},
                           calls=calls), escalation_model=None)
    j(PACKET)
    j(PACKET)                                           # identical packet
    assert len(calls) == 1                              # second served from cache


def test_cache_key_includes_model_so_different_models_recompute() -> None:
    shared: dict = {}
    calls: list[str] = []
    t = _fake_const({"decision": "promote", "to_token": "demand", "reason": "x"}, calls=calls)
    _judge(t, default_model="A", escalation_model=None, cache=shared)(PACKET)
    _judge(t, default_model="B", escalation_model=None, cache=shared)(PACKET)
    assert len(shared) == 2 and len(calls) == 2         # model is part of the key


# ── content-hash cache key (edit prompt content -> new key, no stale replay) ──
def test_content_hash_changes_with_prompt_content() -> None:
    h1 = judge_llm._content_hash("system A", {"x": 1})
    h2 = judge_llm._content_hash("system B", {"x": 1})       # different system text
    h3 = judge_llm._content_hash("system A", {"x": 2})       # different schema
    assert len({h1, h2, h3}) == 3 and len(h1) >= 16
    assert judge_llm._content_hash("system A", {"x": 1}) == h1   # deterministic


# ── promote-confirmation (verify the risky merge with the stronger model) ─────
def _promote(tok):
    return {"decision": "promote", "to_token": tok, "reason": "x"}


def test_promote_confirmed_same_token_promotes() -> None:
    calls: list[str] = []
    t = _fake_by_model({judge_llm.DEFAULT_MODEL: _promote("demand"),
                        judge_llm.ESCALATION_MODEL: _promote("demand")}, calls=calls)
    v = judge_llm.make_synonym_judge_fn(transport=t, cache={})(PACKET)
    assert calls == [judge_llm.DEFAULT_MODEL, judge_llm.ESCALATION_MODEL]   # confirmed
    assert v["decision"] == "promote" and v["to_token"] == "demand"


def test_promote_disagreement_on_token_defers() -> None:
    t = _fake_by_model({judge_llm.DEFAULT_MODEL: _promote("demand"),
                        judge_llm.ESCALATION_MODEL: _promote("consumption")})
    assert judge_llm.make_synonym_judge_fn(transport=t, cache={})(PACKET)["decision"] == "defer"


def test_promote_strong_says_no_global_rule_returns_that() -> None:
    t = _fake_by_model({judge_llm.DEFAULT_MODEL: _promote("demand"),
                        judge_llm.ESCALATION_MODEL: {"decision": "no_global_rule",
                                                     "to_token": None, "reason": "ctx"}})
    v = judge_llm.make_synonym_judge_fn(transport=t, cache={})(PACKET)
    assert v["decision"] == "no_global_rule" and v["to_token"] is None


def test_promote_strong_defers_defers() -> None:
    t = _fake_by_model({judge_llm.DEFAULT_MODEL: _promote("demand"),
                        judge_llm.ESCALATION_MODEL: {"decision": "defer",
                                                     "to_token": None, "reason": "unsure"}})
    assert judge_llm.make_synonym_judge_fn(transport=t, cache={})(PACKET)["decision"] == "defer"


def test_no_global_rule_is_not_escalated() -> None:
    calls: list[str] = []
    t = _fake_by_model({judge_llm.DEFAULT_MODEL: {"decision": "no_global_rule",
                                                  "to_token": None, "reason": "ctx"}}, calls=calls)
    v = judge_llm.make_synonym_judge_fn(transport=t, cache={})(PACKET)
    assert calls == [judge_llm.DEFAULT_MODEL]            # safe decision -> no escalation
    assert v["decision"] == "no_global_rule"


# ── persistent file cache (survives a fresh instance / process) ──────────────
def test_file_cache_persists_across_instances(tmp_path) -> None:
    p = tmp_path / "c.jsonl"
    c1 = judge_llm.FileCache(p)
    assert "k1" not in c1
    c1["k1"] = {"decision": "defer", "to_token": None, "reason": "x"}
    assert "k1" in c1 and c1["k1"]["decision"] == "defer"
    c2 = judge_llm.FileCache(p)                          # fresh load from disk
    assert "k1" in c2 and c2["k1"]["reason"] == "x"


# ── cacheability: failure-path defers must NOT be persisted (retry next run) ──
def test_failure_defer_is_not_cached() -> None:
    cache: dict = {}
    j = _judge(_fake_const(None, exc=ConnectionError("network blip")), cache=cache)
    assert j(PACKET)["decision"] == "defer"
    assert len(cache) == 0                              # outage -> NOT persisted


def test_promote_confirm_transient_failure_not_cached_then_retries() -> None:
    """The cold-probe blocker: mini promotes, the gpt-5.4 CONFIRM call hits a
    transient error -> defer THIS run, NOT cached; a later call re-invokes the
    model and (now healthy) confirms the promote."""
    cache: dict = {}
    n = {"confirm": 0}

    def transport(system, user, schema, schema_name, model):
        if model == judge_llm.DEFAULT_MODEL:
            return {"decision": "promote", "to_token": "demand", "reason": "x"}
        n["confirm"] += 1
        if n["confirm"] == 1:
            raise ConnectionError("APIConnectionError (transient)")   # 1st confirm fails
        return {"decision": "promote", "to_token": "demand", "reason": "confirmed"}

    j = judge_llm.make_synonym_judge_fn(transport=transport, cache=cache)
    v1 = j(PACKET)
    assert v1["decision"] == "defer" and len(cache) == 0      # failure -> defer, NOT cached
    v2 = j(PACKET)                                            # cache empty -> model called AGAIN
    assert v2["decision"] == "promote" and v2["to_token"] == "demand"
    assert len(cache) == 1 and n["confirm"] == 2             # now a real verdict IS cached


def test_semantic_defer_is_cached() -> None:
    """A genuine model-reasoned defer (both models defer) IS cached (decide-once)."""
    calls: list[str] = []
    t = _fake_by_model({
        judge_llm.DEFAULT_MODEL: {"decision": "defer", "to_token": None, "reason": "unsure"},
        judge_llm.ESCALATION_MODEL: {"decision": "defer", "to_token": None, "reason": "still unsure"},
    }, calls=calls)
    cache: dict = {}
    j = judge_llm.make_synonym_judge_fn(transport=t, cache=cache)
    assert j(PACKET)["decision"] == "defer" and len(cache) == 1      # semantic defer cached
    j(PACKET)
    assert calls == [judge_llm.DEFAULT_MODEL, judge_llm.ESCALATION_MODEL]   # 2nd served from cache
