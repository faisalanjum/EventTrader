"""Append mode must APPEND (Codex SEQ 1555 item 1).

Two halves of one boundary were wrong. An OWNER opened with `a` was served a reader, so
its writes were discarded outright. A scratch SIBLING opened with `a` was served an
empty sink, so it overwrote instead of appending. Write/truncate behaviour is unchanged;
only append is corrected.
"""
import contextlib
import io
import os
import sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(R, "ledger"))
sys.path.insert(0, R)
import replay_transcript as RT                                # noqa: E402

OWNER = "bench_1306/.claude/plans/Drivers/experiments/harness/thing.py"
H = "/tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness"
SIDE_FILE = "/tmp/claude-1000/sidecar.py"


def run(program, base="BASE\n", side=None):
    rec = {"message": {"content": [{"type": "tool_use", "name": "Bash", "input": {
        "command": "cd %s\npython3 - <<'PY'\n%sPY\n" % (H, program)}}]}}
    with contextlib.redirect_stdout(io.StringIO()):
        return RT.apply_saved_edits(base, {1: rec}, OWNER, side=side if side is not None
                                    else {})


def test_an_APPEND_to_the_owner_keeps_what_was_there():
    out, _ = run("import io\nio.open(%r, 'a').write('ADDED\\n')\n" % (H + "/thing.py"))
    assert out == "BASE\nADDED\n", out


def test_an_APPEND_to_the_owner_puts_the_cursor_at_the_END():
    """`tell()` on a freshly opened append handle is the end of the file, not zero."""
    out, _ = run("import io\n"
                 "f = io.open(%r, 'a')\n"
                 "io.open(%r, 'w').write(str(f.tell()))\n"
                 % (H + "/thing.py", H + "/other.py"), base="12345\n")
    # the owner is untouched by the second write; the position is what we assert
    side = {}
    out2, _ = run("import io\n"
                  "f = io.open(%r, 'a')\n"
                  "io.open(%r, 'w').write(str(f.tell()))\n"
                  % (H + "/thing.py", SIDE_FILE), base="12345\n", side=side)
    assert side[SIDE_FILE] == "6", side


def test_an_APPEND_to_a_SIDE_FILE_keeps_what_was_there():
    side = {SIDE_FILE: "FIRST\n"}
    run("import io\nio.open(%r, 'a').write('SECOND\\n')\n" % SIDE_FILE, side=side)
    assert side[SIDE_FILE] == "FIRST\nSECOND\n", side[SIDE_FILE]


def test_WRITE_to_the_OWNER_still_truncates():
    """Only append changed: `w` must still replace the owner's text.

    Split from the sibling half deliberately. Combined, this assertion fired first and
    the sibling branch could never be measured on its own - one fault killed the test
    before the other branch was reached, which is a credit the sibling never earned.
    """
    out, _ = run("import io\nio.open(%r, 'w').write('REPLACED\\n')\n" % (H + "/thing.py"))
    assert out == "REPLACED\n", out


def test_WRITE_to_a_SIDE_FILE_still_truncates():
    """The other half of the same two-branch boundary, asserted independently."""
    side = {SIDE_FILE: "FIRST\n"}
    run("import io\nio.open(%r, 'w').write('ONLY\\n')\n" % SIDE_FILE, side=side)
    assert side[SIDE_FILE] == "ONLY\n", side[SIDE_FILE]


def test_the_manifest_compares_CONTENT_not_just_the_file_list(tmp_path):
    """`--verify` must re-measure BYTES. Recording only the path, on both sides, lets
    an edited file pass as the package it was frozen from.

    In-process on a throwaway package. The suite's other manifest test runs the real
    verifier as a SUBPROCESS, which proves the live package verifies but cannot show
    which comparison did it - an in-process fault never reaches a child process.
    """
    import freeze_package as FP
    stage = str(tmp_path)
    io.open(os.path.join(stage, "a.py"), "w", encoding="utf-8").write("frozen\n")
    saved_R = FP.R
    FP.R = stage
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            FP.write()
            io.open(os.path.join(stage, "a.py"), "w", encoding="utf-8").write("EDITED\n")
            rc = FP.verify()
        assert rc != 0, "an edited file verified against the manifest it was frozen from"
    finally:
        FP.R = saved_R
