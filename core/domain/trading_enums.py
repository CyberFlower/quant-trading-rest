"""Shared market-related enums and mappings.

Keep this module side-effect free so it can be reused across apps.
"""


class StockTick(enumerate):
    MIN1, MIN3, MIN5, MIN10, MIN15, MIN30, MIN45, HOUR, DAY, WEEK, MONTH, TOTAL = range(
        12
    )

    def tick_mapper(str):
        mapper = {
            "MIN1": StockTick.MIN1,
            "MIN3": StockTick.MIN3,
            "MIN5": StockTick.MIN5,
            "MIN10": StockTick.MIN10,
            "MIN15": StockTick.MIN15,
            "MIN30": StockTick.MIN30,
            "MIN45": StockTick.MIN45,
            "HOUR": StockTick.HOUR,
            "DAY": StockTick.DAY,
            "WEEK": StockTick.WEEK,
            "MONTH": StockTick.MONTH,
        }
        return mapper[str]


TickToMap = {
    StockTick.MIN1: 1,
    StockTick.MIN3: 3,
    StockTick.MIN5: 5,
    StockTick.MIN10: 10,
    StockTick.MIN15: 15,
    StockTick.MIN30: 30,
    StockTick.MIN45: 45,
    StockTick.HOUR: 60,
    StockTick.DAY: "D",
    StockTick.WEEK: "W",
    StockTick.MONTH: "M",
}


class StageType(enumerate):
    NONE, SELL_1, SELL_2, SELL_3, BUY_1, BUY_2, BUY_3, TOTAL = range(8)
