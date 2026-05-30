"""Bucket I — the in-memory N=2 synonym-learner with the injectable judge seam
(Harness_BuilderPrompt.md §6-I, §11B, §4 ``synonym_fold.py`` contract, §13
judge-seam INTERFACE). Pass 2, DETERMINISTIC, gated 100% — NO LLM, NO
skips/xfails. The judge_fn here is a DETERMINISTIC fixed-verdict STUB (a plain
injectable callable), NOT a model.

§6 bucket I (line 450-451): "seen 1x -> candidate · 2x distinct events ->
promoted, folds on 3rd · evidence-absent -> not counted · conflicting to_token ->
COMPETING candidate (NOT first-wins) -> on a promotion attempt FREEZE + judge-seam
resolves {to_A, to_B, no-global-rule, defer}; one PROMOTED to_token per
(kind, from_token)."

§11B pass criteria (line 560-564): "1 obs -> stays a hidden candidate; 2 distinct
events -> promoted; an observation whose from_token is absent from that event's
evidence is NOT counted AND leaves NO record (evidence gate BEFORE creating any
record — v11-4); a 2nd, different to_token for the same (kind, from_token) is NOT
first-wins-rejected — it coexists as a competing candidate, and on a promotion
attempt FREEZES + the injectable judge seam resolves it to one of {to_A, to_B,
no-global-rule, defer} (one PROMOTED to_token per key); plurals/acronyms are NOT
learned (stay static §F.3/§F.4)."

§4 contract (line 273, conflict semantics LOCKED 2026-05-29): in-memory
PER-CANDIDATE (kind, from_token, to_token) -> {observation_event_keys:set, status,
sample_evidence}; competing to_tokens MAY coexist, each with its OWN count;
promote at len >= 2 (N=2 = ELIGIBILITY gate); count only if from_token in
evidence; synonyms only; CONFLICT = competing candidate (NOT first-wins); on a
promotion attempt with competitors FREEZE + judge_fn(packet)->verdict; one
PROMOTED to_token per (kind, from_token); promoted synonyms feed
build_vocab_snapshot on the next run.

§13 judge-seam INTERFACE (line 615-618): judge_fn(packet)->verdict;
  packet  = {kind, from_token, candidates:[{to_token, observation_count,
             sample_evidence:[...]}, ...]}  -- candidates are ONLY the N=2-cleared
             competitors (the eligibility gate is CODE, run BEFORE the judge).
  verdict = {decision: "promote"|"no_global_rule"|"defer",
             to_token: <a candidate's to_token>|null, reason: str}.

One assert-cluster per test (§9). Pure: builds engines + snapshots in-memory.
"""
from __future__ import annotations

from synonym_fold import (
    SynonymFoldEngine,
    PROMOTION_THRESHOLD,
    STATUS_CANDIDATE,
    STATUS_ELIGIBLE,
    STATUS_PROMOTED,
    STATUS_REJECTED,
    RESOLUTION_OPEN,
    RESOLUTION_PROMOTED,
    RESOLUTION_FROZEN,
    RESOLUTION_NO_GLOBAL_RULE,
)
from vocab_seed import build_vocab_snapshot
from driver_ids import canonicalize, Rejection


# ── tiny deterministic judge-stub factory (NOT an LLM) ───────────────────────
def _fixed_verdict_judge(verdict: dict):
    """Return a deterministic judge_fn that ALWAYS returns ``verdict`` and records
    every packet it was handed in a list (so a test can also inspect calls without
    going through engine.judge_packets()). The judge_fn is a plain callable — §13
    fixed-verdict STUB, no model, no I/O."""
    captured: list[dict] = []

    def judge_fn(packet: dict) -> dict:
        captured.append(packet)
        return dict(verdict)

    judge_fn.captured = captured     # type: ignore[attr-defined]
    return judge_fn


# ─────────────────────────────────────────────────────────────────────────────
# I.1  seen 1x -> stays a HIDDEN candidate
# ─────────────────────────────────────────────────────────────────────────────

def test_seen_once_stays_hidden_candidate() -> None:
    """§6-I / §11B-1 / §4: ONE in-evidence observation makes a
    (synonym, from_token, to_token) candidate a CANDIDATE — NOT promoted — and a
    candidate is HIDDEN: promoted_synonyms() does NOT contain it. EXPECTED: status
    == candidate, that candidate's observation_count == 1, promoted_synonyms() ==
    {} (candidate hidden), the group resolution is still OPEN."""
    eng = SynonymFoldEngine()
    res = eng.observe("topline", "revenue", event_key="AAPL:Q1",
                      evidence_text="topline grew on strong demand")

    assert res.counted is True
    assert res.status == STATUS_CANDIDATE
    assert eng.status_of("synonym", "topline", "revenue") == STATUS_CANDIDATE
    assert eng.observation_count("synonym", "topline", "revenue") == 1
    # Candidate is HIDDEN — never returned (§F.10 v2 Fix #2 mirror).
    assert eng.promoted_synonyms() == {}
    assert "topline" not in eng.promoted_synonyms()
    assert eng.resolution_of("synonym", "topline") == RESOLUTION_OPEN
    # N=2 is the hardcoded eligibility threshold (§4).
    assert PROMOTION_THRESHOLD == 2


