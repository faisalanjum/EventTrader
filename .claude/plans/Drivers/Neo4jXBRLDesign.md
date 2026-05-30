
---

# Locked v1 Design

After multi-round refinement (independent reviews) — the design below is locked. Drivers BORROW guidance extraction's proven methodology + machinery (slug, M1-M4 naming, MERGE-idempotent writer, concept_resolver, member_map) but live in a **separate ontology** with their own node labels, identity rules, and PIT semantics.

## TL;DR (post E30 + Tier-6 fold of DriverImprovements v10)

```
LLM emits per driver (LEARNER ONLY per E30 + ConceptReq §3.3 + §5.4
                      — predictor is consumer-only, does NOT emit drivers
                      to the registry):

  driver_name    "iphone_china_sales" or "opec_supply"  (NOUNS only — NO state words)
  driver_state   "decelerated" or "cut"                  (VERB from registry.allowed_states)
  direction      "long" | "short"                        (this ticker's stock direction)
  evidence       ["SRC:..."]                             (canonical SRC strings)
  is_shortcut    bool DEFAULT false                      (per v8-1 — standalone-shortcut
                                                          discriminator; canonicalize
                                                          step 8 bypasses slot grammar
                                                          for is_shortcut=true Drivers)

Learner optionally emits propose_new_drivers[] when no registry match exists.

Orchestrator code (no second FULL extraction pass / no LLM canonicalizer per E20;
small persisted gated semantic judge calls at propose/unknown/borderline points
are allowed) runs BEFORE writing
complete.json sentinel. Predictor consumes registry catalog + driver_tags
from prior learner reports via prior_reports_context, but never writes to
registry (E30).

LEARNER path (post-outcome):
  1. Learner writes learning/result.json
  2. Orchestrator validates result.json (E1 PARTIAL policy)
  3. Lever #1 (E26): writer-side auto-repair wrapper runs on canonicalize()
     rejections (state-strip / period-strip / magnitude-strip with Fix #4
     exact-match-only + v4-5 V8 post-repair + v3-3 trend-partner)
  4. Lever #2 (E27): write canonical drivers via Pattern A1
     (:VocabToken with vocab_visible_at MIN-on-MATCH per v9-1+v10-1),
     Pattern A2 (:EquivalenceToken with N=2 promotion + two-phase Cypher
     per v5-4+v6-2 + intra-MERGE to_token guard per v9-2 +
     equivalence_visible_at MIN-backdate per v10-2), Pattern B (shortcuts
     direct :Driver registration per v5-5 + ≥2-token gate v7-2)
  5. Lever #3 (E28) -- Pattern A = LEARNER-SELF-CORRECT (MECHANISM UPDATED
     2026-05-29): if validation fails, the producer (learner) self-corrects WITHIN
     ITS OWN session -- after drafting driver tags it calls a deterministic validate
     tool ('driver_write_cli.py --dry-run' = canonicalize + validators), reads the
     exact per-tag rejection reasons, fixes ONLY the flagged tags, and re-validates,
     looping AT MOST 2-3 times, stopping if a rejection repeats (no progress), never
     contorting a name just to pass (drop+note instead). The orchestrator write-path
     validation is the NON-NEGOTIABLE external authority/gate: it re-validates before
     MERGE, handles partial-failure audit/drop, and the learner cannot bypass it --
     the internal loop is a convenience, not the authority. Cost $0 (extra in-session
     turns on interactive OAuth; SDK / claude -p stay forbidden/metered; NOT a second
     extraction pass per E20). This learner-self-correct loop is the PRIMARY path for
     recoverable rejects (Lever #1 deterministic auto-repair is DEMOTED/DEFERRED --
     kept, revived only if post-launch metrics show many mechanically-recoverable
     rejects, then only for unambiguous strips). An optional single orchestrator-level
     fallback retry is DEFERRED (build only if post-launch audit shows many
     gate-failures worth recovering -- same metrics-gated posture as Lever #1). The
     prior TMUX re-injection / 3-stage-merge framing
     (v3-8/v3-9/v4-8/v4-9/v4-15/v5-9/v5-11/v6-1) is SUPERSEDED; retained for reference
     pending the integration rewrite (SKILL.md + driver_write_cli.py).
  6. MERGE Driver + DriverChange (source_type=learner_result)
  7. Supersede prior DCs for SAME source_id NOT in current set
     (per R15 #1 — handles re-runs that DROP drivers; sets superseded_at +
      superseded_pit_cutoff + superseded_by_run_id)
  8. Write audit rows to :DriverAutoRepair (Lever #1), :DriverProposalRejection
     (final reject), :EquivalenceConflictAudit (v5-1+v9-2 to_token conflict),
     :EquivalenceCollisionAudit (v4-6 promotion-time Driver collision),
     :DriverDriftAudit (direction flip across re-runs) — all per E29
  9. THEN writes learning/complete.json sentinel

PREDICTOR path (pre-outcome) — CONSUMER ONLY per E30:
  Predictor's prediction/result.json §7 `key_drivers[]` STAYS as free-form
  analysis prose (Final.md §7 unchanged). Per E21 amended by E30: only §8
  (learner) schema migrates to canonical-form discipline; §7 stays as-is.
  Predictor reads:
    (a) Driver Registry Catalog (PIT-filtered per E5 +
        :VocabToken vocab_visible_at per v9-1+v10-1 +
        :EquivalenceToken{status="promoted"} equivalence_visible_at per v4-7+v10-2)
    (b) prior_reports_context.driver_tags[] from prior learner result.json files
  Predictor's complete.json sentinel does NOT depend on driver_write — driver
  registry writes are learner-only path in Phase 1.

Source_type enum (E16 amended by E30 + v7-3): {learner_result, news, fiscal_kpi}
  — prediction_result REMOVED (predictor doesn't write to registry, permanent
  stance not "for now"). Phase 2 adds news; Phase 3 adds fiscal_kpi.
```

## Why a separate Driver ontology (not just guidance)

Guidance covers financial-statement metrics that exist in XBRL. Drivers cover the **full causal universe** that moves stock prices: macro events (OPEC cuts), regulatory actions (FDA approvals), sentiment shifts, positioning, peer read-through, segment-level fundamentals — most of which have NO XBRL equivalent. We BORROW guidance's machinery; we DO NOT collapse Driver into Guidance.

```
What we BORROW from guidance:           What stays SEPARATE / driver-specific:
─────────────────────────────────────   ──────────────────────────────────────────
- slug() function                       - Driver + DriverChange node labels
- M1-M4 naming discipline               - Driver.id includes specific causal name
- MERGE-idempotent write pattern        - DriverChange slot: state replaces basis
- CONCEPT_CANDIDATES + concept_resolver - FOR_COMPANY edge carries direction
- Cross-segment XBRL inheritance        - 3-component DriverChange slot ID
- concept_family_qname fallback         - pit_cutoff = per-source logical PIT boundary
                                          (aligns with Final.md §9; NOT attributed_at).
                                          See DriverChange PROPERTIES table for full
                                          per-source formula (predictor / learner /
                                          news / fiscal_kpi).
- member_map per ticker                 - is_shortcut on Driver (v8-1 — standalone-
- normalize_for_member_match              shortcut discriminator); NO validation_status
- segment_aliases per ticker              (DROPPED per E2/OQ1 — all registered Drivers
- reduce-dedupe aliases SET               are reusable; L4 no runtime curator)
                                        - :VocabToken / :EquivalenceToken / 5 audit
                                          labels (:DriverAutoRepair, :DriverProposalRejection,
                                          :EquivalenceConflictAudit, :EquivalenceCollisionAudit,
                                          :DriverDriftAudit) — per E27 + E29 Tier-6 fold
                                        - State vocabulary (verbs) replaces
                                          guidance's basis_norm enum
                                        - per-source source_id formulas (per E30 + v7-3):
                                            learner_result    → "learner:{ticker}:{quarter}"
                                            news              → "news:{news_id}"
                                            fiscal_kpi        → "fiscal:{ticker}:{quarter}:{kpi}"
                                            prediction_result → "predictor:{ticker}:{quarter}"
                                              (FORENSIC ONLY per E30 + v7-3 — predictor
                                               is consumer-only in Phase 1; this source_id
                                               is never emitted to the registry)
                                          (NO LearnerResult/PredictionResult Neo4j nodes —
                                           both are file-backed; source_id + result_path
                                           stored as DC props per R3 #4 + R4 #1 + R9 #4)
                                        - per-source pit_cutoff formulas (see DriverChange
                                          PROPERTIES table for full per-source mapping)
```

## ChatGPT corrections accepted across multiple review rounds (R1-R11)

