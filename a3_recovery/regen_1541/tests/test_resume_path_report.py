"""RED-test of the ACTUAL entry point's run (Codex SEQ 1559 item 1): the resume report
the ordered chain writes must say completed, inside the package, with every read
accounted for. Reads the chain's output, so it runs in the full suite after the freeze."""
import hashlib
import io
import json
import os

import pytest

_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pytestmark = pytest.mark.reads_chain_outputs


def _report():
    return json.load(io.open(os.path.join(_R, "reports", "resume_path.json"), encoding="utf-8"))


def test_the_real_resume_completed_from_the_durable_package():
    d = _report()
    assert d["result"] == "completed", d["result"]
    assert d["clean"] is True


def test_the_resume_read_nothing_temporary_or_dirty_or_unmanifested():
    d = _report()
    assert d["temporary_reads"] == []
    assert d["resolved_into_dirty_main"] == []
    assert d["unmanifested_reads"] == []


def test_every_child_process_was_audited():
    d = _report()
    assert all(isinstance(c, list) and "-c" in c for c in d["subprocess_calls"]), d["subprocess_calls"]
    assert d["child_files_opened"] >= 0


def test_the_exact_callable_is_pinned():
    d = _report()
    entry = os.path.join(_R, "bench", ".claude", "plans", "Drivers", "experiments", "harness",
                         "build_kfields_key.py")
    assert d["entry_point"] == "build_kfields_key.py::__main__"
    assert d["entry_sha256"] == hashlib.sha256(io.open(entry, "rb").read()).hexdigest()


def test_the_evidence_root_and_home_follow_the_explicit_projection_or_the_package():
    """With the explicit projection pair (Codex SEQ 1561 item 1) the evidence root is
    the receipt's historical root and HOME stays real - the namespace masks the live
    session records and the mailbox directory; without the pair, the package root and
    the package's own home. Either way no read is excused as a search."""
    d = _report()
    assert d["declared_search_reads"] == 0
    if d.get("projection_rows"):
        import sys
        sys.path.insert(0, _R)
        import project_historical_tree as PHT
        ev, _run = PHT.historical_roots()
        assert d["evidence_root"] == ev
        assert ev in d["search_roots"], d["search_roots"]
        assert d["home_override"] != os.path.join(_R, "home")
    else:
        assert all(r.startswith(_R) for r in d["search_roots"]), d["search_roots"]
        assert d["home_override"] == os.path.join(_R, "home")
