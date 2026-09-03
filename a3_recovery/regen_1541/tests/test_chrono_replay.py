"""The cutoff-aware chronological replay from committed bases (Codex SEQ 1541).

My SEQ 1539 error is pinned here as a red-to-green lesson: searching for an owner's FINAL
hash and finding nothing does NOT prove that no base survives. The base is the committed
file, and these tests prove it exists, is byte-exact, and drives a replay.

The pins are OUTPUT assertions throughout: no target digest reaches the replay, which is
why `test_the_replay_never_takes_a_pin_as_an_input` guards both modules. The replay now
rebuilds this owner byte-exactly, and the tests check that against history's own
measurements as well as the pins.
"""
import hashlib
import json
import os
import pytest
import subprocess
import sys

_T = os.path.dirname(os.path.abspath(__file__))
_R = os.path.dirname(_T)
sys.path.insert(0, os.path.join(_R, "ledger"))
import replay_transcript as RT

BASE = "8cca087c384aa4dd300ebc48f23da6ccb77baff9abf48f9eb22b29af606a1db1"
PIN = "12d4aca9a7bfd9a51303271b54433ad55058dad268e771cff757a3ea0b68a14a"


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _report():
    return json.load(open(os.path.join(_R, "reports", "raw_transport_replay.json")))


def test_the_committed_base_exists_and_is_byte_exact():
    """Read-only: the commit still serves the file, and a durable copy matches it."""
    got = subprocess.check_output(
        ["git", "-C", "/home/faisal/EventMarketDB", "show",
         "cd961e51:.claude/plans/Drivers/experiments/harness/raw_transport.py"])
    assert hashlib.sha256(got).hexdigest() == BASE
    assert _sha(os.path.join(_R, "evidence", "raw_transport.base_8cca087c.py")) == BASE


def test_a_final_hash_scan_would_have_missed_that_base():
    """The lesson: the base's digest is NOT the pinned final digest."""
    assert BASE != PIN


def test_history_itself_measured_this_same_base():
    """The campaign recorded 'raw_transport.py before <base>' while it was running,
    so the base is confirmed by the era's own evidence, not only by my reading."""
    assert BASE in _report()["history_confirms_this_base"]


def test_the_replay_never_takes_a_pin_as_an_input():
    src = open(os.path.join(_R, "ledger", "chrono_replay.py")).read()
    src += open(os.path.join(_R, "ledger", "replay_transcript.py")).read()
    assert PIN not in src and BASE not in src


def test_every_checkpoint_history_printed_is_reproduced():
    """The decisive evidence: the replay prints the SAME numbers the campaign printed,
    including two byte counts of this very file."""
    rep = _report()
    # seven, not eight: the checkpoint at 26932 belonged to the p1319 tree's copy and
    # correctly left this owner's route once the owner was qualified by its worktree.
    assert rep["checkpoints_total"] == 7
    assert rep["checkpoints_met"] == rep["checkpoints_total"]
    lines = [c["line"] for c in rep["checkpoints_from_history"]]
    assert 26825 in lines and 26853 in lines      # the byte-count checkpoints
    for c in rep["checkpoints_from_history"]:
        assert c["met"], c


def test_the_one_refusal_reproduces_historys_own_failure():
    """26845 is not a defect in the replay: that saved program called its helper with
    two arguments where three were required, and it failed the same way when run."""
    rep = _report()
    assert list(rep["refused"]) == ["26845"]
    assert "missing 1 required positional argument" in rep["refused"]["26845"]
    assert "26846" in rep["refusal_is_faithful"]


def test_the_replay_reproduces_the_pins_exactly():
    """The gate: this file is rebuilt byte-exactly from the committed base plus the
    saved records. The digests are compared only AFTER the run."""
    rep = _report()
    assert rep["pin_32846"] == PIN
    assert rep["pin_32846_met"] is True
    assert rep["pin_32672_met"] is True
    assert rep["pin_pre_32672_met"] is True
    assert rep["reached_sha256"] == PIN


def test_the_owner_is_qualified_by_its_worktree():
    """A pristine copy of the same harness lived at scratchpad/p1319, and one record
    cd-ed into THAT tree and edited its copy by the bare name. Matching only on
    'harness/<name>' applied another tree's edit to this file."""
    rep = _report()
    assert rep["owner"].startswith("bench_1306/")
    assert "p1319" in rep["what_closed_the_gap"]
    import chrono_replay as CR
    cmd = ('P=/tmp/claude-1000/x/scratchpad/p1319/.claude/plans/Drivers/experiments/harness\n'
           'cd "$P" && python3 - <<\'PY\'\n'
           'import io\n'
           'io.open("raw_transport.py","w",encoding="utf-8").write("other tree")\n'
           'PY\n')
    other = "p1319/.claude/plans/Drivers/experiments/harness/raw_transport.py"
    assert CR.writes_this(cmd, other) is True          # it does write THAT copy
    assert CR.writes_this(cmd, rep["owner"]) is False  # and must not touch ours


def test_a_single_redirect_from_a_file_replaces_that_file():
    """`cat SRC > DST` REPLACES DST. Modelling only `cp` skipped the truncation, so
    every later block piled onto a stale copy and duplicated whole sections."""
    cmd = "cat /tmp/claude-1000/rt_head.py > /x/harness/raw_transport.py\n"
    rec = {"message": {"content": [{"type": "tool_use", "name": "Bash",
                                    "input": {"command": cmd}}]}}
    side = {"/tmp/claude-1000/rt_head.py": "HEAD ONLY\n"}
    out, _ = RT.apply_saved_edits("stale body that must not survive\n",
                                  {1: rec}, "harness/raw_transport.py", side=side)
    assert out == "HEAD ONLY\n"


