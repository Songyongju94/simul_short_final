"""Offline ingestion tests: fake HTTP/DB only, no service or config imports."""
import hashlib
import importlib.util
import io
from pathlib import Path
import threading
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


c = load('collector', 'trading/CandleCollector.py')
d = load('ingestion', 'model/CandleIngestion.py')
STEP = 300000


def row(t):
    return [t, '100', '102', '99', '101', '0', t + STEP - 1, 0, 0, 0, 0, 0]


class MemoryRepository:
    def __init__(self):
        self.values = {}
        self.owner = threading.get_ident()
        self.released = False

    def acquire_collection(self):
        pass

    def prepare_collection(self, minutes):
        assert minutes == 5

    def release_collection(self):
        self.released = True

    def candle_times(self, symbol, left, right):
        assert self.owner == threading.get_ident()
        return {t for sym, t in self.values if sym == symbol and left <= t < right}

    def add_candles(self, symbol, values):
        assert self.owner == threading.get_ident()
        for value in values:
            self.values[symbol, value[0]] = value


class CollectionTests(unittest.TestCase):
    def test_cache_reuse_corruption_and_expiry(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as archive:
            archive.writestr('candles.csv', '0,100,102,99,101\n')
        content = data.getvalue()
        with TemporaryDirectory() as directory:
            source = c.PublicCandles(cache_dir=directory)
            source.request = Mock(side_effect=lambda url, **kw: (
                SimpleNamespace(text=hashlib.sha256(content).hexdigest())
                if url.endswith('.CHECKSUM') else SimpleNamespace(content=content)))
            expected = source.archive('GOOD', '5m', '1970-01')
            self.assertEqual(source.request.call_count, 2)
            self.assertEqual(source.archive('GOOD', '5m', '1970-01'), expected)
            self.assertEqual(source.request.call_count, 2)
            cached = Path(directory) / 'monthly/GOOD/5m/GOOD-5m-1970-01.zip'
            cached.write_bytes(b'broken')
            self.assertEqual(source.archive('GOOD', '5m', '1970-01'), expected)
            self.assertEqual(source.request.call_count, 4)
            source.cache_ttl = 0
            self.assertEqual(source.archive('GOOD', '5m', '1970-01'), expected)
            self.assertEqual(source.request.call_count, 6)
            self.assertEqual(len(list(cached.parent.iterdir())), 2)

    def test_daily_archive_then_rest_and_no_current_day_archive(self):
        source = self.source()
        day = 86400000
        source.archive = Mock(return_value=[row(t) for t in range(STEP, day, STEP)])
        values, missing, _ = source.fetch('GOOD', 5, 0, day + STEP,
                                         '1970-01', 31 * day, set(), day + STEP)
        source.archive.assert_called_once_with('GOOD', '5m', '1970-01-01', kind='daily')
        self.assertEqual((len(values), missing), (289, 0))
        self.assertEqual(source.request.call_count, 2)
        # A not-yet-published daily file falls back to REST without negative caching.
        source = self.source()
        source.archive = Mock(return_value=[])
        values, missing, _ = source.fetch('GOOD', 5, 0, day, '1970-01', 31 * day,
                                         set(), day + STEP)
        self.assertEqual((len(values), missing), (288, 0))
        self.assertEqual(source.request.call_count, 1)

    def test_fast_worker_starts_next_symbol_before_slow_worker_finishes(self):
        repo, source = MemoryRepository(), self.source()
        third_started = threading.Event()
        def fetch(symbol, *args):
            if symbol == 'SLOW':
                if not third_started.wait(3):
                    raise AssertionError('Slow first task blocked worker refill')
            elif symbol == 'THIRD':
                third_started.set()
            return [c.candle(row(0), 0, STEP, STEP)], 0, 0
        source.fetch = Mock(side_effect=fetch)
        with patch.object(c.time, 'time', return_value=STEP / 1000):
            self.assertEqual(c.collect(repo, ['SLOW', 'FAST', 'THIRD'], 5, 0, STEP,
                                       Mock(), source, workers=2), 3)
        self.assertTrue(third_started.is_set())
        self.assertEqual(len(repo.values), 3)

    def test_rate_limit_retry_uses_shared_cooldown_and_header_usage(self):
        source = c.PublicCandles(cache_dir=None)
        source.limiter = Mock()
        limited = c.requests.Response()
        limited.status_code = 429
        limited.headers['Retry-After'] = '120'
        limited.headers['X-MBX-USED-WEIGHT-1M'] = '2400'
        ok = c.requests.Response()
        ok.status_code = 200
        session = Mock()
        session.get.side_effect = [limited, ok]
        source.local.session = session
        with patch.object(c.time, 'sleep'):
            self.assertIs(source.request('https://example.invalid', weight=2), ok)
        source.limiter.defer.assert_called_once_with(120)
        self.assertEqual(source.limiter.acquire.call_count, 2)
        self.assertEqual(source.limiter.observe.call_count, 2)

    def test_archive_404_and_bad_symbol_are_not_retried(self):
        source = c.PublicCandles(cache_dir=None)
        source.limiter = Mock()
        source.local.session = Mock()
        response = c.requests.Response()
        response.status_code = 404
        source.local.session.get.return_value = response
        self.assertIsNone(source.request('https://example.invalid', optional=True))
        response.status_code = 400
        response._content = b'{"code": -1121, "msg": "Invalid symbol."}'
        with self.assertRaises(c.InvalidSymbol):
            source.request('https://example.invalid', params={'symbol': 'BAD'}, weight=2)
        self.assertEqual(source.local.session.get.call_count, 2)

    def source(self):
        source = c.PublicCandles(cache_dir=None)
        source.exchange = Mock(return_value={'GOOD': {'onboardDate': 0}})
        source.request = Mock(side_effect=lambda url, **kw: SimpleNamespace(
            json=lambda: [row(t) for t in range(kw['params']['startTime'],
                                               kw['params']['endTime'] + 1, STEP)]))
        return source

    def test_internal_holes_resume_and_no_db_in_workers(self):
        repo, source = MemoryRepository(), self.source()
        repo.values['GOOD', STEP] = c.candle(row(STEP), 0, 3 * STEP, STEP)
        with patch.object(c.time, 'time', return_value=3 * STEP / 1000):
            self.assertEqual(c.collect(repo, ['GOOD'], 5, 0, 4 * STEP, Mock(), source), 2)
            self.assertEqual(len(repo.values), 3)
            self.assertEqual(c.collect(repo, ['GOOD'], 5, 0, 4 * STEP, Mock(), source), 0)
        self.assertEqual(source.request.call_count, 2)
        self.assertTrue(repo.released)

    def test_api_pages_are_bounded_and_do_not_drop_late_first_candle(self):
        source = self.source()
        source.request = Mock(return_value=SimpleNamespace(json=lambda: [row(STEP)]))
        values, missing, _ = source.fetch('GOOD', 5, 0, 2 * STEP, '1970-01', 10**15, set(), 0)
        self.assertEqual([v[0] for v in values], [STEP])
        self.assertEqual(missing, 1)
        self.assertEqual(source.request.call_args.kwargs['params']['endTime'], 2 * STEP - 1)
        source = self.source()
        values, missing, _ = source.fetch('GOOD', 5, 0, 1000 * STEP, '', 10**15, set(), 0)
        self.assertEqual(len(values), 1000)
        self.assertEqual(missing, 0)
        self.assertEqual(source.request.call_count, 3)

    def test_onboard_and_delivery_boundaries(self):
        repo, source = MemoryRepository(), self.source()
        source.exchange.return_value = {'GOOD': {'onboardDate': STEP, 'deliveryDate': 3 * STEP}}
        with patch.object(c.time, 'time', return_value=5 * STEP / 1000):
            c.collect(repo, ['GOOD'], 5, 0, 5 * STEP, Mock(), source)
        self.assertEqual(set(repo.values), {('GOOD', STEP), ('GOOD', 2 * STEP)})

    def test_bad_symbol_skips_while_other_symbols_finish(self):
        repo, source, log = MemoryRepository(), self.source(), Mock()
        original = source.fetch
        source.fetch = Mock(side_effect=lambda symbol, *args: (
            original(symbol, *args) if symbol == 'GOOD' else self.bad()))
        with patch.object(c.time, 'time', return_value=STEP / 1000):
            c.collect(repo, ['BAD', 'GOOD'], 5, 0, STEP, log, source)
        self.assertEqual(set(repo.values), {('GOOD', 0)})
        self.assertTrue(any('BAD_SYMBOL' in str(call) for call in log.call_args_list))

    @staticmethod
    def bad():
        raise c.InvalidSymbol('BAD')

    def test_missing_data_is_saved_but_never_reported_as_complete(self):
        repo, source, log = MemoryRepository(), self.source(), Mock()
        source.request = Mock(return_value=SimpleNamespace(json=lambda: [row(STEP)]))
        with patch.object(c.time, 'time', return_value=2 * STEP / 1000):
            with self.assertRaisesRegex(RuntimeError, '1 missing'):
                c.collect(repo, ['GOOD'], 5, 0, 2 * STEP, log, source)
        self.assertEqual(set(repo.values), {('GOOD', STEP)})
        self.assertTrue(repo.released)
        self.assertFalse(any('CANDLE complete' in str(call) for call in log.call_args_list))

    def test_http_failure_propagates_and_unlocks(self):
        repo, source = MemoryRepository(), self.source()
        source.fetch = Mock(side_effect=RuntimeError('HTTP failed'))
        with patch.object(c.time, 'time', return_value=STEP / 1000):
            with self.assertRaisesRegex(RuntimeError, 'HTTP failed'):
                c.collect(repo, ['GOOD'], 5, 0, STEP, Mock(), source)
        self.assertTrue(repo.released)

    def test_archive_checksum_header_and_rest_gap_fill(self):
        source = self.source()
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as archive:
            archive.writestr('candles.csv', 'open_time,open,high,low,close\n0,100,102,99,101\n')
        content = data.getvalue()
        source.request = Mock(side_effect=[SimpleNamespace(content=content),
            SimpleNamespace(text=hashlib.sha256(content).hexdigest() + ' file.zip')])
        self.assertEqual(source.archive('GOOD', '5m', '1970-01')[0][0], '0')
        source.request = Mock(side_effect=[SimpleNamespace(content=content), SimpleNamespace(text='bad file')])
        with self.assertRaisesRegex(ValueError, 'checksum'):
            source.archive('GOOD', '5m', '1970-01')
        source = self.source()
        source.archive = Mock(return_value=[row(t) for t in range(STEP, 1440 * STEP, STEP)])
        values, missing, _ = source.fetch('GOOD', 5, 0, 1440 * STEP, '1970-01', 0, set(), 1)
        self.assertEqual((len(values), missing), (1440, 0))
        self.assertEqual(source.request.call_count, 1)
        self.assertEqual(source.request.call_args.kwargs['params']['endTime'], STEP - 1)

    def test_invalid_ohlc_and_month_boundaries(self):
        with self.assertRaises(ValueError):
            c.candle([0, 100, 90, 99, 101], 0, STEP, STEP)
        parts = list(c.months(0, 40 * 86400000))
        self.assertEqual([p[2] for p in parts], ['1970-01', '1970-02'])
        self.assertEqual(parts[0][1], parts[1][0])


class DatabaseTests(unittest.TestCase):
    def repo(self):
        repo = d.CandleIngestion()
        repo.dbConnection = Mock()
        repo.acquire_collection = Mock()
        repo.release_collection = Mock()
        return repo

    def test_bulk_chunks_and_rollback(self):
        repo = self.repo()
        values = [c.candle(row(t), 0, 1001 * STEP, STEP) for t in range(0, 1001 * STEP, STEP)]
        repo.add_candles('GOOD', values)
        self.assertEqual(repo.dbConnection.cursor.executemany.call_count, 2)
        self.assertEqual(repo.dbConnection.commit.call_count, 2)
        repo.dbConnection.cursor.executemany.side_effect = RuntimeError('disk full')
        with self.assertRaises(RuntimeError):
            repo.add_candles('GOOD', values)
        repo.dbConnection.db.rollback.assert_called_once()

    def test_backup_swap_only_after_copy_and_unchanged_skip(self):
        repo = self.repo()
        repo.dbConnection.cursor.fetchone.side_effect = [dict(revision=2, backup_revision=1), {'exists': 1}]
        self.assertTrue(repo.backup())
        statements = [call.args[0] for call in repo.dbConnection.cursor.execute.call_args_list]
        self.assertLess(next(i for i, v in enumerate(statements) if v.startswith('INSERT INTO')),
                        next(i for i, v in enumerate(statements) if v.startswith('RENAME TABLE')))
        repo = self.repo()
        repo.dbConnection.cursor.fetchone.side_effect = [dict(revision=2, backup_revision=2),
                                                         {'exists': 1}, dict(n=2, last_uid=5), dict(n=2, last_uid=5)]
        self.assertFalse(repo.backup())
        self.assertFalse(any('DROP' in call.args[0] for call in repo.dbConnection.cursor.execute.call_args_list))

    def test_failed_backup_keeps_original(self):
        repo = self.repo()
        repo.dbConnection.cursor.fetchone.side_effect = [dict(revision=2, backup_revision=1), {'exists': 1}]
        def execute(sql, *args):
            if sql.startswith('INSERT INTO candleList_backup_build'):
                raise RuntimeError('disk full')
        repo.dbConnection.cursor.execute.side_effect = execute
        with self.assertRaises(RuntimeError):
            repo.backup()
        self.assertFalse(any('RENAME' in call.args[0] for call in repo.dbConnection.cursor.execute.call_args_list))
        repo.release_collection.assert_called_once()

    def test_interval_mismatch_and_existing_duplicates_fail_without_deleting(self):
        repo = self.repo()
        repo.dbConnection.cursor.fetchone.return_value = {'interval_minutes': 15}
        with self.assertRaisesRegex(ValueError, 'another interval'):
            repo.prepare_collection(5)
        repo = self.repo()
        repo.dbConnection.cursor.fetchone.side_effect = [{'interval_minutes': 5}, None, {'symbol': 'GOOD'}]
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            repo.prepare_collection(5)
        self.assertFalse(any('DELETE' in call.args[0] or 'TRUNCATE' in call.args[0]
                             for call in repo.dbConnection.cursor.execute.call_args_list))


if __name__ == '__main__':
    unittest.main()
