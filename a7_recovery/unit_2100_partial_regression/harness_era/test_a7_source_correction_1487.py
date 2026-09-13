# -*- coding: utf-8 -*-
"""A4 TARGETED SOURCE-CORRECTION FREEZE (Codex SEQ 1487). Test first, zero calls.

Three owners, none new in kind:
  * the reviewed scratch materializer scratchpad/lock/build_final_lock.py gains
    ONE reconciliation change kind, `rebind`, in a versioned seam beside it
    (build_final_lock_v2): an existing source item's binding fields (`quote`,
    and where changed `raw_label_or_claim`) are replaced, bound to the COMPLETE
    old record and its hash, fed by the verified 1486 receipt as data;
  * a targeted phase-one packet, built beside the lock-bound
    build_kfields_key through its own renderers, whose target set is the exact
    frozen-to-corrected inventory diff;
  * the next A4 correction ledger, prepared and empty, deriving the same key.

Every refusal is proved RED on a mutated copy; history is never written.
"""
import ast
import collections
import copy
import difflib
import hashlib
import io
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
_SCRATCH = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
            "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")

import a6_launch_freeze as A6                                    # noqa: E402
import a7_g1_build as G                                          # noqa: E402
import a7_key_correction as KC                                   # noqa: E402
import build_kfields_hard_review as HR                           # noqa: E402
import build_kfields_key as K                                    # noqa: E402
import build_kfields_key_targeted as T                           # noqa: E402
_before_historical_import = list(sys.path)
try:
    import build_final_lock_v2 as L2                             # noqa: E402
finally:
    # The old materializer prepends its old harness. That is local historical
    # test setup, never permission to redirect subsequent current imports.
    sys.path[:] = _before_historical_import
import raw_transport as RT                                       # noqa: E402
import validate_benchmark_inventory as INV                       # noqa: E402

RECEIPT = "/tmp/a7_source_locator_audit_1486.json"
V2 = L2.VERSIONED_INVENTORY
V10 = "/tmp/a7_key_v10_correction.json"
BUDGET = "/tmp/a7_budget_receipt_1487.json"
FROZEN_PKG = os.path.join(K.PKG_DIR, "phase1.manifest.json")
STOPPED_FIN = "/tmp/a7_v3_prepared_run_1479/finalization.json"

_needs_receipt = pytest.mark.skipif(not os.path.isfile(RECEIPT),
                                    reason="the 1486 receipt is absent")
_needs_v2 = pytest.mark.skipif(not os.path.isfile(V2),
                               reason="the versioned inventory is not built")


def _load(path):
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


@pytest.fixture(scope="module")
def frozen():
    return _load(INV.INV)


@pytest.fixture(scope="module")
def receipt():
    return _load(RECEIPT)


@pytest.fixture(scope="module")
def base():
    """The v1 derivation: rows exactly equal to the frozen records."""
    rows, sidecar, raws, locator, problems = L2.base_rows()
    assert problems == []
    return rows


# =========================================== 1. the rebind seam, refusals RED
@_needs_receipt
def test_rebind_changes_are_bound_to_the_complete_old_record(frozen, receipt):
    changes = L2.rebind_changes(receipt, frozen)
    assert len(changes) == 11
    for c in changes:
        assert c["op"] == L2.REBIND
        n = c["record_index"]
        assert c["before"] == frozen["records"][n]
        assert c["before_sha256"] == L2.record_sha(frozen["records"][n])
        assert set(c["after"]) <= {"quote", "raw_label_or_claim"} and c["after"]
        assert receipt["receipt_sha256"] in c["owner"]
    claims = [c for c in changes if "raw_label_or_claim" in c["after"]]
    assert len(claims) == 1 and claims[0]["after"]["raw_label_or_claim"] == \
        claims[0]["before"]["quote"]


