# FINAL_DESIGN.md — the Driver system rulebook (front door)

> **Status: PROVISIONAL LIVE (Phase 3 of the consolidation, written 2026-07-15).** This file is the single
> front door and rule-meaning authority of the four-file set. It was built from the verified consolidation
> atom ledger (`CONSOLIDATION.md`, five verification rounds, two independent reviewers) over the 33 frozen
> sources. **Until the section-14 zero-loss checks pass (Phase 4), the frozen sources remain the byte
> evidence baseline**; on any suspected conflict, read `CONSOLIDATION.md` §10.1 (known stale prose) and the
> Phase-1 manifest (`archive/2026-07-15_pre-consolidation/MANIFEST.json`).
>
> **One-copy law of the four-file set:** rule MEANING lives only here · public channel duties live only in
> `ChannelContract.md` · build/test/run procedure lives only in `BUILD_AND_OPERATIONS.md` · status, history,
> supersessions, and crosswalks live only in `STATUS_AND_HISTORY.md`. The frozen Candidate Fact Packet
> (`15_CandidateFactPacket.md`, owner-frozen v1.0 + the 2026-07-15 Q4 amendment) is a temporary fifth live
> file until its relocation is separately approved. Status tags in this file (FINAL / BUILD-PENDING /
> CONDITIONAL / OPEN / CANDIDATE) are generated summaries — the owning rows live in `STATUS_AND_HISTORY.md`.
>
> **Reading order for a new bot:** §1 mission/safety → §2 flow → §3 naming → §4 types/birth → §5 identity &
> scope → §6 units/periods → §7 the fact contract → §8 enrichment → §9 reads → §10 status tags.

## 0. Glossary (overloaded terms, exact meanings)

- **Driver** — one reusable, atomic cause or standing thing that can matter to a company or market. A class node: name + permanent `fact_type` + `SAME_AS`/`BASE_METRIC` links + birth evidence.
- **DriverUpdate** — one real, source-backed occurrence of a Driver in one source event. The fact node.
- **Catalog G1/G2** — G1 = the live reuse display; G2 = the final catalog admission gate. NOT the XBRL concept linker's G0/G1/G2 guards (§8). Always qualify which you mean.
- **Menu** — a context-specific candidate list (slice menu, concept menu, live reuse view). Never the whole catalog.
- **Slice** — the reporting company's own measured business population inside `fact_scope`. Not a Track A batch partition.
- **Seed** — an evidence-backed catalog candidate artifact. Not yet a graph Driver.
- **Fold** — combine child catalogs under the same reconcile law used everywhere else.
- **Head** — the current canonical representative in a reversible `SAME_AS` set.
- **Created** — the DriverUpdate write time. **Public time / `event_time`** — the source release time.
- **Parked** — a retryable item the core cannot safely write yet. **Skipped** — a terminal, counted non-write.
- **Fail closed** — do not create, attach, merge, or write when required proof is missing.
- **Source** — the graph Event/Report/Transcript/News node that owns the quote.
- **Latent base anchor** — an invisible auto-minted placeholder base metric (e.g. `revenue` when `revenue_guidance` is admitted first): never claim-eligible, never shown in reuse display, graduates on first real evidence. The only legal empty Driver node.

## 1. Mission and safety law `[FINAL]`

- A source quote is required for every fact. A mention without a fact is dropped.
- The catalog must reuse the same name for the same cause across companies and time.
- True duplicates stay recoverable through reversible `SAME_AS`; nodes and facts are never deleted or re-keyed to make history look cleaner.
- The intended loop: extract facts → attribute price moves → learn which Drivers matter → predict → trade.
- **The one law (asymmetric):** merging different meanings causes permanent damage; keeping the same meaning separate is repairable. **When unsure, keep separate.**
- Meaning judgments belong to a capable model. Structure, normalization, identity, validation, and hard safety checks belong to code. A channel or weak model never final-confirms identity, family, link, fact placement, eligibility, or quarantine.
- **Point-in-time (PIT) discipline:** a historical run may see only information public before its cutoff. Writes and menus cut at ≤ event/source public time; backtest/history reads use strict `date < as_of`; live sees the current graph. Never expose realized returns to a fact or verdict producer.
- **Store-when-stated:** only source-stated values enter storage; deterministic scaling may canonicalize them; classification/period/collision/withdrawal logic may derive only approved non-numeric states, IDs, or facts — never an invented stored number.
- Runtime must not depend on a human. One-time owner approvals and frozen-list reviews are design/bootstrap steps, not runtime queues.
- Use the smallest machinery that meets these rules. Missing links are safer than wrong links.

## 2. Graph and flow `[FINAL]`

```text
source channel (SELECT · FETCH · SUBMIT — see ChannelContract.md)
   -> raw event packet
   -> shared decomposer (one stack for all channels)
   -> admission/reuse decision (strong-judge kernel layer)
   -> Driver class + first admitted DriverUpdate, or attach/park/skip/reject
   -> deterministic writer and enrichment
   -> point-in-time raw/reconciled readers

Event/Report/Transcript/News -> DriverUpdate -> Driver
                                |             |-- SAME_AS -> Driver        (reversible synonym)
                                |             `-- BASE_METRIC -> Driver    (family, suffix -> base)
                                |-- DriverPeriod                            (HAS_PERIOD)
                                |-- XBRL Concept / Member                   (MAPS_TO_CONCEPT / MAPS_TO_MEMBER)
                                `-- optional EXPLAINED_BY verdict edge from Event or DailyCompanyMoveEvent
```

The source channel never creates graph identity; the shared core does. The public input boundary is
`ChannelContract.md` (raw adapter submission); the internal core object is the frozen Candidate Fact Packet
(envelope · transient identity signals · proven fact · optional verdict — see `BUILD_AND_OPERATIONS.md`).

## 3. Driver naming — NAME-01..19 + OD-17 `[FINAL]`

