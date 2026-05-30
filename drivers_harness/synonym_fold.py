"""In-memory N=2 synonym-promotion engine with an injectable judge seam
(TEST-SCAFFOLD, pure, no I/O, no LLM).

Pass-2 synonym-learner. A deterministic, offline stand-in for the ingestion-side
``:EquivalenceToken`` store (DriverOntology_Implementation.md §F.10 / Pattern A2)
— but WITHOUT any of that store's heavy ingestion machinery. Per
Harness_BuilderPrompt.md §4 (``synonym_fold.py`` contract, conflict semantics
LOCKED 2026-05-29 — NOT first-wins), §13 (the judge-seam INTERFACE), §11B
(Pass-2 deliverable + the ONE wiring point), and §6 bucket I, this builds ONLY
the in-memory engine:

  - PER-CANDIDATE store keyed ``(kind, from_token, to_token) -> {
    observation_event_keys: set, status, sample_evidence: list}``. COMPETING
    ``to_token``s for the SAME ``(kind, from_token)`` COEXIST — each accumulates
    its OWN distinct event_keys + a few sample evidence strings (§4: "competing
    candidate to_tokens MAY coexist, each with its OWN count"). This REPLACES the
    OLD one-record-per-``(kind, from_token)`` + first-wins ``meaning_conflict``
    reject entirely.
  - ELIGIBILITY (CODE, pre-judge): a candidate is eligible iff
    ``len(observation_event_keys) >= N`` with N=2 (§4: "N=2 = the ELIGIBILITY
    gate"). The judge NEVER sees a sub-N=2 one-off (§13: "the eligibility gate is
    code, run BEFORE the judge").
  - count an observation ONLY if ``from_token`` appears in that event's evidence
    text (§11B-3 / §6-I). v11-4 EVIDENCE GATE *BEFORE* CREATING ANY RECORD: an
    evidence-absent observation leaves NO record (no poison — a zero-evidence
    guess must not PIN a meaning).
  - event-level dedup: ``observation_event_keys`` is a SET, so the same
    ``event_key`` counts once; eligibility needs >= 2 DISTINCT event_keys.
  - SYNONYMS ONLY (§4: "synonyms only (plurals/acronyms stay static §F.3/§F.4)").
    An ``observe`` with kind != "synonym" is NOT learnable (recorded/ignored,
    never promoted).
  - CONFLICT (NOT first-wins, LOCKED 2026-05-29): a 2nd DIFFERENT ``to_token`` is
    NOT rejected — it coexists as a competing candidate accumulating its own
    count. On a PROMOTION ATTEMPT for ``(kind, from_token)``:
      * no competitor (only ONE candidate to_token) AND it is eligible
        -> PROMOTE it directly (no judge).
      * >= 2 distinct to_token candidates coexist -> FREEZE promotion + call the
        injectable judge seam ``judge_fn(packet) -> verdict`` (§13). The packet
        carries ONLY the N=2-cleared competitors; the verdict decision is one of
        ``{promote (one to_token), no_global_rule, defer}``.
  - ONE PROMOTED ``to_token`` per ``(kind, from_token)`` invariant; the judge may
    only approve a candidate that cleared N=2 (never a one-off).
  - ``promoted_synonyms()`` returns ONLY the ONE promoted synonym ``to_token`` per
    ``(kind, from_token)``; candidates / frozen / deferred / no_global_rule are
    HIDDEN (§F.10 v2 Fix #2 mirror).

INJECTABLE judge_fn (§13, mirror of ``emit_fn``): ``SynonymFoldEngine(
judge_fn=<callable>)``. A DEFAULT deterministic STUB is provided so the engine is
deterministic with NO judge injected — it returns ``{"decision": "defer", ...}``
(freeze, re-judge later). Tests inject their own fixed-verdict stub to force
promote / no_global_rule / defer. This is NOT an LLM (Pass 2): no
``claude_agent_sdk`` / ``claude -p`` / ``import anthropic`` / network. Pass 4
wires the real metered cheap-model call behind the SAME seam.

EXPLICITLY OUT OF SCOPE (Harness_BuilderPrompt.md §8 / §11B IGNORE-fence): the
§F.10 ``:EquivalenceToken`` heavy design — NO two-phase Cypher, NO race guards,
NO PIT / ``*_visible_at`` backdating, NO audit tables, NO Neo4j. In-memory only.
The promoted dict is PASSED IN to ``build_vocab_snapshot`` (the prod seam where
Neo4j rows arrive) — this module is NEVER imported by ``vocab_seed`` (PROD-CORE
purity, §9).

PURE: no I/O, network, clock, randomness, NO LLM. Deterministic — output depends
only on the sequence of ``observe`` calls + the injected ``judge_fn``. stdlib only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

# §4 / §11B / §13: N=2 ELIGIBILITY gate (>= 2 DISTINCT events). Hardcoded constant.
PROMOTION_THRESHOLD = 2

# §4: "synonyms only (plurals/acronyms stay static §F.3/§F.4)". Only this kind is
# ever learnable / promoted by the engine.
LEARNABLE_KIND = "synonym"

# How many sample evidence strings to retain per candidate for the judge packet.
SAMPLE_EVIDENCE_CAP = 3

# ── per-candidate status values (§4) ─────────────────────────────────────────
# A candidate's lifecycle, keyed (kind, from_token, to_token):
STATUS_CANDIDATE = "candidate"      # seen but not yet eligible (< N=2) -> HIDDEN
STATUS_ELIGIBLE = "eligible"        # cleared N=2, awaiting a promotion decision
STATUS_PROMOTED = "promoted"        # this candidate IS the one promoted synonym
STATUS_REJECTED = "rejected"        # a competitor that lost the judge decision

# ── resolution state of a (kind, from_token) GROUP (§13 verdict outcomes) ─────
# The promotion attempt outcome for the WHOLE (kind, from_token), distinct from a
# single candidate's status:
RESOLUTION_OPEN = "open"                  # no promotion attempt resolved it yet
RESOLUTION_PROMOTED = "promoted"          # one candidate promoted (direct or judge)
RESOLUTION_FROZEN = "frozen"              # judge returned defer -> stays frozen
RESOLUTION_NO_GLOBAL_RULE = "no_global_rule"  # judge: context-dependent, no fold


@dataclass
class CandidateRecord:
    """One ``(kind, from_token, to_token)`` candidate in the per-candidate store.

    Competing ``to_token`` candidates for the same ``(kind, from_token)`` each get
    their OWN CandidateRecord and accumulate INDEPENDENTLY (§4 conflict semantics,
    NOT first-wins). Mirrors the §F.10 LEARNING fields ONLY (no PIT anchors / no
    audit fields — out of scope per §8):
      - ``observation_event_keys``: SET of distinct counted event keys (the v4-2
        event-level dedup, in-memory). Eligible at len >= N=2.
      - ``sample_evidence``: up to ``SAMPLE_EVIDENCE_CAP`` evidence snippets, for
        the judge packet (§13 ``sample_evidence``).
      - ``status``: candidate -> eligible (>= N) -> promoted / rejected.
    """
    kind: str
    from_token: str
    to_token: str
    observation_event_keys: set = field(default_factory=set)
    sample_evidence: list = field(default_factory=list)
    status: str = STATUS_CANDIDATE

    @property
    def observation_count(self) -> int:
        return len(self.observation_event_keys)

    @property
    def is_eligible(self) -> bool:
        return len(self.observation_event_keys) >= PROMOTION_THRESHOLD


@dataclass(frozen=True)
class ObserveResult:
    """The outcome of a single ``observe`` call (returned for testability).

    ``counted``       — True iff the event_key was added (evidence present,
                        learnable kind, NEW event for this candidate). A SAME
                        event_key re-observed is ``counted=False`` (already in the
                        set) but NOT an error.
    ``status``        — the candidate's status AFTER this observation
                        ("candidate" / "eligible" / "promoted" / "rejected"), or
                        None if nothing was recorded (non-learnable kind, or
                        evidence-absent with NO record created).
    ``reason``        — why it did not count, else None. One of: "evidence_absent",
                        "duplicate_event", "non_learnable_kind".
    ``judged``        — True iff this observation TRIGGERED a judge_fn call (a
                        promotion attempt with competing candidates).
    ``resolution``    — the (kind, from_token) group resolution AFTER this observe
                        ("open" / "promoted" / "frozen" / "no_global_rule").
    """
    counted: bool
    status: str | None
    reason: str | None
    judged: bool
    resolution: str


def _default_judge_stub(packet: dict) -> dict:
    """The DEFAULT deterministic judge STUB (§13). With NO judge injected the
    engine stays deterministic: every contested promotion attempt DEFERS (freeze,
    re-judge when more evidence arrives) — the conservative no-fold default that
    never silently picks a winner. Returns the locked verdict shape."""
    return {"decision": "defer", "to_token": None, "reason": "stub-default"}


class SynonymFoldEngine:
    """In-memory N=2 synonym-promotion engine with an injectable judge seam
    (§4 / §11B / §13 / §6-I).

    Per-candidate, event-deduped, evidence-gated promotion of single-token
    synonyms. Construct (optionally inject ``judge_fn``), ``observe(...)`` a stream
    of producer observations, then feed ``promoted_synonyms()`` into
    ``vocab_seed.build_vocab_snapshot(promoted_synonyms=...)`` on the NEXT run so
    ``canonicalize`` folds them automatically (the §11B wiring point).
    """

    def __init__(
        self,
        judge_fn: Callable[[dict], dict] | None = None,
        promotion_threshold: int = PROMOTION_THRESHOLD,
    ) -> None:
        # PER-CANDIDATE store: (kind, from_token, to_token) -> CandidateRecord.
        # Competing to_tokens for the same (kind, from_token) COEXIST as separate
        # entries (§4, NOT first-wins).
        self._store: dict[tuple[str, str, str], CandidateRecord] = {}
        # GROUP resolution: (kind, from_token) -> one of RESOLUTION_*.
        self._resolution: dict[tuple[str, str], str] = {}
        # The injectable judge seam (§13). Default = deterministic defer stub.
        self._judge_fn: Callable[[dict], dict] = judge_fn or _default_judge_stub
        # Record of every packet sent to judge_fn (introspection surface, §13).
        self._judge_packets: list[dict] = []
        # N (=2). Configurable for tests, defaults to the hardcoded §4 constant.
        self._n = promotion_threshold

    # ── the one mutating entry point ─────────────────────────────────────────
    def observe(
        self,
        from_token: str,
        to_token: str,
        event_key: str,
        evidence_text: str,
        kind: str = "synonym",
    ) -> ObserveResult:
        """Record one producer observation that ``from_token`` means ``to_token``
        in the event identified by ``event_key`` (evidence ``evidence_text``).

        Rules (§4 / §11B / §13 / §6-I), applied in this fail-closed order:

          1. SYNONYMS ONLY — if ``kind != "synonym"`` (plural/acronym), do NOT
             learn/promote; ignore (record nothing learnable) and return
             ``non_learnable_kind`` (§4 / §F.3 / §F.4).
          2. v11-4 EVIDENCE GATE *BEFORE* CREATING ANY RECORD — count the
             observation ONLY if ``from_token`` (case-insensitive substring) is in
             ``evidence_text``. If ABSENT: do NOT count AND do NOT create/seed any
             candidate record (NO POISON — a zero-evidence guess must not PIN a
             meaning). Return ``evidence_absent``.
          3. PER-CANDIDATE accumulate — add ``event_key`` to the
             ``(kind, from_token, to_token)`` candidate's SET (dedup) and append
             evidence to its samples. A 2nd DIFFERENT ``to_token`` is NOT rejected
             — it is a SEPARATE competing candidate accumulating independently.
          4. PROMOTION ATTEMPT — if this candidate just became ELIGIBLE (>= N=2):
             * no competitor (only this to_token candidate) -> PROMOTE directly.
             * >= 2 distinct to_token candidates coexist -> FREEZE + call the
               injectable ``judge_fn(packet)``; apply its verdict.

        Returns an ``ObserveResult`` describing the outcome.
        """
        # 1. SYNONYMS ONLY — plurals/acronyms are never learned (§4 / §F.3 / §F.4).
        if kind != LEARNABLE_KIND:
            return ObserveResult(
                counted=False, status=None, reason="non_learnable_kind",
                judged=False, resolution=self._resolution_of(kind, from_token))

        group_key = (kind, from_token)

        # 2. v11-4 EVIDENCE GATE *BEFORE* CREATING ANY RECORD. Absent -> NO trace:
        #    no candidate is created/seeded, so a zero-evidence guess can never PIN
        #    a meaning or spawn a phantom competing candidate.
        if from_token.lower() not in evidence_text.lower():
            cand = self._store.get((kind, from_token, to_token))
            return ObserveResult(
                counted=False,
                status=(cand.status if cand is not None else None),
                reason="evidence_absent", judged=False,
                resolution=self._resolution_of(kind, from_token))

        # 3. PER-CANDIDATE accumulate. Create the candidate on its first EVIDENCED
        #    sighting. Competing to_tokens coexist (separate store keys).
        cand_key = (kind, from_token, to_token)
        cand = self._store.get(cand_key)
        if cand is None:
            cand = CandidateRecord(kind=kind, from_token=from_token,
                                   to_token=to_token)
            self._store[cand_key] = cand

        # event-level dedup — same event_key counts once.
        if event_key in cand.observation_event_keys:
            return ObserveResult(
                counted=False, status=cand.status, reason="duplicate_event",
                judged=False, resolution=self._resolution_of(kind, from_token))

        was_eligible = cand.is_eligible
        cand.observation_event_keys.add(event_key)
        if len(cand.sample_evidence) < SAMPLE_EVIDENCE_CAP:
            cand.sample_evidence.append(evidence_text)
        just_eligible = cand.is_eligible and not was_eligible
        if just_eligible and cand.status == STATUS_CANDIDATE:
            cand.status = STATUS_ELIGIBLE   # cleared N=2 (pre-judge)

        # 4. PROMOTION ATTEMPT — fire ONLY when THIS candidate JUST crossed N=2. A
        #    DIFFERENT to_token reaching N=2 is the trigger; MORE evidence piling onto
        #    an already-promoted incumbent does NOT re-fire (it is no longer "just"
        #    eligible), so re-open is rival-driven, not event-driven.
        #    RE-OPEN (CombinedPlan §385 / confirmed 2026-05-29 — fix the temporal
        #    first-wins hole): a NEW rival that INDEPENDENTLY clears N=2 RE-OPENS an
        #    already-PROMOTED group -> the judge re-decides [incumbent, rival] so
        #    arrival order never sticks (default defer un-promotes the incumbent).
        #    Only a NO_GLOBAL_RULE group stays terminal (a separate, lower-stakes
        #    question, intentionally left as-is).
        judged = False
        if just_eligible and self._resolution_of(
                kind, from_token) != RESOLUTION_NO_GLOBAL_RULE:
            judged = self._attempt_promotion(kind, from_token)

        return ObserveResult(
            counted=True, status=cand.status, reason=None, judged=judged,
            resolution=self._resolution_of(kind, from_token))

    # ── promotion + freeze + judge (§4 / §13) ────────────────────────────────
    def _attempt_promotion(self, kind: str, from_token: str) -> bool:
        """Run a promotion attempt for ``(kind, from_token)``. Returns True iff the
        injectable ``judge_fn`` was CALLED (i.e. competing candidates forced a
        freeze). Implements the §4 conflict resolution:

          * ELIGIBLE candidates (>= N=2) only — the eligibility gate is CODE, run
            BEFORE the judge (§13). Sub-N=2 candidates are NEVER eligible.
          * 0 eligible -> nothing to do.
          * exactly 1 eligible candidate (no competitor) -> PROMOTE it directly
            (no judge).
          * >= 2 eligible competing candidates -> FREEZE + call ``judge_fn`` with a
            packet carrying ONLY the N=2-cleared competitors; apply the verdict.
        """
        group_candidates = self._candidates(kind, from_token)
        eligible = [c for c in group_candidates if c.is_eligible]
        if not eligible:
            return False
        for c in eligible:
            if c.status == STATUS_CANDIDATE:
                c.status = STATUS_ELIGIBLE

        # CONFIRMED RULE (2026-05-29) — NO first-past-the-post. A group is CONTESTED
        # once >= 2 DISTINCT to_token candidates have been recorded (any count).
        # NOT contested (one meaning ever) + eligible -> PROMOTE DIRECTLY (no judge).
        if len(group_candidates) < 2:
            self._promote(kind, from_token, eligible[0].to_token)
            return False

        # CONTESTED -> auto-promotion STOPS; the first meaning to reach N=2 does NOT
        # silently win. FREEZE + call judge_fn with ONLY the N=2-cleared candidates
        # (eligibility gate is CODE, pre-judge — the judge never sees a sub-N=2
        # one-off, §13). That is the whole point of the judge seam.
        packet = {
            "kind": kind,
            "from_token": from_token,
            "candidates": [
                {
                    "to_token": c.to_token,
                    "observation_count": c.observation_count,
                    "sample_evidence": list(c.sample_evidence),
                }
                for c in eligible      # ONLY N=2-cleared competitors (§13)
            ],
        }
        self._judge_packets.append(packet)
        verdict = self._judge_fn(packet)
        self._apply_verdict(kind, from_token, packet, verdict)
        return True

    def _apply_verdict(
        self, kind: str, from_token: str, packet: dict, verdict: dict
    ) -> None:
        """Apply a ``judge_fn`` ``verdict`` (§13 locked shape) to ``(kind,
        from_token)``:
          * "promote" -> promote ``verdict["to_token"]`` IFF it is one of the
            ELIGIBLE packet candidates (else invalid -> promote NONE; surfaced via
            resolution staying frozen). EXACTLY ONE promoted per (kind, from_token).
          * "no_global_rule" -> promote NONE; mark resolved-no-global-rule (leave
            unfolded; driver-level reuse only).
          * "defer" -> promote NONE; keep the group FROZEN (a later observation
            that changes eligibility re-triggers the attempt / re-judge).
        """
        # RE-OPEN: a contested judge call re-decides the WHOLE group. Any candidate
        # currently PROMOTED (an incumbent that won a prior — possibly arrival-order
        # — decision) is demoted back to ELIGIBLE FIRST, so the verdict alone decides
        # and a temporal first-win never sticks. A non-promote verdict (defer /
        # no_global_rule) therefore leaves the fold EMPTY (promoted_synonyms() == {}),
        # not merely frozen. (One PROMOTED to_token per key.)
        for c in self._candidates(kind, from_token):
            if c.status == STATUS_PROMOTED:
                c.status = STATUS_ELIGIBLE

        decision = verdict.get("decision")
        eligible_to_tokens = {c["to_token"] for c in packet["candidates"]}

        if decision == "promote":
            chosen = verdict.get("to_token")
            if chosen in eligible_to_tokens:
                self._promote(kind, from_token, chosen)
            else:
                # Invalid verdict (to_token not an eligible candidate) — do NOT
                # promote; surface by keeping the group FROZEN for re-judging.
                self._resolution[(kind, from_token)] = RESOLUTION_FROZEN
        elif decision == "no_global_rule":
            self._resolution[(kind, from_token)] = RESOLUTION_NO_GLOBAL_RULE
        else:
            # "defer" (or any unknown decision) -> conservative freeze.
            self._resolution[(kind, from_token)] = RESOLUTION_FROZEN

    def _promote(self, kind: str, from_token: str, to_token: str) -> None:
        """Promote EXACTLY ONE ``to_token`` for ``(kind, from_token)``. The winner
        flips to ``promoted``. Per the confirmed rule, losing competitors are NOT
        rejected/discarded — their records + counts REMAIN intact (no-poison); they
        are simply absent from ``promoted_synonyms()`` (which returns only the
        PROMOTED one). One PROMOTED ``to_token`` per ``(kind, from_token)``."""
        for c in self._candidates(kind, from_token):
            if c.to_token == to_token:
                c.status = STATUS_PROMOTED
        self._resolution[(kind, from_token)] = RESOLUTION_PROMOTED

    # ── internal helpers ─────────────────────────────────────────────────────
    def _candidates(self, kind: str, from_token: str) -> list[CandidateRecord]:
        """All competing candidate records for ``(kind, from_token)`` (any status).
        Deterministic order: insertion order of the underlying dict."""
        return [
            rec for (k, f, _t), rec in self._store.items()
            if k == kind and f == from_token
        ]

    def _resolution_of(self, kind: str, from_token: str) -> str:
        return self._resolution.get((kind, from_token), RESOLUTION_OPEN)

    # ── read accessors (the wiring + introspection surface) ──────────────────
    def promoted_synonyms(self) -> dict[str, str]:
        """Return ``{from_token: to_token}`` for ONLY the ONE PROMOTED synonym per
        ``(kind, from_token)`` (kind == "synonym", status == "promoted").
        CANDIDATES / ELIGIBLE / FROZEN / DEFERRED / NO_GLOBAL_RULE / REJECTED
        entries are HIDDEN — never returned (§F.10 v2 Fix #2 mirror). This is the
        dict fed into ``build_vocab_snapshot(promoted_synonyms=...)`` (§11B wiring).

        Deterministic: iterates the store; carries single-token synonym folds only.
        """
        return {
            from_token: rec.to_token
            for (kind, from_token, _to), rec in self._store.items()
            if kind == LEARNABLE_KIND and rec.status == STATUS_PROMOTED
        }

    def candidates_for(self, kind: str, from_token: str) -> dict[str, str]:
        """Return ``{to_token: status}`` for every competing candidate of
        ``(kind, from_token)`` (any status), for tests asserting that competing
        candidates COEXIST (§4, NOT first-wins). Empty dict if none."""
        return {
            rec.to_token: rec.status
            for rec in self._candidates(kind, from_token)
        }

    def observation_count(
        self, kind: str, from_token: str, to_token: str
    ) -> int:
        """Return the number of DISTINCT counted events for the SPECIFIC candidate
        ``(kind, from_token, to_token)``, or 0 if no such candidate. Per-candidate
        (§4): each competing to_token has its OWN independent count. Lets a test
        assert evidence-absent / duplicate events do not advance a candidate's
        count, AND that a non-promoted "loser" keeps accumulating its own events
        (v11-4 no-poison)."""
        rec = self._store.get((kind, from_token, to_token))
        return rec.observation_count if rec is not None else 0

    def status_of(
        self, kind: str, from_token: str, to_token: str
    ) -> str | None:
        """Return the status of the SPECIFIC candidate
        ``(kind, from_token, to_token)`` ("candidate" / "eligible" / "promoted" /
        "rejected"), or None if no such candidate. Per-candidate (§4)."""
        rec = self._store.get((kind, from_token, to_token))
        return rec.status if rec is not None else None

    def is_frozen(self, kind: str, from_token: str) -> bool:
        """True iff the ``(kind, from_token)`` group is FROZEN (judge deferred,
        awaiting more evidence) — §13 "defer". Lets a test assert defer keeps the
        key frozen with NONE promoted."""
        return self._resolution_of(kind, from_token) == RESOLUTION_FROZEN

    def resolution_of(self, kind: str, from_token: str) -> str:
        """Return the ``(kind, from_token)`` GROUP resolution: "open" / "promoted"
        / "frozen" / "no_global_rule" (§13 verdict outcomes). Distinct from a
        single candidate's status — lets a test assert no_global_rule vs defer."""
        return self._resolution_of(kind, from_token)

    def judge_packets(self) -> list[dict]:
        """Return every packet that was sent to ``judge_fn`` (§13 introspection),
        in call order. A shallow copy so callers cannot mutate the engine's log.
        Lets a test assert the packet shape + that its candidates are ONLY the
        N=2-cleared competitors."""
        return list(self._judge_packets)
