from fastapi import FastAPI, status
from models import VitalsPayload

app = FastAPI()

@app.post("/v1/vitals", status_code=status.HTTP_201_CREATED)
async def ingest_vitals(payload: VitalsPayload):
    # Business logic can confidently assume 'payload' data is 100% sanitized
    return {"status": "success", "processed_id": payload.patient_id}