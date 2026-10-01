"""Transactional bulk ingestion and replace-on-success snapshots."""
class CandleIngestion:
    def acquire_collection(self):
        cursor = self.dbConnection.cursor
        cursor.execute("SELECT GET_LOCK('candle_collection_v1', 0) AS acquired")
        if cursor.fetchone()['acquired'] != 1:
            raise RuntimeError('Another candle collection/backup is running')

    def release_collection(self):
        if self.dbConnection.db.open:
            self.dbConnection.cursor.execute("SELECT RELEASE_LOCK('candle_collection_v1')")

    def prepare_collection(self, minutes):
        cursor = self.dbConnection.cursor
        cursor.execute('''CREATE TABLE IF NOT EXISTS candle_collection_meta (
            id INT PRIMARY KEY, interval_minutes INT NOT NULL,
            revision BIGINT NOT NULL, backup_revision BIGINT NOT NULL
        ) ENGINE=InnoDB''')
        cursor.execute('SELECT interval_minutes FROM candle_collection_meta WHERE id=1')
        row = cursor.fetchone()
        if row is not None and row['interval_minutes'] != minutes:
            raise ValueError('candleList already contains another interval; use a separate database')
        if row is None:
            # Legacy TEST 1 data has no interval column. Do not silently mix intervals.
            cursor.execute('SELECT candleTime FROM candleList LIMIT 1')
            if cursor.fetchone() is not None and minutes != 5:
                raise ValueError('Legacy candleList interval must be verified before non-5m ingestion')
            cursor.execute('INSERT INTO candle_collection_meta VALUES (1, %s, 0, -1)', (minutes,))
            self.dbConnection.commit()
        cursor.execute('SHOW INDEX FROM candleList WHERE Key_name=%s', ('uq_candle_symbol_time',))
        if cursor.fetchone() is None:
            cursor.execute('''SELECT symbol, candleTime FROM candleList
                              GROUP BY symbol, candleTime HAVING COUNT(*) > 1 LIMIT 1''')
            if cursor.fetchone() is not None:
                raise ValueError('Existing duplicate candles must be reconciled before adding a unique index')
            cursor.execute('CREATE UNIQUE INDEX uq_candle_symbol_time ON candleList (symbol, candleTime)')

    def candle_times(self, symbol, start, end):
        self.dbConnection.cursor.execute(
            'SELECT candleTime FROM candleList WHERE symbol=%s AND candleTime >= %s AND candleTime < %s',
            (symbol, start, end))
        return {int(row['candleTime']) for row in self.dbConnection.cursor.fetchall()}

    def add_candles(self, symbol, values):
        cursor = self.dbConnection.cursor
        for offset in range(0, len(values), 1000):
            batch = [(symbol,) + tuple(row) for row in values[offset:offset + 1000]]
            try:
                cursor.executemany('''INSERT INTO candleList
                    (symbol, candleTime, last, high, low, open, close)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE last=VALUES(last), high=VALUES(high),
                        low=VALUES(low), open=VALUES(open), close=VALUES(close)''', batch)
                cursor.execute('UPDATE candle_collection_meta SET revision=revision+1 WHERE id=1')
                self.dbConnection.commit()
            except Exception:
                self.dbConnection.db.rollback()
                raise

    def backup(self):
        self.acquire_collection()
        try:
            cursor = self.dbConnection.cursor
            cursor.execute('SELECT revision, backup_revision FROM candle_collection_meta WHERE id=1')
            meta = cursor.fetchone()
            cursor.execute("SHOW TABLES LIKE 'candleList_org'")
            exists = cursor.fetchone() is not None
            if exists and meta['revision'] == meta['backup_revision']:
                # Other strategies may prune candles without updating our revision.
                cursor.execute('SELECT COUNT(*) AS n, MAX(uid) AS last_uid FROM candleList')
                current = cursor.fetchone()
                cursor.execute('SELECT COUNT(*) AS n, MAX(uid) AS last_uid FROM candleList_org')
                if current == cursor.fetchone():
                    return False
            # Scratch tables are owned exclusively by this collector's lock.
            cursor.execute('DROP TABLE IF EXISTS candleList_backup_build')
            cursor.execute('CREATE TABLE candleList_backup_build LIKE candleList')
            cursor.execute('INSERT INTO candleList_backup_build SELECT * FROM candleList')
            self.dbConnection.commit()
            if exists:
                cursor.execute('DROP TABLE IF EXISTS candleList_backup_previous')
                cursor.execute('''RENAME TABLE candleList_org TO candleList_backup_previous,
                                  candleList_backup_build TO candleList_org''')
                cursor.execute('DROP TABLE candleList_backup_previous')
            else:
                cursor.execute('RENAME TABLE candleList_backup_build TO candleList_org')
            cursor.execute('UPDATE candle_collection_meta SET backup_revision=%s WHERE id=1',
                           (meta['revision'],))
            self.dbConnection.commit()
            return True
        except Exception:
            self.dbConnection.db.rollback()
            raise
        finally:
            self.release_collection()
