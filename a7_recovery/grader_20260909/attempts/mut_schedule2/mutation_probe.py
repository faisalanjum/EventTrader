"""One explicit removed safeguard, then its real pytest check. No AI calls.

The frozen on-disk candidate is unchanged. Only the named function's code is
replaced in this disposable test process, so an unrelated file-hash refusal
cannot masquerade as detection of the intended behavior. Raw exit 1 is the
expected killed-mutant result, not a passing candidate qualification.
"""
import ast
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys

H = Path("/tmp/claude-1000/-home-faisal-EventMarketDB/"
         "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/"
         "bench_1306/.claude/plans/Drivers/experiments/harness_g1v3")
out = Path(os.environ["A7_ATTEMPT_DIR"])
out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(H))
import build_launch_manifest as BLM
BLM.build()

cases = {
    "R2": ("a7_conservation", "_conservation_problems",
           "    problems = []", "    return []\n    problems = []",
           ["test_a7_trace_1471.py::test_same_count_cannot_hide_wrong_or_missing_identity"]),
    "R2_schedule": ("a7_conservation", "terminals",
                    "for r in RT.a1_schedule(plan)]", "for r in rows]",
                    ["test_a7_trace_1471.py::test_dropped_trace_arm_still_owes_the_full_frozen_schedule"]),
    "R3": ("a7_g23_build", "verified_event_context",
           'fresh = load_verified_inputs(inputs["manifest_path"], run, inputs["root"])',
           "fresh = inputs",
           ["test_a7_input_binding.py::test_mutable_path_and_hash_cannot_change_the_public_nonempty_g2"]),
    "R4": ("a7_g1_build", "_write_new", "RT.write_new(path, text)",
           'io.open(path, "w", encoding="utf-8").write(text)',
           ["test_a7_publication.py::test_second_public_write_refuses_and_preserves_every_original_byte"]),
    "R5": ("a7_g23_build", "extras_rules", '"<%s | null>" % " | ".join(buckets)',
           "buckets[0]",
           ["test_a7_score_boundaries.py::test_extra_review_template_shows_a_shape_not_an_example_answer"]),
    "R6": ("scorers.score_exp5_current", "_leg",
           'res["matched"] * denominator >= res["gold_n"] * numerator',
           'res["recall"] >= recall_bar',
           ["test_a7_score_boundaries.py::test_a_real_rounded_up_union_score_must_not_pass"]),
    "R7": ("audit_worker_access", "g1_state_audit",
           '    if len(captured) != len(rows):\n'
           '        return problems + ["the state records %d agent rows but %d captures"\n'
           '                           % (len(rows), len(captured))], {}\n', "",
           ["test_a7_interrupted_capture.py::test_real_finalizer_handles_every_interrupted_capture_shape"]),
}
name = os.environ["A7_MUTATION"]
module_name, function_name, before, after, tests = cases[name]
module = importlib.import_module(module_name)
raw = Path(module.__file__).read_text()
node = next(n for n in ast.parse(raw).body if isinstance(n, ast.FunctionDef) and n.name == function_name)
original = ast.get_source_segment(raw, node)
assert original.count(before) == 1, (name, "mutation anchor is not unique")
changed = original.replace(before, after)
record = {"kind": "INTENTIONAL_IN_PROCESS_FUNCTION_MUTATION", "case": name,
          "module": module.__file__, "module_sha256": hashlib.sha256(raw.encode()).hexdigest(),
          "function": function_name, "original_function": original,
          "mutant_function": changed, "tests": tests}
(out / "MUTATION.json").write_text(json.dumps(record, indent=2) + "\n")
exec(compile(changed, "<intentional-mutation-%s>" % name, "exec"), module.__dict__)
import pytest
os.chdir(H)
code = pytest.main(["-q", "--no-header", "-rfE", "-p", "no:cacheprovider",
                    "--basetemp", str(out / "pytest")] + tests)
raise SystemExit(code)