```
Round 1 (5 of 6 accepted):
  ✅ Axis/occurrence object split           → Driver vs DriverChange
  ✅ Exposure_role on FOR_COMPANY edge      → kept (populated only when 1 driver → N companies)
  ⊘ Magnitude as separate field            → ROLLED BACK in R16 (only v1, no v2 scope)
  ⊘ usage_scope / triggerable as FLAG      → ROLLED BACK in R16 (only v1, no v2 scope)
  ✅ Validation status provisional→validated → Driver.validation_status
       (LATER DROPPED per E2 / OQ1=DROP — see §"Locked v1 Design" TL;DR
        + Driver schema lines 189-193 "validation_status — DROPPED";
        forensic ledger entry preserved for audit-trail completeness)
  ❌ rename direction → stock_impact_direction → REJECTED (breaks Final.md long/short)

Round 2 (5 of 5 accepted):
  ✅ #1 State NEVER in driver_name          → "opec_supply" + state="cut"
  ✅ #2 Direction on FOR_COMPANY edge       → not on DriverChange property
  ✅ #3 evidence_refs canonical strings;    → CITES_EVIDENCE edges best-effort
       CITES_EVIDENCE edges optional
  ✅ #4 pit_cutoff (ON CREATE) +            → re-run-safe PIT visibility.
       written_at (ON MATCH)                    R8 #1 corrected field semantics:
                                                pit_cutoff = source pit (NOT attributed_at)
  ✅ #5 propose_new_drivers → provisional   → not silently canonical

Round 3 (5 of 5 accepted):
  ✅ #1 Ingest BEFORE complete.json         → race-free downstream consumption
  ✅ #2 Driver.segment REQUIRED w/ Total    → deterministic guidance-style
       default (not optional/null)
  ✅ #3 Simplify DriverChange slot —        → dropped from slot since
       drop segment_slug                       driver_name encodes specificity
  ✅ #4 FROM_SOURCE best-effort; no         → learner_result lives as file,
       LearnerResult node                      not Neo4j node. source_id +
                                               result_path stored as DC props
  ✅ #5 Explicit ON MATCH allowlist +       → harden PIT property drift surface
       drift logging on FOR_COMPANY edge

Round 4 (4 of 4 accepted — polish before lock):
  ✅ #1 Define learner_result_id formula    → "learner:{ticker}:{quarter_label}"
                                               + parallel formulas for news/fiscal
  ✅ #2 Fix §24 path pointer                → DriversList.md (stale) →
                                               Drivers/Neo4jXBRLDesign.md
  ✅ #3 Split registry-rendering target —   → learner bundle gets Driver registry
       learner gets registry / predictor       catalog (M1 reuse); predictor's
       gets prior driver tags                  prior_reports_context gets prior
                                               driver_tags per report
  ⊘ #4 evhash16 formula for drivers        → ROLLED BACK in R16 (only v1, no v2
       (not guidance's value+quote)             scope). evhash16 field removed from
                                                DriverChange. Re-run idempotency is
                                                provided by MERGE on stable slot ID +
                                                supersession fields (R15 #1).
```

---

# Node Schemas

## Driver node (registry — append-only, company-agnostic)

```
REQUIRED:
  name              "iphone_china_sales"               // canonical lower_snake_case form
                                                        //  what the LLM emits as driver_name
                                                        //  what Driver.id is derived from
                                                        //  IMMUTABLE once registered
                                                        //  (per ChatGPT R7 #2)
  id                "driver:" + name                    // derived; e.g. "driver:iphone_china_sales"
  label             "iPhone China Sales"               // human-readable display form
                                                        //  may evolve; name stays locked
  aliases           ["china_iphone_sales", ...]        // reduce-dedupe SET on MERGE
  registry_visible_at  ISO ts (PIT — per R11 #1)        // = min(all DC.pit_cutoff for this Driver)
                                                        //  For bootstrap-seeded drivers (no DC yet —
                                                        //   loaded from hardcoded COLD_START_SEED_DRIVERS
                                                        //   constant per E9 + OQ4, NOT a human curator
                                                        //   per L4): the bootstrap loader supplies this
                                                        //   directly at registration time (timeless-only
                                                        //   epoch for macro/regulatory drivers; per-driver
                                                        //   date for modern drivers, per E9 PIT policy).
                                                        //  ON MATCH SET = MIN(existing, new dc.pit_cutoff)
                                                        //  — backward updates allowed (correct PIT logic).
                                                        //  Used for registry catalog rendering filter.
                                                        //  NOT a wall-clock field.
  definition        one sentence
  allowed_states    ["accelerated", "decelerated",     // closed list of VERBS
                     "stable"]                         //  for this driver
  segment           "Total" (default)                   // per ChatGPT R3 #2 — REQUIRED
                                                        //  with "Total" default, NOT null.
                                                        //  "iPhone China" for decomposed
                                                        //  drivers; "Total" otherwise.
                                                        //  Used for member_map matching.
  // validation_status — DROPPED per E2 (OQ1=DROP).
  //   Original: "provisional" | "validated" (ChatGPT R2 #5). Resolved
  //   per L4 (no human curator at runtime). All registered drivers are
  //   reusable; no promotion gate. Field removed from schema.
  created_at        ISO date

OPTIONAL (code-owned — populated only when applicable; not authored by LLM):
  is_shortcut             bool DEFAULT false             // v8-1 NEW (E27 Pattern B
                                                        //  discriminator). TRUE when
                                                        //  Driver was proposed with
                                                        //  is_shortcut=true and passed
                                                        //  the shortcut acceptance path
                                                        //  (zero slot-classifying tokens
                                                        //  + ≥2-token gate per v7-2 +
                                                        //  R11 evidence + shape/banned).
                                                        //  Used by canonicalize step 8
                                                        //  (standalone-shortcut early-
                                                        //  return) — bootstrap query
                                                        //  filters Driver registry
                                                        //  via is_shortcut=true to
                                                        //  populate the shortcuts dict
                                                        //  in VocabSnapshot.
  base_label              "Sales"                       // for XBRL family resolution.
                                                        //  LLM MAY propose this in
                                                        //  propose_new_drivers[];
                                                        //  orchestrator validates +
                                                        //  OWNS the stored value
                                                        //  (per R13 #2).
                                                        //  When proposed but xbrl_qname
                                                        //  not yet resolved: stored
                                                        //  as-is, xbrl_qname stays
                                                        //  null (per E17 non-blocking
                                                        //  XBRL/member linking).
  xbrl_qname              null | "us-gaap:Revenues"     // resolved via base_label
                                                        //  (code-owned — never LLM;
                                                        //   null for non-financial
                                                        //   drivers per E17)
  concept_family_qname    null | family anchor          // fallback for derived metrics
                                                        //  (code-owned — never LLM)
  deprecated_at           ISO date                      // populated only if a driver is
                                                        //  ever soft-retired
  replaced_by             "driver:..." (canonical)      // populated only with deprecated_at

DESIGN-DECISION NOTE — fields INTENTIONALLY NOT on Driver/DriverChange
(removed in R16 cleanup; documented here so future readers don't re-introduce them
without checking the reasoning):

  - level  (macro / sector / company-specific classification on Driver)
       Removed because:
         (1) NO v1 query needs it — retrieval is exact-match driver_id; the
             registry catalog filter uses registry_visible_at, not level.
         (2) Categorization is FUZZY at boundaries — sentiment, positioning,
             peer-readthrough, technical/flow, M&A do NOT fit cleanly into a
             closed enum of 3 (macro/sector/company). An open enum is useless
             for filtering; a closed enum is wrong for reality.
         (3) ConceptualRequirements.md §5.5 raised this as
             "not sure if it helps or serves any purpose" — the answer
             turned out to be NO for v1.
       What replaces the intent:
         - driver_name itself is self-evident (yield_curve, iphone_china_sales —
           the NAME tells the reader what kind of driver it is)
         - source_type distinguishes producers (news / learner / predictor /
           fiscal_kpi) — provenance, not category
         - Final.md §6 industry+mkt_cap peer mechanism (not category-based)
       Categories are NOT maintained anywhere — M2 is a flat example list
       per the explicit "no category buckets" decision (see M2).

  - triggerable  (news/IBKR pipeline flag on Driver)
       Removed: news pipeline is Phase 2 (later). Flag becomes meaningful only
       when news pipeline ships. Re-add at that time, not before.

  - effective_from  (anachronism guard on Driver)
       Removed: registry_visible_at = MIN(DC.pit_cutoff) already provides PIT-safe
       catalog visibility without a separate field. effective_from would be a
       finer-grained "when did the mechanism exist in the world" anchor — but
       no v1 query distinguishes "first observed in our data" from "first
       existed in the world."

  - magnitude  (EV1 size-weighting on DriverChange)
       Removed: EV1 v1 does equal-weight scoring. Add if/when size-weighting
       becomes empirically warranted from EV1 v1 results.

  - evhash16  (change detection hash on DriverChange)
       Removed: MERGE on stable slot ID + supersession fields (R15 #1) provide
       re-run idempotency without a separate hash. evhash16 was a guidance-
       inherited pattern that drivers don't need given supersession.

Common theme: each removed field had "no current query needs it" + "the work
is satisfied elsewhere." Adding any of them back requires showing a v1 query
that genuinely benefits.
```

## DriverChange node (occurrence — one per source mention)

