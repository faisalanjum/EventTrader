# -*- coding: utf-8 -*-
"""Codex SEQ 2018 item 4: READ the final accounting and accepted shards.

READ-ONLY. No model is called, nothing is materialized, signed, graded or
repaired, and no reply is adjudicated here. The existing owner supplies the
shards; this payload only counts them and lifts out, verbatim, every open
semantic issue the key owner itself recorded, with its source and row.
"""
import collections
import hashlib
import io
import json
import os
import sys

A7 = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
UNIT = A7 + "/unit_2017_final_source_key"
sys.path.insert(0, A7 + "/unit_2009/owner")
import a4_review_composite as R                                    # noqa: E402

CL, K, SK, INV = R.CL, R.K, R.SK, R.INV
RUN = os.environ["A7_RUN"]
PKG = os.environ["A7_PACKAGE"]
REVIEW_RUN = os.path.join(os.path.dirname(R.OLD_RUN), "review_2015")
REVIEW_PKG = os.path.join(os.path.dirname(R.OLD_RUN), "closure_2015")


def fsha(path):
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


res = collections.OrderedDict()
res["owners"] = collections.OrderedDict([
    ("review_composite", fsha(R.__file__.rstrip("c"))),
    ("source_key", fsha(SK.__file__.rstrip("c"))),
    ("key_owner_role", fsha(SK.KEY_ROLE_FILE))])
res["run"] = RUN
res["package"] = PKG
res["receipt_sha256"] = INV.sha_file(os.path.join(RUN, K.RECEIPT_NAME))
res["finalization_sha256"] = INV.sha_file(os.path.join(RUN, K.FINALIZATION_NAME))
res["finalization"] = K._load(os.path.join(RUN, K.FINALIZATION_NAME))
res["manifest_sha256"] = INV.sha_file(os.path.join(PKG, SK.MANIFEST_NAME))
res["retry_dir_exists"] = os.path.isdir(os.path.join(RUN, "retry"))
raw_dir = os.path.join(RUN, "raw")
res["raw_files"] = len(os.listdir(raw_dir)) if os.path.isdir(raw_dir) else 0

with R.final_scope(REVIEW_RUN, REVIEW_PKG) as proof:
    resume = SK.resume_plan(RUN, package=PKG)
    res["resume"] = collections.OrderedDict([
        ("published", resume["published"]), ("finalized", resume["finalized"]),
        ("allowed", len(resume["allowed"])), ("served", len(resume["served"])),
        ("owed", resume["owed"]), ("retryable", resume["retryable"]),
        ("never_repeat", len(resume["never_repeat"])),
        ("problems", resume["problems"]),
        ("outcomes", dict(collections.Counter(resume["outcomes"].values())))])
    shards, raws, bad = SK.accepted_shards(RUN, package=PKG)
    res["accepted"] = collections.OrderedDict([
        ("shards", len(shards)), ("raws", len(raws)), ("problems", bad)])
    res["leads_per_source"] = collections.OrderedDict(
        (sid, len(v)) for sid, v in sorted(proof["by_source"].items()))

    # ---- what the key owner itself settled, and what it left open ----------
    # The owner's accepted shard keys rows by their frozen row id and carries
    # its own per-row outcome, so nothing here re-parses a reply.
    rows_total, outcomes, open_issues = 0, collections.Counter(), []
    no_fact_rows, lead_disagreements = [], []
    per_source = collections.OrderedDict()
    for sid in sorted(shards):
        doc = shards[sid]
        rows = doc.get("rows") or {}
        row_outcomes = doc.get("outcomes") or {}
        rows_total += len(rows)
        kinds = collections.Counter(row_outcomes.values())
        outcomes.update(kinds)
        facts = sum(len((settled or {}).get("facts") or [])
                    for settled in rows.values())
        disagreed = [lead.get("lead_id")
                     for lead in (doc.get("lead_reconciliation") or [])
                     if lead.get("agrees") is False]
        lead_disagreements += [(sid, lead_id) for lead_id in disagreed]
        per_source[sid] = collections.OrderedDict([
            ("rows", len(rows)), ("facts", facts), ("outcomes", dict(kinds)),
            ("leads_disagreed", disagreed)])
        for row_id, outcome in sorted(row_outcomes.items()):
            if not ((rows.get(row_id) or {}).get("facts") or []):
                no_fact_rows.append(collections.OrderedDict([
                    ("source_id", sid), ("row_id", row_id),
                    ("outcome", outcome),
                    ("abstention_reasons",
                     [a.get("reason") for a in
                      ((rows.get(row_id) or {}).get("abstentions") or [])])]))
        for issue in doc.get("open_issues") or []:
            open_issues.append(collections.OrderedDict(
                [("source_id", sid)] + list(issue.items())))

res["settled"] = collections.OrderedDict([
    ("rows", rows_total), ("row_outcomes", dict(outcomes)),
    ("per_source", per_source)])
res["open_issues"] = open_issues
res["open_issue_count"] = len(open_issues)
res["rows_yielding_no_fact"] = no_fact_rows
res["rows_yielding_no_fact_count"] = len(no_fact_rows)
res["lead_disagreements"] = lead_disagreements
res["lead_disagreement_count"] = len(lead_disagreements)
res["model_calls"] = 0
print(json.dumps(res, indent=1, default=str))
