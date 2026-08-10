"""#827 round 7b — THE REVIEWER'S CASE LIST, EACH MAPPED TO A RUNNING PROOF.

The reviewer asked for a reconcile against "the exact 22-case audit". I do not
hold his numbered list, so this does NOT claim to reproduce his partition. It
does something stronger and checkable: every case he stated IN HIS OWN WORDS,
across the round-7 blocker report and the round-7b follow-up, is quoted here
verbatim and bound to the test node(s) that prove it — and those nodes are then
RUN, so the map is evidence rather than a table of promises.

If his 22 is a subset of the cases below, all 22 are covered. If a case of his
is absent, this file is where the omission shows, because a case with no proof
node is a hard error here rather than a silent gap.

WHY THIS EXISTS: the prose claim "all his cases are closed" was true but
unprovable, which is exactly the defect this audit keeps finding — a coverage
ledger keyed on the wrong thing hid 34 of 51 parameters while reading as
complete. A count I reconstructed myself is not a receipt.

Read-only: no graph, no network, no AI, no writes outside this receipt.

Run:  venv/bin/python receipts_827/case_map.py
Out:  receipts_827/15_reviewer_case_map.json
"""
import ast
import hashlib
import re
import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", "..", ".."))
OUT = os.path.join(_HERE, "15_reviewer_case_map.json")

R5 = "driver/relocation/test_bind_graph_fact.py"
R8 = "driver/core/test_round8_xbrl_binding.py"
R10 = "driver/core/test_round10_event_boundary.py"
R12U = "driver/core/test_round12_pure_unit_law.py"
V2 = "driver/core/test_v2_attacks.py"
#: The round-9 public two-view bridge suite — where the EXACT namespace
#: attacks live, each beside its lawful twin.
BRIDGE = "driver/relocation/test_two_view_bridge.py"

