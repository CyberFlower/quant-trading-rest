"""Public condition factory implementations."""

from signals.conditions.factory.base import ConditionBundle, ConditionChain, StockContext
from signals.conditions.runtime.chain_runtime import ChainStrategyRuntime


class PublicExampleFactory:
    """Public sample profile with 1 gate + 1 entry on each side."""

    profile = "public_example"

    def create(self, ctx: StockContext):
        from signals.conditions.public.example_condition import (
            ExamplePriceCrossBuyEntry,
            ExamplePriceCrossSellEntry,
            ExampleQuantityGate,
        )

        buy_gate = ExampleQuantityGate()
        sell_gate = ExampleQuantityGate()
        buy_entry = ExamplePriceCrossBuyEntry(
            symbol=ctx.symbol,
            name=ctx.name,
            stock_db=ctx.stock_db,
            window=5,
        )
        sell_entry = ExamplePriceCrossSellEntry(
            symbol=ctx.symbol,
            name=ctx.name,
            min_sell_price=ctx.min_sell_price,
            stock_db=ctx.stock_db,
            window=5,
        )

        bundle = ConditionBundle(
            chain_groups={
                "buy": [ConditionChain(gate=buy_gate, entries=[buy_entry])],
                "sell": [ConditionChain(gate=sell_gate, entries=[sell_entry])],
            },
            refs={
                "buy_gate": buy_gate,
                "buy_entry": buy_entry,
                "sell_gate": sell_gate,
                "sell_entry": sell_entry,
            },
        )
        return ChainStrategyRuntime(bundle, trader=ctx.trader)
