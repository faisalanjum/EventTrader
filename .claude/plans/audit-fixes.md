# Audit Fixes Plan (Temporary)

Created: 2026-02-11 | Delete after all items complete.

---

## CRITICAL (Blocks Earnings Workflow)

- [x] **C1**: Fill in earnings-prediction workflow — replace `{N}`, `{Name}`, `{Description}` placeholders
  - File: `.claude/skills/earnings-prediction/SKILL.md:69-75`

- [x] **C2**: Fix orchestrator hook command — bare name → full path
  - File: `.claude/skills/earnings-orchestrator/SKILL.md:11`
  - Change: `"build_orchestrator_event_json"` → `"python3 $CLAUDE_PROJECT_DIR/.claude/hooks/build_orchestrator_event_json.py"`

- [x] **C3**: Replace deprecated `TodoWrite` with `TaskCreate`/`TaskUpdate` in earnings-attribution
  - File: `.claude/skills/earnings-attribution/SKILL.md:4,82`

- [x] **C4**: Remove deprecated `filtered-data` from earnings-prediction skills
  - File: `.claude/skills/earnings-prediction/SKILL.md:25`

- [x] **C5**: Fix feature flag guard — `batch_embeddings_for_nodes()` checks wrong flag for QAExchange
  - File: `neograph/mixins/embedding.py:242`
  - Bug: Always checks `ENABLE_NEWS_EMBEDDINGS`, even for QAExchange label

---

## ISSUE (Evidence-Standards Gaps) — DONE 2026-02-11

- [x] **I1-I5**: Full rewrite to v2. Removed stale domain table, prose format, PIT markers. Added 4 universal rules + domain boundary with date-anchor exception. Attached to all 13 data sub-agents. Fixed stale cookbook reference in DataSubAgents.md.

---

## ISSUE (Benzinga / Hooks)

- [x] **I6**: Fix `pit_time` import path fragility in pit_fetch.py
  - File: `.claude/skills/earnings-orchestrator/scripts/pit_fetch.py:22`

- [x] **I7**: Consolidate `news-driver-bz` to use `pit_gate.py` instead of `validate_pit_hook.sh`
  - File: `.claude/agents/news-driver-bz.md:17`

- [x] **I8**: Fix `news-driver-bz` absolute hook path → use `$CLAUDE_PROJECT_DIR`
  - File: `.claude/agents/news-driver-bz.md:17`

---

## ISSUE (Vector Search)

- [x] **I9**: Create standalone QA similarity search script
  - Missing: `.claude/skills/earnings-orchestrator/scripts/find_similar_qa.py`

- [ ] **I10**: Uncomment/activate index-based `db.index.vector.queryNodes()` in embedding mixin
  - File: `neograph/mixins/embedding.py:1107-1121`

- [x] **I11**: Fix `initialization.py` to check both embedding flags for ChromaDB init
  - File: `neograph/mixins/initialization.py:234`

- [ ] **I12**: Add unit tests for embedding generation and vector search
  - Missing files

---

## ISSUE (PIT Hook Coverage)

- [ ] **I13**: Add `pit_gate.py` PostToolUse hook to `neo4j-report`
- [ ] **I14**: Add `pit_gate.py` PostToolUse hook to `neo4j-transcript`
- [ ] **I15**: Add `pit_gate.py` PostToolUse hook to `neo4j-xbrl`
- [ ] **I16**: Add `pit_gate.py` PostToolUse hook to `neo4j-entity`

---

## ISSUE (Other)

- [ ] **I17**: Fill in `get_presentations_range.py` (currently stub)
  - File: `scripts/earnings/get_presentations_range.py`

- [ ] **I18**: Fill in orchestrator placeholder steps (3, 5, 6, 7)
  - File: `.claude/skills/earnings-orchestrator/SKILL.md:84,114,117,119`

---

## MINOR

- [ ] **M1**: Create `CLAUDE.md` at project root
- [ ] **M2**: Create `.env.example` with placeholder keys
- [ ] **M3**: Archive 17 test agents from `.claude/agents/`
- [ ] **M4**: Improve Perplexity agent docs (sparse at 17-18 lines each)
