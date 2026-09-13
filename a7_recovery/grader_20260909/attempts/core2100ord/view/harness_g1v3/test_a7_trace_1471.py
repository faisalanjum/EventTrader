"""THE ONE MATERIALIZED TRACE, PROVED BEHAVIOURALLY (Codex SEQ 1471 item 4).

Inspecting source text for a banned call proves only that the text does not
contain it today. These proofs materialize ONCE and then make every other way
of getting the data EXPLODE: reopening a raw answer, calling the one parser
again, or walking the schedule a second time. Whatever still works afterwards
is reading the trace and nothing else.
"""
import io
import json
import copy
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

FIXTURE = os.environ.get("A7_TRACE_FIXTURE")


@pytest.fixture(scope="module")
def run():
    assert FIXTURE, "serve a complete current TEST path via A7_TRACE_FIXTURE"
    import audit_worker_access as AUD
    import a7_reference_inventory as REF
    with io.open(os.path.join(FIXTURE, "PRODUCER.json"), encoding="utf-8") as fh:
        identity = json.load(fh)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(AUD, "PROJECTS_ROOT", os.environ["A7_FIXTURE_PROJECTS"])
        patch.setattr(REF, "INVENTORY_PATH", os.path.join(FIXTURE, "reference_inventory.json"))
        assert PR.current(identity["run_dir"], identity["a6_freeze_sha256"]) == identity
        yield identity


@pytest.fixture(scope="module")
def current_g1(run, tmp_path_factory):
    """Current owner pins over a TEST G1 lifecycle, never recycled old pins."""
    import g1_fake_state as FAKE
    import audit_worker_access as AUD
    out = tmp_path_factory.mktemp("current_g1")
    candidate = out / "candidate"
    path, problems = G.write(str(candidate), run)
    assert problems == [], problems
    return FAKE.complete_test_run("G1", candidate, path, out / "run", AUD.PROJECTS_ROOT)


@pytest.fixture
def sealed(monkeypatch, run):
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
            if (not inside and isinstance(path, str) and ".raw.json" in path
                    and path.startswith(run["run_dir"] + os.sep)):
                raise AssertionError("a raw answer was reopened: %s" % path)
            return real_open(path, *a, **k)

        monkeypatch.setattr(CV, "run_digest", digest)
        monkeypatch.setattr(a1_reader, "read_one", no_parse)
        monkeypatch.setattr(G, "effective_slots", no_walk)
        monkeypatch.setattr(io, "open", no_raw)
    return _seal


def test_the_REAL_downstream_paths_consume_only_the_trace(run, sealed, tmp_path, current_g1):
    """The actual conservation, G1 and G23 entries - not a private helper.

    Each of these used to reach `materialize` again, walking the schedule and
    reparsing every answer. After ONE materialization the reads are sealed and
    the real paths must still finish (Codex SEQ 1472 item 4).
    """
    import a7_g23_run as R
    arms, meta, problems = G.materialize(run)      # the ONE materialization
    assert problems == []
    sealed()

    doc, _p = C.terminals(run, str(tmp_path / "conservation"))
    assert _p == [], _p
    assert doc["branches"], doc.keys()

    g1, _prompts, g1_problems = G.freeze(run)      # real G1
    assert g1_problems == [], g1_problems[:2]
    assert g1["batch_rows"]

    import a7_g23_build as B
    inputs = B.load_verified_inputs(
        os.path.join(run["run_dir"], "plan/a5_exp5_reader.manifest.json"),
        run, os.path.abspath(os.path.join(_HERE, "../../../../..")))
    g23, _pr, g23_problems = R.freeze(
        run, inputs=inputs, g1=current_g1, audit_root=str(tmp_path / "g23"))
    assert g23_problems == [], g23_problems[:2]
    assert g23["batching"]["rows"]


