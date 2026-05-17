# Project Tracker

> Xem yeu cau he thong va kien truc tai: [SYSTEM_BLUEPRINT.md](./SYSTEM_BLUEPRINT.md)

## 1. Muc tieu

Tai lieu nay theo doi tien do implement `Parking-Space-Detection-System` — task status, implementation log, va blockers.

Flow su dung:

1. Ban cung cap danh sach tinh nang.
2. Claude chuyen danh sach tinh nang thanh backlog va task list ky thuat.
3. Claude cap nhat file nay trong suot qua trinh implement.
4. Claude danh dau trang thai task khi da xong hoac bi blocker.

## 2. Cach Claude se lam viec

Claude se di theo thu tu sau:

1. Lam ro pham vi tinh nang va muc uu tien.
2. Tach tinh nang thanh epics, tasks, subtasks.
3. Gan task vao dung module:
   - `apps/ai-detection-service`
   - `apps/backend-api`
   - `apps/web-dashboard`
   - `infra`
   - `docs`
4. Xac dinh dependency, thu tu implement, tieu chi hoan thanh.
5. Thuc hien code, test, tai lieu, va cap nhat file nay.

## 3. Input Tu Ban

Ban dien danh sach tinh nang vao muc duoi day theo format ngan gon:

```md
## Feature Input

### F1. Ten tinh nang
- Mo ta:
- Gia tri mang lai:
- User/role lien quan:
- Muc uu tien: High / Medium / Low
- Rang buoc neu co:

### F2. Ten tinh nang
- Mo ta:
- Gia tri mang lai:
- User/role lien quan:
- Muc uu tien: High / Medium / Low
- Rang buoc neu co:
```

## 4. Feature Input

### F1. Real-time space detection
- Mo ta: Detect trang thai tung parking slot tu video/camera va cap nhat theo chu ky ngan.
- Gia tri mang lai: Tao nguon du lieu cot loi cho toan bo he thong.
- User/role lien quan: System, admin, user
- Muc uu tien: High
- Rang buoc neu co: MVP nen uu tien video file truoc khi chay camera that

### F2. Parking map visualization
- Mo ta: Hien thi layout bai xe va mau sac tung o theo trang thai vacant/occupied/unknown.
- Gia tri mang lai: User va admin nhin duoc tinh trang bai xe ngay lap tuc.
- User/role lien quan: user, admin
- Muc uu tien: High
- Rang buoc neu co: Can phu hop voi slot config va du lieu realtime tu backend

### F3. Availability summary
- Mo ta: Hien thi tong so cho trong, tong so cho dang co xe, va co the tach theo khu vuc.
- Gia tri mang lai: Giup xem nhanh kha nang con trong cua bai xe.
- User/role lien quan: user, admin
- Muc uu tien: High
- Rang buoc neu co: Summary phai dong bo voi state hien tai cua slots

### F4. Admin monitoring dashboard
- Mo ta: Admin xem toan bo trang thai, danh sach slot, log update gan day, va thong tin he thong co ban.
- Gia tri mang lai: Ho tro demo vai tro giam sat va van hanh.
- User/role lien quan: admin
- Muc uu tien: High
- Rang buoc neu co: Chua can auth phuc tap neu chi demo local

## 4b. Trang Thai Feature Hien Tai

| Feature | Status | Ghi chu |
|---|---|---|
| F1. Real-time detection | **Done** | Real detection chay bang OpenCV tu carPark.mp4; 18 slots; threshold chinh qua env DETECTION_THRESHOLD |
| F2. Parking map visualization | **Done** | Hien thi slot grid, color vacant/occupied, realtime qua WebSocket |
| F3. Availability summary | **Done** | Tong, occupied, available cap nhat real-time |
| F4. Admin dashboard | **Done** | Route `/admin` hien thi logs + system state |

Web co the chay thu ngay voi mock data: `docker compose up --build` hoac chay tung service local.

## 5. Assumptions Hien Tai

- He thong hien tai duoc xay dung theo huong MVP cho do an hoc tap.
- Frontend dung React + Vite + TypeScript.
- Backend dung FastAPI va WebSocket.
- AI service dung Python, uu tien mock/simulation truoc, sau do gan detection that.
- Co the deploy local bang Docker Compose.

## 6. Task Breakdown

### Epic A. Project foundation

