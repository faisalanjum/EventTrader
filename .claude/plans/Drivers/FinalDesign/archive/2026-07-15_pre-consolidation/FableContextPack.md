# FableContextPack — neutral context pack for the Driver Catalog design challenge

> **What this is:** a navigation + status pack over `/.claude/plans/Drivers/FinalDesign`, written so Fable can act without re-reading every file in `FinalDesign/`, while still seeing every rule's true status. **It is not authority.** Where this pack and a topic file disagree, the topic file wins. This pack labels status; it does **not** solve or extend the design.

## How to read the status labels
| Label | Meaning |
|---|---|
| **LOCKED** | current rule, clearly locked in a live doc |
| **OWNER-APPROVED / TOPIC-BACKPORT DEBT** | owner decided it, but at least one topic doc may still carry shorter or stale prose; the ledger/status docs record the decision |
| **RECOMMENDED / NOT LOCKED** | a recommendation exists (usually in `66 §0.R`), but it is not final rule text yet |
| **TRACKED** | a visible open item / follow-up — not necessarily Fable's task |
| **DEFERRED** | intentionally a later layer / part 2 |
| **SUPERSEDED / DO NOT USE** | dead rule or history only |

> **Sharpest status fact to carry:** the 2026-07-07 cleanup is applied. `95 #26-#30` now exist for D-1, D-3, FS-14, OD-2, and OD-8; OD-1 and OD-6 correctly have **no** `95` row because they are additions/definitions, not reversals, and are recorded in `90 §E`; D4 scoped automatic quarantine is ratified in principle as `95 #39` and back-ported into `10 PIPE-11 D4`. If an older note says these rows are missing or pending, that note is stale.

---

## 1. Executive Summary

**What the Driver Catalog is for** (`01`, `FablePrompt §5`, `14 §7`): one shared master list of reusable *causes* that move stocks — a "Driver" is one atomic cause on its own card (`same_store_sales`, `oil_price`, `revenue_guidance`). It turns scattered mentions across filings/transcripts/news into ONE clean history per cause, across companies and over time, so the system can grade each cause against what the stock did → learn → predict → trade.

**Why one-name-one-meaning matters** (`01` "the one law", `MF-12`): blending two different causes into one name is **permanent** damage (every later fact and lesson is polluted → bad trades you cannot undo). Splitting one cause into two names is a **cheap** one-line fix. Therefore: **when unsure, keep separate.**

**What fresh Fable is being asked to do** (`FablePrompt §9`, `FableAdmissionKernelDesign.md`): stress-test the v3.4 **Driver Identity Admission Kernel** as the current baseline, not restart from scratch. The kernel decides whether each source-backed candidate cause should reuse an existing Driver, admit a new Driver, rewrite and re-check, skip, or park/fail closed. Batch catalog creation and live/on-demand Driver creation must share this one identity logic. The older task areas — batch vs live, reuse display, report scope, Guidance machinery, evaluation harness, and model strategy — are secondary lenses only when they directly change the admission kernel.

**What Fable must NOT waste time re-designing** (`14 §8`, this pack §12):
- the locked record model (`01`–`09`) — naming, fact_scope, units, periods, family, DriverUpdate fields, verdict;
- Track A/B/C **core architecture** ("do not redo Track A, B, or C from scratch", `14 §8`);
- anything already owner-decided (the OD-set) — reuse it, don't re-open it;
- the retired replay design (`13_Track_RetiredDesign.md` — "do not build from this file").

---

## 2. Authority Map

