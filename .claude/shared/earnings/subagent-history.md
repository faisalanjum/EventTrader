# Subagent History (Shared Append-Only CSV)

Single CSV tracking all sub-agent sessions across both earnings-prediction and earnings-attribution skills.

---

## CSV Location

**File**: `.claude/shared/earnings/subagent-history.csv`

Both skills append to this same file.

---

## CSV Format

**Columns**:
```csv
accession_no,skill,created_at,primary_session_id,agent_type,agent_id,resumed_from
```

| Column | Description |
|--------|-------------|
| `accession_no` | SEC filing identifier |
| `skill` | Which skill: `prediction` or `attribution` |
| `created_at` | ISO8601 timestamp when agent was spawned |
| `primary_session_id` | Primary conversation session ID (first 8 chars) |
| `agent_type` | `primary` for main session, or subagent type: neo4j-entity, neo4j-report, neo4j-xbrl, neo4j-transcript, neo4j-news, perplexity-*, etc. |
| `agent_id` | Subagent ID returned from Task tool (empty for primary) |
| `resumed_from` | Previous agent_id if resumed (empty if fresh) |

**Example**:
```csv
accession_no,skill,created_at,primary_session_id,agent_type,agent_id,resumed_from
0001514416-24-000020,prediction,2026-01-13T09:00:00,aaa11111,primary,,
0001514416-24-000020,prediction,2026-01-13T09:01:05,aaa11111,neo4j-entity,abc12345,
0001514416-24-000020,prediction,2026-01-13T09:02:12,aaa11111,neo4j-report,def67890,
0001514416-24-000020,attribution,2026-01-13T10:30:00,bbb22222,primary,,
0001514416-24-000020,attribution,2026-01-13T10:31:05,bbb22222,neo4j-entity,ghi11111,abc12345
0001514416-24-000020,attribution,2026-01-13T10:32:12,bbb22222,neo4j-news,jkl22222,
```

---

## Operations

### On Analysis Start

1. Read CSV (create with header if doesn't exist)
2. Append `primary` row for this session:
   ```csv
   {accession},{skill},{timestamp},{session_id},primary,,
   ```

### Before Calling a Subagent (Resume Check)

Query latest agent ID for potential resume:

```bash
# Latest neo4j-entity for this accession (any skill)
grep "{accession}" subagent-history.csv | grep ",neo4j-entity," | tail -1 | cut -d',' -f6

# Latest neo4j-entity for this accession AND skill
grep "{accession},{skill}," subagent-history.csv | grep ",neo4j-entity," | tail -1 | cut -d',' -f6
```

**Decision**:
- Agent ID exists → can use `resume: <id>` in Task call
- Want fresh session → proceed without resume

### After Each Subagent Completes

1. Extract `agentId` from Task response (shown as `agentId: xxxxxxxx`)
2. Append row:
   ```csv
   {accession},{skill},{timestamp},{primary_session_id},{agent_type},{agent_id},{resumed_from or empty}
   ```

**Timestamp**: Use `date -Iseconds` format (e.g., `2026-01-15T10:30:00-05:00`)

---

## Querying

All examples use variables - replace `{accession}`, `{skill}`, `{agent_type}` with actual values.

### All sessions for an accession
```bash
grep "{accession}" subagent-history.csv
# Example: grep "0001514416-24-000020" subagent-history.csv
```

### All prediction runs
```bash
grep ",prediction," subagent-history.csv
```

### Primary sessions only
```bash
grep ",primary," subagent-history.csv
```

### Resume chain for an agent
```bash
# Find what agent was resumed from, and what resumed it
grep "{agent_id}" subagent-history.csv
```

---

## Hybrid Architecture

This CSV works together with filesystem discovery:

| Task | Use |
|------|-----|
| **Resume sub-agent** | CSV (semantic lookup by accession + type) |
| **Extract thinking** | Filesystem (comprehensive, automatic) |
| **Audit trail** | Both (CSV for intent, filesystem for reality) |
| **Find session for accession** | CSV (direct lookup) |

The `build-thinking-index.py` script uses filesystem discovery for extraction but can use CSV to find which `primary_session_id` to analyze for a given accession.

---

## Cleanup

Old skill-specific CSVs are deprecated:
- `.claude/skills/earnings-attribution/subagent-history.csv` → migrated here
- `.claude/skills/earnings-prediction/subagent-history.csv` → migrated here

---

*Version 2.0 | 2026-01-15 | Unified CSV with skill column*
