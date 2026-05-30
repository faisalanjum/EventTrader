# Canonical Requirement + Risk List — Driver CREATION Layer

> **Purpose.** Single ground-truth yardstick for every downstream auditor of the driver-CREATION layer.
> Built by reading R1 (`ConceptualRequirements.md`, 102 lines), R2 (`DriverOntology.md`, 97 lines),
> R3 (`DriverNameRisks.md`, 419 lines) END TO END, verified against current bytes on disk.
> **Do NOT trust the meta-plan's own coverage claims** — every item below is cited to a source file:line.
>
> **Scope key.**
> - **CREATION** = turns evidence into a CLEAN, CANONICAL, VALIDATED driver name + companion fields
>   (driver_name, driver_state, direction, segment, base_label, label, aliases, definition, allowed_states)
>   BEFORE Neo4j write. Includes: ontology rules, canonicalize()/classify_token(), slot grammar + vocab banks,
>   standalone-shortcut handling, banned-content gate, new-token gate, LLM emission contract / author prompt,
>   cold-start seed, registry/vocab READ path (reuse-before-create).
> - **INGESTION** = OUT OF SCOPE on its own merits; delegated to guidance-pipeline reuse (writer MERGE,
>   UNIQUE constraints, PIT fields, supersession, two-phase token promotion, audit labels, concurrency).
>   For INGESTION items the only creation-layer obligation is a **CLEAN HANDOFF**: creation emits exactly the
>   input-JSON contract a guidance-style writer expects, and creation does NOT secretly depend on ingestion internals.
> - **HANDOFF** = lives at the creation/ingestion boundary; creation must produce/emit it, ingestion consumes it.
>
> **Three hard conditions this yardstick enforces:**
> 1. ~100% driver-naming accuracy (plan bar >=90%; user wants as close to 100% as mechanically achievable).
> 2. 100% of the 3 requirement files accounted for (covered, or explicitly deferred WITH rationale).
> 3. Minimum incremental work — maximum reuse of guidance pipeline; smallest new code surface.

---

## GROUP A — ConceptualRequirements obligations (R1 = `ConceptualRequirements.md`)

Each item: ID | one-line requirement | source | scope.

