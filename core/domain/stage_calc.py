import pandas
from core.infra import LogWriter, LogLevel
from core.domain import StageType


class StageCalculator:
    def __init__(self, stock_db):
        self.stock_db = stock_db

    def calc_ma_stage_by_series(self, ewm_5, ewm_20, ewm_40):
        if ewm_5.iloc[-1] > ewm_20.iloc[-1] and ewm_20.iloc[-1] > ewm_40.iloc[-1]:
            if self.is_crossed(ewm_5, ewm_40, golden=False):
                return StageType.SELL_1
            return StageType.BUY_3
        elif ewm_5.iloc[-1] > ewm_40.iloc[-1] and ewm_20.iloc[-1] <= ewm_40.iloc[-1]:
            return StageType.BUY_2
        elif ewm_5.iloc[-1] <= ewm_40.iloc[-1] and ewm_5.iloc[-1] > ewm_20.iloc[-1]:
            return StageType.BUY_1

        elif ewm_5.iloc[-1] < ewm_20.iloc[-1] and ewm_20.iloc[-1] < ewm_40.iloc[-1]:
            if self.is_crossed(ewm_5, ewm_40, golden=True):
                return StageType.BUY_1
            return StageType.SELL_3
        elif ewm_5.iloc[-1] < ewm_40.iloc[-1] and ewm_20.iloc[-1] >= ewm_40.iloc[-1]:
            return StageType.SELL_2
        else:
            return StageType.SELL_1

    def calc_ma_stage(self, symbol, tick, prev=False):
        ewm_values = self.get_ewm_values(symbol, tick, prev=prev)

        ewm_5 = ewm_values["ewm_5"]
        ewm_20 = ewm_values["ewm_20"]
        ewm_40 = ewm_values["ewm_40"]

        LogWriter().write_log(
            "calc_ma_stage() {} {} : ewm_5: {}, ewm_20: {}, ewm_40: {}".format(
                symbol,
                self.stock_db.name_table[symbol],
                int(ewm_5.iloc[-1]),
                int(ewm_20.iloc[-1]),
                int(ewm_40.iloc[-1]),
            ),
            LogLevel.DEBUG,
        )

        return self.calc_ma_stage_by_series(ewm_5, ewm_20, ewm_40)

    def is_gradients_increasing(self, symbol, tick):
        ewm_values = self.get_ewm_values(symbol, tick)

        if ewm_values["ewm_5"].iloc[-1] < ewm_values["ewm_5"].iloc[-2]:
            LogWriter().write_log(
                "checkGradientIncreasing() fail by ewm_5", LogLevel.DEBUG
            )
            return False
        if ewm_values["ewm_20"].iloc[-1] < ewm_values["ewm_20"].iloc[-2]:
            LogWriter().write_log(
                "checkGradientIncreasing() fail by ewm_20", LogLevel.DEBUG
            )
            return False
        if ewm_values["ewm_40"].iloc[-1] < ewm_values["ewm_40"].iloc[-2]:
            LogWriter().write_log(
                "checkGradientIncreasing. Can be NONE?", LogLevel.DEBUG
            )

        return True

    def is_gradients_decreasing(self, symbol, tick):
        ewm_values = self.get_ewm_values(symbol, tick)

        if ewm_values["ewm_5"].iloc[-1] > ewm_values["ewm_5"].iloc[-2]:
            LogWriter().write_log(
                "checkGradientDecreasing() fail by ewm_5", LogLevel.DEBUG
            )
            return False
        if ewm_values["ewm_20"].iloc[-1] > ewm_values["ewm_20"].iloc[-2]:
            LogWriter().write_log(
                "checkGradientDecreasing() fail by ewm_20", LogLevel.DEBUG
            )
            return False
        if ewm_values["ewm_40"].iloc[-1] > ewm_values["ewm_40"].iloc[-2]:
            LogWriter().write_log(
                "checkGradientDecreasing. Can be NONE?", LogLevel.DEBUG
            )

        return True

    def is_crossed(self, short, long, golden=True):
        diff = short - long
        signal = diff.ewm(span=9).mean()
        if golden:
            return diff.iloc[-1] > signal.iloc[-1]
        else:
            return diff.iloc[-1] <= signal.iloc[-1]

    def get_ewm_values(self, symbol, tick, prev=False):
        price_list = self.stock_db.price_db.get(symbol, {}).get(tick, [])
        price_to_series = pandas.Series(price_list)
        if prev:
            if len(price_to_series) < 2:
                return {
                    "ewm_5": pandas.Series(dtype=float),
                    "ewm_20": pandas.Series(dtype=float),
                    "ewm_40": pandas.Series(dtype=float),
                }
            price_to_series = price_to_series.iloc[:-1]

        ewm_5 = price_to_series.ewm(span=5).mean()
        ewm_20 = price_to_series.ewm(span=20).mean()
        ewm_40 = price_to_series.ewm(span=40).mean()

        return {
            "ewm_5": ewm_5,
            "ewm_20": ewm_20,
            "ewm_40": ewm_40,
        }
