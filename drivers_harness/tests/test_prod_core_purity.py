"""PROD-CORE purity CI check — Harness_BuilderPrompt.md section 9
("PROD-CORE vs TEST-SCAFFOLD partition") + section 3 RESERVED Pass-2/4 files.

WHY THIS FILE EXISTS (section 9, lines 451-459):
- PROD-CORE modules copy into production UNCHANGED. They must be pure and
  import NOTHING test-only. The explicitly-named PROD-CORE set is:
  driver_ids.py, validators.py, vocab_seed.py, reuse.py, render_catalog.py,
  run_one.py (which also hosts the pure learner_to_writer_input() adapter).
- TEST-SCAFFOLD modules stay in the harness and are NEVER imported by
  prod-core: registry_fake.py and run_sequence.py (plus apply_decision /
  cohort replay / eval glue / all of tests/).
- RULE (line 458): "a PROD-CORE module that imports a TEST-SCAFFOLD module is
  a BUG — it breaks 'copy in, no changes'." Section 9 line 459 mandates exactly
  this CI check: "grep PROD-CORE files for imports of scaffold modules -> must
  be empty." This test IS that CI check, run as pytest.

Also asserts the RESERVED Pass-2/4 files do NOT exist (section 3 lines 120-121,
130-131, 134; section 11 line 490). Their absence is REQUIRED in Pass 1.

This test is pure text inspection of the module source files — NO import of the
modules under test (so it cannot be fooled by import-time side effects) and NO
LLM / network / DB (section 0a / section 8).
"""
from __future__ import annotations

import ast
import os

import pytest

# ---------------------------------------------------------------------------
# Locate the harness root. tests/ lives directly under drivers_harness/, so the
# harness root (where the PROD-CORE modules live) is the parent of this file's
# directory. Resolved from __file__ so the check is location-independent.
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))      # drivers_harness/tests
HARNESS_ROOT = os.path.dirname(_THIS_DIR)                    # drivers_harness/

# The PROD-CORE module set, verbatim from Harness_BuilderPrompt.md section 9
# lines 452-454. learner_to_writer_input() is NOT a separate file — it lives in
# run_one.py (def confirmed in run_one.py), so checking run_one.py covers it.
PROD_CORE_MODULES = [
    "driver_ids.py",
    "validators.py",
    "vocab_seed.py",
    "reuse.py",
    "render_catalog.py",
    "run_one.py",
]

# The TEST-SCAFFOLD module names a prod-core file must NEVER import — section 9
# line 455. These are referenced by bare module name in import statements.
#
# Pass-2 (2026-05-29): synonym_fold is a TEST-SCAFFOLD stand-in for the
# ingestion-side :EquivalenceToken store (Harness_BuilderPrompt.md §4 / §11B;
# DriverOntology_Implementation.md §C/§F.10) — exactly like registry_fake /
# run_sequence. PROD-CORE must NOT import it: the §11B wiring is a PASSED-IN dict
# (build_vocab_snapshot(promoted_synonyms=...)), the prod seam where Neo4j rows
# arrive — vocab_seed fills it from the engine ONLY in tests, never by importing
# the engine. So synonym_fold is added to the forbidden-import set.
#
# Pass-3 (2026-05-29): apply_decision is the fake-writer APPLY step (§15.0) — a
# TEST-SCAFFOLD stand-in for the production Neo4j MERGE (§9 line 503: "apply_decision
# + the cohort replay" stays in the harness, NEVER imported by prod-core; §10 maps
# it to "the orchestrator + the real writer", NOT copied). It imports prod-core
# (driver_ids / vocab_seed) but NO prod-core module may import IT. Added to the
# forbidden-import set so the §9 partition keeps policing the new scaffold module.
SCAFFOLD_MODULE_NAMES = [
    "registry_fake", "run_sequence", "synonym_fold", "apply_decision",
]

