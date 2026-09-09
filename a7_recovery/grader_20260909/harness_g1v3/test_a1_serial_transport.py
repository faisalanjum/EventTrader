"""The A1 launcher must hold at most ONE agent() call in flight.

Codex SEQ 1355 item 3: an 18-at-once burst is what the service refused. The
frozen CALLS list, its order, every prompt, lane, identity and row shape stay
exactly as they are; only the number in flight changes. These proofs execute the
REAL generated launcher against the fake Workflow hooks - no AI, no network.

    venv/bin/python -m pytest <this file> -q
"""
import io
import json
import os
import shutil
import subprocess

import pytest

import build_launch_manifest as blm
import raw_transport as RT

_HERE = os.path.dirname(os.path.abspath(__file__))
_NODE = shutil.which("node")
LAWFUL = ('{"source_id":"X","facts":[],"abstentions":[],"continuity_hints":[]}')


def _armed(tmp_path):
    """One lawfully armed invocation, through the public publisher."""
    prep = RT.a1_prepare_run(str(tmp_path / "armed"))
    assert prep["ok"], prep["problems"][:3]
    return prep["invocations"][0]


def _replay(tmp_path, inv, replies=None, default=LAWFUL):
    cfg = {"launchers": [{"path": inv["scriptPath"], "args": inv["args"]}],
           "replies": replies, "default_reply": default,
           "provide_process": False, "env": {}}
    cfgp = str(tmp_path / "cfg.json")
    io.open(cfgp, "w", encoding="utf-8").write(json.dumps(cfg))
    out = subprocess.run([_NODE, os.path.join(_HERE, "run_launcher_fake.mjs"),
                          cfgp], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr[-1500:]
    return json.loads(out.stdout)


def _prompt_shas(inv):
    """The prompt hash of each planned call, in the launcher's own order."""
    plan = json.load(io.open(os.path.join(
        _HERE, "launch_kfields_drafts.manifest.json"), encoding="utf-8"))
    by_pid = {p["packet_id"]: p["prompt_sha256"] for p in plan["packets"]}
    return [by_pid[a["packet_id"]] for a in inv["args"]]


@pytest.mark.skipif(_NODE is None, reason="node is unavailable")
def test_the_launcher_holds_exactly_one_agent_in_flight(tmp_path):
    """THE DEFECT. Every planned call still happens, one at a time."""
    inv = _armed(tmp_path)
    res = _replay(tmp_path, inv)
    assert res["errors"] == [], res["errors"][:2]
    assert res["maxActive"] == 1, (
        "%d agent calls were in flight at once" % res["maxActive"])
    assert len(res["calls"]) == 2 * len(inv["args"]), \
        "the serial launcher dropped calls: %d of %d" % (
            len(res["calls"]), 2 * len(inv["args"]))


@pytest.mark.skipif(_NODE is None, reason="node is unavailable")
def test_order_and_full_output_survive_the_serial_transport(tmp_path):
    """LAWFUL CONTROL: same calls, same order, every row returned."""
    inv = _armed(tmp_path)
    res = _replay(tmp_path, inv)
    want = [h for h in _prompt_shas(inv) for _lane in (0, 1)]
    assert [c["prompt_sha256"] for c in res["calls"]] == want, \
        "the serial launcher reordered its frozen CALLS"
    assert len(res["rows"]) == 2 * len(inv["args"])
    assert all(r["text"] == LAWFUL for r in res["rows"]), \
        "a reply was altered in transit"
    assert not any(c["schema"] for c in res["calls"])
    lanes = [r["lane_id"] for r in res["rows"]]
    assert len(set(lanes)) == len(lanes), "a lane was answered twice"


@pytest.mark.skipif(_NODE is None, reason="node is unavailable")
def test_a_no_answer_retains_its_row_and_launches_nothing_later(tmp_path):
    """The exact live failure: the runtime returns no answer mid-invocation."""
    inv = _armed(tmp_path)
    shas = _prompt_shas(inv)
    assert len(shas) >= 3, "this source is too small to prove a mid-run stop"
    dead = shas[1]                      # the second packet, both its lanes
    replies = {h: LAWFUL for h in shas}
    replies[dead] = None                # an explicit runtime no-answer
    res = _replay(tmp_path, inv, replies=replies)
    assert res["maxActive"] == 1, res["maxActive"]
    served = [c["prompt_sha256"] for c in res["calls"]]
    assert served[0] == shas[0] and dead in served, served[:4]
    assert shas[2] not in served, \
        "a later call was launched after the no-answer: %s" % served
    attempted = [r for r in res["rows"] if r["text"] is None]
    assert attempted, "the attempted row was dropped instead of retained"
    assert all(r["text"] == LAWFUL for r in res["rows"] if r["text"] is not None)


@pytest.mark.skipif(_NODE is None, reason="node is unavailable")
def test_every_lane_still_carries_the_pinned_identity_and_deny(tmp_path):
    """LAWFUL CONTROL: serialising changed nothing about what is asked for."""
    inv = _armed(tmp_path)
    res = _replay(tmp_path, inv)
    for c in res["calls"]:
        assert c["model"] == blm.PINNED_MODEL
        assert c["effort"] == blm.PINNED_EFFORT
        assert c["agentType"] == blm.PINNED_AGENT_TYPE
        assert c["disallowedTools"] == list(blm.A1_DISALLOWED)
