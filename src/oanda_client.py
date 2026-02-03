"""OANDA v20 streaming client with automatic reconnection."""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from .config import Config
from .metrics import Metrics


class OandaClient:
    """Async OANDA streaming client with reconnection logic."""

    def __init__(
        self,
        config: Config,
        metrics: Metrics,
        logger: logging.Logger,
    ) -> None:
        self.config = config
        self.metrics = metrics
        self.logger = logger
        self._backoff_seconds = 1.0
        self._max_backoff = 30.0

    def _reset_backoff(self) -> None:
        """Reset backoff to initial value after successful connection."""
        self._backoff_seconds = 1.0

    async def _do_backoff(self) -> None:
        """Exponential backoff between reconnection attempts."""
        self.logger.info(
            f"Waiting {self._backoff_seconds}s before reconnecting",
            extra={"backoff_seconds": self._backoff_seconds},
        )
        await asyncio.sleep(self._backoff_seconds)
        self._backoff_seconds = min(self._backoff_seconds * 2, self._max_backoff)

    async def stream(self) -> AsyncGenerator[dict[str, Any], None]:
        """
        Stream tick data from OANDA with automatic reconnection.

        Yields:
            Raw tick dictionaries (including heartbeats).
        """
        instruments = ",".join(self.config.instruments)
        url = self.config.oanda_stream_url
        params = {"instruments": instruments}
        headers = {
            "Authorization": f"Bearer {self.config.oanda_api_key}",
            "Content-Type": "application/json",
        }

        while True:
            try:
                self.logger.info(
                    "Connecting to OANDA stream",
                    extra={
                        "url": url,
                        "instruments": self.config.instruments,
                    },
                )

                async with httpx.AsyncClient(timeout=None) as client:
                    async with client.stream(
                        "GET",
                        url,
                        params=params,
                        headers=headers,
                    ) as response:
                        if response.status_code != 200:
                            error_body = await response.aread()
                            self.metrics.record_disconnect(
                                f"HTTP {response.status_code}: {error_body.decode()}",
                                self.logger,
                            )
                            await self._do_backoff()
                            continue

                        self._reset_backoff()
                        self.logger.info("Connected to OANDA stream")

                        async for line in response.aiter_lines():
                            if line.strip():
                                try:
                                    data = json.loads(line)
                                    yield data
                                except json.JSONDecodeError as e:
                                    self.logger.warning(
                                        f"Invalid JSON: {e}",
                                        extra={"raw_line": line[:200]},
                                    )

            except httpx.ReadTimeout:
                self.metrics.record_disconnect(
                    "Read timeout (no heartbeat)", self.logger
                )
                self.metrics.record_reconnect(self.logger)

            except httpx.ConnectError as e:
                self.metrics.record_disconnect(f"Connection error: {e}", self.logger)
                self.metrics.record_reconnect(self.logger)
                await self._do_backoff()

            except httpx.HTTPStatusError as e:
                self.metrics.record_disconnect(f"HTTP error: {e}", self.logger)
                self.metrics.record_reconnect(self.logger)
                await self._do_backoff()

            except Exception as e:
                self.metrics.record_disconnect(f"Unexpected error: {e}", self.logger)
                self.metrics.record_reconnect(self.logger)
                await self._do_backoff()
