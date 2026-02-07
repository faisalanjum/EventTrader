---
name: test-manifest-gate
description: Validate manifest + TaskGet-only validation gate logic
allowed-tools:
  - TaskCreate
  - TaskUpdate
  - TaskGet
  - TaskList
  - Write
  - Read
permissionMode: dontAsk
---

# Test: Manifest + Validation Gate (TaskGet-Only)

**Objective**: Prove that a manifest listing Task IDs can be validated via TaskGet, and that invalid outputs are detected (fail-closed).

## Steps

### 1) Create three GX test tasks

Create three tasks and record their IDs:
- subject: "GX-TEST-1"
- subject: "GX-TEST-2"
- subject: "GX-TEST-3"

description can be "pending" initially.

### 2) Write outputs via TaskUpdate

Update each task's description:

- GX-TEST-1: **valid 18-field guidance line**
```
quarter|2025|1|Total|Revenue|10|11|12|B USD|as-reported|explicit|.|news|bzNews_1|full|2025-01-01|body|Example guidance
```

- GX-TEST-2: **valid 18-field guidance line**
```
quarter|2025|1|Total|Gross Margin|45|45.5|46|%|as-reported|calculated|.|news|bzNews_2|full|2025-01-02|body|Example margin guidance
```

- GX-TEST-3: **invalid line (too few fields)**
```
quarter|2025|1|Total|Revenue|10|11|12|B USD|as-reported
```

### 3) Write manifest file

Write a manifest JSON to:
`earnings-analysis/test-outputs/manifest-gate.json`

Format:
```
{
  "ticker": "TEST",
  "quarter": "QX_FY0000",
  "expected_count": 3,
  "tasks": [
    {"id": "<GX-TEST-1 ID>", "type": "guidance"},
    {"id": "<GX-TEST-2 ID>", "type": "guidance"},
    {"id": "<GX-TEST-3 ID>", "type": "guidance"}
  ]
}
```

### 4) Validate via TaskGet (TaskGet-only)

For each task ID in the manifest:
- TaskGet the task
- Split `description` by lines
- For each non-empty line:
  - Count fields by splitting on `|`
  - **Pass if field count == 18** (17 pipes)
  - Fail otherwise

### 5) Write results

Write results to:
`earnings-analysis/test-outputs/manifest-gate-test.txt`

Include:
- Manifest path
- Task IDs
- Per-task validation results
- Overall status: **EXPECTED FAIL** (because GX-TEST-3 is invalid)

## Output Format

```
TEST: manifest-gate
TIMESTAMP: {ISO timestamp}
MANIFEST: earnings-analysis/test-outputs/manifest-gate.json

TASKS:
- {id1}: VALID (18 fields)
- {id2}: VALID (18 fields)
- {id3}: INVALID ({field_count} fields)

OVERALL: EXPECTED FAIL (invalid task detected)
```

After writing, return a short summary.
