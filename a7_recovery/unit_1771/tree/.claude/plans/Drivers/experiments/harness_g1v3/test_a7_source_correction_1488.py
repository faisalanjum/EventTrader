# -*- coding: utf-8 -*-
"""RUNNABLE SINGLE LIFECYCLE, RE-ESTABLISHED A3 GATE, BOUND BUDGET AND BOUND
INPUT (Codex SEQ 1488). Test first, zero calls.

  1. build_kfields_key's ONE lifecycle is generalized over a small package
     context; the frozen default is the context's default. The targeted module
     has exactly one gated prepare door and no ungated publication.
  2. The A3 dependency probe imports the same tree the lifecycle imports; a
     versioned baseline beside the old one binds the gate to that tree.
  3. The budget reads the latest accepted G2/G3 artifacts and the targeted
     manifest carries a hash-bound stage budget; package_problems compares
     the whole rebuilt manifest.
  4. The correction owner binds the reviewed receipt by exact file hash and
     recomputed digest and validates its 196-row packet identity.

Every proof below is on a fresh temp tree or a disposable copy; the frozen
inventory, key, runs and history are never written.
"""
import copy
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

import subprocess                                                # noqa: E402

import a1_reader                                                 # noqa: E402
import audit_worker_access as AUD                                # noqa: E402
import build_kfields_key as K                                    # noqa: E402
import build_kfields_key_targeted as T                           # noqa: E402
import raw_transport as RT                                       # noqa: E402
import validate_benchmark_inventory as INV                       # noqa: E402
import test_kfields_key_1363 as TK                               # noqa: E402
if os.path.join(_SCRATCH, "lock") not in sys.path:
    sys.path.insert(0, os.path.join(_SCRATCH, "lock"))
import build_final_lock_v2 as L2                                 # noqa: E402

BUDGET = T.BUDGET_RECEIPT
STOPPED_FIN = "/tmp/a7_v3_prepared_run_1479/finalization.json"
G3 = "/tmp/a7_g3_candidate/a7_g1_candidate.json"
G2 = "/tmp/a7_g2_candidate/a7_g1_candidate.json"


def _load(path):
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _clean_ledger():
    """The live ledger from a CLEAN interpreter: this module's own imports
    (the scratch lock path drags the old harness tree in) must never decide
    which a7_g1_build the ledger owner resolves (Codex SEQ 1489 item E)."""
    out = subprocess.run(
        [sys.executable, "-B", "-c",
         "import sys; sys.path.insert(0, %r); sys.path.insert(0, "
         "'/home/faisal/EventMarketDB'); import a6_launch_freeze as A6; "
         "print(A6.ledger()[0])" % _HERE],
        capture_output=True, text=True, cwd="/home/faisal/EventMarketDB")
    assert out.returncode == 0, out.stderr[-400:]
    return int(out.stdout.strip())


def _sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


@pytest.fixture
def official(tmp_path, monkeypatch):
    """The 1363 fixture, verbatim: a temp tree the location owner accepts."""
    session = tmp_path / "projects" / K.PARENT_SESSION
    (session / "workflows").mkdir(parents=True)
    real = AUD._official_location

    def located(state_path):
        p = os.path.realpath(str(state_path))
        if p.startswith(os.path.realpath(str(session))):
            return str(session), K.PARENT_SESSION
        return real(state_path)
    monkeypatch.setattr(AUD, "_official_location", located)
    return session


@pytest.fixture(scope="module")
def items():
    return T.targeted_items(T.CORRECTED_INVENTORY)


def _call(session, item, answer, **kw):
    return TK.build_call(session, item, answer, **kw)


# ============================================ 1. one lifecycle, one gated door
def test_the_targeted_module_has_one_gated_door_and_no_ungated_publication():
    assert not hasattr(T, "publish")
    assert not hasattr(T, "expected_receipt") and not hasattr(T, "receipt_problems")
    assert callable(T.prepare_run) and callable(T.finalize)
    assert T.record_state is K.record_state


def test_the_frozen_default_context_is_unchanged():
    pkg = K._pkg(None)
    assert pkg["dir"] == K.PKG_DIR
    assert [i["packet_id"] for i in pkg["items"]] == \
        [i["packet_id"] for i in K.phase1_items()]
    assert K.canonical_keys() == K._canonical_keys(None)