# RESERVED Pass-4 files whose ABSENCE is required THROUGH Pass 2 — section 3
# lines 120-121 (llm_emit.py), lines 130-131 (tests/test_llm_layer2.py), line 134
# (tests/fixtures/evidence_samples.json), section 11 line 490.
#
# Pass-2 (2026-05-29): synonym_fold.py + tests/test_synonym_fold.py are NO LONGER
# reserved — they are the Pass-2 deliverable (Harness_BuilderPrompt.md §11B) and
# are NOW BUILT, so they are removed from this absent list. The remaining three
# files belong to Pass 4 (§13) and MUST STILL be absent (their presence in Pass 2
# would be a scope violation). synonym_fold.py is instead policed by the PROD-CORE
# import check above (it must never be imported by a prod-core module).
RESERVED_PASS4_FILES = [
    "llm_emit.py",
    os.path.join("tests", "test_llm_layer2.py"),
    os.path.join("tests", "fixtures", "evidence_samples.json"),
]


def _read_source(module_filename: str) -> str:
    """Read a PROD-CORE module's source text. Fails loudly if the file is
    missing (a missing prod-core module is itself a partition violation)."""
    path = os.path.join(HARNESS_ROOT, module_filename)
    assert os.path.isfile(path), (
        f"PROD-CORE module {module_filename} not found at {path}; the section 9 "
        f"partition cannot be verified."
    )
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _imported_names(source: str) -> set[str]:
    """Parse the module with the stdlib `ast` and return the set of TOP-LEVEL
    module names it imports (both `import X` / `import X.y` and `from X import
    ...`). Using ast (not a substring grep) means a scaffold name appearing in a
    comment, docstring, or string literal does NOT count as an import — only a
    real import statement does. This is stricter and more faithful to "imports a
    TEST-SCAFFOLD module" (section 9 line 458) than a raw text grep."""
    names: set[str] = set()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                # "import registry_fake.foo" -> top-level name "registry_fake"
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            # node.module is None for "from . import x" (relative, level>0).
            if node.module:
                names.add(node.module.split(".")[0])
    return names


# ---------------------------------------------------------------------------
# Core CI check (section 9 lines 451-459): no PROD-CORE module imports a
# TEST-SCAFFOLD module. Proves the prod-core set copies to production with zero
# changes. One assert-cluster, parametrized across the PROD-CORE files so each
# violation is reported against the specific offending module.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("module_filename", PROD_CORE_MODULES)
def test_prod_core_module_imports_no_scaffold(module_filename: str) -> None:
    """section 9 (PROD-CORE vs TEST-SCAFFOLD partition, lines 451-459):
    a PROD-CORE module that imports a TEST-SCAFFOLD module (registry_fake /
    run_sequence) is a BUG that breaks 'copy in, no changes'. EXPECTED: every
    prod-core module's import set is disjoint from {registry_fake, run_sequence}.
    """
    source = _read_source(module_filename)
    imported = _imported_names(source)
    offending = sorted(imported & set(SCAFFOLD_MODULE_NAMES))
    assert offending == [], (
        f"PROD-CORE module {module_filename} imports TEST-SCAFFOLD module(s) "
        f"{offending} — section 9 line 458: this breaks 'copy in, no changes'."
    )


def test_prod_core_no_substring_scaffold_import_lines() -> None:
    """section 9 line 459 (the mandate is literally: 'grep PROD-CORE files for
    imports of scaffold modules -> must be empty'). Belt-and-suspenders TEXT
    grep alongside the ast parse above: assert no prod-core file contains an
    'import registry_fake' / 'from registry_fake' / 'import run_sequence' /
    'from run_sequence' import LINE. EXPECTED: zero such lines across all
    prod-core files."""
    forbidden_line_prefixes = []
    for scaffold in SCAFFOLD_MODULE_NAMES:
        forbidden_line_prefixes.append(f"import {scaffold}")
        forbidden_line_prefixes.append(f"from {scaffold} ")
        forbidden_line_prefixes.append(f"from {scaffold}.")
        forbidden_line_prefixes.append(f"from {scaffold} import")

    violations: list[str] = []
    for module_filename in PROD_CORE_MODULES:
        source = _read_source(module_filename)
        for lineno, raw in enumerate(source.splitlines(), start=1):
            stripped = raw.strip()
            for prefix in forbidden_line_prefixes:
                if stripped.startswith(prefix):
                    violations.append(f"{module_filename}:{lineno}: {stripped}")
    assert violations == [], (
        "PROD-CORE files contain TEST-SCAFFOLD import line(s) — section 9 "
        "line 459 says this grep MUST be empty:\n" + "\n".join(violations)
    )


