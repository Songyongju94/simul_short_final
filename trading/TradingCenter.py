from abc import ABCMeta

class TradingCenter(metaclass = ABCMeta):

    def fetchCurrency(self):
        pass

    def fetchTicker(self):
        pass

    def fetchCandle(self):
        pass

    def changePositionMode(self):
        pass

    def changePositionMode(self):
        pass

    def updateOrderList(self, data):
        pass

    def postOrder(self):
        pass

    def changeMarginType(self):
        pass
