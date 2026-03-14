# Benzinga News Field Inventory — Complete Reference

> Source: Neo4j database, queried **2026-03-14**
> Total News nodes: **342,953**
> Date range: `2021-01-01` to `2026-03-13`
> Previous snapshot (2026-02-09): 335,250 nodes (+7,703 since)

## Coverage Summary

| Field | Coverage | Notes |
|-------|----------|-------|
| `channels` | **100%** (0 without) | JSON string array, 117 unique values |
| `tags` | **37.5%** (128,569 with; 214,384 without) | JSON string array, 12,236 unique values |
| `authors` | **100%** | JSON string array, 282 unique, always exactly 1 per article |
| `body` | **89.8%** (308,117 with) | Full-text indexed |
| `embedding` | **100%** | Vector embedding for similarity search |
| `returns_schedule` | **100%** | JSON object with `hourly`, `session`, `daily` timestamps |
| `market_session` | **100%** | 4 unique values |

---

## All Node Properties

| Field | Type | Format | Notes |
|-------|------|--------|-------|
| `id` | STRING | `bzNews_{numeric_id}` | Primary key |
| `title` | STRING | Free text | Full-text indexed |
| `teaser` | STRING | Free text | Full-text indexed |
| `body` | STRING | Free text | Full-text indexed; 10.2% empty |
| `url` | STRING | URL | Benzinga article URL |
| `created` | STRING | ISO 8601 | e.g. `2023-01-05T14:31:29-05:00` |
| `updated` | STRING | ISO 8601 | e.g. `2023-01-05T14:31:29-05:00` |
| `channels` | STRING | JSON array | **Stored as JSON string**, use `apoc.convert.fromJsonList()` to unwind |
| `tags` | STRING | JSON array | **Stored as JSON string**, use `apoc.convert.fromJsonList()` to unwind |
| `authors` | STRING | JSON array | **Stored as JSON string**, always 1 element |
| `market_session` | STRING | Enum | 4 values (see below) |
| `returns_schedule` | STRING | JSON object | Keys: `hourly`, `session`, `daily` |
| `embedding` | LIST | Float vector | For cosine similarity search |

### Storage Format Warning

`channels`, `tags`, and `authors` are stored as **JSON strings**, not native Neo4j lists.

**Wrong**: `UNWIND n.channels AS ch` (iterates over characters of the string)
**Correct**: `WITH apoc.convert.fromJsonList(n.channels) AS chList UNWIND chList AS ch`

---

## Channels (117 unique)

Articles carry 0–15 channels (median 3, avg 2.7).

