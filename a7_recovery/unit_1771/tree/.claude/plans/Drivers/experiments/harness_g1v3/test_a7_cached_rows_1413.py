"""The runtime's resume-cached progress row. Codex SEQ 1413.

`resumeFromRunId` returns an already-completed agent in ONE exact shape: it
carries `cached: true` and the model ALIAS, and the runtime omits the
progress-row `agentType`, `attempt` and `toolCalls` it writes on a fresh spawn.
The auditor treated the omitted `toolCalls` as a tool violation and skipped
every transcript check, so 88 real paid replies were refused.

This freezes that ONE branch. Everything else stays strict: the cached row is
accepted only on its exact key set, the planned alias, and a matching agent
meta file - and it then goes through every existing transcript check unchanged.
"""
import copy
import io
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import audit_worker_access as AUD                               # noqa: E402
import test_harness_guards as TG        # the ONE official-run fixture, reused

#: The exact key set the runtime writes for a resumed, already-completed agent.
CACHED_KEYS = ("agentId", "cached", "index", "label", "lastProgressAt",
               "model", "phaseIndex", "phaseTitle", "promptPreview",
               "resultPreview", "startedAt", "state", "type")


def _cached_row(pr, alias):
    """The fresh row rewritten into the runtime's exact cached shape."""
    row = {"cached": True, "model": alias,
           "lastProgressAt": 1787540822073, "startedAt": 1787540822073,
           "phaseIndex": 1, "resultPreview": (pr.get("promptPreview") or "")[:40]}
    for k in ("agentId", "index", "label", "phaseTitle", "promptPreview",
              "state", "type"):
        row[k] = pr[k]
    assert tuple(sorted(row)) == tuple(sorted(CACHED_KEYS)), sorted(row)
    return row


def _meta_path(fix, aid):
    for rid in os.listdir(os.path.join(fix["projects"], "proj", "sess",
                                       "subagents", "workflows")):
        d = os.path.join(fix["projects"], "proj", "sess", "subagents",
                         "workflows", rid)
        if os.path.isfile(os.path.join(d, "agent-%s.jsonl" % aid)):
            return os.path.join(d, "agent-%s.meta.json" % aid)
    raise AssertionError("no transcript dir for %s" % aid)


def _write_meta(fix, aid, obj):
    with io.open(_meta_path(fix, aid), "w", encoding="utf-8") as fh:
        json.dump(obj, fh)


def _lane_of(fix, label):
    for pk in fix["plan"]["packets"]:
        for ln in pk["lanes"]:
            if ln["lane_id"] == label:
                return ln
    raise AssertionError(label)


def _make_cached(fix, meta=None, mutate_row=None, which=0):
    """Turn ONE served row of the lawful run into the cached shape + meta."""
    wf = os.path.join(fix["projects"], "proj", "sess", "workflows")
    name = sorted(os.listdir(wf))[0]
    path = os.path.join(wf, name)
    with io.open(path, encoding="utf-8") as fh:
        state = json.load(fh)
    agents = [p for p in state["workflowProgress"]
              if p.get("type") == "workflow_agent"]
    pr = agents[which]
    lane = _lane_of(fix, pr["label"])
    row = _cached_row(pr, lane["model"])
    if mutate_row is not None:
        mutate_row(row)
    state["workflowProgress"][state["workflowProgress"].index(pr)] = row
    with io.open(path, "w", encoding="utf-8") as fh:
        json.dump(state, fh)
    _write_meta(fix, pr["agentId"],
                {"agentType": lane["agentType"], "spawnDepth": 1,
                 "model": lane["model"]} if meta is None else meta)
    return pr["label"]


# --------------------------------------------- the two lawful controls
@TG._needs_node
def test_a7_a_fresh_row_run_is_unchanged(tmp_path):
    """THE UNCHANGED POSITIVE CONTROL: no cached row anywhere, still clean."""
    out = TG._a1_audit_in(TG._a1_official_run(tmp_path))
    assert out["problems"] == [], out["problems"][:5]
    assert {o for _k, o, _w in out["outcomes"]} == {"served"}


@TG._needs_node
def test_a7_the_exact_cached_row_with_its_meta_is_served(tmp_path):
    """THE FAILING CONTROL (red before the fix): one lawful resumed row.

    Before the correction the auditor called this a tool violation, because the
    runtime omits `toolCalls` on a cached row - and then skipped every
    transcript check for it.
    """
    fix = TG._a1_official_run(tmp_path)
    label = _make_cached(fix)
    out = TG._a1_audit_in(fix)
    assert out["problems"] == [], out["problems"][:5]
    assert {o for _k, o, _w in out["outcomes"]} == {"served"}
    assert any(k[1] == label for k, _o, _w in out["outcomes"])


