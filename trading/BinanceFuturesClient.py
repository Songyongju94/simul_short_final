"""USD-M SDK adapter preserving the TradingBinance response contract.

Only this module knows about SDK response models and the separate algo API.
Conditional orderId values are negative algoIds, so persisted identifiers cannot
collide with ordinary Binance orderIds. The positive algoId is also retained.
"""
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4


class OrderType:
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP = "STOP"
    STOP_MARKET = "STOP_MARKET"
    TAKE_PROFIT = "TAKE_PROFIT"
    TAKE_PROFIT_MARKET = "TAKE_PROFIT_MARKET"
    TRAILING_STOP_MARKET = "TRAILING_STOP_MARKET"


FLOAT_FIELDS = frozenset((
    "price", "qty", "quoteQty", "commission", "realizedPnl", "fundingRate",
    "markPrice", "indexPrice", "lastFundingRate", "interestRate",
    "estimatedSettlePrice", "cumQuote", "executedQty", "origQty", "stopPrice",
    "avgPrice", "activatePrice", "priceRate", "maxNotionalValue",
    "quantity", "triggerPrice", "actualPrice", "actualQty",
))
INT_FIELDS = frozenset((
    "id", "orderId", "algoId", "time", "updateTime", "createTime",
    "fundingTime", "nextFundingTime", "pricePrecision", "quantityPrecision",
    "leverage", "counterPartyId",
))


def _plain(value):
    # SDK oneOf wrappers expose actual_instance; regular models use JSON aliases.
    if hasattr(value, "actual_instance"):
        return _plain(value.actual_instance)
    if hasattr(value, "to_dict"):
        return _plain(value.to_dict())
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    return value


def _record(value):
    if isinstance(value, list):
        return [_record(item) for item in value]
    if not isinstance(value, dict):
        return value
    converted = {}
    for key, item in value.items():
        if item is not None and item != "":
            if key in FLOAT_FIELDS:
                item = float(item)
            elif key in INT_FIELDS:
                item = int(item)
        converted[key] = _record(item)
    if "buyer" in converted:
        converted["isBuyer"] = converted["buyer"]
    if "maker" in converted:
        converted["isMaker"] = converted["maker"]
    return SimpleNamespace(**converted)


def _number(value):
    number = Decimal(str(value))
    if not number.is_finite() or number <= 0:
        raise ValueError("Order price and quantity must be finite and positive")
    # Keep decimal text; the SDK serializes it without a float round trip.
    return format(number, "f")


