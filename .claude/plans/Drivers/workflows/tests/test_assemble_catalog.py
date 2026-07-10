"""TDD for assemble_catalog.py — the deterministic catalog writer (HierarchicalCatalogPlan §11.19/§12.7).

Ports reconcile.js:89-94's 5-way precedence VERBATIM:
  1 skip wins -> skips[]
  2 approved SAME_AS w/ KEPT canonical -> canonical_name = canonical
  3 approved rewrite w/ KEPT target    -> canonical_name = target
  4 parked rewrite -> unresolved_rewrites[]
  5 else -> self-canonical
KEPT = seed names - skipped - parked. Evidence copied VERBATIM.
same_as_variants mirrors the applied folds (HierarchicalCatalogPlan §3e/§11.5).
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

WORKFLOWS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOWS))

from assemble_catalog import assemble, serialize  # noqa: E402

PY = sys.executable


def rec(name, company="AAA", quote=None):
    return {
        "driver_name": name,
        "canonical_name": name,
        "companies": [company],
        "evidence_refs": [{
            "company": company, "source_type": "transcript",
            "source_id": f"ev_{name}_{company}", "date": "2026-01-01",
            "quote": quote or f"quote about {name}",
        }],
    }


def seed_of(*names):
    return {"industry": "TestInd", "slug": "test_ind", "run_id": "r1",
            "catalog": [rec(n) for n in names], "analysis": {}}


def dec(gate=None, same_as=None, rewrites=None, parked=None):
    return {"gate_verdicts": gate or [], "approved_same_as": same_as or [],
            "approved_rewrites": rewrites or [], "parked_rewrites": parked or []}


def names_of(cat):
    return sorted(r["driver_name"] for r in cat["catalog"])


def by_name(cat, name):
    return next(r for r in cat["catalog"] if r["driver_name"] == name)


def test_all_admit_self_canonical():
    cat, approved = assemble(seed_of("alpha_sales", "beta_margin"), dec())
    assert names_of(cat) == ["alpha_sales", "beta_margin"]
    assert all(r["canonical_name"] == r["driver_name"] for r in cat["catalog"])
    assert all(r["same_as_variants"] == [] for r in cat["catalog"])
    assert cat["skips"] == [] and cat["unresolved_rewrites"] == []
    assert cat["counts"] == {"keep": 2, "same_as": 0, "rewrite": 0, "skip": 0, "unresolved": 0}
    assert approved == {"same_as": [], "rewrites": [], "high_blast_refute2": []}


def test_same_as_folds_and_mirrors_variant():
    cat, _ = assemble(seed_of("guest_count", "customer_transactions"),
                      dec(same_as=[{"variant": "customer_transactions", "canonical": "guest_count"}]))
    assert by_name(cat, "customer_transactions")["canonical_name"] == "guest_count"
    assert by_name(cat, "guest_count")["same_as_variants"] == ["customer_transactions"]
    assert by_name(cat, "customer_transactions")["same_as_variants"] == []
    assert cat["counts"]["same_as"] == 1 and cat["counts"]["keep"] == 1


def test_skip_wins_over_same_as():
    cat, _ = assemble(
        seed_of("guest_count", "customer_transactions"),
        dec(gate=[{"driver_name": "customer_transactions", "verdict": "skip", "reason": "vague"}],
            same_as=[{"variant": "customer_transactions", "canonical": "guest_count"}]))
    assert names_of(cat) == ["guest_count"]
    assert cat["skips"] == [{"driver_name": "customer_transactions", "why": "vague"}]
    assert by_name(cat, "guest_count")["same_as_variants"] == []  # skipped variant excluded (§11.5)


def test_canonical_skipped_variant_falls_to_admit():
    cat, _ = assemble(
        seed_of("guest_count", "customer_transactions"),
        dec(gate=[{"driver_name": "guest_count", "verdict": "skip", "reason": "rule-break"}],
            same_as=[{"variant": "customer_transactions", "canonical": "guest_count"}]))
    assert names_of(cat) == ["customer_transactions"]
    assert by_name(cat, "customer_transactions")["canonical_name"] == "customer_transactions"


def test_rewrite_applied_with_kept_target():
    cat, _ = assemble(seed_of("gross_margin", "margin_gross"),
                      dec(gate=[{"driver_name": "margin_gross", "verdict": "rewrite",
                                 "rewrite_to": "gross_margin", "reason": "word order"}],
                          rewrites=[{"from": "margin_gross", "to": "gross_margin"}]))
    assert by_name(cat, "margin_gross")["canonical_name"] == "gross_margin"
    assert by_name(cat, "gross_margin")["same_as_variants"] == ["margin_gross"]
    assert cat["counts"]["rewrite"] == 1


def test_parked_rewrite_goes_to_unresolved():
    cat, _ = assemble(seed_of("gross_margin", "margin_gross"),
                      dec(gate=[{"driver_name": "margin_gross", "verdict": "rewrite",
                                 "rewrite_to": "gross_margin", "reason": "word order"}],
                          parked=[{"driver_name": "margin_gross", "proposed_to": "gross_margin",
                                   "why": "refuted by skeptic"}]))
    assert names_of(cat) == ["gross_margin"]
    assert cat["unresolved_rewrites"] == [{"driver_name": "margin_gross",
                                           "proposed_to": "gross_margin", "why": "refuted by skeptic"}]
    assert by_name(cat, "gross_margin")["same_as_variants"] == []


def test_rewrite_target_parked_falls_to_admit():
    # C -> D approved, but D itself parked: D not KEPT -> C admits self-canonical (rule 5 fallback).
    cat, _ = assemble(seed_of("name_c", "name_d"),
                      dec(rewrites=[{"from": "name_c", "to": "name_d"}],
                          parked=[{"driver_name": "name_d", "proposed_to": "other", "why": "refuted"}]))
    assert by_name(cat, "name_c")["canonical_name"] == "name_c"
    assert [u["driver_name"] for u in cat["unresolved_rewrites"]] == ["name_d"]


def test_completeness_partition():
    seed = seed_of("a_one", "b_two", "c_three", "d_four", "e_five")
    cat, _ = assemble(seed, dec(
        gate=[{"driver_name": "a_one", "verdict": "skip", "reason": "vague"}],
        same_as=[{"variant": "b_two", "canonical": "c_three"}],
        parked=[{"driver_name": "d_four", "proposed_to": "c_three", "why": "refuted"}]))
    everywhere = (names_of(cat) + [s["driver_name"] for s in cat["skips"]]
                  + [u["driver_name"] for u in cat["unresolved_rewrites"]])
    assert sorted(everywhere) == ["a_one", "b_two", "c_three", "d_four", "e_five"]


def test_case_insensitive_resolution_keeps_seed_strings():
    cat, _ = assemble(seed_of("guest_count", "customer_transactions"),
                      dec(same_as=[{"variant": "Customer_Transactions", "canonical": "GUEST_COUNT"}]))
    assert by_name(cat, "customer_transactions")["canonical_name"] == "guest_count"  # seed-exact string


def test_verbatim_copy_of_evidence_and_links():
    seed = seed_of("alpha_sales")
    cat, _ = assemble(seed, dec())
    assert by_name(cat, "alpha_sales")["evidence_refs"] == seed["catalog"][0]["evidence_refs"]


def test_gate_rewrite_without_list_entry_hard_fails():
    with pytest.raises(SystemExit):
        assemble(seed_of("alpha_sales"),
                 dec(gate=[{"driver_name": "alpha_sales", "verdict": "rewrite",
                            "rewrite_to": "x", "reason": "r"}]))


def test_cli_deterministic_bytes(tmp_path):
    run = tmp_path / "run1"
    run.mkdir()
    (run / "seed.json").write_text(serialize(seed_of("guest_count", "customer_transactions")))
    (run / "decisions.json").write_text(serialize(
        dec(gate=[{"driver_name": "guest_count", "verdict": "admit", "reason": "t"},
                  {"driver_name": "customer_transactions", "verdict": "admit", "reason": "t"}],
            same_as=[{"variant": "customer_transactions", "canonical": "guest_count"}])))
    shas = []
    for _ in range(2):
        out = subprocess.run([PY, str(WORKFLOWS / "assemble_catalog.py"), str(run)],
                             capture_output=True, text=True)
        assert out.returncode == 0, out.stderr
        shas.append((hashlib.sha256((run / "catalog.json").read_bytes()).hexdigest(),
                     hashlib.sha256((run / "approved.json").read_bytes()).hexdigest()))
        assert shas[-1][0] in out.stdout  # CLI prints the catalog sha
    assert shas[0] == shas[1]
    approved = json.loads((run / "approved.json").read_text())
    assert approved == {"same_as": [{"variant": "customer_transactions", "canonical": "guest_count"}],
                        "rewrites": [], "high_blast_refute2": []}


def test_carried_variants_preserved_and_merged():
    # Fold-parent seeds carry child same_as_variants (§11.5) — assembler must PRESERVE them
    # and UNION with this level's own folds (D8 NAMES would fail otherwise).
    seed = seed_of("alpha_sales", "beta_margin")
    seed["catalog"][0]["same_as_variants"] = ["child_variant_x"]
    cat, _ = assemble(seed, dec(same_as=[{"variant": "beta_margin", "canonical": "alpha_sales"}]))
    assert by_name(cat, "alpha_sales")["same_as_variants"] == ["beta_margin", "child_variant_x"]
    assert by_name(cat, "beta_margin")["canonical_name"] == "alpha_sales"


# ---------------------------------------------------------------- --review (leaf flag-triggered D5)
# HierarchicalCatalogPlan D5/§3c/§11.6/§12.4 leaf path: occurrence key = company. The review
# re-shapes the seed records BEFORE the 5-way precedence: SAME -> keep (refute_survived
# REQUIRED, fail-close) · DIFFERENT -> replace with coined split records per the assignment
# map (complete evidence partition) · UNCLEAR -> park to the unresolved_same_name side-list.

CLI = str(WORKFLOWS / "assemble_catalog.py")
VALIDATOR = str(WORKFLOWS / "validate_catalog.py")


def ref(company, sid, st="transcript", date="2026-01-01", quote=None):
    return {"company": company, "source_type": st, "source_id": sid,
            "date": date, "quote": quote or f"quote {sid}"}


def mrec(name, refs):
    return {"driver_name": name, "canonical_name": name,
            "companies": sorted({r["company"] for r in refs}),
            "evidence_refs": refs, "same_as_variants": []}


def mixed_seed():
    """Leaf seed whose delivery_mix record mixes two meanings (AAA + BBB evidence)."""
    return {"industry": "TestInd", "catalog": [
        mrec("delivery_mix", [ref("AAA", "e1"), ref("BBB", "e2")]),
        mrec("other_metric", [ref("AAA", "e3")])], "analysis": {}}


SPLIT_TO = ("delivery_mix_channel", "delivery_mix_cost")
SPLIT_ASSIGN = [{"company": "AAA", "to": "delivery_mix_channel"},
                {"company": "BBB", "to": "delivery_mix_cost"}]


def split_review(frm="delivery_mix", to=SPLIT_TO, assignments=None):
    return {"reviews": [{"collision_name": frm, "verdict": "DIFFERENT",
                         "new_names": list(to), "why": "homonym"}],
            "split_map": [{"from": frm, "to": list(to),
                           "assignments": SPLIT_ASSIGN if assignments is None else assignments}]}


def unclear_review(frm="delivery_mix", why="mixed meanings"):
    return {"reviews": [{"collision_name": frm, "verdict": "UNCLEAR", "why": why}],
            "split_map": []}


def same_review(frm="delivery_mix", refute=True):
    rv = {"collision_name": frm, "verdict": "SAME", "why": "one meaning"}
    if refute:
        rv["refute_survived"] = True
    return {"reviews": [rv], "split_map": []}


def test_review_same_keeps_record_byte_identical():
    cat, _ = assemble(mixed_seed(), dec(), same_review())
    base, _ = assemble(mixed_seed(), dec())
    assert cat == base                            # SAME -> seed record kept as-is, no new key
    assert "unresolved_same_name" not in cat


def test_review_same_without_refute_survived_fails():
    with pytest.raises(SystemExit, match="refute_survived"):
        assemble(mixed_seed(), dec(), same_review(refute=False))


def test_review_collision_name_must_be_a_seed_name():
    with pytest.raises(SystemExit, match="seed"):
        assemble(mixed_seed(), dec(), same_review(frm="ghost_name"))


def test_review_different_replaces_record_with_split_records():
    cat, _ = assemble(mixed_seed(), dec(), split_review())
    assert names_of(cat) == ["delivery_mix_channel", "delivery_mix_cost", "other_metric"]
    ch, co = by_name(cat, "delivery_mix_channel"), by_name(cat, "delivery_mix_cost")
    assert ch["canonical_name"] == "delivery_mix_channel"          # coined, self-canonical
    assert [e["source_id"] for e in ch["evidence_refs"]] == ["e1"]
    assert [e["source_id"] for e in co["evidence_refs"]] == ["e2"]
    assert ch["companies"] == ["AAA"] and co["companies"] == ["BBB"]
    assert ch["same_as_variants"] == [] and co["same_as_variants"] == []
    assert "unresolved_same_name" not in cat                       # a split is not a park
    assert cat["counts"] == {"keep": 3, "same_as": 0, "rewrite": 0, "skip": 0, "unresolved": 0}


def test_review_split_evidence_ref_keys_within_company():
    seed = {"industry": "TestInd", "catalog": [
        mrec("delivery_mix", [ref("AAA", "e1"), ref("AAA", "e2"), ref("BBB", "e3")])],
        "analysis": {}}
    cat, _ = assemble(seed, dec(), split_review(assignments=[
        {"company": "AAA", "to": "delivery_mix_channel",
         "evidence_ref_keys": [["AAA", "transcript", "e1", "2026-01-01", "quote e1"]]},
        {"company": "AAA", "to": "delivery_mix_cost",
         "evidence_ref_keys": [["AAA", "transcript", "e2", "2026-01-01", "quote e2"]]},
        {"company": "BBB", "to": "delivery_mix_cost"}]))
    assert [e["source_id"] for e in by_name(cat, "delivery_mix_channel")["evidence_refs"]] == ["e1"]
    assert {e["source_id"] for e in by_name(cat, "delivery_mix_cost")["evidence_refs"]} == {"e2", "e3"}
    assert by_name(cat, "delivery_mix_cost")["companies"] == ["AAA", "BBB"]


def test_review_partition_ref_assigned_twice_fails():
    k1 = ["AAA", "transcript", "e1", "2026-01-01", "quote e1"]
    k2 = ["AAA", "transcript", "e2", "2026-01-01", "quote e2"]
    seed = {"industry": "TestInd", "catalog": [
        mrec("delivery_mix", [ref("AAA", "e1"), ref("AAA", "e2"), ref("BBB", "e3")])],
        "analysis": {}}
    with pytest.raises(SystemExit, match="twice|duplicat"):
        assemble(seed, dec(), split_review(assignments=[
            {"company": "AAA", "to": "delivery_mix_channel", "evidence_ref_keys": [k1, k2]},
            {"company": "AAA", "to": "delivery_mix_cost", "evidence_ref_keys": [k1]},  # e1 twice
            {"company": "BBB", "to": "delivery_mix_cost"}]))


def test_review_partition_lost_company_refs_fails():
    with pytest.raises(SystemExit, match="unassigned|lost"):
        assemble(mixed_seed(), dec(), split_review(assignments=[
            {"company": "AAA", "to": "delivery_mix_channel"}]))    # BBB refs never assigned


def test_review_split_target_not_lower_snake_fails():
    with pytest.raises(SystemExit, match="lower_snake"):
        assemble(mixed_seed(), dec(), split_review(
            to=("Delivery_Channel", "delivery_mix_cost"),
            assignments=[{"company": "AAA", "to": "Delivery_Channel"},
                         {"company": "BBB", "to": "delivery_mix_cost"}]))


def test_review_unclear_parks_one_occurrence_per_company():
    cat, _ = assemble(mixed_seed(), dec(), unclear_review())
    assert names_of(cat) == ["other_metric"]                       # parked name NOT a record
    assert cat["unresolved_same_name"] == [{
        "name": "delivery_mix",
        "occurrences": [{"company": "AAA", "evidence_refs": [ref("AAA", "e1")]},
                        {"company": "BBB", "evidence_refs": [ref("BBB", "e2")]}],
        "why": "mixed meanings"}]
    assert cat["counts"]["keep"] == 1


def test_review_decision_on_split_from_name_fails():
    with pytest.raises(SystemExit, match="review"):
        assemble(mixed_seed(),
                 dec(gate=[{"driver_name": "delivery_mix", "verdict": "skip", "reason": "vague"}]),
                 split_review())


def test_review_decision_on_parked_name_fails():
    with pytest.raises(SystemExit, match="review"):
        assemble(mixed_seed(),
                 dec(same_as=[{"variant": "delivery_mix", "canonical": "other_metric"}]),
                 unclear_review())


def test_review_decision_on_coined_split_target_fails():
    # the gate ran BEFORE the split, so a verdict on a coined target cannot exist honestly
    with pytest.raises(SystemExit, match="split target"):
        assemble(mixed_seed(),
                 dec(gate=[{"driver_name": "delivery_mix_channel", "verdict": "skip",
                            "reason": "r"}]),
                 split_review())


# ---------------------------------------------------------------- --review CLI + e2e validator

def write_run(tmp_path, seed, review=None):
    run = tmp_path / "run1"
    run.mkdir()
    (run / "seed.json").write_text(serialize(seed))
    # Stage-0 #3: every seed name needs a gate verdict UNLESS the same-name review covers it
    covered = {rv.get("collision_name") for rv in (review or {}).get("reviews", [])}
    gate = [{"driver_name": r["driver_name"], "verdict": "admit", "reason": "t"}
            for r in seed["catalog"] if r["driver_name"] not in covered]
    (run / "decisions.json").write_text(serialize(dec(gate=gate)))
    if review is not None:
        (run / "review.json").write_text(serialize(review))
    return run


def assemble_cli(run, *args):
    return subprocess.run([PY, CLI, str(run), *map(str, args)], capture_output=True, text=True)


def validate_cli(run, with_review=True):
    args = [PY, VALIDATOR, str(run / "seed.json"), str(run / "catalog.json"),
            str(run / "approved.json")]
    if with_review:
        args += ["--review", str(run / "review.json")]
    return subprocess.run(args, capture_output=True, text=True)


def test_cli_review_relative_and_absolute_paths(tmp_path):
    run = write_run(tmp_path, mixed_seed(), unclear_review())
    out = assemble_cli(run, "--review", "review.json")             # relative to run_dir
    assert out.returncode == 0, out.stderr
    assert "unresolved_same_name=1" in out.stdout
    rel_blob = (run / "catalog.json").read_bytes()
    assert b'"unresolved_same_name"' in rel_blob
    out2 = assemble_cli(run, "--review", run / "review.json")      # absolute path
    assert out2.returncode == 0, out2.stderr
    assert (run / "catalog.json").read_bytes() == rel_blob


def test_cli_review_without_parks_omits_side_list(tmp_path):
    run = write_run(tmp_path, mixed_seed(), split_review())
    out = assemble_cli(run, "--review", "review.json")
    assert out.returncode == 0, out.stderr
    assert "unresolved_same_name=0" in out.stdout                  # token present with --review
    assert "unresolved_same_name" not in json.loads((run / "catalog.json").read_text())


def test_cli_without_review_output_unchanged(tmp_path):
    # Phase-0 byte-identity: no --review -> no side-list key, no print token
    run = write_run(tmp_path, mixed_seed())
    out = assemble_cli(run)
    assert out.returncode == 0, out.stderr
    assert "unresolved_same_name" not in out.stdout
    assert "unresolved_same_name" not in json.loads((run / "catalog.json").read_text())


def test_e2e_leaf_different_split_validates_green(tmp_path):
    run = write_run(tmp_path, mixed_seed(), split_review())
    out = assemble_cli(run, "--review", "review.json")
    assert out.returncode == 0, out.stdout + out.stderr
    v = validate_cli(run)
    assert v.returncode == 0, v.stdout + v.stderr
    assert "VALIDATION PASSED" in v.stdout
    # without --review the coined targets + split-accounted from-name turn RED
    assert validate_cli(run, with_review=False).returncode == 1


def test_e2e_leaf_unclear_park_validates_green(tmp_path):
    run = write_run(tmp_path, mixed_seed(), unclear_review())
    out = assemble_cli(run, "--review", "review.json")
    assert out.returncode == 0, out.stdout + out.stderr
    v = validate_cli(run)
    assert v.returncode == 0, v.stdout + v.stderr
    assert "unresolved_same_name=1" in v.stdout


def test_review_split_ref_idx_within_company():
    # Index-based assignment (10th-pass D5 interface): idx = per-record refs sorted by key5.
    seed = {"industry": "TestInd", "catalog": [
        mrec("delivery_mix", [ref("AAA", "e1"), ref("AAA", "e2"), ref("BBB", "e3")])],
        "analysis": {}}
    # sorted by key5 -> r1=AAA/e1, r2=AAA/e2, r3=BBB/e3
    cat, _ = assemble(seed, dec(), split_review(assignments=[
        {"company": "AAA", "to": "delivery_mix_channel", "ref_idx": ["r1"]},
        {"company": "AAA", "to": "delivery_mix_cost", "ref_idx": ["r2"]},
        {"company": "BBB", "to": "delivery_mix_cost"}]))
    assert [e["source_id"] for e in by_name(cat, "delivery_mix_channel")["evidence_refs"]] == ["e1"]
    assert {e["source_id"] for e in by_name(cat, "delivery_mix_cost")["evidence_refs"]} == {"e2", "e3"}


def test_review_split_default_row_takes_remainder():
    # ONE default row per company = the unclaimed rest (legal now; deterministic, no duplication).
    seed = {"industry": "TestInd", "catalog": [
        mrec("delivery_mix", [ref("AAA", "e1"), ref("AAA", "e2"), ref("BBB", "e3")])],
        "analysis": {}}
    cat, _ = assemble(seed, dec(), split_review(assignments=[
        {"company": "AAA", "to": "delivery_mix_channel", "ref_idx": ["r1"]},
        {"company": "AAA", "to": "delivery_mix_cost"},          # remainder of AAA -> e2
        {"company": "BBB", "to": "delivery_mix_cost"}]))
    assert [e["source_id"] for e in by_name(cat, "delivery_mix_channel")["evidence_refs"]] == ["e1"]
    assert {e["source_id"] for e in by_name(cat, "delivery_mix_cost")["evidence_refs"]} == {"e2", "e3"}


def test_review_split_two_default_rows_same_company_fails():
    # The exact live failure shape: two no-key rows for one company = ambiguous -> hard-fail.
    with pytest.raises(SystemExit, match="default rows"):
        assemble(mixed_seed(), dec(), split_review(assignments=[
            {"company": "AAA", "to": "delivery_mix_channel"},
            {"company": "AAA", "to": "delivery_mix_cost"},
            {"company": "BBB", "to": "delivery_mix_cost"}]))


def test_review_split_unknown_or_foreign_ref_idx_fails():
    with pytest.raises(SystemExit, match="ref_idx"):
        assemble(mixed_seed(), dec(), split_review(assignments=[
            {"company": "AAA", "to": "delivery_mix_channel", "ref_idx": ["r99"]},
            {"company": "BBB", "to": "delivery_mix_cost"}]))
    with pytest.raises(SystemExit, match="belongs to company"):
        assemble(mixed_seed(), dec(), split_review(assignments=[
            {"company": "AAA", "to": "delivery_mix_channel", "ref_idx": ["r2"]},  # r2 is BBB's
            {"company": "BBB", "to": "delivery_mix_cost"}]))


def test_chain_flattens_to_star():
    # a -SAME_AS-> b, b -rewrite-> c  =>  all canonical_name = c (transitive closure of
    # Refute-approved links is bookkeeping, not judgment; leaf contract = STAR).
    cat, _ = assemble(seed_of("name_a", "name_b", "name_c"),
                      dec(gate=[{"driver_name": "name_b", "verdict": "rewrite",
                                 "rewrite_to": "name_c", "reason": "wording"}],
                          same_as=[{"variant": "name_a", "canonical": "name_b"}],
                          rewrites=[{"from": "name_b", "to": "name_c"}]))
    assert by_name(cat, "name_a")["canonical_name"] == "name_c"
    assert by_name(cat, "name_b")["canonical_name"] == "name_c"
    assert by_name(cat, "name_c")["canonical_name"] == "name_c"
    assert by_name(cat, "name_c")["same_as_variants"] == ["name_a", "name_b"]


def test_cycle_resolves_to_shortest_then_lex_root():
    # sales <-> revenue mutual SAME_AS: deterministic root = shortest name, then lexicographic.
    cat, _ = assemble(seed_of("sales", "revenue"),
                      dec(same_as=[{"variant": "sales", "canonical": "revenue"},
                                   {"variant": "revenue", "canonical": "sales"}]))
    assert by_name(cat, "sales")["canonical_name"] == "sales"
    assert by_name(cat, "revenue")["canonical_name"] == "sales"
    assert by_name(cat, "sales")["same_as_variants"] == ["revenue"]


def test_chain_stops_at_last_kept_name():
    # a -> b (kept), b -> c but c is SKIPPED: a folds to b; b stays self-canonical. Star holds.
    cat, _ = assemble(seed_of("name_a", "name_b", "name_c"),
                      dec(gate=[{"driver_name": "name_c", "verdict": "skip", "reason": "vague"}],
                          same_as=[{"variant": "name_a", "canonical": "name_b"},
                                   {"variant": "name_b", "canonical": "name_c"}]))
    assert by_name(cat, "name_a")["canonical_name"] == "name_b"
    assert by_name(cat, "name_b")["canonical_name"] == "name_b"
    assert [s["driver_name"] for s in cat["skips"]] == ["name_c"]
