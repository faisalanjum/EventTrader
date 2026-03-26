"""Order placement and management operations.

Uses a DEDICATED IB() connection (separate from market data) with a fixed
clientId=1 to ensure order tracking survives reconnects.

Architecture:
  - OrderClient has its own IB() instance (not shared with market data)
  - All order fields map 1:1 to ib_async Order field names (camelCase)
  - Adding a new order field = add one line to AdvancedOrderRequest in orders_models.py
  - IB validates all field combinations server-side
"""

import asyncio

from ib_async import (
    IB,
    LimitOrder,
    MarketOrder,
    Order,
    StopOrder,
    TagValue,
    Trade,
)

from app.core.config import get_config
from app.core.setup_logging import logger

ORDER_CLIENT_ID = 1

# ib_async sentinel values — fields with these are "unset"
_UNSET_DOUBLE = 1.7976931348623157e+308
_UNSET_INT = 2147483647


class OrderClient:
    """Order placement and management with dedicated connection."""

    def __init__(self) -> None:
        self._order_ib = IB()
        self._config = get_config()
        self._contract_cache: dict[tuple[str, str, str, str], object] = {}

    async def _connect_orders(self) -> None:
        if self._order_ib.isConnected():
            return
        try:
            await self._order_ib.connectAsync(
                host=self._config.ib_gateway_host,
                port=self._config.ib_gateway_port,
                clientId=ORDER_CLIENT_ID,
                timeout=20, readonly=False,
            )
            self._order_ib.RequestTimeout = 20
            logger.info("Order connection established (clientId={})", ORDER_CLIENT_ID)
        except Exception as e:
            logger.error("Error connecting order client: {}", e)
            raise

    async def _qualify(self, symbol: str, sec_type: str, exchange: str, currency: str):
        from ib_async.contract import Contract
        key = (symbol.upper(), sec_type.upper(), exchange.upper(), currency.upper())
        if key not in self._contract_cache:
            contract = Contract(symbol=symbol, secType=sec_type, exchange=exchange, currency=currency)
            [qualified] = await self._order_ib.qualifyContractsAsync(contract)
            self._contract_cache[key] = qualified
        return self._contract_cache[key]

    # ── Convenience methods (call advanced_order internally) ─────────

    async def place_market_order(self, symbol, sec_type, exchange, currency, action, quantity):
        return await self.advanced_order(symbol, sec_type, exchange, currency, action, quantity, "MKT")

    async def place_limit_order(self, symbol, sec_type, exchange, currency, action, quantity, limit_price):
        return await self.advanced_order(symbol, sec_type, exchange, currency, action, quantity, "LMT", lmtPrice=limit_price)

    async def place_stop_order(self, symbol, sec_type, exchange, currency, action, quantity, stop_price):
        return await self.advanced_order(symbol, sec_type, exchange, currency, action, quantity, "STP", auxPrice=stop_price)

    async def place_trailing_stop_order(self, symbol, sec_type, exchange, currency, action, quantity, trailing_amount, trailing_type="amount"):
        kwargs = {}
        if trailing_type == "percent":
            kwargs["trailingPercent"] = trailing_amount
        else:
            kwargs["auxPrice"] = trailing_amount
        return await self.advanced_order(symbol, sec_type, exchange, currency, action, quantity, "TRAIL", **kwargs)

    # ── Bracket orders ───────────────────────────────────────────────

    async def place_bracket_order(self, symbol, sec_type, exchange, currency, action, quantity,
                                   entry_price, take_profit_price, stop_loss_price):
        _validate_bracket_prices(action, entry_price, take_profit_price, stop_loss_price)
        await self._connect_orders()
        contract = await self._qualify(symbol, sec_type, exchange, currency)
        bracket = self._order_ib.bracketOrder(action, quantity, entry_price, take_profit_price, stop_loss_price)
        trades = []
        for order in bracket:
            trades.append(self._order_ib.placeOrder(contract, order))
        await self._wait_for_status(trades[0])  # wait for parent
        return [_trade_to_dict(t) for t in trades]

    async def place_bracket_with_trailing_stop(self, symbol, sec_type, exchange, currency, action, quantity,
                                                entry_price, take_profit_price, trailing_amount, trailing_type="amount"):
        if action.upper() == "BUY" and take_profit_price <= entry_price:
            raise ValueError("BUY bracket: take_profit must be > entry_price")
        if action.upper() == "SELL" and take_profit_price >= entry_price:
            raise ValueError("SELL bracket: take_profit must be < entry_price")

        await self._connect_orders()
        contract = await self._qualify(symbol, sec_type, exchange, currency)
        tp_action = "SELL" if action.upper() == "BUY" else "BUY"

        parent_id = self._order_ib.client.getReqId()
        tp_id = self._order_ib.client.getReqId()
        trail_id = self._order_ib.client.getReqId()

        parent = LimitOrder(action, quantity, entry_price)
        parent.orderId = parent_id
        parent.transmit = False

        take_profit = LimitOrder(tp_action, quantity, take_profit_price)
        take_profit.orderId = tp_id
        take_profit.parentId = parent_id
        take_profit.transmit = False

        trail_stop = Order(action=tp_action, totalQuantity=quantity, orderType="TRAIL")
        trail_stop.orderId = trail_id
        trail_stop.parentId = parent_id
        if trailing_type == "percent":
            trail_stop.trailingPercent = trailing_amount
        else:
            trail_stop.auxPrice = trailing_amount
        trail_stop.transmit = True

        trades = []
        for order in [parent, take_profit, trail_stop]:
            trades.append(self._order_ib.placeOrder(contract, order))
        await self._wait_for_status(trades[0])  # wait for parent
        return [_trade_to_dict(t) for t in trades]

    # ── Generic advanced order (handles ALL order types) ─────────────

    async def advanced_order(self, symbol: str | None, sec_type: str, exchange: str,
                              currency: str, action: str, quantity: float,
                              order_type: str, conId: int | None = None,
                              **order_fields) -> dict:
        """Place any order type by setting fields directly on ib_async Order.

        Args:
            symbol: Ticker symbol (for stocks/ETFs). Use symbol OR conId.
            conId: Contract ID (for options, futures, or unambiguous lookup).
            sec_type, exchange, currency: Contract identification.
            action: BUY or SELL.
            quantity: Number of shares/contracts.
            order_type: IB order type string (MKT, LMT, STP, STP LMT, TRAIL,
                        TRAIL LIMIT, MOC, LOC, MIT, LIT, MKT PRT, MIDPRICE, etc.)
            **order_fields: Any ib_async Order field name → value.

        Returns:
            dict with order status, fill info, and IDs.
        """
        if not symbol and not conId:
            raise ValueError("Either symbol or conId must be provided")

        await self._connect_orders()

        if conId:
            from ib_async.contract import Contract
            contract = Contract(conId=conId)
            [contract] = await self._order_ib.qualifyContractsAsync(contract)
        else:
            contract = await self._qualify(symbol, sec_type, exchange, currency)

        order = Order(
            action=action.upper(),
            totalQuantity=quantity,
            orderType=order_type,
        )

        # Set any additional fields directly on the Order object
        for field_name, value in order_fields.items():
            if value is not None and hasattr(order, field_name):
                # Special handling for algoParams: dict → list[TagValue]
                if field_name == "algoParams" and isinstance(value, dict):
                    value = [TagValue(k, v) for k, v in value.items()]
                setattr(order, field_name, value)
            elif value is not None and not hasattr(order, field_name):
                raise ValueError(f"Unknown Order field '{field_name}' — check ib_async Order docs")

        trade = self._order_ib.placeOrder(contract, order)
        await self._wait_for_status(trade)
        return _trade_to_dict(trade)

    # ── Order management ─────────────────────────────────────────────

    async def modify_order(self, order_id: int, limit_price=None, stop_price=None, quantity=None):
        if limit_price is None and stop_price is None and quantity is None:
            raise ValueError("At least one of limit_price, stop_price, or quantity must be provided")
        await self._connect_orders()
        target = self._find_trade(order_id)
        otype = target.order.orderType

        # Validate field applicability per order type
        if limit_price is not None:
            if otype not in ("LMT", "STP LMT", "LIT", "LOC", "MIDPRICE", "TRAIL LIMIT"):
                raise ValueError(f"limit_price not applicable to {otype} orders")
            target.order.lmtPrice = limit_price
        if stop_price is not None:
            if otype not in ("STP", "STP LMT", "MIT", "LIT", "TRAIL"):
                raise ValueError(f"stop_price not applicable to {otype} orders")
            target.order.auxPrice = stop_price
        if quantity is not None:
            target.order.totalQuantity = quantity

        self._order_ib.placeOrder(target.contract, target.order)
        trade = target
        await self._wait_for_status(trade)
        return _trade_to_dict(trade)

    async def cancel_order(self, order_id: int):
        await self._connect_orders()
        target = self._find_trade(order_id)
        self._order_ib.cancelOrder(target.order)
        await self._wait_for_status(target)
        return _trade_to_dict(target)

    async def get_open_orders(self):
        await self._connect_orders()
        return [_trade_to_dict(t) for t in self._order_ib.openTrades()]

    async def _wait_for_status(self, trade: Trade, timeout: float = 5.0) -> None:
        """Wait for trade status to change from initial state, or timeout.

        Uses await asyncio.sleep() to yield to the event loop, which lets
        ib_async process incoming TWS messages and update trade status.
        No IB.sleep() — that calls run_until_complete() which crashes
        inside an already-running async context.
        """
        deadline = asyncio.get_event_loop().time() + timeout
        initial = trade.orderStatus.status
        while asyncio.get_event_loop().time() < deadline:
            await asyncio.sleep(0.1)  # yield — ib_async processes messages
            current = trade.orderStatus.status
            if current != initial:
                return
            if current in ("Filled", "Cancelled", "Inactive", "ApiCancelled"):
                return

    def _find_trade(self, order_id: int) -> Trade:
        for trade in self._order_ib.openTrades():
            if trade.order.orderId == order_id:
                return trade
        raise ValueError(f"Order {order_id} not found (clientId={ORDER_CLIENT_ID})")


