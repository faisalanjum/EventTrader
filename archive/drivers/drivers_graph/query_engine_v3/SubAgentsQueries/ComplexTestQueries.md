# Complex Test Queries for Query Engine v3

## Purpose
These queries are designed to thoroughly test Query Engine v3's capability to handle complex, multi-step financial investigations through hint-guided iteration. Each query requires coordinating multiple specialists, temporal reasoning, and iterative discovery.

## Design Principles
1. **Natural Language Only**: No technical database terms or structure knowledge required
2. **Database Extraction Only**: All information must exist in the database - no modeling or external data
3. **Multi-Step Complexity**: Each query requires multiple iterations of investigation
4. **Business Context**: Written as a business analyst would ask them

---

## Super Complex Multi-Step Investigation Queries (22 Total)

### 1. Comprehensive Guidance Evolution Analysis
"Track every revenue guidance number Apple provided over the last 6 quarters including initial guidance, any mid-quarter updates, and final pre-announcement revisions. Compare each guided range to what was actually reported, calculate the percentage miss or beat for each quarter. For quarters with misses greater than 3%, identify what other metrics also missed expectations, find what management said caused the miss, determine if they blamed macro factors or company-specific issues, extract all analyst questions specifically about the miss and management's responses, and show how the stock reacted both immediately and over the following week. Finally, identify if guidance conservatism changed after any major misses."

### 2. Multi-Dimensional Earnings Surprise Forensics  
"For Tesla's last 5 earnings releases where the stock moved more than 8% in either direction, extract every single reported metric including revenue, automotive revenue, energy revenue, gross margins by segment, operating margins, free cash flow, vehicle deliveries by model, average selling prices, and regulatory credits. For each metric, find what the company had previously guided, what analysts expected based on any pre-announcements, and calculate the surprise percentage. Identify which specific metric surprise correlates most strongly with the stock movement direction and magnitude. Extract the exact quotes from the earnings call where management discussed the biggest surprise items, find all follow-up questions analysts asked about those items, and determine if management's explanation satisfied analysts based on their subsequent questions. Track if the initial after-hours movement reversed or accelerated during the next trading day."

### 3. Cross-Competitor Operating Leverage Deep Dive
"Compare operating margins, gross margins, R&D as percentage of revenue, and SG&A as percentage of revenue for Apple, Microsoft, Google, Amazon, and Meta over the last 12 quarters. Identify all quarters where three or more saw margin compression simultaneously. For those quarters, find what common factors each company cited - inflation, wage pressure, investment cycles, or competition. Determine which company showed the best operating leverage by maintaining margins despite revenue headwinds. Extract management commentary about cost control initiatives, efficiency programs, or restructuring. Identify which companies pre-announced margin pressure versus those that surprised. For companies that maintained margins better, find what specific actions they took - hiring freezes, reduced marketing, slower infrastructure investment. Finally, track which companies' stocks were most rewarded for margin resilience."

### 4. Geographic Revenue Momentum with Competitive Context
"Analyze how revenue mix has shifted across geographic regions for Apple, Samsung's reported segments, and Google's hardware division from 2022 through 2024. Show what percentage of revenue comes from Americas, Europe, Greater China, Japan, and Rest of Asia for each company. Identify which regions are growing fastest and slowest for each company. Find management commentary about market share gains or losses in specific countries. Extract any discussion about foreign exchange impacts on regional results. Identify which companies are most exposed to China and how that exposure is trending. Find any mentions of geopolitical risks or trade tensions affecting regional performance. Determine if companies gaining share in certain regions are taking it from specific competitors based on management comments or analyst questions."

### 5. Comprehensive M&A Value Creation Analysis
"For all technology sector acquisitions over $1 billion completed in 2023-2024, track the acquiring company's revenue growth rate, operating margins, debt levels, and cash position for 4 quarters before and after the acquisition. Identify what strategic rationale management provided - market expansion, technology acquisition, talent acquisition, or competitive defense. Find what synergy targets were mentioned if any. Track if acquired company revenues are reported separately or integrated. Identify which acquisitions were immediately accretive versus those requiring integration time. Find any goodwill impairments or restructuring charges related to acquisitions. Extract analyst questions about acquisition performance and management responses. Determine which acquisitions the market viewed favorably based on stock performance from announcement through one year later."

