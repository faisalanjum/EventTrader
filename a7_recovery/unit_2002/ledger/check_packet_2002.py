"""Read-only altered-package and closeout tests over saved TEST evidence."""
import copy
import json
import os
import sys

sys.path.insert(0, "/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_2002/owner")
import a4_source_closure as CL

SK, K = CL.SK, CL.K
tag = os.environ.get("A7_SAVED_TAG", "codex_final2002_qualified")
base = os.path.dirname(CL.PKG_DIR)
review = os.path.join(base, "review_" + tag)
review_pkg = os.path.join(base, "closure_pkg_" + tag)
final = os.path.join(base, "final_" + tag)
final_pkg = os.path.join(base, "final_pkg_" + tag)
manifest_path = os.path.join(final_pkg, SK.MANIFEST_NAME)
fin_path = os.path.join(review, K.FINALIZATION_NAME)
cases = []


def check(name, ok, detail=None):
    cases.append({"case": name, "ok": bool(ok), "detail": detail})


def gate():
    return CL.signing_checks(review, review_pkg, key_run=final,
                             key_package=final_pkg)


check("positive before package changes", gate()["ok"])
manifest = SK._load(manifest_path)
original = SK._load
for field in ("bound", "role_sha256", "output_section_sha256", "prefix_sha256",
              "requested_key_role", "counts", "hard_review", "budget",
              "capacity", "call_order", "events"):
    altered = copy.deepcopy(manifest)
    altered[field] = {} if isinstance(altered[field], dict) else []
    SK._load = lambda path, _doc=altered: (
        copy.deepcopy(_doc) if path == manifest_path else original(path))
    try:
        result = gate()
        check("changed final manifest field refuses: " + field,
              not result["ok"], result["stops"][:2])
    finally:
        SK._load = original

fin = K._load(fin_path)
original = K._load
variants = {
    "receipt identity": dict(fin, receipt_sha256="TEST-not-the-receipt"),
    "completion": dict(fin, primary_complete=False),
    "run problems": dict(fin, problems=["TEST-unresolved-run-problem"]),
    "scheduled count": dict(fin, ledger=dict(fin["ledger"], scheduled=0)),
}
for name, altered in variants.items():
    K._load = lambda path, _doc=altered: (
        copy.deepcopy(_doc) if path == fin_path else original(path))
    try:
        refused = False
        try:
            with CL.final_scope(review, review_pkg):
                pass
        except ValueError:
            refused = True
        check("changed review closeout refuses: " + name, refused)
    finally:
        K._load = original

check("positive after all package changes", gate()["ok"])
print(json.dumps({"test_only": True, "model_calls": 0, "cases": cases,
                  "passed": sum(c["ok"] for c in cases), "total": len(cases)},
                 indent=1))
raise SystemExit(0 if all(c["ok"] for c in cases) else 3)
