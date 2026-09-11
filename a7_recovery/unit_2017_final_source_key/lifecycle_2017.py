# -*- coding: utf-8 -*-
"""Codex SEQ 2018: admit the preserved adjudications, then close the attempt ONCE.

NO MODEL IS CALLED and no completion record is hand-written. Every judgement
comes from the published composite's final-key scope and the unchanged
source-key owner, entered with EXPLICIT real package/run paths.

  A7_STAGE=admit     append each preserved official state through the owner's
                     record_state, then ask the owner what it still owes.
  A7_STAGE=finalize  refuse unless every allowed call is terminal and the
                     attempt is not already closed, then close it exactly once.

A7_RUN / A7_PACKAGE name the real run and package, A7_LEDGER the durable launch
ledger whose preserved rows supply the state paths, and A7_ATTEMPT which
attempt directory is being admitted (1 = the primary, 2 = the owner's child).
"""
import collections
import hashlib
import io
import json
import os
import sys

A7 = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
sys.path.insert(0, A7 + "/unit_2009/owner")
import a4_review_composite as R                                    # noqa: E402

CL, K, SK, INV = R.CL, R.K, R.SK, R.INV
STAGE = os.environ["A7_STAGE"]
RUN = os.environ["A7_RUN"]
PKG = os.environ["A7_PACKAGE"]
LEDGER = os.environ["A7_LEDGER"]
ATTEMPT = int(os.environ.get("A7_ATTEMPT", "1"))
BASE = RUN if ATTEMPT == 1 else os.path.join(RUN, "retry")
REVIEW_RUN = os.path.join(os.path.dirname(R.OLD_RUN), "review_2015")
REVIEW_PKG = os.path.join(os.path.dirname(R.OLD_RUN), "closure_2015")
WORKFLOWS = ("/home/faisal/.claude/projects/-home-faisal-EventMarketDB/"
             "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/workflows")


def fsha(path):
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


res = collections.OrderedDict()
res["stage"] = STAGE
res["attempt"] = ATTEMPT
res["run"] = RUN
res["attempt_dir"] = BASE
res["package"] = PKG
res["owners"] = collections.OrderedDict([
    ("review_composite", fsha(R.__file__.rstrip("c"))),
    ("source_key", fsha(SK.__file__.rstrip("c"))),
    ("key_owner_role", fsha(SK.KEY_ROLE_FILE))])

led = json.loads(io.open(LEDGER, encoding="utf-8").read())
res["ledger_states"] = dict(collections.Counter(
    r["state"] for r in led["launches"] if r["attempt"] == ATTEMPT))

with R.final_scope(REVIEW_RUN, REVIEW_PKG):
    if STAGE == "admit":
        receipt = K._load(os.path.join(BASE, K.RECEIPT_NAME))
        already = set(receipt["states"])
        recorded, skipped, absent, problems = [], [], [], []
        for row in led["launches"]:
            if row["state"] != "preserved" or row["attempt"] != ATTEMPT:
                continue
            path = os.path.join(WORKFLOWS, row["runId"] + ".json")
            if not os.path.isfile(path):
                absent.append(row["label"])
                continue
            if path in already:
                skipped.append(row["label"])
                continue
            bad = SK.record_state(BASE, path)
            if bad:
                problems.extend(bad[:2])
            else:
                recorded.append(row["label"])
                already.add(path)
        res["recorded_now"] = recorded
        res["already_recorded"] = skipped
        res["states_absent"] = absent
        res["record_problems"] = problems[:4]

    resume = SK.resume_plan(RUN, package=PKG)
    receipt = K._load(os.path.join(BASE, K.RECEIPT_NAME))
    res["receipt"] = collections.OrderedDict([
        ("path", os.path.join(BASE, K.RECEIPT_NAME)),
        ("sha256", INV.sha_file(os.path.join(BASE, K.RECEIPT_NAME))),
        ("attempt", receipt["attempt"]), ("allowed", len(receipt["allowed"])),
        ("states", len(receipt["states"]))])
    res["resume"] = collections.OrderedDict([
        ("published", resume["published"]), ("finalized", resume["finalized"]),
        ("allowed", len(resume["allowed"])), ("served", len(resume["served"])),
        ("owed", resume["owed"]), ("retryable", resume["retryable"]),
        ("never_repeat", len(resume["never_repeat"])),
        ("problems", resume["problems"])])
    res["outcomes"] = dict(collections.Counter(resume["outcomes"].values()))
    res["per_label"] = collections.OrderedDict(sorted(resume["outcomes"].items()))
    missing = [l for l, o in resume["outcomes"].items() if o == "missing"]
    res["still_missing"] = missing
    res["terminal"] = not missing and not resume["problems"]
    res["finalized_before"] = os.path.isfile(
        os.path.join(BASE, K.FINALIZATION_NAME))

    if STAGE == "finalize":
        if not res["terminal"] or res["finalized_before"]:
            res["refused"] = ("the attempt is not terminal, has problems, or "
                              "is already closed")
            print(json.dumps(res, indent=1, default=str))
            raise SystemExit(3)
        doc = SK.finalize(BASE, package=PKG)
        res["finalization"] = collections.OrderedDict([
            ("path", os.path.join(BASE, K.FINALIZATION_NAME)),
            ("sha256", INV.sha_file(os.path.join(BASE, K.FINALIZATION_NAME))),
            ("attempt", doc.get("attempt")), ("run_id", doc.get("run_id")),
            ("ledger", doc.get("ledger")), ("budget", doc.get("budget")),
            ("problems", doc.get("problems")), ("retry", doc.get("retry")),
            ("outcomes", doc.get("outcomes"))])
        child = os.path.join(RUN, "retry")
        res["child"] = collections.OrderedDict([
            ("published", os.path.isfile(os.path.join(child, K.RECEIPT_NAME)))])
        if res["child"]["published"]:
            rec = K._load(os.path.join(child, K.RECEIPT_NAME))
            names = sorted(os.listdir(os.path.join(child, "scripts")))
            res["child"].update(collections.OrderedDict([
                ("receipt_path", os.path.join(child, K.RECEIPT_NAME)),
                ("receipt_sha256", INV.sha_file(
                    os.path.join(child, K.RECEIPT_NAME))),
                ("attempt", rec["attempt"]), ("allowed", rec["allowed"]),
                ("states", len(rec["states"])),
                ("scripts_dir", os.path.join(child, "scripts")),
                ("script_sha256", collections.OrderedDict(
                    (n, INV.sha_file(os.path.join(child, "scripts", n)))
                    for n in names)),
                ("finalized", os.path.isfile(
                    os.path.join(child, K.FINALIZATION_NAME)))]))

res["model_calls"] = 0
print(json.dumps(res, indent=1, default=str))