| File | Purpose | Authority | Open it when Fable needs… | Stale traps |
|---|---|---|---|---|
| `01_Overview.md` | mission, the one law, index-card model | **LOCKED** (record model) | the *why* / framing | file self-notes it is a WIP stub (3-tracks map/dashboard unwritten) |
| `02_DriverCatalog.md` | naming rules NAME-01…19 | **LOCKED** | any naming decision | NAME-11 now the local-role rule (OD-3); NAME-08 signed-driver pin (OD-12) |
| `03_Slices_FactScope.md` | fact_scope + slices FS-01…25 | **LOCKED** (FS-22 retired; FS-23 open) | identity, slices, measurement | may still name the **rejected alias layer** (FS-02/FS-19); use `95 #27` |
| `04_Units.md` | unit enum + resolver UNIT-01…14 | **LOCKED** (10-unit enum) | units | UNIT-04 may still say **one hint pair**; use per-slot hints via `95 #26` / `90 §E` |
| `05_Periods.md` | DriverPeriod PER-01…20 | **LOCKED** (PER-20 build-pending) | time windows | PER-19 updated by Track C v2.0 (no both-label transition) |
| `06_MetricFamily.md` | fact_type + BASE_METRIC MF-01…12 | **LOCKED** | family/fact_type | — |
| `07_DriverUpdate.md` | fact record + verdict DU-01…24 | **LOCKED** (DU-13…18 → superseded by 09) | fact fields, verdict | DU-13 says "9-enum" (now 10); use `09` for fields |
| `08_XBRL_ConceptLinking.md` | concept-link recipe XC-01…18 | **LOCKED** (XC-16 recommended) | XBRL linking | XC-12 omits the non-GAAP-no-inherit carve-out (D-5) |
| `09_DriverUpdate_Fields.md` | the 24-field spec (FINAL) | **LOCKED** (owner 07-03) | exact DriverUpdate fields | §3/§8 prose still says "consensus-only" metric-FORBID (D-2) |
| `10_BuildPipeline.md` | **Track A** batch catalog build (PIPE-01…37) | **LOCKED** design; fitness gate never run | the batch build | 0 graph nodes exist; gate unrun |
| `11_TrackB_DriverUpdate_Census.md` | Track B structure inventory (T-refs) | **LOCKED** (adjudicated) | fact-side requirements | mirrors 09/12 |
| `12_TrackB_FactPipeline.md` | **Track B** fact build + missing-Driver handling | **LOCKED** (decisions closed) | writer/validators/missing-Driver | "build-ready" ≠ every identity recipe byte-pinned (D-4) |
| `13_TrackC_GuidanceIntegration.md` | **active Track C** (archive/retire old guidance) | **LOCKED** (v2.0, owner 07-04) | guidance retirement | — |
| `13_Track_RetiredDesign.md` | old Track C **replay** design | **SUPERSEDED / DO NOT USE** | never (history only) | whole file is dead; useful only for its live-graph census numbers |
| `14_BuildReadiness.md` | readiness ledger + missing design + Fable brief | mixed: status doc | what is still un-coded | §7 is aspiration, **not locked design** |
| `66_IssuesToBeHandled.md` | **newest** issue ledger + resolution blocks | status source (recommendations ≠ locked) | issue status, OD blocks | a `66 §0.R` "recommendation" is NOT locked unless it says owner-approved |
| `90_OpenItems.md` | tracked items A–E | status source | open threads | §E now records OD-1/2/6/8 and D4 scoped quarantine cleanup |
| `95_Supersession.md` | reversal ledger | **LOCKED** (dead rules) | "is this rule dead?" | rows #26-#30 and #39 are now present; OD-1/OD-6 intentionally have no 95 row |
| `99_Codex_Decision_Audit.md` | historical audit / completeness cross-check | history only; topic docs win | a completeness cross-check | non-authority; may quote pre-reversal wording |
| `DriverPlan.html` | study slideshow | **DO NOT USE as authority** | a plain-English tour | its authority-tiebreak sentence lives in no md doc |
| `FableAdmissionKernelDesign.md` | current Driver Identity Admission Kernel baseline | **LOCK CANDIDATE / proposal baseline**; topic docs + `90`/`95` win on conflict | the current kernel flow and v3.4 owner-ruling synthesis | implementation experiments still not run |
| `FablePrompt.md` | Fable's mission prompt (admission kernel) | brief, not design | the ask itself | now asks fresh Fable to stress-test v3.4, not restart from zero |
| `FablePromptv2.md` | the **XBRL-integration** design prompt (NOT a newer `FablePrompt.md`) | brief, not design | the XBRL task framing | "v2" = second topic (XBRL fit), not a version bump of `FablePrompt.md` |
| `XBRLIntegrationDesign.md` | **latest XBRL integration design** (10-K/10-Q source-of-truth, Pass 2) | **LOCK CANDIDATE (2026-07-08), owner-ratification pending**; topic docs + `90`/`95` win | XBRL-native DriverUpdate materialization | its 10 amendments (§12.3) are PROPOSED, not yet applied to `08`/`09`/`12`/kernel |
| `WorkflowContextPack.md` | map of the old build **code** (`workflows/`) | navigation only; **code can still be stale** | which existing code to reuse for a build/experiment | topic docs + `95` win over the code |
| `00_Coverage.md` | zero-loss source/index map | **INDEX — non-authority** | a completeness cross-check | its §1 table predates the 2026-07-08 Fable docs (see its §1b) |

---

## 3. Core Invariants (the five non-negotiable laws + two operating principles)

Source: `66 §0.1`, `01`, `FS-04`, `T1.x`.

