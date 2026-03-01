"""Default chain-based strategy runtime."""

from copy import deepcopy
from typing import Dict, List, Tuple

from core.domain import StageType
from signals.conditions.factory.base import ConditionBundle, ConditionChain, ConditionLike


class ChainStrategyRuntime:
    """Run buy/sell condition chains with optional gate and one-or-more entries."""

    def __init__(self, bundle: ConditionBundle, trader=None):
        self.condition_groups = {
            "buy": self._clone_chains(bundle.chain_groups.get("buy", [])),
            "sell": self._clone_chains(bundle.chain_groups.get("sell", [])),
        }
        self.refs: Dict[str, ConditionLike] = dict(bundle.refs)
        self._last_snapshot = {
            "buy": (StageType.NONE, StageType.NONE),
            "sell": (StageType.NONE, StageType.NONE),
        }
        self._bind_trader(trader)

    @staticmethod
    def _clone_chains(chains: List[ConditionChain]) -> List[ConditionChain]:
        return [ConditionChain(gate=chain.gate, entries=list(chain.entries)) for chain in chains]

    def _bind_trader(self, trader):
        for chains in self.condition_groups.values():
            for chain in chains:
                if chain.entries:
                    chain.entries[-1].trader = trader

    @staticmethod
    def _queue_stages(side: str):
        if side == "buy":
            return (StageType.BUY_1, StageType.BUY_2, StageType.BUY_3)
        return (StageType.SELL_1, StageType.SELL_2, StageType.SELL_3)

    def _run_chain(self, side: str, chain: ConditionChain) -> Tuple[int, int]:
        if not chain.entries:
            return (0, StageType.NONE)

        gate_stage = StageType.NONE
        gate_qty = None
        if chain.gate is not None:
            gate_qty, gate_stage = chain.gate.execute()
            if not gate_qty:
                return (0, StageType.NONE)
            for entry in chain.entries:
                entry.update_quantity(gate_qty)

        for entry in chain.entries:
            qty, entry_stage = entry.execute()
            if not qty:
                continue

            if chain.gate is not None:
                entry.settle(qty, entry_stage, long_stage=gate_stage)
                chain.gate.settle(qty, gate_stage)
            else:
                entry.settle(qty, entry_stage)

            queue_stage = getattr(entry, "_last_queue_stage", StageType.NONE)
            if queue_stage in self._queue_stages(side):
                snapshot = (queue_stage, getattr(entry, "last_stage", StageType.NONE))
            else:
                snapshot = (
                    gate_stage if chain.gate is not None else StageType.NONE,
                    entry_stage,
                )
            self._last_snapshot[side] = snapshot
            return (qty, snapshot[0] if snapshot[0] != StageType.NONE else snapshot[1])

        return (0, StageType.NONE)

    def run_buy(self) -> Tuple[int, int]:
        for chain in self.condition_groups["buy"]:
            buy, stage = self._run_chain("buy", chain)
            if buy:
                return (buy, stage)
        return (0, StageType.NONE)

    def run_sell(self) -> Tuple[int, int]:
        for chain in self.condition_groups["sell"]:
            sell, stage = self._run_chain("sell", chain)
            if sell:
                return (sell, stage)
        return (0, StageType.NONE)

    def sync_order_quantities(self, buy_tick, sell_tick, buy, sell) -> None:
        self._sync_side_quantities("buy", buy_tick, buy)
        self._sync_side_quantities("sell", sell_tick, sell)

    def _sync_side_quantities(self, side: str, tick, quantity) -> None:
        for chain in self.condition_groups[side]:
            if chain.gate is not None:
                chain.gate.update_quantity(quantity, tick=tick)

    def stage_snapshot(self, side: str) -> Tuple[int, int]:
        if side not in ("buy", "sell"):
            raise ValueError("side must be 'buy' or 'sell'")
        return self._last_snapshot[side]

    def as_bundle(self) -> ConditionBundle:
        return ConditionBundle(
            chain_groups=deepcopy(self.condition_groups),
            refs=dict(self.refs),
        )
