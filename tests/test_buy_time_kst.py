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
        connection.cursor.fetchall.return_value = [{"Field": "buyTimeKST"}] if exists else []
        return env["CandleBuyResultRepository"](connection, mode), connection

    def test_both_schemas_append_and_preserve_original_data(self):
        for mode, old_count in ((0,27),(1,29)):
            repository, connection = self.repository(mode)
            self.assertEqual(repository.fields[-1].key, "buyTimeKST")
            self.assertEqual(repository.fields[14].key, "buyTime")
            data = [0]*old_count
            data[14] = 1701043200
            repository.addCandleBuyResult(data)
            self.assertEqual(repository.saved[-1], "2023-11-27 09:00:00")
            self.assertEqual(repository.saved[:-1], data)
            self.assertEqual(len(data), old_count)
            sql = [c.args[0] for c in connection.cursor.execute.call_args_list]
            self.assertTrue(any("ADD COLUMN buyTimeKST" in q for q in sql))
            self.assertTrue(any("INTERVAL 9 HOUR" in q for q in sql))

    def test_existing_column_not_added_again(self):
        repository, connection = self.repository(0, True)
        self.assertFalse(any("ALTER TABLE" in c.args[0]
                             for c in connection.cursor.execute.call_args_list))

    def test_update_recalculates_kst_and_midnight_rollover(self):
        repository, _ = self.repository(0, True)
        data = [0]*27 + ["stale"]
        data[14] = int(datetime(2026,9,30,16,30,tzinfo=timezone.utc).timestamp())
        repository.update(1, data)
        self.assertEqual(repository.saved[-1], "2026-10-01 01:30:00")

if __name__ == "__main__":
    unittest.main()