# ─────────────────────────────────────────────────────────────────────────────
# I.2  2 DISTINCT events, NO competitor -> PROMOTED DIRECTLY (no judge)
# ─────────────────────────────────────────────────────────────────────────────

def test_two_distinct_events_promotes_directly_no_judge() -> None:
    """§6-I / §11B-2 / §4: 2 DISTINCT event_keys (each with from_token in evidence)
    for the SOLE candidate (no competitor) PROMOTE it DIRECTLY — no judge call —
    and promoted_synonyms() then contains from_token -> to_token. Also asserts a
    SAME event_key re-observed does NOT double-count (event-level SET dedup, §4):
    a 1st event + a duplicate of it stays a candidate; only a 2nd DISTINCT event
    promotes. EXPECTED final: status == promoted, count == 2, promoted_synonyms()
    == {turnover: revenue}, resolution == promoted, NO judge packet recorded."""
    eng = SynonymFoldEngine()

    r1 = eng.observe("turnover", "revenue", event_key="AAPL:Q1",
                     evidence_text="turnover rose")
    assert r1.status == STATUS_CANDIDATE
    assert eng.observation_count("synonym", "turnover", "revenue") == 1

    # Same event_key again -> deduped, NOT counted, still a candidate.
    r_dup = eng.observe("turnover", "revenue", event_key="AAPL:Q1",
                        evidence_text="turnover rose again same filing")
    assert r_dup.counted is False
    assert r_dup.reason == "duplicate_event"
    assert eng.observation_count("synonym", "turnover", "revenue") == 1
    assert eng.status_of("synonym", "turnover", "revenue") == STATUS_CANDIDATE
    assert eng.promoted_synonyms() == {}     # still hidden after a duplicate

    # 2nd DISTINCT event -> reaches N=2 -> PROMOTED DIRECTLY (sole candidate).
    r2 = eng.observe("turnover", "revenue", event_key="NVDA:Q2",
                     evidence_text="turnover climbed")
    assert r2.counted is True
    assert r2.status == STATUS_PROMOTED
    assert r2.judged is False                # NO judge — no competitor
    assert eng.status_of("synonym", "turnover", "revenue") == STATUS_PROMOTED
    assert eng.observation_count("synonym", "turnover", "revenue") == 2
    assert eng.promoted_synonyms() == {"turnover": "revenue"}
    assert eng.resolution_of("synonym", "turnover") == RESOLUTION_PROMOTED
    assert eng.judge_packets() == []         # the judge was never consulted


# ─────────────────────────────────────────────────────────────────────────────
# I.3  evidence-absent -> NOT counted
# ─────────────────────────────────────────────────────────────────────────────

def test_evidence_absent_not_counted() -> None:
    """§6-I / §11B-3 / §4: an observation whose from_token does NOT appear in the
    event's evidence_text is NOT counted — the event_key is not added, the count
    does not advance, status stays candidate. EXPECTED: after a 1st in-evidence
    obs (count 1, candidate), a 2nd obs with from_token ABSENT from evidence leaves
    count at 1 and status candidate (NOT promoted), and promoted_synonyms() empty.
    A later 2nd obs WITH evidence then promotes — proving only the absent one was
    skipped."""
    eng = SynonymFoldEngine()

    eng.observe("topline", "revenue", event_key="AAPL:Q1",
                evidence_text="topline expanded")
    assert eng.observation_count("synonym", "topline", "revenue") == 1

    # from_token "topline" is ABSENT from this evidence -> NOT counted.
    res = eng.observe("topline", "revenue", event_key="NVDA:Q2",
                      evidence_text="sales were higher this period")
    assert res.counted is False
    assert res.reason == "evidence_absent"
    assert eng.observation_count("synonym", "topline", "revenue") == 1   # not advanced
    assert eng.status_of("synonym", "topline", "revenue") == STATUS_CANDIDATE
    assert eng.promoted_synonyms() == {}

    # A genuine 2nd in-evidence event DOES promote (the absent one was the only skip).
    eng.observe("topline", "revenue", event_key="MSFT:Q3",
                evidence_text="topline accelerated")
    assert eng.observation_count("synonym", "topline", "revenue") == 2
    assert eng.status_of("synonym", "topline", "revenue") == STATUS_PROMOTED


