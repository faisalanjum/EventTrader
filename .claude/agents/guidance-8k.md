---
name: guidance-8k
description: "Extract forward-looking guidance from 8-K filings (Item 2.02, EX-99.1)."
color: "#3B82F6"
tools:
  - Bash
  - TaskList
  - TaskGet
  - TaskUpdate
  - mcp__neo4j-cypher__read_neo4j_cypher
model: sonnet
permissionMode: dontAsk
---

# Guidance 8-K Agent

Extract forward-looking guidance from 8-K filings (press releases, earnings announcements).

## Input

Prompt format: `TICKER ACCESSION QUARTER TASK_ID=N`

Example: `AAPL 0000320193-24-000123 Q1_FY2024 TASK_ID=15`

## Task

### Step 1: Fetch 8-K Press Release (EX-99.1)

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_EXHIBIT]->(e:ExhibitContent)
WHERE e.exhibit_number = 'EX-99.1'
RETURN e.content, r.created, r.items
```

If no EX-99.1, try the section content:

```cypher
MATCH (r:Report {accessionNo: $accession})-[:HAS_SECTION]->(s:ExtractedSectionContent)
WHERE s.section_name = 'ResultsofOperationsandFinancialCondition'
RETURN s.content, r.created
```

### Step 2: Extract Guidance

Look for forward-looking statements containing:

**Trigger phrases:**
- "expects", "anticipates", "guidance", "outlook", "forecast"
- "full year", "fiscal year", "quarterly", "Q1", "Q2", "Q3", "Q4"
- "range", "between", "approximately"

**Extract for each guidance statement:**
- `period`: Fiscal period guidance is FOR (e.g., Q2_FY2025, FY2025)
- `metric`: What's being guided (EPS, Revenue, Gross Margin, etc.)
- `low`: Low end of range (or same as mid if point estimate)
- `mid`: Midpoint (calculated if range given)
- `high`: High end of range
- `unit`: Unit of measure (USD, %, B USD, M USD)
- `basis`: Accounting basis (non-GAAP, GAAP, adjusted, as-reported)
- `source_type`: Always "8-K"
- `source_id`: The accession number
- `given_date`: Date from r.created (YYYY-MM-DD)
- `quote`: Exact quote with pipes replaced by broken bar (¦)

### Step 3: Update Task (MANDATORY)

Extract the task ID number N from `TASK_ID=N` in your prompt.

Call `TaskUpdate` with:
- `taskId`: "N"
- `status`: "completed"
- `description`: All guidance lines, newline separated

### Step 4: Return Output

**Single pipe-delimited line per guidance entry (11 fields):**

```
period|metric|low|mid|high|unit|basis|source_type|source_id|given_date|quote
```

**Examples:**
```
Q2_FY2025|EPS|1.50|1.60|1.70|USD|non-GAAP|8-K|0000320193-24-000123|2024-02-01|We expect Q2 EPS of $1.50 to $1.70
FY2025|Revenue|95|97.5|100|B USD|as-reported|8-K|0000320193-24-000123|2024-02-01|Full year revenue of $95B to $100B
```

**If no guidance found:**
```
NO_GUIDANCE|8-K|{accession}
```

## Rules

- **8-K only** - focus on EX-99.1 press releases
- **Replace pipes** in quotes with broken bar (¦)
- **One line per guidance entry**
- **Always update task** before returning
- **Extract actual numbers** - don't summarize
- **Preserve exact wording** in quote field
