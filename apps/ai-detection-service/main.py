import asyncio
import json
import os
from collections import defaultdict, deque
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
from pathlib import Path

import cv2
import httpx
import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


publisher_task: asyncio.Task | None = None


class SlotStatus(BaseModel):
    slot_id: str
    occupied: bool


class OccupancyUpdate(BaseModel):
    camera_id: str
    timestamp: str
    slots: list[SlotStatus]


_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent.parent


def resolve_path(env_name: str, candidates: list[Path]) -> Path:
    env_path = os.getenv(env_name)
    if env_path and Path(env_path).exists():
        return Path(env_path)
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(f"{env_name} not found")


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _load_config_json(env_name: str, filename: str) -> dict:
    path = resolve_path(env_name, [
        _HERE / "config" / filename,
        _ROOT / "infra" / filename,
    ])
    return load_json(path)


def load_slot_config() -> dict:
    return _load_config_json("SLOT_CONFIG_PATH", "slot-config.json")


def load_slot_coordinates() -> dict:
    return _load_config_json("SLOT_COORDINATES_PATH", "slot-coordinates.json")


def load_reference_image() -> np.ndarray:
    path = resolve_path(
        "REFERENCE_IMAGE_PATH",
        [
            _ROOT / "datasets" / "emty.png",
            _ROOT / "datasets" / "carParkImg.png",
        ],
    )
    image = cv2.imread(str(path))
    if image is None:
        raise FileNotFoundError(f"Cannot read reference image: {path}")
    return image


def load_video_path() -> Path:
    return resolve_path("VIDEO_PATH", [_ROOT / "datasets" / "carPark.mp4"])


def scale_slot_rect(
    slot: dict,
    frame_width: int,
    frame_height: int,
    coord_width: int,
    coord_height: int,
) -> tuple[int, int, int, int]:
    sx = frame_width / coord_width
    sy = frame_height / coord_height

    video_offset_x = int(os.getenv("VIDEO_OFFSET_X", "0"))
    video_offset_y = int(os.getenv("VIDEO_OFFSET_Y", "5"))
    video_scale_x = float(os.getenv("VIDEO_SCALE_X", "0.985"))
    video_scale_y = float(os.getenv("VIDEO_SCALE_Y", "0.980"))

    x = int(slot["x"] * sx * video_scale_x) + video_offset_x
    y = int(slot["y"] * sy * video_scale_y) + video_offset_y
    w = int(slot["w"] * sx * video_scale_x)
    h = int(slot["h"] * sy * video_scale_y)

    x = max(0, min(x, frame_width - 1))
    y = max(0, min(y, frame_height - 1))
    w = max(1, min(w, frame_width - x))
    h = max(1, min(h, frame_height - y))

    return x, y, w, h



def detect_slot_occupied(
    frame_roi: np.ndarray,
    reference_roi: np.ndarray,
    current_state: bool = False,
) -> tuple[bool, float]:
    gray_frame = cv2.cvtColor(frame_roi, cv2.COLOR_BGR2GRAY)
    gray_ref = cv2.cvtColor(reference_roi, cv2.COLOR_BGR2GRAY)

    gray_frame = cv2.GaussianBlur(gray_frame, (5, 5), 0)
    gray_ref = cv2.GaussianBlur(gray_ref, (5, 5), 0)

    diff = cv2.absdiff(gray_frame, gray_ref)
    _, threshold = cv2.threshold(diff, 35, 255, cv2.THRESH_BINARY)

    changed_pixels = cv2.countNonZero(threshold)
    total_pixels = threshold.shape[0] * threshold.shape[1]
    score = changed_pixels / total_pixels

    # Hysteresis: higher threshold to enter occupied, lower to leave it.
    # Prevents oscillation at borderline values caused by lighting/shadow noise.
    high_threshold = float(os.getenv("DETECTION_THRESHOLD", "0.25"))
    low_threshold = float(os.getenv("DETECTION_THRESHOLD_LOW", "0.15"))

    if current_state:
        occupied = score >= low_threshold
    else:
        occupied = score >= high_threshold

    return occupied, score


