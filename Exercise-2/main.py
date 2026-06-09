import logging
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional

import httpx
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from redis import Redis, RedisError
from sqlalchemy.exc import SQLAlchemyError

from config import settings
from schemas import SummarizationRequest, SummarizationResponse
from pii_redaction import redact_pii
from redis_utils import (
    hash_prompt,
    generate_cache_key,
    generate_rate_limit_key,
    CircuitBreakerState,
)

logger = logging.getLogger(settings.APP_NAME)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI(title=settings.APP_NAME)

# Initialize Redis client
redis_client = Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
    socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
)

# Circuit breaker state
circuit_breaker = CircuitBreakerState(
    failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    recovery_timeout=settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS,
)

# HTTP client for calling AI providers
http_client = httpx.AsyncClient(timeout=settings.AI_CALL_TIMEOUT_SECONDS)


def mask_service_id(value: str) -> str:
    """Mask service ID for logging."""
    if len(value) <= 6:
        return "*" * len(value)
    return f"{value[:3]}...{value[-3:]}"


async def check_rate_limit(service_id: str, tokens_requested: int) -> bool:
    """Check if service has exceeded rate limit."""
    try:
        rate_limit_key = generate_rate_limit_key(service_id)
        current_tokens = redis_client.get(rate_limit_key)
        current_tokens = int(current_tokens) if current_tokens else 0
        
        if current_tokens + tokens_requested > settings.RATE_LIMIT_TOKENS_PER_MINUTE:
            return False
        
        # Increment token count with 60-second expiration
        redis_client.incr(rate_limit_key, tokens_requested)
        redis_client.expire(rate_limit_key, 60)
        return True
    except RedisError as exc:
        logger.error("Redis rate limit check failed service=%s error=%s", mask_service_id(service_id), exc)
        # Graceful degradation: allow request if Redis is down
        return True


async def get_cached_response(prompt_text: str) -> Optional[str]:
    """Retrieve cached AI response if available."""
    try:
        cache_key = generate_cache_key(prompt_text)
        cached = redis_client.get(cache_key)
        if cached:
            logger.info("Cache hit for prompt hash=%s", hash_prompt(prompt_text)[:8])
            return cached
        return None
    except RedisError as exc:
        logger.warning("Redis cache lookup failed error=%s", exc)
        # Graceful degradation: continue without cache
        return None


async def cache_response(prompt_text: str, response_text: str, ttl_seconds: int) -> None:
    """Cache AI response in Redis."""
    try:
        cache_key = generate_cache_key(prompt_text)
        redis_client.setex(cache_key, ttl_seconds, response_text)
    except RedisError as exc:
        logger.warning("Redis cache write failed error=%s", exc)


async def call_ai_provider(prompt_text: str, max_tokens: int, provider: str) -> Optional[str]:
    """Call AI provider with timeout and error handling."""
    if provider == "primary":
        url = settings.PRIMARY_AI_PROVIDER_URL
        api_key = settings.PRIMARY_AI_API_KEY
    else:
        url = settings.BACKUP_AI_PROVIDER_URL
        api_key = settings.BACKUP_AI_API_KEY
    
    try:
        response = await http_client.post(
            url,
            json={
                "prompt": prompt_text,
                "max_tokens": max_tokens,
            },
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=settings.AI_CALL_TIMEOUT_SECONDS,
        )
        
        if response.status_code >= 500:
            logger.error("AI provider %s returned 5xx status=%d", provider, response.status_code)
            circuit_breaker.record_failure(provider)
            return None
        
        if response.status_code >= 400:
            logger.error("AI provider %s returned 4xx status=%d", provider, response.status_code)
            return None
        
        # Success
        circuit_breaker.record_success(provider)
        data = response.json()
        # Extract summary from provider response (assumes 'summary' or 'text' field)
        summary = data.get("summary") or data.get("text") or data.get("content", "")
        return summary
    
    except asyncio.TimeoutError:
        logger.error("AI provider %s timeout after %s seconds", provider, settings.AI_CALL_TIMEOUT_SECONDS)
        circuit_breaker.record_failure(provider)
        return None
    except httpx.HTTPError as exc:
        logger.error("AI provider %s HTTP error=%s", provider, exc)
        circuit_breaker.record_failure(provider)
        return None


@app.on_event("startup")
async def startup_event():
    logger.info("AI Gateway startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    await http_client.aclose()


@app.post("/summarize", response_model=SummarizationResponse)
async def summarize(payload: SummarizationRequest):
    """
    Summarize text using AI with caching, rate-limiting, and fallback.
    """
    service_id_masked = mask_service_id(payload.service_id)
    prompt_redacted = redact_pii(payload.prompt_text)
    
    logger.info("Summarization request service=%s tokens=%d", service_id_masked, payload.max_tokens)

    # 1. Check rate limit
    rate_limit_ok = await check_rate_limit(payload.service_id, payload.max_tokens)
    if not rate_limit_ok:
        logger.warning("Rate limit exceeded service=%s", service_id_masked)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )

    # 2. Check cache
    cached_response = await get_cached_response(payload.prompt_text)
    if cached_response:
        return SummarizationResponse(source="cache", summary_text=cached_response)

    # 3. Try primary provider if circuit is not open
    summary_text = None
    if not circuit_breaker.is_open("primary"):
        summary_text = await call_ai_provider(payload.prompt_text, payload.max_tokens, "primary")
        if summary_text:
            await cache_response(payload.prompt_text, summary_text, settings.CACHE_TTL_SECONDS)
            return SummarizationResponse(source="primary_provider", summary_text=summary_text)
    else:
        logger.warning("Circuit breaker open for primary provider state=%s", circuit_breaker.get_state("primary"))

    # 4. Fallback to backup provider
    logger.info("Attempting fallback provider service=%s", service_id_masked)
    summary_text = await call_ai_provider(payload.prompt_text, payload.max_tokens, "backup")
    if summary_text:
        await cache_response(payload.prompt_text, summary_text, settings.CACHE_TTL_SECONDS)
        return SummarizationResponse(source="fallback_provider", summary_text=summary_text)

    # 5. Both providers failed
    logger.error("Both primary and fallback providers failed service=%s", service_id_masked)
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Summarization service temporarily unavailable",
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/circuit-breaker-state")
async def get_circuit_breaker_state():
    """Get circuit breaker state for monitoring."""
    return {
        "primary": circuit_breaker.get_state("primary"),
        "backup": circuit_breaker.get_state("backup"),
    }
