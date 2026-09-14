"""Codex SEQ 1379 — focused proof for the final A4 package. Build-only.

Red first. Every negative has a lawful control beside it, and the lawful
fixture is scaffolding for shape and size, never evidence.
"""
import ast
import copy
import decimal
import io
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, "/home/faisal/EventMarketDB")

import build_inventory_review as BIR                             # noqa: E402
import build_kfields_final as F                                  # noqa: E402
import build_kfields_hard_review as HR                           # noqa: E402
import kf_lint                                                   # noqa: E402

K = F.K
_S = os.environ.get(
    "KF_SCRATCH", "/tmp/claude-1000/-home-faisal-EventMarketDB/"
    "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
EV = io.open(os.path.join(_S, "a4_dir.txt"), encoding="utf-8").read().strip()
HRR = io.open(os.path.join(_S, "hr_dir.txt"), encoding="utf-8").read().strip()
FIXR = io.open(os.path.join(_S, "hrfix_dir.txt"),
               encoding="utf-8").read().strip()

KINDS = {p: r["proposed_record_kind"] for p, r in F._inventory()}
TAGS = {p: list(r["proposed_hard_classes"]) for p, r in F._inventory()}


@pytest.fixture(autouse=True)
def _fresh():
    HR._items.cache_clear()
    HR._source.cache_clear()
    yield


@pytest.fixture
def pkg(tmp_path):
    out = str(tmp_path / "pkg")
    F.build(out, EV, HRR, FIXR)
    return out


# ------------------------------------------------------ the lawful fixture --
def _num(o):
    """Fixture-only: Decimal -> JSON number -> Decimal. Not exact, not evidence."""
    if isinstance(o, decimal.Decimal):
        return float(o)
    if isinstance(o, dict):
        return {k: _num(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_num(v) for v in o]
    return o


def _hard_map():
    out = {}
    for t in HR.tasks(EV):
        for k in t["members"]:
            out[k] = t
    return out


def _sparse_for(packet, hard):
    p1 = F._phase1_settlements(EV)
    rd = F._hard_readings(EV, HRR, FIXR)
    t = hard.get(packet)
    if t is not None:
        lab = HR.call_label(t["task_id"], 1)
        if lab in rd:
            obj = K.RT.parse_reply(rd[lab][2])
            if t["kind"] == "item":
                return obj
            for m, key in zip(obj["members"], t["members"]):
                if key == packet:
                    return m["settled"]
    if packet in p1:
        return K.RT.parse_reply(p1[packet][0])["settled"]
    return {"source_id": packet.split("#")[0], "facts": [],
            "abstentions": [{"reason": "no prior settlement exists"}],
            "continuity_hints": []}


def shard_doc(task, hard=None, one_fact=False):
    """A lawful shard as a plain object, ready to be mutated then dumped."""
    hard = hard or _hard_map()
    rows, review = [], []
    for n, packet in enumerate(task["rows"]):
        sp = _sparse_for(packet, hard)
        nf = len(sp["facts"])
        outcome = "fact" if nf else (
            "control" if KINDS[packet] in F.CONTROL_KINDS else "exclusion")
        rows.append({"row_index": n + 1, "settled": sp,
                     "final_outcome": outcome,
                     "record_kind_note": "frozen %s; settled %s"
                                         % (KINDS[packet], outcome)})
        for i in range(nf):
            review.append({"row_index": n + 1, "fact_index": i,
                           "hard_classes": list(TAGS[packet]),
                           F.GOLD_ONLY[0]: True,
                           F.GOLD_ONLY[1]: {F.GOLD_EXTRA_KEYS[0]: False},
                           F.GOLD_ONLY[2]: None})
    idx = {p: n + 1 for n, p in enumerate(task["rows"])}
    groups = [{"member_row_indexes": [idx[m] for m in members],
               "members_are_one_fact": (True if one_fact else False),
               "reason": "one fact" if one_fact else "distinct facts"}
              for members in task["groups"].values()]
    leads = F.event_leads(EV, HRR, FIXR, task)
    return {"source_id": task["source_id"], "rows": rows, "review": review,
            "groups": groups,
            "lead_reconciliation": [{"lead_id": x["lead_id"], "agrees": True,
                                     "why": "matches"} for x in leads],
            "open_issues": []}


def shard_text(doc):
    return json.dumps(_num(doc))


def all_shards(one_fact=False):
    hard = _hard_map()
    out, raws = {}, {}
    for t in F.event_tasks(EV):
        txt = shard_text(shard_doc(t, hard, one_fact))
        raws[t["source_id"]] = txt
        v, bad = F.read_shard(txt, t, F.event_leads(EV, HRR, FIXR, t))
        assert not bad, (t["source_id"], bad[:2])
        out[t["source_id"]] = v
    return out, raws


# =============================================== positives: the accounting ==
def test_thirty_six_events_and_196_unique_rows_each_exactly_once():
    tasks = F.event_tasks(EV)
    assert len(tasks) == 36
    rows = [p for t in tasks for p in t["rows"]]
    assert len(rows) == 196 == len(set(rows))
    assert set(rows) == {p for p, _r in F._inventory()}
    assert [t["source_id"] for t in tasks] == list(
        dict.fromkeys(r["source_id"] for _p, r in F._inventory()))


def test_every_hard_member_carries_both_blind_leads_and_no_row_is_fabricated():
    hard = _hard_map()
    p1 = F._phase1_settlements(EV)
    for t in F.event_tasks(EV):
        leads = F.event_leads(EV, HRR, FIXR, t)
        by_row = {}
        for x in leads:
            by_row.setdefault(x["row_index"], []).append(x)
        for n, packet in enumerate(t["rows"]):
            got = by_row.get(n + 1, [])
            blind = [x for x in got if x["origin"] != "phase1_a4_envelope"]
            if packet in hard:
                assert len(blind) == 2, (packet, len(blind))
            else:
                assert not blind, "%s acquired a fabricated blind lead" % packet
            if packet in p1:
                assert any(x["origin"] == "phase1_a4_envelope" for x in got)


def test_a_row_with_no_lead_is_still_carried():
    p1 = F._phase1_settlements(EV)
    hard = _hard_map()
    orphan = [p for p, _r in F._inventory()
              if p not in p1 and p not in hard]
    # the 6 unresolved packets are hard, so every leadless row is hard;
    # prove the invariant rather than assuming which rows it covers
    for t in F.event_tasks(EV):
        assert len(t["rows"]) == len(
            [p for p, r in F._inventory() if r["source_id"] == t["source_id"]])
    assert all(p in {x for tt in F.event_tasks(EV) for x in tt["rows"]}
               for p in orphan)


def test_a_missing_event_shard_leaves_rows_unaccounted_and_refuses():
    """Reaches the all-196 guard.

    The lawful fixture always supplies every shard, so the accounting check was
    unreachable and could be deleted with the whole battery still green.
    """
    shards, _raws = all_shards()
    dropped = sorted(shards)[0]
    del shards[dropped]
    _key, side, problems = F.materialize(EV, shards)
    assert any("no final shard" in p for p in problems)
    assert any("never accounted" in p for p in problems)
    assert len(side["packet_to_gold"]) < 196


def test_a_row_accounted_twice_refuses():
    shards, _raws = all_shards()
    first = sorted(shards)[0]
    victim = sorted(shards)[1]
    shards[victim] = copy.deepcopy(shards[first])
    _key, _side, problems = F.materialize(EV, shards)
    assert problems


def test_every_accepted_fact_carries_the_three_review_fields_and_passes_door():
    shards, _raws = all_shards()
    key, side, problems = F.materialize(EV, shards)
    assert problems == []
    assert F.key_problems(key) == []
    for _sid, facts in key.items():
        for f in facts:
            assert set(f) == set(kf_lint.FACT_KEYS)
            assert isinstance(f[F.GOLD_ONLY[0]], bool)
            assert set(f[F.GOLD_ONLY[1]]) == set(F.GOLD_EXTRA_KEYS)


def test_counts_recompute_from_the_accepted_facts():
    shards, _raws = all_shards()
    key, side, _p = F.materialize(EV, shards)
    c = F.counts(key, side)
    assert c["events_accounted"] == 36
    assert c["rows_accounted"] == 196
    assert c["tag_floor"] == BIR.INV.TAG_FLOOR if hasattr(BIR, "INV") \
        else c["tag_floor"] == F.INV.TAG_FLOOR
    assert c["accepted_facts"] == sum(len(v) for v in key.values())
    assert c["phase1_ambiguities"] == 169


# ================================================ the rule text is served ===
def test_the_gate_and_every_tag_rule_are_served_as_owning_text():
    prefix = F.prompt_prefix()
    assert BIR.gate_text().rstrip() in prefix
    assert BIR.crosswalk_text().rstrip() in prefix
    for tag in F.HARD_CLASSES:
        assert ("## Tag `%s`" % tag) in prefix
    # category names alone are not enough: the owning rule text must be there
    assert "Owning rule text, quoted exactly:" in prefix
    assert "DriverUpdate" in prefix


def test_a_changed_gate_or_tag_rule_refuses(pkg, monkeypatch):
    monkeypatch.setattr(BIR, "gate_text",
                        lambda: BIR.__dict__["gate_text"].__wrapped__()
                        if False else "a different gate")
    assert F.package_problems(pkg, EV, HRR, FIXR)


def test_a_changed_crosswalk_refuses(pkg, monkeypatch):
    real = BIR.crosswalk_text
    monkeypatch.setattr(BIR, "crosswalk_text", lambda: real() + "\nextra.\n")
    assert F.package_problems(pkg, EV, HRR, FIXR)


def test_the_group_judgment_reuses_the_hard_review_vocabulary():
    assert not hasattr(F, "GROUP_MEANINGS")
    assert "members_are_one_fact" in F.GROUP_KEYS
    assert "members_are_one_fact" in F.prompt_prefix()


# ================================================= record-kind reconciliation
def test_control_to_fact_and_real_to_zero_are_recorded_never_silent():
    shards, _raws = all_shards()
    key, side, _p = F.materialize(EV, shards)
    conflicts = side["record_kind_conflicts"]
    assert conflicts, "the frozen conflicts must be recorded"
    for m in conflicts:
        assert (m["proposed_record_kind"] in F.CONTROL_KINDS
                and m["accepted_facts"] > 0) or \
               (m["proposed_record_kind"] == "real_item"
                and m["accepted_facts"] == 0)
    # every row states its reconciliation; none may be blank
    for t in F.event_tasks(EV):
        doc = shard_doc(t)
        for r in doc["rows"]:
            assert r["record_kind_note"].strip()


def test_a_blank_record_kind_note_refuses():
    t = F.event_tasks(EV)[0]
    doc = shard_doc(t)
    doc["rows"][0]["record_kind_note"] = "   "
    _v, bad = F.read_shard(shard_text(doc), t,
                           F.event_leads(EV, HRR, FIXR, t))
    assert any("record-kind" in b for b in bad)


def test_an_outcome_that_contradicts_its_facts_refuses():
    t = [x for x in F.event_tasks(EV) if len(x["rows"]) > 1][0]
    doc = shard_doc(t)
    hit = next(r for r in doc["rows"] if r["settled"]["facts"])
    hit["final_outcome"] = "control"
    _v, bad = F.read_shard(shard_text(doc), t,
                           F.event_leads(EV, HRR, FIXR, t))
    assert any("cannot carry a fact" in b for b in bad)


# ====================================================== group relation ======
def test_one_fact_must_leave_exactly_one_and_code_never_chooses():
    shards, _raws = all_shards(one_fact=True)
    _key, _side, problems = F.materialize(EV, shards)
    assert any("code will not choose which" in p for p in problems)


def test_null_group_relation_can_never_be_promoted():
    hard = _hard_map()
    tasks = [t for t in F.event_tasks(EV) if t["groups"]]
    t = tasks[0]
    doc = shard_doc(t, hard)
    doc["groups"][0]["members_are_one_fact"] = None
    doc["groups"][0]["reason"] = "cannot settle it"
    v, bad = F.read_shard(shard_text(doc), t, F.event_leads(EV, HRR, FIXR, t))
    assert not bad
    shards, _r = all_shards()
    shards[t["source_id"]] = v
    _key, _side, problems = F.materialize(EV, shards)
    assert any("cannot be promoted" in p for p in problems)


@pytest.mark.parametrize("bad_value", ['"true"', "1", "[]", '"null"'])
def test_a_group_relation_that_is_not_a_real_boolean_or_null_refuses(bad_value):
    t = [x for x in F.event_tasks(EV) if x["groups"]][0]
    doc = shard_doc(t)
    txt = shard_text(doc).replace('"members_are_one_fact": false',
                                  '"members_are_one_fact": %s' % bad_value)
    _v, bad = F.read_shard(txt, t, F.event_leads(EV, HRR, FIXR, t))
    assert any("members_are_one_fact" in b for b in bad)


# ============================================== rows, leads, review shape ===
@pytest.mark.parametrize("mutate,expect", [
    (lambda d: d["rows"].pop(0), "rows must be"),
    (lambda d: d["rows"].append(copy.deepcopy(d["rows"][0])), "rows must be"),
    (lambda d: d["rows"].reverse(), "echoes index"),
    (lambda d: d["review"].pop(0), "review rows are"),
    (lambda d: d["lead_reconciliation"].pop(0), "lead_reconciliation"),
    (lambda d: d.__setitem__("source_id", "somewhere-else"), "source_id is"),
    (lambda d: d.__setitem__("open_issues", [{"what": "x"}]), "open_issues"),
])
def test_every_shard_mutation_refuses(mutate, expect):
    t = [x for x in F.event_tasks(EV) if len(x["rows"]) > 2][0]
    doc = shard_doc(t)
    mutate(doc)
    _v, bad = F.read_shard(shard_text(doc), t,
                           F.event_leads(EV, HRR, FIXR, t))
    assert bad and any(expect in b for b in bad), bad[:2]


def test_a_lawful_shard_is_accepted():
    t = F.event_tasks(EV)[0]
    v, bad = F.read_shard(shard_text(shard_doc(t)), t,
                          F.event_leads(EV, HRR, FIXR, t))
    assert bad == [] and v["source_id"] == t["source_id"]


@pytest.mark.parametrize("field", list(F.GOLD_ONLY))
def test_a_missing_review_field_refuses(field):
    t = F.event_tasks(EV)[0]
    doc = shard_doc(t)
    if not doc["review"]:
        pytest.skip("this event settled no fact in the fixture")
    del doc["review"][0][field]
    _v, bad = F.read_shard(shard_text(doc), t,
                           F.event_leads(EV, HRR, FIXR, t))
    assert any("review row is not exactly" in b for b in bad)


def test_a_tag_outside_the_frozen_vocabulary_refuses():
    t = next(x for x in F.event_tasks(EV) if shard_doc(x)["review"])
    doc = shard_doc(t)
    doc["review"][0]["hard_classes"] = ["not_a_real_tag"]
    _v, bad = F.read_shard(shard_text(doc), t,
                           F.event_leads(EV, HRR, FIXR, t))
    assert any("hard_classes" in b for b in bad)


# ======================================================= raw-first, numbers =
def test_a_json_number_stays_a_number_and_a_string_stays_a_string():
    raw = '{"a": 3.40, "b": "3.40"}'
    got = K.RT.parse_reply(raw)
    assert isinstance(got["a"], decimal.Decimal)
    assert str(got["a"]) == "3.40"
    assert isinstance(got["b"], str) and got["b"] == "3.40"


def _dumps_calls(tree):
    """Every json.dumps(...) call that drops type information, by position."""
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if not (isinstance(fn, ast.Attribute) and fn.attr == "dumps"):
            continue
        if any(k.arg == "default" for k in node.keywords):
            out.append(node)
    return out


def test_the_lossy_detector_actually_detects(tmp_path):
    """A control that can never fire proves nothing. This one is shown a real
    lossy call and must see it, before the next control claims there are none."""
    assert len(_dumps_calls(ast.parse(
        "import json\njson.dumps(x, default=str)\n"))) == 1
    assert _dumps_calls(ast.parse("import json\njson.dumps(x)\n")) == []


def test_there_is_no_reserialization_seam_in_the_owner():
    """AST, not text. Two earlier versions of this control read the SOURCE as
    words - one matched a comment containing "Decimal", the next matched a
    docstring containing "default=str". A comment cannot serialize anything,
    so the check now asks the parser, which only sees real calls.

    The claim is stronger than it used to be. There is no longer a lossy
    serialization ANYWHERE in the owner to confine to a hash: the exact
    type-preserving identity replaced the last one."""
    src = io.open(os.path.join(_HERE, "build_kfields_final.py"),
                  encoding="utf-8").read()
    tree = ast.parse(src)
    assert _dumps_calls(tree) == []
    # and the prompt the model reads never takes that path at all
    fn = [n for n in ast.walk(tree)
          if isinstance(n, ast.FunctionDef) and n.name == "final_prompt"][0]
    assert _dumps_calls(fn) == []


def test_every_lead_is_raw_bytes_hash_bound_to_what_is_shown():
    n = 0
    for t in F.event_tasks(EV):
        for x in F.event_leads(EV, HRR, FIXR, t):
            assert isinstance(x["reply"], str)
            assert x["sha256"] == K._sha(x["reply"])
            n += 1
    assert n == 274


def test_a_changed_lead_byte_refuses(pkg, monkeypatch):
    real = F._hard_readings

    def drifted(a, b, c):
        out = dict(real(a, b, c))
        k = sorted(out)[0]
        origin, sha, raw = out[k]
        out[k] = (origin, sha, raw + " ")
        return out
    monkeypatch.setattr(F, "_hard_readings", drifted)
    assert F.package_problems(pkg, EV, HRR, FIXR)


# ============================================== package, capacity, ledger ===
def test_the_package_double_builds_byte_identically(tmp_path):
    a, b = str(tmp_path / "a"), str(tmp_path / "b")
    F.build(a, EV, HRR, FIXR)
    F.build(b, EV, HRR, FIXR)
    for name in sorted(os.listdir(a)):
        assert K.INV.sha_file(os.path.join(a, name)) \
            == K.INV.sha_file(os.path.join(b, name)), name


def test_a_lawful_package_passes_preflight(pkg):
    out = F.preflight(pkg, EV, HRR, FIXR)
    assert out["problems"] == []
    assert out["ok"] is True


def test_the_derived_ceiling_is_exact(pkg):
    doc = K._load(os.path.join(pkg, F.MANIFEST_NAME))
    b = doc["budget"]
    assert (b["before"], b["planned_total"], b["after_planned"]) \
        == (4311, 37, 4348)
    assert b["worst_case_total"] == 74
    assert b["worst_case_after"] == 4385 < F.GLOBAL_CEILING == 6000


def test_every_event_and_the_signer_fit_the_transport(pkg):
    doc = K._load(os.path.join(pkg, F.MANIFEST_NAME))
    assert doc["capacity"]["at_or_over_transport_limit"] == []
    assert doc["capacity"]["largest_script_bytes"] < K.TRANSPORT_LIMIT
    shards, raws = all_shards()
    key, side, _p = F.materialize(EV, shards)
    sh = [(sid, K._sha(raws[sid])) for sid in raws]
    script = F.render_signer(sh, F.counts(key, side), raws)
    assert len(script.encode("utf-8")) < K.TRANSPORT_LIMIT


@pytest.mark.parametrize("mutate", [
    lambda d: d["events"].pop(0),
    lambda d: d["call_order"].reverse(),
    lambda d: d["events"][0].__setitem__("prompt_sha256", "0" * 64),
    lambda d: d.__setitem__("prefix_sha256", "0" * 64),
    lambda d: d["counts"].__setitem__("unique_rows", 195),
    lambda d: d["transport"].__setitem__("model_alias", "opus"),
])
def test_every_package_mutation_refuses(pkg, mutate):
    path = os.path.join(pkg, F.MANIFEST_NAME)
    doc = json.loads(K._read(path))
    mutate(doc)
    io.open(path, "w", encoding="utf-8").write(json.dumps(doc, indent=1))
    assert F.package_problems(pkg, EV, HRR, FIXR)


def test_a_stale_model_refuses(pkg, monkeypatch):
    monkeypatch.setattr(K, "MODEL", "claude-fable-5")
    assert F.package_problems(pkg, EV, HRR, FIXR)


def test_an_attempt_three_refuses_at_both_renderers():
    t = F.event_tasks(EV)[0]
    with pytest.raises(ValueError):
        F.render_launcher(t, EV, HRR, FIXR, F.MAX_ATTEMPTS + 1)
    with pytest.raises(ValueError):
        F.render_signer([], {}, {}, F.MAX_ATTEMPTS + 1)


def test_the_signer_is_a_separate_call_on_the_frozen_transport():
    script = F.render_signer([("x", "0" * 64)], {"n": 1}, {"x": "{}"})
    assert json.dumps(K.MODEL) in script
    assert json.dumps(K.EFFORT) in script
    assert json.dumps(K.AGENT_TYPE) in script
    assert "claude-fable" not in script
    assert "a4-final-signer" in script
