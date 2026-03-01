import os
from pathlib import Path

from core.infra.api_recording import ApiRecorder
from core.infra.kiwoom_rest import KiwoomRestAPI
from core.infra.util import find_project_root

RECORDING_ENABLED = False


class KiwoomRecordRestAPI(KiwoomRestAPI):
    def __init__(self, api_key: str, api_secret: str, mock=False, record_path=None):
        default_path = (
            find_project_root(Path(__file__).resolve())
            / "apps"
            / "trading"
            / "tests"
            / "fixtures"
            / "kiwoom.jsonl"
        )
        self._record_path = record_path or os.getenv("KIWOOM_RECORD_PATH") or str(default_path)
        self._recorder = None
        super().__init__(api_key, api_secret, mock=mock)
        if RECORDING_ENABLED and self._record_path:
            self._recorder = ApiRecorder(self._record_path)

    def _record(self, method, params, response):
        if self._recorder:
            self._recorder.record(method, params, response)

    def get_last_prices(self, symbol: str, period_unit: str, base_period: str):
        response = super().get_last_prices(symbol, period_unit, base_period)
        record_params = {
            "symbol": symbol,
            "period_unit": period_unit,
            "base_period": "" if period_unit in ["DAY", "WEEK"] else base_period,
        }
        self._record("get_last_prices", record_params, response)
        return response

    def get_stock_basic_info(self, symbol: str):
        response = super().get_stock_basic_info(symbol)
        self._record("get_stock_basic_info", {"symbol": symbol}, response)
        return response

    def get_stock_price_info(self, symbol):
        response = super().get_stock_price_info(symbol)
        self._record("get_stock_price_info", {"symbol": symbol}, response)
        return response

    def send_order(self, symbol: str, quantity: int, buy: bool, price):
        response = super().send_order(symbol, quantity, buy, price)
        record_params = {
            "symbol": symbol,
            "quantity": quantity,
            "buy": buy,
            "price": price,
        }
        self._record("send_order", record_params, response)
        return response

    def get_deposit_info(self):
        response = super().get_deposit_info()
        self._record("get_deposit_info", {}, response)
        return response

    def get_basic_info(self, symbol: str):
        response = super().get_basic_info(symbol)
        self._record("get_basic_info", {"symbol": symbol}, response)
        return response

    def get_account_balance(self):
        response = super().get_account_balance()
        self._record("get_account_balance", {}, response)
        return response

    def get_hoga(self, symbol: str):
        response = super().get_hoga(symbol)
        self._record("get_hoga", {"symbol": symbol}, response)
        return response
