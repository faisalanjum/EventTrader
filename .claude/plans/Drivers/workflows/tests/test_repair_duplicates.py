import json
import os
import sys
from pathlib import Path

import pytest

WORKFLOWS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOWS))

from assemble_catalog import assemble, serialize  # noqa: E402
from repair_duplicates import apply, embedding_pairs_from_vectors, suggest  # noqa: E402


def ref(company="AAA", sid="e1", quote=None):
    return {"company": company, "source_type": "transcript", "source_id": sid,
            "date": "2026-01-01", "quote": quote or f"quote {sid}"}


def rec(name, companies=("AAA",), refs=None):
    refs = refs or [ref(company=c, sid=f"{name}_{c}") for c in companies]
    return {"driver_name": name, "canonical_name": name, "companies": sorted(companies),
            "evidence_refs": refs,
            "same_as_variants": [],
            "optional_links": {"xbrl_concept": None, "xbrl_member": None, "guidance_ref": None}}


def cands(run, *pairs):
    """Stage-0 #7 fixture: apply() only adds links present in the suggested set on disk."""
    (run / "repair_candidates.json").write_text(json.dumps(
        {"count": len(pairs), "clipped": 0,
         "candidates": [{"a": a, "b": b} for a, b in pairs]}))


def make_run(tmp_path, records):
    run = tmp_path / "run"
    run.mkdir()
    seed = {"industry": "Test", "catalog": records, "analysis": {}}
    dec = {"gate_verdicts": [], "approved_same_as": [], "approved_rewrites": [],
           "parked_rewrites": []}
    cat, approved = assemble(seed, dec)
    (run / "seed.json").write_text(serialize(seed))
    (run / "decisions.json").write_text(serialize(dec))
    (run / "catalog.json").write_text(serialize(cat))
    (run / "approved.json").write_text(serialize(approved))
    return run


def test_suggest_token_overlap_writes_candidate_views(tmp_path):
    run = make_run(tmp_path, [
        rec("guest_count_growth"),
        rec("guest_transactions_growth"),
        rec("wage_inflation"),
    ])
    out = suggest(run, min_token_overlap=2)
    assert out["count"] == 1
    c = out["candidates"][0]
    assert {c["a"], c["b"]} == {"guest_count_growth", "guest_transactions_growth"}
    assert c["reason"].startswith("token_overlap:")
    assert len(c["sides"]) == 2 and all(s["evidence_refs"] for s in c["sides"])
    assert json.loads((run / "repair_candidates.json").read_text())["count"] == 1


def test_embedding_pairs_from_vectors_suggests_semantic_neighbor_without_deciding():
    records = [
        rec("guest_count"),
        rec("customer_transactions"),
        rec("wage_inflation"),
    ]
    pairs = embedding_pairs_from_vectors(records, [
        [1.0, 0.0, 0.0],
        [0.99, 0.01, 0.0],
        [0.0, 1.0, 0.0],
    ], top_k=1, min_score=0.90)
    assert set(pairs) == {("customer_transactions", "guest_count")}
    assert pairs[("customer_transactions", "guest_count")].startswith("embedding:")


def test_apply_approved_same_pair_reassembles_catalog(tmp_path):
    run = make_run(tmp_path, [
        rec("guest_count_growth"),
        rec("guest_transactions_growth"),
    ])
    cands(run, ("guest_count_growth", "guest_transactions_growth"))
    review = {"reviews": [{"a": "guest_count_growth", "b": "guest_transactions_growth",
                           "verdict": "SAME", "why": "same exact meaning"}]}
    rp = run / "repair_review.json"
    rp.write_text(serialize(review))
    out = apply(run, rp)
    assert out["added"] == 1
    cat = json.loads((run / "catalog.json").read_text())
    approved = json.loads((run / "approved.json").read_text())
    assert approved["same_as"]
    rolled = [r for r in cat["catalog"] if r["canonical_name"] != r["driver_name"]]
    assert len(rolled) == 1


def test_apply_high_blast_requires_second_skeptic_proof(tmp_path):
    eight = tuple(f"C{i}" for i in range(8))
    run = make_run(tmp_path, [
        rec("same_store_sales", companies=eight),
        rec("comparable_sales", companies=("C0",)),
    ])
    cands(run, ("same_store_sales", "comparable_sales"))
    review = {"reviews": [{"a": "same_store_sales", "b": "comparable_sales",
                           "verdict": "SAME", "why": "same exact meaning"}]}
    rp = run / "repair_review.json"
    rp.write_text(serialize(review))
    with pytest.raises(SystemExit, match="high-blast"):
        apply(run, rp)
    review["reviews"][0]["high_blast_refute2_survived"] = True
    rp.write_text(serialize(review))
    out = apply(run, rp)
    assert out["added"] == 1
    approved = json.loads((run / "approved.json").read_text())
    assert approved["high_blast_refute2"][0]["survives"] is True


