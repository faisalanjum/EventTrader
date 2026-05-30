# BEST WAY — Driver CREATION Layer (the minimal, near-100%-reliable plan)

> Scope: this plan covers ONLY **driver creation** — turning evidence into a clean, canonical,
> validated driver name + its companion fields, BEFORE anything is written to Neo4j.
> Everything that writes to the database (MERGE, point-in-time fields, dedupe, supersession,
> token-promotion, audit logs) is **ingestion** and is delegated, unchanged, to the existing
> guidance pipeline. We only check the handoff is clean.

---

## 1. TL;DR (plain English, crux first)

We are building one thing: a small, deterministic name-cleaner. The learner LLM proposes a
driver name from earnings evidence; our cleaner turns it into the one true canonical form (or
rejects it for a stated reason), checks the companion fields, and emits a plain JSON packet.
A copy of the existing **guidance writer** takes that packet and does all the database work — we
write almost no new storage code.

The crux: **accuracy is highest when the machine, not the LLM, decides the final name.** Where a
fixed dictionary + fixed slot order can decide, we hit ~100% and we never write a wrong name (bad
input is rejected, not guessed). Where the choice needs human-style judgment (is this token a
*theme* or an *object*? is this evidence really about *China*?), we cap at LLM quality (~85%) and
contain the damage with a deterministic gate + one retry + reject-don't-guess.

Three things in the current big plan are **not yet real and block the near-100% goal**: (1) the
three core functions that decide a token's slot are *named but never written* — so two engineers
could build different name-deciders; (2) the actual prompt that teaches the learner the new format
*does not exist yet* — the live skill still emits the old `{summary, category}` shape; (3) the plan
folds a lot of database-only machinery (token-promotion store, point-in-time backdating, 5 audit
tables) into the "creation" budget — that is ingestion and should be cut from this layer.

Fix those three and the creation layer is done. The honest accuracy bar is **>90% enforced,
~96-98% is an unmeasured projection** — say so, don't sell the projection as a result.

---

## 2. THE BOUNDARY — CREATION (build) vs INGESTION (delegate)

The clean cut is a single JSON packet. Creation produces it; a guidance-style writer consumes it
and owns everything downstream. Nothing in creation reads writer/MERGE internals.

```
   LLM evidence                                         Neo4j
       │                                                  ▲
       ▼                                                  │
┌──────────────────────┐   input JSON packet   ┌──────────────────────┐
│  CREATION (we build) │ ───────────────────►  │  INGESTION (delegate)│
│  pure, no DB writes  │   (the ONLY seam)     │  = guidance writer    │
└──────────────────────┘                       └──────────────────────┘
       ▲   reads through 2 narrow read-paths (vocab snapshot, registry catalog)
       └───────────────────────────────────────────────┘
```

| Concern | CREATION (build new) | INGESTION (delegate to guidance reuse) |
|---|---|---|
| Decide the canonical name | ✅ `canonicalize()` pure fn | — |
| Decide a token's slot | ✅ `classify_token()` / `order_by_slot()` | — |
| Reject bad names with a reason | ✅ shape/banned/state/metric/length gates | — |
| New-token gate (R11) + validators V1–V14 | ✅ | — |
| Companion fields (state, direction, segment, label, aliases, definition, allowed_states) | ✅ author + validate | — |
| Emit the input-JSON packet | ✅ | — |
| Read vocab snapshot (synonym/plural/acronym maps, slot vocabs, shortcuts) | ✅ READ only, point-in-time filtered | writer WRITES the tokens |
| Read registry catalog (existing Driver names/aliases) for reuse-before-create | ✅ READ only, point-in-time filtered | writer WRITES the Drivers |
| MERGE / UNIQUE constraints / `Driver.registry_visible_at` | — | ✅ guidance `guidance_writer.py` + constraints |
| Token promotion store (`:EquivalenceToken`, N=2 gate, two-phase Cypher) | — | ✅ guidance writer (Phase 2+) |
| `:VocabToken` store + `vocab_visible_at` backdating | — | ✅ guidance writer |
| Supersession / `superseded_*` triplets | — | ✅ guidance writer pattern |
| 5 audit/telemetry labels | — | ✅ deferred (sidecar JSON covers day-1) |
| Concurrency / race / out-of-order PIT backdate | — | ✅ guidance writer |

