"""§15A — Layer-1 ACCUMULATION REPLAY  (DETERMINISTIC, GATED 100%)  ·  PASS 3.

Single-event tests prove the gears; THIS proves the engine survives a real run of
events. Production is not one event — it is hundreds in SEQUENCE, each accepted
driver ACCUMULATING into the registry and getting REUSED by later events. The
reuse/dedup guarantee only EXISTS across runs.

This module replays a scripted, ORDERED sequence of hand-crafted emissions
(multiple tickers · >= 2 quarters each · BOTH learner AND news producers · plus a
RE-RUN of an earlier event) with a KNOWN end-state, through the production loop:

    render_catalog(registry, vocab)  (S1, exercised each event)
      -> [scripted emission_json]    (a hand-crafted WRITER emission, NO LLM)
      -> run_one(...)                (S3..S6 — the cleaner)
      -> apply_decision(...)         (§15.0 — the fake-writer MERGE stand-in)
      -> carry (registry, vocab) forward

and asserts the SEVEN §15A cross-run guarantees, one assert-cluster per test:
  (a) same concept across events -> exactly ONE driver; 0 duplicates.
  (b) a driver coined EARLY is REUSED (not re-proposed) LATE.
  (c) the registry grows by EXACTLY the # of distinct NEW concepts (delta from
      the recorded baseline).
  (d) a later emission of a folded form hits the AUTO-ALIAS fast-path (B4).
  (e) a RE-RUN of the same event -> BYTE-IDENTICAL canonical names (idempotency).
  (f) a newly-accepted NOVEL token is classified as a KNOWN slot token in a LATER
      event (the VocabToken seam — new_slot_tokens carried into the snapshot).
  (g) CROSS-PRODUCER: a news emission and a learner emission of the SAME concept
      resolve to the SAME driver (one row, reused).

DETERMINISM / BILLING (Harness_BuilderPrompt.md §0a / §7 / §8): pure, offline, NO
LLM, NO Neo4j, NO network. Synonym promotion (none needed for §15A's guarantees,
but exercised in §15C / the engine tests) uses ONLY the SynonymFoldEngine's
DETERMINISTIC stub judge — never judge_llm / claude_agent_sdk / claude -p /
import anthropic / ANTHROPIC_API_KEY. The real LLM is Pass 4 (§15B), NOT built here.

§15D (BACKEND-AGNOSTIC): the replay drives the §4 Registry interface only, so the
SAME loop runs against ANY Registry implementation.
# TODO(15D-neo4j): run this loop + the contract assertions against a throwaway
#   Neo4j registry in the ingestion harness; do NOT build Neo4j here (§8 fence).

Spec anchors: Harness_BuilderPrompt.md §15.0 (apply_decision), §15A (the loop +
the 7 cross-run guarantees), §2 (the S1..S6 production order), §5 (shapes).

SURFACED (surface-don't-fix, §0a) — V4-segment vs VocabToken-seam interaction:
  When a NEW driver is coined with a NOVEL token in a DISCRIMINATOR position
  (e.g. ``gpu_blackwell_us_revenue`` — blackwell pinned between gpu/us), V4
  requires the stored ``segment`` to match the name's CURRENT sub-dimension token
  set. At coin time the novel token is UNKNOWN, so it is NOT a sub-dimension and
  the valid segment is "GPU US". But once apply_decision merges ``blackwell`` into
  the customer slot (the VocabToken seam), the SAME name's sub-dimension set GROWS
  to {gpu, blackwell, us}, so re-validating the driver against its ORIGINAL "GPU US"
  segment now FAILS V4 — there is NO single segment string that satisfies V4 both
  before AND after the seam for such a driver. This is a genuine cross-run
  interaction, not a test artifact. It does NOT affect:
    - coining the novel-token driver (once, V4 passes at coin time);
    - the seam itself (the lone-token driver blackwell_revenue, whose novel token
      is ALREADY known when IT is coined, has a seam-STABLE single sub-dim → it is
      reused fine, e08/e26);
    - any all-known-token driver (datacenter_us_capex, e04) — V4 stable forever.
  The replay therefore coins gpu_blackwell_us_revenue ONCE (e02, to seed the
  ``blackwell`` slot token for guarantee (f)) and does NOT re-reuse it; guarantee
  (b)'s coined-early-reused-late uses the all-known-token driver instead.
  TODO(surface-to-spec): the ingestion-side writer (out of scope here, §8) likely
  needs to RE-DERIVE / widen a driver's segment when a contained token is later
  learned as a slot token (or V4 should re-validate against the segment as STORED,
  not re-split the name under the grown vocab). Flagged for the §15D / ingestion
  harness; NOT fixed here (additive-only, prod-core untouched).
"""

from __future__ import annotations

import json
import os

import pytest

from render_catalog import render_catalog
from run_one import run_one
from apply_decision import apply_decision
from driver_ids import canonicalize, Rejection, split_respecting_atoms
from registry_fake import Registry
from vocab_seed import build_vocab_snapshot, COLD_START_SEED_DRIVERS


# ─────────────────────────────────────────────────────────────────────────────
# Starting registry — COLD_START_SEED_DRIVERS + the scenario fixture rows.
# §15A wants drivers to RECUR + cross-producer reuse of a seed shortcut
# (oil_supply, cited in guarantee (g)). The cold-start seeds carry oil_supply;
# the scenario fixture carries the modern drivers (iphone_china_sales, ...). We
# union them (fixture wins on a name collision) WITHOUT touching either source
# file — purely an in-test construction (additive, §0a write-scope).
# ─────────────────────────────────────────────────────────────────────────────

_FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__), "fixtures", "fake_registry.json"
)


def _starting_registry() -> Registry:
    """Cold-start seeds + scenario fixture rows, deduped by name (fixture wins)."""
    by_name: dict = {}
    for row in COLD_START_SEED_DRIVERS:
        by_name[row["name"]] = dict(row)
    with open(_FIXTURE_PATH, "r", encoding="utf-8") as fh:
        for row in json.load(fh):
            by_name[row["name"]] = dict(row)
    return Registry(list(by_name.values()))


# ─────────────────────────────────────────────────────────────────────────────
# Emission builders (hand-crafted WRITER emissions, §5; NO LLM).
# ─────────────────────────────────────────────────────────────────────────────

def _emission(
    *,
    source_id: str,
    source_type: str,
    src: str,
    items: list,
    proposals: list | None = None,
) -> dict:
    """A production-shape WRITER emission (§5). One source_catalog entry ``src``
    that every item cites (so V10 resolves)."""
    return {
        "source_id": source_id,
        "source_type": source_type,
        "pit_cutoff": "2026-01-30T17:00:00-05:00",
        "run_id": f"run-{source_id}",
        "result_path": f"/tmp/{source_id}.json",
        "source_catalog": [src],
        "items": items,
        "propose_new_drivers": list(proposals or []),
    }


def _item(name, state, direction, src, evidence_text=None) -> dict:
    it = {
        "ticker": "TICK",
        "driver_name": name,
        "driver_state": state,
        "direction": direction,
        "evidence": [src],
    }
    if evidence_text is not None:
        it["evidence_text"] = evidence_text
    return it


def _proposal(name, base_label, segment, definition, states) -> dict:
    return {
        "name": name,
        "label": name.replace("_", " "),
        "base_label": base_label,
        "segment": segment,
        "definition": definition,
        "allowed_states": list(states),
        "aliases": [],
    }


# trend_motion states reused widely (one state class — passes V6).
_TREND = ["accelerated", "decelerated", "stable", "declined"]


