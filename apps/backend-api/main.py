import os
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


app = FastAPI(title="Parking Backend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SlotStatus(BaseModel):
    slot_id: str
    occupied: bool


class OccupancyUpdate(BaseModel):
    camera_id: str
    timestamp: str
    slots: list[SlotStatus]


slot_state: dict[str, bool] = {
    "A-01": False,
    "A-02": True,
    "A-03": False,
    "A-04": True,
}

slot_logs: list[dict] = []


def build_slots_payload() -> list[dict]:
    return [
        {"slot_id": slot_id, "occupied": occupied}
        for slot_id, occupied in sorted(slot_state.items())
    ]


def build_summary_payload() -> dict:
    total = len(slot_state)
    occupied = sum(1 for value in slot_state.values() if value)
    return {
        "total_slots": total,
        "occupied_slots": occupied,
        "available_slots": total - occupied,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_snapshot(self, websocket: WebSocket) -> None:
        await websocket.send_json(
            {
                "event": "snapshot",
                "data": {
                    "summary": build_summary_payload(),
                    "slots": build_slots_payload(),
                    "logs": slot_logs[-20:],
                },
            }
        )

    async def broadcast(self, payload: dict) -> None:
        disconnected: list[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_json(payload)
            except Exception:
                disconnected.append(connection)

        for connection in disconnected:
            self.disconnect(connection)


manager = ConnectionManager()


def validate_secret(shared_secret: str | None) -> None:
    expected = os.getenv("AI_SHARED_SECRET", "demo-secret")
    if shared_secret != expected:
        raise HTTPException(status_code=401, detail="Invalid shared secret")


@app.get("/")
def root():
    return {
        "service": "backend-api",
        "message": "Parking backend is running",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/slots")
def get_slots():
    return {"slots": build_slots_payload()}


@app.get("/api/slots/status")
def get_slot_status():
    return slot_state


@app.get("/api/summary")
def get_summary():
    return build_summary_payload()


@app.get("/api/logs")
def get_logs():
    return {"logs": slot_logs[-20:]}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    await manager.send_snapshot(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/api/occupancy/update")
async def update_occupancy(
    payload: OccupancyUpdate,
    x_ai_shared_secret: str | None = Header(default=None),
):
    validate_secret(x_ai_shared_secret)

    for slot in payload.slots:
        slot_state[slot.slot_id] = slot.occupied

    slot_logs.append(
        {
            "camera_id": payload.camera_id,
            "timestamp": payload.timestamp,
            "updated_slots": len(payload.slots),
        }
    )

    await manager.broadcast(
        {
            "event": "occupancy_updated",
            "data": {
                "camera_id": payload.camera_id,
                "timestamp": payload.timestamp,
                "summary": build_summary_payload(),
                "slots": build_slots_payload(),
                "logs": slot_logs[-20:],
            },
        }
    )

    return {"message": "Occupancy updated", "updated_slots": len(payload.slots)}
