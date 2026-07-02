# Driver Naming, Slices & XBRL — Final Spec

## 0. The idea, and the one law everything obeys

- **Driver** = a cause that moves a stock (`same_store_sales`, `eps`). One plain name.
- **Fact** (DriverUpdate) = one event-level fact about a driver — a measured value, a forecast, a surprise, or an action (numeric *or* qualitative). e.g. "+8% this quarter", "raised FY guidance", "closed the Ohio plant".
- **Slice** = which *part* of the company the fact is about (North Italia, China, iPhone).
- **Measurement** = which *version* of the number (adjusted, diluted, constant-currency).
- **Link** = an optional pointer to the company's official filing row. A bonus, never the ID.

**The one law (memorize this — every rule below is just an application of it):**
```
OVER-MERGE  (blending two different things into one)  = PERMANENT damage → must NEVER happen
OVER-SPLIT  (one thing accidentally in two rows)      = a 1-line fix     → always acceptable
When unsure → keep separate.
```

**Asymmetric authority — the rule that makes it fully autonomous AND safe:**
```
The LLM may:    ASSIGN each fact to a value (pick an existing menu value, or coin-new) · mark PROVISIONAL  ← over-split-safe
                — it NEVER merges two EXISTING identities together.
CODE alone may: DELETE (frozen list) · MERGE two existing values, and only EXACTLY/confidently — never fuzzy/global.
```
So the system is **correct from day one no matter how wrong the LLM is** — accuracy only affects how much harmless noise there is, never the truth. No human in the loop.

## 1. The parts of a fact, and its ID

```
fact ID    = event + driver + fact_scope                 (NO producer)
verdict ID = event + driver + fact_scope + producer      (the grade can differ per producer)
fact_scope = period + slice + measurement   (use whichever structured parts exist)
             quote_hash = TIE-BREAKER — added only when the structured slot can't separate two genuinely-different
             facts in the same event (same slot, different value-hash). Restatements (same value) merge; never added
             when the structured scope already identifies the fact uniquely (so restatements aren't over-split).
```
**Code** builds the ID from the words the LLM extracts. **The LLM never builds the ID.**

## 2. NAME vs SLICE — the core decision

**Brand / segment / geography / product / customer / channel go in the SLICE, not the name.** The driver name holds *only the cause*.
```
WRONG                          RIGHT
taco_bell_same_store_sales  →  same_store_sales + slice=segment:taco_bell
china_revenue               →  revenue          + slice=geography:china
iphone_revenue              →  revenue          + slice=product:iphone
```

**The exception — when it DOES go in the name.** Ask, in order:
```
0. PRE-FILTER: strip direction/impact words first (rose, fell, growth, decline, headwind, pressure) —
   never in the name. Direction of the DRIVER → driver_state; impact on the COMPANY → the EXPLAINED_BY
   verdict.   "FX headwind" → driver=foreign_exchange; what FX did → driver_state only if stated; the
   "headwind" (negative impact) → the EXPLAINED_BY verdict.
1. Strip the brand/part. Is a normal reusable cause left (revenue, margin, same-store sales, a recall)?
        → YES → SLICE it (base name + slice tag).
2. Only a fragment that needs an object (demand, ban), OR that exact brand/product is itself what
   moves OTHER companies?
        → YES → NAME it.
   When unsure → SLICE.
```

| Phrase | Verdict |
|---|---|
| iPhone demand · GLP-1 pressure · TikTok ban | **NAME** (`iphone_demand`…) — the thing itself moves other companies |
| Taco Bell menu innovation · Cybertruck recall · China revenue | **SLICE** (`menu_innovation`+`segment:taco_bell`, `product_recall`+`product:cybertruck`, `revenue`+`geography:china`) |

> This **reverses** the old "brand = its own driver" rule (R9 / DriverOntology.md) — that doc must be aligned to slice-first. It is safe: nothing is live yet (the ~39 baked-in names in the existing catalog are files, rewritten to base+slice, **never** SAME_AS-merged).

## 3. What stays IN the name (and what never does)

