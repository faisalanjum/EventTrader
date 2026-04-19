# Obsidian Thinking Revamp — Implementation Guide

> **STATUS: ✅ SHIPPED (2026-04-19)** — all 3 approved changes are executed on `main`; 184/184 pytest lock green; 2 orphaned `.pyc` files swept.
>
> | Change | Commit | Notes |
> |---|---|---|
> | 1. Harvester dedupe (`_first_user_matches_skill_prefix` → delegation) | `a3f2cf7` | bundled in the unified-layout feature commit |
> | 2. Orchestrator → canonical validator import | `cd33014` (T5) | **alias sunset happened earlier than this plan's text describes** — `validate_attribution.py` was DELETED (not "kept for 1 release"); orchestrator at `earnings_orchestrator.py:1812` now imports from `validate_learning` directly |
> | 3. Delete 5 dead legacy `build-*-thinking` files | `3802113` | guidance + news pairs + `build-thinking-on-complete.sh` |
> | Orphaned `.pyc` sweep | post-ship | `build-guidance-thinking.cpython-310.pyc` + `build-news-thinking.cpython-310.pyc` removed; `build-thinking-index.cpython-310.pyc` intentionally retained (live `.py` still referenced by `earnings-attribution/SKILL.md:438`) |
>
> **Reader notes:**
> - Treat body text below as HISTORICAL REFERENCE. Where Change 2 still says "keep `validate_attribution.py` in place" / "sunset after one release cycle", the shim was actually removed earlier in T5 — reality is already past the sunset point.
> - The validation grep `rg -n "build-guidance-thinking|build-news-thinking|build-thinking-on-complete" .claude scripts` now self-matches the plan file inside `.claude/plans/` and the pre-existing `.claude/archive/skills/earnings-orchestrator-v2/SKILL.md`. These are semantic hits in documentation, not live runtime references — expected.

This document is the **implementation authority for the current Obsidian thinking / extraction cleanup**.

It is intentionally based on the **live implemented code and current tests**, not on older plans. If this document conflicts with an older plan, **the implemented code and tests win**.

## Purpose

Give a new bot enough context to make the Obsidian extraction / thinking system leaner **without changing behavior** and without accidentally “cleaning up” code that is still live, still intentional, or still required for compatibility.

The goal is:

- production-grade
- minimal
- no over-engineering
- no behavior drift
- no speculative refactors

This is **not** a redesign. It is a **surgical cleanup guide**.

## Scope Boundary

Review and act only on the **currently implemented runtime and test surface**:

- `.claude/settings.json`
- `.claude/hooks/obsidian_capture.py`
- `.claude/hooks/obsidian_capture.sh`
- `.claude/hooks/validate_learning_output.py`
- `scripts/earnings/thinking_blocks.py`
- `scripts/earnings/obsidian_capture_adapter.py`
- `scripts/earnings/thinking_harvester.py`
- `scripts/earnings/result_md_renderer.py`
- `scripts/earnings/validate_learning.py`
- `scripts/earnings/validate_attribution.py`
- `scripts/earnings/earnings_orchestrator.py`
- `scripts/extraction_worker.py`
- `scripts/harvest_guidance_sessions.py`
- `.claude/skills/earnings-orchestrator/scripts/` (touched by Change 3)
- the relevant tests under `scripts/earnings/` and `scripts/`

Do **not** treat older plans as architecture truth. They are background only.

## Current Live Architecture

### 1. Raw hook capture is live and supplemental

`SubagentStop` in `.claude/settings.json` calls `.claude/hooks/obsidian_capture.sh`, which shells into `.claude/hooks/obsidian_capture.py`.

That hook:

- skips `earnings-prediction`, `earnings-attribution`, and `earnings-learner`
- still captures extraction agents and general agents
- writes raw reviewer-facing notes into:
  - `pipeline/extractions/guidance/`
  - `pipeline/news-impact/`
  - `agents/`

This hook is **live** and covered by smoke tests.

### 2. Transcript parsing is centralized

`scripts/earnings/thinking_blocks.py` is the shared parser.

It is currently responsible for:

- reading SDK JSONL
- turning entries into normalized block dicts
- handling redacted thinking detection
- preserving file order optionally for the hook adapter

This module is a **parser module**, not a generic formatting/utilities module.

### 3. Hook adaptation is separate on purpose

`scripts/earnings/obsidian_capture_adapter.py` converts parsed blocks into the legacy hook bucket shape.

It owns hook-specific behavior such as:

- result cleaning
- 2000-char tool_result truncation
- hook pairing semantics

This is the right boundary for hook-specific shaping.

### 4. Canonical thinking notes come from the harvester

`scripts/earnings/thinking_harvester.py` is the canonical writer for:

