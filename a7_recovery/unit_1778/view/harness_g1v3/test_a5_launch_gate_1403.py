"""A5 launch-identity and pre-call-gate proofs. Codex SEQ 1403.

Every negative arms ZERO and has a lawful positive control. No model call.
"""
import io
import json
import os
import shutil
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import build_a5_exp5_kit as A5                                   # noqa: E402
import build_launch_manifest as BLM                              # noqa: E402
import raw_transport as RT                                       # noqa: E402


@pytest.fixture(autouse=True)
def _pinned_env():
    """The gate reads the real environment; pin it for every case."""
    keep = os.environ.get(BLM.OUTPUT_TOKENS_VAR)
    os.environ[BLM.OUTPUT_TOKENS_VAR] = BLM.MAX_OUTPUT_TOKENS_SETTING
    yield
    if keep is None:
        os.environ.pop(BLM.OUTPUT_TOKENS_VAR, None)
    else:
        os.environ[BLM.OUTPUT_TOKENS_VAR] = keep


def _armed(run_dir):
    return os.path.isdir(os.path.join(run_dir, "launch"))


# ------------------------------------ item 1: the receipt binds the A5 plan
def test_lawful_prepare_binds_the_exact_persisted_a5_manifest(tmp_path):
    out = str(tmp_path / "run")
    got = A5.prepare(out)
    assert got["ok"], got["problems"]
    rec = json.load(io.open(os.path.join(out, "receipt.json"),
                            encoding="utf-8"))
    a5m = os.path.join(out, "plan", A5.MANIFEST_NAME)
    assert os.path.isfile(a5m), "the A5 manifest was never persisted"
    assert rec["manifest_sha256"] == A5._sha_text(
        io.open(a5m, encoding="utf-8").read())
    # and it is NOT the K-fields plan
    assert rec["manifest_sha256"] != RT._sha_file(RT.a1_plan_path())
    assert len(got["invocations"]) == 36
    assert len(got["allowed"]) == 392
    for inv in got["invocations"]:
        assert os.path.basename(inv["scriptPath"]).startswith("exp5_a5_")
        armed = io.open(os.path.join(out, "launch",
                                     os.path.basename(inv["scriptPath"])),
                        encoding="utf-8").read()
        assert "const RECEIPT = null" not in armed


def test_a_swapped_a5_manifest_arms_zero(tmp_path, monkeypatch):
    """Codex SEQ 1404 item 4: this used to say 'arms zero' and then permit
    got["ok"]. It now asserts the refusal for real."""
    out = str(tmp_path / "swap")
    # the swap that matters is the A1 plan's CONTENT standing in for A5's,
    # not merely its file name.
    monkeypatch.setattr(A5, "plan", lambda: dict(RT.a1_plan()))
    got = A5.prepare(out)
    assert got["ok"] is False, "the A1 plan armed the A5 run"
    assert not _armed(out), "a callable file appeared despite the swap"


def test_a_drifted_a5_manifest_arms_zero(tmp_path, monkeypatch):
    """Mutating the persisted plan bytes after they are written must refuse."""
    real = A5.plan

    def _drifted():
        doc = real()
        doc["n_packets"] = 999
        return doc

    monkeypatch.setattr(A5, "plan", _drifted)
    out = str(tmp_path / "drift")
    got = A5.prepare(out)
    # UNCONDITIONAL (Codex SEQ 1405 item 5). The old `if got["ok"]:` let the
    # whole assertion be skipped by the very outcome it was written to catch.
    assert got["ok"] is False, "a plan contradicting its own derivation armed"
    assert not _armed(out), "a callable file appeared despite the drift"


# ------------------------------------------ item 2: the pre-call gate runs
def test_a_missing_output_token_setting_arms_zero(tmp_path):
    out = str(tmp_path / "notok")
    keep = os.environ.pop(BLM.OUTPUT_TOKENS_VAR, None)
    try:
        got = A5.prepare(out)
        assert got["ok"] is False
        assert any(BLM.OUTPUT_TOKENS_VAR in p for p in got["problems"])
        assert not _armed(out), "a callable file appeared despite the gate"
    finally:
        if keep is not None:
            os.environ[BLM.OUTPUT_TOKENS_VAR] = keep
    assert A5.prepare(str(tmp_path / "ok"))["ok"]         # positive control


def test_a_wrong_output_token_setting_arms_zero(tmp_path):
    out = str(tmp_path / "wrongtok")
    keep = os.environ.get(BLM.OUTPUT_TOKENS_VAR)
    try:
        os.environ[BLM.OUTPUT_TOKENS_VAR] = "64000"
        got = A5.prepare(out)
        assert got["ok"] is False and not _armed(out)
    finally:
        os.environ[BLM.OUTPUT_TOKENS_VAR] = keep


# ------------------------------- item 3: frozen SOURCE bytes are enforced
def test_frozen_source_byte_drift_arms_zero(tmp_path):
    ev = [e for e in BLM._events() if e["source_id"].startswith("AAL")][0]
    src = os.path.join(BLM._REPO, ev["input_path"])
    orig = io.open(src, "rb").read()
    out = str(tmp_path / "srcdrift")
    try:
        doc = json.loads(orig.decode("utf-8"))
        doc["ticker"] = "MUTATED"
        io.open(src, "w", encoding="utf-8").write(json.dumps(doc, indent=1))
        got = A5.prepare(out)
        assert got["ok"] is False, "changed source bytes armed a run"
        assert not _armed(out)
        assert any("source file" in p or "manifest hash" in p
                   for p in got["problems"]), got["problems"][:2]
    finally:
        io.open(src, "wb").write(orig)
    assert A5.prepare(str(tmp_path / "srcok"))["ok"]      # positive control


# --------------------------------- item 4: the two owners no longer drift
def test_the_matcher_the_scorer_imports_is_bound():
    b = A5.plan()["bound_inputs"]
    assert len(b["matcher_sha256"]) == 64
    live = A5._sha_text(io.open(os.path.join(
        BLM._REPO, "driver", "core", "fact_match.py"), encoding="utf-8").read())
    assert b["matcher_sha256"] == live
    assert "fact_match" in io.open(
        os.path.join(_HERE, "scorers", "score_exp5.py"),
        encoding="utf-8").read()


def test_the_active_rows_are_derived_and_cannot_be_invented():
    rows = A5.active_arms()
    assert [r["arm"] for r in rows] == list(A5.ACTIVE_ARM_IDS)
    kit = {a["arm"]: a for a in A5.frozen_kit()["arms"]}
    for r in rows:                       # every value comes from the kit
        for k in ("role", "tier", "effort"):
            assert r[k] == kit[r["arm"]][k], k
    # the manifest and the lane map cannot disagree, because both read this
    doc = A5.plan()
    assert [a["role"] for a in doc["arms"]] == [r["role"] for r in rows]
    assert [v["role"] for v in A5.arm_of_lane().values()] == \
        [r["role"] for r in rows]


def test_an_unknown_active_arm_id_refuses(monkeypatch):
    monkeypatch.setattr(A5, "ACTIVE_ARM_IDS", ("P1", "P9"))
    with pytest.raises(ValueError):
        A5.active_arms()


# -------------------------------------------------- the fresh-directory rule
def test_a_second_prepare_into_the_same_directory_arms_zero(tmp_path):
    out = str(tmp_path / "twice")
    assert A5.prepare(out)["ok"]
    again = A5.prepare(out)
    assert again["ok"] is False
    assert "not fresh" in again["problems"][0]
