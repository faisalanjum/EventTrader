---
name: test-bg-tools-inventory
description: "Test: What tools are available to a background: true agent?"
background: true
model: haiku
---
You are testing what tools are available when an agent has `background: true` in its frontmatter.

Your job: Write a detailed tool inventory report.

1. Try to use each of these tools and report success/failure:
   - Bash: Run `echo "BASH_WORKS"`
   - Read: Read `earnings-analysis/test-outputs/test-bg-frontmatter.txt` (or any small file)
   - Write: Write to `earnings-analysis/test-outputs/test-bg-tools-inventory.txt`
   - Edit: (skip, would need existing file)
   - Glob: Search for `*.md` in `.claude/agents/`
   - Grep: Search for "test-bg" in `.claude/agents/`
   - WebSearch: Search for "claude code version 2026"
   - WebFetch: Fetch https://example.com
   - Skill: Try invoking any test skill (skip if unsure)
   - ToolSearch: Search for "neo4j" to test MCP discovery
   - TaskCreate: Try creating a task "BG_TOOL_TEST"
   - TaskList: Try listing tasks
   - TaskGet: Try getting a task
   - TaskUpdate: Try updating a task
   - SendMessage: Try sending a message (will fail without team, that's OK)
   - AskUserQuestion: Try asking a question
   - EnterPlanMode: Try entering plan mode
   - NotebookEdit: (skip)

2. After trying MCP discovery via ToolSearch, try calling an MCP tool directly:
   - Try `mcp__neo4j-cypher__read_neo4j_cypher` with query: `RETURN 1 AS test`

3. Write ALL results to `earnings-analysis/test-outputs/test-bg-tools-inventory.txt` with format:
```
BG_TOOLS_INVENTORY_TEST=v2.1.50
BACKGROUND_FIELD=true
TOOL_Bash=WORKS|BLOCKED|ERROR
TOOL_Read=WORKS|BLOCKED|ERROR
TOOL_Write=WORKS|BLOCKED|ERROR
TOOL_Glob=WORKS|BLOCKED|ERROR
TOOL_Grep=WORKS|BLOCKED|ERROR
TOOL_WebSearch=WORKS|BLOCKED|ERROR
TOOL_WebFetch=WORKS|BLOCKED|ERROR
TOOL_Skill=WORKS|BLOCKED|ERROR
TOOL_ToolSearch=WORKS|BLOCKED|ERROR
TOOL_TaskCreate=WORKS|BLOCKED|ERROR
TOOL_TaskList=WORKS|BLOCKED|ERROR
TOOL_TaskGet=WORKS|BLOCKED|ERROR
TOOL_TaskUpdate=WORKS|BLOCKED|ERROR
TOOL_SendMessage=WORKS|BLOCKED|ERROR
TOOL_AskUserQuestion=WORKS|BLOCKED|ERROR
TOOL_EnterPlanMode=WORKS|BLOCKED|ERROR
TOOL_NotebookEdit=WORKS|BLOCKED|ERROR - [details]
TOOL_MCP_ToolSearch=WORKS|BLOCKED|ERROR - [details]
TOOL_MCP_neo4j_call=WORKS|BLOCKED|ERROR - [details]
TOTAL_TOOLS_AVAILABLE=[count]
TOTAL_TOOLS_BLOCKED=[count]
```

Be thorough. Try EVERY tool. Report exact error messages for blocked tools.
