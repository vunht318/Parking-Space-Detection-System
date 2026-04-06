import os
from datetime import datetime, timezone

from fastapi import FastAPI


app = FastAPI(title="Parking AI Detection Service")


@app.get("/")
def root():
    return {
        "service": "ai-detection-service",
        "message": "AI detection scaffold is running",
        "backend_api_url": os.getenv("BACKEND_API_URL", "http://backend-api:8000/api"),
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/sample-payload")
def sample_payload():
    return {
        "camera_id": "cam-01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "slots": [
            {"slot_id": "A-01", "occupied": False},
            {"slot_id": "A-02", "occupied": True},
            {"slot_id": "A-03", "occupied": False},
            {"slot_id": "A-04", "occupied": True},
        ],
    }

