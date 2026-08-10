"""The G-suite's EXAM half (G12-G19) + the coverage registry for all 35.

Why a registry: "G1-G35" was a PLAN for several review rounds, and a plan reads
exactly like a proof until someone checks. This file makes the claim mechanical
— every G-number must be declared with an honest status, and every G declared
`code` must have a real test function behind it, here or in the production
suite. A G-number that quietly loses its test fails this file.

STATUS VOCABULARY (deliberately not all "code"):
  code           - a runnable test proves it today
  grading        - only hidden grading can catch it (a MEANING error); the
                   fixture is registered here, and the honesty is the point
  gated-switch   - provable only after the owner-approved atomic switch
                   (deleting v1, applying the law patch, re-freezing the packet)
"""
import ast
import hashlib
import io
import json
import os
import pathlib
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", ".."))
PKG = os.path.join(_HERE, "exp5_rev4_package.md")
LEDGER = os.path.join(_HERE, "g_status_ledger.md")
PINS = os.path.join(_HERE, "rev4_pin_inventory.md")
PATCH = os.path.join(_HERE, "exp5_rev4_docs.patch")
PROD_TESTS = os.path.join(_REPO, "driver", "core", "test_prepared_fact_v2.py")
ATTACK_TESTS = os.path.join(_REPO, "driver", "core", "test_v2_attacks.py")

sys.path.insert(0, _HERE)


# --------------------------------------------------------------------------
# THE REGISTRY — one row per G-number, no gaps, no silent downgrades.
# --------------------------------------------------------------------------
G_COVERAGE = {
    # G number -> (status, PYTEST NODE ID, remaining-leg reason)
    #
    # THE SELECTOR IS A NODE ID, not a bare function name. One registered name
    # existed in TWO files (G18), so a bare name let the weaker of the two
    # satisfy the row: the harness copy checked three modules, the driver copy
    # four — including `xbrl_attach.py`, the #825 door. A node id cannot be
    # satisfied by a same-named test somewhere else.
    #
    # status vocabulary (closed): code | partial | grading | gated-switch
    # Every partial/grading/gated-switch row states what is NOT yet proven.
    "G1": ("code", "driver/core/test_prepared_fact_v2.py::test_G1_converter_api_fence_by_reflection",
            ""),
    "G2": ("code", "driver/core/test_prepared_fact_v2.py::test_G2_quote_and_concept_name_cannot_alter_a_value",
            ""),
    "G3": ("code", "driver/core/test_prepared_fact_v2.py::test_G3_percent_family_units_are_distinct",
            ""),
    "G4": ("code", "driver/core/test_prepared_fact_v2.py::test_G4_scale_via_model_stated_multiplier",
            ""),
    "G5": ("code", "driver/core/test_prepared_fact_v2.py::test_G5_slot_structure_failures",
            ""),
    "G6": ("code", "driver/core/test_prepared_fact_v2.py::test_G6_wrong_scale_word_elsewhere_in_the_SAME_part_still_fails",
            ""),
    "G7": ("code", "driver/core/test_prepared_fact_v2.py::test_G7_unknown_units_still_multiply",
            ""),
    "G8":  ("partial",
        "driver/core/test_prepared_fact_v2.py::test_G8_per_x_rides_once_at_fact_level",
        "per_x rides once at fact level and is proven; the NAME-13 denominator check "
        "is deleted from Core with check_per_x_against_name and moves to the POST "
        "per-X naming feature; wiring into the admission kernel remains unprovable "
        "because the kernel is not built"),
    "G9": ("gated-switch", ".claude/plans/Drivers/experiments/harness/test_g_suite.py::test_G9_one_shared_validation_entry_point_exists",
            "one shared validation entry point exists and is proven; the scorer and "
            "run_event both moving onto it IS the atomic switch"),
    "G10": ("code", "driver/core/test_prepared_fact_v2.py::test_G10_order_free_under_full_permutation",
            ""),
    "G11": ("partial", "driver/relocation/test_packet_items_through_the_door.py::test_every_saved_packet_item_attaches_on_its_LITERAL_evidence",
            "re-pointed at the strongest proof: 11 saved packet items, loaded from "
            "the TRACKED wp3 packets, attach on their literal source evidence against "
            "real cached filings and live Neo4j. The remaining leg is genuinely "
            "unprovable, not merely unbuilt: the event view those quotes are checked "
            "against is scaffolding derived from each item's own quote, because the "
            "historical text the reader was actually shown was never archived. No "
            "test can recover a record that does not exist"),
    "G12": ("gated-switch", ".claude/plans/Drivers/experiments/harness/test_g_suite.py::test_G12_the_live_launcher_still_serves_the_v1_contract",
            "the rev-4 prompt is authored, but the live launcher still serves the v1 "
            "37-field contract; the assembled prompt is regenerated at the switch"),
    "G13": ("grading", ".claude/plans/Drivers/experiments/harness/test_g_suite.py::test_G13_attack_fixtures_are_registered_and_classified",
            "a MEANING error: only hidden grading can catch it, never a code proof"),
    "G14": ("partial", ".claude/plans/Drivers/experiments/harness/test_g_suite.py::test_G14_guidance_legacy_path_is_untouched",
            "the legacy guidance suite is untouched; hint fields are no longer refused "
            "by a hint-specific branch — they refuse as unexpected keys at the exact-key "
            "owner; 'never a WRITER input' still needs the switched writer"),
    "G15": ("partial", ".claude/plans/Drivers/experiments/harness/test_g_suite.py::test_G15_xbrl_declared_metadata_path_is_untouched",
            "S14: the dead declared-scale helper call removed; proves the "
            "legacy v1 XBRL suite only"),
    "G16": ("gated-switch", ".claude/plans/Drivers/experiments/harness/test_g_suite.py::test_G16_old_path_removal_is_gated_on_the_switch",
            "old-path removal is not provable until the owner-approved atomic switch"),
    "G17": ("code", ".claude/plans/Drivers/experiments/harness/test_g_suite.py::test_G17_transport_is_exact_and_refuses_ambiguity",
            ""),
    "G18": ("partial", "driver/core/test_prepared_fact_v2.py::test_G18_the_new_modules_reach_no_graph_write",
            "the new modules are write-free (proven, and the driver-side proof covers "
            "xbrl_attach too); 'zero writes reachable from the EXAM' needs the "
            "run_event exam path, which is switch-gated"),
    "G19": ("partial", ".claude/plans/Drivers/experiments/harness/test_g_suite.py::test_G19_two_rebuilds_are_byte_identical",
            "docs-patch determinism is proven; contract/launcher/manifest "
            "regeneration happens at the switch"),
    "G20": ("code", "driver/core/test_prepared_fact_v2.py::test_G20_table_wide_scale_applied_once",
            ""),
    # G21/G22/G30 — `partial`, AND THE FLIP-FLOP IS THE LESSON. One round moved
    # them to the real-data attach tests as "the strongest proof"; the next moved
    # them back to the synthetic tests as "the broadest coverage". Both were
    # wrong, because the two sets miss OPPOSITE legs: the real-data tests carry no
    # negative case, and the synthetic tests never touch real Fiscal packet data.
    # No single registered selector covers either rule end to end, and `code`
    # means one selector does. Naming the absent leg is the honest answer;
    # promoting the row is not.
    "G21": ("partial", "driver/core/test_v2_attacks.py::test_ATTACK_a_wrong_declared_scale_fails_the_certified_reconcile",
            "the never-double-scaled rule is proven on synthetic input; the same "
            "rule against a real Fiscal packet row is not exercised by this "
            "selector"),
    "G22": ("partial", "driver/core/test_prepared_fact_v2.py::test_G22_the_xbrl_lane_does_not_require_quote_local_evidence",
            "the XBRL lane is proven; the TEXT lane's matching requirement — the "
            "other half of the rule — is not touched by this selector"),
    "G23": ("partial", "driver/core/test_round10_event_boundary.py::test_MIXED_TYPE_keys_are_refused_cleanly_at_every_door",
            "an old payload now fails as an ordinary unexpected-key refusal at every "
            "door; the retired-name-specific branch and its message are deleted. "
            "Fiscal actually ceasing to emit the fields is O-f, after the boundary proof"),
    # THE FIXTURE ID IS THE LINK. "Only grading can catch this" is a claim about
    # a specific attack, so the row names the attack: A6 is the one quote holding
    # both '$13.9 billion' and '$382 million' with the multipliers swapped. The
    # check below requires the id to exist in the fixture registry AND to be
    # classified `grading` there — rename or reclassify it and this row fails.
    "G24": ("grading", "driver/core/test_prepared_fact_v2.py::test_G24_membership_alone_cannot_catch_a_wrong_slot_assignment",
            "a MEANING error: only hidden grading can catch a wrong slot "
            "assignment (fixture A6_swapped_scale_inside_one_quote)"),
    "G25": ("partial", "driver/core/test_prepared_fact_v2.py::test_G25_emit_once_violation_blocks_a_silent_pass",
            "emit-once detection is proven; the reliability gate that consumes it "
            "lives in the scorer, which moves at the switch"),
    "G26": ("partial", "driver/core/test_prepared_fact_v2.py::test_G26_duration_and_instant_are_meaning_not_date_count",
            "the illegal combination is code-caught; 'a balance with a window still "
            "grades instant' is a MEANING judgment no code can prove"),
    "G27": ("code", "driver/core/test_prepared_fact_v2.py::test_G27_a_point_is_not_a_floor",
            ""),
    "G28": ("code", ".claude/plans/Drivers/experiments/harness/test_g_suite.py::test_G28_source_id_echo_mismatch_is_refused",
            ""),
    "G29": ("code", "driver/core/test_prepared_fact_v2.py::test_G29_two_shape_fields_together_park",
            ""),
    # SAME AS G21/G22, and worse: the registered test is named "the LIVE fiscal
    # packet row" and is eight lines that load no packet, reach no store, and
    # touch no graph. Its synthetic row proves the consistency equation; the live
    # packet leg its own name promises is not exercised anywhere.
    "G30": ("partial", "driver/relocation/test_real_726_end_to_end.py::test_the_REAL_726_fact_binds_to_its_live_row_and_its_filing",
            "the consistency equation is proven on a synthetic row; despite the "
            "test's name no live Fiscal packet is loaded, so the real-packet leg "
            "and the violation case are both unproven here"),
    "G31": ("code", "driver/core/test_prepared_fact_v2.py::test_G31_compensated_misread_can_never_grade_correct",
            ""),
    "G32": ("partial", ".claude/plans/Drivers/experiments/harness/test_g_suite.py::test_G32_source_id_is_delivered_in_the_prompts_event_view",
            "source_id is in the authored prompt; the live event view is regenerated "
            "with the launcher at the switch"),
    "G33": ("code", "driver/core/test_v2_attacks.py::test_ATTACK_an_invalid_slice_kind_is_rejected",
            ""),
    "G34": ("code", "driver/core/test_prepared_fact_v2.py::test_G34_company_confirmed_never_stores_a_guessed_false",
            ""),
    "G35": ("partial", "driver/core/test_prepared_fact_v2.py::test_G35_per_share_cell_lawfully_keeps_multiplier_one",
            "the per-share cell is proven; the aggregate misreading is a MEANING "
            "error only grading can catch (fixture A6-class)"),
}



def _test_names(path):
    tree = ast.parse(io.open(path, encoding="utf-8").read())
    return {n.name for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}



# ---------------------------------------------------------------------------
# THE staged-file set — ONE definition. Every staging check below DERIVES from
# it, so adding a staged module can never leave a check behind (adding
# `xbrl_attach.py` did exactly that: the import check kept its own hand-written
# list of three names and stopped seeing the fourth).
# ---------------------------------------------------------------------------
# EXACT PATHS, not bare filenames. Matching on the basename alone let a staged
# NAME in the WRONG DIRECTORY through — `driver/relocation/xbrl_attach.py` was
# accepted as "the staged file" although the staged file is
# `driver/core/xbrl_attach.py`. A file is only staged where it was approved to
# live. The basename set below is DERIVED, so there is still ONE definition.
STAGED_PATHS = frozenset({"driver/core/slot_convert.py",
                          "driver/core/prepared_fact_v2.py",
                          "driver/core/fact_match.py",
                          "driver/core/xbrl_attach.py"})
STAGED_FILES = frozenset(p.rsplit("/", 1)[-1] for p in STAGED_PATHS)


def unexpected_production_files(status_lines, allowed, staged=STAGED_PATHS):
    """Production paths that are neither individually allowlisted (modified) nor
    the staged set itself (untracked).

    UNTRACKED FILES USED TO BE DROPPED ENTIRELY (`if not ln.startswith("??")`),
    so a brand-new production module could be added and this gate saw nothing.
    Tests are excluded because the assertion is about PRODUCTION.

    MEMBERSHIP IS BY PATH, NOT BY GIT'S STATUS LETTER. The staged-set allowance
    used to apply only to `??` lines, so the moment these very modules were
    `git add`ed for their own commit — the whole point of staging them — git
    reported them as `A ` and the gate called all four "unexpected". Whether a
    file is one of the new v2 modules is a fact about its path; it does not
    change when the index changes.
    """
    out = []
    for ln in status_lines:
        if not ln.strip():
            continue
        path = ln.split()[-1]
        name = path.split("/")[-1]
        if not path.endswith(".py") or name.startswith("test_"):
            continue
        if path in staged:                  # the EXACT path, never the basename
            continue
        if path not in allowed:
            out.append(path)
    return sorted(out)


#: PC-4 (#827): the ONE live->staged import edge the closed C1+C10 rows require,
#: at SYMBOL granularity — (live module, staged module, symbol). CANONICAL_UNITS
#: is slot_convert's own published unit vocabulary and driver_validators must ask
#: it rather than keep a second copy, which is exactly what C1+C10 decided. An
#: ALIAS of this symbol is the same symbol and passes; importing the whole
#: module, a second slot_convert symbol, or any other live->staged pair does not.
_ALLOWED_LIVE_STAGED_IMPORTS = frozenset({
    ("driver_validators.py", "driver.core.slot_convert", "CANONICAL_UNITS")})