def test_a_valid_targeted_primary_finalizes_through_the_shared_lifecycle(
        tmp_path, official, items):
    states = [_call(official, it, TK.lawful_answer(it), run_id="wf_%03d" % n)
              for n, it in enumerate(items)]
    run = str(tmp_path / "run")
    got = T.prepare_run(run)
    assert got["ok"], got["problems"][:3]
    assert [inv["packet_id"] for inv in got["invocations"]] == \
        [i["packet_id"] for i in items]
    receipt = _load(os.path.join(run, K.RECEIPT_NAME))
    assert receipt["allowed"] == [i["packet_id"] for i in items]
    assert receipt["manifest_sha256"] == _sha(os.path.join(T.PKG_DIR, T.PKG_NAME))
    for s in states:
        assert T.record_state(run, s) == []
    doc = T.finalize(run)
    assert doc["problems"] == [], doc["problems"][:3]
    assert doc["primary_complete"] is True
    assert doc["ledger"] == {"scheduled": len(items), "valid": len(items),
                             "invalid_response": 0, "transport_no_answer": 0,
                             "unproved": 0, "missing": 0}
    assert doc["retry"] == [] and "child" not in doc
    raw = sorted(os.listdir(os.path.join(run, "raw")))
    assert len([n for n in raw if n.endswith(".raw.json")]) == len(items)
    first = _sha(os.path.join(run, K.FINALIZATION_NAME))
    with pytest.raises(ValueError):                    # write-once
        T.finalize(run)
    assert _sha(os.path.join(run, K.FINALIZATION_NAME)) == first
    assert io.open(os.path.join(run, K.FINALIZATION_NAME),
                   encoding="utf-8").read() == json.dumps(doc, indent=1)


def test_one_invalid_primary_earns_exactly_one_identical_child_and_no_third(
        tmp_path, official, items):
    states = []
    for n, it in enumerate(items):
        answer = "{not json" if n == 2 else TK.lawful_answer(it)
        states.append(_call(official, it, answer, run_id="wf_%03d" % n))
    run = str(tmp_path / "run")
    assert T.prepare_run(run)["ok"]
    for s in states:
        assert T.record_state(run, s) == []
    doc = T.finalize(run)
    assert doc["problems"] == [] and doc["primary_complete"] is True
    assert doc["ledger"]["valid"] == len(items) - 1
    assert doc["ledger"]["invalid_response"] == 1
    assert doc["retry"] == [items[2]["packet_id"]]
    child = doc["child"]
    assert len(child["invocations"]) == 1
    assert child["invocations"][0]["packet_id"] == items[2]["packet_id"]
    assert child["invocations"][0]["attempt"] == 2
    crec = _load(os.path.join(child["dir"], K.RECEIPT_NAME))
    assert crec["allowed"] == [items[2]["packet_id"]]     # never re-asks the rest
    assert crec["parent"]["finalization_sha256"] == \
        _sha(os.path.join(run, K.FINALIZATION_NAME))
    # the child answers lawfully at attempt 2 and closes with NO successor
    s2 = _call(official, items[2], TK.lawful_answer(items[2]), attempt=2,
               run_id="wf_child")
    assert T.record_state(child["dir"], s2) == []
    cdoc = T.finalize(child["dir"])
    assert cdoc["problems"] == [], cdoc["problems"][:3]
    assert cdoc["ledger"]["valid"] == 1 and cdoc["retry"] == []
    assert "child" not in cdoc
    # attempt 3 cannot exist
    third = str(tmp_path / "third")
    K._write_receipt(third, 3, [items[2]["packet_id"]], pkg=T._ctx())
    assert any("outside 1..2" in p for p in T.finalize(third)["problems"])


@pytest.mark.parametrize("what", ["foreign_location", "tampered_prompt",
                                  "wrong_script"])
def test_a_missing_foreign_or_tampered_state_is_unproved_and_never_credited(
        tmp_path, official, items, what):
    it = items[0]
    if what == "foreign_location":
        state = str(tmp_path / "elsewhere.json")
        TK.build_call(official, it, TK.lawful_answer(it), run_id="wf_x")
        os.replace(str(official / "workflows" / "wf_x.json"), state)
    elif what == "tampered_prompt":
        def tamper(recs):
            recs[0]["message"]["content"] += " x"
        state = _call(official, it, TK.lawful_answer(it), run_id="wf_x",
                      rec_mutate=tamper)
    else:
        def wrong(doc):
            doc["script"] = doc["script"] + "\n// drift\n"
        state = _call(official, it, TK.lawful_answer(it), run_id="wf_x",
                      doc_mutate=wrong)
    run = str(tmp_path / "run")
    assert T.prepare_run(run)["ok"]
    assert T.record_state(run, state) == []
    doc = T.finalize(run)
    outcomes = {k: o for k, o, _w in doc["outcomes"]}
    assert outcomes[it["packet_id"]] == "unproved", what
    assert doc["ledger"]["valid"] == 0 and doc["retry"] == []
    assert "child" not in doc
    # raw text was preserved BEFORE any proof ran
    raw = os.listdir(os.path.join(run, "raw"))
    assert any(n.endswith(".raw.json") for n in raw), raw