def test_a_command_runs_every_program_not_only_the_first():
    """One command was often several processes: a failure in one did not stop the next."""
    cmd = ('python3 - <<\'PY\'\nraise SystemExit("sibling program failed")\nPY\n'
           'python3 - <<\'PY\'\nimport io\n'
           'p="/x/harness/raw_transport.py"\n'
           's=io.open(p,encoding="utf-8").read().replace("A","B")\n'
           'io.open(p,"w",encoding="utf-8").write(s)\nPY\n')
    rec = {"message": {"content": [{"type": "tool_use", "name": "Bash",
                                    "input": {"command": cmd}}]}}
    out, _ = RT.apply_saved_edits("AAA\n", {1: rec}, "harness/raw_transport.py")
    assert out == "BBB\n"


def test_content_delivered_by_cat_is_not_executed_as_a_program():
    """`cat > x <<'PY'` delivers file CONTENT; executing it too would apply it twice."""
    cmd = "cat > /tmp/claude-1000/section.py <<'PY'\nprint('should not run')\nPY\n"
    assert RT.heredocs(cmd) == []


def test_a_double_quoted_c_program_is_shell_expanded():
    """The shell substituted the command's own variables before Python saw them."""
    cmd = ('H=/tmp/claude-1000/harness\n'
           'python3 -c "import io; p=\'$H/raw_transport.py\'; print(p)"')
    assert "/tmp/claude-1000/harness/raw_transport.py" in RT.heredocs(cmd)[0]
    assert "$H" not in RT.heredocs(cmd)[0]


def test_sed_in_place_edits_are_replayed():
    """`sed -i` was a real editing tool in this campaign. Modelling only python
    programs and redirects meant those edits never happened, so a file kept an older
    value and every later record failed to match it."""
    cmd = ("sed -i 's/^KEYS = {\"a\"}$/KEYS = {\"a\", \"b\"}/' "
           "/x/harness/raw_transport.py\n")
    rec = {"message": {"content": [{"type": "tool_use", "name": "Bash",
                                    "input": {"command": cmd}}]}}
    out, _ = RT.apply_saved_edits('KEYS = {"a"}\n', {1: rec}, "harness/raw_transport.py")
    assert out == 'KEYS = {"a", "b"}\n'


def test_a_basic_regular_expression_is_translated_not_passed_through():
    """In a BRE the escaping is inverted from Python's: `\\(` groups, `(` is literal.
    Passing the pattern through unchanged would turn a literal bracket into a class."""
    # `\{` here is not a valid BRE interval, so sed reads it as a literal brace; a bare
    # `{` is likewise literal to Python, so dropping the backslash is the faithful read.
    assert RT._bre_to_py(r'^receipt = \{"run_id"\}$') == r'^receipt = {"run_id"}$'
    assert RT._bre_to_py(r'"states": \[\]') == r'"states": \[\]'   # brackets stay literal
    assert RT._bre_to_py(r'os.path.join(_HERE)') == r'os.path.join\(_HERE\)'
    assert RT._bre_to_py(r'\(group\)') == r'(group)'


def test_every_binding_of_a_path_variable_is_kept():
    """A multi-file record rebinds the same `p` to each file in turn. Keeping only the
    LAST binding hid every earlier one, so a record that really did rewrite this owner
    looked unrelated to it."""
    import chrono_replay as CR
    cmd = ('python3 - <<\'PY\'\n'
           'p=("/tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers"\n'
           '   "/experiments/harness/"\n'
           '   "audit_worker_access.py")\n'
           's=open(p).read(); open(p,"w").write(s)\n'
           'p=("/tmp/claude-1000/x/subagents/workflows/wf_1/agent-2.jsonl")\n'
           's=open(p).read(); open(p,"w").write(s)\n'
           'PY\n')
    owner = "bench_1306/.claude/plans/Drivers/experiments/harness/audit_worker_access.py"
    assert CR.targets(cmd, owner) is True
    assert CR.writes_this(cmd, owner) is True


AUDITOR_PIN = "9e4762e56c527d95c68b3737dd41d1c478337ed6d38ec0017ea048a855c32229"


def test_the_auditor_is_reproduced_byte_exactly():
    """The second owner, rebuilt from its committed base plus the saved records."""
    assert _sha(os.path.join(_R, "evidence",
                             "audit_worker_access.reproduced_9e4762e5.py")) == AUDITOR_PIN


def test_cat_joins_raw_bytes_and_invents_no_newline():
    """`cat A B` concatenates exactly. Adding a newline to a body that already ended
    with one left the result a single byte long - byte-identical content that still
    missed its digest, which is precisely what held this owner back."""
    cmd = ("cat /tmp/claude-1000/head.py /tmp/claude-1000/body.py > "
           "/x/harness/audit_worker_access.py\n")
    rec = {"message": {"content": [{"type": "tool_use", "name": "Bash",
                                    "input": {"command": cmd}}]}}
    side = {"/tmp/claude-1000/head.py": "HEAD\n", "/tmp/claude-1000/body.py": "BODY\n"}
    out, _ = RT.apply_saved_edits("stale\n", {1: rec},
                                  "harness/audit_worker_access.py", side=side)
    assert out == "HEAD\nBODY\n"          # not "HEAD\nBODY\n\n"


def test_a_cd_plus_relative_path_resolves_to_this_owner():
    """A command routinely cd-ed into a PARENT directory and opened the file by a
    multi-segment relative name. Matching only a cd into the file's own directory
    missed those records entirely."""
    import chrono_replay as CR
    cmd = ("ISO=/tmp/claude-1000/x/scratchpad/step1_iso\n"
           'cd "$ISO/.claude/plans/Drivers/experiments"\n'
           "python3 - <<'PY'\n"
           "p='harness/test_harness_guards.py'; s=open(p).read()\n"
           "open(p,'w').write(s)\nPY\n")
    owner = "step1_iso/.claude/plans/Drivers/experiments/harness/test_harness_guards.py"
    assert CR.targets(cmd, owner) is True
    assert CR.writes_this(cmd, owner) is True


