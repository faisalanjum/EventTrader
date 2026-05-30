# Foundation

1. Same driver can be tagged to any number of events. For example:

  No.        Driver          Event
  1.         oil_price       News_id
  2.         oil_price       8-k_id

2. One event can be associated with more than one driver. For example:

  No.        Driver                   Event
  1.         china_iphone_sale        8-k_id
  2.         china_iphone_margin      8-k_id (same id)


  ## Other driver details

  Structure: 
  1. <driver_name> 
  2. <driver_direction> 
  3. <associated_event_id>


2. For <news_events>, we will exclude any events related to actual company produced events such as any reports (8-k, 10-k, 10q etc), transcript etc. 
   One simple way is to exclude all events that happened on the day of these company specific releases (& maybe +1 day).
   
   2.1. So typically news events are more Macro, sector, industry etc related but can be company-specific albeit in rare conditions.
   <driver_identification> involves starting from significant <stock_price_change> over some threshold and finding the <driver> that caused it.
   So: <stock_price_change>   ->   <driver>

   2.2. These events will eventually be made <tradeable>:

        2.2.1. <triggerable>: We will use a mix of new & IBKR Price triggers to determine the change in this variable <driver_change>:
               
               ### note: this is only one strategy but open to better ones for <driver_change> detection:
               
               2.2.1.1: constantly scan benzinga_news tags, channels, body etc for this <driver> name 
                        'may make use of a cheaper model like haiku for confirmation for example'

               2.2.1.2: once above is detected, use IBKR MCP pricing to find change in this <driver> for confirmation

               2.2.1.3: to check if we can directly use IBKR price triggers

               2.2.1.4: [PHASE 4 FUTURE SCOPE — out of Phase-1 driver-naming scope. Refined wording per v6-7 to avoid conflict with the "no runtime human curator" posture (L4):] while <driver_identification> remains an autonomous pipeline, the trade-trigger setup will use a MECHANICAL RANKING (computed code-time from objective signals: how many companies each driver impacts, historical or expected move size, signal-to-noise, win-rate) to select the most effective drivers for triggering. Engineers may inspect / adjust the ranking constants at code-time, but no runtime manual curation occurs in the driver-naming or driver-detection layer. (The original "we will curate a list manually" wording applied loosely to Phase-4 trading-trigger selection only; the autonomous driver-NAMING pipeline of Phase 1 is unaffected.) 
             
        2.2.2. <backtesting> & walk-forward: <driver_change> -> <stock_price_change>

        2.2.3. <live_trading>: Once above is validate, we check before actual trading will be if the <stock_price> has already moved before placing a bet.

        2.2.4. an automatic way of detecting <winning_rate> so only top signals are made to trade

   2.3. Typically expect news events to be caused by one clear driver (although not always) since this is more macro, sector, industry specific
   2.4. These <news_events> drivers may trigger more than one company but since each <driver> in gloabl driver list directory will include event_id, which also implies it will include the company and date_time of that event. 

3. A second set of <drivers> come from <earnings-predictor> & <earnings-learner> but few of their properties first.

  3.1. Since these are primarily extracted from 8-ks & in case of <earnings-learner> (also transcripts or others), they may typically be more than one which also means they can't be empirically proven in an automatic manner unlike <news_events> since a <stock_price> change after an earnings or transcripts release cannot be easily attributed to a single <driver> change (atleast in most cases). So they are NOT <tradeable> in an automatic sense like <news_events> above (meaning require LLM's heavy reasoning for trading signal)

  3.2. However, they can still be used for one purpose. Recall that for now we ask <earnings-predictor> to forcefully read most previous <earnings-learner> reports. Instead we can improve the accuracy of which previous report <earnings-predictor> by asking <earnings-learner> to include <driver> tags along with summary lines for each report so we can provide another level to <earnings-predictor> so it only reads related reports (from among previous learner own-reports as well as peer-reports) i.e. related to current 8-k report predictor is reading. In fact we can guide <earnings-predictor> to start by ranking this relatedness in its skill before it picks the reports it reads without ascribing a specific set of N reports it must read. I beleive <earnings-learner> already supposed to produce <primary_driver> + <contributing_factors> but we can standardize the entire process to make them more easily relatable so <earnings-predictor> has a better chance of reading more relevant report.

  3.3. CLARIFIED (resolves contradiction with §3.2 that was flagged during plan v4 review): <earnings-predictor> is a CONSUMER of <driver> tags, NOT a producer. Predictor reads driver_tags from prior <earnings-learner> reports via <prior_reports_context> for relevance ranking (per §3.2 above) and reads the global Driver registry via the bundle catalog for awareness of stock-movers (per §8.4 below) — but predictor does NOT emit drivers to the registry. <earnings-learner> is the sole Phase-1 producer; it emits <primary_driver> + <contributing_factors> drivers grounded in <8-k>, <transcript>, and other quarter sources it has access to via DataSubAgents. News (Phase 2) and fiscal.ai (Phase 3) are additional producers that come later. The earlier wording in this section ("predictor must produce drivers from 8-K, transcript...") is SUPERSEDED by this clarification.
  3.4 Also note based on one of our principles from <future_checklist>, <earnings-learner> will ask questions from <earnings-predictor> which are observable by it. So typically <earnings-learner> earlier reports will include <drivers> mostly belonging to <8-k> but occasionally also include ones coming from other events such as <transcript> etc especially if they also appear in that quarters <8-k> event. 

4. A final set of <drivers> will come from already scraped KPI's from <fiscal.ai> which don't neccessarily serve a purpose now but will include them anyhow since they focus on <10-k>, <10-q>, other reports/presentations (events not fully covered by 2 above). They also won't follow naming conventions and nomenclature standardization but thats fine for now.

