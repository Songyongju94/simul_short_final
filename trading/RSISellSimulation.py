"""Bounded historical API reads and restartable TEST 19 orchestration."""
from copy import deepcopy
from collections import OrderedDict
from heapq import heappop, heappush
from itertools import groupby
from math import isfinite
import time

from trading.RSISellStrategy import (MINUTE, FOUR_HOURS, SellDataUnavailable,
                                    initial_state, evaluate_batch, provisional_upper)
from model.RSISellRepository import kst


class CandleCache:
    """Bounded, per-symbol LRU. Cache completed candles, never failed reads."""
    def __init__(self, fetch, symbol, request_pause=.25, minute_capacity=50000,
                 hour_capacity=1024):
        if minute_capacity < 500 or hour_capacity < 19:
            raise ValueError("Candle cache capacity is too small")
        self.fetch, self.symbol, self.pause = fetch, symbol, request_pause
        self.minutes, self.hours = OrderedDict(), OrderedDict()
        self.uppers = OrderedDict()
        self.minute_capacity, self.hour_capacity = minute_capacity, hour_capacity

    def _read(self, cache, times, interval, step, limit, capacity):
        missing = [t for t in times if t not in cache]
        pending = {}
        index = 0
        while index < len(missing):
            left = missing[index]
            end = index + 1
            while (end < len(missing) and end-index < limit
                   and missing[end] == missing[end-1]+step):
                end += 1
            expected = missing[index:end]
            rows = self.fetch(symbol=self.symbol, interval=interval, startTime=left,
                              endTime=expected[-1]+step-1, limit=len(expected))
            time.sleep(self.pause)
            if rows is None or [int(row.openTime) for row in rows] != expected:
                raise SellDataUnavailable(f"Missing/duplicate {interval} candles")
            values = []
            for row in rows:
                if interval == "1m":
                    price, low = float(row.open), float(row.low)
                    if not isfinite(price) or price <= 0 or not isfinite(low) or low <= 0 or low > price:
                        raise SellDataUnavailable("Invalid 1m open/low")
                    values.append((int(row.openTime), price, low))
                else:
                    close = float(row.close)
                    if not isfinite(close) or close <= 0:
                        raise SellDataUnavailable("Invalid 4h close")
                    values.append(close)
            pending.update(zip(expected, values))
            index = end
        cache.update(pending)
        result = []
        for t in times:
            result.append(cache[t])
            cache.move_to_end(t)
        while len(cache) > capacity:
            cache.popitem(last=False)
        return result

    def ticks(self, start, end):
        return self._read(self.minutes, list(range(start, end, MINUTE)), "1m",
                          MINUTE, 500, self.minute_capacity)

    def closed_hours(self, tick_time):
        bucket = tick_time // FOUR_HOURS * FOUR_HOURS
        times = list(range(bucket-19*FOUR_HOURS, bucket, FOUR_HOURS))
        values = self._read(self.hours, times, "4h", FOUR_HOURS, 100, self.hour_capacity)
        return dict(zip(times, values))

    def upper_at(self, tick_time, price):
        key = (tick_time, price)
        if key not in self.uppers:
            # Keep the exact original formula and floating-point operations.
            self.uppers[key] = provisional_upper(tick_time, price, self.closed_hours(tick_time))
        self.uppers.move_to_end(key)
        value = self.uppers[key]
        while len(self.uppers) > 1024:
            self.uppers.popitem(last=False)
        return value


def run(repository, fetch, log, balance, fee_percent, target_symbol=None,
        end_time=None, request_pause=.25):
    # Exclude the forming minute because the stop uses its completed LOW.
    end = int(time.time() * 1000) // MINUTE * MINUTE
    if end_time is not None:
        end = min(end, int(end_time * 1000) // MINUTE * MINUTE)
    saved = 0
    repository.acquire()
    try:
        repository.prepare()
        records = sorted(repository.buys(target_symbol),
                         key=lambda buy: (buy["symbol"], buy["buyTime"], buy["uid"]))
        for symbol, group in groupby(records, key=lambda buy: buy["symbol"]):
            cache = CandleCache(fetch, symbol, request_pause)
            queue, positions = [], {}
            for buy in group:
                uid = buy["uid"]
                try:
                    seed = initial_state(buy, balance, fee_percent)
                except ValueError as exc:
                    log(f"RSI SELL SKIPPED {symbol} buyUid={uid} reason={exc}")
                    continue
                seed.update(symbol=symbol, buy_time=int(buy["buyTime"]))
                state = repository.load(uid) or seed
                for key in ("version", "symbol", "buy_time", "buy_price", "recent_low",
                            "stop_price", "balance", "fee_percent"):
                    if state.get(key) != seed[key]:
                        raise ValueError(f"TEST 19 checkpoint mismatch: buyUid={uid}, {key}")
                positions[uid] = (buy, state)
                if state["remaining"] > 0 and state["next_time"] < end:
                    heappush(queue, (state["next_time"], uid))
            # Always service the earliest unprocessed position for this symbol.
            # Each position retains its original 500-minute batch boundaries:
            # missing data, replay and checkpoint semantics therefore stay intact.
            # All overlapping windows fit in the shared cache (at most 999
            # minutes ahead of the earliest active cursor).
            while queue:
                _, uid = heappop(queue)
                buy, state = positions[uid]
                left = state["next_time"]
                right = min(left + 500 * MINUTE, end)
                updated = deepcopy(state)
                try:
                    ticks = cache.ticks(left, right)
                    events = evaluate_batch(updated, ticks, cache.closed_hours, right,
                                            upper_at=cache.upper_at)
                except SellDataUnavailable as exc:
                    log(f"RSI SELL WAITING {symbol} buyUid={uid} nextTime={kst(left/1000)} KST reason={exc}")
                    continue
                # Commit each leg first. Replay deduplicates legs if checkpoint write fails.
                for event in events:
                    if repository.save_event(buy, updated, event):
                        saved += 1
                        log(f"RSI SELL SAVED {symbol} buyUid={uid} stage={event['stage']} "
                            f"sellTime={kst(event['time'])} KST price={event['price']} "
                            f"fraction={event['fraction']} stopPrice={updated['stop_price']}")
                repository.checkpoint(uid, updated)
                state = updated
                positions[uid] = (buy, state)
                if state["remaining"] > 0 and state["next_time"] < end:
                    heappush(queue, (state["next_time"], uid))
            for uid, (buy, state) in positions.items():
                status = "COMPLETED" if state["remaining"] == 0 else "OPEN"
                log(f"RSI SELL {status} {symbol} buyUid={uid} remaining={state['remaining']} "
                    f"nextTime={kst(state['next_time']/1000)} KST")
        return saved
    finally:
        repository.release()
