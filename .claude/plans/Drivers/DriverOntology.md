# Driver Naming Ontology

## §1. Purpose

How an LLM producer reuses or creates Driver names. Two jobs, same rules:
1. Build the initial source-grounded PotentialDriver menu for a company.
2. On a fresh event, choose REUSE an existing Driver / CREATE a new one / SKIP if vague.

A Driver name is a specific, reusable cause, written as a noun. It is never a category, state, stock impact, date, source, company name, or quote wording — those live in other fields (§3).

## §2. Glossary

- **driver**: a reusable causal variable that can affect a stock price.
- **driver_name**: the lowercase identifier of one driver. Contains only ASCII letters, digits, and underscores; starts with a letter; does not end with an underscore; contains no consecutive underscores; has at least two characters.
- **one name per driver**: a Driver stores exactly one `driver_name`. Raw/source wording lives on the DriverUpdate quote/evidence; spelling / plural / acronym / word-order variants resolve to one canonical form; exact duplicate meanings found later are joined by a reversible SAME_AS link.
- **Driver catalog**: the Driver names visible for this event. Do not use names created after the event date.
- **driver_state**: what happened to the driver in this event.
- **stock_impact**: the effect on the affected company's stock; `long` or `short`.
- **evidence**: quote / source / raw wording that supports the DriverUpdate.
- **canonical form**: the one chosen spelling and word-order for a name; if a catalog name already means the same cause, reuse it.

## §3. Field Placement

`driver_name` = the reusable cause only — no state, stock impact, magnitude, source, date, or raw quote wording. Those go in `driver_state` / `stock_impact` / `evidence` (defined in §2).

## §4. Naming Rules

**Core rule.** Name as specific as the evidence allows; never coin a broad or category name. Breadth is not chosen by the LLM — it emerges only when the same exact Driver name is reused across events or companies. Before creating a new name, first try to reuse an existing catalog name at the same useful level of detail.

**R1. Reuse first.** Before proposing a new Driver, check the visible Driver catalog. If an existing Driver clearly names the same reusable cause, reuse its exact `driver_name` — do not create a new name for spelling, plural, acronym, or word-order variants (those are the same canonical form). If none clearly fits, propose a specific, source-grounded new Driver; if the source is vague, skip.

**R2. Name only the causal variable.** `driver_name` carries only the reusable causal noun the evidence is about. What happened to it is `driver_state`. The effect on the stock is `stock_impact`. The affected company is linked from DriverUpdate. The actual stock return lives on the linked event, not on Driver or DriverUpdate. Identity, period, magnitude, source, provider, company, and quote wording belong outside `driver_name`. If the evidence contains two or more independent causal variables, emit a separate driver tag per variable; never bundle them into one name.

**R3. Word order.** When coining a new name, order the parts: concrete thing or actor → needed detail → metric or mechanism. ("Thing or actor" = a product, commodity, customer group, or policy body like the Fed / OPEC.) Examples: `iphone_china_sales`, `hyperscaler_capex`, `oil_price`, `fed_rate`, `restaurant_traffic`.

**R4. Word choice.** If no Driver catalog name fits, use the most standard words available: familiar market/policy names and standard financial phrases first (R5/R6); otherwise use the source's own words for the specific thing and metric. Do not invent a synonym, headline phrase, vague phrase, or broad category.

**R5. Familiar names win.** For well-known market / policy drivers, use the familiar form, not an invented one: `fed_rate`, `yield_curve`, `oil_price`, `tariff_policy`, `fda_approval`.

**R6. Keep standard financial phrases whole.** A standard concept stays together as one name; don't split or reorder it: `gross_margin`, `free_cash_flow`, `net_interest_margin`, `same_store_sales`.

**Earnings convention.** For earnings results, name the metric plus its mechanism — `{metric}_surprise` (reported vs consensus) or `{metric}_guidance` (forward outlook): e.g. `eps_surprise`, `revenue_surprise`, `revenue_guidance`, `gross_margin_guidance`. Beat / miss / raised / lowered → `driver_state`, never the name.

**R7. Banned content.** None of the following appears inside `driver_name`. These banned meanings are rejected even if the source uses them.
- State words that describe what happened — belong in `driver_state`, not in `driver_name`. Stable nouns or standard metric phrases are allowed even if they end in `-ing` or `-ed`, such as `pricing`, `bookings`, `leasing`, `operating_margin`, `consolidated_revenue`, or `diluted_eps`.
- Direction or polarity words — belong in `stock_impact`.
- Motion or change nouns describing what happened to the variable — belong in `driver_state`, not in name.
- Any company's ticker or legal name (affected or peer), and person names. Institutions, regulators, and policy bodies are allowed when they are the cause: `fed_rate`, `opec_supply`, `fda_approval`.
- Period tokens (quarters, years, fiscal markers).
- Numeric or qualitative thresholds, magnitudes, size descriptors, or bare unit tokens (`bps`, `percent`, `usd`).
- Source-type labels (filing forms, document kinds).
- Provider or vendor labels.
- Accounting-tag prefixes (XBRL namespaces).
- Metaphors, sentiment adjectives, effect-on-stock words.
- A bare category word by itself, such as `macro`, `sector`, `demand`, or `sentiment`.
- Vague descriptors too broad to name a causal variable.
- Glue words such as `the`, `of`, `in`, `and`, `to`, or `for`.

**R8. Keep names short.** A few words. If it takes many words to be specific, it's probably two drivers — split them (R2).

**R9. Granularity.** Include only the parts the evidence directly attributes to the cause. Add product, geography, customer, segment, commodity, policy, or market detail only when the source names that detail as part of the cause; don't add details the evidence doesn't name. Company-specific product, brand, segment, or exposure names are allowed when they are the real cause; any company's ticker or legal name (affected or peer) is not. A brand/segment metric (e.g. `taco_bell_same_store_sales`) and its company-wide form (`same_store_sales`) are SEPARATE drivers — never SAME_AS them; name whichever level the evidence attributes the cause to.

**R10. New driver gate.** A new driver may be proposed only when ALL hold:
- No visible Driver catalog name clearly names the same reusable cause.
- The candidate satisfies every rule above.
- Each important noun in the name comes from the source material or an existing catalog Driver.
- The same LLM output attaches this driver to at least one causal claim with non-empty evidence.
- The driver must not be tied to a single specific instance (one event / date / filing / company-quarter / headline / source row). A reusable **class** is allowed even if it appears only once (e.g. `government_shutdown`, `goodwill_impairment`); only a name **bound to a single instance** (e.g. `q1_2026_shutdown_effect`) is rejected.
- If applying R1–R9 produces more than one unresolved candidate name, do not propose a new driver; reject as ambiguous.

## §5. Examples (illustrative only)

**State and magnitude do not enter the name.**
Evidence: "OPEC announced a 1-million-barrel-per-day supply cut."
Outcome: `driver_name = opec_supply`; `driver_state = cut`; the magnitude stays outside the name; `stock_impact` is company-specific and is not illustrated here. Demonstrates R2, R5, R7.

**Word-order variant reuses the catalog name.**
Evidence: "Apple's iPhone sales in mainland China decelerated."
The catalog contains `iphone_china_sales`. The candidate `china_iphone_sales` is in the same canonical form as the catalog name and reuses it. "Apple" does not enter the name. "Decelerated" is the state. Demonstrates R1, R3, R7.
