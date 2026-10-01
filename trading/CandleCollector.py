"""Public-data candle ingestion. Workers do HTTP only; the caller owns the DB."""
import csv
import hashlib
import io
import re
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path
from tempfile import NamedTemporaryFile

import requests


INTERVALS = {1: '1m', 3: '3m', 5: '5m', 15: '15m', 30: '30m', 60: '1h', 240: '4h'}


class InvalidSymbol(ValueError):
    pass


def gaps(start, end, step, present):
    """Half-open missing ranges, including holes before the latest stored candle."""
    left = None
    for stamp in range(start, end, step):
        if stamp not in present:
            if left is None:
                left = stamp
        elif left is not None:
            yield left, stamp
            left = None
    if left is not None:
        yield left, end


def months(start, end):
    while start < end:
        dt = datetime.fromtimestamp(start / 1000, timezone.utc)
        following = datetime(dt.year + (dt.month == 12), dt.month % 12 + 1, 1,
                             tzinfo=timezone.utc)
        right = min(end, int(following.timestamp() * 1000))
        yield start, right, dt.strftime('%Y-%m'), int(following.timestamp() * 1000)
        start = right


def candle(row, start, end, step):
    stamp = int(row[0])
    if not start <= stamp < end:
        return None
    opening, high, low, close = map(float, row[1:5])
    if stamp % step or not all(isfinite(v) and v > 0 for v in (opening, high, low, close)):
        raise ValueError('Invalid candle timestamp or price')
    if not low <= min(opening, close) <= max(opening, close) <= high:
        raise ValueError('Invalid candle OHLC')
    return stamp, close, high, low, opening, close


class WeightLimiter:
    """Shared pacing plus server-observed IP usage; reserve half of the quota."""
    def __init__(self):
        self.lock = threading.Lock()
        self.budget = 1200
        self.next_request = 0.0

    def acquire(self, weight):
        while True:
            with self.lock:
                delay = self.next_request - time.monotonic()
                if delay <= 0:
                    self.next_request = time.monotonic() + weight * 60 / self.budget
                    return
            time.sleep(min(delay, 1))

    def observe(self, headers):
        used = int(headers.get('X-MBX-USED-WEIGHT-1M', 0))
        if used >= self.budget:
            self.defer(60 - time.time() % 60 + 1)

    def defer(self, seconds):
        with self.lock:
            self.next_request = max(self.next_request, time.monotonic() + seconds)