def test_prod_core_modules_all_present() -> None:
    """section 9 lines 452-454: the named PROD-CORE set must all exist as files
    in the harness root (otherwise the partition check is vacuous). EXPECTED:
    all six prod-core module files are present."""
    missing = [
        m for m in PROD_CORE_MODULES
        if not os.path.isfile(os.path.join(HARNESS_ROOT, m))
    ]
    assert missing == [], f"PROD-CORE module file(s) missing: {missing}"


# ---------------------------------------------------------------------------
# RESERVED Pass-4 files MUST NOT exist through Pass 2 (section 3 lines 120-121/
# 130-131/134; section 11 line 490). Their absence is a Pass-1/Pass-2 deliverable.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("reserved_relpath", RESERVED_PASS4_FILES)
def test_reserved_pass4_file_absent(reserved_relpath: str) -> None:
    """section 3 (folder layout, lines 120-121/130-131/134) + section 11 line
    490: the Pass-4 RESERVED files (llm_emit.py, tests/test_llm_layer2.py,
    tests/fixtures/evidence_samples.json) must NOT be created before Pass 4.
    EXPECTED: each reserved path does not exist on disk. (synonym_fold.py +
    tests/test_synonym_fold.py are NO LONGER reserved — they are the now-built
    Pass-2 deliverable per §11B.)"""
    path = os.path.join(HARNESS_ROOT, reserved_relpath)
    assert not os.path.exists(path), (
        f"RESERVED Pass-4 file {reserved_relpath} exists at {path} — section 3 "
        f"/ section 11 require its ABSENCE until Pass 4 (it belongs to a later pass)."
    )


def test_pass2_synonym_fold_now_present() -> None:
    """Pass-2 deliverable (Harness_BuilderPrompt.md §11B line 540): the
    previously-reserved synonym_fold.py + tests/test_synonym_fold.py are NOW
    BUILT. EXPECTED: both exist (the converse of the old Pass-1 absent check),
    so the reserved-file logic above is verifiably scoped to Pass-4 only and the
    Pass-2 engine + its bucket-I tests are present on disk."""
    for built_relpath in ("synonym_fold.py",
                          os.path.join("tests", "test_synonym_fold.py")):
        path = os.path.join(HARNESS_ROOT, built_relpath)
        assert os.path.isfile(path), (
            f"Pass-2 deliverable {built_relpath} missing at {path} — §11B "
            f"requires synonym_fold.py + tests/test_synonym_fold.py be built."
        )


def test_pass3_apply_decision_and_replay_present() -> None:
    """Pass-3 deliverable (Harness_BuilderPrompt.md §15.0 / §15A / §15C): the
    fake-writer apply step apply_decision.py + the accumulation-replay tests +
    the false-reject regression tests are NOW BUILT. EXPECTED: all three exist.
    apply_decision is policed as a TEST-SCAFFOLD module by the import check above
    (it must never be imported by prod-core, §9 line 503)."""
    for built_relpath in (
        "apply_decision.py",
        os.path.join("tests", "test_accumulation_replay.py"),
        os.path.join("tests", "test_false_reject.py"),
    ):
        path = os.path.join(HARNESS_ROOT, built_relpath)
        assert os.path.isfile(path), (
            f"Pass-3 deliverable {built_relpath} missing at {path} — §15.0/§15A/"
            f"§15C require apply_decision + the replay + false-reject tests be built."
        )