def test_every_status_and_route_outcome_is_conserved_exactly_once():
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
        ("abstention only", row(status="answered", readable=True,
                                abstentions=[{"reason": "TEST"}]),
         {}, ["abstained_only"]),
        ("empty success is invalid", row(status="answered", readable=True),
         {}, [None]),
        ("mixed split", row(status="answered", readable=True,
                            facts=[{}, {}, {}, {}, {}],
                            fact_positions=[0, 1, 2, 3, 4]),
         {("fact", i): {"decision": d, "index": 0, "codes": []}
          for i, d in enumerate(("written", "parked", "rejected", "merged", "skipped"))},
         ["written", "parked", "rejected", "merged", "skipped"]),
        ("missing route", row(status="answered", readable=True, facts=[{}],
                              fact_positions=[0]), {}, [None]),
        ("unknown route", row(status="answered", readable=True, facts=[{}],
                              fact_positions=[0]),
         {("fact", 0): {"decision": "a decision no owner declares"}}, [None]),
    ]
    for label, r, per_fact, want in cases:
        got = C._branches_of(r, per_fact)
        assert [b["terminal"] for b in got] == want, (label, got)
        assert len(got) == len(want), (label, got)
        assert [b["fact_position"] for b in got] == (r["fact_positions"] or [None])

    # a route outcome nobody declares is BLOCKING, never a quiet terminal
    lost = [b for _l, r, pf, w in cases[-2:] for b in C._branches_of(r, pf)]
    problems = C._conservation_problems(
        [r for _l, r, _pf, _w in cases[-2:]], [base], lost)
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


def test_public_accounting_keeps_the_real_mixed_split_and_all_origins(run, tmp_path):
    import raw_transport as RT
    arms, meta, problems = G.materialize(run)
    assert problems == []
    plan = RT.a1_plan_for_run(run["run_dir"])
    doc, problems = C.terminals(run, str(tmp_path))
    assert problems == [], problems
    assert doc["packets"] == meta["trace"]  # raw refs AND every saved attempt
    assert doc["scheduled_calls"] == len(RT.a1_schedule(plan))
    assert doc["arms"] == sorted(a["arm"] for a in plan["arms"])
    assert doc["attempt_total"] == sum(len(r["attempts"]) for r in meta["trace"])
    assert doc["branch_total"] == sum(max(1, len(r["facts"])) for r in meta["trace"])
    split = [r for r in meta["trace"] if len(r["facts"]) > 1]
    assert len(split) == 2, "the saved control has one split in each arm"
    for packet in split:
        branches = [b for b in doc["branches"] if b["lane_id"] == packet["lane_id"]]
        assert [b["fact_position"] for b in branches] == [0, 1]
        assert [b["terminal"] for b in branches] == ["parked", "written"]
        assert [b["outcome"]["index"] for b in branches] == [0, 0]
    assert len(doc["union_origins"]) == 2
    for row in doc["union_origins"]:
        assert {o["arm"] for o in row["origins"]} == {"P1", "P2"}
        assert {o["position"] for o in row["origins"]} == {row["fact_position"]}
        for origin in row["origins"]:
            assert any(p["lane_id"] == origin["lane_id"]
                       and p["packet_id"] == origin["packet_id"] for p in split)


def test_a_real_never_called_run_keeps_both_full_arms(tmp_path):
    import build_a5_exp5_kit as A5
    import raw_transport as RT
    producer = str(tmp_path / "uncalled")
    prep = A5.prepare(producer)
    assert prep["ok"], prep.get("problems")
    run = PR.load(producer)
    schedule = RT.a1_schedule(RT.a1_plan_for_run(producer))
    doc, problems = C.terminals(run, str(tmp_path / "audit"))
    assert doc["scheduled_calls"] == len(schedule)
    assert len(doc["packets"]) == len(schedule) == len(doc["branches"])
    assert doc["arms"] == ["P1", "P2"]
    assert doc["attempt_total"] == 0
    assert doc["terminal_counts"] == {"uncalled": len(schedule)}
    missing = [p for p in problems if isinstance(p, dict) and p.get("status") == "uncalled"]
    assert {(p["key"][0], p["key"][1]) for p in missing} == {
        (r["packet_id"], r["lane_id"]) for r in schedule}


