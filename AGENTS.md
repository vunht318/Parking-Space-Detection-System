# AGENTS.md — Codex Execution Guide

## 1. Role and Goal

You are an autonomous AI engineer building the **Parking-Space-Detection-System** end-to-end.

Your job:
1. Read the feature list in `docs/CODEX_EXECUTION_PLAN.md` (Section 4 — Feature Input).
2. Generate or refine the task breakdown from that feature list.
3. Save the updated task list back into `docs/CODEX_EXECUTION_PLAN.md`.
4. Implement tasks one by one in the prescribed order.
5. Mark each task `Done` in `docs/CODEX_EXECUTION_PLAN.md` as soon as it is complete.
6. Log every action in the Implementation Log (Section 9).

Never skip steps. Never mark a task Done without implementing and verifying it.

---

## 2. Repo Structure

```
Parking-Space-Detection-System/
├─ apps/
│  ├─ ai-detection-service/   # Python — video/frame ingestion + occupancy detection
│  ├─ backend-api/            # Python FastAPI — REST API + WebSocket broadcast
│  └─ web-dashboard/          # React + Vite + TypeScript — user & admin UI
├─ datasets/                  # carPark.mp4, carParkImg.png
├─ docs/
│  ├─ CODEX_EXECUTION_PLAN.md # Primary working file — features, tasks, status, logs
│  ├─ SYSTEM_BLUEPRINT.md     # Architecture reference
│  └─ DEPLOYMENT_GUIDE.md
├─ infra/
├─ docker-compose.yml
├─ .env.example
└─ AGENTS.md                  # This file
```

---

## 3. Primary Working File

**`docs/CODEX_EXECUTION_PLAN.md`** is your single source of truth.

- Section 4 — Feature Input: read the feature list the user provides here.
- Section 6 — Task Breakdown: write and maintain the task table here.
- Section 9 — Implementation Log: append one row per completed action.
- Section 10 — Blockers / Decisions: record any blocker or pending decision here.

Do not create separate planning files. All state lives in that file.

---

## 4. Workflow — Step by Step

### Step 1 — Read Features

Open `docs/CODEX_EXECUTION_PLAN.md`, go to **Section 4 — Feature Input**.

For each feature entry (F1, F2, …):
- Extract: name, description, value, user/role, priority, constraints.
- Confirm you understand the acceptance criteria before generating tasks.

### Step 2 — Generate Task Breakdown

Convert the feature list into tasks using the Epic structure below.
Write the result into **Section 6** of `docs/CODEX_EXECUTION_PLAN.md`.

Epic structure:
- **Epic A** — Project foundation (schema, config, env)
- **Epic B** — AI detection pipeline
- **Epic C** — Backend API and realtime
- **Epic D** — Web dashboard
- **Epic E** — Integration and delivery

Task table format per epic:

```markdown
| ID | Task | Module | Priority | Dependency | Status | Done when |
|----|------|--------|----------|------------|--------|-----------|
| A1 | ... | `apps/backend-api` | High | None | Todo | ... |
```

Status values: `Todo` | `In Progress` | `Blocked` | `Done`

Rules:
- Every feature must map to at least one task.
- Every task must have a clear "Done when" criterion.
- Tasks within an epic must be ordered by dependency.

### Step 3 — Confirm Implementation Order

Write or verify **Section 7 — Thu Tu Implement** in `docs/CODEX_EXECUTION_PLAN.md`.

Default recommended order:
1. A1 → A2 → B4 (mock mode first so frontend has data)
2. C1 → C2 → C3 → C4 (backend state + API + WebSocket)
3. D1 → D2 → D3 (frontend data layer + UI)
4. B1 → B2 → B3 (real detection pipeline)
5. E1 → E2 → E3 (Docker, docs, smoke test)

Adjust if the feature list changes the priority.

### Step 4 — Implement Tasks

Pick the first `Todo` task in order. Before writing code:
- Set its status to `In Progress` in `docs/CODEX_EXECUTION_PLAN.md`.
- Re-read the "Done when" criterion.

Implement the task. Then:
- Set its status to `Done`.
- Append a row to Section 9 (Implementation Log).
- Move to the next task.

Repeat until all tasks are `Done`.

---

## 5. Coding Standards

### General
- Keep changes minimal and targeted to the current task. Do not refactor unrelated code.
- Do not add comments unless the reason is non-obvious.
- Do not add error handling for scenarios that cannot happen at runtime.

### Python (ai-detection-service, backend-api)
- Use `FastAPI`, `Pydantic v2`, `httpx` (async HTTP calls).
- Follow the existing `main.py` patterns already in each service.
- Format with `black`, lint with `ruff`.
- Use type hints everywhere.

### TypeScript / React (web-dashboard)
- Use functional components and hooks only.
- Follow the existing `App.tsx` patterns.
- No external UI libraries unless already in `package.json`.
- Format with `prettier`, lint with `eslint`.

### Contracts
- The occupancy payload between AI service and backend is fixed:
  ```json
  {
    "camera_id": "cam-01",
    "timestamp": "<ISO 8601 UTC>",
    "slots": [
      { "slot_id": "A-01", "occupied": true }
    ]
  }
  ```
- Authentication between AI service and backend uses header `X-AI-Shared-Secret` (value from env `AI_SHARED_SECRET`, default `demo-secret`).

### Environment Variables
Defined in `.env.example`. Services read from env at runtime. Never hard-code secrets.

---

## 6. Verification Before Marking Done

A task is `Done` only when:

| Module | Verification |
|--------|-------------|
| `ai-detection-service` | `GET /health` returns `{"status": "ok"}` and the feature logic runs without exception |
| `backend-api` | Relevant endpoint returns correct response; WebSocket broadcast fires on state change |
| `web-dashboard` | UI renders correct data; no console errors; loading/error states are handled |
| `infra` | `docker compose up` starts all services with no crash |

---

## 7. Blocker Protocol

If you cannot complete a task because of a missing decision, unclear requirement, or external dependency:

1. Set task status to `Blocked`.
2. Add a row to **Section 10 — Blockers / Decisions** in `docs/CODEX_EXECUTION_PLAN.md`:
   ```
   | <date> | Blocker | <description> | User | Open |
   ```
3. Move to the next unblocked task.
4. Do not invent requirements to unblock yourself without noting it as a decision.

---

## 8. What NOT to Do

- Do not create new planning or architecture files — use `docs/CODEX_EXECUTION_PLAN.md`.
- Do not implement features not in the feature list.
- Do not add mobile app, billing, reservation, Google Maps, or LED board features.
- Do not use Kubernetes, complex CI/CD, or external cloud services.
- Do not mark a task Done without actually implementing and verifying it.
- Do not push to remote unless the user explicitly asks.

---

## 9. Quick Reference — Existing Scaffold

| File | State |
|------|-------|
| `apps/backend-api/main.py` | FastAPI with `/api/slots`, `/api/summary`, `/api/logs`, `POST /api/occupancy/update`, WebSocket `/ws`. In-memory state. Shared secret auth. |
| `apps/ai-detection-service/main.py` | Scaffold only — health check and sample payload endpoint. Detection logic not implemented. |
| `apps/web-dashboard/src/App.tsx` | React app — connects to REST + WebSocket, renders parking map, summary cards, logs. User/admin split by route `/admin`. |
| `docker-compose.yml` | Orchestrates all three services. |
| `.env.example` | Lists all required env vars. |
| `datasets/carPark.mp4` | Video file for detection testing. |
| `datasets/carParkImg.png` | Reference image for slot annotation. |
