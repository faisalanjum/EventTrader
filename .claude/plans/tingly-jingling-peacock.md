# Guidance Agent System - Implementation Plan

## Overview

Build a parallel agent system for extracting forward-looking guidance from multiple source types (8-K, 10-K, 10-Q, transcripts, news). Runs alongside news attribution in earnings-orchestrator.

**Key Design Decision:** Use 3 consolidated agents with dynamic skill routing instead of 5+ separate agents.

---

## Architecture

```
GUIDANCE ORCHESTRATOR (integrated into earnings-orchestrator)
│
├── Phase 0: Setup
│   └── get_earnings.py → quarters + date ranges
│
├── Phase 1: Discovery (ALL scripts run in parallel)
│   ├── get_8k_filings_range.py      → list of 8-K accessions
│   ├── get_10k_filings_range.py     → list of 10-K accessions
│   ├── get_10q_filings_range.py     → list of 10-Q accessions
│   ├── get_transcript_range.py      → list of transcript IDs (NEW - combined)
│   └── get_guidance_news_range.py   → list of news IDs (NEW - combined)
│
├── Phase 2: Task Creation (upfront, with dependencies if needed)
│   └── Create one task per source document
│
├── Phase 3: Extraction (spawn agents in parallel)
│   │
│   │  ┌─────────────────────────────────────────────────────────────┐
│   │  │ guidance-filing agent (handles all SEC filings)            │
│   │  │   ├── Routes to /guidance-8k-skill for 8-K filings         │
│   │  │   ├── Routes to /guidance-10k-skill for 10-K filings       │
│   │  │   └── Routes to /guidance-10q-skill for 10-Q filings       │
│   │  └─────────────────────────────────────────────────────────────┘
│   │
│   ├── guidance-filing      × N agents (routes via Skill tool)
│   ├── guidance-transcript  × N agents (one per transcript)
│   └── guidance-news        × N agents (one per news article)
│
└── Phase 4: Collection
    └── Orchestrator collects results from completed tasks
    └── (Validator tier deferred to later iteration)
```

### Dynamic Skill Routing Pattern

The `guidance-filing` agent uses the `Skill` tool to dynamically invoke form-specific skills:

```
Orchestrator spawns: guidance-filing agent
  ↓
Agent receives: "AAPL 0001234-25-000001 8-K Q1_FY2025 TASK_ID=5"
  ↓
Agent routes: /guidance-8k-skill with accession and context
  ↓
Skill provides: Form-specific Neo4j queries, extraction patterns
  ↓
Agent outputs: Pipe-delimited guidance entries
```

---

## Task Naming Convention

| Prefix | Example Subject | Source |
|--------|----------------|--------|
| `8K-` | `8K-Q1_FY2025 AAPL 0001234-25-000001` | 8-K filing |
| `10K-` | `10K-Q4_FY2024 AAPL 0001234-25-000100` | 10-K filing |
| `10Q-` | `10Q-Q2_FY2025 AAPL 0001234-25-000050` | 10-Q filing |
| `TR-` | `TR-Q1_FY2025 AAPL 12345` | Transcript (full PR + QA) |
| `NEWS-` | `NEWS-Q1_FY2025 AAPL bzNews_789` | News article |

---

## Output Format (All Agents)

**Pipe-delimited, one line per guidance entry:**

```
period|metric|low|mid|high|unit|basis|source_type|source_id|given_date|quote|action
```

| Field | Type | Example | Description |
|-------|------|---------|-------------|
| `period` | String | `Q2_FY2025` or `FY2025` | Fiscal period guidance is FOR |
| `metric` | String | `EPS`, `Revenue`, `Gross Margin` | What's being guided |
| `low` | Float | `1.50` | Low end of range (or same as mid if point) |
| `mid` | Float | `1.60` | Midpoint |
| `high` | Float | `1.70` | High end of range |
| `unit` | String | `USD`, `%`, `B USD` | Unit of measure |
| `basis` | String | `non-GAAP`, `GAAP`, `adjusted` | Accounting basis |
| `source_type` | String | `8-K`, `10-K`, `transcript`, `news` | Source type |
| `source_id` | String | `0001234-25-000001` or `bzNews_789` | Source identifier |
| `given_date` | Date | `2025-02-05` | When guidance was issued |
| `quote` | String | `We expect Q2 EPS of $1.50-$1.70` | Exact quote (no pipes) |
| `action` | String | `INITIAL`, `RAISED`, `LOWERED`, `MAINTAINED` | Classification |