def test_evidence_absent_first_obs_leaves_no_record_v11_4() -> None:
    """§11B-3 v11-4 (ChatGPT-found, tester-fixed): an evidence-absent observation
    must leave NO record (the evidence gate runs BEFORE record creation), so a
    zero-evidence guess can never PIN a meaning or spawn a phantom competing
    candidate. EXPECTED: obs1 (uptake->revenue, evidence ABSENT) creates NOTHING —
    the candidate does NOT exist afterwards (status None, count 0, candidates_for
    empty); a later obs2 (uptake->demand, evidence PRESENT, a DIFFERENT to_token)
    is LEARNED as the ONLY candidate. Anti-recurrence guard for the
    create-before-evidence-gate bug. (UPDATED to v11-4: assert the candidate does
    NOT EXIST, not merely count 0.)"""
    eng = SynonymFoldEngine()
    r1 = eng.observe("uptake", "revenue", event_key="E1",
                     evidence_text="no relevant token in this evidence")
    assert r1.reason == "evidence_absent"
    # NO record created — the candidate does NOT exist (was the v11-4 bug).
    assert eng.status_of("synonym", "uptake", "revenue") is None
    assert eng.observation_count("synonym", "uptake", "revenue") == 0
    assert eng.candidates_for("synonym", "uptake") == {}   # nothing seeded at all

    r2 = eng.observe("uptake", "demand", event_key="E2",
                     evidence_text="uptake clearly rose")
    assert r2.counted is True and r2.reason is None        # the REAL synonym is LEARNED
    assert eng.observation_count("synonym", "uptake", "demand") == 1
    # Only ONE candidate exists — the absent revenue guess left no phantom.
    assert eng.candidates_for("synonym", "uptake") == {"demand": STATUS_CANDIDATE}


# ─────────────────────────────────────────────────────────────────────────────
# I.4  conflicting to_token -> COMPETING CANDIDATE (NOT first-wins)  [FLIPPED]
# ─────────────────────────────────────────────────────────────────────────────

def test_second_to_token_coexists_as_competing_candidate() -> None:
    """§6-I / §11B-4 / §4 (conflict semantics LOCKED 2026-05-29 — NOT first-wins).
    FLIPS the OLD "2nd to_token rejected / meaning_conflict" test. A 2nd, DIFFERENT
    to_token for the same (synonym, from_token) is NOT rejected — it COEXISTS as a
    separate competing candidate, and both accumulate INDEPENDENTLY (each its OWN
    count). EXPECTED: observe uptake->demand (1 event) and uptake->consumption (1
    event), each in-evidence + distinct events -> BOTH candidates exist; the 2nd is
    NOT flagged rejected; neither is promoted (each still sub-N=2); counts are
    independent (1 each)."""
    eng = SynonymFoldEngine()

    r1 = eng.observe("uptake", "demand", event_key="AAPL:Q1",
                     evidence_text="datacenter uptake was strong")
    # 2nd DIFFERENT to_token, distinct event, in-evidence -> COMPETING candidate.
    r2 = eng.observe("uptake", "consumption", event_key="NVDA:Q2",
                     evidence_text="uptake of capacity rose")

    # Neither was rejected; both COUNTED and COEXIST (NOT first-wins).
    assert r1.counted is True and r1.reason is None
    assert r2.counted is True and r2.reason is None       # NOT rejected (the FLIP)
    assert eng.candidates_for("synonym", "uptake") == {
        "demand": STATUS_CANDIDATE,
        "consumption": STATUS_CANDIDATE,
    }
    # Independent counts — each candidate has its OWN event set.
    assert eng.observation_count("synonym", "uptake", "demand") == 1
    assert eng.observation_count("synonym", "uptake", "consumption") == 1
    # Neither promoted yet (each sub-N=2); nothing folded; group still OPEN.
    assert eng.promoted_synonyms() == {}
    assert eng.resolution_of("synonym", "uptake") == RESOLUTION_OPEN
    assert eng.judge_packets() == []                      # no eligible competitor yet


# ─────────────────────────────────────────────────────────────────────────────
# I.5  promotion attempt WITH competitors -> FREEZE + judge_fn CALLED
# ─────────────────────────────────────────────────────────────────────────────

def test_promotion_attempt_with_competitors_freezes_and_calls_judge() -> None:
    """§4 / §13 (confirmed rule — NO first-past-the-post): with >= 2 COMPETING
    candidates, an eligible one is NOT auto-promoted — promotion FREEZES and the
    injectable judge_fn is INVOKED. The competitors are INTERLEAVED so both coexist
    BEFORE either reaches N=2 (otherwise the first would promote as a sole meaning).
    EXPECTED: the LATEST packet has the LOCKED §13 shape and its candidates are ONLY
    the N=2-cleared competitors (each with observation_count + sample_evidence);
    demand did NOT silently win by reaching N=2 first (default defer -> NONE
    promoted, group FROZEN)."""
    judge = _fixed_verdict_judge({"decision": "defer", "to_token": None,
                                  "reason": "need more evidence"})
    eng = SynonymFoldEngine(judge_fn=judge)
    _seed_two_competitors_interleaved(eng)

    # The judge WAS invoked; the LATEST call carries BOTH N=2-cleared competitors.
    assert len(judge.captured) >= 1
    packet = eng.judge_packets()[-1]
    assert set(packet.keys()) == {"kind", "from_token", "candidates"}
    assert packet["kind"] == "synonym"
    assert packet["from_token"] == "uptake"
    by_to = {c["to_token"]: c for c in packet["candidates"]}
    assert set(by_to) == {"demand", "consumption"}        # both N=2-cleared
    for cand in packet["candidates"]:
        assert set(cand.keys()) == {"to_token", "observation_count",
                                    "sample_evidence"}
        assert cand["observation_count"] == 2
        assert isinstance(cand["sample_evidence"], list)
        assert len(cand["sample_evidence"]) >= 1
    # NO first-past-the-post: demand did NOT auto-win by reaching N=2 first; the
    # default defer verdict -> NONE promoted, group FROZEN.
    assert eng.promoted_synonyms() == {}
    assert "demand" not in eng.promoted_synonyms()
    assert eng.is_frozen("synonym", "uptake") is True


