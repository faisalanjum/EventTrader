# S2 — the ONE candidate-fact packet + decomposition spec ❄️ FROZEN v1.0
> **AMENDED by OD-21 (owner-approved 2026-07-14, parallel surprise track · 66 §0.R OD-21 · 95 #42):** fact_scope
> gains an optional 4th slot `surprise=<actual_vs_consensus|actual_vs_guidance|guidance_vs_consensus>` after
> `measurement` — surprise lane ONLY, CODE-composed (basis_hint × comparison_baseline) pre-fusion, in the id +
> series key. Channels untouched (ChannelContract unchanged). Where this doc's fact_scope grammar shows three
> slots, read four per OD-21; 09/12 carry the binding wording.
**Status: FROZEN — OWNER-APPROVED 2026-07-14 ("Approved. Freeze S2"). Task #778 closed. Any change now requires
an explicit owner amendment. Scope: METRIC (fiscal.ai) + GUIDANCE worked; surprise/action slot in via owner's
parallel track without touching the frozen shape. Repo persistence (FinalDesign doc + DU-02 amendment + 95 rows)
= S6 back-port package, owner-approved batch.**
**Finding in one line: >99% of the packet already exists in locked law; it just was never assembled into ONE object. The genuine gaps are 2 conflicts + 2 missing bindings (Part C).**

---

## PART A — The ONE packet (assembled from existing law)

A channel never mints a name. It hands the shared core ONE object. That object has three blocks, and all three field-lists already exist in the locked design:

### Block 0 — ENVELOPE (per source event) — from 12 FACT-17b top-level
`source_id · source_type · ticker · fye_month` [+ optional `calendar_override`] · `event_time`
- One CLI invocation = ONE source event (the fusion/collision locality guarantee, FACT-17b).

### Block 1 — IDENTITY SIGNALS (per candidate) — from kernel §2 Stage-0 INPUT
`{proposed_name · slice_tokens[] · measurement_spans[] · per_x · quote · event_time}`
- These are the DECOMPOSITION OUTPUTS (Part B). The kernel Stage-0 consumes them to reuse/create/reject the Driver.
- `slice_tokens`, `measurement_spans`, `per_x` are TRANSIENT signals: the kernel folds per_x into the canonical name (NAME-13), measurement_spans into `fact_scope.measurement` (OD-9), slice_tokens into `fact_scope.slice`. They are NOT stored raw.

### Block 2 — THE PROVEN FACT (per candidate) — from 12 FACT-17b item + 09 fields
`driver_name · driver_state · quote` · value slots `level_low / level_high / change_value / comparison_low / comparison_high / comparison_baseline / value_text / conditions / company_confirmed`
- transients (propose-then-discard): `level_unit_raw / change_unit_raw` · 4 per-slot hints (`level_unit_kind_hint / level_money_mode_hint / change_unit_kind_hint / change_money_mode_hint`) · `level_shape_hint / comparison_shape_hint` · `measurement_raw_spans`
- period fields: `period_start_date / period_end_date / fiscal_year / fiscal_quarter / half / month / long_range_start_year / long_range_end_year / sentinel_class / time_type` (+ `period_scope ∈ {ytd,ttm}` on cumulative)
- `slice` = list of `kind:value` tokens or menu-pick refs
- Code (not the packet) builds: `id · fact_scope · series_unit · created · date` (09 §3 code-written 6).

### Block 3 — OPTIONAL Cat-2 VERDICT (per candidate, only when the fact explains a move) — from 07 DU-21..24
`explained_target ∈ {Event, DailyCompanyMoveEvent} · stock_impact ∈ {long,short} · weightage ∈ {0.1..1.0}|null · confidence ∈ {0..100 deciles} · produced_mode ∈ {live,backfill} · llm_producer`
- Cat-1 vs Cat-2 = birth SITUATION only, never stored (ratified). Cat-2 = this block is present.

### THE UNIFICATION (the one thing to state explicitly — missing-rule #3)
> kernel Stage-0 `evidence_atom` **≡** the Block-2 fact item (FACT-17b).
> So "every new Driver arrives WITH its first proven DriverUpdate" is mechanically ONE object: Block 1 (identity signals) + Block 2 (the proven fact) travel together; the kernel judges identity from Block 1+quote, and on CREATE the SAME packet's Block 2 becomes the driver's first DriverUpdate. This is exactly **born-complete admission** (kernel §5 / OD-7).

**Three consumers, one object:** kernel Stage-0 (Block 1) → reuse/create/reject · Track B writer (Block 2) → write the DriverUpdate · verdict_writer (Block 3) → write EXPLAINED_BY.

---

## PART B — The decomposition procedure (raw channel label → the packet's identity signals)
**This is "the one unbuilt bridge." The RULES all exist; they were never assembled into one ordered procedure. It is CHANNEL-INDEPENDENT (fiscal.ai label AND guidance label_slug run the same steps).**

INPUT: a raw label + context (company, quote, value, period, source, and — if present — the XBRL member).
OUTPUT: `{proposed_name, slice_tokens[], measurement_spans[], per_x}` + `fact_type` + unit.

Ordered (stop-at-first is not the pattern here; each step peels one thing off the label):
0. **Strip direction/impact words** (NAME-11 step 0): rose/headwind/pressure… never in the name (unless a specific reusable force like `glp1_pressure`).
1. **Measurement peel** (NAME-14 / FS-25 / OD-9): pull version/basis qualifiers (adjusted, diluted, constant-currency, core…) into `measurement_spans`. `"Adjusted EBITDA"` → spans=["Adjusted"], residual="EBITDA". Code normalizes spans; producer never invents the token; never assume gaap.
2. **Per-X peel** (NAME-13): a stated per-X denominator → `per_x` (goes IN the name; unit stays base). Not stated → none.
3. **Portion check** (OD-17): a portion qualifier (current / funded / fee-earning…) STAYS IN THE NAME — never a slice, never measurement. `"current RPO"` → name `current_rpo`.
4. **Name-vs-slice split** (NAME-10/11 · OD-3 / 95 #38): for each remaining qualifier, the LOCAL role test (from quote + this company only): own measured part {segment/geography/product/customer/channel/entity_ownership} → `slice_tokens`; external actor/cause or unclear role → stays in the NAME. `"iPhone Revenue"` → iPhone = own product → `slice=product:iphone`, residual "revenue".
   - **Slice KIND source:** XBRL member present → kind from the FROZEN axis table (FS-08/11/18, deterministic, code). Text-only → producer proposes kind via the FS-15 / FACT-26f ladder (menu-match → coin → `unknown:` when ≥2 kinds fit — never guess).
5. **Name assembly** (NAME-05/06/07/08/09 · singular-by-default): cause-only, lowercase_snake, familiar/standard phrases whole, one cause per name, + per_x. `"revenue"`.
6. **fact_type stamp** (DU-05/06/07 · OD-1/OD-2): metric / guidance / surprise / action_event; suffix-gate first, then DU-06 persistence test, C2 metric-proof if unclear. A reported KPI value → `metric`; a company forward outlook → `guidance`. Strong-tier, at admission (born-complete).
7. **Unit** (04 UNIT-01 · OD-10/OD-11 · unit_resolver): unit_raw + hints → 10-unit enum; code stamps `series_unit`.

Then Block 1 + Block 2 go to the kernel/writer.

### AUTHORITY SPLIT (the v1-death guardrail — missing-rule #4)
- **CODE (deterministic, never decides meaning):** format norm, measurement token normalization (OD-9), unit resolution, XBRL-member→slice-kind (frozen table), id/fact_scope build, ALL validators.
- **LLM (proposes the SEMANTIC parts only):** name-vs-slice role test, the cause-only name, a prose slice's kind, fact_type. Per NAME-03/19 + v1's death, the NAME is ALWAYS LLM-proposed — **never code-parsed from the label string** (that IS the closed-vocab death).
- **KERNEL (strong-judge, final identity authority):** reuse/create/reject, SAME_AS, fact_type/BASE_METRIC confirmation, establishment.

### Structured-channel nuance (needs owner confirm — folded into missing-rule #4)
For fiscal.ai T1-xbrl records the member is known → slice kind is deterministic (code). But the cause-only NAME and the name-vs-slice decision for TEXT-only records (T2/T3, ~52%) must stay LLM-propose + kernel-judge. Proposed rule: **code may fill format/unit/XBRL-member-slice; the NAME and any prose slice stay LLM-proposed + kernel-judged. No channel ever code-derives a Driver name from its label.**

---

## PART C — RESOLVED 2026-07-14 (owner rulings + Fable adjudication; supersedes the open list)

**① RULED YES, with the owner's wording correction (binding):** channels NEVER create anything. An authorized channel with real evidence SUBMITS a candidate fact; **the shared core validates it and decides** — through the existing kernel machinery (Stage 0–3, strong-judge tier) AND the experiment gate regime (EXP-0 graders · EXP-3 router · EXP-4 SAME_AS keys · fitness gate) per FableExperimentWorkOrder/Plan. DU-02 amendment wording (for the S6 back-port): "governed channels submit candidate-fact packets; the shared core alone admits/creates; on admission the Driver is created WITH its first fact." Lane nuance preserved: "value + period" required-ness stays the LANE MATRIX's job (numberless guidance legal via value_text; action periods rare) — the envelope never hard-requires them universally.

**② ADJUDICATED (Fable, non-rubber-stamp): born-complete STANDS; general name-only seeding REJECTED.**
- Why factless cards break the design: (a) the frozen birth-anchor machinery (kernel §6.3) judges every SAME_AS/ATTACH against birth QUOTES — a factless card is judge-blind and drift-unpinnable; (b) NAME-18(d) requires ≥1 causal claim with real evidence (locked); (c) "hand-seeded vocabulary" is an explicitly rejected death pattern (kernel §13; RavenPack-import rejection, 95 #14); (d) evidence-free cards pollute reuse retrieval — name-string gravity with no evidence mass = v2's death channel.
- Zero cost to us: every channel record arrives evidence-bearing, so "seeding the catalog" = feeding records through the kernel (each born-complete). The seed IS the fiscal.ai pilot.
- The narrow legitimate need ALREADY EXISTS in law — **latent BASE anchors**: when `revenue_guidance` is admitted before `revenue` has any fact, PIPE-25/OD-1 auto-mints an invisible placeholder base (never claim-eligible, never shown in reuse display, graduates exact-norm on first real evidence). No new machinery.
- If the goal is to SEE the name space early: run the decomposer DRY-RUN over labels (paper output, no catalog writes) — available anytime.

**③ RULED + SPEC: fiscal.ai harvest RECORD design UNCHANGED; the new piece is INGESTION ORDER.**
- Field-for-field the seed record already carries what the packet needs (Part D map; 2 trivial lookups: Report.created → event_time, fye_month).
- The adapter RE-SORTS KPI-major records into SOURCE-EVENT-major packets, submitted chronologically per company. **Unit of submission = ONE SOURCE EVENT** — not one KPI, and not one bare fact (FACT-17b one-invocation-one-event: fusion + collision detection see the whole submission). **CORRECTION (2026-07-14): arrival-together is the OPTIMAL case, not a safety requirement** — cross-time/cross-channel arrivals at the same event are the legislated OD-8 late-collision path; see ⑤.
- The KPI grouping carries ZERO identity authority — provenance only. The kernel judges each candidate item independently; series membership EMERGES at read (FACT-33 series key). This directly answers "seed facts may not truly belong to the same driver": the channel never asserts cross-record identity; record 1 of a series CREATEs (full judgment), later records ATTACH (cheap exact path) — the natural kernel flow, no special casing.
- Same-value multi-source records (8-K + 10-Q restating one number) = separate facts on separate events BY DESIGN; read-time collapse (8k > transcript > 10q > 10k > news) merges the view. No channel-side dedup.
- Bookkeeping: the channel keeps its own ledger (record → submitted item → outcome) for the catch-up cursor; NO new packet fields.

**④ RULED + DESIGN: decomposition is ONE SHARED component — the owner's "if only it were possible" is possible, and it's the minimal design.**
- Channels implement ONLY a thin adapter (Part D): enumerate events since cursor → emit RAW ITEMS. The shared decomposer (one prompt+code stack for ALL channels) produces the standard packet; kernel judges; writer writes. One test surface, one certification, six tenants.
- Robustness = already built: the fail-closed validator suite + park ledger + dry-run default (FACT-16/17) — malformed input cannot enter; every failure returns a machine-readable reason to the submitting channel.
- Honest caveat: one component ≠ one difficulty — a prose claim (learner/news) is harder than a KPI label; per-channel certification (EXP-5-class packet experiments) still required before a channel goes live.

**⑤ CROSS-CHANNEL SAME-EVENT LAW (owner Q 2026-07-14 · answer = existing OD-8 FINAL, owner-approved 2026-07-05 — ZERO new machinery).**
Two channels may hit the SAME source event at different times, for the same or different facts. Safe by three
existing layers, all in the shared writer (below every channel — channels need NO coordination):
1. **Same fact → same id → converge.** The id is code-built and producer-free (event+driver+fact_scope); the
   writer MERGEs in place; FACT-14b fills empties and never null-clobbers. Channel B's level+change item onto
   channel A's level-only node = COMPATIBLE → fill (cross-channel "fusion" via the id).
2. **Different fact, same slot, late arrival → OD-8 write rules run against the PRE-BATCH GRAPH STATE on every
   write** (sibling probe: `id = bare` OR `STARTS WITH bare+"|quote_hash="`): exact → merge; compatible → fill;
   CONFLICT (≥1 shared non-null signature slot disagrees) → **new hashed member + late-collision flag — NEVER
   overwrite** (OD-8 rule 8: signature-slot conflicts never overwrite as "correction"; true corrections only via
   explicit `--repair`). Late collisions are legal history (rule 9); ≤1 bare member per group invariant.
3. **Concurrent race** → equal-signature bare+hashed pair detected free by the next write's probe; reads treat
   equal-signature members as ONE fact (prefer oldest/bare); repair lane cleans (OD-8 rule 9 race pin).
Accepted residuals (all existing, measured): non-signature fields (driver_state, quote) keep last-write-wins
with log — cross-channel disagreement rate is exactly what the §12.5 dual-producer probe scores; WHICH member
holds the bare id is arrival-order cosmetic (reads treat members equally); extraction noise can mint a flagged
sibling — visible, over-split, confined to the collision class.
**Claim scope (narrowed 2026-07-14):** the guarantee is exactly "conflicting values never silently overwrite" —
NOT "over-merge impossible." Identity-level over-merge (wrong SAME_AS/ATTACH, upstream mis-decomposition landing
two facts on one id, same-signature restatement-merge-by-definition) is guarded by the kernel's judges +
falsifier + audits with MEASURED upper bounds — the kernel §16 doctrine: zero-by-construction is impossible;
zero-by-measurement with honest bounds is the enforceable promise.

## PART D — Channel adapter contract v0.1 (all a channel implements; everything else is shared)

1. **SELECT** — watch its source; enumerate new source events since its cursor (birth backfill = same enumeration over history, chronological per company).
2. **FETCH** — per event, emit RAW ITEMS: `{quote (verbatim) · raw_label_or_claim · stated value(s)/unit text · stated period fields · source cadence (the channel's own series membership, e.g. fiscal.ai quarterly-vs-annual — form alone is ambiguous: Q4 stated in a 10-K, FY in an 8-K) · adjacent period wording the locator saw (column header / "as of" phrase — transient evidence; the marker scan + time_type judgment need it when the bound quote lacks the header) · source_id/source_type · optional XBRL (when the record is XBRL-tagged, ALWAYS): concept qname + the EXACT context (start/end dates, instant-vs-duration type) + the dimension list — a VERIFIED-empty list asserted explicitly (`dimensions=[]`; a missed extraction must never masquerade as consolidated), every supplied dimension carrying BOTH axis and member, never fragments; the period row consumes the context verbatim and enrichment/backstop-A consume the concept *[OWNER AMENDMENT 2026-07-15, Q4 batch — pre-amendment bytes pinned in the Phase-1 freeze manifest]* · optional value_text/conditions + company-confirmation attribution EVIDENCE (guidance; the CORE derives the `company_confirmed` boolean, never the channel) *[OWNER AMENDMENT 2026-07-15, Q1 batch extension — same ruling as the ChannelContract guidance row]*}`.
3. **SUBMIT** — one packet per source event; consume per-item machine-readable outcomes into its ledger.

Shared side (core-owned, identical for all six): DECOMPOSER (LLM proposes name / prose-slice kind / fact_type; code does format, measurement normalization (OD-9), units, member→slice via frozen axis — Part B) → kernel Stage 0–3 → writer stack → read views. The adapter MAY memoize ONLY the LABEL-pure decomposition parts (name proposal, per_x, portion, the label's slice-token split) per identical (company, label, member) — and a cached result stays a PROPOSAL: each record's per-quote decomposer pass must confirm the cached proposal is consistent with ITS OWN quote (mismatch → fresh decomposition + flag; a label-matched cache must never sail past a quote about something else). Zero identity authority either way — the kernel judges every admission. QUOTE-dependent parts are NEVER memoized — measurement spans, time_type evidence, driver_state, and the marker scans run against EVERY record's own quote (OD-9's never-drop sink is per-quote by definition).

### D.2 — PRECISE fiscal.ai → packet conversion map v0.1 (owner Q2 2026-07-14)
Every row: exact source → exact transform → failure mode. NOTHING guesses; every ambiguity PARKS (arrival-retry).

| packet slot | exact source | transform (who) | on failure |
|---|---|---|---|
| `source_id` | `filing_id` (accession, e.g. 0000320193-24-000123) | look up the graph Report node by accession; id-safe via `canonicalize_source_id` (':'→'_'). *(Exact Report key property confirmed by one read-only query at adapter build.)* | Report not in Neo4j yet (graph runs ~1 qtr behind fiscal.ai) → **PARK-RETRY**, drains when filing ingests |
| `source_type` | `form` | 10-K→`10k` · 10-Q→`10q` (+ 8-K→`8k` when EX-99.1-sourced records appear in parts 2–4) (code map) | other form → PARK |
| `event_time` | Report.created (PIT stamp) | one Neo4j read per filing (batched per company) | missing → PARK |
| `fye_month` | Company record | one lookup per ticker (cached) | missing → PARK |
| **period** | T1: the matched `xbrl_fact` context (instant/duration + exact start/end) — AUTHORITATIVE, verbatim (~48% deterministic). T2/T3: `period` (end date) + `form` + **the channel's cadence signal** (quarterly-vs-annual series membership; form alone is ambiguous — Q4 in a 10-K, FY in an 8-K) + **raw period wording** (transient evidence for the marker scan/time_type when the quote lacks the header) → fiscal window via `fiscal_math` (52/53-wk safe). **`time_type` (duration vs instant) is a REQUIRED decomposer output — a semantic judgment, NEVER a default** (fixed 2026-07-14; the old "duration default for flows" line was a disguised guess — flow-vs-stock IS the meaning call): judged from label + quote ("amount over a window" = duration: revenue, costs, shipments · "standing amount at a date" = instant: subscribers, stores, backlog, headcount, balances), aided by two hints — (a) the SAME (ticker,kpi)'s own T1 siblings' XBRL period_type (deterministic borrow; conflict → PARK), (b) the substrate `KNOWN_INSTANT_LABELS` list (hint only, per FACT-18: `time_type` stays authoritative). **UNCLEAR → PARK** — and this park HAS real drains (unlike the window-marker case): a later T1 sibling of the KPI, or the driver's concept-link (menu carries `period_type`), resolves it → arrival-retry | code (shared resolver is the sole period authority — FACT-17b) | TWO tripwires, both → **PARK**, never trust either side silently: (a) T1-vs-form mismatch (e.g. 9-month context on a "quarterly" record = YTD leak); (b) **T2/T3 contradicting-marker scan** (added 2026-07-14): an explicit window marker in the quote/snippet ("nine/six months", "year-to-date", "trailing/twelve months", "fourth quarter" on an annual stamp) that contradicts the stamped window. Default derivation stays when no marker contradicts — NOT a guess: the harvest's certified Q-vs-YTD binding (#760 guard, 0 leaks) disambiguated with fuller context than the adapter has, and a no-marker record parked "for evidence" would never drain (nothing new arrives for a text record) = losing certified facts. Wrong time_type NETS (all existing law): the marker scan ("as of" on a duration stamp); concept-link **backstop A = the instant/duration veto** (FACT-29; menu carries `period_type`, FACT-30) — a duration-stamped fact whose driver links an instant concept = flag; FACT-16.15 (start==end duration = illegal input) |
| **unit + value** | `value` = the **source-stated SIGNED value, unscaled** (wording fixed 2026-07-14 — "absolute" meant unscaled/full-magnitude, NEVER math `abs()`; OD-12 signed value-space: losses/negatives stay negative — a demonstrated failure class here: the mini-exam truth int() bug turned EPS −0.2 → 0) + `fmt` + `is_currency` | adapter emits `level_unit_raw` (usd/percent/count from fmt) + `level_unit_kind_hint` (money/ratio/count) + `level_money_mode_hint` (aggregate; price_like only for per-X KPIs) + `level_shape_hint='point'`; shared resolver canonicalizes scale (money → the driver's one scale) — deterministic division, no LLM, **sign untouched**. **Free belt+braces: re-assert `value_ok(value, fmt, quote)`** before submit — SCOPE (2026-07-14): the gate guarantees the number appears in the quote at a numeric boundary, NOT that the binding is the correct KPI/period/slice (binding correctness = the binder+verify pass + per-part sample audits; cf. the 13 coincidental small-value mis-bindings found and removed in Part 1); value_ok's sign handling (parenthetical negatives "(0.2)") verified at adapter build | resolver error (cents-on-aggregate, pre-scaled), value_ok fail, or value↔quote SIGN mismatch → **hard-fail → PARK** |
| **measurement** | qualifier spans, grounded in this priority: (1) the QUOTE (the company's own text) · (2) the label ONLY when tier=T2 (T2 verified the label tokens sit next to the value in the filing) | decomposer copies exact spans → `measurement_raw_spans`; CODE normalizes (OD-9: lowercase → non-alnum runs→`_` → maximal contiguous spans = one token); plain KPIs → empty set (never assume gaap) | label-only qualifier with no quote/tier support (vendor wording, not source) → **PARK** — OD-9 is source-grounded; fiscal.ai's label is a vendor label |
| **slice** | T1: `xbrl_fact` → (axis_qname, member_qname, member label) | `classify(axis)` via the FROZEN table (code): SLICE_AXES → kind + normalized member label, emitted as a MENU-PICK REF (writer attaches MAPS_TO_MEMBER + slice_part free — FS-21); unknown axis → `unknown:xbrlaxis_<hex>__<member>` sentinel; multi-member → code-sort, join ';' | NON_SLICE axis or FS-20 elimination member → **PARK+log** (accounting construct — never silently consolidate, OD-17c) |
| | T2/T3 (no member): the label's own-part qualifier | decomposer ladder (NAME-10/11 local role test) + FS-15/FACT-26f kind ladder vs the company PIT menu: menu-match → pick · prose-clear → coin `kind:value` · ≥2 kinds fit → `unknown:<value>` · whole-company → omit slice | never guess a kind (guessed kind = fake axis-grade confirmation) |
| `proposed_name` | kpi label residual (after measurement/per-X/portion/slice peels) | decomposer LLM proposes (NAME-05..08 canonical coining); NEVER code-parsed from the label string (v1 death) | NAME-18(f/g) vague/ambiguous → SKIP |
| `driver_state` | — | `reported` (DU-09 rule 5: bare stated value, no comparison in a table cell) | quote states a comparison → decomposer judges per DU-09 ladder |
| `quote` | `quote` | verbatim, unchanged | empty → hard-fail (REQ all lanes) |
| channel ledger | (ticker, kpi, period) → submitted item → outcome | channel-local file; feeds the catch-up cursor + recall accounting | — |

Channel abstain-outcome mapping (fiscal.ai bot Q&A 2026-07-14): **vendor-calculated `% Chg` / `Common Size` rows
(~45K, ~62% of the universe) are SKIPPED AS SEED FACTS — never claimed recoverable en masse.** A growth/margin
figure EXPLICITLY STATED by the source ("revenue grew 12%") is a DIFFERENT fact and enters through the normal
stated path; otherwise growth/margins stay read-time calculations from stored levels (store-when-stated; the
`calculated` class is a DROP, 09 §5). Same for other fiscal.ai-COMPUTED rows (balancing plugs) → terminal SKIP,
counted · corpus_missing (filing not in Neo4j) →
PARK-RETRY · value-absent on a text record → SKIP **only after the expected source set for that company-period
(10-K/10-Q + earnings 8-K EX-99.1) was PRESENT and actually searched, with zero extraction errors** — an
incomplete search is corpus-incomplete → PARK-RETRY, not a skip. Value-absent SKIPs re-open on THREE triggers
(not just a new source class): (a) a new source — instance (late/amended filing) or class (transcripts added);
(b) a repaired corpus (a re-extracted/fixed section that was corrupt at search time); (c) a CERTIFIED locator
upgrade (precedent: the header-capture fix closed a 91%→100% binding gap — earlier locator versions missed
values later ones find; "certified" = passed the locked regression/A-B regime, no re-scan on uncertified tweaks). **The channel ledger
records a per-company-period source-completeness + extraction-status STAMP; SKIP is legal only against a clean
stamp** — auditable, not merely procedural. **COST NOTE (not a design blocker):** 8-K press releases state
rounded values, so exact-value yield from EX-99.1 packets will be limited — 10-Q/10-K remain the exact-value
backbone; PR packets add early availability only where they match.

**HONEST NUMBERS:** every precision figure quoted in this program so far belongs to a COMPONENT — the relocation
engine's certs (e.g. 97.2% pooled mini-exam) and the binder's sample audits. **END-TO-END seed → decomposer →
kernel → writer precision is UNMEASURED**; measuring it is exactly what the fiscal.ai pilot's pre-registered
gates are for (amendment A1). No component number may be quoted as the system number.

Guidance channel note: NO conversion map exists or is needed for old GuidanceUpdate rows — Track C law forbids
production replay; the guidance channel is FRESH extraction from source docs, so its "map" IS the decomposer
output spec. Old rows serve only as pilot/EXP test inputs.

---

## Worked examples (metric + guidance)

- **fiscal.ai "iPhone Revenue" (AAPL, $201,183M, FY2024, 10-K, member=IPhoneMember):**
  decomp → measurement=∅ · per_x=none · portion=none · name-vs-slice: iPhone=own product → `slice=product:iphone` (kind from frozen axis, member present) · name=`revenue` · fact_type=`metric` · unit=`m_usd`.
  packet → Block1{proposed_name=revenue, slice_tokens=[product:iphone]} + Block2{metric fact: level_low=level_high=201183, level_unit=m_usd, quote="iPhone $ 201,183", period FY2024}. Born-complete: first DriverUpdate rides in.
- **fiscal.ai "Adjusted EBITDA":** measurement peel → spans=["Adjusted"], name=`ebitda`, measurement=`{adjusted}` (the exact 95 #2 retired-defect class — proves the decomposition works). NOT `adjusted_ebitda`.
- **guidance label_slug "adjusted_ebitda" (old Neo4j regime):** SAME decomposition → name=`ebitda`, measurement=`{adjusted}`, fact_type=`guidance`. Confirms decomposition is channel-independent (guidance channel must run it too; old label_slugs are raw labels, not names).
