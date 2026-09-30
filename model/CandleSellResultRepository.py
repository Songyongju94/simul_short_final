import time
from kowanasutil import DBConnection, DBModel, ApiHandler, DBField, DBFieldUID, ApiResult, Log
from model.SellResultSchema import EXTRA_COLUMNS, ensure_sell_columns, with_sell_columns

class CandleSellResultRepository(DBModel, ApiHandler):
    def __init__(self, dbConnection, sellCondition, detailPercentForSell):
        fields = [DBFieldUID(DBModel.Int, 36, DBField.AutoIncrement),  # 0
                  DBField('symbol', DBModel.String, 32),
                  DBField('position', DBModel.String, 16),
                  DBField('buyTime', DBModel.String, 64),
                  DBField('buyPrice', DBModel.Float, 32),
                  DBField('buy2bolPercent', DBModel.Float, 32),  # 5
                  DBField('triggerTime', DBModel.String, 64),
                  DBField('triggerPrice', DBModel.Float, 32),
                  DBField('bolHigh', DBModel.Float, 32),
                  DBField('bolLow', DBModel.Float, 32),
                  DBField('quantity', DBModel.Float, 32),  # 10
                  DBField('sellTime', DBModel.String, 64),
                  DBField('sellPrice', DBModel.Float, 32),
                  DBField('profitPrice', DBModel.Float, 32),
                  DBField('profitPercent', DBModel.Float, 32),
                  DBField('totalPrice', DBModel.Float, 32),  # 15
                  DBField('totalProfitPercent', DBModel.Float, 32),
                  DBField('conditions', DBModel.String, 64),
                  DBField('coinIndex', DBModel.Float, 32),
                  DBField('buyHigh', DBModel.Float, 32),
                  DBField('buyLow', DBModel.Float, 32),     # 20
                  DBField('high2BolPercent', DBModel.Float, 32),
                  DBField('low2BolPercent', DBModel.Float, 32),
                  DBField('fundingTimes', DBModel.Int, 16),
                  DBField('fundingPrice', DBModel.Float, 32),
                  DBField('totalMargin', DBModel.Float, 32),  	# 25
                  DBField('buyTimeOrg', DBModel.String, 64),
                  DBField('buyPriceOrg', DBModel.Float, 32),
                  DBField('quantityOrg', DBModel.Float, 32),
                  DBField('lcStatus', DBModel.Int, 16),     # 29
                  DBField('addTradeCount', DBModel.Int, 16),     # 30
                  DBField('min5Status', DBModel.String, 32),
                  DBField('second5MinStatus', DBModel.String, 64),
                  DBField('lossCutBolHigh', DBModel.Float, 32),
                  DBField('lossCutPerBol', DBModel.Int, 16),
                  DBField('followSellStatus', DBModel.Int, 16),     # 35
                  DBField('2ndMin1Status', DBModel.String, 32),
                  DBField('BTC1Per', DBModel.Float, 32),
                  DBField('BTC5Per', DBModel.Float, 32),
                  DBField('ETH1Per', DBModel.Float, 32),
                  DBField('ETH5Per', DBModel.Float, 32),     # 40
                  DBField('bolHighHour1', DBModel.Float, 32),
                  DBField('bolLowHour1', DBModel.Float, 32),
                  DBField('high2BolPercentHour1', DBModel.Float, 32),
                  DBField('low2BolPercentHour1', DBModel.Float, 32),
                  DBField('bolDataListH1', DBModel.String, 1000),   # 45
                  DBField('min15HighPrice', DBModel.Float, 32),
                  DBField('min15HighPer', DBModel.Float, 32),
                  DBField('expireHighPrice', DBModel.Float, 32),
                  DBField('expireHighPer', DBModel.Float, 32),
                  DBField('riskStatus', DBModel.Int, 16),  # 50
                  DBField('riskProfitPrice', DBModel.Float, 32),
                  DBField('buyTimeEpoch', DBModel.Long, 32),
                  DBField('sellTimeEpoch', DBModel.Long, 32),
                  DBField('riskLockTime', DBModel.String, 64),
                  DBField('addBuyCount', DBModel.Int, 10),  # 55
                  DBField('addMBuyCount', DBModel.Int, 10),
                  DBField('buyMode', DBModel.String, 16),
                  DBField('buyTickNum', DBModel.Int, 10),
                  DBField('buyHTickPrice', DBModel.Float, 32),
                  DBField('h12HighDate', DBModel.String, 64),   # 60
                  DBField('h12Hour', DBModel.Int, 16),  # 61
                  DBField('h12HighPrice', DBModel.Float, 32),   # 62
                  DBField('h12HighPer', DBModel.Float, 32)]  # 63

        super().__init__(dbConnection, 'candleSellResultList', fields=fields, debug=False)
        # DBModel emits TYPE(length), so append these fields after its CREATE.
        # Named inserts also tolerate a schema upgrade interrupted between columns.
        ensure_sell_columns(dbConnection)
        for name, kind, default in EXTRA_COLUMNS:
            field_type = DBModel.String if kind.startswith("VARCHAR") else (
                DBModel.Long if kind == "BIGINT" else DBModel.Float)
            length = int(kind[8:-1]) if kind.startswith("VARCHAR") else 32
            fields.append(DBField(name, field_type, length))
        self._sell_field_names = [field.key for field in fields]
        self.dbConnection = dbConnection
        self.__log = Log()

    def add(self, data=None, columns=None):
        if columns is not None:
            return super().add(data, columns=columns)
        # Legacy writers still pass 64 values. Preserve their indices and append
        # empty metadata, using explicit column names rather than physical order.
        values = with_sell_columns(data)
        return super().add(values, columns=",".join(
            "`" + name + "`" for name in self._sell_field_names))

    def _query(self, sql):
        try:
            self.dbConnection.cursor.execute(sql)
        except Exception as e:
            print(str(e))
            return None
        return self.dbConnection.cursor.fetchall()

    def readCandleSellResultList(self, symbol):
        rows = self._select(where='symbol' + '=\'' + symbol + '\'')
        records = []
        for row in rows:
            record = self._fromRow(row)
            records.append(record)
        return records

    def readCandleSellResultListByCondition(self, symbol, uid, buytime, buyprice):
        rows = self._select(where='symbol' + '=\'' + symbol + '\'' + ' and uid < ' + str(uid) + ' and buyTime = '
                                  + str(buytime) + ' and buyPrice = ' + str(buyprice))
        records = []
        for row in rows:
            record = self._fromRow(row)
            records.append(record)
        return records

    def readLatestCandleSellResultList(self, symbol):
        rows = self._select(where='symbol' + '=\'' + symbol + '\' ORDER BY uid DESC limit 1')
        records = []
        for row in rows:
            record = self._fromRow(row)
            records.append(record)
        return records

    def _fromData(self, row, columns):
        if len(row) > 0:
            return [row[field.key] for field in columns]
        else:
            return []

    def readRiskModeCandleSellResultList(self):
        rows = self._query('SELECT uid, symbol, buyPrice, sellPrice, quantity,'
                           ' buyTimeEpoch, sellTimeEpoch, profitPrice, buyTime, sellTime, riskProfitPrice'
                           ' FROM candleSellResultList order by buyTimeEpoch ASC')
        records = []
        columns = [DBField('uid', DBModel.Int, 36),
                   DBField('symbol', DBModel.String, 32),
                   DBField('buyPrice', DBModel.Float, 32),
                   DBField('sellPrice', DBModel.Float, 32),
                   DBField('quantity', DBModel.Float, 32),
                   DBField('buyTimeEpoch', DBModel.Long, 32),
                   DBField('sellTimeEpoch', DBModel.Long, 32),
                   DBField('profitPrice', DBModel.Float, 32),
                   DBField('buyTime', DBModel.String, 64),
                   DBField('sellTime', DBModel.String, 64),
                   DBField('riskProfitPrice', DBModel.Float, 32)]
        for row in rows:
            record = self._fromData(row, columns)
            records.append(record)
        return records

    def updateRiskModeCandleSellResultList(self, uid, status, riskProfitPrice, riskLockTime):
        try:
            where = 'uid =' + str(uid)
            values = 'riskStatus = ' + str(status) + ',' \
                     'riskProfitPrice = ' + str(riskProfitPrice) + ',' \
                     'riskLockTime = \'' + riskLockTime + '\''
            result = self._update(values, where)  # 0 : DONE
            if result:
                print('successfully update CandleSellResultList DB')
            else:
                self.__log.d('failed update CandleSellResultList DB buyTime = ', uid)
        except Exception as e:
            self.__log.d('failed update CandleBuyResultList DB buyTime = ', uid)
            raise Exception(e)
        return result


    def updateBolGradient(self, buyTime, btcMin1, btcMin5, ethMin1, ethMin5):
        try:
            where = 'buyTime' + '=\'' + buyTime + '\''
            values = 'BTC1Per = ' + str(btcMin1) + ',' \
                     'BTC5Per = ' + str(btcMin5) + ',' \
                     'ETH1Per = ' + str(ethMin1) + ',' \
                     'ETH5Per = ' + str(ethMin5)
            result = self._update(values, where)  # 0 : DONE
            if result:
                print('successfully update CandleSellResultList DB')
            else:
                self.__log.d('failed update CandleSellResultList DB buyTime = ', buyTime)
        except Exception as e:
            self.__log.d('failed update CandleBuyResultList DB buyTime = ', buyTime)
            raise Exception(e)
        return result

    def addCandleSellResult(self, data):
        try:
            result = self.add(data)
            if not result:
                self.__log.d('failed to add')
        except Exception as e:
            raise Exception(e)

    def deleteCandleSellResult(self, uid):
        self.__log.d('call deleteCandleSellResult()..')
        where = 'uid = ' + str(uid)
        result = self._delete(where)  # 0 : DONE
        self.__log.d('remove uid = ', uid)
        if result:
            print('successfully update orderList DB')
        else:
            print('fail to delete DB')
        return result

    def cleanResultSellCandle(self):
        try:
            self.clear()
        except Exception as e:
            raise Exception(e)
