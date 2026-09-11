# -*- coding: utf-8 -*-
"""The fourth isolation check, deliberately in its own module.

`historical_v1_evidence` is module-scoped, so its teardown only happens when the
module that asked for it ends. This module never requests it, so if the live era
gate refuses here, the relaxation did not survive that teardown.
"""
import os

import pytest

import a7_prepared_run as PR
import a7_g1_build as G

OLD_RUN = G.PRIMARY

pytestmark = pytest.mark.skipif(not os.path.isdir(OLD_RUN),
                                reason="the executed run is absent")


def test_after_the_historical_module_the_refusal_returns():
    with pytest.raises(ValueError) as got:
        PR.current(OLD_RUN, PR.load(OLD_RUN)["a6_freeze_sha256"])
    assert "another era" in str(got.value), str(got.value)
