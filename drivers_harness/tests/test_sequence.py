"""S1→S6 production-order integration  (Layer-1, deterministic, NO LLM).

Exercises ``run_sequence`` — the harness mirror of the production sequence
(Harness_BuilderPrompt.md §2 / §6 "SEQUENCE (CORE — point 6)") — with a
HAND-CRAFTED emission (no ``emit_fn``, no ``context``) so the whole chain runs
offline with zero LLM:

    S1   catalog = render_catalog(registry, vocab)
    S2   (skipped: no emit_fn)
    S2.5 (skipped: no learner_result; supplied emission_json used directly)
    S3   validate_emission_shape(emission)
    S4   per item: reuse_or_propose  (B1..B10)
    S5   per item: validators        (V1..V14)
    S6   decide(...)                 -> the "would-write" decision dict

The hand emission references ONE reuse (B-M5: ``china_iphone_sales`` ->
REUSE ``iphone_china_sales``), ONE propose_new (a clean novel driver
``cloud_capex`` with ALL §5 propose-entry fields incl. a one-sentence
definition + evidence), and ONE state-in-name REJECT (B-M4: ``opec_supply_cut``
-> the state ``cut`` must NOT enter the name). The decision dict's
accepted / proposed / rejected buckets + the per-item records are asserted,
and the S1→S6 CALL ORDER + hand-off shapes are asserted to match production.

A second cluster covers the adapter ``learner_to_writer_input`` (doubt #43 /
A14 / A15): it stamps the orchestrator-owned RunContext envelope onto each
learner tag to build ``items[]`` and carries ``propose_new_drivers`` through.
A transcript-sourced tag (``SRC:TR:``) sits alongside an 8-K tag
(``SRC:REPORT:``) so A15 transcript-separate-tagging is exercised.

Spec anchors: Harness_BuilderPrompt.md §2 (the S1→S6 production sequence), §6
point "SEQUENCE (CORE — point 6)", §4 ``run_sequence`` / ``run_one`` contracts,
§5 shapes (emission JSON / RunContext / decision / learner_result) ;
req_canonical.md A14, A15, B-M4, B-M5 ; DoubtsInHTML.md #43.
"""

from __future__ import annotations

import pytest

import run_sequence as RS
from run_sequence import run_sequence
from run_one import run_one, learner_to_writer_input
from render_catalog import render_catalog
from registry_fake import Registry
from vocab_seed import build_vocab_snapshot


# ─────────────────────────────────────────────────────────────────────────────
# fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def vocab():
    """The frozen VocabSnapshot built from the §F.1-F.9 seeds."""
    return build_vocab_snapshot()


@pytest.fixture()
def registry():
    """The scenario registry (fixtures/fake_registry.json) — has
    ``iphone_china_sales`` (B-M5 reuse target) etc."""
    return Registry.from_fixture()


# ── A representative SRC catalog carrying BOTH an 8-K report ref AND a
#    transcript ref, so A15 transcript-separate-tagging + V10 resolution are
#    testable (Harness_BuilderPrompt.md §5 SRC:* convention). ──
SRC_8K = "SRC:REPORT:0001-8k#ITEM2.02"
SRC_TR = "SRC:TR:txn-aapl-q1"
SRC_NEWS = "SRC:NEWS:opec-cut-1"
SOURCE_CATALOG = [SRC_8K, SRC_TR, SRC_NEWS]


