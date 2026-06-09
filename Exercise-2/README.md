# Third-Party AI API Gateway with Rate-Limiting and Fallbacks

A FastAPI-based gateway that manages requests to third-party LLM providers with intelligent caching, rate-limiting, circuit breaker pattern, and automatic fallback to backup providers.

## Features

- **Redis-Based Caching**: Prompt hash caching with 1-hour TTL reduces API calls and costs
- **Sliding Window Rate Limiting**: Per-service-id token limits to prevent overuse
- **Circuit Breaker Pattern**: Automatically switches to fallback provider after 5 consecutive failures; recovers after 60 seconds
- **Timeout Protection**: 5-second timeout on all AI provider calls (fail-fast strategy)
- **PII Redaction**: Masks emails, credit card numbers, SSNs, and names before logging
- **Graceful Degradation**: If Redis unavailable, bypasses cache/rate-limiting but continues serving requests
- **Async Operations**: Full async/await support for high throughput

## Files

- `main.py` - FastAPI application with `/summarize` endpoint
- `config.py` - Configuration for API endpoints, timeouts, and circuit breaker settings
- `schemas.py` - Pydantic request/response models
- `pii_redaction.py` - PII masking utilities (emails, CCs, SSNs, names)
- `redis_utils.py` - Cache keys, rate limiting, circuit breaker state management
- `requirements.txt` - Python dependencies

## Running Locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Ensure Redis is running:
   ```bash
   redis-server
   ```

3. Start the FastAPI app:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

## API Endpoints

### POST /summarize
Summarize text using AI with caching, rate-limiting, and automatic fallback.

**Request Body**:
```json
{
  "service_id": "analytics_dash_01",
  "prompt_text": "Summarize the quarterly financial report for Q1.",
  "max_tokens": 150
}
```

**Cache Hit Response (HTTP 200)**:
```json
{
  "source": "cache",
  "summary_text": "Q1 performance showed a 12% increase in recurring revenue..."
}
```

**Primary Provider Response (HTTP 200)**:
```json
{
  "source": "primary_provider",
  "summary_text": "Q1 performance showed a 12% increase in recurring revenue..."
}
```

**Fallback Provider Response (HTTP 200)**:
```json
{
  "source": "fallback_provider",
  "summary_text": "Q1 performance showed a 12% increase in recurring revenue..."
}
```

**Rate Limit Exceeded (HTTP 429)**:
```json
{
  "detail": "Rate limit exceeded"
}
```

**Service Unavailable (HTTP 503)**:
```json
{
  "detail": "Summarization service temporarily unavailable"
}
```

### GET /circuit-breaker-state
Monitor circuit breaker state for both providers.

**Response**:
```json
{
  "primary": {
    "provider": "primary",
    "failure_count": 0,
    "is_open": false
  },
  "backup": {
    "provider": "backup",
    "failure_count": 0,
    "is_open": false
  }
}
```

## Architecture

1. **Request Validation**: Pydantic validates input
2. **Rate Limiting**: Check Redis for token consumption
3. **Cache Lookup**: Hash prompt and check Redis cache
4. **Primary Provider**: Call primary AI if circuit breaker open
5. **Fallback**: If primary fails, route to backup automatically
6. **Circuit Breaker**: After 5 failures, stop calling primary for 60 seconds
7. **Response Caching**: Cache successful responses for 1 hour

## Configuration

Edit `config.py` to customize:
- `PRIMARY_AI_PROVIDER_URL` - Primary LLM endpoint
- `BACKUP_AI_PROVIDER_URL` - Backup LLM endpoint
- `RATE_LIMIT_TOKENS_PER_MINUTE` - Token limit per service
- `CACHE_TTL_SECONDS` - Cache expiration time (default: 3600s = 1 hour)
- `AI_CALL_TIMEOUT_SECONDS` - Timeout for AI calls (default: 5s)
- `CIRCUIT_BREAKER_FAILURE_THRESHOLD` - Failures before opening circuit (default: 5)
- `CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS` - Time before recovery attempt (default: 60s)

## PII Handling

The `pii_redaction.py` module masks:
- Email addresses → `[EMAIL_MASKED]`
- Credit card numbers → `[CC_MASKED]`
- Social security numbers → `[SSN_MASKED]`
- Full names → `[NAME_MASKED]`

All PII is redacted before logging.