```
ID FORMULA (3 components — per ChatGPT R3 #3 + R10 #1 delimiter-safety):
  "dc:" + source_key + ":" + driver_slug + ":" + state_slug

  source_key = source_id.replace(":", "_")
  (mirrors guidance's source_id sanitization rule — guidance_ids.py:178-186.
   source_id like "learner:AAPL:Q2_FY2026" → source_key "learner_AAPL_Q2_FY2026"
   so the slot ID has exactly 3 ":" delimiters and is unambiguous.)

  source_id (unsanitized, human-readable) is preserved as a DriverChange property
  alongside source_key for lookups + display.

  (driver_slug already encodes specificity per Round 2 #1; segment lives on Driver
   registry not in DC slot. The driver_name is the specificity carrier; no
   occurrence-level segment splits are planned.)

PROPERTIES:
  source_id        per source_type (see formula table)  // PIT source — NOT 8-K accession
                                                        //  (per ChatGPT R1 #6 + R4 #1)
  source_type      "learner_result" |                   // post-outcome (learner attribution)
                                                        //   — sole Phase-1 producer per E30
                   "news" |                             // future: news pipeline (Phase 2)
                   "fiscal_kpi"                         // future: fiscal.ai ingest (Phase 3)
                   // "prediction_result" REMOVED per E30 + v7-3 — predictor is
                   //   consumer-only in Phase 1 (permanent stance, not "for now");
                   //   formula preserved FORENSIC ONLY in §source_id FORMULA below
  result_path      e.g. "earnings-analysis/Companies/   // per ChatGPT R3 #4 — file source
                   AAPL/events/Q2_FY2026/learning/      //  carried as property since
                   result.json"                          //  learner_result is not a graph node

  source_id FORMULA (per ChatGPT R4 #1 — deterministic, stable across re-runs):
    source_type="learner_result"     → "learner:{ticker}:{quarter_label}"
                                        e.g. "learner:AAPL:Q2_FY2026"
                                        1:1 with each learner run (per Final.md §22 JIT).
    source_type="prediction_result"  → "predictor:{ticker}:{quarter_label}"
                                        e.g. "predictor:AAPL:Q2_FY2026"
                                        (Formula PRESERVED FOR FORENSIC/AUDIT COMPLETENESS
                                         per E30 + CombinedPlan §source_id FORMULA — predictor
                                         is consumer-only in Phase 1, does NOT write to the
                                         Driver registry; this source_id is never emitted in
                                         Phase 1. Per ConceptReq §3.3 rewritten to align
                                         with §3.2 producer/consumer split.)
    source_type="news"               → "news:{news_id}" (Neo4j News.id)
    source_type="fiscal_kpi"         → "fiscal:{ticker}:{quarter_label}:{kpi_slug}"
  driver_id        FK to Driver
  driver_state     verb from Driver.allowed_states      // per ChatGPT R2 #1 (in slot)
  evidence_refs    [canonical SRC strings]              // per ChatGPT R2 #3
                                                        //  source of truth, ALWAYS present
                                                        //  ON MATCH: additive merge
  pit_cutoff       ISO ts (ON CREATE only)              // per ChatGPT R8 #1 + Final.md §9
                                                        //  PIT VISIBILITY field — aligns
                                                        //  with Final.md vocabulary.
                                                        //  Per-source formula (per ChatGPT R10 #4 —
                                                        //   pit_cutoff MUST be concrete, never null,
                                                        //   so `dc.pit_cutoff <= predictor.pit_cutoff`
                                                        //   predicate works uniformly):
                                                        //   prediction_result:  [FORENSIC ONLY per E30 + v7-3 —
                                                        //                        predictor doesn't write in Phase 1;
                                                        //                        formula preserved for audit completeness]
                                                        //     historical → predictor bundle pit_cutoff (= filed_8k)
                                                        //     live       → authored_at (wall-clock at write)
                                                        //   learner_result    → learner_result.pit_cutoff
                                                        //                       (always concrete per
                                                        //                        derive_learner_pit 3-tier rule)
                                                        //   news              → news.created
                                                        //   fiscal_kpi        → filing.filed
                                                        //  NEVER updated.
  authored_at      ISO ts (ON CREATE only — wall-clock) // when DC was first written.
                                                        //  For learner source = learner.attributed_at.
                                                        //  Audit-only; NOT used for PIT.
  written_at       ISO ts (ON MATCH update)             // wall-clock of latest write.
                                                        //  Audit/lineage only.
  // evhash16 + magnitude: NOT part of current scope (per R16 "only v1" cleanup).
  // If/when EV1 size-weighted scoring needs them, they get added then. Removed
  // from spec to keep the schema lean.

  // ── Supersession fields (per R15 #1 — handles re-runs that DROP drivers) ──
  superseded_at         null | ISO ts (wall-clock)       // when this DC became superseded
                                                          //  (i.e. a re-run of the same
                                                          //   source_id no longer emitted
                                                          //   this driver). Audit timestamp.
  superseded_pit_cutoff null | ISO ts (PIT)              // pit_cutoff of the superseding
                                                          //  run. Used by PIT retrieval
                                                          //  predicate: a DC is visible at
                                                          //  time T iff
                                                          //    dc.pit_cutoff <= T AND
                                                          //    (dc.superseded_pit_cutoff IS NULL
                                                          //     OR dc.superseded_pit_cutoff > T)
                                                          //  → at T_old (before supersession),
                                                          //    DC was still authoritative; at
                                                          //    T_new (after), it's hidden.
  superseded_by_run_id  null | string                    // identifier of the revising run
                                                          //  (e.g. predictor/learner run UUID
                                                          //   or the new authored_at). Audit
                                                          //  link to the supersession event.
  // If a previously-superseded DC re-appears in a later run's current set
  // (gap-then-return case), ALL THREE fields are CLEARED — the DC becomes
  // authoritative again. The drift_audit log captures the un-supersession event.

EDGES:
  (dc)-[:UPDATES]->(:Driver)
  (dc)-[:FROM_SOURCE]->(:News | :FiscalKPI)             // per ChatGPT R3 #4 + R9 #4 —
                                                        //  BEST-EFFORT: created ONLY when
                                                        //  source maps to an existing Neo4j
                                                        //  node (News, FiscalKPI).
                                                        //  For source_type=learner_result:
                                                        //  NO edge — learner_result is a
                                                        //  file-backed artifact, not a graph
                                                        //  node. source_id + result_path stay
                                                        //  as DriverChange properties only.
                                                        //  (Historical: prediction_result was
                                                        //   also file-backed before being
                                                        //   removed from the active enum per
                                                        //   E30 + v7-3.)
  (dc)-[:FOR_COMPANY {                                  // per ChatGPT R2 #2
        direction: "long" | "short",                    //  direction PER COMPANY
                                                        //  ON CREATE: set
                                                        //  ON MATCH: allowed to update,
                                                        //   but LOGGED to drift_audit
                                                        //   (per ChatGPT R3 #5)
        exposure_role?: "producer" | "consumer" |       //  news transmission role —
                        "supplier" | "competitor" |     //  populated only when a single
                        "neutral"                       //  driver_change affects multiple
                                                        //  companies with different signs
                                                        //  (e.g., OPEC cut: producers vs
                                                        //   consumers). For predictor/learner
                                                        //  drivers (1 ticker each), omitted.
      }]->(:Company)
  (dc)-[:CITES_EVIDENCE]->(:Report | :Transcript |      // BEST-EFFORT optional
                          :News)                        //  per ChatGPT R2 #3
                                                        //  populated when SRC ID parses
  (dc)-[:MAPS_TO_CONCEPT]->(:Concept)                   // inherited via Driver.xbrl_qname
  (dc)-[:MAPS_TO_MEMBER]->(:Member)                     // via Driver.segment + member_map
```

## VocabToken node (E10 + v9-1 + v10-1) — slot-vocab runtime growth store

```
SCHEMA:
  slot               "theme" | "object" | "customer" | "geography" |
                     "institution" | "metric"            // per §F.1 slot enum
  token              "hyperscaler"                       // the new slot token
                                                          //  classify_token() reads this
                                                          //  at canonicalize step 9
  added_at           ISO ts (wall-clock; audit only)
  source_driver_id   "driver:cloud_hyperscaler_revenue"  // FK to the proposing Driver
                                                          //  that first introduced the token
  vocab_visible_at   ISO ts (PIT anchor — v9-1 + v10-1)  // PIT visibility field, mirrors
                                                          //  Driver.registry_visible_at
                                                          //  ON CREATE: = source_driver.registry_visible_at
                                                          //   at write time
                                                          //  ON MATCH (token+slot exists from
                                                          //   earlier write): BACKDATE via
                                                          //   MIN(existing, $source_pit) —
                                                          //   same L6 MIN-backdate as
                                                          //   Driver.registry_visible_at
                                                          //  Read path PIT-filters:
                                                          //   WHERE vt.vocab_visible_at <=
                                                          //         datetime($run_pit_cutoff)
                                                          //  Closes L6 leak (v9-1 — PIT
                                                          //   filter on bootstrap query) +
                                                          //   closes out-of-order under-
                                                          //   visibility (v10-1 — MIN-backdate
                                                          //   on subsequent ON MATCH writes
                                                          //   reverses prior X3 deferral
                                                          //   premise that "Phase 1 is
                                                          //   chronological" — E30 doesn't
                                                          //   lock backfill order)

CONSTRAINTS:
  CREATE CONSTRAINT vocab_token_unique FOR (vt:VocabToken)
    REQUIRE (vt.slot, vt.token) IS UNIQUE;

NOTES:
  - Markdown §F.1 SLOT vocab seeds are BOOTSTRAP ONLY (NEVER mutated at runtime per L5)
  - :VocabToken append happens IMMEDIATELY at Driver-write time (no N=2 gate per v6-4
    Pattern A1 vs A2 split) — the Driver itself already passed R11+V1-V15 which
    validates the token in context. Re-gating via N=2 would needlessly delay future
    slot classification
  - Legacy pre-v9-1 rows lack vocab_visible_at; Phase-1 deployment either runs a
    one-time NULL-fill migration OR treats NULL as epoch_sentinel in the WHERE clause
    (per §13 risk register row — decide at Day 1 schema lock)
```

