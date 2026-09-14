# -*- coding: utf-8 -*-
"""PRIVATE MATERIALIZATION CACHE AND FINAL DRIFT GATE (Codex SEQ 1490).

  1. the cache owns an immutable expected (digest, file_count) and the
     authoritative materialization; callers only ever get deep copies, and
     run_of compares against the private tuple, never a returned meta;
  2. the cold path measures the tree right after validation (equal to the
     supplied executed identity when present) and again as the LAST read
     after every materialization read and the budget; any drift refuses and
     leaves no cache entry;
  3. a7_prepared_run.load refuses a preloaded foreign a7_g1_build before it
     trusts that module's _a6 guard.

Test first, on the executed run and on a disposable prepared run; nothing
frozen is written.
"""
import copy
import io
import os
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
_X = os.path.dirname(_HERE)

import a7_g1_build as G                                          # noqa: E402
import a7_g1_complete_v2 as CV                                   # noqa: E402
import a7_prepared_run as PR                                     # noqa: E402
import build_a5_exp5_kit as A5                                   # noqa: E402

PY = sys.executable
_trace = pytest.mark.skipif(not os.path.isdir(G.PRIMARY),
                            reason="the executed run is absent")


@pytest.fixture
def cold(monkeypatch):
    """This test's own empty private cache; the module's is untouched after."""
    monkeypatch.setattr(G, "_MATERIALIZED", {})


def _key(ident):
    return G._sha(G._plain(ident))


# ----------------------------------------------- 1. private, non-aliased
@_trace
@pytest.mark.usefixtures("historical_v1_evidence", "cold")
def test_cold_and_warm_returns_are_equal_but_never_the_cached_objects():
    ident = PR.load(G.PRIMARY)
    a = G.materialize(ident)
    assert len(G._MATERIALIZED) == 1
    entry = G._MATERIALIZED[_key(ident)]
    assert isinstance(entry["expected"], tuple)
    assert entry["expected"] == tuple(CV.run_digest(G.PRIMARY))
    b = G.materialize(ident)                    # warm
    assert a == b
    for x, y in zip(a, b):
        assert x is not y
    for x, cached in zip(a, entry["data"]):
        assert x is not cached
    for x, cached in zip(b, entry["data"]):
        assert x is not cached


def _mutations():
    def meta_budget(a):
        a[1]["budget"]["completed_actual"] = -1

    def meta_trace_nested(a):
        a[1]["trace"][0]["facts"] = ["forged"]

    def arms_nested(a):
        leg = next(iter(a[0]))
        sid = next(iter(a[0][leg]))
        a[0][leg][sid]["facts"].append({"forged": True})

    def problems(a):
        a[2].append("forged problem")

    def meta_scalar(a):
        a[1]["answers"] = 0
    return [("meta_budget", meta_budget), ("meta_trace_nested", meta_trace_nested),
            ("arms_nested", arms_nested), ("problems", problems),
            ("meta_scalar", meta_scalar)]


@_trace
@pytest.mark.usefixtures("historical_v1_evidence", "cold")
@pytest.mark.parametrize("name,mutate", _mutations(), ids=[m[0] for m in _mutations()])
def test_mutating_a_returned_materialization_never_reaches_the_cache(name, mutate):
    ident = PR.load(G.PRIMARY)
    first = G.materialize(ident)
    pristine = copy.deepcopy(first)
    mutate(first)
    assert first != pristine, name                # the mutation is real
    assert G.run_of(ident) == G.PRIMARY          # the warm proof is unaffected
    assert G.materialize(ident) == pristine      # the trace is pristine
    warm = G.materialize(ident)
    mutate(warm)                                 # mutating a WARM return
    assert G.materialize(ident) == pristine      # ... changes nothing either
    g1, _prompts, problems = G.freeze(ident)     # a real downstream read
    assert problems == [], problems[:2]
    assert g1["materialization"] == pristine[1]  # the G1 freeze carries the pristine meta
    assert g1["materialization"]["budget"]["completed_actual"] == \
        pristine[1]["budget"]["completed_actual"]


# ----------------------------------------------- 2. final cold-path drift
def _freeze_sha(run):
    """The accepted A6 freeze hash `current` now requires (Codex SEQ 1517):
    the exact A6-rendered bytes for this run."""
    import hashlib
    A6 = G._a6()
    return hashlib.sha256(A6.render(A6.freeze(run)).encode("utf-8")).hexdigest()