def test_receipt_or_package_drift_refuses_and_keeps_raw(tmp_path, official,
                                                         items, monkeypatch):
    it = items[0]
    state = _call(official, it, TK.lawful_answer(it), run_id="wf_x")
    run = str(tmp_path / "run")
    assert T.prepare_run(run)["ok"]
    assert T.record_state(run, state) == []
    rpath = os.path.join(run, K.RECEIPT_NAME)
    rec = _load(rpath)
    rec["rules_sha256"] = "0" * 64
    io.open(rpath, "w", encoding="utf-8").write(json.dumps(rec))
    doc = T.finalize(run)
    assert any("receipt.rules_sha256" in p for p in doc["problems"])
    assert doc["ledger"]["valid"] == 0 and doc["retry"] == []
    assert any(n.endswith(".raw.json")
               for n in os.listdir(os.path.join(run, "raw")))


# ================================================= 2. the A3 gate, re-founded
def test_the_a3_probe_hashes_the_tree_the_lifecycle_imports():
    base = _load(K.A3_BASELINE)
    assert os.path.basename(K.A3_BASELINE) != "a3_baseline.json"
    assert os.path.isfile(K.A3_BASELINE_V1)
    files = base["files"]
    for mod in (RT, AUD, a1_reader, INV, K.BLM):
        rel = os.path.relpath(os.path.realpath(mod.__file__),
                              os.path.realpath(K._X))
        assert rel in files, (mod.__name__, rel)
        assert files[rel] == _sha(mod.__file__), mod.__name__
        assert rel.split(os.sep)[0] == os.path.basename(_HERE)
    plan_rel = os.path.relpath(os.path.realpath(RT.a1_plan_path()),
                               os.path.realpath(K._X))
    assert files[plan_rel] == _sha(RT.a1_plan_path())
    assert K.a3_dependency_digest() == base["digest"]
    assert K.a3_problems() == []
    assert base["primary_problems"] == []
    assert base["previous"]["path"] == K.A3_BASELINE_V1
    assert base["previous"]["sha256"] == _sha(K.A3_BASELINE_V1)
    assert base["previous"]["changes"], "the historical changes are enumerated"
    for c in base["previous"]["changes"]:
        assert c["status"] in ("renamed_same_bytes", "changed", "added",
                               "removed")


def test_preflight_passes_on_the_current_tree_and_still_guards_it(monkeypatch):
    assert K.preflight()["problems"] == []
    monkeypatch.setattr(K, "a3_dependency_digest", lambda: "0" * 64)
    assert any("A3 dependency byte moved" in p
               for p in K.preflight()["problems"])
    assert any("A3 dependency byte moved" in p
               for p in K._preflight(T._ctx())["problems"])


def test_all_392_a3_answers_reaudit_clean_and_their_hashes_are_the_frozen_ones():
    ev = K.a3_evidence()
    assert ev["problems"] == []
    assert len(ev["answers"]) == 392
    frozen = _load(os.path.join(K.PKG_DIR, "phase1.manifest.json"))
    assert ev["binding"] == frozen["a3_binding"]


# ================================================= 3. budget and whole-manifest
def test_the_budget_reads_the_latest_g2_g3_artifacts_and_names_the_unknown():
    b = _load(BUDGET)
    s = {r["stage"]: r for r in b["stages"]}
    assert s["g3"]["shape_artifact"] == G3 and s["g3"]["shape_artifact_sha256"] == _sha(G3)
    assert s["g2"]["shape_artifact"] == G2 and s["g2"]["shape_artifact_sha256"] == _sha(G2)
    assert s["g3"]["shape"] == _load(G3)["launchers"]["count"]
    assert s["g2"]["shape"] == _load(G2)["launchers"]["count"]
    # the 1488 receipt is HISTORY (see the 1487 note): self-consistent, and
    # the live ledger has since lawfully advanced past it
    assert b["completed_before"] == sum(r["calls"] for r in b["completed_rows"])
    assert _clean_ledger() >= b["completed_before"]
    assert b["expected_shape_total"] == b["completed_before"] + sum(
        r["shape"] for r in b["stages"])
    assert b["headroom_at_shape"] == b["ceiling"] - b["expected_shape_total"]
    assert "known_maximum_subtotal" in b and b["absolute_maximum"] is None
    assert "maximum_total" not in b
    assert b["calls_armed"] == 0


