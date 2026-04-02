# v2.1.88 Test Run Plan

**Date**: 2026-03-31
**Version**: v2.1.88 (March 30, 2026 release)
**Tests**: 4 (3 hook tests + 1 SDK test)

## Pre-requisites

### 1. Verify CLI version
```bash
claude --version
# Must show 2.1.88+
```

### 2. Add test hooks to settings.json

Add these entries to `.claude/settings.json`. **Do NOT remove existing hooks** — add alongside them.

#### Under `hooks.PermissionDenied` (NEW section):
```json
"PermissionDenied": [
  {
    "hooks": [
      {
        "type": "command",
        "command": "/home/faisal/EventMarketDB/.claude/hooks/test-v188-permission-denied.sh"
      }
    ]
  }
]
```

#### Under `hooks.PreToolUse` (ADD to existing array):
```json
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "command": "/home/faisal/EventMarketDB/.claude/hooks/test-v188-if-compound.sh",
      "if": "Bash(* && git *)"
    },
    {
      "type": "command",
      "command": "/home/faisal/EventMarketDB/.claude/hooks/test-v188-if-control.sh"
    }
  ]
},
{
  "matcher": "Read",
  "hooks": [
    {
      "type": "command",
      "command": "/home/faisal/EventMarketDB/.claude/hooks/test-v188-filepath-log.sh"
    }
  ]
}
```

### 3. Clear old logs
```bash
rm -f /tmp/test-v188-*.log
```

## Test Execution Order

### Test A: file_path absolute (Task #302) — Run FIRST, easiest
```bash
claude -p "You are test-v188-filepath-absolute. Follow the instructions in .claude/agents/test-v188-filepath-absolute.md exactly."
```
**What to check**: `/tmp/test-v188-filepath-log.log` — do `file_path` values start with `/`?
**Output**: `earnings-analysis/test-outputs/test-v188-filepath-absolute.txt`

### Test B: `if` compound commands (Task #301) — Run SECOND
```bash
claude -p "You are test-v188-if-compound. Follow the instructions in .claude/agents/test-v188-if-compound.md exactly."
```
**What to check**: Compound hook fires for `&& git` commands only, control fires for all.
**Output**: `earnings-analysis/test-outputs/test-v188-if-compound.txt`

### Test C: PermissionDenied hook (Task #300) — Run THIRD, requires auto mode
```bash
claude --mode auto -p "You are test-v188-permission-denied. Follow the instructions in .claude/agents/test-v188-permission-denied.md exactly."
```
**What to check**: `/tmp/test-v188-permission-denied.log` — did hook fire? What's the payload?
**IMPORTANT**: Must use `--mode auto` to trigger auto mode classifier denials.
**Output**: `earnings-analysis/test-outputs/test-v188-permission-denied.txt`

### Test D: SDK is_error (Task #303) — Run LAST, independent
```bash
cd /home/faisal/EventMarketDB
# The agent will create and run the Python test script
claude -p "You are test-v188-sdk-error. Follow the instructions in .claude/agents/test-v188-sdk-error.md exactly."
```
**What to check**: Does `--output-format json` response contain `is_error: true` when max turns hit?
**Output**: `earnings-analysis/test-outputs/test-v188-sdk-error.txt`

## Post-test Cleanup

1. Remove test hooks from `.claude/settings.json` (the PermissionDenied section + 2 PreToolUse entries)
2. Clean logs: `rm -f /tmp/test-v188-*.log`
3. Update Infrastructure.md with findings

## Files Created

| Type | Path |
|------|------|
| Agent | `.claude/agents/test-v188-permission-denied.md` |
| Agent | `.claude/agents/test-v188-if-compound.md` |
| Agent | `.claude/agents/test-v188-filepath-absolute.md` |
| Agent | `.claude/agents/test-v188-sdk-error.md` |
| Hook | `.claude/hooks/test-v188-permission-denied.sh` |
| Hook | `.claude/hooks/test-v188-if-compound.sh` |
| Hook | `.claude/hooks/test-v188-if-control.sh` |
| Hook | `.claude/hooks/test-v188-filepath-log.sh` |
| Plan | `.claude/plans/test-v188-run-plan.md` |

## Also document (no test needed)

| Item | Status |
|------|--------|
| `/stats` subagent token counting | Just run `/stats` after any subagent session |
| Nested CLAUDE.md de-dupe | Observe in long sessions — fewer re-injections |
| Prompt cache stability | Internal — no way to directly test |
