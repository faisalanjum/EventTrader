
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
 
 1. At the onset, use claude workflow to create a source-grounded <PotentialDriver> menu for each company separately (spawn a subagent per company or even multiple subagents) keeping @DriverOntology.md rules. In this run, the LLM is not analyzing price impact. It is creating specific candidate Driver names from real source material. Include all sources including news, reports, transcripts etc if possible. A Driver is used only when an llm_producer creates a <DriverUpdate> and says that Driver is the true driver for that specific event.
 
 2. Do post processing, going one level higher to find exact duplicate meanings. Do not delete or hard-merge Driver names. If two names have the exact same meaning, add a reversible SAME_AS link and keep both specific nodes.
 
 3. Reuse maximally & create new minimally: For LLM producers, show them already created drivers for this specific company (& may be even potential drivers in this industry) plus also provide them with a function which shows back top similar drivers (using embeddings). Embeddings only suggest possible matches; they do not decide equality. If still doesn't match, provide them rules on how to create a new Driver using same format as already created ones. 

PotentialDriver menu = allowed candidates
Driver = only created/used when tied to a real DriverUpdate

3. <DriverUpdate>: properties:
   a. driver_state: what happened to the driver itself (e.g. traffic_declined, guidance_raised, oil_price_increased)
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

      b. Then filter all its related events (such as linked news, all reports, transcripts etc) by filtering out only those events which had say >2% associated "daily_stock" return or even relative "daily_stock" return. These are high-signal source material only; they do not prove the item was the true driver.

      c. now using nomenclature rules from @DriverOntology.md rules, spawn multiple subagents using say a claude workflow setup to create a list of specific source-grounded driver names - note we are NOT ascertaining if this was a true driver for a specific event or not. We are only creating plausible candidate names from real source material.

      d. First menu output format is locked:
         - driver_name
         - evidence quote / source / date
         - source company
         - optional XBRL concept/member link when a real anchor exists
         - optional Guidance/GuidanceUpdate link when a real anchor exists

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