def build_detection_payload(
    frame: np.ndarray,
    reference: np.ndarray,
    slot_config: dict,
    slot_coordinates: dict,
    current_states: dict[str, bool] | None = None,
) -> tuple[OccupancyUpdate, dict[str, float]]:
    frame_height, frame_width = frame.shape[:2]
    coord_width = int(slot_coordinates.get("image_width", frame_width))
    coord_height = int(slot_coordinates.get("image_height", frame_height))

    if reference.shape[:2] != frame.shape[:2]:
        reference = cv2.resize(reference, (frame_width, frame_height))

    detected_slots: list[SlotStatus] = []
    scores: dict[str, float] = {}

    for slot in slot_coordinates.get("slots", []):
        x, y, w, h = scale_slot_rect(
            slot=slot,
            frame_width=frame_width,
            frame_height=frame_height,
            coord_width=coord_width,
            coord_height=coord_height,
        )

        frame_roi = frame[y : y + h, x : x + w]
        reference_roi = reference[y : y + h, x : x + w]

        current = current_states.get(slot["slot_id"], False) if current_states else False
        occupied, score = detect_slot_occupied(frame_roi, reference_roi, current_state=current)
        scores[slot["slot_id"]] = score

        detected_slots.append(
            SlotStatus(
                slot_id=slot["slot_id"],
                occupied=occupied,
            )
        )

    return OccupancyUpdate(
        camera_id=slot_config.get("camera_id", "cam-01"),
        timestamp=datetime.now(timezone.utc).isoformat(),
        slots=detected_slots,
    ), scores


async def publish_payload(payload: OccupancyUpdate) -> dict:
    backend_api_url = os.getenv("BACKEND_API_URL", "http://localhost:8000/api")
    shared_secret = os.getenv("AI_SHARED_SECRET", "demo-secret")

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{backend_api_url}/occupancy/update",
            headers={"X-AI-Shared-Secret": shared_secret},
            json=payload.model_dump(),
        )

        response.raise_for_status()
        return response.json()


def draw_debug_overlay(
    frame: np.ndarray,
    payload: OccupancyUpdate,
    slot_coordinates: dict,
) -> np.ndarray:
    frame_height, frame_width = frame.shape[:2]
    coord_width = int(slot_coordinates.get("image_width", frame_width))
    coord_height = int(slot_coordinates.get("image_height", frame_height))

    occupied_map = {slot.slot_id: slot.occupied for slot in payload.slots}
    output = frame.copy()

    for slot in slot_coordinates.get("slots", []):
        x, y, w, h = scale_slot_rect(
            slot=slot,
            frame_width=frame_width,
            frame_height=frame_height,
            coord_width=coord_width,
            coord_height=coord_height,
        )

        occupied = occupied_map.get(slot["slot_id"], False)
        color = (0, 0, 255) if occupied else (0, 255, 0)

        cv2.rectangle(output, (x, y), (x + w, y + h), color, 2)
        cv2.putText(
            output,
            slot["slot_id"],
            (x + 4, y + 18),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            color,
            1,
            cv2.LINE_AA,
        )

    return output


