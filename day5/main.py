from datetime import datetime
from enum import Enum

from fastapi import FastAPI
from pydantic import BaseModel, Field, constr, confloat


class TelemetryStatus(str, Enum):
    ACTIVE = "ACTIVE"
    IDLE = "IDLE"
    MAINTENANCE = "MAINTENANCE"


class TelemetryPayload(BaseModel):
    vehicle_id: constr(pattern=r"^TRUCK-[0-9]{4}$") = Field(
        ..., json_schema_extra={"example": "TRUCK-1234"}
    )
    speed: confloat(ge=0, le=160) = Field(
        ..., json_schema_extra={"example": 72.5}
    )
    status: TelemetryStatus = Field(
        ..., json_schema_extra={"example": "ACTIVE"}
    )
    tire_pressure: float 


app = FastAPI(title="LogiRoute Telemetry Ingestion API", version="1.0.0")


@app.post("/v1/telemetry", status_code=201)
async def ingest_telemetry(payload: TelemetryPayload):
    """Ingest vehicle IoT data and validate the telemetry payload."""
    return {
        "status_code": 201,
        "payload_data": payload.dict(),
        "execution_timestamp": datetime.utcnow().isoformat() + "Z",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("day5.main:app", host="0.0.0.0", port=8000, reload=True)
