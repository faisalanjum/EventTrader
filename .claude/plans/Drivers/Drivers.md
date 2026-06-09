
1. <Driver>:       can be considered a class (OOP) while a 
   <DriverUpdate>: can be considered an instance of that class

2. <Driver>: 
  Naming CORE RULE: Name a driver as specific as the evidence allows; never invent a broad name. 
  Broadness is not stored as a category. It emerges later from how widely the same exact Driver is used. Names are pure noun variables (driver_state / stock_impact / magnitude live in other fields).

  <LLM coins the specific NAME only — it never picks a company/shared/macro tier.>

  No Driver aliases. Raw wording belongs on the DriverUpdate quote/evidence, not on the Driver node.
  
  Examples of broadness emerging from usage:

  1. Mostly one company: iphone_china_sales, aws_revenue, azure_revenue, ozempic_sales, model_3_deliveries

  2. Shared across several companies: same_store_sales, ai_capex, net_interest_margin, revenue_passenger_miles, net_revenue_retention, oil_price, steel_price, lumber_price, freight_rate, copper_price

  3. Market-wide: fed_rate, yield_curve, credit_spread, usd_index, inflation

 <Driver links> to XBRL concept, dimension/Member and guidance (when possible)

 <Driver creation process>: Make exact Driver names specific, reusable, and consistent according to @DriverOntology.md rules
 
 1. At the onset, use claude workflow to create a source-grounded <PotentialDriver> menu for each company separately (spawn a subagent per company or even multiple subagents) keeping @DriverOntology.md rules. In this run, the LLM is not analyzing price impact. It is creating specific candidate Driver names from real source material. Seed sources are company-reported metrics, filings, and transcripts; no news. A Driver is used only when an llm_producer creates a <DriverUpdate> and says that Driver is the true driver for that specific event.
 
 2. Propose-first reuse (G1 — before CREATE). The producer FIRST coins its own exact, source-grounded name from the event evidence (catalog NOT yet shown, so it is not anchored into a near-match). THEN show it the nearest existing names — sorted same-company → same-industry → same-sector → embedding-similar — and REUSE only if EXACT same meaning; otherwise keep its new name (same format), which then goes to G2. Embeddings suggest; they never decide equality. (Blind/parallel build is for the calibration TEST only.)
 
 3. Independent admission gate (G2 — before a new name enters the ONE shared catalog). A DIFFERENT model (not the producer that coined it) rules each new name: reuse / admit / rewrite (wording only) / skip. Fail-closed: exact-same meaning only · choose a canonical + propose reversible SAME_AS links (never delete, merge, or overwrite) · err specific. For any proposed SAME_AS, reuse, or rewrite, first verify all three are true: same object or metric; same scope; same mechanism. If any one is false or unclear, do not SAME_AS, reuse, or rewrite. Keep the names separate, admit separately, or skip. A rewrite may only change wording; it must not change the underlying driver. Judge from each name's evidence, not the bare string. Do NOT classify "fundamental vs news/trading" — that is a producer concern, not a catalog one; a valid reusable driver is admitted (news/macro drivers are coined LIVE by the news producer). (G2 also runs in LIVE production for every new name, not just the seed build; most live events REUSE via G1 so it fires rarely — exact runtime mechanic sync/async = TBD.)

 4. After any batch menu build, run a reconcile pass: surface exact-meaning duplicates, choose a canonical name, and propose reversible SAME_AS links; do not merge or delete nodes. Then an independent **Refute** merge-skeptic tries to break each proposed SAME_AS link, each rewrite, and each D5 same-name SAME union (`HierarchicalCatalogPlan.md`) from the evidence (default = keep separate); refuted SAME_AS are dropped, refuted rewrites are parked in `unresolved_rewrites` (not applied, not lost). Finally a deterministic validator (`validate_catalog.py`, zero judgment) HARD-FAILS any structural break before the catalog ships.

PotentialDriver menu = allowed candidates
Driver = only created/used when tied to a real DriverUpdate

3. <DriverUpdate>: properties:
   a. driver_state: what happened to the driver itself
   b. stock_impact: effect on this company's stock (long / short)
   c. magnitude (note: different from the actual stock move)
   d. llm_producer: earnings-learner or news-driver
   e. confidence: 0-100, how confident the LLM is that this caused the specific change
   f. quote: verbatim quote
   g. company (links to): the company affected by this DriverUpdate
   h. event (links to): news, 10-k, 8-k, transcript etc
   note: the actual stock return lives on the linked event, not on the Driver or DriverUpdate.

Locked rule: exact duplicates get a reversible SAME_AS link; both specific nodes survive. Related-but-not-same names are skipped for now.


