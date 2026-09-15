"""The new instructions through the existing real lifecycle; TEST replies only."""
import pytest

import a7_grading_contract_2168 as CONTRACT
import test_correction_native_2118 as NATIVE
from test_correction_native_2118 import *  # reuse the tested lifecycle assertions
from test_correction_native_2118 import _current_candidate


@pytest.fixture(autouse=True)
def current_contract(monkeypatch):
    # The original full-population evidence remains untouched. Only the
    # correction preparer's existing renderer and rules inputs change.
    monkeypatch.setattr(NATIVE, 'V', CONTRACT)
    monkeypatch.setattr(NATIVE.PREP, 'V', CONTRACT)
    monkeypatch.setattr(NATIVE.PREP, 'CORRECTED_RULES', {
        'G2': CONTRACT.meaning_rules, 'G3': CONTRACT.extras_rules})
