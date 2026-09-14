# -*- coding: utf-8 -*-
"""CLOSEOUT INTEGRITY (Codex SEQ 1482). Three owners, test first, zero calls.

1. THE AUDITOR'S PROMPT PINS. `audit_worker_access.audit` resolved the run's
   own plan for its manifest and bundle (SEQ 1405 B) but rendered its prompt
   pins from the DEFAULT door. Every earlier run happened to use the default
   prompts, so the defect was invisible until the first private-plan run: all
   18 of its completed calls audited `integrity_refusal` although every
   transcript carried exactly the bytes the plan pinned.

   The fake official run had the SAME defect in its fixture: the transcript
   it fabricated carried the default render, not the bytes the launcher sent,
   so the fixture and the auditor agreed by accident. The first test here
   makes the fixture faithful; only then can the auditor be proved.

2. A PUBLISHED FINALIZATION IS IMMUTABLE. `finalization.json` was written by
   atomic REPLACEMENT, so a second closeout - whose raw preservation refuses
   because the paid files already exist - overwrote a clean record with a
   refused one. The existing write-once primitive closes that.

3. THE LEDGER COUNTS REAL CALLS. A refused partial run spent its completed
   calls whether or not it is selectable for scoring. The one ledger owner
   counted a run only when its finalization audited clean, and counted it
   from its SCHEDULE - so the stopped run contributed nothing, and a partial
   run would have contributed its whole schedule. Calls are now the rows the
   official state returned, bound to the preserved raw tree.

Nothing here types a call count, hashes into prose, or touches the stopped
run; mutations are applied to copies and to the test's own fake runs.
"""
import hashlib
import inspect
import io
import json
import os
import shutil
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import a6_launch_freeze as A6                                    # noqa: E402
import a7_g1_build as G                                          # noqa: E402
import a7_prepared_run as PR                                     # noqa: E402
import audit_worker_access as AUD                                # noqa: E402
import build_kfields_final as F                                  # noqa: E402
import raw_transport as RT                                       # noqa: E402
import test_a5_route_1406 as A5R                                 # noqa: E402
import test_a7_runstates_1470 as RS                              # noqa: E402
import test_harness_guards as TG                                 # noqa: E402

#: the stopped, refused, never-again-finalized producer run. Read only.
REFUSED_RUN = "/tmp/a7_v3_prepared_run_1479"
_needs_refused = pytest.mark.skipif(
    not os.path.isfile(os.path.join(REFUSED_RUN, "finalization.json")),
    reason="the refused producer run is absent")


def _sha_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _env(work):
    return dict(os.environ, CLAUDE_CODE_MAX_OUTPUT_TOKENS="128000",
                PYTHONPATH=str(work.parent.parent.parent.parent.parent)
                + os.pathsep + TG._REPO, PYTHONDONTWRITEBYTECODE="1")


def _audit_in(fix, pre=""):
    """The auditor, run inside the mirror against the fake projects root.

    `pre` runs before the audit and may only rebind the run's plan resolver:
    that is how a role or era mutation reaches the auditor without editing a
    receipt-bound plan file.
    """
    code = ("import json,sys;sys.path.insert(0,%r);"
            "import audit_worker_access as A;A.PROJECTS_ROOT=%r;"
            "import raw_transport as RT;%s"
            "o=A.audit(%r);"
            "print(json.dumps({'problems':o['problems'],"
            "'outcomes':[[list(k),x,y] for k,x,y in o['outcomes']]}))"
            % (str(fix["work"]), str(fix["projects"]), pre,
               os.path.join(str(fix["run_dir"]), "receipt.json")))
    return subprocess.run([sys.executable, "-B", "-c", code],
                          cwd=str(fix["work"]), capture_output=True,
                          text=True, env=_env(fix["work"]))


def _outcomes(got):
    assert got.returncode == 0, got.stderr[-2500:]
    doc = json.loads(got.stdout)
    return doc["problems"], {tuple(k): (o, why) for k, o, why in doc["outcomes"]}


