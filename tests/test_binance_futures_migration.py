"""Offline regression tests: no credentials, service startup or network."""
import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "binance_futures_adapter_under_test", ROOT / "trading" / "BinanceFuturesClient.py"
)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
Client = adapter.BinanceFuturesClient


class Model:
    """SDK's public JSON-alias conversion contract."""
    def __init__(self, data):
        self.payload = data

    def to_dict(self):
        return self.payload


class FakeApi:
    def __init__(self):
        self.calls = []
        self.responses = {}
        self.errors = {}

    def __getattr__(self, name):
        def call(**params):
            self.calls.append((name, params))
            if name in self.errors:
                raise self.errors[name]
            return SimpleNamespace(data=lambda: self.responses.get(name, {}))
        return call


def trading_class():
    # Execute only this class and its pure precision helpers. Do not import
    # application dependencies (Config, Log, numpy, service or database modules).
    tree = ast.parse((ROOT / "trading" / "TradingBinance.py").read_text(encoding="utf-8-sig"))
    tree.body = [node for node in tree.body
                 if isinstance(node, (ast.ClassDef, ast.FunctionDef))]
    namespace = {"TradingCenter": object, "OrderType": adapter.OrderType,
                 "time": SimpleNamespace(sleep=lambda _: None),
                 "traceback": SimpleNamespace(format_exc=lambda: "test"),
                 "Currency": lambda values: SimpleNamespace(**values)}
    exec(compile(tree, "TradingBinance.py", "exec"), namespace)
    return namespace["TradingBinance"]


TradingBinance = trading_class()


