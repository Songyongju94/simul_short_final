from model.TradeInfo import TradeInfo

class TradeInfoAdapter:
    @classmethod
    def createFromBinance(cls, data):
        # Debug rows contain bolDataList/openValue before the trailing trade fields.
        debug_row = len(data) >= 29 and isinstance(data[28], str)
        offset = 2 if debug_row else 0
        has_recent_low = len(data) == (32 if debug_row else 30)
        return TradeInfo({'uid': data[0], 'candleTime': data[2], 'position': data[3], 'high': float(data[4]),
                          'low': float(data[5]), 'close': float(data[6]), 'bolHigh': float(data[7]),
                          'bolLow': float(data[8]), 'high2BolPercent': float(data[9]),
                          'low2BolPercent': float(data[10]), 'buyPrice': float(data[11]),
                          'buy2BolPercent': float(data[12]),
                          'coinIndex': float(data[13]), 'buyTime': data[14], 'triggerTime': data[15],
                          'triggerPrice': float(data[16]), 'trigger2bolPercent': float(data[17]),
                          'addBuyCount': int(data[24 + offset]), 'addMBuyCount': int(data[25 + offset]),
                          'buyMode': data[26 + offset],
                          'recentLow': float(data[-2]) if has_recent_low else 0,
                          'recentLowTime': str(data[-1] or '') if has_recent_low else ''})