# ─────────────────────────────────────────────────────────────────────────────
# I.6  VERDICT PATHS — promote / no_global_rule / defer
# ─────────────────────────────────────────────────────────────────────────────

def _judge_defer_until_two(verdict: dict):
    """A deterministic judge_fn that DEFERS while the packet has < 2 candidates, then
    returns ``verdict`` once >= 2 N=2-cleared competitors are present. Lets a
    fixed-outcome test exercise a verdict path WITH two eligible competitors under the
    streaming engine (1st eligible -> 1-candidate call -> defer; 2nd eligible ->
    2-candidate call -> the target verdict). Captures every packet. Still a plain
    deterministic callable — §13 stub, NOT a model."""
    captured: list[dict] = []

    def judge_fn(packet: dict) -> dict:
        captured.append(packet)
        if len(packet["candidates"]) >= 2:
            return dict(verdict)
        return {"decision": "defer", "to_token": None, "reason": "await 2nd eligible"}

    judge_fn.captured = captured     # type: ignore[attr-defined]
    return judge_fn


def _seed_two_competitors_interleaved(eng) -> None:
    """Seed uptake with TWO competing meanings INTERLEAVED so BOTH coexist BEFORE
    either reaches N=2 — required by the confirmed NO-first-past-the-post rule (a
    sole meaning would otherwise auto-promote at N=2). Order: demand E1, consumption
    E2 (both count 1, group now contested), demand E3 (demand -> N=2 -> judge call #1,
    packet=[demand]), consumption E4 (consumption -> N=2, group frozen -> re-judge
    call #2, packet=[demand, consumption]). Each obs is in-evidence + a distinct
    event_key."""
    eng.observe("uptake", "demand", event_key="E1", evidence_text="uptake rose")
    eng.observe("uptake", "consumption", event_key="E2",
                evidence_text="uptake of capacity rose")
    eng.observe("uptake", "demand", event_key="E3", evidence_text="uptake climbed")
    eng.observe("uptake", "consumption", event_key="E4",
                evidence_text="uptake of capacity expanded")


def test_verdict_promote_folds_chosen_only() -> None:
    """§13 decision=="promote": the judge approves ONE candidate -> it folds, the
    OTHER does NOT. EXPECTED: stub returns {promote, to_token: demand} -> uptake
    folds to demand (status promoted), consumption is the loser (status rejected),
    promoted_synonyms() == {uptake: demand} (EXACTLY ONE per key), resolution ==
    promoted."""
    judge = _judge_defer_until_two({"decision": "promote", "to_token": "consumption",
                                    "reason": "consumption is the global metric"})
    eng = SynonymFoldEngine(judge_fn=judge)
    _seed_two_competitors_interleaved(eng)

    assert eng.promoted_synonyms() == {"uptake": "consumption"}   # EXACTLY one per key
    assert eng.status_of("synonym", "uptake", "consumption") == STATUS_PROMOTED
    assert eng.resolution_of("synonym", "uptake") == RESOLUTION_PROMOTED
    assert "demand" not in eng.promoted_synonyms()               # loser not promoted
    # loser NOT discarded/rejected -> its record + count are PRESERVED (no-poison).
    assert eng.observation_count("synonym", "uptake", "demand") == 2


def test_verdict_no_global_rule_folds_none() -> None:
    """§13 decision=="no_global_rule": token is context-dependent -> NO global
    synonym -> promote NONE (driver-level reuse only). EXPECTED: stub returns
    {no_global_rule} -> NEITHER candidate folds, promoted_synonyms() == {},
    resolution == no_global_rule (NOT frozen — it is a resolved no-fold)."""
    judge = _judge_defer_until_two({"decision": "no_global_rule", "to_token": None,
                                    "reason": "context-dependent"})
    eng = SynonymFoldEngine(judge_fn=judge)
    _seed_two_competitors_interleaved(eng)

    assert eng.promoted_synonyms() == {}                       # NONE fold
    assert eng.resolution_of("synonym", "uptake") == RESOLUTION_NO_GLOBAL_RULE
    assert eng.is_frozen("synonym", "uptake") is False         # resolved, not frozen
    # both competitors preserved (no-poison).
    assert eng.observation_count("synonym", "uptake", "demand") == 2
    assert eng.observation_count("synonym", "uptake", "consumption") == 2


