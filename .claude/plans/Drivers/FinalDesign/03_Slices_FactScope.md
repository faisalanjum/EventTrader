# 03 · Slices & fact_scope

**What this is:** how a single fact is *identified* and *bifurcated*. `fact_scope` = the "which part of the company + which time window + which version of the number" tag that separates same-event, same-driver facts. This section owns the **slice** (which part) and **measurement** (which version); **period** lives in its own section (DriverPeriod).

> Every rule below is **LOCKED** unless marked **⏳ OPEN**. Where a rule replaced an older one, **Replaces** points into `95_Supersession.md`. Source of the rules = `Naming_Slices_XBRL.md`; the axis data = `XBRL_SliceAxis_Catalog.md`.

**Still open in this section:** FS-23 (cross-company value comparison), tracked in `90_OpenItems.md`. *(FS-14 point-in-time — RESOLVED 2026-07-02: PIT for DriverUpdate write-time.)*

---

## A. fact_scope = a fact's identity

#### FS-01 — fact_scope is a fact's identity  `[LOCKED]`
- **Plain:** A fact's identity = event + driver + fact_scope. `fact_scope = period + slice + measurement (+ surprise, on the surprise lane only)`.
- **Rule:** fact ID = event + driver + fact_scope (NO producer). Code builds the ID from the parts the LLM extracts — the LLM never builds the ID.
- **Why:** A code-built, producer-free key means two readers of the same fact converge to one node.
- **Source:** Naming_Slices_XBRL.md §1

#### FS-02 — fact_scope is one canonical string  `[LOCKED]`
- **Plain:** The parts join into one string in a fixed order. If no narrower company part is stated, leave the slice empty; for numeric/reading lanes that means consolidated whole-company, while for action events it means no slice applies. Use a quote hash only when two different facts in one event still collide.
- **Rule:** Serialized as ONE canonical string, named parts in a fixed order (`period=…|slice=segment:enterprise|measurement=adjusted|surprise=guidance_vs_consensus`). The `surprise=` slot is **surprise-lane only** (omitted on every other lane) and sits LAST among structured slots, before any `quote_hash` (FS-27 · OD-21). If the source names no narrower business part, omit the slice slot. For metric/guidance/surprise, omitted slice means consolidated whole-company, not missing/unknown. For action_event, omitted slice means no slice applies or no narrower business part is stated. Do NOT add a quote hash for an omitted slice. Add `quote_hash=<hash>` only as the FS-03 tie-breaker when the structured parts still cannot separate two different facts in one event. **Identity uses format-normalization only** (case/whitespace/punctuation); per-company alias files that unify drift are **read-time views + member-matching, NEVER part of the id** — else growing an alias file would change a fact's id (ids are immutable). *(Pinned with 09.)*
- **Why:** One fixed string → the same fact always makes the same key; code builds/compares it deterministically.
- **Source:** Naming_Slices_XBRL.md §1 · DriverGraphSchema.md §4