**Example output:**
```
Q2_FY2025|EPS|1.50|1.60|1.70|USD|non-GAAP|8-K|0001234-25-000001|2025-02-05|We expect Q2 EPS of $1.50 to $1.70|INITIAL
FY2025|Revenue|95|97.5|100|B USD|as-reported|8-K|0001234-25-000001|2025-02-05|Full year revenue of $95B to $100B|RAISED
```

---

## Files to Create

### Scripts (User Creates)

| File | Purpose | Input | Output |
|------|---------|-------|--------|
| `scripts/earnings/get_transcript_range.py` | Combined transcript discovery | `TICKER START END` | `transcript_id\|date\|fiscal_quarter\|fiscal_year` |
| `scripts/earnings/get_guidance_news_range.py` | Combined news discovery | `TICKER START END` | `news_id\|date\|title\|source` |

### Agents (Claude Creates) - 3 Total

| File | Purpose | Tools |
|------|---------|-------|
| `.claude/agents/guidance-filing.md` | Extract guidance from SEC filings (routes to form-specific skills) | Bash, Skill, TaskList, TaskGet, TaskUpdate, mcp__neo4j-cypher |
| `.claude/agents/guidance-transcript.md` | Extract guidance from ONE transcript (PR + QA) | Bash, TaskList, TaskGet, TaskUpdate, mcp__neo4j-cypher |
| `.claude/agents/guidance-news.md` | Extract guidance from ONE news article | Bash, TaskList, TaskGet, TaskUpdate, mcp__neo4j-cypher |

### Skills (Claude Creates) - Form-Specific Extraction Logic

| File | Purpose | Used By |
|------|---------|---------|
| `.claude/skills/guidance-8k-skill/SKILL.md` | 8-K extraction patterns (Item 2.02, EX-99.1) | guidance-filing agent |
| `.claude/skills/guidance-10k-skill/SKILL.md` | 10-K extraction patterns (MD&A, Risk Factors) | guidance-filing agent |
| `.claude/skills/guidance-10q-skill/SKILL.md` | 10-Q extraction patterns (MD&A) | guidance-filing agent |

### Deferred (Later Iteration)

- `guidance-presentation.md` - Requires web/PDF parsing
- `guidance-perplexity.md` - Gap filling
- `guidance-validator.md` - Validation/reconciliation tier

---

## Agent Structures

### 1. guidance-filing Agent (Routes to Skills)

```markdown
---
name: guidance-filing
description: "Extract forward-looking guidance from SEC filings (8-K, 10-K, 10-Q)."
color: "#3B82F6"
tools:
  - Bash
  - Skill              # <-- Enables dynamic skill routing
  - TaskList
  - TaskGet
  - TaskUpdate
  - mcp__neo4j-cypher__read_neo4j_cypher
model: sonnet
permissionMode: dontAsk
---

# Guidance Filing Agent

Extract forward-looking guidance from SEC filings by routing to form-specific skills.

## Input

Prompt format: `TICKER ACCESSION FORM_TYPE QUARTER TASK_ID=N`

Example: `AAPL 0001234-25-000001 8-K Q1_FY2025 TASK_ID=15`

## Task

### Step 1: Route to Form-Specific Skill

Based on FORM_TYPE, invoke the appropriate skill:
- **8-K** → `/guidance-8k-skill {ACCESSION}`
- **10-K** → `/guidance-10k-skill {ACCESSION}`
- **10-Q** → `/guidance-10q-skill {ACCESSION}`

The skill provides form-specific Neo4j queries and extraction patterns.

### Step 2: Extract Guidance (via skill)

The skill guides extraction of:
- Fiscal period covered (Q1, FY, etc.)
- Metric, range (low/mid/high), unit, basis
- Exact quote
- Action classification

### Step 3: Update Task (MANDATORY)

TaskUpdate(taskId: "{TASK_ID}", status: "completed",
           description: "{all guidance lines, newline separated}")

### Step 4: Output via Bash

```bash
echo "period|metric|low|mid|high|unit|basis|source_type|source_id|given_date|quote|action"
```

## Rules

- Route to skill FIRST before extraction
- Pass through skill's output format unchanged
- If no guidance found: output "NO_GUIDANCE|{source_id}"
```