```
IN the name:   the cause · per-X denominators (oil_price_per_barrel, dividend_per_share,
               sales_per_square_foot) · benchmark identity (brent_oil_price, wti_oil_price)
NOT the name:  brand/segment/geo/product/customer/channel (→ slice) · adjusted/diluted/constant-cur
               (→ measurement) · headwind/growth/up/down (→ driver_state)
```
**Why per-X stays in the name:** the read key has *no slot* for it — `$/barrel` and `$/tonne` both look like plain dollars, so two different per-X would merge unless the name separates them. Different per-X = a different driver, never SAME_AS.

## 4. The SLICE = KIND : VALUE

```
slice = KIND : VALUE
   KIND  = one of 6 fixed kinds  (+ unknown = safe 7th)
   VALUE = the specific part (free text)
```
**The 6 kinds** (a value is a slice only if the company **operates as / in / sells** it — works for *any* metric, not just revenue; accounting labels like "Level 2 fair value", "Term Loan", "RSUs" are **not** slices):

| Kind | The part the company… | Example value |
|---|---|---|
| **segment** | operates as (incl. brands) | `north_italia`, `taco_bell` |
| **product** | sells | `iphone`, `aws` |
| **geography** | operates in | `china`, `international` |
| **customer** | sells to | `major_customer_a` |
| **channel** | sells through / runs as (incl. franchised vs company-run) | `franchised`, `online` |
| **entity_ownership** | owns a stake in (JV / equity-method) | `jv_x` |

Rules for the slice:
- **"Brand" is not a kind.** A brand's kind comes from its **axis** (Taco Bell sits on the business-segments axis → `segment`). For menu rows the kind comes from the frozen table; for prose-only parts the producer picks the kind, code validates it's one of the 6.
- **Two parts at once** → multi-valued, code-sorted: `segment:taco_bell;geography:china`. Never drop a part.
- **Slices apply to ALL 4 fact_types** (metric, guidance, surprise, action_event) — the "which part" is orthogonal to "what kind of statement." Company-wide actions → `Total`. (The state-word lanes and the BASE_METRIC link are governed by DriverGraphSchema.md, not here.)
- `period` (time) is **not** a slice — it's its own fact_scope component (the resolved `DriverPeriod`, governed by GuidancePeriod.md).

## 5. MEASUREMENT (the version of the number)

```
measurement = a multi-label, code-sorted SET inside fact_scope
   STORE the SPECIFIC stated label, format-normalized only (case/spacing; no stemming)
        {adjusted} · {diluted, gaap} · {adjusted, constant_currency} · {core} · {cash}
   default = empty / unspecified — NEVER assume gaap
   unknown/novel word ("cash EPS") → kept verbatim as its own token (own row, never merged)
   gaap / non_gaap = a READ-TIME grouping VIEW, derived — NEVER the stored key
```
**Why multi-label:** flavors stack. "Adjusted diluted EPS" = `{adjusted, diluted}`; "GAAP basic EPS" = `{basic, gaap}`. A single-slot tag would merge "GAAP basic" with "GAAP diluted" → over-merge. **Why store the specific word, not the coarse bucket:** "Adjusted EPS" and "Core EPS" are different non-GAAP measures — collapsing both to `non_gaap` is a code-level auto-merge. Store `{adjusted}` ≠ `{core}`; compute the coarse bucket only at read time.
This lets the same fact carry opposite verdicts: `eps {gaap}` missed → short; `eps {adjusted}` beat → long — separate facts.

**Worked:** "Adjusted EPS" → `driver_name=eps`, `measurement={adjusted}` (NOT `adjusted_eps`) — this **intentionally reverses** the old `adjusted_eps`-in-name rule.
> ⚠ **Cross-doc (separate edit, separate approval):** the BASE_METRIC family rules (`MetricGuidanceFamily.md`, `DriverGraphSchema.md`) must be aligned — basis is a *measurement*, not a name suffix, so there is no `adjusted_eps` base, only `eps` + measurement.

## 6. The FROZEN axis→kind table (the deterministic core)

