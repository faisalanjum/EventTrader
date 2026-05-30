"""S4 — the B1..B10 reuse/propose ladder  (PROD-CORE, pure given its args).

Transcribes DriverOntology_Implementation.md §B (B1..B10) over a registry +
VocabSnapshot. Decides, for one extracted noun-phrase, whether to REUSE an
existing driver, PROPOSE_NEW a clean canonical driver, or REJECT with a named
reason. Auto-alias per DriverProcess.html §D2.

reuse.py takes ``registry`` as an ARGUMENT and must NOT import registry_fake
(prod-core purity, Harness_BuilderPrompt.md §9). Imports only the foundation
(driver_ids, vocab_seed) + validators (all PROD-CORE). NO LLM, stdlib only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from driver_ids import (
    canonicalize,
    slug,
    SHAPE_REGEX,
    Rejection,
    classify_token,
    SLOT_ORDER,
    split_respecting_atoms,
)
from vocab_seed import VocabSnapshot, banned_category
import validators as V


# ─────────────────────────────────────────────────────────────────────────────
# Result shape (Harness_BuilderPrompt.md §5 per-item record fields)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ReuseResult:
    """The B1..B10 ladder outcome for one noun-phrase.

    status            ∈ {REUSE, PROPOSE_NEW, REJECT}
    canonical_name    the resolved driver name (REUSE/PROPOSE_NEW), else None
    reason            the §B/§E rejection reason (REJECT), else None
    proposal_payload  the propose_new entry dict (PROPOSE_NEW), else None
    aliases_added     raw forms auto-recorded as aliases (DriverProcess.html §D2)
    new_slot_tokens   [{slot, token}] novel tokens this proposal introduces
    """
    status: str
    canonical_name: Optional[str] = None
    reason: Optional[str] = None
    proposal_payload: Optional[dict] = None
    aliases_added: list = field(default_factory=list)
    new_slot_tokens: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "canonical_name": self.canonical_name,
            "reason": self.reason,
            "proposal_payload": self.proposal_payload,
            "aliases_added": list(self.aliases_added),
            "new_slot_tokens": list(self.new_slot_tokens),
        }


# ─────────────────────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────────────────────

def _known_token(token: str, registry, vocab: VocabSnapshot) -> bool:
    """B8 gate: a token is KNOWN if it appears in some Driver.name, some
    Driver.aliases, or as a key/value in the §F.2-F.4 maps (§B8 wording).
    (Slot/state/compound bank membership also counts as "in §F.2-F.4 maps"'s
    spirit — a token in a slot vocab is a known literal.)"""
    for d in registry.all_drivers():
        if token in d["name"].split("_"):
            return True
        for a in d.get("aliases", []):
            if token in a.split("_"):
                return True
    for m in (vocab.synonym_map, vocab.plural_map, vocab.acronym_map):
        if token in m or token in m.values():
            return True
    for slot_set in vocab.slot_vocabs.values():
        if token in slot_set:
            return True
    if token in vocab.shortcuts or token in vocab.compound_metrics:
        return True
    return False


def _new_slot_tokens(name: str, registry, vocab: VocabSnapshot) -> list:
    """For a proposed canonical ``name``, return [{slot, token}] for every token
    NOT already a known slot literal — the VocabToken read-seam (§15.0). The slot
    is read from the canonicalized name's classification (resolve already ran in
    canonicalize, so each token classifies to exactly one slot or is a novel
    literal placed by position). Best first-cut: classify each token; if UNKNOWN
    to the slot vocabs, infer from neighbours via SLOT_ORDER position in the
    already-ordered name.

    v11-3 (2026-05-29): the name is re-split with ``split_respecting_atoms`` (NOT a
    raw ``name.split('_')``) so a multi-token OBJECT (``vision_pro`` /
    ``cloud_service``) stays WHOLE — it is ONE known object literal, not [vision, pro]
    fragments that would each be emitted as a spurious novel slot token (the #1 bug)."""
    out: list = []
    tokens = split_respecting_atoms(name, set(vocab.frozen_atoms))
    # build the known-slot map for tokens that ARE in a slot vocab
    classified = [(t, classify_token(t, vocab.slot_vocabs)) for t in tokens]
    occupied = {s for (_, s) in classified if s != "UNKNOWN"}
    from driver_ids import SLOT_INDEX  # local import keeps purity; foundation only
    for i, (tok, slot) in enumerate(classified):
        if slot != "UNKNOWN":
            continue
        if _known_token(tok, registry, vocab):
            # known literal (registry/alias) but not a slot-vocab token: infer slot
            pass
        left = max((SLOT_INDEX[s] for (_, s) in classified[:i] if s != "UNKNOWN"), default=-1)
        right = min((SLOT_INDEX[s] for (_, s) in classified[i + 1:] if s != "UNKNOWN"),
                    default=len(SLOT_ORDER))
        free = [idx for idx in range(left + 1, right) if SLOT_ORDER[idx] not in occupied]
        chosen_slot = SLOT_ORDER[free[0]] if len(free) == 1 else "metric"
        if not _known_token(tok, registry, vocab):
            out.append({"slot": chosen_slot, "token": tok})
        occupied.add(chosen_slot)
    return out


def _auto_alias(raw_slug: str, accepted_name: str, vocab: VocabSnapshot) -> Optional[str]:
    """DriverProcess.html §D2 auto-alias: record ``raw_slug`` as an alias of
    ``accepted_name`` IFF (a) it differs from the name, (b) it canonicalizes TO
    the accepted name, and (c) it passes V1 (alias→parent). Returns the alias to
    add, or None."""
    if raw_slug == accepted_name:
        return None
    canon = canonicalize(raw_slug, vocab)
    if isinstance(canon, Rejection) or canon != accepted_name:
        return None
    ok, _ = V.V1_alias_canonicalizes_to_parent(raw_slug, accepted_name, vocab)
    return raw_slug if ok else None


# ─────────────────────────────────────────────────────────────────────────────
# the B1..B10 ladder
# ─────────────────────────────────────────────────────────────────────────────

def reuse_or_propose(
    raw_name: str,
    evidence: list,
    registry,
    vocab: VocabSnapshot,
    *,
    proposal_template: Optional[dict] = None,
    evidence_text: Optional[str] = None,
) -> ReuseResult:
    """Run the B1..B10 reuse/propose ladder for ONE extracted noun-phrase.

    Args:
      raw_name: the noun-phrase the caller (LLM/B1) extracted (may be rough).
      evidence: the SRC:* entries (or text) supporting this tag — for the §D(e)
                new-token gate at B9/B10.
      registry: any object with the §4 Registry interface (the prod seam).
      vocab:    the VocabSnapshot.
      proposal_template: optional dict of companion fields the producer supplied
                for a PROPOSE_NEW entry (label/segment/definition/allowed_states/
                aliases/base_label/is_shortcut). When present its fields seed the
                proposal_payload; otherwise the payload carries the canonical
                name + a placeholder template the caller/V7 will complete.
      evidence_text: optional raw evidence TEXT (the source prose behind the
                SRC:* refs) used by the §D(e) new-token-gate substring check at
                B10/V14. In Layer 1 the tag's ``evidence`` is SRC IDs only, so a
                novel token's appearance is checked against this text when given.

    Returns a ReuseResult (status REUSE | PROPOSE_NEW | REJECT)."""
    # ── B1 Extract — the caller supplied the noun phrase (raw_name). ──
    # ── B2 Slugify. ──
    candidate_slug = slug(raw_name)
    if not candidate_slug or not SHAPE_REGEX.match(candidate_slug):
        return ReuseResult("REJECT", reason="empty_or_invalid_slug")

    # ── B3 Exact name match. ──
    hit = registry.lookup_exact_name(candidate_slug)
    if hit is not None:
        return ReuseResult("REUSE", canonical_name=hit["name"])

    # ── B4 Exact alias match. ──
    hit = registry.lookup_by_alias(candidate_slug)
    if hit is not None:
        return ReuseResult("REUSE", canonical_name=hit["name"])

    # ── B5 Canonicalize. ──
    canonical = canonicalize(candidate_slug, vocab)
    if isinstance(canonical, Rejection):
        return ReuseResult("REJECT", reason=canonical.reason)

    # ── B6 Exact name match on canonical. ──
    hit = registry.lookup_exact_name(canonical)
    if hit is not None:
        res = ReuseResult("REUSE", canonical_name=hit["name"])
        # AUTO-ALIAS: the raw candidate_slug folded to this name (canonical fold).
        alias = _auto_alias(candidate_slug, hit["name"], vocab)
        if alias is not None and alias not in hit.get("aliases", []):
            res.aliases_added.append(alias)
        return res

    # ── B7 Exact alias match on canonical. ──
    hit = registry.lookup_by_alias(canonical)
    if hit is not None:
        res = ReuseResult("REUSE", canonical_name=hit["name"])
        alias = _auto_alias(candidate_slug, hit["name"], vocab)
        if alias is not None and alias not in hit.get("aliases", []):
            res.aliases_added.append(alias)
        return res

    # ── B8 Sorted-token reuse (gated on ALL-tokens-known). ──
    # v11-3: atom-aware split (NOT a raw split) so a multi-token compound/object/ban
    # (short_interest, vision_pro, us_gaap) stays WHOLE — else the B9 banned re-check
    # below sees a bare fragment (`short`) and wrongly REJECTS a legit seeded compound.
    tokens = split_respecting_atoms(canonical, set(vocab.frozen_atoms))
    if all(_known_token(t, registry, vocab) for t in tokens):
        match = registry.sorted_token_match(tokens)
        if match is not None:
            res = ReuseResult("REUSE", canonical_name=match["name"])
            alias = _auto_alias(candidate_slug, match["name"], vocab)
            if alias is not None and alias not in match.get("aliases", []):
                res.aliases_added.append(alias)
            return res
        # all-known but no sorted-token match → fall through to B9 (a clean
        # new combination of known tokens may still be a valid new driver).

    # ── B9 Grammar + new-token gate + validators scoped to name. ──
    # canonical already passed §C grammar (it returned a string). Re-affirm shape.
    if not SHAPE_REGEX.match(canonical):
        return ReuseResult("REJECT", reason="invalid_post_reorder")
    # banned-content re-check on the canonical tokens (defence in depth).
    for t in tokens:
        cat = banned_category(t, vocab)
        if cat is not None:
            return ReuseResult("REJECT", reason="banned_token")

    # ── B10 New driver gate (R11) + V14 new-token gate. ──
    # Build the proposal payload (companion fields from the template, defaults
    # filled so the downstream V-suite can run). new_slot_tokens = the novel
    # tokens this name introduces (VocabToken seam).
    new_slot_tokens = _new_slot_tokens(canonical, registry, vocab)

    proposal = _build_proposal(canonical, proposal_template, vocab)

    # V14 new-token gate: every novel token must pass §D (shape/not-banned/
    # appears-in-evidence). Build a one-item view so V14 can read the evidence
    # (SRC refs) AND the raw evidence_text (the §D(e) substring source).
    item_view = {"driver_name": canonical, "evidence": list(evidence)}
    if evidence_text:
        item_view["evidence_text"] = evidence_text
    items_view = [item_view]
    ok, why = V.V14_new_token_gate(canonical, items_view, registry, vocab)
    if not ok:
        return ReuseResult("REJECT", reason=why)

    # R11d evidence-at-registration: the tag must carry non-empty evidence.
    if not evidence:
        return ReuseResult("REJECT", reason="proposal_without_use")

    res = ReuseResult(
        "PROPOSE_NEW",
        canonical_name=canonical,
        proposal_payload=proposal,
        new_slot_tokens=new_slot_tokens,
    )
    # AUTO-ALIAS: a new driver is accepted → record the raw form IFF it folds
    # to the accepted canonical name and passes V1.
    alias = _auto_alias(candidate_slug, canonical, vocab)
    if alias is not None:
        res.aliases_added.append(alias)
        # carry the auto-alias onto the proposal so the writer persists it
        if alias not in proposal.get("aliases", []):
            proposal.setdefault("aliases", []).append(alias)
    return res


def _build_proposal(
    canonical: str, template: Optional[dict], vocab: VocabSnapshot
) -> dict:
    """Assemble the propose_new entry (Harness_BuilderPrompt.md §5). Uses the
    producer-supplied ``template`` fields when present; otherwise emits a
    minimal payload carrying the canonical name + label. The DEFINITION is left
    to the producer (V7 rejects an empty/bad one at S5) — when no template is
    supplied we leave ``definition`` as supplied-or-empty so V7 surfaces it
    rather than the harness silently inventing prose."""
    tpl = dict(template or {})
    proposal: dict = {
        "name": canonical,
        "label": tpl.get("label", canonical.replace("_", " ")),
        "segment": tpl.get("segment", "Total"),
        "definition": tpl.get("definition", ""),
        "allowed_states": list(tpl.get("allowed_states", [])),
        "aliases": list(tpl.get("aliases", [])),
    }
    if "base_label" in tpl and tpl["base_label"] is not None:
        proposal["base_label"] = tpl["base_label"]
    if "is_shortcut" in tpl:
        proposal["is_shortcut"] = bool(tpl["is_shortcut"])
    return proposal
