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


# ================================================================ C5 build: plan/show (batched lane)

def _cands(names_pairs):
    return [{"a": a, "b": b, "reason": "token_overlap:x", "n_companies": 1,
             "sides": [{"driver_name": a, "evidence_refs": []},
                       {"driver_name": b, "evidence_refs": []}]} for a, b in names_pairs]


def _pin(run, cands_list):
    import json as _json
    from assemble_catalog import h32 as _h32
    blob = {"candidates": cands_list, "count": len(cands_list), "clipped": 0,
            "limit_used": 5000, "use_embeddings": False,
            "pairs_h32": _h32("\n".join(f"{c['a']}|{c['b']}" for c in cands_list)),
            "cands_h32": _h32(_json.dumps(cands_list, sort_keys=True, separators=(",", ":"),
                                          ensure_ascii=False))}
    (run / "repair_candidates.json").write_text(serialize(blob))
    return blob


def test_plan_is_deterministic_and_disjoint(tmp_path):
    from repair_duplicates import plan_batches
    run = tmp_path / "r"; run.mkdir()
    # one high-degree name (alpha in 5 pairs) + independents
    pairs = [("alpha", f"x{i}") for i in range(5)] + [(f"p{i}", f"q{i}") for i in range(12)]
    _pin(run, _cands(pairs))
    s1 = plan_batches(run, k=4, page_size=600)
    p1 = (run / "repair_plan.json").read_bytes()
    s2 = plan_batches(run, k=4, page_size=600)
    assert (run / "repair_plan.json").read_bytes() == p1          # byte-deterministic
    plan = json.loads(p1)
    cands = json.loads((run / "repair_candidates.json").read_text())["candidates"]
    seen = []
    for b in plan["batches"]:
        assert len(b["idx"]) <= 4
        names = []
        for i in b["idx"]:
            names += [cands[i]["a"], cands[i]["b"]]
        assert len(names) == len(set(names))                       # HARD disjointness in-batch
        seen += b["idx"]
    assert sorted(seen) == list(range(len(cands)))                 # every pair planned exactly once
    assert s1["batches"] == len(plan["batches"]) and s2["ok"]


def test_plan_pages_never_straddle(tmp_path):
    from repair_duplicates import plan_batches
    run = tmp_path / "r"; run.mkdir()
    _pin(run, _cands([(f"a{i}", f"b{i}") for i in range(13)]))
    plan_batches(run, k=10, page_size=5)
    plan = json.loads((run / "repair_plan.json").read_text())
    assert plan["pages"] == 3                                      # 5+5+3
    from collections import defaultdict
    per_page = defaultdict(set)
    for b in plan["batches"]:
        per_page[b["page"]].update(b["idx"])
    assert sorted(len(v) for v in per_page.values()) == [3, 5, 5]
    for b in plan["batches"]:
        assert {plan["page_of"][str(i)] for i in b["idx"]} == {b["page"]}


def test_plan_order_breaks_ranked_adjacency(tmp_path):
    from repair_duplicates import plan_batches
    run = tmp_path / "r"; run.mkdir()
    # similarity-ranked input: adjacent pairs share tokens (the anchoring hazard)
    _pin(run, _cands([(f"guest_count_{i}", f"guest_total_{i}") for i in range(20)]))
    plan_batches(run, k=10, page_size=600)
    plan = json.loads((run / "repair_plan.json").read_text())
    flat = [i for b in plan["batches"] for i in b["idx"]]
    assert flat != list(range(20))                                 # hash-shuffle, not ranked order


def test_plan_writes_batch_files_and_binds_candidates_sha(tmp_path):
    from repair_duplicates import plan_batches
    import hashlib
    run = tmp_path / "r"; run.mkdir()
    _pin(run, _cands([("a1", "b1"), ("a2", "b2")]))
    plan_batches(run, k=10, page_size=600)
    plan = json.loads((run / "repair_plan.json").read_text())
    assert plan["cands_sha256"] == hashlib.sha256(
        (run / "repair_candidates.json").read_bytes()).hexdigest()
    bf = json.loads((run / "repair_batches" / "batch_0000.json").read_text())
    assert [p["idx"] for p in bf["pairs"]] == plan["batches"][0]["idx"]
    assert all(set(p) >= {"idx", "a", "b", "sides"} for p in bf["pairs"])


