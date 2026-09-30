import time
import numpy
import traceback

from trading.BinanceFuturesClient import BinanceFuturesClient, OrderType
from datetime import date, timedelta
from kowanasutil import Log, Config

from model.Currency import Currency

from trading.TradingCenter import TradingCenter
from trading.CandleAdapter import CandleAdapter
from Definition import Definition

# Bianace returned wrong pricePrecision values so menually update the price
def updatePricePrecision_all(currSymbol, currPricePrecision):
    pricePrecision = currPricePrecision

    if currSymbol == 'GAIBUSDT':
        pricePrecision = -1

    return pricePrecision

# Bianace returned wrong pricePrecision values so menually update the price
def updatePricePrecision(currSymbol, currPricePrecision):
    symbol = currSymbol.replace('USDT', '')
    pricePrecision = currPricePrecision

    if symbol == 'GAIB' or symbol == 'OURA':
        pricePrecision = -1
    elif symbol == 'YFI':
        pricePrecision = 0
    elif symbol == 'BTC' or symbol == 'MKR' or symbol == 'DEFI' or symbol == 'BTCDOM':
        pricePrecision = 1
    elif symbol == 'ETH' or symbol == 'BCH' or symbol == 'LTC' or symbol == 'XMR' or symbol == 'DASH' \
            or symbol == 'ZEC' or symbol == 'BNB' or symbol == 'COMP' \
            or symbol == 'TRB' or symbol == 'EGLD' or symbol == 'KSM' or symbol == 'AAVE' or symbol == 'FOOTBALL' \
            or symbol == 'QNT' or symbol == 'GMX' or symbol == 'SSV' or symbol == 'NMR' or symbol == 'BSV' \
            or symbol == 'ILV' or symbol == 'AUCTION':
        pricePrecision = 2
    elif symbol == 'EOS' or symbol == 'ETC' or symbol == 'LINK' or symbol == 'XTZ' or symbol == 'ATOM' \
            or symbol == 'NEO' or symbol == 'QTUM' or symbol == 'SNX' \
            or symbol == 'DOT' or symbol == 'BAL' or symbol == 'CRV' or symbol == 'RUNE' or symbol == 'SOL' \
            or symbol == 'UNI' or symbol == 'AVAX' or symbol == 'NEAR' or symbol == 'FIL' \
            or symbol == 'AXS' or symbol == 'ZEN' or symbol == 'LIT' or symbol == 'UNFI' or symbol == 'ALICE' \
            or symbol == 'GTC' or symbol == 'MASK' or symbol == 'DYDX' or symbol == 'CELO' or symbol == 'AR' \
            or symbol == 'LPT' or symbol == 'ENS' or symbol == 'ANT' or symbol == 'FLOW' or symbol == 'API3' \
            or symbol == 'APE' or symbol == 'INJ' or symbol == 'CVX' or symbol == 'ICP' or symbol == 'APT' \
            or symbol == 'BLUEBIRD' or symbol == 'FXS' or symbol == 'HOOK' or symbol == 'HIGH' or symbol == 'XVS' \
            or symbol == 'UMA' or symbol == 'RAD' or symbol == 'CYBER' or symbol == 'BOND' or symbol == 'GAS'\
            or symbol == 'ORDI' or symbol == 'BADGER' or symbol == 'ETHW' or symbol == 'MOVR':
        pricePrecision = 3
    elif symbol == 'XRP' or symbol == 'ADA' or symbol == 'ONT' or symbol == 'IOTA' or symbol == 'BAT' \
            or symbol == 'THETA' or symbol == 'ALGO' or symbol == 'KNC' \
            or symbol == 'ZRX' or symbol == 'OMG' or symbol == 'SXP' or symbol == 'KAVA' or symbol == 'BAND' \
            or symbol == 'RLC' or symbol == 'WAVES' or symbol == 'SUSHI' or symbol == 'ICX' \
            or symbol == 'STORJ' or symbol == 'FTM' or symbol == 'ENJ' or symbol == 'FLM' or symbol == 'TOMO' \
            or symbol == 'LRC' or symbol == 'MATIC' or symbol == 'OCEAN' or symbol == 'BEL' or symbol == 'CTK' \
            or symbol == '1INCH' or symbol == 'SAND' or symbol == 'SFP' or symbol == 'XEM' or symbol == 'CHR' \
            or symbol == 'MANA' or symbol == 'MTL' or symbol == 'OGN' or symbol == 'BAKE' or symbol == 'AUDIO' \
            or symbol == 'C98' or symbol == 'ATA' or symbol == 'KLAY' or symbol == 'CTSI' or symbol == 'IMX' \
            or symbol == 'GMT' or symbol == 'DAR' or symbol == 'GAL' or symbol == 'OP' or symbol == 'STG' \
            or symbol == 'LUNA2' or symbol == 'LDO' or symbol == 'FET' or symbol == 'MAGIC' or symbol == 'RNDR' \
            or symbol == 'MINA' or symbol == 'AGIX' or symbol == 'PHB' or symbol == 'CFX' or symbol == 'STX' \
            or symbol == 'BNX' or symbol == 'PERP' or symbol == 'LQTY' or symbol == 'ID' or symbol == 'ARB' \
            or symbol == 'JOE' or symbol == 'RDNT' or symbol == 'HFT' or symbol == 'BLUR' or symbol == 'EDU' \
            or symbol == 'SUI' or symbol == 'COMBO' or symbol == 'MAV' or symbol == 'WLD' or symbol == 'PENDLE' \
            or symbol == 'ARKM' or symbol == 'AGLD' or symbol == 'YGG' or symbol == 'BNT' or symbol == 'SEI' \
            or symbol == 'HIFI' or symbol == 'ARK' or symbol == 'FRONT' or symbol == 'GLMR' or symbol == 'BICO' \
            or symbol == 'STRAX' or symbol == 'LOOM' or symbol == 'BIGTIME' or symbol == 'POLYX' or symbol == 'POWR' \
            or symbol == 'TIA' or symbol == 'CAKE' or symbol == 'TWT' or symbol == 'STEEM' or symbol == 'NTRN' \
            or symbol == 'PYTH' or symbol == 'SUPER' or symbol == 'ONG' or symbol == 'JTO' \
            or symbol == 'ACE' or symbol == 'NFP' or symbol == 'XAI' or symbol == 'WIF' or symbol == 'MANTA':
        pricePrecision = 4
    elif symbol == 'TRX' or symbol == 'XLM' or symbol == 'VET' or symbol == 'ZIL' or symbol == 'DOGE' \
            or symbol == 'BLZ' or symbol == 'REN' or symbol == 'ALPHA' \
            or symbol == 'SKL' or symbol == 'GRT' or symbol == 'CHZ' or symbol == 'ANKR' or symbol == 'RVN' \
            or symbol == 'COTI' or symbol == 'HBAR' or symbol == 'ONE' or symbol == 'LINA' \
            or symbol == 'STMX' or symbol == 'CELR' or symbol == 'NKN' or symbol == 'DGB' or symbol == 'IOTX' \
            or symbol == '1000XEC' or symbol == 'GALA' or symbol == 'ARPA' or symbol == 'PEOPLE' or symbol == 'ROSE' \
            or symbol == 'DUSK' or symbol == 'WOO' or symbol == '1000LUNC' or symbol == 'T' or symbol == 'ASTR' \
            or symbol == 'ACH' or symbol == 'TRU' or symbol == 'USDC' or symbol == 'TLM' or symbol == 'AMB' \
            or symbol == 'IDEX' or symbol == '1000FLOKI' or symbol == 'MDT' or symbol == 'DODOX' or symbol == 'OXT' \
            or symbol == 'STPT' or symbol == 'WAXP' or symbol == 'RIF' or symbol == 'SNT' or symbol == 'TOKEN' \
            or symbol == 'KAS' or symbol == 'USTC' or symbol == 'AI' or symbol == '1000RATS':
        pricePrecision = 5
    elif symbol == 'IOST' or symbol == 'RSR' or symbol == 'REEF' or symbol == 'DENT' or symbol == 'HOT' \
            or symbol == '1000SHIB' or symbol == 'JASMY' or symbol == 'CKB' \
            or symbol == 'LEVER' or symbol == 'KEY' or symbol == 'XVG' or symbol == 'ORBS' or symbol == 'SLP' \
            or symbol == 'MEME' or symbol == 'MBL' or symbol == 'BEAMX' or symbol == '1000BONK':
        pricePrecision = 6
    elif symbol == 'SPELL' or symbol == '1000PEPE' or symbol == '1000SATS':
        pricePrecision = 7
    else:
        pricePrecision = currPricePrecision
    # else:
    #     pricePrecision = -1
    #     if not(symbol.endswith('BUSD') or symbol.endswith('USDC') or symbol == 'SRM' or symbol == 'HNT'
    #         or symbol == 'CVC' or symbol == 'BTS' or symbol == 'BTC_240628' or symbol == 'ETH_240628'
    #         or symbol == 'BTCST' or symbol == 'SC' or symbol == 'RAY' or symbol == 'FTT' or symbol == 'COCOS'
    #         or symbol == 'ETHBTC' or symbol == 'BTC_240329' or symbol == 'ETH_240329'):
    #         Log().d(symbol, ' pricePrecision is not decided. currPricePrecision=', currPricePrecision)

    return pricePrecision

