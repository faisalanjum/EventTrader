"""Tests for the section_audit feature added on top of the predictor flow.

Covers all Tests-to-update/add bullets from .claude/plans/earningsBundleAuditSteps.md:
  - SDK prompt content via _build_predictor_prompt helper
  - Central existence check in run_predictor_via_sdk wrapper
  - AST guard: every caller uses 4-arg signature
  - AST guard: orchestrator caller preserves tuple unpack
  - run_ab_baseline.py paired-existence resume predicate
  - SKILL.md content sanity (Phase 0.5 placement + required fields)
"""
from __future__ import annotations
import ast
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_EARNINGS = REPO_ROOT / "scripts" / "earnings"
SCRIPTS = REPO_ROOT / "scripts"
for p in (str(SCRIPTS_EARNINGS), str(SCRIPTS), str(REPO_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)


# ── 1. SDK prompt helper ──────────────────────────────────────────────────

class BuildPredictorPromptTests(unittest.TestCase):
    """The helper must include SECTION_AUDIT_PATH and the audit-first instruction."""

    def test_prompt_contains_section_audit_path_env_var(self):
        from earnings_orchestrator import _build_predictor_prompt
        prompt = _build_predictor_prompt(
            Path("/b/bundle.json"), Path("/b/rendered.txt"),
            Path("/p/section_audit.json"), Path("/p/result.json"),
        )
        self.assertIn("SECTION_AUDIT_PATH=/p/section_audit.json", prompt)

    def test_prompt_contains_audit_first_instruction(self):
        from earnings_orchestrator import _build_predictor_prompt
        prompt = _build_predictor_prompt(
            Path("/b"), Path("/r"), Path("/a"), Path("/x"),
        )
        self.assertIn(
            "write SECTION_AUDIT_PATH as facts-only JSON, then write RESULT_PATH",
            prompt,
        )

    def test_prompt_path_order_audit_before_result(self):
        from earnings_orchestrator import _build_predictor_prompt
        prompt = _build_predictor_prompt(
            Path("/b"), Path("/r"), Path("/a"), Path("/x"),
        )
        audit_pos = prompt.index("SECTION_AUDIT_PATH=")
        result_pos = prompt.index("RESULT_PATH=")
        self.assertLess(audit_pos, result_pos)


# ── 2. Central existence check raises on missing file ─────────────────────

class RunPredictorViaSdkExistenceCheckTests(unittest.TestCase):
    """Wrapper must raise if either file is missing after asyncio.run returns."""

    def _make_stub_async(self, files_to_create):
        """Returns a stub that creates `files_to_create` then returns the tuple."""
        async def _stub(bundle_path, rendered_path, section_audit_path, result_path):
            for p in files_to_create:
                if p == "result":
                    result_path.write_text("{}")
                elif p == "audit":
                    section_audit_path.write_text("{}")
            return ("OK", "session-id-stub")
        return _stub

    def _patch_async(self, monkeypatch_target, files_to_create):
        import earnings_orchestrator as eo
        eo._run_predictor_via_sdk_orig = eo._run_predictor_via_sdk
        eo._run_predictor_via_sdk = self._make_stub_async(files_to_create)
        return eo

    def _restore_async(self, eo):
        eo._run_predictor_via_sdk = eo._run_predictor_via_sdk_orig
        del eo._run_predictor_via_sdk_orig

    def test_raises_when_result_missing(self):
        import tempfile
        eo = self._patch_async(None, files_to_create=["audit"])  # audit but not result
        try:
            with tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                with self.assertRaisesRegex(RuntimeError, "result.json"):
                    eo.run_predictor_via_sdk(
                        tmp / "b", tmp / "r",
                        tmp / "section_audit.json", tmp / "result.json",
                    )
        finally:
            self._restore_async(eo)

    def test_raises_when_audit_missing(self):
        import tempfile
        eo = self._patch_async(None, files_to_create=["result"])  # result but not audit
        try:
            with tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                with self.assertRaisesRegex(RuntimeError, "section_audit.json"):
                    eo.run_predictor_via_sdk(
                        tmp / "b", tmp / "r",
                        tmp / "section_audit.json", tmp / "result.json",
                    )
        finally:
            self._restore_async(eo)

    def test_passes_when_both_present(self):
        import tempfile
        eo = self._patch_async(None, files_to_create=["result", "audit"])
        try:
            with tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                final, sid = eo.run_predictor_via_sdk(
                    tmp / "b", tmp / "r",
                    tmp / "section_audit.json", tmp / "result.json",
                )
                self.assertEqual(final, "OK")
                self.assertEqual(sid, "session-id-stub")
        finally:
            self._restore_async(eo)


# ── 3. AST guard: every caller uses 4-arg signature ───────────────────────

CALLER_FILES = [
    REPO_ROOT / "scripts" / "earnings" / "earnings_orchestrator.py",
    REPO_ROOT / "scripts" / "run_q3_from_existing_bundle.py",
    REPO_ROOT / "scripts" / "run_ab_baseline.py",
    REPO_ROOT / "scripts" / "run_burl_ab_sequential.py",
    REPO_ROOT / "scripts" / "run_nvda_ab_sequential.py",
]


def _find_calls(tree: ast.AST, func_name: str) -> list[ast.Call]:
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name) and f.id == func_name:
                out.append(node)
            elif isinstance(f, ast.Attribute) and f.attr == func_name:
                out.append(node)
    return out