- `thinking.md`
- `thinking_{asset}.md`
- `subagents/*.md`
- `subagents_{asset}/*.md`

It handles the three real session patterns:

- `EMBED-visible`
- `EMBED-redacted`
- `FORK`

It also owns:

- skill-fork detection
- subagent linkage
- thinking markdown composition
- subagent trace rendering

### 5. Canonical result sidecars come from the renderer

`scripts/earnings/result_md_renderer.py` is the canonical writer for `result.md` sidecars from `result.json`.

It covers:

- prediction
- learning
- guidance
- baseline experiment

### 6. Prediction and learning are finalized inline

`scripts/earnings/earnings_orchestrator.py` is the live owner for prediction / learning finalization.

It already does:

- session-id stamping
- metadata stamping
- `result.md` render
- `thinking.md` harvest

### 7. Guidance is still split across three live pieces

Guidance is **not** fully inline yet.

Live flow today:

1. `scripts/extraction_worker.py` runs `/extract`
2. raw hook notes are produced by `obsidian_capture.py`
3. `scripts/harvest_guidance_sessions.py` post-hoc harvests canonical company-tree `thinking_{asset}.md`

This split is real and intentional for now. Do **not** mistake it for dead code.

### 8. Compatibility shims are still carrying real load

These are still intentionally present:

- `scripts/earnings/validate_attribution.py`
- `earnings_orchestrator.get_attribution_paths()`
- `earnings_orchestrator.finalize_attribution_result()`

Some helper scripts still import them. They are not dead yet.

## What Was Revalidated

The following targeted test net was run against the current repo state:

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest \
  scripts/earnings/test_thinking_blocks.py \
  scripts/earnings/test_obsidian_capture_adapter.py \
  scripts/earnings/test_obsidian_capture_hook_smoke.py \
  scripts/earnings/test_result_md_renderer.py \
  scripts/earnings/test_thinking_harvester.py \
  scripts/test_harvest_guidance_sessions.py -q
```

Result at review time:

- `184 passed`
- only Neo4j deprecation warnings from test process teardown

That test net is the behavioral lock for this cleanup.

## Approved Changes

These are the only cleanup changes that are recommended as part of this revamp.

## Change 1: Simplify `_first_user_matches_skill_prefix()`

### File

- `scripts/earnings/thinking_harvester.py`

### Current situation

There are two helpers in the harvester:

- `_read_first_user_content()`
- `_first_user_matches_skill_prefix()`

The second is a near-duplicate JSONL walker that differs only in the final predicate.

### Required change

Replace `_first_user_matches_skill_prefix()` with a tiny delegation wrapper around `_read_first_user_content()`.

Target shape:

```python
def _first_user_matches_skill_prefix(sub_jsonl: Path) -> bool:
    try:
        return _read_first_user_content(sub_jsonl).startswith(_SKILL_FORK_FIRST_USER_PREFIX)
    except Exception:
        return False