def live_modules_importing_staged(sources, staged=STAGED_FILES):
    """`sources` = {filename: text} for LIVE modules. The module names come from
    `staged`, never from a second hand-maintained list.

    PC-4 (#827): this used to be `if mod in src` — a RAW SUBSTRING SCAN over the
    file's text, so a module NAME appearing in a comment, a docstring or even a
    longer identifier counted as an import. It was false on the current
    candidate: three of the four edges it reported were prose only, and the one
    real edge it did find was the lawful C1+C10 one. A gate that cannot tell an
    import from a sentence about an import proves nothing, and this one guards
    the staged/live boundary, so it now asks the AST.

    What counts as an edge is a fact about Python: an `import` or `from ...
    import` statement naming a staged module. Anything else in the text is
    prose. The single lawful exception is declared above at symbol granularity,
    so widening it — a second symbol, or the whole module — still fails.
    """
    #: the staged set as FULL dotted module paths — derived, never re-listed
    full = frozenset("driver.core." + n[:-3] for n in staged)
    #: the package these `sources` live in; `.` means this, `..` its parent
    HOME = "driver.core"

    def reaches(node):
        """Every staged module this import statement reaches, as
        (resolved_module, symbol_or_None). `None` means the WHOLE module.

        THE MODULE IS RESOLVED, NEVER MATCHED BY BASENAME (PC-4 corrective,
        SEQ 860). The previous version mapped any matching tail to
        `driver.core.<tail>`, which was wrong in BOTH directions and one of them
        was a false ALLOWANCE: `from unrelated.slot_convert import
        CANONICAL_UNITS` collected the C1 exception although it never reaches
        staged code, and `import unrelated.slot_convert` /
        `from ..relocation import slot_convert` were REPORTED as staged edges
        they are not. A basename is not an identity; the package is.

        Resolution is ordinary Python: an absolute import is already its own
        path, and a relative one counts dots up from HOME — `.` is driver.core,
        `..` is driver — so `from ..core.slot_convert import X` and
        `from .slot_convert import X` resolve to the same module and get the
        same verdict, while `from ..relocation import slot_convert` resolves to
        driver.relocation and is simply not staged.
        """
        if isinstance(node, ast.Import):                 # import a.b.c
            return [(a.name, None) for a in node.names if a.name in full]
        if node.level:                                   # from .x / ..x import
            parts = HOME.split(".")
            if node.level > len(parts):                  # climbs past the root
                return []
            base = ".".join(parts[:len(parts) - node.level + 1])
        else:
            base = ""                                    # absolute
        mod = ".".join(p for p in (base, node.module or "") if p)
        if mod in full:                                  # <staged> import SYMBOL
            return [(mod, a.name) for a in node.names]
        # <package> import <staged> — the module itself is the imported name
        return [(f"{mod}.{a.name}", None)
                for a in node.names if f"{mod}.{a.name}" in full]

    out = []
    for fn, src in sources.items():
        try:
            tree = ast.parse(src)
        except SyntaxError:                  # a live module that will not parse
            out.append(f"{fn} does not parse")   # is its own, louder failure
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            for mod, symbol in reaches(node):
                if symbol is None:
                    # the WHOLE module reaches every symbol in it, so it is
                    # never covered by a symbol-granular allowance
                    out.append(f"{fn} imports module {mod}")
                # the ASNAME is irrelevant: an alias of a symbol IS that
                # symbol, and `*` is never a named symbol so it can never
                # be the allowed one.
                elif (fn, mod, symbol) not in _ALLOWED_LIVE_STAGED_IMPORTS:
                    out.append(f"{fn} imports {mod}.{symbol}")
    return sorted(out)


_STATUS_VOCAB = ("code", "partial", "grading", "gated-switch")
_TEST_ROOTS = ("driver", ".claude/plans/Drivers/experiments/harness")


def _live_test_inventory():
    """Every test function under the BOUNDED roots, RECURSIVELY, as node ids.

    Derived, never hand-listed: the previous version knew only three named files,
    so a proof living anywhere else could not be checked at all — and a proof
    registered by BARE NAME could be satisfied by a same-named test in a file
    nobody had named.
    """
    import ast
    found = set()
    for root in _TEST_ROOTS:
        for f in sorted(pathlib.Path(_REPO, root).rglob("test_*.py")):
            rel = f.relative_to(_REPO).as_posix()
            try:
                tree = ast.parse(f.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in tree.body:
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    found.add(f"{rel}::{node.name}")
    return found


def test_the_registry_is_exactly_G1_to_G35_with_a_closed_vocabulary():
    """PROPERTIES, not a transcribed set. The old version asserted the exact
    gated/partial/grading membership by hand, which is a second status mix that
    goes stale the moment a row moves — the very failure this suite exists to
    stop."""
    assert sorted(G_COVERAGE, key=lambda g: int(g[1:])) == \
        [f"G{i}" for i in range(1, 36)], "a G number is missing, duplicated or extra"
    for g, (status, selector, reason) in G_COVERAGE.items():
        assert status in _STATUS_VOCAB, f"{g}: {status!r} is outside the vocabulary"
        assert "::" in selector, f"{g}: {selector!r} is not a node id"
        if status == "code":
            assert not reason, f"{g}: a code row must not carry a remaining leg"
        else:
            assert reason.strip(), f"{g}: {status} must state what is NOT proven"


def test_every_registered_proof_EXISTS_in_the_live_inventory():
    """Each selector must name a test that really exists under the bounded roots
    — not a stale name, and not a same-named test in some other file."""
    inventory = _live_test_inventory()
    missing = {g: sel for g, (_s, sel, _r) in G_COVERAGE.items()
               if sel not in inventory}
    assert not missing, f"registered but absent from the live inventory: {missing}"


def _registry_selectors():
    return sorted({sel for _s, sel, _r in G_COVERAGE.values()})


def _live_selectors():
    """Which registered proofs carry the `live` marker — asked of pytest ONCE,
    never inferred from a hand list. The child's EXIT CODE is checked: a usage
    error or a collection crash used to yield an EMPTY live set in silence,
    misfiling every live proof into the clean lane. And no cache provider — a
    collection helper must not write .pytest_cache into the tree it reads."""
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:randomly",
         "-p", "no:cacheprovider", "--no-header",
         "-m", "live", "--collect-only", *_registry_selectors()],
        cwd=_REPO, capture_output=True, text=True)
    assert r.returncode == 0, (
        f"live-selector collection exited {r.returncode} — the live/clean "
        f"split cannot be derived from a failed collection:\n{r.stdout[-1500:]}")
    live = set()
    for ln in r.stdout.splitlines():
        ln = ln.strip()
        if "::" in ln and not ln.startswith("<"):
            base = ln.split("[")[0]
            live |= {s for s in _registry_selectors() if s.split("[")[0] == base}
    return live


def _run_selectors(selectors, env=None):
    """{nodeid: outcome} for a selector set. Checks the child's EXIT CODE and
    builds identities from JUnit `classname`."""
    with tempfile.TemporaryDirectory() as tmp:
        xml = os.path.join(tmp, "r.xml")
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:randomly",
             "--no-header", "--tb=line", "-p", "no:cacheprovider",
             f"--junit-xml={xml}", *sorted(selectors)],
            cwd=_REPO, capture_output=True, text=True, env=env)
        # THE UNCHECKED EXIT CODE, now checked. 0 = all passed, 1 = some failed;
        # 2-5 mean interrupted, internal error, usage error or nothing collected,
        # and every one of those used to reach a verdict as though the run was
        # meaningful. I reported this repaired once before actually repairing it.
        assert proc.returncode in (0, 1), (
            f"the registry run exited {proc.returncode} — it did not execute as "
            f"asked:\n{proc.stdout[-2000:]}")
        assert os.path.exists(xml), (
            f"pytest produced no report — the proofs could not even be "
            f"collected:\n{proc.stdout[-2000:]}")
        cases = list(ET.parse(xml).getroot().iter("testcase"))
    assert cases, "zero test cases ran — an empty selection is not a pass"
    out = {}
    for c in cases:
        # `classname`, NEVER `file`: pytest leaves `file` empty here, so every
        # identity read `None::test_x`. Also mine, also previously claimed fixed.
        node = f"{c.get('classname') or '?'}::{c.get('name')}"
        kind = next((k for k in ("failure", "error", "skipped")
                     if c.find(k) is not None), None)
        out[node] = kind or "passed"
    return out


def test_the_registrys_CLEAN_proofs_run_GREEN_without_any_credential(tmp_path):
    """The registry's non-live proofs must pass in a process with NO credentials.

    THE FALSE GREEN THIS CLOSES, and it is the reason this test is split in two:
    the single combined version invoked EVERY registered selector by node id, so
    `-m live` filtering never applied to it and G11's eleven real-packet checks
    ran inside what was called the clean lane. They skipped without a database —
    and a skip here is a failure — yet the test passed, because an earlier test in
    the same process had already reloaded the real `.env`. Run alone it failed.
    Order-dependence is not a proof.

    THE ENVIRONMENT IS THE GATE'S OWN ALLOWLIST, not a credential blocklist: a
    blocklist admits the next credential name nobody enumerated (probed:
    GRAPHDB_LOGIN sailed straight through) and it kept the REAL user HOME, so
    ~-resident secrets stayed reachable inside a lane called credential-free.
    """
    live = _live_selectors()
    clean = [s for s in _registry_selectors() if s not in live]
    assert clean, "every registered proof is live — the split is meaningless"
    results = _run_selectors(clean, env=_gate().sanitized_env(_REPO,
                                                              str(tmp_path)))
    bad = {n: o for n, o in results.items() if o != "passed"}
    assert not bad, (
        f"registered proofs did not PASS in a credential-free process (a skip is "
        f"not a proof): {bad}")


@pytest.mark.live
def test_the_registrys_LIVE_proofs_run_GREEN_against_the_real_graph():
    """The other half. These need the graph, so they belong in the live lane and
    nowhere else — never smuggled into a clean run by an explicit node id."""
    live = _live_selectors()
    assert live, "no registered proof is live — did the markers move?"
    results = _run_selectors(live)
    bad = {n: o for n, o in results.items() if o != "passed"}
    assert not bad, f"live registered proofs did not PASS: {bad}"


def test_every_registered_proof_is_SELECTABLE():
    """Every selector must resolve to something pytest can run. Collection only —
    no execution, so this holds with or without a database."""
    import subprocess as _sp
    selectors = _registry_selectors()
    r = _sp.run([sys.executable, "-m", "pytest", "-q", "-p", "no:randomly",
                 "--no-header", "--collect-only", "-p", "no:cacheprovider",
                 *selectors], cwd=_REPO, capture_output=True, text=True)
    assert r.returncode in (0, 1), f"collection exited {r.returncode}: {r.stdout[-1500:]}"
    collected = sum(1 for ln in r.stdout.splitlines() if "::" in ln)
    assert collected >= len(selectors), \
        f"{len(selectors)} selectors collected only {collected} tests"


def test_every_grading_row_points_at_a_registered_grading_fixture():
    """A `grading` row means only hidden grading can catch the error, so its proof
    must really reach the attack-fixture registry.

    TWO FALSE GREENS THIS CLOSES.

    The first: the old check asked `name in <this file's text>` — and the registry
    row itself lives in this file, so the row satisfied the assertion about
    itself. It could never fail.

    The second was MINE, added while fixing the first: `or "attack" in
    body.lower()`. G24's body contains no fixture reference at all, and the word
    "attack" appears in its docstring, so the fallback passed it. A word is not a
    link. Both routes below are structural:

      - the test's own body reads the fixture registry (G13, which checks the
        whole set); or
      - the registry row NAMES a fixture id that exists in the registry AND is
        classified `grading` there (G24). Rename or reclassify the fixture and
        the row fails.
    """
    fixtures = json.load(io.open(ATTACK_FIXTURES, encoding="utf-8"))["attacks"]
    grading_ids = {a["id"] for a in fixtures if a["caught_by"] == "grading"}
    all_ids = {a["id"] for a in fixtures}
    grading = {g: (sel, reason) for g, (st, sel, reason) in G_COVERAGE.items()
               if st == "grading"}
    assert grading, "if nothing is grading-only any more, change this deliberately"
    for g, (sel, reason) in grading.items():
        rel, name = sel.split("::")
        src = io.open(os.path.join(_REPO, rel), encoding="utf-8").read()
        fn = next((n for n in ast.parse(src).body
                   if isinstance(n, ast.FunctionDef) and n.name == name), None)
        assert fn is not None, f"{g}: {name} is not DEFINED in {rel}"
        body = ast.get_source_segment(src, fn) or ""
        named = sorted(i for i in all_ids if i in reason)
        assert "ATTACK_FIXTURES" in body or named, (
            f"{g}: {name} neither reads the fixture registry nor names a fixture "
            f"id in its reason, so calling it a grading proof is unsupported")
        wrong = [i for i in named if i not in grading_ids]
        assert not wrong, (
            f"{g} names fixture(s) {wrong} that the registry does NOT classify "
            f"as grading-caught — a code-caught attack cannot justify a grading "
            f"row")


_G_RANGE = re.compile(r"g1\s*[-–—]\s*g35", re.I)
_FINISHED = ("complete", "green", "implemented", "proven", "certified")
_NEGATED = ("not", "never", "planned", "pending", "unproven", "overstat")


def g_range_overclaims(text, non_code_rows):
    """Lines declaring the WHOLE G range finished while the registry says it is
    not. Returns the offending lines.

    THE TRIGGER IS THE RANGE TOKEN, not a phrase catalogue: a line may discuss
    G1-G35 freely, and may say it is unfinished; it may not say it is done while
    rows are outside `code`. Negation anywhere on the line excuses it, because
    the package's dated review history legitimately records earlier claims of
    exactly that shape ("planned-not-proven", "OVERSTATED ... as complete"), and
    rewriting history to satisfy a checker is the opposite of what this suite is
    for.

    TWO STATED LIMITS, not hidden: a line that BOTH claims completion and carries
    a negation elsewhere is not flagged, and whether the package's MEANING is
    honest stays a human read — Part J says which half is which.
    """
    if not non_code_rows:
        return []                      # nothing left to overclaim
    bad = []
    for ln in text.splitlines():
        low = ln.lower()
        if not _G_RANGE.search(low) or any(n in low for n in _NEGATED):
            continue
        if any(w in low for w in _FINISHED):
            bad.append(ln.strip())
    return bad