def _scripted_events() -> list:
    """The ORDERED scripted sequence: ~30 emissions across 4 tickers, >= 2
    quarters each, BOTH learner + news producers, a RE-RUN, novel-token coining,
    and word-order folds that seed the auto-alias fast-path. Each entry is a
    ``(label, emission)`` pair; ``label`` is a human tag used in the assertions.

    The sequence is constructed so the KNOWN end-state is deterministic. Designed
    to exercise every §15A guarantee."""
    ev: list = []

    # ── AAPL Q1 (learner) — reuse a seeded modern driver via a word-order
    #    variant (B-M5: china_iphone_sales -> iphone_china_sales, an existing
    #    fixture alias) + a bare seed metric reuse. ──
    ev.append(("e01_aapl_q1_learner", _emission(
        source_id="AAPL_q1_learner", source_type="learner_result", src="SRC:TR:aapl-q1",
        items=[
            _item("china_iphone_sales", "decelerated", "short", "SRC:TR:aapl-q1"),
            # gross_margin state must be in the fixture row's allowed_states
            # (["expanded","contracted","exhausted","built"]) — use "contracted".
            _item("gross_margin", "contracted", "short", "SRC:TR:aapl-q1"),
        ],
    )))

    # ── NVDA Q1 (news) — COIN a brand-new driver carrying a NOVEL token
    #    (blackwell). Its new_slot_tokens seed the VocabToken snapshot (guarantee
    #    f). item name == proposal name (canonical). ──
    ev.append(("e02_nvda_q1_news_coin_blackwell", _emission(
        source_id="NVDA_q1_news", source_type="news", src="SRC:NEWS:nvda-q1",
        items=[_item("gpu_blackwell_us_revenue", "accelerated", "long",
                     "SRC:NEWS:nvda-q1",
                     evidence_text="Blackwell GPU orders from US hyperscalers accelerated.")],
        proposals=[_proposal(
            "gpu_blackwell_us_revenue", "Sales", "GPU US",
            "Revenue from Blackwell GPUs sold to US customers.", _TREND)],
    )))

    # ── XOM Q1 (news) — cross-producer setup: news emits the seed shortcut
    #    oil_supply (B3 exact-name REUSE of the cold-start seed). ──
    ev.append(("e03_xom_q1_news_oil_supply", _emission(
        source_id="XOM_q1_news", source_type="news", src="SRC:NEWS:xom-q1",
        items=[_item("oil_supply", "cut", "short", "SRC:NEWS:xom-q1",
                     evidence_text="OPEC cut oil supply.")],
    )))

    # ── MSFT Q1 (learner) — COIN datacenter_us_capex (canonical name, item ==
    #    proposal). A later word-order variant will fold to it (auto-alias seed). ──
    ev.append(("e04_msft_q1_learner_coin_capex", _emission(
        source_id="MSFT_q1_learner", source_type="learner_result", src="SRC:TR:msft-q1",
        items=[_item("datacenter_us_capex", "accelerated", "long", "SRC:TR:msft-q1",
                     evidence_text="US datacenter capex accelerated.")],
        proposals=[_proposal(
            "datacenter_us_capex", "CapEx", "Datacenter US",
            "Capital expenditure on US datacenters.", _TREND)],
    )))

    # ── NVDA Q1 (learner) — COIN cloud_enterprise_revenue from a word-order raw
    #    (enterprise_cloud_revenue -> cloud_enterprise_revenue). item==proposal
    #    canonical name. ──
    ev.append(("e05_nvda_q1_learner_coin_cloud_ent", _emission(
        source_id="NVDA_q1b_learner", source_type="learner_result", src="SRC:TR:nvda-q1b",
        items=[_item("cloud_enterprise_revenue", "accelerated", "long", "SRC:TR:nvda-q1b",
                     evidence_text="Enterprise cloud revenue accelerated.")],
        # ``cloud`` classifies to the THEME slot (not a V4 sub-dimension); the only
        # V4 sub-token here is ``enterprise`` (customer), so the segment is
        # "Enterprise" (the single sub-dim), not "Cloud Enterprise".
        proposals=[_proposal(
            "cloud_enterprise_revenue", "Revenue", "Enterprise",
            "Cloud revenue from enterprise customers.", _TREND)],
    )))

    # ── AAPL Q2 (news) — REUSE the SAME concept coined at e01 (iphone_china_sales)
    #    via the canonical name (B3) — proves cross-quarter, cross-producer reuse
    #    of an existing driver. ──
    ev.append(("e06_aapl_q2_news_reuse_iphone", _emission(
        source_id="AAPL_q2_news", source_type="news", src="SRC:NEWS:aapl-q2",
        items=[_item("iphone_china_sales", "stable", "long", "SRC:NEWS:aapl-q2")],
    )))

    # ── XOM Q2 (learner) — cross-producer: LEARNER now emits oil_supply (e03 was
    #    news). Both must resolve to the SAME driver (guarantee g). ──
    ev.append(("e07_xom_q2_learner_oil_supply", _emission(
        source_id="XOM_q2_learner", source_type="learner_result", src="SRC:TR:xom-q2",
        items=[_item("oil_supply", "contracted", "short", "SRC:TR:xom-q2",
                     evidence_text="Oil supply contracted further per the call.")],
    )))

    # ── NVDA Q2 (news) — VocabToken seam payoff: emit a LONE-token form
    #    blackwell_revenue. Before e02 coined blackwell this was slot_ambiguous;
    #    now blackwell is a KNOWN customer slot token, so it resolves +
    #    PROPOSE_NEW cleanly (guarantee f). ──
    ev.append(("e08_nvda_q2_news_blackwell_lone", _emission(
        source_id="NVDA_q2_news", source_type="news", src="SRC:NEWS:nvda-q2",
        items=[_item("blackwell_revenue", "accelerated", "long", "SRC:NEWS:nvda-q2",
                     evidence_text="Blackwell revenue accelerated.")],
        proposals=[_proposal(
            "blackwell_revenue", "Revenue", "Blackwell",
            "Revenue attributable to Blackwell products.", _TREND)],
    )))

    # ── MSFT Q2 (news) — word-order variant us_datacenter_capex folds (B6) to the
    #    e04 driver datacenter_us_capex -> REUSE + records the auto-alias. ──
    ev.append(("e09_msft_q2_news_capex_variant", _emission(
        source_id="MSFT_q2_news", source_type="news", src="SRC:NEWS:msft-q2",
        items=[_item("us_datacenter_capex", "stable", "long", "SRC:NEWS:msft-q2")],
    )))

    # ── MSFT Q3 (learner) — re-emit the SAME variant; now it hits the B4
    #    auto-alias fast-path (the alias was added at e09). ──
    ev.append(("e10_msft_q3_learner_capex_fastpath", _emission(
        source_id="MSFT_q3_learner", source_type="learner_result", src="SRC:TR:msft-q3",
        items=[_item("us_datacenter_capex", "accelerated", "long", "SRC:TR:msft-q3")],
    )))

    # ── A spread of distinct NEW concepts across tickers/quarters (to make the
    #    grow-by-exactly-N count meaningful, guarantee c). Each is item==proposal
    #    canonical name, clean novel combination of KNOWN tokens. ──
    ev.append(("e11_nvda_q2_coin_dc_revenue", _emission(
        source_id="NVDA_q2b_news", source_type="news", src="SRC:NEWS:nvda-q2b",
        items=[_item("datacenter_revenue", "accelerated", "long", "SRC:NEWS:nvda-q2b",
                     evidence_text="Datacenter revenue accelerated.")],
        proposals=[_proposal("datacenter_revenue", "Revenue", "Datacenter",
                             "Revenue from datacenter products.", _TREND)],
    )))
    ev.append(("e12_aapl_q2_coin_vision_pro", _emission(
        source_id="AAPL_q2b_learner", source_type="learner_result", src="SRC:TR:aapl-q2b",
        items=[_item("vision_pro_sales", "accelerated", "long", "SRC:TR:aapl-q2b",
                     evidence_text="Vision Pro sales accelerated.")],
        proposals=[_proposal("vision_pro_sales", "Sales", "Vision Pro",
                             "Unit sales of Vision Pro.", _TREND)],
    )))
    ev.append(("e13_xom_q2_coin_cost_of_revenue", _emission(
        source_id="XOM_q2b_news", source_type="news", src="SRC:NEWS:xom-q2b",
        items=[_item("cost_of_revenue", "expanded", "short", "SRC:NEWS:xom-q2b",
                     evidence_text="Cost of revenue expanded.")],
        # allowed_states must be drawn from ONE §F.5 class (V6). Use quantity_move
        # (expanded/contracted/exhausted/built) — NOT a mix with trend_motion.
        proposals=[_proposal("cost_of_revenue", "CostOfRevenue", "Total",
                             "The direct cost attributable to revenue.",
                             ["expanded", "contracted", "exhausted", "built"])],
    )))

    # ── More reuse across later quarters of EARLY-coined drivers (guarantee b:
    #    coined early, reused late). These are all REUSE (no proposals). Note we
    #    REUSE all-KNOWN-token coined drivers (datacenter_us_capex, e04) — NOT the
    #    novel-token driver gpu_blackwell_us_revenue (e02): see the SURFACED note on
    #    the V4-segment-vs-VocabToken-seam interaction in this module's docstring /
    #    the builder return. gpu_blackwell_us_revenue is coined ONCE (e02) to seed
    #    the ``blackwell`` slot token; the seam payoff is the LONE-token driver
    #    blackwell_revenue (e08), whose segment is seam-stable. ──
    ev.append(("e14_nvda_q3_reuse_capex_again", _emission(
        source_id="NVDA_q3_news", source_type="news", src="SRC:NEWS:nvda-q3",
        items=[_item("datacenter_us_capex", "decelerated", "short", "SRC:NEWS:nvda-q3")],
    )))
    ev.append(("e15_msft_q3_reuse_cloud_ent", _emission(
        source_id="MSFT_q3b_news", source_type="news", src="SRC:NEWS:msft-q3b",
        items=[_item("cloud_enterprise_revenue", "decelerated", "short", "SRC:NEWS:msft-q3b")],
    )))
    ev.append(("e16_aapl_q3_reuse_iphone", _emission(
        source_id="AAPL_q3_learner", source_type="learner_result", src="SRC:TR:aapl-q3",
        items=[_item("iphone_china_sales", "declined", "short", "SRC:TR:aapl-q3")],
    )))
    ev.append(("e17_xom_q3_reuse_oil_supply_news", _emission(
        source_id="XOM_q3_news", source_type="news", src="SRC:NEWS:xom-q3",
        # oil_supply allowed_states (seed) = cut/expanded/contracted/exhausted.
        items=[_item("oil_supply", "expanded", "long", "SRC:NEWS:xom-q3",
                     evidence_text="OPEC expanded oil supply.")],
    )))
    ev.append(("e18_nvda_q3_reuse_dc_revenue", _emission(
        source_id="NVDA_q3b_learner", source_type="learner_result", src="SRC:TR:nvda-q3b",
        items=[_item("datacenter_revenue", "stable", "long", "SRC:TR:nvda-q3b")],
    )))
    ev.append(("e19_aapl_q3_reuse_vision_pro", _emission(
        source_id="AAPL_q3b_news", source_type="news", src="SRC:NEWS:aapl-q3b",
        items=[_item("vision_pro_sales", "decelerated", "short", "SRC:NEWS:aapl-q3b")],
    )))
    ev.append(("e20_msft_q4_reuse_capex", _emission(
        source_id="MSFT_q4_learner", source_type="learner_result", src="SRC:TR:msft-q4",
        items=[_item("datacenter_us_capex", "stable", "long", "SRC:TR:msft-q4")],
    )))

    # ── DUPLICATE-CONCEPT bait across producers: the SAME concept reached via
    #    DIFFERENT raw spellings in different quarters must collapse to ONE driver
    #    (guarantee a). gpu_hyperscaler_bookings is a fixture driver with an alias
    #    hyperscaler_gpu_bookings — emit both spellings + a fold. ──
    ev.append(("e21_nvda_q4_reuse_hgb_exact", _emission(
        source_id="NVDA_q4_news", source_type="news", src="SRC:NEWS:nvda-q4",
        items=[_item("gpu_hyperscaler_bookings", "accelerated", "long", "SRC:NEWS:nvda-q4")],
    )))
    ev.append(("e22_nvda_q4_reuse_hgb_alias", _emission(
        source_id="NVDA_q4b_learner", source_type="learner_result", src="SRC:TR:nvda-q4b",
        items=[_item("hyperscaler_gpu_bookings", "stable", "long", "SRC:TR:nvda-q4b")],
    )))

    # ── A few more cross-quarter reuses to push the sequence past ~20 events with
    #    drivers recurring (so reuse-late-after-coined-early is unambiguous). ──
    ev.append(("e23_xom_q4_reuse_oil_supply_learner", _emission(
        source_id="XOM_q4_learner", source_type="learner_result", src="SRC:TR:xom-q4",
        # oil_supply allowed_states (seed) = cut/expanded/contracted/exhausted.
        items=[_item("oil_supply", "contracted", "short", "SRC:TR:xom-q4",
                     evidence_text="Oil supply contracted further per the call.")],
    )))
    ev.append(("e24_aapl_q4_reuse_gross_margin", _emission(
        source_id="AAPL_q4_news", source_type="news", src="SRC:NEWS:aapl-q4",
        items=[_item("gross_margin", "expanded", "long", "SRC:NEWS:aapl-q4")],
    )))
    ev.append(("e25_msft_q4_reuse_cloud_ent_news", _emission(
        source_id="MSFT_q4b_news", source_type="news", src="SRC:NEWS:msft-q4b",
        items=[_item("cloud_enterprise_revenue", "stable", "long", "SRC:NEWS:msft-q4b")],
    )))
    ev.append(("e26_nvda_q4_reuse_blackwell_lone", _emission(
        source_id="NVDA_q4c_news", source_type="news", src="SRC:NEWS:nvda-q4c",
        items=[_item("blackwell_revenue", "stable", "long", "SRC:NEWS:nvda-q4c",
                     evidence_text="Blackwell revenue stable.")],
    )))
    ev.append(("e27_aapl_q4_reuse_eps", _emission(
        source_id="AAPL_q4b_learner", source_type="learner_result", src="SRC:TR:aapl-q4b",
        items=[_item("eps", "beat", "long", "SRC:TR:aapl-q4b")],
    )))
    ev.append(("e28_xom_q4_reuse_revenue", _emission(
        source_id="XOM_q4b_news", source_type="news", src="SRC:NEWS:xom-q4b",
        items=[_item("revenue", "beat", "long", "SRC:NEWS:xom-q4b")],
    )))
    ev.append(("e29_msft_q5_coin_advertising", _emission(
        source_id="MSFT_q5_news", source_type="news", src="SRC:NEWS:msft-q5",
        items=[_item("advertising_china_revenue", "accelerated", "long", "SRC:NEWS:msft-q5",
                     evidence_text="Advertising revenue in China accelerated.")],
        proposals=[_proposal("advertising_china_revenue", "Revenue", "Advertising China",
                             "Advertising revenue from the China market.", _TREND)],
    )))

    # ── e30 = a LATE REUSE of the e04-coined driver (guarantee b: coined at
    #    event #4, reused at event #30 — an all-known-token driver, so its V4
    #    segment stays valid across the whole accumulated run). ──
    ev.append(("e30_msft_q5_reuse_capex_late", _emission(
        source_id="MSFT_q5b_learner", source_type="learner_result", src="SRC:TR:msft-q5b",
        items=[_item("datacenter_us_capex", "decelerated", "short", "SRC:TR:msft-q5b")],
    )))

    return ev


