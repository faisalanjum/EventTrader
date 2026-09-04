"""The fixed decision inputs must hash to their authorities (Codex SEQ 1559 item 2/5).

The real package is the positive control. The refusals are exercised on a SMALL root
built here with the same three authorities, because copying a 210 MB prefix per
control proves nothing extra: the rule under test is the comparison, and the real
positive proves the live shape.
"""
import hashlib
import io
import os
import sys

_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _R)
import verify_fixed_inputs as V                                # noqa: E402


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _root(tmp_path):
    """A lawful small root: prefix + ACCEPTED.tsv, one git object + GIT_BASES.tsv,
    one resume input + RESUME_INPUTS.tsv + the projection inventory that carries it."""
    t = tmp_path / "evidence" / "transcript"; t.mkdir(parents=True)
    prefix = b'{"a":1}\n{"b":2}\n'
    (t / "p.jsonl").write_bytes(prefix)
    (t / "ACCEPTED.tsv").write_text("p.jsonl\t%d\t2\t%s\tnote\n" % (len(prefix), _sha(prefix)))
    g = tmp_path / "evidence" / "git_bases"; (g / "c").mkdir(parents=True)
    obj = b"print(1)\n"; (g / "c" / "x.py").write_bytes(obj)
    tree = b"x.py\n"; (g / "c.tree").write_bytes(tree)
    (g / "GIT_BASES.tsv").write_text("commit\trel\tbytes\tsha256\nc\t<tree>\t%d\t%s\nc\tx.py\t%d\t%s\n"
                                     % (len(tree), _sha(tree), len(obj), _sha(obj)))
    w = tmp_path / "evidence" / "workflow_states"; w.mkdir(parents=True)
    st = b'{"status":"completed"}'
    (w / "wf_x.json").write_bytes(st)
    (w / "WORKFLOW_STATES.tsv").write_text("file\tbytes\tsha256\thistorical_path\nwf_x.json\t%d\t%s\t~/x\n" % (len(st), _sha(st)))
    sa = tmp_path / "evidence" / "subagent_records"; sa.mkdir(parents=True)
    (sa / "SUBAGENT_RECORDS.tsv").write_text("file\tbytes\tsha256\thistorical_path\n")
    (tmp_path / "in.json").write_bytes(b"{}")
    (tmp_path / "evidence" / "RESUME_INPUTS.tsv").write_text(
        "path\tbytes\tsha256\tsource\nin.json\t2\t%s\tnote\n" % _sha(b"{}"))
    # the ONE inventory of what the resume path reads: every resume input is a row of it
    (tmp_path / "evidence" / "PROJECTION.tsv").write_text(
        "phase\thistorical_path\tpackage_path\tbytes\tsha256\ninput\t/h/in.json\tin.json\t2\t%s\n" % _sha(b"{}"))
    return str(tmp_path)


def test_the_real_package_verifies():
    assert V.failures() == []


def test_the_small_root_is_lawful(tmp_path):
    assert V.failures(_root(tmp_path)) == []


def test_it_REFUSES_a_prefix_whose_byte_changed(tmp_path):
    r = _root(tmp_path)
    (tmp_path / "evidence" / "transcript" / "p.jsonl").write_bytes(b'{"a":1}\n{"b":3}\n')
    assert any("transcript prefix" in x for x in V.failures(r))


def test_it_REFUSES_a_prefix_with_an_extra_row(tmp_path):
    r = _root(tmp_path)
    (tmp_path / "evidence" / "transcript" / "p.jsonl").write_bytes(b'{"a":1}\n{"b":2}\n{"c":3}\n')
    assert any("transcript prefix" in x for x in V.failures(r))


def test_it_REFUSES_a_missing_git_object(tmp_path):
    r = _root(tmp_path)
    (tmp_path / "evidence" / "git_bases" / "c" / "x.py").unlink()
    assert any("git store lacks" in x for x in V.failures(r))


def test_it_REFUSES_an_altered_git_object(tmp_path):
    r = _root(tmp_path)
    (tmp_path / "evidence" / "git_bases" / "c" / "x.py").write_bytes(b"print(2)\n")
    assert any("does not hash to its identity" in x for x in V.failures(r))


def test_it_REFUSES_an_altered_resume_input(tmp_path):
    r = _root(tmp_path)
    (tmp_path / "in.json").write_bytes(b"{ }")
    assert any("resume input does not hash" in x for x in V.failures(r))


def test_it_REFUSES_a_missing_resume_input(tmp_path):
    r = _root(tmp_path)
    (tmp_path / "in.json").unlink()
    assert any("resume input missing" in x for x in V.failures(r))


def test_it_REFUSES_an_empty_authority(tmp_path):
    r = _root(tmp_path)
    (tmp_path / "evidence" / "RESUME_INPUTS.tsv").write_text("path\tbytes\tsha256\tsource\n")
    assert any("names no files" in x for x in V.failures(r))


def test_the_cache_key_binds_the_transcript_and_store_identity(tmp_path):
    """A cache built against other inputs must never be served: the key changes when
    the transcript authority changes, with the code unchanged."""
    import shutil
    sys.path.insert(0, os.path.join(_R, "ledger"))
    import replay_transcript as RT
    import chrono_replay as CR
    for rel in ("evidence/transcript/ACCEPTED.tsv", "evidence/git_bases/GIT_BASES.tsv"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(os.path.join(_R, rel), str(tmp_path / rel))
    saved = (RT.PACKAGE, RT.GIT_BASES)
    try:
        RT.PACKAGE, RT.GIT_BASES = str(tmp_path), str(tmp_path / "evidence" / "git_bases")
        if hasattr(CR._code_digest, "value"):
            del CR._code_digest.value
        k1 = CR._code_digest()
        with open(str(tmp_path / "evidence" / "transcript" / "ACCEPTED.tsv"), "a") as fh:
            fh.write("changed\n")
        del CR._code_digest.value
        k2 = CR._code_digest()
    finally:
        RT.PACKAGE, RT.GIT_BASES = saved
        if hasattr(CR._code_digest, "value"):
            del CR._code_digest.value
    assert k1 != k2


def test_it_REFUSES_an_altered_workflow_state_copy(tmp_path):
    r = _root(tmp_path)
    (tmp_path / "evidence" / "workflow_states" / "wf_x.json").write_bytes(b'{"status":"failed"}')
    assert any("workflow_states copy does not hash" in x for x in V.failures(r))


def test_it_REFUSES_an_unpinned_file_inside_a_mount_directory(tmp_path):
    r = _root(tmp_path)
    (tmp_path / "evidence" / "workflow_states" / "wf_stray.json").write_bytes(b"{}")
    assert any("unpinned file" in x for x in V.failures(r))