### The handoff contract (the exact JSON creation emits)

Verified live at `DriverOntology_Implementation.md:545-582`. This is the clean cut. Keep it
**source-agnostic** but swap the two guidance-specific pieces (do NOT copy them):

```jsonc
{
  "source_id":      "AAPL_2025-07-31T17.00.00-04.00",
  "source_type":    "learner_result",     // enum {learner_result, news, fiscal_kpi}
                                           //  — DISJOINT from guidance {8k,10q,...};
                                           //    REPLACE guidance enum, don't inherit
  "pit_cutoff":     "2025-07-31T17:00:00-04:00",
  "run_id":         "...",
  "source_catalog": ["SRC:8K:...", "SRC:TR:..."],  // for V10 evidence resolution
  "items": [
    { "ticker": "AAPL", "driver_name": "iphone_china_sales",
      "driver_state": "missed", "direction": "short",
      "evidence": ["SRC:8K:..."] }
  ],
  "propose_new_drivers": [
    { "name": "iphone_china_sales", "label": "iPhone China Sales",
      "base_label": "Sales", "segment": "China",
      "definition": "Revenue from iPhone sales in the China region.",
      "allowed_states": ["beat","missed","inline"], "aliases": ["china_iphone_sales"],
      "is_shortcut": false }
  ]
}
```

**Two contract rules that protect the clean cut** (verified, both must hold):
- Do **NOT** inherit guidance's `REQUIRED_ITEM_FIELDS` (`period_u_id`, `quote`, `given_date` —
  `guidance_writer.py:52-56`). The driver `items[]` shape above is correct and self-contained.
- Replace, don't copy, the `source_type` enum (`guidance_writer.py:42-48`).

---

## 3. MINIMAL CREATION COMPONENTS (smallest buildable set)

Build only these. "Mirrors" = the verified-real guidance code it can borrow from (per reuse_map).

| # | Component | 1-line purpose | LOC | Mirrors (verified) |
|---|---|---|---|---|
| C1 | **Ontology doc the LLM sees** (`DriverOntology.md` + §A author envelope) | Teach the producer the rules R1–R11 + the format | doc | none (net-new teaching) |
| C2 | **`slug()`** | text → lowercase underscore slug | ~6 | `guidance_ids.py:21` **verbatim** ✅ |
| C3 | **`canonicalize(candidate, vocab)`** | the 12-step name-cleaner (pure, no DB) | ~200 | net-new; word "canonicalize" only — guidance's operate on units/values, NOT names |
| C4 | **`classify_token(token, slot_vocabs)`** | put one token in exactly one slot, fixed precedence | ~40 | net-new |
| C5 | **`order_by_slot()` + `effective_slot_count()`** | reorder to canonical slot order; count slots for length bound | ~30 | net-new |
| C6 | **`SHAPE_REGEX` + grammar (BNF)** | the legal name shape + slot grammar | ~10 | net-new |
| C7 | **Gates inside C3**: shape, multi-token sub, stopword, banned, state-in-name, standalone-shortcut, new-token (R11), metric-presence, length | reject-don't-guess; every reject has a reason code | (in C3) | net-new |
| C8 | **Validators V1–V14** | companion-field + emission cross-checks | ~120 | net-new (V15 is a registry/dedupe check → ingestion) |
| C9 | **Vocab banks (static seed)** §F.1–F.9 | synonym/plural/acronym maps, slot vocabs, shortcuts, banned, stopwords, states, compound-metrics, allowed-verbal-forms | data | net-new data |
| C10 | **`load_vocab_snapshot(pit)`** READ path | build the frozen `VocabSnapshot` = static seed + PIT-filtered Neo4j tokens | ~40 | shape mirrors guidance bundle-render query (NOT `warmup_cache`) |
| C11 | **Registry catalog READ** (reuse-before-create) | PIT-filtered existing Driver names/aliases for the LLM + B-cascade | ~30 | mirror guidance inventory query 7A *shape only* (add aliases/segment/states + `registry_visible_at` filter) |
| C12 | **Emission contract / author prompt** (`earnings-learner/SKILL.md`) | tell the learner to emit `{driver_name, driver_state, direction, evidence}` + `propose_new_drivers[]` + worked examples | doc (~75–150 LOC) | net-new — **currently emits old `{summary, category}` shape** |
| C13 | **Cold-start seed** `COLD_START_SEED_DRIVERS` | ~32 timeless anchors so the first runs have slots to match against | data (~32 rows) | net-new data |

