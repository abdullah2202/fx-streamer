"""Redis pub/sub publisher."""

import json
import logging
from typing import TYPE_CHECKING

import redis.asyncio as redis

if TYPE_CHECKING:
    from .aggregator import Candle

from .config import Config
from .enricher import EnrichedTick


class RedisPublisher:
    """Async Redis publisher for ticks and candles."""

    def __init__(self, config: Config, logger: logging.Logger) -> None:
        self.config = config
        self.logger = logger
        self._client: redis.Redis | None = None

    async def connect(self) -> None:
        """Connect to Redis."""
        self._client = redis.Redis(
            host=self.config.redis_host,
            port=self.config.redis_port,
            password=self.config.redis_password or None,
            decode_responses=True,
        )
        # Test connection
        await self._client.ping()
        self.logger.info(
            "Connected to Redis",
            extra={
                "host": self.config.redis_host,
                "port": self.config.redis_port,
            },
        )

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._client:
            await self._client.aclose()
            self._client = None
            self.logger.info("Disconnected from Redis")

    def _serialize(self, data: dict) -> str:
        """
        Serialize data to JSON.

        This is the serialization point - can be swapped to MsgPack/Protobuf later.
        """
        return json.dumps(data)

    async def publish_tick(self, tick: EnrichedTick) -> None:
        """Publish enriched tick to Redis channel."""
        if not self._client:
            self.logger.warning("Redis not connected, skipping tick publish")
            return

        channel = f"fx:tick:{tick.instrument}"
        message = self._serialize(tick.to_dict())

        try:
            await self._client.publish(channel, message)
        except redis.RedisError as e:
            self.logger.error(f"Failed to publish tick: {e}")

    async def publish_candle(self, candle: "Candle") -> None:
        """Publish completed candle to Redis channel."""
        if not self._client:
            self.logger.warning("Redis not connected, skipping candle publish")
            return

        channel = f"fx:candle:{candle.period_seconds}s:{candle.instrument}"
        message = self._serialize(candle.to_dict())

        try:
            await self._client.publish(channel, message)
        except redis.RedisError as e:
            self.logger.error(f"Failed to publish candle: {e}")
