> **⚠️ FORENSIC / SCRATCH MATERIAL — NOT A SINGLE CANONICAL LIST** (added 2026-05-27)
>
> This file contains FOUR overlapping risk taxonomies drafted by different bots/passes (27 + 36 + 15 + 36 entries, ~409 lines total) that were never deduplicated into one canonical list. The numbering schemes (R1-R27 in Group A-E, separate R1-R36, separate R1-R15, etc.) are NOT cross-comparable.
>
> Used by `DriverOntology Prompt.md` as adversarial-case source material for the "Risk Coverage Index" acceptance test. A "100% coverage" claim against this file is mathematically ambiguous because the taxonomies overlap and have different scope rules. Treat as scratch material, not as a canonical risk register.
>
> `ConceptualRequirements.md` + `CombinedPlan.md` §9 (post-E30 / v6-6 update) map the CONCEPTUAL REQUIREMENTS (§1-§8) — i.e. a ConceptualRequirements §1-§8 coverage matrix, NOT a risk→mechanism matrix. There is NO single canonical risk→mechanism matrix; these risk taxonomies remain un-deduplicated scratch (as stated above).
>
> ---

  Group A — Name shape (mechanical)

  - R1 Case/format violation — name is not lower_snake_case ASCII (e.g. "iPhoneChinaSales", "iphone-china-sales",
  "iphone china sales").
  - R2 Non-ASCII characters — name contains Unicode, emoji, or accented letters.
  - R3 Excess underscore segments — name has 5+ tokens, usually because a state word or modifier was smuggled in (e.g.
  "iphone_china_gross_margin_decline_q3").
  - R4 State verb embedded in name — name contains a verb that belongs in driver_state (e.g. "opec_supply_cut",
  "revenue_decline").
  - R5 Stock-impact direction embedded in name — name encodes long/short or up/down language (e.g. "revenue_short",
  "iphone_drop").
  - R6 Period or date token in name — name carries quarter/year/half tokens (e.g. "q1", "fy26", "2025", "h1").
  - R7 Ticker / legal company name / person name in name — name uses a stock symbol or registered entity (e.g. "aapl",
  "apple", "tesla", "elon_musk").
  - R8 Quantitative threshold in name — name contains a magnitude or unit suffix (e.g. "2pct", "100bps", "10x").

  Group B — Name semantic quality

  - R9 Near-duplicate of existing canonical name — proposed name is a synonym or word-order variant of a Driver already
   in the registry (e.g. "china_iphone_sales" when iphone_china_sales exists).
  - R10 Over-specific / single-use scope — name is so narrow that only one company-quarter can ever match it (e.g.
  "aapl_q3_2025_china_event").
  - R11 Over-generic / vacuous — name is so broad it carries no causal information (e.g. "market_event",
  "stuff_happened").
  - R12 Subjective sentiment in name — name carries judgment vocabulary instead of a neutral causal object (e.g.
  "strong_iphone_sales", "weak_demand").
  - R13 Transient one-off framed as durable driver — name captures a non-recurring event when a durable parent concept
  exists (e.g. "ceo_resigned" instead of "ceo_transition").
  - R14 Two distinct mechanisms bundled in one name — independent causes packed into one driver that should be split
  (e.g. "tariffs_and_supply_chain").
  - R15 Anchor-order inversion — business-object follows metric in the wrong order, producing near-duplicates against
  convention (e.g. "sales_iphone_china" instead of "iphone_china_sales").

  Group C — Vocabulary consistency across drivers

  - R16 Inconsistent metric terminology — same underlying concept named differently across drivers (e.g. "sales" /
  "revenue" / "topline" used interchangeably).
  - R17 Inconsistent business-object terminology — same entity named differently across drivers (e.g. "datacenter" /
  "data_center" / "hyperscale").
  - R18 Inconsistent state-verb terminology — same motion expressed by different verbs across drivers (e.g. "declined"
  on one driver, "decreased" on another, "fell" on a third).

  Group D — Companion metadata quality

  - R19 Bad definition — definition is circular, ambiguous, contradicts the name, or exceeds one sentence (e.g. "the
  iphone_china_sales driver tracks iphone china sales").
  - R20 Wrong segment value — segment is set to specific when "Total" is correct (or vice versa), causing wrong
  member_map linkage downstream.
  - R21 allowed_states too narrow — proposed states omit obvious realistic states for this driver (e.g. a regulatory
  driver listing only "approved", missing "denied", "delayed", "withdrawn").
  - R22 allowed_states too broad — list is so long that nearly any verb would match, defeating the noun/verb
  separation.
  - R23 allowed_states are not verbs — list contains adjectives or nouns (e.g. "good", "bad", "trouble") instead of
  verbs.
  - R24 Bad aliases — proposed aliases themselves violate R1–R8 shape rules, or are so loose they could apply to many
  drivers (e.g. "revenue" as an alias of iphone_china_sales).
  - R25 base_label cannot resolve — proposed base_label doesn't match any concept family in the Concept cache,
  permanently blocking xbrl_qname auto-resolution.

  Group E — Process integrity at creation time

  - R26 Registry catalog not consulted first — LLM emits propose_new_drivers[] when a usable match already existed in
  the rendered catalog block (M1 violation).
  - R27 Internal-inconsistency within one emission — driver_name used in primary_driver / contributing_factors /
  key_drivers doesn't match the name in propose_new_drivers[] for the same intent.

  ---
  Sub-task status: risk list drafted (27 entries, 5 groups). Not approved yet, not written to file.

  What I need from you to close this sub-task:
  1. Is this comprehensive — anything missing?
  2. Is each risk clear enough that a translator-bot would produce the correct LLM rule from it?
  3. If yes to both → I'll prepare the proposed insertion (location + exact text) into Neo4jXBRLDesign.md for your
  approval before any write.


  Each risk is one atomic failure mode. A later bot drafting ontology rules should be able to translate each numbered
  risk into one rule the LLM follows.

  ─── Slug syntax (how the name looks character-by-character) ────────────────
  R1   Casing drift                     Name not entirely lowercase (e.g. iPhoneChinaSales, IPHONE_CHINA_SALES).
  R2   Wrong separator                  Spaces, hyphens, dots, or colons used instead of underscores (e.g.
  iphone-china-sales).
  R3   Non-ASCII characters              Emojis, accented letters, or non-Latin scripts embedded in the slug.
  R4   Edge underscores                 Leading or trailing underscore (_iphone_sales, iphone_sales_).
  R5   Empty or missing name             Proposal with name="" or the field absent.
  R6   Too many segments                 5+ underscore-separated segments — too narrow to be reused.

  ─── Banned content (tokens that must never appear inside the slug) ─────────
  R7   Identity tokens                   Ticker (AAPL), legal company name (apple/samsung), or person name (tim_cook)
  embedded in the slug.
  R8   Date / period tokens              Calendar, quarter, or FY tokens (q1, fy26, 2025, h1).
  R9   Numeric thresholds                Quantitative thresholds (100bps_cut, 2pct, 10x).
  R10  Stopwords                         Glue words (the, of, in, and) inside the slug.

  ─── Noun-vs-verb discipline (the slug must be a noun phrase) ───────────────
  R11  Action verb in name              Verb baked into the slug (opec_supply_cut, sales_dropped). Verb belongs in
  driver_state.
  R12  Direction word in name           Direction token in the slug (increase, decline, drop). Direction lives in the
  `direction` field.
  R13  Adjective state in name          Adjective state in the slug (rising_, weakening_). State lives in
  `driver_state`.

  ─── Variant-duplication (catalog-miss; would create split nodes) ───────────
  R14  Word-order variant                Proposing `china_iphone_sales` when registry has `iphone_china_sales` for the
  same concept.
  R15  Plural / singular variant         Proposing `iphone_china_sale` when `iphone_china_sales` already exists.
  R16  Synonym variant                   Proposing `iphone_demand` when `iphone_sales` already covers the same concept.
  R17  Abbreviation variant              Proposing `gm` when `gross_margin` exists (or vice versa).

  ─── Scope quality (the name carves an unhelpful concept) ───────────────────
  R18  Sentence-form name                Slug reads like a sentence rather than a noun (the_decline_in_sales).
  R19  Too generic name                  Bare metric (sales, margin) with no discriminator on a non-macro concept.
  R20  Multi-concept compression         One slug bundles two distinct drivers (iphone_sales_and_mac_revenue).
  R21  Missing the metric                Object named but not the metric (vision_pro alone for a Vision-Pro-sales
  driver).

  ─── Catalog reuse (LLM ignored or misused the registry) ────────────────────
  R22  Skipped exact-match reuse         New proposal despite an exact match in the registry catalog.
  R23  Skipped alias reuse               New proposal despite an existing driver's aliases[] already covering this
  phrasing.
  R24  Wrong existing driver picked      Reusing a name whose scope doesn't fit (using `iphone_total_sales` for a
  China-specific signal).

  ─── Companion fields the LLM sets alongside name ───────────────────────────
  R25  Label mismatched with name        `label` describes a different concept than `name`.
  R26  Vague definition                  One-sentence `definition` is generic or doesn't describe the specific concept
  named.
  R27  Bad base_label                    `base_label` is junk, non-financial, or contains state/direction tokens.
  R28  Malformed segment                 `segment` empty, null, "all", or contains state/direction. Must be "Total" or
  a clean dimension label.
  R29  Non-verb allowed_states           `allowed_states[]` contains adjectives, nouns, or numerics. Must be verbs
  only.
  R30  Mixed verb classes                `allowed_states[]` mixes incompatible verb classes (raised + fda_approved +
  steepened).
  R31  Malformed or duplicate aliases    `aliases[]` contains the canonical name, M3-violating slugs, or duplicates.
  R32  Aliases bridge unrelated drivers  `aliases[]` points at semantically different concepts (iphone_china_sales
  aliased to samsung_china_sales).

  ─── Emission contract (overall shape of the LLM output) ────────────────────
  R33  Unresolved driver_name            driver_name used in primary/contributing/key_drivers that is neither in
  registry NOR in propose_new_drivers[].
  R34  Direction enum violation          `direction` outside {long, short}.
  R35  State not in allowed_states       `driver_state` picked for an existing driver that isn't in that driver's
  allowed_states[].
  R36  Empty / non-SRC evidence          `evidence[]` empty or contains strings that don't follow the SRC:* catalog
  format.

  ---
  Tally + validation gate

  36 atomic risks across 8 groups. Each is one line; each translates 1:1 into one future ontology rule.


 R1   DUPLICATE_CONCEPT
       Same concept emitted under different driver_names across runs/LLMs.
       Bad: "iphone_china_sales" + "china_iphone_sales" both registered.

  R2   STATE_IN_NAME
       Verb/action word baked into driver_name instead of driver_state.
       Bad: "opec_supply_cut", "revenue_decline", "iphone_sales_drop".

  R3   QUALIFIER_IN_NAME
       Strength/direction/magnitude qualifier baked into name.
       Bad: "strong_revenue", "weak_demand", "large_capex", "2pct_eps_beat".

  R4   FORBIDDEN_TOKEN
       Ticker, legal company name, person name, date/quarter/FY token,
       or source-type prefix appears in name.
       Bad: "AAPL_sales", "apple_china_sales", "q4_revenue", "fy26_eps",
            "8k_revenue", "elon_musk_tweet".

  R5   TOO_VAGUE
       Name lacks a discriminator that distinguishes it from many unrelated
       mechanisms.
       Bad: "demand", "macro", "growth", "weakness", "execution".

  R6   TOO_NARROW
       Name is so specific it can never be reused across tickers/quarters.
       Bad: "apple_q2_2026_keynote_event" (single-use, non-reusable).

  R7   TOKEN_DISORDER
       Same concept expressed in multiple word orders → variant slugs.
       Bad: "china_iphone_sales" vs "iphone_china_sales" vs
            "sales_iphone_china" (all the same concept).

  R8   CASE_OR_PUNCT_DRIFT
       Name uses anything other than lower_snake_case ASCII.
       Bad: "iPhone-China-Sales", "iphone china sales", "iphoneChinaSales".

  R9   BAD_ALIAS
       Aliases entry points to a DIFFERENT concept, not just a spelling
       variant of the canonical name.
       Bad: aliases for "iphone_china_sales" includes "iphone_us_sales".

  R10  BAD_ALLOWED_STATE
       Proposed allowed_states entry is not a clean verb.
       Bad: allowed_states = ["large", "strong", "growth", "weakening"]
       (should be verbs like "raised", "declined", "stable").

  R11  BAD_BASE_LABEL
       Proposed base_label doesn't match a canonical financial-metric label.
       Bad: base_label="iphone_quantity" (should be "Sales" or "Revenue");
            base_label="apple_china" (not a metric at all).

  R12  VAGUE_DEFINITION
       Definition is empty, generic, or fails to disambiguate from neighbors.
       Bad: definition="a driver about sales"; definition="" (empty).

  R13  NAME_LABEL_INCONSISTENCY
       Proposed `name` ≠ slug(label).
       Bad: name="iphone_sales", label="iPhone China Sales"
       (slug of label = "iphone_china_sales" ≠ provided name).

  R14  NO_EVIDENCE_AT_REGISTRATION
       Driver proposed without any supporting evidence_refs in the same
       Driver proposed without any supporting evidence_refs in the same
       emission — driver invented in the abstract, not grounded.
       Bad: propose_new_drivers entry exists but the matching
       primary_driver/key_drivers entry has evidence=[].

  R15  SEGMENT_INCONSISTENCY
       Proposed segment conflicts with what driver_name already implies.
       Bad: name="iphone_china_sales", segment="Total"
       (name already encodes iPhone+China; segment should be "iPhone China").

  Bottom-line check

  Each risk above translates directly to one ontology rule the LLM-author prompt will enforce. Format is consistent:
  short risk ID + one-line definition + concrete bad example. A later bot reading this list can mechanically derive a
  rule per risk.


  Driver Name Creation Rules

  1. Always reuse an existing registry name or alias before proposing a new driver_name.
  2. driver_name must identify the reusable causal variable.
  3. driver_name must not describe a one-time event instance.
  4. driver_name must be a noun phrase only.
  5. Put actions, changes, and outcomes in driver_state, not driver_name.
  6. Bad: revenue_decline; good: revenue_trend + state declined.
  7. Put stock impact in direction, not driver_name.
  8. Bad: bullish_guidance; good: forward_guidance + state raised.
  9. Use lower_snake_case ASCII only.
  10. Do not include dates, quarters, fiscal years, or period labels.
  11. Do not include numeric thresholds or magnitudes.
  12. Bad: 100bps_margin_pressure; good: gross_margin + state compressed.
  13. Do not include ticker symbols.
  14. Do not include legal company names.
  15. Do not include person names.
  16. Product, brand, geography, customer, institution, regulator, and commodity names are allowed when they define the causal
     variable.
  17. Bad: apple_sales; good: iphone_sales.
  18. Bad: nvidia_capex; good: ai_capex or hyperscaler_capex.
  19. Do not include source/provenance terms.
  20. Bad: 8k_guidance, transcript_margin, benzinga_oil_news.
  21. Do not include evidence wording if it is only phrasing, not ontology.
  22. “Low single digit growth” and “growth slowed” should map to the same causal variable if they describe the same driver.
  23. Avoid broad catchalls that cannot retrieve similar cases precisely.
  24. Bad: business_update, earnings_quality, company_performance.
  25. Avoid over-specific names that will never repeat.
  26. Bad: temporary_savannah_dc_startup_costs; better: distribution_center_startup_costs.
  27. Use the most reusable level that preserves the market-moving meaning.
  28. Use a specific product/geography/customer segment only when that exposure is central to the causal variable.
  29. Good: iphone_china_sales when China iPhone demand is the actual driver.
  30. Do not create segment-specific variants when the generic metric is enough.
  31. Good: gross_margin for company-wide margin pressure.
  32. Put business object first and metric last.
  33. Good: iphone_china_sales, cloud_gross_margin, hyperscaler_capex.
  34. Keep standard macro names in their familiar form.
  35. Good: oil_supply, fed_rate, yield_curve, usd_index, credit_spread.
  36. Use trend when the driver is movement of a metric rather than the metric level.
  37. Good: revenue_trend, demand_trend, inventory_trend.
  38. Use concrete financial metric names when the line item itself is the driver.
  39. Good: revenue, eps, gross_margin, operating_margin, free_cash_flow.
  40. Do not encode beat, miss, raised, lowered, cut, or accelerated in driver_name.
  41. Good: eps + state beat; forward_guidance + state lowered.
  42. Use aliases for alternate word order or synonyms.
  43. Bad duplicate: china_iphone_sales; good alias of iphone_china_sales.
  44. Do not force related but different drivers into one name.
  45. iphone_china_sales and galaxy_china_sales can be separate drivers.
  46. Do not create peer/company-specific names unless the product or exposure itself is the causal variable.
  47. Bad: aapl_gross_margin; good: gross_margin.
  48. Sentiment/tone drivers must name the variable, not the polarity.
  49. Bad: positive_management_tone; good: management_tone + state improved.
  50. Valuation drivers must name the valuation variable, not the stock result.
  51. Bad: multiple_expansion; good: valuation_multiple + state expanded.
  52. Regulatory/policy drivers should name the policy variable, not the ruling outcome.
  53. Good: export_restriction, fda_approval, tariff_policy.
  54. If no existing name fits, propose a new reusable driver with name, label, definition, allowed_states, and aliases.
  55. Reject any proposed driver_name that cannot stand alone as a reusable causal variable.

