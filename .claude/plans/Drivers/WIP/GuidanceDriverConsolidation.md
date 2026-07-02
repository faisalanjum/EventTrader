# Guidance → Driver Consolidation

*Plan only. Nothing here is built or changed. 0 Driver nodes exist today; the live guidance data is paused, not touched.*

---

## 1. Crux + the honest verdict

**The goal:** make the Driver process the ONE process. Today's "Guidance" stops being its own family of database records and its own pipeline. It becomes just **one `fact_type` ('guidance')** of the Driver model — and borrows Guidance Extraction's trustworthy "let code decide, not the AI" toolkit (calendar periods, units, accounting-concept links, segments, fixed ID recipe, evidence rules).

**The honest verdict (one screen):**

- **Can we borrow it?** Mostly **YES** — but in two halves:
  - The **producer half** (judge a guidance fact from one source, emit one record) maps cleanly onto a Driver "producer." Already half-done: the guidance state words and the unit list are locked + reused.
  - The **class-naming half** has friction. Today's guidance writer **coins the metric's name AND writes the fact in one shot**. The Driver rules forbid a producer from inventing class names — only the catalog build may.
- **Should we borrow it?** **YES — but only as a per-fact_type "profile"** (a small ON/OFF checklist per fact_type). Three tools are safe everywhere. Three are guidance-shaped and must stay OFF facts that have no fiscal period / accounting concept / business segment (like a CEO leaving).

> **The one sentence the owner must internalize:**
> **Unify is the chosen target (§12): guidance facts get REGENERATED as Driver records — never migrated.** The optional read-only bridge only makes guidance *visible*; it does NOT by itself deliver one process. Build the producer first, prove it, then fold guidance in via the existing write code. Under-doing it is reversible; over-doing it is permanent.

---

## 2. Status banner — what is real vs on paper

| Thing | State today |
|---|---|
| **Guidance pipeline (live, verified)** | Ran in production: **548** metric-tags + **8,432** per-event records. **Currently PAUSED** (scaled to 0), not deleted. |
| **Driver layer** | **ON PAPER only — 0 Driver records, 0 DriverUpdate records, 0 links.** |
| **This file** | **PLAN ONLY.** A proposal. Changes nothing. Fully reversible. |

**The asymmetry that drives every call below:**
Borrowing wrong risks **real** guidance data. The Driver side risks **nothing** by waiting.
→ When unsure: keep two paths longer (safe). Never merge in a way you can't undo (permanent).

---

## 3. The goal restated plainly + the two honest questions

**Plain what / why:**

- **What:** One pipeline. "Driver" = a thing that moves a stock (revenue, capex, a CEO leaving, guidance). Each driver gets a class name once; each real event creates a fact record (a `DriverUpdate`).
- **`fact_type`** = a small label on a driver saying what KIND of fact it is. The schema already names the values, and `'guidance'` is one of them.
- **Why borrow the guidance toolkit:** guidance is trustworthy because the AI only *judges*; **code** computes every ID, unit, period, and link. We want that same discipline on Driver facts.

**Borrow = the deterministic toolkit:**
period resolution (calendar windows) · unit resolution · accounting-concept resolver · segment/member resolution · fixed ID + change-hash recipe · the layered prompt loading · the "AI judges / code decides" split · evidence/quote rules.

**The two honest questions (we do NOT assume the answer is yes):**

1. **POSSIBLE?** Can each piece actually be lifted into the Driver process for `fact_type=guidance` — and which pieces extend cleanly to OTHER fact_types (metric, surprise), vs which are guidance-only?
2. **ADVISABLE?** Does borrowing fit the clean generic Driver model — or does it drag guidance-only assumptions (fiscal periods, accounting concepts, segments) onto facts that have none? Where is reuse a clear win vs a contamination trap?

---

## 4. The reuse matrix (the scannable answer)

> "Possible" = can it technically be lifted. "Advisable" = should it. Verdict = what to do.
> *Two terms used below, defined once:* **fail-closed** = when unsure, code leaves it BLANK (safe). **fail-open** = when unsure, code writes a possibly-WRONG value (dangerous).

