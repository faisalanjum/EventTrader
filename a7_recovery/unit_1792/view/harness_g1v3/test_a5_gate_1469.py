"""THE ONE CURRENT PLAN AND ONE REAL PRE-CALL GATE (Codex SEQ 1469 item 2).

The gate used to read the COMMITTED A1 pair at the DEFAULT era while the run
went on to serve its own v3 launchers: it proved v1 and the run served v3.
These proofs bind the gate to the pair that will actually be served, and then
try to break it - a gate nothing can fail is not a gate.
"""
import hashlib
import io
import json
import os
import shutil
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import build_a5_exp5_kit as A5                                   # noqa: E402
import build_launch_manifest as BLM                              # noqa: E402


def _gate(run):
    """The SHARED pre-call gate, against the pair this run persisted."""
    return [x for x in BLM.preflight(
        env={BLM.OUTPUT_TOKENS_VAR: BLM.MAX_OUTPUT_TOKENS_SETTING},
        run_dir=None,
        manifest_path=os.path.join(run, "plan", A5.MANIFEST_NAME),
        bundle_path=A5.a5_bundle_path(run)) if "no run directory" not in x]


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    out = str(tmp_path_factory.mktemp("a5gate") / "run")
    prep = A5.prepare(out)
    assert prep["ok"], prep["problems"][:3]
    return out


def _plan_of(run):
    with io.open(os.path.join(run, "plan", A5.MANIFEST_NAME),
                 encoding="utf-8") as fh:
        return json.load(fh)


def test_the_persisted_v3_pair_passes_the_shared_gate(run):
    """THE CONTROL every refusal below is measured against."""
    assert _gate(run) == [], _gate(run)[:3]
    assert _plan_of(run)["contract_suffix"] == ".v3"


def test_the_schedule_is_exactly_392_calls_over_196_packets(run):
    plan = _plan_of(run)
    assert len(plan["packets"]) == 196
    assert len(plan["ordered_calls"]) == 392
    with io.open(os.path.join(run, "receipt.json"), encoding="utf-8") as fh:
        assert len(json.load(fh)["allowed"]) == 392


def test_every_one_of_the_196_payloads_carries_ITS_OWN_menu_event_and_item(run):
    """Not fragments and not the first eight sources: all 196, each against its
    OWN readable menu, its OWN source event and its OWN located item."""
    plan = _plan_of(run)
    menus = {e["source_id"]: e.get("menu_display_to_original", {})
             for e in plan["events"]}
    # THE PAYLOADS THE PLAN ITSELF PINS, from the one packet/prompt owner.
    _pks, prompts = A5.packets()
    pinned = plan["prompt_sha256"]
    assert set(prompts) == set(pinned), "the payloads are not the pinned set"
    for pid, text in prompts.items():
        assert hashlib.sha256(text.encode("utf-8")).hexdigest() == pinned[pid], (
            "%s: the payload checked here is not the one the plan pins" % pid)
    assert len(plan["packets"]) == 196
    for pk in plan["packets"]:
        text = prompts[pk["packet_id"]]
        sid = pk["source_id"]
        assert sid in text, "%s: its own source event is absent" % sid
        item = pk["item"] or {}
        for field in sorted(item):
            v = item[field]
            if isinstance(v, str) and v.strip():
                # the payload embeds the item as JSON, so compare through the
                # SAME encoder - a curly apostrophe is \u2019 in the payload.
                needle = json.dumps(v, ensure_ascii=True)[1:-1]
                assert needle in text or v in text, (
                    "%s: its own located item field %r is not in its payload"
                    % (pk["packet_id"], field))
        for shown in (menus.get(sid) or {}):
            needle = json.dumps(str(shown), ensure_ascii=True)[1:-1]
            assert needle in text or str(shown) in text, (
                "%s: its own menu entry %r is missing" % (sid, shown))


def test_pinning_v1_under_the_current_v3_plan_REFUSES(run):
    """The whole point of the era fix: a v3 launch may not pin v1 bytes."""
    plan = _plan_of(run)
    v1 = BLM._sha(BLM._era_path("exp5_prompt_drafter.md", ""))
    assert plan["pins"]["contract"] != v1, "the plan already pins v1"
    broken = dict(plan, pins=dict(plan["pins"], contract=v1))
    assert BLM.protected_pin_problems(broken), "a v1 pin was ACCEPTED under v3"


