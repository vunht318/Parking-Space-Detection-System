# Codex Execution Plan

## 1. Muc tieu

Tai lieu nay la file lam viec chinh de Codex build he thong `Parking-Space-Detection-System` theo quy trinh end-to-end.

Flow su dung:

1. Ban cung cap danh sach tinh nang.
2. Codex chuyen danh sach tinh nang thanh backlog va task list ky thuat.
3. Codex cap nhat file nay trong suot qua trinh implement.
4. Codex danh dau trang thai task khi da xong hoac bi blocker.

## 2. Cach Codex se lam viec

Codex se di theo thu tu sau:

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

| ID | Task | Module | Priority | Dependency | Status | Done when |
|---|---|---|---|---|---|---|
| B1 | Tao video/frame ingestion pipeline | `apps/ai-detection-service` | High | A2 | Blocked | AI service doc duoc source video/camera co ban |
| B2 | Tao occupancy evaluation logic theo slot config | `apps/ai-detection-service` | High | B1 | Blocked | Moi slot co state occupied/vacant/unknown |
| B3 | Phat sinh payload occupancy update dinh ky | `apps/ai-detection-service` | High | B2 | Blocked | Payload hop dong va gui duoc cho backend |
| B4 | Them mock mode de demo khi chua co model that | `apps/ai-detection-service` | High | A1 | Done | Chay duoc demo end-to-end khong phu thuoc model train |

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

1. `A1 -> A2 -> B4`
2. `C1 -> C2 -> C3 -> C4`
3. `D1 -> D2 -> D3`
4. `B1 -> B2 -> B3`
5. `E1 -> E2 -> E3`

Ly do:

- Can mock mode som de frontend va backend co du lieu song de phat trien.
- Can chot contract truoc khi code song song nhieu app.
- Frontend nen di sau khi backend co REST + WebSocket on dinh.

## 8. Quy Uoc Trang Thai

Dung 1 trong cac gia tri sau:

- `Todo`
- `In Progress`
- `Blocked`
- `Done`

## 9. Implementation Log

Cap nhat muc nay trong qua trinh Codex thuc thi:

| Date | Item | Note |
|---|---|---|
| 2026-04-19 | Tao file plan khoi tao | Da dung feature MVP mac dinh tu blueprint hien tai |
| 2026-04-19 | Hoan thien contract payload va slot config | Them `infra/slot-config.json`, dong bo backend va AI service theo schema chung |
| 2026-04-19 | Hoan thien mock mode cho AI service | Them loop publish dinh ky, endpoint run-once, env `MOCK_MODE` va `MOCK_INTERVAL_SECONDS` |
| 2026-04-19 | Chuan hoa web dashboard va local demo flow | Them loading/error states, cap nhat README va compose env cho build demo |

## 10. Blockers / Decisions

| Date | Type | Detail | Owner | Status |
|---|---|---|---|---|
| 2026-04-19 | Decision pending | Can ban cung cap danh sach tinh nang uu tien cuoi cung de Codex chot backlog chinh thuc | User | Open |
| 2026-04-19 | Blocker | Chua co logic doc video/camera that, model detect xe, va annotation slot thuc te nen B1-B3 tam thoi block o muc demo mock mode | User | Open |
