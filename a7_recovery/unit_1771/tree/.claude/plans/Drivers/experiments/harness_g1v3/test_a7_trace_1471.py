"""THE ONE MATERIALIZED TRACE, PROVED BEHAVIOURALLY (Codex SEQ 1471 item 4).

Inspecting source text for a banned call proves only that the text does not
contain it today. These proofs materialize ONCE and then make every other way
of getting the data EXPLODE: reopening a raw answer, calling the one parser
again, or walking the schedule a second time. Whatever still works afterwards
is reading the trace and nothing else.
"""
import io
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import a6_launch_freeze as _A6                                   # noqa: E402,F401
import a1_reader                                                 # noqa: E402
import a7_conservation as C                                      # noqa: E402
import a7_g1_build as G                                          # noqa: E402
import a7_prepared_run as PR                                     # noqa: E402

pytestmark = pytest.mark.skipif(not os.path.isdir(G.PRIMARY),
                                reason="the executed run is absent")


@pytest.fixture(scope="module")
def run():
    return PR.load(G.PRIMARY)


@pytest.fixture
def sealed(monkeypatch):
    """Seal every route to the data EXCEPT the trace."""
    def _seal():
        def no_parse(*a, **k):
            raise AssertionError("a1_reader.read_one was called again")

        def no_walk(*a, **k):
            raise AssertionError("the schedule was walked a second time")

        # THE IDENTITY OWNER LEGITIMATELY READS EVERY FILE - that is how it
        # proves the run has not changed. What must not happen is a raw answer
        # being reopened to be READ AS EVIDENCE, so the digest is exempted and
        # nothing else is.
        import a7_g1_complete_v2 as CV
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
        monkeypatch.setattr(a1_reader, "read_one", no_parse)
        monkeypatch.setattr(G, "effective_slots", no_walk)
        monkeypatch.setattr(io, "open", no_raw)
    return _seal


def test_the_REAL_downstream_paths_consume_only_the_trace(run, sealed):
    """The actual conservation, G1 and G23 entries - not a private helper.

    Each of these used to reach `materialize` again, walking the schedule and
    reparsing every answer. After ONE materialization the reads are sealed and
    the real paths must still finish (Codex SEQ 1472 item 4).
    """
    import a7_g23_run as R
    arms, meta, problems = G.materialize(run)      # the ONE materialization
    assert problems == []
    sealed()

    doc, _p = C.terminals(run)                     # real conservation
    assert doc["branches"], doc.keys()

    g1, _prompts, g1_problems = G.freeze(run)      # real G1
    assert g1_problems == [], g1_problems[:2]
    assert g1["batch_rows"]

    g23, _pr, g23_problems = R.freeze(run)         # real G23
    assert g23_problems == [], g23_problems[:2]
    assert g23["batching"]["rows"]


def test_every_status_and_route_outcome_is_conserved_exactly_once(run):
    """One branch per produced fact, one terminal per packet that produced
    none - across every status and both route-loss cases."""
    base = {"arm": "P1", "packet_id": "p#000", "source_id": "p",
            "lane_id": "p#000/L1", "abstentions": [], "continuity_hints": [],
            "attempts": [], "facts": [], "fact_positions": [], "why": [],
            "readable": False, "status": "uncalled"}

    def row(**kw):
        out = dict(base)
        out.update(kw)
        return out

    cases = [
        ("valid primary", row(status="answered", readable=True,
                              facts=[{}], fact_positions=[0]),
         {("fact", 0): {"decision": "written", "index": 0}}, ["written"]),
        ("valid retry, both attempts",
         row(status="answered", readable=True, facts=[{}], fact_positions=[0],
             attempts=[{"attempt": 1}, {"attempt": 2}]),
         {("fact", 0): {"decision": "parked", "index": 1}}, ["parked"]),
        ("invalid", row(status="invalid"), {}, ["invalid_unreadable"]),
        ("refusal", row(status="refused"), {}, ["refused_unreadable"]),
        ("uncalled", row(status="uncalled"), {}, ["uncalled"]),
        ("missing route", row(status="answered", readable=True, facts=[{}],
                              fact_positions=[0]), {}, [None]),
        ("unknown route", row(status="answered", readable=True, facts=[{}],
                              fact_positions=[0]),
         {("fact", 0): {"decision": "a decision no owner declares"}}, [None]),
    ]
    for label, r, per_fact, want in cases:
        got = C._branches_of(r, per_fact)
        assert [b["terminal"] for b in got] == want, (label, got)
        assert len(got) == 1, (label, got)

    # a route outcome nobody declares is BLOCKING, never a quiet terminal
    lost = [b for _l, r, pf, w in cases[-2:] for b in C._branches_of(r, pf)]
    problems = C._conservation_problems(
        [r for _l, r, _pf, _w in cases[-2:]], ["P1"], lost)
    assert any("no known terminal" in p for p in problems), problems


def test_raw_drift_after_identity_capture_refuses(run, monkeypatch):
    """A raw answer changes after the identity was captured.

    Relocating a run to mutate it would change its identity for a second
    reason - its own recorded location - and prove the wrong thing. The drift
    is applied where it is actually observed: the whole-run digest the identity
    is measured from no longer matches what was captured.
    """
    import a7_g1_complete_v2 as CV
    assert G.run_of(run)                       # the control still holds
    real = CV.run_digest

    def drifted(run_dir):
        digest, files = real(run_dir)
        return ("f" * 64, files)               # one raw byte elsewhere moved

    monkeypatch.setattr(CV, "run_digest", drifted)
    with pytest.raises(ValueError) as exc:
        G.run_of(run)
    assert "no longer measures the supplied identity" in str(exc.value)
