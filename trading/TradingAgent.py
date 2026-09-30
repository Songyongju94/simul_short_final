import time
import numpy
import math
import sys
import gc

from datetime import datetime
from kowanasutil import Log, Config, KowanasTime
from trading.TradingCenterFactory import TradingCenterFactory
from model.CandleResultRepository import CandleResultRepository
from model.CandleBuyResultRepository import CandleBuyResultRepository
from model.CandleSellResultRepository import CandleSellResultRepository
from model.CandleListRepository import CandleListRepository
from model.CandleCompleteListRepository import CandleCompleteListRepository
from model.CandleHighestLowestListRepository import CandleHighestLowestListRepository
from model.SettingRepository import SettingRepository
from model.DeviceRepository import DeviceRepository
from trading.CandleAdapter import CandleAdapter
from trading.CandleResultAdapter import CandleResultAdapter
from trading.TradeInfoAdapter import TradeInfoAdapter
from trading.CandleSellResultAdapter import CandleSellResultAdapter
from Definition import Definition


def isValidCurrency(group, currSymbol):
    symbol = currSymbol.replace('USDT', '')
    if group == 1 or group == 2 or group == 3:  # SHORT ONLY
        if symbol == '1000XEC' or symbol == 'ANKR' or symbol == 'AR' or symbol == 'ATA' or symbol == 'BAL' \
                or symbol == 'BTS' or symbol == 'CTK' or symbol == 'CTSI' or symbol == 'CVC' or symbol == 'DGB' \
                or symbol == 'GAL' or symbol == 'GMT' or symbol == 'GTC' or symbol == 'HBAR' or symbol == 'HNT' \
                or symbol == 'ICX' or symbol == 'IMX' or symbol == 'IOST' or symbol == 'KAVA' or symbol == 'KNC' \
                or symbol == 'KSM' or symbol == 'LINA' or symbol == 'MASK' or symbol == 'OMG' or symbol == 'OP' \
                or symbol == 'PEOPLE' or symbol == 'SKL' or symbol == 'STORJ' or symbol == 'TOMO' or symbol == 'TRB' \
                or symbol == 'TRX' or symbol == 'WAVES' or symbol == 'XTZ' or symbol == 'ZRX':
            return True
    elif group == 4 or group == 5 or group == 6:
        if symbol == 'ANKR' or symbol == 'ANT' or symbol == 'AR' or symbol == 'BEL' or symbol == 'BTS' \
                or symbol == 'C98' or symbol == 'COTI' or symbol == 'CTK' or symbol == 'CTSI' or symbol == 'CVC' \
                or symbol == 'DUSK' or symbol == 'DYDX' or symbol == 'GMT' or symbol == 'GTC' or symbol == 'HNT' \
                or symbol == 'ICX' or symbol == 'IMX' or symbol == 'IOTX' or symbol == 'JASMY' or symbol == 'KAVA' \
                or symbol == 'KNC' or symbol == 'LINA' or symbol == 'LPT' or symbol == 'MASK' or symbol == 'MKR' \
                or symbol == 'NKN' or symbol == 'OP' or symbol == 'PEOPLE' or symbol == 'SKL' or symbol == 'STMX' \
                or symbol == 'STORJ' or symbol == 'WAVES' or symbol == 'WOO' or symbol == 'ZRX':
            return True
    elif group == 7 or group == 8:
        if symbol == '1INCH' or symbol == 'ALGO' or symbol == 'ANKR' or symbol == 'AR' or symbol == 'ATOM' \
                or symbol == 'BAND' or symbol == 'CHR' or symbol == 'COTI' or symbol == 'CTK' or symbol == 'CTSI' \
                or symbol == 'CVC' or symbol == 'DYDX' or symbol == 'ENS' or symbol == 'FLM' or symbol == 'GMT' \
                or symbol == 'HNT' or symbol == 'IOST' or symbol == 'IOTX' or symbol == 'KAVA' or symbol == 'KNC' \
                or symbol == 'LINA' or symbol == 'LIT' or symbol == 'LPT' or symbol == 'MKR' or symbol == 'MTL' \
                or symbol == 'OMG' or symbol == 'ONT' or symbol == 'OP' or symbol == 'ROSE' or symbol == 'THETA' \
                or symbol == 'TOMO' or symbol == 'WAVES' or symbol == 'WOO' or symbol == 'XEM':
            return True
    elif group == 9 or group == 10:
        if symbol == '1000XEC' or symbol == 'ANKR' or symbol == 'ANT' or symbol == 'APE' or symbol == 'API3' \
                or symbol == 'ATOM' or symbol == 'AVAX' or symbol == 'BAL' or symbol == 'BEL' or symbol == 'CELO' \
                or symbol == 'CTSI' or symbol == 'DGB' or symbol == 'GAL' or symbol == 'GRT' or symbol == 'GTC' \
                or symbol == 'IMX' or symbol == 'JASMY' or symbol == 'KAVA' or symbol == 'KNC' or symbol == 'KSM' \
                or symbol == 'LIT' or symbol == 'LPT' or symbol == 'MTL' or symbol == 'NEO' or symbol == 'OMG' \
                or symbol == 'ONT' or symbol == 'SKL' or symbol == 'SNX' or symbol == 'TOMO' or symbol == 'TRB' \
                or symbol == 'TRX' or symbol == 'WOO' or symbol == 'XEM' or symbol == 'ZRX':
            return True
    elif group == 11:
        if symbol == '1INCH' or symbol == 'ANKR' or symbol == 'AR' or symbol == 'ATA' or symbol == 'AVAX' \
                or symbol == 'BAKE' or symbol == 'BAND' or symbol == 'BAT' or symbol == 'CHR' or symbol == 'DGB' \
                or symbol == 'DUSK' or symbol == 'DYDX' or symbol == 'GAL' or symbol == 'GMT' or symbol == 'HNT' \
                or symbol == 'ICX' or symbol == 'IOST' or symbol == 'IOTX' or symbol == 'JASMY' or symbol == 'KLAY' \
                or symbol == 'KSM' or symbol == 'LINA' or symbol == 'LPT' or symbol == 'MKR' or symbol == 'NEAR' \
                or symbol == 'NKN' or symbol == 'OCEAN' or symbol == 'OMG' or symbol == 'ONE' or symbol == 'SNX' \
                or symbol == 'STMX' or symbol == 'STORJ' or symbol == 'SUSHI' or symbol == 'TOMO' or symbol == 'WOO':
            return True
    elif group == 99:  # based on old version
        if symbol == 'ZRX' or symbol == '1000XEC' or symbol == 'KNC' or symbol == 'MASK' or symbol == 'SNX' \
                or symbol == 'XTZ' or symbol == 'SUSHI' or symbol == 'NKN' or symbol == 'CELO' or symbol == 'TOMO' \
                or symbol == 'CVC' or symbol == 'IMX' or symbol == 'KSM' or symbol == 'XEM' or symbol == 'DGB' \
                or symbol == 'CTK' or symbol == 'ATOM' or symbol == 'COMP' or symbol == 'MKR' or symbol == 'ANKR' \
                or symbol == 'OCEAN' or symbol == 'CTSI' or symbol == 'SKL' or symbol == 'ANT' \
                or symbol == 'GMT' or symbol == 'C98' or symbol == 'ALICE' or symbol == 'AR' \
                or symbol == 'GAL' or symbol == 'TRB' or symbol == 'GTC' or symbol == 'STMX' or symbol == 'ONT' \
                or symbol == 'OGN' or symbol == 'API3' or symbol == 'HBAR' or symbol == 'EOS' or symbol == 'LPT' \
                or symbol == 'STORJ' or symbol == 'RSR' or symbol == 'BAND' or symbol == 'OP':
            return True
    elif group == 101:  # based on old version
        if symbol == '1000XEC' or symbol == 'ANT' or symbol == 'API3' or symbol == 'AR' or symbol == 'BAND' \
                or symbol == 'C98' or symbol == 'CELO' or symbol == 'COMP' or symbol == 'CTK' or symbol == 'CVC' \
                or symbol == 'DGB' or symbol == 'GMT' or symbol == 'GTC' or symbol == 'HBAR' or symbol == 'IMX' \
                or symbol == 'KNC' or symbol == 'KSM' or symbol == 'LPT' or symbol == 'MASK' or symbol == 'NKN' \
                or symbol == 'OCEAN' or symbol == 'OGN' or symbol == 'OP' or symbol == 'RSR' or symbol == 'SKL' \
                or symbol == 'SNX' or symbol == 'STMX' or symbol == 'MKR' or symbol == 'SUSHI' or symbol == 'TOMO' \
                or symbol == 'TRB' or symbol == 'XEM' or symbol == 'XTZ' or symbol == 'ZRX':
            return True
    elif group == 0:  # based on old version
        if symbol == 'BTCST':
            return False
        return True
    else:
        # candidates :
        # MTL
        # AAVE
        # SKL
        # SAND
        # CHZ
        # BAKE
        # C98
        # LRC
        # DASH
        # ICP
        # AXS
        # LINK
        # XTZ
        # CRV
        # REEF
        print(symbol, ' discard')
    return False

def getBuyRateBySymbol(group, sym, defaultRate):
    symbol = sym.replace('USDT', '')
    if group == 1:  # G1 - Base 1.1
        if symbol == 'ANKR' or symbol == 'AR' or symbol == 'CTSI':
            return 0.8
        elif symbol == 'TRB':
            return 1.0
        elif symbol == 'MASK' or symbol == 'XTZ':
            return 1.4
        elif symbol == 'GAL':
            return 1.6
        elif symbol == 'ICX' or symbol == 'KSM' or symbol == 'LINA' or symbol == 'OMG' or symbol == 'WAVES' \
                or symbol == 'ZRX':
            return 1.7
        elif symbol == 'TRX':
            return 1.9
    elif group == 2:  # G2 - Base 1.2
        if symbol == 'ANKR' or symbol == 'AR' or symbol == 'CTSI':
            return 0.9
        elif symbol == 'XTZ':
            return 1.6
        elif symbol == 'GAL':
            return 1.7
        elif symbol == 'ICX' or symbol == 'KSM' or symbol == 'LINA' or symbol == 'OMG' or symbol == 'WAVES' \
                or symbol == 'ZRX':
            return 1.8
        elif symbol == 'TRX':
            return 2
    elif group == 3:  # G3 - Base 1.3
        if symbol == 'ANKR' or symbol == 'CTSI' or symbol == 'AR' or symbol == 'HBAR' or symbol == 'OP':
            return 1
        elif symbol == 'GAL':
            return 1.8
        elif symbol == 'ICX' or symbol == 'KSM' or symbol == 'LINA' or symbol == 'OMG' or symbol == 'WAVES' \
                or symbol == 'ZRX':
            return 1.9
        elif symbol == 'TRX':
            return 2.5
    elif group == 4:  # G4 - Base 1.4
        if symbol == 'ANT' or symbol == 'C98' or symbol == 'CTK' or symbol == 'DUSK' or symbol == 'GTC' \
                or symbol == 'IOTX' or symbol == 'MASK' or symbol == 'STMX' or symbol == 'STORJ' or symbol == 'WOO':
            return 0.8
        elif symbol == 'JASMY':
            return 1.7
        elif symbol == 'BEL' or symbol == 'COTI':
            return 1.8
    elif group == 5:  # G5 - Base 1.5
        if symbol == 'ANT' or symbol == 'MASK' or symbol == 'STMX' or symbol == 'STORJ' or symbol == 'WOO' \
                or symbol == 'C98' or symbol == 'CTK' or symbol == 'DUSK' or symbol == 'GTC' or symbol == 'IOTX':
            return 0.9
        elif symbol == 'JASMY':
            return 1.8
        elif symbol == 'BEL' or symbol == 'COTI':
            return 1.9
    elif group == 6:  # G6 - Base 1.6
        if symbol == 'ANT' or symbol == 'C98' or symbol == 'CTK' or symbol == 'DUSK' or symbol == 'GTC' \
                or symbol == 'IOTX' or symbol == 'MASK' or symbol == 'STMX' or symbol == 'STORJ' or symbol == 'WOO':
            return 1
        elif symbol == 'JASMY':
            return 1.9
        elif symbol == 'BEL' or symbol == 'COTI':
            return 2
    elif group == 7:  # G7 - Base 1.7
        if symbol == 'KNC' or symbol == 'HNT':
            return 0.8
        elif symbol == 'ALGO' or symbol == 'THETA' or symbol == 'MTL':
            return 1.1
        elif symbol == 'LINA':
            return 1.2
        elif symbol == 'ROSE':
            return 1.3
        elif symbol == 'IOST' or symbol == 'CTK':
            return 1.4
        elif symbol == 'LIT' or symbol == 'OMG':
            return 1.5
        elif symbol == '1INCH' or symbol == 'AR' or symbol == 'BAND' or symbol == 'KAVA':
            return 1.9
        elif symbol == 'OP' or symbol == 'WAVES':
            return 2
        elif symbol == 'XEM':
            return 2.5
    elif group == 8:  # G8 - Base 1.8
        if symbol == 'GMT' or symbol == 'HNT':
            return 0.9
        elif symbol == 'MTL' or symbol == 'ALGO' or symbol == 'THETA':
            return 1.2
        elif symbol == 'ONT' or symbol == 'LINA':
            return 1.3
        elif symbol == 'FLM':
            return 1.4
        elif symbol == 'CTK' or symbol == 'IOST' or symbol == 'IOTX':
            return 1.5
        elif symbol == 'CHR' or symbol == 'COTI' or symbol == 'ENS' or symbol == 'OMG' or symbol == 'WOO':
            return 1.6
        elif symbol == 'BAND' or symbol == 'KNC':
            return 2
        elif symbol == 'WAVES':
            return 2.5
    elif group == 9:  # G9 - Base 1.0
        if symbol == 'WOO':
            return 1.1
        elif symbol == 'ANKR' or symbol == 'ATOM' or symbol == 'CTSI' or symbol == 'LPT' or symbol == 'MTL' \
                or symbol == 'ZRX':
            return 1.3
        elif symbol == 'APE' or symbol == 'AVAX' or symbol == 'GTC' or symbol == 'LIT':
            return 1.4
        elif symbol == 'KSM' or symbol == 'GAL' or symbol == 'NEO' or symbol == 'TRX':
            return 1.5
        elif symbol == 'ANT' or symbol == 'ONT':
            return 1.6
        elif symbol == 'XEM':
            return 1.9
        elif symbol == 'BEL' or symbol == 'GRT' or symbol == 'TRB':
            return 2.5
    elif group == 10:  # G10 - Base 1.2
        if symbol == '1000XEC' or symbol == 'DGB':
            return 0.8
        elif symbol == 'IMX' or symbol == 'JASMY' or symbol == 'KNC' or symbol == 'SKL':
            return 0.9
        elif symbol == 'API3' or symbol == 'CELO' or symbol == 'SNX':
            return 1.1
        elif symbol == 'OMG':
            return 1.3
        elif symbol == 'TOMO':
            return 1.4
        elif symbol == 'BAL' or symbol == 'GTC':
            return 1.5
        elif symbol == 'AVAX' or symbol == 'KSM':
            return 1.6
        elif symbol == 'APE' or symbol == 'KAVA' or symbol == 'ZRX':
            return 2
        elif symbol == 'BEL' or symbol == 'GRT' or symbol == 'MTL' or symbol == 'ONT' or symbol == 'TRB' \
                or symbol == 'TRX' or symbol == 'XEM':
            return 3
    elif group == 11:  # G11 - Base 1.2
        if symbol == 'GMT' or symbol == 'LPT':
            return 0.8
        elif symbol == 'ONE':
            return 0.9
        elif symbol == 'HNT' or symbol == 'BAT' or symbol == 'IOST':
            return 1
        elif symbol == 'DUSK':
            return 1.1
        elif symbol == 'IOTX':
            return 1.2
        elif symbol == 'MKR':
            return 1.3
        elif symbol == 'DGB' or symbol == 'ATA' or symbol == 'OCEAN' or symbol == 'STORJ':
            return 1.4
        elif symbol == 'JASMY' or symbol == 'SNX' or symbol == 'SUSHI' or symbol == 'TOMO':
            return 1.6
        elif symbol == 'NKN':
            return 1.7
        elif symbol == 'AVAX' or symbol == 'BAKE' or symbol == 'WOO':
            return 1.9
        elif symbol == 'ANKR' or symbol == 'GAL' or symbol == 'ICX' or symbol == 'KSM' or symbol == 'OMG':
            return 2
        elif symbol == '1INCH' or symbol == 'AR' or symbol == 'LINA':
            return 2.5

    return defaultRate

