# -*- coding: utf-8 -*-
"""Meaningful mutations of the changed rules/selection/replacement boundary.

Each case runs the named check UNMUTATED first - the real positive control -
then re-runs it against a mutated copy of the seam and requires it to fail.
A mutation that nothing catches is a check that proves nothing.

The checks are the existing ones: Codex's own rules-pin reproduction and the
native correction proof. Nothing is re-implemented here.
"""
import types
from pathlib import Path

import pytest

import test_correction_native_2118 as T
import test_correction_rules_2118 as RULES
from test_correction_native_2118 import base, both, _current_candidate  # noqa: F401
from test_a7_input_binding import run, inputs, g1                 # noqa: F401

#: (what to break, the replacement, the module holding the check, its name,
#:  the argument a parametrized check needs, and WHICH owner to mutate)
MUTATIONS = [
    ('R.KIND_RULES = dict(CORRECTED_RULES)', 'pass',
     RULES, 'test_candidate_rules_are_the_actual_corrected_prompt_rules',
     'G2', 'PREP'),
    ('R.KIND_RULES = dict(CORRECTED_RULES)', 'pass',
     RULES, 'test_candidate_rules_are_the_actual_corrected_prompt_rules',
     'G3', 'PREP'),
    ("built['input_correction_sha256'] = pin", 'pass',
     T, 'test_the_prepared_candidate_is_the_subset_and_names_its_input_version',
     None, 'PREP'),
    ("('g2_pairs', subset if kind == 'G2' else {}),",
     "('g2_pairs', full_population if kind == 'G2' else {}),",
     T, 'test_the_prepared_candidate_is_the_subset_and_names_its_input_version',
     None, 'PREP'),
    ("if key not in offered:", "if False:",
     T, 'test_an_unapproved_subset_refuses_with_a_valid_control',
     'extra_question', 'PREP'),
    # LOSE ONE CORRECTION BATCH: the seam fits every selected question into its
    # own call, so truncating the packing drops one of them silently.
    ('kind, B.pack_batches(subset),', 'kind, B.pack_batches(subset)[:1],',
     T, 'test_many_questions_in_one_group_across_several_fitted_batches',
     'all', 'PREP'),
    # THE G3 COMPARATOR BOUNDARY, in the renderer: put the asked row back into
    # its own comparison pool, then let every unmatched record back in.
    ('if idx in pool]', 'if True]',
     T, 'test_a_group_with_no_matched_pair_gets_an_explicitly_empty_pool',
     'sparse', 'V'),
    ('if produced in seen:', 'if False:',
     T, 'test_a_broken_matched_inventory_refuses_with_a_valid_control',
     'repeated_index', 'V'),
    # THE COMPLETENESS CHECK: let the explicit view stay sparse, which is
    # exactly the defect - a legitimately unmatched group becomes an absence
    # again and refuses instead of rendering an empty pool.
    ('        view[group] = [list(row) for row in rows]',
     '        view[group] = [list(row) for row in rows] if rows else None\n'
     '        if not rows:\n            view.pop(group)',
     T, 'test_a_group_with_no_matched_pair_gets_an_explicitly_empty_pool',
     'sparse', 'V'),
]


def _mutated(old, new, owner):
    text = Path(owner.__file__).read_text(encoding='utf-8')
    assert text.count(old) == 1, (old, text.count(old))
    module = types.ModuleType(owner.__name__ + '_mutated')
    module.__file__ = owner.__file__
    exec(compile(text.replace(old, new), module.__file__, 'exec'),
         module.__dict__)
    return module


def test_removing_the_consumers_matched_population_check_is_detected(base, both, monkeypatch):
    check = T.test_the_bound_matched_population_is_checked_by_the_consumer
    check(base, both)  # actual consumer positive control, then its mismatch refusal
    fresh = base['tmp'] / 'mutated_consumer'
    fresh.mkdir()
    base['tmp'] = fresh
    changed = _mutated(
        "_same(candidate.get('matched_population'), required['G2'],\n"
        "                      'G3 matched comparison population')",
        'pass', T.REV)
    monkeypatch.setattr(T, 'REV', changed)
    with pytest.raises(pytest.fail.Exception, match='DID NOT RAISE'):
        check(base, both)


@pytest.mark.parametrize('old,new,holder,check_name,argument,owner', MUTATIONS)
def test_a_mutation_of_the_boundary_is_killed(base, monkeypatch, old, new,
                                              holder, check_name, argument,
                                              owner):
    check = getattr(holder, check_name)
    args = (base,) if argument is None else (base, argument)
    check(*args)                                   # the positive control
    # a FRESH working root, so the second run fails on the mutation rather
    # than on the directory its own control already created
    fresh = base['tmp'] / 'mutated'
    fresh.mkdir()
    base['tmp'] = fresh
    changed = _mutated(old, new, getattr(T, owner))
    monkeypatch.setattr(T, owner, changed)
    if owner == 'V':
        # the seam holds its OWN reference to the renderer, so the module the
        # test sees is not the module the seam calls
        monkeypatch.setattr(T.PREP, 'V', changed)
    # `Failed: DID NOT RAISE` is how a killed refusal-check reports itself
    with pytest.raises((AssertionError, ValueError, KeyError,
                        pytest.fail.Exception)):
        check(*args)