### 2. Form-Specific Skills

**guidance-8k-skill:**
```markdown
---
name: guidance-8k-skill
description: "8-K filing extraction patterns (Item 2.02, EX-99.1)"
---

# 8-K Guidance Extraction

## Focus Areas
- Item 2.02 (Results of Operations and Financial Condition)
- Item 7.01 (Regulation FD Disclosure) - pre-announcements
- EX-99.1 (Press Release) - primary guidance source

## Neo4j Query
```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_EXHIBIT]->(e:ExhibitContent)
WHERE e.exhibit_number CONTAINS '99.1'
RETURN e.content, r.created, r.items
```

## Extraction Patterns
- "expects", "anticipates", "guidance", "outlook"
- Range format: "$X to $Y", "$X - $Y", "between $X and $Y"
- Point format: "approximately $X", "about $X"

## Common Metrics
- EPS (adjusted, non-GAAP)
- Revenue (total, segment)
- Operating margin
- Free cash flow
```

**guidance-10k-skill / guidance-10q-skill:** Similar structure with MD&A focus.

### 3. guidance-transcript Agent

```markdown
---
name: guidance-transcript
description: "Extract forward-looking guidance from earnings call transcripts."
color: "#22C55E"
tools:
  - Bash
  - TaskList
  - TaskGet
  - TaskUpdate
  - mcp__neo4j-cypher__read_neo4j_cypher
model: sonnet
permissionMode: dontAsk
---

# Guidance Transcript Agent

Extract guidance from full transcript (Prepared Remarks + Q&A).

## Input

Prompt format: `TICKER TRANSCRIPT_ID QUARTER TASK_ID=N`

## Task

### Step 1: Fetch Full Transcript

```cypher
MATCH (t:Transcript {id: $transcript_id})-[:HAS_FULL_TEXT]->(ft:FullTranscriptText)
RETURN ft.content, t.conference_datetime, t.fiscal_quarter, t.fiscal_year
```

### Step 2: Extract from Prepared Remarks

Focus on CFO/CEO sections for explicit guidance statements.

### Step 3: Extract from Q&A

Look for analyst probes and management clarifications/hedging.

### Step 4: Update Task & Output

(Same pattern as guidance-filing)
```

### 4. guidance-news Agent

```markdown
---
name: guidance-news
description: "Extract guidance mentions from news articles."
color: "#F59E0B"
tools:
  - Bash
  - TaskList
  - TaskGet
  - TaskUpdate
  - mcp__neo4j-cypher__read_neo4j_cypher
model: sonnet
permissionMode: dontAsk
---

# Guidance News Agent

Extract guidance mentions from financial and operational news.

## Input

Prompt format: `TICKER NEWS_ID QUARTER TASK_ID=N`

## Task

### Step 1: Fetch News Content

```cypher
MATCH (n:News {id: $news_id})
RETURN n.title, n.body, n.teaser, n.created, n.channels
```

### Step 2: Extract Guidance Mentions

Focus on reported guidance, analyst reactions, guidance revisions.

### Step 3: Update Task & Output

(Same pattern as guidance-filing)
```

---

## Discovery Script Output Formats

### Existing Scripts (Already Work)

**get_8k_filings_range.py** `TICKER START END`
```
id|date|items
0001234-25-000001|2025-02-05|2.02;7.01
```

**get_10k_filings_range.py** `TICKER START END`
```
id|date|period
0001234-25-000100|2025-03-15|2024-12-31
```

**get_10q_filings_range.py** `TICKER START END`
```
id|date|period
0001234-25-000050|2025-05-10|2025-03-31
```

### New Scripts (User Creates)

**get_transcript_range.py** `TICKER START END`
```
transcript_id|date|fiscal_quarter|fiscal_year
12345|2025-02-05|Q1|2025
12346|2025-05-07|Q2|2025
```
*Note: Combines unique transcript_ids from PR and QA queries*

**get_guidance_news_range.py** `TICKER START END`
```
news_id|date|title|channel
bzNews_789|2025-02-06|AAPL Raises FY25 Guidance|Guidance
bzNews_456|2025-02-06|AAPL Expands Production|Operational
```
*Note: Combines financial guidance + operational news*

---

## Neo4j Queries for Agents

