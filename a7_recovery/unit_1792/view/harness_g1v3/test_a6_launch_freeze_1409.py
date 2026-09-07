# -*- coding: utf-8 -*-
"""A6 launch-freeze proofs (Codex SEQ 1408/1409, repointed at SEQ 1515).
No model/grader call, no launcher execution. The freeze is built from a FRESH
corrected A5 run bound to the signed final A4 lock; the lawful control passes
and every one-field mutation refuses; the freeze double-builds byte-identically.
"""
import copy, io, json, os, sys
import pytest
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import a6_launch_freeze as A6                                    # noqa: E402
import build_a5_exp5_kit as A5                                   # noqa: E402
import build_kfields_final as F                                  # noqa: E402


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    os.environ["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = "128000"
    d = str(tmp_path_factory.mktemp("a6freeze"))
    os.rmdir(d)
    got = A5.prepare(d)
    assert got["ok"], got["problems"]
    return d


@pytest.fixture(scope="module")
def doc(run):
    return A6.freeze(run)


def test_the_lawful_freeze_has_no_problems(doc):
    assert A6.problems(doc) == []


def test_the_freeze_records_the_derived_budget_with_provenance(doc):
    b = doc["budget"]
    assert b["completed_actual"] == 5220 == sum(r["calls"] for r in b["provenance"])
    assert b["planned_producer_primary"] == doc["counts"]["ordered_producer_calls"] == 392
    assert b["producer_primary_after"] == b["completed_actual"] + b["planned_producer_primary"] == 5612
    assert b["global_abort_ceiling"] == F.GLOBAL_CEILING == 6000 and b["under_ceiling"] is True


def test_the_counts_are_derived_and_consistent(doc):
    c = doc["counts"]
    assert c["events"] == 36 and c["packets"] == 196 and c["arms"] == ["P1", "P2"] and c["lanes_per_packet"] == [2]
    assert c["ordered_producer_calls"] == c["unique_ordered_calls"] == 392 == c["packets"] * len(c["arms"])
    assert c["invocations"] == 36 == len(doc["bound_artifacts"]["launchers"])


def test_the_transport_identity_is_the_frozen_one(doc):
    t = doc["transport"]
    assert t["runtime_model_id"] == "claude-sonnet-5" and t["effort"] == "high" and t["agentType"] == "lean-probe"
    assert t["disallowedTools"] == ["Read"] and t["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] == "128000" and "subscription" in t["transport"]


def test_every_forbidden_arm_is_recorded_absent(doc):
    assert set(doc["absent_arms"]) == set(A6.FORBIDDEN_ARMS) and not any(doc["absent_arms"].values())


def test_a_fresh_launch_has_spent_nothing(doc):
    assert doc["zeros"] == {"states": 0, "raw_replies": 0, "made_calls": 0, "database_writes": 0, "activated": False}


def test_arms_zero_grader_calls_and_names_its_a7_owner(doc):
    g = doc["grader"]
    assert g["armed_grader_calls"] == 0 and g["count_is_derivable_now"] is False
    assert [s["stage"] for s in g["stages"]] == ["G1_identity", "reconcile", "G2_meaning", "G3_extras"]
    assert g["a7_boundary"]["batch_owner"] == "grade_batch.js" and g["a7_boundary"]["ceiling"] == 6000
    assert "union" in g["inventory"] and "NOT reducible" in g["inventory"]


def test_the_freeze_builds_twice_to_identical_bytes(run, tmp_path):
    first = A6.write(run, str(tmp_path / "one")); second = A6.write(run, str(tmp_path / "two"))
    assert first[1] == second[1]
    assert io.open(first[0], encoding="utf-8").read() == io.open(second[0], encoding="utf-8").read()
    assert json.loads(io.open(first[0], encoding="utf-8").read()) == A6.freeze(run)


def _set(path, value):
    def go(d):
        node = d
        for k in path[:-1]:
            node = node[k]
        node[path[-1]] = value
    return go


MUTATIONS = [
    ("the A4 lock sha", _set(["a4_lock", "sha256"], "0" * 64)),
    ("the A4 lock state", _set(["a4_lock", "state"], "OPEN")),
    ("the A4 lock ledger_after", _set(["a4_lock", "ledger_after"], 1)),
    ("the corrected inventory sha", _set(["bound_artifacts", "inventory_sha256"], "0" * 64)),
    ("the manifest sha", _set(["bound_artifacts", "manifest_sha256"], "0" * 64)),
    ("the bundle sha", _set(["bound_artifacts", "bundle_sha256"], "0" * 64)),
    ("the ordered call count", _set(["counts", "ordered_producer_calls"], 999)),
    ("the producer-after total", _set(["budget", "producer_primary_after"], 1)),
    ("the runtime id", _set(["transport", "runtime_model_id"], "opus")),
    ("a forbidden arm present", _set(["absent_arms", "opus"], True)),
    ("a nonzero made_calls", _set(["zeros", "made_calls"], 1)),
]


@pytest.mark.parametrize("label,mutate", MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_one_mutated_field_refuses(doc, label, mutate):
    assert A6.problems(doc) == []
    m = copy.deepcopy(doc); mutate(m)
    assert A6.problems(m), label


def test_a_freeze_naming_no_run_refuses(doc):
    m = copy.deepcopy(doc); m["prepared_run"] = "/tmp/does_not_exist_a6"
    assert A6.problems(m)
