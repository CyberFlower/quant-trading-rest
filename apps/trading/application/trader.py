from core.infra import LogWriter, LogLevel
from core.domain import StockTick


class BaseTrader:
    def __init__(self, wrapper, stock_db):
        self.wrapper = wrapper
        self.stock_db = stock_db

    def buy_stock_by_market_price(self, symbol, quantity):
        raise NotImplementedError

    def sell_stock_by_market_price(self, symbol, quantity):
        LogWriter().write_log(
            "{} sell_stock_by_market_price: symbol={}, quantity={}, last_price={}".format(
                self.__class__.__name__,
                symbol,
                quantity,
                self.stock_db.price_db[symbol][StockTick.MIN1][-1],
            ),
            LogLevel.DEBUG,
        )
        return self.wrapper.sell_stock_by_market_price(symbol, quantity)

    def _ensure_rp_etf_symbol(self):
        if self.wrapper.rp_etf_symbol not in self.stock_db.price_db:
            LogWriter().write_log(
                "Please Add RP ETF symbol in IO file.. Symbol: {}".format(
                    self.wrapper.rp_etf_symbol
                ),
                LogLevel.ERROR,
            )
            exit(0)

    def _init_last_exchange_cash(self):
        if not hasattr(self.wrapper, "_last_exchange_cash"):
            self.wrapper._last_exchange_cash = None

    def _should_skip_exchange(self, available_cash, label):
        self._init_last_exchange_cash()
        if self.wrapper._last_exchange_cash == available_cash:
            LogWriter().write_log(
                "{} skipped: waiting for previous exchange to complete (available_cash={})".format(
                    label, available_cash
                ),
                LogLevel.DEBUG,
            )
            return True
        return False


class HantooTrader(BaseTrader):
    def _calc_try_price(self, symbol):
        price = float(self.stock_db.price_db[symbol][StockTick.MIN1][-1])
        return float(int(price * 100 + 99) / 100)

    def _calc_buy_plan(self, symbol, quantity, available_cash):
        try_price = self._calc_try_price(symbol)
        if try_price * quantity <= available_cash:
            return (quantity, 0, False)

        rp_qty = self.wrapper.get_rp_etf_quantity()
        if rp_qty > 0:
            return (0, try_price * quantity - available_cash, True)
        cash_qty = int(available_cash / try_price)
        return (cash_qty, 0, False)

    def _exchange_rp_etf(self, needed_amount, available_cash):
        if self._should_skip_exchange(available_cash, "exchangeRPETFtoCash"):
            return False

        rp_qty = self.wrapper.get_rp_etf_quantity()
        if rp_qty <= 0:
            return False

        rp_etf_price = self.stock_db.price_db[self.wrapper.rp_etf_symbol][
            StockTick.MIN1
        ][-1]
        required_quantity = int(needed_amount / rp_etf_price + 0.999)
        sell_qty = min(rp_qty, required_quantity)
        if sell_qty <= 0:
            return False

        LogWriter().write_log(
            "Exchanging RP ETF to US, required quantity: {}, price: {}".format(
                sell_qty, rp_etf_price
            ),
            LogLevel.DEBUG,
        )

        self.wrapper.sell_stock_by_market_price(self.wrapper.rp_etf_symbol, sell_qty)
        self.wrapper._last_exchange_cash = available_cash
        return True

    def buy_stock_by_market_price(self, symbol, quantity):
        LogWriter().write_log(
            "{} buy_stock_by_market_price: symbol={}, quantity={}, last_price={}".format(
                self.__class__.__name__,
                symbol,
                quantity,
                self.stock_db.price_db[symbol][StockTick.MIN1][-1],
            ),
            LogLevel.DEBUG,
        )
        available_cash = self.wrapper.get_available_cash()

        if available_cash is None:
            LogWriter().write_log(
                "Hantoo buy_stock_by_market_price failed: Unable to retrieve available cash",
                LogLevel.ERROR,
            )
            return 0

        self._ensure_rp_etf_symbol()

        exec_qty, needed_amount, needs_exchange = self._calc_buy_plan(
            symbol, quantity, available_cash
        )
        if exec_qty > 0:
            self.wrapper._last_exchange_cash = None
            return self.wrapper.place_market_buy(symbol, exec_qty)
        if needs_exchange and needed_amount > 0:
            self._exchange_rp_etf(needed_amount, available_cash)

        return 0


class KiwoomTrader(BaseTrader):
    def _calc_try_price(self, symbol):
        return self.stock_db.price_db[symbol][StockTick.MIN1][-1]

    def _calc_buy_plan(self, symbol, quantity, available_cash):
        try_price = self._calc_try_price(symbol)
        if try_price * quantity <= available_cash:
            return (quantity, 0, False)

        rp_qty = self.wrapper.get_rp_etf_quantity()
        if rp_qty > 0:
            return (0, try_price * quantity - available_cash, True)
        cash_qty = int(available_cash / try_price)
        return (cash_qty, 0, False)

    def _exchange_rp_etf(self, needed_amount, available_cash):
        if self._should_skip_exchange(available_cash, "exchangeRPETFtoKRW"):
            return False

        rp_qty = self.wrapper.get_rp_etf_quantity()
        if rp_qty <= 0:
            return False

        rp_etf_price = self.stock_db.price_db[self.wrapper.rp_etf_symbol][
            StockTick.MIN1
        ][-1]
        required_quantity = (needed_amount + rp_etf_price - 1) // rp_etf_price
        sell_qty = min(rp_qty, required_quantity)
        if sell_qty <= 0:
            return False

        LogWriter().write_log(
            "Exchanging RP ETF to KRW, required quantity: {}, price: {}".format(
                sell_qty, rp_etf_price
            ),
            LogLevel.DEBUG,
        )

        self.wrapper.sell_stock_by_market_price(self.wrapper.rp_etf_symbol, sell_qty)
        self.wrapper._last_exchange_cash = available_cash
        return True

    def buy_stock_by_market_price(self, symbol, quantity):
        last_price = None
        if symbol in self.stock_db.price_db:
            ticks = self.stock_db.price_db[symbol].get(StockTick.MIN1)
            if ticks:
                last_price = ticks[-1]
        LogWriter().write_log(
            "{} buy_stock_by_market_price: symbol={}, quantity={}, last_price={}".format(
                self.__class__.__name__, symbol, quantity, last_price
            ),
            LogLevel.DEBUG,
        )
        available_cash = self.wrapper.get_available_cash()

        if available_cash is None:
            LogWriter().write_log(
                "Failed to get available cash, cannot proceed with buy operation.",
                LogLevel.ERROR,
            )
            return 0

        self._ensure_rp_etf_symbol()

        exec_qty, needed_amount, needs_exchange = self._calc_buy_plan(
            symbol, quantity, available_cash
        )
        if exec_qty > 0:
            self.wrapper._last_exchange_cash = None
            return self.wrapper.place_market_buy(symbol, exec_qty)
        if needs_exchange and needed_amount > 0:
            self._exchange_rp_etf(needed_amount, available_cash)

        return 0