### guidance-8k: Get 8-K EX-99.1 Content

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_EXHIBIT]->(e:ExhibitContent)
WHERE e.exhibit_number CONTAINS '99.1'
RETURN e.content, r.created, r.items
```

### guidance-10k/10q: Get MD&A Section

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_SECTION]->(s:Section)
WHERE s.section_name CONTAINS 'MD&A' OR s.section_name CONTAINS "Management's Discussion"
RETURN s.content, r.periodOfReport
```

### guidance-transcript: Get Full Transcript

```cypher
MATCH (t:Transcript {id: $transcript_id})-[:HAS_FULL_TEXT]->(ft:FullTranscriptText)
OPTIONAL MATCH (t)-[:HAS_PREPARED_REMARKS]->(pr:PreparedRemark)
OPTIONAL MATCH (t)-[:HAS_QA_EXCHANGE]->(qa:QAExchange)
RETURN ft.content, t.conference_datetime, t.fiscal_quarter, t.fiscal_year,
       collect(DISTINCT pr.content) as prepared_remarks,
       collect(DISTINCT {q: qa.question, a: qa.answer}) as qa_exchanges
```

### guidance-news: Get News Content

```cypher
MATCH (n:News {id: $news_id})
RETURN n.title, n.body, n.teaser, n.created, n.channels
```

---

## Orchestrator Integration

### Option 1: Add to earnings-orchestrator (Recommended)

Add new steps after get_earnings.py, parallel to news analysis:

```
Step 1: get_earnings.py → E1, E2 quarters
Step 1.5: Guidance Discovery (parallel)
    ├── get_8k_filings_range.py
    ├── get_10k_filings_range.py
    ├── get_10q_filings_range.py
    ├── get_transcript_range.py
    └── get_guidance_news_range.py
Step 1.6: Create Guidance Tasks (one per source)
Step 1.7: Spawn Guidance Agents (parallel)
    └── [Run alongside news agents in Step 3]
Step 2-4: News Analysis (existing)
Step 5: Collect Guidance Results
Step 6: Save to guidance-inventory.md
```

### Option 2: Standalone guidance-orchestrator

Separate skill that can run independently or be called from earnings-orchestrator.

---

## Task Flow Example

**Input:** `AAPL` for Q1_FY2025

**Discovery Phase (all scripts run in parallel):**
```
get_8k_filings_range.py AAPL 2024-10-01 2025-01-15 → 3 8-Ks
get_10k_filings_range.py AAPL 2024-10-01 2025-01-15 → 0 10-Ks
get_10q_filings_range.py AAPL 2024-10-01 2025-01-15 → 1 10-Q
get_transcript_range.py AAPL 2024-10-01 2025-01-15 → 1 transcript
get_guidance_news_range.py AAPL 2024-10-01 2025-01-15 → 5 news
```

**Task Creation (10 total tasks):**
```
TaskCreate: "8K-Q1_FY2025 AAPL 0001234-25-000001"     # 8-K #1
TaskCreate: "8K-Q1_FY2025 AAPL 0001234-25-000002"     # 8-K #2
TaskCreate: "8K-Q1_FY2025 AAPL 0001234-25-000003"     # 8-K #3
TaskCreate: "10Q-Q1_FY2025 AAPL 0001234-25-000050"    # 10-Q
TaskCreate: "TR-Q1_FY2025 AAPL 12345"                 # Transcript
TaskCreate: "NEWS-Q1_FY2025 AAPL bzNews_789"          # News #1
... (4 more news tasks)
```

**Agent Spawning (parallel, using 3 agent types):**
```
# All SEC filings use guidance-filing agent with FORM_TYPE parameter
Task(subagent_type="guidance-filing", prompt="AAPL 0001234-25-000001 8-K Q1_FY2025 TASK_ID=1")
Task(subagent_type="guidance-filing", prompt="AAPL 0001234-25-000002 8-K Q1_FY2025 TASK_ID=2")
Task(subagent_type="guidance-filing", prompt="AAPL 0001234-25-000003 8-K Q1_FY2025 TASK_ID=3")
Task(subagent_type="guidance-filing", prompt="AAPL 0001234-25-000050 10-Q Q1_FY2025 TASK_ID=4")

# Transcript uses guidance-transcript agent
Task(subagent_type="guidance-transcript", prompt="AAPL 12345 Q1_FY2025 TASK_ID=5")

# News uses guidance-news agent
Task(subagent_type="guidance-news", prompt="AAPL bzNews_789 Q1_FY2025 TASK_ID=6")
... etc
```

