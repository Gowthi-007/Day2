from fastapi.testclient import TestClient
from main import app
from uuid import uuid4

client = TestClient(app)

def test_contract_compliance_success():
    response = client.post("/v1/vitals", json={
        "patient_id": str(uuid4()),
        "heart_rate": 72,
        "status": "NORMAL"
    })
    assert response.status_code == 201

def test_out_of_bounds_rejection():
    response = client.post("/v1/vitals", json={
        "patient_id": str(uuid4()),
        "heart_rate": 12,  # Violates the 30 BPM lower bound
        "status": "NORMAL"
    })
    assert response.status_code == 422  # Handled automatically at the gateway