def _states(fix):
    wf = os.path.join(str(fix["projects"]), "proj", "sess", "workflows")
    for name in sorted(os.listdir(wf)):
        with io.open(os.path.join(wf, name), encoding="utf-8") as fh:
            yield json.load(fh)


def _transcript_path(fix, state, agent_id):
    return os.path.join(str(fix["projects"]), "proj", "sess", "subagents",
                        "workflows", state["runId"], "agent-%s.jsonl" % agent_id)


def _transcript_prompt_hashes(fix):
    """{lane_id: sha256 of the prompt STRING the child transcript records}."""
    out = {}
    for st in _states(fix):
        for pr in st["workflowProgress"]:
            if pr.get("type") != "workflow_agent":
                continue
            with io.open(_transcript_path(fix, st, pr["agentId"]),
                         encoding="utf-8") as fh:
                first = json.loads(fh.readline())
            out[pr["label"]] = _sha_text(first["message"]["content"])
    return out


def _launcher_prompt_hashes(fix):
    """{lane_id: prompt_sha256 the LAUNCHER recorded in its result row}."""
    out = {}
    for st in _states(fix):
        for row in st["result"]["results"]:
            out[row["lane_id"]] = row["prompt_sha256"]
    return out


def _planned(plan):
    return {(pk["packet_id"], l["lane_id"])
            for pk in plan["packets"] for l in pk["lanes"]}


# =============================================== 1. the auditor's prompt pins
@TG._needs_node
def test_the_fake_official_transcript_carries_the_bytes_the_launcher_sent(
        tmp_path):
    """THE FIXTURE, FIRST. A transcript fabricated from the default render is
    not evidence about a private-plan run: the auditor and the fixture agreed
    on the wrong bytes. The launcher's own recorded prompt hash is the
    independent leg - it was computed by the fake runtime on the bytes the
    launcher actually passed to `agent()`."""
    fix = A5R._a5_run(tmp_path)
    launched = _launcher_prompt_hashes(fix)
    recorded = _transcript_prompt_hashes(fix)
    assert set(launched) == set(recorded) and launched, sorted(launched)[:3]
    wrong = sorted(l for l in launched if launched[l] != recorded[l])
    assert wrong == [], ("the fake transcript does not carry the bytes the "
                         "launcher sent for %d lane(s): %s"
                         % (len(wrong), wrong[:3]))
    # and those bytes are the plan's own pins, every packet
    pins = {pk["prompt_sha256"] for pk in fix["plan"]["packets"]}
    assert set(launched.values()) == pins


@TG._needs_node
def test_a_private_plan_transcript_equal_to_its_plan_render_is_served(
        tmp_path):
    """THE DEFECT. The plan pins prompts the default door does NOT render;
    a transcript equal to the plan's pin must audit `served`."""
    fix = A5R._a5_run(tmp_path)
    plan = fix["plan"]
    default = TG._mirror_prompts(fix["work"], tmp_path)        # the default door
    first = plan["packets"][0]
    assert _sha_text(default[first["packet_id"]]) != first["prompt_sha256"], \
        "this plan does not differ from the default door; the proof is vacuous"
    problems, outcomes = _outcomes(_audit_in(fix))
    assert problems == [], problems[:5]
    assert set(outcomes) == _planned(plan)
    not_served = {k: v for k, v in outcomes.items() if v[0] != "served"}
    assert not_served == {}, list(not_served.items())[:3]


@TG._needs_node
def test_the_default_kfields_run_still_audits_clean(tmp_path):
    """THE LAWFUL DEFAULT CONTROL: a run with no private plan is unchanged."""
    fix = TG._a1_official_run(tmp_path)
    problems, outcomes = _outcomes(_audit_in(fix))
    assert problems == [], problems[:5]
    assert outcomes and all(v[0] == "served" for v in outcomes.values()), \
        [(k, v) for k, v in outcomes.items() if v[0] != "served"][:3]