@pytest.fixture
def disposable(tmp_path):
    run = str(tmp_path / "v3")
    assert A5.prepare(run)["ok"]
    return run


@pytest.mark.usefixtures("cold")
def test_a_file_changed_during_cold_materialization_refuses_and_caches_nothing(
        disposable, monkeypatch):
    ident = PR.current(disposable, _freeze_sha(disposable))
    real_a6 = G._a6()
    extra = os.path.join(disposable, "raw", "zz_written_during_materialization.txt")

    class Seam(object):
        def budget(self, planned, run_dir=None):
            os.makedirs(os.path.dirname(extra), exist_ok=True)
            io.open(extra, "w").write("drift")     # the tree moves mid-flight
            return real_a6.budget(planned, run_dir)

        def __getattr__(self, name):
            return getattr(real_a6, name)
    monkeypatch.setattr(G, "_a6", lambda: Seam())
    with pytest.raises(ValueError) as exc:
        G.materialize(ident)
    assert "changed" in str(exc.value) or "no longer measures" in str(exc.value)
    assert _key(ident) not in G._MATERIALIZED
    os.remove(extra)
    monkeypatch.setattr(G, "_a6", lambda: real_a6)
    # the unchanged control caches ONCE and returns equal, non-aliased copies
    fresh = PR.current(disposable, _freeze_sha(disposable))
    a = G.materialize(fresh)
    b = G.materialize(fresh)
    assert a == b and a[1] is not b[1]
    assert list(G._MATERIALIZED) == [_key(fresh)]


@_trace
@pytest.mark.usefixtures("historical_v1_evidence", "cold")
def test_the_cold_baseline_must_equal_the_supplied_executed_identity(monkeypatch):
    ident = PR.load(G.PRIMARY)
    assert ident["executed"]                     # the run IS executed
    forged = copy.deepcopy(ident)
    forged["executed"]["run_files"] += 1
    monkeypatch.setattr(PR, "current", lambda run_dir, expect_freeze_sha=None: forged)   # the identity re-check passes
    with pytest.raises(ValueError):
        G.materialize(forged)
    assert _key(forged) not in G._MATERIALIZED


# ----------------------------------------------- 3. the same import class
def _clean(code):
    return subprocess.run([PY, "-B", "-c", code], capture_output=True, text=True,
                          cwd="/home/faisal/EventMarketDB")


def test_prepared_run_load_accepts_this_directory_and_refuses_a_foreign_a7_g1_build(
        tmp_path):
    run = str(tmp_path / "v3")
    assert A5.prepare(run)["ok"]
    old = os.path.join(_X, "harness")
    clean = _clean(
        "import sys; sys.path.insert(0, %r); sys.path.insert(0, '/home/faisal/EventMarketDB')\n"
        "import a7_prepared_run as PR; ident = PR.load(%r); print('ACCEPTED', ident['schema'])"
        % (_HERE, run))
    assert clean.returncode == 0, clean.stderr[-500:]
    assert clean.stdout.split() == ["ACCEPTED", PR.SCHEMA]
    # the foreign tree stays FIRST on sys.path, so the foreign a7_g1_build and
    # its matching foreign a6 both resolve; this module's a7_prepared_run is
    # loaded by file path and must refuse that pair before trusting _a6()
    stale = _clean(
        "import sys, os, importlib.util\n"
        "sys.path.insert(0, '/home/faisal/EventMarketDB'); sys.path.insert(0, %r)\n"
        "import a7_g1_build as foreign\n"
        "spec = importlib.util.spec_from_file_location('a7_prepared_run', %r)\n"
        "PR = importlib.util.module_from_spec(spec); sys.modules['a7_prepared_run'] = PR; spec.loader.exec_module(PR)\n"
        "try:\n"
        "    PR.load(%r); print('ACCEPTED')\n"
        "except RuntimeError as exc:\n"
        "    print('REFUSED', 'resolved to' in str(exc), os.path.dirname(foreign.__file__) in str(exc))\n"
        "except Exception as exc:\n"
        "    print('OTHER', type(exc).__name__)\n"
        % (old, os.path.join(_HERE, "a7_prepared_run.py"), run))
    assert stale.returncode == 0, stale.stderr[-500:]
    assert stale.stdout.strip() == "REFUSED True True", stale.stdout
