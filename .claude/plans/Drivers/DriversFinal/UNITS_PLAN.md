# Units plan (#3): final proposal for approval · v5 · 2026-10-02

**Status:** applied. v4 is in commit 65f8d7da9 and v5 (cents) in commit d7824830d. Codex approved both. This file stays as the record of why each rule reads as it does.
- v1 (sha256 `eb31f321…`) was reviewed by Codex in `/tmp/driver_units_review_20261002/full_plan_review/REVIEW.txt`.
- v2 took in all of that review except the bare "$" sentence.
- v3 added the "$" wording that Codex accepted as a deliberate project convention (§6).
- v4 took in Codex's final wording review (`/tmp/driver_units_review_20261002/v3_review/REVIEW.txt`). It was applied in commit 65f8d7da9.
- v5 (owner decision, 2026-10-02): the bare-"$" convention also covers a bare "¢" or "cents" (25 cents → 0.25 `usd`), because US filings write cents without "U.S." just as they write "$".

**Goal:** assign units from source evidence, with the explicit bare-dollar USD convention in 9.1. Supported units form comparable histories. Remaining unresolved units stay readable individually as `unknown` and are counted. Exact rescaling is allowed; currency exchange and conversion between different physical-unit IDs are not. The change stays small and contradicts no other rule.

**Line numbers** refer to the files as they are now, before any edit.

---

## 1. Evidence (measured 2026-10-02; Neo4j read-only)

