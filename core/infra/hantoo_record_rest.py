import os
from pathlib import Path

from core.infra.api_recording import ApiRecorder
from core.infra.hantoo_rest import KoreaInvestment
from core.infra.util import find_project_root

RECORDING_ENABLED = False


class HantooRecordRestAPI(KoreaInvestment):
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        acc_no: str,
        mock: bool = False,
        record_path=None,
    ):
        default_path = (
            find_project_root(Path(__file__).resolve())
            / "apps"
            / "trading"
            / "tests"
            / "fixtures"
            / "hantoo.jsonl"
        )
        self._record_path = record_path or os.getenv("HANTOO_RECORD_PATH") or str(default_path)
        self._recorder = None
        super().__init__(api_key, api_secret, acc_no, mock=mock)
        if RECORDING_ENABLED and self._record_path:
            self._recorder = ApiRecorder(self._record_path)

    def _record(self, method, params, response):
        if self._recorder:
            self._recorder.record(method, params, response)

    def get_oversea_available_cash(self):
        response = super().get_oversea_available_cash()
        self._record("get_oversea_available_cash", {}, response)
        return response

    def fetch_usa_1m_ohlcv(self, symbol: str, excd: str, nmin: int):
        response = super().fetch_usa_1m_ohlcv(symbol, excd, nmin)
        record_params = {"symbol": symbol, "excd": excd, "nmin": nmin}
        self._record("fetch_usa_1m_ohlcv", record_params, response)
        return response

    def fetch_ohlcv_usa_overesea(
        self,
        symbol: str,
        excd: str,
        timeframe: str = "D",
        end_day: str = "",
        adj_price: bool = True,
    ):
        response = super().fetch_ohlcv_usa_overesea(
            symbol, excd, timeframe, end_day, adj_price
        )
        record_params = {
            "symbol": symbol,
            "excd": excd,
            "timeframe": timeframe,
            "end_day": "",
            "adj_price": adj_price,
        }
        self._record("fetch_ohlcv_usa_overesea", record_params, response)
        return response

    def fetch_domestic_usa_price(self, symbol: str, excd: str) -> dict:
        response = super().fetch_domestic_usa_price(symbol, excd)
        record_params = {"symbol": symbol, "excd": excd}
        self._record("fetch_domestic_usa_price", record_params, response)
        return response

    def get_basic_info(self, symbol: str, excd: str):
        response = super().get_basic_info(symbol, excd)
        record_params = {"symbol": symbol, "excd": excd}
        self._record("get_basic_info", record_params, response)
        return response

    def create_oversea_order(
        self,
        side: str,
        exchange: str,
        symbol: str,
        price,
        quantity,
        order_type: str,
    ) -> dict:
        response = super().create_oversea_order(
            side, exchange, symbol, price, quantity, order_type
        )
        record_params = {
            "side": side,
            "exchange": exchange,
            "symbol": symbol,
            "price": price,
            "quantity": quantity,
            "order_type": order_type,
        }
        self._record("create_oversea_order", record_params, response)
        return response

    def get_hoga(self, symbol: str, excd: str):
        response = super().get_hoga(symbol, excd)
        record_params = {"symbol": symbol, "excd": excd}
        self._record("get_hoga", record_params, response)
        return response

    def check_confirmed_order(self, day=""):
        response = super().check_confirmed_order(day)
        self._record("check_confirmed_order", {"day": ""}, response)
        return response

    def get_account_balance(self):
        response = super().get_account_balance()
        self._record("get_account_balance", {}, response)
        return response
