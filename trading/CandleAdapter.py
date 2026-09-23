from model.Candle import Candle

class CandleAdapter:
    @classmethod
    def createFromBinance(cls, data, btcdomPercent):
        return Candle({'candleTime': data.openTime, 'last': float(data.close), 'high': float(data.high),
                       'low': float(data.low), 'open': float(data.open), 'close': float(data.close),
                       'bolHigh': 0, 'bolLow': 0, 'high2BolPercent': 0, 'low2BolPercent': 0,
                       'btcdomPercent': btcdomPercent})