def test_a_shell_append_to_a_relative_path_is_a_write():
    """`cd <parent>` then `cat >> harness/<name>` appends exactly as a program would.
    Modelling only python opens left every such record invisible to the file it
    actually appended to - the single form that took the era-snapshot check from
    reproducing none of seven surviving versions to reproducing five."""
    import chrono_replay as CR
    cmd = ("ISO=/tmp/claude-1000/x/scratchpad/step1_iso\n"
           'cd "$ISO/.claude/plans/Drivers/experiments"\n'
           "cat >> harness/test_harness_guards.py <<'PY'\n"
           "def test_added():\n    pass\nPY\n")
    owner = "step1_iso/.claude/plans/Drivers/experiments/harness/test_harness_guards.py"
    assert CR.writes_this(cmd, owner) is True


def test_a_relative_name_belongs_to_the_cd_that_precedes_it():
    """One command cd-ed into SEVERAL trees. Pairing every cd with every relative name
    resolved a path into a tree the command was not standing in, which is how another
    copy's edit reached an owner."""
    import chrono_replay as CR
    cmd = ("cd /tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/experiments\n"
           "cat >> harness/raw_transport.py <<'PY'\nx = 1\nPY\n"
           "cd /tmp/claude-1000/x/scratchpad/step1_iso/.claude/plans/Drivers/experiments\n"
           "cat >> harness/audit_worker_access.py <<'PY'\ny = 2\nPY\n")
    bench = "bench_1306/.claude/plans/Drivers/experiments/harness"
    iso = "step1_iso/.claude/plans/Drivers/experiments/harness"
    assert CR.writes_this(cmd, bench + "/raw_transport.py") is True
    assert CR.writes_this(cmd, iso + "/audit_worker_access.py") is True
    # neither name may be resolved through the OTHER command's directory
    assert CR.writes_this(cmd, iso + "/raw_transport.py") is False
    assert CR.writes_this(cmd, bench + "/audit_worker_access.py") is False


def test_a_backup_of_this_file_is_captured_so_the_restore_can_run():
    """A command backs the file up, experiments on it, then copies the backup back.
    Tracking only copies INTO the owner meant the backup was never taken, so the
    restore found nothing and the experiment's edit survived a record whose net effect
    in history was nothing at all."""
    cmd = ("cd /x/harness_dir\n"
           "A=audit_worker_access.py\n"
           "cp $A /tmp/claude-1000/aud_backup.py\n"
           "python3 - <<'PY'\n"
           "import io\n"
           "s = io.open('audit_worker_access.py').read()\n"
           "io.open('audit_worker_access.py','w').write(s.replace('KEEP','GONE'))\n"
           "PY\n"
           "cp /tmp/claude-1000/aud_backup.py $A\n")
    rec = {"message": {"content": [{"type": "tool_use", "name": "Bash",
                                    "input": {"command": cmd}}]}}
    out, _ = RT.apply_saved_edits("KEEP\n", {1: rec}, "harness_dir/audit_worker_access.py")
    assert out == "KEEP\n"


def test_a_replayed_program_may_not_shell_out():
    """A saved program that shelled out was OBSERVING a live tree. That tree is gone,
    so running the command now answers from the wrong world - and the answer decides
    what the program does next. The refusal is distinguishable from a failure history
    itself had, and the file is left exactly as the record found it rather than
    half-edited at the point the observation stopped it."""
    cmd = ("python3 - <<'PY'\n"
           "import io, subprocess\n"
           "orig = io.open('/x/harness/raw_transport.py').read()\n"
           "io.open('/x/harness/raw_transport.py','w').write('EDITED\\n')\n"
           "r = subprocess.run(['pytest'], capture_output=True, text=True)\n"
           "print([l for l in r.stdout.splitlines() if 'passed' in l][-1])\n"
           "io.open('/x/harness/raw_transport.py','w').write(orig)\n"
           "PY\n")
    rec = {"message": {"content": [{"type": "tool_use", "name": "Bash",
                                    "input": {"command": cmd}}]}}
    # the record is REFUSED and reported, not silently half-applied: what survives is
    # the text the record found, never the edit the observation interrupted
    try:
        RT.apply_saved_edits("ORIGINAL\n", {1: rec}, "harness/raw_transport.py")
        raise AssertionError("the shelling-out program should have been refused")
    except RT.ReplayEnvironmentError as exc:
        assert "subprocess.run" in str(exc)
    import subprocess as _s
    assert hasattr(_s, "run")           # the real module is restored afterwards


#: file -> (era blobs reproduced byte-exactly, blobs that survive)
#: EVERY surviving version of each file, as Codex SEQ 1542 requires - not a threshold.
ERA = {"guard": ("test_harness_guards.py", 7, 7),
       "auditor": ("audit_worker_access.py", 5, 5),
       "template": ("launch_kfields_a1_slice.template.js", 4, 4)}


def test_the_replay_reproduces_surviving_era_bytes():
    """The strongest evidence in the recovery: real copies of these files, saved during
    the campaign, rebuilt byte-exactly from the records. The digests are read only
    AFTER the replay runs, so they are output assertions like the pins."""
    src = (open(os.path.join(_R, "ledger", "chrono_replay.py")).read() +
           open(os.path.join(_R, "ledger", "replay_transcript.py")).read())
    # THE CUTOFF COMES FROM THE EVENT, NOT THE CLOCK. A delta is the PRE-trigger state
    # and pins to the message that triggered it; a snapshot is the POST-trigger state.
    checker = open(os.path.join(_R, "verify_snapshots.py")).read()
    assert "getmtime" not in checker and "mtime" not in checker.split('"""')[2]
    reports = [f for f in os.listdir(os.path.join(_R, "reports"))
               if f.startswith("era_snapshots_")]
    assert len(reports) == len(ERA)          # both files' evidence survives, not just one
    seen = set()
    for f in sorted(reports):
        rep = json.load(open(os.path.join(_R, "reports", f)))
        assert rep["aligned_by"] == "transcript event order and type"
        assert {r["kind"] for r in rep["snapshots"]} <= {"delta", "snapshot"}
        name = os.path.basename(rep["path"])
        want, total = next((w, t) for _k, (n, w, t) in ERA.items() if n == name)
        seen.add(name)
        assert len(rep["snapshots"]) == total
        assert sum(1 for s in rep["snapshots"] if s["exact"]) >= want
        for s in rep["snapshots"]:
            assert s["era_sha256"] not in src        # never an input to the replay
    assert seen == {n for n, _w, _t in ERA.values()}