class TradingBinance(TradingCenter):
    def __init__(self):
        self.__definition = Definition()
        self.__config = Config(file=self.__definition.getConfig1())
        self.__log = Log()

        self.__request_client = BinanceFuturesClient(
            api_key=self.__config.configs.get('API_KEY'), secret_key=self.__config.configs.get('SECRET_KEY'))
        self.hedgeModeOn()
        self.upDownLimit = self.__config.configs.get('UP_DOWN_LIMIT')

    def __getInterval(self, min):
        mins = {1: "1m",
                3: "3m",
                5: "5m",
                15: "15m",
                30: "30m",
                60: "1h",
                240: "4h",
                1000: "1w"}
        return mins[min]

    def fetchCurrency(self):
        symbols = None
        try:
            value = self.__request_client.get_exchange_information()
            symbols = value.symbols
        except Exception as e:
            self.__log.d(e, ' ', traceback.format_exc())
            return None

        return [Currency({'symbol': symbol.symbol,
                          'pricePrecision': updatePricePrecision(symbol.symbol, symbol.pricePrecision),
                          'quantityPrecision': symbol.quantityPrecision + 2}) for symbol in symbols]

    def __calcBolinger(self, data):
        ma20 = numpy.mean(data)
        std = numpy.std(data)
        bolup = ma20 + std * 2
        boldown = ma20 - std * 2
        return (bolup, ma20, boldown)

    def getCandlestickData(self, symbol, minuites, limitCnt, startTime):
        values = None
        try:
            values = self.__request_client.get_candlestick_data(symbol=symbol, interval=self.__getInterval(minuites),
                                                                startTime=startTime, endTime=None, limit=limitCnt)
        except Exception as e:
            self.__log.d(e)
            raise
        return values

    def hedgeModeOn(self):
        try:
            result = self.changePositionMode()
        except Exception as e:
            self.__log.d(e)

    def changePositionMode(self):
        result = None
        try:
            result = self.__request_client.change_position_mode(dualSidePosition=True)
        except Exception as e:
            self.__log.d(e)
        return result

    def change_initial_leverage(self, symbol, leverage):
        result = self.__request_client.change_initial_leverage(symbol=symbol, leverage=leverage)
        return result

    def postOrder(self, data, orderType):
        result = None
        price = None
        quantity = None
        clientOrderId = None
        stopPrice = None
        side = data[2]

        if side == 'BUY':
            longShort = "LONG"
        else:
            longShort = "SHORT"

        if data[1].quantityPrecision == 0:
            quantity = int(data[4])
        else:
            quantity = data[4]
        quantity = round(quantity, data[1].quantityPrecision)

        if data[0] == 'open':
            if data[1].pricePrecision == 0:
                price = int(data[3])
            else:
                price = data[3]

            self.__log.d('$$$ send ', data[0], ' order symbol=', data[1].symbol, ' side=', side, ' price=', price,
                         ' quantity=', quantity, ' position=', longShort)
            print('$$$ send ', data[0], ' order symbol=', data[1].symbol, ' side=', side, ' price=', price,
                  ' quantity=', quantity, ' position=', longShort)
            if quantity <= 0:
                print('quantity is less then zero')

            try:
                result = self.__request_client.post_order(
                    symbol=data[1].symbol, side=side, ordertype=OrderType.LIMIT, timeInForce="GTC",
                    price=str(price), quantity=str(quantity), positionSide=longShort)
                self.__log.d('open order result = ', result)
            except Exception as e:
                self.__log.d(e)
        else:
            if side == 'BUY':
                side = 'SELL'
            else:
                side = 'BUY'

            try:
                self.__log.d('$$$ send close order symbol=', data[1].symbol, ' side=', data[2], ' price=', data[3],
                             ' quantity=', quantity, ' stopPrice=', data[5])
                if orderType is None:
                    orderType = OrderType.TAKE_PROFIT

                if orderType == OrderType.LIMIT:
                    result = self.__request_client.post_order(
                        symbol=data[1].symbol, side=side, ordertype=orderType, timeInForce="GTC",
                        price=str(data[3]), quantity=str(quantity), closePosition=False, positionSide=longShort)
                else:
                    result = self.__request_client.post_order(
                        symbol=data[1].symbol, side=side, ordertype=orderType, timeInForce="GTC",
                        stopPrice=str(data[5]), price=str(data[3]), quantity=str(quantity), closePosition=False,
                        positionSide=longShort)
                    self.__log.d('close order result = ', result)
            except Exception as e:
                self.__log.d(e)
        return result

    def getRecentTradesList(self, symbol, count):
        result = None
        self.__log.d('getRecentTradesList ', symbol)
        try:
            result = self.__request_client.get_recent_trades_list(symbol=symbol, limit=count)
        except Exception as e:
            self.__log.d('getRecentTradesList e=', e)
            time.sleep(1)
        return result

    def getOpenOrders(self, symbol):
        self.__log.d('getOpenOrders ', symbol)
        result = None
        try:
            result = self.__request_client.get_open_orders(symbol=symbol)
        except Exception as e:
            self.__log.d(e)
            time.sleep(5)
        return result

    def getOrder(self, symbol, orderId, clientId):
        self.__log.d('getOpenOrders ', symbol)
        result = self.__request_client.get_order(symbol=symbol, orderId=orderId, origClientOrderId=clientId)
        return result

    def cancelAllOrders(self, symbol):
        self.__log.d('cancelAllOrders ', symbol)
        result = self.__request_client.cancel_all_orders(symbol=symbol)
        return result

    def changeMarginType(self, symbol):
        self.__log.d('changeMarginType ', symbol)
        result = self.__request_client.change_margin_type(symbol=symbol, marginType="CROSSED")
        return result

    def getAccountTrades(self, symbol, limitCnt):
        self.__log.d('changeMarginType ', symbol)
        result = self.__request_client.get_account_trades(symbol=symbol, limit=limitCnt)
        return result

    def fetch1MinCandle(self, symbol, sTime, limit):
        try:
            result = self.__request_client.get_candlestick_data(symbol=symbol, interval=self.__getInterval(1),
                                                                startTime=sTime, endTime=None, limit=limit)
            return result
        except Exception as e:
            self.__log.d(e)
            return None

    def fetch3MinCandle(self, symbol, sTime, limit):
        try:
            result = self.__request_client.get_candlestick_data(symbol=symbol, interval=self.__getInterval(3),
                                                                startTime=sTime, endTime=None, limit=limit)
            return result
        except Exception as e:
            self.__log.d(e)
            return None

    def fetch5MinCandle(self, symbol, sTime, limit):
        try:
            result = self.__request_client.get_candlestick_data(symbol=symbol, interval=self.__getInterval(5),
                                                                startTime=sTime, endTime=None, limit=limit)
            return result
        except Exception as e:
            self.__log.d(e)
            return None

    def fetch15MinCandle(self, symbol, sTime, limit):
        try:
            result = self.__request_client.get_candlestick_data(symbol=symbol, interval=self.__getInterval(15),
                                                                startTime=sTime, endTime=None, limit=limit)
            return result
        except Exception as e:
            self.__log.d(e)
            return None

    def fetch30MinCandle(self, symbol, sTime, limit):
        try:
            result = self.__request_client.get_candlestick_data(symbol=symbol, interval=self.__getInterval(30),
                                                                startTime=sTime, endTime=None, limit=limit)
            return result
        except Exception as e:
            self.__log.d(e)
            return None

    def fetch60MinCandle(self, symbol, sTime, limit):
        try:
            result = self.__request_client.get_candlestick_data(symbol=symbol, interval=self.__getInterval(60),
                                                                startTime=sTime, endTime=None, limit=limit)
            return result
        except Exception as e:
            self.__log.d(e)
            return None

    def fetch4HourCandle(self, symbol, sTime, limit):
        try:
            result = self.__request_client.get_candlestick_data(symbol=symbol, interval=self.__getInterval(240),
                                                                startTime=sTime, endTime=None, limit=limit)
            return result
        except Exception as e:
            self.__log.d(e)
            return None

    @staticmethod
    def validSymbol(symbol):
        if symbol == 'BTCBUSD' or symbol == 'BTCUSDT':
            return False
        return True

    def getFundingRate(self, symbol, sTime, eTime):
        try:
            result = self.__request_client.get_funding_rate(symbol=symbol, startTime=sTime, endTime=eTime, limit=None)
            return result
        except Exception as e:
            self.__log.d(e)
            return None

    def getMarkPrice(self, symbol):
        try:
            result = self.__request_client.get_mark_price(symbol=symbol)
            return result
        except Exception as e:
            self.__log.d(e)
            return None
