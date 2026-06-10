"""TDD for slice_seed.py — the §11.11 deterministic seed slicer extracted VERBATIM from the
reconcile.js heredoc into a tested CLI. ZERO AI, ZERO judgment: name-sorted contiguous review
batches under the SEED_MAX caps (<=400 records, <=300000 chars/batch), complete partition,
order preserved, a single fat record goes alone (never split a record)."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

WORKFLOWS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOWS))

from slice_seed import MAX_CHARS, MAX_RECORDS, rec_chars, slice_records  # noqa: E402

PY = sys.executable
CLI = str(WORKFLOWS / "slice_seed.py")


def ref(company="AAA", st="transcript", sid="e1", date="2026-01-01", quote=None):
    return {"company": company, "source_type": st, "source_id": sid,
            "date": date, "quote": quote if quote is not None else f"quote {sid}"}


def rec(name, refs=None):
    refs = refs if refs is not None else [ref(sid=f"ev_{name}")]
    return {"driver_name": name, "canonical_name": name,
            "companies": sorted({r["company"] for r in refs}),
            "evidence_refs": refs, "same_as_variants": [],
            "optional_links": {"xbrl_concept": None, "xbrl_member": None, "guidance_ref": None}}


def write_seed(run_dir, records, industry="Test"):
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "seed.json").write_text(json.dumps(
        {"industry": industry, "catalog": records, "analysis": {}}))
    return run_dir


def cli(run_dir):
    return subprocess.run([PY, CLI, str(run_dir)], capture_output=True, text=True)


def batch_records(run_dir, files):
    out = []
    for f in files:
        out.append(json.loads(Path(f).read_text())["catalog"])
    return out


# ---------------------------------------------------------------- pure-function invariants

def test_slice_records_partitions_under_record_cap():
    recs = [rec(f"d_{i:03d}") for i in range(401)]
    batches = slice_records(recs)
    assert len(batches) == 2
    assert all(len(b) <= MAX_RECORDS for b in batches)
    # complete partition, order preserved
    flat = [r for b in batches for r in b]
    assert flat == recs


def test_slice_records_partitions_under_char_cap():
    # each record ~ a fixed chunk; pick a count that trips chars before records
    recs = [rec(f"d_{i:03d}", refs=[ref(sid=f"e{i}", quote="x" * 4000)]) for i in range(120)]
    batches = slice_records(recs)
    assert len(batches) >= 2
    assert all(rec_chars(b) <= MAX_CHARS for b in batches)
    flat = [r for b in batches for r in b]
    assert flat == recs


def test_slice_records_name_sorted_contiguous():
    recs = [rec(f"d_{i:03d}") for i in range(450)]
    batches = slice_records(recs)
    flat = [r for b in batches for r in b]
    # contiguous slices: each batch is a prefix-continuation of the input order
    assert flat == recs
    # each batch internally keeps the input order
    for b in batches:
        names = [r["driver_name"] for r in b]
        assert names == sorted(names) or names == [r["driver_name"] for r in recs
                                                   if r["driver_name"] in names]


def test_single_fat_record_goes_alone(tmp_path):
    # one record bigger than the char cap on its own -> its own batch (never split)
    fat = rec("fat_one", refs=[ref(sid="big", quote="z" * (MAX_CHARS + 100))])
    recs = [rec("a_small"), fat, rec("z_small")]
    batches = slice_records(recs)
    # the fat record is isolated in a batch of size 1
    fat_batches = [b for b in batches if any(r["driver_name"] == "fat_one" for r in b)]
    assert len(fat_batches) == 1 and len(fat_batches[0]) == 1
    flat = [r for b in batches for r in b]
    assert flat == recs


# ---------------------------------------------------------------- CLI contract

def test_cli_writes_named_batches_and_prints_summary(tmp_path):
    run = write_seed(tmp_path / "run", [rec(f"d_{i:03d}") for i in range(401)])
    out = cli(run)
    assert out.returncode == 0, out.stderr
    summary = json.loads(out.stdout.strip().splitlines()[-1])
    assert summary["ok"] is True
    files = summary["files"]
    assert len(files) == 2
    assert [Path(f).name for f in files] == ["seed_batch_001.json", "seed_batch_002.json"]
    assert all(Path(f).exists() for f in files)
    # concatenation of batch records == seed records exactly
    seed_recs = json.loads((run / "seed.json").read_text())["catalog"]
    flat = [r for b in batch_records(run, files) for r in b]
    assert flat == seed_recs
    # every batch under caps
    for b in batch_records(run, files):
        assert len(b) <= MAX_RECORDS and rec_chars(b) <= MAX_CHARS


def test_cli_single_batch_when_under_caps(tmp_path):
    run = write_seed(tmp_path / "run", [rec("a_one"), rec("b_two")])
    out = cli(run)
    assert out.returncode == 0, out.stderr
    summary = json.loads(out.stdout.strip().splitlines()[-1])
    assert summary["ok"] is True and len(summary["files"]) == 1
    assert Path(summary["files"][0]).name == "seed_batch_001.json"


def test_cli_notes_mention_fat_record(tmp_path):
    fat = rec("fat_one", refs=[ref(sid="big", quote="z" * (MAX_CHARS + 100))])
    run = write_seed(tmp_path / "run", [rec("a_small"), fat])
    out = cli(run)
    assert out.returncode == 0, out.stderr
    summary = json.loads(out.stdout.strip().splitlines()[-1])
    assert "fat_one" in summary["notes"] or "oversize" in summary["notes"].lower()


# ---------------------------------------------------------------- real-seed proof (read-only)

REAL_SEED = (WORKFLOWS.parent / "runs" / "2026-06-09_190054_restaurants" / "seed.json")


def test_real_seed_slices_into_multiple_batches(tmp_path):
    if not REAL_SEED.exists():
        pytest.skip(f"real seed not present: {REAL_SEED}")
    run = tmp_path / "run"
    run.mkdir()
    (run / "seed.json").write_text(REAL_SEED.read_text())   # COPY — never touch the real dir
    out = cli(run)
    assert out.returncode == 0, out.stderr
    summary = json.loads(out.stdout.strip().splitlines()[-1])
    files = summary["files"]
    assert len(files) >= 2
    seed_recs = json.loads((run / "seed.json").read_text())["catalog"]
    flat = [r for b in batch_records(run, files) for r in b]
    assert flat == seed_recs          # complete partition, order preserved
    for b in batch_records(run, files):
        # invariant holds except a lone fat record (none expected here, but allow it)
        assert len(b) <= MAX_RECORDS
        assert rec_chars(b) <= MAX_CHARS or len(b) == 1
