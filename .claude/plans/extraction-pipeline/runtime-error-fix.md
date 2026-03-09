# Runtime Error Fix Plan — E1, E2, E4 (+ E3 monitoring)

Fixes for the OPEN runtime errors observed during AAPL production extraction runs.

**Status**: PLAN — no changes made yet.
**Date**: 2026-03-08
**Scope**: 4 changes, zero regression risk. All changes are additive (new scripts) or edits to error messages/documentation/pass briefs.

---

## Root Cause Analysis (independently verified)

### E1: Agent Query Mutation on 2B (`dim_u_id not defined`)

**Root cause**: Agent transcription error — NOT MCP mangling, NOT backtick escaping, NOT a Neo4j syntax bug.

**Evidence**: Diffed the agent's actual query (from `agent-a8e348490dc0909ed.jsonl:49`) against the correct query in `queries-common.md:127-178`. Both are 51 lines. **One line differs**:

```
LINE 27:
  CORRECT:  dim_u_id,
  FAILING:  dim_u_id AS axis_u_id,
```

The agent prematurely applied the `AS axis_u_id` alias one `WITH` clause too early. In the correct query, line 27 passes `dim_u_id` through unchanged, and the rename to `axis_u_id` happens in the NEXT `WITH` clause (line 33). The agent's version renames `dim_u_id` to `axis_u_id` at line 27, so when line 33 references `dim_u_id` again, the variable no longer exists.

Classic LLM "look-ahead" transcription error — the agent sees that `dim_u_id` will eventually become `axis_u_id` and applies the rename one step too early.

**Current plan is wrong at `extractionPipeline_v2.md:1272`**: Says "RESOLVED (INVALID)" and "likely a Neo4j version quirk." Incorrect. The query text in the file IS correct, but the agent does NOT reproduce it faithfully. The runtime error is real and happens on every run (worker log lines 197, 203 confirm for March 8 run).

---

### E2: Nested Envelope Schema Drift

**Root cause**: Schema drift — the enrichment agent chose a completely different JSON shape, NOT "forgetting fields under context pressure."

**Evidence**: From `agent-ad5bbcb833bb96a68.jsonl:59`, the agent wrote:

```json
{
  "company": { "ticker": "AAPL", "cik": "0000320193", "fye_month": 9 },
  "source": { "source_id": "AAPL_2025-10-30T17.00", "source_type": "transcript", "source_key": "full" },
  "items": [...]
}
```

Instead of the required flat envelope:

```json
{ "source_id": "...", "source_type": "...", "ticker": "...", "fye_month": ..., "items": [...] }
```

The CLI at `guidance_write_cli.py:174` does `data.get('source_id')` which returns `None` because `source_id` is nested inside `data['source']`. Hard rejection at line 175.

**Already partially fixed**: `enrichment-pass.md:80-89` now pins the exact flat envelope format. Later runs (worker log line 701, March 8 batch) show correctly formed payloads.

---

### E3: Member Cache Noise — MONITORING (correct classification)

**Evidence**: `guidance_write_cli.py:261` logs `"Member matching: resolved %d items via code fallback"` on every write run. Working as designed — the CLI does authoritative member matching via direct Neo4j query, overwriting whatever the prompt-side cache provided.

The 2B cache is noisy: 76 rows for AAPL, of which ~60 are debt notes, financial instruments, hedging designations, and executive names. Only ~15 are guidance-relevant segments (Americas, Europe, Greater China, Japan, Rest of Asia Pacific, iPhone, iPad, Mac, Wearables, Services, Product).

**No fix needed for correctness** — the CLI fallback handles it. Optional quality improvement (tighten 2B axis filter) is deferred.

---

### E4: Persisted Output Wrapper — TWO Subcases

**Root cause**: The Claude SDK replaces MCP tool results exceeding ~50KB with a `<persisted-output>` wrapper pointing to a file on disk. The agent sometimes tries to parse this wrapper as raw JSON, causing JSONDecodeError tracebacks.

**Evidence from worker logs**: ALL persisted output events in the March 8 run are from **transcript content fetches** (query 3B: `MATCH (t:Transcript {id: $transcript_id}) OPTIONAL MATCH (t)-[:HAS_PREPARED_REMARKS]->`). AAPL transcript content is 56-61KB per transcript.

Warmup caches (2A ~30KB, 2B ~40KB when correct) return inline for AAPL and do NOT trigger persisted output. However, companies with larger XBRL profiles could exceed the threshold.

