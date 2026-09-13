"""Behavioral mutations of the new filter only; no on-disk owner edits."""
import os
from pathlib import Path
import pytest
import test_meaning_retry_plan_2107 as T

M, G, R = T.M, T.G, T.T.R
source = Path(M.__file__).read_text()
assert G._sha(source) == os.environ['A7_RETRY_PLAN_SHA256']
test = str(Path(T.__file__).resolve())
changes = [
    ('repeat_recovered_success', "'retry_lanes': [lane for lane in final['retry'] if lane in unusable]",
     "'retry_lanes': final['retry']",
     'test_complete_supported_population_keeps_only_genuinely_invalid_retry'),
    ('accept_changed_finalization',
     "if path != G.finalization_path(run, segment) or G._sha(text) != G._sha_file(path):",
     'if False:', 'test_changed_finalization_refuses_without_overwrite'),
    ('ignore_original_validity', "if audit['original_valid'] != validity[lane]:",
     'if False:', 'test_original_validity_must_match_the_actual_parser'),
    ('accept_other_kind', "if G.task_kind(doc) != 'G2':",
     'if False:', 'test_each_early_boundary_refuses_after_real_positive[other_kind]'),
    ('accept_unfinalized', "if G.segment_state(run, segment) != 'finalized':",
     'if False:', 'test_each_early_boundary_refuses_after_real_positive[unfinalized]'),
    ('credit_native_error', "raise ValueError('retry filter original finalization refused: %s' % problems)",
     "return {'retry_lanes': []}",
     'test_original_finalizer_errors_stop_retry_selection_with_positive_control[native refusal]'),
]
original = M.plan
results = []
for name, old, new, case in changes:
    assert source.count(old) == 1, name
    changed = source.replace(old, new)
    namespace = dict(vars(M))
    exec(compile(changed, M.__file__, 'exec'), namespace)
    with R._using(M, plan=namespace['plan']):
        code = int(pytest.main([test + '::' + case, '-q', '-p', 'no:cacheprovider']))
    assert code == 1, (name, code)
    assert M.plan is original
    results.append({'name': name, 'mutant_sha256': G._sha(changed), 'test': case, 'exit': code})
control = int(pytest.main([test, '-q', '-p', 'no:cacheprovider']))
assert control == 0 and Path(M.__file__).read_text() == source
out = Path(__file__).parent / os.environ['A7_TAG']
out.mkdir()
G._write_new(str(out / 'MUTATIONS.json'), G._pretty({
    'code_sha256': G._sha(source), 'test_sha256': G._sha_file(test),
    'mutations': results, 'restored_control_exit': control,
    'actual_model_calls': 0, 'real_run_writes': 0}) + '\n')
print('VERIFIED:6 meaningful retry-filter mutations caught; restored14-test control passed')