# ---- ported from the consolidated parallel build (owner: keep repair_duplicates as the one
# source of truth; graft rare-token + clip reporting + strongest tests) ----

def test_rare_token_lane_pairs_beef_cost_and_beef_price(tmp_path):
    # 'beef' is rare (df<=5) -> one shared rare token suffices; common-only overlap must NOT pair.
    run = make_run(tmp_path, [rec("beef_cost"), rec("beef_price"), rec("labor_cost"),
                              rec("occupancy_cost"), rec("marketing_cost"), rec("insurance_cost"),
                              rec("freight_cost"), rec("packaging_cost")])
    blob = suggest(run)
    got = {tuple(sorted((c["a"], c["b"]))) for c in blob["candidates"]}
    assert ("beef_cost", "beef_price") in got
    # labor_cost vs beef_cost share only 'cost' (df=7 here, common) and no rare token -> NOT suggested
    assert ("beef_cost", "labor_cost") not in got


def test_suggest_limit_clipping_is_reported_never_silent(tmp_path):
    run = make_run(tmp_path, [rec("beef_cost"), rec("beef_price"), rec("beef_supply"),
                              rec("beef_demand")])
    blob = suggest(run, limit=2)
    assert blob["count"] == 2
    assert blob["clipped"] >= 1                      # dropped pairs are COUNTED, not hidden
    full = suggest(run, limit=2000)
    assert full["clipped"] == 0


def test_apply_is_idempotent_byte_identical(tmp_path):
    run = make_run(tmp_path, [rec("guest_count"), rec("customer_transactions"), rec("oil_price")])
    cands(run, ("guest_count", "customer_transactions"))
    review = run / "repair_review.json"
    review.write_text(json.dumps({"reviews": [
        {"a": "guest_count", "b": "customer_transactions", "verdict": "SAME",
         "canonical": "guest_count", "why": "same metric"}]}))
    apply(run, review)
    first = (run / "catalog.json").read_bytes()
    apply(run, review)                               # second run: pair already present -> no-op
    assert (run / "catalog.json").read_bytes() == first


def test_apply_high_blast_with_proof_passes_full_validator(tmp_path):
    # e2e: the n>=8 proof written by apply must satisfy the validator backstop (pure-code recount).
    import subprocess, sys as _sys
    big = [f"C{i}" for i in range(8)]
    run = make_run(tmp_path, [rec("same_store_sales", companies=big),
                              rec("comparable_sales", companies=("C0",)), rec("oil_price")])
    cands(run, ("same_store_sales", "comparable_sales"))
    review = run / "repair_review.json"
    review.write_text(json.dumps({"reviews": [
        {"a": "same_store_sales", "b": "comparable_sales", "verdict": "SAME",
         "canonical": "same_store_sales", "why": "same metric",
         "high_blast_refute2_survived": True}]}))
    apply(run, review)
    out = subprocess.run([_sys.executable, str(WORKFLOWS / "validate_catalog.py"),
                          str(run / "seed.json"), str(run / "catalog.json"),
                          str(run / "approved.json")], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr


@pytest.mark.skipif(
    os.environ.get("RUN_LIVE_EMBEDDINGS") != "1"
    or (not os.environ.get("OPENAI_API_KEY")
        and not (Path("/home/faisal/EventMarketDB/.env").exists()
                 and "OPENAI_API_KEY" in Path("/home/faisal/EventMarketDB/.env").read_text())),
    reason="live embedding smoke is opt-in: set RUN_LIVE_EMBEDDINGS=1")
def test_live_embeddings_rank_semantic_pair(tmp_path):
    # Owner-authorized ONE tiny live smoke: zero-token-overlap synonyms must surface via embeddings.
    run = make_run(tmp_path, [
        rec("guest_count", refs=[ref(quote="guest counts in our restaurants rose 3% this quarter")]),
        rec("customer_transactions", refs=[ref(sid="e2", quote="customer transactions in our restaurants grew 3%")]),
        rec("oil_price", refs=[ref(sid="e3", quote="crude oil prices increased our energy costs")]),
        rec("share_repurchase", refs=[ref(sid="e4", quote="we bought back 2 million shares")]),
    ])
    blob = suggest(run, use_embeddings=True)
    got = {tuple(sorted((c["a"], c["b"]))) for c in blob["candidates"]}
    assert ("customer_transactions", "guest_count") in got
