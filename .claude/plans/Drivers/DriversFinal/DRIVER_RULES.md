# Driver rules

Everything already decided about Drivers and their facts, in plain words: the starting point for your new design. **Frozen as version 1.1 on 2026-09-26.** It reopens only for a rule proven wrong or a decision proven missing; add those to the parking list at the end of Part C.

**How to use this file**
- Read **Start here** (about 15 minutes). It is the only must-read.
- Then design one topic at a time, opening only that topic (§1–§10); where a rule touches another topic, it points there by number.
- One small fold in §1 holds the exact locked wording of the four fact types (the meaning authority); everything else in §1–§10 is open to read.
- To print everything, expand the four folds first (the exact wording in §1, and Parts A, B and C).
- *Why* lines give reasons; ⚠ lines are lessons from the old work. Their numbers are evidence from that work, not current checks. Where each rule comes from is in folded Part C.

**Contents:** [Start here](#start-here) · [1 What you are recording](#1-what-you-are-recording) · [2 Drivers: names, creation and identity](#2-drivers-names-creation-and-identity) · [3 What is on each fact](#3-what-is-on-each-fact) · [4 Forecasts and surprises](#4-forecasts-and-surprises) · [5 When facts repeat, conflict or change](#5-when-facts-repeat-conflict-or-change) · [6 Links, and fixing wrong ones](#6-links-and-fixing-wrong-ones) · [7 Reading facts back](#7-reading-facts-back) · [8 Rules for any build](#8-rules-for-any-build) · [9 Off for now](#9-off-for-now-first-release-limits) · [10 Still open](#10-still-open) · [Word list](#word-list) · then, folded: A switched-off features · B rejected ideas · C sources and proof

## Start here

**The purpose:** give every cause that can matter to a company or market one reusable name (a **Driver**), and store every real, quoted occurrence of it (a **fact**), so the system can run this loop: extract facts → explain price moves → learn which Drivers matter → predict → trade.

**The core, in nine lines**
1. **Driver and fact.** A Driver is one reusable cause or standing thing (`oil_price`, `revenue`, `revenue_guidance`). A fact is one occurrence of a Driver in one **source event** (one filing, call transcript or news story), always with the exact quote.
2. **Four fact types**, one per Driver, fixed forever: `metric` (a standing level you can read again) · `guidance` (the company's own forecast) · `surprise` (a result compared with the analysts' consensus or the company's own earlier forecast, or a forecast compared with the consensus) · `action_event` (a one-time happening). Exact locked wording: 1.5.
3. **Name versus fact.** Name the reusable thing or cause precisely; keep a stated "per X" term, a benchmark and a final `_guidance` or `_surprise` (the name ending that marks those two types). The company's own measured parts (segments, products, regions…) go in **slices**; measurement versions (adjusted, diluted…) go in **measurement tags**; the value, date and state go on the fact.
4. **Evidence.** Store only what the source states, with its exact quote; numbers stay exact and are never invented. The one fact the system writes on its own: spreading a clear withdrawal to the forecasts it covers (4.18).
5. **Identity.** A fact is its source event + its Driver + its scope (period, slices, tags and, for a surprise, the comparison kind). It never changes once written.
6. **The one law.** Merging different meanings does permanent damage; keeping one meaning split can be repaired. When unsure, keep separate.
7. **Time.** A view of the past sees only what was public then.
8. **History.** Nothing is deleted: an amended filing adds new facts, a wrong link is switched off (reversibly), a wrong fact is flagged.
9. **Who decides.** AI judges meaning; fixed rules check structure; whatever proposes an answer never approves it.

**One worked example** (a September test case: Best Buy's earnings call, fiscal Q4 2026)

> International revenue of $1.2 billion increased 0.5% versus last year.

| Piece | Stored as | Why |
|---|---|---|
| Driver | `revenue`, type `metric` | a standing level you can read again |
| Slice | `segment:international` | the company's own part goes in a slice, not in the name |
| State | `increased` | the source states a direction |
| Value | 1,200 `m_usd` | money totals are stored in millions |
| Change | +0.5 `percent_yoy` | growth against a year earlier |
| Compared with | `prior_year`, with no number | last year's amount wasn't stated, so it stays empty |
| Period | Best Buy's fiscal Q4 2026, with its real dates | a real calendar window, not a label |
| Evidence | the exact quote, from the earnings-call transcript (the source event) | every fact needs its quote |

**What's on in the first release** (details: §9)

| On | Off for now |
|---|---|
| fiscal.ai as the only channel · US dollars · company-confirmed guidance | news and other sources · other currencies · third-party guidance · comparing slices across companies · 8-K item categories · a financial-classification field · price-move verdicts · facts from tagged filing data · text values on metrics and conditions on actions · instant linking of new names |

**Your design map** (the topics below, in order; "yours to decide" is where your design freedom is)

| § | Question | Already decided, in short | Yours to decide |
|---|---|---|---|
| 1 | What am I recording? | Drivers and facts; four fixed types; the evidence and history laws | — |
| 2 | What goes in a name, and when is a Driver new? | Name the reusable cause; a Driver is born with its first real fact (one exception: a hidden placeholder base, 2.26); sameness is judged by object, scope and mechanism, never by counts, and approved by an independent check; unsure → keep separate | how candidate Drivers are found and shown; which AI does the checking |
| 3 | What is on each fact? | 24 fields in six groups; allowed states per type; slices, tags, units, signs, periods and number shapes | how facts are stored |
| 4 | How do forecasts and surprises work? | A stated movement is stored, otherwise it is worked out when read; a surprise is written only with its accepted home fact; a withdrawal spreads only when its scope is exact | — |
| 5 | What happens when facts repeat, conflict or change? | Combine only when unambiguous; keep conflicting values; identity never changes; a stored value changes only through repair; a blank never erases | how batches and repairs run |
| 6 | How are facts linked, and wrong links fixed? | The exact official line item or nothing; renames only when declared; wrong links are paused, independently confirmed and switched off reversibly | how detection and recovery are built |
| 7 | How are facts read back? | Exact series match; a same-day source rank; point-in-time views; reconciled views only on request | query and storage design |
| 8 | What must every build respect? | AI judges meaning and code checks structure; fail closed; zero known-wrong; five outcomes; retry only on an exact trigger | components, models, schedules |
| 9 | What is off for now? | The list above, each with its reopen condition | when to reopen one |
| 10 | What is still open? | Four questions; only one (price moves) waits on a switched-off feature, and none blocks designing basic facts | the answers |

## 1. What you are recording

*Answers: what a Driver and a fact are, the four fact types, and the laws every fact follows.*

### Purpose

- 1.1 The same name is reused for the same cause across companies and over time. *Why:* then scattered mentions line up into one clean history per cause, and that history is what gets acted on.
- 1.2 A Driver (the name) is separate from its facts. Each fact is added under an existing or new Driver and tagged with its source and event. A Driver can have facts from many events; one event can have facts for many Drivers.
- 1.3 The loop it serves: extract facts → explain price moves → learn which Drivers matter → predict → trade. *Why not just list events:* services like RavenPack only list that an event happened; this system grades each cause against what the stock actually did.
- 1.4 *Original intent (May 2026):* Drivers were to come from earnings-learner reports (8-Ks, transcripts), from news (mostly macro, sector or industry) and from fiscal.ai data (10-K, 10-Q, presentations). The earnings predictor only *reads* Driver tags, to find relevant past reports and to know what moves prices; it never creates Drivers. (The first release starts with fiscal.ai data only; see 9.5.)

### How the pieces connect

```text
company ◄── source event ◄── fact (DriverUpdate) ──► Driver ──SAME_AS──────► Driver
            (filing,          │                        ├──BASE_METRIC──► Driver
             transcript,      ├──► period              └──CONTINUES_AS─► Driver
             news story)      ├──► XBRL line item or breakdown member (optional)
                              └──◄ verdict (later; folded Part A2)
```
`SAME_AS` = same meaning (reversible) · `BASE_METRIC` = a guidance or surprise Driver's base metric · `CONTINUES_AS` = a company's declared rename (dated).

- **In:** the project's graph database already holds SEC filings (8-K, 10-Q, 10-K, with every section and exhibit), the XBRL data tagged in 10-Q and 10-K filings, earnings-call transcripts, news stories, companies with their official industry and sector, and daily stock prices and returns. The old Guidance data is evidence only (8.11). The first release uses one channel, fiscal.ai, which points to figures inside SEC filings (9.5).
- **Flow:** a source event → the AI reader proposes facts and Driver names → the core decides: reuse a Driver, create one with its first fact, hold, skip or reject → the fact is written → metric facts get links to official filing data (§6) → reads, as of any date (§7).
- **Out:** the earnings predictor reads Driver facts (1.4). Verdicts (folded Part A2) tie facts to price moves, so the system can learn which Drivers matter. Users of the old Guidance data move to Driver facts.
- ⚠ **Database quirks:** numbers stored as text, the literal text 'null' as a date, comma-formatted values, about 12,900 facts with no context link.

### The four fact types

| Type | Means | Examples from the sources |
|---|---|---|
| `metric` | A standing level or condition you can read again later: a number, or a state like sentiment or a policy in force | `revenue`, `oil_price_per_barrel`, `litigation` |
| `guidance` | The company's own forecast, target or outlook | `revenue_guidance`, `bookings_guidance` |
| `surprise` | A company result compared with the consensus or the company's own earlier forecast; or a company forecast compared with the consensus | `earnings_per_share_surprise` |
| `action_event` | A one-time happening: a decision, transaction, incident, approval or one-off charge | `asset_impairment`, `buyback`, `dividend` |

- 1.5 **The persistence test and the locked definitions.** The persistence test decides metric versus action: between two events, is there a standing level you could read again? Yes → `metric`; no → `action_event`. A `_guidance` or `_surprise` name overrides it. The plain version of the definitions is the table above and 1.6–1.8; the exact locked wording is just below (1.9; `fact_scope` is the fact's scope, 3.2).

<details><summary>The exact locked wording (the meaning authority)</summary>

> **metric** = any standing variable readable again over time (number/cost/price/rate/count/ratio OR a qualitative condition: weather, sentiment, policy-in-force, labor, brand) — NOT only a number · **guidance** = the company's own forward outlook/target/forecast · **surprise** = a company value — DELIVERED (an actual) OR PROMISED (a company guide) — vs a CROSS-PARTY EXPECTATION (analyst consensus/Street, or for an actual the company's own prior guide), NOT vs a prior-period actual (that's a metric change) and NOT a new-guide-vs-own-prior-guide revision (that's a guidance movement); the 3 types (`actual_vs_consensus` / `actual_vs_guidance` / `guidance_vs_consensus`) live in the `surprise=` fact_scope slot (OD-21) · **action_event** = a discrete thing that happened (decision, transaction, incident, approval, one-off charge).

> Persistence test: between two events, is there a standing level/severity you could re-read? Yes → metric · No → action_event. A `_surprise`/`_guidance` framing OVERRIDES. Outlook verbs (expect/anticipate/target/plan to) → guidance, never a metric state. Dual framing allowed (`dividend` = action_event vs `dividend_per_share` = metric). Bare-root defaults: litigation/convertible_notes/dividend_policy/restructuring_costs → metric; corporate_restructuring/asset_impairment → action_event.

</details>

- 1.6 In plain words: forecast words ("expect", "anticipate", "target", "plan to") make a fact guidance, never a metric state.
- 1.7 Both framings of one topic can exist as different Drivers: `dividend` (action_event) and `dividend_per_share` (metric).
- 1.8 Fixed defaults for bare names: `litigation`, `convertible_notes`, `dividend_policy`, `restructuring_costs` → metric; `corporate_restructuring`, `asset_impairment` → action_event.
- 1.9 The quoted text is the meaning authority. A restatement (like the plain version above) may change only labels and typography, never meaning, and adds no clause or example. *Why:* an added clause was tested and made results worse.
- 1.10 *Why these four:* they were checked against all 1,282 names from the catalog work, and none fit no type.

### Evidence and history laws

- 1.11 Every fact needs a source quote. A mention without a fact is dropped.
- 1.12 **The one law:** merging different meanings causes permanent damage; keeping the same meaning separate can be repaired. **When unsure, keep separate.** *Why:* a merged forecast and result can never be untangled later (bad trades forever), while a missing link only costs a missed comparison that can be fixed.
- 1.13 Store only what the source states. Exact rescaling (e.g. "$2.1 billion" to a stored number) is allowed. Logic may add labels, states, IDs or facts, but never an invented number. Vendor-calculated ratios, percentage changes and "common-size" rows (figures restated as a percentage of a total) are never stored as facts (in one vendor's data they were about 62% of rows; that's evidence, not a threshold).
- 1.14 **No look-ahead.** A historical run may see only what was public before its cutoff.
  - New facts, and the lists shown while making them, are cut at the source's public time.
  - The list of names may be built offline from the full history (a name carries no value), but a name is shown only from the public time of its first evidence.
  - History reads use "strictly before the as-of date"; live use sees everything current.
  - Never show the realized stock return to whatever produces a fact or a verdict.
  - Never assume which kind of source arrives first; process each at its real public time.
- 1.15 Never delete or re-key Drivers or facts to make history look cleaner. True duplicates are joined with a reversible synonym link.
- 1.16 Missing links are safer than wrong links.
- 1.17 A fact's evidence comes only from its own source.
  - An earlier source never uses a later one as evidence: a later 10-Q may help *find* things during backfill, but the older source must prove its own quote, value, unit, label, period, slice, measurement and meaning; nothing is borrowed from the later source.
  - Every stored number must appear, as printed, in its own quote.
  - An 8-K source event is the whole filing (all sections and exhibits, without duplicates), never just the press-release exhibit.
  - For a table in an 8-K, only the original table counts as evidence; a flattened text, PDF or converted copy doesn't, and unsupported formats fail closed.

### Families and synonyms

- 1.18 Different flavors of one topic are separate Drivers linked as a family.
  - Every guidance or surprise Driver has exactly one base metric; action Drivers have none.
  - The base must exist; it may start as the hidden placeholder.
  - A family comes only from a final suffix, never guessed from name prefixes.
  - *Why separate:* a result and a forecast are different signals that can move the stock opposite ways on the same day ("beat this quarter, cut next year's guidance" → down); merged, you'd lose which one moved it.
  - *Why linked:* to ask "did revenue beat its own forecast?"
- 1.19 Synonym link = same meaning, reversible. Family link = related flavors. Never use one in place of the other. In a synonym group, one name is the current representative (the "head"): established beats young, then the earliest, then alphabetical order. Example chain: `net_sales_guidance` → family → `net_sales` → synonym → `revenue`. A missing synonym link only costs a missed comparison, never a wrong merged number.

### Which companies

- 1.20 Covered companies are those the official company → industry → sector data marks eligible at one recorded moment. The resulting count is an outcome, never a target (no fixed 786 or 796).
- 1.21 A newly eligible company may get facts right away and joins the catalog at the next reviewed refresh. A company that stops being eligible adds nothing new to the catalog, but all its facts and history stay intact and readable. Nothing is deleted, renamed, merged or rewritten automatically. An unclear status keeps history and blocks new catalog inclusion; it never creates a company-specific exception or a second lifecycle list.

## 2. Drivers: names, creation and identity

*Answers: what goes in a Driver's name, when a new Driver is created, and when two names are the same Driver.*

### What a Driver is

- 2.1 A Driver = name + permanent `fact_type` + synonym links + family link + the evidence it was born from (raw quotes, never an AI-written summary). Think of an index card: one card per meaning, and each fact is an entry on that card. The birth evidence never changes as later facts attach, and every identity check compares against it; only a birth quote itself confirmed wrong is replaced, from the next clean facts. *Why:* otherwise a Driver's meaning could drift, one small approval at a time.
- 2.2 Each Driver also has a standing, shown whenever it's offered for reuse:
  - **young:** the default; not yet proven;
  - **established:** passed a one-time independent review showing that all its evidence describes one single mechanism (for the first catalog, also the pre-launch checks); never earned by counts;
  - **frozen:** was established, but its evidence no longer describes one mechanism; it can't receive instant links (9.9) and is left out of cross-company signals while its existing links are re-checked one by one;
  - **quarantined:** switched off after a confirmed mistake, such as one name found to carry two meanings: new facts are held instead of attached (2.47), and earlier facts stay as flagged history (6.20, 6.23).

### Naming

- 2.3 The name holds the cause only; a stated per-unit denominator, a benchmark and a final family suffix may join it (2.15). State, direction, size, time, company, unit and quote live elsewhere. *Why:* a cause-only name is what lets the same cause recur and be tracked; anything extra breaks reuse.
- 2.4 One stored name has one meaning. Spelling, word-order, acronym and plural variants reuse the standard name. Reusing a name whose words are only reordered needs the independent check (8.2) and exactly the same words (none added, dropped, shortened or swapped); no alias is kept for the old order. No alias lists. A true duplicate found later may get a reversible synonym link. *Why:* an alias list can't hold each variant's own evidence, and duplicate names split the history.
- 2.5 The vocabulary is open and comes from the sources. *Why:* a closed vocabulary was tested and rejected; it turned away about 82% of useful names.
- 2.6 Use all the specificity the evidence supports. Never invent a broader class just to force reuse. *Why:* an earlier version coined generic names, collapsed three different demand stories into one, and failed a fresh test.
- 2.7 Format: lowercase plain letters (a–z), digits and underscores; starts with a letter; at least 2 characters; no trailing or doubled underscore. *Why:* one fixed form means the same cause always gives exactly the same text, so names group and compare reliably.
- 2.8 Word order: thing or actor (a commodity, a customer group, a policy body like the Fed or OPEC), then detail, then metric. Use singular count nouns, except (a) a standard plural term the concept is normally reported under (`earnings`, `bookings`, `sales`, `savings`, `futures`, `receivables`) and (b) a plural whose singular means something else (`product_returns`). The examples are not a list; this two-part test decides. A singular/plural pair naming the same concept is one Driver; if the meaning may differ (`booking` vs `bookings`), keep them separate. Never change a locked phrase (2.10).
- 2.9 Use the familiar form only when the source doesn't state a meaningful sibling or benchmark. A stated specific instrument wins over the familiar broad name. *Why:* a name everyone already uses gets the most reuse.
- 2.10 Keep standard financial phrases whole (e.g. `ebitda`, `fcf`, `fed_rate`, `cogs`, `rpo`, `gross_margin`, `free_cash_flow`, `same_store_sales`); split up, they become names nobody reuses. A loss, deficit or negative margin is a negative value of the signed metric (`net_income`, `operating_margin`, `earnings_per_share`…), never a separate "loss" Driver. In general, name the signed measure, never one sign of it: an income-tax *benefit* is a negative value of the income-tax expense Driver (3.34).
- 2.11 One name carries one cause. Split independent causes. Keep names short and noun-like.
- 2.12 The company's own measured segment, product, geography, customer group, sales channel or owned stake goes in the slice, not the name. *Why:* facts are already grouped by slice and period when read; a company part in the name would fragment the history.
- 2.13 **The role test.** First ignore generic direction and effect words. Then sort what's left:
  - the company's own measured part → slice;
  - an outside actor, object, platform, policy, event or product that causes the outcome → stays in the name;
  - an unclear role, or a vague leftover → also stays in the name.

  A customer is a slice only when it is the company's own customer population. There is no vendor slice. *Why:* treating an unclear outside cause as a slice can merge two different causes; keeping it in the name may over-split, which can be repaired.
- 2.14 **Portions.** Population words like `current`, `funded` or `fee_earning` stay in the name and make a different Driver from the bare one.
  - Only a fact about the true whole company has no slice.
  - Network-wide, systemwide, GMV (gross merchandise value) and other curated subsets are *not* the whole company, so they keep their qualifying word in the Driver name.
  - Leftovers the source states ("Other", "Corporate") may be company-specific slices.
  - Accounting eliminations and consolidation artifacts (bookkeeping lines that exist only to add the parts up to the company total) are neither names nor slices: drop and log the artifact and keep the real metric fact.
  - If a fact only *mentions* such an artifact as the reason for a change, it is written on the real metric it affects; if the fact is *about* the artifact itself, it is held and logged. (Eliminations as slices: 3.21.)
  - *Why:* read as the whole company, "system-wide" figures would put a different population into the company's own series.
- 2.15 Only these may appear in a name: the cause, a stated per-unit denominator ("per X"), a benchmark (e.g. Brent in `brent_oil_price`), and a final family suffix (`_guidance`, `_surprise`). *Why:* a denominator or benchmark changes the actual number, so leaving it out would merge different numbers (`oil_price_per_barrel` vs `oil_price_per_tonne`).
- 2.16 **Per-unit names ("per X"):**

| Situation | Rule |
|---|---|
| The source states a business or physical "per X" | Keep it in the name (`oil_price_per_barrel`); never invent one |
| Two names with different denominators | Different Drivers, never synonyms |
| The value's unit | The plain unit, without the "per" part (e.g. `usd`, with "per barrel" in the name) |
| An acronym whose expansion is certain | Spell it out: `EPS` → `earnings_per_share`, `DPS` → `dividend_per_share` (examples, not a list) |
| The expansion is uncertain | Skip the fact; never guess or extend by analogy |
| The name and the stated denominator disagree | Hold the fact |
| The quote | Keeps the acronym as written |
| Scope | Per-unit names only; familiar names (2.9) and standard phrases (2.10) are untouched |

- 2.17 Measurement versions (adjusted, diluted, constant currency…) go in measurement tags, never the name. A missing tag never means GAAP. A measurement tag re-expresses the *same* quantity through a different lens; a word that changes *which portion* is counted belongs in the name instead (2.14). *Why:* one base metric can then carry its GAAP and adjusted readings as separate, comparable facts.
- 2.18 **Never in a name:**
  - state words, direction, motion or change nouns;
  - the reporting company, or any company or person mentioned only in passing (an analyst, executive, law firm or counterparty);
  - period words; numbers, sizes or bare units;
  - source-type labels, vendor metadata, XBRL prefixes;
  - metaphor, sentiment or effect words; bare category words; vague descriptors; glue words.

  **Exceptions:** an outside company, platform, institution or person whose own action or state *is* the cause (`fed_rate`, `aws_outage`, `tiktok_ban`); stable nouns and metric phrases ending in -ing or -ed (`pricing`, `bookings`, `operating_margin`); an effect word only inside a specific, reusable market force (`glp1_pressure`; bare "pressure" stays banned).
- 2.19 A final `_guidance` or `_surprise` stays in the name and fixes the permanent fact type. One surprise Driver holds all three kinds of surprise comparison (4.2). Guidance and surprise Drivers link to their base metric with the family link, never the synonym link. Only a final suffix counts, and it is stripped only once. *Why:* a forecast or a surprise is a genuinely different fact, so it gets its own Driver, linked to the base rather than merged.
- 2.20 **Create a new Driver only when all of these hold:**
  - no existing Driver has the same meaning;
  - every naming rule passes;
  - its nouns come from the source or the catalog;
  - at least one piece of causal evidence exists;
  - it is reusable: a kind, not one instance (`government_shutdown` is fine even if seen once; `q1_2026_shutdown_effect` is not);
  - its meaning is unambiguous.

  Vague evidence is skipped. *Why:* this keeps junk, one-off and made-up names out.
- 2.21 Naming rules change only through a general principle, never by adding a sector example as policy. *Why:* examples overfit; named cases pass while unnamed ones break on data never seen.
- ⚠ **A lawful-looking name can point at the wrong thing:** `restaurant_closures` (the cause) instead of `restaurant_closure_impairment` (the charge the company actually recorded).

### Names ending in `_guidance` or `_surprise`

- 2.22 Strip exactly one final suffix (`bookings_guidance` → `bookings`). A stacked suffix (`revenue_guidance_surprise`) is invalid. A suffix in the middle (`fda_guidance_issuance`) doesn't count.
- 2.23 Admit the name only if the rest is a standing metric or condition whose level, state or severity can be read again over time, **and** the source is forecasting it (`_guidance`) or comparing it with expectations (`_surprise`). Any doubt → don't admit. This admits `bookings_guidance` and rejects names like `fda_guidance` or `buyback_guidance`, unless the rest truly is the guided metric.
- 2.24 If it's not admitted, rename it only to a specific, source-grounded name without the suffix (never a broad bucket like `regulatory_guidance_update`), through the normal duplicate checks. If no safe rename exists, hold it.
- 2.25 An admission decision, once made, is reused; a later refresh never re-decides it.
- 2.26 **Hidden placeholder base.** If a guidance or surprise Driver is admitted before its base metric exists, a hidden placeholder base is created (e.g. `revenue` when `revenue_guidance` comes first).
  - It must be a valid standalone name, never suffixed, and must not clash with any existing, variant, skipped or held name.
  - It takes no facts, can't be claimed, and is never offered for reuse.
  - It becomes a real Driver only when a later metric fact uses exactly the same name, never an approximate match.
  - A `net_sales` fact does not make a `revenue` placeholder real; whether they mean the same is a separate synonym question.
  - It is the only Driver allowed to exist without facts.

### Bare names: a metric must prove itself

- 2.27 Fixed rules come first and can't be overruled: the suffix rules (2.22–2.24) and the fixed defaults in 1.8.
- 2.28 A bare name judged to be `action_event` is typed action, the safe direction.
- 2.29 A bare name judged to be guidance or surprise is a naming mistake, never a type. It is renamed with the suffix (2.22–2.24), or the item is skipped.
- 2.30 **A bare name judged to be a metric is typed metric only if the evidence shows the name itself is a standing level, value, condition or severity that can be read again over time, and not mainly a one-time action, decision, event or plan, with the exact evidence phrase quoted.**
  - Otherwise it is typed `action_event` with a visible, counted warning; the warning never blocks and never queues.
  - In live use, thin or unclear evidence is never defaulted to action: the item is skipped, unless a rule names an exact trigger that could change the result (8.15).
  - *Why the burden is on metric:* a false metric type is the error that spreads and merges permanently; a false action type fails closed and corrupts nothing.
- 2.31 Examples: `bookings` → metric if a standing-measure phrase is quoted · `buyback` → action (the metric form is a more specific name, like `buyback_authorization_remaining`) · `dividend` → action (metric form: `dividend_per_share`) · `restructuring` → action unless the evidence proves a standing cost or charge metric.
- 2.32 A guidance or surprise family may attach only to a base that is a proven metric: metric by fixed rule, metric proven under 2.30, or a hidden placeholder (2.26). So `buyback_guidance → buyback` can never pass on an unproven metric type.
- ⚠ **A wrong `action_event` type can block a real metric's series or family until a rebuild.** Accepted as better than a false metric. When the type is set directly, with no metric check, a wrong action type isn't counted by the warning; its symptom is held facts piling up on that Driver.

### Creating a Driver

- 2.33 One real fact in one event is enough; there is no "seen in several events" rule. Boilerplate, bare mentions and non-facts are dropped before storage. Whether a fact is stored never depends on whether it moved the stock.
- 2.34 **Any authorized source may submit raw evidence.**
  - Only the shared core breaks it down, reuses or creates the Driver, builds identity, checks and writes.
  - A source never names or creates a Driver.
  - Drivers may be proposed from prose or readable tables, including qualitative and action causes, but such a proposal may create a Driver only once an independent check for qualitative duplicates exists and passes; until then it is held. Don't weaken this to gain coverage.
  - A source's own grouping of its records carries no identity weight: it never says two records are the same Driver, and the core judges each item on its own.
  - Text is the only route that creates Drivers (6.11).
- 2.35 Every new Driver arrives with its first proven fact ("born complete"). Creating Drivers from names alone is rejected; the only exception is the hidden placeholder (2.26).
- 2.36 A name on the catalog list is not yet a Driver; the Driver comes into being only with its first written fact (2.35).
- 2.37 A bare-named Driver's first fact must have a readable state, not `unknown`; otherwise it is held until such a fact arrives. A `_guidance` or `_surprise` Driver may start with an `unknown`-state fact. This applies only at creation.
- 2.38 The fact type is set once, at creation. A Driver without a type can't accept facts. A Driver that has facts is never re-typed. No tool may rename, delete, re-type, re-key or orphan a Driver that has facts; repairs may only add reversible links.
- 2.39 Submissions from different sources about the same event reach the same identity. Exact duplicates (the same name at the same moment) always end up as one Driver. Two near-synonyms created at the same moment are an accepted split, repaired later with a synonym link.
- ⚠ **Before text can create any Driver, the new build needs three pieces:** the independent identity check (2.40, 8.2), the duplicate check for wording-only Drivers (2.34) and the no-AI safety checks (6.25).

### Same Driver or not

- 2.40 **The identity test:** same object, same business scope, same mechanism, decided by meaning from the evidence.

  The approved identity checklist applies this test to every new "same Driver" decision (reusing a Driver or linking to one) as five checks, each needing evidence from both sides:
  1. the same exact object, not a broader or narrower class;
  2. the same business population and ownership scope;
  3. the same causal mechanism and position;
  4. no equally plausible competing Driver;
  5. the existing Driver's original evidence describes one coherent mechanism.
- 2.41 Counts never decide identity. Company count, industry count, mention count, exact spelling or popularity may never create, merge, rank, establish, confirm or pick a Driver. There is no "broad" label and no company-count threshold (this replaced a company-count "broad" label in the earlier approved design).
- 2.42 Drivers are company-neutral. One is reused across companies only when identity proves the same cause. A cross-company calculation finds its companies from the facts when it runs; fewer than two means no comparison.
- 2.43 Matching searches the whole catalog as it stood at that time, never filtered by company or industry. Industry labels may be shown only as context.
- 2.44 The rules state only the general identity test. Real industry-pair examples may be used only as hidden tests, never as rules.
- 2.45 These are always different Drivers: a base metric and its guidance or surprise flavor; names with different final suffixes; different per-unit denominators; different portions (2.14). Names that only share words (`brent_oil_price` vs `oil_price`) are never matched as the same Driver for now; that stays off until a test set shows zero wrong merges. Until then some real matches are missed on purpose, and each miss is counted.
- 2.46 The same decision is reused when the exact same input comes back unchanged.
- 2.47 A fact is never attached to a Driver that is switched off for review; it is held instead. A refusal is final for that decision: no retry, escalation or weaker check can turn it into a merge. The pair is looked at again only after an exact change in its evidence or state that a rule names in advance (8.15). If an exact-name match turns out to mean something different (one name, two meanings), coin a more specific name once; if no safe name exists, skip it.
- ⚠ **Some wrong "same meaning" calls can't be avoided at first sight.** The promise is zero *measured* errors with honest upper bounds, reversible once evidence builds up; never zero by construction.
- ⚠ **"When unsure, keep separate" creates near-duplicates** (accepted splits, same-moment races, wrongly refused near-matches). The design needs a way to repair them.
- ⚠ **Some wrong merges can't be caught later:** a merge of different flavors that have no suffix was judged once, with full evidence; only suffixed names can be checked mechanically afterwards.

## 3. What is on each fact

*Answers: what makes a fact unique, which fields it carries, and how slices, tags, units, signs, periods and numbers are recorded.*

### Identity

- 3.1 A fact's identity = source event + Driver + scope. The extractor (a person or a model) is never part of it. Once written, the identity and the stored scope never change. *Why:* two readers of the same fact then reach the same record.
- 3.2 The scope parts, each only when present: period · slices · measurement tags · surprise comparison kind (surprise facts only; required there) · a tie-breaker used only for true conflicts (5.3). A whole-company fact has no slice; "total" is never stored as a slice. Formatting may be tidied (e.g. lowercase), but different words are never treated as the same value. *Why a surprise kind:* two different expectation gaps on one Driver and period can both be true, so identity must keep them apart.
- 3.3 A new scope part may be added only if it defines identity for that fact type, can't be worked out from the existing parts, and is never compared across fact types.

### The 24 fields, grouped by meaning

| Field | Meaning | Values and notes |
|---|---|---|
| **Identity:** which fact is this? | | |
| `id` | The fact's identity (3.1) | Never changes |
| `fact_scope` | The scope part of the identity (3.2) | Never changes |
| **Evidence:** where it came from, and when | | |
| `source_type` | The kind of document the quote truly came from (a press-release quote belongs to the 8-K, never a later 10-Q) | `8k` · `transcript` · `10q` · `10k` · `news`; anything else fails closed |
| `quote` | The exact source words | Always required |
| `date` | The source's full public timestamp | |
| `created` | When the fact was written | Set only at creation |
| **Meaning:** what happened | | |
| `driver_state` | The state (§3 States; forecasts and surprises: §4) | From the fact type's list |
| `company_confirmed` | Did the company or its management say it? | Guidance only; always required (4.9) |
| `value_text` | A forecast stated in words, with no number | Guidance only (4.7) |
| `conditions` | A condition attached to a forecast | Guidance only (4.8) |
| **Amounts and comparisons:** what was stated | | |
| `level_low`, `level_high` | The stated value or range | Shapes in 3.48 |
| `level_unit` | Unit of the value, and of any comparison value | Unit list in 3.28 |
| `change_value`, `change_unit` | A stated change, e.g. "+5%" | Only when stated (3.49) |
| `comparison_low`, `comparison_high` | The value compared against: last year's, the consensus, an earlier forecast | Only when stated |
| `comparison_baseline` | What the comparison is against | `consensus` · `prior_year` · `sequential_period` · `previous_guidance` · none (3.52) |
| **Time:** which period | | |
| `fiscal_year`, `fiscal_quarter` | The company's fiscal framing | |
| `period_scope` | The kind of period | `quarter` · `annual` · `half` · `monthly` · `ytd` · `ttm` · `exact_range` · `short_term` · `medium_term` · `long_term` · `undefined` |
| `time_type` | Does the value cover a span or a single moment? | `duration` · `instant`. Always stated, never defaulted. |
| **Grouping and links** | | |
| `series_unit` | A grouping label that keeps one series together when read (3.35) | Set once, when written |
| `xbrl_qname` | The official XBRL line item this metric matches | Metric only; added later (§6) |

- 3.4 One more flag sits outside the 24: `disputed`, set only by the mistake-repair process (6.20).
- *See also:* What may change after a fact is saved: 5.1.

### What each fact type needs

| | metric | guidance | surprise | action_event |
|---|---|---|---|---|
| Identity, state, quote, source, Driver | required | required | required | required |
| Period | when real | required | when real; required for `guidance_vs_consensus` | rare; only when real |
| Value and change | only when stated | only when stated | only when stated | only when stated |
| Comparison values | when stated | the earlier forecast, when stated | the expectation, when stated | when stated |
| Comparison baseline | only `prior_year` or `sequential_period`; expectation baselines forbidden | `consensus` forbidden | required: `consensus` or `previous_guidance` | when stated |
| Surprise kind in scope | forbidden | forbidden | required | forbidden |
| `value_text`, `conditions` | forbidden | allowed (4.7–4.8) | forbidden | forbidden |
| `company_confirmed` | forbidden | required on every stored guidance fact | forbidden | forbidden |
| Direct XBRL line item | allowed | forbidden; inherits from the base | forbidden; inherits from the base | forbidden |

### States

| Type | Allowed states |
|---|---|
| metric | `increased` · `decreased` · `unchanged` · `mixed` · `reported` · `persists` · `unknown` |
| guidance | `introduced` · `raised` · `lowered` · `reaffirmed` · `withdrawn` · `unknown` |
| surprise | `beat` · `in_line` · `missed` · `unknown` |
| action_event | `at_risk` · `announced` · `occurred` · `continued` · `resolved` · `canceled` · `suspended` · `rumored` · `failed` · `unknown` |

- 3.5 The state lives on the fact (`driver_state`), never in the Driver name. The quote stays the precise truth. Good or bad news never decides a state. A state outside the fact type's list is invalid.
- 3.6 **Metric states** (the first row that matches wins):

| The source… | State |
|---|---|
| states a direction | `increased` / `decreased` |
| shows the same Driver moving differently across parts | `mixed` |
| states it is flat | `unchanged` |
| says it is ongoing, with no direction | `persists` |
| gives a bare value | `reported`; but if it also states the prior value, `increased` / `decreased` |
| none of these | `unknown` |

- 3.7 Metric, surprise and action facts are written from the source text alone, never from past facts. Only guidance may look at earlier facts when written, and only at those public before the source's public time (e.g. to copy a withdrawn forecast's series unit, 3.35, or to spread a withdrawal, 4.18). A guidance movement the source doesn't state is still worked out when read, never stored (4.4).
- *See also:* Guidance and surprise states are in §4: 4.4 and 4.10–4.12.
- 3.8 **Action**, the latest stage of one action:
  - **Final:** `failed` = the action fell through other than by the company withdrawing its own plan (this includes declining an offer it never committed to) · `canceled` = the company's own voluntary withdrawal · `resolved` = a settled two-sided dispute · `occurred` = completed.
  - **Not final:** `rumored` = unconfirmed third-party reports (a denial stays rumored) · `at_risk` = a specific, current threat the source flags, not the company's own plan (generic risk boilerplate is dropped) · `suspended` = paused and resumable (shelved, postponed) · `announced` = the company's stated own action before completion · `continued` = still ongoing.
  - Scrap, abandon or withdraw → `canceled`. A threat stays `at_risk` until it happens, then `failed`.

### Links from a fact

- 3.9 Exactly one link to its Driver, and exactly one link to its source event (a filing, transcript or news story). The company is reached through the source event, not a direct link. A source event must belong to exactly one company, found through ownership, never by counting mentions; otherwise it is held.
- 3.10 One link to its period (3.36), when it has one.
- 3.11 Optional links to XBRL data (§6): at most one official line item (metric facts only; the same one named in `xbrl_qname`), and any number of breakdown members (any fact type), each saying which slice part it supports.
- 3.12 Optional verdict links from a source event or daily move event that the fact helps explain (folded Part A2).

### Slices (parts of the company)

- 3.13 A slice is stored as `kind:value`. The kinds, with their tests:
  - `segment` (the company *operates as* it, e.g. `taco_bell`)
  - `product` (it *sells* it, e.g. `iphone`, `aws`)
  - `geography` (it *operates in* it, e.g. `china`)
  - `customer` (it *sells to* them)
  - `channel` (*how* it sells or runs, e.g. `franchised`)
  - `entity_ownership` (a *stake it owns*; the least clean kind — joint ventures and part-owned companies are the strongest cases; other entity rows are provisional)
  - plus the safe fallback `unknown`.
  - *Why:* the tests work for any metric and match how XBRL breaks data down; a fixed set of kinds keeps slices checkable while values stay open.
- 3.14 A real slice is a business population where "revenue or earnings from ___" makes sense. Accounting labels (fair-value levels, a term loan, stock awards, reconciling items) are not slices. Leftovers the source states ("Other", "Corporate Unallocated") are allowed as company-specific slices, marked as not continuous when read. Pure eliminations, fair-value levels and consolidation artifacts are dropped and logged, never stored as slices; blended leftovers follow 3.21.
- 3.15 A brand is not a kind; the axis it sits on, or its role in the prose, decides (Taco Bell → segment; Kraft → product), because the same word can be a segment at one company and a product at another. A fact may have several slice parts; all are kept, never dropped. Slices apply to all four fact types. A period is never a slice. No slice = the whole company (metric, guidance, surprise) or no applicable part (action).
- 3.16 **Which XBRL breakdown axes count as slices is decided offline, by looking at an axis's *members*, never its name.**
  - *Why:* axis names mislead in about 20% of cases.
  - When facts are processed, an axis is one of three things: a known slice axis (use its kind), a known non-slice axis (ignore that part), or an unknown axis (a provisional slice, never silently dropped).
  - No AI judges a slice's kind at runtime.
  - *Why:* company-made axes are common; silently skipping a real one would merge real businesses, while a provisional slice can only over-split.
- 3.17 The list of a company's slice values offered while reading = every member from all its earlier public 10-Q/10-K filings, plus values already used for that company, cut at the source's public time. Naming a Driver uses no such list. Repair work may see the full history. *Why:* a list built from all filings finds discontinued or renamed segments instead of creating duplicates.
- 3.18 For each slice part, in order:
  1. reuse a listed value with the same meaning, taken exactly from the list, never snapped to a near match;
  2. create a new value grounded in the source when the kind is clear from the prose;
  3. use `unknown:<value>` when the kind is unclear, or when the same label exists under several kinds and nothing says which;
  4. leave it out for the true whole company.

  Ambiguous prose must not guess. The AI may pick an existing value or create a new one, but never merges two existing values; only fixed rules delete (from a fixed list) or merge values, and only on an exact match. *Why:* then every AI mistake is an over-split, which can be repaired; a near-match snap could blend two different businesses.

- 3.19 A slice from an unknown XBRL axis is stored as an `unknown` value that records the exact axis, so it can be reused later.
- 3.20 Within one company, a breakdown member joins an existing value only when the whole `kind:value` matches exactly after formatting is tidied. Never a fuzzy match, never word or suffix stripping (`EuropeSegment` ≠ `europe`). The same words under different kinds are different values and never join (`geography:international` ≠ `segment:international`). *Why:* this really happens: the same label appears on both the geography and segment axes at some companies (e.g. `international` at 5 companies).
- 3.21 **Eliminations** (both lists below apply only to segment-type breakdowns). A short, hand-checked list of pure eliminations actually seen on segment axes is always excluded; names never seen are not pre-listed.
  - Blended "Corporate/Other/Eliminations" and reconciling leftovers are kept as provisional slices: stored and never deleted, but kept out of cross-company use.
  - Everything else is a normal slice, so a missed elimination errs on the side of an extra split.
  - Every exclusion is logged.
  - Mistakes are fixed only offline, by moving an item from the excluded list to the provisional list; nothing is demoted automatically.
  - *Why a fixed list, not a word pattern:* a pattern caught real businesses about 20% of the time (e.g. `GlobalPestElimination`, a real Ecolab business).
- 3.22 A stored slice value never changes after it is first written. There is no alias layer and no "confident alias" merging. The only grouping of drifting labels happens at read time, within one company, and only when every linked fact for both labels shares the same exact XBRL axis and member. Drift seen only in prose stays split. *Why:* never changing a stored value keeps identity stable, so re-runs land on the same record.
- 3.23 There is no cross-company rule that equates slice values; provisional slices stay out of cross-company analysis. Reads group by the full series (7.1), never by Driver or slice alone. *Why:* grouping by Driver alone would blur, say, Taco Bell, China and the company total into one line.
- ⚠ **The one place a mistake merges instead of splits:** an XBRL axis wrongly marked "not a slice" silently folds real segment data into the whole-company total, with no automatic repair. Only offline review of the logged skips protects it.
- ⚠ **Unreviewed XBRL axes can hold real business data:** 246 real Agilent end-market facts sat on an axis once marked "not a slice".

### Measurement tags

- 3.24 Measurement tags are an open, source-grounded, sorted set inside the scope; not a fixed list and not part of the name. *Why:* one fixed slot would merge GAAP basic with GAAP diluted; keeping the exact words keeps "adjusted EPS" apart from "core EPS".
- 3.25 The exact qualifying words are copied from the source, then tidied (lowercase words joined with `_`) and sorted. One unbroken run of qualifiers is one tag (`adjusted, diluted` → `adjusted_diluted`); split only where other words come between.
- 3.26 **Never drop a qualifier.** Any modifier of a number that isn't fully captured by the name, period, unit, slice or growth basis stays as a tag (e.g. `ttm` when the true rolling window can't be built).
  - When unsure, keep it.
  - Example: "more than $4B" vs "at least $4B" — a lower bound alone (a "floor", 3.48) can't tell them apart, so the wording stays as a tag.
  - An empty set is valid and never means GAAP.
  - What counts as "already captured" can be subtle: Darden's "before income tax" heading on a direct impairment charge adds nothing, because the charge itself is the direct amount, so the tag is allowed but unnecessary (a settled review; see the watch-out below).
- 3.27 Tag synonyms are never merged when writing. Views that treat equivalent labels alike exist only at read time and never change identity.
- ⚠ **Qualifiers are subtle.** Darden's $24.7M impairment was judged not to need its "before income tax" column heading, because the charge itself is the direct amount; the settled review says the extra tag is allowed but unnecessary (3.26). That judgment doesn't allow dropping meaningful qualifiers in general. The definitions used to judge it were never given to the AI that did the extracting.
- ⚠ **Same fact, different records.** Two correct readings of one fact (e.g. with or without an optional tag) create two different identities. Consistent reuse of the same Driver and tags is unproved.
- ⚠ **Wording drift in measurement tags can split one series:** a company restating "adjusted" as "non-GAAP" may split one series in two. The loss is accepted; only a read-time view can bring them together, and grouping by XBRL member doesn't cover it.

### Units, scale and signs

- 3.28 Units: `usd` (money per unit: prices, per-share and per-barrel amounts) · `m_usd` (money totals, stored in millions: "$1.5 billion" → 1,500) · `percent` (a percentage level, e.g. a 17.6% margin) · `percent_yoy` (growth vs a year earlier) · `percent_sequential` (growth vs the previous comparable period) · `percent_points` · `basis_points` · `count` (e.g. a share count) · `x` (a multiple, e.g. 2.5x) · `unknown`.
- 3.29 **The unit and scale of every number must be backed by evidence.**
  - For text facts, that's the smallest span inside the quote that supports the scale ("billion" for billions; a "$" alone is enough only at a scale of 1).
  - Evidence may be missing only when the scale is 1 and there's no unit or scale marker.
  - For XBRL-backed facts, the filing's own unit and scale data replaces quote evidence.
  - A unit or scale is never worked out from a name, label, concept name or the size of the number.
  - If the marker (e.g. a "$ in millions" table heading) sits outside the quote, the quote is widened to include it, or the fact isn't recorded; nearby text is never searched for it.
  - Numbers stay exact at every step: scaling is exact, nothing is rounded or cut to fit, and a number that can't be kept exactly is held.
  - Two amounts are compared only on the same scale ("1 billion" and "1 million" never match).
- 3.30 **The value and its comparison share one unit (`level_unit`); a change has its own (`change_unit`).**
  - Work them out separately.
  - `level_unit` is required when any value or comparison number exists; `change_unit` when a change exists.
  - `unknown` is allowed when the source doesn't settle it safely.
  - No number → no unit, with one exception: a growth basis the source supports goes in `level_unit` even with no number (3.33).
  - *Why:* a value and its change often have different units; comparisons are almost always in the value's unit; and forcing a unit onto a number-free fact would invent data.
- 3.31 Validity: percent units and `x` need a scale of 1; cents on a company-wide total is invalid; money in a currency other than US dollars is `unknown` and watched (9.1).
- 3.32 Units live on facts, not Drivers; per-unit names: 2.16. *Why:* one Driver can have facts in different units over time.
- 3.33 **Growth basis** (which unit a growth number gets):

| The source says… | Unit |
|---|---|
| points or basis points (this wins over any "year-over-year" or "sequential" wording) | `percent_points` / `basis_points` |
| year-over-year, comparable or annual growth | `percent_yoy` |
| bare growth on a dated period | `percent_yoy` (the standard year-ago reading); switched to `percent_sequential` only by evidence in the same document, never by company history |
| growth against the immediately previous comparable period | `percent_sequential`; valid only for periods shorter than a year (on an annual period, sequential equals year-over-year, so it is always `percent_yoy`) |
| growth over a vague horizon | `unknown` |
| "up or down X%" on a metric that is itself a percentage | `unknown`, unless points, basis points or "to X%" is stated |

- Growth is never plain `percent`.
- A value stated on two bases becomes two facts, one per basis.
- A numberless growth fact may take its unit from the source's framing; that unit goes in `level_unit` (`change_unit` is used only when a change number exists).
- Adjustments like constant currency or organic go in measurement tags and never decide the basis.
- *Why:* stamping a sequential forecast as year-over-year is wrong data and mixes the two in one series.

- 3.34 **Signs: store the signed value.** A net loss is negative, never a positive "loss" amount. A charge or provision is positive; a benefit, credit, release or reversal is negative.

| Source says | Stored as |
|---|---|
| "$1.5–2.0B loss" | range −2000 to −1500 |
| "at least a $1B loss" | a ceiling of −1000 with no lower bound (income is at most −1000) |
| "EPS $(0.10) to $0.05" | −0.10 to 0.05 |
| "impairment charge $2B" | +2000 |
| "provision release $50M" | −50 |
| "loss narrowed" | `increased` |
| an income-tax benefit of −94 against −175 | `increased` (−94 is higher) |

- Bounds follow the sign: because a loss is negative, "a loss of up to 2B" sets a floor at −2B (it can go no lower).
- Ranges may cross zero. A loss with no number has no numeric bounds. A conditional downside stays in words.
- The sign can come from a noun (loss, charge, benefit), a comparison ("no worse than", "narrower", "wider"), accounting notation (brackets or a minus) or context.

- 3.35 **Series unit.** Each fact gets a grouping unit, set once when written:
  - a fact with a value uses its value's unit, with money put on the Driver's one scale within a currency.
  - A fact with only a change (no value) uses the Driver's usual unit only when its own evidence (never the name) proves that unit; otherwise it keeps its own change unit (its own group) or `unknown`.
  - A fact with no number has none, except a withdrawal or reaffirmation, which copies the unit of exactly one clear earlier forecast (otherwise it fails closed).
  - Reads group by exact equality: no unit families, and `unknown` is never absorbed.
  - The series unit never rewrites the stored values.
- ⚠ **Companies that guide sequentially but omit the word** get the year-over-year default. Accepted and watched.

### Periods

- 3.36 A fact's period is the real calendar window the fact is about. It is not the event date, a raw "Q1", a forecast marker or a stand-in for the fact type. One kind of period record serves all four types and stores only its ID and start and end dates; the fiscal framing stays on the fact, because companies describe the same window differently. *Why real windows:* only they compare across companies — a December-year-end Q1 (Jan–Mar) is not a September-year-end Q1 (Oct–Dec).
- 3.37 Guidance always needs its *target period* (the period the forecast is for): a real one, or an explicitly stated vague horizon. Metrics and surprises use a period that is stated, clearly implied or safely worked out. An action gets a period only when a real window is stated; never force one, since that would invent structure. The filing type alone never says whether a figure is quarterly or annual (a 10-K can state a fourth quarter, an 8-K a full year); that comes from the stated wording or the source's own series.
- 3.38 A result surprise uses the reported period. A `guidance_vs_consensus` surprise uses the forecast's target period, even if it has ended. The source event's own details (e.g. the period a filing covers) may supply an implied reported period only when exact, and never for `guidance_vs_consensus`.
- 3.39 Exact year-to-date, trailing-twelve-month, cumulative and stated ranges beat fiscal shorthand: keep the real dates, never squeeze them into a quarter. *Why:* some fiscal years run 52 or 53 weeks, so month-based math lands a few days off.
- 3.40 Four vague horizons for real dateless windows: `short_term`, `medium_term`, `long_term`, `undefined`. A stated date range is stored as `exact_range`. An unresolved period without an explicit horizon fails. Actions never get a vague horizon. `undefined` means a period-like horizon exists but isn't defined ("going forward"); a periodless action (a CEO resigned) gets no period at all. `undefined` is never a quiet fallback.
- 3.41 One shared fiscal-calendar resolver works out every fact's window: exact dates first, then an explicit horizon, then a stated long range, then the fiscal framing (month, half, quarter, year). A missing fiscal-year end fails closed, because a wrong one silently makes wrong windows. Market-wide facts (oil price, the Fed funds rate) use the calendar year, since they have no company fiscal year.
- 3.42 **Missing or messy dates.**
  - A duration needs both end dates. An end-only horizon ("by 2030") is valid; a start-only one is incomplete and held.
  - A missing end date may be filled only from matching evidence: first confirm the company, fiscal year, quarter (or an explicit calendar range) and period kind all match; then check the whole window makes sense; then keep the given date and fill only the missing one. A single matching day is not proof.
  - Anything unproved or conflicting is held, never guessed: conflicting, mixed or out-of-range details, or a stated label that contradicts the window's length.
  - Holding means no stored record until it's resolved; evidence is never deleted.
- 3.43 Dates from the filing itself win over stored or cached calendar windows. Don't assume stored fiscal dates are correct (see the watch-out below).
- 3.44 **Earnings 8-K pairing.** Each earnings 8-K is matched to its 10-Q or 10-K exactly.
  - Before that filing exists, go ahead only when the quarter's identity is certain.
  - Missing or ambiguous → hold.
  - These are the only two ways: never a third, and never pairing by fiscal label, projected date or filing order.
  - Once the 10-Q or 10-K exists, only the exact match counts: a failed match is held and never falls back to the live check.
  - Several 8-Ks may map to one periodic filing and remain separate events.
  - This pairing only routes the source; the fact's own window is worked out as in 3.41.
- 3.45 The same resolved period appears in the scope and in the period link, checked both ways. After writing, the resolved dates are the truth; raw fiscal year and quarter never regroup facts later. Never group by period alone: forecasts, results and surprises share periods and would blend.
- 3.46 The same window always maps to the same single period record. A single day is an `instant`; a duration whose start equals its end is invalid. Dates are write-once: a wrong first date doesn't fix itself, and a mismatch fails.
- 3.47 `time_type` (duration or instant) is always stated from the meaning, never defaulted.
- ⚠ **Stored fiscal dates can be wrong.** Darden FY2026 Q3 was stored as Dec 1–Feb 28; the filing says Nov 24–Feb 22. The old window came from month-based math made before the filing existed, and other companies haven't been rechecked. Before the fix, giving the correct end date blocked the lookup, while leaving it out silently reused the wrong stored window.
- ⚠ **Dates are write-once:** a wrong first date doesn't fix itself on a re-run.

### Numbers and comparisons

- 3.48 **Number shapes** (a stated zero is a real value, never treated as empty):

| Shape | Means |
|---|---|
| **point** | low and high equal |
| **closed range** | both present, low < high |
| **floor** | low only |
| **ceiling** | high only |
| **numberless** | all empty |

- 3.49 Change and comparison numbers are stored only when the source states them. At most one main comparison per fact; a comparison type may be stored without comparison numbers. Leave the change empty when it could simply be worked out from a closed range; it's worked out when read.
- 3.50 **Value or change?** *(one row is a chosen reading; see the note)*

| The source says… | Stored as |
|---|---|
| a growth percentage on a Driver that is itself a growth rate: same-store sales "rose 3%" | value 3, `percent_yoy` |
| a growth percentage on a Driver with its own level: revenue "up 5%" | change +5, `percent_yoy` |
| a move in basis points or percentage points, with a direction and no "to X%": margin "rose 60 bps" | change +60, `basis_points` (always a change, never the value) |
| the same with "to 17.6%" | value 17.6, `percent` |

**Not settled by the rulebook:** it states the basis-point case two ways (FINAL_DESIGN §7.1 puts it in the value when the Driver is itself a rate; §9 calls it a change). This rule follows §9, which matches the original rule's later, explicit amendment, but the rulebook never says which of its two lines wins. If you disagree, this is the one line to revisit.

- *See also:* For guidance amounts (value or revision?): 4.6.
- 3.51 Sign check: with a stored change, `increased`/`raised` need a positive change and `decreased`/`lowered` a negative one. `beat`/`missed` are exempt (good or bad is a meaning judgment).
- 3.52 **Comparison baseline:** `consensus` · `prior_year` · `sequential_period` · `previous_guidance` · none.
  - Store only the source's headline comparison. On a tie, `prior_year` wins over `sequential_period`; the rest stays in the quote.
  - None when the anchor isn't a prior period: against peers, against an anchor year like 2019, or a streak.
  - "Exceeded expectations" on a surprise → `consensus`. On a guidance fact, "exceeded our guidance" → `previous_guidance`, otherwise none.
  - `consensus` = analysts, the Street, the market. `previous_guidance` = clearly the company's own guidance. There is no "internal target" value: the company's own target wording → `previous_guidance`, otherwise none.
  - A beat size that can be worked out is never stored; it's worked out when read as value − comparison, only for point comparisons.

## 4. Forecasts and surprises

*Answers: how forecasts and surprises are recorded, how forecast movement is worked out, and how a withdrawal spreads.*

### What goes where

- 4.1 **What goes where:**

| The source compares… | Write |
|---|---|
| a reported result with the consensus, or with the company's own earlier guidance | a surprise fact **plus** its metric "home" fact (4.14) |
| a forecast with the consensus | a surprise fact **plus** its guidance home fact |
| a new forecast with the company's own earlier forecast | guidance movement (4.4), not a surprise |
| something with last year or last quarter | a metric change, not a surprise |

- 4.2 The three kinds of surprise comparison: `actual_vs_consensus` · `actual_vs_guidance` · `guidance_vs_consensus`. One surprise Driver holds all three; the kind is part of the fact's scope (3.2).
- 4.3 The surprise kind comes from the basis (a result or a forecast) combined with the baseline (consensus or the company's earlier guidance). Never infer the basis from whether a period has ended.

### Forecasts (guidance)

- 4.4 **Guidance movement: stored when stated, otherwise worked out when read.**
  - A movement the source states (raised, lowered, reaffirmed, withdrawn) is stored as said. When the source states a movement between two closed ranges: midpoint up = `raised`, down = `lowered`, equal = `reaffirmed`.
  - A bare forecast stores `unknown`. Each read then works out the movement (`introduced`, `raised`, `lowered` or `reaffirmed`) by the same midpoint rule, comparing with the previous winning value (after the same-day source ranking and the latest-wins rule, 7.5) in exactly the same guidance series: same company, Driver, slice, target period, measurement tags, series unit and time type. Never across years, quarters, series units or slices.
  - No earlier value → `introduced`; not safely comparable (open or mixed shapes, a numberless earlier value) → `unknown`.
  - It fixes itself when a late fact arrives, and is never written back.
- 4.5 A correction with no business-change wording (known from the source's details or explicit correction wording) gets its worked-out guidance movement forced to `unknown`, so a typo fix is never read as a raise or a cut.
- 4.6 **Guidance amounts: value or revision?** Percent-only guidance stores its growth basis in `level_unit`. On a guidance fact, a change is only the forecast's own revision ("we raised our cost forecast by $4B"); a forecast that the measure itself will change ("we expect costs to rise by more than $4B") is the forecast's value, with the word that says it is a change kept as a tag (3.26). It is neither a revision nor a forecast of the total.
- *See also:* The general value-or-change rule: 3.50.
- ⚠ **What an amount measures is easy to misread.** In the September fuel test, the number was a forecast expense *increase* of more than $4B, associated with higher jet-fuel prices: not the total fuel bill, not a price-only share, and with no baseline. An earlier run got the number, the scale and "more than" right, but treated it as the wrong kind of amount. A candidate fix, tested on four examples only and not adopted: keep in the name a factor that defines what the amount itself measures; leave out a factor that only helps explain an overall total; never invent totals, baselines or causes.
- 4.7 `value_text`: a forecast in words, for guidance facts with no numbers only. Tidied, at most 200 characters, with no stored numbers (the number fields stay empty); date and period anchors are allowed.
- 4.8 `conditions`: guidance only; the condition's wording must remain in the quote.
- 4.9 `company_confirmed`: `true` means the company or its management stated or confirmed it. It's required on every stored guidance fact and decided from who-said-it evidence; sources supply only the evidence. Unclear who said it → the fact is skipped. For now, third-party or rumored guidance is never stored as company guidance, so `false` is never used (9.2). A later company confirmation is a new fact at its own public time; history is never rewritten. *Why only on guidance:* it is the only type whose states can't say "rumored".
- *See also:* A forecast always needs its target period: 3.37.

### Surprises

- 4.10 **Surprise, when it's `in_line`:** whenever there are no words saying good or bad, and the compared value (a result or a forecast) sits inside a closed expectation range or exactly on its edge. This includes a forecast range that contains the consensus number. A beat or miss with no such words that lands strictly inside a closed range is corrected to `in_line`. A value at a stated floor or ceiling is `in_line`.
- 4.11 **Surprise, when it's `beat` or `missed`:** a judgment of the whole phrase, aware of negation, direction and scope. Never assume higher is better, and never map "above" to beat. Words like "above", "below", "exceeded", "ahead of" or "beat the budget" never count as good or bad on their own; they take the same test. An actual range that overlaps the expectation unclearly → `unknown`, unless the source says good or bad.
- 4.12 A result outside the range with no good/bad words needs a stated basis for which direction is good: either the source's own framing, or the metric's meaning. The metric's normal meaning (e.g. more revenue is good) may be used only when there's no common opposite story; capex, R&D, inventory, hiring and cash burn always have one, so they need the source's own framing. Circular, market-reaction, strategy-guess or single-keyword reasons don't count. No valid basis → `unknown`.
- 4.13 Good or bad (beat or miss) is never assigned from the sign of a number; meaning decides.
- 4.14 Every grounded surprise (one tied to a specific metric or forecast, unlike a generic "results beat") needs a matching home fact in the same event: a result surprise → its metric fact; a `guidance_vs_consensus` surprise → its guidance fact. They must match on family, period, period kind, slice, measurement and, when there are values, the tidied value and unit. A numberless surprise needs a numberless home. The home fact must itself be accepted for writing; a held or rejected home doesn't count.
- 4.15 An ungrounded "results beat" is held. A result surprise before its period has ended is rejected. A missing home fact means the whole event is read again, never just the surprise alone.
- 4.16 When a source states several comparisons, the home fact keeps exactly one main baseline (e.g. the prior-year headline). An expectation comparison stated alongside is never added to the home fact. The reader must spot it in the source itself (never from an already-stored comparison) and record it as its own surprise fact, where the expectation is stored.
- 4.17 On a surprise, the change is usually empty because it can be worked out from the two values. It is stored only when the source states a difference that can't be worked out and its sign is clear. "Beat by X" with an unclear sign stays empty (the quote carries it). Otherwise it's worked out when read as result − expectation, with good or bad applied at that point.
- *See also:* Which period a surprise uses: 3.38.
- ⚠ **Missed facts aren't caught when writing:** if a reader emits the metric but drops the surprise stated in the same sentence (or the second of two scenario forecasts), nothing flags it at write time. A later, fuller reading fills the gap, and a weaker re-run can't erase it.

### Withdrawn guidance

- 4.18 A withdrawal spreads to other forecasts only when **all** of these hold:
  - the source clearly states a withdrawal (not a policy remark like "suspending guidance practices");
  - its scope is exact (an exact Driver, period and slice, or a true "all FY2026 guidance");
  - it reaches only forecasts that are still open (current, not already withdrawn, window still relevant) and contained by the resolved period and scope, never by loose text matching.

  If the scope is unclear, don't spread. This is the only fact the system derives and writes on its own.

- 4.19 A covered forecast that the same source replaces, reaffirms or keeps is not withdrawn; it gets its own new fact. That exclusion is per forecast; the other covered forecasts are still withdrawn.
- 4.20 Add only, never delete. An older covered forecast that arrives late gets its missing `withdrawn` fact under the same conditions. Repeat withdrawals of an already-withdrawn forecast are ignored when read.
- 4.21 A retraction with no replacement becomes a numberless fact (for guidance: `withdrawn`) only when the Driver and scope are exact. If they're not exact, don't guess.
- *See also:* A withdrawal or reaffirmation with no number copies the series unit of exactly one clear earlier forecast: 3.35.

## 5. When facts repeat, conflict or change

*Answers: what may change after a fact is saved, and what happens with repeats, conflicting values, corrections and amendments.*

### What may change after saving

- 5.1 **What may change after a fact is saved** (a summary; each row points to its rule):

| Part of the record | After it is saved | Rule |
|---|---|---|
| The fact's identity and scope | Never change | 3.1 |
| A Driver's name and fact type | Never renamed, re-typed or re-keyed once it has facts; repairs only add reversible links | 2.38 |
| A stored slice value | Never changes | 3.22 |
| A period's dates | Write-once; a mismatch fails | 3.46 |
| An empty field | May be filled by a compatible piece of the same fact | 5.2, 5.3 |
| A stored value (one of the ten value fields) | Changes only through the repair process | 5.5 |
| Other fields (e.g. quote, state, date) | The last write wins, with a log; a blank never erases a stored value | 5.5 |
| A re-run of the same input | Changes nothing | 5.4 |
| A newly published amendment | Becomes a new fact at its own public time | 5.7 |
| A later company confirmation of guidance | Becomes a new fact; history is never rewritten | 4.9 |
| A wrong synonym or rename link | Switched off, reversibly; never deleted | 6.18 |
| A wrongly attached fact | Flagged `disputed`; kept as flagged history | 6.20 |
| A guidance movement worked out when read | Never written back | 4.4 |

### Repeats and conflicting values

- 5.2 Pieces of the same fact (same event, Driver and scope) are combined first, filling blanks only and never overwriting. Pieces that disagree on a value are not combined. If the pieces could be combined in more than one way, the whole group is held; the input order never decides. *Why:* repeats of the same fact (a press release and the filing's management discussion both saying "Q1 +3%") become one fact.
- 5.3 **Two values for the same fact** (same event, Driver and scope). Decide using the database as it stood before the batch, so the input order can never decide the outcome.
  - Compare only the ten value fields: `level_low`, `level_high`, `level_unit`, `change_value`, `change_unit`, `comparison_low`, `comparison_high`, `comparison_baseline`, `value_text` and `conditions`. The quote, state, company confirmation, producer, source type, date and XBRL links are not compared.
  - Two facts are **the same** when all ten match, blanks included; **compatible** when no field filled on both sides disagrees (blanks don't count); **conflicting** when at least one field filled on both sides disagrees.

| Already stored | What arrives | Result |
|---|---|---|
| no existing fact | new facts | store one; several conflicting new facts → keep them all, each with a tie-breaker added to its scope |
| one existing fact | a compatible fact | fill its blanks |
| one existing fact | a conflicting fact | add a flagged extra fact |
| several existing facts | an exact match | it merges |
| several existing facts | a fact conflicting with all | add an extra fact |
| several existing facts | a compatible but not exact fact | hold (never guess) |
| one partial existing fact | two new facts competing for it | hold both; a fuller re-run settles it |

- 5.4 A fact is re-written only when a field really changes; re-running the same input changes nothing.

### Corrections and amendments

- 5.5 A real correction of a value goes through the repair process. Other fields: the last write wins, and it's logged. A blank never erases a stored value: a re-read with less detail is taken to have missed it, and only the repair process may clear a field. Late history is never re-keyed; two identical facts from a race read as one until repaired. Within one group, at most one fact has no tie-breaker, and every pair of facts must disagree on at least one filled value.
- 5.6 A model may propose synonym links and combinations, but only a reversible link from an approved record is ever applied. A model never deletes, re-keys or moves facts, or skips approval.
- 5.7 An amendment is a new fact at its own public time; the "latest wins" read rule (7.5) makes it win naturally. An amended filing is a new report, never a silent rewrite.
- *See also:* A correction with no business-change wording never reads as a raise or a cut: 4.5.

## 6. Links, and fixing wrong ones

*Answers: how facts link to official filing data, how declared renames work, and how wrong links and wrong facts are caught and undone.*

### Official filing data (XBRL)

- 6.1 Attach the exact company-reported line item, or attach nothing. A wrong link does silent damage until it's found, and decisions already made on it aren't undone; a missing link fills itself in on a later run at no risk. Stored links can be revoked.
- 6.2 Only a base metric gets a direct link. Guidance and surprise facts inherit through the family link; actions never link; a non-GAAP measurement blocks inheritance. *Why:* a forecast or surprise has no XBRL line of its own; the line lives on the metric. If the base is still a hidden placeholder with no metric facts, guidance and surprise get no link for now; a direct guidance or surprise link is never written to fill the gap.
- 6.3 A fact's measurement tags count as GAAP-compatible only when they are empty or exactly one of `gaap`, `basic`, `diluted`, `reported`, `as_reported`. Anything else, including any combination, → no link.
- 6.4 Never linked, as a principle and not a word list: events and macro causes (resignation, buyback, oil price, interest rates, tariffs, weather…); ratios, derived and growth figures (margins, growth, return on invested capital, EBITDA, free cash flow, per-square-foot, mix…); non-GAAP or adjusted figures. Tax rates are real GAAP line items and may link.
- 6.5 A match must be the same metric: cost of revenue ≠ revenue, a subtotal ≠ its total, basic ≠ diluted. Refuse anything related-but-different: GAAP vs non-GAAP, gross vs net, subtotal vs total, the wrong statement, or a breakdown instead of the consolidated line. When two candidates are equally good, take the more widely used one. When unsure, refuse.
- 6.6 Fixed checks, which can only refuse a link, never create one:
  - a point-in-time share count must be an instant, not a period average;
  - a bare `earnings_per_share` or share count means *diluted*, never the basic line;
  - a per-share metric never maps to a total-dollar cash line;
  - these pairs are always different: SG&A (selling, general and administrative costs) vs general & administrative; SG&A vs selling & marketing; operating expenses vs SG&A; total debt vs notes payable.

  *Why:* measured on 274 companies, these checks cut wrong links from 42 to 1, with no loss of good links.
- 6.7 The candidates are the company's own consolidated numeric line items, cut at the fact's public time for history (live may use the latest). The chosen item must be exactly on that list. Only 10-K and 10-Q filings (and their amendments) carry XBRL; 8-Ks never do.
- 6.8 A line item missing from the database never blocks the fact; the link fills in later.
- 6.9 A link to a breakdown member needs both its axis and its member. It's valid only when it matches one real tagged fact exactly: the line item, duration or instant, exact dates, and the complete set of breakdowns (including "none"). Two different breakdown sets are never combined; that would invent a combination no filing has.
- 6.10 When a source supplies XBRL data, it always includes the exact reporting context (the dates, and whether the value covers a span or a single moment); every breakdown carries both axis and member; and "no breakdowns" is sent only as an explicit, checked statement. A missed extraction must never pass as the consolidated whole.
- 6.11 Only text can create Drivers or non-metric facts. Tagged filing data never decides meaning or identity; it may add numeric metric facts only after the Driver and the company's link to that line item are already admitted, and that route is switched off for now (6.12).
- 6.12 **Facts from tagged filing data:** an approved design, switched off until its proofs pass; its full rules are in folded Part A1.
- ⚠ **XBRL can't back up text facts:** only about 35–60% of 8-K money figures later get a matching tagged figure, so a later match is a grading aid only, never evidence. And percentages spoken on calls often can't be safely recomputed from tagged figures: organic, adjusted, constant-currency or rounded figures may use a different definition.
- ⚠ **XBRL links:** high precision was measured, not zero error; in a 274-company test the matcher found about 70% of the true links. The structural monitor catches only structural slips (e.g. a share count mapped to a period total), not same-type scope mistakes. An extra check using the filing's own subtotal structure is recommended before full-scale linking (timing open) and is required before tagged-data facts are switched on (6.12).

### Declared renames ("continues as")

- 6.13 When a company explicitly states that an old label continues as a new one with the same composition and method, a dated, one-way "continues as" link (old → new) is recorded for that company. It can join two Drivers, two slice labels or two measurement tags. *Why:* declared renames are the only way to join old and new labels, including for the ~57% of facts with no XBRL member link, while identity stays split.
- 6.14 Wording like "recast", "recomposed" or "reclassified" refuses it. It needs independent confirmation of the explicit statement, the unchanged composition and both exact ends; otherwise it is refused.
- 6.15 The link is read-only and reversible, and never spreads across family links. Reads use it only if it was public before the as-of date, checked at each hop. A switched-off link is ignored in every view, including views of the past, however late the mistake was found. *Why:* ignoring a link can only split a history, which is safe.
- 6.16 Safety: at most one active link from the same old label (a second is refused); two old labels into one new label switch both off; a loop is refused.
- 6.17 A rename proposal never counts as a fact, and repeating the same proposal never creates a second link. A refused proposal never invalidates the other facts from the same source.

### Undoing mistakes

- 6.18 A confirmed-wrong synonym or rename link is switched off (quarantined) after independent confirmation, and the switch is recorded. Switching a link off needs this independent confirmation but no person, so it can happen automatically; a link is never switched on or loosened automatically, and switching one back on goes through the same approved path.
- 6.19 If a rename link's two ends have XBRL data, a mechanical check across the change switches the link off automatically when the official line item splits or the direction reverses.
- 6.20 A confirmed wrongly attached fact is marked `disputed` and stays out of cross-company and history-weighted uses until cleared. Facts written under a wrong merge before it was found stay on the switched-off Driver as flagged history: kept, never erased, and left out of features.
- 6.21 Never delete, re-key or move history (1.15).
- 6.22 **Checking a suspected wrong link.** As soon as a link is suspected, it is paused for uses that rely on history (cross-company and history-weighted signals); reads of single events carry on. Independent checks (see the word list), given the raw evidence and never the detector's conclusion, must confirm different meanings. If they can't settle it, the pause stays and the problem class goes to the owner as a rule question; it is never silently kept. Every recovery is recorded and becomes a test case.
- 6.23 **Protecting related links.** When a Driver is found to carry two meanings, all its synonym links are paused and re-checked one by one; it can never again receive instant links or feed cross-company signals, and new facts using that exact name must take a more specific name (2.47). When a base metric is switched off, its guidance and surprise family is paused until linked to a clean base; otherwise each member stands alone. A hidden placeholder tied to its name is fixed or dropped.
- 6.24 **Reversing a switch-off.** A wrong switch-off only splits, so it is safe, and it can be reversed through the same approved path (6.18). Facts always stay on their original Driver.
- 6.25 **Safety checks that use no AI.** Before launch, simple checks must watch the stored facts for signs of a wrong merge:
  - one Driver whose facts for the same company point to conflicting official line items or breakdowns;
  - opposite directions for the same company, period and scope;
  - two differently named Drivers that keep sharing the same company, period and line item.

  A Driver with no filing-data backing may be created only once these checks, including the duplicate check for wording-only Drivers (2.34), are in place. The checks may only report, pause cross-company signals and plan a reversible recovery (6.22); they never decide meaning or delete anything. *Why:* they are the only safety net independent of the AI judges (see the watch-out below).

- ⚠ **All the AI judges came from one vendor;** only the mechanical XBRL checks are fully independent of them.
- ⚠ **A wrong merge of two meanings, or a false "continues as" link, has no automatic tripwire when there's no XBRL data.** The old design called this its deepest worry; only drift checks and audits watch it.

## 7. Reading facts back

*Answers: which facts form one history line, which fact wins, and which views the reads must offer.*

- 7.1 Two facts belong to the same series (one continuous history line) only if all of these match exactly: company, Driver, fact type, slice, resolved period, period kind, measurement tags, series unit, time type and, for surprises, the surprise kind. Family is added only for cross-flavor views.
- 7.2 Series units group by exact equality: no unit families, and `unknown` is never absorbed.
- 7.3 Within one event: combine pieces before settling conflicts (5.2). Clean stated parts beat a vague `mixed` fact. A whole-company fact exists only when it is itself stated.
- 7.4 Display order: value → signed change → comparison → guidance words → the trimmed quote (last resort). Duplicates are judged by the stated value or range and its unit, or by the tidied guidance words for qualitative facts; never by the quote. A citation is the Driver name, plus the scope when needed.
- 7.5 Same company, series and day: rank `8k` > `transcript` > `10q` > `10k` > `news`; then the later timestamp, then the source ID. Across days, the latest is the current view and earlier facts stay as history. "Day" means US Eastern time. The same number stated in different sources (e.g. an 8-K, then a 10-Q) is stored as separate facts on separate events; only reads pick one.
- 7.6 History reads use strictly "before the as-of date"; live reads see the current data. Realized returns are never exposed (1.14).
- 7.7 A standing per-unit policy level (e.g. a dividend per share) is a metric; a one-time decision to start, change or suspend the policy is an action (like 1.7).
- 7.8 A direction plus basis points or percentage points, without "to X", is a change, not a level (3.50). "Narrowed" is worked out when read from consecutive closed ranges, never stored.
- *See also:* Guidance movement is worked out when read: 4.4.
- 7.9 Labels are grouped by XBRL member only within one company and slice part, only when they share one exact axis-and-member pair, and only when each label has at least one linked fact and all their linked facts agree. A conflict is logged as a warning and the system carries on; it never waits for a person. Facts without links follow their own label. The group is keyed by the pair, not a label, and only the display grouping changes.
- 7.10 Every read result is labeled `raw` or `reconciled`, and a reconciled result is returned only when asked for. Reconciled views can be switched off, and use only time-aware rename links (6.13–6.16): followed hop by hop, public before the as-of date, with no model calls. Rename chains are the only reconciled view. A second view (grouping by unknown XBRL axis) was reviewed and deferred; don't rebuild it without a fresh owner decision.
- 7.11 **Views the reads must offer:** raw (every stored fact, unchanged); current (the winning fact per series, with conflicts still visible); history (earlier facts before a cutoff); point-in-time (any of these, using only what was public before a given time); reconciled (7.10); and cross-company or industry comparisons (the same Driver, with companies grouped by the official industry data as of that time, 2.42).

## 8. Rules for any build

*Answers: the rules any new build must respect, whatever its design.*

### Who decides

- 8.1 AI judges meaning. Code handles exact structure, source binding, tidying, arithmetic, identities, checks, counting and writing. A source or a weak model never gives the final word on identity, family, links, where a fact goes, eligibility or quarantine.
- 8.2 Whatever proposes an answer never approves or grades it. The reader and the search may only propose an identity; an independent check approves every new identity decision.
- 8.3 No person is needed at runtime. One-time owner approvals and reviews of fixed lists are setup steps, not runtime queues.

### Keep it small and safe

- 8.4 Use the smallest machinery that meets these rules: no wrappers, copied rule engines, parallel vocabularies, speculative layers or future-only machinery.
- 8.5 Fail closed. Uncertain meaning stays separate, or is held, skipped or refused; it is never guessed into an accepted fact or identity. A model's confidence score is never permission to write or merge.
- 8.6 No meaning-based word patterns, word lists, example branches, thresholds, exceptions or fixed values, unless an official standard or a frozen owner decision supplies them. *Why:* such a pattern "passes our samples and misfires silently on the universe it never saw" — e.g. a check for hidden numbers missed "₹500 crore" and "doubled" and wrongly rejected "Q3" and "top 5 markets".
- 8.7 Fix the whole class of a problem, never just one example.
- ⚠ **Too much material stalled the last attempt;** keep the build small (8.4).
- ⚠ **The rules served to the AI drifted from the approved rules:** an old "may" wording was used where an approved update said "must". Keep one copy of each rule.
- ⚠ **Even reviewed rule text had real errors:** a withdrawal exclusion was once mis-copied as a veto, and was fixed later.

### Sources and the AI reader

- 8.8 Quotes are exact source text, found in the source. AI never rewrites, repairs or swaps a quote.
- 8.9 **What a source may send.** A source sends only evidence, as stated. It must never send what the core decides: Driver names, fact IDs or scope, a fiscal year or quarter it worked out, measurement tags, final units, or any number it calculated. The approved rule is to reject the whole item if it does; it replaces an older rule (ignore such fields and recompute them) once proven.
- 8.10 **The AI reader sees the whole source event**, in order: the context is never shortened, and long events are never left out.
- 8.11 Old Guidance data is evidence only: it is never converted, replayed or bridged into Driver facts, and never used to fill a history gap. Whether to accept a measured temporary history gap or wait for fresh Driver history is decided only when the old data is retired. A read with no Driver facts returns an empty result, never old Guidance data. Retiring the old Guidance system keeps a complete, restorable copy; only explicitly approved parts are removed.
- 8.12 AI calls run on subscriptions only: no API billing, no switching providers, no silent fallback. Any pay-per-use service, such as the paid embeddings the July design allowed only to *suggest* match candidates (never to decide), needs its own separate owner approval.
- 8.13 Passing a test qualifies an AI only for that exact task, model, program running it, connection and configuration, and kind of input; it never carries over.
- ⚠ **Every new "same meaning or not?" decision needs an independent check.** Which AI models to use is build work. A July policy for reading tests said: start with the cheapest model, ship a group only with zero wrong answers and real savings, and send only failing or unclear cases to a stronger model. The August rulings then fixed one strong model per task for the build steps, with no cascades, votes or fallbacks. The fixed parts are 8.12–8.13.

### Outcomes, retries and running

- 8.14 **Every item ends in one of five recorded outcomes.** Nothing disappears silently.

| Outcome | Means |
|---|---|
| **written** | a new fact was stored |
| **merged** | it joined an existing fact |
| **held** (parked) | it waits for a specific trigger (8.15) |
| **skipped** | no fact was produced, on purpose; skips are counted |
| **rejected** | the item or its evidence broke a rule |

- "Not found" is a final skip only when every expected source was present and searched without errors; an incomplete search is held, not skipped. Such a skip reopens only on a new source, a repaired source collection, or a certified upgrade to how evidence is located.
- For each source item it reads, the AI reader returns either one or more facts or exactly one stated reason for returning none, never both and never neither; a rename proposal (6.13) counts as neither.
- If writing an event fails, nothing from it is left half-written and nothing is reported as written; its facts are held.
- An item that both breaks a rule and waits on a trigger is rejected, not held.

- 8.15 **A held item is retried only when a specific, checkable event could change the result.**
  - Only "the source was unavailable" has general automatic retry.
  - "Wait for more evidence", time passing, a guessed future filing, vague meaning or a refused identity is not a trigger; with no trigger, the outcome is final (skip, reject or keep separate).
  - A later source is processed as its own event.
  - It may reopen an older event only when a rule proves the exact connection, and the older event still uses only its own evidence.
  - A retry always re-processes the whole event, never one held fact alone.
- 8.16 **Running rules already decided:**
  - When a metric Driver gets its first accepted fact, the company's earlier sources are searched for its history, oldest first. When a new source arrives, it is searched for updates to Drivers already known.
  - A fact found this way still needs its own source's evidence (1.17): an earlier value, period or official tag may only help find candidates, never prove anything. At most one suggested Driver may come with it (several → fail closed); the core re-checks the match from the old source alone, and a mismatch never forces it.
  - An older source found late is processed as history at its own public time; it is never dropped.
  - History work never starves live work: it stays off until its limits are set from measured capacity.
- ⚠ **Late sources must never be silently missed:** a "last seen" marker isn't proof that everything arrived; late and backdated sources need their own check.
- ⚠ **Live arrival was never tested:** when the tests were planned, the database had no events after 2026-04-28.
- ⚠ **Much of the old design was never built,** and its running layer was only partly decided (8.16; the unset targets are 10.3).

### Quality and proof

- 8.17 **Quality bar: zero known-wrong accepted facts or identities.**
  - Then as much coverage as possible without special cases; report every miss and every refusal.
  - Coverage bars in tests are minimums, not targets; a miss is accepted only after showing that no simple general fix recovers it.
  - "Zero wrong in N checks" is always reported with its honest upper bound (up to about 3/N at 95% confidence), never as a bare "zero wrong".
  - **Go-live bar for the catalog:** a final test fixed in advance on fresh events from covered industries, with at least 3,000 graded items and the answer key locked before any AI call; zero confirmed wrong merges; no unresolved disagreement; every miss, refusal and unscorable item counted; and scores at least as good as the earlier measured baselines (Part C). Zero wrong in 3,000 means at most about 0.1% at 95% confidence.
- 8.18 Judge accuracy on meaning, never by checking that text matches. *Why:* on the same data, quote-matching looked ~99% right while judged accuracy was ~29%.
- ⚠ **End-to-end accuracy (source → stored fact) was never measured;** only parts were tested.
- ⚠ **The four key bets were never proven:** (1) a cheap reader loses nothing compared with a strong one; (2) cheap matching can hold zero wrong merges; (3) a strong judge can hold zero wrong "same" calls without refusing everything; (4) facts from text and from XBRL get the same identity.
- ⚠ **Only selected examples passed in September:** four source examples; 8 of the 10 chosen failures untouched; the original 191 targets not re-run. Broader reliability, identity admission, name stability and the wider fiscal-calendar review are unproved.
- ⚠ **A score is only as good as its grader.** If graders miss wrong merges, every later result is meaningless, so qualify graders first.
- ⚠ **A check that reports "clean" without really checking is worse than no check:** a hand-written file list once missed live code.
- ⚠ **Test results can mislead.** A matching quote, amount or item count, or a high score across fields, doesn't prove the right complete fact survived; an unfinished, failed or refused grading never counts as a pass; a pass with a temporary catalog proves nothing about identity or duplicates; and a number can silently lose precision before any check sees it.

## 9. Off for now (first-release limits)

*Answers: what the first release leaves out, and what it takes to reopen each. These are the decisions that can wait (together with 10.1, the one open question tied to a switched-off feature).*

- 9.1 **US dollars only.** Never convert another currency, infer an exchange rate, or treat an unknown or foreign currency as dollars. A text fact in another currency gets the `unknown` unit and is watched; a tagged-filing fact in another currency is skipped and counted. No such fact enters a dollar series. Full currency support later needs its own design, based on an official currency standard, with values kept as stated, currency-safe identities and reads, complete coverage evidence, and no hand-written currency list or conversion rule.
- ⚠ **Other currencies:** the only unit gap found in testing was euros becoming `unknown` (a safe under-merge); non-dollar data is thinly covered.
- 9.2 **Only company-confirmed guidance** is stored (4.9). Third-party or rumored guidance-like claims are never stored as company guidance. Allowing them later needs its own design (separate reads, ranking, comparison, later-confirmation history, source attribution and user-facing behavior), so they can never pass as company guidance. The action state `rumored` is a separate rule and unaffected.
- 9.3 **No cross-company slice comparison.** Company-specific slice values are never compared, equated, merged or ranked across companies; the same words are not proof of the same meaning. Reopen only for a named user with a real need, and a design that keeps precision without aliases, word matching, fuzzy logic or identity changes. If it's ever built, company-specific leftovers ("Other", "Corporate") stay excluded.
- 9.4 **No 8-K item-number categories.** An 8-K's item number is information only. It may not create, merge, type, rank or route a Driver or fact. Reopen only for a named user with a testable need, and never with a hand-written item map, a meaning shortcut or a second reader.
- 9.5 **One source to start:** fiscal.ai data. News and every other source stay off; a later source needs a new explicit owner decision. Every source, fiscal.ai included, must pass its own certification before going live. Each later source's own open questions are decided only when that source is admitted.
- 9.6 **No financial-classification field** on Drivers for now; facts carry exact data instead (company-specific XBRL links, money units). Revisit only if a named user and a testable definition exist.
- 9.7 **No price-move verdicts yet.** No source that submits them is switched on in the first release (A2.1). A verdict links a source event, or a day's stock move, to the fact that helps explain it. The Driver system itself never judges what moved a price: it only stores, checks and audits judgments that a separately approved source submits, and it never shows the realized return to whatever produces a verdict. Full rules: folded Part A2.
- 9.8 **No text values on metrics, no conditions on actions.** Text values on metrics are reconsidered only if a count of real metric facts shows both many numberless readings and real changes the stored states missed (and then only in the source's exact words); conditions on actions only if a count shows that real caveats are common.
- 9.9 **No instant linking.** A newly created Driver is never linked on the spot as a synonym of an existing one. If this is ever switched on, it needs strong independent confirmation.
- *See also:* Facts from tagged filing data are an approved design, switched off until proven: 6.12 and folded Part A1.

## 10. Still open

*Answers: the only undecided questions about what the system must do. Each says what it affects and when to decide. Only 10.1 waits on a switched-off feature; the others come up when you design live Driver creation, plan how the system runs, and design the reader. None blocks designing basic facts. One rule where this file had to choose between two written versions is flagged where it applies: 3.50.*

- 10.1 **Price moves:** how big a daily move must be to count; where a purely macro fact comes from; what to do when two independent causes explain one move. *Affects:* price-move verdicts only, which are off for now. *Decide when:* a price-move source is switched on (9.7).
- 10.2 **Fixing a Driver that was mis-named or mis-typed after it already has facts.** Renaming or re-typing such a Driver is forbidden (2.38), and no approved fix exists; it was left for the design of live Driver creation. *Affects:* live Driver creation. *Decide when:* you design live creation.
- 10.3 **Service targets:** how fast new facts must appear, expected volumes, schedules, alerts and budgets were never set. The running rules that are decided are in 1.14, 8.15 and 8.16. *Affects:* running the system. *Decide when:* you plan how it runs.
- 10.4 **Is a dash (—) in a table a zero?** Test runs read a prior-year dash as zero, but no rule decides it. *Affects:* reading table values. *Decide when:* you design the reader.

## Word list

*Look terms up here as you need them.*

| Word | Meaning |
|---|---|
| **Driver** | One reusable cause or standing thing that can matter to a company or market. Stored as a name plus a permanent fact type. |
| **DriverUpdate** (a "fact") | One real, source-backed occurrence of a Driver in one source event, e.g. "revenue rose 5% to $2.1B" in one earnings release. |
| **Source event** | The one whole document a fact comes from: one SEC filing (all its sections and exhibits), one earnings-call transcript, or one news story. Every fact has exactly one. |
| **Quote** | The exact words in the source that state the fact. |
| **Fact type** | One of four permanent types: `metric`, `guidance`, `surprise`, `action_event` (§1). |
| **State** | What the fact says happened, from a fixed list per fact type, e.g. `raised`, `beat`, `occurred` (§3). |
| **Base metric, family** | `revenue` is a base metric; `revenue_guidance` and its `_surprise` twin are its family. |
| **Synonym link** (`SAME_AS`) | A reversible link saying two Driver names mean the same thing. |
| **Family link** (`BASE_METRIC`) | The link from a guidance or surprise Driver to its base metric. |
| **Slice** | The part of the company a fact is about: a segment, product, geography, customer group, sales channel or owned stake, e.g. `geography:china`. No slice = the whole company. |
| **Measurement tag** | How a number was measured, e.g. `adjusted`, `diluted`, `constant_currency`. |
| **Period** | The calendar window a fact is about, not the day it was said. |
| **Vague horizon** | A named window with no dates: short term, medium term, long term, or undefined. |
| **Public time** | When the source was released to the public. |
| **Catalog** | The list of known Driver names that new facts are matched against. A first version is built and checked before go-live; after that it grows as new Drivers are created (2.35) and is refreshed after review (1.21). A name on the list is not yet a Driver (2.36). |
| **Hold** ("park") | Keep an item unwritten until a specific, checkable event can change the outcome. |
| **Skip** | A final, counted "not written". |
| **Fail closed** | When required proof is missing: don't create, link, merge or write. |
| **XBRL** | The machine-readable tags in SEC filings. A **concept** is an official line item (e.g. `Revenues`); a **member** is a breakdown value (e.g. one segment). |
| **Verdict** | A stored claim that a fact helps explain a stock move. |
| **Daily move event** | A record of a stock's move on a trading day, used as a target for verdicts. |
| **Consensus** | The analysts' expectation (the "Street"). |
| **GAAP, non-GAAP** | GAAP = the official US accounting rules. Non-GAAP = a company's own adjusted figures outside those rules (e.g. "adjusted EPS"). |
| **Percentage point, basis point** | A percentage point is the plain difference between two percentages (5% → 7% = 2 points). A basis point is 0.01 of a percentage point. |
| **Axis** (XBRL) | A breakdown dimension in a filing, e.g. "by segment" or "by region". A member is one value on it. |
| **Bare name** | A Driver name with no final `_guidance` or `_surprise`. |
| **Scale** | The multiplier a number is stated in: "$2.1 billion" is 2.1 at a scale of one billion. |
| **Old Guidance system** | An earlier, separate system that extracted and stored company guidance; Driver facts replace it. |
| **fiscal.ai** | An outside data vendor, used as a *channel*: each row points to one company figure (a label, a value and a period) inside an SEC filing, sometimes with the figure's XBRL tag. The filing is the source event, not fiscal.ai. It is the first release's only channel (9.5). |
| **Core** | The central system that decides meaning and identity and writes facts. Sources only supply evidence. |
| **Reader** | The AI step that reads a source and proposes facts and names. |
| **Producer** | Whatever produces a fact or a verdict (e.g. the reader, or an approved source). |
| **Independent check** | A separate AI call that works from the evidence itself and never sees another call's response, its reasoning or any hidden answer; it is never the call that produced the answer it checks. The same model may be used in separate blind calls. How independent the checks really are is measured, never assumed. |
| **Certification** | Before a source or an AI task goes live, it must pass an independent test on examples it hasn't seen, with zero observed wrong accepted facts and honest error bounds (8.17). Not the same as a "certified upgrade" (8.14), which is a tested change to how evidence is found. |
| **Live, backfill** | Live = handling new events as they arrive; backfill = filling in past events. |
| **As-of date** | The date a view of the past is taken at. It sees only what was public before that date. |
| **Benchmark** | The specific reference a price or rate is quoted on, e.g. Brent or WTI for oil. A stated benchmark stays in the Driver name (2.9, 2.15). |

---

**That's everything you need to design.** Folded below: A, the full rules for switched-off features; B, the rejected ideas; C, where every rule comes from and proof that nothing was lost.

<details>
<summary><b>Part A — Switched-off features</b> (full rules)</summary>

### A1. Facts from tagged filing data

Approved design, switched off until its proofs pass. If it is ever switched on:
- **Scope:** only 10-K and 10-Q filings (and their amendments); only the filing company's own numeric figures; only for a Driver whose line-item link (6.1) is already admitted and active (never a hidden placeholder); only US dollars, shares or dollars per share; only complete breakdowns and exact dates (never a vague horizon), using the company's actual period ends. A figure on a non-slice breakdown or an excluded elimination is skipped whole. Everything else is skipped and counted. Fiscal year and quarter are left empty rather than guessed, and a single-moment figure gets no period kind.
- **Never:** create a name or a Driver, work out a missing quarter, rewrite percentages, infer a value, create a surprise automatically, replace source text, or loosely match a line item. Tagged text blocks never create anything; the full source text stays the baseline.
- **What is stored:** the value exactly as tagged, with state `reported`; any direction is worked out when read, never written back. A quarter or year-to-date figure is compared with the same period a year earlier (give or take 7 days), and an annual figure with the previous annual value; with no clear comparison it stays `reported`, and so, pending testing, does a single-moment figure. A figure for the filing's own period is always written; a figure for an earlier period only if no fact exists yet for it or its value changed (a restatement).
- **Repeats and conflicts inside one filing:** exact repeats are dropped; if repeated values agree within their stated precision, the most precise one is kept; if they disagree beyond it, the whole group is held, never picked. It reopens only if that filing's tagged data changes; an amended filing is a new source.
- **Text and tagged versions of one fact:** they are the same fact only when they share the event, Driver, period, slice and measurement (matched as below) and their values agree within the text's own stated precision; then the text copy is skipped whole, and a tagged fact arriving after its text twin upgrades it in place (see Undo). If they differ in period, slice or measurement, both are kept as separate facts; a same-value near-match that differs only in period or slice is also logged, never merged or relabeled. If they share all of these but the values conflict, the later one is held and the written fact stands: a held text fact is reopened if the line-item link is revoked or a synonym link it relied on is switched off, and becomes final only after independent re-confirmation. Within one event and series, reads prefer the tagged fact.
- **Measurement:** tagged facts carry no measurement tags. When matching, blank, `gaap`, `reported` and `as_reported` count as the same, plus the line item's own basic or diluted tag; basic and diluted never count as the same.
- **Standing:** tagged facts never count as evidence that makes their Driver established (2.2). A quarantined Driver gets no tagged facts (they are held); a frozen one still does.
- **Undo:** each fact records that it came from tagged data, and through which link. A link can be revoked or restored only after independent review, with a record; reads leave out facts from a revoked link, and the affected items are processed again. Upgrading a text fact to a tagged one is recorded and reversible.
- **Timing:** when a new link becomes active, all of that company's eligible filings are processed, including the current one; text work never waits for this.
- **Before switching on:** its proofs must pass, including the extra subtotal check (§6, the ⚠ line on XBRL links).

### A2. Explaining price moves

- A2.1 The Driver system makes no judgment about what moved a price: no attribution prompt, model, rule of thumb or meaning rule. A separately approved future source may submit such judgments. The core only checks, records, plans, stores and audits them, through the same door and core steps as every source; that source may not copy any of the core's checking, planning, writing or audit steps.
- A2.2 A verdict connects a move target (a source event or a daily move event) to the fact that helps explain it. Its key is the move target + Driver + scope + producer, so two producers may each record their own, disagreeing verdict. One verdict key points at exactly one fact, never at two competing facts from the same day (e.g. the same figure from both the 8-K and the call). Live verdicts win over backfilled ones.
- A2.3 A verdict has three independent parts:
  - `stock_impact`: `long` or `short` — the Driver's push, not necessarily the net move.
  - `weightage`: 0.1 to 1.0 in steps of 0.1, or none. An independent force, never a share, never summed to 100%. None = the direction is known but not the size.
  - `confidence`: 0 to 100 in steps of 10, meaning how sure the attribution is.

  Also recorded: the producer, and whether it's `live` or `backfill`.
- A2.4 Reads may work out a share (weightage ÷ total weightage, within one move target — a source event or a daily move event — and producer) and a signed force (weightage × direction). These are never stored as true causal shares, and a move may be partly unexplained. If every weight is empty, both are empty; never divide by zero or invent a weight.
- A2.5 Never show the realized return to whatever produces a verdict (as in 1.14).
- A2.6 Grade verdicts as a set: the net direction and size, plus relative ranking. Never grade a "true share" per Driver, because reality gives only one net return.
- A2.7 **Daily move event:** one record per company and trading day. The realized return stays in the price data; the trading day comes from the returns data. If a filing event exists that day, the move is linked to the filing alone and the daily move event is ignored, but never deleted: its news verdicts are kept and the case is logged; no "superseded" flag is stored. A late filing sorts this out automatically.
- A2.8 Every fact comes from a source event; news is the source for macro facts. A daily move event is only a verdict target, never a source. A purely macro fact with no source is held.

</details>

<details>
<summary><b>Part B — Ideas rejected, and why</b> (don't reopen without new evidence)</summary>

These were considered and decided against. Don't reopen them without new evidence.

| Rejected | What is done instead | Source |
|---|---|---|
| A fixed, closed list of Driver names | Open names from the sources (2.5) | NAME-03 |
| Alias lists, alias files, "confident alias" merging | One name per meaning; reversible synonym links; read-time grouping only | NAME-02; ST §3 |
| Showing the catalog first when reading | Propose from the source first, then match | ST §3 |
| The company's own brand or segment words in the name | Slice (an outside actor, like AWS for another company, stays in the name: 2.13) | ST §3 |
| Adjusted, diluted etc. in the name | Measurement tag | ST §3 |
| Dropping a per-unit denominator, or treating it as a unit | Keep it in the name | ST §3 |
| "Only a change counts as an update" | Any real, quoted fact counts | ST §3 |
| Needing more than two events before a Driver exists | One real fact is enough | ST §3 |
| Verdict "magnitude"; shares that must add up to 100% | `weightage`, an independent force (A2.3) | ST §3 |
| No family link, or merging flavors as synonyms | Family link | ST §3 |
| Periods only for guidance | Periods for all four types | ST §3 |
| Four slice kinds plus a store type | Six kinds plus `unknown` | ST §3 |
| The XBRL member ID as the slice's identity | `kind:value` from meaning; member links are extra | ST §3 |
| A curated dictionary, live value matching, word matching or simple method agreement for XBRL links | The company's own list; exact match or nothing | ST §3; FD §8 |
| Another provider's vocabulary (RavenPack) as the Driver list | Own open vocabulary | ST §2–3 |
| A stored "bound type"; a low-only point | Self-describing number shapes | ST §3 |
| No field for qualitative guidance | `value_text` | ST §3 |
| A list of confirmation categories | `company_confirmed` yes/no | ST §3 |
| Finding non-GAAP figures by name pattern first | Measurement tags first | ST §3 |
| A quiet "undefined" period; a `long_range` period kind | Explicit vague horizons; `exact_range` | ST §2–3 |
| A previous-guidance comparison on a metric | Not allowed (§3 table) | ST §3 |
| Storing `slice=total` | No slice = the whole company | ST §2–3 |
| Only the latest filing as the slice list | All earlier filings plus used values | ST §3 |
| Trusting a single type classifier | A metric must prove itself (2.30) | ST §3 |
| "Above = beat"; failing on sign | Meaning decides | ST §3 |
| Positive loss amounts; separate loss Drivers | Signed values | ST §3 |
| All growth treated as year-over-year | Sequential growth is its own basis | ST §3 |
| Working out guidance movement from earlier facts when writing, and storing it | Stored only when the source states it; otherwise worked out when read (4.4) | ST §3 |
| Dropping measurement tags | Never drop a qualifier | ST §3 |
| A read-time unit-family map | Exact equality | ST §3 |
| Treating slice values that recur across companies as the same | Retired | ST §3 |
| An outside-brand rule of thumb | The role test (2.13) | ST §3 |
| Never reopening a wrong synonym link | Reversible repair | ST §3 |
| Banning every company or entity word in names | Carve-outs (2.18) | ST §3 |
| Permanent automatic refusal of shared-word names | Off until proven safe (2.45) | ST §3 |
| Result-only surprises, with no comparison kind | Three comparison kinds | ST §3 |
| Automatic demotion of excluded slice values | Offline correction only | ST §3; owner 2026-07-17 |
| A word pattern to spot eliminations | A fixed observed list (3.21) | FS-20 |
| Creating Drivers from names alone, or creating the whole catalog up front | Born complete, created at the first fact | FD §4.2; ST §2 |
| Allow/deny lists, a human queue, a generic `_update` bucket, fuzzy placeholder matching | Rules 2.22–2.26 | OD-1 |
| A third model or tie-breaker; re-typing a Driver after it has facts | Rule 2.30 | OD-2 |
| A hard block when surprise directions contradict | A report-only monitor. *Why:* a block would reject correct "lower is better" facts (the original bug) | FD §4.3 |
| A "broad" Driver label, or a company-count threshold | Identity by meaning only (2.41) | Steps 2026-08-14 |
| A keyword list to decide signs | The sign rules (3.34) | OD-12 |
| Storing a surprise size that can be worked out | Worked out when read | FD §7.1 |
| An "internal target" comparison value | `previous_guidance` or none | FD §7.1 |
| Copying the old Guidance system's stored rows into the new system | Fresh extraction from the source documents; old rows are evidence and test input only (8.11) | CC Part III; ST §2 |
| An AI-written summary as a Driver's defining evidence | Keep the raw birth quotes (2.1) | step 4; Plan |
| An AI prompt told to "abstain when unsure" instead of the fixed linking checks (6.6) | The fixed checks. *Why:* the prompt rule quietly dropped 87 correct links to avoid 1 wrong one, and can drift with the model | Consolidation notes |
| Just listing events (as services like RavenPack or Bigdata do) | Grade each cause against what the stock actually did | A-01 |
| Spotting renames by label similarity | Only explicit, confirmed declarations (6.13) | A-03 |
| Admissions decided by thresholds or counts | Meaning, independently confirmed (2.40–2.41) | Plan; BUILD §8.1 |
| Repeating the same AI prompt and voting | Independent checks (8.2) | Plan |

</details>

<details>
<summary><b>Part C — Sources and proof</b> (where every rule comes from; nothing was lost)</summary>

### C1. Where each rule comes from

| Rule or line | Was (version 1.0) | Sources |
|---|---|---|
| 1.1 | 1.1 | FD §1; A-01 |
| 1.2 | 1.2 | CR §1–2, §6 |
| 1.3 | 1.3 | FD §1; A-01 |
| 1.4 | 1.4 | CR §3–5 |
| context: in | §1 'How it fits together' | FD §0, §2, §7.3; Steps 2026-08-14; CC Part III |
| context: flow | §1 'How it fits together' | FD §2 |
| context: out | §1 'How it fits together' | CR §3–5; FD §1; Steps |
| ⚠ Database quirks | Part 2 B8 | WorkOrder |
| 1.5 | 3.1 | DU-05, DU-06 |
| 1.6 | 3.2 | DU-06 |
| 1.7 | 3.3 | DU-06 |
| 1.8 | 3.4 | DU-06 |
| 1.9 | 3.5 | DU-07; owner 2026-07-26 |
| 1.10 | 3.8 | FD §4.1 |
| 1.11 | 1.7 | FD §1 |
| 1.12 | 1.8 | FD §1; MF-12 |
| 1.13 | 1.9 | FD §1; CC §4; BUILD §3 |
| 1.14 | 1.10 | FD §1; WIP Locator; BUILD §4, §8.1; step 10 |
| 1.15 | 1.11 | FD §1 |
| 1.16 | 1.12 | FD §1 |
| 1.17 | 1.13 | WIP Locator; Steps 2026-08-15; step 9 |
| 1.18 | 2.47 | FD §4.1; MF-02, MF-04 |
| 1.19 | 2.48 | FD §4.1; MF-08; BUILD §8.1 |
| 1.20 | 1.5 | Steps 2026-08-14 |
| 1.21 | 1.6 | Steps 2026-08-14 |
| 2.1 | 2.1 | FD §0; A-01; step 4; BUILD §8.1 |
| 2.2 | 2.1a | BUILD §8.1; step 4; step 7; Steps 2026-08-14 |
| 2.3 | 2.2 | NAME-01 |
| 2.4 | 2.3 | NAME-02; step 4; Steps 2026-08-15 |
| 2.5 | 2.4 | NAME-03 |
| 2.6 | 2.5 | NAME-04; A-01 |
| 2.7 | 2.6 | NAME-05 |
| 2.8 | 2.7 | NAME-06; owner 2026-07-11 |
| 2.9 | 2.8 | NAME-07 |
| 2.10 | 2.9 | NAME-08; ST 2026-08-11; DS |
| 2.11 | 2.10 | NAME-09 |
| 2.12 | 2.11 | NAME-10 |
| 2.13 | 2.12 | NAME-11 |
| 2.14 | 2.13 | OD-17; owner 2026-07-15; A-02 |
| 2.15 | 2.14 | NAME-12; UNIT-08 |
| 2.16 | 2.15 | NAME-13; owner 2026-08-11 |
| 2.17 | 2.16 | NAME-14; A-02 |
| 2.18 | 2.17 | NAME-15/16; A-02 |
| 2.19 | 2.18 | NAME-17 |
| 2.20 | 2.19 | NAME-18; A-02 |
| 2.21 | 2.20 | NAME-19; A-02 |
| ⚠ A lawful-looking name can point at the wrong thing | Part 2 A2 | DS |
| 2.22 | 2.21 | OD-1 |
| 2.23 | 2.22 | OD-1 |
| 2.24 | 2.23 | OD-1 |
| 2.25 | 2.24 | OD-1 |
| 2.26 | 2.25 | OD-1; FD §0 |
| 2.27 | 2.26 | OD-2 |
| 2.28 | 2.27 | OD-2 |
| 2.29 | 2.28 | OD-2; step 4 |
| 2.30 | 2.29 | OD-2; Steps 2026-08-15; step 4 |
| 2.31 | 2.30 | OD-2 |
| 2.32 | 2.31 | OD-2 |
| ⚠ A wrong `action_event` type can block a real metric's series or family until a rebuild | Part 2 A5 | OD-2 |
| 2.33 | 2.32 | FD §4.2; WorkOrder |
| 2.34 | 2.33 | FD §4.2; Steps 2026-08-14; step 2; step 4; CC |
| 2.35 | 2.34 | FD §4.2 |
| 2.36 | 2.35 | owner 2026-07-15 |
| 2.37 | 2.36 | owner 2026-07-15 |
| 2.38 | 2.37 | FD §4.1, §4.2 |
| 2.39 | 2.38 | FD §4.2; OD-15 |
| ⚠ Before text can create any Driver, the new build needs three pieces | Part 2 E4 | step 4; WIP Locator; BUILD §8.1 |
| 2.40 | 2.39 | Steps 2026-08-15; step 4 |
| 2.41 | 2.40 | Steps 2026-08-14, 2026-08-15 |
| 2.42 | 2.41 | Steps 2026-08-14 |
| 2.43 | 2.42 | Steps 2026-08-15 |
| 2.44 | 2.43 | Steps 2026-08-15 |
| 2.45 | 2.44 | OD-19; OD-18 |
| 2.46 | 2.45 | Steps 2026-08-15 |
| 2.47 | 2.46 | OD-18; step 4; Steps 2026-08-15 |
| ⚠ Some wrong "same meaning" calls can't be avoided at first sight | Part 2 A8 | BUILD §8.1 |
| ⚠ "When unsure, keep separate" creates near-duplicates | Part 2 A12 | FD §1, §4.2; OD-18 |
| ⚠ Some wrong merges can't be caught later | Part 2 A11 | CONSOLIDATION |
| 3.1 | 4.1 | FS-01..04; FD §5.1 |
| 3.2 | 4.2 | FD §5.1; OD-21 |
| 3.3 | 4.3 | FD §5.1 |
| table: the 24 fields | §4 | FD §7.1; CC Part III |
| 3.4 | 4.12 | FD §7.1 |
| table: what each fact type needs | §4 | FD §7.2 |
| 3.5 | 4.4 | DU-08..12 |
| 3.6 | 4.5 | DU-08 |
| 3.7 | 4.6 | DU-08; FD §4.3; BUILD §5 |
| 3.8 | 4.11 | DU-12 |
| 3.9 | 4.14 | FD §7.3; BUILD §11; WIP Locator |
| 3.10 | 4.15 | FD §6.2 |
| 3.11 | 4.16 | FD §7.3 |
| 3.12 | 4.17 | FD §7.3 |
| 3.13 | 5.1 | FS-05.. |
| 3.14 | 5.2 | FD §5.2 |
| 3.15 | 5.3 | FD §5.2; A-03 |
| 3.16 | 5.4 | FD §5.2; FS-11, FS-12 |
| 3.17 | 5.5 | FS-14 |
| 3.18 | 5.6 | FS-04, FS-15, FS-16 |
| 3.19 | 5.7 | FD §5.2 |
| 3.20 | 5.8 | FS-18; owner 2026-07-17 (ST §4) |
| 3.21 | 5.9 | FS-20; owner 2026-07-17 |
| 3.22 | 5.10 | FD §5.2; FS-17 |
| 3.23 | 5.11 | FS-22 retired; FS-24 |
| ⚠ The one place a mistake merges instead of splits | Part 2 B1 | A-66 (ISS-15) |
| ⚠ Unreviewed XBRL axes can hold real business data | Part 2 B4 | owner 2026-07-17 |
| 3.24 | 5.12 | FS-25 |
| 3.25 | 5.13 | OD-9 |
| 3.26 | 5.14 | OD-9; DS |
| 3.27 | 5.15 | OD-9 |
| ⚠ Qualifiers are subtle | Part 2 A3 | DS |
| ⚠ Same fact, different records | Part 2 A4 | DS |
| ⚠ Wording drift in measurement tags can split one series | Part 2 A10 | CONSOLIDATION |
| 3.28 | 5.16 | UNIT-01, 08, 11; A-04 |
| 3.29 | 5.17 | UNIT-04; Steps 2026-08-18; CC; BUILD §11 |
| 3.30 | 5.18 | FD §6.1; UNIT-05, 09, 10; step 1 |
| 3.31 | 5.19 | FD §6.1 |
| 3.32 | 5.20 | FD §6.1; UNIT-07 |
| 3.33 | 5.21 | OD-11; UNIT-12 |
| 3.34 | 5.22 | OD-12 |
| 3.35 | 5.24 | OD-10 |
| ⚠ Companies that guide sequentially but omit the word | Part 2 A6 | OD-11 |
| 3.36 | 5.25 | PER-01, 02, 13 |
| 3.37 | 5.26 | FD §6.2; PER-05; CC |
| 3.38 | 5.27 | OD-21 |
| 3.39 | 5.28 | FD §6.2; PER-07 |
| 3.40 | 5.29 | FD §6.2; PER-08 |
| 3.41 | 5.30 | FD §6.2; PER-15, 16 |
| 3.42 | 5.31 | step 1; owner 2026-07-17; DS |
| 3.43 | 5.32 | FD §6.2 note; DS |
| 3.44 | 5.33 | PER-21; owner 2026-07-20 |
| 3.45 | 5.34 | FD §6.2; PER-14 |
| 3.46 | 5.35 | PER-18 |
| 3.47 | 5.36 | FD §6.2 |
| ⚠ Stored fiscal dates can be wrong | Part 2 B2 | FD §6.2 note; DS |
| ⚠ Dates are write-once | Part 2 B3 | PER-17 |
| 3.48 | 5.37 | FD §7.1; ST; BUILD §4 |
| 3.49 | 5.38 | FD §7.1 |
| 3.50 | 5.40 | FD §7.1, §9; DU-16; UNIT-05; A-09; DS; Part 3 |
| 3.51 | 5.41 | FD §7.1 |
| 3.52 | 5.42 | FD §7.1 |
| 4.1 | 3.7 | FD §7.2 |
| 4.2 | 3.6 | OD-21 |
| 4.3 | 6.3 | OD-21 |
| 4.4 | 4.7, 8.9 | DU-09; OD-14; FD §9 |
| 4.5 | 6.9 | FD §9 |
| 4.6 | 5.40 | FD §7.1, §9; DU-16; UNIT-05; A-09; DS; Part 3 |
| ⚠ What an amount measures is easy to misread | Part 2 A1 | DS |
| 4.7 | 5.44 | FD §7.1 |
| 4.8 | 5.45 | FD §7.1 |
| 4.9 | 5.46 | FD §7.1; MF-11; owner 2026-07-15; Steps 2026-08-14 |
| 4.10 | 4.8 | DU-10 |
| 4.11 | 4.9 | DU-10; OD-13 |
| 4.12 | 4.10 | DU-10 |
| 4.13 | 5.23 | OD-13 |
| 4.14 | 6.1 | FD §5.1; owner 2026-07-16; BUILD §11 |
| 4.15 | 6.2 | FD §5.1 |
| 4.16 | 5.43 | DU-15 |
| 4.17 | 5.39 | OD-13 |
| ⚠ Missed facts aren't caught when writing | Part 2 C4 | A-66 (ISS-62) |
| 4.18 | 6.10 | FD §9 |
| 4.19 | 6.11 | FD §9 |
| 4.20 | 6.12 | FD §9 |
| 4.21 | 6.13 | FD §9 |
| 5.1 | new summary | the rules it points to |
| 5.2 | 6.4 | FD §5.1; FS-03; BUILD §11 |
| 5.3 | 6.5 | OD-8 |
| 5.4 | 4.13 | FD §7.1 |
| 5.5 | 6.6 | OD-8; owner 2026-07-03; BUILD §5 |
| 5.6 | 6.7 | FD §5.1 |
| 5.7 | 6.8 | OD-14; owner R6 |
| 6.1 | 7.1 | XC-01..; FD §8 |
| 6.2 | 7.2 | FD §4.1, §8; MF-10; XC-12 |
| 6.3 | 7.3 | XC-05 |
| 6.4 | 7.4 | XC-05 |
| 6.5 | 7.5 | XC-06 |
| 6.6 | 7.6 | XC-07 |
| 6.7 | 7.7 | FD §8; XBRL design |
| 6.8 | 7.8 | FD §8 |
| 6.9 | 7.9 | FS-21; owner 2026-07-17 |
| 6.10 | 7.10 | FD §2; CC; owner 2026-07-15 |
| 6.11 | 7.11 | Steps 2026-08-14; step 12 |
| 6.12 | 7.12 (short form) | FD §8; BUILD §8.2; step 12 |
| ⚠ XBRL can't back up text facts | Part 2 B6 | WIP Locator |
| ⚠ XBRL links | Part 2 C7 | FD §8; XC-16; step 12; BUILD §12 |
| 6.13 | 2.49 | OD-20; A-03 |
| 6.14 | 2.50 | OD-20 |
| 6.15 | 2.51 | OD-20; FD §5.4 |
| 6.16 | 2.52 | OD-20 |
| 6.17 | 2.53 | Steps 2026-08-14 |
| 6.18 | 2.54 | FD §5.4; BUILD §8.1 |
| 6.19 | 2.55 | FD §5.4 |
| 6.20 | 2.56 | FD §5.4; BUILD §8.1 |
| 6.21 | 2.57 | FD §5.4 |
| 6.22 | 2.58 | BUILD §8.1; step 4 |
| 6.23 | 2.59 | FD §5.4; BUILD §8.1; step 4 |
| 6.24 | 2.60 | BUILD §8.1; step 4 |
| 6.25 | 2.61 | BUILD §8.1; step 4; WIP Locator |
| ⚠ All the AI judges came from one vendor | Part 2 A9 | BUILD §8.1 |
| ⚠ A wrong merge of two meanings, or a false "continues as" link, has no automatic tripwire when there's no XBRL data | Part 2 A7 | FD §5.4; BUILD §8.1 |
| 7.1 | 8.1 | FD §9 |
| 7.2 | 8.2 | OD-10 |
| 7.3 | 8.3 | FD §9 |
| 7.4 | 8.4 | FD §9 |
| 7.5 | 8.5 | FD §9; CC Part III |
| 7.6 | 8.6 | FD §9 |
| 7.7 | 8.7 | FD §9 |
| 7.8 | 8.8 | FD §9 |
| 7.9 | 8.10 | FD §9 |
| 7.10 | 8.11 | FD §9, §5.4; step 8 |
| 7.11 | 8.12 | step 8 |
| 8.1 | 11.1 | FD §1; Steps |
| 8.2 | 11.2 | Steps 2026-08-14, 2026-08-15 |
| 8.3 | 11.3 | FD §1 |
| 8.4 | 11.4 | FD §1; Steps |
| 8.5 | 11.5 | FD §0; Steps; step 4 |
| 8.6 | 11.6 | Steps; WorkOrder |
| 8.7 | 11.8 | Steps |
| ⚠ Too much material stalled the last attempt | Part 2 E1 | owner, at this restart (2026-09-25) |
| ⚠ The rules served to the AI drifted from the approved rules | Part 2 A13 | DS |
| ⚠ Even reviewed rule text had real errors | Part 2 C8 | CONSOLIDATION |
| 8.8 | 11.11 | Steps 2026-08-18; owner 2026-08-11 |
| 8.9 | 11.16 | CC; Steps 2026-08-14 |
| 8.10 | 11.17 | Steps 2026-08-18 |
| 8.11 | 11.15 | step 12; CONSOLIDATION; CC Part III; Steps; step 10 |
| 8.12 | 11.12 | Steps 2026-08-14, 2026-08-19; project CLAUDE.md; BUILD §8.1 |
| 8.13 | 11.13 | Steps 2026-08-19; steps 9, 14 |
| ⚠ Every new "same meaning or not?" decision needs an independent check | Part 2 D1 | Steps 2026-08-14, 2026-08-15, 2026-08-19; FinalPlan; FD §10 |
| 8.14 | 11.9 | FD §0; step 5; CC Part I; Steps 2026-08-14; BUILD §11; ST |
| 8.15 | 11.10 | Steps 2026-08-15; step 10 |
| 8.16 | 11.18 | WIP Locator; FinalPlan; step 10 |
| ⚠ Late sources must never be silently missed | Part 2 E2 | step 10 |
| ⚠ Live arrival was never tested | Part 2 B9 | WorkOrder |
| ⚠ Much of the old design was never built | Part 2 E3 | BUILD §7; FD §10 |
| 8.17 | 11.7 | Steps; Plan; OD-6; BUILD §4; step 7 |
| 8.18 | 11.14 | PIPE-32 |
| ⚠ End-to-end accuracy (source → stored fact) was never measured | Part 2 C1 | BUILD §3; CC Part III |
| ⚠ The four key bets were never proven | Part 2 C2 | Plan §12 |
| ⚠ Only selected examples passed in September | Part 2 C3 | DS |
| ⚠ A score is only as good as its grader | Part 2 C5 | Plan |
| ⚠ A check that reports "clean" without really checking is worse than no check | Part 2 C6 | WorkOrder |
| ⚠ Test results can mislead | Part 2 C9 | PIPE-32; ST; DS; BUILD §11 |
| 9.1 | 10.1 | Steps 2026-08-14 |
| ⚠ Other currencies | Part 2 B7 | UNIT-13; WorkOrder |
| 9.2 | 10.2 | Steps 2026-08-14 |
| 9.3 | 10.3 | Steps 2026-08-14; FS-23; FD §5.2 |
| 9.4 | 10.4 | Steps 2026-08-14 |
| 9.5 | 10.5 | Steps 2026-08-14; CC Part I §9 |
| 9.6 | 10.6 | FD §10; owner 2026-07-19 |
| 9.7 | 10.7 | Steps 2026-08-16 |
| 9.8 | 10.8 | Steps; FD §10; A-11 |
| 9.9 | 10.9 | FD §5.4; BUILD §8.1 |
| 10.1 | 13.1 | FD §7.3 |
| 10.2 | 13.2 | FD §4.2, §10; OD-7 |
| 10.3 | 13.3 | FD §10; BUILD §7; step 10 |
| 10.4 | Part 2 A14 | ST; DS |
| A1 (tagged filing data, full rules) | 7.12 (full rules) | FD §8, §9; BUILD §8.2; step 12 |
| A2.1 | 9.1 | Steps 2026-08-16 |
| A2.2 | 9.2 | FD §7.3 |
| A2.3 | 9.3 | FD §7.3 |
| A2.4 | 9.4 | FD §7.3; A-95; step 8 |
| A2.5 | 9.5 | FD §7.3 |
| A2.6 | 9.6 | DU-23 |
| A2.7 | 9.7 | FD §7.3 |
| A2.8 | 9.8 | FD §7.3 |

### C2. Old rule IDs

Every numbered rule family in the old rule map (`ST` §7.1) is accounted for:

| Old IDs | Where they are now |
|---|---|
| NAME-01..19 | 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 2.11, 2.12, 2.13, 2.15, 2.16, 2.17, 2.18, 2.19, 2.20, 2.21 |
| FS-01..27 | 3.1, 3.13, 3.16, 3.17, 3.18, 3.20, 3.21, 3.22, 3.23, 3.24, 5.2, 6.9, 9.3; FS-22 retired (3.23); FS-23 deferred (9.3) |
| UNIT-01..14 | 2.15, 3.28, 3.29, 3.30, 3.32, 3.33, 3.50, 4.6; also ⚠ Other currencies; UNIT-14 left out (build wiring) |
| PER-01..21 | 3.36, 3.37, 3.39, 3.40, 3.41, 3.44, 3.45, 3.46; also ⚠ Dates are write-once; PER-20 left out (build) |
| MF-01..12 | 1.12, 1.18, 1.19, 4.9, 6.2 |
| DU-01..24 | 1.5, 1.6, 1.7, 1.8, 1.9, 3.5, 3.6, 3.7, 3.8, 3.50, 4.4, 4.6, 4.10, 4.11, 4.12, 4.16; also A2.6 |
| XC-01..18 | 6.1, 6.2, 6.3, 6.4, 6.5, 6.6; also ⚠ XBRL links; XC-16 → the ⚠ line on XBRL links (§6); XC-18 (reuse one link per company and Driver; one AI call per company) left out as build scaling; model choice, prompt text and monitor mechanics left out |
| OD-1..21 | 2.14, 2.22, 2.23, 2.24, 2.25, 2.26, 2.27, 2.28, 2.29, 2.30, 2.31, 2.32, 2.39, 2.45, 2.47, 3.2, 3.25, 3.26, 3.27, 3.33, 3.34, 3.35, 3.38, 4.2, 4.3, 4.4, 4.11, 4.13, 4.17, 5.3, 5.5, 5.7, 6.13, 6.14, 6.15, 6.16, 7.2, 8.17, 10.2; also ⚠ A wrong `action_event` type can block a real metric's series or family until a rebuild; ⚠ "When unsure, keep separate" creates near-duplicates; ⚠ Companies that guide sequentially but omit the word; OD-5 never decided (see the unapproved proposals below); OD-6 → the go-live bar in 8.17 |
| PIPE-01..37 | Left out (catalog-building procedure); PIPE-32 → 8.18; its time rule for naming → 1.14 |
| FACT-01..36 | Left out (fact-writing procedure); its meaning rules are in §3–§5 (re-checked 2026-09-26: the no-blank-overwrite rule is in 5.5) |
| T1.1..T12.9, GI-01..04, D1..D8, D-1..D-13, K2 | Left out (duplicate census, retiring the old Guidance system, build constants, doc-debt history, repair batching) |
| 43 replaced rules (`ST` §3) | The rule-level ones are in Part B; the rest were build mechanics, e.g. the stored fact hash (`evhash16`; re-runs now compare fields directly, 5.4) and old tie-breaker formats |
| Source contract clauses (`CC` Part I) | Their meaning is in 2.34, 6.10, 8.1, 8.14, 8.8; formats left out |

**How to read this table:** each ID is *kept* (its meaning is in a rule above), *replaced* (the later rule is above; the old idea is in Part B), *conditional* (kept with its condition, e.g. 6.12 and §9) or *left out* as build detail. This shows every rule ID is accounted for; it can't prove every sentence of every source survived. As an extra check, independent reviews on 2026-09-26 (Codex and two Claude sessions) listed every gap they found; each was checked at source.

### C3. Left out, by source (all are "how", history or status)

- **FINAL_DESIGN.md:** §10 build-status tags; the fact-ID and scope text formats; the tie-breaker recipe and lookup query; database write shapes and constraints; decision memo files; the two-call checks (OD-1 "run twice", OD-2's two steps); the model named for XBRL linking; the linking prompt text; how the monitors work; locks.
- **Steps.md:** reader call shape and reply format; which AI model runs each step; approval rules for commits, pushes, activation and source retrieval; the V1-to-V2 switch; the step order; per-step AI tables; housekeeping.
- **STATUS_AND_HISTORY.md:** handover and status; experiment decisions; history, cross-reference tables and archive lists; the reader-test policy; the internal writer contract; the ID-format law; the interim period labels (their permanent checks are kept in 3.42); the V2 contract freeze.
- **ChannelContract.md:** packet layouts, field formats, versions, adapters, the switch procedure and the fiscal.ai conversion map.
- **BUILD_AND_OPERATIONS.md:** build procedures (catalog, facts, old-Guidance retirement), the running-layer plan, the experiment program and the mechanics of the approved designs; their rules are in the topics and their hazards in the ⚠ lines. Also left out: the reviewer counts in recovery (two independent reviewers, a third for first-catalog links), how the go-live test was run (at least two independent producers, graders separate from them, one blind re-grade) and its exact score floors (0.634 for name plus direction, 72% agreement between producers), the tagged-data proof bars and industry-by-industry rollout, and how a stored link is looked up across taxonomy years.
- **Archived originals:** old wording that was later replaced; their reasons, definitions and examples became *why* lines.
- **Steps 1–14:** procedures, gates, tests and model runs; their meaning clarifications are in 3.42, 6.11 and 8.13.
- **September design study:** test runs, models, hashes, commits, run history and process orders (start and stop); its lessons are ⚠ lines, the naming proposal is the ⚠ line after 4.6, and the tax case is an example in 3.34.
- **Experiment plan and work order:** procedures, budgets, fixtures and file lists; their lessons are ⚠ lines and 8.18.
- **Older documents** (Consolidation, DriverOntology, Drivers, DriverContext, evolution, WIP locator, Fiscal and NAME-13 notes): superseded wording; reasons used only where the newer files were silent.

### C4. Notes

**Where this file came from:** recovered on 2026-09-26 from the old design files at Git commit `9618c78` (plus uncommitted edits to `FINAL_DESIGN.md` and `STATUS_AND_HISTORY.md`). The old files are unchanged and stay as history.

**Source abbreviations:** `FD` = `FINAL_DESIGN.md` · `Steps` = owner rulings in `LeftOverSteps/Steps.md` (Aug 2026) · `ST` = `STATUS_AND_HISTORY.md` · `CC` = `ChannelContract.md` · `BUILD` = `BUILD_AND_OPERATIONS.md` · `A-02` etc. = archived original files · `CR` = `archive/ConceptualRequirements.md` · `DS` = the September 2026 design study · `step N` = the work order `LeftOverSteps/stepN.md` · `owner <date>` = an owner ruling recorded in these files · `Plan`, `WorkOrder` = the experiment plan and work order · `CONSOLIDATION` = the July consolidation audit · `WIP Locator` = the source-locator design notes · `FinalPlan` = the source-linked locator plan · `Consolidation notes` = the older `Consolidation/` topic notes · `project CLAUDE.md` = the project's standing instructions. IDs like `NAME-01` are the old rule numbers.

**Which source wins when they disagree:** later owner rulings in `Steps.md`; then `FINAL_DESIGN.md` for meaning; then the channel contract, the build file and the three documents step 9 makes binding (the two source-locator designs and the Fiscal review plan). Archived files are evidence only. <sub>ST; step 9; FD</sub>

**Unapproved proposals (not decisions):** a Bayes-style learner; a "Driver Genesis" restructure; a news-channel filter design; a reasoning-trace layer with its 10 questions; a read-time "change scanner" (OD-5, only ever recommended). <sub>ST §2; Steps; FD §10</sub>

**Reviews (2026-09-26).** Codex, two Claude sessions and a checking agent listed about 130 points across two rounds; each was checked at source.
- **Rejected, with the reason:** a separate context file (one-file rule) · a status row for every decision (the paralysis trap) · a cheapest-model-first policy as binding (overridden in August for the build steps; see the ⚠ line in §8) · "guidance reissued after a withdrawal" as an open question (an archived issues list called it undefined, but read rule 4.4 now answers it: `unknown`, because the earlier value is a withdrawal with no number) · limiting link reuse by taxonomy year (storage detail) · narrowing 8.12 (an owner rule already requires separate approval for pay-per-use services) · another authority for 3.50 (see the note under that rule).
- **Already covered:** the tax case, "frozen", the surprise wording, source ranking, the ten value fields, the fuel, tax, Darden and Best Buy distinctions, industry as of the viewed date (7.11), and the September naming idea (the ⚠ line after 4.6).

**Version 1.1 (2026-09-26):** reorganized around your design questions, following suggestions from Codex and Claude: a Start-here page, topics ordered by design question, one home for each rule, tables for the densest rules, the lessons moved beside the rules they explain, uncertainty labelled where it occurs, and the sources moved into this part. No rule was removed: C1 maps every rule to its old number and sources. The old one-page summary and "In short" boxes were replaced by Start here. The old lesson "about 57% of facts have no XBRL member link" is now part of the reason in 6.13. Two small fixes after Codex's final read (2026-09-26): the basis-point rule (3.50) is flagged as a chosen reading, and the go-live bar (8.17) keeps only the pass bar; how that test was run moved to C3. Six more after a second Claude session's read: the worked example now uses Best Buy's real quote and its true source (the call transcript); the note on reissued guidance is corrected; and four one-line rules were added (a stated zero is a value, 3.48; an unknown source type is held, in the fields table; "rejected" beats "held", 8.14; retiring old Guidance keeps a restorable copy, 8.11). Final pass after Codex's last read: the tagged-data appendix (A1) now states who wins a text-versus-tagged conflict, how repeated tagged values are handled, and the rules for periods and displayed direction; 7.4, 4.4, 3.21 and 2.7 regained exact wording from the rulebook; and an unknown source type now fails closed.

**Read only as clues:** in the final review, Codex and a Claude session also read the old code, harnesses and tests; every rule kept from that was traced back to a design source. Prompts, experiment runs, the Codex mailbox and Notion were not used as sources. Completeness is claimed only for the sources read: in full, `FINAL_DESIGN.md`, the owner rulings in `Steps.md`, `ChannelContract.md` and `STATUS_AND_HISTORY.md` §2–§4 and §7; for reasons and definitions, the archived originals, `BUILD_AND_OPERATIONS.md` §7, §8, §10 and §11, steps 1–14, the September design study's handover, checkpoint, naming and record-meaning notes, and `ConceptualRequirements.md`; skimmed, the experiment plan and work order, `NewsChannel.md`, `ReasoningTraceQuestions.md`, older notes and the source-locator and Fiscal plans; plus the references followed.

**Parking list (after version 1.1):** none yet. Only a rule proven wrong or a decision proven missing reopens the file.

</details>