A3_RECEIPT_PIN = "19abb07cf23178434ff230443bb1d146f390226fcba3fa20c4a8d2c35e6e1536"


def test_the_a3_primary_receipt_is_rebuilt_byte_exactly_without_a_call():
    """The run that produced this receipt cost 392 paid calls and must never be
    repeated. It is DERIVED instead - from the two reproduced programs, the accepted
    plan, the 36-row ledger read back from history's own printed output, and the 36
    workflow states that still exist. Every count the run's own gate asserted comes
    back with it, which is what makes the digest a result rather than a coincidence."""
    rep = json.load(open(os.path.join(_R, "reports", "a3_receipt_rebuild.json")))
    assert rep["run_id"] == "kf-a3-one-item-196x2-serial-20260821T055948Z"
    assert rep["allowed_calls"] == rep["unique_allowed"] == 392    # the gate's own check
    assert rep["invocations"] == 36                                # the gate's own check
    assert rep["ledger_rows"] == rep["states_recorded"] == rep["unique_states"] == 36
    assert rep["manifest_sha256"] == (
        "d65e4f877ebebfc22f51fb98c3af28ca24c3320772a73046cad90a8955133f28")
    assert rep["max_output_tokens"] == "128000"
    assert rep["sha256"] == A3_RECEIPT_PIN and rep["pin_met"] is True
    assert _sha(os.path.join(_R, "evidence",
                             "a3_receipt.reproduced_19abb07c.json")) == A3_RECEIPT_PIN


A3_RETRY_PIN = "4a2ecf870f390fc67f69d9937a48766a0e990bfff0046c6c486b660453b42465"


def test_the_a3_retry_receipt_is_rebuilt_byte_exactly_without_a_call():
    """The one lawful retry: one key, one invocation, one recorded state, and a parent
    binding to the primary. Its digest matching also CONFIRMS the one figure quoted
    into it - the primary finalization's digest is embedded in these bytes, so it could
    not be wrong and still produce this hash."""
    rep = json.load(open(os.path.join(_R, "reports", "a3_retry_receipt_rebuild.json")))
    assert rep["attempt"] == 2
    assert rep["allowed_calls"] == rep["invocations"] == rep["states_recorded"] == 1
    assert rep["parent"]["receipt_sha256"] == A3_RECEIPT_PIN     # binds to the primary
    assert rep["sha256"] == A3_RETRY_PIN and rep["pin_met"] is True
    assert _sha(os.path.join(_R, "evidence",
                             "a3_retry_receipt.reproduced_4a2ecf87.json")) == A3_RETRY_PIN


A3_FOUR = {
    "a3_receipt.reproduced_19abb07c.json":
        "19abb07cf23178434ff230443bb1d146f390226fcba3fa20c4a8d2c35e6e1536",
    "a3_finalization.reproduced_92e1872c.json":
        "92e1872ce4e171e7829f13274216cff9b32aa237d137d6401cfd34e9c137a8d7",
    "a3_retry_receipt.reproduced_4a2ecf87.json":
        "4a2ecf870f390fc67f69d9937a48766a0e990bfff0046c6c486b660453b42465",
    "a3_retry_finalization.reproduced_15cb7a2d.json":
        "15cb7a2dc8c53f0d9ec093e34b816ff88f5ca678196c1896b32494a13a1f72b2",
}


def test_all_four_a3_artefacts_are_reproduced_byte_exactly():
    """The complete A3 evidence set, rebuilt with NO paid call: the run that produced
    it cost 392 of them and none was repeated."""
    for name, want in A3_FOUR.items():
        assert _sha(os.path.join(_R, "evidence", name)) == want, name


def test_the_a3_evidence_boundary_proves_the_run():
    """SEQ 1542 item 3: the PINNED owner itself is executed, not a copy of its rule.
    `build_kfields_key.py` at a289601b... is the single owner of the A3 evidence
    boundary; its source is verified before and after the call, so an altered owner or
    an altered result fails closed rather than quietly answering."""
    rep = json.load(open(os.path.join(_R, "reports", "a3_evidence_boundary.json")))
    assert rep["owner"] == "build_kfields_key.py"
    assert rep["owner_sha256"] == (
        "a289601b0bf52f223661f63f64128717baabb9ab1d061055119474d3cc4321f9")
    assert rep["owner_unchanged_by_the_call"] is True
    assert rep["callable"] == "a3_evidence"
    assert rep["answers"] == 392          # the canonical A3 call set, proved
    assert rep["problems"] == [] and rep["proved"] is True
    # the durable copy of the owner is the same bytes the boundary ran
    assert _sha(os.path.join(_R, "evidence",
                             "build_kfields_key.pinned_a289601b.py")) == rep["owner_sha256"]


def test_the_accepted_serial_template_is_recovered_from_era_bytes():
    """One of the four pins Codex re-measured survives in the file-history store."""
    assert _sha(os.path.join(_R, "evidence",
                             "launch_kfields_a1_slice.template.era_368bf01c.js")) == (
        "368bf01cb205ccad7e9af90355ab124af5aca5b9efe3f702311f1f4f836b121b")


def test_a_loop_over_filenames_binds_one_variable_to_every_file():
    """A record that renames a symbol across several files walks a TUPLE of names and
    joins each onto a base directory. Matching only single assignments hid every file
    such a record touched - and one of those renames was the reason an anchor went
    unmatched hundreds of records later, in a different file."""
    import chrono_replay as CR
    cmd = ('python3 - <<\'PY\'\n'
           'import io\n'
           'H="/tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/'
           'experiments/harness/"\n'
           'for f in ("build_launch_manifest.py", "launch_kfields_a1_slice.template.js",\n'
           '          "test_harness_guards.py"):\n'
           '    p = H + f\n'
           '    s = io.open(p, encoding="utf-8").read()\n'
           '    io.open(p, "w", encoding="utf-8").write(s.replace("OLD", "NEW"))\n'
           'PY\n')
    base = "bench_1306/.claude/plans/Drivers/experiments/harness/"
    for name in ("build_launch_manifest.py", "launch_kfields_a1_slice.template.js",
                 "test_harness_guards.py"):
        assert CR.targets(cmd, base + name) is True, name
        assert CR.writes_this(cmd, base + name) is True, name
    # a file the loop does NOT name is still not a target
    assert CR.writes_this(cmd, base + "raw_transport.py") is False