def _integer_parameter(value, name):
    """Accept integral floats from legacy callers without truncating fractions."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")
    try:
        number = Decimal(str(value))
    except (ValueError, ArithmeticError):
        raise ValueError(f"{name} must be an integer") from None
    minimum = 1 if name == "limit" else 0
    if (not number.is_finite() or number != number.to_integral_value()
            or number < minimum):
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return int(number)


class BinanceFuturesClient:
    CONDITIONAL = frozenset((
        OrderType.STOP, OrderType.STOP_MARKET, OrderType.TAKE_PROFIT,
        OrderType.TAKE_PROFIT_MARKET, OrderType.TRAILING_STOP_MARKET,
    ))
    ALGO_CLIENT_PREFIX = "sdalgo_"

    def __init__(self, api_key=None, secret_key=None, *, rest_api=None, base_path=None):
        if rest_api is not None:
            self.api = rest_api
            return
        from binance_common.configuration import ConfigurationRestAPI
        from binance_sdk_derivatives_trading_usds_futures.derivatives_trading_usds_futures import (
            DerivativesTradingUsdsFutures,
        )
        options = dict(api_key=api_key, api_secret=secret_key, timeout=10000, retries=0)
        if base_path is not None:
            options["base_path"] = base_path
        self.api = DerivativesTradingUsdsFutures(
            config_rest_api=ConfigurationRestAPI(**options)
        ).rest_api

    def _call(self, method, **params):
        for name in ("start_time", "end_time", "limit"):
            if name in params:
                params[name] = _integer_parameter(params[name], name)
        params = {key: value for key, value in params.items() if value is not None}
        return _plain(getattr(self.api, method)(**params).data())

    def get_exchange_information(self):
        return _record(self._call("exchange_information"))

    def get_candlestick_data(self, symbol, interval, startTime=None, endTime=None, limit=None):
        rows = self._call("kline_candlestick_data", symbol=symbol, interval=interval,
                          start_time=startTime, end_time=endTime, limit=limit)
        names = ("openTime", "open", "high", "low", "close", "volume", "closeTime",
                 "quoteAssetVolume", "numTrades", "takerBuyBaseAssetVolume",
                 "takerBuyQuoteAssetVolume", "ignore")
        candles = []
        for row in rows:
            if len(row) != 12:
                raise ValueError("Unexpected Binance kline shape")
            values = [int(value) if index in (0, 6, 8) else float(value)
                      for index, value in enumerate(row)]
            candles.append(SimpleNamespace(**dict(zip(names, values))))
        return candles

    def get_funding_rate(self, symbol, startTime=None, endTime=None, limit=None):
        return _record(self._call("get_funding_rate_history", symbol=symbol,
                                 start_time=startTime, end_time=endTime, limit=limit))

    def get_mark_price(self, symbol):
        data = self._call("mark_price", symbol=symbol)
        return _record(data)

    def change_position_mode(self, dualSidePosition):
        return _record(self._call("change_position_mode",
                                 dual_side_position=str(dualSidePosition).lower()))

    def change_initial_leverage(self, symbol, leverage):
        return _record(self._call("change_initial_leverage", symbol=symbol, leverage=leverage))

    def change_margin_type(self, symbol, marginType):
        return _record(self._call("change_margin_type", symbol=symbol, margin_type=marginType))

    def get_recent_trades_list(self, symbol, limit=None):
        return _record(self._call("recent_trades_list", symbol=symbol, limit=limit))

    def get_account_trades(self, symbol, limit=None):
        rows = self._call("account_trade_list", symbol=symbol, limit=limit)
        for row in rows:
            row.setdefault("counterPartyId", None)
        return _record(rows)

    def post_order(self, symbol, side, ordertype, timeInForce=None, quantity=None,
                   price=None, stopPrice=None, closePosition=False, positionSide=None,
                   callbackRate=None, activationPrice=None, newClientOrderId=None):
        if side not in ("BUY", "SELL"):
            raise ValueError("Invalid order side")
        if positionSide not in ("LONG", "SHORT", "BOTH", None):
            raise ValueError("Invalid position side")
        if ordertype not in self.CONDITIONAL | {OrderType.LIMIT, OrderType.MARKET}:
            raise ValueError("Unsupported order type")
        if closePosition not in (False, None):
            raise ValueError("This adapter submits quantity-based orders, not close-all orders")
        params = dict(symbol=symbol, side=side, type=ordertype,
                      position_side=positionSide, quantity=_number(quantity))
        if ordertype in (OrderType.LIMIT, OrderType.STOP, OrderType.TAKE_PROFIT):
            params.update(price=_number(price), time_in_force=timeInForce or "GTC")
        if ordertype in self.CONDITIONAL:
            params["algo_type"] = "CONDITIONAL"
            params["client_algo_id"] = newClientOrderId or self.ALGO_CLIENT_PREFIX + uuid4().hex[:28]
            if ordertype == OrderType.TRAILING_STOP_MARKET:
                rate = Decimal(_number(callbackRate))
                if not Decimal("0.1") <= rate <= Decimal("10"):
                    raise ValueError("callbackRate must be between 0.1 and 10")
                params["callback_rate"] = format(rate, "f")
                if activationPrice is not None:
                    params["activate_price"] = _number(activationPrice)
            else:
                params["trigger_price"] = _number(stopPrice)
            return self._algo_record(self._call("new_algo_order", **params))
        params["new_client_order_id"] = newClientOrderId
        return _record(self._call("new_order", **params))

    def _algo_record(self, data):
        data = dict(data)
        algo_id = int(data["algoId"])
        if algo_id <= 0:
            raise ValueError("Invalid algo order identifier")
        data.update(
            orderId=-algo_id,
            clientOrderId=data.get("clientAlgoId", ""),
            type=data.get("orderType", data.get("type")),
            origType=data.get("orderType", data.get("type")),
            origQty=data.get("quantity"),
            stopPrice=data.get("triggerPrice"),
            status=data.get("algoStatus", "NEW"),
            executedQty=data.get("actualQty", 0),
            avgPrice=data.get("actualPrice", 0),
            cumQuote=0,
            isAlgo=True,
        )
        # FINISHED means trigger processing finished, not that the child order filled.
        if data["status"] == "CANCELLED":
            data["status"] = "CANCELED"
        for key, default in (("price", 0), ("reduceOnly", False), ("closePosition", False),
                             ("updateTime", data.get("createTime", 0)),
                             ("activatePrice", None), ("priceRate", None)):
            data.setdefault(key, default)
        return _record(data)

    def get_open_orders(self, symbol=None):
        regular = self._call("current_all_open_orders", symbol=symbol)
        conditional = self._call("current_all_algo_open_orders", symbol=symbol)
        return _record(regular) + [self._algo_record(row) for row in conditional]

    def get_order(self, symbol, orderId=None, origClientOrderId=None):
        if orderId is None and not origClientOrderId:
            raise ValueError("An order identifier is required")
        algo_id = -int(orderId) if orderId is not None and int(orderId) < 0 else None
        is_algo = algo_id is not None or (
            orderId is None and str(origClientOrderId).startswith(self.ALGO_CLIENT_PREFIX)
        )
        if not is_algo:
            return _record(self._call("query_order", symbol=symbol, order_id=orderId,
                                      orig_client_order_id=origClientOrderId or None))
        data = self._call("query_algo_order", algo_id=algo_id,
                          client_algo_id=origClientOrderId or None)
        if data.get("symbol") != symbol:
            raise ValueError("Algo order symbol does not match requested symbol")
        result = self._algo_record(data)
        actual_id = data.get("actualOrderId")
        if actual_id and int(actual_id) > 0:
            child = self._call("query_order", symbol=symbol, order_id=int(actual_id))
            # Preserve the stable parent identifier while reporting real fill state.
            for key in ("status", "executedQty", "avgPrice", "cumQuote", "updateTime"):
                if key in child:
                    setattr(result, key, getattr(_record({key: child[key]}), key))
        return result

    def cancel_all_orders(self, symbol):
        if not symbol:
            raise ValueError("A symbol is required for cancellation")
        results, failures = {}, []
        # Always attempt both families; never claim success on partial cancellation.
        for method in ("cancel_all_open_orders", "cancel_all_algo_open_orders"):
            try:
                results[method] = self._call(method, symbol=symbol)
            except Exception as error:
                failures.append((method, error))
        if failures:
            names = ", ".join(name for name, _ in failures)
            raise RuntimeError("Cancellation incomplete: " + names) from failures[0][1]
        return SimpleNamespace(code=200, msg="All regular and conditional orders canceled",
                               results=results)