def test_swapping_two_packet_payloads_REFUSES(run, tmp_path):
    """Two lawful packets, each valid on its own, exchanged. Nothing about the
    counts changes - only which payload belongs to which packet."""
    work = str(tmp_path / "swapped")
    shutil.copytree(run, work)
    bundle_path = A5.a5_bundle_path(work)
    with io.open(bundle_path, encoding="utf-8") as fh:
        bundle = json.load(fh)
    rows = bundle["slices"]
    a = os.path.normpath(os.path.join(BLM._REPO, rows[0]["launcher"]))
    b = os.path.normpath(os.path.join(BLM._REPO, rows[1]["launcher"]))
    # the launchers named by THIS copy still point at the original run, so the
    # swap is made where the gate will actually read
    ta, tb = io.open(a, "rb").read(), io.open(b, "rb").read()
    assert ta != tb
    try:
        io.open(a, "wb").write(tb)
        io.open(b, "wb").write(ta)
        assert _gate(run), "a payload swap was ACCEPTED"
    finally:
        io.open(a, "wb").write(ta)
        io.open(b, "wb").write(tb)
    assert _gate(run) == [], "the control did not restore"


def test_a_single_drifted_launcher_byte_REFUSES(run):
    plan = _plan_of(run)
    with io.open(A5.a5_bundle_path(run), encoding="utf-8") as fh:
        row = json.load(fh)["slices"][0]
    live = os.path.normpath(os.path.join(BLM._REPO, row["launcher"]))
    original = io.open(live, "rb").read()
    try:
        io.open(live, "wb").write(original + b" ")
        problems = _gate(run)
        assert problems, "a drifted launcher was ACCEPTED"
        assert any(row["source_id"] in p for p in problems), problems[:2]
    finally:
        io.open(live, "wb").write(original)
    assert _gate(run) == []


def test_the_same_canonical_path_rebuilds_byte_for_byte(tmp_path):
    """LITERAL reproducibility, at ONE disposable path (Codex SEQ 1470 item 1).

    Two roots can never be equal byte-for-byte, because a prepared run records
    WHERE IT IS. Excluding the files that carry the path - the manifest, the
    bundle, the receipt and every launcher - made the comparison unable to see
    nondeterministic launch bytes at all, which is most of what matters. So
    build once, snapshot EVERYTHING, delete the output, rebuild at the SAME
    path, and compare every file and every byte with nothing excluded.
    """
    run = str(tmp_path / "canonical")
    assert A5.prepare(run)["ok"]

    def snapshot(root):
        out = {}
        for base, _d, files in os.walk(root):
            for n in files:
                path = os.path.join(base, n)
                out[os.path.relpath(path, root)] = io.open(path, "rb").read()
        return out

    first = snapshot(run)
    assert first, "the build produced nothing"
    shutil.rmtree(run)
    assert A5.prepare(run)["ok"]
    second = snapshot(run)

    assert set(first) == set(second), sorted(set(first) ^ set(second))[:5]
    differing = sorted(k for k in first if first[k] != second[k])
    assert not differing, differing[:5]
    # and the path-bearing documents really were compared, not skipped
    assert os.path.join("plan", A5.MANIFEST_NAME) in first
    assert "receipt.json" in first
    assert any(k.startswith("launch" + os.sep) for k in first)


# ---- Codex SEQ 1471 item 1: the plan states, and write-once -----------------
@pytest.mark.parametrize("label,build,lawful", [
    ("absent plan dir (K-fields)", lambda d: None, True),
    ("present but EMPTY", lambda d: os.makedirs(os.path.join(d, "plan")), False),
    ("malformed json", lambda d: (os.makedirs(os.path.join(d, "plan")),
                                  io.open(os.path.join(d, "plan", "a.json"),
                                          "w").write("{nope")), False),
    ("unrecognised document", lambda d: (os.makedirs(os.path.join(d, "plan")),
                                         io.open(os.path.join(d, "plan",
                                                              "a.json"),
                                                 "w").write('{"hi": 1}')),
     False),
])
def test_only_an_ABSENT_plan_directory_falls_back_to_kfields(label, build,
                                                             lawful, tmp_path):
    """A present plan directory that yields no plan must REFUSE.

    `a1_plan_for_run` skipped malformed json with a bare `except: continue` and
    then answered from the DEFAULT K-fields plan, so a run's own broken plan
    was silently replaced by another door's - and the wrong plan reads as
    success. Only the ABSENT case is lawful (Codex SEQ 1471 item 1).
    """
    import raw_transport as RT
    d = str(tmp_path / label.replace(" ", "_").replace("(", "").replace(")", ""))
    os.makedirs(d)
    build(d)
    if lawful:
        plan = RT.a1_plan_for_run(d)          # the K-fields positive control
        assert isinstance(plan, dict) and plan.get("packets")
    else:
        with pytest.raises(RT.RawTransportError):
            RT.a1_plan_for_run(d)