## EquivalenceToken node (E27 — Pattern A2 unified equivalence store)

```
SCHEMA:
  equivalence_id     UNIQUE — derived: slug("eq:" + kind + ":" + from_token)
                     // v4-6 UNIQUE constraint. Per (kind, from_token) pair -- for the
                     //   PROMOTED entry. Competing CANDIDATE to_tokens are tracked per
                     //   (kind, from_token, to_token), each with its OWN observation_keys/
                     //   count (N=2 applies PER candidate; a later "loser" can still reach
                     //   N=2). Exact key realization finalized at integration.
                     // CONFLICT SEMANTICS (locked design -- supersedes the prior v5-1
                     //   first-wins reject): Multiple CANDIDATE to_tokens may EXIST
                     //   (each evidence-gated); only ONE may PROMOTE per (kind,
                     //   from_token). A second, different evidence-backed to_token is
                     //   NO LONGER first-wins-rejected. On conflict (>=2 evidence-backed
                     //   to_tokens) FREEZE promotion + escalate to ONE isolated Pattern B
                     //   judge call that persists exactly one of:
                     //     {to_token_A, to_token_B,
                     //      NO-GLOBAL-RULE (token is context-dependent -> handle via
                     //                      driver-level reuse only),
                     //      DEFER (stay frozen; re-judge when more evidence)}.
                     //   N=2 is the ELIGIBILITY gate: the judge may only approve a candidate
                     //   that cleared N=2 -- never a one-off merely because it "sounds
                     //   better". The judge runs only on cleared candidates. Code persists the single verdict + replays it
                     //   deterministically forever. The FREEZE + judge-escalation is
                     //   recorded on :EquivalenceConflictAudit (NOT a silent reject).
                     //   Post-promotion: a later stray conflicting observation does NOT
                     //   auto-demote a promoted rule (audit only; re-judge only if it
                     //   independently clears N=2).
                     //   (builder: this changes synonym_fold.py conflict handling from
                     //    block -> judge-escalate; aligned at integration.)
  kind               "synonym" | "plural" | "acronym"
                     // v5-5: NO "shortcut" — shortcuts land as :Driver rows
                     //   directly per Pattern B (E27 acceptance rule (e)). Three
                     //   equivalence kinds share identical promotion/PIT mechanics
                     //   (kind discriminator avoids 3-label code duplication).
  from_token         "topline"                           // source form to fold from
  to_token           "revenue"                           // canonical form to fold to
                                                          //  (multiple CANDIDATE to_tokens may
                                                          //   EXIST per kind+from_token, each
                                                          //   evidence-gated; only ONE may
                                                          //   PROMOTE -- conflicts FREEZE
                                                          //   promotion + judge-escalate per
                                                          //   the locked CONFLICT SEMANTICS
                                                          //   on equivalence_id above)
  observation_keys   [...]                               // v4-1 RENAMED from
                                                          //  source_driver_ids.
                                                          //  APPEND-ONLY-IF-NOT-PRESENT.
                                                          //  observation_count =
                                                          //    size(observation_keys).
                                                          //  Each entry is EVENT-LEVEL
                                                          //  (v4-2 — strip producer prefix:
                                                          //   learner:AAPL:Q2 → AAPL:Q2;
                                                          //   news:bz-12345 stays as-is).
                                                          //  Predictor+learner on same event
                                                          //  collapse to ONE observation —
                                                          //  defensive for Phase 2/3; effective
                                                          //  no-op in Phase 1 (learner-only
                                                          //  per E30).
  observation_pit_cutoffs [...]                          // v4-7 — parallel array; one
                                                          //  entry per observation_key,
                                                          //  captures pit_cutoff at which
                                                          //  that observation occurred.
                                                          //  Used to compute
                                                          //  equivalence_visible_at.
  provenance_source_driver_ids [...]                     // v4-1 — separate provenance
                                                          //  field; audit-only, NOT used
                                                          //  for promotion counting
                                                          //  (avoids v3 conflation bug).
  first_seen_at      ISO ts (wall-clock; audit only)
  last_seen_at       ISO ts (wall-clock; audit only)
  evidence_refs      [...]                               // SRC:* refs supporting the
                                                          //  equivalence (anti-hallucination
                                                          //  per E18 / V10 stricter)
  status             "candidate" | "promoted"            // candidate until N=2 distinct-
                                                          //  source promotion (v3-14 hard
                                                          //  constant N=2). HIDDEN from
                                                          //  LLM bundle while candidate
                                                          //  (v2 Fix #2 — prevents fast-
                                                          //  pass via LLM self-reinforcement).
  promoted_at        null | ISO ts (wall-clock; AUDIT ONLY)
                                                          //  v5-12: NEVER used for PIT
                                                          //  filter; equivalence_visible_at
                                                          //  is the PIT anchor.
  equivalence_visible_at  null | ISO ts (PIT anchor)     // v4-7 + v10-2 — PIT visibility:
                                                          //  ON-SET at promotion to
                                                          //    apoc.coll.sort(observation_pit_cutoffs)[N-1]
                                                          //    (the Nth distinct
                                                          //    observation's pit_cutoff —
                                                          //    earliest PIT at which N
                                                          //    observations existed by
                                                          //    PIT-time).
                                                          //  v10-2: ON every subsequent
                                                          //    observation, re-evaluated —
                                                          //    if sort(new_pit_cutoffs)[N-1]
                                                          //    < existing equivalence_visible_at,
                                                          //    BACKDATES. Same L6 MIN-backdate
                                                          //    pattern as Driver.registry_visible_at +
                                                          //    VocabToken.vocab_visible_at.
                                                          //    Closes out-of-order under-
                                                          //    visibility scenario v4-7 alone
                                                          //    left open when E30 backfill
                                                          //    order isn't chronological.
                                                          //  Read path PIT-filters:
                                                          //    WHERE et.status = "promoted"
                                                          //      AND et.equivalence_visible_at
                                                          //        <= datetime($run_pit_cutoff)

CONSTRAINTS:
  CREATE CONSTRAINT equivalence_id_unique FOR (et:EquivalenceToken)
    REQUIRE et.equivalence_id IS UNIQUE;
  // NOTE (competing-candidate model, 2026-05-29): the equivalence_id-UNIQUE constraint
  //   above + the (kind, from_token)-only derivation + the Phase 1/2/3 two-phase Cypher
  //   are the PRIOR SINGLE-candidate realization. Under the competing-candidate model
  //   (per the equivalence_id field note above), candidate storage extends to
  //   (kind, from_token, to_token) -- either candidates as a sub-map on the (kind,
  //   from_token) node, OR per-(kind, from_token, to_token) rows + a promoted-uniqueness
  //   guard on (kind, from_token). The exact multi-candidate race-safe storage + Cypher
  //   are finalized at INTEGRATION. The SEMANTICS are the contract: per-candidate N=2
  //   eligibility, FREEZE-on-conflict, ONE isolated judge call {to_A, to_B,
  //   no-global-rule, defer}, exactly ONE PROMOTED to_token per (kind, from_token).

WRITE PATH (v5-4 compute-before-SET + v6-2 two-phase pattern):
  - Phase 0 (Python pre-check): query existing EquivalenceToken by equivalence_id;
    if exists AND existing.to_token != $to -> do NOT first-wins-reject. Both
    to_tokens are evidence-gated CANDIDATES; FREEZE promotion for this
    (kind, from_token) + record the FREEZE on :EquivalenceConflictAudit (NOT a
    silent reject). Run the N=2 evidence gate FIRST, then escalate the candidates
    that cleared N=2 to ONE isolated Pattern B judge call that persists exactly
    one of {to_token_A, to_token_B, NO-GLOBAL-RULE (context-dependent -> driver-
    level reuse only)}; code persists + replays that single verdict forever. Only
    ONE to_token may PROMOTE per (kind, from_token). Post-promotion: a later stray
    conflicting observation does NOT auto-demote a promoted rule (audit only;
    re-judge only if it independently clears N=2). The Phase 1/2/3 two-phase race
    machinery below is UNCHANGED.
    (builder: this changes synonym_fold.py conflict handling from block ->
     judge-escalate; aligned at integration.)
  - Phase 1 (Cypher MERGE): single-statement atomic. MERGE + ON CREATE/ON MATCH +
    intra-MERGE `WITH et WHERE et.to_token = $to` guard (v9-2 concurrent-writer race
    protection — closes TOCTOU between Phase 0 and Phase 1) + SET observation arrays +
    v10-2 backdate CASE in SET clause + RETURN would_promote + new_pit_cutoffs
  - Phase 2 (Python between Cypher queries): if Phase 1 returned ZERO rows → write
    :EquivalenceConflictAudit (v9-2 concurrent-conflict path). If would_promote=true:
    run collision recheck against current Driver registry (v4-6 — registry may have
    changed between candidate creation and promotion)
  - Phase 3 (conditional Cypher): SET status="promoted" + promoted_at +
    equivalence_visible_at. Uses `WHERE et.status = "candidate"` guard so concurrent
    Phase 3's are race-safe — exactly ONE status transition succeeds even when both
    writers' Phase 1 returned would_promote=true (v10-3 concurrency invariant)
```

## Audit nodes (E29 — pure telemetry for observability)

