# Verified code checkpoint (Codex SEQ 1943) — STAGED CANDIDATE ONLY

Preservation of independently reviewed CODE. **Not** a completed A7 or EXP-5
result, **not** a passing score, **not** an activation, and **not** a
standalone runnable tree — see the external prerequisite below.

Nothing here is committed or pushed. Staging only, for exact staged-tree
review.

## What is staged, and why each part

* **The current verified owners**, from the candidate side of the aligned
  comparison Codex verified at SEQ 1942: the four changed runtime owners
  (A5, G, KC, R), the two fixture helpers, and the rest of the callable-file
  closure the entrypoints reach that is NOT already published unchanged.
* **The runtime files those owners OPEN by name**, which an import graph never
  mentions: `launch_kfields_drafts.manifest.json`, `a2_runtime_freeze.json`,
  `scorers/grade_batch.js`, `owner_rulings_1383.txt` and the v4/v5/v6 findings
  files that `build_kfields_final` names as constants.
* **The one authorized test-script correction** and the control that proves it
  (`scripts/`, `docs/`), plus the closure derivation.
* **Compact proof records** (`evidence/`): the three unit freezes, the aligned
  comparison, the G1 and G2/G3 rehearsal results, the control output and every
  raw attempt exit.

## Every required current path is staged

An earlier version of this document said current owners rely on the published
1881 view through a `sys.path` fallback. **That is obsolete and removed**: the
required current sibling layout is staged, and the Git-only check below runs
with the working tree off `sys.path` and no fallback directory at all.

Included because an import graph alone never names them: files an owner opens
beside itself via `os.path.join(_HERE, …)`; the lock/candidate/signer owners,
whose own imports are roots too; the three changed focused tests; and the
**caller-selected scorer** `scorers/score_exp5_current.py`, which no import
statement mentions — `s2_g23_native_1942.py` picks it by path and hands it to
`a7_g23_build.bind_grading_scorer`.

## The one code correction in this checkpoint

`scripts/s2_g23_native_1942.py` differs from the sealed unit_1942 script by
exactly one statement:

    -   rows = kdoc.get("rows") or []
    +   rows = kdoc["batch_rows"]

`a7_g23_run.kind_candidate` publishes the batches under `batch_rows`; the only
top-level `rows` in that document sits inside `launchers`. The shipped lookup
was therefore always `None` and called EVERY kind document empty. It is
subscripted, not defaulted: a document missing the required field refuses,
because the existing schema owns that field.

Proved on the four real documents plus a missing-field case
(`evidence/CONTROL_1943.json`, 6/6):

    document           batches  expected   old        new
    nonempty_G2          20     nonempty   empty (X)  nonempty
    nonempty_G3          54     nonempty   empty (X)  nonempty
    empty_G2              0     empty      empty      empty
    empty_G3              0     empty      empty      empty
    batch_rows removed    -      refuse     empty (X)  KeyError

This defect did not invalidate the unit_1942 empty run: that population was
verified empty independently by `R.populations`.

## The remaining external prerequisite — named, not hidden

`one_item_benchmark_inventory.json` is reached at a logical path supplied by
the recovery boundary bind map, not by this tree, so the checkpoint is not
standalone. Its real source IS staged
(`a7_recovery/unit_1939/testfixtures/group_approved_source/final_inventory.json`)
and the map row that serves it is in `unit_1939/map_1939a.tsv`. Reconstruction: `boundary.py --host <map> <payload>` with the map at
`a7_recovery/unit_1939/map_1939a.tsv`, SHA
f8132abafcdf6c029b2512e49c5c8594360d09ba7b7cbc7390915a734dbfe693. Every other checked entrypoint
resolves from HEAD+index alone.

## Resolution: proved by Git-only materialization, not by an index gate

**The previous claim in this document was wrong and is withdrawn.** It gated
`builtins.open` and `io.open`, which Python's importlib does NOT go through, so
every "import ok" row was reading the populated working directory. That check,
its two result files and its green rows are removed from this package.

`scripts/gitonly_check_1944.py` replaces it. The proposed staged tree is
exported with `git archive` into a fresh directory and every entrypoint is
imported and exercised THERE, with the working tree off `sys.path` and bytecode
writing disabled. The export carried 0 `__pycache__` or `.pyc` entries. Each
loaded module's `__file__` must sit inside the export AND its bytes must equal
the STAGED BLOB, so a same-named file elsewhere cannot satisfy it.

Sibling reads are covered separately from imports: `owner_hashes()` is called
live, every `os.path.join(_HERE, …)` file is checked for presence and blob
identity, and the **caller-selected scorer is loaded through the real
`bind_grading_scorer`** and its `meaning_fields()` accessor against the
independently accepted hash. Module membership is taken from `sys.modules`
AFTER the boundaries have run — owners can insert their own paths, so the
initial `sys.path` assignment is not the proof. `manifest()` takes a
bound argument, so its ten sibling reads are proved that way rather than by
inventing a caller.

| run | steps | what it shows |
|---|---|---|
| positive | 28/28, **46 modules**, 0 outside / 0 unstaged / 0 mismatched | the completed selection resolves from Git alone, and the scorer binds |
| missing scorer | 26/28 | removing `score_exp5_current.py` makes the real `bind_grading_scorer` raise FileNotFoundError |
| old selection (tree 1242aba7) | 8/28 | the previous package genuinely could not resolve: `build_launch_manifest`, `a7_prepared_run`, `a7_g23_run`, `kf_lint`, both signer owners and several siblings were absent |
| missing module | 14/26 | removing `a1_reader.py` breaks it and its dependents |
| missing sibling asset | 25/26 | removing `decision_rules_1387.txt` is caught and named |
| missing signer | 25/26 | removing `signer_proof.py` is caught |

## What the completed allowlist adds, and why

`scripts/allowlist_1944.py` derives it from the files themselves: the import
closure of the source/key/signer/producer/grader entrypoints, every sibling
file an owner opens beside itself, and the lock/candidate/signer owners — whose
own imports are roots too, which is how `build_kfields_final_targeted` was
found. The three changed focused tests are included; they are not the published
unchanged versions.

Required sibling paths are staged at the layout the owners derive from
`__file__`. Git deduplicates identical blobs, and no runtime fallback, wrapper,
import framework or path rewrite was added to avoid them.

## What this is not

No runtime behaviour, grading prompt, approval rule, schema meaning, source
selection or scorer threshold is changed. The retained TEST records are TEST
evidence: the rehearsal's decisions were INCONCLUSIVE (null) with 0 matched and
0 accepted facts, and the regression carried 193 failed tests PLUS 14 setup errors = 207 failing
identities, with 896 passed, 2 skipped and 0 collection errors on EACH side
(not 207 failures plus a further 14), all at their existing historical scope. **No statement is made that A7 or
any answer key passed.** A7 remains unmeasured on the new sample.
