#!/usr/bin/env python3
"""Build Goal 6a measurement CSVs and report from committed oracles."""
from __future__ import annotations

import csv
import json
import os
from bisect import bisect_right
from collections import OrderedDict
from pathlib import Path
import sys

from neo4j import GraphDatabase

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import goal6_candidates as goal6

GROUND_TRUTH_PATH = HERE / "ground_truth.csv"
SEC_5253_AUDIT_JSON = HERE / "audit_evidence/sec_52_53_audit/all_verdicts.json"
NR_AUDIT_JSON = HERE / "audit_evidence/sec_nr_auto_ok_audit/cleaned_all_verdicts.json"
GOAL4_BASELINE_CSV = HERE / "audit_evidence/goal4_proven_ok_baseline.csv"

D_MEASUREMENT_CSV = HERE / "goal6a_d_measurement.csv"
E_MEASUREMENT_CSV = HERE / "goal6a_e_measurement.csv"
GOAL6A_REPORT = HERE / "GOAL6A_REPORT.md"

EXPECTED_TOTAL = 10674

CSV_COLUMNS = [
    "accession_8k",
    "ticker",
    "oracle_source",
    "oracle_fy",
    "oracle_q",
    "warm_start",
    "latest_per_ticker",
    "outcome",
    "fy",
    "q",
    "source",
    "correct",
]


