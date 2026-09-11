# -*- coding: utf-8 -*-
"""Codex SEQ 2016 close-out proof: replay BOTH complete stages, READ-ONLY.

No model is called and nothing is written. The composite's own
`merged_readings` joins the preserved review with the clarified one; every old
valid answer is then compared, by the owner's own comparison, to the durable
raw bytes that attempt saved - so "unchanged" is measured against the evidence,
never against this reporter.
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
RUN = os.environ["A7_RUN"]
PKG = os.environ["A7_PACKAGE"]
checks = []


def check(name, got, want):
    assert got == want, "%s: got %r want %r" % (name, got, want)
    checks.append(name)


def fsha(path):
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


res = collections.OrderedDict()
res["owners"] = collections.OrderedDict([
    ("review_composite", fsha(R.__file__.rstrip("c"))),
    ("clarified_hard_review", fsha(HR.__file__.rstrip("c"))),
    ("preserved_hard_review", fsha(str(R.OLD_OWNER_PATH)))])

merged, stages = R.merged_readings(RUN, PKG)
old, _old_stage = R.old_readings()
res["merged_total"] = len(merged)
res["merged_outcomes"] = dict(collections.Counter(v[0] for v in merged.values()))
res["preserved_outcomes"] = dict(collections.Counter(v[0] for v in old.values()))
check("1 the join covers every one of the 66 owed slots", len(merged), 66)
check("2 all 66 now read valid", res["merged_outcomes"], {"valid": 66})
check("3 the preserved stage is still 62 valid and 4 invalid",
      res["preserved_outcomes"], {"valid": 62, "invalid_response": 4})

replaced = [l for l, v in old.items() if v[0] != "valid"]
check("4 exactly the four unresolved slots were replaced",
      replaced, HR._canonical_of(R._context(old, _old_stage)))
check("5 every other slot is the PRESERVED answer, unchanged",
      [l for l in merged if l not in replaced and merged[l] != old[l]], [])

# ---- the preserved answers compared to the bytes their own attempt saved ----
proved, unmatched = 0, []
for base in (R.OLD_RUN, os.path.join(R.OLD_RUN, "retry")):
    doc = K._load(os.path.join(base, K.FINALIZATION_NAME))
    for label, state, _why in doc["outcomes"]:
        if state != "valid":
            continue
        path = os.path.join(base, "raw", "%s.attempt%s.proved.json"
                            % (label.replace("/", "_"), doc["attempt"]))
        if K._stored_matches(path, merged[label][2]) is not True:
            unmatched.append(label)
        else:
            proved += 1
check("6 all 62 preserved answers are byte-identical to their saved raw",
      [proved, unmatched], [62, []])

# ---- what the clarified stage itself produced ------------------------------
new_raw = sorted(os.listdir(os.path.join(RUN, "raw")))
res["clarified"] = collections.OrderedDict([
    ("run", RUN), ("package", PKG),
    ("receipt_sha256", INV.sha_file(os.path.join(RUN, K.RECEIPT_NAME))),
    ("finalization_sha256", INV.sha_file(os.path.join(RUN, K.FINALIZATION_NAME))),
    ("manifest_sha256", INV.sha_file(os.path.join(PKG, CL.MANIFEST_NAME))),
    ("raw_files", new_raw),
    ("raw_sha256", collections.OrderedDict(
        (n, INV.sha_file(os.path.join(RUN, "raw", n))) for n in new_raw)),
    ("answers", collections.OrderedDict(
        (l, collections.OrderedDict([
            ("text_sha256", K._sha(merged[l][2])),
            ("text_bytes", len(merged[l][2].encode("utf-8")))]))
        for l in replaced)),
    ("retry_published", os.path.isdir(os.path.join(RUN, "retry")))])
check("7 no child was published and no third attempt exists",
      [res["clarified"]["retry_published"],
       K._load(os.path.join(RUN, K.FINALIZATION_NAME))["retry"]], [False, []])

res["stage_evidence"] = stages
res["budget"] = K._load(os.path.join(RUN, K.FINALIZATION_NAME))["budget"]
check("8 the ledger is 495 before and 499 after, inside the ceiling",
      [res["budget"][k] for k in
       ("ledger_before", "this_attempt", "ledger_after", "global_ceiling",
        "within_ceiling")], [495, 4, 499, 4382, True])

import a7_prepared_run as PR                                       # noqa: E402
res["a3_answer_run"] = PR._executed(os.path.abspath(K.a3_run_dirs()[0]))
check("9 the original 382 answers are untouched",
      res["a3_answer_run"]["run_files"], 799)

res["per_label"] = collections.OrderedDict(
    (l, collections.OrderedDict([
        ("state", merged[l][0]),
        ("source", "clarified" if l in replaced else "preserved"),
        ("text_sha256", K._sha(merged[l][2]))])) for l in merged)
res["checks"] = checks
res["passed"] = len(checks)
res["model_calls"] = 0
print(json.dumps(res, indent=1, default=str))
