"""S3 + S6 — validate emission shape, run the cleaner per item, return a
"would-write" decision  (PROD-CORE, pure given its args). Plus the pure
learner→writer adapter ``learner_to_writer_input`` (Harness_BuilderPrompt.md §5,
doubt #43).

run_one() does NOT write to any DB (S7 is out of scope). It runs S3
(validate_emission_shape) then per item B1..B10 (reuse_or_propose) + the §E
validators V1..V14, then S6 (assemble the decision dict in §5).

PROD-CORE purity (Harness_BuilderPrompt.md §9): run_one.py must NOT import
registry_fake or run_sequence. Imports only the foundation + validators + reuse
(all PROD-CORE). NO LLM, stdlib only.
"""

from __future__ import annotations

from typing import Optional

import validators as V
from reuse import reuse_or_propose
from vocab_seed import VocabSnapshot


# ─────────────────────────────────────────────────────────────────────────────
# learner_to_writer_input — the orchestrator-stamp adapter (S2.5)
# ─────────────────────────────────────────────────────────────────────────────

def learner_to_writer_input(learner_result: dict, context: dict) -> dict:
    """Adapt a LEARNER ``learner_result`` (``primary_driver`` +
    ``contributing_factors[]`` + ``propose_new_drivers[]``) into a WRITER
    ``emission JSON`` (Harness_BuilderPrompt.md §5 / doubt #43).

    The learner's tags carry NO ticker/envelope. The orchestrator-owned
    ``context`` (RunContext: ticker / source_id / source_type / pit_cutoff /
    run_id / result_path / source_catalog) is STAMPED onto each tag to build
    ``items[]``. ``learner_result`` alone cannot synthesize that envelope, so
    ``context`` is REQUIRED on this path.

    PURE: deterministic, no I/O. The emission's ``source_type`` is taken from
    ``context`` (defaulting to ``learner_result`` — the learner producer)."""
    if context is None:
        raise ValueError("learner_to_writer_input requires a RunContext (doubt #43)")

    ticker = context["ticker"]
    tags: list[dict] = []
    pd = learner_result.get("primary_driver")
    if pd:
        tags.append(pd)
    tags.extend(learner_result.get("contributing_factors", []) or [])

    items: list[dict] = []
    for tag in tags:
        item = {
            "ticker": ticker,
            "driver_name": tag.get("driver_name"),
            "driver_state": tag.get("driver_state"),
            "direction": tag.get("direction"),
            "evidence": list(tag.get("evidence", [])),
        }
        # exposure_role is a news-only PASSTHROUGH (E16) — carry it if present,
        # never compute/validate it in the harness (Harness_BuilderPrompt.md §5).
        if "exposure_role" in tag:
            item["exposure_role"] = tag["exposure_role"]
        # carry any producer-supplied evidence_text for the §D(e) gate (Pass 4).
        if "evidence_text" in tag:
            item["evidence_text"] = tag["evidence_text"]
        items.append(item)

    return {
        "source_id": context["source_id"],
        "source_type": context.get("source_type", "learner_result"),
        "pit_cutoff": context["pit_cutoff"],
        "run_id": context["run_id"],
        "result_path": context["result_path"],
        "source_catalog": list(context.get("source_catalog", [])),
        "items": items,
        "propose_new_drivers": list(learner_result.get("propose_new_drivers", []) or []),
    }


# ─────────────────────────────────────────────────────────────────────────────
# run_one — S3 shape pre-check, then per item B1..B10 + V1..V14, then S6 decision
# ─────────────────────────────────────────────────────────────────────────────