# The DISTINCT NEW concepts the scripted sequence COINS (the known end-state for
# guarantee c). Every other event REUSES an existing driver (seed/fixture/coined).
_DISTINCT_NEW_CONCEPTS = [
    "gpu_blackwell_us_revenue",   # e02
    "datacenter_us_capex",        # e04
    "cloud_enterprise_revenue",   # e05
    "blackwell_revenue",          # e08
    "datacenter_revenue",         # e11
    "vision_pro_sales",           # e12
    "cost_of_revenue",            # e13
    "advertising_china_revenue",  # e29
]


# ─────────────────────────────────────────────────────────────────────────────
# The replay engine (TEST-SCAFFOLD helper local to this module): run the loop,
# capture a per-event trace + the final (registry, vocab) for the assertions.
# ─────────────────────────────────────────────────────────────────────────────

def _replay(events: list):
    """Run the production loop over ``events``. Returns
    ``(registry, vocab, trace, baseline_count)`` where ``trace`` is a list of
    ``{label, source_type, decision}`` per event. render_catalog is invoked each
    event (S1) and its non-empty string asserted, so the FULL S1..S6+apply chain
    is exercised in production order."""
    registry = _starting_registry()
    vocab = build_vocab_snapshot()
    baseline_count = len(registry.all_drivers())
    trace: list = []
    for label, emission in events:
        catalog = render_catalog(registry, vocab)   # S1 — the producer's view
        assert isinstance(catalog, str) and catalog, "render_catalog must produce a block"
        decision = run_one(emission, registry, vocab)  # S3..S6
        assert decision["shape_ok"], (label, decision["shape_errors"])
        registry, vocab = apply_decision(decision, registry, vocab)  # §15.0 apply
        trace.append({
            "label": label,
            "source_type": emission["source_type"],
            "decision": decision,
        })
    return registry, vocab, trace, baseline_count