| # | Module (what it is) | Possible? | Advisable? | Verdict | One line |
|---|---|---|---|---|---|
| 1 | **Evidence rules** — every fact needs a real quote + source + date, or no record | Yes (plain text, no assumptions) | **Clear win — ALL fact_types** | **REUSE the shared file as-is + BUILD a new gate** | Load the existing evidence file unchanged; add a hard-fail check. Don't copy guidance's in-quote tags like `[8-K]` — they'd leak into the fact-identity key. |
| 2 | **Fixed ID + change-hash** — the "which record is this" recipe + a separate hash that flags real value changes | Yes (recipe already adopted) | **Split:** tiny helpers = win; merging guidance's live IDs = NO | **REUSE the pure helpers; BUILD a separate Driver ID maker; keep TWO ID lanes** | Re-using guidance's live IDs would orphan 8,432 records — permanent. Keep guidance on its own `gu:` lane. |
| 3 | **"Code decides" discipline** — AI judges, Python computes IDs/units/periods; the database-write tool is kept out of the AI's hands | Yes (already a standalone command-line library) | **Clear win — universal** | **REUSE the existing scripts as a shared library (do NOT re-code)** | Every producer routes writes through the existing writer. The cache part is guidance-shaped — scope it. |
| 4 | **Units** — a 9-value canonical list + a resolver | Yes | **List = win NOW. Heavy resolver = premature** (only ~3% of live records use it; has a live bug) | **REUSE the list now; DEFER the heavy resolver** | Make the 9-value list the ONE source of truth so the hand-copied schema copy can't rot. Defer the complex resolver until a real metric fact_type exists. |
| 5 | **Periods** — calendar-window records + a 4-step fill-in cascade | Yes for guidance (this exact code wrote 8,432 live records) | **Win for guidance; optional for fiscal metric/surprise; TRAP on action_event** | **REUSE the exact function as a library, SCOPED to guidance** | A CEO resignation has no fiscal quarter — never force a period. Pin guidance to the validated model (a known model has a +1-month bug). |
| 6 | **Accounting-concept resolver** — maps a label to a standard us-gaap concept, leaves blank if unsure | Yes for guidance; low for others until the cache widens | **Mandatory for guidance (else it regresses); DEFER elsewhere; TRAP on action_event** | **REUSE as-is for guidance; BUILD a new validator; DEFER elsewhere** | It is safe BUT **fail-open** when a company has no cache — so the fact_type gate is mandatory, not optional. |
| 7 | **Segment / member resolver** — maps segment text to segment records (100% code-owned) | Yes (pure, deterministic) | **Safe but SPARSE (few facts need it); low value now** | **REUSE-LATER — defer on value grounds; keep one rule** | Lowest risk, lowest value now. The schema ALREADY supports a structured segment scope — no schema change needed. For v1, just lock the rule: producer emits blank, code resolves. |

**Shape of the answer:** 3 universal wins (1, 2-helpers, 3) · 1 now/later split (4) · 3 guidance-scoped-defer (5, 6, 7).

---

## 5. Per-module detail

For each: what it does · verdict + why · what Driver must add · integrity note · the scoping guard.

### 5.1 Evidence / quote rules — universal win
- **Does:** no quote + source + date → no record. The anti-made-up-facts floor.
- **Verdict + why:** clear win for every fact_type. action_event needs it MOST — the quote IS the whole fact (no number to cross-check).
- **Driver must add:** a NEW hard-fail check. The source-link target differs (Driver fact → Event, vs guidance → Report), so the check is new code even though the rules file is reused unchanged.
- **Integrity:** matches the Driver §0 evidence-first intent already.
- **Guard:** do NOT copy guidance's in-quote source tags (`[PR]`/`[8-K]`/`[News]`). Driver already has a structured `source_type` field; the tag string feeds the fact-identity key and inconsistent tagging would split or wrongly merge facts.

### 5.2 Fixed ID + change-hash — split verdict
- **Does:** the ID says WHICH record (the "slot"); a separate hash (`evhash16`) flags when a value actually changed. This split is exactly why re-runs overwrite-in-place instead of duplicating.
- **Verdict + why:** the tiny pure helpers (slugify, the change-hash, source-id normalizer) are a clear win everywhere. Merging guidance's live IDs onto a new recipe is NOT — see the integrity note.
- **Driver must add:** a thin Driver-ID maker (key = event + driver + fact_scope) on a SEPARATE `driver:` lane. The action_event path needs a NEW quote-normalizer (greenfield, high-volume, must be unit-tested).
- **Integrity (load-bearing):** the live guidance ID is `gu:{source}:{label_slug}:{period}:{basis}:{segment}` — **no value hash inside it**. Change ANY part of this recipe and all 8,432 IDs stop matching → re-extraction makes DUPLICATES and orphans the originals. **Permanent.**
- **Guard:** two physically separate ID lanes — `gu:` for guidance, `driver:` for everything else. Never one generic recipe over guidance.

