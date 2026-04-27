from core.infra import LogWriter, LogLevel
from apps.trading.domain.stock import Stock
from core.domain import StageType
from apps.trading.infra.order_ui import OrderIOManager
from core.infra.kiwoom_wrapper import KiwoomWrapper
from core.infra.hantoo_wrapper import HantooWrapper
from apps.trading.application.trader import KiwoomTrader, HantooTrader
from core.infra.stock_db import StockDataBase
from core.infra.market_time import KRXMarketTime, NasdaqMarketTime
from signals.conditions.factory import get_condition_factory
import time
import sys
import os


def _initialize_rp_etf(invest_communicator, runtime_stock_database):
    if not hasattr(invest_communicator, "set_rp_etf_state"):
        return

    invest_communicator.set_rp_etf_state(False)
    rp_symbol = getattr(invest_communicator, "rp_etf_symbol", None)
    if not rp_symbol:
        LogWriter().write_log("RP ETF disabled by profile", LogLevel.INFO)
        return

    rp_name = getattr(invest_communicator, "rp_etf_name", None)
    if not rp_name:
        LogWriter().write_log(
            "RP ETF metadata missing. symbol={}".format(rp_symbol),
            LogLevel.ERROR,
        )
        return

    runtime_stock_database.price_db.setdefault(rp_symbol, {})
    runtime_stock_database.order_table.setdefault(
        rp_symbol,
        {stage: 0 for stage in range(StageType.SELL_1, StageType.BUY_3 + 1)},
    )

    if invest_communicator.check_and_update_stock_info(rp_symbol, rp_name) is False:
        LogWriter().write_log(
            "RP ETF lookup failed. symbol={}, info={}".format(rp_symbol, rp_name),
            LogLevel.ERROR,
        )
        return

    invest_communicator.set_rp_etf_state(True, rp_name)
    LogWriter().write_log(
        "RP ETF enabled. symbol={}, info={}".format(rp_symbol, rp_name),
        LogLevel.INFO,
    )


def run_trading(
    invest_company,
    quant_mode,
    log_category="trading",
    investCommunicator=None,
    market_time=None,
    sleep_fn=time.sleep,
    align_to_minute=True,
    max_loops=None,
):
    runtime_stock_database = StockDataBase()

    if invest_company == "kiwoom":
        if investCommunicator is None:
            investCommunicator = KiwoomWrapper(stock_db=runtime_stock_database)
        elif hasattr(investCommunicator, "stock_db"):
            investCommunicator.stock_db = runtime_stock_database
        if market_time is None:
            market_time = KRXMarketTime()
        trader = KiwoomTrader(investCommunicator, stock_db=runtime_stock_database)
    elif invest_company == "hantoo":
        if investCommunicator is None:
            investCommunicator = HantooWrapper(stock_db=runtime_stock_database)
        elif hasattr(investCommunicator, "stock_db"):
            investCommunicator.stock_db = runtime_stock_database
        if market_time is None:
            market_time = NasdaqMarketTime()
        trader = HantooTrader(investCommunicator, stock_db=runtime_stock_database)
    else:
        exit("Please select the investment company. kiwoom, hantoo available.")

    LogWriter(mode=quant_mode, company=invest_company, category=log_category)
    orderIO = OrderIOManager(invest_company, quant_mode)

    investCommunicator.connect(quant_mode)
    runtime_stock_database.bind(orderIO, investCommunicator)
    condition_profile = os.getenv("QUANT_PROFILE", "private_condition")
    try:
        condition_factory = get_condition_factory(condition_profile)
    except ValueError as exc:
        exit(str(exc))
    LogWriter().write_log(
        "Condition profile: {}".format(condition_profile)
    )

    buy_prices = {}
    holding_quantities = {}

    account_balance = investCommunicator.get_stock_balance()
    orderIO.update_account_balance(account_balance)
    for balance in account_balance:
        buy_prices[balance["symbol"]] = balance["buy_price"]
        holding_quantities[balance["symbol"]] = balance["rmnd_qty"]

    interest_stocks = orderIO.read_stock_infos()
    _initialize_rp_etf(investCommunicator, runtime_stock_database)
    stocks = []
    for symbol in interest_stocks.keys():
        stocks.append(
            Stock(
                symbol,
                interest_stocks[symbol]["name"],
                interest_stocks[symbol]["buyTick"],
                interest_stocks[symbol]["sellTick"],
                [
                    interest_stocks[symbol]["buy_1"],
                    interest_stocks[symbol]["buy_2"],
                    interest_stocks[symbol]["buy_3"],
                ],
                [
                    interest_stocks[symbol]["sell_1"],
                    interest_stocks[symbol]["sell_2"],
                    interest_stocks[symbol]["sell_3"],
                ],
                float(buy_prices.get(symbol, 0)),
                int(holding_quantities.get(symbol, 0)),
                trader=trader,
                stock_db=runtime_stock_database,
                condition_factory=condition_factory,
            )
        )
        LogWriter().write_log("{} {} Added..".format(symbol, interest_stocks[symbol]))

    if align_to_minute:
        sleep_fn((60.0 - time.localtime().tm_sec) % 60.0)

    loop_count = 0
    while True:
        if max_loops is not None and loop_count >= max_loops:
            break
        start_time = time.time()
        LogWriter().write_log(time.strftime("%Y.%m.%d - %H:%M:%S"))
        if market_time.is_market_close():
            if invest_company == "hantoo":
                investCommunicator.check_order_completed()

            account_balance = investCommunicator.get_stock_balance()
            orderIO.update_account_balance(account_balance)
            LogWriter().write_log("Market close")
            break

        if market_time.is_pre_market_open():
            for stock in stocks:
                if not stock.ensure_initialized():
                    continue
                stock.update_by_minute(time.localtime().tm_min)

        if market_time.is_market_open():
            current_minute = market_time.get_minute()

            for stock in stocks:
                if not stock.ensure_initialized():
                    continue
                stock.update_by_minute(current_minute)
                stock.check_condition_and_buy()
                stock.check_condition_and_sell()

                update_stock_infos = {}
                if current_minute % 15 == 0:
                    update_stock_infos = orderIO.read_stock_infos()
                    # TODO needs change logic in multi-thread, currently using 1 core
                    for symbol in update_stock_infos.keys():
                        if stock.symbol == symbol:
                            stock.sync_order_quantities(
                                update_stock_infos[symbol]["buyTick"],
                                update_stock_infos[symbol]["sellTick"],
                                [
                                    update_stock_infos[symbol]["buy_1"],
                                    update_stock_infos[symbol]["buy_2"],
                                    update_stock_infos[symbol]["buy_3"],
                                ],
                                [
                                    update_stock_infos[symbol]["sell_1"],
                                    update_stock_infos[symbol]["sell_2"],
                                    update_stock_infos[symbol]["sell_3"],
                                ],
                            )
                            break

        current_time = time.time()
        sleep_fn(max(0, 60.0 - (current_time - start_time)))
        loop_count += 1

    saved_path = runtime_stock_database.save_minute_price_db(invest_company)
    if saved_path:
        LogWriter().write_log(
            "Saved minute price DB: {}".format(saved_path)
        )

if __name__ == "__main__":
    if len(sys.argv) > 2:
        invest_company = sys.argv[1]
        quant_mode = sys.argv[2]
    else:
        exit("example: python -m apps.trading.main kiwoom quant")

    run_trading(invest_company, quant_mode)