The "operate as/in/sell" test was a **one-time discovery tool** (run once, by us). Its output is a **frozen lookup table** baked into code; runtime is a pure exact-string lookup → **100% deterministic**.
```python
SLICE_AXES = { "us-gaap:StatementBusinessSegmentsAxis":"segment",
               "srt:ProductOrServiceAxis":"product", … }   # frozen
NON_SLICE_AXES = { …vetted measurement/timing/totaling axes… }   # frozen
def slice_of(axis): ...   # SLICE_AXES → kind · NON_SLICE_AXES → skip · else → provisional
```
**The 3-way runtime rule (the flipped default / sentinel):**
```
axis in SLICE_AXES      → use its kind
axis in NON_SLICE_AXES  → skip (vetted non-business)
anything else           → PROVISIONAL slice (over-split-safe), NEVER silently skipped
```
**Why the default is "provisional slice," not "skip":** company-coined slice axes are common (e.g. `ppl:ByCompanyAxis`, 363 uses). Silently skipping a real coined slice axis would merge real businesses = over-merge. Slicing it provisionally can only over-split.

> **DATA SLOT — pin from confirm-c (mechanism is final; only the list contents are pending):** add the missed slice axes; drop the 2 leaks (`ConsolidationItemsAxis`, `ConsolidatedEntitiesAxis`); confirm only **strong-consensus** axes — the 3 standard-but-missed axes become **CONFIRMED**, the genuinely company-coined ones stay **provisional**; weak-vote axes (e.g. `ppl:RatesTypeAxis`) → provisional. entity_ownership: lock equity-method/JV; the rest of that bucket → provisional. → **The actual axis list (51 slice axes across all kinds + member examples + the §10 elimination qname tiers + census + provenance) lives in [`XBRL_SliceAxis_Catalog.md`](XBRL_SliceAxis_Catalog.md).**

## 7. The per-company MENU (build · point-in-time · pick)

```
menu(company, kind) = XBRL members (bucketed by the frozen table)  ∪  values the catalog already used
```
- **Point-in-time:** build from member data available at-or-before the event time (`≤ T`). 8-K / transcript / news events usually carry no usable member breakout of their own, so they fall back to the latest prior available 10-Q/10-K — *unless the event itself has usable member data*. **Never** future data. The catalog-history half is also cut off at `T`.
- **The producer's 4 outcomes per fact:**
```
on the menu          → pick it       → consistent value; code supplies the kind + the official link FREE
                                        (free link only for XBRL-sourced rows; catalog-memory rows may have none)
real, off the menu   → coin in-style → consistent value, no link (fine)
real, no kind fits   → unknown:value · for an unknown XBRL axis, carry the axis: axis:value
                                        (so two different "Other" axes never merge)
no clean part        → Total (only on an explicit company-wide read) · else quote_hash
```
- **"Total" is never the default for silence** — only on a positive "total/consolidated/company-wide" read. Total is its own row, with **no** link.
- **Code validates the producer's pick = FORMAT only** (kind is one of 6+unknown; lowercase/strip punctuation). It must **never** snap a value to a near-match — that would be a code merge.

## 8. WITHIN-company reconciliation (first name wins)

```
1. A slice value, once written, is IMMUTABLE. First-written wins; everything attaches to it.
2. Code dedupe (deterministic, link-only): an XBRL member whose normalized label EQUALS an existing
   value's normalized form folds INTO that value (its link clips on) — no new value created. Exact-after-
   normalization only; no guessing.
3. Producer reuse (semantic): shown the menu (existing values first), the producer reuses an existing
   value when the prose names that part; coins a new value only for a genuinely new part.
4. Within-run: values coined earlier in a run are added live so later events in the run reuse them.
5. The LLM ASSIGNS each fact to a value (its explicit, prose-grounded pick, or coin-new), guarded by
   "unsure → coin new" — it never merges two EXISTING identities. Code may merge two existing values ONLY
   via the exact dedupe (step 2) or the confident alias — never a fuzzy near-match snap.
6. No match → a NEW value = its own row (over-split, fixed later by an alias). Never an auto-merge.
```
This is also how a later official name reconciles to an earlier coined one: the official member folds onto the existing value (a phone-contact gets the official ID added; it never starts a new line).

## 9. The XBRL LINK (enrichment only)