| ID | Requirement | Source | Scope |
|---|---|---|---|
| A1 | Same driver can be tagged to any number of events (driver:event = 1:N). | R1:3-7 | INGESTION (handoff: creation emits one reusable driver name; many-event linkage is a write-side edge). |
| A2 | One event can be associated with more than one driver (event:driver = 1:N); emit a separate driver per causal variable. | R1:9-13 | CREATION (split-per-variable, see B-R2). |
| A3 | A driver_change record's structure is `<driver_name> + <driver_direction> + <associated_event_id>`. | R1:18-21 | HANDOFF (creation supplies driver_name + direction; event_id is attached at ingest). |
| A4 | News-event producer EXCLUDES company-produced events (8-K, 10-K, 10-Q, transcript); simplest filter = exclude events on the day (and maybe +1 day) of company-specific releases. | R1:24-25, 94 | INGESTION/SOURCING (Phase-2 news producer is deferred; not the Phase-1 creation surface). |
| A5 | News drivers are typically macro/sector/industry (rarely company-specific). | R1:27, 52, 86, 94 | CREATION-RELEVANT (informs §5.5 macro-vs-company categorization, A12; macro names use R5 shortcut form). |
| A6 | Driver identification starts from a significant `<stock_price_change>` over a threshold and finds the `<driver>` that caused it: stock_price_change -> driver. | R1:28-29 | CREATION (grounding principle: a driver is something that moved price; see A11). |
| A7 | News-event drivers will become tradeable/triggerable via Benzinga-tag scanning + IBKR price confirmation/triggers (PHASE 4). | R1:31-50 | OUT OF SCOPE (explicitly Phase-4 future; not creation). DEFERRED-with-rationale. |
| A8 | Trade-trigger selection uses a MECHANICAL code-time ranking (companies impacted, move size, S/N, win-rate); NO runtime human curation in the driver-naming/detection layer. | R1:44 | OUT OF SCOPE for creation EXCEPT the binding constraint: creation layer must be fully autonomous, no runtime human curator (see A18 / L4). |
| A9 | Backtesting/walk-forward + live-trading pre-move check + automatic winning-rate detection gate which signals trade. | R1:46-50 | OUT OF SCOPE (Phase-4 trading). DEFERRED-with-rationale. |
| A10 | Earnings drivers (from 8-K, and for learner also transcripts/others) are typically multiple and NOT auto-tradeable like news; need heavy LLM reasoning for a trade signal. | R1:55-57 | CREATION-RELEVANT (these are the Phase-1 producer's drivers; multiplicity => split-per-variable A2). |
| A11 | A driver is anything that led to a stock-price change; for non-news producers, something that did NOT directly (or by LLM reasoning) impact price in this event NEVER gets promoted to a driver. | R1:57, 102 | CREATION (promotion gate: no price-impact => not a driver; ties to R11 evidence gate). |
| A12 | Driver tags let earnings-predictor read only RELATED prior learner reports (own + peer) via relevance ranking; standardize primary_driver + contributing_factors so reports are relatable. | R1:59, 62, 96 | CREATION-RELEVANT (the WHY of standardization; output must carry driver_tags + summary lines per report). |
| A13 | earnings-predictor is CONSUMER ONLY, NOT a producer; it reads driver_tags from prior learner reports + global registry via bundle catalog; predictor `key_drivers[]` stays FREE-FORM prose, never written to registry. | R1:61, 71 | CREATION (defines producer set; predictor MUST NOT be wired as a producer/writer). |
| A14 | earnings-learner is the SOLE Phase-1 producer; emits `primary_driver` + `contributing_factors` grounded in 8-K + transcript + other quarter sources (via DataSubAgents). | R1:61, 96 | CREATION (the one producer the creation layer must serve in Phase 1). |
| A15 | Learner reads 8-K by design but MUST also read transcript for drivers and TAG transcript drivers SEPARATELY, even if only 8-K drivers are given to predictor. | R1:62, 96 | CREATION (emission contract must distinguish/segregate 8-K vs transcript driver tags). |
| A16 | fiscal.ai drivers (from 10-K, 10-Q, presentations) are a deferred (Phase-3) producer; they do NOT follow naming conventions on raw ingest — that is acceptable for now. | R1:64, 98, R2:5 | OUT OF SCOPE for the naming contract on raw ingest (R2 §1 exemption); carried alongside, canonicalized only via a conforming proposal. DEFERRED-with-rationale. |
| A17 | fiscal.ai entries lack event_id; keep `company` + `quarter` fields for them specifically until self-extraction exists. | R1:98 | HANDOFF (schema must allow company+quarter in lieu of event_id for fiscal.ai rows). DEFERRED-with-rationale (Phase 3). |
| A18 | Producer set is exactly: 5.1 news / 5.2 earnings-learner / 5.3 fiscal.ai. (predictor explicitly excluded). | R1:66-71 | CREATION (registry write-access scoping). |
| A19 | OPEN/optional: categorize drivers as macro/sector vs company-specific (as attribute) — uncertain if useful or 100%-achievable; news=macro, rest=company-specific. | R1:72, 86 | CREATION-RELEVANT but OPTIONAL (flagged uncertain in spec; an auditor must NOT treat absence as a gap, but presence should be coherent). |
| A20 | THE CORE OBLIGATION: a super-standardized GLOBAL driver list that ALL producers MUST consult before creating a new driver; if one exists, REUSE it. | R1:76, 80, 88 | CREATION (this is R1's bottom line — equals R2 R1 "reuse first" + the registry READ path). |
| A21 | The driver LIST is distinct from a driver_change EVENT; every driver_change must be appended using an existing or newly-created driver and tagged by source + event_id. | R1:76 | HANDOFF (creation yields the driver; ingest appends the change-event edge with source+event_id). |
| A22 | Need a super-clear driver nomenclature ONTOLOGY to bring maximum determinism to name creation by any LLM. | R1:78 | CREATION (this is R2's reason for existence; determinism is a first-class acceptance criterion). |
| A23 | Phase-1 focus is creating driver-name standardization for earnings-learner only; but ONE global list serves all producers when they activate, so standardize now. | R1:7 (Summary), 80 | CREATION (scope = Phase 1 learner, but the standard must be producer-agnostic / future-proof). |
| A24 | Standardization TENSION (unresolved-in-spec, must be addressed): specific name (predictor picks own-report better) vs generic name (better peer-report + more-companies retrieval); spec leans that news=macro so the generic-for-news arg is weak. | R1:82-88 | CREATION (granularity policy R9 must resolve this tension; auditor checks the plan picks a coherent stance). |
| A25 | Another purpose: feed drivers+events+producer-sources into earnings-orchestrator bundle so predictor is aware of what moves stock prices. | R1:87 | CREATION-RELEVANT (output must be consumable by the bundle catalog; predictor read-path). |
| A26 | News driver = generic/macro/sector, non-fundamental/non-company-specific (mostly); most empirically provable => tradeable & triggerable. | R1:94 | CREATION-RELEVANT (news producer characterization; Phase-2 deferred but informs categorization). |
| A27 | OPEN/PRE-WORK: check whether drivers relate to guidance nomenclature/usage (study guidance_extraction rules FIRST); even if not exact, do drivers first, maybe adopt for guidance later so they link. | R1:100 | CREATION (mandates the guidance-pipeline study + the "mirror guidance" reuse stance = condition 3). |

**Group A coverage note (verify, do not rubber-stamp):** R1 §2.2.x (A7-A9) and most of fiscal.ai (A16-A17) and the Phase-2 news producer (A4, A26) are legitimately OUT-OF-SCOPE / DEFERRED for the Phase-1 CREATION layer. An auditor must accept these as deferred-with-rationale, NOT count them as gaps. The CREATION-binding A-items are: **A2, A5, A6, A10, A11, A12, A13, A14, A15, A18, A19(opt), A20, A22, A23, A24, A25, A27** plus handoff items **A1, A3, A17, A21**.

---

## GROUP B — DriverOntology rules R1-R11 + the explicit field-placement contract (R2 = `DriverOntology.md`)

### B.1 — Field-Placement Contract (R2 §3 table, R2:24-37) — each row is one testable obligation

| ID | Field | Required content | Source | Scope |
|---|---|---|---|---|
| B-F1 | `driver_name` | The reusable causal NOUN variable ONLY. | R2:28 | CREATION |
| B-F2 | `driver_state` | A single VERB from runtime state vocab, drawn from this driver's `allowed_states`. | R2:29 | CREATION |
| B-F3 | `direction` | `long` or `short` (closed enum). | R2:30 | CREATION |
| B-F4 | `evidence` | Source-grounded refs: quotes, IDs, dates, magnitudes, provider names, raw wording. | R2:31 | CREATION (emission) / HANDOFF |
| B-F5 | `aliases` | Exact spelling/order variants of the SAME driver only. | R2:32 | CREATION |
| B-F6 | `label` | Display text whose concept tokens EQUAL the `driver_name` tokens AS A SET. | R2:33 | CREATION |
| B-F7 | `segment` | `"Total"` if name has no sub-dimension; else the sub-dimension the NAME encodes. | R2:34 | CREATION |
| B-F8 | `base_label` | Null OR a canonical financial-metric label from runtime banks. | R2:35 | CREATION |
| B-F9 | `definition` | EXACTLY ONE sentence describing the variable; NOT a tautology of the name tokens. | R2:36 | CREATION |
| B-F10 | `allowed_states` | A subset of ONE state class; size bounded by runtime threshold. | R2:37 | CREATION |

### B.2 — driver_name lexical contract (R2 §2 glossary, R2:12) — atomic

| ID | Requirement | Source | Scope |
|---|---|---|---|
| B-N1 | driver_name = lowercase identifier; ASCII letters/digits/underscores ONLY. | R2:12 | CREATION |
| B-N2 | Must START with a letter. | R2:12 | CREATION |
| B-N3 | Must NOT END with an underscore. | R2:12 | CREATION |
| B-N4 | NO consecutive underscores. | R2:12 | CREATION |
| B-N5 | At least TWO characters. | R2:12 | CREATION |
| B-N6 | "canonical form" = tokens in fixed slot order + no stopwords + each token canonical per synonym/plural/acronym maps + compound metrics as a single metric slot. | R2:22 | CREATION (defines the determinism target). |

### B.3 — Naming Rules R1-R11 (R2 §4, R2:39-87) — each as one obligation

| ID | Rule | Requirement (one line) | Source | Scope |
|---|---|---|---|---|
| B-R1 | Reuse first | Before proposing new, verify candidate is NOT in registry as exact name NOR alias, INCLUDING under canonical form; if a registry driver matches under canonical form, reuse its exact name. | R2:41 | CREATION (the reuse-before-create READ path = A20). |
| B-R2 | Name only the causal variable | name carries only the reusable causal noun; state->driver_state, impact->direction, identity/period/magnitude/source/provider/quote->evidence; if >=2 independent causal variables, emit a separate tag per variable, never bundle. | R2:43 | CREATION |
| B-R3 | Slot order is fixed | Multi-token order = theme, object, customer, geography, institution, metric; each token to exactly one slot; unused slots absent; reorder = same name; earlier slot wins on collision; single-token valid ONLY if it is a standalone shortcut (R5) else needs >=1 discriminator slot; at most one token per slot; two tokens to same slot = REJECT. | R2:45 | CREATION |
| B-R4 | Closed vocabulary | Every token is in runtime vocab OR an existing registry name/alias; a new token may appear ONLY inside a new-driver proposal satisfying R11. | R2:47 | CREATION |
| B-R5 | Standalone shortcut | When assembled name exactly equals a SHORTCUTS_VOCAB entry, that entry IS canonical and slot order does not further apply; covers macro/regulatory/corporate-action/event shortcuts; new shortcut Drivers addable at runtime via `propose_new_drivers[]` with `is_shortcut=true` (subject to >=2-token gate + R11 + banned-content gate); stored as `:Driver{is_shortcut:true}`, no parallel store; runtime shortcuts vocab = markdown seed (§F.1) + live registry filtered `is_shortcut=true`. | R2:49 | CREATION (shortcut handling). Schema `is_shortcut` property = HANDOFF to writer. |
| B-R6 | Compound metrics = one slot | Listed multi-token financial concepts occupy a single metric slot even with underscores. | R2:51 | CREATION (compound-metrics bank). |
| B-R7 | Banned content categories | NONE of the 13 banned categories appears inside driver_name (enumerated in B-R7a..B-R7m below). | R2:53-66 | CREATION (the banned-content GATE). |
| B-R8 | Length bounded | Effective slot count bounded by runtime threshold; exceeding = deterministic REJECT; compound metric counts as one slot toward the bound. | R2:68 | CREATION |
| B-R9 | Granularity | Include only slots the evidence DIRECTLY attributes as cause; removing any included slot must change the named variable; add a sub-dimension (geography/customer/object/theme) ONLY when evidence directly attributes the cause to it; do NOT add unsupported sub-dimensions. | R2:70 | CREATION (resolves tension A24). |
| B-R10 | Companion field rules | (a) aliases never bridge two drivers, each is an exact variant; (b) label tokens = name tokens as a set; (c) segment="Total" unless name encodes a sub-dimension, else that sub-dimension's canonical label; (d) allowed_states from one state class; (e) definition exactly one sentence, not a token restatement; (f) base_label null or canonical financial-metric label. | R2:72-78 | CREATION |
| B-R11 | New driver gate | New driver proposable ONLY when ALL hold (enumerated B-R11a..B-R11g below). | R2:80-87 | CREATION (the new-token / new-driver GATE). |

### B.4 — R7 banned-content categories expanded (R2:54-66) — each is one gate clause

| ID | Banned inside driver_name | Source | Scope |
|---|---|---|---|
| B-R7a | State verbs + verb-derived forms (`-ing`/`-ed`); EXCEPTION = small allowlist of accounting qualifiers (consolidated, diluted, weighted) in runtime vocab. | R2:54 | CREATION |
| B-R7b | Direction/polarity words. | R2:55 | CREATION |
| B-R7c | Motion/change nouns describing what happened to the variable. | R2:56 | CREATION |
| B-R7d | Tickers, legal entity names, person names. | R2:57 | CREATION |
| B-R7e | Period tokens (quarters, years, fiscal markers). | R2:58 | CREATION |
| B-R7f | Numeric/qualitative thresholds, magnitudes, size descriptors. | R2:59 | CREATION |
| B-R7g | Source-type labels (filing forms, document kinds). | R2:60 | CREATION |
| B-R7h | Provider / vendor labels. | R2:61 | CREATION |
| B-R7i | Accounting-tag prefixes (XBRL namespaces). | R2:62 | CREATION |
| B-R7j | Metaphors, sentiment adjectives, effect-on-stock words. | R2:63 | CREATION |
| B-R7k | Bare category labels standalone. | R2:64 | CREATION |
| B-R7l | Vague descriptors too broad to name a causal variable. | R2:65 | CREATION |
| B-R7m | Stopwords. | R2:66 | CREATION |

### B.5 — R11 new-driver gate clauses expanded (R2:81-87) — each is one ALL-must-hold condition

| ID | Condition | Source | Scope |
|---|---|---|---|
| B-R11a | No registry name or alias matches the candidate under canonical form. | R2:81 | CREATION |
| B-R11b | Candidate satisfies EVERY rule above (R1-R10). | R2:82 | CREATION |
| B-R11c | Every token is in runtime vocab/registry/aliases OR is a new token whose slot is unambiguously determined by position among known tokens, not in any banned category, not equal to any existing name/alias/vocab entry, and appears (or its synonym/plural/acronym pre-image appears) in supporting evidence. | R2:83 | CREATION (new-token gate). |
| B-R11d | The same emission attaches this driver to at least one causal claim with NON-EMPTY evidence. | R2:84 | CREATION (evidence-at-registration). |
| B-R11e | Driver must NOT be tied to a single specific event/date/filing/company-quarter/headline/source row; one-offs REJECTED. | R2:85 | CREATION (durability gate). |
| B-R11f | If R1-R10 produce >1 unresolved candidate name, do NOT propose; REJECT as ambiguous. | R2:86 | CREATION (ambiguity = deterministic reject, supports ~100% accuracy). |
| B-R11g | All companion fields satisfy R10. | R2:87 | CREATION |

### B.6 — Ontology meta-obligations (R2 §1, §5)

| ID | Requirement | Source | Scope |
|---|---|---|---|
| B-M1 | Determinism contract: same evidence + same registry catalog + same runtime vocab/thresholds => one of {same reuse, same new proposal, same deterministic rejection}. | R2:5 | CREATION (the core determinism acceptance bar; underpins ~100% accuracy). |
| B-M2 | fiscal.ai (non-conforming source labels) are EXEMPT from the naming contract for raw ingest; carried alongside; not subject to ontology until canonicalized through a conforming proposal. | R2:5 | CREATION-RELEVANT exemption (= A16). DEFERRED-with-rationale. |
| B-M3 | This file defines MEANING not EXECUTION; runtime also supplies live registry catalog + current vocab + current numerical thresholds; their CONTENTS are not in R2; R2 alone is not runnable. | R2:5-7 | CREATION (mandates a separate mechanism/runtime-vocab spec; the plan must supply contents R2 omits). |
| B-M4 | Worked example: state + magnitude do NOT enter the name (`opec_supply` + state `cut`; magnitude stays in evidence). | R2:91-93 | CREATION (acceptance fixture; demonstrates R2/R5/R7). |
| B-M5 | Worked example: word-order variant REUSES registry name (`china_iphone_sales` -> reuse `iphone_china_sales`; "Apple" excluded; "decelerated" = state). | R2:95-97 | CREATION (acceptance fixture; demonstrates R1/R3/R7). |

---

## GROUP C — Deduped canonical risk set (R3 = `DriverNameRisks.md`)

### C.0 — Forensic structure of R3 (what is actually on disk vs the header's claim) — FINDINGS

The R3 header (R3:1-9) declares **four** overlapping taxonomies "27 + 36 + 15 + 36". Reading the file END TO END, the bytes on disk actually contain **SIX** distinct lists (one is positive RULES, not risks):

| Tag | Lines | Title | Count | Header counts it? |
|---|---|---|---|---|
| T1 | R3:11-78 | "Group A-E" (Name shape / semantic / vocab / metadata / process) | 27 (R1-R27) | YES (the "27") |
| T2 | R3:90-162 | 8 dashed groups (slug syntax -> emission contract) | 36 (R1-R36) | YES (the first "36") |
| T3 | R3:165-241 | "DUPLICATE_CONCEPT" all-caps style | 15 (R1-R15) | YES (the "15") |
| T4-RULES | R3:244-302 | "Driver Name Creation Rules" — **POSITIVE rules, NOT risks** | 55 numbered | NO (header omits) |
| T5 | R3:303-345 | "Risks The Driver-Name Ontology Must Prevent" | 35 (1-35) | **NO — header omits this list entirely** |
| T6 | R3:347-419 | "No-Human-Curation Risks For Driver Naming" | 36 (1-36) | YES (the second "36") |

**FINDING C0-a:** The header's "FOUR taxonomies" undercounts. There are 5 risk taxonomies (T1,T2,T3,T5,T6) + 1 positive-rules list (T4-RULES). T5 (35 risks, R3:303-345) is NOT in the header's tally at all. An auditor relying on the header would miss T5 and T4-RULES.
**FINDING C0-b:** T4-RULES (R3:244-302) is the only list of POSITIVE creation rules; it largely restates R2's R1-R11 plus seed examples. It is a useful cross-check fixture, not a risk register.
**FINDING C0-c:** R3:226-227 contain a duplicated line ("Driver proposed without any supporting evidence_refs in the same" appears twice) — verbatim duplication artifact in T3-R14.
**FINDING C0-d:** Per the header (R3:5-7), a literal "100% coverage against this file" claim is mathematically ambiguous because the taxonomies overlap with different scope rules. The spec-side authoritative coverage matrix is `ConceptualRequirements.md` + `CombinedPlan.md` §9. Any plan claim of "100% risk coverage" or a precise "~96-98% accuracy projection" against R3 must be flagged as an OVERSTATEMENT unless it states WHICH deduped set and HOW it is counted.

### C.1 — DEDUPED CANONICAL RISK SET

All ~185 raw entries across T1/T2/T3/T5/T6 dedupe to **35 atomic risks** below. Each canonical risk lists the source entries it absorbs (cited as `Tx-Rn` with R3 line). Scope tagged CREATION / INGESTION / HANDOFF. Most are CREATION (they are name/companion/emission failures the creation layer must mechanically prevent). A handful are emission-contract / write-time integrity checks that straddle the HANDOFF.

#### C.1.1 — Slug syntax / format (mechanical, character-level)

| ID | Canonical risk | Absorbs (R3 file:line) | Scope |
|---|---|---|---|
| K1 | Case/format drift — name not entirely lower_snake_case ASCII (CamelCase, ALL-CAPS, mixed). | T1-R1 (R3:13), T2-R1 (R3:91), T3-R8 (R3:197), T5-R30 (R3:338), T6-R30 (R3:415) | CREATION |
| K2 | Wrong separator — spaces, hyphens, dots, colons instead of underscores. | T1-R1 (R3:13), T2-R2 (R3:92) | CREATION |
| K3 | Non-ASCII characters — Unicode, emoji, accented/non-Latin scripts. | T1-R2 (R3:15), T2-R3 (R3:94) | CREATION |
| K4 | Edge / consecutive underscores — leading/trailing underscore (and, per B-N4, doubled underscores). | T2-R4 (R3:95) | CREATION |
| K5 | Empty / missing name — proposal with name="" or field absent. | T2-R5 (R3:96) | CREATION |
| K6 | Too many segments / excess slots — 5+ tokens, too narrow to reuse (state/modifier usually smuggled in). | T1-R3 (R3:16), T2-R6 (R3:97) | CREATION (= B-R8 length bound). |

#### C.1.2 — Banned tokens inside the slug

| ID | Canonical risk | Absorbs (R3 file:line) | Scope |
|---|---|---|---|
| K7 | State VERB baked into name (cut, decline, drop, beat, raised, lowered, accelerated). | T1-R4 (R3:18), T2-R11 (R3:107), T3-R2 (R3:169), T5-R5 (R3:309), T6-R9 (R3:366) | CREATION (= B-R7a). |
| K8 | Direction / polarity word in name (short, drop, up, down, bullish, bearish, upside). | T1-R5 (R3:20), T2-R12 (R3:109), T6-R8 (R3:363) | CREATION (= B-R7b). |
| K9 | Adjective / qualifier state in name (rising_, weakening_, strong_, weak_, large_). | T2-R13 (R3:111), T3-R3 (R3:173), T5-R6-mag (R3:359) | CREATION (= B-R7a). |
| K10 | Period / date token (q1, fy26, 2025, h1, quarter/year/fiscal markers). | T1-R6 (R3:22), T2-R8 (R3:102), T3-R4-partial (R3:177), T5-R7 (R3:311), T6-R7 (R3:362) | CREATION (= B-R7e). |
| K11 | Numeric threshold / magnitude / unit suffix (2pct, 100bps, 10x, usd/bps/percent unless standard concept). | T1-R8 (R3:25), T2-R9 (R3:103), T3-R3-mag (R3:173), T5-R22 (R3:328), T5-R23-units (R3:329), T6-R6 (R3:359) | CREATION (= B-R7f). |
| K12 | Ticker / legal company name / person name (aapl, apple, tesla, elon_musk, tim_cook). | T1-R7 (R3:23), T2-R7 (R3:100), T3-R4 (R3:177), T5-R8/R9/R10 (R3:312-314), T6-R4 (R3:355), T6-R36 (R3:419) | CREATION (= B-R7d). |
| K13 | Source-type / provenance label (8k, transcript, 10q, news, report, filing prefixes). | T3-R4-src (R3:177), T5-R11 (R3:315), T5-R23-src (R3:393), T6-R23 (R3:393) | CREATION (= B-R7g). |
| K14 | Provider / vendor / raw-KPI label leaking into name (fiscal.ai, benzinga, vendor labels uncleaned). | T5-R24 (R3:330), T6-R24 (R3:395) | CREATION (= B-R7h). |
| K15 | XBRL QName / accounting-tag prefix in name (us_gaap_revenues). | T5-R25 (R3:331) | CREATION (= B-R7i). |
| K16 | Event-id / report-id in name instead of metadata. | T6-R25 (R3:397) | CREATION (= B-R7g family; id belongs in evidence/metadata). |
| K17 | Stopwords (the, of, in, and) inside the slug. | T2-R10 (R3:104) | CREATION (= B-R7m). |

#### C.1.3 — Semantic / scope quality of the name

| ID | Canonical risk | Absorbs (R3 file:line) | Scope |
|---|---|---|---|
| K18 | Over-specific / single-use scope — name only one company-quarter can ever match (aapl_q3_2025_china_event, apple_q2_2026_keynote_event). | T1-R10 (R3:31), T2-R6 (R3:97), T3-R6 (R3:189), T5-R4 (R3:306), T6-R3 (R3:354), + own-report-retrieval-failure T5-R34 (R3:343) | CREATION (= B-R11e durability). |
| K19 | Over-generic / vacuous — bare metric or bucket with no discriminator (sales, demand, macro, weakness, market_event, stuff_happened). | T1-R11 (R3:33), T3-R5 (R3:183), T3-R19 (R3:123-gen), T5-R3 (R3:307), T6-R2 (R3:352) | CREATION (= B-R7l/B-R7k). |
| K20 | Subjective sentiment / judgment in name (strong_iphone_sales, weak_demand, positive_management_tone). | T1-R12 (R3:35), T5-R-sentiment (T4-RULES 48-49 cross), T3-R3 (R3:173) | CREATION (= B-R7j). |
| K21 | Transient one-off framed as durable driver — non-recurring event when a durable parent exists (ceo_resigned vs ceo_transition; one-off assumptions like excluding_fx_this_quarter, holiday_shift). | T1-R13 (R3:37), T5-R21 (R3:327), T5-R32 (R3:341), T6-R33 (R3:413) | CREATION (= B-R11e). |
| K22 | Two/multiple mechanisms bundled in one name (tariffs_and_supply_chain, iphone_sales_and_mac_revenue, revenue_margin_inventory). | T1-R14 (R3:39), T2-R20 (R3:124), T3-multi, T5-R13 (R3:317), T6-R10 (R3:367) | CREATION (= B-R2 split-per-variable). |
| K23 | Mechanism collision — one name groups distinct causal mechanisms that must stay separate (oil_price vs oil_supply). | T6-R11 (R3:369) | CREATION (forces distinct drivers per mechanism). |
| K24 | Effect/outcome mistaken for driver (stock_selloff, price_reaction, market_disappointment, expectations_reset, confidence_loss). | T5-R14 (R3:318), T6-R12 (R3:371) | CREATION (= B-R7j effect-on-stock; A11 only price-CAUSE is a driver). |
| K25 | Metaphor / non-machine term (kitchen_sink, sell_the_news, headwind, tailwind, concerns, uncertainty). | T5-R20 (R3:326), T6-R13 (R3:373) | CREATION (= B-R7j). |
| K26 | Hidden state noun — noun that smuggles a state (collapse, surge, recovery) unless approved as a stable causal object. | T6-R31 (R3:339-340) | CREATION (= B-R7c motion/change nouns). |
| K27 | Anchor/slot-order inversion — wrong token order producing variant slugs (sales_iphone_china vs iphone_china_sales; metric before object). | T1-R15 (R3:41), T2-R-order, T6-R15/ordering (R3:377-378), T4-RULES 32 (R3:278) | CREATION (= B-R3 fixed slot order; object first, metric last). |
| K28 | Sentence-form name — slug reads like a sentence not a noun (the_decline_in_sales). | T2-R18 (R3:122) | CREATION (= B-R2 noun-only). |
| K29 | Missing metric — object named but metric omitted (vision_pro alone for a Vision-Pro-sales driver). | T2-R21 (R3:125), T5-R15 (R3:319-320), T5-R16 (R3:321-322) | CREATION (= B-R9 granularity; include the metric slot when the metric is the driver). |
| K30 | Missing / wrong discriminator — needed qualifier omitted (inventory vs china_inventory) or wrong qualifier used (geography when cause is customer-type); plus segment-overuse when generic metric suffices. | T6-R18/R19/R20 (R3:383-388), T5-R17/R18 (R3:323-324), T1-R-granularity | CREATION (= B-R9 granularity, both directions). |
| K31 | Peer-retrieval pollution / too-broad-peer — name so broad unrelated peer reports match. | T5-R33 (R3:342), T6-R22 (R3:391) | CREATION (granularity vs retrieval; ties A12/A24). |

#### C.1.4 — Cross-driver vocabulary consistency (synonym / variant duplication)

| ID | Canonical risk | Absorbs (R3 file:line) | Scope |
|---|---|---|---|
| K32 | Word-order variant of an existing canonical name (china_iphone_sales when iphone_china_sales exists). | T1-R9 (R3:29), T2-R14 (R3:115), T3-R1 (R3:166), T3-R7 (R3:193), T6-R1/R15 (R3:349-350,377) | CREATION (= B-R1 reuse incl. canonical form). |
| K33 | Plural / singular variant (iphone_china_sale vs iphone_china_sales; order vs orders; tariff vs tariffs). | T2-R15 (R3:117), T5-R29 (R3:337), T6-R17 (R3:381) | CREATION (= B-N6 plural map). |
| K34 | Synonym variant — same concept, different word (iphone_demand vs iphone_sales; sales/revenue/topline/turnover). | T1-R16 (R3:46), T2-R16 (R3:118), T6-R14 (R3:375) | CREATION (= synonym map, B-N6). |
| K35 | Abbreviation / acronym variant (gm vs gross_margin; fcf vs free_cash_flow). | T2-R17 (R3:119), T6-R16 (R3:379) | CREATION (= acronym map, B-N6). |
| K36 | Inconsistent business-object terminology across drivers (datacenter / data_center / hyperscale for one entity). | T1-R17 (R3:48) | CREATION (canonical-object vocab). |
| K37 | Inconsistent state-verb terminology across drivers (declined / decreased / fell for the same motion). | T1-R18 (R3:51), T6-R26 uncontrolled-state (R3:399-400) | CREATION (canonical state vocab; controlled allowed_states). |

#### C.1.5 — Companion-field quality

| ID | Canonical risk | Absorbs (R3 file:line) | Scope |
|---|---|---|---|
| K38 | Bad / vague / circular definition — circular, ambiguous, contradicts name, generic, empty, or >1 sentence. | T1-R19 (R3:55), T3-R12 (R3:216), T5-R26 def (R3:337-cross) | CREATION (= B-F9/B-R10e). |
| K39 | Wrong / malformed segment — segment empty/null/"all"/"specific" when wrong, or carries state/direction; must be "Total" or a clean dimension; must agree with what the name implies. | T1-R20 (R3:57), T2-R28 (R3:140), T3-R15 (R3:232-235) | CREATION (= B-F7/B-R10c). |
| K40 | allowed_states too narrow — omits obvious realistic states (regulatory driver listing only "approved", missing denied/delayed/withdrawn). | T1-R21 (R3:59) | CREATION (= B-F10/B-R10d). |
| K41 | allowed_states too broad — list so long nearly any verb matches, defeating noun/verb separation. | T1-R22 (R3:61) | CREATION (= B-F10). |
| K42 | allowed_states not verbs — list contains adjectives/nouns/numerics (good, bad, trouble, large, strong, growth). | T1-R23 (R3:63), T2-R29 (R3:141), T3-R10 (R3:206) | CREATION (= B-F10 verbs only). |
| K43 | Mixed verb classes in allowed_states — incompatible classes mixed (raised + fda_approved + steepened). | T2-R30 (R3:143) | CREATION (= B-R10d one state class). |
| K44 | Invalid state-pair — a state that makes no sense for the driver (yield_curve + beat). | T6-R27 (R3:401-402) | CREATION (state must belong to driver's allowed_states; ties B-F2). |
| K45 | Bad / malformed / duplicate aliases — alias violates slug rules, is too loose (revenue as alias of iphone_china_sales), equals the canonical name, or duplicates. | T1-R24 (R3:65), T2-R31 (R3:146) | CREATION (= B-F5/B-R10a). |
| K46 | Aliases bridge unrelated drivers — alias points at a semantically different concept (iphone_china_sales aliased to samsung_china_sales / iphone_us_sales). | T2-R32 (R3:148), T3-R9 (R3:201), T6-R31 alias-overmerge (R3:411) | CREATION (= B-R10a). |
| K47 | Alias undermatch — obvious synonyms NOT mapped, causing duplicate drivers. | T6-R32 (R3:412) | CREATION (= reuse completeness; complements K34). |
| K48 | base_label cannot resolve / is junk — doesn't match any Concept-cache family (blocks xbrl_qname auto-resolution), or non-financial / contains state/direction tokens. | T1-R25 (R3:67), T2-R27 (R3:139), T3-R11 (R3:211), T6-R30 xbrl-linking (R3:407-408) | CREATION (= B-F8/B-R10f). HANDOFF: clean base_label enables downstream XBRL resolution. |
| K49 | name != slug(label) / label mismatched with name — label describes a different concept than the name. | T2-R25 (R3:136), T3-R13 (R3:220) | CREATION (= B-F6 label tokens = name tokens as set). |

#### C.1.6 — Emission contract + creation-time process integrity (HANDOFF-adjacent)

| ID | Canonical risk | Absorbs (R3 file:line) | Scope |
|---|---|---|---|
| K50 | Registry catalog not consulted first / skipped exact-match reuse — emits propose_new_drivers[] when a usable exact match existed in the rendered catalog (M1 violation). | T1-R26 (R3:72), T2-R22 (R3:129), T6-R34 reuse-failure (R3:415-416) | CREATION (= B-R1; the reuse-before-create READ path = A20). |
| K51 | Skipped alias reuse — new proposal despite an existing driver's aliases already covering the phrasing. | T2-R23 (R3:130) | CREATION (= B-R1 alias arm). |
| K52 | Wrong existing driver picked — reusing a name whose scope doesn't fit (iphone_total_sales for a China-specific signal). | T2-R24 (R3:131-132) | CREATION (reuse-accuracy; complements K30 discriminator). |
| K53 | Internal inconsistency within one emission — driver_name in primary_driver/contributing_factors/key_drivers != name in propose_new_drivers[] for the same intent. | T1-R27 (R3:74) | CREATION (emission self-consistency). |
| K54 | Unresolved driver_name — a name used in primary/contributing/key_drivers that is NEITHER in registry NOR in propose_new_drivers[]. | T2-R33 (R3:151-152), T3-R-cross | CREATION/HANDOFF (writer would reject; creation must close the loop). |
| K55 | Direction enum violation — `direction` outside {long, short}. | T2-R34 (R3:153) | CREATION (= B-F3). |
| K56 | State not in allowed_states — driver_state chosen for an existing driver that isn't in that driver's allowed_states[]. | T2-R35 (R3:154), T6-R27 (R3:401-402) | CREATION (= B-F2). |
| K57 | Empty / non-SRC evidence — evidence[] empty or strings not in the SRC:* catalog format. | T2-R36 (R3:156), T3-R14 (R3:225-230) | CREATION/HANDOFF (= B-F4; evidence-at-registration = B-R11d). NOTE: SRC:* format is the writer's expected input shape — handoff contract. |
| K58 | No-evidence-at-registration — driver proposed with NO supporting evidence in the same emission (invented in the abstract). | T3-R14 (R3:225-230), T5-R35 (R3:344), T6-R29 (R3:405-406) | CREATION (= B-R11d). |
| K59 | Registry pollution — every run mints weak one-off drivers that never repeat. | T6-R33 (R3:413-414) | CREATION (= B-R11e + B-R11f; the durability/ambiguity gates prevent this in aggregate). |
| K60 | Direction/state confusion — LLM confuses business movement (driver_state) with stock impact (direction). | T6-R28 (R3:403-404) | CREATION (= B-F2 vs B-F3 separation). |

> **Dedup tally:** ~185 raw entries (T1:27 + T2:36 + T3:15 + T5:35 + T6:36 = 149 risks, plus T4-RULES:55 positive rules cross-checked) collapse to **60 canonical IDs K1-K60** (35 if grouped only at the coarsest level; presented at 60 atomic to stay testable). Every canonical K maps to >=1 B-rule or A-item, confirming R2 already covers the risk space — see the mapping column.

### C.2 — Risks that are INGESTION-only (NOT a creation-layer obligation)

Reading R3 END TO END, essentially every risk is about the NAME/companion/emission produced at CREATION time. The handful with an ingestion flavor are still creation-emission obligations, NOT ingestion internals:

| ID | Risk | Why it is HANDOFF not pure-ingestion | Source |
|---|---|---|---|
| K48 (XBRL resolve) | base_label must resolve to a Concept family. | Creation must EMIT a clean base_label; the actual xbrl_qname auto-resolution + Concept cache lookup is ingestion/writer-side (guidance reuse). | T1-R25 (R3:67), T6-R30 (R3:407) |
| K54 (unresolved name) | name in primary/contributing not in registry/proposals. | Creation must close the loop in its OWN emission; the writer's UNIQUE-constraint/MERGE rejection is ingestion-side. | T2-R33 (R3:151) |
| K57 (SRC:* format) | evidence must follow SRC:* catalog format. | The SRC:* shape is the WRITER's expected input contract — creation must conform (handoff); the catalog itself is ingestion-side. | T2-R36 (R3:156) |

**No R3 risk is purely INGESTION with zero creation-layer obligation.** Duplicate-node creation, supersession, two-phase :EquivalenceToken promotion, PIT `registry_visible_at`/`vocab_visible_at`, concurrency/race, and the 5 audit/telemetry labels are INGESTION concerns the user delegates to guidance-pipeline reuse — they are NOT in R1/R2/R3 as creation obligations, so they are not in this yardstick except as the handoff contracts K48/K54/K57 + A1/A3/A17/A21/B-R5(schema).

---

## D — HANDOFF CONTRACT (creation -> guidance-style writer) — the only ingestion-touching obligations

These are the items where the CREATION layer must hand off cleanly (judge ONLY this, per scope). Each is verifiable against the creation emission, not ingestion internals:

| ID | Handoff obligation | Source(s) | Scope |
|---|---|---|---|
| H1 | Creation emits exactly the input-JSON the guidance-style writer expects (fields: driver_name, driver_state, direction, segment, base_label, label, aliases, definition, allowed_states, evidence + propose_new_drivers[] with is_shortcut). | R2 §3 (B-F1..B-F10), R2:49, A3 | HANDOFF |
| H2 | evidence[] entries follow the SRC:* catalog format the writer consumes. | R3 T2-R36 (R3:156), K57 | HANDOFF |
| H3 | base_label is clean enough for downstream xbrl_qname / Concept-cache resolution. | R3 T1-R25 (R3:67), K48 | HANDOFF |
| H4 | driver_change events carry source + event_id (or company+quarter for fiscal.ai) — supplied as metadata, NOT in the name. | A3 (R1:18-21), A17 (R1:98), A21 (R1:76), K16 | HANDOFF |
| H5 | Shortcut Drivers emit `is_shortcut=true` so the writer registers them as `:Driver{is_shortcut:true}` (no parallel store). | R2:49 (B-R5) | HANDOFF |
| H6 | Nothing in creation secretly depends on ingestion internals (no creation logic reaches into supersession/PIT/audit tables — it only produces the JSON contract). | scope rule (this brief) | HANDOFF (negative check). |

---

## E — COVERAGE LEDGER (for downstream auditors)

**Condition 2 (100% of the 3 files accounted for):**
- R1 (`ConceptualRequirements.md`): all of lines 1-103 mapped to A1-A27. Deferred-with-rationale: A4, A7, A8(partial), A9, A16, A17, A26 (Phase-2/3/4 + fiscal.ai exemption). Optional/uncertain: A19. CREATION-binding remainder fully captured.
- R2 (`DriverOntology.md`): §1 meta (B-M1..M3), §2 glossary (B-N1..N6), §3 field table (B-F1..F10), §4 rules R1-R11 (B-R1..R11 + B-R7a-m + B-R11a-g), §5 examples (B-M4-M5). Fully captured.
- R3 (`DriverNameRisks.md`): all 6 lists (T1,T2,T3,T5,T6 risks + T4-RULES) read; ~149 risk entries deduped to K1-K60; the header's missing-T5 + missing-T4-RULES + duplicated-line + ambiguous-100% issues recorded as findings C0-a..C0-d.

**Condition 1 (~100% naming accuracy):** the determinism contract B-M1 + the deterministic-rejection gates (B-R3 reorder=same, B-R8 length, B-R11f ambiguity->reject, B-R11e durability) are the mechanical levers; K1-K60 are the failure modes those levers must each close. An auditor scores the plan by checking each K maps to a concrete mechanism (regex/classifier/vocab/gate), not just prose.

**Condition 3 (minimum work / max reuse):** A27 + B-M2/A16 mandate studying guidance_extraction FIRST and mirroring it; the HANDOFF contract D (H1-H6) is the test that creation reuses a guidance-style writer rather than building new ingestion. Any plan claim of "100% reuse" or a precise "~96-98% accuracy projection" is an OVERSTATEMENT to flag unless evidenced (per C0-d).

---

## SCHEMA OF THIS DOCUMENT (returned to caller)

```
Each item row = { ID, requirement(one line), source(file:line), scope }
scope ∈ { CREATION, INGESTION, HANDOFF }   ; some tagged CREATION-RELEVANT / OPTIONAL / DEFERRED-with-rationale

GROUP A  : A1..A27        ConceptualRequirements obligations            (source R1)
GROUP B  : B-F1..B-F10    field-placement contract                     (source R2 §3)
           B-N1..B-N6     driver_name lexical contract + canonical form (source R2 §2)
           B-R1..B-R11    naming rules                                  (source R2 §4)
           B-R7a..B-R7m   banned-content categories (R7 expanded)       (source R2:54-66)
           B-R11a..B-R11g new-driver gate clauses (R11 expanded)        (source R2:81-87)
           B-M1..B-M5     ontology meta + worked examples               (source R2 §1,§5)
GROUP C  : C0-a..C0-d     forensic findings about R3 structure          (source R3 header + body)
           K1..K60        DEDUPED canonical risk set                    (source R3 T1/T2/T3/T5/T6)
           C.2           ingestion-only / handoff-flavored risks
SECTION D: H1..H6         creation->writer HANDOFF contract             (the only ingestion-touching checks)
SECTION E: coverage ledger mapping each file to IDs (condition-2 proof)
```
