import os
import tomllib
from core.infra import LogWriter, LogLevel
from core.infra.trading_profile import load_trading_profile
from core.domain import StockTick, StageType

import pandas as pd


DEFAULT_CONDITION_PROFILE = "private_condition"
CONDITION_PROFILE_FILE_NAME = "condition_profiles.toml"
ORDER_INPUT_FIELDS = (
    "buy_1",
    "buy_2",
    "buy_3",
    "sell_1",
    "sell_2",
    "sell_3",
    "buyTick",
    "sellTick",
)


class OrderIOManager:
    def __init__(self, invest_company, account_type):
        self.invest_company = invest_company
        self.account_type = account_type
        self.condition_profiles = {}
        self._previous_order_inputs = None
        try:
            profile = load_trading_profile(invest_company, account_type)
            if profile.order_file is None:
                raise RuntimeError(
                    "order_file is required for trading runtime profiles"
                )
            self.file_name = str(profile.order_file)
            self.condition_profile_file = (
                profile.order_file.parent / CONDITION_PROFILE_FILE_NAME
            )
            self.condition_profiles = self._load_condition_profiles()
            os.makedirs(os.path.dirname(self.file_name), exist_ok=True)
        except Exception as e:
            LogWriter().write_log(str(e), LogLevel.ERROR)
            exit(0)

    def _load_condition_profiles(self):
        if not self.condition_profile_file.exists():
            return {}

        with open(self.condition_profile_file, "rb") as f:
            config = tomllib.load(f)

        if not isinstance(config, dict):
            return {}
        return config

    @staticmethod
    def _normalize_profile(value):
        if value is None:
            return None
        value = str(value).strip()
        return value or None

    def _profile_section_candidates(self):
        account_key = str(self.account_type).strip()
        broker_account_key = "{}_{}".format(
            str(self.invest_company).strip(), account_key
        )
        return [broker_account_key, account_key]

    def get_condition_profile(self, symbol):
        symbol = str(symbol)

        for section_name in self._profile_section_candidates():
            section = self.condition_profiles.get(section_name)
            if not isinstance(section, dict):
                continue
            symbols = section.get("symbols")
            if not isinstance(symbols, dict):
                continue
            profile = self._normalize_profile(symbols.get(symbol))
            if profile:
                return profile

        return (
            self._normalize_profile(self.condition_profiles.get("default"))
            or DEFAULT_CONDITION_PROFILE
        )

    def update_account_balance(self, balances):
        try:
            df = pd.read_excel(self.file_name, dtype={"symbol": str})

            bal_map = {}
            for item in balances:
                try:
                    s = str(item.get("symbol"))
                    rmnd = int(item.get("rmnd_qty", 0))
                    bal_map[s] = rmnd
                except Exception:
                    continue

            for index, row in df.iterrows():
                sym = str(row["symbol"])
                df.loc[index, "acc_balance"] = bal_map.get(sym, 0)

            df.to_excel(self.file_name, index=False)
            return

        except Exception as e:
            LogWriter().write_log(e.__str__(), LogLevel.ERROR)
            exit(0)

        LogWriter().write_log("update account balance failed", LogLevel.ERROR)
        exit(0)

    @staticmethod
    def _order_input_values(stock_info):
        # Keep only fields that trigger runtime quantity sync.
        return tuple(stock_info[field] for field in ORDER_INPUT_FIELDS)

    def read_stock_infos(self):
        stock_orders = {}
        try:
            df = pd.read_excel(self.file_name, dtype={"symbol": str})
            for _, row in df.iterrows():
                stock_orders[row["symbol"]] = {
                    "name": row["name"],
                    "buy_1": int(row["buy_1"]),
                    "buy_2": int(row["buy_2"]),
                    "buy_3": int(row["buy_3"]),
                    "sell_1": int(row["sell_1"]),
                    "sell_2": int(row["sell_2"]),
                    "sell_3": int(row["sell_3"]),
                    "buyTick": StockTick.tick_mapper(row["buyTick"]),
                    "sellTick": StockTick.tick_mapper(row["sellTick"]),
                }
                # LogWriter.write_log(stock_orders[row["symbol"]].__str__())

        except Exception as e:
            LogWriter().write_log(e.__str__(), LogLevel.ERROR)
            exit(0)

        if self._previous_order_inputs is None:
            # Seed the first 15-minute comparison snapshot.
            self._previous_order_inputs = {
                symbol: self._order_input_values(stock_info)
                for symbol, stock_info in stock_orders.items()
            }
        return stock_orders

    def read_changed_stock_infos(self):
        # Compare with the previous snapshot, then advance it.
        stock_infos = self.read_stock_infos()
        current_order_inputs = {
            symbol: self._order_input_values(stock_info)
            for symbol, stock_info in stock_infos.items()
        }
        changed_stock_infos = {
            symbol: stock_info
            for symbol, stock_info in stock_infos.items()
            if self._previous_order_inputs.get(symbol)
            != current_order_inputs[symbol]
        }
        self._previous_order_inputs = current_order_inputs
        return changed_stock_infos

    def edit_stock_info(self, symbol, tickType, subtractValue):
        try:
            df = pd.read_excel(self.file_name, dtype={"symbol": str})

            mapper = {
                StageType.BUY_1: "buy_1",
                StageType.BUY_2: "buy_2",
                StageType.BUY_3: "buy_3",
                StageType.SELL_1: "sell_1",
                StageType.SELL_2: "sell_2",
                StageType.SELL_3: "sell_3",
            }
            for index, row in df.iterrows():
                if row["symbol"] == symbol:
                    df.loc[index, mapper[tickType]] -= subtractValue
                    df.to_excel(self.file_name, index=False)
                    return

        except Exception as e:
            LogWriter().write_log(e.__str__(), LogLevel.ERROR)
            exit(0)

        LogWriter().write_log(
            "edit stock info failed {} {}".format(symbol, tickType), LogLevel.ERROR
        )
        exit(0)

# if __name__ == "__main__":
#     start_time = time.time()
#     testIO = OrderIOManager("test")
#     print(testIO.read_stock_infos())
#     testIO.edit_stock_info("005930", StageType.BUY_1, 700)
#     print(testIO.read_stock_infos())
#     diff = time.time() - start_time
#     print(diff)
#     time.sleep(30-diff)
#     print(testIO.read_stock_infos())