def _statuses(trace: list, label: str) -> list:
    """Return the per-item (status, canonical_name) list for the event ``label``."""
    for entry in trace:
        if entry["label"] == label:
            return [(it["status"], it["canonical_name"]) for it in entry["decision"]["items"]]
    raise AssertionError(f"event {label} not in trace")


# ─────────────────────────────────────────────────────────────────────────────
# pytest fixtures — one shared replay (the loop is deterministic + cheap).
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def replay():
    return _replay(_scripted_events())


# ═════════════════════════════════════════════════════════════════════════════
# Guarantee (a) — same concept across events -> exactly ONE driver; 0 duplicates.
# ═════════════════════════════════════════════════════════════════════════════

def test_15A_a_no_duplicate_drivers(replay):
    """§15A(a): no two drivers share the SAME sorted-canonical token set (the
    graph never fragments one concept into two rows). After a 30-event replay
    where the same concept recurs via many spellings/producers, every driver's
    sorted-canonical-token key is UNIQUE."""
    registry, vocab, _trace, _baseline = replay
    seen: dict = {}
    for d in registry.all_drivers():
        key = tuple(sorted(split_respecting_atoms(d["name"], set(vocab.frozen_atoms))))
        assert key not in seen, (
            f"duplicate concept: {d['name']} and {seen[key]} share sorted tokens {key}"
        )
        seen[key] = d["name"]


# ═════════════════════════════════════════════════════════════════════════════
# Guarantee (b) — a driver coined EARLY is REUSED (not re-proposed) LATE.
# ═════════════════════════════════════════════════════════════════════════════

