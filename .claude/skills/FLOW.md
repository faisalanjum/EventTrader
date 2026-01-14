# Earnings Skills Infrastructure & Data Flow

> Complete architecture documentation for earnings-prediction and earnings-attribution skills.

---

## 1. HIGH-LEVEL ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              EARNINGS ANALYSIS SYSTEM                                    │
│                                  (claude-opus-4-5)                                       │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│    ┌──────────────────────┐                    ┌──────────────────────┐                │
│    │  EARNINGS-PREDICTION │                    │ EARNINGS-ATTRIBUTION │                │
│    │    (Forward-Looking) │                    │   (Backward-Looking) │                │
│    │                      │                    │                      │                │
│    │  • Run BEFORE market │                    │  • Run AFTER market  │                │
│    │  • PIT filtering ON  │                    │  • PIT filtering OFF │                │
│    │  • Predicts T=0 move │                    │  • Explains WHY moved│                │
│    └──────────┬───────────┘                    └──────────┬───────────┘                │
│               │                                           │                            │
│               │ MANDATORY                                 │ OPTIONAL                   │
│               ▼                                           ▼                            │
│    ┌──────────────────────┐                    ┌──────────────────────┐                │
│    │    FILTERED-DATA     │                    │   DIRECT SUB-AGENT   │                │
│    │   (Filter Gateway)   │                    │       CALLS          │                │
│    │                      │                    │                      │                │
│    │  • Validates PIT     │                    │  • No PIT validation │                │
│    │  • Blocks returns    │                    │  • Full return data  │                │
│    │  • Routes to agents  │                    │  • All timeframes    │                │
│    └──────────┬───────────┘                    └──────────┬───────────┘                │
│               │                                           │                            │
│               └───────────────────┬───────────────────────┘                            │
│                                   ▼                                                    │
│    ┌────────────────────────────────────────────────────────────────────────────┐     │
│    │                         SUB-AGENT LAYER (Task Tool)                         │     │
│    ├────────────────────────────────────────────────────────────────────────────┤     │
│    │                                                                            │     │
│    │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │     │
│    │  │neo4j-report │ │ neo4j-xbrl  │ │neo4j-news   │ │neo4j-entity │          │     │
│    │  │             │ │             │ │             │ │             │          │     │
│    │  │ • 8-K/10-K  │ │ • EPS/Rev   │ │ • Headlines │ │ • Dividends │          │     │
│    │  │ • EX-99.1   │ │ • Quarters  │ │ • Sentiment │ │ • Splits    │          │     │
│    │  │ • Sections  │ │ • Segments  │ │ • ±N days   │ │ • Prices    │          │     │
│    │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘          │     │
│    │                                                                            │     │
│    │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │     │
│    │  │neo4j-trans. │ │perplexity-  │ │perplexity-  │ │perplexity-  │          │     │
│    │  │             │ │search       │ │ask/reason   │ │research     │          │     │
│    │  │ • Q&A calls │ │             │ │             │ │             │          │     │
│    │  │ • Prepared  │ │ • Raw URLs  │ │ • Facts     │ │ • Deep dive │          │     │
│    │  │ • Remarks   │ │ • Consensus │ │ • Why?      │ │ • 20+ srcs  │          │     │
│    │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘          │     │
│    │                                                                            │     │
│    └────────────────────────────────────────────────────────────────────────────┘     │
│                                   │                                                    │
│                                   ▼                                                    │
│    ┌────────────────────────────────────────────────────────────────────────────┐     │
│    │                           DATA LAYER                                        │     │
│    ├────────────────────────────────────────────────────────────────────────────┤     │
│    │  ┌──────────────────────────────────┐  ┌────────────────────────────────┐  │     │
│    │  │        NEO4J DATABASE            │  │      PERPLEXITY API            │  │     │
│    │  │     (minisforum3:30687)          │  │       (Web Search)             │  │     │
│    │  │                                  │  │                                │  │     │
│    │  │  • 796 Companies                 │  │  • Consensus estimates         │  │     │
│    │  │  • 32K+ Reports                  │  │  • Analyst commentary          │  │     │
│    │  │  • 9.9M XBRL Facts               │  │  • News articles               │  │     │
│    │  │  • 864K News→Company links       │  │  • SEC filings (EDGAR)         │  │     │
│    │  │  • 4,387 Transcripts             │  │                                │  │     │
│    │  └──────────────────────────────────┘  └────────────────────────────────┘  │     │
│    └────────────────────────────────────────────────────────────────────────────┘     │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. EARNINGS-PREDICTION FLOW

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           EARNINGS-PREDICTION SKILL (v1.6)                              │
│                      Model: claude-opus-4-5 | Reasoning: ultrathink                     │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  INPUT: Accession Number (8-K filing with Item 2.02)                                   │
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 1: GET FILING METADATA                                                      │   │
│  │                                                                                  │   │
│  │ YOU ──────▶ /filtered-data ──────▶ neo4j-report ──────▶ NEO4J                   │   │
│  │      --agent neo4j-report                                                        │   │
│  │      --query "8-K {accession} metadata"                                          │   │
│  │                                                                                  │   │
│  │ EXTRACTS: ticker, filing_datetime (THIS IS YOUR PIT), items                     │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                         │                                               │
│                                         ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 2: GET ACTUAL RESULTS (EX-99.1 Press Release)                              │   │
│  │                                                                                  │   │
│  │ YOU ──────▶ /filtered-data ──────▶ neo4j-report ──────▶ NEO4J                   │   │
│  │      --query "EX-99.1 content for {accession}"                                   │   │
│  │                                                                                  │   │
│  │ EXTRACTS: Actual EPS, Actual Revenue, Forward Guidance, One-time items          │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                         │                                               │
│                                         ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 3: GET HISTORICAL CONTEXT (5 PARALLEL QUERIES - ALL PIT FILTERED)          │   │
│  │                                                                                  │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                  │   │
│  │  │ 3A: neo4j-xbrl  │  │ 3B: neo4j-trans │  │ 3C: neo4j-news  │                  │   │
│  │  │ Last 4Q EPS/Rev │  │ Last 2 calls    │  │ 30-day pre-news │                  │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘                  │   │
│  │  ┌─────────────────┐  ┌─────────────────┐                                       │   │
│  │  │ 3D: neo4j-entity│  │ 3E: perplexity  │◀── CONSENSUS ESTIMATES                │   │
│  │  │ Dividends 90d   │  │     -search     │                                       │   │
│  │  └─────────────────┘  └─────────────────┘                                       │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                         │                                               │
│                                         ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 4: CALCULATE SURPRISE                                                       │   │
│  │                                                                                  │   │
│  │   SURPRISE % = ((Actual - Consensus) / |Consensus|) × 100                        │   │
│  │                                                                                  │   │
│  │   MAGNITUDE: SMALL (0-2%) | MEDIUM (2-5%) | LARGE (5%+)                         │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                         │                                               │
│                                         ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 5: MAKE PREDICTION                                                          │   │
│  │                                                                                  │   │
│  │ OUTPUT: Direction (UP/DOWN) + Magnitude + Confidence + Primary Reason           │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                         │                                               │
│                                         ▼                                               │
│  OUTPUT: Append to predictions.csv (actual_* columns filled by attribution later)      │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. FILTERED-DATA VALIDATION FLOW

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              FILTERED-DATA AGENT FLOW                                   │
│                         (Mandatory Gateway for Predictions)                             │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  INPUT: /filtered-data --agent {AGENT} --query "[PIT: datetime] {query}"               │
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 1: PARSE ARGUMENTS                                                          │   │
│  │   Extract: AGENT, QUERY, PIT                                                     │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                         │                                               │
│                                         ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 2: FETCH DATA (Route to Sub-Agent)                                          │   │
│  │                                                                                  │   │
│  │   ALLOWED: neo4j-report, neo4j-xbrl, neo4j-news, neo4j-entity,                  │   │
│  │            neo4j-transcript, perplexity-*                                        │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                         │                                               │
│                                         ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │ STEP 3: VALIDATE RESPONSE (ALWAYS RUNS)                                          │   │
│  │                                                                                  │   │
│  │  CHECK 1: FORBIDDEN PATTERNS (Neo4j only)                                        │   │
│  │  ┌──────────────────────────────────────────────────────────────────────────┐   │   │
│  │  │ ❌ daily_stock    ❌ hourly_stock    ❌ session_stock                     │   │   │
│  │  │ ❌ daily_return   ❌ daily_macro     ❌ daily_industry                    │   │   │
│  │  │ ❌ daily_sector   ❌ hourly_macro    ❌ hourly_industry/sector            │   │   │
│  │  └──────────────────────────────────────────────────────────────────────────┘   │   │
│  │                                                                                  │   │
│  │  CHECK 2: PIT COMPLIANCE (if PIT specified)                                      │   │
│  │  ┌──────────────────────────────────────────────────────────────────────────┐   │   │
│  │  │ Neo4j: created, conference_datetime, declaration_date                    │   │   │
│  │  │ Perplexity: "Date:" lines                                                │   │   │
│  │  │ If DATE > PIT → CONTAMINATED:PIT_VIOLATION                               │   │   │
│  │  └──────────────────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────────────┘   │
│                                         │                                               │
│                         ┌───────────────┴───────────────┐                              │
│                         ▼                               ▼                              │
│              [VALIDATED:CLEAN]                [VALIDATED:CONTAMINATED]                 │
│              Return full data                 Return error / Retry                     │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. EARNINGS-ATTRIBUTION FLOW

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          EARNINGS-ATTRIBUTION SKILL (v4.2)                              │
│                      Model: claude-opus-4-5 | Reasoning: ultrathink                     │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  INPUT: Accession Number (8-K - AFTER market reaction)                                 │
│                                                                                         │
│  STEP 1: DATA INVENTORY ──▶ neo4j-report ──▶ Check what exists                        │
│                                                                                         │
│  STEP 2: GET REPORT + RETURNS ──▶ neo4j-report ──▶ Full return data                   │
│          (daily_stock, daily_macro, daily_adj, sector, industry)                       │
│                                                                                         │
│  STEP 3: GET CONSENSUS ──▶ perplexity-search ──▶ Pre-filing estimates                 │
│                                                                                         │
│  STEP 4: QUERY NEO4J (5 PARALLEL)                                                      │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐                          │
│  │ neo4j-news ±5d  │ │ neo4j-transcript│ │ neo4j-xbrl 4Q   │                          │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘                          │
│  ┌─────────────────┐ ┌─────────────────┐                                              │
│  │ neo4j-entity    │ │ VERIFY coverage │                                              │
│  └─────────────────┘ └─────────────────┘                                              │
│                                                                                         │
│  STEP 5: QUERY PERPLEXITY (FALLBACK)                                                   │
│          search → ask → reason → research (escalation)                                 │
│                                                                                         │
│  STEP 6: SYNTHESIZE & CALCULATE SURPRISES                                              │
│          EPS/Revenue/Guidance Surprise % = ((Actual-Consensus)/|Consensus|)×100        │
│                                                                                         │
│  STEP 7: OUTPUT REPORT ──▶ earnings-analysis/Companies/{TICKER}/{accession}.md        │
│                                                                                         │
│  STEP 8: SELF-AUDIT ──▶ evidence_audit.md checklist                                   │
│                                                                                         │
│  STEP 9: PROPOSE SKILL UPDATES ──▶ Generic learnings only                             │
│                                                                                         │
│  STEP 10: UPDATE TRACKING ──▶ predictions.csv (actual_* columns)                      │
│                               learnings.md (company patterns)                          │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. SUB-AGENT HIERARCHY

