**Yes—Perplexity could replace much of the research, monitoring and reporting work. My recommendation is to use it repeatedly, learn from the results, and build only the parts our trading process still needs.** We should let that comparison shrink our build.

I checked our code, saved company analyses, Perplexity’s current documentation, and the actual catalyst demo. These are the useful findings.

**The catalyst tracker is familiar, but the demonstration proves less than it appears to.**

I opened its embedded application and inspected the publicly served code. It contains 24 fixed example events, with categories, bullish/bearish labels, impact ratings and upcoming dates. It explicitly says “demo mode”; its source names are text labels.

That gives us useful ideas for presenting events. It does **not establish the accuracy of a working monitoring or price-explanation process**. We need real tasks to judge that. [Catalyst demo](https://www.perplexity.ai/computer/a/catalyst-tracker-eK_BhH48QkKvg_DNAGPUIw)

**Brain is more relevant to our goal than that dashboard.**

Perplexity’s Brain maintains knowledge across tasks, links entries to sources, incorporates corrections and updates stale information. Its published design describes saved sessions, distilled notes and linked knowledge pages, with checked changes recorded through Git. This is directly relevant to our aim of understanding a company without rereading everything. Brain is currently described as a research preview for Max and Enterprise Max. [Brain documentation](https://www.perplexity.ai/help-center/en/articles/19700001-what-is-brain), [published memory design](https://www.perplexity.ai/en-GB/hub/blog/ai-agent-memory)

We should test that capability before assuming we need to build its equivalent ourselves.

The recurring jobs I would use it for are:

| Job | Concrete request | What we learn or incorporate into our system |
|---|---|---|
| **Build a company’s history** | “Trace Broadcom’s AI revenue expectations and VMware developments across these quarters.” | Which sources and measures explain the company’s evolution; dated facts with evidence. |
| **Understand an earnings surprise** | “What changed versus management’s previous guidance and analysts’ expectations?” | A repeatable comparison that separates actual results, company forecasts and market expectations. |
| **Investigate unexplained moves** | “Here is this company’s move and the information we already have. Find supported explanations and competing explanations.” | How to search beyond our existing news, and when to leave a move unexplained. |
| **Find effects across companies** | “Does this customer’s spending announcement affect our suppliers or competitors? Establish the business connection.” | Evidence for connections that a company-tagged news feed can miss. |
| **Keep existing knowledge current** | “Compare new information with these saved facts. Return material changes, resolved risks and contradictions.” | An update process that works even when the stock barely moves. |
| **Check context before a trade** | “Which assumptions in this company’s saved context are stale, contradicted or awaiting an imminent event?” | A focused freshness check, rather than another full company report. |

Those are proposed uses of its documented research and finance capabilities—not claims that its output has already passed our checks. Its tools combine financial data, filings, transcripts and web research, including historical investigations. [Finance capabilities](https://www.perplexity.ai/hub/blog/computer-for-professional-finance), [historical research support](https://docs.perplexity.ai/docs/agent-api/tools/finance-search)

There is a particularly concrete starting point in **our existing Broadcom analysis**.

The saved March 2024 analysis already contains dozens of guidance histories, company news and five peers. Its analyst-expectations section is empty, with recorded provider failures; historical forward estimates are deliberately excluded because their availability before the event cannot be established. [Saved analysis]( /home/faisal/EventMarketDB/earnings-analysis/Companies/AVGO/events/Q1_FY2024/context_bundle.json:7431)

A useful Perplexity assignment would therefore be:

> Find the expectations published before Broadcom’s March 2024 earnings announcement. Then identify what the announcement changed. Supply the original sources, relevant passages, financial periods and publication times. Mark anything whose historical availability cannot be verified.

This tests whether it adds something we lack. Asking it to regenerate our existing guidance table would be a weaker comparison.

We also already have [Perplexity search and research code](/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts/pit_fetch.py:830). The subscription’s potential advantage is its combined tools, data access and ability to complete a larger investigation—not merely access to Perplexity search.

**It can help historically, with one essential distinction.**

- **“What happened, and how did this company evolve?”** Historical documents and research can help substantially.
- **“Why did that past price move happen?”** Later evidence can help explain it, provided we identify it as hindsight.
- **“Could we have made this trade using only information available then?”** That requires verified historical information and recorded decision inputs. A date-filtered search or today’s answer about an old event does not establish this.

For example, an article published after earnings may accurately report the earlier consensus. That makes it useful historical evidence; it does not prove we had access to that information before earnings. Search filters support retrieval by dates, but do not themselves supply an archive of every page’s earlier contents. [Date-filter documentation](https://docs.perplexity.ai/docs/search/filters/date-time-filters)

**To learn from Perplexity continuously, I would use this process:**

1. Give Perplexity and our process the **same company context, question and time boundary**.
2. Compare the useful facts each finds, what each misses, and the work needed to correct the results.
3. Check disagreements against original sources. Perplexity’s answer is another candidate answer, not the answer key.
4. When it performs better, identify the reason: a better source, a missing comparison, better retrieval of prior facts, or a useful check.
5. Add that specific improvement to our existing process, then check it on another company or later quarter.

For example, if it repeatedly notices customer spending changes that our same-industry peer search misses, the lesson is to search relevant customers when investigating demand. We would improve that step, rather than create a general-purpose copy of Perplexity.

We can preserve the useful instructions as a reusable skill. Current Perplexity documentation supports custom instruction files; it also says the old “workflows” were replaced by skills and not every workflow migrated. [Skills documentation](https://www.perplexity.ai/help-center/en/articles/13914413-how-to-use-computer-skills)

**Could the subscription replace almost everything? It depends on which outcome we choose.**

| Intended outcome | My assessment |
|---|---|
| You research companies, receive alerts, inspect evidence and decide trades yourself | **Perplexity could become the main working tool.** This may be a much faster route than completing our entire platform first. |
| Maintain useful company context between earnings | **Brain is a serious replacement candidate.** We should test its retention, corrections and retrieval across repeated updates. |
| Run our precise company/fact relationships, price windows and historical trading evaluation consistently | **A subscription has not been shown to cover this automatically.** We still need to define and check those rules, wherever they run. |
| Build dashboards, reports and spreadsheets | Much of this can be delegated. It is unlikely to justify substantial custom development initially. |
| Connect research to brokerage activity | Connections exist, including IBKR. Trading modes and account eligibility are separate; buying Perplexity does not establish unattended execution for our account. [IBKR documentation](https://www.interactivebrokers.com/en/trading/ai-integrations.php) |

Computer can also help build the remaining software. However, generated software still needs our rules and verification.

For our stated goal, I would retain a **small core we control**: accepted facts and their evidence, when information became available, consistent price measurements, and decisions recorded before their outcomes. Perplexity can supply research and help maintain context around that core. The graph’s value should be demonstrated through better retrieval and evaluation.

There is a practical connection available: Codex or Claude Code can request work through the official **Computer MCP connection**, attach context and retrieve generated files. Those calls use the Perplexity account’s Computer credits. Ordinary API calls are separate; Finance Search currently costs US$5 per 1,000 tool calls plus model usage, which gives us another option for routine automated lookups. [Computer connection](https://docs.perplexity.ai/docs/getting-started/integrations/computer-mcp-server), [API pricing](https://docs.perplexity.ai/docs/agent-api/tools/finance-search)

Its recurring automations can run as often as every 15 minutes, but may start late and stop when credits are exhausted. That is useful for ongoing research; we still need to measure whether it meets our timing requirements. [Automation limits](https://www.perplexity.ai/help-center/en/articles/11521526-perplexity-tasks)

**My proposed first comparison is Broadcom’s missing expectations and cross-company evidence, followed by repeated company updates.** Measure verified additions, missed facts, correction time and cost against our current process. Keep Perplexity wherever it performs better; reproduce only the useful steps we can run more reliably or cheaply ourselves.

I have verified the documented capabilities and inspected the demo, but have not run those paid Computer tasks. Whether it deserves the quoted subscription cost—and how much custom work it can eliminate—remains an execution test, not something the marketing page can settle.

---

## Practical workflow and plan choice — checked November 14, 2026 (EST)

**Recommendation: start with Enterprise Pro, free official publications, and the IBKR data already available to us. Use Perplexity for selected investigations; keep the trigger, price calculations and decision record in our own system.** Start with paper trading one approach over hours to a few days. This is a proposed workflow, not an implemented or proven trading strategy.

The capabilities below were checked against official documentation and our code. Paid Computer tasks, account entitlements, research speed, credit consumption and broker execution have **not** been tested in this review.

### 1. Enterprise Pro versus Enterprise Max

**Enterprise Pro provides the core tools needed to try this. Buying Max is not established as necessary to obtain the advertised built-in finance research.** However, Perplexity does not publish a complete provider-by-provider table proving identical coverage, history and freshness on both tiers.

| Relevant difference | Enterprise Pro | Enterprise Max |
|---|---|---|
| Reference price, paid monthly | $40 per seat | $325 per seat |
| Reference price, paid annually | $400/year; approximately $34/month | $3,250/year; approximately $271/month |
| Computer credits renewed each month | 500 | 15,000 |
| Computer, Projects, connectors and recurring work | Available | Available |
| Brain, its background knowledge system | Not currently included | Research Preview |
| Model Council and Max-only Search models | Not included | Included |
| Research, file and creation limits | Lower | Higher |

These are the published reference prices, **not a conversion of the owner's Canadian checkout**. The $34/$271 cards describe annual equivalents. The CAD amount, tax, billing period and amount charged today must be read from checkout. [Billing](https://www.perplexity.ai/help-center/en/articles/10352986-enterprise-pricing-and-billing-frequently-asked-questions), [Pro capabilities](https://www.perplexity.ai/help-center/en/articles/10352973-what-is-enterprise-pro), [monthly credits](https://www.perplexity.ai/help-center/en/articles/13901321-how-credits-work-for-enterprise-organizations-member-guide), [Max capabilities](https://www.perplexity.ai/help-center/en/articles/12310544-what-is-enterprise-max)

The finance page lists included research data from **Benzinga, Coinbase, EDGAR, Fiscal.ai, FMP, Forge, MT Newswires, Polymarket, Quartr, Trading Economics, TradingView and Unusual Whales**. This means access to supported data through Perplexity. It does not give us twelve separate vendor accounts, their full products, unrestricted archives or their APIs. Selected built-in data and a connector requiring our own vendor licence are different offerings—even when the provider appears in both lists. For example, the MT Newswires connector requires MT credentials. [Included versus connected data](https://www.perplexity.ai/en-GB/hub/solutions/finance), [built-in finance tools](https://www.perplexity.ai/en-GB/hub/blog/computer-for-professional-finance), [MT connection requirements](https://www.mtnewswires.com/mcp-server)

**The meaningful Pro limitation is sustained Computer use.** The credits guide lists an 8,000-credit introductory bonus for Enterprise Pro and 40,000 for Enterprise Max, expiring in about 30 days. Added to the monthly grant, those become 8,500 and 55,000 initial credits: consistent with the owner's $85/$550 promotion at the published $1-per-100-credit rate. They are not recurring monthly bonuses. The guide's example research report costs 350–950 credits; our actual tasks may differ substantially. [Credit pricing and promotions](https://www.perplexity.ai/help-center/en/articles/13838041-how-credits-work-on-perplexity)

Pro can buy more Computer credits through its organization pool. At the published reference rates, a purely illustrative month with 15,000 credits would cost $40 + $145 in extra credits = **$185 on Pro**, versus $325 on Max. This is a calculation, not a CAD quote or a promise of equivalent features; confirm regional credit prices. Therefore, running out of Pro credits does not automatically make Max the cheaper choice. [Organization credit purchases](https://www.perplexity.ai/help-center/en/articles/13901296-how-credits-work-for-enterprise-organizations-admin-guide), [credit rate](https://www.perplexity.ai/help-center/en/articles/13838041-how-credits-work-on-perplexity)

Two distinctions matter:

- **Search versus Computer:** standard Ask searches do not spend Computer credits. Computer calls from Claude/Codex do. The published Search model restrictions are expressly separate from Computer's model selector; do not assume every Search restriction applies to Computer. [Search models](https://www.perplexity.ai/help-center/en/articles/10354919-what-advanced-ai-models-are-included-in-my-subscription), [Computer effort settings](https://www.perplexity.ai/help-center/en/articles/20260917-effort-mode-in-perplexity-computer)
- **Computer connection versus API:** the official Computer MCP connection uses account credits and OAuth. Ordinary Search, Sonar and Agent API calls are separately billed on both Enterprise plans. Our existing `pit_fetch.py` uses those separately billed APIs. [Computer MCP](https://docs.perplexity.ai/docs/getting-started/integrations/computer-mcp-server), [API exclusion](https://www.perplexity.ai/help-center/en/articles/10352986-enterprise-pricing-and-billing-frequently-asked-questions)

Start monthly for evaluation. Changing Enterprise tiers can buy another seat while the previous purchased seat remains billed until its renewal; do not assume an annual Pro purchase is credited toward Max. Choose Max if testing Brain or another exclusive feature is itself valuable, or measured usage and account pricing justify it. [Seat changes](https://www.perplexity.ai/help-center/en/articles/12310544-what-is-enterprise-max)

### 2. The first trading approach to test

Use **five selected liquid US stocks**, initially studying earnings and guidance changes and their effects on relevant customers, suppliers or competitors. Look for a supported reason a move might continue over hours to three trading days. Begin with paper long positions; negative findings can produce an avoid/exit judgment. These are proposed pilot boundaries, not approved investment rules.

The key question is not just “did this news move the stock?” It is **“after we discover it, research it and could actually enter, is there still a worthwhile opportunity?”**

```text
New relevant publication ──┐
                          ├─► same review ─► update company knowledge
Unusual IBKR price move ───┘              └─► investigate → pass / watch / trade proposal
```

A useful fact is saved even when there is no price move or trade. A price move is a request to investigate, not proof of a cause or an instruction to buy.

### 3. The trigger without other data subscriptions

Use two triggers, with several ways to discover a publication:

| Input | Practical starting method | What it misses or requires |
|---|---|---|
| Company filings | Poll the free SEC submissions API for the small watchlist; start with a five-minute interval. Process new relevant filings and exhibits. | A filing can appear after the company's original announcement. It is not a complete news feed. |
| Company announcements | Read each company's official investor-relations news feed or announcement page. Broadcom, for example, publishes RSS feeds. | Feed support and update timing vary by company. Confirm the actual source before relying on it. |
| News already included by IBKR | First request the account's available news providers, then consume supported headlines for the watchlist. | IBKR documents BRFG, BRFUPDN and DJNL as enabled by default; actual account availability still needs checking. These are not full Benzinga coverage. |
| Unusual price change | Evaluate matching stock and SPY one-minute observations from entitled IBKR data. | Requires current data for both instruments; delayed or frozen data cannot be presented as live. |
| Wider discovery | Use a bounded Perplexity watchlist review and research on demand. For a Pro pilot, ordinary Search can provide the manual daily review. | Neither search results nor a scheduled research task guarantee every headline or immediate discovery. |

SEC provides unauthenticated submissions APIs updated during dissemination; respect its declared user-agent and rate-limit rules. [SEC APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), [access rules](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data), [Broadcom feeds](https://investors.broadcom.com/rss-feeds)

IBKR's default API news sources are Briefing.com General Market Columns, Briefing.com Analyst Actions and Dow Jones Newsletters. Other feeds, including Benzinga Pro, require separate API subscriptions. `reqNewsProviders` reports what the username can access. [News subscriptions](https://www.interactivebrokers.com/docs/tws-api/doc/news/introduction), [provider discovery](https://www.interactivebrokers.com/docs/tws-api/doc/news/providers)

**Proposed price trigger for testing:** investigate an absolute stock-minus-SPY return of at least **2 percentage points**, over either the last 60 minutes within the current regular session or the previous regular close to now. Before 60 minutes of the session exist, use only the latter. This is an example threshold to evaluate, not an established profitable setting.

```text
Stock return = 100 × (stock end price / stock start price − 1)
SPY return   = 100 × (SPY end price / SPY start price − 1)
Difference   = stock return − SPY return

Stock +3%, SPY +1% → difference +2 percentage points → investigate.
```

Use identical timestamps and session boundaries, the actual exchange calendar and consistent price adjustments. The subtraction is a simple market comparison, not proof that the move is company-specific. IBKR supports historical bars and updates to current bars; missing history stays unknown. [Bar requests](https://www.interactivebrokers.com/docs/tws-api/doc/md/historical-bars), [delayed data](https://www.interactivebrokers.com/docs/tws-api/doc/md/delayed-data)

To limit repeated work, allow at most one price-triggered investigation per company per hour initially. New material publications and reviews of an existing position bypass that price-only delay. Coalesce simultaneous alerts while a company review is running. Persist the last successful publication check and source/version IDs so restarting catches up and does not repeat the same job.

**Do not start with a Computer query every 15 minutes.** Native automations permit that frequency, but can start late, consume credits and stop when credits run out. Background runs also lack the previous conversation's context. A local timer can cheaply check official sources and IBKR data, invoking research only when needed. Perplexity's built-in price alerts are another documented option, but were not account-tested here. [Automations](https://www.perplexity.ai/help-center/en/articles/11521526-perplexity-tasks), [native price alerts](https://www.perplexity.ai/changelog/what-we-shipped-july-18th)

This covers a useful, limited trading universe. It does **not** recreate a complete market-wide breaking-news service.

### 4. Prepare company knowledge before an event

Use the same review process to establish and maintain one short, dated company summary: important business measures, latest guidance, what investors are expecting where verifiable, major customers/suppliers, current risks and upcoming dates. Begin with the latest annual report and recent earnings materials; use our existing saved history wherever sound.

For each new publication, Claude/Codex asks: **does this change an important number, expectation, exposure or risk?** If yes, update the summary and its source-backed facts even when the stock is flat. If the supplied document answers the question, another Perplexity investigation is unnecessary. Use Computer for missing context, conflicting evidence or wider research.

Before a trade, refresh the relevant assumptions and check for intervening publications. A missing or failed check is recorded as missing, not “nothing changed.”

Supply the current summary with the research request. Brain can help on Max, but it runs in the background and is not a guaranteed immediately current record. Pro's Projects and our explicit saved summaries suffice for this pilot. [Brain behavior](https://www.perplexity.ai/help-center/en/articles/19700001-what-is-brain), [Projects on Pro](https://www.perplexity.ai/help-center/en/articles/10352973-what-is-enterprise-pro)

### 5. One investigation answers the trading questions

Send Computer the new publication or price window, the saved company summary and the exact information cutoff. Ask for one compact evidence pack:

| Question | Required answer |
|---|---|
| What changed? | New facts versus previous guidance and, where available, expectations published before the announcement. Keep different periods and accounting measures separate. |
| Has something similar happened? | A dated list of comparable events, including flat and opposite outcomes; state material differences and missing evidence. |
| What matters in this company now? | Which existing business measures, exposures or risks the new information changes, and what remains unresolved. |
| Who else is affected? | Named customers, suppliers or competitors, evidence for the relationship and the mechanism of impact. Being mentioned is insufficient. |
| What could explain or offset the move? | Competing company news, market/sector moves and relevant macro developments; separate observation from inference. |
| What would disprove the idea? | Specific contrary facts or developments, with sources, plus questions that still need answers. |

Return original source links, relevant passages, publication/availability evidence and missing items. A citation alone is not validation: check that the passage exists and supports the claim. Calculations stay in code; semantic judgments stay visible as judgments. This follows the project's existing AI design guidance without requiring another model subscription. [Citation-check pattern](https://docs.typesafe.ai/cookbooks/citation_check)

**Historical comparison needs our price calculation.** For the earnings pilot, begin with all eight previous earnings events for the same company, classify their similarity using the information available around each event, then inspect their outcomes. If fewer exist, report the smaller set. Do not select only past winners or pretend a handful of cases proves a success probability.

Measure two separate things:

1. **Reaction to the announcement:** what prices did around publication, using a named window.
2. **Opportunity after our decision:** what happened from an entry time we could actually have reached, through the chosen exits. Include spread, fees and research delay.

For live paper cases, retain the actual decision time, submitted order and fill. For historical comparisons, define the entry rule before measuring returns and label bar-based fills as estimates; never buy at a price from before the research could finish. Compare stock and benchmark over the same interval. A Date's close-to-close return is not an after-publication or after-entry return.

Use entitled IBKR history for those calculations and save the returned data and query settings. IBKR does not provide every historical security or interval; delisted securities and some old intraday data are unavailable, and historical values can change through filtering/adjustments. This creates limits, including survivor bias, in any backtest based only on currently traded names. [Historical limitations](https://www.interactivebrokers.com/docs/tws-api/doc/md/market-data-limitations)

Perplexity can locate old documents, but today's revised page or estimate is not automatically evidence of what was known then. Later evidence can explain history; it cannot be inserted into an earlier decision. An AI may also know historical outcomes from training, so retrospective reasoning alone is not a clean trading test. Preserve decisions made before outcomes in the forward paper pilot. [Date-filter limits and fields](https://docs.perplexity.ai/docs/search/filters/date-time-filters)

### 6. Company effects and macro context

If an announcement affects another company, assess that company separately using its own current summary, price reaction and trade constraints. For example, a customer's higher spending might benefit a supplier, but higher costs might hurt that same customer's margins. One fact can support different judgments; do not automatically buy every named company.

Keep one shared daily macro note instead of regenerating it for each stock. Include the market and relevant sector's measured moves, the current policy setting, and imminent events relevant to the proposed holding period. Refresh when a material event occurs. Official Fed, BLS and BEA releases can supply public facts; a consensus forecast is separate and must have its own source. If it is unavailable, do not invent the “surprise.” [Fed dates and statements](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm), [BLS release schedule](https://www.bls.gov/schedule/news_release/cpi.htm), [BEA releases](https://www.bea.gov/news/schedule)

### 7. Decision, trade and management

Claude/Codex returns **PASS, WATCH or PROPOSE**, with the evidence, uncertainties, expected holding period and conditions that would invalidate the idea. A large price jump or a high AI confidence number does not by itself justify PROPOSE.

Before any paper order, ordinary code checks current prices, spread, cash, existing positions/orders, duplicate requests and the owner's configured size/loss limits. It also checks that the idea remains valid at the current price. Missing decisive evidence or stale market data means no order. Account size, position limits, entry/exit rules and overnight policy must be explicit before implementation; this research does not set them.

Use IBKR's native attached orders where appropriate, and confirm acceptance and protection for the filled quantity. Reconcile partial fills and existing orders after reconnecting before submitting anything again. The installed library and existing trade client already contain relevant primitives. A skill's prose is not an enforcement mechanism. [IBKR bracket orders](https://www.interactivebrokers.com/docs/general/order-types/complex-orders/bracket-orders)

For this pilot, propose regular-session entries, review new material information and reassess open positions before the close. Set a time exit by the close of the third trading session, counting the entry session as the first. Do not depend on an AI research task to notice a breached stop.

**Hours-to-days holdings can cross a night. Plain US-stock stop orders do not operate outside regular trading hours at IBKR; stop-limit orders can remain unfilled.** Therefore a stop distance is not a guaranteed maximum loss. Overnight permission and handling must be explicit rather than hidden in the term “bracket.” [IBKR outside-hours rules](https://www.interactivebrokers.com/support/faq/content/691836583)

Use paper execution to test the mechanics and record real-time decisions. Paper fills are simulated and do not establish achievable live fills. For initial live use, the owner reviews and submits orders. IBKR's native AI integration has separate eligibility and trading-mode rules, so do not assume an autonomous account connection is available or required. [Paper limitations](https://www.interactivebrokers.com/support/faq/content/35807733), [IBKR AI integration](https://www.interactivebrokers.com/en/trading/ai-integrations.php)

### 8. A concrete example

Illustrative, not an actual announcement:

- Monday at 4:10 p.m. EST, a watched company raises its sales outlook. Its official announcement reaches our publication check; no price threshold is needed.
- The saved company summary already shows its prior outlook and main customer exposures. Claude/Codex identifies the change, updates the facts and asks Perplexity only for missing expectations, comparisons and related-company evidence.
- Before Tuesday's entry review, we have the evidence pack, calculated historical comparisons and current macro context. We check intervening news and current IBKR prices.
- If the opening gap already absorbs the proposed benefit, we can pass. If a supported opportunity remains, we record a paper proposal and apply the trade rules.
- We measure results from the actual paper fill, not Monday's closing price. Later evidence and results are added separately.

If the initial trigger was an unexplained price jump instead, use the same review. “No supported explanation found” is a valid result.

### 9. What we already have, and the small missing connection

| Existing item checked | Reuse or limitation |
|---|---|
| [IBKR client](/home/faisal/EventMarketDB/scripts/trade/ibkr_client.py:570) | Streaming quote subscriptions, reconnect handling and attached entry/stop operations exist. Configuration defaults to delayed data; current entitlement and behavior need verification. |
| [Pinned IBKR library](/home/faisal/EventMarketDB/ibkr-mcp-server/uv.lock:246) | `ib_async` 2.0.1 is installed and locked. Its source already supplies historical bars, live updates and bracket orders. Reuse these instead of building market-data or order primitives. Native broker paths were inspected, not exercised in this review. |
| [Event runner](/home/faisal/EventMarketDB/scripts/run_event_trader.py:114) and [source manager](/home/faisal/EventMarketDB/config/DataManagerCentral.py:253) | The runner checks a Polygon subscription; sources include paid Benzinga and a keyed SEC service. It cannot be assumed to run unchanged with only IBKR and Perplexity. Public SEC access is a different route. |
| [Existing Perplexity retrieval](/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts/pit_fetch.py:844) | Useful existing retrieval and evidence handling, but these API calls do not spend the Computer subscription balance. |
| [Earnings context builder](/home/faisal/EventMarketDB/scripts/earnings/earnings_orchestrator.py:89) | Already assembles company history, peers and macro context. Reuse sound saved material; do not silently rely on removed providers or unverified old return windows. |
| Driver plans | Guide the accepted facts and relationships. The complete new DriverUpdate extraction/writing workflow is not yet built; this pilot does not require finishing it first. |

**Build only one small runner, one reusable review skill and a saved record of facts/decisions.** The runner receives source and price triggers, invokes Claude/Codex, calls Computer when needed and saves results. Codex already supports scripted execution. This is a proposed connection between native capabilities, not a claim that our existing runner implements it. [Scripted Codex](https://learn.chatgpt.com/docs/non-interactive-mode)

The official Computer MCP supports starting work, preserving its thread ID, checking completion and retrieving files. A timeout can mean work continues; check the same thread rather than launching duplicates. Authentication requests, questions or insufficient credits can pause work. An old result returning after a pause must be reassessed against current facts/prices. We found no documented general automation-to-local-runner webhook, so the proposed runner starts and reads its own requests. [Computer MCP behavior](https://docs.perplexity.ai/docs/getting-started/integrations/computer-mcp-server)

### 10. Keep the useful learning, and test the unknowns

Save the source/version, verified availability where known, discovery time, accepted facts, company subject, proposed effects, price window, decision time, decision and reasons. Retain skips and unresolved cases as well as trades; append outcomes later. Keep permitted excerpts, source references and our own findings rather than treating a subscription as ownership of a vendor's database.

These records can later feed the agreed Driver design: facts retain their source and subject; an explanation link records a supported judgment about an affected company/day. A fresh fact need not have an explanation link. Keep pre-trade decisions in their own history so replacing a later explanation cannot rewrite what we knew before a trade. The governing graph rules remain [EXPLAINED_BY.md](DRIVER_Predict_Explain_Learn/References/EXPLAINED_BY.md).

Before relying on the workflow, run these concrete checks:

1. **Access:** on Enterprise Pro, request the news, transcript, historical guidance and dated expectations needed for a real watched company. Record which built-in tools/sources respond, which demand another licence and which are missing. This resolves provider coverage that the public plan pages do not.
2. **Trigger and timing:** compare discovered publications against the official company's release list; measure missed releases and publication-to-discovery-to-decision delay. Verify the broker's actual news providers and live stock/benchmark data.
3. **History:** work through the complete eight-event sample, including unavailable or incomparable cases; independently check prices, dates, adjustments and information cutoffs.
4. **Paper operation:** verify duplicate handling, partial fills, protection, reconnect recovery, research failure and credit exhaustion without modifying the protected live services. Native capabilities must pass the actual account scenario before reuse is accepted.
5. **Cost and value:** record credits, completion time, verified new facts and correction work for repeated real tasks. Compare Perplexity with our process on the same cases. A first batch of ten completed forward reviews can reveal workflow problems; it cannot establish profitability.

Keep whichever research steps Perplexity does better. Copy useful instructions and retrieval ideas into our skill, then test them on another company or later event. **Learning its workflow does not give our future in-house system its licensed data access.** The lasting assets we control are the evidence we may retain, the company knowledge we build, the rules, and decisions recorded before their outcomes.

## Finance access, buying decision and Canadian costs — November 14, 2026 (EST)

This audit clarifies the earlier discussion; retain the original text above as requested. **Recommendation: evaluate one month of Enterprise Pro using its Computer credits and the official Computer MCP connection. No ordinary API credits, Max plan or additional vendor subscriptions are required to start this evaluation.** Enterprise is not a requirement for basic finance access: consumer Pro is a cheaper alternative. The reasons to prefer Enterprise Pro for this project are its documented no-training protection and, if the checkout confirms eligibility, its larger introductory Computer allowance. These are purchase recommendations, not purchases made.

Published capabilities and prices were checked against Perplexity documentation, provider announcements and the Bank of Canada. No authenticated paid task was run. Exact account coverage, useful-answer accuracy, delivery speed and measured cost remain untested. Documentation cannot establish unpublished rights or guarantee that every provider returns every requested record.

### What financial data is actually included?

The [finance page](https://www.perplexity.ai/en-GB/hub/solutions/finance) lists twelve included providers. Their names represent data available through Perplexity, not twelve standalone vendor subscriptions. The following distinguishes documented uses from missing detail.

| Included provider | What the evidence establishes |
|---|---|
| Benzinga | Its own announcement names news, analyst ratings, earnings, insider transactions and price movements. This is a licensed integration, not merely searching public Benzinga pages. The announcement does not specify exhaustive archive coverage or a delivery guarantee. [Benzinga announcement](https://www.prnewswire.com/news-releases/benzinga-and-perplexity-announce-strategic-partnership-to-power-ai-driven-financial-research-302637252.html) |
| Coinbase | Listed among included providers and built-in live finance tools. The reviewed documentation does not enumerate the included fields. Connecting a personal Coinbase account is a separate route. [Built-in tools](https://www.perplexity.ai/en-GB/hub/workshops/perplexity-computer-for-buyside-professionals) |
| EDGAR | SEC filings used as evidence for financial analysis and calculations. The underlying SEC publications are already public. [Finance launch](https://www.perplexity.ai/en-GB/hub/blog/computer-for-professional-finance) |
| Fiscal.ai | The Finance dashboard identifies it as the source of reported revenue and EPS. [Dashboard source attribution](https://www.perplexity.ai/finance?trk=public_post_comment-text) |
| FMP / Financial Modeling Prep | The dashboard identifies FMP as its financial-information provider. This does not grant our application an FMP API key. [Dashboard source attribution](https://www.perplexity.ai/finance?trk=public_post_comment-text) |
| Forge | Private-company fundraising, implied valuations, secondary prices, public marks and profiles; explicitly available to all Computer users without a Forge licence. [Release note](https://www.perplexity.ai/en-GB/changelog/brain-faster-computer-models-website-publishing) |
| MT Newswires | Included news content through the existing partnership. Its separately connected MCP service requires MT credentials. [Partnership](https://www.mtnewswires.com/news/mt-newswires-mcp-server-now-available-in-perplexity-computer-bringing-real-time-global-market-news-to-ai-driven-workflows), [connection requirements](https://www.mtnewswires.com/mcp-server) |
| Polymarket | Prediction-market data. These are market prices/odds, not established probabilities of outcomes. [Dashboard source attribution](https://www.perplexity.ai/finance?trk=public_post_comment-text) |
| Quartr | Its customer case confirms Perplexity integrated live and archived call audio/transcripts, reports and presentation slides. This establishes both current and historical research capability, not a complete archive export entitlement. [Quartr case study](https://quartr.com/customers/how-perplexity-leverages-quartr-api) |
| Trading Economics | Listed as included. Its exact Perplexity fields, history and release delay are not enumerated in the reviewed public documentation; do not promise its full calendar/API. [Included list](https://www.perplexity.ai/en-GB/hub/solutions/finance) |
| TradingView | The dashboard specifically credits TradingView for applicable Computer financial charts. That does not establish a free TradingView paid plan or exchange-data package. [Dashboard source attribution](https://www.perplexity.ai/finance?trk=public_post_comment-text) |
| Unusual Whales | The dashboard attributes options data to it. Its own full MCP service uses a separate API subscription; the included options-data attribution does not prove every options-flow, holdings or historical dataset is included. [Dashboard](https://www.perplexity.ai/finance?trk=public_post_comment-text), [vendor MCP announcement](https://unusualwhales.com/changelog/introducing-the-unusual-whales-mcp-server) |

**There are additional sources beyond those twelve logos.** The dashboard attributes estimates to **FactSet**, and Perplexity's workshop confirms selected built-in FactSet content. Full FactSet MCP access is a separate entitlement, even for existing Workstation customers. [Dashboard](https://www.perplexity.ai/finance?trk=public_post_comment-text), [FactSet requirements](https://www.perplexity.ai/help-center/en/articles/14809838-connecting-perplexity-with-factset)

**PitchBook Essentials**, selected **CB Insights** research/market maps and **Statista** statistics are also included without a separate vendor subscription, including limited access on Free. This is not an exclusive reason to buy Max. Their quota details are not published consistently: the general guide says monthly limits, while some source-specific pages say daily limits. Account limits must settle that discrepancy. [PitchBook dataset](https://www.perplexity.ai/help-center/en/articles/12869442-leveraging-pitchbook-data-with-perplexity), [CB Insights](https://www.perplexity.ai/help-center/en/articles/12869855-integrating-cb-insights-data-with-perplexity), [Statista](https://www.perplexity.ai/help-center/en/articles/12869733-using-premium-statista-data-with-perplexity), [general guide](https://www.perplexity.ai/help-center/en/articles/12870803-premium-data-sources)

The separately licensed connector catalogue is broader:

- Market/research: FactSet, Morningstar, Daloopa, Carbon Arc, Zacks, Wisesheets, AlphaCreek, Canary Data, MT Newswires, Quartr, Stocktwits and IBISWorld; IBKR connects the user's brokerage account.
- Company/private-market context: Guidepoint, Crunchbase, Grata, D&B Commercial Graph, Chronograph, AngelList, Flanks, Octus and Papermark.
- Crypto: Coinbase account data, Base, OpenSea and Allium.

These connectors use the user's partner account and its permissions; some require additional MCP entitlement. The launch also describes connecting a user's own PitchBook licence. **Buy none of these merely to begin our evaluation.** A provider appearing in both the included list and connector catalogue means there are different access routes. [Current connector catalogue](https://www.perplexity.ai/help-center/en/articles/12870803-premium-data-sources), [licensed-source launch](https://www.perplexity.ai/en-GB/hub/blog/computer-for-professional-finance)

### The finance products and workflows are different layers

| Offering | Direct usefulness to us | Important boundary |
|---|---|---|
| Finance dashboard | Inspect companies, news, earnings, watchlists, screeners and market context; check data before requesting a large report. | Some access is already free. Free U.S. price/volume history downloads were explicitly announced. [Dashboard](https://www.perplexity.ai/finance), [downloads](https://www.perplexity.ai/changelog/what-we-shipped-june-6th) |
| Ask / Search | Short cited lookups and refining the research question. | Standard Ask uses no Computer credits, but plan/source limits still apply. [Enterprise Pro](https://www.perplexity.ai/help-center/en/articles/10352973-what-is-enterprise-pro) |
| Computer finance research | Compare earnings with expectations, track guidance, examine peers, explain candidate catalysts, produce a company brief or exportable model. | It performs research and calculations; a citation or polished report is not proof of correctness. [Finance examples](https://www.perplexity.ai/en-GB/hub/solutions/finance) |
| Finance skills | Reuse an instruction set and output format for repeated research. | The launch advertised 35 workflows across ten segments. Workflows were replaced on September 23, 2026; not all migrated. Current installed skills must be checked, not inferred from the old count. [Skills guide](https://www.perplexity.ai/help-center/en/articles/13914413-how-to-use-computer-skills) |
| Catalyst monitoring / automations | Repeated checks for relevant developments across a small watchlist. | Scheduled runs can be every 15 minutes, may start late and consume credits even when no notification is produced. This is not documented as a complete streaming news feed. [Automations](https://www.perplexity.ai/help-center/en/articles/11521526-perplexity-tasks) |
| Documents, spreadsheets and integrations | Return a cited memo, spreadsheet, chart or dashboard; work through Excel or connected office tools when useful. | These are output/workflow options, not additional data licences. [Finance guide](https://www.perplexity.ai/hub/guides/computer-for-professional-finance), [Excel availability](https://www.perplexity.ai/en-GB/hub/workshops/perplexity-computer-for-buyside-professionals) |
| Brain | Retain context across Computer work. | Max/Enterprise Max research preview; not required when we supply our existing company context. [Brain](https://www.perplexity.ai/help-center/en/articles/19700001-what-is-brain) |
| Agent API finance_search | Retrieve structured company financials, prices, segments, earnings and analyst estimates for our own code. | Separately billed. Coverage varies, and Computer's complete source/skill catalogue is not documented as identical. [Finance tool](https://docs.perplexity.ai/docs/agent-api/tools/finance-search) |

Deep Research is also moving into Computer as a skill, with included usage before credits in the new experience; Enterprise rollout follows consumer rollout. Do not treat every research prompt as automatically charged, or assume every account has the same rollout. [Research transition](https://www.perplexity.ai/help-center/en/articles/2026102603-deep-research-and-model-council-in-computer)

The public catalyst demo inspected earlier was illustrative. The documented automation engine supports building a real monitor, but the demo itself did not establish working detection, coverage or latency. We cannot enumerate every currently installed finance skill from public marketing pages alone.

### Can our machine receive the information?

**Yes. Computer is the remote service doing the work; it does not mean its results are trapped in the website.** The official Computer MCP connection supports Claude Code and Codex, signs in through the user's Perplexity account and uses Computer credits without an ordinary API key. It returns answers and supports downloading generated files. [Computer MCP specification](https://docs.perplexity.ai/docs/getting-started/integrations/computer-mcp-server)

```text
Our Claude/Codex → Perplexity Computer → available finance sources
Our saved results ← cited answer / requested data file ← Computer
```

For example, request a CSV of a company's guidance changes with source URLs and dates, then download it through the documented asset tools. That is technically supported; completeness and each returned fact still need checking. The connection does not grant direct calls to every internal finance tool, independent vendor API credentials, an unrestricted database dump, or Perplexity's proprietary implementation. Ordinary API access is a separate alternative, not an extra compulsory charge for this connection.

Portable Computer is another product: local inference on supported NVIDIA hardware can run without Computer credits. It does not establish free access to all remote finance data, and no new hardware is needed for our proposed evaluation. [Portable Computer requirements](https://www.perplexity.ai/help-center/en/articles/20260915-what-is-portable-computer)

### Credits in Canadian dollars

**70 credits means approximately C$1 when billed at the published rate—not C$70.** Perplexity publishes 100 credits per reference dollar. The conversion below uses **US$1 = C$1.4257**, the Bank of Canada's November 13, 2026 daily average, independently retrieved from its FXUSDCAD API and checked against its table. These are converted estimates before tax/card charges, not a Canadian checkout quote. Local pricing can differ. [Credit rate](https://www.perplexity.ai/help-center/en/articles/13838041-how-credits-work-on-perplexity), [Bank of Canada](https://www.bankofcanada.ca/rates/exchange/daily-exchange-rates/), [local-currency billing](https://www.perplexity.ai/help-center/en/articles/13182759-paying-in-local-currency)

| Work / purchase | Reference cost | Converted CAD |
|---|---:|---:|
| Standard Ask question | No Computer credits | No extra Computer charge |
| Computer quick-fact example | 15–70 credits = US$0.15–0.70 | C$0.21–1.00 |
| Computer research-report example | 350–950 credits = US$3.50–9.50 | C$4.99–13.54 |
| 1,000 additional Computer credits | US$10 | C$14.26 |
| Standard Search API request | US$0.005 | C$0.0071 |
| Agent API finance_search invocation | US$0.005, **plus model usage and other calls** | C$0.0071 tool fee, **plus the rest** |

The Computer ranges are examples, not quotes for our prompts. API Search returns retrieved material rather than a completed Computer investigation. Therefore its fee cannot be compared with a full report as though the outputs were equivalent. [Computer examples](https://www.perplexity.ai/help-center/en/articles/13838041-how-credits-work-on-perplexity), [API pricing](https://docs.perplexity.ai/docs/getting-started/pricing)

The concern about repeated small tasks is valid: 100 calls costing 70 credits each consume about **C$99.80 of credit value**. Twenty research reports at the published range would put an Enterprise Pro month at roughly **C$149.70–320.78 total**, including its US$40 subscription, using its 500 monthly credits, and buying the rest at the reference rate. This excludes the introductory bonus, taxes and other work. These are workload calculations, not observed bills. Use short searches for ordinary questions and reserve Computer for investigations that add useful evidence.

### What to buy, and what not to assume

| Plan | Monthly reference price / CAD equivalent | Relevant allowance |
|---|---|---|
| Consumer Pro | US$20 / about C$28.51 | Computer access; 4,000-credit introductory bonus if eligible. Weekly included usage is rolling out; no fixed monthly credit grant. |
| Enterprise Pro | US$40 / about C$57.03 | 500 recurring monthly credits; 8,000-credit introductory bonus if eligible; enterprise data protection and administration. |
| Consumer Max | US$200 / about C$285.14 | 10,000 recurring monthly credits; 35,000-credit introductory bonus if eligible; Brain preview and higher limits. |
| Enterprise Max | US$325 / about C$463.35 | 15,000 recurring monthly credits; 40,000-credit introductory bonus if eligible; higher limits and exclusive features. |

References: [consumer Pro price](https://www.perplexity.ai/properks), [consumer Max](https://www.perplexity.ai/help-center/en/articles/11680686-perplexity-max), [Enterprise prices](https://www.perplexity.ai/help-center/en/articles/10352986-enterprise-pricing-and-billing-frequently-asked-questions), [consumer allowances and bonuses](https://www.perplexity.ai/help-center/en/articles/13838041-how-credits-work-on-perplexity), [Enterprise monthly credits](https://www.perplexity.ai/help-center/en/articles/13901321-how-credits-work-for-enterprise-organizations-member-guide), [Enterprise Max](https://www.perplexity.ai/help-center/en/articles/12310544-what-is-enterprise-max).

The owner's approximately US$34 / US$271 cards are annual-plan monthly equivalents, not month-to-month prices. Enterprise Pro is US$400 paid annually; Max is US$3,250 annually. The owner's **C$482.33 checkout** is a separate actual displayed quote whose billing period must be checked; the converted estimates above do not override it.

The advertised **$85 / $550 in credits** is consistent with the initial monthly grant plus introductory bonus, not that amount renewed monthly. Bonuses expire in about 30 days. Afterward, Enterprise Pro's 500 monthly credits cover only US$5 of reference Computer usage. Additional Computer credits can be purchased without upgrading to Max. [Credit guide](https://www.perplexity.ai/help-center/en/articles/13838041-how-credits-work-on-perplexity), [organization credit purchases](https://www.perplexity.ai/help-center/en/articles/13901296-how-credits-work-for-enterprise-organizations-admin-guide)

For a small evaluation, set an explicit usage limit and keep automatic refills off. This is not a guaranteed hard ceiling: the Enterprise member guide says task overruns can create negative balances that may be invoiced to the organization. [Enterprise billing behavior](https://www.perplexity.ai/help-center/en/articles/13901321-how-credits-work-for-enterprise-organizations-member-guide)

**Our purchase sequence:** one monthly Enterprise Pro seat if its offered bonus and data protection are useful; consumer Pro is sufficient for a cheaper basic Computer evaluation. Start with included usage/credits. Add ordinary API credits only when comparing cheaper automated lookups against Computer, or when our existing API-based code needs them. Do not buy Max merely to obtain the listed finance providers, and do not buy vendor subscriptions before identifying a specific missing dataset.

### The narrow evaluation that directly helps our build

Use the existing company examples rather than inventing a new project:

1. **News:** ask for recent Benzinga/MT items for a watched company, with original links, publication times and the actual source used. Compare with known publications; record missing items and discovery delay.
2. **Company facts:** compare guidance across an earnings release and transcript; identify the company and period, and return a compact cited table. Keep proposed price effects separate from reported facts.
3. **Historical expectations:** use the existing AVGO March 2024 case. Require expectations supported by evidence available before the actual earnings announcement. A post-earnings article reporting an earlier consensus is useful hindsight evidence, but does not by itself establish what our system could have retrieved beforehand.
4. **Broader context:** request the main business exposures, current risks, relevant macro releases and supported effects on peers; mark missing information explicitly.
5. **Local return:** receive the answer and a small structured file through Computer MCP. Record elapsed time, credits, source/date errors and genuinely new useful facts, then repeat the same task on another company/event.

**Current verdict:** there is verified extra data and a usable route back to our machine. Both current and historical research are supported. A complete historical expectations archive, exhaustive low-latency news feed, identical data access across all plans/API routes, and profitable trading performance are not established. Those are specific test questions, not promises that a more expensive subscription resolves. Keep our triggers, company history and trading records; use Perplexity where repeated tests show it supplies better evidence or saves work.

## Current findings and next step — concise summary, November 14, 2026 (EST)

**Start here for the current purchase/setup status.** This section updates earlier recommendations; the detailed evidence and provider catalogue remain above.

### 1. Already purchased and working

The owner reports **$10 of Perplexity API credits purchased** and these successful setup checks:

- The API key is saved in the project's private `.env`, excluded from Git; Codex and Claude Code use it through their API MCP connections.
- Regular API search and answer tests passed. Decisions/Locate returned both expected quotes at the correct text positions.
- Already-running API MCP connections may need restarting to load the key. **Computer MCP still requires separate Perplexity account access.**

These are owner-supplied results, not independently rerun in this document update. The purchase amount is not a verified remaining balance. These tests establish API operation, not complete access to the advertised finance providers or Computer workflows.

### 2. Next recommended purchase

**Buy one Enterprise Pro seat, billed monthly, for the first evaluation:** [official Enterprise plans and purchase page](https://www.perplexity.ai/enterprise/pricing). Confirm the selected tier, monthly billing, CAD total and introductory credit eligibility before paying.

Enterprise Pro's reference price is **US$40/month, approximately C$57 before tax**. The approximately US$34/month card requires annual billing: US$400/year. Prefer monthly while evaluating. Enterprise Pro is recommended for its no-training protection and larger introductory allowance; consumer Pro, about C$29/month, can also run Computer. Max is not established as necessary for the included finance sources. [Billing](https://www.perplexity.ai/help-center/en/articles/10352986-enterprise-pricing-and-billing-frequently-asked-questions), [Enterprise Pro](https://www.perplexity.ai/help-center/en/articles/10352973-what-is-enterprise-pro)

If eligible, Enterprise Pro starts with **8,000 bonus credits plus 500 monthly credits**. The bonus expires in about 30 days; only 500 renew each month. The advertised $85 is not a recurring monthly allowance. Additional Computer credits can be bought without upgrading. [Credits](https://www.perplexity.ai/help-center/en/articles/13838041-how-credits-work-on-perplexity)

### 3. What the subscription supplies

| Research area | Documented sources and scope |
|---|---|
| News and events | Benzinga: news, ratings, earnings, insider transactions and price information. MT Newswires: included news content. |
| Company figures and expectations | FMP financial information, Fiscal.ai reported revenue/EPS, selected FactSet data including estimates. |
| Original company material | EDGAR filings; Quartr live and historical calls, transcripts, reports and slides. |
| Other market context | Unusual Whales options data, Polymarket odds, Forge private-company information; Coinbase and Trading Economics are listed, but their exact included fields are not fully published. |
| Charts and broader research | TradingView charting; PitchBook Essentials, selected CB Insights research and Statista statistics. Some premium-source access is available even on Free, with limits. |

**Included data does not mean full vendor subscriptions, API keys or unrestricted archives.** A separately connected vendor account can provide broader access and may require its own licence. The detailed provider table above gives the individual evidence. [Included sources](https://www.perplexity.ai/en-GB/hub/solutions/finance), [dashboard attribution](https://www.perplexity.ai/finance?trk=public_post_comment-text), [premium-source rules](https://www.perplexity.ai/help-center/en/articles/12870803-premium-data-sources)

### 4. How the information reaches our machine

| Route | Payment | What we receive |
|---|---|---|
| Ordinary API / API MCP — already set up according to the owner | The purchased API credits | Search results and generated answers; separately test the finance_search tool for structured financial data. |
| Computer MCP — next setup after subscription | Computer account credits; separate account sign-in | Computer investigations, cited answers and downloadable files, directly usable by Claude/Codex. |
| Ask/Search in Perplexity | Subscription/free-plan limits; no Computer credits for standard Ask | Quick cited lookups through the interface. |

**Computer results are not trapped in its website.** The official connection supports returning answers and downloading files. The existing API key does not grant Computer access, and Computer calls do not require another ordinary API-credit purchase. [Computer MCP setup](https://docs.perplexity.ai/docs/getting-started/integrations/computer-mcp-server), [Finance API](https://docs.perplexity.ai/docs/agent-api/tools/finance-search)

### 5. Costs to remember

| Usage | Approximate CAD cost |
|---|---:|
| Standard Ask question | No extra Computer charge |
| Computer small-task example: 15–70 credits | C$0.21–1.00 |
| Computer research-report example: 350–950 credits | C$4.99–13.54 |
| 1,000 additional Computer credits | C$14.26 |
| Standard Search API request | C$0.0071 |
| Agent API finance_search invocation | C$0.0071 **plus model usage and any other calls** |

**70 credits is about C$1, not C$70.** Estimates use the published reference prices and November 13's Bank of Canada rate, US$1 = C$1.4257, before tax/card charges. Regional checkout prices can differ. Computer ranges are examples, not measured costs for our requests. Its report is more work than one API lookup, so those prices are not equivalent-output comparisons. [Credit prices](https://www.perplexity.ai/help-center/en/articles/13838041-how-credits-work-on-perplexity), [API prices](https://docs.perplexity.ai/docs/getting-started/pricing), [exchange rate](https://www.bankofcanada.ca/rates/exchange/daily-exchange-rates/)

For scale, twenty reports at that range would cost roughly **C$150–321/month including Enterprise Pro**, after using its recurring 500 credits and buying the rest, excluding the bonus and taxes. Set a usage limit; Enterprise task overruns can still create an invoiced negative balance. [Enterprise credit behavior](https://www.perplexity.ai/help-center/en/articles/13901321-how-credits-work-for-enterprise-organizations-member-guide)

### 6. Use it only where it improves our build

Use Perplexity repeatedly to find missing news, compare guidance and expectations, research company/peer/macro context, and return compact facts with dates and original sources. Keep our own company history, triggers and trading records. Learn from successful research methods and reuse them in our system; that does not transfer the underlying vendor licences.

The useful finance workflows include earnings comparisons, company briefs, research synthesis, annotated price charts, catalyst monitoring and exportable models. The old claim of 35 workflows is not a current installed catalogue: workflows became skills, and some did not migrate. Scheduled monitors can run every 15 minutes, may start late and consume credits per run. Brain is a Max/Enterprise Max preview; we can supply our own context without it. [Skills](https://www.perplexity.ai/help-center/en/articles/13914413-how-to-use-computer-skills), [automations](https://www.perplexity.ai/help-center/en/articles/11521526-perplexity-tasks), [Brain](https://www.perplexity.ai/help-center/en/articles/19700001-what-is-brain)

**Next test after purchase and Computer sign-in:** use one existing company case to retrieve recent news, guidance changes, expectations known before an earnings release, and supported effects on peers; receive the result locally. Record source/date correctness, missing information, useful new facts, elapsed time and credits. Compare the API and Computer on the same bounded questions before expanding use.

**Still unproven:** complete provider coverage, identical access across plans/API routes, dependable news-delivery speed, a historical expectations archive preserved as known at the time, and trading value. The successful API setup does not settle these. Public documentation supports both current and historical research, but these remaining questions require actual finance-data tests.

## Enterprise Pro: seven useful roles for our system — ranked

Based on [DRIVER_RULES_Categorized.md](DRIVER_RULES_Categorized.md), [EXPLAINED_BY.md](DRIVER_Predict_Explain_Learn/References/EXPLAINED_BY.md) and [DriverWorkflow.md](DriverWorkflow.md). Its main role is finding missing information and researching it faster. These are ranked by expected usefulness, not measured gains.

1. **Fill gaps in company history:** Find earlier guidance, risks and business changes missing from our database, using historical filings and calls. [Historical coverage](https://quartr.com/customers/how-perplexity-leverages-quartr-api)
2. **Investigate unexplained price moves:** When our existing sources do not explain a move, research possible causes and bring back supporting sources.
3. **Find what investors expected:** Find dated forecasts before earnings, where available, to distinguish good results from better-than-expected results. These support research; they are not company guidance or standalone expectation facts in release one. [Finance offering](https://www.perplexity.ai/en-GB/hub/solutions/finance)
4. **Find effects on other companies:** Research why Apple's announcement might matter to its suppliers or competitors, with evidence for each connection.
5. **Keep company context current:** Schedule checks for changed guidance, emerging risks and upcoming events, even when the stock barely moves. [Scheduled tasks](https://www.perplexity.ai/help-center/en/articles/11521526-perplexity-tasks)
6. **Add the broader explanation:** Research whether interest rates, commodity prices or industry changes help explain a company's situation.
7. **Spot missing or misunderstood facts:** Compare selected outputs from our system with original sources and flag omissions or conflicting information for review.

**Start with #1 and #2.** Feed useful evidence into our existing process, preserving when information became available. Better accuracy, faster work and lower costs still need measurement; citations alone do not establish correctness.
