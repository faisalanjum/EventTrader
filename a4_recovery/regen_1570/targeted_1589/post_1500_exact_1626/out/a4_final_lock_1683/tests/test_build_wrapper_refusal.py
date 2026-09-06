# -*- coding: utf-8 -*-
"""The build wrapper's own refusal seam (Codex SEQ 1741 item 1).

The defect was not in the builder: the WRAPPER printed the verifier's problem list and then
declared success. This test runs the wrapper's actual tail - the statements from the line
where the verified candidate directory is bound, taken out of the real source file, never a
copy of it - with the verifier stubbed, so the refusal branch is exercised without another
expensive build.

It tests the whole nonempty class, not one sample: one problem, several, a non-string
problem, an empty string inside a list (the LIST is what is nonempty), and a nonempty
tuple. The lawful empty list is the positive control and must still print success.
"""
import ast
import contextlib
import io
import os
import sys
import tempfile
import types

UNIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = UNIT + "/reconstruct/build_final_candidate.py"
#: the seam: everything from where the built candidate directory is bound onwards
FROM_LINE = 32

src = io.open(SRC, encoding="utf-8").read()
tree = ast.parse(src)
tail = [n for n in tree.body if getattr(n, "lineno", 0) >= FROM_LINE]
assert tail, "the wrapper has no tail at line %d" % FROM_LINE


def run_tail(problems):
    """Run the real tail with the verifier stubbed. -> (exit status or None, printed)"""
    work = tempfile.mkdtemp(prefix="wrapper_seam_")
    io.open(os.path.join(work, "one.json"), "w").write("{}\n")
    ns = {"os": os, "sys": sys, "sha": lambda p: "0" * 64,
          "C": types.SimpleNamespace(DEFAULT_OUT=work, verify=lambda out: problems)}
    mod = ast.Module(body=tail, type_ignores=[])
    ast.fix_missing_locations(mod)
    buf = io.StringIO()
    status = None
    try:
        with contextlib.redirect_stdout(buf):
            exec(compile(mod, SRC, "exec"), ns)
    except SystemExit as exc:
        status = exc.code
    return status, buf.getvalue()


CASES = [("the lawful empty list", [], True),
         ("one problem", ["a file is not the derivation"], False),
         ("several problems", ["one", "two", "three"], False),
         ("a non-string problem", [{"path": "key_identity.json", "why": "sha"}], False),
         ("an empty string inside a list", [""], False),
         ("a nonempty tuple", ("only one",), False)]

passed = failed = 0
for name, problems, lawful in CASES:
    status, out = run_tail(problems)
    ok_printed = "BUILD_CANDIDATE_OK" in out
    if lawful:
        good = status is None and ok_printed
        why = "status %r, success printed %r" % (status, ok_printed)
    else:
        good = status not in (None, 0) and not ok_printed
        why = "status %r, success printed %r" % (status, ok_printed)
    print("%-4s %-32s %s" % ("ok" if good else "BAD", name, why))
    passed += bool(good)
    failed += (not good)

print("%d passed / %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
