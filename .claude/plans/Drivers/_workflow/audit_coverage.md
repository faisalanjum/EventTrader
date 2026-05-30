# COVERAGE AUDIT — Driver CREATION layer

Auditor lens: COVERAGE. Yardstick: `_workflow/req_canonical.md`. Every claim verified against current bytes on disk (P1 CombinedPlan, P2 DriverOntology_Implementation, P3 Neo4jXBRLDesign, P4 DriverImprovements, P5 Prompt, R1/R2/R3, live learner SKILL.md). Creation scope only.

## VERDICT SUMMARY

The creation layer is broadly well-covered. Group B (R2 ontology rules R1-R11, field placement, banned categories, new-driver gate) maps cleanly to §C canonicalize steps + §E validators V1-V15 + §D grammar/new-token gate, and the §H Conformance Index is real (every R-rule has an enforcing clause). The deferrals (A4/A7/A8/A9/A16/A17/A26 Phase-2/3/4 + fiscal.ai exemption) are explicit with rationale. ConceptReq §5.5 macro/sector category (A19) is correctly deferred ("No category field in schema (correct rejection)", P1:536).

But there are real gaps against the THREE HARD CONDITIONS:

1. **Two determinism-critical functions are CALLED but never DEFINED** (`classify_token`, `order_by_slot`, `effective_slot_count`) — these are the heart of slot assignment (R3/R4/R8). Their behavior, especially slot inference for an UNKNOWN token, is left to prose. (COV-1, blocker for ~100% accuracy.)
2. **The one-token-to-multiple-slots conflict guard is explicitly DEFERRED** (P4:24) and relies on Python dict iteration order — a "Real correctness gap" admitted by the plan itself. (COV-2, major.)
3. **No DriverNameRisks.md → mechanism coverage matrix exists on disk.** P1 §9 covers only ConceptualRequirements, not R3. The "100% risk coverage" the prompt P5 demands lives only inside the (not-yet-produced) ontology-rewrite output, and P5 keeps it internal-only. So the R3 acceptance claim is unverifiable as an artifact. (COV-3, major.)
4. **Several SEMANTIC R3 risks have NO mechanical enforcer** — K23 mechanism-collision (oil_price vs oil_supply), K30 wrong-discriminator, K47 alias-undermatch, K52 wrong-driver-picked, K31 too-broad-peer. These are pure LLM-judgment, not closed by any validator. The plan neither covers them mechanically nor explicitly defers them with rationale. (COV-4, major.)
5. **The producer-facing prompt that TEACHES the rules does not exist yet and is not designed** — only a ~75 LOC line-item ("Learner SKILL.md emission updates", P1:580). The current learner SKILL.md still emits `primary_driver:{summary, category, evidence_refs}` (SKILL.md:53), the OLD free-form shape with a `category` field that collides with the no-category deferral. For the ~100% accuracy bar, the make-or-break artifact (how a weaker LLM is taught the slot grammar) is undesigned. (COV-5, major.)
6. **The "~96-98% accuracy projection" is unsupported** (P1:883), and contradicts the slot-coverage gap the plan itself documents (TIER-1 seed does NOT cover OBJECTS/CUSTOMERS/THEMES, P1:177). (COV-6, major — overstatement per anti-false-positive rule C0-d.)
7. **Minor ontology↔implementation wording drift**: DriverOntology.md R3 says a non-shortcut name "requires at least one discriminator slot" (R2:45); the implementation enforces a stricter "metric mandatory" (P2:172 REJECTION_NO_METRIC_TOKEN). The stricter rule is design-aligned with R3 risks T5-R15/R26/T6-R26, but the ontology text the LLM sees does not state it. (COV-7, minor.)

Below: item-by-item.

---

## GROUP A — ConceptualRequirements

