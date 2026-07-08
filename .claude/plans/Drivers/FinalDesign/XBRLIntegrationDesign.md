# XBRL-Native Driver / DriverUpdate Integration — FINAL DESIGN (Pass 2)

> **STATUS (2026-07-08): FINAL PROPOSAL — LOCK CANDIDATE, owner ratification pending (§11 pin bundle + §12.3 amendment list, one yes/no).** Supersedes the Pass-1 WIP (three candidate designs: GPT 5.5 · Opus 4.8 · Fable v1.0 — adjudicated §13; full texts in git history and `FableXBRLIntegrationDesign.md`). This is the concrete form of the pending **Codex §4.8 "report processing scope"** decision; on ratification it **ACTIVATES the dormant `09 §10` xbrl_link rider** as pinned below. Scope: 10-K / 10-Q (and /A) only. Authority unchanged: `01–09` + `10` + `12` + `95` + kernel v3.4 win on any conflict. **This document was adversarially audited by a six-lens agent pass (kernel · record-model · pipeline · edge-case · minimalism · requirements; 45 findings) and every finding is dispositioned in the text below and recorded in §13.** Graph counts anywhere are illustrative — **re-read from Neo4j at implementation time (P19)**.
>
> **Tags:** `[covered]` already in locked docs/design (cited) · `[pin PN]` newly pinned here (ratified via §11) · `[exp]` experiment-gated knob with a stated default. Every important rule carries exactly one tag; where a sentence cites locked ground *and* adds a delta, the citation and the delta are tagged separately.

---

## 0. Required outputs

**0.1 One-sentence final design.** Text remains the only path that creates Drivers and all narrative facts; a deterministic materializer turns each 10-K/10-Q's own, entity-scoped XBRL facts into exact numeric metric DriverUpdates for safely concept-linked metric drivers (Driver→concept only, strong-tier-confirmed once per company, revocable by cohort); same-event duplicates die by head-scoped id equality under a declared, fixed GAAP-family fold plus a value-compatibility gate; every mismatch falls to the safe over-split, measured by a tripwire and repairable by state-based parks; and the v3.4 admission kernel's behavior is untouched.

**0.2 Key design choice.** Meaning enters once per (company, metric driver) through the locked `08` concept-link judge with a strong-tier final verify; after that single judged link every fact is pure code. Text mints and narrates; XBRL fills numeric series; the code-built id is the dedup boundary; menus narrow choices but only evidence creates facts.

**0.3 Main risk.** A wrong (company, driver)→concept resolution mass-produces a wrong exact-looking series. Countered by: precision-max linking (strong-tier verify **locked** per kernel §11.0 — P9; XC-16 hierarchy veto + qualifier veto as hard gates), full per-fact provenance (`attached_via`, `xbrl_fact_id`), one-flip cohort revocation with audit events and **state-based parks that re-enqueue on revocation**, and the model-free falsifier + XC-17 monitors — a *missed* link now costs ~nothing (text covers it), so the linker is re-balanced all the way toward precision.

**0.4 Next step.** Owner ratifies §11 + §12.3 (one bundle) as the Codex §4.8 decision → XC-16 + full-universe concept run (pre-gate) → build `xbrl_link_writer` as Track B §17 step 9b → §9 proofs on one industry (a 52/53-week filer mandatory in the fixture set) → flag-on rollout industry-by-industry.

**0.5 Lock-readiness verdict.** **Lockable now, as a bundle:** the design contradicts no locked rule *silently* — every rule it touches is enumerated in §12.3 (ten additive amendments: carve-outs, extensions, and one read-bucket token extension; zero reversals) and ratified together with the pins. Remaining open knobs are `[exp]` with safe defaults; none blocking. What changed from the pre-audit draft and from Pass 1 is recorded in §12.2/§13.

---

## 1. Context — what exists (verified, not remembered)

**Driver/DriverUpdate (locked):** Driver = class (`name + fact_type + SAME_AS/BASE_METRIC + evidence`); everything company/time-specific lives on the fact (`PIPE-02/03`, `DU-02`). Fact id = `event + driver + fact_scope(period|slice|measurement)`, code-built, producer-free, immutable (`FS-01/02`). Kernel v3.4: blind propose → G2 router → born-complete CREATE → Track B writer + validators; CLAIM ships OFF; async LINK sweep; model-free falsifier; edge-state recovery; §11.0 model-tiering lock. Track B (`12`) build-ready: writer (no-null-clobber + the `--repair` deliberate-clear lane, FACT-14), period resolver with **exact-date input first in routing** (FACT-18) + the SEC quarter cache (Step B) + existing-period lookup (Step A), unit resolver, `slice_menu` (frozen axis table FS-11/12, hex sentinel FS-15, elimination guard FS-20), `concept_link` (`08`: guards → PIT company menu → pick → adversarial verify → deterministic backstop/veto; resolve once per (company, base-metric driver), XC-18; ~100% precision / ~70% recall on the 274-company validation), read views with source-rank collapse `{8k:0, transcript:1, 10q:2, 10k:3, news:4}` and OD-14 read-derived guidance movement.

**XBRL substrate (in Neo4j):** `Report → HAS_XBRL → XBRLNode ← REPORTS ← Fact`, with `Fact → HAS_CONCEPT → Concept` (qname, balance, period_type) · `HAS_PERIOD → Period` (exact instant/duration dates; instants store `end_date='null'` string) · `HAS_UNIT → Unit` (common types: `iso4217:USD`, `shares`, `pure`, **`iso4217:USD/shares`** for per-share amounts, plus other currencies/custom units) · `FACT_DIMENSION → Dimension` (axis) + `FACT_MEMBER → Member` · `IN_CONTEXT → Context → FOR_COMPANY` — **entity binding lives on the Context, not the Report**: a Report's fact set is NOT company-scoped (multi-registrant filings exist), and a small cohort of Facts has no `IN_CONTEXT` edge at all. 10-K/10-Q (+/A) only — **8-K never has XBRL**. Deterministic quirks: string booleans; raw duplicate facts; comma-formatted values; `decimals` = precision metadata (values `'0'–'6'`, negatives, `'INF'`, the string `'null'`), never a multiplier.

**Pre-built hooks:** `09 §10` dormant rider · Codex §4.8 (the decision this file makes) · FACT-18 exact-date branch · `03`'s frozen member→slice machinery · kernel §9's falsifier, which already treats concept links as its one model-independent oracle.

## 2. Problem statement

A 10-K/10-Q states the same market-relevant information twice — once as tagged XBRL facts (exact values, periods, units, dimensions; zero LLM needed) and once as narrative text (causal attribution, qualitative readings, occasional guidance, litigation; LLM required) — and the pre-Pass-2 plan routed all of it through LLM re-extraction: full token cost, transcription/period/scale error injected into the highest-precision data owned, the multi-million-fact XBRL asset used only as decoration. The design must decide, fact by fact, the single source of truth, so XBRL-covered facts are reused not re-extracted, non-XBRL market-moving facts are still captured, the two lanes never write the same fact twice, and Driver identity is untouched.

## 3. The boundary is the fact — and what "XBRL-covered" means, exactly

