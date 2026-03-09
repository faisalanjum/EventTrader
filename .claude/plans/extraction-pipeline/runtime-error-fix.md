# Runtime Error Fix Plan — E1, E2, E4 (+ E3 monitoring)

Fixes for the OPEN runtime errors observed during AAPL production extraction runs.

**Status**: IMPLEMENTED — all 4 changes applied and verified (V1-V3 pass).
**Date**: 2026-03-09 (v3: path consistency + verification section)
**Scope**: 4 changes, zero regression risk (no existing working code modified). New code carries standard defect risk — mitigated by simplicity and isolated error paths.

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

**Already partially fixed**: `enrichment-pass.md:80-89` now pins the exact flat envelope format, and line 92 explicitly says "Do NOT wrap items in a `company` object." Later runs (worker log line 701, March 8 batch) show correctly formed payloads.

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

**New files** (both in `.claude/skills/earnings-orchestrator/scripts/`, alongside `guidance_write.sh` and `guidance_write_cli.py`):
- `warmup_cache.sh` — thin shell wrapper (same pattern as `guidance_write.sh`): activates venv, sets Neo4j env vars, runs Python script
- `warmup_cache.py` — connects via `get_manager()` from `neograph.Neo4jConnection` (same pattern as `guidance_write_cli.py:223-224`), runs queries 2A and 2B verbatim (copied from `queries-common.md`), writes results to `/tmp/concept_cache_{TICKER}.json` and `/tmp/member_cache_{TICKER}.json`. Also supports `--transcript $TRANSCRIPT_ID` mode (see Change 2).

**Why `get_manager()` instead of raw Bolt**: `guidance_write_cli.py` already uses this pattern. The shell wrapper sets `NEO4J_URI`/`NEO4J_USERNAME`/`NEO4J_PASSWORD` env vars, `get_manager()` reads them. One connection pattern across all scripts — no credential drift, no manual `driver.session()` management.

**Edits**:
- `primary-pass.md:19-20` — reroute from `QUERIES.md 2A` / `QUERIES.md 2B` to Bash helper:
  ```
  | Concept cache | `bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh $TICKER` → reads `/tmp/concept_cache_{TICKER}.json` |
  | Member cache  | `bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh $TICKER` → reads `/tmp/member_cache_{TICKER}.json` |
  ```
- `enrichment-pass.md:21-22` — same reroute

**Why the pass briefs must be updated**: The pass briefs are the authoritative step-by-step instructions the agent follows. If they say "run 2A and 2B from QUERIES.md", the agent will go to `queries-common.md`, transcribe the 52-line query, and send it through MCP — regardless of any note in the query file. Updating the pass briefs to point directly at the Bash helper means the agent never opens `queries-common.md` for 2A/2B. E1 is eliminated by design — there is no 52-line Cypher to transcribe.

**Fixes**: E1 entirely. E4a (cache truncation) entirely.

**Regression risk**: Zero. New files only. Pass brief edits change the tool path (MCP → Bash) but the data produced is identical. Queries 2A/2B remain in `queries-common.md` for ad-hoc interactive use.

---

### Change 2: Update `transcript-primary.md:12-14` — proactive Bash fetch for query 3B

**Decision**: Extend `warmup_cache.sh` / `warmup_cache.py` with `--transcript $TRANSCRIPT_ID` mode. Do NOT provide an inline Python template for agent transcription.

**Reasoning for script over inline template**:

1. **100% transcription reliability**: E1 proved that LLM transcription of complex queries is unreliable at 52 lines. A 15-line Python template is dramatically simpler, but the only way to guarantee zero transcription error is to eliminate transcription entirely. If the bar is "100% reliable," script wins.

2. **No hardcoded credentials**: An inline template would embed `auth=('neo4j', 'Next2020#')` in a prompt file. The script approach uses the shell wrapper's env vars — same pattern as all other scripts, no credential drift.

3. **One entry point**: The agent already knows `warmup_cache.sh $TICKER` from Change 1. Adding `--transcript $TRANSCRIPT_ID` is a natural extension — one tool to remember, consistent pattern.

4. **Not over-engineering**: This is NOT a generic `fetch_content.py` for all assets. It's a `--transcript` flag on an existing script. 8-K exhibits are under 50KB, news bodies are small — only transcript needs this. The script grows by ~20 lines (one query, one file write).

**Current text** (reactive):
```
## MCP Truncation Workaround

If query 3B result is truncated by the MCP tool, re-run the query via Bash+Python and save to `/tmp` for parsing.
```

**New text** (proactive, script-only):
```
## Content Fetch — Always Use Bash for 3B

Transcript content (query 3B) typically exceeds 50KB and triggers SDK output persistence.
Always fetch via Bash instead of MCP to avoid parse failures:

    ```bash
    bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh $TICKER --transcript $TRANSCRIPT_ID
    ```

Result written to `/tmp/transcript_content_{TRANSCRIPT_ID}.json`. Read this file instead of parsing MCP output.
```