- A1 (1:N driver:event): COVERED — P1:528 DriverChange design (ingestion handoff, clean).
- A2 (split per causal variable): COVERED — B-R2 + B1 extract "never bundle" (P2:30); canonicalize is per-variable (P2:27).
- A3 (driver_change structure): COVERED-HANDOFF — E16 input JSON items[] carry driver_name+direction; event_id at ingest (P2:548-582).
- A5 (news macro): COVERED-RELEVANT — R5 shortcut form (R2:49). Phase-2 producer deferred.
- A6 (price-change → driver): COVERED — R11d evidence-at-registration (R2:84) + A11.
- A7/A8/A9 (Phase-4 trading): DEFERRED-WITH-RATIONALE — P1:531-532, L4 no-curator. Accept.
- A10 (earnings multiple drivers): COVERED — A2 split + learner producer.
- A11 (no price-impact → not a driver): COVERED — R11d + E18 source-catalog (P1:530).
- A12 (driver_tags for relevance ranking): PARTIAL — emission contract that carries driver_tags+summary per report is PLANNED (SKILL.md update, P1:580) but not built; see COV-5.
- A13 (predictor consumer-only): COVERED — E30, V11 carve-out keeps key_drivers[] free-form out of registry (P2:284).
- A14 (learner sole Phase-1 producer): COVERED — E30 (P5:11), P1:533-534.
- A15 (tag transcript drivers separately): PARTIAL — source_catalog extracts 8-K + transcript IDs (P1:286) but the "tag transcript drivers SEPARATELY" segregation is not a designed emission rule; only sourcing is mentioned. Minor hole rolled into COV-5.
- A18 (producer set = news/learner/fiscal): COVERED — E30, V11 producer dispatch (P2:284).
- A19 (macro/sector category — OPTIONAL): DEFERRED-WITH-RATIONALE — P1:536 "No category field (correct rejection)". Coherent. BUT the live learner SKILL.md still has `primary_driver.category` (SKILL.md:53) — present-state contradiction, see COV-5.
- A20 (single global list consulted before create = reuse-first): COVERED — R1 + B3-B8 reuse cascade (P2:41-68), bundle registry render (E5). This is the core obligation; mechanically real.
- A21 (list vs change-event): COVERED-HANDOFF — E14 source_id + event_id metadata.
- A22 (determinism ontology): COVERED — B-M1 determinism contract (R2:5), but see COV-1/COV-2 (determinism leaks via undefined classify_token + deferred slot-conflict guard).
- A23 (producer-agnostic standard now): COVERED — E16 source_type enum {learner_result,news,fiscal_kpi}.
- A24 (specific vs generic tension): COVERED — R9 granularity (R2:70), P1:539. Resolved by "include only evidence-attributed slots." Stance is coherent.
- A25 (feed bundle catalog): COVERED — E5 bundle render, P1:537.
- A27 (study guidance first / mirror): COVERED — §J.1 Mirror Map (P2:616). NOTE: phase-1 map had defects (driver_change_id wrong-name) per reuse_map.md — not a coverage gap but a correctness issue in the reuse lens.

---

## GROUP B — Ontology rules

All field-placement (B-F1..F10), lexical (B-N1..N6), banned categories (B-R7a..m), and new-driver gate clauses (B-R11a..g) map to enforcing clauses. Spot-verified:
- B-N4 (no consecutive `_`): COVERED — SHAPE_REGEX `^[a-z]([a-z0-9]|_(?!_))*[a-z0-9]$` (P2:237), E7.
- B-R1 reuse: COVERED — B3-B8 cascade.
- B-R3 slot order + single-token rule: COVERED in text (R2:45) + order_by_slot (P2:169) BUT order_by_slot UNDEFINED (COV-1); single-token-needs-discriminator is implemented as metric-mandatory (COV-7).
- B-R7a verb forms: COVERED — §F.7 verb_form regex `/^[a-z]+(ed|ing)$/` minus allowlist §F.9 (P2:423,439).
- B-R11c new-token slot: PARTIAL — "slot unambiguously determined by position among known tokens" (P2:262) is prose; no algorithm; zero-anchor → slot_anchor_unavailable (P2:453) but partial-anchor inference unspecified (COV-1).
- B-M4/M5 worked examples: COVERED — R2:91-97; opec_supply passes via shortcut step 8 (exempt from metric gate); china_iphone_sales reuses via canonical form. Consistent.

---

## GROUP C — Deduped risks K1-K60

