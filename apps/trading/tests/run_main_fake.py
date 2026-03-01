import argparse

from apps.trading.main import run_trading
from apps.trading.tests.fake_kiwoom_wrapper import FakeKiwoomWrapper
from apps.trading.tests.fake_hantoo_wrapper import FakeHantooWrapper


class AlwaysOpenMarketTime:
    def is_exchange_available(self):
        return True

    def is_pre_market_open(self):
        return False

    def is_market_open(self):
        return True

    def is_market_close(self):
        return False

    def is_week_close(self):
        return False

    def get_minute(self):
        return 0


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Run apps.trading.main logic with fake wrappers and recorded data."
    )
    parser.add_argument("invest_company", choices=["kiwoom", "hantoo"])
    parser.add_argument("quant_mode", choices=["test", "quant", "isa"])
    parser.add_argument("--max-loops", type=int, default=3)
    parser.add_argument("--kiwoom-data", default=None)
    parser.add_argument("--hantoo-data", default=None)
    return parser.parse_args()


def main():
    args = _parse_args()
    market_time = AlwaysOpenMarketTime()

    if args.invest_company == "kiwoom":
        wrapper = FakeKiwoomWrapper(record_path=args.kiwoom_data)
    else:
        wrapper = FakeHantooWrapper(record_path=args.hantoo_data)

    run_trading(
        args.invest_company,
        args.quant_mode,
        log_category="test",
        investCommunicator=wrapper,
        market_time=market_time,
        sleep_fn=lambda _: None,
        align_to_minute=False,
        max_loops=args.max_loops,
    )


if __name__ == "__main__":
    main()
