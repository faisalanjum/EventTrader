"""The strict identity of all 38 saved attempts, by the ONE existing owner (Codex SEQ 1562 item 1).

`build_inventory_review._attempt_evidence` derives every fact of a paid call from its official
bytes: the official run location and parent session, the state's runId, exactly one agent and
its id, the pinned model, agent type and rendered launcher script, zero tool calls, the
transcript's input digest, every assistant record's model, session, agent and effort, the
ordered continuation chain, raw equality, and globally unique run / agent / transcript / raw /
response identities. The census calls it for all 38 rows with the frozen prompt text, the one
parent session the rows name, and shared seen sets - inside a private mount namespace that
masks the live session records and projects the package copies at their official paths, so the
owner's location rule is met without being weakened.

Every control here mutates ONE real field in a private copy, re-pins the copy's three tables
(WORKFLOW_STATES.tsv, SUBAGENT_RECORDS.tsv, ATTEMPT_EVIDENCE.tsv) to the mutated bytes, and
requires the refusal to name the strict-identity reason - never an outer stale hash. Two
controls do the opposite on purpose: a stale pin and a pin at another path must refuse BEFORE
any owner call. The controls are fixture-free so the exact-credit audit can run each one.
"""
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

R = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path[:0] = [os.path.join(R, "proofs")]
import accepted_evidence_census as AEC  # noqa: E402

CENSUS = os.path.join(R, "proofs", "accepted_evidence_census.py")
STRICT = os.path.join("reports", "strict_attempt_identity.json")
_PACKAGE = []


def _sha(path):
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


