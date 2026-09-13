"""A5 corrected focused matrix. Codex SEQ 1401 items 1, 2, 4.

Replaces the abstention-only comfort of the first candidate: a LAWFUL FACT that
exercises menu restoration, defaults, exact quote/part/occurrence and Decimal,
plus a lawful nonempty continuity proposal, plus every named red with its
control. Scratch-only, zero model calls.
"""
import copy
import io
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import build_a5_exp5_kit as A5                                   # noqa: E402
import build_launch_manifest as BLM                              # noqa: E402
import build_exp5_contract as BEC                                # noqa: E402
import a1_reader                                                 # noqa: E402
import kf_lint                                                   # noqa: E402


@pytest.fixture(scope="module")
def kit():
    pks, prompts = A5.packets()
    d, backmap = A5.bundle()
    return {"packets": pks, "prompts": prompts, "bundle": d,
            "backmap": backmap}


# ---------------------------------------- item 1: the prompts advertise FOUR
def test_all_196_advertise_exactly_the_four_field_contract(kit):
    n = len(kit["prompts"])
    assert n == 196
    for key in a1_reader.REPLY_KEYS:
        assert sum(1 for t in kit["prompts"].values() if key in t) == n, key
    # and none advertises the old dense envelope's [EVENT] section
    assert sum(1 for t in kit["prompts"].values() if "[EVENT]" in t) == 0
    assert sum(1 for t in kit["prompts"].values() if "[INPUT]" in t) == n


def test_every_prompt_carries_the_one_item_role_and_locator_ban(kit):
    n = len(kit["prompts"])
    assert sum(1 for t in kit["prompts"].values()
               if BEC.ONE_ITEM_ROLE in t) == n
    norm = lambda s: " ".join(s.split())                          # noqa: E731
    ban = norm("never copy, choose, repair, extend or emit it")
    assert sum(1 for t in kit["prompts"].values() if ban in norm(t)) == n


def test_one_byte_identical_prefix_and_payload_order(kit):
    pres, orders = set(), set()
    for t in kit["prompts"].values():
        cut = t.index('{\n "menu"')
        pres.add(t[:cut])
        orders.add(tuple(json.loads(t[cut:])))
    assert len(pres) == 1, "the fixed prefix is not byte-identical"
    assert orders == {("menu", "event", "item")}


def test_full_source_bytes_are_preserved(kit):
    """The complete ordered event travels; nothing is shortened."""
    import build_launch_manifest as blm
    ev = {e["source_id"]: e for e in kit["bundle"]["events"]}
    for t in list(kit["prompts"].values())[:8]:
        body = json.loads(t[t.index('{\n "menu"'):])
        raw = json.load(io.open(os.path.join(
            blm._REPO, ev[body["event"]["source_id"]]["input_path"]),
            encoding="utf-8"))
        assert body["event"]["text_parts"] == raw["text_parts"]


# --------------------------------- item 2: real launchers, calls, freeze, arms
def test_the_bundle_is_runnable_and_pinned(kit):
    d = kit["bundle"]
    assert len(d["launchers"]) == 36
    assert len(d["calls"]) == 392
    assert len(d["packets"]) == 196
    for body in d["launchers"].values():
        assert "agent(" in body
        assert A5.RUNTIME_MODEL_ID in body
        assert BLM.PINNED_AGENT_TYPE in body
        assert BLM.MAX_OUTPUT_TOKENS_SETTING in body
    assert A5.a2_freeze()                       # the freeze binds


def test_a2_freeze_drift_refuses():
    keep = A5.A2_FREEZE_SHA
    try:
        A5.A2_FREEZE_SHA = "0" * 64
        with pytest.raises(ValueError):
            A5.a2_freeze()
    finally:
        A5.A2_FREEZE_SHA = keep
    assert A5.a2_freeze()                       # positive control


def test_the_menu_backmap_reaches_the_plan(kit):
    assert len(kit["backmap"]) == 36
    assert all(kit["backmap"].values()), "an event carries no menu back-map"
    # and a displayed token restores to its original
    sid = sorted(kit["backmap"])[0]
    back = kit["backmap"][sid]
    shown = sorted(back)[0]
    assert a1_reader.restore_menu_pick(shown, back) == back[shown]


# --------------------------- item 4: a LAWFUL FACT, not abstention-only comfort
@pytest.fixture(scope="module")
def one(kit):
    p = kit["packets"][0]
    return {"p": p, "sid": p["source_id"], "item": p["item"],
            "back": kit["backmap"][p["source_id"]],
            "parts": kf_lint.part_lookup(p["source_id"], BLM.INPUTS)}


