from model.TradeInfo import TradeInfo

class TradeInfoAdapter:
    @classmethod
    def createFromBinance(cls, data):
        return TradeInfo({'uid': data[0], 'candleTime': data[2], 'position': data[3], 'high': float(data[4]),
                          'low': float(data[5]), 'close': float(data[6]), 'bolHigh': float(data[7]),
                          'bolLow': float(data[8]), 'high2BolPercent': float(data[9]),
                          'low2BolPercent': float(data[10]), 'buyPrice': float(data[11]),
                          'buy2BolPercent': float(data[12]),
                          'coinIndex': float(data[13]), 'buyTime': data[14], 'triggerTime': data[15],
                          'triggerPrice': float(data[16]), 'trigger2bolPercent': float(data[17]),
                          'addBuyCount': int(data[26]), 'addMBuyCount': int(data[27]), 'buyMode': data[28]})