class TradingAgent:
    def __init__(self, context, database_only=False):
        self.__log = Log()
        self.__app = context
        self.__definition = Definition()
        self.__config = Config(file=self.__definition.getConfig1())

        self.__min1DelayLogic = int(self.__config.configs.get('MIN1_DELAY_LOGIC'))
        self.__initialLeverage = int(self.__config.configs.get('INITIAL_LEVERAGE'))

        self.__singleBalance = float(self.__config.configs.get('SINGLE_BALANCE'))
        self.__baseTotalPrice = float(self.__config.configs.get('BASE_TOTAL_RRICE'))
        self.__candleInterval = int(self.__config.configs.get('CANDLE_INTERVAL'))
        self.__runningTR = int(self.__config.configs.get('RUNNING_TR')) + 1
        self.__bolUpBuyRate = float(self.__config.configs.get('BOL_UP_BUY_RATE'))
        self.__bolDownBuyRate = float(self.__config.configs.get('BOL_DOWN_BUY_RATE'))
        self.__duplicateForbidTime = int(self.__config.configs.get('DUPLICATE_FORBID_TIME'))
        self.__buyConditions = self.__config.configs.get('BUY_CONDITION')
        self.__sellConditions = self.__config.configs.get('SELL_CONDITIONS')
        self.__expireTimeToSell = int(self.__config.configs.get('EXPIRE_TIME_TO_SELL'))
        self.__dataPeriod = int(self.__config.configs.get('DATA_PERIOD'))
        self.__dataPeriodForSell = int(self.__config.configs.get('DATA_PERIOD_FOR_SELL'))
        self.__sleepCnt = int(self.__config.configs.get('SLEEP_CNT'))
        self.__sleepTime3 = int(self.__config.configs.get('SLEEP_TIME_3'))

        self.__lossSellFirst = int(self.__config.configs.get('LOSS_SELL_FIRST'))
        self.__sellCountPerInterval = int(self.__config.configs.get('SELL_COUNT_PER_INTERVAL'))

        self.__specificTime = int(self.__config.configs.get('SPECIFIC_TIME'))
        self.__specificEndTime = int(self.__config.configs.get('SPECIFIC_END_TIME'))
        self.__minimumBolTriggerRate = float(self.__config.configs.get('MINIMUM_BOL_TRIGGER_RATE'))
        self.__lossCutPercent = float(self.__config.configs.get('LOSS_CUT_PERCENT'))
        self.__trailingStopMargin = float(self.__config.configs.get('TRAILING_STOP_MARGIN'))
        self.__trailingStopStartFrom = float(self.__config.configs.get('TRAILING_STOP_START_FROM'))
        self.__trailingStopExpireTimeStop = int(self.__config.configs.get('TRAILING_STOP_EXPIRE_TIME_STOP'))
        self.__TrailingStopInterval = int(self.__config.configs.get('TRAILING_STOP_INTERVAL'))

        self.__TrailingStopLossCutSellEnable = int(self.__config.configs.get('TRAILING_STOP_LOSS_CUT_SELL_ENABLE'))
        self.__TrailingStopLossCutSellPercent = float(self.__config.configs.get('TRAILING_STOP_LOSS_CUT_SELL_PERCENT'))
        self.__TrailingStopLossCutSellInterval = int(self.__config.configs.get('TRAILING_STOP_LOSS_CUT_SELL_INTERVAL'))
        self.__TrailingStopLossCutSellAfterTime = int(
            self.__config.configs.get('TRAILING_STOP_LOSS_CUT_SELL_AFTER_TIME'))
        self.__currencyGroupNum = int(self.__config.configs.get('CURRENCY_GROUP_NUM'))

        self.__followLogicInterval = int(self.__config.configs.get('FOLLOW_LOGIC_INTERVAL'))
        self.__lossCutGapOnOff = int(self.__config.configs.get('LOSS_CUT_GAP_ON_OFF'))
        self.__lossCutBeforeHighMinTime = int(self.__config.configs.get('LOSS_CUT_BEFORE_HIGH_MIN_TIME'))
        self.__lossCutTouchMinTime = int(self.__config.configs.get('LOSS_CUT_TOUCH_MIN_TIME'))
        self.__lossCutGapPercent = float(self.__config.configs.get('LOSS_CUT_GAP_PERCENT'))
        self.__detailPercentForSell = int(self.__config.configs.get('DETAIL_PERCENT_FOR_SELL'))
        self.__debuggingMode = int(self.__config.configs.get('DEBUGGING_MODE'))
        self.__specificIndexTo = int(self.__config.configs.get('SPECIFIC_IDX_TO'))
        self.__specificIndexFrom = int(self.__config.configs.get('SPECIFIC_IDX_FROM'))
        self.__tradePermitSide = self.__config.configs.get('TRADE_PERMIT_SIDE')

        self.__lossCutRate = float(self.__config.configs.get('LOSS_CUT_RATE'))
        self.__lossCutMarketRate = int(self.__config.configs.get('LOSS_CUT_MARKET_RATE'))

        self.__followSellEnable = int(self.__config.configs.get('FOLLOW_SELL_ENABLE'))
        self.__followSellGapTime = int(self.__config.configs.get('FOLLOW_SELL_GAP_TIME'))
        self.__followSellGapPer = int(self.__config.configs.get('FOLLOW_SELL_GAP_PER'))

        self.__btcEthGradientEnable = int(self.__config.configs.get('BTC_ETH_GRADIENT_ENABLE'))
        self.__hour1BolDataEnable = int(self.__config.configs.get('HOUR1_BOL_DATA_ENABLE'))

        self.__safeLCEnable = int(self.__config.configs.get('SAFE_LC_ENABLE'))
        self.__safeLCPercent = float(self.__config.configs.get('SAFE_LC_PERCENT'))

        self.__fundingStartTime = int(self.__config.configs.get('FUNDING_START_TIME'))
        self.__fundingTriggerPer = float(self.__config.configs.get('FUNDING_TRIGGER_PER'))
        self.__fundingSellTime = int(self.__config.configs.get('FUNDING_SELL_TIME'))
        self.__fundingLCPercent = float(self.__config.configs.get('FUNDING_LC_PERCENT'))

        self.__highPerDataEnable = int(self.__config.configs.get('HIGH_PER_DATA_ENABLE'))

        self.__riskModeStartTime = int(self.__config.configs.get('RISK_MODE_START_TIME'))
        self.__riskModeDuration = int(self.__config.configs.get('RISK_MODE_DURATION'))
        self.__riskModeLossPrice = int(self.__config.configs.get('RISK_MODE_LOSS_PRICE'))
        self.__riskModePendingTime = int(self.__config.configs.get('RISK_MODE_PENDING_TIME'))

        self.__detectBolPercent = float(self.__config.configs.get('DETECT_BOL_PERCENT'))

        self.__triggerMTotalCnt = int(self.__config.configs.get('TRIGGER_M_TOTAL_CNT'))

        self.__triggerM1 = float(self.__config.configs.get('TRIGGER_M1'))
        self.__triggerM2 = float(self.__config.configs.get('TRIGGER_M2'))
        self.__triggerM3 = float(self.__config.configs.get('TRIGGER_M3'))

        self.__trigger1 = float(self.__config.configs.get('TRIGGER_1'))
        self.__trigger2 = float(self.__config.configs.get('TRIGGER_2'))
        self.__trigger3 = float(self.__config.configs.get('TRIGGER_3'))
        self.__trigger4 = float(self.__config.configs.get('TRIGGER_4'))
        self.__trigger5 = float(self.__config.configs.get('TRIGGER_5'))
        self.__trigger6 = float(self.__config.configs.get('TRIGGER_6'))
        self.__trigger7 = float(self.__config.configs.get('TRIGGER_7'))
        self.__trigger8 = float(self.__config.configs.get('TRIGGER_8'))
        self.__trigger9 = float(self.__config.configs.get('TRIGGER_9'))
        self.__trigger10 = float(self.__config.configs.get('TRIGGER_10'))
        self.__trigger11 = float(self.__config.configs.get('TRIGGER_11'))
        self.__trigger12 = float(self.__config.configs.get('TRIGGER_12'))
        self.__trigger13 = float(self.__config.configs.get('TRIGGER_13'))
        self.__trigger14 = float(self.__config.configs.get('TRIGGER_14'))
        self.__trigger15 = float(self.__config.configs.get('TRIGGER_15'))
        self.__trigger16 = float(self.__config.configs.get('TRIGGER_16'))
        self.__trigger17 = float(self.__config.configs.get('TRIGGER_17'))
        self.__trigger18 = float(self.__config.configs.get('TRIGGER_18'))
        self.__trigger19 = float(self.__config.configs.get('TRIGGER_19'))

        self.__checkMin5CandleCnt = int(self.__config.configs.get('CHECK_MIN5_CANDLE_CNT'))

        self.__btcdomEnable = int(self.__config.configs.get('BTCDOM_ENABLE'))
        self.__btcdomPeriod = int(self.__config.configs.get('BTCDOM_PERIOD'))
        self.__btcdomPercent = int(self.__config.configs.get('BTCDOM_PERCENT'))
        self.__bolUpBuyLRate = float(self.__config.configs.get('BOL_UP_BUY_L_RATE'))
        self.__detectBolLPercent = float(self.__config.configs.get('DETECT_BOL_L_PERCENT'))
        self.__triggerL1 = float(self.__config.configs.get('TRIGGER_L_1'))
        self.__triggerL2 = float(self.__config.configs.get('TRIGGER_L_2'))
        self.__triggerL3 = float(self.__config.configs.get('TRIGGER_L_3'))
        self.__triggerL4 = float(self.__config.configs.get('TRIGGER_L_4'))
        self.__triggerL5 = float(self.__config.configs.get('TRIGGER_L_5'))
        self.__triggerL6 = float(self.__config.configs.get('TRIGGER_L_6'))
        self.__triggerL7 = float(self.__config.configs.get('TRIGGER_L_7'))
        self.__triggerL8 = float(self.__config.configs.get('TRIGGER_L_8'))
        self.__triggerL9 = float(self.__config.configs.get('TRIGGER_L_9'))

        self.__beforeHour = int(self.__config.configs.get('BEFORE_HOUR'))
        self.__afterHour = int(self.__config.configs.get('AFTER_HOUR'))

        self.__secondAddBuyEnable = int(self.__config.configs.get('SECOND_ADD_BUY_ENABLE'))
        self.__secondAddBuyProfit = float(self.__config.configs.get('SECOND_ADD_BUY_PROFIT'))
        self.__secondAddBuyBalance = int(self.__config.configs.get('SECOND_ADD_BUY_BALANCE'))
        self.__secondAddBuyMaxPrice = int(self.__config.configs.get('SECOND_ADD_BUY_MAX_PRICE'))
        self.__secondAddBuySellTime = int(self.__config.configs.get('SECOND_ADD_BUY_SELL_TIME'))
        self.__secondAddBuySellStart = int(self.__config.configs.get('SECOND_ADD_BUY_SELL_START'))
        self.__secondAddBuyLossCut = int(self.__config.configs.get('SECOND_ADD_BUY_LOSS_CUT'))

        self.__sellTrailingStopEnable = int(self.__config.configs.get('SELL_TRAILING_STOP_ENABLE'))
        self.__sellTrailingStopMode = self.__config.configs.get('SELL_TRAILING_STOP_MODE')
        self.__sellTrailingStopPer = int(self.__config.configs.get('SELL_TRAILING_STOP_PER'))
        self.__sellTrailingStopPer2nd = int(self.__config.configs.get('SELL_TRAILING_STOP_PER_2ND'))
        self.__sellTrailingStopTime = int(self.__config.configs.get('SELL_TRAILING_STOP_TIME'))
        self.__sellTrailingStopTime2nd = int(self.__config.configs.get('SELL_TRAILING_STOP_TIME_2ND'))
        self.__sellTrailingStop2ndSellInterval = int(self.__config.configs.get('SELL_TRAILING_STOP_2ND_SELL_INTERVAL'))
        self.__sellTrailingStopLC = int(self.__config.configs.get('SELL_TRAILING_STOP_LC'))
        self.__sellTrailingFundingEnable = int(self.__config.configs.get('SELL_TRAILING_STOP_FUNDING_ENABLE'))
        self.__sellTrailingStopPlusEnable = int(self.__config.configs.get('SELL_TRAILING_STOP_PLUS_ENABLE'))
        self.__sellTrailingStopPlusSellPer = float(self.__config.configs.get('SELL_TRAILING_STOP_PLUS_SELL_PER'))

        self.__tradingFee = float(self.__config.configs.get('TRADING_FEE'))

        dbConnection = self.__app.connectDB()
        self.__rsiDbConnection = dbConnection
        self.__deviceRepository = DeviceRepository(dbConnection)
        self.__settingRepository = SettingRepository(dbConnection)
        self.__candleListRepository = CandleListRepository(dbConnection)
        self.__candleResultRepository = CandleResultRepository(dbConnection)
        self.__candleBuyResultRepository = CandleBuyResultRepository(dbConnection, self.__debuggingMode)
        self.__candleSellResultRepository = CandleSellResultRepository(dbConnection, self.__sellConditions,
                                                                       self.__detailPercentForSell)
        self.__candleHighestLowestListRepository = CandleHighestLowestListRepository(dbConnection)

        self.__candleCompleteListRepository = CandleCompleteListRepository(dbConnection)
        self.__tradingCenter = None if database_only else TradingCenterFactory.create('binance')
        self.__currencies = None
        self.__candles = None
        self.__fetchCandleCount = 0
        self.__previousBuyTime = 0
        self.__h1TotalPrice = self.__h2TotalPrice = self.__h3TotalPrice = self.__h6TotalPrice = self.__h12TotalPrice = \
            self.__h24TotalPrice = self.__h48TotalPrice = self.__m70TotalPrice = self.__m80TotalPrice = \
            self.__m90TotalPrice = self.__m100TotalPrice = self.__m110TotalPrice = self.__m130TotalPrice = \
            self.__m140TotalPrice = self.__m150TotalPrice = self.__m160TotalPrice = self.__m170TotalPrice = \
            self.__m10TotalPrice = self.__m20TotalPrice = self.__m30TotalPrice = self.__m40TotalPrice = \
            self.__m50TotalPrice = self.__per01TotalPrice = self.__per02TotalPrice = self.__per03TotalPrice = \
            self.__per04TotalPrice = self.__per05TotalPrice = self.__per06TotalPrice = self.__per07TotalPrice = \
            self.__per08TotalPrice = self.__per09TotalPrice = self.__per1TotalPrice = self.__per11TotalPrice = \
            self.__per12TotalPrice = self.__per13TotalPrice = self.__per14TotalPrice = self.__per15TotalPrice = \
            self.__per2TotalPrice = self.__per3TotalPrice = \
            self.__per4TotalPrice = self.__per5TotalPrice = self.__per6TotalPrice = self.__per7TotalPrice = \
            self.__per8TotalPrice = self.__per9TotalPrice = self.__per10TotalPrice = self.__per200TotalPrice = \
            self.__baseTotalPrice
        self.totalProfitPercent = self.totalPrice = self.totalPriceLC = 0
        self.shortTermLossCutTotalCnt = 0
        self.addBuyCnt = 0
        self.addSellCnt = 0

    def changeInitialSettings(self):
        print('finished InitialSettings')

    def setInitialMarginType(self):
        print('change setInitialMarginType')

    def fetchCurrency(self):
        print('fetch currency')
        self.__currencies = self.__tradingCenter.fetchCurrency()
        if self.__currencyGroupNum == 0:
            # for i in range(len(self.__currencies) - self.__runningTR):
            #     del self.__currencies[self.__runningTR]
            idx = 0
            i = 0
            for currency in self.__currencies[:]:
                if currency.symbol.endswith('BUSD'):
                    del self.__currencies[idx]
                    continue
                if currency.symbol.endswith('USDC'):
                    del self.__currencies[idx]
                    continue
                if currency.symbol.endswith('ETHBTC'):
                    del self.__currencies[idx]
                    continue
                if currency.symbol.find('_') != -1:
                    del self.__currencies[idx]
                    continue
                if not isValidCurrency(self.__currencyGroupNum, currency.symbol):
                    del self.__currencies[i]
                    continue
                if currency.pricePrecision == -1:
                    del self.__currencies[i]
                    continue
                i += 1
                idx += 1
            self.__currencies = sorted(self.__currencies, key=lambda x: x.symbol)
            self.__log.d('currency len=', len(self.__currencies))
        else:
            i = 0
            for currency in self.__currencies[:]:
                if not isValidCurrency(self.__currencyGroupNum, currency.symbol):
                    del self.__currencies[i]
                    continue
                i += 1
        self.__log.d('fetchCurrency() finished')


    def getStopSymbolInfoFromBuy(self):
        values = self.__candleBuyResultRepository.getSymbolInfo()
        return values

    # Test No 9
    def runTest(self):
        startTime = (round(time.time()) - 31536000 * 10) * 1000
        try:
            values = self.__tradingCenter.getCandlestickData('BTCUSDT', 60, 130, startTime)
            self.__log.d(values)
        except Exception as e:
            self.__log.d('zzz exception')
            self.__log.d(str(e))
        return True

    # Test No 14
    def runRiskMode(self):
        # get sellData for adding cache
        sellCacheData = self.__candleSellResultRepository.readRiskModeCandleSellResultList()
        endTime = sellCacheData[-1][5]
        baseTime = self.__riskModeStartTime + self.__riskModeDuration
        totalCnt = len(sellCacheData)
        suspendTime = 0
        lockStatus = False
        lockTime = 0
        last_idx = 0
        while baseTime < endTime:
            index = 0
            lossPrice = float(0)
            fromBaseTimeStr = time.strftime('%Y-%m-%d %H:%M', time.localtime(baseTime - self.__riskModeDuration))
            baseTimeStr = time.strftime('%Y-%m-%d %H:%M', time.localtime(baseTime))
            self.__log.d('check min ', fromBaseTimeStr, ' - ', baseTimeStr)
            self.__log.d('last index uid = ', sellCacheData[last_idx][0], ' index=', last_idx)
            if len(sellCacheData) > last_idx + 1:
                if sellCacheData[last_idx + 1][5] >= baseTime:
                    baseTime += 60
                    self.__log.d('ignore checking base=', baseTimeStr, ' buyTime=',
                                 sellCacheData[last_idx + 1][8], ' uid=', sellCacheData[last_idx + 1][0])
                    continue

            for sellInfo in sellCacheData[:]:
                uid = sellInfo[0]
                symbol = sellInfo[1]
                buyPrice = sellInfo[2]
                sellPrice = sellInfo[3]
                quantity = sellInfo[4]
                buyTime = sellInfo[5]
                sellTime = sellInfo[6]
                profitPrice = sellInfo[7]
                buyTimeStr = sellInfo[8]
                sellTimeStr = sellInfo[9]
                riskProfitPrice = sellInfo[10]

                closePrice = float(0)
                # if baseTime == 1641246420:
                #     self.__log.d(symbol, ' test')
                if sellTime <= (baseTime - self.__riskModeDuration):
                    self.__log.d(symbol, ' delete cache = ', index, ' uid=', uid, ' total = ', totalCnt)
                    # if uid == 20754:
                    #     self.__log.d(symbol, ' test')
                    if sellTime != sellCacheData[index][6]:
                        self.__log.d(symbol, ' fatal error')
                    del sellCacheData[index]
                    totalCnt -= 1
                    index -= 1
                elif buyTime < (baseTime - self.__riskModeDuration) < sellTime:
                    values_ = self.__tradingCenter.fetch1MinCandle(symbol, (baseTime - self.__riskModeDuration) * 1000,
                                                                   1)
                    if values_ is not None and len(values_) > 0:
                        openPrice = float(values_[0].open)
                        profit = (openPrice - sellPrice) * quantity
                        lossPrice += profit
                        self.__log.d(symbol, ' front uid=', uid, ' baseTime=', baseTime,
                                     ' profitPrice=', profitPrice, ' lossPrice=', lossPrice)
                elif (baseTime - self.__riskModeDuration) <= buyTime and sellTime <= baseTime:
                    lossPrice += profitPrice
                    self.__log.d(symbol, ' full uid=', uid, ' baseTime=', baseTime,
                                 ' full Profit Price=', profitPrice, ' lossPrice=', lossPrice)
                elif buyTime < baseTime < sellTime:
                    values_ = self.__tradingCenter.fetch1MinCandle(symbol, baseTime * 1000, 1)
                    if values_ is not None and len(values_) > 0:
                        closePrice = float(values_[0].close)
                        profit = (buyPrice - closePrice) * quantity
                        lossPrice += profit
                        self.__log.d(symbol, ' end uid=', uid, ' baseTime=', baseTime,
                                     ' profitPrice=', profitPrice, ' lossPrice=', lossPrice)
                elif buyTime >= baseTime:
                    self.__log.d(symbol, ' uid=', uid, ' buyTime > baseTime.. check over skip index=', index)
                    last_idx = index
                    break
                else:
                    self.__log.d(symbol, ' uid=', uid, ' baseTime=', baseTime, ' illegal case ###### ')

                index += 1

            self.__log.d('Total lossPrice = ', lossPrice, ' lockStatus=', lockStatus)
            # need to think more
            if lockStatus:
                if lossPrice > 0:
                    lockStatus = False
                    lockTime = 0
                    self.__log.d(' unlocked lossPrice=', lossPrice)
                else:
                    riskLockTimeStr = time.strftime('%Y-%m-%d %H:%M', time.localtime(lockTime))
                    self.__log.d(' lock status lossPrice=', lossPrice, ' lockTime=', riskLockTimeStr)
                    for sellInfo in sellCacheData[:]:
                        uid1 = sellInfo[0]
                        symbol1 = sellInfo[1]
                        buyPrice1 = sellInfo[2]
                        quantity1 = sellInfo[4]
                        buyTime1 = sellInfo[5]
                        sellTime1 = sellInfo[6]

                        if baseTime >= buyTime1 >= lockTime:
                            self.__log.d(symbol1, ' Suspending status delete uid1=', uid1, ' total = ', totalCnt,
                                         ' baseTime=', baseTime, ' buyTime=', buyTime1, ' lockTime=', lockTime)
                            self.__candleSellResultRepository.updateRiskModeCandleSellResultList(uid1, 2, 0,
                                                                                                 riskLockTimeStr)
                            self.__candleSellResultRepository.commit()
                            continue
                        elif buyTime1 > baseTime:
                            break
                        else:
                            self.__log.d(symbol1, ' ignore case')
            elif not lockStatus and lossPrice < self.__riskModeLossPrice:
                lockStatus = True
                lockTime = baseTime
                # update profit Price
                for sellInfo in sellCacheData[:]:
                    uid2 = sellInfo[0]
                    symbol2 = sellInfo[1]
                    buyPrice2 = sellInfo[2]
                    quantity2 = sellInfo[4]
                    buyTime2 = sellInfo[5]
                    sellTime2 = sellInfo[6]

                    if buyTime2 < lockTime < sellTime2:
                        values_ = self.__tradingCenter.fetch1MinCandle(symbol2, lockTime * 1000, 1)
                        closePrice2 = float(values_[0].close)
                        profit2 = (buyPrice2 - closePrice2) * quantity2
                        self.__log.d(symbol2, ' update sellInfo uid=', uid2, ' updateProfit=', profit2)
                        riskLockTimeStr = time.strftime('%Y-%m-%d %H:%M', time.localtime(lockTime))
                        self.__candleSellResultRepository.updateRiskModeCandleSellResultList(uid2, 1, profit2,
                                                                                             riskLockTimeStr)
                        self.__candleSellResultRepository.commit()
                    elif buyTime2 >= lockTime:
                        self.__log.d(symbol2, ' buyTime2 >= lockTime buyTime=', buyTime2, ' lockTime=', lockTime)
                        break
                    else:
                        self.__log.d('Ignore keep uid=', uid2)
            baseTime += 60

    # Test No 15
    def runRemoveCandleByBuyResult(self):
        idx = 0
        #startSymbol = None
        startSymbol = 'LAUSDT'
        for currency in self.__currencies:
            # if currency.symbol != 'BNXUSDT':
            #     continue
            
            if startSymbol is not None:
                if currency.symbol != startSymbol:
                    continue
                else:
                    startSymbol = None
                    
            values = self.__candleBuyResultRepository.readCandleBuyResultListDesc(currency.symbol)
            self.__log.d(currency.symbol, ' ---------- candle next ---------- index = ', idx)

            count = 0
            length = len(values)
            startTime = endTime = 0
            if length == 0:
                self.__candleListRepository.deleteCandleBySymbol(currency.symbol)
                self.__log.d(currency.symbol, ' delete candleList')
                self.__candleListRepository.commit()
                idx += 1
                continue

            for value in values:
                tradeInfo = TradeInfoAdapter.createFromBinance(value)
                if count == 0:
                    startTime = (tradeInfo.buyTime + 3600 * self.__afterHour)
                    endTime = (tradeInfo.buyTime + 3600 * 24 * 365)

                    sTimeString = time.strftime('%Y-%m-%d %H:%M', time.localtime(startTime))
                    eTimeString = time.strftime('%Y-%m-%d %H:%M', time.localtime(endTime))
                    bTimeString = time.strftime('%Y-%m-%d %H:%M', time.localtime(tradeInfo.buyTime))
                    self.__candleListRepository.deleteCandleBySymbolAndTime(currency.symbol,
                                                                            startTime * 1000, endTime * 1000)
                    self.__log.d('uid(', value[0], ') first next delete startTime=', sTimeString,
                                 ' endTime=', eTimeString, ' buyTime=', bTimeString)
                    if length == 1:
                        startTime = 0
                        endTime = tradeInfo.buyTime - 3600 * self.__beforeHour
                    else:
                        startTime = values[count + 1][14] + 3600 * self.__afterHour
                        endTime = tradeInfo.buyTime - 3600 * self.__beforeHour

                    sTimeString = time.strftime('%Y-%m-%d %H:%M', time.localtime(startTime))
                    eTimeString = time.strftime('%Y-%m-%d %H:%M', time.localtime(endTime))
                    bTimeString = time.strftime('%Y-%m-%d %H:%M', time.localtime(tradeInfo.buyTime))
                    self.__candleListRepository.deleteCandleBySymbolAndTime(currency.symbol,
                                                                            startTime * 1000, endTime * 1000)
                    self.__log.d('uid(', value[0], ') first next delete startTime=', sTimeString,
                                 ' endTime=', eTimeString, ' buyTime=', bTimeString)
                else:
                    if length > count + 1:
                        startTime = values[count + 1][14] + 3600 * self.__afterHour
                    else:
                        startTime = 0
                    endTime = tradeInfo.buyTime - 3600 * self.__beforeHour
                    self.__candleListRepository.deleteCandleBySymbolAndTime(currency.symbol,
                                                                            startTime * 1000, endTime * 1000)
                    sTimeString = time.strftime('%Y-%m-%d %H:%M', time.localtime(startTime))
                    eTimeString = time.strftime('%Y-%m-%d %H:%M', time.localtime(endTime))
                    bTimeString = time.strftime('%Y-%m-%d %H:%M', time.localtime(tradeInfo.buyTime))
                    self.__log.d('uid(', value[0], ') first next delete startTime=', sTimeString,
                                 ' endTime=', eTimeString, ' buyTime=', bTimeString)

                count += 1
            self.__candleListRepository.commit()
            gc.collect()
            idx += 1
        return

    # Test No 16
    def runHighestLowestData(self):
        now = KowanasTime.getKST()
        dateTime = now.strftime('%Y-%m-%d %H:%M')
        self.__log.d('*** runHighestLowestData start time = ', dateTime)
        self.__fetchCandleCount = 0
        limitNum = 1000
        currTime = round(time.time()) * 1000
        if self.__dataPeriod == 0:  # specific Time
            t365Time = self.__specificTime * 1000  # from 2 days before to today.
        elif self.__dataPeriod == 1:
            t365Time = 1567965420000  # 2019년 9월 9일 월요일 오전 2:57:00 GMT+09:00
        elif self.__dataPeriod == 2:  # 1 YEAR
            t365Time = 1609459200000  # from 2021/01/01 to 2021/12/31
            # t365Time = (round(time.time()) - 31536000) * 1000  # from 1 year before to today
        elif self.__dataPeriod == 3:  # 45 days
            t365Time = (round(time.time()) - 3888000) * 1000  # from 45 days before to today.
        elif self.__dataPeriod == 4:  # 31 days
            t365Time = (round(time.time()) - 2678400) * 1000  # from 31 days before to today.
        elif self.__dataPeriod == 5:  # 10 days
            t365Time = (round(time.time()) - 864000) * 1000  # from 10 days before to today.
        elif self.__dataPeriod == 6:  # 3 days
            t365Time = (round(time.time()) - 259200) * 1000  # from 3 days before to today.
        elif self.__dataPeriod == 7:  # 2 days
            t365Time = (round(time.time()) - 172800) * 1000  # from 2 days before to today.
        elif self.__dataPeriod == 8:  # 2 days
            t365Time = (round(time.time()) - 92400) * 1000  # from 1 day before to today(1day + 20 * 60(for bol)).
            # t365Time = (round(time.time()) - 619200) * 1000    # from 10 days before to today.

        startTime = t365Time - 3600000
        minuites = 1000
        try:
            count = 0
            self.__candleHighestLowestListRepository.cleanCandle()
            self.__candleHighestLowestListRepository.commit()
            for currency in self.__currencies:
                if count % 20 == 0:
                    self.__log.d('count = ', count)
                count += 1
                try:
                    values = self.__tradingCenter.getCandlestickData(currency.symbol, minuites, limitNum, startTime)
                except Exception as e:
                    self.__log.d('zzz exception')
                    self.__log.d(str(e))
                    values = self.__tradingCenter.getCandlestickData(currency.symbol, minuites, limitNum, startTime)
                # if currency.symbol == 'BTCUSDT':
                #     time_val = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(startTime / 1000))
                #     self.__log.d('Start Time = ', startTime, '   date = ', time_val)
                #     time.sleep(2)
                highest = 0
                highestWeek = None
                lowest = 10000000
                lowestWeek = None
                lunchingDate = None
                if values is not None and len(values) > 0:
                    lunchingDate = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(values[0].openTime / 1000
                                                                                     + 32400))
                for value in values:
                    high = float(value.high)
                    low = float(value.low)
                    if highest < high:
                        highest = high
                        highestWeek = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(value.openTime / 1000
                                                                                        + 32400))
                    if lowest > low:
                        lowest = low
                        lowestWeek = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(value.openTime / 1000
                                                                                       + 32400))
                currentPrice = float(values[-1].close)
                highRate = round(highest / currentPrice * 100, 2)
                lowRate = round(100 - lowest / currentPrice * 100, 2)
                lowRate = lowRate * -1
                data = [-1, currency.symbol, lunchingDate, dateTime, currentPrice,
                        highest, highestWeek, lowest, lowestWeek, highRate, lowRate]
                try:
                    self.__candleHighestLowestListRepository.addCandle(data)
                except Exception as e:
                    self.__log.d('666 exception')
                    self.__log.d(str(e))
                self.__candleHighestLowestListRepository.commit()
            now = KowanasTime.getKST()
            dateTime = now.strftime('%Y-%m-%d %H:%M')
            self.__log.d('*** success fetchCandle end time = ', dateTime)

        except Exception as e:
            self.__log.d(e)
            self.__log.d('888 exception')
            sys.exit(0)

    # Test No 1
    def fetchCandle(self, minuites):
        now = KowanasTime.getKST()
        dateTime = now.strftime('%Y-%m-%d %H:%M')
        self.__log.d('*** FetchCandle start time = ', dateTime)
        self.__fetchCandleCount = 0
        symbolLog = None
    
        limitNum = 0
        t3Time = (round(time.time()) - 10800) * 1000
        t24Time = (round(time.time()) - 86400) * 1000
        
        if self.__specificEndTime == 0:
          currTime = round(time.time()) * 1000
        else:
          currTime = self.__specificEndTime * 1000

        if self.__dataPeriod == 0:  # specific Time
            t365Time = self.__specificTime * 1000  # from 2 days before to today.
        elif self.__dataPeriod == 1:
            t365Time = 1567965420000  # 2019년 9월 9일 월요일 오전 2:57:00 GMT+09:00
        elif self.__dataPeriod == 2:  # 1 YEAR
            t365Time = 1609459200000  # from 2021/01/01 to 2021/12/31
            # t365Time = (round(time.time()) - 31536000) * 1000  # from 1 year before to today
        elif self.__dataPeriod == 3:  # 45 days
            t365Time = (round(time.time()) - 3888000) * 1000  # from 45 days before to today.
        elif self.__dataPeriod == 4:  # 31 days
            t365Time = (round(time.time()) - 2678400) * 1000  # from 31 days before to today.
        elif self.__dataPeriod == 5:  # 10 days
            t365Time = (round(time.time()) - 864000) * 1000  # from 10 days before to today.
        elif self.__dataPeriod == 6:  # 3 days
            t365Time = (round(time.time()) - 259200) * 1000  # from 3 days before to today.
        elif self.__dataPeriod == 7:  # 2 days
            t365Time = (round(time.time()) - 172800) * 1000  # from 2 days before to today.
        elif self.__dataPeriod == 8:  # 2 days
            t365Time = (round(time.time()) - 92400) * 1000  # from 1 day before to today(1day + 20 * 60(for bol)).
            # t365Time = (round(time.time()) - 619200) * 1000    # from 10 days before to today.

        h24 = 0
        startTime = t365Time - 3600000
        # Round up to a 5-minute boundary (epoch milliseconds).
        startTime = ((startTime + 300000 - 1) // 300000) * 300000
        try:
            self.__candleListRepository.cleanCandle()
            self.__candleListRepository.commit()
            if minuites == 5:
                limitNum = 1440
            elif minuites == 15:
                limitNum = 480
            elif minuites == 240:
                limitNum = 30
            else:
                limitNum = 120  # 5 days   60 mins

            while startTime <= currTime:
                count = 0
                candles = {}
                for currency in self.__currencies:
                    count += 1
                    symbolLog = currency.symbol
                    # if currency.symbol != 'BTCUSDT':
                    #     continue
                    try:
                        values = self.__tradingCenter.getCandlestickData(currency.symbol, minuites, limitNum, startTime)
                    except Exception as e:
                        self.__log.d('zzz exception')
                        self.__log.d(str(e))
                        values = self.__tradingCenter.getCandlestickData(currency.symbol, minuites, limitNum, startTime)
                    candles[currency.symbol] = []
                    if count == 1:
                        time_val = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(startTime / 1000))
                        time_val2 = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(currTime / 1000))                   
                        self.__log.d('Start Time = ', time_val, ' End Time = ', time_val2)
                        
                    if count % 20 == 0:
                        time.sleep(4)
                        self.__log.d('count = ', count)
                    idx = 0
                    for value in values:
                        candle = CandleAdapter.createFromBinance(value, 0)
                        if idx == 0:
                            if startTime != candle.candleTime:
                                self.__log.d(currency.symbol, ' wrong candle Time. Candle is not exist.. skip '
                                                              'startTime=', startTime, ' first =', candle.candleTime)
                                break
                        data = [-1, currency.symbol, candle.candleTime, candle.last, candle.high, candle.low,
                                candle.open, candle.close]
                        try:
                            self.__candleListRepository.addCandle(data)
                        except Exception as e:
                            self.__log.d('666 exception')
                            self.__log.d(str(e))
                        idx += 1
                # per 5 days
                startTime += (432000 * 1000)
                self.__candleListRepository.commit()
            now = KowanasTime.getKST()
            dateTime = now.strftime('%Y-%m-%d %H:%M')
            self.__log.d('*** success fetchCandle end time = ', dateTime)
        except Exception as e:
            self.__log.d(e)
            self.__log.d(symbolLog, ' 888 exception')
            sys.exit(0)
            
    def __calcBollinger(self, symbol, values, value5Min):
        data = [value.close for value in values]
        if value5Min != 0:
            data[19] = value5Min

        ma20 = numpy.mean(data)
        std = numpy.std(data)
        bolup = ma20 + std * 2
        boldown = ma20 - std * 2
        return bolup, ma20, boldown, data

    def __calcBollingerDown(self, data):
        ma20 = numpy.mean(data)
        std = numpy.std(data)
        bolup = ma20 + std * 2
        boldown = ma20 - std * 2
        return bolup, ma20, boldown

    # Test No 2
    def runSpikeCandle(self):
        candles = {}
        self.__candleResultRepository.cleanResultCandle()
        self.__candleResultRepository.commit()
        idx = 1
        for currency in self.__currencies:
            bolUpBuyRate_ = getBuyRateBySymbol(self.__currencyGroupNum, currency.symbol, self.__bolUpBuyRate)
            values = self.__candleListRepository.readCandleList(currency.symbol)
            candles[currency.symbol] = []
            for value in values:
                data = CandleResultAdapter.createFromBinance(value, 0)
                candles[currency.symbol].append(data)
            index = 19
            self.__log.d(currency.symbol, ' ---------- candle next ---------- index = ', idx)
            while len(candles[currency.symbol]) > index:
                candle = candles[currency.symbol][index]
                candle.setBol(self.__calcBollinger(currency.symbol, candles[currency.symbol][index - 19:index + 1:], 0))
                bolUpPrice = candle.bol[0]
                bolDownPrice = candle.bol[2]
                high2BolupPercent = candle.high / bolUpPrice * 100 - 100
                low2BoldownPercent = 100 - candle.low / abs(bolDownPrice) * 100
                if high2BolupPercent >= bolUpBuyRate_ or low2BoldownPercent >= self.__bolDownBuyRate:
                    if high2BolupPercent < 0:
                        high2BolupPercent = 0
                    if low2BoldownPercent < 0:
                        low2BoldownPercent = 0
                    if 200 < low2BoldownPercent:
                        self.__log.d(currency.symbol, ' high2BolupPercent=', high2BolupPercent, ' bolUpPrice=',
                                     bolUpPrice, ' low2BoldownPercent', low2BoldownPercent, ' bolDownPrice=',
                                     bolDownPrice)
                    data = [-1, currency.symbol, candle.candleTime / 1000, candle.high, candle.low, candle.close,
                            bolUpPrice, bolDownPrice, high2BolupPercent, low2BoldownPercent, idx]
                    try:
                        self.__log.d(currency.symbol, ' add record candle.candleTime = ', candle.candleTime)
                        self.__candleResultRepository.addCandleResult(data)
                        self.__candleResultRepository.commit()
                    except Exception as e:
                        self.__log.d('999 exception')
                        self.__log.d(str(e))
                index += 1
            candles[currency.symbol] = []
            idx += 1



    # Test No 3
    def runBuyOperation(self):
        candles = {}
        _fromFollowMin = 0
        bolData = None
        openValue = 0
        sleepCnt = 0
        startSymbol = None
        if startSymbol is None or self.__specificIndexFrom == 0:
            self.__candleBuyResultRepository.cleanResultBuyCandle()
            self.__candleBuyResultRepository.commit()

        idx = 1
        startIndex = self.__specificIndexFrom
        endIndex = self.__specificIndexTo
        for currency in self.__currencies:
            bolUpBuyRate_ = getBuyRateBySymbol(self.__currencyGroupNum, currency.symbol, self.__bolUpBuyRate)
            if self.__specificIndexFrom != 0:
                if idx < startIndex:
                    idx += 1
                    continue
                if idx > endIndex:
                    break
            if startSymbol is not None:
                if currency.symbol != startSymbol:
                    continue
                else:
                    self.__candleBuyResultRepository.deleteSymbolList(startSymbol)
                    self.__candleBuyResultRepository.commit()
                    startSymbol = None
            self.__previousBuyTime = 0
            values = self.__candleListRepository.readCandleList(currency.symbol)
            candles[currency.symbol] = []
            for value in values:
                data = CandleResultAdapter.createFromBinance(value, 0)
                candles[currency.symbol].append(data)
            index = 19
            self.__log.d(currency.symbol, ' ---------- candle next ---------- index = ', idx)
            while len(candles[currency.symbol]) > index:
                candle = candles[currency.symbol][index]
                candle.setBol(
                    self.__calcBollinger(currency.symbol, candles[currency.symbol][index - 19:index + 1:], 0))
                bolUpPrice = candle.bol[0]
                bolDownPrice = candle.bol[2]
                high2BolupPercent = candle.high / bolUpPrice * 100 - 100
                low2BoldownPercent = 100 - candle.low / abs(bolDownPrice) * 100
                if high2BolupPercent >= (bolUpBuyRate_ - 2) or low2BoldownPercent >= (self.__bolDownBuyRate - 2):
                    if high2BolupPercent >= (bolUpBuyRate_ - 2) or low2BoldownPercent >= (
                            self.__bolDownBuyRate - 2):
                        if self.__tradePermitSide == 'BOL_UP_ONLY' and low2BoldownPercent >= (
                                self.__bolDownBuyRate - 2):
                            index += 1
                            continue
                        elif self.__tradePermitSide == 'BOL_DOWN_ONLY' and high2BolupPercent >= (
                                bolUpBuyRate_ - 2):
                            index += 1
                            continue
                    epoch_time = candle.candleTime
                    time_val = time.localtime(epoch_time / 1000)
                    print(currency.symbol, " time=", time_val, ' epochTime=', candle.candleTime)
                    if high2BolupPercent >= (bolUpBuyRate_ - 2):
                        position = 'SHORT'
                    else:
                        position = 'LONG'
                    _fromFollowMin = candle.candleTime / 1000
                    try:
                        valuesFollowMin = self.__tradingCenter.getCandlestickData(
                            currency.symbol, self.__followLogicInterval,
                            (120 / self.__followLogicInterval), _fromFollowMin * 1000)
                    except Exception as e:
                        self.__log.d('getCandlestickData() exception')
                        valuesFollowMin = self.__tradingCenter.getCandlestickData(
                            currency.symbol, self.__followLogicInterval,
                            (120 / self.__followLogicInterval), _fromFollowMin * 1000)
                        self.__log.d(str(e))
                    # temp
                    time_val = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(_fromFollowMin))
                    print(currency.symbol, ' ### 1hour open time = :', time_val)
                    index_FollowMin = 0
                    status = 'START'
                    currentHighPrice = 0
                    currentLowPrice = 0
                    currentClosePrice = 0
                    for valueFollowMin in valuesFollowMin:
                        # temp
                        epoch_time = (valueFollowMin.closeTime - 999) / 1000 - 299
                        time_val = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(epoch_time))
                        if status == 'START':
                            if position == 'SHORT':
                                currFollowMin = (float(valueFollowMin.high) + float(valueFollowMin.open)) / 2
                            else:
                                currFollowMin = (float(valueFollowMin.low) + float(valueFollowMin.open)) / 2

                            # reCalculate bollinger value
                            bol = self.__calcBollinger(
                                currency.symbol, candles[currency.symbol][index - 19:index + 1:], currFollowMin)
                            candle.setBol(bol)
                            currentHighPrice = float(valueFollowMin.high)
                            currentLowPrice = float(valueFollowMin.low)
                            bolUpPrice = candle.bol[0]
                            bolDownPrice = candle.bol[2]
                            high2BolupPercent = currentHighPrice / bolUpPrice * 100 - 100
                            low2BoldownPercent = 100 - currentLowPrice / abs(bolDownPrice) * 100

                            if high2BolupPercent < 0:
                                high2BolupPercent = 0
                            if low2BoldownPercent < 0:
                                low2BoldownPercent = 0

                            if self.__candleInterval == 5:
                                if self.__followLogicInterval == 1:
                                    if index_FollowMin > 4:
                                        break
                            elif self.__candleInterval == 3:
                                if self.__followLogicInterval == 1:
                                    if index_FollowMin > 2:
                                        break
                            else:
                                if self.__followLogicInterval == 5:
                                    if index_FollowMin > 11:
                                        break
                                elif self.__followLogicInterval == 3:
                                    if index_FollowMin > 19:
                                        break
                                elif self.__followLogicInterval == 1:
                                    if index_FollowMin > 59:
                                        break

                            self.__log.d(currency.symbol, ' ----- > start trigger ', self.__followLogicInterval,
                                         ' min open time=', time_val, ' index=', index_FollowMin, 'status=', status)
                            sleepCnt += 1
                            if sleepCnt > self.__sleepCnt:
                                time.sleep(self.__sleepTime3)
                                sleepCnt = 0

                        if high2BolupPercent > bolUpBuyRate_ or \
                                low2BoldownPercent > self.__bolDownBuyRate or status != 'START':
                            self.__log.d(currency.symbol, ' high2BolUpPercent=', high2BolupPercent,
                                         ' low2BolDownPercent=', low2BoldownPercent, ' price=', currentHighPrice,
                                         ' status=', status)
                            if self.__debuggingMode == 1:
                                bolData = ','.join(str(e) for e in bol[3])
                                openValue = float(valueFollowMin.open)

                            if self.__previousBuyTime + self.__duplicateForbidTime > _fromFollowMin:
                                _fromFollowMin += self.__followLogicInterval
                                index_FollowMin += 1
                                status = 'START'
                                self.__log.d(currency.symbol, ' time is duplicated.. go to next status=', status)
                                continue
                            buyTime = 0
                            data = CandleAdapter.createFromBinance(valueFollowMin, 0)
                            if status == 'START':
                                candle.low2BolPercent = low2BoldownPercent
                                candle.high2BolPercent = high2BolupPercent
                                currentClosePrice = float(valueFollowMin.close)
                                candle.bolHigh = bolUpPrice
                                candle.bolLow = bolDownPrice

                                if candle.low2BolPercent > self.__bolDownBuyRate:
                                    triggerPrice = candle.bolLow - candle.bolLow * 0.01 * self.__bolDownBuyRate
                                elif candle.high2BolPercent > bolUpBuyRate_:
                                    triggerPrice = candle.bolHigh + candle.bolHigh * 0.01 * bolUpBuyRate_

                            if position == 'SHORT' and status != 'FINISH':
                                if status == 'START':
                                    if data.high > triggerPrice:
                                        status = 'TRIGGERED'
                                        triggerTime = round(data.candleTime / 1000)
                                        print(currency.symbol, ' SHORT TRIGGERED triggerPrice=', triggerPrice,
                                              ' data.high=', data.high, ' index = ', index_FollowMin)
                                elif status == 'TRIGGERED':
                                    if float(valuesFollowMin[index_FollowMin - 1].close) > data.close:  # check close
                                        status = 'LAST'
                                        print(currency.symbol, ' SHORT LAST before close=',
                                              valuesFollowMin[index_FollowMin - 1].close, ' curr close=',
                                              data.close, ' index = ', index_FollowMin)
                                elif status == 'LAST':
                                    if (float(valuesFollowMin[index_FollowMin - 1].close) - float(
                                            valuesFollowMin[index_FollowMin - 1].close) / 5000) > data.low:  # check low
                                        status = 'FINISH'
                                        print(currency.symbol, ' SHORT FINISH before close=',
                                              valuesFollowMin[index_FollowMin - 1].close, ' curr low=',
                                              data.low, ' index = ', index_FollowMin)
                                        buyPrice = data.open
                                        buy2BolPercent = buyPrice / candle.bolHigh * 100 - 100
                                        buyTime = round(data.candleTime / 1000)
                                        # self.__log.d(currency.symbol, ' SHORT triggerPrice=', triggerPrice, ' buyPrice=', buyPrice)
                                        break
                                    else:
                                        status = 'TRIGGERED'
                            elif position == 'LONG' and status != 'FINISH':
                                if status == 'START':
                                    if data.low < triggerPrice:
                                        status = 'TRIGGERED'
                                        triggerTime = round(data.candleTime / 1000)
                                        print(currency.symbol, ' LONG TRIGGERED triggerPrice=', triggerPrice,
                                              ' data.low=', data.low, ' index = ', index_FollowMin)
                                elif status == 'TRIGGERED':
                                    if float(valuesFollowMin[index_FollowMin - 1].close) < data.close:  # check close
                                        status = 'LAST'
                                        print(currency.symbol, ' LONG LAST before close=',
                                              valuesFollowMin[index_FollowMin - 1].close,
                                              ' curr close=', data.close, ' index = ', index_FollowMin)
                                elif status == 'LAST':
                                    if (float(valuesFollowMin[index_FollowMin - 1].close) + float(
                                            valuesFollowMin[
                                                index_FollowMin - 1].close) / 5000) < data.high:  # check low
                                        status = 'FINISH'
                                        print(currency.symbol, ' LONG FINISH before close=',
                                              valuesFollowMin[index_FollowMin - 1].close, ' curr low=',
                                              data.high, ' index = ', index_FollowMin)
                                        buyPrice = data.open
                                        buy2BolPercent = 100 - buyPrice / abs(candle.bolLow) * 100
                                        buyTime = round(data.candleTime / 1000)
                                        # self.__log.d(currency.symbol, ' LONG triggerPrice=', triggerPrice, ' buyPrice=', buyPrice)
                                        break
                                    else:
                                        status = 'TRIGGERED'
                        _fromFollowMin += self.__followLogicInterval
                        index_FollowMin += 1

                    if status == 'FINISH':
                        if high2BolupPercent > 0:
                            position = 'LONG'
                        elif low2BoldownPercent > 0:
                            position = 'SHORT'

                        if position == 'LONG':
                            self.__log.d(currency.symbol, ' LONG bolLow=', candle.bolLow, ' buy price=', data.open)
                            if data.open > candle.bolLow - candle.bolLow / 100 * self.__minimumBolTriggerRate:
                                self.__log.d(currency.symbol, ' LONG skip __minimumBolTriggerRate bolLow=',
                                             candle.bolLow, ' curr=',
                                             data.open)
                                index += 1
                                continue
                        elif position == 'SHORT':
                            self.__log.d(currency.symbol, ' SHORT bolHigh=', candle.bolHigh, ' buy price=', data.open)
                            if data.open < candle.bolHigh + candle.bolHigh / 100 * self.__minimumBolTriggerRate:
                                self.__log.d(currency.symbol, ' SHORT skip __minimumBolTriggerRate bolHigh=',
                                             candle.bolHigh, ' curr=',
                                             data.open)
                                index += 1
                                continue
                        else:
                            index += 1
                            continue

                        profitRate = 0
                        if position == 'SHORT':
                            profitRate = bolUpBuyRate_
                        elif position == 'LONG':
                            profitRate = self.__bolDownBuyRate
                        else:
                            self.__log.d('position exception')

                        if self.__debuggingMode != 1:
                            data = [-1, currency.symbol, candle.candleTime / 1000, position,
                                    round(currentHighPrice, currency.pricePrecision),
                                    round(currentLowPrice, currency.pricePrecision),
                                    round(currentClosePrice, currency.pricePrecision),
                                    round(candle.bolHigh, currency.pricePrecision),
                                    round(candle.bolLow, currency.pricePrecision), round(candle.high2BolPercent, 2),
                                    round(candle.low2BolPercent, 3), buyPrice, round(buy2BolPercent, 2),
                                    idx, buyTime, triggerTime, triggerPrice, profitRate,
                                    0, 0, 0, 0, 0, 0]
                        else:
                            data = [-1, currency.symbol, candle.candleTime / 1000, position,
                                    round(currentHighPrice, currency.pricePrecision),
                                    round(currentLowPrice, currency.pricePrecision),
                                    round(currentClosePrice, currency.pricePrecision),
                                    round(candle.bolHigh, currency.pricePrecision),
                                    round(candle.bolLow, currency.pricePrecision), round(candle.high2BolPercent, 2),
                                    round(candle.low2BolPercent, 3), buyPrice, round(buy2BolPercent, 2),
                                    idx, buyTime, triggerTime, triggerPrice, profitRate, bolData, openValue,
                                    0, 0, 0, 0, 0, 0]
                        self.__previousBuyTime = buyTime
                        try:
                            self.__log.d(currency.symbol, ' add record buyTime = ', buyTime)
                            self.__candleBuyResultRepository.addCandleBuyResult(data)
                            self.__candleBuyResultRepository.commit()
                        except Exception as e:
                            self.__log.d('addCandleBuyResult() exception')
                            self.__log.d(str(e))
                index += 1
            try:
                self.__candleBuyResultRepository.commit()
            except Exception as e:
                self.__log.d('addCandleBuyResult() commit() exception')
                self.__log.d(str(e))
            candles[currency.symbol] = []
            idx += 1

        return

    def backupCandleList(self):
        self.__log.d('start backupCandleList()')
        self.__candleListRepository.backup()
        self.__candleListRepository.commit()
        self.__log.d('finish backupCandleList()')

    def checkBtcdomRate(self, btcdomCandles, candleTime):
        if candleTime == 1640951100000:
            self.__log.d('BTCDOMUSDT')
        try:
            if btcdomCandles[candleTime] is not None:
                if btcdomCandles[candleTime][0].btcdomPercent > self.__btcdomPercent:
                    # self.__log.d('BTCDOMUSDT', ' Mode Low percent =', candle.btcdomPercent, ' btcdomPercent=',
                    #              self.__btcdomPercent)
                    return True
        except Exception as e:
            self.__log.d('BTCDOMUSDT FATAL candleTime=', candleTime, ' is not available return False')
        return False

    # Test No 3
    def runBuyStaticOperation(self, index, symbol):
        candles = {}
        btcdomCandles = {}
        _fromFollowMin = 0
        
        startSymbol = None
        #startSymbol = 'BTCUSDT'

        sleepCnt = 0
        priceMode = 'HIGH'
        detectBolPercent = self.__detectBolPercent
        if startSymbol is None:
            self.__candleBuyResultRepository.cleanResultBuyCandle()
            self.__candleBuyResultRepository.commit()

        if startSymbol is not None:
            try:
                self.runUnComplatedBuy()
            except Exception as e:
                sys.exit(0)

        idx = index
        for currency in self.__currencies:
            # if startSymbol is not None:
            #     if currency.symbol != startSymbol:
            #         continue
            #     else:
            #         self.__candleBuyResultRepository.deleteSymbolList(startSymbol)
            #         self.__candleBuyResultRepository.commit()
            #         startSymbol = None
            completeList = self.__candleCompleteListRepository.readCompleteList(currency.symbol)
            if len(completeList) > 0:
                idx += 1
                self.__log.d(currency.symbol, ' is already completed skip next')
                continue

            if startSymbol is not None:
                if currency.symbol != startSymbol:
                    idx += 1
                    self.__log.d(currency.symbol, ' is not matched with symbol skip next')
                    continue
                else:
                    startSymbol = None

            self.__previousBuyTime = 0
            values = self.__candleListRepository.readCandleList(currency.symbol)
            candles[currency.symbol] = []
            if len(values) == 0:
                self.__log.d(currency.symbol, ' is empty skip next')
                continue
            for value in values:
                data = CandleResultAdapter.createFromBinance(value, 0)
                candles[currency.symbol].append(data)
            index = 19
            self.__log.d(currency.symbol, ' ---------- candle next ---------- index = ', idx)
            try:
                while len(candles[currency.symbol]) > index + 1:
                    addBuyCount = 0
                    addMBuyCount = 0
                    isDuplicateStatus = 0
                    candle = candles[currency.symbol][index]
                    beforeCandle = candles[currency.symbol][index - 1]
                    if candle.candleTime - beforeCandle.candleTime > self.__candleInterval * 60 * 1000:
                        index += 19
                        continue
                    # if candle.candleTime == 1668394200000:
                    #     self.__log.d(currency.symbol, 'test')
                    # else:
                    #     index += 1
                    #     continue

                    candle.setBol(
                        self.__calcBollinger(currency.symbol, candles[currency.symbol][index - 19:index + 1:], 0))
                    bolUpPrice = candle.bol[0]
                    bolDownPrice = candle.bol[2]
                    high2BolupPercent = candle.high / bolUpPrice * 100 - 100
                    low2BoldownPercent = 100 - candle.low / abs(bolDownPrice) * 100

                    # if candle.candleTime == 1667231400000:
                    #     self.__log.d(currency.symbol, ' ---------- candle next ---------- index = ')
                    # if candle.candleTime == 1667231400000:
                    if self.__btcdomEnable == 1 and high2BolupPercent >= self.__detectBolLPercent and \
                            self.checkBtcdomRate(btcdomCandles, candle.candleTime):
                        priceMode = 'L'
                        detectBolPercent = self.__detectBolLPercent
                        bolUpBuyRate_ = getBuyRateBySymbol(self.__currencyGroupNum, currency.symbol,
                                                           self.__bolUpBuyLRate)
                    else:
                        priceMode = 'H'
                        detectBolPercent = self.__detectBolPercent

                    if high2BolupPercent >= detectBolPercent:
                        if priceMode == 'H':
                            bolUpBuyRate_ = getBuyRateBySymbol(self.__currencyGroupNum, currency.symbol,
                                                               self.__bolUpBuyRate)
                            trigger1 = self.__trigger1
                            trigger2 = self.__trigger2
                            trigger3 = self.__trigger3
                            trigger4 = self.__trigger4
                            trigger5 = self.__trigger5
                            trigger6 = self.__trigger6
                            trigger7 = self.__trigger7
                            trigger8 = self.__trigger8
                            trigger9 = self.__trigger9
                            trigger10 = self.__trigger10
                            trigger11 = self.__trigger11
                            trigger12 = self.__trigger12
                            trigger13 = self.__trigger13
                            trigger14 = self.__trigger14
                            trigger15 = self.__trigger15
                            trigger16 = self.__trigger16
                            trigger17 = self.__trigger17
                            trigger18 = self.__trigger18
                            trigger19 = self.__trigger19
                        elif priceMode == 'L':
                            trigger1 = self.__triggerL1
                            trigger2 = self.__triggerL2
                            trigger3 = self.__triggerL3
                            trigger4 = self.__triggerL4
                            trigger5 = self.__triggerL5
                            trigger6 = self.__triggerL6
                            trigger7 = self.__triggerL7
                            trigger8 = self.__triggerL8
                            trigger9 = self.__triggerL9

                        epoch_time = candle.candleTime
                        time_val = time.localtime(epoch_time / 1000)
                        print(currency.symbol, " time=", time_val, ' epochTime=', candle.candleTime)
                        position = 'SHORT'

                        if self.__min1DelayLogic == 1:
                            _fromFollowMin = candle.candleTime / 1000 - 60
                        else:
                            _fromFollowMin = candle.candleTime / 1000

                        listCnt = 0
                        if self.__candleInterval == 5:
                            listCnt = 6
                        else:
                            listCnt = 120

                        try:
                            valuesFollowMin = self.__tradingCenter.getCandlestickData(
                                currency.symbol, self.__followLogicInterval, listCnt, _fromFollowMin * 1000)
                        except Exception as e:
                            self.__log.d('getCandlestickData() exception')
                            self.__log.d(str(e))
                            sys.exit(0)
                        # temp
                        time_val = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(_fromFollowMin))
                        print(currency.symbol, ' ### 1hour open time = :', time_val)
                        index_FollowMin = 0
                        status = 'START'
                        currentHighPrice = 0
                        currentLowPrice = 0
                        currentClosePrice = 0

                        for valueFollowMin in valuesFollowMin:
                            # temp
                            epoch_time = (valueFollowMin.closeTime - 999) / 1000 - 299
                            time_val = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(epoch_time))
                            if status == 'START':
                                if self.__min1DelayLogic == 1:
                                    if self.__candleInterval == 5:
                                        if self.__followLogicInterval == 1:
                                            if index_FollowMin > 4:
                                                break
                                    elif self.__candleInterval == 3:
                                        if self.__followLogicInterval == 1:
                                            if index_FollowMin > 2:
                                                break
                                    elif self.__candleInterval == 240:
                                        if self.__followLogicInterval == 1:
                                            if index_FollowMin > 239:
                                                break
                                    else:
                                        if self.__followLogicInterval == 5:
                                            if index_FollowMin > 11:
                                                break
                                        elif self.__followLogicInterval == 3:
                                            if index_FollowMin > 19:
                                                break
                                        elif self.__followLogicInterval == 1:
                                            if index_FollowMin > 59:
                                                break
                                    currFollowMin = float(valueFollowMin.close)
                                else:
                                    # currFollowMin = (float(valueFollowMin.high) + float(valueFollowMin.open)) / 2
                                    currFollowMin = (float(valueFollowMin.close) + float(valueFollowMin.open)) / 2

                                # reCalculate bollinger value
                                bol = self.__calcBollinger(
                                    currency.symbol, candles[currency.symbol][index - 19:index + 1:], currFollowMin)
                                candle.setBol(bol)

                                if self.__min1DelayLogic == 1 and index_FollowMin < 119:
                                    currentHighPrice = float(valuesFollowMin[index_FollowMin + 1].high)
                                    currentLowPrice = float(valuesFollowMin[index_FollowMin + 1].low)
                                    currentOpenPrice = float(valuesFollowMin[index_FollowMin + 1].open)
                                else:
                                    currentHighPrice = float(valueFollowMin.high)
                                    currentLowPrice = float(valueFollowMin.low)
                                    currentOpenPrice = float(valueFollowMin.open)
                                bolUpPrice = candle.bol[0]
                                bolDownPrice = candle.bol[2]

                                high2BolupPercent = currentHighPrice / bolUpPrice * 100 - 100
                                low2BoldownPercent = 0
                                triggerPrice = bolUpPrice + bolUpPrice * 0.01 * bolUpBuyRate_

                                if self.__candleInterval == 5:
                                    if self.__followLogicInterval == 1:
                                        if index_FollowMin > 4:
                                            break
                                elif self.__candleInterval == 3:
                                    if self.__followLogicInterval == 1:
                                        if index_FollowMin > 2:
                                            break
                                else:
                                    if self.__followLogicInterval == 5:
                                        if index_FollowMin > 11:
                                            break
                                    elif self.__followLogicInterval == 3:
                                        if index_FollowMin > 19:
                                            break
                                    elif self.__followLogicInterval == 1:
                                        if index_FollowMin > 59:
                                            break
                                self.__log.d(currency.symbol, ' ----- > start trigger ', self.__followLogicInterval,
                                             ' min open time=', time_val, ' index=', index_FollowMin, ' status=',
                                             status)
                                sleepCnt += 1
                                if sleepCnt > self.__sleepCnt:
                                    time.sleep(self.__sleepTime3)
                                    sleepCnt = 0

                            if currentHighPrice >= triggerPrice:
                                openValue = float(valueFollowMin.open)
                                self.__log.d(currency.symbol, ' high2BolUpPercent=', high2BolupPercent,
                                             ' price=', currentHighPrice, ' status=', status)
                                if self.__debuggingMode == 1:
                                    bolData = ','.join(str(e) for e in bol[3])

                                if self.__duplicateForbidTime == 0:
                                    if self.__previousBuyTime + 7200 > _fromFollowMin:
                                        isDuplicateStatus = 1
                                        self.__log.d(currency.symbol, ' Duplicate Status')
                                else:
                                    if self.__previousBuyTime + self.__duplicateForbidTime > _fromFollowMin:
                                        _fromFollowMin += self.__followLogicInterval * 60
                                        index_FollowMin += 1
                                        status = 'START'
                                        self.__log.d(currency.symbol, ' time is duplicated.. go to next status=',
                                                     status)
                                        continue
                                buyTime = 0
                                data = CandleAdapter.createFromBinance(valueFollowMin, 0)
                                if status == 'START':
                                    if self.__buyConditions == 'FORWARD_STATIC_BUY':
                                        position = 'LONG'

                                    candle.low2BolPercent = low2BoldownPercent
                                    candle.high2BolPercent = high2BolupPercent
                                    currentClosePrice = float(valueFollowMin.close)
                                    candle.bolHigh = bolUpPrice
                                    candle.bolLow = bolDownPrice
                                    if self.__min1DelayLogic == 1:
                                        buyTime = triggerTime = round(data.candleTime / 1000) + 60
                                    else:
                                        buyTime = triggerTime = round(data.candleTime / 1000)

                                    if self.__candleInterval == 5:
                                        lastMin = 5 - ((buyTime / 60) % 5)
                                        if lastMin == 5:
                                            if self.__checkMin5CandleCnt == 3:
                                                tick2HighPrice = max(candle.high,
                                                                     candles[currency.symbol][index + 1].high,
                                                                     candles[currency.symbol][index + 2].high)
                                            else:
                                                tick2HighPrice = max(candle.high,
                                                                     candles[currency.symbol][index + 1].high)
                                        else:
                                            valuesMin1_ = self.__tradingCenter.fetch1MinCandle(
                                                currency.symbol, buyTime * 1000, lastMin)
                                            min1High = 0
                                            if len(valuesMin1_) != lastMin:
                                                self.__log.d(currency.symbol, ' Fatal error ############## Exit 00')
                                                sys.exit(0)
                                            for value in valuesMin1_:
                                                if min1High < float(value.high):
                                                    min1High = float(value.high)

                                            if self.__checkMin5CandleCnt == 3:
                                                tick2HighPrice = max(min1High,
                                                                     candles[currency.symbol][index + 1].high,
                                                                     candles[currency.symbol][index + 2].high)
                                            else:
                                                tick2HighPrice = max(min1High, candles[currency.symbol][index + 1].high)
                                    elif self.__candleInterval == 240:
                                        valuesMin5_ = None
                                        if buyTime % (60 * 240) == 0:
                                            valuesMin5_ = self.__tradingCenter.fetch4HourCandle(
                                                currency.symbol, buyTime * 1000, 1)
                                        else:
                                            valuesMin5_ = self.__tradingCenter.fetch4HourCandle(
                                                currency.symbol, (buyTime - 60 * 240) * 1000, 1)
                                        if len(valuesMin5_) != 1:
                                            self.__log.d(currency.symbol, ' Fatal error ############## Exit 555')
                                            sys.exit(0)

                                            tick2HighPrice = float(valuesMin5_[0].high)
                                    else:
                                        valuesMin5_ = None
                                        if buyTime % 300 == 0:
                                            valuesMin5_ = self.__tradingCenter.fetch5MinCandle(
                                                currency.symbol, buyTime * 1000, self.__checkMin5CandleCnt)
                                        else:
                                            valuesMin5_ = self.__tradingCenter.fetch5MinCandle(
                                                currency.symbol, (buyTime - 300) * 1000, self.__checkMin5CandleCnt)
                                        if len(valuesMin5_) != self.__checkMin5CandleCnt:
                                            self.__log.d(currency.symbol, ' Fatal error ############## Exit 66')
                                            sys.exit(0)

                                        lastMin = 5 - ((buyTime / 60) % 5)
                                        if lastMin == 5:
                                            if self.__checkMin5CandleCnt == 3:
                                                tick2HighPrice = max(float(valuesMin5_[0].high),
                                                                     float(valuesMin5_[1].high),
                                                                     float(valuesMin5_[2].high))
                                            else:
                                                tick2HighPrice = max(float(valuesMin5_[0].high),
                                                                     float(valuesMin5_[1].high))
                                        else:
                                            valuesMin1_ = self.__tradingCenter.fetch1MinCandle(
                                                currency.symbol, buyTime * 1000, lastMin)
                                            min1High = 0
                                            if len(valuesMin1_) != lastMin:
                                                self.__log.d(currency.symbol, ' Fatal error ############## Exit 77')
                                                sys.exit(0)
                                            for value in valuesMin1_:
                                                if min1High < float(value.high):
                                                    min1High = float(value.high)

                                            if self.__checkMin5CandleCnt == 3:
                                                tick2HighPrice = max(min1High,
                                                                     float(valuesMin5_[1].high),
                                                                     float(valuesMin5_[2].high))
                                            else:
                                                tick2HighPrice = max(min1High, float(valuesMin5_[1].high))

                                    if self.__triggerMTotalCnt > 0:
                                        if not (currentLowPrice < triggerPrice < currentHighPrice):
                                            buyPrice = currentOpenPrice
                                            triggerMPrice1 = currentOpenPrice + currentOpenPrice * 0.01 * self.__triggerM1
                                            triggerMPrice2 = currentOpenPrice + currentOpenPrice * 0.01 * self.__triggerM2
                                            triggerMPrice3 = currentOpenPrice + currentOpenPrice * 0.01 * self.__triggerM3
                                        else:
                                            buyPrice = round(triggerPrice, currency.pricePrecision)
                                            triggerMPrice1 = bolUpPrice + bolUpPrice * 0.01 * self.__triggerM1
                                            triggerMPrice2 = bolUpPrice + bolUpPrice * 0.01 * self.__triggerM2
                                            triggerMPrice3 = bolUpPrice + bolUpPrice * 0.01 * self.__triggerM3

                                        if tick2HighPrice >= triggerMPrice1:
                                            addMBuyCount += 1
                                            buyPrice = triggerMPrice1 + buyPrice
                                        if tick2HighPrice >= triggerMPrice2:
                                            addMBuyCount += 1
                                            buyPrice = triggerMPrice2 + buyPrice
                                        if tick2HighPrice >= triggerMPrice3:
                                            addMBuyCount += 1
                                            buyPrice = triggerMPrice3 + buyPrice

                                        if addMBuyCount > 0:
                                            buyPrice = round(buyPrice / (addMBuyCount + 1), currency.pricePrecision)

                                    if not (currentLowPrice < triggerPrice < currentHighPrice):
                                        if self.__triggerMTotalCnt == 0:
                                            buyPrice = currentOpenPrice
                                        triggerPrice1 = currentOpenPrice + currentOpenPrice * 0.01 * trigger1
                                        triggerPrice2 = currentOpenPrice + currentOpenPrice * 0.01 * trigger2
                                        triggerPrice3 = currentOpenPrice + currentOpenPrice * 0.01 * trigger3
                                        triggerPrice4 = currentOpenPrice + currentOpenPrice * 0.01 * trigger4
                                        triggerPrice5 = currentOpenPrice + currentOpenPrice * 0.01 * trigger5
                                        triggerPrice6 = currentOpenPrice + currentOpenPrice * 0.01 * trigger6
                                        triggerPrice7 = currentOpenPrice + currentOpenPrice * 0.01 * trigger7
                                        triggerPrice8 = currentOpenPrice + currentOpenPrice * 0.01 * trigger8
                                        triggerPrice9 = currentOpenPrice + currentOpenPrice * 0.01 * trigger9
                                        triggerPrice10 = currentOpenPrice + currentOpenPrice * 0.01 * trigger10
                                        triggerPrice11 = currentOpenPrice + currentOpenPrice * 0.01 * trigger11
                                        triggerPrice12 = currentOpenPrice + currentOpenPrice * 0.01 * trigger12
                                        triggerPrice13 = currentOpenPrice + currentOpenPrice * 0.01 * trigger13
                                        triggerPrice14 = currentOpenPrice + currentOpenPrice * 0.01 * trigger14
                                        triggerPrice15 = currentOpenPrice + currentOpenPrice * 0.01 * trigger15
                                        triggerPrice16 = currentOpenPrice + currentOpenPrice * 0.01 * trigger16
                                        triggerPrice17 = currentOpenPrice + currentOpenPrice * 0.01 * trigger17
                                        triggerPrice18 = currentOpenPrice + currentOpenPrice * 0.01 * trigger18
                                        triggerPrice19 = currentOpenPrice + currentOpenPrice * 0.01 * trigger19

                                        triggerQuantity1 = round(self.__singleBalance / triggerPrice1,
                                                                 currency.quantityPrecision)
                                        triggerQuantity2 = round(self.__singleBalance / triggerPrice2,
                                                                 currency.quantityPrecision)
                                        triggerQuantity3 = round(self.__singleBalance / triggerPrice3,
                                                                 currency.quantityPrecision)
                                        triggerQuantity4 = round(self.__singleBalance / triggerPrice4,
                                                                 currency.quantityPrecision)
                                        triggerQuantity5 = round(self.__singleBalance / triggerPrice5,
                                                                 currency.quantityPrecision)
                                        triggerQuantity6 = round(self.__singleBalance / triggerPrice6,
                                                                 currency.quantityPrecision)
                                        triggerQuantity7 = round(self.__singleBalance / triggerPrice7,
                                                                 currency.quantityPrecision)
                                        triggerQuantity8 = round(self.__singleBalance / triggerPrice8,
                                                                 currency.quantityPrecision)
                                        triggerQuantity9 = round(self.__singleBalance / triggerPrice9,
                                                                 currency.quantityPrecision)
                                        triggerQuantity10 = round(self.__singleBalance / triggerPrice10,
                                                                  currency.quantityPrecision)
                                        triggerQuantity11 = round(self.__singleBalance / triggerPrice11,
                                                                  currency.quantityPrecision)
                                        triggerQuantity12 = round(self.__singleBalance / triggerPrice12,
                                                                  currency.quantityPrecision)
                                        triggerQuantity13 = round(self.__singleBalance / triggerPrice13,
                                                                  currency.quantityPrecision)
                                        triggerQuantity14 = round(self.__singleBalance / triggerPrice14,
                                                                  currency.quantityPrecision)
                                        triggerQuantity15 = round(self.__singleBalance / triggerPrice15,
                                                                  currency.quantityPrecision)
                                        triggerQuantity16 = round(self.__singleBalance / triggerPrice16,
                                                                  currency.quantityPrecision)
                                        triggerQuantity17 = round(self.__singleBalance / triggerPrice17,
                                                                  currency.quantityPrecision)
                                        triggerQuantity18 = round(self.__singleBalance / triggerPrice18,
                                                                  currency.quantityPrecision)
                                        triggerQuantity19 = round(self.__singleBalance / triggerPrice19,
                                                                  currency.quantityPrecision)
                                    else:
                                        if self.__triggerMTotalCnt == 0:
                                            buyPrice = round(triggerPrice, currency.pricePrecision)
                                        triggerPrice1 = bolUpPrice + bolUpPrice * 0.01 * trigger1
                                        triggerPrice2 = bolUpPrice + bolUpPrice * 0.01 * trigger2
                                        triggerPrice3 = bolUpPrice + bolUpPrice * 0.01 * trigger3
                                        triggerPrice4 = bolUpPrice + bolUpPrice * 0.01 * trigger4
                                        triggerPrice5 = bolUpPrice + bolUpPrice * 0.01 * trigger5
                                        triggerPrice6 = bolUpPrice + bolUpPrice * 0.01 * trigger6
                                        triggerPrice7 = bolUpPrice + bolUpPrice * 0.01 * trigger7
                                        triggerPrice8 = bolUpPrice + bolUpPrice * 0.01 * trigger8
                                        triggerPrice9 = bolUpPrice + bolUpPrice * 0.01 * trigger9
                                        triggerPrice10 = bolUpPrice + bolUpPrice * 0.01 * trigger10
                                        triggerPrice11 = bolUpPrice + bolUpPrice * 0.01 * trigger11
                                        triggerPrice12 = bolUpPrice + bolUpPrice * 0.01 * trigger12
                                        triggerPrice13 = bolUpPrice + bolUpPrice * 0.01 * trigger13
                                        triggerPrice14 = bolUpPrice + bolUpPrice * 0.01 * trigger14
                                        triggerPrice15 = bolUpPrice + bolUpPrice * 0.01 * trigger15
                                        triggerPrice16 = bolUpPrice + bolUpPrice * 0.01 * trigger16
                                        triggerPrice17 = bolUpPrice + bolUpPrice * 0.01 * trigger17
                                        triggerPrice18 = bolUpPrice + bolUpPrice * 0.01 * trigger18
                                        triggerPrice19 = bolUpPrice + bolUpPrice * 0.01 * trigger19

                                        triggerQuantity1 = round(self.__singleBalance / triggerPrice1,
                                                                 currency.quantityPrecision)
                                        triggerQuantity2 = round(self.__singleBalance / triggerPrice2,
                                                                 currency.quantityPrecision)
                                        triggerQuantity3 = round(self.__singleBalance / triggerPrice3,
                                                                 currency.quantityPrecision)
                                        triggerQuantity4 = round(self.__singleBalance / triggerPrice4,
                                                                 currency.quantityPrecision)
                                        triggerQuantity5 = round(self.__singleBalance / triggerPrice5,
                                                                 currency.quantityPrecision)
                                        triggerQuantity6 = round(self.__singleBalance / triggerPrice6,
                                                                 currency.quantityPrecision)
                                        triggerQuantity7 = round(self.__singleBalance / triggerPrice7,
                                                                 currency.quantityPrecision)
                                        triggerQuantity8 = round(self.__singleBalance / triggerPrice8,
                                                                 currency.quantityPrecision)
                                        triggerQuantity9 = round(self.__singleBalance / triggerPrice9,
                                                                 currency.quantityPrecision)
                                        triggerQuantity10 = round(self.__singleBalance / triggerPrice10,
                                                                  currency.quantityPrecision)
                                        triggerQuantity11 = round(self.__singleBalance / triggerPrice11,
                                                                  currency.quantityPrecision)
                                        triggerQuantity12 = round(self.__singleBalance / triggerPrice12,
                                                                  currency.quantityPrecision)
                                        triggerQuantity13 = round(self.__singleBalance / triggerPrice13,
                                                                  currency.quantityPrecision)
                                        triggerQuantity14 = round(self.__singleBalance / triggerPrice14,
                                                                  currency.quantityPrecision)
                                        triggerQuantity15 = round(self.__singleBalance / triggerPrice15,
                                                                  currency.quantityPrecision)
                                        triggerQuantity16 = round(self.__singleBalance / triggerPrice16,
                                                                  currency.quantityPrecision)
                                        triggerQuantity17 = round(self.__singleBalance / triggerPrice17,
                                                                  currency.quantityPrecision)
                                        triggerQuantity18 = round(self.__singleBalance / triggerPrice18,
                                                                  currency.quantityPrecision)
                                        triggerQuantity19 = round(self.__singleBalance / triggerPrice19,
                                                                  currency.quantityPrecision)

                                    profitRate = bolUpBuyRate_
                                    buy2BolPercent = profitRate

                                    if tick2HighPrice >= triggerPrice1:
                                        addBuyCount += 1
                                        buyPrice = triggerPrice1 + buyPrice
                                    if tick2HighPrice >= triggerPrice2:
                                        addBuyCount += 1
                                        buyPrice = triggerPrice2 + buyPrice
                                    if tick2HighPrice >= triggerPrice3:
                                        addBuyCount += 1
                                        buyPrice = triggerPrice3 + buyPrice
                                    if tick2HighPrice >= triggerPrice4:
                                        addBuyCount += 1
                                        buyPrice = triggerPrice4 + buyPrice
                                    if tick2HighPrice >= triggerPrice5:
                                        addBuyCount += 1
                                        buyPrice = triggerPrice5 + buyPrice
                                    if tick2HighPrice >= triggerPrice6:
                                        addBuyCount += 1
                                        buyPrice = triggerPrice6 + buyPrice
                                    if tick2HighPrice >= triggerPrice7:
                                        addBuyCount += 1
                                        buyPrice = triggerPrice7 + buyPrice
                                    if tick2HighPrice >= triggerPrice8:
                                        addBuyCount += 1
                                        buyPrice = triggerPrice8 + buyPrice
                                    if tick2HighPrice >= triggerPrice9:
                                        addBuyCount += 1
                                        buyPrice = triggerPrice9 + buyPrice
                                    if tick2HighPrice >= triggerPrice10:
                                        addBuyCount += 1
                                        buyPrice = triggerPrice10 + buyPrice
                                    if tick2HighPrice >= triggerPrice11:
                                        addBuyCount += 1
                                        buyPrice = triggerPrice11 + buyPrice
                                    if tick2HighPrice >= triggerPrice12:
                                        addBuyCount += 1
                                        buyPrice = triggerPrice12 + buyPrice
                                    if tick2HighPrice >= triggerPrice13:
                                        addBuyCount += 1
                                        buyPrice = triggerPrice13 + buyPrice
                                    if tick2HighPrice >= triggerPrice14:
                                        addBuyCount += 1
                                        buyPrice = triggerPrice14 + buyPrice
                                    if tick2HighPrice >= triggerPrice15:
                                        addBuyCount += 1
                                        buyPrice = triggerPrice15 + buyPrice
                                    if tick2HighPrice >= triggerPrice16:
                                        addBuyCount += 1
                                        buyPrice = triggerPrice16 + buyPrice
                                    if tick2HighPrice >= triggerPrice17:
                                        addBuyCount += 1
                                        buyPrice = triggerPrice17 + buyPrice
                                    if tick2HighPrice >= triggerPrice18:
                                        addBuyCount += 1
                                        buyPrice = triggerPrice18 + buyPrice
                                    if tick2HighPrice >= triggerPrice19:
                                        addBuyCount += 1
                                        buyPrice = triggerPrice19 + buyPrice

                                    if addBuyCount > 0:
                                        buyPrice = round(buyPrice / (addBuyCount + 1), currency.pricePrecision)

                                    status = 'FINISH'
                                    break
                            _fromFollowMin += self.__followLogicInterval * 60
                            index_FollowMin += 1

                        if status == 'FINISH':
                            position = 'LONG'
                            if self.__debuggingMode != 1:
                                data = [-1, currency.symbol, candle.candleTime / 1000, position,
                                        round(currentHighPrice, currency.pricePrecision),
                                        round(currentLowPrice, currency.pricePrecision),
                                        round(currentClosePrice, currency.pricePrecision),
                                        round(candle.bolHigh, currency.pricePrecision),
                                        round(candle.bolLow, currency.pricePrecision), round(candle.high2BolPercent, 2),
                                        isDuplicateStatus, buyPrice, round(buy2BolPercent, 2),
                                        idx, buyTime, triggerTime, triggerPrice, profitRate,
                                        self.__expireTimeToSell, 0, 0, 0, 0, 0, addBuyCount,
                                        addMBuyCount, priceMode]
                            else:
                                data = [-1, currency.symbol, candle.candleTime / 1000, position,
                                        round(currentHighPrice, currency.pricePrecision),
                                        round(currentLowPrice, currency.pricePrecision),
                                        round(currentClosePrice, currency.pricePrecision),
                                        round(candle.bolHigh, currency.pricePrecision),
                                        round(candle.bolLow, currency.pricePrecision), round(candle.high2BolPercent, 2),
                                        isDuplicateStatus, buyPrice, round(buy2BolPercent, 2),
                                        idx, buyTime, triggerTime, triggerPrice, profitRate, bolData, openValue,
                                        0, 0, 0, 0, 0, 0, addBuyCount, addMBuyCount, priceMode]

                            self.__previousBuyTime = buyTime
                            try:
                                self.__log.d(currency.symbol, ' add record buyTime = ', buyTime)
                                self.__candleBuyResultRepository.addCandleBuyResult(data)
                                self.__candleBuyResultRepository.commit()
                            except Exception as e:
                                self.__log.d('addCandleBuyResult() exception')
                                self.__log.d(str(e))
                                sys.exit(0)
                    index += 1
                del candles[currency.symbol]
                gc.collect()
            except Exception as e:
                self.__log.d('========= add error index and other info ===========')
                self.__log.d('========= symbol=', currency.symbol, ' symbol idx=', idx, ' list index=', index)
                self.__log.d(str(e))
                sys.exit(0)
            try:
                self.__candleBuyResultRepository.commit()
            except Exception as e1:
                self.__log.d('addCandleBuyResult() commit() exception')
                self.__log.d(str(e1))
                sys.exit(0)

            try:
                values = self.__candleListRepository.readCandleList(currency.symbol)
                if len(values) > 0:
                    self.runDeleteCandleBySymbol(currency.symbol)
                    # update completeList
                    now = KowanasTime.getKST()
                    completeData = [-1, idx, currency.symbol, now.strftime('%Y-%m-%d %H:%M'), '']
                    self.__candleCompleteListRepository.addCompleteList(completeData)
                    self.__candleCompleteListRepository.commit()
            except Exception as e2:
                self.__log.d('runDeleteCandleBySymbol() addCompleteList() exception')
                self.__log.d(str(e2))
                sys.exit(0)
            idx += 1

        return

    def runSellOperation(self):
        tradeList = {}
        self.__candleSellResultRepository.cleanResultSellCandle()
        self.__candleSellResultRepository.commit()
        self.__log.d('runSellOperation  condition : ', self.__sellConditions)
        idx = 0

        sleepCnt = 0
        for currency in self.__currencies:
            # if currency.symbol != 'BNXUSDT':
            #     continue
            values = self.__candleBuyResultRepository.readCandleBuyResultList(currency.symbol, self.__dataPeriodForSell)
            tradeList[currency.symbol] = []
            self.__log.d(currency.symbol, ' ---------- candle next ---------- index = ', idx)

            for value in values:
                min5Status = ''
                tradeInfo = TradeInfoAdapter.createFromBinance(value)
                # if value[0] != 4097:
                #     continue
                # if tradeInfo.buyPrice != 0.15785:
                #     continue
                sleepCnt += 1
                if sleepCnt > self.__sleepCnt:
                    time.sleep(self.__sleepTime3)
                    sleepCnt = 0

                buyTime_ = 0
                if value[14] % 300 != 0:
                    buyTime_ = value[14] - 300
                else:
                    buyTime_ = value[14]
                values5Min = self.__tradingCenter.fetch5MinCandle(currency.symbol, buyTime_ * 1000, 6)
                if float(values5Min[0].close) >= float(values5Min[1].close):
                    tick2HighPriceTickNum = 0
                    buyHTickPrice = float(values5Min[0].close)
                else:
                    tick2HighPriceTickNum = 0
                    buyHTickPrice = float(values5Min[1].close)

                for value5Min in values5Min:
                    open5Min = float(value5Min.open)
                    close5Min = float(value5Min.close)

                    if open5Min < close5Min:
                        min5Status = min5Status + '+ '
                    elif open5Min > close5Min:
                        min5Status = min5Status + '- '
                    else:
                        min5Status = min5Status + '0 '

                if self.__sellConditions == 'TRAILING_STOP_1TICK_BY_CLOSE_PRICE_FOR' \
                        or self.__sellConditions == 'TRAILING_STOP_1TICK_BY_CLOSE_PRICE_REV':
                    data = [-1, currency.symbol, tradeInfo.position, tradeInfo.buyTime, tradeInfo.buyPrice,
                            tradeInfo.buy2BolPercent,
                            tradeInfo.triggerTime, tradeInfo.triggerPrice, tradeInfo.bolHigh, tradeInfo.bolLow, 0,
                            0, 0, 0, 0, 0,
                            0, self.__sellConditions, tradeInfo.coinIndex, tradeInfo.high, tradeInfo.low,
                            tradeInfo.high2BolPercent, tradeInfo.low2BolPercent, 0, 0, 0,
                            0, 0, 0, 0, 0,
                            min5Status, '', 0, 0, 0,
                            '', 0, 0, 0, 0,
                            0, 0, 0, 0, '',
                            0, 0, 0, 0, 0,
                            0, 0, 0, '', tradeInfo.addBuyCount,
                            tradeInfo.addMBuyCount, tradeInfo.buyMode, tick2HighPriceTickNum, buyHTickPrice, '',
                            0, 0, 0]
                    if not self.runConditionTrailingStop1TickByClosePrice(currency, data):
                        self.__log.d(currency.symbol,
                                     ' runConditionTrailingStopByClosePrice() error happened. skip buyTime=',
                                     tradeInfo.buyTime)

                try:
                    self.__log.d(currency.symbol, ' add record tradeInfo buyTime = ', tradeInfo.buyTime)
                    if self.__sellConditions == 'TRAILING_STOP_1TICK_BY_CLOSE_PRICE_FOR' \
                            or self.__sellConditions == 'TRAILING_STOP_1TICK_BY_CLOSE_PRICE_REV':
                        buyTime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data[3] + 32400))
                        triggerTime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data[6] + 32400))
                        sellTime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data[11] + 32400))
                        # if data[23] == 0:
                        #     additionalTradeTime = 0
                        # else:
                        #     additionalTradeTime = time.strftime('%Y-%m-%d %H:%M:%S',
                        #                                         time.localtime(data[23] + 32400))
                        if data[26] == 0:
                            orgBuyTime = ''
                        else:
                            orgBuyTime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data[26] + 32400))
                        data[3] = buyTime
                        data[6] = triggerTime
                        if tradeInfo.addMBuyCount < self.__triggerMTotalCnt:
                            data[10] = round(data[10] * (tradeInfo.addMBuyCount + 1) / (self.__triggerMTotalCnt + 1),
                                             currency.quantityPrecision)
                        else:
                            data[10] = round(data[10] * (tradeInfo.addBuyCount + 1), currency.quantityPrecision)
                        data[11] = sellTime
                        if tradeInfo.addMBuyCount < self.__triggerMTotalCnt:
                            data[13] = round(data[13] * (tradeInfo.addMBuyCount + 1) / (self.__triggerMTotalCnt + 1),
                                             currency.pricePrecision)
                        else:
                            data[13] = round(data[13] * (tradeInfo.addBuyCount + 1), currency.pricePrecision)
                        # data[23] = additionalTradeTime
                        data[26] = orgBuyTime

                    self.__candleSellResultRepository.addCandleSellResult(data)
                    self.__candleSellResultRepository.commit()
                except Exception as e:
                    self.__log.d('runSellOperation() exception')
                    self.__log.d(str(e))

            # tradeList[currency.symbol] = []
            idx += 1
        return

    # runBuyStaticSecondOperation
    def runBuyStaticSecondOperation(self):
        for currency in self.__currencies:
            values = self.__candleBuyResultRepository.readCandleBuyResultList(currency.symbol, self.__dataPeriodForSell)
            for value in values:
                tradeInfo = TradeInfoAdapter.createFromBinance(value)
                # if tradeInfo.uid == 64:
                #     self.__log.d(currency.symbol, ' update success')
                # else:
                #     continue

                buyTime = tradeInfo.buyTime
                buyPrice = tradeInfo.buyPrice
                values5Min = self.__tradingCenter.fetch5MinCandle(currency.symbol, buyTime * 1000, 2)

                lastMin = 5 - ((buyTime / 60) % 5)
                if lastMin == 5:
                    secondBuyBasePrice = float(values5Min[-1].close)
                else:
                    secondBuyBasePrice = float(values5Min[0].close)

                aPrice = round(buyPrice - buyPrice *
                               (self.__secondAddBuyProfit / 100), currency.pricePrecision)

                if secondBuyBasePrice > round(buyPrice - buyPrice *
                                              (self.__secondAddBuyProfit / 100), currency.pricePrecision):
                    continue

                if self.__secondAddBuyBalance < 10:
                    secondBuyBalance = (self.__secondAddBuyBalance - 1) * (tradeInfo.addBuyCount + 1)
                else:
                    secondBuyBalance = self.__secondAddBuyBalance / self.__singleBalance

                if self.__secondAddBuyMaxPrice < secondBuyBalance * self.__singleBalance:
                    secondBuyBalance = round(self.__secondAddBuyMaxPrice / self.__singleBalance)

                totalBuyPrice = buyPrice * (tradeInfo.addBuyCount + 1)

                buyPrice = round((totalBuyPrice + secondBuyBasePrice * secondBuyBalance) / (
                        tradeInfo.addBuyCount + 1 + secondBuyBalance), currency.pricePrecision)

                result = self.__candleBuyResultRepository.updateSecondAddBuyCandleBuyResult(
                    tradeInfo.uid, buyPrice, secondBuyBalance)
                if result:
                    self.__candleBuyResultRepository.commit()
                    self.__log.d(currency.symbol, ' update success buyTime = ', tradeInfo.uid)
                else:
                    self.__log.d(currency.symbol, ' update fail buyTime = ', tradeInfo.uid)
        return

    def runSecondSellOperation(self):
        tradeList = {}
        self.__candleSellResultRepository.cleanResultSellCandle()
        self.__candleSellResultRepository.commit()
        self.__log.d('runSecondSellOperation  condition : ', self.__sellConditions)
        idx = 0

        sleepCnt = 0
        for currency in self.__currencies:
            # if currency.symbol != 'BNXUSDT':
            #     continue
            values = self.__candleBuyResultRepository.readCandleBuyResultList(currency.symbol, self.__dataPeriodForSell)
            tradeList[currency.symbol] = []
            self.__log.d(currency.symbol, ' ---------- candle next ---------- index = ', idx)

            for value in values:
                min5Status = ''
                tradeInfo = TradeInfoAdapter.createFromBinance(value)
                # if value[0] != 4097:
                #     continue
                # if tradeInfo.buyPrice != 0.15785:
                #     continue
                # if tradeInfo.uid == 64:
                #     self.__log.d(currency.symbol, ' update success')
                # else:
                #     continue

                sleepCnt += 1
                if sleepCnt > self.__sleepCnt:
                    time.sleep(self.__sleepTime3)
                    sleepCnt = 0

                buyTime_ = 0
                if value[14] % 300 != 0:
                    buyTime_ = value[14] - 300
                else:
                    buyTime_ = value[14]
                values5Min = self.__tradingCenter.fetch5MinCandle(currency.symbol, buyTime_ * 1000, 6)
                if float(values5Min[0].close) >= float(values5Min[1].close):
                    tick2HighPriceTickNum = 0
                    buyHTickPrice = float(values5Min[0].close)
                else:
                    tick2HighPriceTickNum = 0
                    buyHTickPrice = float(values5Min[1].close)

                if self.__secondAddBuyEnable == 1:
                    if float(values5Min[0].high) >= float(values5Min[1].high):
                        high2Ticks = float(values5Min[0].high)
                    else:
                        high2Ticks = float(values5Min[1].high)

                for value5Min in values5Min:
                    open5Min = float(value5Min.open)
                    close5Min = float(value5Min.close)

                    if open5Min < close5Min:
                        min5Status = min5Status + '+ '
                    elif open5Min > close5Min:
                        min5Status = min5Status + '- '
                    else:
                        min5Status = min5Status + '0 '

                if self.__secondAddBuyEnable == 1:
                    if tradeInfo.addMBuyCount > 0:
                        if self.__secondAddBuyLossCut == 0:
                            lossCutPrice = high2Ticks
                            self.__lossCutRate = lossCutPrice / tradeInfo.buyPrice * 100 - 100
                            defaultLossCut = 2
                            if self.__lossCutRate < defaultLossCut:
                                self.__log.d(currency.symbol, ' uid=', value[0], ' lossCutRate = ', self.__lossCutRate,
                                             ' set ', defaultLossCut)
                                self.__lossCutRate = defaultLossCut
                        tradeInfo.buyPrice = tradeInfo.triggerPrice
                        tradeInfo.addBuyCount = tradeInfo.addBuyCount + tradeInfo.addMBuyCount
                        self.__expireTimeToSell = self.__secondAddBuySellTime
                        self.__sellCountPerInterval = self.__secondAddBuySellStart
                    else:
                        self.__lossCutRate = float(self.__config.configs.get('LOSS_CUT_RATE'))
                    self.__log.d(currency.symbol, ' uid=', value[0], ' lossCutRate = ', self.__lossCutRate)

                if self.__sellConditions == 'TRAILING_STOP_1TICK_BY_CLOSE_PRICE_FOR' \
                        or self.__sellConditions == 'TRAILING_STOP_1TICK_BY_CLOSE_PRICE_REV':
                    data = [-1, currency.symbol, tradeInfo.position, tradeInfo.buyTime, tradeInfo.buyPrice,
                            tradeInfo.buy2BolPercent,
                            tradeInfo.triggerTime, tradeInfo.triggerPrice, tradeInfo.bolHigh, tradeInfo.bolLow, 0,
                            0, 0, 0, 0, 0,
                            0, self.__sellConditions, tradeInfo.coinIndex, tradeInfo.high, tradeInfo.low,
                            tradeInfo.high2BolPercent, tradeInfo.low2BolPercent, 0, 0, 0,
                            0, 0, 0, 0, 0,
                            min5Status, '', 0, 0, 0,
                            '', 0, 0, 0, 0,
                            0, 0, 0, 0, '',
                            0, 0, 0, 0, 0,
                            0, 0, 0, '', tradeInfo.addBuyCount,
                            tradeInfo.addMBuyCount, tradeInfo.buyMode, tick2HighPriceTickNum, buyHTickPrice, '',
                            0, 0, 0]
                    if not self.runConditionTrailingStop1TickByClosePrice(currency, data):
                        self.__log.d(currency.symbol,
                                     ' runConditionTrailingStopByClosePrice() error happened. skip buyTime=',
                                     tradeInfo.buyTime)

                try:
                    self.__log.d(currency.symbol, ' add record tradeInfo buyTime = ', tradeInfo.buyTime)
                    if self.__sellConditions == 'TRAILING_STOP_1TICK_BY_CLOSE_PRICE_FOR' \
                            or self.__sellConditions == 'TRAILING_STOP_1TICK_BY_CLOSE_PRICE_REV':
                        buyTime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data[3] + 32400))
                        triggerTime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data[6] + 32400))
                        sellTime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data[11] + 32400))
                        # if data[23] == 0:
                        #     additionalTradeTime = ''
                        # else:
                        #     additionalTradeTime = time.strftime('%Y-%m-%d %H:%M:%S',
                        #                                         time.localtime(data[23] + 32400))
                        if data[26] == 0:
                            orgBuyTime = ''
                        else:
                            orgBuyTime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data[26] + 32400))
                        data[3] = buyTime
                        data[6] = triggerTime
                        if tradeInfo.addMBuyCount < self.__triggerMTotalCnt:
                            data[10] = round(data[10] * (tradeInfo.addMBuyCount + 1) / (self.__triggerMTotalCnt + 1),
                                             currency.quantityPrecision)
                        else:
                            data[10] = round(data[10] * (tradeInfo.addBuyCount + 1), currency.quantityPrecision)
                        data[11] = sellTime
                        if tradeInfo.addMBuyCount < self.__triggerMTotalCnt:
                            data[13] = round(data[13] * (tradeInfo.addMBuyCount + 1) / (self.__triggerMTotalCnt + 1),
                                             currency.pricePrecision)
                        else:
                            data[13] = round(data[13] * (tradeInfo.addBuyCount + 1), currency.pricePrecision)
                        # data[23] = additionalTradeTime
                        data[26] = orgBuyTime

                    self.__candleSellResultRepository.addCandleSellResult(data)
                    self.__candleSellResultRepository.commit()
                except Exception as e:
                    self.__log.d('runSellOperation() exception')
                    self.__log.d(str(e))

            # tradeList[currency.symbol] = []
            idx += 1
        return

    def runDeleteCandleBySymbol(self, symbol):
        try:
            self.__candleListRepository.deleteCandleBySymbol(symbol)
            self.__log.d(symbol, ' delete symbol')
            self.__candleListRepository.commit()
        except Exception as e:
            self.__log.d('critical error runDeleteCandleBySymbol() exception')
            self.__log.d(str(e))
            sys.exit(0)

    def runUnComplatedBuy(self):
        try:
            completeList = self.__candleCompleteListRepository.read()
            values = self.__candleBuyResultRepository.readBuyTimeBuyResultList()
            for value in values:
                skipDelete = 0
                for complete in completeList:
                    if complete[2] == value[0]:
                        skipDelete = 1
                        self.__log.d(value[0], ' already completed.. skip delete')
                        break
                if skipDelete == 1:
                    continue
                # if value[1] > 1659279600:  # 2022. 08. 01
                #     self.__candleListRepository.deleteCandleBySymbol(value[0])
                #     self.__log.d(value[0], ' delete symbol')
                # else:
                deleteTime = (value[1] + self.__duplicateForbidTime) * 1000
                self.__candleListRepository.deleteCandleByTime(value[0], deleteTime)
                self.__log.d(value[0], ' delete until last.. last=', deleteTime)
            self.__candleListRepository.commit()
        except Exception as e:
            self.__log.d('runUnComplatedBuy() exception')
            self.__log.d(str(e))
            sys.exit(0)

    # Test No 3
    def runFundingBuy(self, index, symbol):
        candles = {}
        _fromFollowMin = 0
        startSymbol = symbol
        if startSymbol is None and self.__specificIndexFrom == 0:
            self.__candleBuyResultRepository.cleanResultBuyCandle()
            self.__candleBuyResultRepository.commit()
        if startSymbol is not None:
            try:
                self.runUnComplatedBuy()
            except Exception as e:
                sys.exit(0)
        idx = index
        for currency in self.__currencies:
            values = self.__candleListRepository.readCandleList(currency.symbol)
            candles[currency.symbol] = []
            for value in values:
                data = CandleResultAdapter.createFromBinance(value)
                candles[currency.symbol].append(data)
            index = 0
            self.__log.d(currency.symbol, ' ---------- candle next ---------- index = ', idx)
            try:
                while len(candles[currency.symbol]) > index:
                    candle = candles[currency.symbol][index]
                    tm = time.localtime(candle.candleTime / 1000)
                    if tm.tm_hour == 1 or tm.tm_hour == 9 or tm.tm_hour == 17:
                        fundingRate = self.__tradingCenter.getFundingRate(currency.symbol, candle.candleTime, 1)
                        if fundingRate is not None and len(fundingRate) == 1:
                            if fundingRate[0].fundingRate > self.__fundingTriggerPer:
                                index += 1
                                continue

                        # buy logic
                        self.__log.d(currency.symbol, ' start buy ', index)
                    index += 1

            except Exception as e:
                self.__log.d('========= add error index and other info ===========')
                self.__log.d('========= symbol=', currency.symbol, ' symbol idx=', idx, ' list index=', index)
                self.__log.d(str(e))
                sys.exit(0)

    def runBtcEthGradientOperation(self):
        values = self.__candleSellResultRepository.readBuyTimeCandleSellResultList()
        for value in values:
            buyTime = datetime.strptime(value, '%Y-%m-%d %H:%M:%S').timestamp()
            min1BuyTime = buyTime - 60 * 20
            if buyTime % 300 == 0:
                min5BuyTime = buyTime - 300 * 20
            else:
                min5BuyTime = buyTime - 300 * 21

            # BTC
            valuesMin1 = self.__tradingCenter.fetch1MinCandle('BTCUSDT', min1BuyTime * 1000, 21)
            bolDataMin1 = [float(value1Min.close) for value1Min in valuesMin1]
            beforeMin1BolData = list(bolDataMin1)
            del beforeMin1BolData[-1]
            del bolDataMin1[0]
            bolMin1 = self.__calcBollingerDown(bolDataMin1)
            bolBeforeMin1 = self.__calcBollingerDown(beforeMin1BolData)
            bolMin1GradientBTC = round((bolMin1[1] - bolBeforeMin1[1]) / bolBeforeMin1[1] * 100, 4)

            valuesMin5 = self.__tradingCenter.fetch5MinCandle('BTCUSDT', min5BuyTime * 1000, 21)
            bolDataMin5 = [float(value5Min.close) for value5Min in valuesMin5]
            beforeMin5BolData = list(bolDataMin5)
            del beforeMin5BolData[-1]
            del bolDataMin5[0]
            bolMin5 = self.__calcBollingerDown(bolDataMin5)
            bolBeforeMin5 = self.__calcBollingerDown(beforeMin5BolData)
            bolMin5GradientBTC = round((bolMin5[1] - bolBeforeMin5[1]) / bolBeforeMin5[1] * 100, 4)

            # ETH
            valuesMin1 = self.__tradingCenter.fetch1MinCandle('ETHUSDT', min1BuyTime * 1000, 21)
            bolDataMin1 = [float(value1Min.close) for value1Min in valuesMin1]
            beforeMin1BolData = list(bolDataMin1)
            del beforeMin1BolData[-1]
            del bolDataMin1[0]
            bolMin1 = self.__calcBollingerDown(bolDataMin1)
            bolBeforeMin1 = self.__calcBollingerDown(beforeMin1BolData)
            bolMin1GradientETH = round((bolMin1[1] - bolBeforeMin1[1]) / bolBeforeMin1[1] * 100, 4)

            valuesMin5 = self.__tradingCenter.fetch5MinCandle('BTCUSDT', min5BuyTime * 1000, 21)
            bolDataMin5 = [float(value5Min.close) for value5Min in valuesMin5]
            beforeMin5BolData = list(bolDataMin5)
            del beforeMin5BolData[-1]
            del bolDataMin5[0]
            bolMin5 = self.__calcBollingerDown(bolDataMin5)
            bolBeforeMin5 = self.__calcBollingerDown(beforeMin5BolData)
            bolMin5GradientETH = round((bolMin5[1] - bolBeforeMin5[1]) / bolBeforeMin5[1] * 100, 4)

            result = self.__candleSellResultRepository.updateBolGradient(value, bolMin1GradientBTC, bolMin5GradientBTC,
                                                                         bolMin1GradientETH, bolMin5GradientETH)
            if result:
                self.__candleBuyResultRepository.commit()
                self.__candleSellResultRepository.commit()
                self.__log.d('update success buyTime = ', buyTime)
            else:
                self.__log.d('update fail buyTime = ', buyTime)

    def runConditionTrailingStop1TickByClosePrice(self, currency, data):
        position = data[2]
        buyTime = data[3]
        buyPrice = data[4]
        quantity = 0
        orgBuyPrice = buyPrice
        orgBuyTime = buyTime
        orgQuantity = round(self.__singleBalance / buyPrice, currency.quantityPrecision)
        lossCutPrice = 0
        self.__trailingStopStartFrom = 0
        shortTermLossCutSellStatus = 0
        singleBalance = self.__singleBalance
        additionalTradeTime = 0
        additionalTradePrice = 0
        tradeTimes = 0
        status = 'NONE'
        second5MinStatus = 'NONE'  # NONE, START, B_LOW_STATUS
        second5MinContinueTime = 0
        lossCutBolHigh = 0
        lossCutPerBolStatus = 0  # 1 : 5min 2tick check  2 : 5min 3tick check(papapa)
        lossCutLimitPercent = 0
        followSellStatus = 0
        min1Status = ''
        safeLC2nd5MinPrice = 0
        safeLC2nd5MinTime = 0
        min15HighPrice = 0
        min15HighPer = 0
        expireHighPrice = 0
        expireHighPer = 0
        buyHTickPrice = data[59]
        h12HighDate = ''
        h12Hour = 0
        h12HighPrice = 0
        h12HighPer = 0

        sellTime = sellPrice = profitPrice = profitPercent = totalProfitPercent = stopPrice = startPrice = \
            trailingLow = sellTimeLC = sellPriceLC = openPriceLC = closePriceLC = profitPriceLC = profitPercentLC = \
            highPriceLC = 0

        openPrice = highPrice = 0

        remainMinTime = buyTime % 3600
        remainHourTime = buyTime - remainMinTime
        remainMin = remainMinTime / 60
        baseMin5 = remainMin - (remainMin % 5)
        tick2Min5 = baseMin5 * 60 + 600
        waitingTick2BuyTime = remainHourTime + tick2Min5

        if self.__sellConditions == 'TRAILING_STOP_1TICK_BY_CLOSE_PRICE_REV':
            if position == 'LONG':
                position = 'SHORT'
            else:
                position = 'LONG'

        if self.__safeLCEnable == 1 and position == 'SHORT':
            valuesMin5Bol = None
            redCount = 0
            min5BuyTime = buyTime - 19 * 300 + 1
            valuesMin5Bol = self.__tradingCenter.fetch5MinCandle(currency.symbol, min5BuyTime * 1000, 20)
            if float(valuesMin5Bol[-2].close) < float(valuesMin5Bol[-2].open):
                redCount = -2
            else:
                redCount = -1

            if valuesMin5Bol is not None:
                safeLC2nd5MinPrice = float(valuesMin5Bol[redCount].close)
                safeLC2nd5MinTime = valuesMin5Bol[redCount].closeTime / 1000

        if status != 'SOLDOUT':
            if self.__TrailingStopLossCutSellEnable == 1:
                if buyTime % 300 == 0:
                    min5BuyTime = buyTime
                else:
                    min5BuyTime = buyTime - 300
                values = self.__tradingCenter.fetch5MinCandle(currency.symbol, min5BuyTime * 1000, 2)
                shortTermlossCutPrice = float(values[0].close)

            if position == 'LONG':
                lossCutPrice = round(buyPrice + buyPrice * self.__lossCutPercent / 100, currency.pricePrecision)
            elif position == 'SHORT':
                lossCutPrice = round(buyPrice - buyPrice * self.__lossCutPercent / 100, currency.pricePrecision)

            quantity = round(singleBalance / buyPrice, currency.quantityPrecision)
            expireTimeCnt = math.ceil(self.__expireTimeToSell / (self.__TrailingStopInterval * 60))
            requestBuyTime = math.floor(buyTime / (self.__TrailingStopInterval * 60)) * self.__TrailingStopInterval * 60

            if self.__TrailingStopInterval == 3:
                values = self.__tradingCenter.fetch3MinCandle(currency.symbol, requestBuyTime * 1000, expireTimeCnt)
            elif self.__TrailingStopInterval == 5:
                values = self.__tradingCenter.fetch5MinCandle(currency.symbol, requestBuyTime * 1000, expireTimeCnt)
            elif self.__TrailingStopInterval == 15:
                values = self.__tradingCenter.fetch15MinCandle(currency.symbol, requestBuyTime * 1000, expireTimeCnt)
            elif self.__TrailingStopInterval == 30:
                values = self.__tradingCenter.fetch30MinCandle(currency.symbol, requestBuyTime * 1000, expireTimeCnt)
            else:
                values = self.__tradingCenter.fetch1MinCandle(currency.symbol, requestBuyTime * 1000, expireTimeCnt)

            if position == 'LONG':
                startPrice = buyPrice + buyPrice * self.__trailingStopStartFrom / 100
            elif position == 'SHORT':
                startPrice = buyPrice - buyPrice * self.__trailingStopStartFrom / 100
            else:
                self.__log.d(currency.symbol, ' FATAL ERROR')

            if self.__TrailingStopLossCutSellEnable == 1:
                limitInterval = self.__TrailingStopLossCutSellInterval + self.__TrailingStopLossCutSellAfterTime
                lcValues = self.__tradingCenter.fetch1MinCandle(currency.symbol, waitingTick2BuyTime * 1000,
                                                                limitInterval)
                idx = 0
                for value in lcValues:
                    if idx == 0 or idx < self.__TrailingStopLossCutSellAfterTime:
                        idx += 1
                        continue
                    close = float(value.close)
                    openP = float(value.open)
                    highP = float(value.high)
                    if position == 'SHORT':
                        if self.__TrailingStopLossCutSellAfterTime <= idx < limitInterval:
                            if shortTermlossCutPrice < close:
                                sellPriceLC = closePriceLC = close
                                openPriceLC = openP
                                highPriceLC = highP
                                sellTimeLC = value.closeTime / 1000
                                profitPercentLC = 100 - round(sellPriceLC / buyPrice * 100, 3)
                                profitPriceLC = round(profitPercentLC * singleBalance / 100 - singleBalance * self.__tradingFee * 0.01, 3)
                                self.totalPrice = round(self.totalPriceLC + profitPriceLC, 2)
                                shortTermLossCutSellStatus = 1
                                self.shortTermLossCutTotalCnt += 1
                                self.__log.d(currency.symbol, ' ### Short term loss cut status. SHORT count=',
                                             self.shortTermLossCutTotalCnt)
                                break
                    idx += 1

            if self.__safeLCEnable == 1 and position == 'SHORT' and safeLC2nd5MinPrice > 0 \
                    and lossCutPerBolStatus == 0 and shortTermLossCutSellStatus == 0:
                limitInterval = self.__expireTimeToSell / 60  # 70
                standByTime = round((safeLC2nd5MinTime - buyTime) / 60)
                safeLCPrice = safeLC2nd5MinPrice + safeLC2nd5MinPrice * self.__safeLCPercent / 100

                lcValues = self.__tradingCenter.fetch1MinCandle(currency.symbol, buyTime * 1000, limitInterval)
                idx = 0
                for value in lcValues:
                    if idx == 0 or idx < standByTime:
                        idx += 1
                        continue
                    close = float(value.close)
                    openP = float(value.open)
                    highP = float(value.high)

                    if standByTime <= idx < limitInterval:
                        if safeLCPrice < close:
                            sellPriceLC = closePriceLC = close
                            openPriceLC = openP
                            highPriceLC = highP
                            sellTimeLC = value.closeTime / 1000
                            profitPercentLC = 100 - round(sellPriceLC / buyPrice * 100, 3)
                            profitPriceLC = round(profitPercentLC * singleBalance / 100 - singleBalance * self.__tradingFee * 0.01, 3)
                            self.totalPrice = round(self.totalPriceLC + profitPriceLC, 2)
                            shortTermLossCutSellStatus = 9
                            self.shortTermLossCutTotalCnt += 1
                            self.__log.d(currency.symbol, ' ### Short term safe loss cut status. SHORT count=',
                                         self.shortTermLossCutTotalCnt)
                            break
                    idx += 1

            index = 0
            for value in values:
                if self.__sellCountPerInterval > 2:
                    if index <= self.__sellCountPerInterval - 2:
                        index += 1
                        continue
                else:
                    if index == 0:
                        index += 1
                        continue
                close = float(value.close)
                openP = float(value.open)
                highP = float(value.high)
                if second5MinContinueTime > 0:
                    if second5MinContinueTime > value.openTime:
                        index += 1
                        continue

                if self.__lossSellFirst == 1:
                    if position == 'SHORT':
                        if lossCutPrice < close:
                            sellTime = value.closeTime / 1000
                            sellPrice = closePrice = close
                            openPrice = openP
                            highPrice = highP
                            profitPercent = round(100 - sellPrice / buyPrice * 100, 3)
                            profitPrice = round(profitPercent * singleBalance / 100 - singleBalance * self.__tradingFee * 0.01, 3)
                            self.totalPrice = round(self.totalPrice + profitPrice, 2)
                            break
                        elif index == expireTimeCnt - 1 or index == len(values) - 1:
                            sellTime = value.closeTime / 1000
                            sellPrice = closePrice = close
                            openPrice = openP
                            highPrice = highP
                            profitPercent = round(100 - sellPrice / buyPrice * 100, 3)
                            profitPrice = round(profitPercent * singleBalance / 100 - singleBalance * self.__tradingFee * 0.01, 3)
                            self.totalPrice = round(self.totalPrice + profitPrice, 2)
                            break
                        else:
                            self.__log.d(currency.symbol, ' continue to go down SHORT')
                else:
                    if position == 'SHORT':
                        if lossCutPrice > close:
                            sellTime = value.closeTime / 1000
                            sellPrice = closePrice = close
                            openPrice = openP
                            highPrice = highP
                            profitPercent = round(100 - sellPrice / buyPrice * 100, 3)
                            profitPrice = round(profitPercent * singleBalance / 100 - singleBalance * self.__tradingFee * 0.01, 3)
                            self.totalPrice = round(self.totalPrice + profitPrice, 2)
                            break
                        elif index == expireTimeCnt - 1 or index == len(values) - 1:
                            sellTime = value.closeTime / 1000
                            sellPrice = closePrice = close
                            openPrice = openP
                            highPrice = highP
                            profitPercent = round(100 - sellPrice / buyPrice * 100, 3)
                            profitPrice = round(profitPercent * singleBalance / 100 - singleBalance * self.__tradingFee * 0.01, 3)
                            self.totalPrice = round(self.totalPrice + profitPrice, 2)
                            break
                        else:
                            self.__log.d(currency.symbol, ' continue to go down SHORT')
                index += 1

            if shortTermLossCutSellStatus == 1 or shortTermLossCutSellStatus == 9:
                if sellTimeLC <= sellTime:
                    sellTime = sellTimeLC
                    sellPrice = sellPriceLC
                    closePrice = closePriceLC
                    openPrice = openPriceLC
                    highPrice = highPriceLC
                    profitPercent = profitPercentLC
                    profitPrice = profitPriceLC
                else:
                    shortTermLossCutSellStatus = 0

        buyTimeStr = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(buyTime))
        self.__log.d(currency.symbol, ' ', position, ' buyTime=', buyTimeStr, ' profitPercent=', profitPercent)
        if singleBalance < self.__singleBalance:
            profitPrice = round(profitPrice - (self.__singleBalance - singleBalance) / 100, 3)
            self.__log.d(currency.symbol, '***************** Need to check ********************')

        if 0 < self.__lossCutRate < 200:
            min1TimeCnt = math.ceil((sellTime - buyTime) / 60) + 1

            if (expireTimeCnt + 1) * self.__TrailingStopInterval < min1TimeCnt:
                self.__log.d(currency.symbol, ' FATAL sellTime is wrong.. set 0 values')
                data[13] = 0
                data[14] = 0
                return True

            idx = 0
            valuesMin1 = self.__tradingCenter.fetch1MinCandle(currency.symbol, buyTime * 1000, min1TimeCnt)
            waitingTick2BuyPrice = float(valuesMin1[0].close)
            if position == 'SHORT':
                if self.__highPerDataEnable == 1:
                    idxExpire = 0
                    expireTimeCnt = math.ceil(self.__expireTimeToSell / 60)
                    valuesMin1_ = self.__tradingCenter.fetch1MinCandle(currency.symbol, buyTime * 1000, expireTimeCnt)
                    for value in valuesMin1_:
                        high = float(value.high)
                        if high > min15HighPrice and idxExpire < 15:
                            min15HighPrice = high
                        if high > expireHighPrice:
                            expireHighPrice = high
                        idxExpire += 1
                    min15HighPer = round(min15HighPrice / buyPrice * 100 - 100, 1)
                    expireHighPer = round(expireHighPrice / buyPrice * 100 - 100, 1)

                    expire12HCnt = 12
                    valuesH12 = self.__tradingCenter.fetch60MinCandle(currency.symbol, (buyTime - 3600) * 1000, 12)
                    idxExpire = 0
                    for value in valuesH12:

                        high = float(value.high)
                        if high > h12HighPrice:
                            h12HighPrice = high
                            h12HighDate = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(value.openTime / 1000))
                            h12Hour = idxExpire
                        idxExpire += 1
                    h12HighPer = round(h12HighPrice / buyPrice * 100 - 100, 1)

                for value in valuesMin1:
                    close = float(value.close)
                    if self.__lossCutMarketRate > 0 \
                            and float(value.high) > buyPrice + buyPrice * self.__lossCutMarketRate / 100:
                        if (value.closeTime / 1000) < sellTime:
                            sellTime = value.closeTime / 1000
                            sellPrice = closePrice = round(buyPrice + buyPrice * self.__lossCutMarketRate / 100,
                                                           currency.pricePrecision)
                            openPrice = float(value.open)
                            highPrice = float(value.high)
                            profitPercent = round(100 - sellPrice / buyPrice * 100, 3)
                            profitPrice = round(profitPercent * singleBalance / 100 - singleBalance * self.__tradingFee * 0.01, 3)
                            self.totalPrice = round(self.totalPrice + profitPrice, 2)
                            lossCutPerBolStatus = 0
                            lossCutBolHigh = 0
                            lossCutLimitPercent = 1
                        break
                    # elif close > buyPrice + buyPrice * self.__lossCutRate / 100:
                    elif close > buyHTickPrice + buyHTickPrice * self.__lossCutRate / 100:
                        if (value.closeTime / 1000) < sellTime:
                            sellTime = value.closeTime / 1000
                            sellPrice = closePrice = close
                            openPrice = float(value.open)
                            highPrice = float(value.high)
                            profitPercent = round(100 - sellPrice / buyPrice * 100, 3)
                            profitPrice = round(profitPercent * singleBalance / 100 - singleBalance * self.__tradingFee * 0.01, 3)
                            self.totalPrice = round(self.totalPrice + profitPrice, 2)
                            lossCutPerBolStatus = 0
                            lossCutBolHigh = 0
                            lossCutLimitPercent = 1
                        break
                    idx += 1
        else:
            min1TimeCnt = math.ceil((sellTime - buyTime) / 60) + 1

            if (expireTimeCnt + 1) * self.__TrailingStopInterval < min1TimeCnt:
                self.__log.d(currency.symbol, ' FATAL sellTime is wrong.. set 0 values')
                data[13] = 0
                data[14] = 0
                return True

            idx = 0
            valuesMin1 = self.__tradingCenter.fetch1MinCandle(currency.symbol, buyTime * 1000, min1TimeCnt)
            waitingTick2BuyPrice = float(valuesMin1[0].close)
            if position == 'SHORT':
                if self.__highPerDataEnable == 1:
                    idxExpire = 0
                    expireTimeCnt = math.ceil(self.__expireTimeToSell / 60)
                    valuesMin1_ = self.__tradingCenter.fetch1MinCandle(currency.symbol, buyTime * 1000, expireTimeCnt)
                    for value in valuesMin1_:
                        high = float(value.high)
                        if high > min15HighPrice and idxExpire < 15:
                            min15HighPrice = high
                        if high > expireHighPrice:
                            expireHighPrice = high
                        idxExpire += 1
                    min15HighPer = round(min15HighPrice / buyPrice * 100 - 100, 1)
                    expireHighPer = round(expireHighPrice / buyPrice * 100 - 100, 1)

                    expire12HCnt = 12
                    valuesH12 = self.__tradingCenter.fetch60MinCandle(currency.symbol, (buyTime - 3600) * 1000, 12)
                    idxExpire = 0
                    for value in valuesH12:
                        high = float(value.high)
                        if high > h12HighPrice:
                            h12HighPrice = high
                            now = datetime.utcnow()
                            self.__log.d("현재 시간:", now)
                            h12HighDate = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(value.openTime / 1000))
                            h12Hour = idxExpire
                        idxExpire += 1
                    h12HighPer = round(h12HighPrice / buyPrice * 100 - 100, 1)

        if self.__followSellEnable == 1 and lossCutLimitPercent == 0 and lossCutPerBolStatus == 0 \
                and shortTermLossCutSellStatus == 0 and profitPrice > 0:
            isBigGap = False
            gapMin1Time = (buyTime - self.__followSellGapTime * 60) * 1000
            valuesGapMin1Before = self.__tradingCenter.fetch1MinCandle(currency.symbol, gapMin1Time, 1)
            valuesGapH1After = self.__tradingCenter.fetch60MinCandle(currency.symbol, (buyTime - 3600) * 1000, 1)
            if valuesGapMin1Before is not None and len(valuesGapMin1Before) == 1 \
                    and valuesGapH1After is not None and len(valuesGapH1After) == 1:
                beforePrice = float(valuesGapMin1Before[0].close)
                afterPrice = float(valuesGapH1After[0].close)

                if beforePrice + beforePrice * 0.01 * self.__followSellGapPer < afterPrice:
                    isBigGap = True

            if isBigGap:
                min1Time = (sellTime - 20 * 60) * 1000
                valuesMin1 = self.__tradingCenter.fetch1MinCandle(currency.symbol, min1Time, 120)
                idx = 0
                bolData = []
                bol = []
                oldBol = []
                for value in valuesMin1:
                    close = float(value.close)
                    openP = float(value.open)
                    highP = float(value.high)
                    if idx < 20:
                        bolData.append(close)
                        if idx == 19:
                            oldBol = self.__calcBollingerDown(bolData)
                        idx += 1
                        continue
                    else:
                        if idx != 20:
                            oldBol = bol
                        del bolData[0]
                        bolData.append(close)
                    bol = self.__calcBollingerDown(bolData)

                    if position == 'LONG':
                        if idx == 20 and (bol[1] > close or oldBol[1] > bol[1]):
                            break

                        if close < bol[1] < oldBol[1] or idx == 199:
                            sellTime = value.closeTime / 1000
                            sellPrice = closePrice = close
                            openPrice = openP
                            highPrice = highP
                            profitPercent = round(sellPrice / buyPrice * 100 - 100, 3)
                            profitPrice = round(profitPercent * singleBalance / 100 - singleBalance * self.__tradingFee * 0.01, 3)
                            self.totalPrice = round(self.totalPrice + profitPrice, 2)
                            followSellStatus = 1
                            break

                    elif position == 'SHORT':
                        if idx == 20 and (bol[1] < close or oldBol[1] < bol[1]):
                            break

                        if close > bol[1] > oldBol[1] or idx == 199:
                            sellTime = value.closeTime / 1000
                            sellPrice = closePrice = close
                            openPrice = openP
                            highPrice = highP
                            profitPercent = round(100 - sellPrice / buyPrice * 100, 3)
                            profitPrice = round(profitPercent * singleBalance / 100 - singleBalance * self.__tradingFee * 0.01, 3)
                            self.totalPrice = round(self.totalPrice + profitPrice, 2)
                            followSellStatus = 1
                            break
                    idx += 1

        data[2] = position
        data[3] = buyTime
        data[4] = buyPrice
        data[10] = quantity
        data[11] = sellTime
        data[12] = round(sellPrice, currency.pricePrecision)
        data[13] = round(profitPrice)
        data[14] = profitPercent
        data[15] = self.totalPrice
        data[16] = totalProfitPercent
        data[23] = 0
        # data[23] = additionalTradeTime / 1000
        data[24] = additionalTradePrice
        data[25] = quantity * buyPrice
        data[26] = orgBuyTime
        data[27] = orgBuyPrice
        data[28] = orgQuantity
        data[29] = shortTermLossCutSellStatus
        data[30] = tradeTimes
        data[32] = second5MinStatus
        data[33] = lossCutBolHigh
        data[34] = round(lossCutPerBolStatus, currency.pricePrecision)
        data[35] = followSellStatus
        data[36] = min1Status

        data[51] = buyTime
        data[52] = sellTime

        data[60] = h12HighDate
        data[61] = h12Hour
        data[62] = h12HighPrice
        data[63] = h12HighPer

        if self.__highPerDataEnable == 1 and position == 'SHORT':
            data[46] = min15HighPrice
            data[47] = min15HighPer
            data[48] = expireHighPrice
            data[49] = expireHighPer

        if self.__hour1BolDataEnable == 1:
            h1BolBuyTime = buyTime - (20 * 3600)
            valuesH1Bol = self.__tradingCenter.fetch60MinCandle(currency.symbol, h1BolBuyTime * 1000, 20)
            if len(valuesH1Bol) >= 20:
                bolH1Data = [float(valueH1Bol.close) for valueH1Bol in valuesH1Bol]
                bolH1Data[19] = buyPrice
                bolH1 = self.__calcBollingerDown(bolH1Data)
                data[41] = round(bolH1[0], currency.pricePrecision)
                data[42] = round(bolH1[2], currency.pricePrecision)

                high2BolupPercentH1 = buyPrice / bolH1[0] * 100 - 100
                low2BoldownPercentH1 = 100 - buyPrice / abs(bolH1[2]) * 100
                data[43] = round(high2BolupPercentH1, 2)
                data[44] = round(low2BoldownPercentH1, 2)
                bolDataH1 = ','.join(str(e) for e in bolH1Data)
                data[45] = bolDataH1
        return True

    # Test No 3
    def runFundingBuy(self, index, symbol):
        candles = {}
        _fromFollowMin = 0
        startSymbol = symbol

        if startSymbol is None and self.__specificIndexFrom == 0:
            self.__candleBuyResultRepository.cleanResultBuyCandle()
            self.__candleBuyResultRepository.commit()

        if startSymbol is not None:
            try:
                self.runUnComplatedBuy()
            except Exception as e:
                sys.exit(0)

        idx = index

        for currency in self.__currencies:
            values = self.__candleListRepository.readCandleList(currency.symbol)
            candles[currency.symbol] = []
            for value in values:
                data = CandleResultAdapter.createFromBinance(value, 0)
                candles[currency.symbol].append(data)

            index = 0
            self.__log.d(currency.symbol, ' ---------- candle next ---------- index = ', idx)
            try:
                while len(candles[currency.symbol]) > index:
                    candle = candles[currency.symbol][index]
                    tm = time.localtime(candle.candleTime / 1000)
                    if tm.tm_hour == 1 or tm.tm_hour == 9 or tm.tm_hour == 17:
                        fundingRate = self.__tradingCenter.getFundingRate(currency.symbol, candle.candleTime, 1)
                        if fundingRate is not None and len(fundingRate) == 1:
                            if fundingRate[0].fundingRate > self.__fundingTriggerPer:
                                index += 1
                                continue

                        # buy logic
                        self.__log.d(currency.symbol, ' start buy ', index)
                    index += 1

            except Exception as e:
                self.__log.d('========= add error index and other info ===========')
                self.__log.d('========= symbol=', currency.symbol, ' symbol idx=', idx, ' list index=', index)
                self.__log.d(str(e))
                sys.exit(0)

    def runSellTrailStopOperation(self):
        tradeList = {}
        self.__candleSellResultRepository.cleanResultSellCandle()
        self.__candleSellResultRepository.commit()
        self.__log.d('runSellOperation  condition : ', self.__sellConditions)
        idx = 0
        e = None
        buyPrice = 0

        sleepCnt = 0
        for currency in self.__currencies:
            # if currency.symbol != 'CYBERUSDT':
            #     continue
            values = self.__candleBuyResultRepository.readCandleBuyResultList(currency.symbol, self.__dataPeriodForSell)
            tradeList[currency.symbol] = []
            self.__log.d(currency.symbol, ' ---------- candle next ---------- index = ', idx)

            for value in values:
                min5Status = ''
                tradeInfo = TradeInfoAdapter.createFromBinance(value)
                # if value[0] != 96:
                #     continue
                # if tradeInfo.buyPrice != 0.15785:
                #     continue
                sleepCnt += 1
                if sleepCnt > self.__sleepCnt:
                    time.sleep(self.__sleepTime3)
                    sleepCnt = 0

                buyTime_ = 0
                if value[14] % 300 != 0:
                    buyTime_ = value[14] - 300
                else:
                    buyTime_ = value[14]
                values5Min = self.__tradingCenter.fetch5MinCandle(currency.symbol, buyTime_ * 1000, 6)
                if float(values5Min[0].close) >= float(values5Min[1].close):
                    tick2HighPriceTickNum = 0
                    buyHTickPrice = float(values5Min[0].close)
                else:
                    tick2HighPriceTickNum = 0
                    buyHTickPrice = float(values5Min[1].close)

                for value5Min in values5Min:
                    open5Min = float(value5Min.open)
                    close5Min = float(value5Min.close)

                    if open5Min < close5Min:
                        min5Status = min5Status + '+ '
                    elif open5Min > close5Min:
                        min5Status = min5Status + '- '
                    else:
                        min5Status = min5Status + '0 '

                if self.__sellConditions == 'TRAILING_STOP_1TICK_BY_CLOSE_PRICE_FOR' \
                        or self.__sellConditions == 'TRAILING_STOP_1TICK_BY_CLOSE_PRICE_REV':
                    data = [-1, currency.symbol, tradeInfo.position, tradeInfo.buyTime, tradeInfo.buyPrice,
                            tradeInfo.buy2BolPercent,
                            tradeInfo.triggerTime, tradeInfo.triggerPrice, tradeInfo.bolHigh, tradeInfo.bolLow, 0,
                            0, 0, 0, 0, 0,
                            0, self.__sellConditions, tradeInfo.coinIndex, tradeInfo.high, tradeInfo.low,
                            tradeInfo.high2BolPercent, tradeInfo.low2BolPercent, 0, 0, 0,
                            0, 0, 0, 0, 0,
                            min5Status, '', 0, 0, 0,
                            '', 0, 0, 0, 0,
                            0, 0, 0, 0, '',
                            0, 0, 0, 0, 0,
                            0, 0, 0, '', tradeInfo.addBuyCount,
                            tradeInfo.addMBuyCount, tradeInfo.buyMode, tick2HighPriceTickNum, buyHTickPrice, '',
                            0, 0, 0]
                    if not self.runConditionTrailingStop1TickByClosePrice(currency, data):
                        self.__log.d(currency.symbol,
                                     ' runConditionTrailingStopByClosePrice() error happened. skip buyTime=',
                                     tradeInfo.buyTime)

                if data[14] < self.__sellTrailingStopPer:
                    buyPrice = data[4]
                    sellPrice = data[12]
                    trailingLossCutPrice = round(buyPrice + buyPrice * self.__sellTrailingStopLC / 100,
                                                 currency.pricePrecision)

                    if sellPrice < trailingLossCutPrice:
                        self.runConditionSellByTime(currency, data)

                self.__log.d(currency.symbol, ' add record tradeInfo buyTime = ', tradeInfo.buyTime)
                if self.__sellConditions == 'TRAILING_STOP_1TICK_BY_CLOSE_PRICE_FOR' \
                        or self.__sellConditions == 'TRAILING_STOP_1TICK_BY_CLOSE_PRICE_REV':
                    orgBuyT = data[3]
                    buyPrice = data[4]
                    orgSellT = data[11]
                    buyTime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data[3] + 32400))
                    triggerTime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data[6] + 32400))
                    sellTime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data[11] + 32400))
                    if data[23] == 0:
                        additionalTradeTime = ''
                    else:
                        additionalTradeTime = time.strftime('%Y-%m-%d %H:%M:%S',
                                                            time.localtime(data[23] + 32400))
                    if data[26] == 0:
                        orgBuyTime = ''
                    else:
                        orgBuyTime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data[26] + 32400))
                    data[3] = buyTime
                    data[6] = triggerTime
                    if tradeInfo.addMBuyCount < self.__triggerMTotalCnt:
                        data[10] = round(data[10] * (tradeInfo.addMBuyCount + 1) / (self.__triggerMTotalCnt + 1),
                                         currency.quantityPrecision)
                    else:
                        data[10] = round(data[10] * (tradeInfo.addBuyCount + 1), currency.quantityPrecision)
                    data[11] = sellTime
                    if tradeInfo.addMBuyCount < self.__triggerMTotalCnt:
                        data[13] = round(data[13] * (tradeInfo.addMBuyCount + 1) / (self.__triggerMTotalCnt + 1),
                                         currency.pricePrecision)
                    else:
                        data[13] = round(data[13] * (tradeInfo.addBuyCount + 1), currency.pricePrecision)

                    data[26] = orgBuyTime

                    totalBalance = (data[55] + 1) * self.__singleBalance
                    fundingRate = self.__tradingCenter.getFundingRate(currency.symbol, orgBuyT * 1000,
                                                                      orgSellT * 1000)
                    fundingPrice = 0
                    fundingTimes = 0

                    if fundingRate is not None:
                        basedFundingBalance = 0
                        fundingTimePrice = 0
                        fundingTimeProfitRate = 0
                        # orgFundingPrice = 0
                        for funding in fundingRate:
                            values = self.__tradingCenter.fetch1MinCandle(currency.symbol, round(funding.fundingTime / 1000) * 1000, 1)
                            if len(values) == 0:
                                self.__log.d('Critical error in funding fee routine')
                                sys.exit()

                            else:
                                fundingTimePrice = float(values[0].open)
                                fundingTimeProfitRate = round(100 - round(fundingTimePrice / buyPrice * 100, 3), 2)
                                basedFundingBalance = round(totalBalance + totalBalance * -1 * fundingTimeProfitRate * 0.01)

                            # self.__log.d(currency.symbol, ' fTimePrice = ', fundingTimePrice,
                            #              ' buyTimePrice = ', buyPrice, ' Balance before =', totalBalance,
                            #              ' Balance after =', basedFundingBalance)
                            fundingPrice += funding.fundingRate * basedFundingBalance
                            # orgFundingPrice += funding.fundingRate * totalBalance
                            fundingTimes += 1
                            # GMTFundingTime = round(funding.fundingTime/1000) - 3600 * 9
                            # fundingDate = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(GMTFundingTime + 32400))
                            # self.__log.d(fundingDate, ' ', currency.symbol, ' fRate = ', round(funding.fundingRate*100, 2),
                            #              ' fPrice = ', round(funding.fundingRate * basedFundingBalance, 1))
                    # fundingPrice & fundingTimes
                    data[24] = fundingPrice
                    data[23] = fundingTimes
                    # self.__log.d(currency.symbol, ' Total = ', round(fundingPrice, 1))

                    if self.__sellTrailingFundingEnable == 1:
                        data[13] += fundingPrice

                    self.__candleSellResultRepository.addCandleSellResult(data)
                    self.__candleSellResultRepository.commit()

            # tradeList[currency.symbol] = []
            idx += 1
        return

    def runConditionSellByTime(self, currency, data):
        buyTime = data[3]
        buyPrice = data[4]
        sellTime = data[11]
        singleBalance = self.__singleBalance

        isLossCut = False
        isSameProfit = False

        plusSellPrice = buyPrice - buyPrice * self.__sellTrailingStopPlusSellPer * 0.01
        plusSellStartTime = sellTime

        if buyTime % (self.__TrailingStopInterval * 60) == 0:
            requestTime = buyTime * 1000
        else:
            requestTime = (buyTime - 900) * 1000

        limit = (self.__sellTrailingStopTime + 900) / 900
        valuesMin15 = self.__tradingCenter.fetch15MinCandle(currency.symbol, requestTime, limit)

        if len(valuesMin15) != limit:
            self.__log.d(currency.symbol, ' FATAL shortage time buyTime=', buyTime, ' skip')
            return True

        for value15 in valuesMin15:
            close = float(value15.close)
            lcPrice = buyPrice + buyPrice * self.__sellTrailingStopLC / 100
            if self.__sellTrailingStopLC > 0 and float(value15.high) > lcPrice:
                sellTime = value15.closeTime / 1000
                sellPrice = round(buyPrice + buyPrice * self.__sellTrailingStopLC / 100,
                                               currency.pricePrecision)
                profitPercent = round(100 - sellPrice / buyPrice * 100, 3)
                profitPrice = round(profitPercent * singleBalance / 100 - singleBalance * self.__tradingFee * 0.01, 3)
                self.totalPrice = round(self.totalPrice + profitPrice, 2)
                isLossCut = True
                break
            elif self.__sellTrailingStopPlusEnable == 1 and plusSellStartTime < (value15.openTime / 1000) \
                    and plusSellPrice > float(value15.low):
                sellTime = value15.closeTime / 1000
                sellPrice = plusSellPrice
                profitPercent = self.__sellTrailingStopPlusSellPer
                profitPrice = 0
                isSameProfit = True
                break

        if not isLossCut and not isSameProfit:
            requestBuyTime = buyTime + self.__sellTrailingStopTime - 60
            values = self.__tradingCenter.fetch1MinCandle(currency.symbol, requestBuyTime * 1000, 1)
            if len(values) == 0:
                self.__log.d(currency.symbol, ' FATAL len(values) == 0 uid=', data[0])
                return True
            close = float(values[0].close)
            sellTime = values[0].closeTime / 1000
            sellPrice = close
            profitPercent = round(100 - sellPrice / buyPrice * 100, 3)

            if profitPercent < self.__sellTrailingStopPer2nd:
                if self.__sellTrailingStop2ndSellInterval > 0:
                    expireTime = buyTime + self.__sellTrailingStopTime2nd
                    currentTime = self.__sellTrailingStopTime
                    while (buyTime + currentTime) < expireTime:
                        if buyTime % (self.__TrailingStopInterval * 60) == 0:
                            requestTime = (buyTime + currentTime) * 1000
                        else:
                            requestTime = (buyTime + currentTime - 900) * 1000

                        limit = (self.__sellTrailingStop2ndSellInterval + 900) / 900

                        valuesMin15 = self.__tradingCenter.fetch15MinCandle(currency.symbol, requestTime, limit)

                        if len(valuesMin15) != limit:
                            self.__log.d(currency.symbol, ' FATAL shortage time buyTime=', buyTime,
                                         ' skip while trailing')
                            return True

                        for value15 in valuesMin15:
                            close = float(value15.close)
                            lcPrice = buyPrice + buyPrice * self.__sellTrailingStopLC / 100
                            if self.__sellTrailingStopLC > 0 and float(value15.high) > lcPrice:
                                sellTime = value15.closeTime / 1000
                                sellPrice = round(buyPrice + buyPrice * self.__sellTrailingStopLC / 100,
                                                  currency.pricePrecision)
                                profitPercent = round(100 - sellPrice / buyPrice * 100, 3)
                                profitPrice = round(profitPercent * singleBalance / 100 - singleBalance * self.__tradingFee * 0.01, 3)
                                self.totalPrice = round(self.totalPrice + profitPrice, 2)
                                isLossCut = True
                                break
                            elif self.__sellTrailingStopPlusEnable == 1 and plusSellPrice > float(value15.low):
                                sellTime = value15.closeTime / 1000
                                sellPrice = plusSellPrice
                                profitPercent = self.__sellTrailingStopPlusSellPer
                                profitPrice = 0
                                isSameProfit = True
                                break

                        if isLossCut or isSameProfit:
                            break
                        else:
                            requestBuyTime = buyTime + currentTime + self.__sellTrailingStop2ndSellInterval - 60
                            values = self.__tradingCenter.fetch1MinCandle(currency.symbol, requestBuyTime * 1000, 1)
                            if len(values) == 0:
                                self.__log.d(currency.symbol, ' FATAL len(values) == 0 uid=', data[0])
                                now = round(time.time()) - 60
                                values = self.__tradingCenter.fetch1MinCandle(currency.symbol, now * 1000, 1)
                                if len(values) == 0:
                                    return True
                                else:
                                    close = float(values[0].close)
                                    sellTime = values[0].closeTime / 1000
                                    sellPrice = close
                                    profitPercent = round(100 - sellPrice / buyPrice * 100, 3)
                                    break
                            close = float(values[0].close)
                            sellTime = values[0].closeTime / 1000
                            sellPrice = close
                            profitPercent = round(100 - sellPrice / buyPrice * 100, 3)

                            if profitPercent >= self.__sellTrailingStopPer2nd:
                                break

                        currentTime += self.__sellTrailingStop2ndSellInterval
                # elif self.__sellTrailingStopTime2nd > 0 and profitPercent < self.__sellTrailingStopPer2nd:
                #     self.__log.d(currency.symbol, ' run 2nd round profitPercent=', profitPercent)
                #     requestBuyTime = buyTime + self.__sellTrailingStopTime2nd - 60
                #     values2nd = self.__tradingCenter.fetch1MinCandle(currency.symbol, requestBuyTime * 1000, 1)
                #     if len(values2nd) == 0:
                #         self.__log.d(currency.symbol, ' FATAL len(values2nd) == 0 uid=', data[0])
                #         return True
                #     close = float(values2nd[0].close)
                #     sellTime = values2nd[0].closeTime / 1000
                #     sellPrice = close
                #     profitPercent = round(100 - sellPrice / buyPrice * 100, 3)

            profitPrice = round(profitPercent * singleBalance / 100 - singleBalance * self.__tradingFee * 0.01, 3)
            self.totalPrice = round(self.totalPrice + profitPrice, 2)

            buyTimeStr = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(buyTime))
            self.__log.d(currency.symbol, ' SHORT', ' buyTime=', buyTimeStr, ' profitPercent=', profitPercent)
            if singleBalance < self.__singleBalance:
                profitPrice = round(profitPrice - (self.__singleBalance - singleBalance) / 100, 3)
                self.__log.d(currency.symbol, '***************** Need to check 2********************')

        data[11] = sellTime
        data[12] = round(sellPrice, currency.pricePrecision)
        data[13] = round(profitPrice)
        data[14] = profitPercent
        data[15] = self.totalPrice

        data[52] = sellTime

        return True

    # TEST 18: independent RSI / daily Bollinger buy simulation
    def runBuyRSIBuyOperation(self, target_symbol=None, wait_minutes=60, index_from=None, index_to=None, cooldown_hours=2):
        """TEST 18: resume daily batches, then prune only obsolete source candles."""
        from bisect import insort
        from math import isfinite
        from model.RSICandleRepository import RSICandleRepository
        from trading.RSIBuyStrategy import DAY, MINUTE, QUARTER, evaluate_intraminute, minute_open_prices, validate_intraminute_state, five_minute_bars, validate_wait_minutes, cooldown_previous_buy, RSIHistoryCache, format_kst
        from trading.BinanceFuturesClient import BinanceFuturesClient

        if self.__candleInterval != 5:
            raise ValueError("TEST 18 requires CANDLE_INTERVAL=5")
        validate_wait_minutes(wait_minutes, {})
        if (isinstance(cooldown_hours, bool) or not isinstance(cooldown_hours, (int, float))
                or not isfinite(cooldown_hours) or cooldown_hours < 0):
            raise ValueError("cooldown_hours must be a finite non-negative number")
        cooldown_seconds = cooldown_hours * 3600
        repository = RSICandleRepository(self.__rsiDbConnection)
        repository.acquire_simulation_lock()
        try:
            repository.prepare_progress()
            client = None
            as_of = int(time.time() * 1000)
            saved = duplicates = 0
            source_windows = list(self.__rsiSourceWindows(repository, target_symbol, index_from, index_to))
            for index, (symbol, start, end) in source_windows:
                progress = repository.load_progress(symbol)
                cursor, rsi_state = progress if progress is not None else (start, {})
                validate_intraminute_state(rsi_state)
                validate_wait_minutes(wait_minutes, rsi_state)
                if progress is not None:
                    # Also finish any cleanup interrupted after the checkpoint commit.
                    repository.prune_processed(symbol, cursor)
                # Do not finish a batch whose entry minute is still open.
                stop = min(end, as_of - MINUTE) // QUARTER * QUARTER
                if cursor >= stop:
                    if cursor >= end:
                        deleted = repository.delete_completed_source(symbol, end)
                        self.__log.d(f"RSI completed {symbol} nextTime={format_kst(cursor / 1000)} deleted={deleted}")
                    else:
                        self.__log.d(f"RSI waiting {symbol} nextTime={format_kst(cursor / 1000)} reason=unprocessed_tail")
                    continue
                existing = repository.existing_buy_times(symbol)
                buy_times = sorted(existing)
                def fetch_minute_opens(left, right):
                    nonlocal client
                    if client is None:
                        client = BinanceFuturesClient()
                    prices = minute_open_prices(client.get_candlestick_data, symbol, left, right)
                    time.sleep(0.25)
                    return prices

                symbol_saved = 0
                history_cache = RSIHistoryCache()
                read_from = min(start, cursor) if progress is None else cursor // DAY * DAY - 20 * DAY
                while cursor < stop:
                    chunk_end = min((cursor // DAY + 1) * DAY, stop)
                    bars = five_minute_bars(
                        repository.read_five_minutes(symbol, read_from, chunk_end), as_of)
                    prepared = history_cache.prepare(bars, cursor, chunk_end)
                    read_from = chunk_end
                    for signal in evaluate_intraminute(
                            bars, cursor, chunk_end, minute_opens=fetch_minute_opens, rsi_state=rsi_state, wait_minutes=wait_minutes,
                            on_event=lambda message: self.__log.d(f"RSI {symbol} {message}"),
                            prepared=prepared):
                        if signal["buyTime"] in existing:
                            duplicates += 1
                            continue
                        previous_buy = cooldown_previous_buy(buy_times, signal["buyTime"], cooldown_seconds)
                        if previous_buy is not None:
                            candidate_at = format_kst(signal["buyTime"])
                            allowed_at = format_kst(previous_buy + cooldown_seconds)
                            self.__log.d(f"RSI {symbol} BUY_COOLDOWN_SKIPPED buyTime={candidate_at} "
                                         f"nextAllowedAt={allowed_at} cooldownHours={cooldown_hours}")
                            continue
                        price = signal["BuyPrice"]
                        if repository.save_signal(symbol, signal, index):
                            repository.commit()
                            saved += 1
                            symbol_saved += 1
                            existing.add(signal["buyTime"])
                            insort(buy_times, signal["buyTime"])
                            bought_at = format_kst(signal["buyTime"])
                            self.__log.d(
                                f"RSI {symbol} BUY_SAVED buyTime={bought_at} BuyPrice={price} "
                                f"signalClose={signal['close']} rsi={signal['rsi']} "
                                f"previousRSI={signal['previousRSI']} entry=1m_open "
                                f"recentLow={signal['recentLow']} recentLowTime={format_kst(signal['recentLowTime'])}")
                        else:
                            duplicates += 1
                    deleted = repository.finish_chunk(symbol, chunk_end, rsi_state)
                    cursor = chunk_end
                    progress = (cursor, rsi_state)
                    self.__log.d("RSI checkpoint ", symbol, " nextTime=", format_kst(cursor / 1000), " deleted=", deleted)
                if cursor >= end:
                    deleted = repository.delete_completed_source(symbol, end)
                    self.__log.d(f"RSI completed {symbol} index={index} saved={symbol_saved} deleted={deleted}")
                else:
                    self.__log.d(f"RSI incomplete {symbol} index={index} saved={symbol_saved} "
                                 f"nextTime={format_kst(cursor / 1000)}")
            self.__log.d("RSI complete; saved=", saved, " duplicates=", duplicates)
            return saved
        finally:
            repository.release_simulation_lock()


    # Source selection for RSI simulation
    def __rsiSourceWindows(self, repository, target_symbol=None, index_from=None, index_to=None):
        index_from = self.__specificIndexFrom if index_from is None else index_from
        index_to = self.__specificIndexTo if index_to is None else index_to
        # Indices refer to DB symbols sorted alphabetically, starting at 1.
        for index, window in enumerate(repository.source_windows(self.__candleInterval), 1):
            # Explicit symbol selection takes precedence over index limits.
            if target_symbol is not None:
                if window[0] == target_symbol:
                    yield index, window
                continue
            if index_from > 0 and index < index_from:
                continue
            if index_to > 0 and index > index_to:
                continue
            yield index, window