def test_the_manifest_carries_a_hash_bound_stage_budget_not_the_obsolete_one():
    doc = _load(os.path.join(T.PKG_DIR, T.PKG_NAME))
    b = doc["budget"]
    receipt = _load(BUDGET)
    assert b["budget_receipt_sha256"] == _sha(BUDGET)
    assert b["before"] == receipt["completed_before"]
    assert b["ceiling"] == receipt["ceiling"]
    assert b["primaries"] == doc["calls"] and b["after"] == b["before"] + b["primaries"]
    assert b["worst_case_after"] == b["before"] + b["primaries"] * K.MAX_ATTEMPTS
    assert b["before"] != 3990


@pytest.mark.parametrize("path,value", [
    (("budget", "before"), 3990),
    (("correction", "targets", 0, "record_index"), 999),
    (("launch", "prepare"), "somewhere else"),
    (("items", 0, "prompt_sha256"), "0" * 64),
    (("calls",), 12),
])
def test_package_problems_compares_the_whole_rebuilt_manifest(tmp_path, path,
                                                              value):
    pkg = str(tmp_path / "pkg")
    T.build_targeted(pkg)
    assert T.package_problems(pkg) == []
    man = os.path.join(pkg, T.PKG_NAME)
    doc = _load(man)
    node = doc
    for k in path[:-1]:
        node = node[k]
    node[path[-1]] = value
    io.open(man, "w", encoding="utf-8").write(json.dumps(doc, indent=1))
    assert T.package_problems(pkg), path


def test_the_targeted_package_double_builds_identically(tmp_path):
    a = T.build_targeted(str(tmp_path / "a"))
    b = T.build_targeted(str(tmp_path / "b"))
    assert a["manifest_sha256"] == b["manifest_sha256"]
    assert a["manifest_sha256"] == _sha(os.path.join(T.PKG_DIR, T.PKG_NAME))


# ============================================== 4. the bound correction input
def test_the_source_receipt_is_bound_by_file_hash_digest_and_packet_identity(
        tmp_path):
    doc, file_sha, digest = L2.load_receipt(L2.RECEIPT_PATH)
    assert file_sha == L2.SOURCE_RECEIPT_SHA256 == _sha(L2.RECEIPT_PATH)
    assert digest == doc["receipt_sha256"]
    text = io.open(L2.RECEIPT_PATH, encoding="utf-8").read()
    # one byte
    p = str(tmp_path / "one_byte.json")
    io.open(p, "w", encoding="utf-8").write(text + " ")
    with pytest.raises(ValueError) as exc:
        L2.load_receipt(p)
    assert "file sha256" in str(exc.value)
    # a packet identity mismatch under the pinned hash is impossible; prove the
    # identity check itself on a copy with the pin lifted
    bad = json.loads(text)
    bad["rows"][5]["packet_id"] = bad["rows"][6]["packet_id"]
    p2 = str(tmp_path / "ids.json")
    io.open(p2, "w", encoding="utf-8").write(json.dumps(bad, ensure_ascii=False))
    with pytest.raises(ValueError) as exc2:
        L2.load_receipt(p2, expected_file_sha256=_sha(p2))
    assert "packet identity" in str(exc2.value) or "digest" in str(exc2.value)
    out = L2.materialize(L2.RECEIPT_PATH)
    assert out["problems"] == []
    corr = json.loads(out["correction_text"])
    assert corr["source_receipt"]["file_sha256"] == file_sha
    assert corr["source_receipt"]["receipt_sha256"] == digest


def test_no_module_writes_a_published_artifact_outside_the_write_once_owner():
    for name in (os.path.join(_HERE, "build_kfields_key_targeted.py"),
                 os.path.join(_SCRATCH, "lock", "build_final_lock_v2.py")):
        src = io.open(name, encoding="utf-8").read()
        assert '"w"' not in src and "'w'" not in src, name
        assert "write_new(" in src