def _load_env() -> None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        if "=" not in line or line.strip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _open_driver():
    _load_env()
    uri = os.environ.get("NEO4J_URI", "bolt://minisforum3:30687")
    user = os.environ.get("NEO4J_USERNAME", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        raise RuntimeError("NEO4J_PASSWORD not set")
    return GraphDatabase.driver(uri, auth=(user, password))


def _add_oracle(rows: OrderedDict, accession: str, ticker: str, source: str, fy, q) -> None:
    if accession in rows:
        raise ValueError(f"Duplicate oracle accession: {accession}")
    rows[accession] = {
        "accession_8k": accession,
        "ticker": ticker.upper(),
        "oracle_source": source,
        "oracle_fy": str(fy),
        "oracle_q": str(q),
    }


def load_scoreable_population() -> list[dict]:
    rows: OrderedDict[str, dict] = OrderedDict()

    for r in csv.DictReader(open(GROUND_TRUTH_PATH, encoding="utf-8")):
        _add_oracle(rows, r["accession_8k"], r["ticker"], "GT", r["fy_xbrl"], r["q_xbrl"])

    sec_rows = json.load(open(SEC_5253_AUDIT_JSON, encoding="utf-8"))
    for r in sec_rows:
        _add_oracle(rows, r["accession_8k"], r["ticker"], "SEC_5253", r["audited_fy"], r["audited_q"])

    nr_rows = json.load(open(NR_AUDIT_JSON, encoding="utf-8"))
    for r in nr_rows:
        if r.get("final_verdict") not in {"ok", "wrong"}:
            continue
        _add_oracle(
            rows,
            r["accession_8k"],
            r["ticker"],
            "cleaned_NR",
            r["cleaned_audited_fy"],
            r["cleaned_audited_q"],
        )

    population = list(rows.values())
    if len(population) != EXPECTED_TOTAL:
        raise RuntimeError(f"scoreable population has {len(population)} rows; expected {EXPECTED_TOTAL}")
    return population


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


_COMPANY_CONTEXT_QUERY = """
MATCH (c:Company)
WHERE c.ticker IN $tickers
OPTIONAL CALL (c) {
  MATCH (k:Report)-[:PRIMARY_FILER]->(c)
  WHERE k.formType = '10-K' AND k.periodOfReport IS NOT NULL
  WITH date(k.periodOfReport).month AS m, count(*) AS cnt
  ORDER BY cnt DESC LIMIT 1
  RETURN m AS fye_month
}
RETURN c.ticker AS ticker,
       c.industry_normalized AS industry_normalized,
       fye_month
"""


_EARNINGS_8K_QUERY = """
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company)
WHERE c.ticker IN $tickers
  AND r.formType = '8-K'
  AND r.items CONTAINS '2.02'
RETURN c.ticker AS ticker,
       coalesce(r.id, r.accessionNo) AS accession_8k,
       r.id AS report_id,
       r.accessionNo AS accession_no,
       r.created AS filed_8k,
       r.market_session AS market_session
ORDER BY c.ticker, datetime(r.created)
"""


_PERIODIC_QUERY = """
MATCH (p:Report)-[:PRIMARY_FILER]->(c:Company)
WHERE c.ticker IN $tickers
  AND p.formType IN ['10-Q', '10-K']
  AND p.periodOfReport IS NOT NULL
RETURN c.ticker AS ticker,
       coalesce(p.id, p.accessionNo) AS accession,
       p.created AS created,
       p.periodOfReport AS period,
       p.formType AS form
ORDER BY c.ticker, datetime(p.created)
"""


_XBRL_IDENTITY_QUERY = """
MATCH (p:Report)
WHERE p.id IN $accessions OR p.accessionNo IN $accessions
OPTIONAL MATCH (p)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(fp:Fact {qname: 'dei:DocumentFiscalPeriodFocus'})
WITH p, collect(DISTINCT fp.value) AS xbrl_periods
OPTIONAL MATCH (p)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(fy:Fact {qname: 'dei:DocumentFiscalYearFocus'})
WITH p, xbrl_periods, collect(DISTINCT fy.value) AS xbrl_years
RETURN coalesce(p.id, p.accessionNo) AS accession,
       CASE WHEN size(xbrl_periods) = 1 THEN head(xbrl_periods) END AS xbrl_period,
       CASE WHEN size(xbrl_years) = 1 THEN head(xbrl_years) END AS xbrl_year
"""


def _to_str(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "to_native"):
        value = value.to_native()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _parse_dt(value):
    return goal6.qi._parse_datetime(_to_str(value))


def _prime_goal6_context_cache(population: list[dict], session) -> None:
    tickers = sorted({r["ticker"] for r in population})

    company = {}
    for rec in session.run(_COMPANY_CONTEXT_QUERY, tickers=tickers):
        company[rec["ticker"]] = {
            "fye_month": goal6.qi._parse_fye(rec["fye_month"]),
            "industry_normalized": _to_str(rec["industry_normalized"]),
        }

    eightks_by_ticker: dict[str, list[dict]] = {ticker: [] for ticker in tickers}
    for rec in session.run(_EARNINGS_8K_QUERY, tickers=tickers):
        ticker = rec["ticker"]
        eightks_by_ticker.setdefault(ticker, []).append({
            "ticker": ticker,
            "accession_8k": _to_str(rec["accession_8k"]),
            "report_id": _to_str(rec["report_id"]),
            "accession_no": _to_str(rec["accession_no"]),
            "filed_8k": _to_str(rec["filed_8k"]),
            "filed_dt": _parse_dt(rec["filed_8k"]),
            "market_session": rec["market_session"],
        })

    periodic_by_ticker: dict[str, list[dict]] = {ticker: [] for ticker in tickers}
    for rec in session.run(_PERIODIC_QUERY, tickers=tickers):
        ticker = rec["ticker"]
        created_dt = _parse_dt(rec["created"])
        if created_dt is None:
            continue
        periodic_by_ticker.setdefault(ticker, []).append({
            "accession": _to_str(rec["accession"]),
            "created": _to_str(rec["created"]),
            "created_dt": created_dt,
            "period": _to_str(rec["period"])[:10],
            "form": _to_str(rec["form"]).replace("/A", ""),
        })

    periodic_times = {
        ticker: [p["created_dt"] for p in rows]
        for ticker, rows in periodic_by_ticker.items()
    }

    wanted = {(r["ticker"], r["accession_8k"]) for r in population}
    seen = set()
    for ticker, rows in eightks_by_ticker.items():
        previous_filed = ""
        for row in rows:
            accession_keys = {
                row["accession_8k"],
                row["report_id"],
                row["accession_no"],
            }
            if not any((ticker, key) in wanted for key in accession_keys if key):
                previous_filed = row["filed_8k"]
                continue
            filed_dt = row["filed_dt"]
            periodic_rows = periodic_by_ticker.get(ticker, [])
            times = periodic_times.get(ticker, [])
            idx = bisect_right(times, filed_dt) if filed_dt is not None else 0
            priors = []
            for prior in reversed(periodic_rows[:idx]):
                priors.append({
                    "accession": prior["accession"],
                    "created": prior["created"],
                    "period": prior["period"],
                    "form": prior["form"],
                })
                if len(priors) >= 12:
                    break
            cmeta = company.get(ticker, {})
            context = {
                "accession_8k": row["accession_8k"],
                "ticker": ticker,
                "filed_8k": row["filed_8k"],
                "market_session": row["market_session"],
                "industry_normalized": cmeta.get("industry_normalized", ""),
                "fye_month": cmeta.get("fye_month"),
                "prev_8k_ts": previous_filed,
                "_prefetched_priors": priors,
            }
            for key in accession_keys:
                if key:
                    goal6._CONTEXT_CACHE[(ticker, key)] = context
                    seen.add((ticker, key))
            previous_filed = row["filed_8k"]

    missing = sorted((ticker, acc) for ticker, acc in wanted if (ticker, acc) not in seen)
    if missing:
        raise RuntimeError(f"Missing generated contexts: {missing[:20]}")


def _prime_xbrl_cache(session, chunk_size: int = 1000) -> None:
    accessions = sorted({
        ctx["_prefetched_priors"][0]["accession"]
        for ctx in goal6._CONTEXT_CACHE.values()
        if ctx.get("_prefetched_priors")
    })
    for start in range(0, len(accessions), chunk_size):
        chunk = accessions[start:start + chunk_size]
        for rec in session.run(_XBRL_IDENTITY_QUERY, accessions=chunk):
            goal6.qi._XBRL_CACHE[_to_str(rec["accession"])] = (
                rec["xbrl_period"],
                rec["xbrl_year"],
            )
        if (start + chunk_size) % 5000 == 0 or start + chunk_size >= len(accessions):
            print(f"xbrl hydrated {min(start + chunk_size, len(accessions))}/{len(accessions)}", flush=True)


def _measurement_row(base: dict, result: dict, *, warm_start: bool, latest_per_ticker: bool) -> dict:
    outcome = str(result.get("outcome", "FAIL_CLOSED"))
    fy = str(result.get("fy", "") or "")
    q = str(result.get("q", "") or "")
    correct = outcome == "AUTO_OK" and fy == base["oracle_fy"] and q == base["oracle_q"]
    return {
        **base,
        "warm_start": _bool_text(warm_start),
        "latest_per_ticker": _bool_text(latest_per_ticker),
        "outcome": outcome,
        "fy": fy if outcome == "AUTO_OK" else "",
        "q": q if outcome == "AUTO_OK" else "",
        "source": str(result.get("source", "") or ""),
        "correct": _bool_text(correct),
    }


def _latest_accessions(population: list[dict], metadata: dict[str, dict]) -> set[str]:
    latest_by_ticker: dict[str, tuple[str, str]] = {}
    for row in population:
        meta = metadata[row["accession_8k"]]
        if not meta["warm_start"]:
            continue
        ticker = row["ticker"]
        filed = meta["filed_8k"]
        current = latest_by_ticker.get(ticker)
        if current is None or filed > current[0]:
            latest_by_ticker[ticker] = (filed, row["accession_8k"])

    missing = sorted({r["ticker"] for r in population} - set(latest_by_ticker))
    if missing:
        raise RuntimeError(f"No warm-start latest row for tickers: {missing[:20]}")
    return {acc for _, acc in latest_by_ticker.values()}


def build_measurements(population: list[dict]) -> tuple[list[dict], list[dict]]:
    d_rows: list[dict] = []
    e_rows: list[dict] = []
    metadata: dict[str, dict] = {}

    driver = _open_driver()
    try:
        with driver.session() as session:
            print("preloading ticker-level context", flush=True)
            _prime_goal6_context_cache(population, session)
            print("preloaded requested contexts", flush=True)
            _prime_xbrl_cache(session)

            for i, row in enumerate(population, start=1):
                warm_start = goal6.row_has_warm_start(
                    row["ticker"], row["accession_8k"], neo4j_session=session
                )
                filed_8k = goal6.row_filed_8k(
                    row["ticker"], row["accession_8k"], neo4j_session=session
                )
                metadata[row["accession_8k"]] = {
                    "warm_start": warm_start,
                    "filed_8k": filed_8k,
                }
                if i % 1000 == 0:
                    print(f"metadata {i}/{len(population)}", flush=True)

            latest = _latest_accessions(population, metadata)

            for i, row in enumerate(population, start=1):
                warm_start = metadata[row["accession_8k"]]["warm_start"]
                latest_per_ticker = row["accession_8k"] in latest
                d_result = goal6.candidate_d(row["ticker"], row["accession_8k"], neo4j_session=session)
                e_result = goal6.candidate_e(row["ticker"], row["accession_8k"], neo4j_session=session)
                d_rows.append(
                    _measurement_row(
                        row,
                        d_result,
                        warm_start=warm_start,
                        latest_per_ticker=latest_per_ticker,
                    )
                )
                e_rows.append(
                    _measurement_row(
                        row,
                        e_result,
                        warm_start=warm_start,
                        latest_per_ticker=latest_per_ticker,
                    )
                )
                if i % 1000 == 0:
                    print(f"candidates {i}/{len(population)}", flush=True)
    finally:
        driver.close()

    return d_rows, e_rows


SUBSETS = [
    ("Full historical", "FULL_HISTORICAL", lambda r: True),
    ("Warm-start", "WARM_START", lambda r: r["warm_start"] == "true"),
    ("Cold-start", "COLD_START", lambda r: r["warm_start"] == "false"),
    ("Latest-per-ticker", "LATEST_PER_TICKER", lambda r: r["latest_per_ticker"] == "true"),
]


def _subset_counts(rows: list[dict], predicate) -> tuple[int, int, int]:
    correct = wrong = fc = 0
    for r in rows:
        if not predicate(r):
            continue
        if r["outcome"] == "FAIL_CLOSED":
            fc += 1
        elif r["correct"] == "true":
            correct += 1
        else:
            wrong += 1
    return correct, wrong, fc


def _pct(part: int, total: int) -> float:
    return 0.0 if total == 0 else 100.0 * part / total


def _table(rows: list[dict]) -> str:
    lines = [
        "| subset | rows | correct_AUTO_OK | wrong_AUTO_OK | fail_closed | correct_pct | wrong_pct | fc_pct |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label, _, pred in SUBSETS:
        c, w, f = _subset_counts(rows, pred)
        total = c + w + f
        lines.append(
            f"| {label} | {total} | {c} | {w} | {f} | "
            f"{_pct(c, total):.6f}% | {_pct(w, total):.6f}% | {_pct(f, total):.6f}% |"
        )
    return "\n".join(lines)


def _delta_table(d_rows: list[dict], e_rows: list[dict]) -> str:
    lines = [
        "| subset | d_correct_pct | e_correct_pct | delta_correct_pct_e_minus_d | d_wrong_pct | e_wrong_pct | delta_wrong_pct_e_minus_d |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for label, _, pred in SUBSETS:
        dc, dw, df = _subset_counts(d_rows, pred)
        ec, ew, ef = _subset_counts(e_rows, pred)
        dt = dc + dw + df
        et = ec + ew + ef
        dcp = _pct(dc, dt)
        ecp = _pct(ec, et)
        dwp = _pct(dw, dt)
        ewp = _pct(ew, et)
        lines.append(
            f"| {label} | {dcp:.6f}% | {ecp:.6f}% | {ecp - dcp:.6f}% | "
            f"{dwp:.6f}% | {ewp:.6f}% | {ewp - dwp:.6f}% |"
        )
    return "\n".join(lines)


def _write_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _goal4_counts(d_rows: list[dict]) -> tuple[int, int, int]:
    baseline = list(csv.DictReader(open(GOAL4_BASELINE_CSV, encoding="utf-8")))
    by_accn = {r["accession_8k"]: r for r in d_rows}
    preserved = regressed_fc = regressed_wrong = 0
    for b in baseline:
        d = by_accn[b["accession_8k"]]
        if d["outcome"] == "FAIL_CLOSED":
            regressed_fc += 1
        elif (d["fy"], d["q"]) == (b["fy"], b["q"]):
            preserved += 1
        else:
            regressed_wrong += 1
    return preserved, regressed_fc, regressed_wrong


def _nr_wrong_counts(d_rows: list[dict]) -> tuple[int, int, int]:
    nr = json.load(open(NR_AUDIT_JSON, encoding="utf-8"))
    truth = {
        r["accession_8k"]: (str(r["cleaned_audited_fy"]), str(r["cleaned_audited_q"]))
        for r in nr
        if r.get("final_verdict") == "wrong"
    }
    by_accn = {r["accession_8k"]: r for r in d_rows}
    still_wrong = now_fc = now_correct = 0
    for accn, (fy, q) in truth.items():
        d = by_accn[accn]
        if d["outcome"] == "FAIL_CLOSED":
            now_fc += 1
        elif (d["fy"], d["q"]) == (fy, q):
            now_correct += 1
        else:
            still_wrong += 1
    return still_wrong, now_fc, now_correct


def _flags(d_rows: list[dict], e_rows: list[dict]) -> dict[str, str]:
    flags: dict[str, str] = {}
    for label, rows in (("D", d_rows), ("E", e_rows)):
        for _, key, pred in SUBSETS:
            c, w, f = _subset_counts(rows, pred)
            flags[f"DECISION_FLAG_{label}_{key}_CORRECT"] = str(c)
            flags[f"DECISION_FLAG_{label}_{key}_WRONG"] = str(w)
            flags[f"DECISION_FLAG_{label}_{key}_FC"] = str(f)

    d_warm_c, d_warm_w, d_warm_f = _subset_counts(d_rows, dict((k, p) for _, k, p in SUBSETS)["WARM_START"])
    d_latest_c, d_latest_w, d_latest_f = _subset_counts(d_rows, dict((k, p) for _, k, p in SUBSETS)["LATEST_PER_TICKER"])
    warm_total = d_warm_c + d_warm_w + d_warm_f
    latest_total = d_latest_c + d_latest_w + d_latest_f
    flags["DECISION_FLAG_D_WARM_START_CORRECT_PCT"] = f"{_pct(d_warm_c, warm_total):.6f}"
    flags["DECISION_FLAG_D_WARM_START_WRONG_PCT"] = f"{_pct(d_warm_w, warm_total):.6f}"
    flags["DECISION_FLAG_D_LATEST_PER_TICKER_CORRECT_PCT"] = f"{_pct(d_latest_c, latest_total):.6f}"
    flags["DECISION_FLAG_D_LATEST_PER_TICKER_WRONG_PCT"] = f"{_pct(d_latest_w, latest_total):.6f}"

    preserved, regressed_fc, regressed_wrong = _goal4_counts(d_rows)
    flags["DECISION_FLAG_D_GOAL4_BASELINE_PRESERVED"] = str(preserved)
    flags["DECISION_FLAG_D_GOAL4_BASELINE_REGRESSED_FC"] = str(regressed_fc)
    flags["DECISION_FLAG_D_GOAL4_BASELINE_REGRESSED_WRONG"] = str(regressed_wrong)

    still_wrong, now_fc, now_correct = _nr_wrong_counts(d_rows)
    flags["DECISION_FLAG_D_CLEANED_NR_WRONG_STILL_WRONG"] = str(still_wrong)
    flags["DECISION_FLAG_D_CLEANED_NR_WRONG_FAIL_CLOSED"] = str(now_fc)
    flags["DECISION_FLAG_D_CLEANED_NR_WRONG_NOW_CORRECT"] = str(now_correct)

    ship = (
        _pct(d_warm_c, warm_total) >= 95.0
        and _pct(d_warm_w, warm_total) < 1.0
        and _pct(d_latest_c, latest_total) >= 95.0
        and _pct(d_latest_w, latest_total) < 1.0
    )
    flags["DECISION_FLAG_SHIP_D_DIRECTLY"] = "yes" if ship else "no"
    return flags


def write_report(d_rows: list[dict], e_rows: list[dict]) -> None:
    flags = _flags(d_rows, e_rows)
    lines = [
        "# Goal 6a Measurement Report",
        "",
        "Goal 6a is measurement-only. No production files under `scripts/earnings/` are modified by these artifacts.",
        "",
        "## Table 1 - D Measurement By Subset",
        "",
        _table(d_rows),
        "",
        "## Table 2 - E Measurement By Subset",
        "",
        _table(e_rows),
        "",
        "## Table 3 - D vs E Delta",
        "",
        _delta_table(d_rows, e_rows),
        "",
        "## Notes",
        "",
        "Candidate D is measured as a research-only reconstruction using the allowed 24h and 150d thresholds.",
        "Candidate E is a research-only policy comparison and is not a shipping candidate.",
        "",
        "## Decision Flags",
        "",
    ]
    for key in sorted(flags):
        lines.append(f"{key} = {flags[key]}")
    lines.append("")
    GOAL6A_REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    population = load_scoreable_population()
    print(f"population {len(population)}")
    d_rows, e_rows = build_measurements(population)
    _write_csv(D_MEASUREMENT_CSV, d_rows)
    _write_csv(E_MEASUREMENT_CSV, e_rows)
    write_report(d_rows, e_rows)
    print(f"wrote {D_MEASUREMENT_CSV}")
    print(f"wrote {E_MEASUREMENT_CSV}")
    print(f"wrote {GOAL6A_REPORT}")


if __name__ == "__main__":
    main()
