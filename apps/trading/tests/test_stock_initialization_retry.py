import unittest
from types import SimpleNamespace

from apps.trading.domain.stock import Stock
from core.domain import StockTick
from core.infra import LogWriter


class FakeRuntime:
    def __init__(self):
        self.synced = False

    def sync_order_quantities(self, buy_tick, sell_tick, buy, sell):
        self.synced = True

    def run_buy(self):
        return None

    def run_sell(self):
        return None


class FakeConditionFactory:
    def create(self, ctx):
        return FakeRuntime()


class FakeTrader:
    def min_sell_price_for_profit(self, symbol, avg_buy_price, quantity):
        return float(avg_buy_price)


class FakeInvestCommunicator:
    def __init__(self, failures_before_success=0):
        self.failures_before_success = failures_before_success
        self.init_attempts = 0
        self.price_calls = 0

    def check_and_update_stock_info(self, symbol, name):
        return True

    def get_last_prices(self, symbol, tick, input_desc):
        self.price_calls += 1
        if tick == StockTick.MIN1:
            self.init_attempts += 1
            if self.init_attempts <= self.failures_before_success:
                return False
        return True


class StockInitializationRetryTest(unittest.TestCase):
    def setUp(self):
        LogWriter(mode="test", company="kiwoom", category="test")

    def _make_stock(self, communicator):
        stock_db = SimpleNamespace(
            investCommunicator=communicator,
            price_db={},
            order_table={},
            name_table={"TEST": "테스트"},
        )
        return Stock(
            "TEST",
            "테스트",
            StockTick.DAY,
            StockTick.DAY,
            [0, 0, 0],
            [0, 0, 0],
            0,
            0,
            stock_db=stock_db,
            trader=FakeTrader(),
            condition_factory=FakeConditionFactory(),
        )

    def test_init_failure_disables_stock_after_ten_attempts(self):
        stock = self._make_stock(FakeInvestCommunicator(failures_before_success=10))

        for _ in range(9):
            self.assertFalse(stock.ensure_initialized())
            self.assertFalse(stock.init_disabled)

        self.assertFalse(stock.ensure_initialized())
        self.assertFalse(stock.is_initialized)
        self.assertTrue(stock.init_disabled)
        self.assertEqual(stock.init_attempts, 10)

    def test_init_can_succeed_after_retry(self):
        stock = self._make_stock(FakeInvestCommunicator(failures_before_success=2))

        self.assertFalse(stock.ensure_initialized())
        self.assertFalse(stock.ensure_initialized())
        self.assertTrue(stock.ensure_initialized())

        self.assertTrue(stock.is_initialized)
        self.assertFalse(stock.init_disabled)
        self.assertEqual(stock.init_attempts, 3)
        self.assertIsNotNone(stock.strategy_runtime)


if __name__ == "__main__":
    unittest.main()
