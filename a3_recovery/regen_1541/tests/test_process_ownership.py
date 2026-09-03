"""A shell command is not one owner - it is several PROCESSES (Codex SEQ 1544 item 2).

Classifying a whole Bash tool call at once let three things go wrong at once: a `cd`
into a sibling tree was ignored, so records that edit `harness_g1v3` were pulled into
`harness`'s route; a filename appearing only as TEXT inside a Python string classified
the surrounding shell; and selecting a command executed every unrelated program that
happened to share the call.

Every control here is a real record from the live transcript, not a fixture.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "ledger"))
import chrono_replay as CR                                    # noqa: E402
import replay_transcript as RT                                # noqa: E402

H = ".claude/plans/Drivers/experiments/harness"
GUARD = "bench_1306/%s/test_harness_guards.py" % H
G1V3 = "bench_1306/%s_g1v3/test_harness_guards.py" % H
RAW = "bench_1306/%s/raw_transport.py" % H


def cmd(line):
    rec = RT.lines([line])[line]
    for b in ((rec.get("message") or {}).get("content") or []):
        if isinstance(b, dict) and b.get("type") == "tool_use":
            return (b.get("input") or {}).get("command") or ""
    raise AssertionError("line %d carries no command" % line)


def test_a_cd_into_a_SIBLING_TREE_keeps_its_records_out_of_this_route():
    """72328/72642/72698 `cd` into `harness_g1v3` and edit a RELATIVE
    `test_harness_guards.py`. The cwd names the tree; ignoring it put another tree's
    records into this owner's route, where they could only refuse."""
    for line in (72328, 72642, 72698):
        assert CR.writes_this(cmd(line), GUARD) is False, line
        assert CR.writes_this(cmd(line), G1V3) is True, line


def test_a_NAME_INSIDE_A_PYTHON_STRING_does_not_classify_the_shell():
    """28721 only PRINTS `-> test_harness_guards.py`. It writes nothing at all."""
    assert CR.writes_this(cmd(28721), GUARD) is False
    assert CR.writes_this(cmd(28721), RAW) is False


def test_ONE_CALL_TWO_PROCESSES_are_owned_separately():
    """24246 process 0 writes `driver_write_cli.py` - neither owner; process 1 writes
    the guard. 25048 process 0 writes the guard, process 1 writes raw_transport."""
    u = RT.process_units(cmd(24246))
    progs = [x for x in u if x[3] == "program"]
    assert len(progs) >= 2
    assert CR.unit_writes(progs[0], GUARD) is False
    assert CR.unit_writes(progs[1], GUARD) is True

    u2 = [x for x in RT.process_units(cmd(25048)) if x[3] == "program"]
    assert len(u2) >= 2
    assert CR.unit_writes(u2[0], GUARD) is True
    assert CR.unit_writes(u2[0], RAW) is False
    assert CR.unit_writes(u2[1], RAW) is True
    assert CR.unit_writes(u2[1], GUARD) is False


def test_a_record_that_writes_NEITHER_owner_is_in_no_route():
    """25012 writes raw_transport and kf_lint; it is not this guard's record."""
    assert CR.writes_this(cmd(25012), GUARD) is False


def test_only_the_OWNING_processes_of_a_call_are_executed():
    """Selecting a command must not run its unrelated sibling programs: 25048's second
    process edits raw_transport and has nothing to say about the guard."""
    sel = CR.selected_units(cmd(25048), GUARD)
    assert [i for i, _ in sel] == [0]


def test_a_heredoc_whose_OPENING_LINE_CONTINUES_is_still_a_program():
    """`python3 - <<'PY' 2>&1 | tail -22` runs a program exactly as `<<'PY'` does. The
    span pattern required the tag to end the line, so every such record was invisible:
    its program never replayed and the files it produced were never built."""
    cmd = ("cd /tmp/x && /usr/bin/python3 -B - <<'PY' 2>&1 | tail -22\n"
           "import io\n"
           "io.open('out.json','w').write('[]')\n"
           "PY\n")
    spans = RT.program_spans(cmd)
    assert len(spans) == 1, spans
    assert "io.open('out.json','w')" in spans[0][2]
    # the plain form still works, and a heredoc that only DELIVERS content is not a
    # program
    assert len(RT.program_spans("cat > f.txt <<'PY'\nbody\nPY\n")) == 0


def test_the_lead_pool_builder_at_22345_is_seen_as_a_program():
    """The record that builds the discovery lead pool uses exactly that shape."""
    spans = RT.program_spans(cmd(22345))
    assert len(spans) == 1, len(spans)
    assert "lead_pool" in spans[0][2]