#: (source relay, VERBATIM case as the reviewer wrote it, [proof node ids]).
#: The quotes are copied, never paraphrased — a paraphrase is where a case
#: quietly changes meaning.
#:
#: THIS FILE HAS ONE JOB: reviewer case -> the exact tests that execute it.
#: It used to carry mutation ids too, and they OVERSTATED the evidence — the
#: four exact namespace cases all cited the same two generic mutations, neither
#: of which individually proves a near-miss URI, fake xmlns text, sibling scope
#: or case-sensitive lookup. Receipt 17 holds the mutation mapping, with each
#: mutation's own named failing node; duplicating it here could only drift.
CASES = [
    # ---- round-7 blocker report: "Main gaps are in inline_html.py" ----------
    ("R7", "NBSP/zero-width-padded dates attach",
     [f"{R5}::test_827R6_a_MALFORMED_filer_identity_never_binds",
      f"{R8}::test_filing_boundary_REFUSES_every_malformed_form"]),
    ("R7", "Padded graph CIKs ... attach",
     [f"{R5}::test_827R6_a_GRAPH_cik_outside_the_stored_form_never_binds"]),
    ("R7", "... and graph numbers attach",
     [f"{R5}::test_827R6_a_PADDED_graph_value_is_not_the_value",
      f"{R5}::test_827R6_a_graph_value_outside_the_derived_grammar_is_refused"]),
    ("R7", "(-390,000,000) incorrectly becomes positive",
     [f"{R5}::test_827R6_accounting_parens_may_not_carry_a_SECOND_sign"]),
    # CORRECTED 2026-08-01 (Codex SEQ 39/40). These two rows previously cited
    # BROADER tests that never executed the case they claimed: the extra-slash
    # row pointed at generic wrong-URI/undeclared-prefix tests, and the
    # fake-script row pointed at ordinary lawful-prefix binding tests that
    # build no script or comment at all. A case map that names a broader
    # passing test is worse than an empty one, because it reads as covered.
    #
    # Each row now names ONLY its own attack and that attack's lawful twin, and
    # the two further near-miss classes get rows of their own rather than being
    # bundled under the script claim.
    ("R7", "A namespace URI with an extra /, ... is trusted",
     [f"{BRIDGE}::test_ATTACK_a_NEAR_MISS_namespace_URI_is_a_different_namespace",
      f"{BRIDGE}::test_the_EXACT_official_URI_is_a_fact"]),
    ("R7", "... or a fake declaration inside <script>, is trusted",
     [f"{BRIDGE}::test_ATTACK_xmlns_looking_TEXT_declares_nothing",
      f"{BRIDGE}::test_a_REAL_declaration_attribute_does_declare"]),
    ("R9", "a declaration on an unrelated sibling is in scope",
     [f"{BRIDGE}::test_ATTACK_a_declaration_on_an_unrelated_SIBLING_is_not_in_scope",
      f"{BRIDGE}::test_the_SAME_declaration_on_an_ANCESTOR_is_in_scope"]),
    ("R9", "a prefix declared only in another case is the same prefix",
     [f"{BRIDGE}::test_ATTACK_a_prefix_declared_only_in_ANOTHER_CASE_is_undeclared",
      f"{BRIDGE}::test_the_SAME_declaration_used_in_ITS_OWN_case_resolves"]),
    ("R7", "Invalid context ... IDs attach",
     [f"{R5}::test_827R5_a_GENUINE_duplicate_context_id_still_says_duplicate",
      f"{R5}::test_827R5_MALFORMED_structure_is_NEVER_called_a_duplicate_id"]),
    ("R7", "Invalid ... unit ... IDs attach",
     [f"{R5}::test_827R5_a_GENUINE_duplicate_unit_id_still_says_duplicate"]),
    ("R7", "Invalid ... fact IDs attach",
     [f"{R5}::test_827R7_an_UNLAWFUL_element_id_is_MALFORMED_under_its_own_name",
      f"{R5}::test_827R7_the_PUBLIC_id_door_refuses_an_unlawful_id_for_EVERY_caller"]),
    ("R7", "Invalid concept ... names attach",
     [f"{R5}::test_827R7_an_UNLAWFUL_concept_QName_never_binds",
      f"{R5}::test_827R7_the_concept_rule_covers_the_FALLBACK_path_too"]),
    ("R7", "Invalid ... measure names attach",
     [f"{R5}::test_827R6_item4_an_unknown_direct_child_of_a_unit",
      f"{R5}::test_827R5_a_MISPLACED_unit_element_refuses_with_ITS_OWN_reason"]),
    ("R7", "Nested dimension markup ... attach",
     [f"{R5}::test_827R6_a_NESTED_context_never_binds",
      f"{R5}::test_827R6_item4_markup_nested_inside_a_measure"]),
    ("R7", "... overlapping ratio measures ... attach",
     [f"{R5}::test_827R6_a_NESTED_or_SELF_RATIO_unit_never_binds"]),
    ("R7", "... and unknown children inside divide containers attach",
     [f"{R5}::test_827R5_a_MISPLACED_unit_element_refuses_with_ITS_OWN_reason",
      f"{R5}::test_827R5_MUST_ALLOW_lawful_unit_shapes_still_bind"]),

    # ---- round-7 blocker report: "The proof system also remains false-green"
    ("R7", "test_v2_attacks.py:1195 collapses 51 (function, parameter) pairs "
           "into 17 function names",
     [f"{V2}::test_827R6_every_public_callable_NAMES_the_test_that_covers_it",
      f"{V2}::test_827R6_every_named_test_node_really_exists"]),
    ("R7", "Its field check still catches every Exception, including "
           "programming crashes",
     [f"{V2}::test_827_every_public_INPUT_FIELD_is_REALLY_VALIDATED"]),
    ("R7", "scan_filing_dates.py:102 verifies the .htm manifest, then scans "
           "every file",
     [f"{R8}::test_the_date_CENSUS_and_the_PRODUCTION_parser_agree_on_legality"]),
    ("R7", "make_index.py:58 says nothing live ran, while receipt 07 records "
           "11 live tests", []),
    ("R7", "The 53 mutations do not cover these holes", []),

    # ---- round-7b follow-up: "Your summary did not explicitly prove ..." ----
    ("R7b", "padded filing CIK",
     [f"{R5}::test_827R6_a_MALFORMED_filer_identity_never_binds",
      f"{R5}::test_827R6_a_filing_CIK_of_ONE_DIGIT_fails_while_the_ten_digit_form_binds",
      f"{R5}::test_827R6_MUST_ALLOW_the_lawful_filer_identity_still_binds"]),
    ("R7b", "vertical-tab/form-feed dates",
     [f"{R8}::test_filing_boundary_REFUSES_every_malformed_form"]),
    ("R7b", "invalid or NBSP-only fact IDs",
     [f"{R5}::test_827R7_an_UNLAWFUL_element_id_is_MALFORMED_under_its_own_name",
      f"{R5}::test_827R7_MUST_ALLOW_an_XML_blank_id_still_uses_the_identity_fallback",
      f"{R10}::test_827R7_UNICODE_whitespace_is_NOT_a_blank_fact_id"]),
    ("R7b", "invalid concept QName",
     [f"{R5}::test_827R7_an_UNLAWFUL_concept_QName_never_binds",
      f"{R5}::test_827R7_MUST_ALLOW_real_concept_QNames_still_bind"]),
    ("R7b", "junk inside numerator",
     [f"{R5}::test_827R5_a_MISPLACED_unit_element_refuses_with_ITS_OWN_reason",
      f"{R5}::test_827R6_item4_an_unknown_direct_child_of_a_unit"]),
    ("R7b", "distinct raw-value identities",
     [f"{R10}::test_827R6_a_PADDED_fact_id_is_a_DIFFERENT_id_and_order_cannot_decide",
      f"{R10}::test_827R7_UNICODE_whitespace_is_NOT_a_blank_fact_id"]),
    ("R7b", "Remove the remaining broad except Exception",
     [f"{V2}::test_827_every_public_INPUT_FIELD_is_REALLY_VALIDATED"]),
    ("R7b", "Prove all 51 (owner, parameter) mappings",
     [f"{V2}::test_827R6_every_public_callable_NAMES_the_test_that_covers_it",
      f"{V2}::test_827R6_every_named_test_node_really_exists"]),
]

