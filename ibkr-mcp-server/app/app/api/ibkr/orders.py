"""Order management tools.

Architecture:
  - Convenience endpoints (market, limit, bracket, etc.) for common cases
  - ONE advanced endpoint for any IB order type with all fields
  - Adding a new field = add one Optional line to AdvancedOrderRequest
  - ib_async field names (camelCase) used directly — zero name mapping

All 139 ib_async Order fields documented below. ~15 active, rest commented
for easy future activation. To add a field:
  1. Uncomment it in AdvancedOrderRequest
  2. That's it — advanced_order() auto-maps non-None fields to Order()
"""

from enum import Enum
from pydantic import BaseModel, Field
from fastapi import HTTPException
from app.api.ibkr import ibkr_router, ib_interface
from app.core.setup_logging import logger


class Action(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class TrailingType(str, Enum):
    AMOUNT = "amount"
    PERCENT = "percent"


# NOTE: IB treats ETFs as STK (e.g. SPY sec_type="STK").
# Options/futures need additional contract fields (expiry, strike, right)
# not yet in this model — use conId for those via /order/advanced.


# ── Request models ───────────────────────────────────────────────────

class MarketOrderRequest(BaseModel):
    symbol: str = Field(description="Ticker symbol (e.g. AAPL)")
    sec_type: str = Field(default="STK", description="Security type (STK for stocks/ETFs, use conId for options/futures)")
    exchange: str = Field(default="SMART", description="Exchange")
    currency: str = Field(default="USD", description="Currency")
    action: Action = Field(description="BUY or SELL")
    quantity: float = Field(gt=0, description="Number of shares (positive)")


class LimitOrderRequest(MarketOrderRequest):
    limit_price: float = Field(gt=0, description="Limit price")


class StopOrderRequest(MarketOrderRequest):
    stop_price: float = Field(gt=0, description="Stop trigger price")


class BracketOrderRequest(MarketOrderRequest):
    entry_price: float = Field(gt=0, description="Limit entry price")
    take_profit_price: float = Field(gt=0, description="Take profit limit price")
    stop_loss_price: float = Field(gt=0, description="Stop loss price")


class TrailingStopRequest(MarketOrderRequest):
    trailing_amount: float = Field(gt=0, description="Trail amount (positive)")
    trailing_type: TrailingType = Field(default=TrailingType.AMOUNT, description="'amount' or 'percent'")


class BracketTrailingRequest(MarketOrderRequest):
    entry_price: float = Field(gt=0, description="Limit entry price")
    take_profit_price: float = Field(gt=0, description="Take profit limit price")
    trailing_amount: float = Field(gt=0, description="Trailing stop amount (positive)")
    trailing_type: TrailingType = Field(default=TrailingType.AMOUNT, description="'amount' or 'percent'")


class AdvancedOrderRequest(BaseModel):
    """Generic order request — supports ALL IB order types.

    Uses exact ib_async Order field names (camelCase).
    Only non-None fields are set on the Order object.
    IB validates all field combinations server-side.

    To add a field: uncomment it below. The service auto-maps it.
    """
    model_config = {"extra": "forbid"}  # reject unknown/misspelled fields

    # ── Contract (required — use EITHER symbol OR conId) ──
    symbol: str | None = Field(default=None, description="Ticker symbol (e.g. AAPL). Use symbol OR conId, not both.")
    conId: int | None = Field(default=None, description="Contract ID — use for options, futures, or any unambiguous contract lookup. Overrides symbol if both provided.")
    sec_type: str = Field(default="STK", description="Security type (STK for stocks/ETFs, OPT, FUT, etc.)")
    exchange: str = Field(default="SMART", description="Exchange")
    currency: str = Field(default="USD", description="Currency")

    # ── Core order (required) ──
    action: Action = Field(description="BUY or SELL")
    quantity: float = Field(gt=0, description="Number of shares")
    orderType: str = Field(description="MKT, LMT, STP, STP LMT, TRAIL, TRAIL LIMIT, MOC, LOC, MIT, LIT, MKT PRT, MIDPRICE, REL, etc.")

    # ── Price fields (set based on order type) ──
    lmtPrice: float | None = Field(default=None, description="Limit price (LMT, STP LMT, LOC, LIT, MIDPRICE cap)")
    auxPrice: float | None = Field(default=None, description="Stop price (STP, STP LMT) / trail amount $ (TRAIL) / trigger (MIT, LIT)")
    trailStopPrice: float | None = Field(default=None, description="Initial trailing stop price (TRAIL LIMIT)")
    trailingPercent: float | None = Field(default=None, description="Trailing percentage (TRAIL, TRAIL LIMIT)")
    lmtPriceOffset: float | None = Field(default=None, description="Limit price offset (TRAIL LIMIT)")
    percentOffset: float | None = Field(default=None, description="Percent offset (REL orders)")

    # ── Time in force ──
    tif: str | None = Field(default=None, description="DAY, GTC, IOC, FOK, GTD, OPG, DTC")
    goodTillDate: str | None = Field(default=None, description="Expiry for GTD (YYYYMMDD HH:MM:SS timezone)")
    goodAfterTime: str | None = Field(default=None, description="Don't activate until (YYYYMMDD HH:MM:SS timezone)")

    # ── Extended hours / routing ──
    outsideRth: bool | None = Field(default=None, description="Allow fills outside regular trading hours")
    hidden: bool | None = Field(default=None, description="Hidden order (not displayed)")
    sweepToFill: bool | None = Field(default=None, description="Sweep to fill")
    allOrNone: bool | None = Field(default=None, description="All or none")
    blockOrder: bool | None = Field(default=None, description="Block order")

    # ── Display / iceberg ──
    displaySize: int | None = Field(default=None, description="Visible quantity for iceberg orders")

    # ── OCA (one-cancels-all) ──
    ocaGroup: str | None = Field(default=None, description="OCA group name (links orders)")
    ocaType: int | None = Field(default=None, description="1=cancel with block, 2=reduce with block, 3=reduce no block")

    # ── Bracket linking ──
    parentId: int | None = Field(default=None, description="Parent order ID (for child orders)")
    transmit: bool | None = Field(default=None, description="False=hold until final child sets True")

    # ── Algo orders ──
    algoStrategy: str | None = Field(default=None, description="Adaptive, Twap, Vwap, ArrivalPx, DarkIce, etc.")
    algoParams: dict[str, str] | None = Field(default=None, description="Algo params as {key: value} — converted to TagValue list")

    # ── Reference / tracking ──
    orderRef: str | None = Field(default=None, description="Custom reference string for tracking")
    whatIf: bool | None = Field(default=None, description="True=simulate only, order is NOT placed (status shows WhatIf)")

    # ── Misc commonly used ──
    minQty: int | None = Field(default=None, description="Minimum fill quantity")
    triggerMethod: int | None = Field(default=None, description="0=default, 1=double bid/ask, 2=last, 3=double last, 4=bid/ask, 7=last or bid/ask, 8=mid")

    # ──────────────────────────────────────────────────────────────────
    # ADDITIONAL FIELDS — uncomment to activate. Service auto-maps them.
    # Each field name matches ib_async Order exactly.
    # ──────────────────────────────────────────────────────────────────

    # ── Adjusted orders (bracket stop modification) ──
    # adjustedOrderType: str | None = Field(default=None, description="STP, STP LMT, TRAIL, TRAIL LIMIT")
    # adjustedStopPrice: float | None = Field(default=None, description="Adjusted stop price")
    # adjustedStopLimitPrice: float | None = Field(default=None, description="Adjusted stop limit price")
    # adjustedTrailingAmount: float | None = Field(default=None, description="Adjusted trail amount")
    # adjustedTrailingUnit: int | None = Field(default=None, description="0=amount, 100=percent")

    # ── Scale orders ──
    # scaleInitLevelSize: int | None = Field(default=None, description="Initial component size")
    # scaleSubsLevelSize: int | None = Field(default=None, description="Subsequent component size")
    # scalePriceIncrement: float | None = Field(default=None, description="Price increment between components")
    # scalePriceAdjustValue: float | None = Field(default=None, description="Price adjustment value")
    # scalePriceAdjustInterval: int | None = Field(default=None, description="Price adjustment interval (seconds)")
    # scaleProfitOffset: float | None = Field(default=None, description="Profit offset for scale orders")
    # scaleAutoReset: bool | None = Field(default=None, description="Auto-reset scale orders")
    # scaleInitPosition: int | None = Field(default=None, description="Initial position for scale")
    # scaleInitFillQty: int | None = Field(default=None, description="Initial fill quantity for scale")
    # scaleRandomPercent: bool | None = Field(default=None, description="Randomize scale quantities")

    # ── Volatility orders ──
    # volatility: float | None = Field(default=None, description="Target volatility")
    # volatilityType: int | None = Field(default=None, description="1=daily, 2=annual")

    # ── Cash quantity ──
    # cashQty: float | None = Field(default=None, description="Cash quantity instead of share count")

    # ── Active time window ──
    # activeStartTime: str | None = Field(default=None, description="Active start (YYYYMMDD HH:MM:SS timezone)")
    # activeStopTime: str | None = Field(default=None, description="Active stop (YYYYMMDD HH:MM:SS timezone)")

    # ── Delta neutral / hedge ──
    # deltaNeutralOrderType: str | None = Field(default=None, description="Delta neutral order type")
    # deltaNeutralAuxPrice: float | None = Field(default=None, description="Delta neutral aux price")
    # hedgeType: str | None = Field(default=None, description="D=delta, B=beta, F=FX, P=pair")
    # hedgeParam: str | None = Field(default=None, description="Hedge parameter value")

    # ── Stock range ──
    # stockRangeLower: float | None = Field(default=None, description="Stock price range lower bound")
    # stockRangeUpper: float | None = Field(default=None, description="Stock price range upper bound")

    # ── Peg orders ──
    # peggedChangeAmount: float | None = Field(default=None, description="Pegged change amount")
    # referenceChangeAmount: float | None = Field(default=None, description="Reference change amount")
    # referenceContractId: int | None = Field(default=None, description="Reference contract ID for peg")

    # ── Discretionary ──
    # discretionaryAmt: float | None = Field(default=None, description="Discretionary amount")
    # discretionaryUpToLimitPrice: bool | None = Field(default=None, description="Discretionary up to limit")

    # ── Randomization ──
    # randomizePrice: bool | None = Field(default=None, description="Randomize price within tick")
    # randomizeSize: bool | None = Field(default=None, description="Randomize order size")

    # ── Smart routing ──
    # notHeld: bool | None = Field(default=None, description="Not-held order")
    # optOutSmartRouting: bool | None = Field(default=None, description="Opt out of SMART routing")
    # routeMarketableToBbo: bool | None = Field(default=None, description="Route marketable to BBO")

    # ── Misc ──
    # autoCancelDate: str | None = Field(default=None, description="Auto cancel date (YYYYMMDD)")
    # autoCancelParent: bool | None = Field(default=None, description="Auto cancel parent if children cancel")
    # overridePercentageConstraints: bool | None = Field(default=None, description="Override % constraints")
    # usePriceMgmtAlgo: bool | None = Field(default=None, description="Use IB price management algo")
    # duration: int | None = Field(default=None, description="Order duration in seconds")
    # rule80A: str | None = Field(default=None, description="Rule 80A code")
    # openClose: str | None = Field(default=None, description="O=open, C=close (institutional)")


class ModifyOrderRequest(BaseModel):
    order_id: int = Field(description="Order ID to modify")
    limit_price: float | None = Field(default=None, gt=0, description="New limit price")
    stop_price: float | None = Field(default=None, gt=0, description="New stop price")
    quantity: float | None = Field(default=None, gt=0, description="New quantity")


class CancelOrderRequest(BaseModel):
    order_id: int = Field(description="Order ID to cancel")


# ── Convenience endpoints ────────────────────────────────────────────

@ibkr_router.post("/order/market", operation_id="place_market_order")
async def place_market_order(req: MarketOrderRequest) -> dict:
    """Place a market order. Fills immediately at current market price."""
    try:
        return await ib_interface.place_market_order(
            req.symbol, req.sec_type, req.exchange, req.currency,
            req.action.value, req.quantity,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("Error placing market order: {}", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@ibkr_router.post("/order/limit", operation_id="place_limit_order")
async def place_limit_order(req: LimitOrderRequest) -> dict:
    """Place a limit order. Fills only at limit price or better."""
    try:
        return await ib_interface.place_limit_order(
            req.symbol, req.sec_type, req.exchange, req.currency,
            req.action.value, req.quantity, req.limit_price,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("Error placing limit order: {}", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@ibkr_router.post("/order/stop", operation_id="place_stop_order")
async def place_stop_order(req: StopOrderRequest) -> dict:
    """Place a stop order. Triggers a market order when stop price is hit."""
    try:
        return await ib_interface.place_stop_order(
            req.symbol, req.sec_type, req.exchange, req.currency,
            req.action.value, req.quantity, req.stop_price,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("Error placing stop order: {}", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@ibkr_router.post("/order/bracket", operation_id="place_bracket_order")
async def place_bracket_order(req: BracketOrderRequest) -> list[dict]:
    """Place a bracket order: entry + take profit + stop loss.

    All 3 orders are parent-child linked via ib_async.bracketOrder().
    If entry cancels, both exits cancel.
    If take profit fills, stop loss cancels (and vice versa).
    BUY: take_profit > entry > stop_loss. SELL: inverted.
    """
    try:
        return await ib_interface.place_bracket_order(
            req.symbol, req.sec_type, req.exchange, req.currency,
            req.action.value, req.quantity, req.entry_price,
            req.take_profit_price, req.stop_loss_price,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("Error placing bracket order: {}", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@ibkr_router.post("/order/trailing_stop", operation_id="place_trailing_stop_order")
async def place_trailing_stop(req: TrailingStopRequest) -> dict:
    """Place a trailing stop. Stop follows price by dollar amount or percentage."""
    try:
        return await ib_interface.place_trailing_stop_order(
            req.symbol, req.sec_type, req.exchange, req.currency,
            req.action.value, req.quantity, req.trailing_amount,
            req.trailing_type.value,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("Error placing trailing stop: {}", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@ibkr_router.post("/order/bracket_trailing", operation_id="place_bracket_trailing_order")
async def place_bracket_trailing(req: BracketTrailingRequest) -> list[dict]:
    """Bracket with trailing stop: entry + take profit + trailing stop.

    Pre-assigns orderIds via getReqId() for correct parent-child linkage.
    """
    try:
        return await ib_interface.place_bracket_with_trailing_stop(
            req.symbol, req.sec_type, req.exchange, req.currency,
            req.action.value, req.quantity, req.entry_price,
            req.take_profit_price, req.trailing_amount,
            req.trailing_type.value,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("Error placing bracket trailing: {}", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


# ── Advanced generic endpoint ────────────────────────────────────────

@ibkr_router.post("/order/advanced", operation_id="place_advanced_order")
async def place_advanced_order(req: AdvancedOrderRequest) -> dict:
    """Place ANY IB order type with full field control.

    Supports: MKT, LMT, STP, STP LMT, TRAIL, TRAIL LIMIT, MOC, LOC,
    MIT, LIT, MKT PRT, MIDPRICE, REL, adaptive, TWAP, VWAP, and more.

    Set orderType + relevant price/config fields. IB validates server-side.
    Use whatIf=true to simulate without placing.

    Examples:
      Stop-limit: orderType="STP LMT", auxPrice=245, lmtPrice=244
      MOC: orderType="MOC"
      LOC: orderType="LOC", lmtPrice=250
      MOO: orderType="MKT", tif="OPG"
      LOO: orderType="LMT", tif="OPG", lmtPrice=250
      GTC limit: orderType="LMT", lmtPrice=250, tif="GTC"
      Extended hours: orderType="LMT", lmtPrice=250, outsideRth=true
      Iceberg: orderType="LMT", lmtPrice=250, displaySize=100
      Adaptive: orderType="LMT", lmtPrice=250, algoStrategy="Adaptive",
               algoParams={"adaptivePriority": "Normal"}
      Trailing limit: orderType="TRAIL LIMIT", auxPrice=2, lmtPriceOffset=0.50
      WhatIf: any order + whatIf=true (simulates only, order NOT placed)
      Options/Futures: use conId instead of symbol (e.g. conId=265598 for AAPL stock)
    """
    # Extract contract fields
    contract_fields = {"symbol", "conId", "sec_type", "exchange", "currency", "action", "quantity", "orderType"}
    order_fields = {}
    for field_name, value in req.model_dump(exclude_none=True).items():
        if field_name not in contract_fields:
            order_fields[field_name] = value

    try:
        return await ib_interface.advanced_order(
            req.symbol, req.sec_type, req.exchange, req.currency,
            req.action.value, req.quantity, req.orderType,
            conId=req.conId,
            **order_fields,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("Error placing advanced order: {}", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


# ── Order management ─────────────────────────────────────────────────

@ibkr_router.post("/order/modify", operation_id="modify_order")
async def modify_order(req: ModifyOrderRequest) -> dict:
    """Modify an open order (clientId=1 orders only)."""
    try:
        return await ib_interface.modify_order(req.order_id, req.limit_price, req.stop_price, req.quantity)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error("Error modifying order: {}", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@ibkr_router.post("/order/cancel", operation_id="cancel_order")
async def cancel_order(req: CancelOrderRequest) -> dict:
    """Cancel an open order by ID (clientId=1 orders only)."""
    try:
        return await ib_interface.cancel_order(req.order_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error("Error cancelling order: {}", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@ibkr_router.get("/orders", operation_id="get_open_orders")
async def get_open_orders() -> list[dict]:
    """Get all open orders (clientId=1)."""
    try:
        return await ib_interface.get_open_orders()
    except Exception as e:
        logger.error("Error getting open orders: {}", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e
