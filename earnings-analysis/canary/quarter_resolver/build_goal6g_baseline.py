#!/usr/bin/env python3
"""
build_goal6g_baseline.py — Deterministic builder for the Goal 6g
expected per-row baseline.

Goal 6g adds an audited-issuer ticker bucket (TRUST_XBRL_ADVANCE) of
18 tickers. For rows where D currently fail-closes via
``rule_g_fail_closed_fy_disagreement_calendar`` AND the ticker is in
the bucket, the resolver should instead advance the prior XBRL FY/Q
by one quarter and return AUTO_OK with source
``rule_h_trusted_issuer_xbrl_advance``. All other rows must remain
byte-identical to D.

This script is a pure function of:
  - goal6a_d_measurement.csv (Goal 6a's frozen D measurement, 10,674 rows)
  - goal6f_candidate_G2_ALL_FY_DISAGREE_per_row.csv (provides advanced FY/Q
    for the disagreement-class rows; per-row outputs match what advance-
    XBRL would compute)
  - the 18-ticker TRUST_XBRL_ADVANCE bucket (hardcoded below — must
    match the production code exactly)

Usage:
  python3 build_goal6g_baseline.py
Writes:
  goal6g_baseline.csv (immutable after first commit)
"""
from __future__ import annotations

import csv
from pathlib import Path
import sys


_HERE = Path(__file__).resolve().parent
D_MEASUREMENT = _HERE / "goal6a_d_measurement.csv"
G2_ALL = _HERE / "goal6f_candidate_G2_ALL_FY_DISAGREE_per_row.csv"
OUT = _HERE / "goal6g_baseline.csv"


# ── Audited-issuer bucket ──────────────────────────────────────────────
# Must match TRUST_XBRL_ADVANCE in scripts/earnings/quarter_identity.py.
# 18 retailers verified silly-recoverable on the 34-edge SEC audit
# (Agent 1 spot-confirmed 5 with literal SEC quotes; recovery pattern
# identical for the rest based on per-row CSV deltas). See
# audit_evidence/per_ticker_autopsy_2026-05-07/AUTOPSY_FINAL.md.
TRUST_XBRL_ADVANCE = frozenset({
    "ACI", "ASO", "BJ", "BURL", "CHWY", "DLTR", "FIVE", "GME",
    "KSS", "LOW", "LULU", "OXM", "ROST", "ULTA",
    "KR", "OLLI", "PLAY", "RH",
})

TARGET_D_SOURCE = "rule_g_fail_closed_fy_disagreement_calendar"
NEW_SOURCE = "rule_h_trusted_issuer_xbrl_advance"


def main() -> int:
    with D_MEASUREMENT.open() as fh:
        d_rows = list(csv.DictReader(fh))
    with G2_ALL.open() as fh:
        g2_rows = {(r["ticker"], r["accession_8k"]): r for r in csv.DictReader(fh)}

    out_rows = []
    n_flipped = 0
    n_unchanged = 0
    flipped_by_ticker: dict[str, int] = {}

    for r in d_rows:
        ticker = r["ticker"]
        acc = r["accession_8k"]
        is_target = (
            r["outcome"] == "FAIL_CLOSED"
            and r.get("source", "") == TARGET_D_SOURCE
            and ticker in TRUST_XBRL_ADVANCE
        )
        if is_target:
            g = g2_rows.get((ticker, acc))
            if not g:
                print(
                    f"FATAL: target row missing G2 reference: {ticker} {acc}",
                    file=sys.stderr,
                )
                return 2
            if g["outcome"] != "AUTO_OK":
                print(
                    f"FATAL: G2 did not fire AUTO_OK for target row: "
                    f"{ticker} {acc} (G2 outcome={g['outcome']})",
                    file=sys.stderr,
                )
                return 2
            new_row = dict(r)
            new_row["outcome"] = "AUTO_OK"
            new_row["fy"] = g["fy"]
            new_row["q"] = g["q"]
            new_row["source"] = NEW_SOURCE
            new_row["correct"] = g["correct"]
            out_rows.append(new_row)
            n_flipped += 1
            flipped_by_ticker[ticker] = flipped_by_ticker.get(ticker, 0) + 1
        else:
            out_rows.append(r)
            n_unchanged += 1

    fieldnames = list(d_rows[0].keys())
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)

    print(f"wrote {OUT.name}", file=sys.stderr)
    print(f"  total rows         : {len(out_rows)}", file=sys.stderr)
    print(f"  rows unchanged     : {n_unchanged}", file=sys.stderr)
    print(f"  rows flipped to OK : {n_flipped}", file=sys.stderr)
    print(f"  flipped by ticker  :", file=sys.stderr)
    for t in sorted(flipped_by_ticker):
        print(f"    {t}: {flipped_by_ticker[t]}", file=sys.stderr)
    if not (set(flipped_by_ticker.keys()) == TRUST_XBRL_ADVANCE):
        missing = TRUST_XBRL_ADVANCE - set(flipped_by_ticker.keys())
        if missing:
            print(
                f"  WARNING: bucket tickers with NO flips: {sorted(missing)}",
                file=sys.stderr,
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