def _hand_emission() -> dict:
    """A production-shape hand-crafted WRITER emission (Harness_BuilderPrompt.md
    §5 emission JSON) — NO LLM. Three items exercise the three S6 buckets:

      1. ``china_iphone_sales`` (8-K)   -> REUSE ``iphone_china_sales``  (B-M5)
      2. ``cloud_capex``        (transcript) -> PROPOSE_NEW (clean novel driver
         with ALL §5 propose fields + one-sentence definition + evidence)
      3. ``opec_supply_cut``    (news)  -> REJECT (state ``cut`` in name, B-M4)
    """
    return {
        "source_id": "AAPL_2026-01-30T17.00.00-05.00",
        "source_type": "learner_result",
        "pit_cutoff": "2026-01-30T17:00:00-05:00",
        "run_id": "run-seq-001",
        "result_path": "/tmp/run-seq-001.json",
        "source_catalog": list(SOURCE_CATALOG),
        "items": [
            {  # B-M5 word-order variant -> reuse the canonical registry name
                "ticker": "AAPL",
                "driver_name": "china_iphone_sales",
                "driver_state": "decelerated",
                "direction": "short",
                "evidence": [SRC_8K],
            },
            {  # clean novel driver -> PROPOSE_NEW (transcript-sourced)
                "ticker": "AAPL",
                "driver_name": "cloud_capex",
                "driver_state": "accelerated",
                "direction": "long",
                "evidence": [SRC_TR],
                "evidence_text": "Management cited rising cloud capex on the call.",
            },
            {  # B-M4 state-in-name -> REJECT (state must stay in driver_state)
                "ticker": "AAPL",
                "driver_name": "opec_supply_cut",
                "driver_state": "cut",
                "direction": "short",
                "evidence": [SRC_NEWS],
            },
        ],
        "propose_new_drivers": [
            {
                "name": "cloud_capex",
                "label": "cloud capex",
                "base_label": "CapEx",
                "segment": "Total",
                "definition": "Capital expenditure on cloud infrastructure.",
                "allowed_states": ["accelerated", "decelerated", "stable", "declined"],
                "aliases": [],
            },
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# SEQUENCE — S1→S6 decision via run_sequence on a hand emission (no LLM)
# ─────────────────────────────────────────────────────────────────────────────

def test_sequence_hand_emission_decision_buckets(registry, vocab):
    """§6 SEQUENCE point-6 / B-M4 / B-M5: run S1→S6 in production order via
    ``run_sequence`` with a hand-crafted emission (no emit_fn) and assert the
    decision dict's accepted / proposed / rejected buckets are exactly the
    spec-derived outcomes.

      B-M5: ``china_iphone_sales`` REUSES ``iphone_china_sales`` (word-order fold).
      §6 G:  ``cloud_capex`` PROPOSE_NEW (clean novel known-token combination).
      B-M4: ``opec_supply_cut`` REJECT — the state ``cut`` may NOT enter the name.

    Spec: Harness_BuilderPrompt.md §6 (SEQUENCE), §5 (decision shape);
    req_canonical.md B-M4, B-M5."""
    decision = run_sequence(None, registry, vocab, emission_json=_hand_emission())

    # S3 shape gate passed (production-complete emission).
    assert decision["shape_ok"] is True
    assert decision["shape_errors"] == []

    # S6 buckets — derived from the spec rules above.
    assert decision["accepted"] == ["iphone_china_sales", "cloud_capex"]
    assert decision["proposed"] == ["cloud_capex"]
    assert decision["rejected"] == [
        {"name": "opec_supply_cut", "reason": "state_in_name"}
    ]
    assert decision["summary"] == {"accepted_count": 2, "rejected_count": 1}


def test_sequence_per_item_records(registry, vocab):
    """§5 per-item records: the decision carries one ``items[]`` record per
    emitted tag, in emission order, with the resolved
    ``raw_name / canonical_name / status / reason`` an ``apply_decision`` step
    would consume. Asserts the REUSE / PROPOSE_NEW / REJECT trichotomy and the
    PROPOSE_NEW payload round-trips the producer template.

    Spec: Harness_BuilderPrompt.md §5 (decision per-item records), §4 run_one."""
    decision = run_sequence(None, registry, vocab, emission_json=_hand_emission())
    recs = decision["items"]
    assert [r["raw_name"] for r in recs] == [
        "china_iphone_sales", "cloud_capex", "opec_supply_cut",
    ]

    reuse_rec, propose_rec, reject_rec = recs

    # item 1 — REUSE the canonical registry name (B-M5).
    assert reuse_rec["status"] == "REUSE"
    assert reuse_rec["canonical_name"] == "iphone_china_sales"
    assert reuse_rec["reason"] is None

    # item 2 — PROPOSE_NEW; payload carries the §5 propose fields incl. definition.
    assert propose_rec["status"] == "PROPOSE_NEW"
    assert propose_rec["canonical_name"] == "cloud_capex"
    assert propose_rec["reason"] is None
    payload = propose_rec["proposal_payload"]
    assert payload is not None
    assert payload["name"] == "cloud_capex"
    assert payload["definition"] == "Capital expenditure on cloud infrastructure."

    # item 3 — REJECT carrying the named §C reason (B-M4: state in name).
    assert reject_rec["status"] == "REJECT"
    assert reject_rec["canonical_name"] is None
    assert reject_rec["reason"] == "state_in_name"


def test_sequence_equals_direct_run_one(registry, vocab):
    """A22 determinism / §2 parity: the deterministic ``run_sequence`` path is a
    pure pass-through to ``run_one`` (S1 render is read-only; with no emit_fn,
    S2/S2.5 are skipped). The decision must equal a DIRECT ``run_one`` on the
    SAME emission — proving run_sequence adds no hidden state and the hand-off
    shape is identical.

    Spec: Harness_BuilderPrompt.md §2 (chain), §4 run_sequence/run_one;
    req_canonical.md A22 (determinism)."""
    emission = _hand_emission()
    via_seq = run_sequence(None, registry, vocab, emission_json=emission)
    via_direct = run_one(emission, registry, vocab)
    assert via_seq == via_direct


def test_sequence_render_catalog_contains_seeded_names(registry, vocab):
    """S1 hand-off shape: ``render_catalog`` produces the LLM-readable block the
    producer would read, and it CONTAINS the seeded driver names the hand
    emission reuses (so a real producer could match them). Confirms S1 feeds a
    faithful catalog into the chain.

    Spec: Harness_BuilderPrompt.md §2 (S1), §4 render_catalog (per-Driver set)."""
    catalog = render_catalog(registry, vocab)
    assert "=== DRIVER CATALOG ===" in catalog
    # the B-M5 reuse target is visible to the producer.
    assert "iphone_china_sales" in catalog
    # a vocab excerpt is present so the producer has slot/shortcut hints.
    assert "=== VOCAB EXCERPT ===" in catalog
    assert "SHORTCUTS:" in catalog


def test_sequence_call_order_S1_through_S6(registry, vocab, monkeypatch):
    """§2 / §6 point-6: assert the S1→S6 production CALL ORDER. We spy on
    ``render_catalog`` (S1) and ``run_one`` (S3-S6) as ``run_sequence`` sees
    them, and supply an ``emit_fn`` (S2) + ``context`` (S2.5) to capture the
    full ordered chain:

        S1 render_catalog  ->  S2 emit_fn  ->  S2.5 learner_to_writer_input
        ->  S3-S6 run_one

    The emit_fn receives the S1 catalog (proving S1 precedes S2), and run_one
    receives the adapter's emission (proving S2.5 precedes S3). NO real LLM —
    emit_fn is a hand stub returning a fixed learner_result (Harness_BuilderPrompt
    §7: the harness never makes the LLM call; emit_fn is the in-session seam).

    Spec: Harness_BuilderPrompt.md §2 (S1..S6 order), §4 run_sequence (S1/S2/
    S2.5/S3-S6 wiring); req_canonical.md A14 (learner is the producer)."""
    calls: list[str] = []

    real_render = render_catalog

    def spy_render(reg_arg, vocab_arg):
        calls.append("S1:render_catalog")
        return real_render(reg_arg, vocab_arg)

    captured = {}

    def emit_fn(evidence_packet, catalog):
        # S2 — runs AFTER S1, and is handed the S1 catalog block.
        calls.append("S2:emit_fn")
        captured["catalog_seen_by_emit"] = catalog
        return {
            "primary_driver": {
                "driver_name": "china_iphone_sales",
                "driver_state": "decelerated",
                "direction": "short",
                "evidence": [SRC_8K],
            },
            "contributing_factors": [],
            "propose_new_drivers": [],
        }

    real_run_one = run_one

    def spy_run_one(emission_json, reg_arg, vocab_arg):
        calls.append("S3-S6:run_one")
        captured["emission_seen_by_run_one"] = emission_json
        return real_run_one(emission_json, reg_arg, vocab_arg)

    # patch the names as run_sequence resolves them (it imported them by name).
    monkeypatch.setattr(RS, "render_catalog", spy_render)
    monkeypatch.setattr(RS, "run_one", spy_run_one)

    context = {
        "ticker": "AAPL",
        "source_id": "AAPL_q1",
        "source_type": "learner_result",
        "pit_cutoff": "2026-01-30T17:00:00-05:00",
        "run_id": "run-seq-order",
        "result_path": "/tmp/run-seq-order.json",
        "source_catalog": list(SOURCE_CATALOG),
    }
    decision = run_sequence(
        {"evidence_text": "...", "source_catalog": list(SOURCE_CATALOG)},
        registry, vocab, emit_fn=emit_fn, context=context,
    )

    # ORDER: S1 render -> S2 emit -> S3-S6 run_one (S2.5 adapter sits between
    # S2 and S3 inside run_sequence; its output is what run_one received).
    assert calls == ["S1:render_catalog", "S2:emit_fn", "S3-S6:run_one"]

    # S1 precedes S2: emit_fn was handed the rendered catalog block.
    assert "=== DRIVER CATALOG ===" in captured["catalog_seen_by_emit"]

    # S2.5 precedes S3: run_one received the ADAPTER's emission (envelope
    # stamped from context; items synthesized from the learner tags).
    em = captured["emission_seen_by_run_one"]
    assert em["source_id"] == "AAPL_q1"
    assert em["items"][0]["ticker"] == "AAPL"
    assert em["items"][0]["driver_name"] == "china_iphone_sales"

    # and the chain still resolves the B-M5 reuse end-to-end.
    assert decision["accepted"] == ["iphone_china_sales"]


def test_sequence_requires_emission_or_emit_fn(registry, vocab):
    """§4 run_sequence contract: with NEITHER an emission_json NOR an emit_fn,
    run_sequence has no producer input and must raise (fail-closed) rather than
    silently produce an empty decision.

    Spec: Harness_BuilderPrompt.md §4 run_sequence."""
    with pytest.raises(ValueError):
        run_sequence(None, registry, vocab)


def test_sequence_emit_fn_without_context_raises(registry, vocab):
    """§4 / §5 / doubt #43: when a learner_result is produced (emit_fn path) the
    RunContext ``context`` is REQUIRED for the S2.5 adapter — the learner tags
    carry no envelope, so without context run_sequence must raise.

    Spec: Harness_BuilderPrompt.md §4 run_sequence (context REQUIRED on the
    learner_result path), §5 RunContext; DoubtsInHTML.md #43."""
    def emit_fn(evidence_packet, catalog):
        return {
            "primary_driver": {
                "driver_name": "china_iphone_sales",
                "driver_state": "decelerated",
                "direction": "short",
                "evidence": [SRC_8K],
            },
            "contributing_factors": [],
            "propose_new_drivers": [],
        }

    with pytest.raises(ValueError):
        run_sequence({}, registry, vocab, emit_fn=emit_fn, context=None)


# ─────────────────────────────────────────────────────────────────────────────
# ADAPTER — learner_to_writer_input (doubt #43 / A14 / A15)
# ─────────────────────────────────────────────────────────────────────────────

def test_adapter_stamps_envelope_and_carries_proposals(vocab):
    """doubt #43 / A14 / A15: ``learner_to_writer_input`` adapts a LEARNER
    ``learner_result`` (``primary_driver`` + ``contributing_factors[]`` +
    ``propose_new_drivers[]``) into a WRITER ``emission JSON``. It STAMPS the
    orchestrator-owned RunContext envelope (ticker / source_id / pit_cutoff /
    run_id / result_path / source_catalog) onto each tag to build ``items[]``,
    and carries ``propose_new_drivers`` through unchanged.

    A15 transcript-separate-tagging: the primary tag is 8-K-sourced
    (``SRC:REPORT:``) while the contributing tag is transcript-sourced
    (``SRC:TR:``); both prefixes survive into the writer items, so a downstream
    consumer can still tell a transcript-sourced driver from an 8-K one.

    Spec: Harness_BuilderPrompt.md §5 (learner→writer adapter, RunContext,
    emission JSON), §4 learner_to_writer_input; req_canonical.md A14, A15;
    DoubtsInHTML.md #43."""
    learner_result = {
        "primary_driver": {  # 8-K-sourced primary (A14)
            "driver_name": "china_iphone_sales",
            "driver_state": "decelerated",
            "direction": "short",
            "evidence": [SRC_8K],
        },
        "contributing_factors": [  # transcript-sourced contributing (A15)
            {
                "driver_name": "cloud_capex",
                "driver_state": "accelerated",
                "direction": "long",
                "evidence": [SRC_TR],
            },
        ],
        "propose_new_drivers": [
            {
                "name": "cloud_capex",
                "label": "cloud capex",
                "base_label": "CapEx",
                "segment": "Total",
                "definition": "Capital expenditure on cloud infrastructure.",
                "allowed_states": ["accelerated", "decelerated", "stable", "declined"],
                "aliases": [],
            },
        ],
    }
    context = {
        "ticker": "AAPL",
        "source_id": "AAPL_2026-01-30",
        "source_type": "learner_result",
        "pit_cutoff": "2026-01-30T17:00:00-05:00",
        "run_id": "run-adapt-001",
        "result_path": "/tmp/run-adapt-001.json",
        "source_catalog": list(SOURCE_CATALOG),
    }

    emission = learner_to_writer_input(learner_result, context)

    # envelope stamped from context (NOT learner-authored).
    assert emission["source_id"] == "AAPL_2026-01-30"
    assert emission["source_type"] == "learner_result"
    assert emission["pit_cutoff"] == "2026-01-30T17:00:00-05:00"
    assert emission["run_id"] == "run-adapt-001"
    assert emission["result_path"] == "/tmp/run-adapt-001.json"
    assert emission["source_catalog"] == list(SOURCE_CATALOG)

    # primary_driver + contributing_factors -> items[], in that order.
    items = emission["items"]
    assert len(items) == 2
    assert [i["driver_name"] for i in items] == ["china_iphone_sales", "cloud_capex"]
    # ticker stamped onto EVERY item (the learner tags carried none).
    assert all(i["ticker"] == "AAPL" for i in items)
    # tag fields carried through verbatim.
    assert items[0]["driver_state"] == "decelerated"
    assert items[0]["direction"] == "short"

    # A15: the 8-K tag and the transcript tag keep their distinct SRC prefixes.
    assert items[0]["evidence"] == [SRC_8K]      # SRC:REPORT: (8-K)
    assert items[1]["evidence"] == [SRC_TR]      # SRC:TR:      (transcript)
    assert items[0]["evidence"][0].startswith("SRC:REPORT:")
    assert items[1]["evidence"][0].startswith("SRC:TR:")

    # propose_new_drivers carried through unchanged (doubt #43).
    assert emission["propose_new_drivers"] == learner_result["propose_new_drivers"]


def test_adapter_no_driver_case_empty_items(vocab):
    """§5 (F5 no-driver case): a ``learner_result`` with ``primary_driver=None``
    and empty ``contributing_factors`` (+ no proposals) adapts to an emission
    with EMPTY ``items[]`` — the adapter does not invent a tag. The envelope is
    still stamped from context.

    Spec: Harness_BuilderPrompt.md §5 (learner_result no-driver case / adapter);
    DoubtsInHTML.md #43."""
    learner_result = {
        "primary_driver": None,
        "contributing_factors": [],
        "propose_new_drivers": [],
    }
    context = {
        "ticker": "AAPL",
        "source_id": "AAPL_nodriver",
        "pit_cutoff": "2026-01-30T17:00:00-05:00",
        "run_id": "run-empty",
        "result_path": "/tmp/run-empty.json",
        "source_catalog": [],
    }
    emission = learner_to_writer_input(learner_result, context)
    assert emission["items"] == []
    assert emission["propose_new_drivers"] == []
    assert emission["source_id"] == "AAPL_nodriver"


def test_adapter_requires_context(vocab):
    """§5 / doubt #43: ``learner_to_writer_input`` REQUIRES a RunContext —
    ``learner_result`` alone cannot synthesize the orchestrator envelope, so a
    None context must raise (fail-closed).

    Spec: Harness_BuilderPrompt.md §5 (context REQUIRED); DoubtsInHTML.md #43."""
    learner_result = {
        "primary_driver": None,
        "contributing_factors": [],
        "propose_new_drivers": [],
    }
    with pytest.raises(ValueError):
        learner_to_writer_input(learner_result, None)
