# Verified grading-code checkpoint (Codex SEQ 1890) — STAGED CANDIDATE ONLY

Preservation of independently reviewed grading CODE. **Not** completed A7/EXP-5
evidence, not a passing score, not an activation, and **not a standalone
runnable tree** — see the external prerequisite below.

## What is staged, and why each part

* The reviewed **1881 grading view**: the six approved owners, the corrected
  G23 lifecycle test, and the module closure they import.
* The **runtime files those owners OPEN**, which imports alone do not name:
  `launch_kfields_drafts.manifest.json`, `a2_runtime_freeze.json`,
  `scorers/grade_batch.js`, `launch_exp5_readers.manifest.json`,
  `exp5_prompt_contract.manifest.v3.json`, and the other prompt/contract and
  launcher assets in the harness directory.
* The **symlinks** by which those owners reach already-committed data. A
  committed target does not recreate a missing link; the negative control below
  proves the link itself is required.
* The **grading scripts and raw evidence** from unit_1881 — results, pytest
  stdout/stderr and every raw attempt exit — copied out of the gitignored
  `logs/` tree.

## Already in HEAD — deliberately not re-copied

* `driver/` (89 tracked modules) — the owners' external package.
* The benchmark inventory and the a4 lock evidence the staged symlinks target.

## The remaining external prerequisite — named, not hidden

`build_kfields_key` reads
`/tmp/…/scratchpad/a3_serial_dir.txt` **at import time**. That path is supplied
by the recovery boundary bind map, not by this tree, so the checkpoint is not
standalone. Reconstruction command:
`boundary.py --host <unit map>.tsv <payload>` with the a4 lock evidence
(already in HEAD) bound at that logical path. Every other checked entrypoint
resolves from HEAD+index alone.

## Resolution check (against HEAD+index, not the working directory)

Positive: `a1_plan_path`, `a1_plan`, `owner_hashes`, the five owner imports,
`validate_benchmark_inventory`, and reading the inventory **through its link**
all resolve. Negative controls each fail exactly where expected: dropping
`launch_kfields_drafts.manifest.json` breaks `a1_plan`; dropping
`scorers/grade_batch.js` breaks `owner_hashes`; dropping the inventory symlink
breaks the inventory read while its target stays committed.

## VERIFIED scope

Mechanical grading checks CLOSED at Codex SEQ 1882. Proof references: 1871
(approved owners) · 1879 (test closure) · 1881 (saved-state collision
corrected; retry proved at the later reader). Staged 1881 results: continuation
4/4, retry and mutations 9/9, after-batch re-audit 4/4, affected module 79
passed; the five failed collision-measurement attempts are preserved with their
raw exits.

## OPEN — nothing here claims otherwise

* The original unit_1773 run is **FAILED** on its two exact P2 duplicate groups.
* Every other real grade is **UNMEASURED**.
* New grader role qualification and the fresh source/key/producer work are open.
* The 1888 source package's fixed-map hash item is recorded there and is
  **unrepaired**; it is not a reason to change grading code.

## Limitations recorded on purpose

TEST fixtures are declared TEST evidence and approve no fact. The 31-file
baseline, the 79-test module, the 108 production routes and the closed
handle/kind matrix were NOT re-run for this checkpoint. unit_1876's saved
workflow histories share one path, so only its recomputed bindings,
populations, routes, score objects and decisions stand.
