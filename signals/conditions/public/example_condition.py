"""Simple public example condition set (gate 1 + entry 1)."""

from core.domain import StageType, StockTick


class ExampleQuantityGate:
    """Order-sync gate that only forwards quantity to entry."""

    def __init__(self):
        self.quantity = 0
        self.last_stage = StageType.NONE

    def update_quantity(self, quantity, tick=None):
        if quantity is None:
            return
        if isinstance(quantity, list):
            self.quantity = sum(quantity)
        else:
            self.quantity = int(quantity)

    def execute(self, quantity=None, required_stage=None):
        if quantity == 0:
            return (0, StageType.NONE)
        if quantity is None:
            return (self.quantity, StageType.NONE)
        return (min(self.quantity, int(quantity)), StageType.NONE)

    def settle(self, executed_qty, stage, **kwargs):
        return None


class _BasePriceCrossEntry:
    def __init__(self, symbol: str, name: str, stock_db=None, window: int = 5):
        if stock_db is None:
            raise ValueError("stock_db is required")
        self.symbol = symbol
        self.name = name
        self.stock_db = stock_db
        self.window = int(window)
        self.quantity = 0
        self.last_stage = StageType.NONE

    def update_quantity(self, quantity, tick=None):
        if quantity is None:
            return
        if isinstance(quantity, list):
            self.quantity = sum(quantity)
        else:
            self.quantity = int(quantity)

    def _prices(self):
        return self.stock_db.price_db.get(self.symbol, {}).get(StockTick.MIN1, []) or []

    def _cross_ready(self):
        prices = self._prices()
        return len(prices) >= self.window + 1

    def _sma_prev_curr(self):
        prices = self._prices()
        prev_window = prices[-(self.window + 1) : -1]
        curr_window = prices[-self.window :]
        return (sum(prev_window) / self.window, sum(curr_window) / self.window)

    def settle(self, executed_qty, stage, **kwargs):
        return None


class ExamplePriceCrossBuyEntry(_BasePriceCrossEntry):
    """Buy when MIN1 price crosses above SMA(window)."""

    def execute(self, quantity=None, required_stage=None):
        if not self._cross_ready():
            return (0, StageType.NONE)
        if self.quantity <= 0:
            return (0, StageType.NONE)

        prices = self._prices()
        prev_price = prices[-2]
        curr_price = prices[-1]
        sma_prev, sma_curr = self._sma_prev_curr()

        if not (prev_price <= sma_prev and curr_price > sma_curr):
            return (0, StageType.NONE)

        qty = self.quantity if quantity is None else min(self.quantity, int(quantity))
        if qty <= 0:
            return (0, StageType.NONE)

        trader = getattr(self, "trader", None)
        if trader is not None:
            executed = trader.buy_stock_by_market_price(self.symbol, qty)
        else:
            executed = self.stock_db.investCommunicator.buy_stock_by_market_price(self.symbol, qty)
        if not executed:
            return (0, StageType.NONE)
        self.quantity -= executed
        self.last_stage = StageType.BUY_1
        return (executed, StageType.BUY_1)


class ExamplePriceCrossSellEntry(_BasePriceCrossEntry):
    """Sell when MIN1 price crosses below SMA(window)."""

    def __init__(self, symbol: str, name: str, min_sell_price: float, stock_db=None, window: int = 5):
        super().__init__(symbol=symbol, name=name, stock_db=stock_db, window=window)
        self.min_sell_price = float(min_sell_price)

    def execute(self, quantity=None, required_stage=None):
        if not self._cross_ready():
            return (0, StageType.NONE)
        if self.quantity <= 0:
            return (0, StageType.NONE)

        prices = self._prices()
        prev_price = prices[-2]
        curr_price = prices[-1]
        if curr_price < self.min_sell_price:
            return (0, StageType.NONE)
        sma_prev, sma_curr = self._sma_prev_curr()

        if not (prev_price >= sma_prev and curr_price < sma_curr):
            return (0, StageType.NONE)

        qty = self.quantity if quantity is None else min(self.quantity, int(quantity))
        if qty <= 0:
            return (0, StageType.NONE)

        trader = getattr(self, "trader", None)
        if trader is not None:
            executed = trader.sell_stock_by_market_price(self.symbol, qty)
        else:
            executed = self.stock_db.investCommunicator.sell_stock_by_market_price(self.symbol, qty)
        if not executed:
            return (0, StageType.NONE)
        self.quantity -= executed
        self.last_stage = StageType.SELL_1
        return (executed, StageType.SELL_1)