```
• Never the identity — the slice TEXT identifies the fact. Often missing (~57%) — fine.
• Needs BOTH the axis and the member (a member alone is meaningless). 0..N per fact.
• Attaches to the FACT (DriverUpdate), NOT the cause (Driver).  ← FIX schema:91 (it's on the class today).
• Free when the producer picks an XBRL menu row; the resolver only handles off-menu cases.
```
> **Concept-side algorithm (the off-menu resolver):** fully specced + census-validated in
> [`XBRLConceptLinking.md`](XBRLConceptLinking.md) — guard → company menu → LLM pick → adversarial
> verify → deterministic backstop; Haiku + backstop + abstain-fix. This §9 governs the member/slice
> side; the concept side lives there. (Its §4 menu adopts this file's §7 point-in-time cutoff.)

## 10. The ELIMINATION / CORPORATE guard (member level)

The business-segments axis also carries reconciliation members (eliminations, corporate, intersegment) — already leaking into the real catalog as fake segments. Guard with **three buckets, exact lists, never a regex** (a regex deletes real segments like `GlobalPestElimination`):
```
HARD-EXCLUDE = a FROZEN exact-qname allowlist of vetted PURE eliminations (~24; false-positives removed)
               → dropped from the menu, and EVERY exclusion is LOGGED (a wrongly-caught segment surfaces).
               Self-corrects: a hard-excluded qname that shows real fact activity → auto-demote to provisional.
PROVISIONAL  = the ~241 (reconciling items · Corporate/Other/Unallocated · blended · raw intersegment)
               → own row, quarantined from cross-company, NEVER deleted.
KEEP         = every other member (real segment). A new coined elimination the list misses → falls to KEEP
               = over-split-safe (a junk row, never a merge).
```

## 11. AUTONOMY & self-improvement (no human in the loop)

```
The LLM routes (KEEP / PROVISIONAL / coin) from a FIXED concise rule + a capped set of examples.
It NEVER deletes or merges. So every LLM error is over-split (recoverable) — truth is structural.

Self-improvement (autonomous, grounded — never the LLM's own guesses):
   strong REAL example     = persistent real magnitude over several periods  +  on a CONFIRMED slice axis
   strong PLUMBING example = exact match on the frozen elimination list
   weak hints (low weight) = has-an-XBRL-member · recurs-across-companies
   PROMOTE (provisional → cross-company-eligible) needs the REAL signal — NEVER recurrence alone.

⚠ Recurrence means OPPOSITE things:
   a DRIVER NAME that recurs across companies → REAL (breadth from reuse).
   a SLICE VALUE that recurs across companies → GENERIC (Corporate/Other/International), NOT a real brand.
   A real specific part lives at ONE company.

The core RULE is fixed; only examples accumulate (capped, diverse) → sharpens without drifting.
```

## 12. CROSS-company comparison = a separate, not-yet-built layer

```
"CONFIRMED" means the KIND is sure (the axis → one of the 6). It does NOT mean the VALUES compare
across companies — "International"/"Other"/building-names mean different things per company.
Cross-company value matching is a SEPARATE layer we have not built; the deferred alias map that would
do it inherits the conservative bar (merge only on confident-same, else keep separate).
```

## 13. Read rule
Consumers must group by **driver + slice + period**, never by driver alone (else Taco Bell, China, and the company total blur into one line). Provisional values are excluded from cross-company comparison until promoted.

## 14. Honest caveats / open
- The big bet — *the same cause gets the same name across companies* — has **never been tested** (0 driver nodes built).
- Cross-company value comparison is unbuilt (§12).
- The exact frozen-axis list is pending **confirm-c** (§6 data slot). Mechanism is final.

---

## THE RULES (complete, lockable — every rule in one place)

```
IDENTITY
 1. fact ID = event + driver + fact_scope.  verdict ID = + producer.  Code builds it; the LLM never does.
 2. fact_scope = period + slice + measurement.  quote_hash = tie-breaker when the structured slot can't separate
    two different facts in one event (same slot, different value-hash); restatements (same value) merge.

NAME vs SLICE
 3. Driver name = the cause only. Brand/segment/geography/product/customer/channel → the SLICE, never the name.
 4. Name it only if: stripping the part leaves no normal cause, OR that exact brand/product itself moves
    OTHER companies (iphone_demand, glp1_pressure, tiktok_ban). Unsure → slice.
 5. Pre-filter: strip direction/impact words first (rose/fell/growth/headwind/pressure) → never the name;
    driver-direction → driver_state, company-impact → the EXPLAINED_BY verdict.
 6. Per-X denominators (oil_price_per_barrel, dividend_per_share) and benchmarks (brent_oil_price) stay in
    the name. Different per-X = a different driver, never SAME_AS.

SLICE
 7. slice = KIND:VALUE. KIND ∈ {segment, product, geography, customer, channel, entity_ownership} (+ unknown).
    VALUE = free text. A value is a slice only if the company operates-as/in/sells it; accounting labels are not.
 8. Kind comes from the AXIS (menu rows) or the producer (prose). "Brand" is not a kind.
 9. Two parts at once → multi-valued, code-sorted (segment:taco_bell;geography:china). Never drop a part.
10. Slices apply to ALL 4 fact_types. Company-wide → Total. period is not a slice.

MEASUREMENT
11. measurement = multi-label sorted SET in fact_scope. Store the SPECIFIC stated label, format-normalized only.
12. Default = empty/unspecified — never assume gaap. Novel words kept verbatim.
13. gaap/non_gaap is a READ-TIME grouping view, never the stored key.

FROZEN TABLE & SENTINEL
14. axis→kind is a FROZEN code table; runtime = exact-string lookup (deterministic). Refreshed offline only.
15. Runtime 3-way: in SLICE_AXES → its kind · in NON_SLICE_AXES → skip · else → PROVISIONAL (never silently skip).
16. Confirm only strong-consensus axes; weak/coined → provisional. (Exact list pinned from confirm-c.)

MENU & LINK
17. menu = XBRL members (frozen-table-bucketed) ∪ catalog's prior values. Built point-in-time (≤ T); 8-K/
    transcript → usually the latest prior available 10-Q/10-K (unless the event has usable member data);
    never future data; catalog-history half also cut off at T.
18. Menu pick → code supplies kind + link. Off-menu → producer emits kind/value; code validates FORMAT only,
    never a near-match snap.
19. unknown XBRL axis slice carries its axis (axis:value); prose-unknown = unknown:value.
20. Blank is never guessed: states a part → that · explicit "total/consolidated" → Total · can't tell → quote_hash.
21. XBRL link = enrichment, on the FACT (fix schema:91), needs axis+member, 0..N, often absent — never the ID.

RECONCILIATION
22. A slice value is IMMUTABLE once written (first-written wins).
23. Code dedupe = exact-after-normalization only (folds a matching XBRL member onto an existing value).
24. Producer reuses an existing menu value for the same part; coins new only for a genuinely new part.
25. Code NEVER merges identities; only the producer's explicit prose pick does. No fuzzy near-match snap, anywhere.
26. No match → a new value (own row, over-split-safe). Cross-company value matching is a separate unbuilt layer.

ELIMINATION GUARD
27. HARD-EXCLUDE = frozen exact-qname allowlist of vetted pure eliminations; LOG every exclusion;
    auto-demote any excluded qname that shows real fact activity.
28. PROVISIONAL = reconciling/corporate/other/blended/intersegment → own row, quarantined, never deleted.
29. KEEP = all other members; a missed coined elimination falls here (over-split-safe). No regex, ever.

AUTONOMY & SAFETY
30. OVER-MERGE never happens via code; OVER-SPLIT is acceptable. When unsure → keep separate.
31. The LLM ASSIGNS each fact to a value (pick-existing or coin-new) + marks PROVISIONAL — never merges two
    existing identities. CODE alone DELETES (frozen list) and MERGES existing values (exact/confident-only).
32. Self-improve from CODE-VERIFIED examples only (real = persistent magnitude + confirmed axis; plumbing =
    exact elimination match; recurrence/link = weak hints). Recurrence is positive for NAMES, negative for VALUES.
    Core rule fixed; examples capped. No human in the loop.
33. Consumers read by driver + slice + period, never driver alone; provisionals excluded from cross-company.
```

## Glossary (plain → field)
`slice`=fact_scope slice · `measurement`=the basis/flavor set (extends guidance `basis_norm`) · `sentence-fingerprint`=quote_hash · `official row/category`=XBRL member/axis · `direction word`=driver_state · `fact`=DriverUpdate
