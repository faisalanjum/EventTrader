
Starting with end in mind:**Trade Earning releases from 8-K reports**



1. LangExtract 8-k_Facts from 8-K reports (see universe below) & link to appropriate XBRL node types like concepts, periods, members,  dimensions etc. 

2. From news (see universe below), use LangExtract to create **CUSTOM:CONCEPTS** & must link them to XBRL Concepts (& may be to dimensions, members & domain). Also link these to news where these CUSTOM:CONCEPTS came from. - better is to start from this so 8-K_Facts may also link to CUSTOM:CONCEPTS? 

3. Again news outside the universe, use semantic search (>90% similarity) to link them to these CUSTOM:CONCEPTS


4. Create **DRIVER** nodes using LangGraph multiagent workflow by determining what made the 8-K report move. Also using all CUSTOM:CONCEPTS that are linked to XBRL concepts & dimensions that are also linked to 8-k_Facts. Note these CUSTOM:CONCEPTS are also linked to other news items which workflow can use. 

5. Finally, when a new earning release comes out (8-K report), we extract 8-K_Facts, then look at all XBRL concepts it relates to and from there check all related CUSTOM:CONCEPTS, DRIVER and OTHER linked news nodes etc. 


Main Steps

    1. Pick the universe for 8-K reports (**8-k_Fact**): 8-K (Item 2.02 Earnings only) reports where the hourly adjusted return exceeded ±3% 
                          AND the daily adjusted return continued in the same direction with a 
                          larger magnitude than the hourly move. 
                          - 1,298 reports across 499 companies (1,163 with >$1B market cap)
                          - Create XBRL nodes using LangExtract (partially done using LangExtract: see 
                                        EventMarketDB/drivers/8K_XBRL_Linking/FinalScripts/Xtract.ipynb )
                            **Include Guidance in LangExtract Schema - again to link to concepts, periods etc**


    2. Pick the universe for News (**Custom Concepts**): 
                          - Also include all news with same universe rules as above for 8-K 
                          - include news from   tag " why its moving" 


  The channels field already categorizes news. Here's what you have:

  | Channel                 | Count  | Example                                 |
  |-------------------------|--------|-----------------------------------------|
  | Price Target            | 73,691 | "Raises Price Target to $105"           |
  | Earnings                | 24,273 | "Q2 EPS $1.28 Beats $0.74 Estimate"     |
  | Guidance                | 11,975 | "Updates FY23 Guidance EPS $3.75-$4.00" |
  | "why it's moving" (tag) | 6,148  | "Shares trading lower after downgrade"  |
  | Initiations             | 4,046  | "Initiates Coverage with Buy Rating"    |
  | Downgrades              | 3,981  | "Downgrades to Market Perform"          |
  | Upgrades                | 3,886  | "Upgrades to Outperform"                |
  | M&A                     | 1,946  | Merger/acquisition news                 |

 & Transcripts 

    3. Create New Node Types & link to existing XBRL concepts: 
                            3.1:    Use LangExtract on News to create following Node types-
                                Guidance, Analysis, Estimates & Narrative , Price targets, Pre-announcements, reactions
                                with accompanying text & link to XBRL concepts

                            3.2: Link individual Transcripts Q&A to specific XBRL concepts as well as New Node Types??


    4. Attribution Analysis: Use LangGraph multi Agent Workflow (+ perplixity sec & tavily search, gpt judge)
                             to determine the actual reason of move.
                             Create Driver Nodes (Non-XBRL KPIs) & link to XBRL concepts & CUSTOM:CONCEPTS 
                            

                             
    5. Trade: based on realtime news, 8-k reports determine if this event is not stale, 
                significant (based on attribution analysis), place a trade




