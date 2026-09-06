"""A5 public-route regression, frozen permanently. Codex SEQ 1406.

Everything here was proved once in throwaway scratch during SEQ 1405 and had NO
permanent test, so the six shared-seam fixes could regress silently. Nothing new
is invented: the A1 temp-project official-evidence fixtures are reused as-is.

A1 and A5 render byte-identical prompts from the same owner
(`build_launch_manifest.one_item_prompts(role="drafter")`), so `_a1_replies`,
`_a1_execute`, `_a1_finalize_in` and `_prepare_retry_in` drive an A5 run
unchanged. Only "prepare" differs, and that is the one helper added below.

NO MODEL CALL: every launcher is executed by the existing fake runner, which
refuses to answer a prompt whose bytes are not the pinned ones.
"""
import io
import json
import os
import shutil
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import build_a5_exp5_kit as A5                                   # noqa: E402
import build_launch_manifest as BLM                              # noqa: E402
import raw_transport as RT                                       # noqa: E402
import test_harness_guards as TG        # the ONE official-run fixture, reused


def _a5_prepare_in(work, run_dir):
    """Prepare an A5 run inside the mirror, through its PUBLIC entry.

    The mirror keeps the REAL a2_runtime_freeze.json, which A5 pins by sha, so
    this deliberately does NOT use `_a1_gate_open` (that rewrites the freeze
    file and would break the pin it is supposed to prove).
    """
    code = ("import json,sys;sys.path.insert(0,%r);"
            "import build_a5_exp5_kit as A5;"
            "print(json.dumps(A5.prepare(%r)))" % (str(work), str(run_dir)))
    got = subprocess.run(
        [sys.executable, "-B", "-c", code], cwd=str(work),
        capture_output=True, text=True,
        env=dict(os.environ, CLAUDE_CODE_MAX_OUTPUT_TOKENS="128000",
                 PYTHONPATH=str(work.parent.parent.parent.parent.parent)
                 + os.pathsep + TG._REPO, PYTHONDONTWRITEBYTECODE="1"))
    assert got.returncode == 0, got.stderr[-2500:]
    return json.loads(got.stdout)


def _a5_plan_of(run_dir):
    """The plan THIS run was published under — read the way the seam reads it."""
    return RT.a1_plan_for_run(str(run_dir))


def _planned_calls(plan):
    """The denominator DERIVED from the plan, never read back out of the
    receipt being checked - otherwise `scheduled == len(allowed)` is a
    tautology that passes on a 2-call run."""
    return len(plan["packets"]) * len(plan["arms"])


def _raw_rows(run_dir):
    d = os.path.join(str(run_dir), "raw")
    return len(os.listdir(d)) if os.path.isdir(d) else 0


def _a5_run(tmp_path, replies_for=None, mutate_after=None, tag="a5"):
    """One complete A5 public run, ready to finalize, in an isolated mirror."""
    work = TG._mirror(tmp_path)
    run_dir = tmp_path / "a5run"
    prep = _a5_prepare_in(work, run_dir)
    assert prep["ok"], prep["problems"][:3]
    plan = _a5_plan_of(run_dir)
    replies = TG._a1_replies(plan)
    if replies_for is not None:
        replies_for(plan, replies)
    projects = str(tmp_path / "projects")
    TG._a1_execute(work, tmp_path, prep, plan, projects, replies, tag)
    if mutate_after is not None:
        mutate_after(run_dir)
    return {"work": work, "run_dir": run_dir, "projects": projects,
            "plan": plan, "prep": prep, "replies": replies}


