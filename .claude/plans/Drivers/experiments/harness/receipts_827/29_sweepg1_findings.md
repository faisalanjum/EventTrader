# SWEEP-G1 — the bounded G1-only sweep: what it found

Scope: EXACTLY the G1 candidate roots (the 394-path universe, g1a3_manifest).
Method per the card: deletion-first; no speculative cleanup; one owner per
surviving rule. Consumes two §5c carry-forwards.

## Carry-forward 1 — CF-PROOF-TMP-1: CLOSED

`scripts/driver_seed/relocate_probe/benchmark/multiaxis_pool/final/test_column_grid.py`
execed `/tmp/cell_address_probe.WhbHsb/lock_row_extract.py` **at import time** —
a scratch directory from a July probe session.

Measured state before the fix:

| fact | value |
|---|---|
| the `/tmp` path exists? | **no** |
| file tracked by git / in the candidate manifest? | **yes / yes** |
| collectable? | **no** — errored at import in every tree |
| stale `__pycache__/lock_row_extract.cpython-311.pyc` present? | **yes**, dated Jul 14 |

The cached bytecode is why the breakage stayed quiet: the module could appear
importable from a `.pyc` whose source had vanished. A test that reaches outside
the repository proves nothing about the repository.

FIX: the import is now TREE-BOUND to `lock_row_extract.py`, the SIBLING file in
that same directory — which is itself in the candidate manifest and holds the
only definition of `aligned_column` anywhere in the tree. The `/tmp` copy was a
duplicate of a file we already ship.

PROOF: the node now collects and passes (2 passed) under the certified
environment (`-B`, `-p no:cacheprovider`), and passes again with the stale
`__pycache__` deleted — so it does not depend on cached bytecode. Deletion of
the module was NOT taken: the path is in the candidate manifest, and repointing
removes the defect without moving the candidate identity.

## Carry-forward 2 — the four D0-selected harness tools: FINDING, needs a ruling

The four are not named in any record I can find (searched the map, the freeze
record, the G2 resume state, the archived reviewer mail). So the class was
derived instead: every harness `.py` tool inside the candidate manifest must
prove necessity (Contract §5's no-unproved-machinery law).

Census over the 22 candidate harness tools — consumers = anything importing or
invoking them anywhere under `driver/`, `scripts/`, the harness, `conftest.py`:

  19 tools have consumers (1 to 13 each)
   3 tools have NONE:  build_fa_inputs · dualcik_scope · period_convention_probe

THREE ORPHANS, NOT FOUR. I am not going to force the count to match a number
whose membership was never written down.

Two facts make deletion the wrong unilateral call:

1. All three are named in `experiments/REGEX_AND_FUZZY_DEBT.md`, which states of
   itself: *"This is a register, not a work order: nothing here is scheduled."*
   It classifies their patterns as mechanical and legitimate — it records status,
   which is not the same as proving necessity, but it is also not permission to
   delete.
2. `dualcik_scope` HAS run and produced committed evidence —
   `exp1_xbrl/census.json`, `o12_bundle_notes.json`,
   `runs/2026-07-09T14-25-39Z_dryrun/dualcik_count_reconcile.json`. A tool with
   no importer is not automatically a tool with no purpose.

Deleting any of them also removes paths from the 394-path candidate, moving the
candidate identity — a §9-class change, not a sweep-local one.

RECORDED AS A CONTRACT-§9 SCOPE-CHANGE CANDIDATE, per SWEEP-G1's own completion
clause ("zero new findings, or each new finding recorded as a §9 scope-change
candidate"). Ruling needed on: (a) is the derived class the right one, given the
original four were never named; (b) does "proves necessity" admit
produced-artifact evidence and register entries, or only a live consumer.

## Other sweep observations: none

No further duplication or organization debt was found inside the G1 scope that
is not already owned by a closed row. No speculative cleanup was performed.
