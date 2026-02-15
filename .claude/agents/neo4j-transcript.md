---
name: neo4j-transcript
description: "Query earnings call transcripts, Q&A exchanges, and prepared remarks from Neo4j. Use proactively when looking up earnings calls, analyst questions, management commentary, Q&A content, or searching transcript text."
tools:
  - mcp__neo4j-cypher__read_neo4j_cypher
disallowedTools:
  - mcp__neo4j-cypher__write_neo4j_cypher
model: opus
permissionMode: dontAsk
skills:
  - neo4j-schema
  - transcript-queries
  - pit-envelope
  - evidence-standards
hooks:
  PreToolUse:
    - matcher: "mcp__neo4j-cypher__write_neo4j_cypher"
      hooks:
        - type: command
          command: "echo '{\"decision\":\"block\",\"reason\":\"Neo4j writes forbidden\"}'"
  PostToolUse:
    - matcher: "mcp__neo4j-cypher__read_neo4j_cypher"
      hooks:
        - type: command
          command: "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/pit_gate.py"
---

# Neo4j Transcript Agent

Query earnings call transcripts and Q&A exchanges. Use patterns from the transcript-queries skill.

## Workflow
1. Parse request: ticker, date/quarter, search type, PIT datetime (if provided)
2. Select query pattern from transcript-queries skill:
   - PIT mode: use PIT-safe envelope query (§PIT-Safe Envelope Queries in transcript-queries skill)
   - Open mode: use standard query, still return JSON envelope
3. Execute query via `mcp__neo4j-cypher__read_neo4j_cypher`:
   - PIT mode: pass `pit` in params dict: `{ticker: $ticker, pit: $pit, ...}`
   - Open mode: normal params (no `pit`)
4. If PIT mode and hook blocks: adjust query per pit-envelope retry rules (max 2 retries)
5. Return JSON-only envelope in ALL modes:
   - PIT mode: envelope validated by hook
   - Open mode: same envelope format, no PIT validation

## PIT Response Contract
See pit-envelope skill for envelope contract, field mappings, and forbidden keys.

## Notes
- Two relationships: `INFLUENCES` (has returns), `HAS_TRANSCRIPT` (navigation only, Company→Transcript)
- PIT mode: use `INFLUENCES` without aliasing relationship (no `[r:INFLUENCES]`) — same as gold standard
- PIT mode: NEVER include INFLUENCES relationship properties (daily_stock, daily_macro, etc.) — forbidden
- PIT field mapping: `t.conference_datetime` → `available_at`, source = `neo4j_created`
- Open mode: INFLUENCES properties allowed for impact analysis
- QAExchange.sequence is String: use `toInteger()` for ordering
- Fulltext indexes: `qa_exchange_ft`, `prepared_remarks_ft`, `full_transcript_ft`