def test_same_count_cannot_hide_wrong_or_missing_identity():
    scheduled = [{"ordinal": i, "source_id": "s", "packet_id": "p%d" % i,
                  "lane_id": "p%d/L%d" % (i, i + 1), "arm": "P%d" % (i + 1)}
                 for i in range(2)]
    rows = [dict(s, status="uncalled", readable=False, facts=[], fact_positions=[],
                 abstentions=[], continuity_hints=[], attempts=[]) for s in scheduled]
    branches = [b for r in rows for b in C._branches_of(r, {})]
    assert C._conservation_problems(rows, scheduled, branches) == []
    for field in ("source_id", "packet_id", "lane_id", "arm", "ordinal"):
        bad = copy.deepcopy(rows)
        bad[0][field] = "wrong"
        assert C._conservation_problems(bad, scheduled, branches), field
    for bad in (rows[:1], rows[:1] * 2, []):
        assert C._conservation_problems(bad, scheduled, branches)
    for bad in (branches[:1], branches[:1] * 2, []):
        assert C._conservation_problems(rows, scheduled, bad)


@pytest.mark.parametrize("loss", ["missing", "unknown"])
def test_public_route_loss_is_named_and_never_gets_credit(run, tmp_path, monkeypatch, loss):
    from scorers import score_exp5 as SCO
    control, problems = C.terminals(run, str(tmp_path / "positive"))
    assert problems == []
    real = SCO._rows_for_event
    changed = []

    def broken(*args):
        rows = real(*args)
        key = next((k for k in rows if k[0] == "fact"), None)
        if key is not None and not changed:
            changed.append(key)
            if loss == "missing":
                rows.pop(key)
            else:
                rows[key] = dict(rows[key], decision="unowned decision")
        return rows

    monkeypatch.setattr(SCO, "_rows_for_event", broken)
    doc, problems = C.terminals(run, str(tmp_path / "negative"))
    assert len(changed) == 1
    assert sum(b["terminal"] is None for b in doc["branches"]) == 1
    assert any("no known terminal" in str(p) for p in problems)
    assert doc["branch_total"] == control["branch_total"]
    assert doc["packets"] == control["packets"]


def test_one_wholly_uncalled_arm_is_not_removed_from_the_denominator(run, tmp_path, monkeypatch):
    arms, meta, problems = G.materialize(run)
    assert problems == []
    for row in meta["trace"]:
        if row["arm"] == "P2":
            row.update(status="uncalled", readable=False, attempt=None, selected_attempt=None,
                       raw_path=None, raw_sha256=None, attempts=[], facts=[],
                       fact_positions=[], abstentions=[], continuity_hints=[])
            problems.append({"slot": row["ordinal"], "status": "uncalled"})
    arms.pop("P2")
    monkeypatch.setattr(G, "materialize", lambda _run: copy.deepcopy((arms, meta, problems)))
    doc, problems = C.terminals(run, str(tmp_path))
    assert doc["arms"] == ["P1", "P2"]
    assert doc["terminal_counts"]["uncalled"] == doc["packets_per_arm"]["P2"]
    assert len(doc["packets"]) == run["scheduled_calls"]
    assert len([p for p in problems if isinstance(p, dict) and p.get("status") == "uncalled"]) == doc["packets_per_arm"]["P2"]


