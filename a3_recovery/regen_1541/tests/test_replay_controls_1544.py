"""Four replay rules the previous suite could not see (Codex SEQ 1544 item 3)."""
import os
import sys

_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_R, "ledger"))
sys.path.insert(0, _R)
import chrono_replay as CR                                    # noqa: E402
import replay_transcript as RT                                # noqa: E402
import replay_caches                                          # noqa: E402

OWNER = "bench_1306/.claude/plans/Drivers/experiments/harness/thing.py"
H = "/tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness"


def rec(command):
    return {"message": {"content": [{"type": "tool_use", "name": "Bash",
                                     "input": {"command": command}}]}}


def test_TERMINATION_is_decided_before_any_composer_or_program_runs():
    """A command whose whole result is a termination status never reached ANY of its
    steps. The check ran after the shell composer, so a killed command still appended
    - inventing a line history never had."""
    cmd = "cat >> %s/thing.py <<'PY'\nINVENTED\nPY\n" % H
    out, _ = RT.apply_saved_edits("BASE\n", {1: rec(cmd)}, OWNER, side={},
                                  result="Exit code 144")
    assert out == "BASE\n"


def test_a_SCRIPT_is_cached_per_CUTOFF_not_per_path():
    """A script is rebuilt from its own history, so its text at cutoff 30 is not its
    text at cutoff 10. Caching by path alone served the earlier text forever."""
    CR._SCRIPT_CACHE.clear()
    path = "/tmp/claude-1000/s/tool.py"
    calls = []

    def resolver(p, before):
        calls.append(before)
        return "AT_%d\n" % before

    saved = RT.SIBLING_RESOLVER
    RT.SIBLING_RESOLVER = resolver
    try:
        cmd = "python3 %s\n" % path
        a = CR._executed_script_texts(cmd, 10)
        b = CR._executed_script_texts(cmd, 30)
    finally:
        RT.SIBLING_RESOLVER = saved
    assert a == ["AT_10\n"], a
    assert b == ["AT_30\n"], b


def test_RESUMING_a_resolution_equals_rebuilding_it_from_scratch():
    """Resolution resumes from the last cutoff for speed. A LATER consumer can reveal an
    EARLIER producer, so the route at the wider cutoff holds a record the narrow one
    never had - and a resume that applies only records AFTER the last cutoff skips it.

    THE SECOND CALL MUST ACTUALLY REBUILD. Clearing only `_LAST_RESOLVED` left
    `_SIBLING_CACHE` (and the on-disk cache) to answer instantly, so both sides returned
    the same cached string and this control compared nothing. Every cache is isolated
    here, and the expected value is calculated independently from the record list.
    """
    import uuid
    path = "/tmp/claude-1000/s/built_%s.py" % uuid.uuid4().hex[:12]
    steps_wide = {5: "A", 8: "P", 18: "M"}
    expected = "".join(v for _n, v in sorted(steps_wide.items()))   # "APM", not observed

    def route(first, upto):
        # the producer at 8 is only revealed once the consumer at 18 is in view
        steps = {5: "A", 18: "M"} if upto < 15 else steps_wide
        return [(n, rec("python3 - <<'PY'\nimport io\n"
                        "t = io.open(%r).read()\n"
                        "io.open(%r,'w').write(t + %r)\nPY\n" % (path, path, v)))
                for n, v in sorted(steps.items()) if first <= n <= upto]

    saved = {k: getattr(CR, k) for k in
             ("route_records", "_disk_get", "_disk_put")}
    # CLEARING A CACHE IS NOT ISOLATION. Emptying `_SIBLING_CACHE` and `_LAST_RESOLVED`
    # destroys whatever the rest of the run put there; the fence below hands back the
    # exact contents, and the same objects, afterwards (Codex SEQ 1556 item 1).
    with replay_caches.preserved(CR, RT):
        CR.route_records = lambda owner, first, upto: (route(first, upto), None)
        CR._disk_get = lambda p, n: None        # the on-disk cache may not answer
        CR._disk_put = lambda p, n, t: None
        try:
            CR._SIBLING_CACHE.clear()
            CR._LAST_RESOLVED.clear()
            CR.sibling_text(path, 10, first=1)                 # warm the resume point
            resumed = CR.sibling_text(path, 20, first=1)
            # a genuinely FRESH rebuild: every cache emptied, not just the resume point
            CR._SIBLING_CACHE.clear()
            CR._LAST_RESOLVED.clear()
            fresh = CR.sibling_text(path, 20, first=1)
        finally:
            for k, v in saved.items():
                setattr(CR, k, v)
    assert fresh == expected, (fresh, expected)
    assert resumed == expected, (resumed, expected)


def test_an_UNRELATED_programs_missing_subprocess_cannot_erase_this_owners_write():
    """Two processes share one Bash call: the first shells out (impossible here), the
    second writes this owner. Running both let the first process's environment failure
    revert the second's write, losing a real edit."""
    # the unrelated program writes ANOTHER file: if it ran, that write shows in the side
    # table; a cut-short restore (rule 26) can no longer hide that it ran
    cmd = ("python3 - <<'PY'\nimport io\n"
           "io.open('%s/other.py','w').write('X\\n')\nPY\n"
           "python3 - <<'PY'\nimport io\n"
           "io.open('%s/thing.py','w').write('OWNER\\n')\nPY\n" % (H, H))
    side = {}
    try:
        out, _ = RT.apply_saved_edits("BASE\n", {1: rec(cmd)}, OWNER, side=side)
    except RT.ReplayEnvironmentError as exc:
        out = "the unrelated process was run: %s" % exc
    assert out == "OWNER\n", out
    assert not any(k.endswith("/other.py") for k in side), "the unrelated program ran"