1. **NAME-01** — the name contains the cause only. Event state, direction, size, time, company, unit, and quote live elsewhere.
2. **NAME-02** — one stored name has one meaning. Spelling/order/acronym/plural variants reuse the canonical name. No alias lists. True later duplicates may receive reversible `SAME_AS`.
3. **NAME-03** — vocabulary is open and source-born. A closed vocabulary was tested and rejected (v1 death: ~82% useful-name rejection).
4. **NAME-04** — use all specificity the evidence supports. Never invent a broader class to force reuse.
5. **NAME-05** — format: lowercase ASCII letters/digits/underscores; starts with a letter; ≥2 chars; no trailing or doubled underscore.
6. **NAME-06** — order: thing/actor, then detail, then metric. Singular count nouns by default; keep standard plural financial terms (`earnings`, `bookings`, `sales`, `savings`, `futures`, `receivables`) and any plural whose meaning differs (`product_returns`); the exception list is illustrative — the two-part test decides. Never alter a locked phrase (NAME-08). A singular/plural pair naming the same concept is a wording variant, never two Drivers; when meaning may differ (`booking`/`bookings`), keep separate.
7. **NAME-07** — use the familiar form only when the source does not state a meaningful sibling or benchmark; a stated specific instrument wins over the familiar broad name.
8. **NAME-08** — keep standard financial phrases whole. Loss/deficit/negative-margin are negative regions of signed `net_income`, `operating_margin`, `eps`, etc.; never create duplicate loss Drivers.
9. **NAME-09** — one name carries one cause. Split independent causes. Keep the result short and noun-like.
10. **NAME-10** — a reporting company's own measured segment, product, geography, customer group, sales channel, or owned entity goes to the slice, not the name.
11. **NAME-11** — the local role test: strip generic direction/effect words; an own measured part becomes a slice; an external actor, object, platform, policy, event, or product causing the outcome stays in the name; unclear role or a vague stripped fragment → keep it in the name. A customer is a slice only when it is the reporting company's own customer population. There is no vendor slice kind.
12. **OD-17 (portions)** — `current`, `funded`, `fee_earning`, and similar population qualifiers stay in the name and differ from the bare Driver. Omit the slice only for the true consolidated reporting population; network/systemwide/GMV/curated subsets remain qualified Drivers. Source-stated residuals may be company-specific slice values. Eliminations and consolidation artifacts are neither names nor slices: drop and log the artifact while keeping the affected real metric fact (a prose fact citing a construct as its mechanism writes on the affected real metric — owner ruling 2026-07-15, Q2: the frozen packet's PARK+log stands for a fact whose measured population IS an accounting construct).
13. **NAME-12** — only the cause, a stated per-X denominator, a benchmark, and a terminal family suffix may appear in a name.
14. **NAME-13** — a stated business/physical per-X denominator stays in the name (`oil_price_per_barrel`); never invent one; different denominators are different Drivers and never `SAME_AS`; store the base unit; `eps` is the familiar exception.
15. **NAME-14** — measurement versions (adjusted, diluted, constant currency…) belong in `fact_scope.measurement`, never the name. Absent measurement never means GAAP.
16. **NAME-15/16** — excluded from names: state words, direction/polarity, motion/change nouns, the reporting company itself and incidental co-mentioned entities, period tokens, numbers/sizes/bare units, source-type labels, vendor metadata, XBRL prefixes, metaphor/sentiment/effect words, bare category words, vague descriptors, and glue words. **Carve-outs:** an external company/platform/institution/person whose own independent action or state IS the cause stays (`fed_rate`, `aws_outage`, `tiktok_ban`); stable nouns/metric phrases ending -ing/-ed are legal (`pricing`, `bookings`, `operating_margin`); a sentiment/effect word is legal only inside a specific reusable market force (`glp1_pressure` — generic "pressure" stays banned).
17. **NAME-17** — terminal `_guidance` and `_surprise` stay in the name and also fix permanent `fact_type`. One surprise Driver holds all three surprise types (OD-21). Link guidance/surprise to the base metric with `BASE_METRIC`, never `SAME_AS`. Only a terminal suffix counts; strip it once.
18. **NAME-18** — admit a new Driver only when: no existing Driver has the same meaning; all name rules pass; nouns are source/catalog grounded; ≥1 causal evidence atom exists; the result is reusable; the meaning is unambiguous. Vague evidence is skipped.
19. **NAME-19** — naming rules change only through a general principle, never by adding a sector example as policy.

## 4. Types, states, families, and birth `[FINAL]`

### 4.1 The four permanent fact types — MF-01..12, DU-05..07

- Exactly four `fact_type` values: **metric** (a standing variable/condition, numeric or qualitative, readable again) · **guidance** (the company's own forward outlook) · **surprise** (a delivered actual or promised guide compared with a cross-party expectation) · **action_event** (a discrete happening).
- Persistence test for metric-vs-action: a standing level/condition readable again later = metric; otherwise action. `_guidance`/`_surprise` framing overrides; outlook verbs route to guidance.
- The permanent type is stamped once at final admission. A Driver without a type cannot accept a fact. Later catalog work cannot retype a fact-bearing Driver.
- Bare-root defaults: litigation, convertible notes, dividend policy, restructuring costs = metric; corporate restructuring, asset impairment = action.
- Different flavors of one topic are separate Drivers linked as a family. Every guidance/surprise Driver has exactly one `BASE_METRIC`; action Drivers have none. The base must exist — it may begin as a latent base anchor (the only legal empty node), which graduates automatically on exact later evidence.
- `SAME_AS` = synonym; `BASE_METRIC` = family. Never substitute one for the other.
- Only the base metric receives direct XBRL concept enrichment; guidance/surprise inherit through the family when allowed (never on non-GAAP measurement).
- **OD-1 (terminal-suffix admission, exact rule):** before any Driver ending in terminal `_guidance`/`_surprise` is admitted (batch Track A AND live governed-create), strip exactly ONE terminal suffix (`bookings_guidance` → `bookings`; stacked `revenue_guidance_surprise` is invalid; mid-name words never count — `fda_guidance_issuance` is not terminal). Ask THE one semantic question from the source quote: *"Is the residue a standing metric or condition whose level, state, or severity can be re-read over time, and is this source forecasting/guiding/targeting it (`_guidance`) or comparing it to expectation (`_surprise`)?"* Run it TWICE independently; BOTH must return YES — any NO, UNCLEAR, missing evidence, or disagreement blocks admission (admits `bookings_guidance`; rejects document/action names like `fda_guidance`, `buyback_guidance`, unless the residue truly is the guided metric). Not admitted → rewrite ONLY to a specific source-grounded non-terminal name obeying NAME-04/16 (never a broad bucket like `regulatory_guidance_update`), through normal dedup/Refute; no safe rewrite → park via existing G2/D5. **Admission memo** (`terminal_admissions.json`): `driver_name` · `suffix` · `stripped_base` · `evidence_ref` · `check_1` · `check_2` — the memo FREEZES the verdict; refreshes reuse it and never re-roll the checks; finalization validates the memo, never re-runs the meaning test. **Latent base:** created only after the family is admitted and no real base exists; must be a valid standalone name (NAME-16/13), collide with no record/variant/`skips[]`/parked name, never itself suffixed/stacked; hidden from reuse menus. **Graduation is automatic and exact:** a later evidence-backed metric with the exact same `norm()` name graduates the latent — no fuzzy matching (`net_sales` never graduates latent `revenue`; that is a normal `SAME_AS` question). **Finalization hard-fails:** missing memo · memo base ≠ stripped residue · either check not YES · a terminal-suffix Driver with anything but exactly one `BASE_METRIC` · a `BASE_METRIC` target that is neither an existing metric nor a valid latent anchor · a suffixed/stacked latent anchor · an anchor colliding with records/variants/`skips[]`/parked. Non-rules: no allow/deny lists, no human queue, no generic `_update` bucket, no fuzzy latent matching.
- **OD-2 (bare names — "metric must prove itself"; action is the safe default):** deterministic rules run first and are un-vetoable (OD-1's suffix gate + the locked DU-06 bare-root defaults). Run the locked DU-05/06 classifier (C1), prompt verbatim. C1=action_event → stamp it (safe direction, no second check). C1=guidance/surprise on a BARE name → a NAMING defect, never a stamp: batch = the F3 both-ways hard-fail → rename; live = admission rejects → re-coin with the suffix through OD-1, else the fact parks. C1=metric → the metric-proof challenge (C2) on the full batch evidence set: *"Using only the evidence: is this name itself a standing level, value, condition, or severity that can be read again over time? Answer NO if the name is mainly a one-time action, decision, event, or plan — even if a related amount/rate/balance could be measured under a more specific metric name. Quote the exact evidence phrase."* C2=YES with a verbatim quoted phrase → stamp metric; anything else → stamp `action_event` + `metric_proof_defaulted=true` in the memo row + a counted report-grade warning (visible, never build-blocking, never a queue). Live thin/unclear evidence parks and retries before any default. **The F2 family gate (capstone):** a `_guidance`/`_surprise` family may attach ONLY to a base that is metric AND PROVEN — (a) deterministically metric (suffix/DU-06), (b) OD-2 metric-proven (memo row), or (c) an OD-1-admitted latent anchor (its `terminal_admissions.json` IS the proof). `buyback_guidance → buyback` can never pass on an unproven metric stamp. Non-rules: no third model/tie-breaker, no re-typing after facts.

### 4.2 Birth: born-complete admission `[FINAL — owner-ratified 2026-07-14/15]`

- One real fact in one event is sufficient. Recurrence or "more than two events" are not gates. Boilerplate, bare mentions, and non-facts are dropped before storage.
- Any authorized evidence-bearing channel may submit raw evidence; **the shared core alone** decomposes, reuses or creates the Driver, builds identity, validates, and writes.
- **Every new Driver arrives WITH its first proven DriverUpdate** (the packet's identity signals and Block-2 fact travel as one object; on CREATE, Block 2 becomes the first fact). General name-only catalog seeding is rejected. Latent base anchors are the only empty-node exception; dry-run proposed names may exist outside the graph.
- **Owner ruling 2026-07-15 (Q3):** the finalized Track-A catalog remains an OFFLINE artifact and retrieval source; graph Driver nodes are created lazily, born-complete at their first fact (the admission layer creates the node in the same write when an ATTACH targets a card with no node yet — mechanics specified at the OD-7/live-admission pass). No materialize-all pre-fact sync; the protected-input guard survives for whatever sync step ultimately exists.
- **OD-2 first-fact pin, scoped by owner ruling 2026-07-15 (Q5):** a zero-fact BARE-named Driver's first fact must have `driver_state != unknown` — otherwise park until a readable-state fact arrives. Terminal-suffix `_guidance`/`_surprise` Drivers, whose lane is already proven by OD-1's two admission checks, may be born with an `unknown`-state first fact; the read layer derives `introduced`/movement per OD-14. This pin does not ratify the broader OD-7 live-admission design; it applies only at first birth — OD-14 still allows `unknown` on later facts where its lane rule requires it.
- Category labels (Cat-1/Cat-2) describe the birth situation only — never a second permanent type, never stored.
- Cross-channel submissions for the same source event converge through the same code-built identity (§5). Near-synonym races are accepted over-splits, repairable later via `SAME_AS`.

### 4.3 Exact state vocabularies — DU-08..12 `[FINAL]`

`driver_state` lives on the DriverUpdate, never the Driver name. The quote remains the precise truth. Good/bad never decides a state. Code hard-fails a state outside its Driver's lane.

- **Metric:** `increased` · `decreased` · `unchanged` · `mixed` · `reported` · `persists` · `unknown`. First match wins: stated direction; same Driver differs across parts → `mixed`; explicit flat → `unchanged`; ongoing without direction → `persists`; bare value → `reported`; else `unknown`. A prior value stated IN THE SOURCE alongside the value routes to `increased`/`decreased` instead of `reported`. Metric/surprise/action states are read from source text alone — no graph-history read; only the guidance lane consumes a code-served prior view.
- **Guidance:** `introduced` · `raised` · `lowered` · `reaffirmed` · `withdrawn` · `unknown`. Store movement only when the source states it; a bare guide stores `unknown` (readers derive `effective_driver_state`, §9 — never written back). Source-stated movement with two closed shapes: midpoint up = raised, down = lowered, equal = reaffirmed; the validator skips stored `unknown`.
- **Surprise:** `beat` · `in_line` · `missed` · `unknown`. Code computes only polarity-free position (above/inside/below/at_floor/at_ceiling) and SETS `in_line` whenever there is no favorability wording and the compared value (actual OR guide) is inside a closed expectation range or exactly at a boundary — including a guide RANGE that contains the consensus point; a wordless producer `beat`/`missed` landing strictly inside a closed range is CORRECTED to `in_line` by code. Open shapes: at a stated floor/ceiling = `in_line`; the favorable/unfavorable side is producer-judged per polarity; an actual range overlapping the expectation unclearly → `unknown` unless the source states favorability. `beat`/`missed` are meaning judgments from the full phrase, negation/polarity/scope-aware — never assume higher is better, never map above→beat (OD-13); wordless outside-range cases need a transient discarded polarity proof (allowed only when the favorable direction has no common mainstream counter-story) or stay `unknown`.
- **Action:** `at_risk` · `announced` · `occurred` · `continued` · `resolved` · `canceled` · `suspended` · `rumored` · `failed` · `unknown`. Classify the LATEST stage of one action. Terminal: `failed` = involuntary failure (incl. declining an offer never committed to) · `canceled` = the company's own voluntary withdrawal · `resolved` = a settled two-sided dispute · `occurred` = completion. Non-terminal: `rumored` = unconfirmed third-party reporting (a denial stays rumored) · `at_risk` = a specific current source-flagged adverse threat that is not the company's own plan (generic risk boilerplate is dropped) · `suspended` = paused/resumable (shelve/postpone) · `announced` = the company's stated own action before completion · `continued` = still ongoing. Scrap/abandon/withdraw → canceled; a threat stays at_risk until it happens, then failed.

## 5. Fact identity, scope, slices, measurement, continuity `[FINAL]`

### 5.1 Identity and fact_scope — FS-01..04, FS-27, OD-8, OD-21

- Base identity = `event + driver + fact_scope`. Producer/model identity is never in the fact key. Code builds the ID; IDs and stored scope tokens are immutable.
- Canonical scope slot order (omit absent slots; never store `slice=total`; formatting normalization allowed, semantic aliasing not). **Exact separators:** slice parts are code-sorted and joined with `;` (`slice=geography:china;segment:taco_bell`); measurement tokens are normalized, code-sorted, and comma-joined (`measurement=adjusted,constant_currency`):

```text
period=<period_u_id>
|slice=<sorted kind:value parts>
|measurement=<sorted tokens>
|surprise=<type>             # surprise lane only
|quote_hash=<full sha256>    # rare collision member only
```

- `surprise=` is required on surprise facts and forbidden elsewhere; values: `actual_vs_consensus` · `actual_vs_guidance` · `guidance_vs_consensus` (OD-21). Code composes it BEFORE fusion from transient `surprise_basis_hint` (`actual`|`guidance`; required on every surprise item, forbidden on other lanes) × required `comparison_baseline` (`consensus`|`previous_guidance`). Never infer basis from whether a period ended.
- Every grounded surprise needs a matching home fact in the same event: actual surprise → metric home; guidance-vs-consensus → guidance home. Match family, period, period scope, slice, measurement, and normalized value/unit when value-bearing; a numberless surprise needs a numberless home. Ungrounded "results beat" parks. An actual surprise before its period ends is rejected. A missing home sibling re-extracts the WHOLE event, never an orphan-only replay.
- New scope slots require: identity-bearing for the lane, non-derivable from existing slots, never compared across lanes.
- Fuse same-event/driver/scope pieces before collision handling.
- **OD-8 collision law (replaces old FS-03/T3.4/FACT-12 text):** hash the fixed ten-slot value signature only — `level_low, level_high, level_unit, change_value, change_unit, comparison_low, comparison_high, comparison_baseline, value_text, conditions`. The field keeps the name `quote_hash` for compatibility; quote text, state, confirmation, producer, source type, date, and XBRL enrichment are all EXCLUDED. Preimage = fixed-order compact JSON ARRAY, ASCII-escaped, compact separators; null ≠ empty string; one shared text normalizer; one writer decimal canonicalizer (no exponent, no trailing zeros, `-0`→`0`); units/values canonical before the full untruncated SHA-256.
- Sibling probe: `id = bare_id OR id STARTS WITH bare_id + "|quote_hash="` (a raw bare prefix is unsafe — scope slots are optional). `exact` = all ten slots incl. nulls match; `compatible` = no shared non-null slot disagrees; `conflict` = at least one shared non-null slot disagrees.
- Collision decisions use the PRE-BATCH graph state (input order can never decide identity). No sibling → one post-fusion fact stays bare; multiple initially pairwise-conflicting facts are all hashed. One sibling → compatible fills without null-clobber; conflict creates a flagged hashed member. Multiple siblings → exact merges; conflict-with-all creates a hashed member; compatible-but-not-exact PARKS as ambiguous. Two in-batch competitors for one partial sibling → park both; a richer rerun resolves.
- A true signature correction requires the repair lane. Non-signature fields keep last-write-wins-with-log. At most one bare member per group; members must pairwise conflict on ≥1 shared non-null slot. Late bare-plus-hashed history is legal, never re-keyed. Equal-signature race duplicates read as one until repaired.
- A model may propose/approve `SAME_AS` and fusions; code alone applies a reversible link from an approved trace. A model never deletes, re-keys, moves facts, or bypasses approval.

### 5.2 Slices — FS-05..24

- Stored token = `KIND:VALUE`, normalized free text. Kinds: `segment` · `product` · `geography` · `customer` · `channel` · `entity_ownership` + safe fallback `unknown`. Tests: operates-as → segment; sells → product; operates-in → geography; sells-to → customer; how-it-sells/runs → channel; stake-it-owns → entity_ownership (the least-clean kind: JV/equity-method strongest, other entity rows conservative/provisional).
- A real slice is a business population for which "revenue/earnings from ___" makes sense. Accounting labels are not slices. Source-stated residuals (Other, Corporate Unallocated) are legal company-specific slices, marked non-continuous at read. Eliminations/fair-value levels/consolidation artifacts are dropped and logged as slice artifacts (three exact frozen buckets: hard-exclude, provisional, keep — never a regex).
- Brand is not a kind — its axis or prose role decides. Multiple parts are code-sorted, semicolon-joined, never dropped. Slices apply to all four fact types. Period is never a slice. Omitted slice = consolidated whole-company (metric/guidance/surprise) or no-applicable-part (action).
- The axis→kind table is FROZEN in code, refreshed only offline through a governed update; that offline classification judges an axis by its MEMBERS, never its name (names lie; ~20% error). Runtime 3-way sentinel: known slice axis → mapped kind; known non-slice axis → skip its member role; unknown axis → PROVISIONAL, never silently dropped.
- The company menu = union of members from all prior public 10-Q/10-K filings + values already used for that company. Write menus cut at event/source public time; naming has no menu; repair may see full history.
- Producer outcomes per part (the kind ladder): (1) menu reuse — the producer judges SAME MEANING, code validates the pick is exactly a menu value and never near-snaps; (2) source-grounded off-menu coin (kind clear from prose); (3) `unknown:<value>` when the kind is unclear or a normalized label exists under multiple menu kinds without selecting context — never guess; (4) omit for true whole-company. Ambiguous prose must not guess.
- Unknown XBRL axis/member sentinel (code-only): `unknown:xbrlaxis_<lowercase UTF-8 hex of exact axis qname>__<normalized_member_value>`. Unknown values enter the company menu for later reuse.
- **FS-18 code dedupe (exact-after-normalization only):** an XBRL member whose normalized label EQUALS an existing value's normalized form folds INTO that value — the link clips on, no new value; never a fuzzy near-match snap. The producer's reuse is semantic (existing values shown first; unsure → coin new; the LLM assigns, never merges two existing identities).
- **FS-20 elimination guard contents (segment-family axes only; exact lists, never a regex):** HARD-EXCLUDE = a frozen exact-qname allowlist of ~24 pure eliminations (`IntersegmentElimination`, `ConsolidationEliminations`, …) — dropped from the menu, every exclusion LOGGED, and one that later shows real activity auto-demotes to provisional; PROVISIONAL = ~241 reconciling/Corporate/Other/Unallocated/blended/raw-intersegment members — own row, quarantined from cross-company reads, never deleted; KEEP = every other segment member (~3,000 real segments) — a missed coined elimination falls here, over-split-safe. A regex was rejected because it over-catches real businesses (~20% false positives, e.g. `GlobalPestElimination`). The exact member lists are data in the external `XBRL_SliceAxis_Catalog.md` §4.
- Stored slice values are first-write immutable. No human alias layer, no "confident alias" merge. The only label-drift grouping is read-time, company-scoped, member-anchored: all linked facts for both labels must share the same exact axis/member pair; prose-only drift stays split.
- `MAPS_TO_MEMBER` is fact-level enrichment: needs both axis and member, may be absent, carries the slice part it supports. FS-22 (cross-company recurrence for identity) is retired; FS-23 (cross-company slice-value comparison) remains open and must exclude residuals.
- Raw reads group by the full series key, never slice alone. Provisional slices stay out of cross-company analysis until promoted.

### 5.3 Measurement — FS-25, OD-9 `[FINAL]`

- An open, source-grounded, code-sorted token set in `fact_scope`. Not a closed enum, not a name field.
- The semantic step copies exact transient `measurement_raw_spans`; code alone normalizes: lowercase → every non-alphanumeric run → `_` → trim → collapse repeats → sort → join.
- A maximal contiguous qualifier span = ONE token (`adjusted, diluted` → `adjusted_diluted`); split only where non-qualifier prose intervenes.
- **Never-drop safety sink:** any number modifier not captured losslessly by name, period, unit, slice, or sequential-basis logic stays in measurement (e.g. `ttm` when the period resolver cannot build the true rolling window). When unsure, keep. Empty measurement is legal and never implies GAAP.
- No write-time synonym merging of tokens; equivalent-label views exist only at read time and never change identity.

### 5.4 Declared continuity and recovery — FS-26, OD-18..20, kernel recovery `[FINAL]`

- **CONTINUES_AS (OD-20):** a company-scoped, directional (old→new), dated continuity declaration, created ONLY when company text explicitly asserts the old label continues as the new with composition/methodology unchanged. Recast/recompose/reclassify wording triggers a code lexical pre-refusal. A dedicated blind strong continuity judge (not the sameness judge) must confirm the explicit declaration, unchanged composition, and both exact endpoints; otherwise refuse (fail-closed). The producer emits a transient `continuity_hint {kind, old, new, quote}` — no standing detector.
- It is read-only, reversible, and never propagates across flavor/family links. Driver endpoints use `(:Driver)-[:CONTINUES_AS {company_cik, evidence_quote, source_event_id, declared_at, created, quarantined}]->(:Driver)` — the `SAME_AS` structural twin. Slice-label/measurement-token endpoints (strings inside fact_scope; they cannot anchor edges) use a reified `(:ContinuationClaim {company_cik, kind: slice_label|measurement_token, old, new, evidence_quote, source_event_id, declared_at, created, quarantined})`, indexed by (company_cik, kind, old) AND (company_cik, kind, new). `CONTINUES_AS` is a class-level link minted live by producers, never part of the fact-edge inventory. The PIT gate is `declared_at`, per hop; `created` is forensic only; a quarantine suppresses application regardless of when discovered (the over-split-safe asymmetry).
- Determinism guards (in the commit transaction): at most ONE active (non-quarantined) outgoing continuation per (company, kind, old) — **fan-out refused**; fan-in (a second old into the same new) auto-quarantines BOTH; a cycle-closing continuation auto-refuses. All three are state-based, reversible refusals.
- Reads follow only declarations public before `as_of`, checked PER HOP, stop at the terminal label, and make no model calls. Exactly one reconciled-view instance exists (`CONTINUES_AS` chains); the unknown-axis qname-grouping view was reviewed and DEFERRED — do not rebuild without a fresh owner decision.
- **OD-18 (flagged ATTACH):** run the deterministic risk prefilter synchronously — exact triggers: a cross-industry exact-name attach · per-head industry-cluster count ≥2 · scope-qualifier heterogeneity, INCLUDING same-industry heterogeneity (two same-industry companies can homonym one word: subscriber-churn vs employee-churn); a flagged ATTACH gets a blind strong three-check (same cause + same causal scope + same mechanism, against the head's frozen birth anchor) before write. `REFUSE` can never be overturned toward a write; `UNSURE` gets one blind escalation and only `CONFIRM` writes; other results → specific re-coin or counted terminal skip; judge timeout parks. A QUARANTINED head blocks exact-ATTACH entirely (incoming facts PARK-RETRY — safe under-attribution). On ESTABLISHED heads only qualifier heterogeneity flags; on non-ESTABLISHED heads the ≥8-company condition also flags. Keep `flag_rate`, `refuse_rate`, `escalation_disagreement_rate`, `recoin_failure_rate` + the post-write sample audit. Accepted residual until OD-19's gate passes: a wrongly refused token-subset re-coin is counted, visible under-attribution by design.
- **OD-19:** generic token-subset matching becomes judge territory only after the K-pairs.v2 portion-family gate records zero wrong-same; until then inert. Cross-flavor, terminal-suffix, per-X, and OD-17 portion differences are PERMANENT refusals.
- **Recovery:** confirmed-wrong `SAME_AS`/`CONTINUES_AS` use their approved reversible quarantine paths (signal → two blind strong graders → quarantine flip + `RecoveryEvent`). A confirmed mis-attached fact is marked `disputed` (recovery-only boolean); disputed facts leave cross-company/history-weighted features until cleared. BASE_METRIC/family propagation remains CANDIDATE. Never delete, re-key, or move history. CLAIM is separate from OD-18, requires strong-judge confirmation if ever enabled, and currently ships OFF.

## 6. Units, signed values, periods `[FINAL]`

### 6.1 Units — UNIT-01..14, OD-10..13

- Exact unit enum: `usd` · `m_usd` · `percent` · `percent_yoy` · `percent_sequential` · `percent_points` · `basis_points` · `count` · `x` · `unknown`.
- The proven pure V2 resolver decides canonical unit and scale; the semantic extractor only copies signed unscaled source numbers + verbatim raw units.
- **Effective UNIT-04 (per-slot hints):** each numeric level or change slot carries its own required raw unit + a unit-kind hint (`money`|`ratio`|`count`|`multiplier`|`unknown`); money kind requires `money_mode` (`aggregate`|`price_like`|`unknown`), null otherwise. Resolve level and change separately.
- Validate final enum AND scaled value: glued billions → `m_usd` ×1,000; cents-on-aggregate and pre-scaled mistakes hard-fail; non-USD gaps may stay `unknown` (monitored).
- Units live on facts, not Drivers. A stated per-X denominator lives in the NAME while the value uses the base unit; the per-X lint (money level + stated denominator + no `_per_` name) is a hard failure. No `comparison_unit` — comparisons share `level_unit`. `level_unit` required when any level/comparison number is non-null; `change_unit` required when `change_value` non-null; `unknown` legal for either when the source does not safely resolve. No number → no unit resolution.
- **OD-11 (growth basis):** `percent_sequential` is a separate series; OD-11 CONSUMES the upstream-resolved `period_scope` (the period resolver runs first) and never infers it. Static-percentage gate first: bare "up/down X%" on a static %-level metric is `unknown` unless points/bps or "of/to X%". A points/bps unit WINS over any sequential/YoY wording; growth is never plain `percent`. YoY/comparable/annual growth → `percent_yoy`. Bare growth on a dated period defaults `percent_yoy` (the standard year-ago convention), overridden to `percent_sequential` ONLY on in-document sequential evidence — never company history. An immediately-prior comparable period → `percent_sequential`. Sentinel-horizon basis → `unknown` (fail-closed). **Annual pin: on an annual period sequential == YoY → always `percent_yoy`; `percent_sequential` is valid only on sub-annual periods (validator: `percent_sequential` + `period_scope=annual` is invalid).** A value stated on two or more bases SPLITS into one fact per basis. A numberless GROWTH fact may take its unit from source framing. Measurement adjustments (constant_currency, organic, adjusted…) are orthogonal — they ride the measurement slot and never decide the basis.
- **OD-12 (signed axis):** a net loss is negative, never a positive loss magnitude. A charge/provision is positive; a benefit/credit/release/reversal is negative. Bounds follow algebra ("loss up to 2B" = floor at −2B); zero-crossing ranges are legal; a numberless loss has no numeric bounds; conditional downside stays narrative. Co-stated one-sided bounds fuse under the normal within-event rule.
- **OD-13:** code never assigns beat/miss from sign — meaning decides favorability.
- **OD-10 (`series_unit`):** code writes it once at WRITE as a grouping tag. Level-bearing facts → the level's canonical axis (money canonicalized to the driver's one scale within a currency). Delta-only facts fold to the Driver's dimension only when the fact's OWN evidence makes the axis unique (metric nature + quote, never the name); any residual ambiguity → exact `change_unit` (own over-split group) or `unknown`, never absorbed. Numberless facts → `series_unit=null`, EXCEPT a withdrawal or reaffirmation, which copies exactly one clear prior guide's `series_unit` and otherwise fails closed. Reads group by equality only — no unit-family map, no unknown absorption. `series_unit` never rewrites `level_*`/`change_*` (those stay source-faithful).

### 6.2 Periods — PER-01..20

- `DriverPeriod` = the actual calendar window the fact is about; not event date, raw "Q1", forecast marker, or a fact-type substitute. One generic node serves all four lanes (`DriverPeriod` label, `gp_` IDs). Nodes store only `id`, `u_id`, `start_date`, `end_date`; fiscal framing stays on the fact.
- One `HAS_PERIOD` edge; meaning comes from the lane. Guidance REQUIRES its target period (real resolved period OR explicit sentinel). Metric/surprise use a stated, clearly implied, or safely derived real period. Action has a period only when a real window is stated — never force one; periodless action has no edge.
- Actual surprise uses the reported period; `guidance_vs_consensus` uses the guidance TARGET period even if ended (OD-21). Event metadata may supply an implied reported period only when exact, never for guidance-vs-consensus.
- Exact YTD/TTM/cumulative/stated ranges beat fiscal shorthand — keep real dates, never collapse to a quarter.
- Four sentinels for real dateless horizons, two-way stored invariant: `short_term`↔`gp_ST` · `medium_term`↔`gp_MT` · `long_term`↔`gp_LT` · `undefined`↔`gp_UNDEF`. Stored `long_range` is retired — a stated date range stores `exact_range`. Unresolved fields with no explicit sentinel hard-fail; action sentinels hard-fail; `gp_UNDEF` is never a quiet fallback.
- One shared fiscal resolver. Resolution order: exact dates → explicit sentinel → long range → month → half → quarter → year → pure-builder undefined (old parity only). Missing fiscal-year-end fails closed. Market-wide facts use calendar mode.
- Code builds the period ID; the same resolved ID appears in `fact_scope` and `HAS_PERIOD`, checked both ways. The resolved ID/dates are authoritative after write; raw fiscal year/quarter never regroup facts later. Never group by period alone.
- Instant is the legal one-day form; a duration with `start_date == end_date` is invalid input. Dates and constraints are write-once (a wrong first date does not self-correct; mismatch hard-fails).
- `time_type` (duration vs instant) is a REQUIRED semantic output, never a default.

## 7. The stored fact contract `[FINAL]`

### 7.1 The 24 counted fields — exact split

| Owner | Fields |
|---|---|
| Code, 6 | `id` · `fact_scope` · `series_unit` · `created` · `date` · `source_type` |
| Semantic/enrichment, 18 | `driver_state` · `quote` · `level_low` · `level_high` · `level_unit` · `change_value` · `change_unit` · `comparison_low` · `comparison_high` · `comparison_baseline` · `value_text` · `conditions` · `company_confirmed` · `xbrl_qname` · `fiscal_year` · `fiscal_quarter` · `period_scope` · `time_type` |

- `created` set only on create; `date` = full source timestamp; `source_type` enum: `8k` · `transcript` · `10q` · `10k` · `news`.
- Recovery-only `disputed` is outside the count, controlled solely by recovery.
- **Number shapes are self-describing:** point = both bands equal; closed range = both present, low < high; floor = low only; ceiling = high only; numberless = all null. Transient shape hints (`level_shape_hint` with level numbers, `comparison_shape_hint` with comparison numbers) are required-when-numbers-present, cross-checked, hard-fail on mismatch, then discarded.
- Change/comparison numbers are source-stated only; at most one primary baseline; a baseline may be present with null comparison numbers. Leave `change_value=null` when it could merely be derived from a closed shape (derive at read).
- A change-flavored unit (bps/percent-points with direction, no "to X") goes in `change_value` when the Driver's level is absolute, but in the level slots when the Driver itself is the rate/growth metric. Percent-only guidance stores its growth basis in `level_unit`; only the guide's own revision size belongs in `change_value`.
- Sign validator: with `change_value` present, `increased`/`raised` requires positive and `decreased`/`lowered` negative; `beat`/`missed` excluded (favorability is semantic, OD-13).
- `comparison_baseline` ∈ `consensus` · `prior_year` · `sequential_period` · `previous_guidance` · null. There is NO `internal_target` value: own-target phrasing maps to `previous_guidance`, else null. Beat size is never stored — it derives at read as `level_low − comparison_low`, defined only for closed point comparisons.
- `value_text`: guidance-only, numberless-only, normalized, ≤200 chars, rejects stored numeric values, allows date/period anchors.
- `conditions`: guidance-only; its clause must remain in the quote.
- `company_confirmed`: guidance-only boolean, producer/CORE-derived from who-said-it attribution (owner ruling 2026-07-15, Q1 — channels submit attribution EVIDENCE only). `true` = stated/confirmed by the company or its management; `false` = the RESERVED meaning, a future explicitly-ALLOWED third-party/rumored guidance-like claim not confirmed by the company (no such class is enabled today — enabling one is a part-2/news-channel owner decision); UNCLEAR attribution is SKIPPED, never stored as a guessed boolean. A later company confirmation is a NEW `true` fact at its own public time — history is never rewritten.
- `xbrl_qname`: metric-only enrichment, dual-stored with the concept edge.
- `period_scope` enum: `quarter` · `annual` · `half` · `monthly` · `ytd` · `ttm` · `exact_range` · `short_term` · `medium_term` · `long_term` · `undefined` (never `long_range`).

### 7.2 Per-lane matrix

| Field | metric | guidance | surprise | action_event |
|---|---|---|---|---|
| Core identity, state, quote, source, Driver edge | required | required | required | required |
| Period | when real | required | when real; guidance-vs-consensus required | rare, when real |
| Level/change | only when stated | only when stated | only when stated | only when stated |
| Comparison values | when stated | prior band when stated | expectation when stated | when stated |
| Comparison baseline | only prior_year/sequential; expectation baselines FORBIDDEN | consensus FORBIDDEN | required: consensus/previous_guidance | when stated |
| `surprise=` slot | forbidden | forbidden | required | forbidden |
| `value_text` · `conditions` · `company_confirmed` | forbidden | allowed under exact rules | forbidden | forbidden |
| Direct XBRL concept | allowed by enrichment | forbidden; inherit | forbidden; inherit | forbidden |

Routing consequences: a reported actual vs consensus or prior guidance writes a surprise PLUS its metric home fact. A forward guide vs consensus writes a surprise PLUS its guidance home fact. A guide vs the company's own prior guide is guidance MOVEMENT, not a surprise. A temporal comparison (prior year/sequential) is a metric change, not a surprise.

### 7.3 Edges, verdict, DailyCompanyMoveEvent

- Exactly one `OF_DRIVER` edge to a typed Driver. Every fact is source-event-based with `FROM_SOURCE`; News is the source on the macro/news path; a `DailyCompanyMoveEvent` (DCM) is only an optional verdict target, never a substitute source (a pure-macro fact with no source stays parked). Company is reached through the Event — no `FOR_COMPANY` edge on facts.
- `MAPS_TO_CONCEPT`: metric-only, zero-or-one, best-effort, paired with `xbrl_qname`. `MAPS_TO_MEMBER`: zero-or-more on any lane, carries `slice_part`.
- **`EXPLAINED_BY` verdict = an edge, never a node**, from an Event or DCM to the DriverUpdate it attributes. Key = explained target + driver + fact_scope + producer (two producers may disagree). A uniqueness check prevents one verdict key pointing at rival same-day source facts; live-over-backfill precedence applies.
- Verdict axes (independent): `stock_impact` ∈ `long`|`short` (the Driver's push, not necessarily the net move) · `weightage` ∈ 0.1..1.0 deciles or null (independent force, never a share, never summed to 100%; null = direction known, size not) · `confidence` ∈ 0..100 tens (certainty the attribution is true). Other fields: producer, mode (`live`|`backfill`), id, created, judgment hash = first 16 hex of SHA-256 over `stock_impact|weightage|confidence` (mode excluded; producer in the key).
- Reads may derive `share_i = weightage_i / Σweightage` within one event+producer and signed force from weightage×impact — never stored as true causal shares. Never show realized return to the verdict producer.
- DCM: own label, `id=dcm:<cik>:<trade_date>`, `FOR_COMPANY`, `ON_DATE`; realized return stays in the price graph; trade date comes from the returns/trading-day layer. Same-day filing/DCM overlap: the filing wins at read; the DCM is ignored, never deleted. `[OPEN: DCM significance threshold · pure-macro source · two-independent-catalyst case]`

## 8. XBRL enrichment (text-created facts) — XC-01..18 `[FINAL; build-pending rollout]`

- Goal: attach the exact company-reported concept or attach NOTHING. A wrong concept is far worse than an absent one. Rejected forever: live value match, token match, static dictionary, simple multi-method agreement.
- Pipeline: deterministic guards → PIT company concept menu → the locked cheap model picks one-or-null → exact in-menu check → adversarial verify (default refute) → deterministic veto/backstop → write or abstain.
- **XC-04 (model):** Haiku, locked — structure + the deterministic layers give it top-model precision at cheap cost. Documented alternatives: Opus/Sonnet (similar precision, higher cost); Haiku-pick + Opus-verify (~90% recall).
- **XC-05 (guards, ordered G2→G0→G1, pure code, zero LLM):** G0 = events/macro (resignation, buyback, oil_price, interest_rates, tariffs, weather…) · G1 = ratios/derived/growth (margin, `_growth`, roic, ebitda, fcf, `_per_square`, `_mix`…; tax_rate/effective_tax_rate are NOT here — real GAAP concepts) · G2 = non-GAAP/adjusted, keyed on the **measurement set** (primary; the name-prefix regex `adjusted_/non_gaap_/core_/organic_/pro_forma_` survives only as the legacy-name fallback). GAAP-compatible measurement sets: empty, `{gaap}`, `{basic}`, `{diluted}`, `{reported}`, `{as_reported}` — anything else abstains conservatively. Guards are principles, not a merge dictionary.
- **XC-06 (two loose prompts):** PICK = "the ONE menu qname that IS exactly this metric, or null" (SAME metric only — cost-of-revenue≠revenue, subtotal≠total, basic≠diluted; two equal candidates → higher usage). VERIFY = "STRICT auditor, default REFUTED when unsure; refute related-but-different, GAAP-vs-non-GAAP, gross-vs-net, subtotal-vs-total, wrong statement, or a dimension instead of the consolidated line." Prompts stay loose (scope is the veto's job — tightening costs recall). Parse default: no match ⇒ refuted.
- **XC-07 (deterministic veto — can only ABSTAIN, never create/change a link):** A = point-in-time share count must be `instant`, not duration weighted-average · B = bare eps/share_count must not map to the *Basic variant (convention = diluted) · C = a per-share metric must not map to a total-$ Cash concept · D = the exact 4-entry component-for-aggregate DENY set: sg_a→G&A · sg_a→S&M · operating_expenses→SG&A · total_debt→NotesPayable. Measured (274 companies): A–C 42→18 wrong; +D → 1 wrong, no recall cost.
- Menu = the company's consolidated numeric concepts + metadata, cut at the fact's public time for history (live may use latest). Pass the whole menu; check the returned qname EXACTLY (same prefix form both sides).
- Store both `xbrl_qname` and `MAPS_TO_CONCEPT`; bounded qname match across taxonomy years; a missing graph concept never blocks the fact and self-heals later.
- Guidance/surprise inherit through `BASE_METRIC`; action abstains; non-GAAP measurement blocks inheritance (XC-12 carve-out).
- Invocation uses in-session subscription agents — SDK/API-key use is NOT approved without separate owner approval.
- Evidence supports high precision, not universal zero error — keep the caveats and sampling monitors beside the numbers. `[CONDITIONAL: XC-16 calculation-hierarchy veto recommended before full rollout — timing open]`
- The XBRL-NATIVE materializer (facts born from tagged XBRL, not text) is a separate CANDIDATE bundle, dormant until owner ratification — see `BUILD_AND_OPERATIONS.md`. The `09` field rider (`origin`, `xbrl_link`, empty≡GAAP folding) stays dormant with it.

## 9. Read, collapse, and point-in-time rules `[FINAL; build-pending]`

- Full series key: company · Driver · fact_type · slice · resolved period · period_scope · measurement · `series_unit` · `time_type` · surprise subtype (surprise lane only). Family added only for cross-flavor views.
- `series_unit` groups by equality — no unknown absorption, no runtime family map.
- Within one event: fuse before collision. Slices beat a vague `mixed` record when clean parts are stated; a consolidated fact exists only when itself stated.
- Render order: level shape → signed change → comparison → guidance `value_text` → truncated verbatim quote (last display fallback only). The collapse comparator is the numeric `level_*` signature, or normalized `value_text` for qualitative facts — never the quote.
- Citation id = Driver name + fact-scope suffix when needed.
- Standing per-X policy level = metric; a discrete decision to initiate/change/suspend the policy = action.
- Direction + bps/percentage-points without "to X" is a change, not a level. `narrowed` is read-derived from consecutive closed widths, never stored.
- Same company/series/day: source rank `8k > transcript > 10q > 10k > news`; ties → later timestamp, then source id. Across days: latest wins as current view, priors kept as PIT history. Amendments are NEW facts at their public time (OD-14) — the latest-date rule makes them win naturally.
- "Day" = Eastern Time. Backtest cutoff strict `date < as_of`; live sees the current graph. Never expose realized returns.
- Member-anchored grouping: deterministic, per company + slice part, requires one exact shared axis/member pair, changes display grouping only.
- Every read result is labeled `raw` or `reconciled`. Reconciled views are disableable and use only deterministic PIT edges (`CONTINUES_AS` chains, per-hop cutoff).
- Guidance movement is read-derived (`effective_driver_state`), never written back. A source-stated raised/lowered/reaffirmed/withdrawn is STORED as said; bare numbers store `unknown`, and the read layer derives introduced/raised/lowered/reaffirmed MECHANICALLY (the midpoint rule) from the prior COLLAPSED current-view value in the canonical guidance series — company · driver · fact_type=guidance · slice · target period · measurement · `series_unit` (grouped by EQUALITY; there is no unit-family map — reversal #36/OD-10; the OD-14 source block's "unit-FAMILY" wording is stale against that later exact rule) · time_type; never across years, quarters, series units, or slices. No prior → `introduced`; not safely comparable (open/mixed shapes, numberless prior) → `unknown`. Self-healing: a late fact re-derives the timeline at the next read. Corrections are excluded: an amendment fixing a value with no business-change wording — identified from source/event metadata or explicit correction wording — has its `effective_driver_state` FORCED to `unknown`; the mechanical derive never reads a typo fix as a raise or lower.
- Withdrawal fan-out is the ONE bounded derived write, code-generated and strictly bounded. Fan out ONLY when ALL hold: the source clearly STATES a withdrawal (not a policy remark like "suspending guidance practices") · with an EXACT scope (exact driver/period/slice, or a true-universal like "all FY2026 guidance") · expanding only to OPEN guides (the collapsed current view, not already withdrawn, window still relevant) whose fact_scope is contained via the RESOLVED period/scope, never loose text matching · and the same source does not replace/reaffirm/keep a covered guide. Scope unclear → do NOT fan out. Add-only: a late older covered guide synchronously receives its missing `withdrawn` fact under the same conditions; reads ignore no-op re-withdrawals of an already-withdrawn guide; never delete. A retraction with no replacement → a numberless fact ONLY when driver/scope is exact (for guidance = `withdrawn`); inexact → don't guess. Amendments remain new facts at their public time.

## 10. Status tags (generated; owning rows live in STATUS_AND_HISTORY.md)

- **FINAL / BUILD-PENDING:** Track A remainder (fold/tree mirrors, finalizer, real folds, WP-FC-RUN, OD-6 fitness gate — never run) · UNIT-14 production wiring · PER-20 resolver build + 21 tests · slice table materialization + PIT menu code · concept-linker vetoes C/D + PIT query build · the whole Track B writer/validator/CLI/park-ledger stack · read layer · verdict/DCM writer · channel adapters + certification · Track C execution · incremental refresh.
- **DESIGN-INCOMPLETE (not final law, not merely build-pending):** the production running layer — schedules, central ledger, retries, backfill, QA/alerting/budgets, model policy, recovery (`BUILD_AND_OPERATIONS.md` §7 lists what the runbook must still define and prove). The OD-5 change scanner is a RECOMMENDATION only, never final design.
- **CONDITIONAL:** OD-19 (inert until K-pairs.v2 zero wrong-same) · XC-16 timing · model-role membership (experiment-gated) · XBRL-native materializer + `09` rider (dormant until ratification) · multi-run concept stability/caching (only if monitoring justifies).
- **OPEN (owner):** G1 live reuse display · catalog target 796-vs-786 + lifecycle/IPO absorption · full model/cost policy beyond signed EXP-2 · FS-23 cross-company slice comparison · 8-K taxonomy · DCM threshold/pure-macro/two-catalyst · Track B dual-producer thresholds · non-USD expansion · metric `value_text`/action `conditions` revisit triggers · Driver Genesis channel-charter questions · Track C history-gap acceptance · third-party `company_confirmed=false` class enablement (part-2/news-channel).
- **CANDIDATE:** Admission Kernel v3.4 bundle (accepted parts listed in §4.2/§5.4 are law; the rest needs the named owner bundle) · XBRL-native materializer · Bayes learner proposal (unvetted) · Driver Genesis restructure (rationale only).
- The five 2026-07-15 owner rulings (Q1 core-derives · Q2 no-change · Q3 offline catalog + lazy born-complete · Q4 XBRL dimensions=[] amendment · Q5 first-fact guard scoped to bare names) are folded into §3-§7 above; their decision record lives in `CONSOLIDATION.md` §10.2 until `STATUS_AND_HISTORY.md` carries it.
