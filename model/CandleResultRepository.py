import time
from kowanasutil import DBConnection, DBModel, ApiHandler, DBField, DBFieldUID, ApiResult, Log

class CandleResultRepository(DBModel, ApiHandler):
    def __init__(self, dbConnection):
        fields = [DBFieldUID(DBModel.Int, 36, DBField.AutoIncrement),
                  DBField('symbol', DBModel.String, 32),
                  DBField('candleTime', DBModel.Long, 32),
                  DBField('high', DBModel.Float, 32),
                  DBField('low', DBModel.Float, 32),
                  DBField('close', DBModel.Float, 32),
                  DBField('bolHigh', DBModel.Float, 32),
                  DBField('bolLow', DBModel.Float, 32),
                  DBField('high2BolPercent', DBModel.Float, 32),
                  DBField('low2BolPercent', DBModel.Float, 32),
                  DBField('coinIndex', DBModel.Float, 32)]
        super().__init__(dbConnection, 'candleResultList', fields=fields, debug=False)
        self.dbConnection = dbConnection
        self.__log = Log()

    def readCandleResultList(self, symbol):
        rows = self._select(where='symbol' + '=\'' + symbol + '\'')
        records = []
        for row in rows:
            record = self._fromRow(row)
            records.append(record)
        return records

    def readCandleXPercentOverList(self, symbol, percent):
        rows = self._select(where='symbol' + '=\'' + symbol + '\' and (high2BolPercent > '
                                  + percent + ' or low2BolPercent > ' + percent + ')')
        records = []
        for row in rows:
            record = self._fromRow(row)
            records.append(record)
        return records

    def _query(self, sql):
        try:
            self.dbConnection.cursor.execute(sql)
        except Exception as e:
            print(str(e))
            return None
        return self.dbConnection.cursor.fetchall()

    def readCandleMultipleList(self, count):
        rows = self._query(
            'SELECT candleTime FROM candleResultList where candleTime > 1 GROUP BY candleTime HAVING COUNT(symbol) >=' + '\'' + count + '\'')
        records = []
        for row in rows:
            record = row['candleTime']
            records.append(record)
        return records

    def deleteMultipleList(self, candleTime):
        try:
            result = self._delete(where='candleTime' + '=\'' + str(candleTime) + '\'')
            if not result:
                self.__log.d('failed to remove')
        except Exception as e:
            raise Exception(e)

    def addCandleResult(self, data):
        try:
            result = self.add(data)
            if not result:
                self.__log.d('failed to add')
        except Exception as e:
            raise Exception(e)

    def cleanResultCandle(self):
        try:
            self.clear()
        except Exception as e:
            raise Exception(e)
