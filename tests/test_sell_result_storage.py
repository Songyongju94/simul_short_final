"""Offline schema compatibility and one-buy/two-leg persistence tests."""
import ast
from copy import deepcopy
import importlib.util
from pathlib import Path
import re
import sqlite3
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


schema = load("schema_for_storage", "model/SellResultSchema.py")
with patch.dict(sys.modules, {"model.SellResultSchema": schema}):
    r = load("repo_for_storage", "model/RSISellRepository.py")


class Cursor:
    """SQLite executes DML; only MySQL metadata/DDL syntax is adapted."""
    def __init__(self, db):
        self.db = db
        self.rows = []
        self.fail_delete = False

    def execute(self, sql, params=()):
        if sql.startswith("SHOW COLUMNS FROM "):
            table = sql.split()[-1]
            self.rows = [dict(Field=x[1], Type=x[2].lower(),
                              Extra="auto_increment" if x[1] == "uid" else "",
                              Null="NO", Default=x[4])
                         for x in self.db.execute(f"PRAGMA table_info({table})").fetchall()]
            return
        if "information_schema.TABLES" in sql:
            self.rows = [{"engine": "InnoDB"}]
            return
        if self.fail_delete and sql.startswith("DELETE"):
            raise RuntimeError("interrupted merge")
        sql = re.sub(r"\) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4", ")", sql)
        cursor = self.db.execute(sql.replace("%s", "?"), params)
        self.rows = [dict(row) for row in cursor.fetchall()] if cursor.description else []

    def fetchall(self):
        return deepcopy(self.rows)

    def fetchone(self):
        return deepcopy(self.rows[0]) if self.rows else None


class Connection:
    def __init__(self):
        self.raw = sqlite3.connect(":memory:")
        self.raw.row_factory = sqlite3.Row
        self.cursor = Cursor(self.raw)
        self.db = SimpleNamespace(begin=lambda: self.raw.execute("BEGIN"),
                                  rollback=self.raw.rollback, open=True)
    def commit(self):
        self.raw.commit()


BUY = dict(uid=42, symbol="TESTUSDT", buyTime=1701043200,
           BuyPrice=100, high=101, low=98, coinIndex=1)
STATE = dict(version=2, buy_price=100, balance=1000, stop_price=95)


