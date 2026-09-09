"""Prepare a fresh durable test view using the existing recovery boundary.

Derived from codex_a7_20260909/prepare_attempt.py. The intentional differences
are the editable harness copy and the complete current driver dependency tree.
Historical evidence and its pins stay unchanged. No model is invoked.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
RECOVERY = HERE.parents[1]
UNIT = RECOVERY / "a7_recovery/unit_1957"
BOUNDARY = RECOVERY / (
    "a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/"
    "out/a4_final_lock_1683/launcher")
sys.path.insert(0, str(BOUNDARY))
import boundary as B

BASELINE_SHA = "28a8d99ff230fefbb858cab890e4ffbb9745cafc5388ae5b23720eff3ea8dc72"
HARNESS = HERE / "harness_g1v3"


def initialize():
    source = UNIT / "view/tree/harness_g1v3"
    assert B.source_sha(str(source)) == BASELINE_SHA, "original harness drift"
    assert not HARNESS.exists(), "working copy already exists"
    shutil.copytree(source, HARNESS)
    assert B.source_sha(str(HARNESS)) == BASELINE_SHA
    return {"source": str(source), "candidate": str(HARNESS),
            "initial_sha256": BASELINE_SHA}


def prepare(name, payload, native, key_fixture, reuse=None, historical=False):
    assert name and name.replace("_", "").isalnum(), "simple name required"
    payload = payload.resolve()
    assert payload.is_file() and payload.is_relative_to(RECOVERY)
    destination = HERE / "attempts" / name
    map_path = UNIT / ("map_codex_grader_%s.tsv" % name)
    assert HARNESS.is_dir(), "initialize the working copy first"
    assert not destination.exists() and not map_path.exists(), "attempt exists"
    template = UNIT / ("map_1957_test.tsv" if key_fixture else "map_1957_cand.tsv")
    rows = B.read_map(str(template))
    assert not B.validate(rows), "template input changed"
    destination.mkdir(parents=True)
    harness_snapshot = destination / "view/harness_g1v3"
    shutil.copytree(HARNESS, harness_snapshot)
    original_payload = payload
    payload = destination / payload.name
    shutil.copy2(original_payload, payload)
    legacy = RECOVERY / "a7_recovery/unit_1771/tree/.claude/plans/Drivers/experiments/harness_g1v3"
    if historical:
        # Frozen TEST-only artifacts, not a reactivation of the old launcher.
        names = ("exp5_prompt_producer.v2.md", "frozen_proof_r15.txt",
                 "step1_inventory.json", "launch_exp5_readers.workflow.js")
        assert B.file_sha(str(legacy / names[-1])) == (
            "0713ea41677bb1c5126dcd88714a66d3663a2578516688732acf9098ebf7b105")
        for name0 in names:
            assert not (harness_snapshot / name0).exists()
            shutil.copy2(legacy / name0, harness_snapshot / name0)
    replaced = []
    for row in rows:
        if row["logical"].endswith("/bench_1306"):
            # The preserved bench has no scripts/ mountpoint. Add it to one
            # private copy, never to the original read-only evidence tree.
            bench = HERE / "bench"
            if not bench.exists():
                shutil.copytree(row["source"], bench)
                (bench / "scripts").mkdir()
            (bench / ".claude/skills/earnings-orchestrator/scripts").mkdir(
                parents=True, exist_ok=True)
            (bench / "data/driver_catalog_seed").mkdir(parents=True, exist_ok=True)
            row.update(source=str(bench), sha=B.source_sha(str(bench)))
        elif historical and row["logical"].endswith("/bench_1306/.claude/plans/Drivers/experiments"):
            private = destination / "view/experiments"
            shutil.copytree(row["source"], private)
            for name0 in ("inventory_review", "kfields_hard_review"):
                (private / name0).mkdir(exist_ok=True)
            row.update(source=str(private), sha=B.source_sha(str(private)))
        elif row["logical"].endswith("/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"):
            replaced.append(dict(row))
            row.update(source=str(harness_snapshot),
                       sha=B.source_sha(str(harness_snapshot)))
        elif row["logical"].endswith("/bench_1306/driver/core"):
            replaced.append(dict(row))
            # Serve the complete package at its actual import root. Mounting
            # only 16 old core files hid function-local imports and fixes.
            row.update(logical=row["logical"][:-len("/core")],
                       source=str(RECOVERY / "driver"),
                       sha=B.source_sha(str(RECOVERY / "driver")))
    assert len(replaced) == 2, replaced
    bench_logical = next(r["logical"] for r in rows
                         if r["logical"].endswith("/bench_1306"))
    support = RECOVERY / "scripts"
    rows.append(dict(logical=bench_logical + "/scripts", source=str(support),
                     sha=B.source_sha(str(support)), mode="ro"))
    support_rel = ".claude/skills/earnings-orchestrator/scripts"
    support = RECOVERY / support_rel
    rows.append(dict(logical=bench_logical + "/" + support_rel, source=str(support),
                     sha=B.source_sha(str(support)), mode="ro"))
    support = RECOVERY / "data/driver_catalog_seed"
    rows.append(dict(logical=bench_logical + "/data/driver_catalog_seed",
                     source=str(support), sha=B.source_sha(str(support)), mode="ro"))
    if historical:
        scratch = bench_logical.rsplit("/", 1)[0]
        experiments = bench_logical + "/.claude/plans/Drivers/experiments"
        sources = (
            (str(legacy), "/tmp/a7_historical_harness"),
            (str(legacy), experiments + "/harness"),
            (str(RECOVERY / "a3_recovery/regen_1541/bench/.claude/plans/Drivers/experiments/inventory_review"), experiments + "/inventory_review"),
            (str(RECOVERY / "a3_recovery/regen_1541/bench/.claude/plans/Drivers/experiments/invrev_run4"), scratch + "/invrev_run4"),
            (str(RECOVERY / "a4_recovery/regen_1566/evidence/replay_experiments/kfields_hard_review"), experiments + "/kfields_hard_review"),
        )
        for source, logical in sources:
            if native and logical != "/tmp/a7_historical_harness":
                # Current key evidence already carries its own canonical
                # dependencies. Old contract tests may read retired bytes at
                # the explicit historical path, never replace those owners.
                continue
            assert not any(r["logical"] == logical for r in rows), logical
            rows.append(dict(logical=logical, source=source,
                             sha=B.source_sha(source), mode="ro"))
    if key_fixture:
        # The native 1957 TEST signer proof, not the older 1942 fixture.
        approved = UNIT / "logs/life_native5/candidate_owed_002"
        proof = json.loads((UNIT / "logs/attempt_signC/COMPACT_signC.json").read_text())
        assert proof["all_green"] and proof["lock_exit"] == 0
        for row in rows:
            if row["logical"] in (
                    "/tmp/a7_approved_key/a4_final_key_lock.json",
                    "/tmp/a7_approved_key/a4_final_key_lock_receipt.json"):
                artifact_name = Path(row["logical"]).name
                assert B.file_sha(str(approved / artifact_name)) == proof[artifact_name]
                row.update(source=str(approved / artifact_name), sha=proof[artifact_name])
            elif row["logical"] == "/tmp/a7_approved_key/ordinary_bound.json":
                source = UNIT / "logs/ordinary_bound_1957.json"
                row.update(source=str(source), sha=B.file_sha(str(source)))
    if native:
        native_rows = [r for r in B.read_map(str(UNIT / "map_1957_test.tsv"))
                       if r["logical"] == "/tmp/a7_lane_input_profiles.json"]
        assert len(native_rows) == 1 and native_rows[0]["mode"] == "ro"
        existing = [r for r in rows if r["logical"] == native_rows[0]["logical"]]
        assert not existing or existing == native_rows
        if not existing:
            rows.extend(native_rows)
    copied = {}
    for row in rows:
        if row["mode"] != "rw":
            continue
        source = Path(row["source"])
        prefix = template.parent / "out_cand"
        relative = (source.relative_to(prefix) if source.is_relative_to(prefix)
                    else source.relative_to(template.parent))
        target = destination / relative
        if source not in copied:
            target.parent.mkdir(parents=True, exist_ok=True)
            if key_fixture and row["logical"] == "/tmp/a7_logs_1781":
                target.mkdir()
                # Only the reused complete key lineage is required, not every
                # failed or unrelated test attempt in the old logs directory.
                lineage = (HERE / "attempts" / reuse / "logs" if reuse else source)
                shutil.copytree(lineage / "life_native5", target / "life_native5")
            elif source.is_dir():
                shutil.copytree(source, target)
            else:
                shutil.copy2(source, target)
            copied[source] = target
        row["source"] = str(copied[source])
    if reuse:
        assert key_fixture and reuse.replace("_", "").isalnum()
        saved = HERE / "attempts" / reuse / "logs"
        proof = saved / ("attempt_grader_" + reuse)
        assert (proof / "OFFLINE_PATH.json").is_file(), "complete TEST proof required"
        for source, logical in (
                (proof, "/tmp/a7_logs_1781/attempt_grader_" + reuse),):
            rows.append(dict(logical=logical, source=str(source),
                             sha=B.source_sha(str(source)), mode="ro"))
    assert not B.validate(rows)
    with map_path.open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write("\t".join(row[k] for k in
                                   ("logical", "source", "sha", "mode")) + "\n")
    freeze = {
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                         cwd=RECOVERY, text=True).strip(),
        "launch_environment": {"CLAUDE_CODE_MAX_OUTPUT_TOKENS":
                               os.environ.get("CLAUDE_CODE_MAX_OUTPUT_TOKENS")},
        "template": str(template), "template_sha256": B.file_sha(str(template)),
        "map": str(map_path), "map_sha256": B.file_sha(str(map_path)),
        "payload": str(payload), "payload_sha256": B.file_sha(str(payload)),
        "original_payload": str(original_payload), "historical_test_artifacts": historical,
        "runner_sha256": B.file_sha(str(UNIT / "ledger/run_1957.sh")),
        "replaced_rows": replaced,
        "inputs": [dict(row, measured_sha256=B.source_sha(row["source"]))
                   for row in rows],
    }
    with (destination / "FREEZE.json").open("x", encoding="utf-8") as stream:
        json.dump(freeze, stream, indent=2)
        stream.write("\n")
    return {"map": str(map_path), "rows": len(rows), "output": str(destination),
            "command": ["bash", str(UNIT / "ledger/run_1957.sh"), map_path.name,
                        os.path.relpath(payload, UNIT / "ledger"),
                        "grader_" + name, "5400"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initialize", action="store_true")
    parser.add_argument("--native", action="store_true")
    parser.add_argument("--key-fixture", action="store_true")
    parser.add_argument("--historical", action="store_true",
                        help="serve the exact retired artifacts for isolated legacy tests")
    parser.add_argument("--reuse", help="completed no-AI path to serve read-only")
    parser.add_argument("name", nargs="?")
    parser.add_argument("payload", nargs="?", type=Path)
    args = parser.parse_args()
    if args.initialize:
        assert args.name is None and args.payload is None
        result = initialize()
    else:
        assert args.name and args.payload
        result = prepare(args.name, args.payload, args.native, args.key_fixture,
                         args.reuse, args.historical)
    print(json.dumps(result, indent=2))