• Risks The Driver-Name Ontology Must Prevent

  1. Duplicate synonym names: Same driver gets multiple names, e.g. china_iphone_sales and iphone_china_sales.
  2. Word-order drift: Same idea changes order across runs; the ontology must force one preferred order.
  3. Too-generic names: Names like sales, demand, macro, weakness are too broad to retrieve useful prior reports.
  4. Too-specific names: Names like iphone_china_q2_2026_sales_drop include temporary facts and will not generalize.
  5. State inside name: Names must not include verbs/states like cut, drop, miss, beat, raised, decline.
  6. Direction inside name: Names must not include stock-impact words like bullish, bearish, positive, negative, upside.
  7. Time inside name: Names must not include dates, quarters, fiscal years, or one-time timing tokens.
  8. Ticker inside name: Names must not include aapl, nvda, tsla, or any stock ticker.
  9. Company-name inside name: Names must not include legal company names like apple, nvidia, tesla.
  10. Person-name inside name: Names must not include executives, analysts, founders, or politicians.
  11. Source-type inside name: Names must not include 8k, transcript, 10q, news, report, or filing.
  12. Evidence text copied as name: Names must not copy raw headline or quote phrasing.
  13. Multiple drivers in one name: Names like revenue_margin_inventory mix separate causal objects.
  14. Effect mistaken for driver: Names like stock_selloff, price_reaction, market_disappointment describe outcome, not cause.
  15. Metric-only driver names: Names like revenue or eps are often too bare; use causal form like revenue_trend, eps_surprise,
     or revenue_guidance.
  16. Guidance metric confused with driver: gross_margin is a metric; gross_margin_guidance or gross_margin_pressure is a
     driver only if that mechanism moved the stock.
  17. Segment missing when needed: If the cause is segment-specific, name it, e.g. iphone_china_sales, not just sales.
  18. Segment overused when not needed: Do not add product/geography if the source supports only company-wide effect.
  19. Category names as drivers: Names like macro, sector, sentiment, positioning are buckets, not drivers.
  20. Vague causal nouns: Names like headwind, tailwind, concerns, uncertainty do not identify the actual cause.
  21. Temporary conditions in name: Do not include one-off assumptions like excluding_fx_this_quarter or holiday_shift.
  22. Numeric thresholds in name: Names must not include 100bps, 2pct, 10x, or any numeric magnitude.
  23. Unit words in name: Names must not encode units like usd, bps, percent, unless part of a standard concept.
  24. Provider/raw-KPI leakage: Fiscal.ai or vendor labels must not become driver names without canonical cleanup.
  25. XBRL QName leakage: Names must not use raw accounting tags like us_gaap_revenues.
  26. Non-causal product names: Product or brand names are allowed only when tied to a causal metric, e.g. iphone_china_sales,
     not just iphone.
  27. Institution-only names: Names like fed, fda, opec are too vague unless tied to mechanism, e.g. fed_rate, fda_approval,
     opec_supply.
  28. Macro variable ambiguity: Names like oil are unclear; use the actual variable, e.g. oil_price or oil_supply.
  29. Plural/singular drift: Avoid both sale and sales, tariff and tariffs; one canonical form must win.
  30. Formatting drift: Names must be lowercase ASCII snake_case only.
  31. Hidden state nouns: Avoid nouns that smuggle state, e.g. collapse, surge, recovery, unless explicitly approved as stable
     causal objects.
  32. One-off event names: Names must describe reusable mechanisms, not a single event headline.
  33. Peer-retrieval pollution: Names must not be so broad that unrelated peer reports match.
  34. Own-report retrieval failure: Names must not be so narrow that the same company’s future similar event fails to match.
  35. No-evidence proposals: A new driver name must not be created unless the current event has evidence for that causal object.


