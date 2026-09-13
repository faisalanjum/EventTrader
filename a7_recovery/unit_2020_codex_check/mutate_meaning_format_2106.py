"""In-memory, explicitly named format mutations. No real file/model changes."""
import os
from pathlib import Path

import pytest
import test_meaning_format_2105 as T

F, G, R = T.F, T.G, T.R
source = Path(F.__file__).read_text()
assert G._sha(source) == os.environ['A7_FORMAT_CODE_SHA256']
test = str(Path(T.__file__).resolve())
changes = [
    ('false_becomes_true', 'read', 'decoded = literals[value]',
     'decoded = True if value == "false" else literals[value]',
     'test_exact_values_recover_without_changing_any_judgment'),
    ('unknown_becomes_true', 'read', 'decoded = literals[value]',
     'decoded = True if value == "null" else literals[value]',
     'test_exact_values_recover_without_changing_any_judgment'),
    ('nonexact_strings_accepted', 'read', 'value = row[\'verdicts\'].get(field)',
     'value = row[\'verdicts\'].get(field)\n            value = value.lower().strip() if isinstance(value, str) else value',
     'test_every_wrong_type_or_nonexact_string_stays_invalid_with_positive_control'),
    ('incomplete_schema_credited', 'read', 'answer, remaining = B.read_meaning_reply(G._plain(rows), packet)',
     'answer, remaining = {r["question_id"]: r["verdicts"] for r in rows}, []',
     'test_original_schema_and_identity_checks_still_own_the_boundary[missing_aspect]'),
    ('original_failures_erased', 'scope', "recovered[lane]['selected'] = None if chosen is None else chosen[0]",
     "recovered[lane]['attempts'] = {n: True for n in recovered[lane]['attempts']}\n            recovered[lane]['selected'] = None if chosen is None else chosen[0]",
     'test_versioned_completion_gets_recovered_relation_and_original_invalid_record'),
    ('original_evidence_failure_ignored', 'scope', "if problems or root is None or G.task_kind(doc) != 'G2':",
     "if root is None or G.task_kind(doc) != 'G2':",
     'test_original_evidence_refusals_cannot_be_normalized_away'),
    ('unapproved_code_allowed', 'scope', 'if G._sha_file(__file__) != expected_code_sha256:',
     'if False:', 'test_an_unapproved_format_version_never_opens_the_scope[code]'),
    ('unapproved_rule_allowed', 'scope', 'if G._sha_file(str(RULE_FILE)) != expected_rule_sha256:',
     'if False:', 'test_an_unapproved_format_version_never_opens_the_scope[rule]'),
    ('no_recovery_identity', 'scope', "value['meaning_format_recovery'] = {",
     "value['wrong_recovery_field'] = {",
     'test_versioned_completion_gets_recovered_relation_and_original_invalid_record'),
    ('other_grading_kind_changed', 'scope', "if problems or root is None or G.task_kind(doc) != 'G2':",
     'if problems or root is None:', 'test_other_grading_kinds_are_unchanged'),
    ('original_validity_drift_ignored', '_read_run', "if record['original_valid'] != original_valid:",
     'if False:', 'test_recovery_reread_refuses_each_own_evidence_failure[validity_drift]'),
    ('uncalled_treated_as_missing_answer', '_read_run', 'if not called:',
     'if False:', 'test_explicit_zero_call_closure_is_not_a_missing_model_answer'),
]
results = []
originals = {name: getattr(F, name) for name in ('read', 'scope', '_read_run')}
for name, function, old, new, case in changes:
    assert source.count(old) == 1, name
    changed = source.replace(old, new)
    namespace = dict(vars(F))
    exec(compile(changed, F.__file__, 'exec'), namespace)
    print('MUTATION', name, case, flush=True)
    with R._using(F, **{function: namespace[function]}):
        code = int(pytest.main([test + '::' + case, '-q', '-p', 'no:cacheprovider']))
    assert code == 1, (name, code)  # no setup, collection or missing-test exit
    assert all(getattr(F, key) is value for key, value in originals.items())
    results.append({'mutation': name, 'function': function, 'old': old, 'new': new,
                    'mutant_sha256': G._sha(changed), 'test': case, 'exit': code})
print('RESTORED_FULL_CONTROL', flush=True)
control = int(pytest.main([test, '-q', '-p', 'no:cacheprovider']))
assert control == 0
assert Path(F.__file__).read_text() == source
out = Path(__file__).parent / os.environ['A7_TAG']
out.mkdir()
G._write_new(str(out / 'MUTATIONS.json'), G._pretty({
    'code_sha256': G._sha(source), 'test_sha256': G._sha_file(test),
    'mutations': results, 'restored_control_exit': control,
    'actual_model_calls': 0, 'files_changed_by_mutations': 0}) + '\n')
print('VERIFIED', len(results), 'mutations detected; restored full control passed', flush=True)