def test_the_package_never_declares_the_G_RANGE_FINISHED_while_rows_are_not():
    """THE FALSE GREEN THIS CLOSES: the old version asserted only that the string
    "G1-G35" was PRESENT in the package. A package reading "G1-G35 ARE ALL
    COMPLETE" satisfied it — and the live package did carry "G1-G35 are
    implemented and green" while fifteen registry rows were not `code`.

    The rule is exercised BOTH WAYS on synthetic text before being applied to the
    real package, so a rule that cannot fail cannot pass this test either.
    """
    non_code = [g for g, (s, _sel, _r) in G_COVERAGE.items() if s != "code"]
    assert non_code, "if every row is `code` now, retire this test deliberately"

    # POSITIVE CONTROLS — each MUST be caught.
    for line in ("G1-G35 are implemented and green",
                 "G1-G35 ARE ALL COMPLETE",
                 "every one of G1–G35 is proven today",
                 "status: G1 - G35 certified"):
        assert g_range_overclaims(line, non_code) == [line], \
            f"the overclaim rule missed {line!r} — it cannot catch its own class"
    # NEGATIVE CONTROLS — honest and historical lines must NOT be caught.
    for line in ("the package already labels G1-G35 planned-not-proven",
                 "G1-G35 planned-not-implemented — CONFIRMED CORRECT STATE",
                 "G1-G35 status lives in the generated ledger",
                 "the first note OVERSTATED G1-G35 as complete"):
        assert g_range_overclaims(line, non_code) == [], \
            f"the overclaim rule falsely flagged {line!r}"
    # AND THE CONTROL THAT MAKES IT MEAN SOMETHING: with nothing outside `code`,
    # the same sentence is not an overclaim at all.
    assert g_range_overclaims("G1-G35 are implemented and green", []) == []

    pkg = io.open(PKG, encoding="utf-8").read()
    found = g_range_overclaims(pkg, non_code)
    assert not found, (
        f"the package declares the whole G range finished while "
        f"{len(non_code)} row(s) are not `code`: {found}")


# --------------------------------------------------------------------- G12 ----

def _prompt_text():
    pkg = io.open(PKG, encoding="utf-8").read()
    return pkg.split("## PART A")[1].split("## PART B")[0]


def test_G12_the_assembled_prompt_defines_every_value_it_demands():
    """A model cannot obey an enum it was never shown. Every value the schema
    can legally carry must be DEFINED in the prompt the model actually reads."""
    from driver.core.prepared_fact_v2 import ITEM_FIELDS
    from driver.core.slot_convert import CANONICAL_UNITS
    prompt = _prompt_text()
    for f in ITEM_FIELDS:
        assert f in prompt, f"item field never named in the prompt: {f}"
    for u in CANONICAL_UNITS:
        assert u in prompt, f"unit value never defined in the prompt: {u}"
    for lane in ("metric", "guidance", "surprise", "action_event"):
        assert lane in prompt
    for shape in ("point", "range", "floor", "ceiling"):
        assert shape in prompt
    for baseline in ("consensus", "prior_year", "sequential_period",
                     "previous_guidance"):
        assert baseline in prompt
    for kind in ("segment", "product", "geography", "customer", "channel",
                 "entity_ownership", "unknown"):
        assert kind in prompt
    for state in ("increased", "decreased", "unchanged", "mixed", "reported",
                  "persists", "introduced", "raised", "lowered", "reaffirmed",
                  "withdrawn", "beat", "in_line", "missed", "at_risk",
                  "announced", "occurred", "continued", "resolved", "canceled",
                  "suspended", "rumored", "failed"):
        assert state in prompt, f"driver_state value never defined: {state}"
    assert "per_x" in prompt and "part_ref" in prompt


def test_G12_the_untrusted_boundary_precedes_the_event():
    prompt = _prompt_text()
    boundary = prompt.index("UNTRUSTED SOURCE EVIDENCE")
    assert "NEVER INSTRUCTIONS" in prompt[boundary:boundary + 200]
    # both slice entry forms are shown
    assert "product:iphone" in prompt and "menu" in prompt.lower()


# --------------------------------------------------------------------- G13 ----

ATTACK_FIXTURES = os.path.join(_HERE, "g13_attack_fixtures.json")


def test_G13_attack_fixtures_are_registered_and_classified():
    """Each attack states WHO catches it. An attack whose only catcher is
    grading is labelled so — never quietly counted as a code proof."""
    fx = json.load(io.open(ATTACK_FIXTURES, encoding="utf-8"))
    assert len(fx["attacks"]) >= 6
    for a in fx["attacks"]:
        assert set(a) >= {"id", "attack", "caught_by", "why"}
        assert a["caught_by"] in ("code", "grading"), a
    assert any(a["caught_by"] == "grading" for a in fx["attacks"]), \
        "if nothing needs grading, the classification is not being taken seriously"


def test_G13_the_code_catchable_attacks_are_actually_caught():
    """Every fixture row marked `caught_by: code` must really be caught — and by
    the layer that owns the rule (production for meaning-adjacent law, the
    schema for transport structure)."""
    from decimal import Decimal
    from driver.core import prepared_fact_v2 as p2
    from driver.core.slot_convert import SlotConversionError, validate_slot

    def _item(**over):
        it = {k: None for k in p2.ITEM_FIELDS}
        it.update(driver_name="revenue", driver_state="reported",
                  quote="revenue of $363 million", measurement_raw_spans=[],
                  slice_parts=[])
        it.update(over)
        return it

    def _fact(lane="metric", **over):
        return p2.PreparedFactV2.from_dict(
            {"fact_type": lane, "part_ref": "p01", "occurrence_in_part": None,
             "per_x": None, "item": _item(**over)})

    money = {"value": Decimal(363), "scale_multiplier": Decimal("1e6"),
             "unit_scale_evidence": "million"}
    # A1 numeric prose in value_text WHILE a numeric slot is populated
    v = p2.validate_via_production(
        _fact("guidance", driver_state="introduced", value_text="about $363 million",
              company_confirmed=True, level_unit="m_usd", level_shape_hint="point",
              level_low=money, level_high=money, fiscal_year=2026,
              period_start_date="2026-01-01", period_end_date="2026-12-31",
              time_type="duration"),
        driver={"name": "revenue", "fact_type": "guidance"},
        source={"date": "2026-04-23T08:30:00-04:00", "source_type": "8k",
                "ticker": "AAL", "source_id": "0000006201-26-000031"}, fye_month=12)
    assert any(x.code == "VALUE_TEXT" for x in v), v
    # A5 a scale word that is not in THIS fact's quote (transport structure)
    with pytest.raises(SlotConversionError):
        validate_slot("level_low", {"value": Decimal(1),
                                    "scale_multiplier": Decimal("1e9"),
                                    "unit_scale_evidence": "billion"},
                      stated_unit="m_usd", quote="revenue of $1 million")
    # A9 a fabricated locator
    assert p2.verify_occurrence("alpha beta", "gamma", None) is not None


# ---------------------------------------------------------------- G14/G15 ----

def test_G14_guidance_legacy_path_is_untouched():
    """The retired-on-the-new-path resolver keeps its own proofs: the new
    converter must not have changed the legacy stack under it."""
    r = subprocess.run([sys.executable, "-m", "pytest", "-q",
                        "-p", "no:cacheprovider",
                        os.path.join(_REPO, "driver", "core", "test_driver_units.py")],
                       capture_output=True, text=True, cwd=_REPO)
    assert r.returncode == 0, r.stdout[-2000:]
    guidance = os.path.join(_REPO, ".claude", "skills", "earnings-orchestrator",
                            "scripts", "guidance_ids.py")
    src = io.open(guidance, encoding="utf-8").read()
    assert "_PRESCALE_BOUNDARY" in io.open(
        os.path.join(_REPO, "driver", "core", "driver_units.py"),
        encoding="utf-8").read(), "the legacy 999 guard was removed from the OLD path"
    # the legacy lane KEEPS its own hint machinery — the new path simply never
    # reaches it (a vacuous `assert src` used to stand here; it proved nothing)
    assert "_XBRL_PER_SHARE_MARKERS" in src and "PER_SHARE_LABELS" in src, \
        "the legacy guidance hint machinery was altered by a change that should "
    assert "def slug" in src, "the legacy slug helper must remain intact"


def test_G15_xbrl_declared_metadata_path_is_untouched():
    # S14 (#827): the dead declared-scale helper call is gone; this node now
    # proves the LEGACY v1 XBRL suite only (G_COVERAGE row -> partial).
    r = subprocess.run([sys.executable, "-m", "pytest", "-q",
                        "-p", "no:cacheprovider",
                        os.path.join(_REPO, "driver", "core", "test_prepared_fact.py")],
                       capture_output=True, text=True, cwd=_REPO)
    assert r.returncode == 0, "the v1 XBRL all-or-nothing suite must still pass"


# --------------------------------------------------------------------- G16 ----

def test_G16_old_path_removal_is_gated_on_the_switch():
    """HONEST STATE: v1 and fact16_checks are still present, deliberately — the
    deletion is the atomic switch, which needs owner sign-offs. What IS provable
    now: v2 rejects old payloads, and the import fence holds one-way."""
    assert os.path.exists(os.path.join(_REPO, "driver", "core", "prepared_fact.py")), \
        "v1 must still exist: the switch is not authorised yet"
    assert os.path.exists(os.path.join(_HERE, "scorers", "fact16_checks.py")), \
        "the duplicate rule engine retires AT the switch, not before"
    from driver.core import fact_match, prepared_fact_v2, slot_convert
    for mod in (slot_convert, prepared_fact_v2, fact_match):
        src = io.open(mod.__file__, encoding="utf-8").read()
        assert "unit_resolver" not in src, f"{mod.__name__} imports a retired resolver"


# --------------------------------------------------------------------- G17 ----

def test_G17_transport_is_exact_and_refuses_ambiguity():
    from decimal import Decimal
    import raw_transport
    doc = raw_transport.parse_exact('{"a": 1.000000000000000000001}')
    assert doc["a"] == Decimal("1.000000000000000000001")
    for bad in ('{"a":1,"a":2}', '{"a": NaN}', '{"a": Infinity}'):
        with pytest.raises(raw_transport.RawTransportError):
            raw_transport.parse_exact(bad)


# ---------------------------------------------------------------- G18/G19 ----

def test_G18_the_new_modules_reach_no_graph_write():
    """AST, not text: an earlier version grepped the raw source and tripped on
    the word `transaction` inside the DIVERGENCE LEDGER's prose — the same
    crude-substring class as matching `cent` inside `percent`."""
    from driver.core import fact_match, prepared_fact_v2, slot_convert
    banned_names = {"ENABLE_DRIVER_WRITES", "neo4j", "GraphDatabase"}
    banned_attrs = {"transaction", "execute_write", "write_transaction"}
    for mod in (slot_convert, prepared_fact_v2, fact_match):
        tree = ast.parse(io.open(mod.__file__, encoding="utf-8").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in banned_names:
                raise AssertionError(f"{mod.__name__} references {node.id}")
            if isinstance(node, ast.Attribute) and node.attr in banned_attrs:
                raise AssertionError(f"{mod.__name__} calls .{node.attr}()")
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names] + [getattr(node, "module", "") or ""]
                assert not any("neo4j" in n for n in names), mod.__name__


def test_G19_two_rebuilds_are_byte_identical():
    """Determinism proven WITHOUT writing: the builder returns the text, so the
    live artifact is never touched by a test."""
    import rev4_build_patch
    first, n1 = rev4_build_patch.build_patch_text()
    second, n2 = rev4_build_patch.build_patch_text()
    assert first == second and n1 == n2
    on_disk = io.open(PATCH, encoding="utf-8").read()
    assert hashlib.sha256(first.encode()).hexdigest() == \
        hashlib.sha256(on_disk.encode()).hexdigest(), \
        "the committed patch is not what the builder now produces — rebuild it"


def test_G19_the_patch_still_applies_strictly():
    r = subprocess.run(["git", "apply", "--check", "--whitespace=error", PATCH],
                       capture_output=True, text=True, cwd=_REPO)
    assert r.returncode == 0, r.stderr


# ---------------------------------------------------------------- G28/G32 ----

def test_G28_source_id_echo_mismatch_is_refused():
    """The wave-1 worker mix-up guard, preserved: a reply for the wrong event
    must never be ingested as the assigned one."""
    src = io.open(os.path.join(_HERE, "raw_transport.py"), encoding="utf-8").read()
    assert "WRONG-EVENT reply, refused" in src
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "ingest_workflow_result")
    body = ast.dump(fn)
    assert "source_id" in body and "inner" in body


def test_G32_source_id_is_delivered_in_the_prompts_event_view():
    prompt = _prompt_text()
    assert "source_id" in prompt
    assert "echo" in prompt.lower(), "the echo instruction must be visible to the model"


# ------------------------------------------- G9 / G12: the honest position ----

def test_G9_one_shared_validation_entry_point_exists():
    """G9 asked for 'scorer == run_event, same function'. What is TRUE today:
    exactly ONE validation entry point exists for v2 — `validate_via_production`
    — and it delegates to production's own `validate_fact`, restating no rule.
    What is NOT yet true: the scorer and run_event both routing through it. That
    swap retires `fact16_checks` and IS the atomic switch, so it is registered
    gated-switch rather than claimed."""
    import inspect
    from driver.core import driver_validators
    from driver.core import prepared_fact_v2 as p2
    src = inspect.getsource(p2.validate_via_production)
    assert "validate_fact" in src, "v2 must delegate to production's validator"
    assert not hasattr(p2, "LANE_STATES") and not hasattr(p2, "PERIOD_SCOPES")
    assert callable(driver_validators.validate_fact)
    # HONEST: the scorer still calls the duplicate engine until the switch
    scorer = io.open(os.path.join(_HERE, "scorers", "score_exp5.py"),
                     encoding="utf-8").read()
    assert "from fact16_checks import check_item" in scorer, (
        "the scorer moved off the duplicate engine — update G9's status from "
        "gated-switch to code, deliberately")


