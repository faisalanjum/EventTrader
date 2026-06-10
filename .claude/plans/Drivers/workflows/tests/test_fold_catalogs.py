"""TDD for fold_catalogs.py — the deterministic fold combine (HierarchicalCatalogPlan §11.7)
+ the §12.8 evidence draw + the §11.11 SEED_MAX guard. ZERO AI, ZERO judgment.

part-a: per-child cluster collapse (canonical fixpoint, 5-tuple evidence union, variant
        carry-forward, drop-but-count side-lists) -> cross-child passthrough vs the
        same-name-review queue (never pre-merge). SEED_MAX guard BEFORE writing.
draw:   §12.8 deterministic per-side evidence views (smallest side first, company
        round-robin, source-type spread, empty-date-first, per-side cap, disjoint view2).
part-b: apply the review file — SAME (refute_survived required) / DIFFERENT (complete
        evidence partition) / UNCLEAR (terminal park) — star + sorted parent seed.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

WORKFLOWS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOWS))

from fold_catalogs import (  # noqa: E402
    RECONCILE_EVIDENCE_PER_RECORD,
    SEED_MAX_RECORDS,
    draw_views,
    part_a,
    part_b,
)

PY = sys.executable
CLI = str(WORKFLOWS / "fold_catalogs.py")


def ref(company="AAA", st="transcript", sid="e1", date="2026-01-01", quote=None):
    return {"company": company, "source_type": st, "source_id": sid,
            "date": date, "quote": quote if quote is not None else f"quote {sid}"}


def rec(name, canonical=None, refs=None, variants=None, xbrl=None):
    refs = refs if refs is not None else [ref(sid=f"ev_{name}")]
    return {"driver_name": name, "canonical_name": canonical or name,
            "companies": sorted({r["company"] for r in refs}),
            "evidence_refs": refs,
            "same_as_variants": variants or [],
            "optional_links": {"xbrl_concept": xbrl, "xbrl_member": None, "guidance_ref": None}}


def child(tmp, run_id, recs, industry=None, skips=None, unres=None, unres_same=None):
    d = tmp / run_id
    d.mkdir(exist_ok=True)
    cat = {"industry": industry or f"Ind_{run_id}", "catalog": recs,
           "skips": skips or [], "unresolved_rewrites": unres or [],
           "unresolved_same_name": unres_same or []}
    (d / "catalog.json").write_text(json.dumps(cat))
    return d


def parent(tmp):
    p = tmp / "parent_run"
    p.mkdir(exist_ok=True)
    return p


def review_same(name, why="same meaning", refute=True):
    rv = {"collision_name": name, "verdict": "SAME", "why": why}
    if refute:
        rv["refute_survived"] = True
    return {"reviews": [rv], "split_map": []}


def cli(*args):
    return subprocess.run([PY, CLI, *map(str, args)], capture_output=True, text=True)


def load(p, name):
    return json.loads((p / name).read_text())


def k5(e):
    return ((e["company"] or "").strip().lower(), (e["source_type"] or "").strip().lower(),
            (e["source_id"] or "").strip().lower(), (e["date"] or "").strip().lower(),
            (e["quote"] or "").strip())


# ---------------------------------------------------------------- part-a

def test_part_a_collapse_resolves_chains_unions_evidence_variants(tmp_path):
    shared = ref(company="AAA", sid="e1")  # duplicate 5-tuple across variant + rep
    c1 = child(tmp_path, "c1", [
        rec("c_rep", refs=[shared]),
        rec("b_mid", canonical="c_rep", refs=[ref(company="BBB", sid="e2")],
            variants=["b_old"]),
        rec("a_var", canonical="b_mid", refs=[ref(company="AAA", sid="e3"), dict(shared)]),
    ])
    p = parent(tmp_path)
    s = part_a(p, "TestSector", "sector", [c1])
    assert s == {"passthrough": 1, "collisions": 0, "children": 1,
                 "collision_names": [], "collision_meta": {}}
    recs = load(p, "fold_passthrough.json")["records"]
    assert len(recs) == 1
    r = recs[0]
    assert r["driver_name"] == "c_rep" and r["canonical_name"] == "c_rep"
    assert {e["source_id"] for e in r["evidence_refs"]} == {"e1", "e2", "e3"}  # deduped union
    assert r["evidence_refs"] == sorted(r["evidence_refs"], key=k5)
    assert r["companies"] == ["AAA", "BBB"]
    assert r["same_as_variants"] == ["a_var", "b_mid", "b_old"]  # carried + variants' own, sorted
    assert load(p, "fold_queue.json") == {"queue": []}


def test_part_a_cycle_fails(tmp_path):
    c1 = child(tmp_path, "c1", [rec("a_one", canonical="b_two"),
                                rec("b_two", canonical="a_one")])
    with pytest.raises(SystemExit, match="cycle"):
        part_a(parent(tmp_path), "S", "sector", [c1])


def test_part_a_dangling_canonical_fails(tmp_path):
    c1 = child(tmp_path, "c1", [rec("a_one", canonical="ghost_name")])
    with pytest.raises(SystemExit, match="dangl"):
        part_a(parent(tmp_path), "S", "sector", [c1])


def test_part_a_drops_side_lists_but_counts_them(tmp_path):
    c1 = child(tmp_path, "c1", [rec("a_one")], industry="IndA",
               skips=[{"driver_name": "s1", "why": "w"}, {"driver_name": "s2", "why": "w"}],
               unres=[{"driver_name": "u1", "proposed_to": "x", "why": "w"}],
               unres_same=[{"name": "n1", "occurrences": [], "why": "w"}])
    c2 = child(tmp_path, "c2", [rec("b_two")], industry="IndB")
    p = parent(tmp_path)
    part_a(p, "TestSector", "sector", [c1, c2])
    man = load(p, "fold_manifest.json")
    assert man["scope_name"] == "TestSector" and man["scope_level"] == "sector"
    assert man["children"] == [
        {"child_run_id": "c1", "scope_name": "IndA", "kept_count": 1, "skips_count": 2,
         "unresolved_rewrites_count": 1, "unresolved_same_name_count": 1},
        {"child_run_id": "c2", "scope_name": "IndB", "kept_count": 1, "skips_count": 0,
         "unresolved_rewrites_count": 0, "unresolved_same_name_count": 0},
    ]
    names = [r["driver_name"] for r in load(p, "fold_passthrough.json")["records"]]
    assert names == ["a_one", "b_two"]  # dropped side-list names NOT carried


def test_part_a_cli_passthrough_vs_collision_queue(tmp_path):
    child(tmp_path, "c1", [rec("oil_price", refs=[ref(company="AAA", sid="e1")]),
                           rec("a_only", refs=[ref(company="AAA", sid="e2")])])
    child(tmp_path, "c2", [rec("oil_price", refs=[ref(company="BBB", sid="e3")]),
                           rec("b_only", refs=[ref(company="BBB", sid="e4")])])
    p = parent(tmp_path)
    out = cli("part-a", p, "--scope-name", "TestSector", "--scope-level", "sector",
              "--children", tmp_path / "c1", tmp_path / "c2")
    assert out.returncode == 0, out.stderr
    assert json.loads(out.stdout.strip().splitlines()[-1]) == {
        "passthrough": 2, "collisions": 1, "children": 2,
        "collision_names": ["oil_price"],
        "collision_meta": {"oil_price": {"n_companies": 2, "n_children": 2}}}
    q = load(p, "fold_queue.json")["queue"]
    assert [i["name"] for i in q] == ["oil_price"]
    assert [o["child_run_id"] for o in q[0]["occurrences"]] == ["c1", "c2"]  # NOT pre-merged
    assert sorted(r["driver_name"] for r in load(p, "fold_passthrough.json")["records"]) \
        == ["a_only", "b_only"]


def test_part_a_collision_meta_distinct_companies_across_occurrences(tmp_path):
    child(tmp_path, "c1", [rec("oil_price", refs=[ref(company="AAA", sid="e1"),
                                                  ref(company="BBB", sid="e2")]),
                           rec("wage_rate", refs=[ref(company="AAA", sid="e3")])])
    child(tmp_path, "c2", [rec("oil_price", refs=[ref(company="BBB", sid="e4")]),
                           rec("wage_rate", refs=[ref(company="CCC", sid="e5")])])
    child(tmp_path, "c3", [rec("oil_price", refs=[ref(company="CCC", sid="e6")])])
    s = part_a(parent(tmp_path), "S", "sector",
               [tmp_path / "c1", tmp_path / "c2", tmp_path / "c3"])
    assert s["collision_names"] == ["oil_price", "wage_rate"]      # sorted queue names
    assert s["collision_meta"] == {
        "oil_price": {"n_companies": 3, "n_children": 3},          # {AAA,BBB} ∪ {BBB} ∪ {CCC}
        "wage_rate": {"n_companies": 2, "n_children": 2}}          # {AAA} ∪ {CCC}


def test_part_a_guard_fires_on_401_records_before_writing(tmp_path):
    child(tmp_path, "c1", [rec(f"d_{i:03d}", refs=[ref(sid=f"e{i}")]) for i in range(401)])
    p = parent(tmp_path)
    out = cli("part-a", p, "--scope-name", "S", "--scope-level", "sector",
              "--children", tmp_path / "c1")
    assert out.returncode == 1
    assert f"SEED_MAX GUARD: records=401>{SEED_MAX_RECORDS}" in (out.stdout + out.stderr)
    assert not (p / "fold_queue.json").exists()       # guard fires BEFORE writing
    assert not (p / "fold_passthrough.json").exists()
    assert not (p / "fold_manifest.json").exists()


def test_part_a_guard_fires_on_oversize_chars(tmp_path):
    c1 = child(tmp_path, "c1", [rec("big_one", refs=[ref(sid="e1", quote="x" * 300_001)])])
    with pytest.raises(SystemExit, match="SEED_MAX GUARD: records=1"):
        part_a(parent(tmp_path), "S", "sector", [c1])


def test_part_a_guard_overrides_recorded_in_summary(tmp_path):
    child(tmp_path, "c1", [rec("a_one"), rec("b_two")])
    p = parent(tmp_path)
    out = cli("part-a", p, "--scope-name", "S", "--scope-level", "sector",
              "--children", tmp_path / "c1", "--max-records", "1")
    assert out.returncode == 1 and "SEED_MAX GUARD: records=2>1" in (out.stdout + out.stderr)
    out = cli("part-a", p, "--scope-name", "S", "--scope-level", "sector",
              "--children", tmp_path / "c1", "--max-records", "50", "--max-chars", "9000")
    assert out.returncode == 0, out.stderr
    summary = json.loads(out.stdout.strip().splitlines()[-1])
    assert summary["max_records"] == 50 and summary["max_chars"] == 9000


# ---------------------------------------------------------------- draw (§12.8)

def queue_item(name, *sides):
    return {"queue": [{"name": name, "occurrences": [
        {"child_run_id": cid, "record": rec(name, refs=refs)} for cid, refs in sides]}]}


def test_draw_side_order_smallest_first_and_per_side_cap():
    big = [ref(company="AAA", sid=f"b{i:02d}") for i in range(25)]
    small = [ref(company="BBB", sid=f"s{i}") for i in range(3)]
    views = draw_views(queue_item("oil_price", ("big_child", big), ("small_child", small)))
    sides = views["items"][0]["sides"]
    assert [s["side_key"] for s in sides] == ["small_child", "big_child"]  # smallest first
    assert len(sides[0]["view1"]) == 3 and sides[0]["view2"] == [] and sides[0]["total_refs"] == 3
    assert len(sides[1]["view1"]) == RECONCILE_EVIDENCE_PER_RECORD                # per-side cap
    assert len(sides[1]["view2"]) == 5 and sides[1]["total_refs"] == 25
    assert views["items"][0]["name"] == "oil_price"


def test_draw_source_type_spread_and_empty_date_first():
    refs = [ref(st="transcript", sid="t2", date="2026-02-01"),
            ref(st="transcript", sid="t1", date="2026-01-01"),
            ref(st="10-k", sid="k1", date=""),
            ref(st="10-k", sid="k2", date="2026-03-01"),
            ref(st="transcript", sid="t3", date="2026-04-01"),
            ref(st="transcript", sid="t4", date="2026-03-15")]
    views = draw_views(queue_item("x_name", ("c1", refs)), cap=3)
    side = views["items"][0]["sides"][0]
    # one per type first (types sorted, earliest date, empty date FIRST): k1, t1;
    # then earliest remaining t2, latest remaining t3; rest canonical: k2, t4
    assert [e["source_id"] for e in side["view1"]] == ["k1", "t1", "t2"]
    assert [e["source_id"] for e in side["view2"]] == ["t3", "k2", "t4"]


def test_draw_company_round_robin_minority_first():
    refs = [ref(company="AAA", sid="a1", date="2026-01-01"),
            ref(company="AAA", sid="a2", date="2026-02-01"),
            ref(company="AAA", sid="a3", date="2026-03-01"),
            ref(company="BBB", sid="b1", date="2026-01-01")]
    views = draw_views(queue_item("x_name", ("c1", refs)))
    side = views["items"][0]["sides"][0]
    assert [e["source_id"] for e in side["view1"]] == ["b1", "a1", "a2", "a3"]


def test_draw_cli_deterministic_and_view2_disjoint(tmp_path):
    child(tmp_path, "c1", [rec("oil_price",
                               refs=[ref(company=f"C{i % 5}", sid=f"x{i:02d}") for i in range(25)])])
    child(tmp_path, "c2", [rec("oil_price", refs=[ref(company="ZZZ", sid="z1")])])
    p = parent(tmp_path)
    part_a(p, "S", "sector", [tmp_path / "c1", tmp_path / "c2"])
    blobs = []
    for _ in range(2):
        out = cli("draw", p)
        assert out.returncode == 0, out.stderr
        assert json.loads(out.stdout.strip().splitlines()[-1]) == {"items": 1}
        blobs.append((p / "fold_queue_views.json").read_bytes())
    assert blobs[0] == blobs[1]  # byte-identical across runs
    sides = json.loads(blobs[0])["items"][0]["sides"]
    big = next(s for s in sides if s["side_key"] == "c1")
    v1, v2 = {k5(e) for e in big["view1"]}, {k5(e) for e in big["view2"]}
    assert len(big["view1"]) == 20 and len(big["view2"]) == 5  # shorter when exhausted, no pad
    assert v1 & v2 == set()                                    # never re-show


# ---------------------------------------------------------------- part-b

def fold_collision(tmp_path, recs1, recs2):
    c1 = child(tmp_path, "c1", recs1)
    c2 = child(tmp_path, "c2", recs2)
    p = parent(tmp_path)
    part_a(p, "TestSector", "sector", [c1, c2])
    return p


def test_part_b_same_union_star_sorted(tmp_path):
    p = fold_collision(
        tmp_path,
        [rec("oil_price", refs=[ref(company="AAA", sid="e1")]),
         rec("crude_price", canonical="oil_price", refs=[ref(company="AAA", sid="e2")]),
         rec("z_solo", refs=[ref(company="AAA", sid="e9")])],
        [rec("oil_price", refs=[ref(company="BBB", sid="e3")])])
    s = part_b(p, review_same("oil_price"))
    assert s["records"] == 2 and s["parks"] == 0 and s["conflicts"] == 0
    seed = load(p, "seed.json")
    assert seed["scope_name"] == "TestSector" and seed["scope_level"] == "sector"
    assert seed["run_id"] == "parent_run"
    assert seed["analysis"] == {"total_distinct_drivers": 2, "from_children": 2}
    assert [r["driver_name"] for r in seed["catalog"]] == ["oil_price", "z_solo"]  # sorted
    assert all(r["canonical_name"] == r["driver_name"] for r in seed["catalog"])   # STAR
    union = seed["catalog"][0]
    assert {e["source_id"] for e in union["evidence_refs"]} == {"e1", "e2", "e3"}
    assert union["evidence_refs"] == sorted(union["evidence_refs"], key=k5)
    assert union["companies"] == ["AAA", "BBB"]
    assert union["same_as_variants"] == ["crude_price"]
    assert load(p, "fold_sidecars.json") == {"unresolved_same_name": [],
                                             "optional_links_conflicts": []}


def test_part_b_same_without_refute_survived_fails(tmp_path):
    p = fold_collision(tmp_path, [rec("oil_price")], [rec("oil_price", refs=[ref(company="B", sid="e2")])])
    with pytest.raises(SystemExit, match="refute_survived"):
        part_b(p, review_same("oil_price", refute=False))


def test_part_b_missing_review_fails(tmp_path):
    p = fold_collision(tmp_path, [rec("oil_price")], [rec("oil_price", refs=[ref(company="B", sid="e2")])])
    with pytest.raises(SystemExit, match="without a review"):
        part_b(p, {"reviews": [], "split_map": []})


def test_part_b_extra_review_fails(tmp_path):
    p = fold_collision(tmp_path, [rec("oil_price")], [rec("oil_price", refs=[ref(company="B", sid="e2")])])
    rv = review_same("oil_price")
    rv["reviews"].append({"collision_name": "never_queued", "verdict": "SAME",
                          "refute_survived": True, "why": "w"})
    with pytest.raises(SystemExit, match="non-queued"):
        part_b(p, rv)


def split_review(frm, assignments, to=("fleet_size_capacity", "fleet_size_cost")):
    return {"reviews": [{"collision_name": frm, "verdict": "DIFFERENT",
                         "new_names": list(to), "why": "homonym"}],
            "split_map": [{"from": frm, "to": list(to), "assignments": assignments}]}


def test_part_b_different_split_default_assignments(tmp_path):
    p = fold_collision(tmp_path,
                       [rec("fleet_size", refs=[ref(company="AAA", sid="e1")], xbrl="us-gaap:A")],
                       [rec("fleet_size", refs=[ref(company="BBB", sid="e2")])])
    s = part_b(p, split_review("fleet_size", [
        {"child_run_id": "c1", "to": "fleet_size_capacity"},
        {"child_run_id": "c2", "to": "fleet_size_cost"}]))
    assert s["records"] == 2 and s["parks"] == 0
    seed = load(p, "seed.json")
    cap = next(r for r in seed["catalog"] if r["driver_name"] == "fleet_size_capacity")
    cost = next(r for r in seed["catalog"] if r["driver_name"] == "fleet_size_cost")
    assert [e["source_id"] for e in cap["evidence_refs"]] == ["e1"]
    assert [e["source_id"] for e in cost["evidence_refs"]] == ["e2"]
    assert cap["companies"] == ["AAA"] and cost["companies"] == ["BBB"]
    assert cap["canonical_name"] == "fleet_size_capacity"
    assert cap["same_as_variants"] == [] and cost["same_as_variants"] == []
    assert cap["optional_links"] == {"xbrl_concept": None, "xbrl_member": None,
                                     "guidance_ref": None}  # splits start all-null
    assert not any(r["driver_name"] == "fleet_size" for r in seed["catalog"])


def test_part_b_split_lost_ref_fails(tmp_path):
    p = fold_collision(tmp_path, [rec("fleet_size", refs=[ref(company="AAA", sid="e1")])],
                       [rec("fleet_size", refs=[ref(company="BBB", sid="e2")])])
    with pytest.raises(SystemExit, match="lost|unassigned"):
        part_b(p, split_review("fleet_size", [{"child_run_id": "c1", "to": "fleet_size_capacity"}]))


def test_part_b_split_partial_keys_lose_a_ref_fails(tmp_path):
    p = fold_collision(tmp_path,
                       [rec("fleet_size", refs=[ref(company="AAA", sid="e1"), ref(company="AAA", sid="e2")])],
                       [rec("fleet_size", refs=[ref(company="BBB", sid="e3")])])
    keys = [["AAA", "transcript", "e1", "2026-01-01", "quote e1"]]  # e2 never assigned
    with pytest.raises(SystemExit, match="lost|unassigned"):
        part_b(p, split_review("fleet_size", [
            {"child_run_id": "c1", "to": "fleet_size_capacity", "evidence_ref_keys": keys},
            {"child_run_id": "c2", "to": "fleet_size_cost"}]))


def test_part_b_split_duplicated_ref_fails(tmp_path):
    p = fold_collision(tmp_path,
                       [rec("fleet_size", refs=[ref(company="AAA", sid="e1")])],
                       [rec("fleet_size", refs=[ref(company="BBB", sid="e2")])])
    k1 = [["AAA", "transcript", "e1", "2026-01-01", "quote e1"]]
    with pytest.raises(SystemExit, match="duplicat|twice"):
        part_b(p, split_review("fleet_size", [
            {"child_run_id": "c1", "to": "fleet_size_capacity", "evidence_ref_keys": k1},
            {"child_run_id": "c1", "to": "fleet_size_cost", "evidence_ref_keys": k1},
            {"child_run_id": "c2", "to": "fleet_size_cost"}]))


def test_part_b_split_within_child_by_evidence_ref_keys(tmp_path):
    p = fold_collision(tmp_path,
                       [rec("fleet_size", refs=[ref(company="AAA", sid="e1"), ref(company="AAA", sid="e2")])],
                       [rec("fleet_size", refs=[ref(company="BBB", sid="e3")])])
    s = part_b(p, split_review("fleet_size", [
        {"child_run_id": "c1", "to": "fleet_size_capacity",
         "evidence_ref_keys": [["AAA", "transcript", "e1", "2026-01-01", "quote e1"]]},
        {"child_run_id": "c1", "to": "fleet_size_cost",
         "evidence_ref_keys": [["AAA", "transcript", "e2", "2026-01-01", "quote e2"]]},
        {"child_run_id": "c2", "to": "fleet_size_cost"}]))
    assert s["records"] == 2
    seed = load(p, "seed.json")
    cap = next(r for r in seed["catalog"] if r["driver_name"] == "fleet_size_capacity")
    cost = next(r for r in seed["catalog"] if r["driver_name"] == "fleet_size_cost")
    assert [e["source_id"] for e in cap["evidence_refs"]] == ["e1"]
    assert {e["source_id"] for e in cost["evidence_refs"]} == {"e2", "e3"}


def test_part_b_split_target_not_lower_snake_fails(tmp_path):
    p = fold_collision(tmp_path, [rec("fleet_size")],
                       [rec("fleet_size", refs=[ref(company="B", sid="e2")])])
    with pytest.raises(SystemExit, match="lower_snake"):
        part_b(p, split_review("fleet_size",
                               [{"child_run_id": "c1", "to": "Fleet_Capacity"},
                                {"child_run_id": "c2", "to": "fleet_size_cost"}],
                               to=("Fleet_Capacity", "fleet_size_cost")))


def test_part_b_unclear_parks_terminal(tmp_path):
    p = fold_collision(tmp_path, [rec("guest_count", refs=[ref(company="AAA", sid="e1")])],
                       [rec("guest_count", refs=[ref(company="BBB", sid="e2")])])
    s = part_b(p, {"reviews": [{"collision_name": "guest_count", "verdict": "UNCLEAR",
                                "why": "mixed meanings"}], "split_map": []})
    assert s["records"] == 0 and s["parks"] == 1
    seed = load(p, "seed.json")
    assert seed["catalog"] == []  # parked name NOT a seed record
    parks = load(p, "fold_sidecars.json")["unresolved_same_name"]
    assert len(parks) == 1 and parks[0]["name"] == "guest_count"
    assert parks[0]["why"] == "mixed meanings"
    assert [o["child_run_id"] for o in parks[0]["occurrences"]] == ["c1", "c2"]
    assert all(o["evidence_refs"] for o in parks[0]["occurrences"])


def test_part_b_optional_links_conflict_nulls_and_records(tmp_path):
    p = fold_collision(tmp_path,
                       [rec("oil_price", refs=[ref(company="AAA", sid="e1")], xbrl="us-gaap:A")],
                       [rec("oil_price", refs=[ref(company="BBB", sid="e2")], xbrl="us-gaap:B")])
    s = part_b(p, review_same("oil_price"))
    assert s["conflicts"] == 1
    seed = load(p, "seed.json")
    assert seed["catalog"][0]["optional_links"]["xbrl_concept"] is None  # never silently pick
    assert load(p, "fold_sidecars.json")["optional_links_conflicts"] == [
        {"driver_name": "oil_price", "key": "xbrl_concept",
         "values": ["us-gaap:A", "us-gaap:B"]}]


def test_part_b_one_non_null_value_kept(tmp_path):
    p = fold_collision(tmp_path,
                       [rec("oil_price", refs=[ref(company="AAA", sid="e1")], xbrl="us-gaap:A")],
                       [rec("oil_price", refs=[ref(company="BBB", sid="e2")])])
    part_b(p, review_same("oil_price"))
    seed = load(p, "seed.json")
    assert seed["catalog"][0]["optional_links"]["xbrl_concept"] == "us-gaap:A"
    assert load(p, "fold_sidecars.json")["optional_links_conflicts"] == []


def test_part_b_cli_guard_and_summary(tmp_path):
    p = fold_collision(tmp_path, [rec("a_one"), rec("b_two")], [rec("c_three", refs=[ref(company="B", sid="e9")])])
    rv = tmp_path / "review.json"
    rv.write_text(json.dumps({"reviews": [], "split_map": []}))
    out = cli("part-b", p, "--review", rv, "--max-records", "1")
    assert out.returncode == 1
    assert "SEED_MAX GUARD: records=3>1" in (out.stdout + out.stderr)
    assert not (p / "seed.json").exists()
    out = cli("part-b", p, "--review", rv)
    assert out.returncode == 0, out.stderr
    summary = json.loads(out.stdout.strip().splitlines()[-1])
    assert summary["records"] == 3 and summary["parks"] == 0 and summary["conflicts"] == 0
    assert len(summary["seed_sha256"]) == 64


def test_part_b_unknown_verdict_fails(tmp_path):
    p = fold_collision(tmp_path, [rec("oil_price")], [rec("oil_price", refs=[ref(company="B", sid="e2")])])
    with pytest.raises(SystemExit, match="verdict"):
        part_b(p, {"reviews": [{"collision_name": "oil_price", "verdict": "MAYBE", "why": "w"}],
                   "split_map": []})