def _corrupt_one_lane(fix, packet_id, lane_id, bad="{not json"):
    """Make EXACTLY ONE already-served call's answer unparseable.

    Replacing a reply by prompt_sha256 cannot do this: both lanes of a packet
    receive the SAME prompt bytes, so that route corrupts TWO calls and a test
    that only checks the packet id passes while proving the wrong thing
    (Codex SEQ 1407 item 1). So the lawful run is left intact and one isolated
    piece of its official evidence is altered - the result row AND the
    assistant transcript text it must agree with - before finalization.
    """
    wf = os.path.join(fix["projects"], "proj", "sess", "workflows")
    for name in sorted(os.listdir(wf)):
        path = os.path.join(wf, name)
        with io.open(path, encoding="utf-8") as fh:
            state = json.load(fh)
        rows = [r for r in state["result"]["results"]
                if (r["packet_id"], r["lane_id"]) == (packet_id, lane_id)]
        if not rows:
            continue
        rows[0]["text"] = bad
        agents = [pr["agentId"] for pr in state["workflowProgress"]
                  if pr.get("label") == lane_id]
        assert len(agents) == 1, agents
        with io.open(path, "w", encoding="utf-8") as fh:
            json.dump(state, fh)
        tx = os.path.join(fix["projects"], "proj", "sess", "subagents",
                          "workflows", state["runId"],
                          "agent-%s.jsonl" % agents[0])
        recs = [json.loads(l) for l in io.open(tx, encoding="utf-8") if l.strip()]
        last = [r for r in recs if r["type"] == "assistant"][-1]
        last["message"]["content"][-1]["text"] = bad
        with io.open(tx, "w", encoding="utf-8") as fh:
            for r in recs:
                fh.write(json.dumps(r) + "\n")
        return
    raise AssertionError("no served row for %s %s" % (packet_id, lane_id))


# ------------------------------------------ item 2: the lawful full-392 route
@TG._needs_node
def test_a5_public_route_runs_end_to_end_on_all_lawful_reply_shapes(tmp_path):
    """THE CONTROL. prepare -> the RETURNED invocations -> record -> audit ->
    finalize, over every planned call.

    SEQ 1405's control was abstention-only. `_a1_replies` covers all three
    lawful branches, so a schema-lawful FACT reply now reaches the finalizer
    through the item/default/menu/source-locator path, and the nonempty
    `continuity_hints` branch is exercised by the SAME existing control rather
    than a duplicate of it.
    """
    fix = _a5_run(tmp_path)
    plan = fix["plan"]
    bodies = [json.loads(fix["replies"][pk["prompt_sha256"]])
              for pk in plan["packets"]]
    assert any(b["facts"] for b in bodies), "no lawful FACT reply was served"
    assert any(b["continuity_hints"] for b in bodies), \
        "the nonempty continuity_hints branch was never served"
    assert any(b["abstentions"] for b in bodies)

    n_calls = _planned_calls(plan)
    assert n_calls == len(fix["prep"]["allowed"]) == 392, n_calls
    out = TG._finalize(fix)
    assert out["audit_problems"] == [], out["audit_problems"][:5]
    assert out["ledger"]["scheduled"] == n_calls, out["ledger"]
    assert out["ledger"]["missing"] == 0, out["ledger"]
    assert out["ledger"].get("primary_valid") == n_calls, out["ledger"]
    assert len(out["validity"]) == n_calls
    assert all(v for _k, v in out["validity"]), "a served answer was not valid"
    assert out["retry"] == [], "a clean primary armed a retry"
    assert out["records"] == n_calls
    assert _raw_rows(fix["run_dir"]) == n_calls


@TG._needs_node
def test_a5_route_binds_its_own_plan_and_not_the_kfields_one(tmp_path):
    """The run is audited against the plan IT persisted, not A1's committed one."""
    work = TG._mirror(tmp_path)
    run_dir = tmp_path / "a5run"
    prep = _a5_prepare_in(work, run_dir)
    assert prep["ok"], prep["problems"][:3]
    plan = _a5_plan_of(run_dir)
    mpath, prefix = RT.a1_plan_identity(plan)
    assert os.path.dirname(mpath) == os.path.join(str(run_dir), RT.PLAN_DIRNAME)
    assert prefix == A5.LAUNCHER_PREFIX
    assert plan is not RT.a1_plan()
    assert plan["door"] == RT.A1_DOOR
    for inv in prep["invocations"]:
        assert os.path.basename(inv["scriptPath"]).startswith(prefix)


