"""Tick data validation and normalization."""

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any


@dataclass
class ValidatedTick:
    """Validated and normalized tick data."""

    instrument: str
    time: str  # ISO 8601
    timestamp_unix: float
    best_bid: Decimal
    best_ask: Decimal
    bid_liquidity: int
    ask_liquidity: int
    tradeable: bool
    raw: dict[str, Any]


def is_heartbeat(data: dict[str, Any]) -> bool:
    """Check if the message is a heartbeat."""
    return data.get("type") == "HEARTBEAT"


def validate_tick(data: dict[str, Any], logger: logging.Logger) -> ValidatedTick | None:
    """
    Validate and normalize raw OANDA tick data.

    Returns:
        ValidatedTick if valid, None if validation fails.
    """
    # Skip heartbeats
    if is_heartbeat(data):
        return None

    # Must be a PRICE type
    if data.get("type") != "PRICE":
        return None

    # Required fields
    required = ["instrument", "time", "bids", "asks"]
    for field in required:
        if field not in data:
            logger.warning(f"Missing required field: {field}", extra={"data": data})
            return None

    # Validate bids and asks arrays
    bids = data.get("bids", [])
    asks = data.get("asks", [])

    if not bids or not asks:
        logger.warning("Empty bids or asks array", extra={"data": data})
        return None

    # Extract best bid/ask (first in array)
    try:
        best_bid = Decimal(bids[0]["price"])
        best_ask = Decimal(asks[0]["price"])
        bid_liquidity = int(bids[0].get("liquidity", 0))
        ask_liquidity = int(asks[0].get("liquidity", 0))
    except (KeyError, InvalidOperation, IndexError) as e:
        logger.warning(f"Invalid price data: {e}", extra={"data": data})
        return None

    # Validate prices are positive
    if best_bid <= 0 or best_ask <= 0:
        logger.warning("Non-positive price", extra={"bid": best_bid, "ask": best_ask})
        return None

    # Validate bid < ask (normal market condition)
    if best_bid >= best_ask:
        logger.warning("Bid >= Ask (crossed market)", extra={"bid": best_bid, "ask": best_ask})
        return None

    # Parse timestamp
    time_str = data["time"]
    try:
        # OANDA format: 2024-01-15T10:30:00.123456789Z
        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        timestamp_unix = dt.timestamp()
    except ValueError as e:
        logger.warning(f"Invalid timestamp: {e}", extra={"time": time_str})
        return None

    return ValidatedTick(
        instrument=data["instrument"],
        time=time_str,
        timestamp_unix=timestamp_unix,
        best_bid=best_bid,
        best_ask=best_ask,
        bid_liquidity=bid_liquidity,
        ask_liquidity=ask_liquidity,
        tradeable=data.get("tradeable", True),
        raw=data,
    )