Section-level routing is provably invalid in both directions: one MD&A paragraph holds a tagged revenue number and an untagged capex-outlook sentence; the Item-8 notes hold tagged tables and untagged litigation prose. `[covered — FablePromptv2 §5, confirmed]`

**Definition (Pass-1 Q14) `[pin — the routing conjunction of P3/P4/P8, restated]`. A fact is *XBRL-covered* iff ALL of:** (1) its value is carried by an XBRL Fact **inside this filing, entity-scoped to this registrant** (P4f); (2) that Fact's concept has an **active** stored resolution to an admitted, non-latent **metric** driver for this company; (3) its measurement is inside the fixed GAAP-family fold (∅/gaap/reported/as_reported, or the linked concept's own Basic/Diluted variant — P3); (4) every axis on the Fact is representable (SLICE_AXES kind or the unknown-axis hex sentinel); (5) its unit is on the v1 whitelist (P4c). Everything else is text-lane territory:

| 10-K/10-Q content | Lane | Why |
|---|---|---|
| Statement lines + dimensional breakdowns (GAAP actuals) | **XBRL** | tagged exactly; the metric lane's numeric levels |
| Restatements, /A amendments | **XBRL** | value-change rule (P4b) |
| Non-GAAP/adjusted/cc numbers; per-X variants; unlinked KPIs | text | G2 guard abstains; different identity |
| Qualitative readings; causal attribution ("driven by X") | text | usually its OWN driver |
| Guidance in MD&A; stated expectation comparisons; actions/litigation/subsequent events | text | XBRL is actuals-only; `XC-12`/`MF-10` drew this exact line |
| XBRL facts of concepts with **no** admitted driver | **XBRL-ignored** (deliberate) | market language mints causes; code never does (the anti-flood rule) |

`[covered]` The deep alignment: XBRL covers exactly the `metric` lane's numeric levels — the boundary MF-10/XC-12 drew years earlier.

## 4. Adjudication of the three Pass-1 candidates

All three converged on the identical core (fact-level routing · rider activation · deterministic XBRL producer for linked metric drivers · text keeps narrative · kernel untouched) — the architecture is confirmed by independent convergence; differences were hardening. **Grafted:** GPT's qualifier-concept catch — as a **refuse-veto**, not a measurement stamp (P9b); GPT's raw `xbrl_fact_id` provenance (P7); Opus's code-diff determinism proof (X-XL0) and flag-on → industry-by-industry rollout; Opus's prompt-narrowing **as a cost experiment only, never the correctness guarantee** (P17 `[exp]`). **Rejected (recorded §12.1):** GPT's driver-admission-from-XBRL and per-fact "hybrid" without ownership rules; Opus's same-node field-precedence merge and concept-label CREATE door.

## 5. The design

### 5.1 Division of labor `[covered — Pass 1, unchanged]`

```
                    10-K / 10-Q filing event
                    ┌───────────────────────┐
                    │  narrative sections    │──► blind text producer ──► v3.4 kernel (G2…) ──► Drivers (all 4 fact_types)
                    │  (MD&A, risks, notes)  │                             └─► Track B writer ──► text DriverUpdates
                    │                        │                                     ▲ skip: head-scoped id equality (folded)
                    │  XBRL Facts (tagged)   │──► xbrl_link materializer ──────────┘ + value gate, vs same-event xbrl facts
                    └───────────────────────┘        (pure code; requires a stored ACTIVE
                                                      (company, driver)→concept resolution)
```

- **Driver creation (Pass-1 Q7):** a Driver can be born from a 10-K/10-Q — via its **text**, through the unchanged kernel. The XBRL lane never proposes names, never routes G1/G2, never touches SAME_AS; direction is Driver→concept only. `[covered]`
- **Order (Pass-1 Q9) `[pin P5a]`:** per filing event — materialize first, text second. Filings without usable XBRL (`xbrl_status ≠ COMPLETED`) run text unsuppressed; text is never blocked globally.
- **Text's remaining job (Pass-1 Q5):** every text row of §3, plus being the only lane for 8-K/transcript/news forever.
- The materializer is a registered Track-B producer (`xbrl_link_writer`, DU-02 contract) writing ordinary DriverUpdates through the same writer/validators — no parallel fact system; raw `Fact` nodes stay substrate. `[covered]`
- **Store-when-stated holds:** an XBRL fact *is* the company stating a value. No Q4=FY−3Q derivation, no auto-surprise, no presentation-label sign games (values stored as tagged, algebraic on the concept's axis — OD-12). `[covered]`

### 5.2 The materializer — recipe (all code, zero LLM per fact)

Per Report `R` (10-K/10-Q/10-K-A/10-Q-A, `xbrl_status=COMPLETED`), **per registrant `C` with active resolutions** (a multi-registrant filing runs once per such registrant):

1. **Load ACTIVE resolutions** `(C, metric driver d) → qname q` (P8). Full catalog records only — **latent bases excluded** `[pin P4e]` (a latent base is not a record; fact-bearing invisible drivers are forbidden; it becomes eligible the moment it graduates to a real record, the existing automatic path).
2. **Select Facts, entity-scoped `[pin P4f]`:** Facts in `R` with concept `q` AND `(f)-[:IN_CONTEXT]->(:Context)-[:FOR_COMPANY]->(C)`; a Fact with **no** `IN_CONTEXT` edge → skip + count (fail-closed). Filters: `is_numeric='1'`, `is_nil='0'`.
3. **Units — explicit v1 whitelist + map `[pin P4c]`:** `iso4217:USD` → money on the driver's canonical scale (OD-10) · `shares` → count · `iso4217:USD/shares` → usd (per-share level; the per-X lives in the driver name per NAME-13/UNIT-08 — so EPS facts ARE materialized) · **everything else** (`pure`, other iso4217 currencies, utr/custom units, other divide units) → **skip + count** in v1; enablement per class after a calibration census `[exp]`. (The `pure`→percent ×100 transform is a value rewrite with a fraction-vs-multiple ambiguity — fenced out.)
4. **Intra-filing dedupe + collision rule `[pin P4g]`:** first drop raw duplicates (identical concept+context+value). Then group the surviving items by fact_scope: values agreeing within the coarser fact's stated `decimals` precision → keep the highest-precision Fact, count the rest; **values disagreeing beyond stated precision → skip the whole scope + log `xbrl_internal_conflict`** (fail-closed; never fuse, never last-write-wins). X-XL0 diffs against the surviving Fact.
5. **Axes (never drop a part — FS-09):** every `(Dimension, Member)` classifies by the frozen table `[covered — FS-11/12/15/18/20]`: SLICE_AXES → `kind:normalized_member_label` (the same FS-18 normalizer the slice menu uses); unknown axis → `unknown:xbrlaxis_<hex>__<value>` provisional sentinel; **any NON_SLICE axis or HARD-EXCLUDE elimination member → skip the whole fact, logged** `[pin P4d]`.
6. **Period:** §5.3.
7. **Id:** `du:{R.source_id}:{d}:{fact_scope}` — the standard recipe. `[covered]`
8. **Primary vs non-primary `[pin P4b]`:** **primary ⇔ the Fact's period end date == `R.periodOfReport`** (durations and instants alike; a 10-Q's quarter and YTD windows both end there) → always write. Everything else (prior-year comparatives end earlier; subsequent-event instants end later) → write **only if** no fact with identical fact_scope exists in the series (backfill) **or** its canonical value differs from the stored one (**a restatement — the market-relevant case**). Identical-value re-tags skipped + counted. `periodOfReport` null (a known small cohort) → derive it as the max duration-period end among `R`'s own facts; none → skip the report + count (fail-closed) `[pin P4h]`.
9. **Write** via `driver_writer`, atomic, all FACT-16 validators running; the item carries `level_shape_hint='point'` (satisfying FACT-16 rule 5 with no carve-out) `[pin P4i]`:

