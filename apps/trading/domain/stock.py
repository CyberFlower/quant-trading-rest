from core.infra import LogWriter, LogLevel
from core.domain import StageType, StockTick, TickToMap
from signals.conditions.factory.base import StockContext
from signals.conditions.factory import get_condition_factory
import time


class MovingAverageType(enumerate):
    SIMPLE, EXPONENTIAL, WEIGHTED = range(3)


class Stock:
    MAX_INIT_ATTEMPTS = 10

    def __init__(
        self,
        symbol,
        name,
        buyTick,
        sellTick,
        buy,
        sell,
        avg_buy_price,
        holding_quantity,
        stock_db,
        trader,
        condition_factory=None,
    ):
        if trader is None:
            raise ValueError("trader is required")
        self.stock_db = stock_db
        self.symbol = symbol
        self.name = name
        self.trader = trader
        self.initialBuy = buy
        self.initialSell = sell
        self.avg_buy_price = float(avg_buy_price)
        self.holding_quantity = max(int(holding_quantity), 0)
        self.min_sell_price = 0.0
        self.condition_factory = condition_factory or get_condition_factory("private_condition")
        self.strategy_runtime = None
        self.is_initialized = False
        self.init_attempts = 0
        self.init_disabled = False

        # Initialize symbol-specific price data
        if self.symbol not in self.stock_db.price_db:
            self.stock_db.price_db[self.symbol] = {}
            self.stock_db.order_table[self.symbol] = {}
            for stage in range(StageType.SELL_1, StageType.BUY_3 + 1):
                self.stock_db.order_table[self.symbol][stage] = 0

        self.isUpdateStart = [False for _ in range(StockTick.MONTH + 1)]
        self.buy_tick = buyTick
        self.sell_tick = sellTick

    def _init_stock_info(self, buy_tick, sell_tick):
        if (
            self.stock_db.investCommunicator.check_and_update_stock_info(
                self.symbol, self.name
            )
            == False
        ):
            return False

        for tick in range(StockTick.HOUR + 1):
            if not self.stock_db.investCommunicator.get_last_prices(
                self.symbol, tick, "주식분봉차트조회"
            ):
                return False

        if not self.stock_db.investCommunicator.get_last_prices(
            self.symbol, StockTick.DAY, "주식일봉차트조회"
        ):
            return False
        if not self.stock_db.investCommunicator.get_last_prices(
            self.symbol, StockTick.WEEK, "주식주봉차트조회"
        ):
            return False

        LogWriter().write_log(
            "init() Symbol: {}, Name: {}".format(self.symbol, self.name), LogLevel.DEBUG
        )
        self._init_min_sell_price()

        ctx = StockContext(
            symbol=self.symbol,
            name=self.name,
            buy_tick=buy_tick,
            sell_tick=sell_tick,
            min_sell_price=self.min_sell_price,
            stock_db=self.stock_db,
            trader=self.trader,
        )
        self.strategy_runtime = self.condition_factory.create(ctx)
        self.sync_order_quantities(buy_tick, sell_tick, self.initialBuy, self.initialSell)
        return True

    def ensure_initialized(self):
        if self.is_initialized:
            return True
        if self.init_disabled:
            return False

        self.init_attempts += 1
        if self._init_stock_info(self.buy_tick, self.sell_tick):
            self.is_initialized = True
            return True

        if self.init_attempts >= self.MAX_INIT_ATTEMPTS:
            self.init_disabled = True
            LogWriter().write_log(
                "Stock init failed after {} attempts. symbol={} name={} skipped".format(
                    self.init_attempts, self.symbol, self.name
                ),
                LogLevel.ERROR,
            )
        else:
            LogWriter().write_log(
                "Stock init retry pending. symbol={} name={} attempt={}/{}".format(
                    self.symbol, self.name, self.init_attempts, self.MAX_INIT_ATTEMPTS
                ),
                LogLevel.DEBUG,
            )
        return False

    def _init_min_sell_price(self):
        if self.avg_buy_price <= 0:
            self.min_sell_price = 0.0
            return
        self.min_sell_price = self.trader.min_sell_price_for_profit(
            self.symbol,
            self.avg_buy_price,
            max(self.holding_quantity, 1),
        )

    def get_stage_snapshot(self, side):
        return self.strategy_runtime.stage_snapshot(side)

    def update_by_minute(self, minute):
        currentPrice = self.stock_db.investCommunicator.update_by_minute(self.symbol)

        for tick in range(StockTick.WEEK + 1):
            if tick >= StockTick.DAY:
                if self.isUpdateStart[tick] == False:
                    self.isUpdateStart[tick] = True
                    self.stock_db.price_db[self.symbol][tick].append(currentPrice)
                else:
                    self.stock_db.price_db[self.symbol][tick].pop(-1)
                    self.stock_db.price_db[self.symbol][tick].append(currentPrice)

            else:
                if minute % TickToMap[tick] == 1:
                    self.stock_db.price_db[self.symbol][tick].append(currentPrice)
                else:
                    self.stock_db.price_db[self.symbol][tick].pop(-1)
                    self.stock_db.price_db[self.symbol][tick].append(currentPrice)

        print(
            "update_by_minute() {} {}: {}".format(
                self.symbol, self.stock_db.name_table[self.symbol], currentPrice
            )
        )

    def check_condition_and_buy(self):
        self.strategy_runtime.run_buy()

    def check_condition_and_sell(self):
        self.strategy_runtime.run_sell()

    def sync_order_quantities(self, buy_tick, sell_tick, buy, sell):
        self.strategy_runtime.sync_order_quantities(buy_tick, sell_tick, buy, sell)
