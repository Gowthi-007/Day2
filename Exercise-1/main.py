import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from redis import Redis, RedisError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
import asyncio

from config import settings
from database import init_db, get_db, Inventory, Reservation
from schemas import ReservationRequest, ReservationResponse

logger = logging.getLogger(settings.APP_NAME)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI(title=settings.APP_NAME)

# Initialize Redis client with connection pooling
redis_client = Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
    socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
)


def mask_user_id(value: str) -> str:
    """Mask user ID for logging."""
    if len(value) <= 6:
        return "*" * len(value)
    return f"{value[:3]}...{value[-3:]}"


def mask_item_id(value: str) -> str:
    """Mask item ID for logging."""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


async def acquire_distributed_lock(item_id: str) -> Optional[str]:
    """
    Acquire a distributed lock for the item using Redis with a unique token.
    Returns the lock token if acquired, None if timeout/failure.
    """
    lock_key = f"inventory_lock:{item_id}"
    lock_token = str(uuid.uuid4())
    
    try:
        acquired = redis_client.set(
            lock_key,
            lock_token,
            ex=10,  # Lock expires after 10 seconds
            nx=True,  # Only set if not exists
        )
        return lock_token if acquired else None
    except RedisError as exc:
        logger.error("Redis lock acquisition failed item=%s error=%s", mask_item_id(item_id), exc)
        return None


async def release_distributed_lock(item_id: str, lock_token: str) -> bool:
    """Release the distributed lock."""
    lock_key = f"inventory_lock:{item_id}"
    
    try:
        # Only delete if token matches to prevent releasing someone else's lock
        current_token = redis_client.get(lock_key)
        if current_token == lock_token:
            redis_client.delete(lock_key)
            return True
        return False
    except RedisError as exc:
        logger.error("Redis lock release failed item=%s error=%s", mask_item_id(item_id), exc)
        return False


def create_reservation_id() -> str:
    """Generate a unique reservation ID."""
    return f"res_{uuid.uuid4().hex[:20]}"


@app.on_event("startup")
def startup_event():
    init_db()
    logger.info("Application startup: database initialized")


@app.post("/reserve", response_model=ReservationResponse)
async def reserve_item(payload: ReservationRequest, db: Session = Depends(get_db)):
    """
    Reserve an item with concurrent safety.
    Uses distributed lock + pessimistic database locking.
    """
    user_id_masked = mask_user_id(payload.user_id)
    item_id_masked = mask_item_id(payload.item_id)
    
    # Try to acquire distributed lock with timeout
    try:
        lock_token = await asyncio.wait_for(
            acquire_distributed_lock(payload.item_id),
            timeout=settings.LOCK_ACQUIRE_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning("Lock acquisition timeout user=%s item=%s", user_id_masked, item_id_masked)
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"status": "failed", "reason": "item_out_of_stock"},
        )

    if not lock_token:
        logger.warning("Lock acquisition failed user=%s item=%s", user_id_masked, item_id_masked)
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"status": "failed", "reason": "item_out_of_stock"},
        )

    try:
        # Use pessimistic locking (with_for_update) to ensure safe stock deduction
        inventory = (
            db.query(Inventory)
            .filter(Inventory.item_id == payload.item_id)
            .with_for_update()
            .first()
        )

        if not inventory:
            logger.warning("Item not found user=%s item=%s", user_id_masked, item_id_masked)
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={"status": "failed", "reason": "item_out_of_stock"},
            )

        if inventory.quantity_available < payload.quantity:
            logger.warning("Insufficient stock user=%s item=%s requested=%d available=%d", 
                          user_id_masked, item_id_masked, payload.quantity, inventory.quantity_available)
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={"status": "failed", "reason": "item_out_of_stock"},
            )

        # Decrement inventory and create reservation
        inventory.quantity_available -= payload.quantity
        inventory.quantity_reserved += payload.quantity

        reservation_id = create_reservation_id()
        expires_at = datetime.utcnow() + timedelta(seconds=settings.RESERVATION_TTL_SECONDS)

        reservation = Reservation(
            reservation_id=reservation_id,
            user_id=payload.user_id,
            item_id=payload.item_id,
            quantity=payload.quantity,
            expires_at=expires_at,
        )

        db.add(reservation)
        db.commit()
        db.refresh(reservation)

        logger.info("Reservation created user=%s item=%s reservation_id=%s quantity=%d",
                   user_id_masked, item_id_masked, reservation_id[:8], payload.quantity)

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": "reserved",
                "reservation_id": reservation_id,
                "expires_at": expires_at.isoformat() + "Z",
            },
        )

    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Database error during reservation user=%s item=%s error=%s",
                    user_id_masked, item_id_masked, exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "failed", "reason": "service_unavailable"},
        )

    finally:
        # Always release the lock
        await release_distributed_lock(payload.item_id, lock_token)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
