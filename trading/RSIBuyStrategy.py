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
