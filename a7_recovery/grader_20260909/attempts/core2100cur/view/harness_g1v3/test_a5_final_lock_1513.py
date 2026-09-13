# -*- coding: utf-8 -*-
"""A5 binds the SIGNED A4 final lock (Codex SEQ 1513 items 1-3, 6-7). Zero calls.

The kit owner reads the final lock, its receipt and the key identity it binds;
the 36 ordered sources derive from that identity; the inventory it checks is the
one the lock's provenance binds; every drift refuses after a lawful control.
"""
import hashlib, io, json, os, shutil, sys
import pytest
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import build_a5_exp5_kit as A5                                   # noqa: E402
import build_launch_manifest as BLM                              # noqa: E402

FINAL_LOCK_SHA = "63018354e6b26a8061a114934df15fe035b44fe031dcf00768b440983d43b8a0"
FINAL_RECEIPT_SHA = "7f1f7bef4d02b9c5501d9ec6d8d5b9eab5e8aab225092878b7280964bd5d44e3"
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()   # noqa: E731


def test_the_kit_binds_the_signed_final_lock_and_its_receipt():
    assert A5.A4_LOCK_SHA == FINAL_LOCK_SHA and A5.A4_LOCK_RECEIPT_SHA == FINAL_RECEIPT_SHA
    assert sha(A5.A4_LOCK_PATH) == FINAL_LOCK_SHA and sha(A5.a4_lock_receipt_path()) == FINAL_RECEIPT_SHA
    lock = A5.a4_lock()
    assert lock["schema"] == "a4-final-key-lock/1511" and lock["state"] == "LOCKED"
    assert lock["signer"]["signed"] is True and lock["signer"]["blocked"] == []
    rec = json.load(io.open(A5.a4_lock_receipt_path(), encoding="utf-8"))
    assert rec["lock_sha256"] == FINAL_LOCK_SHA and rec["every_bound_value_refuses_when_mutated"] is True
    assert not hasattr(A5, "A4_V6_LOCK_SHA")                        # the superseded binding is gone from the active owner


def test_the_36_sources_derive_from_the_bound_key_identity():
    lock = A5.a4_lock()
    ident_path = os.path.join(os.path.dirname(A5.A4_LOCK_PATH), "key_identity.json")
    assert sha(ident_path) == lock["artifacts"]["key_identity"]
    ident = json.load(io.open(ident_path, encoding="utf-8"))
    order = A5.locked_sources(lock)
    assert order == [s["source_id"] for s in ident["key_shards"]] and len(order) == 36 and len(set(order)) == 36
    assert order == [e["source_id"] for e in BLM._events()]
    assert sum(1 for s in ident["key_shards"] if s["composed"]) == 8


def test_the_inventory_check_reads_the_lock_bound_frozen_inventory():
    lock = A5.a4_lock()
    prov_path = os.path.join(os.path.dirname(A5.A4_LOCK_PATH), "provenance.json")
    assert sha(prov_path) == lock["artifacts"]["provenance"]
    prov = json.load(io.open(prov_path, encoding="utf-8"))["provenance"]
    assert A5.inventory_problems(lock) == []
    assert prov["frozen_inventory_sha256"] == sha(BLM.INVENTORY)     # the live packets' inventory is the one the key was proved over
    assert prov["corrected_inventory_sha256"] != prov["frozen_inventory_sha256"]   # the corrected quotes remain a separate, scheduled seam (DEBT-1)


@pytest.mark.parametrize("how", ["lock_sha", "lock_missing", "receipt_sha", "identity_byte", "provenance_byte", "unsigned"])
def test_every_lock_drift_refuses_after_a_lawful_control(how, tmp_path, monkeypatch):
    assert A5.a4_lock()["state"] == "LOCKED" and len(A5.locked_sources()) == 36 and A5.inventory_problems() == []   # control first
    d = str(tmp_path / "lock"); shutil.copytree(os.path.dirname(A5.A4_LOCK_PATH), d)
    monkeypatch.setattr(A5, "A4_LOCK_PATH", os.path.join(d, os.path.basename(A5.A4_LOCK_PATH)))
    if how == "lock_sha":
        monkeypatch.setattr(A5, "A4_LOCK_SHA", "0" * 64)
    elif how == "lock_missing":
        os.remove(A5.A4_LOCK_PATH)
    elif how == "receipt_sha":
        monkeypatch.setattr(A5, "A4_LOCK_RECEIPT_SHA", "0" * 64)
    elif how == "identity_byte":
        io.open(os.path.join(d, "key_identity.json"), "a", encoding="utf-8").write(" ")
    elif how == "provenance_byte":
        io.open(os.path.join(d, "provenance.json"), "a", encoding="utf-8").write(" ")
    else:
        doc = json.load(io.open(A5.A4_LOCK_PATH, encoding="utf-8")); doc["signer"]["signed"] = False
        io.open(A5.A4_LOCK_PATH, "w", encoding="utf-8").write(json.dumps(doc, indent=1))
        monkeypatch.setattr(A5, "A4_LOCK_SHA", sha(A5.A4_LOCK_PATH))
    with pytest.raises(ValueError):
        if how in ("identity_byte",):
            A5.locked_sources()
        elif how in ("provenance_byte",):
            bad = A5.inventory_problems()
            raise ValueError(bad[0]) if bad else None
        else:
            A5.a4_lock()


def test_the_plan_records_the_final_lock_and_no_prompt_exposes_it():
    doc = A5.plan()
    assert "a4_v6_lock" not in doc
    b = doc["a4_lock"]
    assert b["sha256"] == FINAL_LOCK_SHA and b["receipt_sha256"] == FINAL_RECEIPT_SHA and b["state"] == "LOCKED" and b["signed"] is True and b["events"] == 36
    assert doc["n_events"] == 36 and doc["n_packets"] == 196 and doc["planned_producer_calls"] == 196 * len(A5.ACTIVE_ARM_IDS) == 392
    assert doc["a2_runtime_freeze"]["runtime_model_id"] == "claude-sonnet-5" and [a["arm"] for a in doc["arms"]] == ["P1", "P2"]
    _pks, prompts = A5.packets()
    text = "\n".join(prompts.values())
    for h in (FINAL_LOCK_SHA, FINAL_RECEIPT_SHA, b["key_identity_sha256"]):
        assert h not in text
    assert "a4_final_key_lock" not in text and "key_identity" not in text