NEW ● Complete List: All Channels + Tags

  | Channel/Tag              | Count   | Type    |
  |--------------------------|---------|---------|
  | News                     | 142,746 | Channel |
  | Analyst Ratings          | 92,313  | Channel |
  | Price Target             | 73,691  | Channel |
  | Earnings                 | 24,098  | Channel |
  | Trading Ideas            | 22,000  | Channel |
  | Markets                  | 19,174  | Channel |
  | Guidance                 | 11,975  | Channel |
  | Reiteration              | 10,896  | Channel |
  | Options                  | 10,354  | Channel |
  | General                  | 9,997   | Channel |
  | Tech                     | 6,874   | Channel |
  | Short Ideas              | 6,701   | Channel |
  | Short Sellers            | 6,622   | Channel |
  | Movers                   | 6,547   | Channel |
  | "why it's moving"        | 6,148   | Tag     |
  | Top Stories              | 5,290   | Channel |
  | Equities                 | 4,737   | Channel |
  | Earnings Beats           | 4,494   | Channel |
  | Initiation               | 4,046   | Channel |
  | Downgrades               | 3,981   | Channel |
  | Upgrades                 | 3,886   | Channel |
  | Dividends                | 3,709   | Channel |
  | Analyst Color            | 3,249   | Channel |
  | Management               | 2,793   | Channel |
  | Hot                      | 2,678   | Channel |
  | Biotech                  | 2,621   | Channel |
  | Health Care              | 2,289   | Channel |
  | Earnings Misses          | 2,147   | Channel |
  | M&A                      | 1,946   | Channel |
  | Contracts                | 1,719   | Channel |
  | Media                    | 1,664   | Channel |
  | Large Cap                | 1,659   | Channel |
  | Intraday Update          | 1,373   | Channel |
  | Legal                    | 1,032   | Channel |
  | Global                   | 995     | Channel |
  | Long Ideas               | 970     | Channel |
  | After-Hours Center       | 927     | Channel |
  | Technicals               | 835     | Channel |
  | FDA                      | 829     | Channel |
  | Offerings                | 731     | Channel |
  | Buybacks                 | 713     | Channel |
  | Politics                 | 707     | Channel |
  | Government               | 667     | Channel |
  | Entertainment            | 663     | Channel |
  | Events                   | 631     | Channel |
  | Pre-Market Outlook       | 627     | Channel |
  | Rumors                   | 568     | Channel |
  | Small Cap                | 465     | Channel |
  | Previews                 | 421     | Channel |
  | Regulations              | 403     | Channel |
  | Cryptocurrency           | 391     | Channel |
  | Asset Sales              | 356     | Channel |
  | Mid Cap                  | 254     | Channel |
  | Social Media             | 238     | Channel |
  | Gaming                   | 220     | Channel |
  | Restaurants              | 181     | Channel |
  | SPACE                    | 175     | Channel |
  | Travel                   | 170     | Channel |
  | Economics                | 166     | Channel |
  | Insider Trades           | 154     | Channel |
  | Hedge Funds              | 154     | Channel |
  | Signals                  | 149     | Channel |
  | Financing                | 146     | Channel |
  | Opinion                  | 145     | Channel |
  | Cannabis                 | 137     | Channel |
  | Sports                   | 134     | Channel |
  | Asia                     | 130     | Channel |
  | Commodities              | 129     | Channel |
  | Real Estate              | 117     | Channel |
  | Education                | 108     | Channel |
  | Retail Sales             | 104     | Channel |
  | Exclusives               | 104     | Channel |
  | Fintech                  | 94      | Channel |
  | SEC                      | 79      | Channel |
  | Macro Economic Events    | 76      | Channel |
  | Topics                   | 74      | Channel |
  | Interview                | 73      | Channel |
  | Success Stories          | 73      | Channel |
  | Penny Stocks             | 56      | Channel |
  | Eurozone                 | 50      | Channel |
  | REIT                     | 43      | Channel |
  | Movers & Shakers         | 43      | Channel |
  | Entrepreneurship         | 41      | Channel |
  | Federal Reserve          | 34      | Channel |
  | Startups                 | 33      | Channel |
  | Stock Split              | 32      | Channel |
  | Econ #s                  | 32      | Channel |
  | IPOs                     | 31      | Channel |
  | Macro Notification       | 31      | Channel |
  | Insurance                | 27      | Channel |
  | Personal Finance         | 23      | Channel |
  | ESG                      | 23      | Channel |
  | Market Summary           | 19      | Channel |
  | Broad U.S. Equity ETFs   | 16      | Channel |
  | ETFs                     | 15      | Channel |
  | Psychedelics             | 15      | Channel |
  | Market-Moving Exclusives | 14      | Channel |
  | Sports Betting           | 9       | Channel |
  | Emerging Markets         | 9       | Channel |
  | Bonds                    | 8       | Channel |
  | Binary Options           | 8       | Channel |
  | Small Business           | 7       | Channel |
  | Psychology               | 7       | Channel |
  | Futures                  | 5       | Channel |
  | Press Releases           | 5       | Channel |
  | Latin America            | 5       | Channel |
  | Termination              | 3       | Channel |
  | Forex                    | 3       | Channel |
  | New ETFs                 | 2       | Channel |
  | Sector ETFs              | 2       | Channel |
  | Emerging Market ETFs     | 2       | Channel |
  | Mutual Funds             | 1       | Channel |
  | Crowdsourcing            | 1       | Channel |

  ---
  Other Tags (from tags field)

  | Tag               | Count   |
  |-------------------|---------|
  | (empty)           | 115,276 |
  | BZI-AAR           | 14,370  |
  | BZI-UOA           | 9,749   |
  | BZI-POD           | 8,260   |
  | BZI-SHORTHIST     | 6,417   |
  | "why it's moving" | 6,148   |
  | BZI-EP            | 3,605   |
  | Briefs            | 1,627   |
  | BZI-IA            | 1,168   |
  | BZI-Recaps        | 1,098   |
  | BZI-PE            | 1,083   |
  | PT Changes        | 848     |
  | BZI-AAR-UPDATE    | 708     |
  | BZI-ExDiv         | 460     |
  | BZI-ROCE          | 421     |

