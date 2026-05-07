#!/usr/bin/env python3
"""Quarter identity resolver -- single canonical source of truth.

Goal 6c production resolver:
  - Uses the PIT-visible prior periodic projection proven in Goal 3.
  - Replaces only the odd 52/53-week fail-closed branch with Rule F.
  - Adds Candidate D's calendar-branch safety guards.
  - Returns the existing quarter_info shape, plus safety_action.
"""
from __future__ import annotations

import calendar
import os
import sys
from datetime import date, datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT / ".claude/skills/earnings-orchestrator/scripts"))
sys.path.insert(0, str(_PROJECT_ROOT / "scripts/earnings"))

from fiscal_math import period_to_fiscal, _compute_fiscal_dates
from fye_month import get_fye_month
from get_quarterly_filings import (
    parse_xbrl_fiscal_identity,
    XBRL_DENY_PERIODIC_ACCESSIONS,
)


_VALID_QUARTERS = {"Q1", "Q2", "Q3", "Q4"}
_DENY_PRIOR_ACCESSIONS = XBRL_DENY_PERIODIC_ACCESSIONS
_PRIOR_CACHE: dict[tuple[str, str], list[dict]] = {}
_FYE_CACHE: dict[str, int] = {}
_XBRL_CACHE: dict[str, tuple[object, object]] = {}
_CONTEXT_CACHE: dict[tuple[str, str], dict] = {}
_TICKER_CONTEXT_PRELOADED: set[str] = set()
_NEO4J_DRIVER = None


# 8-K metadata only. The quarter label is resolved by
# resolve_quarter_via_prior_periodic(), not by 8-K periodOfReport.
_QUERY = """
MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE r.formType = '8-K'
  AND r.items CONTAINS '2.02'
  AND (r.id = $accession OR r.accessionNo = $accession)
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
       r.created AS filed_8k,
       r.market_session AS market_session,
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
       fye_month,
       prev_8k_ts,
       priors
ORDER BY datetime(r.created)
"""


_PRIOR_QUERY = """
MATCH (this:Report)-[:PRIMARY_FILER]->(c:Company)
WHERE (this.id = $accession_8k OR this.accessionNo = $accession_8k)
MATCH (p:Report)-[:PRIMARY_FILER]->(c)
WHERE p.formType IN ['10-Q', '10-K']
  AND p.periodOfReport IS NOT NULL
  AND datetime(p.created) <= datetime($filed_8k)
WITH p
ORDER BY datetime(p.created) DESC
LIMIT 12
OPTIONAL MATCH (p)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(fp:Fact {qname: 'dei:DocumentFiscalPeriodFocus'})
WITH p, collect(DISTINCT fp.value) AS xbrl_periods
OPTIONAL MATCH (p)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(fy:Fact {qname: 'dei:DocumentFiscalYearFocus'})
WITH p, xbrl_periods, collect(DISTINCT fy.value) AS xbrl_years
RETURN coalesce(p.id, p.accessionNo) AS accession,
       p.created AS created,
       p.periodOfReport AS period,
       p.formType AS form,
       CASE WHEN size(xbrl_periods) = 1 THEN head(xbrl_periods) END AS xbrl_period,
       CASE WHEN size(xbrl_years) = 1 THEN head(xbrl_years) END AS xbrl_year
"""


_XBRL_QUERY = """
MATCH (p:Report)
WHERE p.id = $accession OR p.accessionNo = $accession
OPTIONAL MATCH (p)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(fp:Fact {qname: 'dei:DocumentFiscalPeriodFocus'})
WITH p, collect(DISTINCT fp.value) AS xbrl_periods
OPTIONAL MATCH (p)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(fy:Fact {qname: 'dei:DocumentFiscalYearFocus'})
WITH p, xbrl_periods, collect(DISTINCT fy.value) AS xbrl_years
RETURN CASE WHEN size(xbrl_periods) = 1 THEN head(xbrl_periods) END AS xbrl_period,
       CASE WHEN size(xbrl_years) = 1 THEN head(xbrl_years) END AS xbrl_year
"""


def _record_get(record, key: str, default=None):
    if record is None:
        return default
    if hasattr(record, "get"):
        return record.get(key, default)
    try:
        return record[key]
    except (KeyError, TypeError):
        return default


def _to_str(val) -> str | None:
    """Convert Neo4j values to ISO-ish strings."""
    if val is None:
        return None
    if hasattr(val, "to_native"):
        val = val.to_native()
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val)


def _clean(value) -> str:
    return "" if value is None else str(value).strip()


