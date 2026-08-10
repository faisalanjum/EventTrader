# SWEEP-G1 — the bounded G1-only sweep: CLOSED

Scope: EXACTLY the G1 candidate roots (the 394-path universe, g1a3_manifest).
Method per the card: deletion-first; no speculative cleanup; one owner per
surviving rule. Consumes two §5c carry-forwards. Both are now closed.
Denominator unchanged at 264; no new row.

## Carry-forward 1 — CF-PROOF-TMP-1: CLOSED

`scripts/driver_seed/relocate_probe/benchmark/multiaxis_pool/final/test_column_grid.py`
execed `/tmp/cell_address_probe.WhbHsb/lock_row_extract.py` **at import time** —
a scratch directory from a July probe session.

| fact, measured | value |
|---|---|
| the `/tmp` path exists? | **no** |
| tracked / in the candidate manifest? | **yes / yes** |
| collectable? | **no** — errored at import in every tree |
| stale `__pycache__/lock_row_extract.cpython-311.pyc`? | **yes**, dated Jul 14 |

The cached bytecode is why the breakage stayed quiet: a module can look
importable from a `.pyc` whose source has vanished. A test that reaches outside
the repository proves nothing about the repository.

FIX: the import is TREE-BOUND to `lock_row_extract.py`, the SIBLING file in that
same directory — itself in the candidate manifest, and the only definition of
`aligned_column` anywhere in the tree. The `/tmp` copy was a duplicate of a file
we already ship. Proof: 2 passed under the certified environment, and 2 passed
again with the stale `__pycache__` deleted. The module was NOT deleted: its path
is in the candidate manifest, and repointing fixes the defect without moving the
candidate identity.

## Carry-forward 2 — the four D0-selected harness tools: CLOSED, none deleted

### The roster is FOUR, adjudicated (reviewer ruling SEQ 863/864)

    build_fa_inputs.py · dualcik_scope.py
    period_convention_probe.py · xbrl_dryrun_materializer.py

My first pass derived a THREE-tool class from a no-consumer filter. That was the
wrong denominator and is corrected here: a standalone evidence generator is
normally invoked by hand and needs no importer, so absence of a caller is not
absence of purpose. `xbrl_dryrun_materializer` has five consumers and was
invisible to that filter while genuinely being one of the four.

### The decision rule applied (necessity, not tidiness)

* a live importer is SUFFICIENT but not NECESSARY for a manual proof tool;
* produced-artifact evidence proves necessity only where the LIVE TREE still
  names that artifact as a current input, precondition, ruling or evidence;
* **a debt-register mention alone proves nothing.** The register is explicitly
  "a register, not a work order". It is not why any of these stay.

### Evidence per tool — verified in the live tree, not quoted from the ruling

| tool | current-artifact / data-flow evidence |
|---|---|
| `dualcik_scope` | produces `dualcik_scope_proof.json`, still cited by `exhibits/ra_0004.json`, `exp1_xbrl/o12_bundle_notes.json`, `schema_bindings_probe.json` and the dryrun `manifest.json` |
| `period_convention_probe` | produces `period_convention_proof.json`, still cited by `exp1_xbrl/census.json`, `o12_bundle_notes.json` and `exhibits/ra_0003.json` |
| `build_fa_inputs` | generates the DRAFT basis — `fixtures/FA_selection.json`, `fixtures/fixture_resolutions.json` — consumed by the other probes and the materializer. Stated as the draft basis generator, NOT as a byte reproducer of the signed final fixture: later owner sign-off changes the selection |
| `xbrl_dryrun_materializer` | imported directly by `dualcik_scope.py:12` (`import xbrl_dryrun_materializer as MAT`) AND owns its retained materialized/skips evidence |

All four are justified PROOF-ONLY / post-#827 experiment utilities. **None is
deleted.**

## The six safety-comment deltas — and why six, not four

Six candidate files carry a byte-identical `+4/-0` pointer to
`REGEX_AND_FUZZY_DEBT.md` (added block sha256 prefix `baa063bc6be7f69a`), all
six in `g1a3_manifest`:

    the four above  +  key_lint.py  ·  xbrl_xxl0_verifier.py

This is owner-directed placement, not drift: `WORKORDER_STATUS.md`'s 2026-07-25
entry records that the pointer "was added at the top of all six files so it
cannot be missed in-file".

`key_lint` and `xbrl_xxl0_verifier` are NOT in the necessity carry-forward and
never were — their necessity is independently visible (key_lint is the
WorkOrder's lint/blindness owner with current callers, 12 of them;
xbrl_xxl0_verifier owns retained independent EXP-1 verification evidence). They
are sweep-scope candidate content carrying the same owner-directed pointer.

All six land in this one closure commit. No executable byte changes in any of
them; the comment prevents probe-grade patterns being promoted into
identity/write behaviour and authorizes none of them for production. One shared
register, six pointers, no duplicated rule and no runtime behaviour.

## Other sweep observations: none

No further duplication or organization debt inside the G1 scope that is not
already owned by a closed row. No speculative cleanup performed.
