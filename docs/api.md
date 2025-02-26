# Trading System API Documentation

## API Overview

The trading system provides a RESTful API for monitoring and controlling the trading system. All endpoints return JSON responses and accept JSON request bodies where applicable.

## Authentication

### API Key Authentication

All requests must include an API key in the header:

```
Authorization: Bearer your-api-key-here
```

Example:
```bash
curl -H "Authorization: Bearer your-api-key-here" https://api.example.com/v1/status
```

### Rate Limiting

- 100 requests per minute per API key
- 1000 requests per hour per API key
- Rates are tracked by IP address and API key

## Endpoints

### System Status

#### GET /api/v1/status
Get current system status

**Response:**
```json
{
    "status": "running",
    "mode": "live",
    "active_strategies": 2,
    "total_positions": 3,
    "last_update": "2024-02-21T10:15:30Z"
}
```

### Trading Operations

#### GET /api/v1/positions
Get current positions

**Response:**
```json
{
    "positions": [
        {
            "symbol": "RELIANCE",
            "quantity": 100,
            "entry_price": 2450.75,
            "current_price": 2455.90,
            "pnl": 515.00,
            "entry_time": "2024-02-21T09:30:00Z",
            "strategy": "GANN_15M"
        }
    ]
}
```

#### POST /api/v1/trade
Place new trade

**Request:**
```json
{
    "symbol": "SBIN",
    "quantity": 100,
    "order_type": "MARKET",
    "side": "BUY",
    "product_type": "INTRADAY",
    "price": 650.25,              // Optional, for LIMIT orders
    "trigger_price": 649.50,      // Optional, for SL orders
    "strategy_id": "GANN_15M"     // Optional
}
```

**Response:**
```json
{
    "order_id": "12345678",
    "status": "success",
    "message": "Order placed successfully",
    "timestamp": "2024-02-21T10:15:30Z",
    "details": {
        "symbol": "SBIN",
        "quantity": 100,
        "executed_price": 650.30,
        "order_type": "MARKET",
        "side": "BUY"
    }
}
```

#### PUT /api/v1/trade/{order_id}
Modify existing order

**Request:**
```json
{
    "quantity": 150,              // New quantity
    "price": 651.25,              // New price
    "trigger_price": 650.50       // New trigger price
}
```

**Response:**
```json
{
    "order_id": "12345678",
    "status": "success",
    "message": "Order modified successfully",
    "timestamp": "2024-02-21T10:16:30Z"
}
```

#### DELETE /api/v1/trade/{order_id}
Cancel order

**Response:**
```json
{
    "order_id": "12345678",
    "status": "success",
    "message": "Order cancelled successfully",
    "timestamp": "2024-02-21T10:17:30Z"
}
```

### Strategy Management

#### GET /api/v1/strategies
Get all available strategies

**Response:**
```json
{
    "strategies": [
        {
            "id": "GANN_15M",
            "name": "Gann Square 15min",
            "status": "active",
            "symbols": ["SBIN", "RELIANCE", "INFY"],
            "pnl": 1250.75,
            "active_positions": 2
        }
    ]
}
```

#### POST /api/v1/strategies
Add new strategy

**Request:**
```json
{
    "name": "GANN_5M",
    "type": "gann_square",
    "symbols": ["SBIN", "RELIANCE"],
    "parameters": {
        "timeframe": "5min",
        "gann_increments": [0.125, 0.25, 0.5, 0.75, 1.0],
        "buffer_percentage": 0.002
    }
}
```

**Response:**
```json
{
    "strategy_id": "GANN_5M",
    "status": "created",
    "message": "Strategy created successfully"
}
```

### Performance Metrics

#### GET /api/v1/metrics
Get performance metrics

**Parameters:**
- `start_date`: Start date (YYYY-MM-DD)
- `end_date`: End date (YYYY-MM-DD)
- `strategy_id`: Optional strategy filter

