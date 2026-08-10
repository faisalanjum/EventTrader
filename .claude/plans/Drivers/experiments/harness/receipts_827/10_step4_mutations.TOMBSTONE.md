# TOMBSTONE — 10_step4_mutations.json (deleted, P-O6 #827)

`receipts_827/10_step4_mutations.json` was DELETED. This file replaces it so the
absence is a recorded decision rather than a gap someone re-creates.

## What it was, and why it could not stay

An in-tree receipt of the step-4 mutation battery, written 2026-08-01T15:52:14Z,
claiming:

    "#827 step 4 — 56 staged-tree mutations"

The registry it describes now holds **295** entries. The file therefore read as a
CURRENT certification of a set roughly five times smaller than the one being
certified — and it would keep reading that way, in-tree, for anyone who opened it
without cross-checking the registry's length.

Two further reasons it cannot live in the tree at all:

1. **It certifies the tree it lives in.** A receipt of a run over tree T, stored
   inside T, changes T — so the artifact can never describe the object it is
   committed into. That is why P-O6 makes the final receipt EXTERNAL.
2. **It is a RUN output, and the RUN happens after T is captured.** Nothing in
   the repository may claim that future result in advance.

## Where the proof lives now

The final receipt is EXTERNAL:

    /home/faisal/.core827_backups/step4_mutations_final_receipt.json

produced by `receipts_827/step4_mutations.py --include-live` during the O6 RUN
phase, after the one tree T is captured. As of P-O6 PREP part 2 that receipt also
records `staged_tree_id`, `staged_tree_id_at_end` and `staged_tree_stable`, so it
names the exact tree it certified and fails if the index moved beneath it.

## What changed alongside this deletion

* `make_index.py` no longer lists this file as an in-tree receipt it can demand —
  it describes the external requirement instead. The index's own
  "named-but-absent is a failure" rule is untouched and still enforced for every
  receipt that IS in-tree.
* `case_map.py` no longer states the run's RESULT ("56 rows, every one CAUGHT …
  problems []"). A source file may say what must be produced; it may not assert
  the outcome of a run that has not happened in this tree.

Nothing else referenced the deleted file as data.