**Fixes**: E4b (transcript content truncation).

**Regression risk**: Zero. Only changes documentation/instructions. No existing code modified.

---

### Change 3: Update `guidance_write_cli.py:174` — better error message for E2

**Current code** (`guidance_write_cli.py:174-176`):
```python
if not source_id or not source_type or not ticker:
    print(json.dumps({"error": "Missing required top-level fields: source_id, source_type, ticker"}))
    sys.exit(1)
```

**New code** (additive hint field, existing error string preserved exactly):
```python
if not source_id or not source_type or not ticker:
    error_data = {"error": "Missing required top-level fields: source_id, source_type, ticker"}
    if 'company' in data or 'source' in data:
        error_data["hint"] = "Detected nested 'company'/'source' objects — use flat top-level fields instead. See enrichment-pass.md JSON example."
    print(json.dumps(error_data))
    sys.exit(1)
```

**Why separate `hint` field instead of appending to `error` string**: The existing `error` string is preserved character-for-character. The `hint` is additive-only — a new JSON key that didn't exist before. No consumer can break because no output changes; consumers only gain additional diagnostic context. This is the most conservative possible change to the error path.

**Fixes**: Hardens E2 — agent gets a clear diagnostic hint when it uses the wrong schema shape.

**Regression risk**: Zero. This code only executes on the error path (payload already invalid). Normal payloads never reach this branch. The `error` field value is unchanged.

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

- Does NOT create a generic `fetch_content.py` for all assets — only transcript content exceeds 50KB. 8-K exhibits are under 50KB, news bodies are small. The `--transcript` flag on `warmup_cache.py` handles the one case that needs it.
- Does NOT modify query 2B in `queries-common.md` — the query itself is correct, the problem is agent transcription. Queries remain for ad-hoc interactive use.
- Does NOT change E3 classification — MONITORING remains correct
- Does NOT modify any existing working code paths — all changes are additive (new scripts) or to error messages/documentation/pass briefs
- Does NOT tighten the 2B axis filter (E3 quality improvement) — deferred, optional, would go inside warmup_cache.py if implemented later

---

## External Critique Review

### Round 1 (2026-03-09, v1 → v2)

ChatGPT reviewed the v1 plan and raised 5 objections. Independent verification results:

| # | Objection | Verdict | Action |
|---|-----------|---------|--------|
| 1 | "Pass briefs not wired into warmup helper" | **WRONG** — plan already included this in Change 1 with exact line numbers (primary-pass.md:19-20, enrichment-pass.md:21-22) and explicit rationale paragraph. ChatGPT cited wrong line numbers (`:13` and `:15` — those are section headers, not the 2A/2B references). | None |
| 2 | "CLI hint should be separate JSON field" | **Valid micro-improvement** — preserves exact error string, hint is additive-only. No practical impact (only consumer is an LLM) but marginally cleaner API contract. | Adopted in Change 3 |
| 3 | "Script > inline template for transcript" | **Valid** — plan had flagged this as "Decision needed." For literal 100% reliability, eliminating transcription entirely via script is the right call. Also avoids hardcoded credentials in prompt file. | Adopted in Change 2 |
| 4 | "Use existing get_manager() connection pattern" | **Valid direction, mostly moot** — plan already used shell wrapper pattern. Explicitly specifying `get_manager()` is cleaner than raw Bolt. | Adopted in Change 1 |
| 5 | "'Zero regression risk' overstated" | **Pedantically valid** — "zero regression risk" (no existing code modified) is accurate. "Zero risk of new defects" would be inaccurate. New code always carries nonzero defect risk. | Scope line updated |

### Round 2 (2026-03-09, v2 → v3)

ChatGPT reviewed the v2 plan and raised 6 findings. **Critical context**: ChatGPT analyzed the v1 text, not v2 — 3 of 6 findings were already fixed.

| # | Finding | Verdict | Action |
|---|---------|---------|--------|
| 1 | Path inconsistency — `scripts/warmup_cache.sh` vs bare `warmup_cache.sh` vs full `.claude/skills/...` path | **VALID** — three different path formats for the same file. Pass brief edits (the text agents literally type) especially need the full path. | Fixed: all references now use full paths. File summary now declares base path. |
| 2 | "Unresolved fork / Decision needed marker" | **WRONG** — cites v1 lines 140, 171. V2 has no inline template, no "Decision needed." Decision was made at v2 L122 with 4-point reasoning. | None — already fixed in v2 |
| 3 | "Hint not reflected as separate field" | **WRONG** — cites v1 L188. V2 L170-178 already uses separate `error_data["hint"]` field with explicit rationale at L180. | None — already fixed in v2 |
| 4 | "Generic `/tmp/transcript_content.json`" | **WRONG** — cites v1 L162. V2 L152 already uses `{TRANSCRIPT_ID}` in the filename. | None — already fixed in v2 |
| 5 | Safety claims overstated | **PARTIALLY WRONG** — v2 scope line already says "New code carries standard defect risk." The per-change "Regression risk: Zero" claims are accurate (no existing code modified). | None — already qualified in v2 |
| 6 | No verification section | **VALID** — plan specifies what to build but not how to confirm it works. A smoke-test procedure strengthens confidence. | Fixed: Verification section added (V1-V4) |

