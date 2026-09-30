"""Offline schema/serialization checks without application imports or DB access."""
import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]

class Model:
    Int = Long = String = Float = "test"
    def __init__(self, connection, table, fields, debug):
        self.fields = fields
    def add(self, data):
        self.saved = data
        return True
    def update(self, uid, data):
        self.saved = data
        return True

class Field:
    AutoIncrement = "auto"
    def __init__(self, key, *args):
        self.key = key

class BuyTimeTests(unittest.TestCase):
    def repository(self, mode, exists=False):
        tree = ast.parse((ROOT/"model/CandleBuyResultRepository.py").read_bytes())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
        env = dict(DBModel=Model, ApiHandler=type("Api", (), {}), DBField=Field,
                   DBFieldUID=lambda *args: Field("uid"), Log=Mock,
                   datetime=datetime, timedelta=timedelta, timezone=timezone)
        exec(compile(ast.Module(body=[cls], type_ignores=[]), "isolated", "exec"), env)
        connection = Mock()
        connection.cursor.fetchall.return_value = [{"Field": name, "Type": "varchar(19)"} for name in ("buyTimeKST", "recentLow", "recentLowTime")] if exists else []
        connection.cursor.fetchone.return_value = None
        return env["CandleBuyResultRepository"](connection, mode), connection

    def test_both_schemas_append_and_preserve_original_data(self):
        for mode, old_count in ((0,27),(1,29)):
            repository, connection = self.repository(mode)
            self.assertEqual(repository.fields[-3].key, "buyTimeKST")
            self.assertEqual(repository.fields[14].key, "buyTime")
            data = [0]*old_count
            data[14] = 1701043200
            repository.addCandleBuyResult(data)
            self.assertEqual(repository.saved[-3], "2023-11-27 09:00:00")
            self.assertEqual(repository.saved[:-3], data)
            self.assertEqual(len(data), old_count)
            self.assertEqual(repository.saved[-2:], [0,""])
            sql = [c.args[0] for c in connection.cursor.execute.call_args_list]
            self.assertTrue(any("ADD COLUMN buyTimeKST" in q for q in sql))
            self.assertTrue(any("INTERVAL 9 HOUR" in q for q in sql))

    def test_new_low_fields_and_legacy_update_preserve_saved_low(self):
        for mode, base in ((0,27),(1,29)):
            repository, connection = self.repository(mode, True)
            self.assertEqual([f.key for f in repository.fields[-2:]], ["recentLow","recentLowTime"])
            data=[0]*base+["",95.5,1701043200]
            data[14]=1701043260
            repository.addCandleBuyResult(data)
            self.assertEqual(repository.saved[-2:],[95.5,"2023-11-27 09:00:00"])
            connection.cursor.fetchone.return_value={"recentLow":95.5,"recentLowTime":"2023-11-27 09:00:00"}
            repository.update(1,data[:base])
            self.assertEqual(repository.saved[-2:],[95.5,"2023-11-27 09:00:00"])

    def test_trade_adapter_legacy_and_extended_schemas(self):
        tree=ast.parse((ROOT/"trading/TradeInfoAdapter.py").read_bytes())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef))
        env={"TradeInfo":lambda data: data}
        exec(compile(ast.Module(body=[cls],type_ignores=[]),"isolated","exec"),env)
        for base in (27,29):
            original=[0]*base
            original[-3:]=[2,3,"TEST"]
            for data in (original, original+["KST"], original+["KST",95.5,1701043200]):
                result=env["TradeInfoAdapter"].createFromBinance(data)
                self.assertEqual(result["buyMode"],"TEST")
                self.assertEqual(result["addBuyCount"],2)
                self.assertEqual(result["addMBuyCount"],3)
                self.assertEqual(result["recentLow"],95.5 if len(data)==base+3 else 0)

    def test_epoch_low_time_schema_migration_is_guarded(self):
        repository, connection = self.repository(0, True)
        connection.cursor.reset_mock()
        connection.cursor.fetchall.return_value = [
            {"Field":"buyTimeKST","Type":"varchar(19)"},
            {"Field":"recentLow","Type":"double"},
            {"Field":"recentLowTime","Type":"bigint"}]
        repository._ensure_buy_time_kst()
        sql=[c.args[0] for c in connection.cursor.execute.call_args_list]
        self.assertTrue(any("MODIFY COLUMN recentLowTime VARCHAR(19)" in q for q in sql))
        conversion=next(q for q in sql if "SET recentLowTime" in q)
        self.assertIn("REGEXP '^[0-9]+$'",conversion)
        self.assertIn("INTERVAL 9 HOUR",conversion)

    def test_existing_column_not_added_again(self):
        repository, connection = self.repository(0, True)
        self.assertFalse(any("ALTER TABLE" in c.args[0]
                             for c in connection.cursor.execute.call_args_list))

    def test_update_recalculates_kst_and_midnight_rollover(self):
        repository, _ = self.repository(0, True)
        data = [0]*27 + ["stale"]
        data[14] = int(datetime(2026,9,30,16,30,tzinfo=timezone.utc).timestamp())
        repository.update(1, data)
        self.assertEqual(repository.saved[-3], "2026-10-01 01:30:00")

if __name__ == "__main__":
    unittest.main()