**Response:**
```json
{
    "metrics": {
        "total_trades": 156,
        "win_rate": 0.65,
        "profit_factor": 1.85,
        "sharpe_ratio": 1.92,
        "max_drawdown": 0.045,
        "daily_pnl": [
            {
                "date": "2024-02-21",
                "pnl": 1250.75
            }
        ]
    }
}
```

### Risk Management

#### GET /api/v1/risk/limits
Get current risk limits and usage

**Response:**
```json
{
    "risk_limits": {
        "max_positions": 5,
        "current_positions": 2,
        "max_capital": 100000,
        "used_capital": 45000,
        "daily_loss_limit": 3000,
        "current_loss": 500
    }
}
```

#### POST /api/v1/risk/update
Update risk parameters

**Request:**
```json
{
    "max_positions": 6,
    "max_capital": 120000,
    "daily_loss_limit": 3500
}
```

**Response:**
```json
{
    "status": "success",
    "message": "Risk parameters updated successfully"
}
```

### Historical Data

#### GET /api/v1/data/{symbol}
Get historical data

**Parameters:**
- `interval`: Candle interval (1m, 5m, 15m, etc.)
- `start`: Start timestamp
- `end`: End timestamp
- `limit`: Maximum number of candles

**Response:**
```json
{
    "symbol": "SBIN",
    "interval": "15m",
    "data": [
        {
            "timestamp": "2024-02-21T09:15:00Z",
            "open": 650.25,
            "high": 652.30,
            "low": 649.80,
            "close": 651.75,
            "volume": 125000
        }
    ]
}
```

## Error Handling

### Error Response Format
```json
{
    "status": "error",
    "code": "ERROR_CODE",
    "message": "Error description",
    "timestamp": "2024-02-21T10:15:30Z"
}
```

### Common Error Codes
- `AUTH_ERROR`: Authentication failed
- `INVALID_REQUEST`: Invalid request parameters
- `ORDER_FAILED`: Order placement failed
- `POSITION_LIMIT`: Position limit exceeded
- `SYSTEM_ERROR`: Internal system error

## Pagination

For endpoints returning lists, pagination is supported using:
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 100, max: 1000)

Example:
```bash
GET /api/v1/trades?page=2&limit=50
```

Response includes pagination metadata:
```json
{
    "data": [...],
    "pagination": {
        "current_page": 2,
        "total_pages": 10,
        "total_items": 486,
        "items_per_page": 50
    }
}
```

## WebSocket API

### Connection
```javascript
const ws = new WebSocket('wss://api.example.com/ws');
ws.onopen = () => {
    ws.send(JSON.stringify({
        type: 'auth',
        api_key: 'your-api-key'
    }));
};
```

### Subscriptions

Subscribe to real-time data:
```json
{
    "type": "subscribe",
    "channels": ["trades", "positions"],
    "symbols": ["SBIN", "RELIANCE"]
}
```

### Message Types

1. Trade Updates:
```json
{
    "type": "trade",
    "data": {
        "order_id": "12345678",
        "status": "EXECUTED",
        "symbol": "SBIN",
        "quantity": 100,
        "price": 650.75
    }
}
```

2. Position Updates:
```json
{
    "type": "position",
    "data": {
        "symbol": "SBIN",
        "quantity": 100,
        "pnl": 525.50
    }
}
```

## Rate Limiting Headers

Each response includes rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1582286400
```

## Best Practices

1. Error Handling
   - Implement exponential backoff for retries
   - Handle rate limiting appropriately
   - Log all API errors for debugging

2. Authentication
   - Rotate API keys regularly
   - Use separate keys for different environments
   - Never share or expose API keys

3. Performance
   - Batch requests when possible
   - Use WebSocket for real-time data
   - Implement proper caching

4. Monitoring
   - Monitor API usage and errors
   - Set up alerts for critical errors
   - Track rate limit usage