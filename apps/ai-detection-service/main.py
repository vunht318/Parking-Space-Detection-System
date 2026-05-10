import asyncio
import json
import logging
import os
import time
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path

import cv2
import httpx
import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(title="Parking AI Detection Service")
publisher_task: asyncio.Task | None = None

_reference_frame: np.ndarray | None = None   # empty-lot reference for background subtraction
_demo_paused: bool = False


class SlotStatus(BaseModel):
    slot_id: str
    occupied: bool


class OccupancyUpdate(BaseModel):
    camera_id: str
    timestamp: str
    slots: list[SlotStatus]


class SyntheticDemoRequest(BaseModel):
    vacant_slots: list[str]
    hold_seconds: float = 10.0


# ---------------------------------------------------------------------------
# Config loaders
# ---------------------------------------------------------------------------

def _resolve_config_path(filename: str, env_var: str) -> Path:
    env_path = os.getenv(env_var)
    candidates = [
        Path(env_path) if env_path else None,
        Path(__file__).resolve().parent / "config" / filename,
        Path(__file__).resolve().parent.parent.parent / "infra" / filename,
        Path(__file__).resolve().parent.parent.parent / "datasets" / filename,
    ]
    path = next((p for p in candidates if p and p.exists()), None)
    if path is None:
        raise FileNotFoundError(f"{filename} not found")
    return path


def load_slot_config() -> dict:
    with _resolve_config_path("slot-config.json", "SLOT_CONFIG_PATH").open(encoding="utf-8") as f:
        return json.load(f)


def load_coordinates_file() -> dict:
    path = _resolve_config_path("slot-coordinates.json", "SLOT_COORDINATES_PATH")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_slot_coordinates() -> dict[str, tuple[int, int, int, int]]:
    data = load_coordinates_file()
    return {s["slot_id"]: (s["x"], s["y"], s["w"], s["h"]) for s in data["slots"]}


def _resolve_video_path() -> Path:
    env_path = os.getenv("VIDEO_PATH")
    candidates = [
        Path(env_path) if env_path else None,
        Path(__file__).resolve().parent.parent.parent / "datasets" / "carPark.mp4",
    ]
    path = next((p for p in candidates if p and p.exists()), None)
    if path is None:
        raise FileNotFoundError("carPark.mp4 not found")
    return path


def _resolve_reference_path() -> Path | None:
    env_path = os.getenv("REFERENCE_EMPTY_PATH")
    candidates = [
        Path(env_path) if env_path else None,
        Path(__file__).resolve().parent.parent.parent / "datasets" / "reference_empty.png",
    ]
    return next((p for p in candidates if p and p.exists()), None)


# ---------------------------------------------------------------------------
# Detection logic — background subtraction
# ---------------------------------------------------------------------------

def detect_occupied_bg(
    roi: np.ndarray,
    ref_roi: np.ndarray,
    pixel_threshold: int,
    area_threshold: float,
) -> bool:
    """
    Compare live ROI against the inpainted empty-reference ROI.
    Pixels that changed significantly → likely a car is present.
    """
    diff = cv2.absdiff(roi, ref_roi)
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, pixel_threshold, 255, cv2.THRESH_BINARY)
    changed_ratio = cv2.countNonZero(binary) / binary.size
    return changed_ratio > area_threshold


def analyze_frame(
    frame: np.ndarray,
    coordinates: dict[str, tuple[int, int, int, int]],
    pixel_threshold: int,
    area_threshold: float,
) -> list[SlotStatus]:
    ref = _reference_frame
    results: list[SlotStatus] = []
    for slot_id, (x, y, w, h) in coordinates.items():
        roi = frame[y : y + h, x : x + w]
        if roi.size == 0:
            continue
        if ref is not None:
            ref_roi = ref[y : y + h, x : x + w]
            occupied = detect_occupied_bg(roi, ref_roi, pixel_threshold, area_threshold)
        else:
            # Fallback: absolute texture density when no reference available
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            thresh = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 2
            )
            occupied = (cv2.countNonZero(thresh) / thresh.size) > area_threshold
        results.append(SlotStatus(slot_id=slot_id, occupied=occupied))
    return results


# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Real detection loop
# ---------------------------------------------------------------------------

async def real_detection_loop() -> None:
    global _reference_frame

    interval = float(os.getenv("DETECTION_INTERVAL_SECONDS", "2"))
    pixel_threshold = int(os.getenv("DETECTION_PIXEL_THRESHOLD", "30"))
    area_threshold = float(os.getenv("DETECTION_AREA_THRESHOLD", "0.15"))

    slot_config = load_slot_config()
    camera_id = slot_config.get("camera_id", "cam-01")
    coordinates = load_slot_coordinates()
    video_path = _resolve_video_path()

    # Load empty reference image
    ref_path = _resolve_reference_path()
    if ref_path:
        _reference_frame = cv2.imread(str(ref_path))
        log.info("Loaded empty reference: %s", ref_path.name)
    else:
        log.warning("reference_empty.png not found — falling back to texture density")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    log.info(
        "Video: %s | fps=%.1f | frames=%d | ref=%s | pixel_thr=%d | area_thr=%.2f",
        video_path.name, fps, total_frames,
        ref_path.name if ref_path else "none",
        pixel_threshold, area_threshold,
    )

    frame_index = 0
    last_log_time = time.monotonic()

    while True:
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            frame_index = 0
            log.info("Video looped back to frame 0")
            continue

        frame_index += 1
        now = time.monotonic()
        if now - last_log_time >= 1.0:
            log.info("Frame %d / %d", frame_index, total_frames)
            last_log_time = now

        if not _demo_paused:
            slots = analyze_frame(frame, coordinates, pixel_threshold, area_threshold)
            payload = OccupancyUpdate(
                camera_id=camera_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                slots=slots,
            )
            try:
                await publish_payload(payload)
            except Exception as exc:
                log.warning("Publish failed: %s", exc)

        await asyncio.sleep(interval)


