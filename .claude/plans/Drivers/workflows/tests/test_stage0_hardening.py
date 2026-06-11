"""Stage-0 integrity hardening (CostCutting.md DO-REGARDLESS table) — TDD.

Eight deterministic checks that remove TRUST from clerk relays. Every check is tested
under: honest pass · honest fail · lying/stale relay artifact · edge cases.

  #1 validator sidecar  validate_catalog.py writes validation_exit.json {exit, catalog_sha256,
                        approved_sha256?}; fold part_a + repair-suggest CLI hard-fail unless the
                        consumed catalog is exit-0-validated AND byte-identical since.
  #2 chunk coverage     build_seed.py: every chunks/<cid>.json must have menus/<cid>.json
                        (and no stale extra menus) when a chunks/ dir exists.
  #3 gate coverage      assemble_catalog.py CLI: every seed driver_name needs a gate verdict
                        or a same-name-review entry — un-reviewed names cannot ship.
  #4/#5 write fidelity  --expect counts + h32 (JS-computable UTF-16 rolling hash) bind the
                        agent-written decisions.json / review files to the JS-side string.
  #6 global-fold flag   validator recomputes n_children from child catalogs; a kept SAME in a
                        GLOBAL fold (>=2 children) must carry high_blast_refute2_survived.
  #8 scope pinning      fetch --scope/--subset reads tickers code-to-code; chunker hard-fails
                        if sources/ != scope_resolved.json tickers.
  #7 pair identity      JS assert (verdict echoes its assigned pair) + python backstop:
                        apply() rejects any NEW link absent from repair_candidates.json.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

WORKFLOWS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOWS))

from assemble_catalog import h32, serialize  # noqa: E402
from fold_catalogs import part_a, part_b, require_validated  # noqa: E402

PY = sys.executable
ASSEMBLE = str(WORKFLOWS / "assemble_catalog.py")
VALIDATOR = str(WORKFLOWS / "validate_catalog.py")
REPAIR = str(WORKFLOWS / "repair_duplicates.py")
FOLD = str(WORKFLOWS / "fold_catalogs.py")
BUILD_SEED = str(WORKFLOWS / "build_seed.py")


# ---------------------------------------------------------------- shared fixtures

def ref(company="AAA", sid="e1", quote=None):
    return {"company": company, "source_type": "transcript", "source_id": sid,
            "date": "2026-01-01", "quote": quote or f"quote {sid}"}


def rec(name, companies=("AAA",)):
    return {"driver_name": name, "canonical_name": name, "companies": sorted(companies),
            "evidence_refs": [ref(company=c, sid=f"{name}_{c}") for c in sorted(companies)],
            "same_as_variants": [],
            "optional_links": {"xbrl_concept": None, "xbrl_member": None, "guidance_ref": None}}


def admit_all(seed, but=()):
    return [{"driver_name": r["driver_name"], "verdict": "admit", "reason": "t"}
            for r in seed["catalog"] if r["driver_name"] not in but]


def make_run(tmp_path, names=("alpha_sales", "beta_margin"), name="run"):
    """A run dir whose catalog/approved were produced by the REAL assemble CLI."""
    run = tmp_path / name
    run.mkdir()
    seed = {"industry": "Test", "catalog": [rec(n) for n in names], "analysis": {}}
    dec = {"gate_verdicts": admit_all(seed), "approved_same_as": [],
           "approved_rewrites": [], "parked_rewrites": []}
    (run / "seed.json").write_text(serialize(seed))
    (run / "decisions.json").write_text(serialize(dec))
    out = subprocess.run([PY, ASSEMBLE, str(run)], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr
    return run


def validate_cli(run, approved=True):
    args = [PY, VALIDATOR, str(run / "seed.json"), str(run / "catalog.json")]
    if approved:
        args.append(str(run / "approved.json"))
    return subprocess.run(args, capture_output=True, text=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def stamp(run):
    """Hand-stamped sidecar (what a real validator pass writes) for fixture dirs."""
    sc = {"exit": 0, "catalog_sha256": sha(run / "catalog.json")}
    if (run / "approved.json").exists():
        sc["approved_sha256"] = sha(run / "approved.json")
    (run / "validation_exit.json").write_text(json.dumps(sc) + "\n")


# ================================================================ #1 sidecar: writer

def test_validator_pass_writes_exit0_sidecar_bound_to_bytes(tmp_path):
    run = make_run(tmp_path)
    out = validate_cli(run)
    assert out.returncode == 0, out.stdout
    sc = json.loads((run / "validation_exit.json").read_text())
    assert sc["exit"] == 0
    assert sc["catalog_sha256"] == sha(run / "catalog.json")
    assert sc["approved_sha256"] == sha(run / "approved.json")


def test_validator_fail_writes_exit1_sidecar(tmp_path):
    run = make_run(tmp_path)
    cat = json.loads((run / "catalog.json").read_text())
    cat["catalog"] = cat["catalog"][1:]          # drop a record -> COMPLETE fails
    (run / "catalog.json").write_text(serialize(cat))
    out = validate_cli(run)
    assert out.returncode == 1
    assert json.loads((run / "validation_exit.json").read_text())["exit"] == 1


def test_validator_legacy_two_arg_sidecar_has_no_approved_sha(tmp_path):
    run = make_run(tmp_path)
    out = validate_cli(run, approved=False)
    assert out.returncode == 0
    sc = json.loads((run / "validation_exit.json").read_text())
    assert "approved_sha256" not in sc and sc["exit"] == 0


# ================================================================ #1 sidecar: part_a consumer

def fold_child(tmp_path, name="childA", names=("oil_price",)):
    run = make_run(tmp_path, names=names, name=name)
    out = validate_cli(run)
    assert out.returncode == 0
    return run


def test_part_a_accepts_validated_children(tmp_path):
    c1 = fold_child(tmp_path, "childA")
    c2 = fold_child(tmp_path, "childB", names=("wage_inflation",))
    s = part_a(tmp_path / "parent", "S", "sector", [c1, c2])
    assert s["passthrough"] == 2


def test_part_a_rejects_child_without_sidecar(tmp_path):
    c1 = fold_child(tmp_path, "childA")
    c2 = fold_child(tmp_path, "childB", names=("wage_inflation",))
    (c2 / "validation_exit.json").unlink()
    with pytest.raises(SystemExit, match="never .*validated|no validation_exit"):
        part_a(tmp_path / "parent", "S", "sector", [c1, c2])


def test_part_a_rejects_child_whose_last_validation_failed(tmp_path):
    c1 = fold_child(tmp_path, "childA")
    sc = json.loads((c1 / "validation_exit.json").read_text())
    sc["exit"] = 1
    (c1 / "validation_exit.json").write_text(json.dumps(sc))
    with pytest.raises(SystemExit, match="FAILED"):
        part_a(tmp_path / "parent", "S", "sector",
               [c1, fold_child(tmp_path, "childB", names=("wage_inflation",))])


def test_part_a_rejects_catalog_changed_since_validation(tmp_path):
    c1 = fold_child(tmp_path, "childA")
    cat = json.loads((c1 / "catalog.json").read_text())
    cat["catalog"][0]["driver_name"] = "tampered_name"
    (c1 / "catalog.json").write_text(serialize(cat))   # catalog edited AFTER validation
    with pytest.raises(SystemExit, match="changed since"):
        part_a(tmp_path / "parent", "S", "sector",
               [c1, fold_child(tmp_path, "childB", names=("wage_inflation",))])


def test_part_a_rejects_approved_unbound_or_tampered(tmp_path):
    c1 = fold_child(tmp_path, "childA")
    ap = json.loads((c1 / "approved.json").read_text())
    ap["same_as"].append({"variant": "x", "canonical": "y"})   # tampered after validation
    (c1 / "approved.json").write_text(serialize(ap))
    with pytest.raises(SystemExit, match="approved"):
        part_a(tmp_path / "parent", "S", "sector",
               [c1, fold_child(tmp_path, "childB", names=("wage_inflation",))])


def test_require_validated_child_without_approved_file_ok(tmp_path):
    # synthetic fixtures: catalog-only child + catalog-only sidecar is acceptable
    d = tmp_path / "c"
    d.mkdir()
    (d / "catalog.json").write_text(serialize({"industry": "I", "catalog": [rec("oil_price")],
                                               "skips": [], "unresolved_rewrites": [],
                                               "unresolved_same_name": []}))
    stamp(d)
    require_validated(d)                                        # no raise


# ================================================================ #1 sidecar: repair-suggest CLI consumer

def test_repair_suggest_cli_requires_valid_sidecar(tmp_path):
    run = make_run(tmp_path, names=("guest_count_growth", "guest_transactions_growth"))
    out = subprocess.run([PY, REPAIR, "suggest", str(run)], capture_output=True, text=True)
    assert out.returncode != 0
    assert "validat" in (out.stdout + out.stderr).lower()
    assert validate_cli(run).returncode == 0                    # real validation stamps it
    out2 = subprocess.run([PY, REPAIR, "suggest", str(run)], capture_output=True, text=True)
    assert out2.returncode == 0, out2.stdout + out2.stderr
    assert json.loads(out2.stdout)["count"] == 1


def test_repair_suggest_cli_rejects_stale_catalog(tmp_path):
    run = make_run(tmp_path, names=("guest_count_growth", "guest_transactions_growth"))
    assert validate_cli(run).returncode == 0
    cat = json.loads((run / "catalog.json").read_text())
    cat["catalog"][0]["companies"] = ["ZZZ"]                    # edited after validation
    (run / "catalog.json").write_text(serialize(cat))
    out = subprocess.run([PY, REPAIR, "suggest", str(run)], capture_output=True, text=True)
    assert out.returncode != 0 and "changed since" in (out.stdout + out.stderr)


# ================================================================ #3 gate coverage (assemble CLI)

def test_cli_unreviewed_seed_name_cannot_ship(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    seed = {"industry": "T", "catalog": [rec("alpha_sales"), rec("beta_margin")], "analysis": {}}
    (run / "seed.json").write_text(serialize(seed))
    (run / "decisions.json").write_text(serialize(
        {"gate_verdicts": admit_all(seed, but=("beta_margin",)), "approved_same_as": [],
         "approved_rewrites": [], "parked_rewrites": []}))
    out = subprocess.run([PY, ASSEMBLE, str(run)], capture_output=True, text=True)
    assert out.returncode != 0
    assert "NO gate verdict" in (out.stdout + out.stderr)
    assert "beta_margin" in (out.stdout + out.stderr)


def test_cli_review_covered_name_is_excused(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    seed = {"industry": "T", "catalog": [rec("alpha_sales"), rec("mixed_name")], "analysis": {}}
    (run / "seed.json").write_text(serialize(seed))
    (run / "decisions.json").write_text(serialize(
        {"gate_verdicts": admit_all(seed, but=("mixed_name",)), "approved_same_as": [],
         "approved_rewrites": [], "parked_rewrites": []}))
    (run / "review.json").write_text(serialize(
        {"reviews": [{"collision_name": "mixed_name", "verdict": "UNCLEAR", "why": "thin"}],
         "split_map": []}))
    out = subprocess.run([PY, ASSEMBLE, str(run), "--review", "review.json"],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr


def test_cli_empty_gate_verdicts_nonempty_seed_fails(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    (run / "seed.json").write_text(serialize(
        {"industry": "T", "catalog": [rec("alpha_sales")], "analysis": {}}))
    (run / "decisions.json").write_text(serialize(
        {"gate_verdicts": [], "approved_same_as": [], "approved_rewrites": [],
         "parked_rewrites": []}))
    out = subprocess.run([PY, ASSEMBLE, str(run)], capture_output=True, text=True)
    assert out.returncode != 0 and "NO gate verdict" in (out.stdout + out.stderr)


# ================================================================ #4 decisions write fidelity (--expect)

def test_h32_matches_the_js_charcode_rolling_hash():
    assert h32("\U0001F600") == 1772899        # astral char = surrogate PAIR (55357*31+56832), JS-identical
    assert h32("") == 0
    assert h32("a") == 97
    assert h32("ab") == 97 * 31 + 98          # 3105
    assert h32("é") == 233                    # BMP unicode = one UTF-16 code unit
    assert h32("aé") == 97 * 31 + 233


def expect_for(dec_text, dec_obj):
    return (f"gv={len(dec_obj.get('gate_verdicts') or [])},"
            f"sa={len(dec_obj.get('approved_same_as') or [])},"
            f"rw={len(dec_obj.get('approved_rewrites') or [])},"
            f"pk={len(dec_obj.get('parked_rewrites') or [])},"
            f"hb={len(dec_obj.get('high_blast_refute2') or [])},"
            f"h32={h32(dec_text.rstrip(chr(10)))}")


def expect_run(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    seed = {"industry": "T", "catalog": [rec("alpha_sales"), rec("beta_margin")], "analysis": {}}
    dec = {"gate_verdicts": admit_all(seed), "approved_same_as": [],
           "approved_rewrites": [], "parked_rewrites": []}
    dec_text = json.dumps(dec, separators=(",", ":"))           # the compact JS-style string
    (run / "seed.json").write_text(serialize(seed))
    (run / "decisions.json").write_text(dec_text)               # agent wrote it byte-for-byte
    return run, dec, dec_text


def test_cli_expect_match_passes_with_and_without_trailing_newline(tmp_path):
    run, dec, dec_text = expect_run(tmp_path)
    e = expect_for(dec_text, dec)
    out = subprocess.run([PY, ASSEMBLE, str(run), "--expect", e], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr
    (run / "decisions.json").write_text(dec_text + "\n")        # Write tool added a newline
    out2 = subprocess.run([PY, ASSEMBLE, str(run), "--expect", e], capture_output=True, text=True)
    assert out2.returncode == 0, out2.stdout + out2.stderr


def test_cli_expect_catches_dropped_row(tmp_path):
    run, dec, dec_text = expect_run(tmp_path)
    e = expect_for(dec_text, dec)
    short = dict(dec)
    short["gate_verdicts"] = dec["gate_verdicts"][:1]           # one verdict row lost entirely
    (run / "decisions.json").write_text(json.dumps(short, separators=(",", ":")))
    out = subprocess.run([PY, ASSEMBLE, str(run), "--expect", e], capture_output=True, text=True)
    assert out.returncode != 0 and "EXPECT MISMATCH" in (out.stdout + out.stderr)


def test_cli_expect_catches_same_length_content_edit(tmp_path):
    run, dec, dec_text = expect_run(tmp_path)
    e = expect_for(dec_text, dec)
    tampered = dec_text.replace("beta_margin", "beta_margiX")   # same length, same counts
    (run / "decisions.json").write_text(tampered)
    out = subprocess.run([PY, ASSEMBLE, str(run), "--expect", e], capture_output=True, text=True)
    assert out.returncode != 0 and "EXPECT MISMATCH" in (out.stdout + out.stderr)


def test_cli_expect_catches_reformatting(tmp_path):
    run, dec, dec_text = expect_run(tmp_path)
    e = expect_for(dec_text, dec)
    (run / "decisions.json").write_text(json.dumps(dec, indent=1))   # agent pretty-printed
    out = subprocess.run([PY, ASSEMBLE, str(run), "--expect", e], capture_output=True, text=True)
    assert out.returncode != 0 and "EXPECT MISMATCH" in (out.stdout + out.stderr)


def test_cli_expect_review_binds_review_file(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    seed = {"industry": "T", "catalog": [rec("alpha_sales"), rec("mixed_name")], "analysis": {}}
    dec = {"gate_verdicts": admit_all(seed, but=("mixed_name",)), "approved_same_as": [],
           "approved_rewrites": [], "parked_rewrites": []}
    review = {"reviews": [{"collision_name": "mixed_name", "verdict": "UNCLEAR", "why": "thin"}],
              "split_map": []}
    rv_text = json.dumps(review, separators=(",", ":"))
    (run / "seed.json").write_text(serialize(seed))
    (run / "decisions.json").write_text(serialize(dec))
    (run / "review.json").write_text(rv_text)
    er = f"rv=1,sm=0,h32={h32(rv_text)}"
    ok = subprocess.run([PY, ASSEMBLE, str(run), "--review", "review.json",
                         "--expect-review", er], capture_output=True, text=True)
    assert ok.returncode == 0, ok.stdout + ok.stderr
    flipped = rv_text.replace('"UNCLEAR"', '"SAME"  ')   # verdict flip attempt
    (run / "review.json").write_text(flipped)
    bad = subprocess.run([PY, ASSEMBLE, str(run), "--review", "review.json",
                          "--expect-review", er], capture_output=True, text=True)
    assert bad.returncode != 0 and "EXPECT MISMATCH" in (bad.stdout + bad.stderr)


# ================================================================ #5 part-b + repair-apply fidelity

def global_fold(tmp_path, with_flag):
    c1 = fold_child(tmp_path, "childA", names=("oil_price",))
    c2 = fold_child(tmp_path, "childB", names=("oil_price",))
    p = tmp_path / "parent"
    part_a(p, "GLOBAL", "global", [c1, c2])
    rv = {"collision_name": "oil_price", "verdict": "SAME", "why": "same",
          "refute_survived": True}
    if with_flag:
        rv["high_blast_refute2_survived"] = True
    review = {"reviews": [rv], "split_map": []}
    (p / "same_name_review.json").write_text(serialize(review))
    part_b(p, review)
    seed = json.loads((p / "seed.json").read_text())
    (p / "decisions.json").write_text(serialize(
        {"gate_verdicts": admit_all(seed), "approved_same_as": [],
         "approved_rewrites": [], "parked_rewrites": []}))
    out = subprocess.run([PY, ASSEMBLE, str(p)], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr
    return p, c1, c2


def test_part_b_cli_expect_binds_review_file(tmp_path):
    c1 = fold_child(tmp_path, "childA", names=("oil_price",))
    c2 = fold_child(tmp_path, "childB", names=("oil_price",))
    p = tmp_path / "parent"
    part_a(p, "S", "sector", [c1, c2])
    review = {"reviews": [{"collision_name": "oil_price", "verdict": "SAME", "why": "same",
                           "refute_survived": True}], "split_map": []}
    rv_text = json.dumps(review, separators=(",", ":"))
    (p / "same_name_review.json").write_text(rv_text)
    e = f"rv=1,sm=0,h32={h32(rv_text)}"
    ok = subprocess.run([PY, FOLD, "part-b", str(p), "--review",
                         str(p / "same_name_review.json"), "--expect", e],
                        capture_output=True, text=True)
    assert ok.returncode == 0, ok.stdout + ok.stderr
    tampered = rv_text.replace('"SAME"', '"SAMe"')              # content changed post-JS
    (p / "same_name_review.json").write_text(tampered)
    bad = subprocess.run([PY, FOLD, "part-b", str(p), "--review",
                          str(p / "same_name_review.json"), "--expect", e],
                         capture_output=True, text=True)
    assert bad.returncode != 0 and "EXPECT MISMATCH" in (bad.stdout + bad.stderr)


def test_repair_apply_cli_expect_binds_review_file(tmp_path):
    run = make_run(tmp_path, names=("guest_count_growth", "guest_transactions_growth"))
    assert validate_cli(run).returncode == 0
    (run / "repair_candidates.json").write_text(json.dumps(
        {"count": 1, "clipped": 0, "candidates": [
            {"a": "guest_count_growth", "b": "guest_transactions_growth"}]}))
    review = {"reviews": [{"a": "guest_count_growth", "b": "guest_transactions_growth",
                           "verdict": "SAME", "why": "same"}]}
    rv_text = json.dumps(review, separators=(",", ":"))
    rp = run / "repair_review.json"
    rp.write_text(rv_text)
    e = f"rv=1,h32={h32(rv_text)}"
    ok = subprocess.run([PY, REPAIR, "apply", str(run), "--review", str(rp), "--expect", e],
                        capture_output=True, text=True)
    assert ok.returncode == 0, ok.stdout + ok.stderr
    rp.write_text(rv_text.replace('"SAME"', '"same"'))
    bad = subprocess.run([PY, REPAIR, "apply", str(run), "--review", str(rp), "--expect", e],
                         capture_output=True, text=True)
    assert bad.returncode != 0 and "EXPECT MISMATCH" in (bad.stdout + bad.stderr)


# ================================================================ #2 chunk coverage (build_seed)

def menu(run, cid, ticker, names=("alpha_sales",)):
    (run / "menus").mkdir(exist_ok=True)
    (run / "menus" / f"{cid}.json").write_text(json.dumps(
        {"ticker": ticker, "chunk_id": cid,
         "candidates": [{"driver_name": n, "evidence_quote": "q", "source_type": "transcript",
                         "source_id": "e1", "date": "2026-01-01", "xbrl_or_null": "null"}
                        for n in names],
         "candidate_count": len(names), "skipped_count": 0, "notes": []}))


def chunk_file(run, cid):
    (run / "chunks").mkdir(exist_ok=True)
    (run / "chunks" / f"{cid}.json").write_text(json.dumps(
        {"ticker": cid.split("__")[0], "chunk_id": cid, "events": []}))


def build_seed_cli(run):
    return subprocess.run([PY, BUILD_SEED, str(run), "--industry", "T", "--slug", "t",
                           "--run-id", "r1"], capture_output=True, text=True)


def test_build_seed_fails_on_missing_chunk_menu(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    chunk_file(run, "AAA__chunk_001")
    chunk_file(run, "AAA__chunk_002")
    menu(run, "AAA__chunk_001", "AAA")                          # chunk_002 never read
    out = build_seed_cli(run)
    assert out.returncode != 0
    assert "AAA__chunk_002" in (out.stdout + out.stderr)


def test_build_seed_fails_on_stale_extra_menu(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    chunk_file(run, "AAA__chunk_001")
    menu(run, "AAA__chunk_001", "AAA")
    menu(run, "AAA__chunk_999", "AAA", names=("stale_name",))   # leftover from a prior attempt
    out = build_seed_cli(run)
    assert out.returncode != 0
    assert "AAA__chunk_999" in (out.stdout + out.stderr)


def test_build_seed_passes_with_full_chunk_coverage(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    chunk_file(run, "AAA__chunk_001")
    menu(run, "AAA__chunk_001", "AAA")
    out = build_seed_cli(run)
    assert out.returncode == 0, out.stdout + out.stderr


def test_build_seed_skips_check_without_chunks_dir(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    menu(run, "AAA__menu", "AAA")                               # legacy per-company layout
    out = build_seed_cli(run)
    assert out.returncode == 0, out.stdout + out.stderr


# ================================================================ #6 global-fold validator backstop

def test_global_fold_same_without_second_skeptic_flag_fails(tmp_path):
    p, c1, c2 = global_fold(tmp_path, with_flag=False)
    out = subprocess.run([PY, VALIDATOR, str(p / "seed.json"), str(p / "catalog.json"),
                          str(p / "approved.json"), "--fold", str(c1 / "catalog.json"),
                          str(c2 / "catalog.json"), "--review", str(p / "same_name_review.json"),
                          "--sidecars", str(p / "fold_sidecars.json")],
                         capture_output=True, text=True)
    assert out.returncode == 1
    assert "GLOBAL" in out.stdout and "oil_price" in out.stdout


def test_global_fold_same_with_second_skeptic_flag_passes(tmp_path):
    p, c1, c2 = global_fold(tmp_path, with_flag=True)
    out = subprocess.run([PY, VALIDATOR, str(p / "seed.json"), str(p / "catalog.json"),
                          str(p / "approved.json"), "--fold", str(c1 / "catalog.json"),
                          str(c2 / "catalog.json"), "--review", str(p / "same_name_review.json"),
                          "--sidecars", str(p / "fold_sidecars.json")],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr


# ================================================================ #8 scope pinning

def test_chunker_fails_when_sources_do_not_match_scope(tmp_path):
    from chunk_company_sources import chunk_run
    run = tmp_path / "run"
    (run / "sources").mkdir(parents=True)
    (run / "sources" / "AAA.json").write_text(json.dumps(
        {"ticker": "AAA", "fiscal_kpis": [], "events": []}))
    (run / "scope_resolved.json").write_text(json.dumps({"tickers": ["AAA", "BBB"]}))
    with pytest.raises(SystemExit, match="BBB"):
        chunk_run(run)


def test_chunker_passes_on_exact_scope_match_and_skips_without_file(tmp_path):
    from chunk_company_sources import chunk_run
    run = tmp_path / "run"
    (run / "sources").mkdir(parents=True)
    (run / "sources" / "AAA.json").write_text(json.dumps(
        {"ticker": "AAA", "fiscal_kpis": ["kpi_x"], "events": []}))
    (run / "scope_resolved.json").write_text(json.dumps({"tickers": ["AAA"]}))
    assert chunk_run(run)["per_ticker"] == {"AAA": 1}
    (run / "scope_resolved.json").unlink()                      # legacy: no scope file -> no check
    assert chunk_run(run)["per_ticker"] == {"AAA": 1}


def test_effective_tickers_subset_validation():
    from fetch_company_sources import effective_tickers
    scope = {"tickers": ["AAA", "BBB", "CCC"]}
    assert effective_tickers(scope, None) == ["AAA", "BBB", "CCC"]
    assert effective_tickers(scope, "bbb, aaa") == ["BBB", "AAA"]
    with pytest.raises(SystemExit, match="ZZZ"):
        effective_tickers(scope, "AAA,ZZZ")
    with pytest.raises(SystemExit, match="no tickers"):
        effective_tickers({"tickers": []}, None)


# ================================================================ review-round additions
# (#2 union ground truth: chunks/ dir ∪ chunks_manifest.json — the dir catches KPI-only
#  chunks that have no manifest rows; the manifest catches a chunk file deleted after
#  chunking. #7 python backstop: a NEW repair link must come from the suggested set.)

def test_build_seed_manifest_catches_deleted_chunk_file(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    chunk_file(run, "AAA__chunk_001")
    (run / "chunks_manifest.json").write_text(json.dumps(
        {"budget": 40000, "rows": [
            {"ticker": "AAA", "chunk_id": "AAA__chunk_001", "source_id": "e1"},
            {"ticker": "AAA", "chunk_id": "AAA__chunk_002", "source_id": "e2"}]}))
    menu(run, "AAA__chunk_001", "AAA")          # chunk_002's FILE was deleted post-chunking
    out = build_seed_cli(run)
    assert out.returncode != 0
    assert "AAA__chunk_002" in (out.stdout + out.stderr)


def test_build_seed_dir_catches_kpi_only_chunk_missing_from_manifest_rows(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    chunk_file(run, "AAA__chunk_001")            # KPI-only chunk: zero events = zero manifest rows
    chunk_file(run, "AAA__chunk_002")
    (run / "chunks_manifest.json").write_text(json.dumps(
        {"budget": 40000, "rows": [{"ticker": "AAA", "chunk_id": "AAA__chunk_002",
                                    "source_id": "e1"}]}))
    menu(run, "AAA__chunk_002", "AAA")           # only the manifest-listed chunk has a menu
    out = build_seed_cli(run)                    # the dir lane must still require chunk_001
    assert out.returncode != 0
    assert "AAA__chunk_001" in (out.stdout + out.stderr)


def test_repair_apply_rejects_never_suggested_pair(tmp_path):
    from repair_duplicates import apply as repair_apply
    run = make_run(tmp_path, names=("guest_count_growth", "guest_transactions_growth", "oil_price"))
    (run / "repair_candidates.json").write_text(json.dumps(
        {"count": 1, "clipped": 0, "candidates": [
            {"a": "guest_count_growth", "b": "guest_transactions_growth"}]}))
    rp = run / "repair_review.json"
    rp.write_text(json.dumps({"reviews": [
        {"a": "guest_count_growth", "b": "oil_price", "verdict": "SAME", "why": "x"}]}))
    with pytest.raises(SystemExit, match="never suggested"):
        repair_apply(run, rp)


def test_repair_apply_idempotent_even_when_candidates_exclude_linked_pair(tmp_path):
    # suggest() excludes already_linked pairs — a resume re-apply must NOT false-stop on that.
    from repair_duplicates import apply as repair_apply
    run = make_run(tmp_path, names=("guest_count", "customer_transactions"))
    (run / "repair_candidates.json").write_text(json.dumps(
        {"count": 1, "clipped": 0, "candidates": [
            {"a": "guest_count", "b": "customer_transactions"}]}))
    rp = run / "repair_review.json"
    rp.write_text(json.dumps({"reviews": [
        {"a": "guest_count", "b": "customer_transactions", "verdict": "SAME", "why": "x"}]}))
    repair_apply(run, rp)
    (run / "repair_candidates.json").write_text(json.dumps(
        {"count": 0, "clipped": 0, "candidates": []}))     # re-suggest now excludes the linked pair
    first = (run / "catalog.json").read_bytes()
    repair_apply(run, rp)                                   # idempotent no-op, NOT a false stop
    assert (run / "catalog.json").read_bytes() == first


def test_repair_apply_rejects_new_link_when_candidates_file_missing(tmp_path):
    # Escape-hatch closed (review round 2): a NEW link requires the code-suggested set on
    # disk — no repair_candidates.json = hard fail (already-linked resume stays exempt).
    from repair_duplicates import apply as repair_apply
    run = make_run(tmp_path, names=("guest_count", "customer_transactions"))
    rp = run / "repair_review.json"
    rp.write_text(json.dumps({"reviews": [
        {"a": "guest_count", "b": "customer_transactions", "verdict": "SAME", "why": "x"}]}))
    with pytest.raises(SystemExit, match="repair_candidates.json missing"):
        repair_apply(run, rp)


# ================================================================ final-gate round fixes
# (9-reviewer commit gate: SAME-excusal hole, approved-deletion bypass, mode-blind sidecar,
#  --expect self-disable. Each was proven live by a reviewer before being fixed here.)

def test_cli_same_reviewed_name_still_requires_gate_verdict(tmp_path):
    # SAME-kept records keep their gate verdicts in the real flow (the touches filter only
    # removes reshaped names) — so a SAME review must NOT excuse a missing gate verdict.
    run = tmp_path / "run"
    run.mkdir()
    seed = {"industry": "T", "catalog": [rec("alpha_sales"), rec("mixed_name")], "analysis": {}}
    (run / "seed.json").write_text(serialize(seed))
    (run / "decisions.json").write_text(serialize(
        {"gate_verdicts": admit_all(seed, but=("mixed_name",)), "approved_same_as": [],
         "approved_rewrites": [], "parked_rewrites": []}))
    (run / "review.json").write_text(serialize(
        {"reviews": [{"collision_name": "mixed_name", "verdict": "SAME", "why": "one meaning",
                      "refute_survived": True}], "split_map": []}))
    out = subprocess.run([PY, ASSEMBLE, str(run), "--review", "review.json"],
                         capture_output=True, text=True)
    assert out.returncode != 0
    assert "NO gate verdict" in (out.stdout + out.stderr) and "mixed_name" in (out.stdout + out.stderr)
    # with the gate verdict present it ships fine
    (run / "decisions.json").write_text(serialize(
        {"gate_verdicts": admit_all(seed), "approved_same_as": [],
         "approved_rewrites": [], "parked_rewrites": []}))
    ok = subprocess.run([PY, ASSEMBLE, str(run), "--review", "review.json"],
                        capture_output=True, text=True)
    assert ok.returncode == 0, ok.stdout + ok.stderr


def test_part_a_rejects_approved_deleted_after_validation(tmp_path):
    c1 = fold_child(tmp_path, "childA")
    (c1 / "approved.json").unlink()                  # deletion is a tamper too
    with pytest.raises(SystemExit, match="approved.json deleted"):
        part_a(tmp_path / "parent", "S", "sector",
               [c1, fold_child(tmp_path, "childB", names=("wage_inflation",))])


def test_validator_sidecar_records_fold_mode(tmp_path):
    run = make_run(tmp_path)
    validate_cli(run)
    assert json.loads((run / "validation_exit.json").read_text())["fold"] is False


def test_require_validated_demands_fold_mode_for_fold_parents(tmp_path):
    d = tmp_path / "parent"
    d.mkdir()
    (d / "catalog.json").write_text(serialize({"industry": "I", "catalog": [rec("oil_price")],
                                               "skips": [], "unresolved_rewrites": [],
                                               "unresolved_same_name": []}))
    (d / "fold_manifest.json").write_text(json.dumps({"children": []}))   # it IS a fold parent
    sc = {"exit": 0, "catalog_sha256": sha(d / "catalog.json"), "fold": False}
    (d / "validation_exit.json").write_text(json.dumps(sc))
    with pytest.raises(SystemExit, match="fold"):
        require_validated(d)
    sc["fold"] = True
    (d / "validation_exit.json").write_text(json.dumps(sc))
    require_validated(d)                              # D8-mode validation -> accepted


def test_require_validated_corrupt_sidecar_clean_message(tmp_path):
    d = tmp_path / "c"
    d.mkdir()
    (d / "catalog.json").write_text("{}")
    (d / "validation_exit.json").write_text("{corrupt")
    with pytest.raises(SystemExit, match="unreadable"):
        require_validated(d)


def test_verify_expect_requires_h32_and_rejects_empty(tmp_path):
    from assemble_catalog import verify_expect
    with pytest.raises(SystemExit, match="h32"):
        verify_expect("rv=1", '{"reviews":[1]}', {"rv": 1}, "TEST")
    with pytest.raises(SystemExit, match="h32"):
        verify_expect("", "whatever", {"rv": 99}, "TEST")


def test_repair_apply_rejects_empty_expect_string(tmp_path):
    run = make_run(tmp_path, names=("guest_count", "customer_transactions"))
    assert validate_cli(run).returncode == 0
    (run / "repair_candidates.json").write_text(json.dumps(
        {"count": 1, "clipped": 0, "candidates": [{"a": "guest_count", "b": "customer_transactions"}]}))
    rp = run / "repair_review.json"
    rp.write_text(json.dumps({"reviews": [{"a": "guest_count", "b": "customer_transactions",
                                           "verdict": "SAME", "why": "x"}]}))
    out = subprocess.run([PY, REPAIR, "apply", str(run), "--review", str(rp), "--expect", ""],
                         capture_output=True, text=True)
    assert out.returncode != 0 and "h32" in (out.stdout + out.stderr)
