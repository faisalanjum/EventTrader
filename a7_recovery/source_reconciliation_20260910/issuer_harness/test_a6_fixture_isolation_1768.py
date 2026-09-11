# -*- coding: utf-8 -*-
"""The historical fixture is SCOPED: it relaxes the era gate for the modules that
explicitly ask, and for nothing else (Codex SEQ 1766 item 4, 1768).

Four checks in definition order, which is the order pytest runs them:

  1 outside the fixture the live gate REFUSES the old-era run
  2 outside the fixture the live gate ACCEPTS the preserved current zero-call run
  3 inside the fixture the old-era identity is permitted, and still carries its own
    receipt, freeze and identity checks - the relaxation is the era, nothing else
  4 lives in the sibling module test_a6_fixture_isolation_after_1768.py, because this
    fixture is module-scoped: teardown can only be observed from a module that never
    requested it. Proving it here would prove nothing.

This is a narrow control over the EXISTING gate and the EXISTING fixture. It adds no
framework, launches nothing, and is counted separately from the historical inventory.
"""
import os

import pytest

import a7_prepared_run as PR
import a7_g1_build as G
import build_launch_manifest as BLM

#: the preserved A5 prelaunch run: current era, zero calls made
CURRENT_RUN = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
               "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/a6_a5run_1515")
#: the paid historical run the structural proofs read
OLD_RUN = G.PRIMARY

pytestmark = pytest.mark.skipif(not os.path.isdir(OLD_RUN),
                                reason="the executed run is absent")


def _era_of(run_dir):
    return PR.load(run_dir)["contract_suffix"]


def test_1_outside_the_fixture_the_gate_refuses_the_old_era_run():
    assert _era_of(OLD_RUN) != BLM.PRODUCER_CONTRACT_SUFFIX, (
        "the old run is not from another era, so this control proves nothing")
    with pytest.raises(ValueError) as got:
        PR.current(OLD_RUN, PR.load(OLD_RUN)["a6_freeze_sha256"])
    assert "another era" in str(got.value), str(got.value)


def test_2_outside_the_fixture_the_gate_accepts_the_current_zero_call_run(tmp_path):
    import build_a5_exp5_kit as A5
    fresh = str(tmp_path / "current_zero_calls")
    assert A5.prepare(fresh)["ok"]
    prepared = PR.load(fresh)
    ident = PR.current(fresh, prepared["a6_freeze_sha256"])
    assert not ident["executed"]
    assert ident["contract_suffix"] == BLM.PRODUCER_CONTRACT_SUFFIX


@pytest.mark.usefixtures("historical_v1_evidence")
def test_3_inside_the_fixture_the_old_era_is_permitted_and_still_fully_checked():
    ident = PR.current(OLD_RUN, PR.load(OLD_RUN)["a6_freeze_sha256"])
    # the era is relaxed; every other binding the identity carries is not
    assert ident["contract_suffix"] == _era_of(OLD_RUN)
    # the shape is DERIVED from the identity the same owner builds for the current
    # run outside the fixture, so this cannot drift on a guessed field list
    reference = PR.load(CURRENT_RUN)
    assert set(ident) == set(reference), (
        "the fixture changed the identity's shape: %s"
        % sorted(set(ident) ^ set(reference)))
    for field in sorted(set(reference) - {"contract_suffix"}):
        assert ident.get(field) is not None, (
            "the fixture dropped %s from the identity" % field)
