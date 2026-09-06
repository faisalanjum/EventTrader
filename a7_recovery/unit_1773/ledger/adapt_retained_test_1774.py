# -*- coding: utf-8 -*-
"""Adapt the retained postrun test to THIS recovery boundary, minimally.

Codex SEQ 1774 item 1: adapt only the smallest fixture/selection needed. Four
kinds of test are removed, each for a stated reason, and nothing else is
touched - every remaining line is byte-identical to the retained original,
which is preserved beside it.

  * three tests build a fresh run through A5.prepare; 1774 says reuse the
    closed prelaunch proof instead of reopening A5.prepare
  * one test derives the G2/G3 grading inventories, which is later-step work
    this gate explicitly defers - and it is the ONLY consumer of the two
    imports whose durable version is ambiguous, so removing it lets the module
    import without anyone guessing a version
  * three mutation tests copy the run to a DIFFERENT path before mutating it.
    That copy already refuses on its path-bound receipt, so their generic
    raises(ValueError) does not prove the mutation was detected; they are
    replaced by controlled equivalents in test_a7_recovery_boundary_1774.py
"""
import ast
import io
import os

V = os.path.dirname(os.path.abspath(__file__)) + "/../view/harness_g1v3"
SRC = os.path.normpath(V + "/test_a7_postrun_identity_1521.py")
DST = os.path.normpath(V + "/test_a7_postrun_identity_1521_recovery_1774.py")

DROP = {
    "test_a_fresh_zero_call_run_loads_against_its_own_freeze": "reopens A5.prepare",
    "test_a_substituted_run_refuses_against_the_accepted_hash": "reopens A5.prepare",
    "test_a_middle_state_run_refuses": "reopens A5.prepare",
    "test_grading_inventories_derive_twice_identically_with_zero_problems":
        "G2/G3 later-step work; sole consumer of the ambiguous imports",
    "test_a_changed_receipt_refuses": "uncontrolled: renamed copy refuses on path binding",
    "test_a_changed_finalization_refuses": "uncontrolled: renamed copy refuses on path binding",
    "test_a_changed_raw_tree_refuses": "uncontrolled: renamed copy refuses on path binding",
}
DROP_IMPORT = {"a7_conservation": "only the removed G2/G3 test used it",
               "a7_g23_run": "only the removed G2/G3 test used it; 3 durable versions"}

src = io.open(SRC, encoding="utf-8").read()
lines = src.splitlines(True)
tree = ast.parse(src)
cut = []
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in DROP:
        start = min([node.lineno] + [d.lineno for d in node.decorator_list])
        cut.append((start, node.end_lineno, "def " + node.name, DROP[node.name]))
    if isinstance(node, ast.Import):
        for a in node.names:
            if a.name in DROP_IMPORT:
                cut.append((node.lineno, node.end_lineno, "import " + a.name,
                            DROP_IMPORT[a.name]))

drop_lines = set()
for a, b, _w, _r in cut:
    drop_lines.update(range(a, b + 1))
out = [l for i, l in enumerate(lines, 1) if i not in drop_lines]
io.open(DST, "w", encoding="utf-8").write("".join(out))

kept = [n.name for n in ast.parse("".join(out)).body
        if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
print("removed %d items:" % len(cut))
for a, b, w, r in sorted(cut):
    print("   lines %-5s %-58s %s" % ("%d-%d" % (a, b), w, r))
print("kept %d tests in the adapted module:" % len(kept))
for k in kept:
    print("   ", k)