@_needs_receipt
@pytest.mark.parametrize("label,mutate,expect", [
    ("stale target",
     lambda c: c["before"].__setitem__("quote", c["before"]["quote"] + " "),
     "stale"),
    ("stale hash",
     lambda c: c.__setitem__("before_sha256", "0" * 64), "stale"),
    ("extra field",
     lambda c: c["after"].__setitem__("proposed_record_kind", "real_item"),
     "field"),
    ("missing source bytes",
     lambda c: c["after"].__setitem__("quote", c["after"]["quote"] + "ZZZ"),
     "occur"),
    ("invalid location (not unique)",
     lambda c: c["after"].__setitem__(
         "quote", "Total operating revenues as reported $ 13,912 $ 12,551"),
     "occur"),
    ("claim outside the new quote",
     lambda c: c["after"].__setitem__("raw_label_or_claim", "nowhere at all"),
     "claim"),
])
def test_an_unsupported_patch_REFUSES(frozen, receipt, base, label, mutate,
                                      expect):
    changes = L2.rebind_changes(receipt, frozen)
    first = copy.deepcopy(changes[0])
    mutate(first)
    rows = copy.deepcopy(base)
    problems = L2.apply_rebinds(rows, [first])
    assert problems, label
    assert any(expect in p for p in problems), (label, problems[:2])
    # and the lawful change beside it still applies cleanly
    rows = copy.deepcopy(base)
    assert L2.apply_rebinds(rows, [changes[0]]) == []


@_needs_receipt
def test_an_unowned_difference_REFUSES(frozen, receipt, base):
    changes = L2.rebind_changes(receipt, frozen)
    rows = copy.deepcopy(base)
    assert L2.apply_rebinds(rows, changes) == []
    records = L2.records_of(rows)
    assert L2.unowned_difference_problems(records, frozen, changes) == []
    records[3]["proposed_hard_classes"] = []            # nobody declared this
    bad = L2.unowned_difference_problems(records, frozen, changes)
    assert bad and any("unowned" in p for p in bad), bad


@_needs_receipt
def test_the_materialization_is_exactly_the_eleven(frozen, receipt):
    out = L2.materialize(receipt)
    assert out["problems"] == []
    inv = json.loads(out["inventory_text"])
    assert INV.check(inv) == []
    assert inv["counts"] == frozen["counts"]
    diff = L2.census(frozen, inv)
    assert diff["records"] == 196 and diff["changed_records"] == 11
    assert diff["quote"] == 11 and diff["raw_label_or_claim"] == 1
    assert diff["other_fields"] == 0
    assert [r["source_id"] for r in inv["records"]] == \
        [r["source_id"] for r in frozen["records"]]


@_needs_receipt
def test_double_build_is_deterministic_and_history_is_untouched(tmp_path,
                                                                receipt):
    before = {p: _sha(p) for p in (INV.INV, KC.LEDGER_PATH, STOPPED_FIN,
                                   RECEIPT) if os.path.isfile(p)}
    a = L2.build(str(tmp_path / "one"), receipt)
    b = L2.build(str(tmp_path / "two"), receipt)
    assert a["hashes"] == b["hashes"]
    assert os.path.isfile(os.path.join(str(tmp_path / "one"),
                                       "final_inventory.json"))
    assert {p: _sha(p) for p in before} == before


# ============================================ 2. the targeted phase-one packet
@_needs_v2
def test_targets_are_the_exact_frozen_to_corrected_diff(frozen, receipt):
    targets = T.targets(V2)
    want = [r["packet_id"] for r in receipt["rows"]
            if r.get("outcome") == "EXTENDABLE"]
    assert targets == want and len(targets) == 11
    assert T.targets(INV.INV) == []                     # no diff, no targets


@_needs_v2
def test_a_corrected_inventory_with_an_unapproved_difference_REFUSES(tmp_path):
    doc = _load(V2)
    doc["records"][5]["proposed_record_kind"] = "negative_control"
    bad = str(tmp_path / "bad.json")
    with io.open(bad, "w", encoding="utf-8") as fh:
        json.dump(doc, fh)
    with pytest.raises(ValueError) as exc:
        T.targets(bad)
    assert "only" in str(exc.value)