### 6. Supply Chain Resilience Stress Test
"For all semiconductor, automotive, and consumer electronics companies, identify every mention of supply chain challenges from 2022 through 2024. Track how inventory levels, days sales outstanding, and days payable outstanding evolved during this period. Find which companies built buffer inventory versus those maintaining just-in-time. Identify which companies vertically integrated or reshored production. Extract all management discussion about supplier relationships, dual-sourcing strategies, and supply chain investments. Find which companies reported supply-driven revenue impacts versus those that navigated successfully. Track gross margin impacts from expedited shipping, spot purchases, or alternative suppliers. Identify early warning signals companies provided about supply issues and how accurate those warnings proved. Determine which supply chain strategies proved most resilient based on sustained revenue growth and margin stability."

### 7. Executive Change Performance Attribution
"For all CEO changes in the S&P 500 since 2023, extract the departing CEO's tenure performance including revenue CAGR, margin expansion or contraction, stock performance versus sector, and major strategic initiatives. Find the stated reason for departure - retirement, termination, health, or other opportunities. Identify whether the replacement was internal or external and their previous role. Track all performance metrics for 4 quarters before and after the transition including revenue growth, margins, cash flow, and employee turnover if disclosed. Extract the new CEO's first earnings call remarks about strategic priorities and what they plan to change. Find analyst questions about leadership transition and strategy shifts. Track how long it took for the new CEO to provide updated guidance or strategic plans. Compare companies with smooth transitions versus those with rocky handoffs based on metric volatility and stock performance."

### 8. Interest Rate Sensitivity Revealed
"For all financial institutions, extract every mention of interest rate impacts, net interest margin trends, and rate sensitivity disclosures. Find what each bank reported for net interest income across the last 8 quarters as rates rose then stabilized. Identify which banks grew deposits versus those seeing outflows. Track loan growth and credit quality metrics during the rate cycle. Find management commentary about competitive deposit pricing pressures. Identify which banks successfully passed through rate increases to borrowers versus those that absorbed margin compression. Extract any disclosed sensitivity tables showing revenue impact from rate changes. Find which institutions hedged rate risk versus those that remained exposed. Track market reaction to each bank's quarterly net interest margin results and forward guidance."

### 9. Product Launch Success Patterns
"For major product launches in consumer electronics, automotive, and software sectors in 2023-2024, identify the first mention of the product in company communications. Track all pre-launch commentary about expected demand, production capacity, and market opportunity. Find when revenue from the new product first appears and at what scale. Compare management's initial expectations to actual results after 2-3 quarters. Extract all discussion about product margins versus company average. Identify which launches required guidance revisions up or down. Find analyst questions about competitive responses and market share capture. Track whether successful launches led to halo effects on other products. Determine the typical revenue ramp timeline from launch to material contribution."

### 10. Regulatory Impact Cascade
"For all banks and insurance companies, track every mention of Basel III, CECL, or other regulatory changes from 2023-2024. Find what capital ratios, reserve levels, and other regulatory metrics each company reports. Identify which institutions needed to raise capital or change business mix for compliance. Extract management discussion about regulatory costs and system investments. Find which companies exited certain businesses or products due to regulatory burden. Track if regulatory compliance affected dividend or buyback capacity. Identify competitive advantages gained by companies that adapted quickly versus those struggling with compliance. Extract analyst concerns about regulatory headwinds and management responses about mitigation strategies."

### 11. Technology Investment ROI Reality Check
"For all companies mentioning 'digital transformation,' 'AI investments,' or 'technology modernization,' track their technology spending levels, capitalized software, and R&D expenses over time. Find what specific benefits management promised - cost savings, revenue growth, or customer acquisition. Identify when benefits were supposed to materialize based on initial timelines. Track if promised metrics actually improved in subsequent quarters. Extract any discussion about project delays, cost overruns, or scope changes. Find which companies achieved promised ROI versus those still investing without clear returns. Identify whether heavy tech investors outperformed or underperformed peers on revenue growth and margins."

### 12. ESG Performance and Valuation Link
"Extract all environmental, sustainability, and governance metrics that companies report, including carbon emissions, diversity statistics, board composition, and safety records. Track how these metrics evolved over the past 8 quarters. Find which companies set specific ESG targets and whether they're meeting them. Identify any ESG-related controversies, regulatory issues, or activist campaigns. Extract management discussion about ESG investments and their cost impact. Find investor questions about ESG priorities and capital allocation. Track if companies with improving ESG metrics see valuation premium changes or cost of capital benefits. Identify which ESG initiatives management claims drive business value versus those pursued for stakeholder pressure."