def test_15A_b_early_coin_reused_late(replay):
    """§15A(b): datacenter_us_capex is COINED at event #4 (PROPOSE_NEW) and REUSED
    at event #30 (REUSE, NOT re-proposed). The whole point of accumulation is that
    an early coin is available to a far-later event. (We use the all-known-token
    coined driver — not the novel-token gpu_blackwell_us_revenue — so its V4
    segment stays valid across the accumulated run; see the SURFACED V4-vs-seam
    note in the module docstring.)"""
    _registry, _vocab, trace, _baseline = replay
    # event #4 coined it.
    coin = _statuses(trace, "e04_msft_q1_learner_coin_capex")
    assert ("PROPOSE_NEW", "datacenter_us_capex") in coin
    # event #30 reused it (NOT proposed).
    late = _statuses(trace, "e30_msft_q5_reuse_capex_late")
    assert late == [("REUSE", "datacenter_us_capex")], late
    # belt-and-braces: it was proposed EXACTLY once across the whole replay.
    proposed_count = sum(
        1 for e in trace for it in e["decision"]["items"]
        if it["status"] == "PROPOSE_NEW" and it["canonical_name"] == "datacenter_us_capex"
    )
    assert proposed_count == 1, f"coined more than once: {proposed_count}"


# ═════════════════════════════════════════════════════════════════════════════
# Guarantee (c) — registry grows by EXACTLY the # of distinct NEW concepts.
# ═════════════════════════════════════════════════════════════════════════════

def test_15A_c_grows_by_exactly_distinct_new(replay):
    """§15A(c): final driver count - baseline == the number of DISTINCT new
    concepts coined. Reuse adds ZERO rows; each distinct new concept adds EXACTLY
    one. The known end-state is _DISTINCT_NEW_CONCEPTS (8)."""
    registry, _vocab, _trace, baseline = replay
    final = len(registry.all_drivers())
    assert final - baseline == len(_DISTINCT_NEW_CONCEPTS), (
        f"grew by {final - baseline}, expected {len(_DISTINCT_NEW_CONCEPTS)} "
        f"(baseline={baseline}, final={final})"
    )
    # every distinct-new concept is present as exactly one row...
    names = [d["name"] for d in registry.all_drivers()]
    for concept in _DISTINCT_NEW_CONCEPTS:
        assert names.count(concept) == 1, f"{concept} not present exactly once"
    # ...and NO baseline driver was duplicated or dropped.
    baseline_names = {d["name"] for d in _starting_registry().all_drivers()}
    assert baseline_names.issubset(set(names)), "a baseline driver disappeared"


# ═════════════════════════════════════════════════════════════════════════════
# Guarantee (d) — a later folded form hits the AUTO-ALIAS fast-path (B4).
# ═════════════════════════════════════════════════════════════════════════════

def test_15A_d_auto_alias_fast_path(replay):
    """§15A(d): the word-order variant us_datacenter_capex was folded (B6) at e09
    and auto-aliased onto datacenter_us_capex; at e10 the SAME variant resolves
    via the B4 exact-alias path. We prove the resolution went through the ALIAS by
    asserting (1) the variant is now in the driver's aliases and (2) the registry's
    lookup_by_alias resolves it to the driver — the B4 fast-path mechanism."""
    registry, _vocab, trace, _baseline = replay
    # the variant FOLDED to the canonical driver at e09 (REUSE) ...
    assert _statuses(trace, "e09_msft_q2_news_capex_variant") == [
        ("REUSE", "datacenter_us_capex")]
    # ... auto-aliasing the raw variant onto the driver.
    driver = registry.lookup_exact_name("datacenter_us_capex")
    assert "us_datacenter_capex" in driver["aliases"], driver["aliases"]
    # the B4 exact-alias path now resolves the variant DIRECTLY (no canonicalize).
    hit = registry.lookup_by_alias("us_datacenter_capex")
    assert hit is not None and hit["name"] == "datacenter_us_capex"
    # and the LATE re-emission (e10) reused it.
    assert _statuses(trace, "e10_msft_q3_learner_capex_fastpath") == [
        ("REUSE", "datacenter_us_capex")]


# ═════════════════════════════════════════════════════════════════════════════
# Guarantee (e) — a RE-RUN of the same event -> BYTE-IDENTICAL canonical names.
# ═════════════════════════════════════════════════════════════════════════════

def test_15A_e_event_rerun_byte_identical(replay):
    """§15A(e): event-level idempotency. Re-running an ALREADY-applied event
    against the post-replay (registry, vocab) yields the byte-identical canonical
    names and adds ZERO new drivers (the writer's MERGE is a no-op). We re-run e06
    (an AAPL reuse of iphone_china_sales): both re-runs REUSE the byte-identical
    canonical name, with no new row. (A REUSE event is the right idempotency probe
    — the concept is already in the registry, so the result is order-independent.)"""
    registry, vocab, _trace, _baseline = replay
    events = dict(_scripted_events())
    rerun_emission = events["e06_aapl_q2_news_reuse_iphone"]

    before_names = [d["name"] for d in registry.all_drivers()]
    d1 = run_one(rerun_emission, registry, vocab)
    names1 = [it["canonical_name"] for it in d1["items"]]
    registry, vocab = apply_decision(d1, registry, vocab)

    d2 = run_one(rerun_emission, registry, vocab)
    names2 = [it["canonical_name"] for it in d2["items"]]

    after_names = [d["name"] for d in registry.all_drivers()]
    # byte-identical canonical names across the two re-runs.
    assert names1 == names2 == ["iphone_china_sales"]
    # the re-run added ZERO drivers (concept already in the registry).
    assert sorted(after_names) == sorted(before_names), "re-run grew the registry"
    # both runs are a pure REUSE (idempotent writer).
    assert [it["status"] for it in d1["items"]] == ["REUSE"]
    assert [it["status"] for it in d2["items"]] == ["REUSE"]


