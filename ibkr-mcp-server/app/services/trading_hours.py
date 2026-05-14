"""Per-contract trading-hours detection via IBKR's contract.tradingHours.

This module replaces hardcoded US-equity hour windows with IBKR's
canonical per-contract `tradingHours` string + `timeZoneId`, fetched via
reqContractDetails and cached for 6 hours.

Works for every secType IBKR supports (STK, OPT, FUT, CASH, IND, BOND)
because all contracts expose the same `tradingHours` field — the exact
string IBKR uses internally to route live vs delayed quotes.

Failure modes ALL fall back to returning False, which steers callers to
the historical-bar path (the safe default that existed before Phase 2).
"""

import asyncio
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.setup_logging import logger


_CACHE: dict[int, tuple[str, str, float]] = {}
_CACHE_TTL_SECONDS = 6 * 3600
_REQ_DETAILS_TIMEOUT_SECONDS = 5.0


def _is_in_window(trading_hours: str, time_zone_id: str, now: datetime | None = None) -> bool:
    """Return True iff `now` falls within ANY non-CLOSED session in the IB tradingHours spec.

    Format (IB-documented, empirically verified 2026-05-14 across STK/CASH/FUT/IND):
        "YYYYMMDD:HHMM-YYYYMMDD:HHMM;..." with semicolon-separated segments.
        Segments may span midnight (start_date != end_date), as in forex/futures.
        Closed days appear as "YYYYMMDD:CLOSED".

    Returns False on any parsing failure (fail-safe — fall back to historical).
    """
    if not trading_hours:
        return False
    try:
        tz = ZoneInfo(time_zone_id)
    except Exception:
        return False
    if now is None:
        now = datetime.now(tz)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=tz)
    else:
        now = now.astimezone(tz)
    for segment in trading_hours.split(";"):
        segment = segment.strip()
        if not segment or "CLOSED" in segment.upper():
            continue
        try:
            start_str, end_str = segment.split("-")
            start = datetime.strptime(start_str, "%Y%m%d:%H%M").replace(tzinfo=tz)
            end = datetime.strptime(end_str, "%Y%m%d:%H%M").replace(tzinfo=tz)
        except (ValueError, AttributeError):
            continue
        if start <= now < end:
            return True
    return False


async def is_contract_open(ib, contract) -> bool:
    """Return True iff `contract` is currently in its trading hours.

    Looks up tradingHours via reqContractDetails on first call per contract,
    caches the result for 6 hours. Any failure (network, empty details,
    parse error) returns False so callers fall back to historical bars.

    The caller is expected to have already qualified the contract (conId set).
    """
    conid = getattr(contract, "conId", 0) or 0
    if conid:
        cached = _CACHE.get(conid)
        if cached and (time.time() - cached[2]) < _CACHE_TTL_SECONDS:
            return _is_in_window(cached[0], cached[1])
    try:
        details = await asyncio.wait_for(
            ib.reqContractDetailsAsync(contract), timeout=_REQ_DETAILS_TIMEOUT_SECONDS,
        )
    except (asyncio.TimeoutError, Exception) as e:
        logger.warning("is_contract_open: details lookup failed for conId={}: {}", conid, e)
        return False
    if not details:
        logger.warning("is_contract_open: no details returned for conId={}", conid)
        return False
    d = details[0]
    th = d.tradingHours or ""
    tz = d.timeZoneId or ""
    if conid:
        _CACHE[conid] = (th, tz, time.time())
    return _is_in_window(th, tz)