class CallerArityAstGuardTests(unittest.TestCase):
    """Every run_predictor_via_sdk(...) call across the 5 caller files must have
    exactly 4 positional args + 0 kwargs. Catches arity drift that import-time
    smoke would miss (Python checks arity at call time, not import time)."""

    def test_every_caller_uses_four_positional_args(self):
        for path in CALLER_FILES:
            with self.subTest(file=path.name):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                calls = _find_calls(tree, "run_predictor_via_sdk")
                self.assertGreaterEqual(len(calls), 1, f"no call in {path.name}")
                for call in calls:
                    self.assertEqual(
                        len(call.args), 4,
                        f"{path.name}:{call.lineno} expected 4 positional args, got {len(call.args)}",
                    )
                    self.assertEqual(
                        len(call.keywords), 0,
                        f"{path.name}:{call.lineno} expected 0 kwargs, got {len(call.keywords)}",
                    )


# ── 4. Orchestrator-specific tuple-unpack AST guard ───────────────────────

ORCHESTRATOR = REPO_ROOT / "scripts" / "earnings" / "earnings_orchestrator.py"


class OrchestratorTupleUnpackGuardTests(unittest.TestCase):
    """The orchestrator's run_predictor_via_sdk(...) call MUST be unpacked as
    `_pred_result, predictor_session_id = ...`. Discarding the tuple silently
    breaks predictor_session_id flow into finalize/ledger/harvester."""

    def test_orchestrator_call_is_tuple_assigned(self):
        tree = ast.parse(ORCHESTRATOR.read_text(encoding="utf-8"))
        # Find Assign nodes whose value is a Call to run_predictor_via_sdk
        found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                v = node.value
                if isinstance(v, ast.Call):
                    f = v.func
                    if (isinstance(f, ast.Name) and f.id == "run_predictor_via_sdk") or \
                       (isinstance(f, ast.Attribute) and f.attr == "run_predictor_via_sdk"):
                        # targets must be a single Tuple of length 2
                        self.assertEqual(len(node.targets), 1)
                        target = node.targets[0]
                        self.assertIsInstance(target, ast.Tuple,
                            f"orchestrator line {node.lineno} must unpack tuple, got {type(target).__name__}")
                        self.assertEqual(len(target.elts), 2,
                            f"orchestrator line {node.lineno} expected 2-tuple unpack")
                        found = True
        self.assertTrue(found, "no run_predictor_via_sdk Assign found in orchestrator")


# ── 5. run_ab_baseline.py paired-existence resume predicate ───────────────

AB_BASELINE = REPO_ROOT / "scripts" / "run_ab_baseline.py"