| # | Channel | Count |
|---|---------|-------|
| 1 | `News` | 255,987 |
| 2 | `Analyst Ratings` | 157,682 |
| 3 | `Price Target` | 124,674 |
| 4 | `Earnings` | 50,779 |
| 5 | `Trading Ideas` | 39,238 |
| 6 | `Markets` | 34,240 |
| 7 | `Guidance` | 21,757 |
| 8 | `Options` | 19,422 |
| 9 | `General` | 17,544 |
| 10 | `Movers` | 15,684 |
| 11 | `Reiteration` | 13,539 |
| 12 | `Tech` | 11,999 |
| 13 | `Short Ideas` | 10,410 |
| 14 | `Short Sellers` | 9,772 |
| 15 | `Initiation` | 8,653 |
| 16 | `Hot` | 8,600 |
| 17 | `Downgrades` | 7,769 |
| 18 | `Upgrades` | 7,741 |
| 19 | `Top Stories` | 7,543 |
| 20 | `Dividends` | 7,477 |
| 21 | `Analyst Color` | 6,420 |
| 22 | `Earnings Beats` | 6,192 |
| 23 | `Equities` | 5,818 |
| 24 | `Biotech` | 5,436 |
| 25 | `Media` | 4,732 |
| 26 | `Management` | 4,476 |
| 27 | `M&A` | 4,214 |
| 28 | `Health Care` | 4,184 |
| 29 | `Contracts` | 3,907 |
| 30 | `Intraday Update` | 3,306 |
| 31 | `FDA` | 3,218 |
| 32 | `Earnings Misses` | 2,870 |
| 33 | `Large Cap` | 2,590 |
| 34 | `Rumors` | 2,408 |
| 35 | `Long Ideas` | 2,364 |
| 36 | `Legal` | 2,149 |
| 37 | `Technicals` | 2,136 |
| 38 | `Events` | 1,792 |
| 39 | `Global` | 1,701 |
| 40 | `Buybacks` | 1,554 |
| 41 | `Offerings` | 1,531 |
| 42 | `After-Hours Center` | 1,441 |
| 43 | `Cryptocurrency` | 1,428 |
| 44 | `Politics` | 1,258 |
| 45 | `Government` | 1,182 |
| 46 | `Small Cap` | 1,064 |
| 47 | `Entertainment` | 924 |
| 48 | `Pre-Market Outlook` | 892 |
| 49 | `Insider Trades` | 753 |
| 50 | `Regulations` | 677 |
| 51 | `Asset Sales` | 633 |
| 52 | `Previews` | 603 |
| 53 | `Travel` | 436 |
| 54 | `Retail Sales` | 424 |
| 55 | `Hedge Funds` | 405 |
| 56 | `Social Media` | 402 |
| 57 | `Restaurants` | 378 |
| 58 | `Commodities` | 370 |
| 59 | `IPOs` | 351 |
| 60 | `Financing` | 331 |
| 61 | `Exclusives` | 324 |
| 62 | `Opinion` | 317 |
| 63 | `Education` | 314 |
| 64 | `SPACE` | 308 |
| 65 | `Economics` | 293 |
| 66 | `Mid Cap` | 293 |
| 67 | `Interview` | 278 |
| 68 | `Gaming` | 276 |
| 69 | `Fintech` | 275 |
| 70 | `Cannabis` | 274 |
| 71 | `Signals` | 274 |
| 72 | `Sports` | 242 |
| 73 | `Real Estate` | 231 |
| 74 | `Asia` | 213 |
| 75 | `Eurozone` | 175 |
| 76 | `SEC` | 134 |
| 77 | `Penny Stocks` | 122 |
| 78 | `Stock Split` | 117 |
| 79 | `Topics` | 108 |
| 80 | `Movers & Shakers` | 100 |
| 81 | `Macro Economic Events` | 96 |
| 82 | `Success Stories` | 91 |
| 83 | `REIT` | 90 |
| 84 | `Entrepreneurship` | 86 |
| 85 | `Market Summary` | 85 |
| 86 | `Startups` | 74 |
| 87 | `Federal Reserve` | 70 |
| 88 | `Personal Finance` | 53 |
| 89 | `ETFs` | 50 |
| 90 | `Futures` | 48 |
| 91 | `Bonds` | 46 |
| 92 | `Econ #s` | 46 |
| 93 | `Binary Options` | 40 |
| 94 | `Macro Notification` | 37 |
| 95 | `ESG` | 35 |
| 96 | `Market-Moving Exclusives` | 33 |
| 97 | `Insurance` | 31 |
| 98 | `Broad U.S. Equity ETFs` | 26 |
| 99 | `Prediction Markets` | 23 |
| 100 | `Private Markets` | 22 |
| 101 | `Small Business` | 19 |
| 102 | `Sports Betting` | 18 |
| 103 | `Psychedelics` | 18 |
| 104 | `Psychology` | 16 |
| 105 | `Emerging Markets` | 13 |
| 106 | `Press Releases` | 11 |
| 107 | `Crowdsourcing` | 11 |
| 108 | `Treasuries` | 10 |
| 109 | `Latin America` | 9 |
| 110 | `Sector ETFs` | 9 |
| 111 | `New ETFs` | 8 |
| 112 | `Financial Advisors` | 8 |
| 113 | `Forex` | 6 |
| 114 | `Termination` | 4 |
| 115 | `Emerging Market ETFs` | 3 |
| 116 | `Mutual Funds` | 2 |
| 117 | `Small Cap Analysis` | 2 |
| 118 | `Specialty ETFs` | 1 |

### Guidance Channel Filter

