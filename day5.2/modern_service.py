# modern_service.py
from fastapi import FastAPI, status
from pydantic import BaseModel, Field
from decimal import Decimal, ROUND_HALF_UP

app = FastAPI()

class AccountRequest(BaseModel):
    balance: str = Field(..., description="String passing prevents initial float errors")
    account_type: str

@app.post("/v1/accrual", status_code=status.HTTP_200_OK)
async def calculate_accrual(payload: AccountRequest):
    balance_dec = Decimal(payload.balance)
    
    if payload.account_type == "SAVINGS" and balance_dec > Decimal("10000"):
        daily_rate = Decimal("0.0325") / Decimal("365")
        interest = balance_dec * daily_rate
        # Force strict 2-decimal point banking standards
        final_balance = balance_dec + interest.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return {"final_balance": str(final_balance)}
        
    return {"final_balance": str(balance_dec)}