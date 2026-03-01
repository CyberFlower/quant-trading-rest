from core.infra import LogWriter, LogLevel
from core.domain import StageType, StockTick, TickToMap
from signals.conditions.factory.base import StockContext
from signals.conditions.factory import get_condition_factory
import time


class MovingAverageType(enumerate):
    SIMPLE, EXPONENTIAL, WEIGHTED = range(3)


class Stock:
    def __init__(
        self,
        symbol,
        name,
        buyTick,
        sellTick,
        buy,
        sell,
        min_sell_price,
        stock_db,
        trader=None,
        condition_factory=None,
    ):
        self.stock_db = stock_db
        self.symbol = symbol
        self.name = name
        self.trader = trader
        self.initialBuy = buy
        self.initialSell = sell
        self.min_sell_price = min_sell_price
        self.condition_factory = condition_factory or get_condition_factory("private_condition")
        self.strategy_runtime = None

        # Initialize symbol-specific price data
        if self.symbol not in self.stock_db.price_db:
            self.stock_db.price_db[self.symbol] = {}
            self.stock_db.order_table[self.symbol] = {}
            for stage in range(StageType.SELL_1, StageType.BUY_3 + 1):
                self.stock_db.order_table[self.symbol][stage] = 0

        self.isUpdateStart = [False for _ in range(StockTick.MONTH + 1)]
        self._init_stock_info(buyTick, sellTick)

    def _init_stock_info(self, buy_tick, sell_tick):
        if (
            self.stock_db.investCommunicator.check_and_update_stock_info(
                self.symbol, self.name
            )
            == False
        ):
            exit(0)

        for tick in range(StockTick.HOUR + 1):
            if not self.stock_db.investCommunicator.get_last_prices(
                self.symbol, tick, "주식분봉차트조회"
            ):
                exit(0)

        if not self.stock_db.investCommunicator.get_last_prices(
            self.symbol, StockTick.DAY, "주식일봉차트조회"
        ):
            exit(0)
        if not self.stock_db.investCommunicator.get_last_prices(
            self.symbol, StockTick.WEEK, "주식주봉차트조회"
        ):
            exit(0)

        LogWriter().write_log(
            "init() Symbol: {}, Name: {}".format(self.symbol, self.name), LogLevel.DEBUG
        )

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
