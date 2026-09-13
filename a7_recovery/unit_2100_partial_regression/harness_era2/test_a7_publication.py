"""Current public writers must preserve completed bytes across restart/races."""
import json
import multiprocessing
import os
from pathlib import Path

import pytest

import a7_g1_build as G
import a7_g23_build as B
import a7_g23_run as R
import a7_reference_inventory as REF
import raw_transport as RT
from test_a7_input_binding import run, inputs, g1


@pytest.fixture(scope="module")
def bundle(run, inputs, g1, tmp_path_factory):
    doc, prompts, problems = R.freeze(run, inputs=inputs, g1=g1,
                                      audit_root=str(tmp_path_factory.mktemp("publication_route")))
    assert problems == [], problems
    assert doc["g2_pairs"] and doc["g3_idxs"]
    _gold, identity = G.live_key()
    return run, inputs, g1, doc, prompts, identity


def _write(kind, out, bundle):
    run, inputs, g1, doc, prompts, identity = bundle
    out.mkdir(exist_ok=True)
    if kind == "G1":
        path, problems = G.write(str(out), run)
        assert problems == [], problems
    elif kind == "G23":
        path, problems = R.write(str(out), run, inputs=inputs, g1=g1,
                                 audit_root=str(out / "audit"))
        assert problems == [], problems
    elif kind in ("G2", "G3"):
        path, _sha = R.write_kind(str(out), kind, doc, prompts, identity)
    elif kind == "reference":
        path = str(out / "reference.json")
        REF.write(REF.expected_document(run), path)
        REF.validate(path, run)
    else:
        path = str(out / "sidecar.json")
        B.write_atomic(path, {"TEST": "immutable"})
    return Path(path)


def _bytes(out):
    return {str(p.relative_to(out)): p.read_bytes() for p in out.rglob("*")
            if p.is_file() and "audit" not in p.relative_to(out).parts}


@pytest.mark.parametrize("kind", ["G1", "G23", "G2", "G3", "reference", "sidecar"])
def test_second_public_write_refuses_and_preserves_every_original_byte(kind, bundle, tmp_path):
    out = tmp_path / kind
    path = _write(kind, out, bundle)
    before = _bytes(out)
    assert path.is_file() and before
    with pytest.raises(ValueError, match="already exists|once|overwrit"):
        _write(kind, out, bundle)
    assert _bytes(out) == before


@pytest.mark.parametrize("kind", ["G1", "G23", "G2", "G3"])
def test_interrupted_prompt_write_never_publishes_a_candidate(kind, bundle, tmp_path, monkeypatch):
    calls = []
    real = RT.write_new

    def interrupt(path, text):
        calls.append(path)
        if len(calls) == 2:
            raise RuntimeError("TEST interrupted before publication")
        return real(path, text)

    out = tmp_path / kind
    monkeypatch.setattr(RT, "write_new", interrupt)
    with pytest.raises(RuntimeError, match="TEST interrupted"):
        _write(kind, out, bundle)
    assert len(calls) == 2
    candidate = out / (R.CANDIDATE_NAME if kind == "G23" else G.CANDIDATE_NAME)
    assert not candidate.exists()
    assert list((out / "prompts").glob("*.prompt.txt"))
    partial = _bytes(out)
    monkeypatch.setattr(RT, "write_new", real)
    with pytest.raises(ValueError, match="already exists|once|overwrit"):
        _write(kind, out, bundle)
    assert _bytes(out) == partial
    if kind != "G23":
        with pytest.raises((ValueError, IOError)):
            G.load_frozen(str(out), "0" * 64)
    clean = _write(kind, tmp_path / "fresh_destination", bundle)
    assert clean.is_file()


@pytest.mark.parametrize("kind", ["reference", "sidecar"])
def test_two_independent_writers_cannot_replace_one_another(kind, tmp_path):
    # Force the former check-then-rename implementation's vulnerable ordering.
    # The write_new implementation needs no freshness check: the link itself
    # arbitrates both processes, including this exact race.
    context = multiprocessing.get_context("fork")
    barrier, queue = context.Barrier(2), context.Queue()
    path = str(tmp_path / "published.json")

    def worker(number):
        exists = os.path.exists

        def checked(name):
            found = exists(name)
            if name == path:
                barrier.wait(timeout=10)
            return found

        os.path.exists = checked
        try:
            (REF.write({"writer": number}, path) if kind == "reference"
             else B.write_atomic(path, {"writer": number}))
            queue.put((number, "published"))
        except ValueError:
            queue.put((number, "refused"))
        except BaseException as exc:
            queue.put((number, repr(exc)))

    children = [context.Process(target=worker, args=(n,)) for n in (1, 2)]
    for process in children:
        process.start()
    for process in children:
        process.join(15)
        assert process.exitcode == 0
    results = [queue.get(timeout=2) for _ in children]
    assert sorted(state for _n, state in results) == ["published", "refused"], results
    winner = next(n for n, state in results if state == "published")
    assert json.loads(Path(path).read_text()) == {"writer": winner}
