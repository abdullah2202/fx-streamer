"""Configuration loaded from environment variables."""

from pydantic import Field
from pydantic_settings import BaseSettings


class Config(BaseSettings):  # type: ignore[misc]
    """Application configuration from environment variables."""

    # OANDA
    oanda_api_key: str = Field(..., description="OANDA API key")
    oanda_account_id: str = Field(..., description="OANDA account ID")
    oanda_environment: str = Field(
        default="practice", description="OANDA environment: practice or live"
    )
    oanda_instruments: str = Field(
        default="XAU_USD", description="Comma-separated instrument list"
    )

    # Redis
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_password: str | None = Field(default=None)

    # Aggregation
    aggregation_periods: str = Field(
        default="1s,5s", description="Comma-separated aggregation periods"
    )

    # Logging
    log_level: str = Field(default="INFO")

    @property
    def instruments(self) -> list[str]:
        """Parse comma-separated instruments into list."""
        return [i.strip() for i in self.oanda_instruments.split(",") if i.strip()]

    @property
    def periods(self) -> list[int]:
        """Parse aggregation periods into seconds."""
        result = []
        for p in self.aggregation_periods.split(","):
            p = p.strip().lower()
            if p.endswith("s"):
                result.append(int(p[:-1]))
            elif p.endswith("m"):
                result.append(int(p[:-1]) * 60)
            else:
                result.append(int(p))
        return result

    @property
    def oanda_stream_url(self) -> str:
        """Build OANDA streaming URL based on environment."""
        host = (
            "stream-fxpractice.oanda.com"
            if self.oanda_environment == "practice"
            else "stream-fxtrade.oanda.com"
        )
        return f"https://{host}/v3/accounts/{self.oanda_account_id}/pricing/stream"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