# --------------------------- item 3: exactly one child, and never a third try
@TG._needs_node
def test_a5_one_invalid_primary_makes_exactly_one_child_that_closes_durably(
        tmp_path):
    """EXACTLY ONE call answers unparseably: every call is still accounted, the
    retry is that one lane and not its sibling, attempt 2 closes on disk, and
    attempt 3 is refused.

    The previous version corrupted by prompt_sha256 and so hit BOTH lanes of the
    packet; asserting only the packet id let it pass on 2 invalid calls and 2
    retries (Codex SEQ 1407 item 1). Every count below is now per-LANE.
    """
    fix = _a5_run(tmp_path)
    plan = fix["plan"]
    n_calls = _planned_calls(plan)
    assert n_calls == len(fix["prep"]["allowed"]) == 392, n_calls
    packet = plan["packets"][0]
    pid = packet["packet_id"]
    lanes = [l["lane_id"] for l in packet["lanes"]]
    assert len(lanes) == len(plan["arms"]) == 2, lanes
    target, sibling = (pid, lanes[0]), (pid, lanes[1])
    _corrupt_one_lane(fix, *target)

    primary = TG._finalize(fix)
    led = primary["ledger"]
    assert primary["audit_problems"] == [], primary["audit_problems"][:5]
    assert led["scheduled"] == n_calls, led
    assert led["missing"] == 0, led
    assert led["primary_invalid"] == 1, led
    assert led["primary_valid"] == n_calls - 1, led
    assert sum(v for k, v in led.items() if k != "scheduled") == n_calls, led

    retry = [tuple(c) for c in primary["retry"]]
    assert retry == [target], retry
    valid = {tuple(k) for k, v in primary["validity"] if v}
    assert sibling in valid, "the OTHER lane of the same packet was not valid"
    assert sibling not in set(retry), "a valid sibling was put in the retry set"
    assert target not in valid

    child = TG._prepare_retry_in(fix["work"], fix["run_dir"])
    assert child["ok"], child.get("problems")
    assert [tuple(c) for c in child["allowed"]] == [target], child["allowed"]

    child_dir = os.path.join(str(fix["run_dir"]), RT.RETRY_DIRNAME)
    child_plan = _a5_plan_of(child_dir)
    assert RT.a1_plan_identity(child_plan)[0] == \
        RT.a1_plan_identity(plan)[0], \
        "the child resolved a different plan than the paid primary"
    assert not os.path.isdir(os.path.join(child_dir, RT.PLAN_DIRNAME)), \
        "the child persisted a second plan copy it could disagree with"

    TG._a1_execute(fix["work"], tmp_path, child, child_plan, fix["projects"],
                   fix["replies"], "a5r", start=10000)
    second = TG._a1_finalize_in(fix["work"], child_dir, fix["projects"])
    assert second.returncode == 0, second.stderr[-2500:]
    fin2 = json.loads(second.stdout)
    assert fin2["audit_problems"] == [], fin2["audit_problems"][:5]
    assert fin2["ledger"]["scheduled"] == 1, fin2["ledger"]
    assert fin2["ledger"]["missing"] == 0, fin2["ledger"]
    assert len(fin2["validity"]) == 1 and all(v for _k, v in fin2["validity"])
    assert os.path.isfile(os.path.join(child_dir, RT.FINALIZATION_NAME)), \
        "attempt 2 wrote no durable closeout"

    assert TG._prepare_retry_in(fix["work"], child_dir)["ok"] is False, \
        "a THIRD retry was armed"


# ------------------- item 4: the two defects this seam actually shipped with
def _bundle_of(run_dir):
    return A5.a5_bundle_path(str(run_dir))


@TG._needs_node
def _bump(path):
    with io.open(path, "a", encoding="utf-8") as fh:
        fh.write(" ")


def _first_unarmed(run_dir):
    d = os.path.join(str(run_dir), RT.PLAN_DIRNAME, A5.LAUNCHER_DIRNAME)
    return os.path.join(d, sorted(os.listdir(d))[0])


