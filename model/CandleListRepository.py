import time
import sys

from kowanasutil import DBModel, ApiHandler, DBField, DBFieldUID, Log

from model.CandleIngestion import CandleIngestion

class CandleListRepository(CandleIngestion, DBModel, ApiHandler):
    def __init__(self, dbConnection):
        fields = [DBFieldUID(DBModel.Int, 36, DBField.AutoIncrement),
                  DBField('symbol', DBModel.String, 32),
                  DBField('candleTime', DBModel.Long, 32),
                  DBField('last', DBModel.Float, 32),
                  DBField('high', DBModel.Float, 32),
                  DBField('low', DBModel.Float, 32),
                  DBField('open', DBModel.Float, 32),
                  DBField('close', DBModel.Float, 32)]
        super().__init__(dbConnection, 'candleList', fields=fields, debug=False)
        self.dbConnection = dbConnection
        self.__log = Log()
        self._ensure_candle_time_index()

    def _ensure_candle_time_index(self):
        cursor = self.dbConnection.cursor
        cursor.execute(
            "SHOW INDEX FROM candleList WHERE Key_name = %s",
            ('idx_candlelist_symbol_time',))
        if cursor.fetchone() is not None:
            return
        cursor.execute(
            "CREATE INDEX idx_candlelist_symbol_time "
            "ON candleList (symbol, candleTime)")

    def _query(self, sql):
        try:
            self.dbConnection.cursor.execute(sql)
        except Exception as e:
            print(str(e))
            return None
        return self.dbConnection.cursor.fetchall()

    def readCandleList(self, symbol):
        rows = self._select(where='symbol' + '=\'' + symbol + '\' ORDER BY candleTime ASC')
        records = []
        for row in rows:
            record = self._fromRow(row)
            records.append(record)
        return records

    def readCandlePeriodList(self, symbol, _from, _to):
        rows = self._select(where='symbol' + '=\'' + symbol + '\' and candleTime between '
                                  + str(_from) + ' and ' + str(_to) + ' ORDER BY candleTime ASC')
        records = []
        for row in rows:
            record = self._fromRow(row)
            records.append(record)
        return records

    def cleanCandle(self):
        try:
            self.clear()
        except Exception as e:
            raise Exception(e)

    def addCandle(self, data):
        try:
            result = self.add(data)
            if not result:
                self.__log.d('failed to add')
        except Exception as e:
            raise Exception(e)

    def deleteCandleBySymbol(self, symbol):
        try:
            where = 'symbol' + '=\'' + symbol + '\''
            result = self._delete(where)
            if not result:
                self.__log.d('failed to remove deleteCandleBySymbol()')
                sys.exit(0)
        except Exception as e:
            raise Exception(e)

    def deleteCandleByTime(self, symbol, candleTime):
        try:
            where = 'symbol' + '=\'' + symbol + '\'' + ' and' + ' candleTime' + '<\'' + str(candleTime) + '\''
            result = self._delete(where)
            if not result:
                self.__log.d('failed to deleteCandleByTime()')
        except Exception as e:
            raise Exception(e)

    def deleteCandleBySymbolAndTime(self, symbol, startTime, endTime):
        try:
            where = 'symbol' + '=\'' + symbol + '\'' + ' and ' + \
                    str(startTime) + ' < candleTime  and candleTime < ' + str(endTime)
            result = self._delete(where)
            if not result:
                self.__log.d('failed to deleteCandleBySymbolAndTime()')
        except Exception as e:
            raise Exception(e)


    def deleteFirstCandle(self, symbol, candleTime):
        try:
            where = 'symbol' + '=\'' + symbol + '\'' + ' and' + ' candleTime' + '=\'' + str(candleTime) + '\''
            result = self._delete(where)
            if not result:
                self.__log.d('failed to add')
        except Exception as e:
            raise Exception(e)
            
    def optimizeTableCandle(self):
        try:
            result = self._query('OPTIMIZE TABLE candleList')
            self.__log.d('OPTIMIZE result=', result)
        except Exception as e:
            raise Exception(e)