#: Cases whose proof is NOT a pytest node, and what it is instead. Naming a
#: test for a documentation correction would be the same invented
#: reproducibility the receipt index was built to stop.
NON_TEST_PROOF = {
    "make_index.py:58 says nothing live ran, while receipt 07 records 11 live "
    "tests":
        "receipts_827/03_commands_and_hashes.txt — the 07 provenance line now "
        "states all three facts (43 live + 1 live_write collected; ONE "
        "separately executed read-only live run, 11 passed, tx-bracketed; the "
        "isolated gate runs -m 'not live and not live_write' and executes NO "
        "live test). Corroborated by the gate's own stdout.",
    "The 53 mutations do not cover these holes":
        "the step-4 battery covers them; six rows (58-63) were added for the "
        "round-7b rules specifically. P-O6 (#827): the RESULT is not claimed "
        "here. The in-tree 10_step4_mutations.json is retired (see its "
        "TOMBSTONE) and the outcome lives in the EXTERNAL receipt produced "
        "by the O6 RUN, after tree T is captured — a source file may say "
        "what must be produced, never assert how a run that has not "
        "happened in this tree turned out.",
    "scan_filing_dates.py:102 verifies the .htm manifest, then scans every "
    "file":
        "receipts_827/09_filing_date_inventory.json — the census now scans "
        "EXACTLY the manifest names and records input_manifest_sha256.",
}


def _functions_in(path):
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    return {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}


def main():
    # 1. EVERY case must have a proof of SOME kind. A case with neither a test
    #    node nor a named non-test artifact is an admitted gap, and it stops
    #    the run rather than printing as a blank cell.
    orphans = [c for _s, c, nodes in CASES
               if not nodes and c not in NON_TEST_PROOF]
    if orphans:
        raise SystemExit(f"{len(orphans)} case(s) have no proof at all: {orphans}")

    # 2. EVERY named node must exist on disk, checked by parsing — a map that
    #    points at a test that is not there is worse than no map.
    missing = []
    for _s, case, nodes in CASES:
        for node in nodes:
            path, _, func = node.partition("::")
            full = os.path.join(_REPO, path)
            if not os.path.exists(full) or func not in _functions_in(full):
                missing.append(f"{case!r} -> {node}")
    if missing:
        raise SystemExit(f"{len(missing)} proof node(s) do not exist: {missing}")

    # 4. RUN every distinct node. A map of nodes that do not pass is a map of
    #    nothing; this is the step that makes the file evidence.
    every = sorted({n for _s, _c, nodes in CASES for n in nodes})
    print(f"{len(CASES)} cases · {len(every)} distinct proof nodes · running")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:randomly",
         "-p", "no:cacheprovider", "--no-header", "--tb=line",
         "-m", "not live and not live_write", *every],
        cwd=_REPO, capture_output=True, text=True)
    tail = (proc.stdout or "").strip().splitlines()[-1:] or [""]
    # THE COUNT IS THE EVIDENCE; THE DURATION IS NOISE. pytest ends its summary
    # with "in 0.64s", which differs on every run and made this receipt
    # impossible to reproduce byte for byte. It is dropped here so a second run
    # of this generator can be PROVEN identical.
    tail = [re.sub(r"\s+in\s+[\d.]+s$", "", tail[0])]
    print(f"   pytest exit {proc.returncode}: {tail[0]}")
    if proc.returncode != 0:
        raise SystemExit("proof nodes did not all pass — the map is not "
                         "evidence until they do")

    by_source = {}
    for src, _c, _n in CASES:
        by_source[src] = by_source.get(src, 0) + 1
    doc = {
        "receipt": "#827 round 7b — the reviewer's stated cases, each mapped "
                   "to a proof that was RUN",
        "scope_note": "The reviewer's own numbered 22-case list is not held "
                      "here. Every case he stated VERBATIM across both relays "
                      "is listed; if his 22 is a subset of these, all 22 are "
                      "covered. A case of his that is absent would be an "
                      "omission this file cannot see, which is why the quotes "
                      "are verbatim and the count is reported, not asserted.",
        "script_sha256": hashlib.sha256(
            open(os.path.abspath(__file__), "rb").read()).hexdigest(),
        "cases_total": len(CASES),
        "cases_by_relay": by_source,
        "distinct_proof_nodes": len(every),
        "proof_nodes_pytest_exit": proc.returncode,
        "proof_nodes_result": tail[0],
        "cases": [
            {"relay": src, "reviewer_words": case, "proof_nodes": nodes,
             "non_test_proof": NON_TEST_PROOF.get(case)}
            for src, case, nodes in CASES
        ],
    }
    # BYTE-DETERMINISTIC BY CONSTRUCTION. No timestamp, and no self-hash:
    # a hash that excludes a changing field is proof machinery standing in
    # for determinism. Two runs of this generator produce the same bytes,
    # which is the property, and it is checked by comparing the files.
    with open(OUT, "w") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(f"all {len(every)} proof nodes PASS")
    print(f"wrote {os.path.basename(OUT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