def test_show_prints_selected_candidates_with_binding_hash(tmp_path):
    from repair_duplicates import show_candidates
    from assemble_catalog import h32 as _h32
    run = tmp_path / "r"; run.mkdir()
    _pin(run, _cands([("a1", "b1"), ("a2", "b2"), ("a3", "b3")]))
    out = show_candidates(run, [2, 0])
    assert [c["idx"] for c in out["candidates"]] == [2, 0]         # requested order preserved
    assert out["page_h32"] == _h32(json.dumps(out["candidates"], sort_keys=True,
                                              separators=(",", ":"), ensure_ascii=False))
    import pytest as _pt
    with _pt.raises(SystemExit, match="out of range"):
        show_candidates(run, [99])


def _plan_run(tmp_path):
    """Real run dir (assembled+validated) + pinned candidates + plan, for apply-P2 tests."""
    from repair_duplicates import plan_batches
    run = make_run(tmp_path, [rec("guest_count"), rec("customer_transactions"),
                              rec("store_count"), rec("oil_price")])
    cands_list = _cands([("guest_count", "customer_transactions"),
                         ("store_count", "oil_price")])
    _pin(run, cands_list)
    plan_batches(run, k=10, page_size=600)
    return run


def _rows(run, rows):
    rp = run / "repair_review.json"
    rp.write_text(json.dumps({"reviews": rows}))
    return rp


def test_apply_p2_happy_path_with_confirmed_same(tmp_path):
    from repair_duplicates import apply as repair_apply
    run = _plan_run(tmp_path)
    out = repair_apply(run, _rows(run, [
        {"idx": 0, "a": "guest_count", "b": "customer_transactions", "verdict": "SAME",
         "why": "same metric", "confirmed": True},
        {"idx": 1, "a": "store_count", "b": "oil_price", "verdict": "DIFFERENT", "why": "no",
         "canary_verdict": "DIFFERENT", "canary_why": "solo agrees"}]))
    assert out["added"] == 1


def test_apply_p2_rejects_unconfirmed_batched_same(tmp_path):
    from repair_duplicates import apply as repair_apply
    run = _plan_run(tmp_path)
    rp = _rows(run, [
        {"idx": 0, "a": "guest_count", "b": "customer_transactions", "verdict": "SAME",
         "why": "same metric"},
        {"idx": 1, "a": "store_count", "b": "oil_price", "verdict": "DIFFERENT", "why": "no"}])
    with pytest.raises(SystemExit, match="confirm"):
        repair_apply(run, rp)


def test_apply_p2_rejects_idx_name_transposition(tmp_path):
    from repair_duplicates import apply as repair_apply
    run = _plan_run(tmp_path)
    rp = _rows(run, [
        {"idx": 1, "a": "guest_count", "b": "customer_transactions", "verdict": "SAME",
         "why": "x", "confirmed": True},
        {"idx": 0, "a": "store_count", "b": "oil_price", "verdict": "DIFFERENT", "why": "no"}])
    with pytest.raises(SystemExit, match="does not match plan"):
        repair_apply(run, rp)


def test_apply_p2_rejects_missing_idx_and_duplicate_idx(tmp_path):
    from repair_duplicates import apply as repair_apply
    run = _plan_run(tmp_path)
    rp = _rows(run, [{"idx": 0, "a": "guest_count", "b": "customer_transactions",
                      "verdict": "DIFFERENT", "why": "x"}])
    with pytest.raises(SystemExit, match="exactly once"):
        repair_apply(run, rp)
    rp = _rows(run, [
        {"idx": 0, "a": "guest_count", "b": "customer_transactions", "verdict": "DIFFERENT", "why": "x"},
        {"idx": 0, "a": "guest_count", "b": "customer_transactions", "verdict": "DIFFERENT", "why": "x"},
        {"idx": 1, "a": "store_count", "b": "oil_price", "verdict": "DIFFERENT", "why": "no"}])
    with pytest.raises(SystemExit, match="exactly once"):
        repair_apply(run, rp)


def test_apply_p2_rejects_stale_plan_after_candidates_change(tmp_path):
    from repair_duplicates import apply as repair_apply
    run = _plan_run(tmp_path)
    _pin(run, _cands([("guest_count", "customer_transactions")]))   # regenerated AFTER plan
    rp = _rows(run, [{"idx": 0, "a": "guest_count", "b": "customer_transactions",
                      "verdict": "DIFFERENT", "why": "x"}])
    with pytest.raises(SystemExit, match="stale"):
        repair_apply(run, rp)