**Build order:** C9/C13 (data) → C6/C2 → C4/C5 → C3+C7 → C8 → C10/C11 (read paths) → C12 (prompt) → C1 (doc).
The pure functions (C2–C8) have zero DB dependency and can be unit-tested in isolation before any
Neo4j exists. C10/C11 are the only two functions that touch Neo4j, and **read-only**.

---

## 4. DELTA vs current CombinedPlan

| CUT (over-engineered / ingestion-leak / premature) | KEEP (essential) | ADD (missing requirement coverage) |
|---|---|---|
| **`:EquivalenceToken` runtime store + N=2 gate + two-phase Cypher** out of creation scope — keep only the static §F.2/F.3/F.4 maps + the promoted-rows READ. *(MIN-1, MIN-2)* | The pure `canonicalize()` 12-step pipeline `DriverOntology_Implementation.md:118-181` *(verified, sound)* | **Write `classify_token()` as real code** — pure dict lookup with explicit precedence theme>object>customer>geography>institution>metric; today only *called* (`:166`) never *defined*. *(COV-1)* |
| **`vocab_visible_at` / `equivalence_visible_at` MIN-on-MATCH backdate compute** → ingestion; keep only the READ filters `:192-193,201-202,210-211`. *(MIN-3)* | The static vocab banks §F.1–F.9 `:296-441` and cold-start seed *(verified present)* | **Write `order_by_slot()` + `effective_slot_count()`** — also called-never-defined `:169,:174`. *(COV-1)* |
| **5 audit/telemetry labels** (`:DriverAutoRepair`, `:DriverProposalRejection`, `:EquivalenceConflictAudit`, `:EquivalenceCollisionAudit`, `:DriverDriftAudit`) — pure observability; sidecar JSON `:584` covers day-1. *(MIN-4)* | The new-token gate R11 `:258-264` + grammar/BNF `:242-256` *(verified)* | **Specify the multi-anchor unknown-token rule**: "an unknown token's slot is the unique SLOT_ORDER position strictly between its nearest known left/right neighbors; if 0 or >1 slot fits → REJECT `slot_ambiguous`." Today prose-only (`§D(c)`), not code-checkable. *(COV-1)* |
| **Lever #1 auto-repair (`repair_and_retry`) + its `:DriverAutoRepair` label** — traces to no requirement; its recovery overlaps Lever #3; bad names should just deterministically reject. *(MIN-5)* | Validators V1–V14 `:272-287` *(verified)* | **Wire the slot-conflict tiebreaker into `classify_token`** (R3 "earlier slot wins") OR add a build-time validator rejecting any seed/token in >1 slot_vocab. Today it rests on Python dict iteration order — self-labeled "Real correctness gap." *(COV-2)* |
| **Lever #2 (`write_equivalence_tokens`) + N=2 promotion lifecycle** → Phase 2 (no second producer exists in Phase 1; a new synonym is a code-time map edit per `§I`). *(MIN-2)* | The E16 input-JSON contract `:545-582` — the clean cut *(verified)* | **Migrate `earnings-learner/SKILL.md` off `{summary, category}`** (live at `SKILL.md:53-54`) to `{driver_name, driver_state, direction, evidence}`; drop `category` (collides with the no-category deferral). Treat the author prompt as a first-class reviewable artifact, NOT a LOC line-item. *(COV-5)* |
| **The `~96-98% accuracy` headline** (`CombinedPlan.md:883`) — unmeasured projection presented as result; the enforced bar is `>90%` (`:35`). *(COV-6, MIN-6, REL-8)* | `slug()` verbatim reuse `guidance_ids.py:21` *(verified)* | **Add a materialized R3 risk → enforcing-clause matrix** (dedupe the 4 overlapping taxonomies into one counted set first), OR mark "R3 100% covered" as ASSERTED-NOT-VERIFIED. Condition-2 is unmet for R3 until this exists. *(COV-3)* |
| **`driver_concept_resolver.py` member-map machinery** — guidance segment→XBRL-Member linking has NO driver equivalent; strip it. Keep only the financial base_label sliver. *(CON-8)* | The PIT-filtered READ paths C10/C11 (vocab snapshot + registry catalog) *(verified design)* | **Add an explicit deferral block** naming the semantic risks no Python can catch — *mechanism-collision* (`DriverNameRisks.md:369`), *wrong-discriminator* (`:387`), *alias-undermatch* (`:411`), *reuse-failure* (`:415`) — routed to prompt-teaching + the one retry. Add a scope/segment sanity surface on the B3–B8 reuse cascade so wrong-existing-driver reuse isn't silently unguarded. *(COV-4)* |
| **Fictional `guidance_change_id()` row** in the Mirror Map (`:624`) — function does not exist; real builder is `build_guidance_ids()` (`guidance_ids.py:814`). Fix or delete. *(CON-3, MIN-6)* | | **Teach the metric-mandatory rule in the ontology the LLM sees** (R3/R9): "a non-shortcut name MUST contain a metric slot; an object/geography without a metric is a deterministic rejection." Today canonicalize enforces it (`:172`) but the prompt under-teaches it → silent rejections. *(COV-7)* |
| | | **Fix internal consistency nits** so the plan is buildable from one source of truth: F.9 vs step-7 state conflict on `restricted`/`accumulated` (CON-1); new-token gate range omits §F.6 compound-metrics (CON-2); SKILL.md LOC 75-vs-150 changelog mismatch (CON-4); §8-vs-Appendix-A per-file LOC divergence (CON-5); accuracy threshold 95-vs-90 across 3 spots (CON-6). |

