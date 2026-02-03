"""Main entry point for OANDA streaming bot."""

import asyncio
import signal
import sys

from .aggregator import Aggregator
from .config import Config
from .enricher import enrich_tick
from .metrics import Metrics, setup_logging
from .oanda_client import OandaClient
from .publisher import RedisPublisher
from .validator import is_heartbeat, validate_tick


async def main() -> None:
    """Run the streaming bot."""
    # Load configuration
    config = Config()

    # Set up logging
    logger = setup_logging(config.log_level)
    logger.info(
        "Starting fx-streamer",
        extra={
            "instruments": config.instruments,
            "aggregation_periods": config.periods,
            "environment": config.oanda_environment,
        },
    )

    # Initialize components
    metrics = Metrics()
    publisher = RedisPublisher(config, logger)
    aggregator = Aggregator(
        periods=config.periods,
        publisher=publisher,
        logger=logger,
    )
    client = OandaClient(config, metrics, logger)

    # Graceful shutdown handling
    shutdown_event = asyncio.Event()

    def handle_shutdown(sig: signal.Signals) -> None:
        logger.info(f"Received {sig.name}, shutting down...")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, handle_shutdown, sig)

    # Connect to Redis
    try:
        await publisher.connect()
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        sys.exit(1)

    try:
        # Stream ticks
        async for raw_tick in client.stream():
            if shutdown_event.is_set():
                break

            # Skip heartbeats
            if is_heartbeat(raw_tick):
                logger.debug("Received heartbeat")
                continue

            # Validate tick
            validated = validate_tick(raw_tick, logger)
            if validated is None:
                continue

            # Enrich with derived fields
            enriched = enrich_tick(validated)

            # Record metrics
            metrics.record_tick(enriched.instrument)
            metrics.maybe_report(logger)

            # Publish tick
            await publisher.publish_tick(enriched)

            # Update aggregator
            await aggregator.process(enriched)

    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}")
        raise
    finally:
        # Graceful shutdown
        logger.info("Flushing remaining candles...")
        await aggregator.flush_all()
        await publisher.disconnect()
        logger.info("Shutdown complete")


def run() -> None:
    """Entry point for the application."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