def _parse_datetime(value) -> datetime | None:
    text = _clean(_to_str(value) if value is not None else value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_date(value) -> date | None:
    text = _clean(_to_str(value) if value is not None else value)[:10]
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _parse_fye(value) -> int | None:
    text = _clean(value)
    if not text:
        return None
    try:
        month = int(text)
    except ValueError:
        return None
    if 1 <= month <= 12:
        return month
    return None


def _result(fy, q, source: str, safety_action: str) -> dict:
    return {
        "fy": fy,
        "q": q,
        "source": source,
        "safety_action": safety_action,
    }


def _advance_quarter(fy: int, q: str) -> tuple[int, str] | None:
    if q not in _VALID_QUARTERS:
        return None
    q_num = int(q[1])
    if q_num == 4:
        return fy + 1, "Q1"
    return fy, f"Q{q_num + 1}"


def advance_one_quarter(fy, q):
    if q == "FY":
        q = "Q4"
    return _advance_quarter(int(fy), str(q))


def _period_end_is_calendar_shaped(period: date) -> bool:
    last_day = calendar.monthrange(period.year, period.month)[1]
    return period.day <= 5 or (last_day - period.day) <= 5


def _adjusted_fye_from_annual_period(period: date) -> int:
    if period.day <= 5:
        return period.month - 1 if period.month > 1 else 12
    return period.month


def _normalize_prior_record(rec) -> dict:
    return {
        "accession": _clean(_record_get(rec, "accession")),
        "created": _clean(_to_str(_record_get(rec, "created"))),
        "period": _clean(_to_str(_record_get(rec, "period")))[:10],
        "form": _clean(_record_get(rec, "form")).replace("/A", ""),
        "xbrl_period": _record_get(rec, "xbrl_period"),
        "xbrl_year": _record_get(rec, "xbrl_year"),
    }


def _prior_rows(row_context: dict, *, neo4j_session) -> list[dict]:
    if "_prefetched_priors" in row_context:
        records = []
        for rec in row_context.get("_prefetched_priors") or []:
            normalized = _normalize_prior_record(rec)
            if not any(normalized.get(k) for k in ("accession", "created", "period", "form")):
                continue
            records.append(normalized)
        return records

    accession = _clean(row_context.get("accession_8k"))
    filed = _clean(row_context.get("filed_8k"))
    if not accession or not filed:
        return []

    key = (accession, filed)
    if key in _PRIOR_CACHE:
        return _PRIOR_CACHE[key]

    records = []
    for rec in neo4j_session.run(
        _PRIOR_QUERY,
        accession_8k=accession,
        filed_8k=filed,
    ):
        normalized = _normalize_prior_record(rec)
        if not any(normalized.get(k) for k in ("accession", "created", "period", "form")):
            continue
        records.append(normalized)
    _PRIOR_CACHE[key] = records
    return records


def _ensure_prior_xbrl(prior: dict, *, neo4j_session) -> dict:
    if prior.get("xbrl_period") is not None or prior.get("xbrl_year") is not None:
        return prior
    accession = _clean(prior.get("accession"))
    if not accession:
        return prior
    if accession in _XBRL_CACHE:
        xbrl_period, xbrl_year = _XBRL_CACHE[accession]
    else:
        row = neo4j_session.run(_XBRL_QUERY, accession=accession).single()
        xbrl_period = _record_get(row, "xbrl_period")
        xbrl_year = _record_get(row, "xbrl_year")
        _XBRL_CACHE[accession] = (xbrl_period, xbrl_year)
    enriched = dict(prior)
    enriched["xbrl_period"] = xbrl_period
    enriched["xbrl_year"] = xbrl_year
    return enriched


def _within_existing_short_gap(*, filed: datetime, prior_created: datetime) -> bool:
    seconds_between = (filed - prior_created).total_seconds()
    if 0 <= seconds_between < 24 * 3600:
        return True
    gap_days = (filed.date() - prior_created.date()).days
    return 0 <= gap_days <= 150


def _same_filing_cycle_indicator(
    *,
    prev_8k_ts: str,
    prior_created: datetime,
    filed: datetime,
) -> bool:
    prev = _parse_datetime(prev_8k_ts)
    if prev is None:
        return False
    seconds_between = (filed - prior_created).total_seconds()
    return prev < prior_created <= filed and 0 <= seconds_between < 24 * 3600


def _effective_fye_month(priors: list[dict], default_fye: int) -> int:
    for prior in priors:
        if prior.get("form") != "10-K":
            continue
        period = _parse_date(prior.get("period"))
        if period is not None and _period_end_is_calendar_shaped(period):
            return _adjusted_fye_from_annual_period(period)
    return default_fye


def _resolved_period_end(fy, q, fye_month: int) -> str | None:
    if fy is None or q is None:
        return None
    try:
        _, end_str = _compute_fiscal_dates(fye_month, int(fy), str(q))
        return end_str
    except Exception:
        return None


def _form_for_quarter(q) -> str | None:
    if q is None:
        return None
    return "10-K" if str(q) == "Q4" else "10-Q"


def _attach_resolution_context(
    result: dict,
    *,
    period_of_report: str | None = None,
    form_type_periodic: str | None = None,
    accession_periodic: str = "",
) -> dict:
    result["period_of_report"] = period_of_report
    result["form_type_periodic"] = form_type_periodic
    result["accession_periodic"] = accession_periodic
    return result


def resolve_quarter_via_prior_periodic(row_context: dict, *, neo4j_session) -> dict:
    """Goal 6c production resolver.

    Mirrors Goal 3 _prior_periodic_projection structure, preserves Rule F for
    odd 52/53-week priors, and adds Candidate D guards for calendar-shaped
    priors.
    """
    fye_month = _parse_fye(row_context.get("fye_month"))
    if fye_month is None:
        return _result(None, None, "prior_periodic_projection_no_fye", "NO_RESOLUTION")

    filed = _parse_datetime(row_context.get("filed_8k"))
    if filed is None:
        return _result(None, None, "prior_periodic_projection_bad_filing_time", "NO_RESOLUTION")

    priors = _prior_rows(row_context, neo4j_session=neo4j_session)
    if not priors:
        return _result(None, None, "prior_periodic_projection_no_prior", "FAIL_CLOSED")

    effective_fye = _effective_fye_month(priors, fye_month)
    top = priors[0]

    if top.get("accession") in _DENY_PRIOR_ACCESSIONS:
        return _result(None, None, "prior_periodic_projection_denylisted_prior_fail_closed", "FAIL_CLOSED")

    period = _parse_date(top.get("period"))
    prior_created = _parse_datetime(top.get("created"))
    form = top.get("form") or ""
    if period is None or prior_created is None or form not in {"10-Q", "10-K"}:
        return _result(None, None, "prior_periodic_projection_bad_prior_context", "NO_RESOLUTION")

    if not _period_end_is_calendar_shaped(period):
        top = _ensure_prior_xbrl(top, neo4j_session=neo4j_session)
        seconds_between = (filed - prior_created).total_seconds()
        is_recent = 0 <= seconds_between < 24 * 3600

        xbrl_parsed = parse_xbrl_fiscal_identity(
            top.get("xbrl_year"), top.get("xbrl_period")
        )

        if is_recent:
            if xbrl_parsed is None:
                return _result(None, None, "rule_f_fail_closed_recent_no_xbrl", "FAIL_CLOSED")
            fy, q = str(xbrl_parsed[0]), xbrl_parsed[1]
            return _attach_resolution_context(
                _result(fy, q, "rule_f_direct_recent_prior", "AUTO_OK"),
                period_of_report=period.isoformat(),
                form_type_periodic=form,
                accession_periodic=top.get("accession") or "",
            )

        try:
            math_parsed = period_to_fiscal(
                period.year,
                period.month,
                period.day,
                effective_fye,
                form,
            )
        except Exception:
            math_parsed = None

        if xbrl_parsed is None or math_parsed is None:
            return _result(None, None, "rule_f_fail_closed_missing_signal", "FAIL_CLOSED")
        if str(xbrl_parsed[0]) != str(math_parsed[0]):
            return _result(None, None, "rule_f_fail_closed_fy_disagreement", "FAIL_CLOSED")

        advanced = _advance_quarter(int(xbrl_parsed[0]), str(xbrl_parsed[1]))
        if advanced is None:
            return _result(None, None, "prior_periodic_projection_bad_prior_quarter", "NO_RESOLUTION")
        fy, q = advanced
        return _attach_resolution_context(
            _result(fy, q, "rule_f_advance_xbrl", "AUTO_OK"),
            period_of_report=_resolved_period_end(fy, q, effective_fye),
            form_type_periodic=_form_for_quarter(q),
        )

    gap_days = (filed.date() - prior_created.date()).days
    if gap_days < 0:
        return _result(None, None, "prior_periodic_projection_future_prior_fail_closed", "FAIL_CLOSED")
    if gap_days > 150:
        return _result(None, None, "prior_periodic_projection_long_gap_fail_closed", "FAIL_CLOSED")

    top = _ensure_prior_xbrl(top, neo4j_session=neo4j_session)
    seconds_between = (filed - prior_created).total_seconds()
    is_recent = 0 <= seconds_between < 24 * 3600
    xbrl_parsed = parse_xbrl_fiscal_identity(
        top.get("xbrl_year"), top.get("xbrl_period")
    )
    try:
        math_parsed_prior = period_to_fiscal(
            period.year,
            period.month,
            period.day,
            effective_fye,
            form,
        )
    except Exception:
        math_parsed_prior = None

    if is_recent:
        if xbrl_parsed is None or math_parsed_prior is None:
            return _result(
                None,
                None,
                "rule_g_strict_fail_closed_recent_disagreement_calendar",
                "FAIL_CLOSED",
            )
        if (
            str(xbrl_parsed[0]) != str(math_parsed_prior[0])
            or str(xbrl_parsed[1]) != str(math_parsed_prior[1])
        ):
            return _result(
                None,
                None,
                "rule_g_strict_fail_closed_recent_disagreement_calendar",
                "FAIL_CLOSED",
            )
        return _attach_resolution_context(
            _result(
                xbrl_parsed[0],
                xbrl_parsed[1],
                "rule_g_strict_direct_recent_prior_calendar",
                "AUTO_OK",
            ),
            period_of_report=period.isoformat(),
            form_type_periodic=form,
            accession_periodic=top.get("accession") or "",
        )

    if (
        xbrl_parsed is not None
        and math_parsed_prior is not None
        and str(xbrl_parsed[0]) != str(math_parsed_prior[0])
    ):
        return _result(
            None,
            None,
            "rule_g_fail_closed_fy_disagreement_calendar",
            "FAIL_CLOSED",
        )

    prev_8k_ts = _clean(row_context.get("prev_8k_ts"))
    if not prev_8k_ts and _within_existing_short_gap(
        filed=filed, prior_created=prior_created
    ):
        return _result(
            None,
            None,
            "rule_g_fail_closed_no_prev_short_gap_calendar",
            "FAIL_CLOSED",
        )

    if _same_filing_cycle_indicator(
        prev_8k_ts=prev_8k_ts,
        prior_created=prior_created,
        filed=filed,
    ) and _within_existing_short_gap(filed=filed, prior_created=prior_created):
        return _result(
            None,
            None,
            "rule_g_fail_closed_same_filing_short_gap_calendar",
            "FAIL_CLOSED",
        )

    if math_parsed_prior is None:
        return _result(None, None, "prior_periodic_projection_fiscal_math_error", "NO_RESOLUTION")

    prior_fy, prior_q = math_parsed_prior
    advanced = _advance_quarter(int(prior_fy), str(prior_q))
    if advanced is None:
        return _result(None, None, "prior_periodic_projection_bad_prior_quarter", "NO_RESOLUTION")

    fy, q = advanced
    source = f"prior_periodic_projection_{prior_q.lower()}_to_{q.lower()}"
    if effective_fye != fye_month:
        source += "_effective_fye_from_prior_10k"
    return _attach_resolution_context(
        _result(fy, q, source, "AUTO_OK"),
        period_of_report=_resolved_period_end(fy, q, effective_fye),
        form_type_periodic=_form_for_quarter(q),
    )


def _resolve_fye_month(ticker: str, raw_fye_month, gaps: list[dict]) -> int | None:
    ticker = ticker.upper()
    if ticker in _FYE_CACHE:
        return _FYE_CACHE[ticker]

    fye_month = None
    try:
        fye_month = get_fye_month(ticker, gaps)
    except Exception as exc:
        gaps.append({
            "type": "fiscal_calendar_lookup_failed",
            "reason": f"get_fye_month failed for {ticker}: {exc}",
        })

    if fye_month is None:
        fye_month = _parse_fye(raw_fye_month)
    else:
        fye_month = _parse_fye(fye_month)

    if fye_month is not None:
        _FYE_CACHE[ticker] = fye_month
    return fye_month


def _gap_for_resolution(resolution: dict) -> dict:
    source = resolution.get("source") or "unknown"
    return {
        "type": source,
        "reason": f"Quarter identity resolver did not authorize writes: {source}",
    }


def _quarter_info_from_context_row(ticker: str, accession_8k: str, row, session) -> dict:
    gaps: list[dict] = []
    filed_8k = _to_str(_record_get(row, "filed_8k"))
    market_session = _record_get(row, "market_session") or "post_market"
    prev_8k_ts = _to_str(_record_get(row, "prev_8k_ts"))
    raw_fye_month = _record_get(row, "fye_month")
    fye_month = _resolve_fye_month(ticker, raw_fye_month, gaps)

    row_context = {
        "accession_8k": accession_8k,
        "ticker": ticker,
        "filed_8k": filed_8k,
        "fye_month": raw_fye_month if raw_fye_month is not None else fye_month,
        "prev_8k_ts": prev_8k_ts,
    }
    prefetched_priors = _record_get(row, "priors", None)
    if prefetched_priors is not None:
        row_context["_prefetched_priors"] = prefetched_priors
    resolution = resolve_quarter_via_prior_periodic(row_context, neo4j_session=session)

    internal_action = resolution.get("safety_action")
    safety_action = "AUTO_OK" if internal_action == "AUTO_OK" else "FAIL_CLOSED"
    fy = resolution.get("fy")
    q = resolution.get("q")
    quarter_label = f"{q}_FY{fy}" if safety_action == "AUTO_OK" and fy and q else None

    if safety_action != "AUTO_OK":
        gaps.append(_gap_for_resolution(resolution))
    if not prev_8k_ts:
        gaps.append({
            "type": "no_prev_8k",
            "reason": f"No previous 8-K 2.02 found for {ticker} before {filed_8k}",
        })

    return {
        "accession_8k": accession_8k,
        "filed_8k": filed_8k,
        "market_session": market_session,
        "period_of_report": resolution.get("period_of_report") if safety_action == "AUTO_OK" else None,
        "prev_8k_ts": prev_8k_ts,
        "quarter_label": quarter_label,
        "form_type_periodic": resolution.get("form_type_periodic") if safety_action == "AUTO_OK" else None,
        "accession_periodic": resolution.get("accession_periodic") if safety_action == "AUTO_OK" else "",
        "fye_month": fye_month,
        "quarter_identity_source": resolution.get("source"),
        "safety_action": safety_action,
        "gaps": gaps if gaps else None,
    }


def _resolve_with_session(ticker: str, accession_8k: str, session) -> dict:
    row = session.run(_QUERY, accession=accession_8k, ticker=ticker).single()
    if not row:
        raise ValueError(f"8-K {accession_8k} not found for {ticker}")
    return _quarter_info_from_context_row(ticker, accession_8k, row, session)


def _cache_context_row(ticker: str, row) -> None:
    data = row.data() if hasattr(row, "data") else dict(row)
    accessions = {
        _clean(data.get("accession_8k")),
        _clean(data.get("report_id")),
        _clean(data.get("accession_no")),
    }
    for accession in accessions:
        if accession:
            _CONTEXT_CACHE[(ticker, accession)] = data


def _preload_ticker_contexts(ticker: str, session) -> None:
    if ticker in _TICKER_CONTEXT_PRELOADED:
        return
    for row in session.run(_TICKER_CONTEXT_QUERY, ticker=ticker):
        _cache_context_row(ticker, row)
    _TICKER_CONTEXT_PRELOADED.add(ticker)


def resolve_quarter_info(ticker: str, accession_8k: str, *, session=None) -> dict:
    """Resolve canonical quarter_info from an 8-K accession.

    Returns:
        {accession_8k, filed_8k, market_session, period_of_report,
         prev_8k_ts, quarter_label, form_type_periodic, accession_periodic,
         fye_month, quarter_identity_source, safety_action, gaps}
    """
    ticker = ticker.upper()

    if session is not None:
        return _resolve_with_session(ticker, accession_8k, session)

    key = (ticker, accession_8k)
    cached = _CONTEXT_CACHE.get(key)
    with _get_neo4j_driver().session() as s:
        if cached is None:
            _preload_ticker_contexts(ticker, s)
            cached = _CONTEXT_CACHE.get(key)
        if cached is not None:
            return _quarter_info_from_context_row(ticker, accession_8k, cached, s)
        return _resolve_with_session(ticker, accession_8k, s)


def _get_neo4j_driver():
    global _NEO4J_DRIVER
    if _NEO4J_DRIVER is not None:
        return _NEO4J_DRIVER

    from dotenv import load_dotenv
    from neo4j import GraphDatabase

    load_dotenv(str(_PROJECT_ROOT / ".env"), override=True)
    uri = os.getenv("NEO4J_URI", "bolt://10.102.222.120:7687")
    user = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    if not password:
        raise RuntimeError("NEO4J_PASSWORD not set")
    _NEO4J_DRIVER = GraphDatabase.driver(uri, auth=(user, password))
    return _NEO4J_DRIVER


if __name__ == "__main__":
    import json

    if len(sys.argv) < 3:
        print("Usage: python quarter_identity.py TICKER ACCESSION")
        sys.exit(1)
    qi = resolve_quarter_info(sys.argv[1], sys.argv[2])
    print(json.dumps(qi, indent=2, default=str))
