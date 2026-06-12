from pydantic import BaseModel, Field
from uuid import UUID
from typing import Literal

class VitalsPayload(BaseModel):
    patient_id: UUID
    heart_rate: float #int = Field(..., ge=30, le=250)
    status: Literal["NORMAL", "ELEVATED", "CRITICAL"]