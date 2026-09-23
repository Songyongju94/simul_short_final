import time
import sys

from kowanasutil import DBConnection, DBModel, ApiHandler, DBField, DBFieldUID, ApiResult, Log

class CandleBuyResultRepository(DBModel, ApiHandler):
    def __init__(self, dbConnection, debuggingMode):
        if debuggingMode != 1:
            fields = [DBFieldUID(DBModel.Int, 36, DBField.AutoIncrement), # 0
                      DBField('symbol', DBModel.String, 16),
                      DBField('candleTime', DBModel.Long, 32),
                      DBField('position', DBModel.String, 16),
                      DBField('high', DBModel.Float, 32),
                      DBField('low', DBModel.Float, 32),
                      DBField('close', DBModel.Float, 32),
                      DBField('bolHigh', DBModel.Float, 32),
                      DBField('bolLow', DBModel.Float, 32),
                      DBField('high2BolPercent', DBModel.Float, 32),
                      DBField('low2BolPercent', DBModel.Float, 32),  # 10
                      DBField('BuyPrice', DBModel.Float, 32),
                      DBField('buy2BolPercent', DBModel.Float, 32),
                      DBField('coinIndex', DBModel.Float, 32),
                      DBField('buyTime', DBModel.Long, 32),
                      DBField('triggerTime', DBModel.Long, 32),       # 15
                      DBField('triggerPrice', DBModel.Float, 32),
                      DBField('trigger2bolPercent', DBModel.Float, 32),
                      DBField('dupForbidTime', DBModel.Long, 32),
                      DBField('dupCount', DBModel.Float, 32),
                      DBField('dupBaseSellProfitPer', DBModel.Float, 32),       # 20
                      DBField('dupStatus', DBModel.Float, 32),
                      DBField('sellUid', DBModel.Float, 32),
                      DBField('sellTime', DBModel.Long, 32),    # 23
                      DBField('addBuyCount', DBModel.Int, 10),
                      DBField('addMBuyCount', DBModel.Int, 10),     # 25
                      DBField('buyMode', DBModel.String, 16)]     # 26
        else:
            fields = [DBFieldUID(DBModel.Int, 36, DBField.AutoIncrement), # 0
                      DBField('symbol', DBModel.String, 16),
                      DBField('candleTime', DBModel.Long, 32),
                      DBField('position', DBModel.String, 16),
                      DBField('high', DBModel.Float, 32),
                      DBField('low', DBModel.Float, 32),
                      DBField('close', DBModel.Float, 32),
                      DBField('bolHigh', DBModel.Float, 32),
                      DBField('bolLow', DBModel.Float, 32),
                      DBField('high2BolPercent', DBModel.Float, 32),
                      DBField('low2BolPercent', DBModel.Float, 32),  # 10
                      DBField('BuyPrice', DBModel.Float, 32),
                      DBField('buy2BolPercent', DBModel.Float, 32),
                      DBField('coinIndex', DBModel.Float, 32),
                      DBField('buyTime', DBModel.Long, 32),
                      DBField('triggerTime', DBModel.Long, 32),       # 15
                      DBField('triggerPrice', DBModel.Float, 32),
                      DBField('trigger2bolPercent', DBModel.Float, 32),
                      DBField('bolDataList', DBModel.String, 1000),
                      DBField('openValue', DBModel.Float, 32),
                      DBField('dupForbidTime', DBModel.Long, 32),       # 20
                      DBField('dupCount', DBModel.Float, 32),
                      DBField('dupBaseSellProfitPer', DBModel.Float, 32),
                      DBField('dupStatus', DBModel.Float, 32),
                      DBField('sellUid', DBModel.Float, 32),
                      DBField('sellTime', DBModel.Long, 32),    # 25
                      DBField('addBuyCount', DBModel.Int, 10),
                      DBField('addMBuyCount', DBModel.Int, 10),
                      DBField('buyMode', DBModel.String, 16)]  # 28

        super().__init__(dbConnection, 'candleBuyResultList', fields=fields, debug=False)
        self.dbConnection = dbConnection
        self.__log = Log()

    def _query(self, sql):
        try:
            self.dbConnection.cursor.execute(sql)
        except Exception as e:
            print(str(e))
            return None
        return self.dbConnection.cursor.fetchall()

    def readBuyTimeBuyResultList(self):
        rows = self._query('SELECT symbol, MAX(buyTime) buyTime from candleBuyResultList group by symbol')
        records = []
        for row in rows:
            record = [row['symbol'], row['buyTime']]
            records.append(record)
        return records

    def readCandleBuyResultListBySymbol(self, symbol):
        rows = self._select(where='symbol' + '=\'' + symbol + '\'')
        records = []
        for row in rows:
            record = self._fromRow(row)
            records.append(record)
        return records

    def readCandleBuyResultListByCondition(self, symbol, uid, buytime, buyprice):
        rows = self._select(where='symbol' + '=\'' + symbol + '\'' + ' and uid < ' + str(uid) + ' and buyTime = '
                                  + str(buytime) + ' and BuyPrice = ' + str(buyprice))
        records = []
        for row in rows:
            record = self._fromRow(row)
            records.append(record)
        return records

    def getSymbolInfo(self):
        rows = self._query('SELECT coinIndex, symbol FROM candleBuyResultList order by coinIndex DESC')
        records = []
        for row in rows:
            record = [row['coinIndex'], row['symbol']]
            records.append(record)
            break
        return records

    def readDupCandleBuyResultList(self):
        rows = self._select(where='uid = 1')
        records = []
        for row in rows:
            record = self._fromRow(row)
            records.append(record)
        return records

    def readCandleAllBuyResultList(self, dupOK, sellCondition, dataPeriodForSell):
        if not dupOK and sellCondition == 'TRAILING_STOP_STRONG_FORWARD':
            rows = self._select(where='dupStatus = 1 and buyTime > ' + str(dataPeriodForSell) + ' ORDER BY buyTime ASC')
        elif dupOK:
            rows = self._select(where='dupStatus = 0 and buyTime > ' + str(dataPeriodForSell) + ' ORDER BY buyTime ASC')
        else:
            rows = self._select(where='uid > 0  and buyTime > ' + str(dataPeriodForSell) + ' ORDER BY buyTime ASC')
        records = []
        for row in rows:
            record = self._fromRow(row)
            records.append(record)
        return records

    def readCandleBuyResultList(self, symbol, dataPeriodForSell):
        rows = self._select(where='symbol' + '=\'' + symbol + '\' and dupStatus = 0 and buyTime > '
                                  + str(dataPeriodForSell) + ' ORDER BY buyTime ASC')
        records = []
        for row in rows:
            record = self._fromRow(row)
            records.append(record)
        return records

    def readCandleBuyResultListDesc(self, symbol):
        rows = self._select(where='symbol' + '=\'' + symbol + '\' ORDER BY buyTime DESC')
        records = []
        for row in rows:
            record = self._fromRow(row)
            records.append(record)
        return records

    def readCandleMultipleList(self, count):
        records = []
        if count == 0:
            return records
        rows = self._query(
            'SELECT candleTime FROM candleBuyResultList where candleTime > 1 GROUP BY candleTime HAVING COUNT(symbol) >=' + '\'' + str(count + 1) + '\'')
        for row in rows:
            record = row['candleTime']
            records.append(record)
        return records

    def deleteSymbolList(self, symbol):
        try:
            result = self._delete(where='symbol' + '=\'' + symbol + '\'')
            if not result:
                self.__log.d('failed to remove')
        except Exception as e:
            raise Exception(e)

    def deleteMultipleList(self, candleTime):
        try:
            result = self._delete(where='candleTime' + '=\'' + str(candleTime) + '\'')
            if not result:
                self.__log.d('failed to remove')
        except Exception as e:
            raise Exception(e)

    def addCandleBuyResult(self, data):
        try:
            result = self.add(data)
            if not result:
                self.__log.d('failed to add')
                sys.exit(0)
        except Exception as e:
            raise Exception(e)


    def updateCandleBuyResult(self, buyUID, dupForbidTime, dupCnt, dupBaseSellProfitPercent,
                              dupStatus, sellUID, sellTime):
        try:
            # self.__log.d('call updateCandleBuyResult()..')
            where = 'uid = ' + str(buyUID)

            if dupForbidTime is None:
                values = 'dupStatus = ' + str(dupStatus)
            else:
                values = 'dupForbidTime = ' + str(dupForbidTime) + ',' \
                         'dupCount = ' + str(dupCnt) + ',' \
                         'dupBaseSellProfitPer = ' + str(dupBaseSellProfitPercent) + ',' \
                         'dupStatus = ' + str(dupStatus) + ','\
                         'sellUid = ' + str(sellUID) + ',' \
                         + ' sellTime = ' + str(sellTime)
            result = self._update(values, where)  # 0 : DONE
            if result:
                print('successfully update CandleBuyResultList DB')
            else:
                self.__log.d('failed update CandleBuyResultList DB uid = ', buyUID)
        except Exception as e:
            self.__log.d('failed update CandleBuyResultList DB uid = ', buyUID)
            raise Exception(e)
        return result

    def updateSecondAddBuyCandleBuyResult(self, buyUID, triggerPrice, addMBuyCount):
        try:
            # self.__log.d('call updateSecondAddBuyCandleBuyResult()..')
            where = 'uid = ' + str(buyUID)
            values = 'triggerPrice = ' + str(triggerPrice) + ',' \
                     + ' addMBuyCount = ' + str(addMBuyCount)
            result = self._update(values, where)  # 0 : DONE
            if result:
                print('successfully update CandleBuyResultList DB')
            else:
                self.__log.d('failed update CandleBuyResultList DB uid = ', buyUID)
        except Exception as e:
            self.__log.d('failed update CandleBuyResultList DB uid = ', buyUID)
            raise Exception(e)
        return result

    def updateResetDupStatus(self):
        try:
            sql = 'update candleBuyResultList set dupStatus = 0'
            result = self._query(sql)  # 0 : DONE
            if result:
                self.__log.d('reset dupStatus DB')
        except Exception as e:
            self.__log.d('failed update updateResetDupStatus')
            raise Exception(e)

    def deleteCandleBuyResult(self, uid):
        self.__log.d('call deleteCandleBuyResult()..')
        where = 'uid = ' + str(uid)
        result = self._delete(where)  # 0 : DONE
        self.__log.d('remove uid = ', uid)
        if result:
            print('successfully update orderList DB')
        else:
            print('fail to delete DB')
        return result

    def cleanResultBuyCandle(self):
        try:
            self.clear()
        except Exception as e:
            raise Exception(e)
