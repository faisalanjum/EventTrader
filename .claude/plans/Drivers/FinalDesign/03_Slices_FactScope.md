# 03 · Slices & fact_scope

**What this is:** how a single fact is *identified* and *bifurcated*. `fact_scope` = the "which part of the company + which time window + which version of the number" tag that separates same-event, same-driver facts. This section owns the **slice** (which part) and **measurement** (which version); **period** lives in its own section (DriverPeriod).

> Every rule below is **LOCKED** unless marked **⏳ OPEN**. Where a rule replaced an older one, **Replaces** points into `95_Supersession.md`. Source of the rules = `Naming_Slices_XBRL.md`; the axis data = `XBRL_SliceAxis_Catalog.md`.

**Still open in this section:** FS-23 (cross-company value comparison), tracked in `90_OpenItems.md`. *(FS-14 point-in-time — RESOLVED 2026-07-02: PIT for DriverUpdate write-time.)*

---

## A. fact_scope = a fact's identity

#### FS-01 — fact_scope is a fact's identity  `[LOCKED]`
- **Plain:** A fact's identity = event + driver + fact_scope. `fact_scope = period + slice + measurement`.
- **Rule:** fact ID = event + driver + fact_scope (NO producer). Code builds the ID from the parts the LLM extracts — the LLM never builds the ID.
- **Why:** A code-built, producer-free key means two readers of the same fact converge to one node.
- **Source:** Naming_Slices_XBRL.md §1

#### FS-02 — fact_scope is one canonical string  `[LOCKED]`
- **Plain:** The parts join into one string in a fixed order. If no part is stated, leave the slice empty. Use a quote hash only when two different facts in one event still collide.
- **Rule:** Serialized as ONE canonical string, named parts in a fixed order (`period=…|slice=segment:enterprise|measurement=adjusted`). If the source names no business part, omit the slice slot; do NOT default to total and do NOT add a quote hash. Add `quote_hash=<hash>` only as the FS-03 tie-breaker when the structured parts still cannot separate two different facts in one event. **Identity uses format-normalization only** (case/whitespace/punctuation); per-company alias files that unify drift are **read-time views + member-matching, NEVER part of the id** — else growing an alias file would change a fact's id (ids are immutable). *(Pinned with 09.)*
- **Why:** One fixed string → the same fact always makes the same key; code builds/compares it deterministically.
- **Source:** Naming_Slices_XBRL.md §1 · DriverGraphSchema.md §4

#### FS-03 — quote_hash is a tie-breaker only  `[LOCKED]`
- **Plain:** The quote-hash is only for two genuinely different facts in one event the structured parts can't split.
- **Rule:** `quote_hash` is added ONLY when the structured slot can't separate two different facts in one event (same slot, different value-hash). Restatements (same value) merge; never added when the structured scope already identifies the fact.
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
- **Plain:** Every fact-type can be sliced. Explicit company-wide reads use "Total" for display, stored as `total`. Time is not a slice.
- **Rule:** Slices apply to ALL 4 fact_types. Explicit company-wide → serialized value `total` (display label "Total"). Silence/no stated part → no slice. Never default silence to `total`. period (time) is NOT a slice — it's its own fact_scope part (DriverPeriod).
- **Why:** "Which part" is orthogonal to "what kind of statement"; total-only-on-explicit-read stops silence being mislabeled as company-wide.
- **Source:** Naming_Slices_XBRL.md §4

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
- **Point-in-time (LOCKED 2026-07-02):** For **DriverUpdate write-time** producers, the menu is **restricted to filings at or before the event date** (both the XBRL-members half **and** the catalog-history half cut at ≤ T) — a historical/backfill fact never sees a future segment structure (*err over-split, never leak*). **3-context split:** driver-**name** creation → slice-menu PIT is N/A (names carry no slice) · DriverUpdate **write** → PIT · **read / offline repair** → all known history OK (no fact is being written). *(Slice-value immutability (FS-17) is orthogonal — both hold. Same cutoff as the concept-link menu, XC-09.)*
- **Why:** A union across filings (not just the latest) maximizes reuse — a fact about a discontinued/renamed segment finds its existing value instead of coining a duplicate.
- **Source:** Naming_Slices_XBRL.md §7 *(menu contents extended from "latest prior" → "union of all prior filings"; PIT re-locked per owner, 2026-07-02 — see 90_OpenItems §E)*