def test_verdict_defer_folds_none_and_stays_frozen() -> None:
    """§13 decision=="defer": keep the (kind, from_token) FROZEN, re-judge when
    more evidence arrives -> promote NONE (yet). EXPECTED: stub returns {defer} ->
    NEITHER candidate folds, promoted_synonyms() == {}, resolution == frozen,
    is_frozen() True."""
    judge = _fixed_verdict_judge({"decision": "defer", "to_token": None,
                                  "reason": "not enough signal"})
    eng = SynonymFoldEngine(judge_fn=judge)
    _seed_two_competitors_interleaved(eng)

    assert eng.promoted_synonyms() == {}                       # NONE fold (yet)
    assert eng.resolution_of("synonym", "uptake") == RESOLUTION_FROZEN
    assert eng.is_frozen("synonym", "uptake") is True


def test_default_judge_stub_defers_deterministically() -> None:
    """§13: with NO judge injected the DEFAULT deterministic stub DEFERS, so a
    contested promotion attempt freezes the key (the conservative no-fold default)
    — the engine is deterministic without an injected judge. EXPECTED: two eligible
    competitors -> default stub -> NONE promoted, group FROZEN."""
    eng = SynonymFoldEngine()       # no judge_fn -> default defer stub
    _seed_two_competitors_interleaved(eng)

    assert eng.promoted_synonyms() == {}
    assert eng.is_frozen("synonym", "uptake") is True


# ─────────────────────────────────────────────────────────────────────────────
# I.7  N=2 ELIGIBILITY GATE (code, pre-judge) — judge sees ONLY N=2-cleared
# ─────────────────────────────────────────────────────────────────────────────

def test_eligibility_gate_excludes_sub_n2_competitor_from_packet() -> None:
    """§4 / §13 (confirmed rule): the N=2 eligibility gate is CODE, run BEFORE the
    judge — the judge NEVER sees a sub-N=2 one-off. With ONE eligible competitor
    (demand, N=2) and ONE sub-N=2 competitor (consumption, N=1), the group is
    CONTESTED (>= 2 to_tokens) so demand does NOT auto-promote (no first-past-the-
    post); the judge IS called but its packet contains ONLY the N=2-cleared demand
    (consumption EXCLUDED). EXPECTED: judged True, packet candidates == {demand}
    (consumption excluded), default defer -> NONE promoted, consumption preserved as
    a sub-N=2 candidate (never promoted)."""
    judge = _fixed_verdict_judge({"decision": "defer", "to_token": None,
                                  "reason": "inspect packet"})
    eng = SynonymFoldEngine(judge_fn=judge)

    eng.observe("uptake", "demand", event_key="E1", evidence_text="uptake rose")
    eng.observe("uptake", "consumption", event_key="E2",
                evidence_text="uptake of capacity rose")     # the sub-N=2 competitor
    r = eng.observe("uptake", "demand", event_key="E3",
                    evidence_text="uptake climbed")           # demand -> N=2 (contested)

    # CONTESTED -> NOT auto-promoted; judge called with ONLY the N=2-cleared demand.
    assert r.judged is True
    assert len(judge.captured) == 1
    packet = eng.judge_packets()[-1]
    to_tokens = {c["to_token"] for c in packet["candidates"]}
    assert to_tokens == {"demand"}                            # ONLY N=2-cleared
    assert "consumption" not in to_tokens                     # sub-N=2 EXCLUDED
    assert eng.promoted_synonyms() == {}                      # defer -> none promoted
    assert eng.is_frozen("synonym", "uptake") is True
    # consumption (sub-N=2) preserved, never promoted.
    assert eng.observation_count("synonym", "uptake", "consumption") == 1
    assert eng.status_of("synonym", "uptake", "consumption") == STATUS_CANDIDATE


