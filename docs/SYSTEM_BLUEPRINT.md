# Parking Space Detection System - Tech Structure & Implementation Blueprint

## 1. Muc tieu tai lieu

Tai lieu nay mo ta khung suon ky thuat cho do an `Parking-Space-Detection-System` o muc hoc tap, uu tien:

- Cau truc he thong don gian, de lam va de demo
- Chi xay dung giao dien web, khong trien khai mobile app
- Tap trung vao cac feature toi thieu da duoc xac dinh
- Du de mo rong them neu can, nhung khong over-engineering

Muc tieu cua he thong la phat hien trang thai cho dau xe theo thoi gian thuc va hien thi ket qua tren web cho ca user va admin.

## 2. Pham vi trien khai

Day la phien ban hoc tap, vi vay pham vi nen duoc gioi han o muc MVP.

### 2.1. Nhung gi se lam

1. Real-time Space Detection
2. Space Mapping & Visualization
3. Space Counting & Availability Display
4. Web Dashboard cho ca user va admin

### 2.2. Nhung gi chua uu tien

- Mobile app
- Reservation / dat cho truoc
- Billing / hoa don
- Tich hop thanh toan
- Dieu huong nang cao den tung o
- Tich hop Google Maps
- Dieu khien LED board vat ly ngoai doi thuc

Ghi chu:

- Neu can demo feature guidance, co the chi dung muc goi y khu vuc con trong tren web, khong can xay app rieng va khong can routing phuc tap.

## 3. Kien truc tong quan

He thong duoc chia thanh 3 tang chinh:

```text
[Data Acquisition Layer] -> [Processing & AI Layer] -> [Web Presentation Layer]
 Sensors / Cameras            Detection Engine           User Web / Admin Web
```

### 3.1. Tang Thu Thap Du Lieu

Nhiem vu:

- Lay du lieu tu camera hoac video mau
- Truyen frame sang AI service de xu ly

Trong pham vi hoc tap, nen uu tien:

- Camera-based
hoac
- Video dataset co san

Ly do:

- De demo
- Khong can dau tu sensor that
- Phu hop de lam mo hinh nhan dien bang OpenCV/YOLO

### 3.2. Tang Xu Ly & AI

Nhiem vu:

- Detect xe trong frame
- Xac dinh moi parking slot dang trong hay da co xe
- Tong hop so cho trong theo khu vuc hoac toan bai
- Gui ket qua sang backend/web theo thoi gian thuc

Thanh phan:

- Detection service
- Slot mapping logic
- Occupancy state engine
- Backend API

### 3.3. Tang Hien Thi Web

Nhiem vu:

- Hien thi ban do bai xe
- Hien thi mau sac trang thai tung o
- Hien thi tong so cho trong
- Ho tro 2 nhom nguoi dung tren cung mot web:
  - User: xem cho trong
  - Admin: xem tong quan va giam sat

## 4. Feature toi thieu can co

## 4.1. Real-time Space Detection

Mo ta:

- He thong doc frame tu camera/video
- Phat hien xe
- Xac dinh tung o dang `Occupied` hay `Vacant`

Output:

- `0 = vacant`
- `1 = occupied`

Tan suat cap nhat:

- Moi 1-3 giay la du cho demo hoc tap

## 4.2. Space Mapping & Visualization

Mo ta:

- Mo phong layout bai xe tren web
- Moi o dau xe co vi tri co dinh va trang thai rieng
- Hien thi bang mau sac

Quy uoc mau de xuat:

- Xanh: trong
- Do: co xe
- Xam: khong hoat dong hoac chua co du lieu

## 4.3. Space Counting & Availability Display

Mo ta:

- Tinh tong so cho trong
- Hien thi theo:
  - toan bai
  - tung khu vuc neu can

Cong thuc:

`available = total_slots - occupied_slots`

## 4.4. Web Dashboard cho User va Admin

Mo ta:

- Khong tach thanh app rieng
- Chi can 1 web system
- Co the chia 2 man hinh hoac 2 role

Chuc nang User:

- Xem so cho trong
- Xem ban do cho trong theo thoi gian thuc

Chuc nang Admin:

- Xem toan bo trang thai bai xe
- Theo doi log cap nhat
- Cau hinh danh sach parking slots

## 5. De xuat tech structure

Voi pham vi hoc tap, nen chon kien truc gon nhe:

```text
[Camera / Video Input]
        |
        v
[AI Detection Service]
        |
        v
[Backend API + WebSocket]
        |
        +--> [Web UI for User]
        +--> [Web UI for Admin]
        |
        +--> [Database]
```

## 5.1. AI / Computer Vision

Cong nghe de xuat:

- Python
- OpenCV
- YOLO
- NumPy

Vai tro:

- Doc video/stream
- Detect vehicle
- Xac dinh trang thai parking slot
- Gui du lieu JSON sang backend

## 5.2. Backend

Cong nghe de xuat:

- FastAPI
hoac
- Node.js + Express

Khuyen nghi cho do an nay:

- Chon `FastAPI` neu muon dong bo ngon ngu voi AI service
- Chon `Express` neu team quen JavaScript

Backend can lam:

- Nhan du lieu occupancy tu AI service
- Luu trang thai hien tai
- Cung cap REST API
- Day realtime qua WebSocket

## 5.3. Web Frontend

Cong nghe de xuat:

- React + Vite
- TypeScript
- TailwindCSS hoac CSS thuong

Frontend can lam:

- Hien thi parking map
- Hien thi thong ke so cho trong
- Nghe du lieu realtime tu backend
- Tach giao dien user/admin bang route hoac role

## 5.4. Database

Neu muon giu don gian:

- SQLite cho giai doan dau

Neu muon de mo rong hon:

- PostgreSQL

Bang toi thieu de xuat:

- parking_slots
- cameras
- slot_status_logs
- users

## 5.5. Infra

Toi thieu:

- Docker
- Docker Compose

Khong can:

- Kubernetes
- He thong microservices phuc tap

## 6. De xuat chia repo

Voi muc tieu hoc tap, nen dung `monorepo`.

Ly do:

- Don gian de quan ly
- De chay local
- De viet tai lieu va demo
- Khong can tach qua nhieu repo

Cau truc de xuat:

```text
Parking-Space-Detection-System/
├─ apps/
│  ├─ ai-detection-service/
│  ├─ backend-api/
│  └─ web-dashboard/
├─ docs/
├─ datasets/
├─ infra/
└─ README.md
```

Mo ta:

- `ai-detection-service`: xu ly video/camera va tra trang thai slot
- `backend-api`: API, websocket, log, cung cap du lieu
- `web-dashboard`: giao dien web cho user va admin
- `datasets`: video test, anh mau, file annotation
- `docs`: tai lieu kien truc, schema, API
- `infra`: docker-compose, env mau

## 7. Deployment Strategy cho Monorepo

`Monorepo` khong co nghia la tat ca phai deploy chung thanh mot app duy nhat.
No chi co nghia la nhieu app cung nam trong cung mot repo.

Voi cau truc:

```text
apps/
  ai-detection-service/
  backend-api/
  web-dashboard/
```

co 2 cach deploy phu hop nhat.

### 7.1. Cach 1 - Deploy FE va BE rieng

Mo hinh:

```text
User Browser -> Web Dashboard URL
Web Dashboard -> goi Backend API URL
AI Detection Service -> gui data ve Backend API
Backend API -> push realtime ve Web Dashboard
```

Vi du:

- FE: `https://parking-web.example.com`
- BE: `https://parking-api.example.com`
- AI: chay local, cung may BE, hoac mot service rieng

Uu diem:

- Giong cach lam FE/BE tach rieng ma ban da quen
- De debug
- De thay doi frontend ma khong anh huong backend

Can chu y:

- FE can config `API_BASE_URL`
- Backend can mo `CORS` cho domain FE
- Neu dung WebSocket, FE can co `WS_URL`

### 7.2. Cach 2 - Build FE va serve tu Backend

Mo hinh:

```text
User Browser -> Backend URL
Backend -> vua tra file web build, vua tra API/WebSocket
AI Detection Service -> gui data ve Backend
```

Vi du:

- Web + API chung 1 URL: `https://parking-system.example.com`

Uu diem:

- De demo do an
- Chi can 1 URL
- Giam ro ri CORS
- Deploy don gian hon

Nhuoc diem:

- FE va BE dính nhau hon trong quy trinh deploy

### 7.3. Khuyen nghi cho do an nay

Nen uu tien `Cach 2` trong giai doan demo:

- `web-dashboard` build thanh static files
- `backend-api` serve luon static files do
- `ai-detection-service` chay local hoac cung may backend

Ly do:

- It cong doan deploy hon
- It loi CORS hon
- It domain hon
- De trinh bay va bao ve do an

Neu sau nay muon tach rieng, monorepo van giu nguyen va co the deploy FE/BE thanh 2 service doc lap.

## 8. Huong trien khai de xuat

Khong nen chia qua nhieu phase. Voi do an hoc tap, 3 giai doan la du.

## Phase 1 - Detection MVP

Muc tieu:

- Doc video/camera
- Detect xe
- Xac dinh occupied/vacant cho tung slot

Deliverables:

- AI detection service chay duoc local
- File config parking slots
- JSON output cua trang thai cac slot

## Phase 2 - Backend + Realtime

Muc tieu:

- Nhan du lieu tu AI service
- Luu log co ban
- Day du lieu realtime len web

Deliverables:

- Backend API
- WebSocket realtime
- API lay danh sach slot va trang thai hien tai

## Phase 3 - Web Demo

Muc tieu:

- Hien thi map bai xe
- Hien thi so cho trong
- Tach man hinh user/admin o muc co ban

Deliverables:

- Trang user
- Trang admin
- Dashboard realtime

## 9. Huong thiet ke module

## 9.1. AI Detection Module

Input:

- Video file, webcam, hoac RTSP stream
- Toa do parking slots da duoc danh dau truoc

Output mau:

```json
{
  "camera_id": "cam-01",
  "timestamp": "2026-04-06T10:00:00Z",
  "slots": [
    { "slot_id": "A-01", "occupied": true },
    { "slot_id": "A-02", "occupied": false }
  ]
}
```

Chuc nang:

- Frame capture
- Vehicle detection
- Parking slot occupancy evaluation
- Gui ket qua sang backend

## 9.2. Backend API Module

Trach nhiem:

- Nhan du lieu occupancy
- Luu trang thai moi nhat
- Luu lich su thay doi co ban
- Tra du lieu cho frontend
- Push realtime

API toi thieu:

- `GET /slots`
- `GET /slots/status`
- `GET /summary`
- `POST /occupancy/update`

## 9.3. Web Module

Man hinh User:

- Xem tong so cho trong
- Xem layout bai xe

Man hinh Admin:

- Xem trang thai toan bo slot
- Xem danh sach slot
- Xem log cap nhat gan day

## 10. Danh sach cong viec can lam

## 10.1. Cong viec khoi dong

1. Chot huong camera-based cho MVP
2. Thu thap video/anh mau de test
3. Ve layout bai xe va danh dau parking slots
4. Chot monorepo structure
5. Chot stack backend/frontend

## 10.2. Cong viec AI

1. Tao service doc video
2. Tich hop model detect xe
3. Tao file slot config
4. Viet logic xac dinh occupied/vacant
5. Xuat ket qua thanh JSON

## 10.3. Cong viec backend

1. Khoi tao API service
2. Tao API nhan occupancy update
3. Tao API lay du lieu slot
4. Tao websocket realtime
5. Luu log thay doi trang thai

## 10.4. Cong viec frontend

1. Khoi tao web dashboard
2. Ve layout bai xe
3. Hien thi mau sac trang thai tung slot
4. Hien thi summary tong so cho trong
5. Ket noi websocket realtime
6. Tao trang user va trang admin

## 10.5. Cong viec infra

1. Tao Dockerfile cho tung service
2. Tao `docker-compose.yml`
3. Tao file `.env.example`

## 11. Roadmap ngan han de bat dau ngay

1. Tao cau truc monorepo gom `ai-detection-service`, `backend-api`, `web-dashboard`
2. Chuan bi 1 video test va file cau hinh parking slots
3. Viet AI service xuat trang thai slot tu video
4. Viet backend nhan JSON va phat realtime
5. Viet web hien thi layout + summary
6. Hoan thien demo user/admin tren cung mot he thong web

## 12. Ket luan

Voi pham vi do an hoc tap, huong trien khai hop ly nhat la:

- Chi dung web, khong lam mobile app
- Uu tien camera/video-based detection
- Tap trung vao 4 feature toi thieu:
  - phat hien cho trong
  - hien thi map
  - dem so cho trong
  - dashboard web cho user/admin
- Dung monorepo va kien truc gon nhe de de phat trien, de demo, de bao cao

Tai lieu nay la nen tang de lam tiep:

- Scaffold source code
- Thiet ke database schema
- Viet API contract
- Lap ke hoach phan chia cong viec trong nhom