@_needs_v2
def test_targeted_items_carry_the_corrected_binding_and_the_same_drafts():
    corrected = {n: r for n, r in enumerate(_load(V2)["records"])}
    items = T.targeted_items(V2)
    frozen_items = {i["packet_id"]: i for i in K.phase1_items()}
    assert len(items) == 11
    for it in items:
        n = int(it["packet_id"].rsplit("#", 1)[1])
        assert it["quote"] == corrected[n]["quote"]
        assert it["raw_label_or_claim"] == corrected[n]["raw_label_or_claim"]
        old = frozen_items[it["packet_id"]]
        assert it["a3_drafts"] == old["a3_drafts"]
        assert it["part_ref"] == old["part_ref"]
        assert it["quote"] != old["quote"]


@_needs_v2
def test_targeted_prompts_differ_from_the_frozen_ones_only_in_the_item_block():
    frozen_items = {i["packet_id"]: i for i in K.phase1_items()}
    for it in T.targeted_items(V2):
        old = K.phase1_prompt(frozen_items[it["packet_id"]]).splitlines()
        new = K.phase1_prompt(it).splitlines()
        i_mark, d_mark = old.index(K.ITEM_MARK), old.index(K.DRAFTS_MARK)
        assert old[:i_mark + 1] == new[:new.index(K.ITEM_MARK) + 1]
        assert old[d_mark:] == new[new.index(K.DRAFTS_MARK):]
        changed = [l for l in difflib.unified_diff(old, new, lineterm="", n=0)
                   if l[:1] in "+-" and l[:3] not in ("+++", "---")]
        assert changed, it["packet_id"]
        assert all('"quote"' in l or '"raw_label_or_claim"' in l
                   for l in changed), changed[:4]