```
:DriverAutoRepair (Lever #1 / E26):
  source_id          (per v4-14 + v5-2: part of UNIQUE key with item_index)
  run_id
  item_index         (v9-4 declared property — was missing in v8 schema block
                      but required by idempotency UNIQUE on (source_id, item_index)
                      per v4-14 + v5-2)
  original_name      (the LLM's failed driver_name)
  repaired_name      (the writer's deterministic repair)
  stripped_token     (the token removed during repair)
  repair_kind        ∈ {state_to_driver_state, state_to_trend_partner (v3-3),
                        magnitude_strip (v3-2 narrowed), period_strip,
                        deferred_to_retry (Fix #4)}
  cascade_outcome    ∈ {PASS, REJECTION_NO_METRIC_TOKEN, REJECTION_BANNED_TOKEN,
                        REJECTION_TOO_MANY_SLOTS, DEFERRED_TO_RETRY,
                        FINAL_REJECT_OTHER}
                     (v3-6 / v4-17 — distinguishes "repair committed" from
                      "repair attempted → cascaded to a different rejection")
  evidence_refs      [...]
  repaired_at        ISO ts

  CONSTRAINT: UNIQUE on (source_id, item_index) per v4-14 + v5-2 + v9-4.
              Re-runs of same emission slot overwrite (last-write-wins).
              Sidecar JSON + run_ledger preserve full retry history separately
              (so adding run_id to the key would bloat telemetry — explicit
              push-back per v5 in §7 rejected suggestions).

:DriverProposalRejection (E1 PARTIAL policy + Lever #3 final rejects):
  source_id
  run_id
  proposed_name
  rejection_reason   (named V*-rule reason)
  evidence_refs      [...]
  rejected_at        ISO ts

  CONSTRAINT: MERGE on (source_id, run_id, proposed_name).

:EquivalenceConflictAudit (FREEZE + judge-escalation record + v9-2 race-time):
  equivalence_id
  existing_to        (the to_token already on the existing :EquivalenceToken row)
  proposed_to        (the conflicting, second evidence-backed to_token candidate)
  source_id
  item_index
  outcome            in {FROZEN_PENDING_JUDGE, JUDGE_RESOLVED, POST_PROMOTION_STRAY}
                     (records the FREEZE + judge-escalation, NOT a silent reject --
                      per the locked CONFLICT SEMANTICS on :EquivalenceToken)
  judge_verdict?     in {to_token_A, to_token_B, NO-GLOBAL-RULE} (set on JUDGE_RESOLVED;
                      NO-GLOBAL-RULE means context-dependent -> driver-level reuse only)
  recorded_at        ISO ts (FREEZE / judge-escalation event time)

  NOTE: a conflict FREEZES promotion (does not reject); the single judge verdict is
  persisted + replayed deterministically. A POST_PROMOTION_STRAY conflicting
  observation is audit-only -- it does NOT auto-demote a promoted rule (re-judge only
  if it independently clears N=2).

  DISTINCT FROM :EquivalenceCollisionAudit below (different mechanism, different
  audit node — v8-5 test verifies they don't conflate).

:EquivalenceCollisionAudit (v4-6 promotion-time Driver-registry collision):
  equivalence_id
  conflict_driver_id (the existing :Driver whose name would now be folded by
                      this equivalence into a DIFFERENT existing Driver if
                      promotion proceeded — collision detected at promotion
                      after registry changed since candidate creation)
  detected_at        ISO ts (wall-clock — promotion attempt time)

:DriverDriftAudit (direction flip across re-runs on :FOR_COMPANY edge):
  dc_id
  ticker
  old_direction
  new_direction
  revision_ts
  reason?            (optional — orchestrator-provided rationale if available)
```

---

# LLM Emission Contract

## Per-driver fields (4 required — emitted by LEARNER ONLY in Phase 1 per E30)

Predictor's `prediction/result.json` §7 `key_drivers[]` REMAINS FREE-FORM analysis
prose per E21 amended by E30 — predictor is consumer-only, does NOT emit canonical
drivers to the registry. The §7 line "no controlled vocabulary/tags" STANDS.

GOVERNING RULE (canonical one-liner for the producer/judge/code split): Producer
LLM handles semantics first. Isolated judge handles borderline/global/irreversible
cases. Code persists, gates, and replays decisions deterministically. Gate strength
scales with blast radius x irreversibility.

Learner writes inside `learning/result.json` — `primary_driver` + `contributing_factors[]`
(post-outcome attribution) AND can optionally emit `propose_new_drivers[]` at the
top level (per E27 Pattern A1/A2/B — learner is the sole Phase-1 producer of
canonical drivers + propose_new_drivers per E30):

```json
{
  "primary_driver": {
    "driver_name":  "iphone_china_sales",
    "driver_state": "decelerated",
    "direction":    "short",
    "evidence":     ["SRC:AAPL:Q2_FY2026:0001628280-25-..."]
  },
  "contributing_factors": [
    {
      "driver_name":  "gross_margin",
      "driver_state": "compressed",
      "direction":    "short",
      "evidence":     ["SRC:AAPL:Q2_FY2026:..."]
    }
  ],
  "propose_new_drivers": [ ... ]
}
```

## Optional propose_new_drivers (top-level, when no registry match)

```json
{
  "propose_new_drivers": [
    {
      "name":           "iphone_china_sales",
      "label":          "iPhone China Sales",
      "base_label":     "Sales",
      "segment":        "iPhone China",
      "definition":     "iPhone unit sales in mainland China + Hong Kong, per fiscal quarter",
      "allowed_states": ["accelerated", "decelerated", "stable"],
      "aliases":        ["china_iphone_sales"]
    }
  ]
}
```

Orchestrator registers proposals via MERGE Driver — all registered drivers are reusable (per E2 + OQ1 = DROP `validation_status`; per L4 = no human curator at runtime; no promotion gate). Per E27 Pattern A2 N=2 promotion gate applies to `:EquivalenceToken` only (synonyms/plurals/acronyms transforms), NOT to Drivers themselves.

---

# Naming Discipline (M1-M4, borrowed from guidance)

```
M1  REUSE existing canonical names FIRST.
    Bundle renderer adds the Driver registry catalog into the learner's prompt
    (equivalent to guidance's query 7A render). LLM searches before proposing.

M2  CANONICAL BASE-DRIVER TABLE (seeded over time) — FLAT example list.
    Examples (illustrative only, NOT a closed taxonomy):
      sales, revenue_trend, gross_margin, operating_margin, eps, capex, fcf,
      yield_curve, oil_supply, fed_rate, usd_index, vix, credit_spread,
      fda_approval, opec_supply, tariff, export_restriction, share_buyback,
      restructuring, hyperscaler_capex, ai_server_backlog, iphone_china_sales,
      china_inventory

    NO CATEGORY BUCKETS — intentionally.
    We do NOT maintain driver categories (macro / sector / company / event /
    sentiment / etc.) because:
      (1) Category boundaries are FUZZY — sentiment, positioning,
          peer-readthrough, technical/flow defy clean 3-bucket classification.
      (2) v1 retrieval is exact-match driver_id — no query needs category.
    (3) source_type already captures producer/source type (active enum per E30 + v7-3:
        learner_result, news, fiscal_kpi; "prediction_result" is forensic-only).
    The hard ontology is driver_name + driver_state + DriverChange metadata —
    NOT category.

M3  STATE NEVER IN DRIVER_NAME (per ChatGPT R2 #1).
    Driver = NOUN (causal object).  driver_state = VERB (what happened).

    Wrong: "opec_supply_cut"           → Right: name="opec_supply",         state="cut"
    Wrong: "revenue_decline"           → Right: name="revenue_trend",       state="decelerated"
    Wrong: "iphone_china_sales_drop"   → Right: name="iphone_china_sales",  state="declined"
    Wrong: "guidance_lowered"          → Right: name="forward_guidance",    state="lowered"

    Note: specific multi-word NOUNS are fine. "iphone_china_sales" is a noun
    (Sales of iPhone in China). Only verbs/state-words are banned from the name.

M4  DEFAULT Driver.segment = "Total". REQUIRED, never null (per ChatGPT R3 #2).
    Lives on the Driver registry entry, not in the DriverChange slot.
```

## Shape rules (mechanically checkable)

```
A1  lower_snake_case, ASCII only
A2  Typically ≤ 3 underscore-separated segments. ALLOW 4 only when an approved
    compound metric (gross_margin, operating_margin, cost_of_revenue,
    effective_tax_rate, free_cash_flow) is combined with specific product /
    geography / customer prefix. Example: "iphone_china_gross_margin" (4 segments,
    valid because "gross_margin" is a recognized compound metric).
    Reject "iphone_china_gross_margin_decline" — that's 5 segments AND smuggles state
    word back in. (Per ChatGPT R6 #2.)
A3  No dates / quarter / FY tokens (no q1, fy26, 2025, h1)
A4  BANNED: tickers (AAPL, NVDA, SSNLF), legal company names (apple, tesla, samsung,
    nvidia), person names (elon_musk, tim_cook).
    ALLOWED: product/brand/end-market/institution names, EVEN IF one-company-specific:
      iphone, mac, galaxy, kindle, vision_pro              (products / brands)
      ev_deliveries, smartphone, hyperscaler, cloud         (end-markets / categories)
      fed, opec, ecb, fda, sec                              (institutions / regulators)
    Rule of thumb: would a wire service use this term in a headline without
    naming the parent company? If yes → allowed. If the term IS the parent
    company → banned. (Per R13 #4.)
A5  No quantitative thresholds (no 2pct, 100bps, 10x)
A6  Discriminator required UNLESS it's a standard macro variable
    (yield_curve, oil_supply, fed_rate, usd_index, vix, credit_spread, etc.)
A7  Soft naming preference: for business/segment drivers, put the business object
    first and the metric last. Prefer:
      iphone_china_sales, hyperscaler_capex, china_inventory
    Do NOT force this on standard macro/institution names — keep their canonical
    compound form:
      yield_curve, fed_rate, opec_supply, fda_approval
    Style guide only — NOT validator-enforced. Aliases still handle duplicates if
    LLMs deviate. (Reduces duplicate proposals without adding cognitive cost or
    edge-case failures.)
```

