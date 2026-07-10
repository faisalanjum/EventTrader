"""TDD for validate_catalog.py Phase-0 changes (HierarchicalCatalogPlan D1/§3a/§3e):
- optional 3rd arg approved.json -> D1 fusion-approval check + same_as_variants mirror check
- stale _menu_restaurants_* defaults removed (usage error without explicit args)
- legacy 2-arg mode still validates (D1 skipped with a WARN)
Fixtures are generated through assemble_catalog.assemble() so they match the real writer.
"""
import json
import subprocess
import sys
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOWS))

from assemble_catalog import assemble, serialize  # noqa: E402

PY = sys.executable
VALIDATOR = str(WORKFLOWS / "validate_catalog.py")


def rec(name, company="AAA"):
    return {
        "driver_name": name,
        "canonical_name": name,
        "companies": [company],
        "evidence_refs": [{
            "company": company, "source_type": "transcript",
            "source_id": f"ev_{name}", "date": "2026-01-01", "quote": f"quote about {name}",
        }],
    }


def write_run(tmp_path, same_as=None, mutate=None):
    seed = {"industry": "TestInd", "catalog": [rec("guest_count"), rec("customer_transactions")],
            "analysis": {}}
    decisions = {"gate_verdicts": [], "approved_same_as": same_as or [],
                 "approved_rewrites": [], "parked_rewrites": []}
    cat, approved = assemble(seed, decisions)
    if mutate:
        mutate(cat, approved)
    (tmp_path / "seed.json").write_text(serialize(seed))
    (tmp_path / "catalog.json").write_text(serialize(cat))
    (tmp_path / "approved.json").write_text(serialize(approved))
    return tmp_path


def run_validator(tmp_path, with_approved=True, extra_args=()):
    args = [PY, VALIDATOR, str(tmp_path / "seed.json"), str(tmp_path / "catalog.json")]
    if with_approved:
        args.append(str(tmp_path / "approved.json"))
    args.extend(extra_args)
    return subprocess.run(args, capture_output=True, text=True)


def test_happy_path_with_approved_passes(tmp_path):
    write_run(tmp_path, same_as=[{"variant": "customer_transactions", "canonical": "guest_count"}])
    out = run_validator(tmp_path)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "VALIDATION PASSED" in out.stdout


def test_unapproved_fusion_fails_d1(tmp_path):
    # catalog folds customer_transactions -> guest_count, but approved.json has NO such link
    def mutate(cat, approved):
        approved["same_as"] = []
    write_run(tmp_path, same_as=[{"variant": "customer_transactions", "canonical": "guest_count"}],
              mutate=mutate)
    out = run_validator(tmp_path)
    assert out.returncode == 1
    assert "D1" in out.stdout


def test_variants_mirror_mismatch_fails(tmp_path):
    # record claims a same_as_variant that no fold produced
    def mutate(cat, approved):
        for r in cat["catalog"]:
            if r["driver_name"] == "guest_count":
                r["same_as_variants"] = ["customer_transactions"]
    write_run(tmp_path, mutate=mutate)
    out = run_validator(tmp_path)
    assert out.returncode == 1
    assert "SAME_AS_VARIANTS" in out.stdout


def test_legacy_two_arg_mode_passes_with_warn(tmp_path):
    write_run(tmp_path, same_as=[{"variant": "customer_transactions", "canonical": "guest_count"}])
    out = run_validator(tmp_path, with_approved=False)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "SKIPPED" in out.stderr  # WARN that D1/variants checks were skipped


def test_no_args_is_usage_error_not_stale_defaults():
    out = subprocess.run([PY, VALIDATOR], capture_output=True, text=True)
    assert out.returncode == 2
    assert "Usage" in out.stderr


def test_carried_seed_variants_pass_mirror(tmp_path):
    # Parent-seed records carrying child variants must validate (mirror = carried ∪ folded).
    seed = {"industry": "TestInd", "catalog": [rec("guest_count"), rec("customer_transactions")],
            "analysis": {}}
    seed["catalog"][0]["same_as_variants"] = ["child_variant_x"]
    from assemble_catalog import assemble as _asm
    cat, approved = _asm(seed, {"gate_verdicts": [], "approved_same_as": [], "approved_rewrites": [],
                                "parked_rewrites": []})
    (tmp_path / "seed.json").write_text(serialize(seed))
    (tmp_path / "catalog.json").write_text(serialize(cat))
    (tmp_path / "approved.json").write_text(serialize(approved))
    out = run_validator(tmp_path)
    assert out.returncode == 0, out.stdout + out.stderr