5. Finally, we can think of these drivers coming from few different producers:

  5.1: <news_events>
  5.2: <earnings-learner>
  5.3: <fiscal.ai>
  5.4: <earnings-predictor> — RESOLVED per §3.3 clarification: predictor is CONSUMER ONLY, not a producer. Predictor's result.json (per Final.md §7) keeps its `key_drivers[]` field as FREE-FORM analysis prose ("short causal phrases; no controlled vocabulary/tags" per Final.md §7) — these are predictor's own thinking, NOT canonical-form drivers, NOT written to the Driver registry. So the producer set is: 5.1 news / 5.2 earnings-learner / 5.3 fiscal.ai. Predictor consumes via driver_tags on prior learner reports (§6 in Final.md / §3.2 above).
  5.5: conceptually or even as an attribute would it make sense to categorize these <drivers> into say macro/sector versus company-specific. so for example, <news_events> produces macro categories while rest company specific - not sure if it helps or can be done with 100% accuracy or serves any purpose. 


6. Bottom line of above is this:
 # We need a super standardized way of creating a global list of drivers which must be consulted each time by all of the producers above before creating a new one and if one already exists, it must reuse it. Although since <driver> list is different from <driver_change> event, any <driver_change> event must be appended using existing or newly created driver and tagged by source and event_id etc. 

 # For this we also need a super clear driver nomenclature ontology so we bring as much determinism as possible in driver name creation by any kinds of LLMs.

7. In terms of focus, we are only focusing on first creating this driver name standardization for <earnings-learner> as the Phase-1 producer (per §3.3 clarification: predictor is consumer-only, not producer) since that's the focus of Final.md. <earnings-predictor> consumes via driver_tags on prior learner reports + the bundle catalog. News (Phase 2) and fiscal.ai (Phase 3) are deferred producers. But since we require same one global list accessed by all producers when they activate, we are establishing the naming standardization now.

8. Standardization Rules:
TENSION
  8.1: Should it be more specific <driver> name so <earnings-predictor> can pick up correct own-report to read with higher accuracy?
  8.2: Or should it be more generic so <earnings-predictor> can pick up correct peer-reports with higher accuracy
  8.3: Or should it be more generic so <news_events> can be related to more companies. But thinking aloud, since <news_events> will produce <drivers> which are more macro/sector related anyway this probably doesn't hold. 
  8.4: Another purpose of creating this drivers and connecting them to events and producer sources is we can feed them in our <earnings-orchestrator> context bundle to <earnings-predictor> so its typically aware what moves the stock prices. 
  8.5 Bottom line is this global super standardized <driver> list can become a backbone on which we can build upon but first all of these tensions and purposes etc need to be ironed out in as much depth and with as much clarity as possible. 

# Driver Summary:

1. Who creates it:

  1.1: News driver: excludes if source 8-k, transcript, other reports - generic mostly macro/sector etc - basically not fundamental/non company-specific (for the most part but its fine if it happens as news driver creation is automatic). Most empirical provable so usgae is tradeable & triggerable.

  1.2: Learner: 8-k by design but must also atleast read transcript for drivers (and tag it seperately with transcript drivers) eve if we may only provide 8-k drivers to predictor. Its one usgae is to provide driver tags to predictor so predictor can focus on reading specific previous learner reports (both own and peer)

  1.3 fiscal.ai - I believe its mostly from 10-q, 10-k and presentations but will not be marked by event_id (to be checked - i guess only which quarter). No real usage now but good to keep for comprehensive ness and for future proofing. At some point we may start extracting these from reports in real time if it proves useful for signal detection. So since we wont have event id for this, we may require to keep fields like company & quarter for this specifically until we do our own extractions. 

  1.4 another thing to think about this if above drivers relate to guidance nomenclature or usgae (check how guidance_extraction works first in detail and the rules for its nomenclature). But even if they don't follow exact nomenclature standardization we should atleast do it for drivers first and then maybe later adopt it for guidance extraction pipeline nomenclature so they can be linked together easily. 

  1.5 Overall, a driver is anything that led to a change in stock prices - for news_events (mostly empirically proven) but for other producers, by if something did not directly or by LLM reasoning imacted prices in this event never gets promoted to becoming a driver.


# Harness Test Requirements:
  1. Fully define every component and every phase

  - Cover every single component and every single phase — each one fully defined.
  - We can still ask the builder LLM to checkpoint and report back after each phase.
  - But each step must be fully defined (complete, detailed spec), so the builder LLM can eventually build every part of the infrastructure in isolation.
  - Scope: build everything except the real ingestion work.

  2. Test with real LLMs

  - The tests must include running real LLMs — not mocks — so we can test the system thoroughly.

  3. Include the toughest tests + borrow from the planning docs

  - The test set must include the hardest possible tests, covering all the risks in:
    - .claude/plans/Drivers/DriverNameRisks.md
  - Also borrow relevant material from:
    - .claude/plans/Drivers/ConceptualRequirements.md
    - .claude/plans/Drivers/DoubtsInHTML.md
    - .claude/plans/Drivers/DriverOntology.md
    - …and any other related docs in that folder.

  4. Code quality

  The code we create must be:
  - Well organized
  - Minimalistic — but still 100% reliable and fully covering all requirements
  - Efficient
  - Isolated

  5. Easy to productionize

  - Once fully verified, it should be super easy to integrate into production.

  6. Production-matching run sequence

  - Tests must run in a defined sequence that matches how they'll run in production.