### 13. Pricing Power During Inflation
"For consumer goods, retail, and restaurant companies, track all mentions of pricing actions from 2022-2024. Find what percentage price increases were implemented and their timing. Identify which companies raised prices multiple times versus single adjustments. Extract volume impacts following price increases and elasticity comments. Find which companies lost market share versus those that maintained it despite higher prices. Track gross margin evolution to see if pricing offset input cost inflation. Identify which companies rolled back prices as inflation cooled versus those maintaining higher prices. Extract management commentary about competitive pricing dynamics and consumer pushback. Determine which pricing strategies proved most successful based on revenue growth and margin expansion."

### 14. Dividend Sustainability Deep Analysis
"For all dividend-paying companies, track dividend per share, payout ratios, free cash flow coverage, and debt levels over the past 12 quarters. Identify which companies raised dividends despite deteriorating coverage metrics. Find management commentary about dividend policy and commitment to progressive dividends. Extract any discussion about balancing dividends, buybacks, and growth investment. Identify companies where dividend growth outpaced earnings growth and whether this proved sustainable. Track which companies cut or suspended dividends and what triggered those decisions. Find analyst questions about dividend safety and management responses. Determine which dividend policies the market rewards based on yield premiums and volatility patterns."

### 15. Competitive Intelligence from Management Commentary
"For the top 5 companies in cloud computing, extract every mention of competitors by name or reference. Find what management says about competitive wins, losses, and market dynamics. Identify which companies claim market share gains versus those acknowledging pressure. Track if competitive commentary changes tone over time - more aggressive or defensive. Extract specific product or service areas where competition is most intense. Find what differentiators each company claims versus competitors. Identify when companies match competitor pricing or features. Track if increased competition correlates with margin pressure or slower growth. Determine which companies accurately predicted competitive threats versus those caught off-guard."

### 16. Working Capital Management Excellence
"Track days sales outstanding, days inventory outstanding, and days payable outstanding for all manufacturing and retail companies over 8 quarters. Calculate the cash conversion cycle and identify which companies improved it most. Find management discussion about working capital initiatives and targets. Extract any mention of supply chain financing, factoring, or other working capital tools. Identify which companies freed up cash through working capital improvement versus those seeing deterioration. Track if working capital changes were sustainable or temporary quarter-end management. Find which companies used freed cash for growth investment versus debt reduction. Determine which working capital strategies proved most effective across different industries."

### 17. Restructuring Program Effectiveness
"For all companies announcing restructuring programs since 2023, extract the initial cost savings targets, investment required, and implementation timeline. Track what specific actions were taken - headcount reduction, facility closures, business exits. Find what actual costs were incurred versus initial estimates. Identify when savings started flowing through to margins and at what run rate. Extract any discussion about execution challenges or timeline delays. Track if restructuring achieved promised margin improvement or just maintained margins against headwinds. Find which programs included growth investments versus pure cost cutting. Determine which restructuring approaches delivered best returns based on margin expansion and stock performance."

### 18. Currency Impact Beyond Translation
"For multinational companies, extract all foreign exchange impact disclosures including translation and transaction effects. Find which companies provide constant currency growth rates and how those compare to reported rates. Identify which companies hedge currency exposure versus those that remain exposed. Track if currency impacts are growing or shrinking as percentage of results. Extract management discussion about pricing actions to offset currency headwinds. Find which companies have natural hedges through global cost bases. Identify when currency becomes a material headwind requiring guidance revision. Determine which currency management strategies proved most effective in volatile FX environments."

### 19. Customer Concentration Risk Evolution
"For all companies disclosing customer concentration, track what percentage of revenue comes from top customers over time. Identify which companies successfully diversified versus those with increasing concentration. Find any discussion about customer contract renewals, pricing pressure, or relationship changes. Extract management commentary about customer acquisition and retention strategies. Track if losing a major customer was pre-announced or surprised the market. Identify which companies have bargaining power with concentrated customers based on pricing and term discussions. Determine optimal customer concentration levels by industry based on growth and margin profiles."

### 20. The Ultimate Multi-Factor Market Event Investigation
"For the three worst market days in 2024, identify every company that fell more than 8%. Group them by sector and industry. Find which companies had reported earnings within the prior week versus those with no recent news. Extract all company-specific news from those days. Identify which companies cited macro factors versus company issues in subsequent commentary. Track which companies recovered to prior levels within 30 days versus those that established new lower ranges. Find what management said on the next earnings call about the market event and its impact. Determine if the market correctly identified fundamental problems versus overreacting based on subsequent quarterly performance. Extract analyst questions about resilience and risk management. Finally, identify common characteristics of companies that proved most resilient versus those that remained impaired."

