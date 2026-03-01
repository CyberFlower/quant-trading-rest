import os
from datetime import datetime

from core.infra.kiwoom_wrapper import KiwoomWrapper
from core.infra.stock_db import StockDataBase
from apps.trading.tests.fake_kiwoom_rest import FakeKiwoomRestAPI


class FakeKiwoomWrapper(KiwoomWrapper):
    def __init__(
        self,
        record_path=None,
        price_path=None,
        account_state=None,
        initial_cash=None,
        holdings=None,
    ):
        super().__init__(stock_db=StockDataBase())
        self.record_path = record_path
        self.price_path = price_path
        self.account_state = account_state
        self.initial_cash = initial_cash
        self.holdings = holdings
        self.today = datetime.now().strftime("%Y%m%d")

    def connect(self, mode):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if self.price_path is None:
            self.price_path = os.path.join(
                current_dir, "fixtures", "kiwoom_prices.jsonl"
            )

        self.stock_account = "12345678"
        self.rp_etf_symbol = "423160"
        self.al_symbol = "_AL" if mode != "test" else ""

        self.kiwoom = FakeKiwoomRestAPI(
            record_path=self.record_path,
            price_path=self.price_path,
            account_state=self.account_state,
            initial_cash=self.initial_cash,
            holdings=self.holdings,
        )