| ID | Task | Module | Priority | Dependency | Status | Done when |
|---|---|---|---|---|---|---|
| A1 | Chot schema payload occupancy giua AI service va backend | `apps/ai-detection-service`, `apps/backend-api`, `docs` | High | None | Done | Payload request/response duoc document ro rang |
| A2 | Chot slot configuration format cho bai xe | `apps/ai-detection-service`, `apps/backend-api`, `docs` | High | A1 | Done | Co file config slot co the dung chung giua cac service |
| A3 | Chuan hoa env vars va local run flow | `infra`, `docs` | Medium | None | Done | `.env.example`, README, compose flow nhat quan |

### Epic B. AI detection pipeline

**Approach da chon: Classical OpenCV (khong can ML model)**
- Input: `datasets/carPark.mp4` hoac `datasets/carParkImg.png`
- Goc nhin: top-down (aerial), camera co dinh — ly tuong cho ROI-based detection
- Logic: crop tung slot ROI → grayscale → blur → adaptive threshold → dem pixel → nhieu pixel = co xe
- Khong can YOLO, khong can train model

| ID | Task | Module | Priority | Dependency | Status | Done when |
|---|---|---|---|---|---|---|
| B4 | Them mock mode de demo khi chua co detection that | `apps/ai-detection-service` | High | A1 | Done | Chay duoc demo end-to-end voi du lieu gia |
| B3 | Co che publish payload dinh ky len backend | `apps/ai-detection-service` | High | A1 | Done | Payload duoc gui ve backend theo chu ky, WebSocket broadcast hoat dong |
| B5 | Annotate toa do pixel cac parking slot tren anh goc | `infra`, `tools` | High | A2 | Done | `infra/slot-coordinates.json` co toa do (x, y, w, h) chinh xac cho tung slot_id; kiem tra bang cach overlay len `carParkImg.png` |
| B1 | Doc video frame tu `carPark.mp4` bang OpenCV | `apps/ai-detection-service` | High | B5 | Done | AI service mo duoc file mp4, doc frame lien tuc, khong crash; log frame index moi giay |
| B2 | Xac dinh occupied/vacant cho tung slot bang classical CV | `apps/ai-detection-service` | High | B1, B5 | Done | Moi slot tra ve occupied=true/false chinh xac tren it nhat 3 frame test; nguong co the chinh qua env var |

### Epic C. Backend API and realtime

| ID | Task | Module | Priority | Dependency | Status | Done when |
|---|---|---|---|---|---|---|
| C1 | Xay dung in-memory hoac DB state store cho slots va summary | `apps/backend-api` | High | A1, A2 | Done | Backend giu duoc latest state va summary |
| C2 | Hoan thien `POST /occupancy/update` | `apps/backend-api` | High | C1 | Done | Backend nhan payload hop le va cap nhat state |
| C3 | Hoan thien `GET /slots`, `GET /slots/status`, `GET /summary` | `apps/backend-api` | High | C1 | Done | Frontend lay duoc state hien tai qua REST |
| C4 | Hoan thien WebSocket broadcast realtime | `apps/backend-api` | High | C1, C2 | Done | Client nhan update moi khi state thay doi |
| C5 | Luu recent update logs cho admin view | `apps/backend-api` | Medium | C2 | Done | Admin xem duoc lich su update gan day |

### Epic D. Web dashboard

| ID | Task | Module | Priority | Dependency | Status | Done when |
|---|---|---|---|---|---|---|
| D1 | Dung data layer ket noi REST + WebSocket | `apps/web-dashboard` | High | C3, C4 | Done | Frontend dong bo state ban dau va realtime |
| D2 | Xay giao dien user view cho parking map + summary | `apps/web-dashboard` | High | D1 | Done | Route `/` hien thi map va thong ke co y nghia |
| D3 | Xay giao dien admin view cho monitoring + logs | `apps/web-dashboard` | High | D1, C5 | Done | Route `/admin` hien thi state he thong va logs |
| D4 | Xu ly loading, error, empty states | `apps/web-dashboard` | Medium | D2, D3 | Done | UI khong vo nghia khi backend chua co du lieu |

### Epic E. Integration and delivery

| ID | Task | Module | Priority | Dependency | Status | Done when |
|---|---|---|---|---|---|---|
| E1 | Hoan thien docker-compose cho full local demo | `infra`, root | Medium | B4, C4, D3 | Done | Toan bo he thong chay bang mot lenh |
| E2 | Viet tai lieu huong dan run demo | `docs`, `README.md` | Medium | E1 | Done | Co huong dan setup, run, verify, screenshot flow |
| E3 | Tao smoke test hoac verification checklist | `docs`, cac app lien quan | Medium | E1 | Done | Co cach xac nhan end-to-end khong bi vo |

