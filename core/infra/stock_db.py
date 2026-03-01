from datetime import datetime

import pandas as pd
import pytz
from core.infra.util import get_minute_db_dir


class StockDataBase:
    def __init__(self):
        self.price_db = {}
        # KRX: symbol to name mapping, Nasdaq: symbol to exchange mapping
        self.name_table = {}
        self.order_table = {}
        self.week_trade_quantity = {}
        self.minute_price_db = {}
        self.vwap_bar_db = {}
        self.orderIO = None
        self.investCommunicator = None

    def bind(self, order_io, invest_communicator):
        self.orderIO = order_io
        self.investCommunicator = invest_communicator

    def __call__(self, order_io, invest_communicator):
        self.bind(order_io, invest_communicator)

    def record_minute_price(
        self, company, symbol, date_str, time_str, price_close, volume_cum
    ):
        if company not in self.minute_price_db:
            self.minute_price_db[company] = {}

        name = self.name_table.get(symbol, "")
        key = f"{date_str}_{time_str}_{symbol}"
        self.minute_price_db[company][key] = {
            "date": date_str,
            "time": time_str,
            "symbol": symbol,
            "name": name,
            "price_close": price_close,
            "volume_cum": volume_cum,
        }

    def _get_company_today(self, company):
        if company == "hantoo":
            tz = pytz.timezone("America/New_York")
        else:
            tz = pytz.timezone("Asia/Seoul")
        return datetime.now(tz).strftime("%Y%m%d")

    def save_minute_price_db(self, company):
        data = self.minute_price_db.get(company, {})
        if not data:
            return None

        base_dir = get_minute_db_dir()
        base_dir.mkdir(parents=True, exist_ok=True)

        file_name = f"{self._get_company_today(company)}_{company}_prices.xlsx"
        file_path = base_dir / file_name

        df = pd.DataFrame(
            data.values(),
            columns=["date", "time", "symbol", "name", "price_close", "volume_cum"],
        )
        if company == "hantoo":
            df = df.rename(columns={"name": "excd"})
        df.to_excel(file_path, index=False)
        return str(file_path)
