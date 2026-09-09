"""Record this checkpoint's source inventory and evidence hashes; no execution.

This is a review recorder, not an application layer or a dependency resolver.
The original failure census and the raw test records remain separate evidence.
"""
import ast
import hashlib
import json
from pathlib import Path
import re

U = Path(__file__).resolve().parent
REC = U.parents[1]
OLD = REC / "a7_recovery/unit_1957/view/tree/harness_g1v3"
NEW = U / "harness_g1v3"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p else None


def files(root):
    return {str(p.relative_to(root)): p for p in root.rglob("*")
            if p.is_file() and not {"__pycache__", ".pytest_cache"} & set(p.parts)
            and p.suffix != ".pyc"}


def definitions(path):
    if path is None or path.suffix != ".py":
        return {}
    return {n.name: n for n in ast.parse(path.read_text()).body
            if isinstance(n, (ast.FunctionDef, ast.ClassDef))}


old, new = files(OLD), files(NEW)
changes = []
for rel in sorted(old.keys() | new.keys()):
    if sha(old.get(rel)) == sha(new.get(rel)):
        continue
    a, b = definitions(old.get(rel)), definitions(new.get(rel))
    changes.append({"path": rel, "old_sha256": sha(old.get(rel)),
                    "new_sha256": sha(new.get(rel)),
                    "changed": sorted(k for k in a.keys() & b.keys()
                                      if ast.dump(a[k]) != ast.dump(b[k])),
                    "added": sorted(b.keys() - a.keys()),
                    "removed": sorted(a.keys() - b.keys())})

families, owner = {}, None
for line in (U / "PLAN.md").read_text().splitlines():
    if line.startswith("#### H/"):
        owner = line[len("#### H/"):]
    elif owner and line.startswith("Required test families: "):
        families[owner] = line.split(": ", 1)[1].rstrip(".")

inventory, duplicate_bodies = [], {}
for rel, family in families.items():
    for name, node in definitions(new[rel]).items():
        inventory.append({"file": rel, "function_or_class": name,
                          "line": node.lineno, "end_line": node.end_lineno,
                          "if_nodes": sum(isinstance(n, ast.If) for n in ast.walk(node)),
                          "exception_handlers": sum(isinstance(n, ast.ExceptHandler)
                                                    for n in ast.walk(node)),
                          "test_families": family})
        duplicate_bodies.setdefault(ast.dump(node), []).append(rel + "::" + name)

code = json.loads((U / "CODE_FILES.json").read_text())
assert all(sha(REC / row["path"]) == row["sha256"] for row in code)
tests = json.loads((U / "FINAL_TEST_CASES.json").read_text())
ids = [r["id"] for rows in tests.values() for r in rows]
assert len(ids) == len(set(ids))
assert {i.split("::", 1)[0] for i in ids} == {
    p.name for p in NEW.glob("test_*.py")}
report = {"inventory_scope": "Current rule-owner AST and requirement families; not line/branch coverage.",
          "old_file_count": len(old), "new_file_count": len(new), "changes": changes,
          "rule_owner_inventory": inventory,
          "exact_repeated_current_bodies": [v for v in duplicate_bodies.values() if len(v) > 1],
          "test_modules": sorted({i.split("::", 1)[0] for i in ids}),
          "collected_tests": len(ids), "passed": sum(r["status"] == "passed"
              for rows in tests.values() for r in rows),
          "skipped": [r for rows in tests.values() for r in rows if r["status"] == "skipped"]}
with (U / "REVIEW_INVENTORY.json").open("x") as stream:
    json.dump(report, stream, indent=2)
    stream.write("\n")
print(json.dumps({k: report[k] for k in ("old_file_count", "new_file_count",
                                        "collected_tests", "passed")}))
