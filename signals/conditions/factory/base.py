"""Base interfaces for condition factories and runtime."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol, Tuple


class ConditionLike(Protocol):
    """Minimal condition contract used by strategy runtime."""

    last_stage: int

    def execute(self, quantity=None, required_stage=None):
        ...

    def settle(self, executed_qty, stage, **kwargs):
        ...

    def update_quantity(self, quantity, tick=None):
        ...


@dataclass
class ConditionChain:
    """One executable chain: optional gate + one or more entries."""

    entries: List[ConditionLike] = field(default_factory=list)
    gate: Optional[ConditionLike] = None


@dataclass(frozen=True)
class StockContext:
    """Immutable stock context passed to a condition factory."""

    symbol: str
    name: str
    buy_tick: int
    sell_tick: int
    min_sell_price: float
    stock_db: object
    trader: object = None


@dataclass
class ConditionBundle:
    """Runtime-ready condition graph and named references."""

    chain_groups: Dict[str, List[ConditionChain]]
    refs: Dict[str, ConditionLike]


class StrategyRuntime(Protocol):
    """Execution contract consumed by Stock."""

    def run_buy(self) -> Tuple[int, int]:
        ...

    def run_sell(self) -> Tuple[int, int]:
        ...

    def sync_order_quantities(self, buy_tick, sell_tick, buy, sell) -> None:
        ...

    def stage_snapshot(self, side: str) -> Tuple[int, int]:
        ...


class ConditionFactory(Protocol):
    """Factory contract for profile-specific condition composition."""

    profile: str

    def create(self, ctx: StockContext) -> StrategyRuntime:
        ...