def test_G12_the_live_launcher_still_serves_the_v1_contract():
    """The rev-4 prompt is AUTHORED (Part A) but is NOT what the launcher
    serves: the live template still points at the 37-field v1 contract. Claiming
    G12 against the package Markdown tested a description, not the artifact a
    model would actually receive."""
    tmpl = io.open(os.path.join(_HERE, "launch_kfields_drafts.workflow.template.js"),
                   encoding="utf-8").read()
    assert "exp5_item_contract.md" in tmpl
    assert "37 model-owned fields" in tmpl, (
        "the launcher was regenerated — move G12 to `code` and point this test "
        "at the real assembled prompt")
    contract = io.open(os.path.join(_HERE, "exp5_item_contract.md"),
                       encoding="utf-8").read()
    assert "level_unit_kind_hint" in contract, "the served contract is not v1"


def test_G13_the_annual_sequential_attack_is_actually_run():
    """Fixture A4 claims 'caught_by: code'. That is only honest if the attack is
    EXECUTED — it was not, and V2 accepted it. It now runs through production."""
    from decimal import Decimal
    from driver.core import prepared_fact_v2 as p2
    item = {k: None for k in p2.ITEM_FIELDS}
    s5 = {"value": Decimal(5), "scale_multiplier": Decimal(1),
          "unit_scale_evidence": None}
    item.update(driver_name="revenue", driver_state="reported",
                quote="revenue grew 5% sequentially", measurement_raw_spans=[],
                slice_parts=[], level_low=s5, level_high=s5,
                level_unit="percent_sequential", level_shape_hint="point",
                fiscal_year=2026, period_start_date="2026-01-01",
                period_end_date="2026-12-31", time_type="duration")
    f = p2.PreparedFactV2.from_dict({"fact_type": "metric", "part_ref": "p01",
                                     "occurrence_in_part": None, "per_x": None,
                                     "item": item})
    v = p2.validate_via_production(
        f, driver={"name": "revenue", "fact_type": "metric"},
        source={"date": "2026-04-23T08:30:00-04:00", "source_type": "8k",
                "ticker": "AAL", "source_id": "0000006201-26-000031"},
        fye_month=12)
    assert any("percent_sequential" in x.message for x in v), v


