"""Offline TEST 19 tests: no application/config imports, DB or network."""
import ast
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


s = load("sell_strategy", "trading/RSISellStrategy.py")
schema = load("sell_schema", "model/SellResultSchema.py")
with patch.dict(sys.modules, {"model.SellResultSchema": schema}):
    r = load("sell_repository", "model/RSISellRepository.py")
with patch.dict(sys.modules, {"trading.RSISellStrategy": s, "model.RSISellRepository": r}):
    sim = load("sell_simulation", "trading/RSISellSimulation.py")
M, H = s.MINUTE, s.FOUR_HOURS
BASE = 20 * H


def buy(low=98):
    return dict(uid=42, symbol="TESTUSDT", BuyPrice=100, recentLow=low,
                buyTime=BASE//1000, coinIndex=1, high=101, low=98)


def history(price=100):
    return {t: price for t in range(BASE-19*H, BASE, H)}


def batch(state, prices, closes=None):
    start = state["next_time"]
    ticks = [(start+i*M, *(p if isinstance(p, tuple) else (p, p))) for i, p in enumerate(prices)]
    return s.evaluate_batch(state, ticks, history() if closes is None else closes,
                            start+len(prices)*M)


class ExitTests(unittest.TestCase):
    def test_stop_and_profit_exit_fees_on_sold_notional(self):
        state = s.initial_state(buy(), 10000, s.ROUND_TRIP_FEE_PERCENT)
        events = batch(state, [(100, 95)])
        self.assertAlmostEqual(events[0]["profit"], -510)
        state = s.initial_state(buy(), 10000, s.ROUND_TRIP_FEE_PERCENT)
        events = batch(state, [100]*5+[105, (100, 95)], history(110))
        self.assertAlmostEqual(events[0]["profit"], 250-3.5)
        self.assertAlmostEqual(events[1]["profit"], -250-5)
        self.assertAlmostEqual(sum(e["profit"] for e in events), -8.5)
        self.assertAlmostEqual(state["realized"], -8.5)
        state = s.initial_state(buy(), 10000, s.ROUND_TRIP_FEE_PERCENT)
        events = batch(state, [100]*5+[106])
        self.assertEqual([e["stage"] for e in events], ["TP5", "BB4H"])
        for event in events:
            self.assertAlmostEqual(event["profit"], 300-3.5)
        self.assertAlmostEqual(sum(e["profit"] for e in events), 600-7)

    def test_stop_on_exact_touch_closes_all_at_fixed_price(self):
        state = s.initial_state(buy(), 1000, .1)
        self.assertEqual(state["stop_price"], 95)
        events = batch(state, [(100, 95), (100, 94), (90, 89)])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["price"], 95)
        self.assertEqual(events[0]["fraction"], 1)
        self.assertEqual(events[0]["time"], BASE//1000)
        self.assertAlmostEqual(events[0]["profit"], -51)
        self.assertEqual(state["remaining"], 0)

    def test_deeper_low_and_gap_fill_at_stop(self):
        state = s.initial_state(buy(90), 1000, 0)
        self.assertEqual(state["stop_price"], 90)
        events = batch(state, [(89, 88)])
        self.assertEqual(events[0]["price"], 90)
        self.assertEqual(state["remaining"], 0)

    def test_buy_minute_low_is_checked(self):
        state = s.initial_state(buy(), 1000, 0)
        event = batch(state, [(100, 94)])[0]
        self.assertEqual(event["time"], buy()["buyTime"])

    def test_tp_only_five_minutes_and_both_halves_same_tick(self):
        state = s.initial_state(buy(), 1000, 0)
        events = batch(state, [100, 106, 106, 106, 106, 106])
        self.assertEqual([e["stage"] for e in events], ["TP5", "BB4H"])
        self.assertEqual([e["fraction"] for e in events], [.5, .5])
        self.assertTrue(all(e["time"] == BASE//1000+300 for e in events))

    def test_tp_then_stop_remaining_half(self):
        state = s.initial_state(buy(), 1000, 0)
        events = batch(state, [100]*5+[105, (100, 95)], history(110))
        self.assertEqual([e["stage"] for e in events], ["TP5", "STOP"])
        self.assertEqual(events[-1]["price"], 95)
        self.assertEqual(events[-1]["fraction"], .5)
        self.assertEqual(state["remaining"], 0)

    def test_stop_then_tp_never_oversells(self):
        state = s.initial_state(buy(), 1000, 0)
        events = batch(state, [(100, 94)]+[100]*4+[105])
        self.assertEqual([e["stage"] for e in events], ["STOP"])
        self.assertEqual(sum(e["fraction"] for e in events), 1)
        self.assertEqual(state["remaining"], 0)

    def test_open_profit_precedes_later_low(self):
        state = s.initial_state(buy(), 1000, 0)
        events = batch(state, [100]*5+[(105, 94)], history(110))
        self.assertEqual([e["stage"] for e in events], ["TP5", "STOP"])
        state = s.initial_state(buy(), 1000, 0)
        events = batch(state, [100]*5+[(106, 94)])
        self.assertEqual([e["stage"] for e in events], ["TP5", "BB4H"])

    def test_provisional_ignores_future_close(self):
        closes = history()
        upper = s.provisional_upper(BASE+5*M, 106, closes)
        closes[BASE] = 100000
        self.assertEqual(s.provisional_upper(BASE+5*M, 106, closes), upper)

    def test_missing_or_invalid_data(self):
        state = s.initial_state(buy(), 1000, 0)
        with self.assertRaises(s.SellDataUnavailable):
            s.evaluate_batch(state, [(BASE+M, 100, 99)], {}, BASE+2*M)
        with self.assertRaises(s.SellDataUnavailable):
            batch(state, [(100, 101)])
        with self.assertRaises(ValueError):
            s.initial_state(buy(0), 1000, 0)

    def test_split_batches_dont_repeat_stop(self):
        whole = s.initial_state(buy(), 1000, .1)
        split = deepcopy(whole)
        prices = [100, 100, (100, 95), 100, 100, 105]
        expected = batch(whole, prices)
        actual = batch(split, prices[:2])
        actual += batch(split, prices[2:])
        self.assertEqual(actual, expected)
        self.assertEqual(split, whole)


class CacheTests(unittest.TestCase):
    def test_upper_is_computed_once_per_time_and_price(self):
        cache = sim.CandleCache(Mock(side_effect=self.fetch), "TESTUSDT", 0)
        with patch.object(sim, "provisional_upper", wraps=s.provisional_upper) as calculate:
            first = cache.upper_at(BASE, 106)
            self.assertEqual(cache.upper_at(BASE, 106), first)
            self.assertEqual(calculate.call_count, 1)
            cache.upper_at(BASE, 107)
            self.assertEqual(calculate.call_count, 2)

    def fetch(self, **kw):
        step = M if kw["interval"] == "1m" else H
        return [SimpleNamespace(openTime=t, open=100, low=99, close=100)
                for t in range(kw["startTime"], kw["endTime"]+1, step)]

    def test_overlap_fetches_only_missing_minutes(self):
        fetch = Mock(side_effect=self.fetch)
        cache = sim.CandleCache(fetch, "TESTUSDT", 0)
        first = cache.ticks(BASE, BASE+500*M)
        second = cache.ticks(BASE+100*M, BASE+600*M)
        self.assertEqual(first[100:], second[:400])
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(fetch.call_args.kwargs["limit"], 100)
        cache.ticks(BASE+200*M, BASE+400*M)
        self.assertEqual(fetch.call_count, 2)

    def test_closed_hours_share_history_and_exclude_current_bucket(self):
        fetch = Mock(side_effect=self.fetch)
        cache = sim.CandleCache(fetch, "TESTUSDT", 0)
        self.assertEqual(max(cache.closed_hours(BASE)), BASE-H)
        cache.closed_hours(BASE+5*M)
        self.assertEqual(fetch.call_count, 1)
        cache.closed_hours(BASE+H)
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(fetch.call_args.kwargs["limit"], 1)

    def test_bounded_cache_refetches_evicted_candles(self):
        fetch = Mock(side_effect=self.fetch)
        cache = sim.CandleCache(fetch, "TESTUSDT", 0, minute_capacity=500)
        first = cache.ticks(BASE, BASE+500*M)
        cache.ticks(BASE+500*M, BASE+1000*M)
        self.assertEqual(len(cache.minutes), 500)
        self.assertEqual(cache.ticks(BASE, BASE+500*M), first)
        self.assertEqual(fetch.call_count, 3)

    def test_failed_response_not_cached(self):
        fetch = Mock(return_value=[])
        cache = sim.CandleCache(fetch, "TESTUSDT", 0)
        with self.assertRaises(s.SellDataUnavailable):
            cache.ticks(BASE, BASE+M)
        self.assertEqual(len(cache.minutes), 0)
        fetch.side_effect = self.fetch
        self.assertEqual(len(cache.ticks(BASE, BASE+M)), 1)

    def test_lazy_and_eager_outputs_and_states_match(self):
        for prices in ([100]*5+[106], [(100, 95)], [100]*5+[105, (100, 95)], [100]*30):
            eager = s.initial_state(buy(), 1000, .1)
            lazy = deepcopy(eager)
            ticks = [(BASE+i*M, *(p if isinstance(p, tuple) else (p, p)))
                     for i, p in enumerate(prices)]
            closes = history(110)
            expected = s.evaluate_batch(eager, ticks, closes, BASE+len(ticks)*M)
            provider = Mock(return_value=closes)
            actual = s.evaluate_batch(lazy, ticks, provider, BASE+len(ticks)*M)
            self.assertEqual(actual, expected)
            self.assertEqual(lazy, eager)
            if not eager["took_half"]:
                provider.assert_not_called()


class MemoryRepository:
    def __init__(self):
        self.state, self.events, self.fail = None, {}, False
    def acquire(self): pass
    def release(self): pass
    def prepare(self): pass
    def buys(self, symbol): return [buy()]
    def load(self, uid): return deepcopy(self.state)
    def save_event(self, buy, state, event):
        key = event["stage"]
        fresh = key not in self.events
        self.events.setdefault(key, event)
        return fresh
    def checkpoint(self, uid, state):
        if self.fail:
            raise RuntimeError("interrupted before checkpoint")
        self.state = deepcopy(state)


class IntegrationTests(unittest.TestCase):
    def test_long_overlapping_positions_match_independent_runs_without_rereads(self):
        records = [buy(), {**buy(), "uid": 43, "buyTime": buy()["buyTime"]+60}]
        class Repo(MemoryRepository):
            def __init__(self, records):
                self.records, self.states, self.results = records, {}, {}
            def buys(self, symbol): return self.records
            def load(self, uid): return deepcopy(self.states.get(uid))
            def save_event(self, buy, state, event):
                self.results.setdefault(buy["uid"], []).append(deepcopy(event))
                return True
            def checkpoint(self, uid, state): self.states[uid] = deepcopy(state)
        def fetch(**kw):
            if kw["interval"] == "4h":
                return [SimpleNamespace(openTime=t, close=100)
                        for t in range(kw["startTime"], kw["endTime"]+1, H)]
            return [SimpleNamespace(openTime=t, open=106 if t >= BASE+51010*M else 100, low=99)
                    for t in range(kw["startTime"], kw["endTime"]+1, M)]
        expected_results, expected_states = {}, {}
        for record in records:
            repo = Repo([record])
            sim.run(repo, fetch, Mock(), 1000, .1,
                    end_time=(BASE+51020*M)//1000, request_pause=0)
            expected_results.update(repo.results)
            expected_states.update(repo.states)
        repo, counted = Repo(records), Mock(side_effect=fetch)
        with patch.object(sim, "provisional_upper", wraps=s.provisional_upper) as calculate:
            sim.run(repo, counted, Mock(), 1000, .1,
                    end_time=(BASE+51020*M)//1000, request_pause=0)
            self.assertEqual(calculate.call_count, 1)
        self.assertEqual(repo.results, expected_results)
        self.assertEqual(repo.states, expected_states)
        ranges = [(c.kwargs["startTime"], c.kwargs["endTime"])
                  for c in counted.call_args_list if c.kwargs["interval"] == "1m"]
        self.assertTrue(all(a[1] < b[0] for a, b in zip(ranges, ranges[1:])))

    def test_shared_symbol_cache_reduces_calls_and_matches_independent_runs(self):
        buys = [buy(), {**buy(), "uid": 43, "buyTime": buy()["buyTime"]+60}]
        class Repo(MemoryRepository):
            def __init__(self, records):
                self.records, self.states, self.results = records, {}, {}
            def buys(self, symbol): return self.records
            def load(self, uid): return self.states.get(uid)
            def save_event(self, buy, state, event):
                self.results.setdefault(buy["uid"], []).append(deepcopy(event))
                return True
            def checkpoint(self, uid, state): self.states[uid] = deepcopy(state)
        expected = {}
        independent_calls = 0
        for record in buys:
            repo, fetch = Repo([record]), Mock(side_effect=self.fetch)
            sim.run(repo, fetch, Mock(), 1000, 0, end_time=(BASE+6*M)//1000, request_pause=0)
            expected.update(repo.results)
            independent_calls += fetch.call_count
        repo, fetch = Repo(buys), Mock(side_effect=self.fetch)
        sim.run(repo, fetch, Mock(), 1000, 0, end_time=(BASE+6*M)//1000, request_pause=0)
        self.assertEqual(repo.results, expected)
        self.assertEqual(independent_calls, 4)
        self.assertEqual(fetch.call_count, 2)

    def test_stop_requires_no_four_hour_request(self):
        def fetch(**kw):
            self.assertEqual(kw["interval"], "1m")
            return [SimpleNamespace(openTime=t, open=100, low=95)
                    for t in range(kw["startTime"], kw["endTime"]+1, M)]
        repo = MemoryRepository()
        sim.run(repo, fetch, Mock(), 1000, 0, end_time=(BASE+M)//1000, request_pause=0)
        self.assertEqual(repo.events["STOP"]["fraction"], 1)

    def test_old_checkpoint_rejected_before_fetch(self):
        repo = MemoryRepository()
        repo.state = s.initial_state(buy(), 1000, 0)
        repo.state["version"] = 2
        fetch = Mock(side_effect=AssertionError("must not fetch old checkpoint"))
        with self.assertRaisesRegex(ValueError, "checkpoint mismatch.*version"):
            sim.run(repo, fetch, Mock(), 1000, 0, request_pause=0)
        fetch.assert_not_called()

    def fetch(self, **kwargs):
        if kwargs["interval"] == "4h":
            return [SimpleNamespace(openTime=t, close=100)
                    for t in range(kwargs["startTime"], kwargs["endTime"]+1, H)]
        return [SimpleNamespace(openTime=t, open=106 if t >= BASE+5*M else 100, low=99)
                for t in range(kwargs["startTime"], kwargs["endTime"]+1, M)]

    def test_restart_after_committed_legs_before_checkpoint(self):
        repo = MemoryRepository()
        repo.fail = True
        with self.assertRaisesRegex(RuntimeError, "interrupted"):
            sim.run(repo, self.fetch, Mock(), 1000, 0,
                    end_time=(BASE+6*M)//1000, request_pause=0)
        self.assertEqual(len(repo.events), 2)
        repo.fail = False
        count = sim.run(repo, self.fetch, Mock(), 1000, 0,
                        end_time=(BASE+6*M)//1000, request_pause=0)
        self.assertEqual(count, 0)
        self.assertEqual(repo.state["remaining"], 0)
        fetch = Mock(side_effect=AssertionError("completed trade fetched again"))
        sim.run(repo, fetch, Mock(), 1000, 0, request_pause=0)

    def test_missing_minute_does_not_checkpoint(self):
        repo = MemoryRepository()
        def missing(**kwargs):
            rows = self.fetch(**kwargs)
            return rows[1:] if kwargs["interval"] == "1m" else rows
        sim.run(repo, missing, Mock(), 1000, 0,
                end_time=(BASE+6*M)//1000, request_pause=0)
        self.assertIsNone(repo.state)
        self.assertEqual(repo.events, {})

    def test_sell_record_kst_identity_and_quantity(self):
        cursor = Mock()
        cursor.fetchall.return_value = []
        connection = SimpleNamespace(cursor=cursor, commit=Mock())
        repo = r.RSISellRepository(connection)
        names = ["symbol", "buyTime", "sellTime", "buyTimeEpoch", "sellTimeEpoch",
                 "quantity", "quantityOrg", "conditions", "buyMode"]
        repo.columns = [dict(Field=n, Type="varchar(64)", Extra="") for n in names]
        state = s.initial_state(buy(), 1000, 0)
        event = batch(state, [94])[0]
        self.assertTrue(repo.save_event(buy(), state, event))
        values = dict(zip(names, cursor.execute.call_args.args[1]))
        self.assertEqual(values["quantity"], 10)
        self.assertEqual(values["conditions"], "RSI19v3:42")
        self.assertEqual(values["sellTime"], r.kst(event["time"]))
        saved_row = r.summary_values(buy(), state, [event])
        saved_row.update(uid=1, bolHigh=0)
        cursor.fetchall.return_value = [saved_row]
        self.assertFalse(repo.save_event(buy(), state, event))

    def test_service_19_routes_to_sell_without_trading_initialization(self):
        tree = ast.parse((ROOT/"SignalDetectorService.py").read_text(encoding="utf-8-sig"))
        text = ast.unparse(tree)
        self.assertIn("database_only=self.__testNo in (18, 19, 20)", text)
        self.assertIn("if self.__testNo not in (18, 19, 20):", text)
        self.assertIn("elif self.__testNo == 19:", text)
        self.assertIn("runSellRSIOperation(target_symbol=None)", text)


if __name__ == "__main__":
    unittest.main()