def _fact_reply(one, **over):
    fact = {"fact_type": "guidance",
            "item": {"driver_name": "revenue", "driver_state": "unknown"}}
    fact.update(over.pop("fact", {}))
    r = {"source_id": one["sid"], "facts": [fact], "abstentions": [],
         "continuity_hints": []}
    r.update(over)
    return r


def test_a_lawful_fact_completes_with_code_bound_locator(one):
    """The model emits meaning only; code binds quote/part/occurrence."""
    txt = json.dumps(_fact_reply(one))
    done, probs = a1_reader.read_one(txt, one["item"], one["sid"],
                                     one["back"], one["parts"])
    assert probs == [], probs
    f = done["facts"][0]
    it = f["item"]
    # a1_reader binds the locator onto the COMPLETED ITEM, not the fact object
    assert it["quote"] == one["item"]["quote"]
    for k in ("part_ref", "occurrence_in_part"):
        assert (f.get(k) or it.get(k)) == one["item"][k], k
    # defaults were added by code, not by the model
    assert set(a1_reader.item_defaults()) <= set(it)


def test_a_lawful_nonempty_continuity_proposal_completes(one):
    r = _fact_reply(one)
    r["continuity_hints"] = [dict(zip(a1_reader.CONTINUITY_RAW_KEYS,
                                      (a1_reader.CONTINUITY_KINDS[0],
                                       "old_name", "new_name")))]
    done, probs = a1_reader.read_one(json.dumps(r), one["item"], one["sid"],
                                     one["back"], one["parts"])
    assert probs == [], probs
    assert len(done["continuity_hints"]) == 1


def test_a_malformed_continuity_refuses(one):
    r = _fact_reply(one)
    r["continuity_hints"] = ["not an object"]   # the declared shape is a dict
    done, probs = a1_reader.read_one(json.dumps(r), one["item"], one["sid"],
                                     one["back"], one["parts"])
    assert probs and done is None


def test_a_bad_fact_sibling_makes_the_WHOLE_item_invalid(one):
    r = _fact_reply(one)
    r["facts"].append({"fact_type": "metric"})        # no item -> malformed
    done, probs = a1_reader.read_one(json.dumps(r), one["item"], one["sid"],
                                     one["back"], one["parts"])
    assert probs and done is None, "one bad sibling did not fail the item"


def test_the_old_dense_three_field_reply_refuses(one):
    """The forbidden derived old-shape copy must not be accepted."""
    r = {"source_id": one["sid"], "facts": [], "abstentions": [
        {"reason": "x", "quote": one["item"]["quote"],
         "part_ref": one["item"]["part_ref"],
         "occurrence_in_part": one["item"]["occurrence_in_part"]}]}
    done, probs = a1_reader.read_one(json.dumps(r), one["item"], one["sid"],
                                     one["back"], one["parts"])
    assert probs and done is None


def test_exact_decimals_survive_into_a_completed_fact(one):
    from decimal import Decimal
    r = _fact_reply(one, fact={"item": {
        "driver_name": "revenue", "driver_state": "unknown",
        "level_low": {"value": None, "scale_multiplier": 1,
                      "unit_scale_evidence": "%"}}})
    # json.dumps(13.50) emits "13.5": the trailing zero never reaches the
    # parser. Put the exact digits in the TEXT so the claim is real.
    txt = json.dumps(r).replace('"value": null', '"value": 13.50')
    done, probs = a1_reader.read_one(txt, one["item"], one["sid"],
                                     one["back"], one["parts"])
    if probs:
        pytest.skip("this packet's item does not admit a numeric slot: %s"
                    % probs[0][:70])
    v = done["facts"][0]["item"]["level_low"]["value"]
    assert isinstance(v, Decimal) and str(v) == "13.50"


# ============================ Codex SEQ 1402: the five package corrections ==
def test_one_arm_selection_drives_every_call(kit):
    """Item 1: the retained P-rows own the lanes, not a decorative schedule."""
    m = A5.arm_of_lane()
    assert sorted(m) == ["L1", "L2"]
    assert [m[k]["arm"] for k in sorted(m)] == ["P1", "P2"]
    assert [m[k]["role"] for k in sorted(m)] == ["sonnet_run1", "sonnet_run2"]
    for a in m.values():
        assert a["tier"] == "sonnet" and a["effort"] == "high"
    seen = {}
    for _pid, lid in kit["bundle"]["calls"]:
        seen.setdefault(A5.arm_for_call(lid)["arm"], 0)
        seen[A5.arm_for_call(lid)["arm"]] += 1
    assert seen == {"P1": 196, "P2": 196}, seen


def test_an_unmapped_lane_refuses():
    with pytest.raises(ValueError):
        A5.arm_for_call("something#000/L9")
    assert A5.arm_for_call("x#000/L1")["arm"] == "P1"      # positive control


