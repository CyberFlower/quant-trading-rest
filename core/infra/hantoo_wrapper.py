from core.ports.invest_wrapper import InvestmentWrapper
from core.infra import LogWriter, LogLevel
from core.domain import StockTick, StageType, TickToMap
from core.infra.market_time import NasdaqMarketTime
from core.infra.hantoo_rest import KoreaInvestment
from core.infra.hantoo_record_rest import HantooRecordRestAPI, RECORDING_ENABLED
from core.infra.util import find_project_root
import time
import datetime
import pytz
import pprint
from pathlib import Path

SLEEP_TIME_SEC = 0.5


class HantooWrapper(InvestmentWrapper):
    def __init__(self, stock_db):
        self.stock_db = stock_db

    def connect(self, mode):
        project_root = find_project_root(Path(__file__).resolve())
        key_file = project_root / "investment_key"
        if mode == "quant":
            key_file = key_file / "koreainvestment.key"
        elif mode == "test":
            key_file = key_file / "koreatestinvestment.key"
        else:
            exit("Please select the mode. quant, test available.")

        with open(key_file, encoding="utf-8") as f:
            lines = f.readlines()

        key = lines[0].strip()
        secret = lines[1].strip()
        acc_no = lines[2].strip()
        self.rp_etf_symbol = lines[3].strip()
        self.mock = mode == "test"
        self.order = []
        if RECORDING_ENABLED:
            record_path = str(
                project_root / "apps" / "trading" / "tests" / "fixtures" / "hantoo.jsonl"
            )
            self.broker = HantooRecordRestAPI(
                api_key=key,
                api_secret=secret,
                acc_no=acc_no,
                mock=self.mock,
                record_path=record_path,
            )
        else:
            self.broker = KoreaInvestment(
                api_key=key, api_secret=secret, acc_no=acc_no, mock=self.mock
            )

    def get_last_prices(self, symbol, tick, input_desc):
        if tick <= StockTick.HOUR:
            ohlcv = self.broker.fetch_usa_1m_ohlcv(
                symbol=symbol,
                excd=self.stock_db.name_table[symbol],
                nmin=TickToMap[tick],
            )
            self.stock_db.price_db[symbol][tick] = [
                float(item["last"]) for item in ohlcv["output2"]
            ]
            self.stock_db.price_db[symbol][tick].reverse()

        elif tick > StockTick.HOUR:
            ohlcv = self.broker.fetch_ohlcv_usa_overesea(
                symbol=symbol,
                excd=self.stock_db.name_table[symbol],
                timeframe=TickToMap[tick],
                adj_price=True,
            )
            latest_dt = ohlcv["output2"][0]["xymd"] if ohlcv.get("output2") else None
            self.stock_db.price_db[symbol][tick] = [
                float(item["clos"]) for item in ohlcv["output2"]
            ]
            self.stock_db.price_db[symbol][tick].reverse()

            if tick == StockTick.WEEK:
                self.stock_db.week_trade_quantity[symbol] = [
                    float(item["tvol"]) for item in ohlcv["output2"]
                ]
                self.stock_db.week_trade_quantity[symbol].reverse()
            if tick in (StockTick.DAY, StockTick.WEEK):
                self._normalize_after_close_prices(symbol, tick, latest_dt)

        time.sleep(SLEEP_TIME_SEC)  # Avoid rate limit issues

        if len(self.stock_db.price_db[symbol][tick]) == 0:
            LogWriter().write_log(
                "Hantoo API ERROR OCCURS! No data for {} {}".format(
                    symbol, self.stock_db.name_table[symbol]
                ),
                LogLevel.ERROR,
            )
            return False

        LogWriter().write_log(
            "{} {} 5 latest prices: {}".format(
                symbol, input_desc, self.stock_db.price_db[symbol][tick][-5:]
            ),
            LogLevel.DEBUG,
        )
        return True

    def _normalize_after_close_prices(self, symbol, tick, latest_dt):
        # Normalize prices during market
        if NasdaqMarketTime().is_market_available():
            if tick == StockTick.DAY:
                if latest_dt == self._get_usa_today():
                    self.stock_db.price_db[symbol][tick].pop(-1)
                return
            elif tick == StockTick.WEEK:
                if not NasdaqMarketTime().is_week_close():
                    self.stock_db.price_db[symbol][tick].pop(-1)
                    self.stock_db.week_trade_quantity[symbol].pop(-1)
                    return
            else:
                return

    def _get_usa_today(self):
        nyt = pytz.timezone("America/New_York")
        return datetime.datetime.now(nyt).strftime("%Y%m%d")

    def update_by_minute(self, symbol):
        sleepCount = 0
        while True:
            ohlcv = self.broker.fetch_domestic_usa_price(
                symbol, self.stock_db.name_table[symbol]
            )

            time.sleep(SLEEP_TIME_SEC)  # Avoid rate limit issues

            tryApiReadable = True
            recvdCode = None
            recvdSym = None
            currentPrice = None
            try:
                recvdCode = ohlcv["rt_cd"]
                recvdSym = ohlcv["output"]["rsym"]
                currentPrice = abs(float(ohlcv["output"]["last"]))
            except KeyError:
                LogWriter().write_log(
                    "Hantoo API ERROR OCCURS! {} {}".format(
                        symbol, self.stock_db.name_table[symbol]
                    ),
                    LogLevel.ERROR,
                )
                tryApiReadable = False

            # defense code for weird price
            previousPrice = self.stock_db.price_db[symbol][StockTick.MIN1][-1]
            if (
                tryApiReadable == False
                or recvdCode != "0"
                or recvdSym != "D" + self.stock_db.name_table[symbol] + symbol
                or currentPrice > previousPrice * 1.15
                or currentPrice < previousPrice * 0.85
            ):
                LogWriter().write_log(
                    "Hantoo API ERROR OCCURS! RETRY update price.. {} {}".format(
                        symbol, self.stock_db.name_table[symbol]
                    ),
                    LogLevel.ERROR,
                )

            else:
                ny_now = datetime.datetime.now(pytz.timezone("America/New_York"))
                date_str = ny_now.strftime("%Y%m%d")
                time_str = ny_now.strftime("%H%M")
                try:
                    volume = abs(float(ohlcv["output"]["tvol"]))
                except Exception:
                    volume = None
                self.stock_db.record_minute_price(
                    "hantoo", symbol, date_str, time_str, currentPrice, volume
                )
                return currentPrice

            sleepCount += 1
            if sleepCount > 5:
                LogWriter().write_log(
                    "Error exceeds 5 times. Use previous MIN price", LogLevel.ERROR
                )
                return self.stock_db.price_db[symbol][StockTick.MIN1][-1]

    def check_and_update_stock_info(self, symbol, info):
        self.stock_db.name_table[symbol] = info
        return True

    def get_available_cash(self):
        if self.mock:
            return 0.0
        resp = self.broker.get_oversea_available_cash()
        time.sleep(SLEEP_TIME_SEC)
        if resp["rt_cd"] != "0":
            LogWriter().write_log(
                "Hantoo get_available_cash failed. {}".format(resp["rt_cd"]),
                LogLevel.ERROR,
            )
            return None

        available_cash = float(resp["output"][0]["frcr_gnrl_ord_psbl_amt"])
        LogWriter().write_log(
            "Hantoo get_available_cash success: {}".format(available_cash),
            LogLevel.INFO,
        )
        return max(available_cash - 50.0, 0)


    def place_market_buy(self, symbol, quantity):
        if not self.mock:
            hoga = self.broker.get_hoga(
                symbol=symbol,
                excd=self.stock_db.name_table[symbol],
            )["output2"]["pask1"]
        else:
            hoga = self.stock_db.price_db[symbol][StockTick.MIN1][-1]

        resp = self.broker.create_oversea_order(
            side="buy",
            exchange=self.stock_db.name_table[symbol],
            symbol=symbol,
            price=hoga,
            quantity=quantity,
            order_type="00",
        )
        time.sleep(SLEEP_TIME_SEC)  # Avoid rate limit issues
        if resp["rt_cd"] != "0":
            LogWriter().write_log(
                "{} : Hantoo buy_stock_by_market_price failed. {}".format(
                    symbol, resp["msg1"]
                ),
                LogLevel.ERROR,
            )
            return 0

        try:
            self.order.append(resp["output"]["ODNO"])
        except KeyError:
            LogWriter().write_log(
                "{} : Hantoo buy_stock_by_market_price failed to get order number.".format(
                    symbol
                ),
                LogLevel.ERROR,
            )

        LogWriter().write_log(
            "{} {} : Buying {} stocks, trying price is {}".format(
                symbol,
                self.stock_db.name_table[symbol],
                quantity,
                self.stock_db.price_db[symbol][StockTick.MIN1][-1],
            ),
            LogLevel.INFO,
        )
        return quantity


    def get_rp_etf_quantity(self):
        try:
            balances = self.get_stock_balance()
        except Exception:
            return 0
        for item in balances:
            if item.get("symbol") == self.rp_etf_symbol:
                try:
                    qty = int(item.get("rmnd_qty", 0))
                    return qty if qty > 0 else 0
                except (TypeError, ValueError):
                    return 0
        return 0

    def buy_stock_by_market_price(self, symbol, quantity):
        return self.place_market_buy(symbol, quantity)

    def sell_stock_by_market_price(self, symbol, quantity):
        if not self.mock:
            hoga = self.broker.get_hoga(
                symbol=symbol,
                excd=self.stock_db.name_table[symbol],
            )["output2"]["pbid1"]
        else:
            hoga = self.stock_db.price_db[symbol][StockTick.MIN1][-1]

        resp = self.broker.create_oversea_order(
            side="sell",
            exchange=self.stock_db.name_table[symbol],
            symbol=symbol,
            price=hoga,
            quantity=quantity,
            order_type="00",
        )
        time.sleep(SLEEP_TIME_SEC)  # Avoid rate limit issues
        if resp["rt_cd"] != "0":
            LogWriter().write_log(
                "{} : Hantoo sell_stock_by_market_price failed. {}".format(
                    symbol, resp["msg1"]
                ),
                LogLevel.ERROR,
            )
            return 0

        try:
            self.order.append(resp["output"]["ODNO"])
        except KeyError:
            LogWriter().write_log(
                "{} : Hantoo sell_stock_by_market_price failed to get order number.".format(
                    symbol
                ),
                LogLevel.ERROR,
            )

        LogWriter().write_log(
            "{} {} : Selling {} stocks, trying price is {}".format(
                symbol,
                self.stock_db.name_table[symbol],
                quantity,
                self.stock_db.price_db[symbol][StockTick.MIN1][-1],
            ),
            LogLevel.INFO,
        )
        return quantity

    def check_order_completed(self):
        resp = self.broker.check_confirmed_order()
        if not resp or resp["rt_cd"] != "0":
            return

        for item in resp["output"]:
            order_num = item["odno"]
            symbol = item["pdno"]
            buy_or_sell = item["sll_buy_dvsn_cd"]
            completed_quantity = int(item["ft_ccld_qty"])

            print(
                f"Order {order_num} for {symbol} ({buy_or_sell}): {completed_quantity} completed"
            )

            if order_num not in self.order or symbol == self.rp_etf_symbol:
                continue

            if buy_or_sell == "01":  # 매도
                for stage in range(StageType.SELL_1, StageType.SELL_3 + 1):
                    if completed_quantity >= self.stock_db.order_table[symbol][stage]:
                        completed_quantity -= self.stock_db.order_table[symbol][stage]
                        self.stock_db.order_table[symbol][stage] = 0
                    else:
                        self.stock_db.order_table[symbol][stage] -= completed_quantity
                        completed_quantity = 0
                        break
            elif buy_or_sell == "02":  # 매수
                for stage in range(StageType.BUY_1, StageType.BUY_3 + 1):
                    if completed_quantity >= self.stock_db.order_table[symbol][stage]:
                        completed_quantity -= self.stock_db.order_table[symbol][stage]
                        self.stock_db.order_table[symbol][stage] = 0
                    else:
                        self.stock_db.order_table[symbol][stage] -= completed_quantity
                        completed_quantity = 0
                        break

        for symbol in self.stock_db.order_table.keys():
            for stage in range(StageType.SELL_1, StageType.BUY_3 + 1):
                if self.stock_db.order_table[symbol][stage] > 0:
                    LogWriter().write_log(
                        "Order not completed for {} {} stage {}: {}".format(
                            symbol,
                            self.stock_db.name_table[symbol],
                            stage,
                            self.stock_db.order_table[symbol][stage],
                        ),
                        LogLevel.ERROR,
                    )

    def get_stock_balance(self):
        response = self.broker.get_account_balance()
        result = [
            {
                "symbol": item["ovrs_pdno"],
                "name": item["ovrs_item_name"],
                "buy_price": item["pchs_avg_pric"],
                "rmnd_qty": int(float(item["ovrs_cblc_qty"])),
                "cur_price": item["now_pric2"],
            }
            for item in response["output1"]
        ]
        return result


def main():
    from core.infra.stock_db import StockDataBase

    wrapper = HantooWrapper(stock_db=StockDataBase())
    wrapper.connect("quant")
    balances = wrapper.get_stock_balance()
    pprint.pprint(balances)


if __name__ == "__main__":
    main()
