"""Offline tests: no application imports, config, real DB or network."""
import ast
import json
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
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
s = load("rsi_strategy_test", "trading/RSIBuyStrategy.py")
repo = load("rsi_repo_test", "model/RSICandleRepository.py")
M, Q, D = s.MINUTE, s.QUARTER, s.DAY

def fixture():
    bars = [s.Bar(t,100,100,100,100,0) for t in range(0,20*D,5*M)]
    for i in range(21):
        close = 99-i if i<20 else 80.1
        opening = close+.5 if i<20 else 79.9
        for j in range(3):
            bars.append(s.Bar(20*D+i*Q+j*5*M,opening,max(opening,close),
                              min(opening,close),close,0))
    return bars, 0, 20*D+21*Q

def rows(bars):
    return [dict(candleTime=b.time,open=b.open,high=b.high,low=b.low,close=b.close) for b in bars]

class StrategyTests(unittest.TestCase):
    def test_buy_cooldown_boundaries_and_future_history(self):
        buys = [1000, 20000]
        self.assertEqual(s.cooldown_previous_buy(buys, 8199, 7200), 1000)
        self.assertIsNone(s.cooldown_previous_buy(buys, 8200, 7200))
        self.assertIsNone(s.cooldown_previous_buy(buys, 500, 7200))
        self.assertIsNone(s.cooldown_previous_buy([], 500, 7200))
        self.assertIsNone(s.cooldown_previous_buy(buys, 1001, 0))
        self.assertEqual(s.cooldown_previous_buy(buys, 8200, 10800), 1000)
        # A skipped candidate must not extend the original cooldown.
        self.assertIsNone(s.cooldown_previous_buy(buys, 8201, 7200))

    def test_no_volume_or_db_minute_needed(self):
        bars,start,end=fixture()
        result,=s.evaluate(s.five_minute_bars(rows(bars),end),start,end)
        self.assertEqual(result["buyTime"],end//1000)
        self.assertNotIn("BuyPrice",result)
        self.assertLessEqual(result["rsi"],30)
        self.assertGreater(result["rsi"],result["previousRSI"])

    def test_history_is_relative_to_cursor_not_evaluation_start(self):
        bars, start, end = fixture()
        expected = list(s.evaluate(bars, start, end))
        self.assertEqual(len(expected), 1)
        self.assertEqual(list(s.evaluate(bars, 20*D, end)), expected)

    def test_exact_twenty_day_cursor_history_required(self):
        bars, start, end = fixture()
        cursor = end - 5*M
        history_time = cursor - 20*D
        self.assertIn(history_time, {b.time for b in bars})
        self.assertEqual(len(list(s.evaluate(bars, start, end))), 1)
        # Keep indicator candles fixed to isolate the exact DB timestamp check.
        quarters = s.aggregate(bars, Q, 5*M)
        days = s.aggregate(bars, D, 5*M)
        missing_times = {history_time-j*Q for j in range(5)}
        missing = [b for b in bars if b.time not in missing_times]
        with patch.object(s, "aggregate", side_effect=[quarters, days]):
            self.assertEqual(list(s.evaluate(missing, start, end)), [])

    def test_under_twenty_days_never_buys(self):
        bars,start,end=fixture()
        self.assertEqual(list(s.evaluate([b for b in bars if b.time>=2*D],2*D,end)),[])
        self.assertEqual(list(s.evaluate(bars,0,19*D)),[])

    def test_incomplete_daily_or_signal_candle_blocks(self):
        bars,start,end=fixture()
        for t in (19*D, end-5*M):
            self.assertEqual(list(s.evaluate([b for b in bars if b.time!=t],start,end)),[])

    def test_future_data_does_not_change_signal(self):
        bars,start,end=fixture()
        future=[s.Bar(t,200,200,200,200,0) for t in range(end,22*D,5*M)]
        self.assertEqual(list(s.evaluate(bars,start,end)),list(s.evaluate(bars+future,start,end)))

    def test_four_conditions_and_boundaries(self):
        bars,start,end=fixture()
        for label,close,opening,current,expected in [
            ("recovered_price",98,97,20,1),("bullish",80,80,20,0),
            ("recovered_rsi",80,79,31,1),("rsi_direction",80,79,10,0),
            ("inclusive",97,96,30,1)]:
            with self.subTest(label=label):
                edited=bars[:-3]+[s.Bar(b.time,opening,max(opening,close),min(opening,close),close,0) for b in bars[-3:]]
                with patch.object(s,"wilder_rsi",side_effect=lambda b:[10.]*(len(b)-1)+[current]):
                    self.assertEqual(len(list(s.evaluate(edited,start,end))),expected)

    def test_resume_after_pruning_matches_uninterrupted(self):
        bars, start, end = fixture()
        bars += [s.Bar(t, 100, 100, 100, 100, 0) for t in range(end, 45*D, 5*M)]
        tail, _, _ = fixture()
        bars += [s.Bar(b.time+25*D, b.open, b.high, b.low, b.close, 0)
                 for b in tail if b.time >= 20*D]
        end = bars[-1].time + 5*M
        expected = list(s.evaluate(bars, start, end))
        self.assertGreaterEqual(len(expected), 2)
        state, actual, cursor = {}, [], start
        remaining = list(bars)
        while cursor < end:
            chunk_end = min((cursor//D+1)*D, end)
            batch = [b for b in remaining if b.time < chunk_end]
            actual.extend(s.evaluate(batch, cursor, chunk_end, rsi_state=state))
            # Simulate a new process restoring serialized state and a pruned DB.
            state = json.loads(json.dumps(state))
            remaining = [b for b in remaining if b.time >= chunk_end//D*D-20*D]
            cursor = chunk_end
        self.assertEqual(actual, expected)
        self.assertLess(len(remaining), len(bars))

    def test_cached_batches_match_signals_state_and_logs_with_gaps_and_restart(self):
        bars, start, end = fixture()
        bars += [s.Bar(t,100,100,100,100,0) for t in range(end,45*D,5*M)]
        tail, _, _ = fixture()
        bars += [s.Bar(b.time+25*D,b.open,b.high,b.low,b.close,0)
                 for b in tail if b.time >= 20*D]
        bars = [b for b in bars if b.time != 22*D+5*M and not 30*D <= b.time < 31*D]
        end = bars[-1].time+5*M
        boundaries = sorted(set([d*D for d in range(1,46)] +
                                [20*D+19*Q, 20*D+20*Q, end]))
        baseline, cached = {}, {}
        cache = s.RSIHistoryCache()
        cursor = read_from = 0
        total_signals = 0
        for right in boundaries:
            left = max(0,cursor//D*D-20*D)
            old_bars = [b for b in bars if left <= b.time < right]
            if cursor == 20*D+20*Q:
                cache = s.RSIHistoryCache()
                cached = json.loads(json.dumps(cached))
                read_from = left
            new_bars = [b for b in bars if read_from <= b.time < right]
            prepared = cache.prepare(new_bars,cursor,right)
            old_logs, new_logs = [], []
            expected = list(s.evaluate(old_bars,cursor,right,rsi_state=baseline,on_event=old_logs.append))
            actual = list(s.evaluate(new_bars,cursor,right,rsi_state=cached,
                                     on_event=new_logs.append,prepared=prepared))
            self.assertEqual(actual,expected)
            self.assertEqual(cached,baseline)
            self.assertEqual(new_logs,old_logs)
            self.assertLessEqual(len(cache.bars),21*288)
            total_signals += len(actual)
            cursor = read_from = right
        self.assertGreater(total_signals,0)

    def test_signal_at_first_quarter_after_resume(self):
        bars, start, end = fixture()
        boundary = end-Q
        state = {}
        before = list(s.evaluate([b for b in bars if b.time < boundary],
                                 start, boundary, rsi_state=state))
        restored = json.loads(json.dumps(state))
        after = list(s.evaluate(bars, boundary, end, rsi_state=restored))
        self.assertEqual(len(after), 1)
        self.assertEqual(before+after, list(s.evaluate(bars, start, end)))

    def timed_fixture(self, confirm_at, arm_close=97, arm_rsi=30):
        bars = [s.Bar(i*5*M,100,100,100,100,0) for i in range(20*D//(5*M))]
        for i in range(confirm_at+1):
            close = arm_close if i == 0 else 101
            opening = close-1 if i == confirm_at else close+1
            for j in range(3):
                bars.append(s.Bar(20*D+i*Q+j*5*M, opening, max(opening,close),
                                  min(opening,close), close, 0))
        def values(quarters, state=None):
            result = [arm_rsi if b.time == 20*D else
                      40 if b.time == 20*D+confirm_at*Q else 20
                      for b in quarters]
            if state is not None and result:
                state["value"] = result[-1]
            return result
        return bars, 20*D+(confirm_at+1)*Q, values

    def test_wait_window_boundaries_and_configurable_hours(self):
        for minutes in (60,120,180,240):
            for offset, expected in ((1,1),(minutes//15,1),(minutes//15+1,0)):
                with self.subTest(minutes=minutes, offset=offset):
                    bars,end,values = self.timed_fixture(offset)
                    with patch.object(s,"wilder_rsi",side_effect=values):
                        result = list(s.evaluate(bars,0,end,wait_minutes=minutes))
                    self.assertEqual(len(result),expected)
                    if result:
                        self.assertEqual(result[0]["buyTime"],end//1000)
                        self.assertEqual(result[0]["rsi"],40)
                        self.assertGreater(result[0]["close"],result[0]["bolLow"])

    def test_setup_required_and_no_same_bar_confirmation(self):
        for close, rsi in ((98,30),(97,31)):
            bars,end,values=self.timed_fixture(1,close,rsi)
            with patch.object(s,"wilder_rsi",side_effect=values):
                self.assertEqual(list(s.evaluate(bars,0,end)),[])
        bars,end,values=self.timed_fixture(0)
        with patch.object(s,"wilder_rsi",side_effect=values):
            self.assertEqual(list(s.evaluate(bars,0,end)),[])

    def test_pending_survives_serialized_resume(self):
        bars,end,values=self.timed_fixture(4)
        boundary=20*D+Q
        state={}
        with patch.object(s,"wilder_rsi",side_effect=values):
            self.assertEqual(list(s.evaluate([b for b in bars if b.time<boundary],
                                            0,boundary,rsi_state=state)),[])
            self.assertEqual(state["pending"]["expires_at"],boundary+60*M)
            restored=json.loads(json.dumps(state))
            result=list(s.evaluate(bars,boundary,end,rsi_state=restored))
            self.assertEqual(len(result),1)
            self.assertNotIn("pending",restored)

    def test_repeated_setup_does_not_extend_deadline(self):
        bars,end,values=self.timed_fixture(5)
        bars=[s.Bar(b.time,98,98,97,97,0) if 20*D+Q <= b.time < 20*D+5*Q
              else b for b in bars]
        with patch.object(s,"wilder_rsi",side_effect=values):
            self.assertEqual(list(s.evaluate(bars,0,end)),[])

    def test_wait_configuration_validation(self):
        for minutes in (0,-15,14,60.5,True):
            with self.assertRaises(ValueError):
                list(s.evaluate([],0,D,wait_minutes=minutes))
        with self.assertRaises(ValueError):
            list(s.evaluate([],0,D,rsi_state={"wait_minutes":60},wait_minutes=120))

    def test_rsi_resume_seed_and_gap(self):
        bars = [s.Bar(i*Q, 100+i%7, 110, 90, 100+i%7, 0) for i in range(40)]
        bars += [s.Bar((i+2)*Q, 100+i%5, 110, 90, 100+i%5, 0) for i in range(40, 65)]
        expected = s.wilder_rsi(bars)
        state, actual = {}, []
        for offset in range(0, len(bars), 3):
            actual += s.wilder_rsi(bars[offset:offset+3], state=state)
            state = json.loads(json.dumps(state))
        self.assertEqual(actual, expected)

    def test_rsi_seed_smoothing_and_gap(self):
        closes=[100]
        for i in range(14): closes.append(closes[-1]+(1 if i%2==0 else -1))
        closes.append(closes[-1]+2)
        bars=[s.Bar(i*Q,c,c,c,c,0) for i,c in enumerate(closes)]
        values=s.wilder_rsi(bars)
        self.assertEqual(values[14],50)
        self.assertAlmostEqual(values[15],100*8.5/15)
        bars[-1]=s.Bar(16*Q,102,102,102,102,0)
        self.assertIsNone(s.wilder_rsi(bars)[-1])

    def test_unclosed_and_bad_five_minute_data(self):
        row=dict(candleTime=0,open=1,high=2,low=1,close=2)
        self.assertEqual(s.five_minute_bars([row],5*M-1),[])
        self.assertEqual(len(s.five_minute_bars([row],5*M)),1)
        for data in ([row,row],[dict(row,candleTime=M)],[dict(row,close=float("nan"))]):
            with self.assertRaises(ValueError): s.five_minute_bars(data,10*M)

    def test_exact_entry_minute_only(self):
        fetch=Mock(return_value=[SimpleNamespace(openTime=Q,open="80.2")])
        self.assertEqual(s.entry_price(fetch,"TEST",Q,Q+M),80.2)
        fetch.assert_called_once_with(symbol="TEST",interval="1m",startTime=Q,endTime=Q+M-1,limit=1)
        for response in ([],[SimpleNamespace(openTime=Q+M,open=80)]):
            fetch.return_value=response
            self.assertIsNone(s.entry_price(fetch,"TEST",Q,Q+M))
        fetch.reset_mock()
        self.assertIsNone(s.entry_price(fetch,"TEST",Q,Q+M-1))
        fetch.assert_not_called()
        fetch.return_value=None
        with self.assertRaises(RuntimeError): s.entry_price(fetch,"TEST",Q,Q+M)

class RepositoryTests(unittest.TestCase):
    def test_interrupt_with_closed_db_preserves_original_exception(self):
        cursor = Mock()
        connection = SimpleNamespace(cursor=cursor, db=SimpleNamespace(open=False))
        repository = repo.RSICandleRepository(connection)
        with self.assertRaises(KeyboardInterrupt):
            try:
                raise KeyboardInterrupt()
            finally:
                repository.release_simulation_lock()
        cursor.execute.assert_not_called()

    def test_open_db_releases_simulation_lock(self):
        cursor = Mock()
        connection = SimpleNamespace(cursor=cursor, db=SimpleNamespace(open=True))
        repo.RSICandleRepository(connection).release_simulation_lock()
        cursor.execute.assert_called_once_with("SELECT RELEASE_LOCK('rsi_bb_15m_resume_v1')")

    def test_reads_existing_ohlc_without_volume(self):
        cursor=Mock()
        r=repo.RSICandleRepository(SimpleNamespace(cursor=cursor))
        r.read_five_minutes("TEST",0,D)
        sql,params=cursor.execute.call_args.args
        self.assertIn("FROM candleList",sql)
        self.assertNotIn("volume",sql)
        self.assertEqual(params,("TEST",0,D))

    def test_checkpoint_committed_before_scoped_deletion(self):
        cursor = Mock(rowcount=1)
        cursor.fetchone.return_value = {"lastPruneWeek": None}
        connection = Mock(cursor=cursor)
        events = []
        cursor.execute.side_effect = lambda sql, params: events.append((sql, params))
        connection.commit.side_effect = lambda: events.append(("COMMIT", None))
        r = repo.RSICandleRepository(connection)
        r.finish_chunk("TEST", 30*D+Q, {"value": 25})
        self.assertIn("INSERT INTO rsi_buy_progress", events[0][0])
        self.assertEqual(events[1][0], "COMMIT")
        self.assertIn("DELETE FROM candleList", events[3][0])
        self.assertIn("WHERE symbol=%s AND candleTime < %s", events[3][0])
        self.assertEqual(events[3][1], ("TEST", 5*D))
        self.assertEqual(events[4][0], "COMMIT")

    def test_weekly_cleanup_skips_same_week_after_restart(self):
        connection = Mock()
        connection.cursor.fetchone.return_value = {"lastPruneWeek": 25*D}
        r = repo.RSICandleRepository(connection)
        self.assertEqual(r.prune_processed("TEST",31*D),0)
        self.assertEqual(connection.cursor.execute.call_count,1)
        connection.commit.assert_not_called()
        connection.cursor.rowcount = 288*7
        r.prune_processed("TEST",32*D)
        deletes = [c for c in connection.cursor.execute.call_args_list if "DELETE" in c.args[0]]
        self.assertEqual(deletes[0].args[1],("TEST",12*D))
        self.assertEqual(connection.cursor.execute.call_args.args[1],(32*D,"TEST"))

    def test_failed_cleanup_does_not_mark_week_complete(self):
        connection = Mock()
        connection.cursor.fetchone.return_value = {"lastPruneWeek": None}
        connection.cursor.rowcount = 1
        connection.commit.side_effect = RuntimeError("delete commit failed")
        with self.assertRaises(RuntimeError):
            repo.RSICandleRepository(connection).prune_processed("TEST",32*D)
        self.assertFalse(any("UPDATE rsi_buy_progress" in c.args[0]
                             for c in connection.cursor.execute.call_args_list))

    def test_final_cleanup_requires_durable_completion_and_scopes_deletion(self):
        connection = Mock()
        r = repo.RSICandleRepository(connection)
        r.load_progress = Mock(return_value=(D, {}))
        with self.assertRaises(RuntimeError):
            r.delete_completed_source("TEST", 2*D)
        connection.cursor.execute.assert_not_called()
        r.load_progress.return_value = (2*D, {})
        connection.cursor.rowcount = 100
        self.assertEqual(r.delete_completed_source("TEST",2*D),100)
        self.assertEqual(connection.cursor.execute.call_args.args[1],("TEST",2*D))
        self.assertIn("symbol=%s AND candleTime < %s",connection.cursor.execute.call_args.args[0])
        connection.commit.assert_called_once()

    def test_checkpoint_commit_failure_never_deletes(self):
        connection = Mock()
        connection.commit.side_effect = RuntimeError("connection lost")
        r = repo.RSICandleRepository(connection)
        with self.assertRaises(RuntimeError):
            r.finish_chunk("TEST", 30*D, {})
        self.assertEqual(connection.cursor.execute.call_count, 1)
        self.assertNotIn("DELETE", connection.cursor.execute.call_args.args[0])

    def test_result_defaults_and_parameterization(self):
        fields=[("uid","int","auto_increment"),("symbol","varchar(32)",""),
                ("candleTime","bigint",""),("position","varchar(16)",""),
                ("BuyPrice","double",""),("buyTime","bigint",""),
                ("triggerTime","bigint",""),("triggerPrice","double",""),
                ("buyMode","varchar(16)",""),("sellTime","bigint",""),
                ("bolDataList","varchar(1000)",""),("buyTimeKST","varchar(19)","")]
        cursor=Mock(rowcount=1)
        cursor.fetchall.return_value=[dict(Field=n,Type=t,Extra=e) for n,t,e in fields]
        r=repo.RSICandleRepository(SimpleNamespace(cursor=cursor))
        signal,=s.evaluate(*fixture())
        signal["BuyPrice"]=80.2
        self.assertTrue(r.save_signal("TEST'COIN",signal,1))
        sql,params=cursor.execute.call_args.args
        self.assertNotIn("TEST'COIN",sql)
        data=dict(zip([n for n,t,e in fields if not e],params[:-3]))
        self.assertEqual(data["buyTimeKST"], "1970-01-21 14:15:00")
        self.assertEqual(data["sellTime"],0)
        self.assertEqual(data["bolDataList"],"")

class IntegrationTests(unittest.TestCase):
    def test_on_demand_api_and_repeated_run(self):
        tree=ast.parse((ROOT/"trading/TradingAgent.py").read_text(encoding="utf-8-sig"))
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="TradingAgent")
        cls.body=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in ("runBuyRSIBuyOperation","__rsiSourceWindows")]
        bars,start,end=fixture()
        saved=[]
        checkpoints={}
        failures={"checkpoint": False}
        class FakeRepository:
            def __init__(self,c): pass
            def source_windows(self,i): return [("TEST",start,end)]
            def acquire_simulation_lock(self): pass
            def release_simulation_lock(self): pass
            def prepare_progress(self): pass
            def delete_completed_source(self, symbol, end_time):
                assert checkpoints[symbol][0] >= end_time
                return 0
            def load_progress(self, symbol):
                return json.loads(json.dumps(checkpoints.get(symbol)))
            def prune_processed(self, symbol, next_time):
                cutoff = next_time // D * D - 20*D
                bars[:] = [b for b in bars if b.time >= cutoff]
                return 0
            def finish_chunk(self, symbol, next_time, state):
                if failures["checkpoint"] and next_time > 20*D:
                    failures["checkpoint"] = False
                    raise RuntimeError("stopped after buy commit")
                checkpoints[symbol] = json.loads(json.dumps([next_time, state]))
                return self.prune_processed(symbol, next_time)
            def read_five_minutes(self,symbol,left,right):
                return rows([b for b in bars if left <= b.time < right])
            def existing_buy_times(self,symbol): return {v["buyTime"] for v in saved}
            def save_signal(self,symbol,signal,index): saved.append(signal); return True
            def commit(self): pass
        fetch=Mock(return_value=[SimpleNamespace(openTime=end,open=80.2)])
        factory=Mock(return_value=SimpleNamespace(get_candlestick_data=fetch))
        env={"time":SimpleNamespace(time=lambda:(end+M)/1000,sleep=lambda _:None)}
        exec(compile(ast.Module(body=[cls],type_ignores=[]),"isolated","exec"),env)
        a=env["TradingAgent"]()
        for key,value in dict(rsiDbConnection=None,candleInterval=5,specificIndexFrom=0,specificIndexTo=0,log=SimpleNamespace(d=lambda *a:None)).items():
            setattr(a,"_TradingAgent__"+key,value)
        modules={"model":SimpleNamespace(),"trading":SimpleNamespace(),
                 "model.RSICandleRepository":SimpleNamespace(RSICandleRepository=FakeRepository),
                 "trading.RSIBuyStrategy":s,
                 "trading.BinanceFuturesClient":SimpleNamespace(BinanceFuturesClient=factory)}
        with patch.dict(sys.modules,modules):
            # A DB buy one hour earlier blocks entry before any network request.
            saved.append({"buyTime": end//1000-3600})
            self.assertEqual(a.runBuyRSIBuyOperation(target_symbol="TEST"), 0)
            self.assertEqual(len(saved), 1)
            factory.assert_not_called()
            fetch.assert_not_called()
            saved.clear()
            checkpoints.clear()
            fetch.return_value = []
            self.assertEqual(a.runBuyRSIBuyOperation(target_symbol="TEST"), 0)
            self.assertEqual(checkpoints["TEST"][0], 20*D)
            self.assertEqual(saved, [])
            fetch.reset_mock()
            factory.reset_mock()
            fetch.return_value = [SimpleNamespace(openTime=end, open=80.2)]
            failures["checkpoint"] = True
            with self.assertRaisesRegex(RuntimeError, "stopped after buy commit"):
                a.runBuyRSIBuyOperation(target_symbol="TEST")
            self.assertEqual(len(saved), 1)
            self.assertEqual(checkpoints["TEST"][0], 20*D)
            # Reuse the durable buy row, then advance the previously unfinished batch.
            self.assertEqual(a.runBuyRSIBuyOperation(target_symbol="TEST"),0)
            self.assertEqual(checkpoints["TEST"][0], end)
            self.assertEqual(a.runBuyRSIBuyOperation(target_symbol="TEST"),0)
            self.assertEqual(saved[0]["BuyPrice"],80.2)
            fetch.assert_called_once()
            factory.assert_called_once()
            saved.clear()
            checkpoints.clear()
            bars[:]=[b for b in bars if b.time>=2*D]
            factory.reset_mock()
            self.assertEqual(a.runBuyRSIBuyOperation(target_symbol="TEST"),0)
            factory.assert_not_called()

if __name__=="__main__": unittest.main()