---

## 5. RELIABILITY LEDGER — where 100% is real vs where it caps at LLM judgment

| Creation step | Type | Fail-closed behavior | Reaches ~100%? |
|---|---|---|---|
| Shape gate (`SHAPE_REGEX`) | MECHANICAL | reject `REJECTION_INVALID_SLUG_SHAPE` | ✅ yes |
| Multi-token sub + stopword strip + dedupe | MECHANICAL | reject if empty after strip/dedupe | ✅ yes |
| Per-token normalization (synonym/plural/acronym) | MECHANICAL | exact-match dict lookup; miss = token unchanged | ✅ yes (given disjoint maps — see REL-9) |
| Banned-content gate (R7, 13 categories) | MECHANICAL | reject `REJECTION_BANNED_TOKEN` | ✅ yes |
| State-in-name gate | MECHANICAL | reject `REJECTION_STATE_IN_NAME` | ✅ yes |
| Standalone-shortcut match (R5) | MECHANICAL | exact-set membership | ✅ yes |
| Metric-presence + length bound (R8) | MECHANICAL | reject `REJECTION_NO_METRIC_TOKEN` / `REJECTION_TOO_MANY_SLOTS` | ✅ yes |
| Reorder to canonical slot order (R3) | MECHANICAL (once C4/C5 specified) | deterministic given slot map | ✅ yes **after COV-1/COV-2 fixed** |
| Reuse-before-create exact/alias/sorted-token match (R1, B3–B8) | MECHANICAL | exact lookup | ✅ for *exact* match |
| New-token slot inference (multi-anchor) | MECHANICAL **only after the COV-1 rule is specified**; otherwise UNDERSPECIFIED | reject `slot_ambiguous` / `slot_anchor_unavailable` | ⚠️ yes *iff* the between-anchors rule is written |
| **Which slot a novel token *really* is** (theme vs object vs customer) | **LLM-JUDGMENT** | gate + one retry; if still ambiguous → reject, never guess | ❌ caps at ~85%; contained |
| **Is the evidence really about this discriminator** (China vs customer-type) | **LLM-JUDGMENT** | prompt-teaching + reject-don't-bundle (R2/R9) | ❌ caps at ~85%; contained |
| **Reuse the *right* existing driver** (scope fit) | **LLM-JUDGMENT** | prompt + scope/segment surfacing on B3–B8 *(ADD per COV-4)* | ❌ caps; contained |
| Companion-field validators V1–V14 | MECHANICAL | per-validator rejection reason | ✅ yes |
| Emit input-JSON packet | MECHANICAL | schema-shaped; sidecar records outcomes | ✅ yes |

