# Driver Workflow

> ⚠️ Living checklist: tick [x] when done · owner approves every other edit · fewest words · max 2 levels, no drop-downs.

**Goal:** automatically signal buy, sell or no trade for a company as soon as relevant new information arrives. Paper trading for now.

**How:** keep each company's history current automatically by recording DriverUpdates under their Drivers from internal sources and external research. Link two updates when the same source says one drove or offset the other (CAUSED_BY, OFFSET_BY). Link a daily price move to an update when evidence supports that explanation (EXPLAINED_BY). **Every update and every link is made automatically, with no human in the loop.** [Driver rules](../DRIVER_RULES.md) · [Price-move explanations](../DRIVER_Predict_Explain_Learn/References/EXPLAINED_BY.md)

**Replay:** build history quarter by quarter. Record the updates the Predictor proposes using only information available at prediction time. After the Learner sees the actual price move, compare its findings with the Predictor's. Record any DriverUpdate the Predictor missed, including one from a later disclosure, and any new price-move explanation of an existing update.

**Paper-trading test:** on new events, record every decision, including no trade, before the outcome is known. Judge performance by the price move that follows.

## Rough Stages

- [ ] 1. **Drivers:** ([DRIVER_RULES.md](../DRIVER_RULES.md)) turn every *source into Drivers and DriverUpdates.
- [ ] 2. **Explanations:** a workflow links each price move to the Driver updates behind it ([EXPLAINED_BY](../DRIVER_Predict_Explain_Learn/References/EXPLAINED_BY.md)).
- [ ] 3. **Predictions and reviews.** See [Predictor and Learner rules](../DRIVER_Predict_Explain_Learn/References/DRIVER_LearnerPredictor.md).

## Workflow

### Initial Context

1. **FiscalAI** KPIs: for all of history in our db (for all *source one at a time):
   1.1. **Find this KPI/s** in all sources starting with SEC filings - later optimize this in most cost effective and reliable manner
   1.2. **Assign driverType**: A simple prompt which seperates out which of the 6 drivertype this fact belongs to
   1.3. Run 1/6 driverUpdate workflow


### for #2 & #3 below: "Replay for each Quarter": Starting from first quarter available

2. **Sealed bets using Predictor workflow** 
   2.1. Convert this workflow (check the latest one used) to also include driverUpdate and other recent changes - to be discussed
   2.2. **create driverUpdates**: Create new driverUpdates (as well as trigger historical updates (to be optimized) for this newly found facts) based on reason this workflow found without looking at actual returns or outside reasoning yet.

3. **Learner workflow**
   3.1. Convert this workflow (check the latest one used) to also include driverUpdate and other recent changes - to be discussed
   3.2. Compare with reality using learner workflow above after transcripts or other news available (just before next quarter except for once live in which case only wait for transcipts) 
   3.3. Also make use of perplexity, distilla and web search API to deeply understand the actual reason of price change
   3.4. **forward & backward looking**: In addition to why a stock moved, we also need to understand the thesis using transcripts, perplexity, our own workflow etc to understand what matters for a company & then create driverUpdates (keeping in mind both backward looking corrections we make after learner runs as well as forward looking which needs to be understood during both predictor and learner workflows)
   3.5. Check if more connextions b/w driver updates are possible or lead to more driver/driverUpdates creation as well as linking possible - see Driver_Rules.md - for types of links which may be different than the ones for Explained_By