def test_15A_e_full_replay_byte_identical(replay):
    """§15A(e), stronger: replaying the ENTIRE scripted sequence a SECOND time
    (from a fresh cold start) yields the byte-identical per-event canonical names
    AND the identical final registry. Determinism end-to-end (no set/dict-order
    leakage, no LLM, no clock)."""
    _r1, _v1, trace_a, _b1 = replay
    _r2, _v2, trace_b, _b2 = _replay(_scripted_events())
    names_a = [[it["canonical_name"] for it in e["decision"]["items"]] for e in trace_a]
    names_b = [[it["canonical_name"] for it in e["decision"]["items"]] for e in trace_b]
    assert names_a == names_b
    assert sorted(d["name"] for d in _r1.all_drivers()) == sorted(
        d["name"] for d in _r2.all_drivers())


# ═════════════════════════════════════════════════════════════════════════════
# Guarantee (f) — a newly-accepted NOVEL token becomes a KNOWN slot token later.
# ═════════════════════════════════════════════════════════════════════════════

def test_15A_f_vocab_token_seam(replay):
    """§15A(f): the VocabToken read-seam. The novel token ``blackwell`` was coined
    at e02 (new_slot_tokens -> customer slot). BEFORE that snapshot growth, a
    LONE-token form ``blackwell_revenue`` canonicalizes to a Rejection
    (slot_ambiguous — §D fails closed on a lone novel token before the metric).
    AFTER apply_decision merged ``blackwell`` into the snapshot's customer slot,
    e08 resolves ``blackwell_revenue`` cleanly (PROPOSE_NEW) — a name that would
    NOT have resolved before."""
    registry, vocab, trace, _baseline = replay

    # BEFORE: against the COLD-START snapshot, the lone-token form is rejected.
    cold_vocab = build_vocab_snapshot()
    cold = canonicalize("blackwell_revenue", cold_vocab)
    assert isinstance(cold, Rejection) and cold.reason == "slot_ambiguous", cold

    # the seam carried blackwell into the accumulated snapshot's customer slot.
    assert "blackwell" in vocab.slot_vocabs["customer"]

    # AFTER: the same lone-token form resolves against the accumulated snapshot.
    warm = canonicalize("blackwell_revenue", vocab)
    assert warm == "blackwell_revenue", warm

    # and e08 (which ran AFTER e02 in the replay) accepted it (PROPOSE_NEW), so the
    # seam made a previously-unreachable name reachable mid-replay.
    assert _statuses(trace, "e08_nvda_q2_news_blackwell_lone") == [
        ("PROPOSE_NEW", "blackwell_revenue")]

    # the snapshot stays a frozen dataclass; vocab_seed module seeds are untouched.
    import vocab_seed as _vs
    assert "blackwell" not in {t for s in build_vocab_snapshot().slot_vocabs.values() for t in s}, (
        "build_vocab_snapshot leaked an accumulated token — vocab_seed was mutated")
    assert "blackwell" not in _vs.OBJECTS and "blackwell" not in _vs.CUSTOMERS


# ═════════════════════════════════════════════════════════════════════════════
# Guarantee (g) — CROSS-PRODUCER: news + learner of the SAME concept -> SAME row.
# ═════════════════════════════════════════════════════════════════════════════

def test_15A_g_cross_producer_same_driver(replay):
    """§15A(g): oil_supply is emitted by a NEWS producer (e03) and by a LEARNER
    producer (e07) — across different quarters — and BOTH resolve to the SAME
    single driver row. The shared writer is producer-agnostic (E30 harness
    generality). Proven by: both events REUSE the identical canonical name, the
    producers differ, and the registry holds exactly ONE oil_supply row."""
    registry, _vocab, trace, _baseline = replay

    news_entry = next(e for e in trace if e["label"] == "e03_xom_q1_news_oil_supply")
    learner_entry = next(e for e in trace if e["label"] == "e07_xom_q2_learner_oil_supply")

    assert news_entry["source_type"] == "news"
    assert learner_entry["source_type"] == "learner_result"

    news_names = [it["canonical_name"] for it in news_entry["decision"]["items"]]
    learner_names = [it["canonical_name"] for it in learner_entry["decision"]["items"]]
    assert news_names == learner_names == ["oil_supply"]

    # both REUSED (the seed shortcut), neither coined a competing row.
    assert [it["status"] for it in news_entry["decision"]["items"]] == ["REUSE"]
    assert [it["status"] for it in learner_entry["decision"]["items"]] == ["REUSE"]

    # exactly ONE oil_supply driver in the registry.
    assert sum(1 for d in registry.all_drivers() if d["name"] == "oil_supply") == 1


# ═════════════════════════════════════════════════════════════════════════════
# apply_decision unit checks (§15.0) — the fake-writer mechanics in isolation.
# ═════════════════════════════════════════════════════════════════════════════

