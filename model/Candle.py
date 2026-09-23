from datetime import datetime

class Candle:
    def __init__(self, data):
        self.candleTime = data['candleTime']
        self.last = data['last']
        self.high = data['high']
        self.low = data['low']
        self.bol = None
        self.boldiff = [0, 0, 0]
        self.boldiffbyhigh = [0, 0, 0]
        self.boldiffbylow = [0, 0, 0]
        self.bolpercent = 0.0
        self.open = data['open']
        self.close = data['close']
        self.bolHigh = data['bolHigh']
        self.bolLow = data['bolLow']
        self.high2BolPercent = data['high2BolPercent']
        self.low2BolPercent = data['low2BolPercent']
        self.btcdomPercent = data['btcdomPercent']

    def setBol(self, bol):
        self.bol = bol
        for i in range(3):
            self.boldiff[i] = bol[i] - self.last
            self.boldiffbyhigh[i] = bol[i] - self.high
            self.boldiffbylow[i] = bol[i] - self.low

        if (bol[0] - bol[2]) != 0:
            self.bolpercent = (self.last - bol[2])/(bol[0] - bol[2])*100
            # if self.bolpercent < 0 or self.bolpercent > 100:
            #     if self.bolpercent < 0:
            #         self.bolpercent = abs(self.bolpercent)
            #     else:
            #         self.bolpercent -= 100
            # else:
            #     self.bolpercent = 0
            self.bolpercent -= 100
            self.bolpercent = abs(self.bolpercent)

    def __str__(self):
        return f"{datetime.fromtimestamp(self.candleTime/1000).strftime('%Y%m%d %H%M')} {self.last} {self.bol}"