```

### Why this is good

- removes true local duplication
- reduces drift risk between two JSONL readers in the same module
- preserves current behavior

### Why this is regression-safe

- `_read_first_user_content()` already implements the same string/list handling
- wrapper keeps broad `except Exception` behavior
- no caller contract changes
- existing harvester tests already pin skill-fork behavior

### Validation

Run the full focused test net above.

## Change 2: Use the canonical validator import in core runtime code

### File

- `scripts/earnings/earnings_orchestrator.py`

### Current situation

Core runtime code still imports:

```python
from validate_attribution import validate_attribution_result
```

But the canonical module is now `validate_learning.py`, and `validate_attribution.py` is only a compatibility shim.

### Required change

Change only the **core runtime import** in `earnings_orchestrator.py` to:

```python
from validate_learning import validate_attribution_result
```

### Why this is good

- makes core runtime point at the canonical module
- leaves the alias file in place for compatibility
- reduces conceptual debt without breaking helper scripts

### Why this is regression-safe

- function name stays the same
- module contents are the same canonical validator
- compatibility shim remains for helpers/tests that still import it

### Important constraint

Do **not** remove the alias module in this revamp.

### Post-change note

After this import switch lands, the shim should have **zero core runtime consumers**.

That does **not** mean it is safe to remove immediately, because:

- helper / one-off scripts may still be migrated later
- the alias may still be intentionally referenced by dedicated compatibility tests

Treat this change as the beginning of the shim sunset, not the end of it.

## Change 3: Delete the dead legacy guidance + news thinking stack

### Files

- `.claude/hooks/build-thinking-on-complete.sh`
- `scripts/earnings/build-guidance-thinking.py`
- `.claude/skills/earnings-orchestrator/scripts/build-guidance-thinking.py`
- `scripts/earnings/build-news-thinking.py`
- `.claude/skills/earnings-orchestrator/scripts/build-news-thinking.py`

### Current situation

This stack targets the old layout:

- `Companies/{TICKER}/thinking/{QUARTER}/...`

It is not part of the active runtime path anymore. The only non-archive references are self-references and the dormant hook script itself.

The `build-news-thinking` pair is same-era as the `build-guidance-thinking` pair (identical old-layout target, same dormant-hook wiring pattern) and is only referenced by the dormant path.

### Required change

**Delete all 5 files** in the same cleanup. Do not archive in-tree.

### Why delete, not archive

Archiving in-tree was considered and **rejected**:

- whole-repo grep/search would still return hits inside `archive/`, so every future bot has to re-reason "is this live?" — exactly the fake complexity this revamp removes
- git history already is the audit trail (`git log --follow -- <path>`, `git show <sha>:<path>`); an in-tree archive adds no recovery capability that git doesn't already provide
- these files target a retired layout (`Companies/{TICKER}/thinking/{QUARTER}/...`), not a paused feature — there is no plausible resurrection path without a rewrite
- the revamp's stated goal is "the codebase reflects the real architecture instead of mixed old/new paths"; archiving violates that goal, deleting satisfies it

Archiving is therefore not an acceptable alternative for this cleanup.

### Why this is good

- removes truly obsolete code
- reduces confusion for future bots
- eliminates the biggest source of fake architectural complexity

### Why this is regression-safe

- active settings do not invoke `build-thinking-on-complete.sh`
- active runtime uses `thinking_harvester.py`, not `build-guidance-thinking.py`
- current canonical guidance path is:
  - `extraction_worker.py`
  - `harvest_guidance_sessions.py`
  - `thinking_harvester.py`

### Bytecode note

If matching orphaned bytecode files exist after removal, clean up only the stale targets, for example:

- `build-guidance-thinking*.pyc`
- `build-news-thinking*.pyc`

Do **not** blindly remove the whole `__pycache__` directory in the skill scripts folder, because it may also contain bytecode for still-live modules (notably `build-thinking-index*.pyc`, which is intentionally retained — see the matching non-goal below).

### Important constraint

This cleanup does **not** mean guidance canonicalization is inline yet. It only removes the old obsolete path.

## Explicit Non-Goals

These are the tempting changes that should **not** be part of this revamp.

## Do not move `_truncate_safe_fence()` into `thinking_blocks.py`

### Why not

Yes, it is duplicated between:

- `scripts/earnings/thinking_harvester.py`
- `scripts/earnings/obsidian_capture_adapter.py`

But `thinking_blocks.py` is the shared **parser** module. Moving markdown/fence rendering helpers there makes the module less coherent.

This would be a DRY win on paper but a boundary regression in practice.

### Keep instead

Leave the two local copies alone.

## Do not move `_yaml_scalar()` into `thinking_blocks.py`

### Why not

Yes, it is duplicated between:

- `scripts/earnings/thinking_harvester.py`
- `scripts/earnings/result_md_renderer.py`

But this is frontmatter-rendering logic, not transcript parsing logic.

If these are ever unified, they should go into a dedicated markdown/frontmatter utility module, **not** into the parser.

That is outside this cleanup.

### Keep instead

Leave the two local copies alone.

## Do not mutate `parse_session_blocks()` just to eliminate `_build_agent_linkage()`

### Why not

Adding extra outer-entry linkage metadata to parser output is possible, but it changes the shared parser contract for:

- hook adapter
- harvester
- parser tests

That is not a cleanup cut. It is a shared-module behavior extension.

Not worth the risk in this revamp.

## Do not remove `harvest_guidance_sessions.py`

### Why not

It is currently part of the real live guidance canonicalization path.

Removing it would break guidance company-tree thinking generation.

## Do not remove compatibility aliases yet

Do not remove in this revamp:

- `validate_attribution.py`
- `get_attribution_paths()`
- `finalize_attribution_result()`

They still have live helper-script/tests consumers.

### Sunset rule for `validate_attribution.py`

Safe removal target:

- after Change 2 has shipped
- after one release cycle
- and only if grep shows no remaining non-test consumers

If a dedicated alias-compatibility test is still intentionally present at that point, remove or rewrite the test in the same change that removes the shim.

## Do not refactor the defensive harvester helpers

Keep as-is:

- `_validate_harvest_args()`
- `_locate_subagent_files()`
- `_is_skill_fork()`
- `_tool_use_annotation()`

These may look verbose, but the current structure is readable and heavily exercised by tests.

## Do not “fix” guidance split ownership in this cleanup

Guidance split ownership is the main architectural rough edge, but it is a **separate structural change**, not a safe cleanup.

Do not bundle it into this revamp.

## Do not remove the `build-thinking-index` stack in this revamp

### Files intentionally retained

- `scripts/build-thinking-index.py`
- `scripts/build-thinking-index.sh`
- `.claude/skills/earnings-orchestrator/scripts/build-thinking-index.py`

### Why not

Although these files are same-era as the dead guidance/news-thinking builders, they are still referenced by the active `.claude/skills/earnings-attribution/SKILL.md:438`:

```
python3 $CLAUDE_PROJECT_DIR/.claude/skills/earnings-orchestrator/scripts/build-thinking-index.py {accession_no}
```

Removing them in this cleanup would fail the 0%-regression bar because the active attribution skill still invokes them.

If these should ever be removed, it must happen in a separate change that first retires or rewrites that skill call site.

## Do not archive the one-shot migration tooling in this revamp

### Files intentionally left in place

- `scripts/migrate_unified_layout.py`
- `scripts/earnings/test_migrate_unified_layout.py`

### Why not

Archiving them is not dangerous — they have zero live imports — but it also gives no production benefit. The move only shifts operator / test paths for historical tooling without improving live runtime behavior.

Under this revamp's strict standard (maximum minimalism, zero regression risk, production-grade), "safe but pointless" changes do not belong in the approved set. If repo-hygiene housekeeping is ever done separately, that is a different exercise.

### Keep instead

Leave both files where they are. The `.migration-manifest.json` in the vault continues to cover any reverse need.

## Do not consolidate the 3 A/B scripts

### Files

- `scripts/run_ab_baseline.py`
- `scripts/run_nvda_ab_sequential.py`
- `scripts/run_burl_ab_sequential.py`

### Why not

They look DRY-tempting at a glance, but they are not pure ticker-constant clones:

- NVDA uses `events[:5]` (oldest 5 quarters)
- BURL uses `events[-5:]` with a `base_idx = len(events) - 5` offset for `prev_8k_ts` tracking
- Event-window selection logic and index semantics differ by script

Unifying them would require a parameterization layer roughly the same total size, with added indirection. Not a lean cleanup — leave as-is.

## Recommended Implementation Order

Apply in this exact order:

1. simplify `_first_user_matches_skill_prefix()` in `thinking_harvester.py`
2. switch `earnings_orchestrator.py` to import from `validate_learning`
3. delete the dead legacy guidance + news thinking stack

## Commit Strategy

Use one commit per logical change:

1. `refactor(thinking-harvester): dedupe first-user skill prefix reader`
2. `refactor(orchestrator): import canonical learning validator directly`
3. `cleanup(obsidian): remove dead legacy guidance + news thinking builders`

This keeps every cleanup independently revertible.

## Validation Gate

After each behavior-preserving code change, run:

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest \
  scripts/earnings/test_thinking_blocks.py \
  scripts/earnings/test_obsidian_capture_adapter.py \
  scripts/earnings/test_obsidian_capture_hook_smoke.py \
  scripts/earnings/test_result_md_renderer.py \
  scripts/earnings/test_thinking_harvester.py \
  scripts/test_harvest_guidance_sessions.py -q
```

