---
name: test-re-error-child
description: "Retest 2026-02-05: Child that deliberately fails"
context: fork
---
# Deliberate failure

1. Try to read a file that does NOT exist: /nonexistent/path/fake.txt
2. Reply with: "ERROR_CHILD: Read failed with: [error message]"
