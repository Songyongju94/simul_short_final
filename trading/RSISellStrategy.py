"""TEST 19: open-price profit exits and low-triggered full remaining stop."""
from math import isfinite
from statistics import fmean, pstdev

MINUTE = 60_000
FOUR_HOURS = 240 * MINUTE
ROUND_TRIP_FEE_PERCENT = 0.07  # Combined buy/sell fee, on original buy notional.


class SellDataUnavailable(ValueError):
    pass


def initial_state(buy, balance, fee_percent):
    price, low = float(buy["BuyPrice"]), float(buy["recentLow"] or 0)
    if not all(isfinite(x) and x > 0 for x in (price, low, balance)):
        raise ValueError("BuyPrice, recentLow and balance must be positive")
    if low > price or not isfinite(fee_percent) or fee_percent < 0:
        raise ValueError("Invalid recentLow or fee")
    if int(buy["buyTime"]) % 60:
        raise ValueError("RSI buyTime must be an epoch-second minute boundary")
    return dict(version=3, buy_price=price, recent_low=low,
                stop_price=min(low, price * .95), balance=balance,
                fee_percent=fee_percent, remaining=1.0, took_half=False,
                realized=0.0, next_time=int(buy["buyTime"]) * 1000)


def provisional_upper(t, price, closes):
    bucket = t // FOUR_HOURS * FOUR_HOURS
    required = [bucket - n * FOUR_HOURS for n in range(19, 0, -1)]
    if any(k not in closes for k in required):
        raise SellDataUnavailable("Missing 19 consecutive closed 4h candles")
    values = [float(closes[k]) for k in required] + [price]
    if any(not isfinite(x) or x <= 0 for x in values):
        raise SellDataUnavailable("Invalid closed 4h price")
    return fmean(values) + 2 * pstdev(values)


def evaluate_batch(state, ticks, four_hour_closes, end, upper_at=None):
    """Mutate a private state copy; caller persists events before its checkpoint."""
    if [t for t, price, low in ticks] != list(range(state["next_time"], end, MINUTE)):
        raise SellDataUnavailable("Missing/duplicate 1m opens; checkpoint unchanged")
    if any(not isfinite(price) or price <= 0 or not isfinite(low) or low <= 0
           or low > price for t, price, low in ticks):
        raise SellDataUnavailable("Invalid 1m open/low")
    events = []

    def sell(t, price, fraction, stage, upper=0):
        quantity = state["balance"] / state["buy_price"] * fraction
        percent = (price / state["buy_price"] - 1) * 100
        profit = state["balance"] * fraction * (percent - state["fee_percent"]) / 100
        state["remaining"] -= fraction
        state["realized"] += profit
        events.append(dict(time=t // 1000, price=price, fraction=fraction,
                           stage=stage, quantity=quantity, profit=profit,
                           percent=percent, realized=state["realized"], upper=upper))

    for t, price, low in ticks:
        if state["remaining"] <= 0:
            break
        # The open is observed before this minute's final low. Do not use a
        # later intraminute low to suppress an already executable profit exit.
        if t % (5 * MINUTE) == 0:
            if not state["took_half"] and price >= state["buy_price"] * 1.05:
                sell(t, price, min(.5, state["remaining"]), "TP5")
                state["took_half"] = True
            if state["took_half"] and state["remaining"] > 0:
                # Resolve closed history only when a Bollinger exit is evaluated.
                if upper_at is not None:
                    upper = upper_at(t, price)
                else:
                    closes = four_hour_closes(t) if callable(four_hour_closes) else four_hour_closes
                    upper = provisional_upper(t, price, closes)
                if price > upper:
                    sell(t, price, state["remaining"], "BB4H", upper)
        if state["remaining"] > 0 and low <= state["stop_price"]:
            # Requested model: fill at the fixed stop even when the open gaps
            # below it. Close all remaining quantity, including an exact touch.
            sell(t, state["stop_price"], state["remaining"], "STOP")
        state["next_time"] = t + MINUTE
    return events
