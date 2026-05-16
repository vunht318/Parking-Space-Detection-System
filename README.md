# Parking Space Detection System

Real-time parking lot occupancy detection with AI, REST API, WebSocket broadcast, and a React dashboard.

## Architecture

```
ai-detection-service  →  backend-api  ←→  web-dashboard
      (port 9000)           (port 8000)       (port 5173)
```

- **ai-detection-service** — FastAPI service, publishes occupancy updates to backend (mock mode or real CV pipeline)
- **backend-api** — FastAPI REST + WebSocket, holds slot state, serves summary and logs
- **web-dashboard** — React + Vite dashboard, user view at `/`, admin view at `/admin`

---

## Prerequisites

### Option A — Docker (recommended)

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) ≥ 4.x

### Option B — Run each service manually

- Python 3.11+
- Node.js 20+
- npm 9+

---

## Quick Start — Docker

```bash
# 1. Clone the repo
git clone <repo-url>
cd Parking-Space-Detection-System

# 2. Create your .env file
cp .env.example .env

# 3. Start all services
docker compose up --build
```

All three services start in the correct order. Open:

| URL | Description |
|-----|-------------|
| http://localhost:5173 | User dashboard |
| http://localhost:5173/admin | Admin dashboard |
| http://localhost:8000/api/health | Backend health check |
| http://localhost:9000/health | AI service health check |

To stop: `docker compose down`

---

## Local Development — Without Docker

Run each service in a **separate terminal**, in this order:

### 1. Backend API

```bash
cd apps/backend-api
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 2. AI Detection Service

```bash
cd apps/ai-detection-service
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Set required env vars
export BACKEND_API_URL=http://localhost:8000/api
export AI_SHARED_SECRET=demo-secret
export MOCK_MODE=false
export VIDEO_PATH=../../datasets/carPark.mp4
export DETECTION_INTERVAL_SECONDS=0.02
export SHOW_VIDEO=true

uvicorn main:app --reload --port 9000
```

### 3. Web Dashboard

```bash
cd apps/web-dashboard
npm install
npm run dev
```

The Vite dev server reads `apps/web-dashboard/.env` — default values already point to `localhost:8000`.

---

## Environment Variables

Copy `.env.example` to `.env` and adjust as needed.

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Environment name |
| `BACKEND_PORT` | `8000` | Backend API port |
| `AI_PORT` | `9000` | AI service port |
| `FRONTEND_PORT` | `5173` | Web dashboard port |
| `AI_SHARED_SECRET` | `demo-secret` | Shared secret between AI service and backend |
| `MOCK_MODE` | `false` | `true` = AI service sends fake data; `false` = real CV pipeline |
| `MOCK_INTERVAL_SECONDS` | `2` | How often mock data is pushed (seconds) |
| `DETECTION_INTERVAL_SECONDS` | `0.02` | Delay between processed video frames; lower value makes playback and updates faster |
| `DETECTION_THRESHOLD` | `0.75` | Slot change score needed to mark a slot occupied; higher value reduces false occupied detections |
| `REFERENCE_IMAGE_PATH` | `./datasets/reference_median.png` | Empty/reference parking image used by the CV pipeline |
| `BACKEND_API_URL` | `http://backend-api:8000/api` | Used by AI service to reach backend (Docker internal URL) |
| `VITE_API_BASE_URL` | `http://localhost:8000/api` | Used by frontend to reach backend |
| `VITE_WS_URL` | `ws://localhost:8000/ws` | WebSocket URL for frontend |
| `VIDEO_PATH` | `./datasets/carPark.mp4` | Video file path used by the real CV pipeline |
| `SHOW_VIDEO` | `false` | Show OpenCV debug window; keep `false` in Docker/headless environments |

> **Note:** When running without Docker, set `BACKEND_API_URL=http://localhost:8000/api` so the AI service reaches the backend correctly.

---

## Verify Everything Works

After starting all services, run a quick smoke check:

```bash
# Backend health
curl http://localhost:8000/api/health

# AI service health
curl http://localhost:9000/health

# Current slot state
curl http://localhost:8000/api/slots

# Summary
curl http://localhost:8000/api/summary
```

Expected behavior:
- AI service reads frames from `VIDEO_PATH` and auto-POSTs occupancy updates to backend every `DETECTION_INTERVAL_SECONDS`
- Backend updates slot state and broadcasts via WebSocket at `ws://localhost:8000/ws`
- Dashboard loads initial state via REST, then receives live updates via WebSocket

---

## Project Docs

- [docs/SYSTEM_BLUEPRINT.md](docs/SYSTEM_BLUEPRINT.md) — architecture and design decisions
- [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) — production deployment
- [docs/CLAUDE_EXECUTION_PLAN.md](docs/CLAUDE_EXECUTION_PLAN.md) — feature list and task tracker
- [infra/slot-config.json](infra/slot-config.json) — parking slot configuration