The persisted output file at the saved path contains the MCP result JSON wrapper:
```json
{"result":[{"type":"text","text":"[{...actual data escaped...}]"}]}
```
The agent's first `json.loads()` attempt on this file fails because the file contains the MCP wrapper, not the raw query result. After 2-3 traceback retries, the agent navigates the nested structure and succeeds.

`transcript-primary.md:12-14` already documents a reactive workaround: "If query 3B result is truncated by the MCP tool, re-run the query via Bash+Python and save to `/tmp` for parsing."

**Two subcases**:

| Subcase | Trigger | Size | Current Status |
|---------|---------|------|----------------|
| **E4a: Cache truncation** | Queries 2A/2B for companies with larger XBRL profiles | >50KB | Not observed for AAPL, but possible for others |
| **E4b: Transcript content truncation** | Query 3B (prepared remarks + Q&A) | 56-61KB for AAPL | Primary trigger. Happens every transcript run. |

---

## Fix Plan (4 changes)

### Change 1: Create `warmup_cache.sh` + `warmup_cache.py` + update pass briefs

**New files**:
- `scripts/warmup_cache.sh` — thin shell wrapper (same pattern as `guidance_write.sh`): activates venv, sets Neo4j env vars, runs Python script
- `scripts/warmup_cache.py` — connects via Bolt, runs queries 2A and 2B verbatim (copied from `queries-common.md`), writes results to `/tmp/concept_cache_{TICKER}.json` and `/tmp/member_cache_{TICKER}.json`

**Edits**:
- `primary-pass.md:19-20` — reroute from `QUERIES.md 2A` / `QUERIES.md 2B` to Bash helper:
  ```
  | Concept cache | Bash: `warmup_cache.sh $TICKER` → reads `/tmp/concept_cache_{TICKER}.json` |
  | Member cache  | Bash: `warmup_cache.sh $TICKER` → reads `/tmp/member_cache_{TICKER}.json` |
  ```
- `enrichment-pass.md:21-22` — same reroute

**Why the pass briefs must be updated**: The pass briefs are the authoritative step-by-step instructions the agent follows. If they say "run 2A and 2B from QUERIES.md", the agent will go to `queries-common.md`, transcribe the 52-line query, and send it through MCP — regardless of any note in the query file. Updating the pass briefs to point directly at the Bash helper means the agent never opens `queries-common.md` for 2A/2B. E1 is eliminated by design — there is no 52-line Cypher to transcribe.

**Fixes**: E1 entirely. E4a (cache truncation) entirely.

**Regression risk**: Zero. New files only. Pass brief edits change the tool path (MCP → Bash) but the data produced is identical. Queries 2A/2B remain in `queries-common.md` for ad-hoc interactive use.

---

### Change 2: Update `transcript-primary.md:12-14` — proactive Bash fetch for query 3B

**Current text** (reactive):
```
## MCP Truncation Workaround

If query 3B result is truncated by the MCP tool, re-run the query via Bash+Python and save to `/tmp` for parsing.
```

**New text** (proactive):
```
## Content Fetch — Always Use Bash for 3B

Transcript content (query 3B) typically exceeds 50KB and triggers SDK output persistence.
Always fetch via Bash+Python instead of MCP to avoid parse failures:

    ```bash
    bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh $TICKER --transcript $TRANSCRIPT_ID
    ```

Or use inline Python via Bash:

    ```bash
    python3 -c "
    import json
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver('bolt://localhost:30687', auth=('neo4j', 'Next2020#'))
    with driver.session() as s:
        r = s.run('''
            MATCH (t:Transcript {id: \$tid})
            OPTIONAL MATCH (t)-[:HAS_PREPARED_REMARKS]->(pr:PreparedRemark)
            OPTIONAL MATCH (t)-[:HAS_QA_EXCHANGE]->(qa:QAExchange)
            WITH t, pr, qa ORDER BY toInteger(qa.sequence)
            WITH t, pr.content AS prepared_remarks,
                 [item IN collect({sequence: qa.sequence, questioner: qa.questioner,
                  questioner_title: qa.questioner_title, responders: qa.responders,
                  responder_title: qa.responder_title, exchanges: qa.exchanges})
                  WHERE item.sequence IS NOT NULL] AS qa_exchanges
            RETURN t.id AS transcript_id, t.conference_datetime AS call_date,
                   t.company_name AS company, t.fiscal_quarter, t.fiscal_year,
                   prepared_remarks, qa_exchanges
        ''', tid='$TRANSCRIPT_ID')
        data = [dict(rec) for rec in r]
    driver.close()
    with open('/tmp/transcript_content.json', 'w') as f:
        json.dump(data, f)
    print(f'Wrote {len(data)} records to /tmp/transcript_content.json')
    "
    ```

Result written to `/tmp/transcript_content.json`. Read this file instead of parsing MCP output.
```