def event(stage, price, profit, time=1701043260):
    return dict(stage=stage, price=price, quantity=5, profit=profit, time=time, upper=110)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.connection = Connection()
        self.repo = r.RSISellRepository(self.connection)
        sample = r.summary_values(BUY, STATE, [event("STOP", 95, -25)])
        sample["bolHigh"] = 0
        extras = {name for name, kind, default in schema.EXTRA_COLUMNS}
        base = ["uid INTEGER PRIMARY KEY AUTOINCREMENT"]
        base += [f"`{name}` " + ("TEXT" if isinstance(value, str) else "DOUBLE")
                 for name, value in sample.items() if name not in extras]
        self.connection.raw.execute("CREATE TABLE candleSellResultList (" + ",".join(base) + ")")
        schema.ensure_sell_columns(self.connection)
        self.connection.cursor.execute("SHOW COLUMNS FROM candleSellResultList")
        self.repo.columns = self.connection.cursor.fetchall()
        self.connection.raw.execute("""CREATE TABLE candleBuyResultList (
            uid INTEGER PRIMARY KEY, symbol TEXT, buyTime BIGINT, BuyPrice DOUBLE,
            high DOUBLE, low DOUBLE, coinIndex INTEGER)""")
        self.connection.raw.execute("INSERT INTO candleBuyResultList VALUES (?,?,?,?,?,?,?)",
                                    tuple(BUY.values()))
        self.connection.commit()

    def row(self):
        return dict(self.connection.raw.execute("SELECT * FROM candleSellResultList").fetchone())

    def test_one_row_two_legs_sum_and_buy_join(self):
        first = event("STOP", 95, -25)
        second = event("TP5", 108, 40, 1701043560)
        self.assertTrue(self.repo.save_event(BUY, STATE, first))
        self.assertEqual(self.row()["sell2Time"], "")
        self.assertEqual(self.row()["profitPrice"], -25)
        self.assertTrue(self.repo.save_event(BUY, STATE, second))
        row = self.row()
        self.assertEqual(self.connection.raw.execute("SELECT COUNT(*) FROM candleSellResultList").fetchone()[0], 1)
        self.assertEqual(row["buyUid"], 42)
        self.assertEqual((row["sell1Price"], row["sell2Price"]), (95, 108))
        self.assertEqual(row["profitPrice"], 15)
        self.assertEqual(row["quantity"], 10)
        self.assertEqual(row["sellPrice"], 101.5)
        self.assertEqual(row["sell1Time"], r.kst(first["time"]))
        self.assertEqual(row["sell2Time"], r.kst(second["time"]))
        joined = self.connection.raw.execute("""SELECT s.buyUid FROM candleBuyResultList b
            JOIN candleSellResultList s ON s.buyUid=b.uid""").fetchall()
        self.assertEqual(len(joined), 1)

    def test_restart_after_first_commit_and_after_second_commit(self):
        events = [event("TP5", 105, 25), event("STOP", 95, -25, 1701043560)]
        self.repo.save_event(BUY, STATE, events[0])
        restarted = r.RSISellRepository(self.connection)
        restarted.columns = self.repo.columns
        self.assertFalse(restarted.save_event(BUY, STATE, events[0]))
        self.assertTrue(restarted.save_event(BUY, STATE, events[1]))
        for e in events:
            self.assertFalse(restarted.save_event(BUY, STATE, e))
        self.assertEqual(self.row()["profitPrice"], 0)
        with self.assertRaisesRegex(ValueError, "Replayed sell"):
            restarted.save_event(BUY, STATE, {**events[0], "price": 106})

    def test_same_tick_order_keeps_both_profit_legs(self):
        self.repo.save_event(BUY, STATE, event("TP5", 110, 50))
        self.repo.save_event(BUY, STATE, event("BB4H", 110, 50))
        row = self.row()
        self.assertEqual((row["sell1Reason"], row["sell2Reason"]), ("TP5", "BB4H"))
        self.assertEqual(row["profitPrice"], 100)

    def legacy(self):
        for e in (event("STOP", 95, -25), event("TP5", 108, 40, 1701043560)):
            values = r.summary_values(BUY, STATE, [e])
            values.update(buyUid=0, conditions="RSI19v2:42:"+e["stage"],
                          sellPrice=e["price"], profitPrice=e["profit"], bolHigh=0)
            values.update({name: default for name, kind, default in schema.EXTRA_COLUMNS})
            self.repo._insert_result(values)
        self.connection.commit()

    def test_legacy_merge_archives_originals_and_is_repeatable(self):
        self.legacy()
        self.repo._merge_old_split_rows()
        row = self.row()
        self.assertEqual((row["sell1Price"], row["sell2Price"]), (95, 108))
        self.assertEqual(row["profitPrice"], 15)
        self.assertEqual(self.connection.raw.execute("SELECT COUNT(*) FROM rsi_sell_split_archive").fetchone()[0], 2)
        self.repo._merge_old_split_rows()
        self.assertEqual(self.connection.raw.execute("SELECT COUNT(*) FROM candleSellResultList").fetchone()[0], 1)

    def test_interrupted_merge_rolls_back_then_retries(self):
        self.legacy()
        self.connection.cursor.fail_delete = True
        with self.assertRaisesRegex(RuntimeError, "interrupted"):
            self.repo._merge_old_split_rows()
        self.assertEqual(self.connection.raw.execute("SELECT COUNT(*) FROM candleSellResultList WHERE buyUid=0").fetchone()[0], 2)
        self.assertEqual(self.connection.raw.execute("SELECT COUNT(*) FROM rsi_sell_split_archive").fetchone()[0], 0)
        self.connection.cursor.fail_delete = False
        self.repo._merge_old_split_rows()
        self.assertEqual(self.row()["profitPrice"], 15)

    def test_schema_upgrade_can_run_twice_without_duplicate_columns(self):
        schema.ensure_sell_columns(self.connection)
        self.connection.cursor.execute("SHOW COLUMNS FROM candleSellResultList")
        names = [c["Field"] for c in self.connection.cursor.fetchall()]
        self.assertEqual(names.count("buyUid"), 1)
        self.assertEqual(names[-13:], [name for name, kind, default in schema.EXTRA_COLUMNS])


class Model:
    Int, Long, String, Float = "int", "long", "string", "float"
    def __init__(self, connection, table, fields, debug):
        self.fields = fields
    def add(self, data, columns=None):
        self.saved, self.columns = data, columns
        return True
    def update(self, uid, data):
        self.updated = data
        return True


class Field:
    AutoIncrement = "auto"
    def __init__(self, key, *args):
        self.key = key


class CompatibilityTests(unittest.TestCase):
    def test_old_64_field_writer_and_update_keep_positions(self):
        tree = ast.parse((ROOT/"model/CandleSellResultRepository.py").read_bytes())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
        env = dict(DBModel=Model, ApiHandler=type("Api", (), {}), DBField=Field,
                   DBFieldUID=lambda *args: Field("uid"), Log=Mock,
                   EXTRA_COLUMNS=schema.EXTRA_COLUMNS, ensure_sell_columns=Mock(),
                   with_sell_columns=schema.with_sell_columns)
        exec(compile(ast.Module(body=[cls], type_ignores=[]), "isolated", "exec"), env)
        repo = env["CandleSellResultRepository"](Mock(), "", 0)
        original = list(range(64))
        repo.addCandleSellResult(original)
        self.assertEqual(len(repo.saved), 77)
        self.assertEqual(repo.saved[:64], original)
        self.assertEqual(len(original), 64)
        self.assertEqual(repo.fields[13].key, "profitPrice")
        self.assertEqual(repo.fields[63].key, "h12HighPer")
        self.assertIn("`sell2ProfitPrice`", repo.columns)
        repo.update(1, original)
        self.assertEqual(len(repo.updated), 64)  # No metadata overwrite by legacy updates.
        extended = original + [default for name, kind, default in schema.EXTRA_COLUMNS]
        repo.add(extended)
        self.assertEqual(repo.saved, extended)
        with self.assertRaises(ValueError):
            repo.add([0]*65)


if __name__ == "__main__":
    unittest.main()
