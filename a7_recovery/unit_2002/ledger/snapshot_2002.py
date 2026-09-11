"""Emit the exact review snapshot. Read-only; no model or Git operation."""
import ast
import hashlib
import json
from pathlib import Path

root = Path("/home/faisal/EventMarketDB-driver-recovery")
a7 = root / "a7_recovery"
unit = a7 / "unit_2002"
official = Path("/home/faisal/.claude/projects")
files = set()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(path):
    files.update(p for p in path.rglob("*") if p.is_file()
                 and "__pycache__" not in p.parts)


for name in ("owner", "ledger"):
    tree(unit / name)
files.update((unit / "map_lifecycle_2002.tsv", unit / "REVIEW.md"))
tree(a7 / "unit_1997" / "owner")
tree(a7 / "unit_1997" / "harness_g1v3")
files.add(a7 / "unit_2001/tests/synthetic_reading.py")
files.add(a7 / "unit_1995/owner/test_a4_source_key.py")
for name in ("probe_closure_interactions_2001.py", "probe_closure_run_error_2000.py",
             "run_source_suite_1997.py"):
    files.add(a7 / "codex_review_1989" / name)
tags = ("codex_final2002_qualified", "codex_lifecycle2002_qualified")
evidence_dirs = sorted(p for p in (unit / "key_closure").iterdir()
                       if p.is_dir() and any(p.name.endswith(t) for t in tags))
for path in evidence_dirs:
    tree(path)


def native_paths(state):
    rel = state.relative_to(official)
    copied = unit / "TEST_projects" / rel
    doc = json.loads(copied.read_text())
    result = [(state, copied)]
    for row in doc.get("workflowProgress", []):
        if row.get("type") == "workflow_agent":
            sub = (state.parent.parent / "subagents/workflows" / state.stem
                   / ("agent-%s.jsonl" % row["agentId"]))
            result.append((sub, unit / "TEST_projects" / sub.relative_to(official)))
    return result


native = set()
for path in evidence_dirs:
    for receipt in path.rglob("receipt.json"):
        for state in json.loads(receipt.read_text()).get("states", []):
            native.update(copy for _real, copy in native_paths(Path(state)))
files.update(native)
initial = a7 / "unit_1997/key_source_only/source_only_1997_collect"
tree(initial)
preserved = []
for state in json.loads((initial / "receipt.json").read_text())["states"]:
    for real, copied in native_paths(Path(state)):
        assert real.read_bytes() == copied.read_bytes(), str(copied)
        files.update((real, copied))
        preserved.append({"real": str(real), "copy": str(copied), "sha256": sha(real)})

attempts = ["codex_final2002_qualified", "codex_lifecycle2002_qualified",
            "codex_scope2002_qualified", "codex_packet2002_qualified",
            "codex_composition2002_qualified", "codex_sourcesuite2002_a"]
logs = []
for tag in attempts:
    folder = a7 / "unit_1947/logs" / ("attempt_" + tag)
    assert (folder / "exit").read_text().strip() == "0", tag
    assert not (folder / "stderr.txt").read_bytes(), tag
    tree(folder)
    logs.append({"attempt": tag, "exit": 0,
                 "stdout_sha256": sha(folder / "stdout.txt")})

owner = unit / "owner/a4_source_closure.py"
functions = [{"name": n.name, "line": n.lineno}
             for n in ast.parse(owner.read_text()).body
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
pins = [{"path": str(p), "sha256": sha(p), "bytes": p.stat().st_size}
        for p in sorted(files)]
print(json.dumps({"kind": "A7 source-only closure CODE review, not a real signed key",
                  "owner_sha256": sha(owner), "model_calls": 0,
                  "test_runs": logs, "functions_from_live_code": functions,
                  "preserved_original_native_files": preserved,
                  "qualified_TEST_native_files": len(native),
                  "files": pins, "file_count": len(pins),
                  "limits": ["Core independent review pending",
                             "No real blind-review or final-key call made here",
                             "No semantic truth or production deployment qualified",
                             "A5/A6 new-key binding is the next separate gate"]},
                 indent=1))
