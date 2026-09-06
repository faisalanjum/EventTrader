# -*- coding: utf-8 -*-
"""A5 packets derive from the CORRECTED inventory the signed key was built over
(Codex SEQ 1514). Zero calls. The reader packets must carry the corrected source
passage for exactly the 11 items A4 corrected; everything else stays byte-identical.
"""
import hashlib, io, json, os, sys
import pytest
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import build_a5_exp5_kit as A5                                   # noqa: E402
import build_launch_manifest as BLM                              # noqa: E402
import build_kfields_key_targeted as T                           # noqa: E402
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()   # noqa: E731
CORR_SHA = "1440d75131c0c7418a66821778a88d5c1ff8fd9bdf7f4cca4d561b596c1b3066"
ELEVEN = ["0000006201-26-000031#001", "0000006201-26-000031#006", "0000006201-26-000031#008",
          "0000027904-26-000022#029", "0000092380-26-000044#042", "0000940944-26-000005#065",
          "0000940944-26-000009#068", "0000940944-26-000009#072", "0001041061-25-000109#075",
          "0001104659-26-027061#115", "0001171843-26-001288#133"]


def test_the_resolver_selects_the_corrected_inventory_only_on_a_provenance_match(monkeypatch, tmp_path):
    p = A5.corrected_inventory()
    assert sha(p) == CORR_SHA == T._sha(T.CORRECTED_INVENTORY) if hasattr(T, "_sha") else sha(p) == CORR_SHA
    lock = A5.a4_lock()
    prov = json.load(io.open(os.path.join(os.path.dirname(A5.A4_LOCK_PATH), "provenance.json"), encoding="utf-8"))["provenance"]
    assert prov["corrected_inventory_sha256"] == CORR_SHA and prov["frozen_inventory_sha256"] == sha(BLM.INVENTORY) != CORR_SHA
    # a missing corrected file refuses
    monkeypatch.setattr(A5, "CORRECTED_INVENTORY_PATH", str(tmp_path / "gone.json"))
    with pytest.raises(ValueError):
        A5.corrected_inventory()
    # a hash-drifted corrected file refuses
    drift = str(tmp_path / "drift.json"); io.open(drift, "w", encoding="utf-8").write(io.open(T.CORRECTED_INVENTORY, encoding="utf-8").read() + " ")
    monkeypatch.setattr(A5, "CORRECTED_INVENTORY_PATH", drift)
    with pytest.raises(ValueError):
        A5.corrected_inventory()


def test_one_packet_mismatch_is_reproduced_old_vs_corrected():
    events = BLM._events()
    orig_pk, orig_pr = BLM._one_item_packets(events, role="drafter", contract_suffix=A5.contract_era(), inventory=BLM.INVENTORY)
    corr_pk, corr_pr = BLM._one_item_packets(events, role="drafter", contract_suffix=A5.contract_era(), inventory=A5.corrected_inventory())
    pid = "0000006201-26-000031#001"
    assert orig_pr[pid] != corr_pr[pid]                             # the one mismatch A5 was serving
    o = {p["packet_id"]: p["item"] for p in orig_pk}[pid]; c = {p["packet_id"]: p["item"] for p in corr_pk}[pid]
    assert o["quote"] != c["quote"]                                 # the corrected source passage


def test_the_full_delta_is_exactly_11_prompts_across_8_launchers():
    events = BLM._events()
    _op, orig = BLM._one_item_packets(events, role="drafter", contract_suffix=A5.contract_era(), inventory=BLM.INVENTORY)
    _cp, corr = BLM._one_item_packets(events, role="drafter", contract_suffix=A5.contract_era(), inventory=A5.corrected_inventory())
    changed = sorted(pid for pid in orig if orig[pid] != corr[pid])
    assert changed == sorted(ELEVEN) and len(changed) == 11
    assert len(orig) == len(corr) == 196
    same = [pid for pid in orig if orig[pid] == corr[pid]]
    assert len(same) == 185
    # exactly 8 launcher templates move
    od = BLM.derive_expected(A5.RUNTIME_MODEL_ID, contract_suffix=A5.contract_era(), inventory=BLM.INVENTORY)
    cd = BLM.derive_expected(A5.RUNTIME_MODEL_ID, contract_suffix=A5.contract_era(), inventory=A5.corrected_inventory())
    lmoved = sorted(s for s in od["launchers"] if od["launchers"][s] != cd["launchers"][s])
    assert len(lmoved) == 8 and lmoved == sorted({p.split("#")[0] for p in ELEVEN})
    assert sum(1 for s in od["launchers"] if od["launchers"][s] == cd["launchers"][s]) == 28
    # source-event bytes, order and counts unchanged
    assert [e["input_sha256"] for e in od["events"]] == [e["input_sha256"] for e in cd["events"]]
    assert [c[0] for c in od["calls"]] == [c[0] for c in cd["calls"]] and len(od["calls"]) == len(cd["calls"])


def test_the_a5_plan_and_manifest_use_the_corrected_inventory():
    doc = A5.plan()
    assert doc["bound_inputs"]["inventory_sha256"] == CORR_SHA
    assert doc["inventory_sha256"] == CORR_SHA and doc["inventory_path"] and sha(doc["inventory_path"]) == CORR_SHA
    assert doc["n_packets"] == 196 and doc["planned_producer_calls"] == 392 and [a["arm"] for a in doc["arms"]] == ["P1", "P2"]
    _pk, prompts = A5.packets()
    for pid in ELEVEN:
        assert pid in prompts
    assert BLM.plan_inventory(doc) == doc["inventory_path"]         # the gate resolves the same corrected file
    assert BLM.plan_inventory({}) == BLM.INVENTORY                  # a plan that declares none keeps the original (A1 unchanged)


def test_inventory_problems_binds_the_corrected_inventory_to_the_provenance(monkeypatch):
    assert A5.inventory_problems() == []                            # the corrected file matches the lock's provenance
    monkeypatch.setattr(A5, "CORRECTED_INVENTORY_PATH", BLM.INVENTORY)   # the ORIGINAL is not the corrected the key was built over
    assert A5.inventory_problems()
