"""Every resume input has ONE authority (Codex SEQ 1562 item 2).

evidence/PROJECTION.tsv, built from the freeze's own walk, is the sole inventory of what
the real path may read at a historical path: the vendored experiments tree (including the
four invrev_run4 inputs the path reads through it), the official states and the agent
transcripts - now also the 38 states and 38 transcripts the strict identity proof reads.
evidence/RESUME_INPUTS.tsv only records the PROVENANCE of restored or reproduced bytes,
and every row of it must agree with the projection's identity of the same file.
"""
import io
import json
import os
import sys

R = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path[:0] = [R, os.path.join(R, "proofs")]
import verify_fixed_inputs as VFI  # noqa: E402
import accepted_evidence_census as AEC  # noqa: E402
import project_historical_tree as PHT  # noqa: E402

FOUR = ("attempts.json", "pending_ledger.json", "reconciliation_final.json", "reconciliation_final.txt")


def _projection(root=R):
    out = {}
    for ln in io.open(os.path.join(root, "evidence", "PROJECTION.tsv"), encoding="utf-8").read().split("\n")[1:]:
        if ln.strip():
            ph, h, p, b, s = ln.split("\t")
            out[p] = (ph, h, int(b), s)
    return out


def _resume(root=R):
    out = {}
    for ln in io.open(os.path.join(root, "evidence", "RESUME_INPUTS.tsv"), encoding="utf-8").read().split("\n")[1:]:
        if ln.strip():
            p, b, s, _src = ln.split("\t")
            out[p] = (int(b), s)
    return out


def test_every_resume_input_is_a_projection_row_with_the_same_identity():
    proj, res = _projection(), _resume()
    assert res, "no resume inputs"
    for p, (b, s) in res.items():
        assert p in proj, "resume input not in the projection: %s" % p
        assert proj[p][2:] == (b, s), "identities disagree for %s" % p
    assert VFI.projection_conflicts(R) == []


def test_the_four_inputs_read_through_the_projection_are_its_rows():
    proj = _projection()
    for name in FOUR:
        rel = os.path.join(AEC.RUN, name)
        assert rel in proj and proj[rel][0] == "input", name
        fp = os.path.join(R, rel)
        assert os.path.getsize(fp) == proj[rel][2]


def test_the_projection_carries_the_strict_proofs_38_states_and_38_transcripts():
    by_hist = {h: (ph, p) for p, (ph, h, _b, _s) in _projection().items()}
    rows = json.load(io.open(os.path.join(R, AEC.ATTEMPTS), encoding="utf-8"))
    assert len(rows) == 38
    states, records = set(PHT.state_paths()), set(PHT.record_paths())     # the owner, in-process
    for r in rows:
        assert r["state_path"] in states and by_hist.get(r["state_path"], (None,))[0] == "state", r["state_path"]
        run = os.path.basename(r["state_path"])[:-len(".json")]
        t = os.path.join(os.path.dirname(os.path.dirname(r["state_path"])), "subagents", "workflows", run, "agent-%s.jsonl" % r["agent_id"])
        assert t in records and by_hist.get(t, (None,))[0] == "record", t


def test_a_resume_input_that_disagrees_with_the_projection_is_refused(tmp_path):
    root = str(tmp_path)
    os.makedirs(os.path.join(root, "evidence"))
    io.open(os.path.join(root, "evidence", "PROJECTION.tsv"), "w").write(
        "phase\thistorical_path\tpackage_path\tbytes\tsha256\ninput\t/h/x\tbench/x\t3\t" + "a" * 64 + "\n")
    io.open(os.path.join(root, "evidence", "RESUME_INPUTS.tsv"), "w").write(
        "path\tbytes\tsha256\tsource\nbench/x\t3\t" + "b" * 64 + "\tsrc\nbench/y\t1\t" + "c" * 64 + "\tsrc\n")
    bad = VFI.projection_conflicts(root)
    assert len(bad) == 2 and any("bench/x" in b for b in bad) and any("bench/y" in b for b in bad), bad
    assert any("projection" in b for b in VFI.failures(root))            # and the verifier carries them
    io.open(os.path.join(root, "evidence", "RESUME_INPUTS.tsv"), "w").write(
        "path\tbytes\tsha256\tsource\nbench/x\t3\t" + "a" * 64 + "\tsrc\n")
    assert VFI.projection_conflicts(root) == []