def run_one(emission_json: dict, registry, vocab: VocabSnapshot) -> dict:
    """S3 + S6: validate the emission shape, run the cleaner per item, return the
    decision dict (Harness_BuilderPrompt.md §5). NO DB write.

    decision = {
      items: [ {raw_name, canonical_name|null, status, reason|null,
                proposal_payload|null, aliases_added[], new_slot_tokens[]} ],
      accepted: [name...],
      rejected: [{name, reason}...],
      proposed: [name...],
      self_consistency: [{canonical_name, raw_names:[...]} ...]  (K53 collisions),
      summary: {accepted_count, rejected_count},
      shape_ok: bool,
      shape_errors: [...]
    }
    """
    shape_ok, shape_errors = V.validate_emission_shape(emission_json)
    decision: dict = {
        "items": [],
        "accepted": [],
        "rejected": [],
        "proposed": [],
        # K53 (FIX 4) — within ONE emission, two raw names that canonicalize to the
        # SAME canonical name are a self-consistency issue. Recorded here (observable
        # in the returned decision) so the writer never silently accepts two raw
        # names for one driver. NOTE: this is NOT V12 — V12 detects duplicate
        # proposal NAMES only; K53 is the canonical-collision check across items
        # and/or proposals.
        "self_consistency": [],
        "summary": {"accepted_count": 0, "rejected_count": 0},
        "shape_ok": shape_ok,
        "shape_errors": shape_errors,
    }
    if not shape_ok:
        # S3 gate failed — return the shape errors; no per-item processing.
        return decision

    items = emission_json.get("items", [])
    proposals = emission_json.get("propose_new_drivers", [])
    source_catalog = emission_json.get("source_catalog", [])
    propose_new_names = {p.get("name") for p in proposals}
    # index proposal payloads by name so a PROPOSE_NEW item carries its companion
    # fields into reuse_or_propose (template) + the emission-level validators.
    proposal_by_name = {p.get("name"): p for p in proposals}

    # ── emission-level validators (run once over the whole emission) ──
    # V12 — no two propose_new entries share a name.
    emission_v12_ok, emission_v12_reason = V.V12_no_duplicate_proposal(proposals)

    for it in items:
        raw_name = it.get("driver_name")
        evidence = it.get("evidence", [])
        driver_state = it.get("driver_state")
        direction = it.get("direction")

        record = {
            "raw_name": raw_name,
            "canonical_name": None,
            "status": None,
            "reason": None,
            "proposal_payload": None,
            "aliases_added": [],
            "new_slot_tokens": [],
        }

        # The producer-supplied template for a PROPOSE_NEW name (companion fields).
        template = proposal_by_name.get(raw_name)
        # If raw_name slugs to a proposal name, allow that template too.
        if template is None:
            from driver_ids import slug as _slug
            template = proposal_by_name.get(_slug(raw_name or ""))

        # ── S4: B1..B10 reuse/propose ladder ──
        res = reuse_or_propose(
            raw_name or "", evidence, registry, vocab,
            proposal_template=template,
            evidence_text=it.get("evidence_text"),
        )
        record["status"] = res.status
        record["canonical_name"] = res.canonical_name
        record["reason"] = res.reason
        record["proposal_payload"] = res.proposal_payload
        record["aliases_added"] = list(res.aliases_added)
        record["new_slot_tokens"] = list(res.new_slot_tokens)

        # ── S5: validators V1..V14 (only if the ladder produced a name) ──
        if res.status in ("REUSE", "PROPOSE_NEW"):
            v_reason = _run_validators(
                record=record,
                item=it,
                driver_state=driver_state,
                direction=direction,
                evidence=evidence,
                source_catalog=source_catalog,
                registry=registry,
                vocab=vocab,
                items=items,
                proposals=proposals,
                propose_new_names=propose_new_names,
                emission_v12_ok=emission_v12_ok,
                emission_v12_reason=emission_v12_reason,
            )
            if v_reason is not None:
                # a validator rejected → flip the record to REJECT.
                record["status"] = "REJECT"
                record["reason"] = v_reason

        # ── S6 bucketing ──
        if record["status"] == "REUSE":
            decision["accepted"].append(record["canonical_name"])
        elif record["status"] == "PROPOSE_NEW":
            decision["accepted"].append(record["canonical_name"])
            decision["proposed"].append(record["canonical_name"])
        else:  # REJECT
            decision["rejected"].append(
                {"name": raw_name, "reason": record["reason"]}
            )

        decision["items"].append(record)

    # ── FIX 2 (V13 orphan-proposal scan) — EMISSION-LEVEL, after the item loop ──
    # Every propose_new_drivers[] entry MUST be referenced by >=1 item whose
    # RESOLVED canonical name equals the proposal name (with non-empty evidence).
    # An UNUSED proposal is an orphan: the per-item validator path never fires for
    # it (no item carries it), so we catch it here. Record a V13 rejection with
    # reason proposal_without_use and reflect it in rejected_count. We use the
    # existing V.V13_proposal_used validator, but match against the RESOLVED
    # canonical name of each item (record["canonical_name"]), not the raw name, so
    # an item that reused/proposed INTO the proposal name still counts as a use.
    # An item COUNTS as a use of a proposal only if it RESOLVED (status REUSE or
    # PROPOSE_NEW) — a rejected item is not a live use. We match on the resolved
    # canonical name + the item's own evidence (V13's non-empty-evidence rule).
    resolved_items = [
        {"driver_name": rec["canonical_name"], "evidence": it.get("evidence", [])}
        for rec, it in zip(decision["items"], items)
        if rec["canonical_name"] is not None
        and rec["status"] in ("REUSE", "PROPOSE_NEW")
    ]
    # Names already rejected at the item level (avoid recording a duplicate V13
    # row for a proposal whose own carrying tag was already rejected).
    already_rejected = {r["name"] for r in decision["rejected"]}
    for p in proposals:
        pname = p.get("name")
        used_ok, used_why = V.V13_proposal_used(pname, resolved_items)
        if not used_ok and pname not in already_rejected:
            decision["rejected"].append({"name": pname, "reason": used_why})

    # ── FIX 4 (K53 self-consistency collision) — EMISSION-LEVEL ──
    # If two entries (items and/or proposals) canonicalize to the SAME canonical
    # name within ONE emission, flag it (do not silently accept two raw names for
    # one driver). Group by canonical name; any group with >1 DISTINCT raw name is
    # a collision. Sources: each item's raw driver_name + each proposal name.
    from collections import OrderedDict
    from driver_ids import canonicalize as _canon
    from driver_ids import Rejection as _Rej

    raw_names: list[str] = []
    for it in items:
        rn = it.get("driver_name")
        if rn:
            raw_names.append(rn)
    for p in proposals:
        pn = p.get("name")
        if pn:
            raw_names.append(pn)

    by_canonical: "OrderedDict[str, list[str]]" = OrderedDict()
    for rn in raw_names:
        c = _canon(rn, vocab)
        if isinstance(c, _Rej):
            continue  # rejected raws cannot collide on a canonical driver
        by_canonical.setdefault(c, [])
        if rn not in by_canonical[c]:
            by_canonical[c].append(rn)
    for cname, raws in by_canonical.items():
        if len(raws) > 1:  # two distinct raw names -> ONE driver -> collision
            decision["self_consistency"].append(
                {"canonical_name": cname, "raw_names": list(raws)}
            )

    decision["summary"]["accepted_count"] = len(decision["accepted"])
    decision["summary"]["rejected_count"] = len(decision["rejected"])
    return decision