REBUILT = {
    "launch_kfields_drafts.manifest.rebuilt_d65e4f87.json":
        "d65e4f877ebebfc22f51fb98c3af28ca24c3320772a73046cad90a8955133f28",
    "launch_kfields_a1.bundle.rebuilt_dc9442f3.json":
        "dc9442f344b59fae521dd6a6f672f7f9d627e143e24920977415ff591c995494",
    "exp5_prompt_drafter.rebuilt_a13289a8.md":
        "a13289a8a135fe7f26beaeef1168a219496f197345063c963e677fa7fa452fef",
    "exp5_prompt_contract.manifest.rebuilt_b76a9de3.json":
        "b76a9de31fb24cda3736b99ad9919c82fc0cb6d439c0b78bab58974bd5b29625",
}


def test_the_a3_build_chain_regenerates_its_artefacts_byte_exactly():
    """These four are GENERATED, not edited: no record carries their bytes, so they
    can only come from running the reconstructed builders. Reproducing all four is a
    single decisive output assertion over the whole chain - the rebuilt builders, the
    era inputs they need, the six protected pins, the runtime identity, and the one
    missing `import io` are all verified at once by these digests matching."""
    for name, want in REBUILT.items():
        assert _sha(os.path.join(_R, "evidence", name)) == want, name


def test_a_line_addressed_sed_insert_is_replayed():
    """`sed -i.bak '10i import io' FILE` inserts BEFORE line 10. Modelling only `s///`
    left a file without a line every later step assumed was there - the import that no
    python program in the whole route ever adds."""
    cmd = "sed -i.bak '2i import io' /x/harness/raw_transport.py\n"
    rec = {"message": {"content": [{"type": "tool_use", "name": "Bash",
                                    "input": {"command": cmd}}]}}
    out, _ = RT.apply_saved_edits("A\nB\n", {1: rec}, "harness/raw_transport.py")
    assert out == "A\nimport io\nB\n"
    # `a` appends AFTER the line, and a file with no trailing newline gains exactly one
    cmd_a = "sed -i '1a X' /x/harness/raw_transport.py\n"
    rec_a = {"message": {"content": [{"type": "tool_use", "name": "Bash",
                                      "input": {"command": cmd_a}}]}}
    out_a, _ = RT.apply_saved_edits("A", {1: rec_a}, "harness/raw_transport.py")
    assert out_a == "A\nX\n"


def test_a_grep_guarded_sed_does_not_insert_a_line_that_is_already_there():
    """`grep PATTERN FILE || sed -i '10i ...'` is how the campaign made an edit
    idempotent. Applying it unconditionally inserts a SECOND copy."""
    cmd = ("grep -n \"^import io\" /x/harness/raw_transport.py || "
           "sed -i.bak '1i import io' /x/harness/raw_transport.py\n")
    rec = {"message": {"content": [{"type": "tool_use", "name": "Bash",
                                    "input": {"command": cmd}}]}}
    already, _ = RT.apply_saved_edits("import io\nB\n", {1: rec},
                                      "harness/raw_transport.py")
    assert already == "import io\nB\n"          # the grep found it: no second copy
    missing, _ = RT.apply_saved_edits("B\n", {1: rec}, "harness/raw_transport.py")
    assert missing == "import io\nB\n"          # the grep failed: the sed runs


def test_the_shim_never_intercepts_the_replays_own_reads():
    """THE defect that blocked this recovery for two sessions. Resolving a sibling runs
    `git show`, and subprocess opens files of its own; those came back into the shim,
    which resolved again, without end. The shim must step aside for the replay itself,
    and its fall-through must use openers captured once at import so a nested replay can
    never chain one shim into another."""
    import chrono_replay as CR
    src = open(os.path.join(_R, "ledger", "replay_transcript.py")).read()
    assert "_REAL_IO_OPEN = io.open" in src
    assert "return _REAL_IO_OPEN(path, mode, *args, **kwargs)" in src
    assert "io.open, builtins.open = _REAL_IO_OPEN, _REAL_BUILTIN_OPEN" in src
    # a cycle is caught on the CANONICAL path, and there is no arbitrary depth cap
    assert CR.canonical_path("./a/../harness/x.py") == "harness/x.py"
    assert CR.looks_like_path("harness/x.py") is True
    assert CR.looks_like_path("not a path\nit is a file's text") is False
    assert "len(_RESOLVING) >=" not in open(
        os.path.join(_R, "ledger", "chrono_replay.py")).read()


def test_a_reentrant_read_sees_the_file_as_far_as_it_is_built():
    """On disk there was ONE file. A program reading it while its own rebuild is in
    flight saw the bytes it had so far, not nothing - returning nothing handed such a
    record a stale committed copy and its anchors then failed."""
    import chrono_replay as CR
    key = CR.canonical_path("/x/harness/in_flight.py")
    CR._RESOLVING.add(key)
    CR._INPROGRESS[key] = (0, "half built\n")
    try:
        assert CR.sibling_text("/x/harness/in_flight.py", 10) == "half built\n"
    finally:
        CR._RESOLVING.discard(key)
        CR._INPROGRESS.pop(key, None)


