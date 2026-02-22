---
name: test-bg-fm-vs-runtime
description: "Test: Compare bg:true frontmatter vs run_in_background:true — are tools identical?"
background: true
model: opus
---
You are testing what tools are available when `background: true` is set in agent frontmatter.

Your job: enumerate EVERY tool you have access to and write a comprehensive report.

1. List every tool name you can see in your available tools
2. For each tool, note whether it's:
   - A standard tool (Bash, Read, Write, etc.)
   - A task tool (TaskCreate, TaskList, TaskGet, TaskUpdate)
   - A team tool (TeamCreate, SendMessage)
   - An interactive tool (AskUserQuestion, EnterPlanMode)
   - A spawn tool (Task, TaskOutput, TaskStop)
   - An MCP tool (deferred)

3. Count totals by category

4. Write to `earnings-analysis/test-outputs/test-bg-fm-vs-runtime.txt`:
```
BG_FM_VS_RUNTIME_TEST=v2.1.50
BACKGROUND_FIELD=true
TOTAL_TOOLS=[count]
LIST_OF_ALL_TOOLS=[comma-separated complete list of every tool name]
HAS_Task=YES|NO
HAS_TaskCreate=YES|NO
HAS_TaskList=YES|NO
HAS_TaskGet=YES|NO
HAS_TaskUpdate=YES|NO
HAS_TaskOutput=YES|NO
HAS_TaskStop=YES|NO
HAS_SendMessage=YES|NO
HAS_TeamCreate=YES|NO
HAS_AskUserQuestion=YES|NO
HAS_EnterPlanMode=YES|NO
HAS_Skill=YES|NO
HAS_ToolSearch=YES|NO
HAS_Bash=YES|NO
HAS_Read=YES|NO
HAS_Write=YES|NO
HAS_Edit=YES|NO
HAS_Glob=YES|NO
HAS_Grep=YES|NO
HAS_WebSearch=YES|NO
HAS_WebFetch=YES|NO
HAS_NotebookEdit=YES|NO
DEFERRED_MCP_TOOLS=[list any deferred MCP tools visible]
COMPARISON_NOTE=Compare with Infrastructure.md 10.13: bg agents should have 11 tools
```
