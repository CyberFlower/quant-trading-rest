import os
from core.infra import LogWriter, LogLevel
from core.domain import StockTick, StageType

import pandas as pd


class OrderIOManager:
    def __init__(self, invest_company, account_type):
        self.invest_company = invest_company
        self.account_type = account_type
        self.file_name = ""
        base_dir = os.path.join("order", invest_company)
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)

        if account_type == "test":
            self.file_name = os.path.join(base_dir, "test_order.xlsx")
        elif account_type == "quant":
            self.file_name = os.path.join(base_dir, "quant_order.xlsx")
        elif account_type == "isa":
            self.file_name = os.path.join(base_dir, "isa_order.xlsx")
        else:
            LogWriter().write_log("account_type error", LogLevel.ERROR)
            exit(0)

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

        return stock_orders

    # TODO Refactoring using list periodically. FILE IO spends a lot of time.
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

    def update_stage(self, symbol, dayStage, weekStage):
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
                    if weekStage != StageType.NONE:
                        df.loc[index, "week"] = mapper[weekStage]
                    if dayStage != StageType.NONE:
                        df.loc[index, "day"] = mapper[dayStage]
                    df.to_excel(self.file_name, index=False)
                    return

        except Exception as e:
            LogWriter().write_log("symbol: {} not found".format(symbol), LogLevel.ERROR)


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
