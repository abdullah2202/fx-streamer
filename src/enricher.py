"""Tick enrichment with derived fields."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .validator import ValidatedTick

# Pip multipliers by instrument suffix
# JPY pairs have 2 decimal places, others have 4
PIP_MULTIPLIERS: dict[str, int] = {
    "JPY": 100,  # 0.01 = 1 pip
    "DEFAULT": 10000,  # 0.0001 = 1 pip
}


@dataclass
class EnrichedTick:
    """Tick data with derived fields."""

    instrument: str
    time: str
    timestamp_unix: float
    best_bid: Decimal
    best_ask: Decimal
    bid_liquidity: int
    ask_liquidity: int
    tradeable: bool
    mid_price: Decimal
    spread: Decimal
    spread_pips: Decimal

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "instrument": self.instrument,
            "time": self.time,
            "timestamp_unix": self.timestamp_unix,
            "bid": str(self.best_bid),
            "ask": str(self.best_ask),
            "bid_liquidity": self.bid_liquidity,
            "ask_liquidity": self.ask_liquidity,
            "tradeable": self.tradeable,
            "mid": str(self.mid_price),
            "spread": str(self.spread),
            "spread_pips": float(self.spread_pips),
        }


def _get_pip_multiplier(instrument: str) -> int:
    """Get pip multiplier based on instrument."""
    # Check if it's a JPY pair
    if "JPY" in instrument:
        return PIP_MULTIPLIERS["JPY"]
    return PIP_MULTIPLIERS["DEFAULT"]


def enrich_tick(tick: ValidatedTick) -> EnrichedTick:
    """
    Calculate derived fields from validated tick.

    Derived fields:
        - mid_price: (bid + ask) / 2
        - spread: ask - bid
        - spread_pips: spread in pips based on instrument
    """
    mid_price = (tick.best_bid + tick.best_ask) / 2
    spread = tick.best_ask - tick.best_bid
    pip_multiplier = _get_pip_multiplier(tick.instrument)
    spread_pips = spread * pip_multiplier

    return EnrichedTick(
        instrument=tick.instrument,
        time=tick.time,
        timestamp_unix=tick.timestamp_unix,
        best_bid=tick.best_bid,
        best_ask=tick.best_ask,
        bid_liquidity=tick.bid_liquidity,
        ask_liquidity=tick.ask_liquidity,
        tradeable=tick.tradeable,
        mid_price=mid_price,
        spread=spread,
        spread_pips=spread_pips,
    )