#### FS-15 — The producer's 4 outcomes per fact  `[LOCKED]`
- **Plain:** For each fact the producer picks a menu value, coins one, marks it unknown, uses explicit total, or leaves the slice empty. A quote-hash is only a last tie-breaker.
- **Rule:** (1) on menu → pick (code supplies kind + a free XBRL link); (2) real, off-menu → coin in-style (no link); (3) no kind fits → `unknown:value` (unknown XBRL axis → carry the axis → `axis:value`, so two "Other" axes never merge); (4) explicit company-wide read → `total`; no stated part → omit slice. If two different facts in the same event still collide after all structured parts are set, add `quote_hash`.
- **Why:** Covers every case without forcing a wrong link or a silent merge.
- **Source:** Naming_Slices_XBRL.md §7

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

#### FS-22 — Recurrence means OPPOSITE things for names vs values  `[LOCKED]`
- **Plain:** A driver NAME repeating across companies is good (breadth). A slice VALUE repeating across companies is a red flag (it's generic, like "Other").
- **Rule:** A DRIVER NAME that recurs across companies → REAL (breadth). A SLICE VALUE that recurs across companies → GENERIC (Corporate/Other/International), NOT a real brand. A real specific part lives at ONE company. Promoting a provisional value to cross-company-eligible needs the REAL signal (persistent magnitude on a confirmed axis), NEVER recurrence alone.
- **Why:** Stops generic buckets ("International", "Other") being treated as comparable real businesses.
- **Source:** Naming_Slices_XBRL.md §11

#### FS-23 — Cross-company VALUE comparison is a separate, unbuilt layer  `⏳ OPEN`
- **Plain:** Knowing a value's KIND is sure does NOT mean values compare across companies. That layer isn't built yet.
- **Rule:** "CONFIRMED" means the KIND is sure (axis → one of the 6). It does NOT mean VALUES compare across companies ("International"/"Other" mean different things per company). Cross-company value matching is a SEPARATE, not-yet-built layer; the deferred alias map inherits the conservative bar (merge only on confident-same).
- **Why:** Comparing "International" at A to "International" at B would silently merge different things → deferred.
- **Source:** Naming_Slices_XBRL.md §12 · XBRL_SliceAxis_Catalog.md status · also in `90_OpenItems.md`

#### FS-24 — Read rule: group by driver + slice + period  `[LOCKED]`
- **Plain:** When reading the data, always group by driver + slice + period together — never by driver alone.
- **Rule:** Consumers must group by driver + slice + period, never by driver alone (else Taco Bell, China, and the company total blur into one line). Provisional values are excluded from cross-company until promoted.
- **Why:** Grouping by driver alone would merge different parts into one meaningless series.
- **Source:** Naming_Slices_XBRL.md §13

## I. Measurement (the version of a number)

#### FS-25 — Measurement = a multi-label set in fact_scope  `[LOCKED]`
- **Plain:** The "version of the number" (adjusted, diluted…) is stored as a set of exact stated words, in its own fact_scope slot. Empty by default.
- **Rule:** `measurement` = a multi-label, code-sorted SET inside fact_scope. Store the SPECIFIC stated label, format-normalized only (case/spacing; no stemming): `{adjusted}` · `{diluted, gaap}` · `{core}`. Default = empty — NEVER assume gaap. A novel word ("cash EPS") is kept verbatim as its own token. gaap/non_gaap is a READ-TIME grouping view, never the stored key. Multi-label because flavors stack ("adjusted diluted EPS" = `{adjusted, diluted}`).
- **Why:** A single-slot tag would merge "GAAP basic" with "GAAP diluted"; storing the specific word keeps "Adjusted EPS" ≠ "Core EPS", so the same base metric can carry opposite verdicts.
- **Source:** Naming_Slices_XBRL.md §5 / §1
- **Replaces:** the full version of NAME-14 — 95_Supersession #2