#### FS-27 — the `surprise=` slot + slot-admission governance  `[LOCKED — OD-21, owner 2026-07-14]`
- **Plain:** A surprise fact carries WHICH KIND of expectation-gap it is; and no new fact_scope slot is added without passing a test.
- **Rule:** `surprise=` is a fact_scope slot **REQUIRED on every surprise fact and FORBIDDEN on metric/guidance/action_event**, with three values — `actual_vs_consensus` · `actual_vs_guidance` · `guidance_vs_consensus`. CODE composes it (the producer NEVER emits the final label) from the producer's transient `surprise_basis_hint ∈ {actual, guidance}` (the producer's forward-guide-vs-reported-actual call — DU-05/DU-06 outlook-verb + ISS-16 — that it already makes for the sibling fact) × the `comparison_baseline`: actual+consensus → `actual_vs_consensus` · actual+previous_guidance → `actual_vs_guidance` · guidance+consensus → `guidance_vs_consensus` · anything else (e.g. guidance+previous_guidance = a guide-vs-own-prior movement) is rejected or routed off the surprise lane. Basis comes from the hint, NEVER from whether the period has ended (a guide restated after its period ends is still a guide). `surprise=` is composed + validated **BEFORE within-event fusion and is part of the fusion scope key** (so two surprise types from one event never fuse). Every GROUNDED surprise requires its matching home fact — a numberless grounded surprise still gets its sibling (`unknown`+quote); an ungrounded "results beat" (no identifiable metric) is parked (12 FACT-16 #18). It is **identity-constitutive**: it enters the id AND the read/collapse series key (09 §6.9 · 11 T12.1), so a later earnings surprise never collapses over an earlier outlook surprise on the same driver+period, and a same-event "beat consensus AND own guidance" splits into two facts instead of deduping. **Slot-admission governance (general rule):** a NEW fact_scope slot is admitted ONLY if the dimension is (a) identity-constitutive for its lane, (b) underivable from the other slots, and (c) never compared across lanes. `surprise=` passes all three; the next proposed slot must too.
- **Why:** Two different-tense expectation gaps on one driver+period are BOTH permanently true → the address must separate them; the governance test stops slot sprawl.
- **Source:** OD-21 (66 §0.R · 95 #42)

#### FS-03 — quote_hash is a tie-breaker only  `[LOCKED]`
- **Plain:** The quote-hash is only for two genuinely different facts in one event the structured parts can't split.
- **Rule:** `quote_hash` is added ONLY when the structured slot can't separate two different facts in one event (same slot, different value-hash). Restatements (same value) merge; never added when the structured scope already identifies the fact. Fusion comes first: if one fact has level + change + comparison, write one fused DriverUpdate before testing collision. If a true collision remains, every fact in that collision set gets its own deterministic `quote_hash` built from normalized quote + normalized value signature; no colliding fact keeps the bare id.
- **Why:** Prevents over-splitting restatements (press release + MD&A both "Q1 +3%" → one fact).
- **Source:** Naming_Slices_XBRL.md §1

#### FS-04 — Asymmetric authority (the safety engine)  `[LOCKED]`
- **Plain:** The AI may pick or coin a slice value and mark it "provisional" — but NEVER merges two existing values. Only code merges, and only on an exact/confident match.
- **Rule:** The LLM may ASSIGN each fact to a value (pick-existing or coin-new) and mark PROVISIONAL — it NEVER merges two existing identities. CODE alone may DELETE (frozen list) and MERGE two existing values, exactly/confidently only — never fuzzy or global.
- **Why:** Correct from day one no matter how wrong the LLM is — every LLM error is over-split (recoverable).
- **Source:** Naming_Slices_XBRL.md §0 (asymmetric authority)

## B. The slice = kind:value

#### FS-05 — A slice is KIND:VALUE  `[LOCKED]`
- **Plain:** A slice is written `kind:value` — one of 6 fixed kinds + a free-text value.
- **Rule:** `slice = KIND:VALUE`. KIND ∈ 6 fixed kinds (+ `unknown` = safe 7th). VALUE = the specific part (free text, lowercase, punctuation stripped).
- **Why:** A fixed kind set keeps slices machine-checkable; free-text values stay open to any real business part.
- **Source:** Naming_Slices_XBRL.md §4

#### FS-06 — The 6 slice kinds  `[LOCKED]`
- **Plain:** The 6 kinds, each defined by an "operate / sell" test.
- **Rule:**
  - **segment** — operates AS it (incl. brands): `taco_bell`
  - **product** — SELLS it: `iphone`, `aws`
  - **geography** — operates IN it: `china`
  - **customer** — SELLS TO it: `major_customer_a`
  - **channel** — HOW it sells/runs (franchised vs company-run): `franchised`
  - **entity_ownership** — a stake it OWNS (JV/equity-method): `jv_x`
  - (+ `unknown` = safe fallback)
- **Why:** The operate/sell test works for ANY metric, not just revenue, and maps to the XBRL cube dimensions.
- **Source:** Naming_Slices_XBRL.md §4 · XBRL_SliceAxis_Catalog.md §2
- **Replaces:** old "4 kinds; store_type separate" — 95_Supersession #11

#### FS-07 — The slice test  `[LOCKED]`
- **Plain:** Something is a slice only if the company operates-as/in/sells it. Accounting labels are not slices.
- **Rule:** A value is a slice only if you can say "revenue/earnings from ___" — a real business population. Accounting labels (Level 2 fair value, Term Loan, RSUs, reconciling items) are NOT slices; period and measurement are handled separately.
- **Note (OD-17 b/c — owner 2026-07-11):** company-stated residual buckets ("Other", "Rest of World", "Corporate unallocated") ARE legal slice values of their stated kind. Prose-coined residuals carry no PROVISIONAL flag (FS-20 classifies XBRL members only); what keeps them safe today is company-in-key + the unbuilt FS-23 layer. A residual's composition may change as items are broken out: read views label residual-value series non-continuous across periods. Accounting constructs: see 02 OD-17(c) — excluded as names AND slices, dropped + logged via FS-20's log, the mover recorded on the affected reported metric.
- **Why:** Keeps the slice about the business, not the accounting.
- **Source:** Naming_Slices_XBRL.md §4 · XBRL_SliceAxis_Catalog.md §7

#### FS-08 — "Brand" is not a kind — the kind comes from the axis  `[LOCKED]`
- **Plain:** A brand's kind isn't "brand" — it's whichever XBRL axis it sits on (Taco Bell → segment; Kraft → product).
- **Rule:** "Brand" is not a kind. A brand's kind comes from its XBRL axis. Menu rows → kind from the frozen table; prose-only parts → the producer picks the kind, code validates it's one of the 6.
- **Why:** The same word can be a segment at one filer and a product at another — the axis is ground truth.
- **Source:** Naming_Slices_XBRL.md §4 · XBRL_SliceAxis_Catalog.md §2

#### FS-09 — Multiple parts → code-sorted, joined by ';'  `[LOCKED]`
- **Plain:** A fact about more than one part lists them all, code-sorted, joined by `;`. Never drop a part.
- **Rule:** Two+ parts → multi-valued, code-sorted, joined by `;`: `geography:china;segment:taco_bell`. Never drop a part.
- **Why:** Dropping a part would merge two different facts; code-sort makes the string deterministic.
- **Source:** Naming_Slices_XBRL.md §4

#### FS-10 — Slices apply to all 4 fact-types; period is not a slice  `[LOCKED]`
- **Plain:** Every fact-type can be sliced. Whole-company / total / consolidated / no stated part uses an omitted slice; for actions, omitted simply means no slice applies. Time is not a slice.
- **Rule:** Slices apply to ALL 4 fact_types. Whole-company / consolidated / total-company / no stated segment → omitted slice. For metric/guidance/surprise, omitted slice means consolidated whole-company, not missing/unknown. For action_event, omitted slice means no slice applies or no narrower business part is stated; "Total" display is not an action-event claim. Store a slice only when the source names a real narrower business part. period (time) is NOT a slice — it's its own fact_scope part (DriverPeriod). **OD-17(a) pin (owner 2026-07-11):** an aggregate qualifies for the omitted slice only under the population test (population = the consolidated reporting entity); cross-ownership network aggregates and curated subsets never do.
- **Why:** "Which part" is orthogonal to "what kind of statement"; the omitted slice is the one canonical company-wide bucket, while real narrower parts keep their own slice values.
- **Source:** Naming_Slices_XBRL.md §4
- **Replaces:** explicit total → `slice=total` — 95_Supersession #25

## C. The frozen axis table + sentinel (deterministic)

#### FS-11 — The axis→kind table is frozen in code  `[LOCKED]`
- **Plain:** Which XBRL axis maps to which kind is a fixed lookup baked into code, refreshed only offline.
- **Rule:** The axis→kind mapping is a FROZEN code table; runtime = pure exact-string lookup (100% deterministic). The "operate as/in/sell" test was a one-time discovery tool; its output is the frozen table. Refreshed offline only, never at runtime.
- **Why:** Deterministic lookup → zero runtime AI judgment on kind → no drift, fully reproducible.
- **Source:** Naming_Slices_XBRL.md §6

#### FS-12 — The 3-way sentinel  `[LOCKED]`
- **Plain:** Known slice axis → use its kind. Known non-slice axis → skip. Anything unknown → provisional (never dropped).
- **Rule:** Runtime 3-way: in `SLICE_AXES` → its kind; in `NON_SLICE_AXES` → skip (vetted non-business); anything else → PROVISIONAL slice (over-split-safe), NEVER silently skipped.
- **Why:** Company-coined slice axes are common; silently skipping a real one would merge real businesses. Slicing it provisionally can only over-split.
- **Source:** Naming_Slices_XBRL.md §6

#### FS-13 — The slice-axis data (~55 axes; classify by members)  `[LOCKED]`
- **Plain:** ~55 slice axes across the 6 kinds (verified census). Always judge an axis by its members, not its name.
- **Rule:** The frozen table holds ~55 verified slice axes across the 6 kinds (2026-06-26 census, all adversarially verified). Classify by MEMBERS, never the axis name — names lie (`eqt:DistributionChannelAxis` members are WTI/NYMEX price benchmarks). The full axis list + member examples live in `XBRL_SliceAxis_Catalog.md`.
- **Why:** Name-only classification has ~20% error; the member list is ground truth. The catalog is data, refreshed offline.
- **Source:** XBRL_SliceAxis_Catalog.md §2 / §6

## D. The per-company menu

#### FS-14 — The per-company menu  `[LOCKED]`
- **Plain:** For each company + kind, the menu = the **union** of members from the company's 10-Q/10-K filings + the values the catalog already used. **Not just the latest filing.**
- **Rule:** `menu(company, kind)` = the **unique set (union) of XBRL members across the company's 10-Q/10-K filings** ∪ values the catalog already used — **not just the single latest filing**, so discontinued or renamed segments aren't missed. 8-K/transcript/news events usually carry no member breakout, so their menu comes from these filings (unless the event itself has usable member data).
- **Point-in-time (LOCKED 2026-07-02):** For **DriverUpdate write-time** producers, the menu is **restricted to filings at or before the event timestamp / public source time** (both the XBRL-members half **and** the catalog-history half cut at ≤ T) — a historical/backfill fact never sees a future segment structure (*err over-split, never leak*). Use the source's public/accepted time, not our system write time. **3-context split:** driver-**name** creation → slice-menu PIT is N/A (names carry no slice) · DriverUpdate **write** → PIT · **read / offline repair** → all known history OK (no fact is being written). *(Slice-value immutability (FS-17) is orthogonal — both hold. Same cutoff as the concept-link menu, XC-09.)*
- **Why:** A union across filings (not just the latest) maximizes reuse — a fact about a discontinued/renamed segment finds its existing value instead of coining a duplicate.
- **Source:** Naming_Slices_XBRL.md §7 *(menu contents extended from "latest prior" → "union of all prior filings"; PIT re-locked per owner, 2026-07-02 — see 90_OpenItems §E)*

#### FS-15 — The producer's 4 outcomes per fact  `[LOCKED]`
- **Plain:** For each fact the producer picks a menu value, coins one, marks a real slice unknown, or omits the slice for whole-company. A quote-hash is only a last tie-breaker.
- **Rule:** (1) on menu → pick (code supplies kind + a free XBRL link); (2) real, off-menu → coin in-style (no link); (3) real slice but no kind fits → `unknown:value`; unknown XBRL axis (code-emitted sentinel path only) → `unknown:xbrlaxis_<hex_encoded_exact_axis_qname>__<normalized_member_value>` so two "Other" axes never merge; (4) whole-company / consolidated / total-company / no stated segment → omit slice. If two different facts in the same event still collide after all structured parts are set, add `quote_hash`.
- **Kind ladder (FS-15 clarification — owner 2026-07-11; mirrored in 12 FACT-26f, served verbatim in EXP-5 packets):** per stated company part: (1) menu match (same meaning; the producer judges; code never near-snaps) → take the menu value + its kind (came from the frozen axis table; never reconsidered). (2) The same normalized label under two or more kinds in the menu with no selecting framing → `unknown:<value>`. (3) Prose-only, kind clear ("our X segment", "revenue in China", a named product) → coin `kind:value`. (4) Prose-only, two or more kinds reasonable → `unknown:<value>` — never guess; a guessed kind is a fake axis-grade confirmation. `unknown:` values enter the company menu, so later producers reuse them — one series per company, no fragmentation from honesty.
- **Why:** Covers every case without forcing a wrong link or a silent merge.
- **Source:** Naming_Slices_XBRL.md §7
- **Replaces:** explicit total → `slice=total` — 95_Supersession #25

#### FS-16 — Code validates format only; never near-match snaps  `[LOCKED]`
- **Plain:** Code only checks the shape of the pick (valid kind, lowercase). It never "snaps" a value to a close match.
- **Rule:** Code validates the pick = FORMAT only (kind ∈ 6+unknown; lowercase/strip punctuation). It must NEVER snap a value to a near-match — that would be a code merge.
- **Why:** A near-match snap is exactly the code merge that could blend two different businesses.
- **Source:** Naming_Slices_XBRL.md §7

## E. Within-company reconciliation

#### FS-17 — A slice value is immutable (first-written wins)  `[LOCKED]`
- **Plain:** Once a slice value is written, it never changes; everything else attaches to it.
- **Rule:** A slice value, once written, is IMMUTABLE. First-written wins; everything attaches to it.
- **Why:** Immutability keeps identity stable so re-runs merge in place instead of forking.
- **Source:** Naming_Slices_XBRL.md §8

#### FS-18 — Code dedupe = exact-after-normalization only  `[LOCKED]`
- **Plain:** Code only folds an XBRL member into an existing value when their normalized labels are exactly equal.
- **Rule:** Code dedupe (deterministic, link-only): an XBRL member whose normalized label EQUALS an existing value's normalized form folds INTO that value (its link clips on) — no new value. Exact-after-normalization only; no guessing.
- **Why:** Exact-only merges are safe; the official member just attaches to the value the producer already coined.
- **Source:** Naming_Slices_XBRL.md §8

#### FS-19 — Producer reuse is semantic (existing values first)  `[LOCKED]`
- **Plain:** The producer sees existing values first, reuses one when the prose names that part, coins new only for a genuinely new part.
- **Rule:** Shown the menu (existing values first), the producer reuses when the prose names that part; coins new only for a genuinely new part; unsure → coin new. The LLM ASSIGNS (never merges two existing identities); code merges only via the exact dedupe (FS-18) or a confident alias — never a fuzzy near-match snap. No match → a new value = its own row (over-split, fixed later by an alias).
- **Why:** Semantic reuse maximizes sharing while coin-new-when-unsure stays over-split-safe.
- **Source:** Naming_Slices_XBRL.md §8

## F. The elimination / corporate guard

#### FS-20 — The elimination / corporate guard (3 buckets, never a regex)  `[LOCKED]`
- **Plain:** On segment axes, filter out accounting "plumbing" members with three exact lists — never a pattern match.
- **Rule:** On segment-family axes only, three buckets, exact lists, NEVER a regex:
  - **HARD-EXCLUDE** = a frozen exact-qname allowlist of ~24 pure eliminations (`IntersegmentElimination`, `ConsolidationEliminations`…) — dropped from the menu, every exclusion LOGGED; one that later shows real activity auto-demotes to provisional.
  - **PROVISIONAL** = ~241 reconciling / Corporate / Other / Unallocated / blended / raw-intersegment members — own row, quarantined from cross-company, never deleted.
  - **KEEP** = every other segment member (~3,000 real segments); a missed coined elimination falls here (over-split-safe).
- **Note:** The ~24 is today's vetted set — a few more pure-elimination members may be added over time as they surface, but this list is **stable and rarely needs updating**.
- **Why:** A regex over-catches real businesses (it flagged Ecolab's `GlobalPestElimination` — ~20% false positives). Vet once by hand, then freeze.
- **Source:** Naming_Slices_XBRL.md §10 · XBRL_SliceAxis_Catalog.md §4

## G. The XBRL member link

#### FS-21 — The XBRL member link is enrichment only  `[LOCKED]`
- **Plain:** The link to an official XBRL member is a bonus, never the identity. It attaches to the fact, not the driver.
- **Rule:** Enrichment only — the slice TEXT identifies the fact, never the link (often missing, ~57% — fine). Needs BOTH the axis and the member (a member alone is meaningless), 0..N per fact, on the FACT (DriverUpdate), NOT the driver class (fix schema:91). Free when the producer picks an XBRL menu row; the resolver only handles off-menu cases.
- **Why:** The text identity works even when XBRL is absent; a wrong link would be the only real failure, so it's kept off the identity.
- **Source:** Naming_Slices_XBRL.md §9

## H. Cross-company + read rule

#### FS-22 — Retired: slice-value recurrence is not a rule  `[RETIRED]`
- **Status:** No active rule. Retired by OD-4; cross-company value comparison remains deferred to FS-23.

#### FS-23 — Cross-company VALUE comparison is a separate, unbuilt layer  `⏳ OPEN`
- **Plain:** Knowing a value's KIND is sure does NOT mean values compare across companies. That layer isn't built yet.
- **Rule:** "CONFIRMED" means the KIND is sure (axis → one of the 6). It does NOT mean VALUES compare across companies ("International"/"Other" mean different things per company). Cross-company value matching is a SEPARATE, not-yet-built layer; the deferred alias map inherits the conservative bar (merge only on confident-same). **OD-17(b) pin:** when built, this layer MUST exclude residual slice values (`segment:other`-class buckets) from cross-company folding.
- **Why:** Comparing "International" at A to "International" at B would silently merge different things → deferred.
- **Source:** Naming_Slices_XBRL.md §12 · XBRL_SliceAxis_Catalog.md status · also in `90_OpenItems.md`

#### FS-24 — Read rule: group by driver + slice + period  `[LOCKED]`
- **Plain:** When reading the data, always group by driver + slice + period together — never by driver alone.
- **Rule:** Consumers must group by driver + slice + period (+ `surprise` on the surprise lane, so the 3 surprise types don't blur — OD-21; the full read/collapse key with measurement/period_scope/series_unit/time_type lives in 09 §7 · 11 T12.1), never by driver alone (else Taco Bell, China, and the company total blur into one line). Provisional values are excluded from cross-company until promoted.
- **Why:** Grouping by driver alone would merge different parts into one meaningless series.
- **Source:** Naming_Slices_XBRL.md §13

## I. Measurement (the version of a number)

#### FS-25 — Measurement = a multi-label set in fact_scope  `[LOCKED]`
- **Plain:** The "version of the number" (adjusted, diluted…) is stored as a set of exact stated words, in its own fact_scope slot. Empty by default.
- **Rule:** `measurement` = a multi-label, code-sorted SET inside fact_scope. Store the SPECIFIC stated label, format-normalized only (case/whitespace/punctuation; no stemming): `{adjusted}` · `{constant_currency}` · `{core}`. For serialization, normalize each token, code-sort tokens, then comma-join inside the slot (`measurement=adjusted,constant_currency` for source-separated spans). Default = empty — NEVER assume gaap. A novel qualifier ("cash" in "cash EPS") is kept verbatim after the same format-normalization as its own token. gaap/non_gaap is a READ-TIME grouping view, never the stored key. Multi-label because flavors stack — **but contiguous flavors are ONE token** ("adjusted diluted EPS" = `{adjusted_diluted}`; OD-9 maximal-span), separate tokens only for source-separated spans ("adjusted … on a constant-currency basis" = `{adjusted, constant_currency}`). A measurement word re-expresses the SAME quantity through a different lens; a word that changes WHICH portion is counted is never a measurement token — it belongs in the name (OD-17).
- **Why:** A single-slot tag would merge "GAAP basic" with "GAAP diluted"; storing the specific word keeps "Adjusted EPS" ≠ "Core EPS", so the same base metric can carry opposite verdicts.
- **Source:** Naming_Slices_XBRL.md §5 / §1
- **Replaces:** the full version of NAME-14 — 95_Supersession #2
- **OD-9 tokenization pins (owner-approved 2026-07-06 · 66 §0.R OD-9):**
  - **Producer copies, code normalizes:** the producer copies the exact source qualifier span(s) into a TRANSIENT `measurement_raw_spans` (propose-then-discard, like the shape/unit hints — NOT a stored field; the verbatim text lives in `quote`); it never invents the final token. **Code alone** normalizes each span: **lowercase → every run of non-alphanumeric chars → `_` → trim `_` → collapse repeats.**
  - **Maximal contiguous spans:** contiguous qualifier words = ONE token ("adjusted diluted" → `adjusted_diluted`); separate tokens only for source-separated (non-contiguous) spans ("adjusted … constant-currency basis" → `{adjusted, constant_currency}`). No "one concept or two" judgment. **Contiguity defined (owner 2026-07-11):** qualifier words separated only by punctuation or whitespace form ONE contiguous span ("adjusted, diluted" ≡ "adjusted diluted" → `adjusted_diluted`); a span splits only where non-qualifier prose intervenes.
  - **Never-drop safety SINK (natural-home routing):** each qualifier routes to its NATURAL slot — a time-window like TTM belongs in the PERIOD slot (rolling-12M window ending on the source date), a version/basis belongs in measurement — but leaves measurement ONLY if that slot captures its exact meaning LOSSLESSLY. So TTM → period IF the period resolver builds the true rolling-12M window (≠ FY); else keep `measurement=ttm` as the never-drop safety tag (so TTM EBITDA can't merge with FY EBITDA). Measurement is the fail-closed bucket for any number-modifier NOT fully+losslessly captured by driver / period / unit / slice / the OD-11 growth-basis unit. Unsure → keep. **Never drop.** Boundary: version/basis of the same quantity → measurement; a different quantity → the driver name.
  - **No write-time synonym merging, no closed list, no human, no write-time aliasing;** equivalent-label grouping is READ-TIME only and never changes a stored id.
## J. Declared continuity (CONTINUES_AS)

#### FS-26 — CONTINUES_AS: declared, company-scoped, read-time continuity  `[LOCKED — owner 2026-07-11 · 66 §0.R OD-20]`
- **Plain:** When a company explicitly says "the old label continues as the new one, nothing else changed", we store that declaration and chain the two series at read time. Never a merge; always reversible; only for that company.
- **Rule:** `CONTINUES_AS` = a company-scoped, directional (old → new), dated continuity declaration. Created ONLY when company text explicitly asserts the old name/label continues as the new with composition/methodology unchanged; any recast/recompose/reclassify language BLOCKS it (a code lexical pre-scan auto-refuses before the judge). Endpoints: driver names, slice-value labels, or measurement tokens — bound to the EXACT declared endpoint only, never propagated across `_guidance`/`_surprise`, family, or `BASE_METRIC` links (the cross-flavor permanent refusal applies unchanged).
- **Detection (propose-then-verify):** the producer reading the declaring event emits a TRANSIENT `continuity_hint {kind, old, new, quote}` (discarded after write — the same spine as the shape/unit hints); no standing detector, no new LLM pass.
- **Confirmation:** the strong-judge tier via the LINK-judge harness with a DEDICATED continuity instruction block (NOT the five sameness checks — continuity is licensed by the company's declaration, not judged sameness). Blind, code-assembled input (the producer's rationale never reaches the judge). CONFIRM iff the quote explicitly asserts old→new continuity AND asserts composition/methodology unchanged AND names both endpoints; REFUSE otherwise (fail-closed).
- **Storage:** driver-name endpoints → `(:Driver)-[:CONTINUES_AS {company_cik, evidence_quote, source_event_id, declared_at, created, quarantined}]->(:Driver)` (the `SAME_AS` structural twin — inherits the kernel §10 edge stack). Slice-label / measurement-token endpoints (strings inside fact_scope — they cannot anchor edges) → a reified `(:ContinuationClaim {company_cik, kind: slice_label|measurement_token, old, new, evidence_quote, source_event_id, declared_at, created, quarantined})`, indexed by (company_cik, kind, old) AND (company_cik, kind, new). `CONTINUES_AS` is a class-level link minted live by producers (like live `SAME_AS`) — never part of DU-20's fact-edge inventory.
- **Determinism guards (code, inside the commit transaction):** at most ONE non-quarantined continuation per (company_cik, kind, old) — fan-OUT refused; a second distinct old declaring into the same new within (company_cik, kind) — fan-IN — auto-quarantines both (suspected undeclared recomposition; keep split); a continuation that would close a cycle auto-refuses. All three are STATE-BASED/reversible refusals, never permanent-by-locked-rule.
- **Read:** consumed ONLY by labeled read-time reconciled views (12 FACT-36): raw FACT-33 groups → gather this company's non-quarantined continuations with `declared_at` < as_of (applied PER HOP) → resolve the chain to its as_of-relative terminal → relabel non-terminal segments to the terminal grouping key → label `reconciled`. Deterministic (guaranteed by the fan-out/cycle guards); no model calls at read; never changes a stored id, fact, or fact_scope.
- **PIT:** the gate is `declared_at` (the declaring event's public time — FS-14's source-time discipline), per hop; `created` is the forensic anchor only, never a gate. Asymmetry (kernel axiom C): PIT gates the APPLICATION of a continuation; a quarantine SUPPRESSES it regardless of when discovered — the over-split-safe direction.
- **Recovery:** quarantine via the existing kernel §10 lane (signal-quarantine → two blind strong graders → `quarantined=true` flip + `RecoveryEvent`; V14 extended to cover `ContinuationClaim.quarantined` as a reversible recovery-lane boolean). Where an endpoint is XBRL-backed, the kernel §9 falsifier runs as a tripwire across the declared boundary (concept split / opposite-direction discontinuity → quarantine); for no-XBRL endpoints the false-continuity residual is the documented kernel §16 class.
- **Why:** the only healer for declared renames and for the ~57% of facts with no XBRL member link (FS-21), while fully honoring OD-17/NAME-04/`SAME_AS` strict identity — it groups at read while identity stays split; read-only + reversible keeps it lawful under the one law. Complementary to T12.9 (both deterministic read-time remaps; they compose).
- **Machinery (honest tally):** one edge type + one record type + three deterministic guards + one judge instruction block + one falsifier lane + one V14 clause. Subsumes review items T2-02/T2-05; the label-similarity variant of T2-02 stays rejected.
- **Source:** owner decision 2026-07-11 (CONTINUES_AS clarification) · Fable final deep-dive review
- **Replaces:** — (addition)