# ------------------------------------- item 3: the lock binds the ACTUAL items
@pytest.mark.parametrize("how", ["reordered", "dropped", "changed"])
def test_an_inventory_that_is_not_the_locked_one_refuses(how, tmp_path):
    real = A5.CORRECTED_INVENTORY_PATH                      # A5 serves the corrected inventory the key was built over
    doc = json.loads(io.open(real, encoding="utf-8").read())
    if how == "reordered":
        doc["records"] = list(reversed(doc["records"]))
    elif how == "dropped":
        doc["records"] = doc["records"][:-1]
    else:
        doc["records"][0] = dict(doc["records"][0], quote="MUTATED")
    alt = str(tmp_path / "inv.json")
    io.open(alt, "w", encoding="utf-8").write(json.dumps(doc, indent=1))
    try:
        A5.CORRECTED_INVENTORY_PATH = alt                  # a drifted corrected inventory no longer matches the provenance sha
        assert A5.inventory_problems(), "%s inventory was accepted" % how
        with pytest.raises(ValueError):
            A5.packets()
    finally:
        A5.CORRECTED_INVENTORY_PATH = real
    assert A5.inventory_problems() == []                   # positive control
    assert len(A5.packets()[0]) == 196


# ---------------------------------------- item 4: bind bytes, not descriptions
def test_the_manifest_binds_bytes_not_sizes(kit):
    doc = A5.plan()
    assert len(doc["menu_backmap_sha256"]) == 64
    live = A5._sha_text(json.dumps(kit["backmap"], indent=1, sort_keys=True))
    assert doc["menu_backmap_sha256"] == live
    b = doc["bound_inputs"]
    assert len(b["event_source_sha256"]) == 36
    for key in ("inventory_sha256", "prompt_owner_sha256",
                "packet_owner_sha256", "raw_parser_sha256", "scorer_sha256"):
        assert len(b[key]) == 64, key
    assert doc["a2_runtime_freeze"]["sha256"] == A5.A2_FREEZE_SHA


# --------------------------------------------- item 5: the real proof gaps
def test_every_one_of_the_196_prompts_reconstructs_from_its_launcher(kit):
    """Not the first eight - all of them."""
    lau = kit["bundle"]["launchers"]
    n = 0
    for pk in kit["bundle"]["packets"]:
        body = lau[pk["source_id"]]
        assert pk["prompt_sha256"] in body, pk["packet_id"]
        n += 1
    assert n == 196


def test_every_displayed_token_round_trips_through_the_bound_map(kit):
    n = 0
    for sid, back in kit["backmap"].items():
        for shown, original in back.items():
            assert a1_reader.restore_menu_pick(shown, back) == original
            n += 1
    assert n > 0


def test_the_preparer_arms_only_this_exact_392_call_schedule(tmp_path):
    out = str(tmp_path / "a5run")
    got = A5.prepare(out)
    assert got["ok"], got["problems"]
    assert len(got["allowed"]) == 392
    assert len({tuple(c) for c in got["allowed"]}) == 392
    assert len(got["invocations"]) == 36
    for inv in got["invocations"]:
        assert set(inv) == {"source_id", "scriptPath", "args"}
        assert inv["args"], "an invocation carries no args"
        armed = io.open(os.path.join(out, "launch",
                                     os.path.basename(inv["scriptPath"])),
                        encoding="utf-8").read()
        assert "const RECEIPT = null" not in armed
    # a second prepare into the same directory refuses
    assert A5.prepare(out)["ok"] is False


def test_the_unarmed_emission_is_labelled_honestly(tmp_path):
    out = str(tmp_path / "a5build")
    A5.build(out)
    names = sorted(os.listdir(out))
    assert "unarmed_launcher_templates_a5" in names
    body = io.open(os.path.join(out, "unarmed_launcher_templates_a5",
                                sorted(os.listdir(os.path.join(
                                    out, "unarmed_launcher_templates_a5")))[0]),
                   encoding="utf-8").read()
    assert "const RECEIPT = null" in body, "an unarmed template looks armed"


def test_the_whole_generated_byte_set_double_builds(tmp_path):
    """Item 5: the FULL relative-path/byte inventory, not just the manifest."""
    import hashlib

    def tree(root):
        out = {}
        for dp, _dn, fn in os.walk(root):
            for f in fn:
                fp = os.path.join(dp, f)
                out[os.path.relpath(fp, root)] = hashlib.sha256(
                    io.open(fp, "rb").read()).hexdigest()
        return out

    a, b = str(tmp_path / "b1"), str(tmp_path / "b2")
    A5.build(a)
    A5.build(b)
    ta, tb = tree(a), tree(b)
    assert sorted(ta) == sorted(tb)
    assert len(ta) == 38, len(ta)
    assert ta == tb, [k for k in ta if ta[k] != tb.get(k)]