| Invariant | Statement | Key cites |
|---|---|---|
| **Over-merge vs over-split** | one name = one meaning; over-merge is permanent, over-split is cheap → unsure = keep separate; nothing may fuzzy-match, near-snap, or silently default | `01`, `MF-12`, `FS-04` |
| **Source-backed / store-when-stated** | every name is backed by a real quote; stored values are only what the source states — never computed/fabricated (enumerated exceptions only: implied periods `PER-06`, withdrawal fan-out, derived surprise *state*) | `NAME-18`, `T1.3`, `DU-13` |
| **Code-built, producer-free identity** | id = event + driver + fact_scope; the LLM never builds ids; re-runs MERGE in place; ids are immutable | `FS-01`, `DU-19`, `T1.4` |
| **Point-in-time (PIT) discipline** | writes/menus see only ≤ event-time data; predictors never see realized returns or future facts | `FS-14`, `XC-09`, `DU-23`, `PIPE-34` |
| **LLM judges meaning, code checks structure, all fails closed** | validators hard-fail; enrichment (XBRL links) is never identity; a missing link is safe, a wrong link is the cardinal failure | `T1.6`, `FS-04`, `XC-01` |
| **No human-in-the-loop ambition** (operating goal) | no steady-state review/queue/owner-judgment; one-time human review only at design/bootstrap/eval | `14 §7`, `FablePrompt §4/§7` |
| **Minimal machinery** (operating goal) | no new component unless it clearly improves recall/precision/cost/speed/reliability; prefer reusing the proven substrate; every unresolved case visible, never silent | `14 §7`, `66 §0.1` |

---

## 4. Driver Catalog Locked Rules (record model)

All **LOCKED** in `02`/`03`/`04`/`06` unless noted.

| Topic | Rule (summary) | Source |
|---|---|---|
| **Cause-only name** | the name holds only the reusable cause; state/direction/size/date/company/period/units/quote live in other fields | `02 NAME-01/15/16` |
| **Name format** | lowercase ASCII letters/digits/`_`; starts with a letter; no trailing/double underscore; ≥2 chars | `02 NAME-05` |
| **Open vocabulary** | words come from the source or an existing driver — never a closed word-list | `02 NAME-03` |
| **As specific as evidence** | never coin a broad/category name; breadth emerges only from reuse | `02 NAME-04` |
| **One cause per name** | split bundled causes; short, noun-like | `02 NAME-09` |
| **Word order / familiar / standard phrases** | thing→detail→metric; use familiar forms (`fed_rate`); keep standard phrases whole (`gross_margin`) | `02 NAME-06/07/08` |
| **Name vs slice** | own measured company part (segment/geography/product/customer/channel/entity_ownership) → **slice**, not name; external/unclear cause → name; local role rule, quote+source-company only | `02 NAME-10/11` (**OD-3**, `95 #38`) |
| **Measurement out of name** | adjusted/diluted/constant-currency → the `measurement` slot of fact_scope, never the name | `02 NAME-14`, `03 FS-25` (`95 #2`) |
| **Per-X in name** | source-stated per-X (business AND physical) → in the name; unit stays base; different per-X = different driver | `02 NAME-13`, `04 UNIT-08` (`95 #3`) |
| **What's allowed in a name** | cause + per-X + benchmark identity + terminal `_guidance`/`_surprise` — nothing else | `02 NAME-12/17` |
| **fact_type** | one of {metric, guidance, surprise, action_event}; set once, permanent; persistence test decides metric vs action; strong non-reader model stamps it as the final build step | `06 MF-01`, `07 DU-05/06/07` |
| **SAME_AS** | true synonyms only (`net_sales`↔`revenue`); reversible link, both nodes survive; never cross-flavor; never action↔metric | `06 MF-08`, `02 NAME-02` |
| **BASE_METRIC** | every `_guidance`/`_surprise` → exactly one base metric; terminal suffix only; action_event has none; only the base metric is XBRL-matched | `06 MF-03/06/07/10` |
| **Driver CAN store** | name + fact_type + SAME_AS/BASE_METRIC links + evidence quotes (+ latent base anchors in `families.json`) | `10 PIPE-02` |
| **Driver CANNOT store** | value, unit, period, slice **values**, measurement, driver_state, verdict, XBRL concept/member links — all live on the fact | `10 PIPE-03`, `07 DU-02`, `03 FS-21`, `04 UNIT-07` |
| **New-driver gate** | admit only a reusable, source-grounded, unambiguous cause; vague → skip, never invent | `02 NAME-18` |
| **Finalization / validation** | end-of-build `finalize_catalog.py` stamps fact_type + BASE_METRIC; `validate --final` F1–F5 checks; lane-check hard-fails at fact write | `10 PIPE-24/25/26`, `07 DU-12` |