class PublicCandles:
    def __init__(self, cache_dir=Path(__file__).resolve().parents[1] / '.candle-cache', cache_ttl=7 * 86400):
        self.cache_dir = Path(cache_dir) if cache_dir is not None else None
        self.cache_ttl = cache_ttl
        self.local = threading.local()
        self.limiter = WeightLimiter()
        self.sessions = []
        self.lock = threading.Lock()

    def close(self):
        for session in self.sessions:
            session.close()

    def request(self, url, *, params=None, weight=0, optional=False):
        if not hasattr(self.local, 'session'):
            self.local.session = requests.Session()
            with self.lock:
                self.sessions.append(self.local.session)
        for attempt in range(4):
            self.limiter.acquire(weight)
            try:
                response = self.local.session.get(url, params=params, timeout=(10, 60))
                if weight:
                    self.limiter.observe(response.headers)
                if response.status_code == 404 and optional:
                    return None
                if response.status_code == 400 and response.json().get('code') == -1121:
                    raise InvalidSymbol(params['symbol'])
                if response.status_code in (418, 429):
                    self.limiter.defer(max(60, float(response.headers.get('Retry-After', 60))))
                    response.raise_for_status()
                response.raise_for_status()
                return response
            except (requests.Timeout, requests.ConnectionError):
                if attempt == 3:
                    raise
            except requests.HTTPError as exc:
                if attempt == 3 or (exc.response.status_code < 500
                                    and exc.response.status_code not in (418, 429)):
                    raise
            time.sleep(2 ** attempt)

    def exchange(self):
        data = self.request('https://fapi.binance.com/fapi/v1/exchangeInfo', weight=1).json()
        for limit in data.get('rateLimits', []):
            if (limit['rateLimitType'] == 'REQUEST_WEIGHT' and limit['interval'] == 'MINUTE'
                    and limit['intervalNum'] == 1):
                self.limiter.budget = max(1, int(limit['limit']) // 2)
        return {row['symbol']: row for row in data['symbols']}

    @staticmethod
    def _archive_rows(content):
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            names = [name for name in archive.namelist() if name.endswith('.csv')]
            if len(names) != 1:
                raise ValueError('Expected one archive CSV')
            with archive.open(names[0]) as source:
                rows = csv.reader(io.TextIOWrapper(source, encoding='utf-8-sig'))
                return [row for row in rows if row and row[0] not in ('open_time', 'openTime')]

    @staticmethod
    def _atomic_write(path, content):
        temporary = None
        try:
            with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(content)
            temporary.replace(path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def archive(self, symbol, interval, period, kind='monthly'):
        if (kind not in ('monthly', 'daily') or not re.fullmatch(r'\w+', symbol)
                or interval not in INTERVALS.values()
                or not re.fullmatch(r'\d{4}-\d{2}' if kind == 'monthly'
                                    else r'\d{4}-\d{2}-\d{2}', period)):
            raise ValueError('Invalid archive key')
        name = f'{symbol}-{interval}-{period}.zip'
        cached = self.cache_dir / kind / symbol / interval / name if self.cache_dir else None
        if cached is not None:
            try:
                if time.time() - cached.stat().st_mtime < self.cache_ttl:
                    content = cached.read_bytes()
                    expected = cached.with_suffix('.sha256').read_text(encoding='ascii').strip()
                    if hashlib.sha256(content).hexdigest() == expected:
                        return self._archive_rows(content)
            except (OSError, ValueError, zipfile.BadZipFile, EOFError):
                pass  # Incomplete/corrupt cache entries are downloaded again.
        url = (f'https://data.binance.vision/data/futures/um/{kind}/klines/{symbol}/'
               f'{interval}/{name}')
        response = self.request(url, optional=True)
        if response is None:
            return []  # Do not cache 404s: recent files may be published later.
        checksum = self.request(url + '.CHECKSUM')
        digest = hashlib.sha256(response.content).hexdigest()
        if digest != checksum.text.split()[0]:
            raise ValueError(f'Archive checksum mismatch: {symbol} {period}')
        rows = self._archive_rows(response.content)
        if cached is not None:
            cached.parent.mkdir(parents=True, exist_ok=True)
            self._atomic_write(cached.with_suffix('.sha256'), digest.encode('ascii'))
            self._atomic_write(cached, response.content)
        return rows

    def fetch(self, symbol, minutes, start, end, month, month_end, present, now):
        began = time.perf_counter()
        step, interval = minutes * 60000, INTERVALS[minutes]
        found = {}
        # Download a monthly archive only for substantial missing history.
        if month_end <= now and (end - start) // step - len(present) >= 1440:
            for row in self.archive(symbol, interval, month):
                value = candle(row, start, end, step)
                if value is not None and value[0] not in present:
                    found[value[0]] = value
        # A missing full day needs only one archive, including the current month.
        # Small holes stay on REST to avoid downloading a whole file for one candle.
        day = 86400000
        for day_start in range(start // day * day, end, day):
            day_end = day_start + day
            if day_end > now:
                continue
            left, right = max(start, day_start), min(end, day_end)
            absent = sum((b - a) // step for a, b in gaps(left, right, step, present | found.keys()))
            if absent < min(100, day // step):
                continue
            period = datetime.fromtimestamp(day_start / 1000, timezone.utc).strftime('%Y-%m-%d')
            for row in self.archive(symbol, interval, period, kind='daily'):
                value = candle(row, left, right, step)
                if value is not None and value[0] not in present:
                    found[value[0]] = value
        for left, right in gaps(start, end, step, present | found.keys()):
            while left < right:
                stop = min(right, left + 499 * step)
                response = self.request('https://fapi.binance.com/fapi/v1/klines', weight=2,
                                        params=dict(symbol=symbol, interval=interval, startTime=left,
                                                    endTime=stop - 1, limit=499))
                for row in response.json():
                    value = candle(row, left, stop, step)
                    if value is not None:
                        found[value[0]] = value
                left = stop
        missing = sum((b - a) // step for a, b in gaps(start, end, step, present | found.keys()))
        return list(found.values()), missing, time.perf_counter() - began


def collect(repository, symbols, minutes, start, end, log, source=None, workers=4):
    if minutes not in INTERVALS:
        raise ValueError('Unsupported candle interval')
    step = minutes * 60000
    now = int(time.time() * 1000)
    start = (int(start) + step - 1) // step * step
    end = min(int(end), now) // step * step  # Only fully closed candles.
    symbols = list(dict.fromkeys(symbols))
    if any(not re.fullmatch(r'\w+', symbol) for symbol in symbols):
        raise ValueError('Invalid symbol spelling')
    own_source = source is None
    source = source or PublicCandles()
    total = missing_total = 0
    skipped = set()
    began = time.perf_counter()
    repository.acquire_collection()
    try:
        log(f'CANDLE start symbols={len(symbols)} interval={minutes}m workers={workers} '
            f'start={start} endExclusive={end}')
        setup_at = time.perf_counter()
        repository.prepare_collection(minutes)
        log(f'CANDLE schemaReady elapsedSeconds={time.perf_counter() - setup_at:.3f}')
        exchange = source.exchange()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for left, right, month, month_end in months(start, end):
                todo = iter(symbols)
                pending = {}

                def submit_next():
                    for symbol in todo:
                        if symbol in skipped:
                            continue
                        info = exchange.get(symbol, {})
                        onboard = int(info.get('onboardDate', 0))
                        first = max(left, (onboard + step - 1) // step * step)
                        last = min(right, int(info.get('deliveryDate', right)) // step * step)
                        if first >= last:
                            continue
                        read_at = time.perf_counter()
                        present = repository.candle_times(symbol, first, last)
                        read_seconds = time.perf_counter() - read_at
                        if not next(gaps(first, last, step, present), None):
                            continue
                        job = pool.submit(source.fetch, symbol, minutes, first, last, month,
                                          month_end, present, now)
                        pending[job] = (symbol, read_seconds)
                        return True
                    return False

                for _ in range(workers):
                    submit_next()
                while pending:
                    completed, _ = wait(pending, return_when=FIRST_COMPLETED)
                    for job in completed:
                        symbol, read_seconds = pending.pop(job)
                        try:
                            values, missing, http_seconds = job.result()
                        except InvalidSymbol:
                            skipped.add(symbol)
                            log(f'CANDLE SKIPPED symbol={symbol} reason=BAD_SYMBOL code=-1121')
                        else:
                            # Refill before writing the finished batch so HTTP overlaps DB work.
                            submit_next()
                            write_at = time.perf_counter()
                            repository.add_candles(symbol, values)
                            total += len(values)
                            missing_total += missing
                            log(f'CANDLE symbol={symbol} month={month} inserted={len(values)} '
                                f'missing={missing} httpSeconds={http_seconds:.3f} '
                                f'dbReadSeconds={read_seconds:.3f} '
                                f'dbWriteSeconds={time.perf_counter() - write_at:.3f}')
                            continue
                        submit_next()
        if missing_total:
            raise RuntimeError(f'Candle collection incomplete: {missing_total} missing candles; rerun to retry')
        log(f'CANDLE complete inserted={total} skippedSymbols={len(skipped)} '
            f'elapsedSeconds={time.perf_counter() - began:.3f}')
        return total
    finally:
        if own_source:
            source.close()
        repository.release_collection()
