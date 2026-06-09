from pydantic import BaseModel, conint, constr
from typing import Optional
from datetime import datetime


class ReservationRequest(BaseModel):
    user_id: constr(strip_whitespace=True, min_length=1)
    item_id: constr(strip_whitespace=True, min_length=1)
    quantity: conint(gt=0)  # Greater than zero


class ReservationResponse(BaseModel):
    status: str
    reservation_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    reason: Optional[str] = None