---

# Phased Build Plan

## Phase 1 — Learner drivers (NOW; inline) — per E30 predictor is consumer-only

```
Trigger:        Orchestrator code BEFORE writing learning/complete.json sentinel
                (per ChatGPT R3 #1 — race-free downstream consumption).
                Single Phase-1 producer path: LEARNER post-outcome (per E30 —
                predictor is consumer-only; ConceptReq §3.3 rewritten to align
                with §3.2 producer/consumer split). The pre-E30 dual-producer
                design (predictor + learner both writing canonical drivers) is
                superseded; forensic record preserved in §"ChatGPT corrections"
                R1/R2/R8 ledger above + CombinedPlan §5 [E30].

LEARNER completion order (post-outcome; runs JIT before next predictor):
  1. Learner writes learning/result.json
  2. Orchestrator validates result.json (E1 PARTIAL policy + driver_name resolves
     in registry OR appears in propose_new_drivers[])
  3. Orchestrator registers any propose_new_drivers via MERGE Driver (canonical
     fields only; NO validation_status per E2/OQ1 — all registered drivers are
     reusable; L4 no runtime curator). Pattern A1/A2/B per E27 (Lever #2):
     :VocabToken immediate append + :EquivalenceToken N=2 promotion + shortcut
     Drivers direct registration.
  4. Orchestrator MERGE Driver + DriverChange (source_type="learner_result")
  5. Orchestrator SUPERSEDES any prior DCs for SAME source_id NOT in current set
     (per R15 #1 — handles re-runs that DROP previously-emitted drivers).
     Sets superseded_at + superseded_pit_cutoff + superseded_by_run_id.
     If a previously-superseded DC reappears: clear all three; log to
     :DriverDriftAudit.
  6. Orchestrator writes learning/complete.json sentinel
  7. EV1 scorer + next-quarter predictor see complete sentinel → safe to read.
     Next predictor's prediction/result.json §7 key_drivers[] stays free-form
     (per E21 amended by E30 — predictor is consumer-only, reads registry
     catalog + driver_tags from prior learner reports via prior_reports_context;
     never writes to registry).

LLM cost:       NO second FULL extraction pass / LLM canonicalizer per E20 (learner
                emits drivers in its own result.json file -- per R15 #2; predictor
                consumes registry). Two distinct cost classes -- do NOT conflate them:
                  - Pattern A re-emits run in the producer's OWN interactive OAuth
                    session (cost $0). That stays $0.
                  - The isolated Pattern B judge (borderline/unknown/shortcut +
                    EquivalenceToken conflict resolution) is an INDEPENDENT, METERED,
                    cheap, CACHED call (gpt-4o-mini / haiku, temp 0, structured output,
                    VERDICT PERSISTED). It is honestly metered -- small, cached, well
                    under $1 per cold-start batch, and decays toward $0 as the vocabulary
                    saturates and conflicts stop arising. It is NOT a free extra turn in
                    the producer session: making the producer grade its own proposal
                    would forfeit independence (the producer must not judge itself), so
                    the small metered cost is the price of an independent verdict.
                SDK / claude -p stay forbidden for the producer/extraction path (metered).
Code reuse:     ~95% of guidance machinery BY PATTERN (slug, resolver, member_map,
                writer — same architectural patterns + MERGE-idempotent shapes).
                BY LOC the verbatim-reuse fraction is much smaller (~25 LOC out of
                ~2,500 baseline ≈ 1%) — most driver code is a parallel
                implementation that MIRRORS guidance shapes without literal copy-paste.
                See `DriverProcess.html` §E "Honest 4-bucket breakdown" for details.
NEW code:       scripts/earnings/builders/
                  driver_ids.py            (mirror guidance_ids.py)
                  driver_concept_resolver.py (extend with driver-specific labels)
                  driver_writer.py         (mirror guidance_writer.py)
                  driver_write_cli.py      (orchestrator interface)
                  driver_write.sh          (Bash wrapper)
Schema work:    Driver + DriverChange constraints + indexes in Neo4j
Skills update:  ONLY earnings-learner/SKILL.md emits canonical-form drivers +
                propose_new_drivers[] in Phase 1 (per E30 — predictor is consumer-only;
                ConceptReq §3.3 was rewritten to align with §3.2 producer/consumer
                split). earnings-prediction/SKILL.md §7 key_drivers[] stays free-form
                analysis prose (per E21 amended by E30 — no canonical migration).

Bundle render:  (1) LEARNER bundle adds Driver Registry Catalog block (M1 reuse).
                (2) PREDICTOR bundle ALSO adds Driver Registry Catalog block (M1
                    READ-ONLY — predictor sees existing names for §7 free-form
                    prose authoring + prior_reports_context relevance, never
                    writes back per E30).
                (3) PREDICTOR prior_reports_context rows ADDITIONALLY include
                    driver_tags[] per prior report (for relevance ranking when
                    picking which prior reports to open).

PIT filter on Registry Catalog rendering (per ChatGPT R10 #5 + R11 #1 — vocabulary-leak guard):
  Historical runs (predictor or learner) filter the rendered catalog by
    `WHERE driver.registry_visible_at <= run.pit_cutoff`
  so a 2024 historical replay does NOT see drivers added to the registry in 2026.
  Live runs (run.pit_cutoff is null OR == now) render the full catalog — no filter
  needed; live mode has no PIT restriction.

  CRITICAL — registry_visible_at semantics (per ChatGPT R11 #1 — fixes a self-shadowing
  bug that would break reuse-existing INSIDE the same backfill):
    registry_visible_at = MIN(all DriverChange.pit_cutoff for this Driver)
    For bootstrap-seeded drivers (no DriverChange yet — loaded from hardcoded
    COLD_START_SEED_DRIVERS constant per E9 + OQ4, NOT a human curator per L4):
    the bootstrap loader supplies registry_visible_at directly at registration
    time (timeless-only epoch for macro/regulatory drivers; per-driver date for
    modern drivers, per E9 PIT policy).
    ON MATCH SET registry_visible_at = MIN(existing, new_dc.pit_cutoff)
       — backward updates allowed: backfill discovering a driver at earlier PIT pushes
         the field back; this is correct PIT logic.

  WHY this matters (independent reasoning):
    If we used wall-clock created_at instead, this fails inside a backfill:
      - Backfill at Q1 2024 proposes new driver → created_at = TODAY (e.g. 2026-05)
      - Backfill at Q2 2024 tries to reuse → filter: 2026-05 <= Q2 2024 → FALSE → hidden
      - LLM re-proposes near-duplicate → drift inside the SAME backfill run.
    registry_visible_at = min(DC.pit_cutoff) fixes this:
      - First DC at Q1 2024 → registry_visible_at = Q1 2024
      - Q2 2024 reuse query: Q1 2024 <= Q2 2024 → TRUE → visible → reused. ✓
    Mode A (genuine future-vocabulary leak) still blocked:
      - Driver first observed Jan 2026 → registry_visible_at = Jan 2026
      - 2024 backfill: Jan 2026 <= Q1 2024 → FALSE → hidden. ✓

  Wall-clock fields (Driver.created_at, deprecated_at) remain for AUDIT only — NEVER
  used for PIT visibility.

  Why this matters: without the filter, a historical backfill (per Final.md §22
  "historical prediction/learning catch-up") would expose the LLM to vocabulary
  that didn't exist at the simulated point in time → biased reasoning + PIT leak
  via vocabulary suggestion. Filter cost is trivial — single Cypher WHERE clause
  on the catalog query, gated by Driver.registry_visible_at (REQUIRED PIT field —
  NOT wall-clock created_at).

DriverChange records — Phase 1 producer: LEARNER ONLY per E30:
  - source_type="learner_result"  ← from learner's primary_driver + contributing_factors[]
                                    (post-outcome attribution with hindsight)
  Predictor is CONSUMER ONLY in Phase 1 — does NOT emit DriverChange rows. Predictor's
  prediction/result.json §7 key_drivers[] stays free-form analysis prose per E21 amended
  by E30. The pre-E30 "symmetric producer treatment" + EV1 bet-vs-attribution comparison
  is superseded; forensic record preserved in "ChatGPT corrections" R1/R8 ledger above +
  CombinedPlan §5 [E30].
```

## Phase 2 — News drivers (LATER; full extraction pipeline)

```
Trigger:        Refactor guidance_trigger_daemon to be type-generic
                OR create new news_trigger_daemon.py
Code work:      .claude/skills/extract/types/driver/
                  core-contract.md, primary-pass.md, driver-queries.md
                  assets/news-primary.md
LLM cost:       1 extraction session per significant news event
Schema work:    ZERO (Driver/DriverChange already exist from Phase 1)
Writer reuse:   driver_writer.py + driver_write_cli.py (built in Phase 1) used as-is
```

