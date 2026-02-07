---
name: test-re-arguments
description: "Retest 2026-02-05: Does $ARGUMENTS substitution work?"
context: fork
---
# Test: $ARGUMENTS

The arguments passed to this skill are: $ARGUMENTS

Write to earnings-analysis/test-outputs/test-re-arguments.txt:
- "RECEIVED: $ARGUMENTS"
- "ARGUMENTS: WORKS" if you see actual text (not literal "$ARGUMENTS")
- "ARGUMENTS: NOT_WORKING" if you see the literal string "$ARGUMENTS"