def test_a_merely_mentioned_relative_path_is_not_a_target():
    """The same rule must not pair every `cd` with every quoted literal: doing so
    pulled an unrelated record into an owner's route."""
    import chrono_replay as CR
    cmd = ("cd /tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/experiments\n"
           "python3 - <<'PY'\n"
           "print('see harness/test_harness_guards.py for the guard')\n"
           "open('harness/other_file.py','w').write('x')\nPY\n")
    owner = "bench_1306/.claude/plans/Drivers/experiments/harness/test_harness_guards.py"
    assert CR.writes_this(cmd, owner) is False


@pytest.mark.reads_chain_outputs
def test_every_mutation_is_killed_with_an_independent_positive_control():
    """SEQ 1542: a passing test proves nothing unless it FAILS when its rule is broken.
    Each case breaks exactly one implementation branch and must be caught, and each
    carries its own positive control on the unmutated rule. A SURVIVED mutation is a
    hole in the evidence and fails here."""
    rep = json.load(open(os.path.join(_R, "reports", "mutations.json")))
    assert rep["total"] >= 22
    assert rep["survived"] == 0 and rep["killed"] == rep["total"]
    for c in rep["cases"]:
        assert c["positive_control"] is True, c["case"]
        assert c["mutant_detected"] is True, c["case"]
    # NO HARNESS ERRORS. An uncaught exception used to be recorded as a killed
    # mutation, so a stale anchor or an unrelated crash earned the same credit as a
    # real behavioural break (Codex SEQ 1554).
    for c in rep["cases"]:
        assert not c.get("error"), (c["case"], c["error"])
    # EVERY RULE IS ACCOUNTED FOR, either by a killed mutation or by an explicit
    # control-only reason. Naming a fixed list of mutations here went stale the moment
    # a fake mutation was retired; the property is what matters, and the branch report
    # is where each rule states which of the two it is.
    inv = json.load(open(os.path.join(_R, "reports", "branch_inventory.json")))
    names = {c["case"] for c in rep["cases"]}
    for row in inv["branches"]:
        if row.get("control_only"):
            assert row["mutation"] is None, row
            assert row["control_only"], row
        else:
            assert row["mutation"] in names, row
    assert inv["branches_without_a_mutation"] == [], inv["branches_without_a_mutation"]
    assert inv["untested_branches"] == [], inv["untested_branches"]


# --------------------------------------------------------------- sed semantics ---
# Codex SEQ 1543 item 4: the replay accepted five incorrect sed behaviours. These are
# written RED first; each states what `sed` actually does, not what the replay did.

def _bash(cmd):
    return {"message": {"content": [{"type": "tool_use", "name": "Bash",
                                     "input": {"command": cmd}}]}}


def test_a_line_address_past_the_end_inserts_nothing():
    """`sed '9i X'` on a 3-line file addresses a line that does not exist, so sed runs
    no cycle for it and the file is unchanged. Clamping to the end INVENTS a line."""
    out, _ = RT.apply_saved_edits(
        "A\nB\nC\n", {1: _bash("sed -i '9i X' /x/harness/raw_transport.py\n")},
        "harness/raw_transport.py")
    assert out == "A\nB\nC\n"


def test_an_empty_file_takes_no_line_insert():
    """With no input lines sed executes no cycle at all, so `1i` adds nothing."""
    out, _ = RT.apply_saved_edits(
        "", {1: _bash("sed -i '1i X' /x/harness/raw_transport.py\n")},
        "harness/raw_transport.py")
    assert out == ""


def test_a_non_global_substitution_applies_once_PER_LINE():
    """`s/a/b/` without `g` replaces the first match on EVERY line - not the first
    match in the whole file. Treating the file as one string silently drops edits."""
    out, _ = RT.apply_saved_edits(
        "a a\na a\n", {1: _bash("sed -i 's/a/b/' /x/harness/raw_transport.py\n")},
        "harness/raw_transport.py")
    assert out == "b a\nb a\n"


def test_the_grep_guard_reads_the_FILE_THE_GREP_NAMES():
    """`grep P OTHER || sed -i ... THIS` guards on OTHER's content. Testing the
    pattern against THIS file answers a question nobody asked."""
    cmd = ("grep -n \"^marker\" /tmp/claude-1000/other.py || "
           "sed -i '1i X' /x/harness/raw_transport.py\n")
    side = {"/tmp/claude-1000/other.py": "marker\n"}      # the grep SUCCEEDS
    out, _ = RT.apply_saved_edits("A\n", {1: _bash(cmd)},
                                  "harness/raw_transport.py", side=side)
    assert out == "A\n"                                   # so the sed must not run


def test_sed_operations_run_in_COMMAND_ORDER():
    """A substitution and a line insert in one command run in the order written.
    Regrouping them by kind changes the result."""
    cmd = ("sed -i '1i first' /x/harness/raw_transport.py\n"
           "sed -i 's/^first$/second/' /x/harness/raw_transport.py\n")
    out, _ = RT.apply_saved_edits("A\n", {1: _bash(cmd)}, "harness/raw_transport.py")
    assert out == "second\nA\n"


def test_sed_i_suffix_keeps_the_pre_edit_bytes_for_a_later_restore():
    """`sed -i.bak` leaves the ORIGINAL content in `<file>.bak`, and the campaign
    restored from it. Without that state the restore finds nothing."""
    cmd = ("sed -i.bak '1i X' /tmp/claude-1000/x.py\n")
    side = {"/tmp/claude-1000/x.py": "A\n"}
    RT.apply_saved_edits("owner\n", {1: _bash(cmd)}, "harness/raw_transport.py",
                         side=side)
    assert side.get("/tmp/claude-1000/x.py.bak") == "A\n"


# ------------------------------------------- shell termination and closure ---
# Codex SEQ 1543 item 1. Both are general forms, stated without any record number.

def test_a_command_whose_shell_was_KILLED_makes_no_edit():
    """A command that terminates its own shell never reaches its later steps. The
    transcript records the termination as the command's whole result, so replaying the
    embedded program invents content the era never had."""
    cmd = ("pkill -f 'some-pattern'; sleep 1\n"
           "python3 - <<'PY'\n"
           "import io\n"
           "p='/x/harness/raw_transport.py'\n"
           "io.open(p,'w').write(io.open(p).read() + 'INVENTED\\n')\n"
           "PY\n")
    rec = {"message": {"content": [{"type": "tool_use", "name": "Bash",
                                    "input": {"command": cmd}}]}}
    out, _ = RT.apply_saved_edits("A\n", {1: rec}, "harness/raw_transport.py",
                                  result="Exit code 144")
    assert out == "A\n"