def test_the_v2_modules_are_a_STAGED_read_only_adapter():
    """The reviewer's second correction: V2 must NOT be connected to the live
    path before approval — a staged READ-ONLY adapter is the sanctioned form.
    Four mechanical proofs that this is one.

    At the approved switch this test is updated DELIBERATELY, together with the
    other gated tests; until then, a failure here means the switch happened by
    accident."""
    import ast
    core = os.path.join(_REPO, "driver", "core")
    # #821: the event door + filing binding moved OUT of prepared_fact_v2
    # into its own module. Same staged status, one more file.
    new = STAGED_FILES

    # 1. no PRE-EXISTING production file is modified beyond the DELIBERATE,
    #    individually-justified set (the switch has not happened).
    #    SCOPE (fixed round 8): the whole of `driver/`, not just `driver/core`.
    #    Measuring one subtree and stating the conclusion for the tree is the
    #    exact scope-overclaim this programme keeps logging — the gate itself
    #    was committing it, so relocation changes were invisible here.
    st = subprocess.run(["git", "status", "--porcelain", "--", "driver"],
                        capture_output=True, text=True, cwd=_REPO).stdout
    allowed = {
        # ADDITIVE read-only surface: the XBRL reader now also returns the
        # fact's own fact_id / unit_ref / unit_name / is_divide / value, and the
        # filing company's CIK, so a verifier binds against the FILING and the
        # GRAPH rather than a caller's say-so.
        "driver/core/driver_neo4j_adapter.py",
        # Owner-approved Option 1 (2026-07-27): the XBRL binding defects are
        # fixed INSIDE the shared Route-A binder, never duplicated in Core.
        "driver/relocation/inline_html.py",
        # ONE definition of the Route-A semantic-unit map, the graph-string
        # boolean law, and the stored-period-end rule. Each previously existed
        # twice (or was unreachable from the package path).
        "driver/relocation/exact_numbers.py",
        # Re-exports those two constants unchanged, so the pinned census test
        # and the probe scripts keep importing them from here.
        "driver/relocation/locator.py",
        # Drops its private copy of the exclusive-date rule for the shared one.
        "driver/core/slice_menu.py",
        # #822 (reviewer-directed 2026-07-28): the LIVE CLI built the
        # (axis, member) pair set by hand, one of FOUR copies of a rule that now
        # has ONE owner in `slice_menu`. BEHAVIOUR-PRESERVING — the helper
        # returns the identical set — and de-duplication was the instruction.
        "driver/core/driver_write_cli.py",
        # #819/#820 remainder (reviewer-directed 2026-07-28): the LIVE v1 run
        # input asked only "non-blank string" while the shared predicate
        # rejected the same id, so `x/y` bought several graph reads before
        # `build_id` refused it ~100 lines later. This is a deliberate
        # TIGHTENING, not a behaviour-preserving extraction. FIVE explicit
        # lawful controls are pinned in the v1 suite; the FULL REGRESSION is the
        # broader evidence that nothing else was invalidated (a grep for one
        # literal spelling cannot prove "every fixture id", and an earlier note
        # of mine overclaimed exactly that).
        "driver/core/prepared_fact.py",
        # #820 (reviewer-directed 2026-07-27): `build_id`'s INLINE source-id
        # check is extracted as the named predicate `valid_source_id`, so the
        # run input and the event door ask the SAME law instead of copying its
        # regex. BEHAVIOUR-PRESERVING and proved so: the predicate returns the
        # identical verdict to the inline check on every case tried, and the ID
        # law's own suite (56 tests, incl. the 14 pinned vectors whose hashes
        # would change if any rule moved) is unchanged and green.
        "driver/core/driver_ids.py",
    }
    # PRODUCTION only (the assertion says so), and UNTRACKED files included:
    # both judged by the one derived helper, which a mutation test attacks.
    unexpected = unexpected_production_files(st.splitlines(), allowed)
    assert not unexpected, f"unexpected production file(s): {unexpected}"

    # 2. nothing in the live path imports ANY staged module — the names are
    #    DERIVED from the staged set, so a fourth staged module cannot slip past
    #    a list that still names three.
    live = {fn: io.open(os.path.join(core, fn), encoding="utf-8").read()
            for fn in os.listdir(core)
            if fn.endswith(".py") and fn not in new and not fn.startswith("test_")}
    leaks = live_modules_importing_staged(live)
    assert not leaks, f"the live path now reaches staged code: {leaks}"

    # 3. the adapter reaches production only through PURE functions
    from driver.core import prepared_fact_v2 as p2
    tree = ast.parse(io.open(p2.__file__, encoding="utf-8").read())
    pure = {"build_id", "norm", "IdLawError", "ensure_driver_period",
            "PeriodResolutionError", "compose_surprise_scope", "validate_fact",
            "convert_slot", "validate_slot", "SlotConversionError",
            "CANONICAL_UNITS", "exact_scaleb",
            # F11 narrowed (SEQ 806/808): the old note here credited a
            # "2026-07-27 owner ruling on pure" — test prose, never frozen
            # authority. MULTIPLIER_ONE_UNITS remains slot_convert's own
            # public statement of the multiplier-1 family (consumed by its
            # family_required_multiplier); xbrl_attach's CANDIDATE map no
            # longer imports it, and no production module outside
            # slot_convert does today.
            "MULTIPLIER_ONE_UNITS",
            # ADDED DELIBERATELY 2026-07-27 (#818): the 1,024-character stored
            # bound has ONE owner in slot_convert, and the XBRL multiplier must
            # honour it — 10^1000000 is representable after Emax is widened but
            # needs 1,000,001 characters, so it parks here rather than through a
            # second threshold invented at the call site. Pure, no I/O.
            "assert_storable",
            # ADDED DELIBERATELY 2026-07-27 (#820): the ONE source-id predicate,
            # extracted from `build_id`'s inline check so the event door and the
            # run input ask the SAME law rather than copying its regex. A pure
            # `re.fullmatch` over a string — no I/O, no graph, no state.
            "valid_source_id",
            # ADDED DELIBERATELY 2026-07-28 (#822): ONE owner for "a context
            # carries at most one member per axis". The rule had been hand-
            # rolled in FOUR places across three review rounds; `slice_menu`
            # owns the axis law, so every caller now asks it. A list
            # comprehension and a set comparison — no I/O, no graph, no state.
            # ADDED 2026-07-28 (#822): ONE safe operation over a fact's
            # dimensions — the (axis, member) pair set, or None when an axis
            # repeats. It is one function because building the set is exactly
            # what hides a repeat. Pure: a comprehension and a set comparison.
            "axis_member_pairs",
            # ---- PC-1 (#827) ------------------------------------------------
            # SIX entries, not the one the card first measured. Every one is a
            # symbol the candidate reaches because an ALREADY-CLOSED #827
            # one-owner row put it there — the same authority, and the same
            # proof question, as the deliberate entries above. Re-checked at
            # close: two are pure functions (no I/O, no state), four are static
            # literals. Thirteen of this module's nineteen driver.core imports
            # are function-local, which is why a top-of-file reading saw one of
            # these and the gate's ast-walk sees six.
            #
            # W3: the frozen NAME-17 terminal-suffix split, replacing this
            # module's private _TERMINAL_SUFFIXES copy. A `for`, an `endswith`
            # and a slice.
            "split_terminal_suffix",
            # W4: the ONE 64-hex predicate. A `re.fullmatch` over a string.
            "sha256_hex_ok",
            # T7: the one public numeric-field vocabulary. A tuple literal.
            "NUMERIC_FIELDS",
            # T8: the one lane vocabulary — its KEYS are the lanes. A dict
            # literal.
            "LANE_STATES",
            # P-O10: the 11-key period vocabulary. A tuple literal.
            "PERIOD_ITEM_KEYS",
            # F-PERIOD owner: the two period kinds. A tuple literal.
            "PERIOD_TIME_TYPES",
            # -----------------------------------------------------------------
            # the EXISTING current-filing verifier — reused, never re-built
            "match_xbrl_fact", "check_member_refs", "convert_slot"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("driver.core"):
            for a in node.names:
                assert a.name in pure, f"non-pure production import: {a.name}"

    # 4. no WRITE surface anywhere in the staged set. Reading the store is
    #    legitimate and required (the verifier must fetch its own evidence);
    #    what must not exist is a way to MUTATE the graph. Checked on the AST
    #    so a docstring mentioning a transaction cannot trip it.
    write_attrs = {"transaction", "execute_write", "write_transaction", "run"}
    for fn in sorted(new):
        tree = ast.parse(io.open(os.path.join(core, fn), encoding="utf-8").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in write_attrs:
                raise AssertionError(f"{fn} calls .{node.attr}() — a write surface")
            if isinstance(node, ast.Name) and node.id == "ENABLE_DRIVER_WRITES":
                raise AssertionError(f"{fn} references the write gate")


def test_the_ledger_renderer_is_REPEATABLE_and_matches_disk():
    """Two renders byte-identical, and the on-disk artifact is one of them.

    Determinism is asserted WITHOUT writing: `render()` returns the text, so a
    test never touches the live file — the same discipline as the patch builder.
    """
    sys.path.insert(0, _HERE)
    import make_g_ledger
    first, second = make_g_ledger.render(), make_g_ledger.render()
    assert first == second, "two renders differ — the ledger is not deterministic"
    on_disk = io.open(LEDGER, encoding="utf-8").read()
    assert hashlib.sha256(first.encode()).hexdigest() == \
        hashlib.sha256(on_disk.encode()).hexdigest(), \
        "the committed ledger is not what the renderer now produces — rebuild it"


def test_the_pin_inventory_is_REPEATABLE_and_matches_disk():
    sys.path.insert(0, _HERE)
    import make_pin_inventory
    first, second = make_pin_inventory.render(), make_pin_inventory.render()
    assert first == second, "two renders differ — the pin inventory is not deterministic"
    on_disk = io.open(PINS, encoding="utf-8").read()
    assert hashlib.sha256(first.encode()).hexdigest() == \
        hashlib.sha256(on_disk.encode()).hexdigest(), \
        "the committed pin inventory is not what the generator produces — rebuild it"


def test_the_pin_inventory_uses_SEMANTIC_anchors_and_never_itself():
    """v4 addressed every pin by `file:LINE`, so one inserted sentence
    invalidated 73 of 76 rows while every hash stayed correct. v3 pinned the
    inventory to ITSELF, 74 times.

    IT NOW READS EVERY BACKTICKED PATH, not the first backticked token. v6 added
    a verification table whose first column is a PIN, and the old check read
    that pin AS A FILE PATH — so it asserted against the wrong column and could
    not see the artifact paths at all. A row may carry a pin, a label and a
    path; whichever tokens are paths are the ones checked.
    """
    import re as _re
    text = io.open(PINS, encoding="utf-8").read()
    rows = [l for l in text.splitlines() if l.startswith("| `")]
    assert rows, "the inventory has no rows"
    paths = 0
    for row in rows:
        for token in row.split("`")[1::2]:      # every backticked token in the row
            if "/" not in token:
                continue                       # a pin or a short label, not a path
            paths += 1
            assert not _re.search(r":\d+$", token), f"line-number anchor: {token}"
            assert "pin_inventory" not in token, f"self-reference: {token}"
            assert os.path.exists(os.path.join(_REPO, token)), f"absent: {token}"
    # THE SCAN MUST HAVE FOUND SOMETHING, and every row must name a real file:
    # a silently empty scan is the false green this whole gate exists to stop.
    assert paths >= len(rows), \
        f"{len(rows)} rows but only {paths} paths — a row names no file at all"


def test_the_pin_inventory_RECOMPUTES_each_pin_and_states_the_METHOD():
    """Locating a hash proves it is PRESENT, never that it still describes its
    artifact — so every pin is recomputed, and the DIGEST METHOD is stated,
    because an unlabelled hash is a pin nobody else can reproduce."""
    import re as _re
    sys.path.insert(0, _HERE)
    # ALIASED DELIBERATELY: this module's `PINS` is the inventory FILE, while the
    # generator's `PINS` is the pin->artifact map. Importing it bare shadowed the
    # path and the test died reading a dict as a filename.
    from make_pin_inventory import HASH_METHOD, PINS as PIN_MAP
    text = io.open(PINS, encoding="utf-8").read()
    assert HASH_METHOD in text, "the inventory does not state its hash method"
    for pin in PIN_MAP:
        assert _re.search(rf"^\| `{pin}` \|.*\*\*(AGREES|DIFFERS|ABSENT)\*\* \|$",
                          text, _re.M), f"{pin} carries no recomputation result"


def test_a_DATED_RECORD_is_never_called_a_defect_only_a_CURRENT_claim_is():
    """THE distinction the owner drew (2026-07-30), and v6 got wrong.

    v6 recomputed every pin and printed a flat STALE on any difference. That
    labels a DATED RECORD — a row stating what was true on its own date — as a
    defect, and the repair for a "defect" is to change it, which destroys the
    history. A record stands; a correction is appended beside it.

    Only a place that CLAIMS TO BE CURRENT can be wrong. So: every occurrence is
    classified, the failing set counts current claims ONLY, and each one is named.
    """
    import re as _re
    sys.path.insert(0, _HERE)
    from make_pin_inventory import collect, verify_pins
    text = io.open(PINS, encoding="utf-8").read()
    found, verified = collect(), verify_pins()

    roles = {key[3] for key in found}
    assert roles <= {"current claim", "dated record"}, f"unknown role: {roles}"
    assert "dated record" in roles, \
        "no occurrence is classified as a dated record — the split is not working"

    wrong = sorted({(k[0], k[2]) for k in found if k[3] == "current claim"
                    and verified[k[2]][3] != "AGREES"})
    m = _re.search(r"CURRENT claims whose pin no longer describes its "
                   r"artifact\*\* \| \*\*(\d+)\*\*", text)
    assert m, "the inventory states no count of wrong CURRENT claims"
    assert int(m.group(1)) == len(wrong), \
        f"{len(wrong)} wrong current claim(s) {wrong}, summary says {m.group(1)}"
    for path, pin in wrong:
        assert path in text and pin in text, \
            f"the wrong current claim {path} -> {pin} is not NAMED"

    # AND THE OTHER HALF, so this can never become "flag everything": a pin whose
    # hash differs must NOT be counted when the only places it appears are records.
    record_only = {k[2] for k in found if k[3] == "dated record"} - \
                  {k[2] for k in found if k[3] == "current claim"}
    for pin in record_only:
        assert (pin, ) not in [(w[1], ) for w in wrong], \
            f"{pin} appears only in dated records but was counted as a defect"


def test_the_g_ledger_is_regenerated_not_transcribed():
    """Two hand-copied status mixes had already gone stale against the registry.
    The ledger is now a BUILD PRODUCT: this fails if the file on disk differs
    from what the generator produces, and the package states no counts at all."""
    r = subprocess.run([sys.executable, os.path.join(_HERE, "make_g_ledger.py"),
                        "--check"], capture_output=True, text=True, cwd=_HERE)
    assert r.returncode == 0, r.stdout + r.stderr
    pkg = io.open(PKG, encoding="utf-8").read()
    stale = re.findall(r"code\*{0,2} ?\(?(\d\d)\)?", pkg)
    assert not stale, f"the package transcribes a status count again: {stale}"
    assert "THE LEDGER IS DERIVED, NEVER TRANSCRIBED" in pkg


def test_the_attack_count_is_derived_not_transcribed():
    """The package said "24 attack tests" while 28 existed — the same
    transcription rot as the status mixes. Counts come from the file."""
    n = len([t for t in _test_names(ATTACK_TESTS) if t.startswith("test_")])
    pkg = io.open(PKG, encoding="utf-8").read()
    claimed = re.findall(r"(\d+) attack tests", pkg)
    assert not claimed, (
        f"the package transcribes an attack-test count {claimed}; there are "
        f"{n}. State it as derived, or not at all.")


# ---------------------------------------------------------------------------
# MUTATION TESTS — a gate that has never been attacked is a hope, not a gate.
# Both of these attacks passed the previous version silently.
# ---------------------------------------------------------------------------

def test_the_gate_CATCHES_a_live_import_of_a_staged_module():
    """ATTACK: a live production module starts importing staged code. The old
    check compared against a hand-written three-name list, so an import of the
    fourth staged module (`xbrl_attach`) was invisible."""
    for staged_name in sorted(STAGED_FILES):
        mod = staged_name[:-3]
        attack = {"driver_writer.py": f"from driver.core.{mod} import something"}
        assert live_modules_importing_staged(attack), \
            f"a live import of staged {mod} went undetected"
        # PC-4 corrective (SEQ 859): the staged module can sit in EITHER half of
        # an ImportFrom. The whole-module forms below were invisible to the
        # first version, which read only `.module` — and they are precisely the
        # ones a SYMBOL-granular allowance can never cover, since importing the
        # module reaches every symbol in it.
        for form in (f"from driver.core import {mod}",
                     f"from driver.core import {mod} as shorthand",
                     f"from . import {mod}",
                     f"import driver.core.{mod}"):
            assert live_modules_importing_staged({"driver_writer.py": form}), \
                f"whole-module import went undetected: {form}"
    # NEGATIVE CONTROL: ordinary live code is not flagged
    assert live_modules_importing_staged(
        {"driver_writer.py": "from driver.core.driver_ids import build_id"}) == []

    # PC-4 (#827): the check reads IMPORTS, not text. Everything below was
    # wrong under the old substring scan — the first three were reported as
    # edges when they are sentences, and the last four were the widenings a
    # symbol-granular allowance has to refuse.

    # PROSE IS NOT AN EDGE. These are the three real mentions that live in the
    # current tree's comments and docstrings; the scan called every one a leak.
    for prose in ('# see xbrl_attach for the event door',
                  '"""mirrors prepared_fact_v2\'s lane vocabulary."""',
                  'x = 1  # slot_convert owns the unit law'):
        assert live_modules_importing_staged({"outcome_codes.py": prose}) == [], \
            f"prose was counted as an import: {prose}"

    # THE ONE LAWFUL EDGE (C1+C10), an ALIAS of it, and both written RELATIVELY
    # — the same symbol however it is spelled. The relative spellings are
    # canonicalized (PC-4 corrective, SEQ 859) so one edge cannot get two
    # different verdicts depending on how the author wrote the import.
    for lawful in ("from driver.core.slot_convert import CANONICAL_UNITS",
                   "from driver.core.slot_convert import CANONICAL_UNITS as CU",
                   "from .slot_convert import CANONICAL_UNITS",
                   "from .slot_convert import CANONICAL_UNITS as CU"):
        assert live_modules_importing_staged(
            {"driver_validators.py": lawful}) == [], lawful
    # ...but the relative WHOLE-module form of that same module still fails.
    assert live_modules_importing_staged(
        {"driver_validators.py": "from . import slot_convert"}), \
        "the relative whole-module form rode in on the symbol allowance"

    # PC-4 corrective (SEQ 860/861): THE MODULE IS RESOLVED, NOT MATCHED BY
    # BASENAME. A module merely NAMED like a staged one, in a different
    # package, is not a staged edge — in either direction. Before this, the
    # basename mapping both invented staged edges that do not exist AND let an
    # unrelated package collect the C1 symbol allowance.
    for fn in ("driver_validators.py", "driver_writer.py"):
        for unrelated in ("import unrelated.slot_convert",
                          "from unrelated import slot_convert",
                          "from unrelated.slot_convert import convert_slot",
                          "from unrelated.slot_convert import CANONICAL_UNITS",
                          "from ..relocation import slot_convert",
                          "from ..relocation.slot_convert import CANONICAL_UNITS"):
            assert live_modules_importing_staged({fn: unrelated}) == [], \
                f"an unrelated package was read as a staged edge: {fn} / {unrelated}"

    # the PARENT spelling of the real package resolves to the same place, so it
    # gets the same verdicts — caught whole-module, caught non-C1 symbol, and
    # the C1 symbol allowed in its OWN module only.
    assert live_modules_importing_staged(
        {"driver_validators.py": "from ..core import slot_convert"}), "parent whole-module"
    assert live_modules_importing_staged(
        {"driver_validators.py": "from ..core.slot_convert import convert_slot"}), \
        "parent symbol form"
    assert live_modules_importing_staged(
        {"driver_validators.py": "from ..core.slot_convert import CANONICAL_UNITS"}) == []
    assert live_modules_importing_staged(
        {"driver_writer.py": "from ..core.slot_convert import CANONICAL_UNITS"}), \
        "the C1 allowance is bound to ITS module, whatever the spelling"

    # ...and it is granted to THAT module alone, for THAT symbol alone.
    assert live_modules_importing_staged(
        {"driver_writer.py": "from driver.core.slot_convert import "
                             "CANONICAL_UNITS"}), "the allowance is not module-bound"
    assert live_modules_importing_staged(
        {"driver_validators.py": "from driver.core.slot_convert import "
                                 "CANONICAL_UNITS, convert_slot"}), \
        "a SECOND slot_convert symbol rode in on the allowance"
    assert live_modules_importing_staged(
        {"driver_validators.py": "import driver.core.slot_convert"}), \
        "the WHOLE module rode in on a symbol-granular allowance"
    assert live_modules_importing_staged(
        {"driver_validators.py": "from driver.core.slot_convert import *"}), \
        "a star-import rode in on a symbol-granular allowance"


def test_the_gate_CATCHES_an_unexpected_untracked_production_file():
    """ATTACK: a brand-new production module is simply never `git add`ed. The
    old check dropped every `??` line, so it saw nothing at all."""
    attack = ["?? driver/core/backdoor.py",
              "?? driver/relocation/quiet_helper.py"]
    caught = unexpected_production_files(attack, allowed=set())
    assert caught == ["driver/core/backdoor.py",
                      "driver/relocation/quiet_helper.py"], caught
    # NEGATIVE CONTROLS: the staged files themselves, an untracked TEST, and an
    # allowlisted modification are all lawful and must NOT be flagged.
    lawful = [f"?? {path}" for path in sorted(STAGED_PATHS)]
    lawful += ["?? driver/core/test_something_new.py",
               " M driver/core/driver_ids.py"]
    assert unexpected_production_files(
        lawful, allowed={"driver/core/driver_ids.py"}) == []


def test_an_unallowlisted_MODIFICATION_is_still_caught():
    """The property the gate always had — kept under the rewrite."""
    assert unexpected_production_files(
        [" M driver/core/driver_writer.py"], allowed=set()) == \
        ["driver/core/driver_writer.py"]


def test_the_gate_CATCHES_a_staged_NAME_in_the_WRONG_DIRECTORY():
    """ATTACK: a file with a staged BASENAME appears somewhere it was never
    approved to live. Matching on the filename alone accepted it as "the staged
    file" — a staged module is staged only at its approved PATH."""
    for path in sorted(STAGED_PATHS):
        name = path.rsplit("/", 1)[-1]
        for wrong in (f"driver/relocation/{name}", f"driver/{name}",
                      f"driver/core/sub/{name}"):
            caught = unexpected_production_files([f"?? {wrong}"], allowed=set())
            assert caught == [wrong], f"{wrong} was accepted as staged"
    # NEGATIVE CONTROL: each staged file at its APPROVED path is still lawful
    assert unexpected_production_files(
        [f"?? {path}" for path in sorted(STAGED_PATHS)], allowed=set()) == []


def test_the_manifest_gate_blocks_the_WHOLE_env_file_family_not_just_dot_env():
    """A CLASS guard, not an instance guard.

    The first version listed `.env` as a forbidden path SEGMENT. That blocked
    `.env` and `config/.env` and let `.env.local`, `.env.production` and
    `.env.bak` straight through — and every one of those carries the same
    secrets the rule exists to keep out of a commit. Found by the standing
    simplification/class sweep, not by a failure.
    """
    sys.path.insert(0, _HERE)
    from isolated_manifest_check import forbidden as check_forbidden
    for secret in (".env", "config/.env", ".env.local", ".env.production",
                   "scripts/.env.bak", "a/b/.envrc"):
        assert check_forbidden([secret]) == [secret], \
            f"a secrets file slipped past the manifest gate: {secret}"
    # POSITIVE CONTROLS: ordinary manifest files must NOT be blocked, or the
    # guard would simply refuse everything and prove nothing.
    for ok in ("driver/core/xbrl_attach.py",
               ".claude/plans/Drivers/experiments/harness/test_g_suite.py",
               "scripts/driver_seed/relocate_probe/inline_html_cache/x.htm"):
        assert check_forbidden([ok]) == [], f"a lawful file was blocked: {ok}"


# ---------------------------------------------------------------------------
# IMPORT SAFETY — ONE owner (`import_inertness`), a DERIVED inventory, and all
# four side-effect kinds. The previous version named two generators by hand and
# compared one artifact's bytes: `rev4_build_patch` kept running `git` AND
# `os.chdir` at import, `rev4_coverage_check` ran a subprocess and then called
# `main(sys.argv[1])` (crashing on import), and a write to any OTHER file was
# invisible. Naming targets by hand is what let the siblings keep the defect.
# ---------------------------------------------------------------------------

def _inertness():
    sys.path.insert(0, _HERE)
    import import_inertness
    return import_inertness


@pytest.mark.parametrize("module", _inertness().active_inventory())
def test_EVERY_active_harness_module_imports_INERTLY(module):
    """No process, no chdir, no filesystem write, no output, no import error."""
    issues = _inertness().probe(module)
    assert issues == [], f"{module} is not inert on import: {issues}"


def test_the_active_inventory_INCLUDES_the_declared_generators_themselves():
    """The first derivation returned only the import CLOSURE of the tests, so the
    declared seeds were never checked — which is exactly how `rev4_coverage_check`
    stayed unexamined while being the named target."""
    inv = set(_inertness().active_inventory())
    missing = [m for m in _inertness().DECLARED if m not in inv]
    assert not missing, f"declared generator(s) absent from the inventory: {missing}"
    assert len(inv) > len(_inertness().DECLARED), \
        "the inventory is only the declared list — the closure is not being walked"


def test_the_inventory_CATCHES_a_module_loaded_by_FILENAME_not_by_import():
    """`rev4_build_patch` reads `rev3_build.py` and `exec`s it. There is no import
    statement, so an import-only walk cannot see it — and a module whose code
    really does run inside a generator sat outside the inventory, never probed.

    Checked as a PROPERTY of the derivation, not by asserting one name: any
    harness `.py` named in a string by an active module must be active too.
    """
    inert = _inertness()
    files, inv = inert._module_files(), set(inert.active_inventory())
    # Test modules are deliberately outside the inventory (they are the walk's
    # SEEDS, not its targets), so a doc-string mentioning one is not a load.
    named = {stem for m in inv
             for stem in inert._local_imports(files[m], files)
             if stem in files and not stem.startswith("test_")}
    assert named - inv == set(), \
        f"module(s) loaded by name are missing from the inventory: {named - inv}"
    # POSITIVE CONTROL: the exec'd builder input really is reached this way, so
    # the property above is not vacuously true.
    assert "rev3_build" in inv, \
        "rev3_build is exec'd by rev4_build_patch and must be in the inventory"
    # AND EVERY DECLARED PARTIAL LOAD IS A REAL ONE. `DYNAMIC` says "probe this
    # through its loader instead of importing it", which is also the shape of an
    # excuse — so each key must actually be a module some active module names by
    # filename, and its statement must mention that loader.
    for mod, stmt in inert.DYNAMIC.items():
        assert mod in named, \
            f"DYNAMIC names {mod}, which nothing loads by filename — not an " \
            f"exemption this suite grants"
        owners = [m for m in inv
                  if mod in inert._local_imports(files[m], files) and m != mod]
        assert any(o in stmt for o in owners), \
            f"{mod}'s load statement does not go through its loader {owners}"


@pytest.mark.parametrize("kind,payload", [
    ("process",  "import subprocess\nsubprocess.run(['true'], capture_output=True)\n"),
    ("chdir",    "import os\nos.chdir(os.path.dirname(os.path.abspath(__file__)))\n"),
    ("write",    "open(__file__ + '.sideeffect', 'w').write('x')\n"),
    ("stdout",   "print('noise')\n"),
    # THE FOUR THE PROBE USED TO MISS ENTIRELY. Watching `open` in write mode is
    # not watching the filesystem: a module can make a directory, move a file,
    # delete one, or shorten one without ever opening it for writing.
    ("mkdir",    "import os\nos.mkdir(__file__ + '.d')\n"),
    ("rename",   "import os\nos.rename(__file__, __file__ + '.moved')\n"),
    ("remove",   "import os\nos.remove(__file__ + '.gone') if False else "
                 "os.mkdir(__file__ + '.x') or os.rmdir(__file__ + '.x')\n"),
    ("rmtree",   "import shutil, os\nos.mkdir(__file__ + '.t')\n"
                 "shutil.rmtree(__file__ + '.t')\n"),
])
def test_MUTATION_each_side_effect_kind_is_caught(kind, payload, tmp_path):
    """A gate never attacked is a hope. Each kind is injected into a REAL active
    module inside a TEMP copy of the harness — the live files are never written."""
    import shutil
    inert = _inertness()
    shutil.copytree(_HERE, tmp_path / "h", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.htm"))
    target = tmp_path / "h" / "make_g_ledger.py"
    target.write_text(target.read_text() + "\n" + payload)
    mp = pytest.MonkeyPatch()
    mp.setattr(inert, "_HERE", str(tmp_path / "h"))
    mp.setattr(inert, "_SCORERS", str(tmp_path / "h" / "scorers"))
    try:
        issues = inert.probe("make_g_ledger")
    finally:
        mp.undo()
    assert issues, f"a {kind} side effect at import went undetected"
    # AND on the RIGHT detector, so an unrelated failure cannot green this.
    want = {"process": "created a process", "chdir": "changed directory",
            "write": "wrote file", "stdout": "printed to stdout",
            "mkdir": "changed the filesystem", "rename": "changed the filesystem",
            "remove": "changed the filesystem",
            "rmtree": "changed the filesystem"}[kind]
    assert any(want in i for i in issues), f"wrong detector for {kind}: {issues}"


def test_MUTATION_the_baseline_temp_copy_is_itself_inert():
    """Without a mutation the temp copy must be clean, so every assertion above
    is attributable to its own injection."""
    assert _inertness().probe("make_g_ledger") == []


@pytest.mark.parametrize("label,line,want", [
    ("active current",   '> **CURRENT (2026-07-25):** WorkOrder v2.0 (sha `d91443f8`)',
     "current claim"),
    ("active, no quote", '**CURRENT (2026-08-01):** something (sha d91443f8)',
     "current claim"),
    ("dated history",    '**2026-07-25 ROUND-30** — a CURRENT pin line added (d91443f8)',
     "dated record"),
    ("ledger table row", '| **CURRENT claims whose pin is wrong** | **1** — d91443f8 |',
     "dated record"),
])
def test_a_CURRENT_claim_is_a_STRUCTURAL_marker_not_a_substring(label, line, want):
    """`"CURRENT" in line` classified by the word appearing ANYWHERE, so a dated
    round row that merely MENTIONS a current pin — and a table row in this
    programme's own audit ledger — were both read as live claims. Marking a dated
    record "wrong" invites editing history, which is the damage the split exists
    to prevent. The marker is now the line OPENING with a bold CURRENT token."""
    sys.path.insert(0, _HERE)
    from make_pin_inventory import _roles_for
    assert _roles_for([line])[0] == want, label


def test_a_QUOTED_current_claim_inside_a_code_fence_claims_nothing():
    """Text inside a fence is an EXCERPT. A document quoting someone else's
    current-pin line is not itself making that claim."""
    sys.path.insert(0, _HERE)
    from make_pin_inventory import _roles_for
    fenced = ["```", '> **CURRENT (2026-07-25):** quoted excerpt d91443f8', "```"]
    assert _roles_for(fenced)[1] == "dated record"
    # ...and the fence must CLOSE: the same line outside one is a real claim.
    assert _roles_for([fenced[1]])[0] == "current claim"


def test_the_pin_scan_reads_the_INDEX_not_the_dirty_worktree():
    """The artifact must be reproducible from the commit, and the commit is the
    INDEX. The scan once read the working tree, so dirty files outside the commit
    fed it and a fresh clone regenerating it got a different answer.

    THE SKIP THIS REMOVES: the old version needed a dirty NON-manifest document
    to exist, which is false in any clean tree — so the rule went unproven exactly
    where the artifact has to hold. The primary property needs no such premise:
    for every tracked path the bytes come from the index. The worktree CONTRAST is
    checked additionally whenever a dirty file happens to exist, and its absence
    no longer costs the test.
    """
    sys.path.insert(0, _HERE)
    import make_pin_inventory as m
    tracked = subprocess.run(["git", "ls-files"], cwd=_REPO,
                             capture_output=True, text=True).stdout.split()
    probes = [p for p in tracked
              if p.startswith(".claude/plans/Drivers/") and p.endswith(".md")][:5]
    assert probes, "no tracked plan document — the scan has no premise"
    for p in probes:
        index = subprocess.run(["git", "show", f":{p}"], cwd=_REPO,
                               capture_output=True).stdout
        assert m.committed_bytes(p) == index, \
            f"{p} did not come from the index — the artifact is not the commit's"
    # A path that is not in the index at all has no committed bytes, and must say
    # so rather than fall back to whatever is lying on disk.
    assert m.committed_bytes("no/such/file.md") is None

    dirty = subprocess.run(["git", "diff", "--name-only"], cwd=_REPO,
                           capture_output=True, text=True).stdout.split()
    contrast = [p for p in dirty if p.endswith(".md") and os.path.exists(
        os.path.join(_REPO, p))]
    if contrast:                       # extra proof when the tree provides it
        p = contrast[0]
        assert m.committed_bytes(p) != io.open(
            os.path.join(_REPO, p), "rb").read(), \
            f"{p} has unstaged edits, yet the committed bytes matched the " \
            f"worktree — the index is not being read"


# ---------------------------------------------------------------------------
# THE GATE'S OWN REGRESSION MATRIX.
#
# Every defect the reviewer found in the commit gate, saved as a case here. The
# gate had almost no tests of its own: it checked the tree and the suite, and
# nothing checked IT. Each case below is one way the gate used to pass while
# proving less. They drive the gate's pure functions directly, so the whole
# matrix costs milliseconds instead of a two-minute suite run.
# ---------------------------------------------------------------------------

def _gate():
    sys.path.insert(0, _HERE)
    import isolated_manifest_check
    return isolated_manifest_check


def _junit(cases):
    """cases: [(classname, name, kind|None, message)] -> a JUnit document."""
    body = "".join(
        f'<testcase classname="{c}" name="{n}">'
        + (f'<{k} type="X" message="{m}"></{k}>' if k else "")
        + "</testcase>" for c, n, k, m in cases)
    return f'<testsuites><testsuite name="p">{body}</testsuite></testsuites>'


# ---- the pin file: one delimiter-safe format, duplicates refused -----------

@pytest.mark.parametrize("line,needle", [
    ('{"node": "a::b", "kind": "nonsense", "why": "w"}', "unknown kind"),
    # the DELETED exception kinds must stay dead: a pin resurrecting either is
    # refused as unknown, never quietly honoured again
    ('{"node": "a::b", "kind": "allow_skip", "needs": "x", "why": "w"}',
     "unknown kind"),
    ('{"node": "a::b", "kind": "allow_fail", "needs": "x", "why": "w"}',
     "unknown kind"),
    ('{"kind": "live_read", "why": "w"}', "missing 'node'"),
    ('{"node": "a::b", "kind": "live_read"}', "missing 'why'"),
    ('not json at all', "not valid JSON"),
])
def test_MATRIX_a_malformed_pin_is_REFUSED(line, needle):
    with pytest.raises(AssertionError) as exc:
        _gate().load_pins(line)
    assert needle in str(exc.value), f"wrong detector: {exc.value}"


def test_MATRIX_a_DUPLICATE_pin_is_REFUSED():
    """Two lines naming one node used to overwrite each other in a dict, so a
    reviewed pin could be silently replaced by an unreviewed one."""
    two = ('{"node": "a::b", "kind": "live_read", "why": "first"}\n'
           '{"node": "a::b", "kind": "live_read", "why": "second"}')
    with pytest.raises(AssertionError, match="duplicate pin"):
        _gate().load_pins(two)


def test_MATRIX_an_id_containing_HASH_or_SLASH_survives_the_pin_format():
    """THE DEFECT THIS CLOSES: the old format used ` # ` as its comment delimiter
    and `partition("#")`, so a real parametrized id was truncated and the pin
    silently named a different node. Both characters occur in this very suite:
    `…LITERAL_evidence[0001306830-24-000155#0]` and `…rejected[x/y]`."""
    hard = ["m::t[0001306830-24-000155#0]", "m::t[x/y]", "m::t[a|b]",
            "m::t[  spaced  ]", "?::m"]
    text = "\n".join(json.dumps({"node": n, "kind": "live_read", "why": "w"})
                     for n in hard)
    assert sorted(_gate().load_pins(text)) == sorted(hard)


def test_MATRIX_a_DUPLICATE_pinned_identity_is_REFUSED():
    """The identity list was read into a set, so a doubled line collapsed."""
    with pytest.raises(AssertionError, match="duplicate identity"):
        _gate().load_expected("a::b\na::b\n")


def test_MATRIX_a_DUPLICATE_JUNIT_identity_is_REFUSED():
    """A dict assignment kept only the last of two colliding identities."""
    with pytest.raises(AssertionError, match="duplicate JUnit identity"):
        _gate().parse_junit(_junit([("m", "t", None, ""), ("m", "t", None, "")]))


def test_MATRIX_the_junit_reader_keeps_the_MESSAGE_and_uses_CLASSNAME():
    """Identities came out as `None::test_x` because pytest leaves `file` empty,
    and only the outcome LABEL was kept — which made a missing database and a
    real assertion indistinguishable."""
    got = _gate().parse_junit(_junit([("pkg.mod", "t", "failure", "KeyError NEO4J_URI")]))
    assert list(got) == ["pkg.mod::t"], "identity must come from classname"
    outcome, text = got["pkg.mod::t"]
    assert outcome == "failed" and "NEO4J_URI" in text


# ---- the verdict: what the gate must refuse to call proven -----------------

_OK_PINS = {"L::t": {"node": "L::t", "kind": "live_read", "why": "graph"}}


@pytest.mark.parametrize("results,pins,expected,needle", [
    # a clean-lane FAILURE — nothing exists to excuse it
    ({"m::t": ("failed", "boom")}, {}, {"m::t"}, "must PASS"),
    # a clean-lane SKIP — a skip is not a pass, and nothing can pin one
    ({"m::t": ("skipped", "later")}, {}, {"m::t"}, "must PASS"),
    # the failure MESSAGE is carried, so a missing database and a real
    # assertion stay distinguishable in the verdict
    ({"m::t": ("failed", "KeyError: NEO4J_URI")}, {}, {"m::t"}, "NEO4J_URI"),
    # a test marked live that RAN in the clean lane: marker and pin disagree
    ({"L::t": ("passed", "")}, _OK_PINS, {"L::t"}, "RAN in the clean lane"),
    # a pinned test that is in NEITHER lane: the commit dropped its file
    ({}, {}, {"gone::t"}, "neither ran"),
    # an identity nobody pinned appeared
    ({"new::t": ("passed", "")}, {}, set(), "not in the pin"),
])
def test_MATRIX_the_gate_REFUSES_each_way_it_used_to_pass(results, pins,
                                                          expected, needle):
    problems = _gate().classify(results, pins, expected)
    assert any(needle in p for p in problems), \
        f"expected a problem containing {needle!r}, got {problems}"


def test_MATRIX_a_fully_clean_lane_yields_NO_problems():
    """The POSITIVE CONTROL. Without it every case above could be satisfied by a
    function that simply complains about everything."""
    results = {"m::t": ("passed", ""), "m::u": ("passed", "")}
    expected = {"m::t", "m::u", "L::t"}
    assert _gate().classify(results, _OK_PINS, expected) == []


# ---- the environment, the exit code, and the tree -------------------------

def test_MATRIX_the_sanitized_environment_carries_NO_credential():
    """THE LEAK THIS CLOSES: the clean lane inherited `**os.environ`, so
    NEO4J_URI/USERNAME/PASSWORD and OPENAI_API_KEY reached the tests and 42 of
    them silently used the real database inside a tree called clean."""
    env = _gate().sanitized_env("/tmp/root", "/tmp/home")
    leaked = [k for k in env if any(s in k.upper() for s in
              ("NEO4J", "OPENAI", "ANTHROPIC", "TOKEN", "PASSWORD", "SECRET",
               "KEY", "CREDENTIAL"))]
    assert not leaked, f"the sanitized environment still carries {leaked}"
    assert env["HOME"] == "/tmp/home", "HOME must not be the real user's"
    # POSITIVE CONTROL: it is not simply empty.
    assert env["PYTHONPATH"] == "/tmp/root" and "PATH" in env


def test_PC2_the_sanitized_environment_hands_the_child_a_writable_TMPDIR(tmp_path):
    """PC-2 (#827). Inside a read-only jail the credential-free child pytest
    died at capture init and produced no report at all: the allowlist carried
    no TMPDIR, and tempfile's whole fallback chain was refused (/tmp EROFS,
    /var/tmp EROFS, /usr/tmp ENOENT, cwd EROFS). TMPDIR is the FIRST name
    CPython's tempfile consults, and `home` — the writable scratch
    sanitized_env is already handed — is the answer that needs no new name in
    the allowlist.

    Proven through a REAL child process rather than by reading the dict back:
    the child resolves its temporary directory to that scratch AND writes a
    file there. The credential control stays where it belongs, in
    test_MATRIX_the_sanitized_environment_carries_NO_credential.
    """
    home = str(tmp_path / "home")
    os.makedirs(home)
    env = _gate().sanitized_env(_REPO, home)
    assert env["TMPDIR"] == home
    child = subprocess.run(
        [sys.executable, "-c",
         "import tempfile\n"
         "with tempfile.NamedTemporaryFile() as f:\n"
         "    f.write(b'x'); f.flush()\n"
         "    print(tempfile.gettempdir())\n"
         "    print(f.name)\n"],
        env=env, capture_output=True, text=True)
    assert child.returncode == 0, child.stderr[-800:]
    where, made = child.stdout.split()
    assert where == home, where
    assert made.startswith(home + os.sep), made


def test_MATRIX_run_lane_REFUSES_a_run_that_did_not_execute(tmp_path):
    """Replaces a test that transcribed the constant `PYTEST_RAN == (0, 1)` —
    which proves the tuple's value, never that run_lane USES it. This drives the
    REAL run_lane both ways: a root whose test roots are empty makes pytest exit
    5 (nothing collected), and run_lane must refuse with its own message — not
    stumble on later on the empty report; a root with one passing test must come
    back parsed. Both spawn a real pytest child under the gate's own sanitized
    environment."""
    gate = _gate()
    home = tmp_path / "home"
    home.mkdir()
    empty = tmp_path / "empty"
    for rel in gate.TEST_ROOTS:
        (empty / rel).mkdir(parents=True)
    with pytest.raises(AssertionError, match="did not run as asked"):
        gate.run_lane(str(empty), str(home))
    # POSITIVE CONTROL: a real run parses back one passed identity.
    good = tmp_path / "good"
    for rel in gate.TEST_ROOTS:
        (good / rel).mkdir(parents=True)
    (good / gate.TEST_ROOTS[0] / "test_mini.py").write_text(
        "def test_ok():\n    assert True\n")
    results = gate.run_lane(str(good), str(home))
    assert [o for o, _t in results.values()] == ["passed"], results


def test_MATRIX_write_expected_can_NEVER_select_or_execute_live_write(
        tmp_path, monkeypatch):
    """THE RE-PIN HOLE THIS CLOSES: `--write-expected` used to run with the FULL
    environment and NO marker filter, so with RUN_NEO4J_ROUNDTRIP_PROBE set it
    would have EXECUTED the write probe — re-pinning identities is bookkeeping,
    and it could write to the live graph. Now `live_write` is excluded
    STRUCTURALLY by the marker filter (a deselected test never executes,
    whatever the environment holds), the opt-in variable is stripped as a second
    independent barrier, and the probe's identity enters the pin from
    gate_pins.jsonl — never from execution.

    Exercised on the REAL write_expected with run_lane mocked out and the opt-in
    variable deliberately SET, so the assertions are about what write_expected
    passes down, not about this machine's environment."""
    gate = _gate()
    seen = {}

    def fake_run_lane(root, home, marker=None, env=None):
        seen["marker"], seen["env"] = marker, env
        return {"m::a_clean_test": ("passed", "")}

    monkeypatch.setattr(gate, "run_lane", fake_run_lane)
    monkeypatch.setattr(gate, "EXPECTED", str(tmp_path / "expected.txt"))
    monkeypatch.setenv("RUN_NEO4J_ROUNDTRIP_PROBE", "1")    # armed, on purpose
    assert gate.write_expected() == 0
    assert seen["marker"] == "not live_write", \
        "write_expected must deselect live_write by MARKER, not by luck"
    assert "RUN_NEO4J_ROUNDTRIP_PROBE" not in seen["env"], \
        "the opt-in variable must be stripped from the child environment"
    pinned = (tmp_path / "expected.txt").read_text().splitlines()
    pins = gate.load_pins(io.open(gate.PINS, encoding="utf-8").read())
    write_nodes = sorted(n for n, r in pins.items() if r["kind"] == "live_write")
    assert write_nodes, "no live_write pin exists — this test lost its premise"
    for node in write_nodes:
        assert node in pinned, \
            f"{node} must enter the pin FROM gate_pins.jsonl, never by running"
    assert "m::a_clean_test" in pinned, "the lane's own identities must be kept"


def _census():
    sys.path.insert(0, os.path.join(_HERE, "receipts_827"))
    import graph_census
    return graph_census


#: THE INDEPENDENT PIN — the exact approved administration statement, held in
#: a DIFFERENT FILE from the code it pins, so the pin can never become a
#: statement about itself (round 12's failure).
APPROVED_SNAPSHOT_CYPHER = \
    "SHOW DATABASE neo4j YIELD lastCommittedTxn, databaseID"


def _assert_snapshot_contract(fn):
    """Drive `fn` against a recording mock and require the whole contract:
    exactly one REQUIRED parameter named `session`; `session.run` called
    EXACTLY ONCE with the approved literal; and the row that call produced
    returned. Behaviour, not source text."""
    import inspect
    import uuid

    # THE FULL PARAMETER CONTRACT, not just the names. Reading names alone
    # accepted `def f(session=None)` — a default lets a caller omit the
    # session entirely, so the "exact (session) signature" claim was false.
    params = list(inspect.signature(fn).parameters.values())
    assert len(params) == 1, (
        f"the snapshot path must take exactly one parameter — no text input, "
        f"no *args/**kwargs: got {[p.name for p in params]}")
    (p,) = params
    assert p.name == "session", f"its parameter must be `session`, not {p.name!r}"
    assert p.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD, \
        f"`session` must be an ordinary parameter, not {p.kind}"
    assert p.default is inspect.Parameter.empty, \
        "`session` must be REQUIRED — a default lets a caller omit it"

    # AN UNFORGEABLE ROW, minted fresh per call: a function that runs the
    # approved statement, DISCARDS the row and returns hard-coded values
    # cannot match values it could not know. Compared by EQUALITY, never
    # identity — returning an equal copy of the row is legitimate.
    row = {"lastCommittedTxn": uuid.uuid4().int % 10 ** 12,
           "databaseID": uuid.uuid4().hex}

    class _Row:
        def data(self):
            return dict(row)

    class _Session:
        def __init__(self):
            self.calls = []

        def run(self, text):
            self.calls.append(text)
            return [_Row()]

    s = _Session()
    got = fn(s)
    assert s.calls == [APPROVED_SNAPSHOT_CYPHER], (
        f"the snapshot path must EXECUTE exactly the approved statement once; "
        f"it ran {s.calls!r}")
    assert got == row, f"it must return the row that call produced, got {got!r}"


def test_827_census_snapshot_statement_is_pinned_AT_RUNTIME():
    """THE INDEPENDENT PIN for the #827 census's one administration read.

    RUNTIME, not source text. The previous version scanned `snapshot_tx`'s
    source for the approved literal — and a mutant that keeps that literal as
    DEAD TEXT while executing a different query passed it (reproduced: the
    scan's own multi-line filter hid the executed statement). A pin that reads
    code instead of running it proves nothing about what the code does.
    """
    _assert_snapshot_contract(_census().snapshot_tx)

    # MUTATION 1 — the runtime analogue of the mutant that defeated the source
    # scan: the approved statement is present only as DEAD TEXT (here a
    # docstring, so nothing is left unused) while another statement executes.
    def dead_text_mutant(session):
        """Carries the approved statement as dead text —
        SHOW DATABASE neo4j YIELD lastCommittedTxn, databaseID
        — while executing something else entirely."""
        return [r.data() for r in session.run("""SHOW TRANSACTIONS
            YIELD transactionId""")][0]

    with pytest.raises(AssertionError, match="exactly the approved statement"):
        _assert_snapshot_contract(dead_text_mutant)

    # MUTATION 2 — the approved statement really runs, but so does a second
    # one: "exactly once" must mean once.
    def extra_call_mutant(session):
        rows = [r.data() for r in session.run(APPROVED_SNAPSHOT_CYPHER)]
        session.run("SHOW TRANSACTIONS")
        return rows[0]

    with pytest.raises(AssertionError, match="exactly the approved statement"):
        _assert_snapshot_contract(extra_call_mutant)

    # MUTATION 3 — THE FORGER: it runs the approved statement, DISCARDS the
    # row, and returns the values the old helper hard-coded. It passed while
    # the expected row was a fixed constant; it cannot pass an unforgeable one.
    def row_discarding_forger(session):
        [r.data() for r in session.run(APPROVED_SNAPSHOT_CYPHER)]
        return {"lastCommittedTxn": 4242, "databaseID": "PINNED-DB"}

    with pytest.raises(AssertionError, match="return the row"):
        _assert_snapshot_contract(row_discarding_forger)

    # MUTATION 4 — it grows a text parameter, which is how an exemption
    # returns: a caller could then supply any statement.
    def widened_signature_mutant(session, text=APPROVED_SNAPSHOT_CYPHER):
        return [r.data() for r in session.run(text)][0]

    with pytest.raises(AssertionError, match="exactly one parameter"):
        _assert_snapshot_contract(widened_signature_mutant)

    # MUTATION 5 — the session becomes OPTIONAL. Reading parameter names alone
    # accepted this, so "exact (session) signature" was an overclaim.
    def optional_session_mutant(session=None):
        return [r.data() for r in session.run(APPROVED_SNAPSHOT_CYPHER)][0]

    with pytest.raises(AssertionError, match="must be REQUIRED"):
        _assert_snapshot_contract(optional_session_mutant)


def test_827_census_gate_REFUSES_administration_including_SHOW_TERMINATE():
    """The general gate accepts ONLY 'r'. Driven against the REAL
    run_read_only with a mocked session, so no statement reaches a server.

    `SHOW TRANSACTIONS … TERMINATE TRANSACTIONS` is the case that matters:
    it is administration, it plans 's', and it begins with SHOW — the
    round-12 allowance executed it (reproduced before this fix)."""
    gate = _census()

    class _Session:
        def __init__(self, planned):
            self.planned, self.calls = planned, []

        def run(self, text):
            self.calls.append(text)
            return type("R", (), {"consume": lambda _self: type(
                "S", (), {"query_type": self.planned})()})()

    for planned, hostile in (
            ("s", "SHOW TRANSACTIONS YIELD transactionId AS txId "
                  "TERMINATE TRANSACTIONS txId"),
            ("s", "CREATE INDEX _x IF NOT EXISTS FOR (n:_X) ON (n.y)"),
            ("s", "SHOW DATABASE neo4j YIELD lastCommittedTxn, databaseID"),
            ("w", "CREATE (n:_NeverRuns) RETURN n"),
            ("rw", "MATCH (n:_NeverRuns) DELETE n RETURN 1")):
        s = _Session(planned)
        with pytest.raises(RuntimeError, match="not read-only"):
            gate.run_read_only(s, hostile)
        assert s.calls == ["EXPLAIN " + hostile], \
            f"only the EXPLAIN may run; saw {s.calls}"
    ok = _Session("r")
    gate.run_read_only(ok, "MATCH (n) RETURN count(n)")
    assert ok.calls == ["EXPLAIN MATCH (n) RETURN count(n)",
                        "MATCH (n) RETURN count(n)"]


#: EVERY LANE THAT CAN ACT ON THE WORLD — write to the graph, or spend money.
#: Both were once defended by a pytest marker alone, and both were reached by
#: someone overriding the marker filter: the Neo4j write probe wrote a node,
#: and the OpenAI judge completed a paid request (incident 2026-07-31). A
#: marker is a SELECTOR, never a guard. One rule, one table — a third such lane
#: is one row here, not a third copy of the reasoning.
GUARDED_LANES = [
    pytest.param(os.path.join(_REPO, "driver", "core",
                              "test_neo4j_numeric_roundtrip.py"),
                 "_require_opt_in", id="neo4j-write-probe"),
    pytest.param(os.path.join(_REPO, "drivers_harness", "tests",
                              "test_synonym_judge_live.py"),
                 "_require_llm_opt_in", id="openai-llm-judge"),
]


def _load_guarded_lane(path):
    """Import a guarded module BY PATH, without pytest collecting it."""
    import importlib.util
    for extra in (os.path.dirname(path),
                  os.path.dirname(os.path.dirname(path))):
        if extra not in sys.path:
            sys.path.insert(0, extra)
    spec = importlib.util.spec_from_file_location("_guarded_lane", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("path,guard", GUARDED_LANES)
@pytest.mark.parametrize("value", [
    pytest.param(None, id="absent"),
    pytest.param("", id="empty"),
    pytest.param("0", id="zero"),
    pytest.param("false", id="false"),
    pytest.param(" ", id="whitespace"),
])
def test_every_ACTING_lane_guard_REFUSES_every_value_except_exactly_1(
        path, guard, value, monkeypatch):
    """THE HOLE THIS CLOSES: the write guard tested TRUTHINESS, so
    RUN_NEO4J_ROUNDTRIP_PROBE=0 — a value every reader understands as OFF —
    AUTHORIZED the live write. An authorization must be exact: the one value
    "1" and nothing else.

    Proven by calling each guard DIRECTLY — no pytest child, no marker, no
    graph, no network; nothing beyond the guard executes.
    """
    mod = _load_guarded_lane(path)
    fn = getattr(mod, guard)
    if value is None:
        monkeypatch.delenv(mod.OPT_IN, raising=False)
    else:
        monkeypatch.setenv(mod.OPT_IN, value)
    with pytest.raises(pytest.skip.Exception):
        fn()
    # POSITIVE CONTROL: the ONE authorized value passes the guard itself.
    monkeypatch.setenv(mod.OPT_IN, "1")
    fn()


@pytest.mark.parametrize("path,guard", GUARDED_LANES)
def test_STRUCTURE_every_ACTING_lane_guards_FIRST_and_never_skips_at_collection(
        path, guard):
    """Two structural laws for every acting lane, pinned on the AST.

    1. NO module-level `importorskip`: it fires during COLLECTION, before any
       marker filter — on a machine without the neo4j package the CLEAN lane
       recorded a skip it could not deselect (reproduced before this fix), the
       exact collection-time disease the in-test guard move was meant to end.
    2. The opt-in guard is EVERY test's FIRST executable statement (a docstring
       may precede it), so nothing that acts can run before it.

    Applied to every guarded lane, so the OpenAI judge cannot regress to
    marker-only protection the way it did before the spend incident. The old
    version checked the write probe only, and asserted that module held exactly
    one test — a count that said nothing about the OTHER lane's three.
    """
    tree = ast.parse(io.open(path, encoding="utf-8").read())
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for sub in ast.walk(node):
            assert not (isinstance(sub, ast.Call)
                        and isinstance(sub.func, ast.Attribute)
                        and sub.func.attr == "importorskip"), \
                "importorskip at MODULE level skips during collection, " \
                "before any marker can deselect the module"
    tests = [n for n in tree.body
             if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
    assert tests, f"{os.path.basename(path)} declares no test to guard"
    for t in tests:
        body = t.body
        if (isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            body = body[1:]                 # a docstring may lawfully lead
        first = body[0]
        assert (isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Call)
                and isinstance(first.value.func, ast.Name)
                and first.value.func.id == guard), (
            f"{os.path.basename(path)}::{t.name} must call {guard}() as its "
            f"FIRST executable statement — anything before it can act")


def test_MATRIX_a_FAILED_live_selector_collection_is_REFUSED(monkeypatch):
    """_live_selectors once ignored its child's exit code, so a usage error or
    a collection crash yielded an EMPTY live set in silence — and every live
    proof would then be misfiled into the clean lane. A failed collection must
    refuse loudly, never classify."""
    monkeypatch.setattr(sys.modules[__name__], "_registry_selectors",
                        lambda: ["no/such/file.py::nope"])
    with pytest.raises(AssertionError, match="cannot be derived"):
        _live_selectors()


def test_MATRIX_build_isolated_tree_verifies_HASH_EQUALITY_for_real(
        tmp_path, monkeypatch):
    """Replaces a test that proved only that `git write-tree` changes when a
    file is added — git's documented behaviour, never the gate's code. This one
    drives the REAL build_isolated_tree, both ways.

    THE ATTACK IS A REAL CLASS: a blob stored with CRLF under a `text`
    attribute does not survive its own tree's round-trip — `git archive` hands
    over the CRLF bytes, the fresh repository's `git add` normalises them to
    LF, and the rebuilt tree is a DIFFERENT commit (probed for real before this
    test was written). The historical overlay defect was the same shape: bytes
    in the tree that are not what the index said. The `got == tree` assert is
    the one check that catches every member of that class."""
    gate = _gate()

    def _git(cwd, *a):
        r = subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        return r.stdout.strip()

    # POSITIVE: a faithful tree rebuilds to the SAME hash and is handed back.
    good = tmp_path / "good"
    good.mkdir()
    _git(good, "init", "-q")
    (good / "a.txt").write_text("one\n")
    _git(good, "add", "a.txt")
    tree = _git(good, "write-tree")
    monkeypatch.setattr(gate, "_REPO", str(good))
    base1 = tmp_path / "b1"
    base1.mkdir()
    built = gate.build_isolated_tree(tree, str(base1))
    assert _git(built, "write-tree") == tree, \
        "the repository build_isolated_tree returned is not the commit"

    # ATTACK: the same function must REFUSE a tree whose bytes cannot survive
    # the round-trip. CRLF enters the index first; the attribute arrives after.
    bad = tmp_path / "bad"
    bad.mkdir()
    _git(bad, "init", "-q")
    (bad / "a.txt").write_bytes(b"one\r\n")
    _git(bad, "add", "a.txt")
    (bad / ".gitattributes").write_text("a.txt text\n")
    _git(bad, "add", ".gitattributes")
    tree2 = _git(bad, "write-tree")
    monkeypatch.setattr(gate, "_REPO", str(bad))
    base2 = tmp_path / "b2"
    base2.mkdir()
    with pytest.raises(AssertionError, match="NOT the commit"):
        gate.build_isolated_tree(tree2, str(base2))


def test_MATRIX_post_run_changes_SEES_tracked_untracked_AND_ignored_files(
        tmp_path):
    """Replaces a test that showed `git status` notices a rewritten tracked file
    — again git's behaviour, not the gate's, and it silently blessed the gate's
    own `--untracked-files=no`, under which a test could DROP a brand-new file
    into the isolated tree invisibly. Drives the gate's REAL post-run check on a
    real repository, all FOUR ways — the fourth is the IGNORED dropping: the
    isolated tree carries tracked .gitignore files, so without `--ignored` a
    test could leave anything matching an ignore rule behind unseen. The tree
    starts pristine and cache/bytecode are disabled, so there is nothing an
    ignored line could report except a test's own leavings."""
    gate = _gate()

    def _git(*a):
        subprocess.run(["git", *a], cwd=tmp_path, check=True,
                       capture_output=True)

    _git("init", "-q")
    (tmp_path / "a.txt").write_text("one\n")
    (tmp_path / ".gitignore").write_text("*.log\n")
    _git("add", "a.txt", ".gitignore")
    _git("-c", "user.name=t", "-c", "user.email=t@x", "commit", "-q", "-m", "c")
    assert gate.post_run_changes(str(tmp_path)) == [], \
        "a clean tree must report nothing, or every gate run fails vacuously"
    (tmp_path / "a.txt").write_text("rewritten by a test\n")
    tracked = gate.post_run_changes(str(tmp_path))
    assert len(tracked) == 1 and "a.txt" in tracked[0], tracked
    (tmp_path / "dropping.txt").write_text("left behind by a test\n")
    both = gate.post_run_changes(str(tmp_path))
    assert len(both) == 2, both
    assert any(ln.startswith("??") and "dropping.txt" in ln for ln in both), \
        "an untracked test-created file must be VISIBLE — this was the hole"
    (tmp_path / "leftover.log").write_text("ignored dropping\n")
    everything = gate.post_run_changes(str(tmp_path))
    assert len(everything) == 3, everything
    assert any(ln.startswith("!!") and "leftover.log" in ln for ln in everything), \
        "an IGNORED test-created file must be VISIBLE too — the ignore rules " \
        "in the tree must not become a blind spot"


# ---------------------------------------------------------------------------
# IMPORTING MUST NOT CREDENTIAL THE PROCESS.
#
# THE DEFECT THIS CLOSES was the whole reason a "clean, database-free" lane was
# not one. `get_quarterly_filings.py` called
# `load_dotenv("/home/faisal/.../.env", override=True)` at MODULE level, so any
# test that transitively imported it — via `build_packets` — pulled 14 variables
# into the process: all three Neo4j credentials and seven API keys. `override=True`
# meant a deliberately scrubbed environment was overwritten, so sanitizing at
# launch bought nothing and read-only graph tests silently passed against the real
# database inside a run reported as credential-free.
#
# Checked in a FRESH SUBPROCESS, so the result cannot depend on test order — which
# is exactly how the original went unnoticed inside a full-suite run.
# ---------------------------------------------------------------------------

_CREDENTIALISH = ("NEO4J", "OPENAI", "ANTHROPIC", "API_KEY", "TOKEN", "PASSWORD",
                  "SECRET", "LANGSMITH", "LANGCHAIN", "PERPLEXITY", "TAVILY",
                  "GROK", "OPENROUTER", "ALPHAVANTAGE", "CREDENTIAL")


def _credentials_gained_by_importing(module, extra_path=None):
    """Names matching the credential vocabulary that appear in os.environ purely
    because `module` was imported, measured in a clean child process."""
    probe = (
        "import os, json, sys\n"
        f"BAD = {_CREDENTIALISH!r}\n"
        "before = set(os.environ)\n"
        "try:\n"
        f"    import {module}\n"
        "    err = None\n"
        "except BaseException as exc:\n"
        "    err = f'{type(exc).__name__}: {exc}'[:200]\n"
        "gained = sorted(k for k in set(os.environ) - before\n"
        "                if any(b in k.upper() for b in BAD))\n"
        "sys.stdout.write(json.dumps({'gained': gained, 'err': err}))\n")
    # THE GATE'S ALLOWLIST ENVIRONMENT with a throwaway HOME — never a
    # credential blocklist, which admits the next name nobody enumerated.
    # _CREDENTIALISH remains the DETECTION vocabulary below; it no longer
    # sanitizes anything.
    with tempfile.TemporaryDirectory() as home:
        env = _gate().sanitized_env(_REPO, home)
        # `driver/relocation` too: `locator` imports `exact_numbers` as a
        # sibling, so the repo root alone cannot import it. That is an
        # import-convention fact about the module, not a credential question,
        # and it must not be mistaken for one.
        env["PYTHONPATH"] = os.pathsep.join(
            [p for p in (_REPO, os.path.join(_REPO, "driver", "relocation"),
                         extra_path) if p])
        r = subprocess.run([sys.executable, "-c", probe], cwd=_REPO,
                           capture_output=True, text=True, env=env)
    assert r.stdout, f"the probe did not report: {r.stderr[-400:]}"
    out = json.loads(r.stdout)
    assert out["err"] is None, f"{module} could not be imported: {out['err']}"
    return out["gained"]


@pytest.mark.parametrize("module", [
    "scripts.driver_seed.build_packets",       # the transitive route that leaked
    "driver.core.prepared_fact_v2",
    "driver.core.xbrl_attach",
    "driver.relocation.locator",
])
def test_importing_a_module_gains_ZERO_credentials(module):
    gained = _credentials_gained_by_importing(module)
    assert gained == [], (
        f"importing {module} put {len(gained)} credential variable(s) into the "
        f"process: {gained}. A clean lane cannot be made clean by sanitizing the "
        f"launch if an import re-supplies them.")


def test_the_credential_PROBE_ITSELF_can_detect_a_leak(tmp_path):
    """THE POSITIVE CONTROL, and it is not optional: every assertion above is
    `== []`, which a probe that always returns nothing would also satisfy. So the
    probe must be shown a module that really does leak, and must see it.

    THE LEAKY MODULE IS BUILT HERE AND DIES HERE. My first version committed it to
    `driver/core/_probe_sets_a_credential.py` — a permanent file in the shipped
    tree whose only purpose was to set a fake credential, importable by anything
    and collected by every scan. A control needs to exist for one subprocess, not
    forever.
    """
    leaky = tmp_path / "_leaky_control.py"
    leaky.write_text('import os\n'
                     'os.environ["NEO4J_PASSWORD"] = "not-a-real-password"\n')
    gained = _credentials_gained_by_importing("_leaky_control",
                                              extra_path=str(tmp_path))
    assert "NEO4J_PASSWORD" in gained, (
        f"the probe cannot see a credential that WAS added: {gained}")


# ---------------------------------------------------------------------------
# #827 ROUND 4 — the census read gate now accepts PARAMETERS, and the claim
# that this cannot widen it rests entirely on ONE property: the statement that
# was EXPLAIN-planned is the statement that executes, values included. That was
# asserted in a docstring and proven nowhere.
# ---------------------------------------------------------------------------

class _RecordingSession:
    """Captures every (text, params) pair the gate issues."""

    def __init__(self, query_type="r"):
        self.calls = []
        self._type = query_type

    def run(self, text, **params):
        self.calls.append((text, params))
        session = self

        class _Result:
            def consume(self):
                class _Summary:
                    query_type = session._type
                return _Summary()
        return _Result()


def test_827_the_read_gate_plans_and_executes_the_SAME_parameters():
    """EXPLAIN and the execution must receive IDENTICAL parameters. If the plan
    were computed without the values the caller then supplies, the gate would be
    approving a different statement from the one that runs — and 'parameters
    cannot widen this gate' would be an unbacked claim."""
    import importlib.util
    path = os.path.join(_REPO, ".claude", "plans", "Drivers", "experiments",
                        "harness", "receipts_827", "graph_census.py")
    spec = importlib.util.spec_from_file_location("_gc_gate", path)
    gc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gc)

    session = _RecordingSession()
    text = "MATCH (x:XBRLNode) WHERE x.accessionNo IN $accs RETURN x"
    gc.run_read_only(session, text, accs=["0000320193-24-000001"])

    assert len(session.calls) == 2, session.calls
    (explain_text, explain_params), (run_text, run_params) = session.calls
    assert explain_text == "EXPLAIN " + text
    assert run_text == text
    assert explain_params == run_params == {"accs": ["0000320193-24-000001"]}, (
        f"planned with {explain_params} but executed with {run_params} — the "
        f"gate approved a different statement from the one that ran")


def test_827_the_read_gate_still_REFUSES_a_non_read_plan_with_parameters():
    """The refusal must not weaken merely because parameters are present."""
    import importlib.util
    path = os.path.join(_REPO, ".claude", "plans", "Drivers", "experiments",
                        "harness", "receipts_827", "graph_census.py")
    spec = importlib.util.spec_from_file_location("_gc_gate2", path)
    gc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gc)
    session = _RecordingSession(query_type="w")
    with pytest.raises(RuntimeError, match="not read-only"):
        gc.run_read_only(session, "CREATE (n:X {v: $v})", v=1)
    assert len(session.calls) == 1, "a refused statement must never execute"