| What | Result |
|---|---|
| Unit links (tagged facts, nil facts included) | 6,957 Unit nodes; 12,432,556 fact→unit links: USD 10,573,937 · shares 691,897 · pure 630,170 · USD/share 327,402 |
| Links without registry metadata | 138,133 |
| Company-made units | 98,038 links, 1,458 names. Mostly counts of things or days, **but not all**: metricton, barrel, megawatt, squarefoot, mmbtu, mwh, `nova:FICO_score`, `spr:uSDollarPerHour`, `mur:barrels_per_day` |
| Physical and time links with registry metadata | ≈24,200 (volume, area, energy, mass, power, length, flow, voltage), plus 6,712 per-unit links that are mostly money per X. Some company physical labels have no registry metadata. Metadata shows what was tagged; it doesn't certify meaning. |
| Non-USD money links | 34,237 links over 42 non-USD codes. **CP: 12,186 CAD vs 396 USD (97% of CP's money)**, which is 35.6% of all non-USD links. Aflac: 1,428 JPY |
| Wrong-looking filing tags | Hexcel 10-Q: 18 links tagged `CHE` (WIR Euro) on euro loans · AZEK 10-Q: 4 links tagged `XUA` (ADB unit of account) while its statements are in US dollars · also `XBA` (MAN), `XUA` (CDNA, BECN). Codex traced all 27 to the original filings. |
| "$" wording (unverified lexical sample) | 400 recent 8-K EX-99.1 exhibits containing "$" (not all are press releases): 35 matched a "U.S. dollars"-type spelling and 9 a Canadian-dollar spelling. This is a spelling count; it doesn't measure currency accuracy or lost coverage. |
| Official XBRL Unit Type Registry | `utr.xml` 1.0, lastUpdated 2024-10-22, sha256 `0236426fa29a1c1b…`, 324 entries: **191 currency** · **8 division templates** (entries with numerator/denominator item types) · **2 generic dimensionless** (`pure`, `Rate`) · **1 shares** · **122 concrete measures** (116 REC + 6 CR) |
| Official ISO 4217 lists | current 178 and historical 137 distinct codes; 307 in union before filtering |
| Symbol traps | registry `MT` = one million US tons, `t` = tonne, `T` = US ton; in time units `M` = month and `MM` = minute, but `MBbls`/`MMBbls` mean thousand/million barrels |
| JEV on units (today's 10-unit list) | value unit 98.1% (627/639), change unit 97.5% (233/239); a coupon ("4.95% Notes due 2028") pulled a $1.0B total to `percent` at confidence 0.83 (JEV.md §6.3, line 425) |
| `XBRL_Definitions.md` | Defines company concepts; doesn't read units and gives no unit list |

## 2. Design in short

1. **Our 10 units first:** usd, m_usd, percent, percent_yoy, percent_sequential, percent_points, basis_points, count, x, unknown.
2. **Other money:** an evidenced official ISO denomination (current or historical; official fund and accounting units included) uses the same pair as dollars (`eur` / `m_eur`). Bullion, testing and no-currency codes are never money. **Never exchanged.**
3. **Physical and time units:** one of the **122 concrete measures** in a saved registry copy, selected by the registry's structured fields. Its `pure`, `Rate`, shares entry and the 8 "X per Y" templates are never choices.
4. **Evidence decides:**
   - the unit is what the quote's words, or the filing's own standard tag on that number, prove;
   - never an ambiguous symbol or its case alone, never a company's unit code name;
   - never a tag that contradicts the visible source;
   - the currency is never inferred from the company, its country or the number's size;
   - an unambiguous currency symbol settles it (€ → EUR);
   - **one deliberate exception (9.1):** a bare "$", "¢" or "cents" defaults to US dollars unless applicable source evidence indicates another currency;
   - conflicting statements, or statements whose scope is unclear → `unknown`; statements clearly about other amounts don't change this amount's currency.
5. **Counts:** a real count of things is `count`, with the thing in the Driver name.
6. **`unknown` is the last resort:** a sound number whose unit stays unproven keeps its value as `unknown`, and is counted. An unclear quantity isn't rescued by `unknown`.
7. **"Per X":** a separately stated "per X" stays in the Driver name (2.16). Named units (`MW`, `Hz`, `psi`) are never split into a formula.
8. **Exact rescaling only:** each stated scale is applied once. Never currency exchange, never conversion between different physical-unit IDs. Exact money rescaling and grouping within one currency follow 3.28 and 3.35. Different physical-unit IDs mean separate series.
9. **Time:** a time unit is an amount, never the fact's period.
10. **Protection:** a fact with a number in an `unknown` unit is protected by its source location from its first save (5.9).

**Who does what (rule 8.1):** JEV judges meaning: which unit and currency the evidence supports for this number, and which amounts a currency statement covers. Code verifies the cited source text and locations, applies the approved unit/default decision and exact rescaling, and enforces the saving rules (5.9). A word scan may never establish that no other currency applies (8.6). The rules don't depend on JEV's menu layout.

## 3. Exact edits

### A. `DRIVER_RULES_Categorized.md`

**E1 · line 7 · change note**

Before:
> **Edited 2026-10-02 (owner-approved):** new 1.22–1.25, 3.53 and 9.11: a switched-off `expectation` type, type boundaries (1.23), cause links between facts (`CAUSED_BY`, `OFFSET_BY`, each with its own quote), meaning-changing words kept in the quote, and no outcome in prediction inputs. Reasons: [fact_types.md](Archive/fact_types_2026-10-02.md) (owner decisions).

After:
> **Edited 2026-10-02 (owner-approved):** new 1.22–1.25, 3.53, 3.54, 5.9 and 9.11; changed 3.28, 3.31, 5.2's example and 9.1: a switched-off `expectation` type, type boundaries (1.23), cause links between facts (`CAUSED_BY`, `OFFSET_BY`, each with its own quote), meaning-changing words kept in the quote, no outcome in prediction inputs, other monetary denominations and official-list units (never exchanged or converted), and protection for `unknown` units. Reasons: [fact_types.md](Archive/fact_types_2026-10-02.md) (owner decisions).

**E2 · line 625 · rule 3.28**

Before:
> - 3.28 Units: `usd` (money per unit: prices, per-share and per-barrel amounts) · `m_usd` (money totals, stored in millions: "$1.5 billion" → 1,500) · `percent` (a percentage level, e.g. a 17.6% margin) · `percent_yoy` (growth vs a year earlier) · `percent_sequential` (growth vs the previous comparable period) · `percent_points` · `basis_points` · `count` (e.g. a share count) · `x` (a multiple, e.g. 2.5x) · `unknown`.

After:
> - 3.28 Units: `usd` (money per unit: prices, per-share and per-barrel amounts) · `m_usd` (money totals, stored in millions: "$1.5 billion" → 1,500) · `percent` (a percentage level, e.g. a 17.6% margin) · `percent_yoy` (growth vs a year earlier) · `percent_sequential` (growth vs the previous comparable period) · `percent_points` · `basis_points` · `count` (e.g. a share count) · `x` (a multiple, e.g. 2.5x) · another monetary denomination: the same pair under its official ISO 4217 code in lowercase (`eur` / `m_eur`; 9.1) · another unit: the ID of a concrete measure in a saved copy of the official XBRL Unit Type Registry, case kept (`bbl`, `MWh`, `sqft`, `t`, `D`; 3.54) · `unknown`.

Why:
- CP's money would otherwise all be `unknown`.
- Physical quantities couldn't form history lines, because 3.35 never groups `unknown`.
- Money keeps today's convention: totals in millions, per-unit amounts plain.

**E3 · insert after line 625 (between 3.28 and 3.29) · new rule 3.54**

> - 3.54 **Choosing a unit.**
>   - Our money, percentage, count and multiple units (3.28) come first. Other physical and time units come from the concrete measure entries of the saved registry, selected by its structured fields; its generic dimensionless entries (`pure`, `Rate`) and its "X per Y" templates are never choices, and shares use `count`. `unknown` is the last resort, never a shortcut around a supported unit.
>   - The unit is the one the evidence proves (3.29): the quote's words, or the filing's own standard tag on that exact number. Never an ambiguous symbol or its case alone (registry `MT` = million US tons, `MM` = minute; a filing's "MT" may mean tonnes, its "MM" million), never a company's own unit code name, and never a tag that contradicts the visible source; a disputed tag settles nothing (8.5). The sole currency-default exception is 9.1.
>   - A real count of things is `count`, with the thing in the Driver name. A sound number whose unit stays unproven keeps its value with `unknown`, counted ("FICO score 700" → 700 `unknown`); an unclear quantity is not rescued by `unknown`.
>   - A separately stated "per X" stays in the name (2.16) with its meaning and scale; a named unit (`MW`, `Hz`, `psi`) is never split into a formula. The remaining unit goes on the fact.
>   - Exact rescaling is allowed (1.13): each stated scale is applied once, never again when the unit already includes it ("1.2 million barrels" and "1,200,000 barrels" → 1,200,000 `bbl`; "1,200 MBbls" stays 1,200 `MBbls`). Never exchange currencies or convert between different physical-unit IDs. Exact money rescaling and grouping within one currency still follow 3.28 and 3.35. Different physical-unit IDs stay in separate series.
>   - A time unit is an amount, never the fact's period (3.36).

Why, bullet by bullet:
- it stops generic ratios and templates sneaking around our percent and "per X" rules;
- it stops the wrong ton, code-name guesses and wrong filing tags (Hexcel, AZEK);
- it keeps sound numbers while never rescuing unclear ones;
- named units stay whole;
- no double scaling; same-unit forms still share one series; money normalization is untouched;
- "45 days" is never read as a period.

Examples:

| Source | Unit | Driver name |
|---|---|---|
| "$70 per barrel" (no other currency stated) | 70 `usd` | `oil_price_per_barrel` |
| "1.2 million barrels a day" | 1,200,000 `bbl` | `oil_production_per_day` |
| "500 MW" | 500 `MW` | `power_capacity` |
| "45 days" | 45 `D` | `days_sales_outstanding` |
| "1,200 stores" | 1,200 `count` | `store_count` |
| "Revenue CAD 1.2 billion" | 1,200 `m_cad` | `revenue` |
| "one million troy ounces of gold" | 1,000,000 `ozt` | `gold_production` |
| "gold inventory valued at USD 70 million" | 70 `m_usd` | `gold_inventory_value` |
| "FICO score 700" | 700 `unknown` | a source-supported FICO-score Driver |

These are illustrations, not a naming dictionary; any real Driver still needs its normal identity checks.

**E4 · line 640 · rule 3.31**

Before:
> - 3.31 Validity: percent units and `x` need a scale of 1; cents on a company-wide total is invalid; money in a currency other than US dollars is `unknown` and counted (9.1).

After:
> - 3.31 Validity: percent units and `x` need a scale of 1; cents, or another currency's minor unit, on a company-wide total is invalid; a currency needs its own evidence (9.1).

Why: the old last clause contradicts E2, and the cents check must also cover pence and other minor units. Minor units on per-unit amounts ("25 cents per share" → 0.25 `usd`) stay allowed. Since v5, a bare "cents" or "¢" follows the same USD convention as "$" (9.1).

**E5 · line 714 · rule 9.1**

Before:
> - 9.1 **US dollars only.** Never convert another currency, infer an exchange rate, or treat an unknown or foreign currency as dollars. A text fact in another currency gets the `unknown` unit and is counted; a tagged-filing fact in another currency is skipped and counted. No such fact enters a dollar series. Full currency support later needs its own design, based on an official currency standard, with values kept as stated, currency-safe identities and reads, complete coverage evidence, and no hand-written currency list or conversion rule.

After:
> - 9.1 **Money is kept in its stated currency.** Use the pair in 3.28 for an evidenced denomination in the saved ISO 4217 current or historical lists, official fund and accounting units included; bullion, testing and no-currency codes are never money (a commodity quantity keeps its evidenced physical unit; a monetary value keeps its currency). Never exchange currencies or infer an exchange rate. Use applicable source evidence to identify the currency, including an unambiguous currency symbol (€ → EUR). Never infer it from the company, its country or the number's size. By project convention, a bare "$", "¢" or "cents" defaults to US dollars (cents as hundredths of a dollar) unless applicable source evidence indicates another currency. If potentially relevant currency statements conflict or it is unclear which amounts they cover, use `unknown` and count it. Statements clearly about other amounts do not change this amount's currency. Otherwise, a currency unresolved after applying these rules is `unknown` and counted. Keep applicable currency statements in the evidence (3.29). Different currencies never share a series (3.35).

Why:

| Old 9.1 condition | Met by |
|---|---|
| Official standard, no hand-written list | the saved ISO 4217 lists, filtered only by their official definitions |
| Values kept as stated, no conversion rule | "never exchange" |
| Currency-safe identities and reads | `level_unit` differs → no merge (5.3); exact-unit series (3.35) |
| Coverage evidence | counts and known cases establish the need; coverage and extraction accuracy stay unproven until the new flow is tested |

The old tagged-filing branch is dropped: tagged-data facts stay switched off (On/Off table), and when they're switched on they follow the same pairs. The "$" default is a stated exception to "the source proves the currency"; see §6.

**E6 · line 715 · warning under 9.1**

Before:
> - ⚠ **Other currencies:** the only unit gap found in testing was euros becoming `unknown` (a safe under-merge); non-dollar data is thinly covered.

After:
> - ⚠ **Other currencies:** support is new and not yet validated in this pipeline. A small share of all tagged facts can still dominate one company's reporting.

**E7 · insert after line 771 (after 5.5) · new rule 5.9**

> - 5.9 **An `unknown` unit never proves two amounts equal.** A fact with a number in an `unknown` unit (value, comparison, change or range bound) carries, from its first save, a tie-breaker naming where each such number sits in the original (file, version, exact number occurrences; never quote wording or reading-window positions). Combining, filling blanks and removing duplicates involving such a fact need the same protected locations as well as the usual scope and value checks; a missing or different location never matches. If combining would add or change that protection on a saved fact, the incoming fact is kept separately; a saved fact is never re-keyed. Re-running unchanged input changes nothing (5.4); conflicting values still follow 5.3. This is the exception to 5.5, and reads must not collapse facts this rule keeps apart.

Why:
- "500 `unknown`" (barrels) and "500 `unknown`" (gas) from two places would otherwise merge into one fact, and one would be lost silently. Rule 1.12 says merging different meanings is permanent damage.
- An `unknown` growth basis is unknown meaning: 3% vs last year and 3% vs last quarter are different facts. So **v1's percentage carve-out is withdrawn**.
- The blank-filling path is covered too. Example: a saved "revenue 5,200 `m_usd`" can't silently absorb a later "+3 `unknown`" change without protection.
- Protection from the first save means no re-keying (3.1) and no dependence on arrival order. It applies to numeric facts only: numberless facts have no unit (3.30).

**E8 · line 431 · rule 3.2 (pointer)**

Before: `· a tie-breaker used only for true conflicts (5.3).`
After: `· a tie-breaker used only for true conflicts (5.3) and for facts protected by 5.9.`

**E9 · line 754 · rule 5.2 (pointer + corrected example)**

Before: `…the whole group is held; the input order never decides. *Why:* repeats of the same fact (a press release and the filing's management discussion both saying "Q1 +3%") become one fact.`

After: `…the whole group is held; the input order never decides. Facts containing numbers in an `unknown` unit follow 5.9. *Why:* two passages within the same source event, both stating "Q1 revenue rose 3% year over year" for the same Driver and scope, become one fact.`

Why the example changes:
- The old one mixed a press release (8-K) with management discussion (10-Q). Rule 7.5 stores different source events as separate facts.
- "Q1 +3%" has no basis, so it's `unknown` (3.33) and now protected.
- The new example has a proven basis and a single event.

**E10 · line 757 · rule 5.3 (pointer)**

Before: `Two facts are **the same** when all ten match, blanks included;`
After: `Two facts are **the same** when all ten match, blanks included (facts containing numbers in an `unknown` unit: 5.9);`

**E11 · line 771 · rule 5.5 (pointer)**

Before: `…and every pair of facts must disagree on at least one filled value.`
After: `…and every pair of facts must disagree on at least one filled value (exception: 5.9).`

**E12 · line 850 · rule 7.4 (pointer)**

Before: `…or by the tidied guidance words for qualitative facts; never by the quote.`
After: `…or by the tidied guidance words for qualitative facts; never by the quote; facts protected by 5.9 are never collapsed.`

**E13 · line 1186 · Start-here On/Off table**

Before (On): `fiscal.ai as the only channel · US dollars · company-confirmed guidance`
After (On): `fiscal.ai as the only channel · US dollars and other currencies (kept as stated, never exchanged) · company-confirmed guidance`

Before (Off, start): `news and other sources · other currencies · third-party guidance ·`
After (Off, start): `news and other sources · third-party guidance · outside forecasts (`expectation`, 9.11) ·`

Why: currencies move to On. This also fixes today's earlier gap: the switched-off `expectation` type (9.11) was missing from Off.

**E16 · line 626 · rule 3.29 (pointer)**

Before: `- 3.29 **The unit and scale of every number must be backed by evidence.**`
After: `- 3.29 **The unit and scale of every number must be backed by evidence** (currency evidence and the sole bare-dollar default: 9.1).`

Why: someone reading 3.29 alone can see where the "$" convention lives.

**Result:** 227 → **229 rules**. Facts keep 25 fields; there are no new fields or relationships.

### B. `fact_types.md` (archived 2026-10-02 as `Archive/fact_types_2026-10-02.md`)

**E14 · line 9 · decisions table, row 3**

Before:
> | 3 | Units and currencies | ⏳ Owner to decide | — |

After:
> | 3 | Units and currencies | ✅ Our own units first; other monetary denominations under their official ISO code (`eur`/`m_eur`), never exchanged; physical and time units from the registry's concrete measures; real counts = `count`; sound numbers with an unproven unit = `unknown`, counted; evidence decides (an unambiguous currency symbol settles it; a contradicting tag never wins; by project convention a bare "$", "¢" or "cents" defaults to US dollars unless the source indicates another currency; unclear scope → `unknown`); exact rescaling once, no currency exchange or physical-unit conversion; "per X" stays in the name; numbers in an `unknown` unit are protected by their source location | 3.28, 3.31, 3.54, 5.9, 9.1 |

### C. `rough_design.md` (build note, not a rule)

**E15 · line 22 · step 4 Judge**

Before: `JEV picks fact type, state, unit, span, baseline, horizon, slice kind;`
After: `JEV picks fact type, state, unit (a small first choice: our 10 units + physical/time + other-money total + other-money per unit; then the relevant official list, split into branches if over 255 options; `unknown` in every list; untested), span, baseline, horizon, slice kind;`

## 4. Consistency check

| Rule | Why it still holds |
|---|---|
| 1.12, 8.5 (keep separate; fail closed) | 5.9 and "no conversions" keep separate; a disputed tag settles nothing |
| 1.13 (exact rescaling; no vendor ratios) | One scale application, no unit or currency conversion |
| 1.14 / 1.17 (own source only) | Currency and unit come from the fact's own source; never the company's history |
| 1.24 (the quote keeps meaning words) | Unchanged |
| 2.16 ("per X" in the name) | Kept; named units stay whole; "X per Y" templates excluded |
| 3.1 (identity never changes) | 5.9's tie-breaker is set at first save; no re-keying |
| 3.29 (evidence; never from a name; widen for outside markers) | 3.54 and 9.1 point to it, and 3.29 points to 9.1 (E16). A stated currency outside the quote is widened in, as 3.29 already requires. The "$" default is the one stated exception. |
| 3.30 (no number → no unit) | 5.9 is numeric-only |
| 3.33 (growth with no basis = `unknown`) | Now protected by 5.9; 5.2's example uses a proven basis |
| 3.35 (exact-unit series; money on one scale within a currency) | Already currency-aware |
| 3.36 (period) | A time unit is never the period |
| 5.2–5.5 | Pointers name the exception; 5.2's example fixed |
| 6.20 (nothing fixes after saving) | A later read that resolves a unit adds a new fact; the old one stays |
| 7.1, 7.4, 7.5 | Exact series match; protected facts not collapsed; separate events stay separate |
| 8.1 (AI meaning; code checks and arithmetic) | The who-does-what split |
| 8.14 / 8.15 (outcomes; hold needs a trigger) | No "hold" used |
| Tagged-data route (Off) | Stays off |

## 5. Accepted trade-offs

- Different unit IDs ("1,200 MBbls" vs "1.2 million barrels") form separate series. Ordinary scale words and formatting don't split a series.
- A later read that resolves a unit becomes a new fact; the earlier `unknown` one stays (5.5, 6.20).
- 5.9 keeps protected facts apart. That preserves evidence but **may duplicate a real statement**, including a known value repeated next to an `unknown` change.
- A bare "$" in a source that states another currency needs that statement in the evidence; otherwise the amount isn't recorded or is `unknown`.
- **By convention, an unlabelled non-USD amount in a source that never states its currency can become US dollars.** The default preserves otherwise unresolved bare-dollar amounts as usable USD amounts, accepting that an unlabelled non-USD amount can be wrong. Its coverage benefit and error rate haven't been measured.

## 6. The "$" sentence (settled)

**History:**
1. Codex first proposed that a bare "$" never identifies a currency.
2. Claude objected (citing a lexical sample, now labelled unverified in §1).
3. The owner asked whether the rule should cover all currencies.
4. Codex accepted a USD default as a **deliberate project convention**, stated as the sole currency-default exception.
5. Codex's final review made the wording consistent: no later clause cancels the default, and no word scan stands in for meaning (8.6).

**The three cases:**

| Situation | Currency |
|---|---|
| No currency statement, bare "$" | USD, by convention |
| A CAD statement that clearly covers the amount | CAD |
| Statements that could apply but whose scope can't be resolved | `unknown`, counted |

An unrelated euro amount elsewhere isn't a reason to reject a clear dollar amount.

**Why only "$" gets a default:** our data has "¥" meaning yen (Aflac) and yuan (ACM Research), so no default is safe there.

**Building it:** reuse the existing source reading and its currency context (8.10). AI judges currency meaning and which amounts a statement covers; code verifies the cited text and locations. **No separate word scanner.**

## 7. Follow-ups after approval (not part of this change)

1. **Saved copies at build:**
   - the full registry (`utr.xml` 1.0, 2024-10-22);
   - the 122-measure menu derived from its structured fields;
   - ISO 4217 lists one and three;
   - full hashes kept, each list entry given one recorded disposition, reviewed once (P24).
2. **JEV unit-selection test:** a separate Core/JEV test with its own approval and authorised model calls. FinalPlan Phase 6 is read first, as CLAUDE.md requires, but this isn't a Fiscal Phase 6 run. It covers the full routing flow, including a wrong first route and menu-order permutations, on fresh source-grounded cases. JEV's confidence never grants a write. No accuracy claim before it.
3. **Tests:** Codex's required list (full_plan_review/REVIEW.txt §7), plus the three "$" cases in §6 run through the full reading flow:
   - no statement → `usd`;
   - a clear CAD statement → `cad`, with the statement in evidence;
   - a euro segment elsewhere → only those amounts in `eur`;
   - an unresolvable scope → `unknown`.
   - Neither a code scan nor model confidence guarantees the default is correct.
4. **Decided (owner, v5):** the convention also covers a bare "¢" or "cents"; a stated other currency still wins.
5. **Notion:** update the Workflow section pages' rule ranges for all of today's new and changed rules in one pass.
6. **Commit and push** (owner pre-approved, whole DriversFinal folder).

## 8. Review trail

| Point | Origin | Status |
|---|---|---|
| Official registry, saved copy, case kept | Claude + Codex | ✅ |
| Not exhaustive; company units aren't all counts | Codex | ✅ |
| Currencies now (CP evidence) | Codex | ✅ |
| Scale once; exact rescaling allowed; no conversion between IDs | Codex + Claude | ✅ v2 wording |
| 5.9 protection; first-save tie-breaker; same location ≠ override | Codex | ✅ |
| 5.9 also covers blank-filling, comparisons and range bounds | Codex (review 3) | ✅ v2 |
| v1 percentage carve-out | Claude | ❌ withdrawn (unknown basis = unknown meaning) |
| 5.2 example fixed (same event, proven basis) | Codex | ✅ v2 |
| Registry filter by structured fields; 122 + `unknown` | Codex | ✅ v2 |
| Tag never overrides contradicting text (Hexcel, AZEK) | Codex | ✅ v2 |
| Fund and accounting units allowed; bullion, testing and no-currency excluded; gold by what is measured | Codex | ✅ v2 (replaces Claude's v1 exclusion) |
| FICO keeps 700 with `unknown` | Codex | ✅ v2 |
| Evidence wording (links; 42 non-USD codes; CP 35.6%; physical count qualified) | Codex | ✅ v2 |
| JEV test ≠ Fiscal Phase 6 | Codex | ✅ v2 |
| "Harmless and rare" removed | Codex | ✅ v2 |
| Bare "$" wording: one-currency symbol settles it, shared symbols need context, "$" defaults to USD by stated convention | Claude + owner + Codex | ✅ settled (§6) |
| 3.29 pointer to 9.1 (E16) | Claude; Codex wording | ✅ v4 |
| USD default made consistent (no cancelling clause; E3 names 9.1 as the sole exception) | Codex (v3 review) | ✅ v4 |
| No code word-scan gate; AI judges currency context (8.1, 8.6, 8.10) | Codex (v3 review) | ✅ v4 (Claude's guard withdrawn) |
| Money rescaling within a currency kept explicit | Codex (v3 review) | ✅ v4 |
| Gold keeps its stated physical unit | Codex (v3 review) | ✅ v4 |
| 91% claim labelled as an unverified spelling sample | Codex (v3 review) | ✅ v4 |
| Bare "¢"/"cents" follows the "$" convention | Owner + Claude | ✅ v5 |