@TG._needs_node
@pytest.mark.parametrize("label,break_it", [
    ("the pinned bundle's bytes changed", lambda rd: _bump(_bundle_of(rd))),
    ("the pinned bundle is gone", lambda rd: os.remove(_bundle_of(rd))),
    # same owner as the two above - audit()'s bundle loop - so it is frozen
    # here rather than as a separate full-route copy
    ("a reviewed launcher no longer matches the bundle",
     lambda rd: _bump(_first_unarmed(rd))),
])
def test_a5_a_broken_launcher_bundle_refuses_and_keeps_every_paid_row(
        tmp_path, label, break_it):
    """Both were REAL defects found by mutation in SEQ 1405, in the mechanism
    SEQ 1405 item A had just ordered:

      * drifted bundle bytes were ACCEPTED - the plan pinned `bundle_sha256`
        and nothing ever compared it, so a one-byte change produced a clean
        392-answer finalization.
      * a missing bundle raised FileNotFoundError straight out of audit(). A
        crash is not failing closed: the paid rows were already on disk.

    Rule E, all four halves: refuse, keep every paid raw row, credit zero
    semantic answers, arm zero retries.
    """
    fix = _a5_run(tmp_path, mutate_after=break_it)
    n_calls = _planned_calls(fix["plan"])
    assert n_calls == 392, n_calls
    out = TG._finalize(fix)
    assert out["audit_problems"], "a broken launcher bundle was ACCEPTED"
    assert out["validity"] == [], "a refused run credited a semantic answer"
    assert out["retry"] == [], "a refused run armed a retry"
    assert _raw_rows(fix["run_dir"]) == n_calls, "paid raw rows were lost"

    assert TG._prepare_retry_in(fix["work"], fix["run_dir"])["ok"] is False, \
        "a run that never audited clean armed a retry"


# ---- the REST of the identity mutations, at their lowest PURE owner ---------
# One shared prepared run, then focused contract mutations. Twelve slow
# full-route copies would prove the same class at ~25x the wall clock.
@pytest.fixture(scope="module")
def a5_pure(tmp_path_factory):
    """One prepared A5 run reused by every pure-owner mutation below."""
    tmp_path = tmp_path_factory.mktemp("a5pure")
    work = TG._mirror(tmp_path)
    run_dir = tmp_path / "a5run"
    prep = _a5_prepare_in(work, run_dir)
    assert prep["ok"], prep["problems"][:3]
    with io.open(os.path.join(str(run_dir), "receipt.json"),
                 encoding="utf-8") as fh:
        receipt = json.load(fh)
    return {"run_dir": str(run_dir), "plan": _a5_plan_of(run_dir),
            "receipt": receipt, "prep": prep}


def test_a5_the_lawful_receipt_is_contract_clean(a5_pure):
    """The control every mutation below is measured against."""
    assert RT.a1_run_contract_problems(a5_pure["receipt"],
                                       a5_pure["run_dir"]) == []
    assert BLM.protected_pin_problems(a5_pure["plan"]) == []


@pytest.mark.parametrize("label,mutate", [
    ("the manifest identity is repointed at A1",
     lambda r, p: r.__setitem__("manifest_sha256",
                                RT._sha_file(RT.a1_plan_path()))),
    ("the receipt claims a different run",
     lambda r, p: r.__setitem__("run_id", "someone-elses-run")),
    ("an invocation's saved scriptPath is another source's",
     lambda r, p: r["invocations"][0].__setitem__(
         "scriptPath", r["invocations"][1]["scriptPath"])),
    ("an invocation's saved args are another source's",
     lambda r, p: r["invocations"][0].__setitem__(
         "args", r["invocations"][1]["args"])),
    ("a scheduled call was dropped",
     lambda r, p: r.__setitem__("allowed", r["allowed"][:-1])),
    ("a scheduled call was duplicated",
     lambda r, p: r.__setitem__("allowed", r["allowed"] + r["allowed"][:1])),
])
def test_a5_receipt_identity_mutations_refuse_at_the_contract_owner(
        a5_pure, label, mutate):
    receipt = json.loads(json.dumps(a5_pure["receipt"]))
    mutate(receipt, a5_pure["plan"])
    assert RT.a1_run_contract_problems(receipt, a5_pure["run_dir"]), \
        "the run contract accepted: %s" % label