def test_eligibility_gate_packet_contains_only_n2_cleared() -> None:
    """§4 / §13: when TWO competitors are eligible (N=2) and a THIRD is sub-N=2,
    the judge packet's candidate list EXCLUDES the sub-N=2 one — the judge receives
    ONLY N=2-cleared competitors. EXPECTED: demand(N=2) + consumption(N=2) +
    bookings(N=1) -> packet candidates == {demand, consumption} (bookings absent);
    a sub-N=2 candidate is never promoted."""
    judge = _fixed_verdict_judge({"decision": "defer", "to_token": None,
                                  "reason": "inspect packet"})
    eng = SynonymFoldEngine(judge_fn=judge)

    eng.observe("uptake", "demand", event_key="E1", evidence_text="uptake rose")
    eng.observe("uptake", "consumption", event_key="E3",
                evidence_text="uptake of capacity rose")       # competitor (contested)
    eng.observe("uptake", "bookings", event_key="E5",
                evidence_text="uptake of seats rose")          # sub-N=2 one-off
    eng.observe("uptake", "demand", event_key="E2",
                evidence_text="uptake climbed")                # demand -> N=2
    eng.observe("uptake", "consumption", event_key="E4",
                evidence_text="uptake of capacity expanded")   # consumption -> N=2 (re-judge)

    packet = eng.judge_packets()[-1]
    to_tokens = {c["to_token"] for c in packet["candidates"]}
    assert to_tokens == {"demand", "consumption"}              # bookings EXCLUDED
    assert "bookings" not in to_tokens                         # sub-N=2 not in packet
    # bookings (sub-N=2) is never promoted; it remains a hidden candidate.
    assert eng.observation_count("synonym", "uptake", "bookings") == 1
    assert eng.status_of("synonym", "uptake", "bookings") == STATUS_CANDIDATE


# ─────────────────────────────────────────────────────────────────────────────
# I.8  LOSER LATER REACHES N=2 — no-poison: a non-promoted competitor keeps
#      accumulating its OWN events (proves it was NOT first-wins-rejected)
# ─────────────────────────────────────────────────────────────────────────────

def test_loser_competitor_keeps_accumulating_to_n2_v11_4() -> None:
    """§4 / v11-4 (no-poison) + the confirmed NO-first-past-the-post rule: the first
    meaning to reach N=2 in a CONTESTED group does NOT silently win, and a competing
    candidate is NEVER first-wins-rejected — it keeps accumulating its OWN events.
    EXPECTED: demand reaches N=2 first but (contested) is NOT auto-promoted; the
    'loser' consumption keeps accumulating to N=2 (count == 2); the latest judge
    packet then lists BOTH; default defer -> NONE promoted (no silent winner)."""
    judge = _fixed_verdict_judge({"decision": "defer", "to_token": None,
                                  "reason": "no silent winner"})
    eng = SynonymFoldEngine(judge_fn=judge)

    eng.observe("uptake", "demand", event_key="E1", evidence_text="uptake rose")
    eng.observe("uptake", "consumption", event_key="E2",
                evidence_text="uptake of capacity rose")       # competitor appears (N=1)
    eng.observe("uptake", "demand", event_key="E3",
                evidence_text="uptake climbed")                # demand -> N=2, CONTESTED
    # NO first-past-the-post: demand did NOT auto-win despite reaching N=2 first.
    assert eng.promoted_synonyms() == {}
    assert "demand" not in eng.promoted_synonyms()
    assert eng.observation_count("synonym", "uptake", "consumption") == 1   # not zeroed/rejected

    # The 'loser' keeps accumulating its OWN events (v11-4 no-poison) -> reaches N=2.
    eng.observe("uptake", "consumption", event_key="E4",
                evidence_text="uptake of capacity expanded")   # consumption -> N=2 (re-judge)
    assert eng.observation_count("synonym", "uptake", "consumption") == 2

    # The re-judge fires with BOTH eligible (proves consumption was never discarded).
    packet = eng.judge_packets()[-1]
    assert {c["to_token"] for c in packet["candidates"]} == {"demand", "consumption"}
    assert eng.promoted_synonyms() == {}                       # still no silent winner
    assert eng.observation_count("synonym", "uptake", "demand") == 2


# ─────────────────────────────────────────────────────────────────────────────
# I.9  plurals/acronyms NOT learned (stay static §F.3/§F.4)
# ─────────────────────────────────────────────────────────────────────────────