def _run_validators(
    *,
    record: dict,
    item: dict,
    driver_state,
    direction,
    evidence,
    source_catalog,
    registry,
    vocab: VocabSnapshot,
    items,
    proposals,
    propose_new_names: set,
    emission_v12_ok: bool,
    emission_v12_reason: Optional[str],
) -> Optional[str]:
    """Run the §E validators V1..V14 relevant to one resolved item. Returns the
    first rejection reason, or None if all pass. Validators are ordered V9, V10
    (tag-level), then V11/V12/V13/V14 (emission-level), then the companion-field
    validators V1..V8 against the resolved driver / proposal."""
    name = record["canonical_name"]

    # V9 direction enum
    ok, why = V.V9_direction(direction)
    if not ok:
        return why
    # V10 evidence count + SRC format + catalog resolution
    ok, why = V.V10_evidence(evidence, source_catalog)
    if not ok:
        return why
    # V11 name resolves (registry OR a propose_new in this emission)
    ok, why = V.V11_name_resolves(name, registry, propose_new_names)
    if not ok:
        return why
    # V12 duplicate proposal (emission-level — computed once, applied to proposals)
    if not emission_v12_ok and name in propose_new_names:
        return emission_v12_reason

    # resolve the driver row (existing registry driver OR the proposal payload)
    driver = registry.lookup_exact_name(name)
    if driver is None and record["status"] == "PROPOSE_NEW":
        driver = record["proposal_payload"]

    if record["status"] == "PROPOSE_NEW":
        # V13 proposal is used by >=1 tag with non-empty evidence
        ok, why = V.V13_proposal_used(name, items)
        if not ok:
            return why
        # V14 new-token gate for novel tokens (already run in reuse B10, re-affirm)
        ok, why = V.V14_new_token_gate(name, items, registry, vocab)
        if not ok:
            return why

    # companion-field validators against the resolved driver row
    if driver is not None:
        allowed_states = driver.get("allowed_states", [])
        # V8 driver_state ∈ allowed_states
        ok, why = V.V8_state_in_allowed(driver_state, allowed_states)
        if not ok:
            return why
        # V6 allowed_states well-formed (one class, bounded)
        ok, why = V.V6_allowed_states(allowed_states, vocab)
        if not ok:
            return why
        # V5 base_label
        ok, why = V.V5_base_label(driver.get("base_label"), vocab)
        if not ok:
            return why
        # V4 segment consistent with name
        ok, why = V.V4_segment_consistent(driver.get("segment", "Total"), name, vocab)
        if not ok:
            return why
        # V7 definition (only meaningful for a PROPOSE_NEW; existing rows passed
        # at creation, but re-running is harmless and catches a bad proposal def)
        if record["status"] == "PROPOSE_NEW":
            ok, why = V.V7_definition(driver.get("definition"), name)
            if not ok:
                return why
            # V3 label tokens == name tokens (proposals carry a label)
            if "label" in driver:
                ok, why = V.V3_label_matches_name(driver["label"], name)
                if not ok:
                    return why
        # V1/V2 aliases (proposal aliases must canonicalize to parent + not bridge)
        for alias in driver.get("aliases", []):
            ok, why = V.V1_alias_canonicalizes_to_parent(alias, name, vocab)
            if not ok:
                return why
            ok, why = V.V2_alias_no_bridge(alias, name, registry)
            if not ok:
                return why

    return None