The `Guidance` channel (21,757 articles, rank #7) is the primary way to filter guidance-related news:

```cypher
MATCH (n:News)
WHERE apoc.convert.fromJsonList(n.channels) IS NOT NULL
WITH n, apoc.convert.fromJsonList(n.channels) AS chList
WHERE 'Guidance' IN chList
RETURN n.title, n.created
```

Note: Some earnings-related guidance may only carry the `Earnings` channel (50,779) without `Guidance`. The tag `earnings guidance` (12 articles) and `profit guidance` (5 articles) are too sparse to be useful filters.

---

## Market Session (4 unique)

| Value | Count |
|-------|-------|
| `in_market` | 159,344 |
| `pre_market` | 126,994 |
| `post_market` | 46,630 |
| `market_closed` | 9,985 |

---

## Authors (282 unique)

Every article has exactly 1 author. Top 100 by article count:

| # | Author | Count |
|---|--------|-------|
| 1 | `Benzinga Newsdesk` | 196,475 |
| 2 | `Benzinga Insights` | 88,280 |
| 3 | `Bill Haddad` | 6,992 |
| 4 | `Charles Gross` | 4,720 |
| 5 | `Adam Eckert` | 3,311 |
| 6 | `Vandana Singh` | 2,777 |
| 7 | `Anusuya Lahiri` | 2,762 |
| 8 | `Happy Mohamed` | 2,709 |
| 9 | `Shivani Kumaresan` | 2,683 |
| 10 | `Henry Khederian` | 2,158 |
| 11 | `Michael Horton` | 2,117 |
| 12 | `Avi Kapoor` | 2,081 |
| 13 | `Chris Katje` | 1,665 |
| 14 | `Nabaparna Bhattacharya` | 1,521 |
| 15 | `Anan Ashraf` | 1,511 |
| 16 | `Shanthi Rexaline` | 1,380 |
| 17 | `Priya Nigam` | 1,358 |
| 18 | `Akanksha Bakshi` | 1,262 |
| 19 | `Erica Kollmann` | 1,120 |
| 20 | `Benzinga Neuro` | 1,116 |
| 21 | `Ananya Gairola` | 1,106 |
| 22 | `Lekha Gupta` | 910 |
| 23 | `Melanie Schaffer` | 721 |
| 24 | `Lisa Levin` | 685 |
| 25 | `Shivdeep Dhaliwal` | 586 |
| 26 | `Surbhi Jain` | 567 |
| 27 | `Rounak Jain` | 524 |
| 28 | `Dylan Berman` | 475 |
| 29 | `Bibhu Pattnaik` | 412 |
| 30 | `Mark Putrino` | 399 |
| 31 | `Benzinga EV Insights` | 394 |
| 32 | `Badar Shaikh` | 391 |
| 33 | `Rachit Vats` | 359 |
| 34 | `Kaustubh Bagalkote` | 340 |
| 35 | `Vaishali Prayag` | 321 |
| 36 | `Akanksha` | 308 |
| 37 | `Namrata Sen` | 297 |
| 38 | `Ryan Gustafson` | 285 |
| 39 | `Wayne Duggan` | 261 |
| 40 | `Tyler Bundy` | 253 |
| 41 | `AJ Fabino` | 245 |
| 42 | `Madhukumar Warrier` | 182 |
| 43 | `Zaheer Anwari` | 173 |
| 44 | `FreightWaves` | 172 |
| 45 | `Craig Jones` | 157 |
| 46 | `Randy Elias` | 150 |
| 47 | `Evette Mitkov` | 150 |
| 48 | `Vishaal Sanjay` | 148 |
| 49 | `Joel Elconin` | 137 |
| 50 | `Shomik Sen Bhattacharjee` | 136 |
| 51 | `Luke J Jacobi` | 128 |
| 52 | `Murtuza Merchant` | 120 |
| 53 | `Finit` | 119 |
| 54 | `Franca Quarneti` | 117 |
| 55 | `Piero Cingari` | 116 |
| 56 | `Mohd Haider` | 112 |
| 57 | `Navdeep Yadav` | 108 |
| 58 | `Rishabh Mishra` | 97 |
| 59 | `Samyuktha Sriram` | 96 |
| 60 | `Alex Perry` | 94 |
| 61 | `Aaron Bry` | 90 |
| 62 | `Josh Enomoto` | 88 |
| 63 | `Adrian Zmudzinski` | 84 |
| 64 | `Jayson Derrick` | 83 |
| 65 | `Shivank Goswami` | 82 |
| 66 | `Triveni Kothapalli` | 79 |
| 67 | `Pooja Rajkumari` | 77 |
| 68 | `Michael Cohen` | 72 |
| 69 | `Bhavik Nair` | 66 |
| 70 | `Renato Capelj` | 59 |
| 71 | `Ragothaman Srinivasan` | 59 |
| 72 | `Nina Zdinjak` | 58 |
| 73 | `Maureen Meehan` | 57 |
| 74 | `Snigdha Gairola` | 49 |
| 75 | `Christopher Sappo` | 48 |
| 76 | `Mohit Manghnani` | 45 |
| 77 | `Benzinga Newsbot` | 44 |
| 78 | `Hayden Buckfire` | 41 |
| 79 | `Khyathi Dalal` | 39 |
| 80 | `TradePulse` | 39 |
| 81 | `Vuk Zdinjak` | 38 |
| 82 | `Tanzeel Akhtar` | 37 |
| 83 | `Zoltan Suranyi` | 35 |
| 84 | `Tanya Rawat` | 34 |
| 85 | `Aniket Verma` | 31 |
| 86 | `Steve Krause` | 29 |
| 87 | `Jelena Martinovic` | 29 |
| 88 | `Nikhil Dayal` | 26 |
| 89 | `Sean Torres` | 25 |
| 90 | `Tyree Gorges` | 25 |
| 91 | `Dylan Wechsler` | 24 |
| 92 | `Proiti Seal Acharya` | 23 |
| 93 | `Stjepan Kalinic` | 23 |
| 94 | `Eva Mathew` | 22 |
| 95 | `David Pinsen` | 22 |
| 96 | `Ramakrishnan M` | 21 |
| 97 | `Ye Kuang` | 21 |
| 98 | `Ethan Roberts` | 20 |
| 99 | `Sudhanshu Singh` | 20 |
| 100 | `The Bamboo Works` | 19 |

### Author types

| Type | Examples | Combined Count |
|------|----------|---------------|
| Automated/Bot | Benzinga Newsdesk, Benzinga Insights, Benzinga Neuro, Benzinga Newsbot, Finit, TradePulse | ~286,073 (83.4%) |
| Specialty Bot | Benzinga EV Insights, FreightWaves | ~566 (0.2%) |
| Human reporters | All others | ~56,314 (16.4%) |

---

## Tags (12,236 unique total)

Articles carry 1–34 tags when present (median 1, avg 1.6). 62.5% of articles have no tags.

### Benzinga Internal Tags (BZI-* codes)

| Tag | Count | Meaning |
|-----|-------|---------|
| `BZI-AAR` | 25,003 | Analyst Ratings |
| `BZI-UOA` | 17,252 | Unusual Options Activity |
| `BZI-POD` | 12,389 | Pick of the Day |
| `BZI-SHORTHIST` | 9,385 | Short Interest History |
| `BZI-EP` | 7,281 | Earnings Preview |
| `BZI-Recaps` | 5,697 | Recaps |
| `BZI-ROCE` | 2,307 | Return on Capital Employed |
| `BZI-PE` | 2,246 | Price / Earnings |
| `BZI-IA` | 1,601 | Internal Analytics |
| `BZI-AAR-UPDATE` | 1,159 | Updated Analyst Rating |
| `BZI-ExDiv` | 981 | Ex-Dividend |
| `BZI-Debt` | 944 | Debt |
| `BZI-CROSS` | 879 | Cross-reference |
| `BZI-IT` | 356 | Insider Trades |
| `BZI-CONF` | 241 | Conference |
| `BZI-WIIM` | 191 | Why It's Moving |
| `BZI-TFM` | 153 | Top Forecaster Moves |
| `BZI-GT` | 107 | General Tag |

### Editorial / Content Tags

| Tag | Count |
|-----|-------|
| `why it's moving` | 10,878 |
| `Briefs` | 10,504 |
| `Expert Ideas` | 5,660 |
| `Stories That Matter` | 5,184 |
| `PT Changes` | 1,242 |
| `benzinga neuro` | 1,194 |
| `AI Generated` | 847 |
| `contributors` | 732 |
| `Most Accurate Analysts` | 599 |
| `KeyProj` | 459 |
| `Pro Project` | 281 |
| `Wall Street's Most Accurate Analysts` | 236 |
| `Stock of the Day` | 228 |
| `premarket trading` | 213 |
| `benzai` | 202 |
| `Options Action` | 161 |
| `Top Wall Street Forecasters` | 147 |
| `Options Trade of the Day` | 113 |
| `Partner Content` | 106 |
| `Edge Project` | 94 |
| `PreMarket Prep` | 91 |
| `BZ Data Project` | 66 |
| `if you invested 1000 catalyst` | 63 |
| `top stories` | 58 |
| `Discover Project` | 42 |
| `Benzinga Inspire` | 50 |
| `$500 Dividend` | 357 |
| `Insider sells` | 298 |
| `Halts` | 99 |
| `offering` | 67 |
| `Eurasia` | 261 |

### Technology / AI Tags

| Tag | Count |
|-----|-------|
| `artificial intelligence` | 1,031 |
| `Consumer Tech` | 1,858 |
| `Appleverse` | 1,011 |
| `AI` | 731 |
| `AI Generated` | 847 |
| `AI stocks` | 99 |
| `semiconductors` | 280 |
| `Software & Apps` | 234 |
| `People In Tech` | 231 |
| `Cybersecurity` | 120 |
| `OpenAi` | 111 |
| `Blockchain` | 87 |
| `Generative AI` | 33 |
| `DeepSeek` | 32 |
| `ChatGPT` | 54 |
| `Apple Intelligence` | 52 |
| `xAI` | 62 |
| `cloud` | 35 |
| `cloud stocks` | 47 |
| `cloud computing` | 5 |
| `Robotics` | 27 |
| `Blackwell` | 32 |

### Apple Ecosystem Tags

| Tag | Count |
|-----|-------|
| `Apple` | 613 |
| `iPhone` | 668 |
| `iPhone 17` | 44 |
| `iPhone 16` | 103 |
| `iPhone 15` | 140 |
| `iPhone 15 Pro` | 23 |
| `iPhone 14` | 46 |
| `iPad` | 101 |
| `Apple Watch` | 112 |
| `iOS` | 57 |
| `Apple VIsion Pro` | 57 |
| `vision pro` | 95 |
| `MacBook` | 52 |
| `AirPods` | 45 |
| `App Store` | 51 |
| `SIRI` | 23 |
| `gadgets` | 315 |
| `smartphones` | 58 |
| `Tim Cook` | 309 |
| `Mark Gurman` | 158 |
| `Ming-Chi Kuo` | 83 |
| `Steve Jobs` | 114 |

### EV / Automotive Tags

| Tag | Count |
|-----|-------|
| `electric vehicles` | 3,893 |
| `EVs` | 3,076 |
| `mobility` | 2,972 |
| `Cybertruck` | 438 |
| `Model Y` | 175 |
| `FSD` | 170 |
| `autonomous vehicles` | 103 |
| `Model 3` | 102 |
| `Optimus` | 88 |
| `robotaxi` | 87 |
| `Electric Vehicle` | 69 |
| `Tesla Model Y` | 68 |
| `Electric Vehicle Stocks` | 64 |
| `robotaxis` | 64 |
| `automotive` | 61 |
| `Tesla FSD` | 57 |
| `Tesla Model 3` | 57 |
| `auto` | 56 |
| `NHTSA` | 55 |
| `Model S` | 54 |
| `Cybercab` | 51 |
| `cars` | 50 |
| `auto stocks` | 48 |
| `Model X` | 47 |
| `Full Self-Driving` | 40 |
| `Tesla Cybertruck` | 39 |
| `Tesla Semi` | 31 |
| `Tesla SuperCharger` | 31 |
| `F-150 Lightning` | 34 |
| `Mustang Mach-E` | 24 |
| `Tesla Roadster` | 28 |

### People Tags (analysts, executives, public figures)

| Tag | Count |
|-----|-------|
| `Elon Musk` | 3,583 |
| `Donald Trump` | 894 |
| `Tim Cook` | 309 |
| `Jensen Huang` | 234 |
| `Dan Ives` | 234 |
| `Jim Cramer` | 232 |
| `Gary Black` | 222 |
| `Daniel Ives` | 217 |
| `Gene Munster` | 200 |
| `Jeff Bezos` | 195 |
| `Mark Gurman` | 158 |
| `Joe Biden` | 156 |
| `Mike Khouw` | 132 |
| `Ross Gerber` | 115 |
| `Bob Iger` | 114 |
| `Steve Jobs` | 114 |
| `Cathie Wood` | 101 |
| `Alex Karp` | 92 |
| `Adam Jonas` | 86 |
| `Ming-Chi Kuo` | 83 |
| `Ron DeSantis` | 82 |
| `Andy Jassy` | 79 |
| `Laura Martin` | 79 |
| `Jim Farley` | 77 |
| `Jim Chanos` | 76 |
| `Mark Cuban` | 59 |
| `Roaring Kitty` | 61 |
| `Vlad Tenev` | 58 |
| `Adam Aron` | 56 |
| `Marc Benioff` | 50 |
| `Michael Burry` | 49 |
| `Brian Armstrong` | 49 |
| `Warren Buffett` | 45 |
| `Sam Altman` | 36 |
| `Nelson Peltz` | 33 |
| `Bill Ackman` | 31 |
| `Michael Saylor` | 25 |
| `Kamala Harris` | 47 |

### Analyst / Firm Tags

| Tag | Count |
|-----|-------|
| `Needham` | 449 |
| `Wedbush` | 428 |
| `Goldman Sachs` | 378 |
| `Morgan Stanley` | 338 |
| `CNBC` | 731 |
| `BofA Securities` | 299 |
| `JPMorgan` | 276 |
| `KeyBanc Capital Markets` | 243 |
| `RBC Capital Markets` | 231 |
| `Piper Sandler` | 231 |
| `Oppenheimer` | 206 |
| `Raymond James` | 196 |
| `Bank of America` | 189 |
| `BMO Capital Markets` | 133 |
| `JMP Securities` | 122 |
| `Rosenblatt Securities` | 121 |
| `Stifel` | 119 |
| `Telsey Advisory Group` | 119 |
| `Truist Securities` | 114 |
| `Mizuho Securities` | 97 |
| `KeyBanc` | 96 |
| `Optimize Advisors` | 93 |
| `Benchmark` | 83 |
| `Wells Fargo` | 76 |
| `Future Fund` | 76 |
| `Credit Suisse` | 69 |
| `Cantor Fitzgerald` | 69 |
| `Bernstein` | 63 |
| `Deepwater Asset Management` | 58 |
| `DA Davidson` | 55 |
| `Stephens` | 54 |
| `Rosenblatt` | 52 |
| `UBS` | 35 |
| `Jefferies` | 32 |
| `Canaccord Genuity` | 32 |
| `William Blair` | 45 |
| `Guggenheim Securities` | 45 |
| `Scotiabank` | 24 |
| `ARK Invest` | 35 |
| `GLJ Research` | 24 |
| `Citron Research` | 46 |
| `Muddy Waters` | 27 |
| `Spruce Point Capital` | 27 |

### Company / Product Tags

| Tag | Count |
|-----|-------|
| `Apple` | 613 |
| `Tesla` | 285 |
| `SpaceX` | 393 |
| `Amazon` | 105 |
| `StarLink` | 109 |
| `Disney+` | 99 |
| `Coinbase` | 65 |
| `ESPN` | 56 |
| `TikTok` | 65 |
| `CNBC` | 731 |
| `NVIDIA` | 53 |
| `Reddit` | 53 |
| `Robinhood` | 39 |
| `Netflix` | 37 |
| `Palantir` | 22 |
| `Boeing` | 45 |

### Macro / Commodity / Economy Tags

| Tag | Count |
|-----|-------|
| `China` | 433 |
| `tariffs` | 174 |
| `Inflation` | 70 |
| `energy` | 49 |
| `Golden Cross` | 47 |
| `Tariff` | 31 |
| `Steel` | 30 |
| `solar energy` | 31 |
| `Oil` | 25 |
| `Death Cross` | 30 |
| `Interest Rates` | 13 |
| `Federal Reserve` | 11 |
| `GDP` | 9 |
| `Gold` | 12 |
| `Trump Tariffs` | 12 |
| `Copper` | 11 |
| `Canada` | 43 |
| `Mexico` | 28 |
| `Japan` | 33 |
| `South Korea` | 28 |
| `India` | 114 |
| `Russia` | 51 |
| `Russia-Ukraine War` | 46 |
| `Housing` | 25 |
| `Jerome Powell` | 26 |

### Crypto Tags

| Tag | Count |
|-----|-------|
| `Bitcoin` | 256 |
| `dogecoin` | 219 |
| `Ethereum` | 146 |
| `cryptocurrencies` | 88 |
| `NFT` | 71 |
| `NFTs` | 69 |
| `Meme Coins` | 62 |
| `Shiba Inu` | 26 |
| `Digital Assets` | 38 |
| `Doge` | 50 |
| `FTX` | 30 |
| `Binance` | 22 |

### Sector / Industry Tags

| Tag | Count |
|-----|-------|
| `retail` | 204 |
| `streaming` | 190 |
| `streaming stocks` | 154 |
| `Freight` | 170 |
| `e-commerce` | 171 |
| `Consumer Discretionary` | 150 |
| `healthcare` | 113 |
| `Industrials` | 97 |
| `ecommerce` | 86 |
| `Logistics` | 64 |
| `Video Game Stocks` | 57 |
| `airlines` | 59 |
| `SVOD` | 71 |
| `nfl` | 77 |
| `media stocks` | 125 |
| `video games` | 114 |

### Political / Government Tags

| Tag | Count |
|-----|-------|
| `Donald Trump` | 894 |
| `2024 election` | 98 |
| `Joe Biden` | 156 |
| `Ron DeSantis` | 82 |
| `Department Of Government Efficiency` | 67 |
| `Meme Stocks` | 59 |
| `COVID-19 Vaccine` | 69 |
| `Kamala Harris` | 47 |
| `2024 Presidential Election` | 37 |
| `Elizabeth Warren` | 40 |
| `Bernie Sanders` | 38 |

### Social / Meme Tags

| Tag | Count |
|-----|-------|
| `twitter` | 225 |
| `X` | 72 |
| `Roaring Kitty` | 61 |
| `Meme Stocks` | 59 |
| `Meme Coins` | 62 |
| `wallstreetbets` | 40 |
| `Keith Gill` | 42 |
| `Ryan Cohen` | 36 |

### Guidance-Specific Tags

These are sparse — the `Guidance` **channel** is the primary filter, not tags:

| Tag | Count |
|-----|-------|
| `earnings guidance` | 12 |
| `profit guidance` | 5 |
| `Outlook` | 8 |
| `Preliminary Results` | 9 |

---

## Sectors & Industries (via INFLUENCES relationship)

Every News article maps to exactly **1 Sector** and exactly **1 Industry** through the `INFLUENCES` relationship.
These come from the Company the news is about, not from Benzinga tags/channels.

### Sectors (11 unique)

All sectors belong to the `S&P 500` MarketIndex.

| Sector | ETF | News Count |
|--------|-----|------------|
| `Technology` | `XLK` | 88,815 |
| `ConsumerCyclical` | `XLY` | 66,871 |
| `Healthcare` | `XLV` | 52,296 |
| `Industrials` | `XLI` | 39,487 |
| `FinancialServices` | `XLF` | 20,933 |
| `ConsumerDefensive` | `XLP` | 17,687 |
| `CommunicationServices` | `XLC` | 16,606 |
| `Energy` | `XLE` | 12,296 |
| `BasicMaterials` | `XLB` | 11,954 |
| `RealEstate` | `XLRE` | 8,788 |
| `Utilities` | `XLU` | 7,219 |

### Industries by Sector (115 unique)

#### BasicMaterials (10 industries)

| Industry | ETF | News Count |
|----------|-----|------------|
| `SpecialtyChemicals` | `IYM` | 4,606 |
| `Steel` | `SLX` | 1,826 |
| `AgriculturalInputs` | `MOO` | 1,728 |
| `Chemicals` | `VAW` | 1,346 |
| `BuildingMaterials` | `PKB` | 656 |
| `Copper` | `XME` | 646 |
| `Aluminum` | `XME` | 483 |
| `Gold` | `GDX` | 431 |
| `OtherPreciousMetalsAndMining` | `XME` | 160 |
| `CokingCoal` | `XME` | 72 |

#### CommunicationServices (6 industries)

| Industry | ETF | News Count |
|----------|-----|------------|
| `Entertainment` | `PEJ` | 7,990 |
| `InternetContentAndInformation` | `FDN` | 4,784 |
| `ElectronicGamingAndMultimedia` | `GAMR` | 1,857 |
| `TelecomServices` | `IYZ` | 1,203 |
| `AdvertisingAgencies` | `VOX` | 594 |
| `Publishing` | `COMM` | 178 |

#### ConsumerCyclical (19 industries)

| Industry | ETF | News Count |
|----------|-----|------------|
| `AutoManufacturers` | `CARZ` | 14,383 |
| `Restaurants` | `EATZ` | 7,810 |
| `SpecialtyRetail` | `XRT` | 7,349 |
| `InternetRetail` | `XRT` | 7,345 |
| `ApparelRetail` | `XRT` | 3,986 |
| `TravelServices` | `JETS` | 3,780 |
| `Leisure` | `PEJ` | 2,985 |
| `FootwearAndAccessories` | `XRT` | 2,862 |
| `ResidentialConstruction` | `ITB` | 2,716 |
| `AutoParts` | `CARZ` | 2,538 |
| `ApparelManufacturing` | `XRT` | 2,325 |
| `PackagingAndContainers` | `VDC` | 2,069 |
| `AutoAndTruckDealerships` | `CARZ` | 1,880 |
| `Lodging` | `PEJ` | 1,561 |
| `HomeImprovementRetail` | `XHB` | 1,088 |
| `RecreationalVehicles` | `PEJ` | 1,021 |
| `DepartmentStores` | `XRT` | 572 |
| `Furnishings` | `XHB` | 436 |
| `PersonalServices` | `PEJ` | 165 |

#### ConsumerDefensive (9 industries)

| Industry | ETF | News Count |
|----------|-----|------------|
| `DiscountStores` | `XRT` | 4,146 |
| `HouseholdAndPersonalProducts` | `VDC` | 4,050 |
| `PackagedFoods` | `PBJ` | 3,478 |
| `GroceryStores` | `VDC` | 1,708 |
| `FoodDistribution` | `PBJ` | 1,157 |
| `BeveragesNonAlcoholic` | `PBJ` | 1,091 |
| `FarmProducts` | `MOO` | 971 |
| `EducationAndTrainingServices` | `VCR` | 635 |
| `Confectioners` | `PBJ` | 451 |

#### Energy (5 industries)

| Industry | ETF | News Count |
|----------|-----|------------|
| `OilAndGasEAndP` | `XOP` | 5,069 |
| `OilAndGasRefiningAndMarketing` | `CRAK` | 2,239 |
| `OilAndGasMidstream` | `AMLP` | 2,225 |
| `OilAndGasEquipmentAndServices` | `OIH` | 1,658 |
| `OilAndGasDrilling` | `OIH` | 1,105 |

#### FinancialServices (9 industries)

| Industry | ETF | News Count |
|----------|-----|------------|
| `AssetManagement` | `IAI` | 6,426 |
| `CapitalMarkets` | `IAI` | 5,214 |
| `FinancialDataAndStockExchanges` | `IAI` | 3,294 |
| `InsurancePropertyAndCasualty` | `KIE` | 1,993 |
| `InsuranceLife` | `KIE` | 1,403 |
| `InsuranceBrokers` | `KIE` | 928 |
| `InsuranceDiversified` | `KIE` | 781 |
| `FinancialConglomerates` | `VOX` | 456 |
| `InsuranceReinsurance` | `KIE` | 438 |

#### Healthcare (10 industries)

| Industry | ETF | News Count |
|----------|-----|------------|
| `Biotechnology` | `IBB` | 17,022 |
| `MedicalDevices` | `IHI` | 7,743 |
| `DrugManufacturersGeneral` | `IHE` | 6,339 |
| `DiagnosticsAndResearch` | `IHI` | 6,071 |
| `MedicalInstrumentsAndSupplies` | `IHI` | 3,606 |
| `HealthInformationServices` | `IHF` | 3,425 |
| `HealthcarePlans` | `IHF` | 3,333 |
| `DrugManufacturersSpecialtyAndGeneric` | `XPH` | 2,385 |
| `MedicalCareFacilities` | `IHF` | 1,554 |
| `MedicalDistribution` | `IHF` | 818 |

#### Industrials (19 industries)

| Industry | ETF | News Count |
|----------|-----|------------|
| `AerospaceAndDefense` | `ITA` | 6,502 |
| `SpecialtyIndustrialMachinery` | `IYJ` | 5,831 |
| `Airlines` | `JETS` | 3,503 |
| `IntegratedFreightAndLogistics` | `IYT` | 3,229 |
| `EngineeringAndConstruction` | `PKB` | 3,145 |
| `FarmAndHeavyConstructionMachinery` | `PAVE` | 2,482 |
| `BuildingProductsAndEquipment` | `XHB` | 2,465 |
| `Railroads` | `IYT` | 1,893 |
| `ElectricalEquipmentAndParts` | `IYJ` | 1,578 |
| `ConsultingServices` | `IGV` | 1,552 |
| `IndustrialDistribution` | `IYJ` | 1,385 |
| `SpecialtyBusinessServices` | `IYJ` | 997 |
| `Trucking` | `FTXR` | 943 |
| `ToolsAndAccessories` | `IYJ` | 941 |
| `StaffingAndEmploymentServices` | `IYJ` | 911 |
| `RentalAndLeasingServices` | `IYJ` | 882 |
| `Conglomerates` | `IYJ` | 625 |
| `WasteManagement` | `IYJ` | 366 |
| `SecurityAndProtectionServices` | `HACK` | 257 |

#### RealEstate (10 industries)

| Industry | ETF | News Count |
|----------|-----|------------|
| `REITResidential` | `REZ` | 2,174 |
| `REITRetail` | `SRET` | 1,793 |
| `REITOffice` | `IYR` | 1,213 |
| `REITSpecialty` | `IYR` | 1,206 |
| `REITIndustrial` | `INDS` | 700 |
| `RealEstateServices` | `IYR` | 673 |
| `REITHealthcareFacilities` | `SRET` | 431 |
| `REITDiversified` | `SCHH` | 229 |
| `REITHotelAndMotel` | `SRET` | 188 |
| `REITMortgage` | `REM` | 181 |

#### Technology (12 industries)

| Industry | ETF | News Count |
|----------|-----|------------|
| `SoftwareApplication` | `IGV` | 24,884 |
| `SoftwareInfrastructure` | `IGV` | 19,868 |
| `Semiconductors` | `SOXX` | 14,674 |
| `ConsumerElectronics` | `IYW` | 6,533 |
| `InformationTechnologyServices` | `IGV` | 5,020 |
| `ComputerHardware` | `IYW` | 3,938 |
| `Solar` | `TAN` | 3,536 |
| `SemiconductorEquipmentAndMaterials` | `SOXX` | 3,354 |
| `CommunicationEquipment` | `SOXX` | 2,851 |
| `ScientificAndTechnicalInstruments` | `IYW` | 2,578 |
| `ElectronicComponents` | `IYW` | 1,241 |
| `ElectronicsAndComputerDistribution` | `IYW` | 338 |

#### Utilities (6 industries)

| Industry | ETF | News Count |
|----------|-----|------------|
| `UtilitiesRegulatedElectric` | `IDU` | 4,361 |
| `UtilitiesRenewable` | `TAN` | 707 |
| `UtilitiesRegulatedGas` | `FCG` | 647 |
| `UtilitiesIndependentPowerProducers` | `IDU` | 635 |
| `UtilitiesDiversified` | `IDU` | 591 |
| `UtilitiesRegulatedWater` | `PHO` | 278 |

---

## Relationships

News nodes connect outward only (no inbound relationships):

| Relationship | Target | Count |
|---|---|---|
| `INFLUENCES` | `Company` | 342,952 |
| `INFLUENCES` | `Sector` | 342,952 |
| `INFLUENCES` | `Industry` | 342,952 |
| `INFLUENCES` | `MarketIndex` | 342,951 |

---

## Corrections from Previous Reference (2026-02-09)

1. **`authors` field was omitted** — 100% coverage, 282 unique, always exactly 1 per article
2. **`InformationTechnologyServices` was listed under Industrials** — it actually BELONGS_TO Technology sector per Neo4j graph
3. **Industry count headers were wrong** — e.g., Industrials header said "17" but listed 20 entries, Technology said "13" but listed 11
4. **Total industries: 115** (not 110 as previously stated)
5. **Healthcare: 10 industries** (not 9 as header stated; all 10 were actually listed)
6. **channels field stored as JSON string** — not documented; using `UNWIND n.channels` iterates over characters, must use `apoc.convert.fromJsonList()`
7. **0 articles without channels** (was 365 — likely data cleanup or re-ingestion)

---

## Useful Query Patterns

### Filter by channel
```cypher
MATCH (n:News)
WITH n, apoc.convert.fromJsonList(n.channels) AS chList
WHERE 'Guidance' IN chList
RETURN n.title, n.created
```

### Filter by tag
```cypher
MATCH (n:News)
WHERE n.tags <> '[]'
WITH n, apoc.convert.fromJsonList(n.tags) AS tagList
WHERE ANY(t IN tagList WHERE t CONTAINS 'guidance')
RETURN n.title, n.created
```

### Filter by channel + company
```cypher
MATCH (n:News)-[:INFLUENCES]->(c:Company {ticker: 'AAPL'})
WITH n, apoc.convert.fromJsonList(n.channels) AS chList
WHERE 'Earnings' IN chList
RETURN n.title, n.created ORDER BY n.created DESC
```

### Count channels per article
```cypher
MATCH (n:News)
WITH size(apoc.convert.fromJsonList(n.channels)) AS ch_count
RETURN min(ch_count), max(ch_count), avg(ch_count), percentileCont(ch_count, 0.5) AS median
```