Mechanically COVERED (validator/regex/gate cited):
- K1-K5 (slug syntax): SHAPE_REGEX + B2 + C step1.
- K6 (excess slots): R8 + C step 11 MAX_EFFECTIVE_SLOTS=4 (P2:174,479).
- K7-K17 (banned tokens): §F.7 BANNED_CONTENT + C step 7 + states check.
- K18 over-specific: R11e durability (R2:85). K19 over-generic: §F.7 category/vague_descriptor.
- K20 sentiment / K24 effect / K25 metaphor / K26 hidden-state: §F.7 sentiment/effect/metaphor categories.
- K22 multi-mechanism bundle: B-R2 split + "two tokens same slot = REJECT" (R2:45).
- K27 slot-order inversion: canonical reorder (C step 10) — modulo order_by_slot undefined (COV-1).
- K28 sentence-form: noun-only + stopword strip.
- K29 missing-metric: REJECTION_NO_METRIC_TOKEN (P2:173) — actually ENFORCED (this is the design-intended metric-mandatory rule, aligned with T5-R15/R26).
- K32 word-order variant: V15 + B8 sorted-token + canonical form (R2:41).
- K33 plural / K34 synonym / K35 acronym: §F.2/F.3/F.4 maps via C step 5.
- K38 bad definition: V7. K39 segment: V4. K40-K43 allowed_states: V6. K44/K56 invalid state: V8. K45 alias slug: V1. K46 alias bridge: V2. K48 base_label: V5. K49 label mismatch: V3.
- K53 internal inconsistency / K54 unresolved name: V11. K55 direction enum: V9. K57 evidence format: V10 (E18 catalog resolution). K58 no-evidence: V13 + R11d. K60 direction/state confusion: B-F2 vs B-F3.

NOT mechanically covered (LLM-judgment; no validator) — COV-4:
- K23 mechanism-collision (oil_price vs oil_supply must stay distinct). Nothing forces two distinct causal mechanisms to distinct names if both canonicalize validly. Pure semantic.
- K30 wrong-discriminator (geography used when cause is customer-type). No validator checks discriminator-vs-cause fit.
- K31 too-broad-peer / K30 segment-overuse. R9 prose only; no mechanical granularity check.
- K47 alias-undermatch (obvious synonyms not mapped → dup drivers). Depends on synonym_map completeness; no validator. Partly mitigated by Lever #2 N=2 promotion over time, but first-occurrence dup not prevented.
- K52 wrong-existing-driver-picked (reuse iphone_total_sales for a China signal). The reuse cascade REUSES any canonical match; nothing checks scope-fit. Acknowledged indirectly by Lever#1 exact-match-only commit (P4:314) for repairs, but not for normal reuse.
- K59 registry-pollution: PARTIAL — R11e durability + R11f ambiguity-reject + V13 reduce it in aggregate (P1:810 mentions code-time pruning), but no per-emission mechanical block; relies on durability gate the LLM self-applies.

These map to the inherent LLM-judgment surface. The plan does NOT enumerate them as deferred-with-rationale; they are implicitly assumed handled by R9/R2 prose. For the ~100% bar they are the residual error sources. Flag as COV-4.

C0 findings from req_canonical (R3 header undercount, T4-RULES/T5 omission, duplicated line, ambiguous-100%): confirmed on disk (R3:303-345 T5 list present, R3:226-227 dup). These are R3-authoring defects, not plan gaps, but they mean any plan claim of "100% risk coverage against DriverNameRisks.md" must state which deduped set — none does. Supports COV-3/COV-6.

---

## HANDOFF (H1-H6) — clean by design

E16 input JSON (P2:545-582) is self-contained; canonicalize is a pure function (P2:88 frozen VocabSnapshot, no Neo4j reads). source_type enum is correctly DISJOINT from guidance and prediction_result is removed (E30). is_shortcut emitted for Pattern B (H5). No creation logic reaches supersession/PIT/audit internals (H6). Clean. No finding.

---

## CONDITION CHECKS

- Cond 1 (~100% accuracy): NOT mechanically demonstrated. Bar enforced is >90% (P1:35); claim is ~96-98% (P1:883) unsupported; residual LLM-judgment risks COV-4 + undefined classify_token COV-1 + deferred slot-conflict COV-2 + cold-start slot gap (P1:177) cap achievable determinism below ~100%.
- Cond 2 (100% of 3 files accounted): R1 fully accounted (10 covered + 2 deferred, P1:541). R2 fully covered. R3 NOT accounted as a verifiable artifact — no on-disk risk→mechanism matrix; COV-3.
- Cond 3 (min work / max reuse): reuse framing real but over-credited (see reuse_map.md mirror-map defects). Not a coverage gap per se.