4. **In between quarters**: 
   4.1. Investigate [qualifying moves](../DRIVER_Predict_Explain_Learn/References/DRIVER_LearnerPredictor.md#qualifying-move) between quarterly updates.
   4.2. Find reason from in house news etc as well as external sources if not found internally (perplexity/distilla/web etc) and create driverUpdates & ExplainedBy
   4.3. **live triggers** Create triggers (primarily for news) once in production to detect driverUpdates with high scores for each company and trigger a new predictor check for say freshness (has this already been priced in), materiality (based on company context as well as if previously this led to price change) and so on and trigger buy/sell/none signals - also once trade is done or after horizon period - log results and update score driver.

5. **Context graph and Driver histories.** See [Predictor and Learner rules](../DRIVER_Predict_Explain_Learn/References/DRIVER_LearnerPredictor.md).

6. **Explained_By**: fill these details as well as other important driverUpdates including reupdating previous driverUpdates with new conditions (more context found)

### 6 driverUpdate workflow: `metric`, `guidance`, `surprise`, `action_event`, `expectation`, `others?`

Across three 10-Ks with 50 drivers each, adding Flash to full Decider and cached Sol kept all 126 checked facts for 67% lower API fees. [Tested workflow](DriverUpdateWorkflow.md)

1. Seperate prompt for running each driverUpdate seperately in a checklist workflow form & seperate for each *source if possible.
2. Also seperate out basic rules in ([DRIVER_RULES.md](../DRIVER_RULES.md)) versus say checkers versus other processes so as to ensure every item has a home and that everything in these rules is covered. 

### Previous Guidance & Guidance update routine
1. All guidance needs to be updated (prior - to be decieded when) to each company quarterly results or important events using all official sources including transcripts, filings and maybe news. 
2. First deeply understand the previous guidance/guidanceUpdate system and borrow ideas that apply. 
3. for old triggered automatically and for new updated
4. Also include consensus every quarter

### Other considerations 
1. A way to trigger all known driverUpdates (Import with high driverscores and /or using Explained_By)
2. Also make extensive use of Offset by/ linkedBy and how and when to do linking both between driverUpdates and in ExplainedBy
3. Using Perplexity & Distilla & web search for each comapny we could also:
   3.1. ask what drivers or important things have led to a change in comapny history as well as what matters to understand the context of this company and update driverUpdates
   3.2. Also have our internal workflows look through all depends on offset by and explained by and test each driver?
   3.3. add anything thats missing? 
4. A curator agent that runs in the background on a candence and can rectify or do any other tasks that do not fit in neatly into any of the above tasks? Lets say once a day etc? 


### **driver scoring system** 
IMPORTANT: None of the below steps have been reasoned or thought through and have been put here only to borrow some ideas:
every event becomes a sealed bet, and the bets grade the Drivers.
 
A sealed bet is a prediction written before the price move is known.
 
event → facts (driver updates)
      → bot writes a bet first: "up/down, how much, because of updates A and B"
      → price moves → bet is graded
      → the grade joins the track record of Drivers A and B
 
Why this one:
 
- It trains on your one goal. Extraction quality and graph size are only stand-ins for "did we call the move".
- It settles noise versus never-miss with evidence. Drivers that never move anything sink in rank, but are never deleted. A big move nobody bet on is a miss, and triggers a deeper read there.
- "I drove this change" becomes real, honestly. One event has many updates but one price move, so a single update can't know its share. Over many events, its track record can.
- Cross-reading comes free. Driver names are shared across companies, so track records pool by sector and market. A thinly covered company borrows its sector's record.
- Your context graph gets a truth signal. This is my one pushback: reasoning notes with no grade are stored opinions, and future sessions would inherit their mistakes. Attach every note to a graded bet.
 
Limits:
 
- AI may remember old outcomes. So history should build track records by plain arithmetic (fact × price move, no AI judgment). Only new events prove skill.
- Today's Learner sees the actual return. It can write the after-notes, never the bets.
- Sharp bets need expectations (analyst consensus) switched back on.
- Few events per company. Lean on the sector pool.
 
It mostly reuses what exists: the predictor, the Learner, the "explained by" link in your rules, and the price data.
 
Where to start: one thin end-to-end loop on about 30 companies, press releases and calls only. Build label-and-cut only as far as that loop needs.



**source**: 
   1. SEC filings
   2. Transcripts
   3. News
   4. FiscalAI KPIs
   5. Distilla
   6. Outside research including perplexity finance & web
