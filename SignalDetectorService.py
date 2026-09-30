from datetime import timedelta
from kowanasutil import Log, Service, Task, Scheduler, KowanasTime, Config
from trading import TradingAgent
from SignalDetectorApp import SignalDetectorApp
from Definition import Definition

class SignalDetectorService(Service):
    def __init__(self, name):
        super().__init__(name)
        self.__log = None
        self.__log = Log()
        self.__definition = Definition()
        self.__config = Config(file=self.__definition.getConfig2())
        self.__app = SignalDetectorApp(self.__definition.getDb())
        self.__candleInterval = int(self.__config.configs.get('CANDLE_INTERVAL'))
        self.__testNo = int(self.__config.configs.get('TEST_NO'))
        self.__buyConditions = self.__config.configs.get('BUY_CONDITION')
        self.__btcEthGradientEnable = int(self.__config.configs.get('BTC_ETH_GRADIENT_ENABLE'))
        self.__fundingEnable = int(self.__config.configs.get('FUNDING_ENABLE'))
        self.__secondAddBuyEnable = int(self.__config.configs.get('SECOND_ADD_BUY_ENABLE'))
        self.__sellTrailingStopEnable = int(self.__config.configs.get('SELL_TRAILING_STOP_ENABLE'))
        self.__tradingAgent = TradingAgent(self.__app, database_only=self.__testNo in (18, 19))
        self.previousIndex = 0
        self.previousSymbol = None
        self.__initTask()
        self.__setTasks()


    def __initTask(self):
        # RSI simulation does not initialize the trading center.
        if self.__testNo not in (18, 19):
            self.__tradingAgent.fetchCurrency()
            try:
                self.__tradingAgent.changeInitialSettings()
            except Exception as e:
                self.__log.d(str(e))
            index = 0
            # symbol = 'GALAUSDT'
            symbol = None
            symbolInfo = self.__tradingAgent.getStopSymbolInfoFromBuy()
            if len(symbolInfo) == 1:
                index = symbolInfo[0][0]
                symbol = symbolInfo[0][1]
                if index > self.previousIndex:
                    self.previousIndex = index
                    self.previousSymbol = symbol
                else:
                    index = self.previousIndex
                    symbol = self.previousSymbol

        if self.__testNo == 0:
            self.__tradingAgent.fetchCandle(self.__candleInterval)
            # self.__tradingAgent.runSpikeCandle()
            if self.__buyConditions == 'FORWARD_STATIC_BUY' or self.__buyConditions == 'REVERSE_STATIC_BUY':
                self.__tradingAgent.backupCandleList()
                self.__tradingAgent.runBuyStaticOperation(1, None)
                if self.__secondAddBuyEnable == 1:
                    self.__tradingAgent.runBuyStaticSecondOperation()
            else:
                self.__tradingAgent.runBuyOperation()
            if self.__secondAddBuyEnable == 1:
                self.__tradingAgent.runSecondSellOperation()
            else:
                if self.__sellTrailingStopEnable == 1:
                    self.__tradingAgent.runSellTrailStopOperation()
                else:
                    self.__tradingAgent.runSellOperation()
            if self.__btcEthGradientEnable == 1:
                self.__tradingAgent.runBtcEthGradientOperation()
        elif self.__testNo == 1:
            self.__tradingAgent.fetchCandle(self.__candleInterval)
            self.__tradingAgent.backupCandleList()
        elif self.__testNo == 2:
            self.__tradingAgent.runBuyStaticOperation(index, symbol)
            if self.__secondAddBuyEnable == 1:
                self.__tradingAgent.runBuyStaticSecondOperation()
                self.__tradingAgent.runSecondSellOperation()
            else:
                if self.__sellTrailingStopEnable == 1:
                    self.__tradingAgent.runSellTrailStopOperation()
                else:
                    self.__tradingAgent.runSellOperation()
        elif self.__testNo == 3:
            if self.__buyConditions == 'FORWARD_STATIC_BUY' or self.__buyConditions == 'REVERSE_STATIC_BUY':
                self.__tradingAgent.runBuyStaticOperation(index, symbol)
                if self.__secondAddBuyEnable == 1:
                    self.__tradingAgent.runBuyStaticSecondOperation()
            else:
                self.__tradingAgent.runBuyOperation()
        elif self.__testNo == 4:
            if self.__secondAddBuyEnable == 1:
                self.__tradingAgent.runSecondSellOperation()
            elif self.__sellTrailingStopEnable == 1:
                self.__tradingAgent.runSellTrailStopOperation()
            else:
                self.__tradingAgent.runSellOperation()
        elif self.__testNo == 5:
            self.__tradingAgent.runCleanUpDupDataFromBuy()
        elif self.__testNo == 6:
            self.__tradingAgent.runCleanUpDupDataFromSell()
        elif self.__testNo == 9:
            self.__tradingAgent.runTest()
        elif self.__testNo == 10:
            if self.__btcEthGradientEnable == 1:
                self.__tradingAgent.runBtcEthGradientOperation()
        elif self.__testNo == 11:
            self.__tradingAgent.runCheckHighLowDate()
        elif self.__testNo == 12:
            self.__tradingAgent.runUnComplatedBuy()
        elif self.__testNo == 13:  # Funding logic
            self.__tradingAgent.fetchCandle(self.__candleInterval)
            self.__tradingAgent.runFundingBuy(1, None)
            self.__tradingAgent.runFundingSell()
        elif self.__testNo == 14:  # RiskMode control excute
            self.__tradingAgent.runRiskMode()
        elif self.__testNo == 15:  # remove candle data based on buyResult
            self.__tradingAgent.runRemoveCandleByBuyResult()
        elif self.__testNo == 16:  # highest and lowest value and rate.
            self.__tradingAgent.runHighestLowestData()
        elif self.__testNo == 17:
            self.__tradingAgent.runBuyStaticSecondOperation()
            self.__tradingAgent.runSecondSellOperation()
        elif self.__testNo == 18:
            self.__tradingAgent.runBuyRSIBuyOperation(
                target_symbol=None, wait_minutes=60)
        elif self.__testNo == 19:
            self.__tradingAgent.runSellRSIOperation(target_symbol=None)

    def __setTasks(self):
            return


    def __fetchCurrency(self, args):
        args['app'].fetchCurrency()
