"""TEST 19 persistence; existing sell table layout stays compatible."""
import json
import re
from math import isclose
from datetime import datetime, timedelta, timezone
from model.SellResultSchema import ensure_sell_columns


def kst(seconds):
    return datetime.fromtimestamp(seconds, timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")


def stored_legs(row):
    return [dict(time=int(row[f"sell{i}TimeEpoch"]), price=float(row[f"sell{i}Price"]),
                 quantity=float(row[f"sell{i}Quantity"]), profit=float(row[f"sell{i}ProfitPrice"]),
                 stage=row[f"sell{i}Reason"])
            for i in (1, 2) if row.get(f"sell{i}Reason")]


def summary_values(buy, state, legs):
    """One buy -> one result. Aggregate only the legs actually persisted."""
    if not 1 <= len(legs) <= 2 or len({e["stage"] for e in legs}) != len(legs):
        raise ValueError("Expected one or two distinct sell stages")
    if any(e["stage"] not in ("STOP", "TP5", "BB4H") or e["quantity"] <= 0 for e in legs):
        raise ValueError("Invalid sell leg")
    if len(legs) == 2 and legs[1]["time"] < legs[0]["time"]:
        raise ValueError("Sell legs must be chronological")
    original = state["balance"] / state["buy_price"]
    quantity = sum(e["quantity"] for e in legs)
    if quantity > original and not isclose(quantity, original, rel_tol=1e-6):
        raise ValueError("Sell quantity exceeds original buy quantity")
    profit = sum(e["profit"] for e in legs)
    average = sum(e["price"] * e["quantity"] for e in legs) / quantity
    latest = legs[-1]
    values = dict(buyUid=buy["uid"], symbol=buy["symbol"], position="LONG",
                  buyTime=kst(buy["buyTime"]), buyTimeOrg=kst(buy["buyTime"]),
                  buyTimeEpoch=buy["buyTime"], buyPrice=state["buy_price"],
                  buyPriceOrg=state["buy_price"], quantityOrg=original, quantity=quantity,
                  sellTime=kst(latest["time"]), sellTimeEpoch=latest["time"], sellPrice=average,
                  profitPrice=profit, profitPercent=(average/state["buy_price"]-1)*100,
                  totalPrice=state["balance"]+profit,
                  totalProfitPercent=profit/state["balance"]*100, totalMargin=state["balance"],
                  conditions=f"RSI19v{state['version']}:{buy['uid']}",
                  coinIndex=buy["coinIndex"], buyHigh=buy["high"], buyLow=buy["low"],
                  lossCutBolHigh=state["stop_price"],
                  lcStatus=int(any(e["stage"] == "STOP" for e in legs)), buyMode="RSI_BB_15M")
    for i in (1, 2):
        leg = legs[i-1] if len(legs) >= i else None
        values.update({
            f"sell{i}Price": leg["price"] if leg else 0,
            f"sell{i}Quantity": leg["quantity"] if leg else 0,
            f"sell{i}Time": kst(leg["time"]) if leg else "",
            f"sell{i}TimeEpoch": leg["time"] if leg else 0,
            f"sell{i}ProfitPrice": leg["profit"] if leg else 0,
            f"sell{i}Reason": leg["stage"] if leg else "",
        })
    return values


class RSISellRepository:
    def __init__(self, connection):
        self.connection, self.cursor = connection, connection.cursor
        self.columns = None

    def acquire(self):
        self.cursor.execute("SELECT GET_LOCK('rsi_sell_19_v1', 0) AS acquired")
        if self.cursor.fetchone()["acquired"] != 1:
            raise RuntimeError("TEST 19 is already running")

    def release(self):
        db = getattr(self.connection, "db", None)
        if db is None or db.open:
            self.cursor.execute("SELECT RELEASE_LOCK('rsi_sell_19_v1')")

    def prepare(self):
        ensure_sell_columns(self.connection)
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS rsi_sell_progress (
            buyUid BIGINT NOT NULL PRIMARY KEY, stateJson LONGTEXT NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        self.connection.commit()
        self.cursor.execute("SHOW COLUMNS FROM candleSellResultList")
        self.columns = self.cursor.fetchall()
        self._merge_old_split_rows()

    def buys(self, symbol=None):
        sql = """SELECT uid, symbol, buyTime, BuyPrice, recentLow, coinIndex,
                 high, low FROM candleBuyResultList
                 WHERE buyMode=%s AND position=%s"""
        params = ("RSI_BB_15M", "LONG")
        if symbol is not None:
            sql += " AND symbol=%s"
            params += (symbol,)
        self.cursor.execute(sql + " ORDER BY symbol, buyTime, uid", params)
        return self.cursor.fetchall()

    def load(self, uid):
        self.cursor.execute("SELECT stateJson FROM rsi_sell_progress WHERE buyUid=%s", (uid,))
        row = self.cursor.fetchone()
        return json.loads(row["stateJson"]) if row else None

    def save_event(self, buy, state, event):
        self.cursor.execute("SELECT * FROM candleSellResultList WHERE buyUid=%s", (buy["uid"],))
        matches = self.cursor.fetchall()
        if len(matches) > 1:
            raise ValueError(f"Multiple sell results for buyUid={buy['uid']}")
        row = matches[0] if matches else None
        if row and (row["symbol"] != buy["symbol"] or int(row["buyTimeEpoch"]) != int(buy["buyTime"])
                    or row["conditions"] != f"RSI19v{state['version']}:{buy['uid']}"):
            raise ValueError("Sell result does not match this buy/version")
        legs = stored_legs(row) if row else []
        for leg in legs:
            if leg["stage"] == event["stage"]:
                if (leg["time"] != event["time"] or any(
                        not isclose(leg[key], event[key], rel_tol=1e-10, abs_tol=1e-12)
                        for key in ("price", "quantity", "profit"))):
                    raise ValueError("Replayed sell differs from saved result")
                return False
        legs.append(event)
        values = summary_values(buy, state, legs)
        values["bolHigh"] = event.get("upper", 0) or (row["bolHigh"] if row else 0)
        if row:
            self._update_result(row["uid"], values)
        else:
            self._insert_result(values)
        self.connection.commit()
        return True

    def _update_result(self, uid, values):
        assignments = ",".join("`" + name + "`=%s" for name in values)
        self.cursor.execute("UPDATE candleSellResultList SET " + assignments + " WHERE uid=%s",
                            tuple(values.values()) + (uid,))

    def _insert_result(self, values):
        names, data = [], []
        for column in self.columns:
            if "auto_increment" in column.get("Extra", ""):
                continue
            name, kind = column["Field"], column["Type"].lower()
            if name in values:
                value = values[name]
            elif any(kind.startswith(x) for x in ("varchar", "char", "text", "longtext")):
                value = ""
            elif any(kind.startswith(x) for x in ("int", "bigint", "smallint", "tinyint", "mediumint", "float", "double", "decimal")):
                value = 0
            elif column.get("Default") is not None or column.get("Null") == "YES":
                continue
            else:
                raise ValueError(f"Unsupported required sell column: {name}")
            names.append("`" + name.replace("`", "``") + "`")
            data.append(value)
        self.cursor.execute("INSERT INTO candleSellResultList (" + ",".join(names) +
                            ") VALUES (" + ",".join(["%s"] * len(data)) + ")", tuple(data))

    def _merge_old_split_rows(self):
        """Lossless conversion of v2 split rows under the TEST 19 session lock."""
        self.cursor.execute("""SELECT * FROM candleSellResultList
            WHERE buyUid=0 AND buyMode=%s AND conditions LIKE %s
            ORDER BY sellTimeEpoch, uid""", ("RSI_BB_15M", "RSI19v2:%"))
        groups = {}
        for row in self.cursor.fetchall():
            match = re.fullmatch(r"RSI19v2:(\d+):(STOP|TP5|BB4H)", row["conditions"])
            if not match:
                raise ValueError("Unrecognized legacy RSI sell record")
            groups.setdefault(int(match[1]), []).append((row, match[2]))
        if not groups:
            return
        # The merge updates one row and removes its now-redundant counterpart;
        # require transactions and retain exact originals in an archive.
        self.cursor.execute("""SELECT ENGINE AS engine FROM information_schema.TABLES
            WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='candleSellResultList'""")
        if self.cursor.fetchone()["engine"].lower() != "innodb":
            raise ValueError("RSI sell consolidation requires InnoDB")
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS rsi_sell_split_archive (
            sellUid BIGINT NOT NULL PRIMARY KEY, rowJson LONGTEXT NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        self.connection.commit()
        for buy_uid, entries in groups.items():
            self.cursor.execute("SELECT * FROM candleBuyResultList WHERE uid=%s", (buy_uid,))
            buy = self.cursor.fetchone()
            if not buy or any(row["symbol"] != buy["symbol"] or
                              int(row["buyTimeEpoch"]) != int(buy["buyTime"]) for row, stage in entries):
                raise ValueError(f"Legacy sell has no matching buy: {buy_uid}")
            self.cursor.execute("SELECT uid FROM candleSellResultList WHERE buyUid=%s", (buy_uid,))
            if self.cursor.fetchone():
                raise ValueError(f"Both split and consolidated results exist: {buy_uid}")
            first = entries[0][0]
            state = dict(version=2, buy_price=float(first["buyPrice"]),
                         balance=float(first["totalMargin"]), stop_price=float(first["lossCutBolHigh"]))
            legs = [dict(stage=stage, time=int(row["sellTimeEpoch"]), price=float(row["sellPrice"]),
                         quantity=float(row["quantity"]), profit=float(row["profitPrice"]))
                    for row, stage in entries]
            values = summary_values(buy, state, legs)
            values["bolHigh"] = entries[-1][0]["bolHigh"]
            try:
                self.connection.db.begin()
                for row, stage in entries:
                    self.cursor.execute("""INSERT INTO rsi_sell_split_archive (sellUid,rowJson)
                        VALUES (%s,%s)""", (row["uid"], json.dumps(row, default=str)))
                self._update_result(first["uid"], values)
                for row, stage in entries[1:]:
                    self.cursor.execute("DELETE FROM candleSellResultList WHERE uid=%s", (row["uid"],))
                self.connection.commit()
            except BaseException:
                if self.connection.db.open:
                    self.connection.db.rollback()
                raise

    def checkpoint(self, uid, state):
        self.cursor.execute("""INSERT INTO rsi_sell_progress (buyUid,stateJson)
            VALUES (%s,%s) ON DUPLICATE KEY UPDATE stateJson=VALUES(stateJson)""",
            (uid, json.dumps(state, allow_nan=False)))
        self.connection.commit()
