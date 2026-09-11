# -*- coding: utf-8 -*-
"""Codex SEQ 2016: admit the preserved reviews, then close the attempt ONCE.

NO MODEL IS CALLED and no completion record is hand-written. Every judgement
comes from the published composite and the existing closure/hard-review owners,
entered through the composite's own door with EXPLICIT real paths.

  A7_STAGE=admit     append each preserved official state through the owner's
                     record_state, then ask the owner what each owed label is.
  A7_STAGE=finalize  refuse unless the attempt is terminal and not already
                     closed, then call the write-once finalizer exactly once.

A7_RUN and A7_PACKAGE name the real run and package; A7_LEDGER names the
durable launch ledger whose preserved rows supply the state paths.
"""
import collections
import hashlib
import io
import json
import os
import sys

A = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
sys.path.insert(0, A + "/unit_2009/owner")
import a4_review_composite as R                                    # noqa: E402

CL, HR, K, INV = R.CL, R.HR, R.K, R.INV
STAGE = os.environ["A7_STAGE"]
RUN = os.environ["A7_RUN"]
PKG = os.environ["A7_PACKAGE"]
LEDGER = os.environ["A7_LEDGER"]
WORKFLOWS = ("/home/faisal/.claude/projects/-home-faisal-EventMarketDB/"
             "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/workflows")


def fsha(path):
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


res = collections.OrderedDict()
res["stage"] = STAGE
res["run"] = RUN
res["package"] = PKG
res["owners"] = collections.OrderedDict([
    ("review_composite", fsha(R.__file__.rstrip("c"))),
    ("clarified_hard_review", fsha(HR.__file__.rstrip("c"))),
    ("source_closure", fsha(CL.__file__.rstrip("c")))])

led = json.loads(io.open(LEDGER, encoding="utf-8").read())
res["ledger_states"] = dict(collections.Counter(r["state"] for r in led["launches"]))

if STAGE == "admit":
    receipt = K._load(os.path.join(RUN, K.RECEIPT_NAME))
    already = set(receipt["states"])
    recorded, skipped, absent, problems = [], [], [], []
    with R._current_scope():
        for row in led["launches"]:
            if row["state"] != "preserved":
                continue
            path = os.path.join(WORKFLOWS, row["runId"] + ".json")
            if not os.path.isfile(path):
                absent.append(row["label"])
                continue
            if path in already:
                skipped.append(row["label"])
                continue
            bad = CL.record_state(RUN, path)
            if bad:
                problems.extend(bad[:2])
            else:
                recorded.append(row["label"])
                already.add(path)
    res["recorded_now"] = recorded
    res["already_recorded"] = skipped
    res["states_absent"] = absent
    res["record_problems"] = problems[:4]

with R._current_scope():
    got, run_problems = CL.readings(RUN, PKG)
receipt = K._load(os.path.join(RUN, K.RECEIPT_NAME))
res["receipt"] = collections.OrderedDict([
    ("sha256", INV.sha_file(os.path.join(RUN, K.RECEIPT_NAME))),
    ("attempt", receipt["attempt"]), ("allowed", receipt["allowed"]),
    ("states", len(receipt["states"]))])
res["run_problems"] = run_problems
res["outcomes"] = dict(collections.Counter(v[0] for v in got.values()))
res["per_label"] = collections.OrderedDict(
    (label, collections.OrderedDict([
        ("state", value[0]), ("why", value[1][:200]),
        ("text_sha256", K._sha(value[2]) if value[2] else None),
        ("text_bytes", len(value[2].encode("utf-8")) if value[2] else 0)]))
    for label, value in got.items())
res["terminal"] = not [v for v in got.values() if v[0] == "missing"]
res["finalized_before"] = os.path.isfile(os.path.join(RUN, K.FINALIZATION_NAME))

if STAGE == "finalize":
    if not res["terminal"] or res["run_problems"] or res["finalized_before"]:
        res["refused"] = ("the attempt is not terminal, has run problems, or is "
                          "already closed")
        print(json.dumps(res, indent=1, default=str))
        raise SystemExit(3)
    with R._current_scope():
        doc = CL.finalize(RUN, PKG)
    res["finalization"] = collections.OrderedDict([
        ("sha256", INV.sha_file(os.path.join(RUN, K.FINALIZATION_NAME))),
        ("attempt", doc["attempt"]), ("run_id", doc["run_id"]),
        ("primary_complete", doc["primary_complete"]),
        ("problems", doc["problems"]), ("ledger", doc["ledger"]),
        ("budget", doc["budget"]), ("retry", doc["retry"]),
        ("outcomes", doc["outcomes"])])
    child = os.path.join(RUN, "retry")
    res["child"] = collections.OrderedDict([
        ("published", os.path.isfile(os.path.join(child, K.RECEIPT_NAME)))])
    if res["child"]["published"]:
        rec = K._load(os.path.join(child, K.RECEIPT_NAME))
        res["child"].update(collections.OrderedDict([
            ("receipt_sha256", INV.sha_file(os.path.join(child, K.RECEIPT_NAME))),
            ("attempt", rec["attempt"]), ("allowed", rec["allowed"]),
            ("states", len(rec["states"])),
            ("scripts", sorted(os.listdir(os.path.join(child, "scripts")))),
            ("script_sha256", collections.OrderedDict(
                (n, INV.sha_file(os.path.join(child, "scripts", n)))
                for n in sorted(os.listdir(os.path.join(child, "scripts"))))),
            ("finalized", os.path.isfile(
                os.path.join(child, K.FINALIZATION_NAME)))]))

res["model_calls"] = 0
print(json.dumps(res, indent=1, default=str))