# ── Validation ───────────────────────────────────────────────────────

def _validate_bracket_prices(action: str, entry: float, tp: float, sl: float):
    if action.upper() == "BUY":
        if not (tp > entry > sl):
            raise ValueError(f"BUY bracket: need take_profit ({tp}) > entry ({entry}) > stop_loss ({sl})")
    else:
        if not (sl > entry > tp):
            raise ValueError(f"SELL bracket: need stop_loss ({sl}) > entry ({entry}) > take_profit ({tp})")


def _trade_to_dict(trade: Trade) -> dict:
    return {
        "orderId": trade.order.orderId,
        "permId": trade.order.permId,
        "clientId": trade.order.clientId,
        "symbol": trade.contract.symbol if trade.contract else None,
        "conId": trade.contract.conId if trade.contract else None,
        "action": trade.order.action,
        "orderType": trade.order.orderType,
        "quantity": float(trade.order.totalQuantity),
        "limitPrice": _clean(trade.order.lmtPrice),
        "stopPrice": _clean(trade.order.auxPrice),
        "trailingPercent": _clean(trade.order.trailingPercent),
        "tif": trade.order.tif or None,
        "status": trade.orderStatus.status,
        "filled": float(trade.orderStatus.filled),
        "remaining": float(trade.orderStatus.remaining),
        "avgFillPrice": float(trade.orderStatus.avgFillPrice),
        "parentId": trade.order.parentId,
        "ocaGroup": trade.order.ocaGroup or None,
        "orderRef": trade.order.orderRef or None,
    }


def _clean(val: float) -> float | None:
    """Convert ib_async UNSET sentinel to None."""
    if val is None or val >= _UNSET_DOUBLE * 0.9:
        return None
    return val