class MigrationTests(unittest.TestCase):
    def test_candle_timeout_retries_then_succeeds_with_identical_request(self):
        api = Mock()
        api.kline_candlestick_data.side_effect = [
            adapter.ClientError('Timeout waiting for response from backend server.'),
            adapter.Timeout('read timed out'),
            adapter.ClientError('backend timeout', -1007),
            SimpleNamespace(data=lambda: [])]
        with patch.object(adapter.time, 'sleep') as sleep, patch.object(adapter, 'logger') as log:
            self.assertEqual(Client(rest_api=api).get_candlestick_data('TEST', '1m', 0, 59999, 1), [])
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [1, 2, 4])
        self.assertEqual(log.warning.call_count, 3)
        calls = api.kline_candlestick_data.call_args_list
        self.assertEqual(len(calls), 4)
        self.assertTrue(all(c == calls[0] for c in calls))

    def test_candle_timeout_exhaustion_preserves_exception(self):
        api = Mock()
        error = adapter.ClientError('Timeout waiting for response from backend server.')
        api.kline_candlestick_data.side_effect = error
        with patch.object(adapter.time, 'sleep') as sleep, patch.object(adapter, 'logger') as log:
            with self.assertRaises(adapter.ClientError) as caught:
                Client(rest_api=api).get_candlestick_data('TEST', '1m')
        self.assertIs(caught.exception, error)
        self.assertEqual(api.kline_candlestick_data.call_count, 4)
        self.assertEqual(sleep.call_count, 3)
        log.error.assert_called_once()

    def test_non_timeout_and_order_errors_are_not_retried(self):
        from binance_common.errors import BadRequestError
        for error in (BadRequestError('Invalid symbol.', -1121),
                      adapter.ClientError('Invalid request'), ValueError('bad response')):
            api = Mock()
            api.kline_candlestick_data.side_effect = error
            with patch.object(adapter.time, 'sleep') as sleep:
                with self.assertRaises(type(error)):
                    Client(rest_api=api).get_candlestick_data('TEST', '1m')
                sleep.assert_not_called()
            self.assertEqual(api.kline_candlestick_data.call_count, 1)
        api = Mock()
        api.new_order.side_effect = adapter.ClientError('Timeout waiting for response from backend server.')
        with patch.object(adapter.time, 'sleep') as sleep:
            with self.assertRaises(adapter.ClientError):
                Client(rest_api=api)._call('new_order', symbol='TEST')
            sleep.assert_not_called()
        api.new_order.assert_called_once()

    def setUp(self):
        self.api = FakeApi()
        self.client = Client(rest_api=self.api)
        self.center = TradingBinance.__new__(TradingBinance)
        self.center._TradingBinance__request_client = self.client
        self.center._TradingBinance__log = SimpleNamespace(d=lambda *args: None)
        self.currency = SimpleNamespace(symbol="ETHUSDT", pricePrecision=2, quantityPrecision=3)

    def algo(self, **extra):
        result = dict(algoId=42, clientAlgoId="sdalgo_fixture", symbol="ETHUSDT",
                      orderType="TAKE_PROFIT", quantity="0.125", triggerPrice="1900",
                      algoStatus="NEW", price="1899", positionSide="SHORT", side="BUY")
        result.update(extra)
        return Model(result)

    def test_candles_preserve_fields_numbers_and_all_intervals(self):
        row = [1700000000000, "10", "12", "9", "11", "2", 1700000059999,
               "22", 3, "1", "11", "0"]
        self.api.responses["kline_candlestick_data"] = [row]
        methods = [("fetch1MinCandle", "1m"), ("fetch3MinCandle", "3m"),
                   ("fetch5MinCandle", "5m"), ("fetch15MinCandle", "15m"),
                   ("fetch30MinCandle", "30m"), ("fetch60MinCandle", "1h"),
                   ("fetch4HourCandle", "4h")]
        for method, interval in methods:
            with self.subTest(interval=interval):
                candle = getattr(self.center, method)("ETHUSDT", row[0], 5)[0]
                self.assertEqual(candle.openTime, row[0])
                self.assertEqual(candle.close, 11.0)
                self.assertEqual(candle.numTrades, 3)
                self.assertEqual(candle.takerBuyQuoteAssetVolume, 11.0)
                self.assertEqual(self.api.calls[-1][1],
                                 dict(symbol="ETHUSDT", interval=interval,
                                      start_time=row[0], limit=5))
        self.center.getCandlestickData("ETHUSDT", 1000, 1, row[0])
        self.assertEqual(self.api.calls[-1][1]["interval"], "1w")

    def test_malformed_candle_is_not_silently_accepted(self):
        self.api.responses["kline_candlestick_data"] = [[1, 2]]
        with self.assertRaises(ValueError):
            self.client.get_candlestick_data("ETHUSDT", "1m")

    def test_funding_numeric_contract_and_time_arguments(self):
        self.api.responses["get_funding_rate_history"] = [
            Model(dict(symbol="ETHUSDT", fundingRate="-0.0001", fundingTime=1700000000000))]
        result = self.center.getFundingRate("ETHUSDT", 10, 20)
        self.assertLess(result[0].fundingRate, 0)
        self.assertIsInstance(result[0].fundingTime, int)
        self.assertEqual(self.api.calls[-1], ("get_funding_rate_history",
                                            dict(symbol="ETHUSDT", start_time=10, end_time=20)))

    def test_mark_price_remains_single_object_and_unwraps_oneof(self):
        self.api.responses["mark_price"] = SimpleNamespace(
            actual_instance=Model(dict(symbol="ETHUSDT", markPrice="2000.5",
                                       lastFundingRate="0.0001", nextFundingTime=100)))
        self.assertEqual(self.center.getMarkPrice("ETHUSDT").markPrice, 2000.5)

    def test_exchange_precision_legacy_rules_are_preserved(self):
        self.api.responses["exchange_information"] = Model(dict(symbols=[
            dict(symbol="ETHUSDT", pricePrecision=5, quantityPrecision=3)]))
        currency = self.center.fetchCurrency()[0]
        self.assertEqual(currency.pricePrecision, 2)
        self.assertEqual(currency.quantityPrecision, 5)

    def test_mode_leverage_margin_and_trades(self):
        self.api.responses["change_position_mode"] = Model(dict(code=200, msg="success"))
        self.center.changePositionMode()
        self.assertEqual(self.api.calls[-1], ("change_position_mode", dict(dual_side_position="true")))
        self.center.change_initial_leverage("ETHUSDT", 3)
        self.assertEqual(self.api.calls[-1][1], dict(symbol="ETHUSDT", leverage=3))
        self.center.changeMarginType("ETHUSDT")
        self.assertEqual(self.api.calls[-1][1], dict(symbol="ETHUSDT", margin_type="CROSSED"))
        self.api.responses["recent_trades_list"] = [Model(dict(id=1, price="3", qty="2"))]
        self.assertEqual(self.center.getRecentTradesList("ETHUSDT", 4)[0].qty, 2.0)
        self.api.responses["account_trade_list"] = [
            Model(dict(buyer=False, maker=True, orderId=10, realizedPnl="-1.2"))]
        trade = self.center.getAccountTrades("ETHUSDT", 4)[0]
        self.assertFalse(trade.isBuyer)
        self.assertTrue(trade.isMaker)
        self.assertEqual(trade.realizedPnl, -1.2)
        self.assertIsNone(trade.counterPartyId)

    def test_open_long_and_short_orders_keep_position_side(self):
        self.api.responses["new_order"] = Model(dict(orderId=10, origQty="0.125"))
        for side, position in (("BUY", "LONG"), ("SELL", "SHORT")):
            with self.subTest(side=side), patch("builtins.print"):
                result = self.center.postOrder(["open", self.currency, side, 2000.5, 0.1254, 0], "LIMIT")
                params = self.api.calls[-1][1]
                self.assertEqual(params["side"], side)
                self.assertEqual(params["position_side"], position)
                self.assertEqual(params["quantity"], "0.125")
                self.assertEqual(params["price"], "2000.5")
                self.assertEqual(params["type"], "LIMIT")
                self.assertNotIn("reduce_only", params)
                self.assertNotIn("close_position", params)
                self.assertEqual(result.orderId, 10)

    def test_close_limit_reverses_side_but_keeps_position(self):
        for side, closing, position in (("BUY", "SELL", "LONG"), ("SELL", "BUY", "SHORT")):
            self.center.postOrder(["close", self.currency, side, 2000, 0.125, 1900], "LIMIT")
            name, params = self.api.calls[-1]
            self.assertEqual(name, "new_order")
            self.assertEqual((params["side"], params["position_side"]), (closing, position))
            self.assertNotIn("trigger_price", params)

    def test_default_close_order_uses_algo_api(self):
        self.api.responses["new_algo_order"] = self.algo()
        result = self.center.postOrder(["close", self.currency, "SELL", 1899, 0.125, 1900], None)
        name, params = self.api.calls[-1]
        self.assertEqual(name, "new_algo_order")
        self.assertEqual(params["type"], "TAKE_PROFIT")
        self.assertEqual(params["algo_type"], "CONDITIONAL")
        self.assertEqual(params["trigger_price"], "1900")
        self.assertEqual(params["position_side"], "SHORT")
        self.assertEqual(result.orderId, -42)
        self.assertEqual(result.algoId, 42)
        self.assertEqual(result.stopPrice, 1900.0)

    def test_market_close_omits_price_trigger_and_time_in_force(self):
        self.center.postOrder(["close", self.currency, "BUY", 2000, 0.125, 1900], "MARKET")
        self.assertEqual(self.api.calls[-1],
                         ("new_order", dict(symbol="ETHUSDT", side="SELL", type="MARKET",
                                            position_side="LONG", quantity="0.125")))

    def test_stop_market_and_take_profit_market(self):
        self.api.responses["new_algo_order"] = self.algo()
        for kind in ("STOP_MARKET", "TAKE_PROFIT_MARKET"):
            self.client.post_order("ETHUSDT", "BUY", kind, quantity="0.125",
                                   stopPrice="1900", price="1899", timeInForce="GTC",
                                   positionSide="SHORT")
            params = self.api.calls[-1][1]
            self.assertEqual(params["type"], kind)
            self.assertNotIn("price", params)
            self.assertNotIn("time_in_force", params)

    def test_invalid_quantity_rejected_before_request(self):
        for qty in ("0", "-1", "NaN", "Infinity"):
            with self.subTest(qty=qty), self.assertRaises(ValueError):
                self.client.post_order("ETHUSDT", "BUY", "LIMIT", quantity=qty, price="2")
        self.assertEqual(self.api.calls, [])

    def test_request_preserves_decimal_text(self):
        self.client.post_order("ETHUSDT", "BUY", "LIMIT", quantity="0.00000001",
                               price="123456789.12345678")
        self.assertEqual(self.api.calls[-1][1]["price"], "123456789.12345678")

    def test_query_normal_and_algo_ids_do_not_collide(self):
        self.api.responses["query_order"] = Model(dict(orderId=42, status="NEW"))
        self.api.responses["query_algo_order"] = self.algo()
        self.assertEqual(self.center.getOrder("ETHUSDT", 42, None).orderId, 42)
        self.assertEqual(self.api.calls[-1][0], "query_order")
        self.assertEqual(self.center.getOrder("ETHUSDT", -42, None).orderId, -42)
        self.assertEqual(self.api.calls[-1], ("query_algo_order", dict(algo_id=42)))

    def test_algo_id_works_after_client_recreation_and_by_client_id(self):
        self.api.responses["query_algo_order"] = self.algo()
        client = Client(rest_api=self.api)
        self.assertEqual(client.get_order("ETHUSDT", -42).orderId, -42)
        client.get_order("ETHUSDT", origClientOrderId="sdalgo_fixture")
        self.assertEqual(self.api.calls[-1][1], dict(client_algo_id="sdalgo_fixture"))

    def test_triggered_algo_reports_child_fill_state_not_finished_as_filled(self):
        self.api.responses["query_algo_order"] = self.algo(algoStatus="FINISHED", actualOrderId="123")
        self.api.responses["query_order"] = Model(dict(
            orderId=123, status="PARTIALLY_FILLED", executedQty="0.1", avgPrice="1899"))
        result = self.client.get_order("ETHUSDT", -42)
        self.assertEqual(result.orderId, -42)
        self.assertEqual(result.status, "PARTIALLY_FILLED")
        self.assertEqual(result.executedQty, 0.1)

    def test_algo_symbol_mismatch_is_rejected(self):
        self.api.responses["query_algo_order"] = self.algo(symbol="BTCUSDT")
        with self.assertRaises(ValueError):
            self.client.get_order("ETHUSDT", -42)

    def test_open_orders_include_both_families(self):
        self.api.responses["current_all_open_orders"] = [Model(dict(orderId=42))]
        self.api.responses["current_all_algo_open_orders"] = [self.algo()]
        self.assertEqual([o.orderId for o in self.center.getOpenOrders("ETHUSDT")], [42, -42])

    def test_cancel_all_calls_both_endpoints(self):
        self.assertEqual(self.center.cancelAllOrders("ETHUSDT").code, 200)
        self.assertEqual(self.api.calls, [
            ("cancel_all_open_orders", dict(symbol="ETHUSDT")),
            ("cancel_all_algo_open_orders", dict(symbol="ETHUSDT"))])

    def test_partial_cancellation_attempts_both_and_raises(self):
        for endpoint in ("cancel_all_open_orders", "cancel_all_algo_open_orders"):
            with self.subTest(endpoint=endpoint):
                self.api.calls.clear()
                self.api.errors = {endpoint: RuntimeError("fixture error")}
                with self.assertRaisesRegex(RuntimeError, "Cancellation incomplete"):
                    self.client.cancel_all_orders("ETHUSDT")
                self.assertEqual(len(self.api.calls), 2)

    def test_order_timeout_is_not_retried(self):
        self.api.errors["new_order"] = TimeoutError("fixture timeout")
        with self.assertRaises(TimeoutError):
            self.client.post_order("ETHUSDT", "BUY", "LIMIT", quantity="1", price="2")
        self.assertEqual(len(self.api.calls), 1)

    def test_read_failure_returns_none_without_unbound_local_error(self):
        self.api.errors["recent_trades_list"] = RuntimeError("fixture error")
        self.api.errors["change_position_mode"] = RuntimeError("fixture error")
        self.assertIsNone(self.center.getRecentTradesList("ETHUSDT", 1))
        self.assertIsNone(self.center.changePositionMode())




    def test_integral_float_request_parameters_become_integers(self):
        self.api.responses["kline_candlestick_data"] = []
        start = (1790135400000 / 1000 - 60) * 1000
        self.client.get_candlestick_data("0GUSDT", "1m", start, start + 60000, 120 / 1)
        params = self.api.calls[-1][1]
        self.assertEqual(params["start_time"], 1790135340000)
        for key in ("start_time", "end_time", "limit"):
            self.assertIs(type(params[key]), int)
        self.api.responses["get_funding_rate_history"] = []
        self.client.get_funding_rate("0GUSDT", start, start + 60000, 1.0)
        self.assertIs(type(self.api.calls[-1][1]["start_time"]), int)

    def test_invalid_integer_parameters_are_rejected_before_http(self):
        for name in ("startTime", "endTime", "limit"):
            for value in (1.5, "NaN", "Infinity", -1, True, "bad", ""):
                with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                    self.client.get_candlestick_data("0GUSDT", "1m", **{name: value})
        self.assertEqual(self.api.calls, [])

    def test_optional_integer_parameters_and_zero_timestamp(self):
        self.api.responses["kline_candlestick_data"] = []
        self.client.get_candlestick_data("0GUSDT", "1m", startTime=0.0)
        self.assertEqual(self.api.calls[-1][1], dict(symbol="0GUSDT", interval="1m", start_time=0))
        with self.assertRaises(ValueError):
            self.client.get_candlestick_data("0GUSDT", "1m", limit=0)

    def test_candle_failure_propagates_original_error_instead_of_none(self):
        error = RuntimeError("fixture API failure")
        self.api.errors["kline_candlestick_data"] = error
        with self.assertRaises(RuntimeError) as caught:
            self.center.getCandlestickData("0GUSDT", 1, 6, 1790135340000.0)
        self.assertIs(caught.exception, error)


