"""Checkpoint-only export proof, following checkpoint_1943's materialized check.

No staging, model calls or production writes. Export existing committed support
code, overlay the exact proposed code manifest, then check cold imports and
dynamic/sibling reads in a fresh process. Experiment data is a separate pinned
input, not claimed to be distributed by this code-only checkpoint.
"""
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REC = HERE.parents[1]
VENV = Path(sys.prefix).resolve()
HREL = Path("a7_recovery/grader_20260909/harness_g1v3")
LREL = Path("a7_recovery/unit_1957/lock_owners")
SUPPORT = ("driver", "scripts", ".claude/skills/earnings-orchestrator/scripts",
           "data/driver_catalog_seed")
ENTRIES = ("raw_transport", "a1_reader", "kf_lint", "audit_worker_access",
           "build_launch_manifest", "build_exp5_contract", "build_inventory_review",
           "build_kfields_key", "build_kfields_hard_review", "build_kfields_hr_correction",
           "build_kfields_final", "build_kfields_final_targeted", "build_a5_exp5_kit",
           "a6_launch_freeze", "a7_prepared_run", "a7_g1_build", "a7_g23_build",
           "a7_g23_run", "a7_g1_complete_v2", "a7_reference_inventory",
           "a7_key_correction", "a7_source_meta", "a7_conservation",
           "validate_benchmark_inventory", "signer_proof", "build_final_key_candidate",
           "build_final_key_lock")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def child(export, spec):
    h = export / HREL
    sys.dont_write_bytecode = True
    sys.path = [str(h), str(export / LREL), str(export)] + [
        p for p in sys.path if p and (Path(p).is_relative_to(VENV)
                                      or not p.startswith("/home/faisal/EventMarketDB"))]
    for row in spec:
        assert sha(export / row["path"]) == row["sha256"], row["path"]
    loaded = {name: importlib.import_module(name) for name in ENTRIES}
    # Compile script-only owners without executing their harvesting/publication.
    for row in spec:
        p = export / row["path"]
        if p.suffix == ".py":
            compile(p.read_bytes(), str(p), "exec")
    g, b = loaded["a7_g1_build"], loaded["a7_g23_build"]
    g.owner_hashes()
    scorer = h / "scorers/score_exp5_current.py"
    s = b.bind_grading_scorer(str(scorer), sha(scorer))
    assert b.meaning_fields() == s.MEANING_FIELDS
    assert b.extras_buckets() == list(s.EXTRAS_BUCKETS)
    assert set(s.field_accounting())
    assert b.meaning_rules() and b.extras_rules()
    # The actual route is also exercised, with a nonempty prepared fact. The
    # ordinary suite's public-route controls carry the semantic expectations.
    from driver.core.prepared_fact_v2 import ITEM_FIELDS
    quote = "The TEST metric was 5 million dollars in the stated quarter."
    slot = {"value": 5, "scale_multiplier": 1, "unit_scale_evidence": "million"}
    item = dict.fromkeys(ITEM_FIELDS)
    item.update(driver_name="revenue", driver_state="reported", quote=quote,
                measurement_raw_spans=[], slice_parts=[], level_low=slot,
                level_high=slot, level_shape_hint="point", level_unit="m_usd",
                time_type="duration", period_start_date="2026-01-01",
                period_end_date="2026-03-31")
    fact = {"fact_type": "metric", "part_ref": "p01",
            "occurrence_in_part": None, "per_x": None, "item": item}
    arm = {"E1": {"facts": [fact]}}
    event = {"source_id": "E1", "event_time": "2026-04-23T16:00:00-04:00",
             "source_type": "8k", "ticker": "AAPL", "fye_month": 12,
             "text_parts": [{"part": "p01", "content": quote}], "items": []}
    route = {"E1": s.route_reply(dict(arm["E1"], source_id="E1"), event,
                                 str(export / "TEST_route_audit"))}
    assert route["E1"]["result"]["items"][0]["decision"] == "written"
    gold = dict(fact, du_worthy=True, gold_extra={"expectation_comparison_present": False},
                ambiguity_note=None)
    score = s.score_arm({"E1": [gold]}, arm,
                        {"E1": {"event_date": "2026-04-23", "fye_month": 12}}, route=route,
                        grader_verdicts={("E1", 0): dict.fromkeys(s.MEANING_FIELDS, True)})
    assert score["PASS"] is True and score["matched"] == score["gold_n"] == 1
    loaded["bound_current_scorer"] = s
    loaded.update({n: m for n, m in sys.modules.items() if n != "__main__"
                   and getattr(m, "__file__", "")
                   and not Path(m.__file__).is_relative_to(VENV)
                   and (str(m.__file__).startswith(str(export))
                        or str(m.__file__).startswith("/home/faisal/EventMarketDB"))})
    expected = {row["path"]: row["sha256"] for row in spec}
    for line in subprocess.check_output([
            "git", "ls-tree", "-r", "HEAD", "--", *SUPPORT], cwd=REC, text=True).splitlines():
        meta, rel = line.split("\t", 1)
        blob = subprocess.check_output(["git", "cat-file", "blob", meta.split()[2]], cwd=REC)
        expected[rel] = hashlib.sha256(blob).hexdigest()
    measured = {}
    for name, module in loaded.items():
        path = Path(module.__file__).resolve()
        assert path.is_relative_to(export), (name, str(path), "escaped the export")
        rel = str(path.relative_to(export))
        assert sha(path) == expected[rel], (name, rel, "not a proposed/committed blob")
        measured[name] = {"path": rel, "sha256": sha(path)}
    return {"kind": "PROSPECTIVE_CODE_EXPORT_NOT_EXPERIMENT_QUALIFICATION",
            "entries": list(ENTRIES), "files": len(spec), "loaded": measured,
            "nonempty_route_decision": "written", "synthetic_score_only": score,
            "all_ok": True}


if __name__ == "__main__":
    if sys.argv[1] == "--child":
        result = child(Path(sys.argv[2]), json.loads(Path(sys.argv[3]).read_text()))
        print(json.dumps(result, indent=2))
    else:
        spec_path = HERE / "CODE_FILES.json"
        spec = json.loads(spec_path.read_text())
        out = HERE / "exports" / sys.argv[1]
        out.mkdir(parents=True, exist_ok=False)
        archive = subprocess.Popen(["git", "archive", "HEAD", *SUPPORT], cwd=REC,
                                   stdout=subprocess.PIPE)
        extracted = subprocess.run(["tar", "-x", "-C", str(out)], stdin=archive.stdout)
        archive.stdout.close()
        assert archive.wait() == extracted.returncode == 0
        for row in spec:
            source, target = REC / row["path"], out / row["path"]
            assert sha(source) == row["sha256"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        env = {k: v for k, v in os.environ.items() if not k.startswith("A7_")}
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        command = [sys.executable, "-B", str(Path(__file__).resolve()),
                   "--child", str(out), str(spec_path)]
        result = subprocess.run(command, cwd=out, env=env, capture_output=True, text=True)
        (out.parent / (out.name + ".stdout.json")).write_text(result.stdout)
        (out.parent / (out.name + ".stderr.txt")).write_text(result.stderr)
        (out.parent / (out.name + ".exit.json")).write_text(json.dumps({
            "command": command, "exit": result.returncode,
            "manifest_sha256": sha(spec_path)}) + "\n")
        print(result.stderr[-2000:] if result.returncode else "Export check passed")
        raise SystemExit(result.returncode)
