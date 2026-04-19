import asyncio
import json
import os
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(title="Parking AI Detection Service")
publisher_task: asyncio.Task | None = None


class SlotStatus(BaseModel):
    slot_id: str
    occupied: bool


class OccupancyUpdate(BaseModel):
    camera_id: str
    timestamp: str
    slots: list[SlotStatus]


def load_slot_config() -> dict:
    env_path = os.getenv("SLOT_CONFIG_PATH")
    candidates = [
        Path(env_path) if env_path else None,
        Path(__file__).resolve().parent / "config" / "slot-config.json",
        Path(__file__).resolve().parent.parent.parent / "infra" / "slot-config.json",
    ]

    config_path = next((path for path in candidates if path and path.exists()), None)
    if config_path is None:
        raise FileNotFoundError("slot-config.json not found")

    with config_path.open("r", encoding="utf-8") as config_file:
        return json.load(config_file)


def build_mock_payload(iteration: int = 0) -> OccupancyUpdate:
    slot_config = load_slot_config()
    slots = []

    for index, slot in enumerate(slot_config.get("slots", [])):
        default_occupied = bool(slot.get("default_occupied", False))
        occupied = default_occupied if (iteration + index) % 2 == 0 else not default_occupied
        slots.append(SlotStatus(slot_id=slot["slot_id"], occupied=occupied))

    return OccupancyUpdate(
        camera_id=slot_config.get("camera_id", "cam-01"),
        timestamp=datetime.now(timezone.utc).isoformat(),
        slots=slots,
    )


async def publish_payload(payload: OccupancyUpdate) -> dict:
    backend_api_url = os.getenv("BACKEND_API_URL", "http://backend-api:8000/api")
    shared_secret = os.getenv("AI_SHARED_SECRET", "demo-secret")

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{backend_api_url}/occupancy/update",
            headers={"X-AI-Shared-Secret": shared_secret},
            json=payload.model_dump(),
        )
        response.raise_for_status()
        return response.json()


async def mock_publisher_loop() -> None:
    interval_seconds = float(os.getenv("MOCK_INTERVAL_SECONDS", "2"))
    iteration = 0

    while True:
        payload = build_mock_payload(iteration)
        try:
            await publish_payload(payload)
        except Exception:
            pass

        iteration += 1
        await asyncio.sleep(interval_seconds)


@app.on_event("startup")
async def startup_event() -> None:
    global publisher_task

    if os.getenv("MOCK_MODE", "true").lower() != "true":
        return

    publisher_task = asyncio.create_task(mock_publisher_loop())


@app.on_event("shutdown")
async def shutdown_event() -> None:
    global publisher_task

    if publisher_task is None:
        return

    publisher_task.cancel()
    with suppress(asyncio.CancelledError):
        await publisher_task
    publisher_task = None


@app.get("/")
def root():
    return {
        "service": "ai-detection-service",
        "message": "AI detection mock service is running",
        "backend_api_url": os.getenv("BACKEND_API_URL", "http://backend-api:8000/api"),
        "mock_mode": os.getenv("MOCK_MODE", "true").lower() == "true",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/sample-payload")
def sample_payload():
    return build_mock_payload().model_dump()


@app.get("/mock/status")
def mock_status():
    return {
        "mock_mode": os.getenv("MOCK_MODE", "true").lower() == "true",
        "interval_seconds": float(os.getenv("MOCK_INTERVAL_SECONDS", "2")),
        "backend_api_url": os.getenv("BACKEND_API_URL", "http://backend-api:8000/api"),
    }


@app.post("/mock/run-once")
async def run_mock_once():
    payload = build_mock_payload()
    backend_response = await publish_payload(payload)
    return {"payload": payload.model_dump(), "backend_response": backend_response}
