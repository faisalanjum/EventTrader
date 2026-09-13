"""The A1 reader lanes must be armed with a REAL no-tool boundary.

Codex SEQ 1348: `a2_runtime_freeze.json` claimed every launcher disallowed Read,
but no launcher ever passed `disallowedTools`, and `lean-probe` grants exactly
Read - so one reader reached for it mid-run. These are the smallest checks that
fail while the deny is absent and pass once the ONE owner renders it.

Nothing here is hand-listed: the expected deny is read from its owner constant,
so changing that constant moves every assertion with it.

    venv/bin/python -m pytest <this file> -q
"""
import io
import json
import os
import shutil
import subprocess

import pytest

import build_launch_manifest as blm

_HERE = os.path.dirname(os.path.abspath(__file__))
_NODE = shutil.which("node")


def _deny():
    """The owner's own value - never a literal typed into this file."""
    return list(blm.A1_DISALLOWED)


def _derived_launcher_texts():
    return blm.derive_expected()["launchers"]


# ------------------------------------------------------------------- RED 1 ---
#: how the renderer names the deny inside the slice, and how agent() receives it
CONST = "PINNED_DISALLOWED_TOOLS"
DEFINE = "const %s = " % CONST
PASSES = "disallowedTools: %s," % CONST


def test_every_rendered_launcher_defines_and_passes_exactly_the_owner_deny():
    """The value must come from the owner, and every launcher must hand it to
    agent(). A launcher that defines it but never passes it is still tool-open."""
    texts = _derived_launcher_texts()
    want = DEFINE + json.dumps(_deny())
    undefined = [sid for sid, t in texts.items() if want not in t]
    unpassed = [sid for sid, t in texts.items() if PASSES not in t]
    assert not undefined, ("%d of %d launchers do not define %s"
                           % (len(undefined), len(texts), want))
    assert not unpassed, ("%d of %d launchers never pass %s to agent()"
                          % (len(unpassed), len(texts), PASSES))


def test_the_plan_transport_claim_comes_from_the_same_owner():
    """The plan must not restate the deny independently of the constant."""
    plan = json.load(io.open(os.path.join(
        _HERE, "launch_kfields_drafts.manifest.json"), encoding="utf-8"))
    assert plan["transport"].get("disallowedTools") == _deny(), (
        "the plan transport says %r, the owner says %r"
        % (plan["transport"].get("disallowedTools"), _deny()))


# ------------------------------------------------------------------- RED 2 ---
@pytest.mark.skipif(_NODE is None, reason="node is unavailable")
def test_the_fake_agent_control_sees_the_deny_on_every_actual_call(tmp_path):
    """THE LOAD-BEARING ONE: arm a real launcher the lawful way, execute it with
    the fake agent hooks, and assert the option that actually reaches agent().

    A committed launcher refuses to call until the coordinator arms it, so this
    goes through the public publisher rather than hand-editing the receipt.
    """
    import raw_transport as RT
    run_dir = str(tmp_path / "armed")
    prep = RT.a1_prepare_run(run_dir)
    assert prep["ok"], prep["problems"][:3]
    plan = json.load(io.open(os.path.join(
        _HERE, "launch_kfields_drafts.manifest.json"), encoding="utf-8"))
    inv = prep["invocations"][0]
    cfg = {"launchers": [{"path": inv["scriptPath"], "args": inv["args"]}],
           "replies": None,
           "default_reply": '{"source_id":"X","facts":[],"abstentions":[],'
                            '"continuity_hints":[]}',
           "provide_process": False, "env": {}}
    cfgp = str(tmp_path / "cfg.json")
    io.open(cfgp, "w", encoding="utf-8").write(json.dumps(cfg))
    out = subprocess.run([_NODE, os.path.join(_HERE, "run_launcher_fake.mjs"),
                          cfgp], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr[-1500:]
    calls = json.loads(out.stdout)["calls"]
    assert len(calls) == 2 * len(inv["args"]), (
        "expected two lanes per packet, saw %d calls for %d packets"
        % (len(calls), len(inv["args"])))
    bad = [c.get("disallowedTools") for c in calls
           if c.get("disallowedTools") != _deny()]
    assert not bad, ("%d of %d actual agent() calls did not carry %r (saw %r)"
                     % (len(bad), len(calls), _deny(), bad[:3]))
    assert not any(c.get("schema") for c in calls), \
        "schema: would let JS parse the reply before Python sees it"


# ------------------------------------------------------------------- RED 3 ---
def test_removing_the_deny_from_one_launcher_makes_the_derived_check_refuse(
        tmp_path, monkeypatch):
    """MUTATION: the existing preflight re-derives launcher bytes and compares
    them to what is on disk, so deleting the deny from ONE launcher must be
    refused by the check that already exists - no new proof framework."""
    mirror = str(tmp_path / "harness")
    shutil.copytree(_HERE, mirror,
                    ignore=shutil.ignore_patterns("__pycache__", "runs"))
    monkeypatch.setattr(blm, "_HERE", mirror)
    # The recovered harness carries no generated A1 pair, so the mirror is armed by
    # the SAME builder the preflight re-derives against - never a copied lineage
    # whose bytes this owner does not derive.
    blm.build()
    victim = sorted(_derived_launcher_texts())[0]
    lp = os.path.join(mirror, "launchers_a1",
                      "kfields_a1_%s.workflow.js" % victim)
    text = io.open(lp, encoding="utf-8").read()
    assert PASSES in text, (
        "the on-disk launcher never passed %s, so there is nothing to remove"
        % PASSES)
    env = {blm.OUTPUT_TOKENS_VAR: blm.MAX_OUTPUT_TOKENS_SETTING}

    # LAWFUL CONTROL: untouched, no reason may name this launcher. (A mirror
    # re-derives its own launcher paths, so unrelated reasons can exist; the
    # victim's name is what must appear only after the deny is removed.)
    before = blm.preflight(env=env, run_dir=str(tmp_path / "fresh_a"))
    assert not any(victim in r for r in before), (
        "the control already blamed %s: %s" % (victim, before[:3]))

    io.open(lp, "w", encoding="utf-8").write(
        text.replace("    " + PASSES + "\n", "", 1))
    after = blm.preflight(env=env, run_dir=str(tmp_path / "fresh_b"))
    named = [r for r in after if victim in r]
    assert named, ("removing the deny from %s was NOT refused; reasons were %s"
                   % (victim, after[:3]))
    assert len(after) == len(before) + 1, (
        "the removal should add exactly one reason, not %d"
        % (len(after) - len(before)))