@_needs_v2
def test_the_targeted_package_is_the_phase1_shape_with_only_approved_bytes(
        tmp_path):
    doc = T.build_targeted(str(tmp_path / "pkg"), V2)
    frozen_doc = _load(FROZEN_PKG)
    assert set(doc) - {"correction", "manifest_sha256"} == \
        set(frozen_doc) - {"manifest_sha256"} or \
        set(doc) - {"correction", "manifest_sha256"} == set(frozen_doc)
    assert doc["calls"] == 11 and doc["door"] == frozen_doc["door"]
    assert doc["rules_sha256"] == frozen_doc["rules_sha256"]
    assert doc["transport"] == frozen_doc["transport"]
    assert doc["a3_binding"] == frozen_doc["a3_binding"]
    assert doc["inventory_sha256"] == _sha(V2)
    assert doc["correction"]["frozen_inventory_sha256"] == _sha(INV.INV)
    assert [r["packet_id"] for r in doc["items"]] == T.targets(V2)
    frozen_by = {r["packet_id"]: r for r in frozen_doc["items"]}
    for r in doc["items"]:
        assert r["prompt_sha256"] != frozen_by[r["packet_id"]]["prompt_sha256"]
        assert r["drafts"] == frozen_by[r["packet_id"]]["drafts"]
    assert T.package_problems(str(tmp_path / "pkg")) == []
    man = os.path.join(str(tmp_path / "pkg"), "phase1.manifest.json")
    d = _load(man)
    d["items"][0]["prompt_sha256"] = "0" * 64
    with io.open(man, "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=1)
    assert T.package_problems(str(tmp_path / "pkg"))


@_needs_v2
def test_prepare_run_writes_a_write_once_receipt_naming_exactly_the_targets(
        tmp_path, monkeypatch):
    pkg = str(tmp_path / "pkg")
    T.build_targeted(pkg, V2)
    run = str(tmp_path / "run")
    monkeypatch.setattr(T, "PKG_DIR", pkg)
    # The historical public `publish` bypass was removed. Exercise the one
    # receipt owner with an explicit already-checked TEST package context;
    # the public preflight refusal is tested separately below.
    context = {"dir": pkg, "items": T.targeted_items(V2)}
    keys = K._canonical_keys(context)
    K._write_receipt(run, 1, keys, pkg=context)
    got = {"ok": True, "invocations": K._invocations(keys, 1, context)}
    assert got["ok"], got["problems"][:3]
    receipt = _load(os.path.join(run, K.RECEIPT_NAME))
    assert receipt["allowed"] == T.targets(V2)
    assert receipt["attempt"] == 1 and receipt["states"] == []
    assert set(receipt) == set(K.RECEIPT_IMMUTABLE) | {"states"}
    man = _load(os.path.join(pkg, "phase1.manifest.json"))
    assert receipt["prompts"] == {r["packet_id"]: r["prompt_sha256"]
                                  for r in man["items"]}
    assert K._receipt_problems(run, receipt, context) == []
    assert len(got["invocations"]) == 11
    assert all(inv["attempt"] == 1 for inv in got["invocations"])
    again = T.prepare_run(run)                        # not fresh: refused
    assert not again["ok"] and "fresh" in again["problems"][0]
    assert K.MAX_ATTEMPTS == 2                         # one identical retry


@_needs_v2
def test_prepare_run_is_gated_by_the_lock_bound_preflight_which_refuses_today(
        tmp_path, monkeypatch):
    """An old unapproved package cannot prepare a current targeted run.

    The current source-approval gate refuses before writing any run artifact.
    The native key lifecycle provides the corresponding approved control.
    """
    pkg = str(tmp_path / "pkg")
    T.build_targeted(pkg, V2)
    run = str(tmp_path / "run")
    monkeypatch.setattr(T, "PKG_DIR", pkg)
    got = T.prepare_run(run)
    assert not got["ok"] and got["invocations"] == []
    # The current owner requires an independently bound source approval;
    # this historical package has none. No old dependency-pin bypass exists.
    assert any("no read-only approved source lock" in p for p in got["problems"]), \
        got["problems"][:3]
    assert not os.path.exists(run)


def test_the_targeted_builder_cannot_see_the_key():
    """No hidden key: the module imports nothing that derives or holds it."""
    src = io.open(os.path.join(_HERE, "build_kfields_key_targeted.py"),
                  encoding="utf-8").read()
    names = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    forbidden = {"a7_key_correction", "a7_g1_build", "a7_g23_build",
                 "a7_g23_run", "build_kfields_final", "a7_prepared_run"}
    assert not (names & forbidden), names & forbidden


# ============================================= 3. the ledger shell and budget
@pytest.mark.skipif(not os.path.isfile(V10), reason="v10 shell not prepared")
def test_the_v10_ledger_shell_derives_exactly_the_v9_key():
    v9, v10 = KC.load(), _load(V10)
    assert v10["rows"] == v9["rows"] and v10["schema"] == v9["schema"]
    assert v10["parent"]["sha256"] == _sha(KC.LEDGER_PATH)
    assert v10["source_correction"]["inventory_sha256"] == _sha(V2)
    assert len(v10["pending_targets"]) == 11 and v10["pending_results"] == []
    base, _s = G.gold_by_event()
    k9, p9 = KC.apply(base, v9)
    k10, p10 = KC.apply(base, v10)
    assert p9 == [] and p10 == []
    assert G._plain(k9) == G._plain(k10)


@pytest.mark.skipif(not os.path.isfile(BUDGET), reason="budget not derived")
def test_the_budget_receipt_is_derived_from_live_owners():
    b = _load(BUDGET)
    assert b["completed_before"] == A6.ledger()[0]
    assert b["ceiling"] == G.CEILING
    rows = {r["stage"]: r for r in b["stages"]}
    assert rows["key_review"]["max_attempts"] == K.MAX_ATTEMPTS
    assert rows["hard_review"]["blinds"] == len(HR.BLINDS)
    lim = RT.a1_limits(RT.a1_plan_for_run("/tmp/a7_v3_prepared_run_1479"))
    assert rows["producer"]["primaries"] == lim["primary_calls"]
    assert rows["producer"]["max"] == lim["all_in_max"]
    assert rows["g1"]["lanes"] == len(G.GRADER_LANES)
    assert b["minimum_total"] == b["completed_before"] + sum(
        r["min"] for r in b["stages"])
    derivable = [r for r in b["stages"] if r["max"] is not None]
    assert [r["stage"] for r in b["stages"] if r["max"] is None] == ["g3"]
    assert b["maximum_total"] == b["completed_before"] + sum(
        r["max"] for r in derivable)
    assert b["maximum_fits_ceiling"] == (b["maximum_total"] <= b["ceiling"])
    assert rows["g1"]["shape_from_frozen_completion"] > 0
    assert b["smallest_lawful_predeclared_bound"]["bound"] == b["ceiling"]
    assert b["calls_armed"] == 0
