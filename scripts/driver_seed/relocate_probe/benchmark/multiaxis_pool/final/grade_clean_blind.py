#!/usr/bin/env python3
"""Strict grader for the 100-case unseen-company blind reader run."""
from __future__ import annotations

import collections
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path("/tmp/relocate_multi_axis.mrogHs")
RUN = ROOT / "runs" / "clean_multi_axis"
sys.path.insert(0, str(ROOT / "driver_seed"))
import link_lib as L


QUARTER = re.compile(
    r"\b(?:three(?:\s+and\s+(?:six|nine))?[\s-]+months?|quarter|"
    r"(?:1[234]|twelve|thirteen|fourteen)[\s-]+weeks?)\b",
    re.I,
)


def value_in_quote(value_text, quote):
    if not value_text or not quote or not re.search(r"\d", value_text):
        return False
    return any(
        L.at_boundary(quote, match.start(), match.end(), numeric=True)
        for match in re.finditer(re.escape(value_text), quote)
    )


truth = {
    row["id"]: row
    for row in map(json.loads, (RUN / "holdout_blind_truth.jsonl").read_text().splitlines())
}
outputs = []
for suffix in (0, 1, 2):
    outputs.extend(json.loads((RUN / f"blind_reader_column_mod{suffix}.json").read_text())["records"])
recheck = RUN / "blind_reader_section_recheck.json"
if recheck.exists():
    replacements = {
        row["id"]: row for row in json.loads(recheck.read_text())["records"]
    }
    outputs = [replacements.get(row["id"], row) for row in outputs]
assert len(outputs) == 100
assert len({row["id"] for row in outputs}) == 100
assert set(row["id"] for row in outputs) == set(truth)

counts = collections.Counter()
details = []
for case_id in sorted(truth):
    expected = truth[case_id]
    output = next(row for row in outputs if row["id"] == case_id)
    batch = json.loads((RUN / "holdout_blind_batches" / f"batch_{case_id}.json").read_text())
    emitted = bool(output.get("found"))
    reasons = []
    correct = False
    if emitted:
        index = output.get("candidate_index")
        if not isinstance(index, int) or not 0 <= index < len(batch["candidates"]):
            reasons.append("bad_candidate_index")
        else:
            candidate = batch["candidates"][index]["text"]
            quote = str(output.get("quote") or "")
            evidence = str(output.get("period_evidence") or "")
            value_text = str(output.get("value") or "")
            if not quote or quote not in candidate:
                reasons.append("quote_not_verbatim")
            if not evidence or evidence not in candidate:
                reasons.append("period_evidence_not_verbatim")
            if not value_in_quote(value_text, quote):
                reasons.append("value_not_in_quote")
            if not L.stated_match(value_text, float(Decimal(expected["target_value_raw"]))):
                reasons.append("wrong_value")
            target_year = batch["period_target"][:4]
            if target_year not in candidate:
                reasons.append("target_year_not_proved")
            if not QUARTER.search(evidence):
                reasons.append("single_quarter_not_proved")
            correct = not reasons
    else:
        reasons.append("abstain")

    counts["source_present" if expected["source_present"] else "source_absent"] += 1
    counts["candidate_present" if expected["candidate_present"] else "candidate_absent"] += 1
    counts["emitted" if emitted else "abstained"] += 1
    counts["correct" if correct else "not_correct"] += 1
    if emitted and not correct:
        counts["false_positive"] += 1
    if expected["candidate_present"] and not correct:
        counts["false_negative_reachable"] += 1
    details.append(
        {
            "id": case_id,
            "pool_id": expected["pool_id"],
            "ticker": expected["ticker"],
            "source_present": expected["source_present"],
            "candidate_present": expected["candidate_present"],
            "emitted": emitted,
            "correct": correct,
            "reasons": reasons,
            "reader_reason": output.get("reason", ""),
        }
    )

report = {
    "counts": dict(counts),
    "precision": counts["correct"] / counts["emitted"] if counts["emitted"] else 0,
    "recall_all": counts["correct"] / len(truth),
    "recall_given_source": counts["correct"] / counts["source_present"],
    "recall_given_candidate": counts["correct"] / counts["candidate_present"],
    "details": details,
}
(RUN / "blind_reader_final_grade.json").write_text(json.dumps(report, indent=2))
print(json.dumps({key: value for key, value in report.items() if key != "details"}, indent=2))