## Phase 3 — Fiscal.ai drivers (LATER; optional)

```
Option A: Direct ingest (no LLM) — for each fiscal.ai KPI label, route through
          the SAME `driver_write_cli` pipeline as LLM proposals (per CombinedPlan
          E13) — canonicalize() consults the registry, applies all R1-R11 rules,
          and either reuses an existing Driver, registers a new one via
          propose_new_drivers[], or rejects to `:DriverProposalRejection`:
          - MERGE a Driver entry (canonical fields only: name/label/aliases/
            allowed_states — NO source_type or raw_label on the Driver itself;
            NO validation_status per E2/OQ1 — all registered drivers are reusable).
            Registration happens ONLY if canonicalize() does not reject.
          - MERGE a DriverChange entry carrying:
              source_type="fiscal_kpi"          ← provenance lives HERE (per R7 #3)
              raw_label="<exact fiscal.ai label>" ← preserved verbatim on the CHANGE
              source_id="fiscal:{ticker}:{quarter_label}:{kpi_slug}"
              result_path or fiscal.ai row pointer
          Driver registry stays canonical; per-mention provider provenance stays
          on the occurrence record.
Option B: Full pipeline with asset=fiscal_kpi — canonicalization via LLM.
          Same node split: Driver = canonical (no source_type/raw_label);
          DriverChange = per-occurrence (carries source_type + raw_label).
Schema work:    ZERO
```

---

# Realistic XBRL Coverage (no overpromise — per ChatGPT R2 #5)

```
Driver linkage bucket            xbrl_qname rate    concept_family rate
─────────────────────────────────────────────────────────────────────
Financial (revenue_trend,...)     ~50-70%            ~70-85%
Segment-specific financial        ~30-50%            ~50-70%
Macro / news / positioning        0% by design       0% by design   ← correct behavior
─────────────────────────────────────────────────────────────────────
Aggregate                         ~20-30%            ~35-45%
```

XBRL linkage is a NICE-TO-HAVE bridge for financial drivers. Macro/news/positioning drivers null by design — that's not a coverage gap, it's correct behavior.

# Peer Retrieval — Design (per R16: permanent rule, no fuzzy matching)

```
Peer retrieval is EXACT driver_id match across tickers — full stop.
  Example: AAPL prior report tagged driver:iphone_china_sales
           → matches AAPL future report with same driver_id (own-report retrieval)
           → does NOT match MSFT/SSNLF reports (no overlap on driver_id)

Same-driver cross-ticker peers DO match (e.g., driver:gross_margin appears on
  multiple tickers' reports — exact match works).

EXPLICITLY REJECTED (now and permanently — per R16 user directive):
  - Fuzzy peer matching across DIFFERENT but related driver_ids.
    Example: driver:iphone_china_sales vs driver:samsung_china_sales — both
    involve smartphone-in-china but they are SEPARATE drivers. They will
    NEVER be matched as peers by the driver registry.
  - Embedding-similarity matching AS A PEER-MATCH / EQUALITY DECISION. (Embedding
    similarity MAY be used elsewhere as a TRIGGER ONLY -- a PIT-filtered top-K search
    that flags a near-duplicate for an isolated judge to rule on; it never decides
    driver equality, never auto-rejects, and never relaxes this exact-driver_id peer
    rule.)
  - Facet-overlap matching (retrieval_keys / segment_components etc.).

Cross-product peer relevance (e.g. iphone_china_sales ↔ samsung_china_sales)
is handled at the PREDICTOR layer via Final.md §6 industry+mkt_cap ranking —
NOT at the Driver registry layer. The Driver registry stays a precise,
deterministic ontology; matching stays exact-equality. This is the design,
not a limitation to be lifted.
```

---

# Re-Run / PIT Safety (per ChatGPT R2 #4)

```
Scenario:  Learner re-runs (revised transcript arrives, agent reruns)
           Same source_id (formula "learner:{ticker}:{quarter_label}" is stable across re-runs)

MERGE behavior on DriverChange node:
  ON CREATE SET: all properties initialized; supersession fields = null (authoritative).
  ON MATCH SET allowlist (per ChatGPT R3 #5 — hardening + R15 #1 supersession):
    ✓ written_at             — always updates on re-run
    ✓ evidence_refs          — ADDITIVE merge (union of old + new, never replace)
    ✓ superseded_at          — set when a re-run drops this DC; cleared if reappears
    ✓ superseded_pit_cutoff  — set to revising run's pit_cutoff; cleared on un-supersede
    ✓ superseded_by_run_id   — set to revising run id; cleared on un-supersede
    ✗ pit_cutoff             — NEVER updates (frozen at ON CREATE — PIT visibility,
                                per Final.md §9 vocabulary)
    ✗ authored_at            — NEVER updates (frozen at ON CREATE — first-write wall-clock)
    ✗ source_id              — NEVER updates (slot-bound)
    ✗ driver_id              — NEVER updates (FK)
    ✗ driver_state           — NEVER updates (slot-bound → state change = new node)
    ✗ result_path            — NEVER updates (source identity)

MERGE behavior on FOR_COMPANY edge:
  ON CREATE SET: direction, exposure_role.
  ON MATCH UPDATE: direction MAY change on legitimate revision (e.g., new evidence
    flips the call). BUT every direction change is LOGGED to a separate
    `:DriverDriftAudit` node with {dc_id, ticker, old_direction, new_direction,
    revision_ts, reason?}. This gives full audit trail without paying the storage
    cost of immutable per-revision DriverChange nodes.

PIT query (per R15 #1 — extended with supersession check):
  Historical run:
    WHERE dc.pit_cutoff <= predictor.pit_cutoff
      AND (dc.superseded_pit_cutoff IS NULL
           OR dc.superseded_pit_cutoff > predictor.pit_cutoff)
    — first clause: DC was visible by time T
    — second clause: DC was not yet superseded as of time T
    Together: returns the AUTHORITATIVE driver set as-of T.

  Live run (predictor.pit_cutoff IS NULL per Final.md): skip the PIT time filter,
    but still require superseded_pit_cutoff IS NULL. Live predictor has no PIT
    restriction, but it should only see currently-authoritative DCs.
    (Per R13 #3 + R15 #1.)

Outcome:
  - Drivers from ORIGINAL learner run:  pit_cutoff = T1.  Visible at predictor T ≥ T1.
  - NEW drivers added in REVISION:       pit_cutoff = T2.  Only visible at predictor T ≥ T2.
                                         OLD predictors do NOT see these.    ✓ PIT safe
  - DROPPED drivers in REVISION         superseded_pit_cutoff = T2.
    (per R15 #1):                        Visible at predictor T < T2 (was authoritative
                                         then); HIDDEN at predictor T ≥ T2.    ✓ PIT safe
                                         Audit trail preserved — never deleted.
  - REVISED direction on existing DC:    edge direction reflects the latest call;
                                         drift_audit log preserves history for analysis.

Accepted limitation:
  A predictor at T_old that already ran cannot re-derive what edge direction it ACTUALLY
  saw at T_old without consulting drift_audit. This is fine: predictions are immutable
  once written; drift_audit + the supersession fields preserve a complete audit trail
  for hindsight analysis. No per-revision-immutable DriverChange scheme planned.
```

---

# Final.md Changes Required (when implementing)

```
§7 key_drivers[i] (PREDICTOR — REMAINS FREE-FORM per E21 amended by E30):
  NO schema migration. Predictor is consumer-only in Phase 1; §7 key_drivers[]
  stays as free-form analysis prose ({driver, direction, evidence}); §7 line
  "no controlled vocabulary/tags" STANDS. Only §8 (learner) below migrates to
  canonical-form discipline. Predictor bundle DOES render Driver Registry
  Catalog block but READ-ONLY (M1 reuse for §7 prose authoring + prior_reports
  relevance ranking — never written back to registry per E30).

§8 primary_driver, contributing_factors[i] shape:
  before:  { driver / factor, evidence }
  after:   { driver_name, driver_state, direction, evidence }

§9 PIT fence:
  Add bullet:  DriverChange.pit_cutoff carries the source's logical PIT boundary
  (always concrete — never null, per R10 #4 + R11 #2):
    - source_type="learner_result"    → learner_result.pit_cutoff
    - source_type="prediction_result" → historical: predictor bundle pit_cutoff (= filed_8k)
                                        live:       authored_at (wall-clock at write)
    - source_type="news"              → news.created
    - source_type="fiscal_kpi"        → filing.filed timestamp
  Visibility predicate (matches Final.md §9 line 182, extended with supersession
  per R15 #1):
    Historical run:
      `dc.pit_cutoff <= consuming_predictor.pit_cutoff
        AND (dc.superseded_pit_cutoff IS NULL
             OR dc.superseded_pit_cutoff > consuming_predictor.pit_cutoff)`
    Live run (consuming_predictor.pit_cutoff IS NULL per Final.md): skip the PIT
    time filter, but still require superseded_pit_cutoff IS NULL. Live predictor
    has no PIT restriction (per R13 #3), but it should only see currently-
    authoritative DCs (per R15 #1).
  authored_at + written_at are audit-only, NEVER used for visibility (except as the
  concrete fallback for live prediction_result in the forensic formula above — not
  emitted in Phase 1 per E30 + v7-3).

§11 prior_reports_context (PREDICTOR bundle):
  Add bullet:  prior_report_row entries now include `driver_tags[]` — the canonical
  driver_name + driver_state values from each prior learner_result. Predictor uses
  these for relevance-ranking when deciding which prior reports to open.
  (driver_tags are SUMMARIES of prior drivers for retrieval — NOT the registry itself.)

LEARNER bundle (separate from §11 — clarified per ChatGPT R4 #3):
  Add bullet:  earnings-learner bundle renderer adds a Driver Registry Catalog block
  before the learner authors drivers. Block contains: existing Driver.id + label +
  allowed_states + base_label/segment. Equivalent to guidance's query 7A render.
  This is the M1 reuse surface — learner searches before proposing new drivers.

§15 cause families:
  No change. Stays as PROMPT LENS for whole-move attribution thinking. The Driver
  registry is the SCHEMA; §15 families are still the thinking framework.

§17 code anchors:
  Add anchors: scripts/earnings/builders/driver_{ids,writer,write_cli,concept_resolver}.py
  Reference: GuidanceExtractionImplemented.md as the methodology source

NEW §24 Driver Ontology:
  One-paragraph pointer to .claude/plans/Drivers/Neo4jXBRLDesign.md
  as the source-of-truth canonical design (per ChatGPT R4 #2 — path corrected from
  prior stale DriversList.md reference).
  Companion file: .claude/plans/Drivers/ConceptualRequirements.md
  (origin requirements + reasoning history; non-canonical).
```

