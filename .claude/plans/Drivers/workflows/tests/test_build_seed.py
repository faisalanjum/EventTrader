"""TDD for build_seed.py — deterministic seed grouping + write (E1/E2 + §11.14, 11th-pass code-write).

Replaces menu_build.js's in-JS Converge grouping: reads menus/*.json (one per blind bot),
groups by norm()'d driver_name (final name = the lowercased form), unions evidence
(dedup by exact 5-tuple), first non-null xbrl wins, writes seed.json IN CODE (sha printed).
--expect cross-checks per-ticker candidate counts against the workflow's structured outputs.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOWS))

from build_seed import build_seed, serialize  # noqa: E402

PY = sys.executable
CLI = str(WORKFLOWS / "build_seed.py")


def cand(name, source_id="ev1", quote="q", date="2026-01-01", source_type="transcript", xbrl="null"):
    return {"driver_name": name, "evidence_quote": quote, "source_type": source_type,
            "source_id": source_id, "date": date, "xbrl_or_null": xbrl}


def menu(ticker, *cands):
    return {"ticker": ticker, "candidate_count": len(cands), "candidates": list(cands),
            "skipped_count": 0, "notes": []}


def write_menus(tmp_path, *menus):
    md = tmp_path / "menus"
    md.mkdir(exist_ok=True)
    for i, m in enumerate(menus):
        (md / f"{m['ticker']}__part{i:03d}.json").write_text(json.dumps(m))
    return tmp_path


def test_case_fold_groups_and_lowercases_final_name(tmp_path):
    write_menus(tmp_path, menu("AAA", cand("Guest_Count", source_id="e1")),
                menu("BBB", cand("guest_count", source_id="e2")))
    seed = build_seed(tmp_path, industry="TestInd", slug="test_ind", run_id="r1")
    assert [r["driver_name"] for r in seed["catalog"]] == ["guest_count"]  # §11.14 lowercased
    rec = seed["catalog"][0]
    assert rec["canonical_name"] == "guest_count"
    assert rec["companies"] == ["AAA", "BBB"]
    assert {e["company"] for e in rec["evidence_refs"]} == {"AAA", "BBB"}


def test_five_tuple_dedup(tmp_path):
    write_menus(tmp_path, menu("AAA", cand("oil_price", source_id="e1"), cand("oil_price", source_id="e1")))
    seed = build_seed(tmp_path, industry="T", slug="t", run_id="r1")
    assert len(seed["catalog"][0]["evidence_refs"]) == 1
    assert seed["analysis"]["total_candidates"] == 2  # raw count preserved in analysis


def test_first_xbrl_wins_and_null_ignored(tmp_path):
    write_menus(tmp_path,
                menu("AAA", cand("gross_margin", source_id="e1", xbrl="null")),
                menu("BBB", cand("gross_margin", source_id="e2", xbrl="us-gaap:GrossProfit"),
                     cand("gross_margin", source_id="e3", xbrl="us-gaap:Other")))
    seed = build_seed(tmp_path, industry="T", slug="t", run_id="r1")
    assert seed["catalog"][0]["optional_links"]["xbrl_concept"] == "us-gaap:GrossProfit"


def test_shared_drivers_only_multi_company(tmp_path):
    write_menus(tmp_path, menu("AAA", cand("oil_price", source_id="e1"), cand("aaa_only", source_id="e2")),
                menu("BBB", cand("oil_price", source_id="e3")))
    seed = build_seed(tmp_path, industry="T", slug="t", run_id="r1")
    assert seed["analysis"]["shared_drivers"] == [{"driver_name": "oil_price", "companies": ["AAA", "BBB"]}]
    assert seed["analysis"]["total_distinct_drivers"] == 2


def test_catalog_sorted_and_records_self_canonical(tmp_path):
    write_menus(tmp_path, menu("AAA", cand("zeta_metric", source_id="e1"), cand("alpha_metric", source_id="e2")))
    seed = build_seed(tmp_path, industry="T", slug="t", run_id="r1")
    assert [r["driver_name"] for r in seed["catalog"]] == ["alpha_metric", "zeta_metric"]
    assert all(r["canonical_name"] == r["driver_name"] for r in seed["catalog"])


def test_cli_deterministic_and_expect_ok(tmp_path):
    write_menus(tmp_path, menu("AAA", cand("oil_price", source_id="e1")),
                menu("BBB", cand("oil_price", source_id="e2"), cand("guest_count", source_id="e3")))
    expect = json.dumps({"AAA": 1, "BBB": 2})
    shas = []
    for _ in range(2):
        out = subprocess.run([PY, CLI, str(tmp_path), "--industry", "T", "--slug", "t",
                              "--run-id", "r1", "--expect", expect],
                             capture_output=True, text=True)
        assert out.returncode == 0, out.stderr
        summary = json.loads(out.stdout.strip().splitlines()[-1])
        sha = hashlib.sha256((tmp_path / "seed.json").read_bytes()).hexdigest()
        assert summary["seed_sha256"] == sha
        assert summary["total_distinct_drivers"] == 2
        shas.append(sha)
    assert shas[0] == shas[1]


def test_cli_expect_mismatch_fails(tmp_path):
    write_menus(tmp_path, menu("AAA", cand("oil_price", source_id="e1")))
    out = subprocess.run([PY, CLI, str(tmp_path), "--industry", "T", "--slug", "t",
                          "--run-id", "r1", "--expect", json.dumps({"AAA": 2})],
                         capture_output=True, text=True)
    assert out.returncode == 1
    assert "EXPECT" in (out.stdout + out.stderr)


def test_empty_or_blank_names_skipped(tmp_path):
    write_menus(tmp_path, menu("AAA", cand("", source_id="e1"), cand("  ", source_id="e2"),
                               cand("real_name", source_id="e3")))
    seed = build_seed(tmp_path, industry="T", slug="t", run_id="r1")
    assert [r["driver_name"] for r in seed["catalog"]] == ["real_name"]
