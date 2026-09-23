import time
import sys

from kowanasutil import DBModel, ApiHandler, DBField, DBFieldUID, Log

class CandleListRepository(DBModel, ApiHandler):
    def __init__(self, dbConnection):
        fields = [DBFieldUID(DBModel.Int, 36, DBField.AutoIncrement),
                  DBField('symbol', DBModel.String, 16),
                  DBField('candleTime', DBModel.Long, 32),
                  DBField('last', DBModel.Float, 32),
                  DBField('high', DBModel.Float, 32),
                  DBField('low', DBModel.Float, 32),
                  DBField('open', DBModel.Float, 32),
                  DBField('close', DBModel.Float, 32)]
        super().__init__(dbConnection, 'candleList', fields=fields, debug=False)
        self.dbConnection = dbConnection
        self.__log = Log()

    def _query(self, sql):
        try:
            self.dbConnection.cursor.execute(sql)
        except Exception as e:
            print(str(e))
            return None
        return self.dbConnection.cursor.fetchall()

    def backup(self):
        try:
            result = self._query('CREATE table candleList_org SELECT * FROM candleList')
            self.__log.d('result=', result)
        except Exception as e:
            raise Exception(e)

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
