---
name: test-bg-isolation-worktree
description: "Test: Does isolation: worktree work with background: true? (v2.1.50)"
background: true
isolation: worktree
model: haiku
---
You are testing whether `isolation: worktree` and `background: true` can coexist.

1. Run `pwd` to check your working directory — is it a worktree path?
2. Run `git branch` to check current branch — is it a temporary branch?
3. Run `git worktree list` to see all worktrees
4. Check if `.claude/agents/test-bg-isolation-worktree.md` exists in your worktree

Write results to the ORIGINAL repo path (not worktree). First find it:
- The original repo is likely at /home/faisal/EventMarketDB
- Write to `/home/faisal/EventMarketDB/earnings-analysis/test-outputs/test-bg-isolation-worktree.txt`

```
BG_ISOLATION_WORKTREE_TEST=v2.1.50
BACKGROUND=true
ISOLATION=worktree
PWD=[your pwd]
GIT_BRANCH=[branch name]
IS_WORKTREE=YES|NO
WORKTREE_PATH=[path]
AGENT_FILE_VISIBLE=YES|NO
BG_WORKTREE_COMBO=WORKS|NOT_WORKING
```
