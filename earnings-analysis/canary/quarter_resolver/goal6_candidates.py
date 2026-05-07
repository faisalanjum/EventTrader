#!/usr/bin/env python3
"""RESEARCH-ONLY. Not imported by production. Goal 6a measurement only.

Candidate D and Candidate E are executable research reconstructions for
Goal 6a measurement. They deliberately live under the canary quarter resolver
folder and have no production side effects.

Candidate E is RESEARCH-ONLY, NOT a shipping candidate. Its industry keyed
guards are included only for policy comparison.
"""
from __future__ import annotations

from bisect import bisect_right
from datetime import date, datetime
from pathlib import Path
import sys

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_EARNINGS_DIR = _PROJECT_ROOT / "scripts/earnings"
_HELPER_DIR = _PROJECT_ROOT / ".claude/skills/earnings-orchestrator/scripts"
for _path in (str(_EARNINGS_DIR), str(_HELPER_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import quarter_identity as qi
from fiscal_math import period_to_fiscal
from get_quarterly_filings import parse_xbrl_fiscal_identity


_RECENT_XBRL_RISK_INDUSTRIES = {"RentalAndLeasingServices"}
_JAN_ANNUAL_RISK_INDUSTRIES = {"DiscountStores", "Entertainment", "GroceryStores"}
_JAN_ANNUAL_TIGHT_PRIOR_LAG_INDUSTRIES = {"SpecialtyRetail"}
_SAME_FILING_RISK_INDUSTRIES = {"ScientificAndTechnicalInstruments"}
_ANNUAL_RESIDUAL_RISK_INDUSTRIES = {"InsuranceLife"}

_CONTEXT_CACHE: dict[tuple[str, str], dict] = {}
_TICKER_CONTEXT_PRELOADED: set[str] = set()


_ROW_CONTEXT_QUERY = """
OPTIONAL MATCH (r_by_id:Report {id: $accession})
OPTIONAL MATCH (r_by_accession:Report {accessionNo: $accession})
WITH coalesce(r_by_id, r_by_accession) AS r
MATCH (r)-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE r.formType = '8-K'
  AND r.items CONTAINS '2.02'
WITH r, c

OPTIONAL CALL (c) {
  MATCH (k:Report)-[:PRIMARY_FILER]->(c)
  WHERE k.formType = '10-K' AND k.periodOfReport IS NOT NULL
  WITH date(k.periodOfReport).month AS m, count(*) AS cnt
  ORDER BY cnt DESC LIMIT 1
  RETURN m AS fye_month
}

OPTIONAL CALL (r, c) {
  MATCH (prev:Report)-[:PRIMARY_FILER]->(c)
  WHERE prev.formType = '8-K'
    AND prev.items CONTAINS '2.02'
    AND datetime(prev.created) < datetime(r.created)
  RETURN prev.created AS prev_8k_ts
  ORDER BY datetime(prev.created) DESC LIMIT 1
}

OPTIONAL CALL (r, c) {
  MATCH (p:Report)-[:PRIMARY_FILER]->(c)
  WHERE p.formType IN ['10-Q', '10-K']
    AND p.periodOfReport IS NOT NULL
    AND datetime(p.created) <= datetime(r.created)
  WITH p
  ORDER BY datetime(p.created) DESC
  LIMIT 12
  RETURN collect({
    accession: coalesce(p.id, p.accessionNo),
    created: p.created,
    period: p.periodOfReport,
    form: p.formType
  }) AS priors
}

RETURN coalesce(r.id, r.accessionNo) AS accession_8k,
       r.id AS report_id,
       r.accessionNo AS accession_no,
       r.created AS filed_8k,
       r.market_session AS market_session,
       c.industry_normalized AS industry_normalized,
       fye_month,
       prev_8k_ts,
       priors
"""


_TICKER_CONTEXT_QUERY = """
MATCH (c:Company {ticker: $ticker})
OPTIONAL CALL (c) {
  MATCH (k:Report)-[:PRIMARY_FILER]->(c)
  WHERE k.formType = '10-K' AND k.periodOfReport IS NOT NULL
  WITH date(k.periodOfReport).month AS m, count(*) AS cnt
  ORDER BY cnt DESC LIMIT 1
  RETURN m AS fye_month
}
MATCH (r:Report)-[:PRIMARY_FILER]->(c)
WHERE r.formType = '8-K'
  AND r.items CONTAINS '2.02'
WITH r, c, fye_month

OPTIONAL CALL (r, c) {
  MATCH (prev:Report)-[:PRIMARY_FILER]->(c)
  WHERE prev.formType = '8-K'
    AND prev.items CONTAINS '2.02'
    AND datetime(prev.created) < datetime(r.created)
  RETURN prev.created AS prev_8k_ts
  ORDER BY datetime(prev.created) DESC LIMIT 1
}

OPTIONAL CALL (r, c) {
  MATCH (p:Report)-[:PRIMARY_FILER]->(c)
  WHERE p.formType IN ['10-Q', '10-K']
    AND p.periodOfReport IS NOT NULL
    AND datetime(p.created) <= datetime(r.created)
  WITH p
  ORDER BY datetime(p.created) DESC
  LIMIT 12
  RETURN collect({
    accession: coalesce(p.id, p.accessionNo),
    created: p.created,
    period: p.periodOfReport,
    form: p.formType
  }) AS priors
}

RETURN coalesce(r.id, r.accessionNo) AS accession_8k,
       r.id AS report_id,
       r.accessionNo AS accession_no,
       r.created AS filed_8k,
       r.market_session AS market_session,
       c.industry_normalized AS industry_normalized,
       fye_month,
       prev_8k_ts,
       priors
ORDER BY datetime(r.created)
"""


_ACCESSION_CONTEXT_QUERY = """
UNWIND $rows AS item
OPTIONAL MATCH (r_by_id:Report {id: item.accession})
OPTIONAL MATCH (r_by_accession:Report {accessionNo: item.accession})
WITH item, coalesce(r_by_id, r_by_accession) AS r
MATCH (r)-[:PRIMARY_FILER]->(c:Company {ticker: item.ticker})
WHERE r.formType = '8-K'
  AND r.items CONTAINS '2.02'
WITH item, r, c

OPTIONAL CALL (c) {
  MATCH (k:Report)-[:PRIMARY_FILER]->(c)
  WHERE k.formType = '10-K' AND k.periodOfReport IS NOT NULL
  WITH date(k.periodOfReport).month AS m, count(*) AS cnt
  ORDER BY cnt DESC LIMIT 1
  RETURN m AS fye_month
}

OPTIONAL CALL (r, c) {
  MATCH (prev:Report)-[:PRIMARY_FILER]->(c)
  WHERE prev.formType = '8-K'
    AND prev.items CONTAINS '2.02'
    AND datetime(prev.created) < datetime(r.created)
  RETURN prev.created AS prev_8k_ts
  ORDER BY datetime(prev.created) DESC LIMIT 1
}

OPTIONAL CALL (r, c) {
  MATCH (p:Report)-[:PRIMARY_FILER]->(c)
  WHERE p.formType IN ['10-Q', '10-K']
    AND p.periodOfReport IS NOT NULL
    AND datetime(p.created) <= datetime(r.created)
  WITH p
  ORDER BY datetime(p.created) DESC
  LIMIT 12
  RETURN collect({
    accession: coalesce(p.id, p.accessionNo),
    created: p.created,
    period: p.periodOfReport,
    form: p.formType
  }) AS priors
}

RETURN item.ticker AS ticker,
       item.accession AS requested_accession,
       coalesce(r.id, r.accessionNo) AS accession_8k,
       r.id AS report_id,
       r.accessionNo AS accession_no,
       r.created AS filed_8k,
       r.market_session AS market_session,
       c.industry_normalized AS industry_normalized,
       fye_month,
       prev_8k_ts,
       priors
"""


_LIGHT_COMPANY_QUERY = """
MATCH (c:Company {ticker: $ticker})
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


_LIGHT_EARNINGS_8K_QUERY = """
MATCH (c:Company {ticker: $ticker})<-[:PRIMARY_FILER]-(r:Report)
WHERE r.formType = '8-K'
  AND r.items CONTAINS '2.02'
RETURN c.ticker AS ticker,
       coalesce(r.id, r.accessionNo) AS accession_8k,
       r.id AS report_id,
       r.accessionNo AS accession_no,
       r.created AS filed_8k,
       r.market_session AS market_session
ORDER BY datetime(r.created)
"""


_LIGHT_PERIODIC_QUERY = """
MATCH (c:Company {ticker: $ticker})<-[:PRIMARY_FILER]-(p:Report)
WHERE p.formType IN ['10-Q', '10-K']
  AND p.periodOfReport IS NOT NULL
RETURN c.ticker AS ticker,
       coalesce(p.id, p.accessionNo) AS accession,
       p.created AS created,
       p.periodOfReport AS period,
       p.formType AS form
ORDER BY datetime(p.created)
"""


def _clean(value) -> str:
    return "" if value is None else str(value).strip()


def _to_bool_text(value: bool) -> str:
    return "true" if value else "false"


def _parse_dt(value) -> datetime | None:
    return qi._parse_datetime(qi._to_str(value))


def _return(outcome: str, fy, q, source: str) -> dict:
    if outcome != "AUTO_OK":
        return {"outcome": "FAIL_CLOSED", "fy": "", "q": "", "source": source}
    return {"outcome": "AUTO_OK", "fy": str(fy), "q": str(q), "source": source}


def _fc(source: str) -> dict:
    return _return("FAIL_CLOSED", "", "", source)


def _auto(fy, q, source: str) -> dict:
    return _return("AUTO_OK", fy, q, source)


def _namespace_e(result: dict) -> dict:
    result = dict(result)
    source = _clean(result.get("source"))
    if not source.startswith("candidate_e_"):
        result["source"] = f"candidate_e_{source}"
    return result


def _record_to_dict(row) -> dict:
    data = row.data() if hasattr(row, "data") else dict(row)
    return {
        "accession_8k": _clean(data.get("accession_8k")),
        "ticker": _clean(data.get("ticker")),
        "report_id": _clean(data.get("report_id")),
        "accession_no": _clean(data.get("accession_no")),
        "filed_8k": _clean(qi._to_str(data.get("filed_8k"))),
        "market_session": data.get("market_session"),
        "industry_normalized": _clean(data.get("industry_normalized")),
        "fye_month": qi._parse_fye(data.get("fye_month")),
        "prev_8k_ts": _clean(qi._to_str(data.get("prev_8k_ts"))),
        "_prefetched_priors": data.get("priors") or [],
    }


def _cache_context(ticker: str, row) -> dict:
    data = _record_to_dict(row)
    keys = {
        _clean(data.get("accession_8k")),
        _clean(data.get("report_id")),
        _clean(data.get("accession_no")),
    }
    for accession in keys:
        if accession:
            _CONTEXT_CACHE[(ticker, accession)] = data
    return data


def preload_ticker_contexts(ticker: str, *, neo4j_session) -> None:
    """Optional generator helper: preload research row contexts by ticker."""
    ticker = ticker.upper()
    if ticker in _TICKER_CONTEXT_PRELOADED:
        return
    _preload_ticker_contexts_light(ticker, neo4j_session=neo4j_session)
    _TICKER_CONTEXT_PRELOADED.add(ticker)


def _preload_ticker_contexts_light(ticker: str, *, neo4j_session) -> None:
    company_row = neo4j_session.run(_LIGHT_COMPANY_QUERY, ticker=ticker).single()
    if company_row is None:
        return
    company = {
        "fye_month": qi._parse_fye(company_row["fye_month"]),
        "industry_normalized": _clean(company_row["industry_normalized"]),
    }

    eightks = []
    for rec in neo4j_session.run(_LIGHT_EARNINGS_8K_QUERY, ticker=ticker):
        filed_8k = _clean(qi._to_str(rec["filed_8k"]))
        eightks.append({
            "accession_8k": _clean(rec["accession_8k"]),
            "report_id": _clean(rec["report_id"]),
            "accession_no": _clean(rec["accession_no"]),
            "filed_8k": filed_8k,
            "filed_dt": _parse_dt(filed_8k),
            "market_session": rec["market_session"],
        })

    periodics = []
    for rec in neo4j_session.run(_LIGHT_PERIODIC_QUERY, ticker=ticker):
        created = _clean(qi._to_str(rec["created"]))
        created_dt = _parse_dt(created)
        if created_dt is None:
            continue
        periodics.append({
            "accession": _clean(rec["accession"]),
            "created": created,
            "created_dt": created_dt,
            "period": _clean(qi._to_str(rec["period"]))[:10],
            "form": _clean(rec["form"]).replace("/A", ""),
        })

    periodic_times = [p["created_dt"] for p in periodics]
    previous_filed = ""
    for row in eightks:
        filed_dt = row["filed_dt"]
        idx = bisect_right(periodic_times, filed_dt) if filed_dt is not None else 0
        priors = []
        for prior in reversed(periodics[:idx]):
            priors.append({
                "accession": prior["accession"],
                "created": prior["created"],
                "period": prior["period"],
                "form": prior["form"],
            })
            if len(priors) >= 12:
                break
        context = {
            "accession_8k": row["accession_8k"],
            "ticker": ticker,
            "filed_8k": row["filed_8k"],
            "market_session": row["market_session"],
            "industry_normalized": company["industry_normalized"],
            "fye_month": company["fye_month"],
            "prev_8k_ts": previous_filed,
            "_prefetched_priors": priors,
        }
        for key in {row["accession_8k"], row["report_id"], row["accession_no"]}:
            if key:
                _CONTEXT_CACHE[(ticker, key)] = context
        previous_filed = row["filed_8k"]


def preload_accession_contexts(rows: list[dict], *, neo4j_session, chunk_size: int = 100) -> None:
    """Preload just the requested ticker/accession contexts for measurement."""
    for start in range(0, len(rows), chunk_size):
        chunk = [
            {"ticker": r["ticker"].upper(), "accession": r["accession_8k"]}
            for r in rows[start:start + chunk_size]
        ]
        seen = set()
        for row in neo4j_session.run(_ACCESSION_CONTEXT_QUERY, rows=chunk):
            data = _cache_context(_clean(row["ticker"]), row)
            ticker = _clean(data.get("ticker"))
            if ticker:
                seen.add((ticker, _clean(data.get("accession_8k"))))


def _fetch_row_context(ticker: str, accession_8k: str, *, neo4j_session) -> dict:
    ticker = ticker.upper()
    accession_8k = _clean(accession_8k)
    cached = _CONTEXT_CACHE.get((ticker, accession_8k))
    if cached is not None:
        return cached
    row = neo4j_session.run(
        _ROW_CONTEXT_QUERY,
        ticker=ticker,
        accession=accession_8k,
    ).single()
    if row is None:
        raise ValueError(f"8-K {accession_8k} not found for {ticker}")
    return _cache_context(ticker, row)


def row_has_warm_start(ticker: str, accession_8k: str, *, neo4j_session) -> bool:
    context = _fetch_row_context(ticker, accession_8k, neo4j_session=neo4j_session)
    priors = qi._prior_rows(context, neo4j_session=neo4j_session)
    return bool(priors)


def row_filed_8k(ticker: str, accession_8k: str, *, neo4j_session) -> str:
    context = _fetch_row_context(ticker, accession_8k, neo4j_session=neo4j_session)
    return _clean(context.get("filed_8k"))


def _parse_prior_math(period: date, effective_fye: int, form: str):
    try:
        return period_to_fiscal(
            period.year,
            period.month,
            period.day,
            effective_fye,
            form,
        )
    except Exception:
        return None


def _same_filing_cycle_indicator(
    *,
    prev_8k_ts: str,
    prior_created: datetime,
    filed: datetime,
) -> bool:
    """Structural same-cycle signal using only ordering and the 24h threshold.

    Goal 6a forbids new time thresholds. The broad 150d projection window is
    handled by the existing long-gap gate; this same-cycle guard is therefore
    limited to the already-locked 24h proximity interval.
    """
    prev = qi._parse_datetime(prev_8k_ts)
    if prev is None:
        return False
    seconds_between = (filed - prior_created).total_seconds()
    return prev < prior_created <= filed and 0 <= seconds_between < 24 * 3600


def _within_existing_short_gap(*, filed: datetime, prior_created: datetime) -> bool:
    seconds_between = (filed - prior_created).total_seconds()
    if 0 <= seconds_between < 24 * 3600:
        return True
    gap_days = (filed.date() - prior_created.date()).days
    return 0 <= gap_days <= 150


def _calendar_branch_with_candidate_guards(
    *,
    context: dict,
    priors: list[dict],
    top: dict,
    filed: datetime,
    period: date,
    prior_created: datetime,
    form: str,
    effective_fye: int,
    candidate_e: bool,
    neo4j_session,
) -> dict:
    top = qi._ensure_prior_xbrl(top, neo4j_session=neo4j_session)
    industry = _clean(context.get("industry_normalized"))
    prev_8k_ts = _clean(context.get("prev_8k_ts"))
    gap_days = (filed.date() - prior_created.date()).days
    if gap_days < 0:
        return _fc("prior_periodic_projection_future_prior_fail_closed")
    if gap_days > 150:
        return _fc("prior_periodic_projection_long_gap_fail_closed")

    seconds_between = (filed - prior_created).total_seconds()
    is_recent = 0 <= seconds_between < 24 * 3600
    xbrl_parsed = parse_xbrl_fiscal_identity(
        top.get("xbrl_year"), top.get("xbrl_period")
    )
    math_parsed_prior = _parse_prior_math(period, effective_fye, form)

    if candidate_e and is_recent and industry in _RECENT_XBRL_RISK_INDUSTRIES:
        return _fc("candidate_e_rule_g_fail_closed_recent_industry_calendar")

    if is_recent:
        if xbrl_parsed is None or math_parsed_prior is None:
            source = (
                "candidate_e_rule_g_strict_fail_closed_recent_no_xbrl_calendar"
                if candidate_e
                else "rule_g_strict_fail_closed_recent_disagreement_calendar"
            )
            return _fc(source)
        if (
            str(xbrl_parsed[0]) != str(math_parsed_prior[0])
            or str(xbrl_parsed[1]) != str(math_parsed_prior[1])
        ):
            source = (
                "candidate_e_rule_g_strict_fail_closed_recent_disagreement_calendar"
                if candidate_e
                else "rule_g_strict_fail_closed_recent_disagreement_calendar"
            )
            return _fc(source)
        source = (
            "candidate_e_rule_g_strict_direct_recent_prior_calendar"
            if candidate_e
            else "rule_g_strict_direct_recent_prior_calendar"
        )
        return _auto(xbrl_parsed[0], xbrl_parsed[1], source)

    if (
        xbrl_parsed is not None
        and math_parsed_prior is not None
        and str(xbrl_parsed[0]) != str(math_parsed_prior[0])
    ):
        source = (
            "candidate_e_rule_g_fail_closed_fy_disagreement_calendar"
            if candidate_e
            else "rule_g_fail_closed_fy_disagreement_calendar"
        )
        return _fc(source)

    if candidate_e:
        if (
            form == "10-K"
            and period.month == 1
            and industry in _JAN_ANNUAL_RISK_INDUSTRIES
        ):
            return _fc("candidate_e_rule_g_fail_closed_jan_annual_industry_calendar")
        if (
            form == "10-K"
            and period.month == 1
            and industry in _JAN_ANNUAL_TIGHT_PRIOR_LAG_INDUSTRIES
        ):
            return _fc("candidate_e_rule_g_fail_closed_jan_annual_industry_calendar")
        if form == "10-K" and industry in _ANNUAL_RESIDUAL_RISK_INDUSTRIES:
            return _fc("candidate_e_rule_g_fail_closed_partial_history_annual_calendar")

    if not prev_8k_ts and _within_existing_short_gap(
        filed=filed, prior_created=prior_created
    ):
        source = (
            "candidate_e_rule_g_fail_closed_no_prev_short_gap_calendar"
            if candidate_e
            else "rule_g_fail_closed_no_prev_short_gap_calendar"
        )
        return _fc(source)

    same_filing = _same_filing_cycle_indicator(
        prev_8k_ts=prev_8k_ts,
        prior_created=prior_created,
        filed=filed,
    )
    if same_filing and _within_existing_short_gap(
        filed=filed, prior_created=prior_created
    ):
        source = (
            "candidate_e_rule_g_fail_closed_same_filing_short_gap_calendar"
            if candidate_e
            else "rule_g_fail_closed_same_filing_short_gap_calendar"
        )
        return _fc(source)

    if candidate_e and same_filing:
        last_day = qi.calendar.monthrange(period.year, period.month)[1]
        if period.day != last_day:
            return _fc("candidate_e_rule_g_fail_closed_non_month_end_same_filing_calendar")
        if industry in _SAME_FILING_RISK_INDUSTRIES:
            return _fc("candidate_e_rule_g_fail_closed_same_filing_short_gap_calendar")

    try:
        prior_fy, prior_q = period_to_fiscal(
            period.year,
            period.month,
            period.day,
            effective_fye,
            form,
        )
    except Exception:
        return _fc("prior_periodic_projection_fiscal_math_error")

    advanced = qi._advance_quarter(int(prior_fy), str(prior_q))
    if advanced is None:
        return _fc("prior_periodic_projection_bad_prior_quarter")

    fy, q = advanced
    source = f"prior_periodic_projection_{str(prior_q).lower()}_to_{q.lower()}"
    fye_month = context.get("fye_month")
    if fye_month is not None and effective_fye != fye_month:
        source += "_effective_fye_from_prior_10k"
    return _auto(fy, q, source)


def _resolve_candidate(
    ticker: str,
    accession_8k: str,
    *,
    neo4j_session,
    candidate_e: bool,
) -> dict:
    ticker = ticker.upper()
    context = _fetch_row_context(ticker, accession_8k, neo4j_session=neo4j_session)
    fye_month = qi._parse_fye(context.get("fye_month"))
    if fye_month is None:
        return _fc("prior_periodic_projection_no_fye")

    filed = qi._parse_datetime(context.get("filed_8k"))
    if filed is None:
        return _fc("prior_periodic_projection_bad_filing_time")

    priors = qi._prior_rows(context, neo4j_session=neo4j_session)
    if not priors:
        return _fc("prior_periodic_projection_no_prior")

    effective_fye = qi._effective_fye_month(priors, fye_month)
    top = priors[0]

    if top.get("accession") in qi._DENY_PRIOR_ACCESSIONS:
        return _fc("prior_periodic_projection_denylisted_prior_fail_closed")

    period = qi._parse_date(top.get("period"))
    prior_created = qi._parse_datetime(top.get("created"))
    form = top.get("form") or ""
    if period is None or prior_created is None or form not in {"10-Q", "10-K"}:
        return _fc("prior_periodic_projection_bad_prior_context")

    if not qi._period_end_is_calendar_shaped(period):
        result = qi.resolve_quarter_via_prior_periodic(context, neo4j_session=neo4j_session)
        outcome = "AUTO_OK" if result.get("safety_action") == "AUTO_OK" else "FAIL_CLOSED"
        return _return(outcome, result.get("fy"), result.get("q"), result.get("source") or "unknown")

    result = _calendar_branch_with_candidate_guards(
        context=context,
        priors=priors,
        top=top,
        filed=filed,
        period=period,
        prior_created=prior_created,
        form=form,
        effective_fye=effective_fye,
        candidate_e=candidate_e,
        neo4j_session=neo4j_session,
    )
    if candidate_e:
        return _namespace_e(result)
    return result


def candidate_d(ticker: str, accession_8k: str, *, neo4j_session) -> dict:
    """Return Candidate D's {outcome, fy, q, source} for one 8-K."""
    return _resolve_candidate(
        ticker,
        accession_8k,
        neo4j_session=neo4j_session,
        candidate_e=False,
    )


def candidate_e(ticker: str, accession_8k: str, *, neo4j_session) -> dict:
    """Return Candidate E's research-only {outcome, fy, q, source}."""
    return _resolve_candidate(
        ticker,
        accession_8k,
        neo4j_session=neo4j_session,
        candidate_e=True,
    )


__all__ = [
    "candidate_d",
    "candidate_e",
    "preload_accession_contexts",
    "preload_ticker_contexts",
    "row_filed_8k",
    "row_has_warm_start",
]
