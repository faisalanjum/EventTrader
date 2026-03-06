---
name: evidence-standards
description: Universal evidence guardrails for extraction agents.
user-invocable: false
---

# Evidence Standards

1. Extract only items supported by the loaded source content and query results allowed for this run.
2. If an item is real but some fields are unclear, keep the item and leave unclear fields unknown/null instead of guessing.
3. Keep quotes exact; let deterministic scripts handle normalization, IDs, periods, and writes.
4. No evidence = no item. No guesses.
