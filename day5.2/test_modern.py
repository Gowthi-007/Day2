# test_modern.py
from fastapi.testclient import TestClient
from modern_service import app

client = TestClient(app)

def test_banking_accrual_parity():
    response = client.post("/v1/accrual", json={
        "balance": "12000.00",
        "account_type": "SAVINGS"
    })
    assert response.status_code == 200
    # The interest calculations are exact and bounded perfectly
    assert response.json() == {"final_balance": "12001.07"}