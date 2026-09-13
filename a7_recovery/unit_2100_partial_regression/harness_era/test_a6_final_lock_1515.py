# -*- coding: utf-8 -*-
"""A6 freezes the EXP-5 launch against the SIGNED FINAL A4 lock (Codex SEQ 1515).
Zero model/grader calls. A fresh corrected A5 run is prepared, frozen, and every
binding, count, budget and zero is proved; one-field mutations refuse; the freeze
double-builds byte-identically. The closed A4 baseline is the final lock's own
call_accounting.ledger_after (A4 is not re-walked)."""
import copy, io, json, os, sys, tempfile
import pytest
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import a6_launch_freeze as A6                                    # noqa: E402
import build_a5_exp5_kit as A5                                   # noqa: E402
import build_kfields_final as F                                  # noqa: E402
FINAL_LOCK_SHA = "63018354e6b26a8061a114934df15fe035b44fe031dcf00768b440983d43b8a0"
CORR_SHA = "1440d75131c0c7418a66821778a88d5c1ff8fd9bdf7f4cca4d561b596c1b3066"


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    os.environ["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = "128000"
    d = str(tmp_path_factory.mktemp("a6run"))
    for n in os.listdir(d):
        os.remove(os.path.join(d, n))
    os.rmdir(d)
    got = A5.prepare(d)
    assert got["ok"], got["problems"]
    return d


@pytest.fixture(scope="module")
def doc(run):
    return A6.freeze(run)


def test_the_closed_a4_baseline_is_the_final_lock_ledger_after():
    total, rows = A6.ledger()
    assert total == 5220 and len(rows) == 1                        # the whole closed A4 total, from the lock alone
    assert rows[0]["stage"] == "a4_final_key" and rows[0]["calls"] == 5220
    assert rows[0]["receipt_sha256"] == FINAL_LOCK_SHA and rows[0]["finalization_sha256"] == A5.A4_LOCK_RECEIPT_SHA
    lr = A6._locked_rows()
    assert len(lr) == 1 and lr[0][2] == 5220


def test_the_freeze_binds_the_final_lock_and_the_corrected_a5_candidate(doc):
    a = doc["a4_lock"]
    assert a["sha256"] == FINAL_LOCK_SHA and a["receipt_sha256"] == A5.A4_LOCK_RECEIPT_SHA
    assert a["schema"] == "a4-final-key-lock/1511" and a["state"] == "LOCKED" and a["signed"] is True and a["events"] == 36 and a["ledger_after"] == 5220
    b = doc["bound_artifacts"]
    assert b["inventory_sha256"] == CORR_SHA                       # the CORRECTED inventory the key was built over
    assert len(b["prompt_sha256"]) == 196 and len(b["launchers"]) == 36 and len(b["input_sha256"]) == 36
    for row in b["launchers"]:
        assert len(row["armed_sha256"]) == 64 and len(row["unarmed_sha256"]) == 64
    assert b["manifest_sha256"] and b["bundle_sha256"] and b["menu_backmap_sha256"] and b["reader_sha256"] and b["matcher_sha256"]


def test_counts_transport_arms_and_budget(doc):
    c = doc["counts"]
    assert c["events"] == 36 and c["packets"] == 196 and c["arms"] == ["P1", "P2"] and c["lanes_per_packet"] == [2]
    assert c["ordered_producer_calls"] == c["unique_ordered_calls"] == 392 == c["packets"] * len(c["arms"])
    assert c["invocations"] == 36
    t = doc["transport"]
    assert t["runtime_model_id"] == "claude-sonnet-5" and t["effort"] == "high" and t["agentType"] == "lean-probe"
    assert t["disallowedTools"] == ["Read"] and t["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] == "128000" and "subscription" in t["transport"]
    assert set(doc["absent_arms"]) == set(A6.FORBIDDEN_ARMS) and not any(doc["absent_arms"].values())
    bud = doc["budget"]
    assert bud["completed_actual"] == 5220 and bud["planned_producer_primary"] == 392
    assert bud["producer_primary_after"] == 5612 and bud["global_abort_ceiling"] == F.GLOBAL_CEILING == 6000 and bud["under_ceiling"] is True


def test_zero_spend_and_zero_armed_grader(doc):
    z = doc["zeros"]
    assert z == {"states": 0, "raw_replies": 0, "made_calls": 0, "database_writes": 0, "activated": False}
    g = doc["grader"]
    assert g["armed_grader_calls"] == 0 and g["count_is_derivable_now"] is False
    assert [s["stage"] for s in g["stages"]] == ["G1_identity", "reconcile", "G2_meaning", "G3_extras"]
    assert g["a7_boundary"]["ceiling"] == 6000


def test_the_freeze_builds_twice_to_identical_bytes(run, tmp_path):
    a = A6.write(run, str(tmp_path / "one")); b = A6.write(run, str(tmp_path / "two"))
    assert a[1] == b[1]
    assert io.open(a[0], encoding="utf-8").read() == io.open(b[0], encoding="utf-8").read()
    assert json.loads(io.open(a[0], encoding="utf-8").read()) == A6.freeze(run)


def test_the_lawful_freeze_has_no_problems(doc):
    assert A6.problems(doc) == []


@pytest.mark.parametrize("path,value", [
    (["a4_lock", "sha256"], "0" * 64),
    (["a4_lock", "state"], "OPEN"),
    (["bound_artifacts", "inventory_sha256"], "0" * 64),
    (["bound_artifacts", "manifest_sha256"], "0" * 64),
    (["counts", "ordered_producer_calls"], 999),
    (["budget", "producer_primary_after"], 1),
    (["transport", "runtime_model_id"], "opus"),
])
def test_one_mutated_field_refuses(doc, path, value):
    assert A6.problems(doc) == []                                  # the control passes before the mutation
    m = copy.deepcopy(doc); node = m
    for k in path[:-1]:
        node = node[k]
    node[path[-1]] = value
    assert A6.problems(m), path


def test_a_mutated_final_lock_refuses_the_closed_read(monkeypatch):
    real = A5.a4_lock()
    bad = copy.deepcopy(real); bad["signer"]["signed"] = False
    monkeypatch.setattr(A5, "a4_lock", lambda: (_ for _ in ()).throw(ValueError("unsigned")))
    with pytest.raises(ValueError):
        A6._locked_rows()
