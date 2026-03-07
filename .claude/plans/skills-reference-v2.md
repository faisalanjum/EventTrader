# Plan: Update skills-reference.md to v2.0

## Context
The `docs/claude/skills-reference.md` (v1.0, 2026-01-03) is significantly outdated. Research across all 13 source URLs + related pages found ~15 major gaps: 6 new frontmatter fields, string substitutions, dynamic context injection, bundled skills, commands/skills unification, invocation control, permissions, extended thinking, character budget, open standard (agentskills.io), plugin skills, monorepo discovery, `--add-dir` loading, Task→Agent rename. The core structure (progressive disclosure, best practices, anti-patterns, workflows) remains valid but needs additions.

## File to modify
- `/home/faisal/EventMarketDB/docs/claude/skills-reference.md` (in-place update, same file)

## Approach: Surgical edits preserving existing structure

Keep the existing 15-section structure intact. Add new sections where needed, update existing sections with new content. Don't rewrite what's still accurate.

### Edit 1: Version header (line 1-4)
- Change version to 2.0, date to 2026-03-04
- Update scope line: remove "CLI only" — skills now follow the Agent Skills open standard

### Edit 2: Table of Contents (lines 8-24)
- Insert new sections after existing ones:
  - §5.5 → **Invocation Control** (new section between tool restrictions and descriptions)
  - §5.6 → **String Substitutions & Arguments**
  - §5.7 → **Dynamic Context Injection**
  - §5.8 → **Subagent Integration (context: fork)**
  - §5.9 → **Skill Permissions**
- Renumber remaining sections accordingly
- Better approach: insert new sections as §5 through §9, shift old §6-§15 to §10-§19

### Edit 3: §1 What Are Skills? (lines 28-70)
- Add note: Skills follow the [Agent Skills](https://agentskills.io) open standard (30+ tools)
- Add note: Custom commands have been merged into skills (`.claude/commands/` still works)
- Add **Bundled Skills** subsection: `/simplify`, `/batch`, `/debug`
- Add "ultrathink" extended thinking note

### Edit 4: §2 Frontmatter Attributes (lines 74-125)
- Update file format example: model → `claude-opus-4-6`
- **Expand table from 4 to 10 fields**:
  - `name` → change from Required to **Optional** (defaults to directory name)
  - `description` → change to **Recommended** (not strictly required in CLI)
  - Keep `allowed-tools` and `model`
  - Add `argument-hint` (string, hint for autocomplete)
  - Add `disable-model-invocation` (boolean, prevent auto-loading)
  - Add `user-invocable` (boolean, hide from `/` menu)
  - Add `context` (string, set to `fork` for subagent)
  - Add `agent` (string, subagent type for `context: fork`)
  - Add `hooks` (object, lifecycle hooks scoped to skill)
- Note open standard additional fields: `license`, `compatibility`, `metadata`

### Edit 5: §3 Directory Structure (lines 129-184)
- Update Plugin location path to `<plugin>/skills/<skill-name>/SKILL.md` with namespace note
- Add **Nested Directory Discovery** subsection (monorepo support)
- Add **Skills from --add-dir** note (with live change detection)

### Edit 6: NEW §5 — Invocation Control (insert after §4)
- Full invocation control matrix table:
  - (default): user yes, claude yes, description in context
  - `disable-model-invocation: true`: user yes, claude no, description NOT in context
  - `user-invocable: false`: user no, claude yes, description in context
- Explain reference vs task content distinction

### Edit 7: NEW §6 — String Substitutions & Arguments
- Variable table: `$ARGUMENTS`, `$ARGUMENTS[N]`, `$N`, `${CLAUDE_SESSION_ID}`
- Example: `/migrate-component SearchBar React Vue`
- Note: if `$ARGUMENTS` not in content, arguments appended as `ARGUMENTS: <value>`

### Edit 8: NEW §7 — Dynamic Context Injection
- `` !`command` `` syntax explanation
- PR summary example with `gh pr diff`, `gh pr view --comments`
- Note: preprocessing, not Claude execution

### Edit 9: NEW §8 — Subagent Integration
- `context: fork` explanation
- `agent` field options (Explore, Plan, general-purpose, custom from `.claude/agents/`)
- Table: skill vs subagent relationship
- Note: subagent `skills` field (inverse direction)

### Edit 10: NEW §9 — Skill Permissions
- Three control methods: deny Skill tool, allow/deny specific (`Skill(name)`, `Skill(name *)`), frontmatter
- Character budget: 2% of context window, `SLASH_COMMAND_TOOL_CHAR_BUDGET` env var
- `/context` to check for excluded skills

### Edit 11: §12 (old) → §16 Skills vs Other Features
- Update: remove "Slash Commands" as separate row — note commands merged into skills
- Add Plugins row
- Add Memory row

### Edit 12: §13 (old) → §17 Examples
- Update model references from 4.5 to 4.6
- Add Example 4: Forked Subagent Skill (using `context: fork`, `agent`, dynamic injection)

### Edit 13: §14 (old) → §18 Troubleshooting
- Add: "Claude doesn't see all my skills" (character budget)
- Add: "Skill triggers too often" (use `disable-model-invocation: true`)

### Edit 14: §15 (old) → §19 Checklist
- Add checklist items for new fields
- Add: invocation control configured appropriately
- Add: arguments/substitutions tested if used

### Edit 15: Quick Reference Card
- Update frontmatter template with all 10 fields
- Update model reference to 4.6

### Edit 16: Sources
- Update date to 2026-03-04
- Add agentskills.io and code.claude.com/docs/en/sub-agents
- Note URL redirects (anthropic.com/engineering → claude.com/blog)
- Add GitHub releases/changelog as source

## Verification
- Read the final file and verify all 15 gaps from research are addressed
- Check line count stays reasonable (target ~1400-1500 lines, up from 1099)
- Verify all internal links/anchors are consistent after renumbering