**Recent owner amendments to naming/identity (status varies):**
- `02 NAME-08` signed-driver pin — no loss-magnitude drivers (`net_income` not `net_loss`) — **OWNER-APPROVED** (OD-12, `95 #32`).
- Measurement tokenization (never-drop sink; maximal-contiguous spans) — **OWNER-APPROVED** (OD-9, `95 #35`, in `03 FS-25`).

---

## 5. Batch Track A Process (`10_BuildPipeline.md`)

**Status:** design **LOCKED** through six review rounds; the fitness/honesty gate has **never run** (0 graph nodes exist) — a production-readiness gap, not a design flaw (`10 STATUS`, `PIPE-37`).

```text
LEAF (per industry):  resolve → fetch → chunk → blind readers → converge(seed)
RECONCILE (per level): guard+slice → (dedup ‖ G2) → Refute → 2nd skeptic → D5(splits) → assemble → validate
FOLD (industry→sector→global): part-a collapse → review/Refute → part-b → reconcile(D3) → D8 → repair → D8
FINALIZE (end of build): fact_type stamp + BASE_METRIC → validate --final          ← the only new machinery
ACCEPT: reader A/B → recreate calibration catalog → first real fold → RUN fitness gate
```

| Question | Answer | Source |
|---|---|---|
| **Reused from existing machinery** | almost the whole proven engine byte-for-byte (`workflows/` + 261-test suite): resolve/fetch/chunk/converge/reconcile/assemble/validate/fold/repair, D1–D8, stage-0 relay hardening, the evidence 5-tuple | `PIPE-06/09/10/11/12` |
| **Overridden (prompt/config only, no new machinery)** | rulebook → NAME-01…19 (PIPE-16); name-vs-slice local role rule (PIPE-17 = OD-3); measurement-out/per-X-in (PIPE-18); Refute scope lens redefined (PIPE-19); DROP reader XBRL guess (PIPE-21); catalog-first → **propose-first** (PIPE-22, `95 #21`); models → config slots (PIPE-23) | `10 §3` |
| **Added (genuinely new)** | `finalize_catalog.py` (PIPE-24); `BASE_METRIC` family edges + `families.json` (PIPE-25); `validate --final` F1–F5 (PIPE-26); micro-hardening (PIPE-27) | `10 §4` |
| **Where names are born** | ONLY at the leaf (one exception: D5 DIFFERENT splits, drawn from the occurrences' own evidence). Higher folds never coin fresh names | `PIPE-09`, `D3/D5` |
| **What higher folds CAN do** | collapse SAME_AS clusters, union evidence, run the same reconcile pipeline (D3), run D5 same-name review, ADD links, validate (D8) | `PIPE-11` |
| **What higher folds CANNOT do** | coin new names (except D5 splits), reopen/break committed SAME_AS automatically, delete | `D3/D4` |
| **Repair** | code-suggest (token-overlap ∪ rare-token ∪ embeddings) → Refute-grade judge → code-apply (only code-suggested pairs) → re-validate. C5 batched lane = **leaves only**; **fold repair stays per-pair** (K2 closed) | `PIPE-10 repair`, `66 §0.R K2` |
| **Finalization stamps** | code-first: terminal `_guidance`/`_surprise` suffix → fact_type deterministically (MF-06); classifier (DU-05/06 prompt verbatim) for the rest; `families.json = {base_metric, latent}`; latent bases are **not** catalog records | `PIPE-24/25` |
| **fitness gate** | freeze catalog → feed fresh PIT-filtered events → producer must reuse/create/skip → independent grader scores name+direction, graded once; must beat baselines 0.634 (registry)/0.535 (blind)/72% agreement | `PIPE-37` |

---

## 6. Live / Missing-Driver / Governed-Create State

> `FableAdmissionKernelDesign.md` v3.4 is now the current kernel baseline for live/on-demand Driver creation. The table below records the source-backed topic-doc state around that baseline. If a row looks older than v3.4, fresh Fable should open the cited topic doc and reconcile it explicitly instead of assuming the pack is authority.

| Item | Status | What it says | Source |
|---|---|---|---|
| **Missing-Driver handling** | **LOCKED** (owner-revised 07-03) | a missing Driver does **not** auto-park: the producer proposes a source-grounded name → checks PIT-safe candidates → **reuses only an exact-same-meaning match** → else the proposal goes through the governed **G1/G2 admission path** → G2 admits/reuses/rewrites → the fact writes. **PARK only when that governed path is unavailable / unresolved / rejected.** The low-level writer never invents Drivers. Scope = any missing driver | `12 §10.6` |
| **G1** | **TRACKED / v3.4 baseline exists** | the live **reuse-display** — how a live producer *sees* related existing Drivers before creating a new one. Topic docs tracked this as open; v3.4 supplies the current baseline display policy, still to be tested/implemented | `10 §13`, `90 §A`, `66 §0.2-A`, `FableAdmissionKernelDesign.md §3` |
| **G2** | **LOCKED** | the admission gate — from evidence, per candidate: reuse / admit / rewrite / skip | `10 PIPE-13` |
| **propose-first** | **LOCKED** (`95 #21`) | producer coins its own name+quote **blind**, THEN sees related existing drivers, PIT-filtered (`visible_from ≤ event date`), ranked by semantic match on name+quote+scope; usage counts tie-break only. (Reverses the dead "catalog-first" flow) | `10 PIPE-22` |
| **What's open about G1 reuse-display** | **TRACKED / implementation-gated** | the topic-doc wiring still needs implementation/testing; v3.4 is the current design baseline to attack or confirm | `12 §10.6`, `90 §A`, `FableAdmissionKernelDesign.md` |
| **OD-7: live-created Driver fact_type/family stamping** | **RECOMMENDED / NOT LOCKED** (TRACKED-NONBLOCKING) | recommendation = "born complete" at live admission (stamp fact_type + resolve BASE_METRIC before the first fact write, reusing Track A's exact components), plus a residual quarantine exit (`retrieval_excluded=true`) for a fact-bearing live Driver later proven wrong. Belongs to the final live-admission pass; not a current DriverUpdate rule blocker | `66 §0.R OD-7`, `14 §3 #10`, `90 §A` |
| **What fresh Fable must now do** | v3.4 stress-test | attack the v3.4 **Driver identity admission kernel** from first principles, then either confirm it, minimally revise it, or identify the exact fatal reason it is not enough | `FablePrompt §9`, `FableAdmissionKernelDesign.md`, `14 §2/§7` |

---

## 7. Reuse Views / Menus

Three **separate** views an LLM may see (`FablePrompt §9`, `12`, `08`):

| View | Status | What is locked | What is open |
|---|---|---|---|
| **Driver reuse view** | partly locked | PIT top-K semantic retrieval of the catalog (embed proposed name + short quote + scope, never the name alone; `visible_from ≤ event date`); usage counts tie-break only | the live **display rules** (G1) are open (`90 §A`) |
| **Slice reuse menu** | **LOCKED** | per-company menu = union of XBRL members across the company's 10-Q/10-K ∪ catalog-used values, **both halves cut at ≤ event time** (PIT); producer picks/coins/marks unknown/omits | member-list materialization is build wiring (`12 FACT-26`) |
| **XBRL concept menu** | **LOCKED** | the company's own reported consolidated numeric concepts, PIT-cut at ≤ event time; LLM picks one or null | the PIT menu query is an ADD (not yet in checked-in code, `12 FACT-30`) |

**Locked view discipline** (`10 PIPE-35/37`, `FablePrompt §9`):
- **No full raw catalog dump** — prompts read code-capped views only. *Why unsafe:* the full catalog is huge, invites over-merge to a superficially-similar name, and diverges from the production shape the gate predicts.
- **No future data** — PIT everywhere. *Why forbidden:* showing data dated after the event (a future fact, a future menu, or the realized return) creates invisible look-ahead bias that corrupts the learn→predict loop and passes tests while failing on real money (`FS-14`, `XC-09`, `DU-23`).
- **Side-list / parked / UNCLEAR / latent names are never reuse candidates** — they are not clean, tradeable, retrievable records; latent bases exist only as family anchors + the concept-inheritance hop (`PIPE-35`).

---

## 8. DriverUpdate Boundary (only as needed for Driver creation)

| Concept | Statement | Source |
|---|---|---|
| **Driver** | a reusable cause **class** — name + fact_type + SAME_AS/BASE_METRIC + evidence only | `PIPE-02` |
| **DriverUpdate** | one **event fact** about a driver — a reported state/change/surprise/guidance/action | `07 DU-01` |
| **DriverUpdate identity** | id = event + driver + fact_scope (no producer); fact_scope = period + slice + measurement (format-normalized only, immutable; `quote_hash` last-resort tie-break) | `FS-01/02`, `09 §3` |
| **Why the catalog must NOT store value/period/slice-value/state/unit/verdict/XBRL concept** | all of these are company- and time-specific → they belong on the fact; putting any on the class would either be wrong for other companies or fork the class by company, breaking one-name-one-meaning | `PIPE-03`, `DU-02`, `FS-21`, `XC-10`, `UNIT-07` |

---

## 9. XBRL / Slice / Family Context Needed for Driver Creation

| Point | Status | Summary | Source |
|---|---|---|---|
| **Hand-curated XBRL dictionary rejected** | **LOCKED** | upkeep burden, misses extensions, and produces confident wrong links; other shortcuts (value-match, string-match, multi-method-agreement) also failed | `08 XC-02` (`95 #13`) |
| **Company-reported concept menu used instead** | **LOCKED** | the correct concept is almost always one the company itself reports, so the menu IS the candidate set; guards → PIT menu → Haiku pick → adversarial verify → deterministic veto, abstain-biased | `08 XC-01/03/09` |
| **Own measured parts → slices** | **LOCKED** | segment/geography/product/customer/channel/entity_ownership, when the quote frames them as the reporting company's own measured part | `03 FS-06`, `02 NAME-10` |
| **guidance/surprise are separate Drivers linked by BASE_METRIC** | **LOCKED** | never merged into the base metric; linked, not same-as; only the base metric is XBRL-matched, guidance/surprise inherit | `06 MF-02/03/10`, `02 NAME-17` |

---

## 10. Existing Guidance / Extraction Machinery to Inspect

Reusable substrate (dispositioned in `12 §2`, `13`):

| Machinery | Reuse note | Source |
|---|---|---|
| **Double-run / multi-pass extraction** | reader A/B is planned; multi-pass measured to add junk (3rd pass ~82% junk) — verify before adopting | `10 PIPE-33` |
| **Review passes / gates** | G2 admission + Refute skeptic + high-blast 2nd skeptic are the catalog's review layer | `10 PIPE-13` |
| **Period resolver** | carve out `driver_period_resolver.py` from the proven Guidance cascade (21 tests, YTD/TTM proof) | `05 PER-10/20`, `12 §5` |
| **Unit resolver** | shared V2 resolver, proven 117/117; relocate + wire (UNIT-14) | `04 UNIT-02/13/14`, `12 §6` |
| **Writer / CLI / daemon / run-ledger** | `guidance_writer.py`/`guidance_write_cli.py` forked → `driver_writer.py`/`driver_write_cli.py`; `extraction_worker.py` + `run_ledger.py` = part-2 runtime seams | `12 §2/§13` |
| **Tests / QA** | 468 passing substrate tests + 7 resolver guards reused as the floor | `12 FACT-08` |

**Stale Guidance assumptions that must NOT leak into Driver naming** (`12 FACT-06`, `95`):
- `taco_bell_same_store_sales` (brand in name — `UnitExtraction.md` Rule 0) → **DEAD** (`95 #1`);
- `adjusted_eps` (version in name — Example 7) → **DEAD** (`95 #2`);
- the `segment_aliases/` human-curated alias layer → **rejected** (census §14.4);
- the `concept_resolver.py` curated dictionary → **DEAD** (`95 #13`);
- `segment_slug='Total'` writer default → **DEAD**; whole-company = omitted slice (`95 #25`).

---

## 11. Open Issues Fable Must Care About

Extracted from `66`/`90`/`14`, scoped to Driver Catalog / live Driver creation. "What Fable must decide / not decide" reflects the docs' own framing.

| Issue | Status | Source | Why it matters | Fable's stance per the docs |
|---|---|---|---|---|
| **G1 reuse-display rules** | **TRACKED / v3.4 baseline exists** | `90 §A`, `66 §0.2-A`, `10 §13`, `FableAdmissionKernelDesign.md §3` | live propose-first display must be implemented/tested; old `catalog_first.js` remains dead | attack or confirm v3.4's display policy only where it changes Driver identity safety |
| **Live-created Driver fact_type/family stamping** | **RECOMMENDED / v3.4 baseline exists** (OD-7 still noted as recommendation in the kernel) | `66 §0.R OD-7`, `14 §3 #10`, `FableAdmissionKernelDesign.md §5` | live admission needs born-complete stamping before first fact write | attack or confirm v3.4's born-complete path; do not treat stale stamp-later ideas as live |
| **Catalog → graph materialization** | **RECOMMENDED / NOT LOCKED** (OD-16) | `66 §0.R OD-16`, `14 §3 #11`, `90 §A` | nobody writes finalized catalog → Neo4j (12 assumes nodes exist; 10 says Neo4j writes are a non-goal) | recommendation = a Track-B-owned `catalog_graph_sync.py`; build wiring, not a rule ambiguity |
| **Final model policy** | **TRACKED / DEFERRED** | `90 §B`, `10 §7`, `95 #15`, `14 §2 #10` | exact model/#runs/fallback/grader per job unset ("Opus reads / Sonnet classifies" is a leading default only) | design the model strategy + experiments; verify prior claims first |
| **Fitness gate / quality budget** | gate never run; OD-6 budget recorded in `90 §E` | `10 PIPE-37`, `66 §0.R OD-6`, `90 §E`, `14 §3 #12` | the gate is the real GO; OD-6 defines the budget (zero confirmed wrong merges over ≥3,000 pre-registered graded slots). `10 PIPE-37` still carries the shorter gate wording | use OD-6's definition; the gate still must actually run |
| **Lifecycle / IPO / dormancy** | **TRACKED** | `90 §A`, `10 §13`, `14 §5` | how new/dormant/delisted/IPO companies enter/leave the catalog; current lean: live G1/G2 absorbs | decide as part of catalog maintenance policy |
| **Target universe count** | **TRACKED** | `90 §A`, `10 §13`, `14 §5` | 796 vs 786 tickers unreconciled | a scope choice for build planning |
| **News Driver admission** | **TRACKED / DEFERRED** (D-10) | `66 §0.R D-10`, `14 §4` | news is excluded from the leaf build; news-coined drivers can enter ONLY via live governed G1/G2 (else park) | design the news admission path in part 2 |
| **Report scope (10-K/10-Q trade-off)** | **DEFERRED** (P0 running-layer) — but a **lock candidate now exists** | `14 §2 #5`, `FablePrompt §9`, **`XBRLIntegrationDesign.md` (7/8, owner-ratification pending)** | whether 10-K/10-Q facts are re-extracted vs built from XBRL bounds historical backfill cost | secondary lens only; handle only where it changes the admission kernel |
| **Incremental refresh / live-backfill (running layer)** | **DEFERRED** (the biggest missing design) | `14 §2`, `90 §D`, `10 §13` | the whole "part 2" production loop is unwritten | not the primary Fable task unless it changes Driver admission safety |

---

## 12. Superseded Traps — dead rules Fable must NOT reuse

| Trap | Now | Source |
|---|---|---|
| Brand/segment in the Driver **name** (`taco_bell_same_store_sales`) | own measured part → **slice** | `95 #1`, `NAME-10` |
| adjusted/diluted/constant-currency in the **name** (`adjusted_eps`) | → the `measurement` slot | `95 #2`, `FS-25` |
| per-X as a **unit**, or "$/physical → unknown" | per-X in the **name**, unit stays base | `95 #3`, `NAME-13` |
| **Catalog-first** G1 (show catalog first) | **propose-first** | `95 #21`, `PIPE-22` |
| Hand-curated **XBRL dictionary** | company-reported menu + guards | `95 #13`, `XC-02` |
| **Old guidance replay** into new facts (`legacy_name_map`, mini-run, bridge) | archive/retire; fresh facts from source docs (Track C v2.0) | `13_TrackC`, `13_Retired` = do-not-build |
| Whole-company **`slice=total`** | whole-company = **omitted slice** | `95 #25`, `FS-10/15` |
| **Alias-layer / fuzzy slice merging** (per-company alias files; "confident alias" merge) | member-anchored **read-time** grouping only (T12.9); alias layer rejected (human-in-loop) | census §14.4; `95 #27`; ⚠️ `03 FS-02/FS-19` may still carry stale prose |
| **FS-22** slice-value recurrence = generic/red-flag | retired; no slice-value recurrence rule | `95 #37`, `03 FS-22` |
| **`level_bound`** field; `qualitative` free-text dropped; fact-node `evhash16` | self-describing shapes + transient hints; `value_text`; evhash16 retired on the fact (kept on the verdict edge) | `95 #16/#17/#18` |
| `previous_guidance` on the **metric** lane | both expectation baselines FORBID on metric → route to `_surprise` | `95 #24`; ⚠️ `09 §3/§8`, `07 §D` prose still stale (**D-2 debt**) |

---

## 13. Experiments / Evaluation Context

| Item | Status | Summary | Source |
|---|---|---|---|
| **Reader A/B gate** | **LOCKED** (must precede acceptance) | at minimum Opus single-pass vs Sonnet-5 single-pass; ground truth = Fable-era CAKE evidence + a fresh key under NEW naming rules; scoring is NEW code (the `ab_*` kit is repair-pair-shaped) | `10 PIPE-33`, `§9 step 7` |
| **Fitness / honesty gate** | **LOCKED** requirement; **never run** | freeze catalog → fresh PIT events → reuse/create/skip → grader scores name+direction once, no retuning; ≥2 producers; must beat 0.634/0.535/72% | `10 PIPE-37` |
| **Quality budget definition** | **OWNER-APPROVED / RECORDED IN 90** (OD-6) | GREEN = ≥3,000 pre-registered graded slots (fixed denominator) · zero confirmed wrong merges (2-grader) · zero unresolved flags · existing bars pass; the 0.1% claim = rule-of-three | `66 §0.R OD-6`, `90 §E`; `10 PIPE-37` still carries the shorter gate wording |
| **Model policy baseline** | **OWNER DEFAULT / EXPERIMENT-GATED** | start with Haiku or another cheap/lower-intelligence model for blind leaf Driver proposals, and Sonnet 5 as the default strong-judge candidate for judgments, Refute, LINK/SAME_AS, BASE_METRIC/fact_type confirmations, quarantine, and similar identity-changing checks. Escalate to Opus 4.8 / GPT-5.5 / Fable only if experiments prove the default misses the locked quality bars. Exact model IDs still pin in `manifest.models` | `FableAdmissionKernelDesign.md §11.0`, `10 PIPE-30/31/32`, `95 #15` |
| **Prior model comparisons mentioned** | context | Sonnet-5 18/19 vs Opus 17/19 on the naming/slice/fact_type golden; multi-pass adds junk (3rd pass ~82%); the open question "did Opus underperform Fable for lack of full context / did multi-run fix it" | `10 PIPE-31`, `FablePrompt §9 output #7` |
| **What Fable should verify before proposing a model strategy** | to-check | whether the workflow JS matches the latest rules; whether the A/B kit (`ab_stratum.py`/`ab_pair_judge.js`/`ab_differ.py`) fits; score **judged precision/recall against an adjudicated key, never quote-match/name-overlap** (quote-match measured ~99% while judged precision was ~29%); test paragraph-at-a-time chunks against larger chunks for blind leaf producers, adopting only if context is preserved and recall/precision do not drop | `10 PIPE-32`, `FablePrompt §9 output #8`, `FableAdmissionKernelDesign.md §12` |

---

## 14. Source Map for Fable

| If Fable needs to reason about… | Open these docs |
|---|---|
| naming rules | `02` (NAME-01…19), `95` (dead rules), `66 §0.R OD-1/OD-3` |
| batch catalog process | `10` (PIPE-01…37), `66 §0.R OD-1/OD-2/OD-6` |
| live / missing-Driver path | `12 §10.6`, `66 §0.R OD-7`, `14 §3 #10`, `FablePrompt §9` |
| G1 reuse display | `90 §A`, `10 §13 + PIPE-22/37`, `66 §0.2-A` |
| DriverUpdate fields | `09` (the 24-field spec), `11` (T-refs), `07` (history) |
| slices | `03` (FS-01…25), `12 §7`, `66 §0.R OD-3/OD-4` |
| XBRL | `08` (XC-01…18), `12 §8`, `06 MF-10`; **latest integration design → `XBRLIntegrationDesign.md` (lock candidate, 7/8)** |
| units / periods | `04` (+ OD-9/10/11), `05` (PER-01…20), `12 §5/§6` |
| guidance retirement | `13_TrackC_GuidanceIntegration.md` (active); `13_Track_RetiredDesign.md` = do-not-build |
| model policy | `10 §7 (PIPE-30/31/32)`, `95 #15`, `90 §B`, `FablePrompt §9 output #7` |
| open issues / status | `66` (newest ledger), `90` (tracked), `14` (readiness) |
| superseded rules | `95` (reversal ledger) — the authority on what is dead |
| recent fact identity amendments | `66 §0.R OD-8/OD-9/OD-10`, `90 §E`, `95 #30/#35/#36`, `14 §3` (quote_hash, measurement token, series_unit) |

---

*This pack was originally assembled from a first-hand read of the then-current `FinalDesign/` set on 2026-07-07. It records status only; it neither solves the design nor assigns work beyond what the docs already frame as open. On any conflict, the cited topic file wins.*

*(Refreshed 2026-07-08: added Authority-Map rows for `00_Coverage.md`, `WorkflowContextPack.md`, `XBRLIntegrationDesign.md` (the latest XBRL lock candidate), and `FablePromptv2.md`; the folder now holds 27 items. Still navigation only — topic docs win on any conflict.)*