def test_two_plans_in_one_directory_are_AMBIGUOUS_and_refuse(run, tmp_path):
    """Which plan a run was published under must never be decided by sort
    order."""
    import raw_transport as RT
    d = str(tmp_path / "ambiguous")
    os.makedirs(os.path.join(d, "plan"))
    src = os.path.join(run, "plan", A5.MANIFEST_NAME)
    for name in ("a.json", "b.json"):
        shutil.copy(src, os.path.join(d, "plan", name))
    with pytest.raises(RT.RawTransportError) as exc:
        RT.a1_plan_for_run(d)
    assert "transport plans" in str(exc.value)


def test_a_competing_publication_refuses_and_leaves_the_first_bytes(run):
    """WRITE-ONCE, not atomic replacement. Two builders could both pass the
    freshness check and replace each other's plan bytes."""
    import raw_transport as RT
    path = os.path.join(run, "plan", A5.MANIFEST_NAME)
    first = io.open(path, "rb").read()
    with pytest.raises(ValueError) as exc:
        RT.write_new(path, "a competing plan")
    assert "never overwritten" in str(exc.value)
    assert io.open(path, "rb").read() == first, "the accepted bytes moved"


def test_two_competing_publications_leave_the_winner_untouched(tmp_path,
                                                               monkeypatch):
    """THE RACE, SYNCHRONIZED AT THE RESERVATION ITSELF (Codex SEQ 1475).

    A barrier before `prepare` is not the boundary: scheduling can still let
    one caller fail the initial freshness check before both reach the
    reservation. Both threads are held at the EXACT target `plan_dir`,
    immediately before the real `mkdir`, so the reservation is what decides.
    The freshness check is not a reservation - before this fix the loser went
    on to REPLACE the winner's launcher and bundle bytes.
    """
    import threading
    run = str(tmp_path / "race")
    target = os.path.join(run, "plan")
    at_reservation = threading.Barrier(2)
    reached, results, errors, lock = [], [], [], threading.Lock()
    real_mkdir = A5.os.mkdir

    def held_mkdir(path, *a, **k):
        if os.path.abspath(path) == os.path.abspath(target):
            with lock:
                reached.append(path)
            at_reservation.wait(timeout=60)   # both threads, same instant
        return real_mkdir(path, *a, **k)

    monkeypatch.setattr(A5.os, "mkdir", held_mkdir)

    def build():
        try:
            out = A5.prepare(run)
        except BaseException as exc:          # noqa: BLE001 - nothing vanishes
            with lock:
                errors.append(exc)
            return
        with lock:
            results.append(out)

    threads = [threading.Thread(target=build) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=300)
    assert not any(t.is_alive() for t in threads), "a builder never finished"

    assert errors == [], [repr(e) for e in errors]
    assert len(reached) == 2, reached      # BOTH reached the reservation
    assert len(results) == 2, results
    won = [r for r in results if r["ok"]]
    lost = [r for r in results if not r["ok"]]
    assert len(won) == 1, [r["problems"][:1] for r in results]
    assert len(lost) == 1 and lost[0]["problems"], lost
    monkeypatch.undo()
    assert _gate(run) == [], _gate(run)[:3]


def test_the_loser_writes_no_child_at_all(tmp_path):
    """A second publication into a reserved run must not touch one byte."""
    run = str(tmp_path / "reserved")
    assert A5.prepare(run)["ok"]

    def snapshot():
        out = {}
        for base, _d, files in os.walk(run):
            for n in files:
                p = os.path.join(base, n)
                out[os.path.relpath(p, run)] = io.open(p, "rb").read()
        return out

    before = snapshot()
    assert before, "the winner wrote nothing"
    again = A5.prepare(run)
    assert not again["ok"] and again["problems"]
    assert snapshot() == before, "the loser changed the winner's bytes"