# --------------------------------------------- one mutation at a time
def _mut(**kw):
    def go(row): row.update(kw)
    return go


def _drop(key):
    def go(row): row.pop(key, None)
    return go


ROW_MUTATIONS = [
    ("cached is absent", _drop("cached")),
    ("cached is false", _mut(cached=False)),
    ("cached is a string", _mut(cached="true")),
    ("an extra field appears", _mut(toolCalls=0)),
    ("a required cached field is dropped", _drop("resultPreview")),
    ("the alias is the runtime id", _mut(model="claude-sonnet-5")),
    ("the alias is another model", _mut(model="opus")),
]


@TG._needs_node
@pytest.mark.parametrize("label,mutate", ROW_MUTATIONS,
                         ids=[m[0] for m in ROW_MUTATIONS])
def test_a7_a_mutated_cached_row_refuses(tmp_path, label, mutate):
    fix = TG._a1_official_run(tmp_path)
    _make_cached(fix, mutate_row=mutate)
    out = TG._a1_audit_in(fix)
    assert out["problems"], "the auditor ACCEPTED: %s" % label


META_MUTATIONS = [
    ("meta is missing", "ABSENT"),
    ("meta is malformed", "MALFORMED"),
    ("meta agentType is wrong", {"agentType": "general-purpose",
                                 "spawnDepth": 1, "model": "sonnet"}),
    ("meta model is wrong", {"agentType": "lean-probe", "spawnDepth": 1,
                             "model": "opus"}),
    ("meta spawnDepth is wrong", {"agentType": "lean-probe", "spawnDepth": 2,
                                  "model": "sonnet"}),
    ("meta has an extra field", {"agentType": "lean-probe", "spawnDepth": 1,
                                 "model": "sonnet", "extra": 1}),
    ("meta is missing a field", {"agentType": "lean-probe", "model": "sonnet"}),
]


@TG._needs_node
@pytest.mark.parametrize("label,meta", META_MUTATIONS,
                         ids=[m[0] for m in META_MUTATIONS])
def test_a7_a_mutated_agent_meta_refuses(tmp_path, label, meta):
    fix = TG._a1_official_run(tmp_path)
    if meta == "ABSENT":
        lab = _make_cached(fix)
        wf = os.path.join(fix["projects"], "proj", "sess", "workflows")
        state = json.load(io.open(os.path.join(wf, sorted(os.listdir(wf))[0])))
        aid = [p["agentId"] for p in state["workflowProgress"]
               if p.get("label") == lab][0]
        os.remove(_meta_path(fix, aid))
    elif meta == "MALFORMED":
        lab = _make_cached(fix)
        wf = os.path.join(fix["projects"], "proj", "sess", "workflows")
        state = json.load(io.open(os.path.join(wf, sorted(os.listdir(wf))[0])))
        aid = [p["agentId"] for p in state["workflowProgress"]
               if p.get("label") == lab][0]
        io.open(_meta_path(fix, aid), "w", encoding="utf-8").write("{not json")
    else:
        _make_cached(fix, meta=meta)
    out = TG._a1_audit_in(fix)
    assert out["problems"], "the auditor ACCEPTED: %s" % label


# ------------------- the cached branch still runs every transcript check
TX_MUTATIONS = [
    ("cached transcript model drift",
     lambda tx, n: tx[1]["message"].__setitem__("model", "claude-opus-5")),
    ("cached transcript effort drift",
     lambda tx, n: tx[1].__setitem__("effort", "low")),
    ("cached transcript prompt drift",
     lambda tx, n: tx[0]["message"].__setitem__("content", "different prompt")),
    ("cached transcript tool use",
     lambda tx, n: tx[1]["message"]["content"].append(
         {"type": "tool_use", "name": "Read"})),
    ("cached transcript result text drift",
     lambda tx, n: tx[1]["message"]["content"][0].__setitem__("text", "{}")),
]


@TG._needs_node
@pytest.mark.parametrize("label,mutate_tx", TX_MUTATIONS,
                         ids=[m[0] for m in TX_MUTATIONS])
def test_a7_cached_branch_still_checks_the_transcript(tmp_path, label,
                                                      mutate_tx):
    """The omitted progress fields are excused; the TRANSCRIPT is not."""
    fix = TG._a1_official_run(tmp_path, None, mutate_tx)
    _make_cached(fix)
    out = TG._a1_audit_in(fix)
    assert out["problems"], "the cached branch skipped a transcript check: %s" % label