---

# Open Items (not blocking v1)

```
1.  ~~Driver registry SEED — OPTIONAL bootstrap. Cleanest default: start empty;
    grow organically. Alternative: pre-seed ~20-30 common drivers manually. Pick
    before first Phase 1 production run.~~
    **RESOLVED per E9 + OQ4 = HARDCODED CONSTANT**: bootstrap-seeded via a
    `COLD_START_SEED_DRIVERS = [...]` Python constant in `driver_writer.py`
    (NOT a human curator per L4; code-time constant is normal engineering,
    deterministic, inspectable, no runtime LLM dependency). PIT policy per E9:
    timeless-only epoch for macro/regulatory drivers; per-driver date for
    modern drivers — modern drivers excluded from seed unless dated. Existing
    guidance metric labels MAY seed the financial sliver per OQ4.

2.  ~~State vocabulary closed list — start with verbs grouped by class:
      financial_outcome:  beat, miss, inline, raised, lowered, reaffirmed, withdrawn
      quantity_move:      built, cleared, expanded, contracted, exhausted
      policy_action:      imposed, eased, lifted, restricted, approved, denied
      rate_curve:         steepened, flattened, inverted, normalized
      event_lifecycle:    announced, initiated, completed, cancelled, delayed
      trend_motion:       accelerated, decelerated, stable, declined, expanded, compressed
      absence:            absent, unchanged, pending
    Each Driver carries its own allowed_states subset.
    New states require human review.~~
    **RESOLVED per E8** (Round 5 + Round 6 P2): full canonical `STATES_VOCAB`
    enumerated across 7 classes in `DriverOntology_Implementation.md` §F.5.
    Key corrections vs the legacy list above: (a) base forms are past-tense
    (`missed`/`raised`/`lowered`), with `miss`/`raise`/`lower` mapped via the
    banned-alias map (not as base forms); (b) `absence` class REMOVED (was not
    a real driver-state class); (c) `declined` kept distinct from `deteriorated`
    (trend_motion vs sentiment_motion). Each Driver carries its own
    `allowed_states` subset (drawn from one class). New states added via
    code-time constant edit (no runtime curator per L4).

3.  ~~Validation status promotion criterion — mechanical (≥N observations consistent across
    sources) or human-curated. Decide before first Phase-1 production run.~~
    **RESOLVED per E2 + OQ1=DROP**: `validation_status` field dropped from Driver schema
    entirely. All registered drivers are reusable (L4 — no human curator at runtime,
    no promotion gate). Per E27 Pattern A2 N=2 promotion gate applies to
    `:EquivalenceToken` only (synonyms/plurals/acronyms transforms), NOT to Drivers
    themselves. Driver promotion threshold question is permanently moot.

4.  Driver registry STORAGE location — Neo4j primary; JSON snapshot to
    earnings-analysis/drivers/registry.json for prompt rendering at bundle-build time.

5.  Peer-retrieval ranking by driver overlap — defer until registry has enough entries
    (Phase 2+). Until then, use existing industry+mkt_cap ranking from §6 of Final.md.

6.  EV1 per-driver_axis aggregation — defer. First ship driver capture, then add
    aggregation in scoring/ev1.py after enough data accumulates.

7.  Property-drift across re-runs — drift_audit log + supersession fields cover the
    audit need. No further property-history tracking planned.
```

---

# Locked

```
Architecture:           BORROWED guidance ontology PATTERN + machinery
Driver registry:        SEPARATE ontology, separate node types, separate identity rules
LLM cost (Phase 1):     ZERO additional vs current
ChatGPT corrections:    Refined across 16+ review rounds. 19 of 20 R1-R4 architectural
                        decisions accepted (only R1 direction-rename rejected). All
                        subsequent rounds focused on propagation, consistency, and
                        scope cleanup:
                          R5-R7:  wording propagation + polish (10+ small fixes)
                          R8:     PIT field semantics + Fuller v1 (predictor as producer
                                  — scope LATER reduced by E30 to consumer-only;
                                   §7 key_drivers stays free-form)
                          R9-R10: propagation + 5 spec fixes (delimiter, contracts, PIT filter)
                          R11:    5 final-pass fixes (registry_visible_at, etc.)
                          R12-R14: self-audit + propagation cleanup (10+ fixes)
                          R15:    SUPERSESSION fields added — handles re-runs that
                                  drop drivers (real design hole missed in prior audits)
                          R16:    SCOPE CLEANUP — "only v1, no v2" + permanent NO to
                                  fuzzy matching. Removed magnitude, triggerable, level,
                                  effective_from, evhash16 from spec.
Independent design:     specificity-first naming, state-out-of-name discipline,
                        PIT-safe re-run semantics, edge-based direction with drift audit,
                        ON MATCH allowlist hardening, completion-before-sentinel ingest,
                        optional XBRL bridge, 3-component DC slot, file-source DC props,
                        deterministic source_id formulas, learner-vs-predictor render split,
                        supersession of dropped drivers (R15 #1), no-fuzzy-matching
                        permanent rule (R16)
Next step:              Implementation order (per ChatGPT R11 #5 + R12 #5 reorder —
                        schema FIRST so the writer + seed have constraints to bind to):
                        1. Neo4j schema                       — Driver + DriverChange
                                                                constraints + indexes
                                                                (constraint queries can be
                                                                inline in driver_writer.py's
                                                                create_driver_constraints(),
                                                                mirroring guidance pattern;
                                                                listed first for clarity)
                        2. scripts/earnings/builders/driver_ids.py            (slug, slot ID,
                                                                                source_key sanitization)
                        3. scripts/earnings/builders/driver_concept_resolver.py
                        4. scripts/earnings/builders/driver_writer.py         (MERGE Driver +
                                                                                DriverChange;
                                                                                registry_visible_at
                                                                                MIN-update logic;
                                                                                supersession ON MATCH
                                                                                SET for dropped DCs
                                                                                per R15 #1;
                                                                                drift_audit edge writes)
                        5. scripts/earnings/builders/driver_write_cli.py      (orchestrator
                                                                                interface;
                                                                                proposal validator;
                                                                                compute current-emitted
                                                                                dc_id set vs prior set
                                                                                for supersession)
                        6. Driver registry seed                — `COLD_START_SEED_DRIVERS`
                                                                hardcoded Python constant in
                                                                `driver_writer.py` (per E9
                                                                + OQ4 — NOT curator-curated;
                                                                code-time constant; PIT policy
                                                                = timeless-only epoch for
                                                                macro/regulatory, per-driver
                                                                date for modern; per
                                                                Open Items #1 RESOLVED).
                        7. earnings-learner/SKILL.md           — emit canonical drivers
                                                                (sole Phase-1 producer per E30)
                        8. earnings-prediction/SKILL.md       — NO canonical-emit step in
                                                                Phase 1 (per E30 — predictor
                                                                is consumer-only; §7
                                                                key_drivers[] stays
                                                                free-form). Bundle render
                                                                adds Driver Registry Catalog
                                                                READ-ONLY for §7 prose
                                                                authoring + prior_reports
                                                                relevance ranking.
                        9. Bundle renderer                    — Driver Registry Catalog block
                                                                with registry_visible_at filter
                       10. validate_learning.py               — driver_name resolves OR
                                                                propose_new_drivers[] supplied.
                                                                (NO validate_prediction_result
                                                                 driver-emission validation per
                                                                 E30 — predictor is consumer-only;
                                                                 §7 key_drivers[] stays free-form
                                                                 and is NOT validated for canonical
                                                                 driver names.)
                       11. Final.md updates                   — §8 schema migration only
                                                                (live {summary, category, evidence_refs}
                                                                 per validate_learning.py v3 →
                                                                 {driver_name, driver_state,
                                                                  direction, evidence_refs}); §7 STAYS
                                                                free-form per E30 + E21 amendment;
                                                                §9 pit_cutoff bullet + §11
                                                                driver_tags[] bullet + new §24
                                                                pointer to this doc
```