def test_15_0_apply_propose_new_adds_driver_and_seam():
    """§15.0: a PROPOSE_NEW decision adds the driver row AND merges its
    new_slot_tokens into the returned snapshot (the VocabToken seam), without
    mutating the input snapshot (frozen) or vocab_seed."""
    registry = _starting_registry()
    vocab = build_vocab_snapshot()
    n_before = len(registry.all_drivers())
    emission = _emission(
        source_id="u1", source_type="news", src="SRC:NEWS:u1",
        items=[_item("gpu_blackwell_us_revenue", "accelerated", "long", "SRC:NEWS:u1",
                     evidence_text="Blackwell GPU US revenue accelerated.")],
        proposals=[_proposal("gpu_blackwell_us_revenue", "Sales", "GPU US",
                             "Revenue from Blackwell GPUs sold to US customers.", _TREND)],
    )
    decision = run_one(emission, registry, vocab)
    assert decision["items"][0]["status"] == "PROPOSE_NEW"
    registry2, vocab2 = apply_decision(decision, registry, vocab)
    # driver added
    assert registry2.lookup_exact_name("gpu_blackwell_us_revenue") is not None
    assert len(registry2.all_drivers()) == n_before + 1
    # seam merged (customer slot grew), input snapshot UNCHANGED (frozen).
    assert "blackwell" in vocab2.slot_vocabs["customer"]
    assert "blackwell" not in vocab.slot_vocabs["customer"]
    # frozen_atoms (multi-token only) untouched — the new token is single-token.
    assert vocab2.frozen_atoms == vocab.frozen_atoms


def test_15_0_apply_reuse_applies_alias_no_new_row():
    """§15.0: a REUSE decision whose record carries aliases_added applies the
    alias to the existing driver (so the next emission hits B4) and adds NO new
    driver row."""
    registry = _starting_registry()
    vocab = build_vocab_snapshot()
    # coin datacenter_us_capex first
    coin = _emission(
        source_id="u2a", source_type="news", src="SRC:NEWS:u2a",
        items=[_item("datacenter_us_capex", "accelerated", "long", "SRC:NEWS:u2a",
                     evidence_text="US datacenter capex accelerated.")],
        proposals=[_proposal("datacenter_us_capex", "CapEx", "Datacenter US",
                             "Capital expenditure on US datacenters.", _TREND)],
    )
    registry, vocab = apply_decision(run_one(coin, registry, vocab), registry, vocab)
    n_after_coin = len(registry.all_drivers())
    # now a word-order variant -> B6 REUSE + auto-alias
    variant = _emission(
        source_id="u2b", source_type="learner_result", src="SRC:TR:u2b",
        items=[_item("us_datacenter_capex", "stable", "long", "SRC:TR:u2b")],
    )
    decision = run_one(variant, registry, vocab)
    assert decision["items"][0]["status"] == "REUSE"
    assert "us_datacenter_capex" in decision["items"][0]["aliases_added"]
    registry, vocab = apply_decision(decision, registry, vocab)
    # NO new row, alias applied.
    assert len(registry.all_drivers()) == n_after_coin
    assert "us_datacenter_capex" in registry.lookup_exact_name("datacenter_us_capex")["aliases"]


def test_15_0_apply_promoted_synonym_folds_into_snapshot():
    """§15.0 (promoted synonym): a promoted-synonym dict from a Pass-2
    SynonymFoldEngine (driven by its DETERMINISTIC fixed-verdict stub judge — NO
    LLM) folds into the returned snapshot's synonym_map, so canonicalize then
    folds the from_token on the NEXT run. Uses the engine's REAL promote path
    (N=2 + a fixed 'promote' verdict) — never a hand-built dict."""
    from synonym_fold import SynonymFoldEngine

    # a DETERMINISTIC fixed-verdict stub judge (no LLM): always promote 'demand'.
    def fixed_promote_judge(packet):
        return {"decision": "promote", "to_token": "demand", "reason": "stub-fixed"}

    eng = SynonymFoldEngine(judge_fn=fixed_promote_judge)
    # single candidate, two distinct evidenced events -> direct promote (no judge).
    eng.observe("uptake", "demand", "ev1", "datacenter uptake softened")
    eng.observe("uptake", "demand", "ev2", "enterprise uptake improved")
    promoted = eng.promoted_synonyms()
    assert promoted == {"uptake": "demand"}, promoted

    registry = _starting_registry()
    vocab = build_vocab_snapshot()
    # a no-op decision (no items) so apply ONLY folds the promoted synonym.
    empty_decision = {"items": []}
    _registry2, vocab2 = apply_decision(
        empty_decision, registry, vocab, promoted_synonyms=promoted)
    assert vocab2.synonym_map.get("uptake") == "demand"
    # the fold is now live: 'datacenter_uptake' canonicalizes via the …_demand form.
    folded = canonicalize("datacenter_uptake", vocab2)
    assert folded == "datacenter_demand", folded
    # input snapshot + vocab_seed seed untouched.
    assert "uptake" not in vocab.synonym_map
    import vocab_seed as _vs
    assert "uptake" not in _vs.SYNONYM_MAP


def test_15_0_apply_reject_writes_nothing():
    """§15.0: a REJECT decision writes NOTHING (no auto-repair — §8). A
    state-in-name item (opec_supply_cut) rejects; the registry + snapshot are
    returned unchanged."""
    registry = _starting_registry()
    vocab = build_vocab_snapshot()
    n_before = len(registry.all_drivers())
    emission = _emission(
        source_id="u3", source_type="news", src="SRC:NEWS:u3",
        items=[_item("opec_supply_cut", "cut", "short", "SRC:NEWS:u3")],
    )
    decision = run_one(emission, registry, vocab)
    assert decision["items"][0]["status"] == "REJECT"
    registry2, vocab2 = apply_decision(decision, registry, vocab)
    assert len(registry2.all_drivers()) == n_before
    assert vocab2 is vocab  # no change -> the SAME frozen snapshot returned
