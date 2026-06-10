"""TDD for validate_catalog.py FOLD MODE (HierarchicalCatalogPlan D8/§11.2/§11.3/§11.9).

Fixtures are the REAL pipeline: fold_catalogs part-a/part-b build the parent seed,
assemble_catalog.py (empty decisions) writes the parent catalog, then the validator runs
with --fold <child catalogs> [--review] [--sidecars]. Each D8 check is then proven to
fire on a targeted corruption (zero judgment — names/sets/partitions only).
"""
import json
import subprocess
import sys
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOWS))

from fold_catalogs import part_a, part_b, serialize  # noqa: E402

PY = sys.executable
VALIDATOR = str(WORKFLOWS / "validate_catalog.py")
EMPTY_DECISIONS = {"gate_verdicts": [], "approved_same_as": [],
                   "approved_rewrites": [], "parked_rewrites": []}


def ref(company="AAA", sid="e1", quote=None):
    return {"company": company, "source_type": "transcript", "source_id": sid,
            "date": "2026-01-01", "quote": quote if quote is not None else f"quote {sid}"}


def rec(name, refs):
    return {"driver_name": name, "canonical_name": name,
            "companies": sorted({r["company"] for r in refs}), "evidence_refs": refs,
            "same_as_variants": [],
            "optional_links": {"xbrl_concept": None, "xbrl_member": None, "guidance_ref": None}}


def child(tmp, run_id, recs):
    d = tmp / run_id
    d.mkdir(exist_ok=True)
    (d / "catalog.json").write_text(serialize(
        {"industry": f"Ind_{run_id}", "catalog": recs, "skips": [],
         "unresolved_rewrites": [], "unresolved_same_name": []}))
    return d