def test_plurals_and_acronyms_not_learned() -> None:
    """§11B-5 / §4 ("synonyms only (plurals/acronyms stay static §F.3/§F.4)"):
    observe() with kind in {plural, acronym} does NOT learn/promote even with 2
    distinct in-evidence events; the observation is NOT learnable; no candidate
    record is created for a non-synonym kind; promoted_synonyms() never carries it;
    and the STATIC plural_map/acronym_map in a rebuilt snapshot are UNCHANGED vs
    the no-arg snapshot. EXPECTED: no promotion for plural/acronym kinds, no
    candidate records, snapshot plural_map/acronym_map identical to the static
    seed."""
    eng = SynonymFoldEngine()

    # Two distinct in-evidence PLURAL observations — would promote IF learnable.
    eng.observe("sale", "sales", event_key="AAPL:Q1",
                evidence_text="sale of units", kind="plural")
    p2 = eng.observe("sale", "sales", event_key="NVDA:Q2",
                     evidence_text="sale closed", kind="plural")
    # Two distinct in-evidence ACRONYM observations — would promote IF learnable.
    eng.observe("gm", "gross_margin", event_key="AAPL:Q1",
                evidence_text="gm expanded", kind="acronym")
    a2 = eng.observe("gm", "gross_margin", event_key="NVDA:Q2",
                     evidence_text="gm expanded", kind="acronym")

    # Neither is learnable: reason non_learnable_kind, no candidate created.
    assert p2.counted is False and p2.reason == "non_learnable_kind"
    assert a2.counted is False and a2.reason == "non_learnable_kind"
    assert eng.candidates_for("plural", "sale") == {}
    assert eng.candidates_for("acronym", "gm") == {}
    assert eng.status_of("plural", "sale", "sales") is None
    assert eng.status_of("acronym", "gm", "gross_margin") is None
    assert eng.observation_count("plural", "sale", "sales") == 0
    assert eng.observation_count("acronym", "gm", "gross_margin") == 0
    # promoted_synonyms() (synonyms only) never carries a plural/acronym from_token.
    assert eng.promoted_synonyms() == {}
    assert "sale" not in eng.promoted_synonyms()
    assert "gm" not in eng.promoted_synonyms()

    # The STATIC plural/acronym maps are UNCHANGED by the engine: a snapshot built
    # WITH promoted_synonyms() has the same plural_map/acronym_map as the no-arg one.
    base = build_vocab_snapshot()
    rebuilt = build_vocab_snapshot(promoted_synonyms=eng.promoted_synonyms())
    assert rebuilt.plural_map == base.plural_map
    assert rebuilt.acronym_map == base.acronym_map
    # And the static §F.3/§F.4 entries are intact (sale->sales, gm->gross_margin).
    assert rebuilt.plural_map["sale"] == "sales"
    assert rebuilt.acronym_map["gm"] == "gross_margin"


# ─────────────────────────────────────────────────────────────────────────────
# I.10  THE WIRING TEST — promote -> rebuild -> fold (production path, §11B line 556)
# ─────────────────────────────────────────────────────────────────────────────

def test_wiring_promote_rebuild_fold_production_path() -> None:
    """§11B wiring point (line 556-559) — the round-3 lesson: prove the PRODUCTION
    path, not just the in-memory engine. A promoted synonym must feed
    build_vocab_snapshot()'s synonym_map on the NEXT build so canonicalize folds it
    automatically. (NO competitor here, so it promotes DIRECTLY — no judge.)

    Steps:
      (a) BEFORE promotion: build vocab with the (empty) promoted_synonyms() and
          assert canonicalize('datacenter_uptake', vocab1) does NOT fold to a
          *_demand form — 'uptake' is not yet a known synonym, so the name cannot
          resolve a metric slot and canonicalize REJECTS it.
      (b) Promote uptake->demand via 2 DISTINCT events, each with 'uptake' in
          evidence (sole candidate -> direct promotion, no judge).
      (c) REBUILD: vocab2 = build_vocab_snapshot(promoted_synonyms=
          engine.promoted_synonyms()).
      (d) ASSERT canonicalize('datacenter_uptake', vocab2) == 'datacenter_demand'.
    """
    eng = SynonymFoldEngine()

    # (a) BEFORE promotion — empty promoted dict; 'uptake' is unknown, does NOT
    #     fold to a *_demand form. canonicalize must NOT return 'datacenter_demand'.
    vocab1 = build_vocab_snapshot(promoted_synonyms=eng.promoted_synonyms())
    assert eng.promoted_synonyms() == {}                # nothing promoted yet
    before = canonicalize("datacenter_uptake", vocab1)
    assert before != "datacenter_demand"                # NOT yet folded
    # 'uptake' is not a synonym/metric -> the name cannot resolve (no metric slot).
    assert isinstance(before, Rejection)

    # (b) Promote uptake -> demand via 2 DISTINCT events, each with 'uptake' present.
    #     Sole candidate (no competitor) -> PROMOTES DIRECTLY (no judge call).
    eng.observe("uptake", "demand", event_key="AAPL:Q1",
                evidence_text="datacenter uptake was strong")
    r2 = eng.observe("uptake", "demand", event_key="NVDA:Q2",
                     evidence_text="uptake of new gpus accelerated")
    assert r2.judged is False                                 # no competitor
    assert eng.promoted_synonyms() == {"uptake": "demand"}    # now promoted
    assert eng.judge_packets() == []

    # (c) REBUILD the snapshot from the freshly-promoted synonyms.
    vocab2 = build_vocab_snapshot(promoted_synonyms=eng.promoted_synonyms())
    assert vocab2.synonym_map.get("uptake") == "demand"       # merged into the map

    # (d) Now canonicalize folds uptake -> demand (datacenter=object, demand=metric).
    after = canonicalize("datacenter_uptake", vocab2)
    assert after == "datacenter_demand"                       # promote->rebuild->fold

    # Static seed synonyms still work after the merge (no regression on §F.2).
    assert vocab2.synonym_map["topline"] == "revenue"


