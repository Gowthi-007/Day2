import logging

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from redis import Redis, RedisError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from config import settings
from database import init_db, get_db, PaymentEvent
from payment import StripePaymentEvent

logger = logging.getLogger(settings.APP_NAME)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI(title=settings.APP_NAME)
redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)


def mask_token(value: str) -> str:
    if len(value) <= 10:
        return "*" * len(value)
    return f"{value[:6]}...{value[-4:]}"


@app.on_event("startup")
def startup_event():
    init_db()


@app.post("/webhook")
def stripe_webhook(payload: StripePaymentEvent, db: Session = Depends(get_db)):
    event_key = f"stripe_event:{payload.event_id}"

    try:
        inserted = redis_client.set(
            event_key,
            "processed",
            ex=settings.REDIS_LOCK_TTL_SECONDS,
            nx=True,
        )
    except RedisError as exc:
        logger.error("Redis failure checking webhook token=%s error=%s", mask_token(payload.event_id), exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="infrastructure unavailable")

    if not inserted:
        logger.info("Duplicate webhook skipped token=%s type=%s", mask_token(payload.event_id), payload.type)
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "skipped", "reason": "duplicate"})

    try:
        existing_event = db.query(PaymentEvent).filter(PaymentEvent.event_id == payload.event_id).first()
        if existing_event:
            logger.info("Duplicate webhook detected in DB token=%s", mask_token(payload.event_id))
            return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "skipped", "reason": "duplicate"})

        payment_event = PaymentEvent(
            event_id=payload.event_id,
            type=payload.type,
            amount=payload.amount,
            currency=payload.currency,
        )
        db.add(payment_event)
        db.commit()
        db.refresh(payment_event)

    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Database failure for webhook token=%s error=%s", mask_token(payload.event_id), exc)
        try:
            redis_client.delete(event_key)
        except RedisError:
            logger.warning("Failed to remove Redis token after DB failure token=%s", mask_token(payload.event_id))
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="infrastructure unavailable")

    logger.info("Webhook processed token=%s type=%s", mask_token(payload.event_id), payload.type)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"status": "processed"})
