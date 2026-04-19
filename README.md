# Parking-Space-Detection-System

Tai lieu chinh:

- [docs/CODEX_EXECUTION_PLAN.md](docs/CODEX_EXECUTION_PLAN.md)
- [docs/SYSTEM_BLUEPRINT.md](docs/SYSTEM_BLUEPRINT.md)
- [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)

Thanh phan chinh:

- [apps/ai-detection-service](apps/ai-detection-service): FastAPI mock publisher gui occupancy update dinh ky ve backend
- [apps/backend-api](apps/backend-api): FastAPI REST + WebSocket giu state slot, summary va recent logs
- [apps/web-dashboard](apps/web-dashboard): React + Vite dashboard cho route `/` va `/admin`

Contract va config dung chung:

- Payload occupancy: `camera_id`, `timestamp`, `slots[]`
- Shared secret header: `X-AI-Shared-Secret`
- Slot config: [infra/slot-config.json](infra/slot-config.json)

Run local bang Docker Compose:

1. Tao file `.env` tu `.env.example`.
2. Chay `docker compose up --build`.
3. Mo:
   - User dashboard: `http://localhost:5173`
   - Admin dashboard: `http://localhost:5173/admin`
   - Backend health: `http://localhost:8000/api/health`
   - AI health: `http://localhost:9000/health`

Smoke check nhanh:

- AI service o mock mode se tu dong POST occupancy update ve backend theo chu ky `MOCK_INTERVAL_SECONDS`.
- Backend se cap nhat `GET /api/summary`, `GET /api/slots`, `GET /api/logs` va day du lieu qua `ws://localhost:8000/ws`.
- Frontend se load state ban dau qua REST va cap nhat realtime qua WebSocket.
