"""Per-ticker autopsy fact sheet builder.

Reads:
- master_truth.csv (SEC ground-truth verdicts + EX-99.1 evidence)
- goal6f_candidate_*_per_row.csv (D + 2 G2 + 4 new candidate per-row outputs)
- goal6a_d_measurement.csv (full corpus D outputs incl. warm/latest flags)
- per-ticker fy_convention.json

For each of 34 tickers, writes ./fact_sheets/<TICKER>.json with:
  - SEC truth + D outcome + companion XBRL per row
  - Whether any Goal 6f candidate would have recovered each row
  - The per-row evidence quote captured by the audit

Read-only; no production code touched.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
QR = HERE.parents[1]
AUDIT = HERE.parent / "sec_34_edge_ticker_audit_2026-05-07"
OUT = HERE / "fact_sheets"
OUT.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open() as fh:
        return list(csv.DictReader(fh))


def main() -> None:
    master = read_csv(AUDIT / "master_truth.csv")
    print(f"loaded {len(master)} master_truth rows", file=sys.stderr)

    candidates = {
        "D_BASELINE": read_csv(QR / "goal6f_candidate_D_BASELINE_per_row.csv"),
        "G2_CALENDAR_ONLY": read_csv(QR / "goal6f_candidate_G2_CALENDAR_ONLY_per_row.csv"),
        "G2_ALL_FY_DISAGREE": read_csv(QR / "goal6f_candidate_G2_ALL_FY_DISAGREE_per_row.csv"),
        "MULTI_PRIOR_STABLE_OFFSET": read_csv(QR / "goal6f_candidate_MULTI_PRIOR_STABLE_OFFSET_per_row.csv"),
        "PERIOD_END_SHAPE_GATE": read_csv(QR / "goal6f_candidate_PERIOD_END_SHAPE_GATE_per_row.csv"),
        "CURRENT_8K_OWN_XBRL": read_csv(QR / "goal6f_candidate_CURRENT_8K_OWN_XBRL_per_row.csv"),
        "ADVANCE_RESULT_AGREEMENT": read_csv(QR / "goal6f_candidate_ADVANCE_RESULT_AGREEMENT_per_row.csv"),
    }
    by_acc: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    for cid, rows in candidates.items():
        for r in rows:
            by_acc[(r["ticker"], r["accession_8k"])][cid] = r

    d_full = read_csv(QR / "goal6a_d_measurement.csv")
    d_meta = {(r["ticker"], r["accession_8k"]): r for r in d_full}

    by_ticker: dict[str, list[dict]] = defaultdict(list)
    for r in master:
        by_ticker[r["ticker"]].append(r)

    for ticker in sorted(by_ticker):
        rows = sorted(by_ticker[ticker], key=lambda r: r["filed_8k"])
        conv_path = AUDIT / "tickers" / ticker / "fy_convention.json"
        fy_convention = json.loads(conv_path.read_text()) if conv_path.exists() else None
        report_path = AUDIT / "tickers" / ticker / "REPORT.md"
        report_md = report_path.read_text() if report_path.exists() else ""

        fact_rows = []
        for m in rows:
            acc = m["accession_8k"]
            cands = by_acc.get((ticker, acc), {})
            d_row = d_meta.get((ticker, acc), {})

            d_outcome = m["candidate_d_outcome"]
            d_fy = m["candidate_d_fy"] or None
            d_q = m["candidate_d_q"] or None
            d_source = m["candidate_d_source"]
            tier = m["sec_truth_tier"]
            t_fy = m["sec_truth_fy"] or None
            t_q = m["sec_truth_q"] or None

            d_correct = None
            if d_outcome == "AUTO_OK" and d_fy and d_q and t_fy and t_q:
                d_correct = (d_fy == t_fy and d_q == t_q)
            elif d_outcome == "FAIL_CLOSED":
                d_correct = None  # by-design refusal, not a wrong-fire

            recovered_by = []
            for cid, c in cands.items():
                if cid == "D_BASELINE":
                    continue
                if c.get("changed_vs_d", "false") == "true":
                    if c.get("outcome") == "AUTO_OK" and c.get("correct") == "true":
                        recovered_by.append(f"{cid} -> CORRECT")
                    elif c.get("outcome") == "AUTO_OK" and c.get("correct") == "false":
                        recovered_by.append(f"{cid} -> WRONG ({c.get('fy')} {c.get('q')})")
                    else:
                        recovered_by.append(f"{cid} -> {c.get('outcome')}")

            fact_rows.append({
                "accession_8k": acc,
                "filed_8k": m["filed_8k"],
                "tier": tier,
                "sec_truth": f"{t_fy} {t_q}" if t_fy and t_q else None,
                "evidence_quote": m["evidence_quote"],
                "evidence_url": m["evidence_url"],
                "evidence_doc": m["document_name"],
                "evidence_method": m["evidence_method"],
                "raw_path": m["raw_cached_path"],
                "companion_periodic_accession": m["companion_periodic_accession"],
                "companion_periodic_form": m["companion_periodic_form"],
                "companion_periodic_filed": m["companion_periodic_filed"],
                "companion_periodic_period_of_report": m["companion_periodic_period_of_report"],
                "companion_xbrl_fy": m["companion_xbrl_fy"],
                "companion_xbrl_q": m["companion_xbrl_q"],
                "companion_cover_quote": m["companion_cover_quote"],
                "d_outcome": d_outcome,
                "d_fy": d_fy,
                "d_q": d_q,
                "d_source": d_source,
                "d_correct": d_correct,
                "recovered_by_any_goal6f_cand": recovered_by,
                "warm_start": d_row.get("warm_start"),
                "latest_per_ticker": d_row.get("latest_per_ticker"),
                "reasoning_audit": m["reasoning"],
            })

        ab = [r for r in fact_rows if r["tier"] in ("A", "B")]
        d_correct_count = sum(1 for r in ab if r["d_correct"] is True)
        d_wrong_count = sum(1 for r in ab if r["d_correct"] is False)
        d_fc_count = sum(1 for r in ab if r["d_outcome"] == "FAIL_CLOSED")
        recoverable_count = sum(
            1 for r in ab
            if r["d_outcome"] == "FAIL_CLOSED"
            and any("-> CORRECT" in x for x in r["recovered_by_any_goal6f_cand"])
        )
        new_wrong_from_recovery = sum(
            1 for r in ab
            if r["d_outcome"] == "FAIL_CLOSED"
            and any("-> WRONG" in x for x in r["recovered_by_any_goal6f_cand"])
        )

        sources_used = sorted({r["d_source"] for r in ab})

        out = {
            "ticker": ticker,
            "fy_convention": fy_convention,
            "n_audit_rows_total": len(rows),
            "n_audit_rows_AB": len(ab),
            "AB_summary": {
                "d_correct": d_correct_count,
                "d_wrong": d_wrong_count,
                "d_fail_closed": d_fc_count,
                "fail_closed_with_correct_recovery_in_some_goal6f_cand": recoverable_count,
                "fail_closed_with_wrong_recovery_in_some_goal6f_cand": new_wrong_from_recovery,
            },
            "d_sources_used_AB": sources_used,
            "ticker_audit_report_md": report_md,
            "rows": fact_rows,
        }

        out_path = OUT / f"{ticker}.json"
        out_path.write_text(json.dumps(out, indent=2))

    summary_rows = []
    for ticker in sorted(by_ticker):
        d = json.loads((OUT / f"{ticker}.json").read_text())
        ab = d["AB_summary"]
        summary_rows.append({
            "ticker": ticker,
            "fy_convention": (d.get("fy_convention") or {}).get("naming_convention"),
            "n_AB": d["n_audit_rows_AB"],
            "d_correct": ab["d_correct"],
            "d_wrong": ab["d_wrong"],
            "d_fc": ab["d_fail_closed"],
            "fc_recovered_correct_by_any_cand": ab["fail_closed_with_correct_recovery_in_some_goal6f_cand"],
            "fc_recovered_wrong_by_any_cand": ab["fail_closed_with_wrong_recovery_in_some_goal6f_cand"],
            "primary_d_source": (
                max(set(d["d_sources_used_AB"]), key=lambda s: sum(1 for r in d["rows"] if r["d_source"] == s))
                if d["d_sources_used_AB"]
                else None
            ),
        })

    summary_path = Path(__file__).resolve().parent / "summary.csv"
    with summary_path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary_rows[0].keys()))
        w.writeheader()
        w.writerows(summary_rows)

    print(f"wrote {len(summary_rows)} fact sheets to {OUT}", file=sys.stderr)
    print(f"summary at {summary_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
