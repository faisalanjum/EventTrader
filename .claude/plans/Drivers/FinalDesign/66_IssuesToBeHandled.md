# 66 · Issues To Be Handled — FinalDesign(Claude) review backlog

---

## §0 · MASTER ISSUE CENSUS — every known issue, merged, deduplicated, validated (2026-07-05)

> **What this is:** ONE non-redundant list of ALL issues: the 2026-07-05 verified audit's top-20 findings (workflow wf_66c1adbe-a73: 28 readers/cross-checkers over the 2026-07-04 doc set → 221 findings ranked → top 20 adversarially verified, 12 confirmed · 6 partial · 2 refuted) **merged with** every pre-existing row of this file (ISS-1…62 · ISS-D1…D16 · §4 edge cases · the 2026-07-03 audit tail), each entry re-validated against the current docs on 2026-07-05. Audit tags `[C#/P#/R#]` = the verified top-20.
> **Statuses:** **OPEN-DESIGN** = needs a design decision → full resolution block in §0.R · **OPEN-DOC** = decision already made, wording/back-port debt only · **PARKED** = owner-deferred, home named · **ACCEPTED** = conscious residual, by design · **CLOSED** = verified resolved (pointer = the proof) · **NON-ISSUE** = verified refuted, do not re-raise.

### §0.1 Grounding — what this system is FOR (every fix below is judged against this)

**The end goal (01 §Purpose · 14 §7).** One shared catalog of reusable causes (**Drivers**) + dated, evidence-backed facts about them (**DriverUpdates**) + graded attributions (**EXPLAINED_BY** verdicts), so that scattered mentions across filings/transcripts/news line up into ONE clean history per cause — across companies and over time. That clean history is what gets acted on: grade each cause against what the stock actually did → learn from the past → predict the next move → trade. The end state (14 §7) is a living graph: every new asset auto-converts into the right Drivers/DriverUpdates, no human in the loop, ~100% recall and precision at the lowest practical cost. The graph's power comes from its STRUCTURE being right — which is why identity and integrity rules dominate this whole design.