**Decision needed**: Whether to extend `warmup_cache.sh` with a `--transcript` mode (cleaner, one script) or provide the inline Python template (simpler, no new code). The inline template is ~15 lines — short enough for reliable agent transcription (unlike the 52-line 2B query).

**Fixes**: E4b (transcript content truncation).

**Regression risk**: Zero. Only changes documentation/instructions. No code modified.

---

### Change 3: Update `guidance_write_cli.py:174` — better error message for E2

**Current code** (`guidance_write_cli.py:174-176`):
```python
if not source_id or not source_type or not ticker:
    print(json.dumps({"error": "Missing required top-level fields: source_id, source_type, ticker"}))
    sys.exit(1)
```

**New code** (3-line addition):
```python
if not source_id or not source_type or not ticker:
    hint = ""
    if 'company' in data or 'source' in data:
        hint = " Detected nested 'company'/'source' objects — use flat top-level fields instead. See enrichment-pass.md JSON example."
    print(json.dumps({"error": f"Missing required top-level fields: source_id, source_type, ticker.{hint}"}))
    sys.exit(1)
```

**Fixes**: Hardens E2 — agent gets a clear diagnostic hint when it uses the wrong schema shape.

**Regression risk**: Zero. This code only executes on the error path (payload already invalid). Normal payloads never reach this branch.

---

### Change 4: Update tracker + plan text

**`extraction-pipeline-tracker.md`**:
- E1: Update description from "MCP tool mangles backtick escaping" to "Agent query mutation — premature `AS axis_u_id` alias at line 27 of 52-line query 2B. Fixed by warmup_cache.py Bash helper." Close as DONE with commit reference.
- E4: Split into E4a (cache truncation, fixed by warmup_cache.py) and E4b (transcript content truncation, fixed by proactive Bash fetch in transcript-primary.md).

**`extractionPipeline_v2.md:1272`**:
- Change from: `RESOLVED (INVALID) | ... Runtime error was likely a Neo4j version quirk or transient issue — agents work around it regardless via code fallback. No code change needed.`
- Change to: `RESOLVED (warmup_cache.py) | Query text in queries-common.md is valid Cypher. Runtime error is an agent transcription fidelity failure — the agent prematurely aliases dim_u_id AS axis_u_id one WITH clause too early (verified in agent-a8e348490dc0909ed.jsonl:49 vs queries-common.md:148). Fixed by routing warmup to a Bash helper script that runs the query verbatim via Bolt. Pass briefs updated to point at warmup_cache.sh instead of QUERIES.md 2A/2B.`

**Regression risk**: Zero. Documentation only.

---

## What This Does NOT Do (correctly scoped)

- Does NOT create a generic `fetch_content.py` for all assets — only transcript needs it (8-K exhibits are under 50KB, news bodies are small)
- Does NOT modify query 2B in `queries-common.md` — the query itself is correct, the problem is agent transcription. Queries remain for ad-hoc interactive use.
- Does NOT change E3 classification — MONITORING remains correct
- Does NOT modify any existing working code paths — all changes are additive (new scripts) or to error messages/documentation/pass briefs
- Does NOT tighten the 2B axis filter (E3 quality improvement) — deferred, optional, would go inside warmup_cache.py if implemented later

---

## File Change Summary

| File | Action | Lines Changed |
|------|--------|---------------|
| `scripts/warmup_cache.sh` | CREATE | ~20 lines (shell wrapper) |
| `scripts/warmup_cache.py` | CREATE | ~60 lines (Bolt queries + JSON write) |
| `types/guidance/primary-pass.md` | EDIT | Lines 19-20 (reroute 2A/2B to Bash) |
| `types/guidance/enrichment-pass.md` | EDIT | Lines 21-22 (same reroute) |
| `types/guidance/assets/transcript-primary.md` | EDIT | Lines 12-14 (proactive Bash fetch for 3B) |
| `scripts/guidance_write_cli.py` | EDIT | Lines 174-176 (3-line hint addition) |
| `extraction-pipeline-tracker.md` | EDIT | E1 description + E4 split |
| `extractionPipeline_v2.md` | EDIT | Line 1272 (issue #10 rewording) |

**Total**: 2 new files (~80 lines), 6 file edits (documentation + 3-line code change).

---

*Plan created 2026-03-08. Based on independent verification of agent transcripts, worker logs, source code, and live Neo4j queries.*