class AbBaselineResumeGuardTests(unittest.TestCase):
    """run_ab_baseline.py must resume only when BOTH result.json AND
    section_audit.json exist. Source-level guard against the pre-fix pattern."""

    def test_source_uses_paired_existence_predicate(self):
        src = AB_BASELINE.read_text(encoding="utf-8")
        # The predicate must reference both .exists() in a single conditional.
        # Cheap source check: look for the conjunction pattern.
        self.assertIn(
            "test_result_path.exists() and section_audit_path.exists()",
            src,
            "run_ab_baseline.py must use paired-existence resume predicate",
        )

    def test_source_does_not_use_unpaired_resume(self):
        """Negative guard: ensure the old single-condition resume isn't lurking."""
        src = AB_BASELINE.read_text(encoding="utf-8")
        # The OLD pattern was: `if test_result_path.exists():\n        log.info("  Reusing`
        # We assert the new pattern wins by checking we don't have the old single-existence
        # immediately followed by Reusing log on the next non-blank line.
        lines = src.splitlines()
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped == "if test_result_path.exists():":
                # next non-blank line should NOT be "log.info" with "Reusing"
                for j in range(i + 1, min(i + 4, len(lines))):
                    nxt = lines[j].strip()
                    if nxt:
                        self.assertNotIn("Reusing", nxt,
                            f"line {i+1}: single-condition resume still present")
                        break


# ── 6. SKILL.md content sanity ────────────────────────────────────────────

SKILL_MD = REPO_ROOT / ".claude" / "skills" / "earnings-prediction" / "SKILL.md"


class SkillMdContentSanityTests(unittest.TestCase):
    """Verify Step 9's edits landed correctly: heading level, location,
    SECTION_AUDIT_PATH in Input, all required fields, forbidden keys."""

    def setUp(self):
        self.text = SKILL_MD.read_text(encoding="utf-8")
        self.lines = self.text.splitlines()

    def test_phase_0_5_heading_at_h2_level(self):
        # Must use ## (not ####) per plan
        self.assertIn("## Phase 0.5 — Facts-Only Section Audit", self.text)
        self.assertNotIn("#### Phase 0.5", self.text)

    def test_phase_0_5_appears_between_phase_0_and_reasoning(self):
        # File-order check: Phase 0 → Phase 0.5 → Reasoning
        def _find(prefix):
            for i, line in enumerate(self.lines):
                if line.startswith(prefix):
                    return i
            return -1
        p0 = _find("## Phase 0 — Label Prior Lessons")
        p05 = _find("## Phase 0.5 — Facts-Only Section Audit")
        reasoning = _find("## Reasoning")
        self.assertNotEqual(p0, -1, "Phase 0 heading missing")
        self.assertNotEqual(p05, -1, "Phase 0.5 heading missing")
        self.assertNotEqual(reasoning, -1, "Reasoning heading missing")
        self.assertLess(p0, p05, "Phase 0.5 must appear after Phase 0")
        self.assertLess(p05, reasoning, "Phase 0.5 must appear before Reasoning")

    def test_input_section_mentions_section_audit_path(self):
        # Find the ## Input block and assert SECTION_AUDIT_PATH appears within it.
        in_input = False
        input_block = []
        for line in self.lines:
            if line.startswith("## Input"):
                in_input = True
                continue
            if in_input and line.startswith("## "):
                break
            if in_input:
                input_block.append(line)
        block_text = "\n".join(input_block)
        self.assertIn("SECTION_AUDIT_PATH", block_text,
            "## Input section must mention SECTION_AUDIT_PATH")

    def _phase_0_5_block(self) -> str:
        """Extract just the Phase 0.5 block for scoped substring assertions."""
        in_block = False
        out = []
        for line in self.lines:
            if line.startswith("## Phase 0.5 "):
                in_block = True
                continue
            if in_block and line.startswith("## "):
                break
            if in_block:
                out.append(line)
        return "\n".join(out)

    def test_phase_0_5_lists_all_seven_field_names(self):
        block = self._phase_0_5_block()
        for field in ("section", "key_facts", "bullish_signals", "bearish_signals",
                      "missing_or_unclear", "source_ids", "not_material_reason"):
            self.assertIn(f"`{field}`", block, f"Phase 0.5 missing field `{field}`")

    def test_phase_0_5_forbids_directional_keys(self):
        block = self._phase_0_5_block()
        # Must explicitly forbid these in the audit
        for forbidden in ("direction", "confidence_score",
                          "expected_move_range_pct", "final_call"):
            self.assertIn(forbidden, block,
                f"Phase 0.5 must mention forbidden key `{forbidden}`")
        # Sanity: the prohibition phrasing must appear
        self.assertIn("Do NOT include", block)


if __name__ == "__main__":
    unittest.main()
