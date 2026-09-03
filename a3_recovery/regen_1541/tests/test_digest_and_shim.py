"""Two live rules that were being treated as byte pins (Codex SEQ 1555 item 3).

`_recovered` is fail-closed BEHAVIOUR, not an equality: it must REFUSE a recovered body
whose bytes do not match the digest recorded beside it. And the shim must step aside
while the replay's own machinery reads, or resolving a sibling re-enters the shim.
"""
import contextlib
import hashlib
import io
import os
import sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(R, "ledger"))
import chrono_replay as CR                                    # noqa: E402
import replay_transcript as RT                                # noqa: E402


def test_a_recovered_body_that_does_not_match_its_digest_is_REFUSED(tmp_path):
    """A copied index and a body that does not hash to it: nothing may be served."""
    good = "REAL BODY\n"
    stage = str(tmp_path)
    io.open(os.path.join(stage, "thing.json"), "w", encoding="utf-8").write("TAMPERED\n")
    io.open(os.path.join(stage, "RECOVERED.tsv"), "w", encoding="utf-8").write(
        "%s\t.claude/x/thing.json\n" % hashlib.sha256(good.encode()).hexdigest())
    saved = CR._RECOVERED_DIR
    CR._RECOVERED_DIR = stage
    try:
        assert CR._recovered("/x/.claude/x/thing.json", 10) is None
        # and the matching body IS served, so the refusal is about the digest
        io.open(os.path.join(stage, "thing.json"), "w", encoding="utf-8").write(good)
        assert CR._recovered("/x/.claude/x/thing.json", 10) == good
    finally:
        CR._RECOVERED_DIR = saved


def test_the_shim_steps_aside_while_the_replay_reads_for_itself():
    """The shim must be OFF while the replay's own machinery reads.

    The resolver reads a scratch-root path for itself, the same shape `_committed`
    uses. Stepped aside, that read reaches the real filesystem and finds nothing.
    Left installed, the shim answers the replay's own read from its in-memory copy
    and calls the resolver again for it - so the replay resolves out of itself,
    without end.
    """
    H = "/tmp/claude-1000/x/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness"
    probe = H + "/probe_not_on_disk.txt"
    side = {probe: "SHIM ANSWER\n"}
    seen = {}

    def resolver(path, line):
        if seen.get("busy"):
            seen["got"] = "SHIM ANSWERED THE REPLAY'S OWN READ"
            return "RE-ENTERED\n"
        seen["busy"] = True
        try:
            seen["got"] = io.open(probe, encoding="utf-8").read()
        except (IOError, OSError):
            seen["got"] = "REAL FILESYSTEM SAYS NO"
        finally:
            seen["busy"] = False
        return "RESOLVED\n"

    owner = "bench_1306/.claude/plans/Drivers/experiments/harness/thing.py"
    cmd = ("cd %s\npython3 - <<'PY'\nimport io\n"
           "t = io.open('%s/sibling.py').read()\n"
           "io.open('%s/thing.py','w').write(t)\nPY\n" % (H, H, H))
    rec = {"message": {"content": [{"type": "tool_use", "name": "Bash",
                                    "input": {"command": cmd}}]}}
    saved = RT.SIBLING_RESOLVER
    RT.SIBLING_RESOLVER = resolver
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            RT.apply_saved_edits("BASE\n", {1: rec}, owner, side=side)
    except RecursionError:
        seen["got"] = "SHIM FED ITSELF WITHOUT END"
    finally:
        RT.SIBLING_RESOLVER = saved
    assert seen.get("got") == "REAL FILESYSTEM SAYS NO", seen
