from model.TradeInfo import TradeInfo

class CandleSellResultAdapter:
    @classmethod
    def createFromBinance(cls, data):
        return TradeInfo({'buyTime': data[42], 'position': float(data[3]),
                          'buyPrice': float(data[11]), 'coinIndex': float(data[41])})