def test_dropped_trace_arm_still_owes_the_full_frozen_schedule(run, tmp_path, monkeypatch):
    import raw_transport as RT
    expected = len(RT.a1_schedule(RT.a1_plan_for_run(run["run_dir"])))
    control, problems = C.terminals(run, str(tmp_path / "control"))
    assert problems == [] and control["scheduled_calls"] == expected
    arms, meta, problems = G.materialize(run)
    assert problems == []
    missing_arm = sorted(arms)[-1]
    arms.pop(missing_arm)
    meta["trace"] = [r for r in meta["trace"] if r["arm"] != missing_arm]
    monkeypatch.setattr(G, "materialize", lambda _run: copy.deepcopy((arms, meta, problems)))
    broken, errors = C.terminals(run, str(tmp_path / "broken"))
    assert broken["scheduled_calls"] == expected
    assert missing_arm in broken["arms"]
    assert any("packet identities differ" in str(p) for p in errors)


def test_real_invalid_primary_and_valid_retry_keep_both_raw_attempts(tmp_path, monkeypatch):
    import build_a5_exp5_kit as A5
    import raw_transport as RT
    import audit_worker_access as AUD
    import g1_fake_state as FAKE
    import test_harness_guards as TG
    from pathlib import Path

    projects = os.environ["A7_FIXTURE_PROJECTS"]
    monkeypatch.setattr(AUD, "PROJECTS_ROOT", projects)
    native = FAKE.declared_input_record()
    assert native
    original = TG._a1_transcript

    def transcript(prompt, answer, model, uuid0="u0", uuid1="u1", agent_id="a01", session_id="sess"):
        records = original(prompt, answer, model, uuid0, uuid1, agent_id, session_id)
        records.insert(native["record_index"], {
            "type": native["record_type"], "uuid": "input-" + uuid0,
            "agentId": agent_id, "sessionId": session_id,
            native["payload_field"]: copy.deepcopy(native["payload"])})
        for before, after in zip(records, records[1:]):
            after["parentUuid"] = before["uuid"]
        return records

    monkeypatch.setattr(TG, "_a1_transcript", transcript)
    producer = str(tmp_path / "producer")
    prep = A5.prepare(producer)
    assert prep["ok"], prep.get("problems")
    plan = RT.a1_plan_for_run(producer)
    replies = {p["prompt_sha256"]: json.dumps({
        "source_id": p["source_id"], "facts": [],
        "abstentions": [{"reason": "TEST abstention"}], "continuity_hints": []})
        for p in plan["packets"]}
    bad = dict(replies)
    bad[plan["packets"][0]["prompt_sha256"]] = "{bad json"
    first = tmp_path / "primary_transport"
    first.mkdir()
    TG._a1_execute(Path(_HERE), first, prep, plan, projects, bad, "trace_primary")
    final = RT.a1_finalize(producer)
    expected = {(plan["packets"][0]["packet_id"], lane["lane_id"])
                for lane in plan["packets"][0]["lanes"]}
    assert {tuple(k) for k in final["retry"]} == expected
    retry = RT.a1_prepare_retry(producer)
    assert retry["ok"], retry.get("problems")
    second = tmp_path / "retry_transport"
    second.mkdir()
    TG._a1_execute(Path(_HERE), second, retry, plan, projects, replies, "trace_retry")
    final_retry = RT.a1_finalize(os.path.join(producer, RT.RETRY_DIRNAME))
    assert not final_retry["retry"]
    doc, problems = C.terminals(PR.load(producer), str(tmp_path / "audit"))
    assert problems == [], problems
    retried = [r for r in doc["packets"] if len(r["attempts"]) == 2]
    assert {(r["packet_id"], r["lane_id"]) for r in retried} == expected
    for row in retried:
        assert row["selected_attempt"] == 2
        assert [a["attempt"] for a in row["attempts"]] == [1, 2]
        assert [a["readable"] for a in row["attempts"]] == [False, True]
        for attempt in row["attempts"]:
            assert G._sha_file(attempt["raw_path"]) == attempt["raw_sha256"]
    assert doc["attempt_total"] == doc["scheduled_calls"] + len(expected)
    assert sum(n for stage, n in doc["attempt_counts"].items() if stage != "readable") == len(expected)
