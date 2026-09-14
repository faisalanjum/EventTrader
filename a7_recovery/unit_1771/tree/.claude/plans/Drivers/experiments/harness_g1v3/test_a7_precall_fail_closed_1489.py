# -*- coding: utf-8 -*-
"""PRE-CALL FAIL-CLOSED AND TRACE CORRECTION (Codex SEQ 1489). Test first.

  A. stored answer identity: an existing raw or proved file is recovery only
     when its bytes equal the official text; different bytes -> unproved,
     incomplete, no child, nothing overwritten.
  B. correction output identity: the correction receipt's declared outputs
     must equal the owner's actual outputs, row for row.
  C. unexpressible public subset: K.prepare_run(run_dir) / K.finalize(run_dir)
     and the targeted doors take nothing else; each launches its own full
     denominator.
  D. one full validation, then one trace: the first materialization binds
     raw bytes; a warm trace is guarded only by the run digest + file count.
  E. import order: a6_launch_freeze's lazy a7_g1_build must be this
     directory's copy; a stale preloaded copy fails closed.

Every proof runs on temp copies; no frozen run, key or inventory is written.
"""
import hashlib
import inspect
import io
import json
import os
import shutil
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
_X = os.path.dirname(_HERE)

import audit_worker_access as AUD                                # noqa: E402
import build_kfields_key as K                                    # noqa: E402
import build_kfields_key_targeted as T                           # noqa: E402
import raw_transport as RT                                       # noqa: E402
import test_kfields_key_1363 as TK                               # noqa: E402

PY = sys.executable
STOPPED = "/tmp/a7_v3_prepared_run_1479"


def _load(path):
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


@pytest.fixture
def official(tmp_path, monkeypatch):
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


def _official_text(state):
    return K.direct_result(json.loads(io.open(state, encoding="utf-8").read()))["text"]