@pytest.mark.parametrize("name", sorted(BLM._protected_pins()))
def test_a5_every_protected_pin_refuses_when_its_bytes_move(a5_pure, name):
    """The pin owner, not a route copy: one drifted protected file per case."""
    plan = json.loads(json.dumps(a5_pure["plan"]))
    plan["pins"][name] = "0" * 64
    why = BLM.protected_pin_problems(plan)
    assert any(name in w for w in why), (name, why[:3])


def test_a5_a_plan_that_carries_no_pins_refuses(a5_pure):
    """SEQ 1405 defect 1: the A5 plan shipped with NO pins and the finalizer
    refused all 392 rows. The pin owner must say so on its own."""
    plan = json.loads(json.dumps(a5_pure["plan"]))
    plan.pop("pins")
    assert len(BLM.protected_pin_problems(plan)) == len(BLM._protected_pins())


def test_a5_a_drifted_bound_input_refuses_at_the_inventory_owner():
    """A bound source's live bytes must match what the A4 lock sealed."""
    assert A5.inventory_problems() == []
    lock = A5.a4_lock()
    broken = json.loads(json.dumps(lock))
    broken["artifacts"]["provenance"] = "0" * 64
    assert A5.inventory_problems(broken)


# ------------------------------- item 6: the package rebuilds byte-for-byte
def _raw_tree(run_dir):
    """Every generated file, keyed by relative path, hashed from RAW bytes.

    No normalisation and no permitted exceptions: Step 1 A5 requires an exact
    byte-for-byte rebuild, so the comparison must be over the bytes themselves
    (Codex SEQ 1407 item 2).
    """
    import hashlib
    run_dir = str(run_dir)
    out = {}
    for root, _dirs, files in os.walk(run_dir):
        for name in sorted(files):
            path = os.path.join(root, name)
            with io.open(path, "rb") as fh:
                out[os.path.relpath(path, run_dir)] = hashlib.sha256(
                    fh.read()).hexdigest()
    return out


def test_a5_the_whole_package_rebuilds_byte_for_byte_at_the_same_path(tmp_path):
    """Build, snapshot every raw byte, delete ONLY the run directory, rebuild at
    the IDENTICAL path: the complete path set and every byte hash must match.

    Building into two different paths and then excusing the differences proves
    determinism-modulo-an-excuse, not identity. Same path, no excuses.
    """
    work = TG._mirror(tmp_path)
    run = tmp_path / "build"
    assert _a5_prepare_in(work, run)["ok"]
    first = _raw_tree(run)
    plan = _a5_plan_of(run)

    shutil.rmtree(str(run))
    assert not os.path.exists(str(run))
    assert _a5_prepare_in(work, run)["ok"]
    second = _raw_tree(run)

    assert sorted(second) == sorted(first), \
        set(first).symmetric_difference(second)
    differing = sorted(k for k in first if first[k] != second[k])
    assert differing == [], differing
    assert first == second

    # the composition stays DERIVED from the plan, never typed
    n_events = len(plan["events"])
    unarmed = [k for k in first
               if k.startswith("plan/%s/" % A5.LAUNCHER_DIRNAME)]
    armed = [k for k in first if k.startswith("launch/")]
    assert len(unarmed) == len(armed) == n_events, (len(unarmed), len(armed))
    named = set(first) - set(unarmed) - set(armed)
    assert "plan/%s" % A5.BUNDLE_NAME in named, sorted(named)
    assert "plan/%s" % A5.MANIFEST_NAME in named, sorted(named)
    assert "receipt.json" in named, sorted(named)
    assert len(first) == 2 * n_events + len(named), (len(first), n_events)