@TG._needs_node
def test_one_changed_prompt_byte_in_one_transcript_REFUSES_that_call_only(
        tmp_path):
    fix = A5R._a5_run(tmp_path)
    st = next(_states(fix))
    pr = [p for p in st["workflowProgress"]
          if p.get("type") == "workflow_agent"][0]
    path = _transcript_path(fix, st, pr["agentId"])
    with io.open(path, encoding="utf-8") as fh:
        recs = [json.loads(l) for l in fh if l.strip()]
    recs[0]["message"]["content"] += " "
    with io.open(path, "w", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")
    problems, outcomes = _outcomes(_audit_in(fix))
    lanes = {(k[1]): v for k, v in outcomes.items()}
    assert lanes[pr["label"]][0] == "integrity_refusal", lanes[pr["label"]]
    assert any("pinned bytes" in p for p in problems), problems[:3]
    others = {l: v for l, v in lanes.items() if l != pr["label"]}
    assert others and all(v[0] == "served" for v in others.values())


@TG._needs_node
@pytest.mark.parametrize("label,field,value", [
    ("another role", "prompt_role", "producer"),
    ("another contract era", "contract_suffix", ""),
    ("a role no contract declares", "prompt_role", "nobody"),
])
def test_a_plan_whose_role_or_era_moves_REFUSES_every_call(tmp_path, label,
                                                          field, value):
    """The pins come from the RUN-RESOLVED plan. A plan naming a different
    role or era renders different bytes - or nothing - and every transcript
    stops matching. A role the contract does not declare must be a structured
    refusal, never a crash out of the closeout."""
    fix = A5R._a5_run(tmp_path)
    pre = ("_real=RT.a1_plan_for_run;"
           "RT.a1_plan_for_run=lambda d,_r=_real:dict(_r(d),%s=%r);"
           % (field, value))
    problems, outcomes = _outcomes(_audit_in(fix, pre))
    assert problems, label
    served = [k for k, v in outcomes.items() if v[0] == "served"]
    assert served == [], (label, served[:3])
    assert set(outcomes) == _planned(fix["plan"]), label


def test_the_auditor_takes_no_caller_selected_prompts():
    """No parameter may hand the auditor the pins it is supposed to derive."""
    assert "prompts" not in inspect.signature(AUD.audit).parameters


# ============================================ 2. the finalization is immutable
@TG._needs_node
def test_a_second_finalization_cannot_replace_the_first(tmp_path):
    """A clean closeout, then a second attempt on the same run: the second
    can only refuse - its raw preservation already refuses - and must leave
    the first document and the raw tree byte for byte."""
    fix = TG._a1_public_run(tmp_path)
    first = TG._finalize(fix)
    assert first["audit_problems"] == [], first["audit_problems"][:3]
    fpath = os.path.join(str(fix["run_dir"]), RT.FINALIZATION_NAME)
    sha_before = RT._sha_file(fpath)
    raw_before = F.raw_tree(str(fix["run_dir"]))
    assert raw_before["files"] == len(first["classification"])

    again = TG._a1_finalize_in(fix["work"], fix["run_dir"], fix["projects"])
    assert again.returncode != 0, "a second finalization must not succeed"
    assert "never overwritten" in again.stderr, again.stderr[-600:]
    assert RT._sha_file(fpath) == sha_before, "the first bytes were replaced"
    assert F.raw_tree(str(fix["run_dir"])) == raw_before
    leftovers = [n for n in os.listdir(str(fix["run_dir"]))
                 if ".partial" in n or n.endswith(".tmp")]
    assert leftovers == [], leftovers


# ================================== 3. the ledger counts a refused run's calls
def _row_for(rows, run_dir):
    want = os.path.abspath(run_dir)
    return [r for r in rows if os.path.abspath(r.get("run_dir") or "") == want]


@_needs_refused
def test_the_refused_run_is_counted_once_from_its_bound_raw_tree():
    """A refused-but-paid run's spend is counted once when the run is SUPPLIED,
    never from the baseline (no producer history lives there now, Codex SEQ
    1516). No typed count: the row's calls are the preserved raw files, which
    are the rows the official state returned - measured here from both."""
    base, _b = A6.ledger()
    total, rows = A6.ledger(REFUSED_RUN)
    mine = _row_for(rows, REFUSED_RUN)
    assert len(mine) == 1, [r["stage"] for r in rows]
    raw = F.raw_tree(REFUSED_RUN)
    with io.open(os.path.join(REFUSED_RUN, "receipt.json"),
                 encoding="utf-8") as fh:
        receipt = json.load(fh)
    returned = len(RT.a1_readable_rows(receipt["states"]))
    assert raw["files"] == returned > 0
    assert mine[0]["calls"] == raw["files"]
    assert mine[0]["raw_tree"] == raw["sha256"]
    assert total == base + mine[0]["calls"]
    assert total == sum(r["calls"] for r in rows)
    # a pure read: supplying the same run again gives the same total and rows
    again, rows_again = A6.ledger(REFUSED_RUN)
    assert again == total and len(rows_again) == len(rows)
    assert len(_row_for(rows_again, REFUSED_RUN)) == 1


@_needs_refused
def test_the_refused_run_stays_unselectable_for_scoring():
    with pytest.raises(ValueError) as exc:
        PR.load(REFUSED_RUN)
    assert "does not hold" in str(exc.value)


def test_a_supplied_current_run_adds_only_itself(tmp_path):
    """With no producer history in the baseline, supplying ONE run adds that
    run's attempts and reaches no other run - the refused run and the graded
    primary are not counted unless they are themselves supplied (Codex SEQ
    1516)."""
    base, _b = A6.ledger()
    other = RS._lawful_zero_retry(tmp_path, "other")
    total, rows_other = A6.ledger(other)
    assert not _row_for(rows_other, REFUSED_RUN)          # not reached
    assert not _row_for(rows_other, G.PRIMARY)            # not reached
    added = [r for r in rows_other if r["stage"].startswith("current_producer")]
    assert [r["stage"] for r in added] == ["current_producer_primary"], added
    assert added[0]["calls"] == F.raw_tree(other)["files"]
    assert total == base + added[0]["calls"]


def test_calls_are_the_returned_rows_bound_to_the_raw_tree_not_the_schedule(
        tmp_path):
    """A run whose preserved raw tree no longer matches the rows its official
    state returned is not counted at all - it is refused by name. The
    schedule never enters the count."""
    run = RS._lawful_zero_retry(tmp_path, "rawbound")
    total, rows = A6.ledger(run)
    mine = _row_for(rows, run)
    assert mine and mine[0]["calls"] == F.raw_tree(run)["files"]
    victim = sorted(os.listdir(os.path.join(run, "raw")))[0]
    os.unlink(os.path.join(run, "raw", victim))
    with pytest.raises(ValueError) as exc:
        A6.ledger(run)
    assert "raw" in str(exc.value), str(exc.value)[:160]


@_needs_refused
def test_a_refused_but_bound_closeout_counts_and_a_malformed_one_REFUSES(
        tmp_path, monkeypatch):
    """The audit refusal alone does not hide a run's spend; every other
    binding still must hold."""
    monkeypatch.setattr(RS, "REAL", REFUSED_RUN)
    copy = RS._copy(tmp_path, "refusedcopy")
    base, _rows = A6.ledger()
    total, rows = A6.ledger(copy)
    mine = _row_for(rows, copy)
    assert len(mine) == 1 and mine[0]["calls"] == F.raw_tree(copy)["files"]
    assert total == base + mine[0]["calls"]
    fin_path = os.path.join(copy, RT.FINALIZATION_NAME)
    with io.open(fin_path, encoding="utf-8") as fh:
        fin = json.load(fh)
    fin["ledger"]["scheduled"] += 1              # a ledger no owner recomputed
    with io.open(fin_path, "w", encoding="utf-8") as fh:
        json.dump(fin, fh)
    with pytest.raises(ValueError) as exc:
        A6.ledger(copy)
    assert "does not hold" in str(exc.value), str(exc.value)[:160]


def test_the_history_owner_lists_the_refused_run_as_data_only():
    """The path is data in the one history owner; nothing else names it."""
    assert REFUSED_RUN in G.PRODUCER_HISTORY
    assert G.PRIMARY in G.PRODUCER_HISTORY
    with io.open(os.path.join(_HERE, "a6_launch_freeze.py"),
                 encoding="utf-8") as fh:
        assert os.path.basename(REFUSED_RUN) not in fh.read()