Plus 2 more easy safety habits:
- If the text is vague → skip it (don't invent a driver).
- Never show the AI a name or number from the future.

# rules for driver menu creation is the next correct step to fail close this entire design

# Experiment:
   to ensure the initial driver menu creation is flawless and in line with our requirements.

   - select a sector and inside it list all industries and inside it list all companies in our neo4j database. 

   1. For each company:

      a. start by looking at company-reported operating and financial metrics. Fiscal.ai is one current source for finding those metrics. Fiscal.ai KPI names are only raw suggestions; every candidate must be rewritten into @DriverOntology.md standard `driver_name` before entering the PotentialDriver menu.

	      b. Source = **ALL non-news company sources** (every 8-K/10-K/10-Q + transcript + fiscal.ai KPIs). **`>2% daily_stock` is only a high-signal FLAG on events, NOT a filter** — nothing is excluded for moving less. (News/macro drivers accrete LIVE in production via reuse-or-create + G2 — they are NOT part of the seed build; there is no separate news build.)

      c. now using nomenclature rules from @DriverOntology.md rules, spawn multiple subagents using say a claude workflow setup to create a list of specific source-grounded driver names - note we are NOT ascertaining if this was a true driver for a specific event or not. We are only creating plausible candidate names from real source material.

      d. Catalog record format is locked (ONE record per distinct driver_name):
         - driver_name · canonical_name (= itself until a reconcile roll-up)
         - companies (distinct, derived from evidence_refs)
         - evidence_refs: [ { company, source_type, source_id, date, quote } ]
             source_id = the Neo4j event id (or "fiscal_ai:<ticker>:<metric>" for a KPI) → date/company/return derive from it
         - optional_links: { xbrl_concept, xbrl_member, guidance_ref }  (optional, when a real anchor exists)

      e. IMPORTANT: Understand exactly how Guidance Extraction pipeline works out how to link each Guidance or GuidanceUpdate to associated XBRL Concepts and XBRL Members/Dimensions and use the same methodology to link above curated list of Driver names to it when available. XBRL/member/guidance links are optional when obvious and never forced.

   2. Once you have done for all companies inside a sector:
      
      a. For each Industry, pick all Drivers for each company inside that industry: and see 
         1. if there are exact duplicates that mean the same thing and surface those to me for reversible SAME_AS linking.
         2. Any drivers that apply to more than 1 company inside that industry

	      - This will tell us if this is the correct approach or not. As well this process will also provide us how to change any nomenclature and other rules for a llm_producer to follow for REUSE. Any rule change must be a general principle, not sector-specific examples (examples overfit).

	      First menu pass checks:
	      - no broad/category names
	      - no affected company ticker/legal name in driver_name
	      - no state, stock impact, date, source, or magnitude in driver_name
	      - exact duplicate meanings surfaced for reversible SAME_AS review
	      - same Driver name appears across companies where the same reusable cause exists

      b. Then do same as above for all names across all industries inside this sector. This review is only for exact duplicate meanings, not broad grouping.


# Honesty gate — run AFTER menu creation

A tidy menu alone does not prove the approach. Prior tests had clean-looking reuse metrics, but v2 still failed peer themes when different ideas collapsed into `revenue_demand`.

1. Runtime reuse test
   Freeze the company menu. Feed the LLM fresh event text that was not used to build the menu.
   It must choose one:
   - REUSE an existing Driver
   - CREATE a new Driver
   - SKIP because the text is vague or has no reusable driver

   Write the expected answer (reuse which / create / skip) for each test event before running.
   Only show names/data dated at or before the event. No future leakage.
   Visibility rule: a driver's visible_from = its earliest non-empty evidence date (evidence_refs.date); a KPI-only record (no dated evidence) is EXCLUDED from the PIT-filtered catalog until it gains dated evidence (fail-close).

2. Hard cross-theme test pack
   Include the old failure types: restaurant traffic vs pricing, travel demand, solar policy, tariffs, rates, oil/fuel.

   Write the answer key before running.

   MUST stay separate:
   - aws_revenue vs aws_capex
   - solar_demand vs solar_tax_credit
   - restaurant_traffic vs travel_bookings

   MAY SAME_AS only if exact same meaning in context:
   - guest_count vs customer_transactions

   Related-but-not-same names must not be linked.

3. Independent grading
   A different model, plus optional human spot-checks, grades against the pre-written answer key.
   Set the pass bar before the run.
   Grade once. No re-tuning to pass.

PASS = source-grounded menu exists, fresh-event reuse works, hard themes stay separate, exact duplicates are linked only when truly identical, AND the same Driver was reused across companies where expected (sharing actually emerged — not everything fragmented).