def _package():
    """A private copy of exactly the files the census reads, bound afresh - built once."""
    if not _PACKAGE:
        root = tempfile.mkdtemp(prefix="strictpkg_")
        for rel in AEC.needed_paths(R):
            dst = os.path.join(root, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(os.path.join(R, rel), dst)
        rep = AEC.census(root, bind=True)
        assert rep["defects"] == [], rep["defects"][:5]
        _PACKAGE.append(root)
    return _PACKAGE[0]


def _fresh(tmp_path):
    root = str(tmp_path / "pkg")
    shutil.copytree(_package(), root)
    return root


def _rows(root):
    return json.load(io.open(os.path.join(root, AEC.ATTEMPTS), encoding="utf-8"))


def _write_rows(root, rows):
    io.open(os.path.join(root, AEC.ATTEMPTS), "w", encoding="utf-8").write(json.dumps(rows, indent=1))


def _first(root):
    return [r for r in _rows(root) if r["attempt"] == 1][0]


def _edit_state(root, row, fn):
    p = os.path.join(root, AEC.row_paths(row)["state"])
    st = json.load(io.open(p, encoding="utf-8"))
    fn(st)
    io.open(p, "w", encoding="utf-8").write(json.dumps(st))


def _edit_transcript(root, row, fn):
    p = os.path.join(root, AEC.row_paths(row)["transcript"])
    recs = [json.loads(l) for l in io.open(p, encoding="utf-8") if l.strip()]
    fn(recs)
    io.open(p, "w", encoding="utf-8").write("".join(json.dumps(r) + "\n" for r in recs))


def _agent_row(st):
    return [x for x in st["workflowProgress"] if x.get("type") == "workflow_agent"][0]


def _repin(root, tables=True):
    """Re-pin the private copy's tables to its CURRENT bytes, so a control can only fail
    for the strict-identity reason, never for an outer stale hash."""
    if tables:
        for tsv, base in ((AEC.STATES_TSV, os.path.join("evidence", "workflow_states")),
                          (AEC.RECORDS_TSV, os.path.join("evidence", "subagent_records"))):
            fp = os.path.join(root, tsv)
            out = []
            for l in io.open(fp, encoding="utf-8").read().split("\n"):
                if l and not l.startswith("file\t"):
                    f, _b, _s, rest = l.split("\t", 3)
                    t = os.path.join(root, base, f)
                    if os.path.isfile(t):
                        l = "\t".join([f, str(os.path.getsize(t)), _sha(t), rest])
                out.append(l)
            io.open(fp, "w", encoding="utf-8").write("\n".join(out))
    AEC.census(root, bind=True)


def _census_script():
    """-> (the census to run, its shadow dir or None): the package's own - or, when the
    mutation harness has a source fault installed for it in THIS process, a shadow copy
    carrying exactly that edit, so the subprocess sees the same mutant an in-process
    control would."""
    MU = sys.modules.get("mutations")
    edits = MU.installed_edits("AEC") if MU is not None else []
    if not edits:
        return CENSUS, None
    src = io.open(CENSUS, encoding="utf-8").read()
    for anchor, repl in edits:
        assert src.count(anchor) == 1, "stale mutation anchor for the census"
        src = src.replace(anchor, repl, 1)
    shadow = tempfile.mkdtemp(prefix="shadow_")
    os.makedirs(os.path.join(shadow, "proofs"))
    io.open(os.path.join(shadow, "proofs", "accepted_evidence_census.py"), "w", encoding="utf-8").write(src)
    os.symlink(os.path.join(R, "bench"), os.path.join(shadow, "bench"))
    return os.path.join(shadow, "proofs", "accepted_evidence_census.py"), shadow


def _strict(root, namespace=True):
    """-> (rc, output, strict report or None) of the census's strict mode on `root`."""
    script, shadow = _census_script()
    cmd = [sys.executable, "-B", script, "--strict", "--root", root] + (["--in-namespace"] if namespace else [])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    finally:
        if shadow:
            shutil.rmtree(shadow, ignore_errors=True)
    rp = os.path.join(root, STRICT)
    rep = json.load(io.open(rp, encoding="utf-8")) if os.path.isfile(rp) else None
    return r.returncode, r.stdout + r.stderr, rep


def _failing(rep):
    return {(f["source_id"], f["attempt"]): " | ".join(f["problems"]) for f in rep["failures"]}


def test_the_strict_population_passes_for_all_38_rows(tmp_path):
    rc, out, rep = _strict(_package())
    assert rep is not None and rc == 0, out[-800:]
    assert rep["rows"] == 38 and rep["failures"] == []
    assert rep["owner"] == "build_inventory_review._attempt_evidence"
    assert rep["unique"]["run"] == 38 and rep["unique"]["agent"] == 38 and rep["unique"]["transcript"] == 38 and rep["unique"]["raw"] == 38
    assert rep["unique"]["response"] >= 38
    assert rep["parent_session"] and rep["retries"] == 2 and rep["unlawful_retries"] == []


def _only_the_mutated_row_fails(root, row, reason):
    rc, out, rep = _strict(root)
    assert rep is not None and rc != 0, out[-800:]
    bad = _failing(rep)
    assert list(bad) == [(row["source_id"], row["attempt"])], bad     # exactly the mutated row fails
    assert reason in bad[(row["source_id"], row["attempt"])], bad
    assert "hash" not in bad[(row["source_id"], row["attempt"])]        # never an outer stale hash


def _state_control(mutate, reason):
    def test(tmp_path):
        root = _fresh(tmp_path)
        row = _first(root)
        _edit_state(root, row, mutate)
        _repin(root)
        _only_the_mutated_row_fails(root, row, reason)
    return test


def _every_assistant(recs, fn):
    for r in recs:
        if r.get("type") == "assistant":
            fn(r)


def _transcript_control(mutate, reason):
    def test(tmp_path):
        root = _fresh(tmp_path)
        row = _first(root)
        _edit_transcript(root, row, mutate)
        _repin(root)
        _only_the_mutated_row_fails(root, row, reason)
    return test


# one named control per real field, so the exact-credit audit can call each by name
test_a_wrong_model_in_the_state_fails_for_its_own_reason = _state_control(
    lambda st: _agent_row(st).__setitem__("model", "claude-haiku-4-5-20251001"), "not the pinned")
test_a_wrong_agent_type_in_the_state_fails_for_its_own_reason = _state_control(
    lambda st: _agent_row(st).__setitem__("agentType", "general-purpose"), "ran as")
test_a_tool_call_in_the_state_fails_for_its_own_reason = _state_control(
    lambda st: _agent_row(st).__setitem__("toolCalls", 1), "used tools")
test_a_changed_launcher_script_fails_for_its_own_reason = _state_control(
    lambda st: st.__setitem__("script", st["script"] + "\n// not the launcher\n"), "not the exact rendered launcher")
test_a_wrong_agent_id_in_the_state_fails_for_its_own_reason = _state_control(
    lambda st: _agent_row(st).__setitem__("agentId", "a000000000000000f"), "official agent is")
test_a_wrong_run_id_in_the_state_fails_for_its_own_reason = _state_control(
    lambda st: st.__setitem__("runId", "wf_00000000-000"), "does not name its own run")
test_a_wrong_effort_in_the_transcript_fails_for_its_own_reason = _transcript_control(
    lambda recs: _every_assistant(recs, lambda r: r.__setitem__("effort", "low")), "ran at")
test_a_wrong_session_in_the_transcript_fails_for_its_own_reason = _transcript_control(
    lambda recs: _every_assistant(recs, lambda r: r.__setitem__("sessionId", "00000000-0000-4000-8000-000000000000")), "names session")
test_a_wrong_model_in_the_transcript_fails_for_its_own_reason = _transcript_control(
    lambda recs: _every_assistant(recs, lambda r: r["message"].__setitem__("model", "claude-haiku-4-5-20251001")), "records model")


def test_a_raw_answer_that_is_not_the_proved_answer_fails(tmp_path):
    root = _fresh(tmp_path)
    row = _first(root)
    io.open(os.path.join(root, AEC.row_paths(row)["raw"]), "ab").write(b"\n")
    _repin(root)
    rc, out, rep = _strict(root)
    assert rep is not None and rc != 0, out[-800:]
    assert "not the proved complete" in _failing(rep)[(row["source_id"], row["attempt"])]


def test_a_reused_identity_fails(tmp_path):
    root = _fresh(tmp_path)
    rows = _rows(root)
    a, b = [r for r in rows if r["attempt"] == 1][:2]
    b["raw_name"] = a["raw_name"]                                        # two attempts, one raw identity
    _write_rows(root, rows)
    _repin(root)
    rc, out, rep = _strict(root)
    assert rep is not None and rc != 0, out[-800:]
    assert any("used by another attempt" in v for v in _failing(rep).values()), _failing(rep)


def test_rows_of_two_sessions_have_no_parent_session(tmp_path):
    root = _fresh(tmp_path)
    rows = _rows(root)
    parts = rows[0]["state_path"].split("/")
    parts[-3] = "00000000-0000-4000-8000-000000000000"
    rows[0]["state_path"] = "/".join(parts)
    _write_rows(root, rows)
    _repin(root)
    rc, out, rep = _strict(root)
    assert rc != 0 and "parent session" in out, out[-800:]
    assert rep is None or rep["failures"] == []                          # refused before any owner call


def test_a_foreign_session_directory_is_never_created(tmp_path):
    root = _fresh(tmp_path)
    rows = _rows(root)
    for r in rows:
        parts = r["state_path"].split("/")
        parts[-3] = "00000000-0000-4000-8000-000000000000"
        r["state_path"] = "/".join(parts)
    _write_rows(root, rows)
    _repin(root)
    session_dir = "/".join(rows[0]["state_path"].split("/")[:-2])
    rc, out, rep = _strict(root)
    assert rc != 0 and "official" in out, out[-800:]
    assert not os.path.exists(session_dir)                               # nothing was created on the real filesystem


def test_a_stale_pin_refuses_before_any_owner_call(tmp_path):
    """The opposite of the field controls: the mutated state is NOT re-pinned, so the
    projection must refuse on the mount authority and no strict reason may appear."""
    root = _fresh(tmp_path)
    row = _first(root)
    _edit_state(root, row, lambda st: _agent_row(st).__setitem__("model", "claude-haiku-4-5-20251001"))
    _repin(root, tables=False)                                           # ATTEMPT_EVIDENCE re-bound, the mount tables stale
    rc, out, rep = _strict(root)
    assert rc != 0 and "does not hash to its mount authority" in out, out[-800:]
    assert rep is None or rep["failures"] == []


def test_a_pin_at_another_path_refuses(tmp_path):
    root = _fresh(tmp_path)
    row = _first(root)
    name = os.path.basename(AEC.row_paths(row)["state"])
    fp = os.path.join(root, AEC.STATES_TSV)
    out = []
    for l in io.open(fp, encoding="utf-8").read().split("\n"):
        if l.startswith(name + "\t"):
            f, b, s, hist = l.split("\t", 3)
            l = "\t".join([f, b, s, hist.replace(name, "wf_00000000-000.json")])
        out.append(l)
    io.open(fp, "w", encoding="utf-8").write("\n".join(out))
    rc, text, rep = _strict(root)
    assert rc != 0 and "not at the row's official path" in text, text[-800:]
    assert rep is None or rep["failures"] == []


def test_the_strict_proof_refuses_outside_the_projection(tmp_path):
    rc, out, rep = _strict(_package(), namespace=False)
    assert rc != 0 and "not inside the projection" in out, out[-800:]


def test_schema_valid_json_is_named_truthfully(tmp_path):
    a = AEC.census(_package())["accounting"]
    assert "final_source_results" not in a
    assert a["sources_with_schema_valid_latest_attempt"] == 36
    assert a["meaning_finalized_answers_at_a3"] == 0