**Inside guidance-filing agent (skill routing):**
```
# Agent receives: "AAPL 0001234-25-000001 8-K Q1_FY2025 TASK_ID=1"
# Agent invokes: /guidance-8k-skill 0001234-25-000001
# Skill provides: Neo4j query for EX-99.1, extraction patterns
# Agent extracts: Guidance entries from press release
# Agent outputs: Pipe-delimited lines via bash echo
```

**Collection:**
```
For each completed task:
    result = TaskGet(task_id).description
    Parse pipe-delimited lines
    Append to Companies/AAPL/guidance-inventory.md
```

---

## Implementation Order

### Phase 1: Scripts (User)
1. ☐ Create `get_transcript_range.py` (combines PR + QA, returns unique transcript_ids)
2. ☐ Create `get_guidance_news_range.py` (combines financial + operational news)

### Phase 2: Core Agent + Skills (Claude)
3. ☐ Create `guidance-filing.md` agent (with Skill tool for routing)
4. ☐ Create `guidance-8k-skill/SKILL.md` (8-K extraction patterns)
5. ☐ Create `guidance-10k-skill/SKILL.md` (10-K extraction patterns)
6. ☐ Create `guidance-10q-skill/SKILL.md` (10-Q extraction patterns)

### Phase 3: Remaining Agents (Claude)
7. ☐ Create `guidance-transcript.md` agent
8. ☐ Create `guidance-news.md` agent

### Phase 4: Orchestrator Integration
9. ☐ Update earnings-orchestrator with guidance phases (or create standalone)
10. ☐ Test end-to-end with single ticker (e.g., AAPL)

### Phase 5: Deferred (Later)
- guidance-validator.md (reconciliation tier)
- guidance-presentation.md (web/PDF)
- guidance-perplexity.md (gap filling)

---

## Verification

### Test Discovery Scripts (User)
```bash
source venv/bin/activate
python scripts/earnings/get_8k_filings_range.py AAPL 2024-10-01 2025-01-15
python scripts/earnings/get_10k_filings_range.py AAPL 2024-10-01 2025-01-15
python scripts/earnings/get_10q_filings_range.py AAPL 2024-10-01 2025-01-15
python scripts/earnings/get_transcript_range.py AAPL 2024-10-01 2025-01-15      # NEW
python scripts/earnings/get_guidance_news_range.py AAPL 2024-10-01 2025-01-15   # NEW
```

### Test Single Agent (Claude)
```bash
# Test guidance-filing with 8-K
claude -p "AAPL 0001234-25-000001 8-K Q1_FY2025 TASK_ID=test" --agent guidance-filing

# Test guidance-transcript
claude -p "AAPL 12345 Q1_FY2025 TASK_ID=test" --agent guidance-transcript

# Test guidance-news
claude -p "AAPL bzNews_789 Q1_FY2025 TASK_ID=test" --agent guidance-news
```

### Test Full Flow
```bash
# Run earnings-orchestrator with guidance phases
/earnings-orchestrator AAPL
# Check outputs:
#   - earnings-analysis/Companies/AAPL/guidance-inventory.md
#   - Task list for guidance tasks (8K-*, 10K-*, 10Q-*, TR-*, NEWS-*)
```

---

## Color Coding for Agents

| Agent | Color | Hex |
|-------|-------|-----|
| guidance-filing | Blue | `#3B82F6` |
| guidance-transcript | Green | `#22C55E` |
| guidance-news | Amber | `#F59E0B` |
| guidance-validator | Purple | `#9333EA` |

---

## Dependencies

- Existing scripts: `get_8k_filings_range.py`, `get_10k_filings_range.py`, `get_10q_filings_range.py`
- Existing utilities: `scripts/earnings/utils.py`
- Neo4j schema: Report, ExhibitContent, Transcript, News nodes
- MCP: `mcp__neo4j-cypher__read_neo4j_cypher`

---

## Open Questions (Deferred)

1. **Supersession tracking**: How to link newer guidance that replaces older? (Validator tier)
2. **Action classification**: Need prior guidance context to determine RAISED/LOWERED (Validator tier)
3. **Consensus comparison**: Alpha Vantage integration for street estimates (Later)
4. **Presentation parsing**: IR website PDFs (Later)
