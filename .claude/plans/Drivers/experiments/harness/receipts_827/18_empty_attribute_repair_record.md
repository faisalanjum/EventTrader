# 18 — Empty `sign=""` / `format=""` fixture repair (#827 round 9)

**A WRITTEN, REVIEWED RECORD — not a replay command.** This was a one-time
repair. The machinery that derived it (a diff engine, an AST walker, a temp
module loader and a subprocess harness) was deleted rather than left behind to
maintain; what mattered is the evidence, and it is below.

## Why the repair

The Inline XBRL 1.1 schema declares `sign` as a restriction of `xs:string` whose
pattern is exactly `-`, and `format` as `xs:QName`. Both are OPTIONAL. So a
lawful document has the attribute **absent** or **valid** — `x=""` is neither,
and a fixture emitting it was asserting a sign or a transform the filing never
wrote.

## What was removed — every occurrence, with its exact owner

Baseline: frozen staged tree `28a42377e51b844961c268e5ad6c13b1c5c33f02`.
Line numbers are that tree's. The owner is the enclosing definition, read
structurally — a DIRECT site sits inside one test; a HELPER site is a builder;
a MODULE-LEVEL site is a fixture string every test in the file can reach.

| file | line | attr | owner (AST-derived, exact) |
|---|---|---|---|
| `test_round10_event_boundary.py` | 322, 324 | format | MODULE-LEVEL `_DOOR_DOC` |
| `test_round10_event_boundary.py` | 765 | format | MODULE-LEVEL `_DIM_DOC` |
| `test_round11_outcomes.py` | 376 | format | MODULE-LEVEL `_FULL_DOC` |
| `test_round12_exact_scale.py` | 133 | format | HELPER `_doc` |
| `test_round12_pure_unit_law.py` | 501 | format | **DIRECT** `test_the_binder_reports_the_structured_measures` (local `doc`) |
| `test_round12_pure_unit_law.py` | 549 | format | HELPER `_divide_doc` |
| `test_round14_evidence_matrix.py` | 389, 391, 394, 396 | format | MODULE-LEVEL `_TABLE_DOC` |
| `test_round14_evidence_matrix.py` | 628 | format | MODULE-LEVEL `_NO_BLOCK_DOC` |
| `test_round15_audit_evidence.py` | 587, 589 | format | HELPER `_dim_doc` |
| `test_round15_audit_evidence.py` | 866 | format | **DIRECT** `test_825p2_an_UNSTORABLE_value_keeps_NOT_STORABLE_and_PARKS` (local `doc`) |
| `test_round8_xbrl_binding.py` | 110 | format | HELPER `_doc` |
| `test_round8_xbrl_binding.py` | 904 | format | HELPER `_period_doc` |
| `test_round8_xbrl_binding.py` | 971 | format | **DIRECT** `test_FOREVER_parks_under_its_own_named_reason_not_malformed` (local `doc`) |
| `test_bind_graph_fact.py` | 1018 | sign | HELPER `_ns_doc` |
| `test_row_label_span.py` | 34 | format | MODULE-LEVEL `_FACT` |
| **20 removed** | | | |

> ⚠ **These names were WRONG in the first version of this record.** I wrote
> plausible-looking names — `_DOC`, `_HEAD`, "second document in the same file"
> — from memory instead of reading them, and the reviewer caught five errors
> (`_DOOR_DOC`, `_DIM_DOC`, `_FULL_DOC`, `_NO_BLOCK_DOC`, `_FACT`). Every name
> above is now derived by walking the frozen tree's AST and taking the
> innermost definition containing the line, so a guess cannot survive here.
> A "reviewable purpose" column was also dropped: it restated what I supposed
> each fixture was for, which is exactly the kind of claim this record must not
> make.

**NOT removed, and not markup:** `test_bind_graph_fact.py:29` —
`def _doc(..., sign="", ...)`, a Python keyword default meaning "no sign". It
never reaches a document. A sweep removed it in error and it was restored.

### The count reconciles exactly

```
21  literal `sign=""` / `format=""` in the frozen tree
-1  a Python keyword default in _doc()'s signature — NOT markup, still there
─────
20  emitted markup occurrences, all removed
+3  more removed from the WORKING tree: added by THIS round's own uncommitted
    edits to test_bind_graph_fact.py, so absent from the certified baseline
+1  the signature default, removed by the sweep in error and RESTORED
─────
24  total edits made during the repair
```

### The one template change, classified explicitly

`test_bind_graph_fact.py::_doc` interpolated `sign="{sign}"` with a default of
`""`. It now emits the attribute only when non-empty:

```python
signed = f' sign="{sign}"' if sign else ''
```

The Python keyword default `sign=""` in that signature is retained — it is the
builder's "no sign" argument, not markup, and never reaches a document.

## Why no test lost its purpose

**Value-preserving, measured under the FROZEN parser** — not asserted:

| evidence field | with `x=""` | with `x` absent | identical |
|---|---|---|---|
| `ev['sign']` | `''` | `''` | yes |
| `ev['fmt']` | `''` | `''` | yes |

**Stated exactly as measured, and no wider:** on ONE synthetic document, the
frozen parser produced the same `ev['sign']` and `ev['fmt']` values whether the
attribute was empty or absent. That is a measurement about those two fields in
that before-state. It is NOT a proof that no assertion anywhere could see a
difference — the earlier wording claimed that, and it exceeded the measurement.
What supports the removals is this measurement TOGETHER with the re-run below,
in which every node that could reach an edited fixture actually passes.

**Every affected node re-run and green.** DIRECT sites re-ran their own test;
SHARED and TEMPLATE sites re-ran their WHOLE module, because a module-level
fixture or a builder is reached by all of them — no guess was made about which
tests "really" used the attribute.

```
env -i PATH=… HOME=<empty temp dir> TMPDIR=<same> \
    PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=<repo> \
    python -m pytest -q -p no:randomly \
      -m "not live and not live_write and not llm" <affected nodes>

-> 967 passed, 7 deselected      rc=0
```

`HOME` was an empty temporary directory outside the repository and was removed
afterwards, so no credential file was reachable; plugin autoload was off; the
live, live_write and llm markers were all excluded.

**What this record does NOT claim:** that any of this establishes authorial
intent. Static analysis cannot. Sites are classified structurally, and the
shared/template ones are covered by re-running everything that could reach them.

## The rule keeps its own permanent controls

Deleting the invalid fixtures does not weaken the rule — it is pinned
independently, through the public door, in
`driver/relocation/test_two_view_bridge.py::_ATTRIBUTE_LAW`:

| case | required outcome |
|---|---|
| `sign` absent | `ok` (the positive case) |
| `sign="-"` | `ok` |
| `sign=""` | **`malformed_sign`** |
| `sign="+"` | `malformed_sign` |
| `format` absent | `ok` (no transform) |
| `format="ixt:num-dot-decimal"` | `ok` |
| `format=""` | **`malformed_format`** |
| `format="nope:x"` | `malformed_format` |

and by the mutation `optional_empty_accepted`, which re-introduces the
"accept present-and-empty" defect and must fail those tests at rc=1.
