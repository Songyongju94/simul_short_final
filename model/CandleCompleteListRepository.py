import time
from kowanasutil import DBModel, ApiHandler, DBField, DBFieldUID, Log

class CandleCompleteListRepository(DBModel, ApiHandler):
    def __init__(self, dbConnection):
        fields = [DBFieldUID(DBModel.Int, 36, DBField.AutoIncrement),
                  DBField('coinIndex', DBModel.Float, 32),
                  DBField('symbol', DBModel.String, 16),
                  DBField('buyCompleteTime', DBModel.String, 64),
                  DBField('sellCompleteTime', DBModel.String, 64)]
        super().__init__(dbConnection, 'completeSymbolList', fields=fields, debug=False)
        self.__log = Log()

    def readCompleteList(self, symbol):
        rows = self._select(where='symbol' + '=\'' + symbol + '\'')
        records = []
        for row in rows:
            record = self._fromRow(row)
            records.append(record)
        return records

    def read(self):
        rows = self._select()
        records = []
        for row in rows:
            record = self._fromRow(row)
            records.append(record)
        return records

    def updateCompleteList(self, symbol, buyTime, sellTime):
        try:
            self.__log.d('call updateCompleteList()..')
            where = 'symbol = ' + symbol

            if buyTime is None:
                values = 'sellCompleteTime = ' + sellTime
            else:
                values = 'buyCompleteTime = ' + buyTime

            result = self._update(values, where)  # 0 : DONE
            if result:
                print('successfully update updateBuyCompleteList DB')
            else:
                self.__log.d('failed update updateBuyCompleteList DB symbol = ', symbol)
        except Exception as e:
            self.__log.d('failed update CandleBuyResultList DB symbol = ', symbol)
            raise Exception(e)
        return result

    def cleanCompleteList(self):
        try:
            self.clear()
        except Exception as e:
            raise Exception(e)

    def addCompleteList(self, data):
        previousResult = self.readCompleteList(data[2])
        if previousResult is not None and len(previousResult) > 0:
            return

        try:
            result = self.add(data)
            if not result:
                self.__log.d('failed to add')
        except Exception as e:
            raise Exception(e)