def test_history_is_untouched():
    for p, sha in ((INV.INV, "57a1cdd01125bc1953a4e31c3f534760c2c15eaea4bf2d10c5c451a5e36d03ff"),):
        assert _sha(p) == sha
    assert os.path.isfile(STOPPED_FIN)
    assert _sha(K.A3_BASELINE_V1) == _load(K.A3_BASELINE)["previous"]["sha256"]


def test_the_manifest_binds_the_reviewed_receipt_through_the_correction_receipt():
    doc = _load(os.path.join(T.PKG_DIR, T.PKG_NAME))
    c = doc["correction"]
    assert c["correction_receipt_sha256"] == _sha(T.CORRECTION_RECEIPT)
    assert c["source_receipt"]["file_sha256"] == L2.SOURCE_RECEIPT_SHA256
    cr = _load(T.CORRECTION_RECEIPT)
    assert c["source_receipt"] == cr["source_receipt"]
    assert cr["outputs"]["final_inventory.json"] == c["corrected_inventory_sha256"]
    assert c["corrected_inventory_sha256"] == _sha(T.CORRECTED_INVENTORY)
    assert c["frozen_inventory_sha256"] == _sha(INV.INV)


def test_a_missing_state_is_refused_at_record_and_counted_missing_at_close(
        tmp_path, official, items):
    run = str(tmp_path / "run")
    assert T.prepare_run(run)["ok"]
    assert T.record_state(run, str(tmp_path / "nowhere.json")) != []
    doc = T.finalize(run)
    assert doc["ledger"]["missing"] == len(items)
    assert doc["ledger"]["valid"] == 0 and doc["retry"] == []
    assert "child" not in doc


def test_package_drift_refuses_at_the_one_door_before_any_receipt(
        tmp_path, monkeypatch):
    pkg = str(tmp_path / "pkg")
    T.build_targeted(pkg)
    man = os.path.join(pkg, T.PKG_NAME)
    doc = _load(man)
    doc["budget"]["before"] = 3990
    io.open(man, "w", encoding="utf-8").write(json.dumps(doc, indent=1))
    monkeypatch.setattr(T, "PKG_DIR", pkg)
    run = str(tmp_path / "run")
    got = T.prepare_run(run)
    assert got["ok"] is False and got["invocations"] == []
    assert any("manifest.budget" in p for p in got["problems"])
    assert not os.path.exists(os.path.join(run, K.RECEIPT_NAME))


def test_the_child_call_is_the_identical_prompt_from_the_one_renderer(
        tmp_path, official, items):
    states = []
    for n, it in enumerate(items):
        answer = "{not json" if n == 2 else TK.lawful_answer(it)
        states.append(_call(official, it, TK.lawful_answer(it) if n != 2
                            else answer, run_id="wf_%03d" % n))
    run = str(tmp_path / "run")
    got = T.prepare_run(run)
    assert got["invocations"][2]["script"] == K.render_launcher(items[2], 1)
    for s in states:
        assert T.record_state(run, s) == []
    doc = T.finalize(run)
    child = doc["child"]["invocations"][0]
    assert child["script"] == K.render_launcher(items[2], 2)
    # the same item through the same renderer; only the attempt mark differs
    assert child["script"] != got["invocations"][2]["script"]


@pytest.mark.parametrize("what", ["narrowed", "reordered", "foreign", "frozen_items"])
def test_the_caller_cannot_choose_a_subset_through_the_context(tmp_path, items,
                                                                what):
    """The SEQ 1363 law survives the context: only the built package's own
    items, in order, pass; anything the caller narrows or swaps refuses."""
    if what == "narrowed":
        ctx = {"dir": T.PKG_DIR, "items": items[:3]}
    elif what == "reordered":
        ctx = {"dir": T.PKG_DIR, "items": list(reversed(items))}
    elif what == "foreign":
        ctx = {"dir": str(tmp_path), "items": items}
    else:
        ctx = {"dir": T.PKG_DIR, "items": K.phase1_items()[:len(items)]}
    run = str(tmp_path / "run")
    if what == "foreign":
        with pytest.raises((ValueError, IOError, OSError)):
            K._prepare_run(run, ctx)
    else:
        got = K._prepare_run(run, ctx)
        assert got["ok"] is False and got["invocations"] == []
        assert any("cannot choose the items" in p for p in got["problems"])
    assert not os.path.exists(os.path.join(run, K.RECEIPT_NAME))
