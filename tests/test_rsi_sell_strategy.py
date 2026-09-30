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
        self.assertIn("database_only=self.__testNo in (18, 19)", text)
        self.assertIn("if self.__testNo not in (18, 19):", text)
        self.assertIn("elif self.__testNo == 19:", text)
        self.assertIn("runSellRSIOperation(target_symbol=None)", text)


if __name__ == "__main__":
    unittest.main()