def test_apply_without_plan_keeps_todays_per_pair_semantics(tmp_path):
    # kill switch: no repair_plan.json -> exactly the existing behavior (no idx/confirmed needed)
    from repair_duplicates import apply as repair_apply
    run = make_run(tmp_path, [rec("guest_count"), rec("customer_transactions")])
    _pin(run, _cands([("guest_count", "customer_transactions")]))
    out = repair_apply(run, _rows(run, [
        {"a": "guest_count", "b": "customer_transactions", "verdict": "SAME", "why": "same"}]))
    assert out["added"] == 1


def test_suggest_clears_stale_plan_artifacts(tmp_path):
    # a crashed batched run leaves repair_plan.json + batch files; the NEXT run's suggest
    # (always the first step) must clear them so a per-pair re-run can't false-stop on P2.
    from repair_duplicates import plan_batches, suggest
    run = make_run(tmp_path, [rec("guest_count"), rec("customer_transactions")])
    _pin(run, _cands([("guest_count", "customer_transactions")]))
    plan_batches(run, k=10, page_size=600)
    assert (run / "repair_plan.json").exists()
    suggest(run)
    assert not (run / "repair_plan.json").exists()
    assert not list((run / "repair_batches").glob("batch_*.json"))


def test_suggest_limit_zero_means_no_cap(tmp_path):
    # C5 batched mode: limit=0 = ALL pairs (never a cap); clipped must be 0.
    from repair_duplicates import suggest
    run = make_run(tmp_path, [rec("guest_count_growth"), rec("guest_transactions_growth"),
                              rec("guest_traffic_growth"), rec("store_count_growth")])
    blob = suggest(run, limit=0)
    assert blob["count"] == 6 and blob["clipped"] == 0 and blob["limit_used"] == 0


