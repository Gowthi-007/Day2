import hashlib
import json
from typing import Optional
from datetime import datetime


def hash_prompt(prompt_text: str) -> str:
    """Generate a SHA256 hash of the prompt for cache key."""
    return hashlib.sha256(prompt_text.encode()).hexdigest()


def generate_cache_key(prompt_text: str) -> str:
    """Generate Redis cache key from prompt hash."""
    prompt_hash = hash_prompt(prompt_text)
    return f"ai_cache:{prompt_hash}"


def generate_rate_limit_key(service_id: str) -> str:
    """Generate Redis rate limit key for sliding window."""
    return f"rate_limit:{service_id}"


def generate_circuit_breaker_key(provider: str) -> str:
    """Generate Redis circuit breaker state key."""
    return f"circuit_breaker:{provider}"


class CircuitBreakerState:
    """In-memory or Redis-backed circuit breaker state."""
    
    def __init__(self, failure_threshold: int, recovery_timeout: int):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = {}
        self.last_failure_time = {}
    
    def record_failure(self, provider: str) -> None:
        """Record a failure for the provider."""
        if provider not in self.failure_count:
            self.failure_count[provider] = 0
        self.failure_count[provider] += 1
        self.last_failure_time[provider] = datetime.utcnow()
    
    def record_success(self, provider: str) -> None:
        """Reset failure count on success."""
        self.failure_count[provider] = 0
        if provider in self.last_failure_time:
            del self.last_failure_time[provider]
    
    def is_open(self, provider: str) -> bool:
        """Check if circuit breaker is open (provider is down)."""
        if provider not in self.failure_count:
            return False
        
        # If threshold exceeded, check if recovery timeout has passed
        if self.failure_count[provider] >= self.failure_threshold:
            last_failure = self.last_failure_time.get(provider)
            if not last_failure:
                return False
            
            time_since_failure = (datetime.utcnow() - last_failure).total_seconds()
            if time_since_failure < self.recovery_timeout:
                return True  # Circuit is open, still in timeout window
            else:
                # Recovery timeout passed, reset and try again
                self.failure_count[provider] = 0
                return False
        
        return False
    
    def get_state(self, provider: str) -> dict:
        """Get current state for logging/debugging."""
        return {
            "provider": provider,
            "failure_count": self.failure_count.get(provider, 0),
            "is_open": self.is_open(provider),
        }
