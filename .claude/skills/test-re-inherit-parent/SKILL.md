---
name: test-re-inherit-parent
description: "Retest 2026-02-05: Parent WITHOUT MCP - does child inherit?"
allowed-tools:
  - Skill
  - Write
context: fork
---
# Test: Tool inheritance (parent has NO MCP, child has MCP)

1. Call /test-re-inherit-child
2. Write to earnings-analysis/test-outputs/test-re-inherit-parent.txt:
   - What child returned
   - "INHERIT_DOWN: YES" if child got MCP from you (parent)
   - "INHERIT_DOWN: NO" if child used its own allowed-tools