---

## Verification (post-implementation smoke tests)

### V1: Warmup cache parity

```bash
# Run the new script
bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh AAPL

# Verify output files exist and contain data
python3 -c "import json; d=json.load(open('/tmp/concept_cache_AAPL.json')); print(f'2A: {len(d)} concepts')"
python3 -c "import json; d=json.load(open('/tmp/member_cache_AAPL.json')); print(f'2B: {len(d)} members')"
```

Expected: 2A returns ~222 concepts, 2B returns ~83 members (for AAPL). Compare row count and spot-check 2-3 values against a manual MCP query of 2A/2B to confirm identical data.

### V2: Transcript fetch

```bash
bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh AAPL --transcript AAPL_2025-01-30T17.00

# Verify output
python3 -c "import json; d=json.load(open('/tmp/transcript_content_AAPL_2025-01-30T17.00.json')); print(f'Records: {len(d)}, keys: {list(d[0].keys()) if d else \"empty\"}')"
```

Expected: 1 record with keys `transcript_id`, `call_date`, `company`, `fiscal_quarter`, `fiscal_year`, `prepared_remarks`, `qa_exchanges`. File size should be 50-65KB (matching the persisted output sizes observed in worker logs).

### V3: CLI hint field (E2 hardening)

```bash
# Create a deliberately malformed payload
echo '{"company":{"ticker":"TEST"},"source":{"source_id":"x"},"items":[]}' > /tmp/test_e2.json
python3 .claude/skills/earnings-orchestrator/scripts/guidance_write_cli.py /tmp/test_e2.json --dry-run 2>/dev/null; echo $?
```

Expected: Exit code 1, stdout JSON with `"error": "Missing required top-level fields: source_id, source_type, ticker"` (exact original string) plus `"hint": "Detected nested..."`. Verify `error` field is character-identical to the current version.

### V4: End-to-end dry run

Run one AAPL transcript extraction with `--dry-run` using the updated pass briefs. Confirm the agent:
1. Calls `bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh AAPL` (not MCP queries 2A/2B)
2. Calls `bash .claude/skills/earnings-orchestrator/scripts/warmup_cache.sh AAPL --transcript $TID` (not MCP query 3B)
3. Reads JSON files from `/tmp/` (not MCP output)
4. Produces the same extraction results as a prior run

---

## File Change Summary

All paths relative to project root `/home/faisal/EventMarketDB/`.

| File | Action | Lines Changed |
|------|--------|---------------|
| `.claude/skills/earnings-orchestrator/scripts/warmup_cache.sh` | CREATE | ~20 lines (shell wrapper) |
| `.claude/skills/earnings-orchestrator/scripts/warmup_cache.py` | CREATE | ~80 lines (queries 2A/2B + transcript 3B + JSON write) |
| `.claude/skills/extract/types/guidance/primary-pass.md` | EDIT | Lines 19-20 (reroute 2A/2B to Bash) |
| `.claude/skills/extract/types/guidance/enrichment-pass.md` | EDIT | Lines 21-22 (same reroute) |
| `.claude/skills/extract/types/guidance/assets/transcript-primary.md` | EDIT | Lines 12-14 (proactive Bash fetch for 3B) |
| `.claude/skills/earnings-orchestrator/scripts/guidance_write_cli.py` | EDIT | Lines 174-176 (hint field addition) |
| `.claude/plans/extraction-pipeline/extraction-pipeline-tracker.md` | EDIT | E1 description + E4 split |
| `.claude/plans/extraction-pipeline/extractionPipeline_v2.md` | EDIT | Line 1272 (issue #10 rewording) |

**Total**: 2 new files (~100 lines), 6 file edits (documentation + 4-line code change).

---

*Plan created 2026-03-08. v2 refined 2026-03-09 (5 objections: 2 adopted, 1 wrong, 2 moot). v3 refined 2026-03-09 (6 findings: 2 valid and fixed, 3 wrong (analyzed v1 not v2), 1 partially wrong (already qualified)). Based on independent verification of agent transcripts, worker logs, source code, and live Neo4j queries.*
