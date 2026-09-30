from datetime import datetime

class TradeInfo:
    def __init__(self, data):
        self.uid = data['uid']
        self.candleTime = data['candleTime']
        self.position = data['position']
        self.high = data['high']
        self.low = data['low']
        self.bolHigh = data['bolHigh']
        self.bolLow = data['bolLow']
        self.close = data['close']
        self.buyPrice = data['buyPrice']
        self.high2BolPercent = data['high2BolPercent']
        self.low2BolPercent = data['low2BolPercent']
        self.buy2BolPercent = data['buy2BolPercent']
        self.coinIndex = data['coinIndex']
        self.buyTime = data['buyTime']
        self.triggerTime = data['triggerTime']
        self.triggerPrice = data['triggerPrice']
        self.trigger2bolPercent = data['trigger2bolPercent']
        self.addBuyCount = data['addBuyCount']
        self.addMBuyCount = data['addMBuyCount']
        self.buyMode = data['buyMode']
        self.recentLow = data.get('recentLow', 0)
        self.recentLowTime = data.get('recentLowTime', '')

    def __str__(self):
        return f"{datetime.fromtimestamp(self.candleTime/1000).strftime('%Y%m%d %H%M')}"