def test_d1_accepts_transitive_chain_flattened_canonicals(tmp_path):
    # a -SAME_AS-> b, b -rewrite-> c: assembler flattens a's canonical to c (STAR);
    # D1 must accept a->c because it is REACHABLE via the approved links.
    from assemble_catalog import assemble as _asm
    seed = {"industry": "TestInd", "catalog": [rec("name_a"), rec("name_b"), rec("name_c")],
            "analysis": {}}
    cat, approved = _asm(seed, {
        "gate_verdicts": [{"driver_name": "name_b", "verdict": "rewrite",
                           "rewrite_to": "name_c", "reason": "wording"}],
        "approved_same_as": [{"variant": "name_a", "canonical": "name_b"}],
        "approved_rewrites": [{"from": "name_b", "to": "name_c"}],
        "parked_rewrites": []})
    assert next(r for r in cat["catalog"] if r["driver_name"] == "name_a")["canonical_name"] == "name_c"
    (tmp_path / "seed.json").write_text(serialize(seed))
    (tmp_path / "catalog.json").write_text(serialize(cat))
    (tmp_path / "approved.json").write_text(serialize(approved))
    out = run_validator(tmp_path)
    assert out.returncode == 0, out.stdout + out.stderr
    # and a NOT-reachable fusion still fails D1
    cat["catalog"][2]["canonical_name"] = "name_a"  # c -> a was never approved (wrong direction)
    cat["catalog"][2]["same_as_variants"] = []
    (tmp_path / "catalog.json").write_text(serialize(cat))
    out = run_validator(tmp_path)
    assert out.returncode == 1 and "D1" in out.stdout


def mrec_multi(name, companies):
    refs = [{"company": c, "source_type": "transcript", "source_id": f"ev_{name}_{c}",
             "date": "2026-01-01", "quote": f"quote about {name} at {c}"} for c in companies]
    return {"driver_name": name, "canonical_name": name, "companies": sorted(companies),
            "evidence_refs": refs}


def test_high_blast_fusion_requires_recorded_second_skeptic(tmp_path):
    # 12th pass rev2: code-computed backstop — an approved fusion spanning >= 8 companies MUST carry
    # a surviving high_blast_refute2 verdict in approved.json, else VALIDATION FAILED (the trigger
    # relay inside the workflow is an optimization; THIS is the deterministic enforcement).
    from assemble_catalog import assemble as _asm
    big = [f"C{i}" for i in range(8)]
    seed = {"industry": "TestInd",
            "catalog": [mrec_multi("same_store_sales", big), mrec_multi("comparable_sales", ["C0"])],
            "analysis": {}}
    dec = {"gate_verdicts": [], "approved_same_as": [{"variant": "comparable_sales", "canonical": "same_store_sales"}],
           "approved_rewrites": [], "parked_rewrites": []}
    cat, approved = _asm(seed, dec)
    (tmp_path / "seed.json").write_text(serialize(seed))
    (tmp_path / "catalog.json").write_text(serialize(cat))
    (tmp_path / "approved.json").write_text(serialize(approved))
    out = run_validator(tmp_path)                                   # no recorded 2nd skeptic -> FAIL
    assert out.returncode == 1 and "HIGH-BLAST" in out.stdout
    approved["high_blast_refute2"] = [{"kind": "link", "a": "same_store_sales", "b": "comparable_sales",
                                       "n": 8, "survives": True}]
    (tmp_path / "approved.json").write_text(serialize(approved))
    out = run_validator(tmp_path)                                   # recorded + survived -> PASS
    assert out.returncode == 0, out.stdout + out.stderr
    approved["high_blast_refute2"][0]["survives"] = False           # recorded but refuted -> FAIL
    (tmp_path / "approved.json").write_text(serialize(approved))
    assert run_validator(tmp_path).returncode == 1


def test_small_fusion_needs_no_second_skeptic(tmp_path):
    from assemble_catalog import assemble as _asm
    seed = {"industry": "TestInd", "catalog": [mrec_multi("guest_count", ["AAA", "BBB"]),
                                               mrec_multi("customer_transactions", ["AAA"])], "analysis": {}}
    dec = {"gate_verdicts": [], "approved_same_as": [{"variant": "customer_transactions", "canonical": "guest_count"}],
           "approved_rewrites": [], "parked_rewrites": []}
    cat, approved = _asm(seed, dec)
    (tmp_path / "seed.json").write_text(serialize(seed))
    (tmp_path / "catalog.json").write_text(serialize(cat))
    (tmp_path / "approved.json").write_text(serialize(approved))
    out = run_validator(tmp_path)
    assert out.returncode == 0, out.stdout + out.stderr             # 2 companies: no backstop demand