def build_fold(tmp, recs1, recs2, review):
    """Real pipeline: part-a -> part-b -> assemble_catalog.py (empty decisions)."""
    c1, c2 = child(tmp, "childA", recs1), child(tmp, "childB", recs2)
    p = tmp / "parent_run"
    p.mkdir(exist_ok=True)
    part_a(p, "TestSector", "sector", [c1, c2])
    part_b(p, review)
    (p / "decisions.json").write_text(json.dumps(EMPTY_DECISIONS))
    out = subprocess.run([PY, str(WORKFLOWS / "assemble_catalog.py"), str(p)],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    rv = tmp / "review.json"
    rv.write_text(serialize(review))
    return p, c1, c2, rv


def validate(p, children, approved=True, review=None, sidecars=None):
    args = [PY, VALIDATOR, str(p / "seed.json"), str(p / "catalog.json")]
    if approved:
        args.append(str(p / "approved.json"))
    args += ["--fold", *(str(c / "catalog.json") for c in children)]
    if review is not None:
        args += ["--review", str(review)]
    if sidecars is not None:
        args += ["--sidecars", str(sidecars)]
    return subprocess.run(args, capture_output=True, text=True)


def edit(path, fn):
    obj = json.loads(path.read_text())
    fn(obj)
    path.write_text(serialize(obj))


SAME_REVIEW = {"reviews": [{"collision_name": "guest_count", "verdict": "SAME",
                            "refute_survived": True, "why": "same metric"}], "split_map": []}


def same_fixture(tmp):
    return build_fold(
        tmp,
        [rec("guest_count", [ref("AAA", "e1")]), rec("store_traffic", [ref("AAA", "e2")])],
        [rec("guest_count", [ref("BBB", "e3")]), rec("wing_costs", [ref("BBB", "e4")])],
        SAME_REVIEW)


SPLIT_REVIEW = {
    "reviews": [{"collision_name": "fleet_size", "verdict": "DIFFERENT",
                 "new_names": ["fleet_size_capacity", "fleet_size_cost"], "why": "homonym"}],
    "split_map": [{"from": "fleet_size", "to": ["fleet_size_capacity", "fleet_size_cost"],
                   "assignments": [{"child_run_id": "childA", "to": "fleet_size_capacity"},
                                   {"child_run_id": "childB", "to": "fleet_size_cost"}]}]}


def split_fixture(tmp):
    return build_fold(tmp,
                      [rec("fleet_size", [ref("AAA", "e1")])],
                      [rec("fleet_size", [ref("BBB", "e2")])],
                      SPLIT_REVIEW)


# ---------------------------------------------------------------- GREEN folds

def test_green_same_fold_validates(tmp_path):
    p, c1, c2, rv = same_fixture(tmp_path)
    out = validate(p, [c1, c2], review=rv, sidecars=p / "fold_sidecars.json")
    assert out.returncode == 0, out.stdout + out.stderr
    assert "VALIDATION PASSED" in out.stdout


def test_green_different_split_validates(tmp_path):
    p, c1, c2, rv = split_fixture(tmp_path)
    out = validate(p, [c1, c2], review=rv, sidecars=p / "fold_sidecars.json")
    assert out.returncode == 0, out.stdout + out.stderr
    assert "VALIDATION PASSED" in out.stdout


def test_green_unclear_park_validates_with_sidecars(tmp_path):
    review = {"reviews": [{"collision_name": "guest_count", "verdict": "UNCLEAR",
                           "why": "mixed"}], "split_map": []}
    p, c1, c2, rv = build_fold(
        tmp_path,
        [rec("guest_count", [ref("AAA", "e1")]), rec("store_traffic", [ref("AAA", "e2")])],
        [rec("guest_count", [ref("BBB", "e3")])],
        review)
    out = validate(p, [c1, c2], review=rv, sidecars=p / "fold_sidecars.json")
    assert out.returncode == 0, out.stdout + out.stderr
    # without --sidecars the parked name is unaccounted -> D8 NAMES must fire
    out = validate(p, [c1, c2], review=rv)
    assert out.returncode == 1
    assert "D8 NAMES" in out.stdout


# ---------------------------------------------------------------- D8 corruptions

def test_d8_names_fails_on_dropped_child_name(tmp_path):
    p, c1, c2, rv = same_fixture(tmp_path)
    # a child name the fold never saw (added AFTER part-a ran) -> unaccounted
    edit(c2 / "catalog.json",
         lambda cat: cat["catalog"].append(rec("ghost_metric", [ref("BBB", "e9")])))
    out = validate(p, [c1, c2], review=rv, sidecars=p / "fold_sidecars.json")
    assert out.returncode == 1
    assert "D8 NAMES" in out.stdout and "ghost_metric" in out.stdout


def test_d8_evidence_fails_on_mutated_parent_evidence(tmp_path):
    p, c1, c2, rv = same_fixture(tmp_path)

    def mutate(obj):  # same mutation in seed AND catalog so EVIDENCE-drift stays quiet
        for r in obj["catalog"]:
            if r["driver_name"] == "store_traffic":
                r["evidence_refs"][0]["quote"] = "TAMPERED"
    edit(p / "seed.json", mutate)
    edit(p / "catalog.json", mutate)
    out = validate(p, [c1, c2], review=rv, sidecars=p / "fold_sidecars.json")
    assert out.returncode == 1
    assert "D8 EVIDENCE" in out.stdout and "store_traffic" in out.stdout


def test_d8_partition_fails_on_overlapping_split(tmp_path):
    p, c1, c2, rv = split_fixture(tmp_path)
    stolen = ref("BBB", "e2")  # childB's ref, legitimately assigned to fleet_size_cost

    def mutate(obj):  # add it to fleet_size_capacity too -> split sets overlap
        for r in obj["catalog"]:
            if r["driver_name"] == "fleet_size_capacity":
                r["evidence_refs"].append(stolen)
                r["companies"] = ["AAA", "BBB"]
    edit(p / "seed.json", mutate)
    edit(p / "catalog.json", mutate)
    out = validate(p, [c1, c2], review=rv, sidecars=p / "fold_sidecars.json")
    assert out.returncode == 1
    assert "D8 PARTITION" in out.stdout


def test_d8_variants_fails_on_invented_variant(tmp_path):
    p, c1, c2, rv = same_fixture(tmp_path)
    # no approved.json (mirror check skipped) so the D8 VARIANTS check itself must fire
    edit(p / "catalog.json",
         lambda obj: obj["catalog"][0].__setitem__("same_as_variants", ["invented_variant"]))
    out = validate(p, [c1, c2], approved=False, review=rv, sidecars=p / "fold_sidecars.json")
    assert out.returncode == 1
    assert "D8 VARIANTS" in out.stdout and "invented_variant" in out.stdout


# ---------------------------------------------------------------- §11.3 relaxations

def test_provenance_accepts_split_targets(tmp_path):
    p, c1, c2, rv = split_fixture(tmp_path)
    # simulate a leaf-style D5 split: target record present in catalog but NOT in the seed
    edit(p / "seed.json", lambda obj: obj.__setitem__(
        "catalog", [r for r in obj["catalog"] if r["driver_name"] != "fleet_size_capacity"]))
    out = validate(p, [c1, c2], review=rv, sidecars=p / "fold_sidecars.json")
    assert out.returncode == 0, out.stdout + out.stderr
    # without --review the split-map is unknown -> the target is an invented name again
    out = validate(p, [c1, c2], sidecars=p / "fold_sidecars.json")
    assert out.returncode == 1
    assert "PROVENANCE" in out.stdout


def test_scope_seed_without_industry_passes(tmp_path):
    p, c1, c2, rv = same_fixture(tmp_path)
    seed = json.loads((p / "seed.json").read_text())
    assert "industry" not in seed and seed["scope_level"] == "sector"  # §11.8 shape
    out = validate(p, [c1, c2], review=rv, sidecars=p / "fold_sidecars.json")
    assert out.returncode == 0, out.stdout + out.stderr


def test_park_with_empty_evidence_fails_side_fields(tmp_path):
    review = {"reviews": [{"collision_name": "guest_count", "verdict": "UNCLEAR",
                           "why": "mixed"}], "split_map": []}
    p, c1, c2, rv = build_fold(
        tmp_path,
        [rec("guest_count", [ref("AAA", "e1")]), rec("store_traffic", [ref("AAA", "e2")])],
        [rec("guest_count", [ref("BBB", "e3")])],
        review)
    edit(p / "fold_sidecars.json", lambda sc: sc["unresolved_same_name"][0]
         ["occurrences"][0].__setitem__("evidence_refs", []))
    out = validate(p, [c1, c2], review=rv, sidecars=p / "fold_sidecars.json")
    assert out.returncode == 1
    assert "unresolved_same_name" in out.stdout


def test_d8_variants_accepts_deeper_level_carried_variant(tmp_path):
    # 3+ level folds: a SECTOR child record carries leaf-fold variants in its OWN
    # same_as_variants. The GLOBAL parent carries them forward — they exist in NO child
    # as a record name, only as a child variant NAME. D8 VARIANTS must accept them
    # (legit = child record names ∪ child variant names ∪ split targets).
    r1 = rec("same_store_sales", [ref("AAA", "e1")])
    r1["same_as_variants"] = ["comparable_sales"]          # carried from the leaf fold
    p, c1, c2, _ = build_fold(
        tmp_path,
        [r1, rec("oil_price", [ref("AAA", "e2")])],
        [rec("wage_inflation", [ref("BBB", "e3")])],
        {"reviews": [], "split_map": []})
    out = validate(p, [c1, c2])
    assert out.returncode == 0, out.stdout + out.stderr