## 7. Thu Tu Implement Khuyen Nghi

Phase hien tai (mock done, chuan bi real detection):

1. `B5` — Annotate toa do slot (chay tool, luu slot-coordinates.json)
2. `B1` — OpenCV doc video
3. `B2` — Classical CV detection logic (thay the mock)
4. `E1` — Re-verify docker compose voi detection that

Thu tu goc (da hoan thanh):

1. `A1 -> A2 -> B4` — Contract + mock
2. `C1 -> C2 -> C3 -> C4` — Backend API + WebSocket
3. `D1 -> D2 -> D3 -> D4` — Frontend
4. `E1 -> E2 -> E3` — Docker + docs

## 8. Quy Uoc Trang Thai

Dung 1 trong cac gia tri sau:

- `Todo`
- `In Progress`
- `Blocked`
- `Done`

## 9. Implementation Log

Cap nhat muc nay trong qua trinh Claude thuc thi:

| Date | Item | Note |
|---|---|---|
| 2026-04-19 | Tao file plan khoi tao | Da dung feature MVP mac dinh tu blueprint hien tai |
| 2026-04-19 | Hoan thien contract payload va slot config | Them `infra/slot-config.json`, dong bo backend va AI service theo schema chung |
| 2026-04-19 | Hoan thien mock mode cho AI service | Them loop publish dinh ky, endpoint run-once, env `MOCK_MODE` va `MOCK_INTERVAL_SECONDS` |
| 2026-04-19 | Chuan hoa web dashboard va local demo flow | Them loading/error states, cap nhat README va compose env cho build demo |
| 2026-04-20 | Migrate tu Codex sang Claude Code | Doi AGENTS.md -> CLAUDE.md, CODEX_EXECUTION_PLAN.md -> CLAUDE_EXECUTION_PLAN.md |
| 2026-04-20 | Review codebase va cap nhat plan | F2/F3/F4 xac nhan Done; fix B3 status; them B5 annotation task; chon Classical OpenCV approach cho B1/B2 |
| 2026-05-10 | B5: Annotate 18 slot coordinates bang white-line density analysis | Tao `infra/slot-coordinates.json` (Zone A: 7, Zone B: 5, Zone C: 6); overlay verification passed |
| 2026-05-10 | B1+B2: Real detection pipeline trong ai-detection-service | `real_detection_loop()` doc frame OpenCV, crop ROI, adaptive threshold, publish dinh ky; MOCK_MODE=false de kich hoat |
| 2026-05-10 | Expand slot-config.json len 18 slots; cap nhat requirements.txt, .env.example, docker-compose.yml | opencv-python-headless, DETECTION_THRESHOLD, DETECTION_INTERVAL_SECONDS, SLOT_COORDINATES_PATH |

## 10. Bug Tracker

Format status: `Open` | `In Progress` | `Fixed` | `Won't Fix`

| ID | Phát hiện | Mô tả | Triệu chứng | Root cause | Fix | Status |
|---|---|---|---|---|---|---|
| BUG-01 | 2026-05-17 | WebSocket không hoạt động | Status pill cycling `Disconnected → Connecting` liên tục, log báo `No supported WebSocket library detected`, `GET /ws 404` | `uvicorn` cài thông thường thiếu WebSocket support, cần bản `standard` | `pip install 'uvicorn[standard]'` trong venv backend-api rồi restart | Open |

---

## 11. Blockers / Decisions

| Date | Type | Detail | Owner | Status |
|---|---|---|---|---|
| 2026-04-19 | Decision pending | Can ban cung cap danh sach tinh nang uu tien cuoi cung de Claude chot backlog chinh thuc | User | Open |
| 2026-04-19 | Blocker | Chua co logic doc video/camera that, model detect xe, va annotation slot thuc te nen B1-B3 tam thoi block o muc demo mock mode | User | **Resolved** |
| 2026-04-20 | Decision | Chon Classical OpenCV (khong YOLO) cho detection: goc top-down co dinh, nhe, khong can model weights | Claude | Closed |
| 2026-04-20 | Decision | F2/F3/F4 da done — web chay duoc ngay voi mock data de test UI truoc khi lam real detection | User | Closed |
| 2026-04-20 | Todo | Can chay annotation tool (B5) de danh dau toa do slot tren carParkImg.png truoc khi code B1/B2 | User | Open |