async def video_detection_loop() -> None:
    video_path = load_video_path()
    reference = load_reference_image()
    slot_config = load_slot_config()
    slot_coordinates = load_slot_coordinates()

    detect_interval = float(os.getenv("DETECTION_INTERVAL_SECONDS", "1.0"))
    playback_speed = float(os.getenv("VIDEO_PLAYBACK_SPEED", "1.0"))
    show_video = os.getenv("SHOW_VIDEO", "true").lower() == "true"
    vote_window = int(os.getenv("VOTE_WINDOW", "5"))
    debug_scores = os.getenv("DEBUG_SCORES", "false").lower() == "true"
    max_detections = int(os.getenv("MAX_DETECTIONS", "0"))
    save_frames = os.getenv("SAVE_FRAMES", "false").lower() == "true"
    save_frames_dir = Path(os.getenv("SAVE_FRAMES_DIR", str(_ROOT / "datasets" / "detected_frames")))

    if save_frames:
        import shutil
        if save_frames_dir.exists():
            shutil.rmtree(save_frames_dir)
        save_frames_dir.mkdir(parents=True)
        print(f"Saving detected frames to: {save_frames_dir}")

    slot_votes: dict[str, deque] = defaultdict(lambda: deque(maxlen=vote_window))

    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    video_fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    frame_interval = 1.0 / (video_fps * playback_speed)
    detect_every_n = max(1, round(video_fps * detect_interval * playback_speed))

    heartbeat_interval = float(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "30"))

    loop = asyncio.get_event_loop()
    frame_count = 0
    detect_count = 0
    last_payload: OccupancyUpdate | None = None
    last_published_state: dict[str, bool] = {}
    last_publish_time: float = 0.0

    try:
        while True:
            t0 = loop.time()
            success, frame = cap.read()

            if not success:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                frame_count = 0
                slot_votes.clear()
                last_published_state = {}
                await asyncio.sleep(0.1)
                continue

            frame_count += 1

            if frame_count % detect_every_n == 0:
                detect_count += 1
                last_payload, raw_scores = build_detection_payload(
                    frame, reference, slot_config, slot_coordinates,
                    current_states=last_published_state,
                )
                raw_occupied = {s.slot_id: s.occupied for s in last_payload.slots}

                for slot in last_payload.slots:
                    slot_votes[slot.slot_id].append(slot.occupied)
                    votes = slot_votes[slot.slot_id]
                    slot.occupied = sum(votes) > len(votes) / 2

                if debug_scores:
                    video_t = frame_count / video_fps
                    lines = [
                        f"\n── DETECT #{detect_count:04d}  frame={frame_count:05d}/{int(cap.get(cv2.CAP_PROP_FRAME_COUNT))}  video_t={video_t:.2f}s ──",
                        f"{'SLOT':<10} {'SCORE':>8}  {'RAW':<10} {'VOTED':<10}  VOTES(last {vote_window})",
                        "-" * 68,
                    ]
                    for slot in last_payload.slots:
                        score = raw_scores[slot.slot_id]
                        raw = "OCCUPIED" if raw_occupied[slot.slot_id] else "vacant"
                        voted = "OCCUPIED" if slot.occupied else "vacant"
                        votes_str = str([int(v) for v in slot_votes[slot.slot_id]])
                        lines.append(f"{slot.slot_id:<10} {score:>8.4f}  {raw:<10} {voted:<10}  {votes_str}")
                    print("\n".join(lines), flush=True)

                if save_frames and last_payload is not None:
                    debug_frame = draw_debug_overlay(frame, last_payload, slot_coordinates)
                    video_t = frame_count / video_fps
                    fname = save_frames_dir / f"detect_{detect_count:04d}_frame{frame_count:05d}_t{video_t:.2f}s.jpg"
                    cv2.imwrite(str(fname), debug_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])

                current_state = {s.slot_id: s.occupied for s in last_payload.slots}
                now = loop.time()
                state_changed = current_state != last_published_state
                heartbeat_due = (now - last_publish_time) >= heartbeat_interval

                if state_changed or heartbeat_due:
                    try:
                        await publish_payload(last_payload)
                        reason = "changed" if state_changed else "heartbeat"
                        occupied_n = sum(1 for s in last_payload.slots if s.occupied)
                        print(
                            f"→ detect={detect_count:04d}  occupied={occupied_n}/{len(last_payload.slots)}"
                            f"  [{reason}]  ts={last_payload.timestamp}",
                            flush=True,
                        )
                        last_published_state = current_state
                        last_publish_time = now
                    except Exception as error:
                        print(f"✗ publish failed: {error}", flush=True)

                if max_detections > 0 and detect_count == max_detections:
                    print(f"MAX_DETECTIONS={max_detections} reached — log and frame capture stopped.", flush=True)
                    debug_scores = False
                    save_frames = False

            if show_video:
                if last_payload is not None:
                    debug_frame = draw_debug_overlay(frame, last_payload, slot_coordinates)
                    cv2.imshow("Parking Detection", debug_frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            elapsed = loop.time() - t0
            await asyncio.sleep(max(0.0, frame_interval - elapsed))

    finally:
        cap.release()

        if show_video:
            cv2.destroyAllWindows()


def build_mock_payload(slot_config: dict, iteration: int = 0) -> OccupancyUpdate:
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


async def mock_publisher_loop() -> None:
    slot_config = load_slot_config()
    interval_seconds = float(os.getenv("MOCK_INTERVAL_SECONDS", "2"))
    iteration = 0

    while True:
        payload = build_mock_payload(slot_config, iteration)

        try:
            await publish_payload(payload)
            print(f"Published mock {len(payload.slots)} slots at {payload.timestamp}")
        except Exception as error:
            print(f"Failed to publish mock payload: {error}")

        iteration += 1
        await asyncio.sleep(interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global publisher_task

    mock_mode = os.getenv("MOCK_MODE", "false").lower() == "true"

    if mock_mode:
        publisher_task = asyncio.create_task(mock_publisher_loop())
    else:
        publisher_task = asyncio.create_task(video_detection_loop())

    yield

    if publisher_task is not None:
        publisher_task.cancel()

        with suppress(asyncio.CancelledError):
            await publisher_task

        publisher_task = None


app = FastAPI(title="Parking AI Detection Service", lifespan=lifespan)


@app.get("/")
def root():
    return {
        "service": "ai-detection-service",
        "message": "AI detection service is running",
        "backend_api_url": os.getenv("BACKEND_API_URL", "http://localhost:8000/api"),
        "mock_mode": os.getenv("MOCK_MODE", "false").lower() == "true",
        "video_path": str(load_video_path()),
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/sample-payload")
def sample_payload():
    video_path = load_video_path()
    reference = load_reference_image()

    cap = cv2.VideoCapture(str(video_path))
    success, frame = cap.read()
    cap.release()

    if not success:
        raise RuntimeError(f"Cannot read first frame from video: {video_path}")

    payload, _ = build_detection_payload(frame, reference, load_slot_config(), load_slot_coordinates())
    return payload.model_dump()


@app.get("/mock/status")
def mock_status():
    return {
        "mock_mode": os.getenv("MOCK_MODE", "false").lower() == "true",
        "mock_interval_seconds": float(os.getenv("MOCK_INTERVAL_SECONDS", "2")),
        "detection_interval_seconds": float(os.getenv("DETECTION_INTERVAL_SECONDS", "0.5")),
        "detection_threshold": float(os.getenv("DETECTION_THRESHOLD", "0.25")),
        "detection_threshold_low": float(os.getenv("DETECTION_THRESHOLD_LOW", "0.15")),
        "backend_api_url": os.getenv("BACKEND_API_URL", "http://localhost:8000/api"),
    }


@app.post("/mock/run-once")
async def run_mock_once():
    payload = build_mock_payload(load_slot_config())
    backend_response = await publish_payload(payload)

    return {
        "payload": payload.model_dump(),
        "backend_response": backend_response,
    }


@app.post("/detect/run-once")
async def run_detection_once():
    video_path = load_video_path()
    reference = load_reference_image()

    cap = cv2.VideoCapture(str(video_path))
    success, frame = cap.read()
    cap.release()

    if not success:
        raise RuntimeError(f"Cannot read first frame from video: {video_path}")

    payload, _ = build_detection_payload(frame, reference, load_slot_config(), load_slot_coordinates())
    backend_response = await publish_payload(payload)

    return {
        "payload": payload.model_dump(),
        "backend_response": backend_response,
    }
