"""The audit must cross the subprocess boundary (Codex SEQ 1544 item 6).

`_a3_probe` measures A3 in a CLEAN interpreter on purpose, so the parent's
`sys.addaudithook` sees nothing it reads. A run that looks clean only because its child
was invisible proves nothing about the package.
"""
import io
import os
import subprocess
import sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, R)
import run_resume_path as RRP                                 # noqa: E402


def test_a_CHILD_interpreters_reads_are_audited_too(tmp_path):
    """Without instrumentation the child's opens are invisible to the parent."""
    target = tmp_path / "dependency.json"
    target.write_text('{"a": 1}\n', encoding="utf-8")
    audit = str(tmp_path / "child_audit.txt")
    src = "import io\nio.open(%r, encoding='utf-8').read()\n" % str(target)

    RRP.child_opened.clear()
    unpatch = RRP.instrument_children(audit)
    try:
        out = subprocess.run([sys.executable, "-B", "-c", src, "x"],
                             capture_output=True, text=True)
    finally:
        unpatch()
    assert out.returncode == 0, out.stderr[-300:]
    assert str(target) in RRP.child_opened


def test_a_MISSING_child_dependency_is_REFUSED_not_silently_skipped(tmp_path):
    """A child that cannot read its dependency must fail the run, not pass quietly."""
    audit = str(tmp_path / "child_audit.txt")
    missing = str(tmp_path / "absent.json")
    src = "import io\nio.open(%r, encoding='utf-8').read()\n" % missing

    RRP.child_opened.clear()
    unpatch = RRP.instrument_children(audit)
    try:
        out = subprocess.run([sys.executable, "-B", "-c", src, "x"],
                             capture_output=True, text=True)
    finally:
        unpatch()
    assert out.returncode != 0
    assert "FileNotFoundError" in out.stderr


def test_a_CHANGED_child_dependency_is_visible_to_the_audit(tmp_path):
    """The audit records the path, so a dependency that is not manifested - or whose
    bytes changed - is caught by the same rule the parent's reads are judged by."""
    dep = tmp_path / "dep.json"
    dep.write_text("{}\n", encoding="utf-8")
    audit = str(tmp_path / "child_audit.txt")
    src = "import io\nio.open(%r, encoding='utf-8').read()\n" % str(dep)
    RRP.child_opened.clear()
    unpatch = RRP.instrument_children(audit)
    try:
        subprocess.run([sys.executable, "-B", "-c", src, "x"], capture_output=True)
    finally:
        unpatch()
    manifested = set()          # nothing is manifested in this control
    assert set(RRP.child_opened) - manifested == {str(dep)}