### 5.3 "Code decides" discipline — universal win
- **Does:** the AI judges meaning; Python computes every ID/unit/period; the database-write tool is deliberately absent from the AI's tool list. All writes flow Bash → writer script → one atomic overwrite-in-place.
- **Verdict + why:** clear win, universal — this is the integrity floor.
- **Driver must add:** keep the write tool out of every producer's hands; route writes through the existing writer scripts as a SHARED LIBRARY; adopt the orchestrator's fail-closed billing strip (not the worker's weaker YAML-only env-blanking).
- **Integrity:** preserve the two-layer write gate verbatim — needs BOTH `MODE=write` AND a default-OFF flag; dry-run always validates but never writes.
- **Guard:** the warmup cache's big-text fetch is redundant (the Driver reader already chunks text to disk). Borrow ONLY the guidance-gated concept/member cache, at the producer.

### 5.4 Units — now/later split
- **Does:** a 9-value canonical unit list + a resolver that maps messy units onto it.
- **Verdict + why:** import the 9-value list NOW as the single source of truth (kills a whole class of silent drift — the schema currently hand-copies the list, which can rot and break the dedup/guidance join). The heavy 3-axis resolver is premature: only ~3% of live records use it, it has a known infix bug, and no Driver fact_type needs it yet.
- **Driver must add:** wire the lane-check to validate against the imported list; reuse the simple alias path for action_event money (a $0.50 dividend).
- **Integrity:** the unit list is fact_type-agnostic — safe everywhere.
- **Guard:** defer the heavy resolver until a real metric/surprise fact_type exists AND a public-API refactor is done.

### 5.5 Periods — guidance-scoped win
- **Does:** calendar-window records + a 4-step cascade (reuse → SEC cache → predict → fiscal-year-end math) to fix the exact window.
- **Verdict + why:** clear win for guidance (this exact function wrote 8,432 live records — re-deriving the math risks splitting the live timeseries). Optional for fiscal metric/surprise. Contamination trap on action_event.
- **Driver must add:** supply each company's fiscal-year-end. Keep the `gp_` period namespace + its 4 sentinel records scoped to guidance, NOT the generic writer.
- **Integrity:** the model matters — a known model produces a reproducible **+1-month** period on odd fiscal-year-ends, which silently breaks dedup. Pin guidance to the validated model regardless of the Driver reader's model swap.
- **Guard (precise):** period resolution **fails CLOSED — it RAISES (crashes) if fiscal-year-end is missing.** So the fact_type gate here prevents a hard crash on action_event. Confirm the fiscal-year-end input path before wiring.

### 5.6 Accounting-concept resolver — guidance-scoped, mandatory-for-guidance
- **Does:** maps a label (e.g. `revenue`) to a standard us-gaap concept; leaves it blank when ambiguous.
- **Verdict + why:** mandatory reuse for guidance (skipping it = guidance regresses below today). Defer for metric/surprise until the cache scope widens. Contamination trap on action_event.
- **Driver must add:** a NEW validator (concept exists + company reports it + edge matches property) and set-replace edge hygiene — do NOT lift the guidance writer's add-only edge path (it has a known stale-edge bug).
- **Integrity (precise):** this resolver **fails OPEN on a missing cache** — it could write a plausible-but-WRONG concept onto an action_event. So the fact_type gate here prevents a silently-wrong link. **The gate is mandatory, not cosmetic.**
- **Guard:** never invoked for action_event. The cache currently excludes 8-K filings and has no live fallback — that blocks concept reuse for metric/surprise but does NOT block guidance.

### 5.7 Segment / member resolver — defer on value
- **Does:** maps segment text to segment records; 100% code-owned.
- **Verdict + why:** safe (pure, deterministic) but SPARSE — only a minority of facts carry a segment. Low value now.
- **Driver must add:** nothing yet. Keep ONE rule: the producer emits a blank segment ID, code resolves it.
- **Integrity:** the segment string feeds the fact-identity key — inconsistent segments would split facts.
- **Guard / correction:** **NO schema change is needed.** The locked fact_scope recipe ALREADY lists segment as a first-class structured option (schema line 147: "period / segment / geography / store-type"). Defer member resolution on **value/sparsity** grounds only — there is no schema gap to fix.

---

## 6. Recommended design

**Plain:** build the new Driver producers with the 3 universal safety tools baked in. **The target is unify (§12):** guidance becomes `fact_type=guidance` and is REGENERATED through the Driver producer (never migrated). The read-only bridge below is **optional temporary scaffolding** — build it only if the predictor needs guidance before the unified producer exists.

### 6.1 The per-fact_type "profile" idea (the organizing principle)

Each fact_type gets a small ON/OFF checklist — switch a module ON only where that fact actually has a period / concept / segment. Evaluated in **code** at the producer/writer boundary.

| Module | guidance | metric | surprise | action_event |
|---|---|---|---|---|
| Evidence gate | ON | ON | ON | **ON** (quote IS the fact) |
| ID + change-hash | ON | ON | ON | ON (key falls back to quote-hash) |
| "Code decides" lane check | ON | ON | ON | ON |
| Unit resolver | ON | ON | ON | simple alias only |
| **Period** | **ON** (mandatory) | only if fiscal | only if fiscal | **OFF** |
| **Concept** | **ON** (mandatory) | deferred | deferred | **OFF** |
| **Member/segment** | ON if segment present | if segment present | if segment present | **OFF** |
| Warmup concept/member cache | ON | scoped | scoped | OFF |
| Model | pinned-validated | — | — | — |

**The key guarantee:**
- The **3 universal modules** (evidence, ID/hash, code-decides) can NEVER be switched off.
- The **3 guidance-shaped modules** (period, concept, member) are OFF by default, ON only by profile.
- A fact with no fiscal period simply has nothing for the period cascade to route — that absence IS the signal the module doesn't belong.

### 6.2 The node model (text sketch)

```
 (:DriverUpdate fact) ──OF_DRIVER──▶ (:Driver class)          "fact is an instance of the class"  (always, 1)
 (:DriverUpdate fact) ──FROM_SOURCE──▶ (:Event)               "fact came from this event"  (always)
 (:Event) ──EXPLAINED_BY {verdict}──▶ (:DriverUpdate fact)    "this event's move is explained by this fact"  (0 or 1 per producer)

 Optional best-effort links ON THE CLASS (:Driver):
   (:Driver) ──MAPS_TO_CONCEPT──▶ (:Concept)
   (:Driver) ──MAPS_TO_MEMBER──▶ (:Member)
   (:Driver) ──MAPS_TO_GUIDANCE──▶ (:Guidance anchor)   ← OPTIONAL link to the live guidance graph

 (:Guidance anchor).canonical_driver = "driver:<slug>"   ← DERIVED back-pointer; NEVER relabel the guidance label
```

### 6.3 How guidance's rich content is hosted — two paths

| Path | Where units/period/concept/member live | Note |
|---|---|---|
| **(A) OPTIONAL bridge (temporary scaffolding)** | Stays on the LIVE GuidanceUpdate records; Driver layer reaches them via the read-only `MAPS_TO_GUIDANCE` link + the derived `canonical_driver` pointer. Live nodes NOT mutated. | Reversible. Makes guidance *visible*, not unified. Build ONLY if the predictor needs guidance before the producer exists. |
| **(B) THE TARGET — unify by REGENERATE** | The guidance producer writes guidance facts directly through the existing write code, calling the shared period/concept/member library behind a `fact_type=='guidance'` gate. | **REGENERATE, not migrate** (§12). Needs the class/instance decoupling + the node-label decision (§12). |

### 6.4 The "AI judges / Python decides" split (how the producer calls reused code)

```
PRODUCER emits ONLY judgment:                 SHARED LIBRARY (Python) computes everything:
  driver_name, driver_state,        ──Bash──>   the ID + change-hash
  quote, period-as-stated,                       canonicalize the unit
  value-as-stated, unit-as-stated,               resolve period/concept/member (ONLY if profile says so)
  segment-as-stated                              atomic overwrite-in-place MERGE
                                                 behind a default-OFF flag, dry-run/shadow/write modes
```
The write tool stays absent from every producer. Same shape as the live extractor.

### 6.5 Reuse as a SHARED LIBRARY (not a rewrite)

Treat the existing scripts under `.claude/skills/earnings-orchestrator/scripts/` as a library — **import** the verified pieces, never fork them (re-coding risks subtle divergence from the version that wrote the live nodes).
- **Reusable everywhere:** `slug()`, the change-hash, source-id normalizer, the 9-value unit list, the simple alias path, the code-decides + write-tool-absent guardrails.
- **Guidance-shaped (gate by fact_type):** the period-ID builder + 4-step cascade, the concept resolver, the member/segment resolver.
- **NEW code only:** the thin Driver-ID maker, the Driver write/edge path, the validators.

---

## 7. Company-confirmed vs unconfirmed (the orthogonal tag)

**What it is:** did the company itself state the fact, or is it a third-party/unconfirmed report? An **authority** axis — separate from `fact_type` AND from `driver_state`.

| Example | fact_type | company_confirmed |
|---|---|---|
| 8-K dividend | action_event | confirmed |
| News takeover rumor | action_event | unconfirmed |
| Guidance | guidance | **confirmed (by construction)** |

There is no "unconfirmed guidance" — news ABOUT guidance is deliberately skipped in production.

**Where it lives:** an INSTANCE-level property on `DriverUpdate`, **never** on the Driver class (the class is authority-neutral — the same `dividend` driver can carry a confirmed 8-K fact AND an unconfirmed news-rumor fact).

**Recommended:** a small explicit enum `company_confirmed ∈ {confirmed, unconfirmed}` — NOT overloading `source_type` (a company can be quoted INSIDE a news article = confirmed-via-news; an 8-K can relay a rumor = unconfirmed-in-a-filing, so source_type→authority is not 1:1).

**How it's set:** code-set for guidance (always `confirmed`) and wherever authority is unambiguous (SEC filing = confirmed; pure third-party news = unconfirmed); producer-proposed only in genuinely ambiguous cases. Today the axis is implicitly carried by `source_type` + the locked action_event `rumored` state.

**One required assertion (integrity):** `company_confirmed` is a **PROPERTY ONLY — never part of the fact key** (event + driver + fact_scope). Otherwise a confirmed 8-K fact and an unconfirmed news fact about the same driver/event/scope could be forced to merge or wrongly split. It is additive and blank-until-set; it must not collide with the locked `driver_state` lanes or `fact_type`.

---

## 8. What is already decided vs still on paper (status)

*(This is about how solid each idea is — not the company-confirmed tag.)*

| Design point | Status |
|---|---|
| §0 creation contract (catalog = class only; producers = facts; no build seeder) | ✅ **DECIDED / LOCKED 2026-06-15** |
| guidance `driver_state` words (introduced/raised/lowered/reaffirmed/withdrawn) | **Locked** |
| number/comparison layer reuses guidance's 9-value unit list verbatim | **Locked / verified** |
| action_event `rumored` state (the unconfirmed proxy) | **Adopted 2026-06-17 (RavenPack Borrow 1)** |
| fact_scope supports structured segment | **Locked (schema line 147)** |
| basis (GAAP vs adjusted) lives in the NAME for Drivers | **Deliberate, documented choice (R9)** |
| **Unify is the TARGET direction** (regenerate, not migrate) | ✅ **DECIDED 2026-06-18 (owner) — see §12.** The *build* + the node-label are NOT yet decided. |
| Everything else in THIS file: the profile, `company_confirmed` enum, the bridge resolver, the unify BUILD details | 🟡 **SUGGESTION ONLY — nothing built yet** |
| `MAPS_TO_GUIDANCE` resolver recipe | **Schema marks it "STILL OPEN — SUGGESTION ONLY"** — inherit that status |

---

## 9. Sequenced migration buckets (only the advisable parts)

> Unify is the target (§12). **Bucket 3 (bridge) is OPTIONAL temporary scaffolding** — build it ONLY if the predictor needs guidance before the unified producer (Bucket 4) is ready; otherwise skip straight to Bucket 4. Never build both — that's throwaway work.

### Bucket 0 — Plan + profile spec (no code, fully reversible)
**Goal:** write the per-fact_type profile + the `company_confirmed` tag as a proposal. Unify is already the target (§12) — the call to settle here is the **node label L1/L2/L3** (§12), BEFORE any build.
- Author the profile table (guidance=full, metric/surprise=conditional, action_event=floor-only) as a SUGGESTION-ONLY schema section. Gate: owner sign-off.
- Add the `company_confirmed` proposal (instance-level enum, guidance fixed to confirmed by code, property-only/not-in-key, additive/blank-until-set).
- Record the genuine open owner calls (node label **L1/L2/L3**, `company_confirmed` enum, concept-cache scope, write-flag design). *(Basis placement is NOT one — it's a unify-path reconciliation task; see §11 "Resolved already".)* Gate: no dependent bucket starts until its decision is made.
- **Exit:** owner approved the profile + `company_confirmed` + chose the **node label (L1/L2/L3)**. Zero code/nodes changed.

### Bucket 1 — Universal integrity floor (built into NEW Driver producers only)
**Goal:** give every producer the 3 safe-everywhere tools. Touches 0 live nodes.
- Load the evidence file verbatim + BUILD a hard-fail validator rejecting any DriverUpdate missing quote/source/date. Don't add in-quote source tags. (Skip-harm is severe for action_event.)
- BUILD a thin Driver-ID maker importing the pure helpers; compose the key on a SEPARATE `driver:` lane. **Spec + unit-test the action_event quote-normalizer FIRST — it is greenfield and gates this bucket's own exit demo.**
- Pin the write-tool-absent guardrail + adopt the orchestrator's fail-closed billing strip; reuse the deterministic HELPER scripts as a library (the Driver write/edge path itself is NEW — §6.5).
- **Exit:** producers write metric/action_event facts in dry-run with deterministic IDs + change-hash + evidence gate, write tool absent, billing fail-closed — verified on a small sample. Guidance untouched.

### Bucket 2 — Unit list as single source of truth (small, clear win)
**Goal:** stop hand-copying the 9-value unit list; reuse the simple alias path.
- Make the producer/writer **code lane-check validate against the imported Python unit set** (or add a test asserting the schema table equals the live list). *(Correction: the schema is a markdown doc — it can't literally "import" the list; the anti-drift guard is a test/lane-check in CODE.)*
- Reuse the simple alias path for action_event money; keep the heavy resolver DEFERRED (premature: ~3% used, infix bug, private API).
- **Exit:** Driver unit handling resolves through the shared list + alias path; no hand-copied list can drift silently; heavy resolver explicitly deferred.

### Bucket 3 — Read-only guidance bridge (the SAFE way guidance becomes VISIBLE)
**Goal:** connect the Driver catalog to live guidance read-only. Change NOTHING in the guidance pipeline.
> **Inherit SUGGESTION-ONLY status — the schema marks this resolver "nothing decided, locked, or built."** Not ready-to-build as written.
- Build the `MAPS_TO_GUIDANCE` resolver (exact-slug spine + evidence-judge + merge-skeptic, no list), MATCH-only, one-to-many, set-replace each run. Reuse `slug()` verbatim. NEVER relabel; NEVER create Guidance nodes. Fail-closed (unsure → leave unlinked; an over-merge is permanent).
- Add the optional derived `canonical_driver` back-pointer on the Guidance anchor (class-level only), derived from the edge set with set-replace discipline. One source of truth = the edge.
- **Exit:** Driver→guidance timeseries query works via the bridge with ZERO mutation of live nodes. **Re-measure precision on a NON-restaurant sample** — the prior ~85–98% was a single offline session on 37 restaurant names, NOT a cross-industry result. Owner can STOP here (guidance visible, not unified).

### Bucket 4 — Guidance-shaped resolvers as a SCOPED library (only if a guidance/fiscal producer is built)
**Goal:** when a real guidance (or fiscal metric/surprise) producer is built, call the period/concept/member resolvers as a library, gated by the profile. action_event never touches them.
- Wire period/concept/member behind a `fact_type=='guidance'` gate. Supply each company's fiscal-year-end (the cascade **RAISES** if missing — fails closed). Keep the `gp_` namespace + sentinels scoped to guidance. (Period gate prevents a CRASH; concept/member gate prevents a WRONG link — both mandatory, different reasons.)
- BUILD a NEW optional-link validator + set-replace edge hygiene — do NOT lift the guidance writer's add-only edge path (known stale-edge bug).
- **IF UNIFYING (the target — REGENERATE, not migrate):** decouple the class MERGE (producer MATCHes a catalog-built class, never coins one); decide the node label (§12); reconcile basis placement (see §10); pin the validated model; then delete-and-regenerate guidance through the producer (regenerate-then-retire). Gate: explicit owner go on the label + a green sample-equivalence check before retiring the old nodes.
- **Exit:** chosen-scope guidance/fiscal facts get periods/concepts/members via the library; action_event provably never invokes them; optional links validated; if unified, guidance regenerated through the producer and the old nodes retired ONLY after sample-equivalence passes.

---

## 10. Risks & guards

| Risk | Guard |
|---|---|
| Concept/member resolver **fails OPEN** on action_event (writes a wrong link). Period resolver **fails CLOSED** (crashes if fiscal-year-end missing). | The external fact_type gate is MANDATORY for both — concept/period/member never even invoked for action_event. Gate the period sentinels by fact_type too. |
| Re-cutting guidance's live IDs or relabeling its label = **permanent** (orphans 8,432 records / splits timeseries). | Two physically separate ID lanes (`gu:` vs `driver:`); MATCH-only bridge; derived pointer never relabels; **unify via REGENERATE-then-retire (never a re-keying migration), with sample-equivalence before retiring the old nodes.** |
| **The optional bridge does NOT deliver "one process"** — guidance stays a foreign node. | Treat the bridge as temporary scaffolding only; one process comes from unify (regenerate via the producer). Don't let the bridge masquerade as unification. |
| The `gu:` ID embeds **basis AND segment** as ID segments. Driver puts basis in the NAME and segment in fact_scope. So "keep the `gu:` grammar" on the unify path silently re-imports guidance-shaped structure on TWO axes, not just the prefix. | Treat basis + segment placement as explicit unify-path reconciliation items, not a clean "keep the grammar." |
| The +1-month fiscal-period model bug breaks guidance dedup if guidance runs under the Driver reader's model swap. | Model choice is per-fact_type; pin the guidance fact-writer to the validated model regardless of the reader. |
| Forking the verified code diverges from the version that wrote the live nodes. | Import the pure helpers/resolvers as a shared library; NEW code only = the Driver-ID maker, the write/edge path, the validators. |
| The guidance writer is add-only with a known stale-edge bug; reusing its edge path verbatim inherits it. | Build NEW set-replace edge hygiene + an optional-link validator on the Driver side. |
| The action_event quote-hash key depends on a quote-normalizer that doesn't exist yet (high-volume). | Treat as greenfield with unit tests; a divergent normalizer splits facts. |
| Per-fact_type write flags multiply the silent-no-op surface. | Default-OFF everywhere + dry-run-always-validates + register each fact_type as a run-ledger component so unlogged/poisoned counts surface. |
| Unify-path guidance producer needs **prior-period guidance value memory** to set state (introduced = first/new; raised/lowered judged vs prior history). | A real Bucket-4 producer-design constraint — the producer must read prior Guidance value-history before setting state. |
| Heavy unit resolver / concept resolver premature for metric/surprise (low usage, no reader consumes the optional links today). | Under-reuse: defer for non-guidance fact_types; mandatory ONLY for guidance to avoid regression. |

---

## 11. Open owner decisions

1. **UNIFY vs BRIDGE → DECIDED: UNIFY is the target. See §12** (owner's call 2026-06-18). The migration fear is dropped — guidance nodes are disposable, so we **regenerate, never migrate**. **⭐ The pivotal remaining call is the node LABEL (L1 / L2 / L3 — see §12); decide it BEFORE any build** — it drives query patterns, constraints, and how much write code is reused.
2. **Make `company_confirmed` an explicit enum (recommended) or keep it implicit** via source_type + the rumored state? Explicit is cleaner (authority isn't 1:1 with source_type) but adds a field.
3. **Concept-cache scope:** widen it to include 8-K (pulls in lower-quality XBRL contexts to re-validate) or accept lower concept coverage? Blocks concept reuse for metric/surprise; does NOT block guidance.
4. **Write-flag design:** per-fact_type default-OFF flags (safer, no accidental go-live) vs one global flag (fewer ways to mis-set)? Decide before any producer writes.
5. **`canonical_driver` back-pointer:** adopt it (born-linked, self-heals) or stay strictly edge-only? Edge-only is minimal-safest; the pointer is a convenience denormalization needing set-replace discipline.

**Resolved already (not open — recorded so they aren't reopened):**
- **Basis (GAAP vs adjusted) placement** is NOT an open design question. The schema deliberately chose basis-in-the-NAME (R9). It is only a **unify-path migration reconciliation task**: guidance keys basis inside its ID, Drivers put it in the name — a known mechanism mismatch to bridge during migration if and only if you unify.
- **Segment fact_scope** needs NO schema change — segment is already a first-class structured scope (line 147). Member resolution is deferred on value/sparsity grounds only.

---

## 12. Unify decision — owner's call (2026-06-18)

**Decision: the target IS unify (one process, guidance = `fact_type=guidance`). Confirmed.**
The earlier "migration is weeks + permanent risk" worry is **dropped** — the live guidance nodes are **disposable**: if we unify they get re-created anyway.

**The key reframe — "unify" is two separable jobs; we only need one:**

| Job | Gives | Verdict |
|---|---|---|
| **Runtime unify** (one LLM pass emits guidance + other facts) | the "no double-read" benefit | ✅ the part we want |
| **Migrate the 8,432 live nodes** | tidy tables | 🚫 **off the table — regenerate instead** |

→ **Rule: REGENERATE, never migrate.** Delete-and-re-extract (a backfill), not a re-keying script. No orphaned IDs, no split-timeseries risk.
→ "Delete" really means **regenerate-then-retire** (don't leave a window with no guidance data).

**What dropping migration removes:** re-keying danger + weeks of migration-verification. Gone.

**What still stands (independent of node-disposability):**
- You **can't fold guidance into a producer that doesn't exist yet** — the producer is still the gating unknown.
- **Loss of isolation** — one pipeline means a driver bug can reach guidance.
- **Regenerate isn't free** — it re-pays the full guidance LLM extraction bill (billing-sensitive).

**The condition that makes "exactly the same nodes" both TRUE and CHEAP — and it depends on the label choice below:**
> **Reuse the existing guidance deterministic code as far as the label choice allows — never re-implement its id/unit/period/concept/member logic.**
- The **id/unit/period/concept/member normalization logic** is reusable as a shared library in ALL cases — that part is always "verbatim."
- Whether the **write + MERGE + label step** is reused verbatim depends on the label decision below (the write code currently MERGEs `:Guidance` / `:GuidanceUpdate` labels).

**⭐ THE PIVOTAL OPEN DECISION — the node label (decide BEFORE any build):**
Not a small detail — it sets query patterns, constraints, how much write code is reused, and whether this is *truly* one node family. Three options:

| Option | What it means | Code reuse | "One process"? | Cost |
|---|---|---|---|---|
| **L1 — keep `:GuidanceUpdate`** | guidance instances stay their own label; Driver class canonicalizes via `MAPS_TO_GUIDANCE` (matches the schema's own instance↔instance framing, `DriverGraphSchema.md:352`) | writer **verbatim** ✅ | partial — one pipeline, two instance labels | lowest |
| **L2 — switch to `:DriverUpdate` (`fact_type=guidance`)** | guidance instances ARE DriverUpdate nodes; `:GuidanceUpdate` retired | logic only; **new** write/label layer | full ✅ | highest (re-attach period/concept/member edges; heavier proof) |
| **L3 — dual-label `:DriverUpdate:GuidanceUpdate`** | one physical node carries BOTH labels | writer **near-verbatim** (add the 2nd label) ✅ | full ✅ + old guidance queries still work | medium |

**Tentative lean (your call): L3** — one node, both query worlds keep working, write code reused nearly as-is, so "exactly the same" stays cheap. **L2** is the purest unify but the most work + proof. **L1** is cheapest but leaves guidance a separate instance label (the schema's current framing — closer to the bridge than to unify).

**Bridge may now be throwaway:** if unify is committed, Bucket 3 (read-only bridge) is scaffolding — **build it ONLY if the predictor needs guidance before the unified producer is ready**; else skip it.

**Recommended sequence (refined — same destination, safer road):**
```
1. Build & PROVE the generic producer on EASY fact_types (metric / action_event)
      → derisk the real unknown cheaply, in isolation
2. Fold guidance in: reuse the deterministic LOGIC verbatim (write/label layer per the chosen L1/L2/L3) + ONE regenerate run
3. Skip the read-only bridge unless the predictor needs guidance sooner
```
**Still hold firm:** prove the producer before coupling guidance to it · pin guidance to its validated model (the +1-month bug) · reuse-don't-rewrite so "exactly" stays free.
