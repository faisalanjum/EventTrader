---
name: test-bg-fm-tasktools
description: "Test: Does background: true agent gain TaskCreate/Update tools? (KEY question for v2.1.50)"
background: true
model: opus
tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
  - TaskCreate
  - TaskList
  - TaskGet
  - TaskUpdate
---
You are testing whether a `background: true` agent can gain access to Task tools via the `tools` frontmatter field.

Infrastructure.md says bg agents get only 11 tools and Task tools are BLOCKED.
The `tools` frontmatter field is ENFORCED on agents (v2.1.33+).
Question: Does explicitly listing TaskCreate/List/Get/Update in `tools` override the background restriction?

STEP 1: Try TaskCreate
- Try calling TaskCreate with subject="BG_FM_TASKTOOLS_TEST" and description="Test from bg:true agent with tools whitelist"
- Note exact result (success or error message)

STEP 2: Try TaskList
- Try calling TaskList
- Note exact result

STEP 3: Try TaskGet (if TaskCreate worked, use that ID)
- Note exact result

STEP 4: Try TaskUpdate (if TaskCreate worked)
- Try updating the task with description="UPDATED_BY_BG_AGENT"
- Note exact result

STEP 5: Write results to `earnings-analysis/test-outputs/test-bg-fm-tasktools.txt`:
```
BG_FM_TASKTOOLS_TEST=v2.1.50
BACKGROUND=true
TOOLS_FIELD=[TaskCreate,TaskList,TaskGet,TaskUpdate,Bash,Read,Write,Glob,Grep]
TASKCREATE=WORKS|BLOCKED|ERROR - [exact message]
TASKLIST=WORKS|BLOCKED|ERROR - [exact message]
TASKGET=WORKS|BLOCKED|ERROR - [exact message]
TASKUPDATE=WORKS|BLOCKED|ERROR - [exact message]
CONCLUSION=TOOLS_FIELD_OVERRIDES_BG_RESTRICTION|TOOLS_FIELD_DOES_NOT_OVERRIDE|PARTIAL
```