### 21. Complete Guidance Metric Evolution and Market Sensitivity Analysis
"For Apple, extract every single guidance metric ever provided - not just revenue but also gross margins, operating expenses, tax rates, capital expenditure, services growth, product revenue, geographic performance expectations, foreign exchange impacts, and any other forward-looking metric mentioned. Track how each guidance metric evolved over every earnings cycle from the company's first guidance to present. For each metric, identify when it first appeared in guidance, when it stopped being guided if applicable, and how the specificity changed (exact number vs range vs qualitative). Calculate the stock's reaction when each metric beats or misses its guided range. Identify which quarters saw the biggest stock moves and determine which specific guided metric's surprise drove that move. Track how the importance of different metrics changed over time - for instance, when did services growth guidance become more important than product revenue guidance for stock reaction? Find periods where beating one metric (like iPhone units) mattered most, versus when another metric (like services margin) became the key driver. Extract all analyst questions about guidance metrics to understand which ones investors focus on most each quarter. Identify if there are certain thresholds for specific metrics that trigger outsized reactions (like gross margin below 38% or services growth below 20%). Track how management's guidance philosophy evolved - did they become more or less conservative over time, did they start guiding more or fewer metrics, did they shift from specific numbers to ranges? Finally, determine which 3-5 guidance metrics currently drive the stock most based on recent quarters' reactions and analyst focus."

### 22. Company-Specific True Driver DNA Profiling
"For Apple, Microsoft, Tesla, Amazon, and Netflix, find every single event (earnings, product announcements, management changes, regulatory news, analyst actions) where the stock moved more than 3% above or below the market's daily return. For each event, extract what specific information was released, what metrics were reported if it was earnings, what was announced if it was news, and the exact magnitude of the stock's excess return. Group these events by category - earnings beats/misses, product launches, guidance changes, management commentary, competitive developments, regulatory issues, or macro sensitivity. For each company, identify which category of events consistently drives the largest stock reactions. Within earnings events, determine which specific metrics matter most - is it revenue growth, margin expansion, user metrics, unit sales, or guidance? For product announcements, identify which types move the stock - hardware launches, software updates, service expansions, or pricing changes? Track if the sensitivity to different drivers changed over time - did the company's stock become more sensitive to growth metrics and less to profitability, or vice versa? Find if there are certain thresholds that trigger outsized reactions - does missing revenue by 1% matter less than missing by 3%? Extract management commentary from earnings calls after big moves to understand if they correctly identify what drove the reaction. Look for patterns in analyst questions following large moves to see if the market's focus aligns with management's emphasis. For each company, create a sensitivity profile showing which types of news and which specific metrics within earnings drive the stock most. Compare across the five companies to identify if certain companies are more event-driven while others are more fundamentals-driven. Finally, based on all historical patterns, identify what future events or metrics are most likely to drive significant stock moves for each company."

---

## Testing Methodology

### How to Use These Queries

1. **Start Simple**: Begin with queries 1-5 to test basic multi-step capability
2. **Increase Complexity**: Move to queries 6-15 for deeper investigations
3. **Stress Test**: Use queries 16-20 for maximum complexity testing
4. **Ultimate Tests**: Use queries 21-22 for the most complex guidance and driver analysis

### Expected Specialist Coordination

Each query should trigger:
- **XBRL Specialist**: For financial metrics and facts
- **Transcript Specialist**: For management commentary and Q&A
- **News Specialist**: For events and announcements
- **Market Specialist**: For price reactions and returns

### Success Criteria

The Query Engine v3 succeeds if it can:
1. Parse the natural language without requiring technical knowledge
2. Identify which specialists to engage for each part
3. Use hints from one specialist to guide others
4. Build context iteratively across multiple passes
5. Synthesize findings into coherent answers
6. Provide appropriate confidence scores
7. Handle missing data gracefully

### Iteration Patterns

Most queries should require:
- **Iteration 1**: Initial data gathering from primary sources
- **Iteration 2**: Follow-up based on hints and gaps
- **Iteration 3**: Final details and verification
- **Iteration 4** (if needed): Deep dive on specific findings

---

## Notes

- All queries extract only existing data from the database
- No external data sources or modeling required
- Natural business language throughout
- Each query tests multiple aspects of the system
- Complexity increases through the list
- Real-world business investigation scenarios