```
                              ┌──────────────────┐
                              │      USER        │
                              └────────┬─────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                      ▼
         ┌──────────────────┐                   ┌──────────────────┐
         │ /earnings-       │                   │ /earnings-       │
         │  prediction      │                   │  attribution     │
         └────────┬─────────┘                   └────────┬─────────┘
                  │                                      │
                  │ via filtered-data                    │ direct calls
                  ▼                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         NEO4J SUB-AGENTS (5)                                │
│                                                                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │neo4j-report │ │neo4j-xbrl   │ │neo4j-news   │ │neo4j-entity │           │
│  │             │ │             │ │             │ │             │           │
│  │ 32K Reports │ │ 9.9M Facts  │ │ 864K links  │ │ 796 Cos     │           │
│  │ 30K Exhibits│ │ 467K Concept│ │ 3072d vecs  │ │ 4K Dividends│           │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘           │
│                                                                             │
│  ┌─────────────┐                                                            │
│  │neo4j-trans. │    All query NEO4J via MCP (neo4j-cypher)                 │
│  │ 4,387 Trans │                                                            │
│  └─────────────┘                                                            │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                       PERPLEXITY SUB-AGENTS (5)                             │
│                                                                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │perplexity-  │ │perplexity-  │ │perplexity-  │ │perplexity-  │           │
│  │search       │ │ask          │ │reason       │ │research     │           │
│  │             │ │             │ │             │ │             │           │
│  │ Raw URLs    │ │ sonar-pro   │ │ DeepSeek-R1 │ │ 20+ sources │           │
│  │ CONSENSUS   │ │ Quick facts │ │ "Why" Q's   │ │ Deep dives  │           │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘           │
│                                                                             │
│  ┌─────────────┐                                                            │
│  │perplexity-  │    All query PERPLEXITY API via MCP                       │
│  │sec (EDGAR)  │                                                            │
│  └─────────────┘                                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. NEO4J SCHEMA (Key Relationships)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ENTITY HIERARCHY                                  │
│                                                                             │
│  MarketIndex (SPY) ◀── BELONGS_TO ── Sector (11) ◀── Industry (~115)       │
│                                          ▲                                  │
│                                     BELONGS_TO                              │
│                                          │                                  │
│                                     Company (796)                           │
│                                          │                                  │
│         ┌────────────────────────────────┼────────────────────────────────┐ │
│         │                                │                                │ │
│         ▼                                ▼                                ▼ │
│  ┌─────────────┐                  ┌─────────────┐                ┌────────┐│
│  │   Report    │──PRIMARY_FILER──▶│   Company   │◀──INFLUENCES───│  News  ││
│  │   (32K+)    │  (with returns)  │             │  (with returns)│ (864K) ││
│  │             │                  │             │                │        ││
│  │  .formType  │                  │  .ticker    │                │.created││
│  │  .created   │◀── PIT DATE      │  .cik       │                │.title  ││
│  │  .items     │                  │             │                │.body   ││
│  └──────┬──────┘                  └─────────────┘                └────────┘│
│         │                                │                                 │
│  HAS_EXHIBIT                        DECLARED_*                             │
│  HAS_SECTION                             │                                 │
│  HAS_XBRL                    ┌───────────┴───────────┐                     │
│         │                    ▼                       ▼                     │
│         ▼             ┌─────────────┐         ┌─────────────┐              │
│  ┌─────────────┐      │  Dividend   │         │   Split     │              │
│  │  XBRLNode   │      │   (4,282)   │         │    (33)     │              │
│  │   (8,189)   │      │             │         │             │              │
│  └──────┬──────┘      │.declaration │◀── PIT  │.execution   │◀── PIT      │
│         │             │  _date      │         │  _date      │              │
│    REPORTS            │.cash_amount │         │.split_from  │              │
│         │             └─────────────┘         │.split_to    │              │
│         ▼                                     └─────────────┘              │
│  ┌─────────────┐                                                           │
│  │    Fact     │ (9.9M)                                                    │
│  │             │                                                           │
│  │  .value     │◀── STRING (use toFloat())                                │
│  │  .qname     │                                                           │
│  │  .is_numeric│◀── "1" or "0"                                            │
│  └──────┬──────┘                                                           │
│         │                                                                  │
│  HAS_CONCEPT ──▶ Concept (467K) ──▶ us-gaap:NetIncomeLoss, etc.           │
│  IN_CONTEXT ──▶ Context ──▶ Period (instant/duration)                     │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. PREDICTION vs ATTRIBUTION

| Aspect | PREDICTION | ATTRIBUTION |
|--------|------------|-------------|
| **Timing** | T=0 (filing time) | T+1 (after reaction) |
| **Purpose** | Predict direction | Explain why moved |
| **PIT Filter** | ON (mandatory) | OFF |
| **Return Data** | ❌ FORBIDDEN | ✓ ALLOWED |
| **Routing** | /filtered-data | Direct Task calls |
| **Output** | predictions.csv (partial) | {accession}.md report |
| **Workflow** | 5 steps | 10 steps |

**Relationship**: Attribution fills prediction's `actual_*` columns and validates correctness.

---

## 8. SKILL REFERENCE

| Skill | Sub-Agents | Data Source | Output |
|-------|------------|-------------|--------|
| earnings-prediction | filtered-data → 6 agents | Neo4j + Perplexity (PIT) | predictions.csv |
| earnings-attribution | 6 agents direct | Neo4j + Perplexity (full) | {accession}.md |
| filtered-data | Routes to 10 agents | Validates responses | CLEAN/CONTAMINATED |
| neo4j-report | None | Neo4j MCP | Reports + returns |
| neo4j-xbrl | None | Neo4j MCP | Facts + Concepts |
| neo4j-news | None | Neo4j MCP | News + returns |
| neo4j-transcript | None | Neo4j MCP | Transcripts + Q&A |
| neo4j-entity | None | Neo4j MCP | Companies + actions |
| perplexity-search | None | Perplexity API | Raw URLs |
| perplexity-ask | None | Perplexity API | Synthesized answer |
| perplexity-reason | None | Perplexity API | Chain-of-thought |
| perplexity-research | None | Perplexity API | Deep report |

---

## 9. FILE LOCATIONS

```
.claude/skills/
├── FLOW.md                    ← THIS FILE
├── earnings-prediction/
│   └── SKILL.md              ← v1.6
├── earnings-attribution/
│   ├── SKILL.md              ← v4.2
│   ├── output_template.md
│   ├── evidence_audit.md
│   └── data_gaps.md
├── filtered-data/
│   └── SKILL.md
├── neo4j-{report,xbrl,news,transcript,entity}/
│   └── SKILL.md
├── perplexity-{search,ask,reason,research,sec,routing}/
│   └── SKILL.md
└── evidence-standards/
    └── SKILL.md

.claude/filters/
├── rules.json                ← Forbidden patterns + PIT fields
├── validate.sh               ← Dispatcher
├── validate_neo4j.sh
└── validate_perplexity.sh

earnings-analysis/
├── predictions.csv
└── Companies/{TICKER}/
    ├── {accession}.md
    └── learnings.md
```

---

*Generated: 2026-01-14*