Expected:

- all tests pass
- no snapshot/golden drift
- only the existing Neo4j deprecation warnings may appear

For the dead-code removal step, also run:

```bash
rg -n "build-guidance-thinking|build-news-thinking|build-thinking-on-complete" .claude scripts
```

Expected after cleanup:

- zero hits for `build-guidance-thinking`, `build-news-thinking`, and `build-thinking-on-complete` anywhere under `.claude/` or `scripts/`
- the only remaining references allowed to survive are historical doc snapshots outside these trees (e.g. `docs/claude/earnings-orchestrator-review-2026-02-01.md`), which are intentionally frozen as dated reviews
- `build-thinking-index` is intentionally NOT in this grep — it is still referenced by the active `earnings-attribution/SKILL.md` and must survive this cleanup (see non-goal)

## Success Criteria

This revamp is successful if all of the following are true:

1. active runtime behavior is unchanged
2. active tests stay green
3. dead legacy guidance- and news-thinking code + its dormant hook wrapper are no longer sitting in the live surface (`build-thinking-index` stack intentionally retained per non-goal)
4. the core runtime points at canonical modules where possible
5. no shared parser contract was changed
6. no guidance ownership rewrite was attempted

## Final Instruction To The New Bot

Be conservative.

This cleanup is **not** a “make everything DRY” exercise. The right result is:

- smaller live surface
- clearer ownership
- zero behavior drift

If a change requires touching shared parser semantics, changing guidance ownership, or removing compatibility shims that still have callers, it does **not** belong in this revamp.
