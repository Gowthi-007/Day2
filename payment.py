from pydantic import BaseModel, constr


class StripePaymentEvent(BaseModel):
    event_id: constr(strip_whitespace=True, min_length=1)
    type: constr(strip_whitespace=True, min_length=1)
    amount: int
    currency: constr(strip_whitespace=True, min_length=1, max_length=10)
