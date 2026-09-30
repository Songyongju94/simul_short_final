# Binance USD-M SDK migration

TradingBinance now uses the official
`binance-sdk-derivatives-trading-usds-futures==17.4.1` package through
`trading/BinanceFuturesClient.py`. No runtime imports of `binance_f` remain
in the application Python source.

## Install in the interpreter used by VS Code

From the project directory:

```powershell
C:\Python310\python.exe -m pip install -r requirements-binance.txt
C:\Python310\python.exe -I -B tests\test_binance_futures_migration.py
```

The dependency file pins the Binance SDK and NumPy 1.26.4 for compatibility
with the existing tensorflow-intel 2.18.0; it is not a complete application
environment specification. The existing application dependencies are still
required. Do not install into the empty project venv while launch.json points at
C:/Python310/python.exe.

The SDK is now installed in C:/Python310. All 25 offline tests passed,
including the three real-SDK serializer tests with mocked HTTP responses.
The installed NumPy 2.2.2 conflicts with tensorflow-intel 2.18.0; reinstall
from requirements-binance.txt to apply the compatible NumPy 1.26.4 pin,
then run `C:/Python310/python.exe -m pip check`. The pin satisfies all active
NumPy requirements found in installed package metadata. Binary imports still
need validation after installation. These tests never start run.py, instantiate
Config/Log or use real credentials; SDK tests block socket connections.

## API mapping

| Existing adapter operation | Official SDK REST method |
| --- | --- |
| Exchange information | exchange_information |
| All candle intervals | kline_candlestick_data |
| Funding history | get_funding_rate_history |
| Mark price | mark_price |
| Hedge mode | change_position_mode |
| Leverage | change_initial_leverage |
| Margin type | change_margin_type |
| Recent market trades | recent_trades_list |
| Account trades | account_trade_list |
| LIMIT / MARKET | new_order |
| STOP / TAKE_PROFIT / conditional market / trailing orders | new_algo_order |
| Open orders | current_all_open_orders + current_all_algo_open_orders |
| Order query | query_order or query_algo_order |
| Cancel all | cancel_all_open_orders + cancel_all_algo_open_orders |

The old TradingBinance public methods and candle field names remain in place.
Funding rates and numeric trade/order fields are converted to numbers.
Mark price remains a single object. Existing strategy precision adjustments
(including quantityPrecision + 2) and funding time arguments are preserved;
this migration does not change the trading strategy or historical calculations.

## Conditional orders

Binance now handles conditional orders separately from regular orders.
A conditional response retains the real positive `algoId` and exposes
`orderId = -algoId` as the application's stable identifier. Ordinary order IDs
remain positive. Pass the returned orderId unchanged to getOrder, including
after restart; do not send its negative value directly to Binance.

This ID convention is a deliberate contract extension. External consumers
outside this repository must preserve signed integer IDs. Old regular order IDs
continue to query the regular API. An existing positive algo ID must be supplied
as its negative counterpart. Automatically generated conditional client IDs
begin with `sdalgo_`; client-ID-only lookup uses that prefix. For a custom
conditional client ID, query by the returned negative orderId.

After a conditional order triggers, getOrder queries the resulting ordinary
order using actualOrderId and reports its real fill status. Algo status
FINISHED alone is not treated as FILLED. Pending algo responses expose the
available trigger state rather than inventing filled quantities.

Open-order queries include both families. Cancel-all attempts both families
even if the first request fails and raises on partial failure. It is not an
atomic operation. Order requests are not automatically retried after timeout.

Trailing-stop support in the low-level adapter requires callbackRate, with an
optional activationPrice. The existing TradingBinance.postOrder data tuple
does not expose those parameters and has not been expanded.

## Validation limits

No live service, account-mode change, order, cancellation, or real exchange
request was executed. Offline tests do not establish exchange acceptance,
account settings, current symbol filters, or production readiness. Install the
pinned package and pass the real-SDK offline tests before a separate controlled
demo/testnet validation.

Sources:
- https://github.com/binance/binance-connector-python/tree/master/clients/derivatives_trading_usds_futures
- https://pypi.org/project/binance-sdk-derivatives-trading-usds-futures/17.4.1/
- https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/New-Algo-Order
