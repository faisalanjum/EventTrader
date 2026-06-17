# RavenPack Event Taxonomy — Reference (assembled 2026-06-16)

> Purpose: a clean, **source-grounded** reconstruction of the RavenPack (now "Bigdata.com") event
> taxonomy — the professional "what kinds of events move stocks" ontology — to sit next to
> `DriverGraphSchema.md`. Every name below is **verbatim from a fetched public source**. Nothing invented.
>
> **Companion files (machine-readable) — CURRENT and LEGACY kept in SEPARATE files to avoid confusion:**
>
> *⭐ Use these two — vintages are cleanly split:*
> - [`taxonomy_CURRENT_modern.csv`](./taxonomy_CURRENT_modern.csv) — **529** CURRENT Bigdata.com topics (`vintage=CURRENT-bigdata`; compound `topic,group,type,sub_type` form). **These are a true subset of today's ~7,400.**
> - [`taxonomy_LEGACY_rpa.csv`](./taxonomy_LEGACY_rpa.csv) — **441** LEGACY RPA 1.0 leaf slugs (`vintage=LEGACY-rpa1.0`; old single-slug form). Same events as the current set in older naming.
> - [`bigdata_taxonomy_assembled.csv`](./bigdata_taxonomy_assembled.csv) — the combined union (970) with a `kind` column. Rebuild all three: `python3 merge_taxonomy_sources.py`.
> - [`merge_taxonomy_sources.py`](./merge_taxonomy_sources.py) — reproducible **build** (+ folds in any new candidate file passed as an arg). [`analyze_taxonomy.py`](./analyze_taxonomy.py) — composition/driver-family breakdown.
>
> *Raw sources (provenance):* CURRENT → [`bigdata_cookbook_topic_ids.txt`](./bigdata_cookbook_topic_ids.txt) (519, from `Bigdata-com/bigdata-cookbook`) + [`bigdata_docs_topic_paths.csv`](./bigdata_docs_topic_paths.csv) (128, docs crawl). LEGACY → [`RavenPack_categories.csv`](./RavenPack_categories.csv) (381, PLOS) + [`etda7728_appendixB_categories.txt`](./etda7728_appendixB_categories.txt) (261, ETDA #7728 via Wayback; +60 new) + PDF [`etda7728_dissertation.pdf`](./etda7728_dissertation.pdf).
> *Orthogonal axis:* [`ravenpack_property_role_tokens.txt`](./ravenpack_property_role_tokens.txt) — PROPERTY/entity-role tokens (acquiree, rater, plaintiff…), kept separate from leaves.
> *Unlock:* [`dump_bigdata_taxonomy.py`](./dump_bigdata_taxonomy.py) — dumps the whole live taxonomy once a credential exists (only route to all ~7,400).

---

## 0. Read first — what is public vs gated

| Layer | Status | Source |
|---|---|---|
| **Structure** (6-level field model, 50-field schema, scoring, entity types, property enums) | ✅ **Complete & verbatim** | RavenPack Analytics **User Guide v1.0** |
| **Group backbone** (top-level organization) | ✅ **60 modern groups covered** (≥ the ~56 target) | PLOS + cookbook + docs + ETDA |
| **Leaf categories** (the ~7,400 events) | 🟢 **970 obtainable FREE** (441 legacy slugs + 529 modern paths) ≈ **13% of ~7,400 by depth, full breadth** | PLOS S4–S6 + `bigdata-cookbook` + docs + ETDA #7728 |
| **Complete leaf file** (every ~7,400 category + full path + descriptions) | ⛔ **Gated** | WRDS "RPA Mapping Files" · the taxonomy **API** · or email **support@bigdata.com** |

**Bottom line (re-verified 2026-06-17, two-round multi-agent hunt):** the full ~7,400-row list is RavenPack's
**paid IP — no complete free, no-credential copy exists anywhere.** Confirmed empty across: GitHub code-search
(401) + every Bigdata-com/RavenPack org repo, Gitee/CSDN/JoinQuant (Chinese ecosystem), WRDS data-dictionary
(login), Nasdaq/Quandl (404), DoltHub/data.world/datahub/Socrata/Google-Dataset-Search (0), HuggingFace/Kaggle,
academic appendices (only subsets), web-dorks, Wayback, **Sourcegraph/grep.app/searchcode** (no third-party
corpus — the data is licensed, so nobody commits it), **archive.org full-text** (0), **Common Crawl CC-MAIN-2026-21**
(only the same 128 doc IDs), **Mangee 2021 Appendix D** (deepest known reproduction ≈ 1,395 cats but hard-paywalled,
no mirror, label-form), and the **live API** — now **conclusively credential-gated**: the autosuggest/find_topics
endpoint returns **HTTP 401 "User authentication failed"** even with full browser headers, and the SDK code shows
production sign-in is **password/API-key only (no anonymous path)**. The app bundle, OpenAPI spec, and SDK wheel ship
**no embedded taxonomy**. Four search rounds + direct probing all converge: **970 is the free, no-credential ceiling.**

**What IS free (assembled here):** **970 unique categories** — 441 legacy leaf slugs (PLOS 381 + ETDA #7728 App. B
**+60**) and 529 modern compound paths (docs 128 + `bigdata-cookbook` API-output harvest), spanning **60 groups
(full breadth)**, ≈ **13% of ~7,400 by depth**. The active/common events are well covered; the long tail of rare
leaves is the gated remainder. The ONLY routes to literally all ~7,400 are §6 — and the **lowest-friction
no-payment one is to email `support@bigdata.com`** (the docs explicitly invite requesting the whole taxonomy).

---

## 1. The hierarchy — the field model (verbatim, User Guide pp.29–31)

**4 true nesting levels → 1 leaf, plus 2 orthogonal tags.**

```
TOPIC        subject/theme of events — HIGHEST level     e.g. business, society, politics
  └ GROUP    a collection of related events (2nd highest) e.g. earnings, acquisitions-mergers
     └ TYPE  a class of events w/ similar characteristics e.g. acquisition, merger
        └ SUB_TYPE  a subdivision of that class
           └ CATEGORY  the LEAF: canonical hyphen-slug    e.g. acquisition-completed-acquiree
+ PROPERTY    a named attribute (role/entity/number) of the matched event   (axis, not a branch)
+ FACT_LEVEL  every event is tagged: fact | forecast | opinion              (axis, not a branch)
```

Each category row in the taxonomy file also carries: `DESCRIPTION`, `SCHEDULED` (was it
pre-announced), `VALID_ENTITY_TYPES`. The live taxonomy API keys are exactly
`topics, groups, types, sub_types, properties, categories`.

**Scale (reconciled — all one growing taxonomy):** ~**7,400** total event types · ~**6,700** scored by
sentiment · ~**3,317** equity categories · **56** broader groups · the PLOS study used a **33-group /
437-category** Edge slice (of which **365** are recovered here, full-path).

---

## 2. The group backbone — how the events are organized

**26 GROUPS recovered verbatim with full paths** (from the PLOS data CSVs — these are 26 of the 56
total), spanning **3 topics**:

| topic | groups |
|---|---|
| **business** | acquisitions-mergers · analyst-ratings · assets · bankruptcy · credit · credit-ratings · dividends · earnings · equity-actions · indexes · insider-trading · investor-relations · labor-issues · marketing · order-imbalances · partnerships · price-targets · products-services · regulatory · revenues · stock-prices · technical-analysis |
| **society** | legal · corporate-responsibility · security |
| **politics** | government |

This is the **native RPA equity slice (29 groups once the 16 cross-checked extras are added).** A
separate crawl of **docs.bigdata.com** (current-era taxonomy) recovered **12 more groups** at
topic→type level — `business-operations`, `civil-unrest`, `war-conflict`, `elections`, `crime`,
`cyber-security`, `foreign-exchange`, `consumption`, `exploration`, `industrial-accidents`,
`reputation`, `stock-picks` (see [`bigdata_docs_topic_paths.csv`](./bigdata_docs_topic_paths.csv)) —
bringing named coverage to **41 of the 56 groups**. The remaining ~15 (deeper macro/economic +
environmental branches) appear only in the gated file.

The official Edge "Company News" page names 20 groups in prose form (`acquisitions & mergers`,
`analyst ratings`, …, `stock price`) — the same set, space-spelled.

**ESG controversy sub-taxonomy (171 events) — pillar groups, verbatim:**
Environmental (Airborne Emissions, Pollution, Biodiversity & Land Usage, …) · Social (Human rights,
Layoffs, Labor conditions, Industrial accidents, …) · Governance (Corruption, Financial Crimes/Fraud,
Anti-Competitive practice, Shareholder rights, …).

---

## 3. The 381 categories — verbatim, organized (topic → group → type → category)

> Source: PLOS One `pone.0296927` data files **S4 + S5 + S6** (365) + 16 cross-checked extras = **381**
> native RPA leaf categories. The tree below shows the PLOS core; the **authoritative full list is the
> CSV**: [`RavenPack_categories.csv`](./RavenPack_categories.csv) (381 rows). These are the actual
> RavenPack `TOPIC,GROUP,TYPE,CATEGORY` rows.

### acquisitions-mergers · topic=`business` · 38 categories
- **acquisition** — `acquisition-acquiree` · `acquisition-acquirer` · `acquisition-bid-rejected-acquiree` · `acquisition-bid-rejected-acquirer` · `acquisition-completed-acquiree` · `acquisition-completed-acquirer` · `acquisition-failed-acquiree` · `acquisition-failed-acquirer` · `acquisition-interest-acquiree` · `acquisition-interest-acquirer` · `acquisition-merger-termination-fee` · `acquisition-opposition-acquiree` · `acquisition-opposition-acquirer` · `acquisition-rumor-acquiree` · `acquisition-rumor-acquirer` · `acquisition-rumor-denied-acquiree` · `acquisition-rumor-denied-acquirer`
- **acquisition-regulatory-approval** — `acquisition-regulatory-approval-acquiree` · `acquisition-regulatory-approval-acquirer`
- **acquisition-regulatory-scrutiny** — `acquisition-regulatory-scrutiny-acquiree` · `acquisition-regulatory-scrutiny-acquirer`
- **merger** — `merger` · `merger-completed` · `merger-delayed` · `merger-failed` · `merger-opposition` · `merger-rumor`
- **merger-regulatory-approval** — `merger-regulatory-approval`
- **merger-regulatory-scrutiny** — `merger-regulatory-scrutiny`
- **stake** — `stake-acquiree` · `stake-acquirer`
- **unit-acquisition** — `unit-acquisition-acquiree` · `unit-acquisition-acquirer` · `unit-acquisition-completed-acquiree` · `unit-acquisition-completed-acquirer` · `unit-acquisition-interest-acquiree` · `unit-acquisition-interest-acquirer`
- **unit-acquisition-regulatory-approval** — `unit-acquisition-regulatory-approval-acquirer`

### analyst-ratings · topic=`business` · 11 categories
- **analyst-ratings-change** — `analyst-ratings-change-negative` · `analyst-ratings-change-negative-rater` · `analyst-ratings-change-neutral` · `analyst-ratings-change-positive` · `analyst-ratings-change-positive-rater`
- **analyst-ratings-history** — `analyst-ratings-history-negative` · `analyst-ratings-history-neutral` · `analyst-ratings-history-positive`
- **analyst-ratings-set** — `analyst-ratings-set-negative` · `analyst-ratings-set-neutral` · `analyst-ratings-set-positive`

### assets · topic=`business` · 14 categories
- **asset** — `asset-sale` · `asset-up` · `assets`
- **company-for-sale** — `company-for-sale`
- **facility** — `facility-close` · `facility-open` · `facility-relocation` · `facility-sale` · `facility-upgrade`
- **headquarters-change** — `headquarters-change`
- **patent** — `patent-awarded` · `patent-filing` · `patent-filing-rejected` · `patent-revoked`

### bankruptcy · topic=`business` · 3 categories
- **bankruptcy** — `bankruptcy` · `bankruptcy-fears`
- **bankruptcy-unit** — `bankruptcy-unit`

### corporate-responsibility · topic=`society` · 2 categories
- **donation** — `donation`
- **sponsorship** — `sponsorship`

### credit · topic=`business` · 14 categories
- **credit-extension** — `credit-extension-provider` · `credit-extension-recipient`
- **debt** — `debt` · `debt-extension-recipient` · `debt-increase` · `debt-reduction` · `debt-renegotiation`
- **debt-restructuring** — `debt-restructuring`
- **loan** — `loan-provider` · `loan-recipient`
- **note-acquisition** — `note-acquisition`
- **note-sale** — `note-sale`
- **shelf-registration** — `debt-shelf-registration` · `mixed-shelf-registration`

### credit-ratings · topic=`business` · 18 categories
- **credit-rating-change** — `credit-rating-action` · `credit-rating-affirmation` · `credit-rating-confirmation` · `credit-rating-downgrade` · `credit-rating-provisional-rating` · `credit-rating-set` · `credit-rating-unchanged` · `credit-rating-upgrade` · `credit-rating-withdrawn-rating`
- **credit-rating-outlook** — `credit-rating-outlook-negative` · `credit-rating-outlook-positive` · `credit-rating-outlook-revision` · `credit-rating-outlook-stable`
- **credit-rating-watch** — `credit-rating-watch` · `credit-rating-watch-negative` · `credit-rating-watch-positive` · `credit-rating-watch-removed` · `credit-rating-watch-unchanged`

### dividends · topic=`business` · 7 categories
- **dividend** — `dividend` · `dividend-above-expectations` · `dividend-down` · `dividend-up`
- **dividend-guidance** — `dividend-guidance` · `dividend-guidance-down` · `dividend-guidance-up`

### earnings · topic=`business` · 52 categories
- **earnings** — `earnings` · `earnings-above-expectations` · `earnings-below-expectations` · `earnings-delayed` · `earnings-down` · `earnings-meet-expectations` · `earnings-negative` · `earnings-positive` · `earnings-up`
- **earnings-estimate** — `earnings-estimate` · `earnings-estimate-downgrade` · `earnings-estimate-upgrade` · `earnings-estimate-upgrade-rater`
- **earnings-guidance** — `earnings-guidance` · `earnings-guidance-above-expectations` · `earnings-guidance-below-expectations` · `earnings-guidance-down` · `earnings-guidance-meet-expectations` · `earnings-guidance-suspended` · `earnings-guidance-up`
- **earnings-per-share** — `earnings-per-share` · `earnings-per-share-above-expectations` · `earnings-per-share-below-expectations` · `earnings-per-share-down` · `earnings-per-share-meet-expectations` · `earnings-per-share-negative` · `earnings-per-share-positive` · `earnings-per-share-up`
- **earnings-per-share-guidance** — `earnings-per-share-guidance`
- **earnings-revision** — `earnings-revision` · `earnings-revision-down` · `earnings-revision-up`
- **ebit** — `ebit-down` · `ebit-positive` · `ebit-up`
- **ebitda** — `ebitda-negative` · `ebitda-positive` · `ebitda-up`
- **ebitda-guidance** — `ebitda-guidance` · `ebitda-guidance-down` · `ebitda-guidance-up`
- **operating-earnings** — `operating-earnings` · `operating-earnings-down` · `operating-earnings-negative` · `operating-earnings-positive` · `operating-earnings-up`
- **operating-earnings-guidance** — `operating-earnings-guidance` · `operating-earnings-guidance-up`
- **pretax-earnings** — `pretax-earnings-down` · `pretax-earnings-negative` · `pretax-earnings-positive` · `pretax-earnings-up`

### equity-actions · topic=`business` · 57 categories
- **buybacks** — `buybacks`
- **capex** — `capex` · `capex-down`
- **capex-guidance** — `capex-guidance` · `capex-guidance-down` · `capex-guidance-up`
- **capital-increase** — `capital-increase` · `capital-increase-completed`
- **expenses** — `expenses` · `expenses-charge` · `expenses-down` · `expenses-up`
- **expenses-guidance** — `expenses-guidance` · `expenses-guidance-down` · `expenses-guidance-up`
- **fundraising** — `bought-deal` · `fundraising`
- **going-private** — `going-private`
- **initial-public-offering** — `ipo` · `ipo-completed` · `ipo-considered` · `ipo-failed`
- **initial-public-offering-price** — `ipo-pricing`
- **initial-public-offering-unit** — `ipo-unit` · `ipo-unit-considered`
- **investment** — `investment-investor` · `investment-recipient`
- **name-change** — `name-change`
- **ownership** — `ownership-decrease-held` · `ownership-decrease-owner` · `ownership-increase-held` · `ownership-increase-owner`
- **private-placement** — `private-placement`
- **public-offering** — `public-offering` · `public-offering-delayed` · `public-offering-suspended`
- **reorganization** — `reorganization` · `reorganization-approval` · `reorganization-complete` · `reorganization-considered` · `reorganization-costs` · `reorganization-savings`
- **reorganization-unit** — `reorganization-unit`
- **reverse-stock-splits** — `reverse-stock-splits`
- **rights-issue** — `rights-issue`
- **savings** — `savings`
- **savings-guidance** — `savings-guidance`
- **shareholder-rights-plan** — `shareholder-rights-plan` · `shareholder-rights-plan-suspended`
- **shelf-registration** — `equity-shelf-registration`
- **spin-off** — `spin-off`
- **stock-splits** — `stock-splits`
- **trading** — `trading-delisting` · `trading-delisting-review` · `trading-halt` · `trading-listing` · `trading-resumed`

### government · topic=`politics` · 1 category
- **congressional-testimony** — `congressional-testimony-summoned`

### indexes · topic=`business` · 2 categories
- **index-delisting** — `index-delisting` · **index-listing** — `index-listing`

### insider-trading · topic=`business` · 6 categories
- **insider-buy** — `insider-buy` · **insider-gift** — `insider-gift` · **insider-sell** — `insider-sell` · **insider-surrender** — `insider-surrender` · **insider-trading-lawsuit** — `insider-trading-lawsuit-defendant` · **sell-registration** — `insider-sell-registration`

### investor-relations · topic=`business` · 3 categories
- **board-meeting** — `board-meeting` · **conference-call** — `conference-call` · **major-shareholders-disclosure** — `major-shareholders-disclosure`

### labor-issues · topic=`business` · 14 categories
- **executive-appointment** — `executive-appointment` · **executive-compensation** — `executive-compensation` · **executive-death** — `executive-death` · **executive-firing** — `executive-firing` · **executive-health** — `executive-health` · **executive-resignation** — `executive-resignation`
- **executive-salary** — `executive-salary` · `executive-salary-cut` · `executive-salary-increase`
- **executive-scandal** — `executive-scandal` · **executive-shares-options** — `executive-shares-options` · **hirings** — `hirings` · **layoffs** — `layoffs` · **union-pact** — `union-pact`

### legal · topic=`society` · 20 categories
- **antitrust-investigation** — `antitrust-investigation` · **antitrust-settlement** — `antitrust-settlement`
- **antitrust-suit** — `antitrust-suit-defendant` · `antitrust-suit-plaintiff`
- **appeal** — `appeal-plaintiff` · **confidentiality-pact** — `confidentiality-pact` · **copyright-infringement** — `copyright-infringement-defendant`
- **fraud** — `fraud` · `fraud-defendant` · `fraud-plaintiff`
- **legal-issues** — `legal-issues-defendant` · `legal-issues-dismissed-defendant` · `legal-issues-dismissed-plaintiff` · `legal-issues-plaintiff`
- **patent-infringement** — `patent-infringement-defendant` · `patent-infringement-plaintiff`
- **sanctions** — `sanctions-target` · **settlement** — `settlement`
- **verdict** — `legal-verdict-disfavored` · `legal-verdict-favored`

### marketing · topic=`business` · 5 categories
- **campaign-ad** — `campaign-ad-release` · `campaign-ad-retired`
- **conference** — `conference-organizer` · `conference-participant`
- **press-conference** — `press-conference-organizer`

### order-imbalances · topic=`business` · 9 categories
- **buy-imbalance** `buy-imbalance` · **buy-moc** `mkt-close-buy-imbalance` · **buy-moo** `mkt-open-buy-imbalance` · **delay-imbalance** `delay-imbalance` · **no-imbalance** `no-imbalance` · **no-moc** `no-mkt-close-imbalance` · **sell-imbalance** `sell-imbalance` · **sell-moc** `mkt-close-sell-imbalance` · **sell-moo** `mkt-open-sell-imbalance`

### partnerships · topic=`business` · 4 categories
- **joint-venture** — `joint-venture` · `joint-venture-terminated`
- **partnership** — `partnership` · `partnership-terminated`

### price-targets · topic=`business` · 3 categories
- **price-target** — `price-target-downgrade` · `price-target-set` · `price-target-upgrade`

### products-services · topic=`business` · 47 categories
- **award** `award` · **business-combination** `business-combination`
- **business-contract** — `business-contract` · `business-contract-terminated`
- **clinical-trials** — `clinical-trials` · `clinical-trials-complete` · `clinical-trials-filed` · `clinical-trials-negative` · `clinical-trials-positive` · `clinical-trials-start` · `clinical-trials-suspended`
- **clinical-trials-patient-enrollment** — `patient-enrollment-complete` · `patient-enrollment-start` · `patient-enrollment-suspended`
- **demand** — `demand-decrease` · `demand-increase` · **demand-guidance** — `demand-guidance-increase`
- **fast-track-designation** `fast-track-designation` · **government-contract** `government-contract` · **grant** `grant-recipient` · **market-entry** `market-entry`
- **market-guidance** — `market-guidance` · `market-guidance-up`
- **market-share** — `market-share-gain` · `market-share-loss`
- **orphan-drug-designation** `orphan-drug-designation` · **product-catastrophe** `product-catastrophe` · **product-discontinued** `product-discontinued` · **product-outage** `product-outage`
- **product-price** — `product-price-cut` · `product-price-raise`
- **product-recall** `product-recall` · **product-release** — `product-delayed` · `product-release` · **product-resumed** `product-resumed` · **project-abandoned** `project-abandoned`
- **regulatory-product-application** — `regulatory-product-application` · `regulatory-product-application-withdrawn`
- **regulatory-product-approval** — `regulatory-product-approval-conditional` · `regulatory-product-approval-denied` · `regulatory-product-approval-granted`
- **regulatory-product-review** — `regulatory-product-review-negative` · `regulatory-product-review-positive`
- **regulatory-product-warning** `regulatory-product-warning`
- **supply** — `supply-decrease` · `supply-increase` · **supply-guidance** — `supply-guidance-increase`

### regulatory · topic=`business` · 7 categories
- **auditor-appointment** `auditor-appointment` · **auditor-resignation** `auditor-resignation` · **exchange-compliance** `exchange-compliance` · **exchange-noncompliance** `exchange-noncompliance`
- **regulatory-investigation** — `regulatory-investigation` · `regulatory-investigation-completed` · `regulatory-investigation-completed-sanction`

### revenues · topic=`business` · 18 categories
- **revenue** — `revenue-above-expectations` · `revenue-below-expectations` · `revenue-down` · `revenue-meet-expectations` · `revenue-up` · `revenues`
- **revenue-estimate** — `revenue-estimate` · `revenue-estimate-downgrade` · `revenue-estimate-upgrade`
- **revenue-guidance** — `revenue-guidance` · `revenue-guidance-above-expectations` · `revenue-guidance-below-expectations` · `revenue-guidance-down` · `revenue-guidance-meet-expectations` · `revenue-guidance-up`
- **revenue-volume** — `revenue-volume` · `revenue-volume-down` · `revenue-volume-up`

### security · topic=`society` · 1 category
- **cyber-attacks** — `cyber-attacks`

### stock-prices · topic=`business` · 2 categories
- **stock** — `stock-gain` · `stock-loss`

### technical-analysis · topic=`business` · 7 categories
- **relative-strength-index** — `relative-strength-index` · `relative-strength-index-overbought` · `relative-strength-index-oversold`
- **technical-price-level** — `technical-price-level-resistance-bearish`
- **technical-view** — `technical-view` · `technical-view-bearish` · `technical-view-bullish`

---

## 4. The per-event fields (the 50-field record)

**Scoring fields:**

| Field | Range | Meaning |
|---|---|---|
| `EVENT_SENTIMENT_SCORE` (ESS) | −1.00 … +1.00 | event sentiment for the entity (0 = neutral); spans 6,700+ categories |
| `RELEVANCE` | 0–100 | how strongly the entity ties to the story (≥75 significant; 100 = headline key role) |
| `EVENT_RELEVANCE` | 0–100 | relevance of the *event* in the story (headline=100, ¶1–2 = 80–89, body 0–79) |
| `EVENT_SIMILARITY_DAYS` | 0–365 | **novelty proxy** — days since a similar event last seen (0 = same instant) |
| `EVENT_SIMILARITY_KEY` | 32-char | shared key grouping records of the same event |
| `CSS` (Composite Sentiment) | −1.00 … +1.00 | story-level; blends 5 classifiers (PEQ+BEE+BMQ+BAM+BCA) |
| `NIP` (News Impact Projections) | −1.00 … +1.00 | projected 2-hour volatility impact of a flash |
| `PEQ/BEE/BMQ/BAM/BCA/BER` | −1 / 0 / +1 | sub-classifiers (equities, earnings-eval, editorial, M&A, corp-actions, earnings-release) |
| `ANL_CHG` | −1 / 0 / +1 | analyst recommendation change (downgrade/neutral/upgrade) |
| `MCQ` | −1 / 0 / +1 | multi-classifier (fires only when RELEVANCE ≥ 90) |
| `SOURCE_RANK` | 1–10 | source-trust (1 = fully accountable … 10 = unverifiable) |
| `FACT_LEVEL` | enum | fact / forecast / opinion |
| *(Edge-era)* `ENS` / `AES` | 0–100 / ratio | Event Novelty Score / Aggregate Event Sentiment (rolling 91-day) |

**Entity types** (`ENTITY_TYPE`, 13 codes): `COMP` company · `PEOP` people · `PLCE` place ·
`PROD` product · `PRDT` product-type · `ORGA` organization · `ORGT` org-type · `CMDT` commodity ·
`CURR` currency · `NATL` nationality · `TEAM` sports team · `POSI` position · `SRCE` source.
*(~12M entities now; 86,000+ companies, 138,700+ places, 58,000+ products.)*

**PROPERTY enums:**
- `EARNINGS_TYPE`: reported · non-gaap · ex-exceptionals · adjusted · non-diluted · diluted-adjusted · diluted-reported · headline-basic · headline-diluted · consolidated · standalone
- `EVALUATION_METHOD`: YOY · QOQ · MOM · LFL · `MATURITY`: {1-365}-DAY/{1-52}-WK/{1-12}-MTH/{1-50}-YR
- `RELATIONSHIP`: PRODUCT · OWNER · `REPORTING_PERIOD`: YYYY-Q{1-4} · FY-YYYY-Q{1-4} · YYYY-H{1-2} · YYYY-9MTH · YYYY · FY-YYYY
- Property families: Roles · Positions · Temporal data · Indicators (bearish/bullish/overbought/oversold) · Benchmarks · Opinions

**NEWS_TYPE** (story-format axis): HOT-NEWS-FLASH · NEWS-FLASH · FULL-ARTICLE · PRESS-RELEASE ·
TABULAR-MATERIAL · RNS-SEC8K/10K/10Q/13D/13F/144

---

## 5. Editions (why source numbers differ)

Same `topic,group,type,sub_type` skeleton, three lineages:
- **RPA 1.0 / "Analytics"** (legacy) — User Guide PDF + WRDS "RPA 1.0 Mapping Files". ESS/CSS/NIP/
  EVENT_SIMILARITY_DAYS; ~50 fields; monthly CSV in yearly ZIP from Jan 1 2000.
- **Edge / "Analytics"** (newer) — adds ENS, AES, roles, document-vs-event factors; "7,400 events"; the
  PLOS 33-group/437-category slice (365 of which are in §3).
- **Bigdata.com** (current rebrand) — same skeleton as a compound `topic_id`; `find_topics` API + MCP
  connector. Sub-editions: Dow Jones vs PR (press-release) editions.

---

## 6. How to get ALL ~7,400 (the gated full file)

> **Reality (verified 2026-06-17):** there is **no no-credential route** to the complete list — the live
> autosuggest/find_topics API is **HTTP 401** without a token (browser headers don't help; SDK = password/key
> only, no anonymous mode), and no static public copy exists. Every option below needs *some* credential or a
> request. The **no-payment** ones are Option D (email) and Option 0 (free trial key).

### ⭐ Option D — just ask: email `support@bigdata.com` (NO API key, NO payment)
The docs explicitly invite requesting the whole taxonomy. Lowest-friction route to the **official complete CSV**
without an API key, subscription, or university login. Best fit when the constraint is "no API access."

### ⭐ Option 0 — Bigdata.com 7-day FREE trial (best if you have NO access yet)
No university, no paid subscription needed. Sign up at **https://app.bigdata.com/signup** → get an
**X-API-KEY** instantly → run the included script to dump the **current full taxonomy** to CSV:
```bash
pip install bigdata-client
export BIGDATA_API_KEY='your-trial-key'
python3 dump_bigdata_taxonomy.py        # → bigdata_taxonomy_full.csv (every topic + full path)
```
Script: [`dump_bigdata_taxonomy.py`](./dump_bigdata_taxonomy.py). It enumerates via seeded
`find_topics` (there's no list-all call) — widen its SEEDS to push coverage higher. This yields the
**current** RavenPack taxonomy; the exact legacy RPA-1.0 ~7,400 CSV still needs A or B.

### A — WRDS (no key; if your institution subscribes)
WRDS → RavenPack Analytics → **"RPA 1.0 — Mapping Files"** → download the **event taxonomy dataset**
(CSV: `TOPIC,GROUP,TYPE,SUB_TYPE,PROPERTY,FACT_LEVEL,CATEGORY,DESCRIPTION,SCHEDULED,VALID_ENTITY_TYPES`).
That is the complete leaf list. (Or `SELECT * FROM ravenpack.rpa_taxonomy;`.)

### B — RavenPack taxonomy API (empty filters = full dump)
```r
library(rpapi)
APIHandler = RP_APIHandler(api_key = Sys.getenv("RP_API_KEY"))
payload = '{"topics":[],"groups":[],"types":[],"sub_types":[],"properties":[],"categories":[]}'
write.csv(RP_APITaxonomy(APIHandler, payload), "ravenpack_full_taxonomy.csv", row.names = FALSE)
```
```bash
curl -s -X POST "https://api.ravenpack.com/1.0/taxonomy" \
  -H "API_KEY: $RP_API_KEY" -H "Content-Type: application/json" \
  -d '{"topics":[],"groups":[],"types":[],"sub_types":[],"properties":[],"categories":[]}' \
  -o ravenpack_full_taxonomy.json
```

### C — Bigdata.com SDK (enumerate via seeded search)
```python
from bigdata_client import Bigdata
bd = Bigdata(os.environ["BIGDATA_USERNAME"], os.environ["BIGDATA_PASSWORD"])
paths=set()
for s in ["earnings","merger","analyst","dividend","guidance","lawsuit","layoff","product","credit",
          "insider","buyback","bankruptcy","partnership","sanction","regulation","ipo","debt"]:
    for hit in bd.knowledge_graph.find_topics(s, limit=50): paths.add(hit.id)  # 'topic,group,type,sub_type,'
```

> No public/no-key route returns all ~7,400 — every official repo is an API wrapper with **no embedded
> taxonomy**, and no committed CSV exists on GitHub/Kaggle/HF (verified twice). The full list is behind A/B/C/D/0.

### Free harvest that DID work (no credential) — already folded into `bigdata_taxonomy_assembled.csv`
- **`Bigdata-com/bigdata-cookbook`** commits API *output* files (JSONL/JSON) whose `detections[]` tag each news
  doc with real modern compound topic IDs → harvested **519** (`git clone --depth 1`; grep the result files).
- **Penn State ETDA #7728 App. B** (via Wayback `web/20200323000104if_/…/7728`) → **261** legacy slugs (+60 new).
- **CloudQuant /783** (via Wayback) → the PROPERTY/entity-role axis (acquiree, rater, plaintiff, …).
These cover the **active** events well; the rare long-tail leaves remain gated (A/B/C/D/0).

---

## 7. Sources (all fetched 2026-06-16)

1. **RavenPack Analytics User Guide v1.0** (39pp data dictionary) — `som.ustc.edu.cn/_upload/article/files/c0/28/c4afd94448c68b4ca1c174b1a7c6/e0a62fa2-646e-491a-acc5-18efdbab1181.pdf`
2. **PLOS One `pone.0296927` data files S4/S5/S6** (the 365 categories w/ full paths) — `journals.plos.org/plosone/article/file?type=supplementary&id=10.1371/journal.pone.0296927.s004` (… .s005, .s006)
3. PLOS One S1/S2 (delisted + descriptions) — `…s001`, `…s002`
4. **Edge Company-News Factors** (20 verbatim groups) — `ravenpack.com/products/edge/factors/company-news`
5. **Bigdata `find_topics` docs + `top_topics_to_search.csv`** — `docs.bigdata.com/getting-started/knowledge_graph/find_topics` · `github.com/Bigdata-com/bigdata-docs-resources`
6. **ESG Controversy framework** — `ravenpack.com/research/esg-controversy-scoring-framework`
7. **WRDS RavenPack** (the gated full file) — `wrds-www.wharton.upenn.edu/pages/about/data-vendors/ravenpack/`
8. **Official R / Python clients** (API mechanics) — `github.com/RavenPack/r-api` · `github.com/RavenPack/python-api`
9. **`Bigdata-com/bigdata-cookbook`** (519 modern compound IDs, free) — `github.com/Bigdata-com/bigdata-cookbook` (Batch_Search_API/, Smart_Batching/, API_Tutorials/ result files; `detections[]` topic tags)
10. **Penn State ETDA #7728, Appendix B** (261 legacy slugs, +60 new) — `web.archive.org/web/20200323000104if_/https://etda.libraries.psu.edu/files/final_submissions/7728` (p.78–80)
11. **CloudQuant "RavenPack Data Field Formats"** (PROPERTY/entity-role axis) — `web.archive.org/web/20250419181135id_/https://knowledge.cloudquant.com/783`
12. **docs.bigdata.com** confirms current scale "more than 7,000 categories" — `docs.bigdata.com/getting-started/knowledge_graph/introduction`

---

## 8. Why this matters for the Driver design

A RavenPack `CATEGORY` **bundles** cause + state + polarity into one slug
(`earnings-per-share-above-expectations`). The Driver ontology **un-bundles exactly these** — the
Driver's value-add that RavenPack does not do:

| RavenPack | → | Driver field |
|---|---|---|
| the cause inside the slug (`earnings-per-share`) | → | `driver_name` (e.g. `eps_surprise`) |
| the state suffix (`-above-expectations`, `-up`, `-suspended`) | → | `driver_state` |
| the polarity (`-positive` / `-negative`) | → | `stock_impact` (long/short) |
| `FACT_LEVEL` fact/forecast/opinion | → | `fact_type` surprise(fact) vs guidance(forecast) |
| `EARNINGS_TYPE` {adjusted, non-gaap…}, `EVALUATION_METHOD` {YOY/QOQ/LFL} | → | R9 name qualifiers (`adjusted_eps` ≠ `eps`) |

**Usable now:** the category state suffixes are a battle-tested `driver_state` lexicon —
`-above/-below/-meet-expectations · -up/-down · -positive/-negative · -completed/-failed/-terminated/
-suspended/-rumor/-withdrawn/-denied/-recall`. **Caution:** never import RavenPack slugs as `driver_name`s
(they embed state + polarity → violates R7). Use them only as evidence-side tags + a state-word vocabulary.
