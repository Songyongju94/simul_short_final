import time
import sys

from kowanasutil import DBModel, ApiHandler, DBField, DBFieldUID, Log


class CandleHighestLowestListRepository(DBModel, ApiHandler):
    def __init__(self, dbConnection):
        fields = [DBFieldUID(DBModel.Int, 36, DBField.AutoIncrement),
                  DBField('symbol', DBModel.String, 16),
                  DBField('lunchingDate', DBModel.String, 64),
                  DBField('currentDate', DBModel.String, 64),
                  DBField('currentPrice', DBModel.Float, 32),
                  DBField('high', DBModel.Float, 32),
                  DBField('highWeek', DBModel.String, 64),
                  DBField('low', DBModel.Float, 32),
                  DBField('lowWeek', DBModel.String, 64),
                  DBField('highRate', DBModel.Float, 32),
                  DBField('lowRate', DBModel.Float, 32)]
        super().__init__(dbConnection, 'highestLowestList', fields=fields, debug=False)
        self.dbConnection = dbConnection
        self.__log = Log()

    def _query(self, sql):
        try:
            self.dbConnection.cursor.execute(sql)
        except Exception as e:
            print(str(e))
            return None
        return self.dbConnection.cursor.fetchall()

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