**The reliability story in one line:** the *mechanically-guaranteed floor* is "**no wrong driver is
ever written**" — every name the machine cannot deterministically resolve is REJECTED, not guessed.
The gap from that floor up to ~96-98% is **entirely LLM-bounded** (capped ~85% per
`CombinedPlan.md:25`) and **unvalidated until Q1**. State any >90% claim as *contingent* on landing
C3–C5 (the deterministic classifier) — they are named-but-unwritten today *(REL-8)*.

---

## 6. RESIDUAL RISKS + OPEN DECISIONS (only what the user must decide)

**Residual risks (cannot be closed by code):**
- Slot mis-classification for early **object/customer/theme** tokens — the cold-start seed
  deliberately covers only ~32 timeless anchors, NOT objects/customers/themes
  (`CombinedPlan.md:177`), so the first ~3–5 novel proposals carry the most drift risk.
- Semantic-judgment failures (mechanism-collision, wrong-discriminator, alias-undermatch,
  reuse-failure) depend on evidence attribution no Python check can make; contained by prompt +
  one retry + reject-don't-guess, not eliminated.
- Cross-kind vocab collision is *latent only* today (the seed maps are disjoint by inspection,
  `:326-373`); it becomes real only if runtime token promotion is later enabled. Add a snapshot
  build-time disjointness assertion as cheap insurance *(REL-9)*.

**Open decisions for the user (only you can answer):**
1. **R3 coverage proof:** do you want a materialized risk→clause matrix built (closes Condition-2
   for R3 cleanly), or is "ASSERTED-NOT-VERIFIED, R2's R1–R11 span the risk space" acceptable for
   go/no-go? *(COV-3)*
2. **Accuracy bar language:** confirm we publish **>90% enforced; ~96-98% = unmeasured projection
   pending Q1** everywhere (kills the overstatement). Agree to drop the headline?
3. **Day-0 precondition:** the SKILL.md migration off `{summary, category}` is a blocker for the
   whole layer — confirm it ships first (it touches the live producer artifact). *(COV-5)*
4. **Defer Levers #1/#2 + audit tables + equivalence store to Phase 2?** This is the big
   minimalism cut; it removes the most code with no Phase-1 requirement lost. Confirm.
5. **B3–B8 reuse scope-fit surfacing:** add the lightweight segment/scope sanity check (reduces
   wrong-driver reuse), or accept it as a prompt-only concern? *(COV-4)*

---

## 7. VERDICT

**GAPS_REMAIN** — the design is architecturally sound (clean cut at the E16 packet; `canonicalize()`
is a verified pure function with no DB reads; vocab banks and seed exist), but it is **not yet
spec-complete against the three hard conditions**:

Blocking gaps:
1. **Condition 1 (~100% accuracy) is unmet in mechanism:** `classify_token()`, `order_by_slot()`,
   `effective_slot_count()` are *called but never defined* (`DriverOntology_Implementation.md:166,169,174`;
   zero `def` anywhere). The multi-anchor unknown-token rule is prose-only. Until these are real
   code with the explicit between-anchors precedence, the deterministic core that delivers the
   accuracy is not buildable two-engineers-the-same-way. *(COV-1, COV-2, REL-8)*
2. **Condition 1 (the make-or-break teaching artifact) does not exist:** the live producer
   `earnings-learner/SKILL.md:53-54` still emits the old `{summary, category, evidence_refs}` shape;
   the new author prompt/§A envelope is a LOC estimate, not a reviewable artifact. *(COV-5)*
3. **Condition 2 (100% of the 3 files accounted for) is unmet for R3:** no checked-in
   risk→enforcing-clause matrix exists; the only matrix on disk covers ConceptualRequirements only
   (`CombinedPlan.md:524-541`), and DriverNameRisks.md itself warns its "100% coverage" claim is
   ambiguous (`DriverNameRisks.md:5`). *(COV-3)*

Non-blocking but required for a buildable, honest plan: drop the `~96-98%` headline and fix the
internal-consistency nits (CON-1..CON-7) and the over-built ingestion machinery (MIN-1..MIN-6).
**Condition 3 (minimum work / max reuse) is the strongest leg** once the cuts in §4 are applied —
the true creation surface is ~13 small components, only `slug()` is verbatim-reused, and the heavy
storage/promotion/audit machinery rightly belongs to the reused guidance writer.