**The five integrity invariants — a fix is WRONG if it violates any one:**
1. **One name = one meaning; over-merge is permanent, over-split is cheap → unsure = keep separate** (THE law, 01). Nothing may fuzzy-match, near-snap, or silently default.
2. **Store-when-stated** — never fabricate or compute stored values; the quote is the truth (T1.3). The only code-derived exceptions are explicitly enumerated (implied periods PER-06; withdrawal fan-out; ISS-16's derived surprise STATE — a classification of two stated numbers, never a number).
3. **Deterministic, producer-free, code-built identity** — id = event + driver + fact_scope; the LLM never builds ids; re-runs MERGE in place; ids are immutable (T1.4/T3). Any under-specified identity recipe is a fork risk between two builders — the worst class of bug here.
4. **Point-in-time discipline** — writes and menus see only ≤ event-time data; predictors never see realized returns or future facts (T1.5). Look-ahead corrupts the learn→predict loop invisibly.
5. **LLM judges meaning, code checks structure, everything fails closed** — validators hard-fail; enrichment (XBRL links) is never identity; a missing link is safe, a wrong link is the cardinal failure (T1.6, FS-04).

**The operational bar (14 §7):** minimal machinery — no new component unless it clearly improves recall, precision, cost, speed, or reliability; prefer reusing the proven substrate; every unresolved case must be visible (parked/logged), never silent.

### §0.2 The master list

**A. OPEN-DESIGN — needs a decision (11). One resolution block each in §0.R.** *(OD-1, OD-2, OD-6, OD-8 owner-approved 2026-07-05 and OD-13 owner-approved 2026-07-06 → moved to table B: decided design, back-port debt only; IDs unchanged.)*

| # | Merged from | Issue (zero-ambiguity one-liner) |
|---|---|---|
| OD-3 | ISS-13 | NAME-11 step 2 ("brand/product that itself moves OTHER companies → NAME it") is a cross-company judgment, but the leaf reader is blind ("sees only its chunk; no other company; no catalog" — PIPE-10). Whether the reader may use world knowledge or must defer the name-vs-slice call is unstated. |
| OD-4 | ISS-14 | FS-22 "a slice VALUE recurring across companies ⇒ GENERIC" over-generalizes: `geography:china`, `product:advertising` recur across companies AND genuinely compare; only grab-bag values (International/Other/Corporate) deserve the flag. |
| OD-5 | ISS-8 · 14 §3 #13 | The scanner/change-flag layer (mission step 7, 01 §7) is load-bearing rationale inside LOCKED 09 §4/§9 decisions yet designed nowhere: no trigger rules, no definition of "meaningfully changes", no track owns it, 90 §D omits it. |
| OD-7 | [P5] · ISS-18 residual · 14 §3 #10 | Live governed-create has no fact_type stamping path (Track A's finalize hard-fails on already-stamped input; FACT-16 rejects facts on fact_type-less Drivers), and once a live-created Driver acquires facts, immutability (13 §8) leaves no exit for a mis-name/mis-type. |
| OD-9 | 14 §3 #3 | Measurement multi-word tokenization is unpinned ("cash EPS" → `cash_eps`? `casheps`? `{cash}`?) — identity-bearing (fact_scope slot). |
| OD-10 | 14 §3 #4 · ISS-55/UNIT-12 | The read-time unit-FAMILY map (which of the 9 units group into one series slot, 09 §6.1) is named NEW code but never enumerated; entangled with the open `percent_qoq` decision. |
| OD-11 | 14 §3 #5 · tail-G1 #6 | 09 §7 hard-stamps %-only guides as `percent_yoy` — wrong denomination for QoQ-guiding companies (semis); actively wrong data, worse than `unknown`. |
| OD-12 | 14 §3 #6 · tail-G1 #2 | Negative/loss values have no sign convention: "a loss of up to $2B" is a ceiling in loss-space but a floor in signed space; the shape hints cannot catch a wrong choice; identity + rendering fork between implementers. |
| OD-14 | 14 §3 #8 · tail-G1 #3/#5 | No chronological-write invariant: late old-dated filings (first-class in the refresh design) corrupt derived guidance states + withdrawal fan-out, and can retroactively violate the Event/DCM single-target rule (12 §10.9 checks only at creation time); no detector, no repair trigger. |
| OD-15 | 14 §3 #9 · tail-G1 #5 | Two concurrent producers can coin near-synonym Drivers at the same moment — no locking/serialization point for live Driver creation is defined. |
| OD-16 | 14 §3 #11 · tail-G1 #8 | Nobody owns catalog→Neo4j materialization: 12 assumes Driver nodes exist ("Driver.name assumed from Track A"); 10 declares Neo4j production writes a non-goal (PIPE-05) — a missing build step between the two manuals. |

**B. OPEN-DOC — decision already made; wording/back-port debt only (18).**

| # | Merged from | Debt |
|---|---|---|
| OD-1 | ISS-19 · ISS-20 · [C10] | **OWNER-APPROVED 2026-07-05 in RES · OD-1.** Back-port the terminal-suffix admission gate, two independent source checks, `terminal_admissions.json`, latent-anchor rules, exact latent graduation, and deterministic finalization hard-fails into 10 PIPE-24/25/26/36; update 12/14/90 pointers. |
| OD-2 | ISS-17 | **OWNER-APPROVED 2026-07-05 (v3) in RES · OD-2.** Bare names use "metric must prove itself": deterministic rules first · C1=action_event stamps directly · C1=metric requires the quote-backed metric-proof challenge on full evidence · unproven → action_event (safe default), marked `metric_proof_defaulted` + counted in `--final` warnings · bare guidance/surprise = naming defect (F3/re-coin) · F2 accepts only deterministic / OD-2-proven / OD-1-latent-proven metric bases · no queue, no lists, no third model, no re-type. Back-port → 10 (PIPE-24/26 + one merged F2 spec), 95 row #29, OD-7 cross-notes (live park/retry + first-fact guard). |
| OD-8 | tail-G1 #4/#9 · E2 · 14 §3 #1/#2 | **OWNER-APPROVED 2026-07-05 (FINAL) in RES · OD-8 — back-port only.** Signature-only quote_hash (full sha256 over 10-slot canonical JSON; quote/driver_state/company_confirmed excluded) · conflict-keyed membership (exact/compatible/conflict; strict park in multi-member groups) · exact sibling probe · write-and-flag late collisions · FACT-14b signature-slot scope · batch + race pins. Back-port → 03 FS-03, 11 T3.4, 12 FACT-12/14/17 + §12.3 fixtures, 95 row #30; update §4 E2. |
| OD-6 | ISS-9 · 14 §3 #12 | **OWNER-APPROVED 2026-07-05 (v3) in RES · OD-6 — back-port only.** Quality budget = wrong merges ONLY: GREEN requires ≥3,000 pre-registered graded slots (fixed denominator = key slots × producer runs, ungameable) · zero confirmed wrong merges (2-grader confirmation) · zero unresolved flags (one blind re-grade round, then INCONCLUSIVE blocks green) · existing PIPE-37 bars pass; RED/inconclusive → fix prompts/rules → regression fixtures → fresh unseen key for final GO. → into 10 PIPE-37; closes 14 §3 #12; annotate ISS-9. |
| OD-13 | 14 §3 #7 · tail-G1 #1 | **OWNER-APPROVED 2026-07-06 in RES · OD-13 — back-port only.** Favorability (beat/missed) = a PRODUCER MEANING judgment, not code arithmetic. Code computes only polarity-free `position` (above/inside/below/at_floor/at_ceiling) + `in_line`-when-wordless-inside-closed-range; NEVER maps above→beat, NEVER keyword-matches, NEVER assumes higher=better. Producer sets beat/missed/in_line from full-phrase MEANING (negation/idiom/polarity/scope-aware, bound to THIS actual-vs-expectation comparison); position words + loosely-used verbs ("beat the budget") → polarity test; wordless-outside-range needs a transient DISCARDED polarity proof (allowed only if a higher value has NO mainstream story of being the good surprise — capex/R&D/inventory/hiring/cash-burn need framing, else `unknown`); genuine doubt → `unknown`. Amends ISS-16 (12 §10.5 — drop the >high→beat arithmetic + the directional hard-fail) + DU-16.2 (drop beat/missed from the sign rule). `change_value` stated-only + null-when-sign-ambiguous. Report-only mixed-polarity monitor (no write-block, no human). Stress-test-confirmed (13/14 blind-grader unanimous; all 4 break-classes closed). Back-port → 12 §10.5/§16 · 07 DU-16.2 · 14 §3 #7 · 90 §E · 95 #31; producer-contract prose → part-2 packet (12 §13). |
| D-1 | [C1·P2·P4] · 14 §6 | 04 UNIT-04 is still LOCKED at ONE hint pair per numeric item; owner 2026-07-03 (12 §10.3/FACT-23) pinned per-slot pairs (+ `level_unit_raw`/`change_unit_raw`); 04 carries no amendment marker and no 95 row exists → under the authority chain the dead rule formally wins for a builder of 04 alone. |
| D-2 | [C2·C11] · tail-G2 | 09 §3 + 09 §8 + 07 §D banner still state the pre-OBJ-2 consensus-only metric-FORBID; the correct both-expectation-baselines rule lives only in 09 §4's matrix + 07 DU-15; 95 #24's "amends" list omits the three stale spots. |
| D-3 | tail-G2 · 13R §16 | Alias-layer residue: FS-19 still grants code "a confident alias" merge; FS-02 and 09 §3 still describe "per-company alias files" as the read-time drift view — but the owner REJECTED the alias layer (member-anchored grouping T12.9 is the ONLY approved recovery, census §14.4) and no 95 row records that rejection. |
| D-4 | [C12] | 12's "fully build-ready" STATUS vs 14 §3's P0 recipes inside Track B's own domain (quote_hash, tokenization, unit-family map…): "all owner decisions closed" ≠ "every identity recipe pinned to the byte" — the banner misleads a coding agent into starting §17 step 1 without the quote_hash recipe. |
| D-5 | ISS-25 | 08 XC-12 omits the "any non-GAAP measurement token ⇒ NO concept inheritance" carve-out (it lives only in 09 §3 and 12 FACT-33) — a reader of 08 alone inherits GAAP concepts onto adjusted guidance/surprise facts. |
| D-6 | ISS-22 | FS-24 states the consumer read key as driver+slice+period; the locked series key is company·driver·fact_type·slice·period·measurement·unit·time_type (+BASE_METRIC family) — literal FS-24 blends guidance/metric/surprise sharing one period. |
| D-7 | ISS-12 | FS-03's "restatements (same value) merge" reads as a WRITE-time rule inside the identity section; its own example (press release + MD&A) spans different events → different ids that CANNOT write-merge; the real mechanism is glue-rule-9 READ-time collapse. |
| D-8 | ISS-10 | "The LLM never merges" (FS-04/PIPE-04) overstates: at the NAME layer the LLM does decide fusions (dedup SAME_AS proposals, D5 SAME unions); safety comes from reversibility + D1 approval-tracing + Refute, not decision-abstinence. One clarifying sentence. |
| D-9 | ISS-1 | 90 §A omits 4 owner-opens that live only in 10 §13 (G1 reuse-display rules · K2 fold-repair gate · target N 796-vs-786 · lifecycle/dormancy/IPO); 14 §5 now unions them, but 90's "every open thread in one place" claim stays broken. |
| D-10 | ISS-31 | The news-excluded-from-leaf-build decision's rationale lives only in 10 §14's adjudication record; the normative body never states the consequence: news-coined drivers can enter ONLY via live governed G2 (itself blocked on the open G1 display rules). |
| D-11 | [P3] | 10 PIPE-03's hard-fail verb list lacks "orphan", and no 10 §9 step imports existing fact-bearing Driver names as protected inputs — 13 §8 requires both ("hard-fail if a sync would orphan, rename, delete, or re-type"). |
| D-12 | 14 §6 | Glossary debt for cold-start builders: G1/G2 (two unrelated systems: concept-linker guards vs catalog admission gates), "menu" (3 artifacts), "slice" (also batch-splitting in the Track A diagram), "created" (system write-time on facts vs public-filing-time in PIT menu queries), "parked", "fail-closed", "archive". |
| D-13 | ISS-29b · ISS-38 · ISS-39 · ISS-40 · ISS-43 · ISS-47 · ISS-48 · ISS-49 · [P1] · [P6] | One-line-nit cluster: 09 §5 cites "(§6.6)" for citation IDs (actually glue rule 5, §6.5) · 95 rows #6/#7/#8/#12/#14/#15 lack live back-pointers · 95 #12 still carries stale "(re-confirm at slices)" · 00 dates 10 as "2026-07-02" vs 10's STATUS 2026-07-03 · NAME-10's part-list ≠ FS-06 kinds (says "brand", omits entity_ownership) · FS-08 says "one of the 6" (should be 6 + unknown) · entity_ownership caution (99 §5.7) absent from 03 FS-06 · the FS-14 menu-union reversal has no 95 row (inline source-note only) · 00's census row says "Blocks: T1…T15" but Tn.m labels stop at T12.9 · DriverPlan.html's authority-tiebreak sentence ("newer owner ruling in 11–14 beats older wording in 01–09 until back-ported") appears in no md doc. |

**C. PARKED — owner-deferred, with homes (deliberate, not forgotten).**
DCM significance threshold + pure-macro source (+ the 09 §4 pure-macro FROM_SOURCE carve-out that ships with that decision — ISS-26) → 90 §C · FS-23 cross-company value comparison → 90 §A · §10 dormant XBRL-link rider → Codex §4.8 / part 2 · blanket-withdrawal fan-out (owner sign-off noted) → 09 §7 / 90 §C · 8-K 24-tag taxonomy + filing-amendment handling → 90 §A (amendments also feed OD-14) · final model policy incl. ISS-27's "Sonnet-classifies has no MODELS slot" half → 90 §A / PIPE-30 · G1 reuse-display rules · K2 fold-repair gate · target N 796-vs-786 · lifecycle/dormancy/IPO absorption → 10 §13 · XC-16 calc-hierarchy veto → the pre-full-universe gate (90 §B).

**D. ACCEPTED — conscious residuals (recorded so nobody "fixes" them by accident).**
ISS-41 (wrong-link "cardinal sin" vs "recoverable" rhetoric — both true: precision-first design, recoverable enrichment) · ISS-44 (G2's GAAP-compatible measurement set is a deliberate operational rule) · ISS-45 (DU-06's bare-root defaults are part of the LOCKED fact_type decider, not a naming rule — NAME-19 doesn't govern it) · ISS-46 (lower-fold-collapsed variants keep evidence only in the rep's union — PIPE-28's variant duality, by design) · ISS-51 (MF-08's chain shape is fold-dependent per PIPE-25's pinned lookup) · ISS-53 (relayed unconfirmed surprise: source_type+quote carry provenance; revisit at the first news-sourced surprise census) · ISS-56 (non-USD money → `unknown` + counter; UNIT-12-style revisit) · ISS-62 (first-pass under-extraction: accepted at write, measured at 12 §12.5; the no-null-clobber merge makes re-runs safe) · measurement drift ("adjusted" vs "non-GAAP") splits a series — locked accepted loss (09 §5) · deep-collapsed non-suffixed cross-flavor fusions (10 Round-5 accepted residual) · E6 (segment-structure gap strands a segment until FS-23) · same-day 8-K value outranks same-day 10-Q exactness (09 §9 conscious acceptance).

**E. CLOSED — validated resolved (pointer = proof).**
ISS-2 (equal-rank tie-break — census §14.1) · ISS-3 (verdict layer LOCKED — 12 §10.1) · ISS-4 (hex unknown-axis grammar; 03 FS-15 wording applied 07-04) · ISS-5 (95/99 headers now name the full live set — 07-04) · ISS-6 (member-anchored grouping T12.9) · ISS-7 (history-read PIT — census §14.3) · ISS-11 (id event = FROM_SOURCE always — 12 FACT-11) · ISS-15 (skip logging + documented reliance — FACT-26b) · ISS-16 (three-way routing LOCKED — 12 §10.5) · ISS-18 (governed-create-first — 12 §10.6) · ISS-21 (period eligibility gate — 12 §10.7/95 #23) · ISS-23 (start==end duration = illegal input — FACT-16.15) · ISS-24 (XC-13 now carries the reconciling final-score sentence) · ISS-28 (DCM own label — 12 §10.1) · ISS-30 (ET day convention — census §14.2) · ISS-32 (census §6.4 legend note) · ISS-33 (in substance: 12 FACT-16 rule 7 pins change-null-when-derivable) · ISS-34 (change_unit mirror — census §14.6) · ISS-35 (DU-22 now keys on explained_target) · ISS-36 + ISS-54 (superseded by Track C v2.0 — no replay, no both-label transition) · ISS-37 (00 §2 now flags DriverOntology/INDEX stale bits) · ISS-42 (designed: FACT-19 date-mismatch assertion; build-gated PER-20) · ISS-50 (99 is non-authority; validators build from 12 FACT-16) · ISS-52 (within-flavor action SAME_AS legal — 12 §11) · ISS-57 (artifact-vs-graph-node reconciliation stands) · ISS-58 (optional_links dropped — PIPE-21; 99 §2.14 self-flags) · ISS-59 (10 §9 governs Track A) · ISS-60 (per-X lint escalates to hard-fail — FACT-25) · ISS-61 (shape hints required-when-numbers-present — census §14.7) · audit [C3-C9] (THIS file's ledger desync — fixed in place 2026-07-05, see the ✅ annotations on the rows) · tail-G2: FS-15 hex ✅ · 00 coverage rows ✅ · 95/99 headers ✅.

**F. NON-ISSUE — verified refuted; do NOT re-raise.**
ISS-D1…D16 (§3 below, refutations recorded) · [R1] "three different homes for live G1/G2 wiring" — REFUTED: 10 PIPE-22, 12 FACT-04, and 14 §4 all converge on ONE home (part 2, blocked on the G1 display-rules owner decision) · [R2] "13 §7's park rule contradicts FS-15/FS-19" — REFUTED: FS-19's "unsure → coin new" answers WHICH value a real narrower part gets; 13 §7's park answers WHETHER the source names a narrower part at all (slice-presence); different questions, no conflict (13 §7 explicitly preserves the unknown:value path).

**Traceability — the verified top-20 → this census:** C1=P2=P4 → D-1 · C2=C11 → D-2 · C3 → ISS-11 ✅ · C4 → ISS-60 ✅ · C5 → ISS-52 ✅ · C6 → ISS-15 ✅ · C7 → ISS-4 ✅ · C8 → §5's stale verdict-lock row (fixed in place) · C9 → ISS-37 ✅ · C10 → OD-1 ✅ owner-approved · C12 → D-4 · P1 → D-13 · P3 → D-11 · P5 → OD-7 · P6 → D-13 · R1/R2 → F. *(The other 201 lower-ranked audit findings were deliberately left unverified — mostly doc-hygiene; full list in the wf_66c1adbe-a73 output. Spot-checks show they raise no category this census lacks.)*

### §0.R Resolution blocks — one issue at a time (full treatment: verify → define → recommend → confidence)

*(Written in work order: the OPEN-DOC debts first — their decisions already exist; then the OPEN-DESIGN items. Each block is self-contained.)*

#### RES · SYNC — this ledger's own desync [C3 · C4 · C5 · C6 · C7 · C8 · C9] — ✅ APPLIED 2026-07-05

1. **Real?** YES — all seven independently verified (adversarial re-read, quotes matched). 12 §11's header promised "the ledger 66 gets these annotations after owner review"; the §10 bundle WAS owner-decided 2026-07-03, but the write-back never happened.
2. **The issue, exactly:** seven places where this ledger showed OPEN for something already decided: ISS-11 (id event pinned) · ISS-15 (skip logging) · ISS-52 (within-flavor SAME_AS) · ISS-60 (per-X lint hard-fail) · ISS-4's tail ("FS-15 wording pending" though applied 07-04) · §5's live-opens still leading with the verdict lock (locked 07-03) · ISS-37 (00's stale-trap flags applied). Danger: a future bot re-litigates decided questions or "fixes" them a second, different way.
3. **Fix — APPLIED in place in this edit:** ✅ annotations on all seven rows plus the §4 E1/E8/E9 edge-case pointers, each citing the deciding doc — using this file's existing annotation convention. Zero design content changed.
4. **Confidence: 10/10.** Pure bookkeeping alignment with decisions recorded in 12/07/03/00; no interference possible; nothing simpler exists.

#### RES · D-1 — amend 04 UNIT-04 to per-slot unit hints [C1 = P2 = P4]

1. **Real?** YES — verified against current files: 04 UNIT-04 is `[LOCKED]` at ONE `unit_kind_hint` + `money_mode_hint` per numeric item, no amendment marker; 12 FACT-23/§10.3 (owner-approved 2026-07-03) pins per-slot pairs; 95 has no row; 14 §6 lists the debt but a TODO list is not a resolution.
2. **The issue, exactly:** the producer item contract (12 FACT-17b) requires `level_unit_kind_hint`/`level_money_mode_hint` + `change_unit_kind_hint`/`change_money_mode_hint` + per-slot `level_unit_raw`/`change_unit_raw`, because one pair cannot describe "$5B revenue, up 12%" (a money level + a ratio change). 04's LOCKED text still prescribes the single pair. Under the authority chain (core 01–09 outrank 12), a cold-start builder reading 04 alone is formally REQUIRED to build the dead contract — the exact "stale locked text re-enters prompts" footgun class (10 §12 #1).
3. **Recommendation (pure back-port, no design change):**
   - (a) Amend 04 UNIT-04's Rule: each numeric SLOT (level, change) carries its OWN hint pair + verbatim per-slot `unit_raw`; a bare single pair stays accepted as the LEVEL slot's pair (backward compatibility, per FACT-23). Marker: "(amended per owner 2026-07-03 — 12 §10.3/FACT-23; Replaces: 95 #26)".
   - (b) Add 95 row **#26** (drafted for the owner to paste — 95 is the owner's ledger): Was "one hint pair per numeric item (UNIT-04)" → Now "per-slot pairs; bare pair = level-slot compat" · owner 2026-07-03 · 12 §10.3 · amends UNIT-04.
   - (c) Touch nothing else: UNIT-05 (resolve level/change separately) already implies per-slot; UNIT-02's API sketch is explicitly non-locked.
   - Rejected alternative: leave 04 stale and rely on 14 §6's cleanup list — that leaves a formally-winning dead rule inside a LOCKED core doc.
4. **Confidence: 10/10.** The decision is already owner-locked; this only completes its paper trail. Two text edits + one ledger row; no interference possible.

#### RES · D-2 — finish the 95 #24 back-port: both expectation baselines FORBID on metric [C2 = C11]

1. **Real?** YES — verified: 09 §3's comparison row says "metric lane FORBIDs `consensus`" (silent on `previous_guidance`); 09 §8 says "metric-consensus FORBID"; 07's §D banner likewise — all with no amendment marker — while 09 §4's matrix + 07 DU-15 carry the post-OBJ-2 rule, and 95 #24's "amends" cell names only 09 §4 · 07 DU-15.
2. **The issue, exactly:** OBJ-2 (owner 2026-07-03) made the metric lane's `comparison_baseline` TEMPORAL-ONLY ({prior_year, sequential_period, null}); BOTH `consensus` AND `previous_guidance` are forbidden — an expectation comparison lives ONLY on the `_surprise` fact. Three prose spots still state the older consensus-only rule, so within one doc (09), §3 contradicts §4. A builder implementing from §3's field table writes `previous_guidance` onto metric facts — the exact double-store OBJ-2 eliminated, on permanent records.
3. **Recommendation (pure wording sync):** (a) 09 §3 comparison row → "metric lane FORBIDs BOTH expectation baselines (`consensus` AND `previous_guidance`) — an expectation comparison routes to the `_surprise` fact; the metric baseline is temporal-only (ISS-16/OBJ-2, owner 2026-07-03 — 95 #24)". (b) 09 §8's "(metric-consensus FORBID · …)" → "(metric-expectation-baseline FORBID, 95 #24 · …)". (c) 07 §D banner: the same one-phrase change. (d) 95 #24's "New source" cell → "amends 09 §3/§4/§8 · 07 §D/DU-15".
4. **Confidence: 10/10.** Completes an owner-decided amendment; the governing matrix already carries the correct rule — this only deletes contradictory prose.

#### RES · D-3 — scrub the rejected alias layer's residue; add the missing 95 row

1. **Real?** YES — verified in current files: FS-19 still grants code a merge "via the exact dedupe (FS-18) **or a confident alias**"; FS-02 and 09 §3 still describe "per-company alias files" as the read-time drift view. The owner REJECTED the alias layer outright (census §14.4, 2026-07-03 — human-in-the-loop); the ONLY approved drift-recovery is member-anchored read-time grouping (T12.9). 13R §16 independently flagged the missing 95 row.
2. **The issue, exactly:** "alias files" as a mechanism exists NOWHERE in the live design (no owner, no format, no confidence bar — that was ISS-6, resolved by REPLACING the mechanism, not specifying it). Text that still names it (a) invites a builder to create the rejected layer, and (b) FS-19's "confident alias" grants code a merge power the owner explicitly removed. Not identity-breaking today (every spot says read-time/never-in-id) — but it prescribes dead machinery in LOCKED rules.
3. **Recommendation:** (a) FS-19: delete "or a confident alias" → "code merges only via the exact dedupe (FS-18) — never a fuzzy near-match snap; a no-match = a new value = its own row (over-split; recoverable at read time ONLY via member-anchored grouping, T12.9)". (b) FS-02 + 09 §3: replace the "per-company alias files … read-time views" phrasing with "drift recovery = member-anchored read-time grouping ONLY (T12.9): labels group when ALL their linked facts agree on one exact (axis_qname, member_qname); prose-only drift stays split (safe)" — keeping the unchanged core (never inside the id; ids immutable). (c) Add 95 row **#27** (owner paste): Was "per-company alias files as the over-split recovery" → Now "member-anchored read-time grouping (T12.9); the alias layer REJECTED (human-in-the-loop)" · owner 2026-07-03 · census §14.4.
4. **Confidence: 9.5/10.** The replacing decision is owner-made and live in 11/12; only wording judgment remains here. The 0.5 reserve: FS-18's exact-normalized-label code-dedupe is UNCHANGED and must not be confused with the deleted alias merge — the recommended wording states that explicitly.

#### RES · D-4 — reconcile 12's "build-ready" banner with 14's P0 recipes [C12]

1. **Real?** YES — both texts verified. This is a status-claim collision, not a design conflict: "all owner DECISIONS closed" (true — 12 §16) vs "a safe coding handoff needs every identity recipe pinned" (true — 14 §0/§3).
2. **The issue, exactly:** 12 §17 step 1 builds `driver_ids.py`, which needs OD-8 (quote_hash recipe) and OD-9 (measurement tokenization) pinned; step 10 (driver_read) needs OD-10 (unit-family map); validator rule 16 / the ISS-16 comparator needs OD-13 (lower-is-better). A coding agent trusting 12's banner alone starts step 1 and INVENTS identity recipes — precisely the two-builders-fork-the-graph scenario 14 §3 exists to prevent.
3. **Recommendation:** one scope sentence added to 12's STATUS banner: "Build-ready = all Track B design decisions are closed. Before §17 step 1 runs, the identity recipes in 14 §3 / 66 §0.R (quote_hash recipe + rerun idempotency · measurement tokenization · unit-family map · loss-sign · lower-is-better · sequential-% · chronological-write · concurrency) must be pinned — recipe-pinning work, not reopened design." Optionally tag the blocked steps (1, 4, 5, 10). Nothing else changes.
4. **Confidence: 9.5/10.** Keeps both docs true; prevents the exact failure 14 warns about; the recipes themselves are resolved as OD-8…OD-13 below.

#### RES · D-5 — back-port the non-GAAP inheritance carve-out into 08 XC-12 [ISS-25]

1. **Real?** YES — verified: 08 XC-12 handles the latent-base case but says nothing about measurement; the carve-out ("any non-GAAP measurement token ⇒ NO inheritance") exists only in 09 §3's xbrl_qname row and 12 FACT-33.
2. **The issue, exactly:** a builder implementing concept-inheritance from 08 alone (the concept-linking section's natural home) will inherit the base metric's GAAP concept onto an ADJUSTED guidance/surprise fact — semantically wrong (an adjusted forecast is not a reading of the GAAP line), and exactly the class of wrong-link XC-01 calls the cardinal failure.
3. **Recommendation:** add ONE sentence to XC-12: "Inheritance carve-out: a guidance/surprise fact carrying ANY measurement token outside the G2 GAAP-compatible set (XC-05: empty/{gaap}/{basic}/{diluted}/{reported}/{as_reported}) inherits NOTHING — the same conservative abstain G2 applies at pick time (09 §3 · 12 FACT-33)." No rule change — the rule already exists; 08 becomes self-complete.
4. **Confidence: 10/10.** Pure completeness back-port of a locked rule into its owning section.

#### RES · D-6 — align FS-24's read key to the locked series key [ISS-22]

1. **Real?** YES — verified: FS-24 says "group by driver + slice + period, never by driver alone"; the locked series key (census T12.1 · 09 §7 · PER-14) is company · driver · fact_type · slice · period (+period_scope) · measurement · unit-per-§6.1 · time_type, plus BASE_METRIC family for cross-flavor reads.
2. **The issue, exactly (sharpened — the original ISS-22 wording overstated one consequence):** flavors do NOT blend under literal FS-24 (guidance/surprise are different DRIVERS), but three real blends happen: (a) **companies** — `revenue` + omitted slice + gp_2025 groups EVERY company's revenue into one line (worst case); (b) **measurements** — adjusted and GAAP readings of one driver merge; (c) **units** — a percent-growth fact joins a $-level fact. Each is a silent wrong-series read, the exact failure PER-14 exists to stop.
3. **Recommendation:** rewrite FS-24's Rule line to name the full locked key (company · driver · fact_type · slice · period · measurement · unit · time_type; + family for cross-flavor) and keep "never by driver alone" as the mnemonic; cite census T12.1 as the authoritative statement. One rule-block edit; no design change (03 was simply written before the key was finalized elsewhere).
4. **Confidence: 10/10.** The full key is locked in three other places; this removes the one under-stated copy.

#### RES · D-7 — FS-03's restatement-merge is read-time, not write-time [ISS-12]

1. **Real?** YES — verified: FS-03 says "Restatements (same value) merge" inside the identity section; its own example (press release + MD&A) spans two EVENTS → two ids that cannot write-merge (DU-19); the actual mechanism is glue rule 9's read-time collapse (09 §6.9).
2. **The issue, exactly:** a builder implementing FS-03 literally would try to converge two different-event facts into one node at write time — breaking the id recipe (invariant 3) to satisfy a sentence that was always about the READ view.
3. **Recommendation:** one clarifying clause in FS-03: "Restatements (same value) merge — WITHIN one event via fusion (09 §6.2, one node); ACROSS events via the read-time collapse (09 §6.9) — different events always keep different ids; nothing write-merges across events."
4. **Confidence: 9.5/10.** Pure disambiguation; both referenced mechanisms are locked.

#### RES · D-8 — scope the "LLM never merges" absolute [ISS-10]

1. **Real?** YES — verified: FS-04/PIPE-04 state it absolutely, while at the NAME layer the LLM genuinely decides fusions (dedup SAME_AS proposals; D5 SAME unions) — kept safe by different machinery (Refute + D1 approval-tracing + reversible links + code-only application).
2. **The issue, exactly:** the flattened absolute misleads in BOTH directions: a literal reader thinks SAME_AS proposals violate the law (they don't), or — worse — someone "fixes" the prose by weakening the actual guarantee.
3. **Recommendation:** one clarifying sentence at FS-04 (PIPE-04 points here): "Precisely: at the name layer the LLM may PROPOSE fusions (dedup SAME_AS · D5 SAME); every proposal must survive Refute, is applied only by code from `approved.json` (D1), and lands as a REVERSIBLE link — both nodes survive. What the LLM can never do: directly merge/destroy two existing identities, re-key a fact, or bypass the approval trace. 'Never merges' is a write-authority guarantee, not a decision-abstinence claim."
4. **Confidence: 9.5/10.** Describes exactly what the code already enforces; no rule changes.

#### RES · D-9 — restore 90's "every open thread" promise [ISS-1]

1. **Real?** YES — verified: 90 §A lacks the four owner-opens that live only in 10 §13 (G1 reuse-display rules · K2 fold-repair gate · target N 796-vs-786 · lifecycle/dormancy/IPO absorption); 14 §5 now unions them, but 90 still claims completeness it doesn't have.
2. **The issue, exactly:** two "complete" open-item indexes disagree; a bot consulting only 90 §A believes fewer owner decisions are open than exist.
3. **Recommendation:** add the four rows to 90 §A, each one line, "home: 10 §13"; plus one header sentence: "Track-doc opens are indexed here but owned by their manuals; the full union view = 14 §5." (Chosen over scoping-down 90's claim — the one-place promise is worth keeping at the cost of four lines.)
4. **Confidence: 9.5/10.** Mechanical index completion; no decisions touched.

#### RES · D-10 — state the news-exclusion consequence in 10's normative body [ISS-31]

1. **Real?** YES — verified: PIPE-10's fetch row says "ALL non-news company sources"; the WHY and the consequence live only in §14's adjudication record.
2. **The issue, exactly:** the mission says the news bot reuses the shared catalog (01 §8), yet news can contribute NO names at build time, and the only door (live governed G1/G2) is itself blocked on the open G1 display rules — a cold-start builder never learns this from the normative sections.
3. **Recommendation:** one sentence at PIPE-09 or the PIPE-10 fetch row: "News is deliberately excluded from the leaf build (adjudicated §14); consequence: news-coined drivers enter ONLY via live governed G1/G2 admission (PIPE-22 / 12 §10.6, part 2) — until that wires, a news fact on an unknown driver parks (`parked_facts`, lawful interim per 12 §10.6)."
4. **Confidence: 9/10.** States an existing decision + its already-designed consequence; nothing new.

#### RES · D-11 — add "orphan" + the protected-import step [P3]

1. **Real?** YES — verified: 13 §8 requires "hard-fail if a sync would orphan, rename, delete, or re-type" AND "import existing fact-bearing Driver names as protected inputs"; 10 PIPE-03 has the hard-fail on rename/delete/re-type only, and no 10 §9 step does the import.
2. **The issue, exactly:** (a) "orphan" (a sync that leaves a fact-bearing Driver without catalog backing) is a distinct failure the verb list must name; (b) the import-protected-names step has no home — but note Track A currently makes NO graph writes at all (PIPE-05), so the step belongs to whoever owns catalog→graph sync.
3. **Recommendation:** (a) add "orphan" to PIPE-03's verb list now (one word). (b) Fold the import-protected-names requirement into OD-16's resolution (the graph-sync tool's spec — see RES · OD-16), where it is enforceable, rather than into 10 §9 where no graph-facing step exists yet.
4. **Confidence: 9/10.** (a) is trivial; (b) is the only correct home once OD-16 assigns one.

#### RES · D-12 — the glossary [14 §6]

1. **Real?** YES — the overloads are verified and genuinely dangerous for cold-start builders: **G1/G2** = catalog admission gates (10 PIPE-13) AND concept-linker guards (08 XC-05) — two unrelated systems, both senses inside doc 12; **menu** = slice-value menu (FS-14) · concept menu (XC-09) · reader chunk-menus (`menus/`, PIPE-10); **slice** = fact_scope part AND `slice_seed.py` batch-splitting; **created** = system write-time on facts (09 §3) but public-filing-time in PIT menu queries (XC-09's `r.created`); **live** = produced_mode live-vs-backfill AND live-vs-backtest read mode; plus "parked", "fail-closed", "archive".
2. **Recommendation:** add a ~12-line "Glossary — overloaded terms" section to `00_Coverage.md` (the map doc every new bot reads first), one line per term, each sense with its doc pointer. No term is renamed — renaming locked vocabulary would cost more than the ambiguity.
3. **Confidence: 9/10.** Pure documentation; the only design choice (don't rename) follows minimal-machinery.

#### RES · D-13 — the one-line-nit cluster (each verified; each fix exact)

| Nit | Verified? | Fix | Conf |
|---|---|---|---|
| 09 §5 cites "(§6.6)" for citation IDs | YES — §6.6 is policy-vs-reading; citation IDs are glue rule 5 (§6.5) | "(§6.6)" → "(§6.5, glue rule 5)" | 10 |
| 95 rows #6/#7/#8/#12/#14/#15 lack live back-pointers | YES | add `Replaces: 95 #N` markers: #6/#7/#8 → 07 DU-22/21 · #12 → FS-08/FS-21 · #14 → DU-11 · #15 → PIPE-30/31 | 9 |
| 95 #12 stale "(re-confirm at slices)" | YES — 03 locks it (FS-21) | delete the parenthetical; cite FS-21 | 10 |
| 00 dates 10 "committed 2026-07-02" vs 10's STATUS 07-03 | YES | 00 cell → "2026-07-02, Round-6 fixes 2026-07-03" | 10 |
| NAME-10's part-list says "brand", omits entity_ownership | YES — "brand" is a source word, not a kind (FS-08); entity_ownership is a real 6th kind | add one NAME-10 note: "stored slice KINDS = FS-06's six (a brand's kind comes from its axis; store_type→channel; + entity_ownership)" | 9 |
| FS-08 "code validates it's one of the 6" | YES — FS-05/FS-16 say 6 + unknown | → "one of the 6 + `unknown`" | 10 |
| entity_ownership caution absent from 03 | YES — lives only in 99 §5.7 | add to FS-06's entity_ownership bullet: "least-clean bucket: JV/equity-method strongest; others conservative/often provisional (99 §5.7)" | 9.5 |
| FS-14's menu-union reversal has no 95 row | YES — recorded only in FS-14's inline source note | add 95 row #28 (owner paste): latest-prior menu → union-of-all-prior-filings ∪ catalog history | 8.5 |
| 00's census row "Blocks: T1…T15" | YES — Tn.m labels stop at T12.9 | → "T1…T12 (+ §13–§16 unlabeled)" | 9.5 |
| DriverPlan.html's authority-tiebreak sentence not in any md doc | YES — but it fairly compresses the de-facto back-port convention | fix at the next html regen to cite 14 §6's debt list; html is self-labeled non-authority — no md change needed | 8.5 |

#### RES · OD-1 — terminal suffix + latent base safety [ISS-19 · ISS-20 · C10] — OWNER-APPROVED 2026-07-05

1. **Real?** YES — verified: `fda_guidance` / `regulatory_guidance` can be a document or rule, not a forecast, yet PIPE-24 currently suffix-stamps it as `guidance` and PIPE-25 strips it into a fake metric base (`fda`, `regulatory`). `dividend_guidance` / `buyback_guidance` can forecast an action, not a standing metric, yet an absent base is minted as a latent metric. F2 catches only an existing non-metric target; F3 passes because the suffix caused the stamp; finalization is quote-blind and cannot re-judge meaning later.
2. **The issue, exactly:** terminal `_guidance` / `_surprise` is allowed too late and too mechanically. If a bad terminal-suffix Driver enters the catalog, it can create a wrong `fact_type`, wrong `BASE_METRIC`, and wrong latent base. That is a high-severity over-merge risk because later facts inherit the wrong family.
3. **Owner decision (minimal, no maintained vocabulary):**
   - **Admission-time suffix gate:** before any Driver ending in terminal `_guidance` or `_surprise` is admitted, in both batch Track A and live governed-create, strip exactly one terminal suffix. Example: `bookings_guidance` → residue `bookings`; `revenue_guidance_surprise` is stacked and invalid. Mid-name words do not count; `fda_guidance_issuance` is not terminal `_guidance`.
   - **The one semantic question:** ask from the source quote: "Is the residue a standing metric or condition whose level, state, or severity can be re-read over time, and is this source forecasting/guiding/targeting it (`_guidance`) or comparing it to expectation (`_surprise`)?" This admits real families like `bookings_guidance`; it rejects document/action names like `fda_guidance`, `regulatory_guidance`, `buyback_guidance`, unless the residue is truly the metric being guided or surprised.
   - **Two independent checks:** run the same question twice independently. Both checks must return YES. Any NO, UNCLEAR, missing evidence, or disagreement means the terminal-suffix name is not admitted.
   - **If not admitted:** rewrite only when the source supports a specific, source-grounded, non-terminal name that obeys NAME-04/NAME-16, then send that new name through normal dedup/Refute. Example: if the quote is about an FDA guidance document, `fda_guidance` cannot stay a metric-family name; a specific non-family name such as `fda_guidance_issuance` is allowed only if the quote supports it. Never rewrite to a broad bucket like `regulatory_guidance_update`. If no safe rewrite exists, park by the existing G2/D5 mechanics. Finalization does not invent a new park/skip path.
   - **Admission memo:** every admitted terminal-suffix Driver must write `terminal_admissions.json` with `driver_name`, `suffix`, `stripped_base`, `evidence_ref`, `check_1`, and `check_2`. The memo freezes the verdict; refreshes reuse it and never re-roll the semantic checks. Finalization validates the memo; it does not re-run the meaning test.
   - **Latent base rule:** create a latent base only after the terminal-suffix family is admitted and no real base Driver exists. The latent anchor must be a valid standalone Driver name under NAME-16/13, collide with no record / variant / `skips[]` / parked name, and must not itself be suffixed or stacked. Latents are hidden from normal reuse menus.
   - **Latent graduation:** if a later evidence-backed metric Driver with the exact same `norm()` name is admitted, the latent graduates automatically. No fuzzy matching and no extra semantic gate. Example: `bookings_guidance` may create latent `bookings`; later admitted metric `bookings` graduates it. `net_sales` does not graduate latent `revenue`; that needs the normal SAME_AS path if appropriate.
   - **Finalization hard-fails:** missing memo; memo base not equal to the stripped residue; either memo check is not YES; a terminal-suffix Driver has anything other than exactly one `BASE_METRIC`; the `BASE_METRIC` target is neither an existing metric nor a valid latent metric anchor; the latent anchor is terminal-suffixed/stacked; or the anchor collides with records, variants, `skips[]`, or parked names. Existing F2/F3/F4 stay in force.
   - **Explicit non-rules:** no allow-list, no maintained deny-list, no human review queue, no generic `_update` bucket, no fuzzy latent matching, no broad deterministic rewrite recipe, and no new finalization park path.
   - **Ownership:** 10 owns the Track A rule text and validator changes (PIPE-24/25/26/36 plus finalization checks). 12/14/66/90 only point to that owner text after back-port.
4. **Confidence: 9/10.** This is the smallest no-human design that blocks the known permanent over-merge cases: it gates before admission, requires two independent source-grounded YES answers, records proof for deterministic finalization, and fails closed. Residual: two independent checks could still agree wrongly on a truly ambiguous quote, but that is the irreducible semantic risk in a no-human system.

#### RES · OD-2 **v3 — OWNER-APPROVED 2026-07-05** — bare names: "metric must prove itself"; action_event is the safe default [ISS-17]

> **Provenance:** v1 (2× stability vote → owner queue) WITHDRAWN — violated no-human. v2 (grounded double-check + batch file-don't-block, below) survived a 3-critic adversarial panel (wf_d5f577c3-357) but its batch exit retained the PIPE-36 owner-adjudication touchpoint — REJECTED by the owner as a kept human queue. **v3 = the owner's asymmetric design + five review pins, accepted in lean form.** The owner's core insight, which supersedes v2's symmetric treatment: the two mistake directions are NOT equal — a false METRIC stamp is the AMPLIFYING error (fake `_guidance`/`_surprise` families attach to a bogus base → permanent false merges), while a false ACTION_EVENT stamp fail-closes (blocks family creation, parks facts, corrupts nothing). Spend the entire protection budget on the metric side.

**The owner-approved rule — for every bare, non-suffixed, self-canonical Driver:**
1. **Deterministic rules first** — OD-1's suffix gate and the locked DU-06 bare-root defaults stamp deterministically and are UN-VETOABLE. OD-2 silently deletes no locked rule.
2. Run the locked DU-05/06 classifier (**C1**), prompt VERBATIM (DU-07 untouched).
3. **C1 = action_event → stamp action_event.** No second check — this is the safe direction.
   - 3b. **C1 = guidance/surprise on a bare name → a NAMING defect, never a stamp:** batch = the existing F3 both-ways hard-fail → D4 rename (the `capex_outlook` case, already locked); live = admission REJECTS → re-coin with the suffix through OD-1's gate, else the fact parks.
4. **C1 = metric → the metric-proof challenge (C2), on the FULL evidence set at batch** (runs once per driver — cost trivial): *"Using only the evidence: is this name itself a standing level, value, condition, or severity that can be read again over time? Answer NO if the name is mainly a one-time action, decision, event, or plan — even if a related amount/rate/balance could be measured under a more specific metric name. Quote the exact evidence phrase."*
5. **C2 = YES + a verbatim quoted phrase → stamp metric.** "Clearly confirms" means exactly that; anything else = not confirmed.
6. **Otherwise → stamp action_event**, set `metric_proof_defaulted=true` in the memo row, and COUNT it in the `--final` report warnings — report-grade (the F5-alarm style): visible, never build-blocking, never a queue.
7. **Non-rules:** no owner queue · no third model/tie-breaker · no maintained allow/deny lists · no re-typing after facts (PIPE-24/DU-07 stand in full).
8. **The F2 family gate (the capstone):** a `_guidance`/`_surprise` family may attach ONLY to a base that is metric AND PROVEN — (a) deterministically metric (suffix/DU-06), OR (b) OD-2 metric-proven (memo row), OR (c) an OD-1-admitted LATENT anchor (`terminal_admissions.json` IS its proof — OD-1's two checks asked exactly the standing-metric question; pin 2, closing the latent-breakage hole). `buyback_guidance → buyback` can never pass on an unproven metric stamp. Back-port merges this with OD-1's F2 wording into ONE F2 spec in 10.

**Supporting pins (all lean — no new queue, side-list, model, or human):**
- **Memo (no new artifact):** extend the existing h32-bound `fact_type_decisions.json` rows with {c1_verdict, c1_evidence_ref, c2_required, c2_result, c2_extract, final_fact_type, metric_proof_defaulted, decision_reason}. Live memo = Driver-node properties (OD-7's born-complete pattern; the sealed batch file is never touched at live time).
- **Batch ≠ live (pin 3):** batch runs the rule above on FULL evidence; live evidence is one thin quote, so live-UNCLEAR **parks the fact and retries on each new arrival BEFORE any default** — the full live rule is homed in OD-7 (cross-note there on back-port).
- **First-fact lane-exercise guard (reserved here, homed in OD-7):** a Driver must not become permanently fact-bearing from a first fact whose `driver_state = unknown` — `unknown` proves nothing about the chosen lane; park it and retry when a readable-state fact arrives.
- **Amendment declaration (pin 4):** this asymmetric procedure AMENDS the stamp mechanics around PIPE-24/DU-06/DU-07 — the decider prompt stays verbatim, but the procedure around it changes and C2 can override a C1-metric verdict. Owner-approved 2026-07-05; back-port = a PIPE-24 amendment + DU-06/07 annotations + a 95-row candidate (#29).

**Honest cost + residual floor (owner-acknowledged wording):** a wrong action_event is NOT a mere over-split — it can BLOCK a real metric's series and family until a future repair/rebuild (the bootstrap re-assemble path); still strictly better than a false metric, which creates bad families and bad merges. Residuals: (i) a C1-DIRECT wrong action_event (step 3 — no challenge runs) is NOT counted by the pin-1 warning; its symptom is parked-fact accumulation on that driver, visible operationally — the accepted cost of the asymmetry; (ii) the irreducible semantic floor — a model consistently wrong on full evidence is undetectable at stamp time in any no-human system, now CAPPED by the F2 gate (a wrong metric can't grow families) and SURFACED by the defaulted-stamp count. **Confidence: 9/10.**

**Worked examples (owner's):** `bookings` → metric if the challenge quotes a standing-measure phrase · `buyback` → action_event (amounts existing doesn't make it a metric; the metric form is a more specific name like `buyback_authorization_remaining`) · `dividend` → action_event (DU-06 deterministic; metric form = `dividend_per_share`) · `restructuring` → action_event unless evidence proves a standing cost/charge metric.

---

*Superseded v2 record (kept for the trail):*

#### RES · OD-2 ~~v2~~ — fact_type for bare (non-suffixed) names: grounded double-check · file-don't-block · first-fact lane-exercise [ISS-17] — adversarially iterated 2026-07-05, superseded by v3 above

> **Provenance:** v1 (a 2× stability vote ending in an owner queue) was WITHDRAWN — it violated the no-human requirement outright. Its successor candidate was then attacked by a 3-critic adversarial panel (run wf_d5f577c3-357; locked-rule-conflicts · no-human-violations · minimalism lenses completed; 4 further agents lost to a session limit, their lenses — failure-modes, cold-start, two rival designs — re-performed by the lead). The panel CONFIRMED four fatal flaws, each grounded in locked text, and v2 is rebuilt around them: (1) restamping even a fact-FREE driver is illegal — PIPE-24 locks re-stamping to the re-assemble path and DU-07's "once, permanently" binds ALL drivers (13 §8 is the narrower fact-bearing rule, not the only lock); (2) an `unresolved_fact_type` side-list is a forbidden NEW finalize park path (PIPE-26 additive-only · PIPE-28's closed side-list set · OD-1's own non-rule) and any unstamped record bricks F1/PIPE-36; (3) the lane-rejection "tripwire" FAILS OPEN — `unknown` is lane-legal in every lane, so a mistyped driver usually ACCEPTS its first fact and freezes wrong (systematic, not rare); (4) the live memo cannot live in the sealed batch artifact, and a second check must never veto a deterministic verdict (coverage regression).

1. **Real?** YES — unchanged from v1's verification: non-suffixed SELF-CANONICAL records get their permanent fact_type from ONE classifier verdict (PIPE-24); F3 is silent (no suffix), F5 covers variant records only, the fitness gate scores name+direction. SHARPENED by the panel: the freeze mechanics make it worse — one lane-legal `unknown`-state fact makes any wrong stamp permanent (13 §8), so the design must protect the stamp BEFORE facts exist; afterwards is too late by locked rule.
2. **The issue, exactly:** a permanent, everything-routing field (state lanes · period rules · concept-link routing · family eligibility) rides a single LLM verdict, and the freeze door closes on the first accepted fact.
3. **The design (v2):**
   - **(a) Deterministic supremacy.** A terminal suffix (OD-1's approved gate) or a DU-06 bare-root default stamps DETERMINISTICALLY; no check may veto these. The double-check below runs only for the remaining names (non-suffixed, no bare-root default).
   - **(b) The grounded double-check.** C1 = the locked DU-05/06 classifier, prompt VERBATIM (DU-07 untouched — C2 is a separate check, not an added clause). C2 = an EXTRACTIVE evidence probe, a genuinely different task shape: "From the evidence quotes, extract VERBATIM the phrase showing (i) a standing re-readable level/condition, (ii) an outlook/forecast statement, or (iii) a discrete one-off action — and tag which." Agreement predicate (pinned): C1=metric ⇔ C2 quoted a tag-(i) phrase · C1=action_event ⇔ tag-(iii) · C1=guidance/surprise → lane (d) below regardless of C2 · C2 finds no extract → counts as disagreement. Honest scope: C2 forces evidence-grounding against C1 pattern-matching the NAME; correlation is reduced, not zero (same model, same evidence).
   - **(c) Agree → stamp + memo.** Batch: extra columns on the record's EXISTING `fact_type_decisions.json` row ({verdict_c1, c2_tag, c2_extract, escalated}) — the file is already expect+h32-bound and already what finalize validates; NO new artifact. Live: the memo rides as Driver-node properties, written by the admission worker (OD-7's born-complete pattern — the sealed batch file is never touched at live time).
   - **(d) Non-suffixed guidance/surprise verdicts** take the EXISTING locked lane, restated accurately (panel correction): at batch this is the F3 both-ways hard-fail with the D4 rename remediation (the `capex_outlook` case) — detection deterministic, the rename is a BUILD-time remediation, already locked; at live, admission REJECTS the name (a guidance family must carry the suffix, NAME-17) → re-coin through OD-1's gate, else the fact parks. Nothing new here; v2 just stops mislabeling it "automatic".
   - **(e) Disagree → escalate once on the FULL evidence set** (both checks re-run; no new prompt). **Batch, still disagreeing → STAMP C1's verdict AND FILE the row in the existing `fact_type_disagreements.json`** — file-don't-block: F1 stays 100% green, stamp-once intact, finalization stays additive, and the EXISTING PIPE-36 bar ("empty or every row owner-adjudicated") surfaces it at build acceptance. That is the already-locked bootstrap gate — per 14 §7's own scoping ("one-time human/owner review belongs only to design/bootstrap/evaluation, not runtime"), NOT a steady-state human loop; the pipeline never stops flowing. **Live, still disagreeing → do NOT admit** (fail-closed): the fact parks (12 §10.6's lawful interim, verbatim); every NEW fact arrival auto-retries the vote with the grown evidence — the drain trigger IS the arrival, no scheduler, no human. **Bounded terminal (panel demand):** after 3 distinct-event retries still disagreeing, stamp C1's full-evidence verdict + write the disagreement memo on the node — bounded, visible forever, facts drain, no human.
   - **(f) The first-fact lane-exercise guard** (replaces the illegal tripwire; closes the unknown-swallow freeze): a Driver becomes fact-bearing — and therefore 13 §8-frozen — only through a fact whose `driver_state ≠ unknown`. An unknown-state fact targeting a zero-fact Driver PARKS and auto-replays after the first readable-state fact writes. One-line write-time validator; rationale: the freeze may only engage after the chosen lane has been EXERCISED once (an unknown-only "first fact" carries no lane evidence and near-zero signal — parking it is cheap and visible).
   - **(g) Refresh/idempotency:** stamped types + memos are FROZEN (the existing 10 §13 refresh rule); only never-stamped/live-pending names ever re-vote. No oscillation is possible: retries exist only BEFORE a stamp; stamps never change outside the locked re-assemble path.
   - **(h) Dependency, stated:** the live path activates with governed-create, which is blocked on the open G1 reuse-display owner decision; until wired, parking is the lawful interim (12 §10.6's own words). The batch path depends on nothing new.
   - **Non-rules:** no new side-lists or artifact kinds · no finalize eviction · no restamp outside re-assemble · no third model (C2's model = a PIPE-23 MODELS slot; MAY differ from C1's under the open model policy) · no allow/deny lists beyond the already-locked DU-06 defaults · no owner queue beyond the EXISTING locked PIPE-36 acceptance.
   - **Rejected (with the panel's evidence):** the fact-free restamp + auto re-vote drain (illegal, PIPE-24/DU-07) · the unresolved_fact_type side-list (forbidden new park path; F1/PIPE-36 breach) · 2× same-prompt stability voting alone (blind to systematic error by construction — the panel's minimalism critic upheld the need for a differently-shaped second check) · C2 as a veto over deterministic verdicts (coverage regression below the locked baseline) · relying on DU-12 lane-rejection as the safety net (fails open via `unknown`).
4. **Confidence: 8.5/10.** Every panel-confirmed rule conflict is gone: no restamps, no new artifacts, F1/PIPE-36/additive-finalize intact, memo homes pinned for both paths, deterministic verdicts un-vetoable, the unknown-freeze door closed by (f), every terminal state drains or is visible. The honest remainder: (i) the irreducible semantic floor — C1-on-full-evidence can be consistently wrong on a genuinely dual-framed name; v2 makes that case VISIBLE (filed row / node memo) rather than silent, and DU-06's dual-framing rule means the other framing later becomes its own driver (complement, not corruption); (ii) batch acceptance retains the already-locked owner adjudication of disagreement rows — bootstrap-scope under 14 §7, but a purist reading of "no human anywhere" should know it exists; (iii) C2's decorrelation is partial by nature.

#### RES · OD-3 — may the blind reader make the NAME-11 step-2 call? [ISS-13]

1. **Real?** YES — the tension is verified. But the analysis shows only one mechanically possible answer: NAME-16 #11 BANS the bare fragment (`demand`, `ban`), so a reader that strips the brand at step 2 has NOTHING legal to coin — the name-vs-slice exception MUST be decided at coin time, by the reader.
2. **The issue, exactly:** 10 never states that the reader uses the model's general world knowledge for "this brand/product itself moves OTHER companies" — a cold-start builder might try to defer the call to reconcile/fold (impossible: the fragment can't be coined) or to suppress world knowledge (impossible: the judgment needs it).
3. **Recommendation:** document the de-facto rule in PIPE-17 (no behavior change): "Step 2's 'moves OTHER companies' is judged with the model's general knowledge at coin time — the blind reader has no cross-company view by design. This is safe because every failure mode is recoverable: unsure → SLICE (the ladder's own default); an over-eager exception name is an over-split (cheap, SAME_AS-repairable); G2 re-tests admission from evidence; fold-level D5 + Refute re-judge recurrence with real cross-company evidence (PIPE-20 expects convergence). The reader must NEVER emit the bare fragment (NAME-16 #11)."
4. **Confidence: 9/10.** Documents the only workable reading; all four safety nets already exist.

#### RES · OD-4 — FS-22 over-generalizes "recurs ⇒ generic" [ISS-14]

1. **Real?** YES — verified: FS-22 says "A real specific part lives at ONE company", which mis-flags `geography:china` / `product:advertising` (recur AND genuinely correspond). The operative half of FS-22 (promotion needs the REAL signal, never recurrence) is correct and sufficient on its own.
2. **The issue, exactly:** the overstated sentence invites a builder to treat recurrence as NEGATIVE evidence and quarantine real geography/product values — over-quarantine is cheap but needless, and the sentence is simply false as stated.
3. **Recommendation:** re-scope FS-22's wording, no behavior change: drop "a real specific part lives at ONE company"; state: "a NAME recurring across companies = breadth (good); a VALUE recurring is NOT evidence of comparability — grab-bag values (International/Other/Corporate) recur precisely because they are generic, while even genuinely-corresponding recurrences (`geography:china`) still wait for the unbuilt FS-23 layer. Promotion to cross-company-eligible needs the REAL signal (persistent magnitude on a confirmed axis) — never recurrence alone, in either direction." Cross-company comparison stays gated by FS-23 regardless — so nothing opens up.
4. **Confidence: 9.5/10.** Wording-scoping of a locked rule; the guard (FS-23 + promotion bar) is untouched.

#### RES · OD-5 — the scanner / change-flag layer is designed nowhere [ISS-8 · 14 §3 #13]

1. **Real?** YES — verified: 01 §7 promises auto-flagging; 09 §4/§9's LOCKED decisions lean on scanner properties ("alarm-fatigue noise in the signal path", "the scanner's only sound comparator is the extractive value_text"); no doc defines it; 90 §D omits it.
2. **The issue, exactly:** locked decisions cite a component with no contract — a future designer could build a scanner that violates the assumptions those locks rest on (e.g. an LLM comparator at read time, or paraphrase-sensitive triggers).
3. **Recommendation — write the CONTRACT now (one short section), the component later (part 2):** the scanner is a READ-TIME, CODE-ONLY consumer: **inputs** = the collapsed current view per locked series key (T12.1) + PIT history; **trigger classes** = (i) state transitions (introduced/raised/lowered/withdrawn · increased/decreased flips · beat/missed), (ii) closed-shape numeric deltas ≥ a per-unit-family threshold (config, owner-tuned), (iii) the derived `narrowed` flag, (iv) qualitative change = normalized `value_text` EXACT inequality only (extractive comparator — the locked 09 §4 assumption); **output** = a flag event/notification, NEVER a stored fact and never a stored field (read-derived, re-runnable); **laws** = zero LLM in the scan path · realized returns never read · thresholds are config, not code. Home: add the missing 90 §D row ("scanner/change-flag design — part 2; contract pinned in 66 §0.R OD-5"); the component itself belongs to part 2 (it is a consumer of Track B reads and blocks nothing in Tracks A/B/C).
4. **Confidence: 8/10.** The contract encodes exactly the properties the locked decisions already assume (deterministic, extractive, read-time) — safe by construction; deliberately NOT designing triggers/thresholds now is the minimal-machinery call, and the honest reserve is that part 2 may still evolve the trigger list.

#### RES · OD-6 **v3 — OWNER-APPROVED 2026-07-05** — the quality budget defined: ZERO confirmed wrong merges over ≥3,000 pre-registered key slots [ISS-9 · 14 §3 #12]

> **Provenance:** v1 (wrong-merge rate ≤0.1% of graded decisions) had the right core — the budget bounds the PERMANENT class only — but the owner's review caught two holes and removed one declared softening: (1) v1's denominator was DILUTABLE (producer emissions grew n, so junk output could game the rule-of-three bound); (2) v1's small-sample fallback ("owner accepts a weaker demonstrated bound") reintroduced an owner-fudge; (3) v1 let unresolved grader flags pass GREEN with reporting. v3 = the owner's three pins + two lead completeness pins (declared below).

1. **Real?** YES — PIPE-37 pins the 0.634/0.535/72% baselines but "quality budget 0.1%" is defined nowhere ("0.1%" traces only to superseded/cost-lever docs); a one-shot graded-once gate cannot be scored on an undefined criterion, and an operator improvising a definition AFTER seeing results is retuning-to-pass — the exact thing PIPE-37 forbids.
2. **What is budgeted — wrong merges ONLY:** the producer REUSES an existing catalog Driver where the sha-locked answer key says the source cause is genuinely different (including "no existing driver matches — a new name was required"). Everything recoverable is report-only, bound in aggregate by the existing bars: over-splits (create-instead-of-reuse) · misses/skips · junk creates · wrong directions.
3. **The owner-approved definition:**
   - **Fixed denominator (ungameable):** `graded_slots = sha-locked key slots × producer_runs` — computable BEFORE any producer output exists; producer emissions NEVER grow it. Extra wrong reuses on non-slot emissions still count in the NUMERATOR (conservative by construction).
   - **The 0.1% claim = the rule of three:** zero confirmed wrong merges in ≥3,000 graded slots ⇒ true rate ≤ 3/3,000 = 0.1% at ~95% confidence. **A key smaller than 3,000 slots CANNOT go GREEN** — no weaker-bound fudge; the gate may report the weaker bound (3/n) but may not claim 0.1% or pass.
   - **Confirmation (two graders):** the primary grader flags a wrong merge → an independent second grader must also find "different cause," citing evidence → CONFIRMED → **RED**.
   - **Unresolved flags block GREEN (no fake pass):** grader disagreement → ONE fresh blind re-grade round (two new independent graders, blind to round 1's verdicts); still split → the gate is **INCONCLUSIVE** (not GREEN) — the disagreement itself is the finding: that case class is genuinely ambiguous under current rules, so remediation = clarify the rule/prompt for that class, then full re-gate on a FRESH key. Bounded, deterministic, no human queue.
   - **GREEN =** ≥3,000 pre-registered graded slots · zero confirmed wrong merges · zero unresolved flags · all existing PIPE-37 bars pass (≥0.634 name+direction vs the key · ≥72% inter-producer agreement).
   - **Re-gate rule:** RED/INCONCLUSIVE → fix prompts/rules only (never meaning-matching code — 10 §9 step 11) → the failed cases become regression fixtures (the burned key is honestly a tuning set from that point) → final GO only on a FRESH, unseen, sha-locked key. This is what makes "graded once, no retuning to pass" enforceable rather than aspirational.
   - **Harmonization:** this makes PIPE-37's budget the same principle as PIPE-32's experiment gate ("zero tolerance for merge-direction novelty") — one house rule, two contexts, no second unrelated number.
4. **Lead completeness pins (declared, not silently folded):** (i) the ×2 producer-runs multiplier is not two independent trials (same events, same catalog) — the ~95% confidence claim is approximate; accepted rather than doubling key cost; (ii) skipped slots remain in the denominator — legitimate only because the 0.634 floor forces substantial attempt coverage (a mass-skipping producer fails the baseline before it can dilute the budget); (iii) a "confirmed wrong merge" can itself be a KEY error — partially self-correcting (a wrong key usually splits the two graders → INCONCLUSIVE, not RED), and burned-key cases are reviewed as regression fixtures during remediation.
5. **Non-rules:** no human queue · no unbounded grader tie-breaking (exactly one blind re-grade round) · no new artifacts (fields on the existing gate report/manifest) · no weaker-bound GREEN · no post-hoc definition changes (the full definition is pre-registered with the key).
6. **Back-port:** amend 10 PIPE-37 with the definition + GREEN condition + re-gate rule · closes 14 §3 #12 · annotate ISS-9. **Confidence: 9.5/10** — every GREEN term is mechanical arithmetic on pre-registered quantities; the residual floor = key fallibility + approximate trial-independence, irreducible without doubling the key for negligible gain.

#### RES · OD-7 — live governed-create: fact_type stamping + the no-exit residual [P5 · ISS-18 residual · 14 §3 #10]

1. **Real?** YES — verified: 12 §10.6's governed-create path admits Drivers live, but the only fact_type stamping machinery is Track A's end-of-build finalize (which HARD-FAILS on already-stamped input, PIPE-24), while FACT-16 rule 2 rejects facts on fact_type-less Drivers → live admission is structurally blocked; and P5's verified residual: once a live-created Driver acquires facts, 13 §8 immutability leaves no exit for a mis-name/mis-type.
2. **The issue, exactly:** the owner-revised missing-driver rule (governed G1/G2 first, park only as fallback) cannot function when part 2 wires it — a live-admitted Driver has no path to the fact_type + family every write requires.
3. **Recommendation — "born complete" at live admission (prevention, mirroring Track A's ordering):** the live admission flow runs, in line, BEFORE the first fact write: (1) G2 admission (existing); (2) fact_type stamp — terminal suffix ⇒ deterministic, else the DU-05/06 classifier with the OD-2 stability vote (unstable → PARK the fact, no admission); (3) BASE_METRIC resolution per PIPE-25's exact lookup order against the LIVE graph, including the OD-1 DU-06-root check before minting a latent; (4) the F1–F4-equivalent checks as write-time validators. Only then does the DriverUpdate write (FACT-16 rule 2 stays untouched as the backstop). Track A interop: live-created Drivers live in the GRAPH, not in catalog.json — the next full Track A build imports them as PROTECTED inputs (13 §8 · the D-11/OD-16 import step) and may add links, never re-stamp (no collision with finalize's already-stamped hard-fail). **The residual exit** for a fact-bearing live Driver later proven wrong: additive-only — same-flavor mis-name → SAME_AS to the correct driver (existing, reversible); cross-flavor mis-type (rare — DU-12 lane hard-fails make a mistyped driver reject its own facts loudly and early) → owner-approved quarantine: one non-identity flag `retrieval_excluded=true` (never shown as a reuse candidate — the graph analogue of PIPE-35's side-list semantics) + create the correct driver; stored facts stay attached as historical evidence (ids never re-key).
4. **Confidence: 8/10.** The stamping path reuses Track A's exact components at admission time (no new judgment machinery); the one new element is the owner-gated quarantine flag — deliberately non-identity, mirroring an existing semantics. Reserve: the flag is new surface (small), and part 2 may adjust where the admission worker lives.

#### RES · OD-8 **FINAL — OWNER-APPROVED 2026-07-05** — quote_hash: signature-only hash · conflict-keyed membership · write-and-flag [tail-G1 #4/#9 · E2 · 14 §3 #1/#2]

> **Provenance:** three design iterations (lead v1 → owner hybrid → conflict-keyed final) + a 12-agent adversarial panel (wf_6aec09df-4c9, 11 completed) + independent owner review, all converging. The panel confirmed 6 findings against the earlier candidate: 2 were the same holes already fixed in-conversation (the FACT-14b weaker-rerun fork; the bare+hashed state contradiction), 2 were NEW and are folded below (the false-sibling prefix scan; the unchecked merge-into-bare that let FACT-14b's "correction" branch silently overwrite a different fact), 1 demanded the amendment declarations (met), 1 duplicated the first. The panel's rival designer independently converged on signature-only hashing — the owner's core call, validated three separate ways.

**THE RULE — fact id = event + driver + fact_scope; `quote_hash` is added only when the same event+driver+base-scope still holds MORE THAN ONE real fact after fusion.**

1. **Hash the VALUES, never the quote** (despite the field's name — quotes vary across reruns/producers; values must not). The collision signature = 10 slots, fixed order: `level_low, level_high, level_unit, change_value, change_unit, comparison_low, comparison_high, comparison_baseline, value_text, conditions`. EXCLUDED, each for cause: `quote` (span-varying — the amendment's whole point) · `driver_state` (a derived classification of the values, not a second fact) · `company_confirmed` (MF-11 LOCKS it "never in the fact key") · producer/source_type/date/created (never identity — T1.4/09 §3) · xbrl fields (enrichment, never identity — T1.6).
2. **Exact byte recipe:** compact canonical JSON array (fixed order, ascii-escaped, compact separators; **JSON `null` stays distinct from empty string**); text slots through THE one shared normalizer (OD-9's pin); numbers via the writer's ONE decimal canonicalizer (no exponent, no trailing zeros, "-0"→"0" — never a second implementation). `quote_hash = sha256(collision_signature_json).hexdigest()` — **full sha256, no truncation** (deletes the truncation pin AND the digest-collision guard as dead code; long ids only in the rare collision class).
3. **Step order (amends FACT-17's parenthetical):** fusion → period/slice/measurement → unit resolution → canonical values → collision matching → id write. Units and values must be canonical BEFORE hashing, or signatures are non-deterministic.
4. **Sibling probe (exact form — a raw prefix scan pulls FALSE siblings because scope slots are optional):** `id = bare_id` OR `id STARTS WITH bare_id + "|quote_hash="`. Never `STARTS WITH bare_id` alone.
5. **Matching vocabulary:** **exact** = all signature slots match, including nulls · **compatible** = no shared non-null slot disagrees · **conflict** = ≥1 shared non-null slot disagrees.
6. **Write rules (all against the PRE-batch graph state):**

| Situation | Action |
|---|---|
| no sibling, one post-fusion fact | write the bare id |
| no sibling, multiple post-fusion facts (pairwise-conflicting distinct signatures — same-signature items are restatements fusion already merged) | write ALL with quote_hash |
| one sibling, compatible item | merge/fill (FACT-14b; never erase non-null) |
| one sibling, CONFLICTING item | new hashed member + late-collision flag |
| multiple siblings, exact match | merge into it |
| multiple siblings, conflicts with ALL | new hashed member |
| multiple siblings, compatible but not exact | **PARK as ambiguous — never guess** (the owner's strict call); drains automatically on the next richer arrival (arrival-retry) |

7. **Batch rule:** decisions use the pre-batch state only — item order must never decide identity; two batch items competing to fill the same partial sibling → park the competitors (a richer rerun resolves via exact/conflict).
8. **FACT-14b scope amendment:** normal reruns may FILL missing fields but may NOT overwrite a conflicting SIGNATURE slot as a "correction" — a conflict mints a flagged hashed sibling instead; a true correction goes through explicit `--repair`. (Non-signature fields keep FACT-14b's correction branch unchanged.)
9. **Late collisions are legal history:** one old bare member + newer hashed members may coexist; ids are never re-keyed. **Invariants (validator, code-only):** ≤1 bare member per base-scope group · members pairwise conflict on ≥1 shared non-null slot. **OD-15 race pin:** two producers first-writing concurrently can mint an equal-signature bare+hashed pair — detected free by the next write's probe, counted in the same flag, and READS treat equal-signature members of one group as ONE fact (prefer the oldest/bare id) until the repair lane cleans up. All flags are counters/logs — derivable from the graph, zero new stored artifacts.
10. **Declared owner amendments (95 row #30):** FS-03/T3.4/FACT-12 — the hash preimage is the value signature ALONE, not "normalized quote +" (the old recipe contradicted FS-03's own "never split on quote wording alone") · FACT-17 — unit resolution before collision hashing · FACT-14b — signature-slot conflicts never overwrite in normal writes · T1.4 over T3.4's letter — immutable ids permit one grandfathered bare member in a late-discovered collision (the id recipe's deterministic inputs now include the pre-batch group state).

**Honest residuals:** value-extraction noise or a paraphrased `conditions` re-extraction can mint a spurious flagged member (over-split, visible, confined to the rare collision class) · an ambiguous partial in a collision group parks until a richer extraction arrives (near-zero signal deferred, never lost) · producer races per OD-15 (detected + read-deduped + repair-lane). **Confidence: 9.5/10** — every decision is a pure function of pre-registered inputs; the residual is extraction noise itself, which no identity scheme can remove.

---

*Superseded v1 record (kept for the trail):*

#### RES · OD-8 ~~v1~~ — pin the quote_hash recipe + partial-rerun idempotency — superseded by the FINAL above (v1's quote-in-preimage and equality-only matching were refuted in review + by the adversarial panel)

1. **Real?** YES — verified: T3.4/FACT-12 define WHEN quote_hash applies but no doc pins the algorithm, normalization, value-signature, or what a partial rerun does; two builders would fork fact ids (invariant-3 violation, the worst class).
2. **Recommendation — the recipe (exact):**
   - `quote_hash = sha256( norm(quote) + "\x1f" + value_signature )[:16]` (hex, lowercase; sha256 for collision safety — h32 stays the relay-integrity hash, different job).
   - `norm(quote)` = the ONE shared format-normalizer already used for slice/measurement values (NFC → casefold → strip punctuation → collapse whitespace) — no second normalizer may exist.
   - `value_signature` = fixed-order, `"|"`-joined canonical strings of the stored value slots: `level_low|level_high|level_unit|change_value|change_unit|comparison_low|comparison_high|comparison_baseline|norm(value_text)` — nulls serialize as empty strings; numbers serialize as the EXACT post-canonicalize decimal string the writer stores (never float-formatted — no drift).
   - `"\x1f"` (unit separator) prevents concatenation ambiguity between the two halves.
   - Worked example (two-scenario guidance, one event): "base case $5.0B" (point 5000, m_usd) vs "conservative case $4.5B" (point 4500, m_usd) → same driver+scope, different signatures → both facts get hashes; neither keeps the bare id (T3.4 unchanged).
   - **Partial-rerun idempotency (the new pin):** collision detection is batch-local by construction (one CLI invocation = one event), so ADD one graph read to the id-build path: before finalizing ids, the CLI queries existing DriverUpdates matching (event + driver + fact_scope-prefix-without-quote_hash). If any existing sibling carries a quote_hash → the collision set is ALREADY OPEN: the new/re-run item is ALSO hashed (its hash equal to an existing node's → same fact, MERGE in place; different → a further collision member). If only a bare-id node exists → no collision was ever declared → a re-extracted identical fact converges to the bare id (normal MERGE). This restores "no colliding fact keeps the bare id" across ANY rerun subset, deterministically, with one query and zero graph surgery.
3. **Confidence: 9/10.** Every ingredient reuses an existing pinned element (shared normalizer, stored decimal strings, batch-local fusion, MERGE semantics); the idempotency read is the one addition and is unavoidable in principle (the information lives only in the graph). Reserve: the exact slot list of value_signature should be re-checked once against the final field spec at build time.

#### RES · OD-9 — pin measurement tokenization [14 §3 #3]

1. **Real?** YES — verified: FS-25 pins normalization-per-token and code-sorted comma-joining but not multi-word handling; "cash EPS"/"constant currency" would fork ids between builders.
2. **Recommendation — two clean layers, only one of which is new:**
   - **Label segmentation (NOT new — already FS-25's semantics, restated):** the producer emits the STATED measurement label(s); separately-stated stacked flavors = separate tokens ("adjusted, diluted EPS" → two labels); words that state ONE basis together = one label ("constant currency", "as reported", "pro forma", "non-GAAP"). The metric noun itself is never a measurement label ("cash EPS" → label "cash"; "EPS" is the driver).
   - **Per-label normalization (the new pin):** NFC → casefold → internal spaces AND hyphens → `_` → strip all other punctuation → collapse repeats. One label = ONE token, never split. Worked examples: "Adjusted diluted" → `{adjusted, diluted}` (two stated labels) · "cash EPS" → `{cash}` · "non-GAAP" → `{non_gaap}` (matches the legacy token exactly) · "constant currency" → `{constant_currency}` · "as reported" → `{as_reported}`. Serialization stays FS-25's: code-sort, comma-join.
3. **Confidence: 9/10.** The normalization is mechanical and matches every existing token spelling in the docs (`non_gaap`, `constant_currency`, `as_reported`); the segmentation boundary stays a producer-semantics judgment FS-25 already owns — no new judgment surface was created.

#### RES · OD-10 — enumerate the unit-family map [14 §3 #4 · ISS-55]

1. **Real?** YES — verified: 09 §6.1 names the family map as NEW code ("build + unit-test it — it is not a port") but never enumerates it; ISS-55's percent_qoq question is entangled.
2. **Recommendation — the full map (change_unit → the series-unit slot a delta-only fact joins):**
   `basis_points → percent` · `percent_points → percent` · `percent → percent` · `percent_yoy → percent_yoy` (its OWN family — a growth-rate series must never blend into a margin/level series; PER-14's no-blend logic) · `m_usd → m_usd` · `usd → usd` (money deltas join their own scale; scale mixing is prevented upstream by the resolver) · `count → count` · `x → x` · `unknown → absorbed` into the series matching the other key parts (ports `resolve_unit_groups`' existing unknown-absorption). Numberless facts join the series matching the other key parts (already pinned). Cross-family NEVER joins (existing rule). `percent_qoq`: stays OUT of the enum per UNIT-12's lean — see OD-11, which removes the pressure fail-closed; the map gains a row only if the owner ever adds the unit.
3. **Confidence: 8.5/10.** Small, principled, and the one judgment call (percent_yoy separate) follows directly from the no-blend guard; validated at build time by the §12.6 golden tests.

#### RES · OD-11 — %-only SEQUENTIAL guides must not be stamped percent_yoy [14 §3 #5 · tail-G1 #6]

1. **Real?** YES — verified: 09 §7 pins "%-only guides stay on `<metric>_guidance` with `level_unit=percent_yoy`" unconditionally; a semiconductor-style guide ("December-quarter revenue up 5% **sequentially**") stored as percent_yoy is actively WRONG data — worse than `unknown` (invariant 2: never store what the source didn't say).
2. **The issue, exactly:** the rule bakes a yoy assumption into a stamp that is sometimes provably false from the quote itself.
3. **Recommendation (fail-closed, zero enum churn today):**
   - Amend 09 §7's rule to be framing-aware: **explicitly sequential-framed** %-only guides ("sequentially", "QoQ", "vs Q3") → `level_unit=unknown` + the quote carries the basis + a dedicated **counter** (exactly the ISS-56 non-USD pattern). **Explicit yoy framing or annual-period guides** → `percent_yoy` (unchanged). **Ambiguous quarterly** ("up 5% next quarter") → keep `percent_yoy` as the documented default reading (standard finance convention; documented, not silent).
   - The counter IS the production evidence UNIT-12 demands: if sequential guides prove material, add `percent_qoq` then. Note: the historical blocker on enum growth — verbatim alignment with old Guidance (UNIT-01) — is now dead weight, since Track C v2.0 archives and retires that system; only resolver/validator/family-map updates remain as the cost. Do NOT add the unit before the evidence (UNIT-12's own bar).
4. **Confidence: 8.5/10.** Fail-closed, reversible, evidence-gated; the only residual is the documented yoy-default on genuinely ambiguous phrasing — a conscious convention, logged.

#### RES · OD-12 — the sign convention for negative/loss values [14 §3 #6 · tail-G1 #2]

1. **Real?** YES — verified: no doc states whether "a loss of up to $2B" stores as a ceiling in loss-space or a floor in signed space; the shape hints can't catch a wrong choice (both encodings are shape-valid); identity, validators, and rendering all fork.
2. **Recommendation — SIGNED space, everywhere, with no exceptions:**
   - All stored numeric values are SIGNED in the metric's natural sign; losses/declines are negative. The producer emits signed values (sign is part of the STATED value — reading "a $2B loss" as −2B is comprehension, not fabrication; invariant 2 intact).
   - `level_low` = the algebraic minimum, `level_high` = the algebraic maximum — ALWAYS. Worked examples (make these validator fixtures): "a loss of up to $2B" → value ≥ −2B → **floor**: `level_low=−2000 (m_usd)` · "at least a $1B loss" → value ≤ −1B → **ceiling**: `level_high=−1000` · "a loss of $1.5–2B" → `low=−2000, high=−1500` (note the deliberate order flip vs the spoken range — the existing `low<high` validator enforces it automatically, a free tripwire) · "EPS of −$0.10 to +$0.05" → `low=−0.10, high=0.05`.
   - `driver_state` direction follows the SIGNED value (DU-09 already ignores good/bad): "loss narrowed" = the variable increased. The DU-16.2 sign rule then works unchanged (+change with increased).
   - Why signed (vs magnitude+polarity): it is the ONLY convention under which the existing shape grammar, the low<high check, the midpoint rule, and DU-09's semantics all stay coherent with ZERO new fields; loss-space would need a polarity flag (a new identity-adjacent field) and breaks midpoints.
   - Producer prompts must carry the "up to a loss = a FLOOR" mapping explicitly + one planted trap fixture (12 §12.3).
3. **Confidence: 9/10.** Fully deterministic, zero new fields, and it automatically fixes the loss-metric HALF of OD-13 (see below). Residual: producer prompt discipline on the counter-intuitive floor mapping — hence the mandatory trap fixture.

#### RES · OD-13 — OWNER-APPROVED 2026-07-06 — lower-is-better surprise arithmetic: favorability is a PRODUCER MEANING judgment; code stays polarity-free [14 §3 #7 · tail-G1 #1]

> **Provenance:** iterated across 3 competing model drafts + 2 adversarial stress-test workflows (a 24-phrasing blind-grader battery → red-team, then a 14-phrasing reframe-confirmation: **13/14 unanimous-correct, all 4 break-classes closed**). The earlier mechanical drafts (a code lower-better name-list · an "exceeded/ahead of expectations = beat" idiom rule · category words · an investment-outflow block-list) were **REJECTED** — the stress test proved they were BOTH a hidden maintained list AND breakable (negation "did not beat", idiom-polarity "provisions ahead of expectations", block-bleed onto opex/FCF, loose "beat the budget"). Two owner wording pins folded in (loose-verb → position+polarity; change_value stated-only + null-if-sign-ambiguous).

1. **Real?** YES — ISS-16 (locked) derives the surprise state `>high→beat · <low→missed` and hard-fails a directional word/number conflict. Both assume higher=better → for cost/capex/tax/churn ("opex below guidance — a beat": word=beat, number<low) the guard REJECTS a correct, common fact. Root cause: CODE is judging favorability (a MEANING call), violating the system law (code checks structure, LLM judges meaning).

2. **The decision — split structure from meaning:**
   - **CODE (polarity-free, deterministic):** computes `position` = above / inside / below / at_floor / at_ceiling; sets `in_line` when there is NO favorability wording and the actual is inside a closed range (or at a boundary); NEVER maps above→beat / below→missed, NEVER keyword-matches, NEVER assumes higher=better. A wordless producer-`beat/missed` that lands strictly inside a closed range → code corrects to `in_line` (a free polarity-free catch). All existing structural validators (units / shapes / lane / period↔fact_scope / hints) stay and still hard-fail; OD-13 removes ONLY the polarity-based directional hard-fail.
   - **PRODUCER (meaning judgment, scoped to THIS fact's actual-vs-expectation comparison):**
     - **(a) Stated favorability → set beat/missed/in_line from full-phrase MEANING** — negation/hedge-aware ("did not beat" / "failed to top" → not a beat); scope-aware (bind only to this metric; a YoY/sequential change is a metric change, a forward guidance revision is the guidance lane, a remark about another metric or the market reaction belongs to another fact).
     - **(b) Position words (above/below/exceeded/under/ahead of) and loosely-used favorability verbs ("beat/topped the budget/number/target") are DIRECTIONAL → a position claim → apply the polarity test, NOT automatic favorability.** (revenue beat budget → beat; opex beat budget → beat if clearly lower cost; **capex** beat budget → `unknown` unless framed. "provisions ahead of expectations" → a MISS.) *[owner pin, 2026-07-06]*
     - **(c) Wordless + outside range → set beat/missed only with a clean, transient, DISCARDED polarity proof** (`polarity` · `basis: source_framing | metric_meaning` · `evidence` · one sentence). `metric_meaning` is allowed ONLY if a HIGHER value has **NO COMMON MAINSTREAM story of being the favorable surprise** — opex/tax/churn stay decidable; capex/R&D/inventory/hiring/cash-burn (illustrations of the pattern, NOT a code list) need `source_framing`, else `unknown`. Invalid proof (circular / market-reaction / strategy-guess / isolated-keyword) → `unknown`.
     - **(d) Genuine doubt → `unknown`** (never a wrong label; numbers always stored, magnitude read-derivable).
   - **Open shapes:** floor ("at least X") — at floor = in_line, favorable side = beat, unfavorable = missed (per polarity); ceiling mirror; actual-range overlapping the expectation unclearly → `unknown` unless the source states favorability.

3. **Amendments (both owner-approved 2026-07-06):**
   - **ISS-16 (12 §10.5):** replace the `>high→beat / <low→missed` derivation + the directional-conflict hard-fail with the code-computes-position / producer-judges-favorability / `unknown` model above. **Unchanged:** the trigger (actual-vs-expectation writes metric + `_surprise`), the metric/temporal/guidance three-way routing, `in_line` materialization, OBJ-2.
   - **DU-16.2 (07, hard rule 2 — SIGN):** remove `beat`/`missed` from the sign rule (now `increased/decreased/raised/lowered` only). Surprise favorability is not a numeric sign — a lower-better beat has a NEGATIVE arithmetic delta.

4. **Numbers (owner pins):** actual→`level_*`, expectation→`comparison_*`. `change_value` on a surprise is null when derivable from the operands (the common case); stored ONLY when the source states a non-derivable delta AND its arithmetic sign is determinable — if the source says "beat/missed by X" but the sign is unclear (ambiguous polarity, no operands), **leave `change_value` null** (the quote carries it). Magnitude otherwise read-derived (`actual − expectation`, arithmetic-signed, polarity applied at read).

5. **Safety net (report-only — no human, no write-block):** an offline monitor flags any `_surprise` driver whose stored facts imply CONTRADICTORY polarity (outliers vs the driver's dominant implied polarity) → the repair lane. It catches wrong-side producer slips the polarity-free runtime cannot; a hard-fail is deliberately NOT used (it would reject correct lower-better facts — the original bug). Suppress on ~balanced (genuinely context-dependent) drivers.

6. **Accepted residuals (the honest floor — NOT fixable without re-mechanizing):** (i) borderline-polarity metrics (inventory, R&D, deferred revenue) are genuinely context-dependent → two producers may split beat-vs-`unknown` (never beat-vs-miss on a clear metric); the state is NOT identity, so this never forks the graph, and the dual-producer probe (12 §12.5) measures it; (ii) literal 100% precision AND recall is not attainable on open-ended language — the design delivers **deterministic-on-structure + producer-accurate-on-meaning + fail-closed-`unknown` + monitored**, the professional bar.

7. **No-list / no-human proof:** the word/idiom/category/block lists are DELETED from code and survive only as producer prompt guidance (illustrations of a principle), so the decision gate is a PRINCIPLE ("no mainstream higher-is-good story"), not list-membership. No human in the write path; ambiguity → `unknown`, not a queue.

8. **Back-port targets:** 12 §10.5 (ISS-16 amendment) + §16 (producer-contract pointer) · 07 DU-16.2 (drop beat/missed) · 14 §3 #7 (mark closed) · 90 §E (resolved) · 95 new row #31 (ISS-16 arithmetic → position + producer-favorability; amends 12 §10.5 · 07 DU-16.2). The producer-contract prose itself is part-2 producer-packet material (12 §13). **Confidence: 9.5/10** — stress-test-confirmed; the residual is the irreducible semantics of favorability, converted to honest `unknown` rather than a wrong label. *(OD-12 interaction: independent — if signed storage lands, loss metrics become higher-better automatically and this rule is unchanged; OD-13 no longer depends on OD-12 for the loss subset.)*

#### RES · OD-14 — the chronological-write invariant (late old-dated filings) [14 §3 #8 · tail-G1 #3/#5]

1. **Real?** YES — verified: guidance states + withdrawal fan-out are derived from the PIT prior view AT WRITE TIME (T11.6); the refresh design makes late old-dated filings first-class (99 §2.15); a 2024-dated filing arriving after 2025 facts were written makes the already-derived 2025 states stale (e.g. a fact marked `introduced` when a genuine prior now exists) — and nothing detects it. Same class: 12 §10.9's Event/DCM single-target rule is checked only at creation time — a late filing Event can retroactively coexist with a DCM for the same company/day.
2. **The key design insight that makes a clean fix possible:** the ONLY history-dependent stored artifacts are (i) guidance-lane `driver_state` values and (ii) withdrawal fan-out facts — both DERIVED deterministically from stored stated numbers + the prior view (states classify stored numbers; recomputing them is store-when-stated-safe). Stated values themselves never depend on history. So repair = bounded, deterministic recomputation — never graph surgery, never touching stated numbers, never re-keying ids.
3. **Recommendation:**
   - **Detect (one indexed query, at write time):** after writing fact F with date T into guidance series S (the T12.1 key), check whether S contains any fact with `date > T`. If yes → append a row to a **`state_repair_queue`** ledger (series key + T; a logged artifact — the parked_facts pattern).
   - **Repair (code-only, idempotent, no humans):** for each queued series, re-derive `driver_state` for all facts with `date > T` in chronological order using the SAME derivation code path, and re-run the withdrawal fan-out set for any later blanket withdrawals in scope; write only changed states (non-null→non-null corrections are legal "real changes" under FACT-14; the no-null-clobber rule is untouched). Scheduled by the part-2 worker; the queue makes staleness VISIBLE instead of silent either way.
   - **Event/DCM retro-overlap:** at filing-Event fact-write time, check for an existing `dcm:<cik>:<trade_date>` on the same company/ET-day → set one non-identity flag `superseded_by_event=true` on the DCM (code-set, logged); all grading/read paths EXCLUDE superseded DCMs — the single-target rule now holds at READ time regardless of arrival order. (Verdicts on the DCM are preserved as history; whether they migrate is owner-adjudicated with the parked DCM threshold question, 90 §C.)
4. **Confidence: 8.5/10.** Detection is one cheap query; repair recomputes only derived fields via existing code paths; the DCM flag mirrors the existing live-beats-backfill precedence idea. Residual: repair timing is part-2 scheduling, and the DCM-verdict migration question is consciously left with its parked sibling.

#### RES · OD-15 — concurrent producers coining near-synonym Drivers [14 §3 #9 · tail-G1 #5]

1. **Real?** YES — but bounded: verified that no serialization point is defined for live Driver creation. The actual damage: (a) two producers coining the IDENTICAL name → the `Driver.name` uniqueness constraint + MERGE semantics converge them onto one node — already safe, zero work; (b) two producers coining NEAR-SYNONYMS (`chip_shortage` vs `semiconductor_shortage`) in the race window → an OVER-SPLIT — by the one law, CHEAP and recoverable, and the standing repair lane (embeddings-suggest → Refute-judge → SAME_AS) exists precisely for this.
2. **The issue, exactly:** only (b) is real, and it is the recoverable error class; the design must simply not pretend the window doesn't exist.
3. **Recommendation (no locks, no new machinery):** pin three sentences into the part-2 admission spec: (i) exact-name convergence = the uniqueness constraint + MERGE (mandatory, already in the bootstrap); (ii) near-synonym races are ACCEPTED as over-splits, swept by the scheduled repair lane run over live-created Drivers (the existing Track A repair machinery pointed at the graph); (iii) IF part 2's worker architecture is single-queue anyway (the existing extraction-worker pattern is), route admissions through that one queue — free serialization, shrinking the window to ~zero; never build a distributed lock for a cheap-error class (over-engineering).
4. **Confidence: 8.5/10.** Grounded directly in the one law's asymmetry; every component named already exists; the only judgment is declining to armor a recoverable failure class.

#### RES · OD-16 — who writes the finalized catalog into Neo4j [14 §3 #11 · tail-G1 #8]

1. **Real?** YES — verified: 12 FACT-17's bootstrap says "Driver.name assumed from Track A" while 10 PIPE-05 lists "Neo4j production writes" as a non-goal — no step anywhere creates the Driver nodes Track B's writer requires (FACT-15 rejects facts whose OF_DRIVER target is missing).
2. **Recommendation — one small Track-B-owned tool, `catalog_graph_sync.py` (spec pinned here):**
   - **Ownership: Track B.** Rationale: Track B owns every graph-write pattern (writer, constraint bootstrap, dry-run/ENABLE discipline, owner-approved writes); Track A stays artifact-only, exactly as PIPE-05 declares. Add it to 12 §0's deliverable inventory (a FACT-15b addendum) + one cross-ref row in 10 §13.
   - **Input discipline (Stage-0, unchanged):** consumes ONLY a PIPE-35-verified shipped catalog (`validation_exit.json`: exit==0 · sha match · `final:true` · families sha) — a pre-finalization catalog hard-fails.
   - **Writes (idempotent MERGE, one transaction set):** `MERGE (d:Driver {name}) SET d.fact_type` for every record · latent bases from `families.json.latent` materialized as empty Driver nodes with `fact_type='metric'` (MF-05's "latent, empty folder") · `BASE_METRIC` edges from `families.json` · `SAME_AS` edges for FINAL-level variant RECORDS (real rolled-up records); lower-fold-collapsed variant STRINGS are not nodes — they ride as a `same_as_variants` array property on the head (mirrors PIPE-28's artifact shape exactly).
   - **The protected-input guard (closes 13 §8 + D-11's import half):** before any change, load every fact-bearing Driver (any incoming `OF_DRIVER`); a sync that would rename, re-type, delete, or ORPHAN one → HARD-FAIL the whole run. Links may only be ADDED.
   - **Ops:** dry-run default + an `ENABLE_DRIVER_WRITES`-style flag; graph writes owner-approved per the standing rule; runs AFTER finalization and BEFORE any production fact write (insert as 12 §17 step "3.5"; also a prerequisite row in the part-2 runbook).
3. **Confidence: 9/10.** Every element is an existing pattern (MERGE bootstrap, sidecar verification, dry-run gates, 13 §8's guard) assembled into the one missing step; the only decision — Track B owns it — follows from where the graph-write machinery already lives.

#### §0.R closing — state of play (2026-07-05)

- **Worked and closed in this file:** the ledger re-sync (SYNC, applied in place) + 13 doc-debt resolutions (D-1…D-13, exact edits specified) + 16 design resolutions (OD-1 + OD-2 + OD-6 + OD-8 owner-approved 2026-07-05, OD-13 owner-approved 2026-07-06; the rest recommendations pinned). The two refuted audit items are recorded in §0.2-F; the §4 edge-case pointers were updated in place.
- **Nothing here contradicts a locked decision.** Every recommendation either completes an owner-decided amendment (D-blocks), documents the only mechanically-possible reading (OD-3), or adds the smallest guard consistent with the five §0.1 invariants — and each block names its rejected alternatives.
- **The owner sign-off queue (everything that actually needs a decision, in one list):** 95 rows #26/#27/#28 (D-1/D-3/D-13 — paste-ready) · OD-7's born-complete live admission + quarantine flag · OD-11's sequential-% fail-closed rule · OD-12's signed-space convention · OD-14's repair queue + DCM supersede flag · OD-16's Track-B ownership of `catalog_graph_sync.py`. Everything else in §0.R is wording-sync a doc-editing pass can apply without new decisions.
- **After sign-off, the back-port pass applies:** OD-1→10 PIPE-24/25/26/36 + 12/14/90 pointers · D-1→04/95 · D-2→09/07/95 · D-3→03/09/95 · D-4→12 · D-5→08 · D-6/D-7→03 · D-8→03/10 · D-9→90 · D-10→10 · D-11→10 · D-12→00 · D-13→each row's doc · remaining OD rules→their owning docs per block. Per 14's authority note: a rule is closed only when written into its owning doc.

---

**What this is:** every tension, gap, defect, and doc-inconsistency surfaced by two independent multi-agent audits of the `FinalDesignClaude/` spec set (files `00`–`10`, `90`, `95`, `99`), **deduplicated into one unique list** (no issue appears twice). Nothing here has been changed in the specs — this is a review queue.

**How it was generated (two audits, merged):**
- **Audit A — adversarial refuter sweep (priority).** ~51 agents / 7 lenses → 38 raw findings → paired adversarial refuters hammered them down. **21 suspected defects → 16 refuted, survivors below.** This is the high-confidence set.
- **Audit B — comprehension + contradiction sweep (this session).** 13 agents (10 domain lenses + 3 adversarial critics) → **90 tensions (0 blocker · 32 real · 58 minor) + 10 edge-case scenarios + ~50 open questions.**
- Overlaps merged; where the two audits disagreed on severity, **Audit A's refuter verdict wins** (its refuters are recorded in §3 so we don't re-raise them).

**Verdict on both audits: the spec set is remarkably tight — 0 blockers.** What survives is doc-consistency polish, a handful of small missing guards, and honestly-tracked open items.

**Severity legend:** 🔴 act-on (real gap / footgun) · 🟡 doc-hygiene / low · ⚪ checked-and-dismissed / non-issue.
**Source tags:** `[A-CONF/DISP/CRIT/OBSE#]` = Audit A · `[B-R/M/E#]` = Audit B (R=real, M=minor, E=edge-case).

---

## The design, as grokked (proof, in brief)

- **One law everywhere:** over-merge = permanent damage, over-split = cheap fix → when unsure, keep separate. LLM judges meaning (assign / coin / flag, never merges two existing identities); code checks structure (exact merges, frozen deletes, hard-fails).
- **Three layers:** Driver **class** (name + fact_type + SAME_AS/BASE_METRIC only — Track A builds it; end-of-build finalization stamps fact_type + families) → DriverUpdate **fact** (id = event + driver + fact_scope; 23 fields, 5 code-written; self-describing point/range/floor/ceiling shapes with transient hints; everything company/time-specific incl. XBRL links lives here) → **verdict** as the `EXPLAINED_BY` edge (direction / force / certainty in deciles, producer in the key, PIT-safe grading).
- **fact_scope** = period + slice + measurement (format-normalized only, immutable; quote_hash last-resort); **DriverPeriod** = real calendar windows on Guidance's proven math; **units** = the 9-enum via the shared resolver with producer hints; **concept-linking** = guards → PIT menu → Haiku pick → adversarial verify → deterministic veto, abstain-biased.
- **Status honestly held:** the record-model, Track A, Track B, and Track C archive/retire designs are written; **the fitness/honesty gate has never run (0 graph nodes)**. Still open/written-elsewhere = actual update/live-backfill process, incremental refresh, model policy, FS-23, XC-16, UNIT-14/PER-20 wiring. `07`'s number layer and `99` are history; `09` and topic files win.

---

## §1 — Confirmed & high-value issues (act on these) 🔴

> Audit A's refuter-surviving findings first (the priority set), then Audit-B "real" findings A did not cover.

### From Audit A (refuter-hammered survivors)

- **ISS-1 · `[A-CONF1]` · 🔴 medium — `90_OpenItems` is incomplete as the owner's decision index.**
  Four owner-opens live **only** in `10 §13` and appear nowhere in `90 §A`: **G1 reuse-display rules · K2 fold-repair profile gate · target N = 796 vs 786 · lifecycle/dormancy + IPO absorption.** 90 §A carries only Model-policy / 8-K-taxonomy / Amendments. Not lost (10 §13 is live authority), but 90's "every open thread in one place" promise is broken.
  *Fix:* add 4 rows to 90 §A (or scope 90's claim). *(The `99 §9` opens — guidance bridge, canonical_driver, graph↔JSON mapping — are a **separate, refuted** case: see §3 / ISS-D4.)*

- **ISS-2 · `[A-CONF2]` · 🔴 low→med — Glue rule 9 has no tie-break for equal-rank same-day facts.**
  Two news items (or two 8-Ks) on one day, same series key, different values → same source rank, same day: which is the "current view" is unstated. `09:113` defines collapse by source rank across types and by event-date across days, but never orders equal-rank/same-day.
  *Fix:* break the tie with the already-stored `date` full-ISO timestamp (intraday).
  → **✅ RESOLVED 2026-07-03 (owner):** different source_ids stay separate nodes; current view = later timestamp, tie → lexicographic `source_id`; same source_id merges by normal id rules (census §14.1).

- **ISS-3 · `[A-DISP2 + B-R32]` · 🔴 medium — The `EXPLAINED_BY` verdict is only `[AGREED]`, and nothing tracks the pending lock.**
  `07:5` "remains [AGREED] until locked separately"; DU-21…24 all `[AGREED]`; `09 §5/§7` twice defer verdict-edge hashing as "a separate `EXPLAINED_BY` decision." No `90` row (A–E) tracks this lock. `00` marks `07` ✅.
  *Fix:* add a 90 §A/§B row; schedule the verdict lock.
  → **✅ RESOLVED 2026-07-03 (owner): DU-21…24 LOCKED** via `12_TrackB_FactPipeline.md` §10.1 (explained_target key wording · verdict-edge evhash16 recipe · DCM own label · trade_date owned by the returns layer); `07` upgraded, 90 §E row added.

- **ISS-4 · `[A-DISP1 + B-R7]` · 🔴 medium — Unknown-axis slice `axis:value` grammar conflicts with the kind-format check.**
  `FS-15` says unknown XBRL axis → carry the axis → `axis:value`; but `FS-05/FS-16` allow only 6 kinds + `unknown` and validate "kind ∈ 6+unknown." A literal `<axis>:<value>` fails the check; if the axis rides inside the value, the composed **immutable** serialization + separator is defined nowhere → two builders fork fact ids.
  *Fix:* one clarifying sentence in FS-15 (exact composed string + where the axis sits).
  → **✅ RESOLVED 2026-07-03 (owner):** serialize `unknown:xbrlaxis_<hex_encoded_exact_axis_qname>__<normalized_member_value>` — kind stays `unknown`, hex avoids the ':' ambiguity, no merges across unknown axes (census §14.5; FS-15 wording applied 2026-07-04 — 03 now carries the hex grammar).

- **ISS-5 · `[A-DISP3 + A-OBSE6]` · 🟡 low — Doc headers omit `10_BuildPipeline`.**
  `95` header calls the live plan "`01`–`09`" (yet 95 §C row #21's current rule lives in `10 PIPE-22`). `99` header lists "01–09, 90, 95" and its §8 build-order tells the builder to create topic files that never existed (`03_DriverUpdate`, `04_GuidanceIntegration`, `05_XBRL`, `06_BuildPlan`). `10 PIPE-06` and `00` both classify `10` as a live topic file.
  *Fix:* 95 header → "01–10"; add a one-line note to 99 (historical) that 10 outranks it on pipeline matters.

- **ISS-6 · `[A-CRIT1 + B-M4/M6/R8]` · ✅ RESOLVED 2026-07-03 (was 🔴 medium) — the alias layer is REPLACED by owner-approved member-anchored read-time grouping (census §14.4 / T12.9).**
  `FS-02/FS-19/09 §3/§5` lean on "per-company alias files" as the **only** recovery path for accepted over-splits (e.g. "adjusted" vs "non-GAAP" series splits) and even grant code a "confident alias" merge (FS-19) — but no doc defines its owner, format, confidence bar, storage, or validator, and `90` doesn't track it (its only alias row, FS-23, is the *separate* cross-company layer). Corollary: `FS-04` lists code "MERGE two existing values" but `FS-17` immutability leaves no identity-level mechanism → it must BE this read-time layer.
  *Fix:* write the alias-layer spec (or add a 90 §D "to-write" row); reconcile FS-04's "MERGE" wording with immutability.
  → **✅ RESOLVED 2026-07-03 (owner): member-anchored read-time grouping APPROVED with 3 pins** (the owner-reviewed alias-layer proposal itself stays rejected — human in the loop). Read-time only · label-level · conflict-fail-closed (zero/conflicting/missing/different links = keep separate) · group key = the `(axis_qname, member_qname)` pair, never a label · one company only · stored labels/fact IDs/write-time identity never change · `MAPS_TO_MEMBER` records which slice part it anchors. Census §14.4 + T12.9. Residuals stay split (safe): prose-only drift, measurement drift.

- **ISS-7 · `[A-CRIT2]` · 🔴 medium — The producer's write-time HISTORY READ has no point-in-time cutoff (look-ahead hole).**
  Guidance states (introduced/raised/lowered/reaffirmed) and blanket-withdrawal fan-out depend on reading prior facts. `FS-14`'s 3-context split pins PIT for **menus** only and files pure reads as "all history OK (no fact being written)" — but this history read happens **while a fact IS being written**. Sole guard = `09 §7` "chronological per-company processing," which breaks with two producers (DU-02), backfill re-runs, and late-arriving old-dated filings (IR §2.15 makes those first-class). A backfill producer on a 2024 event could read a 2025 guide as "the prior guide" and store a wrong state no validator catches.
  *Fix:* add an explicit history-read PIT rule (only facts with `date ≤ event time`).
  → **✅ RESOLVED 2026-07-03 (owner):** code-built PIT prior view, `date` strictly **<** current source timestamp; read side = two modes (historical/backtest = PIT-safe · live = current graph OK); producer history need = guidance lane only (census §14.3, T11.6, T12.8).

- **ISS-8 · `[A-CRIT3 + B-R11/M26]` · 🔴 medium — The read-time "scanner" / change-flag layer is invoked as rationale but defined nowhere.**
  Mission step 7 (`01 §7` "auto-flag a buy/sell when a cause meaningfully changes") is treated as a real component inside **locked** `09 §4/§9` decisions ("alarm-fatigue noise in the signal path," "the scanner's only sound comparator is the extractive value_text") — yet no topic file defines it (trigger rules, "meaningfully changes," outputs), it belongs to no Track, and `90 §D` (sections to write) omits it. *(Symptom: numberless metric/surprise facts have no collapse comparator because value_text is guidance-only — consciously accepted per 09 §4 revisit trigger.)*
  *Fix:* add "scanner / change-flag design" to 90 §D.

- **ISS-9 · `[A-CRIT4 + B-M39]` · 🔴 medium — The fitness gate's pass criterion "quality budget 0.1%" is undefined.**
  `PIPE-37` pins the 0.634 / 0.535 / 72% baselines but "quality budget 0.1%" appears only there + in superseded (`DriverContext`) / cost-lever (`CostCutting`, `C5`) docs pulled in only for §11 levers. For a **one-shot, graded-once** gate, an undefined criterion can't be scored.
  *Fix:* define what the 0.1% bounds (wrong-merge rate? junk-name rate? precision loss?) and over what denominator.

### From Audit B (additional real findings; not covered or refuted by A)

- **ISS-10 · `[B-R1]` · 🔴 real (wording) — "LLM never merges" understates class-level fusion.**
  `FS-04/PIPE-04/99 §1` state it as an absolute, but at the **name** layer the LLM *does* decide fusions (dedup = SAME_AS proposer; D5-SAME union). It's kept safe by *different* machinery: SAME_AS is a **reversible link** (both nodes survive), code applies only from `approved.json` and "checks approval, never meaning" (D1), + Refute + high-blast. As written it flattens a graduated authority model. *Fix:* one clarifying sentence that "never merges" is a WRITE/reversibility guarantee, not a decision guarantee.

- **ISS-11 · `[B-R2/R27/E5]` · 🔴 real — A shared macro fact has no `event` for its id.**
  `99 §3.17b`: "All three DailyCompanyMoveEvent nodes may point to the same DriverUpdate," but fact id = `event + driver + fact_scope` (DU-19). A DriverUpdate shared across many DCMEs has no single `event`. Sits inside the already-open macro path (90 §C) but the id contradiction is unaddressed.
  → **✅ DISPOSED 2026-07-03 (12 §11 / FACT-11):** pinned — the fact id's event is ALWAYS the `FROM_SOURCE` event (on the macro path, the News article); a DCM is a verdict TARGET, never the id event, so the shared-fact id is well-defined. The pure-macro (no source event) case stays parked with 90 §C.

- **ISS-12 · `[B-R3/R26/EXTRA2]` · 🔴 real (footgun) — FS-03 "restatements merge → one fact" is a READ-time statement in the WRITE-identity section.**
  Its own example (press release + MD&A) spans different events → different ids (DU-19) → they cannot write-merge; the real mechanism is glue rule 9's read-time collapse (`09 §6.9`). A builder implementing FS-03 literally could try to write-merge across events. *Fix:* reword FS-03 to point at glue rule 9.

- **ISS-13 · `[B-R5/R6]` · 🔴 real — NAME-11 step-2 needs a cross-company view the blind leaf reader doesn't have.**
  Step 2 ("that brand/product moves OTHER companies" → NAME it) is a cross-company judgment, but the leaf reader "sees only its chunk; no other company; no catalog" (PIPE-10). The line between a coinable "specific cross-company cause" (`oil_price`, `glp1_pressure`) and a banned "broad category" (`demand`, `macro`) is judgment-only. *Fix:* state whether the reader uses world-knowledge or defers the name-vs-slice call to reconcile/fold.

- **ISS-14 · `[B-R9]` · 🔴 real — FS-22 "recurs → generic" over-generalizes.**
  "A slice VALUE that recurs across companies → GENERIC ... A real specific part lives at ONE company." But `geography:china` and `product:advertising` recur across companies **and** genuinely compare; FS-23 only rescues the ambiguous ("International"/"Other"). As written it mis-flags real comparable geography/product values. *Fix:* scope FS-22 to grab-bag values.

- **ISS-15 · `[B-R10]` · 🔴 real — The sentinel's `NON_SLICE_AXES` "skip" is the one unrecoverable over-merge hole, with no self-heal.**
  A mis-vetted NON_SLICE axis → member gets no slice → silently merges into the no-slice population (the exact irreversible error the design exists to prevent). HARD-EXCLUDE auto-demotes (FS-20) and unknown → provisional (FS-12); "skip" has **no** runtime recovery — safety rests entirely on offline member-vetting. *Fix:* add a monitor/self-heal for skip, or explicitly flag the reliance.
  → **✅ DISPOSED 2026-07-03 (12 §11 / FACT-26b):** fix-minimal + accept — every sentinel "skip" is LOGGED with axis+member; the log feeds the offline re-vet cadence; the residual reliance on offline vetting is documented, not silent.

- **ISS-16 · `[B-R13]` · 🔴 real — "Beat our own prior guidance" (as a level) is metric-vs-surprise ambiguous.**
  Only `consensus` is force-routed to `_surprise`; `previous_guidance` is legal on **both** metric and surprise lanes (09 §4 / DU-15). The same sentence can land as a metric or a surprise fact — a routing call with permanent-merge consequences and no deterministic guard. *Fix:* add a forcing rule.
  → **✅ LOCKED 2026-07-03 (owner, corpus-grounded + adversarially checked):** three-way — (0) forward-looking guide-vs-guide → GUIDANCE lane (the tense trap); (1) closed actual vs an EXPECTATION comparison (own guidance OR consensus, producer-detected) → BOTH a metric fact (the level) AND a `_surprise` fact whose state is DERIVED from the two stated numbers (>high→beat · <low→missed · within→in_line) — no beat/miss word required (mirrors DU-09's metric-lane increased/decreased); a DIRECTIONAL word/number conflict hard-fails, a marginal in_line does not (word wins, DU-08); (2) actual vs a TEMPORAL prior (prior_year/sequential) → metric change only. in_line surprises materialized (full). Adversarial pass folded OBJ-1 (producer-detect trigger) + OBJ-2 (**`previous_guidance` also forbidden on metric** — true symmetry, no double-store; owner 2026-07-03, 95 #24) + OBJ-3 (directional-conflict-only). Fully closed. (90 §E.)

- **ISS-17 · `[B-R14]` · 🔴 real — A mis-kinded bare self-canonical driver has no deterministic catch.**
  `F3` keys on suffix, `F5` on variant records; a suffixless self-canonical record's fact_type rides on the finalization classifier's single verdict, and the fitness gate tests reuse/direction, not fact_type. No named safeguard.

- **ISS-18 · `[B-R15]` · 🔴 real — Metric-consensus-FORBID assumes a `_surprise` driver that may not exist.**
  `09 §4` forbids `consensus` on metric ("→ the `_surprise` driver"), but producer class-creation is unwired (`PIPE-22`, blocked on owner reuse-display rules) and Track A is the only class creator (DU-02). If `revenue_surprise` was never coined, the forbidden fact has nowhere to route.
  → **✅ RESOLVED 2026-07-03 (owner-revised rule):** governed G1/G2 reuse/create path FIRST — the producer proposes a source-grounded name, checks PIT-safe candidates, reuses only exact-same-meaning, else G2 admission; the DriverUpdate writes on admit/reuse/rewrite. PARK only when that path is unavailable / unresolved / rejected; the low-level writer never invents Drivers (`12` §10.6; scope = any missing driver).

- **ISS-19 · `[B-R28/E3]` · 🔴 real — Terminal-suffix family is purely lexical → domain nouns get mis-familied.**
  `MF-06`/`PIPE-24` create `BASE_METRIC` from any terminal `_guidance`/`_surprise`, with no semantic guard, and `NAME-16` doesn't ban "guidance." So `regulatory_guidance` / `fda_guidance` (an FDA document, not a forecast) is force-typed `guidance`, auto-stripped to `regulatory`, and auto-linked to a forced-metric latent base.
  → **✅ OWNER-APPROVED 2026-07-05 via RES · OD-1:** admission-time suffix gate + two independent source checks + `terminal_admissions.json`; bad terminal names must rewrite to a specific non-family name and re-enter normal dedup/Refute, or park by existing G2/D5.

- **ISS-20 · `[B-R29/E4/E10]` · 🔴 real — Latent bases are force-typed metric, contradicting action roots; F-checks miss it.**
  `PIPE-25` types every latent base `metric` "by definition," but a natural base can be an action root (`dividend` → `DU-06` default `action_event`). `F2` only hard-fails a **record** target; an absent action-root base creates a wrong latent metric, caught only in a **later** build. Also `F4` doesn't check `skips[]` — a G2-skipped name can still be materialized as a latent metric anchor.
  → **✅ OWNER-APPROVED 2026-07-05 via RES · OD-1:** latent base may be created only after an admitted terminal family; the anchor must be NAME-16/13-clean, non-suffixed, non-stacked, and collide with no record / variant / `skips[]` / parked name; graduation is exact `norm()` match only.

- **ISS-21 · `[B-R17]` · 🔴 real — The period cascade never exits to "no period."**
  `PER-11` first-match routing always falls through to `gp_UNDEF`, yet `PER-05/08` say periodless facts get no edge / the resolver returns `None`. The boundary is left to unspecified producer "eligibility"; any stray period-like field on a periodless action → `gp_UNDEF`, fabricating the structure PER-08 bans. *Fix:* define the deterministic signal for "emit period fields at all."
  → **✅ RESOLVED 2026-07-03 (owner):** eligibility gate (≥1 period field emitted, else no HAS_PERIOD) + unresolvable-fields-without-explicit-sentinel = HARD-FAIL as a producer bug; action_event sentinels hard-fail; guidance = real resolved period OR explicit sentinel (`12` §10.7; 95 #23; PER-11 annotated).

- **ISS-22 · `[B-R33/M44]` · 🔴 real — The consumer read key is stated narrower in FS-24 than everywhere else.**
  `FS-24` says group by driver + slice + period; `PER-14` / `09 §7` / `99 §6` require also fact_type, unit, measurement, time_type, company (+ BASE_METRIC). A consumer following FS-24 literally blends a guidance, a metric, and a surprise sharing one period — the exact merge PER-14 forbids. *Fix:* align FS-24 to the full series key.

- **ISS-23 · `[B-R35/M51/E9]` · 🔴 real→minor — One-day-duration vs instant periods collide to the same id.**
  Instant FY = `gp_2025-12-31_2025-12-31`; a genuine one-day **duration** ending Dec-31 resolves identically. MERGE is by period id (PER-18) and `time_type` is not in `fact_scope` (PER-12) → the two share a node **and** a fact_scope → silent merge, contradicting PER-17 "never merge." *Fix:* disambiguate instant/duration ids or add time_type to identity.
  → **✅ RESOLVED 2026-07-03 (owner):** normalization — a start==end duration is illegal input; the producer must mark it instant (`12` §10.7c / FACT-16.15).

- **ISS-24 · `[B-R18]` · 🔴 real (claim clarity) — The concept-link 274-co result reads as both "0 wrong" and "1 wrong."**
  `XC-13` headlines "100% precision"; `XC-07/14` show the journey "42 → 18 → 1 wrong"; `XC-15` admits a still-wrong residual (`CCL cost_of_revenue → OperatingCostsAndExpenses`). The doc reconciles it (100% = post-lock final; "1 wrong" = pre-endpoint) but the admitted residual undercuts the clean headline. *Fix:* one reconciling sentence.

- **ISS-25 · `[B-R20]` · 🔴 real — 08 XC-12 omits the "non-GAAP measurement ⇒ no inheritance" carve-out.**
  Only `09 §3` adds it. A reader of `08` alone would inherit a GAAP concept onto an adjusted guidance/surprise fact. *Fix:* back-port the carve-out into XC-12 so the concept-linking section is self-complete.

- **ISS-26 · `[B-R43/R21/R25/M52]` · 🟡 minor (reconciled w/ A-REF11) — Macro FROM_SOURCE reads as locked in topic files but open in 99.**
  Reconciliation: **News = FROM_SOURCE is LOCKED (2026-07-02); only PURE-MACRO source is open** (90 §C). Residuals: (a) the `99 §3.17b` "do not assume FROM_SOURCE→News" caution is a stale marker acknowledged nowhere; (b) the `09 §4` matrix marks FROM_SOURCE REQ on all lanes with no pure-macro carve-out. *Fix:* add the pure-macro carve-out to 09 §4; annotate/retire the 99 caution.

- **ISS-27 · `[B-R22/R23 + A-OBSE5]` · 🔴 real — The fact_type model is stated inconsistently and the "Sonnet classifies" role has no home.**
  `99 §2.16` bundles fact_type into a Sonnet-5 classifier; `10/07` make it a **separate** end-of-build stamp by a strong NON-reader (Opus); `DU-07` names "Opus" `[LOCKED]` while `PIPE-31` calls Opus "the current instance" (swap needs the PIPE-32 gate + owner sign-off). Separately, the "Sonnet classifies" half has **no MODELS slot** (PIPE-23) and **no census stage** (PIPE-10). Disposed by authority order (PIPE-08), but a cold-start builder can't tell the locked model and has nowhere to put the Sonnet pass. *Fix:* add a classify slot/stage (or state the Opus reader subsumes it) + annotate DU-07 instance-vs-policy.

- **ISS-28 · `[B-M34]` · 🔴 real (query footgun) — `DailyCompanyMoveEvent`'s label relationship to `:Event` is never stated.**
  The verdict validators enumerate the two `explained_target` cases separately; a Cypher `(:Event)-[:EXPLAINED_BY]` query would silently miss every macro verdict. *Fix:* state whether `dcm` is an `:Event` subtype or its own label, and the query implications.
  → **✅ RESOLVED 2026-07-03 (owner):** DailyCompanyMoveEvent = its OWN label, never an `:Event` subtype; verdict consumers match by edge or enumerate both labels (`12` §10.1).

---

## §2 — Low-grade / doc-hygiene nits 🟡

> Audit A observations + remaining low criticisms + Audit B minors, deduped. All non-blocking; most are one-line fixes.

**Audit A (observations + low criticisms):**
- **ISS-29 `[A-CRIT5]`** — Two stale cross-refs in `09`: (1) §8 points at a "Codex §9 L1/L2/L3 row" that does **not exist** in `99` (0 hits); (2) §5 cites "(§6.6)" for predictor citation IDs, but those are **glue rule 5** (§6.6 = policy-vs-reading routing) — an off-by-one from the pre-cut 10-rule numbering. *(overlaps B-M40)*
- **ISS-30 `[A-CRIT6]`** — Glue rule 9 "same-day" and `dcm:<cik>:<trade_date>` have **no day-boundary / timezone convention**; `date` is a full ISO timestamp, so an after-hours 8-K (18:05 ET = next-day UTC) buckets differently across implementations. *(distinct from ISS-2: which facts share a day at all.)* → **✅ RESOLVED 2026-07-03 (owner):** ET (America/New_York) calendar date of `date` for both collapse buckets and `dcm` trade_date; trading-day attribution stays with the returns layer (census §14.2).
- **ISS-31 `[A-CRIT7]`** — **News is excluded from the leaf catalog build** ("ALL non-news company sources") while the mission says the news bot reuses the catalog; the rationale lives only in the `§14` adjudication record, never in the normative body (§0–§13). News-coined drivers can only enter via live G2 (itself blocked on open G1 rules) — a consequence the manual never spells out.
- **ISS-32 `[A-OBSE1]`** — `09 §4` matrix labels `xbrl_qname`/`MAPS_TO_CONCEPT` and `company_confirmed` as **"WS = only when the source states it,"** but §3 says xbrl_qname is enrichment-written and `company_confirmed` is derivable on every guidance fact. The legend has no enrichment/always-derivable category → under-specifies when these must be present. → **✅ RESOLVED 2026-07-03:** census §6.4 legend note + 12 FACT-16 (xbrl_qname = enrichment-written, producer-FORBID at write; company_confirmed = derived who-said-it on every guidance fact).
- **ISS-33 `[A-OBSE2 + B-M17]`** — `09 §3` change row says only "strictly stated-only," dropping `DU-16` rule 6's second half (a **stated** delta still stays null when derivable from a closed level+comparison — no third copy). A builder from 09 alone stores a redundant delta 07 forbids.
- **ISS-34 `[A-OBSE3]`** — No explicit **"`change_unit` required when `change_value` is non-null"** mirror rule, though `level_unit`-required-when-any-number is pinned and delta-only facts key their series on the change-unit family (glue 1). → **✅ RESOLVED 2026-07-03 (owner):** `change_unit` REQUIRED when `change_value` non-null; `unknown` allowed (census §14.6).
- **ISS-35 `[A-OBSE4 + B-M33/M42]`** — `DU-22` verdict key says "**event** + driver + fact_scope + producer," but macro verdicts attach to a `DailyCompanyMoveEvent`; only historical `99` generalizes to "**explained_target**." *Fix:* adopt "explained_target" in DU-22.
- **ISS-36 `[A-OBSE7]`** — `90 §B` says the `09 §5` field-map "still verify against the real guidance schema (`guidance_ids.py`)," while `09`'s header says it was "already verified against the guidance writer/ids/CLI code" — residual verification scope stated in neither.
  → **✅ SUPERSEDED 2026-07-04 (Track C v2.0):** the old guidance field-map is archive/QA reference only, not a Track C production replay map. Fresh field mapping belongs to Track B / part 2.
- **ISS-37 `[A-OBSE8]`** — `00_Coverage` gives `DriverOntology.md` and `INDEX.md` a plain "✅ covered" with **no stale-trap flag**, while `95`'s stale-trap list and `PIPE-06` both mark them stale on naming (00 *does* flag `Drivers.md`). A reader of 00 alone could treat DriverOntology as a safe naming source. → **✅ RESOLVED 2026-07-04:** 00 §2 now flags both (`DriverOntology.md` "✅ / ⛔ stale bits" · `INDEX.md` "stale measurement/name bits logged in 95").
- **ISS-38 `[A-OBSE9 + B-M46]`** — `95` header claims every flipped block carries a "Replaces #N" back-pointer, but rows **#6/#7/#8/#12/#14/#15** have no such pointer in their live blocks → a grep-based reversal audit under-counts.
- **ISS-39 `[A-OBSE10]`** — `95` row #12 still carries "(re-confirm at slices)" although `03` is written and locks it (`FS-21`); the row also cites `FS-08/FS-02` while the block that states the reversal is `FS-21`.
- **ISS-40 `[A-OBSE11 + B-M58]`** — `00` dates `10` "adjudicated + committed 2026-07-02," while `10`'s STATUS is 2026-07-03 (Round-6 nine fixes + the DU-02 wording clarification). Trivia.

**Audit B (additional minors):**
- **ISS-41 `[B-M1]`** — Concept-link rhetoric pulls two ways: `XC-01` "a wrong link is the **cardinal sin**" vs `XC-08` "a bad trade on a **recoverable** link" (used to refuse dropping 87 correct links). Both defensible; could confuse a maintainer's future veto/prompt trade-offs.
- **ISS-42 `[B-M3]`** — "Over-split is recoverable" has an **unadvertised exception**: `PER-17` `ON CREATE SET` dates do **not** self-correct on rerun (write-once-date footgun). Mitigation (parity tests + uniqueness constraint) is only build-pending (PER-20).
- **ISS-43 `[B-M8]`** — Naming docs' slice-list ("brand … channel") ≠ the `FS-06` kind-set: naming names "brand" (FS-08: **not** a kind) and omits `entity_ownership` (a real 6th kind).
- **ISS-44 `[B-M9]`** — Empty measurement: `NAME-14/FS-25` "never assume GAAP" vs `XC-05` "empty measurement … are GAAP-compatible" (a soft GAAP assumption in the concept-router).
- **ISS-45 `[B-M10]`** — Meta-rule `NAME-19`/`DU-07` bans baking examples into rules, but `DU-06`'s bare-root default **hard-codes a named-example list** (litigation/convertible_notes/… → metric; corporate_restructuring/asset_impairment → action_event).
- **ISS-46 `[B-M11]`** — `NAME-02` "each node keeps its own evidence" vs a lower-fold-collapsed variant surviving only as a **name string** in `same_as_variants` (evidence unioned into the rep, not separably recoverable).
- **ISS-47 `[B-M13]`** — `FS-08` "the producer picks the kind, code validates it's **one of the 6**" under-states the allowed set (`FS-05`/`99 §7.5` = 6 **+ unknown**).
- **ISS-48 `[B-M14]`** — `entity_ownership`'s "least-clean, often-provisional" caution is Locked in `99 §5.7` but **absent from `03`**, the canonical rule file (FS-06 lists it as a plain co-equal kind).
- **ISS-49 `[B-M15]`** — The menu-content reversal (`FS-14`: "latest prior → **union** of all prior filings") is **not in the `95` ledger**, which claims to record every reversal.
- **ISS-50 `[B-M18]`** — `99 §7.2` validator list does not mirror the full `09 §4` FORBID matrix (omits metric-consensus-FORBID, the value_text/conditions/company_confirmed/xbrl_qname non-guidance FORBIDs, level_unit-required, shape-hint hard-fail). A builder from 99's checklist ships gaps.
- **ISS-51 `[B-M21]`** — `MF-08`'s canonical chain (`net_sales_guidance → net_sales → SAME_AS → revenue`) is **fold-dependent**: `PIPE-25` step 2 re-points the family edge at the rep when the base was collapsed, silently changing the stated chain shape.
- **ISS-52 `[B-M23]`** — **action↔action SAME_AS is unspecified** (e.g. `buyback` ↔ `share_repurchase`). The rules forbid cross-flavor and action↔metric SAME_AS but never address within-action-flavor synonyms. → **✅ CLARIFIED 2026-07-03 (12 §11):** within-flavor action↔action SAME_AS is LEGAL — the same dedup/Refute machinery applies; only cross-flavor links are banned. Track A concern; no fact-side change.
- **ISS-53 `[B-M24]`** — A **relayed unconfirmed surprise** (consensus is inherently third-party; news-driver is a producer) has no field to mark it unconfirmed — `company_confirmed` is guidance-only.
- **ISS-54 `[B-M27]`** — `PER-19` transition relies on a Neo4j uniqueness constraint that is **per-label**, so `gp_X` can exist as both `:GuidancePeriod` and `:DriverPeriod`; the "one clean window" guarantee rests only on lookup-both-labels code, not the cited constraint.
  → **✅ SUPERSEDED 2026-07-04 (Track C v2.0):** no both-label period transition is built. Old `GuidancePeriod` stays old/archive until deletion or inert quarantine; new DriverUpdate writes use `DriverPeriod`.
- **ISS-55 `[B-M29]`** — Enum asymmetry: `percent_yoy` exists but no **`percent_qoq`**; a stated QoQ growth % lands on `percent`/`percent_points`, mixing sequential and level semantics (UNIT-12 open, lean no).
- **ISS-56 `[B-M30]`** — The money enum is **USD-only** (`usd`/`m_usd`); every non-USD money fact → `unknown` (called a "safe under-merge," but currency is permanently dropped with no flag).
- **ISS-57 `[B-M36]`** — `MF-05` "**create** the base metric Driver in the same run (latent empty folder)" vs `PIPE-25` "a latent base is **NOT** a catalog.json record" (families.json only). Reconciled (artifact vs graph node) but reads as a contradiction.
- **ISS-58 `[B-M37/M50]`** — `99 §2.11` "born complete … **optional links**" vs `PIPE-21/28` **dropping** `optional_links`. 99 §2.14 flags its own "Needs alignment"; surviving class links = SAME_AS/BASE_METRIC only.
- **ISS-59 `[B-M38]`** — Two build orders: `99 §8` (16-step, whole-system, **omits the fitness gate**) vs `10 §9` (12-step Track-A, ends at the fitness gate). PIPE-06 authority makes `10 §9` govern Track A.
- **ISS-60 `[B-E1 residual]`** — No validator cross-checks **name↔unit coherence** (a per-X in the name like `per_square_foot` vs the resolved base `usd`/`count`). → **✅ RESOLVED 2026-07-03 (12 FACT-25):** the per-X lint ESCALATES to a write-time HARD-FAIL on the level slot (money level + per-denominator `unit_raw` + no `_per_` in the name ⇒ reject with rename advice); change-slot and non-USD stay warnings by the lint's design.
- **ISS-61 `[B-M19/E8]` (reconciled w/ A-REF15)** — `level_shape_hint` enum includes `none` but the contract says it's emitted only "for level numbers"; it's **under-specified whether a numberless fact must carry `hint='none'`** and whether a **missing** hint (numbers present) is itself a hard-fail. The forgotten-high protection assumes the hint is mandatory-when-numbers-present. → **✅ RESOLVED 2026-07-03 (owner):** hints REQUIRED whenever their numbers are present; missing or mismatched → hard-fail; numberless facts omit them (census §14.7).
- **ISS-62 `[B-EXTRA1 residual]`** — **Under-extraction has no write-time guard**: a producer emitting only the metric fact and dropping the co-stated surprise (or the 2nd of two scenario guidances) is silently lossy; only the fitness gate might catch it. → **Partly mitigated 2026-07-03:** the §10.8 no-null-clobber merge means a subsequent richer extraction of the same event FILLS the dropped field instead of being blocked, and a weaker rerun can't erase it (`12` §10.8/FACT-14b); genuine first-pass under-extraction still relies on §12.5 measurement.

**⚪ Checked, scoped, non-issues (recorded so we don't re-raise):**
`[B-M2/M47]` "nothing deleted" (drivers) vs frozen-delete (menu members) — scoped differently · `[B-M7]` unit in read-key not identity-key — collision safety implicit via fusion+quote_hash · `[B-M12]` glp1 carve-out described two ways, same outcome · `[B-M16]` slice-menu PIT timing wobble (reconciled 2026-07-02) · `[B-M20]` "quote is/isn't rendered" (old vs new renderer) · `[B-M25]` 99 §3.5 surprise-period example (its example has a stated period) · `[B-M28]` 09 §6.9 vs §7 time_type list (period id already encodes it) · `[B-M32]` G1 guard abbrev tokens `fcf`/`ebitda` (illustrative list) · `[B-M35]` DU-21 one-hop grading vs macro two-hop (scoped) · `[B-M41]` 795-vs-796 count (immaterial; see §3/REF9) · `[B-M48/M54]` model "Locked" in 99 vs leading-default (disposed by PIPE-08) · `[B-M49]` 10's self-stale "257" note (00 already says 261) · `[B-M57]` FS-23 filed under 90 §A vs deferred-language.

---

## §3 — Checked & dismissed by Audit A's refuters (do NOT re-raise) ⚪

> These 16 were raised then **refuted** — recorded with the refutation so they aren't re-litigated. Several are where Audit B's "real" findings landed; the refutation is why they're not in §1.

- **ISS-D1 `[A-REF1]` (= B-R31)** — "Track-A execution / never-run gate absent from `90 §B` while `90 §E` frames it resolved." **Refuted:** not silently dropped — `10` STATUS and `PIPE-37` are loud that the gate has never run; 90 §E records the landing. *(Real status-mislabel is mild; the substance is tracked in 10.)*
- **ISS-D2 `[A-REF2]`** — "Suffixed SAME_AS-variant records get no `BASE_METRIC`, vs `MF-03` requiring one on every _guidance/_surprise." **Refuted:** variants **inherit** the family through their SAME_AS rep (PIPE-25) — MF-03 satisfied at read; the narrowing is intended.
- **ISS-D3 `[A-REF3]`** — "`period_scope` in the series key stated 3 ways." **Refuted:** the resolved period id already encodes instant/duration + scope; PER-13's key is authoritative.
- **ISS-D4 `[A-REF4]` (= B-R30)** — "`99 §9` owner-opens (guidance bridge · canonical_driver back-pointer · graph↔JSON mapping · producer role names · news-impact skill) missing from 90." **Refuted:** `99` is a **non-authority historical** file; `PIPE-08` cross-checks its recorded decisions rather than requiring them in 90. *(Contrast ISS-1: those live in the LIVE `10 §13`, so 90 IS obligated.)*
- **ISS-D5 `[A-REF5]`** — "Blanket-withdrawal fan-out live (09 §7) vs parked (90 §C)." **Refuted:** it's a producer-contract rule with "owner sign-off noted," parked as not-required-for-Track-A — consistent.
- **ISS-D6 `[A-REF6]` (= B-R4)** — "No conflict policy when a second producer / re-run writes different field values to the same fact node." **Refuted:** covered by `09 §7` MERGE + direct field-comparison (implicit last-writer-wins on a detected real change). *(Worth one explicit sentence, but not a live gap.)*
- **ISS-D7 `[A-REF7]` (= B-M40)** — dup of ISS-29(1) (Codex §9 L1/L2/L3 dangling); the surviving instance is CRIT5 → ISS-29.
- **ISS-D8 `[A-REF8]` (= B-M49)** — "10 says '257 stale' but 00 shows 261." **Refuted:** the real staleness is gone (00 = 261); only 10's Round-4 note is self-stale — trivia.
- **ISS-D9 `[A-REF9]` (= B-M41)** — "795 vs 796 vs 786 counts." **Refuted:** 796-vs-786 is the tracked reconciliation; 795 is loose usage in 08 — immaterial.
- **ISS-D10 `[A-REF10]`** — "`XC-10` Why-para says `FOR_COMPANY`/qname/MAPS_TO_CONCEPT live on the fact, vs 09 dropping FOR_COMPANY from DriverUpdate." **Refuted:** XC-10 describes the **old Guidance** design as the analogy, not prescriptive for DriverUpdate.
- **ISS-D11 `[A-REF11]` (= B-R21/R25)** — "99 §3.17b macro FROM_SOURCE caution contradicts the topic files." **Refuted:** News=FROM_SOURCE is LOCKED, only pure-macro open; it's a stale marker on a non-authority file. *(Residuals kept as ISS-26.)*
- **ISS-D12 `[A-REF12]`** — "90 missing the two `09 §4` revisit triggers (value_text→metric, conditions→action_event)." **Refuted:** tracked inside 09 §4 (+ 99 §3.14b); 90 not obligated to mirror every revisit trigger.
- **ISS-D13 `[A-REF13]` (= B-M45)** — "XC-11 SDK/OAuth billing vs June-15 metered-pool, absent from 90/08." **Refuted:** `10 §11` explicitly flags it as a **Track-B-wiring** reconciliation (guards keep volume near zero) — a known deferred, not a defect. *(08 XC-11 could still get a caveat.)*
- **ISS-D14 `[A-REF14]` (= B-R11/M26)** — "Glue-9 comparator undefined for numberless non-guidance facts." **Refuted:** consciously accepted per `09 §4` revisit trigger. *(The broader gap — the undefined scanner — survives as ISS-8.)*
- **ISS-D15 `[A-REF15]` (= B-M19/E8)** — "`level_shape_hint` 'none' unreachable / mandatory ambiguity." **Refuted:** minor, resolvable. *(Kept as ISS-61 for the one-line clarification.)*
- **ISS-D16 `[A-REF16]`** — "Narrowed-range midpoint rule doesn't say which prior band the validator reads." **Refuted:** resolvable via glue rule 8 ("consecutive closed shapes").

---

## §4 — Edge-case scenarios (keep as future regression tests) 🧪

> Concrete scenarios the sweep ran; ✅ = design resolves it deterministically, ⚠️ = has a residual gap (→ links to the issue above).

| # | Scenario | Verdict |
|---|---|---|
| E1 | Fact = slice + per-X + measurement + range level + point comparison ("adjusted sales/sq-ft in China $2.0–2.4k, up from $1.8k") | ✅ orthogonal slots resolve it · ✅ name↔unit lint now hard-fails on the level slot (12 FACT-25 — ISS-60 resolved; change-slot residual = warning) |
| E2 | Same event, two facts, same driver+scope, survive fusion (scenario guidance "$5B base / $4.5B conservative") | ✅ different value signatures → distinct quote_hash · ✅ cross-producer span-fork DISSOLVED by RES · OD-8 (signature-only hash — the quote never enters the preimage; owner-approved 2026-07-05) |
| E3 | Suffix-like token mid-name (`guidance_revision_cost`) vs terminal domain-noun (`regulatory_guidance`) | ✅ mid-name safe (terminal-only) · ✅ terminal domain-noun case owner-decided by RES · OD-1 suffix gate; back-port pending |
| E4 | Latent base collides with a `same_as_variants` string / a `skips[]` park entry | ✅ variant-string collision already covered · ✅ `skips[]`/parked collision owner-decided by RES · OD-1 valid-latent-anchor check; back-port pending |
| E5 | Macro/news fact with no filing event; multi-company shared macro fact | ⚠️ pure-macro FROM_SOURCE open; shared-fact `event`-id undefined (ISS-11, ISS-26) |
| E6 | Segment structure changes; backfill fact lands in the gap | ✅ PIT menu → over-split-safe · subtlety: write-order immutability vs event-time PIT can strand a segment until the unbuilt cross-company layer (FS-23) |
| E7 | "adjusted" vs "non-GAAP" splits one series | ✅ explicitly accepted loss (measurement drift is NOT covered by member grouping — stays split by design; ISS-6's slice-label half resolved via T12.9) |
| E8 | Producer fills `level_low`, forgets `level_high` on a point | ✅ shape-hint hard-fails (point≠floor) · ✅ a MISSING hint with numbers present is ALSO a hard-fail (census §14.7 — ISS-61 resolved) |
| E9 | Instant vs one-day-duration FY ending Dec-31 | ✅ resolved by normalization — a start==end duration is illegal input; the producer must mark it instant (12 FACT-16.15 — ISS-23 resolved) |
| E10 | `BASE_METRIC` target resolves to an action_event (`dividend_guidance → dividend`) | ✅ F2 hard-fails a record target · ✅ absent-base action/document latent blocked by RES · OD-1 admission gate + valid-latent-anchor check; back-port pending |
| E-x | One sentence is both a metric change and a surprise ("rose 12% to $5B, beating consensus") | ✅ metric-consensus-FORBID hard-fails / forces split · ⚠️ if the producer drops the surprise, silent loss (ISS-62) |

---

## §5 — Consolidated open owner-decisions (the union set)

**One gating ack (load-bearing — ISS-cluster `[B-R12/M5/M22/M43/M53/M55]`):** the **`09 §8`** bundle — `level_bound`→self-describing shapes + transient hints, retire fact-node `evhash16`, `qualitative`→`value_text` (amends DU-13/14/16/18). Presented as done across `07`/`09`/`95 #16-20`/`99 §3.2/§3.14`/`06 MF-11` — **✅ GRANTED 2026-07-03** (owner approved all three in-session after a walkthrough; ledgers updated same day: 90 §A→§E, 95 §B intro, 09 header/§8, 00). No longer gating.

**Live opens (need an owner call):** ~~verdict-layer lock~~ (**✅ LOCKED 2026-07-03** via `12` §10.1 — DU-21…24 upgraded, `07` §F; see ISS-3; kept struck-through here so the union list stays complete) · G1 reuse-display rules · K2 fold-repair gate · target N 796 vs 786 · lifecycle/dormancy + IPO absorption (all ISS-1) · FS-23 cross-company value comparison · UNIT-12 `percent_qoq` · 8-K 24-tag taxonomy reuse · amendment handling · macro significance threshold + pure-macro source · XC-16 mandatory-before-any-rollout-or-only-full-universe · §10 dormant XBRL-link write path (Codex §4.8) · final model policy (Opus-reads/Sonnet-classifies is a leading default only).

**Design-done, build/wiring not done:** UNIT-14 (resolver wiring) · PER-20 (`driver_period_resolver.py`, 21 tests, YTD/TTM non-Dec-FYE proof) · XC-16 + concept-link full-universe run · min_score 0.60 vs code-0.72 · prompt-mirror tests for the inlined NAME rules · `--measure-inherit` counter.

**Sections still to write (90 §D + surfaced):** actual update/live-backfill process · incremental refresh · Overview finish · **the scanner / change-flag layer (ISS-8)**. *(Track C archive/retire is now written in `13`; the within-company alias layer is no longer a section to write — ISS-6 resolved 2026-07-03 by member-anchored grouping, census §14.4/T12.9.)*

**The real gate:** RUN the fitness/honesty gate (`PIPE-37`) — never run, 0 graph nodes; must beat 0.634 / 0.535 / 72%; criterion "quality budget 0.1%" undefined (ISS-9).

---

## Appendix — sources & method

- **Audit A** (refuter-hammered survivors): `/tmp/claude-1000/-home-faisal-EventMarketDB/4dac6ff4-c4b2-4395-bb42-ce1495688e97/tasks/woyuee4g0.output` — result keys `confirmed`(2) `disputed`(3) `critic_findings`(7) `observations`(11) `refuted_summaries`(16).
- **Audit B** (comprehension + contradiction sweep, this session): workflow `wf_1819d23e-4df`; per-agent journal `…/subagents/workflows/wf_1819d23e-4df/journal.jsonl`; full result `…/tasks/wxv0yyy0y.output` (90 tensions · 10 edge cases · ~50 open questions).
- **Reconciliation rule applied:** where the two audits disagreed on severity, Audit A's refuter verdict governs (its dismissals are §3, not silently dropped).
- **Doc paths:** issues cite files by number/rule-id (`FS-15`, `PIPE-37`, `09 §4`, `90 §A`) — unambiguous within `FinalDesignClaude/`.
- **No spec files were modified.** Suggested fixes are inline (`*Fix:*`); nothing applied per the standing "propose before changing" rule.



******

  Group 1 — new edge cases NOT in the 66 ledger (the highest-value output):

  #: 1
  Finding: Lower-is-better metrics break the new surprise arithmetic. ISS-16
    (just locked) derives beat/missed as above range → beat. For cost_guidance
    (06's own example!), capex, tax_rate, churn: "opex came in below our
    guidance, beating expectations" → word says beat, number is below range →
  the
     directional-conflict rule hard-fails a correct,  common fact
  Why it bites: A freshly-locked rule mis-handles a whole metric class
  ────────────────────────────────────────
  #: 2
  Finding: Negative/loss values have no sign convention. "A loss of up to $2B"
  is
     a ceiling in loss-space but a floor in signed space; the shape hints can't
    catch a wrong choice
  Why it bites: Identity + rendering fork between two implementers
  ────────────────────────────────────────
  #: 3
  Finding: No chronological-write invariant. Guidance states + withdrawal
  fan-out
     depend on the PIT prior view of what's already written; late-arriving
    old-dated filings (first-class in the refresh design) can silently corrupt
    states — no repair trigger exists
  Why it bites: Silent wrong states, no validator catches it
  ────────────────────────────────────────
  #: 4
  Finding: quote_hash isn't idempotent. A weaker re-run that extracts only 1 of
  2
     colliding facts sees no collision → writes the bare id → a third duplicate
    node
  Why it bites: Undoes the "none keeps the bare id" guarantee
  ────────────────────────────────────────
  #: 5
  Finding: Late filing breaks the Event/DCM single-target rule retroactively
    (rule checks only at creation time); re-issued-after-withdrawal guidance
    (introduced vs raised?) is undefined; two concurrent producers can coin
    near-synonym drivers with no serialization point
  Why it bites: Three write-path races with no doc'd remediation
  ────────────────────────────────────────
  #: 6
  Finding: %-only sequential guides get stamped percent_yoy (09 §7 hard-codes
  it)
     — wrong denomination for QoQ-guiding companies (semis)
  Why it bites: Actively wrong data, worse than unknown
  ────────────────────────────────────────
  #: 7
  Finding: Live governed-create (12 §10.6) has no fact_type path. The only
    stamping machinery is Track A's end-of-build finalize (which hard-fails on
    stamped input), yet FACT-15 rejects facts on fact_type-less drivers
  Why it bites: Blocks the owner-revised missing-driver rule when G1/G2 wires
  ────────────────────────────────────────
  #: 8
  Finding: Nobody owns catalog→graph materialization. 12 assumes Driver nodes
    exist in Neo4j ("assumed from Track A"); 10 declares Neo4j writes a non-goal
  Why it bites: A missing build step between the two manuals
  ────────────────────────────────────────
  #: 9
  Finding: Identity-bearing under-specifications: the quote_hash recipe
    (algorithm/normalization/"value signature" unpinned), multi-word measurement

    token form ("cash EPS" → cash_eps or casheps?), and the read-time unit
  family
     map (which of the 9 units group) are all left to  the builder
  Why it bites: Two independent builds could permanently fork fact ids

  Group 2 — stale docs after the 2026-07-03 owner rulings (the back-port sweep
  that's still owed):

  - 03 + 09 still prescribe the REJECTED alias layer as the drift-recovery path
  (three auditors independently flagged this as the top item; no 95 row logs the
  reversal to member-anchored grouping).
  - 03 FS-15 still carries the dead axis:value unknown-axis grammar, marked
  LOCKED, no annotation — identity-bearing, so a builder of 03 alone forks fact
  ids (the hex format lives only in 11 §14.5 / 12). → **✅ RESOLVED 2026-07-04:** 03 now carries the hex unknown-axis format.
  - 09 §3 + §8 and 07's §D banner still show the pre-OBJ-2 wording
  (previous_guidance allowed on metric); the §4 matrices are correct.
  - 04 UNIT-04 still says one hint pair; 12 pins per-slot pairs.
  - 00_Coverage has no rows at all for 11, 12, or 66 — confirmed a stale map,
  not deliberate (00's own rule requires explicit exclusions), so the zero-loss
  statement no longer covers its own folder. Related header drift: 95 says the
  live plan is "01–09", 99 says "01–09+90+95", while 95's own §C rows cite 10
  and 12. → **✅ RESOLVED 2026-07-04:** 00 lists 11/12/13/66, and 95/99 headers point to the expanded live set.
  - ISS-19/20 fixes are now owner-approved in RES · OD-1: terminal-suffix
  admission gate, two independent checks, memo, valid-latent-anchor check, and
  exact latent graduation. Back-port still goes to 10, with 12/14/90 pointers.
  - Glossary hazards for any future builder: G1/G2 mean two unrelated systems
  (concept-linker guards vs catalog admission gates — both senses inside
  doc 12), "menu" means three artifacts, "slice" also means batch-splitting in
  the Track A diagram, and created means system-write-time on facts but
  public-filing-time on the PIT menu queries.

  Group 3 — the honest boundary of "the entire design." The folder is
  deliberately a rule-delta over external substrates, so full build-grade
  mastery also requires: HCP (the engine mechanics 10 reuses by pointer), the
  Consolidation docs (the 21 period tests, unit steps 1–7, the axis catalog —
  the ~24/~241 elimination lists exist nowhere as files yet), ~4,000 lines of
  substrate code that doc 12 line-cites, and the unwritten sections (Track C,
  incremental refresh, the scanner, Track B "part 2"). My audit read the 17 docs
  only — it did not verify the ~40 code-line claims against the actual code,
  open the external docs, or query the live graph. Those are the three natural
  next passes if you want them.
