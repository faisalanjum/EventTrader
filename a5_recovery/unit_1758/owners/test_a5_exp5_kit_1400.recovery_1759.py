"""A5 focused tests. Codex SEQ 1400 items 3-8.

Scratch-only. No model call, no A6, no repository/plan/database write. Every
negative below has a lawful positive control beside it.
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
import a1_reader                                                 # noqa: E402
import raw_transport as RT                                       # noqa: E402
import kf_lint                                                   # noqa: E402


@pytest.fixture(scope="module")
def kit():
    lock = A5.a4_lock()
    pks, prompts = A5.packets()
    return {"lock": lock, "packets": pks, "prompts": prompts}


# ------------------------------------------------- item 3: lock + denominator
def test_the_a4_lock_binds_and_the_counts_derive(kit):
    assert kit["lock"]["state"] == "LOCKED"
    assert kit["lock"]["signature"]["signed"] is True
    assert len(A5.locked_sources(kit["lock"])) == 36
    assert len(kit["packets"]) == 196
    assert len(kit["prompts"]) == 196
    assert len(kit["packets"]) * len(A5.ACTIVE_ARM_IDS) == 392


@pytest.mark.parametrize("how", ["sha", "missing"])
def test_a4_lock_drift_refuses(how):
    keep_s, keep_p = A5.A4_LOCK_SHA, A5.A4_LOCK_PATH
    try:
        if how == "sha":
            A5.A4_LOCK_SHA = "0" * 64
        else:
            A5.A4_LOCK_PATH = keep_p + ".missing"
        with pytest.raises(ValueError):
            A5.a4_lock()
    finally:
        A5.A4_LOCK_SHA, A5.A4_LOCK_PATH = keep_s, keep_p
    assert A5.a4_lock()["state"] == "LOCKED"          # positive control


@pytest.mark.parametrize("how", ["reordered", "dropped", "duplicated"])
def test_source_or_order_drift_refuses(how):
    real = BLM._events
    try:
        if how == "reordered":
            BLM._events = lambda: list(reversed(real()))
        elif how == "dropped":
            BLM._events = lambda: real()[:-1]
        else:
            BLM._events = lambda: real() + [dict(real()[0])]
        with pytest.raises(ValueError):
            A5.packets()
    finally:
        BLM._events = real
    assert len(A5.packets()[0]) == 196                # positive control


# --------------------------------------------------- item 5: the arm schedule
def test_only_two_independent_sonnet_high_arms_are_active():
    rows = A5.active_arms()          # DERIVED from the frozen kit, not typed
    assert [a["arm"] for a in rows] == ["P1", "P2"]
    assert [a["role"] for a in rows] == ["sonnet_run1", "sonnet_run2"]
    for a in rows:
        assert a["tier"] == "sonnet" and a["effort"] == "high" and a["active"]
    names = json.dumps([dict(a) for a in rows])
    for gone in ("haiku", "opus", "qwen", "gpt", "fallback", "escalation",
                 "P3", "P4", "P5"):
        assert gone.lower() not in names.lower(), gone
    # retired, but retained as evidence
    assert any("P3" in r for r in A5.RETIRED_ARMS)
    assert any("opus_ref" in r for r in A5.RETIRED_ARMS)


# ------------------------------------------- item 4/6: the ONE reply seam
def _reply(sid, facts=None, absts=None, conts=None):
    return {"source_id": sid, "facts": facts or [],
            "abstentions": absts if absts is not None else [],
            "continuity_hints": conts or []}


@pytest.fixture(scope="module")
def one(kit):
    """One real packet and its trusted located item."""
    p = kit["packets"][0]
    return {"packet": p, "sid": p["source_id"], "item": p["item"],
            "menu_back": p.get("menu_back") or p.get("menu_backmap"),
            "parts": kf_lint.part_lookup(p["source_id"], BLM.INPUTS)}


def test_a_lawful_abstention_reply_completes(one):
    txt = json.dumps(_reply(one["sid"], absts=[{"reason": "no lawful fact"}]))
    done, probs = a1_reader.read_one(txt, one["item"], one["sid"],
                                     one["menu_back"], one["parts"])
    assert probs == [], probs
    assert done is not None


@pytest.mark.parametrize("how", ["missing_top_key", "extra_top_key",
                                 "wrong_source", "facts_not_list",
                                 "both_empty", "both_full"])
def test_a_malformed_top_level_reply_refuses(one, how):
    r = _reply(one["sid"], absts=[{"reason": "x"}])
    if how == "missing_top_key":
        del r["continuity_hints"]
    elif how == "extra_top_key":
        r["invented"] = 1
    elif how == "wrong_source":
        r["source_id"] = "not-this-event"
    elif how == "facts_not_list":
        r["facts"] = {}
    elif how == "both_empty":
        r["abstentions"] = []
    else:
        r["facts"] = [{"item": {}}]
    done, probs = a1_reader.read_one(json.dumps(r), one["item"], one["sid"],
                                     one["menu_back"], one["parts"])
    assert probs, "%s was accepted" % how
    assert done is None


def test_the_model_may_not_emit_the_locator(one):
    """Code alone binds quote/part/occurrence."""
    r = _reply(one["sid"], absts=[{"reason": "x"}])
    r["facts"] = []
    r["abstentions"] = [{"reason": "x", "quote": "model wrote this",
                         "part_ref": "P1", "occurrence_in_part": 1}]
    done, probs = a1_reader.read_one(json.dumps(r), one["item"], one["sid"],
                                     one["menu_back"], one["parts"])
    assert probs, "a model-emitted locator was accepted"


@pytest.mark.parametrize("bad", ['{"source_id":"x","source_id":"y"}',
                                 '{"a":NaN}', '{"a":Infinity}',
                                 'not json at all'])
def test_a_malformed_envelope_refuses(one, bad):
    done, probs = a1_reader.read_one(bad, one["item"], one["sid"],
                                     one["menu_back"], one["parts"])
    assert probs and done is None


def test_plain_and_one_whole_fence_are_equal(one):
    body = json.dumps(_reply(one["sid"], absts=[{"reason": "x"}]))
    fenced = "```json\n%s\n```" % body
    a = a1_reader.read_one(body, one["item"], one["sid"], one["menu_back"],
                           one["parts"])
    b = a1_reader.read_one(fenced, one["item"], one["sid"], one["menu_back"],
                           one["parts"])
    assert a[1] == [] and b[1] == []
    assert a[0] == b[0]


def test_exact_decimals_survive_the_parser():
    from decimal import Decimal
    got = RT.parse_reply('{"v": 1.10, "w": 0.30}')
    assert got["v"] == Decimal("1.10") and str(got["v"]) == "1.10"
    assert type(got["v"]) is Decimal


# --------------------------------------------------- item 7: no key exposure
def test_no_prompt_exposes_the_key_or_the_lock(kit):
    text = "\n".join(kit["prompts"].values())
    assert A5.A4_LOCK_SHA not in text
    assert "a4_detailed_key_lock" not in text
    for shard in kit["lock"]["key_shards"]:
        assert shard["sha256"] not in text


def test_the_kit_owner_reaches_no_write_path():
    src = io.open(os.path.join(_HERE, "build_a5_exp5_kit.py"),
                  encoding="utf-8").read().lower()
    for bad in ("neo4j", "driver_write_cli", "session.run", "activate("):
        assert bad not in src, bad


# --------------------------------------------------------- item 8: build twice
# The manifest-only double build lived here and was too weak: it compared ONE
# file while the build emits 38. The full relative-path/byte comparison now
# lives in test_a5_contract_1401.test_the_whole_generated_byte_set_double_builds
# (Codex SEQ 1402 item 5). Keeping a weaker duplicate beside it would just be a
# second, quieter claim about the same property.