| Field | Value (all code) | Tag |
|---|---|---|
| `origin` | `xbrl_link` (null=llm stays retro-correct) | [covered — rider] |
| `level_low = level_high` | the exact signed value parsed from `f.value`, converted to the driver's canonical scale (OD-10); `decimals` recorded as precision metadata only | [pin P4a] |
| `level_unit` / `series_unit` | per the P4c map; series axis per OD-10 | [covered] |
| `change_* / comparison_* / value_text / conditions / company_confirmed` | null / FORBID — XBRL states levels only; deltas derive at read | [covered] |
| `driver_state` | `reported` — polarity-free; direction is read-derived (§5.8) | [covered — rider; matrix legality via P10] |
| `quote` | `[XBRL] <qname> <period> = <scaled value>` — the only quote that exactly matches its stored value | [covered — rider] |
| `measurement` | **always ∅** (as-reported) — no variant stamping; dedupe/series behavior via the P3 fold | [pin P3] |
| `date` / `created` / `source_type` | `R.created` (public filing time — PIT) / write time / `10q`\|`10k` | [covered] |
| edges | `OF_DRIVER→d` · `FROM_SOURCE→R` · `HAS_PERIOD` · `MAPS_TO_CONCEPT` + `xbrl_qname` (origin-gated write-time carve-out; LLM producers stay FORBID) · `MAPS_TO_MEMBER` + `slice_part` | [pin P10] |
| provenance | `attach_mode='xbrl_link'` · `attached_via=resolution_id` · `xbrl_fact_id` (raw source Fact id) | [pin P7] |

