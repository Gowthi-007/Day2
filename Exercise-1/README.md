# High-Throughput Inventory Reservation System

A FastAPI-based inventory reservation system designed for flash sale scenarios with concurrent user access.

## Features

- **Distributed Locking**: Redis-based distributed lock with token validation to prevent race conditions
- **Pessimistic Locking**: SQLAlchemy `with_for_update()` for atomic stock deduction
- **Connection Pooling**: Optimized pool sizing for Redis and database
- **Automatic Expiration**: Reservations expire after 15 minutes
- **Graceful Degradation**: 2-second timeout on lock acquisition with user-friendly errors
- **Masked Logging**: Sensitive data (user IDs, item IDs) are masked in logs

## Files

- `main.py` - FastAPI application with `/reserve` endpoint
- `config.py` - Configuration with pooling and timeout settings
- `database.py` - SQLAlchemy ORM models (Inventory, Reservation) with connection pooling
- `schemas.py` - Pydantic request/response schemas
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

### POST /reserve
Reserve an item with the given quantity.

**Request Body**:
```json
{
  "user_id": "usr_998877",
  "item_id": "item_prod_5544",
  "quantity": 2
}
```

**Success Response (HTTP 201)**:
```json
{
  "status": "reserved",
  "reservation_id": "res_abc123xyz456",
  "expires_at": "2026-06-09T11:00:00Z"
}
```

**Failure Response (HTTP 409)**:
```json
{
  "status": "failed",
  "reason": "item_out_of_stock"
}
```

## Concurrency Guarantees

1. **Distributed Lock**: Each item gets a unique Redis lock token
2. **Pessimistic DB Lock**: The inventory row is locked with `with_for_update()` during transaction
3. **Atomic Operations**: Stock deduction and reservation creation are in a single transaction
4. **No Overselling**: Inventory never goes below zero even under extreme concurrent load

## Performance Considerations

- Database connection pool: 20 connections with max 40 overflow
- Redis socket timeout: 5 seconds
- Lock acquisition timeout: 2 seconds (fail-fast on contention)
- Reservation TTL: 15 minutes (configurable)