def test_a_command_that_RUNS_A_SCRIPT_owns_that_script_s_writes():
    """One record writes a helper script, a later record EXECUTES it, and the script
    edits this owner. The consumer never names the owner, so a name-only route misses
    it and every edit the script makes is lost."""
    import chrono_replay as CR
    script = ("import io\n"
              "p = '/tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/"
              "experiments/harness/raw_transport.py'\n"
              "io.open(p, 'w').write(io.open(p).read() + 'FROM SCRIPT\\n')\n")
    cmd = "python3 /tmp/claude-1000/apply_preflight_cli.py\n"
    owner = "bench_1306/.claude/plans/Drivers/experiments/harness/raw_transport.py"
    # SAVE THE SYMBOL THIS TEST ACTUALLY MUTATES. It swapped `RT.SIBLING_RESOLVER`
    # but saved `CR.SIBLING_RESOLVER`, which does not exist - so the restore set the
    # REAL resolver to None and every later replay in the same process lost its
    # siblings. That is what changed the audit route's bytes.
    saved = RT.SIBLING_RESOLVER
    RT.SIBLING_RESOLVER = lambda p, n: script if p.endswith(
        "apply_preflight_cli.py") else None
    try:
        assert CR.writes_this(cmd, owner) is True
        rec = {"message": {"content": [{"type": "tool_use", "name": "Bash",
                                        "input": {"command": cmd}}]}}
        out, _ = RT.apply_saved_edits("BASE\n", {1: rec}, owner)
        assert out == "BASE\nFROM SCRIPT\n"
    finally:
        RT.SIBLING_RESOLVER = saved


def test_a_path_BUILT_INSIDE_THE_OPEN_CALL_still_names_this_owner():
    """`open(H + "name.py", "w")` names the owner as plainly as a variable holding the
    whole path. The command that restored a deleted region to this file wrote it that
    way, and recognising only the assignment form dropped that record from the route -
    so ~92 KB of restored text was never replayed."""
    import chrono_replay as CR
    H = ("/tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/"
         "experiments/harness/")
    cmd = ("cp %stest_harness_guards.py /tmp/claude-1000/thg.bak\n"
           "python3 - <<'PY'\n"
           "import io\n"
           'H = "%s"\n'
           'io.open(H + "test_harness_guards.py", "w", encoding="utf-8").write("X\\n")\n'
           "PY\n") % (H, H)
    base = "bench_1306/.claude/plans/Drivers/experiments/harness/"
    assert CR.writes_this(cmd, base + "test_harness_guards.py") is True
    # a DIFFERENT name built the same way is a DIFFERENT owner
    assert CR.writes_this(cmd, base + "raw_transport.py") is False


def test_a_git_show_REDIRECT_produces_the_file_the_next_step_reads():
    """`git show HEAD:<rel> > SCRATCH` inside a worktree yields that tree's COMMITTED
    bytes - not the bytes the replay has built so far. Without the producer the reader
    finds nothing and the whole command refuses, losing every edit it went on to make."""
    owner = "bench_1306/.claude/plans/Drivers/experiments/harness/raw_transport.py"
    cmd = ("cd /tmp/claude-1000/x/scratchpad/bench_1306 && git show "
           "HEAD:.claude/plans/Drivers/experiments/harness/raw_transport.py "
           "> /tmp/claude-1000/head_rt.py\n")
    side = {}
    RT.seed_git_show(cmd, side)
    import chrono_replay as CR
    assert list(side) == ["/tmp/claude-1000/head_rt.py"]
    # THIS TREE's base, resolved through the route builder's origin hook - not the
    # default commit, which is a different era of the same filename
    want = RT._committed("/x/" + owner, commit=CR.tree_origin("bench_1306")[1])
    assert side["/tmp/claude-1000/head_rt.py"] == want
    assert len(want) > 10000


def test_a_copy_INTO_ANOTHER_TREE_is_not_a_write_of_this_owner():
    """`cp $H/<name> $P/<name>` sends this owner's bytes to a DIFFERENT tree. An
    ABSOLUTE destination names its own tree, so accepting it on the bare filename
    pulled another tree's record into this owner's route and refused there."""
    import chrono_replay as CR
    H = "/tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness"
    P = "/tmp/claude-1000/x/scratchpad/p1319/.claude/plans/Drivers/experiments/harness"
    owner = "bench_1306/.claude/plans/Drivers/experiments/harness/thing.py"
    out = 'H=%s\nP=%s\ncp "$H/thing.py" "$P/thing.py"\n' % (H, P)
    back = 'H=%s\nP=%s\ncp "$P/thing.py" "$H/thing.py"\n' % (H, P)
    assert CR.writes_this(out, owner) is False
    assert CR.writes_this(back, owner) is True
    # the composer must draw the same line, with the source PRESENT either way
    side = {"__owner__": "MINE\n", H + "/thing.py": "MINE\n",
            P + "/thing.py": "THEIRS\n"}
    assert RT._shell_compose(_bash(out), owner, dict(side)) is None
    assert RT._shell_compose(_bash(back), owner, dict(side)) == "THEIRS\n"
    # a RELATIVE destination still resolves by name, because the cwd names its tree
    rel = 'cd %s\ncp /tmp/claude-1000/src.py thing.py\n' % H
    assert RT._shell_compose(_bash(rel), owner,
                             {"__owner__": "MINE\n",
                              "/tmp/claude-1000/src.py": "SRC\n"}) == "SRC\n"