# ─────────────────────────────────────────────────────────────────────────────
# I.11  LATE-RIVAL / INCUMBENT — temporal first-wins must NOT stick
#       (CombinedPlan §385, confirmed 2026-05-29): a rival that INDEPENDENTLY
#       clears N=2 against an ALREADY-PROMOTED incumbent RE-OPENS the group.
# ─────────────────────────────────────────────────────────────────────────────

def test_late_rival_reopens_promoted_incumbent_and_unpromotes() -> None:
    """THE incumbent sequence: demand E1, E2 -> demand promotes ALONE (sole, no
    competitor yet). THEN consumption E3, E4 -> consumption INDEPENDENTLY reaches
    N=2 -> RE-OPEN: judge_fn called with [demand, consumption]; default defer ->
    demand is UN-PROMOTED, group FROZEN. EXPECTED (the fix): the fold is truly EMPTY
    (promoted_synonyms() == {} — demand GONE, not merely frozen), and the latest
    judge packet lists BOTH incumbent + rival. Proves arrival order does NOT decide
    the winner."""
    eng = SynonymFoldEngine()       # no judge_fn -> default defer stub

    # demand promotes ALONE at N=2 (no rival yet).
    eng.observe("uptake", "demand", event_key="E1", evidence_text="uptake rose")
    eng.observe("uptake", "demand", event_key="E2", evidence_text="uptake climbed")
    assert eng.promoted_synonyms() == {"uptake": "demand"}     # incumbent promoted
    assert eng.judge_packets() == []                           # sole -> no judge

    # late RIVAL independently clears N=2 -> RE-OPEN -> judge([demand, consumption]).
    eng.observe("uptake", "consumption", event_key="E3",
                evidence_text="uptake of capacity rose")
    eng.observe("uptake", "consumption", event_key="E4",
                evidence_text="uptake of capacity expanded")   # consumption -> N=2 (re-open)

    packet = eng.judge_packets()[-1]
    assert {c["to_token"] for c in packet["candidates"]} == {"demand", "consumption"}
    # THE FIX (nudge #1): default defer UN-PROMOTES the incumbent -> the fold is
    # EMPTY (not just frozen). Assert promoted_synonyms() == {} ("no promoted synonym").
    assert eng.promoted_synonyms() == {}
    assert eng.is_frozen("synonym", "uptake") is True
    assert eng.status_of("synonym", "uptake", "demand") != STATUS_PROMOTED


def test_more_evidence_on_incumbent_does_not_reopen() -> None:
    """Nudge #2: re-open ONLY on a DIFFERENT candidate crossing N=2. MORE evidence
    piling onto the ALREADY-PROMOTED incumbent must NOT re-open the group or re-call
    the judge. EXPECTED: demand promotes at N=2; a 3rd demand event leaves it
    promoted, count 3, judge never called."""
    eng = SynonymFoldEngine()
    eng.observe("uptake", "demand", event_key="E1", evidence_text="uptake rose")
    eng.observe("uptake", "demand", event_key="E2", evidence_text="uptake climbed")
    assert eng.promoted_synonyms() == {"uptake": "demand"}

    eng.observe("uptake", "demand", event_key="E3",
                evidence_text="uptake rose yet again")          # MORE evidence on incumbent
    assert eng.promoted_synonyms() == {"uptake": "demand"}     # still promoted
    assert eng.judge_packets() == []                           # NOT re-opened
    assert eng.observation_count("synonym", "uptake", "demand") == 3


def test_reopen_can_switch_winner() -> None:
    """Optional: re-open can CHANGE the winner, not just freeze. demand promotes
    alone; rival consumption clears N=2 -> RE-OPEN -> judge returns
    promote(consumption) -> promoted_synonyms() == {uptake: consumption} (winner
    SWITCHED; ONE per key; incumbent demand demoted). The judge fires ONLY on the
    re-open (the sole promotion took no judge)."""
    judge = _fixed_verdict_judge({"decision": "promote", "to_token": "consumption",
                                  "reason": "rival is the better global synonym"})
    eng = SynonymFoldEngine(judge_fn=judge)

    eng.observe("uptake", "demand", event_key="E1", evidence_text="uptake rose")
    eng.observe("uptake", "demand", event_key="E2", evidence_text="uptake climbed")
    assert eng.promoted_synonyms() == {"uptake": "demand"}     # incumbent
    assert eng.judge_packets() == []                           # sole -> no judge yet

    eng.observe("uptake", "consumption", event_key="E3",
                evidence_text="uptake of capacity rose")
    eng.observe("uptake", "consumption", event_key="E4",
                evidence_text="uptake of capacity expanded")   # rival N=2 -> re-open

    assert eng.promoted_synonyms() == {"uptake": "consumption"}   # winner SWITCHED
    assert eng.status_of("synonym", "uptake", "consumption") == STATUS_PROMOTED
    assert eng.status_of("synonym", "uptake", "demand") != STATUS_PROMOTED
    assert eng.resolution_of("synonym", "uptake") == RESOLUTION_PROMOTED
