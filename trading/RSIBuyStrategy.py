"""DB-fed RSI/BB buy signals. Times are UTC epoch milliseconds."""
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import isfinite
from statistics import fmean, pstdev

MINUTE = 60_000
QUARTER = 15 * MINUTE
DAY = 24 * 60 * MINUTE


def format_kst(epoch_seconds):
    return datetime.fromtimestamp(epoch_seconds, timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S KST')


@dataclass(frozen=True)
class Bar:
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: float


def minute_bars(rows, as_of):
    result = []
    previous = None
    for row in rows:
        raw_time = row["candleTime"]
        t = int(raw_time)
        if t != raw_time or t % MINUTE:
            raise ValueError("RSI source must contain minute-aligned timestamps")
        if previous is not None and t <= previous:
            raise ValueError("RSI source must be ordered and have no duplicate minutes")
        previous = t
        values = [float(row[k]) for k in ("open", "high", "low", "close", "volume")]
        o, h, l, c, v = values
        if (not all(isfinite(x) for x in values) or min(o, h, l, c) <= 0
                or v < 0 or l > min(o, c) or h < max(o, c) or l > h):
            raise ValueError("Invalid or missing OHLCV data")
        if t + MINUTE <= as_of:
            result.append(Bar(t, o, h, l, c, v))
    return result


def aggregate(minutes, interval, source_interval=MINUTE):
    """Only complete contiguous UTC buckets can form an indicator candle."""
    result, group = [], []
    bucket = None
    for bar in minutes:
        current = bar.time // interval * interval
        if current != bucket:
            group = []
            bucket = current
        group.append(bar)
        if (bar.time + source_interval == bucket + interval
                and len(group) == interval // source_interval
                and group[0].time == bucket
                and all(b.time - a.time == source_interval for a, b in zip(group, group[1:]))):
            result.append(Bar(bucket, group[0].open, max(x.high for x in group),
                              min(x.low for x in group), group[-1].close,
                              sum(x.volume for x in group)))
    return result


def wilder_rsi(bars, period=14, state=None):
    """Optionally carry the exact Wilder seed/smoothing state across batches."""
    state = {} if state is None else state
    values = []
    for bar in bars:
        previous_time = state.get("time")
        value = None
        if previous_time is None or bar.time - previous_time != QUARTER:
            state.update(gains=[], losses=[], avg_gain=None, avg_loss=None)
        else:
            change = bar.close - state["close"]
            gain, loss = max(change, 0), max(-change, 0)
            if state["avg_gain"] is None:
                state["gains"].append(gain)
                state["losses"].append(loss)
                if len(state["gains"]) == period:
                    state["avg_gain"] = fmean(state["gains"])
                    state["avg_loss"] = fmean(state["losses"])
            else:
                state["avg_gain"] = (state["avg_gain"] * (period-1) + gain) / period
                state["avg_loss"] = (state["avg_loss"] * (period-1) + loss) / period
            if state["avg_gain"] is not None:
                total = state["avg_gain"] + state["avg_loss"]
                value = 100 * state["avg_gain"] / total if total else 0.0
        state.update(time=bar.time, close=bar.close, value=value)
        values.append(value)
    return values


def five_minute_bars(rows, as_of):
    """Validate existing DB OHLC without requiring or inspecting volume."""
    normalized = [dict(row, volume=0) for row in rows]
    bars = minute_bars(normalized, as_of)
    if any(b.time % (5 * MINUTE) for b in bars):
        raise ValueError("candleList must contain aligned 5m candles")
    return [b for b in bars if b.time + 5 * MINUTE <= as_of]


def cooldown_previous_buy(sorted_buy_times, buy_time, cooldown_seconds):
    """Return the blocking earlier buy (epoch seconds), ignoring future records."""
    from bisect import bisect_left
    index = bisect_left(sorted_buy_times, buy_time)
    if index and buy_time - sorted_buy_times[index-1] < cooldown_seconds:
        return sorted_buy_times[index-1]
    return None


def validate_wait_minutes(wait_minutes, state):
    if isinstance(wait_minutes, bool) or not isinstance(wait_minutes, int) or wait_minutes <= 0 or wait_minutes % 15:
        raise ValueError("RSI wait_minutes must be a positive multiple of 15")
    if state.get("wait_minutes", wait_minutes) != wait_minutes:
        raise ValueError("RSI wait_minutes differs from checkpoint; use restored source and separate progress/results for a new experiment")


class RSIHistoryCache:
    """Per-symbol validated history; discard on restart and reload from DB."""
    def __init__(self):
        self.bars = deque()
        self.source_times = set()
        self.days = {}

    def prepare(self, new_bars, start, end):
        keep_from = start // DAY * DAY - 20 * DAY
        while self.bars and self.bars[0].time < keep_from:
            self.source_times.remove(self.bars.popleft().time)
        self.days = {t: bar for t, bar in self.days.items() if t >= keep_from}
        if new_bars:
            if self.bars and new_bars[0].time <= self.bars[-1].time:
                raise ValueError("RSI cache requires increasing, non-overlapping DB batches")
            self.bars.extend(new_bars)
            self.source_times.update(bar.time for bar in new_bars)
            # Rebuild only days touched by new input, including a partial day on resume.
            dirty_day = new_bars[0].time // DAY * DAY
            dirty_bars = [bar for bar in self.bars if bar.time >= dirty_day]
            for day in aggregate(dirty_bars, DAY, 5 * MINUTE):
                self.days[day.time] = day
        current_bars = [bar for bar in self.bars if bar.time >= start]
        quarters = aggregate(current_bars, QUARTER, 5 * MINUTE)
        return self.source_times, quarters, [self.days[t] for t in sorted(self.days)]


def evaluate(bars, start, end, rsi_state=None, wait_minutes=60, on_event=None, prepared=None):
    """Arm on oversold conditions; confirm on one of the following N quarters."""
    strategy_state = {} if rsi_state is None else rsi_state
    validate_wait_minutes(wait_minutes, strategy_state)
    strategy_state["wait_minutes"] = wait_minutes
    if prepared is None:
        source_times = {bar.time for bar in bars}
        quarters = aggregate(bars, QUARTER, 5 * MINUTE)
        days = aggregate(bars, DAY, 5 * MINUTE)
    else:
        source_times, quarters, days = prepared
    previous_rsi = None if rsi_state is None else rsi_state.get("value")
    if rsi_state is not None:
        quarters = [bar for bar in quarters if start <= bar.time and bar.time + QUARTER <= end]
        rsi = wilder_rsi(quarters, state=rsi_state)
    else:
        rsi = wilder_rsi(quarters)
    daily_window = deque(maxlen=20)
    day_index = 0
    for i, bar in enumerate(quarters):
        decision_time = bar.time + QUARTER
        # The cursor is the last DB 5m candle used by this closed 15m bar.
        cursor_time = decision_time - 5 * MINUTE
        while day_index < len(days) and days[day_index].time + DAY <= decision_time:
            day = days[day_index]
            if daily_window and day.time - daily_window[-1].time != DAY:
                daily_window.clear()
            daily_window.append(day)
            day_index += 1
        if not start <= bar.time < end or decision_time > end:
            continue
        prior = rsi[i-1] if i else previous_rsi
        pending = strategy_state.get("pending")
        if pending is not None and decision_time > pending["expires_at"]:
            if on_event is not None:
                expired = format_kst(pending["expires_at"] / 1000)
                on_event(f"WAIT_EXPIRED expiresAt={expired} waitMinutes={wait_minutes} reason=no_bullish_RSI_rise; buy_cancelled")
            strategy_state.pop("pending", None)
            pending = None
        if pending is not None:
            # Conditions 1/2 are latched; never refresh the original deadline.
            if (decision_time > pending["armed_at"] and rsi[i] is not None
                    and prior is not None and bar.close > bar.open and rsi[i] > prior):
                strategy_state.pop("pending", None)
                yield dict(candleTime=bar.time // 1000, position="LONG",
                           high=bar.high, low=bar.low, close=bar.close,
                           bolHigh=pending["upper"], bolLow=pending["lower"],
                           buyTime=decision_time // 1000, triggerTime=decision_time // 1000,
                           triggerPrice=bar.close, buyMode="RSI_BB_15M",
                           rsi=rsi[i], previousRSI=prior)
            continue
        if (cursor_time - 20 * DAY not in source_times
                or rsi[i] is None or len(daily_window) < 20):
            continue
        if daily_window[-1].time + DAY != decision_time // DAY * DAY:
            continue
        closes = [d.close for d in daily_window]
        mid, deviation = fmean(closes), pstdev(closes)
        lower, upper = mid - 2 * deviation, mid + 2 * deviation
        if lower > 0 and bar.close <= lower * .97 and rsi[i] <= 30:
            strategy_state["pending"] = dict(
                armed_at=decision_time, expires_at=decision_time + wait_minutes * MINUTE,
                lower=lower, upper=upper)
            if on_event is not None:
                armed = format_kst(decision_time / 1000)
                expires = format_kst((decision_time + wait_minutes * MINUTE) / 1000)
                on_event(f"WAIT_STARTED armedAt={armed} close={bar.close} bolLow={lower} "
                         f"threshold={lower * .97} rsi={rsi[i]} expiresAt={expires} waitMinutes={wait_minutes}")



def entry_price(fetch, symbol, decision_time, as_of):
    """Fetch only the exact entry minute; never substitute another candle."""
    if decision_time + MINUTE > as_of:
        return None
    rows = fetch(symbol=symbol, interval="1m", startTime=decision_time,
                 endTime=decision_time + MINUTE - 1, limit=1)
    if rows is None:
        raise RuntimeError("Entry minute request failed")
    if not rows:
        return None
    row = rows[0]
    if row.openTime != decision_time:
        return None
    price = float(row.open)
    if not isfinite(price) or price <= 0:
        raise ValueError("Invalid entry minute open")
    return price


INTRAMINUTE_MODE = "intraminute_open_v1"


class MinuteDataUnavailable(RuntimeError):
    pass


def validate_intraminute_state(state):
    mode = state.get("execution_mode")
    if mode not in (None, INTRAMINUTE_MODE) or (mode is None and ("time" in state or "pending" in state)):
        raise ValueError("Old RSI checkpoint uses closed-15m entry timing. Restore source backup and use separate/reset RSI progress and results for the intraminute strategy.")


def minute_open_prices(fetch, symbol, start, end):
    """Exact minute opens in [start,end); never substitute absent minutes."""
    rows = fetch(symbol=symbol, interval="1m", startTime=start,
                 endTime=end-1, limit=(end-start)//MINUTE)
    expected = list(range(start, end, MINUTE))
    if rows is None or [row.openTime for row in rows] != expected:
        raise MinuteDataUnavailable(f"Incomplete 1m opens for {symbol}: {format_kst(start/1000)}")
    prices = [float(row.open) for row in rows]
    if any(not isfinite(price) or price <= 0 for price in prices):
        raise MinuteDataUnavailable(f"Invalid 1m open for {symbol}")
    lows = [float(row.low) for row in rows]
    if any(not isfinite(low) or low <= 0 or low > price for low, price in zip(lows, prices)):
        raise MinuteDataUnavailable(f"Invalid 1m low for {symbol}")
    return list(zip(expected, prices, lows))


def track_pending_low(pending, price, candle_time):
    # Strict comparison retains the FIRST minute when equal lows recur.
    if pending.get("recent_low") is None or price < pending["recent_low"]:
        pending["recent_low"] = price
        pending["recent_low_time"] = candle_time


def checked_minute_ticks(provider, start, end):
    ticks = provider(start, end)
    if [tick[0] for tick in ticks] != list(range(start, end, MINUTE)):
        raise MinuteDataUnavailable("Incomplete minute-open sequence")
    for t, price, low in ticks:
        if not isfinite(price) or price <= 0 or not isfinite(low) or low <= 0 or low > price:
            raise MinuteDataUnavailable("Invalid minute open/low")
    return ticks


def evaluate_intraminute(bars, start, end, minute_opens, rsi_state=None,
                        wait_minutes=60, on_event=None, prepared=None):
    """Arm on closed 15m data, confirm using each next minute's OPEN only."""
    from copy import deepcopy
    state = {} if rsi_state is None else rsi_state
    validate_intraminute_state(state)
    validate_wait_minutes(wait_minutes, state)
    state.update(execution_mode=INTRAMINUTE_MODE, wait_minutes=wait_minutes)
    if prepared is None:
        source_times = {bar.time for bar in bars}
        quarters = aggregate(bars, QUARTER, 5*MINUTE)
        days = aggregate(bars, DAY, 5*MINUTE)
    else:
        source_times, quarters, days = prepared
    window = deque(maxlen=20)
    day_index = 0
    for bar in quarters:
        if rsi_state is not None and bar.time < start:
            continue
        close_time = bar.time + QUARTER
        if close_time > end:
            break
        pending = state.get("pending")
        had_pending = pending is not None
        if pending is not None and bar.time >= start:
            if state.get("time") != bar.time-QUARTER:
                raise MinuteDataUnavailable("Missing closed 15m history during pending entry")
            # Older intraminute checkpoints lack low history. Reconstruct only
            # completed minutes since BUY_READY before evaluating the new quarter.
            if "low_tracked_until" not in pending:
                left = pending["armed_at"]
                history_end = min(bar.time, pending["expires_at"])
                while left < history_end:
                    right = min(left + QUARTER, history_end)
                    for t, price, minute_low in checked_minute_ticks(minute_opens, left, right):
                        track_pending_low(pending, minute_low, t)
                    left = right
                pending["low_tracked_until"] = history_end
            scan_end = min(close_time, pending["expires_at"] + MINUTE)
            if bar.time < scan_end:
                ticks = checked_minute_ticks(minute_opens, bar.time, scan_end)
                opening = ticks[0][1]
                high = low = opening
                prior = state.get("value")
                for tick_time, price, minute_low in ticks:
                    if not isfinite(price) or price <= 0:
                        raise MinuteDataUnavailable("Invalid minute open")
                    high, low = max(high,price), min(low,price)
                    track_pending_low(pending, price, tick_time)
                    # Start each provisional update from the SAME closed-bar seed.
                    provisional = Bar(bar.time,opening,high,low,price,0)
                    temporary = deepcopy(state)
                    current = wilder_rsi([provisional], state=temporary)[0]
                    if prior is not None and current is not None and price > opening and current > prior:
                        state.pop("pending",None)
                        yield dict(candleTime=bar.time//1000,position="LONG",
                                   high=high,low=low,close=price,BuyPrice=price,
                                   bolHigh=pending["upper"],bolLow=pending["lower"],
                                   buyTime=tick_time//1000,triggerTime=tick_time//1000,
                                   triggerPrice=price,buyMode="RSI_BB_15M",
                                   rsi=current,previousRSI=prior,
                                   recentLow=pending["recent_low"],
                                   recentLowTime=pending["recent_low_time"]//1000)
                        break
                    # This minute's low becomes known only AFTER its open-time
                    # decision. Never include the buying minute's future low.
                    if tick_time < pending["expires_at"]:
                        track_pending_low(pending, minute_low, tick_time)
                        pending["low_tracked_until"] = tick_time + MINUTE
            if state.get("pending") is not None and close_time > pending["expires_at"]:
                state.pop("pending",None)
                had_pending = False
                if on_event:
                    on_event(f"WAIT_EXPIRED expiresAt={format_kst(pending['expires_at']/1000)} waitMinutes={wait_minutes} reason=no_bullish_RSI_rise; buy_cancelled")
        # Only now is this quarter's closing price known.
        current = wilder_rsi([bar],state=state)[0]
        while day_index < len(days) and days[day_index].time+DAY <= close_time:
            day = days[day_index]
            if window and day.time-window[-1].time != DAY:
                window.clear()
            window.append(day)
            day_index += 1
        if bar.time < start or had_pending:
            continue
        if (close_time-5*MINUTE-20*DAY not in source_times or current is None
                or len(window)<20 or window[-1].time+DAY != close_time//DAY*DAY):
            continue
        closes = [day.close for day in window]
        mid, deviation = fmean(closes), pstdev(closes)
        lower, upper = mid-2*deviation, mid+2*deviation
        if lower>0 and bar.close<=lower*.97 and current<=30:
            state["pending"] = dict(armed_at=close_time,expires_at=close_time+wait_minutes*MINUTE,
                                    lower=lower,upper=upper,
                                    recent_low=None,recent_low_time=None,low_tracked_until=close_time)
            if on_event:
                on_event(f"WAIT_STARTED armedAt={format_kst(close_time/1000)} close={bar.close} bolLow={lower} threshold={lower*.97} rsi={current} expiresAt={format_kst((close_time+wait_minutes*MINUTE)/1000)} waitMinutes={wait_minutes}")
