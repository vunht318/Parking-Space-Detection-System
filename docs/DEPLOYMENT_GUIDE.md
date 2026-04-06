# Deployment Guide - Monorepo cho Parking Space Detection System

## 1. Muc tieu

Guide nay giai thich cach deploy monorepo cho du an theo huong don gian nhat:

- `React + Vite` cho web
- `FastAPI` cho backend
- `Python` cho AI detection service

Tai lieu nay uu tien tinh thuc chien cho do an hoc tap, khong di qua sau vao production-scale architecture.

## 2. Monorepo va deploy la 2 viec khac nhau

Monorepo chi la cach to chuc source code.

Vi du:

```text
Parking-Space-Detection-System/
├─ apps/
│  ├─ ai-detection-service/
│  ├─ backend-api/
│  └─ web-dashboard/
└─ docs/
```

Khi deploy, ban co the:

1. Deploy `web-dashboard` rieng va `backend-api` rieng
2. Build `web-dashboard` roi de `backend-api` serve luon
3. Deploy them `ai-detection-service` thanh service rieng neu can

## 3. Cach deploy phu hop nhat voi do an nay

Nen chon:

1. `backend-api` la service chinh
2. `web-dashboard` build ra file tinh
3. `backend-api` serve luon web build
4. `ai-detection-service` chay local hoac chay cung may backend

So do:

```text
AI Detection Service ---> Backend API ---> Browser
                              |
                              +--> REST API
                              +--> WebSocket
                              +--> static web files
```

Nghia la nguoi dung chi can vao 1 URL.

Vi du:

- `https://parking-demo.example.com`

Tai URL nay:

- `/` tra giao dien React build
- `/api/*` tra API
- `/ws` la WebSocket

## 4. Khi nao nen tach FE va BE rieng

Nen tach rieng neu:

- Ban quen kieu FE URL va BE URL
- Frontend va backend do 2 nhom phat trien doc lap
- Ban muon deploy frontend nhanh, cap nhat rieng

Mo hinh:

```text
FE: https://parking-web.example.com
BE: https://parking-api.example.com
AI: local hoac service rieng
```

Khi do:

- FE goi API sang domain BE
- FE mo WebSocket toi BE
- Backend phai config `CORS`

## 5. Khuyen nghi thuc te cho ban

Voi muc do kinh nghiem hien tai va muc tieu do an:

- Trong luc phat trien local: co the chay FE rieng, BE rieng
- Khi demo/deploy: nen gop FE vao BE de co 1 URL

Day la cach can bang tot nhat:

- Dev de thao tac
- Demo de trinh bay

## 6. Luong chay local de de phat trien

Khi dev local:

```text
React dev server: http://localhost:5173
FastAPI backend:  http://localhost:8000
AI service:       http://localhost:9000 hoac worker local
```

Luong du lieu:

```text
Browser -> React dev server
React -> goi API sang FastAPI
AI service -> POST occupancy data ve FastAPI
FastAPI -> push realtime ve React qua WebSocket
```

Ban se code nhanh hon vi:

- FE hot reload rieng
- BE restart rieng
- AI process doc lap

## 7. Luong deploy de demo

Khi deploy:

```text
Browser -> FastAPI
FastAPI -> serve React build
FastAPI -> expose /api va /ws
AI service -> gui data vao FastAPI
```

Khi do URL co the la:

- `https://parking-demo.onrender.com/`
- `https://parking-demo.onrender.com/api/summary`
- `wss://parking-demo.onrender.com/ws`

## 8. Bien moi truong ban can nghi den

## 8.1. Luc dev local

Web:

```env
VITE_API_BASE_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
```

Backend:

```env
APP_ENV=development
PORT=8000
DATABASE_URL=sqlite:///./parking.db
AI_SHARED_SECRET=demo-secret
```

AI service:

```env
BACKEND_API_URL=http://localhost:8000/api
AI_SHARED_SECRET=demo-secret
VIDEO_SOURCE=./datasets/sample.mp4
```

## 8.2. Luc deploy demo 1 URL

Web:

- Thuong khong can `VITE_API_BASE_URL` neu FE duoc build de goi cung origin

Frontend co the goi:

- `/api/summary`
- `/api/slots`
- `/ws`

Backend:

```env
APP_ENV=production
PORT=8000
DATABASE_URL=sqlite:///./parking.db
AI_SHARED_SECRET=demo-secret
STATIC_DIR=./static
```

AI service:

```env
BACKEND_API_URL=https://parking-demo.example.com/api
AI_SHARED_SECRET=demo-secret
VIDEO_SOURCE=./datasets/sample.mp4
```

## 9. CORS co can khong

Neu FE va BE tach rieng:

- Co

Backend can cho phep domain cua FE, vi du:

- `https://parking-web.example.com`

Neu FE duoc serve boi chinh backend:

- Thuong khong can cau hinh CORS phuc tap cho browser

Day la mot trong nhung ly do nen deploy chung 1 URL cho do an.

## 10. AI service nen deploy the nao

Ban co 3 lua chon:

### Lua chon 1 - Chay local tren may demo

Phu hop nhat neu:

- Ban demo bang video mau
- Ban doc webcam/camera tai cho
- Ban khong can host AI tren cloud

Uu diem:

- Don gian
- De kiem soat
- It ton chi phi

### Lua chon 2 - Chay cung may backend

Phu hop neu:

- Ban co VPS hoac may chu rieng
- Ban muon gop backend va AI tren 1 may

Can chu y:

- AI xu ly video co the an CPU/GPU
- Khong nen de no anh huong backend neu tai nguyen qua it

### Lua chon 3 - Tach thanh service rieng

Phu hop neu:

- Ban muon ro rang ve kien truc
- Ban can scale AI doc lap

Voi do an cua ban, `Lua chon 1` hoac `Lua chon 2` hop ly hon.

## 11. Docker mindset cho monorepo

Monorepo van co the co nhieu container.

Vi du:

```text
services:
  backend-api
  web-dashboard-build
  ai-detection-service
```

Nhung voi do an nay, ban nen nghi theo huong:

```text
services:
  backend-api
  ai-detection-service
```

Trong do:

- `web-dashboard` duoc build thanh static files
- `backend-api` serve static files nay

Nhu vay docker-compose gon hon.

## 12. Lo trinh deploy de xuat

1. Dev local voi 3 app tach rieng
2. Hoan thien FE, BE, AI o local
3. Build `web-dashboard`
4. Copy output build vao backend static folder
5. Cau hinh FastAPI:
   - serve `/api/*`
   - serve `/ws`
   - serve file tĩnh cho `/`
6. Deploy backend len 1 server/service
7. Chay AI service local hoac cung server backend
8. Test end-to-end bang 1 URL duy nhat

## 13. Cau truc URL de xuat

Khi deploy chung:

```text
/
/admin
/api/slots
/api/summary
/api/occupancy/update
/ws
```

Ghi chu:

- `/` co the la man hinh user
- `/admin` la man hinh admin
- Cung mot React app, tach route ben trong

## 14. Ket luan

Voi monorepo cua ban:

- Khong bat buoc FE va BE deploy chung
- FE va BE van co the deploy rieng nhu cach ban da quen
- Nhung doi voi do an, nen deploy theo huong `1 URL`, nghia la backend serve luon frontend build

Tom lai:

- Dev: tach FE/BE de lam cho de
- Demo/Deploy: gop FE vao BE de gon, on dinh, de trinh bay
