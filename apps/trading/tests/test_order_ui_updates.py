import unittest
from unittest.mock import patch

import pandas as pd

from apps.trading.infra.order_ui import OrderIOManager
from core.domain import StockTick


class OrderUIUpdatesTest(unittest.TestCase):
    def test_first_read_saves_comparison_snapshot(self):
        manager = object.__new__(OrderIOManager)
        manager.file_name = "unused.xlsx"
        manager._previous_order_inputs = None
        orders = pd.DataFrame(
            [
                {
                    "symbol": "TEST",
                    "name": "TEST",
                    "buy_1": 3,
                    "buy_2": 2,
                    "buy_3": 1,
                    "sell_1": 3,
                    "sell_2": 0,
                    "sell_3": 0,
                    "buyTick": "MIN15",
                    "sellTick": "MIN15",
                }
            ]
        )

        with patch(
            "apps.trading.infra.order_ui.pd.read_excel", return_value=orders
        ):
            stock_infos = manager.read_stock_infos()

        self.assertEqual(
            manager._previous_order_inputs["TEST"],
            (3, 2, 1, 3, 0, 0, StockTick.MIN15, StockTick.MIN15),
        )
        self.assertEqual(stock_infos["TEST"]["buyTick"], StockTick.MIN15)

    def test_only_returns_order_inputs_changed_since_previous_snapshot(self):
        initial = {
            "TEST": {
                "name": "before",
                "buy_1": 3,
                "buy_2": 2,
                "buy_3": 1,
                "sell_1": 3,
                "sell_2": 0,
                "sell_3": 0,
                "buyTick": StockTick.MIN15,
                "sellTick": StockTick.MIN15,
            }
        }
        renamed = {"TEST": {**initial["TEST"], "name": "after"}}
        changed = {"TEST": {**renamed["TEST"], "buy_1": 4}}
        manager = object.__new__(OrderIOManager)
        manager._previous_order_inputs = {
            "TEST": manager._order_input_values(initial["TEST"])
        }

        with patch.object(
            manager,
            "read_stock_infos",
            side_effect=[renamed, changed, changed],
        ):
            self.assertEqual(manager.read_changed_stock_infos(), {})
            self.assertEqual(manager.read_changed_stock_infos(), changed)
            self.assertEqual(manager.read_changed_stock_infos(), {})


if __name__ == "__main__":
    unittest.main()
