# 66 · Issues To Be Handled — FinalDesign(Claude) review backlog

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
  → **✅ RESOLVED 2026-07-03 (owner):** serialize `unknown:xbrlaxis_<hex_encoded_exact_axis_qname>__<normalized_member_value>` — kind stays `unknown`, hex avoids the ':' ambiguity, no merges across unknown axes (census §14.5; FS-15 wording update pending).

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

- **ISS-12 · `[B-R3/R26/EXTRA2]` · 🔴 real (footgun) — FS-03 "restatements merge → one fact" is a READ-time statement in the WRITE-identity section.**
  Its own example (press release + MD&A) spans different events → different ids (DU-19) → they cannot write-merge; the real mechanism is glue rule 9's read-time collapse (`09 §6.9`). A builder implementing FS-03 literally could try to write-merge across events. *Fix:* reword FS-03 to point at glue rule 9.

- **ISS-13 · `[B-R5/R6]` · 🔴 real — NAME-11 step-2 needs a cross-company view the blind leaf reader doesn't have.**
  Step 2 ("that brand/product moves OTHER companies" → NAME it) is a cross-company judgment, but the leaf reader "sees only its chunk; no other company; no catalog" (PIPE-10). The line between a coinable "specific cross-company cause" (`oil_price`, `glp1_pressure`) and a banned "broad category" (`demand`, `macro`) is judgment-only. *Fix:* state whether the reader uses world-knowledge or defers the name-vs-slice call to reconcile/fold.

- **ISS-14 · `[B-R9]` · 🔴 real — FS-22 "recurs → generic" over-generalizes.**
  "A slice VALUE that recurs across companies → GENERIC ... A real specific part lives at ONE company." But `geography:china` and `product:advertising` recur across companies **and** genuinely compare; FS-23 only rescues the ambiguous ("International"/"Other"). As written it mis-flags real comparable geography/product values. *Fix:* scope FS-22 to grab-bag values.

- **ISS-15 · `[B-R10]` · 🔴 real — The sentinel's `NON_SLICE_AXES` "skip" is the one unrecoverable over-merge hole, with no self-heal.**
  A mis-vetted NON_SLICE axis → member gets no slice → silently merges into the no-slice population (the exact irreversible error the design exists to prevent). HARD-EXCLUDE auto-demotes (FS-20) and unknown → provisional (FS-12); "skip" has **no** runtime recovery — safety rests entirely on offline member-vetting. *Fix:* add a monitor/self-heal for skip, or explicitly flag the reliance.