class InstalledSdkTests(unittest.TestCase):
    """Exercises the real SDK serializer when the pinned dependency is installed."""
    def setUp(self):
        if importlib.util.find_spec("binance_sdk_derivatives_trading_usds_futures") is None:
            self.skipTest("Install requirements-binance.txt for real-SDK offline validation")
        import json
        import requests
        self.fixtures = {}
        self.requests = []

        def respond(session, method, url, **kwargs):
            self.requests.append((method, url, kwargs))
            path = url.split(".com", 1)[-1]
            payload = self.fixtures[(method, path)]
            response = requests.Response()
            response.status_code = 200
            response.headers["Content-Type"] = "application/json"
            response._content = json.dumps(payload).encode()
            return response

        self.addCleanup(patch.stopall)
        patch("socket.socket.connect", side_effect=AssertionError("Network forbidden in tests")).start()
        patch.object(requests.Session, "request", new=respond).start()
        self.client = Client(api_key="dummy-key", secret_key="dummy-secret")

    def test_real_sdk_market_data(self):
        self.fixtures[("GET", "/fapi/v1/klines")] = [
            [1, "10", "12", "9", "11", "2", 2, "22", 3, "1", "11", "0"]]
        self.assertEqual(self.client.get_candlestick_data(
            "ETHUSDT", "1m", startTime=1790135340000.0,
            endTime=1790135400000.0, limit=6.0)[0].close, 11.0)
        from urllib.parse import parse_qs
        query = parse_qs(self.requests[-1][2]["params"])
        self.assertEqual(query["startTime"], ["1790135340000"])
        self.assertEqual(query["endTime"], ["1790135400000"])
        self.assertEqual(query["limit"], ["6"])
        self.fixtures[("GET", "/fapi/v1/fundingRate")] = [
            dict(symbol="ETHUSDT", fundingRate="-0.0001", fundingTime=1)]
        self.assertLess(self.client.get_funding_rate("ETHUSDT")[0].fundingRate, 0)
        self.fixtures[("GET", "/fapi/v1/premiumIndex")] = dict(
            symbol="ETHUSDT", markPrice="2000", lastFundingRate="0.0001")
        self.assertEqual(self.client.get_mark_price("ETHUSDT").markPrice, 2000.0)

    def test_real_sdk_order_serialization(self):
        from urllib.parse import parse_qs
        self.fixtures[("POST", "/fapi/v1/order")] = dict(orderId=1, symbol="ETHUSDT")
        self.client.post_order("ETHUSDT", "SELL", "LIMIT", quantity="0.125",
                               price="2000.12345678", positionSide="SHORT")
        params = parse_qs(self.requests[-1][2]["params"])
        self.assertEqual(params["positionSide"], ["SHORT"])
        self.assertEqual(params["price"], ["2000.12345678"])
        self.fixtures[("POST", "/fapi/v1/algoOrder")] = dict(
            algoId=42, clientAlgoId="sdalgo_fixture", symbol="ETHUSDT", algoStatus="NEW")
        self.assertEqual(self.client.post_order(
            "ETHUSDT", "BUY", "STOP_MARKET", quantity="0.125",
            stopPrice="2100", positionSide="SHORT").orderId, -42)
        params = parse_qs(self.requests[-1][2]["params"])
        self.assertEqual(params["triggerPrice"], ["2100"])
        self.assertNotIn("price", params)

    def test_real_sdk_query_and_cancellation(self):
        self.fixtures[("GET", "/fapi/v1/algoOrder")] = dict(
            algoId=42, clientAlgoId="sdalgo_fixture", symbol="ETHUSDT", algoStatus="NEW")
        self.assertEqual(self.client.get_order("ETHUSDT", -42).orderId, -42)
        self.fixtures[("GET", "/fapi/v1/openOrders")] = []
        self.fixtures[("GET", "/fapi/v1/openAlgoOrders")] = [
            dict(algoId=42, symbol="ETHUSDT", algoStatus="NEW")]
        self.assertEqual(self.client.get_open_orders("ETHUSDT")[0].orderId, -42)
        for endpoint in ("/fapi/v1/allOpenOrders", "/fapi/v1/algoOpenOrders"):
            self.fixtures[("DELETE", endpoint)] = dict(code=200, msg="success")
        self.assertEqual(self.client.cancel_all_orders("ETHUSDT").code, 200)

if __name__ == "__main__":
    unittest.main()
