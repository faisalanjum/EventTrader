#!/usr/bin/env python3
"""
compute_goal4_baseline.py — One-shot helper to derive Goal 4's proven-OK baseline.

Runs the CURRENT (Goal 4) resolver against the 9,943 oracle pool
(9,909 ground_truth.csv rows + 34 sec_52_53_audit rows) and persists the rows
where the resolver returns AUTO_OK with the matching oracle (fy, q).

Output: ../goal4_proven_ok_baseline.csv  (relative to this script's parent dir)

This script must be run BEFORE Goal 5 implementation begins, so the verifier
has a stable baseline to check per-row preservation against. It is NOT part
of the Goal 5 production pipeline; it is a one-time setup artifact.

Usage:
    source venv/bin/activate && python3 \\
        earnings-analysis/canary/quarter_resolver/audit_evidence/sec_nr_auto_ok_audit/compute_goal4_baseline.py
"""
from __future__ import annotations
import csv
import json
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
# _HERE = .../earnings-analysis/canary/quarter_resolver/audit_evidence/sec_nr_auto_ok_audit/
# parents[4] = project root
PROJECT_ROOT = _HERE.parents[4]
QR_DIR = PROJECT_ROOT / "earnings-analysis/canary/quarter_resolver"
GROUND_TRUTH_PATH = QR_DIR / "ground_truth.csv"
NEEDS_REVIEW_PATH = QR_DIR / "needs_review.csv"
SEC_5253_AUDIT_JSON = QR_DIR / "audit_evidence/sec_52_53_audit/all_verdicts.json"
OUT_PATH = QR_DIR / "audit_evidence/goal4_proven_ok_baseline.csv"

sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))
sys.path.insert(0, str(PROJECT_ROOT / ".claude/skills/earnings-orchestrator/scripts"))


def main() -> None:
    from quarter_identity import resolve_quarter_info

    # Build oracle pool
    pool = []
    for r in csv.DictReader(open(GROUND_TRUTH_PATH, encoding="utf-8")):
        pool.append((r["accession_8k"], r["ticker"], r["fy_xbrl"], r["q_xbrl"], "GT"))

    nr_by_accn = {r["accession_8k"]: r for r in csv.DictReader(
        open(NEEDS_REVIEW_PATH, encoding="utf-8"))}
    for r in json.load(open(SEC_5253_AUDIT_JSON, encoding="utf-8")):
        accn = r["accession_8k"]
        nr = nr_by_accn.get(accn)
        if nr:
            pool.append((accn, nr["ticker"], r["audited_fy"], r["audited_q"], "SEC"))

    print(f"Oracle pool: {len(pool)} rows", flush=True)

    proven = []
    n_fc = n_wrong = 0
    t0 = time.time()
    for i, (accn, ticker, o_fy, o_q, src) in enumerate(pool):
        if i and i % 200 == 0:
            elapsed = time.time() - t0
            rate = i / elapsed if elapsed > 0 else 0
            eta = (len(pool) - i) / rate if rate > 0 else 0
            print(
                f"  {i}/{len(pool)} ({rate:.1f}/s, ETA {eta/60:.1f}min) "
                f"OK={len(proven)} WRONG={n_wrong} FC={n_fc}",
                flush=True,
            )
        try:
            qi = resolve_quarter_info(ticker, accn)
        except Exception as e:
            n_fc += 1
            continue
        ql = qi.get("quarter_label") or ""
        sa = qi.get("safety_action") or ""
        if sa != "AUTO_OK" or not ql:
            n_fc += 1
            continue
        try:
            q_part, fy_part = ql.split("_FY")
        except ValueError:
            n_fc += 1
            continue
        if (fy_part, q_part) == (o_fy, o_q):
            proven.append((accn, ticker, o_fy, o_q, src))
        else:
            n_wrong += 1

    print()
    print(f"=== Goal 4 baseline ===")
    print(f"Pool: {len(pool)}")
    print(f"Proven OK: {len(proven)}")
    print(f"Wrong (should be 0): {n_wrong}")
    print(f"Fail-closed: {n_fc}")
    print(f"Elapsed: {(time.time()-t0)/60:.1f} min")

    if n_wrong > 0:
        print(
            f"WARNING: {n_wrong} wrong-auto-writes on oracle pool. Goal 4 verifier "
            f"would have failed G7. Investigate before using this baseline.",
            file=sys.stderr,
        )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["accession_8k", "ticker", "fy", "q", "oracle_source"])
        for r in proven:
            w.writerow(r)
    print(f"Wrote {len(proven)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
