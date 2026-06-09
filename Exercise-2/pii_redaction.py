import re
from typing import Optional


def mask_email(text: str) -> str:
    """Replace email addresses with masked version."""
    return re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_MASKED]', text)


def mask_credit_card(text: str) -> str:
    """Replace credit card numbers with masked version."""
    return re.sub(r'\b(?:\d{4}[-\s]?){3}\d{4}\b', '[CC_MASKED]', text)


def mask_names(text: str) -> str:
    """Mask potential names (basic implementation)."""
    # This is a simple heuristic; in production, use NER (Named Entity Recognition)
    return re.sub(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', '[NAME_MASKED]', text)


def mask_ssn(text: str) -> str:
    """Replace SSN patterns with masked version."""
    return re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_MASKED]', text)


def redact_pii(text: str) -> str:
    """Apply all PII redaction rules."""
    text = mask_email(text)
    text = mask_credit_card(text)
    text = mask_ssn(text)
    text = mask_names(text)
    return text