# ======================================================= A. stored identity
@pytest.mark.parametrize("site", ["raw", "proved"])
@pytest.mark.parametrize("same", [True, False], ids=["identical", "different"])
def test_a_stored_answer_is_recovery_only_when_its_bytes_are_the_official_text(
        tmp_path, official, items, site, same):
    states = [TK.build_call(official, it, TK.lawful_answer(it), run_id="wf_%03d" % n)
              for n, it in enumerate(items)]
    run = str(tmp_path / "run")
    assert T.prepare_run(run)["ok"]
    for s in states:
        assert T.record_state(run, s) == []
    text = _official_text(states[0])
    stored = text if same else text + "\n<!-- not the official text -->"
    raw_dir = os.path.join(run, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    if site == "raw":
        path, _ = RT.save_raw(stored, raw_dir, "wf_000.000")
    else:
        path = os.path.join(raw_dir, "%s.attempt1.proved.json"
                            % items[0]["packet_id"].replace("#", "_"))
        RT.write_new(path, stored)
    before = _sha(path)
    doc = T.finalize(run)
    assert _sha(path) == before                       # evidence never overwritten
    outcomes = {k: o for k, o, _w in doc["outcomes"]}
    if same:
        assert doc["problems"] == [] and doc["primary_complete"] is True
        assert doc["ledger"]["valid"] == len(items)
    else:
        assert outcomes[items[0]["packet_id"]] == "unproved"
        assert doc["ledger"]["valid"] == len(items) - 1
        assert doc["primary_complete"] is False
        assert doc["retry"] == [] and "child" not in doc
        assert any(items[0]["packet_id"] in p for p in doc["problems"])


# ================================================= B. correction output identity
@pytest.fixture
def receipt_copy(tmp_path):
    src = os.path.dirname(T.CORRECTION_RECEIPT)
    dst = str(tmp_path / "candidate")
    shutil.copytree(src, dst)
    return os.path.join(dst, os.path.basename(T.CORRECTION_RECEIPT))


def _rewrite(path, fn):
    doc = _load(path)
    fn(doc)
    io.open(path, "w", encoding="utf-8").write(json.dumps(doc, indent=1))


def test_b_an_unaltered_receipt_copy_still_binds(receipt_copy, monkeypatch):
    monkeypatch.setattr(T, "CORRECTION_RECEIPT", receipt_copy)
    doc = T.manifest_document()
    assert doc["correction"]["correction_receipt_path"] == receipt_copy


def _mutations():
    names = sorted(_load(T.CORRECTION_RECEIPT)["outputs"])
    out = []
    for n in names:
        out.append(("changed:" + n, lambda d, n=n: d["outputs"].__setitem__(n, "0" * 64)))
        out.append(("missing:" + n, lambda d, n=n: d["outputs"].pop(n)))
    out.append(("extra", lambda d: d["outputs"].__setitem__("extra.json", "1" * 64)))
    a, b = names[0], names[1]

    def swap(d):
        d["outputs"][a], d["outputs"][b] = d["outputs"][b], d["outputs"][a]
    out.append(("swapped", swap))
    out.append(("all_zero", lambda d: d["outputs"].update(
        {k: "0" * 64 for k in d["outputs"]})))
    return out


@pytest.mark.parametrize("name,mutate", _mutations(), ids=[m[0] for m in _mutations()])
def test_b_every_declared_output_mutation_refuses(receipt_copy, monkeypatch,
                                                  name, mutate):
    _rewrite(receipt_copy, mutate)
    monkeypatch.setattr(T, "CORRECTION_RECEIPT", receipt_copy)
    with pytest.raises(ValueError) as exc:
        T.manifest_document()
    assert "output" in str(exc.value)


# ================================================ C. unexpressible public subset
def test_c_the_public_doors_take_only_the_run_directory():
    for door in (K.prepare_run, K.finalize, T.prepare_run, T.finalize):
        assert list(inspect.signature(door).parameters) == ["run_dir"], door


def test_c_each_public_door_launches_exactly_its_own_denominator(tmp_path, items):
    got = T.prepare_run(str(tmp_path / "t"))
    assert got["ok"], got["problems"][:3]
    assert [i["packet_id"] for i in got["invocations"]] == \
        [i["packet_id"] for i in items]
    got = K.prepare_run(str(tmp_path / "k"))
    assert got["ok"], got["problems"][:3]
    assert [i["packet_id"] for i in got["invocations"]] == \
        [i["packet_id"] for i in K.phase1_items()]


def test_c_a_self_consistent_one_item_package_cannot_enter_through_a_public_door(
        tmp_path, items):
    """Codex's proof 3: a private context may name a built package, but no
    PUBLIC door accepts one, so a one-item denominator is unreachable."""
    pkg = str(tmp_path / "one")
    T.build_targeted(pkg)                       # a real, self-consistent package
    with pytest.raises(TypeError):
        K.prepare_run(str(tmp_path / "run"), pkg={"dir": pkg, "items": items})
    with pytest.raises(TypeError):
        K.prepare_run(str(tmp_path / "run"), {"dir": pkg, "items": items})
    with pytest.raises(TypeError):
        T.prepare_run(str(tmp_path / "run"), {"dir": pkg, "items": items[:1]})


# ============================================= D. one validation, then one trace
import a7_conservation as C                                      # noqa: E402
import a7_g1_build as G                                          # noqa: E402
import a7_g1_complete_v2 as CV                                   # noqa: E402
import a7_prepared_run as PR                                     # noqa: E402

_trace = pytest.mark.skipif(not os.path.isdir(G.PRIMARY),
                            reason="the executed run is absent")


@pytest.fixture
def cold(monkeypatch):
    """This test's own cold trace cache; the module cache is untouched after."""
    monkeypatch.setattr(G, "_MATERIALIZED", {})


@_trace
@pytest.mark.usefixtures("historical_v1_evidence", "cold")
def test_d_first_materialization_binds_raw_bytes_and_records_the_run_identity(
        monkeypatch):
    calls = []
    real = RT.a1_raw_binding_problems

    def spy(*a, **k):
        calls.append(1)
        return real(*a, **k)
    monkeypatch.setattr(RT, "a1_raw_binding_problems", spy)
    ident = PR.load(G.PRIMARY)
    _arms, meta, problems = G.materialize(ident)
    assert problems == [], problems[:2]
    assert calls, "the first materialization did not run the raw-byte binding"
    assert G._MATERIALIZED[G._sha(G._plain(ident))]["expected"] == \
        tuple(CV.run_digest(G.PRIMARY))


@_trace
@pytest.mark.usefixtures("historical_v1_evidence", "cold")
def test_d_a_warm_trace_is_guarded_by_the_digest_owner_only(monkeypatch):
    ident = PR.load(G.PRIMARY)
    want = G.materialize(ident)[1]                        # warm
    monkeypatch.setattr(PR, "current", lambda *a, **k: pytest.fail(
        "PR.current was re-run on a warm trace"))
    monkeypatch.setattr(PR, "load", lambda *a, **k: pytest.fail(
        "PR.load was re-run on a warm trace"))
    monkeypatch.setattr(RT, "a1_raw_binding_problems", lambda *a, **k: pytest.fail(
        "raw bytes were re-bound on a warm trace"))
    real_open, inside = io.open, []
    real_digest = CV.run_digest

    def digest(run_dir):
        inside.append(True)
        try:
            return real_digest(run_dir)
        finally:
            inside.pop()

    def no_raw(path, *a, **k):
        if not inside and isinstance(path, str) and ".raw.json" in path:
            raise AssertionError("a raw answer was reopened: %s" % path)
        return real_open(path, *a, **k)
    monkeypatch.setattr(CV, "run_digest", digest)
    monkeypatch.setattr(io, "open", no_raw)
    assert G.run_of(ident) == G.PRIMARY
    assert G.materialize(ident)[1] == want
    assert G.freeze(ident)[2] == []             # the real G1 path, warm and sealed


@_trace
@pytest.mark.usefixtures("historical_v1_evidence", "cold")
def test_d_drift_after_caching_refuses_through_the_digest_owner():
    ident = PR.load(G.PRIMARY)
    G.materialize(ident)
    digest, files = CV.run_digest(G.PRIMARY)
    with pytest.MonkeyPatch.context() as m:
        # the digest owner reports one more file / a different tree
        m.setattr(CV, "run_digest", lambda run_dir: ("0" * 64, files + 1))
        with pytest.raises(ValueError) as exc:
            G.run_of(ident)
        assert "no longer measures the supplied identity" in str(exc.value)
        with pytest.raises(ValueError):
            G.materialize(ident)
    assert G.run_of(ident) == G.PRIMARY          # the real tree still holds


# ====================================================== E. import order
def _clean(code):
    return subprocess.run([PY, "-B", "-c", code], capture_output=True, text=True,
                          cwd="/home/faisal/EventMarketDB")


def test_e_a_clean_process_resolves_this_directorys_a7_g1_build():
    out = _clean(
        "import sys, os; sys.path.insert(0, %r); sys.path.insert(0, '/home/faisal/EventMarketDB')\n"
        "import a6_launch_freeze as A6\n"
        "total, rows = A6.ledger()\n"
        "import a7_g1_build\n"
        "print(os.path.dirname(os.path.abspath(a7_g1_build.__file__)) == %r, total)"
        % (_HERE, _HERE))
    assert out.returncode == 0, out.stderr[-600:]
    # the clean process resolves THIS directory's owners and derives THIS
    # directory's ledger. It used to be pinned to the 1488 receipt's frozen
    # completed_before, which stopped being the live total the moment the
    # targeted run was counted (SEQ 1492) and again at the hard review (SEQ
    # 1496); a frozen receipt is a stage's before, never the live ledger.
    import a6_launch_freeze as A6
    assert out.stdout.split() == ["True", str(A6.ledger()[0])]


def test_e_a_stale_preloaded_a7_g1_build_fails_closed_before_any_receipt():
    """The trap: an older tree earlier on sys.path preloads ITS a7_g1_build;
    a6_launch_freeze's lazy import must refuse it, not use it."""
    old = os.path.join(_X, "harness")
    code = (
        "import sys, os, importlib.util\n"
        "sys.path.insert(0, '/home/faisal/EventMarketDB'); sys.path.insert(0, %r)\n"
        "import a7_g1_build as stale\n"
        "spec = importlib.util.spec_from_file_location('a6_launch_freeze', %r)\n"
        "A6 = importlib.util.module_from_spec(spec); sys.modules['a6_launch_freeze'] = A6\n"
        "sys.path.insert(0, %r); spec.loader.exec_module(A6)\n"
        "for call in (lambda: A6.ledger(), lambda: A6.freeze(%r)):\n"
        "    try:\n"
        "        call(); print('ACCEPTED')\n"
        "    except RuntimeError as exc:\n"
        "        print('REFUSED', 'resolved to' in str(exc), os.path.dirname(stale.__file__) in str(exc))\n"
        "    except Exception as exc:\n"
        "        print('OTHER', type(exc).__name__)\n"
        % (old, os.path.join(_HERE, "a6_launch_freeze.py"), _HERE, STOPPED))
    out = _clean(code)
    assert out.returncode == 0, out.stderr[-600:]
    assert out.stdout.split("\n")[:2] == ["REFUSED True True", "REFUSED True True"], out.stdout