• No-Human-Curation Risks For Driver Naming

  > **NOTE (judge-domain, NOT a code gap):** Three semantic-discrimination risks in this list —
  > (11) mechanism-collision (oil_price vs oil_supply), (20) wrong-discriminator (geography when
  > the cause is customer-type), and (32) alias-undermatch (obvious synonyms left unmapped) — are
  > NOT covered by the deterministic code (V1-V14 / canonicalize) BY DESIGN. Per the LLM-vs-code
  > boundary, they are **judge-domain**: handled by the Pattern B isolated judge (scope/reuse) +
  > the embedding near-dup trigger + the reconciliation job. Declared judge-domain, not a code gap.

  1. Duplicate-name risk
     Same real driver gets multiple names, e.g. iphone_china_sales vs china_iphone_sales.
  2. Generic-name risk
     Name is too broad to retrieve useful history, e.g. demand, sales, margin, guidance.
  3. Over-specific-name risk
     Name includes one-event details, e.g. aapl_q2_2026_iphone_sales.
  4. Ticker/company-name risk
     Name includes ticker or company name, e.g. aapl_iphone_sales, making reuse harder.
  5. Direction-in-name risk
     Name includes up/down wording, e.g. weak_china_sales, margin_expansion.
  6. Magnitude-in-name risk
     Name includes size, e.g. large_guidance_cut, double_digit_decline.
  7. Date/time-in-name risk
     Name includes quarter/year/event timing, e.g. q3_margin, 2026_tariff.
  8. Stock-verdict-in-name risk
     Name includes market judgment, e.g. bullish_guidance, bearish_margin.
  9. State-in-name risk
     Name embeds what happened instead of leaving it to driver_state, e.g. sales_decline.
  10. Mechanism-mixing risk
     One name combines multiple causes, e.g. iphone_sales_margin, revenue_cost_pressure.
  11. Mechanism-collision risk
     One name groups different causal mechanisms, e.g. oil_price vs oil_supply.
  12. Vague-interpretation risk
     Name describes interpretation, not cause, e.g. expectations_reset, confidence_loss.
  13. Metaphor risk
     Name uses non-machine terms, e.g. kitchen_sink, sell_the_news, headwind.
  14. Synonym-drift risk
     LLMs use different words for same thing, e.g. sales, revenue, turnover.
  15. Ordering-drift risk
     Same dimensions appear in different order, e.g. iphone_china_sales vs china_iphone_sales.
  16. Abbreviation-drift risk
     LLMs mix short and long forms, e.g. gm vs gross_margin, fcf vs free_cash_flow.
  17. Singular/plural risk
     Tiny wording differences create duplicate names, e.g. order vs orders.
  18. Unsupported-product risk
     Name adds product/segment detail not directly supported by evidence.
  19. Missing-discriminator risk
     Name lacks the qualifier needed to make it specific, e.g. inventory instead of china_inventory.
  20. Wrong-discriminator risk
     Name uses the wrong qualifier, e.g. geography when the real cause is customer type.
  21. Too-narrow-peer risk
     Name is so specific that similar peer situations cannot match.
  22. Too-broad-peer risk
     Name is so broad that unrelated peer situations match.
  23. Source-in-name risk
     Name includes where it came from, e.g. transcript_margin, 8k_guidance.
  24. Provider-label risk
     Raw external labels become canonical names without passing naming rules.
  25. Event-id-in-name risk
     Name includes event/report IDs instead of storing them as metadata.
  26. State-vocabulary risk
     LLM invents uncontrolled states, e.g. improved, got_better, moved_higher.
  27. Invalid-state-pair risk
     State does not make sense for the driver, e.g. yield_curve + beat.
  28. Direction-state-confusion risk
     LLM confuses business movement with stock impact.
  29. Evidence-free-name risk
     LLM creates a driver name without concrete supporting quote/source evidence.
  30. XBRL-linking risk
     Financial driver name is not clean enough to map to base metric/member when applicable.
  31. Alias-overmerge risk
     Alias maps two different concepts into one driver.
  32. Alias-undermatch risk
     Obvious synonyms are not mapped, causing duplicate drivers.
  33. Registry-pollution risk
     Every run creates weak one-off drivers that never repeat.
  34. Reuse-failure risk
     LLM proposes a new driver even though an existing registry driver fits.
  35. Macro-exception risk
     Standard macro variables get over-forced into artificial names instead of canonical forms like yield_curve.
  36. Company-product ambiguity risk
     Product names may be valid, but company names are not; the rule must distinguish them clearly.