def test_a_BINARY_read_of_a_replayed_file_yields_BYTES():
    """`open(p, "rb").read()` must give bytes. Serving text for every mode made any
    program that hashed a file die with "Strings must be encoded before hashing" -
    a failure of the replay, not of history, which ran that command successfully."""
    owner = "bench_1306/.claude/plans/Drivers/experiments/harness/thing.py"
    prog = ("import hashlib, io\n"
            "d = hashlib.sha256(io.open('thing.py', 'rb').read()).hexdigest()\n"
            "io.open('thing.py', 'w').write('DIGEST ' + d[:8] + '\\n')\n")
    cmd = ("cd /tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/"
           "experiments/harness\npython3 - <<'PY'\n%s\nPY\n" % prog)
    try:
        out, _ = RT.apply_saved_edits("hello\n", {1: _bash(cmd)}, owner, side={})
    except TypeError as exc:
        # serving text for a binary mode makes the program die here; that outcome is
        # what this control judges, so it is named rather than allowed to escape
        out = "the read gave str: %s" % exc
    import hashlib
    assert out == "DIGEST %s\n" % hashlib.sha256(b"hello\n").hexdigest()[:8], out


def test_a_RESULT_IS_FOUND_BY_ITS_TOOL_USE_ID_not_by_proximity():
    """The transcript interleaves assistant text between a command and its result, so
    a fixed look-ahead window misses it. Record 23746's result sits six lines later:
    reading it as ABSENT turned a failure history also had into an unexplained one."""
    got = RT.saved_result(23746)
    assert got is not None
    assert "AssertionError" in got
    # and the window is not merely wider: the result belongs to THIS command
    assert "driver/__init__.py" in got


@pytest.mark.reads_chain_outputs
def test_the_package_is_one_self_verifying_manifest():
    """SEQ 1543 item 3: one manifest over EVERY required file, recorded relative to the
    package root so it verifies from anywhere, with no second manifest to drift against
    and nothing reaching outside through a symlink into the dirty main checkout."""
    import subprocess
    root = _R
    assert os.path.isfile(os.path.join(root, "PACKAGE_MANIFEST.tsv"))
    assert not os.path.exists(os.path.join(root, "MANIFEST.tsv"))
    assert not os.path.exists(os.path.join(root, "bench", "BENCH_MANIFEST.tsv"))
    out = subprocess.run([sys.executable, os.path.join(root, "freeze_package.py"),
                          "--verify"], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "PACKAGE VERIFIES" in out.stdout
    rows = [l.split("\t", 2) for l in
            open(os.path.join(root, "PACKAGE_MANIFEST.tsv")) if l.strip()]
    # the runtime's own dependencies are IN the package, not borrowed from main
    paths = {r[2].strip() for r in rows}
    assert any(p.startswith("bench/driver/") for p in paths)
    assert any("earnings-orchestrator/scripts/guidance_ids.py" in p for p in paths)
    for owner in ("build_kfields_key.py", "build_inventory_review.py",
                  "build_launch_manifest.py", "a2_runtime_freeze.json"):
        assert any(p.endswith("/" + owner) for p in paths), owner
    # no entry may be a link into the working checkout
    assert not [r for r in rows if r[0] == "link"]


def test_the_a2_runtime_identity_is_the_accepted_bytes():
    """SEQ 1543 item 2: the accepted A2 file is 2,337 bytes with NO trailing newline.
    My extraction had added one, and the recovered index froze that wrong identity."""
    want = "c534022d391e409f48ae65a0ded6bbf7eb428d4a92a00407646cad77f8ef794a"
    for rel in ("recovered/a2_runtime_freeze.json",
                "bench/.claude/plans/Drivers/experiments/harness/a2_runtime_freeze.json"):
        p = os.path.join(_R, rel)
        assert _sha(p) == want, rel
        assert os.path.getsize(p) == 2337
        assert not open(p, "rb").read().endswith(b"\n")
    idx = open(os.path.join(_R, "recovered", "RECOVERED.tsv")).read()
    assert want in idx


def test_two_spellings_of_one_path_CANONICALISE_the_same():
    """An alias must resolve to one identity, or the same file looks like two and a
    re-entrant read never finds the copy already being built."""
    import chrono_replay as _CR
    assert _CR.canonical_path("./a/../harness/x.py") == _CR.canonical_path("harness/x.py")
    assert _CR.canonical_path("harness/x.py") != _CR.canonical_path("harness/y.py")


def test_a_whole_FILE_TEXT_is_not_mistaken_for_a_path():
    """`looks_like_path` recognises a path; a file's entire body is not one, and
    treating it as one turned file contents into route targets."""
    import chrono_replay as _CR
    blob = "not a path\nit is a whole file's text\n" * 40
    assert _CR.looks_like_path(blob) is False
    assert _CR.looks_like_path("harness/raw_transport.py") is True

def test_tree_origin_is_found_when_the_command_names_the_tree_through_a_variable():
    """bench_1306 was created by `git worktree add --detach "$B" <commit>` with
    B=$S/bench_1306: the full path is never in the saved line, only the name."""
    import re
    import chrono_replay as CR
    tree = RT._SCRATCH + "/bench_1306"
    rec = RT.lines({22310})[22310]
    cmd = RT.bash_command(rec)
    want = re.search(r"worktree add --detach \"\$B\" ([0-9a-f]{40})", cmd).group(1)
    CR._ORIGINS.pop(tree, None)
    assert CR.tree_origin(tree) == (22310, want)


def test_a_reentrant_read_honours_its_cutoff():
    """In-flight bytes are served only for a cutoff at or beyond the rebuilt position:
    a nested read asking for an EARLIER line must not see them (rule 14)."""
    import chrono_replay as CR
    key = CR.canonical_path("/x/harness/in_flight_cut.py")
    CR._RESOLVING.add(key)
    CR._INPROGRESS[key] = (100, "NEW\n")
    try:
        assert CR.sibling_text("/x/harness/in_flight_cut.py", 150) == "NEW\n"
        assert CR.sibling_text("/x/harness/in_flight_cut.py", 50) != "NEW\n"
    finally:
        CR._RESOLVING.discard(key)
        CR._INPROGRESS.pop(key, None)