def test_suggest_cli_print_summary_omits_candidates(tmp_path):
    # C5 slim relay: --print-summary prints counts/hashes/params ONLY (tiny, relayable at any
    # scale); the full blob still lands on disk as the pinned candidates file.
    import subprocess, sys as _sys
    run = make_run(tmp_path, [rec("guest_count_growth"), rec("guest_transactions_growth")])
    import hashlib as _h
    sc = {"exit": 0, "fold": False,
          "catalog_sha256": _h.sha256((run / "catalog.json").read_bytes()).hexdigest(),
          "approved_sha256": _h.sha256((run / "approved.json").read_bytes()).hexdigest()}
    (run / "validation_exit.json").write_text(json.dumps(sc))
    out = subprocess.run([_sys.executable, str(WORKFLOWS / "repair_duplicates.py"), "suggest",
                          str(run), "--limit", "0", "--print-summary"],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr
    printed = json.loads(out.stdout.strip().splitlines()[-1])
    assert "candidates" not in printed
    assert printed["count"] == 1 and {"pairs_h32", "cands_h32", "limit_used",
                                      "use_embeddings"} <= set(printed)
    disk = json.loads((run / "repair_candidates.json").read_text())
    assert len(disk["candidates"]) == 1                  # full blob pinned on disk


def test_summary_mode_prints_slim_view_of_existing_file_without_regenerating(tmp_path):
    # decision-④ frozen fixture: arm runs must reuse the PINNED candidates file verbatim.
    import subprocess, sys as _sys, hashlib as _h
    run = make_run(tmp_path, [rec("guest_count_growth"), rec("guest_transactions_growth")])
    _pin(run, _cands([("guest_count_growth", "guest_transactions_growth")]))
    before = _h.sha256((run / "repair_candidates.json").read_bytes()).hexdigest()
    out = subprocess.run([_sys.executable, str(WORKFLOWS / "repair_duplicates.py"),
                          "summary", str(run)], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr
    printed = json.loads(out.stdout.strip().splitlines()[-1])
    assert "candidates" not in printed and printed["count"] == 1
    assert {"pairs_h32", "cands_h32", "limit_used", "use_embeddings"} <= set(printed)
    assert _h.sha256((run / "repair_candidates.json").read_bytes()).hexdigest() == before


def test_ab_harness_prompt_is_byte_identical_to_production():
    # decision-④ round: the whole A/B rests on ab_pair_judge.js using EXACTLY the production
    # per-pair prompt — lock the two template strings together so neither can drift silently.
    a = (WORKFLOWS / "ab_pair_judge.js").read_text()
    r = (WORKFLOWS / "repair_duplicates.js").read_text()
    ga = a[a.index("const PAIR_REVIEW_PROMPT"):a.index("const REVIEW_SCHEMA")]
    gr = r[r.index("const PAIR_REVIEW_PROMPT"):r.index("const REFUTE2_PROMPT")]
    ta = ga[ga.index("You are"):ga.rindex("keep separate.")]
    tr = gr[gr.index("You are"):gr.rindex("keep separate.")]
    assert ta == tr
    # and the meaning rule itself
    ea = a[a.index("const EXACT_MEANING_RULE"):a.index("// VERBATIM")]
    er = r[r.index("const EXACT_MEANING_RULE"):r.index("const SUGGEST_SCHEMA")]
    ra = ea[ea.index("Approve SAME"):ea.rindex("UNCLEAR.")]
    rr = er[er.index("Approve SAME"):er.rindex("UNCLEAR.")]
    assert ra == rr


# ---- post_split repair links onto D5-coined targets (found live 2026-06-11: Arm-1 apply
# blocked on food_beverage_cogs / board_share_repurchase_authorization — repair runs on the
# FINAL catalog, so its SAME_AS rows legitimately reference split-coined names; only
# gate-time decisions are anachronistic there) ----

def make_split_run(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    records = [
        rec("food_cost", companies=("AAA", "BBB")),
        rec("food_beverage_costs", companies=("CCC",)),
    ]
    seed = {"industry": "Test", "catalog": records, "analysis": {}}
    review = {"reviews": [{"collision_name": "food_cost", "verdict": "DIFFERENT",
                           "why": "two different objects"}],
              "split_map": [{"from": "food_cost",
                             "to": ["food_beverage_cogs", "commodity_basket"],
                             "assignments": [{"company": "AAA", "to": "food_beverage_cogs"},
                                             {"company": "BBB", "to": "commodity_basket"}]}]}
    dec = {"gate_verdicts": [], "approved_same_as": [], "approved_rewrites": [],
           "parked_rewrites": []}
    cat, approved = assemble(seed, dec, review)
    (run / "seed.json").write_text(serialize(seed))
    (run / "same_name_review.json").write_text(serialize(review))
    (run / "decisions.json").write_text(serialize(dec))
    (run / "catalog.json").write_text(serialize(cat))
    (run / "approved.json").write_text(serialize(approved))
    return run


def test_repair_link_onto_coined_split_target_applies_with_post_split_tag(tmp_path):
    run = make_split_run(tmp_path)
    cands(run, ("food_beverage_cogs", "food_beverage_costs"))
    review = {"reviews": [{"a": "food_beverage_cogs", "b": "food_beverage_costs",
                           "verdict": "SAME", "why": "same exact object"}]}
    rp = run / "repair_review.json"
    rp.write_text(serialize(review))
    out = apply(run, rp)
    assert out["added"] == 1
    dec = json.loads((run / "decisions.json").read_text())
    assert dec["approved_same_as"] and all(
        l.get("post_split") is True for l in dec["approved_same_as"])
    cat = json.loads((run / "catalog.json").read_text())
    rolled = [r for r in cat["catalog"] if r["canonical_name"] != r["driver_name"]]
    assert len(rolled) == 1


def test_untagged_gate_decision_referencing_coined_target_still_hard_fails(tmp_path):
    run = make_split_run(tmp_path)
    seed = json.loads((run / "seed.json").read_text())
    review = json.loads((run / "same_name_review.json").read_text())
    dec = json.loads((run / "decisions.json").read_text())
    dec["approved_same_as"].append({"variant": "food_beverage_costs",
                                    "canonical": "food_beverage_cogs"})   # NO post_split tag
    with pytest.raises(SystemExit, match="coined split target"):
        assemble(seed, dec, review)


def test_repair_apply_on_split_run_is_idempotent_byte_identical(tmp_path):
    run = make_split_run(tmp_path)
    cands(run, ("food_beverage_cogs", "food_beverage_costs"))
    review = {"reviews": [{"a": "food_beverage_cogs", "b": "food_beverage_costs",
                           "verdict": "SAME", "why": "same exact object"}]}
    rp = run / "repair_review.json"
    rp.write_text(serialize(review))
    assert apply(run, rp)["added"] == 1
    first = (run / "catalog.json").read_bytes()
    out2 = apply(run, rp)
    assert out2["added"] == 0
    assert (run / "catalog.json").read_bytes() == first


def test_apply_does_not_persist_decisions_when_assemble_fails(tmp_path, monkeypatch):
    import repair_duplicates as rd
    run = make_run(tmp_path, [rec("guest_count_growth"), rec("guest_transactions_growth")])
    cands(run, ("guest_count_growth", "guest_transactions_growth"))
    review = {"reviews": [{"a": "guest_count_growth", "b": "guest_transactions_growth",
                           "verdict": "SAME", "why": "same exact meaning"}]}
    rp = run / "repair_review.json"
    rp.write_text(serialize(review))
    before = (run / "decisions.json").read_bytes()

    def boom(*a, **k):
        raise SystemExit("ASSEMBLE FAIL: injected")
    monkeypatch.setattr(rd, "assemble", boom)
    with pytest.raises(SystemExit, match="injected"):
        rd.apply(run, rp)
    assert (run / "decisions.json").read_bytes() == before   # mutate-before-validate is gone


# ---- chunked relay-write of repair_review.json (incident 2026-06-11: single-shot Write of
# the 529-row review truncated at the clerk's output limit; the hand re-transcription
# drifted 1 byte and the expect gate refused — pieces are cut at ROW boundaries by the JS,
# each post-write h32-asserted, and assemble-review is the python FINAL enforcement) ----

from repair_duplicates import assemble_review  # noqa: E402
from assemble_catalog import h32  # noqa: E402


def _piece_texts(rows, k):
    """Replicates the JS piece construction rule exactly: rowStrs joined with ',',
    '{"reviews":[' prefix on piece 0, ']}' suffix on the last piece."""
    rs = [json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in rows]
    out = []
    for s in range(0, len(rs), k):
        body = ",".join(rs[s:s + k])
        out.append(('{"reviews":[' if s == 0 else ',') + body + (']}' if s + k >= len(rs) else ''))
    return out


def _write_pieces(tmp_path, rows, k):
    run = tmp_path / "run"
    run.mkdir(exist_ok=True)
    cdir = run / "review_chunks"
    cdir.mkdir(exist_ok=True)
    pieces = _piece_texts(rows, k)
    for i, t in enumerate(pieces):
        (cdir / f"piece_{i:04d}.txt").write_text(t, encoding="utf-8")
    return run, pieces, "".join(pieces)


def _ar_rows(n):
    return [{"idx": i, "a": f"driver_{i}", "b": f'dr "quoted" \\ {i} 🎂',
             "verdict": "DIFFERENT", "why": f"unicode — naïve café №{i}"} for i in range(n)]


def test_assemble_review_multi_piece_byte_identity(tmp_path):
    rows = _ar_rows(7)
    run, pieces, full = _write_pieces(tmp_path, rows, 3)
    assert len(pieces) == 3
    assert full == json.dumps({"reviews": rows}, ensure_ascii=False, separators=(",", ":"))
    out = assemble_review(run, 3, f"rv=7,h32={h32(full)}")
    assert out["ok"] is True and out["rv"] == 7
    assert (run / "repair_review.json").read_text(encoding="utf-8") == full
    assert not (run / "review_chunks").exists()      # pieces cleaned, no stale survivors


def test_assemble_review_rejects_drifted_piece(tmp_path):
    rows = _ar_rows(5)
    run, pieces, full = _write_pieces(tmp_path, rows, 2)
    p = run / "review_chunks" / "piece_0001.txt"
    p.write_text(p.read_text(encoding="utf-8").replace("naïve", "naive"), encoding="utf-8")
    with pytest.raises(SystemExit, match="EXPECT MISMATCH"):
        assemble_review(run, 3, f"rv=5,h32={h32(full)}")
    assert not (run / "repair_review.json").exists()


def test_assemble_review_rejects_missing_and_stale_extra_piece(tmp_path):
    rows = _ar_rows(5)
    run, pieces, full = _write_pieces(tmp_path, rows, 2)
    with pytest.raises(SystemExit, match="piece"):
        assemble_review(run, 4, f"rv=5,h32={h32(full)}")   # missing piece_0003
    (run / "review_chunks" / "piece_0007.txt").write_text("stale", encoding="utf-8")
    with pytest.raises(SystemExit, match="piece"):
        assemble_review(run, 3, f"rv=5,h32={h32(full)}")   # stale extra survivor


def test_assemble_review_rejects_rv_mismatch(tmp_path):
    rows = _ar_rows(4)
    run, pieces, full = _write_pieces(tmp_path, rows, 2)
    with pytest.raises(SystemExit, match="EXPECT MISMATCH"):
        assemble_review(run, 2, f"rv=9,h32={h32(full)}")
    assert not (run / "repair_review.json").exists()


# ---- §8d GO condition #2: the production canary (batched lane only). Apply RE-derives a
# deterministic ~2% sample (h32 of normalized pair, idx tie-break; min 5, clipped to pool)
# of the DIFFERENT/UNCLEAR rows that never got an isolated look, and refuses to apply if a
# sampled row lacks a solo canary_verdict (canary skipped) or if any canary_verdict is
# SAME (the lane is missing merges — abort loud, never auto-merge from the canary). ----

def test_canary_happy_path_applies_with_solo_verdicts(tmp_path):
    from repair_duplicates import apply as repair_apply
    run = _plan_run(tmp_path)
    out = repair_apply(run, _rows(run, [
        {"idx": 0, "a": "guest_count", "b": "customer_transactions", "verdict": "SAME",
         "why": "same metric", "confirmed": True},
        {"idx": 1, "a": "store_count", "b": "oil_price", "verdict": "DIFFERENT", "why": "no",
         "canary_verdict": "DIFFERENT", "canary_why": "solo agrees: unrelated"}]))
    assert out["added"] == 1


def test_canary_missing_solo_verdict_fails_closed(tmp_path):
    from repair_duplicates import apply as repair_apply
    run = _plan_run(tmp_path)
    rp = _rows(run, [
        {"idx": 0, "a": "guest_count", "b": "customer_transactions", "verdict": "SAME",
         "why": "same metric", "confirmed": True},
        {"idx": 1, "a": "store_count", "b": "oil_price", "verdict": "DIFFERENT", "why": "no"}])
    with pytest.raises(SystemExit, match="canary"):
        repair_apply(run, rp)


def test_canary_hit_aborts_before_any_write(tmp_path):
    from repair_duplicates import apply as repair_apply
    run = _plan_run(tmp_path)
    before_cat = (run / "catalog.json").read_bytes()
    before_dec = (run / "decisions.json").read_bytes()
    rp = _rows(run, [
        {"idx": 0, "a": "guest_count", "b": "customer_transactions", "verdict": "SAME",
         "why": "same metric", "confirmed": True},
        {"idx": 1, "a": "store_count", "b": "oil_price", "verdict": "DIFFERENT", "why": "no",
         "canary_verdict": "SAME", "canary_why": "solo disagrees"}])
    with pytest.raises(SystemExit, match="CANARY HIT"):
        repair_apply(run, rp)
    assert (run / "catalog.json").read_bytes() == before_cat
    assert (run / "decisions.json").read_bytes() == before_dec


def test_canary_excludes_confirm_flipped_rows(tmp_path):
    from repair_duplicates import apply as repair_apply
    run = _plan_run(tmp_path)
    # idx0 = confirm-flipped (DIFFERENT, confirmed:true -> already isolated; NOT canary
    # eligible, needs no canary_verdict); idx1 = batched DIFFERENT -> sampled, has one.
    out = repair_apply(run, _rows(run, [
        {"idx": 0, "a": "guest_count", "b": "customer_transactions", "verdict": "DIFFERENT",
         "why": "confirm flipped it", "confirmed": True},
        {"idx": 1, "a": "store_count", "b": "oil_price", "verdict": "DIFFERENT", "why": "no",
         "canary_verdict": "DIFFERENT", "canary_why": "solo agrees"}]))
    assert out["added"] == 0


def test_canary_not_enforced_without_plan(tmp_path):
    from repair_duplicates import apply as repair_apply
    run = make_run(tmp_path, [rec("guest_count_growth"), rec("guest_transactions_growth")])
    cands(run, ("guest_count_growth", "guest_transactions_growth"))
    out = repair_apply(run, _rows(run, [
        {"a": "guest_count_growth", "b": "guest_transactions_growth",
         "verdict": "DIFFERENT", "why": "per-pair lane, already isolated"}]))
    assert out["added"] == 0