# ---------------------------------------------------------------------------
# Mock loop
# ---------------------------------------------------------------------------

def build_mock_payload(iteration: int = 0) -> OccupancyUpdate:
    slot_config = load_slot_config()
    slots = [
        SlotStatus(
            slot_id=slot["slot_id"],
            occupied=(
                bool(slot.get("default_occupied", False))
                if (iteration + idx) % 2 == 0
                else not bool(slot.get("default_occupied", False))
            ),
        )
        for idx, slot in enumerate(slot_config.get("slots", []))
    ]
    return OccupancyUpdate(
        camera_id=slot_config.get("camera_id", "cam-01"),
        timestamp=datetime.now(timezone.utc).isoformat(),
        slots=slots,
    )


async def mock_publisher_loop() -> None:
    interval = float(os.getenv("MOCK_INTERVAL_SECONDS", "2"))
    iteration = 0
    while True:
        payload = build_mock_payload(iteration)
        try:
            await publish_payload(payload)
        except Exception:
            pass
        iteration += 1
        await asyncio.sleep(interval)


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup_event() -> None:
    global publisher_task
    mock_mode = os.getenv("MOCK_MODE", "true").lower() == "true"
    if mock_mode:
        log.info("Starting in MOCK mode")
        publisher_task = asyncio.create_task(mock_publisher_loop())
    else:
        log.info("Starting in REAL DETECTION mode (background subtraction)")
        publisher_task = asyncio.create_task(real_detection_loop())


@app.on_event("shutdown")
async def shutdown_event() -> None:
    global publisher_task
    if publisher_task is None:
        return
    publisher_task.cancel()
    with suppress(asyncio.CancelledError):
        await publisher_task
    publisher_task = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    mock_mode = os.getenv("MOCK_MODE", "true").lower() == "true"
    return {
        "service": "ai-detection-service",
        "mode": "mock" if mock_mode else "real_detection",
        "reference_loaded": _reference_frame is not None,
        "backend_api_url": os.getenv("BACKEND_API_URL", "http://backend-api:8000/api"),
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/detection/status")
def detection_status():
    return {
        "mode": "mock" if os.getenv("MOCK_MODE", "true").lower() == "true" else "real_detection",
        "reference_loaded": _reference_frame is not None,
        "pixel_threshold": int(os.getenv("DETECTION_PIXEL_THRESHOLD", "30")),
        "area_threshold": float(os.getenv("DETECTION_AREA_THRESHOLD", "0.15")),
        "interval_seconds": float(os.getenv("DETECTION_INTERVAL_SECONDS", "2")),
    }


@app.post("/demo/synthetic-vacant")
async def demo_synthetic_vacant(request: SyntheticDemoRequest):
    """Simulate vacant slots by comparing against reference, pause loop during hold."""
    global _demo_paused

    coordinates = load_slot_coordinates()
    slot_config = load_slot_config()
    camera_id = slot_config.get("camera_id", "cam-01")

    video_path = _resolve_video_path()
    cap = cv2.VideoCapture(str(video_path))
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return {"error": "Cannot read video frame"}

    pixel_threshold = int(os.getenv("DETECTION_PIXEL_THRESHOLD", "30"))
    area_threshold = float(os.getenv("DETECTION_AREA_THRESHOLD", "0.15"))

    # Clear requested slots in the live frame using lane texture
    synthetic = frame.copy()
    ref_path = _resolve_reference_path()
    ref = cv2.imread(str(ref_path)) if ref_path else None
    if ref is not None:
        for slot_id in request.vacant_slots:
            if slot_id in coordinates:
                x, y, w, h = coordinates[slot_id]
                synthetic[y : y + h, x : x + w] = ref[y : y + h, x : x + w]

    slots = analyze_frame(synthetic, coordinates, pixel_threshold, area_threshold)

    payload = OccupancyUpdate(
        camera_id=camera_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        slots=slots,
    )

    _demo_paused = True
    backend_response = await publish_payload(payload)
    log.info("Demo: pausing loop for %.0fs", request.hold_seconds)
    asyncio.get_event_loop().call_later(request.hold_seconds, _resume_detection)

    return {
        "requested_vacant": request.vacant_slots,
        "detected_vacant": [s.slot_id for s in slots if not s.occupied],
        "detected_occupied": [s.slot_id for s in slots if s.occupied],
        "hold_seconds": request.hold_seconds,
        "backend_response": backend_response,
    }


def _resume_detection() -> None:
    global _demo_paused
    _demo_paused = False
    log.info("Demo hold ended — resuming real detection")


@app.get("/sample-payload")
def sample_payload():
    return build_mock_payload().model_dump()


@app.post("/mock/run-once")
async def run_mock_once():
    payload = build_mock_payload()
    backend_response = await publish_payload(payload)
    return {"payload": payload.model_dump(), "backend_response": backend_response}