A **QUARANTINED** target driver → PARK-RETRY (the kernel's exact-ATTACH rule, applied verbatim). **CLAIM_FROZEN does NOT block materialization** — the kernel blocks writes only for QUARANTINED nodes; CLAIM_FROZEN is a claim-eligibility/feature de-mint, and the text lane keeps writing to frozen cards, so lane symmetry is preserved. `[covered — kernel §9.2/§6.5; corrects the pre-audit draft]`

**PIT:** structural for content — the materializer reads only Facts inside `R`; no future taxonomy or values can leak. One declared judgment-level exception to XC-09's letter `[pin P8d]`: a stored resolution's pick was made against a resolution-time menu, then applied to earlier filings during backfill. No structural leak is possible (the concept must exist *inside each source filing* to materialize, and the value/period/unit come from that filing alone); the pick's judgment is additionally era-guarded — a linked driver finding zero facts for `q` in an era triggers a code-driven era re-resolution with the same recipe. Declared, justified, monitored by the resolution audits.

**Volume guards (Pass-1 Q13), all above:** driver-linked concepts only (XBRL-ignored is the big filter) · primary-always / non-primary-on-change · NON_SLICE + elimination skips · latent exclusion · unit whitelist · intra-filing collision rule. Every skip counted, nothing silent.

### 5.3 Periods — deterministic conversion (brief #4; Pass-1 Q25)

| Output | Rule | Tag |
|---|---|---|
| `gp` id | duration → exact-date branch → `gp_<start>_<end>`; instant → `gp_<d>_<d>` (`start_date`; the `end_date='null'` quirk) | [covered — FACT-18] |
| `time_type` | from `Period.period_type` verbatim | [covered] |
| `fiscal_year/quarter` | `fiscal_math.period_to_fiscal(window, FYE)` — the same module both lanes share. Instant off a fiscal boundary → **null, never guessed**; annual → quarter null | [pin P14a] |
| `period_scope` | the **shared deterministic classifier** (below) | [pin P14] |
| Sentinels | impossible on this lane — real dates only; a sentinel on an xbrl_link fact hard-fails | [pin P14b] |
| Amendments | same real windows → same `gp` ids; facts dated at the /A's public time (OD-14); P4b captures deltas | [covered] |

**The classifier `[pin P14]` — one authority for BOTH lanes on dated windows.** Home: inside the FACT-18 resolver wrapper as an exact-date-branch derivation (a declared FACT-18/17b extension, §12.3): for any resolved dated window, `period_scope` is **code-derived from the dates** — producer-supplied scope is accepted only for sentinel/dateless periods (consistent with FACT-17b's "derived fields are recomputed" law). Rules, computed against the **company's ACTUAL fiscal-period ends** — anchored on its own XBRL Period history / the SEC quarter cache (resolver Steps A/B) with FYE-month arithmetic only as the fallback, which is what makes **52/53-week filers** converge (their true 13/14-week windows, not month-math approximations) `[pin P14c]`:

- window == one actual fiscal quarter → `quarter` (**quarter wins over Q1-YTD** — same window, one scope, no split series);
- fiscal-year-start-anchored multi-quarter window → `ytd` (so text "first-half revenue" resolved to the FY-start 6-month window is `ytd`, converging with the 10-Q's tagged 6-month fact);
- non-FY-start-anchored two-quarter window → `half` (the genuine H2 case — kept in the enum's meaning);
- FY-aligned annual window (364/371-day aware) → `annual`; rolling ~12m ending on an actual quarter boundary → `ttm`; ~1 month → `monthly`;
- anything odd (stubs, transition periods, residuals) → **`exact_range` + WARN** — fail-closed to the catch-all, never a guessed label.
- **Instants → `period_scope = null`** (`time_type=instant` separates them in the series key) — the FACT-16.17 instant carve-out (§12.3).

### 5.4 Normal-order duplicates (brief #1) — XBRL stays clean

**No-enrichment rule `[pin P1a]`:** when XBRL wrote first and text later states the same numeric fact, the text twin is **skipped whole** — the xbrl node never gains prose, state, or stated change. Enrichment can't reach consistency (only headline numbers get prose twins → three fact flavors), a rounded quote on an exact node is internal inconsistency, no renderer/comparator reads quotes on numeric facts, and the causal half of such sentences becomes its **own driver's fact**. Text context stays reachable via same-event reads (`FROM_SOURCE`) and sibling facts. `[covered — Pass 1 + conversation lock]`

**The skip test (code, in `driver_write_cli`, post-fusion) — a text item is skipped iff ALL of:**

1. same `source_id` (one CLI invocation = one event) `[covered]`;
2. same **HEAD** — committed, non-quarantined SAME_AS union head (PIPE-35's locked one-hop read; variant-anchored storage legally puts text on differently-worded nodes) — **and the skip-log entry records the crossing SAME_AS edge id(s)** so a later quarantine of any recorded edge re-opens the skip (P8c′) `[pin P5b]`;
3. identical `period_u_id` and code-sorted slice set `[covered]`;
4. **measurement inside the declared fold `[pin P3]`:** the text token set ⊆ {∅, gaap, reported, as_reported} ∪ {the linked concept's own qname variant token — Basic/Diluted only, read deterministically from the qname}. This fold is **also applied at READ time as the rider-3 bucket's declared extension** (§12.3): where one side is `origin=xbrl_link`, the same token set groups into one series — so bare "EPS" (∅, 8-K), "diluted EPS" ({diluted}, text) and the Diluted-concept xbrl fact (∅) form ONE series with a working restatement chain. It is deliberately a **fixed 6-token, xbrl-side-only equivalence** in the rider's own `empty≡{gaap}` precedent — not open-vocabulary write-time synonym merging (OD-9's ban targets open-ended label aliasing; this is a closed, concept-anchored, value-gated family, declared as an amendment, stored ids never change);
5. **value gate `[pin P5c]`:** the text value matches the xbrl value within the text's own stated precision (half-ULP of its least significant digit, post-canonicalization). Compatible → **skip, logged with the deferred-to fact id + crossing edge ids**.

Same id (or folded identity) with an **incompatible value** → **park `xbrl_conflict` — STATE-BASED, flagged as a falsifier exhibit** `[pin P5d]`: the park is keyed to (resolution state, recorded SAME_AS edge states) and **auto-re-enqueues through the writer when the resolution is revoked or a recorded edge is quarantined** — the kernel's L2 repairability doctrine (state-based refusals never permanent); it becomes TERMINAL-counted only after graders re-confirm the resolution correct. Writer backstop `[pin P5e]`: an `origin=llm` write physically arriving at an existing xbrl id is a suppression-miss bug → REJECT + park `duplicate_of_xbrl`, **same state-based re-enqueue keying** — this is what makes "rounded never overwrites exact" structural.

**What the skip consciously discards:** the twin's stated "+12%"/prior-year comparison (read-derivable exactly) and its narrative quote (evidence ≈ zero next to the tag). Revisit trigger parked (§12.2). `[covered]`

**Cross-event "duplication" is the designed restatement chain** (different events, different ids; same-day rank collapse; latest-event-wins) — with two honest qualifications the pre-audit draft lacked: **(a)** the exact-beats-rounded upgrade happens when the 10-Q lands on a **later trade date** than the 8-K (the common case); a **same-day** 8-K + 10-Q pair keeps the 8-K print as that period's current view — `09 §6.9`'s own conscious acceptance, unchanged here `[covered]`; **(b)** within one event and one (union) series, where every locked tie-break ties, **`origin=xbrl_link` outranks `origin=llm` at collapse** — a read-time tie-break addendum to 09 §6.9, no stored rank slot (rider item 5 closed: P2) `[pin P2]`.

**Pass-1 Q1 (no paragraph map needed):** the reader stays blind and exhaustive; coverage is decided per extracted item by the skip test. Input-side trimming (statement-table artifacts are XBRL renderings) is a cost knob `[exp — §10]`, never a correctness dependency.

### 5.5 Reverse-order upgrade (brief #2) — audit-safe, lossless, no-human

When text wrote first (§5.7 lifecycle) and materialization later reaches the **same id**:

- **Value-compatible → in-place upgrade** to the canonical xbrl rendition (exact level, `[XBRL]` quote, `reported`, ∅ measurement, origin/provenance flip, stated `change_*/comparison_*` cleared) — node-level end state **byte-identical to the normal-order outcome**. The clear runs through **FACT-14's existing repair-grade lane** (the one lawful door for deliberate clears). `[pin P11a]`
- Same atomic tx emits an immutable **`UpgradeEvent`** — a distinct audit-event type, deliberately NOT a `RecoveryEvent` (kernel §10.5 defines RecoveryEvent as detector + two grader memos for mutation-free, edge-state recovery; the upgrade is a grader-free, deterministic FACT-14-lane action, so it gets its own event type and the kernel's V14 invariant stays intact) — carrying the **complete prior producer payload** (all producer-written fields + quote + state + origin + attach provenance), new values, `resolution_id`, trigger, timestamp. **No `prior_quote`/`prior_origin` fields on DriverUpdates**; no ephemeral sidecar as the system of record. `[pin P11b — corrects the pre-audit draft's RecoveryEvent reuse]`
- **Structural enforcement:** a new Track-B **writer validator** (not a kernel-V14 extension): any `origin` flip `llm→xbrl_link` must have exactly one matching UpgradeEvent, else hard-fail; no-op re-runs emit nothing. `[pin P11c]`
- **Reversal:** re-apply the archived payload through the same repair lane on 2-strong-grader confirmation, emitting a counter-event. Lossless both directions, zero humans. `[pin P11d]`
- **Value-incompatible → the written fact is never destroyed by automation:** the xbrl item parks `xbrl_conflict` (state-based, P5d), pair flagged to the standing grader lane. `[pin P11e]`
- **Scoped honesty on order-independence `[pin P11f]`:** same-id facts converge byte-identically. A **fold-equivalent** twin written first (text `{diluted}` fact, then the ∅ xbrl fact — different ids) is NOT retro-skipped: both persist in storage, and they converge **at read** through the P3 read-bucket (one series) + the P2 intra-event origin tie-break (xbrl renders as current) — the kernel's own absorb-at-read posture. Storage differs by arrival order; the rendered view does not. §8 lists this plainly.

### 5.6 Slice mismatch (brief #3) — FS-14/15/16 govern; one tripwire added

Text picks slices from the PIT menu — built from the **same XBRL members through the same normalizer** the materializer uses, so exact convergence is the engineered common case. `[covered — FS-14/15/16]` When text still diverges:

| Bucket | Case | Path |
|---|---|---|
| **1 — auto-converged** | menu pick, same label | byte-identical `kind:value` → skipped at write |
| **2 — caught/visible** | pick of an old-label menu row for a renamed member (same member qname) | both facts carry `MAPS_TO_MEMBER` to the same (axis, member qname) → **T12.9 groups the labels at display** (one segment heading, latest label); the two value rows remain distinct series rows (T12.9 is display-layer grouping, not collapse) — a **visible, grouped over-split**, fired on by the tripwire `[covered — FACT-35, honestly scoped; corrects the pre-audit draft's "collapse dedups" claim]` |
| | sliced number mis-written as consolidated | id collides with the consolidated xbrl fact → value gate → `xbrl_conflict` park |
| | XBRL-side NON_SLICE/elimination/unknown-axis skips | logged counters, offline re-vet cadence (ISS-15 pattern) |
| **3 — safe over-split, kept** | coined near-variant (`product:iphones`) or unwarranted `unknown:` despite a menu row | no member link on the coined side → T12.9 cannot group; FS-18 folds exact-only; alias layer owner-rejected → **a persistent within-company split, safe direction — no repair lane exists today, stated plainly** |
| | wrong-axis pick / member qname changed on rename / dropped part of multi-part slice | genuinely different identity strings; rare; tripwire-visible |

**The tripwire `[pin P13]`:** at text-write time — same event + same head + value-compatible level + **exactly one scope component differs (slice OR period; measurement-diff excluded — a non-folding measurement is a legitimately different fact)** → log **`xbrl_twin_suspect{component}`** with both ids. No park, no snap, no id change. It (i) makes the silent over-split channels measurable, (ii) **gates rollout**: `twin_suspect_rate` is a §9 acceptance metric `[exp — bar pre-registered from the X-XL2 calibration run]`, (iii) feeds the offline re-vet and the falsifier's exhibit stream.

### 5.7 Resolution lifecycle (brief #5, #6)

**The record `[pin P8]`:** reify XC-18's store: `ConceptResolution{resolution_id, company, driver, qname, method, model_id, menu_sha, date, state ∈ {active, revoked}}` — `method/model_id/menu_sha` are read by the risk-stratified resolution re-verification and by revocation graders to reproduce the original pick context (named readers). Every materialized fact stamps `attached_via=resolution_id` + `xbrl_fact_id`.

- **Creation:** on metric-driver admission (born-complete) or first-need per company — the locked `08` recipe: guards → PIT menu → pick (cheap tier allowed) → **adversarial verify at the strong-judge tier — LOCKED**: a materialization-grade resolution is a semi-permanent, mass-consequence confirmation, squarely inside kernel §11.0's "cheap tier may never be the final confirmer" rule; only tier *membership* (which model is the strong judge) stays experiment-gated, per §11.0 itself `[pin P9 — corrects the pre-audit draft's [exp] gating]` → deterministic backstops A–D → **XC-16 calc-hierarchy veto** (hard pre-gate) `[covered]` → **qualifier veto**: a candidate qname carrying adjusted/organic/pro-forma-class qualifier tokens is refused outright `[pin P9b]`. Abstain-biased; an abstain costs nothing.
- **Detection of wrong links (Pass-1 Q26):** falsifier (i) same-company multi-concept and (iii) the duplicate oracle (both get denser food), XC-17 signature sampling, the `xbrl_conflict` park stream (direct disagreement evidence), risk-stratified sampled audits (kernel §9.5 budget). Graders see **raw evidence only** — quotes, ids, concepts, values — never the detector's conclusion (smoke-alarm doctrine). `[covered]`
- **Revocation:** 2 independent strong-tier graders → `state=revoked` + RecoveryEvent → **reads exclude the whole cohort by `attached_via` through read-time indirection** (facts never stamped/moved/rewritten — the read-union-excludes-quarantined-edges shape). New materialization stops; **enrichment consumes active resolutions only**. `[pin P8a]`
- **Wrong revocation:** flip back + counter-RecoveryEvent; facts reappear instantly (nothing was replayed). Un-revoke = loosening → same 2-grader bar on new evidence, never timer-based. `[pin P8b]`
- **Gap repair `[pin P8c]`, trigger set now complete:** on **resolution revocation** OR **quarantine of a SAME_AS edge recorded in skip-log entries (P5b)**, the affected parked items (`xbrl_conflict`/`duplicate_of_xbrl`) auto-re-enqueue and the skip log bounds targeted text re-extraction for the affected scopes/variants — so neither a revoked cohort nor a split-off variant is left with an unrepairable series hole. Safe direction meanwhile (a gap under-attributes, never lies), fully visible (RecoveryEvent + skip log).
- **New-driver lifecycle (brief #6):** text mints the driver and **writes its facts immediately — no market-moving text fact ever waits on XBRL** `[pin P12]`; resolution creation **enqueues `materialize(company, driver, all filings incl. the current one)`** (the kernel's on-create-enqueue pattern); §5.5 reconciles same-id facts; fold-equivalent twins converge at read (P11f). Lag affects series depth only, never event coverage.

### 5.8 Read layer (brief #7, #8; Pass-1 Q11, Q19, Q28, Q29)

The design deliberately relies on read-time assembly (Q11): stored facts stay honest per origin; **consistency is a read-boundary guarantee** ("same rendered interface, not same stored shape").

- **`effective_driver_state` `[pin P15]`** — one field on all metric facts in read views: **stored** state when the producer stated one (never overridden) · **derived** when stored is `reported`, with the comparator found by **DriverPeriod date arithmetic, never raw fiscal-field equality** (PER-13's law): the collapsed fact in the same series whose window end is ≈1 year before this fact's end (±7-day tolerance for 52/53-week calendars) for `quarter`/`ytd` scopes; the prior collapsed `annual` fact for annual scope · **fallback `reported`** whenever the comparator is missing or ambiguous (transition years, first linked year, no prior) — fail-closed, never guessed; restated priors compare against the collapsed (latest-event-wins) value · instants stay `reported` `[exp]`. Never written back — OD-14's pattern verbatim.
- **Read bucket:** `empty≡{gaap}` extended to the P3 token family, xbrl-side-only (§5.4.4; declared §12.3). `[pin P3]`
- **Actual-vs-guidance (Q28/Q29) `[covered]`:** an xbrl fact is an ordinary metric fact on the base driver — the existing family read (`revenue_guidance → BASE_METRIC → revenue` → collapsed series) uses it as the actual side with nothing new, and better: exact values, native qname + fiscal-frame join keys (PIPE-29), a guaranteed comparator every period **for non-latent linked bases** (latent bases stay excluded until they graduate — MF-05's "only ever forecast" case keeps no actual, honestly). Measurement compatibility rules unchanged.
- **Surprise coexistence `[covered]`:** a text `*_surprise` fact lives on a different driver → different id; surprise drivers have no resolutions → the xbrl lane can never write, suppress, or touch them; the derived comparison is never stored. Stored producer judgment and derived arithmetic may disagree — OD-13's designed posture, logged, both visible. **Two non-rules, restated: no auto-surprise** (ISS-16's trigger is a *stated* comparison in the source, never a read-back of graph state) **and no stored derived comparison** (DU-16.6).
- Verdicts (`EXPLAINED_BY`) are producer judgments; xbrl facts are eligible targets like any fact. `[covered]`

### 5.9 XBRL-learned menus beyond 10-K/10-Q (brief #9; Pass-1 Q30)

Already the locked design for slices (FS-14: 8-K/transcript/news menus come from the 10-Q/10-K member union, PIT-cut); concept reuse happens at the enrichment layer (XC-18), never as producer input (PIPE-21).

**The invariant `[pin P16]`: a menu may narrow a choice; only evidence may create a fact** — evidence = a source quote (text) or an in-filing XBRL Fact (materializer). Enforced structurally, five ways: quote-required validator · FS-16 no-near-snap · the materializer's in-filing gate (no menu→fact code path exists anywhere) · PIPE-21 (producers never see or emit concept data) · kernel blindness (cards never show XBRL; P6 keeps resolutions/facts out of claim-standing). Boundary: **never extend hints to values or scales** — the in-context-teaching pattern the kernel already rejected.

## 6. Kernel fit — behavior unchanged; every touched rule declared

The xbrl lane never enters Stages 0–2 (no candidate, no router, no CLAIM). It is Track-B writer traffic under a standing meaning judgment — **ATTACH-once-then-materialize** (XC-18's shape); its audit analogue = resolution re-verification + XC-17 + the falsifier. `[covered]`

1. **P6 — eligibility isolation `[pin P6]`:** `origin=xbrl_link` facts and ConceptResolutions **never count toward kernel §6.5's ≥K-distinct-companies BROAD count nor toward ESTABLISHED evidence** — eligibility evidence remains text quotes from distinct primary filing/earnings events (the kernel's own wording). This is a declared one-line amendment to §6.5 (§12.3) so the pin has a landing place.
2. **P7 — provenance:** `attach_mode` gains `xbrl_link`; `attached_via`'s legal values gain resolution-ids for this origin; `xbrl_fact_id` added — declared V9/§10.1 wording amendment (§12.3). `[pin P7]`
3. **Quarantine interplay:** QUARANTINED blocks (park-RETRY) `[covered]`; CLAIM_FROZEN does not block either lane (§5.2).
4. **Falsifier scoping `[pin P4j]`:** signal (iv) periodicity-coherence runs over `origin≠xbrl_link` facts only — code-manufactured recurrence must not silence the one-off detector; a declared §9.1(iv) scoping note (§12.3).

Synergies, accurately stated: falsifier **(i)/(iii)** get dense exact concept/period data (the falsifier is v3.4's only independent oracle and a launch blocker — this feeds it); numeric series the learner grades become exact. Materialization does **not** alter the §15.0 MVP coverage obligation (falsifier (v) timing unaffected).

## 7. Duplicate & miss ledger — every channel, its guard

| Channel | Guard | Tag |
|---|---|---|
| Text twin, same event, same/folded identity | head-scoped skip + fold + value gate | [pin P5/P3] |
| Same identity, incompatible value | `xbrl_conflict` state-based park + flag | [pin P5d] |
| llm write physically at an xbrl id | writer REJECT → `duplicate_of_xbrl` state-based park | [pin P5e] |
| Reverse-order same id | upgrade-on-compatible + UpgradeEvent / park-on-conflict | [pin P11] |
| Reverse-order **fold-equivalent** twin (different id) | persists in storage; converges at read (P3 bucket + P2 tie-break) | [pin P11f] |
| Two XBRL Facts, same scope, rounding-variant values | intra-filing collision rule (keep highest precision / skip + `xbrl_internal_conflict`) | [pin P4g] |
| Another registrant's facts in a combined filing | entity-scoping filter; no-context Facts skipped | [pin P4f] |
| bare "EPS" / "diluted EPS" vs Diluted-concept fact | P3 fold (skip + read bucket) + value gate | [pin P3] |
| "basic EPS" vs Diluted-concept fact | never folds → writes freely (correct) | [pin P3] |
| Divergent period window | **persistent split** (no period-grouping mechanism exists — stated plainly), safe direction; shrunk by P14c actual-calendar anchoring; measured by `xbrl_twin_suspect{period}` + X-XL1 | [pin P13/P14c] |
| Coined near-variant slice | persistent split, safe; tripwire-measured; no repair lane (honest) | [pin P13 + §8] |
| Renamed member, same qname | T12.9 display-grouping; rows stay split; tripwire fires | [covered, scoped] |
| Adjusted/cc/per-X text facts | different identity — never suppressed | [covered] |
| 8-K print vs later-day 10-Q | designed restatement chain: exact supersedes | [covered] |
| 8-K + 10-Q **same trade date** | 8-K print keeps the day (09 §6.9's conscious acceptance, unchanged) | [covered — honest] |
| Comparative re-tags each filing | identical-value skip; value-change = restatement captured | [pin P4b] |
| Raw XBRL duplicates | substrate dedupe | [pin P4g] |
| Two drivers sharing one concept | falsifier (iii) duplicate oracle — denser | [covered] |
| **Miss:** narrative/guidance/action/non-GAAP | text lane unchanged, full coverage | [covered] |
| **Miss:** unlinked concept (~30% abstain) | text writes it; demand-driven backfill on later admission | [covered] |
| **Miss:** latent bases, NON_SLICE/unit/no-context skips | logged + counted, re-vet cadence | [pin P4] |
| **Miss:** revoked-cohort or split-variant history gap | P8c trigger set (revocation + recorded-edge quarantine) re-enqueues parks + bounds re-extraction | [pin P8c] |

## 8. Impossibility statements — where 100% is not achievable, and the pinned fallback

1. **100% suppression hit-rate is impossible.** Fallback: every miss is an over-split absorbed or displayed by existing machinery (union/collapse/T12.9/tripwire) — no miss can over-merge or silently lose a fact; every executed skip is provably a duplicate (identity/fold + value).
2. **100% concept-link precision is not provable forever** (XC-15's own honesty). Fallback: abstain-bias + locked strong verify + XC-16 + qualifier veto; cohort revocation makes the residual reversible in one flip; monitors publish upper bounds.
3. **Coined-slice and divergent-period over-splits have no repair/grouping lane** (alias layer rejected; no period-group mechanism). Fallback: tripwire-measured, rollout-gated, safe direction; P14c shrinks the period class structurally. Inventing repair lanes would reopen rejected designs — declined.
4. **Order-independence holds at node level for same-id facts only.** Two acknowledged exceptions: the conflict branch (a written fact is never auto-destroyed — safety beats symmetry) and fold-equivalent twins (storage keeps both; the rendered view converges via P3+P2).
5. **The XBRL-ignored bucket is a conscious recall boundary** — a never-discussed line item is invisible until language names it. The catalog's philosophy, chosen not accidental.
6. **`pure`/exotic units are skipped in v1** (fraction-vs-multiple ambiguity). Text covers them; enablement is one `[exp]` census away.
7. **Same-day 8-K/10-Q pairs keep the rounded print** as that period's current view — a locked conscious acceptance (09 §6.9) this design honors rather than silently amends.

## 9. Minimal proof plan — before any live enablement

- **X-XL0 — determinism:** code-diff every materialized DriverUpdate against its **surviving** source Fact (value/scale, period dates, members→slice, unit, concept, entity). **Bar: 100%.** Fixtures must include: a multi-registrant filing, a null-`periodOfReport` report, an intra-filing precision-duplicate pair, a 52/53-week filer.
- **X-XL1 — twin fidelity:** N (company, driver, period) triples with both a text and an xbrl fact: value agreement; period-window id-equality rate; every divergence classified. **Bar ≥99% id equality on true twins**; 52/53-week filers mandatory in-sample.
- **X-XL2 — suppression + tripwire calibration:** suppression ON vs OFF over M 10-Qs: skip precision (**zero suppressed non-twins — hard zero**), `duplicate_of_xbrl`≈0, `xbrl_conflict`/`xbrl_internal_conflict` census, `twin_suspect_rate` measured → **the rollout bar is pre-registered from this run** `[exp]`.
- **X-XL3 — recall:** pre-registered sha-locked key (PIPE-37/OD-6 protocol) over K filings; (xbrl ∪ suppressed-text) coverage ≥ text-only baseline; **zero market-moving fact lost — hard zero**.
- **X-XL4 — cost (informational only, never gating):** tokens/filing + backfill, hybrid vs text-only; reported to owner.
- **Hard pre-gates (locked, load-bearing):** XC-16 + full-universe concept run · PIT menu proof (12 §12.4) · falsifier (iii) dry-run over a materialized sample · **fresh Neo4j census** (counts, edge wiring `FACT_MEMBER`/`FACT_DIMENSION`, unit-type inventory, no-context and null-periodOfReport cohort sizes — P19).
- **Rollout:** flag-on, one industry → industry-by-industry; each promotion gated on X-XL0–3 bars holding (X-XL4 excluded from gating).

## 10. Cost (Pass-1 Q2, honest)

Saved: the historical numeric backfill (LLM → code ≈ $0); per new filing, numeric-table extraction + its retry loop; statement-table artifacts need not feed the reader (XBRL renderings — verify provenance at build). Not saved: the narrative read — one LLM pass stays, because that is where non-XBRL market-movers live. Prompt-narrowing may cut output tokens `[exp — P17]`; correctness never depends on it. Cadence/priority of 10-K/10-Q text = part-2 knobs.

## 11. Ratification bundle — one yes/no covers P1–P17 and P19 (+ the §12.3 amendment list)

- **P1** Activate `09 §10` rider items 1–4 as written (origin · `[XBRL]` quote · `reported` state · exact windows · member→slice · full-producer validators). **P1a** normal-order no-enrichment.
- **P2** Rider item 5 closed: no new stored rank slot; **read-time tie-break addendum** — within one event and one series, `origin=xbrl_link` beats `origin=llm` at collapse.
- **P3** xbrl `measurement` always ∅; the **declared GAAP-family fold** — {∅, gaap, reported, as_reported} ∪ the linked concept's own Basic/Diluted token — applied in the skip test AND as the rider-3 read bucket's extension (xbrl-side-only, value-gated, fixed token set; stored ids never change); basic never folds against diluted.
- **P4** Materialization: **a** value = as-tagged signed exact, canonical scale, decimals=precision-only · **b** primary ⇔ period end == `periodOfReport`; non-primary on new-scope-or-value-change · **c** unit whitelist {USD→money, shares→count, USD/shares→usd-per-share}; all else skip+count `[exp enablement]` · **d** SLICE_AXES + hex sentinel; NON_SLICE/elimination → skip whole fact · **e** latent bases excluded · **f** entity-scoping via `IN_CONTEXT→FOR_COMPANY`; no-context Facts skip; multi-registrant = per-registrant runs · **g** intra-filing collision rule (highest-precision wins within rounding; beyond-rounding disagreement → skip + `xbrl_internal_conflict`) · **h** null-`periodOfReport` fallback (derive from max duration end, else skip report) · **i** `level_shape_hint='point'` on every item · **j** falsifier (iv) runs over `origin≠xbrl_link` only · plus: no Q4 derivation, no auto-surprise, raw-duplicate dedupe, `is_numeric='1'`/`is_nil='0'`.
- **P5** **a** materialize-before-text per event; no-XBRL filings unsuppressed · **b** head-scoped skip, crossing SAME_AS edge ids recorded in the skip log · **c** value-compatibility gate · **d** `xbrl_conflict` **state-based** park (re-enqueues on revocation/edge-quarantine; TERMINAL only after graders re-confirm) + falsifier exhibit · **e** writer REJECT backstop `duplicate_of_xbrl`, same state-based keying.
- **P6** xbrl facts/resolutions excluded from BROAD/ESTABLISHED eligibility evidence (kernel §6.5 amendment, §12.3).
- **P7** provenance: `attach_mode='xbrl_link'` · `attached_via=resolution_id` · `xbrl_fact_id` (kernel V9/§10.1 wording amendment).
- **P8** `ConceptResolution` reified (readers named) · **a** revoke = 2 strong graders + RecoveryEvent + read-time cohort exclusion; enrichment consumes active only · **b** un-revoke same bar + counter-event · **c** gap repair triggered by revocation OR recorded-edge quarantine: parks re-enqueue + skip-log-bounded re-extraction · **d** the declared XC-09 judgment-exception for backfill eras, with era re-resolution.
- **P9** strong-judge-tier **final verify** for materialization-grade resolutions — **LOCKED** per kernel §11.0 (only tier membership stays `[exp]` via PIPE-32); XC-16 + full-universe = hard pre-gate · **b** qualifier veto (adjusted/organic/pro-forma-class tokens in a candidate qname → refuse).
- **P10** lane-matrix carve-outs, origin-gated (declared FACT-16(3)/(4) amendments): `xbrl_qname`/`MAPS_TO_CONCEPT` written at write time by this code producer only; `reported` legal on the metric lane for `origin=xbrl_link`.
- **P11** reverse-order upgrade: **a** repair-grade in-place upgrade on value-compatible · **b** immutable **`UpgradeEvent`** with full prior payload; no prior_* fields · **c** writer validator: origin flip ⇔ exactly one event · **d** graded reversal · **e** conflict → xbrl parks, written fact stands · **f** fold-equivalent twins converge at read, not in storage.
- **P12** resolution-on-create enqueues materialize(company, driver, all filings incl. current); text never waits.
- **P13** `xbrl_twin_suspect{slice|period}` tripwire (measurement-diff excluded); `twin_suspect_rate` gates rollout `[exp bar]`.
- **P14** period pins: shared deterministic scope classifier in the FACT-18 wrapper (declared FACT-17b/18 extension), quarter > Q1-YTD, ytd = FY-start-anchored, `half` = non-FY-start two-quarter, annual/ttm/monthly, else `exact_range`+WARN · **a** fiscal fields null-not-guessed · **b** sentinels illegal · **c** classifier + text-label resolution anchor on company-ACTUAL period ends (XBRL history / SEC cache first; month-math fallback) — the 52/53-week convergence rule · instants `period_scope=null` (FACT-16.17 carve-out).
- **P15** `effective_driver_state` read field: stored-if-stated; derived-if-`reported` with the comparator by **DriverPeriod date arithmetic** (YoY ±7d for quarter/ytd; prior collapsed annual for annual); **fallback `reported`** on missing/ambiguous comparator; instants `reported` `[exp]`; never written back.
- **P16** menus narrow, evidence creates (five-point structural enforcement, §5.9); no value/scale hints ever.
- **P17** prompt-narrowing = cost experiment only `[exp]`; code-side suppression is the guarantee.
- **P19** *(renumbered; no reserved slots)* proofs X-XL0–3 + pre-gates + fresh Neo4j census + industry-by-industry rollout are the enablement condition; all graph counts re-read at implementation.

**Doc edits on ratification:** `09 §10` → ACTIVE with P2–P4; 09 §6.9 gains the P2 tie-break addendum · `12` gains build step 9b (`xbrl_link_writer.py`), CLI skip + park classes (state-based), FACT-16.17 instant carve-out, FACT-16(3)/(4) origin-gated carve-outs, FACT-17b/18 classifier extension, FACT-14 upgrade-lane note + UpgradeEvent validator · `08` XC-18 → ConceptResolution + revocation; XC-05 gains the qualifier veto; XC-09 gains the declared backfill-era exception note · kernel: V9/§10.1 provenance wording; §6.5 eligibility-evidence exclusion; §9.1(iv) origin scoping · `66/90` close Codex §4.8 · `95` — no reversal row (additions only; note in §C).

## 12. Considered and rejected · corrections · amendments · unresolved

**12.1 Rejected (with evidence):** concept-first driver minting (parallel catalog; v1 death; XC-02) · dropping 10-K/10-Q text (misses) · per-fact LLM cross-checks · single-node dual ownership / field-precedence merges · section-level identity routing · auto-surprise and stored derived comparisons (ISS-16/DU-16.6) · materializing onto latent bases · writing every comparative re-tag · a new stored collapse-rank slot · counting resolutions toward BROAD · prior_*/audit fields on DriverUpdates (UpgradeEvent instead) · `pure`-unit ×100 transform in v1 · value/scale hints to producers · a coined-slice repair lane (reopens the rejected alias layer) · amending 09 §6.9's same-day conscious acceptance (marginal gain, locked-rule cost) · retro-parking fold-equivalent twins (mutation machinery; read-convergence suffices).

**Non-numeric/TextBlock facts — dispositioned:** Keep it narrow: numeric XBRL remains the only XBRL materialization path. XBRL TextBlocks never create Drivers, DriverUpdates, slices, state, SAME_AS, or concept links. XBRL TextBlocks may be used only as source-text aids: chunking experiments, read-time context packets, and possible future change-flag scanner input. TextBlocks-only extraction is forbidden; full section text remains the completeness baseline. None of this is Pass-2 load-bearing; it is optional input/read plumbing only.

**12.2 Corrections applied in this pass (the audit's yield — ruthlessness applied to our own drafts):** UpgradeEvent split from RecoveryEvent (kernel V14/§10.5 semantics preserved) · CLAIM_FROZEN removed from the park condition (kernel blocks QUARANTINED only) · `xbrl_conflict`/`duplicate_of_xbrl` reclassified TERMINAL→**state-based** (L2 repairability) · skip log records crossing SAME_AS edges; P8c trigger set extended to edge quarantine · strong-tier verify **locked**, not [exp] (kernel §11.0) · P6 given a kernel §6.5 landing place + kernel-consistent wording · falsifier (iv) origin-scoped; §15.0 synergy claim corrected · entity-scoping added (multi-registrant filings) · unit whitelist made explicit (EPS `USD/shares` materializes; `pure` fenced) · intra-filing precision-duplicate collision rule added · 52/53-week anchoring pinned for classifier AND text-label resolution · `half` restored to the classifier; classifier made the shared authority in the FACT-18 wrapper · P4b predicate made exact (end == periodOfReport) + null fallback · effective-state comparator moved to DriverPeriod date arithmetic with fail-closed fallback (PER-13) · same-day 8-K/10-Q honesty (09 §6.9 acceptance honored) · fold declared as a rider-3 extension applied read+write (OD-9 concern addressed by declaration, fixed token set, value gate) · fold-equivalent reverse-order twins acknowledged (P11f) · T12.9 renamed-member row rescoped to display-grouping · earlier stamp-variant measurement idea stays reversed; "decimals-scaled" wording stays corrected · plus the full tag/numbering/typo/index hygiene sweep (five-point, P18 gap removed, dual tags split, Q-index corrected to the 23 numbered questions + the unnumbered enrichment question → §5.4/§5.8, brief-# vs Pass-1-Q# notation disambiguated).

**12.3 Declared amendments to locked docs (ten, all additive — restrictions, carve-outs, or extensions; zero reversals):** (1) `12` FACT-16.17 — instant `period_scope=null` carve-out; (2) kernel V9/§2/§10.1 — `attach_mode` gains `xbrl_link`; `attached_via` value-domain gains resolution-ids; `xbrl_fact_id` added; (3) `12` FACT-16(3)/(4) — origin-gated write-time `xbrl_qname`/`MAPS_TO_CONCEPT` + `reported`-state legality for this producer; (4) `09 §10` rider item 3 — read-bucket token set extended to the P3 family, and the same fold applied in the write-side skip test (xbrl-side-only); (5) kernel §6.5 — eligibility-evidence exclusion for `origin=xbrl_link` facts/resolutions; (6) `08` XC-05 — qualifier veto; XC-18 — ConceptResolution reification + revocation states; (7) `12` FACT-17b/18 — period_scope classifier as the shared exact-date-branch authority; (8) kernel §9.1(iv) — origin scoping of the periodicity detector; (9) `12` park-class additions (state-based `xbrl_conflict`/`duplicate_of_xbrl`/`xbrl_internal_conflict`) + the CLI skip/no-enrichment rules + the UpgradeEvent writer validator; (10) `09 §6.9` — the intra-event origin tie-break addendum. Also declared, not an amendment: the XC-09 backfill-era judgment exception (P8d), justified in place.

**12.4 Remaining unresolved (all [exp], none blocking):** twin-suspect rollout bar (from X-XL2) · strong-judge tier *membership* (PIPE-32 A/B) · `pure`/exotic-unit enablement census · instant effective-state baseline · prompt-narrowing + statement-artifact input trimming · 10-K/10-Q text cadence (part-2).

## 13. Adjudication + change record

**Pass 1 → Pass 2:** base = Fable v1.0 (the converged architecture shared by all three candidates); grafts from GPT 5.5 (qualifier veto, hardened to refuse; `xbrl_fact_id`) and Opus 4.8 (X-XL0; industry rollout; prompt-narrowing as [exp]); conversation pins folded (no-enrichment; head-scoped skip + value gate + fold; parks; upgrade lane; tripwire; period classifier; resolution lifecycle; effective state; menus invariant; eligibility isolation). **Pass-2 adversarial audit:** six lenses (kernel · record-model · pipeline · edge-case · minimalism · requirements), 45 findings — 15 MAJOR, 30 MINOR — every one dispositioned; the accepted corrections are §12.2, the declared amendments §12.3, the honest impossibilities §8. Notable audit-driven design changes: entity-scoping (P4f), unit whitelist (P4c), intra-filing collision rule (P4g), 52/53-week anchoring (P14c), state-based parks (P5d/e), UpgradeEvent (P11b), locked strong verify (P9), eligibility-amendment landing place (P6), falsifier-(iv) scoping (P4j), fold declaration (P3).

## 14. Pass-1 question index (23 numbered follow-ups + the unnumbered enrichment question → where answered)

enrichment/self-sufficiency → §5.4 P1a + §5.8 P15 · 1→§5.4/§10 · 2→§10 · 3→§5.2 step 5 (+§5.6 for divergence) · 5→§5.1 · 7→§5.1 · 8→§5.7 · 9→§5.1 · 11→§5.8 · 13→§5.2 · 14→§3 · 15→§5.7 · 19→§5.8 · 20/21/22→§5.4+§5.6 (layered convergence: shared vocabularies → skip → union/collapse/display-grouping → detectors) · 23→§5.7 (abstain-biased; `cloud_backlog` never force-links) · 24→§5.2 step 5 · 25→§5.3 · 26/27→§5.7 · 28/29→§5.8 · 30→§5.9.

*Assembled 2026-07-08 from first-hand Pass-1/Pass-2 reads of: FableAdmissionKernelDesign v3.4 · FableContextPack · 03/04/05/06/08/09/10/12 · 90 · 95 · 66 (XBRL rows) · 99 §4.6–4.8/§5 · NEO4J_SCHEMA_v3.md · XBRL_PATTERNS.md · extract-skill queries — then adversarially audited by a six-lens agent pass (45 findings, all dispositioned; run wf_a63b0d59-9c2). On any conflict, the cited topic doc wins.*
