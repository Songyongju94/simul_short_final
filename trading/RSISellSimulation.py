"""Bounded historical API reads and restartable TEST 19 orchestration."""
from copy import deepcopy
from math import isfinite
import time

from trading.RSISellStrategy import (MINUTE, FOUR_HOURS, SellDataUnavailable,
                                    initial_state, evaluate_batch)
from model.RSISellRepository import kst


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
        for buy in repository.buys(target_symbol):
            symbol, uid = buy["symbol"], buy["uid"]
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
            closes = {}
            while state["remaining"] > 0 and state["next_time"] < end:
                left = state["next_time"]
                right = min(left + 500 * MINUTE, end)
                rows = fetch(symbol=symbol, interval="1m", startTime=left,
                             endTime=right-1, limit=(right-left)//MINUTE)
                time.sleep(request_pause)
                ticks = [(int(row.openTime), float(row.open), float(row.low)) for row in (rows or [])]
                first_bucket = left // FOUR_HOURS * FOUR_HOURS
                last_bucket = (right-MINUTE) // FOUR_HOURS * FOUR_HOURS
                required = range(first_bucket-19*FOUR_HOURS, last_bucket, FOUR_HOURS)
                missing = [t for t in required if t not in closes]
                if missing:
                    history = fetch(symbol=symbol, interval="4h", startTime=missing[0],
                                    endTime=missing[-1]+FOUR_HOURS-1, limit=100)
                    time.sleep(request_pause)
                    for row in history or []:
                        t, close = int(row.openTime), float(row.close)
                        if t % FOUR_HOURS or not isfinite(close) or close <= 0:
                            raise SellDataUnavailable("Invalid 4h candle")
                        if t in required:
                            closes[t] = close
                updated = deepcopy(state)
                try:
                    events = evaluate_batch(updated, ticks, closes, right)
                except SellDataUnavailable as exc:
                    log(f"RSI SELL WAITING {symbol} buyUid={uid} nextTime={kst(left/1000)} KST reason={exc}")
                    break
                # Commit each leg first. Replay deduplicates legs if checkpoint write fails.
                for event in events:
                    if repository.save_event(buy, updated, event):
                        saved += 1
                        log(f"RSI SELL SAVED {symbol} buyUid={uid} stage={event['stage']} "
                            f"sellTime={kst(event['time'])} KST price={event['price']} "
                            f"fraction={event['fraction']} stopPrice={updated['stop_price']}")
                repository.checkpoint(uid, updated)
                state = updated
                closes = {t: v for t, v in closes.items()
                          if t >= state["next_time"]//FOUR_HOURS*FOUR_HOURS-19*FOUR_HOURS}
            status = "COMPLETED" if state["remaining"] == 0 else "OPEN"
            log(f"RSI SELL {status} {symbol} buyUid={uid} remaining={state['remaining']} "
                f"nextTime={kst(state['next_time']/1000)} KST")
        return saved
    finally:
        repository.release()
