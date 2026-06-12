from fastapi.testclient import TestClient

from day5.main import app

client = TestClient(app)


VALID_PAYLOAD = {
    "vehicle_id": "TRUCK-1234",
    "speed": 72.5,
    "status": "ACTIVE",
}


def test_ingest_telemetry_happy_path():
    response = client.post("/v1/telemetry", json=VALID_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["status_code"] == 201
    assert body["payload_data"] == VALID_PAYLOAD
    assert "execution_timestamp" in body


def test_ingest_telemetry_invalid_vehicle_id():
    payload = {**VALID_PAYLOAD, "vehicle_id": "TRUCK-12A4"}
    response = client.post("/v1/telemetry", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"]


def test_ingest_telemetry_speed_below_minimum():
    payload = {**VALID_PAYLOAD, "speed": -5}
    response = client.post("/v1/telemetry", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"]


def test_ingest_telemetry_speed_above_maximum():
    payload = {**VALID_PAYLOAD, "speed": 200}
    response = client.post("/v1/telemetry", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"]


def test_ingest_telemetry_invalid_status():
    payload = {**VALID_PAYLOAD, "status": "BROKEN"}
    response = client.post("/v1/telemetry", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"]


def test_ingest_telemetry_missing_required_field():
    payload = {"vehicle_id": "TRUCK-1234", "speed": 50}
    response = client.post("/v1/telemetry", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"]
