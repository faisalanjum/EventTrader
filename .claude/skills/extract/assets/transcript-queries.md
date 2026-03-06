# Transcript Queries (S3)

Source content queries for earnings call transcripts.

---

## 3. Source Content: Transcript

### 3A. Transcript List

```cypher
MATCH (t:Transcript)-[:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE ($start_date IS NULL OR t.conference_datetime >= $start_date)
  AND ($end_date IS NULL OR t.conference_datetime <= $end_date)
RETURN t.id, t.conference_datetime, t.fiscal_quarter, t.fiscal_year, t.company_name
ORDER BY t.conference_datetime
```
**Usage**: Pass `null` for both dates to retrieve all historical transcripts. Uses `INFLUENCES` relationship. `conference_datetime` is ISO string.

### 3B. Structured Transcript Content (Primary Fetch)

Returns prepared remarks AND all Q&A exchanges in a single query. This is the primary content fetch for transcript extraction.

```cypher
MATCH (t:Transcript {id: $transcript_id})
OPTIONAL MATCH (t)-[:HAS_PREPARED_REMARKS]->(pr:PreparedRemark)
OPTIONAL MATCH (t)-[:HAS_QA_EXCHANGE]->(qa:QAExchange)
WITH t, pr,
     qa ORDER BY toInteger(qa.sequence)
WITH t,
     pr.content AS prepared_remarks,
     [item IN collect({
       sequence: qa.sequence,
       questioner: qa.questioner,
       questioner_title: qa.questioner_title,
       responders: qa.responders,
       responder_title: qa.responder_title,
       exchanges: qa.exchanges
     }) WHERE item.sequence IS NOT NULL] AS qa_exchanges
RETURN t.id AS transcript_id,
       t.conference_datetime AS call_date,
       t.company_name AS company,
       t.fiscal_quarter AS fiscal_quarter,
       t.fiscal_year AS fiscal_year,
       prepared_remarks,
       qa_exchanges
```
**Critical**: Returns `prepared_remarks` (JSON text with speaker statements) and `qa_exchanges` (array of Q&A objects). Both must be scanned for guidance. See PROFILE_TRANSCRIPT.md for extraction rules.

**Empty check**: If `qa_exchanges` is empty list, try 3C (Q&A Section fallback) before concluding Q&A is missing. If BOTH `prepared_remarks` is null/empty AND no Q&A from either 3B or 3C, try 3D (full transcript text).

### 3C. Q&A Section Content (Fallback)

40 transcripts use `HAS_QA_SECTION → QuestionAnswer` instead of `HAS_QA_EXCHANGE → QAExchange`. Try this when 3B returns empty `qa_exchanges`.

```cypher
MATCH (t:Transcript {id: $transcript_id})-[:HAS_QA_SECTION]->(qa:QuestionAnswer)
RETURN qa.id, qa.content, qa.speaker_roles
```
**Content format**: `content` is a JSON string containing an array of speaker-labeled dialogue lines. `speaker_roles` is a JSON string containing an object mapping speaker names to roles (OPERATOR, EXECUTIVE, ANALYST). Both require JSON parsing. `speaker_roles` is NULL on ~7 of 41 nodes — handle gracefully.

**Note**: These ~40 transcripts have no QAExchange nodes. Without this fallback, their Q&A content is invisible to the agent.

### 3D. Full Transcript Text (Fallback)

Use only when 3B and 3C both return empty content (prepared remarks and Q&A both missing).

```cypher
MATCH (t:Transcript {id: $transcript_id})-[:HAS_FULL_TEXT]->(ft:FullTranscriptText)
RETURN ft.content
```
**Note**: Only 28 FullTranscriptText nodes exist in the database. Most transcripts use PreparedRemark + QAExchange instead.

### 3E. Latest Transcript for Company

```cypher
MATCH (t:Transcript)-[:INFLUENCES]->(c:Company {ticker: $ticker})
RETURN t.id, t.conference_datetime, t.fiscal_quarter, t.fiscal_year
ORDER BY t.conference_datetime DESC
LIMIT 1
```

### 3F. Q&A Exchanges Only

Use when re-scanning Q&A for a specific transcript.

```cypher
MATCH (t:Transcript {id: $transcript_id})-[:HAS_QA_EXCHANGE]->(qa:QAExchange)
RETURN qa.sequence, qa.questioner, qa.questioner_title,
       qa.responders, qa.responder_title, qa.exchanges
ORDER BY toInteger(qa.sequence)
```

### 3G. Q&A by Questioner

Search for a specific analyst's questions across transcripts.

```cypher
MATCH (t:Transcript)-[:INFLUENCES]->(c:Company {ticker: $ticker})
MATCH (t)-[:HAS_QA_EXCHANGE]->(qa:QAExchange)
WHERE qa.questioner CONTAINS $analyst_name
RETURN t.conference_datetime, qa.questioner, qa.questioner_title, qa.exchanges
ORDER BY t.conference_datetime DESC
```
