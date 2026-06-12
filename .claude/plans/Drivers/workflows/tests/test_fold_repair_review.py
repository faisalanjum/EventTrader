"""Fold-parent review handling at repair re-assembly (bug-#2 fix, 2026-06-12).

On a FOLD parent, same_name_review.json is the FOLD-shaped review that fold part-b
already consumed to BUILD the parent seed (DIFFERENT names replaced by split targets,
UNCLEAR names parked to fold_sidecars.json). Re-applying it at repair-apply fed fold
collision_names to the leaf apply_review, which hard-fails ("collision_name ... is not
a seed record name") on any DIFFERENT/UNCLEAR row — empirically reproduced on a copy of
runs/2026-06-10_135310_sector_synthsector. Fix: apply() passes review=None when
fold_manifest.json exists; assemble_catalog.py's CLI hard-blocks --review on fold
parents (the reconcile leaf-D5 overwrite hazard). Leaf behavior is byte-unchanged.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

WORKFLOWS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOWS))

from assemble_catalog import assemble, serialize  # noqa: E402
from repair_duplicates import apply  # noqa: E402


def ref(company="AAA", sid="e1", quote=None):
    return {"company": company, "source_type": "transcript", "source_id": sid,
            "date": "2026-01-01", "quote": quote or f"quote {sid}"}


def rec(name, companies=("AAA",)):
    return {"driver_name": name, "canonical_name": name, "companies": sorted(companies),
            "evidence_refs": [ref(company=c, sid=f"{name}_{c}") for c in sorted(companies)],
            "same_as_variants": [],
            "optional_links": {"xbrl_concept": None, "xbrl_member": None, "guidance_ref": None}}


FOLD_REVIEW = {
    # delivery_mix and traffic are ABSENT from the seed below — exactly the part-b
    # invariant (DIFFERENT -> replaced by split targets; UNCLEAR -> parked to sidecars).
    "reviews": [
        {"collision_name": "delivery_mix", "verdict": "DIFFERENT",
         "new_names": ["restaurant_delivery_channel_mix", "parcel_delivery_mix"], "why": "homonym"},
        {"collision_name": "traffic", "verdict": "UNCLEAR", "why": "vague"},
        {"collision_name": "oil_price", "verdict": "SAME", "why": "same input cost",
         "refute_survived": True},
    ],
    "split_map": [
        {"from": "delivery_mix",
         "to": ["restaurant_delivery_channel_mix", "parcel_delivery_mix"],
         "assignments": [{"child_run_id": "childA", "to": "restaurant_delivery_channel_mix"},
                         {"child_run_id": "childB", "to": "parcel_delivery_mix"}]},
    ],
}


def make_fold_parent(tmp_path, name, with_review=True):
    """A fold-parent run dir as part-b + reconcile leave it (review baked into the seed)."""
    run = tmp_path / name
    run.mkdir()
    records = [rec("restaurant_delivery_channel_mix", ("AAA",)),
               rec("parcel_delivery_mix", ("BBB", "CCC")),
               rec("oil_price", ("AAA", "BBB")),
               rec("same_store_sales", ("AAA",))]
    seed = {"scope_name": "SynthSector", "scope_level": "sector",
            "catalog": records, "analysis": {}}
    dec = {"gate_verdicts": [], "approved_same_as": [], "approved_rewrites": [],
           "parked_rewrites": []}
    (run / "seed.json").write_text(serialize(seed))
    (run / "decisions.json").write_text(serialize(dec))
    out, approved = assemble(seed, dec, None)
    (run / "catalog.json").write_text(serialize(out))
    (run / "approved.json").write_text(serialize(approved))
    (run / "fold_manifest.json").write_text(json.dumps(
        {"scope_name": "SynthSector", "scope_level": "sector", "children": []}))
    if with_review:
        (run / "same_name_review.json").write_text(json.dumps(FOLD_REVIEW))
    (run / "repair_candidates.json").write_text(json.dumps(
        {"count": 1, "clipped": 0,
         "candidates": [{"a": "parcel_delivery_mix", "b": "restaurant_delivery_channel_mix"}]}))
    (run / "repair_review.json").write_text(json.dumps(
        {"reviews": [{"a": "parcel_delivery_mix", "b": "restaurant_delivery_channel_mix",
                      "verdict": "SAME", "why": "same mechanism"}]}))
    return run


def test_fold_parent_apply_ignores_fold_review(tmp_path):
    """THE bug-#2 regression: apply() on a fold parent must succeed with the fold-shaped
    review present (>=1 DIFFERENT + >=1 UNCLEAR row), and produce byte-identical output
    to a twin run without the review file."""
    run_a = make_fold_parent(tmp_path, "with_review", with_review=True)
    run_b = make_fold_parent(tmp_path, "without_review", with_review=False)
    out_a = apply(str(run_a), str(run_a / "repair_review.json"))
    out_b = apply(str(run_b), str(run_b / "repair_review.json"))
    assert out_a["added"] == 1 and out_b["added"] == 1
    assert out_a["catalog_sha256"] == out_b["catalog_sha256"]
    assert (run_a / "catalog.json").read_bytes() == (run_b / "catalog.json").read_bytes()
    assert (run_a / "approved.json").read_bytes() == (run_b / "approved.json").read_bytes()
    # the fix must IGNORE the review, never delete it — the D8 fold gates still read it
    assert (run_a / "same_name_review.json").exists()
    assert json.loads((run_a / "same_name_review.json").read_text()) == FOLD_REVIEW


def test_leaf_apply_still_applies_leaf_review(tmp_path):
    """Leaf behavior byte-unchanged: without fold_manifest.json, a leaf-D5 review is
    still applied at re-assembly (UNCLEAR row parks its seed record)."""
    run = make_fold_parent(tmp_path, "leaf", with_review=False)
    (run / "fold_manifest.json").unlink()
    (run / "same_name_review.json").write_text(json.dumps(
        {"reviews": [{"collision_name": "oil_price", "verdict": "UNCLEAR", "why": "mixed"}],
         "split_map": []}))
    out = apply(str(run), str(run / "repair_review.json"))
    assert out["added"] == 1
    cat = json.loads((run / "catalog.json").read_text())
    parked = [p["name"] for p in cat.get("unresolved_same_name") or []]
    assert parked == ["oil_price"]          # review WAS applied
    assert all(r["driver_name"] != "oil_price" for r in cat["catalog"])


def test_assemble_cli_blocks_review_on_fold_parent(tmp_path):
    """Fail-close guard: assemble_catalog.py CLI must refuse --review on a dir holding
    fold_manifest.json (the reconcile leaf-D5 overwrite hazard) — and still accept it
    on a leaf."""
    run = make_fold_parent(tmp_path, "guard", with_review=False)
    (run / "same_name_review.json").write_text(json.dumps(
        {"reviews": [{"collision_name": "oil_price", "verdict": "UNCLEAR", "why": "mixed"}],
         "split_map": []}))
    # gate verdicts for every name EXCEPT the D5-routed one: on UNPATCHED code this CLI
    # call exits 0 (review silently applied on a fold parent — the hazard); the guard
    # must flip it to a hard fail, so the EXIT CODE itself discriminates the fix
    seed = json.loads((run / "seed.json").read_text())
    dec = json.loads((run / "decisions.json").read_text())
    dec["gate_verdicts"] = [{"driver_name": r["driver_name"], "verdict": "admit"}
                            for r in seed["catalog"] if r["driver_name"] != "oil_price"]
    (run / "decisions.json").write_text(serialize(dec))
    cmd = [sys.executable, str(WORKFLOWS / "assemble_catalog.py"), str(run),
           "--review", "same_name_review.json"]
    proc = subprocess.run(cmd, capture_output=True)
    assert proc.returncode != 0
    assert b"FOLD parent" in proc.stderr
    # control: same CLI on a leaf (no fold_manifest.json) passes the guard; gate verdicts
    # for every seed name EXCEPT the D5-routed one (the real flow filters those out, and
    # the assembler rejects decisions referencing a review-parked name)
    (run / "fold_manifest.json").unlink()
    seed = json.loads((run / "seed.json").read_text())
    dec = json.loads((run / "decisions.json").read_text())
    dec["gate_verdicts"] = [{"driver_name": r["driver_name"], "verdict": "admit"}
                            for r in seed["catalog"] if r["driver_name"] != "oil_price"]
    (run / "decisions.json").write_text(serialize(dec))
    proc2 = subprocess.run(cmd, capture_output=True)
    assert proc2.returncode == 0, proc2.stderr.decode()[:500]
