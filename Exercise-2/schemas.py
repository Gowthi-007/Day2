from pydantic import BaseModel, conint, constr
from typing import Optional


class SummarizationRequest(BaseModel):
    service_id: constr(strip_whitespace=True, min_length=1)
    prompt_text: constr(strip_whitespace=True, min_length=1)
    max_tokens: conint(gt=0, le=4096)


class SummarizationResponse(BaseModel):
    source: str  # "cache", "primary_provider", or "fallback_provider"
    summary_text: str