- **ISS-16 · `[B-R13]` · 🔴 real — "Beat our own prior guidance" (as a level) is metric-vs-surprise ambiguous.**
  Only `consensus` is force-routed to `_surprise`; `previous_guidance` is legal on **both** metric and surprise lanes (09 §4 / DU-15). The same sentence can land as a metric or a surprise fact — a routing call with permanent-merge consequences and no deterministic guard. *Fix:* add a forcing rule.
  → **✅ LOCKED 2026-07-03 (owner, corpus-grounded + adversarially checked):** three-way — (0) forward-looking guide-vs-guide → GUIDANCE lane (the tense trap); (1) closed actual vs an EXPECTATION comparison (own guidance OR consensus, producer-detected) → BOTH a metric fact (the level) AND a `_surprise` fact whose state is DERIVED from the two stated numbers (>high→beat · <low→missed · within→in_line) — no beat/miss word required (mirrors DU-09's metric-lane increased/decreased); a DIRECTIONAL word/number conflict hard-fails, a marginal in_line does not (word wins, DU-08); (2) actual vs a TEMPORAL prior (prior_year/sequential) → metric change only. in_line surprises materialized (full). Adversarial pass folded OBJ-1 (producer-detect trigger) + OBJ-2 (**`previous_guidance` also forbidden on metric** — true symmetry, no double-store; owner 2026-07-03, 95 #24) + OBJ-3 (directional-conflict-only). Fully closed. (90 §E.)

- **ISS-17 · `[B-R14]` · 🔴 real — A mis-kinded bare self-canonical driver has no deterministic catch.**
  `F3` keys on suffix, `F5` on variant records; a suffixless self-canonical record's fact_type rides on the finalization classifier's single verdict, and the fitness gate tests reuse/direction, not fact_type. No named safeguard.

- **ISS-18 · `[B-R15]` · 🔴 real — Metric-consensus-FORBID assumes a `_surprise` driver that may not exist.**
  `09 §4` forbids `consensus` on metric ("→ the `_surprise` driver"), but producer class-creation is unwired (`PIPE-22`, blocked on owner reuse-display rules) and Track A is the only class creator (DU-02). If `revenue_surprise` was never coined, the forbidden fact has nowhere to route.
  → **✅ RESOLVED 2026-07-03 (owner-revised rule):** governed G1/G2 reuse/create path FIRST — the producer proposes a source-grounded name, checks PIT-safe candidates, reuses only exact-same-meaning, else G2 admission; the DriverUpdate writes on admit/reuse/rewrite. PARK only when that path is unavailable / unresolved / rejected; the low-level writer never invents Drivers (`12` §10.6; scope = any missing driver).

- **ISS-19 · `[B-R28/E3]` · 🔴 real — Terminal-suffix family is purely lexical → domain nouns get mis-familied.**
  `MF-06`/`PIPE-24` create `BASE_METRIC` from any terminal `_guidance`/`_surprise`, with no semantic guard, and `NAME-16` doesn't ban "guidance." So `regulatory_guidance` / `fda_guidance` (an FDA document, not a forecast) is force-typed `guidance`, auto-stripped to `regulatory`, and auto-linked to a forced-metric latent base. *Fix:* a semantic guard or small allowlist.

- **ISS-20 · `[B-R29/E4/E10]` · 🔴 real — Latent bases are force-typed metric, contradicting action roots; F-checks miss it.**
  `PIPE-25` types every latent base `metric` "by definition," but a natural base can be an action root (`dividend` → `DU-06` default `action_event`). `F2` only hard-fails a **record** target; an absent action-root base creates a wrong latent metric, caught only in a **later** build. Also `F4` doesn't check `skips[]` — a G2-skipped name can still be materialized as a latent metric anchor. *Fix:* have PIPE-25 consult DU-06 bare-root defaults + have F4 scan side-lists.

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
- **ISS-37 `[A-OBSE8]`** — `00_Coverage` gives `DriverOntology.md` and `INDEX.md` a plain "✅ covered" with **no stale-trap flag**, while `95`'s stale-trap list and `PIPE-06` both mark them stale on naming (00 *does* flag `Drivers.md`). A reader of 00 alone could treat DriverOntology as a safe naming source.
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
- **ISS-52 `[B-M23]`** — **action↔action SAME_AS is unspecified** (e.g. `buyback` ↔ `share_repurchase`). The rules forbid cross-flavor and action↔metric SAME_AS but never address within-action-flavor synonyms.
- **ISS-53 `[B-M24]`** — A **relayed unconfirmed surprise** (consensus is inherently third-party; news-driver is a producer) has no field to mark it unconfirmed — `company_confirmed` is guidance-only.
- **ISS-54 `[B-M27]`** — `PER-19` transition relies on a Neo4j uniqueness constraint that is **per-label**, so `gp_X` can exist as both `:GuidancePeriod` and `:DriverPeriod`; the "one clean window" guarantee rests only on lookup-both-labels code, not the cited constraint.
  → **✅ SUPERSEDED 2026-07-04 (Track C v2.0):** no both-label period transition is built. Old `GuidancePeriod` stays old/archive until deletion or inert quarantine; new DriverUpdate writes use `DriverPeriod`.
- **ISS-55 `[B-M29]`** — Enum asymmetry: `percent_yoy` exists but no **`percent_qoq`**; a stated QoQ growth % lands on `percent`/`percent_points`, mixing sequential and level semantics (UNIT-12 open, lean no).
- **ISS-56 `[B-M30]`** — The money enum is **USD-only** (`usd`/`m_usd`); every non-USD money fact → `unknown` (called a "safe under-merge," but currency is permanently dropped with no flag).
- **ISS-57 `[B-M36]`** — `MF-05` "**create** the base metric Driver in the same run (latent empty folder)" vs `PIPE-25` "a latent base is **NOT** a catalog.json record" (families.json only). Reconciled (artifact vs graph node) but reads as a contradiction.
- **ISS-58 `[B-M37/M50]`** — `99 §2.11` "born complete … **optional links**" vs `PIPE-21/28` **dropping** `optional_links`. 99 §2.14 flags its own "Needs alignment"; surviving class links = SAME_AS/BASE_METRIC only.
- **ISS-59 `[B-M38]`** — Two build orders: `99 §8` (16-step, whole-system, **omits the fitness gate**) vs `10 §9` (12-step Track-A, ends at the fitness gate). PIPE-06 authority makes `10 §9` govern Track A.
- **ISS-60 `[B-E1 residual]`** — No validator cross-checks **name↔unit coherence** (a per-X in the name like `per_square_foot` vs the resolved base `usd`/`count`).
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
| E1 | Fact = slice + per-X + measurement + range level + point comparison ("adjusted sales/sq-ft in China $2.0–2.4k, up from $1.8k") | ✅ orthogonal slots resolve it · ⚠️ no name↔unit coherence check (ISS-60) |
| E2 | Same event, two facts, same driver+scope, survive fusion (scenario guidance "$5B base / $4.5B conservative") | ✅ different value signatures → distinct quote_hash · ⚠️ same-value/same-span or cross-producer span choice can fork/merge (ISS-11 family; quote_hash span not canonicalized) |
| E3 | Suffix-like token mid-name (`guidance_revision_cost`) vs terminal domain-noun (`regulatory_guidance`) | ✅ mid-name safe (terminal-only) · ⚠️ terminal domain-noun mis-familied (ISS-19) |
| E4 | Latent base collides with a `same_as_variants` string / a `skips[]` park entry | ✅ F4 catches the variant-string case · ⚠️ F4 doesn't check side-lists (ISS-20) |
| E5 | Macro/news fact with no filing event; multi-company shared macro fact | ⚠️ pure-macro FROM_SOURCE open; shared-fact `event`-id undefined (ISS-11, ISS-26) |
| E6 | Segment structure changes; backfill fact lands in the gap | ✅ PIT menu → over-split-safe · subtlety: write-order immutability vs event-time PIT can strand a segment until the unbuilt cross-company layer (FS-23) |
| E7 | "adjusted" vs "non-GAAP" splits one series | ✅ explicitly accepted loss (measurement drift is NOT covered by member grouping — stays split by design; ISS-6's slice-label half resolved via T12.9) |
| E8 | Producer fills `level_low`, forgets `level_high` on a point | ✅ shape-hint hard-fails (point≠floor) · ⚠️ missing-hint-as-hard-fail unstated (ISS-61) |
| E9 | Instant vs one-day-duration FY ending Dec-31 | ⚠️ same id → silent merge (ISS-23) |
| E10 | `BASE_METRIC` target resolves to an action_event (`dividend_guidance → dividend`) | ✅ F2 hard-fails a record target · ⚠️ absent base → wrong latent metric (ISS-20) |
| E-x | One sentence is both a metric change and a surprise ("rose 12% to $5B, beating consensus") | ✅ metric-consensus-FORBID hard-fails / forces split · ⚠️ if the producer drops the surprise, silent loss (ISS-62) |

---

## §5 — Consolidated open owner-decisions (the union set)

**One gating ack (load-bearing — ISS-cluster `[B-R12/M5/M22/M43/M53/M55]`):** the **`09 §8`** bundle — `level_bound`→self-describing shapes + transient hints, retire fact-node `evhash16`, `qualitative`→`value_text` (amends DU-13/14/16/18). Presented as done across `07`/`09`/`95 #16-20`/`99 §3.2/§3.14`/`06 MF-11` — **✅ GRANTED 2026-07-03** (owner approved all three in-session after a walkthrough; ledgers updated same day: 90 §A→§E, 95 §B intro, 09 header/§8, 00). No longer gating.

**Live opens (need an owner call):** verdict-layer lock (ISS-3 — owner 2026-07-03: the **Track B structure plan is the lock vehicle**; DU-21…24 presented as lock-candidates in `11_TrackB_DriverUpdate_Census.md` §5) · G1 reuse-display rules · K2 fold-repair gate · target N 796 vs 786 · lifecycle/dormancy + IPO absorption (all ISS-1) · FS-23 cross-company value comparison · UNIT-12 `percent_qoq` · 8-K 24-tag taxonomy reuse · amendment handling · macro significance threshold + pure-macro source · XC-16 mandatory-before-any-rollout-or-only-full-universe · §10 dormant XBRL-link write path (Codex §4.8) · final model policy (Opus-reads/Sonnet-classifies is a leading default only).

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
  - ISS-19/20 fixes (semantic suffix guard; F4 scanning side-lists) are
  "proposed to 10" by 12 §11 — but 10 doesn't contain them and doesn't track
  them.
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
