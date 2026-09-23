from model.Candle import Candle

class CandleResultAdapter:
    @classmethod
    def createFromBinance(cls, data, btcdomPercent):
        return Candle({'candleTime': data[2], 'last': float(data[3]), 'high': float(data[4]),
                       'low': float(data[5]), 'open': float(data[6]), 'close': float(data[7]),
                       'bolHigh': 0, 'bolLow': 0, 'high2BolPercent': 0, 'low2BolPercent': 0,
                       'btcdomPercent': btcdomPercent})
