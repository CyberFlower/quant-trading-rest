from core.ports.invest_wrapper import InvestmentWrapper
from core.infra.kiwoom_rest import KiwoomRestAPI
from core.infra.kiwoom_record_rest import KiwoomRecordRestAPI, RECORDING_ENABLED
from core.infra import LogWriter, LogLevel
from datetime import datetime
import pytz
from pathlib import Path

from core.domain import StockTick, TickToMap
from core.infra.util import find_project_root
from core.infra.market_time import KRXMarketTime


class KiwoomWrapper(InvestmentWrapper):
    def __init__(self, stock_db):
        self.stock_db = stock_db
        self.today = datetime.now().strftime("%Y%m%d")

    def connect(self, mode):
        project_root = find_project_root(Path(__file__).resolve())
        key_file = project_root / "investment_key"
        if mode == "quant":
            key_file = key_file / "kiwoominvestment.key"
        elif mode == "isa":
            key_file = key_file / "kiwoomisainvestment.key"
        elif mode == "test":
            key_file = key_file / "kiwoomtestinvestment.key"
        else:
            exit("Please select the mode. test, quant, isa available.")

        with open(key_file, encoding="utf-8") as f:
            lines = f.readlines()

        key = lines[0].strip()
        secret = lines[1].strip()
        self.stock_account = lines[2].strip()
        self.rp_etf_symbol = lines[3].strip()
        self.al_symbol = "_AL" if mode != "test" else ""
        self.mock = mode == "test"

        if RECORDING_ENABLED:
            record_path = str(
                project_root / "apps" / "trading" / "tests" / "fixtures" / "kiwoom.jsonl"
            )
            self.kiwoom = KiwoomRecordRestAPI(
                key, secret, mock=self.mock, record_path=record_path
            )
        else:
            self.kiwoom = KiwoomRestAPI(key, secret, mock=self.mock)

    def _parse_hoga_price(self, value):
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return abs(int(value))
        value = str(value).strip().replace(",", "")
        if not value:
            return None
        if value[0] in "+-":
            value = value[1:]
        try:
            return abs(int(value))
        except ValueError:
            return None

    # Maximum 900 data
    def get_last_prices(self, symbol, tick, input_desc):
        if tick <= StockTick.HOUR:
            json_data = self.kiwoom.get_last_prices(
                symbol + self.al_symbol, "MIN", str(TickToMap[tick])
            )
            self.stock_db.price_db[symbol][tick] = [
                abs(int(item["cur_prc"]))
                for item in json_data["stk_min_pole_chart_qry"]
            ]
        elif tick == StockTick.DAY:
            json_data = self.kiwoom.get_last_prices(
                symbol + self.al_symbol, "DAY", self.today
            )
            day_rows = json_data["stk_dt_pole_chart_qry"]
            self.stock_db.price_db[symbol][tick] = [
                abs(int(item["cur_prc"])) for item in json_data["stk_dt_pole_chart_qry"]
            ]
        elif tick == StockTick.WEEK:
            json_data = self.kiwoom.get_last_prices(
                symbol + self.al_symbol, "WEEK", self.today
            )
            week_rows = json_data["stk_stk_pole_chart_qry"]
            self.stock_db.price_db[symbol][tick] = [
                abs(int(item["cur_prc"]))
                for item in json_data["stk_stk_pole_chart_qry"]
            ]
            self.stock_db.week_trade_quantity[symbol] = [
                abs(int(item["trde_qty"]))
                for item in json_data["stk_stk_pole_chart_qry"]
            ]
        else:
            return False

        if len(self.stock_db.price_db[symbol][tick]) == 0:
            LogWriter().write_log(
                "Kiwoom API ERROR OCCURS! No data for {} {}".format(
                    symbol, self.stock_db.name_table[symbol]
                ),
                LogLevel.ERROR,
            )
            return False

        self.stock_db.price_db[symbol][tick].reverse()

        if tick == StockTick.DAY:
            latest_dt = day_rows[0]["dt"] if day_rows else None
            self._normalize_after_close_prices(symbol, tick, latest_dt)

        if tick == StockTick.WEEK:
            self.stock_db.week_trade_quantity[symbol].reverse()
            latest_dt = week_rows[0]["dt"] if week_rows else None
            self._normalize_after_close_prices(symbol, tick, latest_dt)

        LogWriter().write_log(
            "getKiwoomLastPrices {} {} {}".format(
                self.stock_db.name_table[symbol],
                tick,
                len(self.stock_db.price_db[symbol][tick]),
            ),
            LogLevel.DEBUG,
        )
        LogWriter().write_log(
            "{} 5 latest prices: {}".format(
                input_desc, self.stock_db.price_db[symbol][tick][-5:]
            ),
            LogLevel.DEBUG,
        )
        return True

    def _normalize_after_close_prices(self, symbol, tick, latest_dt):
        # Normalize prices during market
        if KRXMarketTime().is_market_available():
            if tick == StockTick.DAY:
                if latest_dt == self.today:
                    self.stock_db.price_db[symbol][tick].pop(-1)
                return
            elif tick == StockTick.WEEK:
                if not KRXMarketTime().is_week_close():
                    self.stock_db.price_db[symbol][tick].pop(-1)
                    self.stock_db.week_trade_quantity[symbol].pop(-1)
                    return
            else:
                return

    def update_by_minute(self, symbol):
        currentPrice = self.stock_db.price_db[symbol][StockTick.MIN1][-1]
        requestSymbol = ""
        sleepCount = 0
        record_date = None
        record_time = None
        record_volume = None
        while True:
            response = self.kiwoom.get_stock_price_info(symbol)

            tryAPIReadable = True
            try:
                currentPrice = abs(int(response["cur_prc"]))
                requestSymbol = response["stk_cd"]
                returnCode = response["return_code"]
            except Exception as e:
                LogWriter().write_log(
                    "{} Exception occurred: {}".format(
                        self.stock_db.name_table[symbol], str(e)
                    ),
                    LogLevel.ERROR,
                )
                tryAPIReadable = False

            # Defense code for weird price
            previousPrice = self.stock_db.price_db[symbol][StockTick.MIN1][-1]

            if tryAPIReadable == False or returnCode != 0 or requestSymbol != symbol:
                LogWriter().write_log(
                    "Kiwoom API ERROR OCCURS! RETRY update price.. {} {} {}".format(
                        symbol, requestSymbol, self.stock_db.name_table[symbol]
                    ),
                    LogLevel.ERROR,
                )
            elif (
                previousPrice * 1.15 < currentPrice
                or previousPrice * 0.85 > currentPrice
            ):
                tryAPIReadable = False
                LogWriter().write_log(
                    "Price definitely seems weird.. currentPrice: {} yesterdayPrice: {}".format(
                        currentPrice, previousPrice
                    ),
                    LogLevel.ERROR,
                )
            else:
                record_date = response.get("date")
                tm = response.get("tm")
                if tm:
                    tm = str(tm).zfill(6)
                    record_time = tm[:4]
                else:
                    kst = pytz.timezone("Asia/Seoul")
                    record_time = datetime.now(kst).strftime("%H%M")
                if not record_date:
                    kst = pytz.timezone("Asia/Seoul")
                    record_date = datetime.now(kst).strftime("%Y%m%d")
                try:
                    record_volume = abs(int(response.get("trde_qty", 0)))
                except Exception:
                    record_volume = None
                break

            sleepCount += 1
            if sleepCount > 5:
                LogWriter().write_log(
                    "Error exceeds 5 times. Use previous MIN price", LogLevel.ERROR
                )
                currentPrice = self.stock_db.price_db[symbol][StockTick.MIN1][-1]
                break

        if record_date and record_time:
            self.stock_db.record_minute_price(
                "kiwoom", symbol, record_date, record_time, currentPrice, record_volume
            )
        return currentPrice

    def check_and_update_stock_info(self, symbol, info):
        response = self.kiwoom.get_stock_basic_info(symbol)
        stock_name = response["name"]

        if info != stock_name:
            LogWriter().write_log(
                "Stock name is different by local: {} kiwoom: {}".format(
                    info, stock_name
                ),
                LogLevel.ERROR,
            )
            info = stock_name
            return False

        self.stock_db.name_table[symbol] = info
        return True

    def get_available_cash(self):
        for _ in range(5):
            try:
                output = self.kiwoom.get_deposit_info()

                if output["return_code"] != 0:
                    LogWriter().write_log(
                        "Failed to get available cash, try again.. return code: {} ({})".format(
                            output["return_code"], output.get("return_msg", "")
                        ),
                        LogLevel.ERROR,
                    )
                    continue
                else:
                    cash = int(output["100stk_ord_alow_amt"])
                    LogWriter().write_log(
                        "Available cash: {}".format(cash), LogLevel.DEBUG
                    )
                    return max(cash - 50000, 0)
            except Exception as e:
                LogWriter().write_log(
                    "Failed to get available cash: {}".format(str(e)), LogLevel.ERROR
                )

        return None


    def place_market_buy(self, symbol, quantity):
        hoga = None
        if not self.mock:
            try:
                hoga_data = self.kiwoom.get_hoga(symbol)
                if hoga_data.get("return_code") == 0:
                    hoga = self._parse_hoga_price(hoga_data.get("sel_fpr_bid"))
            except Exception as e:
                LogWriter().write_log(
                    "Failed to fetch hoga for buy: {}".format(str(e)),
                    LogLevel.ERROR,
                )
        if hoga is None:
            hoga = self.stock_db.price_db[symbol][StockTick.MIN1][-1]

        response = self.kiwoom.send_order(
            symbol=symbol, quantity=str(quantity), buy=True, price=hoga
        )

        if response["return_code"] != 0:
            LogWriter().write_log(
                "{} : Buy SendOrder failed, ret: {} ({})".format(
                    self.stock_db.name_table[symbol],
                    response["return_code"],
                    response.get("return_msg", ""),
                ),
                LogLevel.ERROR,
            )
            return 0

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
        hoga = None
        if not self.mock:
            try:
                hoga_data = self.kiwoom.get_hoga(symbol)
                if hoga_data.get("return_code") == 0:
                    hoga = self._parse_hoga_price(hoga_data.get("buy_fpr_bid"))
            except Exception as e:
                LogWriter().write_log(
                    "Failed to fetch hoga for sell: {}".format(str(e)),
                    LogLevel.ERROR,
                )
        if hoga is None:
            hoga = self.stock_db.price_db[symbol][StockTick.MIN1][-1]

        response = self.kiwoom.send_order(
            symbol=symbol, quantity=str(quantity), buy=False, price=hoga
        )

        if response["return_code"] != 0:
            LogWriter().write_log(
                "{} : Sell SendOrder failed, ret: {} ({})".format(
                    self.stock_db.name_table[symbol],
                    response["return_code"],
                    response.get("return_msg", ""),
                ),
                LogLevel.ERROR,
            )
            return 0
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

    def get_stock_balance(self):
        response = self.kiwoom.get_account_balance()
        result = [
            {
                "symbol": item["stk_cd"],
                "name": item["stk_nm"],
                "rmnd_qty": item["rmnd_qty"],
                "buy_price": item["buy_uv"],
                "cur_price": item["cur_prc"],
            }
            for item in response["day_bal_rt"]
        ]
        return result
