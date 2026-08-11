"""LIVE real-OpenAI tests for the synonym judge — OPT-IN (``@pytest.mark.llm``).

EXCLUDED from the default run by ``pytest.ini`` (``addopts = -m "not llm"``), so
the standard suite stays fast / free / deterministic / 0-skipped. Run on demand:

    pytest -m llm tests/test_synonym_judge_live.py

These exercise the REAL call path (Structured Outputs, the locked prompt, the
tiered model policy) — the proof that the integration works, per
INTEGRATION_CONTRACT.md §9. Each asserts CONTRACT shape, not a specific verdict
(the judgment is the model's). Requires OPENAI_API_KEY.
"""
from __future__ import annotations

import pytest

import judge_llm
from synonym_fold import SynonymFoldEngine

PACKET = {
    "kind": "synonym", "from_token": "uptake",
    "candidates": [
        {"to_token": "demand", "observation_count": 2,
         "sample_evidence": ["datacenter uptake was strong", "uptake climbed"]},
        {"to_token": "consumption", "observation_count": 2,
         "sample_evidence": ["uptake of capacity rose", "uptake of capacity expanded"]},
    ],
}


OPT_IN = "RUN_LLM_JUDGE_LIVE"


def _require_llm_opt_in() -> None:
    """The opt-in gate, INSIDE each test — the marker alone is NOT a barrier.

    INCIDENT 2026-07-31: a reviewer overrode the marker filter and these tests
    fired REAL OpenAI requests; at least one completed and cost money. That is
    the identical failure the live WRITE probe had — a lane whose only defence
    is `-m` deselection is one flag away from acting. The write probe now needs
    the marker AND an exact opt-in; so does spending money.

    EXACTLY "1": `=0`, `false`, empty and whitespace are all OFF, because an
    authorisation token has one spelling.
    """
    import os
    if os.environ.get(OPT_IN) != "1":
        pytest.skip(f"live LLM judge is opt-in only — real OpenAI spend "
                    f"requires OWNER approval and {OPT_IN}=1 (exactly)")


def _assert_contract(v: dict) -> None:
    assert set(v.keys()) == {"decision", "to_token", "reason"}
    assert v["decision"] in ("promote", "no_global_rule", "defer")
    assert isinstance(v["reason"], str) and v["reason"]
    if v["decision"] == "promote":
        assert v["to_token"] in {"demand", "consumption"}     # a real candidate
    else:
        assert v["to_token"] is None                          # null IFF not promote


@pytest.mark.llm
def test_live_synonym_judge_returns_contract_valid_verdict() -> None:
    """The real judge returns a schema- and rule-valid verdict on a real packet."""
    _require_llm_opt_in()
    judge = judge_llm.make_synonym_judge_fn()                 # real OpenAI transport
    _assert_contract(judge(PACKET))


@pytest.mark.llm
def test_live_judge_caches_second_identical_call() -> None:
    """The cache replays the identical packet without a second API round-trip
    (same object identity of the cached verdict's content)."""
    _require_llm_opt_in()
    cache: dict = {}
    judge = judge_llm.make_synonym_judge_fn(cache=cache)
    v1 = judge(PACKET)
    assert len(cache) == 1
    v2 = judge(PACKET)
    assert v1 == v2 and len(cache) == 1


@pytest.mark.llm
def test_live_engine_with_real_judge_resolves_contested_group() -> None:
    """Inject the REAL judge into the pure engine on a contested sequence; the
    group reaches a valid terminal/frozen resolution with <= 1 promoted token."""
    _require_llm_opt_in()
    eng = SynonymFoldEngine(judge_fn=judge_llm.make_synonym_judge_fn())
    eng.observe("uptake", "demand", event_key="E1", evidence_text="uptake rose")
    eng.observe("uptake", "consumption", event_key="E2", evidence_text="uptake of capacity rose")
    eng.observe("uptake", "demand", event_key="E3", evidence_text="uptake climbed")
    eng.observe("uptake", "consumption", event_key="E4", evidence_text="uptake of capacity expanded")
    assert eng.resolution_of("synonym", "uptake") in ("promoted", "no_global_rule", "frozen")
    assert len(eng.promoted_synonyms()) <= 1
