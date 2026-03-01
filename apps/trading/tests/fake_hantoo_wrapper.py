import os

from core.infra.hantoo_wrapper import HantooWrapper
from core.infra.stock_db import StockDataBase
from apps.trading.tests.fake_hantoo_rest import FakeKoreaInvestment


class FakeHantooWrapper(HantooWrapper):
    def __init__(self, record_path=None):
        super().__init__(stock_db=StockDataBase())
        self.record_path = record_path

    def connect(self, mode):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if self.record_path is None:
            self.record_path = os.path.join(current_dir, "fixtures", "hantoo_prices.jsonl")

        acc_no = "12345678-01"
        self.rp_etf_symbol = "423160"
        self.mock = mode == "test"
        self.order = []
        self.broker = FakeKoreaInvestment(acc_no=acc_no, record_path=self.record_path)
