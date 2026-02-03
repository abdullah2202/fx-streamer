"""OHLC candle aggregation from tick data."""

import asyncio
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .publisher import RedisPublisher

from .enricher import EnrichedTick


@dataclass
class Candle:
    """OHLC candle for a single period."""

    instrument: str
    period_seconds: int
    period_start: float  # Unix timestamp
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    tick_count: int = 0

    def update(self, mid_price: Decimal) -> None:
        """Update candle with new tick."""
        if self.tick_count == 0:
            self.open = mid_price
            self.high = mid_price
            self.low = mid_price
        else:
            self.high = max(self.high, mid_price)
            self.low = min(self.low, mid_price)
        self.close = mid_price
        self.tick_count += 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "instrument": self.instrument,
            "period": f"{self.period_seconds}s",
            "period_start": self.period_start,
            "open": str(self.open),
            "high": str(self.high),
            "low": str(self.low),
            "close": str(self.close),
            "tick_count": self.tick_count,
        }


@dataclass
class Aggregator:
    """Aggregate ticks into OHLC candles."""

    periods: list[int]  # Periods in seconds
    publisher: "RedisPublisher"
    logger: logging.Logger

    # Current candles: {(instrument, period): Candle}
    _candles: dict[tuple[str, int], Candle] = field(default_factory=dict)
    _flush_task: asyncio.Task[None] | None = field(default=None, init=False)

    def _get_period_start(self, timestamp: float, period: int) -> float:
        """Get the start of the current period."""
        return (timestamp // period) * period

    async def process(self, tick: EnrichedTick) -> None:
        """Process a tick and update candles."""
        for period in self.periods:
            key = (tick.instrument, period)
            period_start = self._get_period_start(tick.timestamp_unix, period)

            if key not in self._candles:
                # Start new candle
                self._candles[key] = Candle(
                    instrument=tick.instrument,
                    period_seconds=period,
                    period_start=period_start,
                    open=tick.mid_price,
                    high=tick.mid_price,
                    low=tick.mid_price,
                    close=tick.mid_price,
                    tick_count=0,
                )

            candle = self._candles[key]

            # Check if we need to start a new candle
            if period_start > candle.period_start:
                # Flush the completed candle
                await self._flush_candle(candle)
                # Start new candle
                self._candles[key] = Candle(
                    instrument=tick.instrument,
                    period_seconds=period,
                    period_start=period_start,
                    open=tick.mid_price,
                    high=tick.mid_price,
                    low=tick.mid_price,
                    close=tick.mid_price,
                    tick_count=0,
                )
                candle = self._candles[key]

            candle.update(tick.mid_price)

    async def _flush_candle(self, candle: Candle) -> None:
        """Publish completed candle to Redis."""
        if candle.tick_count > 0:
            await self.publisher.publish_candle(candle)
            self.logger.debug(
                "Flushed candle",
                extra={
                    "instrument": candle.instrument,
                    "period": f"{candle.period_seconds}s",
                    "tick_count": candle.tick_count,
                },
            )

    async def flush_all(self) -> None:
        """Flush all current candles (for graceful shutdown)."""
        for candle in self._candles.values():
            await self._flush_candle(candle)
        self._candles.clear()
