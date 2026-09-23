class Currency:
    def __init__(self, data):
        # symbol, pricePrecision, quantityPrecision
        self.symbol = data['symbol']
        self.pricePrecision = data['pricePrecision']
        self.quantityPrecision = data['quantityPrecision']

    def __str__(self):
        return f"{self.symbol} {self.pricePrecision} {self.quantityPrecision}"
