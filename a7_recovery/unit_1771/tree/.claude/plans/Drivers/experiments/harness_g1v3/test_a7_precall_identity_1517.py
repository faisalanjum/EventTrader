# -*- coding: utf-8 -*-
"""A7 PRE-CALL IDENTITY: the live route pins the ONE frozen launch (Codex SEQ
1517).

Two seams are closed here:
  1. `a7_prepared_run.load` hashed a SECOND compact json rendering of the A6
     document, so `a6_freeze_sha256` differed from the exact bytes A6 renders
     and locks - two owners for one identity. A6 is now the only serializer.
  2. the live `current`/CLI route accepted an omitted freeze hash, so an
     unpinned lawful run could stand in for the frozen launch. The hash is now
     required and supplied externally.

These proofs bind the exact frozen fresh run to the final A4 lock/receipt, the
corrected inventory and the exact frozen A6 bytes, and refuse every unpinned or
substituted run before call 1. No launcher is executed and no run is finalized.
"""
import hashlib
import io
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import a7_g1_build as G                                          # noqa: E402
import a7_prepared_run as PR                                     # noqa: E402
import build_a5_exp5_kit as A5                                   # noqa: E402

#: the sole A7 pre-call candidate: the already-frozen fresh run (Codex SEQ 1517)
RUN = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
       "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/a6_a5run_1515")
#: the accepted A6 freeze bytes the operator supplies
ACCEPTED = "4123bb693f6b040af48f4ea53c533b2ad800e80102113844adb5afc69c65052d"

pytestmark = pytest.mark.skipif(
    not os.path.isdir(RUN), reason="the frozen A7 candidate run is absent")


def _freeze_sha(run):
    # the accepted hash is the run's PRE-LAUNCH view - what `load` pins - a
    # no-op before execution, the reconstructed pre-call freeze after (SEQ 1521)
    a6 = G._a6()
    return hashlib.sha256(
        a6.render(a6.precall_view(a6.freeze(run), run)).encode("utf-8")).hexdigest()


def _fresh(tmp_path, name="v3"):
    run = str(tmp_path / name)
    assert A5.prepare(run)["ok"]
    return run


# ===================================================== seam 1: one serializer
def test_freeze_sha_is_the_exact_a6_rendered_bytes():
    a6 = G._a6()
    frozen = a6.freeze(RUN)
    want = hashlib.sha256(a6.render(frozen).encode("utf-8")).hexdigest()
    ident = PR.load(RUN)
    assert ident["a6_freeze_sha256"] == want == ACCEPTED
    # NOT the retired compact re-rendering, which had a different hash
    compact = hashlib.sha256(
        json.dumps(frozen, sort_keys=True, separators=(",", ":"))
        .encode("utf-8")).hexdigest()
    assert ident["a6_freeze_sha256"] != compact


# ===================================================== the lawful control
def test_lawful_current_zero_call_control():
    ident = PR.current(RUN, ACCEPTED)
    assert ident["scheduled_calls"] == 392
    assert ident["executed"] is None and ident["finalizations"] == {}
    # bound to the final A4 lock/receipt, the corrected inventory and A6 bytes
    assert ident["a6_freeze_sha256"] == ACCEPTED
    assert ident["a4_lock_sha256"] == A5.A4_LOCK_SHA
    assert ident["a4_lock_receipt_sha256"] == A5.A4_LOCK_RECEIPT_SHA
    assert ident["corrected_inventory_sha256"] == hashlib.sha256(
        io.open(A5.CORRECTED_INVENTORY_PATH, "rb").read()).hexdigest()
    # the launch parameters re-derive from the pinned A6 document
    doc = G._a6().freeze(RUN)
    assert doc["counts"]["invocations"] == 36
    assert doc["counts"]["ordered_producer_calls"] == 392
    assert doc["budget"]["completed_actual"] == 5220
    assert doc["budget"]["producer_primary_after"] == 5612
    assert doc["budget"]["global_abort_ceiling"] == 6000
    assert doc["transport"]["runtime_model_id"] == "claude-sonnet-5"
    assert doc["transport"]["effort"] == "high"
    assert doc["transport"]["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] == "128000"
    assert doc["grader"]["armed_grader_calls"] == 0
    assert not any(doc["zeros"].values())


# ===================================================== seam 2 + the battery
def test_omitted_hash_refuses_before_call_one():
    with pytest.raises(ValueError) as exc:
        PR.current(RUN)
    assert "requires the accepted A6 freeze hash" in str(exc.value)


def test_wrong_hash_refuses_before_call_one():
    with pytest.raises(ValueError) as exc:
        PR.current(RUN, "0" * 64)
    assert "not the required" in str(exc.value)


def test_another_lawful_v3_run_refuses_against_the_accepted_hash(tmp_path):
    other = _fresh(tmp_path)
    assert _freeze_sha(other) != ACCEPTED       # a different run freezes apart
    with pytest.raises(ValueError):
        PR.current(other, ACCEPTED)


@pytest.mark.skipif(not os.path.isdir(G.PRIMARY),
                    reason="the historical run is absent")
def test_the_old_original_inventory_run_refuses():
    # the paid v1 run built on the ORIGINAL inventory: it neither freezes to the
    # accepted bytes nor is of the current era.
    with pytest.raises(ValueError):
        PR.current(G.PRIMARY, ACCEPTED)
    with pytest.raises(ValueError) as exc:
        PR.current(G.PRIMARY, _freeze_sha(G.PRIMARY))
    assert "current producer era" in str(exc.value)


def test_a_moved_run_refuses(tmp_path):
    # a byte-identical copy at another path is a different launch: its receipt
    # binds the original directory, so the run refuses at identity load, well
    # before the accepted hash could even be compared.
    import shutil
    moved = str(tmp_path / "moved_v3")
    shutil.copytree(RUN, moved)
    with pytest.raises(ValueError):
        PR.current(moved, ACCEPTED)


def test_a_middle_state_run_refuses(tmp_path):
    # saved answers but no finalization: neither uncalled nor complete, refused
    # before it could be read (and long before any call).
    mid = _fresh(tmp_path)
    os.makedirs(os.path.join(mid, "answers"))
    io.open(os.path.join(mid, "answers", "00000.json"), "w").write("{}")
    with pytest.raises(ValueError) as exc:
        PR.load(mid)
    assert "no finalization" in str(exc.value)


def test_cli_requires_both_run_and_freeze():
    with pytest.raises(ValueError) as exc:
        PR.cli_run(["--run", RUN])
    assert "--expect-freeze" in str(exc.value)
    with pytest.raises(ValueError) as exc:
        PR.cli_run(["--expect-freeze", ACCEPTED])
    assert "--run" in str(exc.value)


# ============================================ the operator-ready pre-call receipt
def _receipt():
    """The one operator-ready pre-call identity, rendered deterministically."""
    return json.dumps(PR.current(RUN, ACCEPTED), sort_keys=True, indent=1)


def test_operator_receipt_builds_twice_byte_identically():
    a = _receipt()
    b = _receipt()
    assert a == b
    doc = json.loads(a)
    assert doc["run_dir"] == RUN
    assert doc["a6_freeze_sha256"] == ACCEPTED
    assert doc["scheduled_calls"] == 392
