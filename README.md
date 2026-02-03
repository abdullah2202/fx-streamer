# FX Streamer

OANDA v20 streaming bot with Redis pub/sub for tick distribution.

## Features

- **Real-time streaming** from OANDA v20 API
- **Automatic reconnection** with exponential backoff
- **Tick validation** and normalization
- **Derived fields**: mid price, spread, spread in pips
- **OHLC aggregation**: configurable periods (1s, 5s, etc.)
- **Redis pub/sub**: scalable tick distribution
- **Docker-ready**: non-root user, environment-only config

## Quick Start

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Required:
- `OANDA_API_KEY` - Your OANDA API key
- `OANDA_ACCOUNT_ID` - Your OANDA account ID

Optional:
- `OANDA_ENVIRONMENT` - `practice` (default) or `live`
- `OANDA_INSTRUMENTS` - Comma-separated list (default: `EUR_USD`)
- `REDIS_HOST` - Redis host (default: `localhost`)
- `AGGREGATION_PERIODS` - Candle periods (default: `1s,5s`)

### Run with Docker Compose

```bash
# Set environment variables
export OANDA_API_KEY=your-api-key
export OANDA_ACCOUNT_ID=your-account-id
export OANDA_ENVIRONMENT=practice
export OANDA_INSTRUMENTS=EUR_USD,GBP_USD

# Start services
docker-compose up -d

# View logs
docker-compose logs -f streamer

# Subscribe to ticks
docker-compose exec redis redis-cli SUBSCRIBE fx:tick:EUR_USD

# Subscribe to candles
docker-compose exec redis redis-cli SUBSCRIBE fx:candle:1s:EUR_USD
```

### Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run
python -m src.main
```

## Redis Channels

### Ticks
Channel: `fx:tick:{instrument}`

Example message:
```json
{
  "instrument": "EUR_USD",
  "time": "2024-01-15T10:30:00.123456789Z",
  "timestamp_unix": 1705315800.123,
  "bid": "1.08523",
  "ask": "1.08525",
  "bid_liquidity": 1000000,
  "ask_liquidity": 1000000,
  "tradeable": true,
  "mid": "1.08524",
  "spread": "0.00002",
  "spread_pips": 0.2
}
```

### Candles
Channel: `fx:candle:{period}:{instrument}`

Example message:
```json
{
  "instrument": "EUR_USD",
  "period": "1s",
  "period_start": 1705315800.0,
  "open": "1.08524",
  "high": "1.08526",
  "low": "1.08522",
  "close": "1.08525",
  "tick_count": 5
}
```

## Architecture

```
OANDA API → OandaClient → Validator → Enricher → Publisher → Redis
                                          ↓
                                     Aggregator → Publisher → Redis
```

## License

MIT
