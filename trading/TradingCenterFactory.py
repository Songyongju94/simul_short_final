from trading.TradingBinance import TradingBinance 

class TradingCenterFactory:
    @classmethod
    def create(self, name):
        if name == 'binance': return TradingBinance()