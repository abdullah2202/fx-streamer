"""Metrics and logging utilities."""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field

from pythonjsonlogger import jsonlogger


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure structured JSON logging."""
    logger = logging.getLogger("fx-streamer")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(  # type: ignore[no-untyped-call]
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


@dataclass
class Metrics:
    """Track streaming metrics."""

    tick_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    last_report_time: float = field(default_factory=time.time)
    report_interval: float = 10.0  # seconds
    disconnect_count: int = 0
    reconnect_count: int = 0

    def record_tick(self, instrument: str) -> None:
        """Record a tick for an instrument."""
        self.tick_counts[instrument] += 1

    def record_disconnect(self, reason: str, logger: logging.Logger) -> None:
        """Log disconnect event."""
        self.disconnect_count += 1
        logger.warning(
            "Stream disconnected",
            extra={
                "reason": reason,
                "disconnect_count": self.disconnect_count,
            },
        )

    def record_reconnect(self, logger: logging.Logger) -> None:
        """Log reconnection attempt."""
        self.reconnect_count += 1
        logger.info(
            "Reconnecting to stream",
            extra={"reconnect_count": self.reconnect_count},
        )

    def maybe_report(self, logger: logging.Logger) -> None:
        """Report ticks-per-second if interval has passed."""
        now = time.time()
        elapsed = now - self.last_report_time

        if elapsed >= self.report_interval:
            tps = {}
            for instrument, count in self.tick_counts.items():
                tps[instrument] = round(count / elapsed, 2)

            logger.info(
                "Ticks per second",
                extra={
                    "tps": tps,
                    "interval_seconds": round(elapsed, 1),
                    "total_ticks": sum(self.tick_counts.values()),
                },
            )

            # Reset counters
            self.tick_counts.clear()
            self.last_report_time = now
