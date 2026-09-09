# -*- coding: utf-8 -*-
"""THE ONE AUTHORIZED CORRECTION, proved RED then GREEN (Codex SEQ 1943 item 1).

s2_g23_native_1942.py decided whether a kind's population was empty with

    rows = kdoc.get("rows") or []

but `a7_g23_run.kind_candidate` publishes the batches under `batch_rows`. The
only top-level `rows` in that document is nested inside `launchers`, so the
top-level lookup is always None and EVERY kind document is called empty -
including ones carrying dozens of batches.

The corrected statement reads the field the schema actually owns:

    rows = kdoc["batch_rows"]

and it subscripts rather than defaulting: a document missing the required
field is a refusal, not an empty population.

The four documents are the real ones - unit_1876's two preserved NONEMPTY
kind candidates and unit_1942's two genuinely EMPTY ones - plus a fifth built
by deleting the required field, to show the corrected read refuses instead of
inventing a default. Nothing is re-run and no lifecycle is rebuilt.
"""
import collections, hashlib, io, json, os, sys

U = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(U, "docs")
res = collections.OrderedDict(kind="KIND_ROWS_FIELD_CORRECTION")
checks = collections.OrderedDict()


def sha(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def old_dispatch(kdoc):
    """The retained statement exactly as it shipped."""
    rows = kdoc.get("rows") or []
    return "empty" if not rows else "nonempty"


def new_dispatch(kdoc):
    """The corrected statement: the field the schema owns, subscripted."""
    rows = kdoc["batch_rows"]
    return "empty" if not rows else "nonempty"


docs = collections.OrderedDict()
for name in sorted(os.listdir(D)):
    p = os.path.join(D, name)
    doc = json.load(io.open(p, encoding="utf-8"))
    docs[name] = doc
    res.setdefault("inputs", collections.OrderedDict())[name] = {
        "sha256": sha(p),
        "batch_rows": len(doc.get("batch_rows") or []),
        "questions": sum(len(b.get("question_ids") or b.get("questions") or [])
                         for b in (doc.get("batch_rows") or [])),
        "has_top_level_rows": "rows" in doc}

# the fifth case: the required field is absent
missing = {k: v for k, v in docs["nonempty_G2.json"].items()
           if k != "batch_rows"}
res["missing_field_case"] = {"built_from": "nonempty_G2.json",
                             "removed": "batch_rows"}

expected = {"nonempty_G2.json": "nonempty", "nonempty_G3.json": "nonempty",
            "empty_G2.json": "empty", "empty_G3.json": "empty"}
rows = collections.OrderedDict()
for name, doc in docs.items():
    rows[name] = {"expected": expected[name],
                  "old": old_dispatch(doc), "new": new_dispatch(doc)}
for name, r in rows.items():
    print("  %-18s expected %-9s old %-9s new %-9s %s"
          % (name, r["expected"], r["old"], r["new"],
             "OLD WRONG" if r["old"] != r["expected"] else ""))
res["dispatch"] = rows


def refusal(fn):
    try:
        return {"selected": fn(missing), "refused": None}
    except BaseException as exc:                      # noqa: BLE001 - by design
        return {"selected": None,
                "refused": "%s: %s" % (type(exc).__name__, str(exc)[:80])}


res["on_missing_field"] = {"old": refusal(old_dispatch),
                           "new": refusal(new_dispatch)}
print("  missing field      old -> %s   new -> %s"
      % (json.dumps(res["on_missing_field"]["old"]),
         json.dumps(res["on_missing_field"]["new"])))

checks["1_RED_the_old_statement_calls_a_nonempty_kind_empty"] = all(
    rows[n]["old"] == "empty" for n in expected if expected[n] == "nonempty")
checks["2_RED_it_is_wrong_on_every_document_that_carries_batches"] = (
    sum(1 for n, r in rows.items() if r["old"] != r["expected"]) == 2)
checks["3_GREEN_the_corrected_statement_is_right_on_all_four"] = all(
    r["new"] == r["expected"] for r in rows.values())
checks["4_the_empty_cases_stay_empty"] = all(
    rows[n]["new"] == "empty" for n in expected if expected[n] == "empty")
checks["5_a_missing_required_field_refuses_rather_than_defaulting"] = (
    res["on_missing_field"]["new"]["refused"] is not None
    and res["on_missing_field"]["old"]["selected"] == "empty")
checks["6_no_document_carries_a_top_level_rows_field"] = all(
    not v["has_top_level_rows"] for v in res["inputs"].values())

res["checks"] = checks
ok = all(checks.values())
res["all_green"] = ok
io.open(os.path.join(U, "CONTROL_1943.json"), "w",
        encoding="utf-8").write(json.dumps(res, indent=2, default=str) + "\n")
print("%d/%d -> %s" % (sum(1 for v in checks.values() if v), len(checks), ok))
for k, v in checks.items():
    print("  %s %s" % ("GREEN" if v else "RED  ", k))
sys.exit(0 if ok else 1)
