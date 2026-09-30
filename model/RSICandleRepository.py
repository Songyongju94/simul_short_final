"""Storage for RSI analysis. No config access or network clients."""
import json


class RSICandleRepository:
    def __init__(self, db_connection):
        self.connection = db_connection
        self.cursor = db_connection.cursor
        self._result_columns = None

    def acquire_simulation_lock(self):
        self.cursor.execute("SELECT GET_LOCK('rsi_bb_15m_resume_v1', 0) AS acquired")
        if self.cursor.fetchone()["acquired"] != 1:
            raise RuntimeError("Another RSI simulation is already running")

    def release_simulation_lock(self):
        self.cursor.execute("SELECT RELEASE_LOCK('rsi_bb_15m_resume_v1')")

    def prepare_progress(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS rsi_buy_progress (
                symbol VARCHAR(64) NOT NULL PRIMARY KEY,
                nextTime BIGINT NOT NULL,
                stateJson LONGTEXT NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        self.commit()

    def load_progress(self, symbol):
        self.cursor.execute(
            "SELECT nextTime, stateJson FROM rsi_buy_progress WHERE symbol=%s",
            (symbol,))
        row = self.cursor.fetchone()
        if row is None:
            return None
        payload = json.loads(row["stateJson"])
        if payload.get("version") != 1:
            raise RuntimeError("Unsupported RSI checkpoint version; restore backup before restarting")
        return int(row["nextTime"]), payload["rsi"]

    def finish_chunk(self, symbol, next_time, rsi_state):
        # Buy rows must already be durable. Persist progress BEFORE deleting input.
        payload = json.dumps(dict(version=1, rsi=rsi_state), allow_nan=False)
        self.cursor.execute("""
            INSERT INTO rsi_buy_progress (symbol, nextTime, stateJson)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE nextTime=VALUES(nextTime), stateJson=VALUES(stateJson)
        """, (symbol, next_time, payload))
        self.commit()
        return self.prune_processed(symbol, next_time)

    def prune_processed(self, symbol, next_time):
        # Preserve 20 complete UTC days plus the current partial day.
        day = 86_400_000
        keep_from = next_time // day * day - 20 * day
        deleted = 0
        while True:
            self.cursor.execute("""
                DELETE FROM candleList
                WHERE symbol=%s AND candleTime < %s
                LIMIT 10000
            """, (symbol, keep_from))
            count = self.cursor.rowcount
            self.commit()
            deleted += count
            if count < 10000:
                return deleted

    def source_windows(self, interval_minutes):
        if interval_minutes not in (1, 3, 5, 15, 30, 60, 240):
            raise ValueError("CANDLE_INTERVAL must match the existing candleList data")
        self.cursor.execute("""
            SELECT symbol, MIN(candleTime) AS startTime, MAX(candleTime) AS lastTime
            FROM candleList GROUP BY symbol ORDER BY symbol
        """)
        return [(row["symbol"], int(row["startTime"]),
                 int(row["lastTime"]) + interval_minutes * 60000)
                for row in self.cursor.fetchall()]

    def read_five_minutes(self, symbol, start, end):
        self.cursor.execute("""
            SELECT candleTime, open, high, low, close FROM candleList
            WHERE symbol=%s AND candleTime >= %s AND candleTime < %s
            ORDER BY candleTime
        """, (symbol, start, end))
        return self.cursor.fetchall()

    def existing_buy_times(self, symbol):
        self.cursor.execute("""
            SELECT buyTime FROM candleBuyResultList
            WHERE symbol=%s AND buyMode=%s
        """, (symbol, "RSI_BB_15M"))
        return {int(row["buyTime"]) for row in self.cursor.fetchall()}

    def save_signal(self, symbol, signal, coin_index):
        # The normal/debugging schemas differ. Populate the actual table columns.
        if self._result_columns is None:
            self.cursor.execute("SHOW COLUMNS FROM candleBuyResultList")
            self._result_columns = self.cursor.fetchall()
        required = {"symbol", "candleTime", "position", "BuyPrice",
                    "buyTime", "triggerTime", "triggerPrice", "buyMode"}
        found = {column["Field"].lower() for column in self._result_columns}
        if not {name.lower() for name in required} <= found:
            raise RuntimeError("candleBuyResultList is missing required RSI result columns")
        known = {key.lower(): value for key, value in signal.items()}
        known.update(symbol=symbol, coinindex=coin_index)
        names, values = [], []
        for column in self._result_columns:
            if "auto_increment" in column["Extra"].lower():
                continue
            name = column["Field"]
            names.append("`" + name.replace("`", "``") + "`")
            if name.lower() in known:
                values.append(known[name.lower()])
                continue
            kind = column["Type"].lower().split("(")[0]
            if kind in ("char", "varchar", "tinytext", "text", "mediumtext", "longtext"):
                values.append("")
            elif kind in ("tinyint", "smallint", "mediumint", "int", "bigint",
                          "float", "double", "decimal", "bit"):
                values.append(0)
            else:
                raise ValueError("Unsupported result column type: " + kind)
        placeholders = ", ".join(["%s"] * len(values))
        sql = ("INSERT INTO candleBuyResultList (" + ", ".join(names) + ") "
               "SELECT " + placeholders + " FROM DUAL WHERE NOT EXISTS "
               "(SELECT 1 FROM candleBuyResultList WHERE symbol=%s AND buyTime=%s AND buyMode=%s)")
        self.cursor.execute(sql, tuple(values) + (symbol, signal["buyTime"], "RSI_BB_15M"))
        return self.cursor.rowcount > 0

    def commit(self):
        self.connection.commit()

